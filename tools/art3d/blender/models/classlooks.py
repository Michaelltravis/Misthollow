"""A look of their own for seven classes, as pieces for the equipment kit on the KayKit rig
(mhb/kit.py), worn over whatever the hero has on. With the mage's archmage (models/archmage.py) and
the warrior's warden (models/warden.py) every class but none has one:

    templar      a paladin   a halo behind the head, winged pauldrons, a gorget, a white tabard with the sun
    hierophant   a cleric    a gold-ended stole, a sunburst behind the head, wide cuffs, a censer
    footpad      a thief     a red scarf with tails, a bandolier of knives, belt pouches, arm wraps
    nightblade   an assassin a pointed black mantle, crossed blades on the back, a red sash, arm blades
    wayfinder    a ranger    a mantle of leaves, feathers at the shoulder, a bedroll, fur-trimmed bracers
    troubadour   a bard      a white ruff, a half-cape, a lute on the back, frilled cuffs, a tasselled sash
    gravecaller  a necromancer  a collar of bone spikes, a skull on the shoulder, a ragged shroud, a chain

Each look is a function returning (the pack's hero it is modelled on, its colours, its pieces); the
names of its pieces are what world3d/gearlook.js LOOKS lists. Every colour is a column of the kit's
palette (tools/art3d/ramps.json).

    tools/art3d/blender/run.sh models/classlooks.py --look templar --preview --export
    tools/art3d/blender/run.sh models/classlooks.py --all --preview --export
    -> out/<look>_preview.png and out/equip/<look>.glb + .json, one pair a look
"""
import math
import sys

from mhb import kit, scene

R = math.radians


def cuff(pal, name, side, key, trim, flare=0.235, zig=False):
    """A sleeve end on the forearm: side +1 the left arm."""
    wave = (lambda a, i: (0.1 if round(a / (2 * math.pi / 12)) % 2 else -0.04) if i == 3 else 0) if zig else None
    c = kit.shell(f'cuff{side}', [(0, 0, 0.0, 0.15, 0.15), (0, 0, 0.1, 0.17, 0.17), (0, 0, 0.19, flare * 0.94, flare * 0.94), (0, 0, 0.23, flare, flare)],
                  segs=12, smooth=False, wave=wave)
    pal.paint(c, key)
    pal.paint(c, trim, faces=[p.index for p in c.data.polygons if p.center.z > 0.18])
    c.rotation_euler = (0, R(90 * side), 0)
    c.location = (0.55 * side, 0.0, 1.107)
    return kit.join(name, [c])


def bracer(pal, name, side, key, band):
    c = kit.shell(f'bracer{side}', [(0, 0, 0.0, 0.135, 0.135), (0, 0, 0.05, 0.155, 0.155), (0, 0, 0.18, 0.165, 0.165), (0, 0, 0.22, 0.15, 0.15)],
                  segs=10, smooth=False)
    pal.paint(c, key)
    pal.paint(c, band, faces=[p.index for p in c.data.polygons if 0.04 < p.center.z < 0.12])
    c.rotation_euler = (0, R(90 * side), 0)
    c.location = (0.47 * side, 0.0, 1.107)
    return [c]


def belt(pal, key, z=0.63, h=0.11):
    b = kit.shell('belt', [(0, -0.01, z - h / 2 - 0.01, 0.445, 0.40), (0, -0.01, z - h / 2, 0.46, 0.415), (0, -0.01, z + h / 2, 0.46, 0.415),
                           (0, -0.01, z + h / 2 + 0.01, 0.445, 0.40)], segs=16, smooth=False)
    pal.paint(b, key)
    return b


