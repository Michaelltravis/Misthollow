// How a room looks when its words say what it is (Push 33): the server reads each room's name,
// description and neighbours and gives it a look (room_looks.py), and terrain.js draws by it.
//  - cave:  rock for walls (every wall and rubble cell a boulder pile, darkened), stalagmites
//           rising from the rock's foot, a fringe of stalactites along the tops of the walls,
//           glowing crystals and mushrooms
//  - mine:  cave rock, plus timber frames along the walls, rails down the main way, lanterns
//           on the posts, ore glinting in the rock
//  - crypt: (stone hall) coffins and sarcophagi for obstacles, bones, skulls and skull-candles
//           for props, cobwebs in the corners
//  - sewer: (stone hall) a channel of foul water with stone rims, pipes in the walls
//  - dungeon: (stone hall) broken walls and rubble
//  - outdoors: desert (cacti, bleached bones), snow (frosted pines, ice), shore (driftwood,
//           pebbles), volcanic (scorched trees, lava cracks), web (a spider's lair: grey webbed trees,
//           sheets of web, hanging cocoons, egg sacs and old bones)
// Everything placed on the floor that should stop the hero is written into the room's grid as
// BLOCK (the server never sees it: it is scenery, like furniture).
import * as THREE from 'three';
import { trs } from './assets.js';
import { menhir } from './terrain-features.js';
import { PLACES, placeEdge, dressPlace } from './terrain-places.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const FLOOR = 0, BLOCK = 1, WATER = 4;
// (an ice cave and a lava cave are caves: Below Moria's Freezer, the Tunnel to Hell, a glacier's crack)
export const UNDERGROUND = new Set(['cave', 'mine', 'ice_cave', 'lava_cave']);

// a model with its materials darkened or tinted (cached by name+tint)
const tintCache = new Map();
export function tinted(model, color, key, opts = {}) {
  if (!model) return model;
  const name = `${model.name}#${key}`;
  let t = tintCache.get(name);
  if (!t) {
    const c = new THREE.Color(color);
    const mat = m => {
      const n = m.clone();
      if (n.color) n.color.multiply(c);
      if (opts.emissive) { n.emissive = new THREE.Color(opts.emissive); n.emissiveIntensity = opts.glow || 1; }
      return n;
    };
    t = { name, box: model.box, parts: model.parts.map(p => ({ geometry: p.geometry, material: Array.isArray(p.material) ? p.material.map(mat) : mat(p.material) })) };
    tintCache.set(name, t);
  }
  return t;
}
const heightOf = model => { const s = new THREE.Vector3(); model.box.getSize(s); return Math.max(0.01, s.y); };

