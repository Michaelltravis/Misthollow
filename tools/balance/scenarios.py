#!/usr/bin/env python3
"""Mob-brain scenarios: the world's creatures thinking on a simulated clock (sim.py's), measured,
with pass/fail checks for each phase of docs/MOB_AI.md.

    python3 tools/balance/scenarios.py cadence                 # a player in zone 54 for 60 s
    python3 tools/balance/scenarios.py cadence --zone 30 --secs 120
    python3 tools/balance/scenarios.py cadence --compare       # brain on vs off (MH_BRAIN), --check exits 1 on a miss

    python3 tools/balance/scenarios.py threat --check          # S1 (phase 1a): a tank, a healer, a mage
    python3 tools/balance/scenarios.py tactics --check         # S7 (phase 1b): interrupts, holds, learning
    python3 tools/balance/scenarios.py pursuit --check         # S2-S5 (phase 2a): chases, leash, stealth, doors

Scenarios:
- threat (S1): a warrior, a cleric and a mage at level 30 against 3 plain creatures, an elite and
  2, and boss 10050, in a readable and a brutal zone. With the tank taunting whatever isn't on
  them, the tank must take most of the blows after the opener (readable 75%, brutal 60%), the
  healer under 15%, and no creature may switch targets more than 2 (brutal 4) times a minute or
  twice inside its switch cooldown. With no taunts and heavy healing, a creature must turn on the
  healer within 30 s.
- tactics (S7): the same party against a caster, a healer and an elite captain, interrupting
  every wind-up it can: at most 30% of the interruptible ones may land, every special that lands
  must have been warned of, and no player may be held more than the zone allows in 18 s. Then a
  mage sleeps 60 fresh creatures four times each: the share that lands must fall try by try, and
  a hold of another school (entangle) must land every time.
- pursuit (S2-S5, phase 2a): a row of eight rooms with a door, and a border. A kiter outruns a
  readable creature, which gives up at its leash and walks home healed; someone fleeing on foot
  escapes a readable one and is caught by a brutal one, and none crosses the border; sneakers by
  skill, an aware creature, an invisible player; the "!" a second before a charge; a door shut
  behind you opened by hands, pounded down by an ogre (two BOOMs heard first), unlocked by a
  jailer with the key, never by a wolf, and a door bound by magic holds.
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


# ---------------------------------------------------------------- S7: tactics (phase 1b)
S7_PASS = {'resolved_max': 0.30}     # of the interruptible wind-ups, at most this many land when every one is answered


def _numbered(room, me, ch):
    """'2.mage': how a player names the second of a name in the room."""
    kw = str(ch.name).split()[-1].lower()
    same = [c for c in room.characters if c is not me and kw in str(getattr(c, 'name', '')).lower()]
    return f"{same.index(ch) + 1}.{kw}"


async def tactics_fight(world, room, tier, secs, seed, interrupting=True):
    """A warrior, cleric and mage (level 30) against a caster, a healer and an elite captain, the
    heroes interrupting every wind-up they can. Returns what was declared, landed and held."""
    import sim
    import brain
    import mob_ai
    import combat_range as cr
    from bosses import create_mob_from_prototype
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
        h = await sim.make_hero(world, cls, level, f'S7{cls[:3].title()}{seed}{tier[0]}', 0.75)
        h.max_hp = h.hp = h.max_hp * 6
        sim._put(h, room)
        party.append(h)
    tank, healer, mage = party
    plain = _plain_foe(world, level)
    foes = []
    for name, roles, rank in (('conjurer', ['caster'], None), ('priest', ['healer'], None), ('captain', ['guarded'], 'elite')):
        p = dict(world.mob_prototypes[plain])
        p['level'], p['ai'] = level + 2, {'roles': roles}
        if rank:
            p['rank'] = rank
        f = create_mob_from_prototype(p, world)
        f.name = name
        f.max_hp = f.hp = 4000
        f.max_mana = f.mana = 10 ** 5
        f.home_zone = None
        f._brain = None
        sim._put(f, room)
        world.npcs.append(f)
        foes.append(f)
    for j, f in enumerate(foes):
        cr.set_pos(f, 11.5 + j * 0.8, 7)
        f.fighting, f.position = tank, 'fighting'
    for j, h in enumerate(party):
        cr.set_pos(h, 10.5, 6 + j)
        h.fighting, h.position = foes[0], 'fighting'

    announced, landed, seen = set(), {'all': 0, 'interruptible': 0, 'unannounced': 0}, {'interruptible': 0}
    real_announce, real_resolve = mob_ai._announce, mob_ai._resolve_intent

    async def announce(mob, intent):
        announced.add(id(intent))
        if intent.get('interruptible'):
            seen['interruptible'] += 1
        return await real_announce(mob, intent)

    async def resolve(mob):
        it = getattr(mob, 'pending_intent', None)
        if it:
            landed['all'] += 1
            landed['interruptible'] += 1 if it.get('interruptible') else 0
            landed['unannounced'] += 0 if id(it) in announced else 1
        return await real_resolve(mob)
    mob_ai._announce, mob_ai._resolve_intent = announce, resolve
    held_max = {h: 0 for h in party}
    t0 = sim.CLOCK.t
    try:
        while sim.CLOCK.t - t0 < secs:
            for f in foes:
                f.hp = max(f.hp, 2000)               # nobody falls: the scenario is about what they try
                await mob_ai.declare_intents(f)
            if interrupting:
                for f in foes:
                    if (getattr(f, 'pending_intent', None) or {}).get('interruptible'):
                        who = min(party, key=lambda h: getattr(h, 'interrupt_cooldown_until', 0))
                        who.interrupt_cooldown_until = 0       # (every wind-up answered)
                        await CommandHandler.execute(who, 'interrupt', [_numbered(room, who, f)])
            for h in party:
                h.hp = max(h.hp, h.max_hp // 2)
                if h.fighting is not None:
                    await CombatHandler.one_round(h, h.fighting)
            sim.CLOCK.advance(sim.NPC_DELAY)
            for f in foes:
                if f.fighting is not None:
                    await mob_ai.mob_ai_tick(f)
                    if f.fighting is not None:
                        await CombatHandler.one_round(f, f.fighting)
            from brain import cast
            for h in party:
                held_max[h] = max(held_max[h], cast.holds_on(h, sim.CLOCK.t))
            sim.CLOCK.advance(sim.ROUND - sim.NPC_DELAY)
    finally:
        mob_ai._announce, mob_ai._resolve_intent = real_announce, real_resolve
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
    return {'declared': seen['interruptible'], 'landed': landed['interruptible'], 'unannounced': landed['unannounced'],
            'resolved_all': landed['all'], 'held_max': max(held_max.values()),
            'cc_chain': brain.of(foes[0]).profile.get('cc_chain', 1)}


async def adaptation(world, room, tier, n=60, seed=7):
    """A mage puts the same hold (sleep) on n fresh creatures four times each, waking them between,
    then a hold of another school: the share that lands, attempt by attempt."""
    import sim
    import brain
    from spells import SpellHandler, SPELLS
    import combat_range as cr
    from bosses import create_mob_from_prototype
    random.seed(seed)
    room.zone.ai = {'tier': tier}
    mage = await sim.make_hero(world, 'mage', 30, f'S7Ada{tier[0]}', 0.75)
    sim._put(mage, room)
    plain = _plain_foe(world, 30)
    first = second = None
    landed = [0] * 5
    for i in range(n):
        f = create_mob_from_prototype(dict(world.mob_prototypes[plain]), world)
        f.home_zone = None
        f.name = f'sleeper{i}'
        sim._put(f, room)
        b = brain.of(f)
        b.encounter['fought_at'] = sim.CLOCK.t
        for k, (spell, aff) in enumerate([('sleep', {'type': 'sleep', 'value': 1})] * 4 + [('entangle', {'type': 'entangled', 'value': 1})]):
            sch = cr.spell_school(spell, SPELLS.get(spell), mage)
            if k == 0:
                first = sch
            if k == 4:
                second = sch
            await SpellHandler.apply_affect(f, dict(aff), 2, SPELLS[spell]['name'], mage.level, caster=mage, spell_key=spell)
            kind = 'sleeping' if spell == 'sleep' else 'entangled'
            if kind in (getattr(f, 'affect_flags', None) or set()):
                landed[k] += 1
            SpellHandler._cleanse(f, {kind})
            f.position = 'standing'
        room.characters.remove(f)
    room.characters.remove(mage)
    world.players.pop(mage.name.lower(), None)
    room.zone.ai = None
    return [x / n for x in landed], first, second


async def tactics(args):
    import sim
    world = await sim.load_world()
    sim.patch_deaths(world)
    room = world.rooms[3054] if 3054 in world.rooms else next(iter(world.rooms.values()))
    ok = True
    for tier in ('readable', 'brutal'):
        r = await tactics_fight(world, room, tier, args.secs, args.seed)
        share = r['landed'] / max(1, r['declared'])
        good = r['declared'] >= 5 and share <= S7_PASS['resolved_max']
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {tier:8} every wind-up answered: {r['landed']} of {r['declared']} interruptible "
              f"wind-ups landed ({share:.0%}, at most {S7_PASS['resolved_max']:.0%})")
        good = r['unannounced'] == 0 and r['resolved_all'] > 0
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {tier:8} every special that landed was warned of first "
              f"({r['resolved_all']} landed, {r['unannounced']} unwarned)")
        free = await tactics_fight(world, room, tier, max(240, args.secs * 2), args.seed + 1, interrupting=False)
        good = 1 <= free['held_max'] <= free['cc_chain']
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {tier:8} nobody interrupting: holds on one player in any 18 s at most "
              f"{free['held_max']} (the zone allows {free['cc_chain']}; at least one must land)")
        rates, s1, s2 = await adaptation(world, room, tier)
        good = rates[0] == 1.0 and rates[3] < rates[1] <= rates[0] and rates[4] == 1.0 and s1 != s2
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {tier:8} creatures learn: {s1} sleep landed "
              f"{' / '.join(f'{x:.0%}' for x in rates[:4])} on tries 1-4; then {s2} (entangle) {rates[4]:.0%}")
    return ok


# ---------------------------------------------------------------- S2-S5: pursuit (phase 2a)
ARENA = 9990          # a zone of its own: eight rooms in a row, west to east, a door between 3 and 4,
DOOR_AT = 3           # and past the last one a room of another zone (the border)
KEY = 99999


def arena(world):
    """[rooms] of the scenario zone (built once), its door open and unlocked, the border room last."""
    from world import Room, Zone
    if getattr(world, '_arena', None):
        rooms = world._arena
    else:
        z, zb = Zone(ARENA), Zone(ARENA + 1)
        world.zones[ARENA], world.zones[ARENA + 1] = z, zb
        rooms = []
        for i in range(9):
            r = Room(ARENA * 100 + i)
            r.zone = z if i < 8 else zb
            r.name = f'Arena {i}'
            r.flags = set()
            r.sector_type = 'inside'
            (z if i < 8 else zb).rooms[r.vnum] = r
            world.rooms[r.vnum] = r
            rooms.append(r)
        for a, b in zip(rooms, rooms[1:]):
            a.exits['east'] = {'room': b, 'to_room': b.vnum}
            b.exits['west'] = {'room': a, 'to_room': a.vnum}
        d = rooms[DOOR_AT]
        d.exits['east']['door'] = {'name': 'door', 'state': 'open'}
        rooms[DOOR_AT + 1].exits['west']['door'] = {'name': 'door', 'state': 'open'}
        world._arena = rooms
    for r in rooms:
        for ch in list(r.characters):
            r.characters.remove(ch)
    for side in (rooms[DOOR_AT].exits['east']['door'], rooms[DOOR_AT + 1].exits['west']['door']):
        side.clear()
        side.update({'name': 'door', 'state': 'open'})
    return rooms


def _door(rooms, **fields):
    for side in (rooms[DOOR_AT].exits['east']['door'], rooms[DOOR_AT + 1].exits['west']['door']):
        side.update(fields)


async def _runner(world, rooms, at, name, level=30):
    import sim
    from player import Player
    p = Player(world)
    p.name, p.char_class, p.level = name, 'thief', level
    p.max_hp = p.hp = 10 ** 6
    p.connection = sim.Conn()
    p.world = world
    world.players[name.lower()] = p
    sim._put(p, rooms[at])
    return p


def _hunter(world, rooms, at, tier, words='raider', race=None, flags=('aggressive',), level=30, key=False):
    import mob_ai
    import brain
    from bosses import create_mob_from_prototype
    plain = _plain_foe(world, level)
    p = dict(world.mob_prototypes[plain])
    p['level'], p['name'], p['short_desc'] = level, words, f'the {words}'
    p['flags'] = list(set(p.get('flags') or []) | set(flags))
    if race:
        p['race'] = race
    f = create_mob_from_prototype(p, world)
    f.name = f'the {words}'
    f.race = race
    f.home_zone = ARENA
    f.home_room = rooms[at]
    import sim
    sim._put(f, rooms[at])
    world.npcs.append(f)
    if key:
        import types
        f.inventory = list(getattr(f, 'inventory', None) or []) + [types.SimpleNamespace(vnum=KEY, name='a key')]
    rooms[0].zone.ai = {'tier': tier}
    mob_ai.classify_mob(f)
    f._brain = None
    brain.of(f)
    return f


async def _tick(mobs, secs, until=None, each=None):
    """Run the creatures' thinking at 10 Hz for secs (or until until() is true)."""
    import sim
    t0 = sim.CLOCK.t
    while sim.CLOCK.t - t0 < secs:
        for m in mobs:
            if m.hp > 0 and getattr(m, 'fighting', None) is None:
                await m.process_ai()
        if each:
            await each(sim.CLOCK.t - t0)
        await asyncio.sleep(0)
        if until and until():
            break
        sim.CLOCK.advance(0.1)
    return sim.CLOCK.t - t0


