"""Rebuild world/zones on the Bedlam atlas (Push 27), from the atlas, the approved match
(world/atlas/zones.json, rooms.json, vnums.json, overrides.json) and our content.

- Every atlas area becomes a zone: a matched or similar one keeps the number of the zone of ours
  it pairs with most, the rest take 400 + atlas id; atlas-only zones that are not connectors (or
  the city wall) are sealed until built.
- Every atlas room: the atlas's name, game vnum and exits (directions and targets), its place on
  the map; our description (Midgaard read as Garathorm) where the pairing is sound, else a
  placeholder; our terrain where paired (unless ours calls dry land water), else the atlas's;
  our flags, creatures, items, puzzles and the rest carried over; doors ours where we have the
  same doorway, else from the atlas.
- Our rooms the atlas lacks: annexes kept and hung off their free side, moves give their
  creatures and items to the room beside them, drops go. Our zones off the atlas are kept and
  joined at their hookups. Our creatures and items (the prototypes) go with the zone that took
  their rooms.
- The connection pass (connect.py) makes every open room reachable from the temple and back.
- Writes world/zones/*.json, world/atlas/connections.json and world/atlas/renumber.json.

    python3 tools/atlas/build_world.py --check    # say what it would do, write nothing
    python3 tools/atlas/build_world.py            # rebuild world/zones
"""
import collections
import copy
import glob
import json
import os
import random
import re
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (ATLAS_DIR, OUT_DIR, PRE_RELAY_REV, ROOT, SECTOR, UNDER, ZONES_DIR, likeness,  # noqa: E402
                    load_atlas, load_overrides, load_world)
import buildout  # noqa: E402
import connect  # noqa: E402

OPP = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east', 'up': 'down', 'down': 'up'}
WATER = ('water_swim', 'water_noswim', 'water_surface')
WET_WORDS = re.compile(r'\b(river|lake|sea|ocean|water|waters|stream|pool|canal|bay|harbou?r|marsh|swamp|'
                       r'creek|brook|pond|ford|current|wave|waves|surf|shallows|rapids|falls|delta|mere|'
                       r'strait|lagoon|beach|on the|riding|afloat|raft|ferry)\b', re.I)
CARRY = ('flags', 'extra_descs', 'mob_resets', 'obj_resets', 'special', 'room_effects', 'zone_mechanic',
         'hidden_items', 'puzzles', 'gathering_nodes', 'mobs')
LISTS = ('mob_resets', 'obj_resets', 'hidden_items', 'puzzles', 'gathering_nodes')
ZONE_FIELDS = ('lifespan', 'reset_time', 'reset_mode', 'reset_interval', 'level_range', 'level_min', 'level_max',
               'description', 'zone_mechanics', 'author')
IMM_ONLY_ZONES = (12,)      # the God Rooms: immortals only (the owner's call)


def garathorm(text):
    """Midgaard is the atlas's Garathorm."""
    if isinstance(text, str):
        return text.replace('Midgaard', 'Garathorm').replace('MIDGAARD', 'GARATHORM').replace('midgaard', 'garathorm')
    if isinstance(text, list):
        return [garathorm(x) for x in text]
    if isinstance(text, dict):
        return {k: garathorm(v) for k, v in text.items()}
    return text


def clean(room):
    return {k: v for k, v in room.items() if not k.startswith('_')}


