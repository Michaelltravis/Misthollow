"""The archmage look: new pieces for the mage, made to sit on the KayKit adventurers' rig (the
41-joint rig every hero shares, art3d/chars) so they move with every clip the heroes play and go
into the equipment kit like the pack's own hat and cape. Each piece is modelled in the rig's rest
pose around the KayKit mage and bound to its bone (the hat and beard to the head, the mantle to the
chest, the cuffs to the forearms, the sash to the hips, the staff to the right hand); the robe's
skirt is weighted between the hips and the legs so it swings as they stride.

    tools/art3d/blender/run.sh models/archmage.py --preview [--variant blue|crimson|white]
    -> out/archmage_<variant>.glb (the pieces on the rig) and out/archmage_<variant>_preview.png
       (worn by the KayKit mage, at rest and in a few of the heroes' own clips)
"""
import math
import os

import bpy
import bmesh  # (bpy first: as a Python module, bpy brings bmesh with it)
from mathutils import Vector

from mhb import scene
from mhb.palette import Palette
from mhb.preview import preview

KAYKIT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '.cache', 'kaykit-adventurers',
                                       'addons', 'kaykit_character_pack_adventures', 'Characters', 'gltf', 'Mage.glb'))
# the mage's own parts that the look keeps (its pack hat, cape and props give way to the new ones)
KEEP = ('Mage_Body', 'Mage_Head', 'Mage_ArmLeft', 'Mage_ArmRight', 'Mage_LegLeft', 'Mage_LegRight')

VARIANTS = {
    # robe, robe's shadow, trim, sash, beard, the gem and orb's glow
    'blue': {'robe': '#33418f', 'deep': '#232d66', 'trim': '#d6a542', 'sash': '#8e2a35', 'beard': '#ebe6dc', 'glow': '#62e3ff'},
    'crimson': {'robe': '#8a2a33', 'deep': '#5a1a22', 'trim': '#d6a542', 'sash': '#2b2b33', 'beard': '#ebe6dc', 'glow': '#ff9a3c'},
    'white': {'robe': '#e4e0d4', 'deep': '#b8b2a2', 'trim': '#c8ccd6', 'sash': '#3a4a8a', 'beard': '#f4f2ec', 'glow': '#9ad8ff'},
}


# ---- shapes: rings of points round an axis, stitched into a shell ----
def shell(name, rings, segs=12, cap_lo=False, cap_hi=False, loop=False, wave=None):
    """rings: [(cx, cy, z, rx, ry)] from bottom to top (an rx of 0: a point, the tip); loop: the last
    ring joins the first (a closed profile: a brim). wave(angle, ring index) -> radius scale."""
    bm = bmesh.new()
    rows = []
    for i, (cx, cy, z, rx, ry) in enumerate(rings):
        if rx <= 0:
            rows.append([bm.verts.new((cx, cy, z))])
            continue
        row = []
        for k in range(segs):
            a = 2 * math.pi * k / segs
            w = 1 + (wave(a, i) if wave else 0)
            row.append(bm.verts.new((cx + math.cos(a) * rx * w, cy + math.sin(a) * ry * w, z)))
        rows.append(row)
    pairs = list(zip(rows, rows[1:])) + ([(rows[-1], rows[0])] if loop else [])
    for lo, hi in pairs:
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
        p.use_smooth = True
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


