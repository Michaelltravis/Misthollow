"""What a character's gear looks like, for the 3D client (world3d/gearlook.js and equip.js).

The server is the one place items are classified. For each worn piece the client is told its
kind (sword, bow, helm, cloak...), how many hands it takes, how heavy armour is (0 cloth,
1 leather, 2 mail, 3 plate), its material and colour (names of ramps in the equipment palette:
tools/art3d/ramps.json), its element, its named set, and a tier 0-5 that grows with the item's
level and quality. That is all a renderer needs; a `sig` hash lets it re-dress only on change.

  look = {'v': 1, 'sig': '5f2c9a1e', 'rn': 2, 'race': 'dwarf', 'aura': 'set', 'set': 'frostlords_mantle',
          'main': {'k': 'sword', 'h': 1, 'm': 'steel', 't': 2}, 'off': {'k': 'shield', 'v': 'round', ...},
          'head': {...}, 'body': {'w': 2, 'm': 'iron', 't': 1}, 'arms': {...}, 'legs': {...},
          'back': {'k': 'cloak', 'v': 'rogue', 'c': 'black'}, 'quiver': 1, 'light': {'k': 'torch'}}

Item level: an item's `min_level`, else the level of the strongest creature that wears, carries
or drops it (that covers nearly all the world's gear), else its named set's level range. What a
shop sells counts as its weakest carrier's level, and at least new (8): a level-33 shopkeeper's
sword is still a shop sword. Tier:
level <8 -> 0, <18 -> 1, <30 -> 2, <42 -> 3, else 4; one more (up to 4) for magic, glowing,
humming, superior or enchanted gear; a legendary is 5. Renown (`rn`) is the character's own
standing: level 10, 20, 35 and 45 each add a band, prestige makes it 5.

When a character's look changes (they wield, wear, remove, are disarmed, level up), 3D clients
that can see them are told at once (web_map.relay_look); the commands' dispatcher calls
after_command() for the player and anyone in the room with them.
"""
import hashlib
import json
import re

# ---------------------------------------------------------------- item levels
ITEM_LEVELS = {}          # vnum -> level, filled by build_item_levels() at world load
SHOP_LEVEL = 8            # the least a shop's goods count as: bought new, clean (tier 1)


def _refs(value):
    """Item vnums named anywhere in a creature's equipment, inventory or loot tables."""
    if value is None:
        return
    if isinstance(value, (int, str)) and str(value).isdigit():
        yield int(value)
    elif isinstance(value, dict):
        for k in ('vnum', 'obj_vnum', 'item', 'object'):
            if k in value:
                yield from _refs(value[k])
                return
        for v in value.values():
            yield from _refs(v)
    elif isinstance(value, (list, tuple)):
        if len(value) == 2 and all(isinstance(x, (int, float)) for x in value) and isinstance(value[0], int):
            yield value[0]        # [vnum, chance]
            return
        for v in value:
            yield from _refs(v)


def build_item_levels(world):
    """vnum -> item level for every prototype the world knows (see the module notes)."""
    levels = {}
    for vnum, proto in (getattr(world, 'obj_prototypes', {}) or {}).items():
        if isinstance(proto, dict):
            lvl = proto.get('min_level') or proto.get('level')
            if lvl:
                try:
                    levels[int(vnum)] = int(lvl)
                except (TypeError, ValueError):
                    pass
    worn_by, weakest, sold = {}, {}, set()
    for proto in (getattr(world, 'mob_prototypes', {}) or {}).values():
        if not isinstance(proto, dict):
            continue
        lvl = int(proto.get('level') or 1)
        for key in ('equipment', 'inventory', 'loot_table', 'boss_loot_table', 'equipment_rolls'):
            for v in _refs(proto.get(key)):
                worn_by[v] = max(worn_by.get(v, 0), lvl)
                weakest[v] = min(weakest.get(v, lvl), lvl)
        for v in _refs((proto.get('shop_config') or {}).get('sells')):
            sold.add(v)
    # what a shop sells is ordinary gear, however strong the shopkeeper who also carries it: as
    # good as the weakest creature that has it, and new (at least tier 1)
    for v in sold:
        levels.setdefault(v, max(SHOP_LEVEL, weakest.get(v, SHOP_LEVEL)))
    for v, lvl in worn_by.items():
        levels.setdefault(v, lvl)
    try:
        from sets import NAMED_SETS
        for cfg in NAMED_SETS.values():
            lo = (cfg.get('level_range') or (1, 1))[0]
            for v in cfg.get('pieces', {}):
                levels.setdefault(int(v), int(lo))
    except Exception:
        pass
    try:
        from objects import PRESET_OBJECTS
        for v in PRESET_OBJECTS:
            levels.setdefault(int(v), 1)          # starting gear and shop basics
    except Exception:
        pass
    ITEM_LEVELS.clear()
    ITEM_LEVELS.update(levels)
    return levels


