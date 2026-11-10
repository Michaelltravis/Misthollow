"""The warden look: a warrior's own silhouette, made as pieces for the equipment kit on the KayKit
rig (mhb/kit.py), worn over whatever armour the hero has. A warden is one of the lantern-bearers
who hold the road (docs/world/WORLD_SPINE.md): broad at the shoulder, furred against the mist,
the city's crimson at the belt.

  - a fur mantle round the shoulders (the chest)
  - a great layered pauldron with a spike on the shield arm, a smaller one on the sword arm
    (each rides its upper arm)
  - heavy bracers with a gold band (the forearms)
  - a broad war-belt with a round brass buckle (the hips)
  - a crimson tabard, front and back, gold at the hem, with the lantern's diamond on the front
    (weighted between the hips and the legs, so it sways with the stride)

Every colour is a column of the equipment kit's palette (tools/art3d/ramps.json).

    tools/art3d/blender/run.sh models/warden.py --preview --export
    -> out/warden_preview.png (worn by the pack's barbarian, the warrior's body) and
       out/equip/warden.glb + .json
"""
import math
import sys

from mhb import kit, scene

NAME = 'warden'
COLS = {'fur': 'fur_brown', 'tip': 'fur_grey', 'furdark': 'hide', 'steel': 'steel', 'dark': 'black_iron', 'gold': 'gold', 'cloth': 'crimson', 'deep': 'crimson~dark',
        'leather': 'leather_dark', 'brass': 'brass'}


def mantle(pal):
    """A pelt lying on the shoulders: a ragged, pointed hem (every other point of its edge hangs
    lower and further out), flat-shaded so each tuft catches the light by itself, paler at the tips."""
    SEGS = 20
    zig = lambda a, i: ((0.11 if round(a / (2 * math.pi / SEGS)) % 2 else -0.05) if i == 1 else
                        (0.04 if round(a / (2 * math.pi / SEGS)) % 2 == 0 else -0.02) if i == 2 else 0)
    rings = [(0, 0.03, 1.05, 0.45, 0.39), (0, 0.03, 0.99, 0.64, 0.54), (0, 0.03, 1.10, 0.63, 0.53),
             (0, 0.03, 1.20, 0.56, 0.48), (0, 0.03, 1.27, 0.41, 0.36)]
    m = kit.shell('mantle', rings, segs=SEGS, wave=zig, smooth=False)
    pal.paint(m, 'fur')
    pal.paint(m, 'tip', faces=[p.index for p in m.data.polygons if p.center.z < 1.045])
    pal.paint(m, 'furdark', faces=[p.index for p in m.data.polygons if p.center.z > 1.2])
    return kit.join('Warden_Mantle', [m])


def pauldron(pal, side, big):
    """Layered plates over the shoulder: side +1 the left (the shield arm, the great one), -1 the right."""
    s = 1.0 if big else 0.74
    cx, cz = 0.50 * side, 1.15
    parts = []
    # the lower plate, then the dome over it
    low = kit.shell('low', [(cx + 0.03 * side, 0, cz - 0.10 * s, 0.27 * s, 0.29 * s), (cx + 0.03 * side, 0, cz - 0.03 * s, 0.29 * s, 0.30 * s),
                            (cx + 0.02 * side, 0, cz + 0.03 * s, 0.24 * s, 0.26 * s)], segs=10, smooth=False)
    pal.paint(low, 'steel')
    pal.paint(low, 'gold', faces=[p.index for p in low.data.polygons if p.center.z < cz - 0.06 * s])
    dome = kit.shell('dome', [(cx, 0, cz + 0.0 * s, 0.25 * s, 0.27 * s), (cx, 0, cz + 0.09 * s, 0.24 * s, 0.25 * s), (cx, 0, cz + 0.17 * s, 0.17 * s, 0.18 * s),
                              (cx, 0, cz + 0.22 * s, 0.07 * s, 0.07 * s), (cx, 0, cz + 0.235 * s, 0, 0)], segs=10, smooth=True)
    pal.paint(dome, 'steel')
    pal.paint(dome, 'gold', faces=[p.index for p in dome.data.polygons if p.center.z < cz + 0.045 * s])
    parts += [low, dome]
    if big:
        spike = kit.shell('spike', [(0, 0, 0, 0.05, 0.05), (0, 0, 0.17, 0, 0)], segs=6, cap_lo=True, smooth=False)
        spike.location = (cx + 0.10 * side, 0, cz + 0.17)
        spike.rotation_euler = (0, math.radians(32 * side), 0)
        pal.paint(spike, 'dark')
        parts.append(spike)
        for dy in (-0.17, 0.17):                      # two rivets on the rim
            r = kit.ball(f'rivet{dy}', (cx + 0.22 * side, dy, cz - 0.02), 0.028, sub=1)
            pal.paint(r, 'gold')
            parts.append(r)
    return kit.join(f'Warden_Pauldron_{"L" if side > 0 else "R"}', parts)


