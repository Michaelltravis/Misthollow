"""Cover Tracks (docs/STEALTH.md): a thief's or an assassin's way of leaving no trail.

Swept away (`cover_tracks`), whatever is hunting the hero and not in sight of them loses the
trail at once (a hunter, a tracker, a creature that holds a grudge), and for a few minutes after
(the 'tracks_covered' flag):
  - a hunter still after them may lose the trail at each step of its hunt (mobs.hunting_ai);
  - creatures across the open land notice them only from half as far (reach.noticed);
  - a creature they flee or escape from leaves them alone twice as long (reach.lost);
  - a theft leaves no trace to give them away (steal: easier);
  - in /play they leave no footprints in snow and sand (main.js).
"""
import random
import time

COOLDOWN = 45          # seconds
LOSE_EACH_STEP = 0.35  # a hunter's chance, each step of its hunt, to lose a covered trail


def covered(ch):
    return 'tracks_covered' in (getattr(ch, 'affect_flags', None) or ())


def lose_odds(player, mob):
    """How likely a creature after the hero loses the trail when it is swept away (0..1)."""
    skill = (getattr(player, 'skills', None) or {}).get('cover_tracks', 50) or 50
    lvl = (getattr(player, 'level', 1) or 1) - (getattr(mob, 'level', 1) or 1)
    return max(0.25, min(0.95, (60 + skill / 2 + lvl * 2) / 100))


def lose_trail(mob, player, words='sniffs at the ground and casts about, but the trail is gone'):
    """This creature loses the hero's trail: its grudge, its hunt, and it leaves them be a while."""
    name = getattr(player, 'name', '')
    if hasattr(mob, 'clear_grudge'):
        mob.clear_grudge(name)
    else:
        (getattr(mob, 'grudge_list', None) or {}).pop(name, None)
    if getattr(mob, 'hunting_target', None) is player:
        mob.hunting_target = None
    import reach
    reach.lost(mob, player, 90)
    return words


async def cover_tracks(player):
    c = player.config.COLORS
    if 'cover_tracks' not in (player.skills or {}):
        await player.send(f"{c['red']}You don't know how to cover your tracks.{c['reset']}")
        return
    if getattr(player, 'fighting', None):
        await player.send(f"{c['yellow']}No time to sweep a trail with steel in your face.{c['reset']}")
        return
    now = time.time()
    left = getattr(player, 'cover_tracks_cooldown', 0) - now
    if left > 0:
        await player.send(f"{c['yellow']}Your trail is still fresh in your mind's eye: wait {int(left) + 1}s.{c['reset']}")
        return
    player.cover_tracks_cooldown = now + COOLDOWN
    skill = player.skills.get('cover_tracks', 50) or 50
    if random.randint(1, 100) > max(35, skill + 20):
        await player.send(f"{c['yellow']}You scuff at your trail, but leave it plainer than before.{c['reset']}")
        if hasattr(player, 'improve_skill'):
            await player.improve_skill('cover_tracks', difficulty=3)
        return
    from affects import AffectManager
    AffectManager.remove_affect_by_name(player, 'cover_tracks')     # (a fresh sweep: the full time again)
    AffectManager.apply_affect(player, {
        'name': 'cover_tracks', 'type': AffectManager.TYPE_FLAG, 'applies_to': 'tracks_covered',
        'value': 1, 'duration': 20 + (player.level or 1) // 2, 'caster_level': player.level})
    await player.send(f"{c['bright_cyan']}You sweep your trail with your cloak's hem, step only on stone and root, "
                      f"and leave nothing behind you.{c['reset']}")
    if player.room:
        await player.room.send_to_room(f"{player.name} crouches and brushes at the ground behind them.", exclude=[player])
    # whatever is on the trail and not in sight of the hero loses it now
    lost = 0
    for mob in list(getattr(player.world, 'npcs', []) or []):
        if getattr(mob, 'room', None) is None or mob.room is player.room:
            continue
        if player.name not in (getattr(mob, 'grudge_list', None) or {}) and getattr(mob, 'hunting_target', None) is not player:
            continue
        if random.random() <= lose_odds(player, mob):
            words = lose_trail(mob, player)
            lost += 1
            try:
                await mob.room.send_to_room(f"{c['yellow']}{mob.name} {words}.{c['reset']}")
            except Exception:
                pass
    if lost:
        await player.send(f"{c['green']}Somewhere behind you, {'something loses' if lost == 1 else f'{lost} pursuers lose'} your trail.{c['reset']}")
    if hasattr(player, 'improve_skill'):
        await player.improve_skill('cover_tracks', difficulty=3)
