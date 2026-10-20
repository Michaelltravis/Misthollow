// The drow city (the 'drow' look, zone 51), after Menzoberranzan as D&D draws it: a city in a vast
// dark cavern, its homes carved into great stalagmites and hanging stalactites, joined by bridges
// of hardened spider silk, every house outlined in permanent faerie fire (violet, blue and green),
// spiders carved everywhere for Lolth; Narbondel, the great pillar the Archmage heats each day to
// tell the time, at its heart; the spider-shaped temple; groves of glowing fungus.
// Everything here is procedural geometry, merged by material into a few meshes a room.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { cutout } from './cutout.js';

const FLOOR = 0, BLOCK = 1;

// ---- materials: dark calcite and obsidian; faerie fire (bright enough to bloom); silk ----
export const DROW_STONE = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.88, metalness: 0.05, flatShading: true,
  emissive: 0x140e20, emissiveIntensity: 1 });   // (a faint glow of its own: its shapes read in the dark)
const OBSIDIAN = new THREE.MeshStandardMaterial({ color: 0x1c1822, roughness: 0.35, metalness: 0.4, flatShading: true });
const glow = (r, g, b) => new THREE.MeshBasicMaterial({ color: new THREE.Color(r, g, b), toneMapped: true });
export const FAERIE = { violet: glow(1.5, 0.55, 3.0), blue: glow(0.55, 1.2, 3.2), green: glow(0.45, 2.4, 1.3) };
const WINDOW = glow(2.2, 0.9, 2.6);
const SILK = new THREE.MeshStandardMaterial({ color: 0xcfc8dc, roughness: 0.6, emissive: 0x3a3050, emissiveIntensity: 0.6 });
const HEAT = new THREE.MeshBasicMaterial({ vertexColors: true });
const FUNGUS = { teal: glow(0.35, 1.9, 1.8), violet: glow(1.2, 0.5, 2.2), amber: glow(2.2, 1.3, 0.4) };
const FAERIE_KEYS = ['violet', 'blue', 'green'];

function colored(geo, color, top = null, h0 = 0, h1 = 1) {
  const a = new THREE.Color(color), b = new THREE.Color(top ?? color), p = geo.attributes.position, n = p.count;
  const col = new Float32Array(n * 3), c = new THREE.Color();
  for (let i = 0; i < n; i++) {
    const t = Math.min(1, Math.max(0, (p.getY(i) - h0) / Math.max(1e-6, h1 - h0)));
    c.copy(a).lerp(b, t);
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return geo;
}
const place = (geo, x, y, z, yaw = 0, s = 1) => geo.applyMatrix4(new THREE.Matrix4().compose(
  new THREE.Vector3(x, y, z), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), yaw), new THREE.Vector3(s, s, s)));

const cutCache = new Map();
const cutMat = mat => { if (!cutCache.has(mat)) cutCache.set(mat, cutout.apply(mat.clone())); return cutCache.get(mat); };

// pieces gathered by material, merged and added to the room at the end
export class Pieces {
  constructor() { this.by = new Map(); }
  add(material, geo) { if (!this.by.has(material)) this.by.set(material, []); this.by.get(material).push(geo); return geo; }
  flush(c) {
    for (const [mat, geos] of this.by) {
      if (!geos.length) continue;
      const nonIndexed = geos.map(g => (g.index ? g.toNonIndexed() : g));
      for (const g of nonIndexed) { for (const k of Object.keys(g.attributes)) if (!['position', 'normal', 'color', 'uv'].includes(k)) g.deleteAttribute(k); if (!g.attributes.uv) g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2)); }
      const vc = mat.vertexColors;
      for (const g of nonIndexed) if (vc && !g.attributes.color) colored(g, 0xffffff); else if (!vc && g.attributes.color) g.deleteAttribute('color');
      const g = mergeGeometries(nonIndexed, false);
      for (const x of geos) x.dispose();
      if (!g) continue;
      g.computeVertexNormals();
      c.owned.push(g);
      // (the see-through cut round the hero: a spire or the great pillar never hides them)
      const m = new THREE.Mesh(g, cutMat(mat));
      m.castShadow = !(mat instanceof THREE.MeshBasicMaterial);
      m.receiveShadow = true;
      c.group.add(m);
    }
    this.by.clear();
  }
}

