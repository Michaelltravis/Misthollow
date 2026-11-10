// The spells on a character, shown on them for as long as they last (the cast's flash, fxdirector.js,
// is only the moment it lands). The server lists each one's wards (map_system._wards: the hero's
// in player.wards, everyone else's on their entity), and each ward is drawn as one of a few things:
//   shell  — a glassy bubble round the body (Shield blue, Sanctuary white, Divine Shield gold...)
//   orbit  — little things circling the waist (Armor's runes, Stoneskin's stones, Ice Armor's
//            shards, Fire Shield's flames, Barkskin's leaves; a stun's stars over the head)
//   ring   — a slow ring on the ground (the protections, Beacon, Spirit Link; roots when entangled)
//   motes  — sparks drifting up (Bless gold, Haste yellow, Regenerating green...)
//   hover  — Fly: the body lifted off the ground and bobbing, wind stirring under it
//   fade   — Invisible: the hero drawn faint (only you see yourself)
//   harms  — what holds or hurts the body (harms.js): it glows (a poison green, a burn orange, a
//            frost blue), something rises or falls off it (bubbles, flames, rime, drips, Zzz, sweat,
//            hearts, a hushed word), its animation slows or stops (frozen, held, asleep), a sleeper
//            slumps, the frightened tremble, the blinded wear a dark band over the eyes
// One shell at a time (the strongest), at most two orbits; the hero always, and the nearest few
// others by quality tier.
import * as THREE from 'three';
import { shellMaterial } from './shell.js';
import { emitHarms, HAZE } from './harms.js';

export { HAZE };

export const WARDS = {
  // shells, strongest first (p)
  invulnerable: { shell: 0xffe48a, p: 9 },
  sanctuary: { shell: 0xf2f0ff, p: 8 },
  divine_shield: { shell: 0xffd56a, p: 7 },
  holy_shield: { shell: 0xffe6a0, p: 6 },
  aegis_ward: { shell: 0xffc98a, p: 6 },
  mana_shield: { shell: 0x9a7aff, p: 5 },
  spell_reflect: { shell: 0xbff4ff, p: 4 },
  shielded: { shell: 0x7fb8ff, p: 3 },
  // orbits
  armour_ward: { orbit: 'rune', color: 0xd6e2ff },
  stoneskin: { orbit: 'stone', color: 0x9a9186 },
  ice_armor: { orbit: 'shard', color: 0xaee4ff },
  fire_shield: { orbit: 'flame', color: 0xff8a3a },
  barkskin: { orbit: 'leaf', color: 0x7fb050 },
  stunned: { orbit: 'star', color: 0xffe46a },
  // rings on the ground
  prot_evil: { ring: 0xeaf0ff },
  prot_good: { ring: 0xff6a5a },
  beacon_of_light: { ring: 0xffe9a0 },
  guardian_spirit: { ring: 0xc8f0ff },
  spirit_link: { ring: 0x8ae0ff },
  entangled: { ring: 0x5f9a3a },
  // a rare elite (elites.py): a gold ring under it and gold sparks rising
  elite: { ring: 0xffc24a, motes: 0xffd86a },
  // motes
  bless: { motes: 0xffe9a8 },
  haste: { motes: 0xffd25a, fast: true },
  briskness: { motes: 0xfff0a0, fast: true },
  regenerating: { motes: 0x7ae08a },
  mirror_image: { motes: 0xc8b8ff },
  displacement: { motes: 0xb0a0e8 },
  blink: { motes: 0xd8c8ff },
  shadowform: { motes: 0x5a3a8a, sink: true },
  slow: { motes: 0x8a98b0, sink: true, rate: 0.6 },
  silenced: { motes: 0x9a9a9a, sink: true, fx: 'hush' },
  cursed: { motes: 0x7a3aa8, sink: true, fx: 'curse' },
  weakened: { motes: 0x8a9a5a, sink: true },
  // tracks covered (stealth.py): a faint dust settling about the feet (and no footprints: main.js)
  tracks_covered: { motes: 0x9a8a70, sink: true },
  // harms on the body (harms.js): a glow (the strongest, tp), what comes off it, how it moves
  poisoned: { tint: 0x8cff4a, tp: 2, fx: 'poison' },
  burning: { tint: 0xff3c08, tp: 3, fx: 'burn' },
  frozen: { tint: 0x9fd8ff, tp: 4, fx: 'frost', rate: 0.2, shell: 0xd6f2ff, p: 1 },
  paralyzed: { tint: 0x6a6a72, tp: 5, rate: 0 },
  bleeding: { fx: 'bleed' },
  asleep: { fx: 'zzz', rate: 0.3, slump: true },
  feared: { fx: 'fear', tremble: true, tint: 0x7a9aff, tp: 1 },
  charmed: { fx: 'hearts' },
  blinded: { band: true },
  // the body itself
  fly: { hover: true },
  invisible: { fade: true },
};

