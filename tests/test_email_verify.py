"""Email codes against bot sign-ups: when the server can send mail, a new account (from /play's
Create account or the telnet sign-up) and a new email on an account prove the email with a
6-digit code before anything is saved; codes are limited per email and per network address; the
web bridge passes the browser's own address on. Without mail settings nothing changes.

Offline (temporary player and account folders, fake connections, a fake mailer):
    python3 tests/test_email_verify.py
"""
import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import test_webmove as tw  # noqa: E402  (check(), failures)
from test_accounts import connection, say, save_of  # noqa: E402
from config import Config  # noqa: E402
import accounts  # noqa: E402
from accounts import Account  # noqa: E402
import security  # noqa: E402

check, failures = tw.check, tw.failures
MAIL = {'host': 'smtp.example.com', 'port': 587, 'user': 'u', 'password': 'p', 'from': 'game@example.com', 'tls': True}
sent = []                            # (to, code) the fake mailer was asked to send
mail_works = [True]


def fake_send_code(to, code):
    sent.append((to, code))
    return mail_works[0]


def last_code(to):
    return [c for t, c in sent if t == to][-1]


def fresh(tmp, sub):
    base = os.path.join(tmp, sub)
    Config.PLAYER_DIR = os.path.join(base, 'players')
    accounts.ACCOUNTS_DIR = os.path.join(base, 'accounts')
    os.makedirs(Config.PLAYER_DIR)
    os.makedirs(accounts.ACCOUNTS_DIR)
    security._code_sends.clear()
    sent.clear()
    mail_works[0] = True


