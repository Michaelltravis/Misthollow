"""
Misthollow Account System
========================
Every character belongs to exactly one account, and the account's password is the only way in.
This module is the one place accounts and characters are made, joined, claimed, renamed and
deleted (AccountManager); the telnet login (server.py), /play (which drives the same prompts)
and the in-game `account` command all come here.

Names: account names and character names share one namespace (3-12 letters). A name typed at
the login prompt finds an account by its name, or the account of the character by that name;
so a new account takes a name no account and no character has, and a new character a name no
character and no other account has (an account and its own first character share theirs).

Older saves: a character made on its own kept a password of its own and had no account. At
start the server runs `migrate_saves`, which gives each such save an account of its name with
the same password hash (so the password keeps working), rebuilds an account a character names
but whose file is gone, and backs up every save it changes (lib/backups/). `claim` then lets
one account take in a character from another of its owner's accounts, by that one's password.
"""

import os
import json
import glob
import hashlib
import hmac
import logging
import secrets
import shutil
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import security

if TYPE_CHECKING:
    from player import Player

logger = logging.getLogger('Misthollow')

ACCOUNTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'lib', 'accounts')
NAME_MIN, NAME_MAX = 3, 12


class Account:
    """Represents a player account that can have multiple characters."""

    def __init__(self, account_name: str):
        self.account_name = account_name.lower()
        self.password_hash = ''
        self.created_at = datetime.now().isoformat()
        self.last_login = datetime.now().isoformat()
        self.characters: List[str] = []  # Character names
        self.settings = {
            'email': None,
            'max_chars': 8
        }
        self.shared = {
            'bank_gold': 0,
            'storage': []
        }
        self.reset_tokens = []  # list of {token, created_at}
        self.is_admin = False

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storage (salted PBKDF2, security.py)."""
        return security.hash_password(password)

    async def check_password(self, password: str) -> bool:
        """Verify a password against the stored hash; an old-style hash is upgraded."""
        ok, rehash = await security.verify_async(self.password_hash, password)
        if ok and rehash:
            self.password_hash = await security.hash_async(password)
            self.save()
        return ok

    async def set_password(self, password: str):
        """Set a new password. Every device signed in with the old one is forgotten."""
        self.password_hash = await security.hash_async(password)
        security.forget_all(*self.characters)

    def add_character(self, char_name: str) -> bool:
        """Add a character to this account."""
        if len(self.characters) >= self.settings.get('max_chars', 8):
            return False
        if char_name not in self.characters:
            self.characters.append(char_name)
        return True

    def remove_character(self, char_name: str) -> bool:
        """Remove a character from this account."""
        if char_name in self.characters:
            self.characters.remove(char_name)
            return True
        return False

    def to_dict(self) -> dict:
        """Serialize account to dictionary."""
        return {
            'account_name': self.account_name,
            'password_hash': self.password_hash,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'characters': self.characters,
            'settings': self.settings,
            'shared': self.shared,
            'reset_tokens': self.reset_tokens,
            'is_admin': self.is_admin
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Account':
        """Create account from dictionary."""
        account = cls(data.get('account_name', 'unknown'))
        account.password_hash = data.get('password_hash', '')
        account.created_at = data.get('created_at', datetime.now().isoformat())
        account.last_login = data.get('last_login', datetime.now().isoformat())
        account.characters = data.get('characters', [])
        account.settings = data.get('settings', {'email': None, 'max_chars': 8})
        account.shared = data.get('shared', {'bank_gold': 0, 'storage': []})
        account.reset_tokens = data.get('reset_tokens', [])
        account.is_admin = data.get('is_admin', False)
        return account

    def save(self):
        """Save account to file (written whole, then swapped in)."""
        os.makedirs(ACCOUNTS_DIR, exist_ok=True)
        filepath = os.path.join(ACCOUNTS_DIR, f'{self.account_name}.json')
        tmp = filepath + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        os.replace(tmp, filepath)

    @classmethod
    def load(cls, account_name: str) -> Optional['Account']:
        """Load account from file."""
        if not account_name:
            return None
        filepath = os.path.join(ACCOUNTS_DIR, f'{account_name.lower()}.json')
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception:
            return None

    @staticmethod
    def exists(account_name: str) -> bool:
        """Check if an account exists."""
        if not account_name:
            return False
        filepath = os.path.join(ACCOUNTS_DIR, f'{account_name.lower()}.json')
        return os.path.exists(filepath)


# ---------------------------------------------------------------- names and saves

def name_problem(name: str) -> str:
    """Why a name won't do for an account or a character ('' if it will)."""
    if not name or len(name) < NAME_MIN or len(name) > NAME_MAX:
        return f"Names must be between {NAME_MIN} and {NAME_MAX} characters."
    if not name.isalpha() or not name.isascii():
        return "Names must contain only letters."
    return ''


