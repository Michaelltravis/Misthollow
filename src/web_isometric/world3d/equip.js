// Heroes dressed in what they wear. The equipment kit (art3d/chars/equip.glb, built by
// tools/art3d/build.mjs 'equip') holds every adventurer body part and piece on one rig,
// painted from one palette. A character is dressed by merging the parts and pieces their
// look asks for (gearlook.js planLook) into ONE skinned mesh: two draw calls (the mesh and
// its shadow) however much they wear, recoloured by moving each piece's UVs to other palette
// columns. Re-dressing swaps that mesh's geometry in place, so the skeleton, the animation
// mixer and everything that holds the actor stay as they are.
//
// Finer gear adds small pieces built in code (procgear.js add-ons: a pommel stone, a shield
// boss, a crest, a crown, pauldrons, a cloak's emblem), each placed from the shape of the
// piece it sits on, and merged into the same mesh. Columns named '~glow' light themselves
// (a few lines patched into the material's shader), as bright as the plan says.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { loadArt, loadAnims, floatAttr, Actor } from './assets.js';
import { planLook, kitIndex } from './gearlook.js';
import { buildProc, buildAddon, HANGING } from './procgear.js';

const ART = new URL('../art3d/', import.meta.url).href;
const CACHE_MAX = 48;
let kitPromise = null;

// three.js drops dots from node names ('handslot.r' -> 'handslotr')
export const boneKey = name => String(name || '').replace(/[[\].:/]/g, '').replace(/\s/g, '_');

export function loadEquipKit() {
  if (!kitPromise) {
    kitPromise = Promise.all([loadArt('chars/equip.glb'), fetch(ART + 'chars/equip.json').then(r => r.json())])
      .then(([gltf, manifest]) => makeKit(gltf, manifest));
  }
  return kitPromise;
}

function intAttr(attr) {
  const n = attr.count, out = new Uint16Array(n * 4);
  for (let i = 0; i < n; i++) { out[i * 4] = attr.getX(i); out[i * 4 + 1] = attr.getY(i); out[i * 4 + 2] = attr.getZ(i); out[i * 4 + 3] = attr.getW(i); }
  return new THREE.BufferAttribute(out, 4);
}

// every piece as plain float geometry in the rig's rest pose, skinned to its bones (a hat or
// a sword wholly to the bone it hangs from)
function makeKit(gltf, manifest) {
  const kit = kitIndex(manifest);
  const scene = gltf.scene;
  scene.updateMatrixWorld(true);
  let skinned = null;
  scene.traverse(o => { if (!skinned && o.isSkinnedMesh) skinned = o; });
  const bones = skinned.skeleton.bones;
  kit.boneNames = bones.map(b => b.name);
  kit.boneIndex = new Map(bones.map((b, i) => [b.name, i]));
  kit.rest = bones.map(b => b.matrixWorld.clone());
  kit.inverses = kit.rest.map(m => m.clone().invert());
  kit.rigNode = skinned.parent;            // 'Rig': the bones (and, in the kit, the parts)
  kit.material = skinned.material;
  kit.glowMask = glowMask(kit);
  kit.geo = new Map();
  kit.shapes = new Map();
  kit.cache = new Map();
  scene.traverse(o => {
    if (!o.isMesh) return;
    const src = o.geometry;
    const M = o.isSkinnedMesh
      ? new THREE.Matrix4().multiplyMatrices(o.skeleton.bones[0].matrixWorld, o.skeleton.boneInverses[0]).multiply(o.bindMatrix)
      : o.matrixWorld.clone();
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', floatAttr(src.attributes.position));
    g.setAttribute('normal', floatAttr(src.attributes.normal));
    g.setAttribute('uv', floatAttr(src.attributes.uv));
    g.applyMatrix4(M);
    if (o.isSkinnedMesh) {
      g.setAttribute('skinIndex', intAttr(src.attributes.skinIndex));
      g.setAttribute('skinWeight', floatAttr(src.attributes.skinWeight));
    } else skinTo(g, kit.boneIndex.get(o.parent.name) || 0);
    g.setIndex(new THREE.BufferAttribute(src.index.array.slice(), 1));
    kit.geo.set(o.name, g);
  });
  return kit;
}

