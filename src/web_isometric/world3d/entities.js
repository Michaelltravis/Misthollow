// Monsters, NPCs and other players around the hero, from the near-mode map payload
// (`nearby` rooms, every mob with a stable id). Each stands on one of its room's spawn
// slots; when the server moves it to another room it walks there instead of popping.
// Which body each creature gets is decided in looks.js.
import * as THREE from 'three';
import { spawnCharacter, spawnMob, spawnBody, bodyIndexReady } from './assets.js';
import { mountRider } from './steed.js';
import { spawnDressed, dress } from './equip.js';
import { creatureLook, hashStr, npcDress } from './looks.js';
import { makeProc, makeProp } from './proc.js';
import { poseFor, postureChange } from './posture.js';
import { makeKin } from './kin.js';
import { isHostile, conOf, shownName } from './targeting.js';
import { deathStyle, remains, fallOver, nameKey } from './corpse.js';
import { plateAuras } from './hud/buffs.js';
import { abilityIcon } from './hud/icons.js';

export const CLASS_MODEL = {
  warrior: ['barbarian'], paladin: ['knight'], cleric: ['knight', 0xfff0d0], mage: ['mage'],
  necromancer: ['mage', 0x9a7ab8], thief: ['rogue'], assassin: ['rogue_hooded', 0x8a8a9a],
  ranger: ['rogue_hooded', 0xb8d8a8], bard: ['rogue', 0xe0b8e0],
};
export function classModel(cls) {
  const [model, tint] = CLASS_MODEL[String(cls || '').toLowerCase()] || ['knight'];
  return { model, tint };
}

// creature bodies: each kind its own from the kit (default), or the classic shared models
export function kinBodies() {
  try { return localStorage.getItem('mh3d_bodies') !== 'classic'; } catch (_) { return true; }
}

// the body for a look (looks.js): a creature model, a procedural body, a kit prop or a person
const noBodies = () => typeof location !== 'undefined' && /[?&]nobodies\b/.test(location.search || '');
export function spawnLook(look, { kits = null, seed = 0 } = {}) {
  const b = look.beast;
  if (!b) return spawnCharacter(look.model, { tint: look.tint, scale: look.scale, loadout: look.loadout, flat: look.flat });
  // a body made in Blender for this kind (art3d/bodies), when there is one; else as below
  // (?nobodies shows what it replaced, to compare)
  if (b.body && !noBodies()) {
    const rest = { ...look, beast: { ...b, body: null } };
    return bodyIndexReady().then(ix => (ix[b.body] ? spawnBody(b.body, { height: b.h, tint: b.tint }) : spawnLook(rest, { kits, seed })))
      .catch(() => spawnLook(rest, { kits, seed }));
  }
  // its own body from the creature kit (kin.js), unless the player chose the classic models
  if (b.kin && kinBodies() && !b.prefer) return Promise.resolve(makeKin(b.kin, { height: b.h }));
  if (b.proc) return Promise.resolve(makeProc(b.proc, { height: b.h, tint: b.tint, seed }));
  if (b.prop) {
    const model = kits && kits[b.prop[0]] && kits[b.prop[0]].get(b.prop[1]);
    return Promise.resolve(model ? makeProp(model, { size: b.h, tint: b.tint }) : makeProc('slime', { height: 0.8, seed }));
  }
  return spawnMob(b.mob, { height: b.h, tint: b.tint });
}

// how high above its feet a creature's nameplate floats
function plateHeight(e) {
  const box = new THREE.Box3().setFromObject(e.root);
  const top = box.max.y - e.root.position.y;
  return Math.max(0.9, Math.min(4, isFinite(top) ? top + 0.35 : 2.75));
}