// what to draw for a list of ward keys: {shell, orbits: [{kind, color}], rings, motes, hover, fade}
export function wardPlan(keys) {
  const plan = { shell: null, orbits: [], ring: null, motes: [], hover: false, fade: false,
    tint: null, fx: [], rate: 1, restRate: 1, tremble: false, slump: false, band: false };
  let best = -1, tbest = -1;
  for (const k of keys || []) {
    const w = WARDS[k];
    if (!w) continue;
    if (w.shell != null && w.p > best) { best = w.p; plan.shell = w.shell; }
    if (w.orbit && plan.orbits.length < 2 && !plan.orbits.some(o => o.kind === w.orbit)) plan.orbits.push({ kind: w.orbit, color: w.color });
    if (w.ring != null && plan.ring == null) plan.ring = w.ring;
    if (w.motes != null) plan.motes.push({ color: w.motes, fast: !!w.fast, sink: !!w.sink });
    if (w.hover) plan.hover = true;
    if (w.fade) plan.fade = true;
    if (w.tint != null && w.tp > tbest) { tbest = w.tp; plan.tint = w.tint; }
    if (w.fx && !plan.fx.includes(w.fx)) plan.fx.push(w.fx);
    if (w.rate != null) plan.rate = Math.min(plan.rate, w.rate);
    if (w.rate != null && !w.slump) plan.restRate = Math.min(plan.restRate, w.rate);   // (all but sleep's)
    if (w.tremble) plan.tremble = true;
    if (w.slump) plan.slump = true;
    if (w.band) plan.band = true;
  }
  plan.motes = plan.motes.slice(0, 3);
  return plan;
}
export const planKey = keys => [...(keys || [])].filter(k => WARDS[k]).sort().join(',');

const BUDGET = { low: 3, med: 6, high: 10, gallery: 200 };    // others warded besides the hero
const NEAR = 24;
const HOVER = 0.38;                                            // metres off the ground when flying
const _p = new THREE.Vector3();
const _box = new THREE.Box3();

