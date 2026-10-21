"""The brain's parts that need no world: scoring (brain/utility.py), the threat table
(brain/threat.py) and profiles (brain/profile.py: tiers, ranks, roles, the limits data can't break).

    python3 tests/test_brain_core.py
"""
import os
import random
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import test_webmove as tw  # noqa: E402  (check(), failures)

check, failures = tw.check, tw.failures


def utility():
    from brain import utility as u
    check(u.logistic(0.5, k=10, mid=0.5) == 0.5 and u.logistic(1.0) > 0.99 and u.logistic(0.0) < 0.01,
          'logistic: half at its middle, all but 0 and 1 at the ends')
    check(u.inverse(0.25) == 0.75 and u.step(0.6, 0.5) == 1.0 and u.step(0.4, 0.5) == 0.0,
          'inverse and step curves')
    check(u.linear(2.0) == 1.0 and u.linear(-1) == 0.0, 'curves stay inside 0..1')
    check(u.score([0.9, 0.0, 1.0]) == 0.0, 'a zero consideration vetoes the action')
    one, many = u.score([0.8]), u.score([0.8, 1.0, 1.0, 1.0])
    check(abs(one - 0.8) < 1e-9 and many >= 0.8 * 0.999, f'considerations that are all yes do not sink a score ({one}, {many})')
    check(u.score([0.8, 0.8, 0.8]) > 0.8 ** 3, 'many considerations are compensated (above their bare product)')
    check(u.score([1.0], weight=0.5) == 0.5, 'the profile weight scales the score')
    check(u.choose([('a', 0.50), ('b', 0.55)], current='a', rng=None) == 'a',
          'momentum: what it is doing already wins a near tie')
    check(u.choose([('a', 0.30), ('b', 0.90)], current='a', rng=None) == 'b', '...but not a clearly better choice')
    check(u.choose([('a', 0.0), ('b', 0.0)]) is None, 'nothing chosen when everything is vetoed')
    state = random.getstate()
    rng = random.Random(4)
    picks = {u.choose([('a', 1.0), ('b', 0.95), ('c', 0.2)], rng=rng) for _ in range(60)}
    check(picks == {'a', 'b'}, f'among the near-best it picks with its own dice, never a poor choice ({picks})')
    check(random.getstate() == state, "the brain's dice leave the world's random untouched")


def threat():
    from brain.threat import ThreatTable
    class Ch:                      # characters hash by who they are, as Player and Mobile do
        def __init__(self, name):
            self.name = name
    a, b, c = (Ch(n) for n in 'ABC')
    t = ThreatTable()
    t.add(a, 100)
    t.add(b, 40)
    t.add(b, 70)
    check(t.top(now=0) is b and [x for x, _ in t.ranked()] == [b, a], 'the most threatening is on top')
    t.taunt(c, 6, now=10)
    check(t.top(now=11) is c and t.get(c) >= t.get(b) * 1.1 - 1e-9, 'a taunt puts the taunter above the top and holds')
    check(t.top(now=17) is c, '...and once the hold ends the taunter stays on top by its numbers')
    t.add(a, 500)
    check(t.top(now=17) is a, 'after the hold, the numbers rule again')
    t.taunt(b, 6, now=20)
    t.forget(b)
    check(t.top(now=21) is a and b not in t, 'a forgotten character drops out, its taunt with it')
    t.decay(0.5)
    check(len(t) == 2 and abs(t.get(a) - 300) < 1e-6, 'decay fades every entry by its share')
    t.decay(0.9995)
    check(len(t) == 0, 'decay lets small entries fade out altogether')


