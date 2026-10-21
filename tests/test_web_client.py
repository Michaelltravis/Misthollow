"""Live test: /play is the only web client, and a web connection's text is not hard-wrapped.

Needs a running server (./run.sh) and the gauntlet admin account (tools/gauntlet/README.md).
    python3 tests/test_web_client.py
Checks: the retired 2D clients' URLs (/platformer, /2d, /iso) redirect to /play; /play loads
its shared scripts from /v/<commit>/shared/ and nothing from the old 2D folder; a telnet
connection's long lines are wrapped at 80 columns, and a connection that announced itself
as the web bridge (server.WEB_MARK, as web_client.py does) gets them whole; /who (for the
signed-in session only) and /help answer the who and help windows; a fixture can't be taken;
/explored and the progression windows' endpoints answer the session.
"""
import asyncio
import http.client
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from server import WEB_MARK  # noqa: E402
from test_webmove import Telnet, check, failures, HOST, MAP, ANSI  # noqa: E402
import gauntlet_accounts  # noqa: E402  (the test characters, made if missing)


def get(path):
    """(status, headers, body) of a GET on the map server, redirects not followed."""
    c = http.client.HTTPConnection(HOST, MAP, timeout=10)
    c.request('GET', path)
    r = c.getresponse()
    body = r.read()
    c.close()
    return r.status, dict(r.getheaders()), body


def pages():
    for path in ('/platformer', '/platformer?gauntlet=1', '/platformer/net.js', '/2d', '/iso', '/isometric'):
        status, headers, _ = get(path)
        check(status == 302 and headers.get('Location') == '/play', f'{path} redirects to /play ({status} {headers.get("Location")})')
    status, _, body = get('/play')
    page = body.decode(errors='ignore')
    check(status == 200, '/play loads')
    check('/platformer' not in page, '/play loads nothing from the old 2D folder')
    shared = re.findall(r'src="(/v/[^/]+/shared/[a-z-]+\.js)"', page)
    check(len(shared) == 5, f'/play loads its five shared scripts from /v/<commit>/shared/ ({len(shared)})')
    for src in shared:
        status, headers, body = get(src)
        check(status == 200 and 'javascript' in headers.get('Content-Type', '') and len(body) > 1000,
              f'{src} is served ({status}, {headers.get("Content-Type")}, {len(body)} bytes)')
    status, _, _ = get('/shared/../server.py')
    check(status == 404, 'no way out of the shared folder')


LONG = 'the mist ' * 16     # 144 characters: past any 80-column wrap


async def said(web):
    """What `say <LONG>` echoes back, as lines, on a telnet or a web connection."""
    tn = Telnet()
    tn.r, tn.w = await asyncio.open_connection(HOST, 4000)
    tn.buf = ''
    if web:
        tn.w.write(WEB_MARK + b'\r\n')
        await tn.w.drain()
    await tn.read(1.5)
    for line in ('gauntlet', 'gauntlet1', 'play Gauntlet'):
        await tn.cmd(line, 1.2)
    text = await tn.cmd('say ' + LONG.strip(), 1.2)
    await tn.cmd('quit', 0.8)
    tn.w.close()
    return [ANSI.sub('', l) for l in text.replace('\r', '').split('\n')]


async def wrapping():
    lines = await said(web=False)
    hit = [l for l in lines if 'the mist the mist' in l]
    check(hit and all(len(l) <= 80 for l in lines), f'telnet: a long line is wrapped at 80 columns ({[len(l) for l in hit]})')
    lines = await said(web=True)
    hit = [l for l in lines if 'the mist' in l]      # the command's echo, and what you said
    check(any(l.startswith('You say') for l in hit) and all(LONG.strip() in l for l in hit),
          f'web: the same line arrives whole ({[len(l) for l in hit]})')


async def windows():
    """The data behind /play's who and help windows (Push 16)."""
    tn = Telnet()
    await tn.open()                 # signed in: the map server answers to this session's token
    import test_webmove as tw
    status, _, body = get(f'/who?player=Gauntlet&t={tw.TOKEN}')
    data = json.loads(body or b'{}') if status == 200 else {}
    me = [p for p in data.get('players', []) if p.get('name') == 'Gauntlet']
    check(status == 200 and me and me[0].get('level') and me[0].get('cls'), f'/who lists who is online, with level and class ({status}, {me[:1]})')
    status, _, _ = get('/who?player=Gauntlet&t=wrong')
    check(status == 404, f'/who answers only to the session ({status})')
    status, _, body = get('/help')
    topics = json.loads(body).get('topics', []) if status == 200 else []
    check(len(topics) > 300 and any(t['name'] == 'bash' for t in topics), f'/help lists the topics ({len(topics)})')
    status, _, body = get('/help?topic=bash')
    check(status == 200 and 'bash' in json.loads(body).get('text', '').lower(), '/help?topic= reads one')
    # a fixture is the room's: it can't be picked up, and /play doesn't draw it as loot
    await tn.cmd('goto 3001', 1.0)
    text = await tn.cmd('get fountain', 0.8)
    check('fixed in place' in text, f'a fountain stays where it is ({text.strip()[:60]!r})')
    status, _, body = get(f'/state?player=Gauntlet&mode=near&t={tw.TOKEN}')
    rooms = json.loads(body).get('nearby', []) if status == 200 else []
    items = [it for r in rooms if r.get('vnum') == 3001 for it in r.get('items', [])]
    # (the fountain itself must be there: a room emptied by an earlier `purge` proves nothing)
    check(any(it.get('name') == 'fountain' for it in items) and all(it.get('fixed') for it in items if it.get('name') in ('fountain', 'atm')),
          f'the payload marks fixtures ({[(it.get("name"), it.get("fixed")) for it in items]})')
    await tn.cmd('quit', 0.6)


async def progression():
    """The data behind /play's progression and travel windows (Push 17)."""
    tn = Telnet()
    await tn.open()
    import test_webmove as tw
    await tn.cmd('goto 3001', 1.0)
    status, _, body = get(f'/explored?player=Gauntlet&t={tw.TOKEN}')
    rooms = json.loads(body).get('rooms', []) if status == 200 else []
    check(status == 200 and 3001 in rooms, f'/explored lists the rooms explored, the one you stand in too ({status}, {len(rooms)} rooms)')
    status, _, _ = get('/explored?player=Gauntlet&t=wrong')
    check(status == 404, f'/explored answers only to the session ({status})')
    for path in ('talents', 'almanac', 'travel', 'stable', 'services', 'legend', 'doctrine'):
        status, _, body = get(f'/{path}?player=Gauntlet&t={tw.TOKEN}')
        try:
            data = json.loads(body) if status == 200 else None
        except ValueError:
            data = None
        check(isinstance(data, dict) and data, f'/{path} answers its window ({status}, {sorted(data)[:5] if isinstance(data, dict) else body[:60]})')
    await tn.cmd('quit', 0.6)


async def main():
    pages()
    await gauntlet_accounts.ensure()
    await wrapping()
    await windows()
    await progression()
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