// a death that is not a fall, played out on the body over its last two seconds: a spirit fades
// and rises, a slime swells and pops, a thing of stone or ice is gone in a blink (its shards fly:
// main.js onDeath), a creature of fire chars, glows and fades to ash
const ASH = new THREE.Color(0x1a1412);
function dyingAs(d, dt) {
  d.t += dt;
  const root = d.e.root;
  if (!d.mats) {
    d.mats = [];
    root.traverse(o => {
      if (!o.isMesh || !o.material) return;
      const one = m => { const c = m.clone(); c.transparent = true; d.mats.push(c); return c; };
      o.material = Array.isArray(o.material) ? o.material.map(one) : one(o.material);
    });
  }
  if (d.style === 'dissolve') {
    const k = Math.max(0, 1 - d.t / 1.5);
    for (const m of d.mats) m.opacity = k;
    root.position.y += dt * 0.4;
    if (k <= 0) root.visible = false;
  } else if (d.style === 'burst') {
    if (d.t < 0.22) root.scale.setScalar(d.scale * (1 + d.t * 1.6));
    else root.visible = false;
  } else if (d.style === 'shatter') {
    if (d.t > 0.06) root.visible = false;
  } else if (d.style === 'burn') {
    const k = Math.min(1, d.t / 1.1);
    for (const m of d.mats) {
      if (m.color) m.color.lerp(ASH, Math.min(1, dt * 2.5));
      if (m.emissive) { m.emissive.setRGB(1, 0.32, 0.05); m.emissiveIntensity = (1 - k) * 0.9; }
      if (d.t > 1.3) m.opacity = Math.max(0, 1 - (d.t - 1.3) / 0.8);
    }
  }
}

export class Entities {
  constructor(engine, plates, kits = null) {
    this.pullWindow = 0;         // until when a creature changing rooms may be one the hero pulled
    this.engine = engine;
    this.plates = plates;          // DOM container for nameplates
    this.kits = kits;              // static models, for creatures that are props (a mimic)
    this.zone = null;
    this.list = new Map();         // key -> entity
    this.target = null;            // key of the selected entity
    this.dying = [];               // fallen creatures, removed after their death animation
    this.vanished = [];            // gone from this payload: cleared next frame, unless its corpse claims it
    this.hero = null;              // hero position (combat facing)
    this.iconClass = '';           // the hero's class: a spell's icon here as on their buff bar
    this._v = new THREE.Vector3();
  }

  // the buffs and debuffs on someone, as small icons under their name (map_system._auras): the
  // harmful ringed red, each darkening as it wears off. Redrawn only when they change.
  paintAuras(e) {
    const el = e.plate && e.plate.querySelector('.auras');
    if (!el) return;
    const list = plateAuras(e.data.auras);
    const sig = list.map(a => `${a.id}:${a.bad ? 1 : 0}:${a.frac.toFixed(2)}`).join('|') + '/' + this.iconClass;
    if (sig === e._auraSig) return;
    e._auraSig = sig;
    el.replaceChildren(...list.map(a => {
      const d = document.createElement('i');
      d.className = a.bad ? 'au bad' : 'au';
      d.style.setProperty('--left', a.frac);
      d.title = `${a.label}${a.secs != null ? ` · ${a.secs >= 60 ? `${Math.round(a.secs / 60)} min` : `${a.secs} s`}` : ''}`;
      const img = document.createElement('img');
      img.alt = '';
      img.src = abilityIcon(a.id, this.iconClass, { type: 'spell', size: 40 });
      d.appendChild(img);
      return d;
    }));
  }

  setZone(zone) {
    for (const e of this.list.values()) this.remove(e, true);
    this.list.clear();
    this.zone = zone;
  }

  slot(roomVnum, key) {
    const room = this.zone && this.zone.rooms.get(roomVnum);
    if (!room) return null;
    const L = this.zone.layoutOf(room);
    const h = hashStr(key);
    const s = L.spawnSlots[h % L.spawnSlots.length];
    const jx = ((h >>> 8) % 100) / 100 - 0.5, jz = ((h >>> 16) % 100) / 100 - 0.5;
    return new THREE.Vector3(room.ox + s.x / 16 + jx * 0.8, 0, room.oz + s.y / 16 + jz * 0.8);
  }

  // a server position (room-local metres) for a creature in a fight: walk it there
  place(e, m) {
    if (m.x == null || m.z == null || !this.zone) return;
    const room = this.zone.rooms.get(e.vnum);
    if (!room) return;
    const goal = new THREE.Vector3(room.ox + m.x, 0, room.oz + m.z);
    if (!e.root || e.root.position.distanceTo(goal) > 0.15) { e.goal = goal; e.then = null; }
  }

