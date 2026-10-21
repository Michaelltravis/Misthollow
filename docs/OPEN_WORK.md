# Open work — what is known and not yet done

Kept from 2026-10-20 (the session that moved deploys to `main`). Each item says where to start.
Strike an item out (or delete it) in the PR that finishes it.

Done in that pass, for reference: deploys from `main`; every room written (0 placeholders); the
build queue empty (items, bosses, two thin zones peopled); water breathing, corruption immunity
and song power from gear working; the live test suites passing on Windows; requirements.txt.
Then: the kick-counted-as-refused fix, shadows that fade, the Reliquary's air pockets, old
journals renamed, the Foundry's steam and levers, Shadowspire's secret ways, bosses for the
wall and the elven village, and a full test_marquee run (154 ok).

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
  open, non-connector zone of 30+ rooms. A population file's `no_boss` says why a zone has none:
  New Thalos, the Newbie Zone, the School House, Elvandar. (Garathorm Wall has Captain Greywatch
  and the Elven Village the High Elven Guardian since 2026-10-20.)
- **Captain Greywatch answers from anywhere on the wall** (`helpers.anywhere`, `src/allies.py`). If
  he proves too strong a reinforcement for the levels 5-15 there, lower his level or give him
  `rooms` instead of `anywhere`.

## Tests

- **test_aim** failed once in a full run and passed on a rerun: timing.
- The live suites need a local server and a `lib/` with the test accounts. A fresh checkout
  makes them itself (`tests/gauntlet_accounts.py`). test_combat_action levels Gauntlet up a
  little every run.

## Repository

- About 95 old automated branches (Jules / Palette, 5-8 months old, nearly all one-commit
  tweaks to `src/web_client.py`) are still on GitHub, unmerged on purpose: they predate the
  current client. Delete them when convenient.
