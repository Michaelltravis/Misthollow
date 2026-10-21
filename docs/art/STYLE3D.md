# 3D style and the Blender pipeline

Misthollow's 3D art should look like one game. The bought-in packs (KayKit, Quaternius, all CC0;
see SOURCES.md) set the look, and models we make ourselves in Blender must sit beside them without
standing out.

## The look

- **Shapes:** low-poly and chunky, with readable silhouettes. Exaggerate what makes a creature itself (a
  wolf's long muzzle and ruff, a dragon's horns and wings) and leave out small detail that
  disappears at game distance.
- **Colour:**
  - one small palette texture per model;
  - each colour is a ramp from light (top) to dark (bottom), the same way KayKit paints;
  - colours are muted and natural, and saturated colour is kept for what should catch the eye
    (eyes, gems, a boss's markings);
  - borrow from `tools/art3d/ramps.json` (metals, cloths, the class and set colours) where it fits.
- **Shading:**
  - bodies are soft-shaded (smooth normals over a low-poly hull);
  - small hard parts (horns, claws, teeth, plates) are flat-shaded.
- **No baked lighting and no normal maps.** The engine lights everything (`engine.js` moods).

## The rules every model keeps (checked)

| Rule | Checked by |
|---|---|
| One skinned mesh, one armature, one material (the palette) | `qc_models.mjs` |
| Triangles: creature ≤ 3,000, steed ≤ 3,000, boss ≤ 8,000, prop ≤ 1,500 | export and `qc_models.mjs` |
| Real size in metres, feet at 0, centred on its origin | export |
| Faces the game's +Z: model it facing −Y in Blender | gallery arrow and preview |
| Clips `Idle`, `Walk`, `Bite_Front` (attack), `HitRecieve` (sic), `Death`; optionally `Run`, `Bite_InPlace` (roar, breath, cast) and `Jump` | export and `qc_models.mjs` |
| `Idle` and `Walk` loop seamlessly; `Death` ends lying still on the ground | preview |

The clip names are the Quaternius ones, which `world3d/assets.js` `aliasFor()` already maps onto
everything the game plays.

## The pipeline

```
tools/art3d/blender/setup.sh                       # once: bpy 4.2 LTS in tools/art3d/.venv
tools/art3d/blender/run.sh models/<name>.py --preview
    -> tools/art3d/blender/out/<name>.glb, <name>.json, <name>_preview.png
cd tools/art3d && node build.mjs blend [name]      # -> src/web_isometric/art3d/bodies/ + index.json
node tools/art3d/qc_models.mjs                     # the rules above
/play?demo&gallery=bodies                          # in the game's own renderer
```

Claude does the work in Blender by writing the model script, rendering the preview, looking at
it and revising. No screen is needed. The game gallery has the final say.

### Kit pieces from Tripo (`tools/art3d/tripo/`)

Gear can be made by Tripo's API instead of by hand (SOURCES.md says where it comes from): a spec
in `tripo/<name>.json` holds the prompt, the model settings and how the piece fits the kit.

```
node tools/art3d/tripo.mjs concepts tools/art3d/tripo/<name>.json      # concept images; pick one
node tools/art3d/tripo.mjs model tools/art3d/tripo/<name>.json --concept N   # -> tripo/<name>.glb
tools/art3d/blender/run.sh models/tripo_prop.py --spec tripo/<name>.json --preview --export
```

The equipment kit takes every piece in `blender/out/equip`, which git ignores: before
`node build.mjs .cache equip`, export all of them (`models/archmage.py --export` and
`models/tripo_prop.py --spec ... --export` for each spec), or the rebuilt kit loses the ones left
out. On Windows, `setup.sh` needs Python 3.11 for bpy 4.2: `uv venv --python 3.11 tools/art3d/.venv`
and `uv pip install --python tools/art3d/.venv/Scripts/python.exe "bpy==4.2.*"` does it.

### Writing a model (`tools/art3d/blender/mhb`)

- **`Skel`:** the body as a graph of points with radii.
  - `node(name, co, r, parent, sx)` adds a point;
  - `hull()` wraps the graph in a skin and smooths it, rounding the tips;
  - `armature()` makes one bone per point, named after it.
- **`part(kind, name, at, size, rot)`:** small rigid pieces (horns, eyes, claws, plates), each
  painted and then pinned to a bone.
- **`finish_body(body, arm, [(part, bone), ...], budget)`:** weights the body to the bones, decimates
  it into budget, and joins everything into one skinned mesh.
- **`Palette(name, {key: '#hex' | [top, mid, bottom]})`:** the colours.
  - `paint(obj, key)` gives a part one flat colour;
  - `paint_ramp(obj, key)` shades along the ramp by height.
- **`Clips(arm)`:** `with c.clip('Walk', 24, loop=True) as k: k.rot(bone, frame, x=..)`.
  Rotations are in degrees about the bone's own axes.
- **`mhb.export(...)` and `mhb.preview(...)`:** see `models/proof_imp.py` for a whole example.

## Judging

Each new model is compared blind with what it replaces, in the game's gallery and against a named
reference shot (a KayKit or Quaternius model of the same kind). The comparison uses the
`gauntlet-loop` skill, with records in `docs/gauntlet/`. The owner signs off each batch before it
goes into the game.

## The bodies so far (`tools/art3d/blender/models`, `art3d/bodies`)

| Script | Variants (bosses in bold) |
|---|---|
| wolf.py | wolf (also dogs, foxes, jackals, hellhounds) |
| dragon.py | dragon, **frost_wyrm** (Vyrkothas) |
| spider.py | spider, **spider_queen** |
| ghost.py | ghost, elemental |
| snake.py | snake, serpent (also worms and centipedes) |
| brute.py | ogre, troll, yeti, minotaur (also **King Minos**) |
| demon.py | demon, **fiend** (balor, pit fiend, Cinder Tyrant), imp, kobold |
| beast.py | cat, lion, bear, rat, **rat_king** (Sewer King), deer, horse, unicorn, lizard, crocodile, rabbit, pig, sheep, cow, camel, frog |
| bird.py | bird, eagle, **roc** (Roc Matriarch) |
| shell.py | crab, scorpion, turtle, clam (also oysters and mussels) |
| fish.py | fish, shark, whale, ray (manta rays, the ixitxachitl) |
| insect.py | beetle, wasp, **stick_mother** |
| tentacle.py | mindflayer, **overmind** (Master Mindflayer), horror |
| growth.py | treant, myconid, beholder |

Shared pieces live in `mhb/forms.py` (humanoid and quadruped frames with their clips) and
`mhb/gaits.py` (walks, many-legged gaits, slither, wing beats, deaths). A bestiary entry picks a
body with `body:`; an index `look` gives opacity or glow, and `ref` sizes a long, low body by its
length. To compare old and new, use `/play?demo&gallery=kin&add=...` with and without `&nobodies`.

Only a few creatures stay on bodies built in code (kin.js), on purpose: true slimes and oozes (gray ooze,
ochre jello, gelatinous blob, Mudmonster, lemure, yochlol, pit beast, dustdigger, moon jellyfish) and the
hands, arms and feet that reach out of walls. Ducklings and penguins keep their pack models (`prefer: true`).
