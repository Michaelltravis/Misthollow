"""What a room looks like in 3D (Push 33): its *look*, apart from its sector.

A room's sector decides how it plays (moving, water, darkness); its look is only how the 3D client
draws it. The two came apart because most of the world's caves, sewers and deserts were typed
'inside', 'mountain' or 'field' long ago, so a cave drew as a tiled hall. Here each room gets a
look once at load, the first rule that answers:

  1. what is stated: a `look` in the room's zone data (the build-out and new zones write one),
     or world/looks.json (hand overrides by room or by zone, each with its reason);
  2. its name, by the ordered word table LOOK_WORDS; or, for a room typed indoors whose name is
     open country (The Plains, A Mountain Trail), that country (OPEN_COUNTRY);
  3. its description, by the same table (two mentions, or one telling phrase);
  4. its zone's default in world/looks.json;
  5. its neighbours: a room with no word of its own takes the look most of its looked
     neighbours in the same zone share, a few steps out (SPREAD: how far, and through which
     sectors). Underground looks spread only through enclosed rooms that don't read as a
     building's (a tavern, a kitchen...); outdoor looks only through open country;
  6. its zone, when the zone is plainly underground: a third of its enclosed rooms have
     underground looks by now (the most common at least ZONE_MIN), and the rest take that one.

Anything left keeps its sector as its look. Never saved but a stated one (Room.to_dict).
"""
import json
import logging
import os
import re
from collections import Counter

logger = logging.getLogger('Misthollow')

LOOKS = ('cave', 'mine', 'crypt', 'sewer', 'dungeon', 'desert', 'snow', 'shore', 'volcanic', 'swamp', 'web', 'castle',
         'necropolis', 'stones', 'village', 'camp', 'garden', 'ruins', 'terrace', 'ice_cave', 'lava_cave',
         # a drow city in its cavern (the Drow City, zone 51: world/looks.json underground_zones);
         # the client tells its streets, houses, tunnels, bridges and temple apart by their names
         'drow',
         # the Clockwork Foundry (zone 248): steel, pipes, gears and furnaces, not the cave its
         # tunnels' words read as (world/looks.json underground_zones; the art audit)
         'foundry',
         # the Chessboard of Garathorm (zone 36): squares of white marble and black obsidian, not the
         # market streets its old 'city' sector drew (world/looks.json zones; terrain-chess.js)
         'chessboard')
UNDERGROUND = {'cave', 'mine', 'crypt', 'sewer', 'dungeon', 'ice_cave', 'lava_cave'}
# a zone look that holds for every room of its zone, whatever a room's own words say
ZONE_WIDE = {'drow', 'foundry'}
# a hand override (world/looks.json) may also keep a room as plain country or a plain room
OVERRIDE_LOOKS = LOOKS + ('field', 'forest', 'hills', 'mountain', 'city', 'inside',
                          # (a room under the water its words say it is: Underwater In The Sewer)
                          'underwater')
OUTDOOR = {'desert', 'snow', 'volcanic', 'swamp', 'web', 'stones', 'village', 'camp', 'garden', 'ruins', 'terrace'}   # (a shore is an edge: it doesn't spread)
# a sacred ring or a field of standing stones (the Stone Circle): turf and flagstones under the sky,
# a ring of standing stones for walls. Old imports typed such places 'city' (paved, walled), so a
# room drawn as a town whose words name standing stones and no town at all is one of these
STONES_RE = re.compile(r'\b(standing stones?|stone circle|stone ring|ring of (?:grey |great |tall )?stones|monoliths?|'
                       r'menhirs?|megaliths?|dolmens?|the stones (?:lean|crowd|seem|here))\b', re.I)
TOWN_RE = re.compile(r'\b(streets?|houses?|homes?|cottages?|shops?|stores?|markets?|inns?|taverns?|alleys?|guilds?|bakery|'
                     r'smithy|blacksmiths?|merchants?|stalls?|townsfolk|citizens?|city walls?|warehouses?|shopkeepers?|bank)\b', re.I)

# ---- a room typed 'city' that is no town (Phase 2, docs/world/room_visuals.md): an old import
# typed villages, camps, gardens, ruins and plain roads 'city', and they were drawn as market
# streets. Its words say what it is; first match wins. Ruins, gardens and a road of bones say so
# plainly even where a ruined city's houses are named; the rest only where no town is.
TOWNLESS = [
    ('necropolis', r'\b(?:road|path|walkway|pavements?|way) (?:laid )?of (?:bones?|skulls?)|walls? built (?:entirely )?of (?:stacked )?skulls|bone pavements?\b', 1, True),
    ('ruins', r'\b(ruins?|ruined|crumbling|crumbled|broken columns?|collapsed|toppled|shattered (?:walls?|columns?)|fallen (?:columns?|masonry)|'
              r'deserted city|once (?:lush|beautiful|grand|proud)|mass destruction)\b', 2, True),
    ('garden', r'\b(gardens?|flower ?beds?|beds of (?:\w+ )?(?:roses|lilies|lavender|herbs|flowers)|lawns?|hedges?|orchards?|'
               r'beehives?|rose ?bushes|topiary|\bpark\b)\b', 2, False),
    ('camp', r'\b(camps?|campsite|encampment|tents?|fire ?pits?|campfires?|palisades?|bedrolls?)\b', 2, False),
    ('village', r'\b(village|hamlet|huts?|hovels?|shacks?|thatch(?:ed)?|wattle|byres?|farmhouse|farmyard|palms?|nets? (?:hung|drying))\b', 2, False),
    ('desert', r'\b(desert|dunes?|sands)\b', 2, False),
    ('field', r'\b(fields?|countryside|farmland|meadows?|pastures?|hedgerows?|ditches)\b', 2, False),
]
TOWNLESS_RES = [(look, re.compile(pat, re.I), n, plain) for look, pat, n, plain in TOWNLESS]
# a building typed 'city' (an import gave a town's huts, quarters, classrooms and washrooms the
# town's sector): drawn as a room, not a street
CITY_BUILDING = re.compile(r'\b(quarters|huts?|den|sheds?|workshop|prison|class ?rooms?|washroom|surgery|newsroom|outhouse|'
                           r'sanctuary|sanctum|hideaway|rooms?|halls?|chambers?|corridors?|office|wing|cellar|alcove|kitchen|'
                           r'parlou?r|library|study|lodge|barn|stables?|barracks|workshops?|cartographers|dining area|rest)\b', re.I)
