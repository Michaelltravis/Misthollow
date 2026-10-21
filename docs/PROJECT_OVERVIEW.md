# Misthollow: what we have built

A guide to the game as it stands (October 2026). It covers what exists, where it lives in the code,
how to run and test it, and how the owner shapes the world without code.

- **Detailed history:** `docs/REBUILD_PLAN.md` holds the push-by-push log of the 3D rebuild. The
  older `CHANGELOG_*.md` files and topic docs (`COMBAT.md`, `CLASSES.md`, `COMMANDS.md`, `HELP.md`)
  cover the original MUD.
- **This page** is the overview and the map.

---

## 1. What Misthollow is

**The server:** Misthollow is a Python 3 MUD (a CircleMUD descendant, rebuilt). One asyncio server
(`src/main.py`) runs:

| Port | What |
|---|---|
| 4000 | telnet: the classic text game, still fully playable |
| 4001 | the web server: the **3D client at `/play`**, its map/event socket, `/zonemap`, `/abilitybook`, art and sound |
| 4002 | the admin dashboard (local only, Bearer-token auth) |
| 4003 | the web↔telnet bridge the browser's text commands ride on |

**The client:** the 3D client (`/play`) is the game's face. It is three.js 0.185 (vendored), CC0
art (KayKit/Kenney kits plus a procedural creature kit), its own HUD, and CC0 sound and music. It
plays the same world, rules and characters as telnet. The browser sends the MUD's own commands,
and the server answers with structured payloads and events.

**Where it runs:** the owner's Mac mini, `frostpine`.
- It pulls the deploy branch from GitHub every minute (`deploy/autopull.sh`; the branch is set by
  `DEPLOY_BRANCH`, default `main`: what is merged is what is live). It was
  `claude/nice-johnson-slpinu` until 2026-10-20, when any push to that working branch went live.
- It restarts the server only when code changed.
- No inbound access is needed.

---

## 2. How we got here (timeline)

| When | Phase | What came of it |
|---|---|---|
| Feb 2026 | The MUD | Classes, combat, spells, quests, accounts, OLC, crafting, factions, mounts, pets, a 2D isometric web map. |
| Jun 2026 | 2D "platformer" client | Side-view rooms, parallax, combat juice, talents UI, almanac, services, shops stocked, the creation wizard, procedural room dressing. |
| Jun 2026 | Graphical handoff | Real terrain tiles, LPC paper-doll NPCs, DCSS creature sprites, the "Aether" HUD. |
| Jul 2026 | Combat reinvention | Declared intents with reactions (brace / sidestep / interrupt), perfect strikes, poise and stagger, danger zones, mob tactics. |
| Sep 2026 | The Gauntlet | Blind A/B trials of graphics, playability, onboarding and progression against reference games (`docs/gauntlet/`). |
| Oct 2026 | **The 3D rebuild** | `/play` replaced the 2D clients. See below. |
| Oct 2026 | **The world rebuilt** | On the Bedlam atlas, with a hand-written build-out of every connector room. |
| Oct 2026 | **Play-testing pushes** | The owner playing XTC and Deckard: the fixes and features in §5. |

**Inside the 3D rebuild** (`docs/REBUILD_PLAN.md` has the detail):
- **Moving and fighting:** seamless walking between rooms, doors and stairs, real-time action combat
  (opt-in) on top of rounds.
- **Classes and quests:** class-themed effects for every ability, marquee class quests.
- **Look and sound:** painted icons and a themed HUD, sound and music.
- **Gear:** gear you can see on every hero and NPC, gear stats that count, resistances.
- **Systems:** procs and sets, mounts with speed and a riding model.
- **The world:** rooms that look like what they say.

---

## 3. The 3D client (`src/web_isometric/world3d/`)

There are 49 modules. The ones that matter most:

