// Interiors in their zone's own style. Every 'inside' room was drawn as a homely house (plank
// floors, beds, standing lamps, pictures) whether it stood in a castle, a wizard's tower, a
// cathedral, the halls of the gods or a demon prince's temple. A zone states its style in
// world/looks.json 'interiors' (zone_tone.py sends it as the rooms' tone.interior), and here each
// style has its floor and walls, what stands along the walls and in the room, and its light:
//   castle   - flagstones, banners, weapon racks, a long table, standing torches, a real throne
//   arcane   - slate-blue stone, bookshelves, a glowing rune circle, floating crystals, violet light
//   holy     - white marble, white columns, an altar, candles, shafts of light from above
//   infernal - cracked red stone with lava in the cracks, braziers, skulls, a burning pentagram
//   haunted  - dark rotten boards, cobwebs, furniture knocked over, guttering lanterns, ghost light
//   dwarven  - granite, stout pillars banded in gold, a forge, kegs, axes and shields
//   elven    - pale living wood, trees growing through the hall, flowers, lanterns, green-gold light
//   foundry  - the Clockwork Foundry's own look (not an interior style but a zone look, room_looks.py):
//              steel plate, pipes along the walls, great gears, machines, furnaces and steam
// A room's use (a bedroom, a library, a shop, a tavern) still gets its furniture (terrain-town.js
// furnish); the style takes its walls, its centrepieces, its decorations and its light.
import * as THREE from 'three';
import { trs } from './assets.js';
import { tinted, WEB_MAT } from './terrain-looks.js';
import { throne } from './terrain-features.js';
import { Pieces } from './terrain-drow.js';

const FLOOR = 0, BLOCK = 1;
const C = (r, g, b) => new THREE.Color(r, g, b);
export const STYLES = {
  castle: { floor: r => (r < 0.06 ? 'floor_tile_small_broken_A' : 'floor_tile_large') },
  arcane: { floor: r => (r < 0.05 ? 'floor_tile_small_broken_A' : 'floor_tile_small'), tint: C(0.72, 0.76, 1.05), light: 0x9a7aff },
  holy: { floor: () => 'floor_tile_large', tint: C(1.5, 1.47, 1.42), light: 0xfff0c8 },
  infernal: { floor: r => (r < 0.3 ? 'floor_tile_small_broken_A' : 'floor_tile_small'), tint: C(0.78, 0.36, 0.3), light: 0xff4a1a },
  haunted: { floor: () => 'floor_wood_small_dark', tint: C(0.62, 0.68, 0.64), light: 0x9affb0 },
  dwarven: { floor: r => (r < 0.08 ? 'floor_tile_small' : 'floor_tile_large'), tint: C(1.12, 0.98, 0.8) },
  elven: { floor: () => 'floor_wood_large', tint: C(1.2, 1.28, 1.02), light: 0xc8ffb0 },
  foundry: { floor: r => (r < 0.12 ? 'floor_tile_small' : 'floor_tile_large'), tint: C(0.62, 0.6, 0.6), light: 0xff9a40 },
};
// the uses whose own furniture stays (furnish draws it); the rest are halls the style dresses
export const FURNISHED = new Set(['bedroom', 'library', 'tavern', 'shop', 'bank', 'guild']);
// the uses whose walls are their furniture (shelves, counters, casks): they keep it in any style
export const OWN_WALLS = new Set(['library', 'tavern', 'shop', 'bank']);
// the styles a house rug suits (not a wizard's floor of runes, a temple's marble or a hell's)
export const RUGS = new Set(['castle', 'haunted', 'dwarven', 'elven']);

export const interiorStyle = layout => (layout.theme === 'foundry' ? 'foundry'
  : layout.theme === 'inside' && layout.tone && STYLES[layout.tone.interior] ? layout.tone.interior : null);
export function styleFloor(style, r) {
  const s = STYLES[style];
  return { key: s.floor(r), tint: s.tint || null };
}
export const styleWall = (D, style) => (STYLES[style].tint ? tinted(D.get('wall'), STYLES[style].tint, `iwall_${style}`) : D.get('wall'));