def item_level(item):
    lvl = ITEM_LEVELS.get(getattr(item, 'vnum', None))
    if lvl is None:
        lvl = int(getattr(item, 'min_level', 0) or getattr(item, 'level', 0) or 0)
    if not lvl and getattr(item, 'rarity', '') == 'legendary':
        lvl = 45
    return max(1, int(lvl or 1))


QUALITY_FLAGS = {'magic', 'glow', 'hum', 'superior', 'flaming', 'frost'}


def item_tier(item):
    if getattr(item, 'rarity', '') == 'legendary':
        return 5
    lvl = item_level(item)
    t = 0 if lvl < 8 else 1 if lvl < 18 else 2 if lvl < 30 else 3 if lvl < 42 else 4
    flags = set(getattr(item, 'flags', ()) or ())
    if flags & QUALITY_FLAGS or getattr(item, 'enchanted', False):
        t = min(4, t + 1)
    return t


# ---------------------------------------------------------------- reading an item's words
def _text(item):
    t = ' '.join(str(getattr(item, a, '') or '') for a in ('name', 'short_desc', 'room_desc'))
    return t.replace('‑', '-').replace('‐', '-').lower()


def _first(rules, text, default=None):
    for rx, val in rules:
        if rx.search(text):
            return val
    return default


def _rx(words):
    return re.compile(r'\b(?:' + words + r')')


