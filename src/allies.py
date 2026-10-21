"""Creatures that come to each other's aid (a zone's population: world/population, a creature's
`helpers`: {"group": "castle", "rooms": 2, "count": 3}). When a player attacks one, others of
its group within `rooms` steps who are free rush in and join the fight (a boss's call_guards
works the same way: boss_mechanics.py). One whose helpers say "answer": false calls for help
but never comes (a shopkeeper calls the watch; the watch comes). One whose helpers say
"anywhere": true comes from anywhere in its zone (the Captain of the Wall, to any watchman
attacked on the wall), and goes back to its post when the fight is done (return_to_post).
"""


def _group(mob):
    h = getattr(mob, 'helpers', None) or {}
    return h.get('group') if isinstance(h, dict) else None


def nearby_allies(mob, rooms=2, want=3):
    """Free creatures of mob's group, nearest first: [(creature, room it is in)]."""
    group, room = _group(mob), mob.room
    if not group or room is None:
        return []
    out, seen, frontier = [], {room.vnum}, [room]
    for _ in range(rooms):
        nxt = []
        for r in frontier:
            for ex in (r.exits or {}).values():
                to = ex.get('room') if isinstance(ex, dict) else None
                if to is None or to.vnum in seen or to.zone is not room.zone:
                    continue
                door = ex.get('door')
                if isinstance(door, dict) and door.get('state') == 'closed':
                    continue               # a shut door keeps help out
                seen.add(to.vnum)
                nxt.append(to)
                for m in to.characters:
                    if len(out) >= want:
                        return out
                    if m is mob or hasattr(m, 'connection') or getattr(m, 'fighting', None) or getattr(m, 'hp', 0) <= 0:
                        continue
                    if _group(m) == group and (m.helpers or {}).get('answer', True):
                        out.append((m, to))
        frontier = nxt
    return out


def far_allies(mob, near=()):
    """Free creatures of mob's group anywhere in its zone whose helpers say "anywhere"."""
    group, room = _group(mob), mob.room
    zone = getattr(room, 'zone', None)
    if not group or zone is None:
        return []
    out = []
    for r in (getattr(zone, 'rooms', None) or {}).values():
        if r is room:
            continue
        for m in r.characters:
            h = getattr(m, 'helpers', None) or {}
            if (isinstance(h, dict) and h.get('anywhere') and _group(m) == group and m is not mob and m not in near
                    and not hasattr(m, 'connection') and not getattr(m, 'fighting', None) and getattr(m, 'hp', 0) > 0):
                out.append((m, r))
    return out


async def rally(mob, attacker):
    import reach
    if reach.pulled(mob):
        return []          # struck from the next room (reach.py): only the one aimed at comes
    h = getattr(mob, 'helpers', None) or {}
    came = nearby_allies(mob, int(h.get('rooms', 2)), int(h.get('count', 2)))
    far = far_allies(mob, [m for m, _ in came])
    if not came and not far:
        return []
    room = mob.room
    await room.send_to_room(h.get('shout') or f"{mob.name} cries out for help!")
    for m, frm in came + far:
        frm.characters.remove(m)
        m.room = room
        room.characters.append(m)
        if (m, frm) in far:
            m._post = getattr(m, '_post', None) or frm
            await room.send_to_room(f"{m.name} hears the call and comes running to help {mob.name}!")
        else:
            await room.send_to_room(f"{m.name} rushes in to help {mob.name}!")
        m.fighting, m.position = attacker, 'fighting'
        try:
            await m._notify_move(frm, room, 'somewhere', 'somewhere')
        except Exception:
            pass
    return [m for m, _ in came + far]


async def return_to_post(mob):
    """One who came from afar to help goes back to its post once it is no longer fighting."""
    post = getattr(mob, '_post', None)
    if post is None or getattr(mob, 'fighting', None) or getattr(mob, 'hp', 0) <= 0:
        return False
    mob._post = None
    room = mob.room
    if room is post or room is None:
        return False
    room.characters.remove(mob)
    await room.send_to_room(f"{mob.name} goes back to the post.")
    mob.room = post
    post.characters.append(mob)
    await post.send_to_room(f"{mob.name} returns to the post.")
    return True
