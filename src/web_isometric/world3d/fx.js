// Combat visuals: pooled particles (soft dots, and glyphs: notes, skulls, coins, leaves...),
// projectiles, beams, chains, rays, tethers, slash arcs, light pillars, ground sigils and
// cracks, meteors and rains, growths (vines, ice, bones, bars), shields, wings, halos,
// afterimages, ground telegraphs, floating combat text, hit flashes, camera shake and screen
// flashes. Everything is fire-and-forget: fx.update(dt) advances it all, on the frame clock
// (fx.after / fx.every), so a hit-stop slows an effect's whole sequence together.
//
// Each quality tier has a budget (BUDGET): an effect that would go over it is skipped, never
// queued, so a crowded fight costs what a quiet one does.
import * as THREE from 'three';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { shellMaterial } from './shell.js';
import { glyphAtlas, glyphIndex, ATLAS_COLS, GLYPHS, sigilCanvas, wingCanvas, bannerCanvas } from './glyphs.js';

const MAX = 3000;

// what one quality tier may have alive at once
export const BUDGET = {
  high: { glyphs: 700, decals: 10, growths: 8, ghosts: 6, bubbles: 4, lights: 4, meshes: 24 },
  med: { glyphs: 500, decals: 8, growths: 6, ghosts: 3, bubbles: 3, lights: 3, meshes: 16 },
  low: { glyphs: 300, decals: 4, growths: 3, ghosts: 0, bubbles: 2, lights: 0, meshes: 10 },
};

