"""The deep and the dark: hazards some zones state on their rooms (`zone_mechanic`), and the
gear that answers them.

- **Drowning** (the Sunken Temple of Nereus, the Drowned Reliquary). A zone with a
  `drowning_timer` room is deep water in every underwater room. Out of an air pocket a hero
  holds their breath for AIR_TICKS ticks, then drowns: the zone's `damage_per_tick` each tick.
  An `air_pocket` room fills the lungs again; a `pressure_damage` room crushes anyone not made
  for the deep. Water breathing (worn gear flagged `water_breathing` — the Pearl, the Trident,
  the Coral Plate — or the affect) answers both.
- **Shadow corruption** (Shadowspire Citadel). A zone with a `shadow_corruption` room adds its
  `corruption_per_room` for every room entered there (a room of its own adds its own, the
  Corruption Chamber 25); an inner `light_source` room takes its `corruption_reduction` off.
  At `clone_spawn_threshold` the hero's shadow peels away and attacks (a Shadow Stalker), and
  half the corruption goes with it. Leaving the zone sheds it. Corruption immunity (the Amulet
  of Light) answers it.

Called on each room entered (commands.py, after the move) and once a combat round
(world.py, beside environment.tick); per-hero state is transient (not saved).
"""
import time

AIR_TICKS = 10          # breaths held: a minute at TICK_SECONDS
TICK_SECONDS = 6
SHADOW_CLONE_VNUM = 24501


def _mechanics(zone, kind):
    """The rooms of a zone stating a mechanic of this kind ({vnum: mechanic})."""
    cache = getattr(zone, '_mechanics_cache', None)
    if cache is None:
        cache = {}
        for room in (getattr(zone, 'rooms', None) or {}).values():
            m = getattr(room, 'zone_mechanic', None)
            if isinstance(m, dict) and m.get('type'):
                cache.setdefault(m['type'], {})[room.vnum] = m
        try:
            zone._mechanics_cache = cache
        except Exception:
            pass
    return cache.get(kind, {})


def _gear_flag(ch, flag):
    """Worn gear flagged so (or an affect of that name)."""
    if flag in (getattr(ch, 'affect_flags', None) or ()):
        return True
    totals = ch._gear_totals() if hasattr(ch, '_gear_totals') else {}
    if totals.get(flag, 0) > 0:
        return True
    return any(flag in (getattr(it, 'flags', None) or ()) for it in (getattr(ch, 'equipment', None) or {}).values() if it)


def _immortal(ch):
    v = getattr(ch, 'is_immortal', False)
    return bool(v() if callable(v) else v)


def breathes_water(ch) -> bool:
    return _gear_flag(ch, 'water_breathing') or _immortal(ch)


def corruption_immune(ch) -> bool:
    return _gear_flag(ch, 'corruption_immunity') or _immortal(ch)


def _deep(room):
    """The zone's drowning rule, when this room is under its water (None otherwise)."""
    zone = getattr(room, 'zone', None)
    if zone is None or getattr(room, 'sector_type', '') != 'underwater':
        return None
    rules = _mechanics(zone, 'drowning_timer')
    return next(iter(rules.values()), None)


def _colors(ch):
    return ch.config.COLORS


