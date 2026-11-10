# The world's spine

The owner (9 November 2026): "the overall world needs to be cohesive and engaging. I want an
amazing well thought out world!" This is the design that answers it: what the world is, the nine
regions it is made of, the road a hero walks from level 1 to 70, and what each of the 122 zones
has to become to belong. **It is a proposal.** The premise, the region names and every rename
are the owner's to change; nothing in the world's files has been renamed or re-levelled.

- The regions as data: `world/regions.json`, written by `tools/world/regions_ledger.py` (which
  also checks that every zone is in exactly one region and prints the ledger at the end of this
  page).
- What was measured: every zone file in `world/zones/` (rooms, creatures and their levels, the
  exits that cross from one zone to another).

## 1. What is wrong today

The world is 122 zones and about 9,250 rooms from at least four hands: the CircleMUD stock
areas, the Bedlam atlas, the build-out that wrote the connector rooms, and the new end game.
Every room is written and every room can be reached. What it lacks is a reason to be one place.

1. **Nothing in the world is about the game's own name.** The title screen promises a world:
   "Where the mist remembers every name", lanterns that burn blue where the dead have walked, a
   hollow that was a lake, temple bells that call the lost home, dragons beyond the Ashlands. A
   player who logs in meets none of it. The first zone's rooms joke about themselves ("couldn't
   they hire someone to clean this place? What will the newbies think?").
2. **Half the world is one level band.** By the median level of a zone's creatures: 50 zones and
   4,257 rooms (46% of the world) sit at levels 10-19. Levels 30-39 have 9 zones and 380 rooms;
   levels 50-59 have 4 zones. A hero has fifty places to be at level 15 and almost nowhere at 35.
3. **Distance does not mean danger.** Counting zones from the city: the Necropolis of Eternal
   Night (level 31) and the Dragon's Domain (level 35) are two zones from the Temple. Mira
   Retrum I (level 3) is three zones out, past level-9 country. The Dwarven Mines of Khaz-Durum
   (level 13) are five zones out, behind a level-20 kingdom.
4. **The road is the only geography.** The Trade Road is 574 rooms and touches 25 zones: nearly
   everything is "somewhere off the road". No place is north, or the coast, or the mountains, in
   any way the game says or shows.
5. **The names come from everywhere.** Builder's leftovers: MiNar I, Badlands II, Durmandel I
   and II, Lost Crypt I and II, High Tower Of Magic I and II, Castle Of The Apocalypse I and
   II, "Aredrel Dwarven", Isle of Lag, Fameland. And names from other people's books and games,
   which a game that wants players cannot keep: Moria, Gondor, Elvandar, the Tombs of Atuan,
   Salem's Lot, Hommlet, Lloth and the drow, Mount Olympus, Eden.
6. **Twelve zones have no creatures of their own** in their zone files (a population file may
   add some): Fameland, Hommlet, the Cathedral, the Outcast Fortress (102 rooms), Castle of the
   Apocalypse I, High Tower II, World of Chaos (90), Ancalador, Ghenna (86), the Haunted House,
   the School House, the Wall, the Vineyard.
7. **The end game is the one part with a line through it**: the Eastern Highlands, the Sunken
   Coast, the Ashlands, then five zones to the Shattered Throne at level 70. It is 332 rooms of
   9,250, at the far end of a road nothing points down.
8. **`world/WORLD_MAP.md` describes a world that no longer exists** (16 zones around "Midgaard").

## 2. The premise

One paragraph, built from the lines the title screen already speaks:

> There was a kingdom here, and a lake at its heart. When the Throne was shattered the lake
> emptied into the sea in a night and left the Hollow, and out of the Hollow came the mist. The
> mist does not kill. It takes names: of places first, then of people, and what has no name is
> forgotten and then is gone. Garathorm stands because its lanterns burn and its temple bells
> ring every name in the city at dusk. A lantern lit holds the mist back; a lantern that burns
> blue says the nameless dead have walked there. You are a traveller who did not turn back: you
> carry a lantern out along the old roads, relight what has gone dark, and learn who broke the
> Throne, and whether a name the mist has taken can be given back.

What this gives the game, without a new system:

- **A reason for the city**: the one place fully lit. The Temple you wake in after dying is where
  the bells called your name home.
