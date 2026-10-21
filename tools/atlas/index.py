"""Index the world laid on the Bedlam atlas: every zone, what it holds, how it joins the rest, and
what it still needs (room descriptions, creatures, items, a boss), with the order to build them
in. Reads the built world (world/zones), the atlas and the approved match; changes nothing in
the game; writes docs/world/ATLAS_INDEX.md and world/atlas/index.json.

    python3 tools/atlas/index.py
"""
import collections
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (ATLAS_DIR, OUT_DIR, ROOT, WATER_SECTORS, carried, is_boss, level_of, load_atlas,  # noqa: E402
                    load_content, load_overrides, load_population, load_world, write_json, zone_boss_vnums)

DOC = os.path.join(ROOT, 'docs', 'world', 'ATLAS_INDEX.md') if OUT_DIR == ATLAS_DIR else os.path.join(OUT_DIR, 'ATLAS_INDEX.md')
SERVICE = {'shopkeeper', 'guildmaster', 'trainer', 'auctioneer', 'stable_master', 'arena_master',
           'real_estate', 'sage_aldric', 'banker', 'innkeeper', 'healer', 'postmaster'}
OPP = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east', 'up': 'down', 'down': 'up'}


def band(levels):
    if not levels:
        return None
    levels = sorted(levels)
    return {'min': levels[0], 'median': int(statistics.median(levels)), 'max': levels[-1]}


def band_text(b, suggested=False):
    if not b:
        return '?'
    return f"{b['min']}-{b['max']} (median {b['median']})" + (' suggested' if suggested else '')


