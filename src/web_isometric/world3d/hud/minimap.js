// Minimap from the zone map: every room as a tile in its cell, the rooms you have explored
// brighter, shared openings as bridges, passages as dots, the hero as an arrow. Click a
// room to walk there (main.js plans the route through open exits and stairs). The big map
// (`browse`) also zooms (wheel, +/-), pans (drag) and shows another zone than yours (browse(z)).
import { isDeadly } from '../deathlogic.js';
import { chessSquare, SQUARE_FILL } from '../chesslogic.js';
const DEADLY = '#8a1c14';
const SECTOR = {
  inside: '#8a8a96', dungeon: '#6f6a78', cave: '#6a6052', city: '#c7ab7c', forest: '#4f8a46', field: '#86a85a',
  hills: '#7e9a5c', mountain: '#8a857a', desert: '#d6bd86', swamp: '#56664a', water_swim: '#3f7fb0',
  water_noswim: '#2f66a0', underwater: '#2a5a8a', flying: '#a8c8e8', default: '#7d8a70',
  // the room looks (room_looks.py)
  mine: '#7a6450', crypt: '#5e5868', sewer: '#5a6a4a', snow: '#e4ecf4', shore: '#e0cc94', volcanic: '#7a3a2a',
  web: '#5a5e4a', stones: '#7c8a68', village: '#9a8a5e', camp: '#8a7a56', garden: '#5e9a4a', ruins: '#a49c88', terrace: '#e0dacc', ice_cave: '#a8c8e0', lava_cave: '#5a2a1a', castle: '#9a948a', necropolis: '#4c5650', drow: '#4a3a5e', foundry: '#5a4a3a',
  chessboard: SQUARE_FILL.gate,
};
// a room's fill: the Chessboard's squares in their own white and black
const fillOf = r => r.data.look === 'chessboard' ? SQUARE_FILL[chessSquare(r.data.name) || 'gate'] : SECTOR[r.data.look] || SECTOR[r.data.sector] || SECTOR.default;
const CW = 22, CH = 14;      // css px per cell (keeps the 24:15 room shape)
export const ZOOM_MIN = 0.3, ZOOM_MAX = 3;

// a zone the big map shows without walking it (the zone list): its rooms and cells, as Zone has them
export function mapOfZone(zm) {
  const rooms = new Map(), cells = new Map();
  for (const r of (zm && zm.rooms) || []) {
    const room = { data: r, vnum: r.vnum, name: r.name, cx: r.cell[0], cy: r.cell[1] };
    rooms.set(r.vnum, room);
    cells.set(`${room.cx},${room.cy}`, room);
  }
  return { num: zm && zm.zone, name: (zm && zm.name) || '', rooms, cells };
}

// the middle of a zone's rooms, in cells (where a browsed zone opens)
export function middleOf(z) {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const r of z.rooms.values()) {
    minX = Math.min(minX, r.cx); maxX = Math.max(maxX, r.cx + 1); minY = Math.min(minY, r.cy); maxY = Math.max(maxY, r.cy + 1);
  }
  return isFinite(minX) ? { x: (minX + maxX) / 2, y: (minY + maxY) / 2 } : { x: 0, y: 0 };
}