// a carved spire: a stalagmite (or, flip, a stalactite hanging down to the street) hollowed into
// a house: its rock, faerie-fire bands round it, lit windows, a door with a glowing arch and a
// spider sigil over it, a glowing finial at the tip. `face`: the yaw its door looks along.
export function spireHouse(P, x, z, { h = 12, r = 2.2, face = 0, rng = Math.random, fire = 'violet', door = true, y: y0 = 0 } = {}) {
  // (a house far below a bridge: everything it is made of set down by y0)
  const base = P;
  P = y0 ? { add: (m, g) => base.add(m, g.translate(0, y0, 0)) } : base;
  const prof = [[1.18, 0], [1.0, 0.07], [0.92, 0.25], [0.78, 0.48], [0.56, 0.7], [0.32, 0.86], [0.12, 0.96], [0.02, 1]]
    .map(([k, t]) => new THREE.Vector2(r * k * (0.92 + rng() * 0.16), h * t));
  const rock = new THREE.LatheGeometry(prof, 8);
  colored(rock, 0x221d2a, 0x3a3146, 0, h);
  P.add(DROW_STONE, place(rock, x, 0, z, rng() * 6.28));
  const radiusAt = t => { for (let i = 1; i < prof.length; i++) if (prof[i].y >= t * h) { const a = prof[i - 1], b = prof[i], f = (t * h - a.y) / (b.y - a.y); return a.x + (b.x - a.x) * f; } return 0.05; };
  const fireMat = FAERIE[fire] || FAERIE.violet;
  for (const t of [0.24, 0.47, 0.69]) {
    const ring = new THREE.TorusGeometry(radiusAt(t) + 0.04, 0.07, 3, 10);
    ring.rotateX(Math.PI / 2);
    P.add(fireMat, place(ring, x, t * h, z));
  }
  // ribs of faerie fire up the faces
  for (let k = 0; k < 4; k++) {
    const a = face + Math.PI / 4 + k * Math.PI / 2;
    for (let s = 0; s < 3; s++) {
      const t0 = 0.08 + s * 0.24, t1 = t0 + 0.2, y0 = t0 * h, y1 = t1 * h;
      const r0 = radiusAt(t0) + 0.03, r1 = radiusAt(t1) + 0.03;
      const a0 = new THREE.Vector3(x + Math.sin(a) * r0, y0, z + Math.cos(a) * r0), a1 = new THREE.Vector3(x + Math.sin(a) * r1, y1, z + Math.cos(a) * r1);
      const len = a0.distanceTo(a1), rib = new THREE.BoxGeometry(0.06, len, 0.06);
      rib.applyMatrix4(new THREE.Matrix4().compose(a0.clone().lerp(a1, 0.5), new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), a1.clone().sub(a0).normalize()), new THREE.Vector3(1, 1, 1)));
      P.add(fireMat, rib);
    }
  }
  // lit windows: narrow pointed slits round the upper body
  const nw = 3 + Math.floor(rng() * 4);
  for (let i = 0; i < nw; i++) {
    const t = 0.3 + rng() * 0.45, a = rng() * 6.28, rr = radiusAt(t) + 0.02;
    const w = new THREE.BoxGeometry(0.22, 0.6, 0.08);
    place(w, x + Math.sin(a) * rr, t * h, z + Math.cos(a) * rr, a);
    P.add(WINDOW, w);
  }
  if (door) {
    const rr = radiusAt(0.06);
    const dx = x + Math.sin(face) * rr, dz = z + Math.cos(face) * rr;
    const hole = new THREE.BoxGeometry(1.1, 1.9, 0.3);
    P.add(OBSIDIAN, place(hole, dx, 0.95, dz, face));
    const arch = new THREE.TorusGeometry(0.62, 0.06, 3, 12, Math.PI);
    P.add(fireMat, place(arch, dx, 1.55, dz + 0, face));
    for (const s of [-1, 1]) P.add(fireMat, place(new THREE.BoxGeometry(0.08, 1.55, 0.08), dx + Math.cos(face) * 0.62 * s, 0.78, dz - Math.sin(face) * 0.62 * s, face));
    sigil(P, dx + Math.sin(face) * 0.12, 2.75, dz + Math.cos(face) * 0.12, face, 0.42, fireMat);
  }
  const tip = new THREE.OctahedronGeometry(0.22, 0);
  P.add(fireMat, place(tip, x, h + 0.15, z));
}