// a geometry wholly on one bone, or shared half and half with a second
function skinTo(g, b, b2 = null) {
  const n = g.attributes.position.count, si = new Uint16Array(n * 4), sw = new Float32Array(n * 4);
  for (let i = 0; i < n; i++) {
    si[i * 4] = b; sw[i * 4] = b2 == null ? 1 : 0.5;
    if (b2 != null) { si[i * 4 + 1] = b2; sw[i * 4 + 1] = 0.5; }
  }
  g.setAttribute('skinIndex', new THREE.BufferAttribute(si, 4));
  g.setAttribute('skinWeight', new THREE.BufferAttribute(sw, 4));
  return g;
}

// the bones alone, for one actor
function cloneBones(node) {
  const c = node.clone(false);
  for (const ch of node.children) if (!ch.isMesh) c.add(cloneBones(ch));
  return c;
}

function recolour(g, remap, N) {
  const uv = g.attributes.uv.array;
  for (let i = 0; i < uv.length; i += 2) {
    const to = remap[Math.floor(uv[i] * N)];
    if (to !== undefined) uv[i] = (to + 0.5) / N;
  }
}

// a hat made for another head: moved and scaled about the bone it hangs from
const _t = new THREE.Vector3(), _s = new THREE.Vector3(), _q = new THREE.Quaternion(), _v = new THREE.Vector3();
function fitTo(g, fit, bone, kit) {
  const b = kit.boneIndex.get(boneKey(bone));
  if (b == null) return;
  const F = new THREE.Matrix4().compose(_t.fromArray(fit.t || [0, 0, 0]), _q.identity(), _s.setScalar(fit.s || 1));
  g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(kit.rest[b], F).multiply(kit.inverses[b]));
}

// what each role of a built-in-code piece is painted with, unless its look says otherwise
const PROC_PAINT = { wood: 'wood', wood_dark: 'wood_dark', wood_pale: 'wood_pale', metal: 'steel', metal_dark: 'steel~dark',
  leather: 'leather_dark', string: 'white', hole: 'black~dark', gem: 'gem_red', bone: 'bone', cloth: 'red', gold: 'gold', trim: 'gold', accent: 'white' };
function painter(kit, roles, worn) {
  return role => {
    let name = roles && roles[role];
    if (!name) { name = PROC_PAINT[role] || 'steel'; if (worn && kit.col(`${name}~worn`) != null && role !== 'string' && role !== 'hole') name = `${name}~worn`; }
    const c = kit.col(name) ?? kit.col(PROC_PAINT[role] || 'steel') ?? 0;
    return (c + 0.5) / kit.N;
  };
}
function toGeometry(a) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(a.position, 3));
  g.setAttribute('normal', new THREE.BufferAttribute(a.normal, 3));
  g.setAttribute('uv', new THREE.BufferAttribute(a.uv, 2));
  g.setIndex(new THREE.BufferAttribute(a.index, 1));
  return g;
}
const mountMatrix = m => new THREE.Matrix4().compose(_t.fromArray(m.t), _q.fromArray(m.r), _s.fromArray(m.s));

// a prop's own frame (as the pack made it: a sword runs along +y from the hand) where it hangs
// in the rig's rest pose; a body part's frame is the rig's
function frameOf(kit, name) {
  const p = kit.pieces[name];
  if (!p || p.type !== 'prop') return { M: new THREE.Matrix4(), b: null };
  const b = kit.boneIndex.get(boneKey(p.bone));
  return { M: new THREE.Matrix4().multiplyMatrices(kit.rest[b], mountMatrix(p.mount)), b };
}

function procGeometry(kit, pr) {
  const donor = kit.pieces[pr.piece];
  if (!donor) return null;
  const a = buildProc(pr.shape, pr.look, painter(kit, pr.roles, pr.look && (pr.look.t || 0) === 0), { flip: HANGING.has(pr.shape) || pr.shape.startsWith('staff_') });
  if (!a) return null;
  const { M, b } = frameOf(kit, pr.piece);
  return skinTo(toGeometry(a).applyMatrix4(M), b);
}

