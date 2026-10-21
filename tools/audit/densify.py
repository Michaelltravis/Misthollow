#!/usr/bin/env python3
"""Fill the thin zones (tools/audit/density.py): more of each zone's own ordinary creatures, in its
empty rooms near where they already live, written as "fill" entries in world/population/zone_<n>.json
(population.py applies them at load).

    python3 tools/audit/densify.py              # what it would add, zone by zone
    python3 tools/audit/densify.py --write      # write the fill entries

Rules:
- only adventuring zones the audit calls sparse (fewer than SPARSE hostile creatures per walkable
  room); the target is TARGET per walkable room, TRAVEL_TARGET on a road or open plain between places;
- only the zone's own ordinary hostile creatures: aggressive, no rank above regular, not a boss,
  not a sentinel or a shopkeeper, not one of a kind (a name, or "the ..." -- one of those stays one);
- a room gets one only if it is walkable, holds no hostile creature, is not peaceful, a death trap,
  a god room or a shop; a creature of the water goes to the water and a creature of the land to
  the land;
- each creature fills the empty rooms nearest the rooms it already lives in (no farther than
  REACH steps), the zone's creatures taking turns, so the mix stays the zone's own.
"""
import argparse
import asyncio
import collections
import json
import logging
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import density  # noqa: E402

ROOT = density.ROOT
POP = os.path.join(ROOT, 'world', 'population')
TARGET = 0.45
TRAVEL_TARGET = 0.25     # a road or open plain between places: fewer fights on the way
REACH = 10
WATER = {'water_swim', 'water_noswim', 'underwater'}
BARRED = {'peaceful', 'no_mob', 'death', 'deathtrap', 'imm_only', 'godroom', 'god_room', 'gods_only'}
ONE_OF_A_KIND = re.compile(r'^(the|[A-Z])')


def existing_file(z):
    """The zone's population file, whatever its name (zone_66.json, zone_466.json): two files for
    one zone would overwrite each other at load."""
    for name in sorted(os.listdir(POP)):
        if name.startswith('zone_') and name.endswith('.json'):
            try:
                if int(json.load(open(os.path.join(POP, name), encoding='utf-8')).get('zone')) == z:
                    return os.path.join(POP, name)
            except Exception:
                continue
    return None


def ordinary(proto):
    flags = set(proto.get('flags') or [])
    if 'aggressive' not in flags or flags & {'boss', 'sentinel', 'no_attack', 'shopkeeper'}:
        return False
    if proto.get('rank') not in (None, 'regular') or proto.get('special') or proto.get('shop'):
        return False
    return not ONE_OF_A_KIND.match(str(proto.get('short_desc') or 'x').strip())


def exits_of(room):
    for ex in (getattr(room, 'exits', None) or {}).values():
        t = ex.get('room') if isinstance(ex, dict) else None
        if t is None and isinstance(ex, dict) and ex.get('to_room') is not None:
            t = room.world.rooms.get(ex['to_room']) if hasattr(room, 'world') else None
        if t is not None:
            yield t