const STONE_MAT = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, metalness: 0 });
const PLANT_MAT = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, metalness: 0 });
const WOOD_MAT = new THREE.MeshStandardMaterial({ color: 0x5a3e24, roughness: 0.9 });
const IRON_MAT = new THREE.MeshStandardMaterial({ color: 0x3a3a3e, roughness: 0.5, metalness: 0.75 });
const CRYSTAL_MATS = {
  cave: new THREE.MeshBasicMaterial({ color: new THREE.Color(0.9, 2.4, 3.8) }),
  mine: new THREE.MeshBasicMaterial({ color: new THREE.Color(2.4, 1.7, 0.5) }),
  lava: new THREE.MeshBasicMaterial({ color: new THREE.Color(1.7, 0.36, 0.03) }),
};
const SEWER_WATER = new THREE.MeshStandardMaterial({ color: 0x2e3a1c, roughness: 0.55, metalness: 0.05, transparent: true, opacity: 0.94 });
// a sewer's dirt: black standing water, grime, green slime down the walls, water from the pipes
const PUDDLE_MAT = new THREE.MeshStandardMaterial({ color: 0x14180f, roughness: 0.06, metalness: 0.35, transparent: true, opacity: 0.85,
  polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
const GRIME_MAT = new THREE.MeshStandardMaterial({ color: 0x1e1a10, roughness: 1, transparent: true, opacity: 0.55, depthWrite: false,
  polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 });
const SLIME_MAT = new THREE.MeshStandardMaterial({ color: 0x4a6a1e, emissive: 0x0e1a04, roughness: 0.3, transparent: true, opacity: 0.6,
  depthWrite: false, side: THREE.DoubleSide });
const DRIP_MAT = new THREE.MeshStandardMaterial({ color: 0x6a7a58, roughness: 0.1, metalness: 0.1, transparent: true, opacity: 0.55, depthWrite: false });
const ICE_MAT = new THREE.MeshStandardMaterial({ color: 0xcfe8ff, roughness: 0.08, metalness: 0.1, transparent: true, opacity: 0.7,
  polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
export const WEB_MAT = (() => {
  if (typeof document === 'undefined') return null;
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d');
  g.strokeStyle = 'rgba(230,230,240,0.75)'; g.lineWidth = 1.2;
  for (let i = 0; i < 9; i++) { const a = (i / 8) * Math.PI / 2; g.beginPath(); g.moveTo(0, 0); g.lineTo(Math.cos(a) * 128, Math.sin(a) * 128); g.stroke(); }
  for (let r = 18; r < 128; r += 18) { g.beginPath(); for (let i = 0; i <= 8; i++) { const a = (i / 8) * Math.PI / 2, rr = r + (i % 2 ? -3 : 3); i ? g.lineTo(Math.cos(a) * rr, Math.sin(a) * rr) : g.moveTo(Math.cos(a) * rr, Math.sin(a) * rr); } g.stroke(); }
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  return new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, side: THREE.DoubleSide });
})();

// merged procedural pieces of one material, as one mesh owned by the room
function addMerged(c, geos, material, { shadow = true } = {}) {
  if (!geos.length) return null;
  const g = mergeGeometries(geos, false);
  for (const x of geos) x.dispose();
  if (!g) return null;
  c.owned.push(g);
  const m = new THREE.Mesh(g, material);
  m.castShadow = shadow; m.receiveShadow = true;
  c.group.add(m);
  return m;
}
function colored(geo, color) {
  const col = new THREE.Color(color), n = geo.attributes.position.count, a = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { a[i * 3] = col.r; a[i * 3 + 1] = col.g; a[i * 3 + 2] = col.b; }
  geo.setAttribute('color', new THREE.BufferAttribute(a, 3));
  return geo;
}
function lane(layout) {
  const { W, H, gaps } = layout;
  const mx = Math.floor(W / 2), my = Math.floor(H / 2);
  return (x, y) => ((gaps.north || gaps.south) && Math.abs(x - mx) <= 3) || ((gaps.east || gaps.west) && Math.abs(y - my) <= 2);
}
// floor cells next to a BLOCK cell (where the rock meets the floor)
function rockFoot(layout) {
  const { W, H, grid } = layout, out = [];
  const at = (x, y) => (x < 0 || y < 0 || x >= W || y >= H) ? BLOCK : grid[y * W + x];
  for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
    if (at(x, y) !== FLOOR) continue;
    if (at(x + 1, y) === BLOCK || at(x - 1, y) === BLOCK || at(x, y + 1) === BLOCK || at(x, y - 1) === BLOCK) out.push([x, y]);
  }
  return out;
}

// ---------------------------------------------------------------- caves and mines
export function underground(c, look) {
  const { layout, ox, oz, kits, b, rng, occ } = c;
  const { W, H, grid } = layout;
  const N = kits.nature, D = kits.dungeon;
  const at = (x, y) => (x < 0 || y < 0 || x >= W || y >= H) ? BLOCK : grid[y * W + x];
  // the kit's rock is dark and mossy: lifted (a tint above 1) to a pale grey stone, warmer in a mine
  const rockTint = look === 'mine' ? new THREE.Color(1.55, 1.35, 1.15) : look === 'ice_cave' ? new THREE.Color(1.45, 1.62, 1.95)
    : look === 'lava_cave' ? new THREE.Color(0.62, 0.5, 0.46) : new THREE.Color(1.5, 1.48, 1.62);
  const ice = look === 'ice_cave', fire = look === 'lava_cave';
  const rocks = [1, 2, 3].map(i => tinted(N.get(`Rock_Medium_${i}`), rockTint, `${look}rock`)).filter(Boolean);
  // the walls: a boulder pile on every BLOCK cell, tall on the room's edge, lower inside
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (at(x, y) !== BLOCK) continue;
    const edge = x === 0 || y === 0 || x === W - 1 || y === H - 1;
    const rock = rocks[Math.floor(rng() * rocks.length)];
    if (!rock) continue;
    const want = edge ? 2.2 + rng() * 1.4 : 0.9 + rng() * 0.9;
    const s = want / heightOf(rock);
    b.add(occ(rock), trs(ox + x + 0.5 + (rng() - 0.5) * 0.3, -0.1, oz + y + 0.5 + (rng() - 0.5) * 0.3, rng() * 6.28, s * (0.9 + rng() * 0.3), s, s * (0.9 + rng() * 0.3)));
  }
  const stone = [];
  // stalagmites at the rock's foot (they stand in the rock's cell, so the floor stays clear)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (at(x, y) !== BLOCK || rng() > (look === 'cave' || ice ? 0.3 : 0.12)) continue;
    const near = [[1, 0], [-1, 0], [0, 1], [0, -1]].find(([dx, dy]) => at(x + dx, y + dy) === FLOOR);
    if (!near) continue;
    const h = 0.6 + rng() * 1.3, r = 0.12 + rng() * 0.16;
    const g = new THREE.ConeGeometry(r, h, 6);
    g.translate(ox + x + 0.5 + near[0] * 0.45, h / 2, oz + y + 0.5 + near[1] * 0.45);
    stone.push(colored(g, ice ? (rng() < 0.5 ? 0xd6ecf8 : 0xb8d8ec) : fire ? 0x2a2220 : rng() < 0.5 ? 0x6a6258 : 0x585058));
  }
  // stalactites: a fringe hanging from the tops of the walls, leaning into the room
  for (const run of c.runs) {
    for (let i = run.a; i <= run.b; i++) {
      if (rng() > 0.55) continue;
      const h = 0.5 + rng() * 1.1, r = 0.1 + rng() * 0.14;
      const g = new THREE.ConeGeometry(r, h, 5);
      g.rotateX(Math.PI);
      const inset = 0.95;
      const [x, z] = run.horiz
        ? [ox + i + 0.5, oz + run.line + 0.5 + (run.line === 0 ? inset : -inset)]
        : [ox + run.line + 0.5 + (run.line === 0 ? inset : -inset), oz + i + 0.5];
      g.translate(x, 2.9 - h / 2, z);
      stone.push(colored(g, ice ? 0xe4f2fc : fire ? 0x241c18 : 0x5c5650));     // icicles in an ice cave
    }
  }
  addMerged(c, stone, STONE_MAT);
  // glowing crystals (a cave) or ore (a mine) in the rock, mushrooms at its foot
  const glow = [];
  for (const [x, y] of rockFoot(layout)) {
    const r = rng();
    if (r < (look === 'cave' ? 0.07 : 0.05)) {
      for (let k = 0; k < 3; k++) {
        const g = new THREE.OctahedronGeometry(0.08 + rng() * 0.12, 0);
        g.scale(1, 2.2, 1);
        g.rotateZ((rng() - 0.5) * 0.9);
        g.translate(ox + x + 0.5 + (rng() - 0.5) * 0.6, 0.15 + rng() * 0.3, oz + y + 0.5 + (rng() - 0.5) * 0.6);
        glow.push(g);
      }
    } else if (look === 'cave' && r < 0.16 && N.get('Mushroom_Common')) {
      b.add(tinted(N.get('Mushroom_Common'), 0xa0c8ff, 'glowshroom', { emissive: 0x4a8ae0, glow: 2.2 }),
        trs(ox + x + 0.5, 0, oz + y + 0.5, rng() * 6.28, 0.9 + rng() * 0.6), { shadow: false });
    } else if (r < 0.24 && N.get('Pebble_Round_1')) {
      b.add(tinted(N.get('Pebble_Round_1'), rockTint, `${look}peb`), trs(ox + x + 0.3 + rng() * 0.4, 0, oz + y + 0.3 + rng() * 0.4, rng() * 6.28, 1.2 + rng()), { shadow: false });
    }
  }
  // a lava cave: glowing cracks across its floor (merged on their own: boxes are indexed, the
  // crystals not)
  const cracks = [];
  if (fire) {
    for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
      if (at(x, y) !== FLOOR || rng() > 0.08) continue;
      let cx = ox + x + 0.2 + rng() * 0.6, cz = oz + y + 0.2 + rng() * 0.6, a = rng() * 6.28;
      for (let k = 0; k < 3 + Math.floor(rng() * 3); k++) {
        const len = 0.35 + rng() * 0.5;
        const g = new THREE.BoxGeometry(len, 0.03, 0.08 + rng() * 0.07);
        g.rotateY(-a); g.translate(cx + Math.cos(a) * len / 2, 0.02, cz + Math.sin(a) * len / 2); cracks.push(g);
        cx += Math.cos(a) * len; cz += Math.sin(a) * len; a += (rng() - 0.5) * 1.6;
      }
    }
  }
  // an ice cave: the floor glazed in sheets of ice
  if (ice) {
    const sheets = [];
    for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) if (at(x, y) === FLOOR && rng() < 0.18) sheets.push([x, y]);
    if (sheets.length) {
      const geo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
      c.owned.push(geo);
      const im = new THREE.InstancedMesh(geo, ICE_MAT, sheets.length);
      sheets.forEach(([x, y], i) => im.setMatrixAt(i, trs(ox + x + 0.5, 0.02, oz + y + 0.5, 0, 1)));
      c.group.add(im);
    }
  }
  addMerged(c, glow, CRYSTAL_MATS[ice ? 'cave' : fire ? 'lava' : look] || CRYSTAL_MATS.cave, { shadow: false });
  if (cracks.length) addMerged(c, cracks, CRYSTAL_MATS.lava, { shadow: false });
  if (look === 'mine') mineWorks(c);
  else if (D) {
    // torches along the rock where others have passed, spread out (four, to keep it readable)
    const foot = rockFoot(layout).filter(([x, y]) => !lane(layout)(x, y)).sort((p, q) => p[0] - q[0]);
    const n = Math.min(4, foot.length);
    for (let i = 0; i < n; i++) {
      const [x, y] = foot[Math.floor(((i + 0.2 + rng() * 0.6) / n) * foot.length)];
      b.add(D.get('torch_lit'), trs(ox + x + 0.5, 0.4, oz + y + 0.5, 0, 1.3), { shadow: false });
      c.torches.push(new THREE.Vector3(ox + x + 0.5, 1.4, oz + y + 0.5));
    }
  }
}

