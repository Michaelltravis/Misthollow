// What a harm looks like on a body while it lasts (wards.js draws them; the server names them:
// map_system._wards): a poison's bubbles, a burn's flames, a frost's falling rime, a bleed's drips
// and the spots they leave, a sleeper's Zzz, the sweat of fear, a charm's hearts, a silence's
// hushed speech. Each kind is an emitter called every frame with its own clock, kept to time
// (not frames) so a slow machine sees as much, a few a frame at most.
import * as THREE from 'three';

export const HAZE = 0x9ad43a;               // a poison's haze about the body
const _p = new THREE.Vector3();

// a point on the body: round its middle (r), at a share of its height (from..to)
function onBody(root, s, lift, from, to, out = _p) {
  const a = Math.random() * Math.PI * 2, r = 0.16 + s.w * 0.3;
  const pos = root.position;
  return out.set(pos.x + Math.cos(a) * r, pos.y + lift + s.h * (from + Math.random() * (to - from)), pos.z + Math.sin(a) * r);
}
const overHead = (root, s, lift, out = _p) => out.set(root.position.x + (Math.random() - 0.5) * 0.2, root.position.y + lift + s.h + 0.15, root.position.z + (Math.random() - 0.5) * 0.2);

// kind -> [[every (s), jitter (s), emit(fx, root, s, lift)]...]
export const HARMS = {
  poison: [
    [0.07, 0.09, (fx, root, s, lift) => fx.glyph(onBody(root, s, lift, 0.25, 0.9), { glyph: 'bubble', count: 1, color: 0x8cff4a, bright: 2,
      speed: 0.12, up: 0.6, spread: 0.6, life: 1.3, size: 0.2 + Math.random() * 0.16, drag: 0.8, grow: 0.06 })],
    [0.2, 0.15, (fx, root, s, lift) => fx.p.emit(onBody(root, s, lift, 0.15, 0.75), { count: 1, color: HAZE, bright: 0.75, speed: 0.12,
      up: 0.22, life: 1.7, size: 0.55, grow: 0.6, drag: 1 })],
  ],
  burn: [
    [0.02, 0.03, (fx, root, s, lift) => fx.p.emit(onBody(root, s, lift, 0.05, 0.95), { count: 1, color: Math.random() < 0.5 ? 0xff6a10 : 0xffb43a,
      bright: 2.6, speed: 0.25, up: 1.6, life: 0.6, size: 0.36, grow: -0.35, drag: 1 })],
    [0.07, 0.06, (fx, root, s, lift) => fx.glyph(onBody(root, s, lift, 0.15, 0.95), { glyph: 'flame', count: 1, color: 0xff7a1a, bright: 2.4,
      speed: 0.15, up: 1.2, life: 0.6, size: 0.5, drag: 1, rot: 0 })],
    [0.25, 0.1, (fx, root, s, lift) => fx.p.emit(overHead(root, s, lift), { count: 1, color: 0x8a7a6a, bright: 0.45, speed: 0.15,
      up: 0.7, life: 1.6, size: 0.45, grow: 0.7, drag: 0.8 })],
  ],
  frost: [
    [0.1, 0.08, (fx, root, s, lift) => fx.glyph(onBody(root, s, lift, 0.4, 1.05), { glyph: 'snow', count: 1, color: 0xd8f2ff, bright: 1.6,
      speed: 0.1, up: -0.35, life: 1.4, size: 0.14, drag: 0.6, spin: 1 })],
    [0.18, 0.1, (fx, root, s, lift) => fx.p.emit(onBody(root, s, lift, 0.0, 0.3), { count: 1, color: 0xcfeaff, bright: 0.9, speed: 0.2,
      up: 0.05, life: 1.2, size: 0.4, grow: 0.4, drag: 2 })],
  ],
  // drops from the wound, and the spots they leave on the ground a while
  bleed: [
    [0.22, 0.2, (fx, root, s, lift) => fx.glyph(onBody(root, s, lift, 0.35, 0.7), { glyph: 'drop', count: 1, color: 0xb81414, bright: 1.1,
      speed: 0.25, up: -0.4, gravity: 6, life: 0.5, size: 0.12, drag: 0.3, rot: 0 })],
    [0.5, 0.4, (fx, root, s, lift) => { const p = onBody(root, s, lift, 0, 0); p.y = root.position.y + 0.03;
      fx.p.emit(p, { count: 1, color: 0x6a0808, bright: 0.9, speed: 0, life: 3.5, size: 0.16, drag: 0, spread: 0 }); }],
  ],
  zzz: [
    [0.9, 0.3, (fx, root, s, lift) => fx.glyph(overHead(root, s, lift), { glyph: 'zzz', count: 1, color: 0xd6e4ff, bright: 1.5, speed: 0.1,
      up: 0.35, dir: new THREE.Vector3(0.25, 0, 0), life: 1.8, size: 0.28, grow: 0.12, drag: 0.4, rot: 0 })],
  ],
  fear: [
    [0.18, 0.12, (fx, root, s, lift) => fx.glyph(onBody(root, s, lift, 0.75, 1.0), { glyph: 'drop', count: 1, color: 0xbfe6ff, bright: 1.6, speed: 0.7,
      up: 0.9, gravity: 5, life: 0.7, size: 0.18, drag: 0.5, rot: 0 })],
  ],
  // a curse: dark wisps curling up round the body, and a gloom at its feet
  curse: [
    [0.16, 0.1, (fx, root, s, lift) => fx.glyph(onBody(root, s, lift, 0.1, 0.8), { glyph: 'wisp', count: 1, color: 0x9a4ad8, bright: 1.5,
      speed: 0.1, up: 0.5, life: 1.2, size: 0.34, drag: 0.8, spin: 2 })],
    [0.3, 0.15, (fx, root, s, lift) => fx.p.emit(onBody(root, s, lift, 0, 0.1), { count: 1, color: 0x5a2a8a, bright: 0.8, speed: 0.15,
      up: 0.1, life: 1.6, size: 0.6, grow: 0.4, drag: 1.5 })],
  ],
  hearts: [
    [0.55, 0.3, (fx, root, s, lift) => fx.glyph(overHead(root, s, lift), { glyph: 'heart', count: 1, color: 0xff6aa8, bright: 1.7, speed: 0.15,
      up: 0.45, life: 1.4, size: 0.24, drag: 0.6, rot: 0 })],
  ],
  hush: [
    [0.8, 0.3, (fx, root, s, lift) => fx.glyph(overHead(root, s, lift), { glyph: 'hush', count: 1, color: 0xf0f0ff, bright: 1.7, speed: 0,
      up: 0.15, life: 1.0, size: 0.42, drag: 1, rot: 0 })],
  ],
};

// each frame: the harms' emitters on one body, by their clocks (s.harmT)
export function emitHarms(kinds, fx, root, s, dt, lift) {
  s.harmT = s.harmT || {};
  for (const kind of kinds) {
    const list = HARMS[kind];
    if (!list) continue;
    list.forEach(([every, jit, emit], i) => {
      const k = `${kind}${i}`;
      let left = (s.harmT[k] ?? Math.random() * every) - dt;
      for (let n = 0; left <= 0 && n < 3; n++) { emit(fx, root, s, lift); left += every + Math.random() * jit; }
      s.harmT[k] = Math.max(left, -0.5);
    });
  }
}
