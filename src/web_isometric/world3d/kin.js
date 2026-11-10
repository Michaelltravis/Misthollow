// The creature kit: a body built from a recipe (kinrecipe.js), each kind of creature its own.
// A few skeletons (four-legged beasts, birds, swimmers; more in later pushes), each with parts
// that swap in and out (heads, ears, horns, tails, wings, fins), proportions, a coat and its
// markings. Low-poly primitives with flat shading, to sit with the rest of the art, animated in
// code through proc.js's ProcActor (idle, walk, attack, hit, death), so entities.js treats a kit
// body like any other. Built 1 m tall; `height` scales it.
import * as THREE from 'three';
import { ownBody } from './freebody.js';
import { ProcActor } from './proc.js';
import { rng } from './kinrecipe.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const mat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.85, flatShading: true, ...extra });
const DARK_EYE = new THREE.MeshBasicMaterial({ color: 0x141210 });
const GLOW_EYE = new THREE.MeshBasicMaterial({ color: new THREE.Color(2.0, 0.9, 0.25) });
const HOOF = mat(0x2e2824), HORN = mat(0xd8ceb4), BEAK = mat(0xd8a040), PINK = mat(0xc88a8a);
const sph = (r, w = 8, h = 6) => new THREE.SphereGeometry(r, w, h);
const cyl = (a, b, len, n = 6) => new THREE.CylinderGeometry(a, b, len, n);
const cone = (r, len, n = 6) => new THREE.ConeGeometry(r, len, n);
const box = (x, y, z) => new THREE.BoxGeometry(x, y, z);

function m(geo, material, x = 0, y = 0, z = 0, sx = 1, sy = 1, sz = 1) {
  const o = new THREE.Mesh(geo, material);
  o.position.set(x, y, z);
  o.scale.set(sx, sy, sz);
  o.castShadow = true;
  return o;
}
// a mesh the animation moves by itself (not merged with its neighbours)
const keep = o => { o.userData.keep = true; return o; };
function grp(parent, x = 0, y = 0, z = 0) {
  const g = new THREE.Group();
  g.position.set(x, y, z);
  parent.add(g);
  return g;
}
// a limb hanging down from its joint (a cylinder whose top is at the group's origin)
function limb(len, r0, r1, material) {
  const geo = cyl(r0, r1, len, 6);
  geo.translate(0, -len / 2, 0);
  return m(geo, material);
}

// ---------------------------------------------------------------- four-legged beasts
function quad(k) {
  const root = new THREE.Group(), body = new THREE.Group();
  root.add(body);
  const coat = mat(k.c.main), belly = mat(k.c.belly), accent = mat(k.c.accent);
  const eye = k.c.eye === 'glow' ? GLOW_EYE : DARK_EYE;
  const scaled = k.fur === 'scale', shaggy = k.fur === 'shaggy';
  const L = k.leg, G = k.girth, D = k.len, sprawl = k.gait === 'sprawl';
  const torsoY = (sprawl ? L * 0.7 : L) + G * 0.85;
  const torso = keep(m(sph(0.5, 10, 8), coat, 0, torsoY, 0, G * 1.9, G * 1.8, D));
  body.add(torso);
  body.add(m(sph(0.5, 9, 7), belly, 0, torsoY - G * 0.28, 0.02, G * 1.6, G * 1.2, D * 0.86));
  if (shaggy) for (let i = 0; i < 7; i++) {
    const z = D * (0.38 - i * 0.12), s = 0.55 + ((k.seed >> i) & 3) * 0.08;
    body.add(m(sph(G * 0.42 * s, 6, 5), coat, ((i % 2) - 0.5) * G * 0.5, torsoY + G * 0.72, z, 1.2, 0.8, 1.3));
  }
  // markings
  if (k.pattern === 'saddle') body.add(m(sph(0.5, 10, 6), accent, 0, torsoY + G * 0.3, -D * 0.05, G * 1.75, G * 1.2, D * 0.7));
  if (k.pattern === 'stripes') for (let i = 0; i < 5; i++) body.add(m(box(G * 1.95, G * 0.5, 0.035), accent, 0, torsoY + G * 0.35, D * (0.3 - i * 0.14)));
  if (k.pattern === 'spots') { const r = rng(k.seed + 7); for (let i = 0; i < 7; i++) body.add(m(sph(G * 0.16, 6, 4), accent, (r() - 0.5) * G * 1.4, torsoY + G * (0.45 + r() * 0.35), (r() - 0.5) * D * 0.8, 1, 0.4, 1)); }
  if (k.spikes || scaled) for (let i = 0; i < 6; i++) body.add(m(cone(G * 0.12, G * (k.spikes ? 0.5 : 0.25), 4), accent, 0, torsoY + G * 0.95, D * (0.36 - i * 0.14)));
  // legs: hips under the torso's four corners
  const legs = [];
  const hoofed = /^(long|snout)$/.test(k.head) || k.horns !== 'none' || k.tail === 'tuft';
  const legR = Math.max(0.035, G * (shaggy ? 0.2 : 0.16));
  for (const [sx, sz] of [[-1, 1], [1, 1], [-1, -1], [1, -1]]) {
    const hip = grp(body, sx * G * 0.6, torsoY - G * 0.35, sz * D * 0.32);
    const len = sprawl ? L * 0.95 : L + G * 0.5;
    const leg = limb(len, legR, legR * 0.75, k.pattern === 'socks' ? coat : coat);
    if (sprawl) hip.rotation.z = sx * 0.9;
    hip.add(leg);
    hip.add(m(sph(legR * 1.15, 6, 4), hoofed ? HOOF : k.pattern === 'socks' ? belly : accent, 0, -len, 0.02, 1, 0.6, 1.3));
    if (k.pattern === 'socks') hip.add(m(cyl(legR * 1.02, legR * 0.85, len * 0.3, 6), belly, 0, -len * 0.82, 0));
    legs.push({ hip, phase: sx * sz > 0 ? 0 : Math.PI });
  }
  // neck and head at the front
  const neck = grp(body, 0, torsoY + G * 0.35, D * 0.42);
  const N = Math.max(0.08, k.neck);
  const neckMesh = m(cyl(G * 0.42, G * 0.55, N + G * 0.4, 7), coat);
  neckMesh.position.set(0, N * 0.35, N * 0.25);
  neckMesh.rotation.x = 0.6;
  neck.add(neckMesh);
  if (k.mane) for (let i = 0; i < 5; i++) neck.add(m(box(0.05, G * 0.35, G * 0.3), accent, 0, N * 0.2 + i * N * 0.16 + G * 0.2, N * 0.05 + i * N * 0.07 - G * 0.25));
  const head = grp(neck, 0, N * 0.7 + G * 0.15, N * 0.55 + G * 0.2);
  const H = G * 0.95 * k.headSize;
  head.add(m(sph(H * 0.5, 8, 6), coat, 0, 0, 0, 1, 0.95, 1.05));
  if (k.head === 'pointed') head.add(m(cone(H * 0.32, H * 0.8, 7), coat, 0, -H * 0.08, H * 0.6).rotateX(Math.PI / 2));
  if (k.head === 'long') head.add(m(cyl(H * 0.22, H * 0.3, H * 1.0, 7), coat, 0, -H * 0.12, H * 0.62).rotateX(Math.PI / 2));
  if (k.head === 'blunt') head.add(m(sph(H * 0.3, 7, 5), belly, 0, -H * 0.14, H * 0.4, 1.1, 0.8, 0.9));
  if (k.head === 'snout') { head.add(m(cyl(H * 0.24, H * 0.28, H * 0.45, 8), coat, 0, -H * 0.06, H * 0.5).rotateX(Math.PI / 2)); head.add(m(cyl(H * 0.2, H * 0.2, 0.02, 8), PINK, 0, -H * 0.06, H * 0.73).rotateX(Math.PI / 2)); }
  const tipZ = { pointed: H * 0.98, long: H * 1.1, blunt: H * 0.62, snout: H * 0.74 }[k.head] || H * 0.6;
  head.add(m(sph(H * 0.07, 5, 4), DARK_EYE, 0, -H * 0.06, tipZ));
  if (k.pattern === 'blaze') head.add(m(box(H * 0.14, 0.02, H * 0.7), belly, 0, H * 0.4, H * 0.25));
  for (const s of [-1, 1]) head.add(m(sph(H * 0.075, 6, 4), eye, s * H * 0.24, H * 0.1, H * 0.34));
  // ears
  const E = H * k.earSize;
  for (const s of [-1, 1]) {
    if (k.ears === 'pointed') head.add(m(cone(E * 0.13, E * 0.34, 4), coat, s * H * 0.24, H * 0.42, -H * 0.04).rotateZ(-s * 0.25));
    else if (k.ears === 'tall') head.add(m(cone(E * 0.14, E * 0.55, 4), coat, s * H * 0.24, H * 0.52, -H * 0.04).rotateZ(-s * 0.2));
    else if (k.ears === 'round') head.add(m(sph(E * 0.14, 6, 4), accent, s * H * 0.3, H * 0.38, -H * 0.05, 1, 1, 0.5));
    else if (k.ears === 'floppy') head.add(m(sph(E * 0.16, 6, 4), accent, s * H * 0.42, H * 0.12, -H * 0.05, 0.5, 1.4, 0.9));
    else if (k.ears === 'long') head.add(m(sph(E * 0.14, 6, 4), coat, s * H * 0.16, H * 0.82, -H * 0.12, 0.6, 3.0, 0.5).rotateZ(-s * 0.12));
  }
  // horns
  for (const s of [-1, 1]) {
    if (k.horns === 'horns') { const h = m(cone(H * 0.08, H * 0.6, 6), HORN, s * H * 0.42, H * 0.36, 0); h.rotation.z = -s * 1.0; head.add(h); }
    else if (k.horns === 'curled') { const t = new THREE.Mesh(new THREE.TorusGeometry(H * 0.2, H * 0.06, 5, 10, Math.PI * 1.4), HORN); t.position.set(s * H * 0.3, H * 0.3, -H * 0.05); t.rotation.y = s * Math.PI / 2; t.castShadow = true; head.add(t); }
    else if (k.horns === 'antlers') {
      const a = grp(head, s * H * 0.18, H * 0.4, -H * 0.05);
      a.rotation.z = -s * 0.45;
      a.add(m(cyl(H * 0.03, H * 0.04, H * 0.9, 5), HORN, 0, H * 0.45, 0));
      for (let i = 0; i < 3; i++) { const b = m(cyl(H * 0.022, H * 0.03, H * 0.4, 4), HORN, s * H * 0.12, H * (0.35 + i * 0.22), H * 0.08); b.rotation.z = -s * 0.9; b.rotation.x = 0.3; a.add(b); }
    } else if (k.horns === 'tusks') { const t = m(cone(H * 0.08, H * 0.45, 5), HORN, s * H * 0.2, -H * 0.02, tipZ * 0.8); t.rotation.x = -0.25; t.rotation.z = -s * 0.35; head.add(t); }
  }
  if (k.horns === 'spike') { const h = m(cone(H * 0.07, H * 0.8, 6), HORN, 0, H * 0.55, H * 0.25); h.rotation.x = 0.4; head.add(h); }
  // tail
  const tail = grp(body, 0, torsoY + G * 0.25, -D * 0.48);
  const T = k.tailLen;
  if (k.tail === 'bushy') { const t = m(sph(G * 0.32, 7, 5), coat, 0, -G * 0.2 * T, -G * 0.55 * T, 0.8, 0.8, 2.0 * T); t.rotation.x = 0.6; tail.add(t); tail.add(m(sph(G * 0.18, 6, 4), belly, 0, -G * 0.55 * T, -G * 1.05 * T)); }
  else if (k.tail === 'thin' || k.tail === 'long') { const n = k.tail === 'long' ? 7 : 5; for (let i = 0; i < n; i++) tail.add(m(sph(G * (0.1 - i * 0.008), 5, 4), coat, 0, -i * G * 0.06, -i * G * 0.22 * T)); }
  else if (k.tail === 'tuft') { tail.add(m(cyl(G * 0.05, G * 0.04, G * 0.9 * T, 5), coat, 0, -G * 0.45 * T, -G * 0.1).rotateX(0.3)); tail.add(m(sph(G * 0.14, 6, 4), accent, 0, -G * 0.9 * T, -G * 0.3, 0.8, 1.4, 0.8)); }
  else if (k.tail === 'curl') { const t = new THREE.Mesh(new THREE.TorusGeometry(G * 0.12, G * 0.035, 4, 8, Math.PI * 1.6), PINK); t.position.set(0, 0, -G * 0.1); t.castShadow = true; tail.add(t); }
  else if (k.tail === 'puff') tail.add(m(sph(G * 0.2, 6, 5), belly));
  else if (k.tail === 'stub') tail.add(m(sph(G * 0.12, 5, 4), coat, 0, 0, -G * 0.05));
  else if (k.gait === 'sprawl' || k.tail === 'scale') for (let i = 0; i < 6; i++) tail.add(m(sph(G * (0.2 - i * 0.03), 5, 4), coat, 0, -i * G * 0.04, -i * G * 0.3));
  const hopper = k.gait === 'hop';
  return finish(root, body, (t, st, a) => {
    const sp = st === 'walk' ? (hopper ? 9 : 11) : 2;
    if (hopper) {
      const h = st === 'walk' ? Math.max(0, Math.sin(t * sp)) : 0;
      body.position.y = h * 0.18;
      legs.forEach(l => { l.hip.rotation.x = st === 'walk' ? Math.sin(t * sp) * 0.6 : 0; });
    } else {
      body.position.y = st === 'walk' ? Math.abs(Math.sin(t * sp)) * 0.025 : Math.sin(t * 1.6) * 0.006;
      legs.forEach(l => { l.hip.rotation.x = st === 'walk' ? Math.sin(t * sp + l.phase) * 0.55 : Math.sin(t * 1.2 + l.phase) * 0.02; });
      if (sprawl) body.rotation.y = st === 'walk' ? Math.sin(t * sp) * 0.12 : 0;
    }
    torso.scale.y = G * 1.8 * (1 + Math.sin(t * 2.2) * 0.015);
    tail.rotation.y = Math.sin(t * (st === 'walk' ? 9 : 2.2)) * (k.tail === 'stub' ? 0.1 : 0.4);
    const strike = st === 'attack' ? Math.sin(a * Math.PI) : 0;
    neck.rotation.x = strike * (k.horns !== 'none' ? 0.7 : 0.45) + (st === 'idle' ? Math.sin(t * 0.7) * 0.06 : 0);
    neck.position.z = D * 0.42 + strike * 0.12;
    body.rotation.x = st === 'hit' ? -Math.sin(a * Math.PI) * 0.15 : (hopper ? 0 : 0);
  });
}

