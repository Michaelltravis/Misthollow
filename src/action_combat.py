"""Real-time combat for the 3D client.

A web player whose /play client asks for it (its map socket subscribes with combat:'action', a
Settings toggle that is on by default) fights on their own clock instead of the 3-s round:

- each combatant has a swing clock, `next_swing_at`, set whenever it takes a turn (by the round
  wrapper in combat_hooks, in either mode);
- the blow lands the moment attack is pressed if the clock is ready (`webattack`), then every
  SWING seconds while the foe is in reach (the 200 ms action tick swings for you);
- skills and spells resolve at once behind a GCD-second global cooldown ("Not ready yet.");
- a creature fighting such a player acts on its own staggered clock too: a turn every
  MOB_EVERY s (± MOB_JITTER; the first a moment after it engages) in the order a round would
  give it (declare a wind-up, specials, its swing), and a wind-up lands WINDUP s after it is
  declared, checked every tick, so it can be stepped out of.

SWING is today's round, so damage per second is unchanged and every balance number holds.
Everything that counts in rounds (rituals, pets, a companion, a burning mount, marquee effects)
stays on the 3-s round; the round leaves out only the swings action mode makes. Telnet and the
2D client keep the round. Config.ACTION_COMBAT = False turns all of it off.
"""
import logging
import random
import time

from config import Config
import combat_events as ev

logger = logging.getLogger('Misthollow')

SWING = 3.0           # seconds between swings (today's round)
GCD = 1.0             # seconds between two skills or casts
TICK = 0.2            # how often the clocks are checked (main loop: every 2 ticks)
WINDUP = 2.0          # a creature's declared special lands this long after
MOB_EVERY = 3.0       # a creature's turn ...
MOB_JITTER = 0.3      # ... give or take
MOB_FIRST = (0.8, 1.2)  # its first turn after engaging
SKEW = 1.0            # the 3-s round leaves alone anyone who swung less than SWING - SKEW ago
PERFECT_WINDOW = 0.6  # a press in the last 0.6 s before the swing comes round is a perfect strike
PERFECT_GRACE = 0.15  # ... or just after it (the press arrives a moment late)
# reactions and getting away never wait for the global cooldown
GCD_EXEMPT = {'brace', 'sidestep', 'interrupt', 'flee', 'escape', 'webattack', 'perfect', 'swing'}


def enabled():
    return bool(getattr(Config, 'ACTION_COMBAT', True))


def _is_player(ch):
    return hasattr(ch, 'connection')


def wants(player) -> bool:
    """A player is in action mode while one of their live 3D clients asks for it (a closed
    tab, a lost socket or a newer login falls back to rounds at once)."""
    if not enabled() or not _is_player(player):
        return False
    wm = getattr(getattr(player, 'world', None), 'web_map', None)
    if wm is None:
        return False
    name = str(getattr(player, 'name', '') or '').lower()
    for c in list(getattr(wm, 'clients', ()) or ()):
        if getattr(c, 'combat', None) == 'action' and str(getattr(c, 'player_name', '') or '').lower() == name:
            return True
    return False


def on_clock(mob) -> bool:
    """A creature acts on its own clock while it fights an action-mode player beside it."""
    t = getattr(mob, 'fighting', None)
    return (t is not None and _is_player(t) and getattr(t, 'room', None) is getattr(mob, 'room', None)
            and getattr(mob, 'room', None) is not None and wants(t))


def active(ch) -> bool:
    return wants(ch) if _is_player(ch) else on_clock(ch)


def ready(ch, now=None) -> bool:
    return (now if now is not None else time.time()) >= getattr(ch, 'next_swing_at', 0)


def round_skips(ch, now=None) -> bool:
    """The 3-s round leaves out a swing for anyone on the action clock, and for anyone who
    swung less than SWING - SKEW ago (switching modes never brings two swings close)."""
    now = now if now is not None else time.time()
    return active(ch) or now < getattr(ch, 'next_swing_at', 0) - SKEW


