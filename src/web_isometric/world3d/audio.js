// Sound for /play. One AudioContext (browsers let it start on the first click or key), with
// buses for music, effects, ambience and the interface under a master volume; a cap on how many
// sounds play at once; sounds in the world placed left or right and quieter with distance from
// the camera's focus. Recorded effects are short mp3s (audio/sfx, CC0); swings, spells and room
// tone are made here (the 2D client's synths, ported); music streams from audio/music and
// crossfades between zones and into the battle track. What sounds when: soundtable.js.
import { SOUNDS, FILES, BEDS, VOICES, schoolOf } from './soundtable.js';

const BASE = new URL('./audio/', import.meta.url).href;
const ls = {
  get(k) { try { return localStorage.getItem(k); } catch (_) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (_) {} },
};
export const BUSES = ['master', 'music', 'sfx', 'amb', 'ui'];
const DEFAULT_VOL = { master: 0.8, music: 0.45, sfx: 0.85, amb: 0.6, ui: 0.6 };
// the sounds worth having before the first fight (the rest load on first use)
const PRELOAD = ['hit_punch', 'hit_heavy', 'hit_soft', 'hit_blade', 'parry', 'block', 'step_grass', 'step_stone',
  'step_wood', 'step_dirt', 'ui_click', 'ui_open', 'ui_close', 'ui_hover', 'coins', 'door_open', 'door_close'];

