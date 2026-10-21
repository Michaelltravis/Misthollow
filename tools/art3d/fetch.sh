#!/usr/bin/env bash
# Download the CC0 source packs for the 3D client into a cache dir (default .cache,
# git-ignored). Files that are already there are skipped. Then run build.mjs on it.
# Sources and licences: docs/art/SOURCES.md
set -euo pipefail
CACHE="${1:-$(dirname "$0")/.cache}"
mkdir -p "$CACHE"
CACHE="$(cd "$CACHE" && pwd)"

get() {  # get <url> <dest>
  [ -s "$2" ] && return 0
  mkdir -p "$(dirname "$2")"
  curl -fsSL --retry 3 -m 600 -o "$2" "$1"
}

# KayKit packs (Kay Lousberg, CC0) are mirrored on GitHub; jsDelivr serves the files.
kaykit() {  # kaykit <repo> <local dir> <path>...
  local repo="$1" dir="$2"; shift 2
  for p in "$@"; do p="${p%$'\r'}"; get "https://cdn.jsdelivr.net/gh/KayKit-Game-Assets/$repo@main/$p" "$CACHE/$dir/$p"; done
}

A=addons/kaykit_character_pack_adventures
kaykit KayKit-Character-Pack-Adventures-1.0 kaykit-adventurers "$A/LICENSE.txt" \
  $(for n in Knight Barbarian Mage Rogue Rogue_Hooded; do echo "$A/Characters/gltf/$n.glb"; done)

S=addons/kaykit_character_pack_skeletons
kaykit KayKit-Character-Pack-Skeletons-1.0 kaykit-skeletons "$S/LICENSE.txt" \
  $(for n in Skeleton_Warrior Skeleton_Minion Skeleton_Mage Skeleton_Rogue; do echo "$S/Characters/gltf/$n.glb"; done)

D=addons/kaykit_dungeon_remastered/Assets
listing=$(curl -fsSL "https://data.jsdelivr.com/v1/packages/gh/KayKit-Game-Assets/KayKit-Dungeon-Remastered-1.0@main?structure=flat")
kaykit KayKit-Dungeon-Remastered-1.0 kaykit-dungeon "$D/LICENSE.txt" \
  $(printf '%s' "$listing" | python3 -c "import sys,json; [print(f['name'][1:]) for f in json.load(sys.stdin)['files'] if '/Assets/gltf/' in f['name'] and f['name'].endswith('.glb')]")

# KayKit packs that ship .gltf + .bin + one texture: fetch every file of the chosen models
kaykit_gltf() {  # kaykit_gltf <repo> <local dir> <regex of model names>
  local repo="$1" dir="$2" re="$3"
  local list
  list=$(curl -fsSL "https://data.jsdelivr.com/v1/packages/gh/KayKit-Game-Assets/$repo@main?structure=flat")
  kaykit "$repo" "$dir" $(printf '%s' "$list" | python3 -c "
import sys, json, re
rx = re.compile(sys.argv[1])
for f in json.load(sys.stdin)['files']:
    n = f['name'][1:]
    base = n.rsplit('/', 1)[-1].rsplit('.', 1)[0]
    if '/gltf/' in n and (n.endswith('.png') or (n.endswith(('.gltf', '.bin')) and rx.fullmatch(base))):
        print(n)
    elif n.endswith('LICENSE.txt'):
        print(n)
" "$re")
}
# the equipment kit's standalone pieces (build.mjs 'equip'): painted shields, the painted
# two-handed sword, the quiver; they share the characters' textures
kaykit_gltf KayKit-Character-Pack-Adventures-1.0 kaykit-adventurers \
  'quiver|shield_(round|badge|square|spikes)_color|sword_2handed_color'
# towns: houses, shops, temple, walls, market props (KayKit Medieval Hexagon)
kaykit_gltf KayKit-Medieval-Hexagon-Pack-1.0 kaykit-hexagon \
  '(building_(home_A|home_B|tavern|blacksmith|church|market|tower_A|well|windmill|barracks|watermill)_(blue|red|yellow|green))|barrel|bucket_water|crate_A_big|crate_B_small|crate_long_A|sack|wheelbarrow|weaponrack|tent|fence_wood_straight|fence_stone_straight|wall_straight|wall_straight_gate|wall_corner_A_outside|trees_A_medium|tree_single_A|pallet|resource_lumber|target|ladder'
# interiors (KayKit Furniture Bits) and graveyards (KayKit Halloween Bits): every model
kaykit_gltf KayKit-Furniture-Bits-1.0 kaykit-furniture '.*'
kaykit_gltf KayKit-Halloween-Bits-1.0 kaykit-halloween '.*'

# Quaternius Stylized Nature MegaKit (standard, CC0) from OpenGameArt
N="$CACHE/quaternius-nature"
get "https://opengameart.org/sites/default/files/stylized_nature_megakitstandard.zip" "$N/nature.zip"
[ -d "$N/glTF" ] || (cd "$N" && unzip -q -o nature.zip 'glTF/*' License_Standard.txt)

# Quaternius animated creatures (CC0) from OpenGameArt: FBX + textures, converted by build.mjs
oga() {  # oga <zip file name on OGA> <local dir>
  local d="$CACHE/$2"
  get "https://opengameart.org/sites/default/files/$1" "$d/pack.zip"
  [ -f "$d/.unzipped" ] || (cd "$d" && unzip -q -o pack.zip && touch .unzipped)
}
oga "cute_animated_monsters_-_aug_2020.zip" quaternius-cute-monsters
oga "Animal%20Pack%20Vol.2%20by%20%40Quaternius.zip" quaternius-animals-2
oga "Animals%20Pack%20by%20Quaternius.zip" quaternius-animals
oga "Farm%20Animals%20by%20%40Quaternius.zip" quaternius-farm
# Animated Monster Pack (dragon, bat, slime, skeleton) and the Ultimate Animated Character Pack
# (its goblins and zombies; the rest are chibi townsfolk that don't fit the KayKit look)
oga "Animated%20Monster%20Pack%20by%20%40Quaternius.zip" quaternius-monsters
oga "ultimate_animated_character_pack_by_quaternius.zip" quaternius-characters

echo "cache ready: $CACHE"