// ---------------------------------------------------------------- birds
function bird(k) {
  const root = new THREE.Group(), body = new THREE.Group();
  root.add(body);
  const plume = mat(k.c.main), breast = mat(k.c.belly), accent = mat(k.c.accent);
  const eye = k.c.eye === 'glow' ? GLOW_EYE : DARK_EYE;
  const upright = k.stance === 'upright', leather = k.wingType === 'leather';
  const L = k.leg, G = k.girth;
  const bodyY = L + G * (upright ? 1.25 : 0.85);
  const torso = m(sph(0.5, 10, 8), plume, 0, bodyY, 0, G * 1.5, G * (upright ? 2.6 : 1.6), G * (upright ? 1.4 : 2.3));
  if (!upright) torso.rotation.x = -0.25;
  body.add(torso);
  body.add(m(sph(0.5, 9, 7), breast, 0, bodyY - G * 0.12, G * 0.22, G * 1.25, G * (upright ? 2.2 : 1.3), G * (upright ? 1.0 : 1.6)));
  if (k.pattern === 'collar') body.add(m(new THREE.TorusGeometry(G * 0.42, G * 0.08, 4, 10), accent, 0, bodyY + G * (upright ? 1.0 : 0.62), G * 0.55).rotateX(Math.PI / 2.4));
  // head on its neck
  const neck = grp(body, 0, bodyY + G * (upright ? 1.1 : 0.55), G * (upright ? 0.15 : 0.8));
  const NL = k.neckLong ? G * 1.6 : G * 0.25;
  if (k.neckLong) neck.add(m(cyl(G * 0.13, G * 0.18, NL, 6), plume, 0, NL / 2, 0.05));
  const head = grp(neck, 0, NL + G * 0.2, k.neckLong ? 0.08 : 0);
  const H = G * 0.9 * k.headSize;
  head.add(m(sph(H * 0.5, 8, 6), k.pattern === 'cap' ? accent : plume));
  if (k.pattern === 'cap') head.add(m(sph(H * 0.5, 8, 6), breast, 0, -H * 0.12, H * 0.05, 0.95, 0.7, 0.95));
  const beakLen = { short: H * 0.35, hook: H * 0.4, straight: H * 0.55, long: H * 1.4, flat: H * 0.5, snout: H * 0.15 }[k.beak] || H * 0.35;
  if (k.beak === 'flat') head.add(m(box(H * 0.32, H * 0.08, beakLen), BEAK, 0, -H * 0.08, H * 0.42 + beakLen / 2));
  else if (k.beak === 'snout') head.add(m(sph(H * 0.18, 6, 4), plume, 0, -H * 0.05, H * 0.45));
  else {
    head.add(m(cone(H * 0.12, beakLen, 5), BEAK, 0, -H * 0.04, H * 0.42 + beakLen / 2).rotateX(Math.PI / 2));
    if (k.beak === 'hook') head.add(m(cone(H * 0.06, H * 0.16, 4), BEAK, 0, -H * 0.16, H * 0.42 + beakLen * 0.9).rotateX(Math.PI));
  }
  if (k.face === 'owl') for (const s of [-1, 1]) { head.add(m(sph(H * 0.2, 8, 4), breast, s * H * 0.2, H * 0.06, H * 0.36, 1, 1, 0.3)); head.add(m(sph(H * 0.09, 6, 4), k.c.eye === 'glow' ? GLOW_EYE : mat(0xe8b830), s * H * 0.2, H * 0.06, H * 0.43)); }
  else for (const s of [-1, 1]) head.add(m(sph(H * 0.08, 6, 4), eye, s * H * 0.34, H * 0.1, H * 0.2));
  if (k.ears) for (const s of [-1, 1]) head.add(m(cone(H * 0.15, H * 0.5, 4), accent, s * H * 0.22, H * 0.5, -H * 0.02));
  if (k.crest === 'tuft') for (let i = 0; i < 3; i++) head.add(m(cone(H * 0.06, H * 0.4, 4), accent, 0, H * 0.55, -H * 0.1 - i * H * 0.12).rotateX(-0.6 - i * 0.2));
  if (k.crest === 'comb') for (let i = 0; i < 3; i++) head.add(m(box(0.03, H * 0.22, H * 0.14), mat(0xc83020), 0, H * 0.55, H * 0.1 - i * H * 0.13));
  // wings
  const wings = [];
  const W = k.wing;
  for (const s of [-1, 1]) {
    const sh = grp(body, s * G * 0.7, bodyY + G * 0.35, upright ? 0 : G * 0.25);
    if (leather) {
      const arm = m(cyl(0.02, 0.015, W, 4), accent, s * W * 0.5, 0, 0); arm.rotation.z = Math.PI / 2; sh.add(arm);
      const web = new THREE.Mesh(new THREE.ConeGeometry(W * 0.5, W * 0.9, 3, 1), mat(k.c.accent, { side: THREE.DoubleSide }));
      web.scale.set(1, 1, 0.05); web.rotation.z = s * Math.PI / 2; web.position.set(s * W * 0.45, -W * 0.15, 0); web.castShadow = true; sh.add(web);
    } else {
      sh.add(m(sph(0.5, 8, 5), plume, s * W * 0.25, -G * 0.15, -W * 0.25, W * 0.6, 0.08, W * 0.9).rotateY(s * 0.15));
      if (k.pattern === 'bars') for (let i = 0; i < 3; i++) sh.add(m(box(W * 0.5, 0.05, 0.03), accent, s * W * 0.25, -G * 0.11, -W * (0.05 + i * 0.16)));
    }
    if (upright) sh.rotation.z = s * 0.15;
    sh.userData.wing = s;                 // corpse.js folds it over the back when the creature dies
    wings.push({ sh, s });
  }
  // tail
  if (k.tail === 'fan') body.add(m(cone(G * 0.45, G * 1.0, 5), accent, 0, bodyY - G * 0.05, -G * 1.15, 1, 0.15, 1).rotateX(-Math.PI / 2 + 0.25));
  if (k.tail === 'plume') for (let i = 0; i < 3; i++) body.add(m(box(0.04, G * 0.9, G * 0.25), accent, (i - 1) * 0.06, bodyY + G * 0.3, -G * 0.95).rotateX(-0.5 - i * 0.15));
  // legs
  const legs = [];
  for (const s of [-1, 1]) {
    const hip = grp(body, s * G * 0.3, bodyY - G * (upright ? 1.0 : 0.6), upright ? 0.05 : 0);
    hip.add(limb(L + G * 0.2, 0.025, 0.02, BEAK));
    hip.add(m(box(0.12, 0.02, 0.16), BEAK, 0, -(L + G * 0.2), 0.05));
    legs.push(hip);
  }
  const flier = !upright;
  return finish(root, body, (t, st, a) => {
    const walking = st === 'walk';
    const flap = walking && flier ? Math.sin(t * (leather ? 16 : 13)) : Math.sin(t * 2) * 0.05;
    wings.forEach(({ sh, s }) => { sh.rotation.z = s * (walking && flier ? 0.2 + flap * 0.9 : (upright ? 0.15 + Math.sin(t * 8) * (walking ? 0.25 : 0.02) : 0.05 + flap * 0.1)); });
    if (upright) { body.rotation.z = walking ? Math.sin(t * 7) * 0.12 : 0; legs.forEach((l, i) => { l.rotation.x = walking ? Math.sin(t * 7 + i * Math.PI) * 0.4 : 0; }); }
    else legs.forEach((l, i) => { l.rotation.x = walking ? -0.9 : Math.sin(t * 1.3 + i) * 0.03; });
    body.position.y = walking && flier ? 0.08 + flap * 0.04 : Math.sin(t * 1.8) * 0.006;
    const strike = st === 'attack' ? Math.sin(a * Math.PI) : 0;
    neck.rotation.x = strike * 0.8 + (st === 'idle' ? Math.max(0, Math.sin(t * 0.9)) * 0.25 : 0);
    head.rotation.y = st === 'idle' ? Math.sin(t * 0.6) * 0.4 : 0;
    body.rotation.x = st === 'hit' ? -Math.sin(a * Math.PI) * 0.2 : 0;
  });
}