// ---------------------------------------------------------------- synths
// the 2D client's procedural sounds (fx-schools.js, ui.js, immersion.js), written to `out`
let noise = null;
function noiseBuf(ctx) {
  if (!noise || noise.sampleRate !== ctx.sampleRate) {
    noise = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const d = noise.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  }
  return noise;
}
function tone(ctx, out, { f = 440, f2 = null, type = 'sine', dur = 0.2, vol = 0.1, delay = 0, attack = 0.008 }) {
  const t = ctx.currentTime + delay;
  const o = ctx.createOscillator(), g = ctx.createGain();
  o.type = type;
  o.frequency.setValueAtTime(f, t);
  if (f2) o.frequency.exponentialRampToValueAtTime(Math.max(20, f2), t + dur);
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(vol, t + attack);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g); g.connect(out);
  o.start(t); o.stop(t + dur + 0.05);
  return dur + delay;
}
function hiss(ctx, out, { dur = 0.3, vol = 0.1, delay = 0, type = 'bandpass', f = 1200, f2 = null, q = 0.8 }) {
  const t = ctx.currentTime + delay;
  const src = ctx.createBufferSource();
  src.buffer = noiseBuf(ctx);
  const flt = ctx.createBiquadFilter();
  flt.type = type; flt.Q.value = q;
  flt.frequency.setValueAtTime(f, t);
  if (f2) flt.frequency.exponentialRampToValueAtTime(f2, t + dur);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(vol, t + Math.min(0.02, dur * 0.2));
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  src.connect(flt); flt.connect(g); g.connect(out);
  src.start(t, Math.random() * 1.5); src.stop(t + dur + 0.05);
  return dur + delay;
}
// a school's sting (fx-schools.js SOUNDS), louder for bigger casts (tier 0..2)
const STINGS = {
  fire: (c, o, t) => Math.max(hiss(c, o, { dur: 0.35 + t * 0.15, vol: 0.16 + t * 0.05, type: 'lowpass', f: 900 }), tone(c, o, { f: 120, f2: 60, type: 'sawtooth', dur: 0.3 + t * 0.1, vol: 0.1 })),
  frost: (c, o, t) => Math.max(tone(c, o, { f: 1400, f2: 2400, dur: 0.18, vol: 0.1 }), hiss(c, o, { dur: 0.22, vol: 0.1, type: 'highpass', f: 2600 }), t > 0 ? tone(c, o, { f: 700, f2: 200, type: 'triangle', dur: 0.3, vol: 0.1, delay: 0.1 }) : 0),
  lightning: (c, o, t) => Math.max(hiss(c, o, { dur: 0.12, vol: 0.22, type: 'highpass', f: 1800 }), tone(c, o, { f: 80, f2: 50, type: 'square', dur: 0.18 + t * 0.06, vol: 0.12, delay: 0.02 })),
  holy: (c, o, t) => Math.max(...[523, 659, 784].slice(0, 1 + t).map((f, i) => tone(c, o, { f, type: 'triangle', dur: 0.55, vol: 0.09, delay: i * 0.08, attack: 0.03 }))),
  shadow: (c, o) => Math.max(tone(c, o, { f: 300, f2: 90, dur: 0.4, vol: 0.12 }), hiss(c, o, { dur: 0.4, vol: 0.06, type: 'lowpass', f: 500 })),
  blood: (c, o, t) => tone(c, o, { f: 220, f2: 70, type: 'sawtooth', dur: 0.35 + t * 0.1, vol: 0.1 }),
  poison: (c, o) => Math.max(tone(c, o, { f: 400, f2: 320, type: 'triangle', dur: 0.3, vol: 0.08 }), hiss(c, o, { dur: 0.35, vol: 0.07, type: 'lowpass', f: 600 })),
  nature: (c, o) => Math.max(tone(c, o, { f: 520, f2: 660, dur: 0.25, vol: 0.08 }), hiss(c, o, { dur: 0.2, vol: 0.05, f: 2400 })),
  song: (c, o, t) => Math.max(...[440, 554, 659, 880].slice(0, 2 + t).map((f, i) => tone(c, o, { f, dur: 0.24, vol: 0.09, delay: i * 0.07 }))),
  sound: (c, o, t) => STINGS.song(c, o, t),
  arcane: (c, o) => Math.max(tone(c, o, { f: 880, f2: 1320, dur: 0.2, vol: 0.09 }), tone(c, o, { f: 440, f2: 660, type: 'triangle', dur: 0.25, vol: 0.07, delay: 0.04 })),
  physical: (c, o, t) => Math.max(hiss(c, o, { dur: 0.08, vol: 0.14, type: 'highpass', f: 1500 }), tone(c, o, { f: 150, f2: 70, type: 'triangle', dur: 0.12 + t * 0.05, vol: 0.14 })),
  earth: (c, o, t) => Math.max(hiss(c, o, { dur: 0.4 + t * 0.1, vol: 0.16, type: 'lowpass', f: 300 }), tone(c, o, { f: 70, f2: 40, dur: 0.4, vol: 0.16 })),
};
// each returns how long it rings (seconds), so the voice is freed after it
export const SYNTHS = {
  whoosh: (c, o, { tier = 1 }) => hiss(c, o, { dur: [0.12, 0.14, 0.22, 0.32][tier] || 0.14, vol: 0.32, f: tier >= 2 ? 500 : 900, f2: tier >= 2 ? 1600 : 2600, q: 1.2 }),
  whiff: (c, o, { tier = 1 }) => hiss(c, o, { dur: tier >= 2 ? 0.2 : 0.12, vol: 0.18, type: 'highpass', f: 2200, f2: 4200 }),
  bowstring: (c, o) => Math.max(tone(c, o, { f: 220, f2: 110, type: 'triangle', dur: 0.14, vol: 0.18 }), hiss(c, o, { dur: 0.05, vol: 0.12, type: 'highpass', f: 3000 })),
  zap: (c, o) => tone(c, o, { f: 880, f2: 1500, dur: 0.16, vol: 0.12 }),
  ring: (c, o) => Math.max(tone(c, o, { f: 1760, type: 'triangle', dur: 0.45, vol: 0.08 }), tone(c, o, { f: 2637, dur: 0.3, vol: 0.04, delay: 0.02 })),
  thud: (c, o) => tone(c, o, { f: 130, f2: 70, type: 'sawtooth', dur: 0.18, vol: 0.12 }),
  shimmer: (c, o) => Math.max(...[1320, 1760, 2093].map((f, i) => tone(c, o, { f: f * (0.98 + Math.random() * 0.04), dur: 0.5, vol: 0.04, delay: i * 0.06, attack: 0.05 }))),
  heal: (c, o) => Math.max(...[523, 659, 784].map((f, i) => tone(c, o, { f, dur: 0.4, vol: 0.08, delay: i * 0.07, attack: 0.04 }))),
  buff: (c, o) => Math.max(...[392, 523, 659].map((f, i) => tone(c, o, { f, type: 'triangle', dur: 0.3, vol: 0.08, delay: i * 0.06 }))),
  debuff: (c, o) => Math.max(...[440, 349, 277].map((f, i) => tone(c, o, { f, type: 'triangle', dur: 0.3, vol: 0.08, delay: i * 0.07 }))),
  stun: (c, o) => Math.max(...[0, 1, 2].map(i => tone(c, o, { f: 1800 + i * 200, f2: 1500, dur: 0.07, vol: 0.06, delay: i * 0.09 }))),
  fall: (c, o) => Math.max(tone(c, o, { f: 200, f2: 48, type: 'sawtooth', dur: 0.7, vol: 0.09 }), tone(c, o, { f: 110, f2: 40, dur: 0.9, vol: 0.12, delay: 0.1 })),
  death: (c, o) => Math.max(...[200, 150, 110, 80].map((f, i) => tone(c, o, { f, type: 'sawtooth', dur: 0.5, vol: 0.12, delay: i * 0.22 })), tone(c, o, { f: 60, f2: 30, dur: 1.8, vol: 0.2 })),
  windup: (c, o) => Math.max(tone(c, o, { f: 160, f2: 520, type: 'sawtooth', dur: 0.8, vol: 0.07, attack: 0.3 }), hiss(c, o, { dur: 0.8, vol: 0.08, type: 'lowpass', f: 300, f2: 1400 })),
  slam: (c, o) => Math.max(hiss(c, o, { dur: 0.5, vol: 0.4, type: 'lowpass', f: 400, f2: 120 }), tone(c, o, { f: 70, f2: 35, dur: 0.6, vol: 0.35 })),
  fizzle: (c, o) => Math.max(hiss(c, o, { dur: 0.4, vol: 0.12, f: 2400, f2: 400, q: 2 }), tone(c, o, { f: 600, f2: 150, type: 'square', dur: 0.25, vol: 0.03 })),
  charge: (c, o, { school }) => {
    const base = { fire: 140, frost: 900, lightning: 300, holy: 523, shadow: 200, blood: 160, poison: 300, nature: 400, song: 440, sound: 440, arcane: 660, physical: 220, earth: 90 }[school] || 440;
    return Math.max(tone(c, o, { f: base, f2: base * 2, dur: 0.45, vol: 0.06, attack: 0.25 }), hiss(c, o, { dur: 0.45, vol: 0.05, f: base * 2, f2: base * 6, q: 2 }));
  },
  school: (c, o, { school, tier = 1 }) => (STINGS[school] || STINGS.arcane)(c, o, Math.max(0, Math.min(2, tier))),
  splash: (c, o) => Math.max(hiss(c, o, { dur: 0.3, vol: 0.18, f: 900, f2: 500, q: 1.5 }), hiss(c, o, { dur: 0.18, vol: 0.08, type: 'highpass', f: 3000, delay: 0.04 })),
  hop: (c, o) => Math.max(tone(c, o, { f: 300, f2: 620, dur: 0.18, vol: 0.08 }), hiss(c, o, { dur: 0.2, vol: 0.1, f: 900, f2: 2400 })),
  teleport: (c, o) => Math.max(...[523, 784, 1047, 1568].map((f, i) => tone(c, o, { f, dur: 0.5, vol: 0.05, delay: i * 0.05, attack: 0.05 })), hiss(c, o, { dur: 0.6, vol: 0.08, f: 600, f2: 4000, q: 2 })),
  fanfare: (c, o, { tier = 1 }) => Math.max(...(tier >= 2 ? [392, 523, 659, 784, 1047] : [261, 329, 392, 523]).map((f, i) => tone(c, o, { f, type: 'triangle', dur: 0.3, vol: 0.12, delay: i * 0.12, attack: 0.02 }))),
  // the world's murmurs (ambient.js): a crowd's babble, a drip, a gust, heavy steps
  murmur: (c, o) => Math.max(...[0, 0.22, 0.5, 0.8, 1.05].map((d, i) => hiss(c, o, { dur: 0.45 + (i % 2) * 0.2, vol: 0.05, f: 380 + ((i * 137) % 5) * 90, f2: 520 + i * 40, q: 4, delay: d }))),
  drip: (c, o) => Math.max(tone(c, o, { f: 1700, f2: 700, dur: 0.09, vol: 0.09 }), tone(c, o, { f: 1300, f2: 600, dur: 0.07, vol: 0.05, delay: 0.55 })),
  gust: (c, o) => Math.max(hiss(c, o, { dur: 2.2, vol: 0.08, f: 260, f2: 720, q: 0.7 }), hiss(c, o, { dur: 1.6, vol: 0.04, type: 'highpass', f: 1800, f2: 900, delay: 0.4 })),
  steps: (c, o) => Math.max(...[0, 0.5, 1.0, 1.5].map(d => tone(c, o, { f: 92, f2: 52, type: 'triangle', dur: 0.14, vol: 0.13, delay: d }))),
  // the hero's own heart when health runs low: lub-dub
  heartbeat: (c, o) => Math.max(tone(c, o, { f: 62, f2: 44, dur: 0.16, vol: 0.32 }), tone(c, o, { f: 56, f2: 40, dur: 0.14, vol: 0.24, delay: 0.2 })),
  // a creature notices you: a sharp two-note sting
  alert: (c, o) => Math.max(tone(c, o, { f: 660, f2: 700, type: 'triangle', dur: 0.09, vol: 0.09 }), tone(c, o, { f: 990, f2: 1050, type: 'triangle', dur: 0.14, vol: 0.09, delay: 0.08 })),
  // a creature charging in from next door (entities.js onCharge): a low snarl
  growl: (c, o) => Math.max(tone(c, o, { f: 96, f2: 68, type: 'sawtooth', dur: 0.62, vol: 0.1, attack: 0.08 }), tone(c, o, { f: 128, f2: 84, type: 'square', dur: 0.5, vol: 0.035, delay: 0.05 }), hiss(c, o, { dur: 0.6, vol: 0.1, type: 'lowpass', f: 420, f2: 180 })),
  rumble: (c, o) => Math.max(hiss(c, o, { dur: 1.2, vol: 0.07, type: 'lowpass', f: 220, f2: 120 }), tone(c, o, { f: 55, f2: 40, dur: 1.1, vol: 0.06 })),
  chime: (c, o, { tier = 1 }) => Math.max(tone(c, o, { f: tier >= 2 ? 1047 : 880, type: 'triangle', dur: 0.6, vol: 0.09 }), tone(c, o, { f: tier >= 2 ? 1568 : 1320, type: 'triangle', dur: 0.8, vol: 0.07, delay: 0.12 })),
};

