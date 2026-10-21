"""A rigid piece of gear made by Tripo (tools/art3d/tripo.mjs) made over into a piece of the equipment
kit: stood where the KayKit piece it stands in for stands, cut to its budget, repainted onto the kit's
palette and bound to one bone of the heroes' rig, so the kit build (build.mjs equip) takes it like
the archmage's pieces and the game recolours it like any other.

What it is and how it fits come from the spec's "kit" (tools/art3d/tripo/<name>.json):
  piece    the piece's name in the kit
  bone     the bone it is bound to wholly (handslot.r for what the right hand holds)
  like     the KayKit mage's piece it stands in for: the new one runs along that one's long axis,
           foot to head (the head is the wider end), at its length
  budget   at most this many triangles
  colours  {key: kit palette column} the faces may take: each face takes the one whose ramp holds
           the colour Tripo painted it nearest, at that colour's place along the ramp

    tools/art3d/blender/run.sh models/tripo_prop.py --spec tripo/staff_crystal.json --preview --export
    [--src model.glb: else the kept tripo/<name>.glb]
    -> out/tripo_<name>_preview.png (held by the KayKit mage, at rest and in a few clips) and
       out/equip/tripo_<name>.glb + .json for build.mjs equip
"""
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

from mhb import scene
from mhb.palette import Palette
from mhb.preview import preview

ART = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
KAYKIT = os.path.join(ART, '.cache', 'kaykit-adventurers', 'addons', 'kaykit_character_pack_adventures', 'Characters',
                      'gltf', 'Mage.glb')
KEEP = ('Mage_Body', 'Mage_Head', 'Mage_ArmLeft', 'Mage_ArmRight', 'Mage_LegLeft', 'Mage_LegRight')
RAMPS = json.load(open(os.path.join(ART, 'ramps.json')))


def ramp_of(col):
    """A column's ramp, light to dark (a ~glow column is its gem's ramp)."""
    return RAMPS['authored'][col.split('~')[0]]['c']


def rgb(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def lab(c):
    """sRGB (n x 3, 0..1) to CIE Lab, so 'nearest colour' is near to the eye."""
    c = np.asarray(c, dtype=np.float64)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = lin @ np.array([[0.4124, 0.2126, 0.0193], [0.3576, 0.7152, 0.1192], [0.1805, 0.0722, 0.9505]])
    xyz /= np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], axis=1)


def ramp_samples(stops, n=9):
    """n colours along a ramp and where each lies on it (1 its light end, 0 its dark end)."""
    top, mid, bot = (np.array(rgb(s)) for s in stops)
    ts = np.linspace(1, 0, n)
    cols = [top + (mid - top) * (1 - t) * 2 if t >= 0.5 else mid + (bot - mid) * (0.5 - t) * 2 for t in ts]
    return np.array(cols), ts


def world_points(o):
    return np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices])


def axes(p):
    """The centre of a cloud of points and its principal axes, longest first."""
    c = p.mean(axis=0)
    w, v = np.linalg.eigh(np.cov((p - c).T))
    return c, [Vector(v[:, i]) for i in np.argsort(w)[::-1]]


def foot_head(p, c, ax):
    """The two ends along an axis, the wider end (a staff's head, a sword's guard) as the head."""
    a = np.array(ax)
    t = (p - c) @ a
    lo, hi = t.min(), t.max()
    radial = np.linalg.norm((p - c) - np.outer(t, a), axis=1)
    span = (hi - lo) * 0.2
    wide = lambda sel: radial[sel].max() if sel.any() else 0
    lo_pt, hi_pt = Vector(c) + ax * lo, Vector(c) + ax * hi
    return (lo_pt, hi_pt) if wide(t > hi - span) >= wide(t < lo + span) else (hi_pt, lo_pt)


def face_colours(o):
    """The colour Tripo painted each face: its texture sampled at the face's middle and towards
    three of its corners, averaged."""
    me = o.data
    uvs = me.uv_layers.active.data
    images = []
    for m in me.materials:
        img = None
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and any(l.to_socket.name == 'Base Color' for l in n.outputs['Color'].links):
                    img = n.image
        images.append(None if img is None else (np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], -1), img.size))
    out = np.zeros((len(me.polygons), 3))
    for p in me.polygons:
        tex = images[p.material_index] if p.material_index < len(images) else None
        if tex is None:
            out[p.index] = me.materials[p.material_index].diffuse_color[:3] if me.materials else (0.5, 0.5, 0.5)
            continue
        px, (w, h) = tex
        corners = [Vector(uvs[li].uv) for li in p.loop_indices]
        mid = sum(corners, Vector((0, 0))) / len(corners)
        pts = [mid] + [mid + (q - mid) * 0.6 for q in corners[:3]]
        out[p.index] = np.mean([px[int((s.y % 1) * h) % h, int((s.x % 1) * w) % w, :3] for s in pts], axis=0)
    return out


def bind(o, arm, bone):
    """Bound wholly to one bone of the rig."""
    o.parent = arm
    g = o.vertex_groups.new(name=bone)
    g.add([v.index for v in o.data.vertices], 1.0, 'REPLACE')
    m = o.modifiers.new('rig', 'ARMATURE')
    m.object = arm
    return o


