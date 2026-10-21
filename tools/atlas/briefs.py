#!/usr/bin/env python3
"""Writing briefs for the build-out of the connector zones (world/buildout).

Each job is a set of rooms one writer describes by hand (and, for a zone's first job, the zone's
creatures and items): the zone's theme from world/buildout/themes.json, the style rules, and every
room still on placeholder text in walking order, with its terrain, its ways out and the names of
the rooms they lead to. A big zone is split into parts that each cover one stretch of country.

    python3 tools/atlas/briefs.py OUT_DIR            # one brief per job: OUT_DIR/<job>.md
    python3 tools/atlas/briefs.py OUT_DIR --list     # just the jobs and their sizes

The writer answers with world/buildout/parts/<job>.json (see the brief); tools/atlas/buildout.py
checks it and folds it into the world.
"""
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ZONES = os.path.join(ROOT, 'world', 'zones')
BUILDOUT = os.path.join(ROOT, 'world', 'buildout')

# job -> (zones, part, parts, designs the zones' creatures and items)
JOBS = {
    'trade_a': ([408], 1, 4, True), 'trade_b': ([408], 2, 4, True),
    'trade_c': ([408], 3, 4, True), 'trade_d': ([408], 4, 4, True),
    'minar_a': ([435], 1, 3, True), 'minar_b': ([435], 2, 3, True), 'minar_c': ([435], 3, 3, True),
    'sea_a': ([120], 1, 2, True), 'sea_b': ([120], 2, 2, True),
    'desert_plains': ([50, 60], 1, 1, True),
    'mountain_north': ([40, 66], 1, 1, True),
    'mira_quick': ([448, 415], 1, 1, True),
    'mira_south': ([451], 1, 1, True),
    'raven_winter': ([472, 521], 1, 1, True),
    'badlands_kings': ([471, 441, 61], 1, 1, True),
    # connector rooms whose carried text describes another place (Port Halyon still reading as
    # Rome; a road carrying a shop's interior): rewritten to fit their atlas names
    'fixups': ([60, 40, 66, 120, 408], 1, 1, False),
    # Garathorm's own districts (their creatures are in world/population/zone_<n>.json)
    'garathorm_wall': ([403, 418], 1, 1, False),
    'cathedral': ([431], 1, 1, False),
    'school_fameland': ([517, 420], 1, 1, False),
    # rooms whose original writing came back (circle-contrib-areas): tools/atlas/contrib.py
    'ghenna': ([481], 1, 1, False),
    'chaos': ([475], 1, 1, False),
    'minos': ([9], 1, 1, False),
    'hommlet': ([423], 1, 1, False),
    'haunted_house': ([482], 1, 1, False),
    'ancalador': ([479], 1, 1, False),
    # the sealed atlas zones, each written and peopled by one writer
    'z414': ([414], 1, 1, True),
    'z416': ([416], 1, 1, True),
    'z419': ([419], 1, 1, True),
    'z424': ([424], 1, 1, True),
    'z426': ([426], 1, 1, True),
    'z429': ([429], 1, 1, True),
    'z436': ([436], 1, 1, True),
    'z439': ([439], 1, 1, True),
    'z445': ([445], 1, 1, True),
    'z447': ([447], 1, 1, True),
    'z449': ([449], 1, 1, True),
    'z452': ([452], 1, 1, True),
    'z453': ([453], 1, 1, True),
    'z454': ([454], 1, 1, True),
    'z455': ([455], 1, 1, True),
    'z458': ([458], 1, 1, True),
    'z461': ([461], 1, 1, True),
    'z464': ([464], 1, 1, True),
    'z465': ([465], 1, 1, True),
    'z467': ([467], 1, 1, True),
    'z470': ([470], 1, 1, True),
    'z474': ([474], 1, 1, True),
    'z476': ([476], 1, 1, True),
    'z478': ([478], 1, 1, True),
    'z480': ([480], 1, 1, True),
    'z488': ([488], 1, 1, True),
    'z491': ([491], 1, 1, True),
    'z494': ([494], 1, 1, True),
    'z495': ([495], 1, 1, True),
    'z496': ([496], 1, 1, True),
    'z499': ([499], 1, 1, True),
    'z501': ([501], 1, 1, True),
    'z502': ([502], 1, 1, True),
    'z503': ([503], 1, 1, True),
    'z504': ([504], 1, 1, True),
    'z505': ([505], 1, 1, True),
    'z507': ([507], 1, 1, True),
    'z508': ([508], 1, 1, True),
    'z509': ([509], 1, 1, True),
    'z512a': ([512], 1, 3, True), 'z512b': ([512], 2, 3, True), 'z512c': ([512], 3, 3, True),
    'z514': ([514], 1, 1, True),
    'z515': ([515], 1, 1, True),
    'z518': ([518], 1, 1, True),
    'z519': ([519], 1, 1, True),
    'z520': ([520], 1, 1, True),
    'z522': ([522], 1, 1, True),
    # the placeholders left in zones that were ours before the re-lay (2026-10): rooms only, the
    # creatures are there already
    'city_a': ([30], 1, 2, False), 'city_b': ([30], 2, 2, False),
    'outcast_a': ([442], 1, 2, False), 'outcast_b': ([442], 2, 2, False),
    'apocalypse_a': ([220], 1, 2, False), 'apocalypse_b': ([220], 2, 2, False),
    'drow': ([51], 1, 1, False),
    'stable_elves': ([32, 110], 1, 1, False),
    'odds_and_ends': ([457, 72, 250, 65, 53, 12, 63, 150], 1, 1, False),
}
FIXUPS = [3516, 4002, 6602, 6610, 6612, 12003, 12005, 12006, 12007, 12010, 12015, 12018, 12019, 12022, 12023,
          12024, 12029, 12031, 12035, 12036, 12039, 12043, 12044, 12049, 12050, 12051, 12062, 12063, 15061,
          15062, 15065, 15067, 15068, 15071]

