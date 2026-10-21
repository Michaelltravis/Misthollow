"""Noticing, chasing and going home (features.pursuit), out of a fight.

    idle ──sees a foe──> alert ("!": a beat, ALERT_FAR across an open way) ──> pursue
    pursue: steps toward its quarry every `move_secs`, opening, unlocking or pounding doors on
            the way (path.py); attacks when they share a room
        ──past its leash (`leash_rooms` from where the chase began, or `chase_secs`)──> return
        ──loses the trail (out of sight, `chase_persistence` a step; covered tracks)──> return ("?")
    return: walks back to where the chase began, healed there (`return_heal`), then idle

A creature whose foe leaves the fight (flees, steps out) goes after them the same way. A
sentinel, a boss or a shopkeeper never leaves its post: it waits a moment, then resets (healed,
forgetting the fight). Sound (perception.hears) sends a creature that investigates to look.
Every creature, not the four hunters of old; their grudges still feed `memory` creatures.
"""
import time

LOOK_EVERY = 0.5          # seconds between looks around when idle
ALERT_NEAR = (0.6, 1.5)   # a beat before it attacks someone in its own room
ALERT_FAR = 1.0           # ...and before it charges someone across an open way (readability)
OPEN_TIME = (1.0, 3.0)    # it works the door this long before stepping through
SAW_THEM_GO = 4.0         # seconds after it last saw its quarry when it still knows where they went


def _say(room, text):
    if room is not None:
        import asyncio
        try:
            asyncio.get_event_loop().create_task(room.send_to_room(text))
        except Exception:
            pass


def _emit(kind, mob, target=None, *rooms):
    try:
        import combat_events as ev
        for room in {r for r in rooms if r is not None}:
            ev.emit(room, kind, src=mob, dst=target)
    except Exception:
        pass


def stays_put(mob, b) -> bool:
    import reach
    flags = set(getattr(mob, 'flags', None) or ())
    if 'sentinel' in flags or 'boss' in flags or b.profile.get('sentinel') or getattr(mob, 'special', None) in reach.SERVICE:
        return True
    try:
        from bosses import Boss
        return isinstance(mob, Boss)
    except Exception:
        return False


def free(mob) -> bool:
    from .targeting import owned
    return getattr(mob, 'room', None) is not None and not owned(mob) and getattr(mob, 'hp', 0) > 0


def _home(b):
    return b.chase.get('from')


async def _move(mob, d, out_words, in_words):
    """Step through an exit (already open), told to both rooms and the 3D clients."""
    ex = (mob.room.exits or {}).get(d) or {}
    to = ex.get('room')
    if to is None:
        return False
    old = mob.room
    c = mob.config.COLORS
    await old.send_to_room(f"{c['yellow']}{mob.name} {out_words} {d}.{c['reset']}")
    if mob in old.characters:
        old.characters.remove(mob)
    mob.room = to
    to.characters.append(mob)
    opposite = mob.config.DIRECTIONS.get(d, {}).get('opposite', 'somewhere')
    await to.send_to_room(f"{c['bright_red'] if 'hunting' in in_words else c['yellow']}{mob.name} {in_words} the {opposite}.{c['reset']}")
    try:
        await mob._notify_move(old, to, d, opposite)
    except Exception:
        pass
    return True