def pick(*objs):
    """Select just these, the first active (scene.select_only walks objects this script deleted)."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def main():
    opts = scene.args()
    argv = sys.argv
    spec_file = argv[argv.index('--spec') + 1]
    spec = json.load(open(spec_file if os.path.isabs(spec_file) else os.path.join(ART, spec_file)))
    kit = spec['kit']
    name = f"tripo_{spec['name']}"
    src = argv[argv.index('--src') + 1] if '--src' in argv else os.path.join(ART, 'tripo', f"{spec['name']}.glb")

    scene.reset()
    bpy.ops.import_scene.gltf(filepath=KAYKIT)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    # the importer leaves the rig posed in a clip's first frame (an attack): measure the piece the
    # new one stands in for at rest, where the kit binds it, or it hangs where a swinging hand is
    arm.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    like = bpy.data.objects[kit['like']]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=src)
    new = [o for o in bpy.data.objects if o not in before]
    parts = [o for o in new if o.type == 'MESH']
    for o in parts:
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world = Matrix()
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o)
    pick(*parts)
    if len(parts) > 1:
        bpy.ops.object.join()
    piece = parts[0]
    piece.name = piece.data.name = kit['piece']
    # triangles, then down to the budget (the decimator keeps the UVs, so the colours survive)
    m = piece.modifiers.new('tri', 'TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=m.name)
    got = tris(piece)
    if got > kit['budget']:
        m = piece.modifiers.new('cut', 'DECIMATE')
        m.ratio = kit['budget'] / got * 0.98
        bpy.ops.object.modifier_apply(modifier=m.name)
    print('TRIS', got, '->', tris(piece))

    # what Tripo painted, matched to the kit's colours
    painted = lab(face_colours(piece))
    keys = list(kit['colours'])
    ramps = {k: ramp_of(c) for k, c in kit['colours'].items()}
    cand, where, owner = [], [], []
    for k in keys:
        cols, ts = ramp_samples(ramps[k])
        cand.append(lab(cols))
        where += list(ts)
        owner += [k] * len(ts)
    cand = np.concatenate(cand)
    near = np.argmin(((painted[:, None, :] - cand[None, :, :]) ** 2).sum(axis=2), axis=1)

    # stood where the KayKit piece stands: foot to foot, head to head, at its length, turned so their
    # flat sides agree
    P, L = world_points(piece), world_points(like)
    arm.data.pose_position = 'POSE'
    pc, pa = axes(P)
    lc, la = axes(L)
    pf, ph = foot_head(P, pc, pa[0])
    lf, lh = foot_head(L, lc, la[0])
    rot = (ph - pf).normalized().rotation_difference((lh - lf).normalized()).to_matrix()
    d = (lh - lf).normalized()
    flat = lambda v: (v - d * v.dot(d)).normalized()
    side_p, side_l = flat(rot @ pa[1]), flat(la[1])
    roll = side_p.rotation_difference(side_l if side_p.dot(side_l) >= 0 else -side_l).to_matrix()
    s = (lh - lf).length / (ph - pf).length
    for v in piece.data.vertices:
        v.co = lf + (roll @ rot @ (v.co - pf)) * s
    print('FIT', f'scale {s:.4f}', 'length', f'{(lh - lf).length:.3f} m')

    piece.data.materials.clear()
    pal = Palette(name, ramps)
    used = {}
    for p in piece.data.polygons:
        k = owner[near[p.index]]
        pal.paint(piece, k, faces=[p.index], t=where[near[p.index]])
        used[k] = used.get(k, 0) + 1
    print('COLOURS', used)
    bind(piece, arm, kit['bone'])
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name not in KEEP and o is not piece:
            bpy.data.objects.remove(o)

    if '--export' in argv:
        out = os.path.join(opts['out'], 'equip')
        os.makedirs(out, exist_ok=True)
        pick(arm, piece)
        path = os.path.join(out, f'{name}.glb')
        bpy.ops.export_scene.gltf(
            filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
            export_texcoords=True, export_normals=True, export_materials='NONE', export_skins=True,
            export_def_bones=False, export_animations=False, export_lights=False, export_cameras=False)
        side = {'name': name, 'palette': {'cols': pal.cols, 'rows': pal.rows, 'keys': [kit['colours'][k] for k in pal.keys]},
                'pieces': {piece.name: kit['bone']}, 'tris': {piece.name: tris(piece)},
                'source': {'spec': os.path.relpath(spec_file if os.path.isabs(spec_file) else os.path.join(ART, spec_file), ART).replace(os.sep, '/')}}
        with open(os.path.join(out, f'{name}.json'), 'w') as f:
            json.dump(side, f, indent=1)
        print('exported', path)
    if opts['preview']:
        worn = [bpy.data.objects[n] for n in KEEP] + [piece]
        dup = []
        for o in worn:
            c = o.copy()
            c.data = o.data.copy()
            scene.link(c)
            dup.append(c)
        for o in worn:
            o.hide_render = True
        pick(*dup)
        bpy.ops.object.join()
        poses = (('Idle_Rig', 0), ('Spellcast_Shoot_Rig', 14), ('Spellcasting_Rig', 10), ('Running_A_Rig', 6))
        preview(arm, dup[0], name, opts['out'], size=360, samples=10, poses=poses)


main()
