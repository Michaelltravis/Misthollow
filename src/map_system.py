"""
Map rendering and coordinate utilities for Misthollow.
"""

import itertools
import re
import time
from typing import Dict, Tuple, Set, List, Optional

from config import Config
from affects import AffectManager
import nodes as _nodes

DIR_OFFSETS = {
    'north': (0, -1, 0),
    'south': (0, 1, 0),
    'east': (1, 0, 0),
    'west': (-1, 0, 0),
    'up': (0, 0, 1),
    'down': (0, 0, -1),
}

REVERSE_DIR = {
    'north': 'south',
    'south': 'north',
    'east': 'west',
    'west': 'east',
    'up': 'down',
    'down': 'up',
}


def get_room_symbol(room) -> str:
    """Return symbol for a room based on type/flags."""
    if not room:
        return '·'

    flags = set(room.flags) if hasattr(room, 'flags') else set()
    name = room.name.lower() if hasattr(room, 'name') and room.name else ''
    sector = getattr(room, 'sector_type', 'inside')

    # Special overrides
    if 'shop' in flags or 'store' in name or 'shop' in name or 'merchant' in name:
        return '$'
    if 'important' in flags or 'quest' in flags or 'boss' in flags or 'temple' in name or 'castle' in name:
        return '!'

    # Terrain-based
    if sector in ('city', 'inside') or 'indoors' in flags:
        return '□'
    if sector == 'forest':
        return '♣'
    if sector in ('water_swim', 'water_noswim', 'underwater'):
        return '≈'
    if sector in ('mountain', 'hills'):
        return '▲'
    if sector in ('dungeon',) or 'underground' in flags:
        return '▼'

    return '·'


def get_room_icon(room) -> str:
    """Return emoji icon for a room based on type/flags (for web map)."""
    if not room:
        return '❓'

    flags = set(room.flags) if hasattr(room, 'flags') else set()
    name = room.name.lower() if hasattr(room, 'name') and room.name else ''
    sector = getattr(room, 'sector_type', 'inside')

    # Special locations
    if 'deathtrap' in flags:
        return '💀'
    if 'boss' in flags or 'boss' in name:
        return '👹'
    if 'shop' in flags or 'store' in name or 'shop' in name or 'merchant' in name:
        return '🛒'
    if 'bank' in name:
        return '🏦'
    if 'inn' in name or 'tavern' in name:
        return '🍺'
    if 'temple' in name or 'church' in name or 'altar' in name:
        return '⛪'
    if 'castle' in name or 'throne' in name or 'palace' in name:
        return '🏰'
    if 'guild' in name or 'trainer' in name:
        return '📚'
    if 'gate' in name or 'entrance' in name:
        return '🚪'
    if 'important' in flags or 'quest' in flags:
        return '⭐'
    
    # Underground / tunnels (check name before sector)
    if 'sewer' in name or 'drain' in name or 'pipe' in name:
        return '🚰'
    if 'tunnel' in name or 'passage' in name or 'corridor' in name:
        return '🕳️'
    if 'cave' in name or 'cavern' in name or 'grotto' in name:
        return '🦇'
    if 'crypt' in name or 'tomb' in name or 'catacomb' in name:
        return '⚰️'
    if 'mine' in name or 'shaft' in name:
        return '⛏️'

    # Terrain-based
    if sector == 'city':
        return '🏛️'
    if sector == 'inside':
        return '🏠'
    if sector == 'forest':
        return '🌲'
    if sector == 'field':
        return '🌾'
    if sector in ('water_swim', 'water_noswim'):
        return '🌊'
    if sector == 'underwater':
        return '🐠'
    if sector == 'mountain':
        return '⛰️'
    if sector == 'hills':
        return '🏔️'
    if sector == 'dungeon':
        return '🕯️'
    if sector == 'desert':
        return '🏜️'
    if sector == 'swamp':
        return '🐊'
    if sector == 'road':
        return '🛤️'
    if sector == 'sewer':
        return '🚰'
    if sector == 'cave':
        return '🦇'
    if sector == 'tunnel':
        return '🕳️'
    if 'underground' in flags:
        return '🕳️'

    return '📍'


def find_path(rooms: Dict[int, object], start_vnum: int, end_vnum: int, player=None) -> List[int]:
    """Find shortest path between two rooms using BFS. Returns list of vnums."""
    if start_vnum == end_vnum:
        return [start_vnum]
    if start_vnum not in rooms or end_vnum not in rooms:
        return []

    visited = {start_vnum}
    queue = [(start_vnum, [start_vnum])]

    while queue:
        current, path = queue.pop(0)
        room = rooms.get(current)
        if not room:
            continue

        for direction, exit_data in _iter_visible_exits(room, player):
            to_vnum = _get_exit_target_vnum(exit_data)
            if to_vnum is None or to_vnum in visited:
                continue
            if to_vnum not in rooms:
                continue

            new_path = path + [to_vnum]
            if to_vnum == end_vnum:
                return new_path

            visited.add(to_vnum)
            queue.append((to_vnum, new_path))

    return []  # No path found


def _iter_visible_exits(room, player=None):
    if not room:
        return []
    if hasattr(room, 'get_visible_exits'):
        return room.get_visible_exits(player).items()
    return room.exits.items() if hasattr(room, 'exits') else []


def _get_exit_target_vnum(exit_data) -> Optional[int]:
    if not exit_data:
        return None
    if isinstance(exit_data, dict):
        if 'to_room' in exit_data:
            return exit_data.get('to_room')
        to_room = exit_data.get('room')
        return getattr(to_room, 'vnum', None) if to_room else None
    return None


def compute_room_coords(rooms: Dict[int, object], start_vnum: Optional[int], player=None,
                        fixed: Optional[Dict[int, Tuple[int, int, int]]] = None) -> Dict[int, Tuple[int, int, int]]:
    """Assign coordinates to rooms using BFS based on exits.

    Rooms with a stored place (`fixed`: the atlas's, `room.map`) take it first; the rest are
    laid out from their placed neighbours. Handles multiple components by offsetting each
    component on the X axis.
    """
    coords: Dict[int, Tuple[int, int, int]] = {}
    if not rooms:
        return coords

    unvisited = set(rooms.keys())
    occupied = set()
    offset_x = 0

    def _zone_num(vnum):
        z = getattr(rooms[vnum], 'zone', None)
        return getattr(z, 'number', None)

    def _place(vnum, coord, dxyz):
        """Claim a grid cell; on collision slide further along the travel
        direction so distinct rooms never stack on one map square."""
        if coord not in occupied:
            coords[vnum] = coord
            occupied.add(coord)
            return coord
        dx, dy, dz = dxyz if dxyz != (0, 0, 0) else (1, 0, 0)
        x, y, z = coord
        for step in range(1, 8):
            cand = (x + dx * step, y + dy * step, z + dz * step)
            if cand not in occupied:
                coords[vnum] = cand
                occupied.add(cand)
                return cand
        coords[vnum] = coord    # give up: overlap beats omission
        return coord

    def bfs(seed_vnum: int, seed_coord: Tuple[int, int, int]):
        _place(seed_vnum, seed_coord, (0, 0, 0))
        unvisited.discard(seed_vnum)
        expand([seed_vnum])

    def expand(seeds):
        from collections import deque
        queue = deque(seeds)
        while queue:
            vnum = queue.popleft()
            room = rooms[vnum]
            x, y, z = coords[vnum]
            zone_here = _zone_num(vnum)
            # lay out the local zone before chasing cross-zone links, so a
            # town stays one coherent block on the map instead of being
            # scattered by whichever detour the BFS found first
            same, cross = [], []
            for direction, exit_data in _iter_visible_exits(room, player):
                if direction not in DIR_OFFSETS:
                    continue
                to_vnum = _get_exit_target_vnum(exit_data)
                if to_vnum not in rooms or to_vnum in coords:
                    continue
                (same if _zone_num(to_vnum) == zone_here else cross).append((direction, to_vnum))
            for direction, to_vnum in same + cross:
                if to_vnum in coords:
                    continue
                dx, dy, dz = DIR_OFFSETS[direction]
                _place(to_vnum, (x + dx, y + dy, z + dz), (dx, dy, dz))
                unvisited.discard(to_vnum)
                if _zone_num(to_vnum) == zone_here:
                    queue.appendleft(to_vnum)
                else:
                    queue.append(to_vnum)

    # stored places first, then the rooms without one grow out from them
    if fixed:
        placed = []
        for vnum in sorted(v for v in fixed if v in rooms):
            _place(vnum, tuple(fixed[vnum]), (1, 0, 0))
            unvisited.discard(vnum)
            placed.append(vnum)
        expand(placed)
        xs = [c[0] for c in coords.values()]
        if xs:
            offset_x = max(xs) + 3

    # Start with player's component if available
    if start_vnum in unvisited:
        bfs(start_vnum, (0, 0, 0))
        # Update offset AFTER player's BFS so disconnected components don't overlap
        xs = [c[0] for v, c in coords.items() if v in rooms]
        if xs:
            offset_x = max(xs) + 3

    # Layout remaining components
    while unvisited:
        seed = next(iter(unvisited))
        # Place new component to the right of previous components
        component_offset = (offset_x, 0, 0)
        bfs(seed, component_offset)
        # Update offset based on component bounds
        xs = [c[0] for v, c in coords.items() if v in rooms]
        if xs:
            offset_x = max(xs) + 3

    return coords


def stored_cells(rooms: Dict[int, object]) -> Dict[int, Tuple[int, int, int]]:
    """The map places rooms carry (`room.map`, the atlas's x/y/level), as layout cells. The atlas
    draws north as +y and the game as -y, so y turns over."""
    out = {}
    for v, r in rooms.items():
        m = getattr(r, 'map', None)
        if isinstance(m, dict) and 'x' in m and 'y' in m:
            try:
                out[v] = (int(m['x']), -int(m['y']), int(m.get('z', 0) or 0))
            except (TypeError, ValueError):
                continue
    return out


