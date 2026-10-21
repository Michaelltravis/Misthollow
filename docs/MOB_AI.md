# Mob brains (`src/brain/`)

The owner: "we need to improve NPC/Mob intelligence for the ultimate game play experience."

Creature behaviour grew up in four places that never talked to each other: `Mobile.process_ai`
(out of a fight: hunting, patrols, aggression, wandering), `mob_ai.py` (roles and wind-ups in a
fight), `bosses.Boss` (a boss's rotation) and `ai.py` (an older framework only three creatures
used, and for nothing: none of their behaviours existed). Because of that split:

- there is no threat table: a creature picks its first target at random and never changes it,
  and nothing reads a taunt;
- a creature's "spells" are formulas of their own, not `spells.py`; its buff, its pack's call
  and its enrage happen once in its life;
- only 4 creatures ever chase and give up a chase; bosses never attack on sight; nothing opens a
  door; a creature that flees never comes back;
- many flags in the data do nothing (`memory`, `aware`, `scavenger`, `aggr_evil`...), schedules
  are for show, and nobody you talk to remembers you.

The plan: **one brain per creature**, choosing by score from data, with how clever it is set by
its zone and its rank.

| Tier | Where | Feel |
|---|---|---|
| gentle | zones whose creatures' median level is under 9 | no help called, short chases, no crowd control |
| readable | most of the world | clever, and every clever move is warned of and can be answered |
| brutal | median level 45 and up | classic EverQuest: trains, long chases, packs that pile in, root and nuke |

A population file can name a zone's tier, and give a creature its own roles and numbers:

```json
{"zone": 100, "ai": {"tier": "readable"},
 "creatures": {"10050": {"rank": "boss", "ai": {"roles": ["guarded"], "profile": {"leash_rooms": 0}}}}}
```

Brutal turns up the pressure. It never takes the warning away: those limits are in the code
(`brain/profile.py INVARIANTS`), and data can only make them gentler.
- Every damaging special is wound up first.
- A real-time wind-up lasts at least 1.2 s.
- A room shows at most 4 wind-ups at once.
- A chase ends within 10 rooms or 120 s.
- A train is at most 6 creatures.

## How it fits

```
Mobile.process_ai      -> brain.think_idle(mob)     out of a fight (world.process_npcs, when due)
mob_ai.declare_intents -> brain.declare(mob)        a round's pre-pass: wind up a special?
mob_ai.mob_ai_tick     -> brain.combat_turn(mob)    the creatures' turn of a round
```

The names on the left stay what the game calls. combat_hooks wraps them, and the balance sims
call them. The brain calls back through `mob_ai.<name>`, so those wrappers stay in the chain.

| File | What |
|---|---|
| `brain/__init__.py` | the three entry points, `of(mob)`, the kill switch (`MH_BRAIN=0` or `Config.BRAIN = False`) |
| `brain/brain.py` | one creature's brain: roles, profile, mode, threat, its own dice, its last decisions |
| `brain/profile.py` | `world/ai_profiles.json`: tier ← rank ← roles ← the creature's own, inside INVARIANTS |
| `brain/roles.py` | the roles a population file gives, else `mob_ai.classify_mob`'s reading of the creature |
| `brain/utility.py` | response curves, the compensated score, momentum, choosing among the near-best |
| `brain/threat.py` | the threat table: damage, healing, taunts that fixate, decay |
| `brain/scheduler.py` | when a creature thinks, and what thinking costs (`brainstat`) |
| `brain/legacy.py` | the old rules, as the brain's first policy, until each phase replaces its part |
| `brain/debug.py` | immortal `brain <creature>` and `brainstat [reset]` |

The brain's dice are a `random.Random` of its own. It never draws on the world's `random`, so the
balance sims still replay exactly.

## Phases

Each phase ships as its own pull request, behind its flag in `world/ai_profiles.json` `features`.

| Phase | What | Flag | State |
|---|---|---|---|
| 0 | The brain in place, running the old rules unchanged; profiles, scoring, threat table, scheduler, debug commands; `ai.py` gone | none | this PR |
| 1a | Threat and targeting: damage and healing make threat; a real `taunt` for warriors and paladins; Commanding Shout and rescue fixate; healers heal only their own side; pets get a companion profile | `threat` | |
| 1b | Tactics: creatures cast real spells; abilities cool down instead of happening once a life; heals that can be interrupted; Disrupt aimed at your healer; crowd control creatures **learn** (a school used again is resisted more, and they say so); **breakouts** (`rouse` a stunned friend, fire burns away roots and webs, damage wakes a sleeper) | `tactics` | |
| 2a | Awareness and pursuit: sight, hearing, invisibility; a path that opens, unlocks or breaks doors; every creature chases, leashes and walks home; bosses attack on sight and reset | `pursuit` | |
| 2b | Calling for help as one rule; trains in brutal zones; fleeing toward friends and coming back | `social` | |
| 3 | A living world: sleep, food, territory, predators and prey, scavengers, townsfolk who run and fetch the watch, real shop hours | `life` | |
| 4 | Conversation: NPCs remember you, answer by faction and deed, the LLM given what the brain knows | `talk` | |

## Checks

- `python3 tests/test_brain_core.py`: scoring, the threat table, profiles and their limits.
- `python3 tests/test_brain_hooks.py`: the brain in the real game (the hooks, the kill switch, the
  scheduler, population "ai", the creatures `ai.py` had, the debug commands).
- `python3 tests/test_brain_parity.py`: `tools/balance/sim.py` (rounds and real time) and
  `bosses.py` print the same to the byte with the brain on and off. `zones.py` can't be held to
  that: it gives a different answer from run to run on the same code, brain or none.
- `python3 tools/balance/scenarios.py cadence --compare --check`: a player in zone 54 for a while;
  moves, fights and thinking a tick agree with the brain on and off, and so does the time it takes.
