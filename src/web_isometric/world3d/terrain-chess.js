// The Chessboard of Garathorm (the 'chessboard' look, room_looks.py; zone 36). Each room is one
// square of an eight-by-eight board: its whole floor polished white marble or black obsidian (the
// room's name says which), so the rooms laid side by side are the board. The squares open onto each
// other along their whole sides (roomgen.js), with a thin brass inlay between them; round the
// board's edge a marble balustrade with pawn finials and braziers; and beyond each back rank the
// pieces that start there, carved as great statues in their army's stone, facing the board.
// The board's gate (a room of the look that is no square) is a landing of grey marble flanked by
// the two kings.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { cutout } from './cutout.js';
import { chessSquare } from './chesslogic.js';

const WHITE = 0xeeeae2, BLACK = 0x26242c, GREY = 0x9e9a94, BRASS = 0xc8a050, IRON = 0x2e2c30;

// ---- polished marble: a tileable canvas (veins wrap round its edges) of four slabs, 6 m across
function marbleTexture(base, vein, joint, seed) {
  if (typeof document === 'undefined') return null;
  const S = 512, c = document.createElement('canvas');
  c.width = c.height = S;
  const g = c.getContext('2d');
  if (!g) return null;
  const rnd = MH.mulberry32(seed);
  g.fillStyle = base; g.fillRect(0, 0, S, S);
  // soft clouds, then veins: each drawn nine times, shifted a tile's width, so the edges join
  const wrap = draw => { for (const dx of [-S, 0, S]) for (const dy of [-S, 0, S]) { g.save(); g.translate(dx, dy); draw(); g.restore(); } };
  for (let i = 0; i < 10; i++) {
    const x = rnd() * S, y = rnd() * S, r = 80 + rnd() * 160, a = 0.015 + rnd() * 0.025;
    wrap(() => { const gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, `rgba(${vein},${a})`); gr.addColorStop(1, `rgba(${vein},0)`); g.fillStyle = gr; g.fillRect(x - r, y - r, r * 2, r * 2); });
  }
  for (let v = 0; v < 11; v++) {
    let x = rnd() * S, y = rnd() * S, ang = rnd() * Math.PI * 2;
    const pts = [[x, y]];
    for (let i = 0, n = 20 + rnd() * 40; i < n; i++) { ang += (rnd() - 0.5) * 0.8; x += Math.cos(ang) * 10; y += Math.sin(ang) * 10; pts.push([x, y]); }
    const w = 0.6 + rnd() * 1.6, a = 0.12 + rnd() * 0.3;
    wrap(() => { g.strokeStyle = `rgba(${vein},${a})`; g.lineWidth = w; g.beginPath(); pts.forEach(([px, py], i) => i ? g.lineTo(px, py) : g.moveTo(px, py)); g.stroke(); });
  }
  g.strokeStyle = joint; g.lineWidth = 2;
  g.strokeRect(0, 0, S, S);
  g.beginPath(); g.moveTo(S / 2, 0); g.lineTo(S / 2, S); g.moveTo(0, S / 2); g.lineTo(S, S / 2); g.stroke();
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.anisotropy = 4;
  return tex;
}
const floorMat = (color, tex, rough) => new THREE.MeshStandardMaterial({ color, map: tex, roughness: rough, metalness: 0.05 });
const FLOOR_MATS = {
  white: floorMat(0xffffff, marbleTexture('#efebe3', '120,112,104', 'rgba(150,140,128,0.55)', 11), 0.28),
  black: floorMat(0xffffff, marbleTexture('#222028', '190,190,215', 'rgba(0,0,0,0.6)', 23), 0.22),
  gate: floorMat(0xffffff, marbleTexture('#a19d97', '70,66,62', 'rgba(60,56,52,0.5)', 37), 0.35),
};
const BRASS_MAT = new THREE.MeshStandardMaterial({ color: BRASS, roughness: 0.32, metalness: 0.85 });
// the balustrade and the statues stand between the camera and the hero: see-through where they hide him
const STONE_MAT = cutout.apply(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.3, metalness: 0.02 }));

