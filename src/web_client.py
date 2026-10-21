"""
Web Client for Misthollow
A browser-based terminal interface with WebSocket-to-telnet bridge.
Port 4003 by default.
"""

import asyncio
import codecs
import os
import json
import re
from aiohttp import web, WSMsgType
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ANSI color code to CSS class mapping
ANSI_COLORS = {
    '30': 'ansi-black',
    '31': 'ansi-red',
    '32': 'ansi-green',
    '33': 'ansi-yellow',
    '34': 'ansi-blue',
    '35': 'ansi-magenta',
    '36': 'ansi-cyan',
    '37': 'ansi-white',
    '90': 'ansi-bright-black',
    '91': 'ansi-bright-red',
    '92': 'ansi-bright-green',
    '93': 'ansi-bright-yellow',
    '94': 'ansi-bright-blue',
    '95': 'ansi-bright-magenta',
    '96': 'ansi-bright-cyan',
    '97': 'ansi-bright-white',
    '1': 'ansi-bold',
    '0': 'ansi-reset',
}


def ansi_to_html(text: str) -> str:
    """Convert ANSI escape codes to HTML spans."""
    # a terminal's other codes (clear the screen, move the cursor: `clear` sends "\x1b[2J\x1b[H")
    # mean nothing to a page: they go, rather than show as text
    text = re.sub(r'\x1b\[[0-9;?]*[A-La-ln-z]', '', text)
    # Pattern for ANSI escape sequences
    ansi_pattern = re.compile(r'\x1b\[([0-9;]*)m')
    
    result = []
    last_end = 0
    open_spans = 0
    
    for match in ansi_pattern.finditer(text):
        # Add text before this match
        result.append(html_escape(text[last_end:match.start()]))
        
        codes = match.group(1).split(';') if match.group(1) else ['0']
        
        for code in codes:
            if code == '0':
                # Reset - close all open spans
                result.append('</span>' * open_spans)
                open_spans = 0
            elif code in ANSI_COLORS:
                result.append(f'<span class="{ANSI_COLORS[code]}">')
                open_spans += 1
        
        last_end = match.end()
    
    # Add remaining text
    result.append(html_escape(text[last_end:]))
    # Close any remaining spans
    result.append('</span>' * open_spans)
    
    return ''.join(result)