def world_cells(world) -> Dict[int, Tuple[int, int, int]]:
    """Stored places on one world map. Each zone's places are its own (the atlas charts every
    zone on its own sheet), so each zone gets an origin: the temple's zone sits at the origin,
    and a zone reached through a cross-zone exit is set so that the room the exit leads to lies
    one step that way from the room it leaves (zones without a link to a placed zone keep no
    stored places and are laid out as before)."""
    from collections import deque
    by_zone: Dict[int, Dict[int, Tuple[int, int, int]]] = {}
    for v, r in world.rooms.items():
        if r.zone is not None and getattr(r, 'map', None):
            c = stored_cells({v: r}).get(v)
            if c:
                by_zone.setdefault(r.zone.number, {})[v] = c
    if not by_zone:
        return {}
    temple = world.rooms.get(3001)
    first = temple.zone.number if temple is not None and temple.zone is not None and temple.zone.number in by_zone \
        else min(by_zone)
    origin = {first: (0, 0, 0)}
    queue = deque([first])
    while queue:
        za = queue.popleft()
        ox, oy, oz = origin[za]
        for v, (x, y, z) in by_zone[za].items():
            room = world.rooms[v]
            for d, ed in (room.exits or {}).items():
                if d not in DIR_OFFSETS or not isinstance(ed, dict):
                    continue
                to = _get_exit_target_vnum(ed)
                target = world.rooms.get(to)
                zb = target.zone.number if target is not None and target.zone is not None else None
                if zb is None or zb == za or zb in origin or zb not in by_zone or to not in by_zone[zb]:
                    continue
                dx, dy, dz = DIR_OFFSETS[d]
                tx, ty, tz = by_zone[zb][to]
                origin[zb] = (ox + x + dx - tx, oy + y + dy - ty, oz + z + dz - tz)
                queue.append(zb)
    out = {}
    for z, cells in by_zone.items():
        if z in origin:
            ox, oy, oz = origin[z]
            for v, (x, y, zz) in cells.items():
                out[v] = (x + ox, y + oy, zz + oz)
    return out


def check_stored_cells(world) -> List[str]:
    """What the stored map places get wrong, zone by zone: two rooms on one cell, or a compass
    exit pointing away from where its room sits (it will show as a passage, not an open way).
    Logged at load; empty while no room stores a place."""
    problems = []
    by_zone: Dict[int, Dict[int, object]] = {}
    for v, r in world.rooms.items():
        if getattr(r, 'map', None) and r.zone is not None:
            by_zone.setdefault(r.zone.number, {})[v] = r
    for z, rooms in sorted(by_zone.items()):
        cells = stored_cells(rooms)
        seen: Dict[Tuple[int, int, int], int] = {}
        for v, c in sorted(cells.items()):
            if c in seen:
                problems.append(f'zone {z}: rooms {seen[c]} and {v} share the cell {c}')
            else:
                seen[c] = v
        for v, r in rooms.items():
            for d, ed in (r.exits or {}).items():
                if d not in CARDINALS or not isinstance(ed, dict):
                    continue
                to = _get_exit_target_vnum(ed)
                if to in cells and v in cells and cells[to][2] == cells[v][2]:
                    dx, dy, _ = DIR_OFFSETS[d]
                    vx, vy = cells[to][0] - cells[v][0], cells[to][1] - cells[v][1]
                    if (vx > 0) - (vx < 0) != dx or (vy > 0) - (vy < 0) != dy:
                        problems.append(f'zone {z}: {v} {d} -> {to} points away from where {to} sits')
    return problems


def get_frontier_coords(coords: Dict[int, Tuple[int, int, int]], rooms: Dict[int, object], explored: Set[int], player=None) -> list:
    """Returns list of dicts with x, y, z and optional deathtrap flag."""
    frontier_map = {}  # (x,y,z) -> {info}
    occupied_coords = set(coords.values())
    world = player.world if player and hasattr(player, 'world') else None
    for vnum, (x, y, z) in coords.items():
        if vnum not in explored:
            continue
        room = rooms.get(vnum)
        for direction, exit_data in _iter_visible_exits(room, player):
            if direction not in DIR_OFFSETS:
                continue
            to_vnum = _get_exit_target_vnum(exit_data)
            dx, dy, dz = DIR_OFFSETS[direction]
            if not to_vnum or to_vnum not in explored:
                coord = (x + dx, y + dy, z + dz)
                # Skip if an explored room already occupies this coordinate
                if coord in occupied_coords:
                    continue
                # Also skip if coord is already a frontier entry
                if coord not in frontier_map:
                    # Check if the destination is a deathtrap
                    is_deathtrap = False
                    dest_name = None
                    if to_vnum and world:
                        dest_room = world.rooms.get(to_vnum)
                        if dest_room:
                            dest_flags = set(dest_room.flags) if hasattr(dest_room, 'flags') else set()
                            is_deathtrap = 'deathtrap' in dest_flags
                            dest_name = dest_room.name if hasattr(dest_room, 'name') else None
                    # Also check exit description for danger warnings
                    if not is_deathtrap and isinstance(exit_data, dict):
                        desc = exit_data.get('description', '')
                        if 'DANGER' in desc or 'deathtrap' in desc.lower():
                            is_deathtrap = True
                    frontier_map[coord] = {
                        'x': coord[0], 'y': coord[1], 'z': coord[2],
                        'deathtrap': is_deathtrap,
                        'name': dest_name,
                    }
    return list(frontier_map.values())


def render_ascii_map(player, mode: str = 'local', size: int = 11) -> str:
    """Render ASCII map for a player."""
    c = player.config.COLORS
    explored = set(getattr(player, 'explored_rooms', set()))

    # Filter rooms by mode
    rooms: Dict[int, object] = {}
    if mode in ('zone', 'near') and player.room and player.room.zone:
        zone_rooms = set(player.room.zone.rooms.keys())
        for vnum in explored:
            if vnum in zone_rooms:
                room = player.world.rooms.get(vnum)
                if room:
                    rooms[vnum] = room
    else:
        for vnum in explored:
            room = player.world.rooms.get(vnum)
            if room:
                rooms[vnum] = room

    if not rooms:
        return f"{c['yellow']}You haven't explored any rooms yet.{c['reset']}"

    start_vnum = player.room.vnum if player.room else None
    coords = compute_room_coords(rooms, start_vnum, player)
    if start_vnum not in coords:
        return f"{c['yellow']}Your current location is unknown to the map.{c['reset']}"

    player_x, player_y, player_z = coords[start_vnum]
    frontier = get_frontier_coords(coords, rooms, explored, player)

    # Determine bounds
    if mode == 'full':
        frontier_pts = [(f['x'], f['y'], f['z']) for f in frontier]
        points = list(coords.values()) + frontier_pts
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)
    else:
        radius = size // 2
        min_x = player_x - radius
        max_x = player_x + radius
        min_y = player_y - radius
        max_y = player_y + radius

    # Build grid (rooms at even coordinates, exits in between)
    width = (max_x - min_x) * 2 + 1
    height = (max_y - min_y) * 2 + 1
    grid = [[' ' for _ in range(width)] for _ in range(height)]

    def to_grid(x, y):
        gx = (x - min_x) * 2
        gy = (y - min_y) * 2
        return gx, gy

    # Draw exits and rooms
    for vnum, (x, y, z) in coords.items():
        if z != player_z:
            continue
        if x < min_x or x > max_x or y < min_y or y > max_y:
            continue
        room = rooms.get(vnum)
        gx, gy = to_grid(x, y)
        symbol = get_room_symbol(room)
        if vnum == start_vnum:
            symbol = f"{c['bright_yellow']}@{c['reset']}"
        grid[gy][gx] = symbol

        # Draw exits
        for direction, exit_data in _iter_visible_exits(room, player):
            if direction not in DIR_OFFSETS:
                continue
            to_vnum = _get_exit_target_vnum(exit_data)
            dx, dy, dz = DIR_OFFSETS[direction]
            ex = x + dx
            ey = y + dy
            ez = z + dz
            if ez != player_z:
                # indicate up/down diagonals for explored destinations
                if to_vnum in explored:
                    if direction == 'up':
                        ex_g, ey_g = gx + 1, gy - 1
                        if 0 <= ey_g < height and 0 <= ex_g < width:
                            grid[ey_g][ex_g] = '/'
                    elif direction == 'down':
                        ex_g, ey_g = gx + 1, gy + 1
                        if 0 <= ey_g < height and 0 <= ex_g < width:
                            grid[ey_g][ex_g] = '\\'
                continue

            if ex < min_x or ex > max_x or ey < min_y or ey > max_y:
                continue

            # only draw if explored
            if to_vnum in explored:
                ex_g, ey_g = to_grid(ex, ey)
                mid_x = (gx + ex_g) // 2
                mid_y = (gy + ey_g) // 2
                grid[mid_y][mid_x] = '─' if direction in ('east', 'west') else '│'

    # Draw frontier
    for f in frontier:
        x, y, z = f['x'], f['y'], f['z']
        if z != player_z:
            continue
        if x < min_x or x > max_x or y < min_y or y > max_y:
            continue
        gx, gy = to_grid(x, y)
        if grid[gy][gx] == ' ':
            grid[gy][gx] = '?'

    # Build output
    title = "Explored Map"
    if mode == 'zone' and player.room and player.room.zone:
        title = f"{player.room.zone.name}"

    lines = [f"{c['cyan']}[{title}] (Z={player_z}){c['reset']}"]
    for row in grid:
        lines.append(''.join(row))
    return '\n'.join(lines)


def _exp_thresholds(player):
    """Return (exp floor of current level, exp needed for next level).

    exp is cumulative, so within-level progress is
    (exp - floor) / (next - floor). Mirrors Player.exp_to_level().
    """
    try:
        nxt = player.exp_to_level()
    except Exception:
        return 0, 0
    lvl = getattr(player, 'level', 1)
    if lvl <= 1:
        return 0, nxt
    cfg = player.config
    thr = getattr(cfg, 'HIGH_LEVEL_THRESHOLD', 30)
    prev = lvl - 1
    if prev <= thr:
        floor = int(cfg.BASE_EXP * (cfg.EXP_MULTIPLIER ** (prev - 1)))
    else:
        level_30 = int(cfg.BASE_EXP * (cfg.EXP_MULTIPLIER ** (thr - 1)))
        floor = int(level_30 * (getattr(cfg, 'HIGH_LEVEL_EXP_MULTIPLIER', 1.6) ** (prev - thr)))
    return floor, nxt


def _build_set_by_vnum():
    """vnum -> named-set key, so the client can theme each set piece uniquely."""
    out = {}
    try:
        from sets import NAMED_SETS
        for sid, cfg in NAMED_SETS.items():
            for vnum in cfg.get('pieces', {}):
                out[vnum] = sid
    except Exception:
        pass
    return out


_SET_BY_VNUM = _build_set_by_vnum()