def turn_taken(ch, now=None):
    """A turn was taken (the round wrapper calls this in either mode): the clock restarts."""
    ch.next_swing_at = (now if now is not None else time.time()) + SWING


# ---------------------------------------------------------------- swings
async def swing(ch, foe):
    """One blow on ch's own clock: the round wrapper's result ({'res': ...}), or None when it
    isn't time (or a blow is already on its way)."""
    if getattr(ch, '_swinging', False) or not ready(ch) or foe is None:
        return None
    ch._swinging = True            # before any await: a key press and the tick never both swing
    ch._swing_only = True          # the rest of the round (pets, rituals) stays on the 3-s round
    try:
        from combat import CombatHandler
        return await CombatHandler.one_round(ch, foe)
    finally:
        ch._swing_only = False
        ch._swinging = False


def in_reach(ch, foe) -> bool:
    try:
        import combat_range as cr
        from combat_hooks import _reach_of
        d = cr.distance(ch, foe)
        return d is None or d <= _reach_of(ch)[0] + 0.4
    except Exception:
        return True


def tell(player, res=None):
    """The player's 3D client: what the swing came to, when the next is ready, the cooldown."""
    now = time.time()
    ev.emit_private(player, 'swing', src=player, res=res,
                    next_ms=max(0, int((getattr(player, 'next_swing_at', 0) - now) * 1000)),
                    gcd_ms=max(0, int((getattr(player, 'gcd_until', 0) - now) * 1000)),
                    swing_ms=int(SWING * 1000))


async def webattack(player, args):
    """`webattack [#id]`: the 3D client's attack key in action mode. Starts the fight (its first
    blow is the swing) or swings now if the clock is ready; says when the next one comes."""
    from combat import CombatHandler
    c = player.config.COLORS
    room = getattr(player, 'room', None)
    target = None
    if args:
        try:
            target = player.find_target_in_room(args[0])
        except Exception:
            target = None
    foe = getattr(player, 'fighting', None)
    if target is None:
        target = foe or getattr(player, 'target', None)
    if target is None or room is None or getattr(target, 'room', None) is not room or getattr(target, 'hp', 0) <= 0:
        await player.send(f"{c['yellow']}Attack whom?{c['reset']}")
        return
    if target is player:
        return
    if not wants(player):
        # rounds (the setting is off, or the 2D client): the key opens a fight, the round swings
        if foe is None:
            await player.execute_command('kill', [args[0]] if args else [getattr(target, 'name', '').split()[-1]])
        return
    if foe is None:
        # not fighting yet: the usual way in (peaceful rooms, players, shopkeepers refuse there)
        await player.execute_command('kill', [args[0]] if args else [getattr(target, 'name', '').split()[-1]])
        tell(player, getattr(player, '_swing_res', None) if getattr(player, 'fighting', None) else None)
        return
    if target is not foe:
        # turning to another foe in the fight
        player.fighting = target
        foe = target
    if not ready(player):
        tell(player, 'perfect' if perfect_press(player) else 'not_ready')
        return
    perfect_press(player)
    if not in_reach(player, foe):
        await CombatHandler.one_round(player, foe)    # says it's out of reach (no turn taken)
        tell(player, 'oor')
        return
    result = await swing(player, foe)
    tell(player, result.get('res') if result else None)


def perfect_press(player, now=None) -> bool:
    """The attack key pressed in the last PERFECT_WINDOW s before the swing comes round (or
    just after): that swing lands perfectly. Pressed too early, this swing can't be perfect any
    more, so holding the key down never pays."""
    now = now if now is not None else time.time()
    nxt = getattr(player, 'next_swing_at', 0)
    if getattr(player, 'perfect_next', False):
        return True
    if now < getattr(player, 'swing_lockout_until', 0):
        return False
    if nxt - PERFECT_WINDOW <= now <= nxt + PERFECT_GRACE:
        player.perfect_next = True
        return True
    if now < nxt - PERFECT_WINDOW:
        player.swing_lockout_until = nxt + PERFECT_GRACE
    return False


