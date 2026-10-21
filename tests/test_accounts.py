"""One account manager: every character on exactly one account (accounts.py), made from the
telnet login, from /play (which answers the same prompts) or from an account's menu; older saves
moved onto accounts with their passwords working; `claim`; and the immortal grant naming an
account.

Offline only (temporary player and account folders, a fake connection):
    python3 tests/test_accounts.py
"""
import asyncio
import hashlib
import json
import os
import shutil
import sys
import tempfile
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import test_webmove as tw  # noqa: E402  (check(), failures)
from config import Config  # noqa: E402
import security  # noqa: E402
import accounts  # noqa: E402
from accounts import Account, AccountManager  # noqa: E402

check, failures = tw.check, tw.failures
STATS = {'str': 14, 'int': 12, 'wis': 11, 'dex': 13, 'con': 15, 'cha': 10}


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
    """A login connection whose entering the world is only recorded (conn.entered)."""
    import server
    world = types.SimpleNamespace(players={}, get_room=lambda v: None)
    srv = types.SimpleNamespace(world=world, config=Config())
    w = FakeWriter()
    conn = server.Connection(None, w, srv)
    conn.entered = None

    async def enter_game():
        conn.entered = conn.player
    conn.enter_game = enter_game
    return conn, w


async def say(conn, w, *lines):
    for line in lines:
        await conn.handle_input(line)
    return w.text()


def save_of(name):
    path = os.path.join(Config.PLAYER_DIR, f'{name.lower()}.json')
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


async def write_save(name, **fields):
    """A character's save as an older server left it (a real save, then `fields` over it)."""
    from player import Player
    p = Player.create_new(name=name, password=None, race='human', char_class='warrior', stats=STATS, world=None)
    p.level = 3
    await p.save()
    data = save_of(name)
    data.update({'password_hash': '', 'account_name': None}, **fields)
    with open(os.path.join(Config.PLAYER_DIR, f'{name.lower()}.json'), 'w') as f:
        json.dump(data, f)


def fresh(tmp, sub):
    """Empty player and account folders for one part of the test."""
    base = os.path.join(tmp, sub)
    Config.PLAYER_DIR = os.path.join(base, 'players')
    accounts.ACCOUNTS_DIR = os.path.join(base, 'accounts')
    os.makedirs(Config.PLAYER_DIR)
    os.makedirs(accounts.ACCOUNTS_DIR)
    security._fails.clear()
    security._locked.clear()
    return base


