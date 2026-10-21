"""Security: password hashing, the account-character way in, sign-in tokens, login throttling,
the admin dashboard, and the small leaks (echoes, logs, the bridge).

Offline checks always run (temporary player/account folders, a fake connection):
    python3 tests/test_security.py
Live checks run too when a server is up (./run.sh) with the gauntlet accounts
(tools/gauntlet/README.md) and their Probe* characters: the old "account_protected" way in is
shut, a throwaway character (Sectest) checks wrong-password limits and sign-in tokens over
telnet and through the web bridge, and the dashboard refuses requests without its key.
"""
import asyncio
import hashlib
import json
import os
import re
import shutil
import socket
import sys
import tempfile
import time
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import test_webmove as tw  # noqa: E402  (check(), failures, hosts)
import gauntlet_accounts  # noqa: E402  (the test characters, made if missing)
from config import Config  # noqa: E402
import security  # noqa: E402
import accounts  # noqa: E402

check, failures = tw.check, tw.failures
SENTINEL = hashlib.sha256(b'account_protected').hexdigest()
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


# ---------------------------------------------------------------- offline
class FakeWriter:
    def __init__(self):
        self.out = bytearray()
        self.closed = False

    def write(self, b):
        self.out += b

    async def drain(self):
        pass

    def get_extra_info(self, _k):
        return ('127.0.0.1', 5555)

    def close(self):
        self.closed = True

    def is_closing(self):
        return self.closed

    def text(self):
        t = self.out.decode(errors='ignore')
        self.out.clear()
        return t


def connection():
    import server
    world = types.SimpleNamespace(players={}, get_room=lambda v: None)
    srv = types.SimpleNamespace(world=world, config=Config())
    w = FakeWriter()
    return server.Connection(None, w, srv), w