  // a creature or player changed rooms: walk there if the rooms open onto each other, else
  // snap there (stairs, a far passage, recall, a portal) with a puff of dust. `at` (room metres
  // the server gave: a creature in a fight, one pulled in from next door, reach.py) is where it
  // goes; it runs there, across the edge, never appearing at a spawn spot first
  moveTo(e, vnum, at = null) {
    const from = this.zone.rooms.get(e.vnum), to = this.zone.rooms.get(vnum);
    e.vnum = vnum;
    const known = to && at && at.x != null && at.z != null;
    e.goal = known ? new THREE.Vector3(to.ox + at.x, 0, to.oz + at.z) : this.slot(vnum, e.key);
    e.rush = !!known;
    const joined = from && to && this.zone.openDir(from, to);
    // pulled in by the hero's shot or spell (reach.py): it stays where it stood until the blow
    // lands on it (combat.js knows when: the projectile's flight to its body), then charges
    const now = performance.now();
    if (known && joined && e.kind === 'mob' && now < this.pullWindow) {
      if (e.landAt && e.landAt > now - 250) { e.holdUntil = e.landAt; e.holdGuess = false; }
      else { e.holdUntil = now + 1800; e.holdGuess = true; }
      e.pulledAt = now;
    }
    // running in from next door (pulled, or seeing the hero across the open land: reach.py):
    // a snarl and a kick of dust as it sets off (main.js onCharge)
    if (known && joined && e.kind === 'mob') e.charging = true;
    if (e.root && e.goal && (!joined || e.root.position.distanceTo(e.goal) > 60)) {
      if (this.onSnap) this.onSnap(e.root.position.clone(), e.goal.clone());
      e.root.position.copy(e.goal).setY(e.root.position.y);
      e.goal = null;
      e.then = null;
      return;
    }
    // a wanderer (no place from the server) goes through the opening between the two rooms,
    // the middle of their shared side, then on to its spot: not through the wall between
    e.then = null;
    if (!known && joined && e.root && e.goal) {
      const [dx, dz] = { north: [0, -1], south: [0, 1], east: [1, 0], west: [-1, 0] }[joined] || [0, 0];
      const W = to.ox - from.ox || 24, H = to.oz - from.oz || 15;
      const gate = new THREE.Vector3(from.ox + (dx ? (dx > 0 ? Math.abs(W) : 0) : Math.abs(W) / 2), 0,
        from.oz + (dz ? (dz > 0 ? Math.abs(H) : 0) : Math.abs(H) / 2));
      if (dx || dz) { e.then = e.goal; e.goal = gate; }
    }
  }

  // the hero just loosed something that may pull a creature over from next door
  expectPull(ms = 2500) { this.pullWindow = performance.now() + ms; }
  // when a blow aimed at this creature lands (combat.js): one waiting to be pulled waits for it
  landing(key, at) {
    const e = this.list.get(key);
    if (!e) return;
    const now = performance.now();
    e.landAt = at;
    if (!(e.holdUntil > now)) return;
    // (the first blow to land on it frees it: two in flight, the sooner wins)
    e.holdUntil = e.holdGuess ? at : Math.min(e.holdUntil, at);
    e.holdGuess = false;
  }

  // another web player's position, relayed by the server: their hero follows it
  presence({ name, vnum, x, z }) {
    const e = name && this.list.get(`p${name}`);
    if (!e || !this.zone || !this.zone.rooms.get(vnum)) return;   // not drawn yet: the next payload brings them
    if (e.vnum !== vnum) this.moveTo(e, vnum);
    e.data.x = x; e.data.z = z;
    this.place(e, e.data);
  }

  // another player changed rooms some other way (recall, a portal, following a leader)
  playerMoved({ name, to }) {
    const e = this.list.get(`p${name}`);
    if (!e || !this.zone) return;
    if (!this.zone.rooms.get(to)) { this.remove(e, true); return; }   // out of this zone: gone from view
    if (e.vnum !== to) this.moveTo(e, to);
  }

  // everyone drawn in what they wear (adorn.js decides who shows more)
  *dressed() {
    for (const e of this.list.values()) if (e.actor && e.actor.gear) yield e.actor;
  }

  // everyone with a spell on them that shows (wards.js): [actor, ward keys]
  *warded() {
    for (const e of this.list.values()) if (e.actor && e.data && e.data.wards && e.data.wards.length) yield [e.actor, e.data.wards];
  }