// a spider, flat against a wall (a carved sigil in faerie fire) or standing (a statue)
export function sigil(P, x, y, z, yaw, s, mat) {
  const parts = [new THREE.SphereGeometry(0.28, 6, 4).scale(0.8, 1, 0.3), new THREE.SphereGeometry(0.18, 6, 4).translate(0, 0.38, 0).scale(1, 1, 0.3)];
  for (const side of [-1, 1]) for (let k = 0; k < 4; k++) {
    const leg = new THREE.BoxGeometry(0.7, 0.05, 0.05).translate(0.38, 0, 0);
    leg.rotateZ((k - 1.5) * 0.45 + (k < 2 ? 0.3 : -0.3));
    if (side < 0) leg.scale(-1, 1, 1);
    parts.push(leg.translate(0, 0.15, 0));
  }
  const g = mergeGeometries(parts.map(p => p.toNonIndexed ? p.toNonIndexed() : p), false);
  place(g, x, y, z, yaw, s);
  P.add(mat, g);
}
export function spiderStatue(P, x, z, yaw = 0, s = 1.4, rng = Math.random) {
  const body = new THREE.SphereGeometry(0.6, 8, 6).scale(1.1, 0.8, 1.4).translate(0, 1.3, -0.5);
  const thorax = new THREE.SphereGeometry(0.42, 8, 6).scale(1, 0.8, 1.1).translate(0, 1.2, 0.45);
  P.add(OBSIDIAN, place(body, x, 0, z, yaw, s));
  P.add(OBSIDIAN, place(thorax, x, 0, z, yaw, s));
  for (const side of [-1, 1]) for (let k = 0; k < 4; k++) {
    const a = (k - 1.5) * 0.5;
    const knee = new THREE.Vector3(side * 1.1, 1.9, Math.sin(a) * 1.0 + 0.3), foot = new THREE.Vector3(side * 1.7, 0, Math.sin(a) * 1.6 + 0.3);
    const hip = new THREE.Vector3(side * 0.3, 1.25, 0.4);
    for (const [p, q] of [[hip, knee], [knee, foot]]) {
      const len = p.distanceTo(q), seg = new THREE.CylinderGeometry(0.07, 0.05, len, 4);
      seg.applyMatrix4(new THREE.Matrix4().compose(p.clone().lerp(q, 0.5), new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), q.clone().sub(p).normalize()), new THREE.Vector3(1, 1, 1)));
      P.add(OBSIDIAN, place(seg, x, 0, z, yaw, s));
    }
  }
  for (const e of [-0.12, 0.12]) P.add(FAERIE.violet, place(new THREE.SphereGeometry(0.06, 4, 3).translate(e, 1.35, 0.85), x, 0, z, yaw, s));
}

// a giant mushroom of the fungus groves: a pale stalk, a broad cap glowing underneath, spots on top
export function mushroom(P, x, z, { h = 3, rng = Math.random, glowKey = null } = {}) {
  const g = FUNGUS[glowKey || ['teal', 'violet', 'amber'][Math.floor(rng() * 3)]];
  const stalk = new THREE.CylinderGeometry(0.16 * h / 3, 0.28 * h / 3, h, 6);
  colored(stalk, 0x6a6070, 0x9a90a0, -h / 2, h / 2);
  P.add(DROW_STONE, place(stalk.translate(0, h / 2, 0), x, 0, z, rng() * 6.28));
  const cr = 0.9 * h / 3 + rng() * 0.5;
  const cap = new THREE.SphereGeometry(cr, 9, 5, 0, Math.PI * 2, 0, Math.PI / 2).scale(1, 0.45, 1);
  colored(cap, 0x2a2238, 0x4a3a5a, 0, cr * 0.45);
  P.add(DROW_STONE, place(cap, x, h - 0.05, z));
  const gills = new THREE.CircleGeometry(cr * 0.95, 9).rotateX(Math.PI / 2);
  P.add(g, place(gills, x, h - 0.07, z));
  for (let i = 0; i < 5; i++) {
    const a = rng() * 6.28, rr = rng() * cr * 0.7;
    P.add(g, place(new THREE.SphereGeometry(0.09, 4, 3), x + Math.cos(a) * rr, h + cr * 0.45 * Math.sqrt(1 - (rr / cr) ** 2) - 0.02, z + Math.sin(a) * rr));
  }
}

// a bridge of hardened spider silk: a sagging strand thick enough to walk, from a to b
export function silkBridge(P, a, b, { sag = 1.2, w = 0.5 } = {}) {
  const mid = a.clone().lerp(b, 0.5); mid.y -= sag;
  const curve = new THREE.QuadraticBezierCurve3(a, mid, b);
  P.add(SILK, new THREE.TubeGeometry(curve, 16, w * 0.35, 5, false));
  for (const s of [-1, 1]) {
    const off = new THREE.Vector3().subVectors(b, a).cross(new THREE.Vector3(0, 1, 0)).normalize().multiplyScalar(w * s);
    const rail = new THREE.QuadraticBezierCurve3(a.clone().add(off).setY(a.y + 0.9), mid.clone().add(off).setY(mid.y + 0.9), b.clone().add(off).setY(b.y + 0.9));
    P.add(SILK, new THREE.TubeGeometry(rail, 16, 0.04, 3, false));
  }
}

// stalactites hanging from the dark: down to `tip` from far above
export function stalactite(P, x, z, { top = 20, tip = 8, r = 1.2, rng = Math.random } = {}) {
  const len = top - tip;
  const g = new THREE.ConeGeometry(r, len, 7).rotateX(Math.PI);
  colored(g, 0x2a2532, 0x14111a, -len / 2, len / 2);
  P.add(DROW_STONE, place(g, x, tip + len / 2, z, rng() * 6.28));
  if (rng() < 0.6) P.add(FAERIE[FAERIE_KEYS[Math.floor(rng() * 3)]], place(new THREE.OctahedronGeometry(0.16, 0), x, tip - 0.1, z));
}

