#!/usr/bin/env python3
"""Mob-brain scenarios: the world's creatures thinking on a simulated clock (sim.py's), measured,
with pass/fail checks for each phase of docs/MOB_AI.md.

    python3 tools/balance/scenarios.py cadence                 # a player in zone 54 for 60 s
    python3 tools/balance/scenarios.py cadence --zone 30 --secs 120
    python3 tools/balance/scenarios.py cadence --compare       # brain on vs off (MH_BRAIN), --check exits 1 on a miss

    python3 tools/balance/scenarios.py threat --check          # S1 (phase 1a): a tank, a healer, a mage

Scenarios:
- threat (S1): a warrior, a cleric and a mage at level 30 against 3 plain creatures, an elite and
  2, and boss 10050, in a readable and a brutal zone. With the tank taunting whatever isn't on
  them, the tank must take most of the blows after the opener (readable 75%, brutal 60%), the
  healer under 15%, and no creature may switch targets more than 2 (brutal 4) times a minute or
  twice inside its switch cooldown. With no taunts and heavy healing, a creature must turn on the
  healer within 30 s.
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


# ---------------------------------------------------------------- S1: threat (phase 1a)
S1_FIGHTS = [('3 regulars', [('regular', 3)]), ('an elite and 2 regulars', [('elite', 1), ('regular', 2)]),
             ('boss 10050', [('boss', 1)])]
S1_PASS = {   # tier: (the tank's share of blows at least, non-taunt switches a creature a minute at most)
    'readable': (0.75, 2.0),
    'brutal': (0.60, 4.0),
}


def _plain_foe(world, level):
    """A creature with no role of its own (no pack, caster, healer...): the threat table alone
    decides whom it fights."""
    import mob_ai
    from bosses import create_mob_from_prototype, Boss
    for v in sorted(world.mob_prototypes):
        p = world.mob_prototypes[v]
        if not isinstance(p, dict) or not 15 <= int(p.get('level') or 0) <= 45 or p.get('special') \
                or set(p.get('flags') or ()) & {'boss', 'sentinel', 'no_attack', 'caster', 'helper'}:
            continue
        m = create_mob_from_prototype(p, world)
        if not isinstance(m, Boss) and not mob_ai.classify_mob(m):
            return v
    raise SystemExit('no plain creature found')


async def threat_fight(world, room, tier, spec, taunting, healing, secs, seed):
    """A warrior, a cleric and a mage (level 30) against spec; returns what the foes did."""
    import sim
    import brain
    from brain import targeting
    from bosses import create_mob_from_prototype
    from player import Player
    import combat_range as cr
    import mob_ai
    from combat import CombatHandler
    from commands import CommandHandler
    random.seed(seed)
    room.zone.ai = {'tier': tier}
    for ch in list(room.characters):
        if not hasattr(ch, 'connection'):
            room.characters.remove(ch)
    level = 30
    party = []
    for cls in ('warrior', 'cleric', 'mage'):
        h = await sim.make_hero(world, cls, level, f'S1{cls[:3].title()}{seed}', 0.75)
        h.max_hp = h.hp = h.max_hp * 6          # nobody dies: the scenario is about whom they hit
        sim._put(h, room)
        party.append(h)
    tank, healer, mage = party
    plain = _plain_foe(world, level)
    foes = []
    for kind, n in spec:
        for _ in range(n):
            if kind == 'boss':
                f = create_mob_from_prototype(world.mob_prototypes[10050], world)
            else:
                p = dict(world.mob_prototypes[plain])
                p['level'], p['rank'] = level, kind
                f = create_mob_from_prototype(p, world)
            mob_ai.classify_mob(f)        # its roles as it is (over 5000 health it would read as a boss)
            f.max_hp = f.hp = 10 ** 6     # then lasting the whole scenario
            f.home_zone = None
            f._brain = None
            sim._put(f, room)
            world.npcs.append(f)
            foes.append(f)
    for j, f in enumerate(foes):
        cr.set_pos(f, 11.5 + j * 0.8, 7)
        f.fighting, f.position = random.choice(party), 'fighting'       # whoever it saw first
    for j, h in enumerate(party):
        cr.set_pos(h, 10.5, 6 + j)
        h.fighting, h.position = foes[0], 'fighting'

    hits = {h: 0 for h in party}
    real_take = Player.take_damage

    async def take_damage(self, amount, *a, **k):
        attacker = k.get('attacker', a[0] if a else None)
        # the creatures' own blows (not a counter to a hero's swing), after the opener (2 rounds)
        if self in hits and attacker in foes and stats.get('foes_turn') and stats['t'] >= 6.0:
            hits[self] += 1
        return await real_take(self, amount, *a, **k)
    Player.take_damage = take_damage
    switches, healer_drawn = [], [None]
    real_turn = targeting.turn_on

    async def turn_on(mob, b, t, now, why):
        old = mob.fighting
        await real_turn(mob, b, t, now, why)
        if old is not None and old is not t and why != 'taunted':
            switches.append((mob, now))
    targeting.turn_on = turn_on
    stats = {'t': 0.0}
    t0 = sim.CLOCK.t
    try:
        while sim.CLOCK.t - t0 < secs:
            stats['t'] = sim.CLOCK.t - t0
            for f in foes:
                await mob_ai.declare_intents(f)
            # the tank: a taunt for whatever is not on them, else their best attack
            loose = [f for f in foes if f.fighting is not tank]
            if taunting and loose:
                # "2.puff": the second of that name in the room (the foes are all alike)
                kw = str(loose[0].name).split()[-1].lower()
                same = [c for c in room.characters if c is not tank and kw in str(getattr(c, 'name', '')).lower()]
                await CommandHandler.execute(tank, 'taunt', [f"{same.index(loose[0]) + 1}.{kw}"])
                tank.fighting = loose[0]
            else:
                await sim.act(tank, party, foes, {})
            # the healer: heavy healing (anyone under 90%), else a blow
            low = min(party, key=lambda h: h.hp / h.max_hp)
            _, heals = sim.rotation('cleric', level)
            if healing and low.hp < 0.9 * low.max_hp and heals:
                for e in heals:
                    cmd, args = sim._cmd(e)
                    await CommandHandler.execute(healer, cmd, args + ([low.name.lower()] if low is not healer else []))
                healer.mana = healer.max_mana
            mage.fighting = tank.fighting
            for h in party:
                if h.fighting is not None:
                    await CombatHandler.one_round(h, h.fighting)
            sim.CLOCK.advance(sim.NPC_DELAY)
            stats['foes_turn'] = True
            for f in foes:
                if f.fighting is None:
                    continue
                await mob_ai.mob_ai_tick(f)
                if f.fighting is not None:
                    await CombatHandler.one_round(f, f.fighting)
                if f.fighting is healer and healer_drawn[0] is None:
                    healer_drawn[0] = sim.CLOCK.t - t0
            stats['foes_turn'] = False
            sim.CLOCK.advance(sim.ROUND - sim.NPC_DELAY)
    finally:
        Player.take_damage = real_take
        targeting.turn_on = real_turn
        for f in foes:
            if f in world.npcs:
                world.npcs.remove(f)
            if f in room.characters:
                room.characters.remove(f)
        for h in party:
            if h in room.characters:
                room.characters.remove(h)
            world.players.pop(h.name.lower(), None)
        room.zone.ai = None
    total = sum(hits.values()) or 1
    minutes = secs / 60.0
    # two non-taunt switches by one creature inside its switch cooldown: dithering
    cooldown = brain.of(foes[0]).profile.get('switch_cooldown_s', 6)
    by = {}
    dither = 0
    for mob, t in switches:
        if mob in by and t - by[mob] < cooldown - 1e-6:
            dither += 1
        by[mob] = t
    return {'tank': hits[tank] / total, 'healer': hits[healer] / total, 'mage': hits[mage] / total,
            'switches_per_mob_min': len(switches) / max(1, len(foes)) / minutes, 'dither': dither,
            'healer_drawn_s': healer_drawn[0]}


async def threat(args):
    import sim
    world = await sim.load_world()
    sim.patch_deaths(world)
    room = world.rooms[3054] if 3054 in world.rooms else next(iter(world.rooms.values()))
    ok = True
    for tier in ('readable', 'brutal'):
        need_tank, max_sw = S1_PASS[tier]
        for label, spec in S1_FIGHTS:
            r = await threat_fight(world, room, tier, spec, taunting=True, healing=True, secs=args.secs, seed=args.seed)
            good = r['tank'] >= need_tank and r['switches_per_mob_min'] <= max_sw and r['dither'] == 0 and r['healer'] < 0.15
            ok &= good
            print(f"{'ok  ' if good else 'FAIL'} {tier:8} taunting tank vs {label:24} blows on tank {r['tank']:.0%} "
                  f"(>= {need_tank:.0%}), healer {r['healer']:.0%} (< 15%), mage {r['mage']:.0%}; "
                  f"switches {r['switches_per_mob_min']:.1f}/min (<= {max_sw:g}), dithering {r['dither']}")
        r = await threat_fight(world, room, tier, S1_FIGHTS[0][1], taunting=False, healing=True, secs=args.secs, seed=args.seed)
        drawn = r['healer_drawn_s']
        good = drawn is not None and drawn <= 30
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {tier:8} no taunts, heavy healing vs 3 regulars: a creature turns on the "
              f"healer {'after %.0f s' % drawn if drawn is not None else 'never'} (within 30 s)")
    return ok


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
    ap.add_argument('scenario', choices=['cadence', 'threat'])
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
    if args.scenario == 'threat':
        ok = asyncio.run(threat(args))
        sys.exit(0 if ok or not args.check else 1)
    r = asyncio.run(cadence(args.zone, args.secs, args.seed))
    if args.json:
        print(json.dumps(r))
    else:
        show(r)


if __name__ == '__main__':
    main()
