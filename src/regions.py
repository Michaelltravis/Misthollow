"""The regions of the world (docs/world/WORLD_SPINE.md): which of the nine a zone belongs to.

world/regions.json (written by tools/world/regions_ledger.py) lists each region's name, the line
a traveller reads on entering it, its level band and its zones. /play is told a zone's region with
its map (map_system.build_zonemap), and says it on the banner and the map.

    regions.of(30)  ->  {'id': 'vale', 'name': 'The Lantern Vale', 'line': '...', 'levels': [1, 10]}
    regions.of(12)  ->  None        (the God Rooms are in no region)
"""
import json
import logging
import os

logger = logging.getLogger('Misthollow.Regions')

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'world', 'regions.json')
_by_zone = None


def load(path=None):
    """Read the regions afresh (None: the world's own file). A missing or broken file is no
    regions at all, and the game runs as it did before there were any."""
    global _by_zone
    _by_zone = {}
    try:
        with open(path or PATH, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        logger.warning(f'no regions: {e}')
        return _by_zone
    for r in data.get('regions') or []:
        try:
            pub = {'id': str(r['id']), 'name': str(r['name']), 'line': str(r.get('line') or ''),
                   'levels': [int(x) for x in (r.get('levels') or [])][:2]}
        except (KeyError, TypeError, ValueError):
            logger.warning(f'a region is malformed: {r!r:.80}')
            continue
        for z in r.get('zones') or []:
            try:
                z = int(z)
            except (TypeError, ValueError):
                continue
            if z in _by_zone:
                logger.warning(f'zone {z} is in two regions: {_by_zone[z]["id"]} and {pub["id"]} (the first stands)')
                continue
            _by_zone[z] = pub
    return _by_zone


def of(zone_num):
    """The region a zone is in (None: none)."""
    if _by_zone is None:
        load()
    try:
        return _by_zone.get(int(zone_num))
    except (TypeError, ValueError):
        return None


# ---- the bells at dusk ----
# "Garathorm's temple bells ring at dusk to call the lost home" (the title screen's own line, and the
# world's spine: the city stands because its lanterns burn and its bells ring every name at dusk).
BELLS_OUTDOORS = "The Temple's bells begin to ring across the Vale, a stroke for every name in the city, calling the lost home."
BELLS_INDOORS = "Through the walls you hear the Temple's bells begin to ring, a stroke for every name in the city."


def bells_line(room):
    """What someone in `room` hears as the bells ring at dusk (None: they are out of earshot: not in
    the Lantern Vale)."""
    zone = getattr(room, 'zone', None)
    r = of(getattr(zone, 'number', None)) if zone is not None else None
    if not r or r['id'] != 'vale':
        return None
    return BELLS_INDOORS if 'indoors' in (getattr(room, 'flags', None) or ()) else BELLS_OUTDOORS


async def dusk_bells(world):
    """Everyone in the Lantern Vale hears the bells: a line in the log, and in /play a bell (the
    ambient sound, soundtable.js `amb_bell`). Returns how many heard them."""
    heard = 0
    web_map = getattr(world, 'web_map', None)
    for player in list(getattr(world, 'players', {}).values()):
        line = bells_line(getattr(player, 'room', None))
        if not line:
            continue
        heard += 1
        c = player.config.COLORS
        await player.send(f"{c['bright_yellow']}{line}{c['reset']}")
        try:
            if web_map and web_map.has_play(player):
                await web_map.notify_event(player, {'type': 'ambient', 'text': '', 'sound': 'amb_bell', 'key': 'bells'})
        except Exception:
            logger.exception('dusk bells: the sound')
    return heard