// ---------------------------------------------------------------- swimmers
function fish(k) {
  const root = new THREE.Group(), body = new THREE.Group();
  root.add(body);
  const skin = mat(k.c.main), under = mat(k.c.belly), accent = mat(k.c.accent);
  const eye = k.c.eye === 'glow' ? GLOW_EYE : DARK_EYE;
  const G = k.girth, D = k.len, F = k.finSize;
  const y = G * 0.9 + 0.05;
  const hull = grp(body, 0, y, 0);
  hull.add(m(sph(0.5, 12, 8), skin, 0, 0, 0, G * 1.3, G * 1.6, D));
  hull.add(m(sph(0.5, 10, 6), under, 0, -G * 0.28, 0.02, G * 1.15, G * 1.0, D * 0.9));
  if (k.pattern === 'stripes') for (let i = 0; i < 4; i++) hull.add(m(box(G * 1.32, G * 1.2, 0.03), accent, 0, G * 0.1, D * (0.25 - i * 0.15)));
  if (k.pattern === 'spots') { const r = rng(k.seed + 3); for (let i = 0; i < 8; i++) { const s = r() < 0.5 ? -1 : 1; hull.add(m(sph(G * 0.1, 5, 4), accent, s * G * 0.6, (r() - 0.3) * G * 0.6, (r() - 0.5) * D * 0.7, 0.4, 1, 1)); } }
  // snout and face
  const front = D * 0.48;
  if (k.snout === 'pointed') hull.add(m(cone(G * 0.42, D * 0.32, 8), skin, 0, -G * 0.05, front + D * 0.1).rotateX(Math.PI / 2));
  if (k.snout === 'hammer') { hull.add(m(box(G * 2.2, G * 0.3, G * 0.4), skin, 0, G * 0.05, front + G * 0.15)); for (const s of [-1, 1]) hull.add(m(sph(G * 0.1, 5, 4), eye, s * G * 1.08, G * 0.12, front + G * 0.15)); }
  if (k.snout === 'whisker') { hull.add(m(sph(G * 0.32, 8, 6), under, 0, -G * 0.1, front + G * 0.05, 1.2, 0.8, 1)); for (const s of [-1, 1]) for (let i = 0; i < 2; i++) hull.add(m(cyl(0.006, 0.004, G * 0.5, 3), DARK_EYE, s * G * 0.3, -G * 0.08 - i * 0.03, front + G * 0.2).rotateZ(s * Math.PI / 2.2)); }
  if (k.snout !== 'hammer') for (const s of [-1, 1]) hull.add(m(sph(G * 0.06, 6, 4), eye, s * G * 0.58, G * 0.2, front - D * 0.1));
  // fins
  if (k.dorsal === 'small') hull.add(m(cone(G * 0.35, G * 0.6, 4), accent, 0, G * 0.85, -D * 0.05, 0.2, 1, 1.4));
  if (k.dorsal === 'tall') hull.add(m(cone(G * 0.4, G * 1.3 * F, 4), skin, 0, G * 1.1, -D * 0.02, 0.15, 1, 1.2).rotateX(-0.35));
  if (k.dorsal === 'ridge') for (let i = 0; i < 7; i++) hull.add(m(cone(G * 0.12, G * 0.3, 4), accent, 0, G * 0.78, D * (0.3 - i * 0.1), 0.3, 1, 1));
  const fins = [];
  for (const s of [-1, 1]) {
    const fg = grp(hull, s * G * 0.6, -G * 0.3, D * 0.18);
    const big = k.flippers || k.fins === 'wings';
    fg.add(m(sph(0.5, 6, 4), k.fins === 'wings' ? accent : skin, s * G * (big ? 0.5 : 0.25), 0, -G * 0.2, G * (big ? 1.2 : 0.55) * F, 0.06, G * (big ? 0.8 : 0.45) * F));
    fins.push({ fg, s });
  }
  // the tail
  const tail = grp(body, 0, y, -D * 0.48);
  if (k.tail === 'fork') for (const s of [-1, 1]) tail.add(m(cone(G * 0.3, G * 0.9 * F, 4), accent, 0, s * G * 0.32, -G * 0.4, 0.15, 1, 1).rotateX(-Math.PI / 2 + s * 0.6));
  if (k.tail === 'flukes') for (const s of [-1, 1]) tail.add(m(sph(0.5, 6, 4), skin, s * G * 0.45, 0, -G * 0.35, G * 1.0 * F, 0.08, G * 0.55 * F).rotateY(-s * 0.4));
  if (k.tail === 'flippers') for (const s of [-1, 1]) tail.add(m(sph(0.5, 6, 4), skin, s * G * 0.22, -G * 0.15, -G * 0.4, G * 0.5, 0.08, G * 0.9));
  return finish(root, body, (t, st, a) => {
    const swim = st === 'walk';
    const sp = swim ? 7 : 2.4;
    tail.rotation.y = Math.sin(t * sp) * (swim ? 0.55 : 0.25);
    body.rotation.y = Math.sin(t * sp + 1.2) * (swim ? 0.08 : 0.03);
    body.position.y = Math.sin(t * 1.5) * 0.03;
    fins.forEach(({ fg, s }) => { fg.rotation.z = s * Math.sin(t * sp * 0.8) * (k.flippers ? 0.4 : 0.25); });
    const strike = st === 'attack' ? Math.sin(a * Math.PI) : 0;
    body.position.z = strike * 0.25;
    body.rotation.x = -strike * 0.25 + (st === 'hit' ? Math.sin(a * Math.PI * 3) * 0.1 : 0);
  });
}

