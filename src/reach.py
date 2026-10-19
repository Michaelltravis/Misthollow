"""Reaching into the next room (the 3D client, /play).

A MUD fights room by room, but /play draws the rooms of a zone as one place: a creature a few
metres past the room's edge is plainly in bow shot. So, for players with a position (the 3D
client; telnet players have none, and keep the old rules):

  - a shot, a bolt or an aimed spell (combat_range shapes 'ranged' and 'blast') can strike a
    creature in a room next door, measured in metres across the edge, when the two rooms are
    joined by an open way (side by side on the zone map, no closed door). The creature is
    *pulled*: struck, it charges into the hero's room, stepping in at the nearest point, and the
    fight goes on there as any other (the client sends `webpull #id <ability>` first, then the
    ordinary command);
  - an aimed area spell (a circle on the ground) also catches creatures just across the edge
    inside its circle, and pulls them in (Spells.foes_in_room).

Never through a closed door, into or out of a peaceful room, across a zone's border, into a room
the hero may not enter; never a shopkeeper, trainer or other servant, anyone's pet, a quest's
figure, or a creature that does not leave its post (sentinels and bosses: struck from safety,
they could not answer). Melee, touch and cone abilities and charges still need the hero in the
creature's room (the client walks there).
"""
import math
import time

import combat_range as cr

SERVICE = ('guildmaster', 'trainer', 'shopkeeper', 'healer', 'banker', 'postmaster', 'innkeeper')
PULL_SHAPES = ('ranged', 'blast')
MARGIN = 0.6            # metres of slack on a range measured across an edge
_ROOM_EXITS = {}        # zone -> {vnum: {dir: zonemap exit}}


def _zone_exits(world, zone_num):
    idx = _ROOM_EXITS.get(zone_num)
    if idx is None:
        import map_system
        zm = map_system.build_zonemap(world, zone_num) or {'rooms': []}
        idx = _ROOM_EXITS[zone_num] = {r['vnum']: r.get('exits') or {} for r in zm['rooms']}
    return idx


def world_pos(world, ch):
    """(zone, x, z) of a character on its zone's map, in metres; None when unknown."""
    room = getattr(ch, 'room', None)
    if room is None:
        return None
    import map_system
    c = map_system.zone_cell(world, room.vnum)
    if c is None:
        return None
    p = cr.pos_of(ch) or (cr.ROOM_W / 2, cr.ROOM_H / 2)
    return (c[0], c[1] * cr.ROOM_W + p[0], c[2] * cr.ROOM_H + p[1])


def distance(world, a, b):
    pa, pb = world_pos(world, a), world_pos(world, b)
    if pa is None or pb is None or pa[0] != pb[0]:
        return None
    return math.hypot(pa[1] - pb[1], pa[2] - pb[2])


def joined(world, room, other):
    """The direction from `room` to `other` along an open way (the two side by side on the
    zone map, an open door or none), else None."""
    zone = getattr(getattr(room, 'zone', None), 'number', None)
    if zone is None or getattr(getattr(other, 'zone', None), 'number', None) != zone:
        return None
    for d, e in (_zone_exits(world, zone).get(room.vnum) or {}).items():
        if e.get('to') != other.vnum or e.get('kind') != 'open':
            continue
        door = ((room.exits or {}).get(d) or {}).get('door')
        if isinstance(door, dict) and door.get('state') == 'closed':
            continue
        return d
    return None


def neighbours(world, room):
    """[(direction, room)] of the rooms joined to `room` by an open way."""
    out = []
    zone = getattr(getattr(room, 'zone', None), 'number', None)
    if zone is None:
        return out
    for d, e in (_zone_exits(world, zone).get(room.vnum) or {}).items():
        other = world.rooms.get(e.get('to'))
        if other is not None and joined(world, room, other) == d:
            out.append((d, other))
    return out


def why_not(world, player, mob):
    """Why `player` may not reach `mob` in the next room (a short reason), else None."""
    if not hasattr(player, 'connection'):
        return 'not a player'                        # a creature's spell pulls no one
    if cr.pos_of(player) is None:
        return 'no position'                         # telnet: the old rules
    here, there = getattr(player, 'room', None), getattr(mob, 'room', None)
    if here is None or there is None or here is there:
        return 'not next door'
    if hasattr(mob, 'connection') or getattr(mob, 'hp', 0) <= 0:
        return 'not a creature'
    if joined(world, here, there) is None:
        return 'no open way'
    if 'peaceful' in (here.flags or ()) or 'peaceful' in (there.flags or ()):
        return 'a place of peace'
    try:
        if not there.admits(player):
            return 'a place you may not go'
    except Exception:
        pass
    flags = set(getattr(mob, 'flags', ()) or ())
    if getattr(mob, 'special', None) in SERVICE or getattr(mob, 'owner', None) is not None:
        return 'not a foe'
    if (getattr(mob, 'marquee_tag', None) or {}).get('kind') == 'npc':
        return 'not a foe'
    try:
        import marquee
        if not marquee.can_touch(player, mob):
            return 'not yours to fight'
    except Exception:
        pass
    boss = 'boss' in flags or getattr(mob, 'is_boss', False)
    if 'sentinel' in flags or boss:
        return 'it will not leave its post'
    return None