// Narbondel: the great pillar at the city's heart, its foot glowing with the Archmage's heat
// (red to orange, fading up into the dark as the day cools), a ring of faerie fire round its base
export function narbondel(P, x, z, { r = 2.6, h = 26 } = {}) {
  const col = new THREE.CylinderGeometry(r * 0.85, r * 1.1, h, 12, 8);
  P.add(DROW_STONE, colored(place(col.translate(0, h / 2, 0), x, 0, z), 0x2c2532, 0x1c1722, 0, h));
  // the day's heat at its foot: red-hot where the Archmage's fire went in, cooling upward
  const hh = 3.4;
  const heat = new THREE.CylinderGeometry(r * 1.03, r * 1.12, hh, 12, 6).translate(0, hh / 2, 0);
  const p = heat.attributes.position, c = new Float32Array(p.count * 3);
  for (let i = 0; i < p.count; i++) {
    const k = Math.max(0, 1 - p.getY(i) / hh);
    c[i * 3] = 1.5 * k * k + 0.07; c[i * 3 + 1] = 0.42 * k * k * k + 0.03; c[i * 3 + 2] = 0.05 * k + 0.04;
  }
  heat.setAttribute('color', new THREE.BufferAttribute(c, 3));
  P.add(HEAT, place(heat, x, 0, z));
  for (const y of [0.3, 1.1]) P.add(FAERIE.violet, place(new THREE.TorusGeometry(r * 1.35, 0.1, 3, 18).rotateX(Math.PI / 2), x, y, z));
  // the hours carved up its height, faintly lit
  for (let k = 1; k <= 5; k++) {
    const y = hh + k * (h - hh) / 6, rr = r * (1.1 - 0.25 * (y / h)) + 0.04;
    P.add(FAERIE.blue, place(new THREE.TorusGeometry(rr, 0.05, 3, 16).rotateX(Math.PI / 2), x, y, z));
  }
}

// the temple of Lolth, after Arach-Tinilith: a hall shaped as a great spider crouching over the
// way, its abdomen a domed nave, eight arched legs planted round it, its eyes alight
export function spiderTemple(P, x, z, yaw = 0, s = 1, lift = 0) {
  // (its body raised `lift` on its legs: a way runs under its belly)
  const up = lift / s;
  const abdomen = new THREE.SphereGeometry(4.2, 12, 8).scale(1, 0.75, 1.25).translate(0, 4.6 + up, -2.6);
  const thorax = new THREE.SphereGeometry(2.6, 12, 8).scale(1, 0.7, 1).translate(0, 3.6 + up, 2.4);
  for (const g of [abdomen, thorax]) P.add(DROW_STONE, colored(place(g, x, 0, z, yaw, s), 0x231d2b, 0x3a3046, 0, 9 * s));
  P.add(OBSIDIAN, place(new THREE.BoxGeometry(1.6, 1.4, 0.5).translate(0, 3.2 + up, 4.4), x, 0, z, yaw, s));
  P.add(FAERIE.violet, place(new THREE.TorusGeometry(0.85, 0.08, 3, 12, Math.PI).translate(0, 3.85 + up, 4.7), x, 0, z, yaw, s));
  for (const side of [-1, 1]) for (let k = 0; k < 4; k++) {
    const a = -0.9 + k * 0.6;
    const hip = new THREE.Vector3(side * 2.0, 4.0 + up, 1.4 + Math.sin(a) * 1.2), knee = new THREE.Vector3(side * 5.2, 8.2 + up, 1.2 + Math.sin(a) * 4.2),
      foot = new THREE.Vector3(side * 7.6, 0, 1.0 + Math.sin(a) * 6.5);
    for (const [p, q, rr] of [[hip, knee, 0.55], [knee, foot, 0.4]]) {
      const seg = new THREE.CylinderGeometry(rr * 0.8, rr, p.distanceTo(q), 6);
      seg.applyMatrix4(new THREE.Matrix4().compose(p.clone().lerp(q, 0.5), new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), q.clone().sub(p).normalize()), new THREE.Vector3(1, 1, 1)));
      P.add(DROW_STONE, colored(place(seg, x, 0, z, yaw, s), 0x231d2b, 0x30283a, 0, 9 * s));
    }
    P.add(FAERIE.violet, place(new THREE.SphereGeometry(0.3, 6, 4).translate(side * 5.2, 8.2 + up, 1.2 + Math.sin(a) * 4.2), x, 0, z, yaw, s));
  }
  for (const [ex, ey] of [[-0.7, 4.3], [0.7, 4.3], [-0.35, 4.75], [0.35, 4.75]]) P.add(glow(3, 0.4, 0.6), place(new THREE.SphereGeometry(0.28, 6, 4).translate(ex, ey + up, 4.6), x, 0, z, yaw, s));
  for (const t of [0.35, 0.6]) P.add(FAERIE.violet, place(new THREE.TorusGeometry(4.25 * Math.sin(Math.acos(t * 2 - 1)) * 1.0, 0.09, 3, 20).rotateX(Math.PI / 2).scale(1, 1, 1.25).translate(0, 4.6 + up + (t * 2 - 1) * 3.1, -2.6), x, 0, z, yaw, s));
}

