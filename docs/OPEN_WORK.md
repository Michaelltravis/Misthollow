# Open work — what is known and not yet done

Kept from 2026-10-20 (the session that moved deploys to `main`). Each item says where to start.
Strike an item out (or delete it) in the PR that finishes it.

Done in that pass, for reference: deploys from `main`; every room written (0 placeholders); the
build queue empty (items, bosses, two thin zones peopled); water breathing, corruption immunity
and song power from gear working; the live test suites passing on Windows; requirements.txt.

## Art

- **23 rooms still to be seen again** — `docs/JEV_REVIEW_SHOTS.md` lists the shots the art audit
  flagged; `docs/HANDOFF_ART_AUDIT.md` has the method (shoot, fix the land/trees, shoot again).
- **Tripo licence** — check the commercial terms of the Tripo plan before any Tripo model ships
  to players (the crystal staff, `tools/art3d/tripo.mjs`, is the only one so far).

## 3D models (the plan made with the staff's cost as the yardstick)

- **Tripo pilot** — one creature, one boss, one prop through `tools/art3d/tripo.mjs` +
  `tools/art3d/blender/models/tripo_prop.py`, rigged and shown in /play, before the batch.
- **The batch** — about 53 creatures, 48 bosses, 53 props and set pieces: about $330 of API
  credits at the staff's cost per model, plus clean-up time.
- **Character looks** — 8 classes, plus the race features: 25–40 hours.
- **A recipe skill** — write the repeatable steps (prompt, Tripo call, Blender clean-up, the
  manifest entry, the /play check) into a skill so each model is made the same way.
- **Concept art** — optional; a sheet per class/zone before the models, if wanted.

## World

- **Bosses by design, or not** — the build queue (`world/atlas/index.json`) asks a boss of every
  open, non-connector zone of 30+ rooms. A population file's `no_boss` says why a zone has none
  (New Thalos, the Newbie Zone, the School House, the Elven Village, Elvandar, Garathorm Wall);
  revisit if any of them should have one after all.
- **Shadow clones linger** — a Shadowspire hero's shadow (`src/zone_hazards.py`) is an ordinary
  Shadow Stalker once spawned: it stays in the citadel if its hero flees. Despawn it with its
  hero if that turns out to matter.
- **Drowning in the Drowned Reliquary (285)** has no air pockets of its own: 36 rooms, a minute
  of air. Add `air_pocket` rooms there (as zone 240 has) if level-60 players without water
  breathing find it impossible; the Pearl drops from the Temple of Nereus's Sahuagin.
- **Pressure and puzzles not yet read** — zone 248's `steam_damage`/`steam_pressure`/`lever` and
  zone 245's `puzzle_room` (the mirror door) are stated in the zone files but nothing runs them.
- **Old journals** still title a guildmaster "guildmaster" (entries written before the fix).

## Tests

- **test_marquee, end to end** — its fixes (raise Gauntlet for the trial and put it back, a 480 s
  budget for the Gorrund fight) passed in parts but no full run has used all of them together.
  Run `tests/test_marquee.py` against a fresh local server once; it takes about 10 minutes.
- **A kick that lands may be counted as refused** (suspected, seen once): `combat_hooks._capture`
  swaps `player.send` while a skill runs, so it also catches other tasks' lines, such as the
  action tick's "You are stunned and cannot attack!". "cannot" is a refusal word, so the
  cooldown is given back and the ability event dropped. Fix: record only the skill's own sends
  (a `contextvars.ContextVar` set in `execute()`).
- **test_aim** failed once in a full run and passed on a rerun: timing.
- The live suites need a local server and a `lib/` with the test accounts. A fresh checkout
  makes them itself (`tests/gauntlet_accounts.py`). test_combat_action levels Gauntlet up a
  little every run.

## Deploy

- Frostpine still runs the autopull.sh of `claude/nice-johnson-slpinu` until it pulls this change:
  after the merge, fast-forward that branch to `main` once
  (`git push origin origin/main:refs/heads/claude/nice-johnson-slpinu`). From then on it pulls
  `main`. Watch `~/MUDNEW/deploy.log` for `== pull main`; the old branch can go after that.
- The `Misthollow-work` worktree (branch `claude/open-work`) can be removed once this is merged.
