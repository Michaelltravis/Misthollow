# Art sources (Phase A style lock)

Style lock: **Foozle "Lucifer" collection** (dark fantasy, 32px tiles, 48px four-direction
actors, matching UI/effects/items). Every adopted pack is CC0 (Creative Commons Zero 1.0);
each pack's `Readme.txt` with the license statement is committed beside its PNGs under
`src/web_isometric/art/<pack>/`. Aseprite sources and the 10K-pixel mockups are not committed.
Tooling: `tools/art_manifest.py` scans the folder and writes `src/web_isometric/art/manifest.json`.

| Pack | Covers | Source |
|---|---|---|
| lucifer-exterior-tileset | dark forest, graveyard, castle walls, dirt roads, banners (32px atlas 40x8) | https://foozlecc.itch.io/lucifer-exterior-tileset |
| lucifer-dungeon-tileset | stone dungeon, carpets, doors, torches (21x8) | https://foozlecc.itch.io/lucifer-dungeon-tileset |
| lucifer-lava-dungeon-tileset | lava halls, animated doors, flags, torches | https://foozlecc.itch.io/lucifer-lava-dungeon-tileset |
| cave-and-desert-tileset | cave and desert tiles, palms, torches, hazards | https://foozlecc.itch.io/cave-and-desert-tileset |
| green-valley-tileset (16px) | grassland accents, reserve | https://foozlecc.itch.io/green-valley-tileset |
| lucifer-warrior / necromancer / sorceress | hero sheets: idle, walk/run, 3 attacks, hurt, death, 4 directions | https://foozlecc.itch.io/lucifer-warrior (and -necromancer, -sorceress) |
| legend-main-character (64px, reserve) | one hero, 25+ animations, 3 colours; different artist, kept as reserve | https://foozlecc.itch.io/legend-main-character |
| lucifer-skeleton-{grunt,hunter}-enemy, -{king,ancient}-boss | undead | https://foozlecc.itch.io/lucifer-skeleton-grunt-enemy etc. |
| lucifer-goblin-{slinger,berserker}-enemy, -{rider,beast}-boss | goblins | https://foozlecc.itch.io/lucifer-goblin-slinger-enemy etc. |
| lucifer-cultist-enemy, lucifer-possessed-enemy | humanoid casters / possessed | https://foozlecc.itch.io/lucifer-cultist-enemy |
| lucifer-rpg-ui, rpg-ui-set-1 | HUD, boss bars, buttons, icons, fonts, login/menu backgrounds | https://foozlecc.itch.io/lucifer-rpg-ui |
| lucifer-effects, pixel-magic-sprite-effects | hit, slash, magic FX strips | https://foozlecc.itch.io/lucifer-effects |
| lucifer-equipment, lucifer-pickups | item/equipment icons, pickups | https://foozlecc.itch.io/lucifer-equipment |
| trap-pack | 30 animated traps | https://foozlecc.itch.io/trap-pack |

Evaluated, not adopted: Kenney Tiny Town / Tiny Dungeon (CC0, 16px; bright cartoon style clashes
with Lucifer), Pixel Frog Tiny Swords (custom licence, not CC0, 64px bright style),
0x72 DungeonTileset II (CC0, 16px, no attack animations). Failed to fetch: lucifer-desert-tileset
(retry later; the world has one desert room).

Kept from before: the procedural painterly ground (`painter.js`) stays as the base layer; Lucifer
tiles are used for walls, props, doors and decor on top of it. LPC paperdolls and DCSS creature
sprites remain as fallbacks until every class and mob archetype is mapped (see `roles.json`).

## Decisions after the search for beast and extra hero sheets (2026-10-07)
- **Beasts and non-humanoid monsters keep the CC0 DCSS creature art.** No CC0 top-down animal
  pack with four-direction animation exists in a matching style; the candidates found were
  CC-BY (Reemax giant spider, LPC rat/cat/dog, AntumDeluge rodents), paid (PidrouDays bear), or
  16px cartoon (Tiny Creatures). DCSS art already sits inside the actor pipeline with outlines
  and scale rules, and the style-01 critic did not flag it.