NOT_A_BUILDING = re.compile(r'\b(grounds|path|road|courtyard|yard|garden|decks?|platform|porch|balcony|walk|pens|nest|perch)\b', re.I)
OPEN_AIR = re.compile(r'\b(open air|open sky|under the sky|open to (?:the|a) [\w-]*\s*sky|no ceiling)\b', re.I)


def city_building(room):
    """'inside' or 'cave' for a city-typed room that is plainly a building's room or a den in the
    rock; None otherwise."""
    name, desc = room.name or '', room.description or ''
    if (not CITY_BUILDING.search(name) or NOT_A_BUILDING.search(name) or OUTSIDE_RE.search(name)
            or STREET_RE.search(name) or OPEN_AIR.search(desc)):
        return None
    if not (reads_indoors(desc) or ROOFED.search(desc) or len(BUILDING_CUES.findall(desc)) >= 2):
        return None
    if re.search(r'\b(living rock|hollowed out of the rock|hacked out of|cut (?:into|from) the rock|in the rock)\b', desc, re.I):
        return 'cave'
    return 'inside'


# a town's paving, quays and walls say town as plainly as its shops
TOWN_MORE = re.compile(r'\b(cobble\w*|paving|paved|quays?|town walls?|towpath|avenue)\b', re.I)
ROAD_NAME = re.compile(r'\b(road|street|avenue|lane)\b', re.I)


def townless(room):
    """The look a city-typed room's words give it when they describe no town (None: a town, or
    nothing said). A room named for it is it ("The Flower Garden", "A Ruined House", but not
    "Park Road", a street); otherwise its description must say it more than once, and, but for
    ruins and a road of bones, say nothing of a town."""
    name = room.name or ''
    text = f'{name}. {room.description or ""}'
    town = TOWN_RE.search(text) or TOWN_MORE.search(text)
    for look, rx, need, plain in TOWNLESS_RES:
        if look == 'garden' and ROAD_NAME.search(name):
            continue                # (a road past a park or through a village of gardens)
        if rx.search(name):
            return look
        if town and not plain:
            continue
        if len(rx.findall(text)) >= need:
            return look
    return None

# first match wins: the specific before the general
LOOK_WORDS = [
    ('sewer', r'\b(sewers?|drains?|cisterns?|culverts?)\b'),
    ('crypt', r'\b(crypts?|tombs?|catacombs?|ossuar(?:y|ies)|sepulch\w*|sarcophag\w*|barrows?|burial chambers?)\b'),
    ('mine', r'\b(mines?|mineshafts?|shafts?|ore|mining|quarry|lode)\b'),
    ('cave', r'\b(caves?|caverns?|cavernous|grottos?|grottoes|stalactites?|stalagmites?|crawlways?|underground|subterranean)\b'),
    ('dungeon', r'\b(dungeons?|oubliettes?|torture chambers?|prison cells?|cell ?blocks?)\b'),
    # a spider's lair: webbed trees and tunnels (Arachnos, the spider queens' dens)
    ('web', r'\b(webs?|webbed|webby|webbing|cobwebs?|cocoon\w*|egg ?sacs?|spider ?silk)\b'),
    ('volcanic', r'\b(lava|magma|volcan\w*|molten|caldera|ashen|ashlands?|cinders?|obsidian)\b'),
    ('desert', r'\b(deserts?|dunes?|sands|oasis|wastes of sand)\b'),
    ('snow', r'\b(snow\w*|frozen|glaciers?|glacial|tundra|icy|ice|frost\w*|winterlands?|blizzard)\b'),
    ('swamp', r'\b(swamps?|bogs?|marsh\w*|mires?|fens?|quagmire|bayou)\b'),
    ('shore', r'\b(beach(?:es)?|shores?|shoreline|coasts?|coastline|strand)\b'),
]
LOOK_RES = [(look, re.compile(pat, re.I)) for look, pat in LOOK_WORDS]
# one of these in a description is enough
TELLING = {
    'cave': re.compile(r'\b(in(?:side)? (?:a|the|this) (?:cave|cavern|grotto)|cave walls?|cavern walls?|'
                       r'stalactites|rough[- ]hewn rock|natural tunnel)\b', re.I),
    'sewer': re.compile(r'\b(sewage|sewer water|in the sewers?)\b', re.I),
    'mine': re.compile(r'\b(mine cart|ore cart|mining tunnel|support beams|pick ?axes? marks)\b', re.I),
    'crypt': re.compile(r'\b(burial niches?|coffins? line|stone coffins?|sarcophagi)\b', re.I),
    'web': re.compile(r'\b(coated with (?:cob)?webs?|covered in (?:cob)?webs?|thick (?:cob)?webs?|webbed (?:remains|bodies|corpses)|'
                      r'strands? of (?:web|silk)|spider ?silk)\b', re.I),
}
# a room that reads as a building's never takes an underground look from its neighbours
INTERIOR_RE = re.compile(
    r'\b(temple|church|chapel|cathedral|shrine|taverna?|inn|pub|bar|alehouse|bank|library|study|'
    r'bedroom|bed ?chamber|quarters|dormitory|throne|palace|shop|store|market|merchant|smithy|'
    r'guild|barracks|house|home|cottage|kitchen|parlou?r|dining|living room|stable|great hall|lore-hall|'
    r'belfry|bell ?tower|sacristy|vestry|nave|pews?|organ|choir|rose window|vestments|'
    # (a town hall's and a lodge's rooms: the art audit found them drawn as dungeons)
    r'office|foyer|council|committee|waiting room|closet|warehouse|hearth|lodge|reading room|common room)\b', re.I)