// ---------------------------------------------------------------- the engine
class Sound {
  constructor() {
    this.ctx = null;
    this.bus = {};
    this.buffers = new Map();     // "key_n" -> AudioBuffer
    this.loading = new Map();
    this.last = new Map();        // sound -> when it last played (rate limit)
    this.voices = 0;
    this.played = {};             // how often each sound played (for probes and the gallery)
    this.listener = null;         // () => {x, z, yaw}: the camera's focus and turn
    this.vol = {};
    for (const b of BUSES) {
      const v = Number(ls.get(`mh3d_vol_${b}`));
      this.vol[b] = ls.get(`mh3d_vol_${b}`) != null && isFinite(v) ? Math.max(0, Math.min(1, v)) : DEFAULT_VOL[b];
    }
    // the 2D client's one switch ("ambience off") silences /play too until it is set here
    const m = ls.get('mh3d_mute');
    this.muted = m != null ? m === '1' : ls.get('misthollow_ambience') === 'off';
    const q = ls.get('mh3d_quality') || 'high';
    this.maxVoices = VOICES[q === 'med' ? 'medium' : q] || VOICES.high;
    this.bed = { key: null, nodes: [], timer: null };
    this.music = { want: null, zone: null, battle: false, decks: [], cur: -1, timer: null };
    this._unlock = () => this.unlock();
    for (const ev of ['pointerdown', 'keydown', 'touchstart']) window.addEventListener(ev, this._unlock, { capture: true });
    document.addEventListener('visibilitychange', () => {
      if (!this.ctx) return;
      if (document.hidden) this.ctx.suspend().catch(() => {}); else this.ctx.resume().catch(() => {});
    });
  }

