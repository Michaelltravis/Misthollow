// /play — the 3D client. Boots the engine, shows the login over a drifting backdrop, then
// builds the hero's zone as one continuous world and keeps it in step with the server:
// the hero walks freely and the server is told which room they entered (sync.js).
import * as THREE from 'three';
// a zone's light, read from its rooms' words (zone_tone.py)
const TONE_LIGHT = { ghost: 0x9affb0, moon: 0xa8bcff, fire: 0xffb070 };
import { createEngine } from './engine.js';
import { loadKit, GRASS } from './assets.js';
import { WeatherView, weatherKind } from './weather.js';
import { Wildlife } from './wildlife.js';
import { Vistas } from './vista.js';
import { GatherNodes } from './nodes.js';
import { Zone, fetchZonemap, REV } from './zone.js';
import { ROOM_W, ROOM_H, LABEL_FADE } from './terrain.js';
import { Controller, findPath } from './controller.js';
import { Sync } from './sync.js';
import { Entities } from './entities.js';
import { spawnDressed, dress } from './equip.js';
import { cutout } from './cutout.js';
import { FX } from './fx.js';
import { Adorn } from './adorn.js';
import { Wards } from './wards.js';
import { CombatView } from './combat.js';
import { CombatCues } from './combatcues.js';
import { createBubbles } from './hud/bubbles.js';
import { PassageGate, HOP_TIMEOUT_MS } from './passages.js';
import { doorPrompt, doorVerbs, doorAnchor, cap } from './doorlogic.js';
import { createPrompt } from './hud/prompt.js';
import { createCastbar } from './hud/castbar.js';
import { createContextMenu } from './hud/contextmenu.js';
import { attachWorldInput } from './input.js';
import { shouldRetarget, retargetOnDeath, refFor, abilityCommand, tabOrder } from './targeting.js';
import { verbsFor } from './hud/verbs.js';
import { attachPerf } from './perf.js';
import { buildDemo } from './demo.js';
import { sound } from './audio.js';
import { ActionClock } from './actionclock.js';
import { musicFor, bedFor, surfaceFor } from './soundtable.js';
import { interiorKind } from './terrain-town.js';
import { GroundLoot } from './loot.js';
import { nameKey, victimOf } from './corpse.js';
import { mountRider, makeRaft, setSteedFx } from './steed.js';
import { groundItems } from './lootlogic.js';
import { ReactionPrompt, threatens, REACTIONS } from './reactions.js';
import { createWorldMap } from './hud/worldmap.js';
import { createAmbient, cueOf } from './hud/ambient.js';
import { createRoomCard, createEnvLayer } from './hud/roomcard.js';
import { createSkyDial } from './hud/sky.js';
import { createBody } from './hud/body.js';
import { createAlerts, progressText } from './hud/alerts.js';
import { uiIcon } from './hud/icons.js';
import { AimCircle, clampAim, aimCommand } from './aim.js';
import { FAR, farKind } from './far.js';