// ---- materials and shapes built here ----
const glow = (r, g, b) => new THREE.MeshBasicMaterial({ color: new THREE.Color(r, g, b) });
const RUNE = { arcane: glow(1.3, 0.7, 3.0), infernal: glow(3.0, 0.7, 0.2) };
const CRYSTAL = new THREE.MeshStandardMaterial({ color: 0xb8a0ff, emissive: 0x7a5aff, emissiveIntensity: 1.4, roughness: 0.15, flatShading: true });
const LAVA = glow(2.6, 0.9, 0.15);
const GOLD = new THREE.MeshStandardMaterial({ color: 0xd4a640, metalness: 0.7, roughness: 0.35 });
const GRANITE = new THREE.MeshStandardMaterial({ color: 0x8a7e70, roughness: 0.9, flatShading: true });
const IRON = new THREE.MeshStandardMaterial({ color: 0x3a3836, metalness: 0.6, roughness: 0.5, flatShading: true });
const COALS = glow(2.4, 0.8, 0.2);
const BARK = new THREE.MeshStandardMaterial({ color: 0x7a6248, roughness: 0.95, flatShading: true });
const LEAVES = new THREE.MeshStandardMaterial({ color: 0x8ac070, roughness: 0.8, flatShading: true });
const BRASS = new THREE.MeshStandardMaterial({ color: 0xb08a40, metalness: 0.75, roughness: 0.35, flatShading: true });
const STEAM = new THREE.MeshBasicMaterial({ color: 0xe8e4dc, transparent: true, opacity: 0.08, depthWrite: false });
const SPARK = glow(0.6, 1.6, 3.2);
const SHEET = new THREE.MeshStandardMaterial({ color: 0xd8d8d0, roughness: 0.95, flatShading: true });
const WISP = glow(0.9, 2.2, 1.3);
const HOLE = new THREE.MeshBasicMaterial({ color: 0x050505 });
const SHAFT = new THREE.MeshBasicMaterial({ color: 0xfff2c8, transparent: true, opacity: 0.1, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
const at3 = (geo, x, y, z, yaw = 0) => geo.applyMatrix4(new THREE.Matrix4().compose(new THREE.Vector3(x, y, z),
  new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), yaw), new THREE.Vector3(1, 1, 1)));