  // another player put on or took off gear (the server's 'look' relay): re-dress them
  look({ name, look }) {
    const e = name && this.list.get(`p${name}`);
    if (!e || !look) return;
    e.data.look = look;
    if (e.actor) dress(e.actor, look, e.data.char_class);
  }

  // payload.nearby: [{vnum, mobs, players, doors, items}]
  sync(payload, selfName) {
    // a payload without `nearby` (an older /state reply) says nothing about who is around:
    // keep what we have instead of clearing the world
    if (!this.zone || !payload || !Array.isArray(payload.nearby)) return;
    const want = new Map();
    for (const r of payload.nearby || []) {
      const room = this.zone.rooms.get(r.vnum);
      if (!room) continue;
      for (const [dir, info] of Object.entries(r.doors || {})) this.zone.setDoor(room, dir, info);
      for (const m of r.mobs || []) want.set(`m${m.id}`, { kind: 'mob', data: m, vnum: r.vnum });
      for (const p of r.players || []) if (p.name !== selfName) want.set(`p${p.name}`, { kind: 'player', data: p, vnum: r.vnum });
    }
    // (one just pulled in from next door that a single payload leaves out, alive as far as we
    // know, is kept a moment: dropping it would make it fall, then rebuild it at its new spot)
    const now = performance.now();
    for (const [key, e] of this.list) {
      if (want.has(key)) { e.missing = 0; continue; }
      if (e.pulledAt && now - e.pulledAt < 4000 && !(e.data.maxHp && e.data.hp <= 0)) {
        e.missing = e.missing || now;
        if (now - e.missing < 1500) continue;
      }
      this.remove(e);
    }
    for (const [key, w] of want) {
      const e = this.list.get(key);
      if (!e) { this.create(key, w); continue; }
      e.data = w.data;
      if (e.kind === 'player' && e.actor && w.data.look) dress(e.actor, w.data.look, w.data.char_class);
      if (e.kind === 'player' && e.actor) this.posture(e, w.data.position);
      // another player on their mount (steed.js)
      if (e.kind === 'player' && e.actor) { e.riding = mountRider(e.actor, w.data.mount || null, e.riding || null); e.plateY = 0; }
      // a dressed person whose gear changed (disarmed, or picked something up)
      if (e.kind === 'mob' && e.actor && e.actor.gear && w.data.look) {
        const npc = npcDress(w.data, e.look);
        if (npc) dress(e.actor, npc.look, npc.cls);
      }
      this.markHostile(e);
      this.paintAuras(e);
      if (e.vnum !== w.vnum) this.moveTo(e, w.vnum, w.data);
      else this.place(e, w.data);
    }
  }

  // per-round vitals for the hero's room (combat_update)
  combat(payload) {
    for (const m of payload.mobs || []) {
      const e = m.id != null ? this.list.get(`m${m.id}`) : null;
      if (!e) continue;
      Object.assign(e.data, m);
      this.paintAuras(e);
      // (one that came in from next door this round: its room changes here, before the map does)
      if (payload.vnum != null && e.vnum !== payload.vnum && this.zone && this.zone.rooms.get(payload.vnum)) this.moveTo(e, payload.vnum, m);
      else this.place(e, m);
      if (m.fighting && e.actor && e.root && this.hero) {
        e.root.rotation.y = Math.atan2(this.hero.x - e.root.position.x, this.hero.z - e.root.position.z);
        e.actor.once(['1H_Melee_Attack_Chop', '1H_Melee_Attack_Slice_Diagonal', '1H_Melee_Attack_Stab'][(hashStr(e.key) + Date.now()) % 3], 0.08, 1.1);
      }
    }
  }