def _wear_slot(item):
    """Where an item is worn, as the server would put it (named or read from its name: "iron
    greaves" are legs), for the /play inventory's drag and drop."""
    slot = getattr(item, 'wear_slot', None)
    if slot:
        return slot
    try:
        from objects import infer_wear_slot
        return infer_wear_slot(item) if getattr(item, 'item_type', '') not in ('weapon', 'food', 'drink', 'potion', 'scroll', 'container', 'key', 'trash') else None
    except Exception:
        return None


def _gear_rules(player):
    try:
        import class_gear
        return class_gear.for_client(player)
    except Exception:
        return None


def item_info(item):
    """Compact item payload used for ground items, inventory and equipment:
    enough for the client to draw a real icon and rarity border."""
    vnum = getattr(item, 'vnum', None)
    itype = getattr(item, 'item_type', 'other')
    info = {
        'name': getattr(item, 'name', 'something'),
        'short': getattr(item, 'short_desc', '') or getattr(item, 'name', 'something'),
        'type': itype,
        'slot': _wear_slot(item),
        'rarity': getattr(item, 'rarity', 'common'),
        'set_id': getattr(item, 'set_id', None),
        'set_key': _SET_BY_VNUM.get(vnum),
        'level': getattr(item, 'level', 0),
        'affects': getattr(item, 'affects', []) or [],
        'weight': getattr(item, 'weight', 0),
        'cost': getattr(item, 'cost', 0),
    }
    if getattr(item, 'fixed', False):
        info['fixed'] = True      # a fixture: part of the room, not loot
    if itype in ('weapon', 'armor', 'worn', 'treasure'):
        # what the class rules look at (class_gear.py): 'w:sword:2', 's' (a shield), 'a:3' (plate)
        try:
            import class_gear
            gk = class_gear.client_key(item, info['slot'])
            if gk:
                info['gk'] = gk
        except Exception:
            pass
    # a corpse shows what it holds, so the 3D client's loot window can list it
    if itype == 'container' and str(info['name']).lower().startswith('corpse of'):
        info['contents'] = [item_info(it) for it in (getattr(item, 'contents', None) or [])[:30]]
        info['gold'] = int(getattr(item, 'gold', 0) or 0)
    if itype in ('weapon', 'armor', 'worn') or getattr(item, 'wear_slot', None):
        # the item's level (from the creatures that carry it) and how fine it looks (gear_look.py)
        try:
            import gear_look
            info['level'] = gear_look.item_level(item)
            info['tier'] = gear_look.item_tier(item)
        except Exception:
            pass
    # type-specific combat stats so the client can show a real tooltip
    if itype == 'weapon':
        info['damage_dice'] = getattr(item, 'damage_dice', None)
        info['weapon_type'] = getattr(item, 'weapon_type', None)
    elif itype == 'armor':
        info['armor'] = getattr(item, 'armor', 0)
    elif itype == 'light':
        info['light_hours'] = getattr(item, 'light_hours', 0)
    elif itype in ('food',):
        info['food_value'] = getattr(item, 'food_value', 0)
    elif itype in ('drink', 'fountain'):
        info['drinks'] = getattr(item, 'drinks', 0)
    # what it does in a fight, and its set with each tier (procs.py)
    try:
        import procs
        lines = procs.item_lines(item)
    except Exception:
        lines = []
    if lines:
        info['procs'] = lines
    return info


CLASS_RESOURCE = {
    # class -> (attribute, display name, maximum)
    'warrior': ('momentum', 'Momentum', 10),
    'thief': ('luck_points', 'Luck', 10),
    'assassin': ('intel_points', 'Intel', 10),
    'cleric': ('faith', 'Faith', 10),
    'paladin': ('holy_power', 'Holy Power', 5),
    'ranger': ('focus', 'Focus', 100),
    'necromancer': ('soul_shards', 'Soul Shards', 10),
    'bard': ('inspiration', 'Inspiration', 10),
}


def _class_resource(player):
    """The class's signature combat resource, for the client resource chip."""
    spec = CLASS_RESOURCE.get(str(getattr(player, 'char_class', '')).lower())
    if not spec:
        return None
    attr, label, cap = spec
    return {'name': label, 'value': int(getattr(player, attr, 0) or 0), 'max': cap}


def _sight(player):
    """How the player sees the room they stand in, for /play to light it as the text tells it: a
    dark room ("It is pitch black") is dark, a carried light lights a circle round the hero, and
    infravision or a rogue's eyes see it dimly without one."""
    room = getattr(player, 'room', None)
    try:
        dark = bool(room is not None and room.is_dark(getattr(getattr(player, 'world', None), 'game_time', None)))
    except Exception:
        dark = False
    if not dark:
        return {'dark': False}
    try:
        light = bool(player.has_light_source())
        see = bool(player.can_see_in_dark())
    except Exception:
        light, see = False, False
    return {'dark': True, 'light': light, 'see': see}


def _charges(player):
    """Charges a class builds and spends beside its mana (a mage's arcane charges), for the pips
    by the portrait in /play; None for a class without."""
    if str(getattr(player, 'char_class', '')).lower() != 'mage':
        return None
    try:
        from spells import arcane_max
        cap = arcane_max(player)
    except Exception:
        cap = getattr(player, 'max_arcane_charges', 5)
    return {'name': 'arcane', 'label': 'Arcane Charges', 'value': int(getattr(player, 'arcane_charges', 0) or 0), 'max': cap}


# what lingers on a creature that someone put there (its target frame shows them): a wound over
# time, and the harms that hold it (slowed, rooted, silenced, blinded, cursed...)
AILMENT_FLAGS = {'slow', 'slowed', 'entangled', 'rooted', 'silenced', 'stunned', 'blind', 'blinded', 'curse', 'cursed',
                 'poison', 'poisoned', 'weakened', 'sleep', 'asleep', 'charmed', 'feared', 'frozen', 'burning', 'bleeding'}


def _ailments(entity):
    """[{n: name, s: school, r: ticks left}] for a creature's target frame (at most six)."""
    out = []
    for a in getattr(entity, 'affects', None) or ():
        kind = str(getattr(a, 'type', '') or '')
        applies = str(getattr(a, 'applies_to', '') or '').lower()
        harmful = kind == 'dot' or applies in AILMENT_FLAGS or (kind == 'modify_stat' and (getattr(a, 'value', 0) or 0) < 0)
        if not harmful:
            continue
        name = str(getattr(a, 'name', '') or '')
        try:
            from combat_hooks import _school_of_label
            school = _school_of_label(name) if kind == 'dot' else None
        except Exception:
            school = None
        out.append({'n': name, 's': school, 'r': int(getattr(a, 'remaining', 0) or 0), 'dot': kind == 'dot'})
        if len(out) >= 6:
            break
    return out


def _mount_info(player):
    """The mount the player is currently riding (for a 'riding X' HUD chip and
    in-world rider art), or None when on foot."""
    m = getattr(player, 'mount', None)
    if not m:
        return None
    return {
        'key': getattr(m, 'key', ''),
        'name': getattr(m, 'name', 'mount'),
        'can_fly': bool(getattr(m, 'can_fly', False)),
        'loyalty': getattr(m, 'loyalty', None),
    }


def _owned_mounts(player):
    """The mounts the player owns, [{key, name}] (the hero's right-click menu in /play)."""
    try:
        from mounts import MountManager
    except Exception:
        return []
    out = []
    for m in getattr(player, 'owned_mounts', None) or []:
        key = m if isinstance(m, str) else (m or {}).get('key')
        tmpl = MountManager.get_mount_template(key) if key else None
        if tmpl:
            out.append({'key': key, 'name': tmpl.get('name', key)})
    return out


# the spells on someone that the 3D client shows on their body for as long as they last
# (world3d/wards.js): the flags they set, and a few spells known by name that set only stats
WARD_FLAGS = frozenset({
    'sanctuary', 'shielded', 'armour_ward', 'divine_shield', 'invulnerable', 'mana_shield', 'holy_shield',
    'stoneskin', 'ice_armor', 'fire_shield', 'mirror_image', 'displacement', 'blink', 'fly', 'haste',
    'invisible', 'prot_evil', 'prot_good', 'regenerating', 'spell_reflect', 'shadowform', 'beacon_of_light',
    'aegis_ward', 'briskness', 'guardian_spirit', 'spirit_link', 'slow', 'entangled', 'silenced', 'stunned',
    'poisoned', 'tracks_covered',
})
# a wound over time that is a poison shows as one (the 3D client: green bubbles and haze, wards.js)
WARD_NAMES = {'barkskin': 'barkskin', 'bless': 'bless', 'poison': 'poisoned', 'knife_poison': 'poisoned',
              'serpent_sting': 'poisoned', 'wound_poison': 'poisoned', 'deadly_poison': 'poisoned', 'plague': 'poisoned'}
# the harms that hold a body, by their flag (wards.js draws each: an eye band, a sleeper's Zzz...)
STATUS_FLAGS = {'blind': 'blinded', 'sleeping': 'asleep', 'charmed': 'charmed', 'feared': 'feared',
                'paralyzed': 'paralyzed', 'diseased': 'weakened'}
# ...and by what the harm is called: a burn, a bleed, a frost, a curse (wounds over time, and the
# spells that lower a stat or hold the body)
_BURN = re.compile(r'burn|ignit|immolat|scorch|combust|flame|fire|pyre|searing|blaze')
_BLEED = re.compile(r'bleed|rupture|rend|lacerat|hemorr|gore|serrat|garrote(?!_silence)')
_FROST = re.compile(r'frost|freez|frozen|\bice|ice_|chill|cold|glacia|rime|blizzard')
_CURSE = re.compile(r'curse|hex|doom|wither|weaken|enfeebl|bane|mistrot|black_arrow|affliction|agony')
_HOLDS = {'slow', 'stunned', 'paralyzed', 'entangled', 'dex', 'hitroll', 'damroll', 'str', 'armor_class'}


def _harm_ward(a):
    """The ward key a harmful affect shows as (a burn, a bleed, a frost, a curse), or None."""
    name = str(getattr(a, 'name', '') or '').lower().replace(' ', '_')
    kind = str(getattr(a, 'type', '') or '')
    if kind == AffectManager.TYPE_DOT:
        if _BURN.search(name):
            return 'burning'
        if _BLEED.search(name):
            return 'bleeding'
        if _FROST.search(name):
            return 'frozen'
        if _CURSE.search(name):
            return 'cursed'
        return None
    if kind == AffectManager.TYPE_HOT:
        return None
    to = str(getattr(a, 'applies_to', '') or '')
    try:
        lowered = float(getattr(a, 'value', 0) or 0) < 0
    except (TypeError, ValueError):
        lowered = False
    harmful = to in ('slow', 'stunned', 'paralyzed', 'entangled') or (to in _HOLDS and lowered)
    if not harmful:
        return None
    if _FROST.search(name):
        return 'frozen'
    if _CURSE.search(name) or name == 'weakened':
        return 'cursed'
    return None