// a mine: timber frames along the walls, rails along the main way, lanterns on the posts
function mineWorks(c) {
  const { layout, ox, oz, kits, b, rng } = c;
  const { W, H, gaps } = layout;
  const D = kits.dungeon;
  const wood = [], iron = [];
  const post = (x, z) => { const g = new THREE.BoxGeometry(0.22, 2.5, 0.22); g.translate(x, 1.25, z); wood.push(g); };
  // frames every ~5 m along the north and south walls, a beam across their tops
  for (let x = 3; x < W - 3; x += 5) {
    for (const [y, dz] of [[1, 0.2], [H - 2, -0.2]]) {
      if (layout.grid[y * W + x] !== FLOOR) continue;
      post(ox + x + 0.2, oz + y + 0.5 + dz);
      const beam = new THREE.BoxGeometry(1.6, 0.22, 0.26); beam.translate(ox + x + 0.2, 2.45, oz + y + 0.5 + dz); wood.push(beam);
      if (D && rng() < 0.6) {
        b.add(D.get('torch_lit'), trs(ox + x + 0.2, 1.6, oz + y + 0.5 + dz * 2.5, 0, 1.1), { shadow: false });
        c.torches.push(new THREE.Vector3(ox + x + 0.2, 2.5, oz + y + 0.5 + dz * 2.5));
      }
    }
  }
  // rails down the long way through (east-west if there is one), on sleepers
  const mx = Math.floor(W / 2), my = Math.floor(H / 2);
  if (gaps.east || gaps.west) {
    for (let x = 0; x < W; x++) {
      const s = new THREE.BoxGeometry(0.22, 0.06, 1.3); s.translate(ox + x + 0.5, 0.03, oz + my + 0.5); wood.push(s);
    }
    for (const dz of [-0.4, 0.4]) { const r = new THREE.BoxGeometry(W, 0.07, 0.07); r.translate(ox + W / 2, 0.09, oz + my + 0.5 + dz); iron.push(r); }
  } else if (gaps.north || gaps.south) {
    for (let y = 0; y < H; y++) {
      const s = new THREE.BoxGeometry(1.3, 0.06, 0.22); s.translate(ox + mx + 0.5, 0.03, oz + y + 0.5); wood.push(s);
    }
    for (const dx of [-0.4, 0.4]) { const r = new THREE.BoxGeometry(0.07, 0.07, H); r.translate(ox + mx + 0.5 + dx, 0.09, oz + H / 2); iron.push(r); }
  }
  addMerged(c, wood, WOOD_MAT);
  addMerged(c, iron, IRON_MAT);
  // an ore cart or crates by the rails
  if (D) for (let i = 0; i < 2; i++) {
    const x = 3 + Math.floor(rng() * (W - 6)), y = 2 + Math.floor(rng() * (H - 4));
    if (layout.grid[y * W + x] !== FLOOR || lane(layout)(x, y)) continue;
    b.add(D.get(rng() < 0.5 ? 'crates_stacked' : 'barrel_large'), trs(ox + x + 0.5, 0, oz + y + 0.5, rng() * 6.28, 0.8));
    layout.grid[y * W + x] = BLOCK;
  }
}

// ---------------------------------------------------------------- stone halls
// what replaces the plain interior's crates and candles; returns true when it dressed the room
export function dressHall(c, theme) {
  if (theme === 'crypt') return crypt(c);
  if (theme === 'sewer') return sewer(c);
  return false;
}

function crypt(c) {
  const { layout, ox, oz, kits, b, rng, occ } = c;
  const G = kits.graveyard, D = kits.dungeon;
  if (!G) return false;
  const { W, H, grid } = layout;
  const ln = lane(layout);
  // coffins on the obstacles and in rows along the walls
  for (const o of layout.obstacles || []) {
    const key = o.big ? (rng() < 0.5 ? 'coffin_decorated' : 'coffin') : ['bone_A', 'skull', 'ribcage'][Math.floor(rng() * 3)];
    b.add(o.big ? occ(G.get(key)) : G.get(key), trs(ox + o.x + (o.big ? 1 : 0.5), 0, oz + o.y + (o.big ? 1 : 0.5), Math.floor(rng() * 4) * Math.PI / 2, o.big ? 0.75 : 0.6));
  }
  for (let x = 3; x < W - 3; x += 3) {
    for (const y of [2, H - 3]) {
      if (grid[y * W + x] !== FLOOR || ln(x, y) || rng() < 0.35) continue;
      b.add(occ(G.get(rng() < 0.3 ? 'coffin_decorated' : 'coffin')), trs(ox + x + 0.5, 0, oz + y + 0.5, Math.PI / 2, 0.6));
      grid[y * W + x] = BLOCK;
    }
  }
  // bones, skulls and skull-candles on the floor; candles light it
  for (const p of layout.props || []) {
    const key = ['skull_candle', 'bone_B', 'bone_C', 'skull', 'skull_candle'][Math.floor(rng() * 5)];
    b.add(G.get(key), trs(ox + p.x + 0.5, 0, oz + p.y + 0.5, rng() * 6.28, 0.7), { shadow: false });
    if (key === 'skull_candle') c.torches.push(new THREE.Vector3(ox + p.x + 0.5, 0.6, oz + p.y + 0.5));
  }
  // cobwebs in the corners
  if (WEB_MAT) for (const [cx, cz, yaw] of [[1, 1, 0], [W - 1, 1, -Math.PI / 2], [1, H - 1, Math.PI / 2], [W - 1, H - 1, Math.PI]]) {
    if (rng() < 0.3) continue;
    const g = new THREE.PlaneGeometry(1.6, 1.6);
    g.translate(0.8, -0.8, 0); g.rotateY(Math.PI / 4); g.rotateY(yaw);
    g.translate(ox + cx, 2.55, oz + cz);
    c.owned.push(g);
    const m = new THREE.Mesh(g, WEB_MAT);
    c.group.add(m);
  }
  return true;
}