// a web inlaid in the floor in faerie fire (a plaza's centre)
export function floorWeb(P, x, z, { r = 4, mat = FAERIE.violet } = {}) {
  for (let k = 0; k < 8; k++) {
    const a = k * Math.PI / 4;
    P.add(mat, place(new THREE.BoxGeometry(0.07, 0.02, r).translate(0, 0.03, r / 2), x, 0, z, a));
  }
  for (let ring = 1; ring <= 3; ring++) {
    const rr = r * ring / 3.2;
    for (let k = 0; k < 8; k++) {
      const a0 = k * Math.PI / 4, a1 = a0 + Math.PI / 4;
      const p0 = new THREE.Vector3(Math.sin(a0) * rr, 0.03, Math.cos(a0) * rr), p1 = new THREE.Vector3(Math.sin(a1) * rr, 0.03, Math.cos(a1) * rr);
      const seg = new THREE.BoxGeometry(0.06, 0.02, p0.distanceTo(p1));
      seg.applyMatrix4(new THREE.Matrix4().compose(p0.clone().lerp(p1, 0.5), new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), p1.clone().sub(p0).normalize()), new THREE.Vector3(1, 1, 1)));
      P.add(mat, place(seg, x, 0, z));
    }
  }
}

export const DROW_FIRES = FAERIE_KEYS;
export { FLOOR, BLOCK };

// ---------------------------------------------------------------- the rooms
// what kind of place a room of the drow city is, by its name (its imported sector says 'inside'
// for nearly all of them)
export function drowKind(layout, room) {
  const n = String(layout.name || (room && room.data && room.data.name) || '').toLowerCase();
  const sector = room && room.data ? room.data.sector : null;
  if (/center of the drow city/.test(n)) return 'narbondel';
  if (/(entrance|entranceway) to the temple/.test(n)) return 'temple';
  if (/bridge|walkway high above|narrow ledge/.test(n)) return 'bridge';
  if (/fungus/.test(n)) return 'fungus';
  if (/tunnel|cave|alcove/.test(n)) return 'tunnel';
  if (/street|gates?\b|junction|bend in/.test(n)) return 'street';
  return sector === 'city' ? 'street' : 'hall';
}
// how a drow hall is furnished: a throne room or a temple as such, the rest bare stone (null)
export function drowHallKind(layout) {
  const n = String(layout.name || '').toLowerCase();
  return /throne/.test(n) ? 'throne' : /temple|altar|dais|clerics/.test(n) ? 'temple' : null;
}
// the open kinds: no walls round them, the city (or the abyss) beyond their edges
export const DROW_OPEN = new Set(['street', 'narbondel', 'temple', 'bridge', 'fungus']);

const CARD = { north: [0, -1], south: [0, 1], west: [-1, 0], east: [1, 0] };
function neighbour(room, side) {
  if (!room || !room.zoneRef) return null;
  const [dx, dy] = CARD[side];
  return room.zoneRef.cells.get(`${room.cx + dx},${room.cy + dy}`) || null;
}

// cells of the ways through (the exits' lanes) and the middle, kept clear
function lanes(layout) {
  const { W, H, gaps = {} } = layout;
  const mx = Math.floor(W / 2), my = Math.floor(H / 2);
  return (x, y) => ((gaps.north || gaps.south) && Math.abs(x - mx) <= 2) || ((gaps.east || gaps.west) && Math.abs(y - my) <= 2)
    || (Math.abs(x - mx) <= 2 && Math.abs(y - my) <= 2);
}

// the cells of a bridge room the floor is drawn on: the ways across, the rest is the abyss
export function bridgeCells(layout) {
  const { W, H, gaps = {} } = layout;
  const mx = Math.floor(W / 2), my = Math.floor(H / 2);
  const keep = new Set();
  const ns = gaps.north || gaps.south, ew = gaps.east || gaps.west;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const onNS = Math.abs(x - mx) <= 1 && (ns ? (gaps.north || y >= my) && (gaps.south || y <= my) : false);
    const onEW = Math.abs(y - my) <= 1 && (ew ? (gaps.west || x >= mx) && (gaps.east || x <= mx) : false);
    if (onNS || onEW || (Math.abs(x - mx) <= 1 && Math.abs(y - my) <= 1) || (!ns && !ew && Math.abs(y - my) <= 1)) keep.add(y * W + x);
  }
  return keep;
}