def _wards(entity):
    """What a character wears from spells, for the 3D client: a sorted list of ward keys."""
    flags = set(getattr(entity, 'affect_flags', None) or ())
    out = flags & WARD_FLAGS
    out |= {STATUS_FLAGS[f] for f in flags if f in STATUS_FLAGS}
    for a in getattr(entity, 'affects', None) or ():
        key = WARD_NAMES.get(str(getattr(a, 'name', '') or '').lower().replace(' ', '_')) or _harm_ward(a)
        if key:
            out.add(key)
    if (getattr(entity, 'blinded_rounds', 0) or 0) > 0:      # sand in the eyes (Pocket Sand)
        out.add('blinded')
    if getattr(entity, 'elite', False):                       # a rare (elites.py): its gold glow
        out.add('elite')
    return sorted(out)


def _speed(player):
    """How fast the player travels, a multiple of walking pace (mounts.travel_speed)."""
    try:
        from mounts import travel_speed
        return travel_speed(player)
    except Exception:
        return 1.0


def _intent_public(entity):
    """A mob's declared wind-up in client shape, or None. Covers both the
    mob_ai pending_intent system and the bosses.py cast telegraphs, so the
    web UI paints one uniform enemy wind-up bar."""
    import time as _time
    now = _time.time()
    intent = getattr(entity, 'pending_intent', None)
    if intent:
        # resolves at the first combat tick past the windup — i.e. the next
        # round boundary, ~4s after declaration
        return {
            'kind': intent.get('kind', 'heavy'),
            'label': intent.get('label', 'Attack'),
            'interruptible': bool(intent.get('interruptible')),
            'resolve_in': round(max(0.0, intent.get('declared_at', now) + Config.COMBAT_ROUND_SECONDS + 1.3 - now), 1),
        }
    ai_state = getattr(entity, 'ai_state', None)
    cast = ai_state.get('cast') if isinstance(ai_state, dict) else None
    if cast and not cast.get('interrupted'):
        ability = cast.get('ability', {})
        return {
            'kind': 'cast',
            'label': str(ability.get('name', 'casting')).replace('_', ' ').title(),
            'interruptible': bool(ability.get('interruptible')),
            'resolve_in': round(max(0.0, cast.get('resolve_at', now) - now), 1),
        }
    return None


def _reaction_ready(player):
    """Which reaction commands are off cooldown, for the client prompt chips."""
    import time as _time
    now = _time.time()
    return {
        'brace': now >= getattr(player, 'brace_cooldown_until', 0),
        'sidestep': now >= getattr(player, 'sidestep_cooldown_until', 0),
        'interrupt': now >= getattr(player, 'interrupt_cooldown_until', 0),
    }


def _cooldowns(player):
    """Active ability cooldowns the client can paint on the action bar.

    Skill cooldowns are stored as scattered per-player attributes (e.g.
    ``backstab_cooldown_until``, ``second_wind_cooldown_until``,
    ``rallying_cry_cooldown``) all on the ``time.time()`` epoch. Scan for them
    and return ``{skill_key: seconds_remaining}`` for every one still ticking,
    so a warrior/thief/assassin (whose bars are skills, not spells) actually
    sees cooldowns the way casters already do via /abilities."""
    import time as _time
    now = _time.time()
    out = {}
    for attr in list(vars(player).keys()):
        if attr.endswith('_cooldown_until'):
            key = attr[:-len('_cooldown_until')]
        elif attr.endswith('_cooldown'):
            key = attr[:-len('_cooldown')]
        elif attr.endswith('_cd'):   # warrior_abilities stores bash_cd, rally_cd, ...
            key = attr[:-len('_cd')]
        else:
            continue
        if not key:
            continue
        try:
            rem = float(getattr(player, attr, 0) or 0) - now
        except (TypeError, ValueError):
            continue
        # an epoch timestamp in the near future; the upper bound keeps a stray
        # plain-number attribute (e.g. a small counter) from being mistaken for
        # a cooldown when it slips past the 0.4s floor
        if 0.4 < rem < 86400:
            out[key] = round(rem, 1)
    # the marquee abilities' long cooldowns (marquee_abilities.py) and the spells' own
    # (spells.py), each kept in one dict
    timers = list((getattr(player, 'marquee_cd', None) or {}).items()) + list((getattr(player, 'spell_cd', None) or {}).items())
    for key, until in timers:
        try:
            rem = float(until) - now
        except (TypeError, ValueError):
            continue
        if 0.4 < rem < 86400:
            out[key] = round(rem, 1)
    # abilities renamed for the 3D action bar keep their old timer names
    # (towerbolt runs on arcane_blast's cooldown): report them under both
    try:
        from commands import _SKILL_RENAMES
        for new, old in _SKILL_RENAMES.items():
            if old in out and new not in out:
                out[new] = out[old]
    except Exception:
        pass
    return out


def _worn_aura(player):
    """'legendary' when any legendary piece is worn; 'set' at 4+ pieces of one set."""
    import gear_look
    return gear_look.worn_aura(player)


def _look(entity):
    """How a character's gear looks, for the 3D client (gear_look.py)."""
    try:
        import gear_look
        return gear_look.look_of(entity)
    except Exception:
        return None


def _gear_stats(player):
    """What worn gear adds to each attribute and maximum ({'str': 2, 'max_hp': 200}), non-zero only."""
    if not hasattr(player, 'gear_bonus'):
        return {}
    try:
        from player import GEAR_STATS
        return {k: v for k in GEAR_STATS if (v := int(player.gear_bonus(k)))}
    except Exception:
        return {}


def _gear_wards(player):
    """What a player's worn gear wards against, in words: ['fire 20%', 'shadow 75%', 'saves +2',
    'spells 10%', 'hasted'] (empty: nothing)."""
    if not hasattr(player, 'resistance'):
        return []
    try:
        from player import RESIST_KEYS
        out = [f'{k} {player.resistance(k)}%' for k in RESIST_KEYS if player.resistance(k)]
        if player.gear_saves():
            out.append(f'saves {player.gear_saves():+d}')
        gear_spell = player.gear_bonus('spell_resist')
        if gear_spell:
            out.append(f'spells {int(gear_spell)}%')
        if player.gear_hasted():
            out.append('hasted')
        import zone_hazards
        if zone_hazards._gear_flag(player, 'water_breathing'):
            out.append('breathes water')
        if zone_hazards._gear_flag(player, 'corruption_immunity'):
            out.append('corruption immune')
        song = player.get_equipment_bonus('song_power')
        if song > 0:
            out.append(f'songs +{song * 10}%')
        return out
    except Exception:
        return []


def _npc_look(mob):
    """A creature's look, when its zone dressed it (not the gear every creature is handed) and
    something of it shows: a weapon, a shield, a helm, armour or a cloak."""
    if not getattr(mob, 'own_gear', False):
        return None
    look = _look(mob)
    if look and any(k in look for k in ('main', 'off', 'head', 'body', 'back')):
        return look
    return None


def _in_combat(player) -> bool:
    """True only for a LIVE fight: target alive and in the same room.
    Stale fighting references must never wedge graphical clients."""
    f = getattr(player, 'fighting', None)
    if not f:
        return False
    if getattr(f, 'hp', 0) <= 0:
        return False
    room = getattr(player, 'room', None)
    if not room or f not in getattr(room, 'characters', []):
        return False
    return True


def _path_active(player):
    try:
        from paths import PathManager
        if PathManager.lone_wolf_active(player):
            return 'lone_wolf'
        if PathManager.fellowship_active(player):
            return 'fellowship'
    except Exception:
        pass
    return None


# party-frame roles, inferred from class
_GROUP_ROLES = {
    'warrior': 'tank', 'paladin': 'tank',
    'cleric': 'healer', 'bard': 'healer',
    'mage': 'dps', 'necromancer': 'dps', 'thief': 'dps',
    'assassin': 'dps', 'ranger': 'dps',
}
# strongest heal a class can cast on an ally, best first (underscore cast keys)
_HEAL_PRIORITY = ['heal', 'cure_critical', 'cure_serious', 'cure_light', 'lay_on_hands']


def _best_heal_spell(player):
    """The strongest single-target heal the viewer can cast on an ally, or None."""
    known = getattr(player, 'spells', None) or {}
    for key in _HEAL_PRIORITY:
        if key in known:
            return key
    return None


def _fighting_name(entity):
    f = getattr(entity, 'fighting', None)
    if not f or getattr(f, 'hp', 0) <= 0:
        return None
    return getattr(f, 'name', None)


import re as _re
# NPCs are never set to a sleeping position in data, but many are *described*
# asleep or at rest. Read the flavor text so those few render the right pose.
_POSE_SLEEP = _re.compile(r'\b(asleep|sleeping|sleeps here|slumber|snor(?:ing|es)|doz(?:ing|es)|napping|fallen asleep|obviously sl)\b', _re.I)
_POSE_REST = _re.compile(r'\b(rests here|resting (?:here|against)|dormant|reclin|lounging)\b', _re.I)


def _mob_pose(entity):
    """'sleeping' / 'resting' if the mob's description says so, else None.
    Cached on the prototype-shared mob since the text never changes."""
    cached = getattr(entity, '_pose_cache', '__none__')
    if cached != '__none__':
        return cached
    txt = ' '.join(str(getattr(entity, k, '') or '') for k in ('long_desc', 'description'))
    pose = 'sleeping' if _POSE_SLEEP.search(txt) else 'resting' if _POSE_REST.search(txt) else None
    try:
        entity._pose_cache = pose
    except Exception:
        pass
    return pose


