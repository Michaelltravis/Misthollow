// The sky over the hero (docs/GAMEPLAY_POLISH.md, group 3). The server keeps a weather for each
// zone, through the seasons (weather.py: clear, cloudy, rain, storm, snow, fog; the wind); the map
// payload carries the hero's (`weather`). Under open sky it is drawn here: rain falling slant in
// the wind and splashing on the ground, snow drifting, a desert's dust, fog closing in, a storm's
// lightning and its thunder after, leaves blown on a strong wind; the light dims and greys with
// the cloud (engine.weather). Indoors and underground none of it reaches.
//
// Also here, because they share the flat rings and marks on the ground: ripples (rain on water,
// the hero wading) and footprints (snow and sand keep them a while).
import * as THREE from 'three';

// how the sky looks for each kind: the light dimmed, the fog drawn in, the haze greyed, and what falls
export const LOOK = {
  clear: { dim: 0, fog: 0, grey: 0 },
  cloudy: { dim: 0.35, fog: 0.1, grey: 0.3 },
  rain: { dim: 0.5, fog: 0.3, grey: 0.5, rain: 0.6 },
  storm: { dim: 0.72, fog: 0.4, grey: 0.6, rain: 1, lightning: true },
  snow: { dim: 0.3, fog: 0.35, grey: 0.4, snow: 1 },
  fog: { dim: 0.3, fog: 0.85, grey: 0.6 },
  dust: { dim: 0.3, fog: 0.5, grey: 0.15, dust: 1 },
};

// the server's weather as the hero sees it where they stand: a desert's rain is dust (or only
// cloud), on snowy ground rain falls as snow
export function weatherKind(w, theme) {
  if (!w || !w.sky) return 'clear';
  let k = { stormy: 'storm', rainy: 'rain', snowy: 'snow', foggy: 'fog', overcast: 'cloudy' }[w.sky] || 'clear';
  if (w.precipitation === 'snow' || w.precipitation === 'sleet') k = k === 'storm' ? 'snow' : (k === 'rain' ? 'snow' : k);
  if (theme === 'desert' && ['rain', 'storm', 'snow'].includes(k)) k = (w.wind || 0) >= 15 ? 'dust' : 'cloudy';
  if (theme === 'snow' && (k === 'rain' || k === 'storm')) k = 'snow';
  return k;
}

const BOX = 18, TOP = 14;
const COUNT = { low: 500, med: 900, high: 1500 };

function roundDot() {
  if (typeof document === 'undefined') return null;
  const c = document.createElement('canvas');
  c.width = c.height = 32;
  const g = c.getContext('2d');
  const r = g.createRadialGradient(16, 16, 0, 16, 16, 16);
  r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(0.5, 'rgba(255,255,255,0.7)'); r.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = r; g.fillRect(0, 0, 32, 32);
  return new THREE.CanvasTexture(c);
}

// flat rings on the ground or the water, growing and fading (a pool, reused)
export class Ripples {
  constructor(scene, n = 32) {
    this.list = [];
    const geo = new THREE.RingGeometry(0.82, 1, 28).rotateX(-Math.PI / 2);
    for (let i = 0; i < n; i++) {
      const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: 0xdfeeff, transparent: true, opacity: 0, depthWrite: false,
        polygonOffset: true, polygonOffsetFactor: -2 }));
      m.visible = false;
      m.renderOrder = 2;
      scene.add(m);
      this.list.push({ m, t: 0, life: 1, size: 1, a: 0.5 });
    }
    this.next = 0;
  }
  spawn(x, y, z, { size = 0.6, life = 0.9, color = 0xdfeeff, opacity = 0.5 } = {}) {
    const r = this.list[this.next++ % this.list.length];
    r.m.position.set(x, y + 0.03, z);
    r.m.material.color.setHex(color);
    r.t = 0; r.life = life; r.size = size; r.a = opacity;
    r.m.visible = true;
  }
  update(dt) {
    for (const r of this.list) {
      if (!r.m.visible) continue;
      r.t += dt;
      const k = r.t / r.life;
      if (k >= 1) { r.m.visible = false; continue; }
      r.m.scale.setScalar(0.08 + r.size * k);
      r.m.material.opacity = r.a * (1 - k);
    }
  }
}

