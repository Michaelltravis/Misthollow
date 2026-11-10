"""Who lives where, zone by zone (world/population/zone_<n>.json), applied when the world loads,
after the zone files and before the first reset, so a rebuild of world/zones keeps it.

    {"zone": 220,
     "bosses": [{"vnum": 22070, "room": 14151, "mechanics": [{"type": "plague_pools"}], "why": "..."}],
                                                    # spawn here, and only here; fight mechanics
     "doors":  [{"room": 14150, "dir": "south", "key": 22051, "name": "inner gate"}],   # locked to a key
     "lairs":  [{"vnum": 647006, "room": 8403, "herald": 647009, ...}]}   # comes when someone walks in (lairs.py)

Also "items" (prototypes by vnum, as the build-out writes them: keywords, short_desc, room_desc,
description, kind, level and weapon_type/wear_slot/bonus; item_numbers() gives the rest), which
the zone's creatures carry ("inventory") or drop ("loot_table": [{vnum, chance}]);
"creatures" (prototypes by vnum: rank regular/elite/sub-boss, helpers {group, rooms, count}),
"spawns" [{vnum, rooms, max}], "patrols" [{vnum, route}] (mobs.patrol_ai; allies.py) and "fill"
[{vnum, rooms, total}] (more of a creature in a thin zone, tools/audit/densify.py).

A creature needs only its words, level and rank: health, blows, armour and experience left out
are worked out from them (numbers()). An entry for a creature the zone files already have, with
no "name", changes only what it gives (a rank, helpers) and keeps the rest.

A boss placed here spawns in its room and nowhere else in the world (its other resets go). A door
listed is closed and locked, opened by the key named (doors.py key_vnum).
"""
import glob
import json
import logging
import os

logger = logging.getLogger('Misthollow')
POP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'world', 'population')


RANK_HP = {'regular': 1.0, 'elite': 3.4, 'sub-boss': 6.5, 'boss': 11.0}
RANK_XP = {'regular': 2, 'elite': 8, 'sub-boss': 20, 'boss': 20}


def numbers(level, rank=None):
    """A creature's numbers from its level and rank, on the same curve as the castle's and
    Atal'narath's (health about 22 a level for a regular, more by rank)."""
    L, rank = max(1, int(level)), rank or 'regular'
    hp = max(8, int(22 * L * RANK_HP.get(rank, 1.0)))
    n = 1 if L < 10 else 2 if rank in ('regular', 'elite') else 3
    size = 4 if L < 6 else 6 if L < 15 else 8 if L < 22 else 10
    bonus = L // 5 + {'elite': 2, 'sub-boss': 4, 'boss': 6}.get(rank, 0)
    return {'hp_dice': f'{max(1, hp // 10)}d10+{hp // 2}', 'max_hp': hp, 'hp': hp,
            'damage_dice': f'{n}d{size}+{bonus}', 'hitroll': L // 2, 'damroll': bonus,
            'ac': -(10 + L), 'armor_class': 5, 'gold': 4 * L, 'exp': 30 * L,
            'xp': 30 * L * RANK_XP.get(rank, 2), 'detect_bonus': 10}


# An item's numbers from its level and kind (the build-out's: tools/atlas/buildout.py uses these).
SLOTS = {'body': 'body', 'head': 'head', 'legs': 'legs', 'feet': 'feet', 'hands': 'hands', 'arms': 'arms',
         'shield': 'shield', 'about': 'about', 'waist': 'waist', 'wrist': 'wrist1', 'neck': 'neck1',
         'finger': 'finger1', 'hold': 'hold'}
SLOT_ARMOR = {'body': (3, 8, 10), 'shield': (3, 12, 6), 'head': (2, 12, 3), 'legs': (2, 12, 3), 'feet': (2, 12, 3),
              'hands': (2, 12, 2), 'arms': (2, 12, 2), 'about': (1, 12, 3), 'waist': (1, 15, 1), 'wrist': (1, 15, 1),
              'neck': (1, 15, 1), 'finger': (1, 15, 1), 'hold': (0, 99, 1)}