def html_escape(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


KIND_PATTERN = re.compile(r'\x1b\]K:([a-z]+)\x07')
RESUME_PATTERN = re.compile(r'\x1b\]RESUME:([A-Za-z0-9_\-]+)\x07')
# the account menu's characters (server.show_character_menu), for the page's character screen
ACCOUNT_PATTERN = re.compile(r'\x1b\]ACCOUNT:(\{[^\x07]*\})\x07')
# a colour code not finished at the end of what was read ("\x1b", "\x1b[", "\x1b[1;3")
CSI_TAIL = re.compile(rb'\x1b(?:\[[0-9;]*)?$')


class TelnetBridge:
    """Bridge between WebSocket and telnet connection."""
    
    def __init__(self, ws: web.WebSocketResponse, mud_host: str = 'localhost', mud_port: int = 4000):
        self.ws = ws
        self.mud_host = mud_host
        self.mud_port = mud_port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
    
    async def connect(self) -> bool:
        """Connect to the MUD server."""
        try:
            self.reader, self.writer = await asyncio.open_connection(self.mud_host, self.mud_port)
            # announce a web connection (server.WEB_MARK): the page wraps its own text
            self.writer.write(b'\x1b]WEB\x07\r\n')
            await self.writer.drain()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MUD: {e}")
            return False
    
    async def read_loop(self):
        """Read from MUD and send to WebSocket."""
        carry = b''
        # (a character cut in two by the read is put together: the boxes' ═║ are three bytes)
        utf8 = codecs.getincrementaldecoder('utf-8')(errors='replace')
        try:
            while True:
                data = await self.reader.read(4096)
                if not data:
                    break
                # a line cut in two by the read: wait a moment for the rest of it, so the page
                # gets it whole (a prompt, which ends no line, goes after that moment)
                while not data.endswith(b'\n'):
                    try:
                        more = await asyncio.wait_for(self.reader.read(4096), 0.05)
                    except asyncio.TimeoutError:
                        break
                    if not more:
                        break
                    data += more
                data = carry + data
                carry = b''
                # a hidden signal cut in two by the read: keep its start for the next one
                cut = data.rfind(b'\x1b]')
                # (an account's character list runs to a few hundred bytes)
                if cut != -1 and data.find(b'\x07', cut) == -1 and len(data) - cut < 4096:
                    data, carry = data[:cut], data[cut:]
                # and a colour code cut in two ("\x1b[3" | "7m"): the same
                tail = CSI_TAIL.search(data)
                if tail:
                    data, carry = data[:tail.start()], data[tail.start():] + carry

                text = utf8.decode(data)
                
                # Check for MAPSYNC control sequence: \x1b]MAPSYNC:playername:token\x07 (the
                # token is this session's secret for the map server)
                mapsync_pattern = re.compile(r'\x1b\]MAPSYNC:([^\x07:]+)(?::([^\x07]+))?\x07')
                mapsync_match = mapsync_pattern.search(text)
                
                if mapsync_match:
                    player_name = mapsync_match.group(1)
                    # Send mapsync message
                    await self.ws.send_json({
                        'type': 'mapsync',
                        'player': player_name,
                        'token': mapsync_match.group(2) or '',
                    })
                    # Remove the control sequence from output
                    text = mapsync_pattern.sub('', text)

                # RESUME: this browser's sign-in token (security.py), kept by the page in
                # place of the password
                for m in list(RESUME_PATTERN.finditer(text)):
                    await self.ws.send_json({'type': 'resume', 'token': m.group(1)})
                text = RESUME_PATTERN.sub('', text)
                for m in list(ACCOUNT_PATTERN.finditer(text)):
                    try:
                        await self.ws.send_json({'type': 'account', **json.loads(m.group(1))})
                    except ValueError:
                        pass
                text = ACCOUNT_PATTERN.sub('', text)

                # Only send output if there's remaining text
                if KIND_PATTERN.sub('', text).strip():
                    # each line's kind (msgkind.py) as an empty mark the page reads
                    html = KIND_PATTERN.sub(r'<i data-k="\1"></i>', ansi_to_html(text))
                    await self.ws.send_json({
                        'type': 'output',
                        'data': html
                    })
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Read loop error: {e}")
    
    async def write(self, data: str):
        """Write to MUD server."""
        if self.writer:
            self.writer.write((data + '\r\n').encode('utf-8'))
            await self.writer.drain()
    
    async def close(self):
        """Close the connection."""
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass


class WebClient:
    """Web client server."""
    
    def __init__(self, mud_host: str = 'localhost', mud_port: int = 4000, web_port: int = 4003):
        self.mud_host = mud_host
        self.mud_port = mud_port
        self.web_port = web_port
        self.app = web.Application()
        self._setup_routes()
        self.runner = None
    
    def _setup_routes(self):
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/ws', self.handle_websocket)
        # CC0 art packs for the graphical client (docs/art/SOURCES.md). Served
        # here rather than by web_map's hand-rolled HTTP, which truncates
        # larger binary bodies; CORS so Phaser can read pixels off the canvas.
        art_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web_isometric', 'art')
        if os.path.isdir(art_dir):
            self.app.router.add_static('/art/', art_dir, show_index=False)
        self.app.on_response_prepare.append(self._cors)

    @staticmethod
    async def _cors(request, response):
        response.headers['Access-Control-Allow-Origin'] = '*'
    
    async def handle_index(self, request: web.Request) -> web.Response:
        """Serve the web client HTML."""
        return web.Response(text=CLIENT_HTML, content_type='text/html')
    
    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        bridge = TelnetBridge(ws, self.mud_host, self.mud_port)
        
        if not await bridge.connect():
            await ws.send_json({'type': 'error', 'data': 'Failed to connect to MUD server'})
            await ws.close()
            return ws
        
        await ws.send_json({'type': 'connected', 'data': 'Connected to Misthollow'})
        
        # Start read loop
        read_task = asyncio.create_task(bridge.read_loop())
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError:
                        data = None
                    if isinstance(data, dict):
                        if data.get('type') == 'input':
                            await bridge.write(str(data.get('data', '')))
                    else:
                        # Plain text input (a bare number or word parses as JSON too)
                        await bridge.write(msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    break
        finally:
            read_task.cancel()
            await bridge.close()
        
        return ws
    
    async def start(self):
        """Start the web client server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', self.web_port, reuse_address=True)
        await site.start()
        logger.info(f"Web client listening on http://0.0.0.0:{self.web_port}")
    
    async def stop(self):
        """Stop the web client server."""
        if self.runner:
            await self.runner.cleanup()


# Embedded HTML client
CLIENT_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Misthollow</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        :root {
            --bg-color: #0c0c0c;
            --terminal-bg: #0d1117;
            --panel-bg: #161b22;
            --text-color: #e6edf3;
            --text-dim: #8b949e;
            --border-color: #30363d;
            --accent: #58a6ff;
            --accent-glow: rgba(88, 166, 255, 0.15);
            --success: #3fb950;
            --warning: #d29922;
            --danger: #f85149;
            --hp-color: #f85149;
            --mana-color: #58a6ff;
            --move-color: #3fb950;
            --gold-color: #d4a72c;
        }
        
        body {
            background: var(--bg-color);
            color: var(--text-color);
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            height: 100vh;
            height: 100dvh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        button:focus-visible {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
            border-radius: 4px;
        }
        
        /* Header */
        header {
            background: linear-gradient(180deg, var(--panel-bg) 0%, var(--terminal-bg) 100%);
            border-bottom: 1px solid var(--border-color);
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-shrink: 0;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .logo-icon {
            font-size: 1.5rem;
            filter: drop-shadow(0 0 8px rgba(88, 166, 255, 0.5));
        }
        
        header h1 {
            font-family: 'Inter', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-color);
            letter-spacing: -0.02em;
        }
        
        header h1 span {
            color: var(--accent);
        }
        
        .header-controls {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .header-btn {
            background: var(--terminal-bg);
            border: 1px solid var(--border-color);
            color: var(--text-dim);
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-family: 'Inter', sans-serif;
            font-size: 0.8rem;
            font-weight: 500;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .header-btn:hover {
            border-color: var(--accent);
            color: var(--accent);
            background: var(--accent-glow);
        }
        
        .header-btn.active {
            background: var(--accent);
            color: var(--bg-color);
            border-color: var(--accent);
        }
        
        .status-badge {
            font-family: 'Inter', sans-serif;
            font-size: 0.75rem;
            font-weight: 500;
            padding: 4px 10px;
            border-radius: 20px;
            background: var(--success);
            color: #fff;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .status-badge::before {
            content: '';
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #fff;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .status-badge.disconnected {
            background: var(--danger);
        }
        
        .status-badge.connecting {
            background: var(--warning);
        }
        
        /* Main content */
        .main-content {
            flex: 1;
            display: flex;
            overflow: hidden;
            position: relative;
        }
        
        /* Terminal */
        .terminal-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;
        }
        
        #terminal {
            flex: 1;
            overflow-y: auto;
            padding: 16px 20px;
            background: var(--terminal-bg);
            font-size: 0.9rem;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        #terminal::-webkit-scrollbar {
            width: 8px;
        }
        
        #terminal::-webkit-scrollbar-track {
            background: var(--terminal-bg);
        }
        
        #terminal::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 4px;
        }
        
        #terminal::-webkit-scrollbar-thumb:hover {
            background: var(--text-dim);
        }
        
        .cmd-echo {
            color: var(--accent);
            opacity: 0.8;
        }
        
        /* Map panel */
        .map-panel {
            width: 380px;
            border-left: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            background: var(--terminal-bg);
            transition: all 0.25s ease;
        }
        
        .map-panel.hidden {
            width: 0;
            border-left: none;
            overflow: hidden;
        }
        
        .map-header {
            padding: 10px 14px;
            background: var(--panel-bg);
            border-bottom: 1px solid var(--border-color);
            font-family: 'Inter', sans-serif;
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--text-dim);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .map-header button {
            background: none;
            border: none;
            color: var(--text-dim);
            cursor: pointer;
            font-size: 1rem;
            padding: 2px 6px;
            border-radius: 4px;
            transition: all 0.15s;
        }
        
        .map-header button:hover {
            color: var(--accent);
            background: var(--accent-glow);
        }
        
        #map-frame {
            flex: 1;
            border: none;
            background: #0d1117;
        }
        
        /* Controls area */
        .controls-area {
            flex-shrink: 0;
            background: var(--panel-bg);
            border-top: 1px solid var(--border-color);
        }
        
        /* Vitals bar */
        .vitals-bar {
            display: flex;
            gap: 8px;
            padding: 10px 20px;
            background: var(--terminal-bg);
        }
        
        .vital {
            flex: 1;
            height: 26px;
            background: rgba(0,0,0,0.4);
            border-radius: 6px;
            position: relative;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }
        
        .vital-fill {
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            border-radius: 5px;
            transition: width 0.4s ease;
        }
        
        .vital.hp .vital-fill {
            background: linear-gradient(90deg, #991b1b, var(--hp-color));
            box-shadow: 0 0 12px rgba(248, 81, 73, 0.3);
        }
        
        .vital.mana .vital-fill {
            background: linear-gradient(90deg, #1e40af, var(--mana-color));
            box-shadow: 0 0 12px rgba(88, 166, 255, 0.3);
        }
        
        .vital.move .vital-fill {
            background: linear-gradient(90deg, #166534, var(--move-color));
            box-shadow: 0 0 12px rgba(63, 185, 80, 0.3);
        }
        
        .vital-content {
            position: relative;
            z-index: 2;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 100%;
            padding: 0 10px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .vital-label {
            color: rgba(255,255,255,0.7);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .vital-text {
            color: #fff;
            font-weight: 600;
        }
        
        /* Room info */
        .room-info {
            padding: 8px 20px;
            background: var(--terminal-bg);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .room-name {
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--accent);
            flex: 1;
        }
        
        .room-exits {
            display: flex;
            gap: 4px;
        }
        
        .exit-btn {
            width: 24px;
            height: 24px;
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            color: var(--text-dim);
            font-size: 0.7rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s;
        }
        
        .exit-btn:hover {
            border-color: var(--accent);
            color: var(--accent);
            background: var(--accent-glow);
        }
        
        .exit-btn.available {
            color: var(--success);
            border-color: var(--success);
        }
        
        /* Quick commands */
        .quick-commands {
            display: flex;
            gap: 6px;
            padding: 8px 20px;
            flex-wrap: wrap;
        }
        
        .quick-btn {
            background: var(--terminal-bg);
            border: 1px solid var(--border-color);
            color: var(--text-dim);
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-family: 'Inter', sans-serif;
            font-size: 0.75rem;
            font-weight: 500;
            transition: all 0.15s;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .quick-btn:hover {
            border-color: var(--accent);
            color: var(--accent);
            background: var(--accent-glow);
        }
        
        .quick-btn:active {
            transform: scale(0.96);
        }
        
        .quick-btn.combat {
            border-color: var(--danger);
            color: var(--danger);
        }
        
        .quick-btn.combat:hover {
            background: rgba(248, 81, 73, 0.15);
        }
        
        /* Input area */
        #input-area {
            display: flex;
            padding: 12px 20px;
            gap: 10px;
            align-items: center;
        }
        
        .input-prompt {
            color: var(--accent);
            font-size: 1.1rem;
            font-weight: bold;
        }
        
        #command-input {
            flex: 1;
            background: var(--terminal-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-color);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.95rem;
            padding: 10px 14px;
            outline: none;
            transition: all 0.15s;
        }
        
        #command-input:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-glow);
        }
        
        #command-input::placeholder {
            color: var(--text-dim);
            opacity: 0.6;
        }
        
        .send-btn {
            background: var(--accent);
            border: none;
            color: var(--bg-color);
            padding: 10px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem;
            font-weight: 600;
            transition: all 0.15s;
        }
        
        .send-btn:hover {
            filter: brightness(1.1);
            transform: translateY(-1px);
        }
        
        .send-btn:active {
            transform: translateY(0);
        }
        
        /* ANSI Colors - Enhanced */
        .ansi-black { color: #636e7b; }
        .ansi-red { color: #ff7b72; }
        .ansi-green { color: #7ee787; }
        .ansi-yellow { color: #ffd33d; }
        .ansi-blue { color: #79c0ff; }
        .ansi-magenta { color: #d2a8ff; }
        .ansi-cyan { color: #a5d6ff; }
        .ansi-white { color: #e6edf3; }
        
        .ansi-bright-black { color: #8b949e; }
        .ansi-bright-red { color: #ffa198; }
        .ansi-bright-green { color: #a5f3a6; }
        .ansi-bright-yellow { color: #ffdf5d; }
        .ansi-bright-blue { color: #a5d6ff; }
        .ansi-bright-magenta { color: #e2c5ff; }
        .ansi-bright-cyan { color: #bbecf5; }
        .ansi-bright-white { color: #ffffff; }
        
        .ansi-bold { font-weight: 700; }
        
        /* Combat flash effect */
        .combat-flash {
            animation: combatPulse 1s ease-in-out;
        }
        
        @keyframes combatPulse {
            0%, 100% { background: var(--terminal-bg); }
            50% { background: rgba(248, 81, 73, 0.1); }
        }
        
        /* Welcome overlay */
        .welcome-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            animation: fadeIn 0.3s ease;
        }
        
        .welcome-overlay.hidden {
            display: none;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .welcome-content {
            text-align: center;
            max-width: 500px;
            padding: 40px;
        }
        
        .welcome-logo {
            font-size: 4rem;
            margin-bottom: 20px;
            filter: drop-shadow(0 0 30px rgba(88, 166, 255, 0.5));
            animation: float 3s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
        
        .welcome-title {
            font-family: 'Inter', sans-serif;
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--text-color);
            margin-bottom: 10px;
        }
        
        .welcome-title span {
            color: var(--accent);
        }
        
        .welcome-subtitle {
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            color: var(--text-dim);
            margin-bottom: 30px;
        }
        
        .welcome-status {
            font-size: 0.9rem;
            color: var(--warning);
        }
        
        /* Mobile */
        @media (max-width: 900px) {
            .map-panel {
                position: fixed;
                right: 0;
                top: 0;
                bottom: 0;
                width: 100%;
                max-width: 100%;
                z-index: 100;
            }
            .map-panel.hidden {
                transform: translateX(100%);
            }
            .room-info { display: none; }
        }
        
        @media (max-width: 600px) {
            header { padding: 10px 14px; }
            header h1 { font-size: 1rem; }
            #terminal { padding: 12px 14px; font-size: 0.85rem; }
            #input-area { padding: 10px 14px; }
            .quick-commands { padding: 6px 14px; }
            .vitals-bar { padding: 8px 14px; }
            .quick-btn { padding: 5px 10px; font-size: 0.7rem; }
        }
    </style>
</head>
<body>
    <!-- Welcome overlay -->
    <div class="welcome-overlay" id="welcome-overlay">
        <div class="welcome-content">
            <div class="welcome-logo">⚔️</div>
            <h1 class="welcome-title">Mist<span>hollow</span></h1>
            <p class="welcome-subtitle">A classic text adventure awaits</p>
            <div style="text-align:left;background:rgba(0,0,0,0.3);border-radius:12px;padding:16px 20px;margin:16px 0;font-size:0.85rem;line-height:1.6;max-width:340px;">
                <div style="color:#4ade80;font-weight:600;margin-bottom:8px;">🆕 New Player?</div>
                <div style="color:#94a3b8;">Type any name → say <b style="color:#e2e8f0;">Y</b> to create → pick a password → choose your class!</div>
                <div style="color:#4ade80;font-weight:600;margin:12px 0 8px;">🔑 Returning?</div>
                <div style="color:#94a3b8;">Type your name → enter your password</div>
            </div>
            <p class="welcome-status" id="welcome-status">Connecting to server...</p>
        </div>
    </div>

    <header>
        <div class="logo">
            <span class="logo-icon">⚔️</span>
            <h1>Mist<span>hollow</span></h1>
        </div>
        <div class="header-controls">
            <button class="header-btn" id="settings-btn" aria-label="Settings">⚙️</button>
            <button class="header-btn active" id="toggle-map" aria-label="Toggle Map">🗺️ Map</button>
            <span class="status-badge" id="status">Connected</span>
        </div>
    </header>
    
    <div class="main-content">
        <div class="terminal-panel">
            <!-- Room info bar -->
            <div class="room-info" id="room-info" style="display:none;">
                <span class="room-name" id="room-name">Unknown Location</span>
                <div class="room-exits" id="room-exits">
                <button class="exit-btn" data-dir="north" title="North" aria-label="Go North">N</button>
                <button class="exit-btn" data-dir="south" title="South" aria-label="Go South">S</button>
                <button class="exit-btn" data-dir="east" title="East" aria-label="Go East">E</button>
                <button class="exit-btn" data-dir="west" title="West" aria-label="Go West">W</button>
                <button class="exit-btn" data-dir="up" title="Up" aria-label="Go Up">U</button>
                <button class="exit-btn" data-dir="down" title="Down" aria-label="Go Down">D</button>
                </div>
            </div>
            <div id="terminal" role="log" aria-live="polite"></div>
        </div>
        
        <div class="map-panel" id="map-panel">
            <div class="map-header">
                <span>🗺️ World Map</span>
                <button id="close-map" title="Close map" aria-label="Close Map">✕</button>
            </div>
            <iframe id="map-frame" src="about:blank"></iframe>
        </div>
    </div>
    
    <div class="controls-area">
        <!-- Vitals bar -->
        <div class="vitals-bar" id="vitals-bar" style="display:none;">
            <div class="vital hp">
                <div class="vital-fill" id="hp-fill" style="width:100%"></div>
                <div class="vital-content">
                    <span class="vital-label">HP</span>
                    <span class="vital-text" id="hp-text">--/--</span>
                </div>
            </div>
            <div class="vital mana">
                <div class="vital-fill" id="mana-fill" style="width:100%"></div>
                <div class="vital-content">
                    <span class="vital-label">Mana</span>
                    <span class="vital-text" id="mana-text">--/--</span>
                </div>
            </div>
            <div class="vital move">
                <div class="vital-fill" id="move-fill" style="width:100%"></div>
                <div class="vital-content">
                    <span class="vital-label">Move</span>
                    <span class="vital-text" id="move-text">--/--</span>
                </div>
            </div>
        </div>
        
        <div class="quick-commands">
            <button class="quick-btn" data-cmd="look">👁️ Look</button>
            <button class="quick-btn" data-cmd="inventory">🎒 Inv</button>
            <button class="quick-btn" data-cmd="equipment">⚔️ Gear</button>
            <button class="quick-btn" data-cmd="score">📊 Stats</button>
            <button class="quick-btn" data-cmd="quest">📜 Quest</button>
            <button class="quick-btn" data-cmd="who">👥 Who</button>
            <button class="quick-btn" data-cmd="help">❓ Help</button>
            <button class="quick-btn combat" data-cmd="flee">🏃 Flee</button>
        </div>
        
        <div id="input-area">
            <span class="input-prompt">&gt;</span>
            <input type="text" id="command-input" placeholder="Enter command..." aria-label="Command Input" autocomplete="off" autofocus>
            <button class="send-btn" id="send-btn">Send</button>
        </div>
    </div>
    
    <!-- Settings Modal -->
    <div id="settings-modal" class="modal" style="display:none;">
        <div class="modal-content">
            <div class="modal-header">
                <h2>⚙️ Settings</h2>
                <button class="close-modal" id="close-settings" aria-label="Close Settings">✕</button>
            </div>
            <div class="modal-body">
                <div class="setting-group">
                    <label>Font Size</label>
                    <div class="setting-control">
                        <button class="setting-btn" id="font-decrease">A-</button>
                        <span id="font-size-display">14px</span>
                        <button class="setting-btn" id="font-increase">A+</button>
                    </div>
                </div>
                <div class="setting-group">
                    <label id="autoscroll-label">Scroll on Output</label>
                    <div class="setting-control">
                        <button class="setting-btn toggle active" id="autoscroll-toggle" role="switch" aria-checked="true" aria-labelledby="autoscroll-label">ON</button>
                    </div>
                </div>
                <div class="setting-group">
                    <label id="echo-label">Command Echo</label>
                    <div class="setting-control">
                        <button class="setting-btn toggle active" id="echo-toggle" role="switch" aria-checked="true" aria-labelledby="echo-label">ON</button>
                    </div>
                </div>
                <div class="setting-group">
                    <label id="sound-label">Sound Effects</label>
                    <div class="setting-control">
                        <button class="setting-btn toggle" id="sound-toggle" role="switch" aria-checked="false" aria-labelledby="sound-label">OFF</button>
                    </div>
                </div>
                <div class="setting-group">
                    <label id="timestamp-label">Timestamps</label>
                    <div class="setting-control">
                        <button class="setting-btn toggle" id="timestamp-toggle" role="switch" aria-checked="false" aria-labelledby="timestamp-label">OFF</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <style>
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .modal-content {
            background: #1a1a2e;
            border: 1px solid #4a4a6a;
            border-radius: 8px;
            width: 320px;
            max-width: 90%;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            border-bottom: 1px solid #4a4a6a;
        }
        .modal-header h2 {
            margin: 0;
            font-size: 16px;
            color: #88c0d0;
        }
        .close-modal {
            background: none;
            border: none;
            color: #888;
            font-size: 18px;
            cursor: pointer;
        }
        .close-modal:hover { color: #fff; }
        .modal-body {
            padding: 16px;
        }
        .setting-group {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .setting-group label {
            color: #a0a0b0;
            font-size: 13px;
        }
        .setting-control {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .setting-btn {
            background: #2a2a4a;
            border: 1px solid #4a4a6a;
            color: #88c0d0;
            padding: 4px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }
        .setting-btn:hover {
            background: #3a3a5a;
        }
        .setting-btn.toggle {
            min-width: 40px;
        }
        .setting-btn.toggle.active {
            background: #2e7d32;
            border-color: #4caf50;
        }
        #font-size-display {
            color: #fff;
            min-width: 40px;
            text-align: center;
            font-size: 12px;
        }
    </style>
    
    <script>
        const terminal = document.getElementById('terminal');
        const input = document.getElementById('command-input');
        const status = document.getElementById('status');
        const mapPanel = document.getElementById('map-panel');
        const toggleMapBtn = document.getElementById('toggle-map');
        const closeMapBtn = document.getElementById('close-map');
        const mapFrame = document.getElementById('map-frame');
        const welcomeOverlay = document.getElementById('welcome-overlay');
        const welcomeStatus = document.getElementById('welcome-status');
        const roomInfo = document.getElementById('room-info');
        const roomName = document.getElementById('room-name');
        const vitalsBar = document.getElementById('vitals-bar');
        const sendBtn = document.getElementById('send-btn');
        
        let ws = null;
        let commandHistory = [];
        let historyIndex = -1;
        let playerName = null;
        let inCombat = false;
        
        // Set map URL
        const mapUrl = `${location.protocol}//${location.hostname}:4001`;
        mapFrame.src = mapUrl;
        
        function setStatus(state, text) {
            status.textContent = text;
            status.className = 'status-badge ' + state;
        }
        
        function updateVitals(hp, maxHp, mana, maxMana, move, maxMove) {
            vitalsBar.style.display = 'flex';
            
            document.getElementById('hp-text').textContent = hp + '/' + maxHp;
            document.getElementById('hp-fill').style.width = Math.max(0, Math.min(100, (hp/maxHp)*100)) + '%';
            
            document.getElementById('mana-text').textContent = mana + '/' + maxMana;
            document.getElementById('mana-fill').style.width = Math.max(0, Math.min(100, (mana/maxMana)*100)) + '%';
            
            document.getElementById('move-text').textContent = move + '/' + maxMove;
            document.getElementById('move-fill').style.width = Math.max(0, Math.min(100, (move/maxMove)*100)) + '%';
        }
        
        function updateRoomInfo(name, exits) {
            roomInfo.style.display = 'flex';
            roomName.textContent = name;
            
            // Reset all exit buttons
            document.querySelectorAll('.exit-btn').forEach(btn => {
                btn.classList.remove('available');
            });
            
            // Highlight available exits
            if (exits) {
                exits.forEach(dir => {
                    const btn = document.querySelector(`.exit-btn[data-dir="${dir}"]`);
                    if (btn) btn.classList.add('available');
                });
            }
        }
        
        function triggerCombatFlash() {
            terminal.classList.add('combat-flash');
            setTimeout(() => terminal.classList.remove('combat-flash'), 1000);
        }
        
        function appendOutput(html) {
            // Check if we are at the bottom before adding new content
            const isAtBottom = Math.abs(terminal.scrollHeight - terminal.scrollTop - terminal.clientHeight) < 10;

            terminal.insertAdjacentHTML('beforeend', html);

            // Auto-scroll if at the bottom AND settings allow it
            let shouldScroll = true;
            try {
                if (typeof settings !== 'undefined' && settings.autoScroll === false) {
                    shouldScroll = false;
                }
            } catch (e) {
                // settings might be in temporal dead zone, default to true
            }

            if (isAtBottom && shouldScroll) {
                terminal.scrollTop = terminal.scrollHeight;
            }
            
            // Detect player name
            if (!playerName) {
                const match = html.match(/Welcome back, ([^!]+)!/);
                if (match) {
                    playerName = match[1].trim();
                    updateMapPlayer();
                }
            }
            
            // Parse vitals from prompt
            const vitalsMatch = html.match(/HP:\\s*(\\d+)\\/(\\d+)\\s*Mana:\\s*(\\d+)\\/(\\d+)\\s*Move:\\s*(\\d+)\\/(\\d+)/);
            if (vitalsMatch) {
                updateVitals(
                    parseInt(vitalsMatch[1]), parseInt(vitalsMatch[2]),
                    parseInt(vitalsMatch[3]), parseInt(vitalsMatch[4]),
                    parseInt(vitalsMatch[5]), parseInt(vitalsMatch[6])
                );
            }
            
            // Detect combat
            if (html.includes('You are fighting') || html.includes('attacks you') || html.includes('hits you')) {
                if (!inCombat) {
                    inCombat = true;
                    triggerCombatFlash();
                }
            }
            if (html.includes('is dead!') || html.includes('You flee')) {
                inCombat = false;
            }
            
            // Try to detect room name and exits
            const roomMatch = html.match(/<span class="ansi-[^"]*">([^<]+)<\\/span>\\s*\\n.*Exits:/s);
            if (roomMatch) {
                // Simple exit detection
                const exitMatch = html.match(/Exits:\\s*([^\\n]+)/);
                if (exitMatch) {
                    const exitText = exitMatch[1].toLowerCase();
                    const exits = [];
                    if (exitText.includes('north')) exits.push('north');
                    if (exitText.includes('south')) exits.push('south');
                    if (exitText.includes('east')) exits.push('east');
                    if (exitText.includes('west')) exits.push('west');
                    if (exitText.includes('up')) exits.push('up');
                    if (exitText.includes('down')) exits.push('down');
                    updateRoomInfo(roomMatch[1].trim(), exits);
                }
            }
        }
        
        function updateMapPlayer() {
            if (playerName && mapFrame.contentWindow) {
                try {
                    mapFrame.contentWindow.postMessage({ type: 'setPlayer', name: playerName }, '*');
                } catch (e) {}
            }
        }
        
        function toggleMap() {
            mapPanel.classList.toggle('hidden');
            toggleMapBtn.classList.toggle('active');
        }
        
        toggleMapBtn.addEventListener('click', toggleMap);
        closeMapBtn.addEventListener('click', toggleMap);
        
        function connect() {
            welcomeStatus.textContent = 'Connecting to server...';
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);
            
            ws.onopen = () => {
                setStatus('', 'Connected');
                welcomeOverlay.classList.add('hidden');
            };
            
            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.type === 'output') {
                    appendOutput(msg.data);
                } else if (msg.type === 'mapsync') {
                    playerName = msg.player;
                    const newMapUrl = `${mapUrl}/?player=${encodeURIComponent(playerName)}&t=${encodeURIComponent(msg.token || '')}`;
                    if (mapFrame.src !== newMapUrl) {
                        mapFrame.src = newMapUrl;
                    }
                } else if (msg.type === 'error') {
                    appendOutput(`<span class="ansi-red">${msg.data}</span>\\n`);
                }
            };
            
            ws.onclose = () => {
                setStatus('disconnected', 'Disconnected');
                appendOutput('<span class="ansi-yellow">\\n--- Connection closed. Refresh to reconnect. ---\\n</span>');
            };
            
            ws.onerror = () => {
                setStatus('disconnected', 'Error');
                welcomeStatus.textContent = 'Connection failed. Is the server running?';
            };
        }
        
        function sendCommand(cmd) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                if (cmd.trim()) {
                    appendOutput('<span class="cmd-echo">&gt; ' + cmd.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</span>\\r\\n');
                }
                ws.send(JSON.stringify({ type: 'input', data: cmd }));
                if (cmd.trim() && (commandHistory.length === 0 || commandHistory[0] !== cmd)) {
                    commandHistory.unshift(cmd);
                    if (commandHistory.length > 100) commandHistory.pop();
                }
                historyIndex = -1;
            }
        }
        
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const cmd = input.value;
                sendCommand(cmd);
                input.value = '';
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (historyIndex < commandHistory.length - 1) {
                    historyIndex++;
                    input.value = commandHistory[historyIndex];
                }
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (historyIndex > 0) {
                    historyIndex--;
                    input.value = commandHistory[historyIndex];
                } else if (historyIndex === 0) {
                    historyIndex = -1;
                    input.value = '';
                }
            }
        });
        
        sendBtn.addEventListener('click', () => {
            const cmd = input.value;
            sendCommand(cmd);
            input.value = '';
            input.focus();
        });
        
        // Quick command buttons
        document.querySelectorAll('.quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                sendCommand(btn.dataset.cmd);
                input.focus();
            });
        });
        
        // Exit buttons
        document.querySelectorAll('.exit-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                sendCommand(btn.dataset.dir);
                input.focus();
            });
        });
        
        // Focus input on terminal click
        terminal.addEventListener('click', () => input.focus());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (document.activeElement === input) return;
            
            if (e.key === 'm') toggleMap();
            if (e.key === '/') { input.focus(); e.preventDefault(); }
            if (e.key === 'Escape') {
                document.getElementById('settings-modal').style.display = 'none';
            }
        });
        
        // Settings modal
        const settingsModal = document.getElementById('settings-modal');
        const settingsBtn = document.getElementById('settings-btn');
        const closeSettingsBtn = document.getElementById('close-settings');
        
        // Load settings from localStorage
        let settings = {
            fontSize: parseInt(localStorage.getItem('mudFontSize') || '14'),
            autoScroll: localStorage.getItem('mudAutoScroll') !== 'false',
            echo: localStorage.getItem('mudEcho') !== 'false',
            sound: localStorage.getItem('mudSound') === 'true',
            timestamps: localStorage.getItem('mudTimestamps') === 'true'
        };
        
        // Apply settings
        function applySettings() {
            terminal.style.fontSize = settings.fontSize + 'px';
            document.getElementById('font-size-display').textContent = settings.fontSize + 'px';
            
            const autoscrollToggle = document.getElementById('autoscroll-toggle');
            autoscrollToggle.classList.toggle('active', settings.autoScroll);
            autoscrollToggle.textContent = settings.autoScroll ? 'ON' : 'OFF';
            autoscrollToggle.setAttribute('aria-checked', settings.autoScroll ? 'true' : 'false');
            
            const echoToggle = document.getElementById('echo-toggle');
            echoToggle.classList.toggle('active', settings.echo);
            echoToggle.textContent = settings.echo ? 'ON' : 'OFF';
            echoToggle.setAttribute('aria-checked', settings.echo ? 'true' : 'false');
            
            const soundToggle = document.getElementById('sound-toggle');
            soundToggle.classList.toggle('active', settings.sound);
            soundToggle.textContent = settings.sound ? 'ON' : 'OFF';
            soundToggle.setAttribute('aria-checked', settings.sound ? 'true' : 'false');
            
            const timestampToggle = document.getElementById('timestamp-toggle');
            timestampToggle.classList.toggle('active', settings.timestamps);
            timestampToggle.textContent = settings.timestamps ? 'ON' : 'OFF';
            timestampToggle.setAttribute('aria-checked', settings.timestamps ? 'true' : 'false');
        }
        
        function saveSettings() {
            localStorage.setItem('mudFontSize', settings.fontSize);
            localStorage.setItem('mudAutoScroll', settings.autoScroll);
            localStorage.setItem('mudEcho', settings.echo);
            localStorage.setItem('mudSound', settings.sound);
            localStorage.setItem('mudTimestamps', settings.timestamps);
        }
        
        settingsBtn.addEventListener('click', () => {
            settingsModal.style.display = 'flex';
        });
        
        closeSettingsBtn.addEventListener('click', () => {
            settingsModal.style.display = 'none';
        });
        
        settingsModal.addEventListener('click', (e) => {
            if (e.target === settingsModal) settingsModal.style.display = 'none';
        });
        
        document.getElementById('font-increase').addEventListener('click', () => {
            if (settings.fontSize < 24) {
                settings.fontSize += 2;
                applySettings();
                saveSettings();
            }
        });
        
        document.getElementById('font-decrease').addEventListener('click', () => {
            if (settings.fontSize > 10) {
                settings.fontSize -= 2;
                applySettings();
                saveSettings();
            }
        });
        
        document.getElementById('autoscroll-toggle').addEventListener('click', () => {
            settings.autoScroll = !settings.autoScroll;
            applySettings();
            saveSettings();
        });
        
        document.getElementById('echo-toggle').addEventListener('click', () => {
            settings.echo = !settings.echo;
            applySettings();
            saveSettings();
        });
        
        document.getElementById('sound-toggle').addEventListener('click', () => {
            settings.sound = !settings.sound;
            applySettings();
            saveSettings();
        });
        
        document.getElementById('timestamp-toggle').addEventListener('click', () => {
            settings.timestamps = !settings.timestamps;
            applySettings();
            saveSettings();
        });
        
        // Apply initial settings
        applySettings();
        
        // Connect
        connect();
    </script>
</body>
</html>
'''


# Standalone runner for testing
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        client = WebClient()
        await client.start()
        print("Web client running at http://localhost:4003")
        print("Press Ctrl+C to stop")
        try:
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            await client.stop()
    
    asyncio.run(main())