FIXUP_INTRO = """\
## These rooms are rewrites
Each of these rooms already has a description, but it was carried over from a different place
when the world was re-laid on the atlas: Port Halyon's rooms still read as old Rome (an emperor,
the Coliseum, Roman citizens), and some road and wilderness rooms carry a house's or a shop's
interior. Write each one afresh to fit its name, terrain, exits and neighbours. Keep what the
room is for when its "usually here" list shows it (a general store stays a general store, a
bakery a bakery, a mage's workshop a workshop, an office an office), and keep the striking
features that still fit (a pit full of the dead by the road, a burned-out shop beside it). Port
Halyon is a harbour city on the Sea of Storms run by its dock master and harbour council: no
emperor, no Rome, no Coliseum. The current text of each room is shown as "now".
"""
COMPASS = ('north', 'east', 'south', 'west', 'up', 'down')
WATER = ('water_swim', 'water_noswim', 'water_surface', 'underwater')

STYLE = """\
## How to write the rooms
- **One description per room, every room its own.** Rooms that share a name ("The Plains",
  "On Mira Retrum") must still read differently: change the concrete details (the ground, the
  light, a landmark, a sound, a smell, the weather's mark, a sign of people or beasts).
  No sentence may appear twice anywhere in your file.
- **3 to 5 sentences, 45 to 100 words**, present tense, the realm's classic MUD voice (a
  scene, now and then "you"). Plain prose: no colour codes, no lists, no headings, no quotes
  from the brief.
- **Compass words only for real ways out.** Use north, south, east or west (or northern,
  northward, north-east and the like) only for a direction this room has an exit; say where
  the way leads in a few words ("The road runs on east toward the Birch Woods"). Diagonals are
  never exits, so don't use them. Describe distant scenery without compass words ("beyond the
  trees", "far across the water"). A way up or down you describe must exist too.
- **Fit the neighbours.** Each room lists its exits and the names of the rooms they reach:
  let the description agree (birches ahead if the next room is The Birch Woods; the city wall
  if Garathorm is next door). A neighbour in a sealed land ("sealed: not built yet") lies
  behind a barred gate or a closed, overgrown way.
- **The terrain decides the scene.** Outdoors: sky, weather, ground, plants. Inside: walls,
  light, furnishings, no sky. Caves and tunnels: dark, no sky. Water rooms: you are afloat (in a
  boat or on a raft), so describe the water, the swell, the shore or the ice around you.
- **Say what a room looks like when it isn't plain.** The 3D client draws a room by its look
  (src/room_looks.py). When a room is a cave, mine, crypt, sewer, dungeon, desert, snow, shore,
  volcanic ground or swamp, give it that look: write the room as
  `{"description": "...", "look": "cave"}` instead of a bare string. Let the text agree (a cave
  room's words speak of rock, not walls and furniture); the world check fails a room whose
  name says one thing and its look another.
- **No creatures and no loose items in the text** (they come and go); fixed scenery is fine
  (a milestone, a well, a statue, a signpost, a wrecked cart).
- **Names**: the city is Garathorm (never Midgaard); keep every place name exactly as given.
- **Extras (optional):** for a landmark you mention (an inscription, a statue, a strange
  stone), add an extra description: keywords and 1-3 sentences. At most about one per eight rooms.
"""

