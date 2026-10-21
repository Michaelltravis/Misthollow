// A whole zone as one continuous space (from the server's /zonemap). Room (cx, cy) covers
// x in [cx*24, cx*24+24), z in [cy*15, cy*15+15). Rooms are laid out lazily, built as meshes
// near the hero and released far away; walking between rooms is just walking. A step into
// another room is legal only through an 'open' exit (mutual + adjacent, door not closed);
// every other exit is a marked passage that triggers a short hop.
import * as THREE from 'three';
import { buildRoom, ROOM_W, ROOM_H, isIndoor } from './terrain.js';
import { passageSpot, arrivalSpot, wantsPassage } from './passages.js';
import { isDeadly } from './deathlogic.js';
import { FarView } from './far.js';
import { landSides } from './edges.js';

const FLOOR = 0, BLOCK = 1, WATER = 4;
const LIGHTS = 6;
export const REV = { north: 'south', south: 'north', east: 'west', west: 'east', up: 'down', down: 'up' };
const CARD = { north: [0, -1], south: [0, 1], east: [1, 0], west: [-1, 0] };

export async function fetchZonemap(query) {
  const res = await fetch(`/zonemap?${query}`);
  if (!res.ok) throw new Error(`zone map ${query}: ${res.status}`);
  return res.json();
}

export class Zone {
  constructor(engine, kits, zm) {
    this.engine = engine;
    this.kits = kits;
    this.zm = zm;
    this.num = zm.zone;
    this.name = zm.name;
    this.wild = !!zm.wild;       // an opened zone (wilds.py): its outdoor land runs on past its rooms
    this.rooms = new Map();
    this.dared = new Set();     // death traps the hero chose to walk into anyway (E at the edge)
    this.cells = new Map();
    for (const r of zm.rooms) {
      // a way only immortals may take (into the God Rooms) is not drawn: no stairs, no sign
      for (const [d, e] of Object.entries(r.exits)) if (e.imm) delete r.exits[d];
      const room = {
        data: r, vnum: r.vnum, name: r.name, cx: r.cell[0], cy: r.cell[1],
        ox: r.cell[0] * ROOM_W, oz: r.cell[1] * ROOM_H, layout: null, built: null, doors: {},
        zoneRef: this,
      };
      for (const [d, e] of Object.entries(r.exits)) if (e.door) room.doors[d] = { ...e.door };
      this.rooms.set(r.vnum, room);
      this.cells.set(`${room.cx},${room.cy}`, room);
    }
    this.group = new THREE.Group();
    this.group.name = `zone_${this.num}`;
    engine.scene.add(this.group);
    this.lights = [];
    for (let i = 0; i < LIGHTS; i++) {
      const l = new THREE.PointLight(0xff9a48, 0, 9, 1.6);
      l.userData.seed = Math.random() * 100;
      this.group.add(l);
      this.lights.push(l);
    }
    this._lightClock = 0;
    // the rooms past the built ones, drawn cheaply, and the far hills (far.js)
    this.far = new FarView(this);
    // (a filler cell where a zone next door has a room: that zone's stand-in is drawn there)
    this.far.taken = (x, y) => this.ghosts.some(g => g.view.hasCell(x - g.ocx, y - g.ocy));
    // the zones next door, drawn past the border the same way (seamless borders: addGhost)
    this.ghosts = [];
    this._releaseClock = 0;
  }

  // ---- geometry queries ----
  roomAt(x, z) { return this.cells.get(`${Math.floor(x / ROOM_W)},${Math.floor(z / ROOM_H)}`) || null; }
  centre(room) { return new THREE.Vector3(room.ox + ROOM_W / 2, 0, room.oz + ROOM_H / 2); }

  layoutOf(room) {
    if (!room.layout) {
      const r = room.data;
      const exits = {};
      // each exit's kind and the look beyond it (two open-joined outdoor rooms share their side)
      for (const [d, e] of Object.entries(r.exits)) {
        const nb = this.rooms.get(e.to);
        exits[d] = { to_room: e.to, kind: e.kind, door: !!e.door, nlook: nb ? (nb.data.look || nb.data.sector) : null };
      }
      room.layout = MH.generateRoomTopDown({
        vnum: r.vnum, name: r.name, description: r.description, sector: r.sector, look: r.look, features: r.features, tone: r.tone, setpiece: r.setpiece,
        flags: r.flags, zone: this.num, exits,
        land: landSides(room, this, MH.themeForSector),     // a water room's sides that are land (edges.js)
      });
    }
    return room.layout;
  }

