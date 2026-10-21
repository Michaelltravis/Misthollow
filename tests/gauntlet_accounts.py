"""The live suites' test characters, made through the game's own sign-up when they are missing.

Two admin accounts, password gauntlet1 (tools/gauntlet/README.md): `gauntlet` (Gauntlet, and the
assassin Probeassn) and `gauntletb` (Gauntletb, a level-6 warrior, and a Probe* character of each
other class). Only what is missing is made, so a run on a machine that has them changes nothing:
a new name signs up over telnet (the account and its first character, of the same name), the
rest are made from the account menu; the admin flag has no in-game switch and is set in the
account file, as the README does.
    python3 tests/gauntlet_accounts.py
"""
import asyncio
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
import test_webmove as tw  # noqa: E402  (HOST, TELNET)

PASSWORD = 'gauntlet1'
ACCOUNTS = {'gauntlet': [('Gauntlet', 'warrior'), ('Probeassn', 'assassin')],
            'gauntletb': [('Gauntletb', 'warrior'), ('Probemage', 'mage'), ('Probecleric', 'cleric'),
                          ('Probepaladin', 'paladin'), ('Probenecro', 'necromancer'), ('Probethief', 'thief'),
                          ('Proberanger', 'ranger'), ('Probebard', 'bard')]}
LEVELS = {'Gauntletb': 6}
ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x07]*\x07')


def _paths():
    import accounts
    from config import Config
    return accounts.ACCOUNTS_DIR, Config.PLAYER_DIR


def saved(name):
    """A character's save as the server last wrote it (None: no such character)."""
    try:
        with open(os.path.join(_paths()[1], f'{name.lower()}.json'), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


class _Session:
    async def open(self):
        self.r, self.w = await asyncio.open_connection(tw.HOST, tw.TELNET)
        await self.read(1.5)
        return self

    async def read(self, secs):
        out = ''
        end = asyncio.get_event_loop().time() + secs
        while (left := end - asyncio.get_event_loop().time()) > 0:
            try:
                data = await asyncio.wait_for(self.r.read(65536), timeout=left)
            except asyncio.TimeoutError:
                break
            if not data:
                break
            out += data.decode(errors='ignore')
        return ANSI.sub('', out)

    async def cmd(self, line, secs=0.8):
        self.w.write((line + '\r\n').encode())
        await self.w.drain()
        return await self.read(secs)

    async def close(self):
        await self.cmd('quit', 1.0)
        self.w.close()


async def _build(s, cls):
    """Race, sex, class (a mage also picks a look), stats: the sign-up's questions."""
    for line in ('human', 'male', cls) + (('classic',) if cls == 'mage' else ()):
        await s.cmd(line, 0.6)
    return await s.cmd('y', 2.5)


async def ensure(verbose=True):
    """Make whatever test account or character is missing; returns what was made."""
    from accounts import Account
    acct_dir, _ = _paths()
    made = []
    for acct, chars in ACCOUNTS.items():
        first, first_cls = chars[0]
        if not Account.exists(acct) and saved(first) is None:
            # a new name: the sign-up makes the account and its first character together (an
            # older save of that name was given its account by the server's start, accounts.py)
            s = await _Session().open()
            await s.cmd(first, 1.0)
            for line in ('y', PASSWORD, PASSWORD):
                await s.cmd(line, 0.8)
            await _build(s, first_cls)
            await s.close()
            made.append(f'account {acct} ({first})')
        for name, cls in chars[1:]:
            if saved(name) is not None:
                continue
            s = await _Session().open()
            await s.cmd(acct, 1.0)
            await s.cmd(PASSWORD, 1.5)
            await s.cmd('create', 0.8)
            await s.cmd(name, 0.8)
            await _build(s, cls)
            await s.close()
            made.append(f'{name} ({cls}, on {acct})')
        # the wizard commands the suites use (goto, set, mload, ...): no in-game switch makes an
        # admin, so the account file says so (after every session above has saved its copy)
        a = Account.load(acct)
        if a is not None and not a.is_admin:
            a.is_admin = True
            a.save()
            made.append(f'{acct} made admin')
    for name, level in LEVELS.items():
        p = saved(name)
        if p is not None and p.get('level', 1) < level:
            acct = next(a for a, chars in ACCOUNTS.items() if any(n == name for n, _c in chars))
            s = await _Session().open()
            for line in (acct, PASSWORD, f'play {name}', f'advance {name.lower()} {level}', 'save'):
                await s.cmd(line, 1.2)
            await s.close()
            made.append(f'{name} advanced to {level}')
    missing = [n for chars in ACCOUNTS.values() for n, _c in chars
               if (saved(n) or {}).get('account_name', '').lower() not in ACCOUNTS]
    if verbose and made:
        print('test accounts: made ' + '; '.join(made))
    if missing:
        print('test accounts: could not make ' + ', '.join(missing))
    return made


if __name__ == '__main__':
    asyncio.run(ensure())
