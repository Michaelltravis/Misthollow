"""Passwords, sign-in tokens and login throttling.

Passwords are stored as salted PBKDF2-SHA256 (`pbkdf2_sha256$<iterations>$<salt>$<hash>`).
Older files hold an unsalted sha256: `verify` still reads those and asks for a re-hash, so a
character or account is upgraded the next time its owner logs in. The hash a character got
when it was made from the account menu (the word "account_protected") never matches: those
characters are reached through their account only.

Sign-in tokens let the web clients come back without keeping the password: after a login the
client sends `remember`, the server answers with a random token over a hidden signal, and
keeps only its sha256 (lib/resume_tokens.json, at most five devices a character, 30 days
each). `resume <name> <token>` at the name prompt logs in and swaps the token for a new one.
A password change or reset forgets every device.
"""
import asyncio
import hashlib
import hmac
import json
import os
import secrets
import time

ALGO = 'pbkdf2_sha256'
ITERATIONS = 600_000
MIN_PASSWORD = 8                     # new passwords; older, shorter ones keep working

_SENTINEL = hashlib.sha256(b'account_protected').hexdigest()


# ---------------------------------------------------------------- passwords

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), ITERATIONS)
    return f"{ALGO}${ITERATIONS}${salt}${dk.hex()}"


def verify(stored: str, password: str):
    """(matches, needs_rehash) for a stored hash and a typed password."""
    if not stored or not password:
        return False, False
    if stored.startswith(ALGO + '$'):
        try:
            _algo, iters, salt, want = stored.split('$')
            dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), int(iters))
        except (ValueError, TypeError):
            return False, False
        ok = hmac.compare_digest(dk.hex(), want)
        return ok, ok and int(iters) < ITERATIONS
    if len(stored) == 64 and stored != _SENTINEL:          # the old unsalted sha256
        ok = hmac.compare_digest(hashlib.sha256(password.encode('utf-8')).hexdigest(), stored)
        return ok, ok
    return False, False


def usable(stored: str) -> bool:
    """Whether some password can match a stored hash (not empty, damaged or the old
    "account_protected" one)."""
    if not stored:
        return False
    if stored.startswith(ALGO + '$'):
        return len(stored.split('$')) == 4
    return len(stored) == 64 and stored != _SENTINEL


async def hash_async(password: str) -> str:
    return await asyncio.to_thread(hash_password, password)


async def verify_async(stored: str, password: str):
    return await asyncio.to_thread(verify, stored, password)


def weak(password: str) -> str:
    """Why a new password won't do ('' if it will)."""
    if not password or len(password) < MIN_PASSWORD:
        return f"Passwords must be at least {MIN_PASSWORD} characters."
    return ''


# ---------------------------------------------------------------- login throttling

FAILS_PER_CONNECTION = 3
NAME_FAILS = 5
NAME_WINDOW = 600                    # five failures in ten minutes ...
NAME_LOCK = 300                      # ... lock that name for five

_fails = {}                          # name -> [failure times]
_locked = {}                         # name -> locked until


def locked(name: str) -> int:
    """Seconds left on a name's lock (0 when it can try)."""
    until = _locked.get((name or '').lower(), 0)
    left = int(until - time.time())
    if left <= 0:
        _locked.pop((name or '').lower(), None)
        return 0
    return left


def failed(name: str):
    """Count a wrong password against a name; lock it after too many."""
    key = (name or '').lower()
    now = time.time()
    recent = [t for t in _fails.get(key, []) if now - t < NAME_WINDOW]
    recent.append(now)
    _fails[key] = recent
    if len(recent) >= NAME_FAILS:
        _locked[key] = now + NAME_LOCK
        _fails[key] = []


def succeeded(name: str):
    _fails.pop((name or '').lower(), None)


# rate limit for password-reset mails: one an account per 15 minutes
FORGOT_GAP = 900
_forgot = {}


def forgot_allowed(account_name: str) -> bool:
    key = (account_name or '').lower()
    now = time.time()
    if now - _forgot.get(key, 0) < FORGOT_GAP:
        return False
    _forgot[key] = now
    return True


# ---------------------------------------------------------------- email codes
# A new account (or a new email on one) proves its email with a 6-digit code mailed to it. The
# code is kept on the connection that asked for it, as a hash, for 15 minutes and 5 tries. So
# the game can't be used to flood an inbox, an address gets at most 3 codes an hour and one
# network address (the player's own: web_client passes it on) 6.

