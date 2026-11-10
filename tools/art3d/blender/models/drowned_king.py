"""Nerathis, the Drowned King (the Sunken Ruins of Atal'narath; docs/world/WORLD_SPINE.md: the Sunder
Sea's great villain, who "kept his name by drowning with it"). A tall, gaunt king three days under:
grey-green drowned flesh, a crown of coral grown into his skull, a beard and a ragged train of
kelp, barnacled bronze at the shoulders and breast, a trident in his right hand, and eyes that
burn cold under the brow.

    tools/art3d/blender/run.sh models/drowned_king.py --preview
    -> out/drowned_king.glb, .json, _preview.png; then `node build.mjs blend drowned_king`
"""
import math

import mhb
from mhb import Skel, Palette, part, finish_body, Clips, gaits
from mhb.forms import humanoid, humanoid_clips

mhb.reset()
opt = mhb.args()
NAME = 'drowned_king'
P = dict(height=2.9, girth=1.0, shoulders=1.32, arms=1.15, legs=1.0, hunch=0.14, head=1.4, belly=0.82)
pal = Palette(NAME, {
    'flesh': ['#a8c4b8', '#7a9a90', '#4e6c68'], 'kelp': ['#4a6a3a', '#30502a', '#1c3420'], 'coral': ['#f0a088', '#d06a58', '#963c38'],
    'bronze': ['#b8a060', '#86763e', '#5a5028'], 'barnacle': '#d8d4c0', 'eye': '#b4fff0', 'dark': '#16201e', 'gold': ['#f0d880', '#c8a850', '#8a7030'],
    'pearl': '#f4f0e4',
})
R = math.radians

s = Skel(NAME)
L = humanoid(s, **P)
H = P['height']
body = s.hull(subdiv=1, branch_smoothing=0.4, smooth=True)
pal.paint_ramp(body, 'flesh')
arm = s.armature()

parts = []


def add(p, key, bone):
    pal.paint(p, key)
    parts.append((p, bone))


hz, hy = L['head_z'], L['head_y']
rh = 0.075 * H * P['head']
# the skull, long and hollow-cheeked; a heavy brow; the eyes, lit
add(part('sphere', 'skull', (0, hy, hz), (1.05 * rh, 1.15 * rh, 1.25 * rh), segments=12), 'flesh', 'head')
add(part('sphere', 'brow', (0, hy - rh * 0.72, hz + 0.34 * rh), (0.8 * rh, 0.26 * rh, 0.16 * rh), segments=8), 'flesh', 'head')
add(part('sphere', 'jaw', (0, hy - rh * 0.45, hz - 0.8 * rh), (0.7 * rh, 0.7 * rh, 0.5 * rh), segments=8), 'flesh', 'head')
for side, x in (('L', 1), ('R', -1)):
    add(part('sphere', f'socket.{side}', (0.36 * rh * x, hy - rh * 0.92, hz + 0.1 * rh), 0.2 * rh, segments=6), 'dark', 'head')
    add(part('sphere', f'eye.{side}', (0.36 * rh * x, hy - rh * 1.02, hz + 0.1 * rh), 0.11 * rh, segments=6), 'eye', 'head')
# the crown: seven tines of coral grown out of the skull, the tallest in front, a gold band under them
add(part('cyl', 'band', (0, hy, hz + 0.95 * rh), (0.98 * rh, 1.05 * rh, 0.14 * rh), segments=12), 'gold', 'head')
for i in range(7):
    a = R(-90 + (i - 3) * 44)
    tall = (1.35 - 0.16 * abs(i - 3)) * rh
    add(part('cone', f'tine{i}', (math.cos(a) * 0.86 * rh, hy + math.sin(a) * 0.92 * rh, hz + 1.05 * rh + tall / 2),
             (0.15 * rh, 0.15 * rh, tall / 2), rot=(R(8) * math.sin(a), R(-8) * math.cos(a), 0), segments=5), 'coral', 'head')
add(part('sphere', 'crownpearl', (0, hy - 1.05 * rh, hz + 0.97 * rh), 0.14 * rh, segments=6), 'pearl', 'head')
# a beard of kelp: long fronds from the jaw down over the breast
for i, x in enumerate((-0.42, -0.2, 0.0, 0.2, 0.42)):
    long = (1.9 - 0.5 * abs(x) / 0.42) * rh
    add(part('cone', f'beard{i}', (x * rh, hy - rh * (0.8 - 0.25 * abs(x)), hz - 0.95 * rh - long / 2), (0.16 * rh, 0.1 * rh, long / 2),
             rot=(R(180 - 8), 0, R(x * 20)), segments=4), 'kelp', 'head')