// ---- add-ons: where on a piece each one sits ----
// a piece's triangles in its own frame (cached), for finding its spots
function shapeOf(kit, name) {
  let s = kit.shapes.get(name);
  if (s) return s;
  const g = kit.geo.get(name);
  if (!g) return null;
  const pos = g.attributes.position, inv = frameOf(kit, name).M.invert();
  const p = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) _v.fromBufferAttribute(pos, i).applyMatrix4(inv).toArray(p, i * 3);
  s = { p, index: g.index.array, box: new THREE.Box3().setFromArray(p) };
  kit.shapes.set(name, s);
  return s;
}

// how far a ray from o along d travels before it meets the shape (null: it never does)
export function cast(s, o, d) {
  const { p, index } = s;
  let best = null;
  for (let i = 0; i < index.length; i += 3) {
    const a = index[i] * 3, b = index[i + 1] * 3, c = index[i + 2] * 3;
    const e1x = p[b] - p[a], e1y = p[b + 1] - p[a + 1], e1z = p[b + 2] - p[a + 2];
    const e2x = p[c] - p[a], e2y = p[c + 1] - p[a + 1], e2z = p[c + 2] - p[a + 2];
    const hx = d[1] * e2z - d[2] * e2y, hy = d[2] * e2x - d[0] * e2z, hz = d[0] * e2y - d[1] * e2x;
    const det = e1x * hx + e1y * hy + e1z * hz;
    if (Math.abs(det) < 1e-10) continue;
    const f = 1 / det, sx = o[0] - p[a], sy = o[1] - p[a + 1], sz = o[2] - p[a + 2];
    const u = f * (sx * hx + sy * hy + sz * hz);
    if (u < 0 || u > 1) continue;
    const qx = sy * e1z - sz * e1y, qy = sz * e1x - sx * e1z, qz = sx * e1y - sy * e1x;
    const v = f * (d[0] * qx + d[1] * qy + d[2] * qz);
    if (v < 0 || u + v > 1) continue;
    const t = f * (e2x * qx + e2y * qy + e2z * qz);
    if (t > 0 && (best === null || t < best)) best = t;
  }
  return best;
}

const FAR = 6;
export const MASK_AT = 0.3;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const mid = (box, k) => (box.min[k] + box.max[k]) / 2;
// each spot from the piece's shape, in its frame: what the builder needs (procgear.js ADDONS)
export const SPOTS = {
  // past the end of the grip, below the hand
  pommel(s) {
    const r = clamp((s.box.max.x - s.box.min.x) * 0.15, 0.05, 0.09);
    return { p: [0, s.box.min.y - r * 0.5, 0], r };
  },
  // the middle of a shield's face (it looks along +z, away from the hand)
  front(s) {
    const x = mid(s.box, 'x'), y = mid(s.box, 'y'), hit = cast(s, [x, y, FAR], [0, 0, -1]);
    const r = (s.box.max.x - s.box.min.x) * 0.16;
    return { p: [x, y, (hit == null ? s.box.max.z : FAR - hit) - r * 0.12], r };
  },
  // along the crown of a helm, front to back
  top(s) {
    const x = mid(s.box, 'x'), z = mid(s.box, 'z'), hit = cast(s, [x, FAR, z], [0, -1, 0]);
    return { p: [x, (hit == null ? s.box.max.y : FAR - hit) - 0.03, z], r: (s.box.max.z - s.box.min.z) * 0.3 };
  },
  // round the top of a head (a body part: the rig's frame)
  crown(s, ad) {
    // a crown on top, a circlet lower, round the brow
    // a hat (gearlook.js HATS) sits at the brow, as a circlet does
    // a face mask sits across the mouth, a third of the way up the head
    const y = ad.mask ? s.box.min.y + (s.box.max.y - s.box.min.y) * MASK_AT : s.box.max.y - (ad.variant === 'circlet' || ad.hat ? 0.36 : 0.27), z = mid(s.box, 'z'), x = mid(s.box, 'x');
    const across = (o, d, fallback) => { const h = cast(s, o, d); return h == null ? fallback : h; };
    const x1 = FAR - across([FAR, y, z], [-1, 0, 0], FAR - s.box.max.x), x0 = across([-FAR, y, z], [1, 0, 0], FAR + s.box.min.x) - FAR;
    const z1 = FAR - across([x, y, FAR], [0, 0, -1], FAR - s.box.max.z), z0 = across([x, y, -FAR], [0, 0, 1], FAR + s.box.min.z) - FAR;
    return { p: [(x0 + x1) / 2, y, (z0 + z1) / 2], r: (x1 - x0) / 2 + 0.03, rz: (z1 - z0) / 2 + 0.03 };
  },
  // the middle of a cloak's back (its outside looks along -z), leaning as the cloth does
  back(s) {
    const x = mid(s.box, 'x'), y = s.box.min.y + (s.box.max.y - s.box.min.y) * 0.56;
    const r = (s.box.max.x - s.box.min.x) * 0.19;
    const zAt = yy => { const h = cast(s, [x, yy, -FAR], [0, 0, 1]); return h == null ? s.box.min.z : h - FAR; };
    const zt = zAt(y + r), zb = zAt(y - r);
    return { p: [x, y, zAt(y) + 0.004], r, lean: (zt - zb) / (2 * r) };
  },
  // on top of the upper arm, beside the neck (an arm: the rig's frame, the arm out along x)
  shoulder(s, ad) {
    const side = ad.side || 1, x = side * 0.33;
    const top = cast(s, [x, FAR, 0], [0, -1, 0]);
    const y = top == null ? s.box.max.y : FAR - top;
    const front = cast(s, [x, y - 0.1, FAR], [0, 0, -1]);
    const r = clamp((front == null ? 0.12 : FAR - front) + 0.06, 0.17, 0.22);
    return { p: [x, y - 0.01, 0], r, side };
  },
};
// where a lantern hangs: at the hip, a little out and forward, smaller than held
const HIP = new THREE.Matrix4().compose(new THREE.Vector3(0.42, 0.22, 0.16), new THREE.Quaternion(), new THREE.Vector3(0.7, 0.7, 0.7));