def action_range(player, ability):
    """(metres, pulls?) of what the hero is about to do: an ability by name, else the
    ordinary blow. Only what is aimed at a foe pulls (a heal, a blessing, a rescue, anything on
    oneself never does), as the hero's own class book says it (an assassin's weapon poison is
    not the necromancer's spell of the same name)."""
    if not ability or ability in ('attack', 'kill'):
        rng, ranged = cr.auto_range(player)
        return rng, bool(ranged)
    k = cr.key(ability)
    try:
        import mastery
        entry = next((e for e in mastery.book(getattr(player, 'char_class', '')) if e.get('id') == k), None)
    except Exception:
        entry = None
    try:
        from spells import SPELLS
    except Exception:
        SPELLS = {}
    is_spell = entry.get('type') == 'spell' if entry else k in SPELLS
    target = entry.get('target') if entry else None
    if target is None and is_spell and k in SPELLS:
        target = 'enemy' if SPELLS[k].get('target') == 'offensive' else SPELLS[k].get('target')
    rng, shape = cr.ability_range(k, is_spell)
    foe = target in (None, 'enemy')
    return rng, foe and str(shape).split(':')[0] in PULL_SHAPES


def _clamp_into(world, room, wpos):
    """A zone-map point (zone, x, z), brought inside `room` (1 m in from its walls)."""
    import map_system
    c = map_system.zone_cell(world, room.vnum)
    x = wpos[1] - c[1] * cr.ROOM_W
    z = wpos[2] - c[2] * cr.ROOM_H
    return (max(1.0, min(cr.ROOM_W - 1.0, x)), max(1.0, min(cr.ROOM_H - 1.0, z)))


def pulled(mob, within=60.0):
    """Whether this creature was pulled from afar lately (it calls no friends to the fight)."""
    import time as _time
    return _time.time() - (getattr(mob, 'pulled_at', 0) or 0) < within


NOTICE = 16.0           # metres across an open way an aggressive creature notices a hero from
FLEE_GRACE = 30.0       # seconds a creature leaves alone a hero who fled or escaped from it


def lost(mob, player, seconds=FLEE_GRACE):
    """`player` got away from `mob` (fled, escaped): it does not come after them again at once."""
    import time as _time
    seen = getattr(mob, 'lost_quarry', None)
    if seen is None:
        seen = mob.lost_quarry = {}
    if 'tracks_covered' in (getattr(player, 'affect_flags', None) or ()):
        seconds *= 2                                 # (cover tracks: nothing to follow)
    seen[getattr(player, 'name', '')] = _time.time() + seconds


def _now():
    import time as _time
    return _time.time()


def noticed(world, mob, spared=lambda ch: False):
    """The hero next door an aggressive creature notices (docs/OPEN_WORLD.md, phase 4: creatures
    see across the open land, not only into their own room): the nearest player with a position
    in a room joined to its own by an open way, within NOTICE metres, not hiding, not spared;
    never from or into a peaceful room or a room creatures keep out of. Else None."""
    here = getattr(mob, 'room', None)
    if here is None or getattr(mob, 'fighting', None) or hasattr(mob, 'connection'):
        return None
    flags = set(getattr(mob, 'flags', ()) or ())
    if flags & {'sentinel', 'boss'} or getattr(mob, 'special', None) in SERVICE or getattr(mob, 'owner', None) is not None:
        return None
    if getattr(mob, 'position', '') == 'sleeping' or 'blind' in (getattr(mob, 'affect_flags', None) or ()):
        return None
    if 'peaceful' in (here.flags or ()):
        return None
    try:
        from mobs import KEEP_OUT
    except Exception:
        KEEP_OUT = {'no_mob'}
    best, best_d = None, NOTICE
    for _d, room in neighbours(world, here):
        if 'peaceful' in (room.flags or ()) or (KEEP_OUT & set(room.flags or ())):
            continue
        for ch in room.characters:
            if not hasattr(ch, 'connection') or cr.pos_of(ch) is None or spared(ch):
                continue
            if {'hidden', 'sneaking'} & set(getattr(ch, 'flags', ()) or ()):
                continue
            if (getattr(mob, 'lost_quarry', None) or {}).get(getattr(ch, 'name', ''), 0) > _now():
                continue                             # they just got away from it
            if getattr(room, 'sector_type', '') == 'city' and getattr(mob, 'level', 0) - getattr(ch, 'level', 0) > 5:
                continue
            dist = distance(world, mob, ch)
            if dist is not None and 'tracks_covered' in (getattr(ch, 'affect_flags', None) or ()):
                dist *= 2                            # (cover tracks: noticed from half as far)
            if dist is not None and dist <= best_d:
                best, best_d = ch, dist
    return best


