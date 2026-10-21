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
| 0 | The brain in place, running the old rules unchanged; profiles, scoring, threat table, scheduler, debug commands; `ai.py` gone | none | done |
| 1a | Threat and targeting: damage and healing make threat; a real `taunt` for warriors and paladins; Commanding Shout and rescue fixate; healers heal only their own side; pets get a companion profile | `threat` | on |
| 1b | Tactics: creatures cast real spells; abilities cool down instead of happening once a life; heals that can be interrupted; Disrupt aimed at your healer; crowd control creatures **learn** (a school used again is resisted more, and they say so); **breakouts** (`rouse` a stunned friend, fire burns away roots and webs, damage wakes a sleeper) | `tactics` | |
| 2a | Awareness and pursuit: sight, hearing, invisibility; a path that opens, unlocks or breaks doors; every creature chases, leashes and walks home; bosses attack on sight and reset | `pursuit` | |
| 2b | Calling for help as one rule; trains in brutal zones; fleeing toward friends and coming back | `social` | |
| 3 | A living world: sleep, food, territory, predators and prey, scavengers, townsfolk who run and fetch the watch, real shop hours | `life` | |
| 4 | Conversation: NPCs remember you, answer by faction and deed, the LLM given what the brain knows | `talk` | |

## Phase 1a: threat and targeting

Each creature keeps a threat table (`brain/threat.py`).

- **Damage** adds what the blow took, times the attacker's class: warrior ×1.5 (Iron Wall ×2),
  paladin ×1.3, thief and assassin ×0.8, a player's creature ×3.
- **Healing** someone a creature fights adds half the health restored, as threat on the healer,
  shared among the creatures fighting the one healed.
- **Fading:** entries fade about a fifth a minute.

`brain/targeting.py` picks the target, once a turn:

- **The pick:** the top entry, weighed by the profile. Casters, healers who healed in the last
  10 s, and the badly hurt score higher. So do foes in reach, for a creature that fights in melee.
- **Switching:** a creature changes target only for one more than `target_stickiness` ahead
  (readable 0.3, brutal 0.1), and not twice within `switch_cooldown_s` (6 s, brutal 3 s). It never
  turns mid wind-up.
- **Announced:** a switch is said aloud ("⚔ The ogre turns on Mira!"). /play gets an `aggro`
  event and draws a red "!" over the creature as it faces its new target.
- **When its foe falls or leaves**, it takes the next one in its table who is still in the room and
  can be seen (not vanished, hidden, or invisible to it). With nobody left, it drops the fight
  after 6 s.
- **A target set by the rest of the game** (rescue, a pull, a helper joining, the older
  abilities) holds for about a round.

Taunts all go through `brain.taunted(mob, player, secs)`. Each puts the taunter above the top of
the table and holds the creature there:

| Taunt | Hold |
|---|---|
| `taunt [creature]` (warriors and paladins in a fight; 8 s cooldown; otherwise the social) | 6 s (4 s on a boss) |
| Commanding Shout | 12 s |
| Rally's taunting evolution | 6 s |
| the Unbroken Banner | 2 rounds |
| rescue | 4 s |

Commanding Shout and Rally now reach only the creatures fighting your side. Before, they pulled
every creature in the room into the fight, shopkeepers and pets included.

**Fixes that come with it:**
- A creature healer heals only its own kind: never a player's pet, a charmed creature, or one
  fighting it.
- A player's creature (a pet, a hired companion, a raised servant) no longer winds up the
  generic creature specials (heavy blows, lunges). Its owner's orders and its own kit drive it.
- Bosses target the same way: `Boss._select_target` aims at `fighting`, which the threat table
  now sets.

**Measured** (`scenarios.py threat`: warrior, cleric and mage at level 30 against 3 regulars, an
elite and 2, and boss 10050):
- A taunting tank takes 97% of the creatures' blows in a readable zone and 95% in a brutal one.
  The healer takes 3–5%.
- Readable creatures switch 0.4 times a minute, brutal ones 1.8.
- With no taunts and heavy healing, a creature turns on the healer within 7 s.
- `bosses.py` on 5 bosses: a lone hero's median worst health is 33% with threat on and off.

**The one shift:** a necromancer who out-damages their servant now draws the boss. Their worst
health against Skarg goes from 0% to 38%, and against the Spider Queen from 0% to 60%. Before,
a boss locked onto whatever engaged it first. The sim overstates this, because it never gives a
servant its own creature turn; in the game a servant swings every round. A servant's threat
counts ×3 so it can still hold.

## Checks

- `python3 tests/test_brain_core.py`: scoring, the threat table, profiles and their limits.
- `python3 tests/test_brain_hooks.py`: the brain in the real game (the hooks, the kill switch, the
  scheduler, population "ai", the creatures `ai.py` had, the debug commands).
- `python3 tests/test_brain_threat.py`: phase 1a in the real game (threat from blows and heals,
  stickiness and the cooldown, the next foe, taunts, Commanding Shout's reach, healers and pets,
  `MH_BRAIN_OFF=threat`).
- `python3 tools/balance/scenarios.py threat --check`: S1, above.
- `python3 tests/test_brain_parity.py`: with every feature off (`MH_BRAIN_OFF`),
  `tools/balance/sim.py` (rounds and real time) and `bosses.py` print the same to the byte as
  with no brain at all. `zones.py` can't be held to
  that: it gives a different answer from run to run on the same code, brain or none.
- `python3 tools/balance/scenarios.py cadence --compare --check`: a player in zone 54 for a while;
  moves, fights and thinking a tick agree with the brain on and off, and so does the time it takes.
