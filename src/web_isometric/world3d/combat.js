// The fight, on screen. The server sends one structured event for every swing, hit, miss,
// defence, cast, heal, death and wind-up, from the same code that prints the combat log, so
// each line you read has its animation: the attacker winds up and swings (or draws, or
// casts), the blow or bolt travels, the target flinches, blocks or sidesteps, a number
// rises. Ranges and positions come with the events (combat v2: distance matters).
//
// Skills and spells look the way their class does (abilityfx.js recipes, played by
// fxdirector.js); numbers rise when the blow or the bolt that caused them arrives. Timing runs
// on the effects' frame clock (fx.after), so a hit-stop slows the whole sequence alike.
import * as THREE from 'three';
import { recipeFor, timeline, THEMES } from './abilityfx.js';
import { RECIPES } from './abilityfx-table.js';
import { Director } from './fxdirector.js';
import { LANDS } from './soundtable.js';
import { swingClips, rangedBlow } from './gearlook.js';
import { SCHOOL } from './fx.js';
import { SCHOOL_CSS, titleOf, harmColour } from './sctlogic.js';

// a body lying asleep on the ground (entities.js, controller.js: posture.js's Lie_Idle)
const lying = who => !!(who && who.root && who.root.userData && who.root.userData.lying);

// the ordinary swing, by class: for anyone without a look (gearlook.js swingClips picks it
// from what the hand holds)
const SWING = {
  warrior: ['2H_Melee_Attack_Chop', '2H_Melee_Attack_Slice', '2H_Melee_Attack_Stab'],
  paladin: ['1H_Melee_Attack_Chop', '1H_Melee_Attack_Slice_Diagonal', '1H_Melee_Attack_Slice_Horizontal'],
  cleric: ['1H_Melee_Attack_Chop', '1H_Melee_Attack_Slice_Diagonal'],
  thief: ['Dualwield_Melee_Attack_Stab', 'Dualwield_Melee_Attack_Slice', 'Dualwield_Melee_Attack_Chop'],
  assassin: ['Dualwield_Melee_Attack_Stab', 'Dualwield_Melee_Attack_Slice'],
  bard: ['1H_Melee_Attack_Slice_Horizontal', '1H_Melee_Attack_Stab'],
  ranger: ['1H_Ranged_Shoot'],
  mage: ['Spellcast_Shoot'],
  necromancer: ['Spellcast_Shoot'],
};
// a blow trails its weapon's element once that glows (tier 4 and up), a legendary's gold,
// else its class's colour
function slashColour(src, cls) {
  const m = src.look && src.look.main;
  if (m && m.e && (m.t || 0) >= 4 && SCHOOL[m.e]) return SCHOOL[m.e].spark;
  if (m && (m.lg || m.t === 5)) return 0xffd56a;
  const theme = !src.mob && THEMES[cls];
  return theme ? theme.slash : src.hero ? 0xfff0d0 : 0xffb0a0;
}

