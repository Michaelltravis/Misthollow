# Gameplay polish: five groups (/play)

The owner: "What else should we look at to further polish and make the game play amazing", then
"complete all the groups".

| Group | What | State |
|---|---|---|
| 1 | Every harm drawn on the body | done |
| 2 | Combat feel | done |
| 3 | A world that feels alive | |
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
