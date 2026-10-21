#!/usr/bin/env python3
"""What /play draws for itself instead of reading it in the log (web_hud.py, msgkind.UI).

- a line the HUD also shows is marked 'ui' for a web page (the log keeps it, dimmed), never for
  telnet;
- hunger and thirst drain one point a game hour (not two), only for hours lived through: a new
  character, one back from away, a month turning over drain nothing;
- the clock carries its season and moon, the sky its description; the page hears of the body
  (posture, needs, a breath, mail) only when it changed, and of the clock and sky when they turn;
- a world event shows as a chip: what, where, how long.

    python3 tests/test_web_hud.py
"""
import asyncio
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
import test_webmove as tw  # noqa: E402
import test_atlas_engine as tae  # noqa: E402

check, failures = tw.check, tw.failures


class Writer:
    def __init__(self):
        self.data = b''

    def write(self, b):
        self.data += b

    async def drain(self):
        pass


class Client:
    def __init__(self, name):
        self.player_name = name


class FakeMap:
    def __init__(self, names):
        self.clients = {Client(n) for n in names}
        self.events = []

    def has_play(self, p):
        return any(c.player_name.lower() == p.name.lower() for c in self.clients)

    async def notify_event(self, p, ev):
        self.events.append((p.name, ev))


async def main():
    import logging
    logging.disable(logging.WARNING)
    from config import Config
    Config.PLAYER_DIR = tempfile.mkdtemp()
    import msgkind
    import server
    import web_hud

    # ---- the ui kind: every line with text, for a web page only
    marked = msgkind.mark('The sun rises on the eastern horizon.\n\nYou are hungry.', msgkind.UI)
    check(marked.count('\x1b]K:ui\x07') == 2, 'a ui message marks each of its lines that has text')
    check(msgkind.mark('You gain 209 experience points!').startswith('\x1b]K:reward'), 'the kinds read from a line are unchanged')
    for web in (True, False):
        conn = server.Connection.__new__(server.Connection)
        conn.is_web, conn.state, conn.writer, conn.address = web, server.Connection.STATE_PLAYING, Writer(), 'test'
        await conn.send('Night falls across the land.', kind=msgkind.UI)
        has = b'\x1b]K:ui\x07' in conn.writer.data
        check(has == web, f"{'a web page gets' if web else 'telnet never gets'} the ui mark")

    from world import World
    from player import Player
    world = World(Config())
    await world.load()
    gt = world.game_time

    def hero(name, at=3001):
        h = Player.create_new(name=name, password=None, race='human', char_class='warrior',
                              stats={s: 13 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
        h.connection = tae.Conn()
        h.room = world.rooms[at]
        world.rooms[at].characters.append(h)
        world.players[name.lower()] = h
        return h

    # ---- hunger: one point an hour, the hours lived through
    h = hero('Eater')
    h.hunger, h.thirst = 100, 50
    gt.hour, gt.day, gt.month, gt.tick_counter = 10, 20, 6, 0
    await h.hunger_thirst_tick()
    check((h.hunger, h.thirst) == (100, 50), f'a new character drains nothing on its first tick ({h.hunger}, {h.thirst})')
    for _ in range(gt.SECONDS_PER_MUD_HOUR):
        await world.time_tick()
    await h.hunger_thirst_tick()
    check((h.hunger, h.thirst) == (99, 49), f'one game hour costs one point of each, not two ({h.hunger}, {h.thirst})')
    gt.hour, gt.day, gt.month = 23, 30, 6
    h.last_hunger_hour = h.last_thirst_hour = gt.total_hours()
    gt.hour, gt.day, gt.month = 0, 1, 7
    await h.hunger_thirst_tick()
    check((h.hunger, h.thirst) == (98, 48), f'the hour across a new month counts once ({h.hunger}, {h.thirst})')
    h.last_hunger_hour = h.last_thirst_hour = gt.total_hours() - 300
    await h.hunger_thirst_tick()
    check((h.hunger, h.thirst) == (98, 48), 'a player back from long away starts counting from now')
    h.hunger = 25
    h.last_hunger_hour -= 1
    h.connection = server.Connection.__new__(server.Connection)
    h.connection.is_web, h.connection.state, h.connection.writer, h.connection.address = True, server.Connection.STATE_PLAYING, Writer(), 'test'
    await h.hunger_thirst_tick()
    check(b'\x1b]K:ui\x07' in h.connection.writer.data and b'extremely hungry' in h.connection.writer.data,
          'the hunger warning reaches the page marked ui')
    h.connection = tae.Conn()

    # ---- the blocks
    sky = web_hud.sky_block(h)
    check({'hour', 'period', 'season', 'moon', 'month_name', 'light'} <= set(sky['time']), f"the clock has its season and moon ({sorted(sky['time'])})")
    check(sky['weather'].get('desc'), f"the sky comes with its description ({sky['weather'].get('desc')})")
    check(0 <= sky['time']['moon'] < 1, 'the moon is a phase between new and new')
    body = web_hud.body_block(h)
    check({'hunger', 'max_hunger', 'thirst', 'max_thirst', 'position', 'breath', 'mail', 'hunger_state'} <= set(body),
          f'the body block has the needs, the posture, a breath, mail ({sorted(body)})')

    import map_system
    h.explored_rooms = {h.room.vnum}
    payload = map_system.build_map_payload(h, mode='zone')
    check(payload['time'].get('season') and 'moon' in payload['time'] and payload['weather'].get('desc'),
          'the map payload starts the page with the season, the moon, the sky described')
    check('hunger' in payload['player'] and 'world_events' in payload, 'the map payload carries the body and the world events')

    # ---- pushes: the body when it changed, the sky to every page
    other = hero('Elsewhere')
    wm = FakeMap(['Eater', 'Elsewhere'])
    world.web_map = wm
    await web_hud.tick(world)
    vit = [e for n, e in wm.events if e['type'] == 'vitals']
    check(len(vit) == 2, f'each page hears of its body once ({len(vit)})')
    wm.events.clear()
    await web_hud.tick(world)
    check(not [e for n, e in wm.events if e['type'] == 'vitals'], 'nothing changed, nothing sent')
    h.position = 'sitting'
    await web_hud.tick(world)
    sent = [e for n, e in wm.events if e['type'] == 'vitals']
    check(len(sent) == 1 and sent[0]['player']['position'] == 'sitting', 'sitting down tells the page')
    wm.events.clear()
    await web_hud.push_sky(world)
    ticks = [e for n, e in wm.events if e['type'] == 'world_tick']
    check(len(ticks) == 2 and all('season' in e['time'] for e in ticks), f'the hour turning reaches every page ({len(ticks)})')

    # ---- world events: a chip with what, where, how long
    from world_events import WorldEventManager, DoubleXPEvent
    world.event_manager = em = getattr(world, 'event_manager', None) or WorldEventManager(world)
    em.active_events = [DoubleXPEvent(world)]
    rows = web_hud.events_block(world)
    check(rows and rows[0]['kind'] == 'double_xp' and rows[0]['left'] > 0 and rows[0]['label'], f'double experience is a chip ({rows})')
    wm.events.clear()
    world._hud_events = None
    await web_hud.push_events(world)
    await web_hud.push_events(world)
    check(len([e for n, e in wm.events if e['type'] == 'world_event']) == 2, 'an event starting tells each page once')
    em.active_events = []
    world.web_map = None

    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
