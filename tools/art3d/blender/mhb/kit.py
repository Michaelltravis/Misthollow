"""Pieces for the heroes' equipment kit, made on the KayKit adventurers' rig (the 41-joint rig every
hero shares): the shapes, the binding, the export and the preview that models/archmage.py first
worked out, here for every look after it (models/lantern.py is the first to use them).

A look's script loads one of the pack's heroes, models its pieces in the rig's rest pose around
that body (facing -Y, metres, feet at 0), binds each to a bone (or by weights), and exports them
with a sidecar that names the kit's palette column for every colour:

    from mhb import kit
    arm = kit.load_hero('Knight')
    pal = kit.palette('lantern', {'iron': 'black_iron', 'flame': 'fire~glow'})
    ...build objects, pal.paint(...)...
    pieces = {'Lantern_Hip': (obj, 'hips')}
    kit.bind_all(pieces, arm)
    kit.export(pieces, arm, pal, 'lantern', COLS, out)        # -> out/equip/lantern.glb + .json
    kit.preview_worn(arm, kit.BODY['Knight'], pieces, 'lantern', out)

Then `node build.mjs .cache equip` puts every piece in out/equip into the kit.
"""
import json
import math
import os

import bpy
import bmesh  # (bpy first: as a Python module, bpy brings bmesh with it)

from . import scene
from .palette import Palette
from .preview import preview

HERE = os.path.dirname(__file__)
PACK = os.path.normpath(os.path.join(HERE, '..', '..', '.cache', 'kaykit-adventurers', 'addons',
                                     'kaykit_character_pack_adventures', 'Characters', 'gltf'))
RAMPS = json.load(open(os.path.join(HERE, '..', '..', 'ramps.json')))
# a hero's own body parts (what a preview keeps of the pack's model; its props give way to the look's)
BODY = {h: tuple(f'{h}_{p}' for p in ('Body', 'Head', 'ArmLeft', 'ArmRight', 'LegLeft', 'LegRight'))
        for h in ('Knight', 'Barbarian', 'Mage', 'Rogue')}
# (the hooded rogue is its own file: the rogue's parts, the hooded head)
BODY['Rogue_Hooded'] = tuple(n if 'Head' not in n else 'Rogue_Head_Hooded' for n in BODY['Rogue'])