def main():
    atlas = load_atlas()
    A, AREAS = atlas['rooms'], atlas['areas']
    zones, W = load_world()                    # the world as built
    placed, MOBS, OBJS = load_content(zones)
    # and who world/population adds when the game loads (creatures, bosses): the zone files alone
    # called Garathorm's wall and cathedral empty
    pop_bosses, NO_BOSS = load_population(placed, MOBS, OBJS)     # (and the zones that want none, and why)
    bosses_by_table = zone_boss_vnums() | pop_bosses
    ov = load_overrides()
    zj = json.load(open(os.path.join(ATLAS_DIR, 'zones.json'), encoding='utf-8'))
    rj = json.load(open(os.path.join(ATLAS_DIR, 'rooms.json'), encoding='utf-8'))
    conn = json.load(open(os.path.join(ATLAS_DIR, 'connections.json'), encoding='utf-8'))
    areas = {int(k): v for k, v in zj['areas'].items()}
    ztab = {int(k): v for k, v in zj['zones'].items()}
    hooks = {int(k): v for k, v in zj['hookups'].items()}
    clusters = {int(k): v for k, v in rj['orphan_clusters'].items()}
    orphans = {int(k): v for k, v in rj['orphans'].items()}
    vn = {int(k): v for k, v in json.load(open(os.path.join(ATLAS_DIR, 'vnums.json'))).items()}
    area_of_zone = {z: d.get('atlas_area') for z, d in zones.items() if d.get('atlas_area') is not None}
    zone_of_area = {a: z for z, a in area_of_zone.items()}
    added_by_zone = collections.defaultdict(list)
    for c in conn['added']:
        if c['from'] in W:
            added_by_zone[W[c['from']]['_zone']].append(c)

    # steps from the temple, walking as a mortal may (never through the God Rooms)
    def imm_only(v):
        return 'imm_only' in (W[v].get('flags') or [])
    dist, q = {3001: 0}, collections.deque([3001])
    while q:
        x = q.popleft()
        for t in list(W[x]['_exits'].values()) + list(W[x]['_named_exits'].values()):
            if t in W and t not in dist and not imm_only(t):
                dist[t] = dist[x] + 1
                q.append(t)

    boats = {v for v, o in OBJS.items() if (o.get('item_type') or o.get('type')) == 'boat'}
    boat_sources = []
    for v, c in placed.items():
        if v not in W:
            continue
        for o in c['objs']:
            if o in boats:
                boat_sources.append({'room': v, 'zone': W[v]['_zone'], 'item': o, 'how': 'lies here',
                                     'name': OBJS[o].get('short_desc') or ''})
        for mv in c['mobs']:
            mob = MOBS.get(mv) or {}
            sc = mob.get('shop_config') if isinstance(mob.get('shop_config'), dict) else {}
            for o in list(sc.get('sells') or []):
                try:
                    o = int(o.get('vnum') if isinstance(o, dict) else o)
                except (TypeError, ValueError):
                    continue
                if o in boats and mob.get('special') == 'shopkeeper':
                    boat_sources.append({'room': v, 'zone': W[v]['_zone'], 'item': o,
                                         'how': f"sold by {mob.get('short_desc') or mob.get('name')}",
                                         'name': OBJS[o].get('short_desc') or ''})

    def zone_entry(z, status, connector, sealed, atlas_area=None):
        vs = sorted(v for v, r in W.items() if r['_zone'] == z)
        mobs = [m for v in vs for m in placed.get(v, {}).get('mobs', [])]
        # items lying in its rooms, and those its creatures carry, wear or drop
        objs = [o for v in vs for o in placed.get(v, {}).get('objs', [])] +             [o for m in mobs for o in carried(MOBS.get(m) or {}) if o in OBJS]
        need = [v for v in vs if W[v].get('placeholder')]
        bosses = sorted({f"{(MOBS.get(m) or {}).get('short_desc') or m} ({m})" for m in mobs
                         if is_boss(m, MOBS.get(m) or {}, bosses_by_table)})
        svc = sorted({(MOBS.get(m) or {}).get('special') for m in mobs
                      if isinstance((MOBS.get(m) or {}).get('special'), str) and (MOBS.get(m) or {}).get('special') in SERVICE})
        links = collections.defaultdict(list)
        oneway, noexit, water = [], [], []
        for v in vs:
            r = W[v]
            if not r['_exits'] and not r['_named_exits']:
                noexit.append(v)
            if r['_sector'] in WATER_SECTORS:
                water.append(v)
            for d, t in r['_exits'].items():
                if t not in W:
                    continue
                if W[t]['_exits'].get(OPP[d]) != v:
                    oneway.append(f'{v} {d} -> {t}')
                if W[t]['_zone'] != z:
                    links[W[t]['_zone']].append(f"{r['_name']} ({v}) {d} to {W[t]['_name']} ({t})")
        locked = []
        if atlas_area is not None:
            for a, ar in A.items():
                if ar['area'] == atlas_area:
                    for d, kind in (ar.get('doors') or {}).items():
                        if kind == 'locked door':
                            locked.append(f'{vn[a]} {d}')
        needs = []
        if need:
            needs.append(f'descriptions for {len(need)} rooms')
        if not mobs:
            needs.append('creatures')
        if not objs:
            needs.append('items')
        if not bosses and len(vs) >= 30 and not connector and z not in NO_BOSS:
            needs.append('a boss')
        return {
            'name': zones[z]['name'], 'zone': z, 'atlas_area': atlas_area, 'status': status,
            'state': ('sealed until built' if sealed else 'immortals only' if vs and all(imm_only(v) for v in vs)
                      else 'open (connector)' if connector else 'open'),
            'rooms': len(vs), 'steps_from_temple': min((dist[v] for v in vs if v in dist), default=None),
            'terrain': collections.Counter(W[v]['_sector'] for v in vs).most_common(3),
            'creatures': len(mobs), 'items': len(objs), 'bosses': bosses, 'services': svc,
            'level_band': band([level_of(MOBS[m]) for m in mobs if m in MOBS]), 'needs': needs,
            'need_description': need, 'links': {str(k): v for k, v in sorted(links.items())},
            'one_way': oneway, 'no_exits': noexit, 'locked_doors_left_unlocked': locked, 'water_rooms': water,
            'connections_added': added_by_zone.get(z, []),
        }

    index = {'_about': 'Generated by tools/atlas/index.py from the built world; docs/world/ATLAS_INDEX.md is the readable form.',
             'zones': {}, 'boat_sources': boat_sources}
    conn_set = set(ov.get('connectors', []))
    for z, d in sorted(zones.items()):
        a = d.get('atlas_area')
        if a is not None:
            meta = areas[a]
            index['zones'][z] = zone_entry(z, meta['status'], a in conn_set, bool(d.get('sealed')), a)
        elif z in ztab and ztab[z]['status'] != 'internal':
            index['zones'][z] = zone_entry(z, 'ours (off the atlas)', False, bool(d.get('sealed')))
    for z, e in index['zones'].items():
        if e['level_band'] is None:
            nb = [index['zones'][int(k)]['level_band'] for k in e['links'] if int(k) in index['zones'] and index['zones'][int(k)]['level_band']]
            if nb:
                med = int(statistics.median(b['median'] for b in nb))
                e['suggested_band'] = {'min': max(1, med - 5), 'median': med, 'max': med + 5}
    rank = {'immortals only': 1, 'sealed until built': 2}      # open zones first, then the gods', then the sealed
    queue = sorted(index['zones'].items(), key=lambda kv: (rank.get(kv[1]['state'], 0),
                                                           kv[1]['steps_from_temple'] if kv[1]['steps_from_temple'] is not None else 10 ** 6))
    index['queue'] = [z for z, e in queue if e['needs']]
    write_json(os.path.join(OUT_DIR, 'index.json'), index)
    write_doc(index, queue, zones, ztab, hooks, clusters, orphans, conn, A, W, boat_sources, vn)
    tot = collections.Counter()
    for e in index['zones'].values():
        tot['need'] += len(e['need_description'])
        tot['open'] += e['state'].startswith('open')
    print(f"index: {len(index['zones'])} zones ({tot['open']} open); {tot['need']} rooms need descriptions; "
          f"{len(conn['added'])} connections added; {len(index['queue'])} zones in the build queue -> {os.path.relpath(DOC, ROOT)}")


