"""/play's menus and dialogue in its own words, not a telnet terminal's.

Offline: quest_guide.web_line turns every '(type "x")' hint in a line into how to do it with the
HUD, in either quote, more than one to a line, ANSI colours kept; "Type 'journal' to ..." becomes
"Open your Journal (L) to ..."; a hint /play has no window for, and ordinary words, stay as they
are; the web connection sends lines through it (server.Connection.send) and a telnet one does
not; the journal's discovery box is one line on the web.
    python3 tests/test_web_menus.py
"""
import asyncio
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import quest_guide  # noqa: E402

failures = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        failures.append(what)


w = quest_guide.web_line
check(w('Quest Progress: Speak with Sage Aldric (type "talk aldric") (1/1)')
      == 'Quest Progress: Speak with Sage Aldric: right-click them, then Talk (1/1)', 'a (type "talk ...") hint: right-click them, then Talk')
check(w("Check your score (type 'score')") == 'Check your score: open your Character sheet (C)', "single quotes too")
check(w('Look around (type "look"), then rest (type "rest")') == 'Look around: right-click it, then Look, then rest: right-click yourself, then Rest', 'every hint in a line')
check(w("\x1b[36m  Type 'journal' to view your discoveries.\x1b[0m") == "\x1b[36m  Open your Journal (L) to view your discoveries.\x1b[0m", "Type 'journal' to ...: Open your Journal (L) to ..., colours kept")
check(w("Type 'talk aldric' to begin.") == "Right-click them, then Talk to begin.", "Type 'talk aldric' to ...: the HUD's way")
check(w('He is right here. Simply type "talk aldric" to speak with him.') == 'He is right here. Simply right-click them, then Talk to speak with him.',
      'a quest\'s "simply type "talk aldric" to ...": the HUD\'s way, in lower case mid-sentence')
check(w("Type 'channel list' to see them.") == "Type 'channel list' to see them.", 'a command whose /play way is itself typing stays')
check(w("Type 'bake' to bake.") == "Type 'bake' to bake.", 'a command /play has no other way for stays')
check(w("Type 'achievements all' to see 54 unearned achievements.") == 'Open your Almanac (Y) to see 54 unearned achievements.', 'achievements: the Almanac (Y)')
check(w("\r\n\x1b[37mType 'achievements all' to see 54.\x1b[0m") == "\r\n\x1b[37mOpen your Almanac (Y) to see 54.\x1b[0m",
      'right after a colour code too (its m is no word edge)')
check(w("Quest accepted! Use 'quests' to track objectives.") == 'Quest accepted! Open your Journal (L) to track objectives.', "Use 'quests' to ...: the Journal (L)")
check(w("Use the lever to open the gate.") == "Use the lever to open the gate.", 'the word "use" in a sentence stays')
check(w("waiter says, 'Welcome! Type LIST to see my wares.'") == "waiter says, 'Welcome! Right-click the shopkeeper, then Shop to see my wares.'",
      "a shopkeeper's Type LIST: right-click, then Shop")
check(w('TYPE NOTHING here') == 'TYPE NOTHING here', 'capitals that are not a command stay')
check(w('Try the bread (type "bake bread")') == 'Try the bread (type "bake bread")', 'a command /play has no other way for stays')
for plain in ['You gain 50 experience!', 'Sage Aldric says, "Try the fountain."', 'The prototype engine hums.', '']:
    check(w(plain) == plain, f'plain words stay: {plain!r}')

import server  # noqa: E402


class Writer:
    def __init__(self):
        self.out = b''

    def write(self, b):
        self.out += b

    async def drain(self):
        pass


async def sent(is_web, text):
    conn = server.Connection.__new__(server.Connection)
    conn.writer, conn.is_web, conn.state = Writer(), is_web, server.Connection.STATE_PLAYING
    await conn.send(text)
    return conn.writer.out.decode('utf-8')


