"""The lantern every hero carries (docs/world/WORLD_SPINE.md: "the lantern is the world's one
sign"): a small six-sided iron lantern hung from the belt behind the right hip, its flame the one bright
thing on the body. One piece, bound to the hips, so it rides every clip the heroes play.

It hangs from a belt ring by a short hook; iron cap and foot,
six thin posts, and a flame of the kit's glowing fire colour inside (the engine's bloom makes it
shine; world3d gives it its light).

    tools/art3d/blender/run.sh models/lantern.py --preview --export
    -> out/lantern_preview.png (worn by the pack's knight) and out/equip/lantern.glb + .json
"""
import math
import sys

from mhb import kit, scene

NAME = 'lantern'
# each colour the piece uses: the kit's palette column that paints it
COLS = {'iron': 'black_iron', 'brass': 'brass', 'flame': 'fire~glow', 'ember': 'fire', 'leather': 'leather_dark'}

# where it hangs: behind the right hip, just under the belt (the model faces -Y: its right is -X, its
# back +Y). The left hip is behind the shield and the game's camera looks from behind and above, so
# this is where it shows most of the time
X, Y, TOP = -0.36, 0.36, 0.66          # the belt ring
R, H = 0.135, 0.28                     # the cage's radius and height (large for its wearer: at 0.1 by 0.21 it was a few pixels from the game's camera)
SIX = math.pi / 6                      # a face forward, not a corner


def lantern(pal):
    parts = []
    z1 = TOP - 0.075                   # the cap's foot
    z0 = z1 - H                        # the foot's top
    # the belt ring and the hook down to the cap
    loop = kit.ring('loop', (X, Y - 0.03, TOP), 0.024, 0.007, segs=8, sides=4)
    pal.paint(loop, 'brass')
    hook = kit.box('hook', (X, Y - 0.012, TOP - 0.03), (0.012, 0.012, 0.05), rot=(math.radians(-18), 0, 0))
    pal.paint(hook, 'iron')
    parts += [loop, hook]
    # the cap: a low six-sided roof with a knob
    cap = kit.shell('cap', [(X, Y, z1, R * 1.18, R * 1.18), (X, Y, z1 + 0.014, R * 1.18, R * 1.18), (X, Y, z1 + 0.045, R * 0.42, R * 0.42),
                            (X, Y, z1 + 0.058, R * 0.3, R * 0.3), (X, Y, z1 + 0.066, 0, 0)],
                    segs=6, cap_lo=True, smooth=False, turn=SIX)
    pal.paint(cap, 'iron')
    pal.paint(cap, 'brass', faces=[p.index for p in cap.data.polygons if p.center.z > z1 + 0.044])
    # the foot: a thick plate
    foot = kit.shell('foot', [(X, Y, z0 - 0.024, R * 0.86, R * 0.86), (X, Y, z0 - 0.012, R * 1.12, R * 1.12), (X, Y, z0, R * 1.12, R * 1.12)],
                     segs=6, cap_lo=True, cap_hi=True, smooth=False, turn=SIX)
    pal.paint(foot, 'iron')
    parts += [cap, foot]
    # six posts at the corners
    for k in range(6):
        a = SIX + 2 * math.pi * k / 6
        px, py = X + math.cos(a) * R, Y + math.sin(a) * R
        post = kit.box(f'post{k}', (px, py, (z0 + z1) / 2), (0.013, 0.013, H), rot=(0, 0, a))
        pal.paint(post, 'iron')
        parts.append(post)
    # a band round the middle, to read as a cage at game distance
    band = kit.shell('band', [(X, Y, z0 + H * 0.5 - 0.007, R * 1.04, R * 1.04), (X, Y, z0 + H * 0.5 + 0.007, R * 1.04, R * 1.04)],
                     segs=6, smooth=False, turn=SIX)
    pal.paint(band, 'iron')
    parts.append(band)
    # the light: a glowing pane inside the posts, and the flame at its heart
    glass = kit.shell('glass', [(X, Y, z0 + 0.004, R * 0.8, R * 0.8), (X, Y, z1 - 0.004, R * 0.8, R * 0.8)],
                      segs=6, cap_lo=True, cap_hi=True, smooth=False, turn=SIX)
    pal.paint(glass, 'flame')
    flame = kit.shell('flame', [(X, Y, z0 + 0.02, 0, 0), (X, Y, z0 + 0.05, R * 0.4, R * 0.4), (X, Y, z0 + 0.1, R * 0.26, R * 0.26), (X, Y, z0 + 0.15, 0, 0)],
                      segs=6, smooth=True)
    pal.paint(flame, 'ember')
    parts += [glass, flame]
    return kit.join('Lantern_Hip', parts)


def main():
    opts = scene.args()
    arm = kit.load_hero('Knight')
    pal = kit.palette(NAME, COLS)
    pieces = {'Lantern_Hip': (lantern(pal), 'hips')}
    kit.bind_all(pieces, arm)
    if '--export' in sys.argv:
        kit.export(pieces, arm, pal, NAME, COLS, opts['out'])
    if opts['preview']:
        kit.preview_worn(arm, kit.BODY['Knight'], pieces, NAME, opts['out'])


main()