def star(name, at, r, depth=0.03):
    pts = [(math.cos(-math.pi / 2 + i * math.pi / 5) * (r if i % 2 == 0 else r * 0.45),
            math.sin(-math.pi / 2 + i * math.pi / 5) * (r if i % 2 == 0 else r * 0.45)) for i in range(10)]
    bm = bmesh.new()
    front = [bm.verts.new((x, -depth / 2, y)) for x, y in pts]
    back = [bm.verts.new((x, depth / 2, y)) for x, y in pts]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    for k in range(10):
        bm.faces.new((front[k], back[k], back[(k + 1) % 10], front[(k + 1) % 10]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = scene.link(bpy.data.objects.new(name, me))
    o.location = at
    return o


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


def bind(o, arm, bone=None, weights=None):
    """Bind to the rig: wholly to one bone, or by weights(vertex) -> {bone: w}."""
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


# ---- the pieces ----
def hat(pal):
    z0, h = 2.0, 1.15
    rings = []
    for i in range(10):
        t = i / 9
        bend = max(0.0, t - 0.42) / 0.58
        r = 0.58 * (1 - t) ** 0.85 + (0.012 if i < 9 else 0)
        rings.append((-0.12 * bend ** 1.5, 0.5 * bend ** 2, z0 + t * h - 0.35 * bend ** 3, r if i < 9 else 0, r if i < 9 else 0))
    crown = shell('crown', rings, segs=12)
    pal.paint_ramp(crown, 'robe')
    # the brim: a flat ring, floppy at its edge
    brim = shell('brim', [(0, 0, z0 + 0.03, 0.52, 0.52), (0, 0, z0 - 0.01, 0.98, 0.96), (0, 0, z0 - 0.1, 1.08, 1.06),
                          (0, 0, z0 - 0.08, 0.98, 0.96), (0, 0, z0 - 0.02, 0.52, 0.52)], segs=16, loop=True,
                 wave=lambda a, i: 0.05 * math.sin(3 * a + 0.6) if i in (1, 2, 3) else 0)
    pal.paint(brim, 'deep')
    band = shell('band', [(0, 0, z0 + 0.02, 0.595, 0.595), (0, 0, z0 + 0.2, 0.555, 0.555)], segs=12)
    pal.paint(band, 'trim')
    gem = ball('gem', (0, -0.6, z0 + 0.11), 0.08, scale=(1, 0.6, 1.15))
    pal.paint(gem, 'glow')
    setting = ball('setting', (0, -0.57, z0 + 0.11), 0.11, scale=(1, 0.4, 1.25), sub=1)
    pal.paint(setting, 'trim')
    tip = Vector(rings[-1][:2] + (rings[-1][2],))
    charm = star('charm', tip + Vector((0.0, 0.02, -0.22)), 0.09)
    pal.paint(charm, 'trim')
    cord = shell('cord', [(tip.x, tip.y + 0.02, tip.z - 0.15, 0.012, 0.012), (tip.x, tip.y, tip.z + 0.01, 0.012, 0.012)], segs=5)
    pal.paint(cord, 'trim')
    return join('Archmage_Hat', [crown, brim, band, gem, setting, charm, cord])


def beard(pal, head):
    """Grown from the face: the jaw and cheeks of the mage's own head, lifted a little off the skin
    and given thickness (so it hugs the face, with sideburns up the sides), and from under the chin
    a long beard hanging over the chest; a moustache over the mouth."""
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bm.transform(head.matrix_world)

    def keep(f):
        c = f.calc_center_median()
        ax = min(1.0, abs(c.x) / 0.45)
        return c.y < -0.05 and 1.18 < c.z < 1.37 + 0.16 * ax
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep(f)], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * 0.035
    me = bpy.data.meshes.new('jaw')
    bm.to_mesh(me)
    bm.free()
    jaw = scene.link(bpy.data.objects.new('jaw', me))
    sol = jaw.modifiers.new('thick', 'SOLIDIFY')
    sol.thickness = 0.03
    sol.offset = -1
    scene.select_only(jaw)
    bpy.ops.object.modifier_apply(modifier='thick')
    for p in me.polygons:
        p.use_smooth = True
    pal.paint(jaw, 'beard')
    rings = [(0, -0.46, 0.66, 0, 0), (0, -0.47, 0.75, 0.08, 0.06), (0, -0.49, 0.86, 0.2, 0.11), (0, -0.5, 1.0, 0.3, 0.14),
             (0, -0.47, 1.16, 0.34, 0.15), (0, -0.38, 1.3, 0.28, 0.12)]
    hang = shell('beard', rings, segs=12, cap_hi=True, wave=lambda a, i: 0.07 * math.sin(5 * a) if 1 <= i <= 4 else 0)
    pal.paint_ramp(hang, 'beard')
    parts = [jaw, hang]
    for sd in (-1, 1):
        m = ball(f'moustache{sd}', (sd * 0.12, -0.47, 1.36), 0.09, scale=(1.5, 0.55, 0.5), sub=2)
        m.rotation_euler = (0, sd * math.radians(-24), 0)
        pal.paint(m, 'beard')
        parts.append(m)
    return join('Archmage_Beard', parts)


def robe(pal):
    """The skirt from the sash to the ankles, flaring, gold at the hem."""
    rings = [(0, 0.0, 0.68, 0.40, 0.37), (0, 0.01, 0.52, 0.46, 0.42), (0, 0.02, 0.34, 0.53, 0.48),
             (0, 0.03, 0.18, 0.59, 0.53), (0, 0.03, 0.12, 0.61, 0.55)]
    s = shell('skirt', rings, segs=16, wave=lambda a, i: 0.04 * math.sin(4 * a) if i >= 3 else 0)
    pal.paint_ramp(s, 'robe', lo=0.05, hi=0.75)
    hem = [p.index for p in s.data.polygons if (s.matrix_world @ p.center).z < 0.16]
    pal.paint(s, 'trim', faces=hem)
    return join('Archmage_Robe', [s])


def robe_weights(co):
    """Hips at the waist, the legs more and more toward the hem, each side to its own leg."""
    f = max(0.0, min(1.0, (0.68 - co.z) / 0.56))
    leg = 0.85 * f
    side = max(0.0, min(1.0, 0.5 + co.x / 0.3))        # +x is the left leg
    low = max(0.0, min(1.0, (0.34 - co.z) / 0.22)) * 0.5
    w = {'hips': 1 - leg}
    for b, sh in (('l', side), ('r', 1 - side)):
        w[f'upperleg.{b}'] = leg * sh * (1 - low)
        w[f'lowerleg.{b}'] = leg * sh * low
    return w


def mantle(pal):
    rings = [(0, 0.03, 0.98, 0.6, 0.5), (0, 0.03, 1.06, 0.6, 0.5), (0, 0.03, 1.13, 0.55, 0.46), (0, 0.03, 1.19, 0.36, 0.33)]
    m = shell('mantle', rings, segs=16, wave=lambda a, i: 0.05 * math.sin(6 * a) if i == 0 else 0)
    pal.paint(m, 'deep')
    edge = [p.index for p in m.data.polygons if (m.matrix_world @ p.center).z < 1.03]
    pal.paint(m, 'trim', faces=edge)
    return join('Archmage_Mantle', [m])


def cuff(pal, side):
    rings = [(0, 0, 0.0, 0.15, 0.15), (0, 0, 0.1, 0.17, 0.17), (0, 0, 0.19, 0.22, 0.22), (0, 0, 0.23, 0.235, 0.235)]
    c = shell(f'cuff{side}', rings, segs=12)
    pal.paint(c, 'robe')
    pal.paint(c, 'trim', faces=[p.index for p in c.data.polygons if p.center.z > 0.18])
    c.rotation_euler = (0, math.radians(90 * side), 0)
    c.location = (0.55 * side, 0.0, 1.107)
    return join(f'Archmage_Cuff_{"L" if side > 0 else "R"}', [c])


def sash(pal):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=0.43, radius2=0.42, depth=0.12)
    me = bpy.data.meshes.new('sash')
    bm.to_mesh(me)
    bm.free()
    s = scene.link(bpy.data.objects.new('sash', me))
    s.location = (0, 0.0, 0.66)
    s.scale = (1, 0.92, 1)
    for p in me.polygons:
        p.use_smooth = True
    pal.paint(s, 'sash')
    parts = [s]
    for i, (dx, dz, rot) in enumerate(((0.16, 0.48, 8), (0.25, 0.5, -6))):
        t = shell(f'tail{i}', [(0, 0, -0.16, 0.05, 0.015), (0, 0, 0.0, 0.06, 0.018)], segs=6, cap_lo=True, cap_hi=True)
        t.location = (dx, -0.4, dz + 0.12)
        t.rotation_euler = (0, math.radians(rot), 0)
        pal.paint(t, 'sash')
        parts.append(t)
    pouch = ball('pouch', (-0.36, -0.22, 0.58), 0.09, scale=(0.9, 0.7, 1.0), sub=1)
    pal.paint(pouch, 'leather')
    parts.append(pouch)
    return join('Archmage_Sash', parts)


