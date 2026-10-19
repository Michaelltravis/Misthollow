// Small life about the hero (docs/GAMEPLAY_POLISH.md, group 3), drawn by the client alone (no
// server creature: nothing to fight or follow): birds pecking on open ground by day that take
// wing when the hero comes near or a fight starts; fireflies over grass and marsh at night; now
// and then a fish leaping from water nearby, with a splash and its rings.
import * as THREE from 'three';

const BIRDS_ON = new Set(['forest', 'field', 'hills', 'village', 'stones', 'shore', 'camp', 'garden', 'swamp']);
const FIREFLIES_ON = new Set(['forest', 'darkforest', 'field', 'swamp', 'hills', 'garden', 'village', 'camp', 'stones']);
const SCARE = 3.6, GONE = 26;

// a little bird: a body, a head, two wings that flap
function makeBird(rnd) {
  const g = new THREE.Group();
  const col = [0x5a4a3a, 0x3a3a44, 0x8a6a4a, 0x2a2a2a, 0x6a5a48][Math.floor(rnd() * 5)];
  const mat = new THREE.MeshStandardMaterial({ color: col, roughness: 0.9, flatShading: true });
  const body = new THREE.Mesh(new THREE.SphereGeometry(0.09, 6, 4).scale(1, 0.8, 1.5), mat);
  body.position.y = 0.1;
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.055, 6, 4), mat);
  head.position.set(0, 0.17, 0.11);
  const beak = new THREE.Mesh(new THREE.ConeGeometry(0.018, 0.06, 4).rotateX(Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0xd8a040 }));
  beak.position.set(0, 0.16, 0.18);
  const wingGeo = new THREE.PlaneGeometry(0.18, 0.1).translate(0.09, 0, 0).rotateX(-Math.PI / 2);
  const wl = new THREE.Mesh(wingGeo, new THREE.MeshStandardMaterial({ color: col, side: THREE.DoubleSide, roughness: 0.9 }));
  const wr = wl.clone();
  wl.position.set(0.04, 0.13, 0); wr.position.set(-0.04, 0.13, 0); wr.rotation.y = Math.PI;
  g.add(body, head, beak, wl, wr);
  g.userData = { wl, wr, head };
  return g;
}

export class Wildlife {
  // fx (particles), ripples (weather.js), sound; water(x, z) -> is there open water there
  constructor(engine, fx, ripples, sound, water) {
    this.engine = engine; this.fx = fx; this.ripples = ripples; this.sound = sound; this.water = water;
    this.birds = [];
    this.flockT = 3;
    this.flyT = 0;
    this.fishT = 4;
    this.leap = null;
    this.where = { theme: 'field', open: false, night: false, box: null };
    const fish = new THREE.Group();
    const fm = new THREE.MeshStandardMaterial({ color: 0xc8a070, roughness: 0.4, metalness: 0.3, flatShading: true });
    fish.add(new THREE.Mesh(new THREE.SphereGeometry(0.12, 8, 5).scale(0.6, 0.6, 1.6), fm));
    const tail = new THREE.Mesh(new THREE.ConeGeometry(0.08, 0.14, 4).rotateX(-Math.PI / 2), fm);
    tail.position.z = -0.24;
    fish.add(tail);
    fish.visible = false;
    engine.scene.add(fish);
    this.fish = fish;
  }

  // where the hero is: the room's theme, open sky or not, night or day, the room's bounds
  set(theme, open, night, box) { this.where = { theme, open, night, box }; }