def dome(pal, side, key, rim, s=0.9):
    """A rounded shoulder plate over the upper arm."""
    cx, cz = 0.50 * side, 1.15
    d = kit.shell('dome', [(cx, 0, cz - 0.08 * s, 0.27 * s, 0.29 * s), (cx, 0, cz, 0.27 * s, 0.29 * s), (cx, 0, cz + 0.10 * s, 0.24 * s, 0.25 * s),
                           (cx, 0, cz + 0.18 * s, 0.15 * s, 0.16 * s), (cx, 0, cz + 0.22 * s, 0, 0)], segs=10, smooth=True)
    pal.paint(d, key)
    pal.paint(d, rim, faces=[p.index for p in d.data.polygons if p.center.z < cz - 0.03 * s])
    return d


# ---------------------------------------------------------------- templar (a paladin)
def templar():
    cols = {'steel': 'steel', 'gold': 'gold', 'white': 'white', 'shade': 'white~dark', 'halo': 'holy~glow', 'blue': 'royal_blue'}

    def build(pal):
        halo = kit.ring('halo', (0, 0.5, 1.84), 0.5, 0.035, segs=18, sides=5)
        pal.paint(halo, 'halo')
        pieces = {'Templar_Halo': (kit.join('Templar_Halo', [halo]), 'head')}
        for side, tag in ((1, 'L'), (-1, 'R')):
            parts = [dome(pal, side, 'steel', 'gold')]
            for i, (lift, lean) in enumerate(((0.30, 20), (0.24, 42), (0.17, 64))):      # three feathers, fanned
                f = kit.fin(f'wing{i}', [(-0.045, 0), (0.045, 0), (0.03, lift), (0, lift + 0.05), (-0.03, lift)],
                            at=(0.56 * side, 0.07, 1.28), thickness=0.022, rot=(0, R(lean * side), 0))
                pal.paint(f, 'white' if i < 2 else 'gold')
                parts.append(f)
            pieces[f'Templar_Pauldron_{tag}'] = (kit.join(f'Templar_Pauldron_{tag}', parts), f'upperarm.{tag.lower()}')
        g = kit.shell('gorget', [(0, 0.02, 1.16, 0.40, 0.36), (0, 0.02, 1.22, 0.37, 0.33), (0, 0.02, 1.29, 0.40, 0.36)], segs=12, smooth=False)
        pal.paint(g, 'steel')
        pal.paint(g, 'gold', faces=[p.index for p in g.data.polygons if p.center.z > 1.24])
        pieces['Templar_Gorget'] = (kit.join('Templar_Gorget', [g]), 'chest')
        front = kit.panel('front', -0.39, 0.36, 0.62, 0.12, bulge=-0.05)
        back = kit.panel('back', 0.38, 0.40, 0.62, 0.10, bulge=0.05)
        for o in (front, back):
            pal.paint(o, 'white')
            pal.paint(o, 'gold', faces=[p.index for p in o.data.polygons if p.center.z < 0.2])
        sun = kit.shell('sun', [(0, 0, 0, 0.085, 0.085), (0, 0, 0.02, 0.07, 0.07), (0, 0, 0.03, 0, 0)], segs=10, cap_lo=True, smooth=False)
        sun.rotation_euler = (R(90), 0, 0)
        sun.location = (0, -0.445, 0.40)
        pal.paint(sun, 'gold')
        rays = []
        for k in range(8):
            r = kit.box(f'ray{k}', (math.cos(k * math.pi / 4) * 0.13, -0.45, 0.40 + math.sin(k * math.pi / 4) * 0.13), (0.05, 0.014, 0.018), rot=(0, -k * math.pi / 4, 0))
            pal.paint(r, 'gold')
            rays.append(r)
        pieces['Templar_Tabard'] = (kit.join('Templar_Tabard', [front, back, sun] + rays), kit.cloth_weights(0.62, 0.10))
        b = belt(pal, 'blue')
        boss = kit.ball('boss', (0, -0.43, 0.63), 0.07, scale=(1, 0.5, 1), sub=1)
        pal.paint(boss, 'gold')
        pieces['Templar_Belt'] = (kit.join('Templar_Belt', [b, boss]), 'hips')
        return pieces
    return 'Knight', cols, build


