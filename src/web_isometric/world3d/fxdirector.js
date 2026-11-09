// Plays an ability's recipe (abilityfx.js) on the bodies in the scene: the user's clip and
// body motion, what gathers in its hands, what flies, how it lands and what lingers, in the
// colours of its class (THEMES) and school. combat.js calls play() for each ability or spell
// event; main.js calls prelude() on the key press, so the hero moves at once and the server's
// event then only adds what flies and lands. Passive defences (dodges, parries, blocks) get
// their class's touch through react().
import * as THREE from 'three';
import { THEMES, CLIPS, RELEASE, VARIANT_SCHOOL, timeline } from './abilityfx.js';
import { SCHOOL } from './fx.js';
import { SCHOOLS, schoolOf } from './soundtable.js';

const V = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
const hex = c => `#${new THREE.Color(c).getHexString()}`;
const GROWTH_COLOR = { vines: 0x4a8a2a, bones: 0xe8e2cc, ice: 0xbfe8ff, crystals: 0xc8a0ff, bars: 0x9aa0a8, thorns: 0x6a5a2a,
  stones: 0x8a7a6a, spikes: 0x9a9aa8, spears: 0xffe8a0 };

export class Director {
  // chest(who) -> the point a blow or a bolt aims at; getHero() -> {actor, ctl, cls}
  constructor({ fx, engine, getHero, chest }) {
    this.onSound = null;               // (name, world position, {school, tier}) => void (audio.js)
    this.fx = fx;
    this.engine = engine;
    this.getHero = getHero;
    this.chest = chest || (w => w.root.position.clone().setY(w.root.position.y + 1.15));
    this.pre = null;               // the hero's own key press: {id, at, tl}
  }

  // the class's marks (sigils, glyphs, trails) and the school's core (projectiles, impacts)
  palette(r, ev = {}) {
    const theme = THEMES[r.cls] || THEMES.creature;
    const school = r.school || VARIANT_SCHOOL[ev.variant] || ev.school || theme.school;
    const s = SCHOOL[school] || SCHOOL.arcane;
    const creature = r.cls === 'creature';
    return {
      theme, school, spark: s.spark, smoke: s.smoke,
      mark: creature ? s.spark : theme.core, accent: creature ? s.spark : theme.accent, slash: theme.slash,
      glyph: r.glyph || theme.glyph, motif: r.glyph || theme.motif, sigil: theme.sigil,
    };
  }

  // ---- the key press: the hero starts at once ----
  prelude(r, { target = null } = {}) {
    const h = this.getHero();
    if (!h || !h.actor) return;
    const who = { actor: h.actor, root: h.actor.root, hero: true, cls: h.cls };
    const tgt = target && target.root ? { root: target.root, actor: target.actor, ent: target } : null;
    const aimed = tgt && tgt.root !== who.root;
    const tl = timeline(r, aimed ? who.root.position.distanceTo(tgt.root.position) : 0);
    const pal = this.palette(r);
    this.body(r, who, aimed ? tgt : null, tl);
    this.cast(r, who, aimed ? tgt : null, pal, tl);
    this.pre = { id: r.id, at: performance.now() };
  }

  // ---- an ability or spell event: returns when it lands (seconds from now) ----
  // ctx: {src, dst, hits: [who], e, onLand}; `who` is combat.js's resolve(): {actor, root, hero, ent, mob, cls}
  play(r, ctx) {
    const fx = this.fx, ev = ctx.e || {};
    const src = ctx.src, dst = ctx.dst;
    if (!src && !dst) return 0;
    const shape = String(ev.shape || '');
    const around = shape === 'self' || shape.startsWith('nova');
    // where it goes: the target for an aimed ability, the user for self and area ones
    const aimed = !!(dst && src && dst.root !== src.root && (!around || r.travel));
    const from = src ? this.chest(src) : this.chest(dst);
    const to = aimed ? this.chest(dst) : from.clone();
    const tl = timeline(r, aimed ? from.distanceTo(to) : 0);
    const pal = this.palette(r, ev);
    const pre = src && src.hero && this.pre && this.pre.id === r.id && performance.now() - this.pre.at < 1600 ? this.pre : null;
    if (pre) this.pre = null;
    const skip = pre ? (performance.now() - pre.at) / 1000 : 0;
    const near = fx.near(from);
    if (!pre && src) {
      this.body(r, src, aimed ? dst : null, tl);
      if (near) this.cast(r, src, aimed ? dst : null, pal, tl);
    }
    const hits = (ctx.hits || []).filter(h => h && h.root && (!dst || h.root !== dst.root) && (!src || h.root !== src.root));
    // from foe to foe: after the first blink, a hop behind each of the others it reached
    if (r.motion === 'blinks' && src && hits.length) hits.forEach((h, i) => fx.after(0.3 + i * 0.2, () => this.hop(r, src, h)));
    const at = aimed ? dst : src || dst;
    const landAt = Math.max(0.05, tl.land - skip);
    fx.after(Math.max(0, tl.release - skip), () => this.travel(r, src, aimed ? dst : null, hits, pal, from, to, tl, ev));
    fx.after(landAt, () => {
      this.land(r, at, hits, pal, ev, aimed, src);
      this.screen(r, pal);
      if (ctx.onLand) ctx.onLand();
    });
    if (r.aura && near) fx.after(landAt + 0.05, () => this.aura(r, at, pal));
    return landAt;
  }

  // ---- the body: the clip (a second one after it), turning to the target, a motion ----
  body(r, who, target, tl) {
    const clip = CLIPS[r.clip], then = r.then ? CLIPS[r.then] : null;
    const ctl = who.hero ? this.getHero().ctl : null;
    if (target) {
      const a = who.root.position, b = target.root.position;
      if (ctl) ctl.face(b.x, b.z); else who.root.rotation.y = Math.atan2(b.x - a.x, b.z - a.z);
    }
    if (ctl) { ctl.swing(clip, false, { speed: 1.15 * r.speed, force: true }); ctl.localSwingAt = performance.now(); }
    else if (who.actor) who.actor.once(clip, 0.08, r.speed);
    if (then) {
      this.fx.after(((RELEASE[r.clip] || 0.3) + 0.3) / (r.speed || 1), () => {
        if (ctl) ctl.swing(then, false, { speed: 1.15 * r.thenSpeed, force: true });
        else if (who.actor) who.actor.once(then, 0.06, r.thenSpeed);
      });
    }
    if (r.motion) this.motion(r, who, target);
  }