// the city beyond an open room's edges: rows of spire houses (the near ones' doors facing the
// room), stalactite houses hanging further back, silk bridges strung between the spires
function skyline(P, c, { below = 0, near = true } = {}) {
  const { layout, ox, oz, room, rng } = c;
  const { W, H } = layout;
  const sides = [['north', ox, oz, W, 0], ['south', ox, oz + H, W, Math.PI], ['west', ox, oz, H, -Math.PI / 2], ['east', ox + W, oz, H, Math.PI / 2]];
  const tops = [];
  for (const [side, x0, z0, len, faceIn] of sides) {
    const nb = neighbour(room, side);
    // another room beyond this edge (a street running on, a house's walls): nothing between
    if (nb && below === 0) continue;
    const out = side === 'north' ? [0, -1] : side === 'south' ? [0, 1] : side === 'west' ? [-1, 0] : [1, 0];
    const along = side === 'north' || side === 'south' ? [1, 0] : [0, 1];
    for (const row of near ? [0, 1, 2] : [1, 2]) {
      const toCamera = side === 'south';
      const depth = [3.2, 9, 16][row] + (toCamera ? 6 : 0);
      const step = [5.2, 6.5, 8][row];
      for (let t = rng() * step * 0.6; t < len + (row ? 6 : 0); t += step * (0.8 + rng() * 0.4)) {
        const d = depth + rng() * 2.2;
        const x = x0 + along[0] * (t - (row ? 3 : 0)) + out[0] * d, z = z0 + along[1] * (t - (row ? 3 : 0)) + out[1] * d;
        const fire = DROW_FIRES[Math.floor(rng() * 3)];
        if (row === 2 && !toCamera && rng() < 0.35) {
          // a house in a stalactite, hanging from the dark, its tip lit
          stalactite(P, x, z, { top: 34 + below, tip: below + 10 + rng() * 6, r: 1.8 + rng() * 1.2, rng });
          continue;
        }
        const h = toCamera ? 3 + rng() * 2.5 : [9, 15, 22][row] + rng() * [5, 7, 10][row];
        const r = [1.7, 2.3, 3.0][row] + rng() * 0.6;
        // (the near row's doors look into the room; the rest face any way)
        const face = row === 0 ? faceIn : rng() * 6.28;
        spireHouse(P, x, z, { h, r, face, rng, fire, door: row < 2, y: below });
        if (row > 0) tops.push(new THREE.Vector3(x, below + h * 0.62, z));
      }
    }
  }
  // silk bridges between spires near enough each other
  tops.sort((a, b) => a.x + a.z - b.x - b.z);
  for (let i = 0; i + 1 < tops.length; i++) {
    const a = tops[i], b = tops[i + 1], d = a.distanceTo(b);
    if (d > 4 && d < 14 && rng() < 0.6) silkBridge(P, a, b, { sag: d * 0.12, w: 0.45 });
  }
}

// a faerie-fire brazier: an obsidian bowl on a stem, a cold flame of faerie fire
function brazier(P, x, z, fire) {
  P.add(OBSIDIAN, place(new THREE.CylinderGeometry(0.08, 0.14, 1.0, 5).translate(0, 0.5, 0), x, 0, z));
  P.add(OBSIDIAN, place(new THREE.CylinderGeometry(0.34, 0.16, 0.24, 7).translate(0, 1.1, 0), x, 0, z));
  P.add(FAERIE[fire], place(new THREE.OctahedronGeometry(0.22, 0).scale(1, 1.6, 1).translate(0, 1.42, 0), x, 0, z));
}
// a cluster of faerie crystals breaking from the floor
function crystals(P, x, z, rng, fire) {
  for (let i = 0; i < 4; i++) {
    const h = 0.6 + rng() * 1.1, g = new THREE.OctahedronGeometry(0.22, 0).scale(1, h * 2.2, 1);
    g.rotateZ((rng() - 0.5) * 0.7); g.rotateX((rng() - 0.5) * 0.7);
    P.add(FAERIE[fire], place(g.translate(0, h * 0.35, 0), x + (rng() - 0.5) * 0.7, 0, z + (rng() - 0.5) * 0.7));
  }
}

function light(c, x, z, color, y = 4, power = 26) {
  const l = new THREE.PointLight(color, power, 16, 1.4);
  l.position.set(x, y, z);
  c.group.add(l);
}

// cells within r of (x, y) blocked (a landmark's foot)
function block(layout, x, y, r) {
  const { W, H, grid } = layout;
  for (let j = Math.floor(y - r); j <= Math.ceil(y + r); j++) for (let i = Math.floor(x - r); i <= Math.ceil(x + r); i++) {
    if (i < 1 || j < 1 || i >= W - 1 || j >= H - 1) continue;
    if ((i + 0.5 - x) ** 2 + (j + 0.5 - y) ** 2 <= r * r) grid[j * W + i] = BLOCK;
  }
}