  // where the hero appears in a room entered on its `side`: a doorway, or beside the stairs
  // or portal that lead back (passages.js: up/down exits are named by direction of travel)
  side(room, side) {
    const s = arrivalSpot(this.layoutOf(room), side || 'none', ROOM_W, ROOM_H);
    return new THREE.Vector3(room.ox + s.x, 0, room.oz + s.z);
  }

  // the doorway gap on a compass side (for walking lanes through shared openings)
  entry(room, fromDir) {
    const L = this.layoutOf(room);
    const e = (fromDir && L.entries[fromDir]) || L.entries.none;
    return new THREE.Vector3(room.ox + e.x / 16, 0, room.oz + e.y / 16);
  }

  tile(room, x, z) {
    const tx = Math.floor(x - room.ox), ty = Math.floor(z - room.oz);
    if (tx < 0 || ty < 0 || tx >= ROOM_W || ty >= ROOM_H) return BLOCK;
    return this.layoutOf(room).grid[ty * ROOM_W + tx];
  }

  openDir(a, b) {
    for (const [d, e] of Object.entries(a.data.exits)) if (e.kind === 'open' && e.to === b.vnum) return d;
    return null;
  }
  doorClosed(room, dir) { const d = room.doors[dir]; return !!(d && d.closed); }
  // a death trap the hero hasn't dared: they stop at its edge (main.js asks)
  deadly(room) { return !!room && isDeadly(room.data.flags) && !this.dared.has(room.vnum); }

  // can the hero's body stand at (x, z), coming from room `from`?
  blocked(x, z, from) {
    const r = this.roomAt(x, z);
    if (!r) return true;
    if (from && r !== from) {
      const d = this.openDir(from, r);
      if (!d || this.doorClosed(from, d) || this.doorClosed(r, REV[d])) return true;
      if (this.deadly(r)) return true;
    }
    const t = this.tile(r, x, z);
    if (t === BLOCK) return true;
    return t === WATER && !this.layoutOf(r).swim;
  }

  // ---- passages: exits that are not a shared opening ----
  // the spots in a room you step onto to take a passage (room-local metres), for the gate
  passageSpots(room) {
    const L = this.layoutOf(room);
    const out = [];
    for (const [d, e] of Object.entries(room.data.exits)) {
      if (e.kind === 'open') continue;
      const s = passageSpot(L, d, ROOM_W, ROOM_H);
      if (s) out.push({ key: d, x: s.x, z: s.z });
    }
    return out;
  }
  passageWorld(room, dir) {
    const s = passageSpot(this.layoutOf(room), dir, ROOM_W, ROOM_H);
    return s ? new THREE.Vector3(room.ox + s.x, 0, room.oz + s.z) : this.centre(room);
  }

  // {dir, exit} when the hero means to take a passage now (passages.js decides what counts:
  // keys moving onto the stairs, or a click path sent to them), {dir, exit, blocked} when they
  // mean to but it can't open ('door': closed; 'combat': fighting), else null
  passageAt(room, p, v, gate, { viaKeys = false, viaPath = false, goal = null, inCombat = false, now = performance.now() } = {}) {
    const L = this.layoutOf(room);
    const lx = p.x - room.ox, lz = p.z - room.oz;
    const speed = Math.hypot(v.x, v.y);
    for (const [d, e] of Object.entries(room.data.exits)) {
      if (e.kind === 'open') continue;
      let want = false;
      if (CARD[d]) {
        const g = L.gaps[d];
        if (!g) continue;
        const [dx, dz] = CARD[d];
        const out = v.x * dx + v.y * dz;              // pushing outward through the gap
        const inSpan = dx ? (lz >= g.y0 && lz <= g.y1 + 1) : (lx >= g.x0 && lx <= g.x1 + 1);
        const nearEdge = dx > 0 ? lx > ROOM_W - 1.25 : dx < 0 ? lx < 1.25 : dz > 0 ? lz > ROOM_H - 1.25 : lz < 1.25;
        want = inSpan && nearEdge && (viaPath ? goal === d : viaKeys && out > 0.5);
      } else {
        const s = passageSpot(L, d, ROOM_W, ROOM_H);
        if (!s) continue;
        const dist = Math.hypot(lx - s.x, lz - s.z);
        const toward = dist > 1e-3 && speed > 1e-3 ? ((s.x - lx) * v.x + (s.z - lz) * v.y) / (dist * speed) : 1;
        want = wantsPassage({ d: dist, speed, toward, viaKeys, viaPath, goal: goal === d });
      }
      if (!want || (gate && !gate.canFire(d, now))) continue;
      if (this.doorClosed(room, d)) return { dir: d, exit: e, blocked: 'door' };
      if (this.deadly(this.rooms.get(e.to))) return { dir: d, exit: e, blocked: 'deadly' };
      if (inCombat) return { dir: d, exit: e, blocked: 'combat' };
      return { dir: d, exit: e };
    }
    return null;
  }