  motion(r, who, target) {
    const fx = this.fx, root = who.root, ctl = who.hero ? this.getHero().ctl : null;
    const p0 = root.position.clone().setY(0);
    const fwd = V(Math.sin(root.rotation.y), 0, Math.cos(root.rotation.y));
    const tp = target ? target.root.position.clone().setY(0) : null;
    const theme = THEMES[r.cls] || THEMES.creature;
    const ghostly = r.cls === 'assassin' || r.cls === 'thief';
    const slide = (to, time, height = 0, face = true) => {
      if (ctl) return ctl.dash(to.x, to.z, time, { height, face });
      const from = root.position.clone().setY(0);
      let t = 0;
      fx.add({ update: dt => {
        t = Math.min(1, t + dt / time);
        const k = height ? t : 1 - Math.pow(1 - t, 3);
        root.position.set(from.x + (to.x - from.x) * k, height * 4 * t * (1 - t), from.z + (to.z - from.z) * k);
        return t < 1;
      }, dispose: () => { root.position.y = 0; } });
    };
    const lift = (height, time, slam = false) => {
      if (ctl) return ctl.lift(height, time, slam);
      let t = 0;
      fx.add({ update: dt => {
        t = Math.min(1, t + dt / time);
        root.position.y = height * (slam ? (t < 0.75 ? Math.sin(t / 0.75 * Math.PI / 2) : 1 - (t - 0.75) / 0.25) : Math.sin(t * Math.PI));
        return t < 1;
      }, dispose: () => { root.position.y = 0; } });
    };
    const spin = (turns, time) => {
      if (ctl) return ctl.spin(turns, time);
      const base = root.rotation.y;
      let t = 0;
      fx.add({ update: dt => { t = Math.min(1, t + dt / time); root.rotation.y = base + (1 - Math.pow(1 - t, 2)) * turns * Math.PI * 2; return t < 1; } });
    };
    // short of the target, on our side of it
    const before = (gap = 1.4) => {
      if (!tp) return p0.clone().addScaledVector(fwd, 3);
      const d = tp.clone().sub(p0);
      const len = d.length();
      return len > gap ? p0.clone().add(d.setLength(len - gap)) : p0.clone();
    };
    switch (r.motion) {
      case 'dash': {
        const end = before();
        slide(end, 0.28);
        for (let i = 0; i < 6; i++) fx.after(i * 0.045, () => fx.p.emit(root.position.clone().setY(0.25), { count: 5, color: 0xd8c8a0, speed: 1.5, life: 0.5, size: 0.4, drag: 2 }));
        if (ghostly) for (let i = 1; i < 4; i++) fx.after(i * 0.07, () => fx.afterimage(root, { color: theme.core, time: 0.35, opacity: 0.4 }));
        break;
      }
      case 'leap': {
        slide(before(1.2), 0.5, 2.2);
        fx.p.emit(p0.clone().setY(0.2), { count: 16, color: 0xd8c8a0, speed: 2, up: 0.5, life: 0.6, size: 0.45, grow: 0.5, drag: 2 });
        fx.every(0.05, 9, () => fx.p.emit(root.position.clone().setY(root.position.y + 1), { count: 3, color: theme.core, speed: 0.4, life: 0.4, size: 0.25, drag: 2 }));
        break;
      }
      case 'blink': case 'blinks': {
        // gone in a puff, there behind the target (or a few steps ahead)
        let to;
        if (tp) {
          const ty = target.root.rotation.y;
          to = tp.clone().add(V(-Math.sin(ty) * 1.2, 0, -Math.cos(ty) * 1.2));
        } else to = p0.clone().addScaledVector(fwd, 3);
        fx.afterimage(root, { color: theme.core, time: 0.45, opacity: 0.6 });
        fx.p.emit(p0.clone().setY(0.9), { count: 22, color: ghostly ? 0x3a3044 : theme.core, speed: 1.6, up: 0.5, life: 0.6, size: 0.55, grow: 0.6, drag: 1.8 });
        fx.after(0.12, () => {
          if (ctl) { ctl.blink(to.x, to.z); if (tp) ctl.face(tp.x, tp.z); }
          else { root.position.set(to.x, 0, to.z); if (tp) root.rotation.y = Math.atan2(tp.x - to.x, tp.z - to.z); }
          fx.p.emit(to.clone().setY(0.9), { count: 16, color: ghostly ? 0x3a3044 : theme.core, speed: 1.4, up: 0.4, life: 0.5, size: 0.5, grow: 0.5, drag: 1.8 });
        });
        break;
      }
      case 'spin': case 'spin2': spin(r.motion === 'spin2' ? 2 : 1, r.motion === 'spin2' ? 0.75 : 0.45); break;
      case 'hover': lift(0.6, 1.3); break;
      case 'rise': lift(1.6, 0.85, true); break;
      case 'hop': lift(0.45, 0.35); break;
      case 'backstep': {
        slide(p0.clone().addScaledVector(fwd, -1.8), 0.24, 0, false);
        if (ghostly) fx.afterimage(root, { color: theme.core, time: 0.4, opacity: 0.45 });
        break;
      }
      case 'sidestep': {
        const side = V(fwd.z, 0, -fwd.x).multiplyScalar(Math.random() < 0.5 ? -1.4 : 1.4);
        slide(p0.clone().add(side), 0.22, 0, false);
        fx.afterimage(root, { color: theme.core, time: 0.4, opacity: ghostly ? 0.5 : 0.3 });
        break;
      }
      case 'lunge': slide(tp ? before(1.1) : p0.clone().addScaledVector(fwd, 0.8), 0.16); break;
      default: break;
    }
  }