  create(key, w) {
    // where the server says it stands (a web player, a creature in a fight), else a spawn slot
    const room = this.zone && this.zone.rooms.get(w.vnum);
    const at = room && w.data.x != null && w.data.z != null ? new THREE.Vector3(room.ox + w.data.x, 0, room.oz + w.data.z) : this.slot(w.vnum, key);
    if (!at) return;
    const e = { key, kind: w.kind, data: w.data, vnum: w.vnum, root: null, actor: null, goal: null, alive: true };
    this.list.set(key, e);
    e.plate = document.createElement('div');
    e.plate.className = 'plate ' + (w.kind === 'player' ? 'pl' : isHostile(w) ? 'hostile' : (w.data.shopkeeper || w.data.trainer) ? 'npc' : 'neutral');
    e.plate.innerHTML = '<span class="row"><span class="lv"></span><span class="nm"></span></span><i class="hp"><b></b></i><span class="auras"></span>';
    e.plate.querySelector('.nm').textContent = shownName(w.data, w.kind);
    if (w.kind === 'mob' && w.data.level) e.plate.querySelector('.lv').textContent = w.data.level;
    if (w.data.boss) e.plate.classList.add('boss');
    // an elite (silver) or a sub-boss (gold): a zone's ranks (population.py)
    if (!w.data.boss && (w.data.rank === 'elite' || w.data.rank === 'sub-boss')) e.plate.classList.add(w.data.rank === 'elite' ? 'elite' : 'subboss');
    this.plates.appendChild(e.plate);
    this.paintAuras(e);
    // another player is dressed in what they wear (equip.js); a creature gets its body from
    // looks.js, and a person their zone gave gear to wears it as a player would
    const isPlayer = w.kind === 'player';
    const look = isPlayer ? {} : creatureLook(w.data);
    e.look = look;
    e.fly = (look.beast ? look.beast.fly : look.fly) || 0;
    e.still = !!look.still;        // a statue: no breathing while it stands guard
    (isPlayer ? spawnDressed(w.data.look, w.data.char_class) : this.body(w.data, key, look)).then(actor => {
      if (!e.alive) return;
      e.actor = actor;
      e.root = actor.root;
      e.root.position.copy(at);
      e.root.rotation.y = (hashStr(key) % 628) / 100;
      // (a player already resting or asleep when they come into sight is drawn so at once)
      e.position = isPlayer ? w.data.position || 'standing' : 'standing';
      e.pose = isPlayer && poseFor(e.position) ? poseFor(e.position).loop : null;
      actor.play(e.pose || (isHostile(w) ? 'Idle_Combat' : actor.idle || 'Idle'), 0, e.still ? 0 : 0.85 + (hashStr(key) % 30) / 100);
      if (isPlayer && w.data.mount) e.riding = mountRider(actor, w.data.mount, null);
      this.engine.scene.add(e.root);
    }).catch(() => {});
  }

  // another player rests, sleeps or gets up (payload position): they sit down or lie down once,
  // then hold it (update: poseDue)
  posture(e, position) {
    const ch = postureChange(e.position || 'standing', position || 'standing');
    e.position = position || 'standing';
    if (!ch) return;
    e.pose = ch.loop;
    const d = ch.once && !e.riding ? e.actor.once(ch.once, 0.2) : 0;
    e.poseDue = performance.now() + d * 900 + 1;
  }

  // a creature's body: its zone's gear on a person they dressed, else the body looks.js gives it
  body(data, key, look = creatureLook(data)) {
    const npc = npcDress(data, look);
    return npc ? spawnDressed(npc.look, npc.cls, { scale: npc.scale }) : spawnLook(look, { kits: this.kits, seed: hashStr(key) });
  }

  // the body of a creature that just fell, for its corpse to keep (loot.js): it stays where it
  // fell instead of being cleared away. Matched by name ("corpse of the goblin" -> the goblin).
  // One that simply vanished (killed in one blow, never seen hurt) and left a corpse in the same
  // payload died too: it falls now.
  claimFallen(victim) {
    const want = nameKey(victim);
    const i = this.dying.findIndex(d => nameKey(d.e.data && d.e.data.name) === want);
    if (i >= 0) {
      const d = this.dying[i];
      // one that did not fall leaves its remains, and goes on fading, bursting or burning away
      if (d.style && d.style !== 'fall') { d.claimed = true; return { root: remains(d.style, d.e.root.position.clone().setY(0)), fall: null }; }
      this.dying.splice(i, 1);
      return { root: d.e.root, fall: d.fall, actor: d.e.actor };
    }
    const j = this.vanished.findIndex(e => e.actor && nameKey(e.data && e.data.name) === want);
    if (j < 0) return null;
    const [e] = this.vanished.splice(j, 1);
    return { root: e.root, actor: e.actor, fall: fallOver(e.actor, { ground: 0, side: hashStr(e.key) % 2 ? 1 : -1 }) };
  }