# ---------------------------------------------------------------- hierophant (a cleric)
def hierophant():
    cols = {'white': 'white', 'shade': 'white~dark', 'gold': 'gold', 'glow': 'holy~glow', 'brass': 'brass', 'sky': 'sky'}

    def build(pal):
        parts = []
        for x in (-0.17, 0.17):
            s = kit.panel(f'stole{x}', -0.40, 0.13, 1.22, 0.30, bulge=-0.03, flare=0.25, x=x, rows=7, cols=2)
            pal.paint(s, 'white')
            pal.paint(s, 'gold', faces=[p.index for p in s.data.polygons if p.center.z < 0.44])
            pal.paint(s, 'sky', faces=[p.index for p in s.data.polygons if 0.44 <= p.center.z < 0.50])
            parts.append(s)
        yoke = kit.arc('yoke', [(0, 0.02, 1.20, 0.30, 0.42), (0, 0.02, 1.25, 0.26, 0.37)], 20, 160, segs=8)
        pal.paint(yoke, 'white')
        parts.append(yoke)
        pieces = {'Hiero_Stole': (kit.join('Hiero_Stole', parts), kit.cloth_weights(0.60, 0.30, legs=0.35, upper=(0.97, 'chest')))}
        # behind the head, its rays reaching past it on every side (behind the shoulders it was hidden
        # by the head from in front and by the body from above)
        disc = kit.shell('disc', [(0, 0, 0, 0.24, 0.24), (0, 0, 0.025, 0.21, 0.21), (0, 0, 0.035, 0, 0)], segs=12, cap_lo=True, smooth=False)
        disc.rotation_euler = (R(-90), 0, 0)
        disc.location = (0, 0.55, 1.78)
        pal.paint(disc, 'glow')
        burst = [disc]
        for k in range(12):
            a = k * math.pi / 6
            long = 0.58 if k % 2 == 0 else 0.40
            f = kit.fin(f'ray{k}', [(-0.055, 0.2), (0.055, 0.2), (0, 0.2 + long)], at=(0, 0.56, 1.78), thickness=0.022, rot=(0, a, 0))
            pal.paint(f, 'gold')
            burst.append(f)
        pieces['Hiero_Sunburst'] = (kit.join('Hiero_Sunburst', burst), 'head')
        for side, tag in ((1, 'L'), (-1, 'R')):
            pieces[f'Hiero_Cuff_{tag}'] = (cuff(pal, f'Hiero_Cuff_{tag}', side, 'white', 'gold', flare=0.25), f'lowerarm.{tag.lower()}')
        b = belt(pal, 'gold', h=0.07)
        chain = kit.box('chain', (0.34, -0.30, 0.50), (0.012, 0.012, 0.18))
        pal.paint(chain, 'brass')
        pot = kit.ball('pot', (0.34, -0.30, 0.36), 0.075, sub=1)
        pal.paint(pot, 'brass')
        ember = kit.ball('ember', (0.34, -0.30, 0.40), 0.05, sub=1)
        pal.paint(ember, 'glow')
        pieces['Hiero_Censer'] = (kit.join('Hiero_Censer', [b, chain, pot, ember]), 'hips')
        return pieces
    return 'Knight', cols, build


