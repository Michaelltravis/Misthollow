"""The brain changes nothing it has not been told to: with every feature turned off
(MH_BRAIN_OFF=threat,...) the balance sims, which seed random and drive the real mob_ai and bosses
code, print the same thing to the byte as with no brain at all (MH_BRAIN=0). So turning a
feature off in world/ai_profiles.json gives back the old rules exactly.

    python3 tests/test_brain_parity.py          # about a minute and a half

(tools/balance/zones.py is not among them: it gives a different answer from one run to the
next with the same code, brain or none, so it can't be held to the byte.)
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_webmove as tw  # noqa: E402  (check(), failures)

check, failures = tw.check, tw.failures
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

RUNS = [
    ('marquee quests, rounds', ['tools/balance/sim.py', '--classes', 'warrior,cleric,mage', '--levels', '45',
                                '--party', '1,3', '--runs', '1']),
    ('marquee quests, real time', ['tools/balance/sim.py', '--classes', 'warrior,mage', '--levels', '45',
                                   '--party', '1', '--runs', '1', '--mode', 'action']),
    ('zone bosses', ['tools/balance/bosses.py', '--bosses', '10050,5318', '--classes', 'warrior,mage,cleric']),
]


FEATURES = 'threat,tactics,pursuit,social,life,talk'


def run(args, brain_on):
    env = dict(os.environ, MH_BRAIN='1' if brain_on else '0', MH_BRAIN_OFF=FEATURES, PYTHONHASHSEED='0')
    r = subprocess.run([sys.executable] + args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    return r.returncode, r.stdout


def main():
    for what, args in RUNS:
        code_on, on = run(args, True)
        code_off, off = run(args, False)
        same = code_on == code_off == 0 and on == off and on.strip()
        if not same:
            for a, b in zip(on.splitlines(), off.splitlines()):
                if a != b:
                    print(f'     brain on : {a}\n     brain off: {b}')
                    break
        check(bool(same), f'{what}: the brain with its features off and no brain at all, the same to the byte ({len(on.splitlines())} lines)')
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
