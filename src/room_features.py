"""What a room's text says stands in it, for the 3D client to draw (shared/roomgen.js places them,
world3d/terrain-features.js builds them): standing stones, altars, stakes, skull poles, cairns,
banners, cages, graves, braziers, wells, statues...

A room's look (room_looks.py) says what kind of place it is; its features say what is in it. Each
feature is read from the name and description by the word table FEATURES: how many there are
(the mentions, up to a cap) and, said near it, a colour ("a stone wrapped in a collar of red-dyed
wool": a standing stone with a red band). A feature named in the room's own name ("The First
Altar", "At The Slaughter Stone") is its centrepiece: drawn larger, near the middle.

    features(name, description) -> [{'k': 'altar', 'n': 1, 'main': True}, {'k': 'standing_stone', 'n': 2, 'c': 'red'}, ...]

Nothing is saved: features are read at load (World.load -> annotate) and sent in the zone map.
"""
import re

# key, words (regex), most to draw, where: 'edge' (along the walls), 'centre' (in the open),
# 'scatter' (small, anywhere), 'ground' (flat on the floor). First match per word wins; a key may
# appear once per room.
FEATURES = [
    # a stone that stands: named so, or "a broad stone" that stands, leans, rises, is carved... (never
    # "the stone floor", "a stone bridge")
    ('standing_stone', r'standing stones?|monoliths?|menhirs?|megaliths?|stone circle|ring of (?:grey |great |tall )?stones|'
                       r'corner stone|uprights?|dolmens?|the stones (?:here|above|lean|seem|crowd)|'
                       r'(?:a|the|tall|broad|lopsided|weathered|carved|great|grand|squat|nearest|fire-blackened) stone'
                       r'(?=\s+(?:stands?|leans?|rises?|wrapped|carved|crowned|cut|stained|tilts?|split|plastered|squats?|shaped))|'
                       # ("the tall stone." but not "rain strikes the stone.")
                       r'(?:tall|broad|lopsided|weathered|carved|great|grand|squat|nearest|fire-blackened) stone(?=[,.;])', 4, 'edge'),
    ('altar', r'altars?|offering stones?|slaughter stone|sacrificial stones?', 2, 'centre'),
    ('statue', r'statues?|idols?|effig(?:y|ies)|carved figures?|hunched old man|plinths?|monuments?\b|memorial stones?', 2, 'centre'),
    ('obelisk', r'obelisks?', 1, 'centre'),
    ('pillar', r'pillars?|columns?|colonnades?', 4, 'edge'),
    # the wooden legs a dock or a jetty stands on (under the dock at New Thalos, four of them)
    ('piling', r'pilings?|pylons?|piers? posts?', 4, 'centre'),
    ('well', r'\b(?:a|the|an old|stone|deep|village|town) well\b|\b(?:a|the|village|town|iron) pump\b', 1, 'centre'),
    ('fountain', r'fountains?', 1, 'centre'),
    ('brazier', r'braziers?|fire ?pits?|campfires?|camp fires?|bonfires?|firepits?|hearths?|ring of (?:cold |grey )?ash(?:es)?|cook ?fires?|fireplaces?|circle of (?:blackened |fire-blackened )?stones', 2, 'centre'),
    ('tent', r'tents?|pavilions?|yurts?|lean-tos?|(?:market |ramshackle |traders\' )stalls?', 3, 'edge'),
    ('cage', r'cages?|gibbets?', 2, 'edge'),
    ('stake', r'stakes?|palisades?|spikes? (?:of wood|driven)', 5, 'edge'),
    ('pole', r'\bpoles?\b|totems?|totem poles?', 3, 'edge'),
    ('banner', r'banners?|pennants?|flags?|hides? (?:hang|hung|are pegged|pegged)|hung with (?:hides|skins|tanned)|tapestr(?:y|ies)', 4, 'edge'),
    ('cairn', r'cairns?|piles? of stones?|heaped stones', 4, 'scatter'),
    ('skull', r'skulls?', 4, 'scatter'),
    ('bones', r'bones?|ribcages?|\bribs\b|skeletons?|skeletal hands|carcass(?:es)?|corpses (?:drag|lie|litter|rise)', 5, 'scatter'),
    ('grave', r'graves?\b|gravestones?|tombstones?|headstones?|burial mounds?|grave ?markers?', 5, 'edge'),
    ('coffin', r'coffins?|sarcophag(?:us|i)', 3, 'edge'),
    ('candle', r'candles?|tapers?', 4, 'scatter'),
    ('torch', r'torches?|sconces?', 3, 'edge'),
    ('lantern', r'lanterns?|lamps?(?!light)', 3, 'edge'),
    ('drum', r'drums?\b', 1, 'centre'),
    ('throne', r'thrones?|high seat', 1, 'centre'),
    ('table', r'tables?|desks?|trestles?|workbenches?', 2, 'centre'),
    ('bench', r'benches|\bbench\b|pews?', 3, 'edge'),
    ('shelf', r'shelves|shelf|bookcases?|bookshelves', 3, 'edge'),
    # (not a flower bed, a river bed, "beds of roses")
    ('bed', r'(?<!flower )(?<!river )(?<!garden )(?<!stream )(?<!moss )(?<!reed )(?<!sea )(?<!cart )beds?\b'
            r'(?!\s+of\s+(?:\w+\s+){0,2}?(?:roses|lilies|flowers|herbs|lavender|sage|moss|reeds|ferns|leaves|kelp|coral|anemones|tulips|thyme|mint|gravel|sand|silt|stones|pebbles|rock|mud|shingle))'
            r'|cots?\b|bunks?|pallets?\b|straw pallets?', 3, 'edge'),
    ('chest', r'chests?\b|coffers?|strongbox(?:es)?', 3, 'edge'),
    ('barrel', r'barrels?|kegs?|casks?|vats?', 4, 'edge'),
    ('crate', r'crates?|sacks?|bales?', 4, 'edge'),
    ('weapons', r'weapon ?racks?|racks? of (?:\w+ )?(?:spears|swords|weapons|blades)|armou?ry|rusted blades|broken spears|cracked shields|chipped weapons|stolen weapons', 2, 'edge'),
    ('rubble', r'rubble|collapsed|tumbled (?:stones|blocks)|fallen masonry|broken (?:walls?|columns?|pillars?)|ruins?\b', 4, 'scatter'),
    ('dead_tree', r'dead trees?|withered trees?|leafless trees?|blasted trees?|dead (?:oak|ash|elm)|bare (?:thorn )?trees?|thorn trees?|black trees|fallen trunks?|fallen logs?', 3, 'scatter'),
    ('mushroom', r'mushrooms?|toadstools?|fung(?:us|i)', 4, 'scatter'),
    ('flowers', r'wildflowers?|flowers?|blossoms?|blooms?', 4, 'scatter'),
    ('fence', r'fences?|fenced|railings?', 3, 'edge'),
    ('rug', r'rugs?|carpets?(?!\s+(?:of|the|every|its|their)\b)', 1, 'ground'),     # (not "petals carpet the paths")
    ('blood', r'blood(?:stain|stained|y)?|gore|dark stains?|stained (?:dark|black)', 3, 'ground'),
    ('ash', r'scorched|blackened|soot|charred|ash\b|ashes\b', 2, 'ground'),
    ('stake_holes', r'holes of (?:old )?stakes|post ?holes', 1, 'ground'),
    ('crystal', r'crystals?|geodes?', 4, 'scatter'),
    ('chains', r'chains?\b|manacles?|shackles?|iron rings?|rings? set in the (?:floor|wall)', 3, 'edge'),
    # the scenery a room names that its look alone does not draw (the art audit's bare rooms)
    ('gate', r'\b(?:tall|great|high|heavy|huge|iron|black|ancient|massive|bronze|wooden|stone|double|main) gates?\b(?! (?:lies|leads))|\bgates? (?:stands?|rises?|fills?|looms?|of [a-z]+)|gateways?|great archway|portcullis', 1, 'edge'),
    ('tree', r'fruit trees?|(?:apple|pear|cherry|plum|olive|fig|orange|lemon|almond) trees?|orchard|'
             r'\b(?:a|the) (?:lone|single|great|huge|old|tall|gnarled|twisted|ancient|large|mighty|towering) (?:oak|tree|pine|elm|willow|yew|beech|cedar)\b(?! (?:doors?|tables?|chests?|beams?|panels?|benches|bench|chairs?|shutters?|planks?|boards?))|'
             r'\b(?:pines|spruces|firs|larches|alders|birches|willows?)\b|forest\'s edge|edge of the forest', 3, 'scatter'),
    ('reeds', r'\breeds?\b|bulrushes|\brushes\b|cattails?|sedges?', 3, 'scatter'),
    ('roots', r'\broots\b|tree roots|vines\b|creepers|tendrils|(?<!incense )(?<!joss )\bsticks\b', 3, 'edge'),
    ('boat', r'rowboats?|row-boats?|\bskiffs?\b|canoes?|longboats?|fishing boats?|(?:a|an|the|old|small|upturned|beached|moored|wrecked) boats?\b|boathouse|slipways?|(?:a|the|wooden|log) raft\b|boats (?:bob|rock|lie|are moored)|wooden docks|\bwharf\b|\bjett(?:y|ies)\b', 1, 'edge'),
    ('mist', r'\bmists?\b|\bfog\b|\bhaze\b|\bvapou?rs?\b|\bsteam\b|\bsmoke (?:hangs|drifts|curls|fills|wreathes)|wreathed in smoke', 1, 'ground'),
    ('ice', r'icicles?|(?:shards?|spires?|pillars?|columns?|blocks?|formations?|walls?|sheets?) of ice|ice (?:pillars?|columns?|formations?|spires?|shards?|crystals?)', 3, 'scatter'),
    ('flames', r'\bflames?\b|roaring fire|crackling fire|\bfires? (?:burns?|roars?|crackles?|blazes?|smoulders?)|fireplace is going|\bblaz(?:e|ing)\b|lava|magma', 2, 'scatter'),
    ('mirror', r'mirrors?|looking.glass|walls of (?:fused |green |black |smooth )*glass|glass walls|sheets of glass', 4, 'edge'),
    ('bell', r'\bbells?\b|belfry', 1, 'centre'),
    ('waterfall', r'waterfalls?|cascades? (?:down|of water|over)|falls of', 1, 'edge'),
]
COLOURS = {'red': 'red', 'crimson': 'red', 'scarlet': 'red', 'blood-red': 'red', 'black': 'black', 'white': 'white',
           'gold': 'gold', 'golden': 'gold', 'gilded': 'gold', 'silver': 'silver', 'green': 'green', 'blue': 'blue',
           'blue-green': 'teal', 'yellow': 'yellow', 'ochre': 'yellow', 'purple': 'purple', 'bone': 'white'}