hint = 'Speak with Sage Aldric (type "talk aldric")'
check('right-click them, then Talk' in asyncio.run(sent(True, hint)), 'a web connection sends the /play wording')
check('(type "talk aldric")' in asyncio.run(sent(False, hint)), 'a telnet connection keeps the telnet hint')

from journal import JournalManager  # noqa: E402


class P:
    def __init__(self, web):
        self.connection = types.SimpleNamespace(is_web=web)
        self.config = types.SimpleNamespace(COLORS=__import__('collections').defaultdict(str))
        self.said = []

    async def send(self, text=''):
        self.said.append(text)


for web in (True, False):
    p = P(web)
    asyncio.run(JournalManager.show_discovery(p, {'category': 'npc', 'title': 'Sage Aldric'}))
    if web:
        check(p.said == ['New in your journal: Sage Aldric (notable figure encountered)'], f'web: the discovery is one line ({p.said})')
    else:
        check(any('*NPC*' in s for s in p.said) and any("Type 'journal'" in s for s in p.said), 'telnet: the discovery keeps its box')

# `achievements` answers (it read its definitions as dicts and failed: "Something went wrong")
from commands import CommandHandler  # noqa: E402
from achievements import ACHIEVEMENTS  # noqa: E402

first = next(iter(ACHIEVEMENTS))
for args in ([], ['all'], ['progress']):
    p = P(True)
    p.achievements = {first: {'unlocked_at': 'now'}}
    p.achievement_progress = {'kills': 3}
    p.explored_rooms, p.secret_rooms_found = set(), set()
    try:
        asyncio.run(CommandHandler.cmd_achievements(p, args))
        ok = any('ACHIEVEMENTS' in s for s in p.said)
    except Exception as e:  # noqa: BLE001
        ok, p.said = False, [repr(e)]
    check(ok, f'achievements {" ".join(args)}: answers ({p.said[-1][:60] if p.said else ""})')
p = P(True); p.achievements = {first: {}}; p.achievement_progress = {}
asyncio.run(CommandHandler.cmd_achievements(p, []))
check(any(ACHIEVEMENTS[first].name in s for s in p.said), f'an earned one is listed by its name ({ACHIEVEMENTS[first].name})')

# the web bridge (web_client.py) puts back together what the read cut in two: a colour code
# ("\x1b[3" | "7m" printed as is in `commands`), a box character (three bytes), a line
import web_client  # noqa: E402


async def bridged(pieces, gap=0.0):
    sent = []
    ws = types.SimpleNamespace(send_json=lambda m: sent.append(m) or asyncio.sleep(0))
    br = web_client.TelnetBridge.__new__(web_client.TelnetBridge)
    br.ws, br.reader = ws, asyncio.StreamReader()

    async def feed():
        for piece in pieces:
            br.reader.feed_data(piece)
            await asyncio.sleep(gap)
        br.reader.feed_eof()
    await asyncio.gather(br.read_loop(), feed())
    outs = [m['data'] for m in sent if m.get('type') == 'output']
    bridged.messages = len(outs)
    return ''.join(outs)


line = '\x1b[37mstrike  summon\x1b[0m\r\n'.encode()
out = asyncio.run(bridged([line[:3], line[3:]]))
check('\x1b' not in out and 'ansi-white' in out and 'strike  summon' in out, f'a colour code cut in two is whole ({out[:80]!r})')
box = '║ TUTORIAL ║\r\n'.encode()
out = asyncio.run(bridged([box[:1], box[1:]]))
check('║ TUTORIAL ║' in out and '�' not in out, f'a box character cut in two is whole ({out!r})')
out = asyncio.run(bridged([b'You are carry', b'ing:\r\n'], gap=0.01))
check('You are carrying:' in out and bridged.messages == 1, f'a line cut in two goes as one message ({bridged.messages}: {out!r})')
out = asyncio.run(bridged([b'20/20hp> '], gap=0.2))
check('20/20hp&gt;' in out or '20/20hp>' in out, f'a prompt, which ends no line, still goes ({out!r})')

print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
sys.exit(1 if failures else 0)
