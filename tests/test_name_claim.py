"""A new name is held by the connection making it, so a second person typing it is turned away
at once rather than after choosing race, class and stats; a name saved meanwhile anyway is
never made again; and a new character's save is made, never written over another.

Offline (temporary player/account folders, fake connections):
    python3 tests/test_name_claim.py
"""
import asyncio
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import test_webmove as tw  # noqa: E402  (check(), failures)
from test_security import connection  # noqa: E402  (a Connection on a fake writer)
from config import Config  # noqa: E402
import accounts  # noqa: E402
import security  # noqa: E402

check, failures = tw.check, tw.failures


def stub_world(conn):
    """Record entering the game instead of walking into a world the fake doesn't have."""
    conn.entered = 0

    async def enter_game():
        conn.entered += 1
    conn.enter_game = enter_game
    return conn


async def to_stats(conn, w, name, pw='goodpassword'):
    """The name prompt through to the rolled stats; the output along the way."""
    out = ''
    await conn.handle_input(name)
    out += w.text()
    if conn.state != conn.STATE_CONFIRM_NAME:
        return out
    for line in ('y', pw, pw, 'human', 'female', 'warrior'):
        await conn.handle_input(line)
        out += w.text()
    return out


def server_naming():
    import server
    return server._naming


def saved(name):
    with open(os.path.join(Config.PLAYER_DIR, f'{name.lower()}.json')) as f:
        return json.load(f)


