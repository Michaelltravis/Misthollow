"""The world's great villains on bodies of their own (docs/world/WORLD_SPINE.md: each region's villain
"made a different bargain with the mist"). With models/drowned_king.py (Nerathis). Variants:

  ostragoth   Ostragoth, the vampire lord (the Marches): tall and gaunt, bone-pale, a high collar
              lined in blood red, a black cape to the floor, a black glass staff with a red heart
  war         War (the Castle of the Apocalypse): a giant in dark red plate, a horned helm, a
              greatsword held upright, eyes like coals
  famine      Famine: a starved giant in a grey cowl, ribs showing, a pair of scales in one hand
  pestilence  Pestilence: hunched under a rotten green shroud, boils that glow, a censer of plague
  death       Death: a black robe and hood, a skull inside it with cold lights for eyes, a scythe

    tools/art3d/blender/run.sh models/villains.py --variant ostragoth --preview
    -> out/<variant>.glb, .json, _preview.png; then `node build.mjs blend <variant>`
"""
import math

import mhb
from mhb import Skel, Palette, part, finish_body, Clips, gaits
from mhb.forms import humanoid, humanoid_clips

mhb.reset()
opt = mhb.args()
V = opt['variant'] or 'ostragoth'
R = math.radians

BUILD = {
    'ostragoth': dict(height=2.6, girth=0.86, shoulders=1.22, arms=1.12, legs=1.08, hunch=0.06, head=1.3, belly=0.8),
    'war': dict(height=3.1, girth=1.22, shoulders=1.45, arms=1.1, legs=1.0, hunch=0.08, head=1.25, belly=1.0),
    'famine': dict(height=3.1, girth=0.7, shoulders=1.15, arms=1.3, legs=1.1, hunch=0.3, head=1.3, belly=0.6),
    'pestilence': dict(height=2.8, girth=1.05, shoulders=1.1, arms=1.2, legs=0.9, hunch=0.42, head=1.3, belly=1.25),
    'death': dict(height=3.2, girth=0.82, shoulders=1.2, arms=1.2, legs=1.1, hunch=0.1, head=1.3, belly=0.8),
}
P = BUILD[V]
COLOURS = {
    'ostragoth': {'flesh': ['#e8e2dc', '#c4bcb8', '#948c8c'], 'cloth': ['#2a2430', '#1a1620', '#0e0c12'], 'trim': ['#b8283a', '#8a1828', '#56101a'],
                  'eye': '#ff4a3a', 'dark': '#120e14', 'metal': ['#d8c070', '#a88c40', '#6e5a24'], 'bone': '#f2ecde', 'glass': ['#3a3444', '#201c28', '#0e0c14']},
    'war': {'flesh': ['#b84a3a', '#8a2a22', '#561814'], 'cloth': ['#a02a24', '#701a18', '#44100e'], 'trim': ['#e0b050', '#b08030', '#70501c'],
            'eye': '#ffb040', 'dark': '#1a1010', 'metal': ['#d0d4d8', '#9098a0', '#5a6068'], 'bone': '#e8dcc0', 'glass': ['#5a4a44', '#3a2e2a', '#201816']},
    'famine': {'flesh': ['#c8c2a0', '#9c9678', '#6c6850'], 'cloth': ['#7a7668', '#56544a', '#36342e'], 'trim': ['#c8b070', '#988448', '#645828'],
               'eye': '#f0f0a0', 'dark': '#16140e', 'metal': ['#b8a878', '#8a7c50', '#5a5030'], 'bone': '#e8e0c8', 'glass': ['#5a5648', '#3a3830', '#20201a']},
    'pestilence': {'flesh': ['#9cb078', '#6e8450', '#465a32'], 'cloth': ['#5a6a3a', '#3c4a26', '#242e16'], 'trim': ['#b8c060', '#8a9038', '#5a601e'],
                   'eye': '#c8ff60', 'dark': '#12160c', 'metal': ['#a89860', '#7a6c3c', '#4e4422'], 'bone': '#d8d8b0', 'glass': ['#4a5a30', '#2e3a1c', '#1a220e']},
    'death': {'flesh': ['#3a3840', '#24222a', '#121116'], 'cloth': ['#2a2830', '#18161c', '#0a090c'], 'trim': ['#8a8a98', '#5e5e6c', '#3a3a44'],
              'eye': '#a8e8ff', 'dark': '#08080a', 'metal': ['#d0d4dc', '#9aa0aa', '#62666e'], 'bone': '#eeeadc', 'glass': ['#3a3a44', '#22222a', '#101014']},
}
pal = Palette(V, COLOURS[V])

