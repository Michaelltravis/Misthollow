"""The brain in the real game, offline (phase 0: it runs the old rules, with itself in place):

    python3 tests/test_brain_hooks.py

- every way a creature thinks goes through its brain (process_ai, declare_intents, mob_ai_tick),
  and combat_hooks' wrappers stay in the chain: a wind-up still sends its windup event, and
  lands with a resolve;
- MH_BRAIN off (brain.ENABLED): the same rules, no brain made;
- world.process_npcs: the old cadence (by a player every tick, elsewhere one in ten) and its timing;
- a population file's "ai": a zone's tier, a creature's own roles;
- the creatures that had an ai_config (ai.py, gone) load and think without it;
- the immortal "brain" command.
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
    import population
    import brain
    from brain import scheduler
    from bosses import create_mob_from_prototype

    world = World(Config())
    await world.load()
    wm = FakeMap()
    world.web_map = wm
    combat_hooks.install()
    brain.install()
    random.seed(7)
    ROOM = world.rooms[3054] if 3054 in world.rooms else world.rooms[3001]

    def hero(name, level=30):
        p = Player(world)
        p.name, p.char_class, p.level = name, 'warrior', level
        p.max_hp = p.hp = 900
        p.connection = Conn()
        p.world = world
        world.players[name.lower()] = p
        put(p, ROOM)
        cr.set_pos(p, 12, 7)
        return p

    def foe(vnum=3062, hp=5000, room=ROOM):
        mob = create_mob_from_prototype(world.mob_prototypes[vnum], world)
        mob.max_hp = mob.hp = hp
        put(mob, room)
        world.npcs.append(mob)
        cr.set_pos(mob, 13, 7)
        return mob

    def fight(a, b):
        a.fighting, b.fighting = b, a
        a.position = b.position = 'fighting'

    # ---------------- the hooks: combat_hooks still wraps what the brain calls
    check(mob_ai.declare_intents.__module__ == 'combat_hooks' and mob_ai._resolve_intent.__module__ == 'combat_hooks',
          'combat_hooks wraps declare_intents and _resolve_intent, as before')
    ace, brute = hero('Ace'), foe()
    fight(ace, brute)
    brute.ai_state, brute.level, brute.pending_intent = {}, ace.level + 2, None
    wm.full = []
    for _ in range(12):
        if brute.pending_intent:
            break
        await mob_ai.declare_intents(brute)
    await asyncio.sleep(0.02)
    check(getattr(brute, '_brain', None) is not None, 'declaring a special makes the creature its brain')
    wind = [e for e in wm.full if e.get('k') == 'windup']
    check(brute.pending_intent is not None and wind, f'a wind-up through the brain still sends its windup event ({len(wind)})')
    if brute.pending_intent:
        brute.pending_intent['declared_at'] = time.time() - mob_ai.INTENT_WINDUP - 0.1
        await mob_ai.mob_ai_tick(brute)
        await asyncio.sleep(0.02)
        check(brute.pending_intent is None and any(e.get('k') == 'resolve' for e in wm.full),
              '...and the round lands it with a resolve event (through the wrapped _resolve_intent)')

    # ---------------- the kill switch
    brain.ENABLED = False
    try:
        bea, ogre = hero('Bea'), foe()
        fight(bea, ogre)
        ogre.ai_state, ogre.level, ogre.pending_intent = {}, bea.level + 2, None
        for _ in range(12):
            if ogre.pending_intent:
                break
            await mob_ai.declare_intents(ogre)
        check(getattr(ogre, '_brain', None) is None and ogre.pending_intent is not None,
              'MH_BRAIN off: the old rules wind up a special just the same, no brain made')
        await ogre.process_ai()
        check(getattr(ogre, '_brain', None) is None, '...and out of the fight no brain either')
    finally:
        brain.ENABLED = True
    for ch in (bea, ogre):
        ch.fighting, ch.position = None, 'standing'

    # ---------------- out of a fight: process_ai goes through the brain to the old rules
    calm = foe()
    calm.fighting = None
    calls = []
    real_idle = type(calm).legacy_idle_ai

    async def counted(self):
        calls.append(self)
        return await real_idle(self)
    type(calm).legacy_idle_ai = counted
    try:
        await calm.process_ai()
    finally:
        type(calm).legacy_idle_ai = real_idle
    check(calls == [calm] and getattr(calm, '_brain', None) is not None,
          'process_ai: the brain runs the old rules (legacy_idle_ai) out of a fight')

    # ---------------- the scheduler: the old cadence, and its timing
    seen = {}
    far_zone = next(z for z in world.zones.values() if z.rooms and z.number != ROOM.zone.number
                    and all(getattr(getattr(r2.get('room') if isinstance(r2, dict) else None, 'zone', None), 'number', None)
                            != z.number for r2 in (ROOM.exits or {}).values()))
    far_room = next(iter(far_zone.rooms.values()))
    near, far = foe(), foe(room=far_room)
    for m in (near, far):
        m.fighting = None
    world.npcs[:] = [near, far]

    async def count_near():
        seen['near'] = seen.get('near', 0) + 1

    async def count_far():
        seen['far'] = seen.get('far', 0) + 1
    near.process_ai, far.process_ai = count_near, count_far
    scheduler.STATS.reset()
    for _ in range(world.NPC_SLEEP_EVERY):
        await world.process_npcs()
    del near.process_ai, far.process_ai
    check(seen == {'near': world.NPC_SLEEP_EVERY, 'far': 1},
          f'by a player a creature thinks every tick, elsewhere one in ten ({seen})')
    check(scheduler.STATS.ticks == world.NPC_SLEEP_EVERY and scheduler.STATS.thought == world.NPC_SLEEP_EVERY + 1,
          f'brainstat counts the ticks and the creatures that thought ({scheduler.STATS.ticks}, {scheduler.STATS.thought})')

    # ---------------- a population file's "ai": a zone's tier, a creature's roles
    zn = ROOM.zone.number
    population.apply(world, {zn: {'zone': zn, 'ai': {'tier': 'brutal'}}})
    tough = foe()
    check(brain.of(tough).profile['tier'] == 'brutal', "a population file's zone tier reaches its creatures' brains")
    ROOM.zone.ai = None
    vnum = 3062
    proto = dict(world.mob_prototypes[vnum])
    proto['ai'] = {'roles': ['caster'], 'profile': {'leash_rooms': 1}}
    mage = create_mob_from_prototype(proto, world)
    put(mage, ROOM)
    check(mob_ai.classify_mob(mage) == {'caster'}, "a creature's own roles replace the ones read from its name")
    b = brain.of(mage)
    check(b.roles == {'caster'} and b.profile.get('keep_range') is True and b.profile['leash_rooms'] == 1,
          "...and its brain takes the role's template and its own numbers")

    # ---------------- the creatures ai.py used to own
    for v in (3200, 3202, 26000):
        if v not in world.mob_prototypes:
            continue
        m = create_mob_from_prototype(world.mob_prototypes[v], world)
        put(m, ROOM)
        ok = not hasattr(m, 'ai_controller') and m.ai_config.get('greet_message')
        try:
            for _ in range(20):
                await m.process_ai()
        except Exception as e:
            ok = False
            print(f'     {v}: {e!r}')
        check(ok and m.room is ROOM, f'creature {v} (it had an ai_config) keeps its greeting, thinks without ai.py, stays put')

    # ---------------- the immortal "brain" command
    from commands import CommandHandler
    imm = hero('Imm')
    type(imm).is_immortal = property(lambda self: True)
    try:
        imm.connection.lines.clear()
        await CommandHandler.cmd_brain(imm, [mage.name.split()[-1]])
        said = '\n'.join(imm.connection.lines)
        check('tier' in said and 'roles' in said and 'threat' in said, f'"brain <creature>" shows its tier, roles and threat ({said[:80]!r})')
        imm.connection.lines.clear()
        await CommandHandler.cmd_brainstat(imm, [])
        check(any('ms a tick' in s for s in imm.connection.lines), '"brainstat" shows the time a tick takes')
    finally:
        del type(imm).is_immortal

    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
