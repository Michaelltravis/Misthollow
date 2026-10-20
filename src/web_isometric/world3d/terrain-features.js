// What a room's words say stands in it (room_features.py reads them, shared/roomgen.js places
// them on open floor off the lanes): standing stones, altars, stakes, skull poles, banners,
// cairns, cages, graves, braziers, wells, statues... Each from the art kits where they have it,
// else built here in the same chunky low-poly style. buildRoom calls drawFeatures(ctx()).
import * as THREE from 'three';
import { trs } from './assets.js';

// ---- shapes built in code (cached: one geometry each, instanced by the batcher) ----
const cache = new Map();
function made(name, build) {
  let m = cache.get(name);
  if (!m) {
    const parts = build();
    const box = new THREE.Box3();
    for (const p of parts) { p.geometry.computeBoundingBox(); box.union(p.geometry.boundingBox); }
    m = { name: `feat_${name}`, box, parts };
    cache.set(name, m);
  }
  return m;
}
const mats = new Map();
function mat(color, opts = {}) {
  const key = `${color}|${JSON.stringify(opts)}`;
  let m = mats.get(key);
  if (!m) { m = new THREE.MeshStandardMaterial({ color, roughness: 0.92, metalness: 0, flatShading: true, ...opts }); mats.set(key, m); }
  return m;
}
const STONE = 0x8a877c, STONE_DARK = 0x5e5b54, IRON = 0x34322f, WOOD = 0x6b4a2e;
export const COLOUR = { red: 0xb02a22, black: 0x1e1c1c, white: 0xe8e4d8, gold: 0xd4a640, silver: 0xc8ccd4, green: 0x4a8a3a,
  blue: 0x3a5ab0, teal: 0x2f8a86, yellow: 0xd8b04a, purple: 0x6a3a8a, ice: 0x9ad4f0 };