s = Skel(V)
L = humanoid(s, **P)
H = P['height']
body = s.hull(subdiv=1, branch_smoothing=0.4, smooth=True)
# (Ostragoth is dressed: black from the neck down, his pallor in his face alone)
pal.paint_ramp(body, 'cloth' if V == 'ostragoth' else 'flesh')
arm = s.armature()
parts = []


def add(p, key, bone):
    pal.paint(p, key)
    parts.append((p, bone))


hz, hy = L['head_z'], L['head_y']
rh = 0.075 * H * P['head']
cz = s.co('chest').z
hip = L['hip_z']
g = P['girth']
sw = 0.17 * H * P['shoulders'] * g
hooded = V in ('famine', 'pestilence', 'death')

# ---- the head: a skull with weight to it, the eyes lit; under a hood for three of them
skin = 'bone' if V == 'death' else 'flesh'
add(part('sphere', 'skull', (0, hy, hz), (1.02 * rh, 1.12 * rh, 1.2 * rh), segments=12), skin, 'head')
add(part('sphere', 'jaw', (0, hy - rh * 0.45, hz - 0.8 * rh), (0.66 * rh, 0.66 * rh, 0.46 * rh), segments=8), skin, 'head')
if V != 'death':
    add(part('sphere', 'brow', (0, hy - rh * 0.72, hz + 0.34 * rh), (0.8 * rh, 0.26 * rh, 0.16 * rh), segments=8), skin, 'head')
for side, x in (('L', 1), ('R', -1)):
    add(part('sphere', f'socket.{side}', (0.36 * rh * x, hy - rh * 0.92, hz + 0.1 * rh), 0.21 * rh, segments=6), 'dark', 'head')
    add(part('sphere', f'eye.{side}', (0.36 * rh * x, hy - rh * 1.02, hz + 0.1 * rh), 0.11 * rh, segments=6), 'eye', 'head')
if hooded:
    # (set back on the head, so the face looks out of it)
    add(part('sphere', 'hood', (0, hy + 0.55 * rh, hz + 0.2 * rh), (1.25 * rh, 1.2 * rh, 1.4 * rh), segments=12), 'cloth', 'head')
    add(part('cone', 'hoodpeak', (0, hy + 0.9 * rh, hz + 1.2 * rh), (0.5 * rh, 0.5 * rh, 0.6 * rh), rot=(R(-50), 0, 0), segments=6), 'cloth', 'head')
    add(part('cyl', 'cowl', (0, hy * 0.5, cz + 0.1 * H), (sw * 0.95, 0.1 * H * g, 0.04 * H), segments=10), 'cloth', 'chest')


def skirt(n, long, key, flare=1.0, base=None):
    """A ring of cloth tongues hanging from the hips: a robe's ragged hem."""
    z0 = (hip if base is None else base) + 0.03 * H
    for i in range(n):
        a = 2 * math.pi * i / n
        ln = long * (0.86 + 0.14 * (i % 3) / 2) * H
        add(part('cone', f'skirt{i}', (math.cos(a) * 0.105 * H * g * flare, math.sin(a) * 0.095 * H * g * flare, z0 - ln / 2),
                 (0.045 * H * flare, 0.034 * H * flare, ln / 2), rot=(R(180), 0, 0), segments=4), key, 'hips')


