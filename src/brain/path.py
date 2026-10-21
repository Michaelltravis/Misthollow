"""The way somewhere (features.pursuit): the cheapest route through the rooms, doors and all.

    open way             1
    a closed door        +OPEN_COST for a creature with hands (it opens it: `opens_doors`)
    a locked door        +UNLOCK_COST if it carries the key
    a closed or locked   +BASH_COST for a brute (`bash_doors`: readable "brutes", the big ones;
      door, no way in      brutal "strong", any humanoid of level 20 or more): it pounds it down

Never through a door bound by magic (doors.unbreakable), a barricade or a Block Door seal; never
into a room creatures keep out of, a peaceful room, out of its home zone, or (in a readable zone)
into a city's streets after someone. Returns [(direction, how)], how in walk / open / unlock / bash.
"""
import heapq
import time

OPEN_COST, UNLOCK_COST, BASH_COST = 2, 3, 6
ANIMALS = {'animal', 'beast', 'insect', 'spider', 'arachnid', 'wolf', 'canine', 'feline', 'bear', 'rat', 'rodent',
           'snake', 'reptile', 'serpent', 'bird', 'fish', 'plant', 'slime', 'ooze', 'jelly', 'elemental',
           'dragon', 'wyrm', 'worm', 'bat', 'boar', 'horse', 'deer', 'dog', 'cat', 'fox', 'crab', 'scorpion'}


def _words(mob):
    import mob_ai
    return mob_ai._keywords_set(mob) | set(mob_ai._name_lower(mob).split())


HUMANOIDS = {'human', 'elf', 'half-elf', 'dwarf', 'gnome', 'halfling', 'orc', 'half-orc', 'goblin', 'hobgoblin',
             'bugbear', 'kobold', 'gnoll', 'ogre', 'troll', 'giant', 'lizardman', 'drow', 'duergar', 'minotaur',
             'undead', 'demon', 'humanoid'}


def race_of(mob) -> str:
    race = getattr(mob, 'race', None)
    if not race:
        protos = getattr(getattr(mob, 'world', None), 'mob_prototypes', None) or {}
        race = (protos.get(getattr(mob, 'vnum', None)) or {}).get('race')
    return str(race or '').lower()


def has_hands(mob) -> bool:
    race = race_of(mob)
    if race in HUMANOIDS:
        return True
    if race in ANIMALS:
        return False
    return not (_words(mob) & ANIMALS)


def brute(mob, b) -> bool:
    import mob_ai
    how = b.profile.get('bash_doors', 'brutes')
    big = bool(_words(mob) & mob_ai.BIG_KEYWORDS) or getattr(mob, 'rank', None) in ('boss', 'sub-boss')
    if how == 'strong':
        return big or (has_hands(mob) and int(getattr(mob, 'level', 1) or 1) >= 20)
    return big


def opener(mob, b) -> bool:
    how = b.profile.get('opens_doors', 'humanoid')
    return how == 'any' or (how == 'humanoid' and has_hands(mob))


def door_cost(mob, b, door):
    """(extra cost, how) to get through a door, or None (it can't)."""
    import doors
    if not isinstance(door, dict) or door.get('state') != 'closed':
        return 0, 'walk'
    now = time.time()
    if doors.unbreakable(door) or (door.get('barricaded_until', 0) or 0) > now or (door.get('sealed_until', 0) or 0) > now:
        return None
    if not door.get('locked'):
        if opener(mob, b):
            return OPEN_COST, 'open'
        return (BASH_COST, 'bash') if brute(mob, b) else None
    try:
        if doors.has_key(door, doors.carried_keys(mob)) and opener(mob, b):
            return UNLOCK_COST, 'unlock'
    except Exception:
        pass
    return (BASH_COST, 'bash') if brute(mob, b) else None


def allowed(mob, b, room) -> bool:
    from mobs import KEEP_OUT
    flags = set(getattr(room, 'flags', None) or ())
    if KEEP_OUT & flags or 'peaceful' in flags:
        return False
    home = getattr(mob, 'home_zone', None)
    if home is not None and getattr(getattr(room, 'zone', None), 'number', None) != home:
        return False
    if b.profile.get('tier') != 'brutal' and getattr(room, 'sector_type', '') == 'city' \
            and getattr(getattr(mob, 'room', None), 'sector_type', '') != 'city':
        return False                     # (a readable zone's creatures don't chase into town)
    return True


def route(mob, b, start, goal, limit=12):
    """[(direction, how)] the cheapest way from start to goal within `limit` steps, else None."""
    if start is None or goal is None:
        return None
    if start is goal:
        return []
    best = {start: 0}
    q = [(0, 0, id(start), start, [])]
    while q:
        cost, steps, _, room, path = heapq.heappop(q)
        if room is goal:
            return path
        if steps >= limit or cost > best.get(room, 1e9):
            continue
        for d, ex in (getattr(room, 'exits', None) or {}).items():
            to = ex.get('room') if isinstance(ex, dict) else None
            if to is None or (to is not goal and not allowed(mob, b, to)) or (to is goal and not allowed(mob, b, to)):
                continue
            dc = door_cost(mob, b, ex.get('door'))
            if dc is None:
                continue
            c = cost + 1 + dc[0]
            if c < best.get(to, 1e9):
                best[to] = c
                heapq.heappush(q, (c, steps + 1, id(to), to, path + [(d, dc[1])]))
    return None


def steps(mob, b, a, z, limit=12):
    r = route(mob, b, a, z, limit)
    return None if r is None else len(r)


def rooms_apart(a, z, limit=12):
    """Rooms between a and z through any exit, doors or not (how far from home a chase has
    gone), within limit, else None."""
    if a is None or z is None:
        return None
    if a is z:
        return 0
    seen, frontier, n = {a}, [a], 0
    while frontier and n < limit:
        n += 1
        nxt = []
        for r in frontier:
            for ex in (getattr(r, 'exits', None) or {}).values():
                to = ex.get('room') if isinstance(ex, dict) else None
                if to is None or to in seen:
                    continue
                if to is z:
                    return n
                seen.add(to)
                nxt.append(to)
        frontier = nxt
    return None