def bring(world, mob, to_room, struck=False):
    """Move a creature into the room next door (joined by an open way), stepping in at the point
    nearest where it stood; the rooms are told, the 3D clients shown it running in. `struck`: it
    was hit from afar (a pull: it calls no friends). True when it came."""
    there = mob.room
    d = joined(world, to_room, there)
    if d is None:
        return False
    wpos = world_pos(world, mob)
    import map_system
    back = map_system.REVERSE_DIR.get(d, d)
    if struck:
        import time as _time
        mob.pulled_at = _time.time()  # struck from afar: its friends saw nothing (no call for help)
    if mob in there.characters:
        there.characters.remove(mob)
    mob.room = to_room
    to_room.characters.append(mob)
    if wpos is not None:
        x, z = _clamp_into(world, to_room, wpos)
        cr.set_pos(mob, x, z)

    async def tell():
        try:
            await there.send_to_room(f"{mob.name} {'is struck from afar and charges' if struck else 'charges'} off {back}!")
            await to_room.send_to_room(f"{mob.name} charges in from the {d}!")
            await mob._notify_move(there, to_room, back, d)
        except Exception:
            pass
    try:
        import asyncio
        asyncio.get_running_loop().create_task(tell())
    except RuntimeError:
        pass                                        # no loop (a test): the move stands
    return True


def pull(world, player, mob):
    """Bring a creature struck from the next room into the hero's room, where it steps in at
    the point nearest where it stood (a point inside the room is never further from anything
    in it than the creature was). The move is made at once (the blow that follows finds it
    here); the rooms are told, and the 3D clients shown, a moment later. True when it came."""
    return bring(world, mob, player.room, struck=True)


async def webpull(player, args):
    """`webpull #id [ability]`: before an attack or an aimed ability at a creature in the next
    room, bring it in if the hero can reach it from where they stand. Says why not, else
    nothing (the ordinary command follows and strikes it in the hero's room)."""
    world = getattr(player, 'world', None)
    if world is None or not args or not args[0].startswith('#') or not args[0][1:].isdigit():
        return
    uid = int(args[0][1:])
    if any(getattr(ch, '_web_uid', None) == uid for ch in (player.room.characters if player.room else ())):
        return                                      # already here: nothing to do
    mob = None
    for _d, room in neighbours(world, player.room):
        mob = next((ch for ch in room.characters if getattr(ch, '_web_uid', None) == uid), None)
        if mob is not None:
            break
    if mob is None:
        return
    c = player.config.COLORS
    reason = why_not(world, player, mob)
    if reason:
        player._pull_refused = time.monotonic()
        await player.send(f"{c['yellow']}You can't reach {mob.name} from here ({reason}).{c['reset']}")
        return
    # where the hero's screen shows it ("@x,z", its room's metres): a creature the server has
    # no place for (it has not fought yet) is measured from there, not from its room's middle
    rest = list(args[1:])
    if rest and rest[-1].startswith('@'):
        try:
            x, z = (float(v) for v in rest.pop()[1:].split(','))
            if cr.pos_of(mob) is None:
                cr.set_pos(mob, x, z)
        except ValueError:
            pass
    rng, pulls = action_range(player, ' '.join(rest).strip().strip("'\""))
    if not pulls:
        return                                      # melee or touch: the hero walks in
    dist = distance(world, player, mob)
    if dist is None or dist > rng + MARGIN:
        player._pull_refused = time.monotonic()
        await player.send(f"{c['yellow']}{mob.name} is out of reach ({dist or 0:.0f} m; it reaches {rng:g} m).{c['reset']}")
        return
    pull(world, player, mob)


def pull_area(player, centre, radius):
    """An aimed area (centre x, z in the hero's room, radius) that crosses an open edge: the
    creatures inside it next door are pulled in (Spells.foes_in_room then counts them)."""
    world = getattr(player, 'world', None)
    here = getattr(player, 'room', None)
    if world is None or here is None or not hasattr(player, 'connection') or cr.pos_of(player) is None:
        return []
    import map_system
    c = map_system.zone_cell(world, here.vnum)
    if c is None:
        return []
    cx, cz = c[1] * cr.ROOM_W + centre[0], c[2] * cr.ROOM_H + centre[1]
    came = []
    for _d, room in neighbours(world, here):
        for mob in list(room.characters):
            if why_not(world, player, mob):
                continue
            w = world_pos(world, mob)
            if w is not None and math.hypot(w[1] - cx, w[2] - cz) <= radius and pull(world, player, mob):
                came.append(mob)
    return came