_COLOUR_RE = re.compile(r'\b(' + '|'.join(sorted(COLOURS, key=len, reverse=True)) + r')\b', re.I)
_DESTINATION = re.compile(r'\b(?:to|towards?|into|for)\s+(?:the\s+)?(?:[A-Z]\w*\s+){0,3}$')
_RES = [(k, re.compile(r'\b(?:' + pat + r')', re.I), cap, where) for k, pat, cap, where in FEATURES]
# said in the plural, these are still one patch, not many
UNCOUNTED = {'ash', 'blood', 'rubble', 'stake_holes', 'chains', 'flowers', 'mushroom'}
WHERE = {k: where for k, _p, _c, where in FEATURES}


def _colour_near(text, start, end):
    """A colour said close to a mention, in the same sentence: just before it ("a red banner") or
    just after ("a stone wrapped in a collar of red-dyed wool"); the nearest wins."""
    s0 = max(text.rfind('.', 0, start), text.rfind(';', 0, start), start - 30) + 1
    e1 = min([i for i in (text.find('.', end), text.find(';', end)) if i >= 0] + [end + 40])
    best = None
    for m in _COLOUR_RE.finditer(text, s0, e1):
        d = start - m.end() if m.end() <= start else m.start() - end
        if best is None or d < best[0]:
            best = (d, m.group(1).lower())
    return COLOURS[best[1]] if best else None


