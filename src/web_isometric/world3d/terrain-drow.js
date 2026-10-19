// The drow city (the 'drow' look, zone 51), after Menzoberranzan as D&D draws it: a city in a vast
// dark cavern, its homes carved into great stalagmites and hanging stalactites, joined by bridges
// of hardened spider silk, every house outlined in permanent faerie fire (violet, blue and green),
// spiders carved everywhere for Lolth; Narbondel, the great pillar the Archmage heats each day to
// tell the time, at its heart; the spider-shaped temple; groves of glowing fungus.
// Everything here is procedural geometry, merged by material into a few meshes a room.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const FLOOR = 0, BLOCK = 1;

// ---- materials: dark calcite and obsidian; faerie fire (bright enough to bloom); silk ----
export const DROW_STONE = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.88, metalness: 0.05, flatShading: true });
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
      const m = new THREE.Mesh(g, mat);
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
export function spireHouse(P, x, z, { h = 12, r = 2.2, face = 0, rng = Math.random, fire = 'violet', door = true } = {}) {
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
  P.add(DROW_STONE, colored(place(col.translate(0, h / 2, 0), x, 0, z), 0x2c2532, 0x221c28, 0, h));
  const heat = new THREE.CylinderGeometry(r * 1.02, r * 1.12, h * 0.4, 12, 6).translate(0, h * 0.2, 0);
  const p = heat.attributes.position, c = new Float32Array(p.count * 3);
  for (let i = 0; i < p.count; i++) {
    const t = p.getY(i) / (h * 0.4);
    const k = Math.max(0, 1 - t);
    c[i * 3] = 2.6 * k + 0.08; c[i * 3 + 1] = 0.9 * k * k + 0.02; c[i * 3 + 2] = 0.15 * k + 0.03;
  }
  heat.setAttribute('color', new THREE.BufferAttribute(c, 3));
  P.add(HEAT, place(heat, x, 0, z));
  for (const y of [0.3, 1.1]) P.add(FAERIE.violet, place(new THREE.TorusGeometry(r * 1.35, 0.1, 3, 18).rotateX(Math.PI / 2), x, y, z));
}

// the temple of Lolth, after Arach-Tinilith: a hall shaped as a great spider crouching over the
// way, its abdomen a domed nave, eight arched legs planted round it, its eyes alight
export function spiderTemple(P, x, z, yaw = 0, s = 1) {
  const abdomen = new THREE.SphereGeometry(4.2, 12, 8).scale(1, 0.75, 1.25).translate(0, 4.6, -2.6);
  const thorax = new THREE.SphereGeometry(2.6, 12, 8).scale(1, 0.7, 1).translate(0, 3.6, 2.4);
  for (const g of [abdomen, thorax]) P.add(DROW_STONE, colored(place(g, x, 0, z, yaw, s), 0x231d2b, 0x3a3046, 0, 9 * s));
  P.add(OBSIDIAN, place(new THREE.BoxGeometry(2.2, 3, 0.6).translate(0, 1.5, 4.7), x, 0, z, yaw, s));
  P.add(FAERIE.violet, place(new THREE.TorusGeometry(1.2, 0.1, 3, 12, Math.PI).translate(0, 2.9, 4.95), x, 0, z, yaw, s));
  for (const side of [-1, 1]) for (let k = 0; k < 4; k++) {
    const a = -0.9 + k * 0.6;
    const hip = new THREE.Vector3(side * 2.0, 4.0, 1.4 + Math.sin(a) * 1.2), knee = new THREE.Vector3(side * 5.2, 8.2, 1.2 + Math.sin(a) * 4.2),
      foot = new THREE.Vector3(side * 7.6, 0, 1.0 + Math.sin(a) * 6.5);
    for (const [p, q, rr] of [[hip, knee, 0.55], [knee, foot, 0.4]]) {
      const seg = new THREE.CylinderGeometry(rr * 0.8, rr, p.distanceTo(q), 6);
      seg.applyMatrix4(new THREE.Matrix4().compose(p.clone().lerp(q, 0.5), new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), q.clone().sub(p).normalize()), new THREE.Vector3(1, 1, 1)));
      P.add(DROW_STONE, colored(place(seg, x, 0, z, yaw, s), 0x231d2b, 0x30283a, 0, 9 * s));
    }
    P.add(FAERIE.violet, place(new THREE.SphereGeometry(0.3, 6, 4).translate(side * 5.2, 8.2, 1.2 + Math.sin(a) * 4.2), x, 0, z, yaw, s));
  }
  for (const [ex, ey] of [[-0.7, 4.3], [0.7, 4.3], [-0.35, 4.75], [0.35, 4.75]]) P.add(glow(3, 0.4, 0.6), place(new THREE.SphereGeometry(0.28, 6, 4).translate(ex, ey, 4.6), x, 0, z, yaw, s));
  for (const t of [0.35, 0.6]) P.add(FAERIE.violet, place(new THREE.TorusGeometry(4.25 * Math.sin(Math.acos(t * 2 - 1)) * 1.0, 0.09, 3, 20).rotateX(Math.PI / 2).scale(1, 1, 1.25).translate(0, 4.6 + (t * 2 - 1) * 3.1, -2.6), x, 0, z, yaw, s));
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