async def offline(tmp):
    # hashing
    h = security.hash_password('correct horse')
    check(h.startswith('pbkdf2_sha256$600000$') and len(h.split('$')) == 4, 'new hashes are salted PBKDF2-SHA256')
    check(security.hash_password('correct horse') != h, '…with a fresh salt each time')
    check(security.verify(h, 'correct horse') == (True, False), 'the right password verifies, no re-hash needed')
    check(security.verify(h, 'wrong horse') == (False, False), 'a wrong one does not')
    old = hashlib.sha256(b'oldpass1').hexdigest()
    check(security.verify(old, 'oldpass1') == (True, True), 'an old unsalted hash still verifies and asks to be upgraded')
    check(security.verify(SENTINEL, 'account_protected') == (False, False), 'the old "account_protected" hash never matches')
    check(security.verify('', 'anything') == (False, False) and security.verify(h, '') == (False, False),
          'an empty hash or an empty password never matches')
    check(security.verify('pbkdf2_sha256$x$y$z', 'a') == (False, False), 'a damaged hash is a refusal, not a crash')
    check(security.weak('short') and not security.weak('longenough'), 'new passwords need 8 characters')

    # accounts: the upgrade on login, set_password forgets devices, hashed reset tokens
    accounts.ACCOUNTS_DIR = os.path.join(tmp, 'accounts')
    security.TOKENS_FILE = os.path.join(tmp, 'resume_tokens.json')
    security._store = None
    a = accounts.Account('oldacct')
    a.password_hash = hashlib.sha256(b'oldpass1').hexdigest()
    a.characters = ['Oldie']
    a.save()
    got = await accounts.AccountManager.authenticate('oldacct', 'oldpass1')
    check(got is not None, 'an account with an old hash logs in')
    check(accounts.Account.load('oldacct').password_hash.startswith('pbkdf2_sha256$'), '…and its hash is upgraded on disk')
    check(await accounts.AccountManager.authenticate('oldacct', 'nope') is None, 'a wrong account password is refused')
    tok = security.issue_token('Oldie')
    acct = accounts.Account.load('oldacct')
    await acct.set_password('brandnewpass')
    acct.save()
    check(security.use_token('Oldie', tok) is None, "a password change forgets every device of the account's characters")
    reset = accounts.AccountManager.generate_reset_token(acct)
    raw = open(os.path.join(accounts.ACCOUNTS_DIR, 'oldacct.json')).read()
    check(reset not in raw and '"hash"' in raw, 'a reset token is stored hashed, never as itself')
    check(not await accounts.AccountManager.reset_with_token('oldacct', reset, 'short'), 'a reset to a weak password is refused')
    reset = accounts.AccountManager.generate_reset_token(accounts.Account.load('oldacct'))
    check(await accounts.AccountManager.reset_with_token('oldacct', reset, 'resetpass1'), 'a reset token resets the password')
    check(not await accounts.AccountManager.reset_with_token('oldacct', reset, 'resetpass2'), '…once')
    check(await accounts.AccountManager.authenticate('oldacct', 'resetpass1') is not None, '…to the new one')

    # sign-in tokens
    security._store = None
    t1 = security.issue_token('Sample')
    t2 = security.use_token('Sample', t1)
    check(bool(t2) and t2 != t1, 'a sign-in token works once and is swapped for a fresh one')
    check(security.use_token('Sample', t1) is None, '…the old one no longer works')
    check(security.use_token('Sample', 'x' * 43) is None and security.use_token('Nobody', t2) is None,
          'a made-up token, or one for another name, is refused')
    stored = open(security.TOKENS_FILE).read()
    check(t2 not in stored and hashlib.sha256(t2.encode()).hexdigest() in stored, 'tokens are kept as hashes only')
    if os.name == 'nt':
        # os.chmod on Windows sets only the read-only bit: the mode always reads 0o666
        print('skip …in a file only the server can read (Unix file modes: none on Windows)')
    else:
        check(oct(os.stat(security.TOKENS_FILE).st_mode & 0o777) == '0o600', '…in a file only the server can read')
    many = [security.issue_token('Sample') for _ in range(6)]
    check(len(security._load()['sample']) == security.TOKEN_DEVICES, 'at most five devices a character')
    check(security.use_token('Sample', t2) is None and security.use_token('Sample', many[0]) is None,
          '…the oldest drop out first')
    for r in security._load()['sample']:
        r['exp'] = time.time() - 1
    check(security.use_token('Sample', many[-1]) is None, 'an expired token is refused')
    t3 = security.issue_token('Sample')
    check(security.forget_token('Sample', t3) and security.use_token('Sample', t3) is None, 'forget signs one browser out')
    t4 = security.issue_token('Sample')
    security.forget_all('Sample')
    check(security.use_token('Sample', t4) is None, 'forget_all signs every browser out')
    sig = security.resume_signal('abc_DEF-123')
    check(sig == b'\x1b]RESUME:abc_DEF-123\x07', 'the RESUME signal is a raw OSC sequence')

    # throttling
    for _ in range(security.NAME_FAILS - 1):
        security.failed('Victim')
    check(security.locked('Victim') == 0, 'four failures do not lock a name')
    security.failed('Victim')
    check(security.locked('victim') > 0, 'the fifth within ten minutes locks it')
    security._locked.clear()
    check(security.forgot_allowed('acct1') and not security.forgot_allowed('acct1'), 'one reset mail an account per 15 minutes')

    # the login prompts, with a fake connection
    Config.PLAYER_DIR = os.path.join(tmp, 'players')
    os.makedirs(Config.PLAYER_DIR, exist_ok=True)
    owner = accounts.Account('keeper')
    await owner.set_password('keeperpass')
    owner.characters = ['Ward']
    owner.save()
    with open(os.path.join(Config.PLAYER_DIR, 'ward.json'), 'w') as f:
        json.dump({'name': 'Ward', 'password_hash': SENTINEL, 'account_name': 'keeper'}, f)
    conn, w = connection()
    await conn.handle_name('Ward')
    out = w.text()
    check(conn.state == conn.STATE_ACCOUNT_PASSWORD and conn.play_after == 'Ward' and 'belongs to an account' in out,
          "a character on an account, typed by name, asks for the account's password")
    await conn.handle_account_password('account_protected')
    out = w.text()
    check(conn.account is None and 'Invalid password' in out and conn.state == conn.STATE_GET_NAME,
          '"account_protected" no longer opens it')
    check(conn.login_failures == 1, '…and counts as a failed login')
    for _ in range(2):
        await conn.handle_name('Ward')
        await conn.handle_account_password('wrongpass')
    check(w.closed and 'Too many failed attempts' in w.text(), 'three wrong passwords close the connection')
    security._fails.clear()
    security._locked.clear()

    # a resume with a bad token at the name prompt
    conn, w = connection()
    await conn.handle_name('resume Ward ' + 'y' * 43)
    check('sign-in has expired' in w.text() and conn.player is None, 'resume with an unknown token is refused')

    # lines that carry a password
    import server
    sl = server.Connection._secret_line
    check(sl('account password old new') == 'account password ****' and sl('account recover tok newpw1') == 'account recover ****'
          and sl('account reset bob newpw1') == 'account reset ****', 'account password lines are masked')
    check(sl('say my password is fish') == '' and sl('account') == '', '…other lines are not')

    # the bridge reads a bare number as text, not as a crash
    import web_client
    check(web_client.RESUME_PATTERN.search('x\x1b]RESUME:abc-DEF_1\x07y').group(1) == 'abc-DEF_1', 'the bridge finds RESUME')

    # log redaction
    import web_map
    check(web_map._redact('/state?player=Bob&t=SECRET123&mode=near') == '/state?player=Bob&t=…&mode=near',
          'the map server logs paths without their session token')
    import admin_dashboard
    check('SECRET' not in admin_dashboard.redact("path='/state?player=Bob&t=SECRET' \x1b]MAPSYNC:Bob:SECRET\x07 RESUME:SECRET"),
          'the dashboard shows log lines without tokens or signals')