// ---------------------------------------------------------------- two-legged brutes, giants, goblins and fiends
function biped(k) {
  const root = new THREE.Group(), body = new THREE.Group();
  root.add(body);
  const skin = mat(k.c.main), pale = mat(k.c.belly), dark = mat(k.c.accent);
  const eye = k.glow || k.c.eye === 'glow' ? GLOW_EYE : DARK_EYE;
  const F = { brute: [1.25, 0.9, 1.35], giant: [1.05, 1.2, 1.1], small: [0.8, 0.65, 0.9], imp: [0.75, 0.8, 0.85], lanky: [0.75, 1.3, 1.25] }[k.frame] || [1, 1, 1];
  const W = F[0] * k.girth, LEG = 0.42 * F[1], ARM = 0.5 * F[2] * k.armLen;
  const rock = k.fur === 'rock', bone = k.fur === 'bone';
  const hipY = LEG;
  const torso = grp(body, 0, hipY, 0);
  const chest = m(sph(0.5, 9, 7), skin, 0, 0.3, 0, 0.62 * W, 0.62, 0.42 * W);
  torso.add(chest);
  torso.add(m(sph(0.5, 8, 6), pale, 0, 0.2, 0.06, 0.48 * W, 0.42, 0.34 * W));
  torso.rotation.x = 0.15 * k.stoop * (k.frame === 'brute' || k.frame === 'giant' ? 1.6 : 1);
  if (k.fur === 'shaggy') for (let i = 0; i < 6; i++) torso.add(m(sph(0.09 * W, 5, 4), skin, ((i % 3) - 1) * 0.16 * W, 0.45 + (i > 2 ? 0.08 : -0.05), -0.12 * W));
  if (k.fur === 'warts') { const r = rng(k.seed + 5); for (let i = 0; i < 7; i++) torso.add(m(sph(0.03, 4, 3), dark, (r() - 0.5) * 0.5 * W, 0.15 + r() * 0.35, 0.18 * W)); }
  if (rock) for (let i = 0; i < 6; i++) torso.add(m(new THREE.DodecahedronGeometry(0.1 * W, 0), dark, ((i % 3) - 1) * 0.2 * W, 0.2 + (i > 2 ? 0.25 : 0), (i % 2 ? 0.15 : -0.15) * W));
  if (bone) for (let i = 0; i < 4; i++) torso.add(m(box(0.5 * W, 0.025, 0.02), mat(0xe0d8c0), 0, 0.12 + i * 0.09, 0.2 * W));
  // heads
  const heads = [];
  for (let h = 0; h < k.heads; h++) {
    const head = grp(torso, k.heads > 1 ? (h ? 0.16 : -0.16) * W : 0, 0.66, 0.06);
    const H = 0.3 * k.headSize * (k.frame === 'small' ? 1.35 : 1);
    if (k.head === 'bull') { head.add(m(sph(H * 0.55, 8, 6), skin, 0, 0, 0.05, 0.9, 0.9, 1.1)); head.add(m(box(H * 0.55, H * 0.4, H * 0.5), pale, 0, -H * 0.15, H * 0.45)); }
    else if (k.head === 'snout') { head.add(m(sph(H * 0.5, 8, 6), skin)); head.add(m(cone(H * 0.25, H * 0.6, 6), skin, 0, -H * 0.1, H * 0.5).rotateX(Math.PI / 2)); }
    else head.add(m(sph(H * 0.55, 8, 6), skin, 0, 0, 0, 1, 1.05, 0.95));
    if (k.eyes === 1) { head.add(m(sph(H * 0.17, 8, 6), mat(0xf0f0e0), 0, H * 0.08, H * 0.48)); head.add(m(sph(H * 0.08, 6, 4), eye, 0, H * 0.08, H * 0.6)); }
    else for (const s of [-1, 1]) head.add(m(sph(H * 0.07, 6, 4), eye, s * H * 0.18, H * 0.08, H * 0.48));
    if (k.nose === 'long') head.add(m(cone(H * 0.1, H * 0.45, 5), skin, 0, -H * 0.05, H * 0.62).rotateX(Math.PI / 2 + 0.3));
    else if (k.nose === 'round') head.add(m(sph(H * 0.11, 6, 4), dark, 0, -H * 0.04, H * 0.52));
    if (k.tusks) for (const s of [-1, 1]) head.add(m(cone(H * 0.05, H * 0.22, 4), HORN, s * H * 0.16, -H * 0.2, H * 0.42));
    for (const s of [-1, 1]) {
      if (k.ears === 'big') head.add(m(cone(H * 0.16, H * 0.7, 4), skin, s * H * 0.6, H * 0.15, -H * 0.05).rotateZ(-s * 1.25));
      else if (k.ears === 'pointed') head.add(m(cone(H * 0.1, H * 0.35, 4), skin, s * H * 0.5, H * 0.18, 0).rotateZ(-s * 1.1));
      else if (k.ears === 'small') head.add(m(sph(H * 0.1, 5, 4), skin, s * H * 0.52, H * 0.05, 0, 0.5, 1, 1));
      if (k.horns === 'horns') head.add(m(cone(H * 0.1, H * 0.6, 6), HORN, s * H * 0.35, H * 0.5, 0).rotateZ(-s * 0.5));
      if (k.horns === 'nubs') head.add(m(cone(H * 0.07, H * 0.2, 5), HORN, s * H * 0.22, H * 0.5, H * 0.05));
      if (k.horns === 'curled') { const t = new THREE.Mesh(new THREE.TorusGeometry(H * 0.22, H * 0.07, 5, 10, Math.PI * 1.4), HORN); t.position.set(s * H * 0.42, H * 0.35, 0); t.rotation.y = s * Math.PI / 2; head.add(t); }
      if (k.horns === 'antlers') { const a = m(cyl(H * 0.03, H * 0.04, H * 1.0, 4), HORN, s * H * 0.3, H * 0.8, 0); a.rotation.z = -s * 0.5; head.add(a); }
    }
    if (k.hair === 'topknot') head.add(m(cone(H * 0.15, H * 0.35, 5), dark, 0, H * 0.62, -H * 0.05));
    if (k.hair === 'mane') head.add(m(sph(H * 0.5, 7, 5), dark, 0, H * 0.1, -H * 0.2, 1.1, 1.1, 0.8));
    if (k.hair === 'beard') head.add(m(cone(H * 0.25, H * 0.5, 6), dark, 0, -H * 0.45, H * 0.3).rotateX(Math.PI));
    heads.push(head);
  }
  // arms (shoulders on the torso) and legs (hips under it)
  const arms = [];
  for (const s of [-1, 1]) {
    const sh = grp(torso, s * 0.32 * W, 0.5, 0);
    sh.add(limb(ARM, 0.07 * W, 0.06 * W, skin));
    sh.add(m(sph(0.08 * W, 6, 5), dark, 0, -ARM, 0.02));
    if (s > 0 && k.weapon === 'club') sh.add(m(cyl(0.05, 0.1, 0.6, 6), mat(0x6a4a2a), 0, -ARM - 0.1, 0.25).rotateX(1.3));
    if (s > 0 && k.weapon === 'axe') { sh.add(m(cyl(0.025, 0.025, 0.7, 5), mat(0x6a4a2a), 0, -ARM, 0.25).rotateX(1.3)); sh.add(m(box(0.03, 0.22, 0.18), mat(0x9a9aa4), 0, -ARM + 0.02, 0.55)); }
    if (s > 0 && k.weapon === 'whip') sh.add(m(cyl(0.012, 0.006, 0.9, 4), mat(0xd86a2a, { emissive: 0x6a2a0a }), 0, -ARM - 0.3, 0.3).rotateX(0.5));
    sh.rotation.z = s * 0.12;
    arms.push(sh);
  }
  const legs = [];
  for (const s of [-1, 1]) {
    const hip = grp(body, s * 0.17 * W, hipY, 0);
    hip.add(limb(LEG, 0.09 * W, 0.07 * W, skin));
    hip.add(m(box(0.14 * W, 0.06, 0.2 * W), dark, 0, -LEG, 0.04));
    legs.push(hip);
  }
  if (k.tail !== 'none') {
    const tail = grp(body, 0, hipY + 0.05, -0.15 * W);
    for (let i = 0; i < 5; i++) tail.add(m(sph(0.05 - i * 0.006, 5, 4), skin, 0, -i * 0.04, -0.1 - i * 0.1));
    if (k.tail === 'demon') tail.add(m(cone(0.06, 0.12, 3), dark, 0, -0.2, -0.62).rotateX(-Math.PI / 2));
  }
  const wings = [];
  if (k.wings === 'leather') for (const s of [-1, 1]) {
    const w = grp(torso, s * 0.15 * W, 0.5, -0.2 * W);
    const web = new THREE.Mesh(new THREE.ConeGeometry(0.4, 0.7, 3, 1), mat(k.c.accent, { side: THREE.DoubleSide }));
    web.scale.set(1, 1, 0.05); web.rotation.z = s * 1.9; web.position.set(s * 0.35, 0.15, 0); web.castShadow = true;
    w.add(web); w.userData.wing = s; wings.push({ w, s });
  }
  const heavy = k.frame === 'brute' || k.frame === 'giant';
  return finish(root, body, (t, st, a) => {
    const walk = st === 'walk', sp = walk ? (heavy ? 6 : 9) : 1.6;
    legs.forEach((l, i) => { l.rotation.x = walk ? Math.sin(t * sp + i * Math.PI) * 0.5 : 0; });
    arms.forEach((ar, i) => { ar.rotation.x = walk ? -Math.sin(t * sp + i * Math.PI) * 0.4 : Math.sin(t * 1.4 + i) * 0.05; });
    body.position.y = walk ? Math.abs(Math.sin(t * sp)) * 0.03 : Math.sin(t * 1.6) * 0.006;
    body.rotation.z = walk && heavy ? Math.sin(t * sp) * 0.06 : 0;
    heads.forEach((h, i) => { h.rotation.y = st === 'idle' ? Math.sin(t * 0.5 + i * 2) * 0.3 : 0; });
    wings.forEach(({ w, s }) => { w.rotation.y = s * (0.2 + Math.sin(t * (walk ? 10 : 2)) * (walk ? 0.5 : 0.1)); });
    if (st === 'attack') { const k2 = Math.sin(a * Math.PI); arms[1].rotation.x = -2.2 * k2; arms[0].rotation.x = -0.6 * k2; torso.rotation.x = 0.15 + k2 * 0.3; }
    else torso.rotation.x = 0.15 * k.stoop * (heavy ? 1.6 : 1);
    if (st === 'hit') torso.rotation.x -= Math.sin(a * Math.PI) * 0.3;
  });
}

