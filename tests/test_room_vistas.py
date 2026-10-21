"""What a room's words say lies beyond it (room_vistas.py): land across the water where the text
puts it, a shore at hand, mountains on the horizon; nothing where the text denies it.

    python3 tests/test_room_vistas.py
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import test_webmove as tw  # noqa: E402  (check(), failures)

check, failures = tw.check, tw.failures


async def main():
    logging.disable(logging.WARNING)
    from config import Config
    from world import World
    import room_vistas as rv
    world = World(Config())
    await world.load()
    V = lambda v: rv.vistas(world.rooms[v])     # noqa: E731
    has = lambda v, **want: any(all(x.get(k) == w for k, w in want.items()) for x in V(v))   # noqa: E731

    check(has(9540, kind='town', dir='south', near=False), f'"South lies the harbor to Timeless Island": a harbour to the south ({V(9540)})')
    check(has(9540, kind='cliffs', dir=None, near=True), f'"the channel between the two moles": stone at hand on its sides ({V(9540)})')
    check(has(9514, kind='island', dir='north', near=False), f'"sheltered by an island" to the north ({V(9514)})')
    check(has(13773, kind='coast', dir='east'), f'"A stony shore shows dimly to the east" ({V(13773)})')
    check(has(10704, kind='cliffs', dir=None, near=False), f'"Close beyond the bergs looms the black headland of Cape Voogk": cliffs, no side named ({V(10704)})')
    check(has(8809, kind='coast', near=True), f'"The shore is close at hand here": the Sea of Storms\' beach is at hand ({V(8809)})')
    check(V(13760) == [], f'"no shore shows anywhere": none ({V(13760)})')
    check(V(8840) == [], f'"blurring the horizon into grey nothing": none ({V(8840)})')
    check(V(5626) == [], f'"animals ... in the distance" is no land ({V(5626)})')
    check(rv.vistas_of_text('Thistles and docks have taken over the pasture.', water=False) == [], 'docks the weed are no harbour')
    check(rv.vistas_of_text('Fallen walls rise where roots have heaved the paving into ridges.', water=False) == [], 'ridges of paving are no hills')
    inside = next(r for r in world.rooms.values() if r.sector_type == 'inside' and 'mountain' in (r.description or '').lower())
    check(rv.vistas(inside) == [], f'a room indoors sees no horizon ({inside.vnum})')
    water = [r for r in world.rooms.values() if r.sector_type in ('water_swim', 'water_noswim')]
    n = sum(1 for r in water if rv.vistas(r))
    check(n > len(water) // 4, f'many open-water rooms show land somewhere ({n} of {len(water)})')
    from map_system import build_zonemap
    zm = build_zonemap(world, 120)
    row = next(r for r in zm['rooms'] if r['vnum'] == 8809)
    check(row.get('vista') == V(8809), 'the zone map sends each room its vistas')

    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