async def run(tmp):
    security.TOKENS_FILE = os.path.join(tmp, 'resume_tokens.json')
    security._store = None

    # ------------------------------------------------ making accounts
    fresh(tmp, 'make')
    acct, why = await AccountManager.create_account('Rowan', 'rowanpass1')
    check(acct is not None and not why and Account.exists('rowan'), 'an account is made with a valid name and password')
    raw = open(os.path.join(accounts.ACCOUNTS_DIR, 'rowan.json')).read()
    check('rowanpass1' not in raw and Account.load('rowan').password_hash.startswith('pbkdf2_sha256$'),
          '…its password stored only as a salted hash (security.py)')
    check(acct.characters == [] and not acct.is_admin, '…with no characters, and not an admin one')
    for bad, pw, what in (('Ro', 'longenough', 'a name under 3 letters'), ('Rowan2', 'longenough', 'a name with a digit'),
                          ('Abcdefghijklm', 'longenough', 'a name over 12 letters'), ('Fresh', 'short', 'a weak password'),
                          ('rowan', 'otherpass1', 'a name an account has')):
        a, why = await AccountManager.create_account(bad, pw)
        check(a is None and why, f'{what} is refused ({why})')

    # ------------------------------------------------ adding characters
    p, why = await AccountManager.create_character(acct, 'Rowan', 'human', 'warrior', STATS)
    check(p is not None and p.account_name == 'rowan', 'a character may share its own account\'s name')
    p2, why = await AccountManager.create_character(acct, 'thistle', 'elf', 'mage', STATS)
    check(p2 is not None and p2.name == 'Thistle' and Account.load('rowan').characters == ['Rowan', 'Thistle'],
          'a second character joins the account, listed in order')
    s = save_of('Thistle')
    check(s['account_name'] == 'rowan' and s['password_hash'] == '', '…its save names the account and has no password of its own')
    other, _ = await AccountManager.create_account('Sorrel', 'sorrelpass1')
    p3, why = await AccountManager.create_character(other, 'Rowan', 'human', 'warrior', STATS)
    check(p3 is None and 'taken' in why, "another account can't take a character's name")
    p3, why = await AccountManager.create_character(other, 'Thistle', 'human', 'warrior', STATS)
    check(p3 is None and 'taken' in why, '…nor a name another account has its character under')
    a, why = await AccountManager.create_account('Thistle', 'thistlepass')
    check(a is None and 'taken' in why, 'a new account can\'t take a character\'s name')
    other.settings['max_chars'] = 1
    await AccountManager.create_character(other, 'Sorrel', 'human', 'cleric', STATS)
    p4, why = await AccountManager.create_character(other, 'Burdock', 'human', 'thief', STATS)
    check(p4 is None and 'maximum' in why and save_of('Burdock') is None, 'a full account makes no more characters')

    # ------------------------------------------------ deleting
    check(AccountManager.delete_character(acct, 'Thistle'), 'a character is deleted from its account')
    check(Account.load('rowan').characters == ['Rowan'] and save_of('Thistle') is None
          and os.path.exists(os.path.join(Config.PLAYER_DIR, '..', 'deleted', 'thistle.json')),
          '…its save put away in lib/deleted, the account no longer listing it')

    # ------------------------------------------------ telnet sign-up and login
    fresh(tmp, 'login')
    conn, w = connection()
    out = await say(conn, w, 'Newbie')
    check("'Newbie' is a new name. Create account?" in out, 'a new name at the login prompt offers an account')
    out = await say(conn, w, 'y')
    check('Choose a password' in out, '…asks for its password')
    out = await say(conn, w, 'short')
    check('at least 8' in out and conn.state == conn.STATE_GET_PASSWORD, '…a weak one is refused')
    out = await say(conn, w, 'newbiepass1', 'newbiepass1')
    check('Choose Your Race' in out, '…confirmed, the first character is made: race first')
    check(not Account.exists('newbie'), '…and nothing is on disk while the character is half made')
    await say(conn, w, 'human', 'female', 'warrior', 'y')
    a = Account.load('newbie')
    check(conn.entered is not None and conn.entered.name == 'Newbie', 'the finished character enters the game')
    check(a is not None and a.characters == ['Newbie'] and save_of('Newbie')['account_name'] == 'newbie',
          '…made together with its account, of the same name, holding it')
    check(save_of('Newbie')['password_hash'] == '' and await security.verify_async(a.password_hash, 'newbiepass1') == (True, False),
          "…the password is the account's (the character has none of its own)")

    # logging in by the account's name: the menu lists every character
    await AccountManager.create_character(a, 'Second', 'dwarf', 'cleric', STATS)
    conn, w = connection()
    out = await say(conn, w, 'newbie', 'newbiepass1')
    check(conn.account is not None and conn.state == conn.STATE_SELECT_CHAR, 'an account name and its password open the menu')
    check('Newbie' in out and 'Second' in out and 'create' in out and 'delete <name>' in out and 'play <name>' in out,
          '…which lists all its characters with create, play and delete')
    await say(conn, w, 'play Second')
    check(conn.entered is not None and conn.entered.name == 'Second' and conn.entered.account_name == 'newbie',
          '…play enters the game as one of them')

    # logging in by a character's name: its account's password, straight in
    conn, w = connection()
    out = await say(conn, w, 'Second')
    check('belongs to an account' in out and conn.play_after == 'Second', "a character's name asks for its account's password")
    out = await say(conn, w, 'wrongpass1')
    check(conn.entered is None and 'Invalid password' in out and conn.state == conn.STATE_GET_NAME, '…a wrong one is refused')
    await say(conn, w, 'Second', 'newbiepass1')
    check(conn.entered is not None and conn.entered.name == 'Second', '…the right one goes straight in as that character')

    # making one from the menu
    conn, w = connection()
    out = await say(conn, w, 'newbie', 'newbiepass1', 'create', 'Newbie')
    check('already taken' in out, "the menu's create refuses a name that is taken")
    await say(conn, w, 'Third', 'elf', 'male', 'ranger', 'y')
    check(conn.entered is not None and Account.load('newbie').characters == ['Newbie', 'Second', 'Third']
          and save_of('Third')['account_name'] == 'newbie', "the menu's create makes a character on the account")

    # delete from the menu
    conn, w = connection()
    await say(conn, w, 'newbie', 'newbiepass1', 'delete Third', 'THIRD')
    check(Account.load('newbie').characters == ['Newbie', 'Second'] and save_of('Third') is None, "the menu's delete removes it")

    # a sign-up whose name is taken while the character is being made
    conn, w = connection()
    await say(conn, w, 'Racer', 'y', 'racerpass1', 'racerpass1')
    await AccountManager.create_account('racer', 'someoneelse1')
    out = await say(conn, w, 'human', 'male', 'warrior', 'y')
    check(conn.entered is None and 'already taken' in out and save_of('Racer') is None,
          'a name taken mid-sign-up makes nothing and says so')

    # ------------------------------------------------ /play
    # Forge a Hero (net.js): the same prompts, answered for the player
    conn, w = connection()
    conn.is_web = True
    await say(conn, w, 'Webhero')
    await say(conn, w, 'y', 'webheropass', 'webheropass')
    await say(conn, w, 'elf', 'female', 'mage', 'classic', 'y')
    a = Account.load('webhero')
    check(conn.entered is not None and a is not None and a.characters == ['Webhero']
          and save_of('Webhero')['account_name'] == 'webhero', 'a /play-created character lands in an account')
    # Forge a Hero with "on my account": the account's password, its create, the hero's name
    conn, w = connection()
    conn.is_web = True
    out = await say(conn, w, 'webhero', 'webheropass')
    check('Available commands:' in out, '…a hero for an existing account signs in to it')
    out = await say(conn, w, 'create')
    check('Enter name for new character' in out, '…and asks its create menu')
    await say(conn, w, 'Webtwo', 'human', 'male', 'paladin', 'y')
    check(conn.entered is not None and Account.load('webhero').characters == ['Webhero', 'Webtwo'],
          '…the new hero joins that account')
    # the scripted login's answers (net.js) to the account menu
    js = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'web_isometric', 'shared', 'net.js'),
              encoding='utf-8').read()
    check('multiple characters' not in js and "sendDelayed('join-create', 'create')" in js
          and 'enter name for new character' in js, "/play's script answers the account menu for a new hero")

    # ------------------------------------------------ claim
    fresh(tmp, 'claim')
    home, _ = await AccountManager.create_account('home', 'homepass1')
    await AccountManager.create_character(home, 'Home', 'human', 'warrior', STATS)
    away, _ = await AccountManager.create_account('away', 'awaypass1')
    await AccountManager.create_character(away, 'Away', 'human', 'thief', STATS)
    ok, why = await AccountManager.claim(home, 'Away', 'homepass1')
    check(not ok and why == 'Wrong password.' and Account.load('away').characters == ['Away'],
          "claim refuses without the password of the character's account")
    ok, why = await AccountManager.claim(home, 'Away', 'awaypass1', online={'away'})
    check(not ok and 'in the world' in why, '…and a character being played')
    tok = security.issue_token('Away')
    ok, why = await AccountManager.claim(home, 'away', 'awaypass1')
    check(ok and Account.load('home').characters == ['Home', 'Away'] and save_of('Away')['account_name'] == 'home',
          'claim moves a character in with its old account\'s password')
    check(not Account.exists('away') and security.use_token('Away', tok) is None,
          '…the emptied account is retired, and browsers signed in as it forgotten')
    # from the account menu: the password is asked on its own line
    keep, _ = await AccountManager.create_account('keep', 'keeppass1')
    await AccountManager.create_character(keep, 'Kept', 'human', 'warrior', STATS)
    await AccountManager.create_character(keep, 'Spare', 'human', 'warrior', STATS)
    conn, w = connection()
    out = await say(conn, w, 'home', 'homepass1', 'claim Spare')
    check(conn.state == conn.STATE_CLAIM_PASSWORD and 'Password of the account' in out, "the menu's claim asks for the password")
    out = await say(conn, w, 'keeppass1')
    check('Spare is now on this account' in out and Account.load('home').characters == ['Home', 'Away', 'Spare']
          and Account.load('keep').characters == ['Kept'], '…and moves the character, leaving the other account its rest')

    # ------------------------------------------------ migration of older saves
    base = fresh(tmp, 'migrate')
    old_hash = hashlib.sha256(b'legacypass').hexdigest()
    await write_save('Legacy', password_hash=old_hash)                         # made on its own (telnet or /play)
    await write_save('Modern', password_hash=security.hash_password('modernpass1'))
    lost_hash = security.hash_password('lostpass1')
    await write_save('Lostone', password_hash=lost_hash, account_name='vanished')  # its account file is gone
    await write_save('Losttwo', password_hash='', account_name='vanished')
    listed = Account('listed')
    listed.password_hash = security.hash_password('listedpass')
    listed.characters = []
    listed.save()
    await write_save('Unlisted', account_name='listed')                       # on an account that doesn't list it
    await write_save('Nopass')                                                 # no way in, before or now
    clash = Account('clash')                                             # someone else's account has its name
    clash.password_hash = security.hash_password('clashowner')
    clash.characters = ['Owner']
    clash.save()
    await write_save('Clash', password_hash=security.hash_password('clashchar1'))
    before_nopass = open(os.path.join(Config.PLAYER_DIR, 'nopass.json')).read()

    backup = os.path.join(base, 'backup')
    report = accounts.migrate_saves(backup_root=backup)
    a = Account.load('legacy')
    check(a is not None and a.characters == ['Legacy'] and a.password_hash == old_hash,
          'a legacy accountless save gets an account of its name holding its password hash')
    s = save_of('Legacy')
    check(s['account_name'] == 'legacy' and s['password_hash'] == '' and s['level'] == 3,
          '…the save now names it and has no password of its own (the rest unchanged)')
    check(os.path.exists(os.path.join(backup, 'players', 'legacy.json'))
          and json.load(open(os.path.join(backup, 'players', 'legacy.json')))['password_hash'] == old_hash,
          '…the save as it was is backed up first')
    check(await AccountManager.authenticate('legacy', 'legacypass') is not None
          and Account.load('legacy').password_hash.startswith('pbkdf2_sha256$'),
          '…its old password logs in to the account (and the old hash is upgraded)')
    conn, w = connection()
    await say(conn, w, 'Legacy', 'legacypass')
    check(conn.state == conn.STATE_SELECT_CHAR, "…typed at the prompt, the account's menu (its name is the account's too)")
    await say(conn, w, 'play Legacy')
    check(conn.entered is not None and conn.entered.name == 'Legacy', '…from which it plays (as /play does for it)')
    check(await AccountManager.authenticate('modern', 'modernpass1') is not None, 'a newer accountless save keeps its password too')
    v = Account.load('vanished')
    check(v is not None and v.characters == ['Lostone', 'Losttwo'] and v.password_hash == lost_hash,
          'an account a save names but whose file is gone is rebuilt with its characters')
    check(Account.load('listed').characters == ['Unlisted'], 'a save its account does not list is added to the list')
    check('Nopass' in report['unreachable'] and open(os.path.join(Config.PLAYER_DIR, 'nopass.json')).read() == before_nopass,
          'a save with no password and no account is reported and left as it was')
    check(Account.load('clash').characters == ['Owner'] and save_of('Clash')['account_name'] == 'clasha'
          and Account.load('clasha').characters == ['Clash'], "a save whose name another's account has gets an account of another name")
    check(await AccountManager.authenticate('clasha', 'clashchar1') is not None, '…with its own password')
    conn, w = connection()
    await say(conn, w, 'Clash', 'clashchar1')
    check(conn.entered is not None and conn.entered.name == 'Clash' and conn.account.account_name == 'clasha',
          '…and still logs in by its character name, with its own password')
    conn, w = connection()
    await say(conn, w, 'Clash', 'clashowner')
    check(conn.account is not None and conn.account.account_name == 'clash' and conn.entered is None,
          "…while the name's account opens with its owner's password")
    again = accounts.migrate_saves(backup_root=os.path.join(base, 'backup2'))
    check(not any(v for k, v in again.items() if k != 'unreachable') and not os.path.exists(os.path.join(base, 'backup2')),
          'a second run changes nothing')
    ok, _ = await AccountManager.claim(Account.load('legacy'), 'Modern', 'modernpass1')
    check(ok and Account.load('legacy').characters == ['Legacy', 'Modern'], 'two migrated characters of one owner merge with claim')

    # ------------------------------------------------ the immortal grant
    import grants
    fresh(tmp, 'grants')
    boss, _ = await AccountManager.create_account('boss', 'bosspass1')
    p, _ = await AccountManager.create_character(boss, 'Bossman', 'human', 'mage', STATS)
    squat, _ = await AccountManager.create_account('squat', 'squatpass1')
    q, _ = await AccountManager.create_character(squat, 'Qamage', 'human', 'mage', STATS)
    p.grants_received, q.grants_received = [], []
    grants.apply_grants(q, {'qamage': {'immortal': True}}, entering=True)
    check(not Account.load('squat').is_admin, '`"immortal": true` is refused: taking a character name gives nothing')
    grants.apply_grants(q, {'qamage': {'immortal': 'boss'}}, entering=True)
    check(not Account.load('squat').is_admin and not Account.load('boss').is_admin,
          "an immortal grant for a character not on the named account gives nothing")
    lines = grants.apply_grants(p, {'bossman': {'immortal': 'boss'}}, entering=True)
    check(Account.load('boss').is_admin and any('immortal' in l for l in lines), '…on it, the named account is made admin')
    check(p.is_immortal and not q.is_immortal, '…so its characters are immortal, and no one else')
    check(sorted(os.listdir(accounts.ACCOUNTS_DIR)) == ['boss.json', 'squat.json'], 'the grant makes no account')


def main():
    tmp = tempfile.mkdtemp(prefix='mh_accounts_')
    saved = (Config.PLAYER_DIR, accounts.ACCOUNTS_DIR, security.TOKENS_FILE)
    try:
        asyncio.run(run(tmp))
    finally:
        Config.PLAYER_DIR, accounts.ACCOUNTS_DIR, security.TOKENS_FILE = saved
        security._store = None
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(failures)} failure(s)" if failures else '\nall account checks passed')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