// ---------------------------------------------------------------- many-legged crawlers
function crawler(k) {
  const root = new THREE.Group(), body = new THREE.Group();
  root.add(body);
  const shell = mat(k.c.main, k.glow ? { emissive: k.c.main, emissiveIntensity: 0.4 } : {}), under = mat(k.c.belly), mark = mat(k.c.accent);
  const eye = k.c.eye === 'glow' || k.kind === 'spider' ? GLOW_EYE : DARK_EYE;
  const spider = k.kind === 'spider', turtle = k.kind === 'turtle', scorp = k.kind === 'scorpion', crab = k.kind === 'crab';
  const y = turtle ? 0.32 : spider ? 0.5 : 0.3;
  const A = k.abdomen;
  let rear;
  if (turtle) { rear = m(sph(0.5, 10, 6), shell, 0, y + 0.02, 0, 1.1, 0.55, 1.25); body.add(rear); body.add(m(cyl(0.53, 0.55, 0.06, 10), under, 0, y - 0.1, 0, 1, 1, 1.15)); }
  else if (crab) { rear = m(sph(0.5, 10, 6), shell, 0, y, 0, 1.2, 0.45, 0.85); body.add(rear); }
  else { rear = m(sph(0.4 * A, 10, 8), shell, 0, y + 0.05, -0.38 * A, 1, spider ? 0.85 : 0.6, 1.25); body.add(rear); }
  if (!turtle && !crab) body.add(m(sph(0.2, 8, 6), shell, 0, y, 0.08, 1, 0.75, 1.15));
  if (k.pattern === 'mark' && !turtle) body.add(m(sph(0.12, 7, 5), mark, 0, y + 0.3 * A, -0.4 * A, 1, 0.3, 1.3));
  if (k.pattern === 'bands') for (let i = 0; i < 3; i++) body.add(m(new THREE.TorusGeometry(0.3 * A - i * 0.05, 0.035, 4, 12), mark, 0, y + 0.05, -0.3 * A - i * 0.16).rotateY(0));
  if (k.pattern === 'spots') { const r = rng(k.seed + 9); for (let i = 0; i < 6; i++) body.add(m(sph(0.05, 5, 4), mark, (r() - 0.5) * 0.4, y + 0.28, -0.4 * A + (r() - 0.5) * 0.4, 1, 0.4, 1)); }
  if (turtle) for (let i = 0; i < 5; i++) body.add(m(new THREE.CylinderGeometry(0.12, 0.14, 0.05, 6), mark, (i % 2 ? 0.2 : -0.2) * (i > 3 ? 0 : 1), y + 0.26, 0.25 - i * 0.12));
  if (k.hairy) for (let i = 0; i < 10; i++) body.add(m(cone(0.03, 0.12, 3), mark, Math.sin(i) * 0.25, y + 0.22, -0.3 * A + Math.cos(i * 1.7) * 0.25));
  // head
  const head = grp(body, 0, turtle ? y : y + 0.02, turtle ? 0.6 : crab ? 0.38 : 0.28);
  const H = 0.18 * k.headSize;
  head.add(m(sph(H, 8, 6), turtle ? under : shell));
  if (spider) for (const [x, yy] of [[-0.05, 0.08], [0.05, 0.08], [-0.09, 0.03], [0.09, 0.03]]) head.add(m(sph(0.025, 5, 4), eye, x, yy, H * 0.9));
  else for (const s of [-1, 1]) head.add(m(sph(0.03, 5, 4), eye, s * H * 0.6, H * 0.4, H * 0.75));
  if (k.kind === 'insect') for (const s of [-1, 1]) head.add(m(cyl(0.008, 0.006, 0.3, 3), mark, s * 0.06, H + 0.1, H * 0.6).rotateX(0.7).rotateZ(-s * 0.4));
  if (spider) for (const s of [-1, 1]) head.add(m(cone(0.025, 0.1, 4), mat(0x222222), s * 0.05, -H * 0.6, H * 0.8).rotateX(Math.PI));
  // claws
  const claws = [];
  if (k.claws) for (const s of [-1, 1]) {
    const c = grp(body, s * (crab ? 0.45 : 0.2), y, crab ? 0.35 : 0.42);
    c.add(m(cyl(0.035, 0.03, 0.35, 5), shell, s * 0.12, 0, 0.1).rotateZ(s * 1.1));
    c.add(m(sph(0.1, 6, 5), shell, s * 0.25, 0.05, 0.25, 0.8, 0.6, 1.4));
    c.add(m(cone(0.04, 0.16, 4), mark, s * 0.22, 0.05, 0.4).rotateX(Math.PI / 2));
    claws.push(c);
  }
  // tail and stinger
  let tail = null;
  if (k.kind === 'scorpion' && k.stinger) {
    tail = grp(body, 0, y + 0.05, -0.55 * A);
    for (let i = 0; i < 5; i++) tail.add(m(sph(0.07 - i * 0.006, 6, 5), shell, 0, i * 0.11, -i * 0.05 + (i > 2 ? (i - 2) * 0.08 : 0)));
    tail.add(m(cone(0.04, 0.16, 5), mark, 0, 0.58, 0.18).rotateX(2.2));
  } else if (k.stinger) body.add(m(cone(0.04, 0.16, 5), mark, 0, y, -0.38 * A - 0.5 * A).rotateX(-Math.PI / 2));
  if (turtle) body.add(m(cone(0.06, 0.18, 5), under, 0, y - 0.05, -0.65).rotateX(-Math.PI / 2));
  // wings
  const wings = [];
  if (k.wings !== 'none') for (const s of [-1, 1]) {
    const w = grp(body, s * 0.1, y + 0.2, 0);
    const broad = k.wings === 'broad';
    const wm = mat(broad ? k.c.accent : 0xe8f0ff, { transparent: !broad, opacity: broad ? 1 : 0.45, side: THREE.DoubleSide });
    w.add(m(sph(0.5, 6, 4), wm, s * (broad ? 0.35 : 0.25), 0, -0.05, broad ? 0.7 : 0.5, 0.02, broad ? 0.55 : 0.2));
    w.userData.wing = s;
    wings.push({ w, s });
  }
  // legs
  const legs = [];
  const n = turtle ? 4 : k.legs;
  const per = n / 2, L = (spider ? 0.62 : turtle ? 0.25 : 0.42) * k.legLen;
  const legMat = turtle ? under : mark;
  for (let i = 0; i < n; i++) {
    const s = i < per ? -1 : 1, j = i % per;
    const hip = grp(body, s * (turtle ? 0.38 : crab ? 0.42 : 0.14), y, (turtle ? 0.3 - j * 0.6 : (crab ? 0.15 : 0.2) - j * ((crab ? 0.35 : 0.4) / Math.max(1, per - 1))));
    hip.rotation.y = s * (0.35 - j * (0.7 / Math.max(1, per - 1))) + (s < 0 ? Math.PI : 0);
    const up = m(cyl(0.025, 0.022, L, 5).translate(0, L / 2, 0), legMat);
    up.rotation.z = turtle ? -1.4 : -0.95;
    const knee = grp(hip, Math.sin(turtle ? 1.4 : 0.95) * L, Math.cos(turtle ? 1.4 : 0.95) * L, 0);
    if (!turtle) { const lo = m(cyl(0.02, 0.01, L * 1.05, 5).translate(0, -L * 0.52, 0), legMat); lo.rotation.z = 0.35; knee.add(lo); }
    hip.add(up);
    legs.push({ hip, phase: (j % 2 ? Math.PI : 0) + (s < 0 ? 0 : Math.PI) });
  }
  return finish(root, body, (t, st, a) => {
    const walk = st === 'walk', sp = walk ? (turtle ? 4 : 13) : 2;
    legs.forEach(l => { const s = Math.sin(t * sp + l.phase); l.hip.rotation.x = walk ? s * 0.35 : s * 0.03; });
    body.position.y = (wings.length && walk ? 0.1 : 0) + (walk ? Math.sin(t * sp * 2) * 0.015 : Math.sin(t * 1.5) * 0.01);
    wings.forEach(({ w, s }) => { w.rotation.z = s * Math.sin(t * (k.wings === 'broad' ? 8 : 40)) * 0.5; });
    const strike = st === 'attack' ? Math.sin(a * Math.PI) : 0;
    head.position.z = (turtle ? 0.6 : crab ? 0.38 : 0.28) + strike * 0.08;
    claws.forEach((c, i) => { c.rotation.y = (i ? -1 : 1) * strike * 0.6; });
    if (tail) tail.rotation.x = strike * 0.8;
    body.rotation.x = st === 'hit' ? Math.sin(a * Math.PI * 3) * 0.08 : 0;
  });
}

