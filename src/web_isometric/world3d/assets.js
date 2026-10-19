// Art loading: kits (many static models in one file), rigged characters, and the shared
// animation set. Built by tools/art3d/build.mjs; sources in docs/art/SOURCES.md.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

// relative to this module, so the versioned /v/<commit>/ prefix carries over
const ART = new URL('../art3d/', import.meta.url).href;
const loader = new GLTFLoader();
loader.setMeshoptDecoder(MeshoptDecoder);
const load = file => loader.loadAsync(ART + file);
export const loadArt = load;

// ---- kits -------------------------------------------------------------------
// A kit model can be several meshes (trunk + leaves). For instancing, each part's
// transform relative to the model root is baked into its own geometry copy.

// The optimiser stores positions as normalised integers (-1..1) and puts the real
// size in the node transform. Baking that transform into integer storage clamps
// everything to 1 m (walls came out flat), so bake into plain floats.
export function floatAttr(attr) {
  const n = attr.count, s = attr.itemSize, out = new Float32Array(n * s);
  for (let i = 0; i < n; i++) {
    out[i * s] = attr.getX(i);
    if (s > 1) out[i * s + 1] = attr.getY(i);
    if (s > 2) out[i * s + 2] = attr.getZ(i);
    if (s > 3) out[i * s + 3] = attr.getW(i);
  }
  return new THREE.BufferAttribute(out, s);
}

export async function loadKit(name) {
  const gltf = await load(`kits/${name}.glb`);
  const models = new Map();
  for (const root of gltf.scene.children) {
    root.updateMatrixWorld(true);
    const inv = new THREE.Matrix4().copy(root.matrixWorld).invert();
    const parts = [];
    root.traverse(o => {
      if (!o.isMesh) return;
      const g = o.geometry.clone();
      for (const k of ['position', 'normal', 'tangent']) if (g.attributes[k]) g.setAttribute(k, floatAttr(g.attributes[k]));
      g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld));
      g.computeBoundingSphere();
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) {
        // alpha-tested foliage must not write a solid shadow quad
        if (m.alphaTest > 0 || m.transparent) { m.side = THREE.DoubleSide; m.shadowSide = THREE.DoubleSide; }
      }
      parts.push({ geometry: g, material: o.material });
    });
    const box = new THREE.Box3();
    for (const p of parts) { p.geometry.computeBoundingBox(); box.union(p.geometry.boundingBox); }
    models.set(root.name, { name: root.name, parts, box });
  }
  return models;
}

// Collects placements for many models and turns them into one InstancedMesh per
// model part: a forest of 300 trees is a handful of draw calls.
export class Batcher {
  constructor() { this.items = new Map(); }
  add(model, matrix, opts = {}) {
    if (!model) return;
    let it = this.items.get(model.name);
    if (!it) { it = { model, mats: [], shadow: opts.shadow !== false, receive: opts.receive !== false, decorate: opts.decorate }; this.items.set(model.name, it); }
    it.mats.push(matrix.clone());
  }
  build(group) {
    for (const it of this.items.values()) {
      for (const part of it.model.parts) {
        const mesh = new THREE.InstancedMesh(part.geometry, part.material, it.mats.length);
        it.mats.forEach((m, i) => mesh.setMatrixAt(i, m));
        mesh.instanceMatrix.needsUpdate = true;
        mesh.computeBoundingSphere();
        mesh.castShadow = it.shadow;
        mesh.receiveShadow = it.receive;
        if (it.decorate) it.decorate(mesh);
        group.add(mesh);
      }
    }
    this.items.clear();
  }
}

const _q = new THREE.Quaternion(), _e = new THREE.Euler(), _s = new THREE.Vector3(), _p = new THREE.Vector3();
export function trs(x, y, z, yaw = 0, sx = 1, sy = sx, sz = sx) {
  _e.set(0, yaw, 0);
  return new THREE.Matrix4().compose(_p.set(x, y, z), _q.setFromEuler(_e), _s.set(sx, sy, sz));
}

// ---- characters -------------------------------------------------------------
let animsPromise = null;
const charCache = new Map();

export function loadAnims() {
  if (!animsPromise) {
    animsPromise = load('chars/rig_anims.glb').then(g => {
      const clips = new Map();
      for (const c of g.animations) clips.set(c.name, c);
      return clips;
    });
  }
  return animsPromise;
}

function loadChar(name) {
  if (!charCache.has(name)) charCache.set(name, load(`chars/${name}.glb`));
  return charCache.get(name);
}

