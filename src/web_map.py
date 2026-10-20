"""
Web map server for Misthollow.
Serves a lightweight HTML/JS interface and a minimal WebSocket for live updates.
"""

import asyncio
import base64
import gzip
import hashlib
import hmac
import json
import logging
import re
import os
import subprocess
import time
from typing import Optional
from urllib.parse import parse_qs, urlparse

from map_system import build_map_payload, build_combat_payload

logger = logging.getLogger('Misthollow.WebMap')


# a session token in a logged path (`?t=` / `&t=`, `token=`): the log is shown on the admin
# dashboard and kept on disk, so it never holds one
_TOKEN_IN_PATH = re.compile(r'([?&](?:t|token)=)[^&\s]+')


def _redact(path: str) -> str:
    return _TOKEN_IN_PATH.sub(r'\1…', path or '')


# ---- 3D client (/play) static files ----------------------------------------------
# Everything the 3D client loads is served from here (same origin as the page, so no
# proxy or CORS setup). URLs under /v/<version>/ are immutable: the version is the git
# commit the server started from, so a deploy changes every URL and browsers and
# Cloudflare never serve a stale module (no more Cmd+Shift+R after a deploy).
_WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web_isometric')
_STATIC_3D = {
    'world3d': ('world3d', {'js', 'json', 'css', 'mp3', 'ogg', 'm4a', 'wav'}),
    'shared': ('shared', {'js'}),     # net, parser, zone themes, item icons, room layouts
    'vendor': ('vendor', {'js'}),
    'art3d': ('art3d', {'glb', 'png', 'webp', 'json'}),
    'fonts': ('fonts', {'woff2'}),
}
_CT_3D = {'js': 'text/javascript', 'json': 'application/json', 'css': 'text/css',
          'glb': 'model/gltf-binary', 'png': 'image/png', 'webp': 'image/webp', 'woff2': 'font/woff2',
          'mp3': 'audio/mpeg', 'ogg': 'audio/ogg', 'm4a': 'audio/mp4', 'wav': 'audio/wav'}
_AUDIO_3D = {'mp3', 'ogg', 'm4a', 'wav'}   # served in parts on request (Range): music streams


def byte_range(header, size):
    """(start, end) for a single 'bytes=a-b' / 'bytes=a-' / 'bytes=-n' Range header, None when
    there is none or it can't be met."""
    m = re.fullmatch(r'\s*bytes=(\d*)-(\d*)\s*', header or '')
    if not m or (not m.group(1) and not m.group(2)):
        return None
    if m.group(1):
        start = int(m.group(1))
        end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
    else:
        start, end = max(0, size - int(m.group(2))), size - 1
    return (start, end) if 0 <= start <= end < size else None
_GZIP_3D = {'js', 'json', 'css', 'glb'}
_static_cache = {}   # full path -> (mtime, raw bytes, gzipped bytes or None)
_zonemap_bytes = {}  # zone -> (json bytes, gzipped)
_asset_version = None


def asset_version():
    global _asset_version
    if _asset_version is None:
        try:
            _asset_version = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'], cwd=_WEB_DIR, capture_output=True,
                text=True, timeout=5).stdout.strip() or None
        except Exception:
            _asset_version = None
        _asset_version = _asset_version or str(int(time.time()))
    return _asset_version


def static_3d(path):
    """Resolve a /v/<ver>/..., /world3d/, /shared/, /vendor/, /art3d/ or /fonts/ path to (file, ext, immutable),
    or None when it is not an allowed file (unknown root, extension, or traversal)."""
    rel = path.split('?', 1)[0]
    immutable = False
    if rel.startswith('/v/'):
        parts = rel.split('/', 3)
        if len(parts) < 4:
            return None
        rel, immutable = '/' + parts[3], True
    top, _, sub = rel.lstrip('/').partition('/')
    spec = _STATIC_3D.get(top)
    if not spec or not sub:
        return None
    base = os.path.realpath(os.path.join(_WEB_DIR, spec[0]))
    full = os.path.realpath(os.path.join(base, sub))
    ext = sub.rsplit('.', 1)[-1].lower() if '.' in sub else ''
    if not full.startswith(base + os.sep) or ext not in spec[1] or not os.path.isfile(full):
        return None
    return full, ext, immutable


def static_bytes(full, ext, want_gzip):
    mtime = os.path.getmtime(full)
    hit = _static_cache.get(full)
    if not hit or hit[0] != mtime:
        with open(full, 'rb') as f:
            raw = f.read()
        gz = gzip.compress(raw, 6) if ext in _GZIP_3D else None
        if gz is not None and len(gz) >= len(raw) * 0.95:
            gz = None
        hit = _static_cache[full] = (mtime, raw, gz)
    if want_gzip and hit[2] is not None:
        return hit[2], 'gzip'
    return hit[1], None


class WebMapClient:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.player_name: Optional[str] = None
        self.token: Optional[str] = None     # the session secret it subscribed with
        self.mode: str = 'full'
        self.combat: Optional[str] = None    # 'action': real-time combat (action_combat.py)


