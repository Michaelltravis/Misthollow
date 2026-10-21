"""A real taunt for the classes that hold the line (features.threat).

    taunt [creature]     a warrior or a paladin in a fight: the creature (by default the one you
                         fight, else one fighting your side) turns on you and is held SECS seconds
                         (BOSS_SECS for a boss), and you go to the top of its threat table.
                         Once every COOLDOWN seconds.

Anyone else, or out of a fight, "taunt" stays the social it always was.
"""
import time

CLASSES = {'warrior', 'paladin'}
SECS = 6.0
BOSS_SECS = 4.0
COOLDOWN = 8.0


def _is_boss(mob):
    try:
        from bosses import Boss
        if isinstance(mob, Boss):
            return True
    except Exception:
        pass
    return getattr(mob, 'rank', None) in ('boss', 'sub-boss') or 'boss' in getattr(mob, 'flags', ())


async def command(player, args) -> bool:
    """True when the taunt was a tank's taunt (done, or refused with a reason); False: the social."""
    import brain
    if not brain.on('threat') or str(getattr(player, 'char_class', '')).lower() not in CLASSES:
        return False
    foes = brain.enemies_of(player)
    if not foes:
        return False                                   # nobody to hold: the social
    mob = None
    if args:
        mob = player.find_target_in_room(' '.join(args))
        if mob not in foes:
            return False                               # taunting someone not in the fight: the social
    if mob is None:
        mob = player.fighting if player.fighting in foes else foes[0]
    c = player.config.COLORS
    now = time.time()
    left = getattr(player, 'taunt_cooldown_until', 0) - now
    if left > 0:
        await player.send(f"{c['yellow']}You can taunt again in {left:.0f}s.{c['reset']}")
        return True
    player.taunt_cooldown_until = now + COOLDOWN
    secs = BOSS_SECS if _is_boss(mob) else SECS
    was = mob.fighting
    brain.taunted(mob, player, secs)
    if player.fighting is None:
        player.fighting = mob
        player.position = 'fighting'
    await player.send(f"{c['bright_yellow']}You taunt {mob.name}! It turns on you.{c['reset']}")
    if player.room:
        await player.room.send_to_room(
            f"{c['bright_yellow']}{player.name} taunts {mob.name}, drawing its fury"
            f"{' away from ' + was.name if was is not None and was is not player else ''}!{c['reset']}",
            exclude=[player])
        try:
            import combat_events as ev
            ev.emit(player.room, 'aggro', src=mob, dst=player)
        except Exception:
            pass
    return True
