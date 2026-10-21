# Account System

Every character belongs to exactly one account, and the account's password is the only way in.
`src/accounts.py` (`AccountManager`) is the one place accounts and characters are made, claimed,
renamed and deleted; the telnet login (`src/server.py`), /play (which answers the same prompts,
`net.js`) and the in-game `account` command (`src/commands.py`) all go through it.

## Names
- Account names and character names share one namespace: 3-12 letters (`accounts.name_problem`).
- A new account takes a name no account and no character has; a new character a name no
  character and no *other* account has (an account and its first character share theirs).
- The login prompt takes either: an account's name opens that account; a character's name opens
  its account and goes straight into that character.

## Login flow (telnet, and /play under it)
1. `Enter account name (or character name):`
2. Known name: `Account password:` (`<Name> belongs to an account. Account password:` for a
   character). `forgot` and `reset <token> <new>` work here, as before.
   - An account name: the menu. A character name: straight in as that character.
3. New name: `'<Name>' is a new name. Create account? (Y/N)`, then `Choose a password:` /
   `Confirm password:`, then race, sex, class, (a mage's look), stats. The account and its first
   character, of the same name, are made together only when the character is finished
   (`AccountManager.sign_up`): a sign-up left half-way leaves nothing behind.

## The account menu
`create`, `play <name|number>`, `delete <name>` (type the name in capitals to confirm),
`claim <name>`, `list`, `info`, `practice`, `move`, `password`, `link`, `lag`, `time`, `help`, `quit`.
- `claim <name>` asks for the password of the account the character is on now, and moves it
  into this one (the same owner merging accounts). An account left with no characters is retired
  to `lib/deleted/accounts/` (an admin account is kept). Wrong passwords count against that
  account's login lock.
- A character in the world can't be deleted or claimed (its save would be written over).

## /play
- **Enter the Hollow**: name (account or character) and the account's password.
- **Forge a new hero**: a new name and a password make a new account of the hero's name. With
  the optional "…on my account" field filled in, the password is that account's: /play signs
  in to it, uses its `create`, and the hero joins it.

## In game: `account`
`account` / `account info`, `account chars`, `account claim <name> <password>`,
`account password <old> <new>`, `account email <address>`, `account forgot`,
`account recover <token> <new>`; immortals: `account reset <account> <new>`.
`account create` is retired: every character already has an account. Lines carrying a password
(`password`, `recover`, `reset`, `claim`) are echoed masked.

## Data
`lib/accounts/<account>.json`:
```json
{
  "account_name": "michael",
  "password_hash": "pbkdf2_sha256$600000$<salt>$<hash>",
  "created_at": "...",
  "last_login": "...",
  "characters": ["Deckard", "Qamage"],
  "settings": {"email": null, "max_chars": 8},
  "shared": {"bank_gold": 0, "storage": []},
  "reset_tokens": [],
  "is_admin": false
}
```
`lib/players/<name>.json` keeps `account_name`; its own `password_hash` is empty (the account
holds the password).

## Migration of older saves
Before, a character made at the name prompt or by /play had a password of its own and no
account. At every start the server runs `accounts.migrate_saves()` (once all saves are on
accounts it changes nothing):
- an accountless save with a password gets an account named after it holding the same hash
  (an old unsalted one is upgraded at the next login), so its owner logs in exactly as before;
  if someone else's account already has that name, the new account gets letters after it
  (`clash` -> `clasha`) and the character still logs in by its own name;
- a save naming an account whose file is gone gets that account rebuilt;
- a save its account doesn't list is added to the list;
- a save with no account and no password (no way in, before or now) is left alone and logged.

Every save it changes is copied first to `lib/backups/accounts-migration-<time>/players/`.
Old saves stay readable by the code before this change, so a rollback keeps everyone's login.
Owners of several migrated characters can merge them with `claim`.

## Admin / immortal
- An account flagged `is_admin: true` makes every character on it immortal (`Player.is_immortal`).
- The `immortal` gift in `world/grants.json` names the account: `"immortal": "<account>"` makes it
  an admin one only when the character is on that account, and never makes an account. `true`
  is refused (anyone could take a character name); Deckard's `true` was given before this rule.

## Rename and delete
- `AccountManager.rename_character` (no command uses it yet) applies the new-name rules, saves
  under the new name, then removes the old save.
- Deleting puts the save in `lib/deleted/` and forgets the browsers signed in as it.

## Tests
`python3 tests/test_accounts.py` (offline): making accounts and characters, the name rules,
telnet sign-up and login, the menu, /play sign-up and "on my account", `claim`, migration of
legacy saves, and the immortal gift. `tests/test_security.py` covers hashing, tokens and locks.