  remove(e, now) {
    e.alive = false;
    if (e.plate) e.plate.remove();
    if (this.target === e.key) this.setTarget(null);
    this.list.delete(e.key);
    if (!e.root) return;
    // a creature that was fighting or out of health died: let it fall, then clear it away
    const died = !now && e.actor && e.kind === 'mob' && ((e.data.maxHp && e.data.hp <= 0) || e.data.fighting);
    if (!died) {
      if (now) this.engine.scene.remove(e.root);
      else this.vanished.push(e);
      return;
    }
    // it dies as what it is (corpse.js deathStyle): falls and lies there, or fades, bursts, burns
    // or shatters; unless its corpse claims the body (or its remains), it is cleared away
    const style = deathStyle(e.data.name, e.data.short, e.data.body);
    const fall = style === 'fall' || style === 'burn' ? fallOver(e.actor, { ground: 0, side: hashStr(e.key) % 2 ? 1 : -1 }) : null;
    this.dying.push({ e, left: 2.2, fall, style, t: 0, scale: e.root.scale.x });
    if (this.onDeath) this.onDeath(e, style);
  }

  // a heavy blow or a crit shoves a creature back from whoever struck it (`by`: where they stand)
  knock(e, by, dist = 0.4) {
    if (!e || !e.root || e.dying || e.alive === false) return;
    const dx = e.root.position.x - by.x, dz = e.root.position.z - by.z, d = Math.hypot(dx, dz) || 1;
    const T = 0.16;
    e.knock = { x: dx / d * dist / T, z: dz / d * dist / T, t: T };
  }

  // a creature that turns on you gets a hostile (red) nameplate
  markHostile(e) {
    if (!e || !e.plate || e.kind !== 'mob') return;
    const h = isHostile(e);
    e.plate.classList.toggle('hostile', h);
    if (h) e.plate.classList.remove('neutral');
  }

  // byHand: the player chose it (a click, Tab): auto-targeting leaves it alone a moment
  setTarget(key, { byHand = false } = {}) {
    const prev = this.target && this.list.get(this.target);
    if (prev && prev.plate) prev.plate.classList.remove('targeted');
    this.target = key;
    const e = key && this.list.get(key);
    if (e && byHand) e.pickedAt = Date.now();
    if (e && e.plate) e.plate.classList.add('targeted');
    MH.bus.emit(e ? 'target.set' : 'target.clear', e ? { key, kind: e.kind, ...e.data, vnum: e.vnum } : null);
  }

  get targeted() { return this.target ? this.list.get(this.target) || null : null; }

  // nearest entity to a screen point (page px), for click-to-target
  pick(px, py, maxPx = 42) {
    const cam = this.engine.camera, cv = this.engine.renderer.domElement.getBoundingClientRect();
    let best = null, bestD = maxPx;
    for (const e of this.list.values()) {
      if (!e.root) continue;
      this._v.copy(e.root.position).setY(1.1).project(cam);
      if (this._v.z > 1) continue;
      const sx = cv.left + (this._v.x + 1) / 2 * cv.width, sy = cv.top + (1 - this._v.y) / 2 * cv.height;
      const d = Math.hypot(sx - px, sy - py);
      if (d < bestD) { bestD = d; best = e; }
    }
    return best;
  }

