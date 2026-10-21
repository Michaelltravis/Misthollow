"""
Misthollow Server
================
Handles network connections and player sessions.
"""

import msgkind
import quest_guide
import asyncio
import ipaddress
import logging
import re
import textwrap
from typing import Dict
from datetime import datetime
import os

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')
_BOX_CHARS = set('║╔╗╚╝═╠╣╬╦╩─│┌┐└┘├┤┬┴┼')

def _wrap_line(line: str, width: int = 80) -> str:
    """Word-wrap a single line, preserving ANSI codes."""
    stripped = _ANSI_RE.sub('', line)
    # Skip wrapping for short lines or box-drawing lines
    if len(stripped) <= width:
        return line
    # Check if line (after stripping ANSI) starts with box chars
    first_visible = stripped.lstrip()
    if first_visible and first_visible[0] in _BOX_CHARS:
        return line
    # Wrap using the stripped version, then re-insert ANSI codes
    # Strategy: collect ANSI tokens with positions, wrap plain text, reinsert
    tokens = []
    plain = ''
    for part in re.split(r'(\x1b\[[0-9;]*m)', line):
        if part.startswith('\x1b['):
            tokens.append((len(plain), part))
        else:
            plain += part
    wrapped_plain = textwrap.fill(plain, width=width)
    # Reinsert ANSI codes at their original character positions
    result = []
    ti = 0
    for i, ch in enumerate(wrapped_plain):
        while ti < len(tokens) and tokens[ti][0] <= i:
            # Adjust: tokens map to original plain positions, but wrapped may have
            # replaced spaces with newlines. Use a simpler approach.
            pass
            ti += 1
        result.append(ch)
    # Simpler approach: just wrap with ANSI by splitting and rejoining
    # Remove ANSI, wrap, then try to preserve leading ANSI per original line
    leading_ansi = ''
    m = re.match(r'^(\x1b\[[0-9;]*m)+', line)
    if m:
        leading_ansi = m.group(0)
    trailing_ansi = ''
    m2 = re.search(r'(\x1b\[[0-9;]*m)+$', line)
    if m2:
        trailing_ansi = m2.group(0)
    wrapped = textwrap.fill(stripped, width=width)
    # Re-apply leading ANSI to each wrapped line
    lines = wrapped.split('\n')
    return '\n'.join(leading_ansi + l for l in lines) + (trailing_ansi if trailing_ansi and not lines[-1].endswith(trailing_ansi) else '')

def _wrap_text(text: str, width: int = 80) -> str:
    """Wrap multi-line text preserving newlines."""
    return '\n'.join(_wrap_line(line, width) for line in text.split('\n'))

from config import Config

# control characters never come from a player's keyboard: stripped from every line, so a
# `say` can't carry an escape sequence (a forged MAPSYNC) to other players' clients
_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')

# the web bridge's first line (web_client.py): its page lays text out itself, so the
# connection's messages are not hard-wrapped at 80 columns as a telnet terminal's are
WEB_MARK = b'\x1b]WEB\x07'
# ...or with the browser's own address, which the game counts sign-ups and email codes by
# (`\x1b]WEB:203.0.113.5\x07`)
WEB_MARK_RE = re.compile(rb'\x1b\]WEB(?::([0-9A-Fa-f.:]{2,45}))?\x07')

logger = logging.getLogger('Misthollow.Server')

# new names being made right now (lower case -> the Connection making it). A name is checked
# when it is typed but saved only after race, class and stats: the hold turns a second
# connection away at once, rather than after it has chosen everything
_naming = {}