def staff(pal, kay_staff):
    """Along the axis of the pack's own staff (held in the right hand), its head where that one's is."""
    pts = [kay_staff.matrix_world @ v.co for v in kay_staff.data.vertices]
    ys = [p.y for p in pts]
    lo, hi = min(ys), max(ys)
    width = lambda sel: max((p.x for p in sel), default=0) - min((p.x for p in sel), default=0)
    head_end = lo if width([p for p in pts if p.y < lo + 0.3]) > width([p for p in pts if p.y > hi - 0.3]) else hi
    foot_end = hi if head_end == lo else lo
    d = -1 if head_end < foot_end else 1
    x, z = -0.883, 1.049
    n = 7
    # the shaft runs along y: build it along z, then turn it
    sh = shell('shaft', [(0.012 * math.sin(i * 1.3), 0, i / (n - 1) * abs(head_end - foot_end), 0.034 + 0.01 * (i % 2), 0.034 + 0.01 * (i % 2)) for i in range(n)],
               segs=7, cap_lo=True, cap_hi=True)
    pal.paint_ramp(sh, 'wood')
    sh.rotation_euler = (math.radians(-90 * d), 0, 0)
    sh.location = (x, foot_end, z)
    head = Vector((x, head_end, z))
    moon = bpy.data.meshes.new('moon')
    bm = bmesh.new()
    segs, arc = 14, math.radians(250)
    rows = []
    for k in range(segs + 1):
        a = -arc / 2 + arc * k / segs
        rr = 0.17
        tube = 0.035 * (0.35 + 0.65 * math.sin(math.pi * k / segs))
        c = Vector((math.sin(a) * rr, 0, -math.cos(a) * rr))
        ring = []
        for j in range(6):
            b = 2 * math.pi * j / 6
            nrm = Vector((math.sin(a), 0, -math.cos(a)))
            ring.append(bm.verts.new(c + nrm * math.cos(b) * tube + Vector((0, math.sin(b) * tube * 0.7, 0))))
        rows.append(ring)
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(6):
            bm.faces.new((r0[j], r0[(j + 1) % 6], r1[(j + 1) % 6], r1[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(moon)
    bm.free()
    mo = scene.link(bpy.data.objects.new('moon', moon))
    for p in moon.polygons:
        p.use_smooth = True
    # the crescent stands on the staff's head, opening away from the hand
    mo.rotation_euler = (math.radians(90 * d), 0, 0)
    mo.location = head + Vector((0, 0.17 * d, 0))
    pal.paint(mo, 'trim')
    orb = ball('orb', head + Vector((0, 0.17 * d, 0)), 0.09)
    pal.paint(orb, 'glow')
    return join('Archmage_Staff', [sh, mo, orb])


def closeup(body, name, out):
    """The face from the front, three-quarters and the side, close: does the beard grow from it?"""
    import importlib
    import numpy as np
    pvmod = importlib.import_module('mhb.preview')   # (the package's `preview` is the function)
    s = bpy.context.scene                            # lit and floored already by preview()
    s.render.resolution_x = s.render.resolution_y = 400
    tiles = []
    tmp = os.path.join(out, f'.{name}_close.png')
    for yaw in (0, 35, 75):
        c = pvmod._camera(Vector((0, 0, 1.45)), 2.4, yaw, 6)
        s.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(tmp, check_existing=False)
        tiles.append(np.array(img.pixels[:], dtype=np.float32).reshape(400, 400, 4))
        bpy.data.images.remove(img)
        bpy.data.objects.remove(c)
    grid = np.concatenate(tiles, axis=1)
    img = bpy.data.images.new(f'{name}_close', grid.shape[1], grid.shape[0])
    img.pixels = grid.ravel()
    img.filepath_raw = os.path.join(out, f'{name}_closeup.png')
    img.file_format = 'PNG'
    img.save()


def main():
    opts = scene.args()
    variant = opts['variant'] or 'blue'
    v = VARIANTS[variant]
    scene.reset()
    bpy.ops.import_scene.gltf(filepath=KAYKIT)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    kay_staff = bpy.data.objects.get('2H_Staff')
    pal = Palette(f'archmage_{variant}', {
        'robe': [v['robe'], v['robe'], v['deep']], 'deep': v['deep'], 'trim': v['trim'], 'sash': v['sash'],
        'beard': [v['beard'], v['beard'], '#b9b2a6'], 'glow': v['glow'], 'leather': '#6a4a2e', 'wood': ['#8a6a44', '#6b4a2e', '#4a3220'],
    })
    pieces = {
        'Archmage_Hat': (hat(pal), 'head'), 'Archmage_Beard': (beard(pal, bpy.data.objects['Mage_Head']), 'head'), 'Archmage_Mantle': (mantle(pal), 'chest'),
        'Archmage_Cuff_L': (cuff(pal, 1), 'lowerarm.l'), 'Archmage_Cuff_R': (cuff(pal, -1), 'lowerarm.r'),
        'Archmage_Sash': (sash(pal), 'hips'), 'Archmage_Staff': (staff(pal, kay_staff), 'handslot.r'),
        'Archmage_Robe': (robe(pal), None),
    }
    for name, (o, bone) in pieces.items():
        bind(o, arm, bone=bone, weights=None if bone else robe_weights)
        print('PIECE', name, len(o.data.polygons), 'faces', sum(len(p.vertices) - 2 for p in o.data.polygons), 'tris')
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name not in KEEP and o.name not in pieces:
            bpy.data.objects.remove(o)
    if opts['preview']:
        # worn by the KayKit mage: one object for the camera to frame
        worn = [bpy.data.objects[n] for n in KEEP] + [o for o, _ in pieces.values()]
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
        body = dup[0]
        poses = (('Idle_Rig', 0), ('Walking_A_Rig', 8), ('Spellcast_Shoot_Rig', 14), ('Spellcasting_Rig', 10), ('Running_A_Rig', 6))
        preview(arm, body, f'archmage_{variant}', opts['out'], size=360, samples=10, poses=poses)
        closeup(body, f'archmage_{variant}', opts['out'])


main()
