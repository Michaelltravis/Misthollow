"""Other players and groups (push 5): sessions, presence, groups, loot rolls.

Offline: a loot roll holds its item (nobody can take it from the corpse meanwhile), the
winner gets it once, a pass or a broken-up group gives it back; leaving a group of two tells
the one left behind; round-robin hands out in turn among those present.
Live (needs ./run.sh and the gauntlet accounts; Gauntlet and Gauntletb together):
the map socket and /state answer only to the session token from MAPSYNC; a second login takes
the character over (the old session is told and closed, its web clients revoked) and the world
holds one copy; control characters typed into `say` never reach anyone; a web player's position
reaches the other player's 3D client; invite -> group_invite event -> accept -> group events on
both; `group kick` in a group of two doesn't drop the leader; quitting leaves the group.
    python3 tests/test_multiplayer.py [--offline]
"""
import asyncio
import json
import os
import re
import sys
import types
import urllib.error
import urllib.request

import aiohttp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import test_webmove as tw  # noqa: E402  (check(), failures, HOST/TELNET/MAP)
import gauntlet_accounts  # noqa: E402  (the test characters, made if missing)

check, failures = tw.check, tw.failures
MAPSYNC = re.compile(r'\x1b\]MAPSYNC:([^\x07:]+)(?::([^\x07]+))?\x07')
ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')


class Raw:
    """A telnet session that keeps what the server really sent (MAPSYNC and all)."""
    def __init__(self, account, char):
        self.account, self.char, self.raw = account, char, ''

    async def open(self):
        self.r, self.w = await asyncio.open_connection(tw.HOST, tw.TELNET)
        await self.read(1.5)
        for line in (self.account, 'gauntlet1', f'play {self.char}'):
            await self.cmd(line, 1.2)
        return self

    async def read(self, secs):
        out = ''
        end = asyncio.get_event_loop().time() + secs
        while True:
            left = end - asyncio.get_event_loop().time()
            if left <= 0:
                break
            try:
                data = await asyncio.wait_for(self.r.read(65536), timeout=left)
            except asyncio.TimeoutError:
                break
            if not data:
                self.closed = True
                break
            out += data.decode(errors='ignore')
        self.raw += out
        return out

    async def cmd(self, line, secs=0.8):
        self.w.write((line + '\r\n').encode())
        await self.w.drain()
        return ANSI.sub('', await self.read(secs))

    def token(self):
        found = MAPSYNC.findall(self.raw)
        return found[-1][1] if found else ''