# weapon kinds, most specific first; (kind, hands)
WEAPONS = [
    (_rx(r'hand ?crossbow'), ('crossbow', 1)),
    (_rx(r'crossbow|arbalest'), ('crossbow', 2)),
    (_rx(r'longbow|shortbow|short bow|long bow|warbow|recurve|(?!elbow|rainbow)\w*bow\b'), ('bow', 2)),
    (_rx(r'lute|lyre|harp|flute|pipes?\b|horn\b|drum|mandolin|fiddle|viol|ocarina|bagpipe|zither|psaltery|instrument'), ('instrument', 1)),
    (re.compile(r'\wflute\b'), ('instrument', 1)),              # a dirgeflute (not "sharp", "thorn")
    (_rx(r'halberd|glaive|bardiche|guisarme|fauchard|corbin|voulge|pole-?axe|poleaxe|partisan|naginata|bec de|lucerne|polearm'), ('polearm', 2)),
    (_rx(r'scythe|sickle'), ('scythe', 2)),
    (_rx(r'spear|lance|pike|javelin|trident|harpoon|lancet'), ('spear', 2)),
    (_rx(r'maul|warhammer|war hammer|sledge|great ?hammer'), ('hammer', 2)),
    (_rx(r'hammer|mallet|gavel'), ('hammer', 1)),
    (_rx(r'great ?axe|battle ?axe|war ?axe|two-handed axe|executioner'), ('axe', 2)),
    (_rx(r'axe|cleaver|hatchet|tomahawk'), ('axe', 1)),
    (_rx(r'mace|club|morning ?star|flail|cudgel|truncheon|scepter|sceptre|cosh|bludgeon|knobkerrie'), ('mace', 1)),
    (_rx(r'pick(?:axe)?\b|mattock'), ('pick', 1)),
    (_rx(r'whip|lash|scourge|cat-o'), ('whip', 1)),
    (_rx(r'quarter-?staff|stave|crook|\w*staff'), ('staff', 2)),
    (_rx(r'wand|rod\b'), ('wand', 1)),
    (_rx(r'claw|talon|knuckle|cestus|fist'), ('claw', 1)),
    (_rx(r'dart|shuriken|throwing|chakram|bola'), ('thrown', 1)),
    (_rx(r'dagger|knife|dirk|stiletto|shiv|kris|tanto|sai\b|main-gauche|poniard|misericorde|fang\b'), ('dagger', 1)),
    (_rx(r'great ?sword|greatsword|great ?blade|claymore|zweihander|two-handed sword|flamberge|executioner'), ('sword', 2)),
    (re.compile(r'\w(?:greatblade|greatsword)\b'), ('sword', 2)),
    (_rx(r'sword|blade|sabre|saber|rapier|scimitar|katana|falchion|cutlass|estoc|gladius|brand\b|edge\b|longsword|broadsword|tulwar|shamshir|khopesh'), ('sword', 1)),
    # the noun at the end of a made-up word: a warblade, a tombknife, a frostaxe
    (re.compile(r'\w(?:knife|dagger)\b'), ('dagger', 1)),
    (re.compile(r'\w(?:axe)\b'), ('axe', 1)),
    (re.compile(r'\w(?:blade|sword|brand)\b'), ('sword', 1)),
]
WEAPON_TYPE_KIND = {'slash': 'sword', 'pierce': 'dagger', 'stab': 'dagger', 'pound': 'mace', 'crush': 'mace', 'mace': 'mace',
                    'bludgeon': 'mace', 'staff': 'staff', 'bow': 'bow', 'whip': 'whip', 'claw': 'claw', 'sword': 'sword',
                    'dagger': 'dagger', 'axe': 'axe', 'hammer': 'hammer', 'spear': 'spear'}

# what a hand holds that isn't a weapon
HELD = [
    (_rx(r'quiver'), 'quiver'),
    (re.compile(r'\w*book\b|\b(?:tome|grimoire|codex|libram|manual|scroll|journal|ledger|bible|hymnal)'), 'book'),
    (_rx(r'orb|sphere|globe|crystal ball|focus|prism|scrying'), 'orb'),
    (_rx(r'censer|thurible'), 'censer'),
    (_rx(r'lantern|lamp'), 'lantern'),
    (_rx(r'torch'), 'torch'),
    (_rx(r'skull|head of'), 'skull'),
    (_rx(r'relic|reliquary|idol|icon|symbol|talisman|fetish|totem|ankh|holy|unholy|chalice|grail|sigil'), 'relic'),
    (_rx(r'shield|buckler|aegis|targe|pavise'), 'shield'),
]

HEADS = [
    (_rx(r'hood|cowl'), 'hood'),
    (_rx(r'crown|circlet|diadem|tiara|coronet|laurel'), 'crown'),
    (_rx(r'horned|horns|viking|fur hat|pelt|bearskin|skull ?cap'), 'horned'),
    (_rx(r'wizard|witch|pointed|conical'), 'hat'),
    (_rx(r'hat\b|cap\b|beret|tricorn|turban|bandana|headband|mitre|miter'), 'hat'),
    (_rx(r'helm|helmet|bascinet|sallet|barbute|armet|coif|great ?helm|visor|casque|morion'), 'helm'),
    (_rx(r'mask|veil'), 'mask'),
]

