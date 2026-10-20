# Rebuild plan — from first real playtest (2026-10-09)

The first real play on frostpine (not a bot, not a critic) found three things wrong. Root causes
in the code:

| complaint | cause |
|---|---|
| combat is horrible | combat resolves on a **4-second round** (`main.py` fires `combat_tick` every `TICKS_PER_SECOND * 4`; `PULSE_VIOLENCE = 2` in config is ignored). You press, then wait for the round. |
| the UI is too large | the camera zooms to **1.3× "fit one room"** (`scene-topdown.js`), so you see less than one room and a 16-px tile is ~68 px on a wide window; world labels scale with it. The HUD is sized for 1280×720. |
| movement between rooms is clunky | rooms are 24×15 tiles (crossed in ~3.5 s), exits are one-tile gaps in the wall middle, and every crossing waits on the server (pending-move lock up to 2.5 s). |

Decisions (owner): real-time action combat; the web client comes first, telnet may lag behind;
order 1 → 2 → 3 → 4. Every phase ships on its own (auto-deploy to frostpine) and is judged by
playing it, not by screenshots.

## Phase 1 — scale and readability
- Camera: zoom to a fixed world view (~34×19 tiles: the room plus its neighbours), not 1.3× one room.
- HUD ~30% smaller on wide screens; a UI-scale setting (S / M / L) remembered per browser.
- World labels (names, damage numbers, LOOT) sized in screen pixels, not world pixels.
- Underground zones (sewers, caves, crypts, mines) render as stone whatever their old sector tag;
  dark rooms say so ("too dark — hold a light"); neighbours of dark rooms are darkened too.
- Done when: a 1920-wide window shows a room and its neighbours with a HUD under ~15% of the screen.

## Phase 1 — status: shipped
Camera shows ~34×19 tiles (2.5× on a 1920 window instead of 4.25×); HUD scale (auto trims wide
windows; Settings → HUD size); smaller LOOT tag; enclosed zones (sewers, mines, crypts…) render
underground whatever their old sector tags; neighbours of dark rooms are dark; a dark room says
"hold a light". Exposed by the wider view: neighbour paintings arrive slowly (100–160 ms each,
thrown away on every room change) — solved structurally in phase 2.

## Phase 2 — movement (owner, after phase 1: "seamless walking between rooms, no room switching")
The zone is ONE map: rooms laid out on the atlas grid, openings where exits connect, walls where
they don't, one physics world, camera follows. Walking into another room's area sends the move to
the server in the background; nothing on screen rebuilds. Creatures and players stand in their
rooms' areas. Room paintings are made around the player progressively (nearest first, lower detail
far away) and kept in a bounded cache. Only a zone change (or up/down) fades.

- (superseded by the one-map design above; kept for the refusal rule) the server confirms in the
  background and only a refusal snaps you back.
- Wide openings: where two rooms connect, the shared wall is open across a third of its length.
- Faster walk; click-to-move with pathing across rooms (the minimap auto-walk, in the world).
- Done when: holding a direction through five rooms never stops the hero.

### Phase 2 — status, step 1 (shipped)
- Measured first: only 80% of in-zone exits land on the adjacent atlas cell and 7 of 59 zones lay
  out cleanly (MUD loops don't close), so a literal one-map-per-zone would break one exit in five.
  The world is therefore stitched AROUND THE PLAYER: every room is placed next to the one it
  connects to as you go, so every exit you walk through is seamless.
- Entering a room reuses the painting already made for the neighbour view (8 ms instead of
  100–160 ms of repaint at every crossing).
- Creatures seen in a neighbouring room stand on the slot they'll use once you walk in (they
  used to jump).
- Openings are 7 tiles on the long walls and 5 on the short ones (were 3), with clear lanes to
  match; all 3012 rooms pass `tools/qc_platformer_rooms.js`.
- Measured and ruled out: the server answers moves instantly (telnet and the websocket bridge);
  the 9 s crossings seen in headless tests are the test machine's ~1 fps software renderer.
- Owner after step 1: "crossing still feels like switching rooms".

### Phase 2 — status, step 2: optimistic crossing (shipped)
- The move is no longer sent at the doorway. The hero walks on through the opening; the moment
  they leave the room's rectangle into a laid-out neighbour in the same zone, the client switches
  rooms itself (atlas layout + the last payload's creatures, ~5–10 ms when the neighbour is
  already painted) and sends the move in the background.
- Payloads that still place you in the room you just left are ignored while the move is in
  flight; the server's confirmation just clears the flag.
- Only an explicit refusal from the server (or 30 s of silence) puts you back, just inside the
  edge. A short undo timer was tried and removed: on a slow confirmation it undid the switch,
  the hero crossed again and the server moved two rooms.
- Kept on the server path: closed/locked doors (opening them), zone changes, up/down, combat
  (you're held inside the room with "Flee to escape").


## Phase 3 — real-time action combat
- Server: replace round resolution for web players with per-action resolution — an attack is a
  request resolved within ~150 ms with its own swing time and cooldown; abilities keep their
  costs and get cooldowns. Mob AI ticks fast (~250 ms) and uses its existing intents as timed
  attacks with a wind-up you can see and leave.
- Client: every press swings immediately (prediction), hits land on the server's answer; floor
  telegraphs for mob attacks you dodge by moving; brace / stagger / perfect strike / interrupt
  become timing on actions, not rounds.
- Telnet keeps the old round loop until it is ported (owner: web first).
- Done when: a fight is decided by what you press and where you stand, second to second.

## Phase 4 — feel
- Hit-stop, knockback, impact sounds, death and respawn flow, then a playtest by the owner.

## Engine rebuild — a 3D client (owner, 2026-10-09: "still feels bad, rethink the engine")
Owner's verdict after Phase 2: stops at room edges, the screen jumps on crossing, walking feels
poor, the game is choppy. Choice: **new 3D engine + new art**, all-in (no stop-gap patching of
the Phaser client; it stays at `/platformer` until `/play` replaces it).

Why patching could not fix it (research, 2026-10-09): an unconditional clamp
(`scene-topdown.js:5413`) pins the hero inside the room so the seamless crossing almost never
ran; every crossing rebuilds the world at a new origin and evicts neighbour paintings
(`world-peek.js:179`); the server answers moves in text only and sends two full payloads of
every explored room per step.

Design: one continuous 3D world per zone; the client owns the hero's position and tells the
server which room it entered (`webmove <from> <to>`, structured `move_result`); per-zone layout
from the server (`/zonemap`); the DOM HUD (`ui.js`) is kept. Renderer: Three.js 0.185.1
vendored in `src/web_isometric/vendor/three/` (ES modules + import map, no build step); art:
CC0 low-poly (KayKit, Quaternius) — see `docs/art/SOURCES.md`.

| milestone | what | status |
|---|---|---|
| M0 | look and engine spike (now `/play?demo`) — four real room layouts (glade, brook, crypt, hall) stitched into one world, a knight on WASD/click with run/attack animations, skeletons, sun + shadows, torch lights, fog, bloom, see-through walls, F3 perf overlay | shipped; look approved (owner: "wow this looks awesome"; RTX 4070: 144 fps, 6.9 ms) |
| M1 | seamless world on real zones: `/zonemap`, terrain builders per theme, controller with A*, `webmove`, doors, passages, zone changes, login + HUD | **M1a shipped**; M1b shipped (monsters, towns and interiors, inventory, character sheet) |
| M2 | living world: class heroes, mob models, NPCs, items, other players' positions | |
| M3 | combat in 3D, then Phase 3 real-time combat | **combat v2 ready for the owner's test** (see below): events, reach, timing, wind-ups |
| M4 | polish, switch-over, retire the Phaser client | **2D clients retired** (Push 15): `/platformer`, `/2d` and `/iso` redirect to `/play`; the five scripts `/play` shared moved to `src/web_isometric/shared/` |

M0 notes: all URLs under `/v/<commit>/` are immutable (served gzip, `web_map.py`
`static_3d`), so a deploy never needs a hard refresh. Kit models are baked into float
geometry before instancing (the optimiser's quantised positions clamp at 1 m otherwise).
Headless test here: holding S walks the knight from the glade into the crypt at constant speed
across the room boundary (`z = 15`), no stop; ~110 draw calls, ~450k triangles with four rooms
in view. Smoothness and FPS are for the owner's Mac (F3 → "Copy perf report").

### M1a — the real game in 3D at `/play` (2026-10-09)
Owner: "you can redo the HUD to match the new 3d format" — `/play` has its own page and HUD;
the 2D client and its HUD stay at `/platformer`.

- Server: `/zonemap?zone=N|vnum=V` (`map_system.build_zonemap`: per-zone layout, up/down
  levels as islands, every exit `open` / `passage` / `zone`; all 60 zones: no shared cells,
  every `open` exit mutual and adjacent, 80 % of in-zone exits open); `webmove <from> <to>`
  (commands.py) answering a structured `move_result` on the map socket, no echo, name-only
  room output; `mode='near'` payloads add `nearby` rooms (within 3 cells, explored or not)
  with stable mob ids; one payload per move instead of two.
- Client (`src/web_isometric/world3d/`): `zone.js` (one coordinate space per zone, rooms
  streamed within 2 cells, crossings legal only through open exits, passage triggers),
  `sync.js` (moves sent without waiting; refusal → slide back with the server's reason;
  server-made moves relocate the hero, across zones too), `entities.js` (mobs/NPCs/players
  from `nearby`, nameplates, click/Tab targeting; beasts are placeholder wisps until M2),
  `controller.js` (A* click-to-move, minimap travel), doors (E opens), stairs / portals /
  zone-border passages with labels.
- HUD (`world3d/hud/`): login over a drifting 3D backdrop, character creation with the class
  model on a plinth, player frame, health/resource orbs, action bar (3 buttons to start,
  grows at levels 6 and 11, cooldowns), target frame with consider text, room/zone banner,
  toasts, chat log + command line, minimap from the zone map (click a room to walk there),
  menu (character, inventory, equipment, spells, quests), settings (quality, HUD size, F3).
- Verified here: `tests/test_webmove.py` (11 checks incl. closed door and sleeping
  refusals) and Playwright: login → Temple of Midgaard → hold W → server confirms the next
  room two frames after the hero enters it; temple stairs → God Simplex (zone hop); admin
  goto → The Whispering Woods (server-made zone change); Tab targets the nearest creature.
- M1b next: town buildings and interior theming (KayKit Medieval Hexagon, Furniture Bits),
  graveyards (Halloween Bits), monster/animal models (Quaternius), quest tracker and panels
  (inventory, character, spells), polish from the owner's playtest.

### M1b — progress (owner's order: monster models → towns and interiors → inventory → character panels)
- Owner after M1a: walking and the HUD feel good; stairs and lock/unlock doors to fix later;
  no monsters were visible in the sewers (fixed: /state replies wiped them during fights);
  wants to see more of the character's face (camera pitch now follows zoom, 34°–58°).
- Monster models: 38 CC0 Quaternius creatures (OpenGameArt, FBX → glTF in tools/art3d) plus
  procedural rats, spiders, snakes, rabbits and slimes; `world3d/bestiary.js` maps MUD names to
  bodies; creatures fighting you turn and strike each round, the dead fall before they vanish,
  flyers hover. Checked with `/play?demo&gallery=beasts` and in the live sewers and pet shop.
- Towns and interiors: streets get whole houses where they border empty map cells and
  shopfronts (chosen by the shop behind: smithy, tavern, church, market...) where they border
  an indoor room, low stone town walls elsewhere; interiors named as a temple, shop, tavern,
  bank, library, bedroom, guild hall, throne room or house are furnished (wood or stone floor,
  wall shelves, tables with stools, beds, benches and an altar, rugs, lamps); graveyards get
  rows of graves, fences and lanterns (`world3d/terrain-town.js`; KayKit Medieval Hexagon,
  Furniture Bits, Halloween Bits).
- Inventory (I): worn gear in its slots, the bag as a grid with the 2D client's painted item
  icons (`platformer/items.js`), tooltips (type, slot, level, damage, armour, effects, procs,
  weight, value), a menu per item (wear, wield, hold, quaff, eat, drink, recite, zap, brandish,
  read, look inside, examine, drop; remove for worn gear; double-click does the first), gold.
- Character sheet (C; K opens its skills tab): the hero turning in a 3D portrait, vitals,
  attributes (prime stat marked), hit / damage / armour / stance, experience ("max level" at
  the cap), active effects; skills and spells with proficiency, unlearned ones dimmed; talents.
- Still to come from the owner's notes: going up and down stairs, locking and unlocking doors.

### M3 — combat on the new engine (owner, 2026-10-09: "I need to see some combat actions… distance from NPCs can and should matter")
Combat v2 keeps the server's rules (rounds, skills, spells, proficiency, poise, brace and
sidestep, creature wind-ups) and adds positions, reach and a structured event for every line
the combat log prints, so the 3D client animates exactly what the log says.
- **Events** (`src/combat_events.py`, `src/combat_hooks.py`): swing, skill, spell, wound,
  heal, death, fizzle, wind-up, resolve, cancel, out-of-reach and creature moves, batched per
  room in the order the log prints them, sent to the web clients standing in the room
  (`combat_events` on the map socket). Telnet output is unchanged.
- **Timing**: a round is 3 s; creatures act 1.3 s after the heroes, so blows alternate instead
  of landing in one heap. A number rises when its blow lands (a sword 0.3 s into the swing, an
  arrow or bolt when it arrives); a creature's second and third blows follow 0.42 s apart; the
  dead fall after the killing number. Pressing a skill starts its own animation at once; the
  server's answer adds what flies and lands. A creature's wind-up marks the ground for the 4.3 s
  until it lands.
- **Positions** (`src/combat_range.py`): metres inside a room (24 × 15). The client reports
  the hero's spot (5×/s in a fight) and where it placed the creatures; the server moves
  creatures in a fight (5×/s): melee ones close to reach, archers and casters keep their
  preferred distance, everyone keeps 1.1 m apart. Telnet players have no position and are
  always in reach.
- **Reach**: an ordinary blow needs its class's reach (out of it: no blow, a message; melee
  heroes walk in by themselves, archers and casters keep their spot). Skills and spells check
  their range before they cost anything; the client walks just far enough (an archer stops at
  bow range). A skill aimed at a creature you are not fighting yet opens the fight.
- **Dodging**: a heavy blow comes down where you stood when it began (2 m), a spell where you
  stood (1.7 m), a sweep around the creature (4 m). Step out before it lands and it "hits only
  ground"; brace and sidestep still work, and staggering or kicking the creature breaks it.

| Class | Ordinary blow | Skills and spells (metres) | How it plays |
|---|---|---|---|
| Warrior | melee 2.5 | bash, kick, execute 2.5 · cleave cone 3 · charge dash from 15 · rally aura 8 · rescue 6 | charge in, hold the front |
| Paladin | melee 2.5 | censure, order verdict 2.5 · holy smite 14 · absolution heal 12 · halo aura 5 · turn undead cone 8 | front line with a ranged smite |
| Cleric | melee 2.5 | holy smite 14 · cure light, heal, bless 12 · flamestrike blast 3 at 14 · turn undead cone 8 | mid-range healer |
| Ranger | bow 16 (under 3 m: 60 % damage) | truesight shot 18 · loosing storm blast 3.5 at 16 · quarry mark 20 · call lightning 16 · wildbond strike 2.5 | keep your distance |
| Thief | melee 2.5 | backstab, circle, trip, low blow, jackpot 2.5 · pocket sand 5 | in close |
| Assassin | melee 2.5 | backstab, expose, vital, feint, execute contract 2.5 · mark 15 · fade | mark from afar, strike close |
| Mage | arcane bolt 10 (weak point-blank) | magic missile 18 · fireball blast 3 at 16 · lightning bolt 18 · towerbolt 20 · sleep 12 · chill touch 2.5 | back line, blasts |
| Necromancer | shadow bolt 10 | soul bolt 16 · soul siphon 10 · soul reap blast 4 at 14 · chill touch 2.5 · animate dead | back line, drains |
| Bard | melee 2.5 | mockery 14 · fascinate 12 · discordant note cone 7 · crescendo aura 6 | mid-range support |
| Creatures | melee 2.2 | archers 15 (prefer 9) · casters 13 (prefer 8) · healers and support 12 (prefer 8) | |

Areas (cone, blast, aura) are drawn on the ground; who they hit is still decided by each
skill's own server code.
- Fixed on the way: `cast 'lightning bolt' orc` (any two-word spell with a target) looked for
  a target called "bolt orc"; spells now fizzle only after the target and range checks, and a
  fizzle shows on screen; an archer's or caster's ordinary blow reads as an arrow or bolt in the
  log; Tab prefers enemies over shopkeepers, trainers and quest-givers; overlapping hit flashes
  could leave a model stuck red.
