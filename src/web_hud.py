"""What the 3D page (/play) draws for itself instead of reading it in the log.

A MUD tells its world in lines: the sun rises, a storm rolls in, you are hungry, you sit down, you
hold your breath, mail waits, an invasion has begun. /play shows these as part of its HUD (the sky
dial, the body meters, the room card, the alert chips); the line still comes, marked
msgkind.UI so the log keeps it dimmed.

Three small events on the map socket, each sent only when what it carries changed:

  vitals      {type, player: body_block}            one player's body, posture, needs, mail
  world_tick  {type, time, weather}                 the clock and the sky over the player's zone
  world_event {type, events: [events_block rows]}   what is going on across the world

build_map_payload (map_system.py) uses the same blocks, so a page starts with all of it.
"""
import json
import logging

logger = logging.getLogger(__name__)


def _web_map(world):
    return getattr(world, 'web_map', None)


def sky_block(player):
    """The clock and the sky over the player: {time: {...}, weather: {...}}."""
    world = getattr(player, 'world', None)
    gt = getattr(world, 'game_time', None)
    time_info = {}
    if gt is not None:
        time_info = {
            'hour': gt.hour,
            'period': gt.get_period(),
            'day': gt.day,
            'month': gt.month,
            'month_name': gt.get_month_name(),
            'year': gt.year,
            'season': gt.get_season(),
            'moon': gt.moon_phase(),
            'light': gt.get_light_level(),
        }
    weather_info = {}
    zone = getattr(getattr(player, 'room', None), 'zone', None)
    w = getattr(zone, 'weather', None)
    if w is not None:
        weather_info = {
            'sky': getattr(w, 'sky_condition', 'clear'),
            'temperature': getattr(w, 'temperature', 70),
            'wind': getattr(w, 'wind_speed', 0),
            'precipitation': getattr(w, 'precipitation', 'none'),
            'desc': w.get_weather_desc() if hasattr(w, 'get_weather_desc') else '',
        }
    return {'time': time_info, 'weather': weather_info}


def body_block(player):
    """What the page draws of the player's own body: the pools, the posture, hunger and thirst,
    a breath held under water, shadow corruption, unread mail."""
    breath = getattr(player, '_breath', None)
    if breath is not None:
        try:
            from zone_hazards import AIR_TICKS
        except Exception:
            AIR_TICKS = 10
        breath = {'left': int(breath), 'max': AIR_TICKS}
    hunger_of = getattr(player, 'get_hunger_condition', None)
    thirst_of = getattr(player, 'get_thirst_condition', None)
    return {
        'hp': getattr(player, 'hp', 0),
        'max_hp': getattr(player, 'max_hp', 1),
        'mana': getattr(player, 'mana', 0),
        'max_mana': getattr(player, 'max_mana', 1),
        'move': getattr(player, 'move', 0),
        'max_move': getattr(player, 'max_move', 1),
        'position': getattr(player, 'position', 'standing'),
        'hunger': getattr(player, 'hunger', 0),
        'max_hunger': getattr(player, 'max_hunger', 168),
        'hunger_state': hunger_of() if callable(hunger_of) else '',
        'thirst': getattr(player, 'thirst', 0),
        'max_thirst': getattr(player, 'max_thirst', 60),
        'thirst_state': thirst_of() if callable(thirst_of) else '',
        'breath': breath,
        'corruption': int(getattr(player, '_corruption', 0) or 0),
        'mail': int(getattr(player, 'mail_unread', 0) or 0),
    }


EVENT_LABELS = {
    'invasion': 'Invasion',
    'world_boss': 'World boss',
    'treasure_hunt': 'Treasure hunt',
    'double_xp': 'Double experience',
    'weather': 'Wild weather',
}


def events_block(world):
    """What is going on across the world (world_events.py): [{kind, label, where, left, wave, waves}]."""
    em = getattr(world, 'event_manager', None)
    out = []
    for e in list(getattr(em, 'active_events', None) or []):
        if not getattr(e, 'active', False):
            continue
        kind = getattr(e, 'event_type', 'unknown')
        label = EVENT_LABELS.get(kind, kind.replace('_', ' ').title())
        if kind == 'weather' and getattr(e, 'weather_type', None):
            label = str(e.weather_type).title()
        boss = getattr(e, 'boss', None)
        if kind == 'world_boss' and getattr(boss, 'name', None):
            label = boss.name
        row = {'kind': kind, 'label': label, 'where': getattr(e, 'zone_name', None),
               'left': int(getattr(e, 'time_remaining', 0) or 0)}
        if hasattr(e, 'max_waves'):
            row.update(wave=getattr(e, 'wave', 0), waves=e.max_waves)
        out.append(row)
    return out


def _sig(block):
    return json.dumps(block, sort_keys=True, default=str)


async def push_vitals(player, force=False):
    """Send the player's body to their page when it changed (or always, when forced: a posture
    asked for, a meal eaten, so the page answers at once)."""
    wm = _web_map(getattr(player, 'world', None))
    if wm is None or not wm.has_play(player):
        return
    block = body_block(player)
    sig = _sig(block)
    if not force and sig == getattr(player, '_hud_vitals', None):
        return
    player._hud_vitals = sig
    try:
        await wm.notify_event(player, {'type': 'vitals', 'player': block})
    except Exception as e:
        logger.debug(f"vitals push failed for {getattr(player, 'name', '?')}: {e}")


async def push_sky(world, zone=None):
    """Send the clock and sky to each /play page (only those standing in `zone`, when given)."""
    wm = _web_map(world)
    if wm is None:
        return
    for player in _play_players(world, wm):
        if zone is not None and getattr(getattr(player, 'room', None), 'zone', None) is not zone:
            continue
        try:
            await wm.notify_event(player, {'type': 'world_tick', **sky_block(player)})
        except Exception as e:
            logger.debug(f"sky push failed: {e}")


async def push_events(world):
    """Send what is going on across the world to every /play page, when it changed."""
    wm = _web_map(world)
    if wm is None:
        return
    rows = events_block(world)
    sig = _sig([{k: v for k, v in r.items() if k != 'left'} for r in rows])
    if sig == getattr(world, '_hud_events', None):
        return
    world._hud_events = sig
    for player in _play_players(world, wm):
        try:
            await wm.notify_event(player, {'type': 'world_event', 'events': rows})
        except Exception as e:
            logger.debug(f"events push failed: {e}")


def _play_players(world, wm):
    names = {c.player_name.lower() for c in list(getattr(wm, 'clients', ())) if getattr(c, 'player_name', None)}
    return [p for key, p in list(getattr(world, 'players', {}).items())
            if str(getattr(p, 'name', key)).lower() in names]


async def tick(world):
    """Every second (World.time_tick): each /play page hears of its player's body when it changed
    (a posture taken from anywhere, a breath, regeneration out of a fight), and of the world's
    events."""
    wm = _web_map(world)
    if wm is None or not getattr(wm, 'clients', None):
        return
    for player in _play_players(world, wm):
        await push_vitals(player)
    await push_events(world)