ENCLOSED_SECTORS = {'inside', 'cave', 'dungeon', 'underground'}
WATER_SECTORS = {'water_swim', 'water_noswim', 'underwater'}
# outdoor looks found only in a description need an outdoor room
OUTDOOR_FROM_DESC = {'field', 'hills', 'mountain', 'forest', 'desert', 'swamp', 'road'}
# how far each look spreads to rooms with no word of their own, and through which sectors
SPREAD = {
    'cave': (3, ENCLOSED_SECTORS), 'mine': (3, ENCLOSED_SECTORS),
    'sewer': (3, ENCLOSED_SECTORS | {'forest', 'mountain', 'hills', 'field'}),   # the old sewer was typed anyhow
    'dungeon': (2, ENCLOSED_SECTORS), 'crypt': (1, ENCLOSED_SECTORS),
    'desert': (3, {'field', 'hills', 'mountain', 'desert'}), 'volcanic': (3, {'field', 'hills', 'mountain'}),
    'stones': (2, {'field', 'hills', 'city'}),
    # a village's or a camp's or a ruin's rooms with no word of their own (a crossing of paths
    # between the huts), one step and never onto a town street (classify checks the words)
    'village': (1, {'city'}), 'camp': (1, {'city', 'field'}), 'ruins': (1, {'city'}),
    'snow': (3, {'field', 'hills', 'mountain', 'forest'}), 'swamp': (2, {'field', 'swamp'}),
    'web': (3, {'field', 'hills', 'forest', 'city', 'mountain'}),
}

ZONE_MIN = 5

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OVERRIDES = os.path.join(ROOT, 'world', 'looks.json')


def words_look(text):
    """The first look a piece of text names, or None."""
    for look, rx in LOOK_RES:
        if rx.search(text or ''):
            return look
    return None


def description_look(text):
    """A look a description gives: two mentions of its words, or one telling phrase."""
    text = text or ''
    for look, rx in TELLING.items():
        if rx.search(text):
            return look
    for look, rx in LOOK_RES:
        if len(rx.findall(text)) >= 2:
            return look
    return None


def load_overrides(path=OVERRIDES):
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return {'rooms': {}, 'zones': {}, 'underground': {}, 'interiors': {}, 'tones': {}}
    return {'rooms': {int(k): v for k, v in (data.get('rooms') or {}).items()},
            'zones': {int(k): v for k, v in (data.get('zones') or {}).items()},
            'underground': {int(k): v for k, v in (data.get('underground_zones') or {}).items()},
            # the style a zone's indoor rooms are drawn in (castle, arcane, holy...: zone_tone.py)
            'interiors': {int(k): v for k, v in (data.get('interiors') or {}).items()},
            # a zone's stone and light stated by hand, over what zone_tone.py reads from its words
            'tones': {int(k): v for k, v in (data.get('tones') or {}).items()}}


def _zone(room):
    return getattr(getattr(room, 'zone', None), 'number', None)


def _neighbours(room, rooms):
    for ex in (getattr(room, 'exits', None) or {}).values():
        to = ex.get('to_room') if isinstance(ex, dict) else ex
        try:
            other = rooms.get(int(to))
        except (TypeError, ValueError):
            other = None
        if other is not None and other is not room:
            yield other


