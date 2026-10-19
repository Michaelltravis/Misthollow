# Gameplay polish: five groups (/play)

The owner: "What else should we look at to further polish and make the game play amazing", then
"complete all the groups".

| Group | What | State |
|---|---|---|
| 1 | Every harm drawn on the body | done |
| 2 | Combat feel | |
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
