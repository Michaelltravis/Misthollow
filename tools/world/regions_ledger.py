#!/usr/bin/env python3
"""The world's regions (world/regions.json) and the zone ledger in docs/world/WORLD_SPINE.md.

The spine (docs/world/WORLD_SPINE.md) names nine regions and gives every zone a place in one. This
script holds that assignment, writes it as data for the game (world/regions.json: each region's
name, its line, its level band and its zones) and prints the ledger table the document carries:
what each zone is now (rooms, the median level of its creatures) and what the spine asks of it.

    python3 tools/world/regions_ledger.py            # writes world/regions.json, prints the ledger
    python3 tools/world/regions_ledger.py --check    # fails if a zone has no region, or two
"""
import glob
import json
import os
import re
import statistics
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')

# id: (name, the line a player reads on entering, (low, high) levels, [zones])
REGIONS = {
    'vale': ('The Lantern Vale', 'Where the lanterns still hold the mist back.', (1, 10),
             [30, 403, 431, 517, 260, 418, 186, 36, 200, 441, 60, 62, 72, 488, 79, 32]),
    'marches': ('The Marches', 'The road, and the keeps that were raised to guard it.', (8, 20),
                [408, 423, 150, 424, 458, 416, 480, 482, 414, 419, 499, 25, 469, 471, 502, 470, 461, 518, 479]),
    'greenreach': ('The Greenreach', 'Old forest. It was here before the names were.', (10, 25),
                   [435, 436, 439, 445, 447, 63, 61, 110, 504, 51, 270, 442, 519, 520]),
    'stonemarch': ('The Stonemarch', 'The mountains, and the halls the dwarves dug too deep to keep.', (12, 30),
                   [40, 33, 64, 90, 464, 465, 467, 65, 100, 472, 476, 478, 474, 235]),
    'frostmarch': ('The Frostmarch', 'The north, where the mist freezes and does not lift.', (20, 35),
                   [66, 180, 190, 521, 522]),
    'sundersea': ('The Sunder Sea', 'The lake that was the Hollow ran out to here, and took the coast with it.', (5, 30),
                  [50, 426, 54, 52, 53, 120, 9, 494, 496, 495, 491, 448, 449, 451, 452, 453, 454, 415, 455, 130, 15]),
    'deeproad': ('The Deep Road', 'The long way under the world, from the lost dwarf-holds to the city of the dead.', (35, 55),
                 [501, 503, 508, 509, 505, 507, 512, 515, 514]),
    'reach': ('The Sundered Reach', 'East, toward the Throne. Every mile of it was a kingdom once.', (25, 70),
              [67, 238, 68, 240, 69, 245, 248, 280, 285, 290, 295, 300]),
    'beyond': ('The Places Beyond', 'Not on any road: reached by a door, a death or a bargain.', (30, 70),
               [481, 475, 160, 80, 140, 457, 220, 210, 250, 429, 420, 73]),
}
# zones that are not places in the world
OUTSIDE = {0: 'Limbo (internal)', 12: 'God Rooms (immortals)', 97: 'Marquee quest creatures (a holding list)'}

