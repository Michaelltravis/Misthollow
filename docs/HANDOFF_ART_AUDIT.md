# Handoff: art audit round 4

Where the art audit stands, and how to carry it on from a fresh clone. Read with the round-four
notes in `docs/REBUILD_PLAN.md` ("The art audit").

## Done (on branch `claude/nice-johnson-slpinu`)
- Feature models remade to read at the camera's distance (thrones, chain frames, crystals, bone
  heaps, braziers, lanterns, mushrooms); a room's named feature drawn larger, with more of it.
- Town-kit props (crates, sacks, weapon racks, wells, fences) were drawn at a fifth of their size.
- Features stand within the camera's view of a room's middle; frames, gates, bells and waterfalls
  face the camera.
- New scenery read from the words and drawn: gate, tree, reeds, roots, boat, mist, ice, flames,
  mirror, bell, waterfall; an indoor hearth is a fireplace.
- Zone 50 renamed The Desert River and Caverns (`world/atlas/overrides.json` `zone_names`).
- Every exception in `tools/audit/accepted.json` gets a JEV second opinion; the rooms and zones it
  did not uphold were pinned in `world/looks.json` (each with its `_why`).
- `docs/JEV_REVIEW_ZONES.md` and `docs/JEV_REVIEW_ROOMS.md`: nothing to fix. Tests pass.

## Since done (from a fresh clone, on Windows with a GPU)
- The full screenshot pass (all 611 rooms) and JEV's shots, rooms and zones verdicts over them;
  the numbers and what was fixed are in `docs/REBUILD_PLAN.md` ("The full pass, from a fresh clone").
- Left for a person: the 15 shots still listed under "To fix" in `docs/JEV_REVIEW_SHOTS.md` (each
  kept by its own words; JEV's pick from the picture swings for them), and Before The Gates Of
  Mahn-Tor (10162), where the cliffs of the room below rise through the room.

## Not done
- Nothing from this list.

## Carrying on from a fresh clone
1. `git checkout claude/nice-johnson-slpinu`; install the Python requirements, Node, and Playwright
   with its Chromium (`npm i -g playwright && npx playwright install chromium`, or the project's way).
2. Create the screenshot character and its admin account (not in git: `lib/` is ignored): run the
   snippet in `tools/gauntlet/README.md` ("capture character + admin account") once.
3. Set `TYPESAFE_API_KEY` in the terminal's environment (no `.env` file is read). Never commit it.
4. Start the server: `python3 src/main.py` (it listens on 4000/4001).
5. Shoot: `node tools/audit/shoot_rooms.js tools/audit/rooms_audit.json shots` (611 rooms; a stopped
   run picks up where it left off; GPU by default, `SOFTWARE_GL=1` for software rendering).
6. Judge: `python3 tools/jev_audit.py shots shots`, then `zones` and `rooms`. Answers are cached in
   `tools/audit/out/` (ignored by git, so a new machine asks afresh: about a dollar).
7. Fix what each report lists under "To fix", by this rule: follow JEV's pick of a look (a pin in
   `world/looks.json` with its `_why`) unless the room's own words contradict it; then keep it, with
   the words quoted, in `tools/audit/accepted.json`. Restart the server after a pin, shoot the
   rooms you changed again (delete their shots first), and judge again.
8. Rooms still judged bare: check the report's "shown" column and look at the pictures; JEV's
   bare verdict is not reliable (it calls rooms bare with the throne or crates plainly in view).
9. Put the final numbers in the round-four section of `docs/REBUILD_PLAN.md`, run
   `node --test tests/web/*.test.mjs` and the Python suites in `tests/`, open the PR and merge it.
   Gallery of the new features: `/play?demo&gallery=rooms&only=fthrone,fstore,fcrystal,fhall,fshore,fgate`.

## Lessons from the cloud run
- One login per character: never run two shooters as the same character (they knock each other
  off). A second shooter needs a second character of its own.
- A shooter's browser keeps the client code it loaded: after changing client JS, restart it.
- The mood must be snapped before a shot (`shoot_rooms.js` does), or it shows the last room's light.
