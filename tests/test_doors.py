"""Doors: parsing, both sides, keys, picks, the web door command and the live push.

Offline checks always run (fake rooms and players, the real door commands):
    python3 tests/test_doors.py
Live checks run too when a server is up (./run.sh) with the gauntlet admin accounts
(tools/gauntlet/README.md): the High Tower's diamond gate, 2512 north / 2513 south (key 2500,
"a diamond key"), with and without its key, `webdoor`, the push carrying both sides, and walking
through. (The oak door of Minos it used before went with the re-lay on the atlas.)
"""
import asyncio
import json
import os
import socket
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import test_webmove as tw  # noqa: E402  (Telnet helper, check(), failures)
import gauntlet_accounts  # noqa: E402  (the test characters, made if missing)
from config import Config  # noqa: E402
import doors  # noqa: E402

check, failures = tw.check, tw.failures


# ---------------------------------------------------------------- offline fakes
class Zone:
    def __init__(self, number):
        self.number = number


class Room:
    def __init__(self, vnum, zone=1):
        self.vnum, self.exits, self.characters, self.items, self.zone = vnum, {}, [], [], Zone(zone)

    async def send_to_room(self, msg, exclude=None):
        pass


class Item:
    def __init__(self, vnum, name, item_type='key'):
        self.vnum, self.name, self.item_type, self.short_desc = vnum, name, item_type, name


class Player:
    def __init__(self, room):
        self.name, self.account_name, self.room, self.config = 'Tester', 'tester', room, Config()
        self.inventory, self.equipment, self.skills = [], {}, {}
        self.dex = self.str = 14
        self.hp = self.max_hp = 100
        self.level, self.said = 10, []
        self.is_fighting = False
        room.characters.append(self)

    async def send(self, msg='', *a, **k):
        self.said.append(str(msg))


class WebMap:
    def __init__(self):
        self.zone_events, self.events = [], []

    async def send_zone_event(self, zones, event):
        self.zone_events.append((set(zones), event))

    async def notify_event(self, player, event):
        self.events.append(event)


def link(a, d, b, door=None, far_door=None):
    od = doors.OPPOSITE[d]
    a.exits[d] = {'to_room': b.vnum, 'room': b}
    b.exits[od] = {'to_room': a.vnum, 'room': a}
    if door is not None:
        a.exits[d]['door'] = dict(door)
        b.exits[od]['door'] = dict(far_door if far_door is not None else door)


def world_of(*rooms):
    w = types.SimpleNamespace(rooms={r.vnum: r for r in rooms}, web_map=WebMap(), obj_prototypes={77: {'short_desc': 'an iron key'}})
    doors.normalize(w)
    return w


