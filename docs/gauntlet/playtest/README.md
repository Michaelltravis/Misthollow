# Human playtest — the evidence only a person can add

The automated record (`../REPORT.md`, `../STATUS.md`) is complete. What remains is a real person
playing the first ten minutes. This page is the deploy + script for that.

## Deploy from GitHub (frostpine pulls; nothing reaches in)
One-time, on frostpine (OpenClaw, or any terminal on that box):
```
cd ~/MUDNEW && bash deploy/frostpine.sh main && bash deploy/install-autopull.sh
```
After that, frostpine checks GitHub every minute (`deploy/autopull.sh`, cron). Whatever is merged
into `main` — from Claude, from GitHub's web editor, from any computer — is live within a minute
(until 2026-10-20 it was any push to `claude/nice-johnson-slpinu`). It restarts the server only when code changed (docs and gauntlet records alone
don't kick players), keeps live game data that happens to be tracked in git (`data/`, `lib/`,
`logs/`), and refuses to deploy over uncommitted code edits made on the box. Log: `~/MUDNEW/deploy.log`.
Remove with `bash deploy/install-autopull.sh --remove`.

Proxy: `map.frostpine.net/*` → :4001; `mud.frostpine.net/ws` **and `mud.frostpine.net/art/*`** → :4003
(the `/art/` route is new; without it characters render as silhouettes). Play at
`https://map.frostpine.net/play`. (This script was written for the 2D client, retired in Push 15;
`/platformer` now redirects to `/play`.)

## Script (15 minutes, one sitting, a brand-new character)
1. **forge a new soul** → human → a class from the picker (warrior, cleric, ranger carry "★ first pick").
   Note: did the picker tell you how you'd fight before you chose?
2. First screen: read only the welcome card; press **Talk to Sage Aldric** on it.
   Note: did you know what to do within ten seconds? Was anything else shouting for attention?
3. Follow the **Guide** (top-left) step by step — every step has a button. Expected route:
   temple → training dummy (**1** attack, **2** flee, **3** your class ability; **brace** when a creature
   winds up) → Light Forest rabbit/fox (south-west; the Guide gives the way) → back → Great Field (ten
   north, on the Trade Road) → Newbie Zone (east of it, 3 kills). The world is laid on the Bedlam
   atlas since Push 27: the city is Garathorm, and the Guide's directions come from the map.
   Note the clock at level 2 and level 5. Bots: 1.5–5.4 min to level 5, 0–1 deaths.
4. Walk, don't teleport: hold a direction across at least three room edges.
   Note any seam, pop-in or stall at a crossing. Bots: none since world-03 round 5.
5. In the Newbie Zone `consider` a zombie, a wanderer and a veteran: Moderate / Challenging / DEADLY
   to a level 2–3 character. Do NOT fight the DEADLY one (that is the lesson).
6. If you die: which fight, at what HP.
7. Optional multiplayer (second browser or a friend): `group <name>` in the Newbie Zone, kill something
   together, watch the partner's screen for the ally badge and the need/greed/pass popup.
8. Write five lines in `docs/gauntlet/playtest/<date>.md`: class · time to L2 / L5 · deaths ·
   the one thing that confused you · the one thing that felt best.

## Decide afterwards (then it gets executed)
- XP ramp: keep `NEWCOMER_EXP = (250, 350, 500, 650)` (`src/player.py`) or slow to 300/450/600/800.
- Hit-dice variance: keep `randint(d/2, d)` per level or tighten to `randint(0.7d, d)`.
- Defensive stance: leave as a late-game trade, or give it flat damage reduction so it pays at the mastery tier.
- Further critic rounds (walk, onboarding): ~52k tokens each.