def build_group_block(player) -> Optional[dict]:
    """Roster + live vitals for the player's party, for the UI party frames.

    Included in both map_data and the per-round combat_update so allied
    health/mana/target stay live during a fight. Returns None when solo.
    """
    group = getattr(player, 'group', None)
    roster = list(getattr(group, 'members', [])) if group else [player]
    # gather the player's pets + companions so they ride along in the bar
    minions = []
    try:
        from pets import PetManager
        minions += [(p, 'pet') for p in (PetManager.get_player_pets(player) or [])]
    except Exception:
        pass
    try:
        from companions import CompanionManager
        minions += [(c, 'companion') for c in (CompanionManager.get_player_companions(player) or [])]
    except Exception:
        pass
    # solo with no minions => no party bar
    if len(roster) < 2 and not minions:
        return None

    proom = getattr(player, 'room', None)
    pvnum = getattr(proom, 'vnum', None)
    # map adjacent room vnum -> direction, so split members get a heading
    dir_by_vnum = {}
    for direction, exit_data in _iter_visible_exits(proom, player):
        tv = _get_exit_target_vnum(exit_data)
        if tv is not None and tv not in dir_by_vnum:
            dir_by_vnum[tv] = direction

    members = []
    for m in roster:
        mroom = getattr(m, 'room', None)
        mvnum = getattr(mroom, 'vnum', None)
        same_room = mroom is proom and proom is not None
        cls = str(getattr(m, 'char_class', '') or '').lower()
        max_hp = getattr(m, 'max_hp', 1) or 1
        max_mana = getattr(m, 'max_mana', 1) or 1
        members.append({
            'name': getattr(m, 'name', 'Unknown'),
            'char_class': cls,
            'role': _GROUP_ROLES.get(cls, 'dps'),
            'level': getattr(m, 'level', 1),
            'hp': getattr(m, 'hp', 0),
            'maxHp': max_hp,
            'mana': getattr(m, 'mana', 0),
            'maxMana': max_mana,
            'move': getattr(m, 'move', 0),
            'maxMove': getattr(m, 'max_move', 1) or 1,
            'is_leader': bool(group) and m is group.leader,
            'is_self': m is player,
            'sameRoom': same_room,
            'roomName': getattr(mroom, 'name', '???') if mroom else '???',
            'roomVnum': mvnum,
            'dir': None if same_room else dir_by_vnum.get(mvnum),
            'fighting': _fighting_name(m),
            'online': getattr(m, 'connection', None) is not None or m is player,
            'dead': getattr(m, 'hp', 1) <= 0,
        })

    # pets & companions as compact sub-frames after their owner (you)
    for minion, kind in minions:
        mhp = getattr(minion, 'max_hp', 1) or 1
        members.append({
            'name': getattr(minion, 'name', kind), 'char_class': kind,
            'role': 'pet', 'level': getattr(minion, 'level', 1),
            'hp': getattr(minion, 'hp', 0), 'maxHp': mhp,
            'mana': 0, 'maxMana': 0, 'move': 0, 'maxMove': 1,
            'is_leader': False, 'is_self': False, 'is_minion': True, 'minion_kind': kind,
            'sameRoom': getattr(minion, 'room', None) is proom,
            'roomName': '', 'roomVnum': None, 'dir': None,
            'fighting': _fighting_name(minion),
            'online': True, 'dead': getattr(minion, 'hp', 1) <= 0,
        })

    return {
        'leader': getattr(group.leader, 'name', '') if group else getattr(player, 'name', ''),
        'loot_mode': getattr(group, 'loot_mode', 'freeforall') if group else 'freeforall',
        'auto_follow': bool(getattr(group, 'auto_follow', True)) if group else True,
        'exp_bonus': int((group.get_exp_bonus() - 1.0) * 100) if group else 0,
        'size': len(members),
        'is_leader': (player is group.leader) if group else True,
        'heal_spell': _best_heal_spell(player),
        'members': members,
    }


def build_combat_payload(player) -> dict:
    """Lightweight push for live combat: vitals + current-room entities only.

    Sent every violence round, so it must stay cheap — no BFS, no room list.
    """
    room = player.room
    mobs = []
    others = []
    if room and hasattr(room, 'characters'):
        for entity in room.characters:
            if hasattr(entity, 'account_name'):
                if entity is not player:
                    others.append({
                        'name': getattr(entity, 'name', 'Unknown'),
                        'level': getattr(entity, 'level', 1),
                        'char_class': getattr(entity, 'char_class', ''),
                        'hp': getattr(entity, 'hp', 0),
                        'maxHp': getattr(entity, 'max_hp', 1),
                        'lk': (_look(entity) or {}).get('sig'),
                        **_pos_fields(entity),
                        **_ally_combat(entity, player),
                    })
                continue
            quest_mark = ''
            if hasattr(entity, 'vnum'):
                try:
                    from quests import QuestManager
                    quest_mark = QuestManager.get_quest_giver_indicator(player, entity.vnum)
                except Exception:
                    quest_mark = ''
            mob = {
                'id': _mob_uid(entity),
                **_pos_fields(entity),
                'name': getattr(entity, 'name', 'Unknown'),
                'kw': _kw(entity),   # its keywords when named by description (3D body)
                'short': str(getattr(entity, 'short_desc', '') or ''),
                'long': str(getattr(entity, 'long_desc', '') or '')[:80],
                'pv': getattr(entity, 'vnum', None),
                'level': getattr(entity, 'level', 1),
                'hostile': getattr(entity, 'aggressive', False) or getattr(entity, 'hostile', False),
                'boss': 'boss' in (getattr(entity, 'flags', None) or []) or getattr(entity, 'is_boss', False),
                'rank': getattr(entity, 'rank', None),
                'roles': _mob_roles(entity),
                'shopkeeper': getattr(entity, 'special', '') == 'shopkeeper',
                'trainer': getattr(entity, 'special', '') in ('trainer', 'guildmaster'),
                'quest': quest_mark,
                'fighting': bool(getattr(entity, 'fighting', None) is player),
                'fighting_name': getattr(getattr(entity, 'fighting', None), 'name', '') or '',
            }
            hp = getattr(entity, 'hp', None)
            max_hp = getattr(entity, 'max_hp', None)
            if hp is not None and max_hp:
                mob['hp'] = hp
                mob['maxHp'] = max_hp
            intent = _intent_public(entity)
            if intent:
                mob['intent'] = intent
            # rhythm-combat state: poise meter, stagger window, raised guard
            import time as _t
            _tnow = _t.time()
            if getattr(entity, 'max_poise', 0):
                mob['poise'] = {'cur': getattr(entity, 'poise', 0), 'max': entity.max_poise}
            if _tnow < getattr(entity, 'staggered_until', 0):
                mob['staggered'] = round(getattr(entity, 'staggered_until', 0) - _tnow, 1)
            if _tnow < getattr(entity, 'guard_until', 0):
                mob['guarded'] = True
            mobs.append(mob)
    env = None
    if room is not None:
        try:
            from environment import env_public
            env = env_public(room, player)
        except Exception:
            env = None
    return {
        'type': 'combat_update',
        'vnum': room.vnum if room else None,
        'env': env,
        'in_combat': _in_combat(player),
        'sight': _sight(player),
        'player': {
            'name': player.name,
            'momentum': getattr(player, 'momentum', 0),
            'resource': _class_resource(player),
            'charges': _charges(player),
            'path': getattr(player, 'path', None),
            'path_active': _path_active(player),
            'stance': getattr(player, 'stance', getattr(player, 'combat_stance', getattr(player, 'mood', 'normal'))) or 'normal',
            'hp': getattr(player, 'hp', 0),
            'max_hp': getattr(player, 'max_hp', 1),
            'mana': getattr(player, 'mana', 0),
            'max_mana': getattr(player, 'max_mana', 1),
            'move': getattr(player, 'move', 0),
            'max_move': getattr(player, 'max_move', 1),
            'level': getattr(player, 'level', 1),
            'exp': getattr(player, 'exp', 0),
            'exp_floor': _exp_thresholds(player)[0],
            'exp_to_level': _exp_thresholds(player)[1],
            'gold': getattr(player, 'gold', 0),
            'cooldowns': _cooldowns(player),
            'reactions': _reaction_ready(player),
        },
        'mobs': mobs,
        'players': others,
        'group': build_group_block(player),
    }


_ZONEMAP_CACHE: Dict[int, dict] = {}
_MOB_UIDS = itertools.count(1)
_ZONECELL_INDEX: Dict[int, Dict[int, list]] = {}
CARDINALS = ('north', 'south', 'east', 'west')


def _door_info(exit_data, init=None) -> Optional[dict]:
    """A door on an exit, in either of the two formats the zone files use (`init`: the
    zone's starting state from doors.normalize, so the cached zonemap never goes stale
    differently per process; live state comes with map_data)."""
    if not isinstance(exit_data, dict):
        return None
    door = exit_data.get('door')
    if isinstance(door, dict):
        import doors as door_rules
        st = init or {'state': door.get('state'), 'locked': door.get('locked')}
        return {'name': door.get('name', 'door'), 'label': door_rules.label(door),
                'closed': st.get('state') == 'closed' or bool(door.get('closed')),
                'locked': bool(st.get('locked'))}
    flags = exit_data.get('flags') or []
    if 'door' in flags:
        name = (exit_data.get('keyword') or 'door').split()[0]
        return {'name': name, 'closed': 'closed' in flags, 'locked': 'locked' in flags}
    return None


def _quest_block(player):
    """The tracker's quest: the marquee quest (marquee.py), else the first unfinished ordinary
    one with where to go next (quest_guide.py)."""
    b = _marquee_block(player)
    if b:
        return b
    try:
        import quest_guide
        return quest_guide.guide_block(player)
    except Exception:
        return None


def _marquee_block(player):
    try:
        import marquee
        return marquee.quest_block(player)
    except Exception:
        return None


