"""Learn by doing (src/mastery.py): abilities unlock by level, grow with use, trainers teach the rest.

Offline: every class ability has an unlock level and every class something at level 1;
reaching a level grants what it unlocks at 50% (never lowering or removing anything); the
chances and multipliers (improve, fizzle, power, trainer price); one use improves an ability
by 1-2 points and never past 85%; the spellbook's book describes every class; the commands
that perform abilities are found (renamed ones too).
Live (needs ./run.sh and the gauntlet accounts, as the level-6 warrior Gauntletb):
`skills` says when the rest arrive; an ability above your level is refused ("comes at level
14"); a trainer of your class takes a mastered ability 85 -> 90 for 1,250 gold and sends one
below 85 away to use it; another class's trainer points to your guild; /abilitybook; the
arranged bar (`webbar`) comes back in the map payload.
    python3 tests/test_mastery.py
"""
import asyncio
import glob
import json
import os
import random
import sys
import types

import aiohttp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import test_webmove as tw  # noqa: E402  (Telnet helper, check(), failures)
import gauntlet_accounts  # noqa: E402  (the test characters, made if missing)

check, failures = tw.check, tw.failures
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def fake_player(**kw):
    sent = []

    async def send(msg='', *a, **k):
        sent.append(str(msg))
    from config import Config
    p = types.SimpleNamespace(level=1, char_class='warrior', skills={}, spells={}, send=send,
                              config=types.SimpleNamespace(COLORS=Config.COLORS), world=None, sent=sent)
    for k, v in kw.items():
        setattr(p, k, v)
    return p


async def offline():
    import mastery
    from config import Config
    for cls in Config.CLASSES:
        r = mastery.roster(cls)
        missing = [a for a, _k in r if a not in mastery.UNLOCK.get(cls, {})]
        check(not missing, f'{cls}: every ability has an unlock level{f" (missing {missing})" if missing else ""}')
        lv = [mastery.unlock_level(cls, a) for a, _k in r]
        check(all(1 <= v <= 60 for v in lv) and 1 in lv, f'{cls}: levels 1-60, something at level 1 ({sorted(lv)[:3]}...)')

    p = fake_player()
    new = mastery.grant_now(p)
    check(set(p.skills) == {'strike', 'bash'} and set(p.skills.values()) == {50},
          f'a new warrior knows strike and bash at 50% ({p.skills})')
    p.level, p.skills['bash'] = 12, 70
    mastery.grant_now(p)
    check(p.skills['bash'] == 70 and 'second_attack' in p.skills and 'execute' not in p.skills,
          'level 12 adds what it reached, keeps what is better, nothing above (execute is 14)')
    p.level = 3
    mastery.grant_now(p)
    check('second_attack' in p.skills, 'a lower level never takes anything away')
    mage = fake_player(char_class='mage')
    mastery.grant_now(mage)
    check(set(mage.spells) == {'magic_missile', 'armor'}, f"a new mage knows magic missile and armor ({sorted(mage.spells)})")

    check(mastery.improve_chance(50) == 10 and mastery.improve_chance(50, ok=False) == 5 and mastery.improve_chance(84) >= 2,
          'improving: 10% a use at 50%, half on a failure, never below 2%')
    check(abs(mastery.fizzle_chance(50) - 12.5) < 1e-9 and abs(mastery.fizzle_chance(85) - 3.75) < 1e-9 and mastery.fizzle_chance(100) == 0,
          'fizzling: 12.5% at 50%, 3.75% at 85%, never at 100%')
    check(abs(mastery.power(50) - 1.0) < 1e-9 and abs(mastery.power(0) - 0.85) < 1e-9 and abs(mastery.power(100) - 1.15) < 1e-9,
          'power: x0.85 unknown, x1.0 at 50%, x1.15 perfected')
    check(mastery.step_cost(85) == 1250 and mastery.step_cost(95) == 3750, 'a trainer step: 1,250 gold at 85%, 3,750 at 95%')

    real = random.random
    random.random = lambda: 0.0          # every roll succeeds
    try:
        p = fake_player(skills={'kick': 84})
        got = await mastery.improve(p, 'kick')
        check(got == 85 and p.skills['kick'] == 85 and any('improves' in s for s in p.sent),
              f'a lucky use: kick 84 -> {got}, "Your kick improves!"')
        again = await mastery.improve(p, 'kick')
        check(again is None and p.skills['kick'] == 85, 'never past 85% by use')
        check(await mastery.improve(p, 'execute') is None and 'execute' not in p.skills, 'an unknown ability does not improve')
    finally:
        random.random = real

    for cls in Config.CLASSES:
        book = mastery.book(cls)
        described = sum(1 for e in book if e.get('desc'))
        spells_costed = all(e.get('cost') for e in book if e['type'] == 'spell')
        check(book and described >= len(book) * 0.9 and spells_costed and all(e.get('name') for e in book),
              f'{cls}: spellbook of {len(book)} ({described} described, spells costed)')
    check(any(e.get('passive') for e in mastery.book('warrior')), 'passives are marked (they stay off the bar)')

    m = mastery._methods()
    check('bash' in m.get('cmd_bash', set()), 'bash is performed by cmd_bash')
    check(any('truesight_shot' in v for k, v in m.items() if k in ('cmd_truesight_shot', 'cmd_aimed_shot')),
          'renamed abilities are found under both names (truesight shot = aimed shot)')

    # every class ability has its 3D event (push 6), and the 3D client's tests see today's books
    import combat_hooks
    who = fake_player(char_class='ranger', skills={'truesight_shot': 50})
    check(combat_hooks._class_ability(who, 'aimed_shot') == 'truesight_shot' and combat_hooks._class_ability(who, 'look') is None,
          "a renamed command's event names the book's ability (aimed_shot -> truesight_shot); `look` has none")
    check(combat_hooks.event_shape('warpath', 'warrior') == 'self' and combat_hooks.event_shape('eviscerate', 'thief') == 'melee'
          and combat_hooks.aim_of('layhands', 'paladin') == 'ally', 'shapes from the book (warpath: self) and the extras (eviscerate, lay hands)')
    # the level 31-60 abilities joined the books: none may name an affect type that doesn't
    # exist (AffectManager.TYPE_STAT crashed Rallying Cry, Warpath, Titan's Wrath...)
    import re
    from affects import AffectManager
    src = open(os.path.join(ROOT, 'src', 'commands.py')).read()
    kinds = set(re.findall(r"'type':\s*AffectManager\.(\w+)", src))
    missing = sorted(k for k in kinds if not hasattr(AffectManager, k))
    check(not missing, f"every affect type the commands use exists ({missing or sorted(kinds)})")
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import dump_abilitybook
    current = os.path.exists(dump_abilitybook.OUT) and open(dump_abilitybook.OUT).read() == dump_abilitybook.text()
    check(current, 'tests/web/fixtures/abilitybook.json is current (else: python3 tools/dump_abilitybook.py)')