async def offline():
    from commands import CommandHandler as C
    run = C

    # parsing: "s" is south (it used to be east), "u" is up, names and multi-word names
    a, e, s, up = Room(1), Room(2), Room(3), Room(4)
    link(a, 'east', e, {'name': 'door', 'state': 'closed', 'locked': False})
    link(a, 'south', s, {'name': 'door wooden', 'state': 'closed', 'locked': False})
    link(a, 'up', up, {'name': 'trapdoor trap', 'state': 'closed', 'locked': False}, {'name': 'up door', 'state': 'closed', 'locked': False})
    w = world_of(a, e, s, up)
    p = Player(a)
    await run.cmd_open(p, ['s'])
    check(a.exits['south']['door']['state'] == 'open' and a.exits['east']['door']['state'] == 'closed', "'open s' opens the south door, not the east one")
    check(s.exits['north']['door']['state'] == 'open', '…and the far side opens with it')
    await run.cmd_open(p, ['u'])
    check(a.exits['up']['door']['state'] == 'open', "'open u' opens the trapdoor up")
    check(up.exits['down']['door']['name'] == 'up door', 'the far side keeps its own name')
    await run.cmd_close(p, ['wooden'])
    check(a.exits['south']['door']['state'] == 'closed', "'close wooden' finds the wooden door by name")
    await run.cmd_open(p, ['door', 'wooden', 'south'])
    check(a.exits['south']['door']['state'] == 'open', "'open door wooden south' works")
    await run.cmd_close(p, ['door', 'wooden', 'south'])
    check(doors.label(a.exits['south']['door']) == 'wooden door', "labels read naturally ('door wooden' -> 'wooden door')")
    check(any('wooden door' in m for m in p.said), 'messages use the readable name')

    # "open n" with a wooden chest in the bag opens the door, not the chest
    n = Room(5)
    link(a, 'north', n, {'name': 'door', 'state': 'closed', 'locked': False})
    chest = Item(9, 'chest wooden', 'container')
    chest.is_closed, chest.is_locked = True, False
    p.inventory.append(chest)
    await run.cmd_open(p, ['n'])
    check(a.exits['north']['door']['state'] == 'open' and chest.is_closed, "'open n' opens the north door, not the chest")
    await run.cmd_open(p, ['chest'])
    check(not chest.is_closed, "'open chest' still opens the chest")

    # keys: carried or worn; keyless locks are anyone's
    b1, b2 = Room(10), Room(11)
    link(b1, 'west', b2, {'name': 'gate iron', 'state': 'closed', 'locked': True, 'key_vnum': 77})
    w = world_of(b1, b2)
    q = Player(b1)
    keys = doors.carried_keys(q)
    v = doors.view(b1.exits['west']['door'], keys, q)
    check(v['locked'] and not v['has_key'] and v.get('key_name') == 'an iron key', 'view: locked, no key, names the key')
    await run.cmd_unlock(q, ['w'])
    check(b1.exits['west']['door']['locked'], 'no key: unlock refused')
    check(any("don't have the key" in m for m in q.said), "…'You don't have the key.'")
    q.equipment['hold'] = Item(77, 'key iron')
    check(doors.view(b1.exits['west']['door'], doors.carried_keys(q), q)['has_key'], 'a held key counts')
    await run.cmd_unlock(q, ['iron'])
    check(not b1.exits['west']['door']['locked'] and not b2.exits['east']['door']['locked'], "'unlock iron' unlocks both sides")
    await run.cmd_lock(q, ['w'])
    check(b1.exits['west']['door']['locked'] and b2.exits['east']['door']['locked'], "'lock w' locks both sides")
    c1, c2 = Room(12), Room(13)
    link(c1, 'east', c2, {'name': 'door', 'state': 'closed', 'locked': True})
    world_of(c1, c2)
    r = Player(c1)
    check(doors.view(c1.exits['east']['door'], set(), r)['has_key'], 'a keyless lock can be worked by anyone')

    # picks: both sides; pickproof refuses; can_pick follows the skill
    r.skills['pick_lock'] = 90
    check(doors.view(c1.exits['east']['door'], set(), r)['can_pick'], 'can_pick with the skill')
    import random as _random
    real = _random.randint
    _random.randint = lambda a, b: a
    try:
        await run._do_pick(r, ['e'])
    finally:
        _random.randint = real
    check(not c1.exits['east']['door']['locked'] and not c2.exits['west']['door']['locked'], 'a picked lock opens on both sides')
    c1.exits['east']['door'].update({'locked': True, 'pickproof': True})
    await run._do_pick(r, ['e'])
    check(c1.exits['east']['door']['locked'], 'a pickproof lock refuses picks')
    check(not doors.view(c1.exits['east']['door'], set(), r)['can_pick'], '…and says so in the view')

    # every change stamps both sides with one revision and pushes one event for both zones
    # (let the pushes queued above go out first: nothing has yielded to the loop yet)
    await asyncio.sleep(0.02)
    d1, d2 = Room(20, zone=1), Room(30, zone=2)
    link(d1, 'north', d2, {'name': 'door', 'state': 'closed', 'locked': False})
    w = world_of(d1, d2)
    pd = Player(d1)
    await run.cmd_open(pd, ['n'])
    await asyncio.sleep(0.05)
    sent = w.web_map.zone_events
    check(len(sent) == 1 and sent[0][0] == {1, 2} and len(sent[0][1]['doors']) == 2, 'one door event for both sides, both zones')
    revs = {x['rev'] for x in sent[0][1]['doors']} if sent else set()
    check(len(revs) == 1 and d1.exits['north']['door']['rev'] == d2.exits['south']['door']['rev'], 'both sides share the revision')

    # the web door command
    pd.room = d1
    await run.cmd_close(pd, ['n'])
    w.web_map.events.clear()
    pd.world = w
    await run.cmd_webdoor(pd, ['20', 'north', 'open'])
    res = w.web_map.events[-1] if w.web_map.events else {}
    check(res.get('type') == 'door_result' and res.get('ok') and res['door']['state'] == 'open', 'webdoor open -> door_result ok')
    await run.cmd_webdoor(pd, ['99', 'north', 'open'])
    res = w.web_map.events[-1]
    check(res['ok'] is False and res['reason'] == '', 'webdoor from the wrong room -> resync (empty reason)')
    k1, k2 = Room(40), Room(41)
    link(k1, 'east', k2, {'name': 'door', 'state': 'closed', 'locked': True, 'key_vnum': 77})
    w2 = world_of(k1, k2)
    pk = Player(k1)
    pk.world = w2
    await run.cmd_webdoor(pk, ['40', 'east', 'unlockopen'])
    res = w2.web_map.events[-1]
    check(res['ok'] is False and "key" in res['reason'], "locked without the key -> 'You don't have the key.'")
    pk.inventory.append(Item(77, 'key'))
    await run.cmd_webdoor(pk, ['40', 'east', 'unlockopen'])
    res = w2.web_map.events[-1]
    check(res['ok'] and res['door'] == {'state': 'open', 'locked': False, 'broken': False, 'rev': res['door']['rev']}, 'unlockopen with the key -> open and unlocked')

    # load and reset
    m1, m2, m3, m4 = Room(50), Room(51), Room(52), Room(53)
    link(m1, 'east', m2, {'name': 'door', 'state': 'open', 'locked': True, 'key_vnum': 5})
    link(m3, 'east', m4, {'name': 'door', 'state': 'closed', 'locked': True}, {'name': 'door', 'state': 'open', 'locked': False})
    m1.exits['east']['door'].pop('key_vnum')
    m1.exits['east']['door']['key'] = 5
    w = world_of(m1, m2, m3, m4)
    check(m1.exits['east']['door']['locked'] is False, "normalize: 'open and locked' becomes unlocked")
    check(doors.key_vnum(m1.exits['east']['door']) == 5, "normalize: the old 'key' field becomes key_vnum")
    check(m4.exits['west']['door']['state'] == 'closed' and m4.exits['west']['door']['locked'], 'normalize: a disagreeing pair is closed and locked')
    doors.apply(m3, 'east', state='open', locked=False, broken=True)
    zone = types.SimpleNamespace(rooms={50: m1, 51: m2, 52: m3, 53: m4})
    doors.reset_zone(w, zone)
    check(m3.exits['east']['door']['state'] == 'closed' and not m3.exits['east']['door'].get('broken'), 'a zone reset restores a broken door')
    doors.apply(m3, 'east', state='open', locked=False)
    Player(m4)
    doors.reset_zone(w, zone)
    check(m3.exits['east']['door']['state'] == 'open', '…but not while a player stands on either side')