function sewer(c) {
  const { layout, ox, oz, kits, b, rng } = c;
  const { W, H, grid } = layout;
  const D = kits.dungeon;
  // the channel's water, a little below the walkways, with stone rims along it
  const cells = [];
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (grid[y * W + x] === WATER) cells.push([x, y]);
  if (cells.length) {
    const geo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
    c.owned.push(geo);
    const wm = new THREE.InstancedMesh(geo, SEWER_WATER, cells.length);
    cells.forEach(([x, y], i) => wm.setMatrixAt(i, trs(ox + x + 0.5, -0.22, oz + y + 0.5, 0, 1.02)));
    wm.receiveShadow = true;
    c.group.add(wm);
    const rim = [];
    for (const [x, y] of cells) for (const dy of [-1, 1]) {
      if (grid[(y + dy) * W + x] === WATER) continue;
      const g = new THREE.BoxGeometry(1, 0.12, 0.18); g.translate(ox + x + 0.5, 0.0, oz + y + 0.5 + dy * 0.5);
      rim.push(colored(g, 0x5a564e));
      const wall = new THREE.BoxGeometry(1, 0.5, 0.06); wall.translate(ox + x + 0.5, -0.25, oz + y + 0.5 + dy * 0.47);
      rim.push(colored(wall, 0x2e2c28));
    }
    addMerged(c, rim, STONE_MAT, { shadow: false });
  }
  // pipes out of the north wall, dribbling into the channel
  const pipes = [];
  for (let x = 3; x < W - 3; x += 6) {
    if (rng() < 0.3) continue;
    const g = new THREE.CylinderGeometry(0.18, 0.18, 0.9, 10); g.rotateX(Math.PI / 2); g.translate(ox + x + 0.5, 1.1, oz + 0.9);
    pipes.push(g);
  }
  // pipes along the side walls too, and an iron drainpipe or two down the north wall
  for (let y = 3; y < H - 3; y += 5) {
    if (rng() < 0.45) continue;
    for (const [wx, dir] of [[0.9, 1], [W - 0.9, -1]]) {
      if (rng() < 0.5) continue;
      const g = new THREE.CylinderGeometry(0.14, 0.14, 0.8, 8); g.rotateZ(Math.PI / 2); g.translate(ox + wx, 0.9 + rng() * 0.5, oz + y + 0.5);
      pipes.push(g);
    }
  }
  for (let x = 6; x < W - 4; x += 9) {
    if (rng() < 0.5) continue;
    const g = new THREE.CylinderGeometry(0.1, 0.1, 2.4, 8); g.translate(ox + x + 0.5, 1.2, oz + 0.75);
    pipes.push(g);
  }
  addMerged(c, pipes, IRON_MAT);
  // what makes a sewer a sewer: black puddles and grime on the walkways, iron drain grates, slime
  // streaking down the walls and water dribbling from the pipes into the channel
  const floor = [];
  for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) if (grid[y * W + x] === FLOOR) floor.push([x, y]);
  const puddles = [], grime = [], grates = [], slime = [], drips = [];
  for (const [x, y] of floor) {
    const r = rng();
    if (r < 0.07) {
      const g = new THREE.CircleGeometry(0.35 + rng() * 0.45, 12); g.rotateX(-Math.PI / 2);
      g.scale(1, 1, 0.55 + rng() * 0.4); g.rotateY(rng() * 3.14); g.translate(ox + x + 0.5, 0.012, oz + y + 0.5);
      puddles.push(g);
    } else if (r < 0.15) {
      const g = new THREE.CircleGeometry(0.3 + rng() * 0.6, 10); g.rotateX(-Math.PI / 2);
      g.scale(1, 1, 0.5 + rng() * 0.5); g.rotateY(rng() * 3.14); g.translate(ox + x + 0.5, 0.01, oz + y + 0.5);
      grime.push(g);
    } else if (r < 0.165 && grates.length < 3) {
      const base = new THREE.BoxGeometry(0.8, 0.03, 0.8); base.translate(ox + x + 0.5, 0.015, oz + y + 0.5);
      grates.push(base);
      for (let i = -1; i <= 1; i++) {
        const bar = new THREE.BoxGeometry(0.06, 0.05, 0.78); bar.translate(ox + x + 0.5 + i * 0.22, 0.04, oz + y + 0.5);
        grates.push(bar);
      }
    }
  }
  for (let x = 1; x < W - 1; x++) {
    if (grid[W + x] !== FLOOR || rng() < 0.6) continue;
    const g = new THREE.PlaneGeometry(0.35 + rng() * 0.4, 1.4 + rng() * 1.2); g.translate(ox + x + 0.5, 0.9 + rng() * 0.4, oz + 1.02);
    slime.push(g);
  }
  for (const pg of pipes.slice(0, 4)) {
    pg.computeBoundingBox();
    const bb = pg.boundingBox, cx = (bb.min.x + bb.max.x) / 2, cz = bb.max.z + 0.05, top = bb.min.y;
    if (top < 0.6) continue;
    const g = new THREE.CylinderGeometry(0.03, 0.05, top + 0.2, 6); g.translate(cx, (top - 0.2) / 2, cz);
    drips.push(g);
  }
  if (puddles.length) addMerged(c, puddles, PUDDLE_MAT, { shadow: false });
  if (grime.length) addMerged(c, grime, GRIME_MAT, { shadow: false });
  if (grates.length) addMerged(c, grates, IRON_MAT, { shadow: false });
  if (slime.length) addMerged(c, slime, SLIME_MAT, { shadow: false });
  if (drips.length) addMerged(c, drips, DRIP_MAT, { shadow: false });
  // weeds and puddles on the walkways, a lamp or two
  for (const p of layout.props || []) {
    if (D && rng() < 0.3) { b.add(D.get('torch_lit'), trs(ox + p.x + 0.5, 0.4, oz + p.y + 0.5, 0, 1.2), { shadow: false }); c.torches.push(new THREE.Vector3(ox + p.x + 0.5, 1.4, oz + p.y + 0.5)); }
    else if (D) b.add(D.get('barrel_small'), trs(ox + p.x + 0.5, 0, oz + p.y + 0.5, rng() * 6.28, 0.7));
  }
  return true;
}