# What the spine asks of a zone, where it asks anything: a new name (builder's suffixes and names
# taken from other people's books go), a level band to move to, or a note.
ASK = {
    186: 'rename: **The Proving Halls** (under the Temple); rewrite its joke rooms in the world\'s voice',
    36: 'keep: the city\'s own oddity',
    72: 'rename: **The Undercity**; levels 5-12 near the grates, the deep end stays for 25+',
    408: 'rename: **The Lantern Road**; a lantern post every few rooms, lit near the city, dark further out',
    423: 'rename: **Hollowmere** (was Hommlet, a published village); people it: the first village on the road',
    480: 'rename: **Saltmarsh Lot** or the owner\'s choice (was Salem\'s Lot, a published town)',
    25: 'rename with 469: **The High Tower** (lower halls / upper halls)',
    469: 'merge into The High Tower as its upper halls; people it (no creatures of its own)',
    471: 'rename: **The Badlands** (drop the II)',
    470: 'keep: Ostragoth, the Marches\' great villain (docs/world/ostragoth.md)',
    479: 'people it (no creatures of its own), or fold into the Lantern Road',
    482: 'people it (no creatures of its own)',
    435: 'rename: **The Minar Wood** (drop the I)',
    439: 'rename: **The White Mount** (was Mount Olympus); keep its white marble tone',
    504: 'rename: **Elvenhame** or the owner\'s choice (was Elvandar, a published elven city)',
    51: 'rename: **The Umbral City**; its goddess renamed (Lloth and the drow are a published setting\'s)',
    61: 'fold into Arachnos (5 rooms) as its way in',
    442: 'people it (102 rooms, no creatures of its own): the Greenreach\'s outlaw hold',
    519: 'levels 25-32: the Greenreach\'s capstone, with the Warded Castle',
    464: 'keep',
    465: 'rename: **Below the Deeping** (was Below Moria)',
    467: 'rename: **The Deeping Dark** (was Moria Deep)',
    66: 'raise to 20-26: the gate of the Frostmarch',
    180: 'raise to 22-28',
    521: 'raise to 24-30',
    522: 'raise to 28-34',
    190: 'raise to 32-38: the Frostmarch\'s end, the Frost Wyrm',
    448: 'rename with 451: **The Mirrormere** (shallows / deeps); keep as the first water, levels 3-8',
    451: 'merge name into The Mirrormere (deeps), levels 8-14',
    455: 'rename: **Beacon Isle** (was Gondor Island)',
    494: 'rename: **The Garden Isle** (was Eden)',
    496: 'rename: **The Becalmed Isle** (was Isle of Lag, a builder\'s joke)',
    461: 'rename: **The Nameless Tombs** (was Tombs of Atuan, a published place)',
    52: 'keep the name with New Thalos: the old city the sea took, the new one that replaced it',
    130: 'the Hollow\'s own story lives here: Nerathis, the Drowned King, kept his name by drowning with it',
    15: 'keep: the pilgrim\'s road to New Thalos',
    503: 'rename with 508: **Durmandel** (the city / the keep)',
    508: 'merge name into Durmandel',
    509: 'rename: **The Durmandel Mines**',
    505: 'rename with 507: **The Lost Crypt** (upper / lower)',
    507: 'merge name into The Lost Crypt',
    501: 'rename: **Aredrel** (a dwarf-hold; "Aredrel Dwarven" is a builder\'s label)',
    67: 'the gate of the Reach, levels 25-30: every hero is sent here from the city at 25',
    238: 'levels 27-33',
    68: 'levels 33-40',
    240: 'levels 40-46',
    69: 'levels 45-50',
    457: 'rename with 220: **The Castle of the Apocalypse** (the gatehouse / the keep); people the gatehouse',
    220: 'merge name into The Castle of the Apocalypse; the world\'s raid, level 60+',
    210: 'the castle\'s approach; say so at its mouth',
    481: 'people it (86 rooms, no creatures of its own): a hell, reached by dying badly',
    475: 'people it (90 rooms, no creatures of its own), or fold into the Plane of Eternal Chaos',
    140: 'move its way in: a level-31 necropolis two steps from the Temple, through the Undercity\'s deep end only',
    80: 'move its way in: a level-35 dragon two steps from the city; reach it from the Ashlands',
    420: 'people it or cut it (44 rooms, no creatures, a builder\'s hall of fame)',
    429: 'keep: the city before the city, levels 15-25',
    431: 'people it: priests, pilgrims, the bell-ringers (the bells that "call the lost home")',
    403: 'keep: the watch on the wall looks out at the mist',
    517: 'keep: no fights; where a newcomer learns what the lanterns are for',
    60: 'levels 3-10: the first open country; the Goblin King its boss',
    62: 'levels 5-12',
    200: 'levels 5-12',
    40: 'levels 10-18: the gate of the Stonemarch',
    100: 'reach it sooner: a level-13 mine five zones from the city, behind a level-20 kingdom',
    65: 'levels 18-26',
    270: 'levels 25-35: a marquee quest zone',
    512: 'the Deep Road\'s spine (450 rooms): split its map into three stretches by level (42-50, 50-58, 58-68)',
    514: 'the Deep Road\'s end: Morkai, the city of the dead, level 62-68',
}


def zones():
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'world', 'zones', '*.json'))):
        z = json.load(open(f, encoding='utf-8'))
        n = z.get('number')
        if n is None:
            n = int(re.search(r'zone_(\d+)', f).group(1))
        rooms, mobs = z.get('rooms') or {}, z.get('mobs') or {}
        ml = list(mobs.values()) if isinstance(mobs, dict) else mobs
        lv = [m.get('level') for m in ml if isinstance(m.get('level'), int)]
        out[n] = {'name': z.get('name') or f'Zone {n}', 'rooms': len(rooms), 'level': int(statistics.median(lv)) if lv else None}
    return out


def region_of():
    where = {}
    for rid, (_n, _l, _b, zs) in REGIONS.items():
        for z in zs:
            where.setdefault(z, []).append(rid)
    return where


def problems(zs):
    where, bad = region_of(), []
    for n in zs:
        if n in OUTSIDE:
            continue
        if n not in where:
            bad.append(f'zone {n} ({zs[n]["name"]}) has no region')
        elif len(where[n]) > 1:
            bad.append(f'zone {n} ({zs[n]["name"]}) is in {where[n]}')
    for n in where:
        if n not in zs:
            bad.append(f'zone {n} is in {where[n]} but is not in the world')
    return bad


def main():
    zs = zones()
    bad = problems(zs)
    if bad:
        print('\n'.join(bad), file=sys.stderr)
        return 1
    if '--check' in sys.argv:
        print(f'ok: {sum(len(r[3]) for r in REGIONS.values())} zones in {len(REGIONS)} regions')
        return 0
    data = {'_about': 'The regions of the world (docs/world/WORLD_SPINE.md). Written by tools/world/regions_ledger.py: edit REGIONS there.',
            'regions': [{'id': rid, 'name': n, 'line': line, 'levels': list(band), 'zones': list(zl)} for rid, (n, line, band, zl) in REGIONS.items()]}
    with open(os.path.join(ROOT, 'world', 'regions.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write('\n')
    for rid, (name, line, band, zl) in REGIONS.items():
        rooms = sum(zs[z]['rooms'] for z in zl)
        print(f'\n### {name} (levels {band[0]}-{band[1]}; {len(zl)} zones, {rooms:,} rooms)\n')
        print('| Zone | Now | The spine asks |\n|---|---|---|')
        for z in zl:
            now = f'{zs[z]["rooms"]} rooms, ' + (f'level {zs[z]["level"]}' if zs[z]['level'] is not None else 'no creatures of its own')
            print(f'| {zs[z]["name"]} ({z}) | {now} | {ASK.get(z, "keep")} |')
    return 0


if __name__ == '__main__':
    sys.exit(main())
