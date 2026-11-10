# The seamless pass (November 2026)

The owner: "polish every aspect of the game from game play, UI, and graphics. I need everything
to be seamless." How it was done: the game was played in `/play` as the test warrior Gauntletb
(title screen, hero list, the Temple, the Newbie Zone, a fight to the death of a baby dragon,
every main window), and three read-only audits traced the HUD, the 3D client and the server's
play rules in code. What follows is everything found, in the order it should be done. Pass 1 is
done on the branch `claude/seamless-polish`; the rest is the plan.

## Pass 1: done

### Play (server)

| What a player met | Fixed |
|---|---|
| **Dying in a fight emptied your pack into a corpse at the Temple, and copied your gold.** `Player.die()` moves you to the Temple, then `handle_death` built the corpse where you now stood, holding everything you carried and a copy of your gold beside the gold you kept. Each death could double your gold. | `combat.py`: a fallen player keeps their pack and leaves no corpse; death's price is what `die()` takes (exp, 5% of the gold). The gravestone stands where they fell, not at the Temple. |
| **Death traps did not kill.** The trap called `handle_death(player, player)`: you stayed standing in the trap, your gold gone. | `commands.py`: the trap calls `player.die()`. |
| **Flee could pick a death trap or a shut door.** The fight ended, "You flee north!" printed and 1% exp was taken even when the move was then refused. | `combat.py` `_may_take`: no flight through a shut door or into a death trap; exp is lost only for a flight that got somewhere. |
| **A save caught mid-death loaded at -7 hp.** | `player.py`: health loads at 1 or more. |
| "You drop 47 gold coins" on death (nothing is dropped) | "You lose". |

Checks: `tests/test_death.py` (14 checks).

### HUD

| What a player met | Fixed |
|---|---|
| Title screen with several heroes: the logo cut off at the top, the quote written over "Switch account" | The screen scrolls rather than clips, the logo and list give way to a short window, the quote sits below the card. |
| The quest tracker said the step twice | Said once, in bold, where it stands in the list. |
| The minimap cut the zone's name short ("Garathorm Inn…") | It has the width of the map. |
| Windows stacked by their place in the page, not by which opened last; Esc closed every window at once | The window opened last is in front; Esc closes that one, then the next, then drops the target. |
| Esc did nothing in a search box | It steps out of the box. |
| Settings ran off the top of a short window and had no scroll | It keeps to the window and scrolls. |
| Toasts ("Quest abandoned") drew behind the window that raised them | In front. |
| HUD size "Auto" looked only at the width, so a wide, short window got the largest HUD | The height counts too. |
| Chat tabs cut off ("COM…") | They scale with the HUD. |
| The give list stopped at 24 things | All of them. |
| Menu and close buttons clicked twice (the button, then the window) | Once. |
| `> cleave #46` in the chat log | `> cleave`. |
| "Connecting to ws://localhost:4003/ws…" | "Connecting…". |
| The menu's round buttons had no name for a screen reader; looping animations ignored "reduce motion" | Named; one rule stills them all. |

### The 3D client

| What a player met | Fixed |
|---|---|
| Choosing a hero left the title scene standing for seconds under the game's HUD | The mist veil covers the handoff and parts on the built world. |
| Light and fog never quite reached a room's mood (the blend went through 8-bit colour each frame and stalled, sooner at high frame rates) | The colour in flight is kept whole. |
| Creatures snapped to face you | They turn, quickly, the short way round. |
| Rain fell indoors for six seconds after stepping in | Gone as you step in. |
| Rain pulsed every 1.4 s; an old ambience bed held on, then cut | Rain swells in; the bed's swell fades with it. |
| "Screen shake: off" left hit-stop and the zoom punch on | Off means off. |
| Rooms left behind kept their instanced props on the GPU | Freed when a room is released. |
| three.js warned of `PCFSoftShadowMap` each load | `PCFShadowMap`. |

Checks: `node --test tests/web/*.test.mjs` (250 pass), `test_polish`, `test_loot`,
`test_combat_text`, `test_suite`, `test_web_hud`, `test_web_menus`; and by eye in `/play`.
(`test_gates` fails 9 checks on this branch with or without these changes: zones 245, 474,
488, 491, 505 and others have no creature in the room named for its owner.)

## The owner's direction, part way through (9 November)

"I don't care about telnet. I want the 3d environment, characters, and play to be amazing and
engaging. The character models and graphics need to blow people away." And: "the overall world
needs to be cohesive and engaging. I want an amazing well thought out world!" From here the
order of work is: how characters and the world look, how play feels, how the world hangs
together. HUD and text come after.