# ---------------------------------------------------------------- footpad (a thief)
def footpad():
    cols = {'scarf': 'crimson', 'deep': 'crimson~dark', 'leather': 'leather_dark', 'tan': 'leather_tan', 'steel': 'steel', 'gold': 'gold', 'cloth': 'grey~dark'}

    def build(pal):
        wrap = kit.shell('wrap', [(0, 0.0, 1.14, 0.38, 0.35), (0, -0.02, 1.19, 0.44, 0.40), (0, -0.02, 1.27, 0.42, 0.38), (0, 0.0, 1.31, 0.33, 0.31)], segs=12, smooth=False)
        pal.paint(wrap, 'scarf')
        tails = []
        for i, (x, bot) in enumerate(((0.10, 0.72), (0.24, 0.82))):
            # (hung straight: a panel turns about the world's origin, not its own top)
            t = kit.panel(f'tail{i}', 0.39 + 0.03 * i, 0.11, 1.20, bot, bulge=0.07, flare=0.3, x=x, rows=4, cols=2, ragged=0.05)
            pal.paint(t, 'scarf' if i == 0 else 'deep')
            tails.append(t)
        pieces = {'Footpad_Scarf': (kit.join('Footpad_Scarf', [wrap] + tails), 'chest')}
        # the bandolier: a strap from the left shoulder to the right hip, three knives on the chest
        strap = kit.shell('strap', [(0, -0.01, -0.035, 0.455, 0.405), (0, -0.01, 0.035, 0.455, 0.405)], segs=14, smooth=False)
        strap.location = (0, 0, 0.93)                  # (a flat band round the body, tipped from shoulder to hip)
        strap.rotation_euler = (0, R(38), 0)
        pal.paint(strap, 'leather')
        bits = [strap]
        for i in range(3):
            x = 0.16 - 0.14 * i
            k = kit.box(f'knife{i}', (x, -0.39, 1.02 - 0.11 * i), (0.035, 0.03, 0.12), rot=(0, R(38), 0))
            pal.paint(k, 'steel')
            hilt = kit.box(f'hilt{i}', (x + 0.045, -0.39, 1.075 - 0.11 * i), (0.05, 0.035, 0.03), rot=(0, R(38), 0))
            pal.paint(hilt, 'gold')
            bits += [k, hilt]
        pieces['Footpad_Bandolier'] = (kit.join('Footpad_Bandolier', bits), 'spine')
        b = belt(pal, 'leather', h=0.09)
        bag = [b]
        for i, (x, y, r) in enumerate(((0.30, -0.30, 0.085), (-0.12, -0.41, 0.07), (0.40, 0.10, 0.08))):
            p = kit.ball(f'pouch{i}', (x, y, 0.55), r, scale=(1, 0.75, 1.1), sub=1)
            pal.paint(p, 'tan')
            bag.append(p)
        coin = kit.ball('coin', (-0.12, -0.46, 0.57), 0.022, sub=1)
        pal.paint(coin, 'gold')
        pieces['Footpad_Pouches'] = (kit.join('Footpad_Pouches', bag + [coin]), 'hips')
        for side, tag in ((1, 'L'), (-1, 'R')):
            pieces[f'Footpad_Wrap_{tag}'] = (kit.join(f'Footpad_Wrap_{tag}', bracer(pal, 'w', side, 'cloth', 'leather')), f'lowerarm.{tag.lower()}')
        return pieces
    return 'Rogue', cols, build


