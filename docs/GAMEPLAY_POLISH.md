# Gameplay polish: five groups (/play)

The owner: "What else should we look at to further polish and make the game play amazing", then
"complete all the groups".

| Group | What | State |
|---|---|---|
| 1 | Every harm drawn on the body | done |
| 2 | Combat feel | done |
| 3 | A world that feels alive | done |
| 4 | Reasons to keep playing | |
| 5 | Guidance and quality of life | |

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
