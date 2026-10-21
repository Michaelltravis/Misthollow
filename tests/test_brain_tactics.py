"""Tactics (brain/, phase 1b), offline, in the real game:

    python3 tests/test_brain_tactics.py

- a caster's hex is the spell's own affect (a real slow, not a lost turn), Unfettered wards it;
  its ward is a timed affect, once a fight; its spells come from its role's book by level;
- healers heal by declared, interruptible prayer; an elite silences the player healing its foes
  (Disrupt), aimed at the healer; interrupt reaches any creature winding up in the room;
- the zone's real-time wind-up: readable 2 s, brutal 1.4 s;
- creatures learn a hold's school; another school lands; they forget when the fight is over;
- breakouts: rouse (and its cooldown), fire frees the entangled, a blow wakes a sleeper and breaks
  a creature's charm;
- what a creature could do once a fight (pack call, enrage) comes back next fight;
- archers and supporters are read from their words;
- MH_BRAIN_OFF=tactics: the old rules.
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
    from brain import cast, cc
    from bosses import create_mob_from_prototype
    from commands import CommandHandler
    from spells import SpellHandler, SPELLS

    world = World(Config())
    await world.load()
    wm = FakeMap()
    world.web_map = wm
    combat_hooks.install()
    brain.install()
    random.seed(5)
    check(brain.on('tactics'), 'features.tactics is on (world/ai_profiles.json)')
    ROOM = world.rooms[3054] if 3054 in world.rooms else world.rooms[3001]

    def clear():
        for ch in list(ROOM.characters):
            ROOM.characters.remove(ch)
        world.npcs[:] = []
        ROOM.zone.ai = None

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

    def foe(name='brute', roles=None, level=32, rank=None, hp=3000):
        proto = dict(world.mob_prototypes[3062])
        proto['level'] = level
        if roles is not None:
            proto['ai'] = {'roles': roles}
        if rank:
            proto['rank'] = rank
        mob = create_mob_from_prototype(proto, world)
        mob.name = name
        mob.max_hp = mob.hp = hp
        mob.max_mana = mob.mana = 500
        mob.home_zone = None
        put(mob, ROOM)
        world.npcs.append(mob)
        cr.set_pos(mob, 13, 7)
        return mob

    def fight(a, b):
        a.fighting, b.fighting = b, a
        a.position = b.position = 'fighting'

    # ---------------- a caster: its book, its ward, a real hex
    clear()
    ace, mage = hero('Ace'), foe('conjurer', roles=['caster'], level=12)
    fight(ace, mage)
    b = brain.of(mage)
    book = cast.known(mage, b)
    check('magic_missile' in book and 'blindness' in book and 'fireball' not in book,
          f'a level-12 caster knows its role book up to its level ({book})')
    ac0 = mage.armor_class
    await mob_ai.mob_ai_tick(mage)
    check(b.encounter.get('warded') and any(a.name for a in mage.affects) and mage.armor_class != ac0,
          'its first turn puts up its ward, a real affect')
    check(all(getattr(a, 'duration', 0) > 0 for a in mage.affects), '...that runs out (a duration), not a permanent change')
    mage.ai_state['spell_cd'] = 0
    await cast.resolve_hex(mage, ace, 'slow')
    check('slow' in (ace.affect_flags or set()) and not getattr(ace, 'stunned_rounds', 0),
          "a 'slow' hex is the spell's slow (half the swings), not a lost turn")
    SpellHandler._cleanse(ace)
    ace.freedom_until = time.time() + 30
    await cast.resolve_hex(mage, ace, 'entangle')
    check('entangled' not in (ace.affect_flags or set()), 'Unfettered wards off a root hex')
    ace.freedom_until = 0

    # ---------------- heals are prayers; Disrupt; interrupt reaches anyone here
    clear()
    tank, cler = hero('Tank'), hero('Cler', 'cleric')
    priest, kin = foe('priest', roles=['healer']), foe('raider')
    for m in (priest, kin):
        m.fighting, m.position = tank, 'fighting'
    tank.fighting = kin
    kin.hp = 1000
    hp0 = kin.hp
    await mob_ai.mob_ai_tick(priest)
    check(kin.hp == hp0, 'a healer never heals instantly any more')
    priest.pending_intent = None
    await mob_ai.declare_intents(priest)
    it = priest.pending_intent
    check(it and it['kind'] == 'heal' and it.get('interruptible') and it.get('target') is kin,
          f"...it prays over its wounded kin, declared and interruptible ({it and it.get('telegraph')})")
    await CommandHandler.cmd_interrupt(tank, [])
    check(priest.pending_intent is None or any('interrupt again' in s or 'fail' in s for s in tank.connection.lines),
          'interrupt reaches the healer praying behind the line (not only your own foe)')
    priest.pending_intent = dict(it, declared_at=time.time() - 10)
    await mob_ai.mob_ai_tick(priest)
    check(kin.hp > hp0, '...and a prayer left alone mends its kin')

    clear()
    tank, cler = hero('Tank'), hero('Cler', 'cleric')
    capt = foe('captain', roles=['guarded'], rank='elite')
    capt.fighting, capt.position = tank, 'fighting'
    tank.fighting = capt
    tank.hp = 300
    await SpellHandler.apply_spell(cler, tank, SPELLS['heal'], 'heal')
    capt.pending_intent = None
    wm.full = []
    await mob_ai.declare_intents(capt)
    it = capt.pending_intent
    check(it and it['kind'] == 'disrupt' and it.get('target') is cler, 'an elite turns a word of silence on the healer (Disrupt)')
    await asyncio.sleep(0.02)
    wind = [e for e in (wm.full or []) if e.get('k') == 'windup']
    check(wind and (wind[-1].get('dst') or {}).get('p') == 'Cler', f"...its wind-up marked on the healer ({wind[-1:]})")
    if it:
        it['declared_at'] = time.time() - 10
        await mob_ai.mob_ai_tick(capt)
        check('silenced' in (cler.affect_flags or set()), '...and left alone it silences them')

    # ---------------- the zone's real-time wind-up
    for tier, want in (('readable', 2.0), ('brutal', 1.4)):
        clear()
        ROOM.zone.ai = {'tier': tier}
        h, brute = hero('Hal'), foe('ogre', roles=['guarded'])
        fight(h, brute)
        brute.ai_state, brute.pending_intent = {}, None
        for _ in range(20):
            if brute.pending_intent:
                break
            await mob_ai.declare_intents(brute)
        check(brute.pending_intent and brute.pending_intent.get('windup_action') == want,
              f"in a {tier} zone a wind-up on the real-time clock takes {want} s ({brute.pending_intent and brute.pending_intent.get('windup_action')})")
    ROOM.zone.ai = None

    # ---------------- creatures learn a hold's school; another lands; they forget
    clear()
    m, target = hero('Mia', 'mage'), foe('troll', roles=['guarded'])
    fight(m, target)
    b = brain.of(target)
    b.rng.seed(1)
    for _ in range(4):
        await SpellHandler.apply_affect(target, {'type': 'sleep', 'value': 1}, 2, 'sleep', 30, caster=m, spell_key='sleep')
        SpellHandler._cleanse(target, {'sleeping'})
        target.position = 'fighting'
    seen = dict(b.encounter.get('cc_seen') or {})
    check(sum(seen.values()) >= 1, f'it remembers the school of the holds that landed ({seen})')
    b.profile['adapt_rate'] = 1.0                        # (certain, for the test)
    await SpellHandler.apply_affect(target, {'type': 'sleep', 'value': 1}, 2, 'sleep', 30, caster=m, spell_key='sleep')
    check('sleeping' not in (target.affect_flags or set()), 'a school it has seen is shrugged off...')
    await asyncio.sleep(0.02)
    check(any('knows that' in s for s in m.connection.lines), '...and it says so')
    await SpellHandler.apply_affect(target, {'type': 'entangled', 'value': 1}, 2, 'entangle', 30, caster=m, spell_key='entangle')
    check('entangled' in (target.affect_flags or set()), 'a hold of another school lands')
    SpellHandler._cleanse(target, {'entangled'})
    from combat import CombatHandler
    CombatHandler.stun(target, 1)
    got = CombatHandler.stun(target, 1)
    check(got == 'resist', f'a bash it has seen is shrugged off as well ({got})')
    target.fighting = None
    b.encounter['fought_at'] = time.time() - 60
    await brain.think_idle(target)
    check(not b.encounter.get('cc_seen'), 'when the fight is over it forgets the tricks')

    # ---------------- breakouts
    clear()
    a, bb = hero('Ari'), hero('Bo')
    bb.stunned_rounds = 3
    await CommandHandler.execute(a, 'rouse', ['bo'])
    check(bb.stunned_rounds == 0 and getattr(a, '_skip_autoattack', False), 'rouse shakes a stunned friend free, for your next swing')
    bb.stunned_rounds = 3
    a.connection.lines.clear()
    await CommandHandler.execute(a, 'rouse', ['bo'])
    check(bb.stunned_rounds == 3 and any('again in' in s for s in a.connection.lines), 'rouse cools down')
    await SpellHandler.apply_affect(bb, {'type': 'sleep', 'value': 1}, 2, 'sleep', 30)
    a.rouse_cooldown_until = 0
    await CommandHandler.execute(a, 'rouse', ['bo'])
    check('sleeping' not in (bb.affect_flags or set()) and bb.position != 'sleeping', '...and wakes a friend from a magical sleep')
    await SpellHandler.apply_affect(bb, {'type': 'entangled', 'value': 1}, 2, 'entangle', 30)
    await bb.take_damage(5, a, 'fire')
    check('entangled' not in (bb.affect_flags or set()), 'fire burns away the roots holding someone')
    await SpellHandler.apply_affect(bb, {'type': 'sleep', 'value': 1}, 2, 'sleep', 30)
    await bb.take_damage(5, a)
    check('sleeping' not in (bb.affect_flags or set()) and bb.position != 'sleeping', 'a blow wakes a sleeper')
    mez = foe('cultist', roles=['guarded'])
    await SpellHandler.apply_affect(mez, {'type': 'charmed', 'value': 1}, 2, 'charm', 30)
    await mez.take_damage(5, a)
    check('charmed' not in (mez.affect_flags or set()), "a blow breaks a creature's charm")

    # ---------------- once a fight, again next fight
    clear()
    h, wolf = hero('Wes'), foe('wolf', roles=['pack', 'boss'])
    fight(h, wolf)
    wb = brain.of(wolf)
    wolf.ai_state.update({'pack_called': True, 'buffed': True})
    await mob_ai._boss_enrage(wolf, h)
    hr = wolf.hitroll
    wolf.fighting = None
    wb.encounter['fought_at'] = time.time() - 60
    await brain.think_idle(wolf)
    check(not wolf.ai_state.get('pack_called') and not wolf.ai_state.get('enraged') and wolf.hitroll == hr - 5,
          'after the fight its pack call comes back and its enrage wears off')

    # ---------------- archers and supporters
    clear()
    for name, role in (('archer', 'archer'), ('minstrel', 'support')):
        m = foe(name)
        m.ai_state = {}
        check(role in mob_ai.classify_mob(m), f"a creature called '{name}' is read as {role} (it keeps its distance)")

    # ---------------- the switch
    brain.FORCED_OFF.add('tactics')
    try:
        clear()
        h, pri, k = hero('Ivo'), foe('priest', roles=['healer']), foe('raider')
        pri.fighting = k.fighting = h
        h.fighting = k
        k.hp = 1000
        await mob_ai.mob_ai_tick(pri)
        check(k.hp > 1000, 'tactics off: the old instant heal')
    finally:
        brain.FORCED_OFF.discard('tactics')

    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