# ---------------------------------------------------------------- nightblade (an assassin)
def nightblade():
    cols = {'black': 'black', 'night': 'obsidian', 'red': 'blood', 'steel': 'black_iron', 'edge': 'silver', 'gold': 'gold'}

    def build(pal):
        collar = kit.shell('collar', [(0, 0.03, 1.02, 0.46, 0.40), (0, 0.03, 1.08, 0.58, 0.48), (0, 0.03, 1.20, 0.52, 0.45), (0, 0.03, 1.33, 0.44, 0.40)],
                           segs=12, smooth=False)
        pal.paint(collar, 'black')
        pal.paint(collar, 'red', faces=[p.index for p in collar.data.polygons if p.center.z > 1.26])
        parts = [collar]
        for side in (1, -1):                                 # the shoulders drawn out to points
            f = kit.fin(f'point{side}', [(0, -0.07), (0.34, 0.03), (0, 0.10)], at=(0.5 * side, 0.02, 1.12), thickness=0.2,
                        rot=(0, R(-18) if side > 0 else R(180 + 18), 0))
            pal.paint(f, 'night')
            parts.append(f)
        pieces = {'Night_Mantle': (kit.join('Night_Mantle', parts), 'chest')}
        blades = []
        for side in (1, -1):                                 # crossed on the back, hilts over the shoulders
            sh = kit.box(f'sheath{side}', (0.0, 0.43, 0.95), (0.075, 0.04, 0.62), rot=(0, R(34 * side), 0))
            pal.paint(sh, 'steel')
            hilt = kit.box(f'hilt{side}', (0.215 * side, 0.43, 1.27), (0.045, 0.045, 0.16), rot=(0, R(34 * side), 0))
            pal.paint(hilt, 'red')
            pom = kit.ball(f'pom{side}', (0.265 * side, 0.43, 1.345), 0.035, sub=1)
            pal.paint(pom, 'gold')
            blades += [sh, hilt, pom]
        pieces['Night_Blades'] = (kit.join('Night_Blades', blades), 'chest')
        sash = belt(pal, 'red', h=0.10)
        tails = []
        for i, (x, bot) in enumerate(((-0.30, 0.22), (-0.40, 0.32))):
            t = kit.panel(f'st{i}', -0.30 + 0.12 * i, 0.10, 0.60, bot, bulge=-0.03, flare=0.3, x=x, rows=4, cols=2, ragged=0.04)
            pal.paint(t, 'red')
            tails.append(t)
        pieces['Night_Sash'] = (kit.join('Night_Sash', [sash] + tails), kit.cloth_weights(0.60, 0.22))
        for side, tag in ((1, 'L'), (-1, 'R')):
            parts = bracer(pal, 'b', side, 'steel', 'red')
            edge = kit.fin(f'edge{side}', [(0, -0.03), (0.34, 0.0), (0, 0.045)], at=(0.47 * side, 0, 1.24), thickness=0.022,
                           rot=(0, 0 if side > 0 else R(180), 0))
            pal.paint(edge, 'edge')
            pieces[f'Night_Bracer_{tag}'] = (kit.join(f'Night_Bracer_{tag}', parts + [edge]), f'lowerarm.{tag.lower()}')
        return pieces
    return 'Rogue_Hooded', cols, build