- Verified here: `tests/test_combat_v2.py` (3 runs green: out of reach → no blow + `oor`, the
  creature walks in, swings and wounds as events, a skill opens a fight, a wind-up lands
  4.32 s after its 4.3 s mark, stepping out of it makes it miss, a stagger cancels it) and
  `tests/test_webmove.py`; Playwright with a level-15 mage (magic missile, fireball, lightning
  bolt, sleep, towerbolt as an opener, fizzles, the bear's sweep, the kill; no page errors),
  ranger and cleric. This container renders WebGL at ~1 fps, so the feel (timing of swings,
  bolts and numbers) is for the owner to judge on a real GPU.
- Next, from the owner's test: tune numbers (round length, reach, wind-up time) and the look
  of each skill; then Phase 3 (per-action resolution) if rounds still feel slow.

### Stairs and doors (owner, 2026-10-10: "the stairs and lock/unlock doors next")
- **Stairs** (`world3d/passages.js`, `zone.js`, `main.js`): a hop stays in flight until the
  arrival is applied, so a zone hop is sent once (the zone map download used to race the next
  frame: a second move, "You can't go that way.", a double flash). You land 1.6 m beside the
  stairs that lead back (up/down exits are named by direction of travel; the client used the
  wrong side). A gate keeps the stairs you arrived beside quiet until you walk away, stand still
  a moment or click them, plus a 1.2 s cooldown: holding a key into them no longer bounces you
  back. Stairs fire only when you move onto them (or a click sends you there); paths and the
  combat chase walk around them; they are blocked in a fight like doorways. `webmove` takes the
  exit the client names (`webmove 3001 3005 down`: 86 room pairs have stairs and a doorway to
  the same room). The step onto and off the stairs is animated under the fade; creatures and
  followers changing level snap there in a puff of dust. ▼ Down is a stairwell now (a dark
  opening, rim and steps), ▲ Up a staircase climbing away from where you arrive; labels say
  where they lead; furniture keeps off them; the minimap shows ▲/▼ and minimap travel crosses
  stairs (re-planned after each hop).
- **Doors** (`src/doors.py`, door commands, `cmd_webdoor`, `world3d/doorlogic.js`, `hud/prompt.js`,
  `hud/castbar.js`, `hud/contextmenu.js`): one module finds doors (`s` is south and `u` up — they
  used to resolve to east and south; names work: `unlock wooden`, `open door wooden north`),
  changes both sides together, stamps a revision and pushes a `door` event to every web client
  in both zones. Keys count when carried or worn; a lock without a key is anyone's (the world's
  rule); pickproof locks refuse picks. Payload doors carry `label` ("wooden door"),
  `has_key`, `can_pick`, `key_name`. At load, "open and locked" (102 imported doors) becomes
  unlocked and the two sides agree; doors return to their starting state with a zone reset
  (not while a player stands by). In /play: a prompt floats over the nearest door ("E Open
  the oak door", "E Unlock", "E Pick the lock", "Locked — needs a golden key", "E Close"); E
  does it (`webdoor <room> <dir> <action>`, unlock-and-open in one press); walking into a
  closed, unlocked door opens it; a right-click by a door gives the full menu (open, close,
  lock, unlock, pick, knock, bash); lock-picking shows a cast bar and moving abandons it.
  Doors appear on passage doorways too, trapdoors are hatches over stairs, locked doors show
  iron bands and a padlock.
- Verified here: `tests/test_doors.py` (offline: parsing, both sides, keys, picks, push,
  `webdoor`, load, reset; live: the oak door at 921 with and without its golden key, the push
  carrying both sides), `tests/test_webmove.py` (stairs direction), `node --test
  tests/web/*.test.mjs` (every stairs/portal room's landing, the gate, door prompts/menus) and
  `tests/web/probe_play3d.js stairs|doors` in a browser with the zone map delayed 3 s.

### Camera, right-click and auto-target (owner: "let the camera pan around the player with a right click"; "right click should give other context menus"; "if something attacks the player ensure the target is automatically selected")
- **Camera** (`world3d/orbit.js`, `input.js`, `engine.js`): right-drag turns the view around the
  hero (0.0065 rad/px) and tilts it (up = a higher view, −12°…+10° on top of the zoom's pitch,
  26°–66° overall); it stays where you leave it (owner's choice); Home, the minimap's compass
  or Settings → Camera snap back to north up. WASD follow the camera (W = away from it). The
  minimap stays north up with a wedge for where the camera looks and a compass needle. The
  wheel zooms in proportion to the scroll (trackpads glide; a sideways scroll does nothing).
  Overlays (nameplates, floating numbers, the see-through circle, prompts, the minimap) run
  after the camera each frame, so nothing lags while turning; numbers fan along the screen's
  left-right; doors and wall furniture turn see-through when they stand in the way.
- **Right-click** (press and release without dragging; Ctrl+click on a Mac): a menu for what is
  under the cursor (`hud/verbs.js`): a creature (Attack, its bar skills, Target, Consider,
  Look), a shopkeeper/trainer/quest-giver (Talk, Shop, Train, Rent, Look...), another player
  (Look, Whisper, Invite to group, Follow, Assist, Trade), a door (its actions), yourself
  (Character, Inventory, Score, Rest/Sleep/Stand, Recall, or Flee in a fight), the ground
  (Walk here).
- **Exact targets**: the client names a creature by its id (`kill #12`); the server turns that
  into the keyword each command understands (`wolf`, or `2.wolf` when another wolf comes first),
  and spells accept numbered and exact targets too. The action bar sends skills by their id
  (`holy_smite`, `order_verdict`, `execute_contract` used to reach the wrong commands) and
  renamed abilities show their cooldowns.
- **Auto-target** (`world3d/targeting.js`): the first blow, spell or wind-up aimed at you makes
  the attacker your target, unless you are busy with a live foe or picked a hostile by hand a
  moment ago; when your target dies, the creature that hit you last takes its place. Its
  nameplate turns red. Server: map payloads say which creatures fight you; a second attacker no
  longer steals your swings (CircleMUD's rule); an attacked player hears about the fight at
  once; hunting creatures show their moves.
- Verified here: `node --test tests/web/*.test.mjs` (orbit maths, W at any angle, click vs drag,
  targeting rules, menus), `tests/test_combat_v2.py` (`kill #id` hits the second of two
  spectres, the payload's `fighting`, cooldown names, the `#id` rewrite) and
  `tests/web/probe_play3d.js camera|menu|autotarget`.

### Creature models (owner: "some of the npcs have weird character models. Like a blob looks like a humanoid")
- **Why it went wrong**: the client matched the keyword list (`name`: "green") instead of what a
  creature is (`short`: "the green gelatinous blob"), and anything it couldn't place became a
  person or a glowing wisp. 78% of the world's 876 creatures were drawn as people.
- **How a body is chosen** (`world3d/looks.js`, pure, run over every creature by
  `tools/qc_bestiary.mjs`): the server now sends `short`, the start of the room line (`long`)
  and the type number (`pv`). What the short description ends with decides: a two-word creature
  ("the fire elemental", "the giant lizard"); a trade or role word makes a person ("the goat
  herder", "the vampire hunter") unless a race stands beside it ("a goblin mushroom farmer",
  "King of the Goblins") or a creature rules ("the Spider Queen"); otherwise the creature it names
  ("the giant hornet" is a hornet, not a giant); then the undead; then any creature word; then a
  person dressed for the job. A person whose room line says otherwise takes that ("the Sewer King":
  "A massive rat-man standing here."; "the Ancient Guardian": "A towering stone golem...").
- **Sizes and colours**: adjectives in front size the body (small creatures grow more and big
  ones less, so a giant rat is dog-sized and a massive minotaur still fits through a door; a baby
  dragon is not a full dragon) and colour it ("the red dragon", "a black bear", "a frost wolf");
  undead beasts are rotten or bare bone; rulers ("the queen wasp", "the alpha wolf") are bigger.
- **New bodies**: kit props come to life (`proc.js` `makeProp`: a mimic is a chest, a living
  book and a dancing sword fly, a magic carpet floats); a four-legged lizard for crocodiles,
  lizards and basilisks; golems, statues, animated armour and chess pieces are one colour all over
  (stone, bronze, iron, black or white — `flat`) and statues stand still until they fight;
  elementals, djinn and efreet are tinted spirits; pixies and sprites are tiny and hover; hags
  wear witch hats; lizard folk, merfolk, orcs, drow and sahuagin keep their trade's gear with their
  own skin.
- **People by trade**: guards and knights carry sword and shield, casters a staff or spellbook,
  innkeepers a mug, smiths an axe, thieves knives, rangers a crossbow; shopkeepers, townsfolk and
  children carry nothing (no more baker with a two-handed axe); guildmasters dress for their guild.
  The skeleton models follow what the dead were (a skeletal warrior, a lich, an ossuary archer).
  A creature type always looks the same (hashed by type, not by its id).
- **Data**: seven creatures shared their numbers with others (3100–3102, 3120–3122, 3200), so one
  of each pair never appeared; they were renumbered (3011–3016, 3203) with their resets, and the
  Pet Shop, the sewers and Stable Road get their dog, bear, wolf, Sewer King, assassin, Ancient
  Guardian and stable master back.
- Verified here: `node --test tests/web/*.test.mjs` (cases, and every creature in the world gets a
  model, weapon and prop that exist in the art, with no creature word drawn as a person),
  `node tools/qc_bestiary.mjs` (the whole list, grouped by body), `/play?demo&gallery=beasts`
  (labelled samples) and `tests/web/probe_play3d.js creatures` (live: a blob, a mimic, a statue,
  a rook, a golem, a goblin farmer, a brownie, a living book and the Sewer King in the temple).

### Skills: learn by doing, a spellbook and your own bar (owner's choices: "learn by doing"; "spellbook + your own bar")
- **Learning** (`src/mastery.py`): every class ability unlocks at a level (`UNLOCK`, from each
  roster's order, spells keeping their `level_required`, spread to 50; prestige spells 56–60).
  Reaching it grants the ability at 50%, on a level-up, at creation and at login (characters made
  before catch up: "Your training catches up with your level..."). Abilities above your level are
  refused ("You don't know execute yet — it comes at level 14"); before, most button skills only
  checked the class. Practice sessions are no longer handed out.
- **Improving**: using an ability may improve it, up to 85% (Mastered): max(2, 20 − %/5)% on a
  success (10% at 50%), half on a miss, +1–2 points; "Your kick improves! (63%)" and a "+N%"
  on its bar slot. Passives (dodge, parry, shield block, evasion, extra attacks) improve when they
  work, at a quarter of that. Crafting and gathering skills keep their own rules.
- **Proficiency matters**: a spell fizzles (100 − %)/4 % of casts (50% → 12.5%, was 50%; 85% →
  3.75%); ability damage and spell healing ×(0.85 + 0.3·%/100). Passives now work a share of
  their proficiency (dodge and parry ×0.25, shield block ×0.3, evasion ×0.2, second attack and
  dual wield ×0.6, third attack ×0.3): at 50% a dodge used to mean dodging half of all blows.
  These are balance changes to tune after playing.
- **Trainers**: past 85%, your guild's trainer teaches 5% at a time to 100%, for (% − 80) × 250
  gold (1,250 at 85%) or a leftover practice session; below 85% they send you off to use it; a
  trainer of another class (Sergeant Bron) says where your guild is. `practice` lists your
  abilities and when the rest arrive; `skills` shows "[level 14]" for those to come. The minimap
  marks your guild's trainer with a gold star. Immortals: `set <who> skill <ability> <percent>`.
- **Spellbook (K)** and **your own bar**: the spellbook lists every ability of the class (and the
  ones a talent can teach) from `/abilitybook` (fetched once per class): what it costs and
  reaches, how well you know it, "Level 14" for the ones to come. Drag an ability onto one of 16
  slots (1–8, Shift+1–8), between slots to swap, off the bar to remove it; right-click a slot for
  Use / Take off the bar. The bar is kept with the character (`webbar`, saved in the player file,
  sent back as `bar`). New abilities glow into a free slot without moving the others. Heals and
  blessings go to the player you target, else to yourself. Right-click a trainer → Master your
  abilities opens the trainer window.
- Verified here: `tests/test_mastery.py` (offline rules and maths; live: `skills`, the level
  refusal, a trainer step for 1,250 gold, Bron's directions, `/abilitybook`, the saved bar),
  `node --test tests/web/*.test.mjs` (bar logic), `tests/web/probe_play3d.js spellbook|trainer`,
  and the stairs/doors/combat suites unchanged.

### Other players and groups (owner: "can multiple players join the game? Can I see other players and group with them?")
- **Sessions are secret now.** Before, the map server trusted a name: anyone could subscribe to
  another player's live updates, read their state and mail, or move them; a `say` containing a
  hidden MAPSYNC sequence switched every listener's client to another identity. Now every login
  gets a token (`server._issue_web_token`), sent only down that player's own connection inside
  MAPSYNC; the map socket's `subscribe` and the 15 per-player endpoints answer only to it
  (`web_map._player_by_token`, `_authed`); `net.js` adds it to every `?player=` request; control
  characters are stripped from everything typed; the client's parser ignores game words inside
  someone's speech. WebSocket frames over 1 MB are refused.
- **One copy of a character.** Logging in again takes the character over in memory: the old
  session is told and closed without saving a stale copy, its web clients are revoked (they go
  back to the login screen), the world keeps one body. Leaving removes only that very object;
  a command that crashes no longer drops the connection; `goto` is for immortals.
- **Seeing each other.** Payloads carry other players' positions; each web player's position is
  relayed (≤ 5 a second) to the 3D clients that can see them, and room changes of any kind
  (walking, recall, portals, following) reach everyone in view (`web_map.relay_presence`,
  `note_room`). Other heroes run to keep up instead of sliding. Followers are no longer dragged
  out of fights, their explored rooms and maps update, and a sneaking leader's followers get
  their view too.
- **Groups.** Invites arrive as a popup (Join / Decline, 60 s), `group invite <name>` works,
  party frames sit under your own (health, mana, leader's crown, where an absent member is;
  click to target them — heals go to your target — right-click for Whisper, Follow, Make leader,
  Remove, Leave), every change is pushed to the members at once, members leave the group when
  they quit, kicking someone from a group of two no longer drops the leader, the last member is
  told when a group disbands, round-robin hands out loot in turn among those present, gold is
  split among the members present, and autoloot leaves worthwhile drops for the need/greed roll.
  A loot roll now holds its item while it runs (it used to be duplicable by looting the corpse).
- **Chat.** Tabs (All / Group / Say / Tells) and a mode chip on the input (Cmd → Say → Group →
  Tell), `reply` answers the last tell; right-click a player: invite/follow/trade say "walk
  closer" when they're in another room.
- Verified here: `tests/test_multiplayer.py` (tokens, takeover, control characters, presence
  relay, invite/accept/kick/quit events, loot-roll custody, round-robin), the existing suites with
  the token, and `tests/web/probe_play3d.js party` (two browsers: each sees the other walk, invite
  → popup → Join → party frames with the leader's crown on both).

### Every ability looks like its class (owner: "ensure animations for skills, spells, and abilities are unique and themed for every class")
- **Every ability has an event now.** Only the ~50 abilities with a range entry used to reach the
  3D client; the rest showed nothing. Every class ability (renamed commands too: `aimed_shot` is
  the truesight shot) and the extras outside the books (combo finishers, lay on hands, raising
  the dead, songs, summoned elementals) now send an `ability` event, aimed by what its book says
  (`combat_hooks._class_ability`, `event_shape`, `EXTRA_ABILITIES`); a heal with nobody named is
  for yourself; sneaking and hiding are shown only to the one doing it (`emit_private`). The
  warrior, thief, ranger and assassin level 31–60 abilities joined their class books, so they
  show in the spellbook and grow with use; self buffs such as Warpath no longer need a target,
  and bow skills (serpent sting, volley...) no longer walk you up to melee range first.
- **A recipe for every ability** (`world3d/abilityfx-table.js`, 302 lines: 285 book abilities
  and 17 extras): `'body | cast | travel | land | aura | flags'` — the clip and a body motion
  (leap, dash, blink behind the target, spin, hover, rise and slam, backstep, sidestep), what
  gathers while it winds up, what flies, how it lands and what lingers. Each class has its
  theme (`abilityfx.js THEMES`): warrior steel and ember (war crest, sparks, cracked ground),
  paladin gold and azure (sun wheel, pillars, wings, halos), cleric pearl and rose (rose window,
  feathers, petals), mage violet and cyan (rune circles, orbs, the elements), necromancer bile
  and bone (skull circles, flying skulls, drains, bones out of the ground), thief coin and smoke
  (coin rings and fountains, dice, smoke), assassin crimson and nightshade (crosshair, blinks,
  afterimages), ranger leaf and amber (leaf wreaths, arrow rain, paw prints, vines), bard magenta
  and teal (the musical staff, notes, rings of sound). Creatures' spells look like their school.
  Passive defences carry the class too (an assassin's dodge leaves an afterimage, a paladin's
  block a flash of gold); auto-attack arcs are the class's colour.
- **New effects** (`fx.js`, pictures drawn in code in `glyphs.js`): glyph particles (notes,
  skulls, coins, leaves, runes, feathers, daggers...), ground sigils and cracks, chains, rays,
  tethers, arrow and glyph rains, meteors, ground waves, cones, geysers, growths (vines, bones,
  ice, stones, bars, thorns), shields and domes, wings, halos, orbiting glyphs, afterimages,
  glows, stealth fades, screen flashes. Everything runs on the frame clock (`fx.after/every`, so
  a hit-stop slows a whole sequence alike), each quality tier has a budget, effects far from
  the view draw only their core, and particle sizes follow the screen's resolution.
- **Timing.** The key press starts the hero's clip, motion and cast at once
  (`fxdirector.prelude`); the server's event then plays what flies and lands from where the key
  press left off. Each ability's wounds and heals in the same batch rise when it reaches them
  (areas included), not when the event arrives.
- **Checks.** `tools/dump_abilitybook.py` writes every class's book to
  `tests/web/fixtures/abilitybook.json` (`test_mastery --offline` fails when it is stale);
  `tests/web/abilityfx.test.mjs`: every ability has its own line, no two in a class share a
  shape, a spell several classes know looks different in each, only real clips and effects;
  `/play?demo&gallery=abilities&cls=<class>[&only=…][&speed=0.5][&manual]` plays a class's
  whole book on training dummies, labelled; `probe_play3d.js abilityfx` uses a character's own
  abilities on a spectre in the real game. All 302 played in the gallery without an error.

### The look of Misthollow (owner: "ensure the UI is amazing… make it easy for players to fight mobs… immersive… menus visually stunning and easy to read… everything needs a theme")
- **A theme: lanterns in the mist.** The hollow is a fog-bound valley; the HUD is a traveller's
  kit carried through it (`hud/theme.css`): panels of dark mistglass bound in brass filigree
  (gilded corner pieces, a grain in the glass), window heads engraved between gilded rules,
  lacquered brass buttons, bookmark tabs, keycaps, tooltip cards on dark vellum. Fonts are part
  of the repo (`src/web_isometric/fonts`, SIL OFL): Cinzel for titles, Cinzel Decorative for the
  name, Alegreya for lore and descriptions, Alegreya Sans for everything you read at a glance.
- **Every ability has a painted icon** (`hud/icons.js`, drawn in code from the ability's own
  recipe): a gem in its element's colour or its class's two tones (blows in the main colour,
  wards and help in the second), the class's sigil faint behind, a pictogram of what it does
  (the weapon, what it throws, how it lands, what it leaves on you), a badge for how the body
  moves, a frame in the class's metal. `/play?demo&gallery=icons` shows all 315.
- **Frames with faces** (`hud/portrait.js`: one small offscreen renderer photographs a bust):
  your own frame (your class model's portrait, a wax-seal level, health and resource bars with
  numbers and a pale ghost that drains behind a wound, buffs as icons whose ring empties as they
  wear off), the target's (its portrait, name in the colour of how dangerous it is — trivial,
  easy, even, hard, deadly — level, health, distance, and its wind-up as a cast bar: "Crushing
  Blow", "Interrupted!").
- **The action bar**: painted icons, cooldowns as a sweep with the seconds, a glint when ready,
  red when out of reach, blue when you lack the mana, rich tooltip cards (rank, progress,
  description, cost, cooldown, reach, key); lantern orbs for health and the class's resource;
  a menu of brass-rimmed buttons (C I K L M O).
- **Easier fights** (`combatcues.js`): a ring under your target (red for a foe), your reach drawn
  around you while you hover an ability (green when the target is inside it), STEP OUT over
  your head with an arrow to the safe side when a foe's marked blow is about to land where you
  stand, STRIKE NOW when a foe is staggered (the bar's heaviest ready attacks glow), "press F to
  attack" when a foe is in reach, nameplates with level badges in danger colours and gold
  chevrons around your target, bosses crowned. (Fixed on the way: a creature's marked ground was
  drawn at room-local coordinates, i.e. in the wrong place outside the zone's first room.)
- **Immersion**: a title screen (drifting mist over the hollow, the lantern crest, MISTHOLLOW
  engraved in gold, "Where the mist remembers every name.", a line of the hollow's lore turning
  below), a loading ring, chapter cards when you enter a zone, the mist reddening and closing in
  when your health runs low, a "Level Up!" moment with a column of light, "You have fallen" when
  you die, speech over the heads of those who talk, passage signs in the same style, character
  creation with each class's emblem.
- **New windows**: a quest journal (L) — your quests, the chosen one's story, objectives and
  reward, Complete/Abandon, the quests offered by whoever stands beside you with Accept; a big
  map of the zone (M) — explored rooms, your guild, your quest, click a room to walk there.
- Verified here: the probe suite (spellbook, trainer, menu, autotarget, abilityfx, camera, doors,
  stairs, creatures) with the new markup; screenshots of the title screen, the HUD exploring and
  in a fight, the cues, the windows.

### Marquee class quests — the warrior's first (owner: "Each class should have a final marquee spell/skill/ability. This should be a quest for each character. It should be achievable solo or with a group. If done solo the difficulty should take a couple hours of play time. If in a group the difficulty should scale based on how many embark on the quest when the player accepts")
Owner's choices: all-new abilities (the level-60 prestige capstones stay), offered at level 45,
the endgame world plus a private trial. Shipped in two parts: the systems with the warrior's
quest end to end (this push), then the other eight classes on the same engine.
- **The ability: Unbroken Banner** (`marquee_abilities.py`): the warrior plants a war banner;
  foes within 4 m reel (bosses stagger), every foe turns on the warrior, and for five rounds the
  warrior and the allies beside them strike harder, shake off stuns and fear and mend. Its
  damage and healing follow how well it is known (it is learned at 50% and grows with use like
  any ability); its 8-minute cooldown is kept on the character. It is in the warrior's book
  from level 45, marked "earned through The Unbroken Banner"; reaching a level never teaches it.
- **The quest** (`marquee_quests.py`; the engine is `marquee.py`): `talk guildmaster` in the
  warriors' yard from level 45 offers it (a card in the 3D client, Accept / Not now; `marquee
  accept` in text). Seven stages, about two hours alone:
  1. *The Fallen Standard* — find the dying crusader on Castle Apocalypse's West Wall Path.
  2. *The Banner-Reavers* — three war-chiefs carry the banner's pieces: the Hall of War, the
     Inner Gate, the Castle Courtyard.
  3. *Embers for the Cloth* — ember shades in the Ashlands (Steam Vent Valley, the Magma
     Flows, the Scorched Wasteland); about half give an ember core; five are needed.
  4. *The Cinder Smith* — a boss on the Burning Bridge (Hammerfall, Slag Wave, adds at half health).
  5. *The Dragon's Gate* — plant the banner (`marquee plant`, or the tracker's button) and
     hold it for 30 seconds against three flights of drakelings; leaving breaks it.
  6. *The Last Bastion* — `trial enter` (or the button) at the gate: a private copy of the
     besieged bastion for the party. Three waves behind locked gates (the Outer Wall, the
     Breach twice), then Gorrund the Siegebreaker in the keep (Rampart Crush around him, Siege
     Charge at one hero, hounds on call, enraged after 8 minutes). `trial leave` steps out; left
     empty for ten minutes it closes and starts over. Logging out inside comes back at the gate.
  7. *The Last Lesson* — back to the guildmaster, who teaches Unbroken Banner.
- **Alone or together**: accepting asks the group members beside you to embark (a popup with
  Join / Decline, 30 seconds; `marquee join|decline`, `marquee go` to set out at once). Who
  joined is the party for good (`marquee_scale.py`): every foe of the quest has ×(1 + 0.8(n−1))
  health and ×(1 + 0.1(n−1)) damage, waves bring one more foe for every two extra heroes, the
  bosses act sooner; the quest's level is the owner's or the party's average if higher. Leaving
  later changes nothing. Any member's kill counts. Helpers are paid (experience, gold) when the
  trial falls; the owner learns the ability.
- **The quest's own foes** (`world/zones/zone_097.json`, vnums 9700–9707): placed when a party
  member comes near, made for the party, attacking after a breath; someone outside the party
  cannot hurt them ("belongs to Gauntlet's quest"); they go home if the party is away ten
  minutes and come back when it returns. Sized so an elite costs a lone level-45 hero about half
  their health and a boss one to two times it, most of it from blows that are telegraphed (the
  3D client marks the ground; stepping out of it now really spares you).
- **On screen**: the tracker under the minimap (stage, objectives with progress bars, ◆ where
  to go — also on the minimap and the big map — the party, and a button for the next action:
  Speak with…, Plant the banner, Enter the trial, Leave the trial), a draining bar while
  holding the gate, the stage's chapter line, the journal (L) lists it first with what it
  teaches, and `marquee` in text says the same. A `!` over the guildmaster when it is offered,
  a `?` over whoever the quest wants you to speak with.
- **Fixed on the way**: a boss's wind-up now sends the 3D client its marked ground and its
  outcome (`windup` / `resolve` / `cancel` with who stepped clear); bosses' summons, heals and
  wards no longer also hit for level × 2 damage; the kill's beneficiary was read before it was
  set in `handle_death` (legendary drops and on-kill effects); a login whose saved room is gone
  lands at the recall point; rooms can be `lit` (never dark at night).
- **Tests**: `tests/test_marquee.py` — offline: the scaling, the quest data pointing at real
  rooms and creatures, and the whole quest driven on the real world with stand-in players (each
  stage, a party of three, outsiders, the trial opened, won and closed); live: the quest on the
  server from the offer to the learned ability with the trial fought through, and two players
  embarking together (a war-chief with ×1.8 health). Admin: `marquee stage <n>` jumps a quest,
  `marquee forget` clears it and the ability.

### Marquee quests: the mage, the cleric, the paladin and the necromancer
Four more classes on the same engine (the last four — thief, ranger, bard, assassin — come next).
- **The abilities** (`marquee_abilities.py`), each sized off a hero's round of damage
  (`marquee_scale.dpr`) and how well it is known:
  - **Singularity** (mage, 8 min): every foe is dragged to one point (in 3D they slide there),
    held and crushed for two rounds, then it implodes and leaves them slowed.
  - **Seraph's Vigil** (cleric, 10 min): a seraph of light hovers over the cleric for six rounds,
    healing whoever is most wounded each round; while it stands each ally survives one killing
    blow (at 1 HP).
  - **Wings of Dawn** (paladin, 8 min): rise on wings of light and crash down — radiant damage
    within 6 m, every ally healed a quarter of their health and shielded for 15%.
  - **Lich Ascension** (necromancer, 10 min): six rounds as a lich — spells cost half, soul bolts
    split to a second foe, a quarter of what you deal drains back, death turned away once (30%).
  - Unbroken Banner's bonus is now "+25% damage to creatures" instead of a damroll affect.
  - Bosses are never pulled, held, slowed or stunned — they stagger. None of them touches players
    or pets, and none works in a duel or the arena.
- **What it rests on**: lingering parts run on combat rounds (`EFFECTS`, stepped after every
  `World.combat_tick`, only while the caster is online, alive and in the room); creatures can now
  be held (`rooted_until`: they don't move) and slowed (`slowed_until`: half the steps, about half
  the swings, a round longer to wind up); damage-taken and damage-dealt bonuses keyed by source
  so they refresh instead of stacking; a death ward that turns a killing blow aside from any
  creature, trap or hazard (never another player) without announcing a death or making a corpse.
- **The quests** (`marquee_quests.py`, creatures 9710-19, 9720-29, 9750-59, 9760-69 in
  `zone_097.json`, trials in `world/marquee/trials/`):
  - *The Heart of the Void* (mage): the planar traveller in the Plane of Chaos; three
    rift-wardens there; star-glass from arcane wraiths in the High Tower of Magic; the Echo of the
    Archmage; attune the shards in the Pentagram Chamber; the trial *The Collapsing Star* and
    Vaelith the Star-Eater.
  - *The Lost Choir* (cleric): a drowned priestess in the Sunken Temple of Nereus; three drowned
    zealots; seraph feathers from gilded harpies at the Great Pyramid; the Gilded Hierophant;
    consecrate the Pyramid's apex; *The Silent Choir* and Serathiel the Fallen.
  - *The Dawnless Chapel* (paladin): the restless ghost in the Necropolis; three eclipse knights;
    dawn embers from ember wisps in the Ashlands; the Ashen Templar; a dawn vigil in the Mountain
    Pass; *The Dawnless Chapel* and Morvane the Eclipsed.
  - *The First Phylactery* (necromancer): the grave keeper in the Necropolis; three bone colossi;
    soul shards from wailing shades in the Shadowspire; the Soulbinder; bind the soul in the
    Phylactery Chamber; *The Phylactery Vault* and Xal'thar the First Lich.
- **In 3D**: three new effects (`fx.js`) — `implode` (sparks falling in, a black core with a
  burning rim swelling over the target, then a flash), `seraph` (a larger figure of the caster
  made of light, with great wings and a halo, feathers drifting down), `lich` (grave-green glow,
  a crown of grave-fire, skulls circling, a ring of bones underfoot); icons for them (an
  imploding core, a winged seraph, a crowned skull; the banner now shows on its own icon).
- **Fixed on the way**: 104 rooms in five zones (the Plane of Chaos, Silversong, the Haunted
  Swamp, the Dwarven Mines, the Sunken Ruins) showed as "An Empty Room" — the loader now reads
  their `title`/`terrain`; "song of the ages"-style names typed with spaces run the right command
  (3- and 4-word joins) and typed abilities animate in 3D; marquee cooldowns show on the bar and in
  the spellbook; a stat buff saved during a relog came back doubled and stuck (stats are now saved
  without their buffs); hazards killed players twice (two death penalties); and only a
  session's first death made a corpse — now every death leaves a corpse with your gold and what
  you carry, and you keep what you wear (owner's call).
- **Tests**: `tests/test_marquee_abilities.py` (the four abilities and the banner by the numbers,
  the boss rule, root and slow, the ward's paths, effects ending on logout, refusal wording, the
  stat save, the corpse rule, the room names); `tests/test_marquee.py` checks every quest's data and
  plays each new quest through all seven stages offline, and live: each class's test character
  takes its quest, enters and leaves its trial, learns and uses its ability (the mage fights its
  trial through).

### Marquee quests: the thief, the ranger, the bard and the assassin — every class has one
- **The abilities**:
  - **The Heist of Ages** (thief, `heist`, 8 min; the owner chose the name because "Grand Heist"
    is already a thief talent): gone in smoke and behind every foe at once — each struck (3×DPR)
    and relieved of half the gold it carries (gold is only ever moved, never made), then the
    next three swings are certain criticals. In 3D the thief blinks from foe to foe.
  - **Heartseeker** (ranger, 6 min): a round's draw (the bow drawn in 3D, the quarry marked),
    then one arrow through every foe on its line (6×DPR the first, 4×DPR the rest; without
    positions the target and up to two others) — marked to take 20% more for four rounds and
    held two (a boss on the line only staggers). In 3D the arrow streaks through and out.
  - **Song of the Ages** (bard, 8 min): five rounds in which the allies beside the bard get one
    extra round off each of their own ability timers a round (never travel, flight, reactions,
    hunger or the marquee cooldowns; two songs don't stack), deal 20% more to creatures and heal
    20% more, while foes slow; the last note stuns them (bosses stagger).
  - **Thousand Shadows** (assassin, 8 min): for three rounds shadows strike every foe (1.2×DPR);
    the last of them finishes the weakest under 30% (capped at 8×DPR, so the huge only take a
    deep wound; a boss takes a 30% heavier last blow instead). In 3D shadow copies step out of
    the dark around each foe and cut in.
- **A new kind of stage, `visit`**: places to reach, in order or any order — the thief cases
  Thalos (City Hall, the Guild House, the north-west watchtower), the ranger follows Gloomfang's
  trail through the Great Northern Forest, the bard hears the four lost verses (a tavern in
  Thalos, the Cliff Tavern, the Refugee Sanctuary in the Plane of Chaos, Silversong's Ancient
  Grove). Each place tells its part of the story and the tracker marks the next one.
- **The quests** (creatures 9731-36, 9740-47, 9771-76, 9780-88; trials `thief`, `ranger`, `bard`,
  `assassin`):
  - *The Last Score* (thief): the fence in Thalos; case the job; tomb keys from the Great
    Pyramid's tomb wardens; rob the Keeper of Keys; crack the treasure vault of the Sunken Temple;
    *The Vault of Ages* and Auditor Mordessa.
  - *The Last Wyvern* (ranger, eight stages): the old trapper; the trail; three dire alphas;
    storm feathers from the cliff rocs of the Sunken Coast; the Roc Matriarch; wait in a blind at
    the Edge of Chaos; *The Hunting Grounds* and Gloomfang, the Last Wyvern.
  - *The Unsung Verse* (bard): the elven bard of Silversong; the four lost verses; resonant gears
    from the Clockwork Foundry's chime automatons; the Carillon Engine; play the Song at the
    Elemental Nexus; *The Hall of Unsung Kings* and the Mute King.
  - *The Contract of Mirrors* (assassin, from the same guildmaster as the thief — the class
    decides): a veiled informant in the Shadowspire; the three mirror-blades; black lotus from the
    Sunken Coast's cutthroats; the Poisoner; an ambush in the Sanctum of Light; *The Hall of a
    Thousand Mirrors* and the Faceless One.
- **In 3D**: `pierce` (an arrow and a streak of light through the line and on out), `blinks`
  (a hop behind each foe it reached, with a slash and a glint of coin), `clones` (shadow copies of
  the striker around the foe, cutting in); icons for them (an arrow through two rings, three
  hooded shapes, a double blink badge).
- **Tests**: `test_marquee_abilities.py` covers the four (gold conserved, the line pick, the mark,
  the shave and its exclusions, two songs shaving once, the execute and its boss rule);
  `test_marquee.py` plays all eight quests through offline and, live, each class's test character
  takes, enters, learns and uses (the ranger fights its trial through).

### Security (owner's pick, first of four: "Security fixes, Sound and music for /play, Marquee balance pass, Real-time combat")
- **A way into account characters, shut**: a character made from the account menu was saved
  with the password "account_protected", and typing its name at the login prompt with that word
  logged in — for an admin account's characters, as an immortal. Now a character that belongs to
  an account, typed by name, asks for the *account's* password and goes straight in; its own
  stored password is never a way in, new ones store none, and the old word never matches.
- **Passwords** (`src/security.py`): salted PBKDF2-SHA256 (600 000 rounds, worked off the game
  loop). Old unsalted hashes still work and are upgraded the next time their owner logs in. New
  passwords need 8 characters (older, shorter ones keep working).
- **Browsers keep a sign-in, not the password**: the three web clients used to store the
  password (base64) in the browser. Now, after a password login, the page asks the server to
  `remember` it; the server answers over a hidden signal (`RESUME`, turned into a message by the
  bridge) with a random token and keeps only its hash (`lib/resume_tokens.json`, five browsers a
  character, 30 days). `resume <name> <token>` at the name prompt logs in and swaps the token for
  a fresh one. `/play` shows "Welcome back, <name> — Continue / Use another name"; `/platformer`
  fills the name and Enter continues; `/2d` signs back in by itself. A password that an older
  page kept is used once, then deleted. **Log out** (in Settings on `/play` and `/platformer`)
  forgets that browser; changing or resetting a password forgets every browser of the account.
- **Login limits** (in memory): three wrong passwords close the connection; five on one name in
  ten minutes lock it for five (a stored sign-in still works, so nobody can lock an owner out of
  their own browser). Reset mails: one an account per 15 minutes; reset tokens are stored hashed.
- **The admin dashboard** (port 4002) answers on 127.0.0.1 only (`MISTHOLLOW_ADMIN_HOST`
  overrides) and every API call needs the key in `lib/admin_key` (made on first start; the page
  asks once). It refuses other host names (DNS rebinding), POSTs from other sites and non-JSON
  POSTs; player names are put on the page as text (an XSS), its player list works again, and the
  shutdown button that did nothing is gone.
- **Leaks**: the map server no longer logs session tokens in request paths (the dashboard showed
  that log); `account password/recover/reset` lines are echoed masked, not kept for `!` and not
  seen by `snoop`; the web bridge no longer drops the connection when someone types a bare number
  (it parsed as JSON); a hidden signal cut in two by the network is put back together.
- **Tests**: `tests/test_security.py` — offline (hashing and its upgrade, tokens, limits, the
  login prompts with a fake connection, masking, redaction) and live (the old way in refused,
  the limits, `remember`/`resume`/`forget` over telnet and through the bridge, the dashboard's
  refusals). Checked in a browser: `/play`, `/platformer` and `/2d` sign in, come back without a
  password, and log out.

### Sound and music for /play (owner's pick, second of four)
- **The engine** (`world3d/audio.js`): one AudioContext, started by the first click or key (as
  browsers require), with buses for music, effects, ambience and the interface under a master
  volume and a soft limiter; at most 10/16/24 sounds at once by graphics quality, each sound with
  its own minimum gap; sounds in the world are placed left or right of the camera and fade with
  distance from where it looks. Every recorded effect is fetched and decoded right after the
  first click (0.7 MB); one asked for before it has loaded plays as soon as it has, if that is
  within 0.4 s. The tab going to the background suspends it.
- **What sounds when** is a pure-data table (`world3d/soundtable.js`): every combat event and
  blow (swing, bow, bolt, hit by fist or blade, critical, hurt, miss, dodge, parry, block,
  resist, heal, buff, debuff, stun, a creature's death and the hero's, a wind-up's rising
  warning, its slam, a broken wind-up, a fizzle); skills and spells by phase and school (a charge
  while it gathers, a whoosh as it flies, the school's sting where it lands — the 2D client's
  stings, ported — with a recorded impact for frost, holy, fire, nature, physical); footsteps by
  what is underfoot (grass, stone, wood, carpet, snow, dirt, a splash in water) and stride;
  doors only when one really opens, closes or locks; hops and teleports; windows (a bag, a book,
  cloth), buttons, toasts, coins when gold changes hands, level-up and quest fanfares.
- **Ambience**: the 2D client's 25 synthesized room tones (wind, birds, drips, clanks, hums), by
  the zone's look.
- **Music**: six CC0 loops — town, wilds, inn (taverns), dungeon, dark (necropolis, swamps,
  shadow, fire), battle — crossfading between zones and looping without a gap (two decks); the
  battle track comes in 2.5 s into a fight and leaves 6 s after it (a one-blow scuffle doesn't
  swap the music). Streamed (`<audio>`), so the map server now answers Range requests (206) for
  audio files.
- **Settings**: Sound on/off and sliders for master, music, effects, ambience and interface
  (kept per browser; the 2D client's "ambience off" carries over until set here).
- **Sources** (all CC0, `world3d/audio/CREDITS.md`): Kenney's Impact Sounds, RPG Audio,
  Interface Sounds and UI Audio (127 effects); music by cynicmusic (Town Theme RPG, Battle Theme
  A), pauliuw (The Field of Dreams), RandomMind (The Old Tower Inn) and HaelDB (Cave Theme,
  Creepy Forest). 7.3 MB in all. Rebuilt with `tools/audio/fetch.sh && python3
  tools/audio/build.py` (ffmpeg from PATH or `pip install imageio-ffmpeg`).
- **Checks**: `tests/web/sounds.test.mjs` (every sound playable, every file built, every combat
  event and result covered, every name the game plays exists, every zone look has music, a room
  tone and footsteps, every synth runs); `/play?demo&gallery=sounds` plays every sound, sting,
  bed and track; in a browser, the sounds play in a fight, while walking and opening windows, the
  battle music crossfades in and out, and the probe suite still reports no page errors.

### Real-time combat for /play (owner's pick, third of four)
- **Opt-in, on by default**: /play's map socket subscribes with `combat:'action'` (Settings →
  Real-time combat, On/Off, kept per browser). A player is in action mode while one of their
  live /play clients asks for it — a closed tab, a lost socket or a newer login puts them back
  on rounds at once. Telnet and `/platformer` keep the 3-s round and today's rules.
  `Config.ACTION_COMBAT = False` turns it all off.
- **Same pace, real feel** (`src/action_combat.py`): swings stay 3.0 s apart, so damage per
  second (and every balance number) is unchanged. What changes:
  - F lands the first blow the moment it is pressed (`webattack`), then the swings come by
    themselves every 3 s while the foe is in reach; the button wears a ring that fills to the
    next swing and turns gold in the last 0.6 s — press F then and that blow lands perfectly
    (pressed earlier, that swing can't be perfect any more, so holding F never pays);
  - skills and casts resolve at once behind a 1-s global cooldown ("Not ready yet."; the bar
    sweeps; brace, sidestep, interrupt and flee never wait; a refused skill gives its second
    back);
  - creatures fighting you act on their own staggered clocks (a turn every 3 s ± 0.3 s, the
    first a moment after they engage), and their wind-ups land 2 s after they are declared
    (marked 2 s long) — step out of the red ring and the client tells the server at once;
  - rituals, pets, a companion, a burning mount and the marquee effects stay on the 3-s round.
- **Under it**:
  - combat events are buffered per action (a round, a swing, a skill) instead of behind one
    global hold, so overlapping actions never delay each other; a mark taken inside the hold
    keeps an action ahead of its wounds;
  - the round says what became of each swing (hit, crit, miss, dodge, parry, block, a lost
    turn) instead of the wrapper reading it from the text;
  - the end of a round (rituals, pets, companion, mount aura) is its own step
    (`CombatHandler.round_extras`), which a real-time swing leaves to the round;
  - every turn restarts a swing clock in both modes, so switching mid-fight never brings two
    swings close together.
- **A fix it found**: bosses (bosses.py) were also given the ordinary bruiser's crushing blows
  on top of their own rotation. They no longer are, so **every boss hits less hard** — the
  marquee balance pass (next) retunes for it.
- **Not needed yet**: stuns, blindness and other per-swing counters keep their rate because
  swings stay 3 s apart (a `stunned_until` clock waits for faster swings).
- **Tests**: `tests/test_action_combat.py` (offline: event buffers, swing results, who is in
  action mode, the round leaving their swings alone, webattack, the cooldown and its wording,
  perfect timing, creature turns and 2-s wind-ups, the boss fix), `tests/test_combat_action.py`
  (live: first blow at once, then every 3 s, a refused second skill, a wind-up landing 2.0 s
  after it was marked, switching off mid-fight), `tests/web/actionclock.test.mjs`;
  `test_combat_v2` still covers the round.

### Marquee balance pass (owner's pick, fourth of four)
- **Measured, not guessed**: `tools/balance/sim.py` plays every class's marquee quest with the
  real combat code on a simulated clock (a quest takes about a second), alone and in groups of
  2, 3 and 6, at levels 45-60, in both combat modes. It found that the scale's idea of a hero's
  damage was off: the median hero deals 204 a round at 45 and 332 at 60 (`dpr()` guessed 150 to
  197), and a warrior deals 2.4 times what a mage does (`CLASS_K` guessed the mage stronger).
  A lone warrior's elites died in half the intended time; a mage's took a third longer.
- **The quests now** (`src/marquee_scale.py`):
  - health comes from the measured damage of everyone who set out;
  - damage is scaled by what the class (or the party) can stand (`CLASS_D`, measured: a
    thief's creatures hit at 0.56, a paladin's at 1.33), by kind (an elite x2, a ritual's
    waves x0.7) and by level (1.8% a level above 45). The quest keeps the classes that
    embarked.
  - Alone, an elite takes about a minute and a warden two; the trial's boss takes three
    minutes and two thirds of the hero's health. Deaths are rare (0.18 a quest), and no
    group lost a fight.
  - A lone hero who knows the way finishes in 40-81 simulated minutes; the report says what
    that means for the two-hour goal and which number to raise.
- **Fixes that change every fight** (found on the way):
  - creatures now wear the armour their zone files give them (`armor_class` was ignored);
  - a mage's INT now helps them hit and a thief's DEX adds damage (a case mismatch);
  - warrior skills grow with level;
  - Charm Person, sleep and blindness no longer take hold on creatures flagged against them,
    or on bosses;
  - a shield spell cast again renews itself instead of stacking (stoneskin five times was five
    shields);
  - a boss whose blow landed on a pet froze for the rest of the fight;
  - quest creatures with a party's health were handed the world's "boss" kit (a slam on
    everyone in the room every 8 s, fear, adds).
- **The report**: `docs/balance/marquee.md` covers the method, the assumptions, the
  calibration, every table, and how to rerun it.
- **Tests**:
  - `tests/test_balance.py`: the fixes, the scale, party sizing, and one quest simulated.
  - `test_marquee`: a mixed party's creatures follow its classes.
  - `test_marquee_abilities`: Thousand Shadows' test foe is sized to the damage curve.

### Spells and abilities that do what they say (owner: "What else needs work or polish?")
A harness cast every spell in every class book the way the 3D bar casts it, on a groupmate or a
foe as the spell asks, and diffed everything that changed. `tests/test_spells_audit.py` keeps
it that way.
- **Cooldowns**: a spell's cooldown was never enforced (Meteor Storm's ten minutes was zero). It
  now holds, is kept on the character, refuses at no cost ("…is not ready yet (Ns)") and shows
  on the bar.
- **Group and room spells**:
  - group spells now reach the group; they buffed only the caster (Quicken, Epic Tale,
    Refrain of Hope, Song of Battle, Anthem of Defense, Shared Burden);
  - room spells now strike the foes; their curses fell on the caster (Chord of Disruption
    silenced the bard, Siren Song charmed them, Meteor Storm stunned the mage, Crypt Winter
    slowed the necromancer), and Meteor Storm, Crypt Winter and Void Eruption did no damage;
  - every area spell shares one rule for who is a foe: those fighting you or your group, else
    the attackable creatures here; never groupmates, pets, service NPCs or quest figures
    (Earthquake, Blood Boil, Corpse Explosion, Apocalypse and Resonance Burst hurt groupmates;
    Mass Charm charmed them);
  - a room spell with nothing to strike is refused at no cost.
- **Spells that did nothing now do what their description says**:
  - Requiem, Hallowed Ground, Font of the Vigil, Cleansing Rite, Unfettered, Summon Gargoyle
    (a new pet), Soul Harvest, Apocalypse (necromancer), Divine Intervention;
  - Travelling Grace's hops, Serenity's cleanse, Chain Lightning's leaps, Cold Snap, Resurrect
    (gives back the experience a death took);
  - Identify was never wired to its handler.
- **Effects that were only displayed now work**:
  - sanctuary, invulnerability, mana shield, protection from evil/good, divine guardian;
  - guardian spirit, fire shield, ice armor;
  - mirror image, displacement and blink (blows find images);
  - Mirrorward (reflects a spell, creatures' too);
  - haste (an extra swing), slow, stun (lost turns; a boss staggers);
  - charm (stops fighting), fear, paralysis, entanglement;
  - silence and deafen on creatures (no spells), a song's fumble;
  - spell resistance and saving throws, beacon of light, detect evil.
  - Titan's Wrath now cleaves, and its invulnerability lasts the intended ~12 s, not 30.
- **Casting by name**: `cast` takes the name the spellbook shows ("Cinderlance", "Cure Light
  Wounds"), and `spells` lists those names.
- **Commands that replaced each other**: 19 were defined two or three times, and only the last
  ran.
  - Restored: shop `show <item>`, inn lockers (the house chest at home), an immortal's
    `save <zone>` (also `zsave`), cure potions through `quaff`/`use`, and `pet`.
  - Titles: earned ones or your own words.
  - The warrior's rage and the cleric's favour bars errored.
  - Halo of Reckoning/Divine Storm hit shopkeepers and pets and never killed.
  - The dead copies are gone.
- **Warrior talents**: Warlord's Presence and Perfect Form answered "Huh?". They now work on
  Momentum: repeats don't reset it; Perfect Form builds two a blow.
- **Stuns that never ended**: Bash (30%), Kidney Shot and a creature's paralysing touch set the
  target's position to "stunned", which nothing ever reset. A creature lost nothing by it (its
  swings ignore position), but a boss so "stunned" never cast, enraged or changed phase again
  for the rest of the fight: a paladin could bash any boss into a punching bag. All three now
  go through `CombatHandler.stun`: the target loses a round (two for a full Kidney Shot) and a
  creature its wind-up; a boss only staggers, and keeps its feet under a bash.
- **Balance measured again** (`docs/balance/marquee.md`): the fixes moved what classes deal and
  stand, so `marquee_scale` `CLASS_K`/`CLASS_D` were recalibrated (the mage deals 0.58, the
  necromancer 1.10; the paladin stands 1.77, the warrior 0.94, the necromancer 0.60). The
  simulator stopped re-raising a necromancer's bone knight once a gargoyle stood by; it counts
  only the raised dead now. Lone heroes die 0.03 times a quest (0.18 before); no group fight
  was lost in 324 simulated group quests.
- **Tests**: `tests/test_spells_audit.py` (every book spell cast as the bar casts it: no errors,
  no silent no-ops; group and room targeting, cooldowns, names, the effects above, stuns, no
  command defined twice, every class-book skill a command).

### The 2D clients retired, and server polish (owner: "We don't need 2d")
- **`/play` is the only web client.**
  - The five scripts it borrowed from the Phaser client (the socket layer, the text parser, zone
    themes, item icons, room layouts) moved to `src/web_isometric/shared/`. They are served
    like the rest of `/play`: immutable under `/v/<commit>/`, gzipped.
  - The platformer, the top-down `/2d` client, the old isometric `/iso` page and the rest of
    their folder (Phaser, tiles, sprites, scenes) are deleted; their URLs redirect to `/play`.
    The Settings "Old 2D client" button is gone.
  - The endpoints the 2D windows used (`/shop`, `/stable`, `/travel`, `/almanac`, `/talents`,
    and the rest) stay: the next pushes build `/play` windows on them.
  - The 2D art packs (`src/web_isometric/sprites/`, 91 MB; `art/`, 9.6 MB) are unused now. They
    stay until the owner says otherwise.
  - Tools: `tools/gauntlet/capture.js` and `duo.js` drive `/play`; the onboarding capture and
    the 2D room checker (`tools/qc_platformer_rooms.js`) are retired.
- **Web text is no longer hard-wrapped.** The server wrapped every message at 80 columns, so
  `/play`'s chat broke mid-sentence and lost colours mid-line. The bridge now announces itself
  (`server.WEB_MARK`), and only telnet is wrapped.
- **Log rotation**: `log/mud.log` rotates at 10 MB, and five old files are kept.
- **Quieter logs**: a telnet player's every move logged two lines (one a warning, "NO connected
  clients"), and a `/play` page load logged a line for each of its few hundred files. Both are
  debug now.
- **Tests**: `tests/test_web_client.py` (live): the old URLs redirect, `/play` loads its shared
  scripts and nothing from the 2D folder, telnet wraps and the web doesn't.

### `/play` essentials: loot, shop, talk, reactions, who, help (Push 16)
- **Loot you can see** (`world3d/loot.js`, `lootlogic.js`): corpses lie under a slow gold ring
  (see "The dead" below), anything else on the ground as its painted icon bobbing over a ring in
  its rarity's colour. A click walks over and takes it (a corpse: everything in it; taken once
  within reach, so a spot hard against a wall still works); a right-click offers Loot / Look
  inside or Take / Look. Settings has **Auto-loot** (the server's own `autoloot`).
  - Fixtures are the room's: the server never let anything resist `get`, so a player could
    pocket the temple fountain, the bank's ATM or the quest board, and `get all` took them all.
    Objects now know when they are fixed (`Object.fixed`: furniture, a fountain, or 1,000
    weight and up); `get` refuses them, `get all` leaves them, and the payload marks them.
- **The dead** (`world3d/corpse.js`): a creature that dies falls where it stood and stays there as
  its corpse, darkened (on its own copies of the materials) over a dark stain. A body with a death
  clip holds its last frame; a body built in code plays its own death; anything else, or one still
  standing when its death ends (a bat, a crouching beetle), tips onto its side. A corpse come upon
  later gets the same creature's body, lying on the room's spot for it. One killed in a single blow
  (never seen hurt) still falls: its corpse claims it in the same payload. A hero's corpse is a
  grave: a mound, a ring of stones and a wooden marker. Gallery: `/play?demo&gallery=corpses`;
  tests: `tests/web/corpse.test.mjs`.
- **Shop window** (`hud/shop.js`): right-click a shopkeeper → Shop. Buy and Sell tabs with the
  server's prices (`/shop`), icons, and why a row can't be bought or sold; buying goes by the
  item's number in the shop's list (`buy 3`), selling by the word the MUD knows it by.
- **Talk window** (`hud/talk.js`): right-click → Talk walks over and opens what they say, the
  dialogue's responses as buttons, the quests they offer (Accept) and finished quests to hand in
  (Turn in).
- **A marked blow coming** (`world3d/reactions.js`): when a creature winds up at you, a prompt
  shows the keys that answer it — **Q** brace, **E** sidestep, **X** interrupt (a cast the
  server calls interruptible) — with the time left. They are everyone's (`brace`, `sidestep`,
  `interrupt`) and no longer need a slot on the bar. E is the door key otherwise.
- **FLANKED**: a warning when two or more creatures are on you; a class resource at its peak
  (Momentum 10) glows.
- **Who** (P, `hud/who.js`, `/who`): everyone online (your group first) and who is in the room
  with you; a name opens the same menu a right-click would. `who`'s idle times were never shown
  (it read an attribute nothing set); they are now.
- **Help** (H, `hud/help.js`, `/help`): the controls, and a search over the game's 763 help
  topics.
- **Small things**: graphics quality applies at once (only smoother edges wait for a reload);
  the menu's dead `data-cmd` handler and the inventory's unused `sell` sound are gone.
- **Tests**: `tests/web/essentials.test.mjs` (the windows' logic, the ground's items, the
  reaction keys); `tests/test_web_client.py` checks `/who`, `/help` and fixtures live.

### `/play` progression and travel: talents, almanac, travel, stable, bank and mail, legend, world map (Push 17)
Six windows on the menu (now four buttons wide), each with its key, built on the endpoints the
2D client used to read:
- **Talents** (N, `hud/talents.js`, `/talents`): the class's trees tier by tier, points to spend
  at the top. A talent that can be taken now is lit, and a click takes it (`talents learn`);
  the server keeps the rules (a tier opens at five points in its tree a tier, prerequisites,
  top ranks). Warriors grow by doctrine instead, and the window says so.
- **Almanac** (Y, `hud/almanac.js`, `/almanac`): the daily streak and what today, tomorrow and
  day seven bring; achievements by category with progress bars, nearest to done first; titles
  earned (Wear); collections and gear sets.
- **Travel** (T, `hud/travel.js`, `/travel`): the waypoints found, what each costs and why one
  can't be reached now (where you stand, the cooldown, gold); Travel goes.
- **Stable** (U, `hud/stable.js`, `/stable`): mounts (Mount / Dismount, and the ones a stable
  sells), pets and companions with their health (Dismiss).
- **Bank and mail** (B, `hud/services.js`, `/services`): gold in the bank (Deposit / Withdraw at
  a bank), mail (Delete; Write fills in `mail send`), what is kept at an inn.
- **Legend** (G, `hud/legend.js`, `/legend`, `/doctrine`): prestige specialisation at level 50,
  the server's leaderboards with your own place, and for a warrior the war doctrine and the
  evolution of their abilities.
- **The whole world** (the big map's World tab, `hud/worldmap.js`): every room you have
  explored, coloured by zone, zone names over them, you marked; drag to pan, the wheel zooms,
  hover for a room's name. New `/explored` (for the signed-in session only) gives the rooms
  explored.
- **Give…**: right-click another player near you → a short list of what you carry, or gold.
- **Tests**: `tests/web/progression.test.mjs` (talent tiers and ranks, achievements' order,
  travel rows, gold amounts, doctrine rows, the world map's view); `tests/test_web_client.py`
  checks `/explored` and each window's endpoint live.

### Balance follow-ups: real quest times, zone bosses, the bone knight, caster shields (Push 18)
Measured with the simulator; the findings and numbers: `docs/balance/marquee.md` ("Measured
again after the balance follow-ups", "Zone bosses") and `docs/balance/bosses.md`.
- **Real quests are written down** (`src/marquee_log.py`): acceptance, each stage's end, deaths,
  the finish or abandonment, with the party, its classes, its level and the combat mode, in
  `lib/marquee_runs.jsonl` (runtime data). `marquee stats` (immortals) sums them up by class and
  party size: the number to tune the quests' length against once real players have played.
- **Zone bosses** (the 20 dungeon bosses from level 12 to 60) are sized for a lone hero at their
  level, like a marquee trial's boss (`bosses.size_zone_boss`): about two minutes alone, under
  one for a party of three (before: a party of three felled any of them in 2-6 rounds). Each
  boss's own blows are weighed by a measured share (`ZONE_BOSS_DAMAGE`,
  `tools/balance/bosses.py --calibrate`) so the median lone hero loses about half their health
  at the worst moment. Raid bosses above the level cap and the marquee quests' own are left as
  they were.
  - A creature's poison and a boss's adds now weigh as its blows do (they ignored the share).
  - A summoning boss calls only while fewer than twice the call still stand (the Goblin King's
    goblins were endless).
  - A lone mage or necromancer still usually dies at a zone boss's level; the doc says why, and
    what would change it.
- **The bone knight**: its shield wall lasts three rounds and rests six (it was up two rounds in
  three), comes down out of a fight, and its taunt turns only the creatures fighting its owner's
  side, never a groupmate.
- **Caster shields** gain 2 a level, not 4 (at 45 a mage's wards held twice their health).
- **Damage over time finishes a creature** (credited to whoever it fights); a player is never
  killed by it.
- **Marquee numbers**: `CLASS_D` for the mage 0.55 and the necromancer 0.50, measured again
  after the shield and knight changes; the other classes didn't move.
- **The simulator no longer saves its heroes**: an achievement saved them, and thousands filled
  `lib/players` and the leaderboards.
- **Tests**: `tests/test_marquee_log.py`; `tests/test_balance.py` (zone bosses: sizing, adds,
  poison, the summon cap); `tests/test_spells_audit.py` (damage over time, the bone knight).

### Gear you can see: heroes dressed in what they wear (Push 19) (owner: "make equipment look unique on players… scale in detail as the player level and gear gets better")
Until now a hero's 3D body came from the class alone and never changed; other players' gear
wasn't even sent. Now every hero wears their gear, and everyone around sees it change.
- **What the server says** (`src/gear_look.py`): each character's `look`, the one place items
  are read.
  - Per worn piece: kind (sword, bow, mace, helm, hood, cloak…), hands, armour weight (cloth,
    leather, mail, plate), material and colour (ramp names), element, named set and a tier 0-5.
  - A `sig` hash, so a client re-dresses only on change.
  - The item level comes from `min_level`, else the strongest creature that carries or drops
    the item (nearly all gear), else its set's level range. It now shows in the tooltips.
  - Tiers: level <8 → 0, <18 → 1, <30 → 2, <42 → 3, else 4; one more for magic, glowing,
    humming, superior or enchanted gear; a legendary is 5.
  - Sent in your payload, in other players' entries, and as a signature in combat updates.
  - Wear, wield, remove or a disarm relays the new look to the 3D clients around at once
    (`web_map.relay_look`).
  - `tools/qc_gear.py` shows how all the world's gear is read.
- **The art** (`tools/art3d/build.mjs` `equip`, `tools/art3d/ramps.json`): every body part and
  piece of the five KayKit adventurers on one rig.
  - Their four textures (grids of colour ramps) merged into one 366-column palette, with ramps
    for materials, cloths, elements, races, and the class and named-set colours.
  - Worn and dark variants of each.
  - Plus the pack's painted shields, painted greatsword and quiver.
  - 627 KB (`art3d/chars/equip.glb` + `equip.json`).
- **Dressing** (`world3d/gearlook.js` plans, `world3d/equip.js` builds):
  - What a hero wears is merged into one skinned mesh: 2 draw calls however much they wear,
    recoloured by moving UVs between palette columns. Re-dressing swaps the geometry in place.
  - A class keeps its silhouette: the torso, arms and legs come from another model only when
    armour is two weight steps from what the class starts in (a mage in plate gets the knight's
    torso).
  - Metal and leather take the item's material, cloth its colour, its set's or the class's;
    tier 0 is dull and worn.
  - The bow, the mace and the lute, which no pack has, are built in code in the same style
    (`world3d/procgear.js`).
  - The swing follows the hand (two-handed, dual blades, a bow, a staff), and a two-handed
    weapon idles two-handed.
  - The hero, other players, the portraits, the character sheet and the class preview at
    creation all use it.
- **Gallery**: `/play?demo&gallery=gear` (`&only=tiers|kinds|heads|shields|capes|mixes`,
  `&cls=`, `&tier=`): every class at tiers 0-5, every weapon kind, every head and shield, cloaks,
  and mixed bodies.
- **Tests**:
  - `tests/test_gear_look.py`: item levels, how items are read, the starting looks, tiers, the
    relay.
  - `tests/web/gearlook.test.mjs`: silhouettes, bodies by weight, heads, colours, swings,
    shapes.
  - `tests/web/equipkit.test.mjs`: one rig, every part, where pieces hang, the palette.
  - `tests/web/probe_play3d.js gear`: two browsers; one wields a greatblade and the other sees
    it.

### Finer gear, finer detail; standing that shows (Push 20)
The second half of the owner's ask: detail that grows as gear and level do. Everything new is
merged into the same one mesh (no extra draw calls), and placed from the shape of the piece it
sits on, so it fits every body.
- **Every weapon kind** (`world3d/procgear.js`): hammers and mauls, spears, polearms, scythes,
  picks, whips, claws, an orb, a censer, a lantern and a torch. Instruments by name (a lyre, a
  harp, a flute, a drum, a horn; a lute otherwise), and a crown or a circlet. The server now
  names the instrument and the crown it reads (`src/gear_look.py`), held or wielded.
- **Detail by tier** (`world3d/gearlook.js` plans it, `world3d/equip.js` places it):
  - 0: dull and worn.
  - 1: clean.
  - 2: silver trim, a stone in the pommel, a boss on the shield, a plume on the helm (each
    class its own colour: crimson, royal blue, white…).
  - 3: gold trim, pauldrons on heavy armour.
  - 4: gems glow in their element's colour (or the set's), and sparks rise off the weapon.
  - 5: a legendary: shining gold trim, a slow pulse, a sunwheel on the ground under its bearer.
  - Four pieces of one of the ten named sets draw a ring in the set's colour under the wearer.
- **Renown by level**:
  - 10: the class's cloak.
  - 20: the class's emblem on it, in silver (chevron, sunburst, eye, skull, fan, drop, leaf,
    cross, lyre).
  - 35: a mantle on the shoulders in the class colour.
  - 45: gold, and faint motes in the class colour.
  - Prestige: the emblem shines.
- **How it is drawn**:
  - Glow: palette columns marked `~glow` light themselves, through a few lines patched into the
    material's shader. It doesn't use `material.emissive`, so hit flashes still work.
  - Motes, sparks and rings (`world3d/adorn.js`) live as long as the gear is worn. They show for
    the hero and the nearest 4 (medium quality) or 8 (high) others within 22 m; none at low
    quality.
  - A blow trails its weapon's element or a legendary's gold.
  - A torch in the light slot is carried in a free hand; a lantern hangs at the hip.
- **Fixed on the way**: every tube built in code (shafts, bow limbs, blades) was wound
  inside-out, so it drew dark. The Push 19 bow, mace and lute are now lit properly too.
- **Gallery**: `&only=` also takes `held` (focuses, lights, instruments), `renown` (one class
  at each band) and `crowns`; tiers now show the add-ons and the glow.
- **Tests**:
  - `tests/web/gearlook.test.mjs`: every shape and add-on is whole, faces outward and is painted
    from real columns; detail by tier; renown bands; crowns and lights; what glows; hanging
    shapes turned in the hand.
  - `tests/test_gear_look.py`: instruments and crowns by name.
  - `probe_play3d.js gear`: a renowned hero is adorned.

### The world dressed alike: people in their own gear, every race its own (Push 21)
- **People wear what their zone gave them.** About 400 of the world's creatures have gear named
  in their zone files (a cityguard's sword, a knight's blade, a shadow assassin's obsidian
  dagger). Their entries now carry the same `look` a player's do, about 100 bytes each
  (`map_system._npc_look`).
  - The client dresses them as it dresses players, but keeps the body their trade gives them
    (`world3d/looks.js` `npcDress`: a guard stands as a knight, a priest in robes). Their
    colours are the trade's class (a guard a paladin's, a thief an assassin's).
  - A wolf handed a sword stays a wolf: only creatures drawn as people are dressed.
  - Gear every creature is handed when its zone names none is not shown.
  - A creature's level is no standing: no renown flourishes on a shopkeeper.
- **Race** (`world3d/gearlook.js` `RACE`):
  - Each race has its skin on every part of the body: elf, dark elf (white hair too), half-orc,
    dwarf, halfling and gnome. A human keeps the model's own skin, and human creatures vary
    between four tones.
  - Each race has its build: dwarves short and broad, halflings and gnomes small, half-orcs
    tall and broad, elves slight. The sizes match those creatures already had.
  - Players' race comes from the server's look; creatures' from their words (a "dwarven smith").
    At character creation the class preview already shows the race just chosen.
- **Shop gear is ordinary**: an item level came from the strongest creature carrying the item,
  and Midgaard's level-33 shopkeepers made a plain shop sword tier 3 (gold trim, a pommel stone).
  What a shop sells now counts as its weakest carrier's level, at least 8 (bought new: tier 1).
- **Gallery**: `&only=races` shows every race in a warrior's and a mage's starting gear, and the
  four human tones; `&only=people`, people the world dressed (a guard, a dwarven smith, a drow
  assassin, a half-orc warrior…).
- **Tests**:
  - `tests/test_gear_look.py`: shop gear tiers; a cityguard's look; no renown for creatures; no
    look for auto-equipped creatures.
  - `tests/web/gearlook.test.mjs`: race skin, hair and build; people dressed by trade and race;
    beasts and the ungeared left alone.
  - `probe_play3d.js gear`: the guards by the temple wear their swords.

### Endgame gear that works; a bow shoots whoever holds it (Push 22)
- **The endgame items' stats load.** 62 items in the level 40-70 zones (the Cinderbrand
  Greatsword, Coral Plate, the Heartstone of the Expanse…) gave their stats as an `effects` dict
  the server never read, so they had none.
  - They now load as the affects the game reads (`objects.effects_as_affects`): to hit, damage,
    armour (lower is better), the six attributes, health/mana/moves, regeneration, backstab,
    stealth as sneaking. The yes/no ones (water breathing, haste, corruption immunity) become
    item flags.
  - Copies saved before the fix take their stats from the prototype once.
- **Gear speeds regeneration.** A `hp_regen`, `mana_regen` or `move_regen` affect is a
  percentage (+20 heals a fifth faster). Nothing read them before, on any item.
- **What gear still doesn't do** (true of every item, not only these; left for a decision):
  - Health, mana and moves from gear only show in `score`: the real maximum never rises. That
    needs one effective maximum read everywhere health is capped. (Done in Push 23.)
  - Wisdom, constitution and charisma from gear change nothing. (Done in Push 23.)
  - Nothing reads resistances, water breathing, life drain, song power or corruption
    immunity, and haste only comes from spells.
- **The balance simulator chooses gear right.** It scored a lower (better) armour class as
  worse; it now reads an item's `effects` too, and a ranger wields a bow when the world offers
  one at its level.
- **A bow shoots whoever holds it** (`combat_range.auto_range`, owner's pick):
  - The ordinary blow's reach follows the weapon in hand: a bow 16 m, a crossbow 14, a thrown
    weapon 10, anything else 2.5.
  - A mage or a necromancer still throws a bolt at 10 m whatever they hold; a ranger with a
    sword swings it. Rangers start with a bow.
  - The client follows: reach, chasing or holding ground, the projectile, the swing.
- **Measured again** with the real combat code (`docs/balance/marquee.md`, "Measured again with
  the endgame gear"):
  - Heroes at 50-60 deal 10-17% more. `dpr()` rises 4.5% a level from 45 (3.3% before); below
    45 it keeps the curve the zone bosses were sized by.
  - `CLASS_K` follows (the ranger 0.99 to 0.73: a bow's blows are lighter than the swords it
    used to fire).
  - What classes can stand now falls about 1% a level, so the creatures' blows rise 0.9% a
    level (1.8% before). `CLASS_D` is measured again for every class: the mage 0.64, the
    paladin 1.88, the necromancer kept at 0.50 (its deaths come all at once).
  - Played through alone at 45-60 with the new numbers (three quests each), quest bosses cost
    most heroes 40-83% of their health, with at most a third of a death a quest outside the
    necromancer.
  - The zone bosses' damage shares are measured again: the level-60 gate guardians 1.2 to
    0.95. A lone hero still loses about half their health to one at their level.

### Gear health, mana and attributes that count (Push 23) (owner: "Make gear health, mana and stats actually work")
Before, an item's +200 health, +30 mana or +2 constitution showed in `score` and did nothing:
the real maxima never rose, and only strength, dexterity and intelligence from gear reached the
to-hit and damage numbers.
- **A player's attributes and maxima count what they wear, everywhere** (`player.py`
  `GEAR_STATS`).
  - `player.con` is their own constitution plus every worn piece's and set's.
  - `player.max_hp` is their own health plus their gear's; the same for mana, moves and all
    six attributes.
  - So gear reaches everything that reads them: health and mana caps, healing, regeneration
    (constitution, intelligence, wisdom), armour class from dexterity, spell saves (wisdom)
    and criticals (intelligence), skills' attribute bonus, perception, abilities' formulas.
  - Items may name a stat short or long (`con`, `constitution`) and health or mana by any of
    their names (`hp`, `max_hp`, `hitpoints`; `mana`, `max_mana`).
- **Their own values stay their own.**
  - The save keeps the base, so nothing grows with each save.
  - A level, a spell's +2 and its end move the base only.
  - Character creation and New Game+ set it outright.
- **Taking gear off lowers the maxima**, and health, mana and moves come down with them after
  the command. Putting it on raises the maxima; regeneration fills them.
- **Shown where you look:**
  - `score` gives each attribute as its own value and what gear adds, `Con: 13(+2)`, and the
    real maxima.
  - The `/play` character sheet shows the total with a small +2 beside it, and its parts on
    hover.
- **Creatures are as they were:** their gear counts only in their blows.
- **Measured again** (`docs/balance/marquee.md`, "Measured again with gear health and
  attributes"):
  - Lone heroes are sturdier with their gear's health, so quest creatures hit harder for most
    classes: the bard 0.78 to 1.04, the paladin 1.88 to 2.07.
  - Casters' damage rose with gear intelligence, so their creatures got more health.
  - The necromancer's longer fights made it frailer: 0.50 to 0.45, where it dies 0.1-0.2
    times a quest.
  - The zone bosses' damage shares were measured again: most rise (the Goblin King 0.25 to
    0.40). A lone hero still loses about half their health to one at their level, and deaths
    fall from 49 to 39 in 360 fights.
- **Reading an attribute** costs about 1.4 µs; the gear's totals are worked out again only when
  what is worn changes.
- **Tests:** `tests/test_item_stats.py`:
  - Coral Plate's +200 is a real maximum; the shard's +2 reaches all six attributes.
  - Legacy names count; dexterity from gear improves armour class.
  - The save keeps the base, and loading adds the gear again.
  - Levels and spells move the base; taking gear off lowers health.
  - Dexterity from gear counts once in to-hit.
  - A creature's attributes stay its own.

### Resistances, saves and haste from gear (Push 24) (owner: "Make resistances and haste from gear work too")
Before, an item's fire or poison resistance, its saves and its haste were listed and did
nothing. Every spell and creature attack also arrived as untyped damage, so no resistance
could have applied anyway.
- **Gear turns aside each kind of harm** (`player.py` `Player.resistance`, applied first in
  `take_damage`).
  - The kinds: fire, frost (items say cold), lightning, poison (acid too), disease, shadow,
    necrotic (a shadow ward covers it as well), holy, arcane, nature and sound.
  - Items name it `<kind>_resist`; set bonuses count. A ward never turns more than 75%.
  - The hero is told what their gear turned aside: "Your gear turns aside 12 of the fire
    damage."
- **Every source now says what kind of harm it is**, so a ward has something to meet:
  - **Spells** strike as their school (`combat_range.spell_school`).
  - **Creature abilities, breaths, lingering effects and hazards** use one table,
    `combat_range.harm_school`. It names the element before the delivery: Frost Breath is
    frost, a breath that names nothing is fire, and Blade Storm and Shockwave are blows.
  - **Boss abilities:** 69 of the 100 are elemental now, among them Fire Breath, Plague Touch,
    Soul Rend, Psychic Storm, Great Bell and Vine Entangle. An ability's own `element` key
    settles a shared name: the Poisoner's Miasma is poison, Pestilence's a disease.
  - **Creatures' spells** (fireball, lightning bolt, ice storm, shadow bolt, magic missile), a
    dragon's fire breath and venomous bites.
  - **Poison, burning and plague ticks** are warded when they land. A bleed is a wound and
    stays unwarded.
  - **Hazards:** gas vents, flames, lightning through water, freezing water, thorns, burning
    rooms, storm lightning and blizzard cold.
  - **Other sources:** a world boss's blast (a lich's is death magic, a dragon's fire); a
    creature's fire shield searing a hero who strikes it; legendary weapon procs, a nightmare
    mount's flames, envenomed blades and a lich acolyte's bolt (these last four matter in
    player-versus-player fights).
- **Saving throws count gear.**
  - Items give saves the old way: a percent where lower is better, so -10 is +2 on the d20.
  - The throw's sign is fixed. Shield of Faith and Holy Aura used to make their wearers
    worse at saving.
- **Spell resistance from gear counts.** It gives a chance to shrug off a spell's hold and
  takes a share off its damage, creatures' spells included (as are Aegis and Holy Aura's).
- **Curse wards** (`curse_resist`) give that chance for a curse to fail.
- **Haste from gear:** an item flagged `haste`, or with a haste affect, gives the spell's extra
  swing about every other round.
  - The Gear of Infinite Motion, the one item that quickens, can be held now.
  - Endgame trinkets with stats and no slot are worn where their name says (the Amulet of
    Light at the neck) or held.
- **Shown where you look:** `score` has a "Gear:" line, and the `/play` character sheet a row
  of chips: fire 20%, saves +2, spells 10%, hasted.
- **Creatures are as they were:** they have no wards. Typing their attacks changes only what
  a hero's gear meets. A fire shield still burns only those who strike in melee, so it no
  longer burns a dragon for breathing on its wearer.
- **Measured again** (`docs/balance/marquee.md`, "Measured again with gear wards"): lone heroes'
  quests moved within noise, and no class got harder. The zone bosses eased a little (a lone
  hero's median worst 49%, from 51%; 35 deaths in 360 fights, from 39), most of all the
  spider queens behind a poison ward. Nothing was retuned.
- **Tests:** `tests/test_item_stats.py`:
  - Wards, their cap and warded harm.
  - Spells strike as their school.
  - Saves work both ways; spell and curse wards work.
  - The held Gear brings an extra swing.
  - Every boss ability has its kind, and an `element` key settles it.
  - A poison tick is warded and a bleed is not.
  - A boss's Fire Breath meets a fire ward, and the hero is told.
  - A creature's fireball meets a fire ward and spell resistance.
  - A creature's fire shield sears less behind a fire ward.

### The world on the Bedlam atlas, step 1: imported, matched, indexed (Push 25) (owner: "use this map as a basis for all our zones… keep all the room names… ensure the exits go the correct directions… index everything and note where we need to build out each zone")
The owner's atlas of Bedlam (`world/atlas/bedlam-atlas.html`) charts 91 zones and 8,038 rooms,
with names, map positions, terrain, doors, and exits that use only north/east/south/west/up/down
(as the game does).

Our world shares its ancestry. Midgaard is the atlas's Garathorm, Rome is its Port Halyon, and
Haon-Dor, Moria, Thalos, Arachnos, the Sewers, the High Tower, Drow City, the Great Pyramid,
Rand's Tower and Welmar's Castle are all there. But names, exits and numbering have drifted.

This push changes nothing in the game. It builds the tools, the room-by-room match and the index.
The re-lay comes in Pushes 26-27, once the owner has reviewed the proposals.

- **The owner's decisions:**
  - The atlas's names win, so the city becomes Garathorm. Our descriptions are reused where
    they fit.
  - Roads, plains, wilderness and forests (the connectors) open with placeholder descriptions.
    New cities and dungeons stay sealed until built.
  - Our zones that aren't on the atlas join it through connectors.
  - Water will need a boat or a raft.
- **`tools/atlas/extract.py`** reads the atlas page into `world/atlas/bedlam.json`: areas, rooms,
  exits, doors (closed or locked), map labels and line bends.
- **`tools/atlas/match.py`** pairs the atlas with our rooms, one to one, in passes:
  - the same vnum and a like name, with Midgaard read as Garathorm;
  - the same vnum and exits that agree;
  - the same name inside zones already linked;
  - walking the same way out of paired rooms, first by name and then by position.
  - It drops coincidences of numbering. A link with no truly alike name is dropped whole, and a
    lone pair stays only when vnum and name both agree.
  - 1,142 atlas rooms pair with ours. 18 atlas zones are ours already, 9 are like one of ours
    (Tunnel of Sticks, Castle of the Apocalypse, Elven Village, Northern Wilderness, Minos, the
    god rooms, the stables, the arena), and 64 are new.
- **Game vnums** (`world/atlas/vnums.json`):
  - A paired room keeps our vnum, so spawns, shops, quests and tests stay valid.
  - In a similar zone, the atlas room that takes over a room of ours keeps that room's vnum.
  - A new room uses its atlas id. If that id is held by a different room of ours (Eden and our
    Straight Path, Ancalador and New Thalos, and others), it becomes 200000 + id. That applies
    to 324 rooms.
- **Our rooms the atlas lacks** (159, in 79 groups):
  - **Annex:** a group with a service or a real place stays and hangs off a free side of the
    atlas room beside it: the Grunting Boar Inn, the bank, the pet shop, the guilds, Welmar's
    prison.
  - **Move:** a group with only creatures or items gives them to the atlas room beside it.
  - **Drop:** a bare path goes; the atlas has its own way there.
- **Hookups for our zones off the atlas** (32 zones):
  - Each joins at the room and side it hangs off now when the atlas leaves that side free:
    the Newbie Zone on the Great Field, Redferne's house, Khaz-Durum, the Sunken Ruins.
  - Otherwise it joins the nearest free side: a dungeon's own rooms first (the Mindflayer's
    Lair in the Sewer), then a connector. The Northern Wilderness chain moves onto the atlas's
    Northern Wilderness.
  - A zone that also has a compass way in drops its old named way (New Thalos's arch).
  - No side is given twice.
- **`tools/atlas/index.py`** writes `docs/world/ATLAS_INDEX.md` and `world/atlas/index.json`.
  - **The owner's review list:** the hookups, the similar zones, and our rooms the atlas lacks.
  - **The build-out queue** (90 zones): open zones first, nearest the temple first.
  - **For every zone:**
    - status, open or sealed, rooms, levels and terrain;
    - creatures, items, bosses and services, and a level band (suggested from neighbours
      when there are no creatures);
    - every cross-zone link;
    - what it needs.
  - **Totals:**
    - 6,753 rooms need descriptions, and 186 borrowed ones need checking;
    - 389 of our rooms' exits differ from the atlas (the atlas wins);
    - the atlas has 672 one-way exits and 154 rooms with no way out;
    - there are 558 water rooms, and 11 places give a boat today.
- **`world/atlas/overrides.json`** holds the owner's corrections: similar pairs, connectors,
  zones kept beside the city, room pairings and hookups. The tools rerun from it.
- **Tests:** `tests/test_atlas.py`:
  - the import is whole, and the matcher is deterministic;
  - every atlas room has one game vnum, and every room of ours is accounted for once;
  - hookups and annexes land on free sides, never twice, and every zone of ours has a way in;
  - the Newbie Zone stays on the Great Field;
  - the index covers every zone and room.

### The world on the Bedlam atlas, step 2: the engine made ready (Push 26) (owner: "just make sure rooms connect as needed")
The owner approved everything the index proposed. This push readies the engine on today's world;
the world itself is re-laid in the next push.
- **A room's zone is the zone file that holds it** (`world.zone_of`), never its vnum's
  hundred-block: the atlas's zones span many (the Trade Road runs from 1301 to 19748).
  - Creatures staying in their zone, faction guards' home zone, `rlist`/`olist`/`mlist`/`zreset`,
    the local map and the who list's area all ask it.
  - `redit` of a vnum not built yet uses `world.zone_of_vnum`.
- **Rooms can store their place on the map** (`room.map`: the atlas's x, y and level).
  - It is saved and loaded with the room.
  - The 3D zone map (`compute_room_coords` with fixed cells) and the world map (`world_cells`)
    honour it; each zone's sheet is set where its cross-zone links put it.
  - Rooms without one are laid out from their placed neighbours, as before.
  - A load-time check logs two rooms on one cell and exits that point against the map.
- **Sealed zones:** a zone file can mark a zone `"sealed": true` (a land still being built).
  - At load, every way into it from outside gets a barred gate: closed, locked and pickproof,
    and never saved.
  - It turns walkers back: "The way into … is barred; that land is still being charted."
  - Opening, unlocking, picking, bashing, `knock` and the web door buttons do nothing, and no
    door change gets through. Creatures don't walk closed doors.
  - An immortal walks through to build it.
  - Lifting the mark opens it again (a real door on that way comes back).
- **Water will need a boat or a raft** (built now, switched on with the re-laid world):
  - Going out on the water takes a carried or held boat (rafts, canoes, the hollow log, the
    boots that walk on water), or flight. Afloat, you move freely; coming ashore never needs one.
  - Without one: "You need a boat or a raft to go out on the water. (Rafts and canoes are sold
    at the quay in the city.)" Captain Stolar at the levee and the sailor sell them, as does New
    Thalos's shipwright, and a hollow log lies at Haon-Dor's fallen tree.
  - Creatures keep to land unless they live in the water.
  - **Why it waits:** on today's world it would put 580 rooms behind a boat. A ford on the only
    way north (the river crossing in our Northern Wilderness) would cut off Arachnos and the
    whole chain to the endgame zones, and some rooms are coded as water by mistake (Haon-Dor's
    spider web). The re-lay removes that ford, fixes those rooms, and proves every place that
    matters can be reached with a raft bought on the way (`Config.WATER_NEEDS_BOAT`).
- **Tests:** `tests/test_atlas_engine.py`:
  - `zone_of`;
  - stored places in the zone map and the world map, the load check, and save and load;
  - a sealed zone: turned back, nothing opens it, never saved, an immortal passes, unsealing
    opens it;
  - water: no boat no water, a raft takes you out, ashore is free, flying passes, land
    creatures stay ashore and river ones don't.

### The world on the Bedlam atlas, step 3: re-laid, every room connected (Push 27) (owner: "Make sure rooms connect as needed")
The world is rebuilt on the owner's atlas: `tools/atlas/build_world.py` writes `world/zones` from
the atlas, the approved match and our content. It reads our world as it was before the re-lay
from git (`PRE_RELAY_REV`), so it reproduces byte for byte.
- **125 zones and 9,251 rooms.**
  - Every atlas zone is a zone: the matched and similar ones under their old numbers, new ones
    under 400 + atlas id.
  - The city is Garathorm Inner City (zone 30, its south part absorbed). The Light Forest and
    most of the dark forest are in the Plains (60). Moria's surface is in the Mountain Range
    (40). The three sewer levels are one Sewer (72). Port Halyon, once Rome, is in the Sea of
    Storms (120).
- **Every atlas room** has its atlas name, its exits exactly as the atlas has them, and its
  place on the map (`map`, so the 3D map lays the zone out as the atlas draws it).
- **Our content carried over:**
  - descriptions where the pairing is sound (Midgaard read as Garathorm);
  - flags, creatures, items, puzzles and the rest;
  - doors where we had the same doorway. The atlas's other doors are closed doors; the 224
    it locks stay unlocked until keys are made.
  - **Ours where the atlas calls a room water but its name says dry land** (3 rooms, Haon-Dor's
    spider web among them).
- **The 6,787 new rooms** carry short placeholder descriptions built from their terrain and ways
  out, flagged `placeholder` (the index counts them as still to write).
- **55 zones are sealed until built:** the new cities and dungeons, barred at every way in.
- **Our rooms the atlas lacked:**
  - 11 annex groups kept and hung off their free side: the Grunting Boar Inn, the bank, the
    guilds, Welmar's prison;
  - creatures and items of the rest given to the room beside them.
  - In a similar zone, every room of ours takes over an atlas room one for one while the atlas
    has rooms to spare, so the arena, the stables and the warrior's quest places keep their
    numbers.
- **Our 32 zones off the atlas** join at the 21 reviewed hookups.
- **Every room connects** (`tools/atlas/connect.py`):
  - The temple reaches every open room, and you can walk back from each.
  - What the atlas left unjoined got a way, 77 in all (each in `world/atlas/connections.json`
    with its reason):
    - 14 of our own old ways in (Drow City from the desert, the arena, Minos);
    - 1 of the atlas's own ways out, walked back: the god rooms lie up from the temple, as they
      always did, because the atlas goes down from them to it (our old `up` couldn't keep its
      direction: the atlas uses the god room's `down` for its stairs);
    - 11 of our own old ways out (Arachnos);
    - 31 ways back along one-way entries;
    - 18 ways to rooms drawn close by on the map (Minos's pits, two cells apart);
    - 2 ways back out of a trap whose natural way was taken (the Plane of Chaos).
  - One atlas stub, with no name and no way in or out, is left out.
- **Water needs a boat or a raft** (`Config.WATER_NEEDS_BOAT` on).
  - Rafts and canoes are sold at the quay (Captain Stolar, the sailor) and by New Thalos's
    shipwright, and a hollow log lies at Haon-Dor's fallen tree. All are reachable on foot from
    the temple.
- **The tutorials' directions come from the map** at load (`quests.apply_routes`: "From the
  Temple, go south three times, then west 11 times"), so they stay right however the world
  changes. The sage's compass hints and `help stable` follow the new layout.
- **Saved places follow their rooms.** A character who logged out, set their recall point or
  left their storage in one of the 432 rooms the re-lay removed comes back in the room that
  stands in for it (`world.renumbered`, from `world/atlas/renumber.json`), not at the temple.
  Companions' respawn rooms follow too. The 20 house plots kept their rooms.
- **Midgaard is Garathorm in all player-facing text** (80 places in code, quests and help). Code
  identifiers (faction keys, achievement and quest ids) stay, and the Garathorm Native
  achievement accepts the new name.
- **The 3D client's zone themes** follow the new numbers: the Northern Wilderness is frozen, and
  the Mountain Range and the Sea of Storms take their rooms' own terrain.
- **The atlas tools** read the pre-re-lay world from git and can write to a scratch folder
  (`ATLAS_OUT`). `tests/test_atlas.py` re-runs them there and checks they reproduce the
  committed match exactly.
- **`docs/world/ATLAS_INDEX.md`** now indexes the built world:
  - the build-out queue (68 open zones, 2,692 open rooms still on placeholders);
  - the ways added, the hookups, the annexes;
  - each zone's needs, and water and boats.
- **Tests:**
  - `tests/test_world_atlas.py`:
    - every atlas room and exit is in place;
    - nothing is added without a reason, and nothing dangles;
    - cells are unique;
    - every open room is reached and walked back from;
    - sealed ways are barred;
    - every shop, trainer, stable, travel point and quest place is reached;
    - a raft is reachable on foot;
    - every room the code names exists;
    - every removed room has a stand-in you can walk to.
  - `test_atlas_engine.py` runs on the atlas places.
  - `test_webmove` no longer pins the old temple's stairs.
  - `probe_play3d.js atlas` walks the temple, the Great Field on the Trade Road, the forest and
    the Newbie Zone in a browser.
  - The door tests (`test_doors` live, `probe_play3d.js doors`) use the High Tower's diamond
    gate. The oak door of Minos they used before went with the re-lay.
- **Balance** (`tools/balance/sim.py`, all nine classes alone at 45-60, three runs each):
  - Every fight came out exactly as before: the same deaths, and the same health at the boss.
  - Only the walking between a quest's places grew, because the atlas's world is bigger:
    2-9 minutes for most classes and 22 for the bard, whose quest spans the most ground.
  - Quests now take 53-82 minutes alone, still inside the two-hour aim.
  - The zone bosses (`tools/balance/bosses.py`) came out identical, line for line: a lone
    hero's median worst fight is 49%, with 35 deaths in 360.
  - Nothing was retuned.

### The God Rooms for immortals only (Push 28) (owner: "God rooms should be immortal only")
The God Rooms (zone 12) stand up the stairs from the temple, and the atlas gives them one-way
ways out to Port Halyon and the Long Lake shore, so mortals could use them as a shortcut. Now
only immortals may be in them, and the same rule keeps mortals out of the lands sealed until
built, however they try to get there.
- **The mark is the world build's:** `tools/atlas/build_world.py` writes `imm_only` on every room
  of `IMM_ONLY_ZONES` (12), so a rebuild keeps it. The connection pass runs a second time over
  the rooms mortals may walk, so nothing they need lies only through the God Rooms (it adds
  nothing today; it guards rebuilds).
- **One rule, `Room.admits(ch)`:** a room only immortals may enter, or a room of a sealed land,
  takes immortals only; creatures never count as immortal. `Player.recall_room()` is your
  recall point while you may be there, else the temple.
- **Every way in asks it:**
  - walking (a mortal at the stairs: "A divine force prevents you from entering.");
  - following an immortal (the follower stays behind: "A divine force keeps you from
    following ...");
  - the teleport spell (it never lands in the God Rooms or a sealed land; before, 44% of casts
    landed in a sealed land);
  - summoning (refused into a room the summoned may not be in);
  - binding your recall point; `recall`, autorecall and death go to `recall_room()`;
  - logging in (`World.login_room`: a mortal saved in the God Rooms, or in a sealed land after
    a teleport, comes back at their recall room or the temple);
  - a companion's respawn room;
  - fleeing and escaping (only ways walking would allow);
  - pets ordered to move or flee;
  - creatures wandering, hunting, fleeing or tracking (`imm_only` counts as `no_mob`);
  - world bosses and invasions (never in the God Rooms or a sealed land).
- **Left as they are:**
  - An immortal's own pets and companions go where their owner goes.
  - Immortal commands (`goto`, `transfer`, `at`) work as before.
  - The stairs stay on the 3D map and in the exits ("▲ Up · God Rooms"), like the barred
    gates of the sealed lands, and immortals keep the God Rooms' ways out as their shortcuts.
- **What walks as mortals do:**
  - the tutorial directions (`quests.route_dirs`), whose routes all came out the same;
  - the index's steps from the temple: the Sea of Storms is 26 steps away, not 3. The God
    Rooms are listed as "immortals only", after the open zones in the build-out queue;
  - the quest simulator's walk, which now also stops at the bars of the sealed lands;
  - the world check: mortals reach every open room and walk back without the God Rooms;
    immortals reach the God Rooms too.
- **Tests:**
  - `test_atlas_engine.py`: a mortal is turned back at the stairs, an immortal goes up, and a
    mortal following them stays behind. Summoning a mortal up is refused. Teleport never lands
    there or in a sealed land. Logging in or recalling there sends a mortal to the temple, and
    binding there is refused. A wandering creature never steps in. Directions never lead
    through.
  - `test_world_atlas.py` checks the mark and both walks.
  - `test_webmove` (live): the God Rooms' map marks them, and the immortal test hero goes up
    and back.
- **Balance:** the quest simulator (all nine classes alone at 45-60, three runs each) came out
  the same as in Push 27, row for row: no quest's walk went through the God Rooms or a sealed
  land. Nothing was retuned.

### The connector zones built out (Push 29) (owner: "Start building out the connector zones next": every room by hand, new creatures and items, all 15 at once)
The 15 connector zones, the wilderness, roads and seas that join everything else, are written.
- **Every room by hand.** The 2,104 placeholder rooms each have their own description, written
  one at a time from a brief. Another 34 rooms are rewritten: Port Halyon no longer reads as old
  Rome, and road rooms no longer carry a house's interior. That makes 2,138 rooms, plus 215
  extra descriptions for landmarks. Rooms that share a name ("The Plains", "On Mira Retrum")
  each read differently.
- **How the writing was done** (`tools/atlas/briefs.py`, `world/buildout/themes.json`):
  - 16 jobs of 34-157 rooms each; a big zone is split into stretches of walking order.
  - Each brief carries the zone's theme, mood and levels, the style rules, and every room with
    its terrain, its ways out and the rooms they reach.
  - `world/buildout/jobs.json` fixes each job's rooms.
- **The writers' check** (`tools/atlas/buildout.py --check`):
  - 45-100 words and 3-5 sentences;
  - compass words only for real ways out (place names like "the Great Eastern Desert" excepted);
  - no sentence twice;
  - creatures and items complete.
- **Folded into the world by the build** (`buildout.apply`, called by `build_world.py`):
  - The writing lives in `world/buildout/parts/<job>.json`. Rebuilding the world keeps it.
  - Descriptions are wrapped at 72 columns. A rewritten room drops the old extras that came with
    its old text.
- **112 kinds of creature and 84 items:**
  - Each job designed the creatures of its own stretch (4-8 kinds), and they stand only in the
    rooms that job wrote: 415 placed.
  - Their numbers come from their level and kind, fitted to the world's own creatures: health
    20 + 14L + 0.15L² (animals 0.9x, monsters 1.2x, undead 1.1x), a blow 1.5 + 1.45L, armour
    97 - 3L, experience 55L + 20. Humanoids carry 12L gold.
  - Items get modest gear numbers for their level (weapons about 4 + 0.15L a blow; armour a few
    points; at most one small bonus). Each is dropped by one of its writer's creatures at
    10-35%, besides the usual loot.
  - Townsfolk are harmless; only predators, outlaws, undead and monsters attack.
  - Vnums: creatures 600000 + zone·100, items 700000 + zone·100, kept per job in
    `world/buildout/vnums.json`.
- **The index** counts 4,683 rooms still to write, all outside the connectors.
- **Tests:** `tests/test_buildout.py` checks that:
  - every connector room is written, and every part passes the writers' check;
  - creature numbers follow their level;
  - no creature stands where creatures may not be, or on both water and land;
  - every item is dropped.

  The 3D client's creature looks (`node --test tests/web/looks.test.mjs`) give every new creature
  a body.

### Every creature its own body, step 1: the creature kit for wildlife (Push 30) (owner: "start on push 1 then continue with push 2")
A creature's 3D body is now built from parts in code, so every kind of creature looks like itself
and no two kinds look the same.
- **`world3d/kinrecipe.js`** (pure, no three.js) turns a creature into a recipe:
  - a skeleton (`quad` for four-legged beasts, `bird`, `fish` for swimmers);
  - its parts: heads (pointed, blunt, long, snout), ears, horns (antlers, horns, curled, tusks,
    a spike), tails, manes, beaks, crests, wings (feathered or leathery), fins, flukes and
    flippers;
  - its proportions, a coat with belly and accent shades, and markings (saddle, stripes, spots,
    socks, a blaze, wing bars, a cap, a collar, countershading).

  The words of its name decide what they can: "stag" gives antlers, "boar" tusks, "shaggy"
  thick fur, "lean" a thinner body, "black" or "arctic" a coat; a raven is black and a gull white
  without saying so. A seed from its prototype number fills in the rest, so the same creature
  always looks the same.
- **`looks.js`** attaches the recipe to the look for every creature whose bestiary body is one
  of the kit's skeletons. **`kin.js`** builds it (flat-shaded primitives, about the cost of the
  rats and spiders) and animates it through proc.js's `ProcActor`:
  - beasts trot, hop (hares) or sprawl (lizards), lunge, horned ones lowering their heads;
  - birds flap when they move, and penguins waddle;
  - swimmers sweep their tails.

  A body's size is its height, or most of its length when it is long and low.
- **Settings › Creatures:** Unique (the kit) or Classic (the shared models).
- `/play?demo&gallery=kin[&only=wolf,stag]` lays out sample creatures from the world.
- **175 kinds** of wildlife are on kit bodies (133 beasts, 30 birds, 12 swimmers), every one
  distinct (`tests/web/looks.test.mjs` checks the whole world).

### Every creature its own body, step 2: the rest of the bestiary (Push 31)
The creature kit covers nearly every non-person creature: **404 kinds, every one distinct**.
- **Six more skeletons** in `kin.js` and `kinrecipe.js`:
  - **biped:** brutes and trolls (stooped, long arms, warts, a long nose), giants and ogres
    (clubs; one eye for a cyclops, tusks for an ogre), goblins and kobolds (big ears, a snout and
    a tail), and fiends (horns, a demon's tail, leathery wings). Also a minotaur's bull head, an
    ettin's two heads, a balor's whip, and an earth elemental's rock.
  - **crawler:** spiders (eight legs, glowing eyes, fangs), beetles and insects (six legs,
    feelers, wings that buzz or broad moth wings, wasp bands and stings), crabs and lobsters
    (claws), scorpions (claws and a curled stinger), and turtles (a plated shell).
  - **serpent:** snakes, with a cobra's hood, a viper's wedge head and diamonds, a python's bulk
    and blotches, a hydra's several heads, a sea serpent's frill, a couatl's feathers, a worm's
    toothed maw, and a centipede's legs and mandibles.
  - **dragon:** four legs or a wyvern's two, wings, horns, a spiked back and a spade tail. A
    dracolich is bone with glowing eyes; a whelp is young and big-headed; a dragon turtle has a
    shell.
  - **spirit:** a ghost's sheet, a shade's dark hood, a banshee's hair, flame, ice shards, water
    and wind rings for elementals, a wisp, disembodied hands, glowing eyes, and trailing wisps.
  - **blob:** slimes and oozes, frogs (they hop and gape), jellyfish (a bell and tentacles),
    clams (they open and close on a pearl), and a gelatinous cube.

  Species colours apply when no colour word is given: hornets yellow, trolls green, imps red.
- **Left on their models:** props that come alive, trees, mushrooms, skulls, the floating eyes
  and the tentacled horrors (36 in all).
- **Drawing cost:** a body's still parts are merged, and its plain colours baked into one
  vertex-coloured material per moving part. Its glowing and see-through parts are copies of its
  own, so a hit flash lights only that creature. About 10 draw calls a creature, half the
  triangles of the classic models.
- **Tests:** `tests/web/looks.test.mjs` checks the whole world stays distinct and that the
  newer skeletons follow their words (an ogre's two eyes, a cyclops' one, a minotaur's bull
  head, a cobra's hood, a hydra's three heads, a wyvern's two legs, a fire elemental's flame, a
  frog). The browser probe and `/play?demo&gallery=kin` show them in place.

### Loot that drops, gear that procs, sets that count, and `gearup` (Push 32)
Owner: "Make gear procs and set bonuses work too", and "load XTC with gear so I can test end game".
- **Loot.** A creature spawned from its zone now carries what the zone gave it (`inventory`:
  keys, coins, gear, dropped when it dies) and rolls the drops its zone wrote for it
  (`loot_table`). Both lay unread before, so every creature fell back to the generic tier
  table. 820 creatures carry 1,465 items between them, and 177 have their own drop tables
  (among them the build-out's 84 items). A shopkeeper's wares stay its shop. `tests/test_loot.py`.
- **Procs** (`src/procs.py`, one engine):
  - **Sources:** the legendaries' own procs; zone items' spell-named affects (vampiric touch,
    poison cloud, ice blast, turn undead), life drain, undead bane, chaos, and flaming, frost or
    shocking weapons; a proc on four named sets (Necromancer's Regalia drains, Chaos Weave spits
    a random school, Apocalypse Raiment breaks ruin over every foe, Frostlord's Mantle bites
    whoever strikes you).
  - **On hit:** every weapon blow a player lands (the main swing, the extra swings and haste,
    the off-hand, cleave and circle); spells and abilities don't. A weapon's procs fire on its
    own blows. Each has its chance, damage grown from the item's level (a legendary names its
    own), a school that resistances answer, and a one-second cooldown. Chains and splashes find
    only the wearer's foes. Creatures' gear doesn't proc, so their fights keep their tuning.
  - **On defend:** dread (the attacker falters), a reflecting shield, and the frost aura. The
    Cocoon of Arrested Decay turns a killing blow aside once a day.
  - **On equip:** +damage %, all attributes (counted once when the item lists them too),
    stealth, sight in the dark, a fire ward, and travel speed (read by Push 33).
  - **On kill:** health and mana restored.
  - **Seen:** the room reads one line. The 3D client gets a `proc` event and draws a burst in the
    school's colour with the proc's name and a sting. Errors are logged, not swallowed.
  - **Legendaries drop from real bosses:** each of the 20 is mapped to a boss of fitting level
    (`legendary.LEGENDARY_BOSSES`, 3-5% a kill), and the item says who drops it. Any other boss
    of level 40 or more has 1% at a random one.
- **Sets:**
  - A set's armour class is applied as armour (5 per point); `earth_resist` wards nature and
    earth; `curse_resist` is a spell ward.
  - Every tier can be reached: a tier asking for more pieces than one hero can wear at once
    (from the pieces' slots: two rings, two necklaces, two bracers) unlocks at that many
    (`sets.SET_CAPS`, built at load).
  - `sets` names each set and shows every tier: what it gives, whether it's active, and how many
    more to wear. Identify, inspect and the 3D tooltip list an item's procs, its set and the
    tiers. The almanac shows zone sets as well as named ones.
- **`gearup <player>`** (immortal): raises them to the level cap; fills every slot with the best
  item by item level; adds a whole named set, a legendary weapon with an on-hit proc, 50,000 gold
  and the fastest mount, ridden.
- **Balance:** `tools/balance/bosses.py` reads the same before and after (median worst 49%,
  25 deaths in 180). Its heroes wear ordinary gear, and creatures' gear doesn't proc.
  `tests/test_procs.py` covers each kind.

### Rooms look like what they say they are (Push 33)
Owner: "some of the rooms in the game need to be styled like the description. For instance if it
says a cave, the room should look like a cave. Let's think how to fix this going forward."

- **The problem:** the 3D client styled a room by its `sector` alone, and the sectors were wrong
  for whole kinds of place, in the atlas source too:
  - 340 of 342 rooms named as caves were typed `inside`, so they drew as tiled halls (with
    invisible walls where roomgen's cavern rubble lay);
  - every desert room was typed `field`;
  - 52 of 54 sewer rooms were typed `mountain` or `hills`.
- **A look per room** (`src/room_looks.py`), worked out at load. It is apart from the sector,
  which still decides movement, water and darkness. The first rule that answers wins:
  1. a look the zone data states (the build-out writes one) or `world/looks.json` (hand
     overrides by room or zone, each with its reason);
  2. the room's name (an ordered word table);
  3. its description (two mentions, or one telling phrase);
  4. the zone's default in looks.json;
  5. its neighbours, a few steps within the zone. Underground looks spread only through
     enclosed rooms that don't read as a building's (a tavern, a kitchen); outdoor looks only
     through open country;
  6. a plainly underground zone (a third of its enclosed rooms already underground) gives its
     look to the rest.
- **Today:** 1,076 rooms are caves, 303 mines, 299 crypts, 106 sewers and 95 dungeons, with 57
  desert, 265 snow, 81 shore, 67 volcanic and 27 swamp. The rest keep their sector.
  - Below Moria and the Castle Catacombs are set by zone in looks.json.
  - The look rides beside `sector` in the zone map, atlas and room payloads.
- **The 3D client draws each** (`world3d/terrain-looks.js`, `terrain.js`):
  - **caves:** rock for walls (a darkened boulder pile on every wall and rubble cell),
    stalagmites at the rock's foot, a fringe of stalactites, glowing crystals and mushrooms, a few
    torches;
  - **mines:** the same rock, with timber frames, rails on sleepers, lanterns, crates and ore
    glints;
  - **crypts:** coffins, bones, skull-candles and cobwebs;
  - **sewers:** a channel of foul water with rims and pipes;
  - **dungeons:** broken walls and rubble;
  - **outdoors:** desert (sand, cacti, bleached bones), snow (white ground, frosted pines, ice),
    shore (a waterline and driftwood), volcanic (ash, jagged lava cracks, scorched trees) and
    swamp pools.
  - **spider lairs (`web`):** dead trees hung with web sheets and strands, cocoons, egg sacs and
    bones, in a grey-green gloom (`terrain-looks.js webDress`). The owner's example was Arachnos's
    Webbed Entrance [6301], drawn as plains with a town.
  - **castles (`castle`, `terrain-castle.js`):** for a castle's yard, walls and gates by name.
    Streets toward a keep, halls and caverns are left out, and a courtyard counts only when a
    castle is named. The client draws:
    - a 3.8 m curtain wall with merlons and buttresses; the side nearest the camera is a parapet;
    - a tower at each closed corner;
    - banners and torches on the walls the camera faces;
    - a gatehouse with a raised portcullis over every way out;
    - a yard of a well, crates, weapon racks and targets;
    - the stone tinted black, white, red or bone from the room's words.
  - **dead cities (`necropolis`):** a town's streets in black stone, with crypts, shrines, dead
    trees, graves, bones and skulls in place of street furniture, braziers of cold green
    ghost-fire, and a grave-green mood (`terrain-town.js`, `engine.js`). Morkai's streets use it.
  - **webs in a room or a cave:** a room whose words name webs twice (the spider queens' dens, a
    cellar thick with cobweb) keeps its own look, with the web dressing hung in it and no
    canopy.
  - **ways into another region (any room):** a stone gateway over every cardinal exit of kind
    `zone`. It has two great pillars, a lintel carrying the region's name on a carved plaque,
    banners, and a fire either side. Indoors and underground it is lower and plainer. On the
    side nearest the camera it stays low, with the name turned to the camera. Stairs up or down
    into another region get a free-standing arch over them (`standingGate`).
    - The owner: "castle and main zone entrances should look interesting too. Everything is too
      generic."
  - **Moods** (`engine.js`): cave, desert, snow and volcanic, plus footsteps, ambience, music and
    minimap colours by look.
  - `/play?demo&gallery=rooms` shows one room of each look, plus castles and gateways
    (`&only=castle,blackcastle,gate,gatecity,gatecave,gatesouth`).
  - `tools/qc_room_looks.py [--zone N]` lists rooms whose look conflicts with strong words in
    their description (webs, trees, caves, streets). It reports 0.
    - Rooms judged right as drawn are in its `ACCEPT` list, with why. Rooms pinned in
      looks.json (which may now pin a plain field, forest, hills, mountain, city or inside) are
      skipped.
  - **Rules from its findings (`room_looks.py`):**
    - an indoor room named as open country but described as a building (≥3 indoor words)
      stays a building; a road needs a roof, a vault or a building it runs through. Examples:
      Townsbridge's alehouse, chapel and barns, all called "The Plains"; the customs hall the
      Trade Road runs through.
    - a road through a tunnel is a cave;
    - a field room named for a building and described as one is a room (a guardhouse, the
      guards' quarters), unless its name puts it outside;
    - a tunnel is a cave even without rock words;
    - a room typed as open country but described all in tunnels is a cave (the Mountain
      Range's Maze and Hole);
    - a city-typed room named a cave is one (the Golden Cave);
    - "Forrest" is a forest;
    - a wood hung with webs is a spider lair;
    - a furnished room (≥2 of hearth, table, bed, shelves, rafters, windows...) never takes its
      zone's underground look. Castle bedrooms had been drawn as caves.
- **Keeping it true:**
  - `tests/test_room_looks.py` (the world check): every room looks like what its name says
    unless pinned, stated looks never contradict names, overrides are valid, plus known rooms
    and the counts.
  - `tests/web/roomlooks.test.mjs`: every look lays out rooms you can walk through, and has its
    theme, mood and sounds.
  - The build-out's briefs ask writers for `{"description": ..., "look": "cave"}`, and
    `buildout.py` validates and merges it.
  - The browser probe's `looks` mode walks into a cave, a sewer, a desert and a crawlway.
- **To change a room's look:** add it to `world/looks.json` (`rooms` or `zones`, with a `_why`).

### Faster travel on mounts, and the hero drawn riding (Push 34)
Owner: "let's find a way to increase character speed? Maybe that's mounts since that's built in."
- **Travel speed** (`mounts.travel_speed`): the mount you ride, scaled by its loyalty (half at 0),
  plus haste (+15%), gear that quickens travel (the Threshold Walkers) and the Pursuit of Justice
  talent, capped at +80%.
  - Mounts: donkey +15%, pony +20%, horse +35%, warhorse +30%, nightmare +50%, griffin +60%,
    clockwork steed +50%, and the faction mounts.
  - The map payload sends `speed`, for you and for players near you (with the mount they ride).
- **In 3D:**
  - The hero's run is multiplied by the speed (`controller.js speedMul`).
  - A mounted hero sits on a steed built from the creature kit (`steed.js`, table in
    `steedlogic.js`): a horse's build and coat, the nightmare black with burning hooves, a
    griffin a winged lion, the clockwork steed brass, a stag, boar, camel, panther, warg and the
    rest. It has a saddle and blanket (barding for war mounts), a seated rider and clopping hooves.
  - Other players are drawn on theirs. `/play?demo&gallery=steeds` shows them.
  - Mounting or dismounting pushes a fresh payload, so the change shows at once.
- **Telnet:**
  - A mount's saving on what moving costs is kept to the fraction, so a horse halves the cost even
    on 1-cost ground (the old `max(1, …)` floor ate it).
  - `ride n n 3e` (or `ride nnee`) speedwalks up to ten rooms, reining in at closed doors, water you
    can't cross, a fight or a hostile creature.
- **Mount fixes:**
  - Loyalty decays while ridden (a point every other minute), with a warning when hungry; feeding
    restores it.
  - All 14 faction mounts that factions.py names but the templates lacked now exist.
  - The griffin is won from the Roc Matriarch, and the clockwork steed from the Carillon Engine.
  - The stable shows real speeds. Help covers mount and ride.
- **Tests:**
  - `tests/test_mounts.py`: speeds, cap, payload, faction mounts, move cost, loyalty, ride and
    boss drops.
  - `tests/web/steeds.test.mjs`: every server mount has a buildable steed, and the speed and seat
    wiring.
  - The browser probe's `mount` mode buys a horse, mounts it (a steed under the hero, 1.35× the
    run) and dismounts.

### Mounts that look the part
Owner: "The mounts look pretty basic and silly. Can we make these look amazing somehow?"
- **Real bodies:** a mount is now the animated creature body (`bodies/*.glb`) with its own walk and
  run, not a kit model. `steedlogic.js MOUNT_LOOK` gives each mount:
  - its body: a horse, the unicorn for the celestial charger, a lion with wings for the griffins,
    a dragon for the mana wyrm and drake, the spider, wolf, camel and treant;
  - its coat and size;
  - its tack, cloth and trim colours;
  - its marks.
  The kit steed shows until the body loads (`steed.js realSteed`).
- **Tack fitted to the body** (`tack.js`): rays feel the back, flanks and belly, and every piece is
  shaped to them and hung on the spine, chest or head bone, so it moves as the body moves.
  - A blanket under a dished saddle with a pommel, horn and cantle; skirts with gilt studs; a girth;
    stirrups.
  - A breastcollar round the chest with a medallion and gem, and a bridle with a browband, bit rings
    and reins to the rider's hands.
  - War mounts wear a caparison to the knees. It is a painted cloth with a diamond lattice, a trim
    border, a crest on each flank and a scalloped hem, and the mount has a plume.
  - Plate adds a chanfron, crinet and peytral. Pack mounts carry bags and a bedroll.
  - Metal is half-metallic with a little glow of its own, since there is no environment to reflect.
- **Marks:**
  - feathered wings that flap as it runs;
  - glowing eyes on the nightmare, warg, spider and drake;
  - particles: hellfire, celestial sparks, steam, arcane motes, moonlight, shadow, embers and
    leaves, and dust at a run.
- **The rider** sits just behind the withers and rises and falls with the back.
- **Bulkier, bigger horses** (owner: "make the horses bulkier and bigger"):
  - `steed.js inflate` thickens the horse and unicorn along their bones, using `steedlogic.js
    BULK`. Each vertex is pushed out from the nearest point on the bones it is skinned to, shared by
    its skin weights, so the bulk bends with the walk and run.
  - The legs are about 1.5 to 1.75 times as thick, the barrel and neck about 1.35 times.
  - The bodies' positions are packed 16-bit integers. They are unpacked to floats first, or a
    vertex pushed past the end wraps round (the muzzle tip ended up behind the tail as a black rod).
  - Horses are 15–25% bigger beside their riders: horse 1.15, warhorses, nightmare and celestial
    charger 1.25, clockwork steed 1.2.
- **Tests:** `tests/web/steeds.test.mjs` checks that every server mount has a look whose body is in
  `bodies/index.json`, with known tack and marks, and that `steed.js` builds the body, the tack and
  the fallback.

### Forests, mountains, water, and rooms that join up (Push 33, follow-ups)
- **Reading:** a room named as open country is drawn as that country whatever it was typed:
  - plains, forest, mountain (from strong words for rooms typed indoors);
  - a path through woods is forest, and a mountain road is mountain;
  - a cave's ledge stays a cave;
  - a named forest or mountain isn't swapped by its description, unless the description says
    snow.
- **Mountains** draw as cliffs (tall weathered rock on the border and rubble), scree, boulders and
  a few hardy pines, with no grass or flowers.
- **Forests** have trunks standing through the room, not only round its edge.
- **Water rooms** (605 of them) are water from bank to bank. They were meadows, or a meadow with a
  blocking pond.
  - You cross open water (the server already asks for a boat or raft), and the hero rides a raft.
  - Banks keep a few trees and rocks, and water rooms open onto each other.
- **Seamless country:**
  - **Open joins:** two outdoor rooms side by side that open onto each other share their whole
    side (no ring or treeline between them), water joined to water and land to land.
  - **Filler:** where the zone map has no room, the room draws its country half-way into the
    empty cell: a ground skirt in its own palette, with that country's trees, cliffs, dunes or
    water.
  - **Haze:** outdoors, the far background is the haze colour, not a dark void.
  - **Cost:** filler trees thin out with distance. A 13-room view in the demo is about 90 draw
    calls and 0.65M triangles.
- **XTC:** a one-time gift (`world/grants.json`) gives a griffin and a horse, charts the whole map
  (but the God Rooms and sealed lands) and every travel waypoint. `givemount` lets an immortal
  give anyone a mount.

### Push 35 — play-testing fixes, more bars, the world's murmurs (owner, 2026-10-12)
- **Riding:** R (or the menu's horseshoe, the riding chip, or right-clicking yourself) gets you up
  or down. `mount last` remounts the mount last ridden. Gifts (`world/grants.json`) are given part
  by part, and an `immortal` gift makes the account an admin one (Deckard); a /play character
  without an account gets one of its own.
- **Deaths always finish:** if the rewards fail part-way, the creature still leaves a corpse and
  the room. Proc kills go through `handle_death`.
- **Shops:** the misaligned CircleMUD import is undone (`shops.repair_config`). A raft costs 480,
  merchants never refuse a sale for want of coin, and `sell 2.sword` works.
- **Death traps** are drawn as a ledge round a burning abyss (`deathtrap.js`). The hero stops at
  the edge (press E to go on), and the minimap shows them red.
- **Character creation:** choices glow on hover rather than lifting, so the menu no longer jumps.
- **More bars:** three extra bars of 8 (Alt+1–8, Alt+Shift+1–8, click), which float and can be
  dragged, turned and locked. Layout is kept per character on the device (`barlayout.js`,
  `hud/bars.js`); `webbar` holds 40 slots.
- **Ambient murmurs fit the place:**
  - `ambient_place.py` reads a room's tags: castle, smithy, market, tavern, street, building, its
    look, and the sky.
  - `ambient_lines.py` gives each line the tags it needs, so there are no merchants or smiths in
    a castle.
  - Creatures really next door are heard from where they are.
  - /play gets a sound from that direction and a cue (an edge arrow and a minimap ping) instead of
    a chat line; captions are optional. Telnet keeps the text.
  - One system now (`ambient_events.py` is gone). Use `ambient` / `ambient now` (immortal) to
    inspect a room.

### Dead Morkai: an end-game city of the dead
Owner: "Morkai should be an end game area and themed dark, undead, skeletons, aberrations."
- **Scope:** the city (35 rooms in the Orc Tunnels, 13828 and 13831–13899) and its under-tombs
  (zone 514, 33 rooms) are now levels 60–68. The approach tunnels stay 42–52, and the Gate To
  Morkai warns that few come back.
- **The story:** the orc city fell to what woke under the Well of Souls (Moloch, beneath the tombs).
  Its orcs rose as the dead, and aberrations crawl up through the Gateway To The Underworld. Every
  room is rewritten (`world/buildout/parts/z512b.json`, `z514.json`).
- **The creatures**, each named so its 3D body fits (`looks.js`, `bestiary.js`):
  - skeletal orc warriors and archers, rotting orc ghouls, orc bone-shamans, soul wraiths, death
    knights (elite);
  - eye tyrants and mind flayers (elite), tentacled horrors;
  - in the tombs, carrion crawlers, gibbering mouthers, risen cultists and a bone colossus;
  - Vrakk the Hollow-Eyed (sub-boss) atop the Black Spire;
  - **Gorbash the Bone King** (boss) on the high seat, with gloom, waves of his dead and
    grave-chill pools;
  - Imrael the Lich and Moloch (68) below.
- **Drops** (60–68): a bone-hafted cleaver, a grave shroud, a death knight's greathelm, a
  soul-glass amulet, a void-iron ring, Vrakk's blackplate and the crown of the Bone King.
- **The look:** streets and squares are `necropolis`; halls, the church and the morgue are
  `crypt`; zone 514's zone key is `necropolis`, which sets dark music.
- **Counts:** a reset counts its creature across the whole zone (`world.reset_zone`).
  - The build-out used to give every placement `max: 1`, so each build-out creature lived only
    once per zone, whatever count its writer gave.
  - Each placement now carries the creature's count, which lifts the cap in every build-out zone:
    about 834 more creatures in the world at load (2,387 to 3,221).
- `buildout.py`: a creature's `"avoid": [room names]` keeps it out of rooms; the tunnel orcs avoid
  dead Morkai.

### A second opinion from JEV (TypeSafe's decision model)
Owner: "I have a JEV account, can we leverage JEV for anything in misthollow?"
- `tools/jev_audit.py rooms|creatures` asks JEV which look each room's own words describe, and
  which body each creature's words describe. It chooses from the game's own options and says how
  sure it is.
- It lists only the cases where JEV is at least 90% sure of another option and gives the drawn
  one 5% or less: `docs/JEV_REVIEW_ROOMS.md` and `docs/JEV_REVIEW_CREATURES.md`. It changes nothing
  in the game; each entry is for a person to judge.
- **The key:** a network secret for `api.typesafe.ai`, or `TYPESAFE_API_KEY`. Answers are cached in
  `tools/audit/out/` (not committed), so a re-run asks only new questions.
- **First run:** 1,620 creatures (2.5M tokens, about $0.10) gave 68 to review. 8,571 rooms (8.7M
  tokens, about $0.37) gave 882. Each answer took about a quarter of a second.
- `tools/qc_bestiary.mjs --json` lists every mob with what it is drawn as, for the creature run.
- **Fixes from the review** (owner: "fix the clear creature and room mistakes"):
  - **Creatures (68 flagged, 20 left, all judgement calls):**
    - The Skull Clan are orcs, not floating skulls. A reaver is a raider, not a spider (but a
      spine reaver still skitters). The mutant orc is an orc.
    - "Bone" alone no longer makes an ogre, troll or orc undead (`looks.js deadWords`). The bone
      colossus, made of skeletons, stays dead.
    - Ghouls and the shambling dead wear the zombie body.
    - Bodies that existed but went unused are now used: the Rat King, rocs, little dragons
      (dragonets, drakelings, baby dragons), and big cats for tigers.
    - A lizard's hatchling is a lizard; a sea snake is a snake, not a sea serpent; a gorgon has
      the medusa's shape; a sworn blade is a warrior.
    - Nine one-offs, mostly ghosts known only by their keywords or behaviour, are set by prototype
      (`looks.js BY_PROTO`).
    - Tests: `tests/web/looks.test.mjs`.
  - **Rooms (882 flagged, 691 left):** 192 clear errors are pinned in `world/looks.json`, each
    with its reason:
    - shops, houses and halls drawn as streets;
    - streets, alleys and plazas drawn indoors;
    - gardens and hedge mazes drawn indoors;
    - meadows, cornfields and plains drawn as forest, snowfield or standing stones;
    - mountain paths drawn as snowfield; the necropolis's open streets drawn as crypts;
    - docks, piers and open-sea boat rooms drawn indoors.
  - **Left for a person:** what remains is mostly near-synonyms (a castle hall or a plain room, a
    dug tunnel or a cave), plus the city wall-walks, the glacier cracks, the tree city's rooms,
    and paths just outside gates and cave mouths.

### The archmage: a mage's second look, made in Blender
Owner: "build the mage look in Blender for free and let me see an example"; then "blue and gold
is fine. The eyebrows and hair should match the beard color."
- **The pieces** (`tools/art3d/blender/models/archmage.py`): a tall, crooked, wide-brimmed hat
  with a gold band, an arcane gem and a star charm; a beard grown from the mage's own jaw and
  cheeks, with a moustache; a robe to the ankles; a mantle, bell cuffs and a crimson sash; a staff
  with a gold crescent moon cradling a glowing orb.
  - Each piece is modelled in the rest pose of the KayKit rig that every hero shares, and bound to
    a bone: the hat and beard to the head, the robe weighted between the hips and the legs. So
    every hero clip moves them. About 1,800 triangles.
  - Its colours are columns of the equipment kit's palette (a new `archmage_blue` ramp in
    `ramps.json`, plus gold, crimson, `fur_white` and `arcane~glow`), so the preview and the game
    match.
  - `run.sh models/archmage.py --preview --export` renders a turntable and a close-up of the face,
    and writes `blender/out/equip/archmage.glb` with a sidecar naming each colour's column.
- **Into the kit** (`build.mjs equip`): pieces in `blender/out/equip` join `equip.glb`. Joints are
  found by name, and every UV is moved to its named palette column. The pieces get a new type,
  `worn`.
- **The look** (`gearlook.js`): a mage whose look has `style: 'archmage'` wears the pieces.
  - Hair and eyebrows turn `fur_white` to match the beard.
  - The archmage hat stands in for any hat; a helm or crown replaces it.
  - The moon staff is drawn whenever a staff is held.
  - The renown shoulder pieces are left off, since the archmage has its own mantle.
  - The classic mage and every other class are unchanged.
- **Choosing it:**
  - **At creation:** after choosing mage, a mage is asked "classic or archmage" (`server.py`). The
    3D wizard shows both on the hero (`login.js`).
  - **Later:** `appearance [classic|archmage]` changes it at any time.
  - **Stored:** it is kept as `Player.look_style` and sent as the look's `style` (`gear_look.py`),
    for a mage only (`player.py LOOK_STYLES`).
- **Gallery:** `/play?demo&gallery=gear&only=tiers&cls=mage&style=archmage` shows the archmage at
  every gear tier.
- **Tests:** `tests/test_archmage_look.py` (creation, save and load, mage only, `appearance`) and
  `tests/web/gearlook.test.mjs` (the plan).

### The drow city, as D&D draws one
Owner: "The drow city doesn't look like a drow city. research DnD and then create the appropriate
art for the zone."
- **What D&D says** (Menzoberranzan, the archetypal drow city, Forgotten Realms sources):
  - It fills a vast dark cavern.
  - Its homes are carved into great stalagmites and stalactites, the biggest formations being the
    noble houses' castles, joined by bridges of hardened spider silk.
  - Every house is outlined in permanent faerie fire (violet, blue and green), with spiders carved
    everywhere for Lolth.
  - Narbondel, a great pillar the Archmage heats each day, tells the time; Arach-Tinilith, the
    temple of Lolth, is shaped as a spider.
- **The look:** every room of the Drow City (zone 51) has the new `drow` look
  (`world/looks.json` `underground_zones`, and absolute there, so even its tunnels and bridges
  have it). The JEV pins that drew its streets as a surface town are gone.
- **The drawing** (`world3d/terrain-drow.js`, called from `terrain.js buildRoom`):
  - Each room's kind is read from its name: street, Narbondel ("The Center Of The Drow City"),
    temple ("Entrance To The Temple Of Lloth"), bridge (the Thin Underground Bridges, the Ornate
    Walkway), fungus forest, tunnel or hall (the noble houses, academies, barracks).
  - **Streets:** dark obsidian flagstones. Where no room is next door, rows of spire houses stand
    beyond the edge, each ringed and ribbed in faerie fire, with lit window slits, a glowing door
    arch and a spider sigil over it. Houses carved in stalactites hang further back, with silk
    bridges strung between the spires. In the street: giant glowing mushrooms, spider statues,
    faerie crystals and faerie-fire braziers.
  - **Narbondel:** a dark pillar in the plaza's north-east, red-hot at its foot, with hour-rings up
    its height and a web of faerie fire inlaid in the floor.
  - **The temple:** a great spider crouching over the plaza on eight legs, its body high enough to
    walk under, its eyes red.
  - **Bridges:** only the way across is floor, with silk rails and glowing strands along its
    edges; the rest is the abyss, with the city's spires far below.
  - **The fungus forest:** thick with glowing mushrooms.
  - **Tunnels:** the cave rock, with fungus and crystals.
  - **Halls:** dark stone walls with faerie fire along their tops and feet, spiders carved on them,
    and a web in the floor of throne rooms and temples. Every hall gets spider statues,
    faerie-ringed obsidian pillars and crystals. A temple keeps its altar, benches and candles; a
    throne room gets a matron's throne of black stone, crowned with eight spider legs. Neither
    gets a human hall's lamps, banners, rugs or knightly pillars (`furnish` skips them for drow),
    and a pillar named in a room's text is drawn the drow way. No warm torches: each room gets two
    faerie-fire lights instead.
  - **Gateways** into another region are black stone with plain columns, with no banners or
    torches.
  - **People:** a priestess who keeps a door (the Temple Warden of Lloth) is robed, not a knight
    (`looks.js`: priests are read before guards).
  - Everything is procedural geometry merged by material, with the see-through cut, so a spire or
    the pillar never hides the hero.
- **Mood:** a black cavern with violet gloom (`engine.js` `drow`); no sky or weather; the dark
  music and the drow ambient bed; the minimap colour.
- **Gallery:** `/play?demo&gallery=rooms&only=drow,drowcenter,drowtemple,drowbridge,drowfungus,drowhouse`.
- **Tests:** `tests/test_room_looks.py` (every Drow City room is drow) and
  `tests/web/roomlooks.test.mjs` (`drow` is a walkable look with its sounds and moods).


### The art audit: every zone drawn to its theme
Owner: "audit the rooms and use JEV as you see fit to ensure all the game art is correct and to theme
of each zone." The drow city had shown the gap: every room of it read right by its own words (a
cave, a hall), and the city of the dark elves was still drawn as plain tunnels. So the audit judges
zones as a whole as well as rooms, and looks at the rooms as they are drawn.
- **Three passes with JEV** (`tools/jev_audit.py`; answers cached in `tools/audit/out/`, reports in
  `docs/JEV_REVIEW_*.md`):
  - `zones`: for each zone, its setting (a castle, a wizard's tower, a hell, a dwarven hold...) and
    whether the looks its rooms are drawn with show it (right, partly, generic, wrong).
  - `rooms`: each room's look against its own words (the earlier pass, run again).
  - `shots DIR`: screenshots of rooms in /play, sent as image assets (the
    `TypeSafe-Danger-Zone-Images` header; a data: URI in the state is read as text and never
    seen), judged against the room's words and its zone's setting: good, the wrong kind of place,
    the wrong style, bare, unreadable.
- **What it found, and the fixes:**
  - **Every indoor room was a homely house** (plank floors, beds, standing lamps, pictures),
    whether in Welmar's Castle, the High Tower of Magic, the White Gold Cathedral, the halls of the
    gods or Orcus's temple. A zone now states the style of its interiors (`world/looks.json`
    `interiors`, sent as the rooms' `tone.interior` by `zone_tone.py`), and
    `world3d/terrain-interiors.js` draws it: **castle** (flagstones, banners, weapon racks, long
    tables, standing torches, a throne with a high gilded back), **arcane** (slate-blue stone,
    bookshelves, a glowing rune circle, floating crystals), **holy** (white marble, white pillars
    banded in gold, an altar, candles, shafts of light), **infernal** (cracked red stone with lava
    in the cracks, braziers, skulls, a burning pentagram), **haunted** (rotten boards, cobwebs,
    furniture knocked over, lanterns, ghost light), **dwarven** (granite, gold-banded pillars, a
    forge and anvil, kegs, axes and shields), **elven** (pale living wood, trees growing through the
    hall, flowers, lanterns). A room's use still gets its furniture (a bedroom its beds, a library
    its shelves). 33 zones have a style.
  - **The Clockwork Foundry was a cave** (its tunnels' words): it has its own look, `foundry`, with
    steel plate, pipes along the walls, great gears in them, machines, conveyors, furnaces where a
    room's name says so, sparks in the Tesla corridor, steam, and a foundry mood.
  - **Castles' halls were made caves** by the caves under them (the zone-wide "plainly underground"
    rule): a zone with an interior style keeps its halls (Ostragoth, Caboon, Mahn-Tor).
  - **Caverns of ice were plain caves** (the Winterlands' halls of ice pillars and icicles): a cave
    whose words name ice twice or more is an ice cave, lava twice or more a lava cave.
  - **Ghenna, a hell, was a grey town**, and Orcus's temple likewise: a zone's tone can be stated
    (`world/looks.json` `tones`): red stone under firelight.
  - **228 rooms** JEV was sure of and that read so are pinned (`world/looks.json` `rooms`, each
    with its reason): cells, cellars and prisons as dungeons, spider lairs as webs, mine tunnels as
    mines, ice caves, gardens, ruins, camps, the Submerged Temple's marble halls as halls, and the
    Garathorm city wall as ramparts.
  - The Pit of Minos is a dungeon and the Mindflayer's Lair a cave, not a house's rooms.
  - **Under the sea read as a dry field** (sand, boulders, pines tinted green for kelp; JEV: "the
    wrong kind of place" in all three sunken zones): kelp is built (`terrain-looks.js` `kelp`),
    bubbles rise, shafts of light fall from the surface, the seabed is blue-green and the fog is
    deep and close. Underwater In The Sewer is drawn under the water.
  - **A snowfield at dawn or dusk was sand** (the warm dusk sun on white): snow keeps its cold
    light but at night.
  - **A wizard's office was a feast** (a table named in its words drew the kit's banquet table):
    in an arcane, holy, haunted, elven or infernal hall it is a plain table; a styled library, shop,
    bank or tavern keeps its shelves and counters; a castle's bedroom its banners and torches; a
    haunted house has dust sheets over the furniture, holes in the boards and ghostly wisps.
  - The Winterlands' Massive Hallways (giants' halls of black stone), the bottom of a well and a
    black stone corridor are built halls, not a cave, a forest or a house.
- **Round three: every flag closed.** All three reviews end with nothing left to fix; every
  exception is in `tools/audit/accepted.json` with its reason, and the reports list them apart
  ("accepted as they are"; for the shots also "the look confirmed": JEV judged the picture wrong but
  its own pick of a look is the one drawn, so what it wants is detail, not another look).
  - **Coverage:** 611 rooms shot live: two of every zone, and one of every look used in every zone
    (each zone-look pair). The words of all 8,440 rooms were judged; the zones were judged again
    after the fixes (the zone check now asks again whenever a zone's looks change).
  - **More rooms pinned** (about 290 in this round, each with its reason): roads through farmland
    drawn as streets, riverbanks, burial mounds, ice and lava caves, spider dens, offices and lodges
    drawn as dungeons, the Crown of Bone's halls as crypts, the Olympian thrones as halls...
  - **Snowy woods and snowy slopes:** a snowfield whose words name a wood has trees standing in it,
    and one whose words name a mountainside has snow-capped cliffs round it.
  - **The building words** cover offices, foyers, council rooms, closets, warehouses, lodges and
    common rooms, so a town hall is never made a dungeon by the zone rule; and a styled zone's halls
    don't take the dungeon look from a pinned cell next door.
  - Room-review totals: 663 disagreements, then 447, 239, and none open. Shots: of 611, 164
    judged good, 247 bare (the right place, plainly furnished), and every wrong one fixed,
    confirmed or accepted.
- **The screenshots** (`tools/jev_audit.py shots`): two rooms of every zone, live in /play.
  Note for the probe: a mood blends in over a few seconds of game time, and a software-rendered
  browser runs a frame a second, so a shot must snap the mood (`engine.setMood({}, true)`) or it
  shows the last room's light (the sunken zones first read as daylight that way).
  - Left as they are, by judgement: the Great Eastern Desert (named a desert, it is a river and a
    mountain's caves, and drawn as such), the Winterwood's snowy paths (snow, JEV would have them
    forest), mountain snowfields.
- **Gallery:** `/play?demo&gallery=rooms&only=icastle,ithrone,ibedroom,iarcane,iholy,iinfernal,ihaunted,idwarven,ielven,foundry,foundry2`.
- **Tests:** `tests/test_room_looks.py` (the Foundry is foundry throughout, every styled zone's rooms
  carry its style, Ostragoth's halls are halls, the Winterlands' cavern an ice cave, the city wall
  a rampart, Ghenna red stone), `tests/web/roomlooks.test.mjs` (`foundry` is a walkable look with
  its sounds and mood).

### The menus and dialogue in /play's dress (owner, 2026-10-20)
Owner: "work on all the text menus ... fix every menu in the game to ensure the UI and dialogue is
clean and matches the rest of the game." Talking to Sage Aldric showed the gap: the window printed
the server's telnet frames (`╔══╗ ║ TUTORIAL COMPLETE ║`, `+===+ | *NPC* Notable figure |`) and its
telnet hints (`(type "talk aldric")`) as they came. Some 300 places in the server draw their own
boxes; telnet keeps them, and /play now draws them in its own dress instead:
- **`hud/frames.js`** reads framed text: a little box round a title or two (a tutorial step done, a
  discovery, a level gained) is a banner; a bigger box (score, weather, the journal, skills) is a
  panel whose rows stay in step, its frame the panel's edge, its inner rules hairlines, its column
  bars faint; a rule alone is the diamond rule; a title on a rule, or between two, a heading;
  a progress bar (`[█████░░░░░]`, or a bare run of blocks) a meter of the same width. The chat log
  gathers a box as its lines stream in; the talk window and help use the same.
- **The talk window** sets what happened to you apart from what they say: rewards, quest steps
  and journal notes as notes, the tutorial's box a banner; a quest's progress line and a tip that
  comes while they speak are left out; "They have nothing to say" when they don't.
- **The server speaks /play's words to /play** (`quest_guide.web_line`, in `Connection.send` for a
  web connection): `(type "talk aldric")` becomes ": right-click them, then Talk", "Type 'journal'
  to ..." becomes "Open your Journal (L) to ...", a shopkeeper's "Type LIST" the Shop; `/quests`
  (the journal and offers) likewise. A discovery is one line there ("New in your journal: ...").
- **Typed `help` and `map`** open the Help (at the topic) and Map windows, not a paged index or a
  map in letters. The server no longer echoes a web page's commands (each showed twice).
- **Every menu, swept.** Of the server's 533 commands, the ones that show something (not the class
  abilities, the emotes, an immortal's tools, or what acts: quit, rent, drop, a toggle...) were run
  on a web connection where each shows (a shop's list at a shop, mail at the post office, the
  auction house, the stable, the arena, the housing district, a trainer), 104 of them, drawn as
  /play draws them and read; and every window of the HUD opened and looked at.
  - A list the server lines up with spaces (the stable's mounts, the housing plots, settings,
    levels, arena rewards, the command list) is drawn fixed-width, so it lines up again; a row
    set one space apart amid it is one of its rows.
  - A line that begins with a prompt ("20/20hp ...> the pilgrim leaves north") loses the prompt
    and keeps the rest (the talk window dropped such a line whole); the help index is not paged
    on a web page ("Press ENTER to continue" there was a dead end).
  - A menu's bars were taken for the fight's health bar (msgkind.py) and hidden from the log's
    All tab with the fight, reputation's whole list among them: the health bar is ten cells,
    and a row of a box is the menu's.
  - The windows' descriptions (a shop's, the stable's, a quest offered, the Legend's) were set in
    small capitals and read as shouting: the body face. The Talents window said "type doctrine":
    the Legend's Doctrine page (G). A shop called a bottle "drinkcon": a drink. A mount for sale
    said its speed twice.
- **Fixed on the way:** `achievements` failed outright (it read its definitions as dicts); the
  updates list read its file in the system's code page (dashes came out as "â€”" on Windows);
  `inspect`, `minimap`, `protect` and `drink_alt` failed outright (two `@classmethod`s), and so did
  the rent an item adds (`@classmethod` on a `@staticmethod`); `social` alone failed (the emotes'
  helper answered to it: it lists the emotes now); `arena top` failed (the online players are a
  dict).
- **Then read in /play itself, and every command.** The 104 menus typed into /play's own chat box
  and read from its log; then all 520 of the server's commands but the 13 that stop the server,
  write the world's files or end the session (shutdown, zsave, zreset, redit, oedit, medit,
  backup, restore, purge, slay, quit, rent, dc): emotes, abilities with no one to use them on,
  the immortals' tools, the toggles. Checked for a frame's characters left outside /play's
  frames, a terminal code, a broken character, paging, a typing hint, a prompt, a failure.
  - The web bridge sent what it read in pieces, cut mid colour code, mid box character or mid
    line: it keeps each whole now. A terminal's other codes (`clear`'s clear-screen) go; typed
    `clear` empties the log. A hint right after a colour code was never rewritten (the code's m
    hid the word's edge). `move` alone failed (it took the words typed for a direction).
  - Lists in columns line up (emotes, commands, settings, the housing plots' heading, arena and
    auction help); `minimap` opens the Map.
- **Every frame the server draws** (`tools/audit/frame_lines.py`: 526 lines in 27 files, from the
  source, fields filled with a sample) is checked against `frames.js`: none is left a line of text
  with the frame's characters in it. Two styles it lacked: a box's empty row (a lone ║, the talent
  trees') and a heading with words after it ("═══ DUEL OVER ═══ Ann defeats Bo!").
- **Tests:** `tests/web/frames.test.mjs` (frames, banners, panels, meters, the talk window),
  `tests/test_web_menus.py` (web_line, the web send path, the discovery line, `achievements`,
  the bridge, `move`, and every frame in the source).