class Connection:
    """Represents a single client connection."""
    
    STATE_GET_NAME = 0
    STATE_CONFIRM_NAME = 1
    STATE_GET_PASSWORD = 2
    STATE_CONFIRM_PASSWORD = 3
    STATE_GET_RACE = 4
    STATE_GET_CLASS = 5
    STATE_ROLLING_STATS = 6
    STATE_PLAYING = 7
    # Account system states
    STATE_ACCOUNT_PASSWORD = 10
    STATE_SELECT_CHAR = 11
    STATE_CREATE_CHAR_NAME = 12
    STATE_CHANGE_PASSWORD = 14
    STATE_CONFIRM_NEW_PASSWORD = 15
    STATE_CONFIRM_DELETE = 16
    STATE_GET_SEX = 17
    STATE_GET_STYLE = 18
    STATE_CLAIM_PASSWORD = 19
    STATE_GET_EMAIL = 20                # a sign-up's email (when emails are verified)
    STATE_VERIFY_CODE = 21              # the code mailed to it

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, server):
        self.reader = reader
        self.writer = writer
        self.server = server
        self.world = server.world
        self.config = server.config
        
        self.address = writer.get_extra_info('peername')
        self.connected_at = datetime.now()
        self.last_input = datetime.now()
        
        self.state = self.STATE_GET_NAME
        self.player = None
        self.input_buffer = []
        
        # Character creation temps
        self.temp_name = None
        self.temp_password = None
        self.temp_race = None
        self.temp_sex = None
        self.temp_class = None
        
        # Account system temps
        self.account = None
        self.temp_account_name = None
        self.play_after = None          # a character asked for by name, opened via its account
        self.held_name = None           # the new name this connection is making (_naming)
        self.new_account_only = False   # `newaccount`: the password makes an account, no hero
        self.temp_email = ''            # ...signing in by this email too
        self.code = None                # the email code asked for (security.new_code), and what for:
        self.code_for = ''              # 'signup', 'newaccount' or 'email' (a menu's new email)
        self.login_failures = 0         # wrong passwords on this connection (security.py)
        self.forgot_sent = False
        self.is_web = False             # the web bridge announced itself (WEB_MARK): no hard wrap
        # where the player is: this connection's own address, or the browser's one the web
        # bridge passes on (believed only from this machine: web_client.py)
        self.client_ip = self.address[0] if self.address else ''
        
        logger.info(f"New connection from {self.address}")
        
    async def send(self, message: str, newline: bool = True, kind: str = None):
        """Send a message to the client (kind: a msgkind the line is, for a web page)."""
        try:
            if message is None:
                return
            # Word-wrap for a telnet terminal (a web page wraps its own text); a web page is
            # told what kind each line is (msgkind.py: the blow-by-blow, a kill's reward), so
            # /play can keep its log for what isn't drawn, and is told how to do a thing with
            # its windows, not what to type (quest_guide.web_line)
            if not self.is_web:
                message = _wrap_text(message, 80)
            elif self.state == self.STATE_PLAYING:
                message = msgkind.mark(quest_guide.web_line(message), kind)
            # Convert all newlines to \r\n for telnet compatibility
            message = message.replace('\r\n', '\n').replace('\n', '\r\n')
            if newline and not message.endswith('\r\n'):
                message += '\r\n'
            self.writer.write(message.encode('utf-8'))
            await self.writer.drain()
        except asyncio.CancelledError:
            logger.debug(f"Send cancelled for {self.address}")
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
            logger.debug(f"Connection lost while sending to {self.address}")
        except Exception as e:
            logger.error(f"Error sending to {self.address}: {e}")
            
    async def send_prompt(self):
        """Send the appropriate prompt based on state."""
        if self.state == self.STATE_PLAYING and self.player:
            # Respect prompt toggle
            if not getattr(self.player, 'prompt_enabled', True):
                return
            
            c = self.config.COLORS
            hp_color = c['green'] if self.player.hp > self.player.max_hp * 0.5 else c['yellow'] if self.player.hp > self.player.max_hp * 0.25 else c['red']

            # Sneaking indicator
            sneak_status = ""
            if hasattr(self.player, 'flags') and 'sneaking' in self.player.flags:
                sneak_status = f" {c['bright_black']}[sneaking]{c['reset']}"
            
            # Add enemy health if fighting
            enemy_status = ""
            if self.player.is_fighting and self.player.fighting:
                enemy = self.player.fighting
                enemy_hp_pct = (enemy.hp / enemy.max_hp) * 100
                enemy_color = c['bright_green'] if enemy_hp_pct > 75 else c['green'] if enemy_hp_pct > 50 else c['yellow'] if enemy_hp_pct > 25 else c['red']
                enemy_status = f" {c['white']}[{enemy_color}{enemy.name}: {enemy.hp}/{enemy.max_hp}{c['white']}]{c['reset']}"

            # Custom prompt support
            custom = getattr(self.player, 'custom_prompt', None)
            if custom:
                hp_pct = int((self.player.hp / self.player.max_hp) * 100) if self.player.max_hp > 0 else 0
                mana_pct = int((self.player.mana / self.player.max_mana) * 100) if self.player.max_mana > 0 else 0
                move_pct = int((self.player.move / self.player.max_move) * 100) if self.player.max_move > 0 else 0
                
                prompt = custom
                prompt = prompt.replace('%h', str(self.player.hp))
                prompt = prompt.replace('%H', str(self.player.max_hp))
                prompt = prompt.replace('%m', str(self.player.mana))
                prompt = prompt.replace('%M', str(self.player.max_mana))
                prompt = prompt.replace('%v', str(self.player.move))
                prompt = prompt.replace('%V', str(self.player.max_move))
                prompt = prompt.replace('%g', str(self.player.gold))
                prompt = prompt.replace('%x', str(self.player.exp))
                prompt = prompt.replace('%p', str(hp_pct))
                prompt = prompt.replace('%q', str(mana_pct))
                prompt = prompt.replace('%r', str(move_pct))
                prompt = prompt.replace('%n', '\r\n')
                
                prompt = f"\r\n{prompt} {enemy_status}{c['reset']}> "
                await self.send(prompt, newline=False)
                return

            # Warrior Momentum display in prompt
            momentum_status = ""
            if getattr(self.player, 'char_class', '').lower() == 'warrior':
                mom = getattr(self.player, 'momentum', 0)
                if mom > 0:
                    filled = '█' * mom
                    empty = '░' * (10 - mom)
                    momentum_status = f" {c['bright_yellow']}[Momentum: {filled}{empty} {mom}/10]{c['reset']}"
                    if getattr(self.player, 'unstoppable_rounds', 0) > 0:
                        momentum_status += f" {c['bright_red']}★UNSTOPPABLE★{c['reset']}"

            prompt = f"\r\n{hp_color}{self.player.hp}/{self.player.max_hp}hp {c['cyan']}{self.player.mana}/{self.player.max_mana}mp {c['yellow']}{self.player.move}/{self.player.max_move}mv{sneak_status}{momentum_status}{enemy_status}{c['reset']}> "
            await self.send(prompt, newline=False)
        else:
            await self.send("> ", newline=False)
            
    async def handle_input(self, line: str):
        """Process input based on current state."""
        line = line.strip()
        self.last_input = datetime.now()
        
        if self.state == self.STATE_GET_NAME:
            await self.handle_name(line)
        elif self.state == self.STATE_CONFIRM_NAME:
            await self.handle_confirm_name(line)
        elif self.state == self.STATE_GET_PASSWORD:
            await self.handle_password(line)
        elif self.state == self.STATE_CONFIRM_PASSWORD:
            await self.handle_confirm_new_char_password(line)
        elif self.state == self.STATE_GET_RACE:
            await self.handle_race(line)
        elif self.state == self.STATE_GET_SEX:
            await self.handle_sex(line)
        elif self.state == self.STATE_GET_CLASS:
            await self.handle_class(line)
        elif self.state == self.STATE_GET_STYLE:
            await self.handle_style(line)
        elif self.state == self.STATE_ROLLING_STATS:
            await self.handle_stats(line)
        elif self.state == self.STATE_PLAYING:
            await self.handle_command(line)
        # Account system states
        elif self.state == self.STATE_ACCOUNT_PASSWORD:
            await self.handle_account_password(line)
        elif self.state == self.STATE_SELECT_CHAR:
            await self.handle_select_char(line)
        elif self.state == self.STATE_CREATE_CHAR_NAME:
            await self.handle_create_char_name(line)
        elif self.state == self.STATE_CLAIM_PASSWORD:
            await self.handle_claim_password(line)
        elif self.state == self.STATE_CHANGE_PASSWORD:
            await self.handle_change_password(line)
        elif self.state == self.STATE_CONFIRM_NEW_PASSWORD:
            await self.handle_confirm_password(line)
        elif self.state == self.STATE_CONFIRM_DELETE:
            await self.handle_confirm_delete(line)
        elif self.state == self.STATE_GET_EMAIL:
            await self.handle_signup_email(line)
        elif self.state == self.STATE_VERIFY_CODE:
            await self.handle_verify_code(line)

    async def handle_name(self, name: str):
        """Handle name/account entry."""
        if not name:
            await self.send("Enter account name (or character name): ")
            return

        # a web client coming back with its sign-in token (security.py)
        if name.lower().startswith('resume '):
            await self.handle_resume(name.split())
            return

        from accounts import AccountManager, name_problem, name_taken, email_problem, verification_on
        # `newaccount <name> [<email>]`: an account with no character yet (/play's Create
        # account), signing in by its email too; its menu's create makes the heroes, of any free
        # names. When the server can send mail, the email is needed and proves itself with a code.
        if name.lower().startswith('newaccount '):
            parts = name.split()
            want, email = parts[1], (parts[2] if len(parts) > 2 else '')
            # (held last: a refusal for anything else leaves the name free)
            why = (name_problem(want) or ("That name is already taken." if name_taken(want) else '')
                   or (email_problem(email) if email else '') or ('Usage: newaccount <name> [<email>]' if len(parts) > 3 else '')
                   or ("An email is needed: newaccount <name> <email>. A code will be sent to it."
                       if not email and verification_on() else '')
                   or ("That name is already taken." if not self._hold_name(want) else ''))
            if why:
                await self.send(why)
                await self.send("Enter account name (or character name): ")
                return
            self.temp_account_name = want.lower()
            self.temp_email = email
            self.temp_name = None
            self.new_account_only = True
            await self.send(f"Choose a password for the account {want.capitalize()}: ")
            self.state = self.STATE_GET_PASSWORD
            return
        # an email: the account that signs in by it
        if '@' in name:
            account = AccountManager.find_by_email(name)
            if account is None:
                await self.send(f"No account uses the email {name}.")
                await self.send("Enter account name (or character name): ")
                return
            self.temp_account_name = account.account_name
            self.play_after = self.login_alt = None
            await self.send("Account password: ")
            self.state = self.STATE_ACCOUNT_PASSWORD
            return
        why = name_problem(name)
        if why:
            await self.send(why)
            await self.send("Enter account name (or character name): ")
            return
        
        name_lower = name.lower()
        name_cap = name.capitalize()
        
        # an account by that name, or the account of the character by that name: its password
        # (the account's) is the only way in
        choices = AccountManager.login_choices(name_lower)
        if choices:
            account, char_name = choices[0]
            # (a character of that name on another account: its password is tried next)
            self.login_alt = (choices[1][0].account_name, choices[1][1]) if len(choices) > 1 else None
            self.temp_account_name = account.account_name
            if char_name:
                self.play_after = char_name
                await self.send(f"{char_name} belongs to an account. Account password: ")
            else:
                await self.send(f"Account password: ")
            self.state = self.STATE_ACCOUNT_PASSWORD
            return
        if name_taken(name_lower):
            # a character with no account and no password (accounts.migrate_saves left it)
            await self.send(f"{name_cap} can't be logged into: it has no account. Ask an immortal for help.")
            await self.send("Enter account name (or character name): ")
            return
        
        # A new name: a new account, and its first character of the same name
        if not self._hold_name(name_lower):
            await self.send(f"'{name_cap}' is already taken: someone is making it right now.")
            await self.send("Enter account name (or character name): ")
            return
        self.temp_account_name = name_lower
        self.temp_name = name_cap
        await self.send(f"'{name_cap}' is a new name. Create account? (Y/N) ")
        self.state = self.STATE_CONFIRM_NAME
            
    async def handle_confirm_name(self, response: str):
        """Confirm new character name."""
        if response.lower() in ('y', 'yes'):
            await self.send("Choose a password: ")
            self.state = self.STATE_GET_PASSWORD
        else:
            self._let_name_go()
            self.temp_name = self.temp_account_name = None
            await self.send("What name shall you be known by? ")
            self.state = self.STATE_GET_NAME

    def _hold_name(self, name: str) -> bool:
        """Hold a new name while this connection makes it (False: another connection is)."""
        key = name.lower()
        holder = _naming.get(key)
        if (holder is not None and holder is not self and not getattr(holder, '_disconnected', False)
                and not holder.writer.is_closing()):
            return False
        self._let_name_go()
        _naming[key] = self
        self.held_name = key
        return True

    def _let_name_go(self):
        if self.held_name and _naming.get(self.held_name) is self:
            del _naming[self.held_name]
        self.held_name = None

    async def handle_password(self, password: str):
        """The new account's password (a sign-up: the account and its first character are
        made together when the character is finished)."""
        if not password:
            await self.send("Password cannot be empty. Enter password: ")
            return
        import security
        why = security.weak(password)
        if why:
            await self.send(f"{why} Enter password: ")
            return
        self.temp_password = password
        await self.send("Confirm password: ")
        self.state = self.STATE_CONFIRM_PASSWORD
            
    async def handle_confirm_new_char_password(self, password: str):
        """Confirm new character password. When the server can send mail, the email proves
        itself with a code before anything is made (the sign-up's email is asked for here;
        `newaccount` brought its own)."""
        if password != self.temp_password:
            await self.send("Passwords don't match. Enter password: ")
            self.temp_password = None
            self.state = self.STATE_GET_PASSWORD
            return
        from accounts import verification_on
        if verification_on():
            if self.new_account_only:
                await self._mail_signup_code()
            else:
                await self.send("Your email (a code will be sent to it, and you can sign in by it): ")
                self.state = self.STATE_GET_EMAIL
            return
        await self._signup_settled()

    async def _signup_settled(self):
        """A sign-up's password (and email) settled: `newaccount`'s account alone, then its
        menu; or the sign-up's first hero, race first."""
        if not self.new_account_only:
            await self.show_race_menu()
            self.state = self.STATE_GET_RACE
            return
        from accounts import AccountManager
        self.new_account_only = False
        account, why = await AccountManager.create_account(self.temp_account_name, self.temp_password, self.temp_email)
        self.temp_email = ''
        self.temp_password = None
        self._let_name_go()
        if account is None:
            self.temp_account_name = None
            await self.send(f"{why} The account was not made.")
            await self.send("Enter account name (or character name): ")
            self.state = self.STATE_GET_NAME
            return
        self.account = account
        await self.send(f"Account {account.account_name} made.")
        await self.show_character_menu()

    async def handle_signup_email(self, email: str):
        """The sign-up's email (nothing typed: start over)."""
        from accounts import email_problem
        if not email:
            await self._abandon_signup("Sign-up stopped: nothing was made.")
            return
        why = email_problem(email)
        if why:
            await self.send(f"{why} Your email: ")
            return
        self.temp_email = email.strip()
        await self._mail_signup_code()

    async def _mail_code(self, email: str, purpose: str) -> str:
        """Mail a code to `email`, kept for `purpose` ('signup', 'newaccount', 'email'): '' when
        it went, else why not (too many lately, or the mail failed)."""
        import security
        from accounts import send_code
        why = security.code_send_allowed(email, self.client_ip)
        if why:
            return why
        code, kept = security.new_code()
        if not await asyncio.to_thread(send_code, email, code):
            return f"A code couldn't be sent to {email}. Check the address, or try again later."
        self.code, self.code_for = kept, purpose
        logger.info(f"Email code sent for {purpose} ({self.temp_account_name or (self.account and self.account.account_name)}) from {self.client_ip}")
        return ''

    async def _mail_signup_code(self):
        why = await self._mail_code(self.temp_email, 'newaccount' if self.new_account_only else 'signup')
        if why:
            await self._abandon_signup(f"{why} Nothing was made.")
            return
        await self.send(f"A code has been sent to {self.temp_email}. Enter the 6-digit code "
                        f"('resend' for another, or nothing to start over): ")
        self.state = self.STATE_VERIFY_CODE

    async def handle_verify_code(self, line: str):
        """The code mailed for a sign-up: right, it goes on; wrong, it asks again (five tries)."""
        import security
        if not line:
            await self._abandon_signup("Sign-up stopped: nothing was made.")
            return
        if line.lower() == 'resend':
            await self._mail_signup_code()
            return
        result = security.check_code(self.code, line)
        if result == 'ok':
            self.code = None
            await self._signup_settled()
        elif result == 'wrong':
            await self.send("That code isn't right. Enter the 6-digit code: ")
        elif result == 'expired':
            await self.send("That code has expired. Type 'resend' for a new one: ")
        else:
            await self._abandon_signup("Too many wrong codes: nothing was made. Start again.")

    async def _abandon_signup(self, why: str):
        """A sign-up given up: nothing of it is kept, and the name prompt comes back."""
        self.temp_password = self.temp_name = self.temp_account_name = self.code = None
        self.temp_email = ''
        self.new_account_only = False
        self._let_name_go()
        await self.send(why)
        await self.send("Enter account name (or character name): ")
        self.state = self.STATE_GET_NAME
            
    async def show_race_menu(self):
        """Display race selection menu."""
        c = self.config.COLORS
        await self.send(f"\r\n{c['cyan']}================================================================{c['reset']}")
        await self.send(f"{c['cyan']}                    Choose Your Race                          {c['reset']}")
        await self.send(f"{c['cyan']}================================================================{c['reset']}")

        for i, (race_id, race) in enumerate(self.config.RACES.items(), 1):
            mods = ' '.join([f"{stat[:3].upper()}:{mod:+d}" for stat, mod in race['stat_mods'].items() if mod != 0])
            await self.send(f" {c['bright_yellow']}{i}){c['reset']} {c['bright_green']}{race_id:<12}{c['white']}{race['description']}{c['reset']}")
            if mods:
                await self.send(f"              {c['yellow']}({mods}){c['reset']}")

        await self.send(f"{c['cyan']}================================================================{c['reset']}")
        await self.send(f"\r\n{c['white']}Enter race name or number: {c['reset']}")
        
    async def handle_race(self, race: str):
        """Handle race selection."""
        race = race.strip().lower().replace(' ', '_')
        
        # Accept number selection
        if race.isdigit():
            idx = int(race) - 1
            race_list = list(self.config.RACES.keys())
            if 0 <= idx < len(race_list):
                race = race_list[idx]
            else:
                await self.send(f"Invalid selection. Choose 1-{len(race_list)} or enter race name.")
                await self.send("Enter race name or number: ")
                return
        
        if race not in self.config.RACES:
            await self.send(f"'{race}' is not a valid race. Choose from: {', '.join(self.config.RACES.keys())}")
            await self.send("Enter race name or number: ")
            return
            
        self.temp_race = race
        await self.show_sex_menu()
        self.state = self.STATE_GET_SEX

    async def show_sex_menu(self):
        """Ask whether the character is male or female (words, and the 3D hero's face and build)."""
        c = self.config.COLORS
        await self.send(f"\r\n {c['bright_yellow']}1){c['reset']} {c['bright_green']}male{c['reset']}")
        await self.send(f" {c['bright_yellow']}2){c['reset']} {c['bright_green']}female{c['reset']}")
        await self.send(f"\r\n{c['white']}Is your character male or female? {c['reset']}")

    async def handle_sex(self, answer: str):
        """Handle the male/female choice."""
        a = answer.strip().lower()
        sex = {'1': 'male', 'm': 'male', 'male': 'male', '2': 'female', 'f': 'female', 'female': 'female'}.get(a)
        if not sex:
            await self.send("Please choose male or female (1 or 2).")
            await self.send("Is your character male or female? ")
            return
        self.temp_sex = sex
        await self.show_class_menu()
        self.state = self.STATE_GET_CLASS
        
    async def show_class_menu(self):
        """Display class selection menu."""
        c = self.config.COLORS
        await self.send(f"\r\n{c['cyan']}================================================================{c['reset']}")
        await self.send(f"{c['cyan']}                    Choose Your Class                         {c['reset']}")
        await self.send(f"{c['cyan']}================================================================{c['reset']}")

        for i, (class_id, cls) in enumerate(self.config.CLASSES.items(), 1):
            await self.send(f" {c['bright_yellow']}{i}){c['reset']} {c['bright_green']}{class_id:<12}{c['white']}{cls['description']}{c['reset']}")
            await self.send(f"              {c['yellow']}Prime: {cls['prime_stat'].upper():<3} HP:{cls['hit_dice']:>2}  MP:{cls['mana_dice']:>2}{c['reset']}")

        await self.send(f"{c['cyan']}================================================================{c['reset']}")
        await self.send(f"\r\n{c['white']}Enter class name or number: {c['reset']}")
        
    async def handle_class(self, char_class: str):
        """Handle class selection."""
        char_class = char_class.strip().lower()
        
        # Accept number selection
        if char_class.isdigit():
            idx = int(char_class) - 1
            class_list = list(self.config.CLASSES.keys())
            if 0 <= idx < len(class_list):
                char_class = class_list[idx]
            else:
                await self.send(f"Invalid selection. Choose 1-{len(class_list)} or enter class name.")
                await self.send("Enter class name or number: ")
                return
        
        if char_class not in self.config.CLASSES:
            await self.send(f"'{char_class}' is not a valid class. Choose from: {', '.join(self.config.CLASSES.keys())}")
            await self.send("Enter class name or number: ")
            return
            
        self.temp_class = char_class
        self.temp_style = ''
        if char_class == 'mage':
            await self.show_style_menu()
            self.state = self.STATE_GET_STYLE
            return
        await self.show_stats()
        self.state = self.STATE_ROLLING_STATS

    async def show_style_menu(self):
        """A mage chooses their look in the 3D world: the classic mage, or the archmage (a tall hat,
        a long white beard, a robe to the ankles and a moon staff). 'appearance' changes it later."""
        c = self.config.COLORS
        await self.send(f"\r\n {c['bright_yellow']}1){c['reset']} {c['bright_green']}classic{c['reset']}   {c['white']}the young mage in a travelling coat{c['reset']}")
        await self.send(f" {c['bright_yellow']}2){c['reset']} {c['bright_green']}archmage{c['reset']}  {c['white']}a tall hat, a long white beard, a robe to the ankles{c['reset']}")
        await self.send(f"\r\n{c['white']}Which look, classic or archmage? {c['reset']}")

    async def handle_style(self, answer: str):
        a = answer.strip().lower()
        style = {'1': '', 'classic': '', 'c': '', '2': 'archmage', 'archmage': 'archmage', 'a': 'archmage'}.get(a)
        if style is None:
            await self.send("Please choose classic or archmage (1 or 2).")
            await self.send("Which look, classic or archmage? ")
            return
        self.temp_style = style
        await self.show_stats()
        self.state = self.STATE_ROLLING_STATS
        
    async def show_stats(self):
        """Show rolled stats and ask for confirmation."""
        import random
        
        # Roll stats
        self.temp_stats = {}
        for stat in ['str', 'int', 'wis', 'dex', 'con', 'cha']:
            # Roll 4d6, drop lowest
            rolls = sorted([random.randint(1, 6) for _ in range(4)], reverse=True)[:3]
            base = sum(rolls)
            # Apply racial modifiers
            mod = self.config.RACES[self.temp_race]['stat_mods'].get(stat, 0)
            self.temp_stats[stat] = max(self.config.MIN_STAT, min(self.config.MAX_STAT, base + mod))
        
        c = self.config.COLORS
        await self.send(f"\r\n{c['cyan']}═══════════════ Your Statistics ═══════════════{c['reset']}")
        await self.send(f"{c['bright_red']}Strength:     {self.temp_stats['str']:>2}{c['reset']}")
        await self.send(f"{c['bright_blue']}Intelligence: {self.temp_stats['int']:>2}{c['reset']}")
        await self.send(f"{c['bright_cyan']}Wisdom:       {self.temp_stats['wis']:>2}{c['reset']}")
        await self.send(f"{c['bright_green']}Dexterity:    {self.temp_stats['dex']:>2}{c['reset']}")
        await self.send(f"{c['bright_yellow']}Constitution: {self.temp_stats['con']:>2}{c['reset']}")
        await self.send(f"{c['bright_magenta']}Charisma:     {self.temp_stats['cha']:>2}{c['reset']}")
        await self.send(f"{c['cyan']}═════════════════════════════════════════════{c['reset']}")
        await self.send(f"\r\n{c['white']}Accept these stats? (Y)es, (N)o to reroll: {c['reset']}")
        
    async def handle_stats(self, response: str):
        """Handle stat confirmation."""
        if response.lower() in ('y', 'yes'):
            await self.create_character()
        else:
            await self.show_stats()
            
    async def create_character(self):
        """Create the new character: on the account logged into, or (a sign-up) on a new
        account of its name, made with it (accounts.AccountManager)."""
        from accounts import AccountManager
        char = dict(race=self.temp_race, char_class=self.temp_class, stats=self.temp_stats, world=self.world,
                    sex=self.temp_sex or 'neutral', look_style=getattr(self, 'temp_style', '') or '')
        if self.account:
            self.player, why = await AccountManager.create_character(self.account, self.temp_name, **char)
        else:
            self.account, self.player, why = await AccountManager.sign_up(self.temp_account_name, self.temp_password or '',
                                                                          email=self.temp_email, **char)
        self.temp_password = None
        self.temp_email = ''
        self._let_name_go()
        if self.player is None:
            # the name was taken while the character was being made
            await self.send(f"{why} Your character was not made.")
            if self.account:
                await self.show_character_menu()
            else:
                self.temp_name = self.temp_account_name = None
                await self.send("Enter account name (or character name): ")
                self.state = self.STATE_GET_NAME
            return
        await self.enter_game()
        
    async def enter_game(self):
        """Enter the game world."""
        # Already playing (another window, or a connection that dropped and hasn't timed
        # out): this connection takes the character over. Nothing is loaded twice, and the
        # old session neither saves a stale copy nor removes the live one from the world.
        existing = self.world.players.get(self.player.name.lower()) if self.player else None
        if existing is not None and existing is not self.player:
            await self._take_over(existing)
            return
        self.state = self.STATE_PLAYING
        self.player.connection = self
        
        # Track login info for account system
        from datetime import datetime
        self.player.last_login = datetime.now()
        self.player.last_host = self.address[0] if self.address else 'Unknown'
        
        # Move to starting room before adding to world
        room = self.world.login_room(self.player)
        if room:
            self.player.room = room

        # Add player to world
        await self.world.add_player(self.player)
        
        # Show welcome message
        c = self.config.COLORS
        await self.send(f"\r\n{c['bright_cyan']}══════════════════════════════════════════════════════════════{c['reset']}")
        await self.send(f"{c['bright_yellow']}  Welcome to Misthollow, {self.player.name}!{c['reset']}")
        await self.send(f"{c['white']}  A world of quests, combat, crafting, and adventure awaits.{c['reset']}")
        await self.send(f"{c['white']}  Type {c['bright_green']}help newbie{c['white']} for a new player guide, or {c['bright_green']}hint{c['white']} for tips.{c['reset']}")
        await self.send(f"{c['bright_cyan']}══════════════════════════════════════════════════════════════{c['reset']}\r\n")

        # Process rent charges from previous session
        try:
            rent_data = getattr(self.player, 'rent_data', None)
            if rent_data and rent_data.get('rented'):
                from datetime import datetime
                rent_time = datetime.fromisoformat(rent_data['rent_time'])
                elapsed = (datetime.now() - rent_time).total_seconds()
                days_elapsed = max(1, elapsed / 86400)  # At least 1 day charge
                daily_cost = rent_data.get('daily_cost', 0)
                total_charge = int(daily_cost * days_elapsed)

                if total_charge > 0:
                    if self.player.gold >= total_charge:
                        self.player.gold -= total_charge
                        await self.send(f"{c['bright_yellow']}The innkeeper collected {total_charge} gold for {days_elapsed:.1f} days of storage.{c['reset']}")
                    else:
                        # Player can't afford - drop random items
                        shortfall = total_charge - self.player.gold
                        self.player.gold = 0
                        dropped = 0
                        while shortfall > 0 and self.player.inventory:
                            item = self.player.inventory.pop()
                            item_rent = 10  # base value of dropped item
                            shortfall -= getattr(item, 'value', getattr(item, 'cost', 50))
                            dropped += 1
                        await self.send(f"{c['red']}You couldn't afford {total_charge} gold in rent!{c['reset']}")
                        if dropped:
                            await self.send(f"{c['red']}The innkeeper confiscated {dropped} item(s) to cover the debt.{c['reset']}")
                        await self.send(f"{c['yellow']}You have {self.player.gold} gold remaining.{c['reset']}")

                # Clear rent data
                self.player.rent_data = None
        except Exception as e:
            import logging
            logging.getLogger('Misthollow').error(f"Rent processing error: {e}")

        # Learn by doing (mastery.py): a character made before it catches up on everything
        # its level has reached
        try:
            import mastery
            caught = mastery.grant_now(self.player)
            if caught:
                names = ', '.join(mastery.name_of(a) for a, _k in caught[:6]) + (', …' if len(caught) > 6 else '')
                await self.send(f"{c['bright_yellow']}Your training catches up with your level: {len(caught)} new "
                                f"abilit{'y' if len(caught) == 1 else 'ies'} ({names}). Abilities now grow as you use them; "
                                f"type 'skills' (or press K in /play).{c['reset']}")
        except Exception as e:
            import logging
            logging.getLogger('Misthollow').error(f"Ability catch-up error: {e}")

        # a class wears only what it is trained in (class_gear.py): an older character puts the rest away
        try:
            import class_gear
            await class_gear.shed(self.player)
        except Exception as e:
            import logging
            logging.getLogger('Misthollow').error(f"Class gear check error: {e}")

        if room:
            room.characters.append(self.player)
            
            # Initialize explored_rooms and add starting room for map
            if not hasattr(self.player, 'explored_rooms'):
                self.player.explored_rooms = set()
            self.player.explored_rooms.add(room.vnum)
            
            # Announce arrival
            await room.send_to_room(f"{self.player.name} has entered the realm.", exclude=[self.player])
            # graphical clients already in the room see the newcomer at once
            wm = getattr(self.player.world, 'web_map', None)
            if wm:
                try:
                    await wm.notify_room(room, {'type': 'player_move', 'name': self.player.name, 'action': 'arrive', 'to': room.vnum})
                except Exception:
                    pass
            
            # Daily login bonus check
            try:
                from daily import DailyBonusManager
                await DailyBonusManager.check_daily_bonus(self.player)
            except Exception:
                pass
            
            # Mark explored on login
            try:
                from achievements import AchievementManager
                await AchievementManager.check_exploration(self.player, getattr(self.player.room, 'vnum', 0))
            except Exception:
                pass

            # Waypoint discovery
            try:
                from travel import discover_waypoint
                discovered = discover_waypoint(self.player, getattr(self.player.room, 'vnum', 0))
                if discovered:
                    key, info = discovered
                    await self.player.send(f"{c['bright_cyan']}Waypoint discovered: {info['name']}{c['reset']}")
            except Exception:
                pass

            # Show room
            await self.player.do_look([])

            # Room entry triggers (Sage Aldric greeting, etc.)
            try:
                from commands import CommandHandler
                await CommandHandler._room_entry_triggers(self.player)
            except Exception as e:
                import logging
                logging.getLogger('Misthollow').error(f"Room entry trigger error: {e}")

            # Web map update
            if hasattr(self.world, 'web_map') and self.world.web_map:
                await self.world.web_map.notify_player(self.player)
            
            # Send map sync signal for web client (hidden control message), with this
            # session's secret for the map server
            await self._issue_web_token()
            
            # Start tutorial for new players (level 1, no quests completed)
            if self.player.level == 1 and not getattr(self.player, 'quests_completed', []):
                try:
                    from quests import QuestManager
                    await QuestManager.start_tutorial(self.player)
                except Exception:
                    pass

            # Check for unread mail
            try:
                from mail_system import MailManager
                unread = MailManager.get_unread_count(self.player.name)
                self.player.mail_unread = unread     # the page's envelope (web_hud.py)
                if unread > 0:
                    await self.send(f"{c['bright_yellow']}You have {unread} unread mail message{'s' if unread != 1 else ''}! Type 'mail read' to read.{c['reset']}", kind=msgkind.UI)
            except Exception:
                pass

            # Show a tip to newer players
            try:
                if self.player.level < 15:
                    from tips import TipManager
                    await TipManager.maybe_show_tip(self.player, chance=0.3)
            except Exception:
                pass

        await self.send_prompt()
    
    # ==================== ACCOUNT SYSTEM HANDLERS ====================
    
    async def handle_account_password(self, password: str):
        """Handle account password entry."""
        if not password:
            await self.send("Password cannot be empty. Account password: ")
            return
        
        # Forgot/reset flow
        if password.lower().startswith('forgot'):
            from accounts import Account, AccountManager
            import security
            account = Account.load(self.temp_account_name)
            if not account or not account.settings.get('email'):
                await self.send("No email on file for this account.")
                await self.send("Set one after login with: account email <address>")
                await self.send("Account password: ")
                return
            if self.forgot_sent or not security.forgot_allowed(account.account_name):
                await self.send("A reset email was sent recently. Check your inbox, or try again in 15 minutes.")
                await self.send("Account password: ")
                return
            self.forgot_sent = True
            token = AccountManager.generate_reset_token(account)
            sent = AccountManager.send_reset_email(account, token)
            if sent:
                await self.send("Reset email sent. Check your inbox for the token.")
                await self.send("You can reset here with: reset <token> <newpass>")
            else:
                await self.send("Email not configured. Contact an admin to reset.")
            await self.send("Account password: ")
            return
        
        if password.lower().startswith('reset '):
            parts = password.split()
            if len(parts) < 3:
                await self.send("Usage: reset <token> <newpass>")
                await self.send("Account password: ")
                return
            token = parts[1]
            new_pw = parts[2]
            from accounts import AccountManager
            import security
            why = security.weak(new_pw)
            if why:
                await self.send(why)
                await self.send("Account password: ")
                return
            ok = await AccountManager.reset_with_token(self.temp_account_name, token, new_pw)
            if ok:
                await self.send("Password reset! Please log in with your new password.")
            else:
                await self.send("Invalid or expired token.")
            await self.send("Account password: ")
            return
        
        from accounts import AccountManager
        import security
        wait = security.locked(self.temp_account_name)
        if wait:
            await self._locked_out(wait)
            return
        self.account = await AccountManager.authenticate(self.temp_account_name, password)
        alt, self.login_alt = getattr(self, 'login_alt', None), None
        if self.account is None and alt and not security.locked(alt[0]):
            # the name is an account's and another account's character's: that one's password
            self.account = await AccountManager.authenticate(alt[0], password)
            if self.account:
                self.temp_account_name, self.play_after = alt
        
        if self.account:
            security.succeeded(self.temp_account_name)
            # asked for one of its characters by name: straight in (a web page always shows the
            # account's heroes: one login, every hero)
            wanted, self.play_after = self.play_after, None
            if wanted and wanted in self.account.characters and not self.is_web:
                from player import Player
                self.player = Player.load(wanted, self.world)
                if self.player:
                    self.player.account_name = self.account.account_name
                    await self.enter_game()
                    return
            await self.show_character_menu()
        else:
            await self._wrong_password(self.temp_account_name, "Invalid password!")
            self.temp_account_name = None
            self.play_after = None
            if not self.writer.is_closing():
                await self.send("\r\nEnter account name (or character name): ")
            self.state = self.STATE_GET_NAME

    @staticmethod
    def _account_of(player_file: str):
        """The account a saved character belongs to ('' when none)."""
        try:
            import json
            with open(player_file) as f:
                return (json.load(f).get('account_name') or '').lower()
        except (OSError, ValueError):
            return ''

    async def _wrong_password(self, name: str, line: str = "Wrong password!"):
        """Count a failed login: the name locks after five in ten minutes, and this
        connection closes after three."""
        import security
        security.failed(name)
        self.login_failures += 1
        logger.warning(f"Failed login for '{name}' from {self.address}")
        await self.send(line)
        if self.login_failures >= security.FAILS_PER_CONNECTION:
            await self.send("Too many failed attempts. Goodbye.")
            self.writer.close()

    async def _locked_out(self, wait: int):
        mins = max(1, (wait + 59) // 60)
        await self.send(f"Too many failed logins for that name. Try again in {mins} minute{'s' if mins != 1 else ''}.")
        self.temp_account_name = None
        self.temp_name = None
        self.play_after = None
        await self.send("Enter account name (or character name): ")
        self.state = self.STATE_GET_NAME

    async def handle_resume(self, parts):
        """`resume <name> <token>` from a web client: the device token stands in for the
        password once, and is swapped for a fresh one (security.py)."""
        import security
        from player import Player
        name = parts[1] if len(parts) == 3 else ''
        token = parts[2] if len(parts) == 3 else ''
        player = None
        if name.isalpha() and 3 <= len(name) <= 12:
            fresh = security.use_token(name, token)
            if fresh:
                player = Player.load(name.capitalize(), self.world)
                if player is None:
                    security.forget_all(name)
        if player is None:
            await self.send("That sign-in has expired. Please log in with your password.")
            await self.send("Enter account name (or character name): ")
            return
        if getattr(player, 'account_name', None):
            from accounts import Account
            self.account = Account.load(player.account_name)
        self.player = player
        await self._send_raw(security.resume_signal(fresh))
        await self.enter_game()

    async def _send_raw(self, data: bytes):
        """Bytes straight to the client (a hidden signal must not be word-wrapped)."""
        try:
            self.writer.write(data)
            await self.writer.drain()
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
            pass
    
    async def show_character_menu(self, note: str = '', bad: bool = False):
        """Display character selection menu (note: what the last command did, which a web page
        shows over its list; bad: it was refused)."""
        c = self.config.COLORS
        from accounts import AccountManager
        
        await self.send(f"\r\n{c['bright_cyan']}════════════════════════════════════════════════════════════{c['reset']}")
        await self.send(f"{c['bright_yellow']}  Welcome back, {self.account.account_name}!{c['reset']}")
        await self.send(f"{c['bright_cyan']}════════════════════════════════════════════════════════════{c['reset']}")
        
        # Show commands first
        await self.send(f"\r\n{c['white']}Available commands:{c['reset']}")
        await self.send(f"  {c['bright_green']}create{c['reset']}                      - Create a new character")
        await self.send(f"  {c['bright_green']}play <name>{c['reset']}                 - Play the character <name>")
        await self.send(f"  {c['bright_green']}list [level|name]{c['reset']}           - List all your characters")
        await self.send(f"  {c['bright_green']}info <name>{c['reset']}                 - Show character info")
        await self.send(f"  {c['bright_green']}practice <name>{c['reset']}             - Show character skills")
        await self.send(f"  {c['bright_green']}move <name> <up|down> [n]{c['reset']}   - Reorder character list")
        await self.send(f"  {c['bright_green']}password{c['reset']}                    - Change account password")
        await self.send(f"  {c['bright_green']}email <address>{c['reset']}             - Sign in by this email (and get password resets)")
        await self.send(f"  {c['bright_green']}verify <code>{c['reset']}               - The code mailed for a new email")
        await self.send(f"  {c['bright_green']}delete <name>{c['reset']}               - Delete a character")
        await self.send(f"  {c['bright_green']}claim <name>{c['reset']}                - Move in a character from another account of yours")
        await self.send(f"  {c['bright_green']}time{c['reset']}                        - Display game time")
        await self.send(f"  {c['bright_green']}link{c['reset']}                        - Show connection info")
        await self.send(f"  {c['bright_green']}quit{c['reset']}                        - Disconnect")
        
        # Then show characters
        char_info = AccountManager.get_character_info(self.account)
        
        if char_info:
            await self.send(f"\r\n{c['white']}Your Characters:{c['reset']}")
            for i, info in enumerate(char_info, 1):
                await self.send(f"  {c['bright_green']}{i}) {info['name']:<12}{c['white']} Lvl {info['level']:<3} {info['class']:<12}{c['reset']}")
        else:
            await self.send(f"\r\n{c['yellow']}You have no characters yet. Type 'create' to make one!{c['reset']}")

        await self.send(f"\r\n{c['bright_cyan']}════════════════════════════════════════════════════════════{c['reset']}")
        self.state = self.STATE_SELECT_CHAR
        if self.is_web:
            # the page draws the menu itself: the account and its characters as a hidden signal
            # (web_client.py turns it into {type: 'account'})
            import json
            menu = {'account': self.account.account_name, 'max': self.account.settings.get('max_chars', 8),
                    'email': self.account.settings.get('email') or '', 'note': note, 'bad': bad,
                    'pending': self.temp_email if self.code_for == 'email' and self.code else '',
                    'chars': [{k: i[k] for k in ('name', 'level', 'class', 'race')} for i in char_info]}
            await self._send_raw(f"\x1b]ACCOUNT:{json.dumps(menu, separators=(',', ':'))}\x07".encode('utf-8'))
    
    async def show_account_help(self):
        """Display detailed account menu help."""
        c = self.config.COLORS
        await self.send(f"\r\n{c['bright_yellow']}Account Commands:{c['reset']}")
        await self.send(f"  {c['bright_green']}create{c['reset']}              - Create a new character")
        await self.send(f"  {c['bright_green']}play <name>{c['reset']}         - Play the character <name>")
        await self.send(f"  {c['bright_green']}time{c['reset']}                - Display the game time")
        await self.send(f"  {c['bright_green']}list [<sort>]{c['reset']}       - List all your characters")
        await self.send(f"  {c['bright_green']}move <name> <up|down> [n]{c['reset']} - Move character in list")
        await self.send(f"  {c['bright_green']}password{c['reset']}            - Change your account password")
        await self.send(f"  {c['bright_green']}info <name>{c['reset']}         - Show information about character")
        await self.send(f"  {c['bright_green']}practice <name>{c['reset']}     - Show skills practiced for character")
        await self.send(f"  {c['bright_green']}link{c['reset']}                - Show information about your connection")
        await self.send(f"  {c['bright_green']}lag{c['reset']}                 - Show network latency")
        await self.send(f"  {c['bright_green']}delete <name>{c['reset']}       - Delete a character (permanent!)")
        await self.send(f"  {c['bright_green']}claim <name>{c['reset']}        - Move in a character from another account of yours")
        await self.send(f"  {c['bright_green']}menu{c['reset']}                - Show this menu again")
        await self.send(f"  {c['bright_green']}help{c['reset']}                - Display this help")
        await self.send(f"  {c['bright_green']}quit{c['reset']}                - Leave the account menu")
    
    async def show_character_list(self, sort_by: str = None):
        """Display detailed character list with columns."""
        c = self.config.COLORS
        from player import Player
        from datetime import datetime
        
        await self.send(f"\r\n{c['bright_cyan']}Characters in account \"{self.account.account_name}\"{c['reset']}")
        
        # Header
        await self.send(f"{c['white']}Name         Rce  Cls  Lvl  Last Login       Area            Host{c['reset']}")
        await self.send(f"{c['bright_black']}{'─' * 80}{c['reset']}")
        
        char_list = []
        for char_name in self.account.characters:
            info = Player.get_info(char_name)
            if info:
                # Calculate last login relative time
                last_login = info.get('last_login')
                if last_login:
                    try:
                        login_dt = datetime.fromisoformat(last_login)
                        delta = datetime.now() - login_dt
                        if delta.days > 365:
                            login_str = f"{delta.days // 365} yrs"
                        elif delta.days > 30:
                            login_str = f"{delta.days // 30} mths"
                        elif delta.days > 0:
                            login_str = f"{delta.days} days"
                        elif delta.seconds > 3600:
                            login_str = f"{delta.seconds // 3600} hrs"
                        elif delta.seconds > 60:
                            login_str = f"{delta.seconds // 60} mins"
                        else:
                            login_str = f"{delta.seconds} secs"
                    except:
                        login_str = "Unknown"
                else:
                    login_str = "Never"
                
                # Get area name from last room vnum
                area = "Unknown"
                room_vnum = info.get('room', 3001)
                if room_vnum and self.world:
                    try:
                        from world import zone_of
                        zone_vnum = zone_of(self.world.rooms.get(room_vnum)) or room_vnum // 100
                        if zone_vnum in self.world.zones:
                            area = self.world.zones[zone_vnum].name[:14]
                    except:
                        pass
                
                # Race/class abbreviations
                race_abbr = info.get('race', 'Hum')[:3].lower()
                class_abbr = info.get('char_class', 'war')[:3].lower()
                
                # Last host (truncate if too long)
                last_host = info.get('last_host', 'Unknown')
                if len(last_host) > 20:
                    last_host = last_host[:17] + '...'
                
                char_list.append({
                    'name': info['name'],
                    'race': race_abbr,
                    'class': class_abbr,
                    'level': info['level'],
                    'last_login': login_str,
                    'area': area,
                    'host': last_host
                })
            else:
                char_list.append({
                    'name': char_name,
                    'race': '???',
                    'class': '???',
                    'level': 0,
                    'last_login': 'Unknown',
                    'area': 'Unknown',
                    'host': 'Unknown'
                })
        
        # Sort if requested
        if sort_by == 'level':
            char_list.sort(key=lambda x: x['level'], reverse=True)
        elif sort_by == 'name':
            char_list.sort(key=lambda x: x['name'])
        elif sort_by == 'login':
            pass  # Keep original order for now
        
        for info in char_list:
            await self.send(f"{c['bright_green']}{info['name']:<12} {c['white']}{info['race']:<4} {info['class']:<4} {info['level']:<4} {info['last_login']:<16} {info['area']:<15} {c['bright_black']}{info['host']}{c['reset']}")
    
    async def show_character_info(self, char_name: str):
        """Display detailed info about a character."""
        c = self.config.COLORS
        from player import Player
        
        char_name = char_name.capitalize()
        if char_name not in self.account.characters:
            await self.send(f"Character '{char_name}' not found in your account.")
            return
        
        info = Player.get_info(char_name)
        if not info:
            await self.send(f"Error loading character '{char_name}'.")
            return
        
        await self.send(f"\r\n{c['bright_cyan']}═══════════ Character Info: {info['name']} ═══════════{c['reset']}")
        await self.send(f"  {c['white']}Name:{c['reset']}    {info['name']}")
        await self.send(f"  {c['white']}Race:{c['reset']}    {info['race']}")
        await self.send(f"  {c['white']}Class:{c['reset']}   {info['char_class']}")
        await self.send(f"  {c['white']}Level:{c['reset']}   {info['level']}")
        await self.send(f"  {c['white']}HP:{c['reset']}      {info['hp']}/{info['max_hp']}")
        await self.send(f"  {c['white']}Mana:{c['reset']}    {info['mana']}/{info['max_mana']}")
        await self.send(f"  {c['white']}Gold:{c['reset']}    {info['gold']:,}")
        await self.send(f"  {c['white']}Exp:{c['reset']}     {info['exp']:,}")
        
        # Stats
        stats = info.get('stats', {})
        if stats:
            await self.send(f"\r\n  {c['yellow']}Stats:{c['reset']}")
            await self.send(f"    STR: {stats.get('str', 10)}  INT: {stats.get('int', 10)}  WIS: {stats.get('wis', 10)}")
            await self.send(f"    DEX: {stats.get('dex', 10)}  CON: {stats.get('con', 10)}  CHA: {stats.get('cha', 10)}")
        
        # Combat stats
        await self.send(f"\r\n  {c['yellow']}Combat:{c['reset']}")
        await self.send(f"    Kills: {info.get('kills', 0):,}  Deaths: {info.get('deaths', 0):,}")
        await self.send(f"    Hitroll: {info.get('hitroll', 0)}  Damroll: {info.get('damroll', 0)}")
        
        # Last login info
        await self.send(f"\r\n  {c['yellow']}Login:{c['reset']}")
        await self.send(f"    Last Login: {info.get('last_login', 'Never')[:19] if info.get('last_login') else 'Never'}")
        await self.send(f"    Last Host:  {info.get('last_host', 'Unknown')}")
        
        await self.send(f"{c['bright_cyan']}{'═' * 45}{c['reset']}")
    
    async def show_character_practice(self, char_name: str):
        """Display skills practiced for a character."""
        c = self.config.COLORS
        from player import Player
        
        char_name = char_name.capitalize()
        if char_name not in self.account.characters:
            await self.send(f"Character '{char_name}' not found in your account.")
            return
        
        info = Player.get_info(char_name)
        if not info:
            await self.send(f"Error loading character '{char_name}'.")
            return
        
        skills = info.get('skills', {})
        spells = info.get('spells', {})
        
        await self.send(f"\r\n{c['bright_cyan']}═══════════ Skills for {info['name']} ═══════════{c['reset']}")
        
        if skills:
            await self.send(f"\r\n{c['yellow']}Skills:{c['reset']}")
            for skill, level in sorted(skills.items()):
                bar = '█' * (level // 10) + '░' * (10 - level // 10)
                await self.send(f"  {skill:<20} [{bar}] {level}%")
        
        if spells:
            await self.send(f"\r\n{c['yellow']}Spells:{c['reset']}")
            for spell, level in sorted(spells.items()):
                bar = '█' * (level // 10) + '░' * (10 - level // 10)
                await self.send(f"  {spell:<20} [{bar}] {level}%")
        
        if not skills and not spells:
            await self.send(f"  {c['bright_black']}No skills or spells learned yet.{c['reset']}")
        
        await self.send(f"\r\n{c['bright_cyan']}{'═' * 40}{c['reset']}")
    
    async def show_connection_link(self):
        """Display connection information."""
        c = self.config.COLORS
        from datetime import datetime
        
        addr = self.address[0] if self.address else 'Unknown'
        port = self.address[1] if self.address and len(self.address) > 1 else 'Unknown'
        
        connected_duration = datetime.now() - self.connected_at
        hours = connected_duration.seconds // 3600
        mins = (connected_duration.seconds % 3600) // 60
        secs = connected_duration.seconds % 60
        
        await self.send(f"\r\n{c['bright_cyan']}═══════════ Connection Info ═══════════{c['reset']}")
        await self.send(f"  {c['white']}Your IP:{c['reset']}     {addr}")
        await self.send(f"  {c['white']}Your Port:{c['reset']}   {port}")
        await self.send(f"  {c['white']}Connected:{c['reset']}   {hours}h {mins}m {secs}s")
        await self.send(f"  {c['white']}Server:{c['reset']}      Misthollow v1.0")
        await self.send(f"{c['bright_cyan']}{'═' * 40}{c['reset']}")
    
    async def show_lag(self):
        """Display network lag (simple echo test)."""
        c = self.config.COLORS
        import time
        start = time.time()
        await self.send(".")  # Send a byte
        elapsed = (time.time() - start) * 1000
        await self.send(f"\r\n{c['white']}Network latency: {c['bright_green']}{elapsed:.1f}ms{c['reset']}")
    
    async def change_password(self):
        """Start password change flow."""
        c = self.config.COLORS
        await self.send(f"\r\n{c['yellow']}Enter new password: {c['reset']}", newline=False)
        self.state = self.STATE_CHANGE_PASSWORD
    
    async def handle_select_char(self, line: str):
        """Handle character selection commands."""
        if not line:
            await self.send("Account> ", newline=False)
            return
        
        parts = line.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd == 'play' or cmd == 'p':
            if not args:
                await self.send("Play which character? ")
                return
            char_name = args[0].capitalize()
            if char_name not in self.account.characters:
                # Try by number
                try:
                    idx = int(args[0]) - 1
                    if 0 <= idx < len(self.account.characters):
                        char_name = self.account.characters[idx]
                    else:
                        await self.send("Character not found. Try: play <name>")
                        return
                except ValueError:
                    await self.send("Character not found. Try: play <name>")
                    return
            
            # Load and enter game
            from player import Player
            self.player = Player.load(char_name, self.world)
            if self.player:
                self.player.account_name = self.account.account_name
                await self.enter_game()
            else:
                await self.send("Error loading character!")
                await self.show_character_menu()
        
        elif cmd == 'create' or cmd == 'c':
            if len(self.account.characters) >= self.account.settings.get('max_chars', 8):
                await self.send("You have reached the maximum number of characters!")
                await self.show_character_menu()
                return
            await self.send("Enter name for new character (or nothing, to go back): ")
            self.state = self.STATE_CREATE_CHAR_NAME
        
        elif cmd == 'delete' or cmd == 'd':
            if not args:
                await self.send("Delete which character? ")
                return
            char_name = args[0].capitalize()
            if char_name not in self.account.characters:
                await self.send("Character not found.")
                return
            if char_name.lower() in self.world.players:
                await self.send(f"{char_name} is in the world right now: quit them first.")
                return
            c = self.config.COLORS
            self.temp_delete_char = char_name
            await self.send(f"\r\n{c['bright_red']}WARNING: This will PERMANENTLY delete {char_name}!{c['reset']}")
            await self.send(f"{c['yellow']}To confirm, type the character name in ALL CAPS: {c['reset']}", newline=False)
            self.state = self.STATE_CONFIRM_DELETE
        
        elif cmd == 'claim':
            if not args:
                await self.send("Usage: claim <name> (a character on another account of yours: you are asked for that account's password)")
                return
            self.temp_claim_char = args[0].capitalize()
            await self.send(f"Password of the account {self.temp_claim_char} is on now: ", newline=False)
            self.state = self.STATE_CLAIM_PASSWORD
        
        elif cmd == 'list' or cmd == 'l':
            sort_by = args[0] if args else None
            await self.show_character_list(sort_by)
        
        elif cmd == 'move' or cmd == 'm':
            if len(args) < 2:
                await self.send("Usage: move <name> <up|down> [n]")
                return
            char_name = args[0].capitalize()
            direction = args[1].lower()
            amount = int(args[2]) if len(args) > 2 else 1
            
            if char_name not in self.account.characters:
                await self.send("Character not found.")
                return
            
            idx = self.account.characters.index(char_name)
            if direction == 'up':
                new_idx = max(0, idx - amount)
            elif direction == 'down':
                new_idx = min(len(self.account.characters) - 1, idx + amount)
            else:
                await self.send("Use 'up' or 'down'.")
                return
            
            self.account.characters.remove(char_name)
            self.account.characters.insert(new_idx, char_name)
            self.account.save()
            await self.send(f"Moved {char_name} to position {new_idx + 1}.")

        elif cmd == 'email':
            # (when the server can send mail, a new email proves itself with a code: `verify`)
            from accounts import AccountManager, email_problem, verification_on
            if not args:
                await self.send(f"Email: {self.account.settings.get('email') or 'none'}. Usage: email <address>")
                return
            why = email_problem(args[0], self.account)
            if why:
                ok, note = False, why
            elif verification_on():
                why = await self._mail_code(args[0], 'email')
                if why:
                    ok, note = False, why
                else:
                    self.temp_email = args[0].strip().lower()
                    ok, note = True, f"A code has been sent to {self.temp_email}. Type: verify <code>"
            else:
                ok = AccountManager.set_email(self.account, args[0])
                note = (f"Email set to {self.account.settings['email']}: sign in by it from now on." if ok
                        else email_problem(args[0], self.account))
            await self.send(note)
            await self.show_character_menu(note, bad=not ok)

        elif cmd == 'verify':
            # the code mailed for the menu's new email
            import security
            from accounts import AccountManager, email_problem
            if self.code_for != 'email' or not self.temp_email:
                await self.show_character_menu("No email is waiting for a code: email <address> first.", bad=True)
                return
            result = security.check_code(self.code, args[0] if args else '')
            if result == 'ok':
                email, self.temp_email, self.code, self.code_for = self.temp_email, '', None, ''
                ok = AccountManager.set_email(self.account, email)
                note = (f"Email set to {email}: sign in by it from now on." if ok else email_problem(email, self.account))
            elif result == 'wrong':
                ok, note = False, "That code isn't right. Type: verify <code>"
            else:
                self.temp_email, self.code, self.code_for = '', None, ''
                ok, note = False, ("That code has expired." if result == 'expired' else "Too many wrong codes.") + " Ask for a new one: email <address>"
            await self.send(note)
            await self.show_character_menu(note, bad=not ok)

        elif cmd == 'password' or cmd == 'passwd':
            self.temp_new_password = None
            await self.send("Enter new password: ", newline=False)
            self.state = self.STATE_CHANGE_PASSWORD
        
        elif cmd == 'info' or cmd == 'i':
            if not args:
                await self.send("Info for which character? ")
                return
            await self.show_character_info(args[0])
        
        elif cmd == 'practice' or cmd == 'prac':
            if not args:
                await self.send("Practice info for which character? ")
                return
            await self.show_character_practice(args[0])
        
        elif cmd == 'link':
            await self.show_connection_link()
        
        elif cmd == 'lag':
            await self.show_lag()
        
        elif cmd == 'time':
            from datetime import datetime
            c = self.config.COLORS
            now = datetime.now()
            await self.send(f"\r\n{c['white']}Game time: {c['bright_cyan']}{now.strftime('%A, %B %d, %Y at %I:%M %p')}{c['reset']}")
        
        elif cmd == 'menu':
            await self.show_character_menu()
        
        elif cmd == 'help' or cmd == '?':
            await self.show_account_help()
        
        elif cmd == 'quit' or cmd == 'q':
            await self.send("Farewell! Disconnecting...")
            self.writer.close()
            return
        
        elif cmd.isdigit():
            # Quick select by number
            idx = int(cmd) - 1
            if 0 <= idx < len(self.account.characters):
                char_name = self.account.characters[idx]
                from player import Player
                self.player = Player.load(char_name, self.world)
                if self.player:
                    self.player.account_name = self.account.account_name
                    await self.enter_game()
                else:
                    await self.send("Error loading character!")
                    await self.show_character_menu()
            else:
                await self.send("Invalid selection.")
        else:
            await self.send("Unknown command. Type 'help' for available commands.")
    
    async def handle_change_password(self, password: str):
        """Handle new password entry."""
        import security
        why = security.weak(password)
        if why:
            await self.send(f"{why} Try again: ", newline=False)
            return
        self.temp_new_password = password
        await self.send("Confirm new password: ", newline=False)
        self.state = self.STATE_CONFIRM_NEW_PASSWORD
    
    async def handle_confirm_password(self, password: str):
        """Handle password confirmation."""
        if password != self.temp_new_password:
            await self.send("Passwords don't match. Password not changed.")
            self.temp_new_password = None
            self.state = self.STATE_SELECT_CHAR
            await self.show_character_menu()
            return
        
        await self.account.set_password(password)
        self.account.save()
        await self.send("Password changed successfully! Web browsers signed in to this account will ask for it again.")
        self.temp_new_password = None
        self.state = self.STATE_SELECT_CHAR
        await self.show_character_menu()
    
    async def handle_confirm_delete(self, confirmation: str):
        """Handle character deletion confirmation."""
        c = self.config.COLORS
        char_name = getattr(self, 'temp_delete_char', None)
        
        if not char_name:
            await self.send("Error: No character selected for deletion.")
            self.state = self.STATE_SELECT_CHAR
            await self.show_character_menu()
            return
        
        # Must type name in ALL CAPS
        if confirmation != char_name.upper():
            await self.send(f"{c['yellow']}Deletion cancelled. You must type {char_name.upper()} to confirm.{c['reset']}")
            self.temp_delete_char = None
            self.state = self.STATE_SELECT_CHAR
            await self.show_character_menu()
            return
        
        # Confirmed - delete the character
        from accounts import AccountManager
        if AccountManager.delete_character(self.account, char_name):
            await self.send(f"{c['bright_red']}Character '{char_name}' has been permanently deleted.{c['reset']}")
        else:
            await self.send(f"{c['red']}Error deleting character.{c['reset']}")
        
        self.temp_delete_char = None
        self.state = self.STATE_SELECT_CHAR
        await self.show_character_menu()
    
    async def handle_create_char_name(self, name: str):
        """Handle new character name for account (nothing typed: back to the menu)."""
        if not name:
            await self.show_character_menu()
            return
        
        from accounts import name_problem, name_taken
        why = name_problem(name)
        if why:
            await self.send(why)
            await self.send("Enter name for new character (or nothing, to go back): ")
            return
        
        name = name.capitalize()
        
        # Check if name is taken (a character's, another account's, or one being made)
        if name_taken(name, self.account) or not self._hold_name(name):
            await self.send("That name is already taken. Choose another: ")
            return
        
        self.temp_name = name
        await self.show_race_menu()
        self.state = self.STATE_GET_RACE
    
    async def handle_claim_password(self, password: str):
        """`claim <name>` from the account menu: the password of the account the character is
        on now moves it to this one (accounts.AccountManager.claim)."""
        import security
        from accounts import AccountManager
        name, self.temp_claim_char = getattr(self, 'temp_claim_char', None), None
        self.state = self.STATE_SELECT_CHAR
        if not name or not password:
            await self.send("Nothing claimed.")
            return
        # wrong passwords count against the account being tried, as at the login prompt
        source, _ = AccountManager.account_for(name)
        key = source.account_name if source else name.lower()
        wait = security.locked(key)
        if wait:
            await self.send(f"Too many wrong passwords for {name}. Try again in {max(1, (wait + 59) // 60)} minutes.")
            return
        ok, why = await AccountManager.claim(self.account, name, password, online=set(self.world.players))
        if ok:
            security.succeeded(key)
            await self.send(f"{name} is now on this account.")
            await self.show_character_menu()
            return
        if why == "Wrong password.":
            await self._wrong_password(key, f"Wrong password for {name}'s account.")
            return
        await self.send(why)
        
    async def handle_command(self, line: str):
        """Handle a game command."""
        if not line:
            # Allow help pagination to continue on empty input
            if getattr(self.player, 'help_pagination', None):
                from commands import CommandHandler
                await CommandHandler.continue_help_pagination(self.player)
            await self.send_prompt()
            return

        # Echo command back to player so they see what they typed (not the 3D client's
        # internal moves: those are its walking, not something the player typed). A line
        # carrying a password or a sign-in token is neither echoed (snoop sees the echo)
        # nor kept for '!'.
        c = self.config.COLORS
        # the web clients' sign-in tokens (security.py): their own quiet requests
        first = line.split(None, 1)[0].lower() if line.split() else ''
        if first in ('remember', 'forget'):
            await self._device_token(first, line.split()[1:])
            return
        # (named in full: 'web' alone is a spell)
        web_internal = line.startswith(('webmove ', 'webdoor ', 'webbar ', 'webattack', 'webpull ', 'webping ', 'webtrack ', 'uiseen '))
        secret = self._secret_line(line)
        # (a web page shows what was typed itself, as it was typed: /play's log, the web
        # client's echo setting; the server's echo there was each command twice, and the ones
        # its windows send for you besides)
        if secret:
            web_internal = True
            if not self.is_web:
                await self.send(f"{c['cyan']}> {secret}{c['reset']}\r\n")
        if not web_internal and not self.is_web:
            await self.send(f"{c['cyan']}> {line}{c['reset']}\r\n")

        # Handle ! to repeat last command
        if line.strip() == '!':
            if self.player.last_command:
                line = self.player.last_command
                await self.send(f"Repeating: {line}\r\n")
            else:
                await self.send("No previous command to repeat.\r\n")
                await self.send_prompt()
                return

        # Store command for ! repeat (not the 3D client's own walking and door work)
        if not web_internal:
            self.player.last_command = line

        # Parse command and arguments
        parts = line.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        # Check for alias substitution
        if cmd in self.player.custom_aliases:
            aliased_command = self.player.custom_aliases[cmd]
            # Reconstruct line with alias expanded + original args
            expanded_line = aliased_command
            if args:
                expanded_line += ' ' + ' '.join(args)
            # Re-parse with alias expanded
            parts = expanded_line.split()
            cmd = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

        # Execute command
        await self.player.execute_command(cmd, args)
        
        # Occasional tip for newer players after commands
        try:
            if self.player.level < 15:
                from tips import TipManager
                await TipManager.maybe_show_tip(self.player, chance=0.03)
        except Exception:
            pass

        # Track command for tutorial progress
        try:
            from quests import QuestManager
            await QuestManager.check_tutorial_progress(self.player, cmd)
            # Check for auto-completion of tutorial quests
            for quest in list(getattr(self.player, 'active_quests', [])):
                if quest.quest_id.startswith('tutorial_') and quest.is_complete():
                    await QuestManager.auto_complete_tutorial_quest(self.player, quest)
            
            # Periodic auto-hint for tutorial quests (5 min no progress)
            await QuestManager.check_auto_hint(self.player)
            
            # Compass sense hint after movement/look
            if cmd in ('look', 'north', 'south', 'east', 'west', 'up', 'down', 'n', 's', 'e', 'w', 'u', 'd'):
                await QuestManager.show_compass_hint(self.player)
        except Exception:
            pass
        
        await self.send_prompt()
        
    @staticmethod
    def _secret_line(line: str) -> str:
        """What to show instead of a line that carries a password or a token ('' if it
        carries none)."""
        words = line.split()
        if not words:
            return ''
        first = words[0].lower()
        if first == 'account' and len(words) > 1 and words[1].lower() in ('password', 'recover', 'reset', 'claim'):
            return f"account {words[1].lower()} ****"
        return ''

    async def _device_token(self, verb: str, args):
        """`remember`: a sign-in token for this browser, sent over the hidden RESUME
        signal (only web clients ask). `forget <token>`: that browser signs out."""
        import security
        if not self.player:
            return
        if verb == 'remember':
            token = security.issue_token(self.player.name)
            await self._send_raw(security.resume_signal(token))
        elif args:
            security.forget_token(self.player.name, args[0])

    async def _issue_web_token(self):
        """A fresh secret for this session's graphical clients. The map socket and the map
        server's per-player endpoints answer only to it; it rides the MAPSYNC signal, which
        only this connection receives. Clients holding an older one are cut off."""
        import secrets
        token = secrets.token_urlsafe(18)
        self.player.web_token = token
        wm = getattr(self.world, 'web_map', None)
        if wm and hasattr(wm, 'revoke'):
            try:
                await wm.revoke(self.player.name, token)
            except Exception:
                pass
        await self.send(f"\x1b]MAPSYNC:{self.player.name}:{token}\x07")

    async def _take_over(self, existing):
        """Attach this connection to a character already in the world, closing the old one."""
        c = self.config.COLORS
        old = getattr(existing, 'connection', None)
        if old is not None and old is not self:
            try:
                await old.send(f"\r\n{c['bright_yellow']}{existing.name} has just logged in somewhere else, "
                               f"so this session is closing.{c['reset']}\r\n")
            except Exception:
                pass
            old.player = None              # its disconnect must not save or remove the character
            try:
                old.writer.close()
            except Exception:
                pass
        self.player = existing
        existing.connection = self
        self.state = self.STATE_PLAYING
        logger.info(f"{existing.name} taken over by a new connection from {self.address}")
        await self.send(f"{c['bright_cyan']}You take over {existing.name}, who was already in the world.{c['reset']}")
        await existing.do_look([])
        await self._issue_web_token()

    async def disconnect(self):
        """Handle disconnection gracefully — stop combat, save state, clean up."""
        if getattr(self, '_disconnected', False):
            return                         # quit already did this; the input loop's finally comes again
        self._disconnected = True
        self._let_name_go()
        logger.info(f"Connection closed: {self.address}")
        
        if self.player:
            try:
                # Stop combat immediately
                if self.player.fighting:
                    # Clear the opponent's target if they were fighting this player
                    opponent = self.player.fighting
                    if opponent and getattr(opponent, 'fighting', None) == self.player:
                        opponent.fighting = None
                        if opponent.position == 'fighting':
                            opponent.position = 'standing'
                    self.player.fighting = None
                    if self.player.position == 'fighting':
                        self.player.position = 'standing'

                # Update logout timestamp + playtime
                now = datetime.now()
                if hasattr(self.player, 'last_login'):
                    self.player.total_playtime += max(0, int((now - self.player.last_login).total_seconds()))
                self.player.last_logout = now
            except Exception as e:
                logger.error(f"Error updating player state on disconnect: {e}")

            # Leave the group (no ghost members sharing gold, loot and experience)
            try:
                from groups import GroupManager
                await GroupManager.disconnect(self.player)
            except Exception as e:
                logger.error(f"Error leaving the group on disconnect: {e}")

            # Save player state
            try:
                await self.player.save()
            except Exception as e:
                logger.error(f"Error saving player {self.player.name} on disconnect: {e}")

            # Remove from world
            try:
                await self.world.remove_player(self.player)
            except Exception as e:
                logger.error(f"Error removing player {self.player.name} from world: {e}")
            
            # Announce departure
            try:
                if self.player.room:
                    await self.player.room.send_to_room(
                        f"{self.player.name} has left the realm.",
                        exclude=[self.player]
                    )
            except Exception:
                pass

            # Clear connection reference
            self.player.connection = None
        
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass


class MUDServer:
    """Main MUD server class."""
    
    def __init__(self, world, config: Config):
        self.world = world
        self.config = config
        self.connections: Dict[str, Connection] = {}
        self.server = None
        
    async def start(self):
        """Start the server."""
        # every character on an account before anyone logs in (accounts.py; once all are,
        # this changes nothing)
        try:
            from accounts import migrate_saves
            migrate_saves()
        except Exception:
            logger.exception('accounts migration')
        self.server = await asyncio.start_server(
            self.handle_connection,
            self.config.HOST,
            self.config.PORT,
            reuse_address=True
        )
        
        addr = self.server.sockets[0].getsockname()
        logger.info(f"Server listening on {addr[0]}:{addr[1]}")
        
        asyncio.create_task(self.server.serve_forever())
        
    # --- IP Ban List ---
    BANNED_IPS = {
        # Scanners / bots
        '204.76.203.210', '193.111.248.141', '157.245.224.87',
        '157.230.157.100', '18.116.101.220', '3.129.187.38',
        '89.42.231.182', '204.76.203.215', '3.130.168.2',
        '167.94.138.171', '16.58.56.214', '206.168.34.58',
        # China
        '106.117.108.141', '110.177.176.239', '110.177.181.3',
        '111.162.156.51', '111.162.158.127', '112.122.236.114',
        '113.57.185.86', '119.164.101.49', '119.48.135.48',
        '121.29.84.65', '122.96.28.137', '123.160.223.73',
        '123.160.223.74', '123.191.141.46', '123.191.159.14',
        '123.245.85.154', '124.117.192.143', '124.117.192.29',
        '124.117.193.197', '14.135.75.17', '171.12.10.208',
        '171.12.10.76', '171.37.93.108', '220.167.232.177',
        '220.167.233.72', '220.197.78.186', '221.199.14.242',
        '221.199.73.249', '221.207.34.83', '222.176.200.45',
        '222.176.201.50', '222.176.201.94', '222.186.13.130',
        '223.166.22.174', '223.166.22.191', '223.166.22.35',
        '27.47.27.109', '59.173.109.209', '60.13.7.147',
        '60.16.200.153',
        # Scanners (added Mar 15)
        '85.217.149.48',
    }

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a new connection."""
        conn = Connection(reader, writer, self)
        conn_id = f"{conn.address[0]}:{conn.address[1]}" if conn.address else f"unknown-{id(conn)}"

        # Block banned IPs immediately
        client_ip = conn.address[0] if conn.address else None
        if client_ip and client_ip in self.BANNED_IPS:
            logger.info(f"Blocked banned IP: {client_ip}")
            try:
                writer.close()
            except Exception:
                pass
            return

        self.connections[conn_id] = conn
        
        try:
            # Send welcome screen
            await self.send_welcome(conn)
            
            # Read input loop
            while True:
                try:
                    data = await asyncio.wait_for(reader.readline(), timeout=1800.0)
                    if not data:
                        break
                    mark = WEB_MARK_RE.fullmatch(data.strip())
                    if mark:
                        conn.is_web = True
                        # the browser's own address, from the bridge on this machine only (a
                        # telnet player can't claim one)
                        if mark.group(1) and conn.address and ipaddress.ip_address(conn.address[0]).is_loopback:
                            conn.client_ip = mark.group(1).decode('ascii')
                        continue
                    line = _CONTROL_CHARS.sub('', data.decode('utf-8', errors='ignore')).strip()
                    await conn.handle_input(line)
                except asyncio.TimeoutError:
                    # Force-rent at 2x cost on idle timeout
                    if conn.player:
                        try:
                            from commands import CommandHandler
                            rent_cost = CommandHandler.calc_total_rent(conn.player) * 2
                            if conn.player.gold >= rent_cost:
                                conn.player.gold -= rent_cost
                                conn.player.rent_paid = True
                                await conn.send(f"\r\nIdle timeout! You've been force-rented for {rent_cost} gold (2x normal rate).\r\n")
                            else:
                                await conn.send(f"\r\nIdle timeout! You couldn't afford rent ({rent_cost} gold). Some items may be lost!\r\n")
                        except Exception:
                            pass
                    else:
                        await conn.send("\r\nConnection timed out. Goodbye!\r\n")
                    break
                except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError) as e:
                    addr = getattr(conn, 'address', 'unknown')
                    logger.info(f"Connection lost for {addr}: {e}")
                    break
                except Exception as e:
                    import traceback
                    logger.error(f"Error handling input: {e}")
                    logger.error(traceback.format_exc())
                    break
                    
        finally:
            await conn.disconnect()
            if conn_id in self.connections:
                del self.connections[conn_id]
                
    async def send_welcome(self, conn: Connection):
        """Send the welcome screen."""
        c = self.config.COLORS
        welcome = f"""
{c['bright_cyan']}
    ===================================================================

      ___  ________ _____ _____ _   _ _____ _      _     _____  _    _
     |  \\/  |_   _/  ___|_   _| | | |  _  | |    | |   |  _  || |  | |
     | .  . | | | \\ `--.  | | | |_| | | | | |    | |   | | | || |  | |
     | |\\/| | | |  `--. \\ | | |  _  | | | | |    | |   | | | || |/\\| |
     | |  | |_| |_/\\__/ / | | | | | \\ \\_/ / |____| |___\\ \\_/ /\\  /\\  /
     \\_|  |_/\\___/\\____/  \\_/ \\_| |_/\\___/\\_____/\\_____/\\___/  \\/  \\/

    ===================================================================

    {c['white']}Welcome, brave adventurer, to a world of fantasy and magic!
    Explore vast dungeons, battle fearsome creatures, and
    forge your legend in Misthollow!

    {c['bright_green']}* 8 unique races with special abilities
    * 8 character classes to master
    * Hundreds of zones to explore
    * Epic quests and legendary items

{c['bright_cyan']}    ===================================================================
{c['reset']}

{c['white']}What name shall you be known by?{c['reset']} """

        await conn.send(welcome, newline=False)
        
    async def process_input(self):
        """Process input from all connections (called each tick)."""
        # Input is handled asynchronously per connection
        pass
        
    async def shutdown(self):
        """Shut down the server."""
        logger.info("Shutting down server...")
        
        # Disconnect all clients
        for conn in list(self.connections.values()):
            await conn.send("\r\n\r\nServer shutting down. Goodbye!\r\n")
            await conn.disconnect()
            
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
    async def broadcast(self, message: str, exclude=None):
        """Broadcast a message to all players."""
        for conn in self.connections.values():
            if conn.player and (exclude is None or conn.player not in exclude):
                await conn.send(f"\r\n{message}\r\n")
