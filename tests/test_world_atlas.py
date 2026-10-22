"""The world re-laid on the Bedlam atlas (Push 27), checked: every room connects as it should.

- Every atlas room is there with its atlas name, at its game vnum, with every one of its exits
  (direction and target); nothing else is added except the reviewed hookups, the annexes' ways
  and the connection pass's ways (world/atlas/connections.json), each with a reason.
- Nothing leads nowhere; two rooms never share a cell on a zone's map.
- Every open room can be reached from the temple and walked back from (death traps excepted);
  sealed zones are barred at every way in.
- Every shop, trainer, guildmaster, stable, travel point and quest place can be reached; with the
  water rule on, a boat can be bought or found on foot before any water.
- Every room the code, the quests and the tests name still exists.

    python3 tests/test_world_atlas.py
"""
import asyncio
import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'atlas'))
from common import load_atlas  # noqa: E402

failures = []
OPP = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east', 'up': 'down', 'down': 'up'}
WATER = ('water_swim', 'water_noswim', 'water_surface')
SERVICE = {'shopkeeper', 'guildmaster', 'trainer', 'auctioneer', 'stable_master', 'arena_master',
           'real_estate', 'sage_aldric'}


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        failures.append(msg)


def bfs(start, nxt):
    seen, q = {start}, collections.deque([start])
    while q:
        x = q.popleft()
        for y in nxt(x):
            if y not in seen:
                seen.add(y)
                q.append(y)
    return seen