// the whole dressing of one room of the drow city
// a matron's throne: black stone, a high back crowned with eight spider legs, faerie-fire trim
function drowThrone(P, x, z, glowMat) {
  const add = (m, g) => P.add(m, place(g, x, 0, z));
  add(OBSIDIAN, new THREE.BoxGeometry(1.6, 0.35, 1.4).translate(0, 0.175, 0.1));          // the step
  add(OBSIDIAN, new THREE.BoxGeometry(1.2, 0.55, 1.0).translate(0, 0.62, 0.05));           // the seat
  add(OBSIDIAN, new THREE.BoxGeometry(1.2, 2.6, 0.24).translate(0, 1.6, -0.42));           // the back
  for (const sx of [-0.55, 0.55]) add(OBSIDIAN, new THREE.BoxGeometry(0.16, 0.42, 0.9).translate(sx, 1.08, 0.05));
  add(glowMat, new THREE.BoxGeometry(1.26, 0.05, 0.05).translate(0, 2.9, -0.3));
  for (const sx of [-0.62, 0.62]) add(glowMat, new THREE.BoxGeometry(0.05, 2.5, 0.05).translate(sx, 1.65, -0.3));
  sigil(P, x, 1.75, z - 0.29, 0, 0.7, glowMat);
  // the legs: four a side, bent out and up from the back's top
  for (const side of [-1, 1]) for (let i = 0; i < 4; i++) {
    const a = 0.35 + i * 0.32, y0 = 2.85 - i * 0.28;
    const up = new THREE.CylinderGeometry(0.035, 0.06, 0.9, 4).translate(0, 0.45, 0).rotateZ(-side * a);
    add(OBSIDIAN, up.translate(side * 0.5, y0, -0.42));
    const tip = new THREE.CylinderGeometry(0.01, 0.035, 0.7, 4).translate(0, 0.35, 0).rotateZ(side * 0.5);
    add(OBSIDIAN, tip.translate(side * (0.5 + Math.sin(a) * 0.9), y0 + Math.cos(a) * 0.9, -0.42));
  }
}

// a pillar of the Underdark: black stone ringed with faerie fire
function drowPillar(P, x, z, glowMat, h = 3.2) {
  P.add(OBSIDIAN, place(new THREE.CylinderGeometry(0.45, 0.55, h, 8).translate(0, h / 2, 0), x, 0, z));
  for (const y of [0.4, h * 0.7]) P.add(glowMat, place(new THREE.TorusGeometry(y < 1 ? 0.6 : 0.5, 0.05, 3, 12).rotateX(Math.PI / 2), x, y, z));
}