FOREST_WORDS = r'\b(forests?|forrests?|woods|woodlands?|groves?|copse|thickets?|jungle|wildwood|greenwood|glades?|clearing|trees?|treetops?|branch(?:es)?)\b'
FOREST_RE = re.compile(FOREST_WORDS, re.I)
# a description plainly among trees: three or more of these (a field or a road through woods)
TREE_CUES = re.compile(r'\b(trees?|branch(?:es)?|boughs?|limbs?|canopy|foliage|trunks?|undergrowth|forest|woods|leaves|treetops?)\b', re.I)
CITY_CUES = re.compile(r'\b(streets?|shops?|buildings?|houses?|market|plaza|alley|cobble\w*|town|city)\b', re.I)
TUNNEL_RE = re.compile(r'\b(tunnels?|burrows?)\b', re.I)
TUNNEL_WORDS = re.compile(r'\b(tunnels?|passages?)\b', re.I)
# a description plainly underground (The Maze, The Hole in the Mountain Range's tunnels, typed forest)
CAVE_CUES = re.compile(r'\b(tunnels?|passages?|caverns?|caves?|alcoves?|ceiling)\b', re.I)
# a description plainly inside a building: three or more of these (the build-out wrote rooms an
# atlas called "The Plains" as a village's alehouse and chapel)
INDOOR_CUES = re.compile(r'\b(walls?|ceiling|floor(?:boards?)?|doors?|doorways?|hearth|tables?|benches|chambers?|halls?|roof|'
                         r'beams|rafters|shel(?:f|ves)|altar|pews?|windows?|vault(?:ed)?|furniture|counters?|bunks?)\b', re.I)
# a road through a building says so: under a roof, a vault, a gallery (not a road between houses)
ROOFED = re.compile(r'\b(roof(?:ed)?|ceiling|vault(?:ed)?|gallery|covered|beneath (?:the|a|its)|undercroft|'
                    r'through (?:a|an|the) (?:[\w-]+ ){0,3}(?:barn|hall|house|inn|waystation|tollhouse))\b', re.I)
# a name that puts the room outside a building ("In Front Of The Stable", "Before The Watchtower")
OUTSIDE_RE = re.compile(r'^\s*(in front of|before|outside|near|beside|behind|by)\b', re.I)
# a field-typed room whose name is a building's (a guardhouse, the Ambassadors Halls)
BUILDING_RE = re.compile(r'\b(guardhouse|guard ?rooms?|halls|quarters)\b', re.I)


# furniture and fittings only a building has (caves have walls, ceilings and floors too)
BUILDING_CUES = re.compile(r'\b(hearths?|tables?|benches|beds?|bunks?|shel(?:f|ves)|counters?|rafters|thatch|windows?|'
                           r'furniture|pews?|chimney|plaster|carpets?|rugs?|stalls?|mangers?|cupboards?|kitchen)\b', re.I)


def reads_building(text):
    """Whether a description is furnished like a building (a lodge, a watchtower's chamber)."""
    return len(BUILDING_CUES.findall(text or '')) >= 2


def reads_indoors(text):
    """Whether a description plainly puts its room inside a building."""
    return len(INDOOR_CUES.findall(text or '')) >= 3
# a castle's outside (its yard, walls and gate) is drawn as one: curtain walls with merlons, towers
# at the corners, banners; its halls and chambers stay rooms (INTERIOR_RE)
CASTLE_RE = re.compile(r'\b(castle|keep|fortress|citadel|stronghold|bailey|battlements?|ramparts?|gatehouse|'
                       r'portcullis|drawbridge|barbican|parapets?|wall ?walk|outer ward|inner ward|bastion)\b', re.I)
# a courtyard or a turret is a castle's only when the castle is named in its words or its zone's
# (a temple's courtyard, a mage's garden court stay as they are)
CASTLE_WEAK = re.compile(r'\b(courtyard|turrets?)\b', re.I)
CAVERN_RE = re.compile(r'\b(caverns?|caves?|shaft)\b', re.I)
ROCK_CUES = re.compile(r'\b(caves?|caverns?|rock|stone|earth|dark(?:ness)?|damp|underground|walls?)\b', re.I)
MOUNTAIN_WORDS = (r'\b(mountains?|mountainside|peaks?|summit|cliffs?|cliff\'s edge|crags?|ledges?|ravine|gorge|'
                  r'canyon|scree|slopes?|rocky|boulders?|the pass|mountain pass|precipice)\b')
MOUNTAIN_RE = re.compile(MOUNTAIN_WORDS, re.I)
# an indoor-typed room takes only the plain words (a ledge or a slope indoors is likely underground)
MOUNTAIN_STRONG = r'\b(mountains?|mountainside|peaks?|summit|cliffs?|cliff\'s edge)\b'

# a room typed as indoors whose name is open country ("The Plains", "A Mountain Trail"): drawn as
# the country it names, not as a furnished house (sector-named looks: field, forest, hills,
# mountain; a road in a town is a street)
OPEN_COUNTRY = [
    ('mountain', MOUNTAIN_STRONG),
    ('hills', r'\b(hills?|hillside|highlands?|downs|ridges?|foothills)\b'),
    ('forest', FOREST_WORDS),
    ('field', r'\b(plains?|meadows?|fields?|grasslands?|prairie|steppes?|pastures?|farmland|heath|moors?|savannah?)\b'),
    ('road', r'\b(roads?|trails?|paths?|highway|crossroads|track)\b'),
]
OPEN_RES = [(look, re.compile(pat, re.I)) for look, pat in OPEN_COUNTRY]
STREET_RE = re.compile(r'\b(street|avenue|lane|square|alley|plaza|market|wall road|gate)\b', re.I)
INDOOR_SECTORS = {'inside', 'dungeon'}