- **A reason for death's cost**: you lose a little of what you were (the experience), never your
  name.
- **A reason to travel**: every region has lanterns gone dark and a reason they went.
- **One enemy with many faces**: each region's great villain made a different bargain with the
  mist. The vampire lord Ostragoth kept his name by taking other people's. The Drowned King
  Nerathis kept his by drowning with it. The Horsemen in the Castle of the Apocalypse are what
  the kingdom's last four lords became. Morkai is a city that forgot it died.
- **A way to see it**: the mist is weather the client already draws. Thick at a region's dark
  edge, blue lantern-light where the dead walk, clear inside a lit lantern's circle.

## 3. Pillars: what makes it feel like one world

1. **Every zone answers three questions**: what was this before the mist, what holds it now, and
   what does a lantern-bearer do here. A zone that cannot answer is rewritten, merged or cut.
2. **The lantern is the world's one sign.** Lantern posts line the roads: lit near the city, dark
   further out. A lit post is safety (a waypoint, a place to rest); a blue one is a warning.
   The player's own light (the game already has one) is a lantern.
3. **Regions, not a road.** Nine regions, each with its own light, stone, weather, music and
   creatures, a level band, a way in from its neighbours and one great villain. The game says
   which you are in (the banner, the map), and you can see where one ends.
4. **Further is deeper.** A region's levels rise with distance from the city, and the regions
   themselves are ordered. Nothing far above a region's band sits on its road.
5. **Names from this world only.** No builder's numerals, no jokes about the game, nothing from
   another author's world.
6. **One voice.** Plain, a little grave, never winking at the player. The room text audit
   (`docs/world/room_text_audit.md`) is the tool; the Proving Halls are the first rewrite.

## 4. The nine regions

| Region | Levels | What it is | Its light and look | Its great villain |
|---|---|---|---|---|
| **The Lantern Vale** | 1-10 | Garathorm and the lit country round it: the city, its wall and cathedral, the halls under the Temple, the fields, the first woods | Warm lantern gold, clear air, bells | The Sewer King below; the Goblin King in the fields |
| **The Marches** | 8-20 | The old road and the keeps raised to guard it, half of them fallen: villages, castles, a wizards' tower, the Badlands | Grey stone, long evening light, mist in the ditches | **Ostragoth**, who keeps his name by taking others' |
| **The Greenreach** | 10-25 | The old forest to the west: elves above, the Umbral City below, ogres, spiders, a baron's fief | Green-gold under leaves, faerie fire below | The Spider Queen; the High Priestess below |
| **The Stonemarch** | 12-30 | The mountains and the dwarf-halls dug too deep: mines, a goblin warren, giants on the passes | Cold blue rock, forge-red in the deeps | The Mazekeeper; what the dwarves woke |
| **The Frostmarch** | 20-35 | The north, where the mist froze: winter wood, the Winterlands, the Frostspire | White and steel, snow that does not melt | Vyrkothas the Frost Wyrm |
| **The Sunder Sea** | 5-30 | Where the lake ran out: the desert river, New Thalos and the drowned old city, the pyramid, the isles, the sunken ruins | Sand gold and sea green, storms | Nerathis, the Drowned King |
| **The Deep Road** | 35-55 | The long way under the world: lost dwarf-holds, crypts, the orc tunnels, Morkai the dead city | Black stone, ghost-green light | Orcus's temple; Morkai itself |
| **The Sundered Reach** | 25-70 | East to the Throne, every mile of it a kingdom once: highlands, the coast, the Ashlands, and the last five zones | Ash red, then starless black | Whoever sits the Shattered Throne |
| **The Places Beyond** | 30-70 | Not on any road: the hells, the planes, the necropolis, the Castle of the Apocalypse | Each its own, all wrong | The Four Horsemen |

The client already has what the looks need: lighting moods by place (`engine.js` MOODS), a zone's
stone and light (`zone_tone.py`), weather and music. What is new is choosing them by region, so
a region reads as one country.

## 5. The road: where a hero is, level by level