# a staff's head (world3d/procgear.js staff_*): drawn from its words; none, and the class decides
STAFF_HEADS = [
    (_rx(r'skull|bone|lich|death|grave|necro|corpse|tomb'), 'skull'),
    (_rx(r'crystal|gem|star|astronom|prism|arcane|shard|quartz|sapphire|ruby|emerald|moon|sun'), 'crystal'),
    (_rx(r'gnarled|oak|root|twisted|druid|thorn|vine|yew|branch|briar|bramble|living wood|driftwood'), 'gnarled'),
    (_rx(r'pilgrim|walking|quarter-?staff|plain|simple|shepherd|crook'), 'plain'),
]
# a hat's shape (procgear.js brimhat, cap, mitre; the pack's wizard hat): none, and the class decides
HATS = [
    (_rx(r'wizard|witch|pointed|conical|mage|archmage|sorcer|magus|star'), 'wizard'),
    (_rx(r'mitre|miter|bishop|prelate'), 'mitre'),
    (_rx(r'cap\b|beret|bandana|headband|turban|skull ?cap|coif|kerchief'), 'cap'),
    (_rx(r'tricorn|feather|brim|wide|plumed|cavalier|travell?er|bard|minstrel|wanderer|straw'), 'brim'),
]

SHIELDS = [
    (_rx(r'spike|spiked|barbed|thorn'), 'spike'),
    (_rx(r'tower|kite|pavise|great ?shield|rectang|heater|square'), 'square'),
    (_rx(r'buckler|round|targe|wooden|wood|hide'), 'round'),
    (_rx(r'crest|badge|heraldic|emblazon|sigil|royal|noble|knight'), 'badge'),
]

CLOAKS = [
    (_rx(r'fur|pelt|hide|bearskin|wolfskin'), 'barbarian'),
    (_rx(r'mantle|shroud|arcane|robe|stole|vestment'), 'mage'),
    (_rx(r'cape|royal|noble|tabard|surcoat|regal|knight'), 'knight'),
]

# armour weight: 3 plate, 2 mail, 1 leather, 0 cloth
WEIGHTS = [
    (re.compile(r'\w*plates?\b|\bplated|\bcuirass|\bgauntlet|\bvambrace|\bgreave|\bsabaton|\bsolleret|\bcuisse|\btasset|\bpauldron|\bspaulder|\baegis|\bcarapace'), 3),
    (re.compile(r'\bchain|\w*mail\b|\bring ?mail|\bscale|\bsplint|\bbanded|\bbrigandine|\blamellar|\bhauberk|\bcoat of'), 2),
    (_rx(r'leather|studded|hide|pelt|fur\b|jerkin|vest|jacket|doublet|bracer|glove|boot|buskin|sandal|chaps|harness|apron'), 1),
    (re.compile(r'\brobe|\bvestment|\bgarb|\bgown|\btunic|\bshirt|\bdress|\bcassock|\bhabit|\braiment|\bsilk|\w*cloth\b|\bwrap|\bsash|\btoga|\bkimono|\bmantle|\bshoes|\bslipper|\btrousers|\bbreeches|\bpants|\bleggings|\bhose\b'), 0),
]

