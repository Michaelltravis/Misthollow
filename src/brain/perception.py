"""What a creature notices (features.pursuit): its eyes and ears.

Sight: everyone in its own room, and anyone in a room joined to it by an open way (no closed
door) within the profile's `sight_m` metres: measured on the zone map for /play players,
NEIGHBOUR_M for a telnet player (no position: about half a room away). Dark halves the range.
Never through a closed door, never while it sleeps or is blind.
- invisible: only to a creature that detects invisibility (the spell) or is `aware`;
- hidden or sneaking: one roll, the creature's eyes against the player's stealth (the old
  aggressive_ai roll, now used across rooms too), remembered a few seconds so a hider isn't
  re-rolled every tick; a spotted hider is revealed.

Hostile on sight (`hostile_to`): an `aggressive` (or `hostile`) creature; one that hates the
player's alignment (`aggr_good`, `aggr_evil`, `aggr_neutral`); one whose faction hates them; one
with a `memory` that holds a grudge (it was hurt by them in the last MEMORY_SECS). Never in a
peaceful room, never an immortal it must leave alone, and in a city never a player more than five
levels below it.

Hearing: a fight or a door being pounded within `hear_rooms` rooms through open ways (a closed
door counts as one room more). Investigated only where the profile says so (`investigate`:
brutal zones, and `aware`, `hunter` or `tracker` creatures anywhere).
"""
import time

NEIGHBOUR_M = 12.0
SPOT_MEMORY = 5.0        # seconds a stealth roll stands
MEMORY_SECS = 600.0      # a creature with a memory holds a grudge this long
GOOD, EVIL = 350, -350   # alignments (CircleMUD)


def _flags(ch):
    return set(getattr(ch, 'flags', None) or ())


def _aff(ch):
    return set(getattr(ch, 'affect_flags', None) or ())


def awake(mob) -> bool:
    return getattr(mob, 'position', None) not in ('sleeping', 'stunned', 'incapacitated', 'dead') \
        and 'blind' not in _aff(mob)


def open_ways(room):
    """[(direction, room, through_door)] the rooms an exit leads to; through_door: closed."""
    out = []
    for d, ex in (getattr(room, 'exits', None) or {}).items():
        to = ex.get('room') if isinstance(ex, dict) else None
        if to is None:
            continue
        door = ex.get('door')
        out.append((d, to, isinstance(door, dict) and door.get('state') == 'closed'))
    return out


def _dark(mob, room):
    try:
        return room.is_dark(mob.world.game_time)
    except Exception:
        return False


def _distance(mob, ch):
    """Metres to someone across an open way: on the zone map for a /play player, NEIGHBOUR_M for
    one with no position (telnet: they would otherwise be measured from the room's centre)."""
    try:
        import combat_range as cr
        if cr.pos_of(ch) is None:
            return NEIGHBOUR_M
        import reach
        d = reach.distance(mob.world, mob, ch)
    except Exception:
        d = None
    return d if d is not None else NEIGHBOUR_M


def _stealth_roll(mob, b, ch):
    """True if the creature spots this hider/sneaker (rolled once a SPOT_MEMORY seconds)."""
    now = time.time()
    memo = b.encounter.setdefault('spot', {})
    got = memo.get(ch)
    if got is not None and now < got[0]:
        return got[1]
    env = 0
    room = getattr(ch, 'room', None)
    if room is not None and _dark(mob, room):
        env += 20
    if getattr(room, 'sector_type', '') in ('forest', 'swamp'):
        env += 10
    if hasattr(ch, 'has_light_source') and ch.has_light_source():
        env -= 25
    rng = b.rng
    detection = int(getattr(mob, 'level', 1) or 1) * 3 + int(getattr(mob, 'detect_bonus', 0) or 0) + rng.randint(1, 20)
    if 'aware' in _flags(mob):
        detection += 25
    skills = getattr(ch, 'skills', None) or {}
    stealth = max(skills.get('hide', 0), skills.get('sneak', 0)) + env + rng.randint(1, 20)
    seen = stealth < detection
    memo[ch] = (now + SPOT_MEMORY, seen)
    return seen


