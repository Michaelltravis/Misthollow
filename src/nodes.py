"""Herb and ore spots out in the open world (docs/GAMEPLAY_POLISH.md, group 4).

Foraging and mining work anywhere the ground allows (crafting.py); some rooms also hold a spot
worth stopping for: a herb patch in a forest, field or marsh, an ore vein on a hillside, a
mountain or in a dungeon. Where one is (and where in the room) is fixed by the room, so every
player finds it in the same place. Worked, it gives surely and gives more (two finds, the second
from the better half of the ground's table), then it is spent for a while (RESPAWN seconds).
The 3D client draws each (the map payload's nearby rooms carry `node`) and a click works it.
"""
import time

RESPAWN = 300           # seconds a worked spot takes to come back
SHARE = 22              # of every 100 rooms of the right ground, how many hold a spot
ROOM_W, ROOM_H = 24, 15  # (combat_range.py: a room's metres)


def _kind(room):
    from crafting import FORAGE_MATERIALS, MINE_MATERIALS
    flags = set(getattr(room, 'flags', None) or ())
    if flags & {'peaceful', 'death', 'imm_only', 'godroom'}:
        return None
    sector = getattr(room, 'sector_type', '') or ''
    if sector in MINE_MATERIALS:
        return 'ore'
    if sector in FORAGE_MATERIALS:
        return 'herb'
    return None


def node_of(room):
    """{'k': 'herb'|'ore', 'x', 'z'} (room metres) for a room that holds a spot, else None."""
    if room is None or getattr(room, 'vnum', None) is None:
        return None
    kind = _kind(room)
    if not kind:
        return None
    h = (int(room.vnum) * 2654435761) & 0xffffffff
    if h % 100 >= SHARE:
        return None
    return {'k': kind, 'x': 3.5 + (h >> 8) % (ROOM_W - 7), 'z': 3.5 + (h >> 16) % (ROOM_H - 7)}


def ready(room):
    return time.time() >= getattr(room, 'node_ready_at', 0)


def take(room):
    room.node_ready_at = time.time() + RESPAWN


def at(room, kind):
    """The spot of this kind in the room, if there is one and it is ready to work."""
    n = node_of(room)
    return n if n and n['k'] == kind and ready(room) else None


def payload(room):
    n = node_of(room)
    if n:
        n['ready'] = ready(room)
    return n