function addonGeometry(kit, plan, ad) {
  const on = ad.on && kit.pieces[ad.on] ? ad.on : null;
  const paint = painter(kit, ad.roles, false);
  let a, M, b, b2 = null;
  if (ad.spot === 'hip') {
    // hung from a bone (in its frame), not set on a piece
    b = kit.boneIndex.get(boneKey(ad.bone || 'hips'));
    if (b == null) return null;
    a = ad.shape ? buildProc(ad.kind, {}, paint) : buildAddon(ad.kind, {}, paint);
    M = new THREE.Matrix4().copyPosition(kit.rest[b]).multiply(HIP);
  } else {
    const s = on && shapeOf(kit, on);
    const spot = SPOTS[ad.spot];
    if (!s || !spot) return null;
    const at = { ...spot(s, ad), spikes: ad.spikes, variant: ad.variant, motif: ad.motif };
    a = buildAddon(ad.kind, at, paint);
    const f = frameOf(kit, on);
    M = f.M;
    b = f.b != null ? f.b : kit.boneIndex.get(boneKey(ad.bone));
    // a pauldron rides between the arm and the chest, so it stays on the shoulder as the arm moves
    if (ad.spot === 'shoulder') b2 = kit.boneIndex.get('chest');
  }
  if (!a || b == null) return null;
  const g = toGeometry(a).applyMatrix4(M);
  const fitted = on && plan.props.find(p => p.name === on && p.fit);
  if (fitted) fitTo(g, fitted.fit, kit.pieces[on].bone, kit);
  return skinTo(g, b, b2);
}

// one merged geometry for a plan (shared by everyone who looks the same)
export function assemble(kit, plan) {
  const hit = kit.cache.get(plan.key);
  if (hit) { kit.cache.delete(plan.key); kit.cache.set(plan.key, hit); return hit; }
  const parts = [];
  for (const it of plan.props) {
    const src = kit.geo.get(it.name);
    if (!src) continue;
    const remap = it.remap && Object.keys(it.remap).length ? it.remap : null;
    if (!remap && !it.fit) { parts.push(src); continue; }
    const g = src.clone();
    if (remap) recolour(g, remap, kit.N);
    if (it.fit) fitTo(g, it.fit, kit.pieces[it.name].bone, kit);
    parts.push(g);
  }
  for (const pr of plan.procs) { const g = procGeometry(kit, pr); if (g) parts.push(g); }
  for (const ad of plan.addons || []) {
    try { const g = addonGeometry(kit, plan, ad); if (g) parts.push(g); } catch (err) { console.warn('equip addon', ad.kind, err); }
  }
  const merged = mergeGeometries(parts, false);
  kit.cache.set(plan.key, merged);
  while (kit.cache.size > CACHE_MAX) {
    const [k, old] = kit.cache.entries().next().value;
    kit.cache.delete(k);
    old.dispose();
  }
  return merged;
}