def cape(n, long, key, y=0.09):
    for i in range(n):
        x = (i - (n - 1) / 2) * 0.062
        ln = long * (1 - 0.06 * (i % 2)) * H
        add(part('cone', f'cape{i}', (x * H, y * H * g, cz + 0.03 * H - ln / 2), (0.04 * H, 0.016 * H, ln / 2), rot=(R(180 + 5), 0, 0), segments=4),
            key, 'chest' if i % 2 else 'spine')


hand_r, hand_l = s.co('arm2.R'), s.co('arm2.L')

if V == 'ostragoth':
    # hair swept back to a point, a widow's peak; fangs; the high collar open at the front
    add(part('cone', 'hair', (0, hy + 0.5 * rh, hz + 0.75 * rh), (0.95 * rh, 0.8 * rh, 0.9 * rh), rot=(R(-58), 0, 0), segments=6), 'cloth', 'head')
    add(part('cone', 'peak', (0, hy - 0.85 * rh, hz + 0.95 * rh), (0.22 * rh, 0.12 * rh, 0.3 * rh), rot=(R(180), 0, 0), segments=4), 'cloth', 'head')
    for x in (-0.16, 0.16):
        add(part('cone', f'fang{x}', (x * rh, hy - rh * 1.0, hz - 0.62 * rh), (0.05 * rh, 0.05 * rh, 0.14 * rh), rot=(R(180), 0, 0), segments=4), 'bone', 'head')
    for i in range(7):
        a = R(20 + 140 * i / 6)                       # round the back of the neck, from shoulder to shoulder
        tall = (0.17 + 0.05 * math.sin(math.pi * i / 6)) * H
        add(part('cone', f'collar{i}', (math.cos(a) * sw * 0.72, 0.02 * H + math.sin(a) * 0.085 * H, cz + 0.1 * H + tall / 2),
                 (0.05 * H, 0.016 * H, tall / 2), rot=(R(-14) * math.sin(a), R(14) * math.cos(a), a - R(90)), segments=4), 'trim', 'chest')
    cape(7, 0.62, 'cloth')
    add(part('sphere', 'brooch', (0, -0.115 * H * g, cz + 0.05 * H), 0.024 * H, segments=6), 'eye', 'chest')
    add(part('cyl', 'sash', (0, 0, hip + 0.03 * H), (0.118 * H * g, 0.105 * H * g, 0.022 * H), segments=10), 'trim', 'hips')
    skirt(8, 0.26, 'cloth')
    # the black glass staff, a red heart held in its claw
    hx, hyy = hand_r.x, hand_r.y - 0.02 * H
    add(part('cyl', 'staff', (hx, hyy, hand_r.z + 0.16 * H), (0.013 * H, 0.013 * H, 0.5 * H), segments=6), 'glass', 'arm2.R')
    top = hand_r.z + 0.68 * H
    add(part('sphere', 'heart', (hx, hyy, top + 0.04 * H), 0.045 * H, segments=8), 'eye', 'arm2.R')
    for i in range(3):
        a = 2 * math.pi * i / 3
        add(part('cone', f'claw{i}', (hx + math.cos(a) * 0.04 * H, hyy + math.sin(a) * 0.04 * H, top + 0.03 * H), (0.012 * H, 0.012 * H, 0.06 * H),
                 rot=(R(-18) * math.sin(a), R(18) * math.cos(a), 0), segments=4), 'glass', 'arm2.R')