// ---------------------------------------------------------------- serpents and worms
function serpent(k) {
  const root = new THREE.Group(), body = new THREE.Group();
  root.add(body);
  const scale = mat(k.c.main), belly = mat(k.c.belly), mark = mat(k.c.accent);
  const eye = k.c.eye === 'glow' ? GLOW_EYE : DARK_EYE;
  const G = k.girth, n = k.segs;
  const segs = [];
  for (let i = 0; i < n; i++) {
    const f = 1 - i / (n + 2);
    const band = (k.pattern === 'bands' && i % 2) || (k.pattern === 'rings' && i % 3 === 0) || (k.pattern === 'stripe' && false);
    const seg = keep(m(sph(G * f, 7, 5), band ? mark : scale, 0, G * f * 0.85, -i * G * 1.25, 1, 0.85, 1.25));
    body.add(seg);
    if (k.pattern === 'diamonds' && i % 2 === 0) body.add(m(new THREE.OctahedronGeometry(G * f * 0.4, 0), mark, 0, G * f * 1.55, -i * G * 1.25, 1, 0.3, 1.2));
    if (k.pattern === 'blotches' && i % 3 === 1) body.add(m(sph(G * f * 0.5, 5, 4), mark, 0, G * f * 1.5, -i * G * 1.25, 1.2, 0.3, 1));
    if (k.pattern === 'stripe') body.add(m(box(G * 0.25, 0.01, G * 1.3), mark, 0, G * f * 1.72, -i * G * 1.25));
    if (k.frill && i % 2 === 0 && i < n - 2) body.add(m(cone(G * 0.3, G * 0.7, 3), mark, 0, G * f * 1.8, -i * G * 1.25, 0.2, 1, 1));
    if (k.legsOn) for (const s of [-1, 1]) body.add(m(cyl(0.012, 0.008, G * 1.4, 3), mark, s * G * 0.9, G * 0.4, -i * G * 1.25).rotateZ(s * 1.2));
    segs.push({ seg, z: -i * G * 1.25, f });
  }
  if (k.feathered) for (const s of [-1, 1]) body.add(m(sph(0.5, 6, 4), mark, s * G * 2.5, G * 1.6, -G * 2, G * 3, 0.05, G * 1.8));
  // heads at the front, raised
  const heads = [];
  for (let h = 0; h < k.heads; h++) {
    const spread = k.heads > 1 ? (h - (k.heads - 1) / 2) * G * 2.2 : 0;
    const neck = grp(body, spread, G, G * 0.6);
    for (let i = 0; i < 3; i++) neck.add(m(sph(G * (0.9 - i * 0.05), 7, 5), scale, 0, G * 0.9 * (i + 1), G * 0.4 * i));
    const head = grp(neck, 0, G * 3.4, G * 1.2);
    const H = G * 1.25;
    if (k.head === 'maw') { head.add(m(cyl(H * 0.8, H * 0.9, H * 1.0, 8), scale).rotateX(Math.PI / 2)); head.add(m(cyl(H * 0.6, H * 0.6, 0.02, 8), mat(0x3a0a0a), 0, 0, H * 0.52).rotateX(Math.PI / 2)); for (let i = 0; i < 6; i++) head.add(m(cone(H * 0.08, H * 0.3, 3), HORN, Math.cos(i) * H * 0.5, Math.sin(i) * H * 0.5, H * 0.5).rotateX(Math.PI / 2)); }
    else {
      head.add(m(sph(H, 8, 6), scale, 0, 0, H * 0.3, k.head === 'wedge' ? 1.25 : 1, 0.7, 1.5));
      head.add(m(sph(H * 0.8, 7, 5), belly, 0, -H * 0.25, H * 0.5, 1, 0.4, 1.3));
      if (k.head === 'hood') head.add(m(sph(H * 1.4, 8, 5), mark, 0, -H * 0.2, -H * 0.4, 1.4, 1.2, 0.2));
      if (k.head === 'mandible') for (const s of [-1, 1]) head.add(m(cone(H * 0.15, H * 0.8, 4), mark, s * H * 0.4, -H * 0.2, H * 1.4).rotateX(Math.PI / 2).rotateY(-s * 0.4));
      if (!k.eyesOff) for (const s of [-1, 1]) head.add(m(sph(H * 0.16, 5, 4), eye, s * H * 0.55, H * 0.28, H * 0.75));
    }
    heads.push({ neck, head });
  }
  return finish(root, body, (t, st, a) => {
    const walk = st === 'walk', sp = walk ? 7 : 1.8;
    segs.forEach(({ seg, z, f }, i) => { seg.position.x = Math.sin(t * sp - i * 0.7) * G * (walk ? 1.2 : 0.4) * k.coil; });
    const strike = st === 'attack' ? Math.sin(a * Math.PI) : 0;
    heads.forEach(({ neck, head }, i) => {
      neck.rotation.x = strike * 0.9 - (st === 'idle' ? Math.sin(t * 1.3 + i) * 0.08 : 0);
      neck.rotation.z = Math.sin(t * 1.1 + i * 1.7) * 0.12;
      head.rotation.x = -strike * 0.4;
    });
    body.rotation.x = st === 'hit' ? Math.sin(a * Math.PI * 3) * 0.06 : 0;
  }, { byHeight: true });
}