// a ring of runes laid in the floor: two circles, ticks between them, a star inside (infernal)
function runeCircle(P, x, z, r, mat, star) {
  for (const rr of [r, r * 0.84]) P.add(mat, at3(new THREE.TorusGeometry(rr, 0.035, 3, 48).rotateX(Math.PI / 2), x, 0.03, z));
  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * Math.PI * 2;
    P.add(mat, at3(new THREE.BoxGeometry(0.06, 0.02, r * 0.12), x + Math.cos(a) * r * 0.92, 0.03, z + Math.sin(a) * r * 0.92, -a));
  }
  if (star) for (let i = 0; i < 5; i++) {
    const a = -Math.PI / 2 + (i / 5) * Math.PI * 2, b = -Math.PI / 2 + (((i + 2) % 5) / 5) * Math.PI * 2;
    const ax = Math.cos(a) * r * 0.82, az = Math.sin(a) * r * 0.82, bx = Math.cos(b) * r * 0.82, bz = Math.sin(b) * r * 0.82;
    const len = Math.hypot(bx - ax, bz - az);
    P.add(mat, at3(new THREE.BoxGeometry(len, 0.02, 0.06), x + (ax + bx) / 2, 0.03, z + (az + bz) / 2, -Math.atan2(bz - az, bx - ax)));
  }
}
function crystal(P, x, y, z, s = 1) {
  P.add(CRYSTAL, at3(new THREE.OctahedronGeometry(0.28 * s, 0).scale(0.7, 1.7, 0.7), x, y, z));
}
function tree(P, x, z, h = 4.2) {
  P.add(BARK, at3(new THREE.CylinderGeometry(0.28, 0.5, h, 7).translate(0, h / 2, 0), x, 0, z));
  for (let i = 0; i < 4; i++) {
    const a = i * 1.7;
    P.add(BARK, at3(new THREE.CylinderGeometry(0.05, 0.14, 1.4, 5).translate(0, 0.7, 0).rotateZ(0.9).rotateY(a), x, h * 0.62, z));
  }
  P.add(LEAVES, at3(new THREE.IcosahedronGeometry(1.5, 0).scale(1.2, 0.7, 1.2), x, h + 0.3, z));
}
function forge(P, x, z) {
  P.add(GRANITE, at3(new THREE.BoxGeometry(1.6, 0.9, 1.2).translate(0, 0.45, 0), x, 0, z));
  P.add(COALS, at3(new THREE.BoxGeometry(1.2, 0.08, 0.8), x, 0.92, z));
  P.add(GRANITE, at3(new THREE.CylinderGeometry(0.35, 0.5, 1.6, 6).translate(0, 1.7, 0), x, 0, z - 0.3));
  P.add(IRON, at3(new THREE.BoxGeometry(0.7, 0.28, 0.3).translate(0, 0.62, 0), x + 1.3, 0, z));       // the anvil
  P.add(IRON, at3(new THREE.BoxGeometry(0.3, 0.48, 0.24).translate(0, 0.24, 0), x + 1.3, 0, z));
}
// a great gear on the wall: a rim, teeth, spokes and a hub, in brass or iron
function gear(P, x, y, z, r, yaw, mat) {
  const g = [];
  g.push(new THREE.TorusGeometry(r, r * 0.12, 4, 24));
  const teeth = Math.max(8, Math.round(r * 10));
  for (let i = 0; i < teeth; i++) {
    const a = (i / teeth) * Math.PI * 2;
    g.push(new THREE.BoxGeometry(r * 0.22, r * 0.22, r * 0.18).rotateZ(a).translate(Math.cos(a) * r * 1.12, Math.sin(a) * r * 1.12, 0));
  }
  for (let i = 0; i < 4; i++) g.push(new THREE.BoxGeometry(r * 2, r * 0.1, r * 0.1).rotateZ((i / 4) * Math.PI));
  g.push(new THREE.CylinderGeometry(r * 0.22, r * 0.22, r * 0.3, 8).rotateX(Math.PI / 2));
  for (const geo of g) P.add(mat, at3(geo, x, y, z, yaw));
}
function pipeRun(P, x0, z0, x1, z1, y, r = 0.12) {
  const len = Math.hypot(x1 - x0, z1 - z0);
  P.add(IRON, at3(new THREE.CylinderGeometry(r, r, len, 8).rotateZ(Math.PI / 2), (x0 + x1) / 2, y, (z0 + z1) / 2, -Math.atan2(z1 - z0, x1 - x0)));
  for (let t = 1; t < len; t += 2) {
    const k = t / len;
    P.add(BRASS, at3(new THREE.CylinderGeometry(r * 1.4, r * 1.4, 0.12, 8).rotateZ(Math.PI / 2), x0 + (x1 - x0) * k, y, z0 + (z1 - z0) * k, -Math.atan2(z1 - z0, x1 - x0)));
  }
}
// a machine: an iron housing, a brass piston, a pressure gauge, a stack venting steam
function machine(P, x, z, rng) {
  const h = 1.2 + rng() * 0.8;
  P.add(IRON, at3(new THREE.BoxGeometry(1.5, h, 1.3).translate(0, h / 2, 0), x, 0, z));
  P.add(BRASS, at3(new THREE.CylinderGeometry(0.16, 0.16, 1.1, 8).translate(0, h + 0.55, 0), x + 0.4, 0, z));
  P.add(BRASS, at3(new THREE.CylinderGeometry(0.22, 0.22, 0.08, 12).rotateX(Math.PI / 2), x - 0.3, h * 0.65, z + 0.66));
  P.add(IRON, at3(new THREE.CylinderGeometry(0.14, 0.18, 1.2, 8).translate(0, h + 0.6, 0), x - 0.45, 0, z - 0.3));
  for (let i = 0; i < 3; i++) P.add(STEAM, at3(new THREE.IcosahedronGeometry(0.25 + i * 0.12, 0), x - 0.45 + (rng() - 0.5) * 0.3, h + 1.4 + i * 0.45, z - 0.3));
}
function furnace(P, x, z) {
  P.add(GRANITE, at3(new THREE.BoxGeometry(2, 2, 1.6).translate(0, 1, 0), x, 0, z));
  P.add(COALS, at3(new THREE.BoxGeometry(1.1, 0.7, 0.05), x, 0.7, z + 0.81));
  P.add(IRON, at3(new THREE.CylinderGeometry(0.3, 0.42, 2.2, 8).translate(0, 3.1, 0), x, 0, z - 0.3));
}
function conveyor(P, x, z, len, yaw) {
  P.add(IRON, at3(new THREE.BoxGeometry(len, 0.12, 0.9).translate(0, 0.62, 0), x, 0, z, yaw));
  for (let t = -len / 2 + 0.3; t < len / 2; t += 0.6) P.add(BRASS, at3(new THREE.CylinderGeometry(0.06, 0.06, 0.95, 6).rotateX(Math.PI / 2).translate(t, 0.52, 0), x, 0, z, yaw));
  for (const s of [-1, 1]) P.add(IRON, at3(new THREE.BoxGeometry(0.1, 0.55, 0.1).translate(s * (len / 2 - 0.1), 0.28, 0), x, 0, z, yaw));
}
function goldBand(P, x, z, y, r) { P.add(GOLD, at3(new THREE.TorusGeometry(r, 0.06, 4, 16).rotateX(Math.PI / 2), x, y, z)); }
function shaft(P, x, z) { P.add(SHAFT, at3(new THREE.CylinderGeometry(0.9, 1.5, 6, 12, 1, true).translate(0, 3, 0), x, 0, z)); }
function lavaCrack(P, x, z, rng) {
  let a = rng() * Math.PI, px = x, pz = z;
  for (let i = 0; i < 4; i++) {
    const len = 0.5 + rng() * 0.7;
    P.add(LAVA, at3(new THREE.BoxGeometry(len, 0.015, 0.05), px + Math.cos(a) * len / 2, 0.025, pz + Math.sin(a) * len / 2, -a));
    px += Math.cos(a) * len; pz += Math.sin(a) * len; a += (rng() - 0.5) * 1.4;
  }
}
function light(c, x, z, color, y = 3.2, power = 22) {
  const l = new THREE.PointLight(color, power, 15, 1.4);
  l.position.set(x, y, z);
  c.group.add(l);
}

