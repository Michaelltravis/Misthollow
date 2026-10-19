// Herb patches and ore veins out in the world (nodes.py; the map payload's nearby rooms carry
// `node`: its kind, where in the room, whether it is ready): a herb patch is a low green clump
// starred with bright flowers, an ore vein a grey boulder shot with metal; a ready one glints now
// and then, a worked one sits dull until it comes back. Clicked, the hero walks over and
// forages or mines it (main.js).
import * as THREE from 'three';

function herbPatch() {
  const g = new THREE.Group();
  const leaf = new THREE.MeshStandardMaterial({ color: 0x3f7a2e, roughness: 0.9, flatShading: true });
  for (let i = 0; i < 6; i++) {
    const m = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.5, 5), leaf);
    m.position.set(Math.cos(i * 1.05) * 0.18, 0.22, Math.sin(i * 1.05) * 0.18);
    m.rotation.set(Math.sin(i) * 0.4, 0, Math.cos(i) * 0.4);
    g.add(m);
  }
  const petal = new THREE.MeshStandardMaterial({ color: 0xe86ad8, emissive: 0x8a2a80, emissiveIntensity: 0.6, roughness: 0.5 });
  for (let i = 0; i < 4; i++) {
    const f = new THREE.Mesh(new THREE.SphereGeometry(0.06, 6, 4), petal);
    f.position.set(Math.cos(i * 1.6 + 0.4) * 0.16, 0.48, Math.sin(i * 1.6 + 0.4) * 0.16);
    g.add(f);
  }
  g.userData.glow = [petal];
  return g;
}

function oreVein() {
  const g = new THREE.Group();
  const rock = new THREE.MeshStandardMaterial({ color: 0x6e6a64, roughness: 0.95, flatShading: true });
  const b = new THREE.Mesh(new THREE.DodecahedronGeometry(0.5, 0).scale(1.2, 0.75, 1), rock);
  b.position.y = 0.3;
  g.add(b);
  const metal = new THREE.MeshStandardMaterial({ color: 0xd8a84a, emissive: 0x6a4a10, emissiveIntensity: 0.5, metalness: 0.8, roughness: 0.3, flatShading: true });
  for (let i = 0; i < 5; i++) {
    const s = new THREE.Mesh(new THREE.OctahedronGeometry(0.09, 0), metal);
    s.position.set(Math.cos(i * 1.3) * 0.42, 0.25 + (i % 3) * 0.13, Math.sin(i * 1.3) * 0.3);
    g.add(s);
  }
  g.userData.glow = [metal];
  return g;
}

export class GatherNodes {
  // zone() -> the Zone (rooms with ox, oz); fx (particles)
  constructor(engine, zone, fx) {
    this.engine = engine; this.zone = zone; this.fx = fx;
    this.list = new Map();       // vnum -> {root, kind, ready, x, z}
    this._v = new THREE.Vector3();
    this.sparkT = 0;
  }

  sync(payload) {
    if (!payload || !Array.isArray(payload.nearby)) return;
    const Z = this.zone();
    if (!Z) return;
    const seen = new Set();
    for (const r of payload.nearby) {
      if (!r.node) continue;
      const room = Z.rooms.get(r.vnum);
      if (!room) continue;
      seen.add(r.vnum);
      let n = this.list.get(r.vnum);
      if (!n) {
        const root = r.node.k === 'ore' ? oreVein() : herbPatch();
        root.position.set(room.ox + r.node.x, 0, room.oz + r.node.z);
        root.rotation.y = (r.vnum * 1.7) % 6.28;
        root.userData.node = r.vnum;
        this.engine.scene.add(root);
        n = { root, kind: r.node.k, vnum: r.vnum, ready: null };
        this.list.set(r.vnum, n);
      }
      if (n.ready !== !!r.node.ready) {
        n.ready = !!r.node.ready;
        for (const m of n.root.userData.glow) m.emissiveIntensity = n.ready ? 0.6 : 0;
        n.root.scale.setScalar(n.ready ? 1 : 0.8);
      }
    }
    for (const [v, n] of this.list) if (!seen.has(v)) { this.engine.scene.remove(n.root); this.list.delete(v); }
  }

  clear() { for (const n of this.list.values()) this.engine.scene.remove(n.root); this.list.clear(); }

  // a ready one glints now and then
  update(dt) {
    if ((this.sparkT -= dt) > 0) return;
    this.sparkT = 0.35;
    for (const n of this.list.values()) {
      if (!n.ready || Math.random() > 0.5) continue;
      const p = n.root.position;
      this.fx.p.emit(this._v.set(p.x + (Math.random() - 0.5) * 0.6, 0.5 + Math.random() * 0.3, p.z + (Math.random() - 0.5) * 0.6),
        { count: 1, color: n.kind === 'ore' ? 0xffe08a : 0xffb8f0, bright: 2.2, speed: 0.1, up: 0.3, life: 0.7, size: 0.14, drag: 1 });
    }
  }

  // the one under the pointer (screen x, y), as loot.js picks
  pick(x, y, canvas) {
    if (!this.list.size) return null;
    const r = canvas.getBoundingClientRect();
    let best = null, bestD = 40;
    for (const n of this.list.values()) {
      const v = this._v.copy(n.root.position).setY(0.4).project(this.engine.camera);
      if (v.z > 1) continue;
      const d = Math.hypot(r.left + (v.x + 1) / 2 * r.width - x, r.top + (1 - v.y) / 2 * r.height - y);
      if (d < bestD) { best = n; bestD = d; }
    }
    return best;
  }
}