# ---------------------------------------------------------------- live
def server_up():
    try:
        with socket.create_connection((tw.HOST, tw.TELNET), timeout=1):
            return True
    except OSError:
        return False


class Raw:
    """A telnet session that keeps the raw bytes (the hidden signals)."""
    async def open(self):
        self.r, self.w = await asyncio.open_connection(tw.HOST, tw.TELNET)
        await self.read(1.2)
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
                self.eof = True
                break
            out += data.decode(errors='ignore')
        return out

    async def cmd(self, line, secs=0.8):
        self.w.write((line + '\r\n').encode())
        await self.w.drain()
        return await self.read(secs)

    def close(self):
        try:
            self.w.close()
        except Exception:
            pass


RESUME = re.compile(r'\x1b\]RESUME:([A-Za-z0-9_\-]+)\x07')
# a new throwaway name each run: the lock it earns lasts five minutes
NAME, PW = 'Sec' + ''.join(__import__('random').choice('abcdefghijklmnopqrstuvwxyz') for _ in range(7)), 'sectest-pass1'


async def make_sectest():
    """The throwaway character (no account) the limits are tried on."""
    s = await Raw().open()
    out = await s.cmd(NAME, 1.0)
    if 'is a new name' in out:
        await s.cmd('y', 0.6)
        await s.cmd(PW, 1.0)
        await s.cmd(PW, 1.0)
        await s.cmd('human', 0.8)
        await s.cmd('female', 0.8)
        await s.cmd('warrior', 0.8)
        await s.cmd('y', 2.5)
        await s.cmd('quit', 1.0)
    else:
        await s.cmd(PW, 2.0)
        await s.cmd('n', 2.0)
        await s.cmd('quit', 1.0)
    s.close()


