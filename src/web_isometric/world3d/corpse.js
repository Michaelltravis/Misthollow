// The dead, on the ground: a creature that dies falls where it stood and stays there as its
// corpse (the map payload's "corpse of <whoever>", loot.js), darkened, over a stain, under the
// gold ring that says it can be looted. A body with a death clip plays it and holds its last
// frame; one without (code-built bodies, props, creatures whose pack has no death) tips over onto
// its side. A hero's corpse, or anything with no body to draw, gets a grave: a mound of earth,
// a few stones and a wooden marker.
import * as THREE from 'three';

// "corpse of the goblin" -> "the goblin"
export const victimOf = name => String(name || '').replace(/^\s*(the\s+)?corpse\s+of\s+/i, '').trim();
// how a name is compared with a creature's ("The Goblin" is "goblin")
export const nameKey = s => String(s || '').toLowerCase().replace(/^(a|an|the)\s+/, '').trim();

// a body that has a real death clip (not one the creature's alias falls back to idle for)
function deathClip(actor) {
  if (!actor || !actor.mixer || typeof actor.action !== 'function') return null;
  if (actor.alias && actor.alias.Death_A === actor.alias.Idle) return null;
  return actor.action('Death_A');
}

// Start a body's fall; returns {update(dt) -> still falling?}. `ground` is the floor's height.
export function fallOver(actor, { ground = 0, side = 1 } = {}) {
  const root = actor.root;
  const clip = deathClip(actor);
  // only a small body that ends its death still standing goes over: a dragon's or a giant's own
  // death leaves it as it should lie (tipping one turned it on its back)
  root.updateMatrixWorld(true);
  const b0 = new THREE.Box3().setFromObject(root);
  const tip = !isFinite(b0.min.y) || b0.max.y - b0.min.y < TIP_BELOW;
  if (clip) {
    actor.mixer.stopAllAction();
    clip.reset();
    clip.setLoop(THREE.LoopOnce, 1);
    clip.clampWhenFinished = true;
    clip.timeScale = 1;
    clip.play();
    let left = clip.getClip().duration + 0.05;
    return {
      update(dt) {
        if (left <= 0) return false;
        actor.mixer.update(Math.min(dt, left));
        left -= dt;
        if (root.position.y > ground) root.position.y = Math.max(ground, root.position.y - dt * 3);   // a flyer drops
        if (left <= 0) settle(root, ground, tip);
        return left > 0;
      },
    };
  }
  // a small body built in code (proc.js, kin.js, a prop) has a death of its own, which it holds;
  // a big one (a dragon) goes over whole below, legs and all: its own death rolls only the torso
  if (!actor.mixer && tip && typeof actor.once === 'function' && typeof actor.update === 'function') {
    let left = (actor.once('Death_A') || 1) + 0.05;
    foldWings(root);
    return {
      update(dt) {
        if (left <= 0) return false;
        actor.update(Math.min(dt, left));
        left -= dt;
        if (root.position.y > ground) root.position.y = Math.max(ground, root.position.y - dt * 3);
        if (left <= 0) settle(root, ground, tip);
        return left > 0;
      },
    };
  }
  // no death at all (or a big code-built body): tip over onto one side and drop to the floor
  if (!actor.mixer) foldWings(root);
  const from = root.rotation.z, to = side * Math.PI / 2, y0 = root.position.y;
  let t = 0;
  const T = 0.55;
  return {
    update(dt) {
      if (t >= T) return false;
      t = Math.min(T, t + dt);
      const k = t / T, e = k * k;                       // falling: slow, then fast
      root.rotation.z = from + (to - from) * e;
      root.position.y = y0 + (ground - y0) * e;
      if (t >= T) settle(root, ground);
      return t < T;
    },
  };
}

// a creature built in code dies on its side: its wings (kin.js marks them) fold up over its back,
// so they lie along it instead of one spearing the floor and the other the sky
export function foldWings(root) {
  root.traverse(o => { const s = o.userData && o.userData.wing; if (s) o.rotation.z = s * Math.PI * 0.45; });
}