// ---------------------------------------------------------------- open country
// what grows (or lies) on an outdoor look's edges: [key, kit, tint] lists by look
export function outdoorEdge(theme, kits, layout) {
  const N = kits.nature, G = kits.graveyard;
  // a village, a camp, a garden, ruins (terrain-places.js)
  if (PLACES.has(theme)) return { ...placeEdge(theme, kits, layout), rock: k => N.get(k), bush: null };
  if (theme === 'snow') return { trees: ['Pine_1', 'Pine_2'].map(k => tinted(N.get(k), 0xdfe8f0, 'frost')), treeP: 0.35, rock: k => tinted(N.get(k), 0xe8eef4, 'snowrock'), bush: null };
  if (theme === 'volcanic') return { trees: ['DeadTree_1', 'DeadTree_2'].map(k => tinted(N.get(k), 0x2a2420, 'scorch')), treeP: 0.12, rock: k => tinted(N.get(k), 0x3a302c, 'basalt'), bush: null };
  if (theme === 'web') return { trees: ['DeadTree_1', 'DeadTree_2', 'TwistedTree_1', 'DeadTree_1'].map(k => tinted(N.get(k), 0xa4a496, 'webbed')).filter(Boolean), treeP: 0.7, rock: k => tinted(N.get(k), 0x5a5648, 'lairrock'), bush: null };
  if (theme === 'shore') return { trees: [], treeP: 0, rock: k => N.get(k), bush: null };
  // a stone circle (the Stone Circle of the Raven Clans): standing stones ring the open turf, grey
  // boulders between them, a lone pine or two
  if (theme === 'stones') return { trees: [menhir(0), menhir(1), menhir(2), menhir(0), menhir(1), N.get('Pine_2')], treeP: 0.32, rock: k => tinted(N.get(k), MOUNTAIN_ROCK, 'mtnrock'), bush: null };
  if (theme === 'desert') return { trees: [], treeP: 0, rock: k => tinted(N.get(k), 0xffc890, 'sandstone'), bush: null };
  if (theme === 'water_swim' || theme === 'water_noswim') return { trees: ['CommonTree_1', 'CommonTree_3', 'Pine_1'].map(k => N.get(k)), treeP: 0.18, rock: k => N.get(k), bush: null, banks: true };
  if (theme === 'mountain') return { trees: ['Pine_1', 'Pine_2'].map(k => tinted(N.get(k), 0x8aa08a, 'alpine')), treeP: 0.12, rock: k => tinted(N.get(k), MOUNTAIN_ROCK, 'mtnrock'), bush: null, cliffs: true };
  // under the sea (Atal'narath): tall dark kelp for trees, blue-grey rock, no grass
  if (theme === 'underwater') return { trees: [kelp(0), kelp(1), kelp(2), kelp(1)], treeP: 0.45, rock: k => tinted(N.get(k), SEA_ROCK, 'searock'), bush: null };
  return null;
}

// kelp: a few tall swaying stalks with ribbon leaves, built here (the kit has no sea plants; its
// pines tinted green read as a forest on dry land)
const KELP_MAT = new THREE.MeshStandardMaterial({ color: 0x4a7a3a, emissive: 0x0c2410, roughness: 0.7, side: THREE.DoubleSide, flatShading: true });
const kelpCache = new Map();
function kelp(v) {
  if (kelpCache.has(v)) return kelpCache.get(v);
  const parts = [];
  const stalks = 3 + v;
  for (let s = 0; s < stalks; s++) {
    const h = 3.2 + ((s * 37 + v * 11) % 10) / 6, ox = Math.cos(s * 2.4 + v) * 0.35, oz = Math.sin(s * 2.4 + v) * 0.35;
    for (let k = 0; k < 6; k++) {
      const y0 = (k / 6) * h, seg = h / 6, sway = Math.sin(k * 0.9 + s) * 0.18;
      parts.push({ geometry: new THREE.CylinderGeometry(0.035, 0.05, seg, 5).translate(ox + sway, y0 + seg / 2, oz), material: KELP_MAT });
      parts.push({ geometry: new THREE.PlaneGeometry(0.18, 0.55).rotateZ(0.6 * (k % 2 ? 1 : -1)).rotateY(s + k).translate(ox + sway, y0 + seg * 0.7, oz), material: KELP_MAT });
    }
  }
  const box = new THREE.Box3();
  for (const p of parts) { p.geometry.computeBoundingBox(); box.union(p.geometry.boundingBox); }
  const m = { name: `kelp${v}`, box, parts };
  kelpCache.set(v, m);
  return m;
}
// rising bubbles and light falling from the surface far above
const BUBBLE_MAT = new THREE.MeshStandardMaterial({ color: 0xd8f4ff, emissive: 0x2a5a6a, roughness: 0.1, transparent: true, opacity: 0.55, depthWrite: false });
const SEA_SHAFT = new THREE.MeshBasicMaterial({ color: 0x9ae8ff, transparent: true, opacity: 0.09, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });

// under the sea: the kit's dark rock lifted to a pale blue-grey; coral bright, faintly glowing
const SEA_ROCK = new THREE.Color(1.15, 1.35, 1.5);
const CORAL = [[new THREE.Color(2.6, 1.0, 0.75), 0x401008], [new THREE.Color(1.9, 1.0, 2.6), 0x240a30], [new THREE.Color(2.6, 1.8, 0.6), 0x302008]];
// a mountain's rock: the kit's dark mossy rock lifted to a weathered grey-brown
const MOUNTAIN_ROCK = new THREE.Color(1.35, 1.28, 1.22);

// a mountain: its walls are cliffs (every BLOCK cell a boulder pile, tall at the room's edge and
// lower inside, under open sky), with a hardy pine here and there in the clefts
export function mountainCliffs(c) {
  const { layout, ox, oz, kits, b, rng, occ } = c;
  const { W, H, grid } = layout;
  const N = kits.nature;
  const at = (x, y) => (x < 0 || y < 0 || x >= W || y >= H) ? BLOCK : grid[y * W + x];
  const rocks = [1, 2, 3].map(i => tinted(N.get(`Rock_Medium_${i}`), MOUNTAIN_ROCK, 'mtnrock')).filter(Boolean);
  const pines = ['Pine_1', 'Pine_2'].map(k => tinted(N.get(k), 0x8aa08a, 'alpine')).filter(Boolean);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (at(x, y) !== BLOCK) continue;
    const edge = x === 0 || y === 0 || x === W - 1 || y === H - 1;
    const px = ox + x + 0.5 + (rng() - 0.5) * 0.4, pz = oz + y + 0.5 + (rng() - 0.5) * 0.4;
    if (!edge && pines.length && rng() < 0.18) {
      b.add(occ(pines[Math.floor(rng() * pines.length)]), trs(px, 0, pz, rng() * 6.28, 0.45 + rng() * 0.25));
      continue;
    }
    const rock = rocks[Math.floor(rng() * rocks.length)];
    if (!rock) continue;
    const want = edge ? 2.6 + rng() * 2.0 : 0.9 + rng() * 1.1;
    const s = want / heightOf(rock);
    b.add(occ(rock), trs(px, -0.1, pz, rng() * 6.28, s * (0.9 + rng() * 0.35), s, s * (0.9 + rng() * 0.35)));
  }
}