// Which accessory meshes each model shows; everything else attached to the rig is hidden.
const LOADOUTS = {
  knight: ['1H_Sword', 'Round_Shield', 'Knight_Helmet', 'Knight_Cape'],
  barbarian: ['2H_Axe', 'Barbarian_Hat', 'Barbarian_Cape'],
  mage: ['2H_Staff', 'Mage_Hat', 'Mage_Cape'],
  rogue: ['Knife', 'Knife_Offhand', 'Rogue_Cape'],
  rogue_hooded: ['1H_Crossbow', 'Rogue_Cape'],
};

export class Actor {
  constructor(root, clips, alias = null) {
    this.root = root;
    this.mixer = new THREE.AnimationMixer(root);
    this.clips = clips;
    this.alias = alias;        // creature models: our clip names -> theirs
    this.actions = new Map();
    this.current = null;
  }
  action(name) {
    if (this.alias) name = this.alias[name] || name;
    if (!this.actions.has(name)) {
      const clip = this.clips.get(name);
      if (!clip) return null;
      this.actions.set(name, this.mixer.clipAction(clip));
    }
    return this.actions.get(name);
  }
  // loop a base animation, cross-fading from whatever played before
  play(name, fade = 0.18, timeScale = 1) {
    const a = this.action(name);
    if (!a) return;
    a.timeScale = timeScale;
    if (this.current === a) return;
    a.reset().setLoop(THREE.LoopRepeat, Infinity).fadeIn(fade).play();
    if (this.current) this.current.fadeOut(fade);
    this.current = a;
  }
  // cut a play-once short (the hero started running mid-swing)
  stopOnce(fade = 0.1) {
    const a = this.onceAction;
    this.onceAction = null;
    if (!a || a === this.current) return;
    a.fadeOut(fade);
    // once() faded the base loop out: bring it back, or the model drops to its bind pose
    if (this.current) this.current.reset().fadeIn(fade).play();
  }
  // play once (an attack, a hit), then fall back to the base loop
  once(name, fade = 0.08, timeScale = 1) {
    const a = this.action(name);
    if (!a) return 0;
    this.onceAction = a;
    const base = this.current;
    a.reset().setLoop(THREE.LoopOnce, 1);
    a.clampWhenFinished = false;
    a.timeScale = timeScale;
    a.fadeIn(fade).play();
    if (base && base !== a) base.fadeOut(fade);
    const done = e => {
      if (e.action !== a) return;
      this.mixer.removeEventListener('finished', done);
      if (base && this.current === base) { a.fadeOut(0.15); base.reset().fadeIn(0.15).play(); }
    };
    this.mixer.addEventListener('finished', done);
    return a.getClip().duration / timeScale;
  }
  // (a harm may slow or stop the body: wards.js sets root.userData.animRate)
  update(dt) { const r = this.root.userData.animRate; this.mixer.update(r == null ? dt : dt * r); }
}

export async function spawnCharacter(name, opts = {}) {
  const [gltf, clips] = await Promise.all([loadChar(name), loadAnims()]);
  const root = SkeletonUtils.clone(gltf.scene);
  const keep = new Set(opts.loadout || LOADOUTS[name] || []);
  root.traverse(o => {
    if (o.isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
      o.frustumCulled = false;   // skinned bounds lag the pose; the hero must never blink out
      // a static accessor mesh hanging off a bone (weapon, hat, shield)
      if (!o.isSkinnedMesh && LOADOUTS[name] !== undefined) o.visible = keep.has(o.name);
    }
  });
  if (opts.scale) root.scale.setScalar(opts.scale);
  // every actor owns its materials, so a hit flash or a fade touches only this body; a flat
  // one (a statue, a golem) is one colour all over instead of a tinted costume
  root.traverse(o => {
    if (o.isMesh && o.material) {
      o.material = o.material.clone();
      if (opts.flat) { o.material.map = null; o.material.color.set(opts.tint != null ? opts.tint : 0x9a9590); o.material.needsUpdate = true; }
      else if (opts.tint) o.material.color.multiply(new THREE.Color(opts.tint));
    }
  });
  return new Actor(root, clips);
}