DESIGN = """\
## Creatures and items (you design them for your stretch of {zones})
Write them into the same file (`creatures`, `items`). Numbers (health, damage, armour, value)
are worked out by the build from each one's level and kind; you give the words and the facts.

Creature:
```json
{{"id": "highwayman", "keywords": "highwayman bandit man", "short_desc": "a ragged highwayman",
 "long_desc": "A ragged highwayman leans on a waymark, thumbing the edge of his knife.",
 "description": "Two to four sentences of what you see up close.",
 "kind": "humanoid", "level": 14, "aggressive": true, "alignment": -400,
 "sectors": ["forest", "field"], "rooms": ["The King's Road", "On The Trail Of Shadows"],
 "count": 10, "drops": [{{"item": "highwayman-blade", "chance": 20}}]}}
```
- `kind`: animal, humanoid, monster or undead. Animals carry no gold.
- `level` within the zone's levels; lower nearer the temple, higher in the wild and dark places.
- `sectors` (terrains it keeps to) and/or `rooms` (room names it keeps to): where it is placed.
  Water creatures only on water; land creatures only on land.
- `count`: how many stand in your rooms (your creatures are placed only in the rooms you
  write). Wild country: about one creature for every five rooms, spread over 4 to 6 kinds;
  none or only harmless folk in streets and towns.
- `aggressive`: true only for predators, outlaws, undead and monsters; never for townsfolk.
- The 3D client gives each creature a body from the plain words in its name: say clearly what
  it is with a common noun (wolf, bear, boar, stag, hare, spider, crab, seal, shark, raven,
  troll, ogre, ghost, skeleton, bandit, mercenary, cultist, hunter, guard, merchant).
- `long_desc` is the line shown in the room: a full sentence that starts with the creature.

Item:
```json
{{"id": "highwayman-blade", "keywords": "short sword notched", "short_desc": "a notched short sword",
 "room_desc": "A notched short sword lies here.", "description": "One to three sentences.",
 "kind": "weapon", "level": 14, "weapon_type": "slash"}}
```
- `kind`: weapon (with `weapon_type` slash, pierce or pound), armor (with `wear_slot`: body,
  head, legs, feet, hands, arms, shield, about, waist, wrist, neck, finger), treasure (to sell),
  food, potion or light.
- Optional `bonus`, one small one at most: {{"str": 1}} (or dex, con, int, wis, cha), or
  {{"hitroll": 1}} / {{"damroll": 1}} (up to 2), or {{"hp": 10}} (up to 15).
- 3 to 5 items, each dropped by at least one of your creatures (`drops`, chance 10-35).
"""

ROOMS_ONLY = """\
## Creatures and items
Another writer designs this zone's creatures and items; you write the rooms only.
"""

OUTPUT = """\
## What to hand back
Write one JSON file, `{out}` (UTF-8, valid JSON: escape double quotes inside text as \\"):
```json
{{"job": "{job}",
 "rooms": {{"<vnum>": "The description, as one paragraph.", "<vnum>": {{"description": "...", "look": "cave"}}}},
 "extras": {{"<vnum>": [{{"keywords": "waymark stone", "description": "..."}}]}}{design}}}
```
Every one of your {n} rooms must be in `rooms`, keyed by its vnum.

Write it in pieces of about 30 rooms, in the order listed: `world/buildout/parts/{job}.p1.json`,
`.p2.json` and so on, each a JSON object of the same shape holding some of the rooms (put
`creatures` and `items` in the last piece). Then fold them together with
`python3 tools/atlas/buildout.py --merge {job}`, check the result with
`python3 tools/atlas/buildout.py --check {out}`, and fix whatever it reports in `{out}` itself
(run the check until it says OK). Write every description yourself, one room at a time: never
generate them with code, templates or word lists. Touch no other file and don't use git.
Finish with a two-line summary of what you wrote.
"""


def load():
    zones, rooms = {}, {}
    for path in sorted(glob.glob(os.path.join(ZONES, 'zone_*.json'))):
        with open(path, encoding='utf-8') as f:
            z = json.load(f)
        zones[z['number']] = z
        rs = z.get('rooms') or {}
        for v, r in (rs.items() if isinstance(rs, dict) else ((str(r['vnum']), r) for r in rs)):
            r['_zone'] = z['number']
            rooms[int(v)] = r
    return zones, rooms


