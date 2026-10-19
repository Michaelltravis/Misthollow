# Gameplay polish: five groups (/play)

The owner: "What else should we look at to further polish and make the game play amazing", then
"complete all the groups".

| Group | What | State |
|---|---|---|
| 1 | Every harm drawn on the body | done |
| 2 | Combat feel | done |
| 3 | A world that feels alive | done |
| 4 | Reasons to keep playing | done |
| 5 | Guidance and quality of life | done |

## 1. Harms on the body (`harms.js`, `wards.js`, `map_system._wards`)

The server names what holds or hurts a character, by its flag (`STATUS_FLAGS`: blind, sleeping,
charmed, feared, paralyzed, diseased) and by what the harm is called (`_harm_ward`: a wound over
time that is a burn, a bleed, a frost or a curse; a frost or curse that slows, holds or lowers a
stat), plus Pocket Sand's `blinded_rounds`. The 3D client draws each on the hero and on the
creatures and players about:

| Ward | Look |
|---|---|
| poisoned | green glow, bubbles, haze; a wince and a puff of gas at each tick |
| burning | a flickering red-orange glow, flames and embers, smoke over the head |
| frozen | an ice shell, a frost-blue glow, snowflakes and rime; the body moves at a fifth of its pace |
| paralyzed | a grey glow; the body stands still |
| bleeding | drops falling from the wound, and dark spots left on the ground a while |
| asleep | a Zzz over the head; slumped forward, moving slowly |
| feared | a pale blue face, sweat flying, trembling |
| blinded | a dark band over the eyes, worn on the head (it turns and nods with it) |
| charmed | hearts rising |
| silenced | a struck-through speech bubble over the head |
| cursed | dark purple wisps curling up the body and a gloom at its feet |

The strongest glow wins (frost over burn over poison); the slowest pace wins. Everything is taken
off again when the harm ends (the materials, the lean, the tremble, the band, the pace).

Checks: `node --test tests/web/wards.test.mjs`.

## 2. Combat feel

- **A heavy blow lands** (`combat.js land`): a crit or a heavy blow shoves the creature back from
  whoever struck it (0.55 m for a crit, 0.35 m heavy: `Entities.knock`) and its flinch plays
  slower, a stagger; the hero's own crit, or a crit on the hero, darts the view in and lets it
  ease back (`engine.punch`). The hit-stop and the screen shake by the size of the blow were there.
- **Each creature dies as what it is** (`corpse.js deathStyle`, played on the body by
  `entities.js dyingAs`, its particles by `main.js onDeath`): a spirit, a lich or a vampire fades
  and rises in pale light; a slime or an ooze swells and pops in a green splash; a creature of fire
  chars, glows and burns to ash in embers and smoke; a golem, a gargoyle or an elemental of stone
  or ice shatters in shards and dust; anything else falls as before. Those that did not fall
  leave remains for their corpse (a heap of ash, a puddle of goo, rubble, a faint pool of light).
- **Health running low** (30%, as the reddened edge already showed): the hero's heart beats, the
  edge pulsing in time with it; below 15% faster and redder (`main.js`, `hud.css hp-crit`).
- **A creature notices you** (it attacks you first, or charges in from next door): a "!" over its
  head and a sharp sting, once in a while each (`main.js notice`).
- **Loot**: the rarity beams were there; a "Loot gold" setting now sits by Auto-loot (the
  server's `autoloot gold`, on by default).

Checks: `node --test tests/web/corpse.test.mjs tests/web/wards.test.mjs`.

## 3. A world that feels alive

- **Weather** (`weather.js`): the server keeps a weather for each zone through the seasons
  (`weather.py`); the map payload carries the hero's (`weather`: sky, wind, precipitation). Under
  open sky (`main.js UNDER_SKY`: never in a house, cave, crypt, sewer...) the client draws it:
  rain falling slant in the wind and splashing in rings, its hiss; a storm's lightning (the scene
  lit for an instant: `engine.lightning`) and thunder a moment after; snow drifting; a desert's
  dust instead of its rain; fog closing in; leaves blown past on a strong wind. Cloud dims the sun
  and greys the haze, rain and fog draw it in (`engine.weather`, eased). `weatherKind` reads the
  sky as the ground makes it (rain on snowy ground falls as snow).