def http_status(path):
    try:
        with urllib.request.urlopen(f'http://{tw.HOST}:{tw.MAP}{path}', timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


class Sock:
    """A map socket subscribed (or not) with a token, collecting what arrives."""
    async def open(self, http, name, token, mode='near'):
        self.ws = await http.ws_connect(f'ws://{tw.HOST}:{tw.MAP}/')
        self.got = []
        self.task = asyncio.create_task(self._pump())
        await self.ws.send_str(json.dumps({'type': 'subscribe', 'player': name, 'token': token, 'mode': mode}))
        return self

    async def _pump(self):
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                self.got.append(json.loads(msg.data))

    async def wait(self, kind, secs=6, pred=lambda d: True):
        for _ in range(int(secs * 10)):
            hit = next((d for d in self.got if d.get('type') == kind and pred(d)), None)
            if hit:
                return hit
            await asyncio.sleep(0.1)
        return None

    async def close(self):
        self.task.cancel()
        await self.ws.close()


async def offline():
    import groups
    sent = []

    def player(name, room):
        async def send(msg='', *a, **k):
            sent.append((name, str(msg)))
        return types.SimpleNamespace(name=name, room=room, inventory=[], connection=object(), group=None, following=None,
                                     send=send, world=None, config=types.SimpleNamespace(COLORS=groups.Config.COLORS),
                                     level=10, gold=0)

    room = types.SimpleNamespace(items=[])
    a, b = player('Ann', room), player('Bob', room)
    g = groups.Group(a)
    g.add_member(b)
    a.group = b.group = g
    sword = types.SimpleNamespace(short_desc='a fine sword', name='sword', rarity='rare')
    corpse = types.SimpleNamespace(contents=[sword])
    room.items.append(corpse)

    roll = groups.LootRoll(g, sword, corpse, [a, b])
    check(sword not in corpse.contents, 'a roll holds its item: it is no longer in the corpse to be taken')
    roll.votes = {'ann': 'greed', 'bob': 'need'}
    await roll.resolve()
    check(sword in b.inventory and sword not in a.inventory and sword not in corpse.contents,
          'need beats greed: Bob gets it, once')

    shield = types.SimpleNamespace(short_desc='a shield', name='shield', rarity='rare')
    corpse.contents.append(shield)
    roll = groups.LootRoll(g, shield, corpse, [a, b])
    roll.votes = {'ann': 'pass', 'bob': 'pass'}
    await roll.resolve()
    check(shield in corpse.contents, 'everyone passed: it goes back into the corpse')

    ring = types.SimpleNamespace(short_desc='a ring', name='ring', rarity='epic')
    corpse.contents.append(ring)
    roll = groups.LootRoll(g, ring, corpse, [a, b])
    g.active_rolls.append(roll)
    g.disband()
    check(ring in corpse.contents and not roll.group.active_rolls, 'the group breaks up: the roll ends, the item goes back')

    # leaving a group of two tells the one left behind (it used to message an empty list)
    sent.clear()
    a.group = b.group = None
    g = groups.Group(a)
    g.add_member(b)
    a.group = b.group = g
    await groups.GroupManager.leave_group(b)
    check(a.group is None and any(n == 'Ann' and 'Bob leaves the group' in m and 'disbanded' in m for n, m in sent),
          'Bob leaves a group of two: Ann is told it is disbanded')

    # round-robin among the members present
    c = player('Cid', room)
    g = groups.Group(a)
    g.add_member(b)
    g.add_member(c)
    order = [g.next_looter([a, c]).name for _ in range(4)]
    check(order == ['Ann', 'Cid', 'Ann', 'Cid'], f'round-robin skips who is away ({order})')


async def live():
    await gauntlet_accounts.ensure()
    async with aiohttp.ClientSession() as http:
        # ---- the session token ----
        g = await Raw('gauntlet', 'Gauntlet').open()
        await g.cmd('goto 3001', 0.8)
        tok = g.token()
        check(bool(tok), f'MAPSYNC carries a session token ({len(tok)} chars)')
        bad = await Sock().open(http, 'Gauntlet', 'not-the-token')
        check(await bad.wait('auth', 4) is not None and not await bad.wait('map_data', 1), 'subscribing with a wrong token gets nothing but "auth: no"')
        await bad.close()
        check(http_status('/state?player=Gauntlet') == 404 and http_status('/services?player=Gauntlet') == 404,
              'no token: /state and /services (mail) answer nothing')
        check(http_status(f'/state?player=Gauntlet&t={tok}') == 200, 'with the token: /state answers')
        gs = await Sock().open(http, 'Gauntlet', tok)
        check(await gs.wait('map_data', 6) is not None, 'with the token the map socket subscribes')

        # ---- a second login takes the character over ----
        g2 = await Raw('gauntlet', 'Gauntlet').open()
        await asyncio.sleep(0.5)
        old_text = ANSI.sub('', await g.read(1.0) + g.raw)
        check('logged in somewhere else' in old_text, 'the old session is told why it is closing')
        check(await gs.wait('revoked', 4) is not None, "the old session's web client is revoked")
        tok2 = g2.token()
        check(tok2 and tok2 != tok and 'You take over Gauntlet' in ANSI.sub('', g2.raw), 'the new session takes over (with a new token)')
        check(http_status(f'/state?player=Gauntlet&t={tok}') == 404 and http_status(f'/state?player=Gauntlet&t={tok2}') == 200,
              'the old token stops working, the new one works')
        text = await g2.cmd('score', 1.0)
        check('Gauntlet' in text, 'the taken-over character plays on')
        await gs.close()
        g = g2

        # ---- two players: speech, presence, groups ----
        b = await Raw('gauntletb', 'Gauntletb').open()
        await b.cmd('goto 3001', 0.8)
        await g.cmd('goto 3001', 0.8)
        btok = b.token()
        gws = await Sock().open(http, 'Gauntlet', g.token())
        bws = await Sock().open(http, 'Gauntletb', btok)
        await gws.wait('map_data', 6)
        await bws.wait('map_data', 6)

        b.raw = ''
        await g.cmd('say \x1b]MAPSYNC:Mallory:abc\x07hello there', 1.0)
        await b.read(0.8)
        check('\x1b]MAPSYNC:Mallory' not in b.raw and '\x07' not in b.raw.split('hello there')[0][-60:] and 'hello there' in b.raw,
              'control characters in `say` never reach the listener (no forged MAPSYNC)')

        bws.got.clear()
        await gws.ws.send_str(json.dumps({'type': 'pos', 'vnum': 3001, 'x': 7.5, 'z': 5.0}))
        pres = await bws.wait('presence', 4, lambda d: d.get('name') == 'Gauntlet')
        check(pres is not None and abs(pres['x'] - 7.5) < 0.01, f"Gauntlet's position reaches Gauntletb's client ({pres})")

        await b.cmd('group leave', 0.4)
        await g.cmd('group leave', 0.4)
        bws.got.clear(); gws.got.clear()
        await g.cmd('group invite gauntletb', 0.8)
        inv = await bws.wait('group_invite', 4)
        check(inv is not None and inv.get('from') == 'Gauntlet', f'`group invite` reaches the invitee as an event ({inv})')
        await b.cmd('group accept', 0.8)
        both = await gws.wait('group', 4, lambda d: d.get('group') and len(d['group'].get('members', [])) == 2)
        check(both is not None, 'joining pushes the group to its members')

        gws.got.clear(); bws.got.clear()
        text = await g.cmd('group kick gauntletb', 1.0)
        await g.read(0.4)
        alive = await g.cmd('score', 1.0)
        check('Gauntlet' in alive and not getattr(g, 'closed', False), '`group kick` in a group of two no longer drops the leader')
        check(await bws.wait('group', 4, lambda d: d.get('group') is None) is not None, "the kicked member's frames clear")

        # quitting leaves the group
        await g.cmd('group invite gauntletb', 0.6)
        await b.cmd('group accept', 0.8)
        g.raw = ''
        await b.cmd('quit', 1.0)
        await g.read(1.0)
        check('left the realm and the group' in ANSI.sub('', g.raw), 'a member who quits leaves the group (no ghost)')

        await gws.close()
        await bws.close()
        g.w.close()


async def main():
    await offline()
    if '--offline' not in sys.argv:
        await live()
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