export function dressInterior(c, style, kind) {
  const { layout, ox, oz, kits, b, rng, occ, torches } = c;
  const D = kits.dungeon, F = kits.furniture, G = kits.graveyard, T = kits.town, N = kits.nature;
  const { W, H, grid, gaps = {} } = layout;
  const P = new Pieces();
  const mx = Math.floor(W / 2), my = Math.floor(H / 2), cx = ox + W / 2, cz = oz + H / 2;
  const at = (x, y) => grid[y * W + x];
  const lane = (x, y) => ((gaps.north || gaps.south) && Math.abs(x - mx) <= 3) || ((gaps.east || gaps.west) && Math.abs(y - my) <= 2)
    || (Math.abs(x - mx) <= 1 && Math.abs(y - my) <= 1);
  const block = (x, y) => { if (x > 0 && y > 0 && x < W - 1 && y < H - 1) grid[y * W + x] = BLOCK; };
  const put = (kit, key, x, z, yaw = 0, s = 1, opts) => { const m = kit && kit.get(key); if (m) b.add(opts && opts.occ ? occ(m) : m, trs(x, opts && opts.y || 0, z, yaw, s), opts); return !!m; };
  // knocked over: rolled onto its side
  const fallen = (kit, key, x, z, s = 0.8) => {
    const m = kit && kit.get(key);
    if (m) b.add(m, new THREE.Matrix4().compose(new THREE.Vector3(x, 0.25, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.PI / 2 * (rng() < 0.5 ? 1 : -1), rng() * 6.28, 0)), new THREE.Vector3(s, s, s)));
  };
  // a dungeon-kit piece in the style's stone
  const stone = (tint, tag) => ({ get: key => tinted(D.get(key), tint, `${tag}_${key}`) });
  const furnished = FURNISHED.has(kind);
  const own = STYLES[style].light != null;     // the style lights the room itself (no warm torchlight)

  if (style === 'foundry') return foundryDress(c, { P, put, block, lane, at, mx, my, cx, cz });

  // ---- along the north wall (the one the camera faces) and the sides ----
  const wallSpots = [];
  for (let x = 3; x < W - 3; x += 4) if (at(x, 1) === FLOOR && at(x + 1, 1) === FLOOR && !lane(x, 1)) wallSpots.push(x);
  const sideSpots = [];
  for (const [x, yaw] of [[1, Math.PI / 2], [W - 2, -Math.PI / 2]]) for (let y = 3; y < H - 3; y += 4) if (at(x, y) === FLOOR && !lane(x, y)) sideSpots.push([x, y, yaw]);
  {
    for (const x of wallSpots) {
      // (a furnished room's wall keeps room for its own furniture: only hung things there)
      if (furnished && (OWN_WALLS.has(kind) || style === 'arcane' || style === 'elven' || style === 'haunted')) continue;
      const wx = ox + x + 1, wz = oz + 1.05;
      if (style === 'castle') put(D, ['banner_patternA_red', 'banner_patternB_blue', 'banner_shield_white'][(x >> 2) % 3], wx, oz + 0.8, 0, 0.65);
      else if (style === 'arcane') { put(F, 'shelf_B_large_decorated', wx, wz + 0.3, 0, 0.85, { occ: true }); block(x, 1); block(x + 1, 1); }
      else if (style === 'holy') put(D, 'banner_shield_white', wx, oz + 0.8, 0, 0.65);
      else if (style === 'infernal') put(D, 'banner_thin_red', wx, oz + 0.8, 0, 0.7);
      else if (style === 'dwarven') { if ((x >> 2) % 2) put(D, 'sword_shield', wx, wz + 0.2, 0, 0.8); else put(D, 'banner_patternA_red', wx, oz + 0.8, 0, 0.65); }
      else if (style === 'elven' && N) put(N, rng() < 0.5 ? 'Fern_1' : 'Bush_Common_Flowers', wx, wz + 0.2, rng() * 6.28, 1.1, { shadow: false });
      else if (style === 'haunted' && F) put(F, rng() < 0.5 ? 'pictureframe_large_A' : 'cabinet_medium', wx, wz + 0.3, rng() < 0.4 ? 0.25 : 0, 0.85, { occ: true, y: 0 });
    }
    for (const [x, y, yaw] of furnished ? [] : sideSpots) {
      if (rng() < 0.35) continue;
      const sx = ox + x + 0.5 + (x === 1 ? -0.2 : 0.2), sz = oz + y + 0.5;
      if (style === 'castle' || style === 'dwarven') { if (T) { put(T, 'weaponrack', sx, sz, yaw, 4.5); block(x, y); } }
      else if (style === 'arcane') { put(F, 'shelf_B_large', sx, sz, yaw, 0.8, { occ: true }); block(x, y); }
      else if (style === 'holy') { put(G, 'candle_triple', sx, sz, 0, 1); }
      else if (style === 'infernal') { put(G, 'skull_candle', sx, sz, rng() * 6.28, 0.9); }
      else if (style === 'haunted') { put(G, 'candle_melted', sx, sz, 0, 1); }
      else if (style === 'elven' && G) { put(G, 'lantern_standing', sx, sz, 0, 1); torches.push(new THREE.Vector3(sx, 1.4, sz)); }
    }
  }

  // ---- roomgen's obstacles (they block already): the style's centrepieces ----
  if (!furnished) for (const o of layout.obstacles || []) {
    const x = ox + o.x + (o.big ? 1 : 0.5), z = oz + o.y + (o.big ? 1 : 0.5);
    const yaw = Math.floor(rng() * 4) * Math.PI / 2, r = rng();
    if (style === 'castle') {
      if (o.big) { if (r < 0.45) put(D, 'pillar', x, z, yaw, 1, { occ: true }); else { put(D, 'table_long_decorated_A', x, z, yaw, 0.9, { occ: true }); put(D, 'candle_triple', x, z, 0, 0.7, { y: 0.95 }); } }
      else put(D, r < 0.5 ? 'sword_shield' : 'barrel_small', x, z, yaw, 0.8);
    } else if (style === 'arcane') {
      if (o.big) { put(F, 'table_medium', x, z, yaw, 0.8, { occ: true }); put(F, 'book_set', x, z, rng() * 6.28, 0.8, { shadow: false, y: 0.85 }); }
      else { crystal(P, x, 1.1 + rng() * 0.4, z, 1); }
    } else if (style === 'holy') {
      if (o.big) { put(stone(C(2.6, 2.55, 2.45), 'holy'), 'pillar', x, z, 0, 0.9, { occ: true }); goldBand(P, x, z, 0.5, 0.6); goldBand(P, x, z, 2.9, 0.5); }
      else put(G, 'candle_triple', x, z, 0, 1);
    } else if (style === 'infernal') {
      if (o.big) { put(stone(C(0.5, 0.22, 0.2), 'hell'), 'pillar', x, z, yaw, 0.9, { occ: true }); }
      else { put(D, 'torch_lit', x, z, 0, 1.6, { y: 0.4, shadow: false }); light(c, x, z, 0xff4a1a, 2, 10); }
    } else if (style === 'haunted') {
      // furniture under dust sheets, or knocked over; a skull in the dust
      if (o.big && r < 0.55) { P.add(SHEET, at3(new THREE.BoxGeometry(1.6, 0.9, 1.1).translate(0, 0.45, 0), x, 0, z, rng())); P.add(SHEET, at3(new THREE.SphereGeometry(0.62, 7, 4, 0, Math.PI * 2, 0, Math.PI / 2).scale(1.3, 0.5, 0.9), x, 0.9, z)); }
      else if (o.big) fallen(F, r < 0.8 ? 'table_medium' : 'cabinet_medium', x, z, 0.85);
      else if (r < 0.5) fallen(F, 'chair_A_wood', x, z, 0.8); else put(G, 'skull', x, z, rng() * 6.28, 1);
    } else if (style === 'dwarven') {
      if (o.big && r < 0.3) forge(P, x - 0.4, z);
      else if (o.big) { put(stone(STYLES.dwarven.tint, 'dwarf'), 'pillar', x, z, 0, 1.1, { occ: true }); goldBand(P, x, z, 1.2, 0.62); goldBand(P, x, z, 2.4, 0.58); }
      else put(D, r < 0.5 ? 'keg' : 'barrel_small', x, z, yaw, r < 0.5 ? 0.45 : 0.85);
    } else if (style === 'elven') {
      if (o.big) tree(P, x, z, 3.8 + rng() * 1.2);
      else if (N) put(N, r < 0.5 ? 'Flower_3_Group' : 'Plant_7', x, z, rng() * 6.28, 1, { shadow: false });
    }
  }

  // ---- the middle of the room ----
  if (!furnished) {
    if (style === 'arcane') { runeCircle(P, cx, cz, 2.4, RUNE.arcane, false); crystal(P, cx, 2.6, cz, 1.6); }
    if (style === 'infernal') runeCircle(P, cx, cz, 2.6, RUNE.infernal, true);
    if (style === 'castle' && F && kind !== 'temple' && kind !== 'throne') put(F, 'rug_rectangle_stripes_A', cx, cz, Math.PI / 2, 1.2, { shadow: false, receive: true });
    // the throne room's throne (the house kit's armchair in a castle hall was a cushioned armchair)
    if (kind === 'throne' && !gaps.north && style !== 'haunted') {
      const col = style === 'holy' || style === 'dwarven' ? 'gold' : style === 'infernal' ? 'black' : 'red';
      put({ get: () => throne(col) }, 'throne', cx, oz + 2.2, 0, 1.3);
      // a high carved back over it, crowned in gold, so it reads as a throne and not a hearth
      P.add(style === 'infernal' ? IRON : GRANITE, at3(new THREE.BoxGeometry(1.7, 3.2, 0.24).translate(0, 1.6, 0), cx, 0, oz + 1.55));
      P.add(GOLD, at3(new THREE.ConeGeometry(0.22, 0.5, 4).translate(0, 3.45, 0), cx, 0, oz + 1.55));
      for (const sx of [-0.7, 0.7]) P.add(GOLD, at3(new THREE.ConeGeometry(0.14, 0.36, 4).translate(sx, 3.35, 0), cx, 0, oz + 1.55));
      block(mx, 2); block(mx - 1, 2);
    }
    if (style === 'holy' && kind !== 'temple' && !gaps.north && at(mx, 2) === FLOOR) { put(G, 'shrine_candles', cx, oz + 2.2, 0, 0.75); block(mx, 2); block(mx - 1, 2); }
  }
  if (style === 'holy') for (const [fx, fz] of [[0.3, 0.35], [0.7, 0.6]]) shaft(P, ox + W * fx, oz + H * fz);
  if (style === 'infernal') for (let i = 0; i < 6; i++) lavaCrack(P, ox + 2 + rng() * (W - 4), oz + 2 + rng() * (H - 4), rng);
  if (style === 'haunted') {
    // ghostly wisps drifting at head height; holes broken through the boards
    for (let i = 0; i < 5; i++) P.add(WISP, at3(new THREE.IcosahedronGeometry(0.12 + rng() * 0.08, 1), ox + 2 + rng() * (W - 4), 1.3 + rng() * 1.2, oz + 2 + rng() * (H - 4)));
    for (let i = 0; i < 4; i++) {
      const hx = 2 + Math.floor(rng() * (W - 4)), hy = 2 + Math.floor(rng() * (H - 4));
      if (lane(hx, hy) || at(hx, hy) !== FLOOR) continue;
      P.add(HOLE, at3(new THREE.PlaneGeometry(0.7 + rng() * 0.5, 0.4 + rng() * 0.4).rotateX(-Math.PI / 2), ox + hx + 0.5, 0.012, oz + hy + 0.5, rng() * 3));
    }
  }
  if (style === 'haunted' && WEB_MAT) for (const [wx, wz, yaw] of [[1, 1, 0], [W - 1, 1, -Math.PI / 2], [1, H - 1, Math.PI / 2], [W - 1, H - 1, Math.PI], [W / 2 - 3, 1, 0], [W / 2 + 3, 1, -Math.PI / 2]]) {
    const g = new THREE.PlaneGeometry(1.8, 1.8);
    g.translate(0.9, -0.9, 0); g.rotateY(Math.PI / 4); g.rotateY(yaw);
    g.translate(ox + wx, 2.55, oz + wz);
    c.owned.push(g);
    c.group.add(new THREE.Mesh(g, WEB_MAT));
  }
  // ---- props (walk-through): small things ----
  if (!furnished) for (const p of layout.props || []) {
    const x = ox + p.x + 0.5, z = oz + p.y + 0.5, r = rng();
    if (style === 'arcane') put(F, r < 0.5 ? 'book_single' : 'book_set', x, z, rng() * 6.28, 0.7, { shadow: false });
    else if (style === 'holy' || style === 'castle') put(G, 'candle_thin', x, z, 0, 1, { shadow: false });
    else if (style === 'infernal') put(G, ['bone_A', 'bone_B', 'skull', 'ribcage'][Math.floor(r * 4)], x, z, rng() * 6.28, 0.9, { shadow: false });
    else if (style === 'haunted') put(G, r < 0.5 ? 'candle_melted' : 'bone_C', x, z, rng() * 6.28, 0.9, { shadow: false });
    else if (style === 'dwarven') put(D, r < 0.5 ? 'coin_stack_large' : 'candle_lit', x, z, rng() * 6.28, r < 0.5 ? 0.45 : 0.9, { shadow: false });
    else if (style === 'elven' && N) put(N, r < 0.5 ? 'Clover_1' : 'Mushroom_Common', x, z, rng() * 6.28, 0.8, { shadow: false });
  }
  // ---- standing light: torches in a castle and a dwarven hall; the style's own light elsewhere ----
  for (const [fx, fy] of [[2, 2], [W - 3, 2]]) {
    if (at(fx, fy) !== FLOOR || lane(fx, fy)) continue;
    if (style === 'castle' || style === 'dwarven') {
      put(D, 'torch_lit', ox + fx + 0.5, oz + fy + 0.5, 0, 1.5, { y: 0.4, shadow: false });
      torches.push(new THREE.Vector3(ox + fx + 0.5, 1.6, oz + fy + 0.5));
      block(fx, fy);
    } else if (style === 'haunted' && G) { put(G, 'lantern_standing', ox + fx + 0.5, oz + fy + 0.5, 0, 1); block(fx, fy); }
  }
  if (own) {
    torches.length = 0;
    const col = STYLES[style].light;
    light(c, ox + W * 0.3, oz + H * 0.45, col, 3.2, style === 'haunted' ? 12 : 22);
    light(c, ox + W * 0.7, oz + H * 0.45, col, 3.2, style === 'haunted' ? 12 : 22);
  }
  P.flush(c);
  return true;
}