def profiles():
    from brain import profile as pr
    real = pr._data
    pr._data = {
        'features': {'threat': True},
        'floors': {'windup_action_s': 1.5, 'room_windup_cap_max': 9, 'leash_rooms_max': 4},
        'zone_tiers': {'by_level': [[0, 'gentle'], [9, 'readable'], [45, 'brutal']]},
        'tiers': {'readable': {'leash_rooms': 3, 'assist_count': 2, 'windup_action_s': 2.0, 'room_windup_cap': 2,
                               'chase_secs': 30},
                  'gentle': {'inherit': 'readable', 'leash_rooms': 2},
                  'brutal': {'inherit': 'readable', 'leash_rooms': 7, 'windup_action_s': 0.3, 'room_windup_cap': 12,
                             'chase_secs': 999}},
        'ranks': {'elite': {'add': {'assist_count': 1}, 'mul': {'special_rate': 1.5}},
                  'boss': {'set': {'sentinel': True}}},
        'roles': {'caster': {'keep_range': True}},
    }
    try:
        check(pr.feature('threat') and not pr.feature('pursuit'), 'feature flags (missing: off)')
        check(pr.tier_named('gentle') == {'leash_rooms': 2, 'assist_count': 2, 'windup_action_s': 2.0,
                                          'room_windup_cap': 2, 'chase_secs': 30},
              'a tier inherits what it does not say')

        def zone(levels, ai=None):
            z = types.SimpleNamespace(mobs={i: {'level': lv} for i, lv in enumerate(levels)}, number=1)
            if ai is not None:
                z.ai = ai
            return z
        check(pr.zone_tier(zone([3, 5, 7])) == 'gentle' and pr.zone_tier(zone([20, 30, 40])) == 'readable'
              and pr.zone_tier(zone([44, 50, 60])) == 'brutal', 'a zone takes the tier its median level falls in')
        check(pr.zone_tier(zone([60, 60], ai={'tier': 'readable'})) == 'readable', 'a population file can name the tier')
        check(pr.zone_tier(None) == 'readable', 'no zone: readable')

        def mob(levels, rank=None, own=None):
            room = types.SimpleNamespace(zone=zone(levels))
            return types.SimpleNamespace(room=room, rank=rank, ai_data={'profile': own} if own else {},
                                         home_zone=None, world=None)
        p = pr.resolve(mob([20]), roles={'caster'})
        check(p['tier'] == 'readable' and p['leash_rooms'] == 3 and p['keep_range'] is True and p['special_rate'] == 1.0,
              'a regular caster in a readable zone')
        e = pr.resolve(mob([20], rank='elite'))
        check(e['assist_count'] == 3 and e['special_rate'] == 1.5, 'rank adds and multiplies')
        check(pr.resolve(mob([20], rank='boss'))['sentinel'] is True, 'rank sets')
        b = pr.resolve(mob([60]))
        check(b['windup_action_s'] == 1.5, f"brutal data asks for a 0.3 s wind-up: held at the floor ({b['windup_action_s']})")
        check(b['room_windup_cap'] == 4, f"...a cap of 12 wind-ups a room: held at the code's 4, a looser floor can't lift it ({b['room_windup_cap']})")
        check(b['leash_rooms'] == 4, f"...a 7-room leash: held at the floors' stricter 4 ({b['leash_rooms']})")
        check(b['chase_secs'] == 120, f"...a 999 s chase: held at 120 ({b['chase_secs']})")
        own = pr.resolve(mob([20], own={'leash_rooms': 0, 'windup_action_s': 0.1}))
        check(own['leash_rooms'] == 0 and own['windup_action_s'] == 1.5,
              "a creature's own numbers win, inside the limits")
    finally:
        pr._data = real

    d = pr.reload()
    check({'readable', 'gentle', 'brutal'} <= set(d.get('tiers') or {}), 'world/ai_profiles.json loads, with its three tiers')
    feats = d.get('features') or {}
    shipped = {'threat', 'tactics', 'pursuit'}
    check(all(feats.get(k) is True for k in shipped) and not any(v for k, v in feats.items() if k not in shipped),
          f'phase 2a ships with threat, tactics and pursuit on, the rest off ({feats})')


def main():
    utility()
    threat()
    profiles()
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