// the zones the big map's list offers: those you have set foot in, and the one you stand in, by name
export function zoneIndex(atlas, explored, here = null) {
  const zoneOf = new Map(((atlas && atlas.rooms) || []).map(r => [r.vnum, r.zone]));
  const seen = new Map();
  for (const v of explored || []) {
    const z = zoneOf.get(v);
    if (z != null && z >= 0) seen.set(z, (seen.get(z) || 0) + 1);
  }
  if (here != null && !seen.has(here)) seen.set(here, 0);
  const names = new Map(((atlas && atlas.zones) || []).map(z => [z.id, z.name]));
  return [...seen.entries()].map(([id, n]) => ({ id, name: names.get(id) || `Zone ${id}`, n }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

// `cell` scales the rooms (the big map, M, draws them larger)
export function createMinimap(root, onPick, onNorth = null, { cell = 1, browse = false } = {}) {
  const pings = [], PING_MS = 4000;
  let scale = 1;                              // the big map's zoom
  let follow = true, vc = { x: 0, y: 0 };     // centred on the hero, or where it was dragged (cells)
  let shown = null, shownSeen = new Set();    // another zone being looked at, and your rooms there
  const CWc = () => CW * cell * scale, CHc = () => CH * cell * scale;
  const cv = root.querySelector('canvas');
  const ctx = cv.getContext('2d');
  const S = 2;   // the canvas is drawn at twice its CSS size (it is hidden at creation, so not measured)
  let zone = null, explored = new Set(), hero = { x: 0, z: 0, yaw: 0, cam: 0 }, room = null, dirty = true, last = 0;
  let guild = null;            // {vnum, room, trainer}: where your class's trainer stands
  let questMark = null;        // the room your marquee quest sends you to (a gold diamond)
  const north = root.querySelector('.mm-north');
  if (north) north.addEventListener('click', e => { e.stopPropagation(); if (onNorth) onNorth(); });
  const W = () => cv.width, H = () => cv.height;

  const centre = () => (follow && !shown ? { x: hero.x / 24, y: hero.z / 15 } : vc);
  function toScreen(cx, cy) {
    const c = centre();
    return [(cx - c.x) * CWc() * S + W() / 2, (cy - c.y) * CHc() * S + H() / 2];
  }
  // the cell under a point of the canvas (css px from its corner)
  function cellAt(px, py) {
    const c = centre();
    return [(px * S - W() / 2) / (CWc() * S) + c.x, (py * S - H() / 2) / (CHc() * S) + c.y];
  }
  function draw() {
    ctx.clearRect(0, 0, W(), H());
    const z = shown || zone;
    if (!z) return;
    const cw = CWc() * S, ch = CHc() * S, pad = 2.2 * S * Math.min(1, scale);
    const fine = scale >= 0.55;               // zoomed far out the rooms are bare tiles
    for (const r of z.rooms.values()) {
      const [x, y] = toScreen(r.cx, r.cy);
      if (x < -cw || y < -ch || x > W() + cw || y > H() + ch) continue;
      const seen = shown ? shownSeen.has(r.vnum) : explored.has(r.vnum) || r === room;
      ctx.globalAlpha = seen ? 0.95 : 0.32;
      const fill = isDeadly(r.data.flags) ? DEADLY : fillOf(r);
      ctx.fillStyle = fill;
      ctx.beginPath(); ctx.roundRect(x + pad, y + pad, cw - pad * 2, ch - pad * 2, 3 * S); ctx.fill();
      if (!fine) continue;
      if (fill === DEADLY) {
        // a death trap: red, a skull on it
        ctx.font = `${10 * S}px sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillStyle = '#ffd9cf'; ctx.fillText('☠', x + cw / 2, y + ch / 2);
        ctx.fillStyle = fill;
      }
      // openings: little bridges across the shared edge; passages: dots on the edge
      for (const [d, e] of Object.entries(r.data.exits)) {
        if (d === 'east' && e.kind === 'open') { ctx.fillRect(x + cw - pad - 1, y + ch / 2 - 2 * S, pad * 2 + 2, 4 * S); continue; }
        if (d === 'south' && e.kind === 'open') { ctx.fillRect(x + cw / 2 - 2 * S, y + ch - pad - 1, 4 * S, pad * 2 + 2); continue; }
        if (e.kind === 'open' || !seen) continue;
        ctx.fillStyle = e.kind === 'zone' ? '#ffd27a' : '#bfe0ff';
        if (d === 'up' || d === 'down') {
          // stairs: ▲ on the right of the room, ▼ on the left (where they stand in the room)
          const px = d === 'up' ? x + cw * 0.7 : x + cw * 0.3, py = y + ch / 2, s = 3.2 * S * Math.min(1, scale);
          ctx.beginPath();
          if (d === 'up') { ctx.moveTo(px, py - s); ctx.lineTo(px + s, py + s * 0.8); ctx.lineTo(px - s, py + s * 0.8); }
          else { ctx.moveTo(px, py + s); ctx.lineTo(px + s, py - s * 0.8); ctx.lineTo(px - s, py - s * 0.8); }
          ctx.closePath(); ctx.fill();
          ctx.strokeStyle = 'rgba(0,0,0,.6)'; ctx.lineWidth = 0.8 * S; ctx.stroke();
        } else {
          const px = d === 'east' ? x + cw - pad : d === 'west' ? x + pad : x + cw / 2;
          const py = d === 'north' ? y + pad : d === 'south' ? y + ch - pad : y + ch / 2;
          ctx.beginPath(); ctx.arc(px, py, 2.2 * S * Math.min(1, scale), 0, Math.PI * 2); ctx.fill();
        }
        ctx.fillStyle = fill;
      }
    }
    ctx.globalAlpha = 1;
    if (shown) return;                          // another zone: none of you, your marks or your pings
    // pings (ambient.js): something heard in a room, a ring that swells and fades
    const nowP = performance.now();
    for (let i = pings.length - 1; i >= 0; i--) {
      const p = pings[i], age = (nowP - p.at) / PING_MS;
      if (age >= 1) { pings.splice(i, 1); continue; }
      const pr = zone.rooms.get(p.vnum);
      if (!pr) continue;
      const [x, y] = toScreen(pr.cx, pr.cy);
      ctx.globalAlpha = 1 - age;
      ctx.strokeStyle = p.kind === 'danger' ? '#ff5a3c' : '#f3d999';
      ctx.lineWidth = 2.2 * S;
      for (const k of [0, 0.5]) {
        const a = (age * 2 + k) % 1;
        ctx.beginPath(); ctx.arc(x + cw / 2, y + ch / 2, (4 + a * 14) * S, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    // your guild's trainer: a gold star
    const gr = guild && zone.rooms.get(guild.vnum);
    if (gr) {
      const [x, y] = toScreen(gr.cx, gr.cy);
      ctx.font = `${11 * S}px sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.lineWidth = 2.4 * S; ctx.strokeStyle = 'rgba(0,0,0,.75)'; ctx.fillStyle = '#ffd86a';
      ctx.strokeText('★', x + cw / 2, y + ch / 2); ctx.fillText('★', x + cw / 2, y + ch / 2);
    }
    // the marquee quest's next place: a gold diamond
    const qr = questMark != null && zone.rooms.get(questMark);
    if (qr) {
      const [x, y] = toScreen(qr.cx, qr.cy);
      ctx.font = `bold ${12 * S}px sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.lineWidth = 2.6 * S; ctx.strokeStyle = 'rgba(0,0,0,.8)'; ctx.fillStyle = '#ffb84a';
      ctx.strokeText('◆', x + cw / 2, y + ch / 2); ctx.fillText('◆', x + cw / 2, y + ch / 2);
    }
    if (room) {
      const [x, y] = toScreen(room.cx, room.cy);
      ctx.strokeStyle = '#f3d999'; ctx.lineWidth = 1.6 * S;
      ctx.beginPath(); ctx.roundRect(x + pad, y + pad, cw - pad * 2, ch - pad * 2, 3 * S); ctx.stroke();
    }
    // where the camera looks: a soft wedge from the hero (the map itself stays north up)
    const [hx, hy] = toScreen(hero.x / 24, hero.z / 15);
    ctx.save();
    ctx.translate(hx, hy);
    ctx.rotate(-hero.cam);                       // yaw 0 looks north (up the map)
    const g = ctx.createRadialGradient(0, 0, 0, 0, 0, 34 * S);
    g.addColorStop(0, 'rgba(243,217,153,.38)'); g.addColorStop(1, 'rgba(243,217,153,0)');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, 34 * S, -Math.PI / 2 - 0.55, -Math.PI / 2 + 0.55); ctx.closePath(); ctx.fill();
    ctx.restore();
    // the hero: an arrow pointing the way they face
    ctx.save();
    ctx.translate(hx, hy);
    ctx.rotate(-hero.yaw + Math.PI);
    ctx.fillStyle = '#fff'; ctx.strokeStyle = '#000'; ctx.lineWidth = 1 * S;
    ctx.beginPath(); ctx.moveTo(0, -5 * S); ctx.lineTo(3.6 * S, 4 * S); ctx.lineTo(0, 2 * S); ctx.lineTo(-3.6 * S, 4 * S); ctx.closePath();
    ctx.fill(); ctx.stroke();
    ctx.restore();
  }

  // the canvas's own css size (the big map's is scaled down to fit small windows)
  const cssOf = e => { const r = cv.getBoundingClientRect(); return [(e.clientX - r.left) * (W() / S) / r.width, (e.clientY - r.top) * (H() / S) / r.height]; };
  let drag = null, dragged = false;
  cv.addEventListener('click', e => {
    if (dragged) { dragged = false; return; }
    if (!zone || shown) return;                 // another zone's rooms are looked at, not walked to
    const [cx, cy] = cellAt(...cssOf(e)).map(Math.floor);
    const target = zone.cells.get(`${cx},${cy}`);
    if (target) onPick(target);
  });
  const zoomAt = (f, px = null, py = null) => {
    const to = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, scale * f));
    if (to === scale) return;
    if (px == null || (follow && !shown)) { scale = to; dirty = true; return; }
    const [bx, by] = cellAt(px, py);          // the cell under the pointer stays under it
    scale = to;
    const [ax, ay] = cellAt(px, py);
    vc = { x: vc.x + bx - ax, y: vc.y + by - ay };
    dirty = true;
  };
  if (browse) {
    cv.addEventListener('wheel', e => { e.preventDefault(); zoomAt(Math.exp(-e.deltaY * 0.0015), ...cssOf(e)); }, { passive: false });
    cv.addEventListener('pointerdown', e => { drag = { at: cssOf(e), c: { ...centre() }, moved: false }; });
    cv.addEventListener('pointermove', e => {
      if (!drag) return;
      const [px, py] = cssOf(e), dx = px - drag.at[0], dy = py - drag.at[1];
      if (!drag.moved && Math.hypot(dx, dy) < 5) return;
      if (!drag.moved) { drag.moved = true; try { cv.setPointerCapture(e.pointerId); } catch (_) { /* gone */ } }
      follow = false;
      vc = { x: drag.c.x - dx / CWc(), y: drag.c.y - dy / CHc() };
      cv.style.cursor = 'grabbing';
      dirty = true;
    });
    const end = () => { if (drag && drag.moved) dragged = true; drag = null; cv.style.cursor = ''; };
    cv.addEventListener('pointerup', end);
    cv.addEventListener('pointercancel', end);
  }
  const label = () => {
    const z = shown || zone;
    root.querySelector('.mm-zone').textContent = z ? z.name : '';
    const rm = root.querySelector('.mm-room');
    if (rm) rm.textContent = shown ? `Looking at ${shown.name}${zone ? ` · you are in ${zone.name}` : ''}` : room ? room.name : '';
  };

  return {
    // something heard in a room (ambient.js): 'danger' red, else gold
    ping(vnum, kind = 'danger') { pings.push({ vnum, kind, at: performance.now() }); dirty = true; },
    setZone(z) {
      zone = z; dirty = true;
      if (shown && z && shown.num === z.num) shown = null;
      label();
    },
    // another zone to look at (mapOfZone), with the rooms you know (any of the world's); null: yours
    browse(z, seen = []) {
      if (!z || (zone && z.num === zone.num)) { this.home(); return; }
      shown = z; shownSeen = new Set(seen); follow = false; vc = middleOf(z); dirty = true;
      label();
    },
    browsing() { return shown ? shown.num : null; },
    // back to you: your zone, centred on you (the zoom is kept)
    home() { shown = null; follow = true; dirty = true; label(); },
    zoomBy(f) { zoomAt(f); },
    get zoom() { return scale; },
    setExplored(list) { explored = new Set(list); dirty = true; },
    setGuild(g) {
      const v = g && g.vnum;
      if (v === (guild && guild.vnum)) return;
      guild = g || null; dirty = true;
      cv.title = g ? `★ ${g.trainer} (${g.room}) trains you` : '';
    },
    setQuestMark(vnum) { if (vnum === questMark) return; questMark = vnum; dirty = true; },
    redraw() { dirty = true; last = 0; },
    setRoom(r) { room = r; dirty = true; label(); },
    setTime(t) {
      if (!t) return;
      const h = t.hour != null ? t.hour : null;
      root.querySelector('.mm-time').textContent = h == null ? '' : `${String(h).padStart(2, '0')}:00${t.period ? ' · ' + t.period : ''}`;
    },
    // camYaw: the camera's turn (0 = north up); the compass needle and the view wedge follow it
    update(pos, yaw, camYaw = 0) {
      if (Math.abs(pos.x - hero.x) > 0.05 || Math.abs(pos.z - hero.z) > 0.05 || Math.abs(yaw - hero.yaw) > 0.05
        || Math.abs(camYaw - hero.cam) > 0.02) dirty = true;
      if (north && Math.abs(camYaw - hero.cam) > 0.002) {
        north.firstElementChild.style.transform = `rotate(${camYaw}rad)`;
        const turned = Math.abs(Math.atan2(Math.sin(camYaw), Math.cos(camYaw))) > 0.05;
        north.classList.toggle('turned', turned);
      }
      hero = { x: pos.x, z: pos.z, yaw, cam: camYaw };
      if (pings.length) dirty = true;
      const now = performance.now();
      if (dirty && now - last > 80) { draw(); dirty = false; last = now; }
    },
  };
}