// the Clockwork Foundry: pipes along the walls, great gears turning in them, machines and conveyors
// on the floor, a furnace where the room's name says so, sparks in the Tesla corridor
function foundryDress(c, { P, put, block, lane, at, mx, my, cx, cz }) {
  const { layout, ox, oz, kits, rng } = c;
  const D = kits.dungeon;
  const { W, H } = layout;
  const name = `${layout.name || ''}`.toLowerCase();
  // pipes along the top of the north and side walls, and a gear in the north wall every few metres
  pipeRun(P, ox + 1, oz + 1.1, ox + W - 1, oz + 1.1, 2.3, 0.14);
  pipeRun(P, ox + 1, oz + 1.25, ox + W - 1, oz + 1.25, 1.7, 0.09);
  for (const x of [1.15, W - 1.15]) pipeRun(P, ox + x, oz + 1, ox + x, oz + H - 1, 2.1, 0.12);
  for (let x = 4; x < W - 3; x += 6) gear(P, ox + x, 1.4, oz + 0.75, 0.9 + rng() * 0.5, 0, rng() < 0.5 ? BRASS : IRON);
  // the floor's machines on roomgen's obstacles (they block already)
  const furnaceRoom = /\b(furnace|forge|smelt|boiler|power core|coal)\b/.test(name);
  let furnaces = 0;
  for (const o of layout.obstacles || []) {
    const x = ox + o.x + (o.big ? 1 : 0.5), z = oz + o.y + (o.big ? 1 : 0.5), r = rng();
    if (o.big && furnaceRoom && furnaces < 2) { furnace(P, x, z); furnaces++; light(c, x, z + 1.2, 0xff7a20, 1.4, 24); }
    else if (o.big && r < 0.55) machine(P, x, z, rng);
    else if (o.big) conveyor(P, x, z, 2.4, Math.floor(rng() * 2) * Math.PI / 2);
    else put(D, r < 0.5 ? 'barrel_small' : 'box_large', x, z, rng() * 6.28, r < 0.5 ? 0.85 : 0.6);
  }
  // an assembly line runs down the room where its name says so (off the ways through)
  if (/\b(assembly|conveyor|intake|line)\b/.test(name)) for (const z of [3.5, H - 3.5]) {
    const y = Math.floor(z);
    let ok = true;
    for (let x = 3; x < W - 3; x++) if (at(x, y) !== FLOOR || lane(x, y)) { ok = false; break; }
    if (ok) { conveyor(P, ox + W / 2, oz + z, W - 8, 0); for (let x = 4; x < W - 4; x++) block(x, y); }
  }
  // the Tesla corridor's sparks; steam everywhere else
  if (/\b(tesla|power|coil|lightning)\b/.test(name)) {
    for (let i = 0; i < 10; i++) {
      const x = ox + 2 + rng() * (W - 4), y = 1.4 + rng() * 1.2;
      P.add(SPARK, at3(new THREE.BoxGeometry(0.6 + rng() * 0.8, 0.04, 0.04).rotateZ((rng() - 0.5) * 1.6), x, y, oz + 1.2, 0));
    }
    light(c, cx, cz - 3, 0x7ab8ff, 2.8, 26);
  }
  for (let i = 0; i < 5; i++) {
    const x = ox + 2 + rng() * (W - 4), z = oz + 2 + rng() * (H - 4);
    for (let k = 0; k < 3; k++) P.add(STEAM, at3(new THREE.IcosahedronGeometry(0.22 + k * 0.12, 1), x + (rng() - 0.5) * 0.5, 0.5 + k * 0.5, z));
  }
  c.torches.length = 0;
  light(c, ox + W * 0.3, oz + H * 0.4, STYLES.foundry.light, 3, 22);
  light(c, ox + W * 0.7, oz + H * 0.4, STYLES.foundry.light, 3, 22);
  P.flush(c);
  return true;
}