METALS = [
    (_rx(r'green dragon|emerald dragon|dragon-?green'), 'dragon_green'),
    (_rx(r'dragon'), 'dragon_red'),
    (_rx(r'mithril|mithral|silvery-blue|moonsilver'), 'mithril'),
    (_rx(r'adamant'), 'adamant'),
    (_rx(r'obsidian|onyx|black|ebon|shadow|dark|void|night'), 'obsidian'),
    (_rx(r'gold|golden|gilded|gilt|royal'), 'gold'),
    (_rx(r'silver|silvery|argent'), 'silver'),
    (_rx(r'bronze'), 'bronze'),
    (_rx(r'copper'), 'copper'),
    (_rx(r'brass'), 'brass'),
    (_rx(r'bone|skull|ivory|horn\b'), 'bone'),
    (_rx(r'crystal|glass|diamond|prism|quartz'), 'crystal'),
    (_rx(r'rust|corrod|pitted'), 'rust'),
    (_rx(r'iron'), 'iron'),
    (_rx(r'steel'), 'steel'),
]
LEATHERS = [
    (_rx(r'dragon'), 'dragonhide'),
    (_rx(r'snake|serpent|lizard|wyrm'), 'snakeskin'),
    (_rx(r'black|dark|shadow|night|ebon'), 'leather_black'),
    (_rx(r'red|crimson|blood'), 'leather_red'),
    (_rx(r'hide|pelt|fur|rawhide'), 'hide'),
    (_rx(r'supple|tan|light|soft|suede'), 'leather_tan'),
    (_rx(r'studded|boiled|hardened|thick'), 'leather_dark'),
]
WOODS = [
    (_rx(r'black|dark|ebon|shadow|night|gnarled|twisted'), 'wood_dark'),
    (_rx(r'ash|birch|pale|white|elven|bleached'), 'wood_pale'),
    (_rx(r'yew|red|blood|cherry|mahogany'), 'wood_red'),
]
COLOURS = [
    (_rx(r'crimson|maroon|scarlet|blood'), 'crimson'),
    (_rx(r'red|ruby'), 'red'),
    (_rx(r'navy|midnight'), 'navy'),
    (_rx(r'royal'), 'royal_blue'),
    (_rx(r'blue|azure|sapphire|cobalt'), 'blue'),
    (_rx(r'forest|moss|verdant|woodland|ranger'), 'forest'),
    (_rx(r'olive|khaki'), 'olive'),
    (_rx(r'green|emerald|jade'), 'green'),
    (_rx(r'violet'), 'violet'),
    (_rx(r'magenta|fuchsia'), 'magenta'),
    (_rx(r'purple|amethyst|lavender|plum'), 'purple'),
    (_rx(r'black|dark|shadow|ebon|night|sable|raven|shadowy'), 'black'),
    (_rx(r'white|pale|ivory|snow|alabaster|bleached'), 'white'),
    (_rx(r'grey|gray|ash|silver|dusky|smoke'), 'grey'),
    (_rx(r'brown|umber|tan\b|russet|sackcloth|burlap|homespun'), 'brown'),
    (_rx(r'yellow|golden|gold|amber|saffron'), 'yellow'),
    (_rx(r'orange|flame|fiery|ember'), 'orange'),
    (_rx(r'teal|turquoise|aqua|sea'), 'teal'),
    (_rx(r'pink|rose'), 'pink'),
    (_rx(r'sky|frost|ice|glacial'), 'sky'),
]
CLOTH_COLOURS = ['red', 'crimson', 'blue', 'royal_blue', 'navy', 'green', 'forest', 'olive', 'purple', 'violet',
                 'magenta', 'black', 'white', 'grey', 'brown', 'yellow', 'orange', 'teal', 'pink', 'sky']
ELEMENTS = [
    (_rx(r'flaming|flame|fire|ember|inferno|blaze|burning|molten|magma|lava|phoenix|cinder|scorch'), 'fire'),
    (_rx(r'frost|ice|frozen|glacial|winter|snow|cold|rime|frigid'), 'frost'),
    (_rx(r'storm|lightning|thunder|spark|shock|tempest'), 'lightning'),
    (_rx(r'holy|blessed|divine|radiant|sacred|celestial|angel|saint|sun|dawn'), 'holy'),
    (_rx(r'poison|venom|toxic|plague|blight'), 'poison'),
    (_rx(r'vampir|blood'), 'blood'),
    (_rx(r'shadow|void|umbral|shade|abyss|night|doom'), 'shadow'),
    (_rx(r'arcane|mana|runic|rune|mystic|eldritch|star|astral'), 'arcane'),
    (_rx(r'thorn|verdant|druid|wild|living|grove|nature'), 'nature'),
]
ELEMENT_FLAGS = {'flaming': 'fire', 'frost': 'frost'}
# which instrument (the client builds each its own shape)
INSTRUMENTS = [
    (_rx(r'lyre'), 'lyre'), (_rx(r'harp'), 'harp'), (re.compile(r'flute|pipes?\b|whistle|recorder|ocarina'), 'flute'),
    (_rx(r'drum|tabor|tambour'), 'drum'), (_rx(r'horn\b|trumpet|bugle|warhorn'), 'horn'),
]
CROWNS = [(_rx(r'circlet|diadem|tiara|coronet|laurel'), 'circlet')]