// ---- glow: the '~glow' columns light themselves ----
// one texel per palette column, lit where the column glows
function glowMask(kit) {
  const data = new Uint8Array(kit.N * 4);
  kit.columns.forEach((c, i) => { if (String(c.name).endsWith('~glow')) data[i * 4] = data[i * 4 + 3] = 255; });
  const tex = new THREE.DataTexture(data, kit.N, 1);
  tex.magFilter = tex.minFilter = THREE.NearestFilter;
  tex.needsUpdate = true;
  return tex;
}
// an actor's own material: the kit's, plus its glow (uGlow: 0 dark, 1 lit, more for a legendary).
// Not material.emissive, which hit flashes (fx.tint) borrow.
function dressedMaterial(kit) {
  const mat = kit.material.clone();
  const uGlow = { value: 0 };
  mat.onBeforeCompile = shader => {
    shader.uniforms.uGlow = uGlow;
    shader.uniforms.uGlowMask = { value: kit.glowMask };
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform float uGlow;\nuniform sampler2D uGlowMask;')
      .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
#ifdef USE_MAP
  totalEmissiveRadiance += diffuseColor.rgb * texture2D(uGlowMask, vec2(vMapUv.x, 0.5)).r * uGlow;
#endif`);
  };
  mat.customProgramCacheKey = () => '|equipglow';
  mat.userData.glow = uGlow;
  return mat;
}

// a dressed character: its own bones, one mesh, the shared clips
export async function spawnDressed(look, cls, opts = {}) {
  const [kit, clips] = await Promise.all([loadEquipKit(), loadAnims()]);
  const root = new THREE.Group();
  const rig = cloneBones(kit.rigNode);
  root.add(rig);
  const byName = new Map();
  rig.traverse(o => byName.set(o.name, o));
  const skeleton = new THREE.Skeleton(kit.boneNames.map(n => byName.get(n)), kit.inverses.map(m => m.clone()));
  const plan = planLook(look, cls, kit);
  const material = dressedMaterial(kit);
  const mesh = new THREE.SkinnedMesh(assemble(kit, plan), material);
  mesh.bind(skeleton, new THREE.Matrix4());
  mesh.castShadow = mesh.receiveShadow = true;
  // skinned bounds would lag the pose: a fixed, generous sphere lets it be culled off-screen
  mesh.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 1.1, 0), 3.2);   // a swung greatsword included
  mesh.name = 'dressed';
  root.add(mesh);
  const actor = new Actor(root, clips);
  actor.gear = { kit, mesh, plan, cls, sig: look && look.sig, glow: material.userData.glow, scale: opts.scale || 1 };
  // (a hero's lantern burns whatever they wear: gearlook.js plan.lantern)
  material.userData.glow.value = Math.max(plan.glow || 0, plan.lantern ? 1 : 0);
  actor.idle = plan.idle;
  shape(actor);
  return actor;
}

// the body's build (its race's height and breadth) times the scale it was asked for
function shape(actor) {
  const g = actor.gear, b = g.plan.build || { h: 1, w: 1 };
  actor.root.scale.set(g.scale * b.w, g.scale * b.h, g.scale * b.w);
}

// put a dressed actor into another look; false when nothing changed
export function dress(actor, look, cls) {
  const g = actor && actor.gear;
  if (!g) return false;
  const sig = look && look.sig;
  if (sig === g.sig && cls === g.cls) return false;
  const plan = planLook(look, cls, g.kit);
  g.mesh.geometry = assemble(g.kit, plan);
  Object.assign(g, { plan, sig, cls });
  g.glow.value = plan.glow;
  actor.idle = plan.idle;
  shape(actor);
  return true;
}