def exits_of(r):
    out = []
    for d in COMPASS:
        ex = (r.get('exits') or {}).get(d)
        if isinstance(ex, dict) and ex.get('to_room') is not None:
            out.append((d, ex['to_room'], ex))
    return out


def walk_order(zone, rooms, start):
    """The zone's rooms in walking order: depth first from where you come in, compass order, so
    each part of a split zone is one stretch of country."""
    vs = {v for v, r in rooms.items() if r['_zone'] == zone}
    order, seen = [], set()
    starts = [start] + sorted(vs)
    for s in starts:
        if s in seen or s not in vs:
            continue
        stack = [s]
        while stack:
            v = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            order.append(v)
            nxt = [t for d, t, ex in exits_of(rooms[v]) if t in vs and t not in seen]
            stack.extend(reversed(nxt))
    return order


def entrance(zone, rooms, zones):
    """Where you come into the zone from the temple's side: the zone's room nearest the temple
    on foot (never through the God Rooms or a sealed land)."""
    dist, q = {3001: 0}, collections.deque([3001])
    while q:
        v = q.popleft()
        if rooms[v]['_zone'] == zone:
            return v
        for d, t, ex in exits_of(rooms[v]):
            if t in rooms and t not in dist and 'imm_only' not in (rooms[t].get('flags') or []) \
                    and not zones[rooms[t]['_zone']].get('sealed'):
                dist[t] = dist[v] + 1
                q.append(t)
    return min(v for v, r in rooms.items() if r['_zone'] == zone)


MANIFEST = os.path.join(BUILDOUT, 'jobs.json')


def manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding='utf-8') as f:
            return {k: v for k, v in json.load(f).items() if not k.startswith('_')}
    return {}


def job_rooms(job, zones, rooms):
    """The rooms a job writes: as fixed in world/buildout/jobs.json when it was handed out (writing
    a room clears its placeholder, so they can't be worked out again afterwards)."""
    known = manifest()
    if job in known:
        return list(known[job])
    return _job_rooms(job, zones, rooms)