// ---------------------------------------------------------------- dragons and wyverns
function dragon(k) {
  const root = new THREE.Group(), body = new THREE.Group();
  root.add(body);
  const scale = mat(k.c.main), belly = mat(k.bony ? 0x3a3438 : k.c.belly), dark = mat(k.c.accent);
  const eye = k.c.eye === 'glow' || k.bony ? GLOW_EYE : mat(0xe8c040, { emissive: 0x6a4a00 });
  const G = 0.42 * k.girth, two = k.legs === 2;
  const y = two ? 0.62 : 0.5;
  const torso = m(sph(0.5, 10, 8), k.bony ? dark : scale, 0, y, 0, G * 2, G * 1.9, 1.15);
  body.add(torso);
  body.add(m(sph(0.5, 9, 7), belly, 0, y - G * 0.35, 0.05, G * 1.6, G * 1.1, 0.95));
  if (k.bony) for (let i = 0; i < 5; i++) body.add(m(new THREE.TorusGeometry(G * 0.85, 0.025, 4, 10, Math.PI), mat(0xd8d0c0), 0, y, 0.3 - i * 0.15).rotateY(0).rotateZ(0));
  if (k.shell) body.add(m(sph(0.6, 10, 6), dark, 0, y + 0.12, -0.05, 1.3, 0.6, 1.25));
  for (let i = 0; i < 6; i++) body.add(m(cone(0.05, 0.16, 4), dark, 0, y + G * 0.92, 0.35 - i * 0.14));
  // neck and head
  const neck = grp(body, 0, y + G * 0.4, 0.5);
  const NL = 0.55 * k.neck * (k.young ? 0.7 : 1);
  for (let i = 0; i < 4; i++) neck.add(m(sph(0.13 - i * 0.012, 7, 5), k.bony ? dark : scale, 0, i * NL * 0.28, i * NL * 0.2));
  const head = grp(neck, 0, NL * 1.1, NL * 0.85);
  const H = 0.22 * (k.young ? 1.3 : 1);
  head.add(m(sph(H, 8, 6), k.bony ? mat(0xe0d8c8) : scale, 0, 0, 0, 0.9, 0.8, 1.1));
  head.add(m(box(H * 0.8, H * 0.45, H * 1.2), k.bony ? mat(0xe0d8c8) : scale, 0, -H * 0.2, H * 0.8));
  const jaw = keep(m(box(H * 0.7, H * 0.18, H * 1.0), belly, 0, -H * 0.5, H * 0.7));
  head.add(jaw);
  for (const s of [-1, 1]) {
    head.add(m(sph(H * 0.14, 6, 4), eye, s * H * 0.42, H * 0.2, H * 0.45));
    if (k.horns === 'horns') head.add(m(cone(H * 0.12, H * 0.9, 5), HORN, s * H * 0.35, H * 0.55, -H * 0.4).rotateX(-0.9));
  }
  if (k.frill) for (let i = 0; i < 4; i++) head.add(m(cone(H * 0.08, H * 0.5, 3), dark, 0, H * 0.4, -H * 0.3 - i * H * 0.2).rotateX(-1.1));
  // wings
  const wings = [];
  if (k.wings === 'leather') for (const s of [-1, 1]) {
    const sh = grp(body, s * G * 0.8, y + G * 0.6, 0.15);
    const span = 1.05 * k.wing * (k.young ? 0.6 : 1);
    const arm = m(cyl(0.03, 0.02, span, 5), dark, s * span / 2, 0.05, 0); arm.rotation.z = Math.PI / 2; sh.add(arm);
    const web = new THREE.Mesh(new THREE.ConeGeometry(span * 0.55, span, 3, 1), mat(k.bony ? 0x8a8070 : k.c.accent, { side: THREE.DoubleSide, transparent: k.bony, opacity: k.bony ? 0.5 : 1 }));
    web.scale.set(1, 1, 0.04); web.rotation.z = s * Math.PI / 2; web.rotation.x = 0.3; web.position.set(s * span * 0.5, -span * 0.15, -span * 0.15); web.castShadow = true;
    sh.add(web);
    sh.userData.wing = s;
    wings.push({ sh, s });
  }
  // legs
  const legs = [];
  const spots = two ? [[-1, -0.15], [1, -0.15]] : [[-1, 0.3], [1, 0.3], [-1, -0.3], [1, -0.3]];
  for (const [s, z] of spots) {
    const hip = grp(body, s * G * 0.7, y - G * 0.4, z);
    const L = y - G * 0.4;
    hip.add(limb(L, 0.07, 0.05, scale));
    for (let c = -1; c <= 1; c++) hip.add(m(cone(0.025, 0.1, 3), HORN, c * 0.04, -L, 0.08).rotateX(Math.PI / 2));
    legs.push({ hip, phase: s * (z > 0 ? 1 : -1) > 0 ? 0 : Math.PI });
  }
  // tail
  const tail = grp(body, 0, y, -0.55);
  const tseg = [];
  for (let i = 0; i < 7; i++) { const sgm = keep(m(sph(0.12 - i * 0.014, 6, 5), scale, 0, -i * 0.03, -i * 0.15)); tail.add(sgm); tseg.push(sgm); }
  if (k.tail === 'spade') tail.add(m(new THREE.OctahedronGeometry(0.1, 0), dark, 0, -0.22, -1.1, 1, 0.3, 1.4));
  return finish(root, body, (t, st, a) => {
    const walk = st === 'walk', sp = walk ? 6 : 1.4;
    legs.forEach(l => { l.hip.rotation.x = walk ? Math.sin(t * sp + l.phase) * 0.45 : 0; });
    wings.forEach(({ sh, s }) => { sh.rotation.z = s * (walk ? Math.sin(t * 5) * 0.6 : 0.1 + Math.sin(t * 0.8) * 0.06); });
    body.position.y = walk && wings.length ? 0.12 + Math.sin(t * 5) * 0.05 : Math.sin(t * 1.2) * 0.01;
    tseg.forEach((sgm, i) => { sgm.position.x = Math.sin(t * (walk ? 4 : 1.2) - i * 0.5) * 0.04 * i; });
    const strike = st === 'attack' ? Math.sin(a * Math.PI) : 0;
    neck.rotation.x = strike * 0.6 + (st === 'idle' ? Math.sin(t * 0.6) * 0.05 : 0);
    jaw.rotation.x = strike * 0.5;
    jaw.position.y = -H * 0.5 - strike * H * 0.15;
    body.rotation.x = st === 'hit' ? -Math.sin(a * Math.PI) * 0.12 : 0;
  });
}

// ---------------------------------------------------------------- ghosts, shades and elementals
const SPIRIT_EYE = { white: 0xffffff, gold: 0xffd060, red: 0xff4030, blue: 0x60b0ff, green: 0x70ff90 };
function spirit(k) {
  const root = new THREE.Group(), body = new THREE.Group();
  root.add(body);
  const form = k.form;
  const glowy = form === 'flame' || form === 'wisp' || form === 'ice';
  const veil = new THREE.MeshStandardMaterial({ color: k.c.main, roughness: 0.6, flatShading: true, transparent: true, opacity: form === 'shade' ? 0.9 : 0.72,
    emissive: glowy ? k.c.main : 0x000000, emissiveIntensity: glowy ? 0.7 : 0 });
  const inner = mat(k.c.accent, { transparent: true, opacity: 0.8 });
  const eyeMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(SPIRIT_EYE[k.eyeColor] || 0xffffff).multiplyScalar(1.6) });
  const W = k.wide, T = k.tall;
  const core = grp(body, 0, 0.75 * T, 0);
  let headY = 0.35;
  if (form === 'wisp') { core.add(m(sph(0.18, 10, 8), veil)); core.add(m(sph(0.09, 8, 6), eyeMat)); headY = 0; }
  else if (form === 'hands') { for (const s of [-1, 1]) { core.add(m(sph(0.12, 7, 5), veil, s * 0.18, 0, 0, 1, 0.6, 1.4)); for (let f = 0; f < 4; f++) core.add(m(cyl(0.02, 0.015, 0.14, 4), veil, s * 0.18 + (f - 1.5) * 0.05, 0, 0.18).rotateX(Math.PI / 2)); } headY = 0; }
  else {
    core.add(m(cone(0.32 * W, 0.9 * T, 8, 1, true), veil, 0, -0.1, 0).rotateX(Math.PI));
    core.add(m(sph(0.2 * W, 8, 6), veil, 0, headY, 0));
    if (k.hood) core.add(m(sph(0.25 * W, 8, 6, 0, Math.PI * 2, 0, Math.PI * 0.6), inner, 0, headY + 0.03, -0.03));
    if (form === 'wail') for (let i = 0; i < 5; i++) core.add(m(cyl(0.012, 0.004, 0.5, 3), inner, (i - 2) * 0.05, headY - 0.2, -0.12).rotateX(0.2));
    for (const s of [-1, 1]) core.add(m(sph(0.035, 6, 4), eyeMat, s * 0.07 * W, headY + 0.02, 0.17 * W));
    if (k.arms) for (const s of [-1, 1]) core.add(m(cone(0.06, 0.45, 5), veil, s * 0.3 * W, 0.1, 0.05).rotateZ(s * 2.4));
    if (form === 'flame') for (let i = 0; i < 6; i++) core.add(m(cone(0.07, 0.35, 5), veil, Math.cos(i) * 0.15, headY + 0.15 + (i % 2) * 0.08, Math.sin(i) * 0.12));
    if (form === 'ice') for (let i = 0; i < 6; i++) core.add(m(new THREE.OctahedronGeometry(0.08, 0), veil, Math.cos(i) * 0.25 * W, (i % 3) * 0.15 - 0.1, Math.sin(i) * 0.2, 0.6, 1.6, 0.6));
    if (form === 'water') core.add(m(new THREE.TorusGeometry(0.28 * W, 0.04, 5, 14), inner, 0, -0.3, 0).rotateX(Math.PI / 2));
    if (form === 'wind') for (let i = 0; i < 3; i++) core.add(m(new THREE.TorusGeometry(0.2 + i * 0.08, 0.02, 4, 14), inner, 0, -0.1 - i * 0.18, 0).rotateX(Math.PI / 2));
  }
  // trailing wisps
  const trail = [];
  for (let i = 0; i < k.trail && form !== 'hands'; i++) { const w = keep(m(sph(0.06 - i * 0.008, 5, 4), veil, 0, -0.45 * T - i * 0.06, -0.05 - i * 0.07)); core.add(w); trail.push(w); }
  return finish(root, body, (t, st, a) => {
    const walk = st === 'walk';
    core.position.y = 0.75 * T + Math.sin(t * 1.8 * k.sway) * 0.05;
    core.rotation.z = Math.sin(t * 1.3 * k.sway) * (walk ? 0.12 : 0.05);
    core.rotation.x = walk ? 0.25 : 0;
    trail.forEach((w, i) => { w.position.x = Math.sin(t * 3 - i * 0.8) * 0.05 * (i + 1); });
    const strike = st === 'attack' ? Math.sin(a * Math.PI) : 0;
    core.position.z = strike * 0.25;
    core.scale.setScalar(1 + strike * 0.15 + (st === 'hit' ? Math.sin(a * Math.PI) * -0.1 : 0));
  });
}

