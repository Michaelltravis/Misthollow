// Making a fight easy to read (owner: "Make it easy for players to fight mobs"):
//   - a ring under your target (red for a foe, gold for anyone else, blue for a player)
//   - your reach drawn around you while you hover an ability on the bar (green when your
//     target is inside it, amber when you would have to close in), and a mark under each
//     creature in the next room it would reach from where you stand (reach.py: pulled in, or
//     leapt at)
//   - STEP OUT: when a foe's marked blow is about to land where you stand, a call over your head
//     and an arrow on the ground toward the safe side
//   - STRIKE NOW: when a foe is staggered, a call, and the bar's heaviest ready attack glows
import * as THREE from 'three';

const ring = (inner, outer, color, opacity) => {
  const m = new THREE.Mesh(new THREE.RingGeometry(inner, outer, 64), new THREE.MeshBasicMaterial({
    color, transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
  m.rotation.x = -Math.PI / 2;
  m.renderOrder = 4;
  return m;
};

export class CombatCues {
  // rangeOf(id) -> metres or null; onStrike() asks the HUD to light the strongest attack;
  // canReach(entity, id, metres) -> whether the ability reaches that creature next door
  // want() -> the quest step's {t: kill|talk|collect, target}; loot() -> the ground items (loot.js)
  constructor({ engine, ents, getHero, rangeOf, canReach, want, loot, callout, onStrike }) {
    this.engine = engine; this.ents = ents; this.getHero = getHero; this.rangeOf = rangeOf; this.canReach = canReach;
    this.want = want; this.loot = loot;
    this.qmarks = []; this.qmarked = []; this._qClock = 0;
    this.callout = callout; this.onStrike = onStrike;
    const scene = engine.scene;
    // the target ring: a bright edge, a soft fill, four ticks that turn
    this.target = new THREE.Group();
    this.tEdge = ring(0.92, 1.0, 0xffffff, 0.85);
    this.tFill = ring(0.0, 0.92, 0xffffff, 0.12);
    this.tTicks = new THREE.Group();
    for (let i = 0; i < 4; i++) {
      const tick = new THREE.Mesh(new THREE.PlaneGeometry(0.1, 0.32), this.tEdge.material);
      tick.rotation.x = -Math.PI / 2;
      tick.position.set(Math.sin(i * Math.PI / 2) * 1.16, 0, Math.cos(i * Math.PI / 2) * 1.16);
      tick.rotation.z = -i * Math.PI / 2;
      this.tTicks.add(tick);
    }
    this.target.add(this.tEdge, this.tFill, this.tTicks);
    this.target.visible = false;
    scene.add(this.target);
    // your reach while you hover an ability
    this.reach = ring(0.985, 1.0, 0x7fe08a, 0.0);
    this.reach.visible = false;
    scene.add(this.reach);
    this.reachWant = null;
    this.reachId = null;
    // the creatures next door within that reach: a small mark under each (a pool, reused)
    this.marks = [];
    this.marked = [];
    this._markClock = 0;
    // the way out of a marked blow
    const shape = new THREE.Shape();
    shape.moveTo(0, 0.9); shape.lineTo(0.5, 0.2); shape.lineTo(0.2, 0.2); shape.lineTo(0.2, -0.7); shape.lineTo(-0.2, -0.7); shape.lineTo(-0.2, 0.2); shape.lineTo(-0.5, 0.2); shape.closePath();
    this.arrow = new THREE.Mesh(new THREE.ShapeGeometry(shape), new THREE.MeshBasicMaterial({ color: 0xffe08a, transparent: true, opacity: 0.9,
      depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
    this.arrow.rotation.order = 'YXZ';
    this.arrow.visible = false;
    this.arrow.renderOrder = 5;
    scene.add(this.arrow);
    this.dangers = new Map();       // telegraph key -> {center, follow, shape, r, angle, facing, until}
    this.calloutUntil = 0;
    this._v = new THREE.Vector3();
  }

  // ---- what combat.js reports ----
  telegraph(key, d) { this.dangers.set(key, d); }
  telegraphEnd(key) { this.dangers.delete(key); }
  opening(src) {
    if (!src || !src.root) return;
    const t = this.ents.targeted;
    if (t && t.root !== src.root) return;           // only the foe you are fighting
    this.say('STRIKE NOW', 'Staggered — hit it with your heaviest blow', 'open', 2200);
    if (this.onStrike) this.onStrike();
  }
  hoverAbility(id) { this.reachWant = id ? this.rangeOf(id) : null; this.reachId = id || null; this._markClock = 0; }

  // what the quest's step wants, picked out in the world: a slow gold ring under each creature to
  // slay or speak with, and under each thing to pick up (quest_guide.py want)
  questWanted(e, w) {
    const target = String(w.target).toLowerCase();
    if (w.t === 'talk') return e.kind === 'mob' && (String(e.data.pv) === target || String(e.data.name || '').toLowerCase().includes(target));
    return e.kind === 'mob' && e.alive !== false && [e.data.name, e.data.short].some(n => String(n || '').toLowerCase().includes(target));
  }
  updateQuest(dt, t) {
    if ((this._qClock -= dt) <= 0) {
      this._qClock = 0.4;
      this.qmarked = [];
      const w = this.want && this.want();
      if (w && w.target) {
        if (w.t === 'collect') {
          const target = String(w.target).toLowerCase();
          for (const l of (this.loot && this.loot().values()) || []) {
            const it = l.item || {};
            if (!l.corpse && (String(it.vnum) === target || [it.name, it.short].some(n => String(n || '').toLowerCase().includes(target)))) this.qmarked.push({ root: l.root, size: 0.8 });
          }
        } else {
          for (const e of this.ents.list.values()) {
            if (e.root && this.questWanted(e, w)) this.qmarked.push({ root: e.root, size: Math.max(0.8, Math.min(2.4, (e.plateY || 2) * 0.42)) });
            if (this.qmarked.length >= 10) break;
          }
        }
      }
    }
    while (this.qmarks.length < this.qmarked.length) {
      const m = ring(0.78, 0.9, 0xffc84a, 0.7);
      this.engine.scene.add(m);
      this.qmarks.push(m);
    }
    this.qmarks.forEach((m, i) => {
      const q = this.qmarked[i];
      m.visible = !!(q && q.root && q.root.parent);
      if (!m.visible) return;
      m.position.set(q.root.position.x, 0.045, q.root.position.z);
      m.scale.setScalar(q.size * (1.1 + Math.sin(t * 2.2 + i) * 0.08));
      m.material.opacity = 0.45 + 0.25 * Math.sin(t * 2.2 + i);
    });
  }

  // the marks under the creatures next door the hovered ability reaches
  updateMarks(dt, t, r) {
    if (r && this.canReach && (this._markClock -= dt) <= 0) {
      this._markClock = 0.2;
      this.marked = [];
      for (const e of this.ents.list.values()) {
        if (e.kind === 'mob' && e.root && e.alive !== false && this.canReach(e, this.reachId, r)) this.marked.push(e);
        if (this.marked.length >= 12) break;
      }
    } else if (!r) this.marked = [];
    while (this.marks.length < this.marked.length) {
      const m = ring(0.5, 0.66, 0x7fe08a, 0.75);
      m.visible = false;
      this.engine.scene.add(m);
      this.marks.push(m);
    }
    this.marks.forEach((m, i) => {
      const e = this.marked[i];
      m.visible = !!(e && e.root);
      if (!m.visible) return;
      const p = e.root.position, size = Math.max(0.7, Math.min(2.2, (e.plateY || 2) * 0.38));
      m.position.set(p.x, 0.05, p.z);
      m.scale.setScalar(size * (1 + Math.sin(t * 4 + i) * 0.06));
    });
  }

  say(title, sub, tone, ms) {
    const el = this.callout;
    if (!el) return;
    el.className = `callout ${tone}`;
    el.querySelector('.co-t').textContent = title;
    el.querySelector('.co-s').textContent = sub || '';
    this.calloutUntil = performance.now() + ms;
    this.calloutTone = tone;
  }

  // ---- every frame ----
  update(dt, t) {
    const h = this.getHero();
    const now = performance.now();
    // the target ring
    const tg = this.ents.targeted;
    if (tg && tg.root && tg.alive !== false) {
      const p = tg.root.position;
      const size = Math.max(0.75, Math.min(2.6, (tg.plateY || 2) * 0.42));
      this.target.visible = true;
      this.target.position.set(p.x, 0.04, p.z);
      this.target.scale.setScalar(size * (1 + Math.sin(t * 3) * 0.03));
      this.tTicks.rotation.y = t * 0.8;
      const col = tg.kind === 'player' ? 0x7fb8ff : tg.plate && tg.plate.classList.contains('hostile') ? 0xff4a2a : 0xf3d27a;
      this.tEdge.material.color.setHex(col); this.tFill.material.color.setHex(col);
    } else this.target.visible = false;
    if (!h || !h.actor) return;
    const hp = h.actor.root.position;
    // your reach while hovering an ability
    const r = this.reachWant;
    if (r) {
      this.reach.visible = true;
      this.reach.position.set(hp.x, 0.05, hp.z);
      this.reach.scale.setScalar(r);
      const inside = tg && tg.root && Math.hypot(tg.root.position.x - hp.x, tg.root.position.z - hp.z) <= r + 0.3;
      this.reach.material.color.setHex(inside ? 0x7fe08a : 0xffb04a);
      this.reach.material.opacity = Math.min(0.85, this.reach.material.opacity + dt * 4);
    } else if (this.reach.visible) {
      this.reach.material.opacity -= dt * 4;
      if (this.reach.material.opacity <= 0) this.reach.visible = false;
    }
    this.updateMarks(dt, t, r);
    this.updateQuest(dt, t);
    // standing where a marked blow will land?
    let danger = null;
    for (const [key, d] of this.dangers) {
      if (now > d.until) { this.dangers.delete(key); continue; }
      const c = d.follow ? d.follow.position : d.center;
      if (!c) continue;
      const dx = hp.x - c.x, dz = hp.z - c.z, dist = Math.hypot(dx, dz);
      let inside = dist < d.r + 0.35;
      if (inside && d.shape === 'cone') {
        const a = Math.atan2(-dz, dx);
        let diff = Math.atan2(Math.sin(a - d.facing), Math.cos(a - d.facing));
        inside = Math.abs(diff) < d.angle / 2 + 0.15;
      }
      if (inside) {
        // the way out: straight away from the centre (for a cone, to the nearer side)
        let ax = dist > 0.05 ? dx / dist : 1, az = dist > 0.05 ? dz / dist : 0;
        if (d.shape === 'cone') { const s = Math.sign(Math.sin(Math.atan2(-dz, dx) - d.facing)) || 1; ax = -Math.sin(d.facing) * s; az = -Math.cos(d.facing) * s; }
        danger = { ax, az, label: d.label, left: d.until - now };
        break;
      }
    }
    // out of a marked blow's ground: say so at once (main.js sends where you stand)
    if (this._inDanger && !danger && this.onLeave) this.onLeave();
    this._inDanger = !!danger;
    if (danger) {
      this.arrow.visible = true;
      this.arrow.position.set(hp.x + danger.ax * 1.5, 0.06, hp.z + danger.az * 1.5);
      // laid flat (its tip, local +Y, then points to -Z) and turned to point the way out
      this.arrow.rotation.set(-Math.PI / 2, Math.atan2(-danger.ax, -danger.az), 0);
      this.arrow.material.opacity = 0.55 + Math.sin(t * 14) * 0.35;
      if (this.calloutTone !== 'danger' || now > this.calloutUntil - 200) this.say('STEP OUT', danger.label ? `${danger.label} is coming down here` : 'A heavy blow is coming down here', 'danger', 450);
      else this.calloutUntil = now + 450;
    } else this.arrow.visible = false;
    // the callout floats over the hero's head
    const el = this.callout;
    if (el) {
      const show = now < this.calloutUntil;
      el.classList.toggle('on', show);
      if (show) {
        const cam = this.engine.camera, cv = this.engine.renderer.domElement;
        this._v.copy(hp).setY(hp.y + 2.9).project(cam);
        el.style.transform = `translate(${((this._v.x + 1) / 2 * cv.clientWidth).toFixed(1)}px, ${((1 - this._v.y) / 2 * cv.clientHeight).toFixed(1)}px) translate(-50%, -100%)`;
      } else this.calloutTone = null;
    }
  }
}
