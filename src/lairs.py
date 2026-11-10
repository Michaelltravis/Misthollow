"""Lairs: a boss who is not waiting in his room but comes when someone walks in, and shuts them in
with him (the owner, of Ostragoth: "he flys in as a bat then transforms ... The door should
automatically shut and lock. The only way out is to be summoned, defeat the boss, or recall").

A zone's population file lists them beside its bosses (world/population/zone_<n>.json):

    "lairs": [{"vnum": 647006, "room": 8403, "herald": 647009, "mechanics": [...],
               "seal": "...", "arrive": "...", "transform": "...", "freed": "...", "retreat": "..."}]

The boss is not in the world until someone walks into the lair (on_enter, from a step through a
door). Then every door of the room slams shut and locks (pickproof, and magically_blocked, so no
key, pick, bash or spell opens it), the herald (a great black bat) flies in, and a moment later it
becomes the boss, who falls on whoever came in. While the lair is sealed no one inside walks,
flees, portals, travels, shadow-steps or teleports out (holds()): recall (even mid-fight), being
summoned, and dying still take them out. The boss's death opens the doors, and he does not come
again until his zone resets. If the lair empties of the living first, he goes as he came, healed,
and the doors open: the next to walk in meets him whole.
"""
import asyncio
import logging
import time

logger = logging.getLogger('Misthollow')

LAIRS = {}          # lair room vnum -> Lair
ARRIVE_DELAY = 1.5  # the door slams; then the herald comes...
TURN_DELAY = 2.5    # ...and then it becomes the boss
WATCH = 1.0         # how often a sealed lair looks to see whether it is over


class Lair:
    def __init__(self, spec, zone=None):
        self.spec = spec
        self.vnum = int(spec['vnum'])
        self.room_vnum = int(spec['room'])
        self.zone = zone
        self.sealed = False
        self.boss = None
        self.slain_at = 0.0
        self.task = None

    def waiting(self, room):
        """Whether the boss would come for someone walking in now: not sealed already, and not
        slain since his zone last reset."""
        if self.sealed:
            return False
        if self.slain_at:
            zone = getattr(room, 'zone', None)
            if (getattr(zone, 'last_reset_at', 0) or 0) <= self.slain_at:
                return False
            self.slain_at = 0.0
        return True

    def say(self, key, default=''):
        return self.spec.get(key) or default


def register(world, spec, zone_number=None):
    """Remember a lair (population.apply); returns a problem, or None."""
    room = world.rooms.get(int(spec.get('room', 0) or 0))
    if room is None or int(spec.get('vnum', 0) or 0) not in world.mob_prototypes:
        return f"lair {spec.get('vnum')} or room {spec.get('room')} missing"
    if spec.get('herald') and int(spec['herald']) not in world.mob_prototypes:
        return f"lair {spec['vnum']}: no herald {spec['herald']}"
    LAIRS[room.vnum] = Lair(spec, zone_number)
    return None


def lair_of(room):
    return LAIRS.get(getattr(room, 'vnum', None))


def holds(ch):
    """What keeps ch in a sealed lair (a line to tell them), or None if they may go. Immortals
    are never held."""
    lair = lair_of(getattr(ch, 'room', None))
    if lair is None or not lair.sealed or getattr(ch, 'is_immortal', False):
        return None
    return lair.say('held', "The sealed chamber holds you: only death, a recall or a summons takes you from here.")


def closed_to(room):
    """Why no one may be brought into a sealed lair (a summons in, a teleport landing), or None."""
    lair = lair_of(room)
    if lair is None or not lair.sealed:
        return None
    return lair.say('barred', "The chamber is sealed: nothing living may be brought into it now.")


def _living(room):
    """The players still standing in the room (an immortal looking on counts: asking reads an
    account from disk, too dear once a second)."""
    return [c for c in list(getattr(room, 'characters', None) or [])
            if hasattr(c, 'connection') and getattr(c, 'hp', 0) > 0]


async def on_enter(player, room):
    """A player has walked into `room`: if it is a lair whose boss is waiting, he comes."""
    lair = lair_of(room)
    if lair is None or not hasattr(player, 'connection') or getattr(player, 'is_immortal', False):
        return
    if not lair.waiting(room):
        return
    lair.sealed = True
    lair.task = asyncio.ensure_future(_run(lair, room, player))


