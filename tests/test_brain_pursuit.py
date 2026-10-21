"""Awareness and pursuit (brain/, phase 2a), offline, on a clock the test turns:

    python3 tests/test_brain_pursuit.py

- who a creature attacks on sight: aggressive; aggr_evil only the evil; a `memory` that holds a
  grudge; never a no_attack creature, an immortal, or (in a city) someone far below it;
- what it sees: invisible only with detect invisibility or `aware`; a blind creature nothing;
  across an open way in the light, not in the dark at the same distance; never through a door;
- the way: a door opened by hands, unlocked with a key, pounded by a brute; never a door bound by
  magic, a barricade, a peaceful room, a room creatures keep out of, another zone, or (readable)
  into town;
- a boss notices who walks in, and resets (healed) when they leave; a sentinel never leaves;
- a brutal creature hears a fight next door and goes to look; a foe who flees is followed;
- MH_BRAIN_OFF=pursuit: the old rules (no brain moves).
(The chases themselves, leash and doors timed: tools/balance/scenarios.py pursuit.)
"""
import asyncio
import logging
import os
import sys
import time
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))


class Clock:
    t = 2.0e9

    def __call__(self):
        return self.t


CLOCK = Clock()
time.time = CLOCK                       # every module's time.time() reads the test's clock

import test_webmove as tw  # noqa: E402  (check(), failures)
from test_action_combat import Conn, FakeMap, put  # noqa: E402

check, failures = tw.check, tw.failures