def ramp_of(col):
    """A kit column's ramp, light to dark, as the kit build makes it: 'name', 'name~dark' (the dark
    end darkened further) or 'name~glow' (lifted, as build.mjs lifts it)."""
    name = col.split('~')[0]
    c = RAMPS['authored'][name]['c']
    rgb = lambda hx: [int(hx.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    hexs = lambda b: '#%02x%02x%02x' % tuple(max(0, min(255, int(v))) for v in b)
    if col.endswith('~dark'):
        return [hexs([v * k for v in rgb(c[2])]) for k in (1, 0.83, 0.66)]
    if col.endswith('~glow'):
        return [hexs([v * 1.12 + 18 for v in rgb(x)]) for x in c]
    return c


def palette(name, cols):
    """cols: {key: kit column}. The model's own small palette, painted with the kit's colours."""
    return Palette(name, {k: ramp_of(c) for k, c in cols.items()})


def load_hero(hero='Knight'):
    """An empty scene with one of the pack's heroes in it; returns its armature."""
    scene.reset()
    bpy.ops.import_scene.gltf(filepath=os.path.join(PACK, f'{hero}.glb'))
    return next(o for o in bpy.data.objects if o.type == 'ARMATURE')


# ---- shapes ----
def shell(name, rings, segs=12, cap_lo=False, cap_hi=False, loop=False, wave=None, smooth=True, turn=0.0):
    """rings: [(cx, cy, z, rx, ry)] from bottom to top (an rx of 0: a point, the tip); loop: the last
    ring joins the first (a closed profile). wave(angle, ring index) -> radius scale; turn: the
    first corner's angle (radians: a six-sided shell turned to put a face, not a corner, forward)."""
    bm = bmesh.new()
    rows = []
    for i, (cx, cy, z, rx, ry) in enumerate(rings):
        if rx <= 0:
            rows.append([bm.verts.new((cx, cy, z))])
            continue
        row = []
        for k in range(segs):
            a = turn + 2 * math.pi * k / segs
            w = 1 + (wave(a, i) if wave else 0)
            row.append(bm.verts.new((cx + math.cos(a) * rx * w, cy + math.sin(a) * ry * w, z)))
        rows.append(row)
    pairs = list(zip(rows, rows[1:])) + ([(rows[-1], rows[0])] if loop else [])
    for lo, hi in pairs:
        if len(hi) == 1 and len(lo) == 1:
            continue
        if len(hi) == 1:
            for k in range(segs):
                bm.faces.new((lo[k], lo[(k + 1) % segs], hi[0]))
        elif len(lo) == 1:
            for k in range(segs):
                bm.faces.new((lo[0], hi[(k + 1) % segs], hi[k]))
        else:
            for k in range(segs):
                bm.faces.new((lo[k], lo[(k + 1) % segs], hi[(k + 1) % segs], hi[k]))
    if cap_lo and len(rows[0]) > 1:
        bm.faces.new(list(reversed(rows[0])))
    if cap_hi and len(rows[-1]) > 1:
        bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    return scene.link(bpy.data.objects.new(name, me))


def ball(name, at, r, scale=(1, 1, 1), sub=2):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = scene.link(bpy.data.objects.new(name, me))
    o.location = at
    o.scale = scale
    return o


def box(name, at, size, rot=(0, 0, 0)):
    """A flat-shaded block: size (x, y, z) in metres, centred on `at`."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = scene.link(bpy.data.objects.new(name, me))
    o.location = at
    o.scale = size
    o.rotation_euler = rot
    return o


def ring(name, at, r, tube, segs=10, sides=5, rot=(0, 0, 0)):
    """A torus standing in the XZ plane (its hole along Y) before `rot`."""
    bm = bmesh.new()
    rows = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        row = []
        for j in range(sides):
            b = 2 * math.pi * j / sides
            rr = r + math.cos(b) * tube
            row.append(bm.verts.new((math.cos(a) * rr, math.sin(b) * tube, math.sin(a) * rr)))
        rows.append(row)
    for k in range(segs):
        r0, r1 = rows[k], rows[(k + 1) % segs]
        for j in range(sides):
            bm.faces.new((r0[j], r0[(j + 1) % sides], r1[(j + 1) % sides], r1[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = scene.link(bpy.data.objects.new(name, me))
    o.location = at
    o.rotation_euler = rot
    return o


def arc(name, rings, a0, a1, segs=10, thickness=0.02, smooth=False):
    """An open strip of shell: like shell(), but only from angle a0 to a1 (degrees; 0 is +X, 90 is
    +Y, the back), given a little thickness. A half-cape, a collar open at the front."""
    bm = bmesh.new()
    rows = []
    for (cx, cy, z, rx, ry) in rings:
        row = []
        for k in range(segs + 1):
            a = math.radians(a0 + (a1 - a0) * k / segs)
            row.append(bm.verts.new((cx + math.cos(a) * rx, cy + math.sin(a) * ry, z)))
        rows.append(row)
    for lo, hi in zip(rows, rows[1:]):
        for k in range(segs):
            bm.faces.new((lo[k], lo[k + 1], hi[k + 1], hi[k]))
    if thickness:
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thickness)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    return scene.link(bpy.data.objects.new(name, me))


def panel(name, y, width, top, bot, bulge=0.0, flare=0.18, x=0.0, rows=5, cols=4, thickness=0.018, ragged=0.0):
    """A hanging cloth in the XZ plane at depth y: from `top` down to `bot`, `width` wide (a little
    wider at the hem: flare), bellied out by `bulge` (negative: toward the front). ragged: how far
    every other point of the hem is cut up."""
    bm = bmesh.new()
    grid = []
    for r in range(rows + 1):
        t = r / rows
        w = width * (1 + flare * t)
        row = []
        for c in range(cols + 1):
            u = c / cols - 0.5
            z = top + (bot - top) * t + (ragged if r == rows and c % 2 else 0)
            row.append(bm.verts.new((x + u * w, y + bulge * (0.35 + 0.65 * t) * (1 - (2 * u) ** 2 * 0.5), z)))
        grid.append(row)
    for r in range(rows):
        for c in range(cols):
            bm.faces.new((grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]))
    if thickness:
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thickness)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    return scene.link(bpy.data.objects.new(name, me))


def fin(name, pts, at=(0, 0, 0), thickness=0.02, rot=(0, 0, 0)):
    """A flat blade: the outline `pts` [(x, z)] in the XZ plane, `thickness` deep along Y, then
    turned by `rot` and put `at`. A feather, a wing plate, a blade, a ray."""
    bm = bmesh.new()
    front = [bm.verts.new((x, -thickness / 2, z)) for x, z in pts]
    back = [bm.verts.new((x, thickness / 2, z)) for x, z in pts]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(pts)
    for k in range(n):
        bm.faces.new((front[k], back[k], back[(k + 1) % n], front[(k + 1) % n]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = scene.link(bpy.data.objects.new(name, me))
    o.location = at
    o.rotation_euler = rot
    return o


def cloth_weights(top, bot, legs=0.55, upper=None):
    """Weights for a cloth hanging from the hips: its top edge moves with the hips, its hem is shared
    with the legs (more to the nearer one), so it sways with the stride. upper: (z, bone) above which
    it rides that bone instead (a stole from the chest: (0.97, 'chest'))."""
    def w(co):
        if upper and co.z >= upper[0]:
            return {upper[1]: 1.0}
        if upper and co.z >= top:
            return {'spine': 1.0}
        t = max(0.0, min(1.0, (top - co.z) / max(1e-6, top - bot)))
        leg = legs * t * t
        left = 0.5 + max(-0.5, min(0.5, co.x / 0.3))
        return {'hips': 1 - leg, 'upperleg.l': leg * left, 'upperleg.r': leg * (1 - left)}
    return w


def bake(o):
    """Apply an object's own transform, so its vertices are where the rig's rest pose sees them."""
    scene.select_only(o)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


def join(name, objs):
    for o in objs:
        bake(o)
    scene.select_only(*objs, active=objs[0])
    bpy.ops.object.join()
    o = objs[0]
    o.name = o.data.name = name
    return o


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


# ---- on the rig ----
def bind(o, arm, bone=None, weights=None):
    """Bind to the rig: wholly to one bone, or by weights(world position) -> {bone: w}."""
    o.parent = arm
    if bone:
        g = o.vertex_groups.new(name=bone)
        g.add([v.index for v in o.data.vertices], 1.0, 'REPLACE')
    else:
        groups = {}
        for v in o.data.vertices:
            for b, w in weights(o.matrix_world @ v.co).items():
                if w <= 0:
                    continue
                if b not in groups:
                    groups[b] = o.vertex_groups.new(name=b)
                groups[b].add([v.index], w, 'REPLACE')
    m = o.modifiers.new('rig', 'ARMATURE')
    m.object = arm
    return o


def bind_all(pieces, arm):
    """pieces: {name: (object, bone | weights function)}; prints each piece's triangles."""
    for name, (o, how) in pieces.items():
        bind(o, arm, bone=how if isinstance(how, str) else None, weights=None if isinstance(how, str) else how)
        print('PIECE', name, tris(o), 'tris')


def export(pieces, arm, pal, name, cols, out):
    """out/equip/<name>.glb (the pieces, skinned to the rig) and its sidecar (.json: each colour's
    kit column, each piece's bone), as build.mjs's equip job reads them."""
    out = os.path.join(out, 'equip')
    os.makedirs(out, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o, _ in pieces.values():
        o.hide_render = False
        o.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    path = os.path.join(out, f'{name}.glb')
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
        export_texcoords=True, export_normals=True, export_materials='NONE', export_skins=True,
        export_def_bones=False, export_animations=False, export_lights=False, export_cameras=False)
    side = {'name': name, 'palette': {'cols': pal.cols, 'rows': pal.rows, 'keys': [cols[k] for k in pal.keys]},
            'pieces': {n: (b if isinstance(b, str) else 'skinned') for n, (o, b) in pieces.items()},
            'tris': {n: tris(o) for n, (o, b) in pieces.items()}}
    with open(os.path.join(out, f'{name}.json'), 'w') as f:
        json.dump(side, f, indent=1)
    print('exported', path)
    return path


POSES = (('Idle_Rig', 0), ('Walking_A_Rig', 8), ('Running_A_Rig', 6), ('1H_Melee_Attack_Chop_Rig', 10), ('Hit_A_Rig', 6))


def preview_worn(arm, body, pieces, name, out, poses=POSES, size=360, samples=10):
    """The pieces worn by the pack's hero (its own parts named in `body`), at rest and in a few of
    the heroes' own clips: out/<name>_preview.png. The pack's other props are taken out of the scene."""
    keep = set(body) | {o.name for o, _ in pieces.values()}
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name not in keep:
            bpy.data.objects.remove(o)
    worn = [bpy.data.objects[n] for n in body] + [o for o, _ in pieces.values()]
    dup = []
    for o in worn:
        c = o.copy()
        c.data = o.data.copy()
        scene.link(c)
        dup.append(c)
    for o in worn:
        o.hide_render = True
    bpy.ops.object.select_all(action='DESELECT')
    for c in dup:
        c.select_set(True)
    bpy.context.view_layer.objects.active = dup[0]
    bpy.ops.object.join()
    have = {a.name for a in bpy.data.actions}
    poses = tuple(p for p in poses if p[0] in have) or (('Idle_Rig', 0),)
    preview(arm, dup[0], name, out, size=size, samples=samples, poses=poses)
    return dup[0]
