"""The Bedlam atlas, imported and matched to our world (Push 25: nothing in the game changes).

The import keeps every area, room, exit and door of the owner's atlas; every atlas room gets one
game vnum and no two share one; a room the atlas shares with us keeps our vnum; every room of ours
is accounted for once (on the atlas, left over, moved from a similar zone, or in a zone the atlas
lacks); each zone of ours off the atlas joins it at a free side, never one given twice; and the
index covers every zone.

    python3 tests/test_atlas.py
"""
import collections
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'atlas'))
from common import PRE_RELAY_REV, load_atlas, load_world  # noqa: E402

failures = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        failures.append(msg)


def main():
    # the tools run clean, into a scratch folder: the atlas, re-read, and the match, re-run on our
    # world as it was before the re-lay, come out exactly as committed
    import tempfile
    tmp = tempfile.mkdtemp(prefix='atlas-')
    env = dict(os.environ, ATLAS_OUT=tmp)
    for tool in ('extract.py', 'match.py', 'index.py'):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'atlas', tool)], capture_output=True, text=True, env=env)
        check(r.returncode == 0, f'tools/atlas/{tool} runs ({(r.stderr or r.stdout).strip()[-160:]})')
    for name in ('bedlam.json', 'rooms.json', 'zones.json', 'vnums.json'):
        same = open(os.path.join(tmp, name)).read() == open(os.path.join(ROOT, 'world', 'atlas', name)).read()
        check(same, f'{name} comes out exactly as committed')

    atlas = load_atlas()
    A = atlas['rooms']
    exits = sum(len(r['exits']) for r in A.values())
    doors = sum(len(r.get('doors', {})) for r in A.values())
    check((len(atlas['areas']), len(A), exits, doors) == (91, 8038, 18664, 669),
          f'the import keeps 91 areas, 8,038 rooms, 18,664 exits and 669 doors ({len(atlas["areas"])}, {len(A)}, {exits}, {doors})')
    check(all(d in ('north', 'east', 'south', 'west', 'up', 'down') for r in A.values() for d in r['exits']),
          'atlas exits are compass and up/down only, as the game has')
    check(all(t in A for r in A.values() for t in r['exits'].values()), 'no atlas exit leads nowhere')
    check(A[3001]['name'] == 'The Temple Of Garathorm' and A[3001]['exits'].get('south') == 3005,
          'the temple is where the atlas puts it')

    zones, ours = load_world(PRE_RELAY_REV)        # our world as it was before the re-lay
    rooms = json.load(open(os.path.join(ROOT, 'world', 'atlas', 'rooms.json')))
    zj = json.load(open(os.path.join(ROOT, 'world', 'atlas', 'zones.json')))
    vn = json.load(open(os.path.join(ROOT, 'world', 'atlas', 'vnums.json')))
    rows = {int(k): v for k, v in rooms['atlas'].items()}
    check(set(rows) == set(A) and set(int(k) for k in vn) == set(A), 'every atlas room has a row and a game vnum')
    games = [v['game'] for v in rows.values()]
    check(len(games) == len(set(games)), 'no two atlas rooms share a game vnum')
    paired = {a: v['ours'] for a, v in rows.items() if v.get('ours') is not None}
    check(all(rows[a]['game'] == o for a, o in paired.items()), 'a room the atlas shares with us keeps our vnum')
    check(len(set(paired.values())) == len(paired), 'no room of ours is paired twice')
    check(len(paired) > 1000, f'over a thousand atlas rooms are ours already ({len(paired)})')

    # every room of ours, once
    status = {int(z): v['status'] for z, v in zj['zones'].items()}
    orphans = {int(k) for k in rooms['orphans']}
    where = collections.Counter()
    for v, r in ours.items():
        z = r['_zone']
        places = (v in set(paired.values())) + (v in orphans) + (status[z] in ('similar', 'ours-only', 'internal') and v not in set(paired.values()))
        where[places] += 1
    check(where.get(1, 0) == len(ours) and len(ours) == 3012,
          f'each of our 3,012 rooms is accounted for once: on the atlas, left over, or in a zone kept or replaced ({dict(where)})')
    # an orphan game vnum is not reused by a different atlas room (references to it stay ours)
    taken_by_atlas = {g for g in games}
    check(not any(v in taken_by_atlas and v not in paired.values() and not any(rows[a]['game'] == v and rows[a].get('takes_content_of') for a in rows)
                  for v in orphans), 'a room of ours left over does not lend its number to a different atlas room')

    # hookups: free sides, none given twice, the room of ours has the way back free
    used = collections.Counter()
    bad = []
    for z, hs in zj['hookups'].items():
        for h in hs:
            if not h.get('atlas_room'):
                continue
            a, d = h['atlas_room'], h['dir']
            used[(a, d)] += 1
            if d in A[a]['exits']:
                bad.append((z, a, d))
    for c in rooms['orphan_clusters'].values():
        if c.get('attach_atlas'):
            used[(c['attach_atlas'], c['dir'])] += 1
            if c['dir'] in A[c['attach_atlas']]['exits']:
                bad.append(('annex', c['attach_atlas'], c['dir']))
    check(not bad, f'every hookup and annex joins at a side the atlas leaves free ({bad[:3]})')
    check(all(n == 1 for n in used.values()), 'no side is given twice')
    unplaced = [(z, h) for z, hs in zj['hookups'].items() for h in hs if h['how'] == 'unplaced']
    check(not unplaced, f'every zone of ours off the atlas has a way in ({unplaced[:2]})')
    hooked = {int(z) for z, hs in zj['hookups'].items() if any(h.get('atlas_room') for h in hs)}
    check({186, 260, 120}.isdisjoint({z for z, s in status.items() if s == 'ours-only'} - hooked) and 186 in hooked,
          'the Newbie Zone and the housing district join the atlas world')
    nb = next(h for h in zj['hookups']['186'] if h.get('atlas_room'))
    check(nb['how'] == 'same place' and A[nb['atlas_room']]['name'] == 'The Great Field Of Garathorm',
          'the Newbie Zone stays where it was, off the Great Field')

    # the index, of the world as built
    idx = json.load(open(os.path.join(ROOT, 'world', 'atlas', 'index.json')))
    covered = {e['atlas_area'] for e in idx['zones'].values() if e['atlas_area'] is not None}
    check(covered == set(atlas['areas']), f'the index has a zone for every atlas area ({len(covered)} of {len(atlas["areas"])})')
    check(sum(1 for e in idx['zones'].values() if e['atlas_area'] is None) == sum(1 for s in status.values() if s == 'ours-only'),
          'and every zone of ours off the atlas')
    doc = open(os.path.join(ROOT, 'docs', 'world', 'ATLAS_INDEX.md')).read()
    missing = [e['name'] for e in idx['zones'].values() if f"### {e['name']} (zone" not in doc]
    check(not missing, f'the readable index has a section for every zone ({missing[:3]})')
    check(not idx['queue'] or not idx['zones'][str(idx['queue'][0])]['state'].startswith('sealed'),
          f"the build queue is empty or starts with an open zone ({len(idx['queue'])} queued)")
    conn = [e for e in idx['zones'].values() if e['state'] == 'open (connector)']
    check(len(conn) == len(json.load(open(os.path.join(ROOT, 'world', 'atlas', 'overrides.json')))['connectors']),
          f'every connector the owner named is open ({len(conn)})')
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