def _players_dir() -> str:
    from config import Config
    return Config.PLAYER_DIR


def _save_path(char_name: str) -> str:
    return os.path.join(_players_dir(), f'{char_name.lower()}.json')


def _read_save(char_name: str) -> Optional[dict]:
    try:
        with open(_save_path(char_name), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write_save(path: str, data: dict):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def name_taken(name: str, account: Optional[Account] = None) -> bool:
    """Whether a name is someone's: a character's, or an account's other than `account` (a
    new character may share its own account's name)."""
    key = (name or '').lower()
    if os.path.exists(_save_path(key)):
        return True
    return Account.exists(key) and (account is None or account.account_name != key)


class AccountManager:
    """The one place accounts and characters are made, joined, claimed, renamed and deleted."""

    @staticmethod
    async def create_account(account_name: str, password: str) -> Tuple[Optional[Account], str]:
        """A new, empty account: (account, '') or (None, why not)."""
        why = name_problem(account_name) or security.weak(password)
        if why:
            return None, why
        password_hash = await security.hash_async(password)
        # checked after the hashing (it awaits): nothing else runs between this and the save
        if name_taken(account_name):
            return None, "That name is already taken."
        account = Account(account_name)
        account.password_hash = password_hash
        account.save()
        logger.info(f"accounts: made account {account.account_name}")
        return account, ''

    @staticmethod
    async def create_character(account: Account, name: str, race: str, char_class: str, stats: Dict[str, int],
                               world=None, sex: str = 'neutral', look_style: str = '') -> Tuple[Optional['Player'], str]:
        """A new character inside an account: (player, '') or (None, why not). The character has
        no password of its own: its account opens it."""
        from player import Player
        why = name_problem(name)
        if why:
            return None, why
        name = name.capitalize()
        if name_taken(name, account):
            return None, "That name is already taken."
        if not account.add_character(name):
            return None, "You have reached the maximum number of characters!"
        player = Player.create_new(name=name, password=None, race=race, char_class=char_class, stats=stats,
                                   world=world, sex=sex, look_style=look_style)
        player.account_name = account.account_name
        account.save()
        await player.save()
        logger.info(f"accounts: made {name} on {account.account_name}")
        return player, ''

    @staticmethod
    async def sign_up(account_name: str, password: str, race: str, char_class: str, stats: Dict[str, int],
                      world=None, sex: str = 'neutral', look_style: str = '') -> Tuple[Optional[Account], Optional['Player'], str]:
        """A new account and its first character, named after it, made together (a sign-up
        left half-way leaves nothing behind): (account, player, '') or (None, None, why not)."""
        account, why = await AccountManager.create_account(account_name, password)
        if account is None:
            return None, None, why
        player, why = await AccountManager.create_character(account, account_name, race, char_class, stats,
                                                            world, sex, look_style)
        if player is None:
            AccountManager._retire(account)
            return None, None, why
        return account, player, ''

    @staticmethod
    def login_choices(name: str) -> List[Tuple[Account, Optional[str]]]:
        """What a name typed at the login prompt may open, in order: (the account by that name,
        None), then (the account of the character by that name, its name). Both only when a
        save given its account by the migration has the name of someone else's account."""
        if not name:
            return []
        choices = []
        account = Account.load(name)
        if account is not None:
            choices.append((account, None))
        data = _read_save(name)
        if data and data.get('account_name') and (account is None or account.account_name != data['account_name'].lower()):
            owner = Account.load(data['account_name'])
            if owner is not None:
                choices.append((owner, data.get('name') or name.capitalize()))
        return choices

    @staticmethod
    def account_for(name: str) -> Tuple[Optional[Account], Optional[str]]:
        """What a name typed at the login prompt opens first: (the account by that name, None),
        or (the account of the character by that name, its name), or (None, None)."""
        choices = AccountManager.login_choices(name)
        return choices[0] if choices else (None, None)

    @staticmethod
    async def authenticate(account_name: str, password: str) -> Optional[Account]:
        """Authenticate and return account if valid."""
        account = Account.load(account_name)
        if account and await account.check_password(password):
            account.last_login = datetime.now().isoformat()
            account.save()
            return account
        return None

    @staticmethod
    async def claim(account: Account, char_name: str, password: str, online=()) -> Tuple[bool, str]:
        """Move a character into `account` from another account, given that account's password
        (the same owner merging two accounts): (True, '') or (False, why not). `online`: the
        lowercased names in the world just now (one being played can't move: its save would be
        written over). An account left with no characters is retired, unless it is an admin one."""
        name = (char_name or '').capitalize()
        data = _read_save(name)
        if name_problem(name) or data is None:
            return False, f"There is no character called {name or 'that'}."
        name = data.get('name') or name
        if name in account.characters:
            return False, f"{name} is already on this account."
        if name.lower() in online:
            return False, f"{name} is in the world right now: quit them first."
        source = Account.load(data.get('account_name') or '')
        if source is not None:
            ok = await source.check_password(password)
        else:
            # a save the migration couldn't give an account to: its own password, if any
            ok = (await security.verify_async(data.get('password_hash') or '', password))[0]
        if not ok:
            return False, "Wrong password."
        if len(account.characters) >= account.settings.get('max_chars', 8):
            return False, "This account has no room for another character."
        if source is not None:
            source.remove_character(name)
            source.save()
        account.add_character(name)
        account.save()
        data['account_name'] = account.account_name
        data['password_hash'] = ''
        _write_save(_save_path(name), data)
        security.forget_all(name)
        if source is not None and not source.characters and not source.is_admin:
            AccountManager._retire(source)
        logger.info(f"accounts: {account.account_name} claimed {name} from {source.account_name if source else 'no account'}")
        return True, ''

    @staticmethod
    def _retire(account: Account):
        """Put an account file away (lib/deleted/accounts): its name is free again."""
        path = os.path.join(ACCOUNTS_DIR, f'{account.account_name}.json')
        if not os.path.exists(path):
            return
        gone = os.path.join(ACCOUNTS_DIR, '..', 'deleted', 'accounts')
        os.makedirs(gone, exist_ok=True)
        os.replace(path, os.path.join(gone, f"{account.account_name}-{datetime.now():%Y%m%d%H%M%S}.json"))

    @staticmethod
    def set_email(account: Account, email: str) -> bool:
        """Set account email for password resets."""
        if not email or '@' not in email:
            return False
        account.settings['email'] = email
        account.save()
        return True

    @staticmethod
    def generate_reset_token(account: Account) -> str:
        """Generate a password reset token; only its hash is kept."""
        token = secrets.token_urlsafe(16)
        now = datetime.now().isoformat()
        # Prune old tokens
        from config import Config
        cutoff = datetime.now() - timedelta(hours=Config.PASSWORD_RESET_TTL_HOURS)
        account.reset_tokens = [t for t in account.reset_tokens
                                if t.get('hash') and datetime.fromisoformat(t.get('created_at', now)) > cutoff]
        account.reset_tokens.append({'hash': hashlib.sha256(token.encode()).hexdigest(), 'created_at': now})
        account.save()
        return token

    @staticmethod
    def send_reset_email(account: Account, token: str) -> bool:
        """Send reset email via SMTP. Returns True if sent."""
        from config import Config
        cfg = Config()

        if not cfg.SMTP_HOST or not cfg.SMTP_FROM:
            return False
        if not account.settings.get('email'):
            return False

        msg = EmailMessage()
        msg['Subject'] = 'Misthollow Password Reset'
        msg['From'] = cfg.SMTP_FROM
        msg['To'] = account.settings['email']
        msg.set_content(
            f"Hello {account.account_name},\n\n"
            f"Use this token to reset your password (valid {cfg.PASSWORD_RESET_TTL_HOURS} hours):\n\n"
            f"{token}\n\n"
            f"You can reset from the login screen by typing:\n"
            f"reset {token} <newpassword>\n\n"
            f"If you did not request this, you can ignore this email."
        )

        try:
            server = smtplib.SMTP(cfg.SMTP_HOST, cfg.SMTP_PORT)
            if cfg.SMTP_TLS:
                server.starttls()
            if cfg.SMTP_USER and cfg.SMTP_PASS:
                server.login(cfg.SMTP_USER, cfg.SMTP_PASS)
            server.send_message(msg)
            server.quit()
            return True
        except Exception:
            return False

    @staticmethod
    async def reset_with_token(account_name: str, token: str, new_password: str) -> bool:
        """Reset password using a valid token."""
        account = Account.load(account_name)
        if not account:
            return False
        if security.weak(new_password):
            return False
        want = hashlib.sha256((token or '').encode()).hexdigest()
        # Validate token
        now = datetime.now()
        from config import Config
        cutoff = now - timedelta(hours=Config.PASSWORD_RESET_TTL_HOURS)
        valid = False
        for t in list(account.reset_tokens):
            try:
                created = datetime.fromisoformat(t.get('created_at'))
            except Exception:
                created = now
            if created < cutoff:
                account.reset_tokens.remove(t)
                continue
            if hmac.compare_digest(t.get('hash', ''), want):
                valid = True
                account.reset_tokens.remove(t)
                break
        if not valid:
            account.save()
            return False
        await account.set_password(new_password)
        account.save()
        return True

    @staticmethod
    def get_character_info(account: Account) -> List[dict]:
        """Get info about all characters on an account."""
        from player import Player

        char_info = []
        for char_name in account.characters:
            info = Player.get_info(char_name)
            if info:
                char_info.append({
                    'name': info['name'],
                    'class': info['char_class'],
                    'level': info['level'],
                    'race': info['race'],
                    'last_login': info.get('last_login') or 'Unknown'
                })
            else:
                # Character file missing - still show in list
                char_info.append({
                    'name': char_name,
                    'class': '???',
                    'level': 0,
                    'race': '???',
                    'last_login': 'Unknown'
                })
        return char_info

    @staticmethod
    def delete_character(account: Account, char_name: str) -> bool:
        """Delete a character from an account (its save is put away in lib/deleted, and every
        browser signed in as it is forgotten)."""
        if char_name not in account.characters:
            return False

        # Remove from account
        account.remove_character(char_name)
        account.save()
        security.forget_all(char_name)

        # Move player file to deleted folder (don't truly delete)
        deleted_dir = os.path.join(_players_dir(), '..', 'deleted')
        os.makedirs(deleted_dir, exist_ok=True)

        old_path = _save_path(char_name)
        new_path = os.path.join(deleted_dir, f'{char_name.lower()}.json')

        if os.path.exists(old_path):
            os.replace(old_path, new_path)

        return True

    @staticmethod
    async def rename_character(account: Account, old_name: str, new_name: str) -> bool:
        """Rename a character on an account (the new name under the same rules as a new one)."""
        from player import Player

        if old_name not in account.characters:
            return False
        if name_problem(new_name) or name_taken(new_name, account):
            return False

        player = Player.load(old_name)
        if not player:
            return False

        old_path = _save_path(old_name)
        player.name = new_name.capitalize()
        await player.save()  # saves to the new name
        if os.path.exists(old_path):
            os.remove(old_path)

        idx = account.characters.index(old_name)
        account.characters[idx] = player.name
        account.save()
        security.forget_all(old_name)
        return True


# ---------------------------------------------------------------- migration of older saves

def _free_account_name(name: str) -> Optional[str]:
    """An account name for a save that had none: its own, or (taken by someone else's
    account) its own with letters after it."""
    base = name.lower()
    if not name_problem(base) and not Account.exists(base):
        return base
    stem = base[:NAME_MAX - 1]
    for c in 'abcdefghijklmnopqrstuvwxyz':
        alt = stem + c
        if not name_problem(alt) and not Account.exists(alt) and not os.path.exists(_save_path(alt)):
            return alt
    return None


def migrate_saves(backup_root: Optional[str] = None) -> Dict[str, list]:
    """Put every character under lib/players on an account (run at start; once everything is
    on one, it changes nothing):

    - a save with no account and a password of its own gets an account named after it (another
      name when an account already has that one), holding that same password hash, so its owner
      logs in just as before; the save then has no password of its own;
    - a save naming an account whose file is gone gets that account back, with the password of
      the first of its characters that has one;
    - a save on an account that doesn't list it is added to the list;
    - a save with no account and no password (no way in, now or before) is left as it is.

    Every save it changes is copied first to <backup_root>/players (default
    lib/backups/accounts-migration-<time>). Returns what it did, by kind."""
    report = {'accounts_made': [], 'rebuilt': [], 'listed': [], 'unreachable': [], 'renamed': []}
    players = _players_dir()
    saves = []
    for path in sorted(glob.glob(os.path.join(players, '*.json'))):
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, ValueError):
            logger.warning(f"accounts migration: can't read {os.path.basename(path)}")
            continue
        if isinstance(data, dict):
            saves.append((path, data))
    backup = None

    def changed(path, data):
        nonlocal backup
        if backup is None:
            backup = backup_root or os.path.normpath(os.path.join(players, '..', 'backups',
                                                                  f"accounts-migration-{datetime.now():%Y%m%d-%H%M%S}"))
            os.makedirs(os.path.join(backup, 'players'), exist_ok=True)
        dest = os.path.join(backup, 'players', os.path.basename(path))
        if not os.path.exists(dest):
            shutil.copy2(path, dest)
        _write_save(path, data)

    # characters naming an account whose file is gone, by that account
    missing: Dict[str, list] = {}
    for path, data in saves:
        name = data.get('name') or os.path.basename(path)[:-5].capitalize()
        acct_name = (data.get('account_name') or '').lower()
        if acct_name:
            account = Account.load(acct_name)
            if account is None:
                missing.setdefault(acct_name, []).append((path, data, name))
            elif name not in account.characters:
                account.characters.append(name)      # repaired whole, past the usual limit
                account.save()
                report['listed'].append(f"{name} ({acct_name})")
            continue
        ph = data.get('password_hash') or ''
        if not security.usable(ph):
            report['unreachable'].append(name)
            continue
        new = _free_account_name(name)
        if new is None:
            report['unreachable'].append(name)
            continue
        account = Account(new)
        account.password_hash = ph
        account.characters = [name]
        account.save()
        data['account_name'] = new
        data['password_hash'] = ''
        changed(path, data)
        report['accounts_made'].append(name)
        if new != name.lower():
            report['renamed'].append(f"{name} -> account {new}")

    for acct_name, members in sorted(missing.items()):
        ph = next((d.get('password_hash') for _p, d, _n in members if security.usable(d.get('password_hash') or '')), '')
        # (an account made above may have taken the name: these then get one of their own)
        target = acct_name if not Account.exists(acct_name) and not name_problem(acct_name) else _free_account_name(acct_name)
        if not ph or target is None:
            report['unreachable'].extend(n for _p, _d, n in members)
            continue
        account = Account(target)
        account.password_hash = ph
        account.characters = [n for _p, _d, n in members]
        account.save()
        for path, data, _n in members:
            if data.get('password_hash') or data.get('account_name') != target:
                data['password_hash'] = ''
                data['account_name'] = target
                changed(path, data)
        report['rebuilt'].append(f"{target} ({', '.join(account.characters)})")
        if target != acct_name:
            report['renamed'].append(f"account {acct_name} -> {target}")

    done = {k: v for k, v in report.items() if v}
    if done:
        logger.info(f"accounts migration: {done}" + (f" (saves backed up in {backup})" if backup else ''))
    return report