def _index(rooms, ch):
    return rooms.index(ch.room) if ch.room in rooms else None


async def kiter(world, tier, pace, seed):
    """A hero runs east from the hunter at pace s a room. (furthest room it reached, caught, back
    home healed within 60 s of giving up)."""
    import brain
    random.seed(seed)
    rooms = arena(world)
    hero = await _runner(world, rooms, 1, f'Kite{seed}')
    mob = _hunter(world, rooms, 0, tier)
    mob.hp = mob.max_hp // 2                      # (to see it healed at home)
    b = brain.of(mob)
    b.rng.seed(seed)
    far = [0]
    nxt = [0.5]                                   # (they run at its "!")

    async def run(t):
        far[0] = max(far[0], _index(rooms, mob) or 0)
        if t >= nxt[0] and mob.fighting is None:
            i = _index(rooms, hero)
            if i is not None and i < 7:
                from sim import _put
                _put(hero, rooms[i + 1])
            nxt[0] = t + pace
    await _tick([mob], 40, until=lambda: mob.fighting is not None or b.mode == 'return', each=run)
    caught = mob.fighting is hero
    home_in = None
    if not caught:
        t = await _tick([mob], 60, until=lambda: b.mode == 'idle' and mob.room is rooms[0])
        home_in = t if mob.room is rooms[0] else None
    healed = mob.hp >= mob.max_hp
    for r in rooms:
        for ch in list(r.characters):
            r.characters.remove(ch)
    if mob in world.npcs:
        world.npcs.remove(mob)
    world.players.pop(hero.name.lower(), None)
    return far[0], caught, home_in, healed, b.profile.get('leash_rooms')