- **Five classes stay recolours of the three Lucifer silhouettes** (warrior, sorceress,
  necromancer) until a sheet in the same style is commissioned. CC0 alternatives found were
  16px idle-only (PixeLike) or AI-generated / non-CC0 (Pixel Heroes, Tiny Questers).
  Recolours are distinct at a glance (see `class-lineup.png`); the gap is silhouette variety.

# 3D client art (`/play`, docs/REBUILD_PLAN.md engine section)

Style: stylised low-poly 3D. Every pack is **CC0 1.0**; each pack's licence file is copied to
`src/web_isometric/art3d/licenses/`. `tools/art3d/fetch.sh` downloads the sources (not
committed) and `tools/art3d/build.mjs` builds the optimised files in `src/web_isometric/art3d/`:
characters without animations (~150 KB each), one shared animation file for the common
41-joint rig (`chars/rig_anims.glb`, 68 clips), and kits (many props in one file, textures
stored once, meshopt-compressed).

| Pack | Author | Covers | Source |
|---|---|---|---|
| KayKit Character Pack: Adventurers 1.0 | Kay Lousberg | Knight, Barbarian, Mage, Rogue, Rogue (hooded), weapons/shields/hats; the pack's painted shields, painted two-handed sword and quiver (`Assets/gltf`); 75 animations | https://kaylousberg.itch.io/kaykit-adventurers (mirror: github.com/KayKit-Game-Assets/KayKit-Character-Pack-Adventures-1.0) |
| KayKit Character Pack: Skeletons 1.0 | Kay Lousberg | skeleton warrior, mage, rogue, minion; 95 animations (superset, same rig) | https://kaylousberg.itch.io/kaykit-skeletons (mirror: github.com/KayKit-Game-Assets/KayKit-Character-Pack-Skeletons-1.0) |
| KayKit Dungeon Remastered 1.0 | Kay Lousberg | walls, floors, pillars, torches, barrels, crates, chests, rubble, stairs (37 used of 200+) | https://kaylousberg.itch.io/kaykit-dungeon-remastered (mirror: github.com/KayKit-Game-Assets/KayKit-Dungeon-Remastered-1.0) |
| Stylized Nature MegaKit (standard) | Quaternius | trees, pines, dead trees, bushes, ferns, grass, flowers, rocks, pebbles (26 used) | https://opengameart.org/content/stylized-nature-megakit, https://quaternius.com |

| Cute Animated Monsters (Aug 2020) | Quaternius | 21 monsters: bat, bee, crab, cyclops, demons, ghost, skull, treant, mushroom, yeti, panda, dragon, alien, cthulhu… (FBX + textures) | https://opengameart.org/content/textured-cute-monster-pack |
| Animal Pack Vol.2 | Quaternius | wolf, dog, cat, eagle, piranha (FBX) | https://opengameart.org/content/animated-animales-low-poly |
| Animals Pack | Quaternius | fox, fish, bird, chick, whale (FBX) | https://opengameart.org/content/5-low-poly-animals |
| Farm Animals | Quaternius | cow, horse, zebra, llama, pig, pug, sheep (FBX) | https://opengameart.org/content/lowpoly-animated-farm-animal-pack |
| Animated Monster Pack | Quaternius | dragon (young dragons), bat, slime (FBX) | https://opengameart.org/content/lowpoly-animated-monsters |
| Ultimate Animated Character Pack (Nov 2019) | Quaternius | goblins and zombies, male and female (FBX; the pack's chibi townsfolk with black faces don't fit the KayKit look and are left out) | https://opengameart.org/content/animated-characters-pack |

