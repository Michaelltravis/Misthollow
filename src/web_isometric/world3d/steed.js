// The hero (or another player) riding their mount (Push 34): a steed built from the creature kit
// (kin.js), by the mount's key: a horse's build and coat, a nightmare black with burning eyes and
// hooves, a griffin a lion's body with wings, a clockwork steed brass, a stag, a boar, a camel, a
// panther, a warg. Saddle and blanket on its back (barding for war mounts). The steed is a child
// of the rider's root, so it goes wherever they go; the rider's own body sits up on the saddle
// in a seated pose. On foot, nothing changes.
import * as THREE from 'three';
import { kinRecipe } from './kinrecipe.js';
import { makeKin } from './kin.js';
import { steedSpec, mountLook } from './steedlogic.js';
import { spawnBody } from './assets.js';
import { feeler, section, buildTack, makeRein } from './tack.js';
export { STEEDS, steedSpec } from './steedlogic.js';

// a kit body `height` tall stands about this much shorter than a rider of that height (it is
// long, not tall), so steeds are drawn this much bigger
const KIN_SCALE = 1.25;
const FACE = 0;

const SADDLE_MAT = new THREE.MeshStandardMaterial({ color: 0x5a3418, roughness: 0.7 });
const FLAME_MAT = new THREE.MeshBasicMaterial({ color: new THREE.Color(2.6, 0.9, 0.2) });
const hash = s => { let h = 2166136261; for (const ch of String(s)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return h >>> 0; };


// the particles a mount's marks are drawn with (main.js sets it: fx.js)
let FX = null;
export function setSteedFx(fx) { FX = fx; }

// a steed for a mount key, sized to a rider `riderH` metres tall:
// { root, saddleY, spec, update(dt, moving, speed), bob, onReady }
// The creature kit's body (kin.js) shows at once; the mount's real body (bodies/*.glb, its look:
// steedlogic.js MOUNT_LOOK) replaces it when loaded, fitted with its tack (tack.js), and calls
// onReady (the rider is set at the new saddle's height: mountRider)
export function makeSteed(key, riderH = 1.7) {
  const root = new THREE.Group();
  root.name = `steed_${key}`;
  const kit = kitSteed(key, riderH);
  root.add(kit.group);
  const steed = { root, saddleY: kit.saddleY, spec: kit.spec, bob: 0, onReady: null, real: null, key };
  steed.update = (dt, moving, speed = 1) => (steed.real ? steed.real.update(dt, moving, speed) : kit.update(dt, moving, speed));
  realSteed(key, riderH).then(real => {
    if (!real || !root.parent && root.userData.gone) return;
    root.remove(kit.group);
    root.add(real.group);
    steed.real = real;
    steed.saddleY = real.saddleY;
    real.steed = steed;
    if (steed.onReady) steed.onReady();
  }).catch(() => {});
  return steed;
}

// ---- the creature kit's steed (shown while the real body loads, or if it cannot) ----
function kitSteed(key, riderH) {
  const base = steedSpec(key);
  const spec = { ...base, height: base.height * riderH * KIN_SCALE };
  const recipe = kinRecipe(spec.body, spec.words, hash(key), spec.tint);
  const actor = makeKin(recipe, { height: spec.height });
  actor.root.rotation.y = FACE;          // the kit's creatures face +z, as a rider does
  const group = new THREE.Group();
  group.add(actor.root);
  const saddleY = spec.height * spec.back;
  const blanket = new THREE.Mesh(new THREE.BoxGeometry(spec.height * 0.36, 0.05, spec.height * 0.32),
    new THREE.MeshStandardMaterial({ color: spec.extra.barding || 0x7a2a22, roughness: 0.85 }));
  blanket.position.set(0, saddleY - 0.02, 0);
  const saddle = new THREE.Mesh(new THREE.BoxGeometry(spec.height * 0.24, 0.1, spec.height * 0.2), SADDLE_MAT);
  saddle.position.set(0, saddleY + 0.04, 0);
  group.add(blanket, saddle);
  return {
    group, saddleY, spec,
    update(dt, moving, speed = 1) {
      actor.play(moving ? 'Walking_A' : 'Idle');
      actor.update(dt * (moving ? Math.max(0.8, speed) : 1));
    },
  };
}

// ---- the real body, fitted ----
const PICK = ['hips', 'spine', 'chest', 'head', 'muzzle', 'thorax', 'abdomen', 'snout', 'belly'];
async function realSteed(key, riderH) {
  const look = mountLook(key);
  let a;
  try { a = await spawnBody(look.body, { tint: look.coat }); } catch (_) { return null; }
  const meshes = [];
  a.root.traverse(o => {
    if (!o.isMesh) return;
    meshes.push(o);
    const m = o.material;
    if (look.metal) { m.metalness = 0.55; m.roughness = 0.32; m.emissive = new THREE.Color(look.coat).multiplyScalar(0.14); }
    if (look.ghost) { m.transparent = true; m.opacity = look.ghost; m.depthWrite = false; }
    if (look.glow) { m.emissive = new THREE.Color(look.glow); m.emissiveIntensity = 0.22; }
  });
  const holder = new THREE.Group();
  holder.add(a.root);
  const bones = {}, feet = [];
  a.root.traverse(o => {
    if (!o.isBone) return;
    const n = o.name.toLowerCase();
    if (PICK.includes(n) && !bones[n]) bones[n] = o;
    if (!bones.neck && /^neck/.test(n)) bones.neck = o;
    if (/^(fl3|hl3)|^leg\d2|^leg3/.test(n)) feet.push(o);
  });
  bones.spine = bones.spine || bones.belly || bones.thorax || bones.hips;
  bones.chest = bones.chest || bones.thorax || bones.spine;
  bones.muzzle = bones.muzzle || bones.snout;
  holder.updateMatrixWorld(true);
  const at = b => b.getWorldPosition(new THREE.Vector3());
  // where the rider sits: on the back, just behind the withers (near halfway from the spine to
  // the chest); the body scaled so that the saddle is at the rider's own seat height (times the
  // mount's size), then moved so the saddle is over the steed's origin (the rider's)
  const sp = at(bones.spine), ch = at(bones.chest);
  const sz = sp.z + (ch.z - sp.z) * (bones.spine === bones.chest ? 0 : 0.45);
  let feel = feeler(meshes);
  const back = feel.top(0, sz) ?? (new THREE.Box3().setFromObject(a.root).max.y * 0.7);
  const want = riderH * 0.58 * (look.size || 1);
  const k = want / Math.max(0.05, back);
  a.root.scale.multiplyScalar(k);
  a.root.position.z = -sz * k;
  holder.updateMatrixWorld(true);
  feel = feeler(meshes);
  const box = new THREE.Box3().setFromObject(a.root);
  const L = Math.max(0.5, box.max.z - box.min.z);
  const tack = buildTack(feel, bones, look, { z: 0, y: want }, L);
  for (const [obj, bone] of tack.parts) { holder.add(obj); obj.castShadow = true; (bone || holder).attach(obj); }
  // reins from the bit to the rider's hands
  const reinMat = new THREE.MeshStandardMaterial({ color: look.tack === 'dark' ? 0x1a1414 : 0x3a2414, roughness: 0.7 });
  const reins = tack.bits.map(() => { const r = makeRein(reinMat); holder.add(r); return r; });
  // glowing eyes
  const head = bones.head;
  if (look.eyes && head) {
    const hp = at(head), hw = Math.max(0.04, feel.side(hp.y, hp.z, 1) ?? 0.08);
    const em = new THREE.MeshBasicMaterial({ color: new THREE.Color(look.eyes).multiplyScalar(3) });
    for (const side of [-1, 1]) {
      const e = new THREE.Mesh(new THREE.SphereGeometry(Math.max(0.02, hw * 0.16), 8, 6), em);
      e.position.copy(hp).add(new THREE.Vector3(side * hw * 0.62, hw * 0.35, hw * 0.55));
      holder.add(e); head.attach(e);
    }
  }
  // feathered wings at the shoulders (a griffin, a gryphon)
  const wings = [];
  if (look.wings && bones.chest) {
    const cp = at(bones.chest), cs = section(feel, cp.z) || { top: want, a: L * 0.12 };
    for (const side of [-1, 1]) {
      const w = featherWing(look.wings, L * 0.62, side);
      w.position.set(side * cs.a * 0.55, cs.top - 0.02, cp.z);
      holder.add(w); bones.chest.attach(w);
      w.userData.base = w.quaternion.clone();
      w.userData.side = side;
      wings.push(w);
    }
  }
  const restY = at(bones.spine).y;
  const group = new THREE.Group();
  group.add(holder);
  let t = 0, fxT = 0, gait = '';
  const v = new THREE.Vector3(), hands = new THREE.Vector3(), q = new THREE.Quaternion(), Zx = new THREE.Vector3(0, 0, 1);
  const real = {
    group, saddleY: want + 0.02, look, feet,
    update(dt, moving, speed = 1) {
      t += dt;
      const run = moving && speed > 1.45;
      const g = run ? 'Running_A' : moving ? 'Walking_A' : 'Idle';
      if (g !== gait) { a.play(g, 0.25); gait = g; }
      a.update(dt * (moving ? Math.max(0.75, Math.min(1.6, run ? speed / 1.6 : speed)) : 1));
      holder.updateMatrixWorld(true);
      // the rider rises and falls with the back
      if (real.steed) real.steed.bob = holder.worldToLocal(bones.spine.getWorldPosition(v)).y - restY;
      // the reins: from the bit's rings to the rider's hands (in front of the saddle)
      reins.forEach((r, i) => {
        const side = i ? 1 : -1;
        tack.bits[i].getWorldPosition(v); holder.worldToLocal(v);
        hands.set(side * riderH * 0.08, want + riderH * 0.24 + (real.steed ? real.steed.bob : 0), riderH * 0.16);
        r.userData.set(v, hands, 0.05 + riderH * 0.03);
      });
      for (const w of wings) {
        const flap = moving ? Math.sin(t * 7) * 0.5 : 0.1 + Math.sin(t * 1.6) * 0.06;
        q.setFromAxisAngle(Zx, w.userData.side * flap);
        w.quaternion.copy(w.userData.base).multiply(q);
      }
      if (FX && (fxT -= dt) <= 0) { fxT = 0.05; marks(look, feet, bones, moving, run, holder); }
    },
  };
  return real;
}

// a wing of layered feathers, spreading out to `side`: long pointed flight feathers fanned back
// from the shoulder, darker at the tips, under a row of short coverts
const feather = (w, len) => {
  const sh = new THREE.Shape();
  sh.moveTo(0, 0); sh.quadraticCurveTo(w, len * 0.35, w * 0.35, len); sh.lineTo(-w * 0.1, len * 0.96);
  sh.quadraticCurveTo(-w * 0.9, len * 0.4, 0, 0);
  return new THREE.ShapeGeometry(sh, 6);
};
function featherWing(color, span, side) {
  const g = new THREE.Group();
  const base = new THREE.Color(color);
  const layer = (n, len0, dlen, w, lift, dark) => {
    for (let i = 0; i < n; i++) {
      const len = span * (len0 + dlen * i);
      const m = new THREE.Mesh(feather(span * w, len), new THREE.MeshStandardMaterial({
        color: base.clone().offsetHSL(0, 0, (i % 2) * 0.05 - dark), roughness: 0.8, side: THREE.DoubleSide }));
      // fanned out from the shoulder, sweeping back and up
      m.rotation.order = 'YXZ';
      m.rotation.z = side * (-0.25 - i * 0.07);
      m.rotation.x = -0.95 - i * 0.06;
      m.position.set(side * i * span * 0.025, lift, -i * span * 0.03);
      g.add(m);
    }
  };
  layer(9, 0.34, 0.075, 0.13, 0, 0.08);
  layer(6, 0.2, 0.04, 0.12, 0.02, -0.04);
  return g;
}

// what marks a mount out as it goes, in particles (a few each twentieth of a second)
const _p = new THREE.Vector3();
function marks(look, feet, bones, moving, run, holder) {
  const fx = look.fx;
  const foot = () => feet[Math.floor(Math.random() * feet.length)];
  const atFoot = () => { const f = feet.length ? foot() : bones.hips; return f ? f.getWorldPosition(_p) : null; };
  if (!FX.near || FX.near(holder.getWorldPosition(_p), 30)) {
    if (run && feet.length && Math.random() < 0.5) {
      const p = atFoot(); if (p) FX.p.emit(p.setY(0.15), { count: 1, color: 0xb8a888, bright: 0.7, speed: 0.6, up: 0.3, life: 0.7, size: 0.35, grow: 0.7, drag: 2 });
    }
    if (fx === 'hellfire') {
      for (let i = 0; i < 2; i++) { const p = atFoot(); if (p) FX.p.emit(p, { count: 1, color: Math.random() < 0.5 ? 0xff5a10 : 0xffb030, bright: 2.6, speed: 0.3, up: 1.4, life: 0.5, size: 0.28, grow: -0.3, drag: 1 }); }
      if (moving) { const p = atFoot(); if (p) FX.p.emit(p, { count: 1, color: 0x3a2a24, bright: 0.5, speed: 0.2, up: 0.6, life: 1.2, size: 0.4, grow: 0.6, drag: 1 }); }
    } else if (fx === 'celestial') {
      const p = atFoot(); if (p) FX.p.emit(p, { count: 1, color: Math.random() < 0.5 ? 0xffe8a0 : 0xffffff, bright: 2.2, speed: 0.3, up: 0.8, life: 1.1, size: 0.16, drag: 0.6 });
      if (Math.random() < 0.4 && bones.spine) FX.glyph(bones.spine.getWorldPosition(_p).add(new THREE.Vector3((Math.random() - 0.5) * 1.2, Math.random() * 0.6, (Math.random() - 0.5) * 1.4)),
        { glyph: 'star', count: 1, color: 0xffe08a, bright: 2, speed: 0.1, up: 0.4, life: 1.2, size: 0.14, drag: 0.5 });
    } else if (fx === 'steam') {
      if (Math.random() < 0.25 && bones.muzzle) FX.p.emit(bones.muzzle.getWorldPosition(_p), { count: 2, color: 0xe8e8ec, bright: 0.9, speed: 0.4, up: 0.6, life: 1.2, size: 0.3, grow: 0.8, drag: 1.2 });
      if (moving && Math.random() < 0.3) { const p = atFoot(); if (p) FX.p.emit(p, { count: 1, color: 0xffd080, bright: 2, speed: 1.4, up: 1, gravity: 6, life: 0.4, size: 0.08, drag: 0.5 }); }
    } else if (fx === 'arcane' || fx === 'moon') {
      const c = fx === 'moon' ? 0xd8e4ff : (look.glow || 0x9ab8ff);
      const at = bones.spine ? bones.spine.getWorldPosition(_p) : null;
      if (at && Math.random() < 0.7) FX.p.emit(at.add(new THREE.Vector3((Math.random() - 0.5) * 1.4, (Math.random() - 0.3) * 0.8, (Math.random() - 0.5) * 1.6)),
        { count: 1, color: c, bright: 2, speed: 0.15, up: 0.35, life: 1.4, size: 0.13, drag: 0.6 });
      if (moving) { const p = atFoot(); if (p) FX.p.emit(p, { count: 1, color: c, bright: 1.8, speed: 0.2, up: 0.3, life: 0.9, size: 0.16, drag: 0.8 }); }
    } else if (fx === 'shadow') {
      const p = atFoot(); if (p) FX.p.emit(p, { count: 1, color: 0x6a3aaa, bright: 0.9, speed: 0.2, up: 0.4, life: 1, size: 0.4, grow: 0.5, drag: 1 });
    } else if (fx === 'embers') {
      if (Math.random() < 0.3 && bones.muzzle) FX.p.emit(bones.muzzle.getWorldPosition(_p), { count: 1, color: 0x5a4a44, bright: 0.6, speed: 0.3, up: 0.7, life: 1.4, size: 0.35, grow: 0.7, drag: 1 });
      if (Math.random() < 0.4) { const p = atFoot(); if (p) FX.p.emit(p, { count: 1, color: 0xff8a2a, bright: 2.4, speed: 0.4, up: 1, life: 0.6, size: 0.12, drag: 0.6 }); }
    } else if (fx === 'leaves') {
      if (Math.random() < 0.15 && bones.chest) FX.glyph(bones.chest.getWorldPosition(_p).add(new THREE.Vector3(0, 0.6, 0)),
        { glyph: 'leaf', count: 1, color: 0x7aa04a, bright: 1, speed: 0.3, up: -0.4, life: 2, size: 0.2, drag: 0.4, spin: 3 });
    }
  }
}

// The riding pose: the rig has no riding clip, so a rider plays their idle (or an attack, a cast)
// and the legs are set astride on top of it each frame. Each leg bone is aimed along a direction in
// the rider's own frame (x: out to that side, y: up, z: forward): thighs out over the steed's back,
// shins down its flanks, feet forward in the stirrups. Aiming (not fixed angles) works whatever
// axes the rig's bones were authored in.
export const RIDE_POSE = {
  upperleg: [0.85, -0.35, 0.45],
  lowerleg: [0.12, -1, 0.1],
  foot: [0.12, -0.25, 1],
};
const PARTS = [['upperleg', 'lowerleg'], ['lowerleg', 'foot'], ['foot', null]];
const norm = n => String(n || '').toLowerCase().replace(/[^a-z]/g, '');
function legBones(rider) {
  const out = {};
  rider.root.traverse(o => {
    if (!o.isBone) return;
    const n = norm(o.name);
    for (const [part] of PARTS) for (const side of ['l', 'r']) {
      if (n === part + side && !out[part + side]) out[part + side] = o;
    }
    if (n === 'hips' && !out.hips) out.hips = o;
  });
  return out;
}
const _a = new THREE.Vector3(), _b = new THREE.Vector3(), _want = new THREE.Vector3();
const _qw = new THREE.Quaternion(), _qp = new THREE.Quaternion(), _qd = new THREE.Quaternion(), _qr = new THREE.Quaternion();
// a bone's pointing direction in the world: toward its child bone (the foot has none: its own +y)
function boneDir(bone, child, out) {
  bone.getWorldPosition(_a);
  if (child) return out.copy(child.getWorldPosition(_b)).sub(_a).normalize();
  return out.set(0, 1, 0).applyQuaternion(bone.getWorldQuaternion(_qw)).normalize();
}
// set the legs astride (call after the rider's animation update, every frame: the mixer poses the
// bones from the clip each time, so nothing piles up)
export function ridePose(state, root) {
  if (!state || !state.bones || !root) return;
  root.updateWorldMatrix(true, true);
  root.getWorldQuaternion(_qr);
  for (const side of ['l', 'r']) {
    const sx = side === 'l' ? 1 : -1;
    for (const [part, next] of PARTS) {
      const bone = state.bones[part + side];
      if (!bone || !bone.parent) continue;
      const child = next ? state.bones[next + side] : null;
      const w = RIDE_POSE[part];
      _want.set(w[0] * sx, w[1], w[2]).normalize().applyQuaternion(_qr);
      const cur = boneDir(bone, child, new THREE.Vector3());
      _qd.setFromUnitVectors(cur, _want);
      bone.getWorldQuaternion(_qw);
      bone.parent.getWorldQuaternion(_qp);
      bone.quaternion.copy(_qp.invert().multiply(_qd.multiply(_qw)));
      bone.updateWorldMatrix(false, true);
    }
  }
}

// Put a rider on (or off) a steed. `rider` is an actor with `.root` (its first child is the body
// model); returns the riding state, or null on foot.
export function mountRider(rider, key, prev = null) {
  if (prev && prev.key === key) return prev;
  if (prev) {
    rider.root.remove(prev.steed.root);
    prev.steed.root.userData.gone = true;
    for (const [c, y] of prev.lifted) c.position.y = y;
  }
  if (!key) return null;
  // the rider's height, standing (before anything is lifted)
  // (its spells' shells and rings, wards.js, are not the body)
  const box = new THREE.Box3();
  rider.root.updateMatrixWorld(true);
  for (const c of rider.root.children) if (!/^(steed_|raft$|ward_)/.test(String(c.name))) box.expandByObject(c);
  if (box.isEmpty()) box.setFromObject(rider.root);
  const riderH = Math.max(0.8, (box.max.y - box.min.y) / Math.max(1e-3, rider.root.scale.y || 1));
  const steed = makeSteed(key, riderH);
  // the hips' height standing: the rider goes up until their hips sit on the saddle
  const bones = legBones(rider);
  let hipsH = riderH * 0.42;
  if (bones.hips) {
    rider.root.updateMatrixWorld(true);
    const v = bones.hips.getWorldPosition(new THREE.Vector3());
    hipsH = (v.y - box.min.y) / Math.max(1e-3, rider.root.scale.y || 1);
  }
  // a flyer's hover (wards.js) comes off: the saddle sets the height
  const hover = rider.root.userData.wardLift || 0;
  rider.root.userData.wardLift = 0;
  const lifted = rider.root.children.filter(c => !/^(steed_|raft$|ward_)/.test(String(c.name))).map(c => [c, c.position.y - hover]);
  const state = { key, steed, lifted, bones, scale: riderH, lift: 0 };
  // up into the saddle (again when the real body comes, its saddle at its own height), rising and
  // falling with the steed's back as it goes
  const seat = () => {
    state.lift = Math.max(0, steed.saddleY - hipsH + riderH * 0.01);
    for (const [c, y] of lifted) c.position.y = y + state.lift;
  };
  seat();
  steed.onReady = seat;
  rider.root.add(steed.root);
  state.pose = () => {
    const bob = steed.bob || 0;
    if (bob) for (const [c, y] of lifted) c.position.y = y + state.lift + bob;
    ridePose({ bones }, rider.root);
  };
  return state;
}

// A raft under the hero on open water (a water room: the server lets only those with a boat or a
// raft in): a few lashed logs, riding a little low, bobbing.
export function makeRaft() {
  const root = new THREE.Group();
  root.name = 'raft';
  const wood = new THREE.MeshStandardMaterial({ color: 0x7a5634, roughness: 0.9 });
  const rope = new THREE.MeshStandardMaterial({ color: 0xc8b48a, roughness: 1 });
  for (let i = -2; i <= 2; i++) {
    const log = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.13, 1.9, 7), wood);
    log.rotation.x = Math.PI / 2;
    log.position.set(i * 0.27, -0.02, 0);
    log.castShadow = true;
    root.add(log);
  }
  for (const z of [-0.6, 0.6]) {
    const tie = new THREE.Mesh(new THREE.BoxGeometry(1.45, 0.05, 0.08), rope);
    tie.position.set(0, 0.11, z);
    root.add(tie);
  }
  root.userData.bob = t => { root.position.y = -0.06 + Math.sin(t * 1.6) * 0.03; root.rotation.z = Math.sin(t * 1.1) * 0.03; };
  return root;
}