const COLORS = { dmgOut: '#ffe9a8', dmgIn: '#ff6a52', heal: '#7dff8f', miss: '#b8b8c4', crit: '#ffb02a', parry: '#8cc8ff', block: '#9ad0ff', dodge: '#d8e0ff', spell: '#e0b8ff' };
const keyOf = ref => JSON.stringify(ref || null);
const abilityId = e => String(e.ability || e.spell || '').toLowerCase().replace(/[\s']+/g, '_');

// whether a wound over time is a poison's (its school, or its name: Knife Poison, Serpent Sting...)
export const poisonTick = (e, school) => school === 'poison' || /poison|venom|sting|plague|toxin/i.test(String(e.dot || ''));

export class CombatView {
  constructor({ engine, fx, ents, getHero, heroName, onOutOfRange, onWound, onAggro }) {
    this.engine = engine;
    this.fx = fx;
    this.ents = ents;
    this.getHero = getHero;           // () => { actor, ctl, cls }
    this.heroName = heroName;         // () => name
    this.onOutOfRange = onOutOfRange; // (event) => void
    this.onWound = onWound;           // (entity) => void: its health changed
    this.onAggro = onAggro;           // (mob id, event) => void: a creature went for the hero
    this.telegraphs = new Map();      // mob id -> telegraph
    this.impacts = new Map();         // "src>dst" -> {at, crit, n}: when this action's blow lands
    this.director = new Director({ fx, engine, getHero, chest: w => this.chest(w) });
    this.director.onSound = (name, at, opts) => this.sfx(name, at, opts);
    this.onSound = null;              // (sound name, world position, {school, tier}) => void (audio.js)
    this._v = new THREE.Vector3();
    // the hero's column of scrolling combat text rises from the hero (fx.lane)
    this.fx.laneAnchor = () => { const h = this.getHero(); return h && h.actor && h.actor.root ? h.actor.root.position : null; };
  }
  // the player's setting: numbers over what is struck ('all' or 'foes')
  showsFoes() { const s = this.fx.opts.sct; return s === 'all' || s === 'foes'; }
  harmColour(e, src) { return harmColour(e.school, src && src.look); }
  // a sound where something happens (soundtable.js names)
  sfx(name, at, opts) { if (this.onSound && name) this.onSound(name, at && at.root ? at.root.position : at, opts); }
  pairKey(a, b) { return `${keyOf(a)}>${keyOf(b)}`; }
  // the next wound (or heal) from src to dst should appear when this action's blow lands
  expect(e, delayMs) {
    const k = this.pairKey(e.src, e.dst);
    this.impacts.set(k, { at: performance.now() + delayMs, crit: e.res === 'crit' || e.crit, n: 0, label: e.label || '', school: e.school || null });
    // (a creature pulled in from next door waits for this blow before it charges: entities.js)
    if (e.dst && e.dst.m != null && this.ents.landing) this.ents.landing(`m${e.dst.m}`, performance.now() + delayMs);
  }
  // real-time combat: the hero's blow, shown the moment the key is pressed (the server's attack
  // event then finds it already swinging and doesn't swing twice)
  localSwing() {
    const h = this.getHero();
    if (!h || !h.ctl) return;
    const cls = String(h.cls || '').toLowerCase();
    const look = MH.state.player && MH.state.player.look;
    const list = this.clips({ hero: true, cls, look }, !!rangedBlow(look, cls));
    h.ctl.swing(list[Math.floor(Math.random() * list.length)], true);
    h.ctl.localSwingAt = performance.now();
  }
  // a hero's or another player's swing: from what they hold, else their class's
  clips(who, ranged) {
    if (who.look) return swingClips(who.look, who.cls, ranged);
    return SWING[String(who.cls || '').toLowerCase()] || SWING.paladin;
  }
  // what the hero is about to do: the recipe (main.js plays its start on the key press)
  recipe(id, cls, ev = {}) { return recipeFor(RECIPES, id, cls, ev); }

  // ---- who is who ----
  resolve(ref) {
    if (!ref) return null;
    const h = this.getHero();
    if (ref.p && h && ref.p.toLowerCase() === String(this.heroName()).toLowerCase()) {
      return { actor: h.actor, root: h.actor.root, hero: true, cls: h.cls, look: MH.state.player && MH.state.player.look };
    }
    const e = ref.m != null ? this.ents.list.get(`m${ref.m}`) : ref.p ? this.ents.list.get(`p${ref.p}`) : null;
    if (!e || !e.root) return null;
    return { actor: e.actor, root: e.root, ent: e, mob: ref.m != null, cls: e.data && e.data.char_class, look: e.data && e.data.look };
  }
  chest(who) { return who.root.position.clone().setY(who.root.position.y + (who.ent && who.ent.plateY ? who.ent.plateY * 0.45 : 1.15)); }
  face(who, other) {
    if (!who || !other) return;
    const a = who.root.position, b = other.root.position;
    if (who.hero) { const h = this.getHero(); h.ctl.face(b.x, b.z); }
    else who.root.rotation.y = Math.atan2(b.x - a.x, b.z - a.z);
  }
  play(who, anim, speed = 1) {
    if (!who || !who.actor) return 0.5;
    if (who.hero) {
      // the hero already swung the moment the key was pressed: don't swing twice
      const ctl = this.getHero().ctl;
      if (performance.now() - (ctl.localSwingAt || 0) > 700) ctl.swing(anim, true);
      return 0.45;
    }
    return who.actor.once(anim, 0.08, speed) || 0.5;
  }

  // ---- events ----
  // a round's events arrive together; one creature's second and third blows follow its
  // first a beat apart, so a flurry reads as a flurry instead of one blur
  isHero(ref) { return !!(ref && ref.p && String(ref.p).toLowerCase() === String(this.heroName()).toLowerCase()); }
  // the server measures a wind-up's ground in the room's own metres (0..24, 0..15): place it
  // in the world by the room's offset
  toWorld(x, z) {
    const room = this.roomVnum != null && this.ents.zone ? this.ents.zone.rooms.get(this.roomVnum) : null;
    return new THREE.Vector3((room ? room.ox : 0) + x, 0, (room ? room.oz : 0) + z);
  }
  handle(list, roomVnum = null) {
    list = list || [];
    this.roomVnum = roomVnum;
    const seq = new Map();
    // whatever goes for the hero becomes the target at once (main.js decides when to switch)
    if (this.onAggro) for (const e of list) {
      if (!e.src || e.src.m == null) continue;
      const atHero = this.isHero(e.dst) || (e.hits || []).some(h => this.isHero(h.dst)) || (e.also || []).some(h => this.isHero(h.dst));
      if (atHero && ['attack', 'dmg', 'windup', 'spell', 'ability', 'resolve', 'debuff', 'aggro'].includes(e.k)) this.onAggro(e.src.m, e);
    }
    // a skill's or a spell's wounds and heals follow it in the batch: each rises when the
    // ability reaches its target (an area's too), so they are found and timed first
    const reached = new Map();
    list.forEach((e, i) => {
      if (e.k !== 'ability' && e.k !== 'spell') return;
      const who = keyOf(e.src), hits = [];
      for (let j = i + 1; j < list.length; j++) {
        const f = list[j];
        if (keyOf(f.src) !== who) continue;
        if (f.k === 'dmg' || f.k === 'heal') { if (f.dst && !hits.some(h => keyOf(h) === keyOf(f.dst))) hits.push(f.dst); continue; }
        if (['ability', 'spell', 'attack'].includes(f.k)) break;
      }
      reached.set(e, hits);
    });
    for (const e of list) {
      if (e.k === 'move') { this.move(e); continue; }
      if (e.k === 'dmg') { this.wound(e); continue; }
      if (e.k === 'heal') { this.heal(e); continue; }
      // deaths after the killing number has risen; stars once the stunning blow has landed
      if (e.k === 'death') { this.fx.after(0.65, () => this.event(e)); continue; }
      if (e.k === 'stun') { this.fx.after(0.36, () => this.event(e)); continue; }
      const key = e.src ? keyOf(e.src) : '_';
      const n = seq.get(key) || 0;
      seq.set(key, n + 1);
      const d = (e.delay_ms || 0) + (e.k === 'attack' ? n * 420 : n * 300);
      if (reached.has(e)) {
        const at = d + this.landsIn(e) * 1000;
        for (const dst of new Set([keyOf(e.dst), ...reached.get(e).map(keyOf)])) if (dst !== 'null') this.expect({ src: e.src, dst: JSON.parse(dst), res: e.res, label: titleOf(e.spell || e.ability), school: e.school }, at);
        e._hits = reached.get(e);
      }
      if (d > 0) this.fx.after(d / 1000, () => this.event(e)); else this.event(e);
    }
  }
  // how long an ability or spell takes to reach its target (its recipe's timeline)
  landsIn(e) {
    const src = this.resolve(e.src), dst = this.resolve(e.dst);
    const r = this.recipe(abilityId(e), src && !src.mob ? src.cls : null, e);
    const around = String(e.shape || '') === 'self' || String(e.shape || '').startsWith('nova');
    const dist = src && dst && src.root !== dst.root && (!around || r.travel) ? this.chest(src).distanceTo(this.chest(dst)) : 0;
    let t = timeline(r, dist).land;
    // the hero's own: the key press already started it
    const pre = this.director.pre;
    if (src && src.hero && pre && pre.id === r.id) t = Math.max(0.05, t - (performance.now() - pre.at) / 1000);
    return t;
  }

  // a creature moving in a fight (server position, room metres)
  move(e) {
    const ent = e.src && e.src.m != null ? this.ents.list.get(`m${e.src.m}`) : null;
    if (ent) this.ents.place(ent, { x: e.x, z: e.z });
  }

  // a wound: the number rises when the blow that caused it lands (or now, for wounds
  // nothing announced: poison, fire, traps, a creature's special)
  // a wound over time ticking (a burn, a poison: affects.py): a small number in its school's
  // colour drifting off to the side, a wisp of it, and the target frame shows what is on it
  tick(e) {
    const dst = this.resolve(e.dst);
    if (!dst) return;
    if (dst.ent && dst.ent.data && e.left != null) { dst.ent.data.hp = e.left; if (this.onWound) this.onWound(dst.ent); }
    const school = e.school && e.school !== 'physical' ? e.school : (e.k === 'heal' ? 'nature' : 'poison');
    const color = '#' + this.colorOf(school).toString(16).padStart(6, '0');
    const p = this.chest(dst);
    if (dst.hero) this.fx.lane(e.k === 'heal' ? `+${e.amt}` : `-${e.amt}`, { color: e.k === 'heal' ? COLORS.heal : COLORS.dmgIn, edge: e.k === 'heal' ? '' : color, size: 13, life: 1.5 });
    else if (this.showsFoes()) this.fx.text(p, e.k === 'heal' ? `+${e.amt}` : `${e.amt}`, { color: e.k === 'heal' ? COLORS.heal : color, size: 13, rise: 0.9, life: 0.9, side: 0.6 });
    this.fx.p.emit(p, { count: 6, color: this.colorOf(school), speed: 0.5, up: 0.9, life: 0.6, size: 0.18, drag: 1.4 });
    if (e.k !== 'heal' && poisonTick(e, school)) this.wince(dst, p);
    if (this.onAilment && e.k !== 'heal' && dst.ent) this.onAilment(dst.ent, e.dot, school);
  }

  // a poison biting: the body winces (a flinch, never rooting the hero) and coughs a puff of
  // green gas; at most once a second and a half each, however many poisons tick together
  wince(dst, p) {
    const who = dst.hero ? 'hero' : dst.ent && dst.ent.key;
    const now = performance.now();
    this._winced = this._winced || new Map();
    if (!who || now - (this._winced.get(who) || 0) < 1500) return;
    this._winced.set(who, now);
    if (lying(dst)) { /* a sleeper on the ground stays down */ }
    else if (dst.hero) this.getHero().ctl.swing('Hit_B', true, { speed: 0.9 });
    else if (dst.actor && !(dst.ent && dst.ent.dying)) dst.actor.once('Hit_A', 0.08, 0.85);
    this.fx.p.emit(p, { count: 7, color: 0x6aa83a, bright: 0.8, speed: 0.55, up: 0.45, life: 1.1, size: 0.38, grow: 0.6, drag: 1.6 });
    this.fx.glyph(p, { glyph: 'bubble', count: 4, color: 0x9cff5a, bright: 1.4, speed: 0.5, up: 0.7, life: 0.9, size: 0.14, drag: 1.2 });
  }

  wound(e) {
    if (e.dot) return this.tick(e);
    const k = this.pairKey(e.src, e.dst);
    const imp = this.impacts.get(k);
    const now = performance.now();
    let delay = 0, crit = false, label = '', school = e.school;
    if (imp && now < imp.at + 1800) {
      delay = Math.max(0, imp.at - now) + imp.n * 420;
      crit = imp.crit && imp.n === 0;
      label = imp.n === 0 ? imp.label : '';
      school = school || imp.school;
      imp.n++;
    }
    const show = () => {
      const dst = this.resolve(e.dst);
      if (!dst) return;
      // the server says what is left after this wound, so the bar never counts a blow twice
      // (the round's own update may already have arrived)
      const killing = e.left != null ? e.left <= 0 : false;
      if (dst.ent && dst.ent.data && e.left != null) { dst.ent.data.hp = e.left; if (this.onWound) this.onWound(dst.ent); }
      const p = this.chest(dst);
      const src = this.resolve(e.src);
      const hue = this.harmColour({ school }, src);
      // what hurts the hero rises in its column, red edged with the harm's colour; the hero's (and
      // everyone's) blows rise over what they struck, in the harm's colour, the spell named above
      if (dst.hero) this.fx.lane(crit ? `-${e.amt}!` : `-${e.amt}`, { color: '#ff3d2e', edge: hue !== SCHOOL_CSS.physical ? hue : '', crit, size: 21 });
      else if (this.fx.opts.sct === 'all' || this.fx.opts.sct === 'foes') {
        // a burst of small hits on one creature (an area spell's ticks, a flurry) adds up in one
        // number ("1,204 ×3") instead of a cloud of them
        const key = keyOf(e.dst), last = this.lastNum && this.lastNum.get(key), now = performance.now();
        if (!crit && !label && last && now - last.at < 220 && last.entry.t < 0.5 && !last.crit) {
          last.sum += e.amt; last.n++; last.at = now; last.entry.t = Math.min(last.entry.t, 0.15);
          last.entry.d.textContent = `${last.sum.toLocaleString()} ×${last.n}`;
        } else {
          const entry = this.fx.text(p, crit ? `${e.amt}!` : `${e.amt}`, { color: crit && hue === SCHOOL_CSS.physical ? COLORS.crit : hue, crit, size: 19,
            label: src && !src.mob && label ? label : '' });
          (this.lastNum || (this.lastNum = new Map())).set(key, { entry, sum: e.amt, n: 1, at: now, crit });
        }
      }
      if (!imp || imp.n > 1) { this.fx.flash(dst.root, dst.hero ? 0xff2a1a : 0xffe0c0, 0.12); if (e.school) this.fx.impact(p, e.school); }
      // the view shakes with the size of the blow: a crit, a killing blow, a hit that takes a big
      // bite of the hero's health
      const bite = dst.hero && MH.state && MH.state.player && MH.state.player.max_hp ? e.amt / MH.state.player.max_hp : 0;
      if (crit || killing || bite > 0.04) this.fx.shake(Math.min(0.42, (killing ? 0.26 : crit ? 0.22 : 0.12) + bite * 1.6), killing ? 0.3 : 0.2);
      if (crit) { const src = this.resolve(e.src); if (src && !src.mob) this.director.react('crit', { ...dst, cls: src.cls }); }
      if ((crit || killing || bite > 0.15) && this.engine.hitStop) this.engine.hitStop(killing ? 110 : bite > 0.15 ? 80 : 70);
      // a second or third blow in the same round gets its own swing
      if (imp && imp.n > 1) { const src = this.resolve(e.src); if (src && !src.hero) this.play(src, '1H_Melee_Attack_Slice_Diagonal', 1.3); }
    };
    this.fx.after(delay / 1000, show);
  }

  event(e) {
    switch (e.k) {
      case 'attack': return this.attack(e);
      case 'ability': case 'spell': return this.ability(e);
      case 'heal': return this.heal(e);
      case 'buff': case 'debuff': return this.buff(e);
      case 'windup': return this.windup(e);
      case 'resolve': return this.resolveWindup(e);
      case 'cancel': return this.cancelWindup(e);
      case 'hazard': return this.hazard(e);
      case 'gloom': return this.gloom(e);
      case 'death': return this.death(e);
      case 'stun': return this.stun(e);
      case 'oor': return this.isHero(e.src) && this.onOutOfRange && this.onOutOfRange(e);   // only our own
      case 'fizzle': return this.fizzle(e);
      case 'aggro': return this.aggro(e);
      case 'alert': return this.mark(e, '!', '#ffd23c');
      case 'lost': return this.mark(e, '?', '#b8b0c8');
      case 'proc': return this.proc(e);
      case 'fade': return this.fade(e);
      case 'xp': case 'gold': case 'rep': return this.reward(e);
      case 'fallen': return this.onFallen && this.onFallen(e);
      case 'res':
        if (!this.isHero(e.dst)) return;
        if (!e.spent && e.v > 0) this.fx.lane(`+1 ${e.name === 'arcane' ? 'Arcane Charge' : titleOf(e.name)}`, { color: SCHOOL_CSS.arcane, size: 13 });
        return this.onCharges && this.onCharges(e);
      default: return null;
    }
  }

  // an ordinary blow (auto-attack), melee or ranged, with its result
  attack(e) {
    const src = this.resolve(e.src), dst = this.resolve(e.dst);
    if (!src) return;
    if (dst) this.face(src, dst);
    const cls = String(src.cls || '').toLowerCase();
    // heroes shoot what their weapon shoots (a bow's arrows; a caster's arcane or shadow bolts);
    // creatures as the server says
    const ranged = (src.hero || !src.mob) ? (rangedBlow(src.look, cls) || (e.ranged ? { kind: 'shot', school: 'physical' } : null)) : e.ranged;
    let anim;
    if (src.hero || !src.mob) { const list = this.clips(src, !!ranged); anim = list[Math.floor(Math.random() * list.length)]; }
    else anim = ['1H_Melee_Attack_Chop', '1H_Melee_Attack_Slice_Diagonal', '1H_Melee_Attack_Stab'][Math.floor(Math.random() * 3)];
    this.play(src, anim, 1.15);
    const rkind = ranged && (typeof ranged === 'object' ? ranged.kind : e.style === 'bolt' ? 'bolt' : 'shot');
    this.sfx(!ranged ? 'swing' : rkind === 'shot' ? 'shot' : 'bolt', src);
    if (!dst) return;
    if (ranged) {
      const r = typeof ranged === 'object' ? ranged
        : e.style === 'bolt' ? { kind: 'bolt', school: e.school || 'arcane', size: 0.2 } : { kind: 'shot', school: 'physical' };
      const speed = r.kind === 'shot' ? 26 : 18;
      const flight = 250 + this.chest(src).distanceTo(this.chest(dst)) / speed * 1000;
      this.expect(e, flight);
      this.fx.projectile(this.chest(src), this.chest(dst), { kind: r.kind === 'shot' ? 'arrow' : 'orb', school: r.school, speed, size: r.size || 0.2, delay: 0.25, onHit: () => this.land(e, src, dst, r.school) });
    } else {
      this.expect(e, 300);
      // a hero's or another player's blow trails their weapon's element or their class's colour
      const m = src.look && src.look.main;
      this.fx.slash(src.root.position, dst.root.position, { color: slashColour(src, cls), wide: !!(m && m.h === 2), delay: 0.18 });
      this.fx.after(0.3, () => this.land(e, src, dst, e.school || 'physical'));
    }
  }

  // where a blow arrives: the flinch, the spark (the number comes with its wound event:
  // the amount actually taken); a defence in the defender's class colours
  land(e, src, dst, school) {
    const p = this.chest(dst);
    const heroHit = dst.hero;
    const res = e.res || (e.amt > 0 ? 'hit' : 'miss');
    // what it sounds like: a wound on the hero, a blade or a fist, a ring of steel
    const held = src && src.look && src.look.main && src.look.main.k;
    const blade = src && !src.mob && (held ? ['sword', 'axe', 'dagger', 'polearm', 'scythe', 'spear', 'claw'].includes(held)
      : ['warrior', 'paladin', 'thief', 'assassin', 'bard'].includes(String(src.cls || '').toLowerCase()));
    this.sfx(res === 'hit' ? (heroHit ? 'hurt' : blade ? 'hit_blade' : 'hit') : LANDS[res] || 'miss', dst, { school });
    if (res === 'hit' || res === 'crit') {
      const crit = e.crit || res === 'crit';
      this.fx.impact(p, school, crit || e.heavy);
      this.fx.flash(dst.root, heroHit ? 0xff2a1a : 0xffe0c0, 0.16);
      // (one lying asleep does not jerk up to flinch: the blow wakes it, and it gets up, posture.js)
      if (dst.actor && !dst.hero && !(dst.ent && dst.ent.dying) && !lying(dst)) dst.actor.once(Math.random() < 0.5 ? 'Hit_A' : 'Hit_B', 0.05, crit || e.heavy ? 0.85 : 1.2);
      if (dst.hero && !lying(dst)) this.getHero().ctl.swing(Math.random() < 0.5 ? 'Hit_A' : 'Hit_B', true);
      // a crit or a heavy blow shoves a creature back (it staggers: the flinch played slower), and
      // the view darts in when it is the hero's crit or a crit on the hero
      if ((crit || e.heavy) && dst.ent && !dst.hero && src && src.root) this.ents.knock(dst.ent, src.root.position, crit ? 0.55 : 0.35);
      if (crit && ((src && src.hero) || heroHit) && this.engine.punch) this.engine.punch(heroHit ? 1.8 : 1.2);
    } else {
      const word = { miss: 'Miss', dodge: 'Dodge', parry: 'Parry', block: 'Block', resist: 'Resist', immune: 'Immune' }[res] || res;
      if (heroHit) this.fx.lane(word, { color: COLORS[res] || COLORS.miss, size: 15 });
      else this.fx.text(p, word, { color: COLORS[res] || COLORS.miss, size: 15 });
      if (res === 'parry' || res === 'block') { this.fx.sparks(p, 0xbfe0ff, 10); if (dst.actor && !dst.hero) dst.actor.once('Block_Hit', 0.05, 1.3); }
      if (res === 'dodge' && dst.actor && !dst.hero) dst.actor.once(Math.random() < 0.5 ? 'Dodge_Left' : 'Dodge_Right', 0.05, 1.4);
      if (res === 'dodge' && dst.hero) this.getHero().ctl.swing(Math.random() < 0.5 ? 'Dodge_Left' : 'Dodge_Right', true);
      if (['dodge', 'parry', 'block'].includes(res) && !dst.mob) this.director.react(res, dst);
    }
  }

  // a skill or spell: its recipe (the user's clip and motion, what gathers, flies, lands and
  // lingers), then the target's flinch when it arrives
  ability(e) {
    const src = this.resolve(e.src);
    let dst = this.resolve(e.dst);
    // an aimed area spell lands where it was aimed (the server's room metres), not on a creature
    if (e.at && e.at.length === 2) {
      const spot = new THREE.Object3D();
      spot.position.copy(this.toWorld(e.at[0], e.at[1]));
      dst = { root: spot, point: true };
    }
    const r = this.recipe(abilityId(e), src && !src.mob ? src.cls : null, e);
    // something thrown at nobody in particular goes to the hero's target
    if (!dst && src && src.hero && r.travel && this.ents.targeted && this.ents.targeted.root) {
      const t = this.ents.targeted;
      dst = { actor: t.actor, root: t.root, ent: t, mob: t.kind === 'mob', cls: t.data && t.data.char_class };
    }
    const hits = (e._hits || []).map(h => this.resolve(h)).filter(Boolean);
    const school = r.school || e.school || (THEMES[r.cls] || THEMES.creature).school;
    // a skill or spell lands unless the server says otherwise (parried, resisted...); the
    // number comes with its wound event; an ally's blessing never makes them flinch
    const friendly = r.flags.has('ally') || (dst && !dst.mob && src && !src.mob && !e.res);
    const landAll = () => {
      if (dst && !dst.point && src && dst.root !== src.root && !friendly) this.land({ ...e, res: e.res || 'hit', heavy: r.flags.has('heavy') }, src, dst, school);
      for (const t of e.also || []) { const w = this.resolve(t.dst); if (w) this.land({ ...t, res: t.res || 'hit', heavy: r.flags.has('heavy') }, src, w, school); }
    };
    this.director.play(r, { src, dst, hits, e, onLand: landAll });
  }

  // a spell that came apart in the caster's hands: a puff of grey smoke, a few sparks
  // a creature turns on someone (brain/targeting.py: a taunt, a healer it hates, its foe fallen):
  // it faces them, a red "!" over its head
  aggro(e) {
    const src = this.resolve(e.src), dst = this.resolve(e.dst);
    if (!src) return;
    if (dst) this.face(src, dst);
    const p = this.chest(src).add(new THREE.Vector3(0, 0.9, 0));
    this.fx.text(p, '!', { color: '#ff5a3c', size: 22, rise: 0.5, life: 0.9 });
  }
  // a creature notices someone (brain/pursuit.py: a yellow "!", turned to face them) or loses the
  // trail (a grey "?")
  mark(e, glyph, color) {
    const src = this.resolve(e.src), dst = this.resolve(e.dst);
    if (!src) return;
    if (dst) this.face(src, dst);
    const p = this.chest(src).add(new THREE.Vector3(0, 0.9, 0));
    this.fx.text(p, glyph, { color, size: 24, rise: 0.5, life: 1.2 });
  }
  fizzle(e) {
    const src = this.resolve(e.src);
    if (!src) return;
    if (!src.hero) this.play(src, 'Spellcast_Shoot', 1.1);
    const p = this.chest(src).add(new THREE.Vector3(0, 0.25, 0));
    this.fx.after(0.32, () => {
      this.sfx('fizzle', src);
      this.fx.p.emit(p, { count: 18, color: 0x8a8a96, speed: 1.1, up: 0.9, life: 0.9, size: 0.38, grow: 0.5, drag: 1.6 });
      this.fx.sparks(p, this.colorOf(e.school || 'arcane'), 6);
      this.fx.text(p.clone().setY(p.y + 0.5), 'Fizzled', { color: '#b8b0c8', size: 14, rise: 0.6 });
    });
  }
  // gear acting by itself (procs.py): a burst in its school's colour on whoever it struck, its
  // name above them, and a sting; a reflection or an aura comes off the wearer
  proc(e) {
    const dst = this.resolve(e.dst);
    if (!dst) return;
    const color = this.colorOf(e.school || 'arcane');
    const p = this.chest(dst);
    this.fx.after(0.12, () => {
      this.sfx('sting', dst, { school: e.school || 'arcane' });
      this.fx.impact(p, e.school || 'arcane', true);
      this.fx.p.emit(p, { count: 22, color, speed: 3.2, up: 1.2, life: 0.55, size: 0.3, drag: 1.8, glyph: 'star', spin: 3 });
      this.fx.shockwave(dst.root.position.clone(), { color, radius: 1.8, time: 0.35, thin: true });
      this.fx.light(p, color, 6, 0.3);
      this.fx.text(p.clone().setY(p.y + 0.7), e.name || 'Proc', { color: '#' + color.toString(16).padStart(6, '0'), size: 14, rise: 0.8 });
    });
  }
  // a kill's reward (combat_hooks: 'xp', 'gold', 'rep'): the experience rises in gold over the
  // fallen creature, and the HUD fills the bar, flies the coins to the pack, toasts the standing
  reward(e) {
    // (the reward can arrive before the death it pays for: then the creature still targeted)
    const t = this.ents && this.ents.targeted;
    const kill = this.lastKill && performance.now() - this.lastKill.at < 6000 ? this.lastKill.pos
      : t && t.root && t.kind === 'mob' ? t.root.position.clone() : null;
    // what you earn rises in the middle of the screen (the owner: not down by the bars): a kill's
    // experience over the corpse, any other (a quest, a discovery) and gold in the hero's column
    const bonus = Object.entries(e.bonus || {}).map(([k, v]) => ` · ${k[0].toUpperCase() + k.slice(1)} +${v}`).join('');
    if (e.k === 'xp' && e.src_kind === 'kill' && kill) {
      this.fx.text(kill.clone().setY(kill.y + 1.6), `+${e.amt} XP${bonus}`, { color: '#f3d27a', size: 20, rise: 1.6, life: 1.6 });
    } else if (e.k === 'xp' && e.amt > 0) {
      this.fx.lane(`+${e.amt} XP${bonus}`, { color: '#f3d27a', size: 18, life: 2.2 });
    } else if (e.k === 'gold' && e.amt > 0) {
      this.fx.lane(`+${e.amt} gold`, { color: '#ffd34a', size: 15, life: 2 });
    }
    if (this.onReward) this.onReward(e, kill ? this.screenOf(kill) : null);
  }
  // a point in the world on the page (css px), or null behind the camera
  screenOf(v) {
    const cam = this.engine.camera, cv = this.engine.renderer.domElement;
    const p = v.clone().setY(v.y + 1).project(cam);
    if (p.z > 1) return null;
    const r = cv.getBoundingClientRect();
    return { x: r.left + (p.x + 1) / 2 * r.width, y: r.top + (1 - p.y) / 2 * r.height };
  }
  // an effect on the hero has worn off (affects.py): its name, greyed, sinks away over them
  fade(e) {
    const dst = this.resolve(e.dst);
    if (!dst || !dst.hero) return;
    this.fx.lane(`−${titleOf(e.name)}`, { color: '#a8a4b4', size: 13 });
    if (this.onFade) this.onFade(e.name);
  }
  colorOf(school) { return ({ fire: 0xff7a2a, frost: 0x9fd8ff, lightning: 0xbfd8ff, arcane: 0xc87aff, holy: 0xffe8a0, shadow: 0x8a4ad0, necrotic: 0x7aff8a, nature: 0x9aff6a, poison: 0xb8ff5a, sound: 0xffb8ff, blood: 0xd02a2a })[school] || 0xffffff; }

  // a heal: the number rises when the spell that caused it arrives; a heal nothing announced
  // (a potion, regeneration, a drain) gets a soft glow of its own
  heal(e) {
    if (e.dot) return this.tick(e);
    const k = this.pairKey(e.src, e.dst);
    const imp = this.impacts.get(k);
    const now = performance.now();
    const announced = imp && now < imp.at + 1800;
    const delay = announced ? Math.max(0, imp.at - now) : 0;
    this.fx.after(delay / 1000, () => {
      const dst = this.resolve(e.dst) || this.resolve(e.src);
      if (!dst) return;
      this.sfx('heal', dst);
      if (!announced) {
        this.fx.swirl(dst.root, { school: e.school || 'holy', time: 0.8, count: 2 });
        this.fx.p.emit(this.chest(dst), { count: 10, color: 0x8dffa0, speed: 0.6, up: 1.4, life: 0.8, size: 0.2, drag: 1.2 });
      }
      if (e.amt && dst.hero) this.fx.lane(`+${e.amt}`, { color: COLORS.heal, size: 18 });
      else if (e.amt && this.showsFoes()) this.fx.text(this.chest(dst), `+${e.amt}`, { color: COLORS.heal, size: 18 });
    });
  }
  buff(e) {
    const dst = this.resolve(e.dst);
    if (!dst) return;
    this.sfx(e.k, dst);
    this.fx.swirl(dst.root, { school: e.school || (e.k === 'debuff' ? 'shadow' : 'holy'), time: 0.8, count: 2 });
    if (e.name && dst.hero) this.fx.lane(e.k === 'debuff' ? titleOf(e.name) : `+${titleOf(e.name)}`, { color: e.k === 'debuff' ? '#d8a8ff' : '#fff0b0', size: 14 });
    else if (e.name) this.fx.text(this.chest(dst).setY(dst.root.position.y + 2.4), e.name, { color: e.k === 'debuff' ? '#d8a8ff' : '#fff0b0', size: 13, rise: 0.8 });
  }
  stun(e) {
    const dst = this.resolve(e.dst);
    if (!dst) return;
    this.sfx('stun', dst);
    let t = 0;
    const top = () => dst.root.position.clone().setY(dst.root.position.y + (dst.ent && dst.ent.plateY ? dst.ent.plateY : 2.4) - 0.2);
    this.fx.add({ update: dt => {
      t += dt;
      if (Math.floor(t * 20) % 2 === 0) for (let i = 0; i < 3; i++) {
        const a = t * 6 + i * 2.1;
        this.fx.glyph(top().add(new THREE.Vector3(Math.cos(a) * 0.45, 0, Math.sin(a) * 0.45)), { glyph: 'star', count: 1, color: 0xffe066, speed: 0, life: 0.18, size: 0.3 });
      }
      return t < (e.secs || 1.6);
    } });
    if (dst.hero) this.fx.lane('Stunned!', { color: '#ffe066', size: 15 });
    else this.fx.text(top(), 'Stunned', { color: '#ffe066', size: 13, rise: 0.6 });
  }

  // a creature gathers itself for a big blow: the ground warns you
  windup(e) {
    const src = this.resolve(e.src);
    if (!src) return;
    const a = e.area || {};
    const secs = Math.max(0.4, (e.ms || 1500) / 1000);
    const target = this.resolve(e.dst);
    const center = a.x != null ? this.toWorld(a.x, a.z)
      : a.shape === 'cone' || !a.shape ? src.root.position.clone() : (target ? target.root.position.clone() : src.root.position.clone());
    let facing = 0;
    if (target) { const d = target.root.position.clone().sub(src.root.position); facing = Math.atan2(-d.z, d.x); }
    const t = this.fx.telegraph(center, { shape: a.shape || 'circle', radius: a.r || 2.6, angle: a.angle || Math.PI / 2, facing, time: secs });
    this.sfx('windup', src);
    if (!a.x && (a.shape === 'circle' || !a.shape)) t.follow = src.root;
    const key = e.src && e.src.m != null ? `m${e.src.m}` : 'x';
    if (this.telegraphs.get(key)) this.telegraphs.get(key).cancel();
    this.telegraphs.set(key, t);
    if (src.actor) src.actor.once(src.mob ? 'Block' : 'Spellcast_Long', 0.1, 0.8);
    this.fx.text(this.chest(src).setY(src.root.position.y + 2.6), e.label || 'Winding up!', { color: '#ff8a5a', size: 14, rise: 0.5, life: Math.min(1.6, secs), exact: true });
    // the cues (combatcues.js): step out if you stand where it will land
    if (this.onTelegraph) this.onTelegraph(key, { center: a.x != null ? center : null, follow: t.follow || null, shape: a.shape || 'circle',
      r: a.r || 2.6, angle: a.angle || Math.PI / 2, facing, until: performance.now() + secs * 1000 + 300, label: e.label, src });
  }
  resolveWindup(e) {
    const key = e.src && e.src.m != null ? `m${e.src.m}` : 'x';
    const t = this.telegraphs.get(key);
    if (t) { t.cancel(); this.telegraphs.delete(key); }
    if (this.onTelegraphEnd) this.onTelegraphEnd(key, 'landed');
    const src = this.resolve(e.src);
    const a = e.area || {};
    // the blow lands on the ground it marked (a heavy blow or a spell where you stood)
    const at = a.x != null ? this.toWorld(a.x, a.z) : src ? src.root.position.clone() : null;
    if (src) {
      const tgt = at && a.x != null ? { root: { position: at } } : null;
      if (tgt) this.face(src, tgt);
      if (src.actor) src.actor.once(e.kind === 'cast' ? 'Spellcast_Shoot' : e.kind === 'aoe' ? '2H_Melee_Attack_Spin' : '2H_Melee_Attack_Chop', 0.06, 1.2);
    }
    if (at) {
      const school = e.school || 'physical';
      this.fx.after(e.kind === 'cast' ? 0.45 : 0.25, () => this.sfx('resolve', at, { school }));
      if (e.kind === 'cast' && src) this.fx.projectile(this.chest(src), at.clone().setY(0.4), { school, size: 0.3, speed: 18, delay: 0.2, onHit: p => this.fx.impact(p, school, true) });
      this.fx.after(e.kind === 'cast' ? 0.45 : 0.25, () => { this.fx.shockwave(at, { school, radius: a.r || 3 }); this.fx.shake(0.18, 0.25); });
    }
    for (const h of e.hits || []) { const d = this.resolve(h.dst); if (d) this.land(h, src, d, e.school || 'physical'); }
    if (e.dodged) for (const ref of e.dodged) { const d = this.resolve(ref); if (d) this.fx.text(this.chest(d), 'Evaded!', { color: '#a8ffd0', size: 16 }); }
  }
  // a wind-up broken before it landed (staggered, kicked, snared, killed, the fight over)
  cancelWindup(e) {
    const key = e.src && e.src.m != null ? `m${e.src.m}` : 'x';
    const t = this.telegraphs.get(key);
    if (t) { t.fade(); this.telegraphs.delete(key); }
    if (this.onTelegraphEnd) this.onTelegraphEnd(key, e.reason);
    const src = this.resolve(e.src);
    if (!src || e.reason === 'death' || e.reason === 'end') return;
    // a foe knocked off its stride is open: the cues call for the strike
    if (e.reason === 'stagger' && this.onOpening) this.onOpening(src);
    const p = this.chest(src);
    this.fx.sparks(p, 0xffe066, 16);
    this.sfx('cancel', src);
    const word = { stagger: 'Staggered!', snare: 'Snared!' }[e.reason] || 'Interrupted!';
    this.fx.text(p.clone().setY(src.root.position.y + 2.6), word, { color: '#ffe066', size: 15, rise: 0.6 });
    if (src.actor && !(src.ent && src.ent.dying) && !lying(src)) src.actor.once(Math.random() < 0.5 ? 'Hit_A' : 'Hit_B', 0.05, 1.0);
  }
  // a lasting danger on the ground (a boss's plague pool: boss_mechanics.py): marked for as long as
  // it lasts, with the STEP OUT cue while you stand in it
  hazard(e) {
    const a = e.area || {};
    // where it was laid: its spot, else at the feet of whoever it was laid on
    const on = a.x == null ? this.resolve(e.dst) : null;
    if (a.x == null && !(on && on.root)) return;
    const center = a.x != null ? this.toWorld(a.x, a.z) : on.root.position.clone().setY(0), secs = Math.max(1, (e.ms || 10000) / 1000);
    const color = { poison: 0x5adc3c, necrotic: 0x7a3cdc, fire: 0xff6a1a, frost: 0x6ad0ff }[e.school] || 0xff3a28;
    this.fx.telegraph(center, { shape: 'circle', radius: a.r || 2.4, time: secs, color });
    const key = `h${e.id || Math.random()}`;
    if (this.onTelegraph) this.onTelegraph(key, { center, follow: null, shape: 'circle', r: a.r || 2.4, angle: Math.PI * 2, facing: 0,
      until: performance.now() + secs * 1000, label: e.label || 'Get out!', src: this.resolve(e.src) });
    this.fx.after(secs, () => this.onTelegraphEnd && this.onTelegraphEnd(key, 'gone'));
  }
  // the room darkens as a boss weakens (Death): 0 light .. 1 dark; it lifts when the boss falls
  gloom(e) {
    this.gloomFrom = e.src && e.src.m != null ? e.src.m : null;
    if (this.onGloom) this.onGloom(Math.max(0, Math.min(1, Number(e.level) || 0)));
  }
  death(e) {
    if (this.gloomFrom != null && e.dst && e.dst.m === this.gloomFrom && this.onGloom) { this.gloomFrom = null; this.onGloom(0); }
    const dst = this.resolve(e.dst);
    if (!dst) return;
    // where the last creature fell: its reward rises there and its coins fly from there
    if (dst.mob) this.lastKill = { pos: dst.root.position.clone(), at: performance.now() };
    this.sfx(dst.hero ? 'hero_death' : 'death', dst);
    this.fx.p.emit(this.chest(dst), { count: 30, color: 0xd8d0c0, speed: 2.4, up: 0.8, life: 0.9, size: 0.45, grow: 0.6, drag: 1.4 });
  }
}
