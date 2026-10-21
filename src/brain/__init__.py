"""Mob brains: one per creature, deciding what it does in and out of a fight (docs/MOB_AI.md).

    Mobile.process_ai      -> think_idle(mob)       out of a fight, every tick it is due (scheduler)
    mob_ai.declare_intents -> declare(mob)          the round's pre-pass: wind up a special?
    mob_ai.mob_ai_tick     -> combat_turn(mob)      the creatures' turn of a round

The names on the left stay what the rest of the game calls: combat_hooks wraps them, the balance
sims call them. A brain calls back through mob_ai.<name> (never a reference it kept), so those
wrappers stay in the chain.

How clever a creature is comes from world/ai_profiles.json (profile.py): its zone's tier (gentle,
readable, brutal), its rank and its roles. Phase 0 runs the old rules unchanged (legacy.py) with
the brain in place around them. MH_BRAIN=0 in the environment (or Config.BRAIN = False) skips the
brain altogether: the kill switch while the phases land.
"""
import os

from . import legacy

ENABLED = os.environ.get('MH_BRAIN', '1') != '0'


def enabled() -> bool:
    if not ENABLED:
        return False
    try:
        from config import Config
        return getattr(Config, 'BRAIN', True)
    except Exception:
        return True


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


async def think_idle(mob):
    if not enabled():
        return await legacy.idle(mob)
    of(mob)
    return await legacy.idle(mob)


async def declare(mob):
    if not enabled():
        return await legacy.declare(mob)
    of(mob)
    return await legacy.declare(mob)


async def combat_turn(mob):
    if not enabled():
        return await legacy.combat_turn(mob)
    of(mob)
    return await legacy.combat_turn(mob)


_installed = False


def install():
    """The immortal commands (debug.py). Called from main.py after combat_hooks.install()."""
    global _installed
    if _installed:
        return
    _installed = True
    from . import debug
    debug.install()
