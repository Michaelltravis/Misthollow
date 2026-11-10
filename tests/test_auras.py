#!/usr/bin/env python3
"""The buffs and debuffs on a creature's or another player's nameplate in /play
(map_system._auras): every spell and skill on them, one a spell, the harmful marked and first.

    python3 tests/test_auras.py
"""
import os
import sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))

FAILED = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok:
        FAILED.append(what)


def main():
    from affects import Affect, AffectManager
    import map_system as ms

    def aff(name, kind, to, value, duration, remaining=0):
        return Affect(name=name, type=kind, applies_to=to, value=value, duration=duration, remaining=remaining)

    S, F, D, H = AffectManager.TYPE_MODIFY_STAT, AffectManager.TYPE_FLAG, AffectManager.TYPE_DOT, AffectManager.TYPE_HOT
    body = SimpleNamespace(affects=[
        aff('armor', S, 'armor_class', -20, 24, 10),       # lower AC is better: a buff
        aff('armor', F, 'armour_ward', 1, 24, 20),         # ...its second affect: shown once
        aff('bless', S, 'hitroll', 2, 12),
        aff('rejuvenation', H, 'hp', 5, 6),
        aff('poison', D, 'hp', 4, 8, 3),
        aff('poison', F, 'poisoned', 1, 8, 3),
        aff('slow', F, 'slow', 1, 4),
        aff('curse', S, 'hitroll', -3, 10),
        aff('sunder armor', S, 'armor_class', 15, 5),      # higher AC is worse: a debuff
    ])
    out = ms._auras(body)
    names = [a['n'] for a in out]
    check(names.count('armor') == 1 and next(a for a in out if a['n'] == 'armor')['r'] == 20,
          "a spell's two affects are one aura, with the longer time left")
    bad = {a['n'] for a in out if a['h']}
    check(bad == {'poison', 'slow', 'curse', 'sunder armor'}, f'the harmful are marked ({sorted(bad)})')
    check(all(a['h'] for a in out[:len(bad)]), 'debuffs come first')
    check({'armor', 'bless', 'rejuvenation'} <= set(names) - bad, 'a ward, a stat boost and a heal over time are buffs')
    check(all(set(a) == {'n', 'h', 'r', 'd'} for a in out), 'each is {n, h, r, d}')

    check(ms._auras(SimpleNamespace(affects=[aff(f's{i}', S, 'str', 1, 5) for i in range(20)])).__len__() == 10, 'at most ten')
    check(ms._auras(SimpleNamespace()) == [], 'a body with nothing on it has no auras')
    blinded = ms._auras(SimpleNamespace(affects=[], blinded_rounds=2))
    check(blinded == [{'n': 'blinded', 'h': 1, 'r': 0, 'd': 0}], 'sand in the eyes (no affect) shows as blinded')

    src = open(os.path.join(HERE, '..', 'src', 'map_system.py'), encoding='utf-8').read()
    check(src.count("'auras': _auras(entity)") == 3, "creatures (map and each round) and other players carry 'auras'")

    print(f"\n{'ALL PASSED' if not FAILED else f'{len(FAILED)} FAILED'}")
    return 0 if not FAILED else 1


if __name__ == '__main__':
    sys.exit(main())