# ---------------------------------------------------------------- live
def server_up():
    try:
        with socket.create_connection((tw.HOST, tw.TELNET), timeout=1):
            return True
    except OSError:
        return False


async def live():
    import aiohttp
    await gauntlet_accounts.ensure()
    tw.ACCOUNT, tw.PASSWORD, tw.CHAR = 'gauntletb', 'gauntlet1', 'Gauntletb'
    tn = tw.Telnet()
    await tn.open()
    for line in ('wake', 'stand', 'goto 2512', 'restore'):
        await tn.cmd(line, 0.5)
    async with aiohttp.ClientSession() as http:
        async with http.ws_connect(f'ws://{tw.HOST}:{tw.MAP}/') as ws:
            await ws.send_str(tw.subscribe(tw.CHAR))
            got = []

            async def pump():
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        got.append(json.loads(msg.data))
            pumper = asyncio.create_task(pump())

            async def door_view():
                got.clear()
                await ws.send_str(tw.subscribe(tw.CHAR))
                for _ in range(25):
                    await asyncio.sleep(0.2)
                    for d in got:
                        for r in d.get('nearby') or []:
                            if r['vnum'] == 2512 and 'north' in (r.get('doors') or {}):
                                return r['doors']['north']
                return None

            # start closed and locked, without the key
            await tn.cmd('oload 2500', 0.5)
            for line in ('close north', 'lock north', 'drop key', 'purge'):
                await tn.cmd(line, 0.5)
            v = await door_view()
            check(v is not None and v['state'] == 'closed' and v['locked'] and v['has_key'] is False,
                  f"near payload: the diamond gate 2512 north is closed, locked, has_key false ({v and v.get('label')})")
            check(v is not None and v.get('key_name') == 'a diamond key', "…and names the key it needs")
            await tn.cmd('oload 2500', 0.5)
            v = await door_view()
            check(v is not None and v['has_key'] is True, 'with the diamond key: has_key true')
            got.clear()
            await tn.cmd('webdoor 2512 north unlockopen', 1.0)
            res = [d for d in got if d.get('type') == 'door_result']
            ev = [d for d in got if d.get('type') == 'door']
            check(bool(res) and res[-1]['ok'] and res[-1]['door']['state'] == 'open', 'webdoor unlockopen -> ok, open')
            both = {(x['vnum'], x['dir']) for e in ev for x in e['doors']}
            check({(2512, 'north'), (2513, 'south')} <= both, 'the door event carries both sides (2512 north, 2513 south)')
            got.clear()
            await tn.cmd('webmove 2512 2513 north', 1.0)
            mv = [d for d in got if d.get('type') == 'move_result']
            check(bool(mv) and mv[-1]['ok'] and mv[-1]['dir'] == 'north', 'walking through the opened door')
            await tn.cmd('webmove 2513 2512 south', 1.0)
            # leave it as the zone keeps it (open, unlocked), without our key
            for line in ('drop key', 'purge'):
                await tn.cmd(line, 0.5)
            pumper.cancel()
    tn.w.close()


async def main():
    await offline()
    if server_up():
        await live()
    else:
        print('skip live checks: no server on', tw.HOST, tw.TELNET)
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