if V == 'war':
    # a horned great helm, a breastplate, pauldrons with spikes, a tattered cape, the greatsword
    add(part('cyl', 'helm', (0, hy, hz + 0.25 * rh), (1.12 * rh, 1.2 * rh, 0.95 * rh), segments=10), 'metal', 'head')
    add(part('cube', 'visor', (0, hy - 1.15 * rh, hz + 0.1 * rh), (0.7 * rh, 0.06 * rh, 0.12 * rh)), 'dark', 'head')
    for side, x in (('L', 1), ('R', -1)):
        add(part('cone', f'horn.{side}', (1.25 * rh * x, hy, hz + 1.0 * rh), (0.2 * rh, 0.2 * rh, 0.85 * rh), rot=(0, R(38 * x), 0), segments=6), 'bone', 'head')
        add(part('sphere', f'pauldron.{side}', (sw * 1.05 * x, 0, cz + 0.05 * H), (0.1 * H, 0.09 * H, 0.07 * H), segments=10), 'metal', 'chest')
        add(part('cone', f'spike.{side}', (sw * 1.12 * x, 0, cz + 0.13 * H), (0.02 * H, 0.02 * H, 0.06 * H), rot=(0, R(25 * x), 0), segments=5), 'trim', 'chest')
    add(part('sphere', 'breast', (0, -0.1 * H * g, cz), (0.14 * H * g, 0.055 * H, 0.11 * H), segments=10), 'metal', 'chest')
    add(part('cube', 'crest', (0, -0.155 * H * g, cz + 0.01 * H), (0.02 * H, 0.008 * H, 0.07 * H)), 'trim', 'chest')
    cape(6, 0.5, 'cloth')
    add(part('cyl', 'belt', (0, 0, hip + 0.03 * H), (0.12 * H * g, 0.108 * H * g, 0.026 * H), segments=10), 'trim', 'hips')
    skirt(8, 0.2, 'cloth')
    hx, hyy = hand_r.x, hand_r.y - 0.02 * H
    add(part('cube', 'blade', (hx, hyy, hand_r.z + 0.5 * H), (0.035 * H, 0.008 * H, 0.42 * H)), 'metal', 'arm2.R')
    add(part('cone', 'point', (hx, hyy, hand_r.z + 0.96 * H), (0.035 * H, 0.008 * H, 0.05 * H), segments=4), 'metal', 'arm2.R')
    add(part('cube', 'guard', (hx, hyy, hand_r.z + 0.07 * H), (0.1 * H, 0.014 * H, 0.014 * H)), 'trim', 'arm2.R')
    add(part('cyl', 'grip', (hx, hyy, hand_r.z - 0.02 * H), (0.014 * H, 0.014 * H, 0.09 * H), segments=6), 'dark', 'arm2.R')

if V == 'famine':
    # ribs across a hollow chest, a rope belt, a long ragged robe, the scales held out
    for i in range(4):
        add(part('cyl', f'rib{i}', (0, -0.085 * H * g, cz + (0.035 - 0.036 * i) * H), (0.1 * H * g, 0.012 * H, 0.008 * H), segments=6), 'bone', 'chest')
    add(part('cyl', 'rope', (0, 0, hip + 0.03 * H), (0.11 * H * g, 0.1 * H * g, 0.014 * H), segments=10), 'trim', 'hips')
    skirt(10, 0.34, 'cloth', flare=1.1)
    cape(5, 0.5, 'cloth')
    hx, hyy, hzz = hand_l.x, hand_l.y - 0.03 * H, hand_l.z
    add(part('cyl', 'post', (hx, hyy, hzz + 0.02 * H), (0.008 * H, 0.008 * H, 0.1 * H), segments=5), 'metal', 'arm2.L')
    add(part('cube', 'beam', (hx, hyy, hzz + 0.11 * H), (0.11 * H, 0.008 * H, 0.008 * H)), 'metal', 'arm2.L')
    for dx in (-0.1, 0.1):
        add(part('cyl', f'chain{dx}', (hx + dx * H, hyy, hzz + 0.05 * H), (0.004 * H, 0.004 * H, 0.06 * H), segments=4), 'metal', 'arm2.L')
        add(part('cone', f'pan{dx}', (hx + dx * H, hyy, hzz - 0.02 * H), (0.04 * H, 0.04 * H, 0.016 * H), rot=(R(180), 0, 0), segments=8), 'trim', 'arm2.L')