# ---------------------------------------------------------------- placeholder descriptions
LINES = {
    'city': ["Worn flagstones run between weathered walls, swept by passing feet.",
             "Shuttered windows and old doorways crowd in on either hand.",
             "Lantern hooks and faded signboards hang over the street.",
             "The paving is uneven here, patched with newer stone.",
             "Voices and the clatter of carts carry from somewhere nearby."],
    'forest': ["Old trees crowd close, their roots knotted across the path.",
               "Ferns and moss soften the ground beneath a dim green canopy.",
               "Birdsong drifts down through the branches overhead.",
               "Fallen needles and leaves muffle every step.",
               "Shafts of pale light slant between the trunks."],
    'field': ["Open grassland rolls away under a wide sky.",
              "Wind moves through the tall grass in long, slow waves.",
              "Wildflowers dot the meadow, and insects hum among them.",
              "A worn track crosses the open ground.",
              "The land lies flat and quiet in every direction."],
    'hills': ["The ground rises and falls in grassy folds.",
              "Rocks break through the thin soil of the slope.",
              "From the crest the land below spreads out like a map.",
              "A narrow path winds between the hillocks.",
              "Gorse and heather cling to the windy rise."],
    'mountain': ["Bare rock climbs steeply on one side and falls away on the other.",
                 "The air is thin and cold, and loose scree shifts underfoot.",
                 "A narrow ledge picks its way along the mountainside.",
                 "Wind howls through a cleft in the stone.",
                 "Snow lingers in the shadowed hollows of the rock."],
    'water_swim': ["Shallow water laps around stones and reeds.",
                   "The current is gentle here, clear enough to see the bottom.",
                   "Mud and pebbles shift beneath the slow water.",
                   "Reeds rustle along the water's edge."],
    'water_noswim': ["Deep water stretches away, dark and restless.",
                     "Waves slap against the hull of anything that floats here.",
                     "The far shore is a smudge on the horizon.",
                     "The water runs deep and cold, too deep to wade."],
    'inside': ["Stone walls close in, cool to the touch.",
               "Dust lies thick in the corners, undisturbed for some time.",
               "The air is still and smells faintly of old smoke.",
               "Shadows gather where the light does not reach.",
               "The floor is worn smooth by long use."],
}


def placeholder(room, sector, vnum, names):
    rng = random.Random(vnum)
    lines = rng.sample(LINES.get(sector, LINES['inside']), 2)
    ways = [d for d in ('north', 'east', 'south', 'west', 'up', 'down') if d in room.get('exits', {})]
    if ways:
        tail = (f"A way leads {ways[0]}." if len(ways) == 1 else
                f"Ways lead {', '.join(ways[:-1])} and {ways[-1]}.")
        lines.append(tail)
    return textwrap.fill(' '.join(lines), 72)