// a deterministic jitter for a shape's vertices, so a stone is rough but the same every time
function rough(geo, seed, amt) {
  const p = geo.attributes.position;
  let s = seed * 9301 + 49297;
  const rnd = () => { s = (s * 9301 + 49297) % 233280; return s / 233280 - 0.5; };
  const seen = new Map();
  for (let i = 0; i < p.count; i++) {
    const k = `${p.getX(i).toFixed(3)},${p.getY(i).toFixed(3)},${p.getZ(i).toFixed(3)}`;
    let d = seen.get(k);
    if (!d) { d = [rnd() * amt, rnd() * amt * 0.5, rnd() * amt]; seen.set(k, d); }
    p.setXYZ(i, p.getX(i) + d[0], p.getY(i) + d[1], p.getZ(i) + d[2]);
  }
  geo.computeVertexNormals();
  return geo;
}
// a standing stone: a tall slab, narrower at the top, rough, its foot at y = 0
export function menhir(v) {
  return made(`menhir${v}`, () => {
    const g = new THREE.BoxGeometry(0.95, 2.8 + v * 0.35, 0.6, 2, 4, 2);
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const t = (p.getY(i) + (2.8 + v * 0.35) / 2) / (2.8 + v * 0.35);      // 0 at the foot, 1 at the top
      const k = 1 - 0.32 * t;
      p.setX(i, p.getX(i) * k); p.setZ(i, p.getZ(i) * k);
    }
    g.translate(0, (2.8 + v * 0.35) / 2, 0);
    return [{ geometry: rough(g, 11 + v, 0.12), material: mat(v === 1 ? 0x7e7b72 : STONE) }];
  });
}
// a band round a standing stone (a collar of red-dyed wool, a rope of vines)
function band(color) {
  return made(`band_${color}`, () => {
    // wide enough to sit outside the stone all round (it is 0.81 x 0.51 at this height)
    const g = new THREE.TorusGeometry(0.4, 0.1, 6, 16);
    g.rotateX(Math.PI / 2); g.scale(1.22, 1.3, 0.92); g.translate(0, 1.3, 0);
    return [{ geometry: g, material: mat(COLOUR[color] || 0xb02a22) }];
  });
}
function altar(main, color) {
  return made(`altar${main ? 'M' : ''}_${color || ''}`, () => {
    const s = main ? 1.25 : 1;
    const base = rough(new THREE.BoxGeometry(1.7 * s, 0.85 * s, 0.9 * s, 2, 1, 2), 3, 0.08).translate(0, 0.425 * s, 0);
    const top = new THREE.BoxGeometry(1.95 * s, 0.16, 1.1 * s).translate(0, 0.85 * s + 0.08, 0);
    const parts = [{ geometry: base, material: mat(STONE_DARK) }, { geometry: top, material: mat(color && COLOUR[color] ? COLOUR[color] : 0x4a4640, color === 'gold' || color === 'silver' ? { metalness: 0.6, roughness: 0.4 } : {}) }];
    // a dark stain of old offerings on the top
    parts.push({ geometry: new THREE.CircleGeometry(0.32 * s, 10).rotateX(-Math.PI / 2).translate(0.2, 0.85 * s + 0.165, 0), material: mat(0x2a0e0c) });
    return parts;
  });
}
function statue() {
  return made('statue', () => [
    { geometry: new THREE.BoxGeometry(0.9, 0.55, 0.9).translate(0, 0.275, 0), material: mat(STONE_DARK) },
    { geometry: rough(new THREE.CylinderGeometry(0.24, 0.36, 1.35, 7), 5, 0.05).translate(0, 1.22, 0), material: mat(STONE) },
    { geometry: new THREE.IcosahedronGeometry(0.21, 0).translate(0, 2.08, 0), material: mat(STONE) },
    { geometry: new THREE.BoxGeometry(0.95, 0.16, 0.22).translate(0, 1.62, 0), material: mat(STONE) },
  ]);
}
function obelisk() {
  return made('obelisk', () => {
    const g = new THREE.CylinderGeometry(0.22, 0.38, 3.4, 4, 1).rotateY(Math.PI / 4).translate(0, 1.7, 0);
    const tip = new THREE.ConeGeometry(0.22, 0.45, 4).rotateY(Math.PI / 4).translate(0, 3.62, 0);
    return [{ geometry: g, material: mat(0x3a3836) }, { geometry: tip, material: mat(0xc8a040, { metalness: 0.5, roughness: 0.45 }) }];
  });
}
function cairn(v) {
  return made(`cairn${v}`, () => {
    const parts = [];
    let y = 0;
    for (let i = 0; i < 4 + v; i++) {
      const r = 0.28 - i * 0.045;
      const g = rough(new THREE.DodecahedronGeometry(r, 0), 20 + i + v * 7, 0.05);
      g.scale(1.1, 0.7, 1).translate((i % 2 ? 0.05 : -0.04), y + r * 0.6, (i % 3 ? 0.03 : -0.03));
      parts.push(g);
      y += r * 1.1;
    }
    const merged = parts.map(g => ({ geometry: g, material: mat(STONE) }));
    return merged;
  });
}
// chains: a gallows-frame of two iron-bound posts and a beam, three chains hanging from it to
// manacles, one trailing across the floor (big enough to read from the camera)
function chains() {
  return made('chains', () => {
    const iron = mat(0x5e5a54, { metalness: 0.6, roughness: 0.45 });
    const wood = mat(0x4a3424);
    const parts = [
      { geometry: new THREE.BoxGeometry(0.18, 2.3, 0.18).translate(-0.62, 1.15, 0), material: wood },
      { geometry: new THREE.BoxGeometry(0.18, 2.3, 0.18).translate(0.62, 1.15, 0), material: wood },
      { geometry: new THREE.BoxGeometry(1.5, 0.18, 0.2).translate(0, 2.25, 0), material: wood },
    ];
    for (const [x, len] of [[-0.34, 1.35], [0, 1.9], [0.34, 1.1]]) {
      const n = Math.round(len / 0.15);
      for (let i = 0; i < n; i++) {
        const g = new THREE.TorusGeometry(0.075, 0.024, 4, 8);
        if (i % 2) g.rotateY(Math.PI / 2);
        g.translate(x, 2.12 - i * 0.15, 0);
        parts.push({ geometry: g, material: iron });
      }
      // the manacle at the end
      parts.push({ geometry: new THREE.TorusGeometry(0.12, 0.035, 5, 12).translate(x, 2.12 - n * 0.15 - 0.06, 0), material: iron });
    }
    // the middle one runs on along the floor
    for (let i = 0; i < 6; i++) {
      const g = new THREE.TorusGeometry(0.075, 0.024, 4, 8).rotateX(Math.PI / 2);
      if (i % 2) g.rotateZ(Math.PI / 2);
      g.translate(0.05 + i * 0.03, 0.03, 0.15 + i * 0.14);
      parts.push({ geometry: g, material: iron });
    }
    return parts;
  });
}
function cage() {
  return made('cage', () => {
    const parts = [];
    for (let i = 0; i < 8; i++) {
      const a = i / 8 * Math.PI * 2;
      parts.push({ geometry: new THREE.CylinderGeometry(0.025, 0.025, 1.4, 4).translate(Math.cos(a) * 0.42, 1.0, Math.sin(a) * 0.42), material: mat(IRON, { metalness: 0.5, roughness: 0.6 }) });
    }
    for (const y of [0.3, 1.7]) parts.push({ geometry: new THREE.TorusGeometry(0.42, 0.04, 5, 16).rotateX(Math.PI / 2).translate(0, y, 0), material: mat(IRON, { metalness: 0.5, roughness: 0.6 }) });
    // the gibbet: a post and an arm
    parts.push({ geometry: new THREE.BoxGeometry(0.16, 2.6, 0.16).translate(-0.62, 1.3, 0), material: mat(WOOD) });
    parts.push({ geometry: new THREE.BoxGeometry(0.75, 0.13, 0.13).translate(-0.3, 2.5, 0), material: mat(WOOD) });
    return parts;
  });
}
function drum() {
  return made('drum', () => [
    { geometry: new THREE.CylinderGeometry(0.42, 0.38, 0.75, 10).translate(0, 0.375, 0), material: mat(0x7a4a2a) },
    { geometry: new THREE.CylinderGeometry(0.43, 0.43, 0.04, 10).translate(0, 0.77, 0), material: mat(0xd8c49a) },
  ]);
}
function brazier() {
  return made('brazier', () => [
    { geometry: new THREE.CylinderGeometry(0.42, 0.26, 0.3, 8).translate(0, 0.78, 0), material: mat(IRON, { metalness: 0.5, roughness: 0.6 }) },
    ...[0, 1, 2].map(i => { const a = i / 3 * Math.PI * 2; return { geometry: new THREE.CylinderGeometry(0.03, 0.03, 0.7, 4).translate(Math.cos(a) * 0.24, 0.35, Math.sin(a) * 0.24), material: mat(IRON) }; }),
    { geometry: new THREE.DodecahedronGeometry(0.22, 0).scale(1.4, 0.5, 1.4).translate(0, 0.94, 0), material: mat(0x2a1e18) },
    // the fire itself: two crossed tongues of flame, bright enough to bloom
    { geometry: new THREE.ConeGeometry(0.3, 0.75, 6).translate(0, 1.32, 0), material: mat(0xff7a1a, { emissive: 0xff6a10, emissiveIntensity: 2.2, transparent: true, opacity: 0.9 }) },
    { geometry: new THREE.ConeGeometry(0.17, 0.5, 5).translate(0.05, 1.5, 0.03), material: mat(0xffd060, { emissive: 0xffc040, emissiveIntensity: 2.6 }) },
  ]);
}
function fountain() {
  return made('fountain', () => [
    { geometry: new THREE.CylinderGeometry(1.0, 1.08, 0.5, 14, 1, true).translate(0, 0.25, 0), material: mat(STONE, { side: THREE.DoubleSide }) },
    { geometry: new THREE.TorusGeometry(1.0, 0.09, 5, 20).rotateX(Math.PI / 2).translate(0, 0.5, 0), material: mat(STONE) },
    { geometry: new THREE.CircleGeometry(0.98, 18).rotateX(-Math.PI / 2).translate(0, 0.38, 0), material: mat(0x3a7a9a, { roughness: 0.15, metalness: 0.2 }) },
    { geometry: new THREE.CylinderGeometry(0.14, 0.2, 1.2, 8).translate(0, 0.6, 0), material: mat(STONE) },
    { geometry: new THREE.CylinderGeometry(0.42, 0.15, 0.18, 10).translate(0, 1.2, 0), material: mat(STONE) },
  ]);
}
// a throne on a stepped dais: a high back with a crest, arms, a red cushion, trim in the
// throne's own metal (gold unless the words say otherwise)
export function throne(color) {
  return made(`throne_${color || ''}`, () => {
    const body = color === 'black' ? 0x2a2626 : color === 'white' ? 0xd8d4c8 : color === 'gold' ? 0xc89a3a : 0x5a4a3c;
    const m = mat(body, color === 'gold' ? { metalness: 0.6, roughness: 0.4 } : {});
    const trim = mat(color === 'silver' || color === 'white' ? 0xc8ccd4 : 0xd4a640, { metalness: 0.7, roughness: 0.35 });
    const step = mat(STONE_DARK);
    return [
      { geometry: new THREE.BoxGeometry(2.0, 0.18, 1.8).translate(0, 0.09, 0.1), material: step },
      { geometry: new THREE.BoxGeometry(1.6, 0.18, 1.3).translate(0, 0.27, -0.05), material: step },
      { geometry: new THREE.BoxGeometry(1.2, 0.5, 0.95).translate(0, 0.61, -0.05), material: m },
      { geometry: new THREE.BoxGeometry(1.2, 2.3, 0.22).translate(0, 1.5, -0.5), material: m },
      { geometry: new THREE.ConeGeometry(0.42, 0.55, 4).rotateY(Math.PI / 4).scale(1.4, 1, 0.4).translate(0, 2.92, -0.5), material: trim },
      { geometry: new THREE.BoxGeometry(1.32, 0.1, 0.3).translate(0, 2.62, -0.5), material: trim },
      { geometry: new THREE.BoxGeometry(0.18, 0.45, 0.9).translate(-0.6, 1.08, -0.02), material: m },
      { geometry: new THREE.BoxGeometry(0.18, 0.45, 0.9).translate(0.6, 1.08, -0.02), material: m },
      { geometry: new THREE.BoxGeometry(0.22, 0.08, 0.95).translate(-0.6, 1.33, -0.02), material: trim },
      { geometry: new THREE.BoxGeometry(0.22, 0.08, 0.95).translate(0.6, 1.33, -0.02), material: trim },
      { geometry: new THREE.BoxGeometry(0.95, 0.12, 0.8).translate(0, 0.92, 0), material: mat(0x8a1e1e) },
      { geometry: new THREE.BoxGeometry(0.9, 1.2, 0.08).translate(0, 1.55, -0.37), material: mat(0x8a1e1e) },
    ];
  });
}
// the drow's pillar: black stone ringed with faerie fire (the dungeon kit's has a knight's shields)
function drowPillar() {
  return made('drow_pillar', () => {
    const fire = mat(0x9a5aff, { emissive: 0xb070ff, emissiveIntensity: 1.6 });
    return [
      { geometry: new THREE.CylinderGeometry(0.42, 0.52, 3.4, 8).translate(0, 1.7, 0), material: mat(0x1c1822, { roughness: 0.35, metalness: 0.4 }) },
      { geometry: new THREE.TorusGeometry(0.58, 0.05, 3, 12).rotateX(Math.PI / 2).translate(0, 0.4, 0), material: fire },
      { geometry: new THREE.TorusGeometry(0.48, 0.05, 3, 12).rotateX(Math.PI / 2).translate(0, 2.4, 0), material: fire },
    ];
  });
}
// a cluster of glowing crystals, waist to head high, leaning out from a common root
function crystal(color) {
  return made(`crystal_${color || ''}`, () => {
    const c = COLOUR[color] || 0x8a6ae0;
    const m = mat(c, { emissive: c, emissiveIntensity: 1.3, roughness: 0.2 });
    const pale = mat(0xe8e0ff, { emissive: c, emissiveIntensity: 0.8, roughness: 0.15 });
    const shards = [[0, 1.5, 0, 0], [0.32, 1.0, 0.45, 0.1], [-0.3, 1.1, -0.4, 0.15], [0.12, 0.7, 0.2, -0.35], [-0.18, 0.6, -0.15, 0.38]];
    return shards.map(([x, h, lean, z], i) => ({
      geometry: new THREE.OctahedronGeometry(0.5, 0).scale(0.32 + h * 0.05, h, 0.32 + h * 0.05).translate(0, h * 0.5, 0).rotateZ(-lean).rotateX(z).translate(x, 0, z * 0.6),
      material: i === 3 ? pale : m,
    }));
  });
}
// ---- scenery the words name that a room's look does not draw by itself ----
// a gate: two squared stone piers, a lintel, two iron-banded oak leaves standing half open
function gate() {
  return made('gate', () => {
    const stone = mat(STONE), oak = mat(0x5a3a22), iron = mat(IRON, { metalness: 0.5, roughness: 0.55 });
    const parts = [
      { geometry: rough(new THREE.BoxGeometry(0.6, 3.4, 0.6, 1, 3, 1), 41, 0.05).translate(-1.3, 1.7, 0), material: stone },
      { geometry: rough(new THREE.BoxGeometry(0.6, 3.4, 0.6, 1, 3, 1), 42, 0.05).translate(1.3, 1.7, 0), material: stone },
      { geometry: new THREE.BoxGeometry(3.3, 0.55, 0.7).translate(0, 3.6, 0), material: stone },
      { geometry: new THREE.BoxGeometry(0.8, 0.8, 0.75).rotateZ(Math.PI / 4).scale(1, 0.5, 1).translate(0, 4.0, 0), material: stone },
    ];
    // each leaf hinged on its pier's inner face, swung a little open
    for (const sx of [-1, 1]) {
      parts.push({ geometry: new THREE.BoxGeometry(1.0, 2.9, 0.12).translate(-sx * 0.5, 1.45, 0).rotateY(sx * 0.6).translate(sx * 1.0, 0, 0), material: oak });
      for (const y of [0.6, 2.3]) parts.push({ geometry: new THREE.BoxGeometry(1.02, 0.1, 0.16).translate(-sx * 0.5, y, 0).rotateY(sx * 0.6).translate(sx * 1.0, 0, 0), material: iron });
    }
    return parts;
  });
}
// a stand of reeds: thin stems, a few with brown heads
function reeds(v) {
  return made(`reeds${v}`, () => {
    const parts = [], stem = mat(0x6a8a3a), head = mat(0x5a3a1e);
    let s = 7 + v * 13;
    const r = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
    for (let i = 0; i < 16; i++) {
      const h = 0.9 + r() * 0.9, x = (r() - 0.5) * 1.1, z = (r() - 0.5) * 1.1, lean = (r() - 0.5) * 0.3;
      parts.push({ geometry: new THREE.CylinderGeometry(0.012, 0.025, h, 3).translate(0, h / 2, 0).rotateZ(lean).translate(x, 0, z), material: stem });
      if (i % 3 === 0) parts.push({ geometry: new THREE.CylinderGeometry(0.04, 0.04, 0.22, 5).translate(0, h - 0.1, 0).rotateZ(lean).translate(x, 0, z), material: head });
    }
    return parts;
  });
}
// roots or vines: gnarled runs creeping along the floor and up the wall behind
function roots(v) {
  return made(`roots${v}`, () => {
    const m = mat(0x4e3a26), parts = [];
    for (let i = 0; i < 6; i++) {
      const a = (i - 2.5) * 0.28 + v * 0.1, x0 = Math.sin(a) * 0.4;
      const pts = [new THREE.Vector3(x0 * 3, 0.05, 0.9 - i * 0.05), new THREE.Vector3(x0 * 2, 0.15, 0.2), new THREE.Vector3(x0, 1.0, -0.35), new THREE.Vector3(x0 * 1.5, 2.2, -0.45), new THREE.Vector3(x0 * 0.5, 3.0, -0.5)];
      parts.push({ geometry: new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 10, 0.07 - i * 0.006, 5), material: m });
    }
    return parts;
  });
}
// a rowboat drawn up on the floor, with its oars
function boat() {
  return made('boat', () => {
    const g = new THREE.BoxGeometry(2.6, 0.5, 1.0, 6, 1, 2);
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const t = Math.abs(p.getX(i)) / 1.3;                       // 0 amidships, 1 at bow and stern
      const k = 1 - t * t * 0.85;
      p.setZ(i, p.getZ(i) * k * (p.getY(i) < 0 ? 0.6 : 1));
      p.setY(i, p.getY(i) + t * t * 0.18);
    }
    g.computeVertexNormals(); g.translate(0, 0.3, 0);
    const wood = mat(0x7a5434), dark = mat(0x3e2a1a);
    return [
      { geometry: g, material: wood },
      { geometry: new THREE.BoxGeometry(2.2, 0.06, 0.72).translate(0, 0.5, 0), material: dark },
      { geometry: new THREE.BoxGeometry(0.2, 0.06, 0.8).translate(-0.4, 0.58, 0), material: wood },
      { geometry: new THREE.BoxGeometry(0.2, 0.06, 0.8).translate(0.5, 0.58, 0), material: wood },
      { geometry: new THREE.CylinderGeometry(0.03, 0.03, 2.0, 4).rotateZ(Math.PI / 2).rotateY(0.15).translate(0.1, 0.62, 0.25), material: dark },
    ];
  });
}
// low mist: soft pale banks lying over the floor at a few heights, each fading out at its rim
let mistTex = null;
function mistAlpha() {
  if (!mistTex) {
    const n = 64, data = new Uint8Array(n * n * 4);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      const d = Math.hypot(x - n / 2 + 0.5, y - n / 2 + 0.5) / (n / 2);
      const a = Math.max(0, 1 - d) ** 1.2;
      data.set([255, 255, 255, Math.round(a * 255)], (y * n + x) * 4);
    }
    mistTex = new THREE.DataTexture(data, n, n);
    mistTex.needsUpdate = true;
  }
  return mistTex;
}
function mist() {
  return made('mist', () => {
    const m = mat(0xc4ccd4, { transparent: true, opacity: 0.4, depthWrite: false, map: mistAlpha(), emissive: 0x6a747e, emissiveIntensity: 0.25 });
    return [[0, 0.25, 0, 3.0], [2.2, 0.4, 1.3, 2.4], [-2.4, 0.35, -1.0, 2.6], [0.6, 0.6, -2.0, 2.2], [-1.2, 0.8, 1.8, 2.0], [2.6, 0.7, -1.6, 1.8], [-2.8, 0.55, 1.9, 1.9]].map(([x, y, z, r]) =>
      ({ geometry: new THREE.PlaneGeometry(r * 2, r * 2 * 0.7).rotateX(-Math.PI / 2).translate(x, y, z), material: m }));
  });
}
// a patch of open fire: a ring of blackened stones round tongues of flame
function flames(v) {
  return made(`flames${v}`, () => {
    const parts = [{ geometry: new THREE.CircleGeometry(0.75, 10).rotateX(-Math.PI / 2).translate(0, 0.03, 0), material: mat(0x1e1612) }];
    for (let i = 0; i < 7; i++) {
      const a = i / 7 * Math.PI * 2;
      parts.push({ geometry: rough(new THREE.DodecahedronGeometry(0.16, 0), 60 + i, 0.04).translate(Math.cos(a) * 0.72, 0.1, Math.sin(a) * 0.72), material: mat(0x3a3430) });
    }
    const hot = mat(0xff6a14, { emissive: 0xff5a10, emissiveIntensity: 2.2, transparent: true, opacity: 0.88 });
    const core = mat(0xffd060, { emissive: 0xffc040, emissiveIntensity: 2.6 });
    for (const [x, z, h, m] of [[0, 0, 1.1, hot], [0.25, 0.15, 0.75, hot], [-0.22, -0.1, 0.8, hot], [0.05, -0.25, 0.6, hot], [0, 0.02, 0.6, core]]) {
      parts.push({ geometry: new THREE.ConeGeometry(m === core ? 0.14 : 0.24, h, 5).translate(x, h / 2 + 0.05, z), material: m });
    }
    return parts;
  });
}
// a fireplace against a wall: a stone surround, a dark firebox with logs burning in it, the
// chimney breast going up (a house's or a hall's hearth; a brazier is for open floors)
function fireplace() {
  return made('fireplace', () => {
    const stone = mat(0x7a746a), dark = mat(0x1a1410);
    const hot = mat(0xff6a14, { emissive: 0xff5a10, emissiveIntensity: 2.2, transparent: true, opacity: 0.9 });
    return [
      { geometry: rough(new THREE.BoxGeometry(2.0, 1.5, 0.7, 2, 2, 1), 91, 0.04).translate(0, 0.75, -0.15), material: stone },
      { geometry: new THREE.BoxGeometry(1.1, 0.9, 0.5).translate(0, 0.5, 0.0), material: dark },
      { geometry: new THREE.BoxGeometry(2.3, 0.16, 0.85).translate(0, 1.55, -0.1), material: mat(0x5a4a3a) },
      { geometry: rough(new THREE.BoxGeometry(1.4, 2.4, 0.55, 1, 2, 1), 92, 0.03).translate(0, 2.8, -0.22), material: stone },
      { geometry: new THREE.CylinderGeometry(0.08, 0.08, 0.8, 5).rotateZ(Math.PI / 2).translate(0, 0.14, 0.12), material: mat(0x4a3020) },
      { geometry: new THREE.CylinderGeometry(0.08, 0.08, 0.8, 5).rotateZ(Math.PI / 2).rotateY(0.4).translate(0, 0.22, 0.1), material: mat(0x4a3020) },
      { geometry: new THREE.ConeGeometry(0.22, 0.6, 5).translate(-0.12, 0.5, 0.12), material: hot },
      { geometry: new THREE.ConeGeometry(0.18, 0.45, 5).translate(0.16, 0.42, 0.14), material: hot },
    ];
  });
}
// a tall mirror in a heavy frame, its glass catching the light
function mirror() {
  return made('mirror', () => [
    { geometry: new THREE.BoxGeometry(1.1, 2.3, 0.14).translate(0, 1.25, 0), material: mat(0xb08a3a, { metalness: 0.6, roughness: 0.4 }) },
    { geometry: new THREE.BoxGeometry(0.9, 2.05, 0.04).translate(0, 1.27, 0.07), material: mat(0xc8d8e8, { metalness: 0.9, roughness: 0.05, emissive: 0x5a6a7c, emissiveIntensity: 0.6 }) },
    { geometry: new THREE.BoxGeometry(1.3, 0.12, 0.5).translate(0, 0.06, 0), material: mat(0x6a5226) },
  ]);
}
// a bronze bell hung in a timber frame
function bell() {
  return made('bell', () => {
    const wood = mat(0x5a3e26), bronze = mat(0xb07a34, { metalness: 0.7, roughness: 0.35 });
    const prof = [[0.05, 0], [0.62, 0], [0.6, 0.12], [0.45, 0.4], [0.38, 0.85], [0.3, 1.05], [0.05, 1.1]].map(([x, y]) => new THREE.Vector2(x, y));
    return [
      { geometry: new THREE.BoxGeometry(0.22, 3.2, 0.22).translate(-1.0, 1.6, 0), material: wood },
      { geometry: new THREE.BoxGeometry(0.22, 3.2, 0.22).translate(1.0, 1.6, 0), material: wood },
      { geometry: new THREE.BoxGeometry(2.4, 0.26, 0.3).translate(0, 3.15, 0), material: wood },
      { geometry: new THREE.LatheGeometry(prof, 12).translate(0, 1.75, 0), material: bronze },
      { geometry: new THREE.SphereGeometry(0.12, 6, 5).translate(0, 1.72, 0), material: mat(IRON) },
    ];
  });
}
// a waterfall: a rock face with a white-blue sheet falling down it into a foaming pool
function waterfall() {
  return made('waterfall', () => [
    { geometry: rough(new THREE.BoxGeometry(3.0, 4.2, 1.0, 3, 4, 1), 77, 0.25).translate(0, 2.1, -0.6), material: mat(0x6e6a62) },
    { geometry: new THREE.PlaneGeometry(1.3, 4.0, 1, 4).translate(0, 2.05, -0.06), material: mat(0xbfe4f4, { transparent: true, opacity: 0.85, emissive: 0x6aa8c8, emissiveIntensity: 0.5, side: THREE.DoubleSide }) },
    { geometry: new THREE.CircleGeometry(1.25, 14).scale(1, 1, 0.6).rotateX(-Math.PI / 2).translate(0, 0.04, 0.45), material: mat(0x3a7a9a, { roughness: 0.15, metalness: 0.2 }) },
    { geometry: new THREE.TorusGeometry(0.75, 0.16, 4, 12).rotateX(Math.PI / 2).scale(1, 1, 0.5).translate(0, 0.08, 0.2), material: mat(0xf0f8fc, { emissive: 0xc8e0ec, emissiveIntensity: 0.4 }) },
  ]);
}
// flat on the ground: a splash of blood, a smear of ash, the holes of old stakes
function decal(kind, v) {
  return made(`decal_${kind}${v}`, () => {
    const col = kind === 'blood' ? 0x6e0e0a : kind === 'ash' ? 0x24221f : 0x1a1612;
    const m = mat(col, { transparent: true, opacity: kind === 'ash' ? 0.75 : 0.9, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 });
    const parts = [];
    const n = kind === 'stake_holes' ? 5 : 3;
    for (let i = 0; i < n; i++) {
      const r = kind === 'stake_holes' ? 0.09 : (kind === 'blood' ? 0.4 : 0.25) + ((i * 37 + v * 13) % 10) / 22;
      const x = kind === 'stake_holes' ? (i - 2) * 0.55 : ((i * 53 + v * 7) % 10) / 10 - 0.5;
      const z = kind === 'stake_holes' ? ((i % 2) * 0.18) : ((i * 29 + v * 11) % 10) / 10 - 0.5;
      parts.push({ geometry: new THREE.CircleGeometry(r, 9).scale(1, 1, 0.75).rotateX(-Math.PI / 2).translate(x, 0.025 + i * 0.002, z), material: m });
    }
    return parts;
  });
}