async def on_enter(player, room):
    """A hero has just entered a room."""
    c = _colors(player)
    mech = getattr(room, 'zone_mechanic', None) or {}
    # --- the deep
    if _deep(room) is not None and not breathes_water(player):
        if mech.get('type') == 'air_pocket':
            if getattr(player, '_breath', AIR_TICKS) < AIR_TICKS:
                await player.send(f"{c['bright_cyan']}{mech.get('message') or 'You gulp fresh air.'}{c['reset']}")
            player._breath = AIR_TICKS
        elif getattr(player, '_breath', None) is None:
            player._breath = AIR_TICKS
            player._breath_at = time.time()
            await player.send(f"{c['bright_cyan']}You take a deep breath and go under. "
                              f"(Air for about {AIR_TICKS * TICK_SECONDS} seconds; find an air pocket.){c['reset']}")
    elif _deep(room) is None and getattr(player, '_breath', None) is not None:
        player._breath = None
        await player.send(f"{c['bright_cyan']}You break the surface and breathe again.{c['reset']}")
    # --- the dark
    zone = getattr(room, 'zone', None)
    rules = _mechanics(zone, 'shadow_corruption') if zone is not None else {}
    if not rules:
        if getattr(player, '_corruption', 0):
            player._corruption = 0
            await player.send(f"{c['white']}The darkness in you thins and lifts in the open air.{c['reset']}")
        return
    if corruption_immune(player):
        return
    base = min(rules.values(), key=lambda m: m.get('corruption_per_room', 99))
    level = getattr(player, '_corruption', 0)
    if mech.get('type') == 'light_source':
        eased = min(level, int(mech.get('corruption_reduction', 10)))
        player._corruption = level - eased
        if eased:
            await player.send(f"{c['bright_yellow']}{mech.get('message') or 'The light eases the darkness in you.'} "
                              f"(Shadow corruption: {player._corruption}%){c['reset']}")
        return
    gain = int((mech if mech.get('type') == 'shadow_corruption' else base).get('corruption_per_room', 5))
    player._corruption = min(100, level + gain)
    text = (mech.get('message') if mech.get('type') == 'shadow_corruption' and mech.get('message') else None) \
        or (base.get('corruption_message') or 'Darkness seeps into your soul. Shadow corruption: {level}%')
    if '{level}' in text:
        text = text.replace('{level}', str(player._corruption))
    else:
        text = f"{text} (Shadow corruption: {player._corruption}%)"
    await player.send(f"{c['magenta']}{text}{c['reset']}")
    threshold = int(base.get('clone_spawn_threshold', 75))
    if player._corruption >= threshold:
        await _shadow_clone(player, room, base)


async def _shadow_clone(player, room, rule):
    """The hero's shadow peels away and attacks; half the corruption goes with it."""
    c = _colors(player)
    world = getattr(player, 'world', None)
    proto = getattr(world, 'mob_prototypes', {}).get(SHADOW_CLONE_VNUM) if world else None
    player._corruption //= 2
    await player.send(f"{c['bright_red']}{rule.get('clone_message') or 'Your shadow peels away from the floor and attacks!'}"
                      f"{c['reset']} {c['magenta']}(Shadow corruption: {player._corruption}%){c['reset']}")
    if not proto:
        return
    from bosses import create_mob_from_prototype
    mob = create_mob_from_prototype(dict(proto), world)
    mob.short_desc = f"{player.name}'s shadow"
    mob.room = mob.home_room = room
    mob.home_zone = room.zone.number if getattr(room, 'zone', None) else None
    room.characters.append(mob)
    world.npcs.append(mob)
    try:
        from combat import CombatHandler
        await CombatHandler.start_combat(mob, player)
    except Exception:
        mob.fighting, mob.position = player, 'fighting'


async def tick(world):
    """Once a combat round: lungs empty in the deep, and the deep crushes."""
    now = time.time()
    for p in list(getattr(world, 'players', {}).values()):
        room = getattr(p, 'room', None)
        if room is None or getattr(p, 'hp', 0) <= 0:
            continue
        rule = _deep(room)
        if rule is None:
            if getattr(p, '_breath', None) is not None:
                p._breath = None   # surfaced some other way (recall, a portal)
            continue
        if breathes_water(p):
            p._breath = None
            continue
        if now - getattr(p, '_breath_at', 0) < TICK_SECONDS:
            continue
        p._breath_at = now
        c = _colors(p)
        mech = getattr(room, 'zone_mechanic', None) or {}
        if mech.get('type') == 'air_pocket':
            p._breath = AIR_TICKS
            continue
        if getattr(p, '_breath', None) is None:
            p._breath = AIR_TICKS
        if mech.get('type') == 'pressure_damage':
            dmg = int(mech.get('damage_per_tick', 40))
            await p.send(f"{c['blue']}{mech.get('message') or 'The pressure crushes you!'} [{dmg}]{c['reset']}")
            if await p.take_damage(dmg, None, 'drowning'):
                continue
        if p._breath > 0:
            p._breath -= 1
            if p._breath in (5, 3, 1):
                await p.send(f"{c['cyan']}Your chest tightens: air for {p._breath * TICK_SECONDS} more seconds.{c['reset']}")
            elif p._breath == 0:
                await p.send(f"{c['bright_red']}Your breath gives out!{c['reset']}")
            continue
        dmg = int(rule.get('damage_per_tick', 25))
        await p.send(f"{c['bright_red']}{rule.get('message') or 'You are drowning!'} [{dmg}]{c['reset']}")
        await p.take_damage(dmg, None, 'drowning')