  // stairs and portal tiles: paths walk around them unless they are the destination
  avoidTile(room, tx, ty) {
    const L = this.layoutOf(room);
    const on = t => t && t.x === tx && t.y === ty;
    return on(L.stairsUp) || on(L.stairsDown) || (L.portals || []).some(on);
  }

  // the matching side of a passage in the destination room: the exit that leads back where we
  // came from (the reverse of `dir` when it does), beside its stairs or in its doorway
  arrival(room, fromVnum, dir) {
    const ex = room.data.exits;
    const back = REV[dir];
    let side = back && ex[back] && ex[back].to === fromVnum ? back : null;
    if (!side) side = Object.keys(ex).find(d => ex[d].to === fromVnum) || null;
    return side ? this.side(room, side) : this.centre(room);
  }

  // ---- streaming ----
  build(room) {
    if (room.built) return;
    room.built = buildRoom(this.layoutOf(room), room.ox, room.oz, this.kits, room);
    this.group.add(room.built.group);
  }
  release(room) {
    if (!room.built) return;
    this.group.remove(room.built.group);
    for (const g of room.built.owned || []) g.dispose();
    room.built = null;
  }
  prebuild(room, radius = 1) {
    for (let dy = -radius; dy <= radius; dy++) for (let dx = -radius; dx <= radius; dx++) {
      const r = this.cells.get(`${room.cx + dx},${room.cy + dy}`);
      if (r) this.build(r);
    }
  }