def sees(mob, b, ch, far=False) -> bool:
    """Whether the creature sees this character now (same room, or across an open way when far)."""
    if ch is mob or getattr(ch, 'hp', 0) <= 0:
        return False
    from mobs import spared
    if spared(ch) or not awake(mob):
        return False
    aff = _aff(ch)
    if 'invisible' in aff and not ('detect_invisible' in _aff(mob) or 'aware' in _flags(mob)):
        return False
    if far:
        rng_m = b.profile.get('sight_m', 16)
        if _dark(mob, getattr(ch, 'room', None)):
            rng_m /= 2
        d = _distance(mob, ch)
        if 'tracks_covered' in aff:
            d *= 2
        if d > rng_m:
            return False
    if {'hidden', 'sneaking'} & _flags(ch):
        return _stealth_roll(mob, b, ch)
    return True


def hostile_to(mob, ch) -> bool:
    """Whether the creature attacks this player on sight."""
    if not hasattr(ch, 'connection'):
        return False
    from mobs import spared
    if spared(ch):
        return False
    room = getattr(mob, 'room', None)
    flags = _flags(mob)
    import reach
    from .targeting import owned
    if 'no_attack' in flags or getattr(mob, 'special', None) in reach.SERVICE or owned(mob):
        return False
    if (getattr(getattr(ch, 'room', None), 'sector_type', '') == 'city' or getattr(room, 'sector_type', '') == 'city') \
            and getattr(mob, 'level', 0) - getattr(ch, 'level', 0) > 5:
        return False
    if (getattr(mob, 'lost_quarry', None) or {}).get(getattr(ch, 'name', ''), 0) > time.time():
        return False                               # they just got away from it (reach.lost)
    if {'aggressive', 'hostile'} & flags:
        return True
    al = int(getattr(ch, 'alignment', 0) or 0)
    if ('aggr_good' in flags and al >= GOOD) or ('aggr_evil' in flags and al <= EVIL) \
            or ('aggr_neutral' in flags and EVIL < al < GOOD):
        return True
    if 'memory' in flags:
        g = (getattr(mob, 'grudge_list', None) or {}).get(getattr(ch, 'name', None))
        if g and time.time() - g.get('time', 0) < MEMORY_SECS:
            return True
    if getattr(mob, 'faction', None):
        try:
            from factions import FactionManager
            key = FactionManager.normalize_key(mob.faction)
            if key and FactionManager.is_hostile(ch, key):
                return True
        except Exception:
            pass
    return False


def look(mob, b):
    """(target, far) the first hostile the creature sees: in its own room first, then the nearest
    across an open way; else (None, False). Spotted hiders are revealed."""
    room = getattr(mob, 'room', None)
    if room is None or 'peaceful' in (room.flags or ()):
        return None, False
    for ch in room.characters:
        if hasattr(ch, 'connection') and not getattr(ch, 'is_fighting', False) and hostile_to(mob, ch) \
                and sees(mob, b, ch):
            return ch, False
    from mobs import KEEP_OUT
    best, best_d = None, None
    for _d, to, shut in open_ways(room):
        if shut or 'peaceful' in (to.flags or ()) or (KEEP_OUT & set(to.flags or ())):
            continue
        for ch in to.characters:
            if hasattr(ch, 'connection') and hostile_to(mob, ch) and sees(mob, b, ch, far=True):
                d = _distance(mob, ch)
                if best_d is None or d < best_d:
                    best, best_d = ch, d
    return best, best is not None


def rooms_within(room, n):
    """{room: steps} within n steps through exits (a closed door costs one step more)."""
    out, frontier = {room: 0}, [(room, 0)]
    while frontier:
        nxt = []
        for r, k in frontier:
            for _d, to, shut in open_ways(r):
                cost = k + 1 + (1 if shut else 0)
                if cost <= n and (to not in out or out[to] > cost):
                    out[to] = cost
                    nxt.append((to, cost))
        frontier = nxt
    return out


def hears(mob, b):
    """A noise worth going to (a fight, a door pounded) within hear_rooms: its room, else None."""
    p = b.profile
    if not (p.get('investigate') or {'aware', 'hunter', 'tracker'} & _flags(mob)):
        return None
    n = int(p.get('hear_rooms', 1) or 0)
    if n <= 0 or getattr(mob, 'room', None) is None:
        return None
    now = time.time()
    best = None
    for r, k in rooms_within(mob.room, n).items():
        if k == 0:
            continue
        loud = now - (getattr(r, '_noise_at', 0) or 0) < 4.0
        if not loud:
            loud = any(getattr(ch, 'fighting', None) is not None and hasattr(ch, 'connection') for ch in r.characters)
        if loud and (best is None or k < best[1]):
            best = (r, k)
    return best[0] if best else None


def make_noise(room):
    """A loud thing happened here (a door pounded, broken)."""
    try:
        room._noise_at = time.time()
    except AttributeError:
        pass