| KayKit Medieval Hexagon 1.0 | Kay Lousberg | town houses, tavern, smithy, church, market, towers, wells, town walls, street props (64 used) | https://kaylousberg.itch.io/kaykit-medieval-hexagon (mirror: github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0) |
| KayKit Furniture Bits 1.0 | Kay Lousberg | beds, tables, chairs, shelves, cabinets, rugs, lamps, books, pictures (all 53) | https://kaylousberg.itch.io/furniture-bits (mirror: github.com/KayKit-Game-Assets/KayKit-Furniture-Bits-1.0) |
| KayKit Halloween Bits 1.0 | Kay Lousberg | graves, gravestones, fences, lanterns, benches, shrines, dead trees (all 63) | https://kaylousberg.itch.io/halloween-bits (mirror: github.com/KayKit-Game-Assets/KayKit-Halloween-Bits-1.0) |

Heroes are dressed from the equipment kit (`chars/equip.glb` + `equip.json`, the `equip` job in
`build.mjs`): every body part and piece of the five adventurers on one rig, their four textures
merged into one palette of colour ramps (`tools/art3d/ramps.json` names each swatch's role and adds
ramps for materials, cloth colours, elements, races, the classes' and the named sets' colours).
`world3d/equip.js` merges what a hero wears into one mesh; weapons the pack lacks (bow, mace, lute)
are built in code in the same style (`world3d/procgear.js`), so they need no art source.

Towns, interiors and graveyards are placed by `world3d/terrain-town.js`: houses fill empty
map cells beside streets, shopfronts (pressed to two tiles) stand where a street meets an
indoor room and are chosen by that room's name, interiors are furnished by kind (temple, shop,
tavern, bank, library, bedroom, guild, throne room, house).

Creatures (`art3d/mobs/`, 38 models, 2.6 MB) are converted from FBX by `build.mjs` with
FBX2glTF (npm `fbx2gltf`), textured, turned to face +Z (`tools/art3d/mob-yaw.json`), scaled to
1 m and listed with their clip names in `mobs/index.json`. Rats, spiders, snakes, rabbits and
slimes have no CC0 model: `world3d/proc.js` builds them from primitives. Which body a creature
gets is decided by name in `world3d/bestiary.js`. (Quaternius' newer "Ultimate Monsters" and
"Ultimate Animated Animals" are CC0 too, but their Google Drive links refuse downloads from
this environment — "quota exceeded" — so the OpenGameArt packs above are used.)

Build notes: the nature kit's COLOR_0 (wind masks for Quaternius' own shader) is dropped
because glTF multiplies it into the colour; its bushes use the twisted tree's autumn-red leaf
atlas, which the build remixes to green; normal maps are dropped and textures resized to 512.
Those two packs' FBX colours come through linearised twice; the build undoes one (`gamma`), and
renames their clips to the names `assets.js` maps (dropping the rest). Creatures normally get a
body built in code (kin.js); a `prefer`red bestiary entry keeps the pack model instead (goblins,
zombies, bats, young dragons, slimes).
Models we make ourselves in Blender: see STYLE3D.md (art3d/bodies).

Generated with Tripo (https://www.tripo3d.ai, through its API, developers.tripo3d.ai): **not CC0**.
These are ours under Tripo's terms of service for paid API use; check those terms before a
commercial release. Each piece has a spec in `tools/art3d/tripo/` (the prompts and settings),
the model Tripo returned beside it (`<name>.glb`, committed so the kit builds from a fresh clone
without asking Tripo again) and the log of its tasks and credits (`<name>.run.json`).
`tools/art3d/tripo.mjs` makes them; `blender/models/tripo_prop.py` fits each to the KayKit rig and
repaints it onto the equipment kit's palette, and `build.mjs equip` takes it in.

| Piece | Made | Covers | Spec |
|---|---|---|---|
| Tripo_Staff_Crystal | 2026-10-20, concept by `banana`, model by `P2-20260801`, 120 credits | the mage's crystal staff (`gearlook.js` STAFF_PIECE), in place of the one `procgear.js` builds | `tools/art3d/tripo/staff_crystal.json` |
Another CC0 candidate: isaiah658's "50+ Monsters Pack 3D" (OpenGameArt, static OBJ, would need
rigging in Blender).