# ---------------------------------------------------------------- wayfinder (a ranger)
def wayfinder():
    cols = {'leaf': 'forest', 'moss': 'olive', 'deep': 'forest~dark', 'leather': 'leather', 'fur': 'fur_brown', 'feather': 'white', 'tip': 'teal',
            'wool': 'leather_tan', 'horn': 'bone'}

    def build(pal):
        SEGS = 20
        zig = lambda amp: (lambda a, i: (amp if round(a / (2 * math.pi / SEGS)) % 2 else -amp * 0.4) if i == 1 else 0)
        low = kit.shell('low', [(0, 0.03, 1.02, 0.45, 0.39), (0, 0.03, 0.93, 0.66, 0.56), (0, 0.03, 1.10, 0.60, 0.51), (0, 0.03, 1.16, 0.50, 0.43)],
                        segs=SEGS, wave=zig(0.12), smooth=False)
        pal.paint(low, 'leaf')
        pal.paint(low, 'deep', faces=[p.index for p in low.data.polygons if p.center.z < 1.0])
        top = kit.shell('top', [(0, 0.03, 1.12, 0.46, 0.40), (0, 0.03, 1.06, 0.60, 0.51), (0, 0.03, 1.20, 0.53, 0.46), (0, 0.03, 1.28, 0.40, 0.36)],
                        segs=SEGS, wave=zig(0.10), smooth=False, turn=math.pi / SEGS)
        pal.paint(top, 'moss')
        pieces = {'Way_Mantle': (kit.join('Way_Mantle', [low, top]), 'chest')}
        feathers = []
        for i, (lift, lean, key) in enumerate(((0.34, 12, 'feather'), (0.30, 32, 'tip'), (0.24, 52, 'feather'))):
            f = kit.fin(f'f{i}', [(-0.03, 0), (0.03, 0), (0.045, lift * 0.6), (0, lift), (-0.045, lift * 0.6)], at=(0.52, 0.10, 1.24), thickness=0.016,
                        rot=(R(8), R(lean), 0))
            pal.paint(f, key)
            feathers.append(f)
        pieces['Way_Feathers'] = (kit.join('Way_Feathers', feathers), 'upperarm.l')
        roll = kit.shell('roll', [(0, 0, -0.30, 0.0, 0.0), (0, 0, -0.29, 0.11, 0.11), (0, 0, 0.29, 0.11, 0.11), (0, 0, 0.30, 0.0, 0.0)], segs=10, smooth=True)
        roll.rotation_euler = (0, R(90), 0)
        roll.location = (0, 0.47, 0.84)
        pal.paint(roll, 'wool')
        straps = []
        for x in (-0.16, 0.16):
            s = kit.ring(f's{x}', (x, 0.47, 0.84), 0.115, 0.018, segs=10, sides=4, rot=(0, 0, R(90)))
            pal.paint(s, 'leather')
            straps.append(s)
        pieces['Way_Bedroll'] = (kit.join('Way_Bedroll', [roll] + straps), 'spine')
        b = belt(pal, 'leather', h=0.09)
        pouch = kit.ball('pouch', (0.33, -0.27, 0.55), 0.085, scale=(1, 0.75, 1.1), sub=1)
        pal.paint(pouch, 'wool')
        horn = kit.shell('horn', [(0, 0, 0, 0.05, 0.05), (0.03, 0, 0.10, 0.035, 0.035), (0.09, 0, 0.19, 0, 0)], segs=7, cap_lo=True, smooth=True)
        horn.rotation_euler = (R(180), 0, 0)
        horn.location = (-0.20, -0.42, 0.60)
        pal.paint(horn, 'horn')
        pieces['Way_Belt'] = (kit.join('Way_Belt', [b, pouch, horn]), 'hips')
        for side, tag in ((1, 'L'), (-1, 'R')):
            parts = bracer(pal, 'b', side, 'leather', 'moss')
            trim = kit.shell(f'trim{side}', [(0, 0, 0.19, 0.17, 0.17), (0, 0, 0.23, 0.20, 0.20), (0, 0, 0.27, 0.17, 0.17)], segs=10, smooth=False,
                             wave=lambda a, i: 0.08 * math.sin(5 * a) if i == 1 else 0)
            trim.rotation_euler = (0, R(90 * side), 0)
            trim.location = (0.47 * side, 0.0, 1.107)
            pal.paint(trim, 'fur')
            pieces[f'Way_Bracer_{tag}'] = (kit.join(f'Way_Bracer_{tag}', parts + [trim]), f'lowerarm.{tag.lower()}')
        return pieces
    return 'Rogue_Hooded', cols, build


