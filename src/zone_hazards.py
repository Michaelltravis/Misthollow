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
  half the corruption goes with it. Leaving the zone sheds it, and the shadow fades with it.
  Corruption immunity (the Amulet of Light) answers it.
- **Steam** (the Clockwork Foundry). A `steam_damage` room scalds whoever stands in it while
  its steam is on (`currently_active`, on unless it says not). A `lever` room's lever (`pull
  lever`) sends the steam from its `steam_from` rooms to its `steam_to` rooms, and back when
  pulled again; the pressure builds back by itself after STEAM_BACK seconds.
- **Secret ways** (Shadowspire's Mirror Chamber and Shadow Library). A `puzzle_room` hides its
  `hidden_exit` until a hero solves it: `touch mirror`, `read tome`. A solved one stays open
  to that hero (Player.discovered_exits, saved).

Called on each room entered (commands.py, after the move), once a combat round (world.py,
beside environment.tick), by pull/read/touch (commands.py), and once when the world loads
(seed). Per-hero breath and corruption are transient; the steam is the world's.
"""
import msgkind
import time

AIR_TICKS = 10          # breaths held: a minute at TICK_SECONDS
TICK_SECONDS = 6
SHADOW_CLONE_VNUM = 24501
STEAM_BACK = 600        # a pulled lever springs back (the pressure builds again) after this long
# what a hero does to a puzzle room's thing: (verb, words that name it)
PUZZLE_ACTS = {'mirror_door': ('touch', {'mirror', 'mirrors', 'reflection', 'reflections', 'door'}),
               'shadow_tome': ('read', {'book', 'books', 'tome', 'tomes', 'shelf', 'shelves', 'passage'})}
LEVER_WORDS = {'lever', 'levers', 'valve', 'valves', 'wheel', 'wheels', 'brass'}


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
    # --- the foundry's steam and the citadel's secrets
    kind = mech.get('type')
    if kind == 'steam_damage' and steam_on(room):
        await player.send(f"{c['bright_red']}Steam roars through the pipes here: get through, or find the lever.{c['reset']}")
    elif kind == 'steam_damage':
        await player.send(f"{c['cyan']}The pipes here are cold; the steam has been sent elsewhere.{c['reset']}")
    elif kind == 'lever':
        await player.send(f"{c['yellow']}The lever stands {'down, pulled' if lever_pulled(room) else 'at rest'}"
                          f" (pull lever).{c['reset']}")
    elif kind == 'steam_pressure' and mech.get('description'):
        await player.send(f"{c['yellow']}{mech['description']}{c['reset']}")
    elif kind == 'puzzle_room' and mech.get('hint') and not _found(player, room, mech):
        await player.send(f"{c['bright_magenta']}{mech['hint']}{c['reset']}")
    # --- the deep
    if _deep(room) is not None and not breathes_water(player):
        if mech.get('type') == 'air_pocket':
            if getattr(player, '_breath', AIR_TICKS) < AIR_TICKS:
                await msgkind.send_ui(player, f"{c['bright_cyan']}{mech.get('message') or 'You gulp fresh air.'}{c['reset']}")
            player._breath = AIR_TICKS
        elif getattr(player, '_breath', None) is None:
            player._breath = AIR_TICKS
            player._breath_at = time.time()
            await msgkind.send_ui(player, f"{c['bright_cyan']}You take a deep breath and go under. "
                                          f"(Air for about {AIR_TICKS * TICK_SECONDS} seconds; find an air pocket.){c['reset']}")
    elif _deep(room) is None and getattr(player, '_breath', None) is not None:
        player._breath = None
        await msgkind.send_ui(player, f"{c['bright_cyan']}You break the surface and breathe again.{c['reset']}")
    # --- the dark
    zone = getattr(room, 'zone', None)
    rules = _mechanics(zone, 'shadow_corruption') if zone is not None else {}
    if not rules:
        if getattr(player, '_corruption', 0):
            player._corruption = 0
            await msgkind.send_ui(player, f"{c['white']}The darkness in you thins and lifts in the open air.{c['reset']}")
        await _shadow_fades(player)
        return
    if corruption_immune(player):
        return
    base = min(rules.values(), key=lambda m: m.get('corruption_per_room', 99))
    level = getattr(player, '_corruption', 0)
    if mech.get('type') == 'light_source':
        eased = min(level, int(mech.get('corruption_reduction', 10)))
        player._corruption = level - eased
        if eased:
            await msgkind.send_ui(player, f"{c['bright_yellow']}{mech.get('message') or 'The light eases the darkness in you.'} "
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
    await msgkind.send_ui(player, f"{c['magenta']}{text}{c['reset']}")
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
    mob._shadow_of = player
    player._shadow = mob
    mob.room = mob.home_room = room
    mob.home_zone = room.zone.number if getattr(room, 'zone', None) else None
    room.characters.append(mob)
    world.npcs.append(mob)
    try:
        from combat import CombatHandler
        await CombatHandler.start_combat(mob, player)
    except Exception:
        mob.fighting, mob.position = player, 'fighting'


async def _shadow_fades(player):
    """A hero's shadow does not outlive the citadel's hold on them: it goes when they leave."""
    shadow = getattr(player, '_shadow', None)
    player._shadow = None
    if shadow is None or getattr(shadow, 'hp', 0) <= 0:
        return
    room = getattr(shadow, 'room', None)
    world = getattr(player, 'world', None)
    if room is not None and shadow in room.characters:
        room.characters.remove(shadow)
    if world is not None and shadow in getattr(world, 'npcs', []):
        world.npcs.remove(shadow)
    for ch in list(getattr(room, 'characters', None) or []):
        if getattr(ch, 'fighting', None) is shadow:
            ch.fighting = None
            if getattr(ch, 'position', None) == 'fighting':
                ch.position = 'standing'
    shadow.fighting = None
    if room is not None:
        try:
            await room.send_to_room(f"{shadow.short_desc} thins to nothing and is gone.")
        except Exception:
            pass


async def tick(world):
    """Once a combat round: lungs empty in the deep, the deep crushes, steam scalds, and pulled
    levers spring back when their time is up."""
    now = time.time()
    for p in list(getattr(world, 'players', {}).values()):
        room = getattr(p, 'room', None)
        if room is None or getattr(p, 'hp', 0) <= 0:
            continue
        await _scald(p, room, now)
        await _drown(p, room, now)
    for room, pulled_at in list(_pulled.items()):
        if now - pulled_at >= STEAM_BACK:
            await _throw(room, back=True)


async def _drown(p, room, now):
    rule = _deep(room)
    if rule is None:
        if getattr(p, '_breath', None) is not None:
            p._breath = None   # surfaced some other way (recall, a portal)
        return
    if breathes_water(p):
        p._breath = None
        return
    if now - getattr(p, '_breath_at', 0) < TICK_SECONDS:
        return
    p._breath_at = now
    c = _colors(p)
    mech = getattr(room, 'zone_mechanic', None) or {}
    if mech.get('type') == 'air_pocket':
        p._breath = AIR_TICKS
        return
    if getattr(p, '_breath', None) is None:
        p._breath = AIR_TICKS
    if mech.get('type') == 'pressure_damage':
        dmg = int(mech.get('damage_per_tick', 40))
        await p.send(f"{c['blue']}{mech.get('message') or 'The pressure crushes you!'} [{dmg}]{c['reset']}")
        if await p.take_damage(dmg, None, 'drowning'):
            return
    if p._breath > 0:
        p._breath -= 1
        if p._breath in (5, 3, 1):
            await p.send(f"{c['cyan']}Your chest tightens: air for {p._breath * TICK_SECONDS} more seconds.{c['reset']}")
        elif p._breath == 0:
            await p.send(f"{c['bright_red']}Your breath gives out!{c['reset']}")
        return
    dmg = int(rule.get('damage_per_tick', 25))
    await p.send(f"{c['bright_red']}{rule.get('message') or 'You are drowning!'} [{dmg}]{c['reset']}")
    await p.take_damage(dmg, None, 'drowning')


# ---------------------------------------------------------------- steam and levers
_steam = {}             # room vnum -> its steam is on (once a lever has moved it; else the room says)
_pulled = {}            # lever room -> when it was pulled (springs back after STEAM_BACK)


def steam_on(room) -> bool:
    mech = getattr(room, 'zone_mechanic', None) or {}
    if mech.get('type') != 'steam_damage':
        return False
    return _steam.get(room.vnum, mech.get('currently_active', True) is not False)


async def _scald(p, room, now):
    if not steam_on(room) or now - getattr(p, '_steam_at', 0) < TICK_SECONDS:
        return
    p._steam_at = now
    mech = room.zone_mechanic
    dmg = int(mech.get('damage_per_tick', 35))
    c = _colors(p)
    await p.send(f"{c['bright_red']}{mech.get('message') or 'Scalding steam burns you!'} [{dmg}]{c['reset']}")
    await p.take_damage(dmg, None, 'fire')


async def _throw(room, back=False):
    """Move a lever room's steam: from its steam_from rooms to its steam_to rooms (or back)."""
    mech = room.zone_mechanic
    zone_rooms = getattr(getattr(room, 'zone', None), 'rooms', None) or {}
    src, dst = [int(v) for v in mech.get('steam_from') or []], [int(v) for v in mech.get('steam_to') or []]
    off, on = (dst, src) if back else (src, dst)
    for v in off:
        _steam[v] = False
    for v in on:
        _steam[v] = True
    if back:
        _pulled.pop(room, None)
    else:
        _pulled[room] = time.time()
    for v in off + on:
        r = zone_rooms.get(v)
        if r is None:
            continue
        try:
            if v in on:
                await r.send_to_room("With a shriek of pipes, scalding steam floods in!")
            else:
                await r.send_to_room("The steam dies away with a long hiss, and the pipes tick as they cool.")
        except Exception:
            pass
    if back:
        try:
            await room.send_to_room("The lever's spring wins: it slams back with a clang as the pressure builds again.")
        except Exception:
            pass


def lever_pulled(room) -> bool:
    return room in _pulled


# ---------------------------------------------------------------- the citadel's secret ways
def seed(world):
    """When the world loads: a puzzle room's secret way is hidden until a hero finds it."""
    for room in getattr(world, 'rooms', {}).values():
        mech = getattr(room, 'zone_mechanic', None) or {}
        if mech.get('type') == 'puzzle_room' and isinstance(room.exits.get(mech.get('hidden_exit')), dict):
            room.exits[mech['hidden_exit']]['hidden'] = True


def _found(player, room, mech):
    return (room.vnum, mech.get('hidden_exit')) in (getattr(player, 'discovered_exits', None) or set())


SECRET_TEXT = {
    'mirror_door': "Your fingers pass through the glass of the one reflection with a door in it. The mirror "
                   "ripples, and a way {d} opens where no way was.",
    'shadow_tome': "The tome describes this very room, and a passage {d} you had not seen. As you read, the "
                   "words come true: the way {d} is there.",
}


async def act(player, verb, words) -> bool:
    """pull/read/touch on the room's own puzzle or lever. True when it was one."""
    room = getattr(player, 'room', None)
    mech = getattr(room, 'zone_mechanic', None) or {}
    said = {w.lower().strip('.,!') for w in (words or [])}
    c = _colors(player)
    if mech.get('type') == 'lever' and verb == 'pull' and said & LEVER_WORDS:
        back = lever_pulled(room)
        await player.send(f"{c['yellow']}You throw your weight on the lever. It "
                          f"{'swings back up' if back else 'grinds down'} with a heavy CLUNK.{c['reset']}")
        try:
            await room.send_to_room(f"{player.name} heaves on the lever.", exclude=[player])
        except Exception:
            pass
        await _throw(room, back=back)
        return True
    how = PUZZLE_ACTS.get(mech.get('puzzle')) if mech.get('type') == 'puzzle_room' else None
    if how and verb == how[0] and said & how[1]:
        d = mech.get('hidden_exit')
        if _found(player, room, mech):
            await player.send(f"{c['cyan']}You found its secret already: the way {d} is open to you.{c['reset']}")
            return True
        if getattr(player, 'discovered_exits', None) is None:
            player.discovered_exits = set()
        player.discovered_exits.add((room.vnum, d))
        text = SECRET_TEXT.get(mech.get('puzzle'), 'A hidden way opens {d}!').format(d=d)
        await player.send(f"{c['bright_green']}{text}{c['reset']}")
        return True
    return False