def features(name, description):
    """The features a room's words name, in the order of FEATURES."""
    name = name or ''
    desc = ' '.join(str(description or '').split())
    text = f'{name}. {desc}'
    out, said = [], {}
    for key, rx, cap, _where in _RES:
        # a place named as where a way leads ("a track leads east to the Third Altar") is the next
        # room's, not this one's
        hits = [h for h in rx.finditer(text) if not _DESTINATION.search(text[max(0, h.start() - 40):h.start()])]
        if not hits:
            continue
        # "braziers smoulder at every corner": more than one, though said once
        n = len(hits) + any(h.group(0).lower().endswith('s') and key not in UNCOUNTED for h in hits)
        said[key] = len(hits)
        f = {'k': key, 'n': max(1, min(cap, n))}
        if rx.search(name):
            f['main'] = True
        c = None
        for h in hits:
            c = _colour_near(text, h.start(), h.end())
            if c:
                break
        if c:
            f['c'] = c
        out.append(f)
    # an altar "like a low table of rough rock" is not a table as well
    keys = {f['k'] for f in out}
    if 'altar' in keys:
        out = [f for f in out if f['k'] != 'table']
    # "the holes of old stakes": the holes, not a stake
    if 'stake_holes' in keys:
        out = [f for f in out if not (f['k'] == 'stake' and said['stake'] == 1)]
    return out


def annotate(world):
    """Read every room's features once (World.load): room.features."""
    n = 0
    for room in world.rooms.values():
        room.features = features(getattr(room, 'name', ''), getattr(room, 'description', ''))
        n += bool(room.features)
    return n