function colored(geo, color) {
  const col = new THREE.Color(color), n = geo.attributes.position.count, a = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { a[i * 3] = col.r; a[i * 3 + 1] = col.g; a[i * 3 + 2] = col.b; }
  geo.setAttribute('color', new THREE.BufferAttribute(a, 3));
  return geo.index ? geo.toNonIndexed() : geo;
}
const box = (w, h, d, x, y, z, color) => colored(new THREE.BoxGeometry(w, h, d).translate(x, y, z), color);
const lathe = (pts, color, seg = 16) => colored(new THREE.LatheGeometry(pts.map(([r, y]) => new THREE.Vector2(r, y)), seg), color);
// a half-circle of profile points (a ball on the profile: a pawn's head, a bishop's mitre)
const arc = (cy, rx, ry, n = 7) => Array.from({ length: n + 1 }, (_, i) => { const a = -Math.PI / 2 + (i / n) * Math.PI; return [Math.max(0.001, Math.cos(a) * rx), cy + Math.sin(a) * ry]; });

// ---- the pieces, a unit tall (to the top of the king's cross), on their own base ----
const BASE = [[0.001, 0], [0.42, 0], [0.42, 0.06], [0.37, 0.1], [0.34, 0.13], [0.34, 0.17], [0.27, 0.21]];
function piece(kind, color) {
  const out = [];
  if (kind === 'pawn') {
    out.push(lathe([...BASE, [0.18, 0.3], [0.12, 0.45], [0.2, 0.5], [0.2, 0.53], [0.1, 0.55], ...arc(0.67, 0.15, 0.14).slice(1)], color));
  } else if (kind === 'rook') {
    out.push(lathe([...BASE, [0.24, 0.28], [0.21, 0.58], [0.3, 0.63], [0.3, 0.78], [0.23, 0.78], [0.23, 0.72], [0.001, 0.72]], color));
    for (let i = 0; i < 4; i++) {
      const a = i * Math.PI / 2 + Math.PI / 4;
      out.push(colored(new THREE.BoxGeometry(0.14, 0.1, 0.09).rotateY(-a).translate(Math.cos(a) * 0.265, 0.83, Math.sin(a) * 0.265), color));
    }
  } else if (kind === 'bishop') {
    out.push(lathe([...BASE, [0.2, 0.3], [0.12, 0.55], [0.22, 0.58], [0.22, 0.61], [0.11, 0.63], ...arc(0.76, 0.15, 0.15).slice(1, 5), [0.08, 0.89], [0.001, 0.94]], color));
    out.push(colored(new THREE.SphereGeometry(0.045, 8, 6).translate(0, 0.96, 0), color));
    // the mitre's slit
    out.push(box(0.02, 0.14, 0.34, 0.06, 0.8, 0, color === WHITE ? 0xb8b2a6 : 0x111014));
  } else if (kind === 'queen' || kind === 'king') {
    out.push(lathe([...BASE, [0.22, 0.3], [0.13, 0.6], [0.26, 0.64], [0.26, 0.67], [0.15, 0.7], [0.21, 0.84], [0.23, 0.86], [0.17, 0.88], [0.001, 0.9]], color));
    if (kind === 'queen') {
      for (let i = 0; i < 8; i++) {
        const a = i * Math.PI / 4;
        out.push(colored(new THREE.SphereGeometry(0.035, 6, 4).translate(Math.cos(a) * 0.2, 0.9, Math.sin(a) * 0.2), BRASS));
      }
      out.push(colored(new THREE.SphereGeometry(0.06, 8, 6).translate(0, 0.95, 0), color));
    } else {
      out.push(box(0.06, 0.16, 0.06, 0, 0.98, 0, BRASS), box(0.16, 0.05, 0.06, 0, 1.0, 0, BRASS));
    }
  } else if (kind === 'knight') {
    out.push(lathe([...BASE, [0.26, 0.26], [0.26, 0.3], [0.001, 0.3]], color));
    // the horse's head: a neck leaning back, the head reaching forward (+z), ears, a mane
    out.push(colored(new THREE.BoxGeometry(0.3, 0.46, 0.34).rotateX(-0.28).translate(0, 0.52, -0.04), color));
    out.push(colored(new THREE.BoxGeometry(0.24, 0.2, 0.44).rotateX(0.5).translate(0, 0.72, 0.13), color));
    out.push(colored(new THREE.BoxGeometry(0.2, 0.13, 0.16).rotateX(0.5).translate(0, 0.6, 0.32), color));
    for (const s of [-1, 1]) out.push(colored(new THREE.ConeGeometry(0.04, 0.13, 4).translate(s * 0.07, 0.88, -0.02), color));
    out.push(box(0.06, 0.48, 0.08, 0, 0.6, -0.22, color === WHITE ? 0xd8d2c6 : 0x18171c));
  }
  return out;
}
const HEIGHT = { pawn: 3.2, rook: 4.0, knight: 4.4, bishop: 4.8, queen: 5.4, king: 5.8 };