async def main():
    import logging
    logging.disable(logging.WARNING)
    from config import Config
    from world import World
    import doors
    import map_system as ms
    atlas = load_atlas()
    A = atlas['rooms']
    vn = {int(k): v for k, v in json.load(open(os.path.join(ROOT, 'world', 'atlas', 'vnums.json'))).items()}
    zj = json.load(open(os.path.join(ROOT, 'world', 'atlas', 'zones.json')))
    rj = json.load(open(os.path.join(ROOT, 'world', 'atlas', 'rooms.json')))
    conn = json.load(open(os.path.join(ROOT, 'world', 'atlas', 'connections.json')))
    world = World(Config())
    await world.load()
    W = world.rooms

    # ---- the atlas, room by room and exit by exit
    incoming = collections.Counter(t for r in A.values() for t in r['exits'].values())
    stubs = {a for a, r in A.items() if not (r['name'] or '').strip() and not r['exits'] and not incoming[a]}
    missing = [a for a in A if a not in stubs and vn[a] not in W]
    check(not missing, f'every atlas room is in the world at its game vnum ({len(missing)} missing: {missing[:5]})')
    misnamed = [a for a in A if a not in stubs and vn[a] in W and (A[a]['name'] or 'A Nameless Place').replace('Midgaard', 'Garathorm') != W[vn[a]].name]
    check(not misnamed, f'every atlas room has its atlas name ({misnamed[:3]})')
    wrong = []
    for a, r in A.items():
        if a in stubs:
            continue
        room = W[vn[a]]
        for d, t in r['exits'].items():
            ex = room.exits.get(d)
            if not isinstance(ex, dict) or ex.get('to_room') != vn[t]:
                wrong.append((a, d, t))
    check(not wrong, f'every atlas exit goes the way the atlas says ({len(wrong)} wrong: {wrong[:3]})')

    # ---- nothing added without a reason
    allowed = {(c['from'], c['dir']) for c in conn['added']}
    for z, hs in zj['hookups'].items():
        for h in hs:
            if h.get('atlas_room'):
                allowed.add((vn[h['atlas_room']], h['dir']))
                allowed.add((h['zone_room'], OPP[h['dir']]))
    for c in rj['orphan_clusters'].values():
        if c['kind'] == 'annex' and c.get('attach_atlas'):
            allowed.add((vn[c['attach_atlas']], c['dir']))
            allowed.add((c['entry'], OPP[c['dir']]))
    # ways restored from an area's original files (world/atlas/overrides.json "exits")
    with open(os.path.join(ROOT, 'world', 'atlas', 'overrides.json'), encoding='utf-8') as f:
        for v, ways in (json.load(f).get('exits') or {}).items():
            allowed |= {(int(v), d) for d in ways}
    atlas_vnums = {vn[a] for a in A if a not in stubs}
    extra = []
    for a, r in A.items():
        if a in stubs:
            continue
        v = vn[a]
        for d, ex in W[v].exits.items():
            # (open ground joins side-by-side outdoor rooms of an opened zone: wilds.py)
            if d not in r['exits'] and (v, d) not in allowed and not ex.get('wild'):
                extra.append((v, d, ex.get('to_room')))
    check(not extra, f'no exit beyond the atlas without a reason ({len(extra)}: {extra[:3]})')
    check(not conn['still_cut_off'], f"the connection pass left nothing cut off ({conn['still_cut_off'][:5]})")

    # ---- nothing leads nowhere; unique cells
    dangling = [(v, d) for v, r in W.items() for d, ex in r.exits.items() if isinstance(ex, dict) and ex.get('to_room') not in W]
    check(not dangling, f'no exit leads nowhere ({dangling[:3]})')
    probs = [p for p in ms.check_stored_cells(world) if 'share the cell' in p]
    check(not probs, f'no two rooms share a cell on a zone map ({probs[:2]})')

    # ---- reachable from the temple, and back: by mortals over the rooms they may walk (never
    #      through the God Rooms), and by immortals into the God Rooms too
    sealed = {z.number for z in world.zones.values() if getattr(z, 'sealed', False)}
    all_open = {v for v, r in W.items() if r.zone is not None and r.zone.number not in sealed and r.zone.number not in (0, 97)}
    gods = {v for v in all_open if 'imm_only' in W[v].flags}
    open_rooms = all_open - gods
    deadly = {v for v in open_rooms if W[v].flags & {'deathtrap', 'death'}}

    # a ferry or a barge (rites.py tolls) carries a body across a way it cannot walk: a way through
    import rites
    carried = collections.defaultdict(list)
    for t in rites.DATA.get('tolls', []):
        carried[t['room']].append(t['to'])
        if t.get('via'):
            carried[t['room']].append(t['via'])          # the boat, mid-crossing
            carried[t['via']].append(t['to'])

    def walker(rooms):
        def fwd(v):
            return [ex['to_room'] for ex in W[v].exits.values() if isinstance(ex, dict) and ex.get('to_room') in rooms
                    and not doors.is_seal(ex.get('door'))] + [t for t in carried.get(v, ()) if t in rooms]
        rev = collections.defaultdict(set)
        for v in rooms:
            for t in fwd(v):
                rev[t].add(v)
        return fwd, bfs(3001, fwd), bfs(3001, lambda v: rev[v])
    fwd, reach, back = walker(open_rooms)
    _, reach_all, back_all = walker(all_open)
    cut = sorted((open_rooms - reach) - deadly)
    trapped = sorted((reach - back) - deadly)
    check(not cut, f'every open room can be reached from the temple ({len(cut)} cannot: {cut[:6]})')
    check(not trapped, f'and walked back from ({len(trapped)} cannot: {trapped[:6]})')
    # a death trap kills whoever walks in and turns back whoever catches themself (commands.py), so
    # nobody passes through one: a room behind a death trap is a room nobody reaches or leaves
    _, reach_safe, back_safe = walker(open_rooms - deadly)
    behind = sorted(((reach & back) - deadly) - (reach_safe & back_safe))
    check(not behind, f'and no death trap stands in the way ({len(behind)} only through one: {behind[:6]})')
    zone12 = {v for v, r in W.items() if r.zone is not None and r.zone.number == 12}
    check(zone12 and zone12 == gods, f'the God Rooms, and only they, are for immortals only ({sorted(zone12 ^ gods)[:5]})')
    check(gods <= reach_all and gods <= back_all, f'an immortal reaches the God Rooms and walks back ({sorted(gods - (reach_all & back_all))})')
    barred = [(v, d) for v, r in W.items() for d, ex in r.exits.items()
              if isinstance(ex, dict) and ex.get('room') is not None and ex['room'].zone is not None
              and ex['room'].zone.number in sealed and r.zone is not None and r.zone.number not in sealed
              and not doors.is_seal(ex.get('door'))]
    check(not barred, f'every way into a sealed zone is barred ({barred[:3]})')
    def unbuilt(z):         # a zone file still carrying placeholder rooms
        with open(os.path.join(ROOT, 'world', 'zones', f'zone_{z:03d}.json'), encoding='utf-8') as f:
            rooms = json.load(f).get('rooms') or {}
        return any(r.get('placeholder') for r in (rooms.values() if isinstance(rooms, dict) else rooms))
    built_sealed = sorted(z for z in sealed if not unbuilt(z))
    check(not built_sealed, f'a zone stays sealed only while it is unbuilt ({len(sealed)} sealed; built yet sealed: {built_sealed})')

    # ---- what matters can be reached (on foot, or with a boat found on foot first)
    important = set()
    for v, r in W.items():
        for reset in r.mob_resets or []:
            mob = world.mob_prototypes.get(reset.get('vnum') if isinstance(reset, dict) else reset) or {}
            if isinstance(mob.get('special'), str) and mob['special'] in SERVICE:
                important.add(v)
    import travel
    important |= {d['vnum'] for d in travel.WAYPOINTS.values()}
    important |= {int(m) for m in re.findall(r"'room':\s*(\d+)", open(os.path.join(ROOT, 'src', 'marquee_quests.py')).read())}
    unreach_imp = sorted(v for v in important if v in W and v not in reach and W[v].zone.number not in sealed)
    check(not unreach_imp, f'every shop, trainer, stable, travel point and quest place can be reached ({unreach_imp[:5]})')

    def on_foot(v):
        return [t for t in fwd(v) if not (W[t].sector_type in WATER and W[v].sector_type not in WATER)]
    land = bfs(3001, on_foot)
    boats = {v for v, o in world.obj_prototypes.items() if (o.get('item_type') or o.get('type')) == 'boat'}
    sources = set()
    for v, r in W.items():
        for reset in r.obj_resets or []:
            if (reset.get('vnum') if isinstance(reset, dict) else reset) in boats:
                sources.add(v)
        for reset in r.mob_resets or []:
            mob = world.mob_prototypes.get(reset.get('vnum') if isinstance(reset, dict) else reset) or {}
            sells = (mob.get('shop_config') or {}).get('sells') if isinstance(mob.get('shop_config'), dict) else []
            if mob.get('special') == 'shopkeeper' and boats & {int(x) for x in (sells or []) if str(x).isdigit()}:
                sources.add(v)
    check(sources & land, f'a raft can be bought or found on foot from the temple ({sorted(sources & land)[:4]})')

    # ---- every room the code, quests and tests name still exists
    renum = json.load(open(os.path.join(ROOT, 'world', 'atlas', 'renumber.json')))['rooms']
    gone = {int(k) for k in renum}
    named = []
    files = glob.glob(os.path.join(ROOT, 'src', '*.py')) + glob.glob(os.path.join(ROOT, 'world', 'quests', '*.json')) + \
        glob.glob(os.path.join(ROOT, 'tests', '*.py'))
    for f in files:
        for i, line in enumerate(open(f, encoding='utf-8', errors='ignore'), 1):
            if not re.search(r'room|goto|recall|start|temple|travel|dest|location|portal|to_room', line, re.I):
                continue
            for m in re.finditer(r'(?<![\d.])(\d{4,5})(?![\d.])', line):
                n = int(m.group(1))
                if n in gone and n not in W:
                    named.append(f'{os.path.relpath(f, ROOT)}:{i} {n}')
    check(not named, f'every room the code, quests and tests name still exists ({named[:4]})')

    # ---- a saved place in a room that is gone lands in its stand-in, which is open and reached
    #      (a stand-in in the God Rooms by an immortal: login sends a mortal to their recall room)
    from world import renumbered
    bad_stand = sorted(int(k) for k, t in renum.items()
                       if (t not in reach and not (t in gods and t in reach_all)) or int(k) in W)
    check(not bad_stand, f'every gone room has a stand-in you can walk to ({bad_stand[:5]})')
    check(renumbered(3500) == renum['3500'] and renumbered(3001) == 3001 and renumbered(None) is None,
          'renumbered() gives the stand-in for a gone room and leaves the rest alone')
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