def _job_rooms(job, zones, rooms):
    if job == 'fixups':
        return list(FIXUPS)
    zs, part, parts, design = JOBS[job]
    out = []
    for z in zs:
        order = [v for v in walk_order(z, rooms, entrance(z, rooms, zones)) if rooms[v].get('placeholder')]
        if parts > 1:
            size = -(-len(order) // parts)
            order = order[(part - 1) * size: part * size]
        out.extend(order)
    return out


def neighbour(t, rooms, zones, zone):
    r = rooms.get(t)
    if r is None:
        return f'{t} (nowhere)'
    z = zones[r['_zone']]
    where = ''
    if r['_zone'] != zone:
        where = f" [{z['name']}{': sealed, not built yet' if z.get('sealed') else ''}]"
    return f"{t} {r.get('name', '?')}{where}"


def room_line(v, rooms, zones, mobs, objs):
    r = rooms[v]
    zone = r['_zone']
    flags = [f for f in (r.get('flags') or []) if f in ('indoors', 'dark', 'no_mob', 'peaceful', 'deathtrap', 'death')]
    ex = []
    for d, t, e in exits_of(r):
        door = e.get('door') or {}
        dn = f" (through {door.get('name', 'a door')})" if door and not door.get('sealed_zone') else ''
        ex.append(f"{d}: {neighbour(t, rooms, zones, zone)}{dn}")
    here = []
    for m in r.get('mob_resets') or []:
        mv = m.get('vnum') if isinstance(m, dict) else m
        if mv in mobs:
            here.append(mobs[mv].get('short_desc') or mobs[mv].get('name'))
    for o in r.get('obj_resets') or []:
        ov = o.get('vnum') if isinstance(o, dict) else o
        if ov in objs:
            here.append(objs[ov].get('short_desc') or objs[ov].get('name'))
    sector = r.get('sector_type', '?') + (' (on the water)' if r.get('sector_type') in WATER else '')
    line = f"- **{v}** {r.get('name')} | {sector}{' | ' + ', '.join(flags) if flags else ''}\n  exits: {'; '.join(ex) or 'none'}"
    if here:
        line += f"\n  usually here (don't write them in): {', '.join(sorted(set(here)))}"
    return line


def brief(job, zones, rooms, mobs, objs, themes):
    zs, part, parts, design = JOBS[job]
    vs = job_rooms(job, zones, rooms)
    names = ', '.join(f"{zones[z]['name']} (zone {z})" for z in zs)
    out = os.path.join('world', 'buildout', 'parts', f'{job}.json')
    L = [f"# Build-out brief `{job}`: {names}" + (f", part {part} of {parts}" if parts > 1 else ''), '']
    L.append(f"You are writing the room descriptions for {len(vs)} rooms of the MUD Misthollow, by hand, "
             f"one at a time" + (", and this zone's creatures and items" if design else '') + '. '
             'The rooms exist already (names, exits and map come from the owner\'s atlas); today they carry '
             'placeholder text. Read the realm and zone notes, then the rules, then write.\n')
    L.append('## The realm\n' + themes['world'] + '\n')
    for z in zs:
        t = themes['zones'][str(z)]
        lo, hi = t['levels']
        vz = [v for v, r in rooms.items() if r['_zone'] == z]
        here = collections.Counter()
        for v in vz:
            for m in rooms[v].get('mob_resets') or []:
                mv = m.get('vnum') if isinstance(m, dict) else m
                if mv in mobs:
                    here[mobs[mv].get('short_desc') or mobs[mv].get('name')] += 1
        L.append(f"## {t['name']} (zone {z}), levels {lo}-{hi}")
        L.append(t['theme'])
        L.append(f"\n**Mood:** {t['mood']}")
        if design:
            L.append(f"\n**Creature ideas:** {t['creatures']}\n\n**Item ideas:** {t['items']}")
        if here:
            L.append('\n**Creatures already in the zone:** ' + ', '.join(f'{n} x{c}' for n, c in here.most_common(25)))
        L.append('')
    L.append(STYLE)
    if job == 'fixups':
        L.append(FIXUP_INTRO)
    L.append(DESIGN.format(zones=names) if design else ROOMS_ONLY)
    others = []
    for path in sorted(glob.glob(os.path.join(BUILDOUT, 'parts', '*.json'))):
        other = os.path.splitext(os.path.basename(path))[0]
        if other == job or '.p' in other or other not in JOBS or not set(JOBS[other][0]) & set(zs):
            continue
        with open(path, encoding='utf-8') as f:
            got = json.load(f)
        for c in got.get('creatures') or []:
            others.append(f"{c.get('short_desc')} (level {c.get('level')}, {other})")
    if design and others:
        L.append('**Already made for this zone by the writers of its other stretches** (yours stand only '
                 'in your rooms; make your own kinds for what your stretch holds, and don\'t repeat these unless '
                 'the same beast plainly lives here too): ' + '; '.join(others) + '\n')
    L.append(OUTPUT.format(out=out, job=job, n=len(vs),
                           design=',\n "creatures": [...],\n "items": [...]' if design else ''))
    L.append(f"## Your rooms ({len(vs)}, in walking order)\n")
    for v in vs:
        L.append(room_line(v, rooms, zones, mobs, objs))
        if job == 'fixups':
            L.append('  now: ' + ' '.join((rooms[v].get('description') or '').split()))
    written = sorted({t for v in vs for d, t, e in exits_of(rooms[v])
                      if t in rooms and not rooms[t].get('placeholder') and (rooms[t].get('description') or '').strip()})
    if written:
        L.append('\n## Neighbouring rooms already written (for continuity; do not rewrite them)\n')
        for t in written:
            text = ' '.join((rooms[t].get('description') or '').split())
            L.append(f"- **{t}** {rooms[t].get('name')}: {text[:300]}")
    return '\n'.join(L) + '\n', vs


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    zones, rooms = load()
    mobs, objs = {}, {}
    for z in zones.values():
        for key, dst in (('mobs', mobs), ('objects', objs)):
            ps = z.get(key) or {}
            for p in (ps.values() if isinstance(ps, dict) else ps):
                dst[int(p['vnum'])] = p
    with open(os.path.join(BUILDOUT, 'themes.json'), encoding='utf-8') as f:
        themes = json.load(f)
    known = manifest()
    fresh = {job: _job_rooms(job, zones, rooms) for job in JOBS if job not in known}
    if fresh and '--list' not in sys.argv:
        with open(MANIFEST, 'w', encoding='utf-8') as f:
            json.dump({'_about': 'The rooms each build-out job writes (tools/atlas/briefs.py), fixed when handed out.',
                       **known, **fresh}, f, indent=1)
            f.write('\n')
    total = 0
    for job in JOBS:
        text, vs = brief(job, zones, rooms, mobs, objs, themes)
        total += len(vs)
        if '--list' not in sys.argv:
            with open(os.path.join(out_dir, f'{job}.md'), 'w', encoding='utf-8') as f:
                f.write(text)
        print(f'{job:<16} {len(vs):>4} rooms  {len(text) // 4:>6} tokens (about)')
    print(f'{total} rooms in all')


if __name__ == '__main__':
    main()
