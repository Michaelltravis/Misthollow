"""Rare elites (docs/GAMEPLAY_POLISH.md, group 4): now and then, in a zone where someone is
playing, one of its ordinary creatures turns up as a rare: a name of its own ("a grizzled grey
wolf"), much tougher and stronger, worth three times the experience and four times the gold,
carrying a piece of gear fit for its level, and a gold glow about it in /play (map_system ward
'elite'). The zone is told where it was seen. One at a time a zone; checked with the weather
(world.weather_tick, every five minutes).
"""
import logging
import random

logger = logging.getLogger(__name__)

CHANCE = 0.35            # each check, for each zone with a player in it
TITLES = ('grizzled', 'savage', 'ancient', 'dread', 'elder', 'scarred', 'monstrous', 'feral', 'cunning', 'blood-mad')
NOT = {'boss', 'sentinel', 'shopkeeper', 'trainer', 'peaceful', 'nokill', 'no_kill', 'healer', 'banker', 'innkeeper', 'elite'}


def eligible(mob):
    flags = set(str(f).lower() for f in (getattr(mob, 'flags', None) or ()))
    if flags & NOT or getattr(mob, 'elite', False) or getattr(mob, 'owner', None) is not None:
        return False
    if getattr(mob, 'special', None) or getattr(mob, 'fighting', None) or hasattr(mob, 'connection'):
        return False
    room = getattr(mob, 'room', None)
    if room is None or 'peaceful' in (room.flags or ()):
        return False
    return getattr(mob, 'hp', 0) > 0 and (getattr(mob, 'level', 1) or 1) >= 2


def rename(short, title):
    """'a grey wolf' -> 'a grizzled grey wolf' (the article kept, made to fit)."""
    words = (short or 'a creature').split()
    if words and words[0].lower() in ('a', 'an', 'the'):
        rest = ' '.join(words[1:])
        art = 'the' if words[0].lower() == 'the' else ('an' if title[0] in 'aeiou' else 'a')
        return f"{art} {title} {rest}"
    return f"{title} {short}"


def gear_for(world, level):
    """A piece of wearable gear (weapon or armour) fit for a creature of this level, the better
    the more it is worth; None when nothing fits."""
    protos = getattr(world, 'obj_prototypes', None) or {}
    fits = [p for p in protos.values() if isinstance(p, dict) and p.get('item_type') in ('weapon', 'armor')
            and level - 6 <= (p.get('min_level') or 0) <= level + 2]
    if not fits:
        return None
    fits.sort(key=lambda p: p.get('value') or 0, reverse=True)
    pick = random.choice(fits[:max(1, len(fits) // 4)])
    from objects import create_object
    return create_object(pick['vnum'], world)


def promote(mob, world=None, title=None):
    """Make this creature a rare elite. Returns its new short description."""
    title = title or random.choice(TITLES)
    mob.elite = True
    mob.flags = set(mob.flags or ()) | {'elite'}
    mob.short_desc = rename(getattr(mob, 'short_desc', None) or mob.name, title)
    mob.name = f"{title} {mob.name}"
    mob.max_hp = int(mob.max_hp * 2.5)
    mob.hp = mob.max_hp
    lvl = getattr(mob, 'level', 1) or 1
    mob.damroll = (getattr(mob, 'damroll', 0) or 0) + max(2, lvl // 4)
    mob.hitroll = (getattr(mob, 'hitroll', 0) or 0) + max(2, lvl // 5)
    mob.exp = int((getattr(mob, 'exp', 0) or lvl * 100) * 3)
    mob.gold = int((getattr(mob, 'gold', 0) or lvl * 5) * 4)
    item = gear_for(world, lvl) if world is not None else None
    if item is not None:
        if not hasattr(mob, 'inventory') or mob.inventory is None:
            mob.inventory = []
        mob.inventory.append(item)
    return mob.short_desc


async def tick(world):
    """Each zone with a player in it may get a rare (one at a time a zone)."""
    from mobs import zone_of
    players = [p for p in getattr(world, 'players', {}).values() if getattr(p, 'room', None)]
    zones = {zone_of(p.room) for p in players}
    zones.discard(None)
    for z in zones:
        if random.random() > CHANCE:
            continue
        live = [m for m in getattr(world, 'npcs', []) if getattr(m, 'room', None) is not None and zone_of(m.room) == z]
        if any(getattr(m, 'elite', False) and getattr(m, 'hp', 0) > 0 for m in live):
            continue
        pool = [m for m in live if eligible(m)]
        if not pool:
            continue
        mob = random.choice(pool)
        name = promote(mob, world)
        await announce(world, z, mob, name)


async def announce(world, zone, mob, name):
    c = world.config.COLORS
    where = getattr(mob.room, 'name', 'somewhere')
    from mobs import zone_of
    for p in list(getattr(world, 'players', {}).values()):
        if getattr(p, 'room', None) is None or zone_of(p.room) != zone:
            continue
        await p.send(f"{c['bright_yellow']}★ A rare creature stirs: {name} has been seen near {where}!{c['reset']}")
        wm = getattr(world, 'web_map', None)
        if wm:
            try:
                await wm.notify_event(p, {'type': 'world_rare', 'name': name, 'where': where, 'vnum': mob.room.vnum})
            except Exception:
                pass
    logger.info(f"rare elite: {name} in room {mob.room.vnum}")