def bracer(pal, side):
    rings = [(0, 0, 0.0, 0.135, 0.135), (0, 0, 0.05, 0.155, 0.155), (0, 0, 0.18, 0.165, 0.165), (0, 0, 0.22, 0.15, 0.15)]
    c = kit.shell(f'bracer{side}', rings, segs=10, smooth=False)
    pal.paint(c, 'steel')
    pal.paint(c, 'gold', faces=[p.index for p in c.data.polygons if 0.04 < p.center.z < 0.12])
    c.rotation_euler = (0, math.radians(90 * side), 0)
    c.location = (0.47 * side, 0.0, 1.107)
    return kit.join(f'Warden_Bracer_{"L" if side > 0 else "R"}', [c])


def belt(pal):
    b = kit.shell('belt', [(0, -0.01, 0.56, 0.445, 0.40), (0, -0.01, 0.58, 0.46, 0.415), (0, -0.01, 0.68, 0.46, 0.415), (0, -0.01, 0.70, 0.445, 0.40)],
                  segs=16, smooth=False)
    pal.paint(b, 'leather')
    # the buckle: a round brass boss on the front, a dark stud at its heart
    boss = kit.shell('boss', [(0, 0, 0, 0.11, 0.11), (0, 0, 0.03, 0.10, 0.10), (0, 0, 0.05, 0.05, 0.05), (0, 0, 0.055, 0, 0)], segs=10, cap_lo=True, smooth=False)
    boss.rotation_euler = (math.radians(90), 0, 0)
    boss.location = (0, -0.415, 0.63)
    pal.paint(boss, 'brass')
    stud = kit.ball('stud', (0, -0.475, 0.63), 0.03, sub=1)
    pal.paint(stud, 'dark')
    return kit.join('Warden_Belt', [b, boss, stud])


TAB_TOP, TAB_BOT = 0.62, 0.17


def panel(name, y, width, bulge):
    """A hanging cloth: a grid of quads from the belt down, a little wider and further out at the hem."""
    import bpy
    import bmesh
    bm = bmesh.new()
    rows, cols = 5, 4
    grid = []
    for r in range(rows + 1):
        t = r / rows
        z = TAB_TOP + (TAB_BOT - TAB_TOP) * t
        w = width * (1 + 0.18 * t)
        row = []
        for c in range(cols + 1):
            u = c / cols - 0.5
            row.append(bm.verts.new((u * w, y + bulge * (0.35 + 0.65 * t) * (1 - (2 * u) ** 2 * 0.5), z)))
        grid.append(row)
    for r in range(rows):
        for c in range(cols):
            bm.faces.new((grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]))
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.018)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    return scene.link(bpy.data.objects.new(name, me))


def tabard(pal):
    front = panel('front', -0.385, 0.34, -0.05)
    back = panel('back', 0.37, 0.38, 0.05)
    for o in (front, back):
        pal.paint(o, 'cloth')
        pal.paint(o, 'gold', faces=[p.index for p in o.data.polygons if p.center.z < TAB_BOT + 0.07])
    pal.paint(back, 'deep', faces=[p.index for p in back.data.polygons if p.center.z >= TAB_BOT + 0.07])
    # the lantern's sign on the front: a gold diamond
    sign = kit.box('sign', (0, -0.455, 0.42), (0.11, 0.02, 0.11), rot=(0, math.radians(45), 0))
    pal.paint(sign, 'gold')
    return kit.join('Warden_Tabard', [front, back, sign])


def tabard_weights(co):
    """The belt's edge moves with the hips; the hem is shared with the legs, more to the nearer one."""
    t = max(0.0, min(1.0, (TAB_TOP - co.z) / (TAB_TOP - TAB_BOT)))
    leg = 0.55 * t * t
    left = 0.5 + max(-0.5, min(0.5, co.x / 0.3))
    return {'hips': 1 - leg, 'upperleg.l': leg * left, 'upperleg.r': leg * (1 - left)}


def main():
    opts = scene.args()
    arm = kit.load_hero('Barbarian')
    pal = kit.palette(NAME, COLS)
    pieces = {
        'Warden_Mantle': (mantle(pal), 'chest'),
        'Warden_Pauldron_L': (pauldron(pal, 1, True), 'upperarm.l'), 'Warden_Pauldron_R': (pauldron(pal, -1, False), 'upperarm.r'),
        'Warden_Bracer_L': (bracer(pal, 1), 'lowerarm.l'), 'Warden_Bracer_R': (bracer(pal, -1), 'lowerarm.r'),
        'Warden_Belt': (belt(pal), 'hips'), 'Warden_Tabard': (tabard(pal), tabard_weights),
    }
    kit.bind_all(pieces, arm)
    if '--export' in sys.argv:
        kit.export(pieces, arm, pal, NAME, COLS, opts['out'])
    if opts['preview']:
        kit.preview_worn(arm, kit.BODY['Barbarian'], pieces, NAME, opts['out'])


main()