def plan(world, zones):
    out = {}
    for z, s in zones.items():
        if not s['sparse']:
            continue
        rooms = {v: r for v, r in world.rooms.items() if getattr(getattr(r, 'zone', None), 'number', None) == z}
        homes = collections.defaultdict(set)
        hostile_rooms = set()
        for v, r in rooms.items():
            for m in r.mob_resets or []:
                mv = int(m.get('vnum', -1)) if isinstance(m, dict) else int(m)
                p = world.mob_prototypes.get(mv)
                if p is None:
                    continue
                if 'aggressive' in (p.get('flags') or []) or p.get('rank') in ('elite', 'sub-boss', 'boss'):
                    hostile_rooms.add(v)
                if ordinary(p):
                    homes[mv].add(v)
        # a creature the zone's population places by design (a guard post, a boss) keeps its number
        pop = (world._population or {}).get(z, {}) if hasattr(world, '_population') else {}
        # (a guard post is a few rooms; a spawn over many rooms is the kind's spread, and a patrol kind may also stand about)
        placed = {int(x['vnum']) for x in (pop.get('bosses') or []) + (pop.get('lairs') or [])} | \
            {int(x['vnum']) for x in (pop.get('spawns') or []) if len(x.get('rooms') or []) <= 3}
        for mv in placed:
            homes.pop(mv, None)
        # a zone's own regulars written for it in its population file ("fills": a zone that had no
        # ordinary foe): they may stand anywhere open in it, spread evenly
        recruits = {int(v): c for v, c in ((pop.get('creatures') or {}).items()) if isinstance(c, dict) and c.get('fills')}
        if not homes and not recruits:
            out[z] = {'skip': 'no ordinary hostile creature to fill with'}
            continue

        # a zone that keeps its creatures in place with no_mob rooms (a wizard's house, every room
        # barred to wanderers) may still have them placed there ("fill_no_mob" in its population)
        barred = BARRED - {'no_mob'} if pop.get('fill_no_mob') else BARRED

        def open_room(r):
            flags = set(getattr(r, 'flags', None) or [])
            return (r.vnum not in hostile_rooms and not (flags & barred) and getattr(r, 'sector_type', '') not in density.DEEP - WATER
                    and not any(getattr(c, 'special', None) == 'shopkeeper' for c in r.characters))
        free = {v for v, r in rooms.items() if open_room(r)}
        travel = s['travel']          # (density.is_travel: the audit and the fill agree)
        need = max(0, math.ceil((TRAVEL_TARGET if travel else TARGET) * s['walk']) - s['hostile'])
        # nearest free rooms to each creature's homes (water to water, land to land)
        reach = {}
        for mv, c in recruits.items():
            wet = bool(c.get('water'))
            spots = [v for v in sorted(free) if (getattr(rooms[v], 'sector_type', '') in WATER) == wet]
            # every other open room first, so they spread out rather than bunch
            reach[mv] = spots[::2] + spots[1::2]
            homes.setdefault(mv, set())
        for mv, hs in homes.items():
            if mv in reach:
                continue
            wet = all(getattr(rooms[h], 'sector_type', '') in WATER for h in hs)
            dist, frontier = {h: 0 for h in hs}, list(hs)
            while frontier:
                nxt = []
                for v in frontier:
                    for t in exits_of(rooms[v]):
                        if t.vnum in rooms and t.vnum not in dist and dist[v] < REACH:
                            dist[t.vnum] = dist[v] + 1
                            nxt.append(t.vnum)
                frontier = nxt
            reach[mv] = [v for v, _ in sorted(dist.items(), key=lambda kv: (kv[1], kv[0]))
                         if v in free and (getattr(rooms[v], 'sector_type', '') in WATER) == wet]
        added = collections.defaultdict(list)
        taken = set()
        order = sorted(homes, key=lambda mv: -len(homes[mv]))
        while need > 0:
            moved = False
            for mv in order:
                if need <= 0:
                    break
                pick = next((v for v in reach[mv] if v not in taken), None)
                if pick is None:
                    continue
                taken.add(pick)
                added[mv].append(pick)
                need -= 1
                moved = True
            if not moved:
                break
        cur = collections.Counter()
        for c in world.npcs:
            if getattr(c, 'vnum', None) in homes and c.room is not None and c.room.vnum in rooms:
                cur[c.vnum] += 1
        out[z] = {'fill': [{'vnum': mv, 'rooms': sorted(rs), 'total': cur[mv] + len(rs),
                            'why': world.mob_prototypes[mv].get('short_desc')} for mv, rs in sorted(added.items())],
                  'short': need}
    return out


async def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    logging.disable(logging.WARNING)
    os.environ['MH_NO_FILL'] = '1'          # plan from the world as written, not as last filled
    from config import Config
    from world import World
    world = World(Config())
    await world.load()
    for r in world.rooms.values():
        r.world = world
    zones = density.survey(world)
    import population
    world._population = population.load()
    p = plan(world, zones)
    total = 0
    for z, x in p.items():
        s = zones[z]
        if 'skip' in x:
            print(f"{z:>4} {s['name'][:28]:28} skip: {x['skip']}")
            continue
        n = sum(len(f['rooms']) for f in x['fill'])
        total += n
        print(f"{z:>4} {s['name'][:28]:28} {s['hostile']:>4} hostile in {s['walk']:>4} rooms  +{n:<4}"
              f"{'  (short ' + str(x['short']) + ': no more free rooms in reach)' if x['short'] else ''}")
        if a.write and x['fill']:
            path = existing_file(z) or os.path.join(POP, f'zone_{z:03d}.json')
            d = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {'zone': z}
            d['fill'] = x['fill']
            d.setdefault('_about', 'Who lives where (population.py).')
            d['_fill'] = (f'tools/audit/densify.py: {n} more of the zone\'s own ordinary creatures in its empty rooms, '
                          f'{TARGET} hostile per walkable room as the aim')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(d, f, indent=1, ensure_ascii=False)
                f.write('\n')
    if a.write:
        # a zone the plan no longer fills loses an old fill
        wanted = {z for z, x in p.items() if x.get('fill')}
        for name in sorted(os.listdir(POP)):
            path = os.path.join(POP, name)
            if not (name.startswith('zone_') and name.endswith('.json')):
                continue
            d = json.load(open(path, encoding='utf-8'))
            if 'fill' in d and int(d.get('zone', -1)) not in wanted:
                d.pop('fill', None)
                d.pop('_fill', None)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(d, f, indent=1, ensure_ascii=False)
                    f.write('\n')
    print(f'{total} creatures added over {sum(1 for x in p.values() if x.get("fill"))} zones' + (' (written)' if a.write else ''))


if __name__ == '__main__':
    asyncio.run(main())