async def offline():
    # two connections, one new name: the second is turned away while the first is making it
    a, wa = connection()
    b, wb = connection()
    stub_world(a), stub_world(b)
    await to_stats(a, wa, 'Aria', 'apassword1')
    check(a.state == a.STATE_ROLLING_STATS, 'the first connection reaches the stats with a new name')
    out = await to_stats(b, wb, 'aria', 'bpassword1')
    check(b.state == b.STATE_GET_NAME and 'already taken' in out,
          'a second connection typing that name while it is being made is told it is taken')
    check(b.temp_name is None, '…and keeps nothing of it')

    # the first finishes: its character is saved and it goes in
    await a.handle_input('y')
    check(a.entered == 1 and saved('Aria')['name'] == 'Aria', 'the first connection makes the character and goes in')
    check(security.verify(accounts.Account.load('aria').password_hash, 'apassword1')[0], "…on its account, with its password")

    # the race the hold closes: a connection already at the stats when the name gets saved
    # by someone else must not overwrite it (or take over the one in the world)
    c, wc = connection()
    stub_world(c)
    await to_stats(c, wc, 'Brin', 'cpassword1')
    with open(os.path.join(Config.PLAYER_DIR, 'brin.json'), 'w') as f:
        json.dump({'name': 'Brin', 'password_hash': security.hash_password('theirs123')}, f)
    await c.handle_input('y')
    out = wc.text()
    check(c.entered == 0 and c.player is None, 'a name saved since it was typed is not made again')
    check(security.verify(saved('Brin')['password_hash'], 'theirs123')[0], '…and the saved one is left as it was')
    check(c.state == c.STATE_GET_NAME and 'already taken' in out, '…the player is told and asked for another name')
    check(not accounts.Account.exists('brin'), '…and no account is left behind')

    # a connection that leaves mid-creation lets the name go
    d, wd = connection()
    stub_world(d)
    await to_stats(d, wd, 'Corin')
    await d.disconnect()
    e, we = connection()
    stub_world(e)
    await to_stats(e, we, 'Corin')
    check(e.state == e.STATE_ROLLING_STATS, 'a name let go by a closed connection can be taken')
    await e.disconnect()

    # saying no to the new name lets it go
    f_, wf = connection()
    await f_.handle_input('Dara')
    await f_.handle_input('n')
    g, wg = connection()
    await g.handle_input('Dara')
    check(g.state == g.STATE_CONFIRM_NAME, 'a name turned down at "Create account?" is free again')

    # the account menu's create holds names the same way, against both paths
    owner = accounts.Account('keeper')
    await owner.set_password('keeperpass')
    owner.save()
    h, wh = connection()
    stub_world(h)
    h.account = accounts.Account.load('keeper')
    h.state = h.STATE_CREATE_CHAR_NAME
    await h.handle_input('Dara')
    check(h.state == h.STATE_CREATE_CHAR_NAME and 'already taken' in wh.text(),
          'the account menu cannot take a name being made at the name prompt')
    await h.handle_input('Elin')
    check(h.state == h.STATE_GET_RACE, 'the account menu holds a free name')
    i, wi = connection()
    await i.handle_input('Elin')
    check(i.state == i.STATE_GET_NAME and 'already taken' in wi.text(),
          'the name prompt cannot take a name being made from the account menu')
    for line in ('human', 'male', 'warrior', 'y'):
        await h.handle_input(line)
    check(h.entered == 1 and saved('Elin')['account_name'] == 'keeper'
          and 'Elin' in accounts.Account.load('keeper').characters, 'the account character is made and linked')

    # an account character whose name was saved meanwhile is not linked to the account
    j, wj = connection()
    stub_world(j)
    j.account = accounts.Account.load('keeper')
    j.state = j.STATE_CREATE_CHAR_NAME
    for line in ('Fenn', 'human', 'male', 'warrior'):
        await j.handle_input(line)
    with open(os.path.join(Config.PLAYER_DIR, 'fenn.json'), 'w') as f:
        json.dump({'name': 'Fenn', 'password_hash': ''}, f)
    await j.handle_input('y')
    check(j.entered == 0 and 'Fenn' not in accounts.Account.load('keeper').characters
          and 'already taken' in wj.text() and j.state == j.STATE_SELECT_CHAR,
          'an account character whose name was saved meanwhile is neither made nor linked')

    # Create account (`newaccount`) holds its name the same way, both ways round
    k, wk = connection()
    await k.handle_input('Hale')
    n, wn = connection()
    await n.handle_input('newaccount Hale')
    check(n.state == n.STATE_GET_NAME and 'already taken' in wn.text() and not accounts.Account.exists('hale'),
          '`newaccount` cannot take a name a sign-up is making')
    o, wo = connection()
    await o.handle_input('newaccount Iver')
    q, wq = connection()
    await q.handle_input('Iver')
    check(q.state == q.STATE_GET_NAME and 'already taken' in wq.text(), '…nor a sign-up a name `newaccount` is making')
    for line in ('iverpass12', 'iverpass12'):
        await o.handle_input(line)
    check(accounts.Account.exists('iver') and 'iver' not in server_naming(), '…which, made, it lets go')
    r, wr = connection()
    await r.handle_input('newaccount Jorn not-an-email')
    s, ws = connection()
    await s.handle_input('Jorn')
    check("isn't an email" in wr.text() and s.state == s.STATE_CONFIRM_NAME,
          '…and one refused for its email leaves the name free')
    await k.disconnect()
    await q.disconnect()
    await s.disconnect()

    # a new character's file is made exclusively, even past the name check
    from player import Player
    p = Player.load('Aria')
    try:
        await p.save(new=True)
        check(False, 'saving a new character over an existing file is refused')
    except FileExistsError:
        check(True, 'saving a new character over an existing file is refused')
    with open(os.path.join(Config.PLAYER_DIR, 'gale.json'), 'w') as f:
        json.dump({'name': 'Gale', 'password_hash': 'theirs'}, f)
    real_taken = accounts.name_taken
    accounts.name_taken = lambda *a: False      # a save the check can't see (another server process)
    try:
        made, why = await accounts.AccountManager.create_character(
            accounts.Account.load('keeper'), 'Gale', 'human', 'warrior',
            {'str': 14, 'int': 12, 'wis': 11, 'dex': 13, 'con': 15, 'cha': 10})
    finally:
        accounts.name_taken = real_taken
    check(made is None and 'already taken' in why and saved('Gale')['password_hash'] == 'theirs'
          and 'Gale' not in accounts.Account.load('keeper').characters,
          '…so create_character leaves it alone and does not list the name on the account')


async def main():
    tmp = tempfile.mkdtemp(prefix='mh-name-')
    saved_dirs = (accounts.ACCOUNTS_DIR, security.TOKENS_FILE, Config.PLAYER_DIR)
    accounts.ACCOUNTS_DIR = os.path.join(tmp, 'accounts')
    security.TOKENS_FILE = os.path.join(tmp, 'resume_tokens.json')
    security._store = None
    Config.PLAYER_DIR = os.path.join(tmp, 'players')
    os.makedirs(Config.PLAYER_DIR, exist_ok=True)
    try:
        await offline()
    finally:
        accounts.ACCOUNTS_DIR, security.TOKENS_FILE, Config.PLAYER_DIR = saved_dirs
        security._store = None
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