| Levels | Where | How the game sends you |
|---|---|---|
| 1-5 | The Proving Halls under the Temple; the city | Sage Aldric's tutorial ends with your lantern lit |
| 3-10 | The Vale's fields and woods; the first water (the Mirrormere) | The first dark lantern post on the road |
| 8-20 | **A choice of three**: the Marches (the road and its keeps), the Greenreach (west), the Sunder Sea (south) | Three captains in the city, each with a region's opening quest |
| 12-30 | The Stonemarch, from the Marches or the Greenreach | Each region's last quest points over the passes |
| 20-35 | The Frostmarch (north, from the Stonemarch); the Sunder Sea's far isles; the Greenreach's cathedral and Warded Castle | These fill the level-30s gap, which is where the world is thinnest today |
| 25-50 | The Sundered Reach as far as the Ashlands | The city sends every hero east at 25 |
| 35-55 | The Deep Road, entered from the Badlands | The second way to 50, underground |
| 50-70 | The Reach's last five zones; Morkai; the Places Beyond | The Throne |

The changes that make the road true, in order of how much they matter:

1. **Raise the Frostmarch to 20-35.** Five zones, 266 rooms, all at 11-20 today, on the far
   side of the Stonemarch. They are the cheapest fix for the level-30s gap.
2. **Move two ways in.** The Necropolis (31) and the Dragon's Domain (35) open two zones from
   the Temple. Reach the Necropolis only through the Undercity's deep end, and the Dragon's
   Domain from the Ashlands.
3. **Order the Vale.** The Proving Halls 1-5, the fields 3-10, the Undercity's near end 5-12.
   Mira Retrum I (level 3) becomes the Mirrormere and is reached from the Vale, not past
   level-9 country.
4. **Thin the level-15 crowd by region**, not by cutting: within the Marches, the Greenreach
   and the Sunder Sea, spread each region's zones across its band (the ledger says which).

## 6. What comes first

Each step stands by itself and can be checked in the game.

1. **Regions in the game** (small, code): `world/regions.json` is read by the server; the
   banner on entering a zone names its region, and says the region's line when you cross into
   it; the map names it. **Done (9 November, the owner agreed to the nine):** `src/regions.py`,
   the zone map's `region`, `hud/regionsay.js`; checks in `tests/test_regions.py` and
   `tests/web/regions.test.mjs`. The map does not yet say a region's level band: the bands in
   section 4 are the plan, and the zones are not re-levelled to them.
2. **The renames** (the owner's list: the ledger's "rename" rows; data only, but every quest,
   help page and test that names a zone follows).
3. **The Vale rewritten as the opening hour**: the Proving Halls in the world's voice, the
   lantern in the tutorial, lantern posts on the first stretch of road, the bells at dusk.
4. **The road made true**: the Frostmarch raised, the two ways in moved, the Vale ordered
   (balance work: `tools/balance`, the population files).
5. **Region looks**: light, stone, weather and music chosen by region. **Begun (9 November):**
   each region has a slight colour cast over the whole picture (`world3d/regionlook.js`, eased in
   as a border is crossed): the Vale warm, the Frostmarch cold, the Reach ash-red. Stone,
   weather and music by region are still to do.
6. **Region by region**: people the empty zones, give each region its opening quest in the city
   and its villain's story, in the order the road runs.
7. Retire `world/WORLD_MAP.md` (the 16-zone world) in favour of this page and the atlas index.

## 7. The ledger: every zone and what the spine asks of it

"Now" is from the zone's own file: its rooms, and the median level of its creatures. "keep"
means the zone belongs as it is. Not in the world: Limbo (0), the God Rooms (12) and the
marquee quests' creature list (97).

### The Lantern Vale (levels 1-10; 16 zones, 1,129 rooms)