// rest a fallen body on the floor: nothing below it, nothing floating above it; one still
// standing after its death (a bat's folded wings, a beetle's crouch) goes over onto its side
export const TIP_BELOW = 1.6;     // metres standing: smaller bodies still upright after their death go over
// a body's own bounds, without its wings (kin.js marks them): a dead dragon rests on its flank, and
// a wing that would prop it up passes under the floor instead
export function bodyBox(root) {
  root.updateMatrixWorld(true);
  const box = new THREE.Box3(), part = new THREE.Box3();
  const walk = o => {
    if (o.userData && o.userData.wing) return;
    if (o.isMesh) box.union(part.setFromObject(o));
    for (const c of o.children) walk(c);
  };
  walk(root);
  return box.isEmpty() ? new THREE.Box3().setFromObject(root) : box;
}

export function settle(root, ground = 0, tip = true) {
  let box = bodyBox(root);
  if (!isFinite(box.min.y)) return;
  const h = box.max.y - box.min.y, len = Math.max(box.max.x - box.min.x, box.max.z - box.min.z);
  if (tip && h > len * 0.9 && Math.abs(root.rotation.z) < 0.5) {
    root.rotation.z += Math.PI / 2;
    box = bodyBox(root);
  }
  root.position.y += ground - box.min.y + 0.01;
}

// darken a body (its own copies of the materials: the living keep theirs); returns the copies
export function deaden(root, k = 0.82, grey = 0.2) {
  const made = [];
  root.traverse(o => {
    if (!o.isMesh || !o.material) return;
    const one = m => {
      const c = m.clone();
      if (c.color) {
        // a little greyer and a little darker: the dead keep their colours
        const l = c.color.r * 0.299 + c.color.g * 0.587 + c.color.b * 0.114;
        c.color.lerp(new THREE.Color(l, l, l), grey).multiplyScalar(k);
      }
      if (c.emissive) c.emissive.multiplyScalar(0.2);
      made.push(c);
      return c;
    };
    o.material = Array.isArray(o.material) ? o.material.map(one) : one(o.material);
  });
  return made;
}

// how big a body lies: the radius of its footprint on the floor
export function footprint(root) {
  const box = bodyBox(root);
  if (!isFinite(box.min.x)) return 0.6;
  return Math.max(0.35, Math.min(2.5, Math.max(box.max.x - box.min.x, box.max.z - box.min.z) / 2));
}

let stainTex = null;
function stainTexture() {
  if (stainTex) return stainTex;
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(32, 32, 2, 32, 32, 31);
  grd.addColorStop(0, 'rgba(40,12,8,0.85)');
  grd.addColorStop(0.55, 'rgba(36,14,10,0.55)');
  grd.addColorStop(1, 'rgba(30,16,12,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, 64, 64);
  stainTex = new THREE.CanvasTexture(c);
  stainTex.colorSpace = THREE.SRGBColorSpace;
  return stainTex;
}

// a dark stain on the floor under a body (its geometry and material are its own)
export function stain(r) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(r * 2.2, r * 1.7), new THREE.MeshBasicMaterial({
    map: stainTexture(), transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }));
  m.rotation.x = -Math.PI / 2;
  m.position.y = 0.02;
  m.userData.own = true;
  return m;
}