  update(dt, t, hero) {
    this.hero = hero;
    for (const e of this.vanished) this.engine.scene.remove(e.root);
    this.vanished.length = 0;
    for (let i = this.dying.length - 1; i >= 0; i--) {
      const d = this.dying[i];
      if (d.fall) d.fall.update(dt);
      if (d.style && d.style !== 'fall') dyingAs(d, dt);
      if ((d.left -= dt) <= 0) { this.engine.scene.remove(d.e.root); this.dying.splice(i, 1); for (const m of d.mats || []) m.dispose(); }
    }
    for (const e of this.list.values()) {
      if (!e.root) continue;
      // walking to a new room's spot (other players keep up with where they really are:
      // the further behind, the faster they run)
      // knocked back by a heavy blow: a short shove, easing off
      if (e.knock) {
        const k = Math.min(dt, e.knock.t);
        e.root.position.x += e.knock.x * k; e.root.position.z += e.knock.z * k;
        if ((e.knock.t -= dt) <= 0) e.knock = null;
      }
      const held = e.holdUntil && performance.now() < e.holdUntil;
      if (!held && e.holdUntil) e.holdUntil = 0;
      if (e.charging && !held) { e.charging = false; if (e.goal && this.onCharge) this.onCharge(e); }
      if (e.goal && !held) {
        const p = e.root.position, dx = e.goal.x - p.x, dz = e.goal.z - p.z, d = Math.hypot(dx, dz);
        if (d < 0.1 && e.then) { e.goal = e.then; e.then = null; }
        else if (d < 0.1) { e.goal = null; e.rush = false; if (e.actor) e.actor.play(e.riding ? 'Idle' : e.pose || (isHostile(e) ? 'Idle_Combat' : e.actor.idle || 'Idle'), 0.18, e.still ? 0 : 1); }
        else {
          // (a creature charging over from next door runs)
          const speed = e.kind === 'player' ? Math.min(9 * (e.data.speed || 1), Math.max(3.2, d * 4)) : e.rush ? Math.min(7, Math.max(3.2, d * 1.6)) : 3.2;
          const step = Math.min(d, speed * dt);
          p.x += dx / d * step; p.z += dz / d * step;
          e.root.rotation.y = Math.atan2(dx, dz);
          if (e.actor) e.actor.play(e.riding ? 'Idle' : speed > 4.5 ? 'Running_A' : 'Walking_A', 0.15, 1.1);
        }
      }
      // sat down or got up (posture): once that clip is through, hold the pose (or stand idle)
      if (e.actor && e.poseDue && !e.goal && performance.now() >= e.poseDue) {
        e.poseDue = 0;
        e.actor.play(e.riding ? 'Idle' : e.pose || (isHostile(e) ? 'Idle_Combat' : e.actor.idle || 'Idle'), 0.35);
      }
      if (e.actor) e.actor.update(dt);
      if (e.riding) { e.riding.steed.update(dt, !!e.goal, 1.5); e.riding.pose(t, !!e.goal); }
      if (e.fly) e.root.position.y = e.fly + Math.sin(t * 2.1 + (hashStr(e.key) % 9)) * 0.12;
    }
  }

  // nameplates, once the camera is placed for this frame (engine late tick)
  layoutPlates(hero) {
    if (!hero) return;
    const cam = this.engine.camera, cv = this.engine.renderer.domElement;
    const w = cv.clientWidth, h = cv.clientHeight;
    for (const e of this.list.values()) {
      // (no body yet, its model still loading: its plate waits hidden, not in the corner)
      if (!e.root) { if (e.plate) e.plate.style.display = 'none'; continue; }
      const dist = e.root.position.distanceTo(hero);
      // in the dark only what the hero can see has a name over it (main.js sets sightRadius)
      const show = (dist < 26 && !(this.sightRadius && dist > this.sightRadius)) || this.target === e.key;
      if (!show) { e.plate.style.display = 'none'; continue; }
      this._v.copy(e.root.position).setY(e.root.position.y + (e.plateY || (e.plateY = plateHeight(e)))).project(cam);
      if (this._v.z > 1 || Math.abs(this._v.x) > 1.1 || Math.abs(this._v.y) > 1.1) { e.plate.style.display = 'none'; continue; }
      e.plate.style.display = '';
      e.plate.style.transform = `translate(${((this._v.x + 1) / 2 * w).toFixed(1)}px, ${((1 - this._v.y) / 2 * h).toFixed(1)}px) translate(-50%, -100%)`;
      const hp = e.data.maxHp ? e.data.hp / e.data.maxHp : 1;
      e.plate.classList.toggle('hurt', hp < 0.999);
      // a creature's level badge in the colour of how dangerous it is to you
      if (e.kind === 'mob' && this.heroLevel && e._conFor !== this.heroLevel) {
        e._conFor = this.heroLevel;
        e.plate.dataset.con = conOf(e.data.level || 1, this.heroLevel).key;
      }
      e.plate.querySelector('.hp b').style.width = `${Math.max(0, Math.min(1, hp)) * 100}%`;
      e.plate.style.opacity = this.target === e.key ? 1 : Math.max(0.25, Math.min(1, (28 - dist) / 8));
    }
  }
}