| Area | Files | What they do |
|---|---|---|
| Boot and loop | `main.js`, `engine.js`, `play.html` | The scene, the camera rig (orbit, north-up), moods (lighting by place and time), the gloom dimmer, the frame loop. `main.js` wires everything. |
| The zone | `zone.js`, `world.js`, `terrain.js`, `terrain-looks.js`, `terrain-town.js`, `../shared/roomgen.js` | Streams a zone's rooms on a grid (`/zonemap`). Each room is laid out (24×15 m) by its look and drawn with instanced kits: towns, interiors, caves, crypts, sewers, forests, mountains, water, deserts. Open-joined outdoor rooms share their whole side; empty cells get filler land. |
| Movement | `controller.js`, `passages.js`, `sync.js`, `input.js` | WASD and click-to-walk, crossing shared openings, hopping passages (stairs, misaligned exits), server sync (`webmove`). |
| Creatures and players | `entities.js`, `kin.js`, `kinrecipe.js`, `looks.js`, `bestiary.js` | Every creature its own body from a procedural kit. NPCs and other players wear their gear. Nameplates show bosses (crown), sub-bosses (gold) and elites (silver). |
| Gear on bodies | `gearlook.js`, `equip.js`, `procgear.js`, `adorn.js` | Heroes dressed in what they wear; detail grows with gear level and renown. |
| Combat | `combat.js`, `fx.js`, `fxdirector.js`, `abilityfx*.js`, `combatcues.js`, `reactions.js`, `actionclock.js`, `targeting.js` | Server combat events become animations, effects and floating text. Wind-ups mark the ground with STEP OUT. Q/E/X answer marked blows. The real-time swing clock. Lasting hazards (plague pools) and boss gloom. |
| Riding | `steed.js`, `steedlogic.js` | The hero sits their mount in a riding pose and runs at the mount's speed. A raft on open water. |
| Death traps | `deathtrap.js`, `deathlogic.js` | A ledge round a burning abyss, skulls at the ways in. The hero stops at the edge (E dares it). |
| Sound | `audio.js`, `soundtable.js`, `audio/` | Positional sound effects, ambience beds, six music tracks, place sounds (anvil, crowd, drip, wind, steps). |
| HUD | `hud/*.js`, `hud/hud.css`, `hud/theme.css` | See below. |

**The HUD (`hud/`):**
- **Frames and maps:** unit and target frames; minimap (death traps red, pings for creatures heard);
  world map.
- **Action bars** (`hud.js`, `bars.js`, `barlayout.js`):
  - main bar: 1–8 and Shift+1–8;
  - three extra floating bars, movable, turnable and lockable: Alt+1–8, Alt+Shift+1–8, and one you
    click.
- **Inventory** (`inventory.js`): drag and drop between the pack and the paper doll; rings on either
  finger.
- **Windows:** spellbook (K), character (C), journal (L), talents, almanac, travel, stable,
  services, legend, shop, loot window, talk, who, help.
- **Chat and cues:** chat; ambient cues (`ambient.js`: an arrow at the screen edge for a creature
  heard next door).
- **Riding:** the riding chip and the R key.

**Keys:**

| Key | Action |
|---|---|
| WASD | move |
| F / Space | attack |
| 1–8, ⇧1–8 | main bar |
| Alt+1–8, Alt+⇧1–8 | extra bars |
| Q / E / X | answer a marked blow |
| E | doors, and dares a death trap |
| R | ride or dismount |
| I | inventory |
| C | character |
| K | spellbook |
| L | journal |
| M | map |
| P | who |
| H | help |
| N | talents |
| Y | almanac |
| T | travel |
| U | stable |
| B | services |
| G | legend |
| O | settings |
| Tab | cycle targets |
| Esc | close windows |

**Settings (O):**
- graphics and HUD size;
- creature bodies;
- auto-loot and real-time combat;
- **extra bars (0–3)** and **ambient captions**;
- volumes per bus.

---

## 4. The server (`src/`)

There are 84 modules. The systems, and where they live:

### The world
- **Loading:** `world.py` loads `world/zones/*.json`, links exits, normalises doors, applies
  **population** (§6), resets zones and classifies room looks.
- **The atlas** (`tools/atlas/`, `world/atlas/`):
  - The world was rebuilt on the Bedlam atlas (`build_world.py`).
  - Every connector room has a hand-written description from the **build-out** (`world/buildout`).
  - Sealed lands are barred until built.
  - The God Rooms (`imm_only`) are for immortals only.
- **Map layout** (`map_system.py`):
  - `build_zonemap` lays each zone out two ways: the atlas's stored placement, and one from the exits
    alone.
  - `relax_cells` moves rooms that lead to each other side by side.
  - Each zone keeps the layout with fewer gaps. Cardinal "passages" went from 4,946 to 2,086 (about
    580 of the rest are one-way exits).
- **Room looks** (`room_looks.py`): each room gets a look (cave, crypt, sewer, forest, mountain,
  water, desert…) from its name, description and neighbours. `world/looks.json` pins exceptions.
- **Doors** (`doors.py`): states, locks, keys (`key_vnum`), picking, bashing, knocking, seals.
- **Death traps:** `commands.py` handles the death on entry, the dex save and the achievement; /play
  draws them and stops you at the edge.
- **Water** needs a boat or raft (`Room.admits`).

