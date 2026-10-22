"""Structured combat events for the graphical (3D) client.

Every swing, hit, miss, defence, cast, heal, death and wind-up is also emitted as a small
JSON event from the same code that prints its combat-log line, so the client can animate
exactly what the log says. Events emitted during one moment are batched per room and sent
on the map socket as {"type": "combat_events", "room": vnum, "events": [...]} to the web
clients of everyone standing in that room. Telnet players are unaffected.

Event shape (all fields optional except k):
  k       attack | ability | spell | heal | buff | debuff | windup | resolve | death | stun | oor
  src/dst {"p": player name} or {"m": mob uid}
  res     hit | crit | miss | dodge | parry | block | resist | immune
  amt     damage or healing amount
  ability / spell, school (fire, frost, lightning, arcane, holy, shadow, necrotic, nature,
  poison, sound, physical, blood), ranged (bool), area {shape, r, angle, x, z}, ms (wind-up)
  fx      a creature's ability, in lower_snake (fire_breath): the look the 3D client draws its
          wind-up, release and interruption with (world3d/mobfx-hand.js)
"""
import asyncio
import contextvars
import logging

logger = logging.getLogger('Misthollow')

_pending = {}        # room vnum -> (room, [events]) ready to send
_scheduled = False


class _Action:
    """One action's events (a round, a swing, a skill), held until it finishes."""
    __slots__ = ('rooms', 'depth', 'closed')

    def __init__(self):
        self.rooms = {}
        self.depth = 0
        self.closed = False


# the action this task is in (each asyncio task has its own; a task started inside an action
# shares it until the action ends, then goes on alone)
_action = contextvars.ContextVar('misthollow_combat_action', default=None)


def _open():
    a = _action.get()
    return a if a is not None and not a.closed else None


class hold:
    """`with hold():` keeps this action's events together until it finishes, so a swing and
    its wounds leave in one message even though the round awaits in between. Each action holds
    only its own events: another one, in this room or elsewhere, is never kept waiting."""
    def __enter__(self):
        a = _open()
        self._token = None
        if a is None:
            a = _Action()
            self._token = _action.set(a)
        a.depth += 1
        self._a = a
        return self

    def __exit__(self, *exc):
        a = self._a
        a.depth -= 1
        if a.depth <= 0 and not a.closed:
            a.closed = True
            for vnum, (room, events) in a.rooms.items():
                entry = _pending.get(vnum)
                if entry is None:
                    _pending[vnum] = (room, list(events))
                else:
                    entry[1].extend(events)
            a.rooms.clear()
            if self._token is not None:
                try:
                    _action.reset(self._token)
                except ValueError:
                    _action.set(None)
            _schedule()
        return False


def _target():
    a = _open()
    return a.rooms if a is not None else _pending


def ref(ch):
    """How a combatant is named in an event."""
    if ch is None:
        return None
    if hasattr(ch, 'account_name') or getattr(ch, 'is_player', False):
        return {'p': getattr(ch, 'name', '?')}
    try:
        from map_system import _mob_uid
        return {'m': _mob_uid(ch)}
    except Exception:
        return {'m': id(ch) & 0x7fffffff}


def mark(room):
    """Where the next event for `room` will go: lets a wrapper put an action ahead of the
    wounds it caused (the swing before its damage numbers). Take it inside the action's hold."""
    entry = _target().get(getattr(room, 'vnum', None))
    return len(entry[1]) if entry else 0


def emit_at(room, index, k, src=None, dst=None, **fields):
    """emit(), but inserted at `index` (from mark(), in the same hold) instead of appended."""
    emit(room, k, src, dst, **fields)
    entry = _target().get(getattr(room, 'vnum', None))
    if entry and index is not None and index < len(entry[1]) - 1:
        entry[1].insert(index, entry[1].pop())


def _event(k, src, dst, fields):
    ev = {'k': k}
    if src is not None:
        ev['src'] = ref(src)
    if dst is not None:
        ev['dst'] = ref(dst)
    for key, value in fields.items():
        if value is not None:
            ev[key] = value
    return ev


def emit_private(ch, k, src=None, dst=None, **fields):
    """An event only `ch`'s own web clients see (sneaking, hiding: nobody else should know)."""
    room = getattr(ch, 'room', None)
    wm = getattr(getattr(ch, 'world', None), 'web_map', None)
    if room is None or wm is None:
        return
    msg = {'type': 'combat_events', 'room': getattr(room, 'vnum', None), 'events': [_event(k, src, dst, fields)]}
    try:
        asyncio.get_running_loop().create_task(wm.notify_event(ch, msg))
    except RuntimeError:
        pass


def emit(room, k, src=None, dst=None, **fields):
    """Queue one event for the web clients in `room`: sent at the end of this moment, or when
    the action it belongs to (hold) finishes."""
    if room is None:
        return
    ev = _event(k, src, dst, fields)
    vnum = getattr(room, 'vnum', None)
    if vnum is None:
        return
    target = _target()
    entry = target.get(vnum)
    if entry is None:
        entry = target[vnum] = (room, [])
    entry[1].append(ev)
    if target is _pending:
        _schedule()


def _schedule():
    global _scheduled
    if _scheduled or not _pending:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _scheduled = True
    loop.call_soon(lambda: asyncio.ensure_future(_flush()))


async def _flush():
    global _scheduled
    _scheduled = False
    batch = list(_pending.items())
    _pending.clear()
    for vnum, (room, events) in batch:
        world = None
        for ch in getattr(room, 'characters', []) or []:
            world = getattr(ch, 'world', None)
            if world:
                break
        wm = getattr(world, 'web_map', None) if world else None
        if not wm or not events:
            continue
        try:
            await wm.send_room_event(room, {'type': 'combat_events', 'room': vnum, 'events': events})
        except Exception as e:
            logger.debug(f"combat_events flush failed: {e}")


def result_of(text):
    """Map a combat-log line's outcome word to an event result (for call sites that only
    have the message)."""
    t = (text or '').lower()
    for word, res in (('parr', 'parry'), ('dodge', 'dodge'), ('block', 'block'), ('sidestep', 'dodge'),
                      ('miss', 'miss'), ('resist', 'resist'), ('immune', 'immune')):
        if word in t:
            return res
    return 'hit'