// prints left in snow and sand, fading after a while (a pool, the oldest reused)
export class Footprints {
  constructor(scene, n = 48) {
    this.list = [];
    const geo = new THREE.CircleGeometry(1, 12).rotateX(-Math.PI / 2);
    for (let i = 0; i < n; i++) {
      const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: 0x2a2620, transparent: true, opacity: 0, depthWrite: false,
        polygonOffset: true, polygonOffsetFactor: -1 }));
      m.scale.set(0.11, 1, 0.2);
      m.visible = false;
      scene.add(m);
      this.list.push({ m, t: 0, a: 0.4 });
    }
    this.next = 0;
    this.side = 1;
  }
  // a step at (x, z), heading `yaw` (radians, as the body turns), on snow or sand
  step(x, y, z, yaw, surface) {
    const f = this.list[this.next++ % this.list.length];
    this.side = -this.side;
    const off = 0.14 * this.side;
    f.m.position.set(x + Math.cos(yaw) * off, y + 0.025, z - Math.sin(yaw) * off);
    f.m.rotation.y = yaw;
    f.m.material.color.setHex(surface === 'snow' ? 0x8a9ab4 : 0x6a5434);
    f.a = surface === 'snow' ? 0.5 : 0.38;
    f.t = 0;
    f.m.visible = true;
  }
  update(dt) {
    for (const f of this.list) {
      if (!f.m.visible) continue;
      f.t += dt;
      f.m.material.opacity = f.a * Math.max(0, Math.min(1, (14 - f.t) / 4));
      if (f.t > 14) f.m.visible = false;
    }
  }
}

export class WeatherView {
  // engine (engine.js: weather, lightning), fx (particles), sound
  constructor(engine, fx, sound) {
    this.engine = engine; this.fx = fx; this.sound = sound;
    const scene = engine.scene;
    const n = COUNT[(engine.quality && engine.quality.name) || 'high'] || COUNT.high;
    this.n = n;
    // rain: short streaks
    this.rainPos = new Float32Array(n * 6);
    this.drops = new Float32Array(n * 3);
    const rg = new THREE.BufferGeometry();
    rg.setAttribute('position', new THREE.BufferAttribute(this.rainPos, 3));
    this.rain = new THREE.LineSegments(rg, new THREE.LineBasicMaterial({ color: 0xc4d4e4, transparent: true, opacity: 0.4, depthWrite: false }));
    this.rain.frustumCulled = false;
    this.rain.visible = false;
    scene.add(this.rain);
    // snow and dust: soft dots
    this.flakes = new Float32Array(n * 3);
    const sg = new THREE.BufferGeometry();
    sg.setAttribute('position', new THREE.BufferAttribute(this.flakes, 3));
    this.snow = new THREE.Points(sg, new THREE.PointsMaterial({ color: 0xffffff, size: 0.16, map: roundDot(), transparent: true, opacity: 0.9, depthWrite: false }));
    this.snow.frustumCulled = false;
    this.snow.visible = false;
    scene.add(this.snow);
    this.ripples = new Ripples(scene);
    this.prints = new Footprints(scene);
    this.kind = 'clear';
    this.wind = 0;
    this.open = false;
    this.amount = 0;           // how much falls, easing in and out (0..1)
    this.seeded = null;
    this.boltT = 8; this.thunderT = -1; this.rainT = 0; this.leafT = 0;
  }

  // what the sky is doing where the hero stands: the kind (weatherKind), the wind (mph), and
  // whether they stand under open sky
  set(kind, wind, open) {
    this.kind = LOOK[kind] ? kind : 'clear';
    this.wind = wind || 0;
    this.open = !!open;
    const L = this.open ? LOOK[this.kind] : LOOK.clear;
    this.engine.weather = { dim: L.dim, fog: L.fog, grey: L.grey };
  }

  // seed the falling things in the box round the hero
  seed(c) {
    for (let i = 0; i < this.n; i++) {
      this.drops[i * 3] = c.x + (Math.random() * 2 - 1) * BOX;
      this.drops[i * 3 + 1] = Math.random() * TOP;
      this.drops[i * 3 + 2] = c.z + (Math.random() * 2 - 1) * BOX;
      this.flakes[i * 3] = this.drops[i * 3]; this.flakes[i * 3 + 1] = this.drops[i * 3 + 1]; this.flakes[i * 3 + 2] = this.drops[i * 3 + 2];
    }
    this.seeded = c.clone();
  }

