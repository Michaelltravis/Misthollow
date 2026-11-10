"""One-time gifts to named characters (world/grants.json), given on their next login.

    {"xtc": {"mounts": ["griffin", "horse"], "ride": "griffin", "explore_all": true,
             "waypoints_all": true, "room": 14804, "gearup": true, "gold": 0, "why": "..."},
     "deckard": {"immortal": "deckard"}}

Each part of a gift is given once: the save records it in `grants_received` (by its own key,
"<name>:<part>:<value>"), so editing a character's entry gives only the parts added or changed
(adding a mount never puts them back on the one they rode). Mounts already owned aren't given
twice; unknown mounts are skipped.

`immortal` names an account: it is made an admin one only when the character is on that account
(a character name anyone could take never gives admin). Every character has an account
(accounts.py); none is made here.
"""
import json
import logging
import os

logger = logging.getLogger('Misthollow')
GRANTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'world', 'grants.json')
PARTS = ('mounts', 'ride', 'explore_all', 'waypoints_all', 'room', 'gearup', 'immortal', 'gold')


RUNTIME = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'grants.json')


def _read(path) -> dict:
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, ValueError):
        return {}
    return {k.lower(): v for k, v in data.items() if not k.startswith('_') and isinstance(v, dict)}


def load_grants(path=GRANTS) -> dict:
    """The gifts: world/grants.json, and (with it) the ones the server itself gave out at
    start (lib/grants.json: accounts.apply_moves). A part both give is the server's, the later
    gift (a new `gearup` value gives the kit again, at today's level cap)."""
    gifts = _read(path)
    if path == GRANTS:
        for name, gift in _read(RUNTIME).items():
            gifts[name] = {**gifts.get(name, {}), **gift}
    return gifts


def add_runtime_gifts(gifts: dict, path=None):
    """Add gifts the server gives out itself (lib/grants.json, never in git), by character name."""
    path = path or RUNTIME
    have = _read(path)
    for name, gift in gifts.items():
        have[name.lower()] = {**have.get(name.lower(), {}), **gift}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(have, f, indent=2)


def grant_key(name, gift) -> str:
    """The whole gift's key (how gifts were recorded before they were given part by part)."""
    body = {k: v for k, v in gift.items() if k != 'why'}
    return f"{name.lower()}:{json.dumps(body, sort_keys=True)}"


def part_key(name, part, value) -> str:
    return f"{name.lower()}:{part}:{json.dumps(value, sort_keys=True)}"


def apply_grants(player, grants=None, entering=False) -> list:
    """Give this player the parts of their gift they haven't had; returns lines to tell them.
    `entering`: they are entering the world now (World.add_player), past the login; an immortal
    part waits for that (the account they logged in with is settled by then)."""
    gift = (grants if grants is not None else load_grants()).get(str(getattr(player, 'name', '')).lower())
    if not gift:
        return []
    got = getattr(player, 'grants_received', None)
    if got is None:
        player.grants_received = got = []
    whole = grant_key(player.name, gift)
    todo = [p for p in PARTS if gift.get(p) and part_key(player.name, p, gift[p]) not in got
            and (entering or p != 'immortal')]
    if whole in got:
        # given whole before parts were counted: every part of it is had
        got.extend(part_key(player.name, p, gift[p]) for p in todo)
        return []
    if not todo:
        return []
    from mounts import MountManager, MOUNT_TEMPLATES
    lines = []
    world = getattr(player, 'world', None)
    for part in todo:
        value = gift[part]
        if part == 'mounts':
            for m in value:
                if m not in MOUNT_TEMPLATES:
                    logger.warning(f"grants: {player.name}: no mount {m!r}")
                    continue
                if not MountManager.get_owned_mount_data(player, m):
                    player.owned_mounts.append({'key': m, 'loyalty': 100})
                    lines.append(f"You are given {MOUNT_TEMPLATES[m]['name']} ({m}).")
        elif part == 'ride':
            if value in MOUNT_TEMPLATES and MountManager.get_owned_mount_data(player, value):
                player.mount = MountManager.create_mount(value)
                player.last_mount = value
                lines.append(f"You are riding {player.mount.name}. (R or dismount to get down; ride n n 3e to speedwalk)")
        elif part == 'explore_all':
            if world is None:
                continue
            # every room on the map, but the God Rooms and lands sealed until built
            rooms = [r.vnum for r in world.rooms.values()
                     if 'imm_only' not in (r.flags or ()) and not getattr(getattr(r, 'zone', None), 'sealed', False)]
            before = len(player.explored_rooms)
            player.explored_rooms.update(rooms)
            lines.append(f"Your map is unveiled: {len(player.explored_rooms) - before:,} more rooms charted.")
        elif part == 'waypoints_all':
            from travel import WAYPOINTS
            before = len(player.discovered_waypoints)
            player.discovered_waypoints.update(WAYPOINTS.keys())
            lines.append(f"Every travel waypoint is known to you ({len(player.discovered_waypoints) - before} new).")
        elif part == 'room':
            if world is None:
                continue
            # put them somewhere (an owner testing a place): where they wake on this login
            v = int(value)
            if v in world.rooms:
                player.room_vnum = v
                lines.append(f"You find yourself at {world.rooms[v].name}.")
            else:
                logger.warning(f"grants: {player.name}: no room {v}")
        elif part == 'gearup':
            # the endgame kit (CommandHandler.gear_up): given once they are in the world (it levels
            # them through the game's own level-up, which talks to them)
            player._grant_gearup = True
        elif part == 'immortal':
            # the account the gift names is made an admin one (Player.is_immortal: every wizard
            # command, on every character of it), and only when this character is on it
            from accounts import Account
            want = value.lower() if isinstance(value, str) else ''
            if not want:
                logger.warning(f"grants: {player.name}: immortal must name the account (\"immortal\": \"<account>\")")
                continue
            if (getattr(player, 'account_name', None) or '').lower() != want:
                logger.warning(f"grants: {player.name}: not on the account {want!r}; no immortal")
                continue
            acct = Account.load(want)
            if acct is None:
                logger.warning(f"grants: {player.name}: no account {want!r}")
                continue
            if not acct.is_admin:
                acct.is_admin = True
                acct.save()
            lines.append("The gods raise you among them: you are immortal. (wizhelp lists your powers)")
        elif part == 'gold':
            player.gold = (getattr(player, 'gold', 0) or 0) + int(value)
            lines.append(f"You are given {int(value):,} gold.")
        got.append(part_key(player.name, part, value))
    logger.info(f"grants: gave {player.name} {todo}")
    return lines