async def _through(mob, b, d, how, now, quarry=None):
    """One step along a route: through an open way, or work the door first. True if it acted."""
    import doors
    from . import perception
    ex = (mob.room.exits or {}).get(d) or {}
    door = ex.get('door')
    c = mob.config.COLORS
    rng = b.rng
    if isinstance(door, dict) and door.get('state') == 'closed':
        name = doors.label(door) if hasattr(doors, 'label') else door.get('name', 'door')
        if how in ('open', 'unlock'):
            started = b.chase.get('door_at')
            if started is None:
                b.chase['door_at'] = now + rng.uniform(*OPEN_TIME)
                await mob.room.send_to_room(f"{c['yellow']}{mob.name} {'fumbles a key into' if how == 'unlock' else 'works at'} the {name} {d}.{c['reset']}")
                return True
            if now < started:
                return True
            b.chase.pop('door_at', None)
            doors.apply(mob.room, d, state='open', **({'locked': False} if how == 'unlock' else {}))
            await mob.room.send_to_room(f"{c['yellow']}{mob.name} {'unlocks and opens' if how == 'unlock' else 'opens'} the {name} {d}.{c['reset']}")
            b.chase['next_move_at'] = now + 0.5
            return True
        if how == 'bash':
            from commands import CommandHandler
            max_hp = CommandHandler._door_max_hp(door)
            door.setdefault('hp', max_hp)
            blow = int(getattr(mob, 'str', 12) or 12) * 2 + int(getattr(mob, 'level', 1) or 1) + rng.randint(0, 10)
            door['hp'] -= min(blow, max(1, -(-max_hp // 3)))      # three blows at least: you hear it coming
            far = ex.get('room')
            b.chase['bashing'] = True
            perception.make_noise(mob.room)
            perception.make_noise(far)
            if door['hp'] <= 0:
                await CommandHandler._break_door_open(mob, mob.room, d, ex, door, mob.config)
            else:
                await mob.room.send_to_room(f"{c['bright_red']}{mob.name} slams against the {name} {d}! BOOM!{c['reset']}")
                if far is not None:
                    await far.send_to_room(f"{c['bright_red']}💥 BOOM! Something heavy pounds against the {name}!{c['reset']}")
            b.chase['next_move_at'] = now + b.profile.get('move_secs', 1.6)
            return True
        return False
    b.chase.pop('door_at', None)
    b.chase.pop('bashing', None)
    hunting = quarry is not None
    moved = await _move(mob, d, 'stalks' if hunting else 'heads back', 'arrives, hunting, from' if hunting else 'arrives from')
    b.chase['next_move_at'] = now + b.profile.get('move_secs', 1.6)
    if moved and hunting:
        b.chase['steps'] = b.chase.get('steps', 0) + 1
    return moved


def begin_chase(mob, b, quarry, now=None, alerted=False):
    """Go after quarry from here."""
    now = time.time() if now is None else now
    b.chase.setdefault('from', mob.room)
    b.chase.setdefault('since', now)
    b.chase['quarry'] = quarry
    b.chase['seen_at'] = now
    b.chase.setdefault('next_move_at', now + (0 if alerted else b.profile.get('move_secs', 1.6) * 0.5))
    b.mode = 'pursue'


async def give_up(mob, b, why, quarry=None, lost=False):
    """It turns back: the chase is over, it walks home and forgets the fight."""
    import reach
    c = mob.config.COLORS
    if quarry is not None:
        reach.lost(mob, quarry)
        try:
            mob.clear_grudge(getattr(quarry, 'name', None))
        except Exception:
            pass
    if lost:
        await mob.room.send_to_room(f"{c['yellow']}{mob.name} loses the trail and looks about, baffled.{c['reset']}")
        _emit('lost', mob, None, mob.room)
    else:
        await mob.room.send_to_room(f"{c['yellow']}{mob.name} gives up the chase and turns back.{c['reset']}")
    b.note('gives up', None, why)
    b.chase.pop('quarry', None)
    b.chase.pop('door_at', None)
    import brain
    brain.end_encounter(mob, b)
    b.mode = 'return'
    if _home(b) is None or _home(b) is mob.room:
        await _arrive_home(mob, b)


async def _arrive_home(mob, b):
    if b.profile.get('return_heal', True) and not getattr(mob, 'fighting', None):
        mob.hp = max(mob.hp, getattr(mob, 'max_hp', mob.hp))
    b.chase.clear()
    b.mode = 'idle'


def _leash_broken(mob, b, quarry, now):
    from . import path
    p = b.profile
    if now - b.chase.get('since', now) > p.get('chase_secs', 30):
        return 'too long a chase'
    home = _home(b)
    there = getattr(quarry, 'room', None)
    if home is None or there is None:
        return None
    n = path.rooms_apart(home, there, limit=int(p.get('leash_rooms', 3)) + 1)
    if n is None or n > p.get('leash_rooms', 3):
        return 'too far from home'
    return None


async def _chase(mob, b, now):
    from . import perception, path
    q = b.chase.get('quarry')
    if q is None or getattr(q, 'hp', 0) <= 0 or getattr(q, 'room', None) is None:
        await give_up(mob, b, 'its quarry is gone', None)
        return True
    if q.room is mob.room:
        if perception.sees(mob, b, q):
            await _attack(mob, b, q)
            return True
        await give_up(mob, b, 'it lost sight of them', q, lost=True)
        return True
    if stays_put(mob, b):
        if now - b.chase.get('since', now) > 6.0:       # a moment's wait at its post, then it resets
            await give_up(mob, b, 'it never leaves its post', q)
        return True
    if now < b.chase.get('next_move_at', 0):
        return True                                     # (between steps: nothing to work out)
    why = _leash_broken(mob, b, q, now)
    if why:
        await give_up(mob, b, why, q)
        return True
    # where are they? seen across an open way, just seen going, or followed by the trail (each
    # step a roll)
    adjacent = any(to is q.room and not shut for _d, to, shut in perception.open_ways(mob.room))
    if adjacent and perception.sees(mob, b, q, far=True):
        b.chase['seen_at'] = now
    recently = now - b.chase.get('seen_at', b.chase.get('since', now)) < SAW_THEM_GO
    if not recently and not b.chase.get('door_at') and not b.chase.get('bashing'):
        import stealth
        rng = b.rng
        if stealth.covered(q) and rng.random() < stealth.LOSE_EACH_STEP:
            await give_up(mob, b, 'the trail was swept away', q, lost=True)
            return True
        if rng.random() > b.profile.get('chase_persistence', 0.5):
            await give_up(mob, b, 'it lost the trail', q, lost=True)
            return True
    r = path.route(mob, b, mob.room, q.room, limit=int(b.profile.get('leash_rooms', 3)) + 2)
    if not r:
        await give_up(mob, b, 'no way to them', q)
        return True
    d, how = r[0]
    if not await _through(mob, b, d, how, now, quarry=q):
        await give_up(mob, b, 'the way is shut', q)
    elif mob.room is q.room and perception.sees(mob, b, q):
        await _attack(mob, b, q)
    return True


async def _attack(mob, b, q):
    from combat import CombatHandler
    c = mob.config.COLORS
    if getattr(mob, 'fighting', None) is None:
        await mob.room.send_to_room(f"{c['bright_red']}{mob.name} attacks {q.name}!{c['reset']}")
        if 'hidden' in (getattr(q, 'flags', None) or set()):
            q.flags.discard('hidden')
        await CombatHandler.start_combat(mob, q)
    b.mode = 'idle'
    b.chase.pop('quarry', None)
    b.chase.pop('next_move_at', None)
    b.chase.pop('since', None)


async def _go_home(mob, b, now):
    from . import path
    home = _home(b)
    if home is None or mob.room is home:
        await _arrive_home(mob, b)
        return False
    if now < b.chase.get('next_move_at', 0):
        return True
    r = path.route(mob, b, mob.room, home, limit=16)
    if not r:
        b.chase.clear()
        b.mode = 'idle'
        return False
    d, how = r[0]
    await _through(mob, b, d, how, now)
    if mob.room is home:
        await _arrive_home(mob, b)
    return True


async def _alerted(mob, b, now):
    from . import perception
    t = b.chase.get('alert')
    if t is None or getattr(t, 'hp', 0) <= 0:
        b.mode = 'idle'
        return False
    if now < b.chase.get('alert_until', 0):
        return True
    b.chase.pop('alert', None)
    near = t.room is mob.room
    if not perception.hostile_to(mob, t):
        b.mode = 'idle'
        return False
    if not perception.sees(mob, b, t, far=not near):
        # gone from sight while it bristled: if it saw which way (through an exit of this room)
        # it goes after them, else it lets it go
        if near or not any(to is t.room for _d, to, _shut in perception.open_ways(mob.room)):
            b.mode = 'idle'
            return False
    elif near:
        await _attack(mob, b, t)
        return True
    begin_chase(mob, b, t, now, alerted=True)
    return await _chase(mob, b, now)


HOSTILE_FLAGS = {'aggressive', 'hostile', 'aggr_good', 'aggr_evil', 'aggr_neutral', 'memory'}


def could_hunt(mob, b) -> bool:
    """Whether this creature could take against someone on sight now: its nature allows it
    (worked out once), and a player is in its zone or the next (world.process_npcs' awake zones;
    elsewhere there is no one to see, so it doesn't look)."""
    got = b.chase.get('could_hunt')
    if got is None:
        flags = set(getattr(mob, 'flags', None) or ())
        got = bool(flags & HOSTILE_FLAGS or getattr(mob, 'faction', None)) and 'no_attack' not in flags
        b.chase['could_hunt'] = got
    if not got:
        return False
    awake = getattr(getattr(mob, 'world', None), '_awake_now', None)
    if awake is None:
        return True
    return getattr(getattr(getattr(mob, 'room', None), 'zone', None), 'number', None) in awake


async def think(mob, b) -> bool:
    """Out of a fight, a turn of noticing, chasing or going home. True if it did something."""
    if b.mode == 'idle':
        now = time.time()
        if now < b.chase.get('look_at', 0) or not could_hunt(mob, b):
            return False                  # (the common case, kept cheap: most creatures, most ticks)
    if not free(mob) or getattr(mob, 'fighting', None) is not None:
        return False
    now = time.time()
    if b.mode == 'return':
        return await _go_home(mob, b, now)
    if b.mode == 'pursue':
        return await _chase(mob, b, now)
    if b.mode == 'alert':
        return await _alerted(mob, b, now)
    if b.mode == 'investigate':
        return await _investigate(mob, b, now)
    if now < b.chase.get('look_at', 0):
        return False
    b.chase['look_at'] = now + LOOK_EVERY * b.rng.uniform(0.8, 1.2)
    from . import perception
    if not perception.awake(mob):
        return False
    t, far = perception.look(mob, b)
    if t is not None and not (far and stays_put(mob, b)):
        b.mode = 'alert'
        b.chase['alert'] = t
        b.chase['alert_until'] = now + (ALERT_FAR if far else b.rng.uniform(*ALERT_NEAR))
        b.chase.setdefault('from', mob.room)
        c = mob.config.COLORS
        if far:
            await mob.room.send_to_room(f"{c['bright_yellow']}{mob.name} spots {t.name} and bristles!{c['reset']}")
            if t.room is not None:
                await t.room.send_to_room(f"{c['bright_yellow']}! {mob.name} has seen you from nearby!{c['reset']}")
        _emit('alert', mob, t, mob.room, t.room)
        b.note(f"notices {getattr(t, 'name', t)}", None, 'across an open way' if far else 'here')
        return True
    if stays_put(mob, b) or getattr(mob, 'patrol_route', None):
        return False
    noise = perception.hears(mob, b)
    if noise is not None:
        b.mode = 'investigate'
        b.chase['goal'] = noise
        b.chase.setdefault('from', mob.room)
        b.chase['since'] = now
        b.note('investigates a noise', None, f'room {getattr(noise, "vnum", "?")}')
        return True
    return False


async def _investigate(mob, b, now):
    from . import path, perception
    goal = b.chase.get('goal')
    if goal is None or now - b.chase.get('since', now) > b.profile.get('chase_secs', 30):
        b.mode = 'return'
        return True
    if now < b.chase.get('next_move_at', 0):
        return True                                     # (between steps)
    t, far = perception.look(mob, b)
    if t is not None:
        b.mode = 'alert'
        b.chase['alert'] = t
        b.chase['alert_until'] = now + (ALERT_FAR if far else b.rng.uniform(*ALERT_NEAR))
        _emit('alert', mob, t, mob.room, t.room)
        return True
    if mob.room is goal:
        b.mode = 'return'
        return True
    r = path.route(mob, b, mob.room, goal, limit=int(b.profile.get('hear_rooms', 1)) + 2)
    if not r:
        b.mode = 'return'
        return True
    d, how = r[0]
    if not await _through(mob, b, d, how, now, quarry=None):
        b.mode = 'return'
    return True


def after_fight(mob, b, now=None) -> bool:
    """Its foe left the fight (fled, stepped out): go after them. True if it did."""
    now = time.time() if now is None else now
    q = b.last_target
    if q is None or getattr(q, 'hp', 0) <= 0 or getattr(q, 'room', None) is None or q.room is mob.room:
        return False
    if not hasattr(q, 'connection') or b.mode in ('pursue', 'return'):
        return False
    if now - b.encounter.get('fought_at', now) > 6.0:
        return False
    begin_chase(mob, b, q, now)
    b.chase['from'] = b.chase.get('from') or mob.room
    b.note(f"goes after {getattr(q, 'name', q)}", None, 'its foe left the fight')
    return True