# ---------------------------------------------------------------- the build
def build(write=False):
    atlas = load_atlas()
    A, AREAS = atlas['rooms'], atlas['areas']
    zones, R = load_world(PRE_RELAY_REV)      # our world as it was before the re-lay
    ov = load_overrides()
    zj = json.load(open(os.path.join(ATLAS_DIR, 'zones.json')))
    rj = json.load(open(os.path.join(ATLAS_DIR, 'rooms.json')))
    areas = {int(k): v for k, v in zj['areas'].items()}
    ztab = {int(k): v for k, v in zj['zones'].items()}
    hooks = {int(k): v for k, v in zj['hookups'].items()}
    rows = {int(k): v for k, v in rj['atlas'].items()}
    clusters = {int(k): v for k, v in rj['orphan_clusters'].items()}
    moves = {int(k): v for k, v in rj['similar_moves'].items()}
    game = {a: r['game'] for a, r in rows.items()}
    pair = {a: r['ours'] for a, r in rows.items() if r.get('ours') is not None}
    movers = collections.defaultdict(list)
    for o, a in moves.items():
        movers[a].append(o)

    # zone numbers for the atlas areas
    keep_numbers = {z for z, v in ztab.items() if v['status'] in ('ours-only', 'internal')}
    used = set(keep_numbers)
    area_zone = {}
    order = sorted(areas, key=lambda a: (areas[a]['status'] not in ('matched', 'similar'), -areas[a]['paired'], a))
    for area in order:
        meta = areas[area]
        pick = None
        if meta['status'] in ('matched', 'similar'):
            counts = collections.Counter(R[pair[a]]['_zone'] for a in rows if rows[a]['area'] == area and a in pair)
            for z in meta['our_zones']:
                counts[z] += 0.5
            for z, _ in counts.most_common():
                if z not in used:
                    pick = z
                    break
        if pick is None:
            pick = 400 + area
        area_zone[area] = pick
        used.add(pick)
    connectors = set(ov.get('connectors', [])) | set(ov.get('open_too', []))
    sealed_area = {a for a, v in areas.items() if v['status'] == 'atlas-only' and a not in connectors}

    new_rooms = {}          # game vnum -> room dict (with _zone)
    room_zone = {}
    notes = collections.Counter()

    # ---- atlas rooms (an unfinished stub on the atlas, with no name and no way in or out, is left out)
    incoming = collections.Counter(t for r in A.values() for t in r['exits'].values())
    stubs = {a for a, r in A.items() if not (r['name'] or '').strip() and not r['exits'] and not incoming[a]}
    for a, ar in sorted(A.items()):
        if a in stubs:
            notes['atlas stubs left out'] += 1
            continue
        v = game[a]
        z = area_zone[ar['area']]
        o = pair.get(a)
        mv = movers.get(a, [])
        base = R.get(o) if o is not None else None
        room = {'vnum': v, 'name': ar['name'] or 'A Nameless Place', '_zone': z,
                'map': {'x': ar['x'], 'y': ar['y'], 'z': ar['z']}}
        # terrain
        atlas_sector = SECTOR.get(ar['terrain'], 'inside')
        if atlas_sector != 'inside' and UNDER.search(ar['name'].lower()):
            atlas_sector = 'inside'
        if base:
            ours = base['_sector'] or atlas_sector
            ours = {'water_surface': 'water_swim', 'indoors': 'inside'}.get(ours, ours)
            if ours in WATER and atlas_sector not in WATER and not WET_WORDS.search(ar['name']):
                ours = atlas_sector          # ours called dry land water (the spider web in the tree)
                notes['water fixed'] += 1
            room['sector_type'] = ours
        else:
            room['sector_type'] = atlas_sector
        # carried content
        sources = ([base] if base else []) + [R[x] for x in mv if x in R]
        for src in sources:
            for k in CARRY:
                val = src.get(k)
                if not val:
                    continue
                if k in LISTS:
                    room.setdefault(k, [])
                    room[k] = room[k] + copy.deepcopy(val)
                elif k == 'extra_descs' and isinstance(val, dict):
                    room.setdefault(k, {}).update(copy.deepcopy(val))
                elif k == 'flags':
                    room['flags'] = sorted(set(room.get('flags', [])) | set(val))
                elif k not in room:
                    room[k] = copy.deepcopy(val)
        if 'flags' not in room:
            room['flags'] = ['indoors'] if room['sector_type'] == 'inside' else []
        # description
        desc_src = None
        if base and (rows[a].get('how') != 'position' or likeness(ar['name'], base['_name']) >= 0.3):
            desc_src = base
        elif mv:
            for x in mv:
                if x in R and likeness(ar['name'], R[x]['_name']) >= 0.3:
                    desc_src = R[x]
                    break
        if desc_src and len((desc_src.get('description') or '').strip()) >= 40:
            room['description'] = desc_src['description']
        else:
            room['_needs_placeholder'] = True
        # exits: the atlas's
        exits = {}
        for d, t in ar['exits'].items():
            tv = game[t]
            ex = {'to_room': tv}
            ob = base['exits'].get(d) if base and isinstance(base.get('exits'), dict) else None
            same = isinstance(ob, dict) and ob.get('to_room') in (tv, pair.get(t))
            if same:
                ex = {k: copy.deepcopy(val) for k, val in ob.items() if k != 'room'}
                ex['to_room'] = tv
            else:
                ex['description'] = f"To the {d} lies {A[t]['name'] or 'somewhere'}."
                kind = (ar.get('doors') or {}).get(d)
                if kind:
                    ex['door'] = {'name': 'door', 'state': 'closed', 'locked': False}
                    if kind == 'locked door':
                        notes['locked doors left unlocked (no key known)'] += 1
            exits[d] = ex
        room['exits'] = exits
        new_rooms[v] = room

    # ---- our rooms the atlas lacks
    renumber = {}
    attach_ways = []
    for cid, c in sorted(clusters.items()):
        kind = c['kind']
        if kind == 'annex' and c.get('attach_atlas'):
            z = area_zone[A[c['attach_atlas']]['area']]
            cl = set(c['rooms'])
            for x in c['rooms']:
                r = clean(R[x])
                r['exits'] = {d: ex for d, ex in (r.get('exits') or {}).items()
                              if isinstance(ex, dict) and ex.get('to_room') in cl}
                r['_zone'] = z
                r['_annex'] = True
                new_rooms[x] = r
            entry, d, at = c['entry'], c['dir'], game[c['attach_atlas']]
            attach_ways.append((at, d, entry))
        else:
            beside = game.get(c.get('beside_atlas')) if c.get('beside_atlas') else None
            for x in c['rooms']:
                if beside:
                    renumber[x] = beside
                if kind in ('move', 'unplaced') and beside:
                    for k in ('mob_resets', 'obj_resets'):
                        if R[x].get(k):
                            new_rooms[beside].setdefault(k, [])
                            new_rooms[beside][k] += copy.deepcopy(R[x][k])
                            notes[f'{k} moved'] += len(R[x][k])
    for at, d, entry in attach_ways:
        new_rooms[at]['exits'][d] = {'to_room': entry, 'description': f"To the {d} lies {new_rooms[entry].get('name')}."}
        new_rooms[entry]['exits'][OPP[d]] = {'to_room': at, 'description': f"To the {OPP[d]} lies {new_rooms[at].get('name')}."}

    # ---- our zones off the atlas, kept, joined at their hookups
    for z, v in ztab.items():
        if v['status'] not in ('ours-only', 'internal'):
            continue
        for x, r in R.items():
            if r['_zone'] == z:
                rr = clean(r)
                rr['_zone'] = z
                new_rooms[x] = rr
    hooked = []
    for z, hs in hooks.items():
        for h in hs:
            if not h.get('atlas_room'):
                continue
            at, d, inside = game[h['atlas_room']], h['dir'], h['zone_room']
            old_from = h.get('from')
            ex_in = new_rooms[inside].setdefault('exits', {})
            for dd in [k for k, e in ex_in.items() if isinstance(e, dict) and e.get('to_room') == old_from]:
                ex_in.pop(dd)
            new_rooms[at]['exits'][d] = {'to_room': inside, 'description': f"To the {d} lies {new_rooms[inside].get('name')}."}
            ex_in[OPP[d]] = {'to_room': at, 'description': f"To the {OPP[d]} lies {new_rooms[at].get('name')}."}
            hooked.append((at, d, inside))

    # rooms of ours that are gone: where their references go (a similar zone's room: the atlas
    # room about where it was; any other: the nearest kept room on our old map)
    similar_pos = {int(k): v for k, v in rj.get('similar_pos', {}).items()}
    for x, a in moves.items():
        if x not in new_rooms and x not in renumber:
            renumber[x] = game[a]
    for x, a in similar_pos.items():
        if x not in new_rooms and x not in renumber:
            renumber[x] = game[a]
    for x, r in R.items():
        if x in new_rooms:
            continue
        if x in renumber:
            continue
        # the nearest kept room of ours, walking our old map
        seen, q, dest = {x}, collections.deque([x]), None
        while q and dest is None:
            y = q.popleft()
            for t in list(R[y]['_exits'].values()) + list(R[y]['_named_exits'].values()):
                if t in R and t not in seen:
                    if t in new_rooms:
                        dest = t
                        break
                    seen.add(t)
                    q.append(t)
        if dest is None and r['_zone'] in [area_zone[a] for a in areas]:
            dest = min((g for g, rr in new_rooms.items() if rr.get('_zone') == r['_zone']), default=None)
        if dest is not None:
            renumber[x] = dest

    # exits of kept rooms of ours that lead to rooms now gone: re-pointed or dropped
    for v, r in new_rooms.items():
        for d, ex in list((r.get('exits') or {}).items()):
            t = ex.get('to_room') if isinstance(ex, dict) else None
            if t is None or t in new_rooms:
                continue
            if r.get('_annex') or v not in game.values():
                r['exits'].pop(d)
                notes['dangling exits of our rooms dropped'] += 1
    # an exit of ours into an atlas room that does not lead back (other than a hookup): dropped
    atlas_vnums = set(game.values())
    hook_set = {(inside, OPP[d]) for at, d, inside in hooked} | {(e, OPP[d]) for at, d, e in attach_ways}
    for v, r in new_rooms.items():
        if v in atlas_vnums:
            continue
        for d, ex in list((r.get('exits') or {}).items()):
            t = ex.get('to_room') if isinstance(ex, dict) else None
            if t in atlas_vnums and (v, d) not in hook_set:
                back = (new_rooms[t].get('exits') or {})
                if not any(isinstance(e, dict) and e.get('to_room') == v for e in back.values()):
                    r['exits'].pop(d)
                    notes['one-way leftovers into the atlas dropped'] += 1
    # terrain set by hand where both the atlas and our old world had it wrong (overrides.json "sectors")
    for v, sector in (ov.get('sectors') or {}).items():
        if int(v) in new_rooms:
            new_rooms[int(v)]['sector_type'] = sector
            notes['sectors set by hand'] += 1
    # ways the atlas lost that the area's original files have (overrides.json "exits": {room: {dir: room}})
    for v, ways in (ov.get('exits') or {}).items():
        r = new_rooms.get(int(v))
        for d, t in (ways or {}).items():
            if r is not None and int(t) in new_rooms and d not in (r.get('exits') or {}):
                r.setdefault('exits', {})[d] = {'to_room': int(t)}
                notes['ways restored from the original areas'] += 1

    # ---- zones: names, fields, prototypes, sealed marks
    new_zones = {}
    for area, z in area_zone.items():
        meta = AREAS[area]
        new_zones[z] = {'number': z, 'name': meta['name'], 'builders': meta['builder'] or '',
                        'atlas_area': area, 'rooms': {}, 'mobs': {}, 'objects': {}}
        if area in sealed_area:
            new_zones[z]['sealed'] = True
    # a name of our own where the atlas's does not fit the rooms the zone ends up with (overrides.json "zone_names")
    for z, name in (ov.get('zone_names') or {}).items():
        if int(z) in new_zones:
            new_zones[int(z)]['name'] = name
    for z, v in ztab.items():
        if v['status'] in ('ours-only', 'internal'):
            src = {k: copy.deepcopy(val) for k, val in zones[z].items() if not k.startswith('_') and k != 'rooms'}
            src['rooms'] = {}
            new_zones[z] = src
    # where each zone of ours went (its prototypes and zone-wide data follow)
    successor = {}
    for z in zones:
        if z in new_zones and (ztab[z]['status'] in ('ours-only', 'internal') or z in area_zone.values()):
            successor[z] = z
            continue
        took = collections.Counter(new_rooms[pair[a]]['_zone'] for a in pair if R[pair[a]]['_zone'] == z and pair[a] in new_rooms)
        took.update(new_rooms[a_v]['_zone'] for o, a in moves.items() if R[o]['_zone'] == z for a_v in [game[a]])
        successor[z] = took.most_common(1)[0][0] if took else min(area_zone.values())
    for z, data in zones.items():
        s = successor[z]
        tgt = new_zones[s]
        for key in ('mobs', 'objects', 'mobiles'):
            if data.get(key):
                tgt.setdefault(key, {})
                for k, val in data[key].items():
                    tgt[key].setdefault(k, copy.deepcopy(val))
        if s != z or ztab[z]['status'] not in ('ours-only', 'internal'):
            for key in ZONE_FIELDS:
                if key in data and key not in tgt:
                    tgt[key] = copy.deepcopy(data[key])
            if data.get('resets'):
                tgt.setdefault('resets', [])
                for rs in data['resets']:
                    rs = copy.deepcopy(rs)
                    for rk in ('room', 'room_vnum'):
                        if rk in rs and rs[rk] not in new_rooms:
                            rs[rk] = renumber.get(rs[rk], rs[rk])
                    tgt['resets'].append(rs)

    # ---- rooms only immortals may be in
    for v, r in new_rooms.items():
        if r.get('_zone') in IMM_ONLY_ZONES:
            r['flags'] = sorted(set(r.get('flags') or []) | {'imm_only'})

    # ---- the connection pass over open rooms: first over all of them (the God Rooms get their
    #      way in), then over what mortals may walk, so nothing they need lies only through a
    #      room closed to them
    sealed_zones = {z for z, d in new_zones.items() if d.get('sealed')}
    for v, r in new_rooms.items():
        r['_zone'] = r.get('_zone')
    open_vnums = {v for v, r in new_rooms.items() if r['_zone'] not in sealed_zones and r['_zone'] not in (0, 97)}
    old = {x: {'exits': {d: {'to_room': t} for d, t in list(r['_exits'].items()) + list(r['_named_exits'].items())}}
           for x, r in R.items()}
    # ways an earlier build's pass added stay (descriptions speak of them; opening a zone must not
    # take a road away): kept when both rooms are still here and the way is free
    kept = []
    prev = os.path.join(OUT_DIR, 'connections.json')
    if os.path.exists(prev):
        with open(prev, encoding='utf-8') as f:
            for c in json.load(f).get('added') or []:
                a, d, b = c.get('from'), c.get('dir'), c.get('to')
                if a in new_rooms and b in new_rooms and d not in (new_rooms[a].get('exits') or {}):
                    connect.add_exit(new_rooms, a, d, b, c.get('why') or 'kept from an earlier build', kept)
    added, cut = connect.connect(new_rooms, open_vnums, old, renumber)
    added = kept + added
    mortal = {v for v in open_vnums if 'imm_only' not in (new_rooms[v].get('flags') or [])}
    added_m, cut_m = connect.connect(new_rooms, mortal, old, renumber)
    added, cut = added + added_m, set(cut) | set(cut_m)

    # ---- placeholders, Garathorm, files
    for v, r in new_rooms.items():
        if r.pop('_needs_placeholder', False) or not (r.get('description') or '').strip():
            r['description'] = placeholder(r, r.get('sector_type', 'inside'), v, None)
            r['placeholder'] = True
    # the build-out: hand-written rooms, creatures and items (world/buildout, tools/atlas/buildout.py)
    built = buildout.apply(new_zones, new_rooms, write=write)
    for v, r in new_rooms.items():
        z = r.pop('_zone')
        r.pop('_annex', None)
        new_zones[z]['rooms'][str(v)] = garathorm(r) if not isinstance(r.get('name'), str) or True else r
    for z, data in new_zones.items():
        data['name'] = garathorm(data['name'])
        for key in ('mobs', 'objects', 'mobiles'):
            if key in data:
                data[key] = garathorm(data[key])

    summary = {
        'zones': len(new_zones), 'sealed': len(sealed_zones), 'rooms': len(new_rooms),
        'placeholders': sum(1 for r in new_rooms.values() if r.get('placeholder')),
        'connections added': len(added), 'still cut off': len(cut), 'renumbered': len(renumber),
        'hookups': len(hooked), 'annex ways': len(attach_ways), **notes,
        **{f'build-out {k}': n for k, n in built.items()},
    }
    if write:
        old_files = set(glob.glob(os.path.join(ZONES_DIR, 'zone_*.json')))
        written = set()
        for z, data in sorted(new_zones.items()):
            path = os.path.join(ZONES_DIR, f'zone_{z:03d}.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=1, ensure_ascii=False)
                f.write('\n')
            written.add(path)
        for path in old_files - written:
            os.remove(path)
        with open(os.path.join(OUT_DIR, 'connections.json'), 'w', encoding='utf-8') as f:
            json.dump({'_about': 'Exits the connection pass added beyond the atlas (tools/atlas/connect.py), with why; '
                                 'hookups and annex ways are in zones.json and rooms.json.',
                       'added': added, 'still_cut_off': sorted(cut)}, f, indent=1)
        with open(os.path.join(OUT_DIR, 'renumber.json'), 'w', encoding='utf-8') as f:
            json.dump({'_about': 'Rooms of ours that are gone, and the room that stands in for each (references follow).',
                       'rooms': {str(k): v for k, v in sorted(renumber.items())}}, f, indent=1)
    return summary, cut, added


def main():
    write = '--check' not in sys.argv
    summary, cut, added = build(write=write)
    for k, v in summary.items():
        print(f'{k}: {v}')
    if cut:
        print('still cut off (first 20):', sorted(cut)[:20])
    why = collections.Counter(a['why'] for a in added)
    print('connections by reason:', dict(why))
    print('written' if write else '(check only: nothing written)')


if __name__ == '__main__':
    main()
