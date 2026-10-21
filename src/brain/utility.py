"""Choosing by score: each thing a creature could do is scored from a handful of considerations,
each a 0..1 reading of the fight passed through a response curve, multiplied together.

    score = weight * compensate(product of curves) * momentum

compensate() keeps an action with many considerations from sinking just for having many (Dave
Mark's infinite-axis utility). momentum favours what the creature is already doing, so it doesn't
dither between two near-equal choices; choose() picks among the near-best with the brain's own
dice, never the world's (random.* stays untouched, so the balance sims stay reproducible).
"""
import math


def clamp01(x):
    return 0.0 if x <= 0 else 1.0 if x >= 1 else float(x)


# ---------------------------------------------------------------- response curves (0..1 -> 0..1)
def linear(x, slope=1.0, shift=0.0):
    return clamp01(slope * x + shift)


def inverse(x):
    return clamp01(1.0 - x)


def logistic(x, k=10.0, mid=0.5):
    return clamp01(1.0 / (1.0 + math.exp(-k * (x - mid))))


def step(x, at=0.5):
    return 1.0 if x >= at else 0.0


def bell(x, mid=0.5, width=0.25):
    return clamp01(math.exp(-((x - mid) ** 2) / (2 * width * width)))


CURVES = {'linear': linear, 'inverse': inverse, 'logistic': logistic, 'step': step, 'bell': bell}


def compensate(p, n):
    """Lift a product of n considerations back toward what one would score."""
    if n <= 1:
        return p
    return p + (1.0 - p) * (1.0 - 1.0 / n) * p


def score(considerations, weight=1.0):
    """considerations: the curve outputs (0..1). A zero anywhere vetoes the action."""
    vals = [clamp01(c) for c in considerations]
    if not vals:
        return clamp01(weight)
    p = 1.0
    for v in vals:
        p *= v
        if p == 0.0:
            return 0.0
    return weight * compensate(p, len(vals))


MOMENTUM = 1.2      # what the creature is doing already
NEAR_BEST = 0.10    # choices within this share of the best are all fair picks


def choose(scored, current=None, rng=None, momentum=MOMENTUM, near=NEAR_BEST):
    """scored: [(name, score)]. The current choice gets momentum; then one of the choices
    within `near` of the best, by the brain's own dice (rng), else the best. None if all vetoed."""
    best, pool = 0.0, []
    for name, s in scored:
        if name == current:
            s *= momentum
        if s <= 0:
            continue
        pool.append((name, s))
        best = max(best, s)
    if not pool:
        return None
    fair = [n for n, s in pool if s >= best * (1.0 - near)]
    if rng is None or len(fair) == 1:
        return max(pool, key=lambda t: t[1])[0]
    return rng.choice(fair)
