// Seeing further (docs/OPEN_WORLD.md, phase 2; the owner: "the world should feel more open world
// like"). Only the rooms round the hero are built in full (zone.js); past them the zone is drawn
// here, cheaply: one tinted ground tile per room and a few shapes for what stands in it (crowns of
// trees, mounds, crags, roofs), every room's in a handful of instanced meshes (a few draw calls for
// the whole zone). A room's stand-in shows only while the room itself is not built and drawn, on
// the hero's own level, within the quality's reach; and outdoors a ring of far hills stands
// round the hero, the haze's colour, so the land never simply ends.
//
// And past the zone's rooms, its empty map cells are more of the country nearest them (filler
// cells, edges.js fillKind): the open sea runs on as sea to the haze, a forest as forest, a marsh
// as marsh, rather than the sky showing through at the room's edge (the owner, on the Sea of
// Storms). Their shapes stand back where a built room's own land (terrain.js fillerLand) lies.
import * as THREE from 'three';
import { ROOM_W, ROOM_H, GROUND, WATER_MAT } from './terrain.js';
import { fillKind, landSides, SIDES } from './edges.js';

// how many rooms out the stand-ins reach, and how much further the outdoor haze lies, by quality
export const FAR = { low: { range: 6, sight: 1.25 }, med: { range: 8, sight: 1.45 }, high: { range: 10, sight: 1.65 } };

const UNDER = new Set(['cave', 'mine', 'ice_cave', 'lava_cave', 'sewer', 'dungeon', 'crypt', 'underwater', 'web', 'drow', 'foundry']);
const TOWN = new Set(['city', 'castle', 'village', 'camp', 'necropolis', 'ruins', 'garden', 'terrace']);
const WATER = new Set(['water_swim', 'water_noswim', 'shore']);
// how far past the zone's rooms the filler cells reach (in rooms; the haze takes over beyond)
export const FILL_REACH = 4;

// what a room is, seen from afar
export function farKind(theme) {
  if (!theme || UNDER.has(theme)) return 'none';
  if (WATER.has(theme)) return theme === 'shore' ? 'field' : 'water';
  if (TOWN.has(theme)) return 'town';
  if (theme === 'inside') return 'roof';
  if (['forest', 'darkforest', 'swamp', 'snow', 'hills', 'mountain', 'desert', 'field', 'stones', 'volcanic'].includes(theme)) return theme;
  return 'field';
}

// the shapes one room is given (room-local metres): [layer, x, z, sx, sy, sz, colour]
export function farShapes(kind, rnd) {
  const out = [];
  const spot = () => [1.5 + rnd() * (ROOM_W - 3), 1.5 + rnd() * (ROOM_H - 3)];
  const add = (layer, n, size, col) => { for (let i = 0; i < n; i++) { const [x, z] = spot(); const s = size[0] + rnd() * (size[1] - size[0]); out.push([layer, x, z, s, s * (layer === 'crown' ? 1.6 : layer === 'mound' ? 0.45 : 1), s, col(rnd())]); } };
  const greens = r => new THREE.Color().setHSL(0.27 + r * 0.06, 0.45, 0.2 + r * 0.08).getHex();
  if (kind === 'forest' || kind === 'darkforest') add('crown', 13, [1.6, 2.4], kind === 'darkforest' ? r => new THREE.Color().setHSL(0.3, 0.35, 0.13 + r * 0.05).getHex() : greens);
  else if (kind === 'swamp') { add('crown', 5, [1.2, 1.8], r => new THREE.Color().setHSL(0.2, 0.3, 0.18 + r * 0.05).getHex()); }
  else if (kind === 'snow') { add('crown', 7, [1.4, 2.0], r => new THREE.Color().setHSL(0.45, 0.15, 0.55 + r * 0.15).getHex()); add('mound', 3, [3, 5], () => 0xe8eef6); }
  else if (kind === 'field' || kind === 'stones') { add('crown', 2, [1.4, 2.0], greens); add('rock', 2, [0.5, 0.9], () => 0x8a8478); }
  else if (kind === 'hills') { add('mound', 4, [4, 7], r => new THREE.Color().setHSL(0.24, 0.35, 0.32 + r * 0.06).getHex()); add('crown', 3, [1.4, 2.0], greens); }
  else if (kind === 'mountain' || kind === 'volcanic') add('rock', 5, [2.5, 4.5], r => new THREE.Color().setHSL(kind === 'volcanic' ? 0.03 : 0.1, 0.08, 0.35 + r * 0.12).getHex());
  else if (kind === 'desert') add('mound', 3, [4, 7], () => 0xd9bf8a);
  else if (kind === 'town') add('house', 6, [3.2, 4.6], r => new THREE.Color().setHSL(0.08, 0.25, 0.45 + r * 0.15).getHex());
  else if (kind === 'roof') out.push(['house', ROOM_W / 2, ROOM_H / 2, 16, 4, 10, 0x8a7a68]);
  return out;
}

