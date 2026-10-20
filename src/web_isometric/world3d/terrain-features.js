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
  blue: 0x3a5ab0, teal: 0x2f8a86, yellow: 0xd8b04a, purple: 0x6a3a8a };

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
// chains: an iron post with a ring at the top, a chain hanging from it to a manacle on the ground
function chains() {
  return made('chains', () => {
    const iron = mat(IRON, { metalness: 0.55, roughness: 0.55 });
    const parts = [{ geometry: new THREE.BoxGeometry(0.12, 1.5, 0.12).translate(0, 0.75, 0), material: iron },
      { geometry: new THREE.TorusGeometry(0.1, 0.025, 5, 10).translate(0.12, 1.38, 0), material: iron }];
    for (let i = 0; i < 9; i++) {
      const g = new THREE.TorusGeometry(0.06, 0.018, 4, 8);
      if (i % 2) g.rotateY(Math.PI / 2);
      // a sagging run from the ring down to the ground and along it
      const t = i / 8;
      g.translate(0.18 + t * 0.55, Math.max(0.03, 1.3 * (1 - t) * (1 - t)), 0);
      parts.push({ geometry: g, material: iron });
    }
    parts.push({ geometry: new THREE.TorusGeometry(0.11, 0.035, 5, 12).rotateX(Math.PI / 2).translate(0.82, 0.04, 0), material: iron });
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
export function throne(color) {
  return made(`throne_${color || ''}`, () => {
    const m = mat(color === 'gold' ? 0xc89a3a : color === 'black' ? 0x2a2626 : STONE_DARK, color === 'gold' ? { metalness: 0.6, roughness: 0.4 } : {});
    return [
      { geometry: new THREE.BoxGeometry(1.1, 0.55, 0.9).translate(0, 0.275, 0), material: m },
      { geometry: new THREE.BoxGeometry(1.1, 1.7, 0.2).translate(0, 1.2, -0.38), material: m },
      { geometry: new THREE.BoxGeometry(0.16, 0.4, 0.8).translate(-0.5, 0.75, 0.02), material: m },
      { geometry: new THREE.BoxGeometry(0.16, 0.4, 0.8).translate(0.5, 0.75, 0.02), material: m },
      { geometry: new THREE.BoxGeometry(0.85, 0.1, 0.7).translate(0, 0.6, 0.05), material: mat(0x7a1e1e) },
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
function crystal(color) {
  return made(`crystal_${color || ''}`, () => {
    const c = COLOUR[color] || 0x8a6ae0;
    const m = mat(c, { emissive: c, emissiveIntensity: 0.9, roughness: 0.2 });
    return [0, 1, 2].map(i => ({ geometry: new THREE.OctahedronGeometry(0.16 + i * 0.05, 0).scale(0.6, 1.8, 0.6).rotateZ((i - 1) * 0.35).translate((i - 1) * 0.16, 0.3 + i * 0.05, (i % 2) * 0.08), material: m }));
  });
}
// flat on the ground: a splash of blood, a smear of ash, the holes of old stakes
function decal(kind, v) {
  return made(`decal_${kind}${v}`, () => {
    const col = kind === 'blood' ? 0x4a0a08 : kind === 'ash' ? 0x24221f : 0x1a1612;
    const m = mat(col, { transparent: true, opacity: kind === 'ash' ? 0.75 : 0.9, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 });
    const parts = [];
    const n = kind === 'stake_holes' ? 5 : 3;
    for (let i = 0; i < n; i++) {
      const r = kind === 'stake_holes' ? 0.09 : 0.25 + ((i * 37 + v * 13) % 10) / 22;
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
  const put = (model, x, z, yaw, s, opts) => { if (model) b.add(model, trs(x, 0, z, yaw, s), opts); };
  const putY = (model, x, y, z, yaw, s, opts) => { if (model) b.add(model, trs(x, y, z, yaw, s), opts); };
  for (const f of feats) {
    const cx = ox + f.x + f.w / 2, cz = oz + f.y + f.h / 2;
    const yaw = f.yaw || 0, s = f.s || 1, main = f.main;
    const v = (f.x * 7 + f.y * 3 + (f.i || 0)) % 3;
    const blocker = m => (occ ? occ(m) : m);
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
      case 'statue': put(blocker(statue()), cx, cz, yaw, s * (main ? 1.3 : 1)); break;
      case 'obelisk': put(blocker(obelisk()), cx, cz, yaw, s); break;
      case 'pillar': if (layout.theme === 'drow') put(blocker(drowPillar()), cx, cz, 0, 1); else if (D) put(blocker(D.get(v === 0 ? 'pillar_decorated' : 'column')), cx, cz, 0, 1); break;
      case 'well': if (T) put(blocker(T.get(['building_well_blue', 'building_well_green', 'building_well_red'][v])), cx, cz, yaw, 0.9); break;
      case 'fountain': put(blocker(fountain()), cx, cz, 0, main ? 1.25 : 1); break;
      case 'brazier': {
        put(blocker(brazier()), cx, cz, 0, 1);
        if (torches) torches.push(new THREE.Vector3(cx, 1.15, cz + 0.12));
        break;
      }
      case 'tent': if (T) put(blocker(T.get('tent')), cx, cz, yaw, sized(T.get('tent'), 2.2)); break;
      case 'cage': put(blocker(cage()), cx, cz, yaw, 1); break;
      case 'chains': put(chains(), cx, cz, yaw, 1); break;
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
      case 'candle': if (D || G) put(v === 1 && G ? G.get('candle_melted') : D.get('candle_triple'), cx, cz, yaw, 0.9, { shadow: false }); break;
      case 'torch': {
        if (!D) break;
        putY(D.get('torch_lit'), cx, 0.4, cz, 0, 1.6, { shadow: false });
        if (torches) torches.push(new THREE.Vector3(cx, 1.6, cz));
        break;
      }
      case 'lantern': if (G) put(G.get('lantern_standing'), cx, cz, yaw, 1); break;
      case 'drum': put(blocker(drum()), cx, cz, yaw, 1); break;
      case 'throne': put(blocker(throne(layout.theme === 'drow' ? 'black' : f.c)), cx, cz, Math.round(yaw / (Math.PI / 2)) * Math.PI / 2, main ? 1.25 : 1); break;
      // (a wizard's, a temple's, a haunted or elven hall's table is a plain one, not a feast)
      case 'table': if (F && layout.tone && ['arcane', 'holy', 'haunted', 'elven', 'infernal'].includes(layout.tone.interior)) put(blocker(F.get('table_medium')), cx, cz, Math.round(yaw / (Math.PI / 2)) * Math.PI / 2, 0.85);
        else if (D) put(blocker(D.get('table_long_decorated_A')), cx, cz, Math.round(yaw / (Math.PI / 2)) * Math.PI / 2, 0.9); break;
      case 'bench': if (G) put(G.get(v === 0 ? 'bench_decorated' : 'bench'), cx, cz, yaw, 1); break;
      case 'shelf': if (F) put(blocker(F.get(v === 0 ? 'shelf_B_large_decorated' : 'shelf_A_big')), cx, cz, yaw, 1); else if (D) put(blocker(D.get('shelves')), cx, cz, yaw, 1); break;
      case 'bed': if (F) put(blocker(F.get('bed_single_A')), cx, cz, yaw, 1); break;
      case 'chest': if (D) put(D.get(f.c === 'gold' ? 'chest_gold' : 'chest'), cx, cz, yaw, 1); break;
      case 'barrel': if (D) put(D.get(v === 0 ? 'barrel_large' : 'barrel_small'), cx, cz, yaw, 1); break;
      case 'crate': if (T) put(T.get(v === 0 ? 'crate_A_big' : v === 1 ? 'sack' : 'crate_B_small'), cx, cz, yaw, 1); break;
      case 'weapons': if (T) put(blocker(T.get('weaponrack')), cx, cz, yaw, 1); else if (D) put(D.get('sword_shield'), cx, cz, yaw, 1); break;
      case 'fence': if (T) put(T.get('fence_wood_straight'), cx, cz, yaw, 1); break;
      case 'dead_tree': if (N) put(blocker(N.get(v === 0 ? 'DeadTree_1' : 'DeadTree_2')), cx, cz, yaw, 0.6 + rng() * 0.25); break;
      case 'rubble': if (D) put(D.get(v === 0 ? 'rubble_large' : 'rubble_half'), cx, cz, yaw, 0.8, { shadow: false }); break;
      case 'cairn': put(cairn(v), cx, cz, yaw, s * (0.8 + v * 0.15)); break;
      case 'skull': if (G) put(G.get(v === 2 ? 'skull_candle' : 'skull'), cx, cz, yaw, 1, { shadow: false }); break;
      case 'bones': if (G) put(G.get(['bone_A', 'bone_B', 'ribcage'][v]), cx, cz, yaw, 1, { shadow: false }); break;
      case 'mushroom': if (N) for (let i = 0; i < 3; i++) put(N.get('Mushroom_Common'), cx + (rng() - 0.5) * 0.8, cz + (rng() - 0.5) * 0.8, rng() * 6.28, 0.7 + rng() * 0.5, { shadow: false }); break;
      case 'flowers': if (N) for (let i = 0; i < 2; i++) put(N.get(i ? 'Flower_3_Group' : 'Flower_4_Group'), cx + (rng() - 0.5) * 0.8, cz + (rng() - 0.5) * 0.8, rng() * 6.28, 0.7, { shadow: false }); break;
      case 'crystal': put(crystal(f.c), cx, cz, yaw, s, { shadow: false }); break;
      case 'rug': if (F) put(F.get(v === 0 ? 'rug_rectangle_A' : 'rug_oval_A'), cx, cz, Math.round(yaw / (Math.PI / 2)) * Math.PI / 2, 1, { shadow: false }); break;
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