async def sneaker(world, tier, seed, skill=0, aware=False, invisible=False, across=False):
    """(spotted within 10 s, seconds from its alert to its attack)."""
    import brain
    import combat_events as ev
    random.seed(seed)
    rooms = arena(world)
    hero = await _runner(world, rooms, 1 if across else 0, f'Sneak{seed}')
    hero.skills = dict(getattr(hero, 'skills', None) or {}, sneak=skill, hide=skill)
    if not across:
        hero.flags.add('sneaking')
    if invisible:
        hero.affect_flags = set(getattr(hero, 'affect_flags', None) or ()) | {'invisible'}
    mob = _hunter(world, rooms, 0, tier, flags=('aggressive', 'aware') if aware else ('aggressive',))
    b = brain.of(mob)
    b.rng.seed(seed)
    stamp = {}
    real = ev.emit

    def emit(room, kind, *a, **kw):
        if kind == 'alert' and (kw.get('src') if 'src' in kw else (a[0] if a else None)) is mob:
            import sim
            stamp.setdefault('alert', sim.CLOCK.t)
        return real(room, kind, *a, **kw)
    ev.emit = emit
    try:
        import sim
        t = await _tick([mob], 10, until=lambda: mob.fighting is not None)
        attacked = mob.fighting is hero
        delay = (sim.CLOCK.t - stamp['alert']) if attacked and 'alert' in stamp else None
    finally:
        ev.emit = real
    for r in rooms:
        for ch in list(r.characters):
            r.characters.remove(ch)
    if mob in world.npcs:
        world.npcs.remove(mob)
    world.players.pop(hero.name.lower(), None)
    return attacked, delay