async def offline(tmp):
    real_settings, real_send = accounts.mail_settings, accounts.send_code
    accounts.MAIL_FILE = os.path.join(tmp, 'mail.json')

    # ------------------------------------------------ the mail settings
    for k in ('HOST', 'PORT', 'USER', 'PASSWORD', 'FROM', 'TLS'):
        os.environ.pop(f'MISTHOLLOW_SMTP_{k}', None)
    check(accounts.mail_settings() == {} and not accounts.verification_on(), 'no mail settings: no email codes')
    with open(accounts.MAIL_FILE, 'w') as f:
        json.dump({'host': 'smtp.x.com', 'port': '2525', 'from': 'g@x.com', 'tls': 'false'}, f)
    s = accounts.mail_settings()
    check(s['host'] == 'smtp.x.com' and s['port'] == 2525 and s['tls'] is False and accounts.verification_on(),
          'lib/mail.json turns them on')
    os.environ['MISTHOLLOW_SMTP_HOST'] = 'smtp.env.com'
    os.environ['MISTHOLLOW_SMTP_FROM'] = 'e@x.com'
    check(accounts.mail_settings()['host'] == 'smtp.env.com', '…and MISTHOLLOW_SMTP_* in the environment come first')
    for k in ('HOST', 'FROM'):
        os.environ.pop(f'MISTHOLLOW_SMTP_{k}')
    os.remove(accounts.MAIL_FILE)

    # without mail: newaccount needs no email and no code (as before)
    fresh(tmp, 'nomail')
    conn, w = connection()
    await say(conn, w, 'newaccount Plain', 'plainpass1', 'plainpass1')
    check(Account.exists('plain') and conn.state == conn.STATE_SELECT_CHAR, 'without mail, newaccount makes the account at once')

    accounts.mail_settings = lambda: dict(MAIL)
    accounts.send_code = fake_send_code
    try:
        # ------------------------------------------------ newaccount (/play's Create account)
        fresh(tmp, 'newaccount')
        conn, w = connection()
        conn.is_web = True
        out = await say(conn, w, 'newaccount Ana')
        check('An email is needed' in out and conn.state == conn.STATE_GET_NAME, 'with mail, newaccount needs an email')
        out = await say(conn, w, 'newaccount Ana ana@example.com', 'anapass123', 'anapass123')
        check(sent[-1][0] == 'ana@example.com' and re.fullmatch(r'\d{6}', sent[-1][1]) and 'Enter the 6-digit code' in out
              and conn.state == conn.STATE_VERIFY_CODE, '…mails a 6-digit code to it and asks for it')
        check(not Account.exists('ana'), '…and nothing is saved before the code comes back')
        wrong = '000000' if last_code('ana@example.com') != '000000' else '111111'
        out = await say(conn, w, wrong)
        check("isn't right" in out and conn.state == conn.STATE_VERIFY_CODE and not Account.exists('ana'), 'a wrong code asks again')
        out = await say(conn, w, last_code('ana@example.com'))
        a = Account.load('ana')
        check(a is not None and a.settings['email'] == 'ana@example.com' and conn.state == conn.STATE_SELECT_CHAR
              and 'ACCOUNT:' in out, 'the right one makes the account, with its email, and opens its menu')

        # an expired code, and resend
        conn, w = connection()
        await say(conn, w, 'newaccount Cato cato@example.com', 'catopass12', 'catopass12')
        conn.code['until'] = 0
        out = await say(conn, w, last_code('cato@example.com'))
        check('expired' in out and conn.state == conn.STATE_VERIFY_CODE, 'an expired code is refused')
        out = await say(conn, w, 'resend')
        check(len([t for t, _c in sent if t == 'cato@example.com']) == 2 and 'Enter the 6-digit code' in out, "…'resend' mails a new one")
        await say(conn, w, last_code('cato@example.com'))
        check(Account.exists('cato'), '…which works')

        # five wrong codes, or nothing typed: nothing made
        conn, w = connection()
        await say(conn, w, 'newaccount Dree dree@example.com', 'dreepass12', 'dreepass12')
        good = last_code('dree@example.com')
        bad = '000000' if good != '000000' else '111111'
        for _ in range(security.CODE_TRIES):
            out = await say(conn, w, bad)
        check('Too many wrong codes' in out and conn.state == conn.STATE_GET_NAME and not Account.exists('dree'),
              'five wrong codes end the sign-up, making nothing')
        conn, w = connection()
        await say(conn, w, 'newaccount Dree dree2@example.com', 'dreepass12', 'dreepass12')
        out = await say(conn, w, '')
        check('Sign-up stopped' in out and conn.state == conn.STATE_GET_NAME and not Account.exists('dree'),
              'nothing typed at the code stops the sign-up')

        # mail that can't be sent
        mail_works[0] = False
        conn, w = connection()
        out = await say(conn, w, 'newaccount Esk esk@example.com', 'eskpass123', 'eskpass123')
        check("couldn't be sent" in out and conn.state == conn.STATE_GET_NAME and not Account.exists('esk'),
              'a code that cannot be mailed makes nothing and says so')
        mail_works[0] = True

        # ------------------------------------------------ the telnet sign-up
        fresh(tmp, 'signup')
        conn, w = connection()
        out = await say(conn, w, 'Bryn', 'y', 'brynpass12', 'brynpass12')
        check('Your email' in out and conn.state == conn.STATE_GET_EMAIL, 'the telnet sign-up asks for an email after the password')
        out = await say(conn, w, 'not-an-email')
        check("isn't an email" in out and conn.state == conn.STATE_GET_EMAIL, '…refusing one that is not')
        out = await say(conn, w, 'bryn@example.com')
        check(conn.state == conn.STATE_VERIFY_CODE and sent[-1][0] == 'bryn@example.com', '…and mails the code')
        out = await say(conn, w, last_code('bryn@example.com'))
        check('Choose Your Race' in out and not Account.exists('bryn'), "the right code goes on to the hero (nothing saved yet)")
        await say(conn, w, 'human', 'female', 'warrior', 'y')
        a = Account.load('bryn')
        check(a is not None and a.settings['email'] == 'bryn@example.com' and a.characters == ['Bryn']
              and save_of('Bryn')['account_name'] == 'bryn', '…and the finished hero makes the account, with its email')

        # ------------------------------------------------ limits
        fresh(tmp, 'limits')
        check(all(security.code_send_allowed('same@example.com', f'10.0.0.{i}') == '' for i in range(security.CODES_PER_EMAIL)),
              'three codes to one email in an hour are allowed')
        check('Too many codes' in security.code_send_allowed('same@example.com', '10.0.0.9'), 'a fourth code to one email in an hour is refused')
        for i in range(security.CODES_PER_ADDRESS):
            security.code_send_allowed(f'p{i}@example.com', '198.51.100.7')
        check('Too many codes' in security.code_send_allowed('p99@example.com', '198.51.100.7'),
              'a seventh code from one address in an hour is refused')
        check(security.code_send_allowed('p99@example.com', '198.51.100.8') == '', '…another address is not')
        conn, w = connection()
        conn.client_ip = '198.51.100.7'
        out = await say(conn, w, 'newaccount Fenn fenn@example.com', 'fennpass12', 'fennpass12')
        check('Too many codes' in out and not Account.exists('fenn') and conn.state == conn.STATE_GET_NAME,
              'a sign-up past the limit is turned away, making nothing')

        # ------------------------------------------------ a new email on an account (the menu)
        fresh(tmp, 'menu')
        await accounts.AccountManager.create_account('gale', 'galepass12')
        conn, w = connection()
        conn.is_web = True
        await say(conn, w, 'gale', 'galepass12')
        out = await say(conn, w, 'email gale@example.com')
        sig = json.loads(re.findall(r'\x1b\]ACCOUNT:(\{[^\x07]*\})\x07', out)[-1])
        check('A code has been sent to gale@example.com' in out and not Account.load('gale').settings.get('email')
              and sig['pending'] == 'gale@example.com', "the menu's email mails a code first; the page is told it waits")
        out = await say(conn, w, 'verify 12')
        check("isn't right" in out and not Account.load('gale').settings.get('email'), '…a wrong code sets nothing')
        out = await say(conn, w, f"verify {last_code('gale@example.com')}")
        sig = json.loads(re.findall(r'\x1b\]ACCOUNT:(\{[^\x07]*\})\x07', out)[-1])
        check(Account.load('gale').settings['email'] == 'gale@example.com' and sig['pending'] == '' and sig['email'] == 'gale@example.com',
              '…the right one sets it')
        out = await say(conn, w, 'verify 123456')
        check('No email is waiting' in out, '`verify` with nothing waiting says so')

        # ------------------------------------------------ the browser's address
        import server
        m = server.WEB_MARK_RE.fullmatch(b'\x1b]WEB:203.0.113.5\x07')
        check(m and m.group(1) == b'203.0.113.5' and server.WEB_MARK_RE.fullmatch(b'\x1b]WEB\x07'),
              'the web mark carries the browser address (or none)')
        check(server.WEB_MARK_RE.fullmatch(b'\x1b]WEB:1.2.3.4; rm\x07') is None, '…and nothing else')
        import web_client

        def req(remote, **headers):
            return types.SimpleNamespace(remote=remote, headers=headers)
        check(web_client.client_address(req('127.0.0.1', **{'X-Forwarded-For': '203.0.113.5, 10.0.0.1'})) == '203.0.113.5',
              "behind a proxy on this machine, the browser's address comes from its header")
        check(web_client.client_address(req('127.0.0.1', **{'CF-Connecting-IP': '198.51.100.2'})) == '198.51.100.2', '…or Cloudflare\'s')
        check(web_client.client_address(req('93.184.216.34', **{'X-Forwarded-For': '1.1.1.1'})) == '93.184.216.34',
              "…but a header from anywhere else is not believed")
        check(web_client.client_address(req('127.0.0.1', **{'X-Forwarded-For': 'junk'})) == '127.0.0.1', '…nor a header that is not an address')
    finally:
        accounts.mail_settings, accounts.send_code = real_settings, real_send


async def main():
    tmp = tempfile.mkdtemp(prefix='mh-verify-')
    saved = (accounts.ACCOUNTS_DIR, accounts.MAIL_FILE, Config.PLAYER_DIR, security.TOKENS_FILE)
    security.TOKENS_FILE = os.path.join(tmp, 'resume_tokens.json')
    security._store = None
    try:
        await offline(tmp)
    finally:
        accounts.ACCOUNTS_DIR, accounts.MAIL_FILE, Config.PLAYER_DIR, security.TOKENS_FILE = saved
        security._store = None
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