### Characters
- **Accounts and security:** `accounts.py`, `security.py`, `player.py`. Every character is on exactly one
  account, and the account's password is the only way in (docs/ACCOUNT_SYSTEM_PLAN.md):
  - `AccountManager` is the one place accounts and characters are made, claimed, renamed and
    deleted, for the telnet login, /play (Forge a Hero, optionally onto an account you have) and
    the in-game `account` command;
  - at start, `migrate_saves` puts any older accountless save on an account of its own name with
    the same password (backed up first);
  - salted hashing, resume tokens, and immortals (an account's `is_admin`).
- **Gifts** (`grants.py` + `world/grants.json`):
  - one-time gifts by character name, given part by part: mounts, ride, the whole map, waypoints,
    room, the endgame kit (`gearup`), gold;
  - `immortal`, which names an account (`"immortal": "<account>"`) and makes it an admin one, only
    when the character is on it (so taking a character name never gives admin).
- **Abilities:**
  - learned by level and improved by use (mastery), with trainers and a spellbook;
  - marquee abilities from class quests (`marquee.py`, `quests`);
  - `webbar` keeps the 40-slot bar layout.
- **Equipment** (`equip.py`):
  - where things go: a ring on either finger, neck and wrist pairs, the off hand for light weapons;
  - `wear/wield <item> [slot]` swaps; `remove <slot>`; `hold`; `2.ring`;
  - procs and sets (`procs.py`, `sets.py`); gear stats and resistances; item levels (`gear_look.py`);
  - what each class may wear and wield, D&D style (`class_gear.py`, [docs/gear/class_gear.md](gear/class_gear.md)).
- **Mounts** (`mounts.py`): speed (capped at +80%), loyalty, faction and boss mounts, `ride n n 3e`
  speedwalk, `mount last`.

### Combat
- **Rounds and action:** `combat.py` runs rounds. `action_combat.py` is the opt-in real-time mode
  (swing clock, global cooldown). `combat_events.py` and `combat_hooks.py` send structured events to
  /play.
- **Deaths always finish:** `handle_death` has a fallback, so a slain creature never stands on at 0
  hp.
- **Bosses** (`bosses.py`): abilities with telegraphed wind-ups, phases, adds, enrage, interrupts.
- **Boss mechanics** (`boss_mechanics.py`, set per boss in its zone's population file):
  - `plague_pools`: hazards to step out of;
  - `call_guards`: nearby creatures rush in at health thresholds;
  - `hunger`: whoever stands still starves;
  - `waves`: servants at thresholds;
  - `gloom`: the room darkens as the boss weakens.
- **Creature behaviour:**
  - **Patrols** (`mobs.patrol_ai`) walk a route.
  - **Helpers** (`allies.py`): kin within a room or two come when one is attacked.
  - **Ranks:** regular, elite, sub-boss.

### Economy and places
- **Shops** (`shops.py`):
  - the misaligned CircleMUD import is repaired at load;
  - merchants never refuse a sale for want of coin;
  - prices are sane (a raft costs 480).
- **Travel and services:** waypoints, bank, mail, storage, stable, housing, arena.

### The world's murmurs
- **Choosing a line:**
  - `ambient_place.py` reads a room's tags: castle, smithy, market, tavern, street, building, its
    look, the sky.
  - `ambient_lines.py` lists lines that need those tags.
  - So there are no merchants or smiths in a castle.
- **Creatures next door** are heard from where they are.
- **Who gets what:** telnet gets text; /play gets a sound from that direction, plus a cue for
  creatures. One system, in `ambient.py`.

### The web side
- **`web_map.py`:** `/play`, its socket (`map_data`, `combat_update`, events), `/zonemap`,
  `has_play`.
- **Moves always reach /play:** `Player.sync_room` runs after every command, and after teleport,
  recall and summon.

---

## 5. The play-testing pushes (Oct 12)

The owner's requests and what each became:

| Asked | Done |
|---|---|
| Gear procs and sets work; faster travel | Procs engine, set tiers, mount speed and the riding model |
| Loot window for corpses | Click a corpse: a window of its contents |
| Rooms look like their description | `room_looks.py`; caves, crypts, sewers, plains, forests, mountains and water drawn as such |
| Seamless rooms | Open joins share their whole side; filler land; the map re-laid (passages −58%); passages as mist, not white |
| XTC: mounts, whole map, endgame kit, wake at the Tunnel of Sticks | `world/grants.json` gifts |
| "xtc can't dismount" | R key, menu horseshoe, riding chip, right-click yourself; `mount last` |
| Can't get into Castle of the Apocalypse II | Stuck "dead" guardian fixed (deaths always finish); the door works |
| Shops won't buy; rafts cost a million | Shop import repaired; merchants always pay; a raft costs 480 |
| Deckard, full immortal | `immortal` gift; accounts made for /play characters |
| Jumpy creation menus | Hover glows instead of lifting; no scrollbar flicker |
| Death traps should look deadly | The abyss look, the edge prompt, red on the minimap |
| More bars, movable | Three extra floating bars |
| Ambient lines out of place, as text | Place-aware lines; sound and HUD cues in /play |
| Drag-and-drop gear; rings on both fingers | Inventory drag and drop; `equip.py` |
| Teleport didn't update the view | `Player.sync_room` |
| Apocalypse bosses: Kirgan, Pestilence, War, Famine, Death | Placed as the owner laid out; Kirgan's key opens the Inner Hall |
| Boss mechanics, room dynamics | Plague pools, War's guards, Famine's hunger, Death's waves and gloom |
| Populate the castle | Regulars, elites, sub-bosses, patrols, helpers |

---

## 6. Shaping the world without code (owner files)

| File | What it controls |
|---|---|
| `world/population/zone_<n>.json` | Who lives where in a zone (see below). Applied at load, so it survives rebuilds. |
| `world/grants.json` | One-time gifts to named characters: `mounts`, `ride`, `explore_all`, `waypoints_all`, `room`, `gearup`, `immortal`, `gold`. Each part is given once; edit to add more. |
| `world/looks.json` | Pins a room's or zone's look (cave, crypt, forest…) when the classifier is wrong. |
| `world/buildout/` | The hand-written build-out of connector rooms (descriptions, creatures, items), merged by `tools/atlas/build_world.py`. |
| `world/marquee/`, `world/quests/` | Class marquee quests and quest data. |

**A population file** (`world/population/zone_220.json` is the full example) can hold:
- `bosses`: placed in a room, spawning only there, with their fight `mechanics`;
- `doors`: locked to a key;
- `creatures`: new prototypes with `rank` (regular, elite, sub-boss) and `helpers`
  ({group, rooms, count});
- `spawns`: which rooms each creature appears in;
- `patrols`: routes to walk.

**Immortal commands added or changed:**

| Command | What it does |
|---|---|
| `ambient` / `ambient now` | Shows a room's place tags; sends a murmur now |
| `givemount <who> <mount>` | Gives a mount and puts them on it |
| `gearup <who>` | The endgame kit, of the class's own kind |
| `goto`, `set`, `slay`, `oload`, `restore` | As before |

---

## 7. Testing

**Offline tests** (`tests/*.py`, 35 files):
- Each loads the real world and checks a system; run with `python3 tests/<name>.py`.
- Recent ones: `test_wear`, `test_shops`, `test_ambient`, `test_population`,
  `test_castle_population`, `test_boss_mechanics`, `test_relocate`, `test_webbar`, `test_mounts`,
  `test_procs`, `test_room_looks`, `test_atlas_engine`.
- `test_webmove`, `test_mastery` and others need the server running (live telnet + socket).

**Client tests** (`tests/web/*.test.mjs`, 19 files):
- Run with `node --test tests/web/*.test.mjs`.
- They cover the pure modules: bars, layout, inventory drag, death traps, room looks, passages,
  steeds, sounds, targeting, ability effects, gear looks.

**Live probes** (`tests/web/probe_play3d.js <mode> <outdir>`):
- A headless Chromium plays /play against a running server, as the `gauntlet` test account, and
  saves screenshots.
- Run with `NODE_PATH=/opt/node22/lib/node_modules node tests/web/probe_play3d.js castlelife /tmp/out`.
- Modes: `abilityfx`, `ambient`, `atlas`, `autotarget`, `bars`, `camera`, `castle`, `castlelife`,
  `creatures`, `deathtrap`, `dnd`, `doors`, `gear`, `guardfight`, `guardian`, `horsemen`, `looks`,
  `menu`, `mount`, `party`, `seam`, `spellbook`, `stairs`, `trainer`.

**The Gauntlet** (`docs/gauntlet/`, `tools/gauntlet/`): blind A/B judging of builds against reference
games, kept for big visual or feel changes.

---

## 8. Operations

- **Deploy:**
  - Push to the deploy branch. `frostpine` pulls within a minute and restarts if code changed.
  - To deploy from `main`, set `DEPLOY_BRANCH=main` in frostpine's autopull job
    (`deploy/install-autopull.sh`).
- **Start locally:** `cd src && python3 main.py`, then open `http://localhost:4001/play`.
- **Logs:**
  - `log/mud.log` (rotating);
  - `deploy.log` on frostpine.
- **Data that is never in git:**
  - `lib/` (accounts, keys);
  - `data/` (runtime state);
  - `logs/`;
  - player files.
- **Static content** lives in `world/`, `src/` and `docs/`.

---

## 9. What's next

- **Living zones, zone by zone:** the castle is the pattern (roster, ranks, patrols, helpers, boss
  mechanics). Then come the high-level zones, and the Sunken Ruins of Atal'Narath re-themed to match
  their descriptions.
- **Seamless zone borders:** load the next zone's edge rooms in advance, so crossing a zone exit
  doesn't reload the scene.
- **Death traps:** most of Ocam's Reach and the castle paths are flagged as death traps with
  ordinary street descriptions. Review whether those flags are real.
- **Balance:** a sim pass on the new boss mechanics and the castle's elites and sub-bosses
  (`tools/balance`).