async def _run(lair, room, player):
    try:
        await _seal(lair, room)
        await asyncio.sleep(ARRIVE_DELAY)
        if not _living(room):
            await _open(lair, room)
            return
        herald = _bring(room, int(lair.spec['herald'])) if lair.spec.get('herald') else None
        if herald is not None:
            await room.send_to_room(lair.say('arrive', f"{herald.name} bursts into the room!"))
            await _show(room, herald, 'arrive')
        await asyncio.sleep(TURN_DELAY)
        if herald is not None:
            _remove(herald)
        boss = _bring(room, lair.vnum)
        lair.boss = boss
        if boss is None:
            await _open(lair, room)
            return
        await room.send_to_room(lair.say('transform', f"{boss.name} is here!"))
        await _show(room, boss, 'arrive')
        live = _living(room)
        if not live:
            await _retreat(lair, room)
            return
        target = player if player in live else live[0]
        from combat import CombatHandler
        await CombatHandler.start_combat(boss, target)
        await _watch(lair, room)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(f'lair {lair.room_vnum}')
        try:
            await _open(lair, room)
        except Exception:
            lair.sealed = False


async def _watch(lair, room):
    """Until the boss falls or the lair is empty of the living."""
    while True:
        await asyncio.sleep(WATCH)
        boss = lair.boss
        if boss is None or getattr(boss, 'hp', 0) <= 0 or boss not in (room.characters or []):
            lair.slain_at = time.time()
            lair.boss = None
            await room.send_to_room(lair.say('freed', "The bolts draw back of themselves, and the way out stands open."))
            await _open(lair, room)
            return
        if not _living(room):
            await _retreat(lair, room)
            return


async def _retreat(lair, room):
    """No one living is left: the boss leaves as he came, whole again, and his servants with him."""
    boss, lair.boss = lair.boss, None
    if boss is not None:
        for m in [m for m in list(room.characters) if getattr(m, 'summoned_by', None) is boss]:
            _remove(m)
        await room.send_to_room(lair.say('retreat', f"{boss.name} is gone."))
        _remove(boss)
    await _open(lair, room)


async def _seal(lair, room):
    import doors
    for d, ex, door in doors.doors_in(room):
        if doors.is_seal(door):
            continue
        doors.apply(room, d, state='closed', locked=True, magically_blocked=True, pickproof=True,
                    mirror=('pickproof',))
        far, od, _ = doors.other_side(room, d)
        if far is not None:
            await far.send_to_room(lair.say('heard', f"The {doors.label(door)} {od} slams shut, and a bolt shoots home."))
    await room.send_to_room(lair.say('seal', "Behind you the door slams shut, and a bolt shoots home!"))


async def _open(lair, room):
    """Every door back as the zone starts it (open, here), unbolted."""
    import doors
    init = getattr(getattr(room, 'world', None), 'door_init', None) or getattr(doors.WORLD, 'door_init', None) or {}
    for d, ex, door in doors.doors_in(room):
        if doors.is_seal(door):
            continue
        want = init.get((room.vnum, d)) or {'state': 'open', 'locked': False}
        doors.apply(room, d, state=want['state'], locked=want['locked'], magically_blocked=None, pickproof=None,
                    mirror=('pickproof',))
    lair.sealed = False


def _world(room):
    import doors
    return getattr(room, 'world', None) or doors.WORLD


def _bring(room, vnum):
    """A creature of `vnum` made and set down in `room` (the lair's own, not a zone reset's)."""
    world = _world(room)
    proto = (getattr(world, 'mob_prototypes', None) or {}).get(vnum)
    if not proto:
        return None
    from bosses import create_mob_from_prototype
    mob = create_mob_from_prototype(proto, world)
    mob.room = mob.home_room = room
    mob.home_zone = getattr(getattr(room, 'zone', None), 'number', None)
    room.characters.append(mob)
    world.npcs.append(mob)
    return mob


def _remove(mob):
    room = getattr(mob, 'room', None)
    if room is not None and mob in room.characters:
        room.characters.remove(mob)
    world = getattr(mob, 'world', None)
    if world is not None and mob in getattr(world, 'npcs', []):
        world.npcs.remove(mob)
    for c in list(getattr(room, 'characters', None) or []):
        if getattr(c, 'fighting', None) is mob:
            c.fighting = None
            if getattr(c, 'position', None) == 'fighting':
                c.position = 'standing'
    mob.fighting = None
    mob.room = None


async def _show(room, mob, action):
    """The graphical clients see it come (a flight in through the window: 'up')."""
    wm = getattr(_world(room), 'web_map', None)
    if wm is None:
        return
    try:
        await wm.notify_room(room, {'type': 'mob_move', 'action': action, 'name': mob.name, 'dir': 'up',
                                    'vnum': room.vnum})
    except Exception:
        pass
    for p in list(room.characters):
        if hasattr(p, 'sync_room'):
            try:
                await p.sync_room()
            except Exception:
                pass