// scattered on the open ground of an outdoor look (instead of grass and flowers)
export function outdoorDress(c, theme) {
  const { layout, ox, oz, kits, b, rng } = c;
  const { W, H, grid } = layout;
  const N = kits.nature, G = kits.graveyard;
  const ln = lane(layout);
  if (PLACES.has(theme)) { dressPlace(c, theme, ln); return; }
  const solid = [], glow = [];
  for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
    if (grid[y * W + x] !== FLOOR) continue;
    const r = rng(), px = ox + x + 0.2 + rng() * 0.6, pz = oz + y + 0.2 + rng() * 0.6, yaw = rng() * 6.28;
    if (theme === 'desert') {
      if (!ln(x, y) && r < 0.025) { cactus(solid, px, pz, rng); grid[y * W + x] = BLOCK; }
      else if (r < 0.04 && G) b.add(tinted(G.get(rng() < 0.5 ? 'bone_A' : 'skull'), 0xf4ecd8, 'bleached'), trs(px, 0, pz, yaw, 0.6), { shadow: false });
      else if (r < 0.07) b.add(tinted(N.get('Pebble_Round_3'), 0xe0c8a0, 'sandpeb'), trs(px, 0, pz, yaw, 1.3), { shadow: false });
    } else if (theme === 'shore') {
      if (r < 0.05) b.add(N.get(rng() < 0.5 ? 'Pebble_Round_1' : 'Pebble_Round_3'), trs(px, 0, pz, yaw, 1.4), { shadow: false });
      else if (!ln(x, y) && r < 0.065) driftwood(solid, px, pz, yaw, rng);
    } else if (theme === 'mountain') {
      // scree and the odd boulder
      if (r < 0.07) b.add(tinted(N.get(rng() < 0.5 ? 'Pebble_Round_1' : 'Pebble_Round_3'), MOUNTAIN_ROCK, 'mtnpeb'), trs(px, 0, pz, yaw, 1.2 + rng()), { shadow: false });
      else if (!ln(x, y) && r < 0.085) b.add(tinted(N.get('Rock_Medium_' + (1 + Math.floor(rng() * 3))), MOUNTAIN_ROCK, 'mtnrock'), trs(px, 0, pz, yaw, 0.3 + rng() * 0.2));
    } else if (theme === 'underwater') {
      // the seabed: coral in three colours, sea fans, shells; nothing stands on the ways through
      const k = Math.floor(rng() * 3), [cc, ce] = CORAL[k];
      if (!ln(x, y) && r < 0.05) b.add(tinted(N.get('Bush_Common'), cc, `coral${k}`, { emissive: ce, glow: 1 }), trs(px, 0, pz, yaw, 0.55 + rng() * 0.5), { shadow: false });
      else if (!ln(x, y) && r < 0.08) b.add(tinted(N.get('Fern_1'), new THREE.Color(0.9, 2.2, 2.0), 'seafan'), trs(px, 0, pz, yaw, 0.9 + rng() * 0.5), { shadow: false });
      else if (r < 0.105) b.add(tinted(N.get('Pebble_Round_3'), new THREE.Color(2.2, 1.9, 1.7), 'shell'), trs(px, 0, pz, yaw, 1.1), { shadow: false });
    } else if (theme === 'stones') {
      // short moor grass, tall tufts, grey pebbles; only pebbles on the ways through
      if (ln(x, y)) { if (r < 0.06) b.add(tinted(N.get('Pebble_Round_1'), MOUNTAIN_ROCK, 'mtnpeb'), trs(px, 0, pz, yaw, 1.2), { shadow: false }); }
      else if (r < 0.22) b.add(N.get('Grass_Common_Short'), trs(px, 0, pz, yaw, 0.6 + rng() * 0.3), { shadow: false });
      else if (r < 0.26) b.add(N.get('Grass_Wispy_Tall'), trs(px, 0, pz, yaw, 0.6), { shadow: false });
      else if (r < 0.3) b.add(tinted(N.get('Pebble_Round_3'), MOUNTAIN_ROCK, 'mtnpeb'), trs(px, 0, pz, yaw, 1.3), { shadow: false });
    } else if (theme === 'snow') {
      if (r < 0.03) b.add(tinted(N.get('Rock_Medium_1'), 0xe8eef4, 'snowrock'), trs(px, 0, pz, yaw, 0.25), { shadow: false });
    } else if (theme === 'volcanic') {
      if (r < 0.035) {
        // a jagged crack: a few short segments, each turning a little
        let cx = px, cz = pz, a = yaw;
        for (let k = 0; k < 3 + Math.floor(rng() * 3); k++) {
          const len = 0.35 + rng() * 0.5;
          const g = new THREE.BoxGeometry(len, 0.03, 0.06 + rng() * 0.05);
          g.rotateY(-a); g.translate(cx + Math.cos(a) * len / 2, 0.02, cz + Math.sin(a) * len / 2); glow.push(g);
          cx += Math.cos(a) * len; cz += Math.sin(a) * len; a += (rng() - 0.5) * 1.6;
        }
      }
      else if (r < 0.09) b.add(tinted(N.get('Pebble_Round_1'), 0x2a2420, 'ash'), trs(px, 0, pz, yaw, 1.5), { shadow: false });
    }
  }
  // under the sea: streams of bubbles, and shafts of light from the surface
  if (theme === 'underwater') {
    const bubbles = [], shafts = [];
    for (let i = 0; i < 7; i++) {
      const bx = ox + 2 + rng() * (W - 4), bz = oz + 2 + rng() * (H - 4);
      for (let k = 0; k < 6; k++) bubbles.push(new THREE.IcosahedronGeometry(0.05 + rng() * 0.07, 1).translate(bx + (rng() - 0.5) * 0.3, 0.4 + k * 0.55 + rng() * 0.2, bz + (rng() - 0.5) * 0.3));
    }
    for (const [fx, fz] of [[0.25, 0.4], [0.62, 0.3], [0.8, 0.7]]) shafts.push(new THREE.CylinderGeometry(0.8, 1.6, 7, 10, 1, true).translate(ox + W * fx, 3.5, oz + H * fz));
    addMerged(c, bubbles, BUBBLE_MAT, { shadow: false });
    addMerged(c, shafts, SEA_SHAFT, { shadow: false });
  }
  addMerged(c, solid, PLANT_MAT);
  addMerged(c, glow, CRYSTAL_MATS.lava, { shadow: false });
  // snow: the prose's ice as glassy patches
  if (theme === 'snow' && layout.iceCells && layout.iceCells.length) {
    const geo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
    c.owned.push(geo);
    const im = new THREE.InstancedMesh(geo, ICE_MAT, layout.iceCells.length);
    layout.iceCells.forEach(([x, y], i) => im.setMatrixAt(i, trs(ox + x + 0.5, 0.02, oz + y + 0.5, 0, 1)));
    c.group.add(im);
  }
}