def open_country(room):
    """The open country an indoor-typed room's name says it is (None: it doesn't, or it reads as a
    building: a tavern on a mountain road is still a tavern). A forest is a forest whatever the
    room was typed (a wood on a hillside, in a town's park), but never under water."""
    sector = getattr(room, 'sector_type', '') or 'inside'
    if sector not in INDOOR_SECTORS:
        name = room.name or ''
        if sector in WATER_SECTORS or INTERIOR_RE.search(name):
            return None
        if sector != 'forest' and FOREST_RE.search(name):
            return 'forest'
        # mountain country typed as field, hills or forest (a mountain road, a ledge above a
        # ravine); a town's mountain wall stays in town
        if sector not in ('mountain', 'city') and MOUNTAIN_RE.search(name):
            return 'mountain'
        return None
    name = room.name or ''
    # an indoor room whose own description is underground (a ledge in a cavern) is underground
    if description_look(room.description) in UNDERGROUND:
        return None
    # and one whose description is plainly a building's (the village alehouse the atlas called
    # "The Plains", the customs hall the Trade Road runs through) is that building; a road through
    # one only when it runs under a roof, and through a tunnel it is a cave; a street stays a street
    desc = room.description or ''
    road_name = dict(OPEN_RES)['road'].search(name)
    if road_name and len(TUNNEL_WORDS.findall(desc)) >= 2 and not STREET_RE.search(name):
        return 'cave'
    if reads_indoors(desc) and not STREET_RE.search(name) and (not road_name or ROOFED.search(desc)):
        return None
    # a road names where it goes ("The Path By The Cathedral"): still a road (through a forest, a
    # forest); anything else that names a building is that building
    road = dict(OPEN_RES)['road'].search(name)
    if road and not re.search(r'\b(tavern|inn|shop|store)\b', name, re.I):
        return ('forest' if FOREST_RE.search(name) else 'mountain' if re.search(MOUNTAIN_STRONG, name, re.I)
                else 'city' if STREET_RE.search(name) else 'field')
    if INTERIOR_RE.search(name):
        return None
    for look, rx in OPEN_RES:
        if rx.search(name):
            if look == 'road':
                return 'city' if STREET_RE.search(name) else 'field'
            return look
    return None


def _castle(room, sector, name, desc):
    """A castle's yard, walls or gate by its name (not a street toward the keep, not a hall in it,
    not a cavern called a castle's way)."""
    if INTERIOR_RE.search(name) or CAVERN_RE.search(desc) or (sector == 'city' and STREET_RE.search(name)):
        return False
    if CASTLE_RE.search(name):
        return True
    zone = getattr(getattr(room, 'zone', None), 'name', '') or ''
    return bool(CASTLE_WEAK.search(name) and (CASTLE_RE.search(desc) or CASTLE_RE.search(zone)))


def _own_look(room):
    """(look, why) from the room's own words, or (None, None)."""
    sector = getattr(room, 'sector_type', '') or ''
    if sector in WATER_SECTORS:
        return None, None
    name, desc = room.name or '', room.description or ''
    # a tunnel through rock is a cave, whatever it was typed (the Mountain Range's were 'forest')
    if (TUNNEL_RE.search(name) and (ROCK_CUES.search(desc) or len(TUNNEL_WORDS.findall(desc)) >= 2)
            and sector != 'city' and not INTERIOR_RE.search(name)):
        return 'cave', 'name'
    # and so is a room typed as open country whose description is all tunnel and cavern
    if (sector in ('forest', 'hills', 'field') and len(CAVE_CUES.findall(desc)) >= 3
            and re.search(r'\b(tunnels?|caverns?|caves?)\b', desc, re.I) and not FOREST_RE.search(name)
            and not reads_building(desc)):
        return 'cave', 'description'
    # a building typed as open country (a guardhouse, the guards' quarters) is a building
    if (sector in ('field', 'hills') and (INTERIOR_RE.search(name) or BUILDING_RE.search(name))
            and not OUTSIDE_RE.search(name) and reads_indoors(desc)):
        return 'inside', 'name'
    look = words_look(room.name)
    why = 'name'
    if not look and _castle(room, sector, name, desc):
        return 'castle', 'name'
    if not look:
        look = open_country(room)
        # a forest or a mountain stays one whatever its description says, unless it is snowbound
        if look in ('forest', 'mountain') and description_look(room.description) == 'snow':
            look = 'snow'          # (still read from its name: a snowbound wood)
    # a wood hung with webs (the Great Forest of MiNar, the trees of Haon-Dor's spiders)
    if look in ('forest', 'field', None) and len(dict(LOOK_RES)['web'].findall(desc)) >= 2 and sector not in INDOOR_SECTORS:
        return 'web', 'description'
    if not look and sector == 'forest' and FOREST_RE.search(room.name or ''):
        # a forest typed as one and named as one: no description turns it into a swamp or a shore
        d = description_look(room.description)
        return (d, 'description') if d == 'snow' else ('forest', 'name')
    if not look:
        look, why = description_look(room.description), 'description'
    if not look:
        return None, None
    # (a city-typed room named a cave is a cave: the Golden Cave of the Mountain Range)
    if sector == 'city' and look not in ('sewer', 'forest', 'web') and not (look == 'cave' and why == 'name'):
        return None, None
    # an outdoor look found only in a description keeps an enclosed room enclosed
    if look in OUTDOOR | {'shore'} and why == 'description' and sector not in OUTDOOR_FROM_DESC:
        return None, None
    # and an underground one found only in a description, an enclosed room
    if look in UNDERGROUND and why == 'description' and sector not in ENCLOSED_SECTORS:
        return None, None
    return look, why


