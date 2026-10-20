"""Every room looks like what it says it is (Push 33), offline: the world check.

    python3 tests/test_room_looks.py

A room whose name says cave, mine, crypt, sewer, desert, snow, shore or volcanic draws as one,
unless world/looks.json pins it otherwise; a look a zone or the build-out states for a room never
contradicts the room's own name; every override names a real room or zone and a known look.
"""
import asyncio
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
import test_webmove as tw  # noqa: E402

check, failures = tw.check, tw.failures


async def main():
    import logging
    logging.disable(logging.WARNING)
    from config import Config
    from world import World
    import room_looks as rl
    world = World(Config())
    await world.load()
    rooms = world.rooms
    ov = rl.load_overrides()

    # ---- what a room's name says, it looks like
    wrong = []
    for r in rooms.values():
        own, why = rl._own_look(r)
        # (a cave whose words fill it with ice or lava is still the cave its name says)
        refined = own == 'cave' and r.look in ('ice_cave', 'lava_cave')
        if own and why == 'name' and r.look != own and r.look_why != 'stated' and not refined:
            wrong.append((r.vnum, r.name, r.look))
    check(not wrong, f'every room looks like what its name says ({len(wrong)} do not: {wrong[:4]})')

    # ---- a stated look never contradicts the room's own name (the build-out writes one per room)
    raw = json.load(open(rl.OVERRIDES, encoding='utf-8'))
    pinned = {int(k) for k in (raw.get('_why') or {}) if str(k).isdigit()}
    clash = []
    for r in rooms.values():
        said = getattr(r, 'stated_look', None)
        named = rl.words_look(r.name)
        if said and named and named != said and r.vnum not in pinned:
            clash.append((r.vnum, r.name, said, named))
    check(not clash, f"a room's stated look agrees with its name ({clash[:4]})")

    # ---- the overrides file
    zones = {getattr(getattr(r, 'zone', None), 'number', None) for r in rooms.values()}
    bad = [(k, v) for k, v in ov['rooms'].items() if k not in rooms or v not in rl.OVERRIDE_LOOKS]
    bad += [(k, v) for k, v in ov['zones'].items() if k not in zones or v not in rl.LOOKS]
    check(not bad, f'every override names a real room or zone and a known look ({bad[:4]})')
    why = raw.get('_why') or {}
    check(all(str(k) in why for k in list(ov['rooms']) + list(ov['zones'])), 'and says why')

    # ---- known places
    def look_of(name, n=0):
        found = [r for r in rooms.values() if r.name == name]
        return found[n].look if len(found) > n else None
    check(rooms[4469].look == 'cave', 'The Large Cave is a cave')
    check(look_of('The Low Crawlway') == 'cave', 'a crawlway under Moria is a cave')
    check(rooms[7001].look == 'sewer', 'The Muddy Sewer is a sewer (once typed mountain)')
    check(rooms[5300].look == 'desert', 'The Great Eastern Desert is desert (once typed field)')
    check(look_of('The Castle Yard') not in rl.UNDERGROUND, "a castle's yard is not underground")
    check(look_of('Deeper and Deeper') == 'cave', "the Pale Man's caverns are caves throughout")
    # dead Morkai (owner: "end game area and themed dark, undead, skeletons, aberrations")
    check(rooms[13832].look == 'necropolis' and rooms[13841].look == 'crypt', "Morkai's streets are a dead city, its halls crypts")
    taverns = [r for r in rooms.values() if r.sector_type == 'inside' and 'tavern' in r.name.lower()
               and not r.name.lower().startswith(('below', 'under', 'beneath'))]   # a mine under a tavern is a mine
    check(taverns and all(r.look not in rl.UNDERGROUND for r in taverns), 'no tavern turns into a cave')
    # (unless its own description is plainly a building's: Townsbridge's alehouse and chapel)
    plains = [r for r in rooms.values() if r.name == 'The Plains' and not rl.reads_indoors(r.description)]
    check(plains and all(r.look not in ('inside', 'dungeon') for r in plains), 'no room called The Plains is drawn as a building')
    # the room audit's cases (tools/qc_room_looks.py)
    check(rooms[8151].look == 'inside', 'the village alehouse called The Plains is a building')
    check(rooms[4105].look == 'cave' and rooms[4066].look == 'cave', "the Mountain Range's Golden Cave and Maze are caves")
    check(rooms[14648].look == 'web' and rooms[6132].look == 'web', 'webbed woods are spider lairs')
    check(rooms[16126].look == 'forest', 'the edge of a Forrest is a forest')
    check(rooms[8387].look == 'inside', "a castle's guest room with a bed is a room, not a cave")
    indoor_country = [(r.vnum, r.name) for r in rooms.values() if r.look == 'inside' and rl.open_country(r)]
    check(not indoor_country, f'no room named as open country is drawn indoors ({indoor_country[:4]})')
    mtn = [(r.vnum, r.name, r.look) for r in rooms.values() if r.sector_type in ('field', 'hills', 'forest')
           and rl.MOUNTAIN_RE.search(r.name or '') and not rl.FOREST_RE.search(r.name or '') and r.look in ('field', 'hills', 'forest')]
    check(not mtn, f'no room named as mountain country is drawn as field, hills or forest ({mtn[:4]})')
    water = [r for r in rooms.values() if r.sector_type in rl.WATER_SECTORS]
    check(all(r.look == r.sector_type for r in water), 'water stays water')

    # the Sewer is underground throughout (owner: "sewers should look like a sewer"): no pipe
    # junction drawn as a town street, no ledge as a mountain, no lair as a field
    sewer = [r for r in rooms.values() if getattr(getattr(r, 'zone', None), 'number', None) == 72]
    above = [(r.vnum, r.name, r.look) for r in sewer if r.look not in rl.UNDERGROUND and r.look not in rl.WATER_SECTORS]
    check(sewer and not above, f'every room of the Sewer is underground or water ({above[:4]})')
    check(rooms[7016].look == 'sewer' and rooms[7337].look == 'cave', 'a pipe bend is a sewer, the Basilisk\'s Cave a cave')
    # the Drow City is drow throughout (owner: "the drow city doesn't look like a drow city"): its
    # streets, houses, tunnels and bridges all drawn by the drow look (terrain-drow.js)
    drow = [r for r in rooms.values() if getattr(getattr(r, 'zone', None), 'number', None) == 51]
    other = [(r.vnum, r.name, r.look) for r in drow if r.look != 'drow']
    check(drow and not other, f'every room of the Drow City has the drow look ({other[:4]})')
    # the art audit (tools/jev_audit.py zones): the Clockwork Foundry is steel and furnaces, not a
    # cave; a castle's, a tower's, a temple's indoor rooms are drawn in its style (zone_tone.py sends
    # it as tone.interior); a castle's halls are not made caves by the caves under it
    zn = lambda r: getattr(getattr(r, 'zone', None), 'number', None)
    foundry = [(r.vnum, r.name, r.look) for r in rooms.values() if zn(r) == 248 and r.look != 'foundry']
    check(not foundry, f'every room of the Clockwork Foundry has the foundry look ({foundry[:4]})')
    styled = {z: st for z, st in ov['interiors'].items()}
    unstyled = [(r.vnum, r.name) for r in rooms.values() if zn(r) in styled and (r.tone or {}).get('interior') != styled[zn(r)]]
    check(styled and not unstyled, f'the rooms of every styled zone carry its interior style ({unstyled[:3]})')
    check(rooms[15039].tone['interior'] == 'castle' and rooms[2571].tone['interior'] == 'arcane',
          "Welmar's guest suite is a castle's, the High Tower's office a wizard's")
    check(rooms[8371].look == 'inside' and rooms[2702].look == 'inside', "Ostragoth's and Caboon's hallways are castle halls, not caves")
    check(rooms[3943].look == 'ice_cave' and rooms[2901].look == 'castle', 'the Winterlands cavern of ice pillars is an ice cave, the city wall a rampart')
    check(all(rooms[v].tone and rooms[v].tone.get('stone') == 'red' for v in (9919, 9944)), 'Ghenna is red stone under firelight')
    # filler the look contradicts is gone ("Bird calls echo through the canopy." down a sewer pipe)
    wrong = [(r.vnum, line) for r in rooms.values() for kind, lines in rl.FILLER.items() if r.look not in rl.FILLER_FITS[kind]
             for line in lines if line in rl._norm(r.description)]
    check(not wrong, f'no room keeps filler its look contradicts ({wrong[:3]})')
    check('canopy' not in rooms[7313].description and 'water' in rooms[7313].description.lower(),
          'the Spongy Room in the sewers lost its birdsong and gained its own dank lines')

    # ---- the payloads carry it
    from map_system import build_zonemap
    zm = build_zonemap(world, rooms[4469].zone.number)
    check(any(r['vnum'] == 4469 and r.get('look') == 'cave' for r in zm['rooms']), 'the zone map sends each room its look')

    s = rl.summary(world)
    print('looks:', dict(s['looks'].most_common()))
    print('why:', dict(s['why']))
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