// ---- particles: additive soft dots, CPU-simulated, one THREE.Points ----
class Particles {
  constructor(scene, max = MAX, glyphTex = null) {
    this.cap = max;
    this.glyphs = !!glyphTex;
    this.pos = new Float32Array(max * 3);
    this.col = new Float32Array(max * 3);
    this.size = new Float32Array(max);
    this.alpha = new Float32Array(max);
    this.vel = new Float32Array(max * 3);
    this.life = new Float32Array(max);
    this.max = new Float32Array(max);
    this.grav = new Float32Array(max);
    this.drag = new Float32Array(max);
    this.grow = new Float32Array(max);
    this.n = 0;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('color', new THREE.BufferAttribute(this.col, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('size', new THREE.BufferAttribute(this.size, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('alpha', new THREE.BufferAttribute(this.alpha, 1).setUsage(THREE.DynamicDrawUsage));
    let m;
    if (glyphTex) {
      // glyphs: which picture (atlas cell), turned and spinning
      this.glyph = new Float32Array(max);
      this.rot = new Float32Array(max);
      this.spin = new Float32Array(max);
      g.setAttribute('glyph', new THREE.BufferAttribute(this.glyph, 1).setUsage(THREE.DynamicDrawUsage));
      g.setAttribute('rot', new THREE.BufferAttribute(this.rot, 1).setUsage(THREE.DynamicDrawUsage));
      const rows = Math.ceil(GLYPHS.length / ATLAS_COLS);
      m = new THREE.ShaderMaterial({
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
        uniforms: { uScale: { value: 300 }, uAtlas: { value: glyphTex }, uGrid: { value: new THREE.Vector2(ATLAS_COLS, rows) } },
        vertexShader: `attribute float size; attribute float alpha; attribute float glyph; attribute float rot; attribute vec3 color;
          varying vec3 vC; varying float vA; varying float vG; varying float vR; uniform float uScale;
          void main() { vC = color; vA = alpha; vG = glyph; vR = rot; vec4 mv = modelViewMatrix * vec4(position, 1.0);
            gl_PointSize = size * uScale / -mv.z; gl_Position = projectionMatrix * mv; }`,
        fragmentShader: `uniform sampler2D uAtlas; uniform vec2 uGrid; varying vec3 vC; varying float vA; varying float vG; varying float vR;
          void main() { vec2 c = gl_PointCoord - 0.5; float s = sin(vR), k = cos(vR);
            c = vec2(k * c.x - s * c.y, s * c.x + k * c.y) + 0.5;
            vec2 cell = vec2(mod(vG, uGrid.x), floor(vG / uGrid.x));
            float a = texture2D(uAtlas, (cell + clamp(c, 0.0, 1.0)) / uGrid).a * vA;
            if (a < 0.01) discard;
            gl_FragColor = vec4(vC * a, a); }`,
      });
    } else {
      m = new THREE.ShaderMaterial({
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
        uniforms: { uScale: { value: 300 } },
        vertexShader: `attribute float size; attribute float alpha; attribute vec3 color; varying vec3 vC; varying float vA;
          uniform float uScale;
          void main() { vC = color; vA = alpha; vec4 mv = modelViewMatrix * vec4(position, 1.0);
            gl_PointSize = size * uScale / -mv.z; gl_Position = projectionMatrix * mv; }`,
        fragmentShader: `varying vec3 vC; varying float vA;
          void main() { vec2 d = gl_PointCoord - 0.5; float r = length(d); if (r > 0.5) discard;
            float a = smoothstep(0.5, 0.0, r); gl_FragColor = vec4(vC * a * vA, a * vA); }`,
      });
    }
    g.setDrawRange(0, 0);
    this.points = new THREE.Points(g, m);
    this.points.frustumCulled = false;
    this.points.renderOrder = 10;
    scene.add(this.points);
    this.geo = g;
  }
  emit(p, { count = 10, color = 0xffffff, bright = 1, speed = 2, up = 0, life = 0.6, size = 0.25, gravity = 0, spread = 1, drag = 1.5, grow = 0, jitter = 0, dir = null, glyph = 'dot', spin = 0, rot = null } = {}) {
    const c = color instanceof THREE.Color ? color : _c.set(color);
    const gi = this.glyphs ? (typeof glyph === 'number' ? glyph : glyphIndex(glyph)) : 0;
    for (let k = 0; k < count && this.n < this.cap; k++) {
      const i = this.n++;
      this.pos[i * 3] = p.x + (Math.random() - 0.5) * jitter;
      this.pos[i * 3 + 1] = p.y + (Math.random() - 0.5) * jitter;
      this.pos[i * 3 + 2] = p.z + (Math.random() - 0.5) * jitter;
      let vx = (Math.random() - 0.5) * 2, vy = (Math.random() - 0.5) * 2, vz = (Math.random() - 0.5) * 2;
      const l = Math.hypot(vx, vy, vz) || 1;
      vx = vx / l * spread; vy = vy / l * spread; vz = vz / l * spread;
      if (dir) { vx += dir.x; vy += dir.y; vz += dir.z; }
      const s = speed * (0.5 + Math.random() * 0.7);
      this.vel[i * 3] = vx * s; this.vel[i * 3 + 1] = vy * s + up; this.vel[i * 3 + 2] = vz * s;
      this.col[i * 3] = c.r * bright; this.col[i * 3 + 1] = c.g * bright; this.col[i * 3 + 2] = c.b * bright;
      this.size[i] = size * (0.6 + Math.random() * 0.8);
      this.life[i] = this.max[i] = life * (0.6 + Math.random() * 0.6);
      this.alpha[i] = 1;
      this.grav[i] = gravity; this.drag[i] = drag; this.grow[i] = grow;
      if (this.glyphs) {
        this.glyph[i] = gi;
        this.rot[i] = rot == null ? (Math.random() - 0.5) * 0.8 : rot;
        this.spin[i] = spin * (Math.random() < 0.5 ? -1 : 1) * (0.6 + Math.random() * 0.8);
      }
    }
  }
  update(dt) {
    let i = 0;
    while (i < this.n) {
      this.life[i] -= dt;
      if (this.life[i] <= 0) { this.kill(i); continue; }
      const d = Math.max(0, 1 - this.drag[i] * dt);
      this.vel[i * 3] *= d; this.vel[i * 3 + 1] = this.vel[i * 3 + 1] * d - this.grav[i] * dt; this.vel[i * 3 + 2] *= d;
      this.pos[i * 3] += this.vel[i * 3] * dt; this.pos[i * 3 + 1] += this.vel[i * 3 + 1] * dt; this.pos[i * 3 + 2] += this.vel[i * 3 + 2] * dt;
      const k = this.life[i] / this.max[i];
      this.alpha[i] = Math.min(1, k * 2.2);
      this.size[i] = Math.max(0, this.size[i] + this.grow[i] * dt);
      if (this.glyphs) this.rot[i] += this.spin[i] * dt;
      i++;
    }
    const attrs = this.glyphs ? ['position', 'color', 'size', 'alpha', 'glyph', 'rot'] : ['position', 'color', 'size', 'alpha'];
    for (const a of attrs) this.geo.attributes[a].needsUpdate = true;
    this.geo.setDrawRange(0, this.n);
  }
  kill(i) {
    const j = --this.n;
    if (i === j) return;
    for (let k = 0; k < 3; k++) { this.pos[i * 3 + k] = this.pos[j * 3 + k]; this.vel[i * 3 + k] = this.vel[j * 3 + k]; this.col[i * 3 + k] = this.col[j * 3 + k]; }
    this.size[i] = this.size[j]; this.alpha[i] = this.alpha[j]; this.life[i] = this.life[j]; this.max[i] = this.max[j];
    this.grav[i] = this.grav[j]; this.drag[i] = this.drag[j]; this.grow[i] = this.grow[j];
    if (this.glyphs) { this.glyph[i] = this.glyph[j]; this.rot[i] = this.rot[j]; this.spin[i] = this.spin[j]; }
  }
}

// ---- schools: colours for spells and impacts ----
export const SCHOOL = {
  fire: { core: new THREE.Color(4, 1.6, 0.4), spark: 0xff7a2a, smoke: 0x5a3020 },
  frost: { core: new THREE.Color(1.2, 2.6, 4), spark: 0x9fd8ff, smoke: 0xdaf2ff },
  lightning: { core: new THREE.Color(2.4, 2.6, 4.5), spark: 0xbfd8ff, smoke: 0x8a9aff },
  arcane: { core: new THREE.Color(2.6, 1.0, 4.2), spark: 0xc87aff, smoke: 0x6a3aa8 },
  holy: { core: new THREE.Color(4, 3.4, 1.6), spark: 0xffe8a0, smoke: 0xfff4d0 },
  shadow: { core: new THREE.Color(1.4, 0.4, 2.2), spark: 0x8a4ad0, smoke: 0x2a1040 },
  necrotic: { core: new THREE.Color(0.8, 2.6, 0.9), spark: 0x7aff8a, smoke: 0x1a3a1a },
  nature: { core: new THREE.Color(1.2, 3, 0.8), spark: 0x9aff6a, smoke: 0x3a6a2a },
  poison: { core: new THREE.Color(1.2, 2.6, 0.4), spark: 0xb8ff5a, smoke: 0x4a6a1a },
  sound: { core: new THREE.Color(3, 2, 3.6), spark: 0xffb8ff, smoke: 0x8a5aa8 },
  physical: { core: new THREE.Color(3, 3, 3), spark: 0xffffff, smoke: 0x888888 },
  blood: { core: new THREE.Color(2.8, 0.3, 0.3), spark: 0xd02a2a, smoke: 0x5a0a0a },
};

const _v = new THREE.Vector3(), _w = new THREE.Vector3(), _u = new THREE.Vector3(), _c = new THREE.Color();
const UP = new THREE.Vector3(0, 1, 0);
const posOf = t => (t && t.position ? t.position : t);
// shared geometries (never disposed): a flat square for decals, a beam along +Z, shells
const GEO = {};
function geo(name) {
  if (GEO[name]) return GEO[name];
  switch (name) {
    case 'plane': return (GEO[name] = new THREE.PlaneGeometry(2, 2).rotateX(-Math.PI / 2));
    case 'beam': return (GEO[name] = new THREE.CylinderGeometry(1, 1, 1, 10, 1, true).rotateX(Math.PI / 2).translate(0, 0, 0.5));
    case 'sphere': return (GEO[name] = new THREE.SphereGeometry(1, 28, 18));
    case 'dome': return (GEO[name] = new THREE.SphereGeometry(1, 36, 12, 0, Math.PI * 2, 0, Math.PI / 2));
    case 'halo': return (GEO[name] = new THREE.TorusGeometry(1, 0.11, 8, 40).rotateX(Math.PI / 2));
    case 'wing': return (GEO[name] = new THREE.PlaneGeometry(1, 1).translate(-0.5, 0.5, 0));
    case 'ring': return (GEO[name] = new THREE.RingGeometry(0.85, 1, 48));
    case 'thinring': return (GEO[name] = new THREE.RingGeometry(0.94, 1, 48));
    case 'spike': return (GEO[name] = new THREE.ConeGeometry(0.17, 1, 6).translate(0, 0.5, 0));
    case 'thorn': return (GEO[name] = new THREE.ConeGeometry(0.09, 1, 5).translate(0, 0.5, 0));
    case 'crystal': return (GEO[name] = new THREE.OctahedronGeometry(0.5, 0).scale(0.45, 1, 0.45).translate(0, 0.5, 0));
    case 'bar': return (GEO[name] = new THREE.CylinderGeometry(0.05, 0.05, 1, 6).translate(0, 0.5, 0));
    case 'stone': return (GEO[name] = new THREE.DodecahedronGeometry(0.42, 0).translate(0, 0.2, 0));
    case 'vine': {
      const pts = [];
      for (let i = 0; i <= 12; i++) { const k = i / 12; pts.push(new THREE.Vector3(Math.sin(k * 7) * 0.22 * (1 - k * 0.5), k, Math.cos(k * 7) * 0.22 * (1 - k * 0.5))); }
      return (GEO[name] = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 24, 0.05, 5, false));
    }
    case 'blade': return (GEO[name] = new THREE.ConeGeometry(0.07, 0.6, 4).rotateX(Math.PI / 2));
    case 'shard': return (GEO[name] = new THREE.OctahedronGeometry(0.16, 0).scale(0.6, 0.6, 2.2));
    default: return null;
  }
}
// a soft shell that glows at its rim (shields, domes)

// how long combat numbers stay (the owner: "the text fades pretty fast"): longer than they were,
// x Settings -> Number duration; past TEXT_MAX on screen the oldest fade out early, and the hero's
// column keeps LANE_MAX lines
const TEXT_LIFE = 1.45, LANE_LIFE = 1.35, TEXT_MAX = 14, LANE_MAX = 7;

export class FX {
  constructor(engine, overlay) {
    this.engine = engine;
    this.scene = engine.scene;
    this.tier = (engine.quality && engine.quality.name) || 'high';
    this.budget = BUDGET[this.tier] || BUDGET.high;
    this.live = {};
    this.p = new Particles(engine.scene);
    const atlas = typeof document !== 'undefined' ? glyphAtlas() : null;
    if (atlas) {
      const tex = new THREE.CanvasTexture(atlas);
      tex.flipY = false;
      this.g = new Particles(engine.scene, this.budget.glyphs, tex);
    }
    // the flash lights (light()): made once, so the number of lights in the scene never changes
    this.lightPool = [];
    for (let i = 0; i < (this.budget.lights || 0); i++) {
      const l = new THREE.PointLight(0xffffff, 0, 6, 1.6);
      l.userData.free = true;
      this.scene.add(l);
      this.lightPool.push(l);
    }
    this.textures = new Map();
    this.items = [];                   // live effects: {update(dt) -> keep?}
    this.overlay = overlay;            // DOM layer for floating text
    this.texts = [];
    this.shakeT = 0; this.shakeMag = 0;
    engine.onTick(dt => this.update(dt));
    // floating text is placed once the camera has moved for this frame (no lag while orbiting)
    if (engine.onLateTick) engine.onLateTick(dt => this.updateTexts(dt)); else this._textsInTick = true;
    engine.rig.shake = () => this.shakeOffset();
  }

  add(item) { this.items.push(item); return item; }

  // particles keep their size on any screen: scaled by the drawing buffer's height (a sharp
  // display draws them with as many more pixels as it has); glyphs are pictures, so larger
  scaleToScreen() {
    const h = this.engine.renderer.domElement.height || 720;
    if (h === this._h) return;
    this._h = h;
    const s = 300 * h / 720;
    this.p.points.material.uniforms.uScale.value = s;
    if (this.g) this.g.points.material.uniforms.uScale.value = s * 3.6;
  }

  update(dt) {
    this.scaleToScreen();
    this.p.update(dt);
    if (this.g) this.g.update(dt);
    for (let i = this.items.length - 1; i >= 0; i--) {
      let keep = false;
      try { keep = this.items[i].update(dt); } catch (err) { console.warn('fx', err); }
      if (!keep) { const it = this.items[i]; this.items.splice(i, 1); try { if (it.dispose) it.dispose(); } catch (err) { console.warn('fx', err); } }
    }
    if (this._textsInTick) this.updateTexts(dt);
    if (this.shakeT > 0) this.shakeT -= dt;
  }

  // ---- budgets: ask before adding something costly; give back when it is gone ----
  take(kind) {
    const cap = this.budget[kind];
    if (cap == null) return true;
    if ((this.live[kind] || 0) >= cap) return false;
    this.live[kind] = (this.live[kind] || 0) + 1;
    return true;
  }
  give(kind) { this.live[kind] = Math.max(0, (this.live[kind] || 0) - 1); }
  // far from the view, only an effect's core is drawn
  near(p, dist = 28) { const f = this.engine.rig && this.engine.rig.focus; return !f || !p || Math.hypot(p.x - f.x, p.z - f.z) < dist; }

  // ---- the frame clock: sequences follow frame time (a hit-stop slows them all alike) ----
  after(secs, fn) {
    if (!(secs > 0)) { try { fn(); } catch (err) { console.warn('fx', err); } return null; }
    let t = secs;
    return this.add({ update: dt => { t -= dt; if (t > 0) return true; fn(); return false; } });
  }
  every(secs, count, fn, start = 0) {
    let t = start, n = 0;
    return this.add({ update: dt => {
      t -= dt;
      while (t <= 0 && n < count) { fn(n++); t += secs; }
      return n < count;
    } });
  }

  // ---- glyph particles: notes, skulls, coins, leaves... (dots when glyphs are unavailable) ----
  glyph(p, opts = {}) {
    if (this.g) this.g.emit(p, { size: 0.42, bright: 1.6, ...opts });
    else this.p.emit(p, { ...opts, glyph: undefined });
  }

  // ---- screen feedback ----
  // the player's settings (hud settings -> main.js): numbers 'all' | 'you' | 'foes' | 'off', their size, shake
  get opts() { return this._opts || (this._opts = { sct: 'all', size: 1, shake: true, life: 1 }); }
  set opts(o) { this._opts = { ...this.opts, ...o }; }
  shake(mag = 0.15, time = 0.22) {
    if (!this.opts.shake) return; this.shakeMag = Math.max(this.shakeMag * (this.shakeT > 0 ? 1 : 0), mag); this.shakeT = Math.max(this.shakeT, time); }
  shakeOffset() {
    if (this.shakeT <= 0) return null;
    const m = this.shakeMag * Math.min(1, this.shakeT / 0.12);
    return _w.set((Math.random() - 0.5) * m, (Math.random() - 0.5) * m, (Math.random() - 0.5) * m);
  }
  // the whole view washes with a colour for a moment (the biggest abilities)
  screen(color = '#ffffff', { time = 0.45, opacity = 0.32 } = {}) {
    if (typeof document === 'undefined' || !this.overlay) return;
    const d = document.createElement('div');
    d.style.cssText = `position:fixed;inset:0;pointer-events:none;z-index:4;background:${color};opacity:${opacity};transition:opacity ${time}s ease-out`;
    (this.overlay.parentElement || document.body).appendChild(d);
    requestAnimationFrame(() => requestAnimationFrame(() => { d.style.opacity = '0'; }));
    setTimeout(() => d.remove(), time * 1000 + 120);
  }

  // ---- floating combat text ----
  // label: a small line above (the spell that did it); edge: a glow in another colour (the
  // school of a blow that hurt the hero)
  text(pos, str, { color = '#ffffff', size = 18, crit = false, rise = 1.4, life = 1.1, side = 0, label = '', edge = '', exact = false } = {}) {
    const d = document.createElement('div');
    d.className = 'fct' + (crit ? ' crit' : '');
    if (label) { const l = document.createElement('span'); l.className = 'fct-l'; l.textContent = label; d.append(l, str); }
    else d.textContent = str;
    if (edge) d.style.setProperty('--edge', edge);
    d.style.color = color;
    d.style.fontSize = `${(crit ? size * 1.45 : size) * this.opts.size}px`;
    this.overlay.appendChild(d);
    // words born together over the same head (a flurry, a crit and a stun) fan out instead
    // of printing on top of each other
    let stack = 0;
    for (const o of this.texts) if (o.t < 0.45 && o.p0.distanceToSquared(pos) < 0.5) stack++;
    const fan = stack ? (stack % 2 ? 0.45 : -0.45) * Math.ceil(stack / 2) : 0;
    // fan out along the screen's left-right, whichever way the camera has been turned
    const right = new THREE.Vector3(1, 0, 0).applyQuaternion(this.engine.camera.quaternion).setY(0).normalize();
    const p = pos.clone().addScaledVector(right, side + fan + (Math.random() - 0.5) * 0.3)
      .add(new THREE.Vector3(0, stack * 0.3, 0));
    // long enough to read (Settings -> Number duration), a crit longer; small ticks stay quick
    if (!exact) life *= TEXT_LIFE * (this.opts.life || 1) * (crit ? 1.3 : size <= 13 ? 0.8 : 1);   // (exact: timed to something, a wind-up)
    const entry = { d, p0: pos.clone(), p, t: 0, life, rise, crit };
    this.texts.push(entry);
    // a crowd of numbers: the oldest ordinary ones fade out early rather than pile up
    const live = this.texts.filter(o => o.t < o.life - 0.3);
    for (let i = 0; i < live.length - TEXT_MAX; i++) if (!live[i].crit) live[i].t = Math.max(live[i].t, live[i].life - 0.3);
    return entry;
  }
  // ---- the hero's column (scrolling combat text): what happens to the hero rises over its head
  // in the order it happens, each new line pushing the older ones up so nothing overlaps.
  // laneAnchor() gives the hero's position (combat.js sets it) ----
  lane(str, { color = '#ffffff', size = 17, crit = false, edge = '', life = 1.9 } = {}) {
    if (!this.laneAnchor || this.opts.sct === 'off' || this.opts.sct === 'foes') return;
    life *= LANE_LIFE * (this.opts.life || 1) * (crit ? 1.25 : size <= 13 ? 0.8 : 1);
    size *= this.opts.size;
    const d = document.createElement('div');
    d.className = 'fct lane' + (crit ? ' crit' : '');
    d.textContent = str;
    d.style.color = color;
    d.style.fontSize = `${crit ? size * 1.35 : size}px`;
    if (edge) d.style.setProperty('--edge', edge);
    this.overlay.appendChild(d);
    this.laneItems = this.laneItems || [];
    const step = (crit ? size * 1.35 : size) + 5;
    for (const o of this.laneItems) o.want += step;              // older lines move up
    this.laneItems.push({ d, t: 0, life, want: 0, y: -step * 0.6, crit });
    while (this.laneItems.length > LANE_MAX) this.laneItems.shift().d.remove();
  }
  updateLane(dt, cam, w, h) {
    const items = this.laneItems;
    if (!items || !items.length) return;
    const at = this.laneAnchor && this.laneAnchor();
    for (let i = items.length - 1; i >= 0; i--) {
      const o = items[i];
      o.t += dt;
      if (o.t >= o.life || !at) { o.d.remove(); items.splice(i, 1); continue; }
      o.y += (o.want - o.y) * Math.min(1, dt * 12);              // ease to its place in the column
      const drift = o.t * 14;                                      // and keep rising slowly
      _v.copy(at).setY(at.y + 2.5).project(cam);
      const k = o.t / o.life;
      const pop = o.crit ? 1 + Math.max(0, 0.5 - o.t * 3.5) : 1 + Math.max(0, 0.2 - o.t * 2);
      o.d.style.transform = `translate(${((_v.x + 1) / 2 * w).toFixed(1)}px, ${((1 - _v.y) / 2 * h - o.y - drift).toFixed(1)}px) translate(-50%, -100%) scale(${pop.toFixed(2)})`;
      o.d.style.opacity = k < 0.78 ? 1 : 1 - (k - 0.78) / 0.22;
    }
  }
  updateTexts(dt) {
    const cam = this.engine.camera, cv = this.engine.renderer.domElement;
    const w = cv.clientWidth, h = cv.clientHeight;
    this.updateLane(dt, cam, w, h);
    for (let i = this.texts.length - 1; i >= 0; i--) {
      const x = this.texts[i];
      x.t += dt;
      if (x.t >= x.life) { x.d.remove(); this.texts.splice(i, 1); continue; }
      const k = x.t / x.life;
      _v.copy(x.p).setY(x.p.y + x.rise * (1 - Math.pow(1 - k, 2))).project(cam);
      const pop = x.crit ? 1 + Math.max(0, 0.6 - x.t * 4) : 1 + Math.max(0, 0.25 - x.t * 2);
      x.d.style.transform = `translate(${((_v.x + 1) / 2 * w).toFixed(1)}px, ${((1 - _v.y) / 2 * h).toFixed(1)}px) translate(-50%, -50%) scale(${pop.toFixed(2)})`;
      x.d.style.opacity = k < 0.75 ? 1 : 1 - (k - 0.75) / 0.25;
    }
  }

  // ---- bodies: a hit flash, a longer glow, fading out of sight (materials are per actor) ----
  flash(root, color = 0xff3a2a, time = 0.18) { this.tint(root, color, { time, strength: 0.9, hold: 0 }); }
  tint(root, color, { time = 1.2, strength = 0.55, hold = 0.7, pulse = 0 } = {}) {
    if (!root) return;
    const mats = [];
    root.traverse(o => { if (o.isMesh && o.material && o.material.emissive) mats.push(o.material); });
    const c = new THREE.Color(color);
    let t = 0;
    // remember each material's own glow once: overlapping flashes must not keep the colour
    for (const m of mats) if (!m.userData.baseEmissive) m.userData.baseEmissive = m.emissive.clone();
    const token = {};
    for (const m of mats) m.userData.flashToken = token;
    this.add({ update: dt => {
      t += dt;
      const fadeFrom = time * hold;
      let k = t < fadeFrom ? 1 : Math.max(0, 1 - (t - fadeFrom) / Math.max(0.01, time - fadeFrom));
      if (pulse) k *= 0.65 + 0.35 * Math.sin(t * pulse * Math.PI * 2);
      for (const m of mats) {
        if (m.userData.flashToken !== token) continue;          // a newer flash owns it now
        m.emissive.copy(m.userData.baseEmissive).lerp(c, k * strength);
      }
      return t < time;
    } });
  }
  // see-through for a while (stealth, a blink), then solid again
  fade(root, { time = 2.4, opacity = 0.28, inT = 0.25, outT = 0.35 } = {}) {
    if (!root) return;
    const mats = [];
    root.traverse(o => { if (o.isMesh && o.material) mats.push(o.material); });
    const token = {};
    for (const m of mats) {
      if (m.userData.baseTransparent == null) { m.userData.baseTransparent = m.transparent; m.userData.baseOpacity = m.opacity; }
      m.userData.fadeToken = token;
      m.transparent = true; m.needsUpdate = true;
    }
    let t = 0;
    this.add({ update: dt => {
      t += dt;
      const k = t < inT ? t / inT : t > time - outT ? Math.max(0, (time - t) / outT) : 1;
      for (const m of mats) if (m.userData.fadeToken === token) m.opacity = m.userData.baseOpacity * (1 - (1 - opacity) * k);
      return t < time;
    }, dispose: () => {
      for (const m of mats) {
        if (m.userData.fadeToken !== token) continue;
        m.opacity = m.userData.baseOpacity; m.transparent = m.userData.baseTransparent; m.needsUpdate = true;
      }
    } });
  }
  // a frozen copy of a body in its pose of the moment, fading where it stood (dashes, dodges,
  // shadow clones); `at` moves it, `color` tints it
  afterimage(root, { color = 0x8a4ad0, time = 0.55, opacity = 0.55, at = null, yaw = null } = {}) {
    if (!root || !this.take('ghosts')) return;
    let ghost;
    try { ghost = SkeletonUtils.clone(root); } catch (err) { this.give('ghosts'); return; }
    const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false });
    ghost.traverse(o => { if (o.isMesh) { o.material = mat; o.castShadow = false; o.receiveShadow = false; } });
    ghost.position.copy(at || root.position);
    ghost.rotation.copy(root.rotation);
    if (yaw != null) ghost.rotation.y = yaw;
    ghost.scale.copy(root.scale);
    this.scene.add(ghost);
    let t = 0;
    this.add({ update: dt => { t += dt; mat.opacity = opacity * Math.max(0, 1 - t / time); return t < time; },
      dispose: () => { this.scene.remove(ghost); mat.dispose(); this.give('ghosts'); } });
  }

  // ---- bursts ----
  impact(p, school = 'physical', big = false) {
    const s = SCHOOL[school] || SCHOOL.physical;
    this.p.emit(p, { count: big ? 34 : 16, color: s.spark, speed: big ? 5 : 3.5, life: 0.45, size: big ? 0.32 : 0.22, gravity: 4, drag: 2.5 });
    this.p.emit(p, { count: big ? 10 : 5, color: s.smoke, speed: 1, up: 0.8, life: 0.7, size: 0.5, grow: 0.8, drag: 1 });
    this.light(p, s.core, big ? 7 : 4, 0.22);
  }
  sparks(p, color = 0xffe0a0, n = 12) { this.p.emit(p, { count: n, color, speed: 4, life: 0.3, size: 0.16, gravity: 6, drag: 2 }); }

  // a short-lived point light (pooled small: at most a few at once)
  // A flash of light. The lights are a fixed pool, always in the scene and dark when idle: adding
  // or removing a light makes every lit material rebuild its shader, and a big spell's burst of
  // them (meteors, novas) stalled the GPU until the browser dropped the 3D view (it went black).
  light(p, color, intensity = 5, time = 0.25) {
    if (!p || !Number.isFinite(p.x) || !Number.isFinite(p.y) || !Number.isFinite(p.z) || !(intensity > 0) || !(time > 0)) return;
    const l = this.lightPool.find(x => x.userData.free);
    if (!l) return;
    l.userData.free = false;
    l.color.set(color);
    l.position.copy(p);
    l.intensity = intensity;
    let t = time;
    this.add({ update: dt => { t -= dt; l.intensity = intensity * Math.max(0, t / time); return t > 0; },
      dispose: () => { l.intensity = 0; l.userData.free = true; } });
  }

  // ---- melee: a bright arc swept in front of the attacker ----
  // tilt turns the arc (0 flat, 1 upright: a rising or falling blow)
  slash(from, to, { color = 0xffffff, wide = false, delay = 0, tilt = 0, flip = false, reach = 1, time = 0.22 } = {}) {
    const dir = _v.copy(to).sub(from).setY(0).normalize();
    const g = new THREE.RingGeometry((wide ? 1.0 : 0.7) * reach, (wide ? 2.1 : 1.35) * reach, 24, 1, -Math.PI * (wide ? 0.85 : 0.45), Math.PI * (wide ? 1.7 : 0.9));
    const mat = new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(2.2), transparent: true, opacity: 0,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false });
    const m = new THREE.Mesh(g, mat);
    const holder = new THREE.Group();
    holder.add(m);
    m.rotation.x = -Math.PI / 2;
    holder.position.copy(from).setY(1.05).addScaledVector(dir, wide ? 0.2 : 0.55);
    holder.rotation.y = Math.atan2(dir.x, dir.z);
    holder.rotation.z = tilt * Math.PI / 2 * (flip ? -1 : 1);
    m.rotation.z = -Math.PI / 2;
    let t = -delay;
    this.scene.add(holder);
    return this.add({ update: dt => {
      t += dt;
      if (t < 0) return true;
      const k = t / time;
      mat.opacity = k < 0.3 ? k / 0.3 : Math.max(0, 1 - (k - 0.3) / 0.7);
      m.rotation.z += dt * 9 * (wide ? 1.4 : 1) * (flip ? -1 : 1);
      return k < 1;
    }, dispose: () => { this.scene.remove(holder); g.dispose(); mat.dispose(); } });
  }

  // ---- projectiles: a head with a trail, flies from -> to, then onHit ----
  // kind: orb | arrow | shard | blade | glyph (a big glyph: `glyph`); trail(pos) runs each frame
  projectile(from, to, { school = 'arcane', color = null, speed = 16, size = 0.22, arc = 0.4, kind = 'orb', glyph = 'star', onHit = null, delay = 0, trail = null, spin = 0 } = {}) {
    const s = SCHOOL[school] || SCHOOL.arcane;
    const tint = color != null ? new THREE.Color(color) : null;
    let head = null;
    if (kind === 'arrow') head = arrowMesh();
    else if (kind === 'blade' || kind === 'shard') {
      head = new THREE.Mesh(geo(kind), new THREE.MeshBasicMaterial({ color: tint ? tint.clone().multiplyScalar(kind === 'shard' ? 1.8 : 1.2) : s.core }));
    } else if (kind === 'orb') head = new THREE.Mesh(new THREE.SphereGeometry(size, 12, 8), new THREE.MeshBasicMaterial({ color: tint ? tint.clone().multiplyScalar(2.4) : s.core }));
    const start = from.clone(), end = to.clone();
    const dist = start.distanceTo(end);
    const dur = Math.max(0.12, dist / speed);
    let t = -delay;
    if (head) { head.visible = false; this.scene.add(head); }
    const self = this;
    const pos = new THREE.Vector3();
    return this.add({ update(dt) {
      t += dt;
      if (t < 0) return true;
      const k = Math.min(1, t / dur);
      pos.lerpVectors(start, end, k);
      pos.y += Math.sin(k * Math.PI) * arc * dist * 0.08;
      if (head) {
        head.visible = true;
        head.position.copy(pos);
        if (kind === 'arrow' || kind === 'shard' || kind === 'blade') {
          _v.copy(end).sub(start).normalize();
          head.lookAt(_u.copy(head.position).add(_v));
          if (spin || kind === 'blade') head.rotateZ(t * (spin || 18));
        }
      }
      if (kind === 'glyph') self.glyph(pos, { glyph, count: 1, color: tint || s.spark, speed: 0, life: 0.06, size: size * 3.2, rot: spin ? t * spin : 0 });
      if (trail) trail(pos, k);
      else if (kind === 'orb') self.p.emit(pos, { count: 2, color: tint || s.spark, speed: 0.4, life: 0.35, size: size * 1.4, drag: 3 });
      if (k >= 1) { if (onHit) onHit(end); return false; }
      return true;
    }, dispose() { if (head) { self.scene.remove(head); if (kind === 'orb') head.geometry.dispose(); if (head.material) head.material.dispose && head.material.dispose(); } } });
  }

  // ---- lightning: a jagged beam that flickers ----
  beam(from, to, { school = 'lightning', color = null, time = 0.28, delay = 0, jag = 0.35 } = {}) {
    const s = SCHOOL[school] || SCHOOL.lightning;
    const pts = [];
    const segs = 10;
    for (let i = 0; i <= segs; i++) pts.push(new THREE.Vector3());
    const g = new THREE.BufferGeometry().setFromPoints(pts);
    const mat = new THREE.LineBasicMaterial({ color: color != null ? new THREE.Color(color).multiplyScalar(2.4) : s.core, transparent: true });
    const line = new THREE.Line(g, mat);
    line.frustumCulled = false;
    let t = -delay, flick = 0;
    const self = this;
    this.scene.add(line);
    const a = posOf(from), b = posOf(to);
    return this.add({ update(dt) {
      t += dt;
      if (t < 0) { line.visible = false; return true; }
      line.visible = true;
      if ((flick -= dt) <= 0) {
        flick = 0.04;
        const at = g.attributes.position;
        for (let i = 0; i <= segs; i++) {
          _v.lerpVectors(a, b, i / segs);
          const off = i === 0 || i === segs ? 0 : jag;
          at.setXYZ(i, _v.x + (Math.random() - 0.5) * off, _v.y + (Math.random() - 0.5) * off, _v.z + (Math.random() - 0.5) * off);
        }
        at.needsUpdate = true;
      }
      mat.opacity = Math.max(0, 1 - t / time);
      return t < time;
    }, dispose() { self.scene.remove(line); g.dispose(); mat.dispose(); } });
  }
  // a bolt that leaps from one body to the next, a spark where it touches
  chain(points, { school = 'lightning', color = null, step = 0.09, delay = 0, time = 0.3 } = {}) {
    for (let i = 0; i < points.length - 1; i++) {
      this.beam(points[i], points[i + 1], { school, color, delay: delay + i * step, time });
      this.after(delay + (i + 1) * step, () => this.impact(points[i + 1], school));
    }
  }
  // a straight, solid ray (a holy lance, an arcane beam): a glowing core in a softer sheath
  ray(from, to, { color = 0xffe8a0, width = 0.24, time = 0.45, delay = 0 } = {}) {
    const len = from.distanceTo(to);
    if (len < 0.05) return null;
    const outer = new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(1.6), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    const inner = new THREE.MeshBasicMaterial({ color: new THREE.Color(color).lerp(new THREE.Color(0xffffff), 0.6).multiplyScalar(2.6), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    const a = new THREE.Mesh(geo('beam'), outer), b = new THREE.Mesh(geo('beam'), inner);
    const grp = new THREE.Group();
    grp.add(a, b);
    grp.position.copy(from);
    grp.lookAt(to);
    a.scale.set(width, width, len); b.scale.set(width * 0.4, width * 0.4, len);
    this.scene.add(grp);
    let t = -delay;
    return this.add({ update: dt => {
      t += dt;
      if (t < 0) return true;
      const k = t / time;
      const o = k < 0.15 ? k / 0.15 : Math.max(0, 1 - (k - 0.15) / 0.85);
      outer.opacity = o * 0.55; inner.opacity = o;
      const w = width * (1 + Math.sin(t * 60) * 0.15) * (1 - k * 0.5);
      a.scale.set(w, w, len); b.scale.set(w * 0.4, w * 0.4, len);
      return k < 1;
    }, dispose: () => { this.scene.remove(grp); outer.dispose(); inner.dispose(); } });
  }
  // a stream between two bodies (a drain pulls toward `to`; a link flows both ways)
  tether(fromT, toT, { color = 0x7aff8a, time = 0.9, delay = 0, glyph = null, rate = 60, lift = 0.9, size = 0.3 } = {}) {
    let t = -delay, acc = 0;
    const a = new THREE.Vector3(), b = new THREE.Vector3(), mid = new THREE.Vector3();
    const curve = (k, out) => {
      // a gentle arc between the two chests
      const u = 1 - k;
      return out.set(u * u * a.x + 2 * u * k * mid.x + k * k * b.x, u * u * a.y + 2 * u * k * mid.y + k * k * b.y, u * u * a.z + 2 * u * k * mid.z + k * k * b.z);
    };
    return this.add({ update: dt => {
      t += dt;
      if (t < 0) return true;
      a.copy(posOf(fromT)); b.copy(posOf(toT));
      if (fromT.isObject3D) a.y += 1.1;
      if (toT.isObject3D) b.y += 1.1;
      mid.lerpVectors(a, b, 0.5).y += lift;
      acc += dt * rate;
      while (acc >= 1) {
        acc -= 1;
        const k = Math.random();
        curve(k, _v);
        curve(Math.min(1, k + 0.08), _u);
        const dir = _u.sub(_v).normalize().multiplyScalar(4);
        if (glyph && Math.random() < 0.35) this.glyph(_v, { glyph, count: 1, color, speed: 0.2, dir, life: 0.25, size: size * 1.8, drag: 0 });
        else this.p.emit(_v, { count: 1, color, speed: 0.2, dir, life: 0.22, size, drag: 0 });
      }
      return t < time;
    } });
  }

  // ---- from the sky ----
  // many small things falling on an area: arrows, shards, holy motes, notes
  rain(center, { count = 10, radius = 3, kind = 'arrow', school = 'physical', color = null, glyph = 'star', time = 0.6, height = 10, slant = 2.5, size = 0.18, delay = 0, onEach = null } = {}) {
    for (let i = 0; i < count; i++) {
      const a = Math.random() * Math.PI * 2, r = Math.sqrt(Math.random()) * radius;
      const at = new THREE.Vector3(center.x + Math.cos(a) * r, 0.15, center.z + Math.sin(a) * r);
      const from = at.clone().add(new THREE.Vector3(-slant, height, -slant * 0.6));
      this.projectile(from, at, { kind, school, color, glyph, size, speed: 24, arc: 0, delay: delay + (i / count) * time,
        onHit: p => { this.p.emit(p, { count: 6, color: color != null ? color : (SCHOOL[school] || SCHOOL.physical).spark, speed: 2.2, up: 1, life: 0.35, size: 0.16, gravity: 6, drag: 2 }); if (onEach) onEach(p); } });
    }
  }
  // one great body falling (a meteor, a hammer of light), trailing fire and smoke
  meteor(to, { school = 'fire', color = null, size = 0.55, height = 15, delay = 0, onHit = null, glyph = null } = {}) {
    const s = SCHOOL[school] || SCHOOL.fire;
    const from = to.clone().add(new THREE.Vector3(-4.5, height, -3));
    const tint = color != null ? color : s.spark;
    return this.projectile(from, to.clone().setY(0.3), { kind: glyph ? 'glyph' : 'orb', glyph, school, color, size, speed: 20, arc: 0, delay,
      trail: p => {
        this.p.emit(p, { count: 4, color: tint, speed: 0.8, life: 0.45, size: size * 1.6, drag: 2, jitter: size });
        this.p.emit(p, { count: 1, color: s.smoke, speed: 0.4, up: 0.4, life: 0.9, size: size * 2, grow: 0.8, drag: 1 });
        if (glyph) return;
      }, onHit });
  }

  // ---- along the ground ----
  // a front that sweeps away from `from` along dir (a shock line, a wave of sound or light)
  wave(from, dir, { length = 6, width = 2.6, time = 0.45, color = 0xffffff, glyph = null, delay = 0, y = 0.4, rate = 22 } = {}) {
    const d = dir.clone().setY(0).normalize();
    const side = new THREE.Vector3(-d.z, 0, d.x);
    let t = -delay, acc = 0;
    return this.add({ update: dt => {
      t += dt;
      if (t < 0) return true;
      const k = Math.min(1, t / time);
      acc += dt * rate * 10;
      const front = _v.copy(from).setY(y).addScaledVector(d, k * length);
      while (acc >= 1) {
        acc -= 1;
        const w = (Math.random() - 0.5) * width * (0.4 + k * 0.6);
        _u.copy(front).addScaledVector(side, w);
        if (glyph && Math.random() < 0.3) this.glyph(_u, { glyph, count: 1, color, speed: 0.6, up: 1.4, life: 0.4, size: 0.4 });
        else this.p.emit(_u, { count: 1, color, speed: 0.8, up: 1.2, life: 0.35, size: 0.26, drag: 2 });
      }
      return k < 1;
    } });
  }
  // a spray from the chest in a cone (breath, sand, notes, a hail of bolts)
  // a spray or a breath fanning out to `radius`: its front reaches it about when the ability lands
  // (abilityfx.js FIXED cone), the rest washing over it and fading (particles slow by their drag:
  // at full speed and this life they carry 0.8-1.5 radii)
  cone(from, dir, { radius = 7, angle = 0.9, color = 0xffffff, glyph = null, time = 0.3, delay = 0, rate = 120, size = 0.3 } = {}) {
    const d = dir.clone().normalize();
    let t = -delay, acc = 0;
    const speed = radius / 0.3;
    return this.add({ update: dt => {
      t += dt;
      if (t < 0) return true;
      acc += dt * rate;
      while (acc >= 1) {
        acc -= 1;
        const yaw = (Math.random() - 0.5) * angle;
        _v.copy(d).applyAxisAngle(UP, yaw).multiplyScalar(speed);
        _v.y += (Math.random() - 0.3) * 1.5;
        if (glyph && Math.random() < 0.35) this.glyph(from, { glyph, count: 1, color, speed: 1, spread: 0.15, dir: _v, life: 0.38, size: size * 1.4, drag: 0.6, spin: 4 });
        else this.p.emit(from, { count: 1, color, speed: 1, spread: 0.15, dir: _v, life: 0.38, size, drag: 0.6 });
      }
      return t < time;
    } });
  }
  // a column bursting up out of the ground
  geyser(p, { color = 0xffffff, glyph = null, height = 3.2, time = 0.5, radius = 0.45, delay = 0 } = {}) {
    let t = -delay, acc = 0;
    return this.add({ update: dt => {
      t += dt;
      if (t < 0) return true;
      acc += dt * 90;
      while (acc >= 1) {
        acc -= 1;
        const a = Math.random() * Math.PI * 2, r = Math.random() * radius;
        _v.set(p.x + Math.cos(a) * r, 0.1, p.z + Math.sin(a) * r);
        if (glyph && Math.random() < 0.3) this.glyph(_v, { glyph, count: 1, color, speed: 0.3, up: height * 2.2, life: 0.5, size: 0.4, gravity: 3, spin: 3 });
        else this.p.emit(_v, { count: 1, color, speed: 0.3, up: height * 2.4, life: 0.45, size: 0.28, gravity: 4, drag: 0.6 });
      }
      return t < time;
    } });
  }

  // ---- a column of light from the sky (holy smite, heals, judgement) ----
  pillar(p, { school = 'holy', color = null, radius = 0.9, height = 7, time = 0.7, delay = 0 } = {}) {
    const s = SCHOOL[school] || SCHOOL.holy;
    const g = new THREE.CylinderGeometry(radius, radius * 1.15, height, 20, 1, true).translate(0, height / 2, 0);
    const mat = new THREE.MeshBasicMaterial({ color: color != null ? new THREE.Color(color).multiplyScalar(1.2) : s.core.clone().multiplyScalar(0.6), transparent: true, opacity: 0, side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending, depthWrite: false });
    const m = new THREE.Mesh(g, mat);
    m.position.copy(posOf(p)).setY(0);
    let t = -delay, burst = false;
    const self = this;
    this.scene.add(m);
    return this.add({ update(dt) {
      t += dt;
      if (t < 0) return true;
      const k = t / time;
      mat.opacity = (k < 0.2 ? k / 0.2 : Math.max(0, 1 - (k - 0.2) / 0.8)) * 0.42;
      m.scale.set(1 - k * 0.4, 1, 1 - k * 0.4);
      if (!burst) { burst = true; self.p.emit(_v.copy(m.position).setY(0.3), { count: 26, color: color != null ? color : s.spark, speed: 3, up: 1.5, life: 0.7, size: 0.26, drag: 2 }); }
      return k < 1;
    }, dispose() { self.scene.remove(m); g.dispose(); mat.dispose(); } });
  }

  // ---- swirl around a body: heals, buffs, auras, summons (glyphs when `glyph` is set) ----
  swirl(target, { school = 'holy', color = null, glyph = null, time = 1.0, rise = 2.2, count = 3, radius = 0.7 } = {}) {
    const s = SCHOOL[school] || SCHOOL.holy;
    const tint = color != null ? color : s.spark;
    let t = 0, acc = 0;
    const self = this;
    return this.add({ update(dt) {
      t += dt; acc += dt;
      const p = posOf(target);
      while (acc > 0.03) {
        acc -= 0.03;
        for (let i = 0; i < count; i++) {
          const a = t * 9 + i * (Math.PI * 2 / count);
          _v.set(p.x + Math.cos(a) * radius, (p.y || 0) + (t / time) * rise, p.z + Math.sin(a) * radius);
          if (glyph) self.glyph(_v, { glyph, count: 1, color: tint, speed: 0.1, up: 0.4, life: 0.5, size: 0.34 });
          else self.p.emit(_v, { count: 1, color: tint, speed: 0.2, up: 0.6, life: 0.6, size: 0.2, drag: 2 });
        }
      }
      return t < time;
    } });
  }
  // things circling a body for a while (runes, blades, notes, motes)
  orbit(target, { glyph = 'star', color = 0xffffff, count = 3, radius = 0.9, time = 2, size = 0.36, height = 1.1, speed = 4, rise = 0, delay = 0 } = {}) {
    let t = -delay, acc = 0;
    return this.add({ update: dt => {
      t += dt;
      if (t < 0) return true;
      acc += dt;
      const p = posOf(target);
      while (acc > 0.025) {
        acc -= 0.025;
        for (let i = 0; i < count; i++) {
          const a = t * speed + i * (Math.PI * 2 / count);
          _v.set(p.x + Math.cos(a) * radius, (p.y || 0) + height + rise * (t / time) + Math.sin(t * 3 + i) * 0.12, p.z + Math.sin(a) * radius);
          this.glyph(_v, { glyph, count: 1, color, speed: 0, life: 0.14, size, rot: -a });
        }
      }
      return t < time;
    } });
  }

  // ---- ground ring that expands (AoE, shouts, stomps); y lifts it (sound rings) ----
  shockwave(p, { school = 'physical', color = null, radius = 4, time = 0.45, delay = 0, y = 0.08, thin = false } = {}) {
    const s = SCHOOL[school] || SCHOOL.physical;
    const mat = new THREE.MeshBasicMaterial({ color: color != null ? new THREE.Color(color).multiplyScalar(2) : s.core, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    const m = new THREE.Mesh(geo(thin ? 'thinring' : 'ring'), mat);
    m.rotation.x = -Math.PI / 2;
    const at = posOf(p);
    m.position.copy(at).setY(y);
    let t = -delay;
    const self = this;
    this.scene.add(m);
    return this.add({ update(dt) {
      t += dt;
      if (t < 0) return true;
      const k = t / time;
      m.scale.setScalar(0.3 + k * radius);
      if (p.isObject3D) m.position.set(at.x, y, at.z);
      mat.opacity = Math.max(0, 1 - k) * 0.9;
      return k < 1;
    }, dispose() { self.scene.remove(m); mat.dispose(); } });
  }

  // ---- ground sigils and marks: a decal drawn in glyphs.js, tinted, turning slowly ----
  sigilTexture(name, variant = 0) {
    const key = `${name}#${variant}`;
    if (!this.textures.has(key)) {
      const cv = sigilCanvas(name, name === 'scorch' ? 128 : 256, variant + 1);
      const tex = cv ? new THREE.CanvasTexture(cv) : null;
      if (tex) tex.colorSpace = THREE.SRGBColorSpace;
      this.textures.set(key, tex);
    }
    return this.textures.get(key);
  }
  decal(p, { sigil = 'ring', radius = 2, time = 1.2, color = 0xffffff, bright = 1.6, spin = 0.5, delay = 0, follow = null, dark = false, opacity = 0.9, grow = 0.25, y = 0.05 } = {}) {
    if (!this.take('decals')) return null;
    const tex = this.sigilTexture(sigil, sigil === 'crack' ? Math.floor(Math.random() * 3) : 0);
    const mat = new THREE.MeshBasicMaterial({ map: tex, color: dark ? new THREE.Color(0x000000) : new THREE.Color(color).multiplyScalar(bright),
      transparent: true, opacity: 0, depthWrite: false, blending: dark ? THREE.NormalBlending : THREE.AdditiveBlending,
      polygonOffset: true, polygonOffsetFactor: -2 });
    const m = new THREE.Mesh(geo('plane'), mat);
    m.renderOrder = 2;
    m.position.copy(posOf(p)).setY(y);
    m.rotation.y = Math.random() * Math.PI * 2;
    this.scene.add(m);
    let t = -delay;
    return this.add({ update: dt => {
      t += dt;
      if (t < 0) return true;
      const k = t / time;
      const o = k < 0.15 ? k / 0.15 : k > 0.7 ? Math.max(0, (1 - k) / 0.3) : 1;
      mat.opacity = o * opacity;
      m.scale.setScalar(radius * (1 - grow + grow * Math.min(1, k * 4)));
      m.rotation.y += spin * dt;
      if (follow) m.position.copy(posOf(follow)).setY(y);
      return k < 1;
    }, dispose: () => { this.scene.remove(m); mat.dispose(); this.give('decals'); } });
  }

  // ---- growths: spikes, ice, crystals, bones, bars, thorns, vines, stones out of the ground ----
  growth(p, { kind = 'spike', count = 8, radius = 1.4, time = 1.4, height = 1.3, color = 0x88cc66, glow = 0.35, delay = 0, ring = true, tilt = 0.35, follow = null } = {}) {
    if (!this.take('growths')) return null;
    const shape = { ice: 'crystal', crystals: 'crystal', bones: 'spike', thorns: 'thorn', bars: 'bar', vines: 'vine', stones: 'stone', spikes: 'spike', spears: 'bar' }[kind] || 'spike';
    const glassy = kind === 'ice' || kind === 'crystals';
    const mat = new THREE.MeshStandardMaterial({ color, emissive: new THREE.Color(color).multiplyScalar(glow), roughness: glassy ? 0.15 : 0.7,
      metalness: kind === 'bars' ? 0.7 : 0.05, transparent: true, opacity: glassy ? 0.85 : 1 });
    const mesh = new THREE.InstancedMesh(geo(shape), mat, count);
    mesh.frustumCulled = false;
    const base = posOf(p).clone().setY(0);
    const parts = [];
    for (let i = 0; i < count; i++) {
      const a = ring ? (i / count) * Math.PI * 2 + Math.random() * 0.3 : Math.random() * Math.PI * 2;
      const r = ring ? radius * (0.85 + Math.random() * 0.3) : Math.sqrt(Math.random()) * radius;
      parts.push({ x: Math.cos(a) * r, z: Math.sin(a) * r, a, h: height * (0.65 + Math.random() * 0.55), lean: tilt * (0.6 + Math.random() * 0.8), w: 0.8 + Math.random() * 0.5, spin: Math.random() * 6 });
    }
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3(), tr = new THREE.Vector3();
    this.scene.add(mesh);
    let t = -delay;
    const place = s => {
      const at = follow ? posOf(follow) : base;
      for (let i = 0; i < count; i++) {
        const pt = parts[i];
        // lean away from the centre (a cage's bars stand straight)
        e.set(kind === 'bars' ? 0 : Math.sin(pt.a) * pt.lean, pt.spin, kind === 'bars' ? 0 : -Math.cos(pt.a) * pt.lean, 'XYZ');
        q.setFromEuler(e);
        const k = Math.max(0.001, s);
        sc.set(pt.w, kind === 'stones' ? pt.w * k : pt.h * k, pt.w);
        tr.set(at.x + pt.x, kind === 'stones' ? -0.4 + 0.4 * k : 0, at.z + pt.z);
        m4.compose(tr, q, sc);
        mesh.setMatrixAt(i, m4);
      }
      mesh.instanceMatrix.needsUpdate = true;
    };
    place(0);
    return this.add({ update: dt => {
      t += dt;
      if (t < 0) return true;
      const k = t / time;
      // up fast with a little overshoot, stand, then sink away
      const s = k < 0.15 ? Math.sin(k / 0.15 * Math.PI * 0.5) * 1.08 : k > 0.78 ? Math.max(0, (1 - k) / 0.22) : 1;
      place(s);
      return k < 1;
    }, dispose: () => { this.scene.remove(mesh); mesh.dispose(); mat.dispose(); this.give('growths'); } });
  }

  // ---- shells: a shield around a body, a dome over the ground ----
  bubble(target, { color = 0x9ad0ff, radius = 1.15, time = 2, delay = 0, y = 1.0, opacity = 0.9 } = {}) {
    if (!this.take('bubbles')) return null;
    const mat = shellMaterial(color, 0);
    const m = new THREE.Mesh(geo('sphere'), mat);
    this.scene.add(m);
    let t = -delay;
    return this.add({ update: dt => {
      t += dt;
      if (t < 0) { m.visible = false; return true; }
      m.visible = true;
      const k = t / time;
      const o = k < 0.12 ? k / 0.12 : k > 0.8 ? Math.max(0, (1 - k) / 0.2) : 1;
      mat.uniforms.uOpacity.value = o * opacity;
      const p = posOf(target);
      m.position.set(p.x, (p.y || 0) + y, p.z);
      m.scale.setScalar(radius * (k < 0.12 ? 0.7 + 0.3 * (k / 0.12) : 1 + Math.sin(t * 5) * 0.02));
      return k < 1;
    }, dispose: () => { this.scene.remove(m); mat.dispose(); this.give('bubbles'); } });
  }
  dome(p, { color = 0xffe8a0, radius = 4, time = 2.4, delay = 0, opacity = 0.7 } = {}) {
    if (!this.take('bubbles')) return null;
    const mat = shellMaterial(color, 0);
    const m = new THREE.Mesh(geo('dome'), mat);
    m.position.copy(posOf(p)).setY(0);
    this.scene.add(m);
    let t = -delay;
    return this.add({ update: dt => {
      t += dt;
      if (t < 0) { m.visible = false; return true; }
      m.visible = true;
      const k = t / time;
      mat.uniforms.uOpacity.value = (k < 0.15 ? k / 0.15 : k > 0.75 ? Math.max(0, (1 - k) / 0.25) : 1) * opacity;
      m.scale.set(radius, radius * 0.8 * Math.min(1, k * 5), radius);
      return k < 1;
    }, dispose: () => { this.scene.remove(m); mat.dispose(); this.give('bubbles'); } });
  }

  // ---- on a body: wings of light, a halo ----
  wings(target, { color = 0xffe8a0, time = 1.8, span = 1.7, y = 1.2, flap = 1.4, delay = 0 } = {}) {
    if (!this.take('meshes')) return null;
    if (!this.textures.has('wing')) { const cv = wingCanvas(256); this.textures.set('wing', cv ? new THREE.CanvasTexture(cv) : null); }
    const mat = new THREE.MeshBasicMaterial({ map: this.textures.get('wing'), color: new THREE.Color(color).multiplyScalar(1.8), transparent: true, opacity: 0,
      blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    const grp = new THREE.Group();
    const left = new THREE.Mesh(geo('wing'), mat), right = new THREE.Mesh(geo('wing'), mat);
    right.scale.x = -1;
    left.scale.setScalar(span); right.scale.set(-span, span, span);
    grp.add(left, right);
    this.scene.add(grp);
    let t = -delay;
    const root = target.isObject3D ? target : null;
    return this.add({ update: dt => {
      t += dt;
      if (t < 0) { grp.visible = false; return true; }
      grp.visible = true;
      const k = t / time;
      mat.opacity = (k < 0.15 ? k / 0.15 : k > 0.7 ? Math.max(0, (1 - k) / 0.3) : 1) * 0.85;
      const p = posOf(target);
      grp.position.set(p.x, (p.y || 0) + y + k * 0.25, p.z);
      if (root) { grp.rotation.y = root.rotation.y; grp.position.addScaledVector(_v.set(Math.sin(root.rotation.y), 0, Math.cos(root.rotation.y)), -0.22); }
      const beat = 0.35 + Math.sin(t * flap * Math.PI * 2) * 0.35;
      left.rotation.y = -beat; right.rotation.y = beat;
      return k < 1;
    }, dispose: () => { this.scene.remove(grp); mat.dispose(); this.give('meshes'); } });
  }
  halo(target, { color = 0xffe08a, time = 2, y = 2.3, radius = 0.32, delay = 0 } = {}) {
    if (!this.take('meshes')) return null;
    const mat = new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(2.4), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    const m = new THREE.Mesh(geo('halo'), mat);
    m.scale.setScalar(radius);
    this.scene.add(m);
    let t = -delay;
    return this.add({ update: dt => {
      t += dt;
      if (t < 0) { m.visible = false; return true; }
      m.visible = true;
      const k = t / time;
      mat.opacity = k < 0.15 ? k / 0.15 : k > 0.75 ? Math.max(0, (1 - k) / 0.25) : 1;
      const p = posOf(target);
      m.position.set(p.x, (p.y || 0) + y + Math.sin(t * 3) * 0.04, p.z);
      m.rotation.y += dt * 1.5;
      return k < 1;
    }, dispose: () => { this.scene.remove(m); mat.dispose(); this.give('meshes'); } });
  }

  // ---- a war banner planted in the ground: it slams down, its cloth waves, it stands for a
  // while beside a glowing sigil, then sinks away ----
  banner(p, { color = 0xc8401e, sigil = 'crest', time = 15, height = 3.2, glow = 0xffa040 } = {}) {
    if (!this.take('meshes')) return null;
    const key = `banner#${color}#${sigil}`;
    if (!this.textures.has(key)) {
      const cv = bannerCanvas(`#${new THREE.Color(color).getHexString()}`, sigil);
      const tex = cv ? new THREE.CanvasTexture(cv) : null;
      if (tex) tex.colorSpace = THREE.SRGBColorSpace;
      this.textures.set(key, tex);
    }
    const grp = new THREE.Group();
    const wood = new THREE.MeshStandardMaterial({ color: 0x8a6a42, roughness: 0.8, emissive: 0x1a1008 });
    const steel = new THREE.MeshStandardMaterial({ color: 0xd8dce4, metalness: 0.8, roughness: 0.3, emissive: new THREE.Color(glow).multiplyScalar(0.25) });
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.065, height, 8).translate(0, height / 2, 0), wood);
    const tip = new THREE.Mesh(new THREE.ConeGeometry(0.1, 0.32, 6).translate(0, height + 0.16, 0), steel);
    const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 1.2, 6).rotateZ(Math.PI / 2).translate(0.6, height - 0.12, 0), wood);
    const clothGeo = new THREE.PlaneGeometry(1.15, 1.6, 14, 4).translate(0.62, height - 0.95, 0);
    const base = clothGeo.attributes.position.array.slice();
    // the cloth glows faintly from within, so it reads in a dark crypt too
    const cloth = new THREE.Mesh(clothGeo, new THREE.MeshStandardMaterial({ map: this.textures.get(key), emissive: 0xffffff, emissiveMap: this.textures.get(key), emissiveIntensity: 0.45,
      side: THREE.DoubleSide, roughness: 0.9, transparent: true, alphaTest: 0.5 }));
    for (const m of [pole, tip, bar, cloth]) { m.castShadow = true; grp.add(m); }
    const at = posOf(p).clone().setY(0);
    grp.position.copy(at);
    // the cloth turned toward the view (a flag seen edge-on is a stick), a little askew
    const cam = this.engine.camera.position;
    grp.rotation.y = Math.atan2(cam.x - at.x, cam.z - at.z) + (Math.random() - 0.5) * 0.6;
    this.scene.add(grp);
    this.decal(at, { sigil, radius: 2.4, time, color: glow, spin: 0.25, opacity: 0.55 });
    let t = 0, landed = false;
    return this.add({ update: dt => {
      t += dt;
      // down hard from above, then standing; sinking at the end
      grp.position.y = t < 0.18 ? (1 - t / 0.18) * 3 : t > time - 0.6 ? -height * Math.min(1, (t - (time - 0.6)) / 0.6) : 0;
      if (!landed && t >= 0.18) {
        landed = true;
        this.shockwave(at, { color: glow, radius: 3.5, time: 0.5 });
        this.p.emit(at.clone().setY(0.3), { count: 26, color: 0xb8a888, speed: 3, up: 1, life: 0.7, size: 0.45, grow: 0.5, drag: 2 });
      }
      // the cloth ripples from the pole outward
      const a = clothGeo.attributes.position;
      for (let i = 0; i < a.count; i++) {
        const u = Math.max(0, base[i * 3] - 0.05) / 1.15;
        a.setZ(i, base[i * 3 + 2] + Math.sin(t * 5 + u * 4.5 + base[i * 3 + 1]) * 0.14 * u);
      }
      a.needsUpdate = true;
      if (Math.random() < dt * 8) this.p.emit(at.clone().setY(height + 0.2), { count: 1, color: glow, bright: 1.4, speed: 0.4, up: 0.6, life: 0.8, size: 0.16 });
      return t < time;
    }, dispose: () => {
      this.scene.remove(grp);
      for (const m of [pole, tip, bar, cloth]) { m.geometry.dispose(); }
      wood.dispose(); steel.dispose(); cloth.material.dispose();
      this.give('meshes');
    } });
  }

  // ---- telegraph: a danger zone on the floor that fills until the blow lands ----
  // ---- a singularity collapsing: sparks fall in from all around, a black core swells with a
  // burning rim, then it implodes in a flash and a ring ----
  implode(p, { color = 0xb070ff, radius = 6, time = 0.9 } = {}) {
    if (!this.take('meshes')) return null;
    const at = posOf(p).clone();
    at.y = Math.max(0, at.y || 0) + 2.1;        // above their heads, where everyone can see it
    const core = new THREE.Mesh(geo('sphere'), new THREE.MeshBasicMaterial({ color: 0x040006, transparent: true, opacity: 0, depthWrite: false }));
    const rim = new THREE.Mesh(geo('sphere'), new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(2.2), transparent: true, opacity: 0,
      blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.BackSide }));
    core.renderOrder = 6;
    this.scene.add(core, rim);
    this.decal(at.clone().setY(0), { sigil: 'runeCircle', radius: radius * 0.8, time: time + 0.4, color, spin: -2.6, grow: -0.5, opacity: 0.8 });
    const d = new THREE.Vector3();
    let t = 0, burst = false;
    return this.add({ update: dt => {
      t += dt;
      const k = Math.min(1, t / time);
      // the pull: sparks fall in from the edge toward the core
      for (let i = Math.ceil(dt * 110); i > 0 && k < 0.9; i--) {
        const a = Math.random() * Math.PI * 2, r = radius * (0.55 + Math.random() * 0.45);
        _v.set(at.x + Math.cos(a) * r, 0.2 + Math.random() * 2.2, at.z + Math.sin(a) * r);
        d.set(at.x - _v.x, at.y - _v.y, at.z - _v.z).multiplyScalar(1 / 0.5);
        this.p.emit(_v, { count: 1, color, bright: 1.7, speed: 1, spread: 0.04, dir: d, drag: 0, life: 0.42, size: 0.17 });
      }
      // the core swells dark with its rim burning, then collapses to nothing
      const s = k < 0.85 ? 0.3 + k * 1.4 : Math.max(0.01, 1 - (k - 0.85) / 0.15) * 1.5;
      core.scale.setScalar(s);
      rim.scale.setScalar(s * 1.2);
      core.material.opacity = Math.min(0.94, k * 2.2);
      rim.material.opacity = Math.min(0.85, k * 1.7);
      core.position.copy(at);
      rim.position.copy(at);
      if (!burst && k >= 1) {
        burst = true;
        core.visible = rim.visible = false;
        this.light(at, color, 10, 0.35);
        this.shockwave(at.clone().setY(0), { color, radius: radius * 1.1, time: 0.5 });
        this.shockwave(at.clone().setY(0), { school: 'arcane', radius: radius * 0.6, delay: 0.08 });
        this.p.emit(at, { count: 70, color, bright: 2.2, speed: 7.5, life: 0.6, size: 0.3, drag: 2.6 });
        this.glyph(at, { glyph: 'star', count: 12, color: 0xe8d8ff, speed: 6, life: 0.6, size: 0.4, drag: 2.5, spin: 6 });
        this.screen('#b49aff', { time: 0.32, opacity: 0.22 });
      }
      return t < time + 0.05;
    }, dispose: () => { this.scene.remove(core, rim); core.material.dispose(); rim.material.dispose(); this.give('meshes'); } });
  }

  // ---- a seraph above the caster: their own shape, larger, made of light, with great wings and
  // a halo; feathers drift down from it while it stands ----
  seraph(target, { color = 0xfff0c8, time = 15 } = {}) {
    const root = target && target.isObject3D ? target : null;
    if (!root) return null;
    const anchor = new THREE.Object3D();
    this.scene.add(anchor);
    this.wings(anchor, { color, time, span: 2.7, y: 1.55, flap: 0.6 });
    this.halo(anchor, { color: 0xffe08a, time, y: 3.0, radius: 0.46 });
    let ghost = null, mat = null;
    if (this.take('ghosts')) {
      try { ghost = SkeletonUtils.clone(root); } catch (err) { ghost = null; this.give('ghosts'); }
    }
    if (ghost) {
      mat = new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(1.5), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
      ghost.traverse(o => { if (o.isMesh) { o.material = mat; o.castShadow = false; o.receiveShadow = false; } });
      ghost.scale.copy(root.scale).multiplyScalar(1.45);
      this.scene.add(ghost);
    }
    this.pillar(root.position.clone().setY(0), { color, radius: 1.1, height: 9, time: 0.9 });
    let t = 0;
    return this.add({ update: dt => {
      t += dt;
      const k = t / time, rp = root.position, yaw = root.rotation.y;
      anchor.position.set(rp.x - Math.sin(yaw) * 0.7, rp.y + 1.8 + Math.sin(t * 1.6) * 0.12, rp.z - Math.cos(yaw) * 0.7);
      anchor.rotation.y = yaw;
      if (ghost) {
        mat.opacity = (k < 0.08 ? k / 0.08 : k > 0.85 ? Math.max(0, (1 - k) / 0.15) : 1) * 0.5;
        ghost.position.copy(anchor.position);
        ghost.rotation.y = yaw;
      }
      if (Math.random() < dt * 5) {
        this.glyph(_v.set(anchor.position.x + (Math.random() - 0.5) * 2.4, anchor.position.y + 1.4, anchor.position.z + (Math.random() - 0.5) * 2.4),
          { glyph: 'feather', count: 1, color, speed: 0.15, life: 1.8, size: 0.32, gravity: 0.5, drag: 1.4, spin: 2 });
      }
      return t < time;
    }, dispose: () => { this.scene.remove(anchor); if (ghost) { this.scene.remove(ghost); mat.dispose(); this.give('ghosts'); } } });
  }

  // ---- a lich: grave-green glow on the body, a crown of grave-fire, skulls circling the head,
  // a ring of bones on the ground that follows ----
  lich(root, { color = 0x7aff9a, time = 18 } = {}) {
    if (!root) return null;
    this.tint(root, color, { time, strength: 0.42, hold: Math.max(0.5, (time - 0.8) / time) });
    this.orbit(root, { glyph: 'skull', color, count: 4, radius: 0.85, time, size: 0.36, height: 2.15, speed: 2.4 });
    this.decal(root.position.clone().setY(0), { sigil: 'boneCircle', radius: 1.7, time, color, spin: 0.3, follow: root, opacity: 0.7 });
    this.swirl(root, { color, glyph: 'wisp', time: 1.2, rise: 2.6, count: 4 });
    let t = 0;
    return this.add({ update: dt => {
      t += dt;
      const p = root.position;
      // the crown of grave-fire above the head
      for (let i = Math.ceil(dt * 26); i > 0; i--) {
        const a = Math.random() * Math.PI * 2;
        this.p.emit(_v.set(p.x + Math.cos(a) * 0.2, p.y + 2.0, p.z + Math.sin(a) * 0.2), { count: 1, color, bright: 1.8, speed: 0.15, up: 1.4, life: 0.45, size: 0.2, drag: 0.6 });
      }
      if (Math.random() < dt * 4) {
        this.glyph(_v.set(p.x + (Math.random() - 0.5) * 1.3, p.y + 0.3 + Math.random() * 1.2, p.z + (Math.random() - 0.5) * 1.3),
          { glyph: 'wisp', count: 1, color, speed: 0.1, up: 0.5, life: 1.2, size: 0.28, drag: 1 });
      }
      return t < time;
    } });
  }

  telegraph(center, { shape = 'circle', radius = 3, angle = Math.PI / 2, facing = 0, time = 1.5, color = 0xff3a28 } = {}) {
    const g = new THREE.Group();
    const thetaStart = shape === 'cone' ? facing - angle / 2 : 0, thetaLen = shape === 'cone' ? angle : Math.PI * 2;
    const baseGeo = new THREE.CircleGeometry(1, 48, thetaStart, thetaLen);
    const edgeGeo = new THREE.RingGeometry(0.96, 1, 48, 1, thetaStart, thetaLen);
    const fillMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.16, depthWrite: false });
    const edgeMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(2), transparent: true, opacity: 0.85, depthWrite: false });
    const growMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.32, depthWrite: false });
    const base = new THREE.Mesh(baseGeo, fillMat), edge = new THREE.Mesh(edgeGeo, edgeMat), grow = new THREE.Mesh(baseGeo, growMat);
    for (const m of [base, edge, grow]) { m.rotation.x = -Math.PI / 2; m.renderOrder = 3; g.add(m); }
    // circle angles start on +X and turn toward -Z in this flat frame; match world yaw
    g.rotation.y = 0;
    g.position.copy(center).setY(0.06);
    g.scale.setScalar(radius);
    let t = 0;
    const self = this;
    this.scene.add(g);
    const item = this.add({ update(dt) {
      t += dt;
      if (item.fading != null) {          // broken before it landed: the mark drains away
        item.fading -= dt;
        const a = Math.max(0, item.fading / 0.3);
        fillMat.opacity = 0.16 * a; edgeMat.opacity = 0.85 * a; growMat.opacity = 0.32 * a;
        g.scale.setScalar(radius * (1 + (1 - a) * 0.15));
        return item.fading > 0;
      }
      const k = Math.min(1, t / time);
      grow.scale.setScalar(k);
      edgeMat.opacity = 0.6 + Math.sin(t * 18) * 0.25 * k;
      if (item.follow) g.position.copy(item.follow.position).setY(0.06);
      return t < time + 0.15 && !item.cancelled;
    }, dispose() { self.scene.remove(g); baseGeo.dispose(); edgeGeo.dispose(); fillMat.dispose(); edgeMat.dispose(); growMat.dispose(); } });
    item.cancel = () => { item.cancelled = true; };
    item.fade = () => { if (item.fading == null) item.fading = 0.3; };
    return item;
  }
}

// arrows share their parts (a volley or an arrow rain makes dozens)
let ARROW = null;
function arrowMesh() {
  if (!ARROW) ARROW = {
    shaft: new THREE.CylinderGeometry(0.025, 0.025, 0.9, 5).rotateX(Math.PI / 2), wood: new THREE.MeshStandardMaterial({ color: 0x8a6a42 }),
    tip: new THREE.ConeGeometry(0.05, 0.16, 6).rotateX(Math.PI / 2).translate(0, 0, 0.5), steel: new THREE.MeshStandardMaterial({ color: 0xc8ccd4, metalness: 0.6, roughness: 0.3 }),
    fl: new THREE.BoxGeometry(0.12, 0.01, 0.16).translate(0, 0, -0.4), feather: new THREE.MeshStandardMaterial({ color: 0xe8e0d0 }),
  };
  const g = new THREE.Group();
  g.add(new THREE.Mesh(ARROW.shaft, ARROW.wood), new THREE.Mesh(ARROW.tip, ARROW.steel), new THREE.Mesh(ARROW.fl, ARROW.feather));
  return g;
}