def _named_set(item):
    try:
        from map_system import _SET_BY_VNUM
        return _SET_BY_VNUM.get(getattr(item, 'vnum', None))
    except Exception:
        return None


def _element(item, text, magical):
    flags = set(getattr(item, 'flags', ()) or ())
    for f, e in ELEMENT_FLAGS.items():
        if f in flags:
            return e
    # a word only counts on gear that is magical (a "dark robe" isn't a shadow weapon)
    return _first(ELEMENTS, text) if magical else None


def _common(item, text):
    """Fields every piece has: tier, set, legendary, element."""
    out = {'t': item_tier(item)}
    s = _named_set(item)
    if s:
        out['s'] = s
    elif getattr(item, 'set_id', None):
        # a zone set: its pieces share one colour, picked from the set's id
        sid = str(item.set_id)
        out['zc'] = CLOTH_COLOURS[int(hashlib.md5(sid.encode()).hexdigest()[:6], 16) % len(CLOTH_COLOURS)]
    if getattr(item, 'rarity', '') == 'legendary':
        out['lg'] = getattr(item, 'vnum', None)
    flags = set(getattr(item, 'flags', ()) or ())
    magical = bool(flags & QUALITY_FLAGS or getattr(item, 'enchanted', False) or out['t'] >= 4)
    e = _element(item, text, magical)
    if e:
        out['e'] = e
    return out


def _material(text, default):
    return _first(METALS, text, default)


def weapon_piece(item):
    text = _text(item)
    found = _first(WEAPONS, text)
    if not found:
        k = WEAPON_TYPE_KIND.get(str(getattr(item, 'weapon_type', '') or '').lower())
        found = (k, 2 if k in ('staff', 'bow') else 1) if k else ('sword', 1)
    kind, hands = found
    if 'two_handed' in set(getattr(item, 'flags', ()) or ()):
        hands = 2
    p = {'k': kind, 'h': hands}
    if kind == 'instrument':
        p['v'] = _first(INSTRUMENTS, text, 'lute')
    if kind == 'staff':
        head = _first(STAFF_HEADS, text)
        if head:
            p['v'] = head
    if kind in ('staff', 'bow', 'wand', 'instrument'):
        p['m'] = _first(WOODS, text, 'wood')
        metal = _first(METALS, text)
        if metal:
            p['m2'] = metal
    else:
        p['m'] = _material(text, 'steel')
        wood = _first(WOODS, text)
        if wood:
            p['m2'] = wood
    p.update(_common(item, text))
    return p


def held_piece(item):
    """The off hand: a second weapon, a shield, or something held (a book, an orb, a lute)."""
    text = _text(item)
    if getattr(item, 'item_type', '') == 'weapon' or _first(WEAPONS, text) and not _first(HELD, text):
        p = weapon_piece(item)
        p['h'] = 1
        return p
    kind = _first(HELD, text) or ('instrument' if _first(WEAPONS, text, ('', 0))[0] == 'instrument' else None)
    if kind == 'shield':
        return shield_piece(item)
    if not kind:
        return None                  # lockpicks, a vial: nothing to draw
    p = {'k': kind}
    if kind in ('book',):
        p['c'] = _first(COLOURS, text)
    if kind == 'instrument':
        p['v'] = _first(INSTRUMENTS, text, 'lute')
        p['m'] = _first(WOODS, text, 'wood')
    p.update(_common(item, text))
    return {k: v for k, v in p.items() if v is not None}