function cactus(out, x, z, rng) {
  const h = 1.2 + rng() * 1.2, col = 0x4f7a3a;
  const trunk = new THREE.CylinderGeometry(0.16, 0.2, h, 8); trunk.translate(x, h / 2, z); out.push(colored(trunk, col));
  for (const side of [-1, 1]) {
    if (rng() < 0.35) continue;
    const ah = 0.4 + rng() * 0.5, y0 = h * (0.35 + rng() * 0.3);
    const elbow = new THREE.CylinderGeometry(0.11, 0.11, 0.35, 7); elbow.rotateZ(Math.PI / 2); elbow.translate(x + side * 0.3, y0, z); out.push(colored(elbow, col));
    const arm = new THREE.CylinderGeometry(0.1, 0.12, ah, 7); arm.translate(x + side * 0.45, y0 + ah / 2, z); out.push(colored(arm, col));
  }
}
function driftwood(out, x, z, yaw, rng) {
  const g = new THREE.CylinderGeometry(0.09, 0.13, 1.2 + rng(), 7);
  g.rotateZ(Math.PI / 2); g.rotateY(yaw); g.translate(x, 0.1, z);
  out.push(colored(g, 0x9a8a72));
}

// ground colours for the looks (terrain.js GROUND adds these)
export const LOOK_GROUND = {
  cave: { a: 0x5c5650, b: 0x766e66, path: 0x7e766c, wet: 0x2a3844 },
  mine: { a: 0x4c4034, b: 0x645444, path: 0x76644e, wet: 0x262c2e },
  // a stone circle: cropped moor turf, a worn grey track
  // a village's beaten earth, a camp's trampled mud, a garden's lawn and gravel, a ruin's grass over old paving
  village: { a: 0x77874c, b: 0x8f985c, path: 0x8a7452, wet: 0x3c4a3a },
  camp: { a: 0x6e6a48, b: 0x847a54, path: 0x75614a, wet: 0x3a3a2e },
  garden: { a: 0x4f8a3e, b: 0x6aa24a, path: 0xc8bc9a, wet: 0x2e5a4a },
  terrace: { a: 0xd8d2c4, b: 0xe8e2d6, path: 0xc4bcaa, wet: 0x8aa0aa },
  ruins: { a: 0x6f8048, b: 0x8a8c5e, path: 0xa49c88, wet: 0x3c4a3a },
  stones: { a: 0x5f7448, b: 0x7c8a58, path: 0x8a8678, wet: 0x3c4a3a },
  // an ice cave's frosted rock floor; a lava cave's black glass and ash
  ice_cave: { a: 0x7e92a8, b: 0x96aac0, path: 0x8698ac, wet: 0x6a90b4 },
  lava_cave: { a: 0x3a2a24, b: 0x4a342c, path: 0x56382a, wet: 0x7a2208 },
  snow: { a: 0xd8e2ec, b: 0xf2f6fa, path: 0xb4c0ca, wet: 0x9cc4dc },
  shore: { a: 0xd4c08a, b: 0xe6d6a6, path: 0xc0a874, wet: 0x5a8a98 },
  volcanic: { a: 0x2a2422, b: 0x40342c, path: 0x56443a, wet: 0x4a1a08 },
  web: { a: 0x4c4636, b: 0x5e5644, path: 0x6c6250, wet: 0x2a3030 },
  // a water room's banks, and the sandy bed seen through the shallows
  water_swim: { a: 0x6f8a4a, b: 0x8aa060, path: 0x8a7a58, wet: 0x2e5a6a },
  water_noswim: { a: 0x6a8448, b: 0x86985c, path: 0x8a7a58, wet: 0x22485a },
  // the seabed: pale sand, lighter where currents sweep the ways through
  underwater: { a: 0x4e7c7a, b: 0x6a9a8e, path: 0x8ab0a0, wet: 0x1e4a5a },   // a seabed, blue-green under the water
};

// a drowned city (the room's name says temple, plaza, palace, throne, vault, gate, quarter, ruin,
// city): broken pale columns standing and fallen, and rubble, among the coral
export const RUIN_RE = /\b(temple|plaza|palace|throne|vault|gate(way)?|quarter|ruin|city|hall|shrine|street|court)s?\b/i;
export function sunkenRuins(c) {
  const { layout, ox, oz, kits, b, rng, occ } = c;
  const D = kits.dungeon;
  if (!D) return;
  const { W, H, grid } = layout;
  const ln = lane(layout);
  const STONE = new THREE.Color(1.6, 1.62, 1.5);
  const pillar = tinted(D.get('pillar'), STONE, 'seastone'), column = tinted(D.get('column'), STONE, 'seastone');
  const rubble = tinted(D.get('rubble_large') || D.get('rubble_half'), STONE, 'searubble');
  const spots = [];
  for (let y = 2; y < H - 2; y++) for (let x = 2; x < W - 2; x++) {
    if (grid[y * W + x] === FLOOR && !ln(x, y) && (x % 4 === 2) && (y % 4 === 2)) spots.push([x, y]);
  }
  for (const [x, y] of spots) {
    const r = rng();
    if (r > 0.55) continue;
    const px = ox + x + 0.5, pz = oz + y + 0.5;
    if (r < 0.25 && pillar) {                        // a column still standing
      b.add(occ(pillar), trs(px, 0, pz, rng() * 6.28, 0.9, 0.6 + rng() * 0.5, 0.9));
      grid[y * W + x] = BLOCK;
    } else if (r < 0.4 && column) {                  // one fallen, lying in the sand
      const g = trs(px, 0.35, pz, rng() * 6.28, 1.1);
      g.multiply(new THREE.Matrix4().makeRotationZ(Math.PI / 2));
      b.add(column, g);
    } else if (rubble) {
      b.add(occ(rubble), trs(px, 0, pz, rng() * 6.28, 0.7 + rng() * 0.3));
      grid[y * W + x] = BLOCK;
    }
  }
}

// ---------------------------------------------------------------- a spider's lair
// webs: sheets strung across the corners and between the trunks round the edge, a few strands
// across the room overhead, cocoons hanging from them, clusters of egg sacs at the trees' feet and
// the bones of what was caught. Walk-through scenery (nothing here blocks).
let webTex = null, webMat = null;
function webMaterial() {
  if (webMat) return webMat;
  const cv = document.createElement('canvas');
  cv.width = cv.height = 256;
  const g = cv.getContext('2d');
  g.strokeStyle = 'rgba(240,240,232,0.95)';
  g.lineWidth = 2;
  const c = 128, spokes = 11;
  for (let i = 0; i < spokes; i++) {
    const a = (i / spokes) * Math.PI * 2;
    g.beginPath(); g.moveTo(c, c); g.lineTo(c + Math.cos(a) * 128, c + Math.sin(a) * 128); g.stroke();
  }
  g.lineWidth = 1.4;
  for (let r = 10; r < 124; r += 9) {
    g.beginPath();
    for (let i = 0; i <= spokes; i++) {
      const a = (i / spokes) * Math.PI * 2, rr = r + Math.sin(i * 2.7) * 2;
      const x = c + Math.cos(a) * rr, y = c + Math.sin(a) * rr;
      if (i === 0) g.moveTo(x, y); else g.quadraticCurveTo(c + Math.cos(a - 0.3) * (rr - 4), c + Math.sin(a - 0.3) * (rr - 4), x, y);
    }
    g.stroke();
  }
  webTex = new THREE.CanvasTexture(cv);
  webTex.colorSpace = THREE.SRGBColorSpace;
  webMat = new THREE.MeshBasicMaterial({ map: webTex, transparent: true, opacity: 0.6, side: THREE.DoubleSide, depthWrite: false });
  return webMat;
}