def build_zonemap(world, zone_num: int) -> Optional[dict]:
    """One zone laid out as a single continuous space for the 3D client (/play).

    The same BFS as the atlas, but over the zone's own rooms only (a zone laid out on
    its own misplaces far fewer exits than the global atlas), then:
      - every up/down level becomes its own island, side by side on x;
      - rooms the layout had to stack on one cell move to the nearest free cell;
      - every exit is classified: 'open' (the target sits in the next cell AND its
        opposite exit points back, so the two rooms can share an opening), 'passage'
        (same zone, any other placement, up/down, named exits) or 'zone' (another zone).
    Static data only (doors are reported as built; live door state is in map_data).
    Hidden exits are left out until the client knows which ones the player found."""
    if zone_num in _ZONEMAP_CACHE:
        return _ZONEMAP_CACHE[zone_num]
    zone = world.zones.get(zone_num)
    rooms = {v: r for v, r in world.rooms.items() if r.zone is not None and r.zone.number == zone_num}
    if not zone or not rooms:
        return None
    # two layouts: the atlas's own placement and one laid out from the exits alone; each is
    # relaxed (rooms that lead to each other moved side by side) and the one with fewer gaps
    # to hop is kept (the owner: "I'd love for the rooms to be seamless")
    coords, cells = min((_lay_out(rooms, fixed) for fixed in (stored_cells(rooms), {})),
                        key=lambda cc: _gaps(rooms, cc[1]))

    out_rooms = []
    links = set()
    for v, room in rooms.items():
        cx, cy = cells[v]
        exits = {}
        for direction, ed in (room.exits or {}).items():
            if not isinstance(ed, dict) or ed.get('hidden'):
                continue
            to = _get_exit_target_vnum(ed)
            target = world.rooms.get(to) if to is not None else None
            if not target:
                continue
            tz = target.zone.number if target.zone else None
            entry = {'to': to, 'kind': 'zone' if tz != zone_num else 'passage'}
            if 'imm_only' in (target.flags or []) and 'imm_only' not in (room.flags or []):
                entry['imm'] = True        # into the God Rooms: /play draws no way a mortal can't take
            if tz != zone_num:
                entry['zone'] = tz
                entry['toName'] = target.name
                entry['zoneName'] = getattr(target.zone, 'name', '') or ''
                links.add(tz)
            elif direction in CARDINALS and to in cells:
                ox, oy, _ = DIR_OFFSETS[direction]
                back = (target.exits or {}).get(REVERSE_DIR[direction])
                if (cells[to] == (cx + ox, cy + oy) and isinstance(back, dict)
                        and not back.get('hidden') and _get_exit_target_vnum(back) == v):
                    entry['kind'] = 'open'
            door = _door_info(ed, (getattr(world, 'door_init', None) or {}).get((v, direction)))
            if door:
                entry['door'] = door
            exits[direction] = entry
        out_rooms.append({
            'vnum': v, 'name': room.name, 'sector': getattr(room, 'sector_type', '') or '',
            'look': getattr(room, 'look', None) or getattr(room, 'sector_type', '') or '',   # room_looks.py
            'flags': list(room.flags) if hasattr(room, 'flags') else [],
            'description': getattr(room, 'description', '') or '',
            # what its words say stands in it (room_features.py): the client draws them
            'features': getattr(room, 'features', None) or [],
            'tone': getattr(room, 'tone', None),
            'setpiece': getattr(room, 'setpiece', None),
            'cell': [cx, cy], 'level': coords[v][2], 'exits': exits,
        })
    w = max(c[0] for c in cells.values()) + 1
    h = max(c[1] for c in cells.values()) + 1
    _ZONEMAP_CACHE[zone_num] = data = {
        'type': 'zonemap', 'zone': zone_num, 'name': zone.name,
        'size': [w, h], 'rooms': out_rooms, 'links': sorted(z for z in links if z is not None),
    }
    return data


def _lay_out(rooms, fixed):
    """(coords, cells) for a zone: levels as islands side by side, then relaxed."""
    coords = compute_room_coords(rooms, min(rooms), fixed=fixed)
    # islands: level 0 first, then 1, -1, 2, -2 ... each to the right of the last
    levels: Dict[int, List[int]] = {}
    for v, (x, y, z) in coords.items():
        levels.setdefault(z, []).append(v)
    cells: Dict[int, Tuple[int, int]] = {}
    taken: Set[Tuple[int, int]] = set()
    left = 0
    for z in sorted(levels, key=lambda lv: (abs(lv), -lv)):
        vs = levels[z]
        minx = min(coords[v][0] for v in vs)
        miny = min(coords[v][1] for v in vs)
        right = left
        for v in vs:   # coords keeps placement order, so the first claimant keeps a cell
            cell = (coords[v][0] - minx + left, coords[v][1] - miny)
            if cell in taken:
                cell = _nearest_free(cell, taken)
            cells[v] = cell
            taken.add(cell)
            right = max(right, cell[0])
        left = right + 3
    return coords, relax_cells(cells, rooms)


def _gaps(rooms, cells) -> int:
    """How many walkable joins (exits both ways) are not side by side: passages to hop."""
    n = 0
    for v, js in _joins(rooms, cells).items():
        for d, t in js:
            dx, dy = DIR_OFFSETS[d][:2]
            if (cells[t][0] - cells[v][0], cells[t][1] - cells[v][1]) != (dx, dy):
                n += 1
    return n


def _joins(rooms, cells):
    """Each room's walkable joins: (direction, neighbour) for a cardinal exit whose neighbour
    leads straight back (so the two could share an opening if they sat side by side)."""
    out = {}
    for v, room in rooms.items():
        lst = []
        for d in CARDINALS:
            ed = (room.exits or {}).get(d)
            if not isinstance(ed, dict) or ed.get('hidden'):
                continue
            t = _get_exit_target_vnum(ed)
            if t is None or t == v or t not in cells or t not in rooms:
                continue
            back = (rooms[t].exits or {}).get(REVERSE_DIR[d])
            if isinstance(back, dict) and not back.get('hidden') and _get_exit_target_vnum(back) == v:
                lst.append((d, t))
        out[v] = lst
    return out


def relax_cells(cells: Dict[int, Tuple[int, int]], rooms, passes: int = 8) -> Dict[int, Tuple[int, int]]:
    """Re-lay a zone's rooms so that rooms leading to each other sit side by side (then /play
    walks across instead of hopping a passage: the owner, "I'd love for the rooms to be
    seamless"). A room moves, or swaps cells with another, into the cell beside a room it
    leads to whenever that joins more exits than it breaks; repeated until nothing improves.
    Only ever gains: a join already made is never traded for nothing."""
    pos = dict(cells)
    at = {c: v for v, c in pos.items()}
    joins = _joins(rooms, pos)
    step = {d: DIR_OFFSETS[d][:2] for d in CARDINALS}

    def made(v, c, where):
        # joins of v that hold if v stood at c (others at `where`)
        n = 0
        for d, t in joins.get(v, ()):
            tc = c if t == v else where(t)
            if tc is not None and (tc[0] - c[0], tc[1] - c[1]) == step[d]:
                n += 1
        return n

    for _ in range(passes):
        moved = 0
        for v in sorted(pos):
            here = pos[v]
            js = joins.get(v)
            if not js:
                continue
            cur_where = lambda t: pos.get(t)
            base_v = made(v, here, cur_where)
            if base_v == len(js):
                continue
            best = None
            for d, t in js:
                tc = pos[t]
                c = (tc[0] - step[d][0], tc[1] - step[d][1])
                if c == here:
                    continue
                other = at.get(c)
                if other is None:
                    w = lambda x: pos.get(x)
                    gain = made(v, c, w) - base_v
                else:
                    def w(x, other=other, c=c):
                        return here if x == other else c if x == v else pos.get(x)
                    gain = (made(v, c, w) + made(other, here, w)) - (base_v + made(other, c, cur_where))
                    # a pair counted from both sides when v and other are linked: fine, both sides move together
                if gain > 0 and (best is None or gain > best[0]):
                    best = (gain, c, other)
            if best:
                _, c, other = best
                if other is None:
                    del at[here]
                else:
                    pos[other] = here
                    at[here] = other
                pos[v] = c
                at[c] = v
                moved += 1
        if not moved:
            break
    return pos


def _nearest_free(cell: Tuple[int, int], taken: Set[Tuple[int, int]]) -> Tuple[int, int]:
    x, y = cell
    for r in range(1, 64):
        ring = [(x + dx, y + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)
                if max(abs(dx), abs(dy)) == r and y + dy >= 0]
        for c in ring:
            if c not in taken:
                return c
    return (x + 64, y)


def zone_cell(world, vnum: int) -> Optional[Tuple[int, int, int]]:
    """(zone, cx, cy) of a room in its zone map."""
    room = world.rooms.get(vnum)
    if not room or not room.zone:
        return None
    zm = build_zonemap(world, room.zone.number)
    if not zm:
        return None
    idx = _ZONECELL_INDEX.get(zm['zone'])
    if idx is None:
        idx = _ZONECELL_INDEX[zm['zone']] = {r['vnum']: r['cell'] for r in zm['rooms']}
    c = idx.get(vnum)
    return (room.zone.number, c[0], c[1]) if c else None


_ATLAS_CACHE = None


def build_atlas(world) -> dict:
    """The complete world atlas: every room with coordinates and exit links,
    plus zone metadata and zone-to-zone connections. The world is static, so
    this is computed once and cached - it powers the full game map (M)."""
    global _ATLAS_CACHE
    if _ATLAS_CACHE is not None:
        return _ATLAS_CACHE

    coords = compute_room_coords(world.rooms, 3001, fixed=world_cells(world))
    zone_colors = [
        '#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899',
        '#f43f5e', '#ef4444', '#f97316', '#f59e0b', '#eab308',
        '#84cc16', '#22c55e', '#10b981', '#14b8a6', '#06b6d4',
        '#0ea5e9', '#3b82f6', '#6366f1', '#8b5cf6', '#a855f7',
    ]
    zones = {}
    rooms = []
    links = set()          # (zone_a, zone_b) pairs that touch
    for vnum, room in world.rooms.items():
        if vnum not in coords:
            continue
        x, y, z = coords[vnum]
        znum = room.zone.number if room.zone else -1
        if znum not in zones:
            zones[znum] = {
                'id': znum,
                'name': room.zone.name if room.zone else 'Unknown',
                'color': zone_colors[len(zones) % len(zone_colors)],
            }
        exits = {}
        for direction, exit_data in _iter_visible_exits(room, None):
            tv = _get_exit_target_vnum(exit_data)
            if tv and tv in world.rooms:
                exits[direction] = tv
                tz = world.rooms[tv].zone.number if world.rooms[tv].zone else -1
                if tz != znum:
                    links.add((min(znum, tz), max(znum, tz)))
        rooms.append({
            'vnum': vnum, 'name': room.name, 'zone': znum,
            'x': x, 'y': y, 'z': z,
            'sector': getattr(room, 'sector_type', '') or '',
            'look': getattr(room, 'look', None) or getattr(room, 'sector_type', '') or '',
            'exits': exits,
            # the graphical client pre-renders neighbouring rooms from the atlas;
            # the layout generator keys props and darkness off these, so without
            # them the peeked room would differ from the one you walk into
            'description': getattr(room, 'description', '') or '',
            'flags': list(room.flags) if hasattr(room, 'flags') else [],
        })
    _ATLAS_CACHE = {
        'type': 'atlas',
        'rooms': rooms,
        'zones': list(zones.values()),
        'links': sorted(links),
    }
    return _ATLAS_CACHE