  // ---- start (on a user gesture: browsers keep audio off until then) ----
  unlock() {
    const Ref = window.AudioContext || window.webkitAudioContext;
    if (!Ref) return;
    if (!this.ctx) {
      try { this.ctx = new Ref({ latencyHint: 'interactive' }); } catch (_) { return; }
      const c = this.ctx;
      const comp = c.createDynamicsCompressor();
      comp.threshold.value = -10; comp.knee.value = 8; comp.ratio.value = 4;
      comp.connect(c.destination);
      for (const b of BUSES) this.bus[b] = c.createGain();
      this.bus.master.connect(comp);
      for (const b of BUSES) if (b !== 'master') this.bus[b].connect(this.bus.master);
      this.applyVolumes();
      // the common sounds at once, every other effect a moment later (about 0.7 MB in all; the
      // browser fetches and decodes them in parallel): a recorded sound plays once it has loaded
      PRELOAD.forEach(k => { for (let i = 1; i <= FILES[k]; i++) this.load(k, i); });
      setTimeout(() => Object.keys(FILES).forEach(k => { for (let i = 1; i <= FILES[k]; i++) this.load(k, i); }), 1200);
      if (this.bed.want) { const w = this.bed.want; this.bed.want = null; this.ambience(w); }
      if (this.music.want) this.playMusic(this.music.want, 0.5);
    }
    if (this.ctx.state === 'suspended') this.ctx.resume().catch(() => {});
    // a track a phone would not start without a tap starts on the next one (this listener
    // stays: it is only a state check)
    if (this.ctx.state === 'running') for (const d of this.music.decks) if (d.el.paused && d.playing) d.el.play().catch(() => {});
  }
  get ready() { return !!(this.ctx && this.ctx.state === 'running'); }

