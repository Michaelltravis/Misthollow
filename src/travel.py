"""
Misthollow Travel & Waypoints
===========================
Fast travel waypoint system.
"""

import time
from typing import Dict, Optional, Tuple

from config import Config


WAYPOINTS: Dict[str, dict] = {
    # Major cities / hubs
    'midgaard_temple': {
        'name': 'Temple of Garathorm',
        'vnum': 3001,
        'cost': 10,
    },
    'midgaard_square': {
        'name': 'Temple Square',
        'vnum': 3002,
        'cost': 10,
    },
    'midgaard_inn': {
        'name': 'The Prancing Pony Inn',
        'vnum': 3030,
        'cost': 15,
    },
    'haon_dor_entrance': {
        'name': 'Haon Dor Forest Entrance',
        'vnum': 4001,
        'cost': 20,
    },
    'greystone_castle': {
        'name': 'Greystone Castle Gates',
        'vnum': 5001,
        'cost': 25,
    },
    'goblin_warrens': {
        'name': 'Goblin Warrens Entrance',
        'vnum': 6001,
        'cost': 25,
    },
    'forgotten_crypt': {
        'name': 'Forgotten Crypt Entrance',
        'vnum': 7001,
        'cost': 35,
    },
    'haunted_swamp': {
        'name': 'Haunted Swamp Entrance',
        'vnum': 9001,
        'cost': 35,
    },
    'dwarven_mines': {
        'name': 'Dwarven Mines Entrance',
        'vnum': 10000,
        'cost': 45,
    },
    'elven_village': {
        'name': 'Silversong Village Green',
        'vnum': 11001,
        'cost': 45,
    },
    'sunken_ruins_docks': {
        'name': "Docks of Garathorm",
        'vnum': 13000,
        'cost': 55,
    },
    'necropolis_gates': {
        'name': 'Gates of the Dead',
        'vnum': 14000,
        'cost': 60,
    },
    'kings_road': {
        'name': "The King's Road",
        'vnum': 15000,
        'cost': 50,
    },
    'plane_chaos_portal': {
        'name': 'Hidden Portal (Plane of Chaos)',
        'vnum': 16000,
        'cost': 80,
    },
}


def get_waypoint_by_name(name: str) -> Optional[Tuple[str, dict]]:
    """Find a waypoint by key or partial name."""
    if not name:
        return None

    name = name.lower().strip()

    # Exact key match
    if name in WAYPOINTS:
        return name, WAYPOINTS[name]

    # Partial key or name match
    for key, info in WAYPOINTS.items():
        if name in key.lower() or name in info.get('name', '').lower():
            return key, info

    return None


def discover_waypoint(player, room_vnum: int) -> Optional[Tuple[str, dict]]:
    """Discover a waypoint if the room matches."""
    for key, info in WAYPOINTS.items():
        if info.get('vnum') == room_vnum:
            if not hasattr(player, 'discovered_waypoints'):
                player.discovered_waypoints = set()
            if key not in player.discovered_waypoints:
                player.discovered_waypoints.add(key)
                return key, info
            return None
    return None


def can_travel(player) -> Tuple[bool, str]:
    """Check travel cooldown and room restrictions."""
    now = time.time()
    cooldown_until = getattr(player, 'travel_cooldown_until', 0)
    if cooldown_until and now < cooldown_until:
        remaining = int(cooldown_until - now)
        return False, f"You must wait {remaining}s before traveling again."

    if player.is_fighting:
        return False, "You cannot travel while fighting!"

    if player.room and 'no_recall' in player.room.flags:
        return False, "Powerful magic prevents you from traveling from here!"

    import lairs
    held = lairs.holds(player)
    if held:
        return False, held

    return True, ""


def set_travel_cooldown(player):
    """Set travel cooldown."""
    cooldown = getattr(Config, 'TRAVEL_COOLDOWN_SECONDS', 60)
    player.travel_cooldown_until = time.time() + cooldown
