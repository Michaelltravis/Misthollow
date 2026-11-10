"""The regions of the world (src/regions.py, world/regions.json, docs/world/WORLD_SPINE.md), offline.

Every zone of the world is in exactly one region (but Limbo, the God Rooms and the marquee
creatures' list, which are not places); a zone's map tells /play its region.

    python3 tests/test_regions.py
"""
import asyncio
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'world'))
import test_webmove as tw  # noqa: E402

check, failures = tw.check, tw.failures


async def main():
    import logging
    logging.disable(logging.WARNING)
    import regions
    import regions_ledger as ledger
    check(not ledger.problems(ledger.zones()), 'every zone file is in exactly one region (tools/world/regions_ledger.py)')
    with open(regions.PATH, encoding='utf-8') as f:
        data = json.load(f)
    want = {r['id']: sorted(r['zones']) for r in data['regions']}
    check(want == {rid: sorted(v[3]) for rid, v in ledger.REGIONS.items()}, "world/regions.json is the ledger's own (run the ledger again after editing it)")
    regions.load()
    vale = regions.of(30)
    check(vale and vale['name'] == 'The Lantern Vale' and vale['line'] and vale['levels'] == [1, 10], f'the city is in the Lantern Vale ({vale})')
    check(regions.of(300)['id'] == 'reach', 'the Shattered Throne ends the Sundered Reach')
    check(regions.of(12) is None and regions.of(0) is None and regions.of('x') is None, 'the God Rooms and Limbo are in no region')

    # a broken file is no regions, not a crash
    bad = os.path.join(tempfile.mkdtemp(), 'regions.json')
    with open(bad, 'w', encoding='utf-8') as f:
        f.write('{"regions": [{"id": "a", "name": "A", "zones": [1, 2]}, {"name": "no id"}, {"id": "b", "name": "B", "zones": [2, "x", 3]}]}')
    got = regions.load(bad)
    check(sorted(got) == [1, 2, 3] and got[2]['id'] == 'a' and got[3]['id'] == 'b', 'a malformed region is skipped; a zone listed twice keeps its first')
    check(regions.load(os.path.join(tempfile.gettempdir(), 'no-such-regions.json')) == {}, 'no file: no regions')
    regions.load()

    from config import Config
    Config.PLAYER_DIR = tempfile.mkdtemp()
    from world import World
    import map_system
    world = World(Config())
    await world.load()
    zm = map_system.build_zonemap(world, world.rooms[3001].zone.number)
    check(zm.get('region') and zm['region']['id'] == 'vale', "the city's map says its region")
    zm12 = map_system.build_zonemap(world, 12)
    check(zm12 is None or zm12.get('region') is None, "the God Rooms' map says none")
    named = [z for z in world.zones.values() if regions.of(z.number)]
    check(len(named) >= 120, f'{len(named)} loaded zones have a region')

    # ---- the bells at dusk: heard in the Lantern Vale, and nowhere else
    temple, square = world.rooms[3001], world.rooms[3005]
    check(regions.bells_line(temple) == regions.BELLS_INDOORS, 'in the Temple the bells come through the walls')
    check(regions.bells_line(square) == regions.BELLS_OUTDOORS, 'in the square they ring across the Vale')
    far = next(r for r in world.rooms.values() if regions.of(r.zone.number) and regions.of(r.zone.number)['id'] == 'reach')
    check(regions.bells_line(far) is None and regions.bells_line(None) is None, 'the Sundered Reach is out of earshot')
    import test_atlas_engine as tae
    from player import Player
    def hero_at(name, room):
        h = Player.create_new(name=name, password=None, race='human', char_class='warrior',
                              stats={k: 13 for k in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
        h.connection = tae.Conn()
        h.room = room
        world.players[name.lower()] = h
        return h
    near, away = hero_at('Bellnear', square), hero_at('Bellfar', far)
    heard = await regions.dusk_bells(world)
    check(heard == 1 and 'bells' in tae.said(near, 1).lower() and 'bells' not in tae.said(away, 3).lower(), 'at dusk those in the Vale are told, the others are not')

    print('ALL OK' if not failures else f'{len(failures)} FAILED')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