class WebMapServer:
    def __init__(self, world, config):
        self.world = world
        self.config = config
        self.server = None
        self.clients = set()

    async def start(self):
        self.server = await asyncio.start_server(self._handle_client, self.config.MAP_HOST, self.config.MAP_PORT, reuse_address=True)
        logger.info(f"Web map server listening on {self.config.MAP_HOST}:{self.config.MAP_PORT}")
        # Start background ping task to detect dead connections
        self._ping_task = asyncio.create_task(self._ping_clients_loop())

    async def _ping_clients_loop(self):
        """Periodically ping all WebSocket clients to detect dead connections."""
        while True:
            await asyncio.sleep(30)  # Ping every 30 seconds
            dead_clients = []
            for client in list(self.clients):
                success = await self._ws_ping(client.writer)
                if not success:
                    dead_clients.append(client)
            for client in dead_clients:
                self.clients.discard(client)
                logger.info(f"Removed stale WebSocket client for '{client.player_name}' (ping failed)")
                try:
                    client.writer.close()
                except Exception:
                    pass

    async def _ws_ping(self, writer):
        """Send a WebSocket ping frame. Returns True on success."""
        try:
            # Opcode 0x9 is ping, 0 length
            writer.write(bytes([0x89, 0x00]))
            await writer.drain()
            return True
        except Exception:
            return False

    async def stop(self):
        # Cancel ping task
        if hasattr(self, '_ping_task') and self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        # Close all clients
        for client in list(self.clients):
            try:
                client.writer.close()
            except Exception:
                pass
        self.clients.clear()

    # ---- other players, as the 3D clients around them see them ----
    def _viewers(self, vnums, skip_name=None, radius=3):
        """3D ('near') clients whose hero stands within `radius` cells of any of these rooms."""
        from map_system import zone_cell
        cells = [zone_cell(self.world, v) for v in vnums if v is not None]
        cells = [c for c in cells if c]
        out = []
        for client in list(self.clients):
            if client.mode != 'near' or not client.player_name:
                continue
            if skip_name and client.player_name.lower() == skip_name.lower():
                continue
            other = self.world.players.get(client.player_name.lower())
            room = getattr(other, 'room', None)
            oc = zone_cell(self.world, room.vnum) if room is not None else None
            if oc and any(c[0] == oc[0] and abs(c[1] - oc[1]) <= radius and abs(c[2] - oc[2]) <= radius for c in cells):
                out.append(client)
        return out

    async def _send_all(self, clients, event):
        data = json.dumps(event)
        for client in clients:
            try:
                if not await self._ws_send(client.writer, data):
                    self.clients.discard(client)
            except Exception:
                self.clients.discard(client)

    async def relay_presence(self, player):
        """A web player's position, to the 3D clients that can see them (at most 5 a second)."""
        now = time.monotonic()
        if now - getattr(player, '_presence_at', 0) < 0.2:
            return
        player._presence_at = now
        pos = getattr(player, 'web_pos', None)
        if not pos:
            return
        await self._send_all(self._viewers([pos[0]], skip_name=player.name),
                             {'type': 'presence', 'name': player.name, 'vnum': pos[0], 'x': round(pos[1], 2), 'z': round(pos[2], 2)})

    async def relay_look(self, player, look):
        """A character's gear changed (gear_look.py): the 3D clients that can see them re-dress them."""
        room = getattr(player, 'room', None)
        if room is None:
            return
        await self._send_all(self._viewers([room.vnum], skip_name=player.name),
                             {'type': 'look', 'name': player.name, 'look': look})

    async def note_room(self, player):
        """Tell the 3D clients around a player that the player changed rooms (any way: a walk,
        recall, a portal, following the leader...). Called whenever the player's own view is
        refreshed, so every kind of move is covered."""
        room = getattr(player, 'room', None)
        vnum = getattr(room, 'vnum', None)
        last = getattr(player, '_web_last_vnum', None)
        if vnum is None or vnum == last:
            return
        player._web_last_vnum = vnum
        if last is None:
            return
        await self._send_all(self._viewers([last, vnum], skip_name=player.name),
                             {'type': 'player_move', 'name': player.name, 'from': last, 'to': vnum, 'action': 'move'})

    async def notify_player(self, player):
        try:
            await self.note_room(player)
        except Exception as e:
            logger.debug(f"note_room failed: {e}")
        matching_clients = 0
        dead_clients = []
        client_names = [c.player_name for c in self.clients if c.player_name]
        logger.debug(f"notify_player called for '{player.name}', connected clients: {client_names}")
        for client in list(self.clients):
            if not client.player_name:
                continue
            if client.player_name.lower() != player.name.lower():
                continue
            matching_clients += 1
            try:
                payload = build_map_payload(player, mode=client.mode)
                logger.debug(f"notify_player: sending {len(payload.get('rooms', []))} rooms to '{client.player_name}'")
                success = await self._ws_send(client.writer, json.dumps(payload))
                if not success:
                    dead_clients.append(client)
                    logger.warning(f"notify_player: send failed for '{client.player_name}'")
                else:
                    logger.debug(f"notify_player: send SUCCESS for '{client.player_name}'")
            except Exception as e:
                logger.error(f"notify_player exception for '{client.player_name}': {e}")
                dead_clients.append(client)
        # Clean up dead clients
        for client in dead_clients:
            self.clients.discard(client)
            logger.info(f"Removed dead WebSocket client for '{client.player_name}'")
        if matching_clients == 0:
            # a telnet player has no map client: the usual case, not a fault
            logger.debug(f"notify_player: no map client for '{player.name}' (total clients: {len(self.clients)}, names: {client_names})")

    async def notify_room(self, room, event=None, skip=None):
        """Push fresh map payloads to every connected player standing in the
        room - optionally preceded by a lightweight event (mob movement) so
        graphical clients can animate the cause before the roster updates."""
        if not room:
            return
        for ch in list(getattr(room, 'characters', [])):
            if ch is skip:
                continue
            name = getattr(ch, 'name', None)
            if not name or not hasattr(ch, 'connection'):
                continue
            if name.lower() not in self.world.players:
                continue
            for client in list(self.clients):
                if not client.player_name or client.player_name.lower() != name.lower():
                    continue
                try:
                    if event:
                        await self._ws_send(client.writer, json.dumps(event))
                    payload = build_map_payload(ch, mode=client.mode)
                    await self._ws_send(client.writer, json.dumps(payload))
                except Exception:
                    self.clients.discard(client)

    async def send_room_event(self, room, event: dict):
        """A small structured event (combat_events.py) to the web clients of everyone in
        `room` — no map payload, so it is cheap enough to send many times a round."""
        names = {getattr(ch, 'name', '').lower() for ch in (getattr(room, 'characters', None) or [])
                 if hasattr(ch, 'account_name')}
        if not names:
            return
        data = json.dumps(event)
        dead = []
        for client in list(self.clients):
            if (client.player_name or '').lower() not in names:
                continue
            try:
                if not await self._ws_send(client.writer, data):
                    dead.append(client)
            except Exception:
                dead.append(client)
        for client in dead:
            self.clients.discard(client)

    async def send_zone_event(self, zones, event: dict):
        """A small structured event to every web client whose player stands in one of the
        `zones` (zone numbers): a door that opens or locks is seen by everyone nearby."""
        data = json.dumps(event)
        dead = []
        for client in list(self.clients):
            p = self.world.players.get((client.player_name or '').lower())
            room = getattr(p, 'room', None) if p else None
            zn = getattr(getattr(room, 'zone', None), 'number', None)
            if zn is None or zn not in zones:
                continue
            try:
                if not await self._ws_send(client.writer, data):
                    dead.append(client)
            except Exception:
                dead.append(client)
        for client in dead:
            self.clients.discard(client)

    async def notify_combat(self, player):
        """Push a lightweight vitals/entity update during combat rounds, to the
        fighter AND to everyone else standing in the room (each sees the round
        from their own side), so a party member's wind-ups, staggers and hits
        are visible to allies who are not themselves in the fight."""
        dead_clients = []
        room = getattr(player, 'room', None)
        viewers = {}
        viewers[player.name.lower()] = player
        for other in (getattr(room, 'characters', None) or []):
            if other is not player and hasattr(other, 'account_name') and getattr(other, 'name', None):
                viewers.setdefault(other.name.lower(), other)
        for client in list(self.clients):
            viewer = viewers.get((client.player_name or '').lower())
            if not viewer:
                continue
            try:
                payload = build_combat_payload(viewer)
                if not await self._ws_send(client.writer, json.dumps(payload)):
                    dead_clients.append(client)
            except Exception:
                dead_clients.append(client)
        for client in dead_clients:
            self.clients.discard(client)

    def has_play(self, player) -> bool:
        """Has this player the 3D client (/play) attached? Its ambient murmurs then come as
        sounds and cues on the map socket (ambient.py), not as chat lines."""
        n = str(getattr(player, 'name', '') or '').lower()
        return bool(n) and any(c.player_name and c.player_name.lower() == n for c in self.clients)

    async def notify_event(self, player, event: dict):
        """Push a small structured event (ambient echo, npc chatter...) to a
        player's connected web clients."""
        dead_clients = []
        for client in list(self.clients):
            if not client.player_name or client.player_name.lower() != player.name.lower():
                continue
            try:
                if not await self._ws_send(client.writer, json.dumps(event)):
                    dead_clients.append(client)
            except Exception:
                dead_clients.append(client)
        for client in dead_clients:
            self.clients.discard(client)

    async def _handle_client(self, reader, writer):
        try:
            request = await reader.readline()
            if not request:
                writer.close()
                return
            request_line = request.decode(errors='ignore').strip()
            parts = request_line.split(' ', 2)
            if len(parts) < 2:
                writer.close()
                return
            method = parts[0]
            path = parts[1]
            # a page load fetches a few hundred static files: those only at debug level
            static = path.startswith(('/v/', '/world3d/', '/shared/', '/vendor/', '/art3d/', '/fonts/'))
            (logger.debug if static else logger.info)(f"HTTP request: method='{method}' path='{_redact(path)}'")


            headers = {}
            while True:
                line = await reader.readline()
                if not line:
                    break
                line = line.decode(errors='ignore').strip()
                if line == '':
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()

            if headers.get('upgrade', '').lower() == 'websocket':
                await self._handle_websocket(reader, writer, headers)
                return

            if method not in ('GET', 'HEAD', 'OPTIONS'):
                logger.warning(f"Unexpected HTTP method: '{method}' for path '{_redact(path)}'")
                await self._http_response(writer, 405, 'Method Not Allowed', 'Method Not Allowed')
                return
            
            # Handle OPTIONS preflight
            if method == 'OPTIONS':
                self.send_response(200)
                return

            if path.startswith('/map.js'):
                await self._http_response(writer, 200, 'OK', self._js(), content_type='application/javascript')
            elif path.startswith('/map.css'):
                await self._http_response(writer, 200, 'OK', self._css(), content_type='text/css')
            elif path.startswith('/state'):
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                logger.info(f"HTTP /state request: player='{player_name}'")
                if not player_name:
                    await self._http_response(writer, 400, 'Bad Request', 'Missing player parameter')
                    return
                player = self._authed(query)
                if not player:
                    logger.warning(f"/state: no player '{player_name}' with that session token")
                    await self._http_response(writer, 404, 'Not Found', 'Player not found')
                    return
                # Ensure current room is in explored_rooms
                if player.room and hasattr(player, 'explored_rooms'):
                    if player.room.vnum not in player.explored_rooms:
                        player.explored_rooms.add(player.room.vnum)
                # the 3D client asks for mode=near (its zone + the occupants of nearby rooms)
                mode = (query.get('mode') or ['full'])[0]
                payload = build_map_payload(player, mode=mode if mode in ('full', 'zone', 'near') else 'full')
                logger.info(f"/state: returning {len(payload.get('rooms', []))} rooms for '{player_name}'")
                await self._http_response(writer, 200, 'OK', json.dumps(payload), content_type='application/json')
            elif path.startswith('/lookat'):
                # examine a detail: room extra descriptions, items, mobs,
                # inventory - resolved server-side so the client never has
                # to scrape the text stream
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                target = ((query.get('target') or [''])[0]).strip().lower()
                player = self._authed(query)
                if not player or not target or not player.room:
                    await self._http_response(writer, 200, 'OK', json.dumps({'found': False}), content_type='application/json')
                    return
                room = player.room
                result = None
                # room extra descriptions ("look at fountain")
                for keys, text in (getattr(room, 'extra_descs', None) or {}).items():
                    if any(target in k.lower() or k.lower() in target for k in keys.split()):
                        result = {'title': keys.split()[0].title(), 'text': text, 'kind': 'detail'}
                        break
                # mobs and players in the room
                if not result:
                    for ch in room.characters:
                        name = getattr(ch, 'name', '') or ''
                        kws = getattr(ch, 'keywords', None) or name.lower().split()
                        if target in name.lower() or any(target in k.lower() for k in kws):
                            text = getattr(ch, 'description', '') or getattr(ch, 'long_desc', '') or f'{name} looks unremarkable.'
                            result = {'title': name, 'text': text, 'kind': 'being'}
                            break
                # items on the ground, then in inventory
                if not result:
                    pools = [(getattr(room, 'items', None) or []), (getattr(player, 'inventory', None) or [])]
                    for pool in pools:
                        for it in pool:
                            name = getattr(it, 'name', '') or ''
                            if target in name.lower():
                                text = getattr(it, 'description', '') or getattr(it, 'long_desc', '') or getattr(it, 'short_desc', '') or 'Nothing remarkable.'
                                written = getattr(it, 'text', None)
                                if written and getattr(it, 'item_type', '') in ('note', 'scroll', 'book'):
                                    text = f"{text}\n\n\u201c{written}\u201d"
                                result = {'title': getattr(it, 'short_desc', name) or name, 'text': text, 'kind': 'item'}
                                break
                        if result:
                            break
                body = json.dumps(dict(result, found=True)) if result else json.dumps({'found': False})
                await self._http_response(writer, 200, 'OK', body, content_type='application/json')
            elif path.startswith('/abilitybook'):
                # a class's abilities for the 3D client's spellbook: what each is, costs, reaches
                # and unlocks at (static; how well a player knows them comes in the map payload)
                import mastery
                q = parse_qs(urlparse(path).query)
                klass = (q.get('cls') or [''])[0].lower()
                body = json.dumps({'cls': klass, 'abilities': mastery.book(klass), 'byUse': mastery.BY_USE,
                                   'learnAt': mastery.LEARN_AT, 'step': mastery.STEP})
                await self._http_response(writer, 200, 'OK', body, content_type='application/json')
            elif path.startswith('/combatdata'):
                # combat v2 ranges for the 3D client (one source of truth: combat_range.py)
                import combat_range as cr
                import action_combat
                body = json.dumps({
                    'melee': cr.MELEE, 'pointBlank': cr.POINT_BLANK, 'round': cr.round_seconds(),
                    'npcDelay': cr.NPC_PHASE_DELAY,
                    'auto': {k: {'range': v[0], 'ranged': v[1]} for k, v in cr.AUTO_RANGE.items()},
                    # the weapon in hand comes first (a bow shoots whoever holds it)
                    'weapons': {k: {'range': v[0], 'ranged': v[1]} for k, v in cr.WEAPON_RANGE.items()},
                    'abilities': {k: {'range': v[0], 'shape': v[1]} for k, v in cr.ABILITY_RANGE.items()},
                    'spellDefault': cr.DEFAULT_SPELL[0],
                    # real-time combat (action_combat.py): the clocks the client predicts with
                    'action': {'on': action_combat.enabled(), 'swing': action_combat.SWING, 'gcd': action_combat.GCD,
                               'windup': action_combat.WINDUP, 'perfect': action_combat.PERFECT_WINDOW,
                               'grace': action_combat.PERFECT_GRACE},
                })
                await self._http_response(writer, 200, 'OK', body, content_type='application/json')
            elif path.startswith('/zonemap'):
                # one zone as a continuous space for the 3D client (/play); static per run
                from map_system import build_zonemap
                q = parse_qs(urlparse(path).query)
                try:
                    zone = int((q.get('zone') or [''])[0]) if q.get('zone') else None
                    if zone is None and q.get('vnum'):
                        room = self.world.rooms.get(int(q['vnum'][0]))
                        zone = room.zone.number if room and room.zone else None
                except ValueError:
                    zone = None
                data = build_zonemap(self.world, zone) if zone is not None else None
                if not data:
                    await self._http_response(writer, 404, 'Not Found', json.dumps({'found': False}),
                                              content_type='application/json')
                    return
                hit = _zonemap_bytes.get(zone)
                if not hit:
                    raw = json.dumps(data, separators=(',', ':')).encode()
                    hit = _zonemap_bytes[zone] = (raw, gzip.compress(raw, 6))
                gz = 'gzip' in headers.get('accept-encoding', '')
                body = hit[1] if gz else hit[0]
                head = ["HTTP/1.1 200 OK", "Content-Type: application/json", f"Content-Length: {len(body)}",
                        "Cache-Control: no-cache", "Vary: Accept-Encoding", "Access-Control-Allow-Origin: *",
                        "Connection: close"] + (["Content-Encoding: gzip"] if gz else [])
                writer.write(("\r\n".join(head) + "\r\n\r\n").encode())
                if method != 'HEAD':
                    writer.write(body)
                await writer.drain()
                return
            elif path.startswith('/who'):
                # who is online, for the web client's who window (the `who` command's list)
                query = parse_qs(urlparse(path).query)
                player = self._authed(query)
                if not player:
                    await self._http_response(writer, 404, 'Not Found', 'Player not found')
                    return
                group = getattr(player, 'group', None)
                mates = {getattr(m, 'name', '') for m in (getattr(group, 'members', None) or [])} if group else set()
                from datetime import datetime
                classes = getattr(player.config, 'CLASSES', {}) or {}
                out = []
                for p in list(self.world.players.values()):
                    conn = getattr(p, 'connection', None)
                    last = getattr(conn, 'last_input', None)
                    idle = int((datetime.now() - last).total_seconds() // 60) if last else 0
                    room = getattr(p, 'room', None)
                    out.append({
                        'name': p.name, 'level': getattr(p, 'level', 1),
                        'cls': (classes.get(p.char_class, {}) or {}).get('name', p.char_class),
                        'title': getattr(p, 'title', '') or '', 'guild': getattr(p, 'guild', None) or '',
                        'zone': room.zone.name if room is not None and getattr(room, 'zone', None) else '',
                        'idle_min': idle if idle >= 5 else 0,
                        'group': p is not player and p.name in mates,
                    })
                await self._http_response(writer, 200, 'OK', json.dumps({'players': out}), content_type='application/json')
            elif path.startswith('/help'):
                # the game's help topics, for the web client's help window: the list (no query) or
                # one topic's text (?topic=); the same words as the MUD's `help`
                query = parse_qs(urlparse(path).query)
                from help_data import HELP_TOPICS, get_help_text
                topic = (query.get('topic') or [''])[0].strip().lower()
                if topic:
                    text = re.sub(r'\x1b\[[0-9;]*m', '', get_help_text(topic) or '')
                    body = json.dumps({'name': topic, 'text': text})
                else:
                    body = json.dumps({'topics': [{
                        'name': name, 'category': t.get('category', ''),
                        'summary': (str(t.get('description', '')).strip().split('\n')[0])[:110],
                    } for name, t in HELP_TOPICS.items()]})
                await self._http_response(writer, 200, 'OK', body, content_type='application/json')
            elif path.startswith('/explored'):
                # the rooms this player has explored (the world map draws only those)
                query = parse_qs(urlparse(path).query)
                player = self._authed(query)
                if not player:
                    await self._http_response(writer, 404, 'Not Found', 'Player not found')
                    return
                rooms = sorted(set(getattr(player, 'explored_rooms', set()) or set()) | {getattr(getattr(player, 'room', None), 'vnum', None)} - {None})
                await self._http_response(writer, 200, 'OK', json.dumps({'rooms': rooms}), content_type='application/json')
            elif path.startswith('/atlas'):
                # the complete world atlas (static; cached server-side)
                from map_system import build_atlas
                body = json.dumps(build_atlas(self.world))
                await self._http_response(writer, 200, 'OK', body, content_type='application/json')
            elif path.startswith('/shop'):
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                kw = ((query.get('keeper') or [''])[0]).strip().lower()
                player = self._authed(query)
                from shops import ShopManager
                keeper = None
                if player and player.room:
                    for ch in player.room.characters:
                        if ShopManager.is_shopkeeper(ch) and (not kw or kw in (getattr(ch, 'name', '') or '').lower()):
                            keeper = ch
                            break
                shop = ShopManager.get_shop(keeper) if keeper else None
                if not keeper or not shop:
                    body = json.dumps({'found': False})
                else:
                    from map_system import item_info
                    buy = []
                    for it in shop.get_sellable_items()[:40]:
                        d = item_info(it)
                        d['price'] = shop.get_sell_price(it, player)
                        buy.append(d)
                    sell = []
                    for it in (getattr(player, 'inventory', None) or [])[:40]:
                        d = item_info(it)
                        d['price'] = shop.get_buy_price(it, player)
                        d['will_buy'] = shop.will_buy(it)
                        sell.append(d)
                    body = json.dumps({'found': True, 'keeper': keeper.name,
                                       'gold': getattr(player, 'gold', 0),
                                       'buy': buy, 'sell': sell})
                await self._http_response(writer, 200, 'OK', body, content_type='application/json')
            elif path.startswith('/training'):
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                player = self._authed(query)
                if not player:
                    body = json.dumps({'found': False})
                else:
                    from config import Config as _Cfg
                    cd = _Cfg().CLASSES.get(str(getattr(player, 'char_class', '')).lower(), {})
                    body = json.dumps({
                        'found': True,
                        'practices': getattr(player, 'practices', 0),
                        'gold': getattr(player, 'gold', 0),
                        'level': getattr(player, 'level', 1),
                        'skills': [{'id': sk, 'prof': player.skills.get(sk, 0), 'known': sk in player.skills}
                                   for sk in cd.get('skills', [])],
                        'spells': [{'id': sp, 'prof': player.spells.get(sp, 0), 'known': sp in player.spells}
                                   for sp in cd.get('spells', [])],
                    })
                await self._http_response(writer, 200, 'OK', body, content_type='application/json')
            elif path.startswith('/container'):
                # peek inside a container on the ground or in inventory
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                target = ((query.get('target') or [''])[0]).strip().lower()
                player = self._authed(query)
                if not player or not target or not player.room:
                    await self._http_response(writer, 200, 'OK', json.dumps({'found': False}), content_type='application/json')
                    return
                from map_system import item_info
                found = None
                where = None
                for pool, wh in ((getattr(player.room, 'items', None) or [], 'room'),
                                 (getattr(player, 'inventory', None) or [], 'inv')):
                    for it in pool:
                        if getattr(it, 'item_type', '') == 'container' and target in (getattr(it, 'name', '') or '').lower():
                            found, where = it, wh
                            break
                    if found:
                        break
                if not found:
                    body = json.dumps({'found': False})
                else:
                    contents = [item_info(x) for x in (getattr(found, 'contents', None) or [])][:30]
                    body = json.dumps({'found': True, 'title': getattr(found, 'short_desc', '') or found.name,
                                       'where': where, 'closed': bool(getattr(found, 'closed', False)),
                                       'items': contents})
                await self._http_response(writer, 200, 'OK', body, content_type='application/json')
            elif path.startswith('/sprites/'):
                # Serve sprite images
                sprite_file = path.replace('/sprites/', '')
                sprite_path = os.path.join(os.path.dirname(__file__), 'web_isometric', 'sprites', sprite_file)
                try:
                    with open(sprite_path, 'rb') as f:
                        data = f.read()
                    ext = sprite_file.rsplit('.', 1)[-1].lower()
                    ct = {'png': 'image/png', 'jpg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png')
                    writer.write(f"HTTP/1.1 200 OK\r\nContent-Type: {ct}\r\nContent-Length: {len(data)}\r\nConnection: close\r\nAccess-Control-Allow-Origin: *\r\n\r\n".encode())
                    writer.write(data)
                    await writer.drain()
                    return
                except FileNotFoundError:
                    await self._http_response(writer, 404, 'Not Found', 'Sprite not found')
            elif path.startswith(('/platformer', '/2d', '/iso')):
                # the 2D clients (platformer, top-down, isometric) are retired: /play is the web client
                writer.write(b"HTTP/1.1 302 Found\r\nLocation: /play\r\nContent-Length: 0\r\n"
                             b"Cache-Control: no-cache\r\nConnection: close\r\n\r\n")
                await writer.drain()
                return
            elif path.startswith('/talents'):
                # talent trees + the player's progression, for the talent UI
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                player = self._authed(query)
                if not player:
                    await self._http_response(writer, 404, 'Not Found', 'Player not found')
                    return
                try:
                    from talents import CLASS_TALENT_TREES, TalentManager
                    cls_name = getattr(player, 'char_class', '').lower()
                    learned = dict(getattr(player, 'talents', {}) or {})
                    trees = CLASS_TALENT_TREES.get(cls_name, [])
                    data = {
                        'class': cls_name,
                        'points_total': TalentManager.get_talent_points(player),
                        'points_available': TalentManager.get_available_points(player),
                        'has_trees': bool(trees),
                        'trees': [{
                            'name': t['name'],
                            'description': t.get('description', ''),
                            'icon': t.get('icon', ''),
                            'points': TalentManager.get_tree_points(player, t['name']),
                            'talents': [{
                                'id': ta.id, 'name': ta.name, 'description': ta.description,
                                'tier': ta.tier, 'max_rank': ta.max_rank,
                                'requires': list(getattr(ta, 'requires', []) or []),
                                'rank': int(learned.get(ta.id, 0)),
                            } for ta in t['talents'].values()],
                        } for t in trees],
                    }
                    await self._http_response(writer, 200, 'OK', json.dumps(data), content_type='application/json')
                except Exception as e:
                    logger.error(f"/talents error: {e}")
                    await self._http_response(writer, 500, 'Error', 'talent data unavailable')
            elif path.startswith('/almanac'):
                # progression hub: daily streak, achievements, titles, collections
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                player = self._authed(query)
                if not player:
                    await self._http_response(writer, 404, 'Not Found', 'Player not found')
                    return
                try:
                    from datetime import datetime, date
                    from achievements import ACHIEVEMENTS
                    from daily import DAILY_REWARDS, MILESTONE_REWARDS
                    # ---- daily ----
                    daily = dict(getattr(player, 'daily', {}) or {})
                    streak = int(daily.get('streak', 0) or 0)
                    total_days = int(daily.get('total_days', 0) or 0)
                    claimed_today = False
                    lc = daily.get('last_claim')
                    if lc:
                        try:
                            claimed_today = datetime.fromisoformat(lc).date() == date.today()
                        except Exception:
                            pass
                    streak_day = ((max(1, streak) - 1) % 7) + 1
                    next_day = (streak_day % 7) + 1
                    ms_claimed = daily.get('milestones_claimed', []) or []
                    next_ms = None
                    for md in sorted(MILESTONE_REWARDS):
                        if md not in ms_claimed and total_days < md:
                            next_ms = {'day': md, 'name': MILESTONE_REWARDS[md].get('item_name', '')}
                            break
                    # ---- achievements ----
                    unlocked = dict(getattr(player, 'achievements', {}) or {})
                    prog = dict(getattr(player, 'achievement_progress', {}) or {})
                    ach_list = []
                    for aid, a in ACHIEVEMENTS.items():
                        is_un = aid in unlocked
                        if a.hidden and not is_un:
                            continue
                        cur = int(prog.get(a.progress_key, 0)) if a.progress_key else 0
                        ach_list.append({
                            'id': aid, 'name': a.name, 'description': a.description,
                            'category': a.category, 'icon': a.icon, 'points': a.points,
                            'target': a.target, 'progress': min(cur, a.target) if a.target else 0,
                            'unlocked': is_un, 'reward_title': a.reward_title,
                            'reward_gold': a.reward_gold, 'reward_xp': a.reward_xp,
                        })
                    points = sum(int(x.get('points', 0)) for x in unlocked.values())
                    max_points = sum(a.points for a in ACHIEVEMENTS.values())
                    # ---- titles ----
                    titles = list(getattr(player, 'available_titles', []) or [])
                    # ---- collections ----
                    colls = []
                    try:
                        from collection_system import COLLECTION_SETS
                        cprog = dict(getattr(player, 'collection_progress', {}) or {})
                        for cname, cset in COLLECTION_SETS.items():
                            have = cprog.get(cname, []) or []
                            items = cset.get('items', [])
                            colls.append({
                                'name': cname, 'description': cset.get('description', ''),
                                'have': len(have), 'total': len(items),
                                'reward': cset.get('reward', {}),
                            })
                    except Exception:
                        pass
                    # ---- gear sets ----
                    gear_sets = []
                    try:
                        # every set the hero owns a piece of, named or a zone's, with each tier
                        import sets as _sets
                        import procs as _procs
                        def _sid(it):
                            v = getattr(it, 'set_id', None)
                            return int(v) if isinstance(v, str) and v.isdigit() else v
                        worn_items = [it for it in (getattr(player, 'equipment', {}) or {}).values() if it]
                        owned_items = worn_items + list(getattr(player, 'inventory', []) or [])
                        owned_ids = []
                        for it in owned_items:
                            sid = _sid(it)
                            if sid not in (None, '') and sid not in owned_ids:
                                owned_ids.append(sid)
                        for sid in owned_ids:
                            worn = sum(1 for it in worn_items if _sid(it) == sid)
                            owned = len({getattr(it, 'vnum', id(it)) for it in owned_items if _sid(it) == sid})
                            tiers = []
                            for need, stats, where, plist in _sets.set_tiers(sid):
                                txt = '; '.join(([_sets.describe_bonus(stats)] if stats else []) + [_procs.describe(p) for p in plist])
                                if where == 'in_zone':
                                    txt += ' (in its zone)'
                                tiers.append({'need': need, 'active': worn >= need, 'text': txt})
                            total = len(_sets.NAMED_SETS[sid]['pieces']) if sid in _sets.NAMED_SETS else _sets.SET_CAPS.get(sid, 0)
                            gear_sets.append({'name': _sets.set_name(sid), 'worn': worn, 'owned': owned,
                                              'total': total, 'tiers': tiers})
                    except Exception:
                        logger.exception('almanac gear sets')
                    data = {
                        'daily': {
                            'streak': streak, 'total_days': total_days,
                            'claimed_today': claimed_today,
                            'streak_day': streak_day,
                            'today': DAILY_REWARDS.get(streak_day, DAILY_REWARDS[1]),
                            'next': DAILY_REWARDS.get(next_day, DAILY_REWARDS[1]),
                            'next_milestone': next_ms,
                        },
                        'gear_sets': gear_sets,
                        'achievements': {
                            'points': points, 'max_points': max_points,
                            'unlocked': len(unlocked), 'total': len(ACHIEVEMENTS),
                            'list': ach_list,
                        },
                        'titles': {'current': getattr(player, 'title', 'the Adventurer'), 'available': titles},
                        'collections': colls,
                    }
                    await self._http_response(writer, 200, 'OK', json.dumps(data), content_type='application/json')
                except Exception as e:
                    logger.error(f"/almanac error: {e}")
                    await self._http_response(writer, 500, 'Error', 'almanac data unavailable')
            elif path.startswith('/regen'):
                # recovery rates by position (tick = 60s, so these are /min),
                # active modifiers, and rent availability — for the rest UI
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                player = self._authed(query)
                if not player:
                    await self._http_response(writer, 404, 'Not Found', 'Player not found')
                    return
                try:
                    from regeneration import RegenerationCalculator as RC
                    from config import Config as _Cfg
                    cfg = _Cfg()
                    gt = getattr(self.world, 'game_time', None)
                    room = getattr(player, 'room', None)
                    weather = None
                    if room and getattr(room, 'zone', None) and hasattr(room.zone, 'weather'):
                        weather = room.zone.weather
                    POS = {'standing': 1.0, 'sitting': 1.25, 'resting': 1.5, 'sleeping': 2.0}
                    rates = {}
                    for pos, mult in POS.items():
                        rates[pos] = {
                            'hp': round(RC.calculate_hp_regen(player, cfg.HP_REGEN_RATE, mult, gt, weather)),
                            'mana': round(RC.calculate_mana_regen(player, cfg.MANA_REGEN_RATE, mult, gt, weather)),
                            'move': round(RC.calculate_move_regen(player, cfg.MOVE_REGEN_RATE, mult, gt, weather)),
                        }
                    # active modifiers
                    mods = []
                    hour = getattr(gt, 'hour', 12) if gt else 12
                    if 0 <= hour < 6:
                        mods.append({'icon': '🌙', 'label': 'Night +25% (rest/sleep)'})
                    aff = set(getattr(player, 'affect_flags', set()) or set())
                    if 'regenerating' in aff:
                        mods.append({'icon': '✨', 'label': 'Regeneration x2'})
                    if 'poison' in aff or 'poisoned' in aff:
                        mods.append({'icon': '☠', 'label': 'Poisoned −50%'})
                    if 'disease' in aff or 'diseased' in aff:
                        mods.append({'icon': '🤢', 'label': 'Diseased −75%'})
                    sky = getattr(weather, 'sky_condition', None) if weather else None
                    if sky in ('rainy', 'stormy', 'snowy'):
                        mods.append({'icon': '☔', 'label': f'{sky.title()} weather'})
                    # rent availability
                    at_inn = False
                    if room and hasattr(room, 'characters'):
                        for ch in room.characters:
                            if getattr(ch, 'special', None) == 'innkeeper':
                                at_inn = True
                                break
                    rent_cost = None
                    if at_inn:
                        try:
                            from commands import CommandHandler
                            rent_cost = CommandHandler.calc_total_rent(player)
                        except Exception:
                            rent_cost = max(20, getattr(player, 'level', 1) * 5)
                    data = {
                        'position': getattr(player, 'position', 'standing'),
                        'rates': rates, 'modifiers': mods,
                        'at_inn': at_inn, 'rent_cost': rent_cost,
                        'gold': int(getattr(player, 'gold', 0) or 0),
                        'in_combat': bool(getattr(player, 'fighting', None)),
                    }
                    await self._http_response(writer, 200, 'OK', json.dumps(data), content_type='application/json')
                except Exception as e:
                    logger.error(f"/regen error: {e}")
                    await self._http_response(writer, 500, 'Error', 'regen data unavailable')
            elif path.startswith('/travel'):
                # discovered fast-travel waypoints + gold/cooldown state
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                player = self._authed(query)
                if not player:
                    await self._http_response(writer, 404, 'Not Found', 'Player not found')
                    return
                try:
                    import time as _t
                    from travel import WAYPOINTS
                    disc = set(getattr(player, 'discovered_waypoints', set()) or set())
                    here = getattr(getattr(player, 'room', None), 'vnum', None)
                    wps = []
                    for key, info in WAYPOINTS.items():
                        if key not in disc:
                            continue
                        wps.append({
                            'key': key, 'name': info.get('name', key),
                            'vnum': info.get('vnum'), 'cost': info.get('cost', 0),
                            'here': info.get('vnum') == here,
                        })
                    cd_until = getattr(player, 'travel_cooldown_until', 0) or 0
                    cd = max(0, int(cd_until - _t.time()))
                    data = {
                        'waypoints': sorted(wps, key=lambda w: w['cost']),
                        'gold': int(getattr(player, 'gold', 0) or 0),
                        'cooldown': cd,
                        'total': len(WAYPOINTS), 'discovered': len(disc),
                    }
                    await self._http_response(writer, 200, 'OK', json.dumps(data), content_type='application/json')
                except Exception as e:
                    logger.error(f"/travel error: {e}")
                    await self._http_response(writer, 500, 'Error', 'travel data unavailable')
            elif path.startswith('/abilities'):
                # static costs for the player's known spells, for hotbar clarity
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                player = self._authed(query)
                if not player:
                    await self._http_response(writer, 404, 'Not Found', 'Player not found')
                    return
                try:
                    from spells import SPELLS
                    known = getattr(player, 'spells', None) or {}
                    abilities = {}
                    for key, spell in SPELLS.items():
                        if key not in known:
                            continue
                        abilities[key] = {
                            'name': spell.get('name', key),
                            'mana_cost': int(spell.get('mana_cost', 0) or 0),
                            'cooldown': int(spell.get('cooldown', 0) or 0),
                            'level': int(spell.get('level_required', 0) or 0),
                        }
                    data = {'abilities': abilities, 'resource': 'mana'}
                    await self._http_response(writer, 200, 'OK', json.dumps(data), content_type='application/json')
                except Exception as e:
                    logger.error(f"/abilities error: {e}")
                    await self._http_response(writer, 500, 'Error', 'ability data unavailable')
            elif path.startswith('/legend'):
                # prestige specialization + server leaderboards
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                player = self._authed(query)
                if not player:
                    await self._http_response(writer, 404, 'Not Found', 'Player not found')
                    return
                try:
                    from prestige import PRESTIGE_CLASSES
                    base = str(getattr(player, 'char_class', '') or '').lower()
                    current = getattr(player, 'prestige_class', None)
                    options = []
                    for key, pc in PRESTIGE_CLASSES.items():
                        if pc.get('base_class') != base:
                            continue
                        options.append({
                            'key': key, 'name': pc.get('name', key), 'theme': pc.get('theme', ''),
                            'description': pc.get('description', ''),
                            'abilities': [{'name': a.get('name', k), 'description': a.get('description', ''),
                                           'type': a.get('type', '')} for k, a in pc.get('abilities', {}).items()],
                        })
                    prestige = {
                        'base_class': base, 'current': current,
                        'current_name': PRESTIGE_CLASSES.get(current, {}).get('name') if current else None,
                        'eligible': player.level >= 50 and not current,
                        'level': player.level, 'options': options,
                    }
                    # leaderboards from the real player directory
                    import glob
                    pdir = self.config.PLAYER_DIR if hasattr(self, 'config') else None
                    if not pdir:
                        from config import Config
                        pdir = Config().PLAYER_DIR
                    rows = []
                    for pf in glob.glob(os.path.join(pdir, '*.json')):
                        try:
                            with open(pf) as f:
                                d = json.load(f)
                            st = d.get('stats', {}) or {}
                            rows.append({
                                'name': d.get('name', os.path.basename(pf)[:-5]).capitalize(),
                                'level': d.get('level', 1),
                                'kills': st.get('kills', d.get('kills', 0)) or 0,
                                'gold': (d.get('gold', 0) or 0) + (d.get('bank_gold', 0) or 0),
                                'achievements': len(d.get('achievements', {}) or {}),
                                'quests': len(d.get('quests_completed', []) or []),
                            })
                        except Exception:
                            continue
                    boards = {}
                    me = (getattr(player, 'name', '') or '').capitalize()
                    for cat in ('level', 'kills', 'gold', 'achievements', 'quests'):
                        ranked = sorted(rows, key=lambda r: r.get(cat, 0), reverse=True)
                        top = [{'name': r['name'], 'value': r.get(cat, 0)} for r in ranked[:10]]
                        my_rank = next((i + 1 for i, r in enumerate(ranked) if r['name'] == me), None)
                        boards[cat] = {'top': top, 'my_rank': my_rank, 'total': len(ranked)}
                    data = {'prestige': prestige, 'leaderboards': boards}
                    await self._http_response(writer, 200, 'OK', json.dumps(data), content_type='application/json')
                except Exception as e:
                    logger.error(f"/legend error: {e}")
                    await self._http_response(writer, 500, 'Error', 'legend data unavailable')
            elif path.startswith('/stable'):
                # pets, hired companions, owned + purchasable mounts
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                player = self._authed(query)
                if not player:
                    await self._http_response(writer, 404, 'Not Found', 'Player not found')
                    return
                try:
                    pets = []
                    try:
                        from pets import PetManager
                        for p in PetManager.get_player_pets(player) or []:
                            pets.append({
                                'name': getattr(p, 'name', 'pet'), 'level': getattr(p, 'level', 1),
                                'hp': getattr(p, 'hp', 0), 'maxHp': getattr(p, 'max_hp', 1),
                                'loyalty': getattr(p, 'loyalty', 100),
                                'type': getattr(p, 'pet_type', 'summon'),
                                'abilities': list(getattr(p, 'special_abilities', []) or []),
                            })
                    except Exception:
                        pass
                    comps = []
                    try:
                        from companions import CompanionManager
                        for cm in CompanionManager.get_player_companions(player) or []:
                            comps.append({
                                'name': getattr(cm, 'name', 'companion'), 'level': getattr(cm, 'level', 1),
                                'hp': getattr(cm, 'hp', 0), 'maxHp': getattr(cm, 'max_hp', 1),
                                'role': getattr(cm, 'companion_type', 'Fighter'),
                            })
                    except Exception:
                        pass
                    from mounts import MountManager
                    cur = getattr(player, 'mount', None)
                    cur_key = getattr(cur, 'key', None) if cur else None
                    owned = []
                    for m in getattr(player, 'owned_mounts', []) or []:
                        key = m if isinstance(m, str) else m.get('key', '')
                        tpl = MountManager.get_mount_template(key) or {}
                        owned.append({
                            'key': key, 'name': tpl.get('name', key),
                            'description': tpl.get('description', ''),
                            'speed_bonus': tpl.get('speed_bonus', 0),
                            'travel': int(round(tpl.get('travel', 0.3) * 100)),      # +35% speed
                            'can_fly': bool(tpl.get('can_fly')), 'combat_ok': bool(tpl.get('combat_ok')),
                            'loyalty': (m.get('loyalty', 100) if isinstance(m, dict) else 100),
                            'active': key == cur_key,
                        })
                    room = getattr(player, 'room', None)
                    at_stable = False
                    if room:
                        if getattr(room, 'sector_type', '') == 'city':
                            at_stable = True
                        for ch in getattr(room, 'characters', []) or []:
                            if getattr(ch, 'special', None) == 'stable_master':
                                at_stable = True
                                break
                    purchasable = []
                    owned_keys = {o['key'] for o in owned}
                    for k, v in MountManager.list_purchasable_mounts().items():
                        if k in owned_keys:
                            continue
                        purchasable.append({
                            'key': k, 'name': v.get('name', k), 'cost': v.get('cost', 0),
                            'description': v.get('description', ''),
                            'speed_bonus': v.get('speed_bonus', 0), 'can_fly': bool(v.get('can_fly')),
                            'travel': int(round(v.get('travel', 0.3) * 100)),
                            'afford': getattr(player, 'gold', 0) >= v.get('cost', 0),
                        })
                    data = {
                        'pets': pets, 'companions': comps,
                        'mounts': {'owned': owned, 'current': cur_key, 'at_stable': at_stable,
                                   'purchasable': purchasable, 'gold': getattr(player, 'gold', 0)},
                    }
                    await self._http_response(writer, 200, 'OK', json.dumps(data), content_type='application/json')
                except Exception as e:
                    logger.error(f"/stable error: {e}")
                    await self._http_response(writer, 500, 'Error', 'stable data unavailable')
            elif path.startswith('/services'):
                # mail inbox, bank balance, storage locker
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                player = self._authed(query)
                if not player:
                    await self._http_response(writer, 404, 'Not Found', 'Player not found')
                    return
                try:
                    from mail_system import MailManager
                    msgs = MailManager.get_all_mail(player.name) or []
                    mail = [{
                        'id': m.get('msg_id', i), 'sender': m.get('sender', '?'),
                        'ts': (m.get('timestamp', '') or '')[:16].replace('T', ' '),
                        'body': m.get('body', ''), 'read': bool(m.get('read', False)),
                    } for i, m in enumerate(msgs)]
                    room = getattr(player, 'room', None)
                    flags = getattr(room, 'flags', set()) or set()
                    at_bank = 'bank' in flags
                    at_inn = False
                    if room and hasattr(room, 'characters'):
                        for ch in room.characters:
                            if getattr(ch, 'special', None) == 'innkeeper':
                                at_inn = True
                                break
                    storage = [{'name': getattr(it, 'short_desc', None) or getattr(it, 'name', 'an item')}
                               for it in (getattr(player, 'storage', None) or [])]
                    sloc = None
                    if getattr(player, 'storage_location', None):
                        sr = self.world.get_room(player.storage_location)
                        sloc = getattr(sr, 'name', None) if sr else None
                    data = {
                        'mail': {'unread': sum(1 for m in mail if not m['read']), 'messages': mail},
                        'bank': {'balance': int(getattr(player, 'bank_gold', 0) or 0),
                                 'on_hand': int(getattr(player, 'gold', 0) or 0), 'at_bank': at_bank},
                        'storage': {'items': storage, 'location': sloc, 'at_inn': at_inn},
                    }
                    await self._http_response(writer, 200, 'OK', json.dumps(data), content_type='application/json')
                except Exception as e:
                    logger.error(f"/services error: {e}")
                    await self._http_response(writer, 500, 'Error', 'services data unavailable')
            elif path.startswith('/quests'):
                # quest journal: active quests w/ progress + quests offered by
                # NPCs in the current room (the contextual "board")
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                player = self._authed(query)
                if not player:
                    await self._http_response(writer, 404, 'Not Found', 'Player not found')
                    return
                try:
                    from quests import QuestManager, QUEST_DEFINITIONS
                    from datetime import datetime
                    active = []
                    try:
                        import marquee
                        mq_entry = marquee.journal_entry(player)
                        if mq_entry:
                            active.append(mq_entry)
                    except Exception as e:
                        logger.debug(f"/quests marquee: {e}")
                    # (in /play's words, not a telnet's: quest_guide.web_line)
                    from quest_guide import web_line
                    for q in getattr(player, 'active_quests', []) or []:
                        objs = [{
                            'description': web_line(o.description),
                            'current': int(getattr(o, 'current', 0)),
                            'required': int(getattr(o, 'required', 1)),
                            'completed': bool(getattr(o, 'completed', False)),
                            'type': getattr(o, 'type', ''),
                            'target': getattr(o, 'target', None),
                        } for o in q.objectives]
                        remaining = None
                        if getattr(q, 'time_limit', None):
                            elapsed = (datetime.now() - q.started_at).total_seconds() / 60
                            remaining = max(0, int(q.time_limit - elapsed))
                        active.append({
                            'id': q.quest_id, 'name': q.name, 'description': web_line(q.description),
                            'objectives': objs, 'rewards': q.rewards,
                            'complete': q.is_complete(), 'remaining_min': remaining,
                            'tracked': __import__('quest_guide').tracked(player, q),
                        })
                    # available from NPCs present in the room
                    givers = []
                    room = getattr(player, 'room', None)
                    seen = set()
                    if room and hasattr(room, 'characters'):
                        for ent in room.characters:
                            vnum = getattr(ent, 'vnum', None)
                            if vnum is None or hasattr(ent, 'account_name') or vnum in seen:
                                continue
                            seen.add(vnum)
                            qids = QuestManager.get_available_quests(player, vnum)
                            if not qids:
                                continue
                            offers = []
                            for qid in qids:
                                qd = QUEST_DEFINITIONS.get(qid, {})
                                offers.append({
                                    'id': qid, 'name': qd.get('name', qid),
                                    'description': web_line(qd.get('description', '')),
                                    'level_min': qd.get('level_min', 1),
                                    'level_max': qd.get('level_max', 99),
                                    'rewards': qd.get('rewards', {}),
                                    'repeatable': bool(qd.get('repeatable', False)),
                                    'daily': bool(qd.get('daily', False)),
                                })
                            givers.append({'name': getattr(ent, 'name', 'Someone'), 'offers': offers})
                    data = {'active': active, 'givers': givers,
                            'completed': len(getattr(player, 'quests_completed', []) or [])}
                    await self._http_response(writer, 200, 'OK', json.dumps(data), content_type='application/json')
                except Exception as e:
                    logger.error(f"/quests error: {e}")
                    await self._http_response(writer, 500, 'Error', 'quest data unavailable')
            elif path.startswith('/doctrine'):
                # warrior doctrine + ability-evolution progression
                parsed = urlparse(path)
                query = parse_qs(parsed.query)
                player_name = (query.get('player') or [''])[0]
                player = self._authed(query)
                if not player:
                    await self._http_response(writer, 404, 'Not Found', 'Player not found')
                    return
                try:
                    from warrior_abilities import DOCTRINES, EVOLUTION_TREE
                    usage = dict(getattr(player, 'ability_usage', {}) or {})
                    evolved = dict(getattr(player, 'ability_evolutions', {}) or {})
                    data = {
                        'doctrine': getattr(player, 'war_doctrine', None),
                        'momentum': getattr(player, 'momentum', 0),
                        'doctrines': {k: {
                            'name': v.get('name', k), 'description': v.get('description', ''),
                            'flavor': v.get('flavor', ''), 'bonus': v.get('momentum_bonus', ''),
                        } for k, v in DOCTRINES.items()},
                        'abilities': [{
                            'ability': ab,
                            'usage': int(usage.get(ab, 0)),
                            'evolved': evolved.get(ab),
                            'thresholds': {str(th): {doc: list(pair) for doc, pair in paths.items()}
                                           for th, paths in tree.items()},
                        } for ab, tree in EVOLUTION_TREE.items()],
                    }
                    await self._http_response(writer, 200, 'OK', json.dumps(data), content_type='application/json')
                except Exception as e:
                    logger.error(f"/doctrine error: {e}")
                    await self._http_response(writer, 500, 'Error', 'doctrine data unavailable')
            elif path.startswith('/art/'):
                # Serve the CC0 art packs (png/json only, no traversal); see docs/art/SOURCES.md
                art_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), 'web_isometric', 'art'))
                art_file = path.split('?', 1)[0].replace('/art/', '', 1)
                art_path = os.path.realpath(os.path.join(art_dir, art_file))
                ext = art_file.rsplit('.', 1)[-1].lower() if '.' in art_file else ''
                if not art_path.startswith(art_dir + os.sep) or ext not in ('png', 'json'):
                    await self._http_response(writer, 404, 'Not Found', 'Not found')
                    return
                try:
                    with open(art_path, 'rb') as f:
                        data = f.read()
                    ct = 'image/png' if ext == 'png' else 'application/json'
                    writer.write((f"HTTP/1.1 200 OK\r\nContent-Type: {ct}\r\nContent-Length: {len(data)}\r\n"
                                  f"Cache-Control: max-age=3600\r\nConnection: close\r\nAccess-Control-Allow-Origin: *\r\n\r\n").encode())
                    writer.write(data)
                    await writer.drain()
                    return
                except FileNotFoundError:
                    await self._http_response(writer, 404, 'Not Found', 'Art not found')
            elif path.startswith(('/v/', '/world3d/', '/shared/', '/vendor/', '/art3d/', '/fonts/')):
                hit = static_3d(path)
                if not hit:
                    await self._http_response(writer, 404, 'Not Found', 'Not found')
                    return
                full, ext, immutable = hit
                data, enc = static_bytes(full, ext, 'gzip' in headers.get('accept-encoding', ''))
                status, extra = "HTTP/1.1 200 OK", []
                if ext in _AUDIO_3D:
                    extra.append("Accept-Ranges: bytes")
                    rng = byte_range(headers.get('range'), len(data)) if 'range' in headers else None
                    if 'range' in headers and rng is None:
                        writer.write((f"HTTP/1.1 416 Range Not Satisfiable\r\nContent-Range: bytes */{len(data)}\r\n"
                                      "Content-Length: 0\r\nConnection: close\r\n\r\n").encode())
                        await writer.drain()
                        return
                    if rng:
                        status = "HTTP/1.1 206 Partial Content"
                        extra.append(f"Content-Range: bytes {rng[0]}-{rng[1]}/{len(data)}")
                        data = data[rng[0]:rng[1] + 1]
                head = [
                    status,
                    f"Content-Type: {_CT_3D[ext]}",
                    f"Content-Length: {len(data)}",
                ] + extra + [
                    "Cache-Control: " + ("public, max-age=31536000, immutable" if immutable else "no-cache"),
                    "Vary: Accept-Encoding",
                    "Access-Control-Allow-Origin: *",
                    "Connection: close",
                ]
                if enc:
                    head.append(f"Content-Encoding: {enc}")
                writer.write(("\r\n".join(head) + "\r\n\r\n").encode())
                if method != 'HEAD':
                    writer.write(data)
                await writer.drain()
                return
            elif path.split('?', 1)[0] in ('/play', '/play/'):
                # the 3D client (docs/REBUILD_PLAN.md, engine section)
                try:
                    with open(os.path.join(_WEB_DIR, 'world3d', 'play.html'), 'r', encoding='utf-8') as f:
                        page = f.read().replace('{{V}}', asset_version())
                    await self._http_response(writer, 200, 'OK', page, content_type='text/html')
                except FileNotFoundError:
                    await self._http_response(writer, 404, 'Not Found', '3D client not found')
            else:
                await self._http_response(writer, 200, 'OK', self._html(), content_type='text/html')

        except Exception as e:
            logger.error(f"Web map client error: {e}")
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def _http_response(self, writer, status_code, status_text, body, content_type='text/plain'):
        data = body.encode('utf-8')
        headers = [
            f"HTTP/1.1 {status_code} {status_text}",
            f"Content-Type: {content_type}; charset=utf-8",
            f"Content-Length: {len(data)}",
            "Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
            "Pragma: no-cache",
            "Connection: close",
            "Access-Control-Allow-Origin: *",
            "Access-Control-Allow-Methods: GET, POST, OPTIONS",
            "Access-Control-Allow-Headers: Content-Type",
            "X-Frame-Options: ALLOWALL",
            "",
            "",
        ]
        writer.write("\r\n".join(headers).encode('utf-8') + data)
        await writer.drain()

    async def _handle_websocket(self, reader, writer, headers):
        key = headers.get('sec-websocket-key')
        if not key:
            writer.close()
            return
        accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        )
        writer.write(response.encode('utf-8'))
        await writer.drain()

        client = WebMapClient(reader, writer)
        self.clients.add(client)

        try:
            while True:
                message = await self._ws_read(reader)
                if message is None:
                    logger.info(f"WebSocket message is None, closing connection for client")
                    break
                if message == '':
                    # Control frame (ping/pong), continue waiting
                    continue
                try:
                    payload = json.loads(message)
                except Exception as e:
                    logger.debug(f"Failed to parse WebSocket message: {e}")
                    continue

                if payload.get('type') in ('pos', 'mobpos'):
                    # combat v2 (combat_range.py): the 3D client says where its hero stands
                    # and where it placed the creatures of its room; only for its own player
                    player = self.world.players.get((client.player_name or '').lower())
                    if player and player.room and payload.get('vnum') == player.room.vnum:
                        from combat_range import set_pos, mob_seed
                        if payload.get('type') == 'pos':
                            try:
                                set_pos(player, float(payload.get('x')), float(payload.get('z')))
                                await self.relay_presence(player)
                            except (TypeError, ValueError):
                                pass
                        else:
                            mob_seed(player.room, payload.get('mobs') or [])
                    continue
                if payload.get('type') == 'subscribe':
                    # only with the secret the player's own connection received (MAPSYNC)
                    player = self._player_by_token(payload.get('player'), payload.get('token'))
                    client.mode = payload.get('mode', 'full')
                    client.player_name = player.name if player else None
                    client.token = payload.get('token') if player else None
                    client.combat = 'action' if player and payload.get('combat') == 'action' else None
                    logger.info(f"WebSocket subscribe: player='{payload.get('player')}' mode='{client.mode}' ok={bool(player)}")
                    if not player:
                        await self._ws_send(writer, json.dumps({'type': 'auth', 'ok': False}))
                    if player:
                        # Ensure current room is in explored_rooms for initial map
                        if player.room and hasattr(player, 'explored_rooms'):
                            if player.room.vnum not in player.explored_rooms:
                                player.explored_rooms.add(player.room.vnum)
                                logger.info(f"Added current room {player.room.vnum} to explored_rooms")
                        map_payload = build_map_payload(player, mode=client.mode)
                        logger.info(f"Sending initial map: {len(map_payload.get('rooms', []))} rooms")
                        await self._ws_send(writer, json.dumps(map_payload))
        finally:
            self.clients.discard(client)
            try:
                writer.close()
            except Exception:
                pass

    def _player_by_token(self, name, token):
        """The online player of that name, if the token is that player's current session
        secret (only their own connection received it, in MAPSYNC); else None."""
        p = self.world.players.get(str(name or '').lower()) if name else None
        secret = str(getattr(p, 'web_token', '') or '') if p else ''
        if p and token and secret and hmac.compare_digest(secret, str(token)):
            return p
        return None

    def _authed(self, query):
        """The player a request names (?player=), if it carries their session token (&t=)."""
        return self._player_by_token((query.get('player') or [''])[0], (query.get('t') or [''])[0])

    async def revoke(self, name, keep_token):
        """A new session for this character: clients holding an older token stop receiving."""
        for client in list(self.clients):
            if (client.player_name or '').lower() == str(name).lower() and client.token != keep_token:
                client.player_name = None
                client.token = None
                client.combat = None
                try:
                    await self._ws_send(client.writer, json.dumps({'type': 'revoked'}))
                except Exception:
                    pass

    async def _ws_read(self, reader):
        """Read a WebSocket frame. Returns message text, empty string for control frames, or None on close/error."""
        try:
            header = await reader.readexactly(2)
            if not header:
                logger.info("WebSocket: empty header received")
                return None
            b1, b2 = header[0], header[1]
            opcode = b1 & 0x0F
            masked = b2 & 0x80
            length = b2 & 0x7F
            
            logger.debug(f"WebSocket frame: opcode={opcode}, masked={masked}, length={length}")
            
            # Handle close frame
            if opcode == 0x8:
                logger.info("WebSocket close frame received from client")
                return None
            
            if length == 126:
                length = int.from_bytes(await reader.readexactly(2), 'big')
            elif length == 127:
                length = int.from_bytes(await reader.readexactly(8), 'big')
            if length > 1 << 20:
                logger.warning(f"WebSocket frame of {length} bytes refused")
                return None                     # no client of ours sends a megabyte
            
            mask = b''
            if masked:
                mask = await reader.readexactly(4)
            
            data = await reader.readexactly(length) if length > 0 else b''
            if masked and data:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            
            # Handle ping - respond with pong
            if opcode == 0x9:
                logger.debug("WebSocket ping received, sending pong")
                return ''  # Return empty string to continue loop
            
            # Handle pong - just ignore
            if opcode == 0xA:
                logger.debug("WebSocket pong received")
                return ''  # Return empty string to continue loop
            
            return data.decode('utf-8', errors='ignore')
        except asyncio.IncompleteReadError as e:
            logger.info(f"WebSocket connection closed (incomplete read): {e}")
            return None
        except (ConnectionResetError, BrokenPipeError, ConnectionError, OSError) as e:
            logger.info(f"WebSocket read error: {e}")
            return None
        except Exception as e:
            logger.warning(f"WebSocket read unexpected error: {e}")
            return None

    async def _ws_send(self, writer, text):
        """Send a WebSocket text frame. Returns True on success, False on failure."""
        try:
            payload = text.encode('utf-8')
            length = len(payload)
            if length < 126:
                header = bytes([0x81, length])
            elif length < (1 << 16):
                header = bytes([0x81, 126]) + length.to_bytes(2, 'big')
            else:
                header = bytes([0x81, 127]) + length.to_bytes(8, 'big')
            writer.write(header + payload)
            await writer.drain()
            return True
        except (ConnectionResetError, BrokenPipeError, ConnectionError, OSError) as e:
            logger.debug(f"WebSocket send failed: {e}")
            return False
        except Exception as e:
            logger.warning(f"WebSocket send unexpected error: {e}")
            return False

    def _html(self):
        return """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Misthollow Map</title>
  <link rel=\"stylesheet\" href=\"/map.css\" />
  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
  <link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap\" rel=\"stylesheet\">
</head>
<body>
  <div id=\"app\">
    <header>
      <h1>⚔️ Misthollow</h1>
      <div class=\"controls\">
        <label>Level <select id=\"zSelect\"></select></label>
        <label>Zoom <input id=\"zoom\" type=\"range\" min=\"0.3\" max=\"3\" step=\"0.1\" value=\"1\" /></label>
        <label><input id=\"iconMode\" type=\"checkbox\" checked /> Icons</label>
        <label><input id=\"fogMode\" type=\"checkbox\" checked /> Fog</label>
        <label><input id=\"zoneMode\" type=\"checkbox\" checked /> Zones</label>
        <label><input id=\"minimapToggle\" type=\"checkbox\" checked /> Minimap</label>
      </div>
      <div class=\"status-bar\">
        <span id=\"wsStatus\" class=\"status connecting\">WS: connecting</span>
        <span id=\"playerWarning\" class=\"warning hidden\">⚠️ Add ?player=Name to URL</span>
      </div>
    </header>
    <div class=\"content\">
      <canvas id=\"mapCanvas\"></canvas>
      <aside>
        <div id=\"zoneInfo\" class=\"zone-info\"></div>
        <h2>📍 Room Details</h2>
        <div id=\"roomDetails\">Click a room to see details.<br/><br/><em style=\"color:#6b7280\">Right-click to set destination and see path.</em></div>
        <div id=\"pathInfo\" class=\"path-info hidden\"></div>
        <div class=\"legend\">
          <h3>Legend</h3>
          <div class=\"legend-grid\">
            <span>🏛️ City</span><span>🏠 Indoor</span>
            <span>🌲 Forest</span><span>🌊 Water</span>
            <span>⛰️ Mountain</span><span>🕯️ Dungeon</span>
            <span>🛒 Shop</span><span>⭐ Quest</span>
            <span>👹 Boss</span><span>💀 Danger</span>
            <span>🌀 Portal</span><span></span>
          </div>
        </div>
        <div id=\"zoneFilter\" class=\"zone-filter\">
          <h3>🗺️ Zone Filter</h3>
          <div id=\"zoneFilterList\"></div>
        </div>
        <div id=\"zoneList\" class=\"zone-list\"></div>
      </aside>
    </div>
    <canvas id=\"minimap\"></canvas>
    <canvas id=\"zoneOverview\"></canvas>
    <div id=\"debugPanel\" class=\"debug-panel hidden\">
      <div><span class=\"label\">WS</span> <span id=\"debugWs\">-</span></div>
      <div><span class=\"label\">Poll</span> <span id=\"debugPoll\">-</span></div>
      <div><span class=\"label\">Payload</span> <span id=\"debugPayload\">-</span></div>
      <div><span class=\"label\">Error</span> <span id=\"debugError\">-</span></div>
    </div>
  </div>
  <script src=\"/map.js\"></script>
</body>
</html>"""

    def _css(self):
        return """
*{box-sizing:border-box}
body{margin:0;background:#0a0e14;color:#e6edf3;font-family:'Inter',system-ui,-apple-system,sans-serif}
#app{display:flex;flex-direction:column;min-height:100vh}
header{padding:14px 20px;border-bottom:1px solid rgba(255,255,255,0.08);background:linear-gradient(180deg,#12171f 0%,#0d1117 100%);display:flex;flex-wrap:wrap;align-items:center;gap:18px;backdrop-filter:blur(8px)}
header h1{margin:0;font-size:24px;font-weight:700;letter-spacing:-0.5px}
header .controls{display:flex;gap:14px;align-items:center;flex-wrap:wrap}
header label{font-size:12px;opacity:.75;font-weight:500;display:flex;align-items:center;gap:4px;cursor:pointer}
header input[type=checkbox]{width:16px;height:16px;accent-color:#6366f1;cursor:pointer}
header select,header input[type=range]{background:#1a1f2e;border:1px solid #2d3748;border-radius:6px;color:#e6edf3;padding:4px 8px;cursor:pointer;transition:border-color 0.2s,box-shadow 0.2s}
header select:hover,header input:hover{border-color:#6366f1}
header select:focus,header input:focus{outline:none;border-color:#6366f1;box-shadow:0 0 0 3px rgba(99,102,241,0.2)}
.status-bar{margin-left:auto;display:flex;gap:12px;align-items:center;font-size:11px;font-weight:500}
.status{padding:5px 12px;border-radius:999px;border:1px solid;text-transform:uppercase;letter-spacing:.6px;font-weight:600;transition:all 0.3s}
.status.connecting{color:#f0b429;border-color:#8b6b1a;background:rgba(240,180,41,0.1);animation:pulse 2s infinite}
.status.connected{color:#4ade80;border-color:#22c55e;background:rgba(74,222,128,0.1)}
.status.disconnected{color:#f87171;border-color:#ef4444;background:rgba(248,113,113,0.1)}
.status.polling{color:#60a5fa;border-color:#3b82f6;background:rgba(96,165,250,0.1)}
.warning{color:#fca5a5;background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);padding:6px 12px;border-radius:8px;font-size:12px}
.hidden{display:none}
#mapCanvas{flex:1;min-height:65vh;width:100%;background:radial-gradient(ellipse at center,#0f1419 0%,#050709 100%);border:1px solid rgba(255,255,255,0.06);border-radius:12px;cursor:grab}
#mapCanvas:active{cursor:grabbing}
#minimap{position:fixed;right:18px;bottom:18px;width:220px;height:220px;border:1px solid rgba(255,255,255,0.1);background:rgba(10,14,20,0.95);border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.5);backdrop-filter:blur(12px)}
#minimap.hidden{display:none}
.content{display:flex;gap:14px;padding:14px;flex:1}
aside{width:320px;background:linear-gradient(180deg,#12171f 0%,#0f1318 100%);border:1px solid rgba(255,255,255,0.06);padding:16px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.3);display:flex;flex-direction:column;gap:12px;max-height:calc(100vh - 120px);overflow-y:auto}
aside h2{margin:0;font-size:15px;font-weight:600;color:#a5b4fc}
aside h3{font-size:12px;color:#6b7280;margin:8px 0 6px 0;text-transform:uppercase;letter-spacing:0.5px}
.zone-info{background:linear-gradient(135deg,rgba(99,102,241,0.15) 0%,rgba(139,92,246,0.1) 100%);border:1px solid rgba(99,102,241,0.3);border-radius:10px;padding:12px;font-size:13px}
.zone-info .zone-name{font-weight:600;font-size:15px;margin-bottom:4px}
.zone-info .zone-stats{color:#8b949e;font-size:12px}
.path-info{background:linear-gradient(135deg,rgba(34,197,94,0.15) 0%,rgba(16,185,129,0.1) 100%);border:1px solid rgba(34,197,94,0.3);border-radius:10px;padding:12px;font-size:13px}
.path-info .path-title{font-weight:600;color:#4ade80;margin-bottom:4px}
.path-info .path-steps{color:#8b949e;font-size:12px}
#roomDetails{background:rgba(0,0,0,0.25);border-radius:10px;padding:14px;font-size:13px;line-height:1.7}
.legend{background:rgba(0,0,0,0.15);border-radius:10px;padding:12px}
.legend-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 12px;font-size:12px}
.legend-grid span{display:flex;align-items:center;gap:4px}
.zone-list{background:rgba(0,0,0,0.15);border-radius:10px;padding:12px}
.zone-list h3{margin-top:0}
.zone-item{display:flex;align-items:center;gap:8px;padding:6px 0;font-size:12px;border-bottom:1px solid rgba(255,255,255,0.05);cursor:pointer;transition:background 0.15s;padding:6px 8px;border-radius:6px;margin:1px 0}
.zone-item:hover{background:rgba(255,255,255,0.06)}
.zone-item.active{background:rgba(99,102,241,0.2);border:1px solid rgba(99,102,241,0.4)}
.zone-item:last-child{border-bottom:none}
.zone-dot{width:12px;height:12px;border-radius:50%;flex-shrink:0}
.zone-filter{background:rgba(0,0,0,0.15);border-radius:10px;padding:12px}
.zone-filter h3{margin-top:0}
.zone-filter-item{display:flex;align-items:center;gap:8px;padding:5px 8px;font-size:12px;cursor:pointer;border-radius:6px;transition:background 0.15s;margin:2px 0}
.zone-filter-item:hover{background:rgba(255,255,255,0.06)}
.zone-filter-item.active{background:rgba(99,102,241,0.25);border:1px solid rgba(99,102,241,0.4)}
.zone-filter-item .zf-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.zone-filter-item .zf-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.zone-filter-item .zf-count{color:#6b7280;font-size:11px}
#zoneOverview{position:fixed;left:18px;bottom:18px;width:140px;height:140px;border:1px solid rgba(255,255,255,0.1);background:rgba(10,14,20,0.95);border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,0.5);backdrop-filter:blur(12px);cursor:pointer;z-index:10}
#zoneOverview.hidden{display:none}
#tooltip{position:fixed;background:rgba(12,15,20,0.98);border:1px solid rgba(255,255,255,0.15);border-radius:12px;padding:12px 16px;font-size:13px;pointer-events:none;z-index:1000;box-shadow:0 12px 40px rgba(0,0,0,0.6);backdrop-filter:blur(16px);max-width:280px;opacity:0;transition:opacity 0.2s}
#tooltip.visible{opacity:1}
#tooltip .tt-icon{font-size:24px;margin-bottom:6px}
#tooltip .tt-name{font-weight:600;color:#e6edf3;font-size:14px;margin-bottom:6px}
#tooltip .tt-zone{color:#a5b4fc;font-size:11px;margin-bottom:6px}
#tooltip .tt-info{color:#8b949e;font-size:12px;line-height:1.5}
.debug-panel{position:fixed;left:18px;bottom:18px;background:rgba(10,14,20,0.95);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:10px 14px;font-size:11px;min-width:180px;box-shadow:0 4px 20px rgba(0,0,0,0.4);backdrop-filter:blur(12px)}
.debug-panel .label{display:inline-block;width:56px;color:#6b7280;text-transform:uppercase;letter-spacing:.4px;font-weight:500}
.debug-panel div{margin-bottom:5px}
.debug-panel div:last-child{margin-bottom:0}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.6}}
@keyframes reveal{0%{transform:scale(0);opacity:0}100%{transform:scale(1);opacity:1}}
@media(max-width:900px){header{flex-direction:column;align-items:flex-start}.status-bar{margin-left:0}.content{flex-direction:column}aside{width:100%;max-height:none}#minimap{position:static;width:100%;height:180px;margin:8px 0;border-radius:12px}}
"""

    def _js(self):
        return r"""(() => {
  const canvas = document.getElementById('mapCanvas');
  const ctx = canvas.getContext('2d');
  const minimap = document.getElementById('minimap');
  const miniCtx = minimap.getContext('2d');
  const zoneOverview = document.getElementById('zoneOverview');
  const zoCtx = zoneOverview.getContext('2d');
  const zSelect = document.getElementById('zSelect');
  const zoomControl = document.getElementById('zoom');
  const minimapToggle = document.getElementById('minimapToggle');
  const iconMode = document.getElementById('iconMode');
  const fogMode = document.getElementById('fogMode');
  const zoneMode = document.getElementById('zoneMode');
  const roomDetails = document.getElementById('roomDetails');
  const pathInfo = document.getElementById('pathInfo');
  const zoneInfo = document.getElementById('zoneInfo');
  const zoneList = document.getElementById('zoneList');
  const zoneFilterList = document.getElementById('zoneFilterList');
  const wsStatus = document.getElementById('wsStatus');
  const playerWarning = document.getElementById('playerWarning');
  const debugPanel = document.getElementById('debugPanel');
  const debugWs = document.getElementById('debugWs');
  const debugPoll = document.getElementById('debugPoll');
  const debugPayload = document.getElementById('debugPayload');
  const debugError = document.getElementById('debugError');

  // Create tooltip
  const tooltip = document.createElement('div');
  tooltip.id = 'tooltip';
  tooltip.innerHTML = '<div class="tt-icon"></div><div class="tt-name"></div><div class="tt-zone"></div><div class="tt-info"></div>';
  document.body.appendChild(tooltip);

  let state = { rooms: [], frontier: [], zones: [], player: null };
  let pan = { x: 0, y: 0 };
  let targetPan = { x: 0, y: 0 };
  let zoom = 1;
  let targetZoom = 1;
  let selectedZ = 0;
  let activeZone = null; // null = all zones, number = specific zone id
  let revealed = new Map();
  let hoveredRoom = null;
  let selectedRoom = null;
  let pathRooms = new Set();
  let pulsePhase = 0;
  let useIcons = true;
  let showFog = true;
  let showZones = true;
  let portalRooms = new Set(); // vnums of rooms that connect to other zones (shown as portals when filtering)
  let crossZoneExits = []; // {fromVnum, toVnum, fromZone, toZone, dir} for portal markers

  const ROOM_SIZE = 36;
  const ROOM_SPACING = 56;
  const ROOM_RADIUS = 8;

  const getZoneColor = (zoneId) => {
    const zone = state.zones.find(z => z.id === zoneId);
    return zone ? zone.color : '#6366f1';
  };
  const getZoneName = (zoneId) => {
    const zone = state.zones.find(z => z.id === zoneId);
    return zone ? zone.name : 'Zone ' + zoneId;
  };

  const dirOffsets = {
    north: [0, -1, 0], south: [0, 1, 0],
    east: [1, 0, 0], west: [-1, 0, 0],
    up: [0, 0, 1], down: [0, 0, -1]
  };

  const stamp = () => new Date().toLocaleTimeString();
  const setDebug = (el, v) => { if (el) el.textContent = v; };
  const setDebugError = (v) => setDebug(debugError, v || '-');
  const markPayload = () => setDebug(debugPayload, stamp());
  const lerp = (a, b, t) => a + (b - a) * t;

  const setWsStatus = (st, label) => {
    wsStatus.classList.remove('connecting', 'connected', 'disconnected', 'polling');
    wsStatus.classList.add(st);
    wsStatus.textContent = 'WS: ' + label;
    setDebug(debugWs, label);
  };

  // Build cross-zone exit index
  const buildCrossZoneIndex = () => {
    crossZoneExits = [];
    portalRooms = new Set();
    const roomMap = new Map();
    const coordMap = new Map();
    state.rooms.forEach(r => { roomMap.set(r.vnum, r); coordMap.set(r.x + ',' + r.y + ',' + r.z, r); });
    state.rooms.forEach(room => {
      (room.exits || []).forEach(dir => {
        const off = dirOffsets[dir];
        if (!off) return;
        const target = coordMap.get((room.x + off[0]) + ',' + (room.y + off[1]) + ',' + (room.z + off[2]));
        if (target && target.zone !== room.zone) {
          crossZoneExits.push({ fromVnum: room.vnum, toVnum: target.vnum, fromZone: room.zone, toZone: target.zone, dir });
          portalRooms.add(room.vnum);
          portalRooms.add(target.vnum);
        }
      });
    });
  };

  // Get visible rooms based on zone filter
  const getVisibleRooms = () => {
    if (activeZone === null) return state.rooms;
    // Show rooms in active zone + portal rooms from adjacent zones
    const adjacentPortalVnums = new Set();
    crossZoneExits.forEach(cx => {
      if (cx.fromZone === activeZone) adjacentPortalVnums.add(cx.toVnum);
      if (cx.toZone === activeZone) adjacentPortalVnums.add(cx.fromVnum);
    });
    return state.rooms.filter(r => r.zone === activeZone || adjacentPortalVnums.has(r.vnum));
  };

  const setActiveZone = (zoneId) => {
    activeZone = zoneId;
    // Re-center on zone centroid
    const zoneRooms = zoneId === null ? state.rooms : state.rooms.filter(r => r.zone === zoneId);
    if (zoneRooms.length > 0) {
      const cx = zoneRooms.reduce((s, r) => s + r.x, 0) / zoneRooms.length;
      const cy = zoneRooms.reduce((s, r) => s + r.y, 0) / zoneRooms.length;
      targetPan.x = canvas.clientWidth / 2 - (cx * ROOM_SPACING * zoom);
      targetPan.y = canvas.clientHeight / 2 - (cy * ROOM_SPACING * zoom);
    }
    updateUI();
    renderZoneOverview();
  };

  function resize() {
    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvas.clientWidth * dpr;
    canvas.height = canvas.clientHeight * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    minimap.width = minimap.clientWidth * dpr;
    minimap.height = minimap.clientHeight * dpr;
    miniCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    zoneOverview.width = zoneOverview.clientWidth * dpr;
    zoneOverview.height = zoneOverview.clientHeight * dpr;
    zoCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  window.addEventListener('resize', resize);
  setTimeout(resize, 0);

  zoomControl.addEventListener('input', (e) => { targetZoom = parseFloat(e.target.value); });
  minimapToggle.addEventListener('change', (e) => { minimap.classList.toggle('hidden', !e.target.checked); zoneOverview.classList.toggle('hidden', !e.target.checked); });
  iconMode.addEventListener('change', (e) => { useIcons = e.target.checked; });
  fogMode.addEventListener('change', (e) => { showFog = e.target.checked; });
  zoneMode.addEventListener('change', (e) => { showZones = e.target.checked; });

  let dragging = false;
  let last = { x: 0, y: 0 };
  canvas.addEventListener('mousedown', (e) => { dragging = true; last = { x: e.clientX, y: e.clientY }; });
  window.addEventListener('mouseup', () => dragging = false);

  const hitTest = (mx, my) => {
    const visible = getVisibleRooms().filter(r => r.z === selectedZ);
    return visible.find(r =>
      Math.abs(r.x * ROOM_SPACING - mx) < ROOM_SIZE/2 + 6 &&
      Math.abs(r.y * ROOM_SPACING - my) < ROOM_SIZE/2 + 6);
  };

  window.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left - pan.x) / zoom;
    const my = (e.clientY - rect.top - pan.y) / zoom;
    const hit = hitTest(mx, my);

    if (hit && !dragging) {
      hoveredRoom = hit;
      tooltip.querySelector('.tt-icon').textContent = hit.icon || '';
      tooltip.querySelector('.tt-name').textContent = hit.name;
      tooltip.querySelector('.tt-zone').textContent = '\u{1F4CD} ' + (hit.zoneName || 'Unknown Zone');
      const isPortal = activeZone !== null && hit.zone !== activeZone;
      tooltip.querySelector('.tt-info').innerHTML =
        (isPortal ? '<b style="color:#c084fc">\u{1F300} Portal from ' + getZoneName(hit.zone) + '</b><br>' : '') +
        '<b>Sector:</b> ' + hit.sector + '<br><b>Exits:</b> ' + hit.exits.join(', ') +
        '<br><b>VNUM:</b> ' + hit.vnum;
      tooltip.style.left = Math.min(e.clientX + 16, window.innerWidth - 300) + 'px';
      tooltip.style.top = Math.min(e.clientY + 16, window.innerHeight - 150) + 'px';
      tooltip.classList.add('visible');
    } else {
      hoveredRoom = null;
      tooltip.classList.remove('visible');
    }
    if (!dragging) return;
    targetPan.x += e.clientX - last.x;
    targetPan.y += e.clientY - last.y;
    last = { x: e.clientX, y: e.clientY };
  });

  canvas.addEventListener('click', (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left - pan.x) / zoom;
    const my = (e.clientY - rect.top - pan.y) / zoom;
    const hit = hitTest(mx, my);
    if (hit) {
      selectedRoom = hit;
      const isPortal = activeZone !== null && hit.zone !== activeZone;
      roomDetails.innerHTML =
        '<div style="font-size:24px;margin-bottom:8px">' + (isPortal ? '\u{1F300}' : (hit.icon || '\u{1F4CD}')) + '</div>' +
        '<strong style="font-size:15px">' + hit.name + '</strong><br/>' +
        '<span style="color:#a5b4fc">' + (hit.zoneName || '') + '</span>' +
        (isPortal ? '<br/><span style="color:#c084fc;font-size:12px">Portal entry — click to switch zone</span>' : '') +
        '<br/><br/>' +
        '<span style="color:#6b7280">Sector:</span> ' + hit.sector + '<br/>' +
        '<span style="color:#6b7280">Exits:</span> ' + hit.exits.join(', ') + '<br/>' +
        '<span style="color:#6b7280">VNUM:</span> ' + hit.vnum;
      // Double-click portal room to switch to that zone
      if (isPortal) {
        setTimeout(() => { setActiveZone(hit.zone); }, 300);
      }
    }
  });

  canvas.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left - pan.x) / zoom;
    const my = (e.clientY - rect.top - pan.y) / zoom;
    const hit = hitTest(mx, my);
    if (hit && state.player) {
      computePath(state.player.vnum, hit.vnum);
    }
  });

  const computePath = (startVnum, endVnum) => {
    pathRooms.clear();
    if (startVnum === endVnum) { pathInfo.classList.add('hidden'); return; }
    const roomMap = new Map();
    state.rooms.forEach(r => roomMap.set(r.vnum, r));
    const coordMap = new Map();
    state.rooms.forEach(r => coordMap.set(r.x + ',' + r.y + ',' + r.z, r));
    const visited = new Set([startVnum]);
    const queue = [[startVnum, [startVnum]]];
    let foundPath = null;
    while (queue.length > 0) {
      const [current, path] = queue.shift();
      const room = roomMap.get(current);
      if (!room) continue;
      for (const dir of room.exits) {
        const off = dirOffsets[dir];
        if (!off) continue;
        const neighbor = coordMap.get((room.x + off[0]) + ',' + (room.y + off[1]) + ',' + (room.z + off[2]));
        if (!neighbor || visited.has(neighbor.vnum)) continue;
        const newPath = [...path, neighbor.vnum];
        if (neighbor.vnum === endVnum) { foundPath = newPath; break; }
        visited.add(neighbor.vnum);
        queue.push([neighbor.vnum, newPath]);
      }
      if (foundPath) break;
    }
    if (foundPath) {
      foundPath.forEach(v => pathRooms.add(v));
      const dest = roomMap.get(endVnum);
      pathInfo.innerHTML =
        '<div class="path-title">\u{1F9ED} Path to ' + (dest ? dest.name : 'destination') + '</div>' +
        '<div class="path-steps">' + (foundPath.length - 1) + ' rooms away</div>';
      pathInfo.classList.remove('hidden');
    } else {
      pathInfo.innerHTML = '<div class="path-title">\u274C No path found</div>';
      pathInfo.classList.remove('hidden');
    }
  };

  const roundRect = (x, y, w, h, r) => {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r); ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h); ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r); ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
  };

  const render = () => {
    pan.x = lerp(pan.x, targetPan.x, 0.12);
    pan.y = lerp(pan.y, targetPan.y, 0.12);
    zoom = lerp(zoom, targetZoom, 0.1);
    pulsePhase += 0.06;
    const now = Date.now();
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#050709';
    ctx.fillRect(0, 0, w, h);
    ctx.save();
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, zoom);

    // Grid
    ctx.strokeStyle = 'rgba(255,255,255,0.02)';
    ctx.lineWidth = 1;
    const gridSize = ROOM_SPACING;
    const startX = Math.floor(-pan.x / zoom / gridSize) * gridSize - gridSize;
    const startY = Math.floor(-pan.y / zoom / gridSize) * gridSize - gridSize;
    const endX = startX + w / zoom + gridSize * 2;
    const endY = startY + h / zoom + gridSize * 2;
    for (let gx = startX; gx < endX; gx += gridSize) { ctx.beginPath(); ctx.moveTo(gx, startY); ctx.lineTo(gx, endY); ctx.stroke(); }
    for (let gy = startY; gy < endY; gy += gridSize) { ctx.beginPath(); ctx.moveTo(startX, gy); ctx.lineTo(endX, gy); ctx.stroke(); }

    const visibleAll = getVisibleRooms();
    const rooms = visibleAll.filter(r => r.z === selectedZ);
    const frontier = state.frontier.filter(r => r.z === selectedZ);
    const roomMap = new Map();
    const coordMap = new Map();
    rooms.forEach(r => { roomMap.set(r.vnum, r); coordMap.set(r.x + ',' + r.y + ',' + r.z, r); });

    // Zone boundaries
    if (showZones && state.zones.length > 0) {
      const zoneRooms = {};
      rooms.forEach(r => { if (!zoneRooms[r.zone]) zoneRooms[r.zone] = []; zoneRooms[r.zone].push(r); });
      Object.entries(zoneRooms).forEach(([zoneId, zRooms]) => {
        if (zRooms.length < 2) return;
        const zid = parseInt(zoneId);
        const color = getZoneColor(zid);
        const isActive = activeZone === null || activeZone === zid;
        const xs = zRooms.map(r => r.x * ROOM_SPACING);
        const ys = zRooms.map(r => r.y * ROOM_SPACING);
        const minX = Math.min(...xs) - ROOM_SIZE;
        const maxX = Math.max(...xs) + ROOM_SIZE;
        const minY = Math.min(...ys) - ROOM_SIZE;
        const maxY = Math.max(...ys) + ROOM_SIZE;
        ctx.strokeStyle = color + (isActive ? '40' : '20');
        ctx.fillStyle = color + (isActive ? '08' : '04');
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 4]);
        roundRect(minX, minY, maxX - minX, maxY - minY, 16);
        ctx.fill(); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = color + (isActive ? 'aa' : '44');
        ctx.font = 'bold 11px Inter, system-ui';
        ctx.textAlign = 'left'; ctx.textBaseline = 'top';
        const zone = state.zones.find(z => z.id === zid);
        if (zone) ctx.fillText(zone.name, minX + 8, minY + 6);
      });
    }

    // Fog of war
    if (showFog) {
      ctx.fillStyle = 'rgba(0,0,0,0.6)';
      ctx.fillRect(startX, startY, endX - startX, endY - startY);
      ctx.globalCompositeOperation = 'destination-out';
      rooms.forEach(room => {
        const px = room.x * ROOM_SPACING;
        const py = room.y * ROOM_SPACING;
        const revealTime = revealed.get(room.vnum) || now;
        const age = Math.min((now - revealTime) / 500, 1);
        const radius = (ROOM_SPACING * 0.8) * age;
        const grad = ctx.createRadialGradient(px, py, 0, px, py, radius);
        grad.addColorStop(0, 'rgba(0,0,0,1)');
        grad.addColorStop(0.7, 'rgba(0,0,0,0.8)');
        grad.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = grad;
        ctx.beginPath(); ctx.arc(px, py, radius, 0, Math.PI * 2); ctx.fill();
      });
      ctx.globalCompositeOperation = 'source-over';
    }

    // Connections
    ctx.lineCap = 'round';
    const drawn = new Set();
    const oneWayDrawn = new Set();
    const drawArrow = (fromX, fromY, toX, toY, color) => {
      const headLen = 12;
      const angle = Math.atan2(toY - fromY, toX - fromX);
      const arrowX = fromX + (toX - fromX) * 0.65;
      const arrowY = fromY + (toY - fromY) * 0.65;
      ctx.save(); ctx.fillStyle = color; ctx.beginPath();
      ctx.moveTo(arrowX, arrowY);
      ctx.lineTo(arrowX - headLen * Math.cos(angle - Math.PI / 6), arrowY - headLen * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(arrowX - headLen * Math.cos(angle + Math.PI / 6), arrowY - headLen * Math.sin(angle + Math.PI / 6));
      ctx.closePath(); ctx.fill(); ctx.restore();
    };

    rooms.forEach(room => {
      const oneWay = room.oneWayExits || [];
      room.exits.forEach(dir => {
        const off = dirOffsets[dir];
        if (!off) return;
        const target = coordMap.get((room.x + off[0]) + ',' + (room.y + off[1]) + ',' + (room.z + off[2]));
        if (!target) return;
        const isOneWay = oneWay.includes(dir);
        const isCrossZone = room.zone !== target.zone;
        const isPath = pathRooms.has(room.vnum) && pathRooms.has(target.vnum);
        if (!isOneWay) {
          const pair = room.vnum < target.vnum ? room.vnum + '-' + target.vnum : target.vnum + '-' + room.vnum;
          if (drawn.has(pair)) return;
          drawn.add(pair);
        } else {
          const key = room.vnum + '->' + target.vnum;
          if (oneWayDrawn.has(key)) return;
          oneWayDrawn.add(key);
        }
        const x1 = room.x * ROOM_SPACING, y1 = room.y * ROOM_SPACING;
        const x2 = target.x * ROOM_SPACING, y2 = target.y * ROOM_SPACING;
        ctx.lineWidth = isPath ? 5 : (isCrossZone ? 4 : 3);
        let lineColor;
        if (isPath) {
          ctx.strokeStyle = '#22c55e'; ctx.shadowColor = '#22c55e'; ctx.shadowBlur = 10;
          lineColor = '#22c55e';
        } else if (isCrossZone) {
          // Portal connections: dashed purple/pink
          ctx.strokeStyle = '#c084fc';
          ctx.setLineDash([8, 6]);
          ctx.shadowBlur = 0;
          lineColor = '#c084fc';
        } else if (isOneWay) {
          ctx.strokeStyle = '#f59e0b'; ctx.shadowBlur = 0; lineColor = '#f59e0b';
        } else {
          const grad = ctx.createLinearGradient(x1, y1, x2, y2);
          grad.addColorStop(0, 'rgba(99,102,241,0.4)');
          grad.addColorStop(1, 'rgba(168,85,247,0.4)');
          ctx.strokeStyle = grad; ctx.shadowBlur = 0;
          lineColor = 'rgba(168,85,247,0.6)';
        }
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
        ctx.shadowBlur = 0; ctx.setLineDash([]);
        if (isOneWay) drawArrow(x1, y1, x2, y2, lineColor);
      });
    });

    // Rooms
    rooms.forEach(room => {
      const px = room.x * ROOM_SPACING;
      const py = room.y * ROOM_SPACING;
      const isHovered = hoveredRoom && hoveredRoom.vnum === room.vnum;
      const isSelected = selectedRoom && selectedRoom.vnum === room.vnum;
      const isPath = pathRooms.has(room.vnum);
      const zoneColor = getZoneColor(room.zone);
      const isPortalGhost = activeZone !== null && room.zone !== activeZone;

      if (!revealed.has(room.vnum)) revealed.set(room.vnum, now);
      const revealAge = Math.min((now - revealed.get(room.vnum)) / 400, 1);
      const scale = 0.3 + revealAge * 0.7;

      ctx.save();
      ctx.translate(px, py);
      ctx.scale(scale, scale);
      if (isPortalGhost) ctx.globalAlpha = 0.5;

      ctx.shadowColor = isPath ? '#22c55e' : (isHovered ? zoneColor : 'rgba(0,0,0,0.6)');
      ctx.shadowBlur = isHovered || isPath ? 24 : 16;
      ctx.shadowOffsetY = 4;

      const grad = ctx.createLinearGradient(-ROOM_SIZE/2, -ROOM_SIZE/2, ROOM_SIZE/2, ROOM_SIZE/2);
      if (isPath) { grad.addColorStop(0, '#22c55e'); grad.addColorStop(1, '#15803d'); }
      else { grad.addColorStop(0, zoneColor); grad.addColorStop(1, zoneColor + '60'); }
      ctx.fillStyle = grad;
      roundRect(-ROOM_SIZE/2, -ROOM_SIZE/2, ROOM_SIZE, ROOM_SIZE, ROOM_RADIUS);
      ctx.fill();

      ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;
      ctx.strokeStyle = isHovered || isSelected ? '#fff' : (isPath ? '#4ade80' : zoneColor + 'aa');
      ctx.lineWidth = isHovered || isSelected ? 3 : 1.5;
      roundRect(-ROOM_SIZE/2, -ROOM_SIZE/2, ROOM_SIZE, ROOM_SIZE, ROOM_RADIUS);
      ctx.stroke();

      // Portal diamond overlay
      if (isPortalGhost) {
        ctx.fillStyle = '#c084fc';
        ctx.font = '14px system-ui';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText('\u{1F300}', 0, 2);
      } else if (useIcons && room.icon) {
        ctx.font = '20px system-ui';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillStyle = '#fff';
        ctx.fillText(room.icon, 0, 2);
      } else {
        ctx.fillStyle = '#0a0e14';
        ctx.font = 'bold 16px system-ui';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(room.symbol, 0, 2);
      }

      ctx.restore();
    });

    // Vertical exit indicators
    const verticalExitRooms = rooms.filter(r => r.exits && (r.exits.includes('up') || r.exits.includes('down')));
    // Frontier
    frontier.forEach(room => {
      const px = room.x * ROOM_SPACING;
      const py = room.y * ROOM_SPACING;
      if (room.deathtrap) {
        // Deathtrap frontier - red dashed border with skull
        ctx.strokeStyle = 'rgba(239,68,68,0.6)'; ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        roundRect(px - ROOM_SIZE/2 + 4, py - ROOM_SIZE/2 + 4, ROOM_SIZE - 8, ROOM_SIZE - 8, ROOM_RADIUS - 2);
        ctx.stroke(); ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(239,68,68,0.7)';
        ctx.font = 'bold 20px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText('💀', px, py + 2);
      } else {
        // Normal frontier - gray dashed border with ?
        ctx.strokeStyle = 'rgba(100,116,139,0.3)'; ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        roundRect(px - ROOM_SIZE/2 + 4, py - ROOM_SIZE/2 + 4, ROOM_SIZE - 8, ROOM_SIZE - 8, ROOM_RADIUS - 2);
        ctx.stroke(); ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(100,116,139,0.5)';
        ctx.font = 'bold 18px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText('?', px, py + 2);
      }
    });

    // Player
    if (state.player && state.player.z === selectedZ) {
      const px = state.player.x * ROOM_SPACING;
      const py = state.player.y * ROOM_SPACING;
      const pulse = Math.sin(pulsePhase) * 0.35 + 0.65;
      const pulseSize = 12 + Math.sin(pulsePhase * 1.3) * 4;
      for (let i = 3; i >= 0; i--) {
        ctx.fillStyle = 'rgba(251,191,36,' + (0.08 * pulse * (4 - i)) + ')';
        ctx.beginPath(); ctx.arc(px, py, pulseSize + 12 + i * 8, 0, Math.PI * 2); ctx.fill();
      }
      ctx.shadowColor = '#f59e0b'; ctx.shadowBlur = 30 * pulse;
      const pGrad = ctx.createRadialGradient(px, py, 0, px, py, pulseSize);
      pGrad.addColorStop(0, '#fef3c7'); pGrad.addColorStop(0.4, '#fbbf24');
      pGrad.addColorStop(0.8, '#f59e0b'); pGrad.addColorStop(1, '#b45309');
      ctx.fillStyle = pGrad;
      ctx.beginPath(); ctx.arc(px, py, pulseSize, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;
      ctx.fillStyle = '#1c1917'; ctx.font = 'bold 14px system-ui';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText('@', px, py + 1);
    }

    // Up/down indicators
    verticalExitRooms.forEach(room => {
      const px = room.x * ROOM_SPACING;
      const py = room.y * ROOM_SPACING;
      ctx.font = 'bold 11px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      if (room.exits.includes('up')) {
        const ux = px + ROOM_SIZE/2 - 2, uy = py - ROOM_SIZE/2 + 2;
        ctx.fillStyle = '#22d3ee'; ctx.beginPath(); ctx.arc(ux, uy, 8, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
        ctx.fillStyle = '#0a0e14'; ctx.fillText('\u2191', ux, uy + 1);
      }
      if (room.exits.includes('down')) {
        const dx = px + ROOM_SIZE/2 - 2, dy = py + ROOM_SIZE/2 - 2;
        ctx.fillStyle = '#dc2626'; ctx.beginPath(); ctx.arc(dx, dy, 9, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
        ctx.fillStyle = '#fff'; ctx.fillText('\u2193', dx, dy + 1);
      }
    });

    ctx.restore();
    renderMinimap(rooms);
    requestAnimationFrame(render);
  };

  const renderMinimap = (rooms) => {
    const mw = minimap.clientWidth;
    const mh = minimap.clientHeight;
    miniCtx.clearRect(0, 0, mw, mh);
    if (rooms.length === 0) return;
    miniCtx.fillStyle = 'rgba(8,11,16,0.95)';
    miniCtx.fillRect(0, 0, mw, mh);
    const xs = rooms.map(r => r.x), ys = rooms.map(r => r.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const width = maxX - minX + 1, height = maxY - minY + 1;
    const scale = Math.min((mw - 32) / (width * 10), (mh - 32) / (height * 10));
    miniCtx.save(); miniCtx.translate(16, 16); miniCtx.scale(scale, scale);
    if (showZones) {
      const zoneRooms = {};
      rooms.forEach(r => { if (!zoneRooms[r.zone]) zoneRooms[r.zone] = []; zoneRooms[r.zone].push(r); });
      Object.entries(zoneRooms).forEach(([zid, zRooms]) => {
        miniCtx.fillStyle = getZoneColor(parseInt(zid)) + '20';
        zRooms.forEach(r => { miniCtx.fillRect((r.x - minX) * 10, (r.y - minY) * 10, 8, 8); });
      });
    }
    rooms.forEach(room => {
      const color = pathRooms.has(room.vnum) ? '#22c55e' : getZoneColor(room.zone);
      miniCtx.fillStyle = color;
      miniCtx.beginPath(); miniCtx.arc((room.x - minX) * 10 + 4, (room.y - minY) * 10 + 4, 3, 0, Math.PI * 2); miniCtx.fill();
    });
    if (state.player && state.player.z === selectedZ) {
      const pulse = Math.sin(pulsePhase) * 0.3 + 0.7;
      miniCtx.fillStyle = 'rgba(251,191,36,' + pulse + ')';
      miniCtx.beginPath(); miniCtx.arc((state.player.x - minX) * 10 + 4, (state.player.y - minY) * 10 + 4, 6, 0, Math.PI * 2); miniCtx.fill();
    }
    miniCtx.strokeStyle = 'rgba(255,255,255,0.25)'; miniCtx.lineWidth = 1.5 / scale;
    const vpX = (-pan.x / zoom / ROOM_SPACING - minX) * 10;
    const vpY = (-pan.y / zoom / ROOM_SPACING - minY) * 10;
    const vpW = (canvas.clientWidth / zoom / ROOM_SPACING) * 10;
    const vpH = (canvas.clientHeight / zoom / ROOM_SPACING) * 10;
    miniCtx.strokeRect(vpX, vpY, vpW, vpH);
    miniCtx.restore();
  };

  // Zone overview mini-map (all zones as clusters)
  const renderZoneOverview = () => {
    const ow = zoneOverview.clientWidth;
    const oh = zoneOverview.clientHeight;
    zoCtx.clearRect(0, 0, ow, oh);
    zoCtx.fillStyle = 'rgba(8,11,16,0.95)';
    zoCtx.fillRect(0, 0, ow, oh);
    if (state.zones.length === 0) return;

    // Compute zone centroids from all rooms
    const zoneCentroids = {};
    const zoneCounts = {};
    state.rooms.forEach(r => {
      if (!zoneCentroids[r.zone]) { zoneCentroids[r.zone] = { x: 0, y: 0 }; zoneCounts[r.zone] = 0; }
      zoneCentroids[r.zone].x += r.x;
      zoneCentroids[r.zone].y += r.y;
      zoneCounts[r.zone]++;
    });
    const centroids = [];
    Object.keys(zoneCentroids).forEach(zid => {
      const n = zoneCounts[zid];
      centroids.push({ zone: parseInt(zid), x: zoneCentroids[zid].x / n, y: zoneCentroids[zid].y / n, count: n });
    });
    if (centroids.length === 0) return;

    const xs = centroids.map(c => c.x), ys = centroids.map(c => c.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const rangeX = maxX - minX || 1, rangeY = maxY - minY || 1;
    const pad = 20;
    const scaleX = (ow - pad * 2) / rangeX;
    const scaleY = (oh - pad * 2) / rangeY;
    const sc = Math.min(scaleX, scaleY);

    // Draw cross-zone connections
    zoCtx.strokeStyle = 'rgba(255,255,255,0.1)';
    zoCtx.lineWidth = 1;
    const connectedPairs = new Set();
    crossZoneExits.forEach(cx => {
      const pair = Math.min(cx.fromZone, cx.toZone) + '-' + Math.max(cx.fromZone, cx.toZone);
      if (connectedPairs.has(pair)) return;
      connectedPairs.add(pair);
      const from = centroids.find(c => c.zone === cx.fromZone);
      const to = centroids.find(c => c.zone === cx.toZone);
      if (!from || !to) return;
      zoCtx.beginPath();
      zoCtx.moveTo(pad + (from.x - minX) * sc, pad + (from.y - minY) * sc);
      zoCtx.lineTo(pad + (to.x - minX) * sc, pad + (to.y - minY) * sc);
      zoCtx.stroke();
    });

    // Store centroid positions for click detection
    zoneOverview._centroids = [];
    centroids.forEach(c => {
      const cx = pad + (c.x - minX) * sc;
      const cy = pad + (c.y - minY) * sc;
      const color = getZoneColor(c.zone);
      const isActive = activeZone === c.zone;
      const radius = Math.max(4, Math.min(12, Math.sqrt(c.count) * 1.5));
      zoneOverview._centroids.push({ zone: c.zone, cx, cy, radius });

      if (isActive) {
        zoCtx.fillStyle = color + '40';
        zoCtx.beginPath(); zoCtx.arc(cx, cy, radius + 6, 0, Math.PI * 2); zoCtx.fill();
      }
      zoCtx.fillStyle = isActive ? color : color + '99';
      zoCtx.beginPath(); zoCtx.arc(cx, cy, radius, 0, Math.PI * 2); zoCtx.fill();
      if (isActive) {
        zoCtx.strokeStyle = '#fff'; zoCtx.lineWidth = 2;
        zoCtx.beginPath(); zoCtx.arc(cx, cy, radius, 0, Math.PI * 2); zoCtx.stroke();
      }
    });

    // Title
    zoCtx.fillStyle = 'rgba(255,255,255,0.4)';
    zoCtx.font = '10px Inter, system-ui';
    zoCtx.textAlign = 'left'; zoCtx.textBaseline = 'top';
    zoCtx.fillText('Zone Overview' + (activeZone !== null ? ' \u2022 ' + getZoneName(activeZone) : ' \u2022 All'), 6, 4);
  };

  // Click on zone overview to switch zones
  zoneOverview.addEventListener('click', (e) => {
    const rect = zoneOverview.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const centroids = zoneOverview._centroids || [];
    let clicked = null;
    for (const c of centroids) {
      if (Math.hypot(mx - c.cx, my - c.cy) < c.radius + 4) { clicked = c.zone; break; }
    }
    if (clicked !== null) {
      setActiveZone(clicked === activeZone ? null : clicked);
    } else {
      setActiveZone(null);
    }
  });

  const updateUI = () => {
    // Level select
    const visibleRooms = getVisibleRooms();
    const zs = [...new Set(visibleRooms.map(r => r.z))].sort((a,b) => a - b);
    zSelect.innerHTML = zs.map(z =>
      '<option value="' + z + '"' + (z === selectedZ ? ' selected' : '') + '>Level ' + z + '</option>'
    ).join('');

    // Zone info
    if (state.player && state.rooms.length > 0) {
      const playerRoom = state.rooms.find(r => r.vnum === state.player.vnum);
      if (playerRoom) {
        const zone = state.zones.find(z => z.id === playerRoom.zone);
        const zoneRoomCount = state.rooms.filter(r => r.zone === playerRoom.zone).length;
        zoneInfo.innerHTML =
          '<div class="zone-name" style="color:' + (zone ? zone.color : '#a5b4fc') + '">' +
          (playerRoom.zoneName || 'Unknown Zone') + '</div>' +
          '<div class="zone-stats">' + zoneRoomCount + ' rooms explored' +
          (activeZone !== null ? ' \u2022 <span style="color:#c084fc">Filtering: ' + getZoneName(activeZone) + '</span>' : '') +
          '</div>';
      }
    }

    // Zone filter list
    if (state.zones.length > 0) {
      const zoneCounts = {};
      state.rooms.forEach(r => { zoneCounts[r.zone] = (zoneCounts[r.zone] || 0) + 1; });
      let html = '<div class="zone-filter-item' + (activeZone === null ? ' active' : '') + '" data-zone="all">' +
        '<span class="zf-dot" style="background:linear-gradient(135deg,#6366f1,#a855f7)"></span>' +
        '<span class="zf-name">All Zones</span>' +
        '<span class="zf-count">' + state.rooms.length + '</span></div>';
      // Sort by room count descending
      const sorted = [...state.zones].sort((a, b) => (zoneCounts[b.id] || 0) - (zoneCounts[a.id] || 0));
      sorted.forEach(z => {
        const count = zoneCounts[z.id] || 0;
        const isPlayerZone = state.player && state.rooms.find(r => r.vnum === state.player.vnum && r.zone === z.id);
        html += '<div class="zone-filter-item' + (activeZone === z.id ? ' active' : '') + '" data-zone="' + z.id + '">' +
          '<span class="zf-dot" style="background:' + z.color + '"></span>' +
          '<span class="zf-name">' + (isPlayerZone ? '\u{1F4CD} ' : '') + z.name + '</span>' +
          '<span class="zf-count">' + count + '</span></div>';
      });
      zoneFilterList.innerHTML = html;
      // Attach click handlers
      zoneFilterList.querySelectorAll('.zone-filter-item').forEach(el => {
        el.addEventListener('click', () => {
          const zv = el.dataset.zone;
          setActiveZone(zv === 'all' ? null : parseInt(zv));
        });
      });
    }

    // Zone list (bottom)
    if (state.zones.length > 0) {
      zoneList.innerHTML = '<h3>Zones Explored</h3>' + state.zones.map(z =>
        '<div class="zone-item' + (activeZone === z.id ? ' active' : '') + '" data-zone="' + z.id + '"><span class="zone-dot" style="background:' + z.color + '"></span>' + z.name + '</div>'
      ).join('');
      zoneList.querySelectorAll('.zone-item').forEach(el => {
        el.addEventListener('click', () => {
          const zv = parseInt(el.dataset.zone);
          setActiveZone(zv === activeZone ? null : zv);
        });
      });
    }
  };

  zSelect.addEventListener('change', (e) => { selectedZ = parseInt(e.target.value, 10); });

  const urlParams = new URLSearchParams(window.location.search);
  const player = urlParams.get('player') || '';
  const token = urlParams.get('t') || '';
  const debugEnabled = urlParams.get('debug') === '1';
  if (debugPanel && debugEnabled) debugPanel.classList.remove('hidden');
  if (!player) playerWarning.classList.remove('hidden');

  const applyState = (data) => {
    if (data.type === 'map_data') {
      state = data;
      buildCrossZoneIndex();
      if (state.player) {
        selectedZ = state.player.z;
        // Default to player's current zone on first load or zone change
        const playerRoom = state.rooms.find(r => r.vnum === state.player.vnum);
        if (playerRoom && state.rooms.length > 50) {
          // Auto-switch zone filter when player changes zones
          if (activeZone === null || (playerRoom.zone !== activeZone)) {
            activeZone = playerRoom.zone;
          }
        }
        // Center on player or zone centroid
        if (activeZone !== null) {
          const zoneRooms = state.rooms.filter(r => r.zone === activeZone);
          if (zoneRooms.length > 0) {
            // Center on player if in this zone, else zone centroid
            if (playerRoom && playerRoom.zone === activeZone) {
              targetPan.x = canvas.clientWidth / 2 - (state.player.x * ROOM_SPACING * zoom);
              targetPan.y = canvas.clientHeight / 2 - (state.player.y * ROOM_SPACING * zoom);
            } else {
              const cx = zoneRooms.reduce((s, r) => s + r.x, 0) / zoneRooms.length;
              const cy = zoneRooms.reduce((s, r) => s + r.y, 0) / zoneRooms.length;
              targetPan.x = canvas.clientWidth / 2 - (cx * ROOM_SPACING * zoom);
              targetPan.y = canvas.clientHeight / 2 - (cy * ROOM_SPACING * zoom);
            }
          }
        } else {
          targetPan.x = canvas.clientWidth / 2 - (state.player.x * ROOM_SPACING * zoom);
          targetPan.y = canvas.clientHeight / 2 - (state.player.y * ROOM_SPACING * zoom);
        }
      }
      updateUI();
      renderZoneOverview();
      markPayload();
    }
  };

  let pollTimer = null;
  const startPolling = () => {
    if (pollTimer || !player) return;
    setWsStatus('polling', 'polling');
    const fetchState = () => {
      fetch('/state?player=' + encodeURIComponent(player) + '&t=' + encodeURIComponent(token))
        .then(r => { setDebug(debugPoll, 'HTTP ' + r.status); return r.ok ? r.json() : null; })
        .then(data => { if (data) applyState(data); })
        .catch(() => setDebugError('poll error'));
    };
    fetchState();
    pollTimer = setInterval(fetchState, 2000);
  };
  const stopPolling = () => { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } };

  let ws = null;
  let wsConnected = false;
  let reconnectAttempts = 0;
  const maxReconnectDelay = 30000;

  const connectWebSocket = () => {
    setWsStatus('connecting', 'connecting');
    ws = new WebSocket('ws://' + window.location.host);
    const fallbackTimer = setTimeout(() => { if (!wsConnected) startPolling(); }, 3000);
    ws.addEventListener('open', () => {
      wsConnected = true; reconnectAttempts = 0;
      clearTimeout(fallbackTimer); stopPolling();
      setWsStatus('connected', 'connected');
      if (player) ws.send(JSON.stringify({ type: 'subscribe', player, token, mode: 'full' }));
    });
    ws.addEventListener('close', () => {
      wsConnected = false;
      setWsStatus('disconnected', 'reconnecting...');
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), maxReconnectDelay);
      reconnectAttempts++;
      setTimeout(connectWebSocket, delay);
    });
    ws.addEventListener('error', (e) => { console.error('WebSocket error:', e); });
    ws.addEventListener('message', (e) => applyState(JSON.parse(e.data)));
  };

  connectWebSocket();
  render();
})();"""
