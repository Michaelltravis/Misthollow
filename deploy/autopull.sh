#!/usr/bin/env bash
# Deploy-from-GitHub, pull style: run every minute on frostpine (cron/launchd, see
# install-autopull.sh). When the branch on GitHub moves, pull it; restart the server only
# when something the server runs has changed (records and docs alone do not kick players).
# Needs no inbound access: frostpine reaches out to GitHub, nothing reaches in.
set -uo pipefail
# (main: what is merged is what is live; a working branch pushed mid-task no longer reaches players)
BRANCH="${DEPLOY_BRANCH:-main}"
REPO_DIR="${MUD_DIR:-$HOME/MUDNEW}"
LOG="$REPO_DIR/deploy.log"
LOCK="/tmp/mud-autopull.lock"
cd "$REPO_DIR" || exit 1
exec 9>"$LOCK"; flock -n 9 2>/dev/null || { command -v flock >/dev/null && exit 0; }   # one at a time (macOS has no flock: skip)

git fetch -q origin "$BRANCH" 2>>"$LOG" || exit 0
here=$(git rev-parse HEAD); there=$(git rev-parse "origin/$BRANCH")
[ "$here" = "$there" ] && exit 0

changed=$(git diff --name-only "$here" "$there")
if echo "$changed" | grep -qvE '^(docs/|tools/gauntlet/|\.github/|README)'; then restart=1; else restart=0; fi
{
  echo "---- $(date '+%F %T') $(git rev-parse --short "$here") -> $(git rev-parse --short "$there") (restart=$restart)"
  if [ "$restart" = 1 ]; then bash deploy/frostpine.sh "$BRANCH"; else NO_RESTART=1 bash deploy/frostpine.sh "$BRANCH"; fi
} >>"$LOG" 2>&1