async def main():
    logging.disable(logging.WARNING)
    from config import Config
    from world import World, Room, Zone
    from player import Player
    import combat_hooks
    import brain
    from brain import perception, path, pursuit
    from bosses import create_mob_from_prototype, Boss

    world = World(Config())
    await world.load()
    world.web_map = FakeMap()
    combat_hooks.install()
    brain.install()
    check(brain.on('pursuit'), 'features.pursuit is on (world/ai_profiles.json)')

    # a row of rooms of a zone of their own (and one room of another zone past the end)
    Z, ZB = 9980, 9981
    world.zones[Z], world.zones[ZB] = Zone(Z), Zone(ZB)
    rooms = []
    for i in range(6):
        r = Room(Z * 100 + i)
        r.zone = world.zones[Z if i < 5 else ZB]
        r.flags, r.sector_type = set(), 'inside'
        r.zone.rooms[r.vnum] = r
        world.rooms[r.vnum] = r
        rooms.append(r)
    for a, b in zip(rooms, rooms[1:]):
        a.exits['east'], b.exits['west'] = {'room': b}, {'room': a}

    def reset():
        for r in rooms:
            r.characters.clear()
            r.flags = set()
            r.sector_type = 'inside'
            for ex in r.exits.values():
                ex.pop('door', None)
        world.npcs[:] = []
        world.zones[Z].ai = None

    def hero(name, at=0, level=30, align=0):
        p = Player(world)
        p.name, p.char_class, p.level, p.alignment = name, 'warrior', level, align
        p.max_hp = p.hp = 900
        p.connection = Conn()
        p.world = world
        world.players[name.lower()] = p
        put(p, rooms[at])
        return p

    def creature(name='raider', at=0, flags=('aggressive',), level=30, race='human', vnum=3062, tier='readable'):
        world.zones[Z].ai = {'tier': tier}
        proto = dict(world.mob_prototypes[vnum])
        proto['level'] = level
        proto['flags'] = list(flags)
        m = create_mob_from_prototype(proto, world)
        m.name, m.race, m.home_zone = name, race, Z
        m.special = None
        put(m, rooms[at])
        world.npcs.append(m)
        m._brain = None
        return m

    async def tick(mobs, secs):
        for _ in range(int(secs * 10)):
            for m in mobs:
                await m.process_ai()
            await asyncio.sleep(0)
            CLOCK.t += 0.1

    # ---------------- hostile on sight
    reset()
    good, evil = hero('Goody', align=800), hero('Baddy', align=-800)
    m = creature(flags=('aggr_evil',))
    check(perception.hostile_to(m, evil) and not perception.hostile_to(m, good), 'aggr_evil attacks only the evil')
    m2 = creature(flags=('memory',))
    check(not perception.hostile_to(m2, good), 'a creature with a memory leaves a stranger alone...')
    m2.add_grudge(good, 10)
    check(perception.hostile_to(m2, good), '...and attacks on sight someone who hurt it')
    m3 = creature(flags=('aggressive', 'no_attack'))
    check(not perception.hostile_to(m3, good), 'a no_attack creature never attacks')
    good.nohassle = True
    check(not perception.hostile_to(creature(), good), 'nor anyone an immortal (nohassle)')
    good.nohassle = False
    rooms[0].sector_type = 'city'
    low = hero('Lowly', level=5)
    check(not perception.hostile_to(creature(level=30), low), 'in a city, never someone far below it')

    # ---------------- what it sees
    reset()
    h, m = hero('Vis'), creature()
    b = brain.of(m)
    h.affect_flags = {'invisible'}
    check(not perception.sees(m, b, h), 'an invisible player is unseen...')
    m.affect_flags = {'detect_invisible'}
    check(perception.sees(m, b, h), '...but by a creature that detects invisibility')
    m.affect_flags = {'blind'}
    h.affect_flags = set()
    check(not perception.sees(m, b, h), 'a blind creature sees nothing')
    m.affect_flags = set()
    reset()
    h, m = hero('Far', at=1), creature(at=0)
    b = brain.of(m)
    check(perception.look(m, b) == (h, True), 'across an open way it sees a player (telnet: about half a room)')
    rooms[1].flags.add('dark')
    check(perception.look(m, b) == (None, False), '...not in the dark at the same distance')
    rooms[1].flags.discard('dark')
    rooms[0].exits['east']['door'] = {'name': 'door', 'state': 'closed'}
    check(perception.look(m, b) == (None, False), '...nor through a closed door')

    # ---------------- the way
    reset()
    m, wolf, ogre = creature(), creature('wolf', race='wolf'), creature('ogre', race='giant')
    jailer = creature('jailer')
    jailer.inventory = [types.SimpleNamespace(vnum=77777, name='a key')]
    closed = {'name': 'door', 'state': 'closed'}
    locked = {'name': 'door', 'state': 'closed', 'locked': True, 'key': 77777}
    b, bw, bo, bj = (brain.of(x) for x in (m, wolf, ogre, jailer))
    check(path.door_cost(m, b, closed) == (path.OPEN_COST, 'open'), 'a creature with hands opens a door')
    check(path.door_cost(wolf, bw, closed) is None, 'a wolf can not')
    check(path.door_cost(ogre, bo, locked) == (path.BASH_COST, 'bash'), 'an ogre pounds a locked door down')
    check(path.door_cost(jailer, bj, locked) == (path.UNLOCK_COST, 'unlock'), 'a jailer with the key unlocks it')
    check(path.door_cost(m, b, locked) is None, 'a raider without the key can not')
    check(path.door_cost(ogre, bo, dict(locked, arcane=True)) is None, 'no one passes a door bound by magic')
    check(path.door_cost(ogre, bo, dict(closed, barricaded_until=CLOCK.t + 60)) is None, 'nor a barricade')
    rooms[2].flags.add('peaceful')
    check(path.route(m, b, rooms[0], rooms[3]) is None, 'never through a peaceful room')
    rooms[2].flags = {'no_mob'}
    check(path.route(m, b, rooms[0], rooms[3]) is None, 'nor a room creatures keep out of')
    rooms[2].flags = set()
    check(path.route(m, b, rooms[0], rooms[3]) == [('east', 'walk')] * 3, 'the open way: three steps east')
    check(path.route(m, b, rooms[4], rooms[5]) is None, 'never out of its home zone')
    rooms[3].sector_type = 'city'
    check(path.route(m, b, rooms[0], rooms[3]) is None, 'a readable zone\'s creature does not chase into town')
    rooms[3].sector_type = 'inside'

    # ---------------- a boss notices who walks in, and resets when they leave
    reset()
    boss = None
    for vnum, proto in world.mob_prototypes.items():
        if isinstance(proto, dict) and 'boss' in (proto.get('flags') or []) and proto.get('boss_config'):
            p = dict(proto)
            p['flags'] = list(set(p['flags']) | {'aggressive'})
            cand = create_mob_from_prototype(p, world)
            if isinstance(cand, Boss):
                boss = cand
                break
    if boss is None:
        check(False, 'found a boss to test')
    else:
        boss.home_zone = Z
        put(boss, rooms[0])
        world.npcs.append(boss)
        h = hero('Brave', at=0, level=boss.level)
        await tick([boss], 3)
        check(boss.fighting is h, f'an aggressive boss attacks who walks into its room (mode {brain.of(boss).mode})')
        boss.hp = boss.max_hp // 2
        bb = brain.of(boss)
        bb.last_target, bb.encounter['fought_at'] = h, CLOCK.t        # (a round of the fight was fought)
        put(h, rooms[1])
        boss.fighting, h.fighting = None, None
        boss.position = 'standing'
        await tick([boss], 10)
        check(boss.room is rooms[0] and boss.hp == boss.max_hp, 'they leave: it stays at its post, and resets healed')

    # ---------------- a sentinel never leaves; a brutal creature hears a fight; a fleeing foe
    reset()
    h, s = hero('Seen', at=1), creature('guard', flags=('aggressive', 'sentinel'))
    await tick([s], 4)
    check(s.room is rooms[0] and s.fighting is None, 'a sentinel sees across the way but never leaves its post')
    reset()
    a, b2 = hero('Ann', at=2), hero('Bob', at=2)
    foe = creature('brawler', at=2, flags=())
    a.fighting, foe.fighting = foe, a
    lis = creature('listener', at=1, flags=('aggressive',), tier='brutal')
    rooms[1].exits['east']['door'] = {'name': 'door', 'state': 'closed'}        # (it can't see them)
    rooms[2].exits['west']['door'] = {'name': 'door', 'state': 'closed'}
    await tick([lis], 6)
    check(lis.room is rooms[2] or brain.of(lis).mode in ('investigate', 'alert') or lis.fighting is not None,
          f'a brutal creature hears the fight next door and goes to look (mode {brain.of(lis).mode})')
    reset()
    runner, chaser = hero('Run', at=0), creature('chaser', at=0, flags=())
    cb = brain.of(chaser)
    chaser.fighting, runner.fighting = runner, chaser
    cb.last_target, cb.encounter['fought_at'] = runner, CLOCK.t
    put(runner, rooms[1])
    chaser.fighting, runner.fighting = None, None
    await tick([chaser], 4)
    check(chaser.room is rooms[1] or chaser.fighting is runner, f'a foe who leaves the fight is followed (mode {cb.mode})')

    # ---------------- the switch
    brain.FORCED_OFF.add('pursuit')
    try:
        reset()
        h, m = hero('Off', at=1), creature()
        await tick([m], 4)
        check(m.room is rooms[0] and brain.of(m).mode == 'idle', 'pursuit off: no brain moves (the old rules)')
    finally:
        brain.FORCED_OFF.discard('pursuit')

    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
