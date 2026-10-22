"""Whatever moves a player, /play follows, offline (Player.sync_room).

    python3 tests/test_relocate.py

The owner: "when I cast teleport and I moved to a new room the UI didn't update visually". The
teleport spell (and other spells and commands) moved the caster by hand and never told the 3D
client; now every command ends by checking the room the client last saw.
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


class FakeMap:
    def __init__(self):
        self.sent = []

    async def notify_player(self, p):
        self.sent.append(p.room.vnum)
        p._web_last_vnum = p.room.vnum

    async def notify_room(self, *a, **k):
        pass

    async def notify_event(self, *a, **k):
        pass

    def has_play(self, p):
        return True


async def main():
    import logging
    logging.disable(logging.WARNING)
    from config import Config
    Config.PLAYER_DIR = tempfile.mkdtemp()
    from world import World
    from player import Player
    from commands import CommandHandler
    import test_atlas_engine as tae
    world = World(Config())
    await world.load()
    world.web_map = fm = FakeMap()
    h = Player.create_new(name='Blinker', password=None, race='human', char_class='mage',
                          stats={s: 13 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    h.connection = tae.Conn()
    h.room = world.rooms[3001]
    world.rooms[3001].characters.append(h)
    h._web_last_vnum = 3001

    async def cmd_blink(cls, player, args):        # a spell that moves its caster by hand, as teleport did
        player.room.characters.remove(player)
        player.room = world.rooms[3014]
        player.room.characters.append(player)
    CommandHandler.cmd_zzblink = classmethod(cmd_blink)
    await h.execute_command('zzblink', [])
    check(fm.sent == [3014] and 3014 in h.explored_rooms, f'moved by a command: the 3D client is sent the new room ({fm.sent})')
    await h.execute_command('look', [])
    check(fm.sent == [3014], 'a command that does not move you sends nothing more')
    # slain in a creature's round (no command of yours runs): /play is still sent the temple
    temple = h.recall_room()
    await h.die(None)
    check(h.room is temple and temple.vnum != 3014 and fm.sent == [3014, temple.vnum],
          f'killed: the 3D client is sent the temple you wake in ({fm.sent})')
    # the teleport spell itself
    from spells import SpellHandler
    import inspect
    src = inspect.getsource(SpellHandler)
    check("special == 'teleport'" in src, 'the teleport spell is still there to be covered')
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
