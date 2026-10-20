"""A zone's own colours, read from what its rooms say (Phase 4 of docs/world/room_visuals.md).

Morkai is built of black stone, Olympus of white marble, the Thalos desert city of red sandstone,
and a haunted crypt burns with green ghost-fire; the 3D client drew every town's paving and every
hall's walls the same grey under the same light. Here each zone's rooms are read for the colour
of their stone and the colour of their light; where the words agree often enough the zone gets a
tone, and /play tints its stone and its light by it:

  {'stone': 'black' | 'white' | 'red' | 'green' | 'blue' | 'gold' | 'brown', 'light': 'ghost' | 'moon' | 'fire',
   'interior': 'castle' | 'arcane' | 'holy' | 'infernal' | 'haunted' | 'dwarven' | 'elven'}

A zone's tone can also be stated by hand (world/looks.json 'tones': Ghenna, a hell, has red stone
and firelight whatever its words say). The interior style is not read from the words but stated per
zone in world/looks.json 'interiors'
(the art audit, tools/jev_audit.py zones): its indoor rooms are drawn in that style
(world3d/terrain-interiors.js) and not as a homely house.

Nothing is saved: tones are read at load (World.load -> annotate), sent with each room in the zone
map (`tone`).
"""
import re
from collections import Counter, defaultdict

COLOUR = {'black': 'black', 'obsidian': 'black', 'basalt': 'black', 'jet': 'black',
          'white': 'white', 'marble': 'white', 'alabaster': 'white', 'ivory': 'white',
          'red': 'red', 'crimson': 'red', 'sandstone': 'red', 'rust': 'red', 'ochre': 'red',
          'green': 'green', 'jade': 'green', 'mossy': 'green',
          'blue': 'blue', 'azure': 'blue', 'sapphire': 'blue',
          'gold': 'gold', 'golden': 'gold', 'gilded': 'gold',
          'brown': 'brown', 'earthen': 'brown', 'mud': 'brown'}
MATERIAL = r'(?:stone|stones|marble|granite|basalt|obsidian|sandstone|brick|bricks|rock|slate|flagstones?|walls?|cobbles?|tiles?|paving|blocks|masonry)'
STONE_RE = re.compile(r'\b(' + '|'.join(sorted(COLOUR, key=len, reverse=True)) + r')[\s-]+' + MATERIAL + r'\b', re.I)
# a material that is its own colour, named alone
BARE_RE = re.compile(r'\b(marble|obsidian|basalt|sandstone|alabaster)\b', re.I)
LIGHT_RE = {
    'ghost': re.compile(r'\b(ghost[\s-]?fire|ghostly (?:light|glow)|green (?:flames?|fire|glow)|witch[\s-]?light|corpse[\s-]?light)\b', re.I),
    'moon': re.compile(r'\b(moonlight|moonlit|starlight|starlit|silver(?:y)? light)\b', re.I),
    'fire': re.compile(r'\b(torchlight|firelight|candlelight|lamplight|ruddy (?:light|glow)|braziers? (?:glow|burn|blaze))\b', re.I),
}
MIN_ROOMS = 5            # a zone needs this many rooms to have a tone
MIN_HITS = 4             # and its words this many agreeing mentions
SHARE = 0.45             # making up this much of all the colours named


def read(texts):
    """The tone a body of room texts agree on (None: they don't): enough mentions for the size
    of the zone (one in eight rooms, at least MIN_HITS) and most of the colours named."""
    need = max(MIN_HITS, len(texts) / 8)
    stone, light = Counter(), Counter()
    for t in texts:
        for m in STONE_RE.finditer(t):
            stone[COLOUR[m.group(1).lower()]] += 1
        for m in BARE_RE.finditer(t):
            stone[COLOUR[m.group(1).lower()]] += 0.5
        for k, rx in LIGHT_RE.items():
            light[k] += len(rx.findall(t))
    tone = {}
    total = sum(stone.values())
    if total:
        c, n = stone.most_common(1)[0]
        if n >= need and n / total >= SHARE:
            tone['stone'] = c
    ltotal = sum(light.values())
    if ltotal:
        k, n = light.most_common(1)[0]
        if n >= max(3, len(texts) / 10) and n / ltotal >= 0.5:
            tone['light'] = k
    return tone or None


def annotate(world):
    """Give every room its zone's tone (room.tone, None for most); returns {zone number: tone}."""
    by_zone = defaultdict(list)
    for room in world.rooms.values():
        z = getattr(getattr(room, 'zone', None), 'number', None)
        by_zone[z].append(room)
    from room_looks import load_overrides
    ov = load_overrides()
    interiors, stated = ov.get('interiors', {}), ov.get('tones', {})
    tones = {}
    for z, rooms in by_zone.items():
        tone = read([f"{r.name}. {r.description or ''}" for r in rooms]) if len(rooms) >= MIN_ROOMS else None
        if stated.get(z):
            tone = {**(tone or {}), **stated[z]}
        if interiors.get(z):
            tone = {**(tone or {}), 'interior': interiors[z]}
        if tone:
            tones[z] = tone
        for r in rooms:
            r.tone = tone
    return tones