def trainer_room(trainer_vnum):
    for f in glob.glob(os.path.join(ROOT, 'world/zones/*.json')):
        z = json.load(open(f))
        for rv, r in (z.get('rooms') or {}).items():
            if any(m.get('vnum') == trainer_vnum for m in r.get('mob_resets') or []):
                return int(rv)
    return None


async def live():
    await gauntlet_accounts.ensure()
    tw.ACCOUNT, tw.PASSWORD, tw.CHAR = 'gauntletb', 'gauntlet1', 'Gauntletb'
    tn = tw.Telnet()
    await tn.open()
    for line in ('wake', 'stand', 'restore'):
        await tn.cmd(line, 0.4)
    me = tw.CHAR.lower()

    text = await tn.cmd('skills', 1.2)
    check('[level 14]' in text and 'Execute' in text, "`skills` says when the rest arrive (execute: level 14)")
    text = await tn.cmd('execute', 1.0)
    check('comes at level 14' in text, f"an ability above your level is refused: {text.strip().splitlines()[-1] if text.strip() else '(nothing)'}")

    book = tw.get_json('/abilitybook?cls=warrior')
    ex = next((a for a in book.get('abilities', []) if a['id'] == 'execute'), None)
    check(ex is not None and ex['level'] == 14 and ex.get('desc'), f"/abilitybook: execute at level 14 ({ex and ex.get('desc', '')[:40]})")

    # a trainer of your class: mastered -> next step for gold; below mastery -> use it
    room = trainer_room(3023)
    gold_text = await tn.cmd('score', 0.8)
    for line in (f'set {me} skill bash 85', f'set {me} gold 5000', f'set {me} practices 0', f'goto {room}'):
        await tn.cmd(line, 0.6)
    text = await tn.cmd('practice bash', 1.0)
    check('85% → 90%' in text and '1,250 gold' in text, f"the trainer takes bash 85 -> 90 for 1,250 gold: {text.strip().splitlines()[-1] if text.strip() else ''}")
    text = await tn.cmd('practice kick', 1.0)
    check('come back when you have mastered' in text.lower(), 'below 85% the trainer sends you off to use it')
    text = await tn.cmd('practice', 1.2)
    check('grow as you use them' in text and 'Bash' in text and '90%' in text, '`practice` lists your abilities')

    # someone else's trainer points to your guild
    bron = trainer_room(3202)
    await tn.cmd(f'goto {bron}', 0.6)
    text = await tn.cmd('practice', 1.2)
    check("don't teach warriors" in text and 'Find them in' in text, "another class's trainer sends you to your guild")

    # the bar you arranged comes back in the map payload
    await tn.cmd('webbar bash kick - strike', 0.6)
    async with aiohttp.ClientSession() as http:
        async with http.ws_connect(f'ws://{tw.HOST}:{tw.MAP}/') as ws:
            await ws.send_str(tw.subscribe(tw.CHAR))
            bar = None
            for _ in range(40):
                msg = await asyncio.wait_for(ws.receive(), timeout=10)
                d = json.loads(msg.data) if msg.type == aiohttp.WSMsgType.TEXT else {}
                if d.get('type') == 'map_data':
                    bar = d['player'].get('bar')
                    break
            check(bar is not None and bar[:4] == ['bash', 'kick', None, 'strike'] and len(bar) == 40,
                  f"the arranged bar comes back in the payload ({bar and bar[:4]})")
    await tn.cmd('webbar', 0.4)

    # leave the character as it was
    for line in (f'set {me} skill bash 50', f'set {me} gold 949', 'recall', 'save'):
        await tn.cmd(line, 0.6)
    tn.w.close()


async def main():
    await offline()
    if '--offline' not in sys.argv:
        await live()
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