def write_doc(index, queue, zones, ztab, hooks, clusters, orphans, conn, A, W, boat_sources, vn):
    L = []
    w = L.append
    Z = index['zones']
    opened = [e for e in Z.values() if e['state'].startswith('open')]
    imm = [e for e in Z.values() if e['state'] == 'immortals only']
    w('# Atlas index: the world on the Bedlam atlas\n')
    w('Generated by `python3 tools/atlas/index.py` from the world as built on the owner\'s atlas '
      '(`world/atlas/bedlam.json`). The full lists are in `world/atlas/index.json`.\n')
    w('## At a glance\n')
    w(f"- **{len(Z)} zones, {sum(e['rooms'] for e in Z.values()):,} rooms.** {len(opened)} are open; "
      f"{len(imm)} for immortals only ({', '.join(e['name'] for e in imm)}); "
      f"{len(Z) - len(opened) - len(imm)} are sealed until built (their ways in are barred).")
    w(f"- **Every open room** can be reached from the temple and walked back from. "
      f"{len(conn['added'])} ways were added to make it so, each with its reason (below).")
    w(f"- **Still to write:** descriptions for {sum(len(e['need_description']) for e in Z.values()):,} rooms "
      f"(placeholders now), {sum(len(e['need_description']) for e in opened):,} of them in open zones.")
    w(f"- **Water** needs a boat or a raft: {sum(len(e['water_rooms']) for e in Z.values()):,} water rooms; "
      f"{len(boat_sources)} places give a boat.\n")

    w('## Build-out queue\n')
    w('Open zones first, nearest the temple first; then the God Rooms (immortals only); then the sealed ones (a sealed zone opens when '
      'it is done: its `"sealed": true` comes off). Done means real descriptions, creatures and '
      'items at its level band, and a boss where it is big enough for one.\n')
    w('| # | zone | state | rooms | steps from temple | levels | needs |')
    w('|---|---|---|---|---|---|---|')
    n = 0
    for z, e in queue:
        if not e['needs']:
            continue
        n += 1
        b = band_text(e['level_band']) if e['level_band'] else band_text(e.get('suggested_band'), True)
        w(f"| {n} | {e['name']} ({z}) | {e['state']} | {e['rooms']} | "
          f"{e['steps_from_temple'] if e['steps_from_temple'] is not None else '—'} | {b} | {'; '.join(e['needs'])} |")
    w('')

    w('## Ways added so every room connects\n')
    why = collections.Counter(c['why'] for c in conn['added'])
    w('What the atlas left unjoined (rooms with no way in, or no way back out) was joined like this; '
      'the full list is in `world/atlas/connections.json`.\n')
    for k, v in why.most_common():
        w(f'- {k}: {v}')
    w('')
    w('| from | way | to | why |')
    w('|---|---|---|---|')
    for c in conn['added']:
        if c['from'] in W and c['to'] in W:
            w(f"| {W[c['from']]['_name']} ({c['from']}) | {c['dir']} | {W[c['to']]['_name']} ({c['to']}) | {c['why']} |")
    w('')

    w('## Our zones off the atlas and where they join it\n')
    w('| zone | joins at | way |')
    w('|---|---|---|')
    for z, hs in sorted(hooks.items()):
        for h in hs:
            if h.get('atlas_room'):
                g = vn[h['atlas_room']]
                w(f"| {ztab[z]['name']} ({z}) | {W[g]['_name'] if g in W else g} ({g}) | {h['dir']} |")
    w('')
    w('## Our rooms the atlas had no room for\n')
    w('| zone | rooms | kept as | joins at |')
    w('|---|---|---|---|')
    def now(text):
        return text.replace('Midgaard', 'Garathorm')
    for cid, c in sorted(clusters.items(), key=lambda kv: (kv[1]['kind'], kv[0])):
        names = ', '.join(f"{W[v]['_name'] if v in W else now(orphans[v]['name'])} ({v})" for v in c['rooms'][:4]) + \
            (' …' if len(c['rooms']) > 4 else '')
        first = c['rooms'][0]
        if first in W:
            zname = zones[W[first]['_zone']]['name']
        else:
            old = orphans[first]['zone']
            zname = 'was ' + now(ztab[old]['name']) if old in ztab else str(old)
        if c.get('attach_atlas'):
            g = vn[c['attach_atlas']]
            where = f"{W[g]['_name'] if g in W else g} ({g}), {c['dir']}"
        elif c.get('beside_atlas'):
            g = vn[c['beside_atlas']]
            where = f"creatures and items to {W[g]['_name'] if g in W else g} ({g})"
        else:
            where = '—'
        w(f"| {zname} | {names} | {c['kind']} | {where} |")
    w('')

    w('## Every zone\n')
    for z, e in sorted(Z.items(), key=lambda kv: kv[1]['name']):
        w(f"### {e['name']} (zone {z}{', atlas ' + str(e['atlas_area']) if e['atlas_area'] is not None else ''})\n")
        w(f"- **{e['status']}**, {e['state']}. {e['rooms']} rooms; " +
          ', '.join(f'{t} {c}' for t, c in e['terrain']) + '.')
        b = band_text(e['level_band']) if e['level_band'] else band_text(e.get('suggested_band'), True)
        w(f"- Creatures {e['creatures']}, items {e['items']}, levels {b}"
          + (f"; bosses: {', '.join(e['bosses'])}" if e['bosses'] else '')
          + (f"; services: {', '.join(e['services'])}" if e['services'] else '') + '.')
        if e['needs']:
            w(f"- **Needs:** {'; '.join(e['needs'])}.")
        if e['links']:
            w('- Joins: ' + '; '.join(f"{Z[int(k)]['name'] if int(k) in Z else 'zone ' + k} ×{len(v)}" for k, v in e['links'].items()) + '.')
        extras = []
        if e['connections_added']:
            extras.append(f"{len(e['connections_added'])} ways added to connect it")
        if e['one_way']:
            extras.append(f"{len(e['one_way'])} one-way exits (as the atlas has them)")
        if e['locked_doors_left_unlocked']:
            extras.append(f"{len(e['locked_doors_left_unlocked'])} doors the atlas locks, unlocked until keys are made")
        if e['water_rooms']:
            extras.append(f"{len(e['water_rooms'])} water rooms (boat or raft)")
        if extras:
            w('- ' + '; '.join(extras) + '.')
        w('')

    w('## Water and boats\n')
    for b in boat_sources:
        w(f"- {b['name']} ({b['item']}): {b['how']}, room {b['room']} ({W[b['room']]['_name']}).")
    w('')
    os.makedirs(os.path.dirname(DOC), exist_ok=True)
    with open(DOC, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