  // one more blink: gone in smoke, behind this one, a slash and a glint of coin
  hop(r, who, foe) {
    const fx = this.fx, root = who.root, ctl = who.hero ? this.getHero().ctl : null;
    if (!root || !foe || !foe.root) return;
    const theme = THEMES[r.cls] || THEMES.creature;
    const tp = foe.root.position.clone().setY(0), ty = foe.root.rotation.y;
    const to = tp.clone().add(V(-Math.sin(ty) * 1.1, 0, -Math.cos(ty) * 1.1));
    fx.afterimage(root, { color: theme.core, time: 0.4, opacity: 0.55 });
    fx.p.emit(root.position.clone().setY(0.9), { count: 14, color: 0x3a3044, speed: 1.4, up: 0.4, life: 0.5, size: 0.5, grow: 0.5, drag: 1.8 });
    if (ctl) { ctl.blink(to.x, to.z); ctl.face(tp.x, tp.z); }
    else { root.position.set(to.x, 0, to.z); root.rotation.y = Math.atan2(tp.x - to.x, tp.z - to.z); }
    fx.slash(to, tp, { color: this.palette(r).slash, tilt: Math.random() - 0.5, flip: Math.random() < 0.5 });
    fx.glyph(this.chest(foe), { glyph: 'coin', count: 5, color: 0xffd86a, speed: 2.5, up: 2, gravity: 8, life: 0.7, size: 0.32, spin: 6 });
  }

  // the hands, a little in front of the chest
  hands(who) {
    const c = this.chest(who);
    const y = who.root.rotation.y;
    return c.add(V(Math.sin(y) * 0.45, 0.15, Math.cos(y) * 0.45));
  }

  // ---- while the clip winds up ----
  sfx(name, at, opts) { if (this.onSound) this.onSound(name, at, opts); }

  cast(r, who, target, pal, tl) {
    const t = r.cast;
    if (!t) return;
    const fx = this.fx, root = who.root;
    if (tl.release > 0.2) this.sfx('charge', root.position, { school: pal.school });
    const dur = Math.max(0.25, tl.release);
    switch (t.kind) {
      case 'sigil':
        fx.decal(root.position, { sigil: pal.sigil, radius: t.big ? 2.6 : 1.5, time: dur + (t.big ? 1.3 : 0.6), color: pal.mark, spin: t.big ? 0.7 : 1.3, follow: root });
        break;
      case 'gather': fx.every(0.03, Math.ceil(dur / 0.03), () => {
        const h = this.hands(who);
        for (let i = 0; i < 3; i++) {
          const d = V(Math.random() - 0.5, Math.random() - 0.3, Math.random() - 0.5).normalize().multiplyScalar(1.1);
          fx.p.emit(h.clone().add(d), { count: 1, color: i ? pal.mark : pal.spark, speed: 0, dir: d.clone().multiplyScalar(-1 / 0.3), life: 0.3, size: 0.2, drag: 0 });
        }
      }); break;
      case 'glyphs': case 'motifs': fx.every(0.07, Math.ceil(dur / 0.07) + 2, () => {
        const a = Math.random() * Math.PI * 2, p = root.position;
        fx.glyph(V(p.x + Math.cos(a) * 0.8, 0.2, p.z + Math.sin(a) * 0.8), { glyph: t.kind === 'glyphs' ? pal.glyph : pal.motif, count: 1, color: pal.mark, speed: 0.2, up: 2.2, life: 0.8, size: 0.36, drag: 1 });
      }); break;
      case 'flare': fx.after(Math.max(0, dur - 0.06), () => {
        const h = this.hands(who);
        fx.light(h, pal.spark, 7, 0.3);
        fx.p.emit(h, { count: 18, color: pal.spark, bright: 1.6, speed: 3, life: 0.3, size: 0.3, drag: 3 });
      }); break;
      case 'rings': fx.every(0.13, 3, () => fx.shockwave(root, { color: pal.mark, radius: 2.4, y: 1.1, thin: true, time: 0.45 })); break;
      case 'smoke':
        fx.p.emit(root.position.clone().setY(0.6), { count: 26, color: 0x5a5a64, speed: 1.2, up: 0.6, life: 0.9, size: 0.6, grow: 0.8, drag: 1.6, jitter: 0.6 });
        break;
      case 'embers': fx.every(0.04, Math.ceil(dur / 0.04) + 4, () => {
        const a = Math.random() * Math.PI * 2, p = root.position;
        fx.p.emit(V(p.x + Math.cos(a) * 0.6, 0.3 + Math.random(), p.z + Math.sin(a) * 0.6), { count: 1, color: Math.random() < 0.5 ? 0xff8a2a : pal.mark, bright: 1.4, speed: 0.2, up: 1.8, life: 0.7, size: 0.16, drag: 0.5 });
      }); break;
      case 'aim':
        if (target) {
          fx.ray(this.hands(who), this.chest(target), { color: pal.mark, width: 0.022, time: dur + 0.1 });
          fx.decal(target.root.position, { sigil: 'crosshair', radius: 0.9, time: dur + 0.4, color: pal.mark, spin: 2, follow: target.root });
        }
        break;
      case 'charge':
        fx.tint(root, pal.mark, { time: dur + 0.25, strength: 0.6, hold: 0.85 });
        fx.every(0.04, Math.ceil(dur / 0.04), () => {
          const c = this.chest(who), d = V(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).normalize().multiplyScalar(1.3);
          fx.p.emit(c.clone().add(d), { count: 1, color: pal.mark, speed: 0, dir: d.multiplyScalar(-1 / 0.35), life: 0.35, size: 0.22, drag: 0 });
        });
        break;
      case 'spiral': fx.swirl(root, { glyph: pal.glyph, color: pal.mark, time: dur + 0.35, rise: 2.4, count: 3 }); break;
      case 'orbit': fx.orbit(root, { glyph: pal.glyph, color: pal.mark, count: 3, radius: 0.85, time: dur + 0.35, speed: 6 }); break;
      case 'dust':
        fx.p.emit(root.position.clone().setY(0.15), { count: 18, color: 0xb8a888, speed: 1.6, up: 0.4, life: 0.6, size: 0.45, grow: 0.6, drag: 2 });
        break;
      default: break;
    }
  }