def _trees(room):
    """Open country (or a 'city' road) that its description plainly puts among trees."""
    sector = getattr(room, 'sector_type', '') or ''
    if sector not in ('field', 'hills', 'city') or INTERIOR_RE.search(room.name or ''):
        return False
    d = room.description or ''
    if sector == 'city' and (STREET_RE.search(room.name or '') or len(CITY_CUES.findall(d)) >= 2):
        return False
    return len(TREE_CUES.findall(d)) >= 3


def _fits(room, look):
    """Whether a look that isn't the room's own (a zone's) suits it: an underground one an
    enclosed room that doesn't read as a building's, an outdoor one open country."""
    sector = getattr(room, 'sector_type', '') or 'inside'
    if look in UNDERGROUND:
        return sector in ENCLOSED_SECTORS and not INTERIOR_RE.search(f'{room.name} {room.description}')
    if look == 'chessboard':
        return sector == 'city'          # (the board's squares and its gate, not the treasuries under it)
    if look in ('stones', 'village', 'camp', 'garden', 'ruins', 'terrace'):
        return sector in OUTDOOR_FROM_DESC or (sector == 'city' and not TOWN_RE.search(f'{room.name} {room.description}'))
    return sector in OUTDOOR_FROM_DESC


# ---------------------------------------------------------------- filler that contradicts the look
# An old import gave short rooms a couple of sentences from their sector ("Bird calls echo through
# the canopy." in a forest room, "The cobblestones are worn smooth by countless feet." in a city
# one). Where the look disagrees with the sector (a sewer pipe typed 'city', a cave typed 'field')
# they say the wrong thing: they go, and an underground room gets two lines of its own place.
FILLER = {
    'city': ('The smell of smoke and humanity hangs in the air.', 'Vendors and pedestrians bustle past.',
             'The cobblestones are worn smooth by countless feet.', 'Buildings crowd together on all sides.',
             'The sounds of city life echo around.', 'Worn flagstones run between weathered walls, swept by passing feet.',
             'Voices and the clatter of carts carry from somewhere nearby.', 'Lantern hooks and faded signboards hang over the street.',
             'Shuttered windows and old doorways crowd in on either hand.', 'The paving is uneven here, patched with newer stone.'),
    'forest': ('The scent of pine and earth fills the air.', 'Branches intertwine overhead, filtering the light.',
               'Bird calls echo through the canopy.', 'Ancient trees rise on all sides.',
               'The forest floor is carpeted with fallen leaves.'),
    'field': ('The air is fresh and clean.', 'The ground is soft underfoot.', 'Tall grass sways in a gentle breeze.',
              'Wildflowers dot the landscape.', 'The open sky stretches overhead.'),
    'mountain': ('Bare rock dominates the landscape.', 'Snow clings to shadowed crevices.', 'The path is steep and treacherous.',
                 'The air is thin and cold at this altitude.', 'The wind howls around exposed peaks.'),
    'hills': ('Rocks jut from the grassy slopes.',),
    'water': ('The depths are dark and unknowable.', 'The roar of water fills your ears.'),
    # (the surface's: not under the water, under_water)
    'surface': ('Waves crash and foam relentlessly.', 'Spray mists the air around.'),
}
FILLER_FITS = {'city': {'city', 'castle'}, 'forest': {'forest', 'darkforest', 'web', 'swamp'},
               'field': {'field', 'hills', 'shore', 'village', 'camp', 'garden'}, 'mountain': {'mountain', 'hills', 'snow'},
               'hills': {'hills', 'field', 'mountain'}, 'water': WATER_SECTORS | {'shore'},
               'surface': {'water_swim', 'water_noswim', 'shore'}}
OWN_LINES = {
    'sewer': ('Foul water trickles along a channel down the middle of the floor.', 'Pipes sweat and drip somewhere in the dark.',
              'The stench of rot and wet stone hangs heavy in the air.', 'Slime streaks the curved brick walls.',
              'Puddles of black water gather in the cracked floor.', 'Rats scurry away from the light.'),
    'cave': ('Water drips from the rock overhead.', 'The air is cold and smells of wet stone.',
             'The rock walls glisten with damp.', 'Your footsteps echo away into the dark.'),
    'mine': ('Old timbers prop up the rock overhead.', 'Rusted rails run along the floor.', 'Rock dust hangs in the still air.'),
    'crypt': ('The air smells of dust and old death.', 'Niches in the walls hold crumbling bones.', 'The silence is deep and cold.'),
    'dungeon': ('Iron rings are set into the damp walls.', 'The stone floor is slick and cold.', 'Somewhere a chain rattles.'),
    'chessboard': ('Squares of white marble and black obsidian run away in rank and file.',
                   'Your footsteps ring out across the polished stone.', 'A thin line of brass divides one square from the next.',
                   'The great board waits in silence for the next move.'),
}


