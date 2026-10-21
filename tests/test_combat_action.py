"""Real-time combat, live: a server (./run.sh) and the gauntlet admin account
(tools/gauntlet/README.md). The map socket subscribes the way /play does with
combat:'action', then:

- `webattack` on a creature: the blow lands at once (an attack event within a moment) and the
  client is told when the next is due; pressed again at once: not ready, no blow;
- the swings then come by themselves, about 3 s apart;
- a second skill within a second: "Not ready yet." and no ability event;
- a creature's wind-up is marked 2 s long and lands about 2 s later;
- switching action mode off mid-fight goes back to rounds with no two swings close together.

    python3 tests/test_combat_action.py
"""
import asyncio
import json
import os
import re
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_webmove as tw  # noqa: E402  (Telnet, check(), failures)
import gauntlet_accounts  # noqa: E402  (the test characters, made if missing)

check, failures = tw.check, tw.failures
ROOM, MOB, KW = 3054, 3062, 'fido'


def server_up():
    try:
        with socket.create_connection((tw.HOST, tw.TELNET), timeout=1):
            return True
    except OSError:
        return False


async def main():
    import aiohttp
    await gauntlet_accounts.ensure()
    tw.ACCOUNT, tw.PASSWORD, tw.CHAR = 'gauntlet', 'gauntlet1', 'Gauntlet'
    tn = tw.Telnet()
    await tn.open()
    for line in ('wake', 'stand', 'restore', f'goto {ROOM}', 'purge'):
        await tn.cmd(line, 0.5)
    level = 60
    # the hero outlasts the fight whatever its own level: a level-1 Gauntlet (20 health) falls
    # to this creature in two blows, and a dead hero has no swings to time (put back below)
    hp = re.findall(r'(\d+)/(\d+)hp', await tn.cmd('score', 0.6))
    maxhp = int(hp[-1][1]) if hp else 0
    me = tw.CHAR.lower()
    for line in (f'set {me} maxhp 60000', f'set {me} hp 60000'):
        await tn.cmd(line, 0.4)
    async with aiohttp.ClientSession() as http:
        async with http.ws_connect(f'ws://{tw.HOST}:{tw.MAP}/') as ws:
            def sub(action=True):
                return json.dumps({'type': 'subscribe', 'player': tw.CHAR, 'token': tw.TOKEN, 'mode': 'near',
                                   **({'combat': 'action'} if action else {})})
            await ws.send_str(sub())
            got = []

            async def pump():
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        d = json.loads(msg.data)
                        if d.get('type') == 'combat_events':
                            for e in d['events']:
                                got.append((time.time(), e))
            pumper = asyncio.create_task(pump())
            await asyncio.sleep(1.0)

            def mine(k, since=0):
                return [(t, e) for t, e in got if t >= since and e.get('k') == k and (e.get('src') or {}).get('p') == tw.CHAR]

            # a long fight: a creature with plenty of health, as strong as the hero
            for line in (f'mload {MOB}', f'set {KW} maxhp 60000', f'set {KW} hp 60000', f'set {KW} level {level}'):
                await tn.cmd(line, 0.4)
            t0 = time.time()
            await tn.cmd(f'webattack {KW}', 0.6)
            first = mine('attack', t0)
            check(bool(first) and first[0][0] - t0 < 0.5, f'webattack: the first blow lands at once ({first[0][0] - t0:.2f} s)' if first else 'webattack: the first blow lands at once (none)')
            sw = mine('swing', t0)
            check(bool(sw) and 2400 <= sw[-1][1].get('next_ms', 0) <= 3000, f'…and says when the next one is due ({sw[-1][1] if sw else None})')
            t1 = time.time()
            await tn.cmd('webattack', 0.4)
            again = mine('swing', t1)
            check(not mine('attack', t1) and again and again[-1][1].get('res') in ('not_ready', 'perfect'),
                  f'pressed again at once: no blow ({again[-1][1].get("res") if again else None})')

            # the swings come by themselves, every 3 s. Counted on the swing clock: a creature this
            # big has the boss kit, and its Terrifying Roar may stun the hero, whose swing then
            # comes on time but is spent ('skip', no blow)
            await asyncio.sleep(10.5)
            ticks = [t for t, e in mine('swing', t0) if e.get('res') != 'not_ready']
            gaps = [b - a for a, b in zip(ticks, ticks[1:])]
            check(len(ticks) >= 4 and all(2.7 <= g <= 3.4 for g in gaps), f'then a swing every 3 s by itself ({[round(g, 2) for g in gaps]})')

            # the global cooldown. Only a kick that was used counts: one refused (the roar's stun)
            # gives its second back, so that try is made again
            for _ in range(3):
                t2 = time.time()
                await tn.cmd('kick', 0.15)
                out = await tn.cmd('bash', 0.6)
                abil = [e.get('ability') for _t, e in mine('ability', t2)]
                if 'kick' in abil:
                    break
                await asyncio.sleep(1.5)
            check('Not ready yet' in out and 'bash' not in abil, f'a second skill within a second: "Not ready yet." (abilities {abil})')

            # a creature's wind-up: 2 s long, landing about 2 s later
            winds = [(t, e) for t, e in got if e.get('k') == 'windup']
            for _ in range(20):
                if winds:
                    break
                await asyncio.sleep(0.5)
                winds = [(t, e) for t, e in got if e.get('k') == 'windup']
            if winds:
                tw0, w = winds[0]
                res = [t for t, e in got if e.get('k') == 'resolve' and t >= tw0]
                for _ in range(10):
                    if res:
                        break
                    await asyncio.sleep(0.5)
                    res = [t for t, e in got if e.get('k') == 'resolve' and t >= tw0]
                check(w.get('ms') == 2000, f"a creature's wind-up is marked 2 s long ({w.get('ms')})")
                check(bool(res) and 1.6 <= res[0] - tw0 <= 2.6, f'…and lands about 2 s later ({res[0] - tw0:.2f} s)' if res else '…and lands (no resolve seen)')
            else:
                check(False, 'the creature winds up a blow (none seen in 10 s)')

            # off again: rounds, and no two swings close together across the switch
            t3 = time.time()
            await ws.send_str(sub(action=False))
            await asyncio.sleep(9.5)
            blows = [t for t, _e in mine('attack', t3 - 3.5)]
            gaps = [b - a for a, b in zip(blows, blows[1:])]
            check(bool(blows) and all(g >= 1.9 for g in gaps), f'action mode off mid-fight: rounds, no two swings close ({[round(g, 2) for g in gaps]})')

            # tidy up (purge only where the creature is: never the room a hero woke in)
            for line in (f'set {KW} hp 1', 'restore'):
                await tn.cmd(line, 0.5)
            await asyncio.sleep(3.5)
            for line in (f'goto {ROOM}', 'purge') + ((f'set {me} maxhp {maxhp}',) if maxhp else ()) + ('restore',):
                await tn.cmd(line, 0.5)
            pumper.cancel()
    await tn.cmd('quit', 0.5)
    tn.w.close()


if __name__ == '__main__':
    if not server_up():
        print('skip: no server on', tw.HOST, tw.TELNET)
        sys.exit(0)
    asyncio.run(main())
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)