| Zone | Now | The spine asks |
|---|---|---|
| Garathorm Inner City (30) | 213 rooms, level 17 | keep |
| Garathorm Wall (403) | 50 rooms, no creatures of its own | keep: the watch on the wall looks out at the mist |
| Garathorm Cathedral (431) | 73 rooms, no creatures of its own | people it: priests, pilgrims, the bell-ringers (the bells that "call the lost home") |
| Garathorm School House (517) | 33 rooms, no creatures of its own | keep: no fights; where a newcomer learns what the lanterns are for |
| Garathorm Housing District (260) | 22 rooms, level 27 | keep |
| Garathorm Vineyard (418) | 3 rooms, no creatures of its own | keep |
| Newbie Zone (186) | 41 rooms, level 4 | rename: **The Proving Halls** (under the Temple); rewrite its joke rooms in the world's voice |
| The Chessboard of Garathorm (36) | 67 rooms, level 7 | keep: the city's own oddity |
| Forest of Shadows (200) | 10 rooms, level 8 | levels 5-12 |
| King's Forest (441) | 11 rooms, level 9 | keep |
| Plains (60) | 187 rooms, level 4 | levels 3-10: the first open country; the Goblin King its boss |
| The Orc Enclave (62) | 68 rooms, level 5 | levels 5-12 |
| Sewer (72) | 196 rooms, level 9 | rename: **The Undercity**; levels 5-12 near the grates, the deep end stays for 25+ |
| Tunnels of Sin (488) | 85 rooms, level 14 | keep |
| Redferne's Residence (79) | 20 rooms, level 20 | keep |
| Stable & Temple (32) | 50 rooms, level 25 | keep |

### The Marches (levels 8-20; 19 zones, 1,745 rooms)

