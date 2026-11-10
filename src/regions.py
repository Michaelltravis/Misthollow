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


# ---- what a zone is called ----
NAMES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'world', 'zone_names.json')
_names = None


def zone_name(zone_num, name):
    """A zone's name in play: the one world/zone_names.json gives it, else its own (`name`)."""
    global _names
    if _names is None:
        _names = {}
        try:
            with open(NAMES_PATH, encoding='utf-8') as f:
                _names = {int(k): str(v) for k, v in (json.load(f).get('names') or {}).items() if str(v).strip()}
        except (OSError, ValueError) as e:
            logger.warning(f'no zone names: {e}')
    try:
        return _names.get(int(zone_num), name)
    except (TypeError, ValueError):
        return name


# ---- a zone lifted to its region's levels ----
LEVELS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'world', 'zone_levels.json')


def new_level(level, rule):
    """A creature's level under a zone's rule {add, lo, hi}: `add` more, held within [lo, hi]; one
    already above the band keeps its own."""
    level = int(level or 1)
    lo, hi = int(rule.get('lo', 1)), int(rule.get('hi', 999))
    if level >= hi:
        return level
    return max(lo, min(hi, level + int(rule.get('add', 0))))


def relevel(world, path=None):
    """Lift the creatures of the zones in world/zone_levels.json (run once as the world loads, after
    the population is applied and before anything spawns). Returns {zone: creatures lifted}."""
    try:
        with open(path or LEVELS_PATH, encoding='utf-8') as f:
            rules = {int(k): v for k, v in (json.load(f).get('zones') or {}).items()}
    except (OSError, ValueError) as e:
        logger.warning(f'no zone levels: {e}')
        return {}
    import population
    done = {}
    for znum, rule in rules.items():
        zone = world.zones.get(znum)
        if zone is None:
            continue
        vnums = set()
        for room in getattr(zone, 'rooms', {}).values():
            for reset in getattr(room, 'mob_resets', None) or []:
                v = reset.get('vnum') if isinstance(reset, dict) else reset
                if v is not None:
                    vnums.add(int(v))
        n = 0
        for v in sorted(vnums):
            proto = world.mob_prototypes.get(v)
            if not proto or proto.get('_releveled'):
                continue
            old = int(proto.get('level') or 1)
            new = new_level(old, rule)
            if new == old:
                continue
            want = population.numbers(new, proto.get('rank'))
            have_hp = proto.get('max_hp') or population._avg(proto.get('hp_dice')) or 0
            proto['level'] = new
            if want['max_hp'] > have_hp:
                proto['hp_dice'] = want['hp_dice']
                if proto.get('max_hp'):
                    proto['max_hp'] = proto['hp'] = want['max_hp']
            if population._avg(want['damage_dice']) > (population._avg(proto.get('damage_dice')) or 0):
                proto['damage_dice'] = want['damage_dice']
            for k in ('hitroll', 'damroll'):
                proto[k] = max(int(proto.get(k) or 0), want[k])
            proto['exp'] = max(int(proto.get('exp') or 0), int((proto.get('exp') or want['exp']) * new / max(1, old)))
            proto['gold'] = max(int(proto.get('gold') or 0), want['gold'])
            proto['_releveled'] = old
            n += 1
        done[znum] = n
    return done


# ---- words of another author's world ----
WORDS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'world', 'words.json')


def _replacer(words):
    import re
    if not words:
        return None
    table = {k.lower(): v for k, v in words.items()}
    pat = re.compile(r'\b(' + '|'.join(re.escape(k) for k in sorted(words, key=len, reverse=True)) + r')\b', re.I)

    def one(m):
        new = table[m.group(0).lower()]
        return new[:1].upper() + new[1:] if m.group(0)[:1].isupper() else new
    return lambda text: pat.sub(one, text) if isinstance(text, str) and pat.search(text) else text


def reword(value, fix):
    """`value` (a string, or a dict or list of them, however deep) with every word replaced; dicts and
    lists are changed in place and returned."""
    if isinstance(value, str):
        return fix(value)
    if isinstance(value, dict):
        for k in list(value):
            value[k] = reword(value[k], fix)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            value[i] = reword(v, fix)
    return value


def apply_words(world, path=None):
    """Replace the words in world/words.json in every room (its name, its description, what can be
    looked at in it), creature and thing (run once as the world loads, before anything spawns).
    Returns how many strings changed."""
    try:
        with open(path or WORDS_PATH, encoding='utf-8') as f:
            words = json.load(f).get('words') or {}
    except (OSError, ValueError) as e:
        logger.warning(f'no words: {e}')
        return 0
    fix = _replacer(words)
    if fix is None:
        return 0
    changed = 0

    def counted(text):
        nonlocal changed
        new = fix(text)
        if new != text:
            changed += 1
        return new
    for room in getattr(world, 'rooms', {}).values():
        room.name = counted(room.name)
        room.description = counted(getattr(room, 'description', '') or '')
        if isinstance(getattr(room, 'extra_descs', None), dict):
            reword(room.extra_descs, counted)
    for table in (getattr(world, 'mob_prototypes', {}), getattr(world, 'obj_prototypes', {})):
        for proto in table.values():
            if isinstance(proto, dict):
                reword(proto, counted)
    return changed