// ---- creatures (mobs/*.glb: 1 m tall, facing +Z, each with its own clips) ----
const mobCache = new Map();
let mobIndex = null;
export function mobIndexReady() {
  if (!mobIndex) mobIndex = fetch(ART + 'mobs/index.json').then(r => r.json()).catch(() => ({}));
  return mobIndex;
}
function loadMob(name) {
  if (!mobCache.has(name)) mobCache.set(name, load(`mobs/${name}.glb`));
  return mobCache.get(name);
}
// map the names the game plays (the KayKit set) to whatever this creature has
function aliasFor(names) {
  const has = n => names.includes(n);
  const find = (...res) => { for (const re of res) { const n = names.find(x => re.test(x)); if (n) return n; } return null; };
  const idle = find(/^Idle$/, /^Flying$/, /^Swimming$/, /Idle/, /Action/) || names[0];
  const walk = find(/^Walk$/, /^Walking$/, /^WalkSlow$/, /^Flying$/, /^Swimming$/, /^Run$/) || idle;
  const run = find(/^Run$/, /^Walk$/, /^Walking$/, /^Flying$/, /^Swimming$/) || walk;
  const bite = find(/^Bite_Front$/, /^Bite$/, /^Bite_InPlace$/, /^Jump$/) || idle;
  const hit = find(/^HitRecieve$/, /^HitReact/, /Hit/) || null;
  const death = find(/^Death$/) || null;
  const jump = find(/^Jump$/) || bite;                              // a hop: dodges, stomps, rearing up
  const roar = find(/^Bite_InPlace$/, /^Bite_Front$/, /^Bite$/) || bite;   // breath, spit, a spell
  const a = {
    Idle: idle, Idle_B: idle, Idle_Combat: idle, Unarmed_Idle: idle, Spellcasting: idle,
    Walking_A: walk, Walking_B: walk, Walking_C: walk, Walking_D_Skeletons: walk, Running_A: run, Running_B: run,
    '1H_Melee_Attack_Chop': bite, '1H_Melee_Attack_Slice_Diagonal': bite, '1H_Melee_Attack_Stab': bite,
    '1H_Melee_Attack_Slice_Horizontal': bite, '1H_Melee_Attack_Jump_Chop': jump,
    '2H_Melee_Attack_Chop': bite, '2H_Melee_Attack_Slice': bite, '2H_Melee_Attack_Stab': bite, '2H_Melee_Attack_Spin': jump,
    Dualwield_Melee_Attack_Chop: bite, Dualwield_Melee_Attack_Slice: bite, Dualwield_Melee_Attack_Stab: bite,
    Unarmed_Melee_Attack_Kick: bite, Unarmed_Melee_Attack_Punch_A: bite, Throw: bite, Block_Attack: bite,
    Spellcast_Shoot: roar, Spellcast_Long: roar, Spellcast_Raise: roar, Spellcast_Summon: roar,
    '1H_Ranged_Shoot': roar, '2H_Ranged_Shoot': roar,
    Block: jump, Cheer: jump, Taunt: find(/^No$/) || jump,
    Dodge_Left: jump, Dodge_Right: jump, Dodge_Backward: jump, Dodge_Forward: jump,
    Hit_A: hit || idle, Hit_B: hit || idle, Block_Hit: hit || idle, Death_A: death || idle, Death_B: death || idle,
  };
  return has(idle) ? a : a;
}
export async function spawnMob(name, opts = {}) {
  return actorFrom(await loadMob(name), opts.height || 1, opts);
}

// ---- bodies made in Blender (tools/art3d/blender -> bodies/*.glb: real size in metres, facing +Z,
// feet at 0, one skinned mesh, the creature clip names; bodies/index.json lists them with height) ----
const bodyCache = new Map();
let bodyIndex = null;
export function bodyIndexReady() {
  if (!bodyIndex) bodyIndex = fetch(ART + 'bodies/index.json').then(r => (r.ok ? r.json() : {})).catch(() => ({}));
  return bodyIndex;
}
// opts.height: stand this tall (else its own size)
export async function spawnBody(name, opts = {}) {
  const index = await bodyIndexReady();
  const entry = index[name];
  if (!entry) throw new Error(`no body ${name}`);
  if (!bodyCache.has(name)) bodyCache.set(name, load(`bodies/${name}.glb`));
  // the bestiary's h is its height, or for a long low body (index ref) its length
  const s = opts.height ? opts.height / (entry.ref || entry.height || 1) : 1;
  const a = actorFrom(await bodyCache.get(name), s, opts);
  // the body's own look (bodies/index.json): a ghost is see-through, an elemental glows
  const look = entry.look || {};
  if (look.opacity != null || look.glow) {
    a.root.traverse(o => {
      if (!o.isMesh) return;
      if (look.opacity != null) { o.material.transparent = true; o.material.opacity = look.opacity; o.material.depthWrite = look.opacity > 0.8; }
      if (look.glow) { o.material.emissive = o.material.color.clone(); o.material.emissiveIntensity = look.glow; o.material.emissiveMap = o.material.map; }
    });
  }
  return a;
}

function actorFrom(gltf, scale, opts) {
  const root = SkeletonUtils.clone(gltf.scene);
  root.traverse(o => {
    if (o.isMesh) {
      o.castShadow = true; o.receiveShadow = true; o.frustumCulled = false;
      o.material = o.material.clone();
      if (opts.tint) o.material.color.multiply(new THREE.Color(opts.tint));
    }
  });
  root.scale.setScalar(scale);
  const clips = new Map(gltf.animations.map(c => [c.name, c]));
  return new Actor(root, clips, aliasFor([...clips.keys()]));
}