// a grave: a low mound of earth, a few stones round it and a wooden marker at its head
export function grave(rng = Math.random) {
  const g = new THREE.Group();
  const earth = new THREE.MeshStandardMaterial({ color: 0x4b3a2c, roughness: 1 });
  const mound = new THREE.Mesh(new THREE.SphereGeometry(0.5, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), earth);
  mound.scale.set(0.75, 0.38, 1.25);
  mound.castShadow = mound.receiveShadow = true;
  g.add(mound);
  const rock = new THREE.MeshStandardMaterial({ color: 0x7a766c, roughness: 0.9, flatShading: true });
  for (let i = 0; i < 7; i++) {
    const a = (i / 7) * Math.PI * 2 + rng() * 0.4;
    const r = 0.08 + rng() * 0.07;
    const s = new THREE.Mesh(new THREE.DodecahedronGeometry(r, 0), rock);
    s.position.set(Math.cos(a) * 0.44, r * 0.5, Math.sin(a) * 0.7);       // half sunk in the earth
    s.rotation.set(rng() * 3, rng() * 3, rng() * 3);
    s.castShadow = true;
    g.add(s);
  }
  const wood = new THREE.MeshStandardMaterial({ color: 0x6b4a2e, roughness: 0.9 });
  const post = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.75, 0.08), wood);
  post.position.set(0, 0.37, -0.72);
  const bar = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.07, 0.07), wood);
  bar.position.set(0, 0.55, -0.72);
  post.rotation.z = bar.rotation.z = (rng() - 0.5) * 0.15;      // leaning a little
  post.castShadow = bar.castShadow = true;
  g.add(post, bar);
  g.traverse(o => { o.userData.own = true; });
  return g;
}

// how a creature dies, by what it is: a spirit fades away, a slime bursts, a creature of fire burns
// to ash, a thing of stone or ice shatters; anything else falls (fallOver)
const BURN = /\b(fire|flame|flaming|magma|lava|ember|inferno|imp|demon|demonic|efreet|ifrit|salamander|phoenix|hellhound|balor)\b/i;
const DISSOLVE = /\b(ghost|ghostly|spirit|wraith|spectre|specter|spectral|phantom|shade|wisp|banshee|apparition|poltergeist|haunt|soul|lich|vampire|wight|revenant|shadow)\b/i;
const BURST = /\b(slime|ooze|jelly|blob|pudding|mold|mould|fungus|myconid|amoeba|gelatinous|leech|maggot|cube)\b/i;
const SHATTER = /\b(golem|elemental|gargoyle|statue|crystal|construct|animated|stone|ice|frost|iron|clay)\b/i;
export function deathStyle(...names) {
  const s = names.filter(Boolean).join(' ');
  if (BURN.test(s)) return 'burn';
  if (DISSOLVE.test(s)) return 'dissolve';
  if (BURST.test(s)) return 'burst';
  if (SHATTER.test(s)) return 'shatter';
  return 'fall';
}

// what one that did not fall leaves for its corpse: a heap of ash, a puddle of goo, a scatter of
// rubble, a faint pool of light where a spirit was
export function remains(style, at) {
  const g = new THREE.Group();
  g.position.copy(at);
  const add = (geo, color, x, z, sy, extra = {}) => {
    const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color, roughness: 0.9, flatShading: true, ...extra }));
    m.position.set(x, 0, z); m.scale.y = sy; g.add(m); return m;
  };
  if (style === 'burst') add(new THREE.SphereGeometry(0.55, 14, 6, 0, Math.PI * 2, 0, Math.PI / 2), 0x5aa82a, 0, 0, 0.12, { roughness: 0.25, transparent: true, opacity: 0.85 });
  else if (style === 'shatter') for (let i = 0; i < 7; i++) add(new THREE.DodecahedronGeometry(0.12 + (i % 3) * 0.06, 0), 0x8a8478, Math.cos(i * 2.1) * 0.45, Math.sin(i * 2.1) * 0.45, 1);
  else if (style === 'dissolve') add(new THREE.CircleGeometry(0.5, 24).rotateX(-Math.PI / 2).translate(0, 0.02, 0), 0xbfe0ff, 0, 0, 1, { emissive: 0x6a9acc, emissiveIntensity: 0.6, transparent: true, opacity: 0.55 });
  else add(new THREE.ConeGeometry(0.42, 0.3, 9).translate(0, 0.15, 0), 0x3a3634, 0, 0, 1);
  return g;
}
