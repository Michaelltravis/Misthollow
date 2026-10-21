"""What a room's words say lies beyond it: land seen across the water, a shore at hand, mountains
on the horizon. The 3D client draws it there (world3d/vista.js: a silhouette in the haze; a
`near` one keeps a water room's bank on that side, edges.js landSides).

The owner, on the Sea of Storms: "ocean rooms that have no exit should just show more ocean on the
horizon or a land mass if there's a description of land in the distance". So: sentence by
sentence, a word for land (island, coast, cliffs, mountains, a town...) with a word that puts it
at a distance ("in the distance", "beyond", "looms", "lies") or at hand ("close at hand", "either
side", "between the two moles"), or a compass word, makes one vista:

    {'kind': 'island'|'coast'|'cliffs'|'mountains'|'hills'|'forest'|'town',
     'dir': 'north'|'south'|'east'|'west'|None, 'near': bool}

A sentence that denies it ("no shore shows anywhere", "the horizon blurs into grey nothing", far
shores "lost in blackness") gives none. Only open-country and water rooms have vistas (a room
indoors or underground sees no horizon), and a land room sees no forest vista (the country round
it runs on by itself: far.js).
"""
import re

KINDS = (
    ('island', r'islands?|isles?|islets?|atolls?'),
    ('cliffs', r'cliffs?|headlands?|capes?|bluffs?|crags?|promontor(?:y|ies)|sea[- ]?stacks?|moles?|breakwaters?|sea[- ]?walls?|jett(?:y|ies)|piers?'),
    ('mountains', r'mountains?|peaks?|mountain range|volcano(?:es)?|summits?'),
    ('hills', r'hills|downs'),
    ('town', r'towns?|city|cities|harbou?rs?|ports?|roofs|rooftops|towers?|lighthouses?|villages?|spires?|quays?'),
    ('coast', r'coasts?|coastline|shores?|shoreline|beach(?:es)?|mainland|strand'),
    ('forest', r'forests?|woods|woodland|treeline|jungle'),
)
LAND = re.compile(r'\b(' + '|'.join(f'(?P<{k}>{rx})' for k, rx in KINDS) + r')\b', re.I)
FAR = re.compile(r"\b(in the distance|distant|far(?: off| away| across| beyond| side)?|off in|off to|beyond|across|"
                 r"on the horizon|horizon|looms?|rises?|rising|lies|lie|lying|visible|can be seen|stands? out|shows?|"
                 r"glimpse[sd]?|catch sight|line of|wrapped in)\b", re.I)
NEAR = re.compile(r"\b(close at hand|at hand|close beside|beside you|close by|nearby|hard by|right here|"
                  r"either side|both sides|on each side|alongside|between the (?:two )?\w+)\b", re.I)
# land on both sides at once lies on the room's sides, not one way (9540: "the channel between the
# two moles" runs north and south)
BOTH = re.compile(r"\b(either side|both sides|on each side|alongside|between the (?:two )?\w+)\b", re.I)
NOT = re.compile(r"\b(no (?:shore|land|coast|island|sign of land)|not a (?:shore|speck)|never|nothing|nowhere|"
                 r"lost in (?:blackness|darkness|the dark|the mist|the fog|mist|fog)|out of sight|cannot see|can't see)\b", re.I)
DIR = re.compile(r'\b(north|south|east|west)(?:ward|wards|ern|erly)?\b', re.I)
# rooms that have a horizon (room_looks.py looks and the sectors)
OPEN = {'water_swim', 'water_noswim', 'water_surface', 'shore', 'field', 'hills', 'mountain', 'forest', 'darkforest',
        'desert', 'snow', 'swamp', 'stones', 'volcanic', 'camp', 'ruins', 'terrace', 'garden', 'village'}
WATER = {'water_swim', 'water_noswim', 'water_surface', 'shore'}


def _sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', ' '.join(str(text or '').split())) if s.strip()]


def vistas_of_text(text, water=True):
    """The vistas a description gives (water: a room on the water, where a forest across the
    water is a vista too)."""
    out, seen = [], set()
    for s in _sentences(text):
        if NOT.search(s):
            continue
        m = LAND.search(s)
        if not m:
            continue
        kind = next(k for k, _ in KINDS if m.group(k))
        if kind == 'forest' and not water:
            continue
        near = bool(NEAR.search(s))
        far = bool(FAR.search(s))
        d = DIR.search(s)
        if not (near or far or d):
            continue
        if near and BOTH.search(s):
            d = None
        v = {'kind': kind, 'dir': d.group(1).lower() if d else None, 'near': near and not re.search(r'\b(in the distance|distant|on the horizon|far)\b', s, re.I)}
        key = (v['kind'], v['dir'], v['near'])
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
        if len(out) >= 3:
            break
    # a kind named with a side needs no second, sideless one
    sided = {(v['kind'], v['near']) for v in out if v['dir']}
    return [v for v in out if v['dir'] or (v['kind'], v['near']) not in sided]


def vistas(room):
    """A room's vistas (cached on the room: its words do not change while the world runs)."""
    cached = getattr(room, '_vistas', None)
    if cached is not None:
        return cached
    look = str(getattr(room, 'look', None) or getattr(room, 'sector_type', '') or '')
    sector = str(getattr(room, 'sector_type', '') or '')
    flags = getattr(room, 'flags', None) or ()
    out = []
    if (look in OPEN or sector in OPEN) and 'indoors' not in flags:
        out = vistas_of_text(getattr(room, 'description', '') or '', water=look in WATER or sector in WATER)
    try:
        room._vistas = out
    except Exception:
        pass
    return out