def shield_piece(item):
    text = _text(item)
    p = {'k': 'shield', 'v': _first(SHIELDS, text, 'round'), 'm': _material(text, 'iron')}
    wood = _first(WOODS, text) or ('wood' if re.search(r'\bwood|oak|plank|timber', text) else None)
    if wood:
        p['m2'] = wood
    p.update(_common(item, text))
    return p


def head_piece(item):
    text = _text(item)
    kind = _first(HEADS, text, 'helm')
    p = {'k': kind}
    if kind == 'crown':
        p['v'] = _first(CROWNS, text, 'crown')
    if kind == 'hat':
        v = _first(HATS, text)
        if v:
            p['v'] = v
    if kind == 'hood' and re.search(r'\bmask|\bmasked\b|\bveiled?\b|face-?wrap', text):
        p['v'] = 'masked'               # a cloth over the face below the eyes (procgear.js facemask)
    if kind in ('helm', 'crown', 'horned'):
        p['m'] = _material(text, 'gold' if kind == 'crown' else 'iron')
    else:
        p['c'] = _first(COLOURS, text)
    p.update(_common(item, text))
    return {k: v for k, v in p.items() if v is not None}


def armour_piece(item):
    text = _text(item)
    w = _first(WEIGHTS, text)
    if w is None and _first(METALS, text) not in (None, 'bone', 'crystal', 'obsidian', 'dragon_red', 'dragon_green'):
        w = 2                         # iron sleeves, golden armour: metal, so mail at least
    if w is None:
        wt = getattr(item, 'weight', 0) or 0
        w = 3 if wt >= 18 else 2 if wt >= 10 else 1 if wt >= 5 else 0
    if w >= 2 and re.search(r'\b(?:leather|hide|cloth|silk)\b', text):
        w = 1 if 'leather' in text or 'hide' in text else 0     # leather gauntlets, silk gloves
    p = {'w': w}
    if w >= 2:
        p['m'] = _material(text, 'iron' if w == 2 else 'steel')
    elif w == 1:
        p['m'] = _first(LEATHERS, text, 'leather')
    c = _first(COLOURS, text)
    if c and w == 0:
        p['c'] = c
    p.update(_common(item, text))
    return p


def cloak_piece(item):
    text = _text(item)
    p = {'k': 'cloak', 'v': _first(CLOAKS, text, 'rogue'), 'c': _first(COLOURS, text)}
    p.update(_common(item, text))
    return {k: v for k, v in p.items() if v is not None}


def renown(ch):
    if getattr(ch, 'prestige_class', None):
        return 5
    lvl = getattr(ch, 'level', 1) or 1
    return 4 if lvl >= 45 else 3 if lvl >= 35 else 2 if lvl >= 20 else 1 if lvl >= 10 else 0


def worn_aura(ch):
    """'legendary' when any legendary piece is worn; 'set' at 4+ pieces of one set."""
    worn = [it for it in (getattr(ch, 'equipment', {}) or {}).values() if it]
    if any(getattr(it, 'rarity', '') == 'legendary' for it in worn):
        return 'legendary'
    counts = {}
    for it in worn:
        sid = getattr(it, 'set_id', None)
        if sid:
            counts[str(sid)] = counts.get(str(sid), 0) + 1
    return 'set' if any(c >= 4 for c in counts.values()) else None


def _standing(ch):
    """A player's renown; a creature has none (its level is no standing)."""
    return renown(ch) if hasattr(ch, 'account_name') else 0


def _sex(ch):
    """A hero's sex, when they chose one (male or female: the 3D face and build, gearlook.js)."""
    sex = str(getattr(ch, 'sex', '') or '').lower()
    return sex if sex in ('male', 'female') else ''


def _style(ch):
    """A look the hero chose beyond their class's own (player.py LOOK_STYLES): the archmage, for a mage."""
    from player import LOOK_STYLES
    style = str(getattr(ch, 'look_style', '') or '')
    return style if str(getattr(ch, 'char_class', '') or '').lower() in LOOK_STYLES.get(style, ()) else ''