// the things that circle: small and cheap, shared geometry
let GEO = null;
function geos() {
  if (GEO) return GEO;
  GEO = {
    rune: new THREE.OctahedronGeometry(0.075, 0).scale(0.6, 1.3, 0.6),
    stone: new THREE.DodecahedronGeometry(0.085, 0),
    shard: new THREE.OctahedronGeometry(0.07, 0).scale(0.5, 1.8, 0.5),
    leaf: new THREE.CircleGeometry(0.08, 6).scale(0.6, 1.2, 1),
    star: new THREE.OctahedronGeometry(0.06, 0).scale(1, 1, 0.35),
    ring: new THREE.RingGeometry(0.82, 1, 56).rotateX(-Math.PI / 2),
    disc: new THREE.CircleGeometry(1, 40).rotateX(-Math.PI / 2),
  };
  return GEO;
}
const COUNT = { rune: 3, stone: 4, shard: 5, flame: 4, leaf: 5, star: 3 };
// where a body's eyes are, for a blindfold (root-local metres): its head mesh if it has one (the
// big heads of the rigged folk: about two fifths up it), else its head bone, else an upright
// body's top; none for a beast whose head is out in front
function eyeLine(root, h, w) {
  const sy = Math.max(1e-3, root.scale.y || 1);
  let head = null, bone = null;
  root.traverse(o => {
    if (/^ward_/.test(String(o.name))) return;
    if (!head && o.isMesh && /head/i.test(o.name)) head = o;
    if (!bone && o.isBone && /^head/i.test(o.name)) bone = o;
  });
  if (head) {
    const b = new THREE.Box3().setFromObject(head);
    const lo = (b.min.y - root.position.y) / sy, hi = (b.max.y - root.position.y) / sy;
    if (hi > lo) return { y: lo + (hi - lo) * 0.38, r: Math.max(0.12, 0.52 * Math.max(b.max.x - b.min.x, b.max.z - b.min.z) / sy), bone };
  }
  if (bone && h > w * 0.9) {
    const v = new THREE.Vector3();
    bone.getWorldPosition(v);
    const by = (v.y - root.position.y) / sy;
    return { y: by + 0.4 * (by / 1.21), r: 0.6 * (by / 1.21), bone };
  }
  return h > w * 1.15 ? { y: h * 0.86, r: Math.max(0.13, w * 0.24) } : null;
}

// a body's own children (not its steed or raft): what flying lifts
const ridden = root => root.children.some(c => /^(steed_|raft$)/.test(String(c.name)));
const body = root => root.children.filter(c => !/^(steed_|raft$|ward_)/.test(String(c.name)));

export class Wards {
  constructor(engine, fx) {
    this.engine = engine;
    this.fx = fx;
    this.tier = (engine.quality && engine.quality.name) || 'high';
    this.on = new Map();         // actor -> {key, plan, parts}
  }

  // each frame: the hero (its own wards) and others [[actor, wards], ...]
  update(dt, t, hero, heroWards, others = []) {
    const focus = hero && hero.root ? hero.root.position : null;
    const want = new Map();
    if (hero && hero.root && heroWards && heroWards.length) want.set(hero, heroWards);
    const near = [];
    for (const [a, w] of others) {
      if (!a || !a.root || !a.root.parent || !w || !w.length) continue;
      const d = focus ? a.root.position.distanceTo(focus) : 0;
      if (d < NEAR) near.push([d, a, w]);
    }
    near.sort((x, y) => x[0] - y[0]);
    for (const [, a, w] of near.slice(0, BUDGET[this.tier] ?? BUDGET.high)) want.set(a, w.filter(k => k !== 'invisible'));
    for (const [a, s] of this.on) if (!want.has(a) || s.key !== planKey(want.get(a)) || !a.root.parent) this.drop(a);
    for (const [a, w] of want) {
      let s = this.on.get(a);
      if (!s) {
        const key = planKey(w);
        if (!key) continue;
        s = this.make(a, wardPlan(w), key);
        this.on.set(a, s);
      }
      this.tick(a, s, dt, t);
    }
  }

