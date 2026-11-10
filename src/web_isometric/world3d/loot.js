// What lies on the ground around the hero (the map payload's `nearby[].items`): a corpse is the
// body of whoever died, lying where they fell (or, come upon later, on the room's spot for it),
// darkened over a stain, under a slow gold ring (corpse.js); a hero's corpse is a grave. Anything
// else is its painted icon (shared/items.js) bobbing over a ring in its rarity's colour. Click one to walk over and take it (a corpse: loot it);
// right-click for more. Each sits on one of its room's free spots, the same spot every time.
import * as THREE from 'three';
import { groundItems } from './lootlogic.js';
import { freeBody } from './freebody.js';
import { victimOf, fallOver, deaden, footprint, stain, grave, bodyBox } from './corpse.js';

const RING_MAX = 1.4;     // a corpse's ring, however big the body (a dragon's filled the room)
const RARITY = { common: 0xb8b0a0, uncommon: 0x6fd06f, rare: 0x5aa8ff, epic: 0xc07aff, legendary: 0xffa640, set: 0x5fe0c8 };

function groundRing(color, inner, outer, opacity) {
  const m = new THREE.Mesh(new THREE.RingGeometry(inner, outer, 40), new THREE.MeshBasicMaterial({
    color, transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
  m.rotation.x = -Math.PI / 2;
  m.position.y = 0.03;
  return m;
}

// a beam of light over loot worth seeing from afar: taller the rarer (uncommon and up)
const BEAM_H = { uncommon: 1.2, rare: 1.9, epic: 2.6, legendary: 3.4, set: 2.6 };
const BEAM_GEO = new THREE.CylinderGeometry(0.05, 0.16, 1, 10, 1, true).translate(0, 0.5, 0);
const beamMats = new Map();
export function rarityBeam(rarity) {
  const h = BEAM_H[rarity];
  if (!h) return null;
  let m = beamMats.get(rarity);
  if (!m) { m = new THREE.MeshBasicMaterial({ color: RARITY[rarity], transparent: true, opacity: 0.32, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }); beamMats.set(rarity, m); }
  const b = new THREE.Mesh(BEAM_GEO, m);
  b.scale.set(1, h, 1);
  b.renderOrder = 3;
  return b;
}
const RANK = ['common', 'uncommon', 'rare', 'epic', 'legendary'];
// the finest thing a corpse holds (its beam shows when that is rare or better)
export function bestRarity(items) {
  let best = -1, set = false;
  for (const it of items || []) { if (it.set_id) set = true; best = Math.max(best, RANK.indexOf(it.rarity || 'common')); }
  return set ? 'set' : best >= 2 ? RANK[best] : null;
}

export class GroundLoot {
  // slot(vnum, key) -> a free spot in that room (Entities.slot); icon(item) -> a canvas;
  // claim(name) -> the body of a creature that just fell (Entities.claimFallen); body(name, key)
  // -> a Promise of a body for one (Entities.body); hero(name) -> is that a player's name
  constructor(engine, { slot, icon, claim = () => null, body = null, hero = () => false }) {
    this.engine = engine; this.slot = slot; this.icon = icon;
    this.claim = claim; this.bodyFor = body; this.isHero = hero;
    this.list = new Map();
    this._v = new THREE.Vector3();
  }

  sync(payload) {
    if (!payload || !Array.isArray(payload.nearby)) return;
    const want = new Map(groundItems(payload).map(g => [g.key, g]));
    for (const [key, l] of this.list) if (!want.has(key)) this.remove(l);
    for (const [key, g] of want) {
      const l = this.list.get(key);
      if (l) { l.item = g.item; l.kw = g.kw; continue; }
      const at = this.slot(g.vnum, g.key);
      if (at) this.add(g, at);
    }
  }

  add(g, at) {
    const root = new THREE.Group();
    root.position.copy(at);
    if (g.corpse) return this.addCorpse(g, at, root);
    const canvas = this.icon(g.item);
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    const bob = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
    bob.scale.set(0.55, 0.55, 1);
    bob.position.y = 0.6;
    root.add(bob, groundRing(RARITY[g.item.rarity] || RARITY.common, 0.32, 0.42, 0.7));
    // something worth stooping for shows from across the room: a beam of its rarity's light
    const beam = rarityBeam(g.item.set_id ? 'set' : g.item.rarity);
    if (beam) root.add(beam);
    root.userData.loot = g.key;
    this.engine.scene.add(root);
    this.list.set(g.key, { ...g, root, bob, phase: Math.random() * 6.28 });
  }

  // a corpse: the body that fell (kept where it lies), a body made for it lying on its spot, or
  // a hero's grave; a stain under it and the gold ring round it (always root's last child)
  addCorpse(g, at, root) {
    const victim = victimOf(g.item.name || g.item.short);
    const l = { ...g, root, bob: null, phase: Math.random() * 6.28, body: null, fall: null, mats: [] };
    root.userData.loot = g.key;
    this.list.set(g.key, l);
    // a corpse holding something rare or better: its beam (before the ring, which stays last)
    const best = bestRarity(g.item.contents);
    if (best) root.add(rarityBeam(best));
    const lay = (body, fall) => {
      l.body = body; l.fall = fall;
      l.mats = deaden(body);
      root.position.y = at.y;
      this.marks(l);
      this.engine.scene.add(root);
    };
    const toGrave = () => {
      root.add(grave(), groundRing(0xffd27a, 0.85, 0.96, 0.5));
      this.engine.scene.add(root);
    };
    if (this.isHero(victim)) { toGrave(); return; }
    const fell = this.claim(victim);
    if (fell) { lay(fell.root, fell.fall); return; }
    if (!this.bodyFor) { toGrave(); return; }
    // come upon later: a body for it, already lying on its spot
    this.bodyFor(victim, g.key).then(actor => {
      if (this.list.get(g.key) !== l) return;            // gone before it was made
      const body = actor.root;
      body.position.copy(at);
      body.rotation.y = (g.key.length * 1.7) % 6.28;
      this.engine.scene.add(body);
      const fall = fallOver(actor, { ground: at.y, side: g.key.length % 2 ? 1 : -1 });
      for (let i = 0; i < 40 && fall.update(0.25);) i++;
      lay(body, null);
    }).catch(() => { if (this.list.get(g.key) === l) toGrave(); });
  }

  // the stain and the ring under a body, sized and centred on it as it lies now (again once it
  // has finished falling: a dragon standing is not the dragon lying down), the ring last
  marks(l) {
    for (const m of [l.stainMesh, l.ringMesh]) if (m) { l.root.remove(m); m.geometry.dispose(); m.material.dispose(); }
    const box = bodyBox(l.body);
    if (isFinite(box.min.x)) l.root.position.set((box.min.x + box.max.x) / 2, l.root.position.y, (box.min.z + box.max.z) / 2);
    const r = Math.min(RING_MAX, footprint(l.body));
    l.stainMesh = stain(r);
    l.ringMesh = groundRing(l.key === this.marked ? 0xfff4d6 : 0xffd27a, r + 0.15, r + 0.26, 0.5);
    l.root.add(l.stainMesh, l.ringMesh);
  }

  // the corpse Tab aimed at (main.js): its ring brighter and paler, pulsing (null: none)
  mark(key) {
    for (const l of this.list.values()) if (l.ringMesh) l.ringMesh.material.color.set(l.key === key ? 0xfff4d6 : 0xffd27a);
    this.marked = key || null;
  }

  remove(l) {
    if (l.body) { this.engine.scene.remove(l.body); freeBody(l.body); }
    for (const m of l.mats || []) m.dispose();
    this.engine.scene.remove(l.root);
    l.root.traverse(o => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) { if (o.material.map) o.material.map.dispose(); o.material.dispose(); }
    });
    this.list.delete(l.key);
  }

  clear() { for (const l of [...this.list.values()]) this.remove(l); }

  // the ground item under a screen point, or null: the nearest whose mark is within a
  // finger's width of it on screen (an icon is small, and the camera is often moving)
  pick(x, y, canvas) {
    if (!this.list.size) return null;
    const r = canvas.getBoundingClientRect();
    const cam = this.engine.camera;
    let best = null, bestD = Infinity;
    for (const l of this.list.values()) {
      const v = this._v.copy(l.root.position).setY(l.corpse ? 0.15 : 0.6).project(cam);
      if (v.z > 1) continue;                                   // behind the camera
      const sx = r.left + (v.x + 1) / 2 * r.width, sy = r.top + (1 - v.y) / 2 * r.height;
      const d = Math.hypot(sx - x, sy - y);
      if (d < (l.corpse ? 46 : 34) && d < bestD) { best = l; bestD = d; }
    }
    return best;
  }

  update(dt, t) {
    for (const l of this.list.values()) {
      if (l.fall && !l.fall.update(dt)) { l.fall = null; this.marks(l); }     // a body still falling; then where it lies
      if (l.bob) l.bob.position.y = 0.6 + Math.sin(t * 2.2 + l.phase) * 0.08;
      const ring = l.root.children[l.root.children.length - 1];
      if (ring && ring.material) ring.material.opacity = l.key === this.marked ? 0.85 + Math.sin(t * 6) * 0.15
        : (l.corpse ? 0.35 : 0.5) + Math.sin(t * 3 + l.phase) * 0.2;
    }
  }
}