// `indoor`: webs hung in a room or a cave (a spider queen's den, a cellar): no canopy overhead
export function webDress(c, { indoor = false } = {}) {
  const { layout, ox, oz, kits, b, rng } = c;
  const { W, H, grid } = layout;
  const G = kits.graveyard;
  const ln = lane(layout);
  const at = (x, y) => (x < 0 || y < 0 || x >= W || y >= H) ? BLOCK : grid[y * W + x];
  const sheets = [], silk = [];
  const sheet = (x, y, z, w, h, yaw, tilt = 0) => {
    const g = new THREE.PlaneGeometry(w, h);
    g.rotateX(tilt); g.rotateY(yaw); g.translate(x, y, z);
    sheets.push(g);
  };
  // across each corner, high up, and between the trunks along the edges
  for (const [cx, cy, yaw] of [[2, 2, Math.PI / 4], [W - 3, 2, -Math.PI / 4], [2, H - 3, -Math.PI / 4], [W - 3, H - 3, Math.PI / 4]]) {
    sheet(ox + cx + 0.5, (indoor ? 1.3 : 1.9) + rng() * 0.6, oz + cy + 0.5, 3.4 + rng(), 2.6 + rng(), yaw, (rng() - 0.5) * 0.4);
  }
  for (let x = 4; x < W - 4; x += 5 + Math.floor(rng() * 3)) {
    for (const y of [1, H - 2]) if (!ln(x, y) && rng() < 0.75) sheet(ox + x + 0.5, 1.4 + rng() * 0.8, oz + y + 0.5, 2.2 + rng() * 1.2, 1.6 + rng(), (rng() - 0.5) * 0.5);
  }
  for (let y = 3; y < H - 3; y += 4 + Math.floor(rng() * 3)) {
    for (const x of [1, W - 2]) if (!ln(x, y) && rng() < 0.75) sheet(ox + x + 0.5, 1.4 + rng() * 0.8, oz + y + 0.5, 2.0 + rng(), 1.6 + rng(), Math.PI / 2 + (rng() - 0.5) * 0.5);
  }
  // overhead: a canopy sheet or two, and strands strung corner to corner
  for (let i = 0; i < (indoor ? 0 : 2); i++) sheet(ox + W * (0.3 + 0.4 * rng()), 3.3 + rng() * 0.6, oz + H * (0.3 + 0.4 * rng()), 5 + rng() * 3, 4 + rng() * 2, rng() * Math.PI, -Math.PI / 2 + (rng() - 0.5) * 0.5);
  const strand = (x1, y1, z1, x2, y2, z2, r = 0.012) => {
    const a = new THREE.Vector3(x1, y1, z1), bb = new THREE.Vector3(x2, y2, z2), len = a.distanceTo(bb);
    const g = new THREE.CylinderGeometry(r, r, len, 4);
    g.translate(0, len / 2, 0);
    g.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), bb.clone().sub(a).normalize()));
    g.translate(x1, y1, z1);
    silk.push(colored(g, 0xe8e8e0));
  };
  for (let i = 0; i < 4; i++) {
    const x1 = ox + 1 + rng() * (W - 2), z1 = oz + (i % 2 ? 1 : H - 1), x2 = ox + 1 + rng() * (W - 2), z2 = oz + (i % 2 ? H - 1 : 1);
    strand(x1, 3 + rng(), z1, x2, 3 + rng(), z2);
  }
  // cocoons: wrapped bodies hanging near the edges on a thread
  for (let i = 0; i < 5; i++) {
    const side = Math.floor(rng() * 4);
    const x = side < 2 ? 2 + Math.floor(rng() * (W - 4)) : side === 2 ? 2 : W - 3;
    const y = side >= 2 ? 2 + Math.floor(rng() * (H - 4)) : side === 0 ? 2 : H - 3;
    if (ln(x, y)) continue;
    const px = ox + x + 0.5, pz = oz + y + 0.5, hy = 1.1 + rng() * 0.6, len = 0.7 + rng() * 0.4;
    const g = new THREE.CapsuleGeometry(0.2 + rng() * 0.08, len, 3, 8);
    g.rotateZ((rng() - 0.5) * 0.3); g.translate(px, hy, pz);
    silk.push(colored(g, 0xdcd8cc));
    strand(px, hy + len / 2 + 0.2, pz, px, 3.6, pz);
  }
  // egg sacs at the trees' feet, and the bones of what was caught
  for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
    if (at(x, y) !== FLOOR || ln(x, y)) continue;
    const nearWall = at(x - 1, y) === BLOCK || at(x + 1, y) === BLOCK || at(x, y - 1) === BLOCK || at(x, y + 1) === BLOCK;
    const r = rng(), px = ox + x + 0.5, pz = oz + y + 0.5;
    if (nearWall && r < 0.12) {
      for (let k = 0, n = 3 + Math.floor(rng() * 4); k < n; k++) {
        const s = 0.1 + rng() * 0.12, g = new THREE.SphereGeometry(s, 7, 5);
        g.translate(px + (rng() - 0.5) * 0.5, s * 0.8, pz + (rng() - 0.5) * 0.5);
        silk.push(colored(g, 0xeeeae0));
      }
    } else if (G && r < 0.03) {
      b.add(tinted(G.get(rng() < 0.6 ? 'bone_A' : 'skull'), 0xe8e0cc, 'webbones'), trs(px, 0, pz, rng() * 6.28, 0.6), { shadow: false });
    } else if (r < 0.06) {
      sheet(px, 0.03, pz, 1.2 + rng(), 1.2 + rng(), rng() * Math.PI, -Math.PI / 2);         // web on the ground
    }
  }
  addMerged(c, silk, PLANT_MAT, { shadow: false });
  if (sheets.length) {
    const g = mergeGeometries(sheets, false);
    for (const x of sheets) x.dispose();
    if (g) {
      c.owned.push(g);
      const m = new THREE.Mesh(g, webMaterial());
      m.renderOrder = 2;
      c.group.add(m);
    }
  }
}