def _norm(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def scrub_filler(world):
    """Take out the sector filler a room's look contradicts (see FILLER); returns how many rooms."""
    import textwrap
    n = 0
    for room in (getattr(world, 'rooms', {}) or {}).values():
        look = getattr(room, 'look', None)
        text = _norm(getattr(room, 'description', ''))
        if not look or not text:
            continue
        cut = 0
        for kind, lines in FILLER.items():
            if look in FILLER_FITS[kind]:
                continue
            for line in lines:
                if line in text:
                    text = _norm(text.replace(line, ''))
                    cut += 1
        if not cut:
            continue
        own = OWN_LINES.get(look)
        if own:
            k = int(getattr(room, 'vnum', 0) or 0)
            text = f'{text} {own[k % len(own)]} {own[(k // len(own) + 1 + k) % len(own)] if len(own) > 1 else ""}'.strip()
            text = _norm(text.replace(own[k % len(own)] + ' ' + own[k % len(own)], own[k % len(own)]))
        room.description = textwrap.fill(text, 79)
        n += 1
    return n


# ---------------------------------------------------------------- under the water
# A room typed open water whose place is under it (Under The Dock, Beneath The Shallow Lake) drew as
# the sea's surface: waves, the far shore, a door standing in open water (the owner, of the grate
# under New Thalos's dock: "it doesn't look like a lair"). Such a room is drawn as the seabed:
#   its name or its words say so: under the dock, beneath the lake, water that fills the passage;
#   you dive into it: a way down from the water above, and its way up leads back to that water;
#   or every way out of it leads under the water (the lair behind the grate under the dock).
UNDER_NAME = re.compile(r'\b(under ?water|(?:under|beneath|below) (?:the )?(?:docks?|piers?|jetty|wharf|waves|surface|water|sea|lake|'
                        r'shallow lake|river|pool)|sea ?floor|ocean floor|sea ?bed|lake ?bed|river ?bed)\b', re.I)
UNDER_DESC = re.compile(r'\b(water (?:that )?fills the (?:passage|chamber|tunnel|room) completely|water closes (?:around|over) you|'
                        r'swim+ing (?:under|beneath)(?:neath)? the|holding your breath)\b', re.I)


def under_water(rooms, ov):
    """Give the water rooms that lie under the water the 'underwater' look; returns how many."""
    water = {'water_swim', 'water_noswim'}
    free = lambda r: (getattr(r, 'sector_type', '') in water and r.look_why is None and r.vnum not in ov['rooms'])

    def way(room, d):
        ex = (getattr(room, 'exits', None) or {}).get(d)
        to = ex.get('to_room') if isinstance(ex, dict) else ex
        try:
            return rooms.get(int(to))
        except (TypeError, ValueError):
            return None

    under = set()
    for room in rooms.values():
        if not free(room):
            continue
        up = way(room, 'up')
        dived = (up is not None and getattr(up, 'sector_type', '') in water
                 and any(way(n, 'down') is room for n in _neighbours(room, rooms)))
        if UNDER_NAME.search(room.name or '') or UNDER_DESC.search(room.description or '') or dived:
            under.add(room)
    # (out from those, while every way out of a water room leads under the water)
    grew = True
    while grew:
        grew = False
        for room in rooms.values():
            if room in under or not free(room):
                continue
            near = list(_neighbours(room, rooms))
            if near and all(n in under or getattr(n, 'look', None) == 'underwater' for n in near):
                under.add(room)
                grew = True
    for room in under:
        room.look, room.look_why = 'underwater', 'description'
    return len(under)


def classify(world, overrides=None):
    """Give every room its `look` (and `look_why`). Returns the counts per look."""
    rooms = getattr(world, 'rooms', {}) or {}
    ov = overrides if overrides is not None else load_overrides()
    for room in rooms.values():
        sector = getattr(room, 'sector_type', '') or 'inside'
        # a room pinned by hand (world/looks.json) over the look its zone states for all its rooms
        stated = ov['rooms'].get(room.vnum) or getattr(room, 'stated_look', None)
        if stated:
            room.look, room.look_why = stated, 'stated'
            continue
        look, why = _own_look(room)
        # a zone wholly underground (the sewers): every room is underground whatever its imported
        # sector says (a pipe junction typed 'city', a ledge 'mountain'), but for one whose own name
        # says another underground place (a cave in the sewers stays a cave) and the water in it
        under = (ov.get('underground') or {}).get(_zone(room))
        # (the drow city is drow throughout: its tunnels, bridges and the dwellings carved in the
        # stalagmites too; terrain-drow.js tells them apart by their names)
        if under and (under in ZONE_WIDE or not look or look not in UNDERGROUND) and sector not in WATER_SECTORS:
            room.look, room.look_why = under, 'stated'      # (world/looks.json states it)
            continue
        if not look and _trees(room):
            look, why = 'forest', 'description'
        text = f'{room.name} {room.description}'
        if not look and sector in ('city', 'field', 'hills') and STONES_RE.search(text) and not TOWN_RE.search(text):
            look, why = 'stones', 'description'
        if not look and sector == 'city':
            b = city_building(room)
            look, why = (b, 'name') if b else (townless(room), 'description')
        if not look and _zone(room) in ov['zones'] and _fits(room, ov['zones'][_zone(room)]):
            look, why = ov['zones'][_zone(room)], 'zone'
        room.look, room.look_why = (look, why) if look else (sector, None)
    under_water(rooms, ov)
    # neighbours: waves out from the rooms with a look of their own
    for wave in range(max(n for n, _ in SPREAD.values())):
        taken = {}
        for room in rooms.values():
            if room.look_why is not None:
                continue
            sector = getattr(room, 'sector_type', '') or 'inside'
            near = Counter(n.look for n in _neighbours(room, rooms)
                           if n.look_why is not None and _zone(n) == _zone(room) and n.look in SPREAD)
            if not near:
                continue
            look = near.most_common(1)[0][0]
            steps, through = SPREAD[look]
            if wave >= steps or sector not in through:
                continue
            if look in UNDERGROUND and look != 'sewer' and INTERIOR_RE.search(f'{room.name} {room.description}'):
                continue
            # (a styled zone's halls stay its halls: a cell pinned a dungeon doesn't make the tower's
            # reading room one)
            if look in UNDERGROUND and _zone(room) in (ov.get('interiors') or {}):
                continue
            if look in ('village', 'camp', 'ruins') and (TOWN_RE.search(f'{room.name} {room.description}') or STREET_RE.search(room.name or '')):
                continue
            taken[room] = look
        for room, look in taken.items():
            room.look, room.look_why = look, 'neighbours'
    # a zone that is plainly underground (a third or more of its enclosed rooms have underground
    # looks by now, the most common at least ZONE_MIN): its other enclosed rooms take that look
    zones = {}
    for room in rooms.values():
        zones.setdefault(_zone(room), []).append(room)
    for zn, members in zones.items():
        # (a castle's, a tower's, a temple's halls are drawn in its interior style, never made a cave
        # by the caves under it: those keep the look their own words give them)
        if zn in (ov.get('interiors') or {}):
            continue
        enclosed = [r for r in members if (getattr(r, 'sector_type', '') or 'inside') in ENCLOSED_SECTORS]
        named = Counter(r.look for r in enclosed if r.look_why is not None and r.look in UNDERGROUND)
        if not named:
            continue
        look, n = named.most_common(1)[0]
        if n < ZONE_MIN or sum(named.values()) * 3 < len(enclosed):
            continue
        for r in enclosed:
            # (never a room plainly a building's: a watchtower's chamber, a lodge, a cellar)
            if r.look_why is None and not INTERIOR_RE.search(f'{r.name} {r.description}') and not reads_building(r.description):
                r.look, r.look_why = look, 'zone'
    # a cave of ice or of fire by its own words (two or more mentions): the Winterlands' caverns of
    # ice pillars and icicles, a tunnel with lava in its cracks (not a room pinned by hand)
    for room in rooms.values():
        if room.look != 'cave' or room.vnum in ov['rooms']:
            continue
        text = f'{room.name} {room.description}'
        if len(ICE_WORDS.findall(text)) >= 2:
            room.look, room.look_why = 'ice_cave', 'description'
        elif len(LAVA_WORDS.findall(text)) >= 2:
            room.look, room.look_why = 'lava_cave', 'description'
    return Counter(r.look for r in rooms.values())


# snow in a wood and snow on a mountainside: the client draws trees through the first and cliffs
# round the second (terrain-looks.js SNOW_WOOD, SNOW_PEAK; the same words)
SNOW_WOOD = re.compile(r'\b(trees?|forest|woods?|woodland|winterwood|pines?|firs?|spruces?|taiga|birch(?:es)?|groves?|fallen trunks?|root plates?)\b', re.I)
SNOW_PEAK = re.compile(r'\b(mountains?|mountainside|peaks?|summit|cliffs?|crags?|ridges?|slopes?|mountain pass)\b', re.I)
ICE_WORDS = re.compile(r'\b(ice|icy|icicles?|frost(?:ed|y)?|frozen|glaciers?|rime)\b', re.I)
LAVA_WORDS = re.compile(r'\b(lava|magma|molten)\b', re.I)


def summary(world):
    """Counts per look and per reason, for the world check and the docs."""
    rooms = (getattr(world, 'rooms', {}) or {}).values()
    return {'looks': Counter(r.look for r in rooms), 'why': Counter(r.look_why for r in rooms)}


# Filler the old description padder added everywhere: an indoor scene's lines (walls, a ceiling,
# stale air, dust). Under open sky or the sea they contradict the room, so they come out of every
# room that is not enclosed (the owner: rooms should match their descriptions).
INDOOR_FILLER = [
    "Dust motes drift in the stale air.", "The walls are rough-hewn and cold to the touch.",
    "The ceiling hangs low overhead.", "The air is still and musty.", "Shadows gather in the corners.",
]
_FILLER_RE = [re.compile(r'\s*' + r'\s+'.join(re.escape(w) for w in f.split())) for f in INDOOR_FILLER]
OPEN_LOOKS = {'field', 'forest', 'hills', 'mountain', 'desert', 'snow', 'shore', 'swamp', 'volcanic',
              'water_swim', 'water_noswim', 'underwater', 'city', 'darkforest',
              'stones', 'village', 'camp', 'garden', 'ruins', 'terrace', 'chessboard'}


def strip_filler(world) -> int:
    """Take the indoor filler out of the descriptions of rooms not enclosed; returns how many."""
    n = 0
    for room in (getattr(world, 'rooms', {}) or {}).values():
        look = getattr(room, 'look', None) or getattr(room, 'sector_type', '')
        flags = set(getattr(room, 'flags', None) or ())
        if look not in OPEN_LOOKS or ('indoors' in flags and look not in ('underwater', 'water_swim', 'water_noswim')):
            continue
        d = getattr(room, 'description', '') or ''
        new = d
        for rx in _FILLER_RE:
            new = rx.sub('', new)
        if new != d:
            room.description = new.strip()
            n += 1
    return n