const LAYERS = {
  crown: () => new THREE.ConeGeometry(1, 1, 6).translate(0, 0.9, 0),
  mound: () => new THREE.SphereGeometry(1, 8, 5, 0, Math.PI * 2, 0, Math.PI / 2),
  rock: () => new THREE.IcosahedronGeometry(1, 0).translate(0, 0.4, 0),
  house: () => new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0),
};

export class FarView {
  // zone: {num, rooms, group}: a Zone, or a neighbouring zone's map drawn past the border
  // (zone.js addGhost: its group placed where the border puts it, no horizon of its own)
  constructor(zone, { horizon = true } = {}) {
    this.zone = zone;
    this.group = new THREE.Group();
    this.group.name = `far_${zone.num}`;
    this.cells = [];             // [{room, level, parts: [[mesh, i]], shown}]
    this.fills = [];             // filler cells: [{cx, cy, level, tile: parts, shapes: parts, shown}]
    this.range = FAR.high.range;
    this.outdoors = false;
    this.sea = false;            // on open water: the far hills lie flat (main.js)
    this.taken = null;           // (cx, cy) => true: a neighbouring zone draws that cell (zone.js)
    this.cellSet = new Set();
    for (const room of zone.rooms.values()) this.cellSet.add(`${room.cx},${room.cy}`);
    const mat = new THREE.MeshLambertMaterial({ color: 0xffffff });
    const plans = [];
    const counts = { tile: 0, sea: 0, crown: 0, mound: 0, rock: 0, house: 0 };
    // (water: the room's own wet bed, under the room's own water surface, so the far sea and the
    // room's are one sea)
    const tileOf = (kind, theme) => {
      const pal = GROUND[theme] || GROUND.default;
      const mid = new THREE.Color(pal.a).lerp(new THREE.Color(pal.b), 0.5);
      // (as terrain.js groundSheet colours a water room's bed: its ground, mostly gone to wet)
      return kind === 'water' ? mid.lerp(new THREE.Color(pal.wet || 0x22485a), 0.8).getHex() : mid.multiplyScalar(0.9).getHex();
    };
    for (const room of zone.rooms.values()) {
      const theme = MH.themeForSector((room.data.look || room.data.sector || '') + '');
      const kind = farKind(theme);
      if (kind === 'none') continue;
      const rnd = MH.mulberry32((room.vnum * 2654435761) ^ 0x51);
      const shapes = farShapes(kind, rnd);
      plans.push({ room, tile: tileOf(kind, theme), shapes, sea: kind === 'water' });
      counts.tile++;
      if (kind === 'water') counts.sea++;
      for (const s of shapes) counts[s[0]]++;
    }
    // the filler cells (the zone's own view only: a neighbour's is drawn past its border)
    const fills = horizon && zone.cells ? fillerPlan(zone) : [];
    for (const f of fills) {
      const rnd = MH.mulberry32(((f.cx * 73856093) ^ (f.cy * 19349663) ^ 0x2f1) >>> 0);
      f.shapes = farShapes(f.kind, rnd);
      f.tile = tileOf(f.kind, f.theme);
      counts.tile++;
      if (f.kind === 'water') counts.sea++;
      for (const sh of f.shapes) counts[sh[0]]++;
    }
    this.meshes = {};
    for (const [layer, n] of Object.entries(counts)) {
      if (!n) continue;
      const geo = layer === 'tile' || layer === 'sea' ? new THREE.PlaneGeometry(ROOM_W, ROOM_H).rotateX(-Math.PI / 2) : LAYERS[layer]();
      const m = new THREE.InstancedMesh(geo, layer === 'sea' ? WATER_MAT : mat, n);
      m.frustumCulled = false;     // (one mesh spans the zone)
      m.castShadow = m.receiveShadow = false;
      this.meshes[layer] = m;
      this.group.add(m);
    }
    const used = { tile: 0, sea: 0, crown: 0, mound: 0, rock: 0, house: 0 };
    const mtx = new THREE.Matrix4(), col = new THREE.Color(), q = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0);
    for (const { room, tile, shapes, sea } of plans) {
      const parts = [];
      const put = (layer, x, y, z, sx, sy, sz, c, yaw = 0) => {
        const m = this.meshes[layer], i = used[layer]++;
        q.setFromAxisAngle(up, yaw);
        mtx.compose(new THREE.Vector3(x, y, z), q, new THREE.Vector3(sx, sy, sz));
        m.setColorAt(i, col.set(c));
        parts.push([m, i, mtx.clone()]);
      };
      put('tile', room.ox + ROOM_W / 2, room.data.look && WATER.has(MH.themeForSector(room.data.look)) ? -0.4 : -0.07, room.oz + ROOM_H / 2, 1, 1, 1, tile);
      if (sea) put('sea', room.ox + ROOM_W / 2, -0.12, room.oz + ROOM_H / 2, 1, 1, 1, 0xffffff);
      for (const [layer, x, z, sx, sy, sz, c] of shapes) put(layer, room.ox + x, 0, room.oz + z, sx, sy, sz, c, (x * 7 + z * 3) % 6.28);
      this.cells.push({ room, level: room.data.level || 0, parts, shown: true });
    }
    for (const f of fills) {
      const ox = f.cx * ROOM_W, oz = f.cy * ROOM_H;
      const tile = [], shapes = [];
      let parts = tile;
      const put = (layer, x, y, z, sx, sy, sz, c, yaw = 0) => {
        const m = this.meshes[layer], i = used[layer]++;
        q.setFromAxisAngle(up, yaw);
        mtx.compose(new THREE.Vector3(x, y, z), q, new THREE.Vector3(sx, sy, sz));
        m.setColorAt(i, col.set(c));
        parts.push([m, i, mtx.clone()]);
      };
      // (under any built room's own land and water: terrain.js fillerLand lies at 0 and -0.12)
      put('tile', ox + ROOM_W / 2, f.kind === 'water' ? -0.4 : -0.13, oz + ROOM_H / 2, 1, 1, 1, f.tile);
      if (f.kind === 'water') put('sea', ox + ROOM_W / 2, -0.12, oz + ROOM_H / 2, 1, 1, 1, 0xffffff);
      parts = shapes;
      for (const [layer, x, z, sx, sy, sz, c] of f.shapes) put(layer, ox + x, 0, oz + z, sx, sy, sz, c, (x * 7 + z * 3) % 6.28);
      this.fills.push({ cx: f.cx, cy: f.cy, level: f.level, tile, shapes, shown: [true, true] });
    }
    for (const m of Object.values(this.meshes)) if (m.instanceColor) m.instanceColor.needsUpdate = true;
    for (const c of this.cells) this.show(c, false);
    for (const f of this.fills) this.showFill(f, false, false);
    zone.group.add(this.group);
    this.skip = null;            // (room) => true: never shown (a neighbour's rooms over our own)
    this.horizon = horizon ? makeHorizon() : null;
    if (this.horizon) zone.group.add(this.horizon);
    this._clock = 0;
    this._key = '';
  }

  hasCell(cx, cy) { return this.cellSet.has(`${cx},${cy}`); }

  // a filler cell: its ground, and what stands on it (not where a built room's own land lies)
  showFill(f, tile, shapes) {
    for (const [k, on, parts] of [[0, tile, f.tile], [1, shapes, f.shapes]]) {
      if (f.shown[k] === on) continue;
      f.shown[k] = on;
      for (const [m, i, mtx] of parts) { m.setMatrixAt(i, on ? mtx : ZERO); m.instanceMatrix.needsUpdate = true; }
    }
  }

  show(c, on) {
    if (c.shown === on) return;
    c.shown = on;
    for (const [m, i, mtx] of c.parts) {
      m.setMatrixAt(i, on ? mtx : ZERO);
      m.instanceMatrix.needsUpdate = true;
    }
  }

  // which stand-ins show: the rooms on the hero's level within reach, save those built and drawn
  update(dt, hero, level, fogColor) {
    const cx = Math.floor(hero.x / ROOM_W), cy = Math.floor(hero.z / ROOM_H);
    const key = `${cx},${cy},${level},${this.range}`;
    if ((this._clock -= dt) <= 0 || key !== this._key) {
      this._clock = 0.5;
      this._key = key;
      for (const c of this.cells) {
        const r = c.room;
        const far = Math.max(Math.abs(r.cx - cx), Math.abs(r.cy - cy));
        const drawn = r.built && r.built.group.visible;
        this.show(c, c.level === level && far <= this.range && !drawn && !(this.skip && this.skip(r)));
      }
      const cells = this.zone.cells;
      const drawnAt = (x, y) => { const r = cells && cells.get(`${x},${y}`); return !!(r && r.built && r.built.group.visible); };
      for (const f of this.fills) {
        const on = f.level === level && Math.max(Math.abs(f.cx - cx), Math.abs(f.cy - cy)) <= this.range && !(this.taken && this.taken(f.cx, f.cy));
        let near = false;
        if (on) for (let dy = -1; dy <= 1 && !near; dy++) for (let dx = -1; dx <= 1; dx++) if (drawnAt(f.cx + dx, f.cy + dy)) { near = true; break; }
        this.showFill(f, on, on && !near);
      }
    }
    const h = this.horizon;
    if (!h) return;
    h.visible = this.outdoors;
    if (h.visible) {
      h.position.set(hero.x, -3, hero.z);
      h.scale.y = this.sea ? 0.12 : 1;     // at sea the far hills lie down into a horizon line
      if (fogColor) h.material.color.copy(fogColor).multiplyScalar(0.78);
    }
  }

  dispose() {
    for (const m of Object.values(this.meshes)) { m.geometry.dispose(); m.dispose(); }
    this.zone.group.remove(this.group);
    if (this.horizon) { this.horizon.geometry.dispose(); this.zone.group.remove(this.horizon); }
  }
}