// ---- placing them ----
// kit models scaled to a height in metres
function sized(model, h) {
  if (!model || !model.box) return 1;
  const mh = model.box.max.y - model.box.min.y;
  return mh > 0.01 ? h / mh : 1;
}

export function drawFeatures(c) {
  const { layout, ox, oz, kits, b, rng, torches, occ } = c;
  const feats = layout.features || [];
  if (!feats.length) return;
  const D = kits.dungeon, N = kits.nature, T = kits.town, F = kits.furniture, G = kits.graveyard;
  const indoor = ['inside', 'dungeon', 'crypt', 'castle', 'sewer', 'cave', 'mine', 'drow', 'foundry'].includes(layout.theme);
  const has = k => feats.some(f => f.k === k);
  // a store room, a treasury, a cellar: its stores piled high
  const store = /\b(?:store ?rooms?|storage|pantry|larder|warehouse|cellar|treasury|hoard|stores)\b/i.test(layout.name || '');
  // a thing set against a wall faces out from the nearest one (its back to the wall)
  const wallYaw = f => {
    const x = f.x + f.w / 2, y = f.y + f.h / 2;
    const d = [[x, 0], [layout.W - x, Math.PI], [y, Math.PI / 2], [layout.H - y, -Math.PI / 2]];
    let best = d[0];
    for (const e of d) if (e[0] < best[0]) best = e;
    // (yaw 0 faces +z: the wall at x = 0 means facing +x, and so on)
    return { 0: Math.PI / 2, [Math.PI]: -Math.PI / 2, [Math.PI / 2]: 0, [-Math.PI / 2]: Math.PI }[best[1]];
  };
  // open floor at a point (the walls, water and lanes stay clear of a heap's spill)
  const openAt = (x, y) => {
    const gx = Math.floor(x), gy = Math.floor(y);
    if (gx < 1 || gy < 1 || gx >= layout.W - 1 || gy >= layout.H - 1) return false;
    return layout.grid[gy * layout.W + gx] === 0;
  };
  const put = (model, x, z, yaw, s, opts) => { if (model) b.add(model, trs(x, 0, z, yaw, s), opts); };
  const putY = (model, x, y, z, yaw, s, opts) => { if (model) b.add(model, trs(x, y, z, yaw, s), opts); };
  for (const f of feats) {
    const cx = ox + f.x + f.w / 2, cz = oz + f.y + f.h / 2;
    const yaw = f.yaw || 0, s = f.s || 1, main = f.main;
    const v = (f.x * 7 + f.y * 3 + (f.i || 0)) % 3;
    const blocker = m => (occ ? occ(m) : m);
    // more of the same round it, on open floor only (a store room's crates, a crystal cave's
    // clusters, a charnel heap): r is how far they spread, sc their size
    const heap = (get, n, r, sc) => {
      for (let i = 0; i < n; i++) {
        const a = rng() * Math.PI * 2, d = 0.5 + rng() * (r - 0.5);
        const x = f.x + f.w / 2 + Math.cos(a) * d, y = f.y + f.h / 2 + Math.sin(a) * d;
        if (!openAt(x, y)) continue;
        put(get(i), ox + x, oz + y, rng() * 6.28, sc * (0.8 + rng() * 0.4), { shadow: false });
      }
    };
    switch (f.k) {
      case 'standing_stone': {
        const big = main ? 1.35 : 1;
        put(blocker(menhir(v)), cx, cz, yaw + (rng() - 0.5) * 0.3, s * big);
        if (f.c) put(band(f.c), cx, cz, yaw, s * big, { shadow: false });
        break;
      }
      case 'altar': {
        put(blocker(altar(main, f.c)), cx, cz, Math.round(yaw / (Math.PI / 2)) * Math.PI / 2, 1);
        const top = (main ? 1.25 : 1) * 0.85 + 0.17;
        if (D) for (const dx of [-0.6, 0.6]) putY(D.get('candle_triple'), cx + dx * (main ? 1.2 : 1), top, cz, 0, 0.7, { shadow: false });
        break;
      }
      case 'statue': put(blocker(statue()), cx, cz, yaw, s * (main ? 1.6 : 1.3)); break;
      case 'obelisk': put(blocker(obelisk()), cx, cz, yaw, s); break;
      case 'pillar': if (layout.theme === 'drow') put(blocker(drowPillar()), cx, cz, 0, 1); else if (D) put(blocker(D.get(v === 0 ? 'pillar_decorated' : 'column')), cx, cz, 0, 1); break;
      // (the town kit is built small: its props stand at x4-5, its wells at x2.6, as terrain-town.js has them)
      case 'well': if (T) put(blocker(T.get(['building_well_blue', 'building_well_green', 'building_well_red'][v])), cx, cz, yaw, 2.6); break;
      case 'fountain': put(blocker(fountain()), cx, cz, 0, main ? 1.25 : 1); break;
      case 'brazier': {
        // (indoors, a hearth or fireplace the words name is one, set against the wall)
        // (indoors, a hearth or fireplace the words name is built into the north wall, a chair drawn
        // up to it where the brazier would have stood)
        if (['inside', 'castle'].includes(layout.theme) && /\b(?:hearths?|fireplaces?)\b/i.test(`${layout.name} ${layout.description}`)) {
          const fz = oz + 1.75;
          put(fireplace(), cx, fz, 0, 1);
          if (torches) torches.push(new THREE.Vector3(cx, 0.7, fz + 0.3));
          if (F) put(blocker(F.get('armchair_pillows')), cx, cz, Math.PI, 1);
          break;
        }
        put(blocker(brazier()), cx, cz, 0, main ? 1.5 : 1.15);
        if (torches) torches.push(new THREE.Vector3(cx, main ? 1.9 : 1.4, cz + 0.12));
        break;
      }
      case 'tent': if (T) put(blocker(T.get('tent')), cx, cz, yaw, sized(T.get('tent'), 2.2)); break;
      case 'cage': put(blocker(cage()), cx, cz, yaw, main ? 1.35 : 1.15); break;
      // (a frame, a gate, a bell's frame face the camera: turned side-on they read as a post)
      case 'chains': put(blocker(chains()), cx, cz, 0, main ? 1.2 : 1); break;
      case 'stake': if (G) put(G.get('post'), cx, cz, yaw, sized(G.get('post'), 1.4) * 0.9); break;
      case 'pole': if (G) put(G.get(has('skull') ? 'post_skull' : 'post'), cx, cz, yaw, sized(G.get('post'), 2.4)); break;
      case 'banner': {
        if (!D) break;
        const key = f.c === 'blue' ? 'banner_patternB_blue' : f.c === 'white' ? 'banner_shield_white' : v === 0 ? 'banner_patternA_red' : 'banner_thin_red';
        if (indoor) putY(D.get(key), cx, 0, cz, yaw, 1);
        else {
          // outdoors: a banner on its own pole
          if (G) put(G.get('post'), cx, cz, yaw, sized(G.get('post'), 2.6));
          putY(D.get(key), cx, 0.4, cz + 0.12, yaw, 0.9);
        }
        break;
      }
      case 'grave': if (G) put(blocker(G.get(['gravestone', 'grave_A', 'gravemarker_A'][v])), cx, cz, Math.round(yaw / Math.PI) * Math.PI, 1); break;
      case 'coffin': if (G) put(blocker(G.get(v === 2 ? 'coffin_decorated' : 'coffin')), cx, cz, yaw, 1); break;
      case 'candle': if (D || G) {
        put(v === 1 && G ? G.get('candle_melted') : D.get('candle_triple'), cx, cz, yaw, 1.2, { shadow: false });
        if (D) heap(() => D.get('candle_triple'), main ? 4 : 1, 1.2, 0.9);
        if (torches && main) torches.push(new THREE.Vector3(cx, 0.9, cz));
      } break;
      case 'torch': {
        if (!D) break;
        putY(D.get('torch_lit'), cx, 0.4, cz, 0, 1.6, { shadow: false });
        if (torches) torches.push(new THREE.Vector3(cx, 1.6, cz));
        break;
      }
      case 'lantern': {
        if (!G) break;
        const lm = G.get('lantern_standing');
        put(lm, cx, cz, yaw, sized(lm, main ? 2.2 : 1.7));
        if (torches) torches.push(new THREE.Vector3(cx, (main ? 2.2 : 1.7) * 0.85, cz + 0.12));
        break;
      }
      case 'drum': put(blocker(drum()), cx, cz, yaw, 1); break;
      // (a throne faces the way the room is seen from, its seat and arms in view, its back to the north)
      case 'throne': put(blocker(throne(layout.theme === 'drow' ? 'black' : f.c)), cx, cz, 0, main ? 1.3 : 1.1); break;
      // (a wizard's, a temple's, a haunted or elven hall's table is a plain one, not a feast)
      case 'table': if (F && layout.tone && ['arcane', 'holy', 'haunted', 'elven', 'infernal'].includes(layout.tone.interior)) put(blocker(F.get('table_medium')), cx, cz, Math.round(yaw / (Math.PI / 2)) * Math.PI / 2, 0.85);
        else if (D) put(blocker(D.get('table_long_decorated_A')), cx, cz, Math.round(yaw / (Math.PI / 2)) * Math.PI / 2, 0.9); break;
      case 'bench': if (G) put(G.get(v === 0 ? 'bench_decorated' : 'bench'), cx, cz, yaw, 1); break;
      case 'shelf': if (F) put(blocker(F.get(v === 0 ? 'shelf_B_large_decorated' : 'shelf_A_big')), cx, cz, yaw, 1); else if (D) put(blocker(D.get('shelves')), cx, cz, yaw, 1); break;
      case 'bed': if (F) put(blocker(F.get('bed_single_A')), cx, cz, yaw, 1); break;
      case 'chest': if (D) { put(D.get(f.c === 'gold' ? 'chest_gold' : 'chest'), cx, cz, yaw, 1); if (main) heap(i => D.get(i % 2 ? 'chest' : 'chest_gold'), 3, 1.5, 1); } break;
      case 'barrel': if (D) { put(D.get(v === 0 ? 'barrel_large' : 'barrel_small'), cx, cz, yaw, 1); heap(i => D.get(i % 2 ? 'barrel_large' : 'barrel_small'), main || store ? 4 : 1, 1.3, 1); } break;
      case 'crate': if (T) { put(T.get(v === 0 ? 'crate_A_big' : v === 1 ? 'sack' : 'crate_B_small'), cx, cz, yaw, 5); heap(i => T.get(['crate_A_big', 'sack', 'crate_B_small'][i % 3]), main || store ? 5 : 2, 1.5, 5); } break;
      case 'weapons': if (T) put(blocker(T.get('weaponrack')), cx, cz, wallYaw(f), 4); else if (D) put(D.get('sword_shield'), cx, cz, yaw, 1); break;
      case 'fence': if (T) put(T.get('fence_wood_straight'), cx, cz, yaw, 3.2); break;
      case 'dead_tree': if (N) put(blocker(N.get(v === 0 ? 'DeadTree_1' : 'DeadTree_2')), cx, cz, yaw, 0.6 + rng() * 0.25); break;
      case 'rubble': if (D) put(D.get(v === 0 ? 'rubble_large' : 'rubble_half'), cx, cz, yaw, 0.8, { shadow: false }); break;
      case 'cairn': put(cairn(v), cx, cz, yaw, s * (0.8 + v * 0.15)); break;
      case 'skull': if (G) { put(G.get(v === 2 ? 'skull_candle' : 'skull'), cx, cz, yaw, 0.8, { shadow: false }); heap(() => G.get('skull'), main ? 5 : 1, 1.4, 0.7); } break;
      case 'bones': if (G) {
        // a heap, not a lone bone: a ribcage, a skull, long bones round them
        put(G.get('ribcage'), cx, cz, yaw, 1.0, { shadow: false });
        put(G.get('skull'), cx + 0.45, cz + 0.2, yaw + 1, 0.75, { shadow: false });
        heap(i => G.get(i % 2 ? 'bone_A' : 'bone_B'), main ? 8 : 4, 1.5, 1.3);
      } break;
      case 'mushroom': if (N) {
        // underground or in a wood they grow big: a stand of them, one as tall as a man
        const m = N.get('Mushroom_Common'), big = indoor || ['forest', 'swamp'].includes(layout.theme);
        for (let i = 0; i < (main ? 6 : 4); i++) {
          const h = (big ? (i === 0 ? 1.9 : 0.6 + rng() * 0.9) : 0.35 + rng() * 0.3) * (main ? 1.2 : 1);
          put(m, cx + (i ? (rng() - 0.5) * 1.6 : 0), cz + (i ? (rng() - 0.5) * 1.6 : 0), rng() * 6.28, sized(m, h), { shadow: i === 0 });
        }
      } break;
      case 'flowers': if (N) for (let i = 0; i < 2; i++) put(N.get(i ? 'Flower_3_Group' : 'Flower_4_Group'), cx + (rng() - 0.5) * 0.8, cz + (rng() - 0.5) * 0.8, rng() * 6.28, 0.7, { shadow: false }); break;
      case 'crystal':
        put(crystal(f.c), cx, cz, yaw, s * (main ? 1.4 : 1), { shadow: false });
        if (main) heap(() => crystal(f.c), 3, 1.8, 0.45);
        break;
      case 'rug': if (F) put(F.get(v === 0 ? 'rug_rectangle_A' : 'rug_oval_A'), cx, cz, Math.round(yaw / (Math.PI / 2)) * Math.PI / 2, 1, { shadow: false }); break;
      case 'gate': put(blocker(gate()), cx, cz, 0, main ? 1.2 : 1); break;
      case 'tree': if (N) {
        const pine = ['snow', 'mountain', 'hills'].includes(layout.theme) || /pine|spruce|fir|larch|taiga/i.test(`${layout.name} ${layout.description}`);
        const tm = N.get(pine ? (v ? 'Pine_1' : 'Pine_2') : ['CommonTree_1', 'CommonTree_2', 'CommonTree_3'][v]);
        put(blocker(tm), cx, cz, rng() * 6.28, sized(tm, (main ? 5.5 : 4.2) * (0.85 + rng() * 0.3)));
      } break;
      case 'reeds': put(reeds(v), cx, cz, rng() * 6.28, 1, { shadow: false }); heap(i => reeds((v + i + 1) % 3), main ? 3 : 1, 1.4, 1); break;
      case 'roots': put(roots(v), cx, cz, wallYaw(f), main ? 1.3 : 1, { shadow: false }); break;
      case 'boat': put(blocker(boat()), cx, cz, Math.round(yaw / (Math.PI / 2)) * Math.PI / 2 + 0.2, 1); break;
      case 'mist': {
        // (over the whole room, spread wide but kept low)
        const k = Math.max(1.6, Math.min(layout.W, layout.H) / 5);
        b.add(mist(), trs(ox + layout.W / 2, 0, oz + layout.H / 2, rng() * 6.28, k, 1, k), { shadow: false, receive: false });
        break;
      }
      case 'ice': put(blocker(crystal('ice')), cx, cz, yaw, s * (main ? 1.6 : 1.25), { shadow: false }); break;
      case 'flames': if (indoor && has('brazier')) break; put(blocker(flames(v)), cx, cz, yaw, main ? 1.4 : 1, { shadow: false }); if (torches) torches.push(new THREE.Vector3(cx, 0.9, cz)); break;
      case 'mirror': put(blocker(mirror()), cx, cz, wallYaw(f), 1); break;
      case 'bell': put(blocker(bell()), cx, cz, 0, main ? 1.25 : 1); break;
      case 'waterfall': put(blocker(waterfall()), cx, cz, wallYaw(f), main ? 1.2 : 1); break;
      case 'blood': case 'ash': case 'stake_holes': put(decal(f.k, v), cx, cz, yaw, 1, { shadow: false, receive: false }); break;
      default: break;
    }
  }
}

// the cells the features stand on (buildRoom draws scenery as if they were open floor, then gives
// them back to the walls of the walkable grid)
export function featureCells(layout) {
  const out = [];
  for (const f of layout.features || []) {
    if (!f.block) continue;
    for (let dy = 0; dy < f.h; dy++) for (let dx = 0; dx < f.w; dx++) out.push((f.y + dy) * layout.W + f.x + dx);
  }
  return out;
}