  // ---- what flies: from the hands to the target (or out around the user) ----
  travel(r, src, dst, hits, pal, from, to, tl, ev) {
    const t = r.travel;
    if (!t) return;
    const fx = this.fx;
    this.sfx('travel', from, { tier: t.kind === 'beam' || t.kind === 'pierce' ? 3 : 2 });
    const n = t.arg && /^\d+$/.test(t.arg) ? Number(t.arg) : 1;
    const base = src ? src.root : dst.root;
    let dir = to.clone().sub(from).setY(0);
    if (dir.lengthSq() < 0.01) dir = V(Math.sin(base.rotation.y), 0, Math.cos(base.rotation.y));
    dir.normalize();
    const dist = from.distanceTo(to);
    const speed = Math.max(4, dist / Math.max(0.05, tl.travel));
    // where something aimed at nobody comes down: a few steps ahead
    const ahead = dst ? dst.root.position.clone() : base.position.clone().addScaledVector(dir, 4);
    const radius = r.radius || 3;
    const trail = p => { if (Math.random() < 0.35) fx.glyph(p, { glyph: pal.glyph, count: 1, color: pal.mark, speed: 0.3, life: 0.35, size: 0.22, drag: 2 }); };
    switch (t.kind) {
      case 'slash': {
        const a = base.position, b = dst ? dst.root.position : a.clone().add(dir);
        const color = pal.slash;
        if (t.arg === 'x') { fx.slash(a, b, { color, tilt: 0.5 }); fx.slash(a, b, { color, tilt: 0.5, flip: true, delay: 0.07 }); }
        else if (t.arg === 'up') fx.slash(a, b, { color, tilt: 1, reach: 1.15 });
        else if (t.arg === 'rev') fx.slash(a, b, { color, flip: true, tilt: 0.25 });
        else if (t.arg === 'wide') { fx.slash(a, b, { color, wide: true }); fx.shockwave(a, { color: pal.mark, radius: 3, delay: 0.1 }); }
        else if (t.arg === '3' || t.arg === '2') for (let i = 0; i < Number(t.arg); i++) fx.slash(a, b, { color, tilt: (i - 1) * 0.45, flip: i % 2 === 1, delay: i * 0.08 });
        else fx.slash(a, b, { color });
        break;
      }
      case 'orb':
        fx.projectile(from, to, { school: pal.school, size: t.arg === 'big' ? 0.42 : 0.24, speed, arc: 0.3,
          trail: p => { fx.p.emit(p, { count: 2, color: pal.spark, speed: 0.4, life: 0.35, size: t.arg === 'big' ? 0.5 : 0.32, drag: 3 }); trail(p); } });
        break;
      case 'orbs':
        for (let i = 0; i < n; i++) {
          const side = V(dir.z, 0, -dir.x).multiplyScalar((i - (n - 1) / 2) * 0.5);
          fx.projectile(from.clone().add(side), to, { school: pal.school, size: 0.17, speed: speed * 1.05, arc: 1.2 + (i % 3) * 0.8, delay: i * 0.08,
            onHit: p => fx.impact(p, pal.school) });
        }
        break;
      case 'glyph': case 'motif':
        fx.projectile(from, to, { kind: 'glyph', glyph: t.arg || (t.kind === 'glyph' ? pal.glyph : pal.motif), color: pal.mark, size: 0.3, speed, arc: 0.5, spin: 5, trail: p => { fx.glyph(p, { glyph: t.arg || pal.glyph, count: 1, color: pal.mark, speed: 0, life: 0.06, size: 0.95 }); if (Math.random() < 0.5) fx.p.emit(p, { count: 1, color: pal.spark, speed: 0.3, life: 0.3, size: 0.2 }); } });
        break;
      case 'bolt':
        fx.beam(from, to, { school: pal.school, time: 0.32 });
        fx.beam(from, to, { school: pal.school, time: 0.22, delay: 0.06, jag: 0.5 });
        break;
      case 'sky': {
        const top = to.clone().add(V(0.6, 9, -0.4));
        fx.beam(top, to, { school: pal.school, time: 0.4 });
        fx.beam(top.clone().add(V(-0.8, 0, 0.5)), to, { school: pal.school, time: 0.3, delay: 0.05, jag: 0.6 });
        fx.light(to, pal.spark, 8, 0.3);
        break;
      }
      case 'chain': {
        const pts = [from, to, ...hits.map(h => this.chest(h))];
        fx.chain(pts, { school: pal.school, step: 0.08 });
        break;
      }
      case 'ray': fx.ray(from, to, { color: pal.spark, width: 0.16, time: 0.45 }); break;
      case 'skyray': fx.ray(to.clone().setY(11), to.clone().setY(0), { color: pal.mark, width: 0.38, time: 0.55 }); break;
      case 'tether':
        if (dst && src) fx.tether(dst.root, src.root, { color: pal.spark, glyph: pal.glyph, time: 1.0 });
        break;
      case 'link':
        if (dst && src) fx.tether(src.root, dst.root, { color: pal.mark, time: 0.5, rate: 90, lift: 0.3, size: 0.16 });
        break;
      case 'pierce': {
        // one arrow through everything on its line, and on out of the room
        const far = to.clone().addScaledVector(dir, 9);
        fx.projectile(from, far, { kind: 'arrow', speed, arc: 0,
          trail: p => { fx.p.emit(p, { count: 2, color: pal.mark, bright: 1.7, speed: 0.1, life: 0.45, size: 0.2 }); } });
        fx.ray(from, far, { color: pal.mark, width: 0.07, time: 0.6, delay: tl.travel * 0.4 });
        for (const h of hits) fx.after(tl.travel * 0.8, () => fx.impact(this.chest(h), pal.school, true));
        break;
      }
      case 'arrow':
        fx.projectile(from, to, { kind: 'arrow', speed, arc: 0.3, trail: p => { if (Math.random() < 0.6) fx.p.emit(p, { count: 1, color: pal.mark, speed: 0.1, life: 0.3, size: 0.14 }); trail(p); } });
        break;
      case 'arrows':
        for (let i = 0; i < n; i++) {
          const side = V(dir.z, 0, -dir.x).multiplyScalar((i - (n - 1) / 2) * 0.9);
          fx.projectile(from, to.clone().add(side), { kind: 'arrow', speed, arc: 0.6, delay: i * 0.03 });
        }
        break;
      case 'rain':
        fx.rain(ahead, { count: n, radius, kind: 'arrow', time: 0.5, color: pal.mark, height: 10 });
        break;
      case 'rainglyph':
        fx.rain(ahead, { count: n, radius: r.radius || 4, kind: 'glyph', glyph: pal.glyph, color: pal.mark, size: 0.32, time: 0.6, height: 9 });
        break;
      case 'meteor':
        fx.meteor(ahead.clone().setY(0), { school: pal.school, size: 0.55 });
        break;
      case 'meteors':
        for (let i = 0; i < n; i++) {
          const a = Math.random() * Math.PI * 2, d = i ? Math.sqrt(Math.random()) * Math.max(3, radius) : 0;
          const p = ahead.clone().add(V(Math.cos(a) * d, 0, Math.sin(a) * d)).setY(0);
          fx.meteor(p, { school: pal.school, size: 0.42, delay: i * 0.11, onHit: q => { fx.impact(q.clone().setY(0.5), pal.school, true); fx.shockwave(q, { school: pal.school, radius: 2 }); } });
        }
        break;
      case 'wave':
        fx.wave(base.position, dir, { length: dst ? Math.max(3, dist) : (r.radius || 6), width: 2.8, color: pal.mark, glyph: pal.glyph, time: Math.max(0.25, tl.travel) });
        break;
      case 'cone': {
        const sp = ev && ev.school ? (SCHOOL[ev.school] || SCHOOL.arcane).spark : pal.spark;
        fx.cone(from, dir, { radius: r.radius || 7, color: r.school ? pal.spark : sp, glyph: pal.glyph, time: 0.32 });
        break;
      }
      case 'blade':
        fx.projectile(from, to, { kind: 'blade', color: pal.mark, speed, arc: 0.2, spin: 20 });
        break;
      case 'blades':
        for (let i = 0; i < n; i++) {
          const a = (i / n) * Math.PI * 2;
          const end = from.clone().add(V(Math.cos(a) * 6, -0.4, Math.sin(a) * 6));
          fx.projectile(from, end, { kind: 'blade', color: pal.mark, speed: 22, arc: 0.1, spin: 24, delay: i * 0.015 });
        }
        break;
      case 'shards':
        for (let i = 0; i < n; i++) {
          const side = V(dir.z, 0, -dir.x).multiplyScalar((i - (n - 1) / 2) * 0.35);
          fx.projectile(from.clone().add(side), to, { kind: 'shard', color: pal.spark, speed, arc: 0.15, delay: i * 0.05 });
        }
        break;
      default: break;
    }
  }