  // ---- volumes (Settings) ----
  setVolume(bus, v) {
    this.vol[bus] = Math.max(0, Math.min(1, Number(v) || 0));
    ls.set(`mh3d_vol_${bus}`, String(this.vol[bus]));
    this.applyVolumes();
  }
  setMuted(m) {
    this.muted = !!m;
    ls.set('mh3d_mute', this.muted ? '1' : '0');
    this.applyVolumes();
  }
  applyVolumes() {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    for (const b of BUSES) {
      const v = b === 'master' ? (this.muted ? 0 : this.vol.master) : this.vol[b];
      this.bus[b].gain.setTargetAtTime(v, t, 0.03);
    }
  }

  // ---- recorded effects ----
  load(key, i) {
    const id = `${key}_${i}`;
    if (this.buffers.has(id) || this.loading.has(id) || !this.ctx) return this.loading.get(id) || null;
    const p = fetch(`${BASE}sfx/${id}.mp3`).then(r => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(r.status))))
      .then(a => new Promise((res, rej) => this.ctx.decodeAudioData(a, res, rej)))
      .then(buf => { this.buffers.set(id, buf); this.loading.delete(id); return buf; })
      .catch(() => { this.loading.delete(id); return null; });
    this.loading.set(id, p);
    return p;
  }

  // where a sound in the world goes: left/right of the camera, softer far away (null: too far)
  place(at, def) {
    const c = this.ctx;
    const out = c.createGain();
    out.gain.value = def.vol != null ? def.vol : 0.5;
    let node = out;
    if (at && def.pos && this.listener) {
      const L = this.listener();
      if (L) {
        const dx = at.x - L.x, dz = at.z - L.z;
        const d = Math.hypot(dx, dz);
        if (d > 45) return null;
        out.gain.value *= 1 / (1 + (d / 14) ** 2);
        if (c.createStereoPanner && d > 0.5) {
          // the camera looks down -z turned by yaw: screen-right is (cos yaw, -sin yaw)
          const right = dx * Math.cos(L.yaw || 0) - dz * Math.sin(L.yaw || 0);
          const pan = c.createStereoPanner();
          pan.pan.value = Math.max(-0.8, Math.min(0.8, right / 12));
          out.connect(pan);
          node = pan;
        }
      }
    }
    node.connect(this.bus[def.bus || 'sfx']);
    return out;
  }

  // play a sound by name (soundtable.js), optionally at a place in the world
  play(name, opts = {}) {
    const def = SOUNDS[name];
    if (!def || !this.ready || this.muted) return false;
    if (def.layers) {
      let any = false;
      for (const l of def.layers) any = this.play(l, opts) || any;
      if (any) this.played[name] = (this.played[name] || 0) + 1;
      return any;
    }
    const now = this.ctx.currentTime;
    if (now - (this.last.get(name) ?? -9) < (def.gap ?? 0.025)) return false;
    if (this.voices >= this.maxVoices) return false;
    let buf = null;
    if (def.file) {
      const n = FILES[def.file] || 1, i = 1 + Math.floor(Math.random() * n);
      buf = this.buffers.get(`${def.file}_${i}`) || [...Array(n).keys()].map(j => this.buffers.get(`${def.file}_${j + 1}`)).find(Boolean);
      if (!buf) {
        // not loaded yet: fetch it now and play it if that is quick (a late sound is worse than none)
        const asked = performance.now();
        const p = this.load(def.file, i);
        if (p && !opts._late) p.then(b => { if (b && performance.now() - asked < 400) this.play(name, { ...opts, _late: true }); });
        return false;
      }
    }
    const out = this.place(opts.at, { ...def, vol: (def.vol != null ? def.vol : 0.5) * (opts.vol || 1) });
    if (!out) return false;
    this.last.set(name, now);
    this.played[name] = (this.played[name] || 0) + 1;
    this.voices++;
    let secs = 0.5;
    if (buf) {
      const src = this.ctx.createBufferSource();
      src.buffer = buf;
      src.playbackRate.value = 1 + (Math.random() * 2 - 1) * (def.rate || 0);
      src.connect(out);
      src.start();
      secs = buf.duration / src.playbackRate.value;
    } else {
      const fn = SYNTHS[def.synth];
      if (fn) secs = fn(this.ctx, out, { tier: opts.tier ?? def.tier ?? 1, school: opts.school || 'arcane' }) || 0.5;
    }
    setTimeout(() => { this.voices = Math.max(0, this.voices - 1); try { out.disconnect(); } catch (_) {} }, (secs + 0.15) * 1000);
    return true;
  }

  // ---- ambience: a room tone and its calls, by the zone's look (immersion.js beds) ----
  ambience(key) {
    if (!this.ctx) { this.bed.want = key; return; }
    if (this.bed.key === key) return;
    const old = this.bed.nodes;
    const t = this.ctx.currentTime;
    for (const n of old) { if (n.gain) n.gain.setTargetAtTime(0.0001, t, 0.6); }
    setTimeout(() => old.forEach(n => { try { n.stop ? n.stop() : n.disconnect(); } catch (_) {} }), 2500);
    clearTimeout(this.bed.timer);
    this.bed = { key, nodes: [], timer: null };
    const spec = BEDS[key];
    if (!spec) return;
    const c = this.ctx;
    const src = c.createBufferSource();
    src.buffer = noiseBuf(c); src.loop = true;
    const flt = c.createBiquadFilter();
    flt.type = 'bandpass'; flt.frequency.value = spec.wind[0]; flt.Q.value = 0.6;
    const g = c.createGain();
    const level = spec.wind[1] * 6;            // the 2D client mixed these very low
    g.gain.value = 0.0001;
    g.gain.setTargetAtTime(level, t, 0.9);
    const lfo = c.createOscillator(); lfo.frequency.value = 0.07;
    const lfoG = c.createGain(); lfoG.gain.value = level * 0.5;
    lfo.connect(lfoG); lfoG.connect(g.gain);
    src.connect(flt); flt.connect(g); g.connect(this.bus.amb);
    src.start(); lfo.start();
    this.bed.nodes.push(src, lfo, g);
    if (spec.chirp) {
      const loop = () => {
        if (this.bed.key !== key) return;
        const ch = spec.chirp, f = ch.f[0] + Math.random() * (ch.f[1] - ch.f[0]);
        if (!document.hidden && this.voices < this.maxVoices) {
          const out = c.createGain(); out.gain.value = 1; out.connect(this.bus.amb);
          tone(c, out, { f, f2: ch.drip ? f * 0.6 : f * (0.8 + Math.random() * 0.4), dur: ch.dur, vol: ch.vol * 4 });
          setTimeout(() => { try { out.disconnect(); } catch (_) {} }, (ch.dur + 0.3) * 1000);
        }
        this.bed.timer = setTimeout(loop, (ch.every[0] + Math.random() * (ch.every[1] - ch.every[0])) * 1000);
      };
      this.bed.timer = setTimeout(loop, 1500);
    }
  }

  // ---- music: two decks crossfading (a zone change, the battle track, the loop's end) ----
  deck() {
    const el = new Audio();
    el.preload = 'auto';
    el.crossOrigin = 'anonymous';
    const d = { el, key: null, playing: false, src: null, gain: null };
    if (this.ctx) {
      d.src = this.ctx.createMediaElementSource(el);
      d.gain = this.ctx.createGain();
      d.gain.gain.value = 0;
      d.src.connect(d.gain); d.gain.connect(this.bus.music);
    }
    el.addEventListener('timeupdate', () => {
      // near the end: the other deck starts the track again, so the loop never gaps
      if (d.playing && el.duration && el.currentTime > el.duration - 3.5 && this.music.decks[this.music.cur] === d) this.playMusic(d.key, 3, true);
    });
    return d;
  }
  setZoneMusic(key) {
    this.music.zone = key;
    if (!this.music.battle) this.playMusic(key, 3);
  }
  setBattle(on) {
    if (on === this.music.battle) return;
    this.music.battle = on;
    clearTimeout(this.music.timer);
    // a scuffle doesn't swap the music: the battle track comes in after a few seconds of
    // fighting and leaves a while after the last blow
    this.music.timer = setTimeout(() => this.playMusic(on ? 'battle' : this.music.zone, on ? 1.5 : 4), on ? 2500 : 6000);
  }
  playMusic(key, fade = 2, again = false) {
    this.music.want = key;
    if (!this.ctx || !key) return;
    const m = this.music;
    if (m.decks.length < 2) m.decks = [this.deck(), this.deck()];
    const cur = m.decks[m.cur];
    if (!again && cur && cur.key === key && cur.playing) return;
    const next = m.decks[(m.cur + 1) % 2];
    const t = this.ctx.currentTime;
    if (next.key !== key) { next.el.src = `${BASE}music/${key}.mp3`; next.key = key; }
    next.el.currentTime = 0;
    next.playing = true;
    next.gain.gain.cancelScheduledValues(t);
    next.gain.gain.setValueAtTime(0.0001, t);
    next.gain.gain.linearRampToValueAtTime(1, t + fade);
    next.el.play().catch(() => {});
    if (cur && cur.playing) {
      cur.gain.gain.cancelScheduledValues(t);
      cur.gain.gain.setValueAtTime(cur.gain.gain.value, t);
      cur.gain.gain.linearRampToValueAtTime(0.0001, t + fade);
      const old = cur;
      setTimeout(() => { if (m.decks[m.cur] !== old) { old.el.pause(); old.playing = false; } }, fade * 1000 + 100);
    }
    m.cur = (m.cur + 1) % 2;
  }
  stopMusic(fade = 2) {
    this.music.want = null;
    for (const d of this.music.decks) if (d.playing) {
      const t = this.ctx.currentTime;
      d.gain.gain.setTargetAtTime(0.0001, t, fade / 3);
      setTimeout(() => { d.el.pause(); d.playing = false; }, fade * 1000);
    }
  }
}

export const sound = new Sound();
export { schoolOf };