# ---------------------------------------------------------------- troubadour (a bard)
def troubadour():
    cols = {'white': 'white', 'cape': 'royal_blue', 'lining': 'gold', 'purple': 'purple', 'wood': 'wood', 'pale': 'wood_pale', 'dark': 'wood_dark',
            'gold': 'gold', 'red': 'crimson'}

    def build(pal):
        SEGS = 24
        pleat = lambda a, i: (0.10 if round(a / (2 * math.pi / SEGS)) % 2 else -0.06) if i in (0, 2) else 0
        ruff = kit.shell('ruff', [(0, 0.0, 1.19, 0.50, 0.46), (0, 0.0, 1.23, 0.36, 0.33), (0, 0.0, 1.27, 0.50, 0.46)], segs=SEGS, wave=pleat, smooth=False)
        pal.paint(ruff, 'white')
        pieces = {'Troub_Ruff': (kit.join('Troub_Ruff', [ruff]), 'chest')}
        # the half-cape: over the left shoulder, from the front round to the back
        cape = kit.arc('cape', [(0.10, 0.02, 0.70, 0.62, 0.56), (0.10, 0.02, 0.95, 0.58, 0.52), (0.08, 0.02, 1.14, 0.50, 0.45), (0.05, 0.02, 1.23, 0.38, 0.35)],
                       -70, 110, segs=10, thickness=0.02)
        pal.paint(cape, 'cape')
        pal.paint(cape, 'lining', faces=[p.index for p in cape.data.polygons if p.center.z < 0.78])
        clasp = kit.ball('clasp', (0.20, -0.36, 1.18), 0.045, sub=1)
        pal.paint(clasp, 'gold')
        pieces['Troub_Capelet'] = (kit.join('Troub_Capelet', [cape, clasp]), 'chest')
        # the lute, slung across the back: its bowl low at the right, its neck up over the left shoulder
        bowl = kit.ball('bowl', (-0.10, 0.50, 0.82), 0.22, scale=(1.0, 0.42, 1.25), sub=2)
        pal.paint(bowl, 'wood')
        face = kit.ball('face', (-0.10, 0.575, 0.82), 0.19, scale=(1.0, 0.12, 1.25), sub=2)
        pal.paint(face, 'pale')
        hole = kit.ball('hole', (-0.10, 0.60, 0.86), 0.06, scale=(1, 0.2, 1), sub=1)
        pal.paint(hole, 'dark')
        neck = kit.box('neck', (0.13, 0.52, 1.20), (0.06, 0.04, 0.56), rot=(0, R(33), 0))
        pal.paint(neck, 'dark')
        head = kit.box('head', (0.30, 0.52, 1.47), (0.09, 0.05, 0.13), rot=(0, R(33), 0))
        pal.paint(head, 'wood')
        pegs = []
        for i in range(2):
            pg = kit.ball(f'peg{i}', (0.35 + 0.04 * i, 0.52, 1.44 + 0.07 * i), 0.022, sub=1)
            pal.paint(pg, 'gold')
            pegs.append(pg)
        pieces['Troub_Lute'] = (kit.join('Troub_Lute', [bowl, face, hole, neck, head] + pegs), 'chest')
        sash = belt(pal, 'purple', h=0.10)
        tail = kit.panel('tail', -0.33, 0.10, 0.60, 0.30, bulge=-0.03, flare=0.2, x=-0.30, rows=3, cols=2)
        pal.paint(tail, 'purple')
        tassel = kit.ball('tassel', (-0.30, -0.36, 0.27), 0.045, scale=(1, 1, 1.4), sub=1)
        pal.paint(tassel, 'gold')
        pieces['Troub_Sash'] = (kit.join('Troub_Sash', [sash, tail, tassel]), kit.cloth_weights(0.60, 0.27))
        for side, tag in ((1, 'L'), (-1, 'R')):
            pieces[f'Troub_Cuff_{tag}'] = (cuff(pal, f'Troub_Cuff_{tag}', side, 'red', 'white', flare=0.24, zig=True), f'lowerarm.{tag.lower()}')
        return pieces
    return 'Rogue', cols, build