  // ---- where it arrives ----
  land(r, who, hits, pal, ev = {}, aimed = true, src = null) {
    const t = r.land;
    const fx = this.fx;
    if (!who || !who.root) return;
    const p = this.chest(who), ground = who.root.position.clone().setY(0);
    const shapeR = Number((String(ev.shape || '').split(':')[1]) || 0);
    const R = r.radius || shapeR || (t && t.big ? 4 : 2.5);
    const heavy = r.flags.has('heavy') || (t && t.big);
    if (t) {
      this.sfx('sting', p, { school: pal.school, tier: t.big ? 2 : heavy ? 1 : 0 });
      const imp = SCHOOLS[schoolOf(pal.school)] && SCHOOLS[schoolOf(pal.school)].impact;
      if (imp) this.sfx(imp === 'shatter' && t.big ? 'shatter_big' : imp, p);
    }
    if (t) switch (t.kind) {
      case 'hit': fx.impact(p, pal.school, heavy); break;
      case 'sparks':
        fx.sparks(p, 0xffe0a0, 20);
        fx.p.emit(p, { count: 8, color: pal.mark, bright: 1.5, speed: 3, up: 1, life: 0.5, size: 0.18, gravity: 5, drag: 2 });
        fx.light(p, pal.spark, 4, 0.18);
        break;
      case 'burst': case 'motifs':
        fx.glyph(p, { glyph: t.arg || (t.kind === 'burst' ? pal.glyph : pal.motif), count: t.big ? 18 : 11, color: pal.mark, speed: 3.6, life: 0.75, size: 0.45, drag: 2.4, spin: 4 });
        fx.impact(p, pal.school, heavy);
        break;
      case 'fountain':
        fx.glyph(ground.clone().setY(0.6), { glyph: t.arg || pal.glyph, count: 16, color: pal.mark, speed: 1.8, up: 6.5, gravity: 12, life: 1.1, size: 0.42, drag: 0.4, spin: 7 });
        fx.light(p, pal.mark, 4, 0.3);
        break;
      case 'nova':
        fx.shockwave(ground, { color: pal.mark, radius: R, time: 0.5 });
        fx.shockwave(ground, { school: pal.school, radius: R * 0.7, delay: 0.08 });
        fx.glyph(ground.clone().setY(0.8), { glyph: pal.glyph, count: t.big ? 22 : 14, color: pal.mark, speed: R * 2.2, life: 0.55, size: 0.4, drag: 2.5, spin: 3 });
        fx.p.emit(ground.clone().setY(0.6), { count: 30, color: pal.spark, speed: R * 1.8, life: 0.45, size: 0.26, drag: 3 });
        break;
      case 'blast':
        fx.impact(p, pal.school, true);
        fx.shockwave(ground, { school: pal.school, radius: R });
        fx.decal(ground, { sigil: 'scorch', radius: R * 0.8, time: 2.4, dark: true, opacity: 0.55, spin: 0 });
        fx.p.emit(ground.clone().setY(0.4), { count: 26, color: pal.smoke, speed: 2.4, up: 3, life: 0.9, size: 0.4, gravity: 7, drag: 1 });
        fx.light(p, pal.spark, 9, 0.35);
        break;
      case 'pillar':
        fx.pillar(ground, { school: pal.school, color: r.school ? null : pal.mark, radius: t.big ? 1.5 : 0.9, time: t.big ? 0.9 : 0.7 });
        break;
      case 'sigil':
        fx.decal(ground, { sigil: pal.sigil, radius: t.big ? Math.max(3, R) : 1.7, time: t.big ? 2.4 : 1.5, color: pal.mark, spin: 0.8 });
        break;
      case 'crack':
        fx.decal(ground, { sigil: 'crack', radius: t.big ? 3.2 : 2.1, time: 2.6, dark: true, opacity: 0.75, spin: 0, grow: 0.5 });
        fx.p.emit(ground.clone().setY(0.2), { count: 22, color: 0xb8a888, speed: 3, up: 1.2, life: 0.7, size: 0.45, grow: 0.5, drag: 2.2 });
        fx.sparks(p, 0xffd8a0, 10);
        fx.shake(0.14, 0.22);
        break;
      case 'quake':
        fx.decal(ground, { sigil: 'crack', radius: Math.max(3, R), time: 2.8, dark: true, opacity: 0.8, spin: 0, grow: 0.6 });
        fx.growth(ground, { kind: 'stones', count: t.big ? 14 : 10, radius: Math.max(1.6, R * 0.55), time: 1.3, height: 1, color: 0x8a7a6a, glow: 0, ring: false });
        fx.shockwave(ground, { color: 0xd8c8a0, radius: Math.max(3, R) + 1, time: 0.55 });
        fx.p.emit(ground.clone().setY(0.3), { count: 34, color: 0xb8a888, speed: 4, up: 1.4, life: 0.8, size: 0.5, grow: 0.5, drag: 2 });
        fx.shake(0.28, 0.4);
        break;
      case 'growth':
        fx.growth(ground, { kind: t.arg, color: t.arg === 'spears' ? pal.mark : GROWTH_COLOR[t.arg] || pal.mark, glow: ['ice', 'crystals', 'spears'].includes(t.arg) ? 0.5 : 0.08,
          count: t.arg === 'bars' ? 10 : t.arg === 'thorns' ? 14 : 8, radius: t.arg === 'bars' ? 1.0 : 1.4, height: t.arg === 'bars' ? 2.2 : 1.3, time: 1.6, ring: t.arg !== 'thorns' });
        break;
      case 'cloud':
        fx.p.emit(p, { count: 40, color: pal.spark, speed: 1.2, up: 0.3, life: 1.6, size: 0.8, grow: 0.6, drag: 1.2, jitter: 1.4 });
        fx.glyph(p, { glyph: pal.glyph, count: 5, color: pal.mark, speed: 1, up: 0.5, life: 1.3, size: 0.4, drag: 1.5 });
        break;
      case 'bubble': fx.bubble(who.root, { color: pal.accent, time: 1.6 }); break;
      case 'mark': {
        const g = t.arg || pal.glyph;
        fx.every(0.05, 46, () => {
          const top = who.root.position.clone().setY(who.root.position.y + (who.ent && who.ent.plateY ? who.ent.plateY + 0.3 : 2.7));
          fx.glyph(top, { glyph: g, count: 1, color: pal.mark, speed: 0, life: 0.09, size: 0.85, rot: 0 });
        });
        fx.decal(ground, { sigil: r.cls === 'assassin' ? 'crosshair' : pal.sigil, radius: 0.9, time: 2.2, color: pal.mark, spin: 1.5, follow: who.root });
        break;
      }
      case 'swirl': fx.swirl(who.root, { glyph: pal.glyph, color: pal.mark, time: 1.0, rise: 2.4, count: 3 }); break;
      case 'geyser': fx.geyser(ground, { color: pal.spark, glyph: pal.glyph, height: 3.6, time: 0.55 }); break;
      case 'shatter':
        fx.glyph(p, { glyph: 'shard', count: t.big ? 22 : 14, color: pal.accent, speed: 5, gravity: 10, life: 0.9, size: 0.38, spin: 10 });
        fx.sparks(p, 0xffffff, 12);
        break;
      case 'freeze':
        fx.tint(who.root, 0x9fd8ff, { time: t.big ? 2.2 : 1.5, strength: 0.75, hold: 0.7 });
        fx.decal(ground, { sigil: 'frost', radius: t.big ? 2.6 : 1.6, time: 2, color: 0x9fd8ff });
        fx.growth(ground, { kind: 'ice', count: t.big ? 10 : 6, radius: 0.85, height: t.big ? 1.6 : 1.1, color: 0xbfe8ff, glow: 0.5, time: 1.6 });
        break;
      case 'halo': fx.halo(who.root, { color: pal.mark, time: 2 }); break;
      case 'wings': fx.wings(who.root, { color: pal.mark, time: 1.8 }); break;
      case 'smoke':
        fx.p.emit(ground.clone().setY(0.7), { count: 30, color: 0x5a5a64, speed: 1.4, up: 0.7, life: 1.0, size: 0.65, grow: 0.9, drag: 1.6, jitter: 0.8 });
        break;
      case 'rings': fx.every(0.12, 3, () => fx.shockwave(who.root, { color: pal.mark, radius: 2.2, y: 1.1, thin: true, time: 0.4 })); break;
      case 'dome': fx.dome(ground, { color: pal.mark, radius: Math.max(2.5, R), time: 2.4 }); break;
      case 'implode': fx.implode(ground, { color: pal.mark, radius: Math.max(4, R), time: t.big ? 1.1 : 0.9 }); break;
      case 'clones': {
        // shadow copies of the striker step out of the dark around it and cut in
        const n = t.big ? 4 : 3, base = Math.random() * Math.PI * 2, tp = who.root.position;
        for (let i = 0; i < n; i++) {
          const a = base + i * Math.PI * 2 / n, at = V(tp.x + Math.sin(a) * 1.35, 0, tp.z + Math.cos(a) * 1.35);
          fx.after(i * 0.07, () => {
            if (src && src.root) fx.afterimage(src.root, { color: pal.mark, time: 0.55, opacity: 0.7, at, yaw: Math.atan2(tp.x - at.x, tp.z - at.z) });
            fx.slash(at, tp, { color: pal.slash, tilt: (i - 1) * 0.5, flip: i % 2 === 1 });
          });
        }
        fx.after(n * 0.07, () => fx.impact(p, pal.school, true));
        break;
      }
      case 'heal':
        fx.p.emit(ground.clone().setY(0.3), { count: t.big ? 30 : 18, color: 0x8dffa0, speed: 0.6, up: 2.4, life: 1.0, size: 0.24, drag: 1.2, jitter: 1 });
        fx.glyph(ground.clone().setY(0.4), { glyph: pal.glyph, count: t.big ? 8 : 5, color: pal.mark, speed: 0.4, up: 2, life: 1.0, size: 0.36, drag: 1 });
        fx.pillar(ground, { color: 0x9dffb0, radius: t.big ? 1.0 : 0.6, height: 4, time: 0.6 });
        break;
      default: break;
    }
    // everyone else it reached gets a touch of it too
    if (hits.length && t && !['hit', 'sparks'].includes(t.kind)) for (const h of hits) fx.impact(this.chest(h), pal.school);
  }