  make(a, plan, key) {
    const root = a.root;
    // the body's size, standing (measured once; the hover lift and a steed are left out)
    root.updateMatrixWorld(true);
    _box.makeEmpty();
    for (const c of body(root)) _box.expandByObject(c);
    const h = _box.isEmpty() ? 1.8 : Math.max(0.6, (_box.max.y - _box.min.y) / Math.max(1e-3, root.scale.y || 1));
    const w = _box.isEmpty() ? 0.8 : Math.max(0.5, Math.max(_box.max.x - _box.min.x, _box.max.z - _box.min.z) / Math.max(1e-3, root.scale.x || 1));
    const s = { key, plan, h, w, parts: [], mats: [], orbits: [], motesT: Math.random() * 0.2, windT: 0, lift: 0, faded: null };
    const add = (m, name) => { m.name = `ward_${name}`; root.add(m); s.parts.push(m); return m; };
    const g = geos();
    if (plan.shell != null) {
      const mat = shellMaterial(plan.shell, 0.55);
      s.mats.push(mat);
      s.shell = add(new THREE.Mesh(new THREE.SphereGeometry(1, 28, 18), mat), 'shell');
      s.shell.scale.set(Math.max(0.6, w * 0.75), h * 0.62, Math.max(0.6, w * 0.75));
      s.shell.position.y = h * 0.5;
      s.shell.renderOrder = 3;
    }
    for (const o of plan.orbits) {
      const items = [];
      const n = COUNT[o.kind] || 3;
      for (let i = 0; i < n; i++) {
        let m;
        if (o.kind === 'flame') { items.push({ m: null, a: (i / n) * Math.PI * 2 }); continue; }
        if (o.kind === 'stone' || o.kind === 'leaf') {
          const mat = new THREE.MeshStandardMaterial({ color: o.color, roughness: 0.9, flatShading: true, side: THREE.DoubleSide });
          s.mats.push(mat);
          m = new THREE.Mesh(g[o.kind], mat);
        } else {
          const mat = new THREE.MeshBasicMaterial({ color: new THREE.Color(o.color).multiplyScalar(1.4), transparent: true, opacity: 0.85,
            blending: THREE.AdditiveBlending, depthWrite: false });
          s.mats.push(mat);
          m = new THREE.Mesh(g[o.kind], mat);
        }
        items.push({ m: add(m, o.kind), a: (i / n) * Math.PI * 2 });
      }
      s.orbits.push({ ...o, items, spin: o.kind === 'star' ? 2.4 : o.kind === 'stone' ? 0.9 : 1.4,
        r: o.kind === 'star' ? 0.22 + w * 0.12 : 0.42 + w * 0.32, y: o.kind === 'star' ? h + 0.12 : h * (o.kind === 'stone' ? 0.35 : 0.55) });
    }
    if (plan.ring != null) {
      const mat = new THREE.MeshBasicMaterial({ color: new THREE.Color(plan.ring).multiplyScalar(1.2), transparent: true, opacity: 0.42,
        blending: THREE.AdditiveBlending, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, side: THREE.DoubleSide });
      s.mats.push(mat);
      s.ring = add(new THREE.Mesh(g.ring, mat), 'ring');
      s.ring.scale.setScalar(0.55 + w * 0.6);
      s.ring.position.y = 0.05;
      s.ring.renderOrder = 2;
    }
    if (plan.hover) {
      const mat = new THREE.MeshBasicMaterial({ color: 0xdfefff, transparent: true, opacity: 0.16, blending: THREE.AdditiveBlending,
        depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 });
      s.mats.push(mat);
      s.wind = add(new THREE.Mesh(g.disc, mat), 'wind');
      s.wind.scale.setScalar(0.35 + w * 0.35);
      s.wind.position.y = 0.04;
    }
    if (plan.fade) s.faded = this.fade(root);
    else if (plan.tint != null) s.tinted = this.tint(root, plan.tint);
    // blinded: a dark band over the eyes
    const eyes = plan.band ? eyeLine(root, h, w) : null;
    if (eyes) {
      const mat = new THREE.MeshBasicMaterial({ color: 0x0c0a0a, transparent: true, opacity: 0.9, side: THREE.DoubleSide });
      s.mats.push(mat);
      s.band = add(new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 1, 24, 1, true), mat), 'band');
      s.band.scale.set(eyes.r, eyes.r * 0.16, eyes.r);
      s.band.position.y = s.eyeY = eyes.y;
      // worn on the head: it nods, turns and slumps with it
      if (eyes.bone) { root.updateMatrixWorld(true); eyes.bone.attach(s.band); }
    }
    root.userData.animRate = plan.rate;
    return s;
  }

  tick(a, s, dt, t) {
    const root = a.root;
    // flying: the body (not a steed or these wards) up off the ground, bobbing; none while riding
    if (s.plan.hover) {
      const target = ridden(root) ? 0 : HOVER + Math.sin(t * 2.2) * 0.07;
      this.lift(root, target);
      if (s.wind) { s.wind.material.opacity = ridden(root) ? 0 : 0.12 + 0.06 * Math.sin(t * 3.1); s.wind.rotation.y += dt * 2; }
    }
    if (s.shell) {
      s.shell.material.uniforms.uOpacity.value = 0.5 + 0.12 * Math.sin(t * 1.7);
      s.shell.position.y = s.h * 0.5 + (root.userData.wardLift || 0);
    }
    if (s.ring) { s.ring.rotation.y += dt * 0.35; s.ring.material.opacity = 0.34 + 0.1 * Math.sin(t * 1.4); }
    const lift = root.userData.wardLift || 0;
    for (const o of s.orbits) {
      for (const it of o.items) {
        it.a += dt * o.spin;
        const x = Math.cos(it.a) * o.r, z = Math.sin(it.a) * o.r, y = o.y + lift + Math.sin(it.a * 2 + t) * 0.06;
        if (it.m) {
          it.m.position.set(x, y, z);
          it.m.rotation.set(t * 1.3 + it.a, t * 0.9, 0);
        } else if (this.fx.near(root.position, NEAR) && Math.random() < dt * 9) {
          // flames: a flicker from each point of the circle
          root.localToWorld(_p.set(x, y, z));
          this.fx.p.emit(_p, { count: 1, color: o.color, bright: 1.8, speed: 0.15, up: 0.9, life: 0.45, size: 0.16, drag: 1, grow: -0.3 });
        }
      }
    }
    // a harm's glow on the body comes and goes (a frost's or a hold's stays still)
    if (s.tinted) {
      const burn = s.plan.tint === WARDS.burning.tint;
      const k = s.plan.rate < 0.5 ? 0.3 : burn ? 0.42 + 0.18 * Math.sin(t * 9) * Math.sin(t * 3.7) : 0.2 + 0.13 * Math.sin(t * 2.6);
      for (const [, , mine] of s.tinted) for (const m of [].concat(mine)) if ('emissiveIntensity' in m) m.emissiveIntensity = k;
    }
    if (s.band && s.band.parent === root) s.band.position.y = s.eyeY + (root.userData.wardLift || 0);
    // the frightened tremble; a sleeper slumps forward
    if (s.plan.tremble) this.shake(root, (Math.random() - 0.5) * 0.06, (Math.random() - 0.5) * 0.06);
    // (one lying down asleep, posture.js, neither slumps nor breathes slowed: its clip is sleep
    // enough, and its getting down plays at its own pace)
    if (s.plan.slump) {
      const lying = !!root.userData.lying;
      this.lean(root, lying ? 0 : 0.28);
      root.userData.animRate = lying ? s.plan.restRate : s.plan.rate;
    }
    if (!this.fx.near(root.position, NEAR)) return;
    if (s.plan.motes.length && (s.motesT -= dt) <= 0) {
      const m = s.plan.motes[Math.floor(Math.random() * s.plan.motes.length)];
      s.motesT = (m.fast ? 0.05 : 0.11) + Math.random() * 0.08;
      const pos = root.position, r = 0.3 + s.w * 0.4;
      _p.set(pos.x + (Math.random() - 0.5) * r * 2, pos.y + lift + 0.2 + Math.random() * s.h, pos.z + (Math.random() - 0.5) * r * 2);
      this.fx.p.emit(_p, { count: 1, color: m.color, bright: 1.6, speed: m.fast ? 0.6 : 0.12, up: m.sink ? -0.25 : m.fast ? 0.2 : 0.4,
        life: m.fast ? 0.6 : 1.8, size: 0.12, drag: 0.5 });
    }
    if (s.plan.fx.length) emitHarms(s.plan.fx, this.fx, root, s, dt, lift);
    if (s.plan.hover && !ridden(root) && (s.windT -= dt) <= 0) {
      s.windT = 0.12;
      const pos = root.position;
      _p.set(pos.x + (Math.random() - 0.5) * 0.7, pos.y + 0.08, pos.z + (Math.random() - 0.5) * 0.7);
      this.fx.p.emit(_p, { count: 1, color: 0xe8f4ff, bright: 1.2, speed: 0.6, up: 0.05, life: 0.5, size: 0.18, grow: 0.6, drag: 2 });
    }
  }

  // raise the body's own parts to `to` metres (root.userData.wardLift holds what is applied, so
  // a steed mounted meanwhile, steed.js, takes it off before it lifts the rider to the saddle)
  lift(root, to) {
    const now = root.userData.wardLift || 0;
    if (Math.abs(to - now) < 1e-4) return;
    for (const c of body(root)) c.position.y += to - now;
    root.userData.wardLift = to;
  }

  // the hero drawn faint: its own copies of the materials, put back unless gear replaced them
  fade(root) {
    const swaps = [];
    root.traverse(o => {
      if (!o.isMesh || !o.material || /^ward_/.test(String(o.name))) return;
      const one = m => { const c = m.clone(); c.transparent = true; c.opacity = Math.min(c.opacity ?? 1, 0.38); c.depthWrite = false; return c; };
      const was = o.material;
      o.material = Array.isArray(was) ? was.map(one) : one(was);
      swaps.push([o, was, o.material]);
    });
    return swaps;
  }

  // the body's own parts nudged by (x, z) from where they stand (the frightened trembling); and
  // tipped forward by `a` (a sleeper's slump). What is applied is kept, so it can be taken off
  shake(root, x, z) {
    const was = root.userData.wardShake || [0, 0];
    for (const c of body(root)) { c.position.x += x - was[0]; c.position.z += z - was[1]; }
    root.userData.wardShake = [x, z];
  }
  lean(root, a) {
    const was = root.userData.wardLean || 0;
    if (Math.abs(a - was) < 1e-4) return;
    for (const c of body(root)) c.rotation.x += a - was;
    root.userData.wardLean = a;
  }

  // a harm's glow: the body's own copies of its materials (put back unless gear replaced them)
  tint(root, color) {
    const swaps = [];
    const glow = new THREE.Color(color);
    root.traverse(o => {
      if (!o.isMesh || !o.material || /^ward_/.test(String(o.name))) return;
      // (every material copied, so putting them back never frees one the body still shares)
      const one = m => { const c = m.clone(); if (c.emissive) { c.emissive = glow.clone(); c.emissiveIntensity = 0.2; } return c; };
      const was = o.material;
      const mine = Array.isArray(was) ? was.map(one) : one(was);
      o.material = mine;
      swaps.push([o, was, mine]);
    });
    return swaps;
  }

  drop(a) {
    const s = this.on.get(a);
    if (!s) return;
    for (const m of s.parts) a.root.remove(m);
    for (const m of s.mats) m.dispose();
    if (s.shell) s.shell.geometry.dispose();
    if (s.plan.hover) this.lift(a.root, 0);
    if (s.plan.tremble) this.shake(a.root, 0, 0);
    if (s.plan.slump) this.lean(a.root, 0);
    if (s.band) { if (s.band.parent) s.band.parent.remove(s.band); s.band.geometry.dispose(); }
    delete a.root.userData.animRate;
    for (const [o, was, mine] of [...(s.faded || []), ...(s.tinted || [])]) {
      if (o.material !== mine) continue;
      for (const m of [].concat(mine)) m.dispose();
      o.material = was;
    }
    this.on.delete(a);
  }

  clear() { for (const a of [...this.on.keys()]) this.drop(a); }
}