async def door_closer(world, tier, kind, seed):
    """The hunter's quarry shuts the door between rooms 3 and 4 behind them. kind: humanoid,
    animal, brute (the door locked, no key), key (locked, it carries the key), arcane (bound by
    magic). (got through, seconds from the door shut to its opening, BOOMs heard)."""
    import brain
    import sim
    random.seed(seed)
    rooms = arena(world)
    hero = await _runner(world, rooms, DOOR_AT, f'Door{seed}')
    words, race = {'humanoid': ('raider', 'human'), 'animal': ('wolf', 'wolf'), 'brute': ('ogre', 'giant'),
                   'key': ('jailer', 'human'), 'arcane': ('ogre', 'giant')}[kind]
    mob = _hunter(world, rooms, DOOR_AT - 1, tier, words=words, race=race, key=(kind == 'key'))
    b = brain.of(mob)
    b.rng.seed(seed)
    # it has seen them ("!"); they step through and shut (and lock, or ward) the door
    await _tick([mob], 2.5, until=lambda: b.mode == 'alert')
    sim._put(hero, rooms[DOOR_AT + 1])
    fields = {'state': 'closed'}
    if kind in ('brute', 'key', 'arcane'):
        fields['locked'] = True
        fields['key'] = KEY
    if kind == 'arcane':
        fields['arcane'] = True
    _door(rooms, **fields)
    booms = [0]
    real = rooms[DOOR_AT + 1].send_to_room

    async def heard(msg, *a, **k):
        if 'BOOM' in str(msg):
            booms[0] += 1
        return await real(msg, *a, **k)
    rooms[DOOR_AT + 1].send_to_room = heard
    shut_at = sim.CLOCK.t
    opened = [None]

    async def watch(t):
        if opened[0] is None and rooms[DOOR_AT].exits['east']['door'].get('state') != 'closed':
            opened[0] = sim.CLOCK.t - shut_at
    try:
        await _tick([mob], 40, until=lambda: mob.room is rooms[DOOR_AT + 1] or b.mode in ('return', 'idle'), each=watch)
    finally:
        del rooms[DOOR_AT + 1].send_to_room
    through = mob.room is rooms[DOOR_AT + 1]
    for r in rooms:
        for ch in list(r.characters):
            r.characters.remove(ch)
    if mob in world.npcs:
        world.npcs.remove(mob)
    world.players.pop(hero.name.lower(), None)
    return through, opened[0], booms[0]