  // each frame: c is where the hero (the camera's target) is; groundY its ground
  update(dt, t, c, groundY = 0) {
    this.ripples.update(dt);
    this.prints.update(dt);
    const L = this.open ? LOOK[this.kind] : LOOK.clear;
    const want = L.rain || L.snow || L.dust || 0;
    this.amount += (want - this.amount) * Math.min(1, dt * 0.6);
    if (!this.seeded || this.seeded.distanceTo(c) > BOX * 1.5) this.seed(c);
    const wx = this.wind / 18, wz = this.wind / 40;          // the wind's slant (metres a second, roughly)
    // rain
    const raining = (L.rain || 0) > 0 || (this.rain.visible && this.amount > 0.02 && !L.snow && !L.dust);
    this.rain.visible = raining && this.amount > 0.02;
    if (this.rain.visible) {
      const live = Math.floor(this.n * Math.min(1, this.amount));
      const fall = 16, sx = wx * 2.2, sz = wz * 2.2;
      for (let i = 0; i < live; i++) {
        const j = i * 3;
        this.drops[j] += sx * dt; this.drops[j + 1] -= fall * dt; this.drops[j + 2] += sz * dt;
        if (this.drops[j + 1] < groundY) {
          // a splash, near the hero, now and then
          if (i % 7 === 0 && Math.abs(this.drops[j] - c.x) < 9 && Math.abs(this.drops[j + 2] - c.z) < 9) this.ripples.spawn(this.drops[j], groundY, this.drops[j + 2], { size: 0.35, life: 0.45, opacity: 0.45 });
          this.drops[j] = c.x + (Math.random() * 2 - 1) * BOX; this.drops[j + 1] = groundY + TOP * (0.7 + Math.random() * 0.3); this.drops[j + 2] = c.z + (Math.random() * 2 - 1) * BOX;
        }
        const k = i * 6;
        this.rainPos[k] = this.drops[j]; this.rainPos[k + 1] = this.drops[j + 1]; this.rainPos[k + 2] = this.drops[j + 2];
        this.rainPos[k + 3] = this.drops[j] - sx * 0.05; this.rainPos[k + 4] = this.drops[j + 1] + 0.55; this.rainPos[k + 5] = this.drops[j + 2] - sz * 0.05;
      }
      this.rain.geometry.setDrawRange(0, live * 2);
      this.rain.geometry.attributes.position.needsUpdate = true;
      this.rain.material.opacity = 0.18 + 0.3 * Math.min(1, this.amount);
      // its sound: a hiss now and then, louder in a storm
      if ((this.rainT -= dt) <= 0) { this.rainT = 1.4; this.sound.play('rain', { vol: 0.4 + 0.6 * this.amount }); }
    }
    // snow and dust
    const flaking = (L.snow || L.dust) && this.amount > 0.02;
    this.snow.visible = !!flaking;
    if (flaking) {
      const dust = !!L.dust;
      const live = Math.floor(this.n * 0.7 * Math.min(1, this.amount));
      this.snow.material.color.setHex(dust ? 0xc8a878 : 0xffffff);
      this.snow.material.size = dust ? 0.1 : 0.16;
      for (let i = 0; i < live; i++) {
        const j = i * 3;
        if (dust) { this.flakes[j] += (3 + wx * 3) * dt; this.flakes[j + 1] += Math.sin(t * 2 + i) * 0.3 * dt - 0.2 * dt; this.flakes[j + 2] += wz * 2 * dt; }
        else { this.flakes[j] += (Math.sin(t * 0.9 + i * 1.3) * 0.5 + wx) * dt; this.flakes[j + 1] -= 1.3 * dt; this.flakes[j + 2] += (Math.cos(t * 0.7 + i) * 0.4 + wz) * dt; }
        if (this.flakes[j + 1] < groundY || Math.abs(this.flakes[j] - c.x) > BOX || Math.abs(this.flakes[j + 2] - c.z) > BOX) {
          this.flakes[j] = c.x + (Math.random() * 2 - 1) * BOX; this.flakes[j + 1] = groundY + (dust ? Math.random() * 3 : TOP * Math.random());
          this.flakes[j + 2] = c.z + (Math.random() * 2 - 1) * BOX;
        }
      }
      this.snow.geometry.setDrawRange(0, live);
      this.snow.geometry.attributes.position.needsUpdate = true;
    }
    if (!this.open) return;
    // a storm's lightning, its thunder a moment after
    if (L.lightning && (this.boltT -= dt) <= 0) {
      this.boltT = 6 + Math.random() * 10;
      if (this.engine.lightning) this.engine.lightning();
      this.thunderT = 0.4 + Math.random() * 1.4;
    }
    if (this.thunderT > 0 && (this.thunderT -= dt) <= 0) this.sound.play('thunder');
    // a strong wind: leaves (or sand) blown past
    if (this.wind >= 15 && (this.leafT -= dt) <= 0) {
      this.leafT = 0.12 + Math.random() * 0.2;
      const p = new THREE.Vector3(c.x - 8 + Math.random() * 4, groundY + 0.5 + Math.random() * 2.5, c.z + (Math.random() * 2 - 1) * 8);
      if (this.fx && this.fx.glyph) this.fx.glyph(p, { glyph: this.kind === 'dust' ? 'dot' : 'leaf', count: 1, color: this.kind === 'snow' ? 0xffffff : 0x8aa04a,
        bright: 1, speed: 0.2, dir: new THREE.Vector3(4 + this.wind / 10, -0.3, 0.6), life: 3, size: 0.18, drag: 0.1, spin: 4 });
    }
  }
}