| Zone | Now | The spine asks |
|---|---|---|
| Trade Road (408) | 574 rooms, level 14 | rename: **The Lantern Road**; a lantern post every few rooms, lit near the city, dark further out |
| Hommlet (423) | 12 rooms, no creatures of its own | rename: **Hollowmere** (was Hommlet, a published village); people it: the first village on the road |
| Welmar's Castle (150) | 58 rooms, level 13 | keep |
| Castle Catacombs (424) | 47 rooms, level 15 | keep |
| Castle Varok (458) | 84 rooms, level 19 | keep |
| Castle Of Caboon (416) | 49 rooms, level 11 | keep |
| Salem's Lot (480) | 82 rooms, level 17 | rename: **Saltmarsh Lot** or the owner's choice (was Salem's Lot, a published town) |
| Haunted House (482) | 49 rooms, no creatures of its own | people it (no creatures of its own) |
| Strange Garden (414) | 34 rooms, level 19 | keep |
| Mishrak (419) | 94 rooms, level 19 | keep |
| Phaeton's Academy (499) | 53 rooms, level 19 | keep |
| High Tower Of Magic I (25) | 98 rooms, level 16 | rename with 469: **The High Tower** (lower halls / upper halls) |
| High Tower Of Magic II (469) | 84 rooms, no creatures of its own | merge into The High Tower as its upper halls; people it (no creatures of its own) |
| Badlands II (471) | 118 rooms, level 13 | rename: **The Badlands** (drop the II) |
| Draconian Camp (502) | 55 rooms, level 18 | keep |
| Castle of Ostragoth (470) | 111 rooms, level 18 | keep: Ostragoth, the Marches' great villain (docs/world/ostragoth.md) |
| Tombs of Atuan (461) | 36 rooms, level 19 | rename: **The Nameless Tombs** (was Tombs of Atuan, a published place) |
| Necromancer Mines (518) | 52 rooms, level 17 | keep |
| Ancalador (479) | 55 rooms, no creatures of its own | people it (no creatures of its own), or fold into the Lantern Road |

### The Greenreach (levels 10-25; 14 zones, 1,338 rooms)

| Zone | Now | The spine asks |
|---|---|---|
| MiNar I (435) | 439 rooms, level 9 | rename: **The Minar Wood** (drop the I) |
| Baron Kalveh's Fief (436) | 95 rooms, level 20 | keep |
| Mount Olympus (439) | 66 rooms, level 13 | rename: **The White Mount** (was Mount Olympus); keep its white marble tone |
| Ogre Village (445) | 88 rooms, level 19 | keep |
| Mahn-Tor Keep (447) | 90 rooms, level 22 | keep |
| Arachnos (63) | 53 rooms, level 13 | keep |
| Haon-Dor (Dark) (61) | 5 rooms, level 15 | fold into Arachnos (5 rooms) as its way in |
| Elven Village (110) | 35 rooms, level 10 | keep |
| Elvandar (504) | 69 rooms, level 19 | rename: **Elvenhame** or the owner's choice (was Elvandar, a published elven city) |
| Drow City (51) | 100 rooms, level 16 | rename: **The Umbral City**; its goddess renamed (Lloth and the drow are a published setting's) |
| The Whispering Woods (270) | 19 rooms, level 31 | levels 25-35: a marquee quest zone |
| Outcast Fortress (442) | 102 rooms, no creatures of its own | people it (102 rooms, no creatures of its own): the Greenreach's outlaw hold |
| White Gold Cathedral (519) | 100 rooms, level 27 | levels 25-32: the Greenreach's capstone, with the Warded Castle |
| Warded Castle (520) | 77 rooms, level 31 | keep |

### The Stonemarch (levels 12-30; 14 zones, 962 rooms)

| Zone | Now | The spine asks |
|---|---|---|
| Mountain Range (40) | 160 rooms, level 8 | levels 10-18: the gate of the Stonemarch |
| The Three Of Swords (33) | 76 rooms, level 13 | keep |
| Rand's Tower (64) | 38 rooms, level 16 | keep |
| The Haunted Swamp (90) | 20 rooms, level 13 | keep |
| Brethrenmere (464) | 62 rooms, level 21 | keep |
| Below Moria (465) | 97 rooms, level 16 | rename: **Below the Deeping** (was Below Moria) |
| Moria Deep (467) | 22 rooms, level 24 | rename: **The Deeping Dark** (was Moria Deep) |
| Dwarven Kingdom (65) | 49 rooms, level 20 | levels 18-26 |
| The Dwarven Mines of Khaz-Durum (100) | 25 rooms, level 13 | reach it sooner: a level-13 mine five zones from the city, behind a level-20 kingdom |
| Mount Ravenmist (472) | 90 rooms, level 19 | keep |
| Stone Circle (476) | 94 rooms, level 23 | keep |
| Fire Grotto (478) | 96 rooms, level 23 | keep |
| Cave Elf Kingdom (474) | 113 rooms, level 16 | keep |
| The Goblin Warrens (235) | 20 rooms, level 17 | keep |

### The Frostmarch (levels 20-35; 5 zones, 266 rooms)

| Zone | Now | The spine asks |
|---|---|---|
| Northern Wilderness (66) | 66 rooms, level 12 | raise to 20-26: the gate of the Frostmarch |
| The Great Northern Forest (180) | 26 rooms, level 11 | raise to 22-28 |
| The Frostspire (190) | 27 rooms, level 20 | raise to 32-38: the Frostmarch's end, the Frost Wyrm |
| The Winterwood (521) | 67 rooms, level 12 | raise to 24-30 |
| The Winterlands (522) | 80 rooms, level 16 | raise to 28-34 |

### The Sunder Sea (levels 5-30; 21 zones, 1,765 rooms)

| Zone | Now | The spine asks |
|---|---|---|
| The Desert River and Caverns (50) | 105 rooms, level 8 | keep |
| Troglodyte Mines (426) | 44 rooms, level 12 | keep |
| New Thalos (54) | 285 rooms, level 12 | keep |
| Thalos (52) | 49 rooms, level 12 | keep the name with New Thalos: the old city the sea took, the new one that replaced it |
| Great Pyramid (53) | 59 rooms, level 19 | keep |
| Sea of Storms (120) | 350 rooms, level 17 | keep |
| Minos River Island (9) | 10 rooms, level 11 | keep |
| Eden (494) | 21 rooms, level 18 | rename: **The Garden Isle** (was Eden) |
| Isle of Lag (496) | 22 rooms, level 22 | rename: **The Becalmed Isle** (was Isle of Lag, a builder's joke) |
| Island Of The Dead (495) | 98 rooms, level 23 | keep |
| Morvoct (491) | 86 rooms, level 22 | keep |
| Mira Retrum I (448) | 111 rooms, level 3 | rename with 451: **The Mirrormere** (shallows / deeps); keep as the first water, levels 3-8 |
| Leper Island (449) | 80 rooms, level 11 | keep |
| Mira Retrum II (451) | 141 rooms, level 10 | merge name into The Mirrormere (deeps), levels 8-14 |
| Submerged Temple (452) | 65 rooms, level 14 | keep |
| Crater (453) | 42 rooms, level 16 | keep |
| Caverns of the Pale Man (454) | 100 rooms, level 17 | keep |
| Quickstream (415) | 22 rooms, level 9 | keep |
| Gondor Island (455) | 16 rooms, level 19 | rename: **Beacon Isle** (was Gondor Island) |
| The Sunken Ruins of Atal'narath (130) | 18 rooms, level 17 | the Hollow's own story lives here: Nerathis, the Drowned King, kept his name by drowning with it |
| The Straight Path (15) | 41 rooms, level 26 | keep: the pilgrim's road to New Thalos |

### The Deep Road (levels 35-55; 9 zones, 1,099 rooms)

| Zone | Now | The spine asks |
|---|---|---|
| Aredrel Dwarven (501) | 99 rooms, level 38 | rename: **Aredrel** (a dwarf-hold; "Aredrel Dwarven" is a builder's label) |
| Durmandel I (503) | 114 rooms, level 41 | rename with 508: **Durmandel** (the city / the keep) |
| Durmandel II (508) | 32 rooms, level 43 | merge name into Durmandel |
| Durmandel Mines I (509) | 151 rooms, level 46 | rename: **The Durmandel Mines** |
| Lost Crypt I (505) | 107 rooms, level 39 | rename with 507: **The Lost Crypt** (upper / lower) |
| Lost Crypt II (507) | 84 rooms, level 43 | merge name into The Lost Crypt |
| Orc Tunnels (512) | 450 rooms, level 50 | the Deep Road's spine (450 rooms): split its map into three stretches by level (42-50, 50-58, 58-68) |
| Orcus Temple (515) | 29 rooms, level 51 | keep |
| Morkai (514) | 33 rooms, level 64 | the Deep Road's end: Morkai, the city of the dead, level 62-68 |

### The Sundered Reach (levels 25-70; 12 zones, 332 rooms)

| Zone | Now | The spine asks |
|---|---|---|
| The Eastern Highlands (67) | 14 rooms, level 25 | the gate of the Reach, levels 25-30: every hero is sent here from the city at 25 |
| The Haunted Monastery (238) | 25 rooms, level 27 | levels 27-33 |
| The Sunken Coast (68) | 12 rooms, level 33 | levels 33-40 |
| The Sunken Temple of Nereus (240) | 25 rooms, level 44 | levels 40-46 |
| The Ashlands (69) | 12 rooms, level 45 | levels 45-50 |
| Shadowspire Citadel (245) | 30 rooms, level 49 | keep |
| The Clockwork Foundry (248) | 30 rooms, level 54 | keep |
| The Ashen Expanse (280) | 36 rooms, level 60 | keep |
| The Drowned Reliquary (285) | 36 rooms, level 62 | keep |
| The Black Observatory (290) | 36 rooms, level 64 | keep |
| Crown of Bone (295) | 36 rooms, level 66 | keep |
| The Shattered Throne (300) | 40 rooms, level 69 | keep |

### The Places Beyond (levels 30-70; 12 zones, 637 rooms)

| Zone | Now | The spine asks |
|---|---|---|
| Ghenna (481) | 86 rooms, no creatures of its own | people it (86 rooms, no creatures of its own): a hell, reached by dying badly |
| World Of Chaos (475) | 90 rooms, no creatures of its own | people it (90 rooms, no creatures of its own), or fold into the Plane of Eternal Chaos |
| The Plane of Eternal Chaos (160) | 26 rooms, level 34 | keep |
| The Dragon's Domain (80) | 5 rooms, level 35 | move its way in: a level-35 dragon two steps from the city; reach it from the Ashlands |
| The Necropolis of Eternal Night (140) | 31 rooms, level 31 | move its way in: a level-31 necropolis two steps from the Temple, through the Undercity's deep end only |
| Castle Of The Apocalypse I (457) | 44 rooms, no creatures of its own | rename with 220: **The Castle of the Apocalypse** (the gatehouse / the keep); people the gatehouse |
| Castle Of The Apocalypse II (220) | 143 rooms, level 61 | merge name into The Castle of the Apocalypse; the world's raid, level 60+ |
| Tunnel Of Sticks (210) | 101 rooms, level 25 | the castle's approach; say so at its mouth |
| Bedlam Arena (250) | 18 rooms, level 50 | keep |
| City of Ancients (429) | 46 rooms, level 22 | keep: the city before the city, levels 15-25 |
| Fameland (420) | 44 rooms, no creatures of its own | people it or cut it (44 rooms, no creatures, a builder's hall of fame) |
| The Mindflayer's Lair (73) | 3 rooms, level 22 | keep |