if V == 'pestilence':
    # boils that glow on the shoulders and back, a rotten shroud, a censer of plague on a chain
    for i, (x, y, z, r) in enumerate(((0.9, 0.1, 0.07, 0.035), (-0.85, 0.2, 0.08, 0.03), (0.4, 0.75, 0.04, 0.04), (-0.3, 0.8, 0.0, 0.03), (0.0, 0.95, -0.06, 0.035))):
        add(part('sphere', f'boil{i}', (sw * x, y * 0.1 * H * g, cz + z * H), r * H, segments=6), 'eye', 'chest')
    skirt(11, 0.36, 'cloth', flare=1.2)
    cape(6, 0.46, 'cloth')
    add(part('cyl', 'rope', (0, 0, hip + 0.03 * H), (0.125 * H * g, 0.11 * H * g, 0.016 * H), segments=10), 'trim', 'hips')
    hx, hyy, hzz = hand_r.x, hand_r.y - 0.03 * H, hand_r.z
    add(part('cyl', 'chain', (hx, hyy, hzz - 0.07 * H), (0.005 * H, 0.005 * H, 0.08 * H), segments=4), 'metal', 'arm2.R')
    add(part('sphere', 'censer', (hx, hyy, hzz - 0.18 * H), 0.045 * H, segments=8), 'metal', 'arm2.R')
    add(part('sphere', 'fume', (hx, hyy, hzz - 0.15 * H), 0.03 * H, segments=6), 'eye', 'arm2.R')

if V == 'death':
    # the robe to the floor, the long sleeves, the scythe
    skirt(12, 0.44, 'cloth', flare=1.15)
    cape(7, 0.6, 'cloth')
    add(part('cyl', 'cord', (0, 0, hip + 0.03 * H), (0.115 * H * g, 0.102 * H * g, 0.012 * H), segments=10), 'trim', 'hips')
    for side, x in (('L', 1), ('R', -1)):
        hd = s.co(f'arm2.{side}')
        add(part('cone', f'sleeve.{side}', (hd.x, hd.y, hd.z + 0.05 * H), (0.05 * H, 0.05 * H, 0.1 * H), segments=6), 'cloth', f'arm2.{side}')
    hx, hyy = hand_r.x, hand_r.y - 0.02 * H
    add(part('cyl', 'snath', (hx, hyy, hand_r.z + 0.22 * H), (0.012 * H, 0.012 * H, 0.6 * H), segments=6), 'glass', 'arm2.R')
    top = hand_r.z + 0.8 * H
    for i in range(5):                                # the blade: a curve of five tapering pieces, out and down
        a = R(8 + 20 * i)
        add(part('cube', f'blade{i}', (hx + (0.06 + 0.1 * i) * H * math.cos(a) * 0.9, hyy, top - (0.016 * i * i) * H),
                 ((0.062 - 0.006 * i) * H, 0.008 * H, (0.05 - 0.008 * i) * H), rot=(0, R(14 * i), 0)), 'metal', 'arm2.R')

body = finish_body(body, arm, parts, budget=7000)

c = Clips(arm)
humanoid_clips(c, gaits, frames_walk=40, swing=16, arm=14, heavy=1.3 if V in ('war', 'death') else 1.15, height=H)

mhb.export(arm, body, V, opt['out'], kind='boss', clips=c.names, meta={'for': {
    'ostragoth': 'Ostragoth, the vampire lord', 'war': 'War', 'famine': 'Famine', 'pestilence': 'Pestilence', 'death': 'Death'}[V]
    + ' (its own colours: not tinted)'})
if opt['preview']:
    mhb.preview(arm, body, V, opt['out'], poses=(('Idle', 0), ('Walk', 9), ('Bite_Front', 9), ('Bite_InPlace', 14), ('Death', 999)))
