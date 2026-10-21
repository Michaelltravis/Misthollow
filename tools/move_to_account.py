#!/usr/bin/env python3
"""Move characters onto one account, making the account if it doesn't exist yet.

Run on the server's machine, from the repository, with the game stopped (a character in the
world would save itself back over the move). Without --apply it only says what it would do.

    python3 tools/move_to_account.py deckard --min-level 60            # what would move
    python3 tools/move_to_account.py deckard --min-level 60 --apply    # move them
    python3 tools/move_to_account.py deckard Aimer Sable --apply       # these, by name

A new account's password is asked for at the terminal (twice) and never shown. Characters
leave the account they were on (one left empty is put away in lib/deleted/accounts, unless
it is an admin account) and keep no password of their own: the new account's opens them.
"""
import argparse
import asyncio
import getpass
import glob
import json
import os
import socket
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
from config import Config  # noqa: E402
from accounts import Account, AccountManager, name_problem  # noqa: E402
import security  # noqa: E402


def saves():
    """Every character save: (name, level, class, account)."""
    out = []
    for path in sorted(glob.glob(os.path.join(Config.PLAYER_DIR, '*.json'))):
        try:
            with open(path, encoding='utf-8') as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if d.get('name'):
            out.append((d['name'], int(d.get('level') or 0), d.get('char_class', '?'), (d.get('account_name') or '').lower()))
    return out


def server_up() -> bool:
    try:
        with socket.create_connection(('127.0.0.1', Config.PORT), timeout=1):
            return True
    except OSError:
        return False


async def new_password(account_name: str) -> str:
    while True:
        pw = getpass.getpass(f"Password for the new account '{account_name}': ")
        why = security.weak(pw)
        if why:
            print(why)
            continue
        if getpass.getpass('Again: ') != pw:
            print("They don't match.")
            continue
        return pw


async def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('account', help='the account to move characters onto (made if missing)')
    ap.add_argument('names', nargs='*', help='characters to move, by name')
    ap.add_argument('--min-level', type=int, help='also move every character of at least this level')
    ap.add_argument('--apply', action='store_true', help='make the change (without it: only show it)')
    ap.add_argument('--server-stopped', action='store_true',
                    help="go ahead although something answers on the game's port (it isn't this game)")
    args = ap.parse_args()

    acct_name = args.account.lower()
    why = name_problem(acct_name)
    if why:
        sys.exit(why)
    everyone = saves()
    by_name = {n.lower(): (n, lvl, cls, a) for n, lvl, cls, a in everyone}
    chosen, missing = [], []
    for n in args.names:
        (chosen.append(by_name[n.lower()]) if n.lower() in by_name else missing.append(n))
    if args.min_level is not None:
        chosen += [c for c in everyone if c[1] >= args.min_level and c not in chosen]
    if missing:
        sys.exit(f"No character called: {', '.join(missing)}")
    if not chosen:
        sys.exit('No characters chosen: name some, or give --min-level.')

    account = Account.load(acct_name)
    if account is None and acct_name in by_name and by_name[acct_name][3] != acct_name:
        sys.exit(f"'{acct_name}' is a character's name (on {by_name[acct_name][3] or 'no account'}): choose another account name.")
    moving = [c for c in chosen if c[3] != acct_name]
    print(f"Account {acct_name}: {'exists, with ' + ', '.join(account.characters) if account and account.characters else 'exists, empty' if account else 'will be made'}")
    for n, lvl, cls, a in chosen:
        print(f"  {n:<14} level {lvl:<3} {cls:<12} {'already on it' if a == acct_name else 'from ' + (a or 'no account')}")
    room = (account.settings.get('max_chars', 8) if account else 8)
    have = len(account.characters) if account else 0
    if have + len(moving) > room:
        print(f"The account will hold {have + len(moving)} characters: its limit goes from {room} to {have + len(moving)}.")
    if not args.apply:
        print('\nNothing changed. Run again with --apply to do it.')
        return
    if server_up() and not args.server_stopped:
        sys.exit(f"The game answers on port {Config.PORT}: stop it first (a character in the world would save "
                 "itself back over the move).")

    if account is None:
        account, why = await AccountManager.create_account(acct_name, await new_password(acct_name))
        if account is None:
            sys.exit(why)
        print(f'Made account {acct_name}.')
    if have + len(moving) > account.settings.get('max_chars', 8):
        account.settings['max_chars'] = have + len(moving)
        account.save()
    for n, *_rest in moving:
        ok, why = AccountManager.move_character(account, n)
        print(f"  {n}: {'moved' if ok else why}")
    print(f"\n{acct_name} now holds: {', '.join(Account.load(acct_name).characters)}")


if __name__ == '__main__':
    asyncio.run(main())
