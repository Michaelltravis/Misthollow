"""Whom a creature fights (features.threat): its threat table, weighed by its profile.

    score(t) = threat(t) / the top threat
               * (1 + focus_casters if t casts + focus_healers if t healed lately + finisher if t is low)
               * REACH_PENALTY when a creature that fights in melee can't reach t

A creature changes target only for one that scores more than `target_stickiness` above the one it
has, and not again within `switch_cooldown_s`. A taunt holds it regardless. It never turns while
winding up a special (the warning named whom it is for). Every turn is said aloud ("The ogre turns
on Mira!") and sent to /play as an 'aggro' event.

Anything else in the game that sets a creature's target (rescue, a pull, a helper joining, the
older abilities) is respected: the brain sees the target changed under it and holds the new one
for OVERRIDE_SECS, as a short taunt.
"""
import time

CASTERS = {'mage', 'necromancer', 'sorcerer', 'wizard', 'warlock'}
HEALED_LATELY = 10.0     # seconds a heal marks the healer
LOW_HP = 0.25
REACH_PENALTY = 0.6
OVERRIDE_SECS = 3.0      # about a round
RETURN_GRACE = 6.0       # out of a fight this long, a creature forgets it (two rounds)


_OWNED_KINDS = None


def owned(ch) -> bool:
    """A player's creature: a pet, a hired companion, a raised servant."""
    global _OWNED_KINDS
    if getattr(ch, 'owner', None) is not None:
        return True
    if _OWNED_KINDS is None:
        try:
            from pets import Pet
            from companions import Companion
            _OWNED_KINDS = (Pet, Companion)
        except Exception:
            return False
    return isinstance(ch, _OWNED_KINDS)


def players_side(ch) -> bool:
    return hasattr(ch, 'connection') or owned(ch)


def unseen(mob, t) -> bool:
    """Gone from its sight: vanished or hidden, or invisible to a creature that can't see it.
    (Phase 2a gives creatures their own eyes and ears; until then, this much.)"""
    if 'hidden' in (getattr(t, 'flags', None) or ()):
        return True
    if 'invisible' in (getattr(t, 'affect_flags', None) or ()):
        return not ('detect_invisible' in (getattr(mob, 'affect_flags', None) or ())
                    or 'aware' in (getattr(mob, 'flags', None) or ()))
    return False


def valid(mob, t) -> bool:
    room = getattr(mob, 'room', None)
    return (t is not None and t is not mob and getattr(t, 'hp', 0) > 0 and getattr(t, 'is_alive', True)
            and room is not None and t in room.characters and getattr(t, 'position', None) != 'dead'
            and not unseen(mob, t))


def _class(t):
    return str(getattr(t, 'char_class', '') or '').lower()


def _reaches(mob, t, profile):
    if profile.get('keep_range'):
        return True
    try:
        import combat_range as cr
        d = cr.distance(mob, t)
        if d is None:
            return True
        return d <= cr.mob_reach(mob)[0] + 1.5
    except Exception:
        return True


def score(mob, b, t, top, now):
    p = b.profile
    s = b.threat.get(t) / top if top > 0 else 0.0
    if s <= 0:
        return 0.0
    mult = 1.0
    if _class(t) in CASTERS:
        mult += p.get('focus_casters', 0.0)
    if now - b.encounter.get('healed', {}).get(t, -1e9) <= HEALED_LATELY:
        mult += p.get('focus_healers', 0.0)
    if getattr(t, 'hp', 1) < LOW_HP * max(1, getattr(t, 'max_hp', 1)):
        mult += p.get('finisher', 0.0)
    if not _reaches(mob, t, p):
        mult *= REACH_PENALTY
    return s * mult


def best(mob, b, now):
    """(target, score) of the best valid entry in the threat table, else (None, 0)."""
    entries = [(t, v) for t, v in b.threat.ranked() if valid(mob, t)]
    if not entries:
        return None, 0.0
    top = entries[0][1]
    scored = [(t, score(mob, b, t, top, now)) for t, _ in entries]
    return max(scored, key=lambda x: x[1])


async def turn_on(mob, b, t, now, why):
    """Make t the creature's target, aloud."""
    old = mob.fighting
    mob.fighting = t
    if getattr(mob, 'position', None) != 'fighting':
        mob.position = 'fighting'
    if getattr(mob, '_turn_foe', None) is not None:
        mob._turn_foe = t        # its real-time clock runs on (action_combat.mob_turn): no early turn for turning
    b.last_target = t
    b.encounter['switched_at'] = now
    b.note(f"turns on {getattr(t, 'name', t)}", None, why)
    if old is not t and getattr(mob, 'room', None) is not None:
        c = mob.config.COLORS
        try:
            await mob.room.send_to_room(f"{c['bright_red']}⚔ {mob.name} turns on {t.name}!{c['reset']}")
        except Exception:
            pass
        try:
            import combat_events as ev
            ev.emit(mob.room, 'aggro', src=mob, dst=t)
        except Exception:
            pass


def _seed_and_notice(mob, b, now):
    """Respect a target the rest of the game set; give a first foe a foothold in the table."""
    cur = mob.fighting
    if cur is None:
        return
    if b.last_target is not None and cur is not b.last_target and cur is not b.threat.fixated_on \
            and valid(mob, cur):
        b.threat.taunt(cur, OVERRIDE_SECS, now)
        b.note(f"held on {getattr(cur, 'name', cur)}", None, 'set from outside (rescue, a pull, a helper)')
    elif cur not in b.threat:
        b.threat.add(cur, 1.0)
    b.last_target = cur


async def retarget(mob, b, now=None):
    """Once a turn of a fight: whom to fight now."""
    now = time.time() if now is None else now
    b.encounter['fought_at'] = now
    b.threat.fade(now)
    _seed_and_notice(mob, b, now)
    if getattr(mob, 'pending_intent', None):
        return                               # the warning named its target
    cur = mob.fighting
    fix = b.threat.fixated_on
    if fix is not None and now < b.threat.fixated_until and valid(mob, fix):
        if cur is not fix:
            await turn_on(mob, b, fix, now, 'taunted')
        return
    t, s = best(mob, b, now)
    if t is None or t is cur:
        return
    if not valid(mob, cur):
        await turn_on(mob, b, t, now, 'its foe is gone')
        return
    p = b.profile
    top = b.threat.ranked()[0][1] if len(b.threat) else 0.0
    cs = score(mob, b, cur, top, now)
    if s > cs * (1.0 + p.get('target_stickiness', 0.3)) \
            and now >= b.encounter.get('switched_at', -1e9) + p.get('switch_cooldown_s', 6):
        await turn_on(mob, b, t, now, f"score {s:.2f} over {cs:.2f}")


async def pick_up(mob, b, now=None):
    """Its target fell or left: the next in its table who is here, else None (the fight is over)."""
    now = time.time() if now is None else now
    if not len(b.threat) or now - b.encounter.get('fought_at', now) > RETURN_GRACE:
        return None
    t, _ = best(mob, b, now)
    if t is not None:
        b.encounter['fought_at'] = now
        await turn_on(mob, b, t, now, 'the next who hurt it')
    return t