// ---------------------------------------------------------------- oozes, frogs, jellies and clams
function blob(k) {
  const root = new THREE.Group(), body = new THREE.Group();
  root.add(body);
  const goo = new THREE.MeshStandardMaterial({ color: k.c.main, roughness: 0.25, metalness: 0.05, transparent: k.form !== 'frog' && k.form !== 'clam', opacity: 0.82, flatShading: k.form === 'frog' || k.form === 'clam' });
  const deep = mat(k.c.accent), pale = mat(k.c.belly);
  let main = null, jaw = null;
  const tent = [];
  if (k.form === 'frog') {
    main = keep(m(sph(0.5, 9, 7), goo, 0, 0.32, 0, 1.0, 0.6, 1.0)); body.add(main);
    body.add(m(sph(0.45, 8, 6), pale, 0, 0.26, 0.08, 0.9, 0.45, 0.9));
    for (const s of [-1, 1]) { body.add(m(sph(0.12, 7, 5), goo, s * 0.22, 0.58, 0.25)); body.add(m(sph(0.06, 6, 4), DARK_EYE, s * 0.24, 0.62, 0.33)); body.add(m(sph(0.16, 6, 4), goo, s * 0.38, 0.12, -0.15, 0.8, 0.5, 1.6)); }
    jaw = keep(m(box(0.6, 0.02, 0.3), deep, 0, 0.24, 0.35)); body.add(jaw);
  } else if (k.form === 'clam') {
    main = keep(m(sph(0.5, 10, 5, 0, Math.PI * 2, 0, Math.PI / 2), goo, 0, 0.12, 0, 1.2, 0.5, 1.0)); body.add(main);
    jaw = keep(m(sph(0.5, 10, 5, 0, Math.PI * 2, 0, Math.PI / 2), pale, 0, 0.12, 0, 1.2, 0.5, 1.0)); jaw.rotation.x = Math.PI; body.add(jaw);
    for (let i = 0; i < 5; i++) main.add(m(box(0.02, 0.2, 0.9), deep, (i - 2) * 0.18, 0.35, 0));
    body.add(m(sph(0.08, 8, 6), mat(0xf4f0ff, { emissive: 0x404050 }), 0, 0.15, 0.1));
  } else if (k.form === 'jelly') {
    main = keep(m(sph(0.5, 12, 7, 0, Math.PI * 2, 0, Math.PI / 2), goo, 0, 0.55, 0, 1, 0.7, 1)); body.add(main);
    for (let i = 0; i < 8; i++) { const tt = keep(m(cyl(0.02, 0.005, 0.55, 3), goo, Math.cos(i * 0.8) * 0.3, 0.3, Math.sin(i * 0.8) * 0.3)); body.add(tt); tent.push(tt); }
  } else if (k.form === 'cube') {
    main = keep(m(box(0.9, 0.9, 0.9), goo, 0, 0.45, 0)); body.add(main);
    body.add(m(new THREE.DodecahedronGeometry(0.12, 0), mat(0xd8d0c0), 0.1, 0.35, 0.05));
  } else {
    const flat = k.form === 'ooze' ? 0.5 : 0.85;
    main = keep(m(sph(0.5, 14, 10), goo, 0, 0.42 * flat, 0, 1.2 - flat * 0.2, flat, 1.2 - flat * 0.2)); body.add(main);
    body.add(m(sph(0.2, 8, 6), deep, 0, 0.38 * flat, 0, 1, 0.8, 1));
  }
  if (k.form !== 'frog' && k.form !== 'clam' && k.form !== 'cube') {
    const n = k.eyes;
    for (let i = 0; i < n; i++) body.add(m(sph(0.06, 7, 5), DARK_EYE, (i - (n - 1) / 2) * 0.17, k.form === 'jelly' ? 0.6 : 0.5, 0.4));
  }
  for (let i = 0; i < k.bubbles; i++) body.add(m(sph(0.04 + (i % 2) * 0.02, 5, 4), pale, Math.cos(i * 2) * 0.2, 0.3 + i * 0.07, Math.sin(i * 2) * 0.2));
  return finish(root, body, (t, st, a) => {
    const walk = st === 'walk';
    const w = Math.sin(t * (walk ? 8 : 2.5));
    const hop = walk && k.form === 'frog' ? Math.max(0, w) : walk && k.form !== 'clam' ? Math.max(0, w) * 0.5 : 0;
    body.position.y = hop * 0.2 + (k.form === 'jelly' ? 0.15 + Math.sin(t * 1.5) * 0.06 : 0);
    if (k.form !== 'frog' && k.form !== 'clam') main.scale.y = (k.form === 'cube' ? 1 : (k.form === 'ooze' ? 0.5 : 0.85)) * (1 - w * 0.06 * k.squish);
    tent.forEach((tt, i) => { tt.rotation.x = Math.sin(t * 2 + i) * 0.3; });
    const strike = st === 'attack' ? Math.sin(a * Math.PI) : 0;
    if (jaw && k.form === 'clam') jaw.rotation.x = Math.PI + strike * 0.6 + Math.max(0, Math.sin(t * 0.7)) * 0.1;
    if (jaw && k.form === 'frog') jaw.position.z = 0.35 + strike * 0.4;
    body.position.z = strike * 0.15;
  });
}

// scale to 1 m tall, feet on the ground, and hand over as a ProcActor
// One creature's materials: its plain coloured parts baked into one vertex-coloured material per
// moving part (a body draws in a handful of calls, not sixty), its glowing or see-through parts
// on copies of their own, so a hit flash lights this creature and no other.
const plain = mt => mt && mt.isMeshStandardMaterial && !mt.transparent && mt.emissive.getHex() === 0 && mt.side === THREE.FrontSide;
function prepGeo(c, color) {
  c.updateMatrix();
  let g = c.geometry.index ? c.geometry.toNonIndexed() : c.geometry.clone();
  for (const name of Object.keys(g.attributes)) if (!['position', 'normal', 'uv'].includes(name)) g.deleteAttribute(name);
  if (!g.attributes.uv) g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
  if (!g.attributes.normal) g.computeVertexNormals();
  if (color) {
    const n = g.attributes.position.count, arr = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { arr[i * 3] = color.r; arr[i * 3 + 1] = color.g; arr[i * 3 + 2] = color.b; }
    g.setAttribute('color', new THREE.BufferAttribute(arr, 3));
  }
  return g.applyMatrix4(c.matrix);
}
function mergeStill(node, own) {
  for (const child of [...node.children]) if (!child.isMesh) mergeStill(child, own);
  const groups = new Map();
  for (const c of [...node.children]) {
    if (!c.isMesh || !c.geometry) continue;
    if (c.userData.keep) { c.material = own.copy(c.material); continue; }
    const key = plain(c.material) ? 'coat' : c.material;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(c);
  }
  for (const [key, list] of groups) {
    const coat = key === 'coat';
    if (!coat && list.length < 2) { list[0].material = own.copy(list[0].material); continue; }
    const merged = mergeGeometries(list.map(c => prepGeo(c, coat ? c.material.color : null)), false);
    if (!merged) { list.forEach(c => { c.material = own.copy(c.material); }); continue; }
    const one = new THREE.Mesh(merged, coat ? own.coat : own.copy(key));
    one.castShadow = true;
    list.forEach(c => node.remove(c));
    node.add(one);
  }
}
function ownMaterials() {
  const copies = new Map();
  return {
    coat: new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, flatShading: true }),
    copy(mt) { if (!copies.has(mt)) copies.set(mt, mt.clone()); return copies.get(mt); },
  };
}

function finish(root, body, animate, { byHeight = false } = {}) {
  mergeStill(body, ownMaterials());
  root.updateMatrixWorld(true);
  const bb = new THREE.Box3().setFromObject(root);
  // a creature's size is its height, or most of its length when it is long and low (a lizard,
  // a shark): a giant lizard grows long, not tall as a house
  const h = Math.max(0.05, bb.max.y - bb.min.y, byHeight ? 0 : (bb.max.z - bb.min.z) * 0.6);
  const inner = new THREE.Group();
  while (root.children.length) inner.add(root.children[0]);
  inner.scale.setScalar(1 / h);
  inner.position.y = -bb.min.y / h;
  root.add(inner);
  return new ProcActor(root, body, animate);
}

const BUILD = { quad, bird, fish, biped, crawler, serpent, dragon, spirit, blob };
export const KIN_PLANS = Object.keys(BUILD);

// a creature body from its recipe, `height` metres tall
export function makeKin(recipe, { height = 1 } = {}) {
  const a = BUILD[recipe.plan](recipe);
  a.root.scale.setScalar(height);
  ownBody(a.root);      // its buffers and materials are its alone: freed when it is cleared away (freebody.js)
  return a;
}