  update(dt, t, hero, vel) {
    const cx = Math.floor(hero.x / ROOM_W), cy = Math.floor(hero.z / ROOM_H);
    // one room per frame within 2 cells, nearest first, ahead of the hero first
    let best = null, bestD = Infinity;
    for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
      const r = this.cells.get(`${cx + dx},${cy + dy}`);
      if (!r || r.built) continue;
      const d = dx * dx + dy * dy - 0.6 * Math.sign(dx * (vel ? vel.x : 0) + dy * (vel ? vel.y : 0));
      if (d < bestD) { bestD = d; best = r; }
    }
    if (best) this.build(best);
    if ((this._releaseClock -= dt) <= 0) {
      this._releaseClock = 1;
      for (const r of this.rooms.values()) {
        if (!r.built) continue;
        const far = Math.max(Math.abs(r.cx - cx), Math.abs(r.cy - cy));
        if (far > 4) this.release(r);
        // kept built for the way back, but not drawn (nor their shadows) past the fog: up to 81
        // rooms were drawn every frame for the few the camera shows
        else r.built.group.visible = far <= 3;
      }
    }
    this.updateLights(dt, t, hero);
    const here = this.roomAt(hero.x, hero.z);
    const level = here ? here.data.level || 0 : 0;
    this.far.update(dt, hero, level, this.engine.scene.fog && this.engine.scene.fog.color);
    for (const g of this.ghosts) {
      g.view.range = this.far.range;
      g.view.update(dt, { x: hero.x - g.ox, z: hero.z - g.oz }, level === g.alevel ? g.blevel : NaN, null);
    }
  }

  // A zone next door, from its map, drawn past the border where its way in says it lies: the
  // room a 'zone' exit leads to sits in the cell beyond the exit's room (ocx, ocy: where its
  // map's (0, 0) falls on ours). Only its stand-ins (far.js), none over our own rooms' ground.
  addGhost(zm, ocx, ocy, alevel, blevel) {
    if (this.ghosts.some(g => g.num === zm.zone) || zm.zone === this.num) return null;
    const group = new THREE.Group();
    group.position.set(ocx * ROOM_W, 0, ocy * ROOM_H);
    this.group.add(group);
    const rooms = new Map();
    for (const r of zm.rooms) {
      rooms.set(r.vnum, { data: r, vnum: r.vnum, cx: r.cell[0], cy: r.cell[1], ox: r.cell[0] * ROOM_W, oz: r.cell[1] * ROOM_H, built: null });
    }
    const view = new FarView({ num: zm.zone, rooms, group }, { horizon: false });
    // (where one of its rooms would stand on one of ours, ours is drawn instead)
    view.skip = r => this.cells.has(`${r.cx + ocx},${r.cy + ocy}`);
    const g = { num: zm.zone, view, group, ocx, ocy, ox: ocx * ROOM_W, oz: ocy * ROOM_H, alevel, blevel };
    this.ghosts.push(g);
    return g;
  }

  updateLights(dt, t, hero) {
    if ((this._lightClock -= dt) <= 0) {
      this._lightClock = 0.25;
      const all = [];
      for (const r of this.rooms.values()) if (r.built) for (const p of r.built.torches) all.push(p);
      all.sort((a, b) => a.distanceToSquared(hero) - b.distanceToSquared(hero));
      this.lights.forEach((l, i) => {
        const p = all[i];
        if (p && p.distanceToSquared(hero) < 30 * 30) { l.position.copy(p); l.userData.on = true; } else l.userData.on = false;
      });
    }
    for (const l of this.lights) {
      const s = l.userData.seed;
      const flick = 0.85 + Math.sin(t * 9.1 + s) * 0.06 + Math.sin(t * 23.7 + s * 2) * 0.05;
      const want = l.userData.on ? 26 * flick : 0;
      l.intensity += (want - l.intensity) * Math.min(1, dt * 8);
    }
  }

  // live door state: map_data's per-viewer view ({state, locked, broken, label, has_key,
  // can_pick, keyless, key_name, rev}) or a 'door' push ({state, locked, broken, label, rev});
  // an older revision than the one we have is ignored
  setDoor(room, dir, info) {
    const d = room.doors[dir];
    if (!d || !info) return;
    if (info.rev != null && d.rev != null && info.rev < d.rev) return;
    if (info.rev != null) d.rev = info.rev;
    d.closed = info.state === 'closed';
    d.locked = !!info.locked;
    d.broken = !!info.broken;
    for (const k of ['label', 'has_key', 'can_pick', 'keyless', 'key_name', 'sealed', 'barricaded']) if (k in info) d[k] = info[k];
    const mesh = room.built && room.built.doors && room.built.doors[dir];
    if (mesh) {
      mesh.userData.setOpen(!d.closed);
      if (mesh.userData.setLocked) mesh.userData.setLocked(d.closed && d.locked);
    }
  }
  doorOf(room, dir) { return room.doors[dir] || null; }

  indoor(room) { return isIndoor(this.layoutOf(room).theme); }

  dispose() {
    for (const r of this.rooms.values()) this.release(r);
    this.far.dispose();
    for (const g of this.ghosts) { g.view.dispose(); this.group.remove(g.group); }
    this.ghosts = [];
    this.engine.scene.remove(this.group);
  }

  // ---- room graph path (for click-to-travel on the minimap) ----
  // Rooms joined by open exits (and, with `passages`, by stairs and other passages in this
  // zone), never through a closed door: walking carries the hero there for real.
  roomPath(from, to, { passages = false } = {}) {
    const prev = new Map([[from.vnum, null]]);
    const q = [from];
    while (q.length) {
      const r = q.shift();
      if (r === to) break;
      for (const [d, e] of Object.entries(r.data.exits)) {
        if (prev.has(e.to) || e.kind === 'zone' || (e.kind !== 'open' && !passages)) continue;
        if (this.doorClosed(r, d)) continue;
        const n = this.rooms.get(e.to);
        if (!n) continue;
        prev.set(e.to, r);
        q.push(n);
      }
    }
    if (!prev.has(to.vnum)) return null;
    const path = [];
    for (let r = to; r; r = prev.get(r.vnum)) path.unshift(r);
    return path;
  }
  // the exit of `a` that leads to `b` (open first)
  linkDir(a, b) {
    return this.openDir(a, b) || Object.keys(a.data.exits).find(d => a.data.exits[d].to === b.vnum) || null;
  }
}