# ---------------------------------------------------------------- the global cooldown
def gcd_applies(player, cmd, ability) -> bool:
    """Skills and casts wait for the global cooldown in action mode (never reactions)."""
    if not _is_player(player) or not wants(player):
        return False
    c = str(cmd or '').lower()
    if c in GCD_EXEMPT or str(ability or '').lower() in GCD_EXEMPT:
        return False
    return bool(ability) or c in ('cast', 'c', 'ca', 'cas')


async def gcd_refuse(player) -> bool:
    """True (and says "Not ready yet.") while the global cooldown runs."""
    left = getattr(player, 'gcd_until', 0) - time.time()
    if left <= 0:
        return False
    c = player.config.COLORS
    await player.send(f"{c['yellow']}Not ready yet.{c['reset']}")
    tell(player, 'gcd')
    return True


def gcd_start(player):
    player.gcd_until = time.time() + GCD


# ---------------------------------------------------------------- the action tick
async def tick(world):
    """Every TICK s: action-mode players swing when their clock comes round (and their foe is
    in reach); the creatures fighting them take their turns and land their wind-ups."""
    if not enabled():
        return
    now = time.time()
    # every action-mode player (one set upon before they have struck back counts too: the
    # creature's turns start at once)
    players = [p for p in list(getattr(world, 'players', {}).values()) if getattr(p, 'room', None) is not None and wants(p)]
    if not players:
        return
    mobs = []
    seen = set()
    for p in players:
        foe = getattr(p, 'fighting', None)
        room = p.room
        if foe is not None and getattr(foe, 'hp', 0) > 0 and foe in room.characters and ready(p, now) and in_reach(p, foe):
            try:
                result = await swing(p, foe)
                if result is not None:
                    tell(p, result.get('res'))
            except Exception as e:
                logger.debug(f"action swing failed for {p.name}: {e}")
        for ch in list(room.characters):
            if id(ch) not in seen and not _is_player(ch) and getattr(ch, 'fighting', None) is not None and on_clock(ch):
                seen.add(id(ch))
                mobs.append(ch)
    for mob in mobs:
        try:
            await mob_turn(mob, now)
        except Exception as e:
            logger.debug(f"action turn failed for {getattr(mob, 'name', '?')}: {e}")


async def mob_turn(mob, now):
    """A creature on the action clock: its wind-up lands WINDUP s after declaring; its turn
    comes every MOB_EVERY s, in a round's order (declare, specials, swing)."""
    import mob_ai
    intent = getattr(mob, 'pending_intent', None)
    if intent and now - intent.get('declared_at', now) >= intent.get('windup_action', WINDUP):
        await mob_ai._resolve_intent(mob)
    nxt = getattr(mob, '_turn_at', None)
    engaged = getattr(mob, '_turn_foe', None)
    if nxt is None or engaged is not mob.fighting:
        # it has just turned on an action-mode player: its first turn a moment from now
        mob._turn_foe = mob.fighting
        mob._turn_at = now + random.uniform(*MOB_FIRST)
        return
    if now < nxt:
        return
    mob._turn_at = now + MOB_EVERY + random.uniform(-MOB_JITTER, MOB_JITTER)
    if not getattr(mob, 'pending_intent', None):
        await mob_ai.declare_intents(mob)
    await mob_ai.mob_ai_tick(mob)
    foe = getattr(mob, 'fighting', None)
    if foe is None or getattr(foe, 'hp', 0) <= 0 or getattr(mob, 'hp', 0) <= 0:
        return
    mob.next_swing_at = 0          # its turn is its swing (the clock is the turn's)
    await swing(mob, foe)
    # the heroes' vitals after it struck
    wm = getattr(getattr(foe, 'world', None), 'web_map', None)
    if wm is not None and _is_player(foe):
        try:
            await wm.notify_combat(foe)
        except Exception:
            pass