const $ = s => document.querySelector(s);
const WATER_TILE = 4;   // zone.js / terrain.js tile kinds
// where no sky reaches: no weather, no birds (weather.js, wildlife.js)
const UNDER_SKY = new Set(['inside', 'web', 'necropolis', 'drow', 'foundry', 'sewer', 'underwater', 'ice_cave', 'lava_cave', 'cave', 'mine', 'dungeon', 'crypt']);
const WATER_Y = -0.12;
const params = new URLSearchParams(location.search);
const pref = k => { try { return localStorage.getItem(k); } catch (_) { return null; } };
const engine = createEngine($('#stage'), { quality: params.get('q') || pref('mh3d_quality') || pref('mh3d_quality_auto') || 'high' });
attachPerf(engine, $('#perf'));
// no graphics card in use (Windows' Basic Render Driver, SwiftShader, llvmpipe): the browser draws
// the 3D on the CPU, a few frames a second at best. Low quality for this visit (not saved: a
// machine that gets its graphics back gets its quality back), and a word on why (runGame)
const softGPU = (() => {
  try {
    const gl = engine.renderer.getContext(), d = gl.getExtension('WEBGL_debug_renderer_info');
    const g = String(d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
    return /basic render driver|swiftshader|llvmpipe|software rasterizer/i.test(g) ? g : null;
  } catch (_) { return null; }
})();
if (softGPU && !params.get('q')) engine.setQuality('low');
// a machine that cannot keep up (frames slower than ~30 a second for ten seconds even at the
// screen's own pixel density) steps the graphics down a notch, once in a while, and says so;
// remembered for next time. Never over a quality the player chose (Settings -> Graphics)
const LOWER = { high: 'med', med: 'low' };
const autoQ = { ema: 16.7, last: 0, slow: 0, done: 0 };
engine.onLateTick(() => {
  const now = performance.now(), gap = now - autoQ.last;
  autoQ.last = now;
  if (params.get('q') || pref('mh3d_quality') || softGPU || gap <= 0 || gap > 250) return;
  autoQ.ema += (gap - autoQ.ema) * 0.05;
  const floor = engine.renderer.getPixelRatio() <= 1.01;
  autoQ.slow = floor && autoQ.ema > 34 ? autoQ.slow + gap : 0;
  const next = LOWER[engine.quality.name];
  if (autoQ.slow > 10000 && next && now - autoQ.done > 30000) {
    autoQ.done = now; autoQ.slow = 0;
    engine.setQuality(next);
    try { localStorage.setItem('mh3d_quality_auto', next); } catch (_) {}
    MH.bus.emit('perf.lowered', next);
  }
});
// how long the start takes, by stage (ms from the page's start; the perf overlay and probes
// read MH.bootTimes): the art kits fetched and parsed, the title backdrop built, in the world
const bootTimes = (window.MH = window.MH || {}).bootTimes = {};
const mark = k => { bootTimes[k] = Math.round(performance.now()); };
const loaded = Promise.all(['dungeon', 'nature', 'town', 'furniture', 'graveyard'].map(k => loadKit(k)))
  .then(([dungeon, nature, town, furniture, graveyard]) => { mark('kits'); return { dungeon, nature, town, furniture, graveyard }; });

if (params.has('demo')) runDemo(); else runGame();

async function runDemo() {
  const kits = await loaded;
  if (params.get('gallery')) {
    const { showGallery, showMobGallery } = await import('./gallery.js');
    const g = params.get('gallery');
    const { showBeastGallery, showAbilityGallery, showIconGallery, showSoundGallery, showGearGallery, KIN_SAMPLES } = await import('./gallery.js');
    const extra = ['town', 'furniture', 'graveyard'].includes(g) ? await loadKit(g) : null;
    const at = g === 'mobs' ? await showMobGallery(engine) : g === 'beasts' ? await showBeastGallery(engine, kits)
      : g === 'kin' ? await showBeastGallery(engine, kits, KIN_SAMPLES)
      : g === 'abilities' ? await showAbilityGallery(engine)
      : g === 'mobfx' ? await (await import('./gallery.js')).showMobFxGallery(engine, kits)
      : g === 'gear' ? await showGearGallery(engine)
      : g === 'corpses' ? await (await import('./gallery.js')).showCorpseGallery(engine, kits)
      : g === 'wards' ? await (await import('./gallery.js')).showWardGallery(engine)
      : g === 'bodies' ? await (await import('./gallery.js')).showBodyGallery(engine)
      : g === 'icons' ? (await showIconGallery()) || new THREE.Vector3()
      : g === 'sounds' ? (await showSoundGallery()) || new THREE.Vector3()
      : g === 'rooms' ? (await import('./demo.js')).buildLooksGallery(engine, kits)
      : g === 'chessboard' ? (await import('./demo.js')).buildChessGallery(engine, kits)
      : g === 'steeds' ? await (await import('./demo.js')).buildSteedGallery(engine, kits)
      : showGallery(engine, extra || (g === 'nature' ? kits.nature : kits.dungeon), Number(params.get('scale')) || 1);
    engine.rig.target.copy(at); engine.placeCamera(true);
    // the rooms gallery lights its torches around wherever the camera looks, as the game does
    if ((g === 'rooms' || g === 'chessboard') && window.MH3D_gallery) engine.onTick((dt, t) => window.MH3D_gallery.world.update(dt, t, engine.rig.target));
    window.MH3D = { engine, THREE, gallery: window.MH3D_gallery };
  } else {
    const banner = $('#banner');
    const demo = await buildDemo(engine, kits, {
      interactive: true,
      banner: name => { banner.querySelector('.room').textContent = name; banner.style.opacity = 1; setTimeout(() => { banner.style.opacity = 0; }, 2000); },
    });
    engine.onTick((dt, t) => demo.update(dt, t));
    window.MH3D = { engine, demo, THREE };
  }
  $('#login').classList.add('hidden');
  $('#loading').classList.add('done');
}

async function runGame() {
  const [{ createHud }, { createMinimap, mapOfZone, zoneIndex }, { setupLogin }] = await Promise.all([
    import('./hud/hud.js'), import('./hud/minimap.js'), import('./hud/login.js')]);
  const kits = await loaded;
  const hud = createHud();
  setupLogin();
  let backdrop = await buildDemo(engine, kits, { interactive: false });
  mark('title');
  $('#loading').classList.add('done');
  MH.bus.on('login.success', () => mark('login'));
  if (softGPU) MH.bus.on('login.success', () => setTimeout(() => hud.toast(
    'Your browser is drawing the game without a graphics card, so it will be slow. Turn on hardware acceleration in the browser\'s settings (Chrome: Settings → System), or play in a browser on a computer with graphics.', 12000), 3000));

  // ranges and round timing, one source of truth on the server (combat_range.py)
  let ranges = { melee: 2.5, auto: {}, abilities: {}, spellDefault: 14 };
  // real-time combat (action_combat.py): your swing clock and the global cooldown, as the
  // server last told them (Settings -> Real-time combat; off: the 3-s round)
  const clock = MH.actionClock = new ActionClock();
  const actionMode = () => MH.combatMode === 'action' && !(ranges.action && ranges.action.on === false);
  fetch('/combatdata').then(r => r.json()).then(d => { ranges = d; hud.setRanges(d); clock.configure(d.action); }).catch(() => {});
  const myClass = () => String(MH.state.player && MH.state.player.char_class || '').toLowerCase();
  // the hero's ordinary blow: the weapon in hand decides (a bow shoots), else the class
  const heroAuto = () => {
    const look = MH.state.player && MH.state.player.look, k = look && look.main && look.main.k;
    return (ranges.weapons && ranges.weapons[k]) || ranges.auto[myClass()] || { range: ranges.melee || 2.5, ranged: false };
  };
  const reachOf = () => heroAuto().range;
  const ents = new Entities(engine, $('#plates'), kits);
  // what lies on the ground (loot.js): corpses and items, a click takes them
  const loot = new GroundLoot(engine, { slot: (v, k) => ents.slot(v, k), icon: it => {
    const c = document.createElement('canvas'); c.width = c.height = 64;
    try { if (MH.itemIcons) MH.itemIcons.intoCanvas(c, it); } catch (_) {}
    return c;
  },
  // a corpse keeps the body that fell, or gets one; a hero's (yours, or a player's here) is a grave
  claim: name => ents.claimFallen(name),
  body: (name, key) => ents.body({ name, short: name }, key),
  hero: name => {
    const k = nameKey(name);
    return k === nameKey(MH.state.playerName) || [...ents.list.values()].some(e => e.kind === 'player' && nameKey(e.data.name) === k);
  } });
  engine.onTick((dt, t) => loot.update(dt, t));
  const fx = new FX(engine, $('#fct'));
  setSteedFx(fx);              // (a mount's marks as it goes: hellfire, sparkles, steam...)
  // the sky over the hero (weather.js: the server's weather for the zone, under open sky only) and
  // the small life about them (wildlife.js: birds, fireflies, a leaping fish)
  const sky = new WeatherView(engine, fx, sound);
  // land in the distance, where the hero's room's words put it (vista.js)
  const vistas = new Vistas(engine.scene);
  const wild = new Wildlife(engine, fx, sky.ripples, sound, (x, z) => {
    const r = zone && zone.roomAt(x, z);
    return !!(r && zone.tile(r, x, z) === WATER_TILE);
  });
  // herb patches and ore veins (nodes.js; the server's nodes.py): drawn, glinting, worked on a click
  const spots = new GatherNodes(engine, () => zone, fx);
  engine.onTick(dt => spots.update(dt));
  let spotWalk = null;
  function workSpot(n) {
    if (!n || !hero) return;
    const go = () => { spotWalk = null; if (heroRoom && heroRoom.vnum === n.vnum) MH.sendCommand(n.kind === 'ore' ? 'mine' : 'forage'); };
    const near = () => Math.hypot(hero.root.position.x - n.root.position.x, hero.root.position.z - n.root.position.z) < 1.6;
    if (near()) return go();
    travel = null;
    ctl.walkTo(n.root.position.x, n.root.position.z);
    spotWalk = { near, go, until: performance.now() + 9000 };
  }
  engine.onTick(() => {
    if (!spotWalk || !hero) return;
    if (performance.now() > spotWalk.until || !ctl.path) { if (spotWalk.near()) spotWalk.go(); else spotWalk = null; return; }
    if (spotWalk.near()) { ctl.stop(); spotWalk.go(); }
  });
  // the world's news: an achievement earned, a rare creature sighted in this zone (elites.py)
  MH.bus.on('world.achievement', e => {
    sound.play('quest_done');
    hud.herald({ kicker: 'Achievement unlocked', title: `${e.icon || '★'} ${e.name}`, sub: `${e.desc || ''}${e.title ? ` · new title: ${e.title}` : ''}` });
  });
  MH.bus.on('perf.lowered', q => hud.toast(`Graphics lowered to ${q === 'low' ? 'Low' : 'Medium'} to keep the game smooth (Settings -> Graphics)`, 5000));
  // a ping (alt-click on the ground): a ring and a beam where it was put, for you and your group
  // (commands.py webping; the minimap flashes gold there too)
  function pingAt(x, z) {
    const r = zone && zone.roomAt(x, z);
    if (r) MH.sendCommand(`webping ${r.vnum} ${(x - r.ox).toFixed(1)} ${(z - r.oz).toFixed(1)}`, false);
  }
  const beamGeo = new THREE.CylinderGeometry(0.12, 0.3, 1, 10, 1, true).translate(0, 0.5, 0);
  MH.bus.on('world.ping', e => {
    const r = zone && zone.rooms.get(e.vnum);
    mmSmall.ping(e.vnum, 'ping'); mmBig.ping(e.vnum, 'ping');
    sound.play('quest_stage');
    if (e.from && e.from !== MH.state.playerName) hud.toast(`${e.from} marks a spot`);
    if (!r) return;
    const x = r.ox + e.x, z = r.oz + e.z;
    for (let i = 0; i < 3; i++) fx.after(i * 0.35, () => sky.ripples.spawn(x, 0, z, { size: 2.4, life: 1.4, color: 0xffd24a, opacity: 0.85 }));
    const beam = new THREE.Mesh(beamGeo, new THREE.MeshBasicMaterial({ color: 0xffd24a, transparent: true, opacity: 0.55,
      blending: THREE.AdditiveBlending, depthWrite: false }));
    beam.position.set(x, 0, z); beam.scale.set(1, 7, 1);
    engine.scene.add(beam);
    const t0 = performance.now();
    const fade = () => {
      const k = (performance.now() - t0) / 3500;
      if (k >= 1) { engine.scene.remove(beam); beam.material.dispose(); return; }
      beam.material.opacity = 0.55 * (1 - k);
      requestAnimationFrame(fade);
    };
    fade();
  });
  MH.bus.on('world.rare', e => {
    sound.play('ui_offer');
    hud.herald({ kicker: 'A rare creature stirs', title: e.name, sub: `seen near ${e.where}`, tone: 'rare' });
  });
  let skyOpen = false, skyTheme = 'field';
  function applySky() {
    const w = lastPayload && lastPayload.weather;
    sky.set(weatherKind(w, skyTheme), w && w.wind, skyOpen);
    GRASS.wind.value = 0.3 + Math.min(1.2, ((w && w.wind) || 0) / 20);
  }
  engine.onTick((dt, t) => {
    if (!hero || !hero.root) return;
    const p = hero.root.position;
    GRASS.hero.value.set(p.x, p.y, p.z);
    GRASS.time.value = t;
    sky.update(dt, t, p, 0);
    wild.update(dt, t, p, !!MH.state.inCombat);
  });
  const wards = new Wards(engine, fx);      // the spells on everyone, shown while they last
  const adorn = new Adorn(engine, fx);       // what lingers round the well-geared and the renowned
  const combat = new CombatView({
    engine, fx, ents,
    getHero: () => hero && { actor: hero, ctl, cls: (MH.state.player && MH.state.player.char_class || '').toLowerCase() },
    heroName: () => MH.state.playerName,
    onOutOfRange: e => outOfRange(e),
    onWound: ent => { if (ents.targeted === ent) hud.setTarget({ kind: ent.kind, ...ent.data }); },
    onAggro: id => aggro(id),
  });
  // a boss's gloom (Death): the scene's light dims; it lifts when the boss falls or you leave
  let gloomRoom = null;
  combat.onGloom = level => { engine.gloom = level; gloomRoom = level > 0 && heroRoom ? heroRoom.vnum : null; };
  // fights made easy to read: a ring under your target, your reach while you hover an
  // ability, STEP OUT under a marked blow, STRIKE NOW at a staggered foe
  const cues = new CombatCues({ engine, ents, getHero: () => hero && { actor: hero, ctl }, callout: $('#callout'),
    rangeOf: id => { const r = rangeOf(id, (hud.player && (hud.player.spells || {})[id] != null)); return r || null; },
    // next door, from where the hero stands: pulled in by a shot or a spell, or leapt at
    // what the quest's step wants (quest_guide.py want): a gold ring under it
    want: () => (MH.state.player && MH.state.player.quest && MH.state.player.quest.want) || null,
    loot: () => loot.list,
    canReach: (e, id, r) => {
      if (!id || !heroRoom || !hero || !hero.root || e.vnum === heroRoom.vnum) return false;
      const spell = !!(hud.player && (hud.player.spells || {})[id] != null);
      return reachAcross(e, r, pullsOf(id, spell)) || (leapsOf(id) && reachAcross(e, r, false, true));
    },
    onStrike: () => hud.suggestStrike() });
  // sound (audio.js): heard from where the camera looks, turned with it
  combat.onSound = (name, at, opts) => sound.play(name, { at, ...(opts || {}) });
  sound.listener = () => ({ x: engine.rig.target.x, z: engine.rig.target.z, yaw: engine.rig.yaw });
  MH.bus.on('combat.state', on => sound.setBattle(!!on));
  combat.onTelegraph = (k, d) => cues.telegraph(k, d);
  // what used to be text only: charges gained and spent, a wound ticking on a foe, an effect gone
  combat.onCharges = e => hud.setCharges(e);
  combat.onAilment = (ent, name, school) => hud.noteAilment(ent, name, school);
  combat.onFade = () => { if (MH.refreshState) setTimeout(() => MH.refreshState(), 200); };
  combat.onReward = (e, from) => hud.reward(e, from);
  combat.onFallen = e => hud.fallen(e);
  // the player's combat-number settings (hud settings)
  MH.bus.on('settings.sct', o => { fx.opts = o; });
  // Settings -> Brightness: the whole picture lighter (engine exposure)
  MH.bus.on('settings.brightness', v => { engine.brightness = v; });
  try { engine.brightness = +(localStorage.getItem('mh3d_bright') || 1) || 1; } catch (_) {}
  try { fx.opts = { sct: localStorage.getItem('mh3d_sct') || 'all', size: +(localStorage.getItem('mh3d_sctsize') || 1) || 1, shake: localStorage.getItem('mh3d_shake') !== 'off', life: +(localStorage.getItem('mh3d_sctlife') || 1) || 1 }; } catch (_) {}
  // ---- the way to the quest (quest_guide.py `where`): a gold chevron on the ground by the hero,
  // pointing at the exit the way goes out of this room (or its stairs); gone once you are there ----
  const guide = (() => {
    const g = new THREE.Group();
    const shape = new THREE.Shape();
    shape.moveTo(0, 0.42); shape.lineTo(0.34, -0.18); shape.lineTo(0, -0.02); shape.lineTo(-0.34, -0.18); shape.closePath();
    const mat = new THREE.MeshBasicMaterial({ color: 0xfff0a0, transparent: true, opacity: 0.9, depthWrite: false, depthTest: false, side: THREE.DoubleSide });
    const edge = new THREE.MeshBasicMaterial({ color: 0x1a1006, transparent: true, opacity: 0.7, depthWrite: false, depthTest: false, side: THREE.DoubleSide });
    const geo = new THREE.ShapeGeometry(shape);
    for (let i = 0; i < 3; i++) {
      // a dark rim under each chevron, so it reads on gold rugs and pale stone alike
      const rim = new THREE.Mesh(geo, edge);
      rim.rotation.x = -Math.PI / 2; rim.position.set(0, -0.005, i * 0.5); rim.scale.setScalar(1.75); rim.renderOrder = 9;
      const m = new THREE.Mesh(geo, mat);
      m.rotation.x = -Math.PI / 2; m.position.z = i * 0.5; m.scale.setScalar(1.45); m.renderOrder = 10;      // (the tip leads, toward local -z)
      g.add(rim, m);
    }
    g.visible = false;
    engine.scene.add(g);
    return { g, mat };
  })();
  engine.onTick((dt, t) => {
    const w = MH.state.player && MH.state.player.quest && MH.state.player.quest.where;
    const on = !!(w && w.dir && hero && hero.root && heroRoom && zone && w.vnum !== heroRoom.vnum);
    guide.g.visible = on;
    if (!on) return;
    const to = zone.passageWorld(heroRoom, w.dir), p = hero.root.position;
    const dx = to.x - p.x, dz = to.z - p.z, d = Math.hypot(dx, dz) || 1;
    guide.g.position.set(p.x + dx / d * 1.9, 0.08, p.z + dz / d * 1.9);
    guide.g.rotation.y = Math.atan2(-dx, -dz);
    guide.mat.opacity = 0.55 + 0.35 * Math.sin(t * 4);
  });
  // ---- seeing in the dark (map_system._sight): a dark room is dark; a carried light makes a warm
  // circle round the hero, infravision a dim grey sight, nothing at all a glimmer to feel by ----
  engine.onTick(dt => {
    // exit signs fade with distance and step back in a fight (terrain.js LABEL_FADE)
    if (hero && hero.root) { LABEL_FADE.hero.set(hero.root.position.x, 0, hero.root.position.z); LABEL_FADE.on = true; }
    LABEL_FADE.combat = !!MH.state.inCombat;
    const s = (MH.state.player && MH.state.player.sight) || {};
    const lit = s.dark && s.light, eyes = s.dark && !s.light && s.see, blind = s.dark && !s.see;
    engine.darkness = !s.dark ? 0 : lit ? 0.35 : eyes ? 0.35 : 0.6;
    ents.sightRadius = !s.dark ? 0 : lit ? 16 : eyes ? 14 : 7;
    const L = engine.heroLight;
    if (!L) return;
    const want = lit ? 64 : blind ? 22 : 0;
    L.color.setHex(lit ? 0xffb36a : 0x8a9ac8);
    L.distance = lit ? 17 : 7;
    L.intensity += (want - L.intensity) * Math.min(1, dt * 4);
    if (hero && hero.root) L.position.set(hero.root.position.x, hero.root.position.y + 1.7, hero.root.position.z);
  });
  // stepping out of a marked blow's ground: the server hears where you stand at once
  cues.onLeave = () => { posClock = 0; };
  combat.onTelegraphEnd = k => cues.telegraphEnd(k);
  combat.onOpening = src => cues.opening(src);
  MH.bus.on('hud.abilityHover', a => cues.hoverAbility(a && a.id));
  // speech over the speaker's head: "Sage Aldric says, '...'" (NPCs, other players, you)
  const bubbles = createBubbles($('#plates'), engine);
  engine.onLateTick(() => { if (hero) bubbles.update(); });
  MH.bus.on('terminal.output', ({ html, text }) => {
    if (!hero || !MH.state.isLoggedIn) return;
    const plain = String(text || html || '').replace(/<[^>]+>/g, '').replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&');
    for (const line of plain.split(/\r?\n/)) {
      const m = /^\s*(.+?) (?:says?|exclaims?|asks?|whispers?|sings?)(?: to you)?,? ['"\u2018\u201c](.+?)['"\u2019\u201d]\s*$/.exec(line);
      if (!m) continue;
      const who = m[1].trim().toLowerCase(), words = m[2].trim();
      if (who === 'you') { bubbles.say(hero.root, words, { npc: false }); continue; }
      const e = [...ents.list.values()].find(x => x.root && x.data && String(x.data.name || '').toLowerCase() === who)
        || [...ents.list.values()].find(x => x.root && x.data && who.includes(String(x.data.name || '~').toLowerCase()));
      if (e) bubbles.say(e.root, words, { npc: e.kind !== 'player', lift: (e.plateY || 2.2) + 0.55 });
    }
  });
  engine.onTick((dt, t) => { if (hero) cues.update(dt, t); });
  // health running low (hud.js marks it at 30%): the heart beats, faster below 15%, and the
  // reddened edge pulses with it (hud.css)
  let beat = 0;
  engine.onTick(dt => {
    const p = MH.state.player, k = p && p.max_hp ? p.hp / p.max_hp : 1;
    const low = k > 0 && k <= 0.3, crit = low && k <= 0.15;
    document.documentElement.classList.toggle('hp-crit', crit);
    if (!low) { beat = 0; return; }
    if ((beat -= dt) <= 0) {
      beat = crit ? 0.62 : 0.95;
      sound.play('heartbeat');
      document.documentElement.style.setProperty('--beat', `${beat}s`);
    }
  });
  MH.bus.on('combat.events', p => {
    // the server's word on your swing clock (private to you)
    for (const e of p.events || []) if (e.k === 'swing' && combat.isHero(e.src)) clock.told(e, performance.now());
    if (hero) combat.handle(p.events, p.room);
    for (const e of p.events || []) if (e.k === 'death' && e.dst && e.dst.p && combat.isHero(e.dst)) hud.fallen();
    // the target's wind-up shows on the target frame as a cast bar
    const t = ents.targeted;
    if (!t || t.kind !== 'mob') return;
    for (const e of p.events || []) {
      if (!e.src || e.src.m !== t.data.id) continue;
      if (e.k === 'windup') hud.targetCast({ label: e.label, ms: e.ms });
      else if (e.k === 'resolve') hud.targetCast({ end: 'landed' });
      else if (e.k === 'cancel' && e.reason !== 'death') hud.targetCast({ end: 'broken' });
    }
  });
  // a creature the room brings in (a lair's herald, its master in its place: combat.js arrive)
  MH.bus.on('mob.move', p => { if (hero && p && (p.vnum == null || !heroRoom || p.vnum === heroRoom.vnum)) combat.arrive(p); });
  // your group: frames, the invite popup, loot rolls; click a member to target them (heals and
  // blessings go to your target), right-click for more
  MH.bus.on('group.update', e => hud.party.update(e && e.group));
  MH.bus.on('group.invite', e => hud.party.showInvite(e));
  MH.bus.on('loot.roll', r => hud.party.lootRoll(r));
  MH.bus.on('loot.result', r => hud.party.lootResult(r));
  // the marquee quest: an offer, a group member's embarking, its stages, the reward
  MH.bus.on('quest.offer', e => { sound.play('ui_offer'); hud.quest.offer(e.quest); });
  MH.bus.on('quest.embark', e => hud.quest.showEmbark(e));
  MH.bus.on('quest.stage', e => { sound.play('quest_stage'); hud.quest.stage(e); });
  MH.bus.on('quest.done', e => { sound.play('quest_done'); hud.quest.done(e); });
  MH.bus.on('ability.improve', () => sound.play('improve'));
  MH.bus.on('quest.mark', vnum => mm.setQuestMark(vnum == null ? null : vnum));
  // a level gained: a column of light on the hero, stars thrown up around them
  MH.bus.on('hud.levelup', () => {
    sound.play('levelup');
    if (!hero) return;
    const p = hero.root.position;
    fx.pillar(p, { school: 'holy', radius: 1.3, height: 10, time: 1.6 });
    fx.shockwave(p, { color: 0xffd86a, radius: 6, time: 0.9 });
    fx.glyph(p.clone().setY(1), { glyph: 'star', count: 34, color: 0xffe8a0, speed: 4, up: 3, life: 1.5, size: 0.5, gravity: 2, spin: 4 });
    fx.light(p.clone().setY(2), 0xffe0a0, 8, 1.2);
  });
  MH.bus.on('hud.targetPlayer', name => {
    const e = ents.list.get(`p${name}`);
    if (e) ents.setTarget(e.key, { byHand: true });
    else hud.toast(`${name} isn't in sight`);
  });
  MH.bus.on('hud.partyMenu', ({ name, x, y, leader }) => ctxMenu.show(x, y, name, [
    { label: 'Target', run: () => MH.bus.emit('hud.targetPlayer', name) },
    { label: 'Whisper…', run: () => hud.whisper(name) },
    { label: 'Follow', run: () => MH.sendCommand(`follow ${name}`) },
    ...(leader ? [{ label: 'Make leader', run: () => MH.sendCommand(`group leader ${name}`) },
      { label: 'Remove from group', run: () => MH.sendCommand(`group kick ${name}`) }] : []),
    { label: 'Leave group', run: () => MH.sendCommand('group leave') },
  ]));
  // other players: where they walk (relayed ~5x a second) and when they change rooms
  MH.bus.on('player.presence', p => ents.presence(p));
  MH.bus.on('player.move', p => { if (p && p.name && p.name !== MH.state.playerName) ents.playerMoved(p); });
  // another login took this character over: say so, then back to the login screen
  MH.bus.on('session.revoked', () => {
    hud.toast('This character was just logged in somewhere else.');
    setTimeout(() => location.reload(), 2600);
  });
  // the server went away mid-play (restarted, the network blinked): say so over the world, wait
  // for it, then reload and sign back in (shared/net.js MH.awaitServer)
  MH.bus.on('connection.lost', () => {
    if ($('#reconnect')) return;
    const v = document.createElement('div');
    v.id = 'reconnect';
    v.innerHTML = '<div class="ld-ring"></div><b>The mist thickens…</b><span>Lost touch with the world. Reconnecting…</span>';
    document.body.appendChild(v);
    if (MH.setCombat) MH.setCombat(false);
    MH.awaitServer(n => { if (n > 3) v.querySelector('span').textContent = `The world is away. Still trying (attempt ${n})…`; });
  });
  // creatures that take the stairs or a far passage leave and arrive in a puff of dust
  ents.onSnap = (from, to) => {
    for (const q of [from, to]) fx.p.emit(q.clone().setY(0.4), { count: 18, color: 0xd8d0c0, speed: 1.6, up: 0.6, life: 0.7, size: 0.4, grow: 0.5, drag: 1.5 });
  };
  // a creature charging in from next door: a snarl, and dust kicked up as it sets off
  ents.onCharge = e => {
    const at = e.root.position.clone();
    sound.play('growl', { at });
    fx.p.emit(at.clone().setY(0.25), { count: 14, color: 0xcabfa8, speed: 2.2, up: 0.4, life: 0.6, size: 0.35, grow: 0.6, drag: 2 });
    notice(e);
  };
  // a creature that has just noticed you: a "!" over its head and a sharp sting (once a while each)
  function notice(e) {
    if (!e || !e.root || e.kind !== 'mob') return;
    const now = performance.now();
    if (e.noticedAt && now - e.noticedAt < 15000) return;
    e.noticedAt = now;
    const p = e.root.position.clone().setY(e.root.position.y + (e.plateY || 2) + 0.35);
    fx.text(p, '!', { color: '#ffd23a', size: 34, rise: 0.5, life: 1.2, exact: true });
    sound.play('alert', { at: e.root.position });
  }
  // how each creature dies (corpse.js deathStyle; entities.js plays it on the body): a spirit's
  // last light rising, a slime's splash, a burning body's embers, a statue's shards
  ents.onDeath = (e, style) => {
    const at = e.root.position.clone(), mid = at.clone().setY(at.y + (e.plateY || 2) * 0.45);
    if (style === 'dissolve') {
      fx.p.emit(mid, { count: 34, color: 0xcfe8ff, bright: 1.8, speed: 0.6, up: 1.4, life: 1.6, size: 0.22, drag: 0.8, jitter: 0.8 });
      sound.play('aura', { at });
    } else if (style === 'burst') {
      fx.after(0.22, () => {
        fx.p.emit(mid, { count: 40, color: 0x7ad83a, bright: 1.3, speed: 3.6, up: 1.4, gravity: 9, life: 0.8, size: 0.24, drag: 0.6 });
        sound.play('step_water', { at, vol: 1.5 });
      });
    } else if (style === 'shatter') {
      fx.after(0.06, () => {
        fx.glyph(mid, { glyph: 'shard', count: 16, color: 0xd8d2c8, bright: 1.2, speed: 4.2, up: 2, gravity: 10, life: 0.9, size: 0.3, drag: 0.4, spin: 6 });
        fx.p.emit(at.clone().setY(0.3), { count: 20, color: 0xb8b0a0, speed: 2.4, up: 0.6, life: 0.9, size: 0.5, grow: 0.6, drag: 2 });
        sound.play('shatter_big', { at });
      });
    } else if (style === 'burn') {
      for (let i = 0; i < 6; i++) fx.after(i * 0.25, () => fx.p.emit(mid, { count: 10, color: i < 3 ? 0xff7a1a : 0x6a5a50, bright: i < 3 ? 2.2 : 0.6,
        speed: 0.6, up: 1.4, life: 0.9, size: i < 3 ? 0.22 : 0.5, grow: i < 3 ? -0.2 : 0.6, drag: 1, jitter: 0.7 }));
      sound.play('fizzle', { at });
    }
  };
  const mmSmall = createMinimap($('#minimap'), room => travelTo(room), () => engine.snapNorth());
  // the sun or moon on its arc, the season, the weather over the zone (hud/sky.js)
  // hunger, thirst, stamina and a posture to get up from, under the player frame (hud/body.js)
  const body = createBody($('#body-meters'), { icon: name => uiIcon(name, { size: 40 }), send: cmd => MH.sendCommand(cmd) });
  // the room's ways out and what holds there, under the minimap; the place's bite on screen (hud/roomcard.js)
  const roomCard = createRoomCard($('#minimap .mm-card'), { icon: (name, o) => uiIcon(name, o) });
  const envLayer = createEnvLayer({ breath: $('#breath'), corruption: $('#corruption') });
  // unread mail and the world's events, at the minimap's foot (hud/alerts.js)
  const alerts = createAlerts($('#minimap .mm-alerts'), { icon: name => uiIcon(name, { size: 36 }), openMail: () => hud.openPanel('mail') });
  // the minimap grows with its sky, room card and alerts: what sits below it (the quest tracker) follows
  // (its height as laid out, before the HUD's scale: the CSS multiplies by --ui)
  if (window.ResizeObserver) new ResizeObserver(() => { const h = $('#minimap').offsetHeight; if (h) document.documentElement.style.setProperty('--mm-h', `${h}px`); }).observe($('#minimap'));
  const skyDial = createSkyDial($('#minimap .mm-sky'), name => uiIcon(name, { size: 44, color: '#e6eef6', glow: 'rgba(190,215,240,.55)' }));
  // the big map (M): the same drawing, larger — the whole zone at a glance, click to walk there
  const bigEl = $('#bigmap');
  const mmBig = createMinimap(bigEl, room => { bigEl.classList.add('hidden'); travelTo(room); }, null, { cell: 1.7, browse: true });
  bigEl.querySelector('.bm-close').addEventListener('click', () => bigEl.classList.add('hidden'));
  let atlasP = null, knownRooms = [];
  const fetchAtlas = () => atlasP || (atlasP = fetch('/atlas').then(r => r.json()).catch(e => { atlasP = null; throw e; }));
  const fetchExplored = async () => (await fetch(`/explored?player=${encodeURIComponent(MH.state.playerName || '')}`)).json();
  const world = createWorldMap(bigEl.querySelector('.wm-canvas'), {
    fetchAtlas, fetchExplored,
    here: () => heroRoom && heroRoom.vnum,
    onZone: id => { zoneSel.value = String(id); showZone(id, 'zone'); },
  });
  // the zone list: every zone you have set foot in; choosing one shows it (another zone is only looked at)
  const zoneSel = bigEl.querySelector('.bm-zones');
  zoneSel.addEventListener('keydown', e => { if (e.key !== 'Escape') e.stopPropagation(); });
  zoneSel.addEventListener('change', () => showZone(Number(zoneSel.value)));
  async function fillZones() {
    try {
      const [atlas, ex] = await Promise.all([fetchAtlas(), fetchExplored()]);
      knownRooms = (ex && ex.rooms) || [];
      const here = zone ? zone.num : null;
      zoneSel.replaceChildren(...zoneIndex(atlas, knownRooms, here).map(z => {
        const o = document.createElement('option');
        o.value = String(z.id);
        o.textContent = z.id === here ? `${z.name} (you are here)` : z.name;
        return o;
      }));
      zoneSel.value = String(mmBig.browsing() ?? here);
    } catch (_) { /* the list stays as it was */ }
  }
  async function showZone(id, tab = null) {
    world.focusZone(id);
    if (tab) setMapTab(tab);
    if (!zone || id === zone.num) { mmBig.home(); return; }
    try { mmBig.browse(mapOfZone(await fetchZonemap(`zone=${id}`)), knownRooms); }
    catch (_) { hud.toast('That map could not be unrolled.'); }
  }
  bigEl.querySelector('.bm-zoom').addEventListener('click', e => {
    const z = e.target.closest('button') && e.target.closest('button').dataset.z;
    if (!z) return;
    if (z === 'home') {
      mmBig.home(); world.home();
      if (zone) zoneSel.value = String(zone.num);
      return;
    }
    const f = z === 'in' ? 1.25 : 0.8;
    if (mapTab === 'zone') mmBig.zoomBy(f); else world.zoomBy(f);
  });
  let mapTab = 'zone';
  const setMapTab = t => {
    mapTab = t;
    bigEl.querySelectorAll('.bm-tab').forEach(b => b.classList.toggle('on', b.dataset.tab === t));
    bigEl.querySelector('.mm-wrap').classList.toggle('hidden', t !== 'zone');
    bigEl.querySelector('.wm-wrap').classList.toggle('hidden', t !== 'world');
    world.show(t === 'world' && !bigEl.classList.contains('hidden'));
  };
  bigEl.querySelectorAll('.bm-tab').forEach(b => b.addEventListener('click', () => setMapTab(b.dataset.tab)));
  MH.bus.on('hud.map', on => {
    const show = on === undefined || on === null ? bigEl.classList.contains('hidden') : !!on;
    bigEl.classList.toggle('hidden', !show);
    if (show) { mmBig.home(); world.home(); mmBig.redraw(); setMapTab(mapTab); fillZones(); } else world.show(false);
  });
  const mm = {
    setZone: z => { mmSmall.setZone(z); mmBig.setZone(z); },
    setExplored: l => { mmSmall.setExplored(l); mmBig.setExplored(l); },
    setGuild: g => { mmSmall.setGuild(g); mmBig.setGuild(g); },
    setQuestMark: v => { mmSmall.setQuestMark(v); mmBig.setQuestMark(v); },
    setRoom: r => { mmSmall.setRoom(r); mmBig.setRoom(r); },
    setTime: t => { mmSmall.setTime(t); mmBig.setTime(t); },
    update: (p, yaw, cam) => { mmSmall.update(p, yaw, cam); if (!bigEl.classList.contains('hidden')) mmBig.update(p, yaw, cam); },
  };
  const prompt = createPrompt($('#prompt'));
  // the world's murmurs: sounds from where they come, creatures heard next door as cues (hud/ambient.js)
  const ambient = createAmbient({
    sound, hero: () => hero && hero.root.position, camYaw: () => engine.rig.yaw,
    centreOf: v => { const r = zone && zone.rooms.get(v); return r ? zone.centre(r) : null; },
    minimaps: [mmSmall, mmBig], root: $('#amb-cue'), caption: $('#amb-caption'),
    captions: () => { try { return localStorage.getItem('mh3d_ambcap') === 'on'; } catch (_) { return false; } },
  });
  // a creature heard next door: its way out flares on the room's compass too
  MH.bus.on('ambient.murmur', m => { ambient.on(m); const c = cueOf(m); if (c && c.dir) roomCard.ping(c.dir); });
  const castbar = createCastbar($('#castbar'));
  const ctxMenu = createContextMenu($('#ctx-menu'));
  let zone = null, hero = null, ctl = null, sync = null, heroRoom = null;
  // (seamless borders: the zone maps in hand, by zone number; the compass steps)
  const zmCache = new Map();
  const CARDS = { north: [0, -1], south: [0, 1], east: [1, 0], west: [-1, 0] };
  let starting = null, slide = null, hop = null, lastPayload = null, leashToast = 0, doorToast = 0;
  // stairs and other passages: a gate keeps the ones you arrived beside quiet until you mean
  // them (passages.js); `climb` is the short step onto or off the stairs around a hop
  const gate = new PassageGate();
  let heroSpots = [], lastActive = 0, climb = null, travel = null, relocating = null;
  let stepSurface = 'step_dirt', stride = 0;   // footsteps: what is underfoot, distance since the last

  // ---- server events ----
  MH.bus.on('map', payload => {
    lastPayload = payload;
    if (zone) applySky();
    skyDial.set(payload.time, payload.weather);
    if (payload.current_room) {
      skyDial.setIndoors((payload.current_room.flags || []).includes('indoors'));
      roomCard.update(payload.current_room);
      envLayer.update(payload.current_room, payload.weather);
    }
    if (payload.player) { envLayer.body(payload.player); alerts.setMail(payload.player.mail); }
    if ('world_events' in payload) alerts.setEvents(payload.world_events);
    if (payload.player) { hud.setPlayer(payload.player); body.update(payload.player); ents.heroLevel = payload.player.level || 1; }
    // what the hero wears (gear_look.py): re-dressed when it changes
    if (hero && payload.player && payload.player.look) dress(hero, payload.player.look, payload.player.char_class);
    if (hero && payload.player) ride(payload.player);
    if (ctl && payload.player) ctl.setPosture(payload.player.position);    // resting sits down, sleeping lies down
    if ('group' in payload) hud.party.update(payload.group);
    if (payload.player && 'quest' in payload.player) hud.quest.update(payload.player.quest);
    if (!payload.player || !payload.player.vnum) return;
    if (!zone) { if (!starting) starting = start(payload).catch(err => { console.error(err); hud.toast('Could not load the world: ' + err.message); }).finally(() => { starting = null; }); return; }
    if (starting) return;
    ents.sync(payload, MH.state.playerName); loot.sync(payload); spots.sync(payload); followLoot(payload);
    applyPendingAggro();
    mm.setExplored((payload.rooms || []).map(r => r.vnum));
    mm.setTime(payload.time);
    mm.setGuild(payload.player.guild);
    sync.onMap(payload);
  });
  MH.bus.on('combat.update', p => {
    if (p && 'group' in p) hud.party.update(p.group);
    if (MH.state.player) { hud.setPlayer(MH.state.player); body.update(MH.state.player); }
    ents.combat(p);
    const t = ents.targeted;
    if (t) hud.setTarget({ kind: t.kind, ...t.data });
    // (swings, hits and casts are drawn from the server's combat events: combat.js)
  });
  // the hour turning, the sky changing over the zone (web_hud.py world_tick): the dial and the 3D sky
  MH.bus.on('world.tick', e => {
    if (lastPayload) { if (e.time) lastPayload.time = e.time; if (e.weather) lastPayload.weather = e.weather; }
    skyDial.set(e.time, e.weather);
    mm.setTime(e.time);
    if (zone) applySky();
    if (lastPayload && lastPayload.current_room) envLayer.update(lastPayload.current_room, lastPayload.weather);
  });
  // an invasion, double experience, a world boss begins or ends (web_hud.py world_event)
  MH.bus.on('world.event', e => alerts.setEvents(e.events));
  // a step of an ordinary quest (quests.py quest_progress): a toast, a chime when it is done
  MH.bus.on('quest.progress', e => { hud.toast(progressText(e)); if (e.done) sound.play('quest_stage'); });
  // the body between map payloads (web_hud.py): regeneration out of a fight, a posture taken
  MH.bus.on('vitals', () => {
    const p = MH.state.player;
    if (!p) return;
    hud.setPlayer(p);
    body.update(p);
    envLayer.body(p);
    alerts.setMail(p.mail);
    if (ctl) ctl.setPosture(p.position);
  });
  MH.bus.on('move.result', res => { if (sync) sync.onResult(res); });
  MH.bus.on('player.look', p => ents.look(p));      // another player changed gear
  MH.bus.on('target.set', t => hud.setTarget(t));
  MH.bus.on('target.clear', () => hud.setTarget(null));

  // ---- riding (steed.js): the hero sits their mount, and goes as fast as the server says ----
  let riding = null, raft = null, onWater = false;
  function ride(p) {
    if (!hero || !ctl) return;
    const key = p.mount ? p.mount.key || 'horse' : null;
    riding = mountRider(hero, key, riding);
    ctl.mounted = !!riding;
    ctl.speedMul = Math.max(1, Math.min(1.8, Number(p.speed) || 1));
  }

  // ---- start: the first map payload after login ----
  async function start(payload) {
    const v = payload.player.vnum;
    const zm = await fetchZonemap(`vnum=${v}`);
    if (backdrop) { backdrop.dispose(); backdrop = null; }
    engine.rig.yaw = 0;          // the title screen's drift ends: play starts north up
    enterZone(zm);
    const room = zone.rooms.get(v);
    hero = await spawnDressed(payload.player.look, payload.player.char_class);
    engine.scene.add(hero.root);
    ctl = new Controller(engine, hero, blockedFor);
    ride(payload.player);
    ctl.avoidDefault = avoidStairs();
    sync = new Sync({
      heroRoomVnum: () => heroRoom && heroRoom.vnum,
      confirmed: v2 => onConfirmed(v2),
      refused: res => onRefused(res),
      relocate: v2 => relocate(v2),
    });
    sync.start(v);
    zone.prebuild(room, 1);
    placeHero(room, zone.centre(room));
    engine.rig.target.copy(hero.root.position);
    engine.placeCamera(true);
    hud.showGame(true);
    hud.banner(room.name, zone.name);
    ents.sync(payload, MH.state.playerName); loot.sync(payload); spots.sync(payload); followLoot(payload);
    mm.setExplored((payload.rooms || []).map(r => r.vnum));
    mm.setTime(payload.time);
    window.MH3D = { engine, zone: () => zone, hero, ctl, sync, ents, loot, fx, combat, hud, cues, THREE, sound, adorn, wards, sky, wild, spots,
      heroRoom: () => heroRoom, hop: () => hop, gate, lastPayload: () => lastPayload,
      // for probes: an area spell being aimed ({id, at, radius}), or null
      aim: () => (aiming ? { id: aiming.ab.id, at: aiming.at, radius: aiming.ab.radius } : null),
      // for probes: walk onto a passage of this room on purpose (what clicking it does)
      walkToPassage: dir => { const sp = zone.passageWorld(heroRoom, dir); ctl.walkTo(sp.x, sp.z, null, { goal: { room: heroRoom.vnum, dir }, avoid: null }); } };
  }

  function enterZone(zm) {
    if (zone) zone.dispose();
    zone = new Zone(engine, kits, zm);
    ents.setZone(zone);
    loot.clear();
    spots.clear();
    mm.setZone(zone);
    zmCache.set(zm.zone, zm);
    nextDoor(zone);
  }
  // ---- seamless borders (docs/OPEN_WORLD.md, phase 3) ----
  // The maps of the zones next door are fetched as a zone is entered, kept, and drawn past its
  // borders (zone.addGhost): crossing a border is then a step, not a load and a fade.
  async function nextDoor(z) {
    const seen = new Set();
    for (const room of z.rooms.values()) {
      for (const [d, e] of Object.entries(room.data.exits || {})) {
        if (e.kind !== 'zone' || !CARDS[d] || e.zone == null || seen.has(e.zone)) continue;
        seen.add(e.zone);
        let zm = zmCache.get(e.zone);
        if (!zm) {
          try { zm = await fetchZonemap(`vnum=${e.to}`); } catch (_) { continue; }
          if (zm) zmCache.set(zm.zone, zm);
        }
        if (!zm || zone !== z) { if (zone !== z) return; continue; }
        const b = zm.rooms.find(r => r.vnum === e.to);
        if (!b) continue;
        const [dx, dy] = CARDS[d];
        z.addGhost(zm, room.cx + dx - b.cell[0], room.cy + dy - b.cell[1], room.data.level || 0, b.level || 0);
      }
    }
  }

  // hero's body is blocked by walls and by any crossing into another room that is not an
  // open exit. Mid-fight the hero may walk on out (combat.walk_out: a parting blow from each foe)
  function blockedFor(x, z, fx, fz) {
    const from = zone.roomAt(fx, fz);
    return zone.blocked(x, z, from);
  }

  function placeHero(room, pos) {
    hero.root.position.set(pos.x, 0, pos.z);
    setHeroRoom(room);
  }
  function setHeroRoom(room) {
    if (gloomRoom != null && (!room || room.vnum !== gloomRoom)) { engine.gloom = 0; gloomRoom = null; }
    const changed = heroRoom !== room;
    heroRoom = room;
    mm.setRoom(room);
    if (changed) {
      if (hud.closeTalk) hud.closeTalk();
      heroSpots = zone.passageSpots(room);
      const p = hero.root.position;
      gate.enterRoom(heroSpots, { x: p.x - room.ox, z: p.z - room.oz });
    }
    const L = zone.layoutOf(room);
    // on open water the hero is on a raft (unless a mount carries them)
    onWater = L.theme === 'water_swim' || L.theme === 'water_noswim';
    if (onWater && !raft) raft = makeRaft();
    if (raft) { if (onWater && !riding) hero.root.add(raft); else hero.root.remove(raft); }
    const look = { theme: L.theme, zoneKey: L.zoneKey, dark: L.dark, snowy: L.snowy, icy: L.icy,
      interior: L.theme === 'inside' ? interiorKind(L) : null };
    sound.setZoneMusic(musicFor(look));
    sound.ambience(bedFor(look));
    stepSurface = surfaceFor(look);
    // the sky and its small life: open sky or not, night or day, this room's bounds
    const hourNow = lastPayload && lastPayload.time ? lastPayload.time.hour : 12;
    skyTheme = L.theme;
    skyOpen = !L.dark && !UNDER_SKY.has(L.theme);
    applySky();
    wild.set(L.theme, skyOpen, hourNow >= 20 || hourNow < 5, { x0: room.ox, z0: room.oz, x1: room.ox + ROOM_W, z1: room.oz + ROOM_H });
    applyFar(L);
    vistas.set(room, zone && zone.cells, skyOpen);
    const hour = lastPayload && lastPayload.time ? lastPayload.time.hour : 12;
    // the room's look (room_looks.py): rock is darkest, then crypts and sewers; sand, snow and ash
    // colour the day
    const rock = L.theme === 'cave' || L.theme === 'mine';
    if (L.theme === 'ice_cave' || L.theme === 'lava_cave') { engine.setMood(L.theme); return; }
    const dark = L.dark || ['dungeon', 'crypt', 'sewer'].includes(L.theme);
    const night = hour >= 20 || hour < 5, dusk = hour >= 18 || hour < 7;
    // (a spider's lair is dark by its flags, but its own gloom is dark enough: the webs must show)
    const mood = rock ? 'cave' : L.theme === 'web' ? 'web' : L.theme === 'necropolis' ? 'necropolis' : L.theme === 'drow' ? 'drow' : L.theme === 'foundry' ? 'foundry' : L.theme === 'sewer' ? 'sewer' : dark ? 'crypt' : L.theme === 'inside' ? 'interior'
      : L.theme === 'volcanic' ? 'volcanic' : L.theme === 'underwater' ? 'underwater'
      // (snow keeps its cold light at dawn and dusk: the warm dusk sun made a snowfield sand)
      : L.theme === 'snow' && !night ? 'snow' : night ? 'night' : dusk ? 'dusk'
      : L.theme === 'water_swim' || L.theme === 'water_noswim' ? 'sea'
      : L.theme === 'desert' ? 'desert' : L.theme === 'snow' ? 'snow' : L.theme === 'forest' ? 'forest' : 'day';
    engine.setMood(mood);
    // a zone's light (zone_tone.py): green ghost-fire, cold moonlight, the warmth of torches
    const light = L.tone && TONE_LIGHT[L.tone.light];
    if (light) {
      const m = engine.MOODS ? engine.MOODS[mood] : null;
      const mix = (a, b, k) => new THREE.Color(a).lerp(new THREE.Color(b), k).getHex();
      if (m) engine.setMood({ sun: mix(m.sun, light, 0.55), sky: mix(m.sky, light, 0.3), fog: mix(m.fog, light, 0.12) });
    }
  }

  // how far the hero sees (far.js): the quality's reach, and the far hills under open sky
  function applyFar(L) {
    const f = FAR[engine.quality && engine.quality.name] || FAR.high;
    engine.farSight = f.sight;
    if (!zone || !zone.far) return;
    zone.far.range = f.range;      // (the zones next door follow it: zone.update)
    const kind = farKind(L && L.theme);
    zone.far.outdoors = !!L && !L.dark && kind !== 'none' && kind !== 'roof';
    zone.far.sea = kind === 'water';     // the far hills lie down into a sea horizon
  }

  // ---- walking between rooms ----
  function heroWalkedInto(from, to) {
    setHeroRoom(to);
    sync.walked(from.vnum, to.vnum, zone.openDir(from, to));
    hud.banner(to.name, '');
  }
  function onConfirmed(v) {
    if (hop && hop.to === v && !hop.loading) finishHop(v);
  }
  function onRefused(res) {
    // an empty reason is the server saying "you are not where you think": just resync
    if (res.reason) hud.toast(res.reason);
    if (hop) {
      const h = hop; hop = null; climb = null;
      $('#vignette').style.background = '';
      if (heroRoom && heroRoom.vnum === res.room) {
        // step back off the stairs you tried (beside them, not across the room)
        slide = { from: hero.root.position.clone(), to: zone.side(heroRoom, h.dir), t: 0, room: heroRoom };
        gate.disarm(h.dir);
        return;
      }
    }
    const back = zone.rooms.get(res.room);
    if (!back) return relocate(res.room);
    // slide back through the shared opening into the room the server kept us in
    const d = heroRoom && zone.openDir(back, heroRoom);
    const target = d ? zone.entry(back, d) : zone.centre(back);
    slide = { from: hero.root.position.clone(), to: target, t: 0, room: back };
    ctl.stop();
  }
  // a room change the client did not ask for (flee, recall, goto, a portal, following a
  // leader): the server's room wins. One at a time: a second request waits for the first.
  async function relocate(v) {
    if (hop && hop.to === v) return;          // our own hop is already taking us there
    if (relocating) { relocating.next = v; return; }
    relocating = { next: null };
    try {
      const room = zone.rooms.get(v);
      const oldV = heroRoom && heroRoom.vnum;
      if (room) {
        const d = heroRoom && zone.openDir(heroRoom, room);
        if (d) { slide = { from: hero.root.position.clone(), to: zone.entry(room, REV[d]), t: 0, room }; return; }
        return teleport(room, oldV != null ? zone.arrival(room, oldV, null) : zone.centre(room));
      }
      // another zone: load it, arrive by the exit that leads back where we were
      const zm = await fetchZonemap(`vnum=${v}`);
      enterZone(zm);
      const r = zone.rooms.get(v);
      teleport(r, oldV != null ? zone.arrival(r, oldV, null) : zone.centre(r));
      hud.banner(r.name, zone.name);
      if (lastPayload) { ents.sync(lastPayload, MH.state.playerName); loot.sync(lastPayload); spots.sync(lastPayload); }
    } finally {
      const next = relocating && relocating.next;
      relocating = null;
      if (next != null && (!heroRoom || next !== heroRoom.vnum)) relocate(next);
    }
  }
  function teleport(room, pos) {
    sound.play('teleport');
    zone.prebuild(room, 1);
    placeHero(room, pos);
    ctl.halt();
    engine.rig.target.copy(hero.root.position);
    engine.placeCamera(true);
    flashDip();
    gate.landed(performance.now());
  }
  function flashDip() {
    const v = $('#vignette');
    v.style.transition = 'none'; v.style.background = 'rgba(4,4,8,.85)';
    requestAnimationFrame(() => { v.style.transition = 'background .45s'; v.style.background = ''; });
  }

  // ---- passages: exits that hop (misaligned rooms, stairs, portals, zone borders) ----
  // The hop stays in flight until the arrival is applied (including loading another zone),
  // so the frame loop can never send the same move twice.
  function startHop(ps) {
    const spot = zone.passageWorld(heroRoom, ps.dir);
    const stairs = ps.dir === 'up' || ps.dir === 'down';
    // (a zone next door whose map is in hand, across a compass side: walked into, not loaded)
    const seamless = ps.exit.kind === 'zone' && !!CARDS[ps.dir] && zmCache.has(ps.exit.zone);
    hop = { from: heroRoom, dir: ps.dir, to: ps.exit.to, kind: ps.exit.kind, zone: ps.exit.zone, seamless, at: performance.now() };
    ctl.halt();
    if (!seamless) sound.play(stairs ? stepSurface : 'hop');
    sync.walked(heroRoom.vnum, ps.exit.to, ps.dir);
    // step onto the stairs (a little up, or down into the stairwell) while the screen dims
    climb = { from: hero.root.position.clone(), to: spot.setY(stairs ? (ps.dir === 'up' ? 0.5 : -0.6) : 0), t: 0, dur: seamless ? 0.2 : 0.35 };
    if (seamless) return;
    const v = $('#vignette');
    v.style.transition = 'background .25s'; v.style.background = 'rgba(4,4,8,.9)';
  }
  async function finishHop(v) {
    const h = hop;
    if (!h) return;
    h.loading = true;
    try {
      if (h.kind === 'zone' || !zone.rooms.get(v)) {
        let zm = h.zone != null ? zmCache.get(h.zone) : null;
        if (!zm || !zm.rooms.some(r => r.vnum === v)) {
          try { zm = await fetchZonemap(`vnum=${v}`); } catch (_) {
            try { zm = await fetchZonemap(`vnum=${v}`); } catch (err) { zm = null; }
          }
        }
        if (!zm) { hop = null; climb = null; return relocate(v); }
        enterZone(zm);
        const r = zone.rooms.get(v);
        land(r, zone.arrival(r, h.from.vnum, h.dir), h.from.vnum, h.seamless);
        hud.banner(r.name, zone.name);
        if (lastPayload) { ents.sync(lastPayload, MH.state.playerName); loot.sync(lastPayload); spots.sync(lastPayload); }
      } else {
        const r = zone.rooms.get(v);
        land(r, zone.arrival(r, h.from.vnum, h.dir), h.from.vnum);
        hud.banner(r.name, '');
      }
    } finally {
      if (hop === h) hop = null;
    }
    // minimap travel goes on across the stairs
    if (travel && heroRoom !== travel.target) setTimeout(() => { if (travel) travelTo(travel.target, travel.hops + 1); }, 60);
    else travel = null;
  }
  // arrive: appear on the passage that leads back, then step off it to the arrival point
  function land(room, at, fromVnum, seamless = false) {
    zone.prebuild(room, 1);
    const side = Object.keys(room.data.exits).find(d => room.data.exits[d].to === fromVnum && room.data.exits[d].kind !== 'open');
    const from = side ? zone.passageWorld(room, side) : at.clone();
    placeHero(room, at);
    ctl.halt();
    engine.rig.target.copy(at);
    engine.placeCamera(true);
    climb = { from: from.setY(side === 'up' ? 0.5 : side === 'down' ? -0.6 : 0), to: at.clone(), t: 0, dur: seamless ? 0.2 : 0.3 };
    hero.root.position.copy(climb.from);
    if (!seamless) flashDip();          // (across a border into land already in sight: no dip)
    gate.landed(performance.now());
  }

  // ---- travel: click a room on the minimap ----
  // Walk through shared openings to the first passage on the way (stairs, a misaligned
  // doorway), take it on purpose, then plan again from the other side (up to 8 hops).
  function travelTo(room, hops = 0) {
    if (!heroRoom || room === heroRoom || hops > 8) { travel = null; return; }
    const path = zone.roomPath(heroRoom, room, { passages: true });
    if (!path) { travel = null; return hud.toast('No open path there from here.'); }
    const pts = [];
    let goal = null;
    for (let i = 1; i < path.length; i++) {
      const a = path[i - 1], b = path[i];
      const d = zone.openDir(a, b);
      if (d) {
        pts.push(zone.entry(a, d), zone.entry(b, REV[d]));
        if (i === path.length - 1) pts.push(zone.centre(b));
        continue;
      }
      goal = { room: a.vnum, dir: zone.linkDir(a, b) };
      pts.push(zone.passageWorld(a, goal.dir));
      break;
    }
    travel = goal ? { target: room, hops } : null;
    const p0 = hero.root.position;
    const gx = pts.length ? Math.floor(pts[0].x) : 0, gz = pts.length ? Math.floor(pts[0].z) : 0;
    const avoid = avoidStairs();
    const lead = pts.length ? findPath(p0.x, p0.z, pts[0].x, pts[0].z, (ax, az, bx, bz) =>
      !blockedFor(bx + 0.5, bz + 0.5, ax + 0.5, az + 0.5) && !((bx !== gx || bz !== gz) && avoid(bx, bz))) || [] : [];
    ctl.follow((lead.length ? lead : pts.slice(0, 1)).concat(pts.slice(1)).map(p => ({ x: p.x, z: p.z })), null, { goal });
  }
  // stairs and portal tiles: paths go around them unless they are where you are going
  function avoidStairs() {
    return (tx, tz) => {
      const r = zone && zone.roomAt(tx + 0.5, tz + 0.5);
      return !!r && zone.avoidTile(r, tx - r.ox, tz - r.oz);
    };
  }
  // the passage whose stairs or portal tile is at a world point, if any
  function passageUnder(x, z) {
    const r = zone.roomAt(x, z);
    if (!r || r !== heroRoom) return null;
    for (const s of heroSpots) if (Math.hypot(x - (r.ox + s.x), z - (r.oz + s.z)) < 0.8) return s.key;
    return null;
  }

  // ---- targeting and actions ----
  const canvas = engine.renderer.domElement;
  // ---- aiming an area spell (aim.js): the key starts it, the mouse moves the circle, a left
  // click (or the key again) casts it there, a right click or Escape lets it go ----
  const aimCircle = new AimCircle(engine.scene);
  let aiming = null;           // { ab, at: {x, z} }
  let mouse = null;            // the last place the mouse was over the canvas
  function aimPoint() {
    const p = hero.root.position;
    let g = mouse && ctl.groundAt(mouse.x, mouse.y);
    if (!g && ents.targeted && ents.targeted.root) g = ents.targeted.root.position;
    if (!g) g = p;
    return clampAim(p, g, aiming.ab.range, [heroRoom, ...openNeighbours()], ROOM_W, ROOM_H);
  }
  // the rooms an aimed circle may land in besides the hero's: joined by an open way, no closed
  // door, neither room peaceful (reach.py: what it catches there charges in)
  function openNeighbours() {
    if (!heroRoom || !zone || (heroRoom.data.flags || []).includes('peaceful')) return [];
    return Object.entries(heroRoom.data.exits || {})
      .filter(([d, x]) => x.kind === 'open' && !zone.doorClosed(heroRoom, d))
      .map(([, x]) => zone.rooms.get(x.to))
      .filter(r => r && !(r.data.flags || []).includes('peaceful'));
  }
  function startAim(ab) {
    if (!hero || !heroRoom || !ctl) return false;
    aiming = { ab };
    aimCircle.show(ab.radius, ab.range, 0xffa040);
    aiming.at = aimPoint();
    aimCircle.place(aiming.at, hero.root.position, aiming.at.clamped);
    hud.toast(`${ab.name || 'Aim'}: click to cast, right-click or Esc to cancel`);
    return true;
  }
  function stopAim() { aiming = null; aimCircle.hide(); }
  function castAimed() {
    if (!aiming) return;
    const ab = aiming.ab, at = aimPoint();
    stopAim();
    ents.expectPull(3500);       // (what the circle catches next door waits for it to land)
    MH.bus.emit('hud.ability', { ...ab, at });
  }
  canvas.addEventListener('pointermove', e => { mouse = { x: e.clientX, y: e.clientY }; });
  engine.onTick(dt => {
    if (!aiming) return;
    if (!hero || !heroRoom) return stopAim();
    aiming.at = aimPoint();
    aimCircle.place(aiming.at, hero.root.position, aiming.at.clamped);
    aimCircle.tick(dt);
  });
  canvas.addEventListener('pointerdown', e => {
    if (aiming) {
      if (e.button === 0) { e.stopImmediatePropagation(); castAimed(); }
      else if (e.button === 2) stopAim();
      return;
    }
    if (e.button === 0 && e.altKey && ctl) { const g = ctl.groundAt(e.clientX, e.clientY); if (g) pingAt(g.x, g.z); return; }
    if (e.button !== 0 || e.ctrlKey || !ctl) return;
    const hit = ents.pick(e.clientX, e.clientY);
    if (hit) { ents.setTarget(hit.key, { byHand: true }); return; }
    const item = loot.pick(e.clientX, e.clientY, canvas);
    if (item) { takeLoot(item); return; }
    const spot = spots.pick(e.clientX, e.clientY, canvas);
    if (spot) { workSpot(spot); return; }
    const g = ctl.groundAt(e.clientX, e.clientY);
    if (!g) return;
    travel = null;
    // a click on the stairs means "take them"; anywhere else, walk around stairs on the way
    const pass = passageUnder(g.x, g.z);
    if (pass) { const s = zone.passageWorld(heroRoom, pass); ctl.walkTo(s.x, s.z, null, { goal: { room: heroRoom.vnum, dir: pass }, avoid: null }); }
    else ctl.walkTo(g.x, g.z);
  });
  canvas.addEventListener('dblclick', e => {
    const hit = ents.pick(e.clientX, e.clientY);
    if (hit && hit.kind === 'mob') { ents.setTarget(hit.key, { byHand: true }); attack(); }
  });
  // a corpse aimed at with Tab after a fight (targeting.tabOrder): its ring marked, the target
  // frame shows it, F walks over and loots it; any creature targeted, or the corpse gone, clears it
  let corpseTarget = null;
  function setCorpseTarget(key) {
    corpseTarget = key || null;
    loot.mark(corpseTarget);
    const l = corpseTarget && loot.list.get(corpseTarget);
    if (l) hud.setTarget({ kind: 'corpse', key: l.key, name: l.item.short || l.item.name, victim: victimOf(l.item.name || l.item.short) });
  }
  MH.bus.on('target.set', () => { if (corpseTarget) { corpseTarget = null; loot.mark(null); } });
  engine.onTick(() => { if (corpseTarget && !loot.list.has(corpseTarget)) { setCorpseTarget(null); if (!ents.targeted) hud.setTarget(null); } });
  MH.bus.on('hud.untarget', () => { ents.setTarget(null); if (corpseTarget) { setCorpseTarget(null); hud.setTarget(null); } });
  MH.bus.on('hud.cycleTarget', () => {
    if (!hero) return;
    const p = hero.root.position;
    // your own room first (the server fights room by room); the next room's only when yours has
    // nothing, and then only what is close (a thief 16 m off through a wall is no target)
    const all = [...ents.list.values()].filter(e => e.kind === 'mob' && e.root && e.root.position.distanceTo(p) < 22)
      .map(e => Object.assign(e, { dist: e.root.position.distanceTo(p) }));
    const mine = heroRoom ? all.filter(e => e.vnum === heroRoom.vnum) : all;
    const near = mine.length ? mine : all.filter(e => e.dist < 14);
    const corpses = [...loot.list.values()].filter(l => l.corpse && l.root && l.root.position.distanceTo(p) < 22)
      .map(l => ({ key: l.key, dist: l.root.position.distanceTo(p) }));
    const order = tabOrder(near, corpses);
    if (!order.length) return hud.toast('Nothing nearby to target.');
    const cur = corpseTarget ? `corpse:${corpseTarget}` : `mob:${ents.target}`;
    const i = order.findIndex(o => `${o.kind}:${o.key}` === cur);
    const next = order[(i + 1) % order.length];
    if (next.kind === 'corpse') { ents.setTarget(null); setCorpseTarget(next.key); }
    else ents.setTarget(next.key, { byHand: true });
  });
  // how far from its target an action reaches (combat_range.py via /combatdata);
  // null for actions centred on the hero (rally, fade, crescendo...)
  // whether an ability strikes from afar (reach.py pulls across an edge only for these)
  // ...and the leaps and charges carry the hero across to it instead
  function pullsOf(id, spell) {
    const ab = ranges.abilities && ranges.abilities[id];
    return ab ? /^(ranged|blast)/.test(ab.shape) : !!spell;
  }
  function leapsOf(id) {
    const ab = ranges.abilities && ranges.abilities[id];
    return !!(ab && ab.shape === 'dash');
  }
  function rangeOf(id, spell) {
    if (id === 'attack') return reachOf();
    const ab = ranges.abilities && ranges.abilities[id];
    if (ab) return /^(self|nova)/.test(ab.shape) ? null : ab.range;
    return spell ? ranges.spellDefault || 14 : ranges.melee || 2.5;
  }
  // the server fights within one room: be in the target's room and within the action's
  // reach, walking only as far as needed (an archer stops at bow range, not in its face)
  // a shot, a bolt or an aimed spell at a creature in the next room, from where the hero stands
  // (reach.py): the two rooms joined by an open way (no closed door, neither peaceful), the
  // creature one that would come (no servant, sentinel or boss) and within the action's range;
  // the server pulls it in, then the ordinary command strikes it in the hero's room
  // A leap or a charge (`leap`) carries the hero over instead: the hero moves into the
  // creature's room as by walking (webmove, so every rule of moving applies), out of a fight
  // only, and any creature may be leapt at (a boss or a sentinel answers where it stands)
  function openWayTo(t) {
    const there = zone.rooms.get(t.vnum);
    const way = there && Object.entries(heroRoom.data.exits || {}).find(([, x]) => x.to === t.vnum && x.kind === 'open');
    if (!way || zone.doorClosed(heroRoom, way[0])) return null;
    if ((heroRoom.data.flags || []).includes('peaceful') || (there.data.flags || []).includes('peaceful')) return null;
    return { there, dir: way[0] };
  }
  function reachAcross(t, range, pulls, leap = false) {
    if (!(pulls || leap) || range == null || !heroRoom || !zone || !t || !t.root || t.kind !== 'mob' || t.vnum === heroRoom.vnum) return false;
    if (leap && MH.state.inCombat) return false;
    if (!openWayTo(t)) return false;
    const m = t.data || {};
    if (m.shopkeeper || m.trainer) return false;
    if (!leap && (m.boss || (m.flags || []).includes('sentinel') || (m.flags || []).includes('boss'))) return false;
    const p = hero.root.position, q = t.root.position;
    return Math.hypot(q.x - p.x, q.z - p.z) <= range + 0.5;
  }
  // over the edge onto the creature: the server is told of the room first (the ability that
  // follows finds the creature beside the hero), then the ability's own leap, dash or blink
  // carries the hero there, landing inside the creature's room
  function leapAcross(t, then) {
    const { there, dir } = openWayTo(t);
    const from = heroRoom;
    setHeroRoom(there);
    sync.walked(from.vnum, there.vnum, dir);
    then();
    const p = hero.root.position, q = t.root.position;
    const d = Math.hypot(q.x - p.x, q.z - p.z) || 1, k = Math.max(0, d - 1.3) / d;
    const x = Math.min(there.ox + ROOM_W - 1, Math.max(there.ox + 1, p.x + (q.x - p.x) * k));
    const z = Math.min(there.oz + ROOM_H - 1, Math.max(there.oz + 1, p.z + (q.z - p.z) * k));
    if (ctl.dashing) { ctl.dashing.tx = x; ctl.dashing.tz = z; }
    else if (zone.roomAt(p.x, p.z) !== there) ctl.dash(x, z, 0.45, { height: 1.6 });
  }
  function inReach(t, range, then, { pulls = false, leap = false, ability = 'attack' } = {}) {
    // (the target fell, or its body was taken away, as the key went down: nothing to reach)
    if (!t || !t.root || !hero || !hero.root) return hud.toast('No target — click a creature or press Tab.');
    const same = heroRoom && t.vnum === heroRoom.vnum;
    const p = hero.root.position, q = t.root.position;
    const d = Math.hypot(q.x - p.x, q.z - p.z);
    if (range == null || (same && d <= range + 0.3)) return then();
    if (!same && leap && reachAcross(t, range, false, true)) return leapAcross(t, then);
    if (!same && reachAcross(t, range, pulls)) {
      // (where it is drawn, in its room's metres: the server measures from there)
      const tr = zone && zone.rooms.get(t.vnum), at = tr ? ` @${(q.x - tr.ox).toFixed(1)},${(q.z - tr.oz).toFixed(1)}` : '';
      ents.expectPull();
      MH.sendCommand(`webpull ${refFor(t)} ${ability}${at}`, false);
      return then();
    }
    if (same) return approach(t, range, then);
    // another room (the server fights room by room): stop just inside the target's room,
    // at the action's reach if the room is big enough for it
    const room = zone && zone.rooms.get(t.vnum);
    if (!room) return approach(t, Math.min(range, 4), () => { if (heroRoom && t.vnum === heroRoom.vnum) then(); });
    const k = Math.max(1.2, range - 0.6) / (d || 1);
    const x = Math.min(room.ox + ROOM_W - 1.5, Math.max(room.ox + 1.5, q.x + (p.x - q.x) * k));
    const z = Math.min(room.oz + ROOM_H - 1.5, Math.max(room.oz + 1.5, q.z + (p.z - q.z) * k));
    ctl.walkTo(x, z, () => { if (heroRoom && t.vnum === heroRoom.vnum) then(); });
  }
  function attack() {
    // a corpse aimed at: F loots it
    if (corpseTarget && !ents.targeted) { const l = loot.list.get(corpseTarget); if (l) return takeLoot(l); }
    const t = ents.targeted;
    if (!t || !t.root) return hud.toast('No target — click a creature or press Tab.');
    if (t.kind !== 'mob') return hud.toast('You cannot attack that.');
    inReach(t, reachOf(), () => {
      ctl.face(t.root.position.x, t.root.position.z);
      if (actionMode()) {
        // real time: every press goes to the server; a blow that is due shows at once, an early
        // press waits for the clock (pressed in its last moments, that blow lands perfectly)
        const now = performance.now();
        const press = clock.press(now);
        if (press.swing && MH.state.inCombat) combat.localSwing();
        const cmd = `webattack ${refFor(t)}`;
        lastAction = { cmd, at: now };
        MH.sendCommand(cmd, false);
        return;
      }
      // (the opening blow comes back at once as an attack event, with the class's swing)
      if (!MH.state.inCombat) { const cmd = `kill ${refFor(t)}`; lastAction = { cmd, at: performance.now() }; MH.sendCommand(cmd, 'combat'); }
    }, { pulls: !!heroAuto().ranged, ability: 'attack' });
  }
  MH.bus.on('hud.attack', attack);
  // the server refused an action for distance: close in (or step back) and retry once
  let lastAction = null, oorToast = 0;
  function approach(target, need, then) {
    const p = hero.root.position, q = target.root.position;
    const dx = p.x - q.x, dz = p.z - q.z, d = Math.hypot(dx, dz) || 1;
    const stand = Math.max(1.2, need - 0.6);
    ctl.walkTo(q.x + dx / d * stand, q.z + dz / d * stand, then);
  }
  function outOfRange(e) {
    const ref = e.dst && e.dst.m != null ? ents.list.get(`m${e.dst.m}`) : ents.targeted;
    const t = ref && ref.root ? ref : ents.targeted;
    if (!t || !t.root) return hud.toast(e.need ? `Too far — get within ${e.need} m` : 'Out of range');
    // the round's blow fell short: a melee hero closes in on its own (keys still win);
    // archers and casters keep the spot they chose and are told the range instead
    if (e.auto) {
      if (!heroAuto().ranged) { if (!ctl.keys.size && !ctl.path) approach(t, e.need || reachOf()); }
      else if (performance.now() - oorToast > 5000) { oorToast = performance.now(); hud.toast(`Out of range — get within ${e.need || reachOf()} m`); }
      return;
    }
    // an ability: walk into its reach and use it again
    if (lastAction && performance.now() - lastAction.at < 4000) {
      const retry = lastAction; lastAction = null;
      hud.toast(`Closing to ${e.need} m…`);
      approach(t, e.need || 2.5, () => MH.sendCommand(retry.cmd, 'combat'));
    } else hud.toast(`Too far — get within ${e.need} m`);
  }
  MH.bus.on('hud.flee', () => MH.sendCommand('flee'));
  MH.bus.on('hud.cameraReset', () => engine.snapNorth());
  // right-click a slot on the bar
  MH.bus.on('hud.slotMenu', ({ x, y, slot, id, name }) => ctxMenu.show(x, y, name || id, [
    { label: 'Use', run: () => hud.useAbility(id) },
    { label: 'Take off the bar', run: () => hud.unslot(slot) },
    { label: 'Spellbook (K)', run: () => hud.spellbook.toggle(true) },
  ]));
  const NO_GCD = new Set(['brace', 'sidestep', 'interrupt', 'flee', 'escape', 'evade']);
  const DOOR_SPELL_REACH = 9;     // how near a closed door must be for a door spell from the bar
  MH.bus.on('hud.ability', ab => {
    // an area spell: the key starts the aim (the same key again casts it where the circle is)
    if (ab.radius && !ab.at) {
      if (aiming && aiming.ab.id === ab.id) return castAimed();
      if (startAim(ab)) return;
    }
    const t = ents.targeted;
    // real time: skills and casts wait for the global cooldown (the bar shows its sweep)
    if (actionMode() && MH.state.inCombat && !NO_GCD.has(ab.id)) {
      const now = performance.now();
      if (clock.gcdLeft(now) > 80) return hud.flashSlot && hud.flashSlot(ab.id, 'busy');
      clock.startGcd(now);
    }
    // the hero starts the ability's own move on the key press (its recipe, abilityfx.js: the
    // clip, a leap or a blink, what gathers in the hands); the server's event then only adds
    // what flies and lands (fxdirector.js picks up where the key press left off)
    const r = combat.recipe(ab.id, myClass(), { k: ab.spell ? 'spell' : 'ability' });
    const begin = target => combat.director.prelude(r, { target: target && target.root ? target : null });
    // a heal or a blessing goes to the player you have targeted, else to yourself
    if (ab.ally) {
      begin(t && t.kind === 'player' ? t : null);
      return MH.sendCommand(abilityCommand(ab, t && t.kind === 'player' ? refFor(t) : null), 'combat');
    }
    // at a door (Block Door, Break Door): the nearest closed one, by its direction
    if (ab.door) {
      const nd = nearestDoor(DOOR_SPELL_REACH, { closedOnly: true });
      if (!nd) return hud.toast('Stand by a closed door.');
      begin(null);
      if (ctl) ctl.face(nd.at.x, nd.at.z);
      return MH.sendCommand(abilityCommand(ab, nd.dir), 'combat');
    }
    // aimed: turn to the circle, cast with its centre in the room's own metres
    if (ab.at) {
      begin(null);
      if (ctl) ctl.face(ab.at.x, ab.at.z);
      return MH.sendCommand(aimCommand(abilityCommand(ab, null), heroRoom, ab.at), 'combat');
    }
    if (ab.self || !t || t.kind !== 'mob') {
      if (!ab.self && !t) return hud.toast('No target — click a creature or press Tab.');
      // a self ability that throws something (a release of charges) throws it at your target
      begin(r.travel && t && t.kind === 'mob' ? t : null);
      return MH.sendCommand(abilityCommand(ab, null), 'combat');
    }
    inReach(t, rangeOf(ab.id, ab.spell), () => {
      begin(t);
      // the exact creature ('#12'): the server turns it into the keyword its commands know
      const cmd = abilityCommand(ab, refFor(t));
      lastAction = { cmd, at: performance.now() };
      MH.sendCommand(cmd, 'combat');
    }, { pulls: pullsOf(ab.id, ab.spell), leap: leapsOf(ab.id), ability: ab.id });
  });
  // ---- doors ----
  // Every door of the hero's room has a prompt spot (the middle of its doorway, or the
  // stairs for a trapdoor); the nearest one says what E will do (doorlogic.js). E, walking
  // into a closed door and the right-click menu all send "webdoor <room> <dir> <action>";
  // the server answers door_result and pushes the new state of both sides to everyone.
  function doorAnchorWorld(room, dir) {
    const a = doorAnchor(zone.layoutOf(room), dir, ROOM_W, ROOM_H);
    return a ? new THREE.Vector3(room.ox + a.x, 0, room.oz + a.z) : null;
  }
  function nearestDoor(maxDist, { closedOnly = false } = {}) {
    if (!heroRoom) return null;
    const p = hero.root.position;
    let best = null;
    for (const [dir, info] of Object.entries(heroRoom.doors)) {
      if (closedOnly && !info.closed) continue;
      const at = doorAnchorWorld(heroRoom, dir);
      if (!at) continue;
      const dist = Math.hypot(p.x - at.x, p.z - at.z);
      if (dist < maxDist && (!best || dist < best.dist)) best = { dir, info, at, dist };
    }
    return best;
  }
  // a way out into a death trap the hero hasn't dared, within reach: {dir, room, at, dist}
  function nearestDeadly(maxDist) {
    if (!heroRoom) return null;
    const p = hero.root.position;
    let best = null;
    for (const [dir, e] of Object.entries(heroRoom.data.exits)) {
      const to = zone.rooms.get(e.to);
      if (!zone.deadly(to)) continue;
      const at = doorAnchorWorld(heroRoom, dir) || zone.passageWorld(heroRoom, dir);
      const dist = Math.hypot(p.x - at.x, p.z - at.z);
      if (dist < maxDist && (!best || dist < best.dist)) best = { dir, room: to, at, dist };
    }
    return best;
  }
  const DEADLY_PROMPT = { key: 'E', text: 'Certain death lies beyond — go on anyway', tone: 'locked' };
  let deadlyToast = 0;
  function dareDeath(d) {
    zone.dared.add(d.room.vnum);
    hud.toast(`You steel yourself for ${d.room.data.name || 'what lies beyond'}…`);
  }
  let doorBusy = 0;
  const doorAuto = new Map();          // dir -> when we last opened it by walking into it
  function sendDoor(dir, action) {
    const now = performance.now();
    if (!heroRoom || !action || now - doorBusy < 400) return;
    doorBusy = now;
    MH.sendCommand(`webdoor ${heroRoom.vnum} ${dir} ${action}`, false);
  }
  // a door action chosen from the menu: walk up to the door first if it is out of reach
  function doDoor(dir, action) {
    const at = doorAnchorWorld(heroRoom, dir);
    const p = hero.root.position;
    if (!at || Math.hypot(p.x - at.x, p.z - at.z) < 2.6) return sendDoor(dir, action);
    const c = zone.centre(heroRoom);
    const toC = c.clone().sub(at).setY(0).normalize().multiplyScalar(1.3);
    const room = heroRoom;
    ctl.walkTo(at.x + toC.x, at.z + toC.z, () => { if (heroRoom === room) sendDoor(dir, action); });
  }
  // a door's sound when its state really changes (not when a view merely refreshes it)
  function setDoorHeard(r, dir, info) {
    const d = zone.doorOf(r, dir);
    const before = d ? { closed: d.closed, locked: d.locked } : null;
    zone.setDoor(r, dir, info);
    if (!before || !d || !heroRoom || Math.abs(r.ox - heroRoom.ox) + Math.abs(r.oz - heroRoom.oz) > 60) return false;
    const at = doorAnchorWorld(r, dir);
    if (before.closed !== d.closed) return sound.play(d.closed ? 'door_close' : 'door_open', { at });
    if (before.locked !== d.locked) return sound.play('lock', { at });
    return false;
  }
  MH.bus.on('door.update', ev => {
    // the room card's compass: a door of the room you stand in opened, shut, locked
    const cur = lastPayload && lastPayload.current_room;
    if (cur) {
      for (const d of ev.doors || []) {
        const e = d.vnum === cur.vnum && cur.exits && cur.exits[d.dir];
        if (e && e.door) Object.assign(e.door, { state: d.state, locked: d.locked, broken: d.broken });
      }
      roomCard.update(cur);
    }
    if (!zone) return;
    let heard = false;
    for (const d of ev.doors || []) {
      const r = zone.rooms.get(d.vnum);
      if (!r) continue;
      // the two sides of one door arrive together: one sound for both
      if (heard) zone.setDoor(r, d.dir, d); else heard = setDoorHeard(r, d.dir, d);
    }
  });
  MH.bus.on('door.result', res => {
    doorBusy = 0;
    if (res.ok && res.pending) { castbar.start(res.secs || 5, res.action === 'lock' ? 'Locking without a key…' : 'Picking the lock…'); return; }
    if (!res.ok && res.reason) hud.toast(res.reason);
    if (!res.ok) sound.play('ui_error');
    if (res.door && zone) { const r = zone.rooms.get(res.vnum); if (r) setDoorHeard(r, res.dir, res.door); }
  });
  MH.bus.on('env.channel', c => castbar.start(c.secs || 5, c.label || 'Working…'));
  MH.bus.on('env.channel.end', () => castbar.end());
  // E: do what the prompt says
  window.addEventListener('keydown', e => {
    if (!hero || e.repeat || /INPUT|TEXTAREA/.test(e.target.tagName)) return;
    if (aiming && e.key === 'Escape') { stopAim(); e.stopPropagation(); return; }
    // a marked blow coming: Q, E or X answer it first (reactions.js)
    const answer = react.press(e.key, performance.now());
    if (answer) { MH.sendCommand(answer); drawReact(performance.now()); e.preventDefault(); return; }
    if (e.key.toLowerCase() !== 'e') return;
    const d = nearestDoor(2.6);
    if (!d) { const dd = nearestDeadly(3.2); if (dd) dareDeath(dd); return; }
    const pr = doorPrompt(d.info);
    if (pr && pr.action) sendDoor(d.dir, pr.action);
    else if (pr) hud.toast(pr.text);
  });
  // walking into a closed door: an unlocked one opens; a locked one says why not
  function pushingDoor(room, dir, now) {
    const info = room.doors[dir];
    if (!info || !info.closed) return;
    const pr = doorPrompt(info);
    if (pr && pr.action === 'open') {
      if (now - (doorAuto.get(dir) || 0) > 2000) { doorAuto.set(dir, now); sendDoor(dir, 'open'); }
    } else if (pr && now - doorToast > 4000) {
      doorToast = now;
      hud.toast(pr.action ? `${pr.text} — press E` : pr.text);
    }
  }
  // every frame: the prompt over the nearest door, pushing into a closed doorway, and timed
  // work (picking a lock) that ends when you move
  let pushClock = 0;
  function doorTick(dt, now) {
    const p = hero.root.position;
    const near = nearestDoor(2.6);
    const speed = ctl.vel.length();
    const deadly = nearestDeadly(3.2);
    if (near && (near.info.closed || (near.dist < 1.8 && speed < 1)) && !near.info.broken) {
      const hatch = near.dir === 'up' || near.dir === 'down';
      prompt.show(near.at.clone().setY(hatch ? 1.7 : 2.8), doorPrompt(near.info));
    } else if (deadly) prompt.show(deadly.at.clone().setY(2.8), DEADLY_PROMPT);
    else prompt.hide();
    if (near && near.info.closed && near.dist < 1.2 && ctl.keys.size) {
      const w = ctl.wish();
      const dx = near.at.x - p.x, dz = near.at.z - p.z, l = Math.hypot(dx, dz) || 1;
      if ((dx * w.x + dz * w.y) / l > 0.5) { if ((pushClock += dt) > 0.25) pushingDoor(heroRoom, near.dir, now); }
      else pushClock = 0;
    } else pushClock = 0;
    if (castbar.active && (ctl.keys.size || ctl.path)) { castbar.end(); MH.sendCommand('stopwork', false); }
  }
  // ---- right-click (press and release without dragging): a menu for what is under it ----
  // (a right-drag turns the camera: input.js tells them apart)
  attachWorldInput(engine, canvas, { onContext: openContext, typing: e => /INPUT|TEXTAREA/.test((e.target || {}).tagName || '') });
  function pickAt(x, y) {
    const ent = ents.pick(x, y);
    if (ent) return { kind: ent.kind === 'player' ? 'player' : 'mob', ent };
    const item = loot.pick(x, y, canvas);
    if (item) return { kind: 'item', loot: item };
    const r = canvas.getBoundingClientRect();
    const hp = hero.root.position.clone().setY(hero.root.position.y + 1.1).project(engine.camera);
    const sx = r.left + (hp.x + 1) / 2 * r.width, sy = r.top + (1 - hp.y) / 2 * r.height;
    if (Math.hypot(x - sx, y - sy) < 36) return { kind: 'self' };
    const g = ctl.groundAt(x, y);
    if (!g) return null;
    let best = null;
    for (const [dir, info] of Object.entries(heroRoom.doors)) {
      const at = doorAnchorWorld(heroRoom, dir);
      if (!at) continue;
      const dist = Math.hypot(g.x - at.x, g.z - at.z);
      if (dist < 2 && (!best || dist < best.dist)) best = { dir, info, dist };
    }
    return best ? { kind: 'door', door: best } : { kind: 'ground', point: g };
  }
  function openContext(x, y) {
    if (!hero || !heroRoom) return;
    const hit = pickAt(x, y);
    if (!hit) return;
    menuFor(hit, x, y);
  }
  let lastMenuAt = { x: innerWidth / 2, y: innerHeight / 2 };
  function menuFor(hit, x, y) {
    lastMenuAt = { x, y };
    const p = MH.state.player || {};
    const { title, items } = verbsFor(hit, { skills: hud.targetSkills(), posture: p.position, inCombat: MH.state.inCombat,
      room: heroRoom && heroRoom.vnum, inGroup: hud.party.inGroup, mount: p.mount || null, mounts: p.mounts || [] });
    if (!items.length) return;
    ctxMenu.show(x, y, title, items.map(it => ({ label: it.label, run: (it.cmd || it.act) ? () => runVerb(hit, it) : null })));
  }
  function runVerb(hit, it) {
    if (it.cmd) return MH.sendCommand(it.cmd);
    const a = it.act;
    if (a === 'attack') { ents.setTarget(hit.ent.key, { byHand: true }); return attack(); }
    if (a === 'target') return ents.setTarget(hit.ent.key, { byHand: true });
    if (a.startsWith('ability:')) { ents.setTarget(hit.ent.key, { byHand: true }); return hud.useAbility(a.slice(8)); }
    if (a.startsWith('door:')) return doDoor(hit.door.dir, a.slice(5));
    if (a.startsWith('tell:')) return hud.whisper(a.slice(5));
    if (a === 'inventory' || a === 'character') return hud.openPanel(a);
    if (a === 'trainer') return hud.openTrainer(hit.ent.data && (hit.ent.data.short || hit.ent.data.name));
    // talking and trading happen in the same room: walk over first
    const npc = hit.ent && hit.ent.data ? (hit.ent.data.short || hit.ent.data.name) : '';
    if (a.startsWith('talk:')) return inReach(hit.ent, 3, () => hud.openTalk(npc, a.slice(5)));
    if (a.startsWith('shop:')) return inReach(hit.ent, 3, () => hud.openShop(a.slice(5)));
    if (a === 'loot' || a === 'take') return takeLoot(hit.loot);
    if (a.startsWith('give:')) return hud.giveTo(a.slice(5), lastMenuAt.x, lastMenuAt.y);
    if (a === 'walk' && hit.point) { travel = null; return ctl.walkTo(hit.point.x, hit.point.z); }
  }

  // ---- what lies on the ground: walk over, then take it (a corpse: everything in it) ----
  // (taken as soon as it is within reach: the spot itself may be hard against a wall or a pillar)
  let lootWalk = null;
  // an open loot window follows its corpse in each payload (closes when it's emptied, gone, or
  // the hero has left the room)
  function followLoot(payload) {
    if (!hud.lootwin.open || !payload) return;
    const g = groundItems(payload).find(x => x.key === hud.lootwin.key);
    hud.lootwin.follow(g && (!heroRoom || g.vnum === heroRoom.vnum) ? g : null);
  }
  const nearLoot = l => heroRoom && l.vnum === heroRoom.vnum && l.root
    && Math.hypot(l.root.position.x - hero.root.position.x, l.root.position.z - hero.root.position.z) < 1.8;
  function takeLoot(l) {
    if (!l || !hero || !l.root) return;
    // a corpse opens its loot window (hud/lootwin.js); anything else is picked up
    const go = l.corpse
      ? () => { lootWalk = null; hud.lootwin.show({ key: l.key, kw: l.kw, item: l.item }); }
      : () => { lootWalk = null; MH.sendCommand(`get ${l.kw}`); setTimeout(() => MH.refreshState && MH.refreshState(), 450); };
    if (nearLoot(l)) return go();
    travel = null;
    ctl.walkTo(l.root.position.x, l.root.position.z);
    lootWalk = { l, go, until: performance.now() + 9000 };
  }
  engine.onTick(() => {
    if (!lootWalk || !hero) return;
    if (performance.now() > lootWalk.until || !ctl.path) { if (nearLoot(lootWalk.l)) lootWalk.go(); else lootWalk = null; return; }
    if (nearLoot(lootWalk.l)) { ctl.stop(); lootWalk.go(); }
  });
  // a name in the who window: the menu a right-click on them would open
  MH.bus.on('hud.pickWho', ({ row, x, y }) => {
    const ent = row.kind === 'mob' ? ents.list.get(`m${row.id}`) : ents.list.get(`p${row.name}`);
    if (ent) menuFor({ kind: ent.kind === 'player' ? 'player' : 'mob', ent }, x, y);
  });
  // graphics quality from Settings, at once (only smoother edges wait for a reload)
  MH.bus.on('hud.quality', q => {
    if (engine.setQuality(q)) hud.toast('Smoother edges come with the next reload');
    if (heroRoom) applyFar(zone.layoutOf(heroRoom));
  });

  // ---- a marked blow coming at you: Q brace, E sidestep, X interrupt (reactions.js) ----
  const react = new ReactionPrompt();
  const reactEl = $('#react');
  let reactSig = '';
  function drawReact(now) {
    const c = react.active(now);
    const sig = c ? `${c.label}|${c.keys.join('')}|${c.used || ''}` : '';
    if (sig !== reactSig) {
      reactSig = sig;
      reactEl.classList.toggle('hidden', !c);
      if (c) reactEl.innerHTML = `<span class="rx-what">${cap(String(c.label)).replace(/[&<>"]/g, '')}!</span>`
        + c.keys.map(k => `<span class="rx-key${c.used === k ? ' used' : ''}"><kbd>${k.toUpperCase()}</kbd>${REACTIONS[k].label}</span>`).join('')
        + '<span class="rx-bar"></span>';
    }
    if (c) { const bar = reactEl.querySelector('.rx-bar'); if (bar) bar.style.transform = `scaleX(${Math.max(0, (c.until - now) / c.span).toFixed(3)})`; }
  }
  engine.onLateTick(() => drawReact(performance.now()));
  const fightsMe = src => {
    const e = src && src.m != null ? ents.list.get(`m${src.m}`) : null;
    return !!(e && ((e.data && String(e.data.fighting || '').toLowerCase() === String(MH.state.playerName || '').toLowerCase()) || ents.targeted === e));
  };
  MH.bus.on('combat.events', p => {
    if (!hero) return;
    for (const e of p.events || []) {
      if (e.k === 'windup' && threatens(e, s => combat.isHero(s), ev => fightsMe(ev.src))) react.windup(e, performance.now());
      else if ((e.k === 'resolve' || e.k === 'cancel') && e.src) react.end(e.src.m);
    }
  });

  // ---- FLANKED: two or more creatures on you at once ----
  let flankedAt = 0;
  engine.onTick(() => {
    if (!hero || !heroRoom || !MH.state.inCombat) return;
    const now = performance.now();
    if (now - flankedAt < 15000) return;
    const me = String(MH.state.playerName || '').toLowerCase();
    const on = [...ents.list.values()].filter(e => e.kind === 'mob' && e.vnum === heroRoom.vnum && e.data && String(e.data.fighting || '').toLowerCase() === me);
    if (on.length >= 2) { flankedAt = now; hud.toast(`Flanked: ${on.length} foes on you — back off so they come one at a time`); }
  });

  // ---- auto-target: whatever attacks you becomes your target (targeting.js decides when) ----
  const pendingAggro = new Map();      // creature id -> when it hit us before it was drawn
  let aggroRefresh = 0;
  function aggro(id) {
    const now = Date.now();
    const e = ents.list.get(`m${id}`);
    if (!e) {
      pendingAggro.set(id, now);
      if (now - aggroRefresh > 1500 && MH.refreshState) { aggroRefresh = now; MH.refreshState(); }
      return;
    }
    const fresh = !e.aggroAt || now - e.aggroAt > 20000;
    e.aggroAt = now;
    ents.markHostile(e);
    if (fresh) notice(e);
    if (heroRoom && shouldRetarget(ents.targeted, e, heroRoom.vnum, now)) ents.setTarget(e.key);
  }
  function applyPendingAggro() {
    const now = Date.now();
    for (const [id, at] of pendingAggro) {
      const e = ents.list.get(`m${id}`);
      if (e) {
        pendingAggro.delete(id);
        e.aggroAt = at;
        if (heroRoom && shouldRetarget(ents.targeted, e, heroRoom.vnum, now)) ents.setTarget(e.key);
      } else if (now - at > 10000) pendingAggro.delete(id);
    }
  }

  // ---- in a fight: keep a target, close in for melee, show the distance ----
  let chaseClock = 0;
  function fightTick(dt) {
    const p = hero.root.position;
    let t = ents.targeted;
    // your target died or vanished: the creature that hit you last takes its place
    if (heroRoom && (!t || (t.data && t.data.maxHp && t.data.hp <= 0))) {
      const next = retargetOnDeath(ents.list.values(), heroRoom.vnum);
      if (next && next !== t) { ents.setTarget(next.key); t = next; }
    }
    if (MH.state.inCombat && (!t || !t.root)) {
      // whoever is fighting you becomes your target
      const foe = [...ents.list.values()].filter(e => e.kind === 'mob' && e.root && e.data.fighting && e.vnum === (heroRoom && heroRoom.vnum))
        .sort((a, b) => a.root.position.distanceTo(p) - b.root.position.distanceTo(p))[0];
      if (foe) { ents.setTarget(foe.key); t = foe; }
    }
    const dist = t && t.root ? Math.hypot(t.root.position.x - p.x, t.root.position.z - p.z) : null;
    const sameRoom = !!(t && t.vnum === (heroRoom && heroRoom.vnum));
    // (in the next room across an open way: what strikes from afar reaches it from here, reach.py)
    hud.setDistance(dist, sameRoom, { across: !!(t && !sameRoom && reachAcross(t, 1e9, true)),
      leap: !!(t && !sameRoom && reachAcross(t, 1e9, false, true)), ranged: !!heroAuto().ranged });
    if ((chaseClock -= dt) > 0 || !MH.state.inCombat || !t || !t.root || t.kind !== 'mob') return;
    chaseClock = 0.4;
    const reach = reachOf();
    const ranged = heroAuto().ranged;
    // melee heroes follow a foe that steps away; archers and casters hold their ground
    if (!ranged && dist > reach + 0.3 && !ctl.keys.size && !ctl.path && t.vnum === heroRoom.vnum) approach(t, reach);
  }

  // ---- positions for the server's range rules (combat_range.py) ----
  // the hero's spot in its room ~5x a second in a fight (2x otherwise, only when it
  // changes), and once per room the spots where this client placed the creatures
  let posClock = 0, lastPos = '', seeded = '';
  function reportPositions(dt) {
    const sock = MH.state.mapSocket;
    if ((posClock -= dt) > 0 || !heroRoom || !sock || sock.readyState !== 1) return;
    posClock = 0.2;                 // (sent only when it changes; other players see you move from it)
    const p = hero.root.position;
    const x = +(p.x - heroRoom.ox).toFixed(2), z = +(p.z - heroRoom.oz).toFixed(2);
    const key = `${heroRoom.vnum}:${x}:${z}`;
    if (key !== lastPos) { lastPos = key; sock.send(JSON.stringify({ type: 'pos', vnum: heroRoom.vnum, x, z })); }
    const mobs = [...ents.list.values()].filter(e => e.kind === 'mob' && e.vnum === heroRoom.vnum && e.root && e.data.id != null)
      .map(e => ({ id: e.data.id, x: +(e.root.position.x - heroRoom.ox).toFixed(2), z: +(e.root.position.z - heroRoom.oz).toFixed(2) }));
    const mk = `${heroRoom.vnum}:${mobs.map(m => m.id).join(',')}`;
    if (mobs.length && mk !== seeded) { seeded = mk; sock.send(JSON.stringify({ type: 'mobpos', vnum: heroRoom.vnum, mobs })); }
  }

  // footsteps: one every stride (longer when running), by what is underfoot
  function footsteps(dt, p) {
    const v = hop || climb || slide ? 0 : ctl.vel.length();
    if (v < 0.6) { stride = Math.min(stride, 0.4); return; }
    stride += v * dt;
    const len = riding ? 1.25 : v > 3.2 ? 1.6 : 0.95;
    if (stride < len) return;
    stride = 0;
    const wet = heroRoom && zone.tile(heroRoom, p.x, p.z) === WATER_TILE;
    // wading leaves rings on the water; snow and sand (and fresh snow falling) keep footprints
    if (wet && !riding) sky.ripples.spawn(p.x, WATER_Y, p.z, { size: 0.9, life: 1.1, opacity: 0.5 });
    else if (!wet && !riding) {
      // tracks covered (stealth.py): no prints, only a faint brush of dust at the heel
      const covered = ((MH.state.player && MH.state.player.wards) || []).includes('tracks_covered');
      const snowy = skyTheme === 'snow' || stepSurface === 'step_snow' || (skyOpen && sky.kind === 'snow');
      if (covered) fx.p.emit(new THREE.Vector3(p.x, 0.12, p.z), { count: 2, color: snowy ? 0xe8eef6 : 0xb8a888, bright: 0.6, speed: 0.35, up: 0.15, life: 0.6, size: 0.25, grow: 0.5, drag: 2 });
      else if (snowy || skyTheme === 'desert' || skyTheme === 'shore') sky.prints.step(p.x, 0, p.z, hero.root.rotation.y, snowy ? 'snow' : 'sand');
    }
    // a mount's hooves clop; feet patter
    sound.play(wet ? 'step_water' : riding ? 'wood' : stepSurface, { vol: riding ? 0.4 : v > 3.2 ? 1 : 0.7 });
  }

  // ---- the frame ----
  engine.onTick((dt, t) => {
    // behind the title screen the view drifts slowly over the hollow
    if (!hero) { if (backdrop) { backdrop.update(dt, t); engine.rig.yaw = Math.sin(t * 0.045) * 0.5; } return; }
    const now = performance.now();
    if (climb) {
      // stepping onto stairs before a hop, or off them after one
      climb.t = Math.min(1, climb.t + dt / climb.dur);
      const k = 1 - Math.pow(1 - climb.t, 2);
      hero.root.position.lerpVectors(climb.from, climb.to, k);
      if (climb.t >= 1) { if (!hop) hero.root.position.y = 0; climb = null; }
    } else if (slide) {
      slide.t = Math.min(1, slide.t + dt / 0.3);
      const k = 1 - Math.pow(1 - slide.t, 3);
      hero.root.position.lerpVectors(slide.from, slide.to, k);
      if (slide.t >= 1) { setHeroRoom(slide.room); slide = null; }
    } else if (!hop) {
      ctl.update(dt);
    }
    const p = hero.root.position;
    engine.rig.target.set(p.x, 0, p.z);
    footsteps(dt, p);
    zone.update(dt, t, p, ctl.vel);
    hero.update(dt);
    if (raft && raft.parent) raft.userData.bob(t);
    if (riding) { const moving = ctl.vel.lengthSq() > 0.06; riding.steed.update(dt, moving, ctl.vel.length() / 2.4); riding.pose(t, moving); }
    if (travel && (ctl.keys.size || MH.state.inCombat)) travel = null;
    // stepping on or off stairs, sliding and hopping count as moving: only standing still
    // after you have arrived wakes the stairs beside you
    if (climb || slide || hop || ctl.keys.size || ctl.path || ctl.vel.lengthSq() > 0.04) lastActive = now;
    if (!slide && !hop && !climb && heroRoom) {
      // (mid-leap the server already has the hero in the room being leapt into)
      const r = ctl.dashing ? heroRoom : zone.roomAt(p.x, p.z);
      if (r && r !== heroRoom) heroWalkedInto(heroRoom, r);
      // a click path's passage counts only in the room it belongs to
      const goal = ctl.goal && ctl.goal.room === heroRoom.vnum ? ctl.goal.dir : null;
      gate.update(heroSpots, { x: p.x - heroRoom.ox, z: p.z - heroRoom.oz }, { idleMs: now - lastActive, goal });
      const ps = zone.passageAt(heroRoom, p, ctl.vel, gate,
        { viaKeys: ctl.keys.size > 0, viaPath: !!ctl.path, goal, now });
      if (ps && !ps.blocked) startHop(ps);
      else if (ps && ps.blocked === 'door') pushingDoor(heroRoom, ps.dir, now);
      else if (ps && ps.blocked === 'deadly' && now - deadlyToast > 3000) {
        deadlyToast = now;
        hud.toast('Certain death lies beyond. Press E to go on anyway.');
      }
      doorTick(dt, now);
    } else prompt.hide();
    castbar.update();
    if (hop && !hop.loading && now - hop.at > HOP_TIMEOUT_MS) {
      // no answer: give up quietly, ask the server where we are
      const h = hop; hop = null; climb = null;
      $('#vignette').style.background = '';
      hero.root.position.y = 0;
      if (heroRoom) slide = { from: hero.root.position.clone(), to: zone.side(heroRoom, h.dir), t: 0, room: heroRoom };
      gate.disarm(h.dir);
      if (MH.refreshState) MH.refreshState();
      hud.toast("The way didn't open.");
    }
    ents.update(dt, t, p);
    adorn.update(dt, t, hero, ents.dressed());
    wards.update(dt, t, hero, (MH.state.player && MH.state.player.wards) || [], ents.warded());
    fightTick(dt);
    sync.tick();
    reportPositions(dt);
  });
  // overlays once the camera is placed for this frame (nothing lags while it turns)
  engine.onLateTick(() => {
    if (!hero) return;
    const p = hero.root.position;
    cutout.update(engine.camera, p);
    ents.layoutPlates(p);
    prompt.update(engine.camera, canvas);
    mm.update(p, ctl.yaw, engine.rig.yaw);
    ambient.update();
  });
}
