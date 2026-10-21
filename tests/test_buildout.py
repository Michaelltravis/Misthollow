"""The build-out of the connector zones (Push 29), offline.

Every connector room is written by hand (no placeholder left), each part passes the writers'
check (length, compass words only for real ways out, no sentence twice), and what the build made
of the parts is in the world as it loads: the creatures carry the numbers their level and kind
give, stand where creatures may (on the water only if they live there), and every new item is
dropped by one of them.

    python3 tests/test_buildout.py
"""
import asyncio
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'src'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'atlas'))
import test_webmove as tw  # noqa: E402  (check(), failures)

check, failures = tw.check, tw.failures


async def main():
    import logging
    logging.disable(logging.WARNING)
    import briefs
    import buildout
    from config import Config
    from world import World

    # ---- the parts pass the writers' check
    w = buildout.World()
    parts = sorted(p for p in glob.glob(os.path.join(buildout.PARTS, '*.json')) if '.p' not in os.path.basename(p)[:-5])
    jobs = {os.path.splitext(os.path.basename(p))[0] for p in parts}
    check(jobs == set(briefs.JOBS), f'every job has its part ({sorted(set(briefs.JOBS) - jobs)} missing)')
    for p in parts:
        probs = buildout.check(p, w, quiet=True)
        check(not probs, f'{os.path.basename(p)} passes the writers\' check ({probs[:2]})')

    # ---- in the world as it loads
    world = World(Config())
    await world.load()
    zones = {z for job in briefs.JOBS.values() for z in job[0]}
    import json
    raw = {}
    for z in zones:
        with open(os.path.join(ROOT, 'world', 'zones', f'zone_{z:03d}.json'), encoding='utf-8') as f:
            raw.update({int(k): r for k, r in json.load(f)['rooms'].items()})
    left = sorted(v for v, r in raw.items() if r.get('placeholder'))
    check(not left, f'every connector room is written by hand ({len(left)} still placeholders: {left[:6]})')
    new_mobs = {v: p for v, p in world.mob_prototypes.items() if buildout.MOB_BASE <= v < buildout.OBJ_BASE}
    new_objs = {v: p for v, p in world.obj_prototypes.items() if buildout.OBJ_BASE <= v < buildout.OBJ_BASE + 100000
                and not p.get('gate_key')}          # (a gate's key is rites.py's, carried by its keeper)
    check(len(new_mobs) >= 40 and len(new_objs) >= 30, f'the zones have their new creatures and items ({len(new_mobs)}, {len(new_objs)})')
    # (of the creatures the build-out made: a zone's population file may add its own in the range)
    made = set(json.load(open(buildout.REGISTRY, encoding='utf-8')).get('mobs', {}).values())
    off = [v for v, p in new_mobs.items() if v in made
           and p['damage_dice'] not in (buildout.stats(p['level'], 'animal')['damage_dice'], buildout.stats(p['level'], 'monster')['damage_dice'])]
    check(not off, f'every new creature hits as its level says ({off[:5]})')
    placed, wrong, wet_wrong = {}, [], []
    for r in world.rooms.values():
        for m in r.mob_resets or []:
            mv = m.get('vnum') if isinstance(m, dict) else m
            if mv in new_mobs:
                placed[mv] = placed.get(mv, 0) + 1
                if r.flags & {'no_mob', 'imm_only', 'peaceful', 'deathtrap', 'death'} or (r.zone and r.zone.sealed):
                    wrong.append((mv, r.vnum))
    # (or comes when it is called: a lair's boss and the herald that flies in first, lairs.py, and a
    # boss's waves and raised followers, boss_mechanics.py)
    import population
    for d in population.load().values():
        for b in d.get('lairs') or []:
            placed.setdefault(int(b['vnum']), 0)
            if b.get('herald'):
                placed.setdefault(int(b['herald']), 0)
        for b in (d.get('bosses') or []) + (d.get('lairs') or []):
            for m in b.get('mechanics') or []:
                for v in list((m.get('adds') or {}).keys()) + list(m.get('raise') or []):
                    placed.setdefault(int(v), 0)
    check(set(placed) >= set(new_mobs), f'every new creature stands somewhere ({sorted(set(new_mobs) - set(placed))[:5]})')
    check(not wrong, f'none where creatures may not be ({wrong[:4]})')
    homes = {}
    for r in world.rooms.values():
        for m in r.mob_resets or []:
            mv = m.get('vnum') if isinstance(m, dict) else m
            if mv in new_mobs:
                homes.setdefault(mv, set()).add(r.sector_type in buildout.WATER)
    mixed = [v for v, h in homes.items() if len(h) > 1]
    check(not mixed, f'a creature lives on the water or on land, not both ({[new_mobs[v]["short_desc"] for v in mixed[:4]]})')
    dropped = {e.get('vnum') for p in new_mobs.values() for e in (p.get('loot_table') or []) if isinstance(e, dict)}
    dropped |= {(e.get('vnum') if isinstance(e, dict) else e) for p in new_mobs.values() for e in (p.get('inventory') or [])}   # a gatekeeper's key (rites.py)
    orphan = sorted(set(new_objs) - dropped)
    check(not orphan, f'every new item is dropped by a creature ({orphan[:5]})')
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