- **Grass bends** away from the hero walking through it and stirs in the wind, harder as it
  blows (`assets.js bendable`: a few lines in the instanced Grass_* tufts' vertex shader, on their
  own copy of the material).
- **Ripples** when the hero wades, and **footprints** in snow and sand (or fresh snow falling),
  left foot, right foot, fading after a while (`weather.js Ripples`, `Footprints`).
- **Small life** (`wildlife.js`, client only): birds pecking on open ground by day that take wing
  when the hero comes near or a fight starts; fireflies over grass and marsh at night; now and then
  a fish leaping from water nearby, with a splash and its rings.
- **Townsfolk keep a day** (`mobs.py Mobile._townsfolk_day`): a peaceable creature of the
  streets makes for a house next door at night and stays in; by day it comes back out.

Checks: `node --test tests/web/alive.test.mjs`; `python3 tests/test_polish.py` (townsfolk, weather).

## 4. Reasons to keep playing

- **Rare elites** (`elites.py`): checked with the weather (every five minutes), each zone with a
  player in it may get one (35%; one at a time a zone): an ordinary creature turns up with a name
  of its own ("a grizzled grey wolf"), 2.5 times the health, harder blows, three times the
  experience and four times the gold, and a piece of gear fit for its level in its pack. The zone
  is told where it was seen (in the log, and in /play a gold herald: `world_rare`); in /play it
  wears a gold ring and rising sparks (the `elite` ward).
- **The bounty board's daily bounties** (`bounties.py`): three named contracts a day (novice,
  veteran, champion), each on a dangerous creature that roams the world in numbers (never the
  town's own people, never harmless beasts): slay so many, for gold and experience by its level.
  They are daily quests offered by the bounty board's keeper, so the journal offers them and the
  tracker leads to the nearest of the creature; a new three each day.
- **Herb patches and ore veins** (`nodes.py`, drawn by `nodes.js`): about one room in five of
  forest, field, marsh, hills, mountain or dungeon holds a spot, in the same place for everyone.
  Worked (a click walks the hero over and forages or mines), it gives surely and twice (the
  second from the better half of the ground's finds), then is spent for five minutes; a ready
  spot glints, a spent one is dull.
- **The bestiary's milestones** (`achievements.py`): 10, 25, 50, 100 and 200 creatures catalogued
  are achievements, with gold, experience, titles (the Naturalist, the Beastwise, Keeper of
  Beasts, the Living Almanac) and, for the later ones, a point of wisdom or intellect.
- **Achievements in /play**: unlocked, each is heralded on screen (`world_achievement`: its icon,
  name, what it was for and any title won), not only written in the log.

Checks: `node --test tests/web/progress.test.mjs`; `python3 tests/test_polish.py` (spots,
elites, bounties, bestiary).

## 5. Guidance and quality of life

- **What the quest wants, picked out in the world**: the tracker's block says what the current
  step wants (`quest_guide.py want`: slay, speak with or pick up what); in /play a slow gold ring
  lies under each creature to slay or speak with, and under each thing to pick up
  (`combatcues.js updateQuest`).
- **Target of target**: the target frame says whom your target is fighting (`⟶ you` in red, or
  the friend it has turned on), from the payload's `fighting_name`.
- **Pings**: alt-click on the ground puts a ping there (`webping`): a gold beam and rings in the
  world and a flash on the minimap, for you and everyone in your group; once a second at most.
- **Graphics that keep up** (a performance pass, the Mac in mind): the picture's sharpness
  already followed the machine (engine.js); now a machine that still cannot keep up (slower than
  ~30 frames a second for ten seconds at the screen's own pixel density) steps the graphics down a
  notch and says so, remembered for next time; never over a quality the player chose.
- The internal commands the client sends (`webpull`, `webping`, `webtrack`, `uiseen`) no longer
  echo into the chat (server.py).

Checks: `node --test tests/web/progress.test.mjs`; `python3 tests/test_polish.py` (want, ping).