const ZERO = new THREE.Matrix4().makeScale(0, 0, 0);

// The zone's empty cells within FILL_REACH of its rooms, each with the kind of country it is: the
// nearest room's (edges.js fillKind), the cell past a water room's land side counting as land.
export function fillerPlan(zone) {
  const themeOf = s => MH.themeForSector(String(s || ''));
  const src = new Map();       // 'x,y' -> {kind, theme, level}
  for (const room of zone.rooms.values()) {
    const theme = themeOf(room.data.look || room.data.sector);
    const kind = farKind(theme);
    src.set(`${room.cx},${room.cy}`, kind === 'none' || kind === 'roof' ? null : { kind, theme, level: room.data.level || 0 });
  }
  const shore = new Map();     // the cell past a water room's land side: land
  for (const room of zone.rooms.values()) {
    for (const side of Object.keys(landSides(room, zone, themeOf))) {
      const [dx, dy] = SIDES[side], k = `${room.cx + dx},${room.cy + dy}`;
      if (!src.has(k)) shore.set(k, { kind: 'field', theme: 'field', level: room.data.level || 0 });
    }
  }
  const at = (x, y) => { const k = `${x},${y}`; return src.has(k) ? src.get(k) : shore.get(k) || null; };
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const room of zone.rooms.values()) {
    x0 = Math.min(x0, room.cx); x1 = Math.max(x1, room.cx); y0 = Math.min(y0, room.cy); y1 = Math.max(y1, room.cy);
  }
  const out = [];
  for (let y = y0 - FILL_REACH; y <= y1 + FILL_REACH; y++) for (let x = x0 - FILL_REACH; x <= x1 + FILL_REACH; x++) {
    if (src.has(`${x},${y}`)) continue;
    const own = shore.get(`${x},${y}`);
    const f = own ? { src: own } : fillKind(at, x, y, FILL_REACH);
    if (!f || !f.src) continue;
    out.push({ cx: x, cy: y, kind: f.src.kind, theme: f.src.theme, level: f.src.level });
  }
  return out;
}

// a ring of far hills round the hero: a band whose top rises and falls, in the haze's colour
// (no fog on it: it is the haze), past the fog's edge
function makeHorizon() {
  const R = 175, segs = 96;
  const geo = new THREE.CylinderGeometry(R, R, 1, segs, 1, true);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const a = Math.atan2(pos.getZ(i), pos.getX(i));
    if (pos.getY(i) > 0) {
      const hgt = 10 + 7 * Math.sin(a * 3 + 1.3) + 5 * Math.sin(a * 7 + 0.4) + 3 * Math.sin(a * 13 + 2.1);
      pos.setY(i, hgt);
    } else pos.setY(i, -2);
  }
  geo.computeVertexNormals();
  const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: 0x8fa0b0, fog: false, side: THREE.DoubleSide }));
  m.name = 'horizon';
  m.frustumCulled = false;
  m.renderOrder = -1;
  m.visible = false;
  return m;
}