export function drowDress(c, kind) {
  const { layout, ox, oz, rng } = c;
  const { W, H, grid } = layout;
  const P = new Pieces();
  const free = lanes(layout);
  const cx = ox + W / 2, cz = oz + H / 2;
  const fire = DROW_FIRES[Math.abs(layout.vnum || 0) % 3];
  if (kind === 'bridge') {
    // the abyss: the city's spires far below, glowing; the bridge's rails of silk
    skyline(P, c, { below: -24, near: false });
    const keep = bridgeCells(layout);
    for (let i = 0; i < W * H; i++) if (!keep.has(i)) grid[i] = BLOCK;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      if (!keep.has(y * W + x)) continue;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= W || ny >= H || keep.has(ny * W + nx)) continue;
        // a glowing silk strand along the open edge
        const g = new THREE.BoxGeometry(dx ? 0.06 : 1, 0.06, dy ? 0.06 : 1);
        P.add(FAERIE.violet, place(g, ox + x + 0.5 + dx * 0.5, 0.95, oz + y + 0.5 + dy * 0.5));
        if ((x + y) % 2 === 0) P.add(SILK, place(new THREE.CylinderGeometry(0.05, 0.06, 1, 4).translate(0, 0.5, 0), ox + x + 0.5 + dx * 0.5, 0, oz + y + 0.5 + dy * 0.5));
      }
    }
    light(c, cx, cz, 0x9a6aff, 3, 18);
    P.flush(c);
    return;
  }
  if (DROW_OPEN.has(kind)) skyline(P, c);
  if (kind === 'narbondel') {
    // the great pillar just beyond the plaza, a web of faerie fire inlaid in its floor
    // the great pillar stands in the plaza's north-east, clear of the crossing ways (and of where
    // anyone arrives, the middle), a web of faerie fire inlaid in the floor beside its foot
    const nx = W * 0.79, nz = H * 0.26;
    narbondel(P, ox + nx, oz + nz, { r: 1.9, h: 30 });
    block(layout, nx, nz, 2.3);
    floorWeb(P, cx - W * 0.12, cz + H * 0.08, { r: 4.6 });
    light(c, ox + nx - 1, oz + nz + 3, 0xff6a2a, 2.5, 34);
  }
  if (kind === 'temple') {
    // the temple crouches over the north of the plaza, its door looking south down the way; its
    // feet and its hall block, the way under its belly is open
    spiderTemple(P, cx, oz + 5.2, 0, 0.72, 1.7);
    for (const [fx, fz] of [[-5.5, 5.9], [5.5, 5.9], [-5.6, 3.6], [5.6, 3.6], [-5.4, 1.2], [5.4, 1.2], [-4.6, -1.6], [4.6, -1.6]]) block(layout, W / 2 + fx, 5.2 + fz * 0.72, 0.9);
    floorWeb(P, cx, oz + H * 0.72, { r: 3.4 });
    light(c, cx, oz + 7.5, 0xc040ff, 3.5, 40);
  }
  if (kind === 'hall') {
    // a noble house: faerie fire along the walls' tops, spiders carved on them, a web in the floor
    for (const run of c.runs) {
      const L = run.b - run.a + 1;
      const [x, z, yaw] = run.horiz ? [ox + run.a + L / 2, oz + run.line + (run.line === 0 ? 0.62 : 0.38), 0] : [ox + run.line + (run.line === 0 ? 0.62 : 0.38), oz + run.a + L / 2, Math.PI / 2];
      P.add(FAERIE[fire], place(new THREE.BoxGeometry(L, 0.07, 0.07), x, 2.45, z, yaw));
      P.add(FAERIE[fire], place(new THREE.BoxGeometry(L, 0.05, 0.05), x, 0.12, z, yaw));
      for (let t = 3; t < L - 2; t += 7) {
        const along = run.a + t;
        const [sx, sz] = run.horiz ? [ox + along, z] : [x, oz + along];
        const face = run.horiz ? (run.line === 0 ? 0 : Math.PI) : (run.line === 0 ? Math.PI / 2 : -Math.PI / 2);
        sigil(P, sx, 1.55, sz, face, 0.85, FAERIE[fire]);
      }
    }
    if (/throne|temple|altar|dais|chamber/i.test(layout.name || '')) floorWeb(P, cx, cz, { r: 3.5, mat: FAERIE[fire] });
    // the throne where furnish leaves its place, against the north wall
    if (drowHallKind(layout) === 'throne' && !layout.gaps.north) drowThrone(P, cx, oz + 2.2, FAERIE[fire]);
  }
  // the street's furniture on roomgen's obstacles (they block already): mushrooms, spider
  // statues, crystals; the fungus forest is thick with mushrooms
  const obstacles = layout.obstacles || [];
  for (const o of obstacles) {
    const x = ox + o.x + (o.big ? 1 : 0.5), z = oz + o.y + (o.big ? 1 : 0.5);
    const r = rng();
    if (kind === 'hall') {
      // a hall of the house (its throne or altar aside): a spider statue, a pillar ringed in faerie fire, crystals
      if (o.big && r < 0.45) spiderStatue(P, x, z, rng() * 6.28, 0.75, rng);
      else if (o.big) drowPillar(P, x, z, FAERIE[fire]);
      else crystals(P, x, z, rng, fire);
      continue;
    }
    if (kind === 'fungus' || r < 0.4) mushroom(P, x, z, { h: o.big ? 3 + rng() * 2.5 : 1.6 + rng(), rng });
    else if (r < 0.65 && o.big) spiderStatue(P, x, z, rng() * 6.28, 0.9, rng);
    else crystals(P, x, z, rng, DROW_FIRES[Math.floor(rng() * 3)]);
  }
  if (kind === 'fungus') {
    for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
      if (grid[y * W + x] !== FLOOR || free(x, y) || rng() > 0.07) continue;
      mushroom(P, ox + x + 0.5, oz + y + 0.5, { h: 2.5 + rng() * 3.5, rng });
      grid[y * W + x] = BLOCK;
    }
  }
  if (kind === 'tunnel') {
    // glowing fungus at the rock's feet, a few faerie crystals
    for (let i = 0; i < 6; i++) {
      const x = 1 + Math.floor(rng() * (W - 2)), y = 1 + Math.floor(rng() * (H - 2));
      if (grid[y * W + x] !== FLOOR || free(x, y)) continue;
      if (rng() < 0.6) mushroom(P, ox + x + 0.5, oz + y + 0.5, { h: 0.8 + rng() * 1.2, rng }); else crystals(P, ox + x + 0.5, oz + y + 0.5, rng, fire);
    }
  }
  // the props (walk-through): faerie-fire braziers in the open city, crystals in the halls
  for (const p of layout.props || []) {
    const x = ox + p.x + 0.5, z = oz + p.y + 0.5;
    if (kind === 'hall') { if (rng() < 0.5) brazier(P, x, z, fire); continue; }
    if (rng() < 0.5) brazier(P, x, z, DROW_FIRES[Math.floor(rng() * 3)]);
  }
  const lc = { violet: 0x9a5aff, blue: 0x4a8aff, green: 0x3adf8a };
  light(c, ox + W * 0.3, oz + H * 0.4, lc[fire], 4, 22);
  light(c, ox + W * 0.72, oz + H * 0.6, lc[DROW_FIRES[(DROW_FIRES.indexOf(fire) + 1) % 3]], 4, 18);
  P.flush(c);
}