async def live():
    import aiohttp
    await gauntlet_accounts.ensure()
    # 1. the old way into an account character is shut
    s = await Raw().open()
    out = await s.cmd('Probemage', 1.0)
    check('belongs to an account' in out, 'Probemage typed by name asks for its account password')
    out = await s.cmd('account_protected', 1.5)
    check('Invalid password' in out and 'Welcome to Misthollow' not in out, '"account_protected" no longer logs in')
    # a right password clears that failure, so reruns never lock the account other suites use
    await s.cmd('gauntletb', 0.8)
    await s.cmd('gauntlet1', 1.2)
    await s.cmd('quit', 0.3)
    s.close()

    # 2. a fresh character, then the limits
    await make_sectest()
    s = await Raw().open()
    for i in range(3):
        await s.cmd(NAME, 0.8)
        out = await s.cmd('not-the-password', 1.2)
    check('Too many failed attempts' in out, 'three wrong passwords on one connection: goodbye')
    s.close()
    s = await Raw().open()
    out = ''
    for i in range(2):
        await s.cmd(NAME, 0.8)
        out = await s.cmd('not-the-password', 1.2)
    s.close()
    s = await Raw().open()
    await s.cmd(NAME, 0.8)
    out = await s.cmd(PW, 1.5)
    check('Too many failed logins' in out, 'five failures in ten minutes lock the name, even for the right password')
    s.close()

    # 3. sign-in tokens, on the gauntlet account's character
    s = await Raw().open()
    await s.cmd(tw.ACCOUNT, 0.8)
    await s.cmd(tw.PASSWORD, 1.2)
    out = await s.cmd(f'play {tw.CHAR}', 2.0)
    check('\x1b]MAPSYNC:' in out, f'{tw.CHAR} logs in through the account')
    out = await s.cmd('remember', 1.0)
    tok = (RESUME.findall(out) or [''])[-1]
    check(len(tok) >= 40, '`remember` sends a sign-in token over the hidden signal')
    check('remember' not in re.sub(r'\x1b\][^\x07]*\x07', '', out), '…and is not echoed')
    out = await s.cmd('account password wrongold newpassword1', 1.0)
    check('wrongold' not in out and 'account password ****' in out, 'an account password line is echoed masked')
    out = await s.cmd('!', 1.0)
    check('wrongold' not in out, "…and '!' does not repeat it")
    await s.cmd('quit', 1.0)
    s.close()
    await asyncio.sleep(0.5)

    s = await Raw().open()
    out = await s.cmd(f'resume {tw.CHAR} {tok}', 2.0)
    fresh = (RESUME.findall(out) or [''])[-1]
    check('\x1b]MAPSYNC:' in out and fresh and fresh != tok, 'resume <name> <token> logs in and swaps the token')
    await s.cmd('quit', 1.0)
    s.close()
    await asyncio.sleep(0.5)
    s = await Raw().open()
    out = await s.cmd(f'resume {tw.CHAR} {tok}', 1.5)
    check('sign-in has expired' in out and '\x1b]MAPSYNC:' not in out, 'the used token no longer works')
    s.close()

    # 4. through the web bridge: a bare number does not kill it, RESUME arrives as a message
    async with aiohttp.ClientSession() as http:
        async with http.ws_connect(f'ws://{tw.HOST}:4003/ws') as ws:
            msgs = []

            async def pump():
                async for m in ws:
                    if m.type == aiohttp.WSMsgType.TEXT:
                        msgs.append(json.loads(m.data))
            p = asyncio.create_task(pump())
            await asyncio.sleep(1.0)
            await ws.send_str('12345')
            await asyncio.sleep(0.8)
            await ws.send_str(f'resume {tw.CHAR} {fresh}')
            await asyncio.sleep(2.5)
            kinds = [m.get('type') for m in msgs]
            text = ' '.join(m.get('data', '') for m in msgs if m.get('type') == 'output')
            check('mapsync' in kinds, 'the bridge survives a bare number and the token logs in through it')
            check('resume' in kinds and 'RESUME' not in text, 'the new token arrives as {type: resume}, not as text')
            newest = [m['token'] for m in msgs if m.get('type') == 'resume'][-1:]
            if newest:
                await ws.send_str(f'forget {newest[0]}')
            await ws.send_str('quit')
            await asyncio.sleep(1.0)
            p.cancel()
    if newest:
        s = await Raw().open()
        out = await s.cmd(f'resume {tw.CHAR} {newest[0]}', 1.5)
        check('sign-in has expired' in out, '`forget` signs that browser out')
        s.close()

    # 5. the admin dashboard
    key = open(os.path.join(ROOT, 'lib', 'admin_key')).read().strip()
    async with aiohttp.ClientSession() as http:
        base = 'http://127.0.0.1:4002'
        async with http.get(f'{base}/api/stats') as r:
            check(r.status == 401, 'the dashboard API refuses a request without the key')
        async with http.get(f'{base}/api/players', headers={'X-Admin-Key': key}) as r:
            check(r.status == 200 and isinstance(await r.json(), list), '…and answers with it (player list works)')
        async with http.get(f'{base}/api/stats', headers={'X-Admin-Key': key, 'Host': 'evil.example'}) as r:
            check(r.status == 421, 'a request naming another host is refused (DNS rebinding)')
        async with http.post(f'{base}/api/broadcast', headers={'X-Admin-Key': key, 'Origin': 'http://evil.example'},
                             json={'message': 'x'}) as r:
            check(r.status == 403, 'a POST from another site is refused')
        async with http.post(f'{base}/api/broadcast', headers={'X-Admin-Key': key}, data='message=x') as r:
            check(r.status == 415, 'a POST that is not JSON is refused')
        async with http.post(f'{base}/api/shutdown', headers={'X-Admin-Key': key}, json={}) as r:
            check(r.status in (404, 405), 'the dead shutdown button is gone')
    try:
        with socket.create_connection((socket.gethostbyname(socket.gethostname()), 4002), timeout=1):
            reach = True
    except OSError:
        reach = False
    check(not reach or socket.gethostbyname(socket.gethostname()).startswith('127.'),
          'the dashboard is not reachable on the machine\'s network address')


async def main():
    tmp = tempfile.mkdtemp(prefix='mh-sec-')
    saved = (accounts.ACCOUNTS_DIR, security.TOKENS_FILE, Config.PLAYER_DIR)
    try:
        await offline(tmp)
    finally:
        accounts.ACCOUNTS_DIR, security.TOKENS_FILE, Config.PLAYER_DIR = saved
        security._store = None
        shutil.rmtree(tmp, ignore_errors=True)
    if server_up() and '--offline' not in sys.argv:
        await live()
    else:
        print('skip live checks: no server on', tw.HOST, tw.TELNET)
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