  // ---- what lingers on whoever it was for ----
  aura(r, who, pal) {
    const t = r.aura;
    if (!t || !who || !who.root) return;
    const fx = this.fx, root = who.root;
    this.sfx('aura', root.position, { school: pal.school });
    const T = r.time || (t.big ? 4 : 2.6);
    const around = (radius = 0.7) => { const a = Math.random() * Math.PI * 2, p = root.position; return V(p.x + Math.cos(a) * radius, p.y, p.z + Math.sin(a) * radius); };
    const steady = (every, fn) => fx.every(every, Math.ceil(T / every), fn);
    switch (t.kind) {
      case 'orbit': fx.orbit(root, { glyph: t.arg || pal.glyph, color: pal.mark, count: 3, time: T }); break;
      case 'runes': fx.orbit(root, { glyph: 'rune', color: pal.mark, count: 4, radius: 1.05, time: T, speed: 3 }); break;
      case 'blades': fx.orbit(root, { glyph: 'dagger', color: pal.accent, count: 4, radius: 0.95, time: T, speed: 7, size: 0.44 }); break;
      case 'halo': fx.halo(root, { color: pal.mark, time: T }); break;
      case 'wings': fx.wings(root, { color: pal.mark, time: Math.min(T, 3) }); break;
      case 'bubble': fx.bubble(root, { color: pal.accent, time: T }); break;
      case 'shroud':
        fx.fade(root, { time: T, opacity: 0.6 });
        steady(0.06, () => fx.p.emit(around(0.5).setY(0.3 + Math.random() * 1.4), { count: 1, color: 0x2a1838, speed: 0.3, up: 0.4, life: 0.8, size: 0.6, grow: 0.4, drag: 1.5 }));
        break;
      case 'fade':
        fx.fade(root, { time: T, opacity: 0.25 });
        steady(0.2, () => fx.p.emit(around(0.4).setY(1 + Math.random()), { count: 1, color: pal.mark, speed: 0.1, life: 0.4, size: 0.14 }));
        break;
      case 'glow': fx.tint(root, pal.mark, { time: T, strength: 0.45, hold: 0.8, pulse: 1.2 }); break;
      case 'embers': steady(0.05, () => fx.p.emit(around(0.6).setY(0.3 + Math.random() * 0.8), { count: 1, color: Math.random() < 0.5 ? 0xff8a2a : pal.mark, bright: 1.4, speed: 0.2, up: 1.6, life: 0.8, size: 0.15, drag: 0.5 })); break;
      case 'notes': steady(0.14, () => fx.glyph(around(0.7).setY(1 + Math.random() * 0.8), { glyph: Math.random() < 0.5 ? 'note' : 'notes', count: 1, color: Math.random() < 0.6 ? pal.mark : pal.accent, speed: 0.3, up: 1.2, life: 1.0, size: 0.36, drag: 1 })); break;
      case 'motes': steady(0.06, () => fx.p.emit(around(0.7).setY(0.2 + Math.random()), { count: 1, color: pal.mark, bright: 1.3, speed: 0.1, up: 1.1, life: 1.0, size: 0.16, drag: 0.8 })); break;
      case 'frost':
        fx.tint(root, 0x9fd8ff, { time: T, strength: 0.4, hold: 0.85 });
        steady(0.09, () => fx.glyph(around(0.8).setY(1.8 + Math.random() * 0.6), { glyph: 'snow', count: 1, color: 0xcfeaff, speed: 0.2, up: -0.6, life: 1.1, size: 0.3, drag: 0.6, spin: 2 }));
        break;
      case 'flames': steady(0.04, () => fx.glyph(around(0.55).setY(0.2 + Math.random() * 1.2), { glyph: 'flame', count: 1, color: Math.random() < 0.5 ? 0xff7a2a : 0xffc04a, speed: 0.2, up: 1.6, life: 0.5, size: 0.34, drag: 1 })); break;
      case 'leaves': steady(0.11, () => fx.glyph(around(0.9).setY(2 + Math.random() * 0.5), { glyph: 'leaf', count: 1, color: Math.random() < 0.6 ? pal.mark : pal.accent, speed: 0.4, up: -0.8, life: 1.4, size: 0.32, drag: 0.8, spin: 3 })); break;
      case 'stone':
        fx.tint(root, 0x8a8a90, { time: T, strength: 0.6, hold: 0.85 });
        steady(0.12, () => fx.p.emit(around(0.5).setY(0.4 + Math.random()), { count: 1, color: 0x8a8070, speed: 0.4, life: 0.6, size: 0.18, gravity: 6 }));
        break;
      case 'bark':
        fx.tint(root, 0x6a4a22, { time: T, strength: 0.55, hold: 0.85 });
        steady(0.16, () => fx.glyph(around(0.6).setY(1 + Math.random()), { glyph: 'leaf', count: 1, color: 0x7ab040, speed: 0.3, up: -0.5, life: 1, size: 0.28, spin: 2 }));
        break;
      case 'mirror':
        for (let k = 0; k < 2; k++) fx.after(k * 0.45, () => {
          const y = root.rotation.y, side = V(Math.cos(y), 0, -Math.sin(y));
          fx.afterimage(root, { color: pal.mark, time: 0.9, opacity: 0.45, at: root.position.clone().addScaledVector(side, 0.95) });
          fx.afterimage(root, { color: pal.accent, time: 0.9, opacity: 0.45, at: root.position.clone().addScaledVector(side, -0.95) });
        });
        break;
      case 'ghost':
        fx.tint(root, 0xb8ffc8, { time: T, strength: 0.4, hold: 0.85 });
        steady(0.12, () => fx.glyph(around(0.5).setY(0.5 + Math.random()), { glyph: 'wisp', count: 1, color: pal.mark, speed: 0.2, up: 1.4, life: 0.9, size: 0.34, spin: 3 }));
        break;
      case 'sigil': fx.decal(root.position, { sigil: pal.sigil, radius: 2.2, time: T, color: pal.mark, spin: 0.4, follow: root, opacity: 0.6 }); break;
      case 'rage':
        fx.tint(root, 0xff3a1a, { time: T, strength: 0.6, hold: 0.85, pulse: 2 });
        steady(0.06, () => fx.p.emit(around(0.6).setY(0.3 + Math.random()), { count: 1, color: 0xff5a1a, bright: 1.5, speed: 0.2, up: 1.6, life: 0.6, size: 0.16, drag: 0.5 }));
        break;
      case 'poison': steady(0.09, () => fx.glyph(around(0.35).setY(1 + Math.random() * 0.4), { glyph: 'drop', count: 1, color: 0x9aff4a, speed: 0.1, life: 0.7, size: 0.22, gravity: 6 })); break;
      case 'bleed': steady(0.1, () => fx.glyph(around(0.3).setY(1 + Math.random() * 0.5), { glyph: 'drop', count: 1, color: 0xd02a2a, speed: 0.1, life: 0.7, size: 0.22, gravity: 7 })); break;
      case 'seraph': fx.seraph(root, { color: pal.accent || pal.mark, time: T }); break;
      case 'lich': fx.lich(root, { color: 0x7aff9a, time: T }); break;
      case 'banner': {
        // planted beside the user, a step to the side so it never stands inside them
        const y = root.rotation.y, at = root.position.clone().add(V(Math.cos(y) * 0.9, 0, -Math.sin(y) * 0.9)).setY(0);
        fx.banner(at, { color: new THREE.Color(pal.mark).multiplyScalar(0.8).getHex(), sigil: pal.sigil, glow: pal.mark, time: T });
        break;
      }
      default: break;
    }
  }

