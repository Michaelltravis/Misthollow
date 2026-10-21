"""How clever a creature fights: its zone's tier, then its rank, its roles and its own numbers
(world/ai_profiles.json), resolved once when its brain is made.

    floors <- tier <- rank (add / mul / set) <- each role's template <- the creature's own "ai.profile"

and then held inside INVARIANTS, the limits that keep every fight answerable. Data can make a
creature gentler than these, never harsher: a wind-up is always long enough to see, a room never
holds more warnings than can be read, a chase always ends.
"""
import json
import logging
import os
import statistics

logger = logging.getLogger('Misthollow.Brain')

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    'world', 'ai_profiles.json')

# (key, 'min' | 'max', the code's limit, the floors key that may only make it stricter)
INVARIANTS = (
    ('windup_s', 'min', 3.0, None),                       # round mode: resolves next round at the soonest
    ('windup_action_s', 'min', 1.2, 'windup_action_s'),   # real time: never too quick to see
    ('room_windup_cap', 'max', 4, 'room_windup_cap_max'),
    ('leash_rooms', 'max', 10, 'leash_rooms_max'),
    ('chase_secs', 'max', 120, 'chase_secs_max'),
    ('train_cap', 'max', 6, 'train_cap'),
)

_data = None


def data():
    """world/ai_profiles.json, read once (reload() reads it again)."""
    global _data
    if _data is None:
        try:
            with open(PATH, encoding='utf-8') as f:
                _data = json.load(f)
        except (OSError, ValueError) as e:
            logger.error(f"brain: {PATH}: {e}; every creature fights as before")
            _data = {}
    return _data


def reload():
    global _data
    _data = None
    return data()


def feature(name) -> bool:
    return bool((data().get('features') or {}).get(name))


def tier_named(name, _seen=None) -> dict:
    """A tier's numbers, its "inherit" chain filled in under it."""
    tiers = data().get('tiers') or {}
    t = tiers.get(name)
    if t is None:
        return {}
    _seen = _seen or set()
    base = {}
    parent = t.get('inherit')
    if parent and parent not in _seen:
        _seen.add(name)
        base = tier_named(parent, _seen)
    base.update({k: v for k, v in t.items() if k != 'inherit'})
    return base


def zone_level(zone) -> int:
    """The median level of a zone's creatures (the same idea as tools/balance/zones.zone_level)."""
    cached = getattr(zone, '_ai_level', None)
    if cached is not None:
        return cached
    levels = [int(p.get('level') or 1) for p in (getattr(zone, 'mobs', None) or {}).values()
              if isinstance(p, dict)]
    lv = int(statistics.median(levels)) if levels else 1
    try:
        zone._ai_level = lv
    except AttributeError:
        pass
    return lv


def zone_tier(zone) -> str:
    """The tier a population file names for the zone, else the one its level falls in."""
    named = (getattr(zone, 'ai', None) or {}).get('tier') if zone is not None else None
    if named:
        return named
    if zone is None:
        return 'readable'
    lv = zone_level(zone)
    tier = 'readable'
    for at, name in (data().get('zone_tiers') or {}).get('by_level') or ():
        if lv >= at:
            tier = name
    return tier


def _home_zone(mob):
    room = getattr(mob, 'room', None)
    zone = getattr(room, 'zone', None)
    world = getattr(mob, 'world', None)
    home = getattr(mob, 'home_zone', None)
    if home is not None and world is not None:
        zone = (getattr(world, 'zones', None) or {}).get(home, zone)
    return zone


def _apply_rank(p, rank):
    r = (data().get('ranks') or {}).get(rank or 'regular') or {}
    for k, v in (r.get('add') or {}).items():
        p[k] = (p.get(k) or 0) + v
    for k, v in (r.get('mul') or {}).items():
        p[k] = (p.get(k) if p.get(k) is not None else 1.0) * v
    p.update(r.get('set') or {})


def clamp(p) -> dict:
    """Hold a profile inside INVARIANTS (and inside floors, where they are stricter)."""
    floors = data().get('floors') or {}
    for key, how, limit, floor_key in INVARIANTS:
        if floor_key is not None and floors.get(floor_key) is not None:
            f = floors[floor_key]
            limit = max(limit, f) if how == 'min' else min(limit, f)
        if p.get(key) is None:
            continue
        p[key] = max(p[key], limit) if how == 'min' else min(p[key], limit)
    return p


def resolve(mob, roles=()) -> dict:
    """The numbers this creature thinks with."""
    zone = _home_zone(mob)
    tier = zone_tier(zone)
    p = tier_named(tier) or tier_named('readable')
    p['tier'] = tier
    p.setdefault('special_rate', 1.0)
    rank = getattr(mob, 'rank', None) or 'regular'
    p['rank'] = rank
    _apply_rank(p, rank)
    templates = data().get('roles') or {}
    for role in sorted(roles):
        p.update(templates.get(role) or {})
    own = (getattr(mob, 'ai_data', None) or {}).get('profile') or {}
    p.update(own)
    return clamp(p)