def _ally_combat(entity, viewer) -> dict:
    """What another player in the room is doing in a fight, for party readability."""
    tgt = getattr(entity, 'fighting', None)
    return {
        'in_combat': bool(tgt),
        'fighting': getattr(tgt, 'name', '') if tgt else '',
        'fighting_you': bool(tgt is viewer),
        'sex': (getattr(entity, 'sex', 'male') or 'male'),
        'stance': getattr(entity, 'stance', getattr(entity, 'combat_stance', 'normal')) or 'normal',
        'dead': getattr(entity, 'hp', 1) <= 0,
    }

def _mob_roles(entity) -> list:
    """mob_ai tactical roles (pack, caster, boss, ...) so the client can pick art by role."""
    try:
        from mob_ai import classify_mob
        return sorted(r for r in classify_mob(entity) if r != 'scripted')
    except Exception:
        return []

def _pos_fields(entity):
    """x/z in metres inside the creature's room, when combat v2 has placed it."""
    p = getattr(entity, 'web_pos', None)
    room = getattr(entity, 'room', None)
    if p and room is not None and p[0] == getattr(room, 'vnum', None):
        return {'x': round(p[1], 2), 'z': round(p[2], 2)}
    return {}


def _kw(entity):
    """A creature's keywords, when it is called by its description instead (mobs.Mobile.said_name)."""
    kw = getattr(entity, 'keyword_name', None)
    return kw if kw and kw != getattr(entity, 'name', None) else None


def _mob_uid(entity) -> int:
    """A stable id for one live mob, so clients can follow it across updates (mobs have
    no unique name: three "a rat" in one room are three ids)."""
    uid = getattr(entity, '_web_uid', None)
    if uid is None:
        uid = next(_MOB_UIDS)
        try:
            entity._web_uid = uid
        except Exception:
            pass
    return uid


def _guild_block(player):
    """{vnum, room, trainer} of the trainer who teaches the player's class (minimap star)."""
    try:
        import mastery
        g = mastery.guild_of(player.world, getattr(player, 'char_class', ''))
        return {'vnum': g[0], 'room': g[1], 'trainer': g[2]} if g else None
    except Exception:
        return None


def _keys_for(player):
    """The vnums the player carries or wears, reused for a moment (a payload asks per room)."""
    import doors as door_rules
    now = time.monotonic()
    cached = getattr(player, '_door_keys_cache', None)
    if cached and now - cached[0] < 0.2:
        return cached[1]
    keys = door_rules.carried_keys(player)
    try:
        player._door_keys_cache = (now, keys)
    except Exception:
        pass
    return keys


def _room_entities(room, vnum, player):
    """Mobs, other players, doors and floor items of one room, as the map payload
    lists them (used for every explored room and for the 3D client's nearby rooms)."""
    # Build mob list for this room
    mob_list = []
    if hasattr(room, 'characters'):
        for entity in room.characters:
            if hasattr(entity, 'account_name'):
                continue  # skip players (handled below)
            quest_mark = ''
            # quest scan is per-mob, per-room, per-push: only the CURRENT
            # room renders markers, so only compute it there (a veteran
            # character's full explored set made every step crawl)
            if hasattr(entity, 'vnum') and player.room and vnum == player.room.vnum:
                try:
                    from quests import QuestManager
                    quest_mark = QuestManager.get_quest_giver_indicator(player, entity.vnum)
                except Exception:
                    quest_mark = ''
            mob_info = {
                'id': _mob_uid(entity),
                **_pos_fields(entity),
                'name': getattr(entity, 'name', 'Unknown'),
                # what it is ("the green gelatinous blob") and its type, for the 3D body; kw its
                # keywords when it is named by its description (mobs.Mobile.said_name)
                'kw': _kw(entity),
                'short': str(getattr(entity, 'short_desc', '') or ''),
                'long': str(getattr(entity, 'long_desc', '') or '')[:80],
                'pv': getattr(entity, 'vnum', None),
                'level': getattr(entity, 'level', 1),
                'hostile': getattr(entity, 'aggressive', False) or getattr(entity, 'hostile', False),
                'boss': 'boss' in (getattr(entity, 'flags', None) or []) or getattr(entity, 'is_boss', False),
                'rank': getattr(entity, 'rank', None),
                'roles': _mob_roles(entity),
                'shopkeeper': getattr(entity, 'special', '') == 'shopkeeper',
            'trainer': getattr(entity, 'special', '') in ('trainer', 'guildmaster'),
                'quest': quest_mark,
                'flags': list(getattr(entity, 'flags', []) or []),
                'pose': _mob_pose(entity),
                'sex': (getattr(entity, 'sex', 'male') or 'male'),
                'char_class': (getattr(entity, 'char_class', '') or ''),
                # who it is fighting (the 3D client keeps your attacker targeted) and what it
                # does (innkeeper, banker...: the right-click menu offers the right things)
                'fighting': getattr(entity, 'fighting', None) is player,
                'fighting_name': getattr(getattr(entity, 'fighting', None), 'name', '') or '',
                'special': str(getattr(entity, 'special', '') or ''),
                'wards': _wards(entity),
                'ails': _ailments(entity),
            }
            # Include HP if available
            hp = getattr(entity, 'hp', None)
            max_hp = getattr(entity, 'max_hp', None)
            if hp is not None and max_hp:
                mob_info['hp'] = hp
                mob_info['maxHp'] = max_hp
            # the gear its zone gave it (a guard's sword and helm): a person in /play wears it
            npc_look = _npc_look(entity)
            if npc_look:
                mob_info['look'] = npc_look
            mob_list.append(mob_info)

    # Build other-players list for this room
    player_list = []
    if hasattr(room, 'characters'):
        for entity in room.characters:
            if hasattr(entity, 'account_name') and entity is not player:
                player_list.append({
                    'name': getattr(entity, 'name', 'Unknown'),
                    'level': getattr(entity, 'level', 1),
                    'char_class': getattr(entity, 'char_class', ''),
                    'hp': getattr(entity, 'hp', 0),
                    'maxHp': getattr(entity, 'max_hp', 1),
                    # resting, sleeping...: others see them sat down or lying (world3d/posture.js)
                    'position': getattr(entity, 'position', 'standing'),
                    # where they stand (3D clients), and whether they are in your group
                    **_pos_fields(entity),
                    'groupmate': bool(getattr(player, 'group', None)) and getattr(entity, 'group', None) is getattr(player, 'group', None),
                    'look': _look(entity),
                    # what they ride and how fast they go (others see them on their steed)
                    'mount': (_mount_info(entity) or {}).get('key') or None,
                    'speed': _speed(entity),
                    'wards': _wards(entity),
                    **_ally_combat(entity, player),
                })

    # Build door info for exits (as this player sees them: can they open the lock?),
    # leaving out doors on hidden exits they haven't found
    doors = {}
    if hasattr(room, 'exits'):
        import doors as door_rules
        keys = _keys_for(player)
        for direction, exit_data in _iter_visible_exits(room, player):
            if isinstance(exit_data, dict) and isinstance(exit_data.get('door'), dict):
                doors[direction] = door_rules.view(exit_data['door'], keys, player)

    # Items on ground
    item_list = []
    for item in (getattr(room, 'items', None) or getattr(room, 'contents', []))[:12]:
        item_list.append(item_info(item))
    return mob_list, player_list, doors, item_list


def _nearby_entities(player, radius: int = 3) -> list:
    room = getattr(player, 'room', None)
    if not room:
        return []
    zc = zone_cell(player.world, room.vnum)
    if not zc:
        return []
    zn, px, py = zc
    out = []
    for v, (cx, cy) in (_ZONECELL_INDEX.get(zn) or {}).items():
        if abs(cx - px) > radius or abs(cy - py) > radius:
            continue
        r = player.world.rooms.get(v)
        if not r:
            continue
        mobs, players, doors, items = _room_entities(r, v, player)
        entry = {'vnum': v, 'mobs': mobs, 'players': players, 'doors': doors, 'items': items}
        node = _nodes.payload(r)            # a herb patch or ore vein (nodes.py)
        if node:
            entry['node'] = node
        out.append(entry)
    return out