def item_numbers(i):
    L, kind = max(1, int(i['level'])), i['kind']
    out = {'item_type': kind, 'type': kind, 'min_level': L}
    if kind == 'weapon':
        avg = 4 + 0.15 * L
        n = 1 if L < 10 else 2
        s = max(4, min(12, round(2 * avg - 1))) if n == 1 else max(3, round(avg - 1))
        out.update(damage_dice=f'{n}d{s}', weapon_type=i['weapon_type'], weight=6, value=25 * L + 40)
    elif kind == 'armor':
        base, per, weight = SLOT_ARMOR[i['wear_slot']]
        out.update(wear_slot=SLOTS[i['wear_slot']], armor=base + L // per, weight=weight, value=20 * L + 30)
    elif kind == 'treasure':
        out.update(weight=1, value=30 * L + 25)
    elif kind == 'food':
        out.update(food_value=12 + L // 3, nutrition=12 + L // 3, weight=1, value=5 + L)
    elif kind == 'potion':
        out.update(spell_effects=['cure_light' if L < 12 else 'cure_serious' if L < 25 else 'cure_critical'],
                   weight=1, value=40 + 10 * L)
    elif kind == 'light':
        out.update(light_hours=48, weight=2, value=15 + 2 * L)
    if i.get('bonus'):
        out['affects'] = [{'type': k, 'value': int(v)} for k, v in i['bonus'].items()]
    return out


def _avg(dice, default=0):
    import re
    m = re.match(r'\s*(\d+)d(\d+)\s*([+-]\s*\d+)?', str(dice or ''))
    if not m:
        return default
    return int(m.group(1)) * (int(m.group(2)) + 1) / 2 + int((m.group(3) or '0').replace(' ', ''))


def ranked(proto, rank):
    """What a rank lifts in an old creature: its health, blows and experience up to the rank's
    curve at its level (never down: a creature built tougher stays so)."""
    if rank not in ('elite', 'sub-boss', 'boss'):
        return {}
    want, out = numbers(proto.get('level') or 1, rank), {}
    have = proto.get('max_hp') or _avg(proto.get('hp_dice'))
    if want['max_hp'] > have:
        out.update(max_hp=want['max_hp'], hp=want['max_hp'], hp_dice=want['hp_dice'])
    if _avg(want['damage_dice']) > _avg(proto.get('damage_dice')):
        out['damage_dice'] = want['damage_dice']
    for k in ('hitroll', 'damroll', 'xp', 'exp'):
        if want[k] > (proto.get(k) or 0):
            out[k] = want[k]
    return out


def load(pop_dir=POP_DIR) -> dict:
    out = {}
    for f in sorted(glob.glob(os.path.join(pop_dir, 'zone_*.json'))):
        try:
            with open(f, encoding='utf-8') as fh:
                d = json.load(fh)
            out[int(d.get('zone'))] = d
        except Exception as e:
            logger.warning(f"population: {os.path.basename(f)}: {e}")
    return out


def apply(world, data=None) -> list:
    """Place the bosses and lock the doors; returns what could not be done."""
    problems = []
    for z, d in (data if data is not None else load()).items():
        # how clever its creatures fight ({"tier": "brutal"}; brain/profile.py)
        zone = (getattr(world, 'zones', None) or {}).get(int(z))
        if zone is not None and d.get('ai'):
            zone.ai = d['ai']
        # the zone's own items (prototypes, as the build-out makes them: words, level and kind;
        # the numbers from item_numbers). Its creatures carry or drop them by vnum.
        for v, it in (d.get('items') or {}).items():
            v = int(v)
            # (applied twice, as a test may: its own item again is no clash)
            if v in world.obj_prototypes and world.obj_prototypes[v].get('_population') != int(z):
                problems.append(f"zone {z}: item {v} is taken already")
                continue
            try:
                world.obj_prototypes[v] = {'vnum': v, '_population': int(z), 'name': ' '.join(str(it['keywords']).split()),
                                           'short_desc': it['short_desc'], 'room_desc': it['room_desc'],
                                           'description': it['description'], **item_numbers(it)}
            except (KeyError, ValueError, TypeError) as e:
                problems.append(f"zone {z}: item {v}: {e!r}")
        # the zone's own creatures (prototypes: a rebuild of world/zones keeps them)
        for v, proto in (d.get('creatures') or {}).items():
            v = int(v)
            if 'name' not in proto:
                if v not in world.mob_prototypes:
                    problems.append(f"zone {z}: no creature {v} to give {sorted(proto)}")
                else:       # an old creature given a rank or helpers (a rank lifts its numbers to fit)
                    old = world.mob_prototypes[v]
                    # (numbers the entry states win over the rank's: a zone tuned by hand)
                    new = dict(old)
                    new.update(ranked(old, proto.get('rank')))
                    new.update({k: x for k, x in proto.items() if k != 'why'})
                    world.mob_prototypes[v] = new
                continue
            p = dict(proto)
            p['vnum'] = v
            if 'level' in p:
                for k, x in numbers(p['level'], p.get('rank')).items():
                    p.setdefault(k, x)
            p.setdefault('max_hp', p.get('hp', 1000))
            p.setdefault('hp', p['max_hp'])
            if p.get('rank') == 'boss' and 'boss' not in (p.get('flags') or []):
                p['flags'] = list(p.get('flags') or []) + ['boss']
            world.mob_prototypes[v] = p
        # where they live: each room named gets one (max per room)
        for sp in d.get('spawns') or []:
            vnum = int(sp['vnum'])
            if vnum not in world.mob_prototypes:
                problems.append(f"zone {z}: no creature {vnum}")
                continue
            # a reset's max counts the creature across the whole zone (world.reset_zone): one in
            # each room named means that many in all, plus any patrols of the same kind
            rooms_named = sp.get('rooms') or []
            total = sum(len(x.get('rooms') or []) for x in d.get('spawns') or [] if int(x['vnum']) == vnum) \
                + sum(1 for pt in d.get('patrols') or [] if int(pt['vnum']) == vnum)
            for rv in rooms_named:
                room = world.rooms.get(int(rv))
                if room is None:
                    problems.append(f"zone {z}: no room {rv} for {vnum}")
                    continue
                room.mob_resets.append({'vnum': vnum, 'max': max(int(sp.get('max', 1)), total)})
        # fill (tools/audit/densify.py): more of the zone's own ordinary creatures, in empty rooms
        # near where they already live. Every reset of the creature in the zone counts to the new
        # total, so the old rooms keep theirs.
        zone_rooms = None
        for fl in ([] if os.environ.get('MH_NO_FILL') else d.get('fill') or []):   # (densify.py plans without them)
            vnum, total = int(fl['vnum']), int(fl['total'])
            if vnum not in world.mob_prototypes:
                problems.append(f"zone {z}: no creature {vnum} to fill with")
                continue
            if zone_rooms is None:
                zone_rooms = [r for r in world.rooms.values() if getattr(getattr(r, 'zone', None), 'number', None) == int(z)]
            for r in zone_rooms:
                for m in r.mob_resets or []:
                    if isinstance(m, dict) and int(m.get('vnum', -1)) == vnum and not m.get('route'):
                        m['max'] = max(int(m.get('max', 1)), total)
            for rv in fl.get('rooms') or []:
                room = world.rooms.get(int(rv))
                if room is None:
                    problems.append(f"zone {z}: no room {rv} to fill")
                    continue
                room.mob_resets.append({'vnum': vnum, 'max': total})
        # patrols: start at the route's first room and walk it (mobs.patrol_ai)
        for pt in d.get('patrols') or []:
            vnum, route = int(pt['vnum']), [int(r) for r in pt.get('route') or []]
            bad = [r for r in route if r not in world.rooms]
            if vnum not in world.mob_prototypes or not route or bad:
                problems.append(f"zone {z}: patrol {vnum} route {bad or route}")
                continue
            # the route goes with the reset, so two patrols of one kind walk two routes (world.reset_zone)
            world.rooms[route[0]].mob_resets.append({'vnum': vnum, 'max': 1, 'route': route})
        for b in d.get('bosses') or []:
            vnum, room = int(b['vnum']), world.rooms.get(int(b['room']))
            if room is None or vnum not in world.mob_prototypes:
                problems.append(f"zone {z}: boss {vnum} or room {b.get('room')} missing")
                continue
            for r in world.rooms.values():
                if r.mob_resets:
                    r.mob_resets = [m for m in r.mob_resets if int(m.get('vnum', -1)) != vnum]
            room.mob_resets.append({'vnum': vnum, 'max': 1})
            if b.get('mechanics'):
                world.mob_prototypes[vnum]['mechanics'] = b['mechanics']   # boss_mechanics.py
        # a boss who comes when someone walks into his lair, and shuts them in (lairs.py): no reset
        # places him anywhere
        for b in d.get('lairs') or []:
            import lairs
            vnum = int(b['vnum'])
            problem = lairs.register(world, b, int(z))
            if problem:
                problems.append(f"zone {z}: {problem}")
                continue
            for r in world.rooms.values():
                if r.mob_resets:
                    r.mob_resets = [m for m in r.mob_resets if int(m.get('vnum', -1)) != vnum]
            if b.get('mechanics'):
                world.mob_prototypes[vnum]['mechanics'] = b['mechanics']
        for dd in d.get('doors') or []:
            room = world.rooms.get(int(dd['room']))
            ex = (room.exits or {}).get(dd['dir']) if room else None
            if not isinstance(ex, dict):
                problems.append(f"zone {z}: no exit {dd.get('dir')} in room {dd.get('room')}")
                continue
            door = ex.get('door') if isinstance(ex.get('door'), dict) else {}
            door.update({'name': dd.get('name') or door.get('name') or 'door', 'state': 'closed', 'locked': True,
                         'key_vnum': int(dd['key'])})
            ex['door'] = door
    for p in problems:
        logger.warning(f"population: {p}")
    return problems
