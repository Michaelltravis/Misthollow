"""A mage's look, offline: asked at creation after the class (telnet, and the 3D client's wizard
answers the same prompt), kept with the character, sent in the look as `style` (the archmage's
Blender pieces, gearlook.js), only for a mage, and changed any time with `appearance`.

    python3 tests/test_archmage_look.py
"""
import asyncio
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
import test_webmove as tw  # noqa: E402

check, failures = tw.check, tw.failures
STATS = {s: 13 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}


async def main():
    import logging
    logging.disable(logging.WARNING)
    from config import Config
    Config.PLAYER_DIR = tempfile.mkdtemp()
    from world import World
    from player import Player
    from server import Connection
    from commands import CommandHandler
    import gear_look
    import test_atlas_engine as tae
    world = World(Config())
    await world.load()

    def connection(name):
        conn = Connection.__new__(Connection)
        conn.config, conn.world, conn.account, conn.player = world.config, world, None, None
        conn.temp_name, conn.temp_password, conn.temp_race, conn.temp_sex, conn.temp_class = name, None, 'human', 'male', None
        out = []

        async def send(message='', newline=True):
            out.append(str(message))
        conn.send = send
        conn.state = conn.STATE_GET_CLASS
        return conn, out

    # ---- creation: a mage is asked which look; anyone else goes straight to the stats
    conn, out = connection('Merlo')
    await conn.handle_input('mage')
    check(conn.state == conn.STATE_GET_STYLE and 'classic or archmage' in ' '.join(out[-3:]).lower(), 'a mage: classic or archmage?')
    out.clear()
    await conn.handle_input('wizardy')
    check(conn.state == conn.STATE_GET_STYLE and 'classic or archmage' in ' '.join(out).lower(), 'anything else asks again')
    await conn.handle_input('2')
    check(conn.temp_style == 'archmage' and conn.state == conn.STATE_ROLLING_STATS, 'then the stats (2 is the archmage)')
    other, _ = connection('Brann')
    await other.handle_input('warrior')
    check(other.state == other.STATE_ROLLING_STATS, 'a warrior is not asked')

    # ---- kept with the character, and in the look (only a mage's)
    merlo = Player.create_new(name='Merlo', password=None, race='human', char_class='mage', world=world, stats=STATS,
                              sex='male', look_style=conn.temp_style)
    await merlo.save()
    back = Player.load('Merlo', world)
    check(back is not None and back.look_style == 'archmage', f'saved and loaded ({getattr(back, "look_style", None)})')
    check(gear_look.look_of(back).get('style') == 'archmage', 'the look carries it (the archmage pieces)')
    odd = Player.create_new(name='Odd', password=None, race='human', char_class='warrior', world=world, stats=STATS,
                            look_style='archmage')
    check('style' not in gear_look.look_of(odd), 'not a mage: no archmage look')
    plain = Player.create_new(name='Plain', password=None, race='human', char_class='mage', world=world, stats=STATS)
    check(plain.look_style == '' and 'style' not in gear_look.look_of(plain), 'a mage made without choosing: the classic look')

    # ---- appearance: changed any time, and the look follows
    back.connection = tae.Conn()
    back.room = world.rooms.get(3001)
    sig = gear_look.look_of(back)['sig']
    await CommandHandler.cmd_appearance(back, [])
    check('archmage look' in tae.said(back, 1), 'appearance: says which look')
    await CommandHandler.cmd_appearance(back, ['classic'])
    check(back.look_style == '' and 'style' not in gear_look.look_of(back) and gear_look.look_of(back)['sig'] != sig,
          'appearance classic: the classic look again')
    await CommandHandler.cmd_appearance(back, ['bunny'])
    check(back.look_style == '', 'only the looks there are')
    await CommandHandler.cmd_appearance(back, ['archmage'])
    check(back.look_style == 'archmage', 'appearance archmage')
    odd.connection = tae.Conn()
    odd.room = world.rooms.get(3001)
    await CommandHandler.cmd_appearance(odd, ['archmage'])
    check(odd.look_style == 'archmage' and 'one look' in tae.said(odd, 1), 'a warrior has one look')
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


asyncio.run(main())