// a statue of a piece on a plinth at (x, z), its face turned by yaw
function statue(geos, kind, side, x, z, yaw) {
  const color = side === 'white' ? WHITE : BLACK;
  geos.push(box(2.0, 0.5, 2.0, x, 0.25, z, GREY), box(1.8, 0.08, 1.8, x, 0.54, z, BRASS));
  const s = HEIGHT[kind] || 3;
  for (const g of piece(kind, color)) geos.push(g.scale(s * 0.85, s, s * 0.85).rotateY(yaw).translate(x, 0.58, z));
}

// the room's square: the polished floor, its brass inlay, the balustrade on the board's edge, the
// statues beyond it
export function chessboard(c) {
  const { layout, ox, oz, room, owned, group, torches } = c;
  const { W, H, grid } = layout;
  const BLOCK = 1;
  const at = (x, y) => (x < 0 || y < 0 || x >= W || y >= H) ? BLOCK : grid[y * W + x];
  const name = layout.name || (room && room.name) || '';
  const sq = chessSquare(name);
  const cells = room && room.zoneRef ? room.zoneRef.cells : null;
  const nb = (dx, dy) => !!(cells && cells.get(`${room.cx + dx},${room.cy + dy}`));

  // ---- the floor: one sheet of the square's stone, its texture laid in world space (3 m slabs)
  const floor = new THREE.PlaneGeometry(W, H, 1, 1).rotateX(-Math.PI / 2).translate(ox + W / 2, 0.02, oz + H / 2);
  const uv = floor.attributes.uv, pos = floor.attributes.position;
  for (let i = 0; i < pos.count; i++) uv.setXY(i, pos.getX(i) / 6, -pos.getZ(i) / 6);
  owned.push(floor);
  const fm = new THREE.Mesh(floor, FLOOR_MATS[sq || 'gate']);
  fm.receiveShadow = true;
  group.add(fm);
  // (its edge, down to the paving round the board)
  const lip = new THREE.BoxGeometry(W, 0.3, H).translate(ox + W / 2, -0.14, oz + H / 2);
  owned.push(lip);
  group.add(new THREE.Mesh(lip, FLOOR_MATS[sq || 'gate']));

  // ---- brass between the squares: along its north and west edges (the next square draws its own)
  const inlay = [];
  if (sq) {
    inlay.push(new THREE.BoxGeometry(W, 0.012, 0.08).translate(ox + W / 2, 0.025, oz));
    inlay.push(new THREE.BoxGeometry(0.08, 0.012, H).translate(ox, 0.025, oz + H / 2));
    if (!nb(1, 0)) inlay.push(new THREE.BoxGeometry(0.08, 0.012, H).translate(ox + W, 0.025, oz + H / 2));
    if (!nb(0, 1)) inlay.push(new THREE.BoxGeometry(W, 0.012, 0.08).translate(ox + W / 2, 0.025, oz + H));
  }
  if (inlay.length) {
    const g = mergeGeometries(inlay, false);
    for (const x of inlay) x.dispose();
    owned.push(g);
    group.add(new THREE.Mesh(g, BRASS_MAT));
  }

  // ---- the balustrade: on every stretch of the ring still walled (the board's edge), posts at
  // world-steady spacing (4 m east-west, 3 m north-south) so the next square's posts keep step
  const stone = [];
  const segs = [];
  for (const y of [0, H - 1]) for (let x = 0; x < W;) {
    if (at(x, y) !== BLOCK) { x++; continue; }
    const a = x; while (x < W && at(x, y) === BLOCK) x++;
    segs.push({ horiz: true, line: y, a, b: x - 1 });
  }
  for (const x of [0, W - 1]) for (let y = 0; y < H;) {
    if (at(x, y) !== BLOCK) { y++; continue; }
    const a = y; while (y < H && at(x, y) === BLOCK) y++;
    segs.push({ horiz: false, line: x, a, b: y - 1 });
  }
  // (a lone corner cell is the end of the other side's stretch, not a stretch of its own)
  const long = segs.filter(s => s.b > s.a);
  const inSeg = (horiz, x, y) => long.some(s => s.horiz === horiz && s.line === (horiz ? y : x) && (horiz ? x : y) >= s.a && (horiz ? x : y) <= s.b);
  const posts = new Map();
  for (const s of long) {
    const L = s.b - s.a + 1, mid = (s.a + s.b + 1) / 2, edge = s.line + 0.5;
    const [cx, cz, w, d] = s.horiz ? [ox + mid, oz + edge, L, 0.7] : [ox + edge, oz + mid, 0.7, L];
    stone.push(box(w, 0.3, d, cx, 0.15, cz, 0xd6d0c4));
    stone.push(box(s.horiz ? w : 0.56, 0.12, s.horiz ? 0.56 : d, cx, 1.0, cz, 0xe4dfd4));
    // balusters every half metre
    for (let t = s.a + 0.25; t < s.b + 1; t += 0.5) {
      const [bx, bz] = s.horiz ? [ox + t, oz + edge] : [ox + edge, oz + t];
      stone.push(lathe([[0.001, 0.3], [0.09, 0.3], [0.06, 0.4], [0.11, 0.56], [0.11, 0.62], [0.05, 0.84], [0.08, 0.94], [0.001, 0.94]], 0xe8e3d8, 6).translate(bx, 0, bz));
    }
    for (let t = s.a; t <= s.b; t++) {
      const [x, y] = s.horiz ? [t, s.line] : [s.line, t];
      const steady = s.horiz ? x % 4 === 0 : y % 3 === 0;
      const end = (t === s.a && t > 0) || (t === s.b && t < (s.horiz ? W : H) - 1);
      const corner = (x === 0 || x === W - 1) && (y === 0 || y === H - 1) && inSeg(true, x, y) && inSeg(false, x, y);
      if (steady || end || corner) posts.set(`${x},${y}`, [x, y, end || corner]);
    }
  }
  for (const [x, y, lit] of posts.values()) {
    const px = ox + x + 0.5, pz = oz + y + 0.5;
    stone.push(box(0.8, 1.15, 0.8, px, 0.575, pz, 0xd0cabd), box(0.92, 0.1, 0.92, px, 1.2, pz, 0xe4dfd4));
    // a brazier at the board's corners and either side of its gate, on the rest a pawn in black or
    // white, turn about
    const k = Math.round((ox + x) / 4) + Math.round((oz + y) / 3);
    if (lit) {
      stone.push(lathe([[0.001, 1.25], [0.08, 1.25], [0.05, 1.35], [0.22, 1.45], [0.24, 1.55], [0.001, 1.5]], IRON, 10).translate(px, 0, pz));
      torches.push(new THREE.Vector3(px, 1.72, pz + 0.12));
    } else {
      for (const g of piece('pawn', k % 2 ? WHITE : BLACK)) stone.push(g.scale(0.62, 0.62, 0.62).translate(px, 1.25, pz));
    }
  }

  // ---- the statues: a back-rank square's piece stands beyond the board's edge behind it, in its
  // army's stone, facing the board; the gate is flanked by the two kings
  const home = /home of the (black|white) (king|queen)(?:'s (rook|knight|bishop))?\b/i.exec(layout.description || '');
  if (home) {
    const side = home[1].toLowerCase(), kind = (home[3] || home[2]).toLowerCase();
    const north = !nb(0, -1) ? true : !nb(0, 1) ? false : side === 'black';
    statue(stone, kind, side, ox + W / 2, north ? oz - 2.3 : oz + H + 2.3, north ? 0 : Math.PI);
  } else if (!sq) {
    if (!nb(0, -1)) statue(stone, 'king', 'black', ox + 3, oz - 1.8, 0);
    if (!nb(0, 1)) statue(stone, 'king', 'white', ox + 3, oz + H + 1.8, Math.PI);
  }
  if (stone.length) {
    const g = mergeGeometries(stone, false);
    for (const x of stone) x.dispose();
    if (g) {
      owned.push(g);
      const m = new THREE.Mesh(g, STONE_MAT);
      m.castShadow = m.receiveShadow = true;
      group.add(m);
    }
  }
}
