// What lingers round a character whose gear or standing has earned it (gearlook.js plan.adorn):
// faint motes in their class's colour from level 45, sparks off a weapon whose element glows
// (tier 4 and up), a slow ring on the ground under a full set or a legendary, and a
// legendary's glow breathing in and out. Every fx.js effect is timed and gone, so these are
// kept here, per actor, for as long as they wear it.
//
// Cheap by design: the motes and sparks are a particle or two a frame from fx's shared pool;
// the ring is one small additive quad. Only the hero and the nearest few others are adorned
// (BUDGET by quality tier), and nobody further than NEAR.
import * as THREE from 'three';
import { THEMES } from './abilityfx.js';
import { SCHOOL } from './fx.js';

const BUDGET = { low: 0, med: 4, high: 8, gallery: 200 };    // others adorned besides the hero
const NEAR = 22;
// a set's accent colour (shared/items.js SET_THEMES)
const SET_ACCENT = { miners_garb: 0xe8b860, forest_stalker: 0x9ad06a, drow_shadow: 0xb08aff, pharaohs_legacy: 0xffe9a8,
  sewer_rat: 0xb0b070, dragonscale: 0x8ae060, necromancers_regalia: 0x9adba0, chaos_weave: 0xe08aff,
  apocalypse_raiment: 0xe0402a, frostlords_mantle: 0xbfe2ff };
const LEGENDARY = 0xffd56a;
const _p = new THREE.Vector3();

const wanted = a => !!(a && (a.motes || a.aura || a.legendary || a.element));

export class Adorn {
  setTier(tier) { this.tier = tier; }      // graphics quality, changed in Settings

  constructor(engine, fx) {
    this.engine = engine;
    this.fx = fx;
    this.tier = (engine.quality && engine.quality.name) || 'high';
    this.on = new Map();         // actor -> what it has
  }

  // each frame: the hero, and everyone else who is dressed (actors with .gear)
  update(dt, t, hero, others = []) {
    const focus = hero && hero.root ? hero.root.position : null;
    const keep = new Set();
    if (hero && hero.gear && wanted(hero.gear.plan.adorn)) keep.add(hero);
    const near = [];
    for (const a of others) {
      if (!a || !a.gear || !a.root || !a.root.parent || !wanted(a.gear.plan.adorn)) continue;
      const d = focus ? a.root.position.distanceTo(focus) : 0;
      if (d < NEAR) near.push([d, a]);
    }
    near.sort((x, y) => x[0] - y[0]);
    for (const [, a] of near.slice(0, BUDGET[this.tier] ?? BUDGET.high)) keep.add(a);
    for (const [a, s] of this.on) if (!keep.has(a) || s.plan !== a.gear.plan) this.drop(a);
    for (const a of keep) {
      let s = this.on.get(a);
      if (!s) { s = this.make(a); this.on.set(a, s); }
      this.tick(a, s, dt, t);
    }
  }

  make(a) {
    const plan = a.gear.plan, ad = plan.adorn;
    const s = { plan, base: plan.glow, motesT: Math.random(), sparkT: Math.random(), ring: null };
    if (ad.motes) { const cls = ad.motes.replace(/^class_/, ''); s.motes = (THEMES[cls] || THEMES.creature).core; }
    if (ad.element) s.spark = (SCHOOL[ad.element] || SCHOOL.arcane).spark;
    if (ad.legendary) s.pulse = true;
    const ringColour = ad.legendary ? LEGENDARY : ad.aura === 'set' && ad.set ? SET_ACCENT[ad.set] : null;
    if (ringColour && this.fx.sigilTexture) {
      const tex = this.fx.sigilTexture(ad.legendary ? 'sunwheel' : 'ring');
      if (tex) {
        const mat = new THREE.MeshBasicMaterial({ map: tex, color: new THREE.Color(ringColour).multiplyScalar(1.3), transparent: true,
          opacity: 0.32, depthWrite: false, blending: THREE.AdditiveBlending, polygonOffset: true, polygonOffsetFactor: -2 });
        const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), mat);
        m.scale.setScalar(ad.legendary ? 2.3 : 1.9);
        m.renderOrder = 2;
        this.engine.scene.add(m);
        s.ring = m;
      }
    }
    // the weapon hand, for its sparks
    if (s.spark) a.root.traverse(o => { if (!s.hand && o.isBone && o.name === (ad.hand || 'handslotr')) s.hand = o; });
    return s;
  }

  tick(a, s, dt, t) {
    const pos = a.root.position;
    if (s.ring) {
      s.ring.position.set(pos.x, pos.y + 0.04, pos.z);
      s.ring.rotation.y += dt * 0.25;
      s.ring.material.opacity = 0.26 + 0.08 * Math.sin(t * 1.3);
    }
    // a legendary's light breathes
    if (s.pulse && a.gear.glow) a.gear.glow.value = s.base * (1 + 0.35 * Math.sin(t * 2.1));
    if (!this.fx.near(pos, NEAR)) return;
    if (s.motes && (s.motesT -= dt) <= 0) {
      s.motesT = 0.09 + Math.random() * 0.09;
      _p.set(pos.x + (Math.random() - 0.5) * 1.1, pos.y + 0.3 + Math.random() * 1.6, pos.z + (Math.random() - 0.5) * 1.1);
      this.fx.p.emit(_p, { count: 1, color: s.motes, bright: 1.6, speed: 0.12, up: 0.35, life: 2.2, size: 0.14, drag: 0.4 });
    }
    if (s.spark && s.hand && (s.sparkT -= dt) <= 0) {
      s.sparkT = 0.09 + Math.random() * 0.08;
      s.hand.localToWorld(_p.set(0, 0.25 + Math.random() * 0.7, 0));      // along the blade
      this.fx.p.emit(_p, { count: 1, color: s.spark, bright: 1.6, speed: 0.35, up: 0.5, life: 0.7, size: 0.08, drag: 1, jitter: 0.5 });
    }
  }

  drop(a) {
    const s = this.on.get(a);
    if (!s) return;
    if (s.ring) { this.engine.scene.remove(s.ring); s.ring.geometry.dispose(); s.ring.material.dispose(); }
    if (s.pulse && a.gear && a.gear.glow) a.gear.glow.value = Math.max(a.gear.plan.glow || 0, a.gear.plan.lantern ? 1 : 0);
    this.on.delete(a);
  }
}
