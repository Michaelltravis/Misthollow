"""Mob brains: one per creature, deciding what it does in and out of a fight (docs/MOB_AI.md).

    Mobile.process_ai      -> think_idle(mob)       out of a fight, every tick it is due (scheduler)
    mob_ai.declare_intents -> declare(mob)          the round's pre-pass: wind up a special?
    mob_ai.mob_ai_tick     -> combat_turn(mob)      the creatures' turn of a round

The names on the left stay what the rest of the game calls: combat_hooks wraps them, the balance
sims call them. A brain calls back through mob_ai.<name> (never a reference it kept), so those
wrappers stay in the chain.

How clever a creature is comes from world/ai_profiles.json (profile.py): its zone's tier (gentle,
readable, brutal), its rank and its roles. What the brain does beyond the old rules (legacy.py) is
switched on feature by feature there ("features"):

    threat   whom it fights: a threat table from damage, healing and taunts (targeting.py); a
             real taunt; healers heal only their own side; a player's creatures fight as their
             owner bids, without the generic creature specials (phase 1a)

MH_BRAIN=0 in the environment (or Config.BRAIN = False) skips the brain altogether: the kill
switch while the phases land. MH_BRAIN_OFF=threat,... turns single features off.
"""
import os
import time

from . import legacy

ENABLED = os.environ.get('MH_BRAIN', '1') != '0'
FORCED_OFF = {f.strip() for f in os.environ.get('MH_BRAIN_OFF', '').split(',') if f.strip()}


def enabled() -> bool:
    if not ENABLED:
        return False
    try:
        from config import Config
        return getattr(Config, 'BRAIN', True)
    except Exception:
        return True


def on(feature) -> bool:
    """Whether a brain feature is in play (the brain on, the feature on in ai_profiles.json)."""
    if feature in FORCED_OFF or not enabled():
        return False
    from . import profile
    return profile.feature(feature)


def of(mob):
    """The creature's brain, made the first time it is asked for."""
    b = getattr(mob, '_brain', None)
    if b is None or b.mob is not mob:          # (a copied creature gets a brain of its own)
        from .brain import Brain
        b = Brain(mob)
        try:
            mob._brain = b
        except AttributeError:
            pass
    return b


def forget(mob):
    """Drop a creature's brain (its prototype or zone changed; the next think makes a new one)."""
    try:
        mob._brain = None
    except AttributeError:
        pass


def _thinks_for_itself(mob) -> bool:
    from .targeting import owned
    return not owned(mob)


async def think_idle(mob):
    if not enabled():
        return await legacy.idle(mob)
    b = of(mob)
    if on('threat') and not mob.fighting and len(b.threat) and _thinks_for_itself(mob):
        from . import targeting
        if await targeting.pick_up(mob, b) is not None:
            return                       # someone who hurt it is still here: back at them
        if time.time() - b.encounter.get('fought_at', 0) > targeting.RETURN_GRACE:
            b.reset_encounter()          # the fight is over
    return await legacy.idle(mob)


async def declare(mob):
    if not enabled():
        return await legacy.declare(mob)
    b = of(mob)
    if on('threat'):
        if not _thinks_for_itself(mob):
            return None                  # a player's creature: no creature specials
        if mob.fighting is not None:
            from . import targeting
            await targeting.retarget(mob, b)
    return await legacy.declare(mob)


async def combat_turn(mob):
    if not enabled():
        return await legacy.combat_turn(mob)
    b = of(mob)
    if on('threat'):
        if not _thinks_for_itself(mob):
            return False
        if mob.fighting is not None:
            from . import targeting
            await targeting.retarget(mob, b)
    return await legacy.combat_turn(mob)


async def next_target(mob):
    """A fighting creature's target fell or left (world._npc_combat_phase): the next in its threat
    table who is here, or None (and the old rule: it stops fighting)."""
    if not on('threat') or not _thinks_for_itself(mob):
        return None
    from . import targeting
    return await targeting.pick_up(mob, of(mob))


def taunted(mob, ch, secs):
    """A taunt (taunt, Commanding Shout, Rally, the Unbroken Banner, rescue): the creature turns
    on ch and is held there for secs. With threat off, the old rule: it just turns."""
    mob.fighting = ch
    if on('threat') and _thinks_for_itself(mob):
        if getattr(mob, 'position', None) not in ('fighting', 'sleeping', 'stunned', 'incapacitated', 'dead'):
            mob.position = 'fighting'
        if getattr(mob, '_turn_foe', None) is not None:
            mob._turn_foe = ch       # its real-time clock runs on: no early turn for being taunted
        b = of(mob)
        b.threat.taunt(ch, secs)
        b.last_target = ch
        b.encounter['fought_at'] = time.time()
        b.note(f"taunted by {getattr(ch, 'name', ch)}", None, f'{secs:.0f} s')


def enemies_of(player):
    """The creatures in the player's room fighting the player's side (a taunt's reach): never a
    shopkeeper standing by, nor anyone's pet."""
    from .targeting import owned, players_side
    room = getattr(player, 'room', None)
    out = []
    for ch in list(getattr(room, 'characters', []) or []):
        if hasattr(ch, 'connection') or owned(ch) or getattr(ch, 'hp', 0) <= 0:
            continue
        foe = getattr(ch, 'fighting', None)
        if foe is not None and players_side(foe) or getattr(player, 'fighting', None) is ch:
            out.append(ch)
    return out


_installed = False


def install():
    """The immortal commands (debug.py) and the threat hooks (hooks.py). Called from main.py after
    combat_hooks.install(), and by the balance sims and tests."""
    global _installed
    if _installed:
        return
    _installed = True
    from . import debug, hooks
    debug.install()
    hooks.install()