async def pursuit(args):
    import sim
    world = await sim.load_world()
    sim.patch_deaths(world)
    ok = True

    def say(good, text):
        nonlocal ok
        ok &= bool(good)
        print(f"{'ok  ' if good else 'FAIL'} {text}")

    for tier in ('readable', 'brutal'):
        # S2: a kiter faster than it (1 room a second)
        far, caught, home, healed, leash = await kiter(world, tier, 1.0, args.seed)
        # (brutal's leash is 7 rooms: this arena's 8 can't outrun it, so there only the leash is checked)
        say(far <= leash and (tier == 'brutal' or (not caught and home is not None and home <= 60 and healed)),
            f"{tier:8} S2 kiter: chased {far} rooms (leash {leash}), then "
            + ('caught them in the last room of the arena' if caught else
               f"home in {'%.0f s' % home if home is not None else 'never'}, {'healed' if healed else 'NOT healed'}"))
        # S3: someone fleeing on foot (a room every 1.3 s), 20 tries
        n, caught_n, crossed = 20, 0, 0
        for s in range(n):
            far, caught, _home, _healed, _l = await kiter(world, tier, 1.3, args.seed * 100 + s)
            caught_n += caught
            crossed += far >= 8
        esc = 1 - caught_n / n
        want = (esc >= 0.85) if tier == 'readable' else (caught_n / n >= 0.5)
        say(want and crossed == 0, f"{tier:8} S3 fleeing on foot: escaped {esc:.0%} of {n} "
            f"({'at least 85%' if tier == 'readable' else 'caught at least half'}); crossed the zone border {crossed}x")
        # S4: sneakers
        rate = lambda xs: sum(1 for a, _ in xs if a) / len(xs)
        plain = [await sneaker(world, tier, s, skill=60) for s in range(30)]
        skilled = [await sneaker(world, tier, s, skill=100) for s in range(30)]
        aware = [await sneaker(world, tier, s, skill=60, aware=True) for s in range(30)]
        invis = [await sneaker(world, tier, s, invisible=True) for s in range(20)]
        far_ = [await sneaker(world, tier, s, across=True) for s in range(10)]
        delays = [d for a, d in far_ if a and d is not None]
        say(rate(invis) == 0 and rate(aware) >= rate(plain) >= rate(skilled) and rate(aware) >= 0.7,
            f"{tier:8} S4 stealth: a sneaker (60) spotted {rate(plain):.0%}, a master (100) {rate(skilled):.0%}, "
            f"by an aware creature {rate(aware):.0%} (at least 70%), invisible {rate(invis):.0%} (never)")
        say(delays and min(delays) >= 1.0,
            f"{tier:8} S4 across an open way: its '!' at least 1 s before it attacks "
            f"({', '.join('%.1f' % d for d in sorted(delays)[:4]) or 'no attack'} s)")
        # S5: the door shut behind them
        got = {k: await door_closer(world, tier, k, args.seed) for k in ('humanoid', 'animal', 'brute', 'key', 'arcane')}
        th, t_open, _ = got['humanoid']
        say(th and t_open is not None and 2.0 <= t_open <= 6.0, f"{tier:8} S5 a raider opens the shut door after "
            f"{'%.1f s' % t_open if t_open is not None else 'never'} (2-6 s) and comes through")
        say(not got['animal'][0], f"{tier:8} S5 a wolf can't open it: {'came through!' if got['animal'][0] else 'gives up'}")
        th, _, booms = got['brute']
        say(th and booms >= 2, f"{tier:8} S5 an ogre at the locked door: {booms} BOOMs heard, then through" if th
            else f"{tier:8} S5 an ogre at the locked door: never through ({booms} BOOMs)")
        say(got['key'][0] and got['key'][2] == 0, f"{tier:8} S5 a jailer with the key unlocks it quietly "
            f"({'through' if got['key'][0] else 'NOT through'}, {got['key'][2]} BOOMs)")
        say(not got['arcane'][0], f"{tier:8} S5 a door bound by magic holds even an ogre "
            f"({'it came through!' if got['arcane'][0] else 'held'})")
    return ok


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
    ap.add_argument('scenario', choices=['cadence', 'threat', 'tactics', 'pursuit'])
    ap.add_argument('--zone', type=int, default=54)
    ap.add_argument('--secs', type=float, default=60)
    ap.add_argument('--seed', type=int, default=54)
    ap.add_argument('--compare', action='store_true', help='brain on vs off')
    ap.add_argument('--tolerance', type=float, default=0.10, help='--compare: how far the rates may differ')
    ap.add_argument('--slower', type=float, default=1.4,
                    help='--compare: how much slower thinking may get (phase 0 measured 0.97x; with eyes and ears, phase 2a, about 1.3x)')
    ap.add_argument('--check', action='store_true', help='exit 1 when a check fails')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    if args.compare:
        ok = compare(args)
        sys.exit(0 if ok or not args.check else 1)
    if args.scenario in ('threat', 'tactics', 'pursuit'):
        ok = asyncio.run({'threat': threat, 'tactics': tactics, 'pursuit': pursuit}[args.scenario](args))
        sys.exit(0 if ok or not args.check else 1)
    r = asyncio.run(cadence(args.zone, args.secs, args.seed))
    if args.json:
        print(json.dumps(r))
    else:
        show(r)


if __name__ == '__main__':
    main()