CODE_TTL = 900
CODE_TRIES = 5
CODES_PER_EMAIL = 3
CODES_PER_ADDRESS = 6
CODE_WINDOW = 3600
_code_sends = {}                     # 'email:x' / 'ip:x' -> [send times]


def code_send_allowed(email: str, address: str) -> str:
    """Why no code may be mailed now ('' if one may; it is then counted)."""
    now = time.time()
    keys = [(f"email:{(email or '').strip().lower()}", CODES_PER_EMAIL), (f"ip:{address or '?'}", CODES_PER_ADDRESS)]
    for key, most in keys:
        recent = [t for t in _code_sends.get(key, []) if now - t < CODE_WINDOW]
        _code_sends[key] = recent
        if len(recent) >= most:
            return "Too many codes have been sent just now. Try again in an hour."
    for key, _most in keys:
        _code_sends[key].append(now)
    return ''


def new_code() -> tuple:
    """A fresh code: (the code to mail, what to keep of it)."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    return code, {'hash': hashlib.sha256(code.encode()).hexdigest(), 'until': time.time() + CODE_TTL, 'tries': 0}


def check_code(kept: dict, typed: str) -> str:
    """'ok', 'wrong' (a try used), 'expired' or 'spent' (out of tries) for a typed code."""
    if not kept:
        return 'expired'
    if time.time() > kept['until']:
        return 'expired'
    if kept['tries'] >= CODE_TRIES:
        return 'spent'
    if hmac.compare_digest(kept['hash'], hashlib.sha256((typed or '').strip().encode()).hexdigest()):
        return 'ok'
    kept['tries'] += 1
    return 'spent' if kept['tries'] >= CODE_TRIES else 'wrong'


# ---------------------------------------------------------------- sign-in tokens

TOKEN_DEVICES = 5
TOKEN_DAYS = 30
TOKENS_FILE = os.path.join(os.path.dirname(__file__), '..', 'lib', 'resume_tokens.json')

_store = None


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _load():
    global _store
    if _store is None:
        try:
            with open(TOKENS_FILE) as f:
                _store = json.load(f)
            if not isinstance(_store, dict):
                _store = {}
        except (OSError, ValueError):
            _store = {}
    return _store


def _save():
    store = _load()
    os.makedirs(os.path.dirname(TOKENS_FILE), exist_ok=True)
    tmp = TOKENS_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(store, f)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, TOKENS_FILE)


def _live(name: str):
    now = time.time()
    store = _load()
    recs = [r for r in store.get(name.lower(), []) if r.get('exp', 0) > now]
    if recs:
        store[name.lower()] = recs
    else:
        store.pop(name.lower(), None)
    return recs


def issue_token(name: str) -> str:
    """A new device token for a character (the oldest goes past five)."""
    token = secrets.token_urlsafe(32)
    now = time.time()
    recs = _live(name)
    recs.append({'h': _digest(token), 'made': int(now), 'exp': int(now + TOKEN_DAYS * 86400)})
    _load()[name.lower()] = recs[-TOKEN_DEVICES:]
    _save()
    return token


def use_token(name: str, token: str):
    """Check a device token and swap it for a fresh one: the new token, or None."""
    if not name or not token:
        return None
    want = _digest(token)
    recs = _live(name)
    for r in recs:
        if hmac.compare_digest(r.get('h', ''), want):
            recs.remove(r)
            _load()[name.lower()] = recs
            return issue_token(name)
    _save()
    return None


def forget_token(name: str, token: str) -> bool:
    want = _digest(token or '')
    recs = _live(name)
    keep = [r for r in recs if not hmac.compare_digest(r.get('h', ''), want)]
    if keep:
        _load()[name.lower()] = keep
    else:
        _load().pop(name.lower(), None)
    _save()
    return len(keep) != len(recs)


def forget_all(*names):
    store = _load()
    gone = False
    for n in names:
        if n and store.pop(n.lower(), None) is not None:
            gone = True
    if gone:
        _save()


def resume_signal(token: str) -> bytes:
    """The hidden signal carrying a token to the web bridge (written raw: the normal send
    would wrap it)."""
    return f"\x1b]RESUME:{token}\x07".encode('utf-8')