# ---------------------------------------------------------------- gravecaller (a necromancer)
def gravecaller():
    cols = {'bone': 'bone', 'old': 'bone~dark', 'shroud': 'shadow', 'deep': 'black', 'purple': 'violet~dark', 'iron': 'black_iron', 'glow': 'poison~glow',
            'dark': 'obsidian'}

    def build(pal):
        base = kit.shell('base', [(0, 0.03, 1.04, 0.47, 0.40), (0, 0.03, 1.10, 0.58, 0.49), (0, 0.03, 1.19, 0.50, 0.43), (0, 0.03, 1.25, 0.40, 0.36)],
                         segs=12, smooth=False)
        pal.paint(base, 'deep')
        spikes = [base]
        for k in range(9):                                   # a fan of bone round the back and sides, tallest behind
            a = R(-20 + 220 * k / 8)
            tall = 0.20 + 0.16 * math.sin(math.pi * k / 8)
            s = kit.shell(f'sp{k}', [(0, 0, 0, 0.045, 0.045), (0, 0, tall, 0, 0)], segs=5, cap_lo=True, smooth=False)
            s.location = (math.cos(a) * 0.50, 0.03 + math.sin(a) * 0.43, 1.17)
            s.rotation_euler = (R(-24) * math.sin(a), R(24) * math.cos(a), 0)
            pal.paint(s, 'bone' if k % 2 == 0 else 'old')
            spikes.append(s)
        pieces = {'Grave_Collar': (kit.join('Grave_Collar', spikes), 'chest')}
        # a skull on the left shoulder, looking out and a little forward
        cx, cz = 0.52, 1.24
        skull = kit.ball('skull', (cx, 0, cz), 0.17, scale=(1.0, 1.05, 0.95), sub=2)
        pal.paint(skull, 'bone')
        jaw = kit.box('jaw', (cx + 0.02, -0.10, cz - 0.15), (0.17, 0.12, 0.07))
        pal.paint(jaw, 'old')
        bits = [skull, jaw]
        for dx in (-0.065, 0.075):
            eye = kit.ball(f'eye{dx}', (cx + dx, -0.155, cz + 0.01), 0.048, sub=1)
            pal.paint(eye, 'glow')
            bits.append(eye)
        nose = kit.box('nose', (cx + 0.005, -0.17, cz - 0.06), (0.03, 0.03, 0.04))
        pal.paint(nose, 'dark')
        pieces['Grave_Skull'] = (kit.join('Grave_Skull', bits + [nose]), 'upperarm.l')
        SEGS = 16
        rag = lambda a, i: (0.10 if round(a / (2 * math.pi / SEGS)) % 2 else -0.08) if i == 0 else 0
        shroud = kit.shell('shroud', [(0, 0, 0.10, 0.60, 0.54), (0, 0, 0.30, 0.54, 0.48), (0, 0, 0.50, 0.48, 0.43), (0, 0, 0.64, 0.45, 0.40)],
                           segs=SEGS, wave=rag, smooth=False)
        pal.paint(shroud, 'shroud')
        pal.paint(shroud, 'purple', faces=[p.index for p in shroud.data.polygons if p.center.z < 0.25])
        pieces['Grave_Shroud'] = (kit.join('Grave_Shroud', [shroud]), kit.cloth_weights(0.64, 0.10, legs=0.7))
        chain = belt(pal, 'iron', h=0.06)
        charm = kit.ball('charm', (0, -0.44, 0.56), 0.075, scale=(1, 0.8, 1.05), sub=1)
        pal.paint(charm, 'bone')
        gem = kit.ball('gem', (0.26, -0.33, 0.63), 0.045, sub=1)
        pal.paint(gem, 'glow')
        pieces['Grave_Chain'] = (kit.join('Grave_Chain', [chain, charm, gem]), 'hips')
        for side, tag in ((1, 'L'), (-1, 'R')):
            pieces[f'Grave_Cuff_{tag}'] = (cuff(pal, f'Grave_Cuff_{tag}', side, 'shroud', 'bone', flare=0.23), f'lowerarm.{tag.lower()}')
        return pieces
    return 'Mage', cols, build


LOOKS = {'templar': templar, 'hierophant': hierophant, 'footpad': footpad, 'nightblade': nightblade, 'wayfinder': wayfinder,
         'troubadour': troubadour, 'gravecaller': gravecaller}


def make(name, opts):
    hero, cols, build = LOOKS[name]()
    arm = kit.load_hero(hero)
    pal = kit.palette(name, cols)
    pieces = build(pal)
    kit.bind_all(pieces, arm)
    if '--export' in sys.argv:
        kit.export(pieces, arm, pal, name, cols, opts['out'])
    if opts['preview']:
        kit.preview_worn(arm, kit.BODY[hero], pieces, name, opts['out'])


def main():
    opts = scene.args()
    names = list(LOOKS) if '--all' in sys.argv else [sys.argv[sys.argv.index('--look') + 1]]
    for name in names:
        print('LOOK', name)
        make(name, opts)


main()