## Pass 3 and the first of the look: done

**HUD (from pass 3 below):** a window that could not fetch its data says so, with Retry (eight
windows, `hud/netfail.js`); item tooltips and menus keep to the screen by their own size; a
tooltip no longer sticks when its slot is re-drawn; the login button waits for an answer; the
creation choices take Tab, Enter and Space; E/Q/X no longer fire inside a list and I/C/K not
with Alt; the zone map opens on the whole zone, its unseen rooms clearer; every window fades
in; tips, the welcome and "Huh?!?" speak of keys and windows on /play (`tips.PLAY_TIPS`).

**How characters are lit (`charlook.js`, `charlight.js`):** seen from behind in a torch-lit
hall the hero was the darkest thing on the screen. Every body (hero, players, creatures) now
gets, on top of the room's light: a rim light in the colour of the place's sky, a floor of
its own colour so nobody is a silhouette (more of both the darker the place), and a soft
shadow at its feet where the sun casts none.

**The picture (`engine.js`):** edges are smoothed on Med and High (the scene was drawn into an
unsampled target, so the canvas's antialiasing never applied); a grade before the tone map
gives back the contrast and colour ACES took from the kits' flat colours.

Checks: `tests/web/charlight.test.mjs`; by eye in the Newbie Zone's hall and the Temple
Fountain by day.

## What code cannot do: the two decisions that set the ceiling

1. **The character models.** Heroes and people are the KayKit kit: charming, small-headed toy
   figures, the same body for everyone. Light, materials and animation can make them read
   well; they cannot make them "blow people away". That needs new character art: the Tripo
   plan in `docs/OPEN_WORK.md` (a pilot of one creature, one boss, one prop; then about 53
   creatures, 48 bosses and the 8 classes, about $330 of credits plus clean-up), or a bought or
   commissioned character set. The pilot is the next step, and it needs the owner's go-ahead
   (cost, and the Tripo licence check noted there).
2. **One world.** 125 zones and 9,280 rooms came from many hands (CircleMUD areas, the Bedlam
   atlas, the build-out). A cohesive world needs a spine: the regions and what each is, the
   road a hero walks from level 1 to 60, the powers and their quarrels, and each zone given
   its place in that (or cut). That is a design document first, then zone-by-zone work.
   **The design is written: `docs/world/WORLD_SPINE.md`** (the premise, nine regions, the road
   from level 1 to 70, and a ledger of all 122 zones). It waits on the owner's read.

## Characters without a budget: scripted models (done)

The owner has no money for bought 3D art. The project already had the answer: models written as
Blender scripts (`tools/art3d/blender`, Blender's Python module in `tools/art3d/.venv`), built
and rendered headless, in the same low-poly style as the CC0 packs. A hero is the pack's body
dressed from one equipment kit, so what heroes gain is **pieces on the shared rig**: they move
with all 68 clips.

- **The lantern** (`models/lantern.py`): every hero carries a small iron lantern behind the
  right hip, its flame lit; out of the dark it casts a little warmth at their feet. The world's
  one sign (`docs/world/WORLD_SPINE.md`), on every player.
- **A look for every class** (`models/warden.py`, `models/classlooks.py`, with the mage's
  earlier `models/archmage.py`): the warrior's warden, the paladin's templar (a glowing halo,
  winged pauldrons, a sun tabard), the cleric's hierophant, the thief's footpad, the assassin's
  nightblade, the ranger's wayfinder, the bard's troubadour (a lute on the back), the
  necromancer's gravecaller (bone spikes, a skull on the shoulder with lit eyes). 54 pieces.
  Chosen in the Character window (C: "Look") or with `appearance <look>`; only a mage is asked
  at creation. `mhb/kit.py` holds the shapes and the export, so a new look is a short script.
- Checks: `tests/test_warden_look.py`, `tests/web/gearlook.test.mjs` (every class's look, its
  pieces in the kit, nobody else's), `node tools/art3d/qc_models.mjs`; the warden and the
  templar seen in the live game.

What this route does not do: it adds character and silhouette in the house style; it is not a
higher-fidelity art style. Bodies and faces are still the pack's.

## The second 3D and play pass (done)

- Shadows no longer crawl as the hero walks (the sun moves in steps of one shadow texel).
- Torch light no longer jumps from torch to torch (a pooled light goes out before it moves).
- Creatures swell into place over a fifth of a second instead of appearing whole.
- A nameplate's health bar is written only when the health changes.
- Trackers no longer follow a scent into a peaceful room (`mobs.py`).
- Sage Aldric gives the next lesson to a pupil who abandoned one (`quests.resume_tutorial`):
  abandoning a tutorial step used to end the chain for good.

Tried and taken back: creatures shrinking away as they leave (a vanished creature is held one
frame for its corpse to claim; the two did not fit).

## Pass 2: the owner's calls (each changes how the game plays)

1. **What creatures are called.** The log says "You attack dragon!", "newbie marches east",
   "Dragon is DEAD!" while the nameplate says "Baby dragon". `Mobile.said_name` keeps one-word
   names on purpose (`tests/test_mob_names.py`: "a one-word name stays"). Proposal: say the
   description ("the baby dragon") whenever it is a name and not a sentence; the keyword stays
   for targeting.
2. **Rest between fights.** A 75 hp warrior regains about 8 hp a minute standing in town (3 when
   thirsty): five to seven minutes from a death back to full. Proposal: a fast out-of-combat
   rate (5% every 5 s after 8 s without a fight); hunger and thirst slow it less.
3. **Auto-loot items on by default** for new characters (gold already is), and **wimpy** at 20%
   for levels 1-10 now that flight is safe.
4. **Logging in where you logged out, mid-danger.** A hero saved in a hostile room at low health
   wakes among the same creatures (this is how Gauntletb died on login). Proposal: wake at the
   Temple when the saved room is hostile and health is under 30%, and a few seconds of grace.
   Dropping the connection in a fight is also a free escape.
5. **A baby dragon (level 4, 83 hp) against a level-6 warrior hitting for 6-10** is about ten
   rounds. Low-level fights may want fewer hit points or harder blows (`tools/balance`).

## Pass 3: HUD (from the audit, not yet done)

- Network failures shown as empty data in eight windows ("no shopkeeper here", "0 gold in the
  bank"): say "Could not reach the server" with Retry.
- Three tooltip systems (`.tipcard`, `#item-tip`, the browser's `title=`): one.
- Item tooltip and item menu can leave the screen (`inventory.js` clamps by constants).
- Centre-screen popups share one column and can overlap (toasts, banner, herald, react prompt).
- A tooltip can stick when the slot under the cursor is re-drawn.
- Windows close at once but fade in; the tracker and party frames have no entrance.
- Four button styles and about 277 raw colours in `hud.css`: tokens (`--gold-edge`, `--danger`,
  `--warn`) and `.btn.sm`.
- Creation choices are `<div>`s (no keyboard); login has no busy state.
- E/Q/X fire inside a `<select>`; I/C/K toggle with Alt held.
- The zone map opens small and dim in a large dark field: fit it to the zone, lift the contrast.
- Tutorial lines that still say "type" on /play: the welcome banner (`server.py:586`,
  `quests.py:2726`), tips (`tips.py`), "Huh?!? Type 'help'" (`commands.py:404`).
- Room text: "you here noises" (Newbie Zone); `(dragon)` keyword tails on room lines in /play.

## Pass 4: the 3D client (from the audit, not yet done)

- **No antialiasing on Med/High** (bloom renders into a target without samples): give the
  composer a 4-sample target.
- **Room pop-in and build hitches**: `zone.js` builds one whole room a frame at full opacity;
  time-slice it and swap the far stand-in in the same frame.
- **Zone borders rebuild everything**: prebuild the next zone's near rooms before the swap.
- Creatures and other players appear and vanish at full opacity: a quarter-second fade.
- Torch light jumps between torches (six pooled lights re-assigned at full strength).
- Shadows shimmer as you walk (snap the sun to shadow texels) and end in a hard line at far zoom.
- Other players stutter (they reach each 5 Hz goal early and idle).
- A dip to the bind pose after one-shot clips (`assets.js`).
- Ground rings sink into rough outdoor ground.
- Creature bodies are never disposed (`kin.js` makes fresh geometry per creature).
- Quality changes do not reach particles, weather or audio budgets.
- Per-frame DOM work for nameplates (`entities.js` reads layout each frame).
- `THREE.Clock` is deprecated (`engine.js`, `hud/stage.js`): `THREE.Timer`.
- The hero is a dark shape in dim rooms seen from behind: a soft rim or fill light of their own.

## Pass 5: play (from the audit, not yet done)

- 23 `peaceful` rooms lack `no_mob`; the old movement code checks only `KEEP_OUT`.
- Abandoning a tutorial quest ends the chain for good: Sage Aldric should offer the next step.
- `sync_room` only pushes when the room changed; a state change in place can leave /play stale.
- The 65 and 54 `except Exception:` blocks in `commands.py` and `combat.py` have not been read
  for swallowed failures.