cz = s.co('chest').z
sw = 0.17 * H * P['shoulders'] * P['girth']
# barnacled bronze: a breastplate, and a pauldron on each shoulder crusted with shell
add(part('sphere', 'breast', (0, -0.1 * H * P['girth'], cz - 0.01 * H), (0.13 * H * P['girth'], 0.05 * H, 0.1 * H), segments=10), 'bronze', 'chest')
add(part('sphere', 'gorgetgem', (0, -0.145 * H * P['girth'], cz + 0.02 * H), 0.022 * H, segments=6), 'eye', 'chest')
for side, x in (('L', 1), ('R', -1)):
    add(part('sphere', f'pauldron.{side}', (sw * 1.02 * x, -0.005 * H, cz + 0.045 * H), (0.085 * H, 0.08 * H, 0.06 * H), segments=10), 'bronze', 'chest')
    for j, (dx, dy, dz) in enumerate(((0.03, -0.04, 0.045), (-0.02, 0.03, 0.05), (0.05, 0.02, 0.02))):
        add(part('cone', f'barn{j}.{side}', ((sw * 1.02 + dx * H) * x, dy * H, cz + 0.045 * H + dz * H), (0.016 * H, 0.016 * H, 0.014 * H), segments=5), 'barnacle', 'chest')
# a train of kelp from the shoulders down the back, and a ragged skirt of it at the hips
for i, x in enumerate((-0.11, -0.04, 0.04, 0.11)):
    long = (0.36 - 0.04 * (i % 2)) * H
    add(part('cone', f'train{i}', (x * H, 0.09 * H * P['girth'], cz - long / 2 + 0.02 * H), (0.035 * H, 0.014 * H, long / 2), rot=(R(180 + 6), 0, 0), segments=4),
        'kelp', 'chest' if i % 2 else 'spine')
hip = L['hip_z']
for i in range(9):
    a = 2 * math.pi * i / 9
    long = (0.2 + 0.05 * (i % 3)) * H
    add(part('cone', f'skirt{i}', (math.cos(a) * 0.105 * H * P['girth'], math.sin(a) * 0.095 * H * P['girth'], hip - long / 2 + 0.03 * H),
             (0.04 * H, 0.03 * H, long / 2), rot=(R(180), 0, 0), segments=4), 'kelp', 'hips')
add(part('cyl', 'girdle', (0, 0, hip + 0.02 * H), (0.118 * H * P['girth'], 0.105 * H * P['girth'], 0.022 * H), segments=10), 'gold', 'hips')

# the trident, held upright in his right hand: a long haft, three tines, a barb on each outer one
hand = s.co('arm2.R')
hx, hyy = hand.x, hand.y - 0.02 * H
add(part('cyl', 'haft', (hx, hyy, hand.z + 0.2 * H), (0.014 * H, 0.014 * H, 0.52 * H), segments=6), 'bronze', 'arm2.R')
top = hand.z + 0.72 * H
add(part('cube', 'yoke', (hx, hyy, top), (0.1 * H, 0.014 * H, 0.014 * H)), 'bronze', 'arm2.R')
for i, dx in enumerate((-0.09, 0.0, 0.09)):
    tall = (0.2 if dx == 0 else 0.15) * H
    add(part('cone', f'prong{i}', (hx + dx * H, hyy, top + tall / 2), (0.016 * H, 0.016 * H, tall / 2), segments=5), 'gold', 'arm2.R')
add(part('sphere', 'buttgem', (hx, hyy, hand.z - 0.33 * H), 0.024 * H, segments=6), 'eye', 'arm2.R')

body = finish_body(body, arm, parts, budget=7000)

c = Clips(arm)
humanoid_clips(c, gaits, frames_walk=40, swing=16, arm=14, heavy=1.3, height=H)

mhb.export(arm, body, NAME, opt['out'], kind='boss', clips=c.names, meta={'for': 'Nerathis, the Drowned King (its own colours: not tinted)'})
if opt['preview']:
    mhb.preview(arm, body, NAME, opt['out'], poses=(('Idle', 0), ('Walk', 9), ('Bite_Front', 9), ('Bite_InPlace', 14), ('Death', 999)))