  // shakes, hit-stops and the screen washing over, when it lands
  screen(r, pal) {
    const f = r.flags;
    if (f.has('shake+')) this.fx.shake(0.3, 0.35);
    else if (f.has('shake')) this.fx.shake(0.16, 0.22);
    if (f.has('stop') && this.engine && this.engine.hitStop && this.fx.opts.shake) this.engine.hitStop(85);
    if (f.has('flash')) this.fx.screen(hex(pal.mark), { time: 0.5, opacity: 0.28 });
  }

  // ---- passive defences in the class's colours (combat.js land) ----
  react(kind, who) {
    if (!who || !who.root) return;
    const fx = this.fx, cls = String(who.cls || '').toLowerCase(), theme = THEMES[cls];
    if (!theme || !fx.near(who.root.position)) return;
    const p = this.chest(who);
    if (kind === 'dodge') {
      if (cls === 'assassin' || cls === 'thief') fx.afterimage(who.root, { color: theme.core, time: 0.4, opacity: 0.5 });
      if (cls === 'thief') fx.p.emit(p, { count: 12, color: 0x5a5a64, speed: 1.2, up: 0.4, life: 0.7, size: 0.5, grow: 0.6, drag: 1.8 });
      else fx.glyph(p, { glyph: theme.glyph, count: 5, color: theme.core, speed: 1.6, life: 0.5, size: 0.32, drag: 2 });
    } else if (kind === 'parry') {
      fx.sparks(p, cls === 'warrior' ? 0xffb060 : 0xbfe0ff, 14);
      if (cls === 'paladin') fx.glyph(p, { glyph: 'sun', count: 3, color: theme.core, speed: 1.2, life: 0.4, size: 0.4 });
    } else if (kind === 'block') {
      if (cls === 'paladin' || cls === 'warrior' || cls === 'cleric') fx.bubble(who.root, { color: theme.accent, time: 0.45, radius: 1.05 });
      fx.glyph(p, { glyph: theme.motif, count: 4, color: theme.core, speed: 1.4, life: 0.45, size: 0.34 });
    } else if (kind === 'crit') {
      fx.glyph(p, { glyph: theme.glyph, count: 8, color: theme.core, speed: 3, life: 0.6, size: 0.4, drag: 2.5, spin: 4 });
    }
  }
}
