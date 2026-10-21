#!/usr/bin/env python3
"""Mob-brain scenarios: the world's creatures thinking on a simulated clock (sim.py's), measured,
with pass/fail checks for each phase of docs/MOB_AI.md.

    python3 tools/balance/scenarios.py cadence                 # a player in zone 54 for 60 s
    python3 tools/balance/scenarios.py cadence --zone 30 --secs 120
    python3 tools/balance/scenarios.py cadence --compare       # brain on vs off (MH_BRAIN), --check exits 1 on a miss

Scenarios:
- cadence: a hero stands in a busy zone while world.process_npcs runs ten times a second;
  counts the creatures' moves (a step to another room), the fights they start, how many think a
  tick and how long the thinking takes (brain/scheduler STATS). --compare runs it with the brain
  on and off: the rates must agree within --tolerance and the time a tick within --slower.

Later phases add their scenarios here (a tank and a healer against a pack, a kiter, a fleeing
player, a sneaker, a door-closer), each with the numbers it must reach.
"""
import argparse
import asyncio
import json
import os
import random
import subprocess
import sys
import time as _time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


async def cadence(zone_no, secs, seed):
    import sim                                  # (its clock: time.time() is simulated from here)
    world = await sim.load_world()
    from player import Player
    from mobs import Mobile
    from combat import CombatHandler
    from brain import scheduler

    zone = world.zones.get(zone_no)
    if zone is None or not zone.rooms:
        raise SystemExit(f'no zone {zone_no}')
    # the room of the zone with the most creatures in it and around it
    room = max(zone.rooms.values(), key=lambda r: sum(1 for c in r.characters if isinstance(c, Mobile)))
    hero = Player(world)
    hero.name, hero.char_class, hero.level = 'Watcher', 'warrior', 30
    hero.max_hp = hero.hp = 10 ** 6
    hero.connection = sim.Conn()
    hero.world = world
    world.players['watcher'] = hero
    hero.room = room
    room.characters.append(hero)

    counts = {'moves': 0, 'fights': 0}
    real_move = Mobile._notify_move

    async def notify_move(self, *a, **k):
        counts['moves'] += 1
        return await real_move(self, *a, **k)
    Mobile._notify_move = notify_move
    real_start = CombatHandler.start_combat.__func__

    async def start_combat(cls, attacker, *a, **k):
        if isinstance(attacker, Mobile):
            counts['fights'] += 1
        return await real_start(cls, attacker, *a, **k)
    CombatHandler.start_combat = classmethod(start_combat)

    random.seed(seed)
    in_zone = sum(1 for n in world.npcs if getattr(getattr(n, 'room', None), 'zone', None) is zone)
    scheduler.STATS.reset()
    wall = _time.perf_counter()
    for _ in range(int(secs * 10)):
        await world.process_npcs()
        sim.CLOCK.advance(0.1)
    wall = _time.perf_counter() - wall
    st = scheduler.STATS
    return {'zone': zone_no, 'secs': secs, 'creatures': len(world.npcs), 'in_zone': in_zone,
            'moves_per_min': counts['moves'] * 60.0 / secs, 'fights_per_min': counts['fights'] * 60.0 / secs,
            'thought_per_tick': st.thought / max(1, st.ticks), 'ms_per_tick': st.ms_total / max(1, st.ticks),
            'wall_s': wall}


def show(r, label=''):
    print(f"{label}zone {r['zone']}  {r['secs']:.0f} s  creatures {r['creatures']} ({r['in_zone']} in the zone)  "
          f"moves/min {r['moves_per_min']:.1f}  fights/min {r['fights_per_min']:.1f}  "
          f"thinking/tick {r['thought_per_tick']:.0f}  ms/tick {r['ms_per_tick']:.2f}")


def compare(args):
    out = {}
    for on in (True, False):
        env = dict(os.environ, MH_BRAIN='1' if on else '0', PYTHONHASHSEED='0')
        cmd = [sys.executable, os.path.abspath(__file__), 'cadence', '--zone', str(args.zone),
               '--secs', str(args.secs), '--seed', str(args.seed), '--json']
        p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=3600)
        if p.returncode:
            print(p.stdout, p.stderr)
            raise SystemExit(f'cadence (brain {"on" if on else "off"}) failed')
        out[on] = json.loads(p.stdout.strip().splitlines()[-1])
        show(out[on], label=f"brain {'on ' if on else 'off'}  ")
    ok = True
    for k in ('moves_per_min', 'fights_per_min', 'thought_per_tick'):
        a, b = out[True][k], out[False][k]
        good = abs(a - b) <= args.tolerance * max(b, 1e-9) or abs(a - b) < 0.5
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {k}: {a:.1f} with the brain, {b:.1f} without (within {args.tolerance:.0%})")
    ratio = out[True]['ms_per_tick'] / max(out[False]['ms_per_tick'], 1e-9)
    good = ratio <= args.slower
    ok &= good
    print(f"{'ok  ' if good else 'FAIL'} thinking takes {ratio:.2f}x the time it did without the brain (at most {args.slower:.2f}x)")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('scenario', choices=['cadence'])
    ap.add_argument('--zone', type=int, default=54)
    ap.add_argument('--secs', type=float, default=60)
    ap.add_argument('--seed', type=int, default=54)
    ap.add_argument('--compare', action='store_true', help='brain on vs off')
    ap.add_argument('--tolerance', type=float, default=0.10, help='--compare: how far the rates may differ')
    ap.add_argument('--slower', type=float, default=1.15, help='--compare: how much slower thinking may get (timing noise)')
    ap.add_argument('--check', action='store_true', help='exit 1 when a check fails')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    if args.compare:
        ok = compare(args)
        sys.exit(0 if ok or not args.check else 1)
    r = asyncio.run(cadence(args.zone, args.secs, args.seed))
    if args.json:
        print(json.dumps(r))
    else:
        show(r)


if __name__ == '__main__':
    main()