  update(dt, t, hero, fighting) {
    if (!hero) return;
    const w = this.where;
    // ---- birds ----
    const birdy = w.open && !w.night && BIRDS_ON.has(w.theme);
    if (birdy && !fighting && this.birds.length === 0 && (this.flockT -= dt) <= 0) this.flock(hero, w.box);
    for (let i = this.birds.length - 1; i >= 0; i--) {
      const b = this.birds[i], g = b.g, u = g.userData;
      const d = Math.hypot(g.position.x - hero.x, g.position.z - hero.z);
      if (!b.fly && (d < SCARE || fighting || !birdy)) {
        b.fly = true;
        const a = Math.atan2(g.position.x - hero.x, g.position.z - hero.z) + (Math.random() - 0.5) * 0.8;
        b.v = new THREE.Vector3(Math.sin(a) * (3 + Math.random() * 2), 2.4 + Math.random() * 1.5, Math.cos(a) * (3 + Math.random() * 2));
        g.rotation.y = a;
        if (i === 0) this.sound.play('flutter', { at: g.position });
      }
      if (b.fly) {
        b.v.y += dt * 0.8;
        g.position.addScaledVector(b.v, dt);
        const flap = Math.sin(t * 38 + i) * 0.9;
        u.wl.rotation.z = flap; u.wr.rotation.z = -flap;
        b.t += dt;
      } else {
        // pecking, hopping, turning
        b.t += dt;
        u.head.position.y = 0.17 - Math.max(0, Math.sin(t * 3 + b.seed * 9)) * 0.06;
        if (Math.random() < dt * 0.4) { g.rotation.y += (Math.random() - 0.5) * 2; g.position.x += Math.sin(g.rotation.y) * 0.12; g.position.z += Math.cos(g.rotation.y) * 0.12; }
      }
      if ((b.fly && b.t > 3.5) || d > GONE) {
        this.engine.scene.remove(g);
        this.birds.splice(i, 1);
        if (!this.birds.length) this.flockT = 18 + Math.random() * 25;
      }
    }
    // ---- fireflies: a soft glow drifting low, blinking out ----
    if (w.open && w.night && FIREFLIES_ON.has(w.theme) && (this.flyT -= dt) <= 0) {
      this.flyT = 0.09;
      const a = Math.random() * Math.PI * 2, r = 2 + Math.random() * 10;
      const p = new THREE.Vector3(hero.x + Math.cos(a) * r, 0.3 + Math.random() * 1.6, hero.z + Math.sin(a) * r);
      this.fx.p.emit(p, { count: 1, color: Math.random() < 0.5 ? 0xd8ff6a : 0xfff08a, bright: 2.4, speed: 0.25, up: 0.05, life: 2.6, size: 0.13, drag: 0.2 });
    }
    // ---- a fish leaping from the water nearby ----
    if (this.leap) {
      const L = this.leap;
      L.t += dt;
      const k = L.t / L.dur;
      if (k >= 1) {
        this.fish.visible = false;
        this.ripples.spawn(L.to.x, L.y, L.to.z, { size: 0.9, life: 1.2, opacity: 0.6 });
        this.sound.play('step_water', { at: L.to, vol: 0.6 });
        this.leap = null;
      } else {
        this.fish.position.set(L.from.x + (L.to.x - L.from.x) * k, L.y + Math.sin(k * Math.PI) * L.h, L.from.z + (L.to.z - L.from.z) * k);
        this.fish.rotation.set(-Math.cos(k * Math.PI) * 0.9, L.yaw, 0);
      }
    } else if ((this.fishT -= dt) <= 0) {
      this.fishT = 5 + Math.random() * 8;
      for (let i = 0; i < 16; i++) {
        const a = Math.random() * Math.PI * 2, r = 3 + Math.random() * 11;
        const x = hero.x + Math.cos(a) * r, z = hero.z + Math.sin(a) * r;
        if (!this.water(x, z) || !this.water(x + Math.cos(a) * 0.9, z + Math.sin(a) * 0.9)) continue;
        const yaw = a + (Math.random() - 0.5);
        const to = new THREE.Vector3(x + Math.sin(yaw) * 1.1, 0, z + Math.cos(yaw) * 1.1);
        this.leap = { from: new THREE.Vector3(x, 0, z), to, y: -0.1, h: 0.7 + Math.random() * 0.4, t: 0, dur: 0.75, yaw };
        this.fish.visible = true;
        this.ripples.spawn(x, -0.1, z, { size: 0.7, life: 0.9, opacity: 0.55 });
        break;
      }
    }
  }

  // a few birds come down on open ground near the hero (inside the room's bounds when given)
  flock(hero, box) {
    const n = 3 + Math.floor(Math.random() * 3);
    const a = Math.random() * Math.PI * 2, r = 6 + Math.random() * 4;
    let cx = hero.x + Math.cos(a) * r, cz = hero.z + Math.sin(a) * r;
    if (box) { cx = Math.min(box.x1 - 1, Math.max(box.x0 + 1, cx)); cz = Math.min(box.z1 - 1, Math.max(box.z0 + 1, cz)); }
    if (this.water(cx, cz)) return;
    let seed = Math.floor(Math.random() * 1e6);
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < n; i++) {
      const g = makeBird(rnd);
      g.position.set(cx + (rnd() - 0.5) * 1.6, 0, cz + (rnd() - 0.5) * 1.6);
      g.rotation.y = rnd() * 6.28;
      this.engine.scene.add(g);
      this.birds.push({ g, fly: false, t: 0, seed: rnd(), v: null });
    }
  }
}