def _signature(ch):
    """What the look depends on, cheaply: rebuilt only when this changes."""
    eq = getattr(ch, 'equipment', {}) or {}
    parts = [_standing(ch), str(getattr(ch, 'race', '') or ''), _sex(ch), _style(ch)]
    for slot in sorted(eq):
        it = eq[slot]
        if it is not None:
            parts.append((slot, id(it), getattr(it, 'name', ''), tuple(sorted(getattr(it, 'flags', ()) or ())),
                          getattr(it, 'rarity', ''), bool(getattr(it, 'enchanted', False))))
    return tuple(parts)


def look_of(ch):
    """The look summary for a character (cached until their gear or standing changes)."""
    key = _signature(ch)
    cached = getattr(ch, '_look_cache', None)
    if cached and cached[0] == key:
        return cached[1]
    eq = getattr(ch, 'equipment', {}) or {}
    look = {'v': 1, 'rn': _standing(ch)}
    race = str(getattr(ch, 'race', '') or '').lower()
    if race:
        look['race'] = race
    if _sex(ch):
        look['sex'] = _sex(ch)
    if _style(ch):
        look['style'] = _style(ch)
    if eq.get('wield'):
        look['main'] = weapon_piece(eq['wield'])
    if eq.get('shield'):
        look['off'] = shield_piece(eq['shield'])
    for slot in ('dual_wield', 'hold'):
        it = eq.get(slot)
        if not it or 'off' in look and look['off'].get('k') == 'shield' and slot == 'hold':
            continue
        p = held_piece(it)
        if p is None:
            continue
        if p['k'] == 'quiver':
            look['quiver'] = 1
        elif 'off' not in look:
            look['off'] = p
    if eq.get('head'):
        look['head'] = head_piece(eq['head'])
    if eq.get('body'):
        look['body'] = armour_piece(eq['body'])
    for name, slots in (('arms', ('arms', 'hands')), ('legs', ('legs', 'feet'))):
        it = next((eq[s] for s in slots if eq.get(s)), None)
        if it is not None:
            look[name] = armour_piece(it)
    if eq.get('about'):
        look['back'] = cloak_piece(eq['about'])
    if eq.get('light'):
        look['light'] = {'k': 'lantern' if re.search(r'lantern|lamp', _text(eq['light'])) else 'torch'}
    aura = worn_aura(ch)
    if aura:
        look['aura'] = aura
    sets = {}
    for p in look.values():
        if isinstance(p, dict) and p.get('s'):
            sets[p['s']] = sets.get(p['s'], 0) + 1
    if sets:
        best = max(sets, key=sets.get)
        if sets[best] >= 2:
            look['set'] = best
    look['sig'] = hashlib.md5(json.dumps(look, sort_keys=True, default=str).encode()).hexdigest()[:8]
    ch._look_cache = (key, look)
    if getattr(ch, '_look_sent', None) is None:
        ch._look_sent = look['sig']      # what the map payloads are showing everyone
    return look


# ---------------------------------------------------------------- telling the 3D clients
async def touch(ch):
    """Tell the 3D clients around this character if their look changed."""
    if not hasattr(ch, 'account_name') and not hasattr(ch, 'connection'):
        return
    before = getattr(ch, '_look_sent', None)
    look = look_of(ch)
    if before is None or before == look['sig']:
        return                       # unchanged, or never shown yet (the map payloads carry it)
    ch._look_sent = look['sig']
    world = getattr(ch, 'world', None)
    wm = getattr(world, 'web_map', None) if world else None
    room = getattr(ch, 'room', None)
    if wm is not None and room is not None and hasattr(wm, 'relay_look'):
        try:
            await wm.relay_look(ch, look)
        except Exception:
            pass


async def after_command(player):
    """After any command: the player, and anyone in the room (a disarm, a theft)."""
    room = getattr(player, 'room', None)
    people = [player] + [c for c in (getattr(room, 'characters', []) or []) if c is not player and hasattr(c, 'account_name')]
    for ch in people:
        await touch(ch)
