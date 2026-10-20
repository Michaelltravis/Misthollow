#!/usr/bin/env bash
# Run a model script headless:   tools/art3d/blender/run.sh models/wolf.py [--preview] [--out DIR]
# A model script builds one model with the mhb helpers and exports it to blender/out/<name>.glb
# (what build.mjs's 'blend' job picks up); --preview also renders turntable PNGs beside it.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/../.venv/bin/python"
[ -x "$PY" ] || PY="$HERE/../.venv/Scripts/python.exe"     # (a venv made on Windows)
[ -x "$PY" ] || { echo "no bpy: run tools/art3d/blender/setup.sh" >&2; exit 1; }
script="$1"; shift
[ -f "$script" ] || script="$HERE/$script"
PYTHONPATH="$HERE${PYTHONPATH:+:$PYTHONPATH}" exec "$PY" "$script" "$@"
