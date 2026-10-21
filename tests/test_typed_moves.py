"""In /play you walk (WASD, the arrow keys, a click: `webmove`); a direction typed into the game's
text box does not move you. Telnet, and the plain web page, still move by typing.

Offline: `n`, `north`, `up`... from a /play player (a web connection with a 3D position) are
refused with how to walk instead; the same from telnet, from the plain web page (no 3D position)
or from a /play player who came back by telnet still move; `webmove` is not a typed direction.
    python3 tests/test_typed_moves.py
"""
import asyncio
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
from commands import CommandHandler  # noqa: E402

failures = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        failures.append(what)


class Body:
    def __init__(self, web, pos):
        self.connection = types.SimpleNamespace(is_web=web)
        self.web_pos = (3001, 5.0, 5.0) if pos else None
        self.said = []

    async def send(self, text):
        self.said.append(text)


async def main():
    moved = []

    async def fake_move(cls, player, direction):
        moved.append(direction)

    real = CommandHandler.cmd_move
    CommandHandler.cmd_move = classmethod(fake_move)
    try:
        for name, web, pos, walks in [('/play', True, True, False), ('telnet', False, False, True),
                                      ('the plain web page', True, False, True),
                                      ('a /play player back by telnet', False, True, True)]:
            for cmd, d in [('cmd_north', 'north'), ('cmd_south', 'south'), ('cmd_east', 'east'),
                           ('cmd_west', 'west'), ('cmd_up', 'up'), ('cmd_down', 'down')]:
                moved.clear()
                p = Body(web, pos)
                await getattr(CommandHandler, cmd)(p, [])
                if walks:
                    check(moved == [d], f'{name}: typed {d} moves')
                else:
                    check(not moved and any('WASD' in s for s in p.said), f'{name}: typed {d} is refused with how to walk')
        check(CommandHandler.COMMAND_ALIASES.get('n') == 'north' or CommandHandler.ALIASES.get('n') == 'north',
              '`n` is still north (refused in /play by cmd_north)')
        # `move north` typed: the words come as a list; refused in /play, moves on telnet
        for name, web, pos, walks in [('/play', True, True, False), ('telnet', False, False, True)]:
            moved.clear()
            p = Body(web, pos)
            await real.__func__(CommandHandler, p, ['north'])
            if walks:
                check(moved == ['north'], f'{name}: typed `move north` moves')
            else:
                check(not moved and any('WASD' in s for s in p.said), f'{name}: typed `move north` is refused with how to walk')
    finally:
        CommandHandler.cmd_move = real
    # what the dispatcher does with a typed word that is a direction, or a part of one, or an exit's
    # name: the same refusal in /play (typed_move), never straight to cmd_move
    disp = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'commands.py'), encoding='utf-8').read()
    fallback = disp[disp.index("# Check if it's a direction"):disp.index("is not a valid command. Type 'help'")]
    check('cmd_move(' not in fallback and fallback.count('typed_move(') == 5,
          'a typed direction, part of one, or an exit\'s name goes through typed_move')
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'commands.py'), encoding='utf-8').read()
    body = src[src.index('async def cmd_webmove'):src.index('async def cmd_webmove') + 4000]
    check('typed_move' not in body and 'cmd_move' in body, '`webmove` (how /play walks) goes straight to cmd_move')
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
