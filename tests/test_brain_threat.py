"""Threat and targeting (brain/, phase 1a), offline, in the real game:

    python3 tests/test_brain_threat.py

- a blow makes threat by the attacker's class (a warrior's counts half again); healing someone a
  creature fights makes threat on the healer;
- whom a creature fights: the most threatening, kept unless another is clearly ahead
  (stickiness) and not twice inside its switch cooldown; a turn is said aloud and sent as 'aggro';
- its foe falls: the next who hurt it, if here; a target the rest of the game sets (rescue) holds;
- taunt: a warrior's or paladin's in a fight holds the creature; anyone else's, or out of a
  fight, is the social; it cools down;
- Commanding Shout reaches only creatures fighting your side (never a shopkeeper, nor a pet);
- a creature healer heals its own side, never a player's pet; a pet takes no creature specials;
- MH_BRAIN_OFF=threat: the old rules.
"""
import asyncio
import logging
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import test_webmove as tw  # noqa: E402  (check(), failures)
from test_action_combat import Conn, FakeMap, put  # noqa: E402

check, failures = tw.check, tw.failures


async def main():
    logging.disable(logging.WARNING)
    from config import Config
    from world import World
    from player import Player
    import combat_hooks
    import combat_range as cr
    import mob_ai
    import brain
    from brain import targeting, threat as threat_mod
    from bosses import create_mob_from_prototype
    from commands import CommandHandler

    world = World(Config())
    await world.load()
    wm = FakeMap()
    world.web_map = wm
    combat_hooks.install()
    brain.install()
    random.seed(3)
    check(brain.on('threat'), 'features.threat is on (world/ai_profiles.json)')
    ROOM = world.rooms[3054] if 3054 in world.rooms else world.rooms[3001]

    def clear():
        for ch in list(ROOM.characters):
            ROOM.characters.remove(ch)
        world.npcs[:] = []

    def hero(name, cls='warrior', level=30):
        p = Player(world)
        p.name, p.char_class, p.level = name, cls, level
        p.max_hp = p.hp = 900
        p.max_mana = p.mana = 900
        p.connection = Conn()
        p.world = world
        world.players[name.lower()] = p
        put(p, ROOM)
        cr.set_pos(p, 12, 7)
        return p

    def foe(name='brute', vnum=3062, hp=3000, roles=None):
        proto = dict(world.mob_prototypes[vnum])
        if roles is not None:
            proto['ai'] = {'roles': roles}
        mob = create_mob_from_prototype(proto, world)
        mob.name = name
        mob.max_hp = mob.hp = hp
        mob.home_zone = None
        put(mob, ROOM)
        world.npcs.append(mob)
        cr.set_pos(mob, 13, 7)
        return mob

    def fight(a, b):
        a.fighting, b.fighting = b, a
        a.position = b.position = 'fighting'

    # ---------------- where threat comes from
    clear()
    war, mage, ogre = hero('War'), hero('Mag', 'mage'), foe('ogre', roles=['guarded'])
    fight(war, ogre)
    await ogre.take_damage(100, war)
    await ogre.take_damage(100, mage)
    b = brain.of(ogre)
    check(abs(b.threat.get(war) - 150) < 1e-6 and abs(b.threat.get(mage) - 100) < 1e-6,
          f"a warrior's blows count half again ({b.threat.get(war):.0f} vs the mage's {b.threat.get(mage):.0f})")
    war.war_doctrine = 'iron_wall'
    check(threat_mod.threat_mod(war) == 2.0, 'an Iron Wall warrior counts twice')
    war.war_doctrine = None

    clear()
    tank, cler, wolf1, wolf2 = hero('Tank'), hero('Cler', 'cleric'), foe('wolf'), foe('wolf')
    for w in (wolf1, wolf2):
        w.fighting, w.position = tank, 'fighting'
    tank.hp = 300
    from spells import SpellHandler, SPELLS
    heal_key = next(k for k in ('heal', 'cure_critical', 'cure_serious', 'cure_light') if k in SPELLS)
    await SpellHandler.apply_spell(cler, tank, SPELLS[heal_key], heal_key)
    gained = tank.hp - 300
    t1, t2 = brain.of(wolf1).threat.get(cler), brain.of(wolf2).threat.get(cler)
    check(gained > 0 and abs(t1 - gained * threat_mod.HEAL_SHARE / 2) < 1 and abs(t1 - t2) < 1e-6,
          f'healing the one they fight: threat on the healer, shared between them ({gained} healed -> {t1:.0f} each)')

    # ---------------- whom it fights: stickiness, the cooldown, the announcement
    clear()
    a, c, troll = hero('Aro'), hero('Cyn', 'cleric'), foe('troll', roles=['guarded'])
    fight(a, troll)
    b = brain.of(troll)
    b.threat.add(a, 100)
    b.threat.add(c, 120)                        # ahead, but within stickiness (0.3)
    await targeting.retarget(troll, b, now=1000.0)
    check(troll.fighting is a, 'a foe a little ahead does not turn it (stickiness)')
    b.threat.add(c, 100)                        # 220 vs 100: clearly ahead
    a.connection.lines.clear()
    wm.full = []
    await targeting.retarget(troll, b, now=1001.0)
    await asyncio.sleep(0.02)
    check(troll.fighting is c, 'a foe clearly ahead does')
    check(any('turns on Cyn' in s for s in a.connection.lines), f'...said aloud ({a.connection.lines[-1:]})')
    check(any(e.get('k') == 'aggro' for e in (wm.full or [])), "...and sent to /play as 'aggro'")
    b.threat.add(a, 500)
    await targeting.retarget(troll, b, now=1002.0)
    check(troll.fighting is c, 'not again inside its switch cooldown')
    await targeting.retarget(troll, b, now=1001.0 + b.profile['switch_cooldown_s'] + 0.1)
    check(troll.fighting is a, '...but after it')
    import action_combat as ac
    troll._turn_foe, troll._turn_at = troll.fighting, time.time() + 3.0
    b.threat.add(c, 100000)
    await targeting.retarget(troll, b, now=1100.0)
    turn_at = troll._turn_at
    await ac.mob_turn(troll, time.time())
    check(troll.fighting is c and troll._turn_at == turn_at,
          'on the real-time clock a creature that turns keeps its turn time (no early turn for turning)')
    troll.pending_intent = {'kind': 'heavy', 'declared_at': 1110.0}
    b.threat.add(a, 10 ** 6)
    await targeting.retarget(troll, b, now=1130.0)
    check(troll.fighting is c, 'never turns while winding up a special (the warning named its target)')
    troll.pending_intent = None

    # ---------------- its foe falls: the next who hurt it; a target set from outside holds
    clear()
    p1, p2, bear = hero('Pia'), hero('Pol'), foe('bear', roles=['guarded'])
    fight(p1, bear)
    b = brain.of(bear)
    await bear.take_damage(50, p1)
    await bear.take_damage(30, p2)
    ROOM.characters.remove(p1)                 # Pia leaves
    got = await brain.next_target(bear)
    check(got is p2 and bear.fighting is p2, 'its foe gone: the next who hurt it, still here')
    put(p1, ROOM)
    await targeting.retarget(bear, b)
    bear.fighting = p1                          # rescue, a pull, a helper: set from outside
    b.threat.add(p2, 10000)
    await targeting.retarget(bear, b)
    check(bear.fighting is p1, 'a target the rest of the game sets is held (a short taunt)')

    # ---------------- taunt
    clear()
    w, cl, gob = hero('Wren'), hero('Clio', 'cleric'), foe('goblin', roles=['guarded'])
    gob.fighting, gob.position = cl, 'fighting'
    cl.fighting = gob
    b = brain.of(gob)
    b.threat.add(cl, 400)
    await CommandHandler.cmd_taunt(w, ['goblin'])
    check(gob.fighting is w and b.threat.top() is w, "a warrior's taunt: the goblin turns on them, top of its table")
    check(b.threat.fixated_on is w and b.threat.fixated_until > time.time() + 5, '...and is held about 6 s')
    w.connection.lines.clear()
    await CommandHandler.cmd_taunt(w, ['goblin'])
    check(any('taunt again' in s for s in w.connection.lines), 'taunt cools down')
    m = hero('Mira', 'mage')
    m.connection.lines.clear()
    fix_before = b.threat.fixated_on
    await CommandHandler.cmd_taunt(m, ['goblin'])
    check(b.threat.fixated_on is fix_before and gob.fighting is w, "a mage's taunt is the social: nothing turns")
    clear()
    calm_w, calm = hero('Wil'), foe('rat', roles=['guarded'])
    await CommandHandler.cmd_taunt(calm_w, ['rat'])
    check(calm.fighting is None, 'out of a fight, taunt is the social: the rat stays calm')

    # ---------------- Commanding Shout: only those fighting your side
    clear()
    shouter, ally, orc = hero('Shout', level=50), hero('Ally', 'cleric'), foe('orc', roles=['guarded'])
    keeper = foe('shopkeeper', roles=['guarded'])
    orc.fighting, orc.position = ally, 'fighting'
    from pets import PetManager
    pet = None
    try:
        pet = await PetManager.summon_pet(ally, 'undead_warrior', duration_minutes=5)
    except Exception:
        pet = None
    await CommandHandler.cmd_commanding_shout(shouter, [])
    check(orc.fighting is shouter and brain.of(orc).threat.fixated_on is shouter, 'Commanding Shout holds the orc fighting your side')
    check(keeper.fighting is None, '...never the shopkeeper standing by')
    if pet is not None:
        check(getattr(pet, 'fighting', None) is not shouter, "...nor anyone's pet")

    # ---------------- a creature healer heals its own side; a pet takes no creature specials
    clear()
    owner, priest, kin = hero('Owen', 'necromancer'), foe('priest', roles=['healer'], hp=500), foe('kin', hp=500)
    servant = None
    try:
        servant = await PetManager.summon_pet(owner, 'undead_warrior', duration_minutes=5)
    except Exception as e:
        print(f'     (no servant: {e!r})')
    priest.mana = 500
    priest.fighting, priest.position = owner, 'fighting'
    if servant is not None:
        servant.max_hp = 1000
        servant.hp = 100
        kin.hp = 300                            # wounded (60%), but less so than the servant (10%)
        await mob_ai._healer_tick(priest, owner)
        check(servant.hp == 100 and kin.hp > 300, f'a creature healer heals its kin, never the necromancer\'s servant ({servant.hp}, {kin.hp})')
        servant.fighting, servant.position = priest, 'fighting'
        servant.ai_state, servant.level, servant.pending_intent = {}, owner.level + 5, None
        for _ in range(10):
            await mob_ai.declare_intents(servant)
        check(servant.pending_intent is None, 'a pet winds up no creature specials (its owner bids it)')
        check(not await mob_ai.mob_ai_tick(servant), '...and takes no creature turn of its own')
        brain.of(priest).threat.add(owner, 50)
        check(not len(brain.of(servant).threat), 'a pet keeps no threat table')

    # ---------------- the switch: MH_BRAIN_OFF=threat is the old rules
    brain.FORCED_OFF.add('threat')
    try:
        clear()
        x, y, cat = hero('Xan'), hero('Yo'), foe('cat', roles=['guarded'])
        fight(x, cat)
        await cat.take_damage(100, y)
        check(not len(brain.of(cat).threat), 'threat off: no table kept')
        cat.fighting = None
        await CommandHandler.cmd_taunt(x, ['cat'])
        check(cat.fighting is None, '...and taunt is the social')
    finally:
        brain.FORCED_OFF.discard('threat')

    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
