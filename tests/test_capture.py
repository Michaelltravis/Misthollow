"""What a skill says is read from the lines it sends (combat_hooks._capture): only its own. A line
another task sends meanwhile (the action tick's "You are stunned and cannot attack!") is
delivered but not taken for the skill's words, so a kick that landed keeps its cooldown.

    python3 tests/test_capture.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import test_webmove as tw  # noqa: E402  (check(), failures)

check, failures = tw.check, tw.failures


class Hero:
    def __init__(self):
        self.got = []

    async def send(self, msg='', *a, **k):
        self.got.append(str(msg))


async def main():
    import combat_hooks as ch
    hero = Hero()

    async def tick():                         # another task, as the action tick is
        await asyncio.sleep(0.01)
        await hero.send('You are stunned and cannot attack!')

    async def kick():                         # the skill
        await hero.send('You kick the rat hard.')
        await asyncio.sleep(0.03)
        await hero.send('The rat staggers.')

    other = asyncio.create_task(tick())
    await asyncio.sleep(0)
    lines = []
    undo = ch._capture(hero, lines)
    try:
        await kick()
    finally:
        undo()
    await other
    check(lines == ['You kick the rat hard.', 'The rat staggers.'], f"only the skill's own lines are read ({lines})")
    check(len(hero.got) == 3 and 'cannot attack' in hero.got[1], f'every line is still delivered ({hero.got})')
    check(not any(w in ' '.join(lines).lower() for w in ch._REFUSALS), 'so the kick is not taken for refused')
    check('send' not in hero.__dict__, 'the hero sends as before once the skill is done')

    # two captures nested (a swing reads both sides into one list), undone in either order
    a, b, both = Hero(), Hero(), []
    ua, ub = ch._capture(a, both), ch._capture(b, both)
    await a.send('you hit'); await b.send('you are hit')
    ua(); ub()
    await a.send('later')
    check(both == ['you hit', 'you are hit'], f'nested captures read both, then stop ({both})')

    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
