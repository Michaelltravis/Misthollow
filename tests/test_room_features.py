#!/usr/bin/env python3
"""What a room's words say stands in it (room_features.py), and the Stone Circle's own look:

- A Sharp Bend In The Stone Circle [24641]: two standing stones, its centrepiece, one with a red
  collar; the holes of old stakes, not a stake;
- a place named as where a way leads ("a track leads east to the Third Altar") is not here;
- a colour is read beside its own noun, in its own sentence;
- said in the plural, more than one ("braziers smoulder at every corner");
- an altar "like a low table" is not a table as well;
- every room has its features at load, and the zone map sends them;
- the Stone Circle of the Raven Clans (zone 476) draws as standing stones on open turf, and its
  ambient lines are outdoor ones, not "warm light fills the interior spaces";
- every feature the reader can name, the client can place and draw.

    python3 tests/test_room_features.py
"""
import asyncio
import logging
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
ROOT = os.path.join(HERE, '..')

FAILED = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok:
        FAILED.append(what)


def by_key(fs):
    return {f['k']: f for f in fs}


async def main():
    logging.disable(logging.WARNING)
    import room_features as rf

    # ---- the reader
    f = by_key(rf.features('A Sharp Bend In The Stone Circle',
                           'The circle makes a sharp turn at a stone wrapped in a collar of red-dyed wool. A narrow track '
                           'leads east to the Third Altar Of The Stones, and the ring runs back north. The ground is pocked '
                           'with the holes of old stakes, and an iron smell lingers in the air.'))
    st = f.get('standing_stone', {})
    check(st.get('main') and st.get('c') == 'red' and st.get('n', 0) >= 1, f'24641: standing stones, its centrepiece, one with a red collar ({st})')
    check('altar' not in f, 'the altar the track leads to is not in this room')
    check('stake_holes' in f and 'stake' not in f, 'the holes of old stakes, not a stake')
    f = by_key(rf.features('The Temple', 'A great altar of slab stone stands before a wall painted with a huge red eye. '
                                         'Braziers smoulder at every corner.'))
    check(f.get('brazier', {}).get('n', 0) >= 2, 'braziers, said in the plural, are more than one')
    check('c' not in f.get('altar', {}), 'the red of the painted eye is not the altar\'s')
    f = by_key(rf.features('The Slaughter Stone', 'A broad flat stone like a low table of rough rock, stained black.'))
    check('altar' in f and f['altar'].get('main') and 'table' not in f, 'an altar like a table is an altar only, and the room\'s centrepiece')
    f = by_key(rf.features('A Hall', 'Black banners hang from the walls; a red rug lies before the throne.'))
    check(f.get('banner', {}).get('c') == 'black' and f.get('rug', {}).get('c') == 'red', f"each colour goes with its own noun ({f.get('banner')}, {f.get('rug')})")
    check(rf.features('A Field', 'Grass waves in the wind.') == [], 'a plain room names nothing')
    check(not by_key(rf.features('The Stone Floor', 'The stone floor is cold. A stone bridge crosses the stream.')).get('standing_stone'),
          'a stone floor or a stone bridge is not a standing stone')

    # ---- the art audit's bare rooms: the scenery the words name, and the words that only seem to
    keys = lambda n, d: {f['k'] for f in rf.features(n, d)}
    check('well' in keys('Northern Square', 'A pump with an iron handle stands in the middle.'), 'a town pump is drawn as a well')
    check('pillar' in keys('A Street', 'The avenue runs east between empty colonnades.'), 'a colonnade is pillars')
    check('bones' in keys('A Bay', 'the bleached ribs of a whale stand upright in the shingle'), "a whale's ribs are bones")
    check({'bed', 'grave'}.isdisjoint(keys('The River', 'The water runs clear over a bed of gravel.')), 'a bed of gravel is neither a bed nor a grave')
    check('roots' not in keys('An Alcove', 'A bowl of white sand holds a few burnt-down incense sticks.'), 'incense sticks are not roots')
    check('gate' in keys('Before The Gates', 'Before you rises the gate of Burzuk, a wall of black timber.'), 'a gate that rises is drawn')
    check('gate' not in keys('A Hall', 'The hall continues north, and the gate lies south.'), 'a gate named as where a way goes is not')
    check({'mist', 'reeds', 'boat', 'bell', 'mirror', 'waterfall', 'tree', 'ice', 'flames'} <= set().union(*(keys('x', d) for d in [
        'Mist curls low over the ground.', 'Reeds crowd the bank.', 'A rowboat is beached on the shingle.', 'The great bell hangs silent.',
        'Mirrors line the walls.', 'A waterfall cascades down the cliff.', 'A line of fruit trees runs along the wall.',
        'Icicles hang from the roof.', 'Ancient fires burn in the hollow.'])), 'the scenery words are read')

    # ---- the client knows every feature the reader names
    gen = open(os.path.join(ROOT, 'src/web_isometric/shared/roomgen.js'), encoding='utf-8').read()
    draw = open(os.path.join(ROOT, 'src/web_isometric/world3d/terrain-features.js'), encoding='utf-8').read()
    keys = [k for k, *_ in rf.FEATURES]
    check(all(re.search(rf'\b{k}:\s*\[', gen) for k in keys), f'roomgen places every feature ({[k for k in keys if not re.search(rf"{k}:", gen)]})')
    check(all(f"'{k}'" in draw for k in keys), f"the client draws every feature ({[k for k in keys if repr(k) not in draw]})")

    # ---- the world
    from config import Config
    from world import World
    import map_system
    import atmosphere
    world = World(Config())
    await world.load()
    r = world.rooms.get(24641)
    check(r is not None and r.look == 'stones', f'24641 draws as a stone circle ({getattr(r, "look", None)})')
    check(r is not None and any(f['k'] == 'standing_stone' and f.get('c') == 'red' for f in r.features), 'its features are read at load')
    zone476 = [x for x in world.rooms.values() if getattr(x, 'zone', None) == 476 or 24600 <= x.vnum < 24700]
    stones = sum(x.look == 'stones' for x in zone476)
    check(stones >= len(zone476) * 0.5, f'most of the Stone Circle draws as one ({stones} of {len(zone476)})')
    named = sum(bool(x.features) for x in world.rooms.values())
    check(named >= len(world.rooms) * 0.3, f'many rooms name what stands in them ({named} of {len(world.rooms)})')
    zm = map_system.build_zonemap(world, r.zone.number) or {}
    rooms = zm.get('rooms') or []
    entry = (rooms.get(24641) or rooms.get('24641')) if isinstance(rooms, dict) else next((e for e in rooms if e.get('vnum') == 24641), None)
    check(bool(entry) and entry.get('features') == r.features, 'the zone map sends them')
    lines = set()
    for _ in range(80):
        line = atmosphere.AtmosphereManager.get_atmosphere(r)
        if line:
            lines.add(line)
    check(not any('interior' in l.lower() for l in lines), f'its ambient lines are outdoor ones ({sorted(lines)[:2]})')

    print(f"\n{'ALL OK' if not FAILED else f'{len(FAILED)} FAILED'}")
    sys.exit(1 if FAILED else 0)


if __name__ == '__main__':
    asyncio.run(main())