def build_map_payload(player, mode: str = 'full') -> dict:
    """Build map data payload for the web map UI."""
    explored = set(getattr(player, 'explored_rooms', set()))
    rooms: Dict[int, object] = {}

    if mode == 'zone' and player.room and player.room.zone:
        zone_rooms = set(player.room.zone.rooms.keys())
        for vnum in explored:
            if vnum in zone_rooms:
                room = player.world.rooms.get(vnum)
                if room:
                    rooms[vnum] = room
    else:
        for vnum in explored:
            room = player.world.rooms.get(vnum)
            if room:
                rooms[vnum] = room

    if not rooms:
        return {
            'type': 'map_data',
            'rooms': [],
            'frontier': [],
            'player': None,
        }

    start_vnum = player.room.vnum if player.room else None
    coords = compute_room_coords(rooms, start_vnum, player)
    if start_vnum not in coords:
        return {
            'type': 'map_data',
            'rooms': [],
            'frontier': [],
            'player': None,
        }

    frontier = get_frontier_coords(coords, rooms, explored, player)

    room_items = []
    zones_seen = {}
    for vnum, (x, y, z) in coords.items():
        room = rooms.get(vnum)
        exits = []
        one_way_exits = []
        
        portal_exits = []
        for direction, exit_data in _iter_visible_exits(room, player):
            if direction not in DIR_OFFSETS:
                # named passages (gate/arch/portal/...) — kept for pathfinding
                pt = _get_exit_target_vnum(exit_data)
                if pt:
                    portal_exits.append({'name': direction, 'to_room': pt})
                continue
            exits.append(direction)
            
            # Check if this is a one-way exit
            to_vnum = _get_exit_target_vnum(exit_data)
            if to_vnum:
                dest_room = rooms.get(to_vnum) or (player.world.rooms.get(to_vnum) if hasattr(player, 'world') else None)
                if dest_room:
                    reverse_dir = REVERSE_DIR.get(direction)
                    has_return = False
                    if reverse_dir:
                        for dest_dir, dest_exit in _iter_visible_exits(dest_room, player):
                            if dest_dir == reverse_dir:
                                dest_target = _get_exit_target_vnum(dest_exit)
                                if dest_target == vnum:
                                    has_return = True
                                    break
                    if not has_return:
                        one_way_exits.append(direction)
        
        zone_num = room.zone.number if room.zone else 0
        zone_name = room.zone.name if room.zone else 'Unknown'
        if zone_num not in zones_seen:
            zones_seen[zone_num] = zone_name
        
        mob_list, player_list, doors, item_list = _room_entities(room, vnum, player)

        room_items.append({
            'vnum': vnum,
            'name': room.name,
            'sector': room.sector_type,
            'look': getattr(room, 'look', None) or room.sector_type,
            'zone': zone_num,
            'zoneName': zone_name,
            'x': x,
            'y': y,
            'z': z,
            'symbol': get_room_symbol(room),
            'icon': get_room_icon(room),
            'exits': exits,
            'oneWayExits': one_way_exits,
            'portals': portal_exits,
            'flags': list(room.flags) if hasattr(room, 'flags') else [],
            'mobs': mob_list,
            'players': player_list,
            'doors': doors,
            'items': item_list,
        })

    player_coord = coords[start_vnum]

    # Frontier is now a list of dicts
    valid_frontier = [f for f in frontier if isinstance(f, dict) and 'x' in f]
    
    # Build zones list with colors
    zone_colors = [
        '#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899',
        '#f43f5e', '#ef4444', '#f97316', '#f59e0b', '#eab308',
        '#84cc16', '#22c55e', '#10b981', '#14b8a6', '#06b6d4',
        '#0ea5e9', '#3b82f6', '#6366f1', '#8b5cf6', '#a855f7',
    ]
    zones_list = []
    for i, (zone_num, zone_name) in enumerate(zones_seen.items()):
        zones_list.append({
            'id': zone_num,
            'name': zone_name,
            'color': zone_colors[i % len(zone_colors)],
        })
    
    # Game time info
    time_info = {}
    world = getattr(player, 'world', None)
    if world and hasattr(world, 'game_time'):
        gt = world.game_time
        time_info = {
            'hour': getattr(gt, 'hour', 12),
            'period': gt.get_period() if hasattr(gt, 'get_period') else 'afternoon',
            'day': getattr(gt, 'day', 1),
            'month': getattr(gt, 'month', 6),
            'year': getattr(gt, 'year', 1000),
        }

    # Weather info for current zone
    weather_info = {}
    if player.room and player.room.zone and hasattr(player.room.zone, 'weather'):
        w = player.room.zone.weather
        weather_info = {
            'sky': getattr(w, 'sky_condition', 'clear'),
            'temperature': getattr(w, 'temperature', 70),
            'wind': getattr(w, 'wind_speed', 0),
            'precipitation': getattr(w, 'precipitation', 'none'),
        }

    # Detailed info for the player's current room (the web client's MH.state.currentRoom)
    current_room = None
    if player.room:
        cur = player.room
        cur_exits = {}
        raw_exits = cur.exits if isinstance(getattr(cur, 'exits', None), dict) else {}
        # The graphical client shows EVERY real exit of the current room — closed
        # doors and hidden/secret passages included — so the player can see (and
        # use) e.g. a closed trapdoor. We iterate the raw exits (not the
        # visibility-filtered set) and flag hidden ones for a distinct UI marker.
        for direction, exit_data in raw_exits.items():
            if not exit_data:
                continue
            door = None
            if isinstance(exit_data, dict) and isinstance(exit_data.get('door'), dict):
                import doors as door_rules
                door = door_rules.view(exit_data['door'], _keys_for(player), player)
                door.setdefault('sealed', False)
                door.setdefault('barricaded', False)
            to_vnum = _get_exit_target_vnum(exit_data)
            if not to_vnum and not door:
                continue   # nothing actually leads anywhere here
            hidden = bool(isinstance(exit_data, dict) and exit_data.get('hidden'))
            # signpost data: name the zone when this exit crosses a border, and
            # flag exits that lead into a deathtrap so the UI can warn loudly
            to_zone = None
            deathtrap = False
            world = getattr(player, 'world', None)
            if to_vnum and world:
                dest = world.rooms.get(to_vnum)
                if dest:
                    if dest.zone and cur.zone and dest.zone.number != cur.zone.number:
                        to_zone = dest.zone.name
                    dflags = set(dest.flags) if hasattr(dest, 'flags') else set()
                    if 'deathtrap' in dflags or 'death' in dflags:
                        deathtrap = True
            if not deathtrap and isinstance(exit_data, dict):
                desc = str(exit_data.get('description', '') or '')
                if 'DANGER' in desc or 'deathtrap' in desc.lower():
                    deathtrap = True
            cur_exits[direction] = {
                'to_room': to_vnum,
                'door': door,
                'to_zone': to_zone,
                'hidden': hidden,
                'deathtrap': deathtrap,
            }
        try:
            from gravestones import GravestoneRegistry
            stones = GravestoneRegistry.for_room(cur.vnum)
        except Exception:
            stones = []
        # keywords the player can "look at" - first word of each extra_desc key
        details = []
        for keys in (getattr(cur, 'extra_descs', None) or {}):
            first = (keys.split() or [''])[0]
            if first:
                details.append(first.lower())
        current_room = {
            'vnum': cur.vnum,
            'name': cur.name,
            'description': getattr(cur, 'description', '') or '',
            'sector': getattr(cur, 'sector_type', '') or '',
            'look': getattr(cur, 'look', None) or getattr(cur, 'sector_type', '') or '',
            'flags': list(cur.flags) if hasattr(cur, 'flags') else [],
            'exits': cur_exits,
            'gravestones': stones,
            'details': details,
        }
        # environmental gameplay: hazards, trap state (per-viewer detection),
        # elemental terrain states (burning webs, frozen water)
        try:
            from environment import env_public
            current_room['env'] = env_public(cur, player)
        except Exception:
            pass

    payload = {
        'type': 'map_data',
        'rooms': room_items,
        'frontier': valid_frontier,
        'current_room': current_room,
        'zones': zones_list,
        'time': time_info,
        'weather': weather_info,
        # presence: who else is around (multiplayer readability)
        'presence': {
            'here': sum(1 for c in (getattr(getattr(player, 'room', None), 'characters', None) or []) if c is not player and hasattr(c, 'account_name')),
            'zone': sum(1 for p in getattr(getattr(player, 'world', None), 'players', {}).values()
                        if p is not player and getattr(getattr(p, 'room', None), 'zone', None) is getattr(getattr(player, 'room', None), 'zone', object())),
            'online': len(getattr(getattr(player, 'world', None), 'players', {}) or {}),
        },
        'player': {
            'name': player.name,
            'vnum': start_vnum,
            'sex': (getattr(player, 'sex', 'male') or 'male'),
            'x': player_coord[0],
            'y': player_coord[1],
            'z': player_coord[2],
            'hp': getattr(player, 'hp', 0),
            'max_hp': getattr(player, 'max_hp', 1),
            'mana': getattr(player, 'mana', 0),
            'max_mana': getattr(player, 'max_mana', 1),
            'move': getattr(player, 'move', 0),
            'max_move': getattr(player, 'max_move', 1),
            'level': getattr(player, 'level', 1),
            'char_class': getattr(player, 'char_class', ''),
            'race': getattr(player, 'race', ''),
            'class_skills': Config().CLASSES.get(getattr(player,'char_class','').lower(), {}).get('skills', []),
            'class_spells': Config().CLASSES.get(getattr(player,'char_class','').lower(), {}).get('spells', []),
            # what the class may wear and wield (class_gear.py): the inventory greys out the rest
            'gear_rules': _gear_rules(player),
            'title': getattr(player, 'title', ''),
            'str': getattr(player, 'str', 0),
            'int': getattr(player, 'int', 0),
            'wis': getattr(player, 'wis', 0),
            'dex': getattr(player, 'dex', 0),
            'con': getattr(player, 'con', 0),
            'cha': getattr(player, 'cha', 0),
            # what worn gear adds to those and to the maxima (the values above count it)
            'gear_stats': _gear_stats(player),
            # what it wards against ('fire 20%'...), its saves, haste
            'gear_wards': _gear_wards(player),
            # totals (equipment + stats + stance), not the base attributes
            'hitroll': player.get_hit_bonus() if hasattr(player, 'get_hit_bonus') else getattr(player, 'hitroll', 0),
            'damroll': player.get_damage_bonus() if hasattr(player, 'get_damage_bonus') else getattr(player, 'damroll', 0),
            'armor_class': player.get_armor_class() if hasattr(player, 'get_armor_class') else getattr(player, 'armor_class', 0),
            'gold': getattr(player, 'gold', 0),
            'exp': getattr(player, 'exp', 0),
            'exp_floor': _exp_thresholds(player)[0],
            'exp_to_level': _exp_thresholds(player)[1],
            'sight': _sight(player),
            'in_combat': _in_combat(player),
            'path': getattr(player, 'path', None),
            'path_active': _path_active(player),
            'equipment': {
                slot: dict(item_info(item), affects=getattr(item, 'affects', []))
                for slot, item in getattr(player, 'equipment', {}).items()
                if item is not None
            },
            'inventory': [
                dict(item_info(item), item_type=getattr(item, 'item_type', 'other'))
                for item in getattr(player, 'inventory', [])
            ],
            'aura': _worn_aura(player),
            'look': _look(player),
            'mount': _mount_info(player),
            'mounts': _owned_mounts(player),
            'speed': _speed(player),          # the 3D hero runs this much faster (Push 34)
            'position': getattr(player, 'position', 'standing'),
            'autoloot': bool(getattr(player, 'autoloot', False)),
            'autoloot_gold': bool(getattr(player, 'autoloot_gold', True)),
            'autogold': bool(getattr(player, 'autogold', True)),
            'resource': _class_resource(player),
            'charges': _charges(player),
            'cooldowns': _cooldowns(player),
            'reactions': _reaction_ready(player),
            'skills': dict(getattr(player, 'skills', {})),
            'spells': dict(getattr(player, 'spells', {})),   # learned spells (the roster is class_spells)
            'talents': dict(getattr(player, 'talents', {})),
            'practices': getattr(player, 'practices', 0),
            'bar': getattr(player, 'web_bar', None),          # the 3D client's action bar, as arranged
            'guild': _guild_block(player),                    # where the class's trainer stands
            'affects': AffectManager.save_affects(player),
            'wards': _wards(player),                          # the spells shown on the body (wards.js)
            'quest': _quest_block(player),                    # the tracker: a marquee quest, else an ordinary one
        },
        'group': build_group_block(player),
    }
    if mode == 'near':
        # the 3D client draws every room around the hero, explored or not: send their
        # occupants so monsters ahead are standing there before you walk in
        payload['nearby'] = _nearby_entities(player)
    return payload
