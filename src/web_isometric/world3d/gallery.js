// /play?gallery=dungeon|nature — every model of a kit in a row, for checking art and
// scale with the game camera. A development page, not part of the game.
import * as THREE from 'three';
import { trs, spawnMob, mobIndexReady } from './assets.js';
import { creatureLook } from './looks.js';
import { spawnLook } from './entities.js';

export function showGallery(engine, kit, scale = 1) {
  const only = new URLSearchParams(location.search).get('only');
  const names = [...kit.keys()].filter(n => !only || only.split(',').some(o => n.includes(o)));
  const cols = 8, step = 5;
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(cols * step + 6, Math.ceil(names.length / cols) * step + 6),
    new THREE.MeshStandardMaterial({ color: 0x6d6a60, roughness: 1 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(cols * step / 2 - step / 2, 0, Math.ceil(names.length / cols) * step / 2 - step / 2);
  floor.receiveShadow = true;
  engine.scene.add(floor);
  names.forEach((n, i) => {
    const m = kit.get(n);
    for (const p of m.parts) {
      const mesh = new THREE.Mesh(p.geometry, p.material);
      mesh.applyMatrix4(trs((i % cols) * step, 0, Math.floor(i / cols) * step, 0, scale));
      mesh.castShadow = mesh.receiveShadow = true;
      engine.scene.add(mesh);
    }
  });
  names.forEach((n, i) => engine.scene.add(new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1),
    new THREE.Vector3((i % cols) * step, 0.05, Math.floor(i / cols) * step), 2.2, 0xff3030, 0.5, 0.3)));
  console.log('gallery order:', names.join(', '));
  engine.setMood('day', true);
  return new THREE.Vector3(cols * step / 2, 0, step * 1.5);
}

// every creature model in a row, each with an arrow along +Z (the way actors face)
export async function showMobGallery(engine) {
  const index = await mobIndexReady();
  const only = new URLSearchParams(location.search).get('only');
  const names = Object.keys(index).sort().filter(n => !only || only.split(',').includes(n));
  const cols = Math.min(8, names.length), step = 4;
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(cols * step + 6, Math.ceil(names.length / cols) * step + 6),
    new THREE.MeshStandardMaterial({ color: 0x6d6a60, roughness: 1 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(cols * step / 2 - step / 2, 0, Math.ceil(names.length / cols) * step / 2 - step / 2);
  floor.receiveShadow = true;
  engine.scene.add(floor);
  const actors = [];
  for (let i = 0; i < names.length; i++) {
    const a = await spawnMob(names[i], { height: 1.4 });
    const x = (i % cols) * step, z = Math.floor(i / cols) * step;
    a.root.position.set(x, 0, z);
    a.play('Idle', 0);
    engine.scene.add(a.root);
    engine.scene.add(new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1), new THREE.Vector3(x, 0.05, z), 1.6, 0xff3030, 0.4, 0.25));
    actors.push(a);
  }
  engine.onTick(dt => actors.forEach(a => a.update(dt)));
  console.log('mob gallery order:', names.join(', '));
  engine.setMood('day', true);
  return new THREE.Vector3(cols * step / 2, 0, step * 1.5);
}

// creatures at their in-game sizes beside a knight, from descriptions the MUD uses (each
// through looks.js, exactly as the game picks them), labelled
const SAMPLES = ['the green gelatinous blob', 'the giant hornet', 'the goat herder', 'a goblin mushroom farmer', 'the Spider Queen',
  'the mimic', 'the Book Monster', 'the dancing sword', 'the magic carpet', 'the broom', 'the stone golem', 'the statue of Indra',
  'a fire elemental', 'the djinn', 'A tiny pixie', 'the sea hag', 'the merman', 'a lizard man', 'the baker', 'the cityguard',
  "the mages' guildmaster", 'an orc shaman', 'a skeletal warrior', 'a rotting zombie', 'an ancient lich', 'a vampire spawn',
  'the Black Rook', 'the White Bishop', 'a possessed suit of armor', 'the red dragon', 'the baby dragon', 'a black bear',
  'the large, grey wolf', 'the giant earth beetle', 'a sewer crocodile', 'the dragon turtle', 'a hell hound', 'the ancient tree',
  'the myconoid', 'a ghostly mermaid', { short: 'the Sewer King', long: 'A massive rat-man standing here.', boss: true }];

// the creature kit (kin.js): world creatures on their own bodies, /play?gallery=kin
export const KIN_SAMPLES = ['a lean grey wolf', 'a black dire wolf', 'a tawny prairie wolf', 'a frost wolf', 'a badland jackal',
  'a red fox', 'an arctic fox', 'a feral hound', 'a mountain lion', 'a white stag', 'a great red stag', 'a golden stag',
  'a dun wild horse', 'a shaggy aurochs bull', 'a shaggy mountain goat', 'a bristly wild boar', 'a grizzled badger',
  'a big brown bear', 'a moss-backed owlbear', 'a great cave bear', 'a brown field hare', 'a white snow hare', 'a sewer rat',
  'a giant lizard', 'a grey heron', 'a grey harbour gull', 'a carrion crow', 'a giant raven', 'a snow owl', 'a mountain hawk',
  'a crested penguin', 'a vampire bat', 'a chicken', 'a blue shark', 'a great hammerhead shark', 'a grey seal',
  'a killer whale', 'a flying fish', 'a speckled trout',
  'a hill troll', 'a frost troll', 'a wandering ogre', 'a hill giant', 'the minotaur', 'an ettin', 'a goblin scout', 'a kobold scavenger',
  'a red demon', 'a cackling imp', 'the pit fiend', 'a yeti', 'an earth elemental',
  'a giant web spider', 'a grey rock spider', 'a scarab beetle', 'a black scorpion', 'a green shore crab', 'a snapping turtle',
  'a giant hornet', 'a dusk moth', 'a banded sea snake', 'a spitting cobra', 'a horned viper', 'a swamp hydra', 'a giant worm',
  'a giant centipede', 'a great sea serpent', 'a red dragon', 'a rock wyvern', 'the dracolich', 'a green dragon whelp',
  'a hollow-eyed shade', 'a restless spirit', 'a fire elemental', 'an ice elemental', 'the djinn', 'a wailing banshee', 'a will-o-wisp',
  'a green slime', 'a grey ooze', 'a giant river frog', 'a pale moon jellyfish', 'a giant clam', 'a gelatinous cube',
  'a desert camel', 'a wererat', 'the ixitxachitl', 'a fluffy duckling'];

export async function showBeastGallery(engine, kits, samples = SAMPLES) {
  const q = new URLSearchParams(location.search), only = q.get('only');
  // &add=a goblin,the vampire bat: more descriptions to show (&add alone, with &only=, to see just those)
  const add = (q.get('add') || '').split(',').map(s => s.trim()).filter(Boolean);
  const list = [{ short: 'the knight (hero)' }, ...[...samples, ...add].map(s => typeof s === 'string' ? { short: s } : s)]
    .filter(m => !only || only.split(',').some(o => m.short.toLowerCase().includes(o)));
  const cols = 10, step = 3.2, rows = Math.ceil(list.length / cols);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(cols * step + 6, rows * step * 1.4 + 6), new THREE.MeshStandardMaterial({ color: 0x6f7a5a, roughness: 1 }));
  floor.rotation.x = -Math.PI / 2; floor.position.set((cols - 1) * step / 2, 0, (rows - 1) * step * 0.7); floor.receiveShadow = true;
  engine.scene.add(floor);
  const actors = [], labels = [];
  for (let i = 0; i < list.length; i++) {
    const m = list[i], x = (i % cols) * step, z = Math.floor(i / cols) * step * 1.4;
    const look = i === 0 ? { model: 'knight' } : creatureLook({ ...m, pv: i });
    const a = await spawnLook(look, { kits, seed: i });
    const fly = look.beast ? look.beast.fly : look.fly;
    a.root.position.set(x, fly || 0, z);
    a.play('Idle', 0, look.still ? 0 : 1);
    engine.scene.add(a.root);
    actors.push(a);
    const el = document.createElement('div');
    el.textContent = m.short;
    el.style.cssText = 'position:fixed;left:0;top:0;font:11px sans-serif;color:#fff;background:#0008;padding:1px 4px;border-radius:3px;pointer-events:none;white-space:nowrap;z-index:50';
    document.body.appendChild(el);
    labels.push({ el, at: new THREE.Vector3(x, -0.2, z + 0.9) });
  }
  const v = new THREE.Vector3();
  engine.onTick(dt => {
    actors.forEach(a => a.update(dt));
    const cv = engine.renderer.domElement.getBoundingClientRect();
    for (const l of labels) {
      v.copy(l.at).project(engine.camera);
      l.el.style.display = v.z > 1 ? 'none' : '';
      l.el.style.transform = `translate(${(cv.left + (v.x + 1) / 2 * cv.width).toFixed(0)}px, ${(cv.top + (1 - v.y) / 2 * cv.height).toFixed(0)}px) translate(-50%, 0)`;
    }
  });
  console.log('beast gallery:', list.map(m => m.short).join(', '));
  engine.setMood('day', true);
  return new THREE.Vector3((cols - 1) * step / 2, 0, (rows - 1) * step * 0.6);
}

// /play?demo&gallery=abilities&cls=mage[&only=fireball,frost][&speed=0.5][&manual] — a class's
// whole book played in turn by its hero on training dummies, labelled with each recipe line
// (abilityfx-table.js). ← → step, space pauses. `manual` stops the clock for screenshots
// (MH3D.gallery.play(i), then engine.step()): tests/web/probe_play3d.js abilityfx.
export async function showAbilityGallery(engine) {
  const q = new URLSearchParams(location.search);
  const cls = (q.get('cls') || 'mage').toLowerCase();
  const only = q.get('only');
  const [{ FX }, { Director }, { RECIPES }, { recipeFor, timeline }, { spawnCharacter }, { classModel }] = await Promise.all([
    import('./fx.js'), import('./fxdirector.js'), import('./abilityfx-table.js'), import('./abilityfx.js'), import('./assets.js'), import('./entities.js')]);
  engine.timeScale = Number(q.get('speed')) || 1;
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 30), new THREE.MeshStandardMaterial({ color: 0x4a4740, roughness: 1 }));
  floor.rotation.x = -Math.PI / 2; floor.position.set(3.5, 0, 0); floor.receiveShadow = true;
  engine.scene.add(floor);
  const fx = new FX(engine, document.querySelector('#fct'));
  const body = async (model, opts, x, z, yaw) => {
    const a = await spawnCharacter(model, opts);
    a.root.position.set(x, 0, z); a.root.rotation.y = yaw;
    a.play('Idle', 0);
    engine.scene.add(a.root);
    return a;
  };
  const look = classModel(cls);
  const hero = await body(look.model, { tint: look.tint }, 0, 0, Math.PI / 2);
  const dummy = await body('knight', { flat: true, tint: 0x8a7a64 }, 7, 0, -Math.PI / 2);
  const left = await body('knight', { flat: true, tint: 0x7a6e5c }, 8.6, -2.4, -Math.PI / 2);
  const right = await body('knight', { flat: true, tint: 0x7a6e5c }, 8.6, 2.4, -Math.PI / 2);
  const ally = await body('knight', { tint: 0xd0e0ff }, -1.6, 2.6, Math.PI / 2);
  const actors = [hero, dummy, left, right, ally];
  const who = (a, mob = true) => ({ actor: a, root: a.root, mob, cls: a === hero ? cls : null });
  const director = new Director({ fx, engine, getHero: () => null, chest: w => w.root.position.clone().setY(w.root.position.y + 1.15) });
  let book = [];
  try { book = (await (await fetch(`/abilitybook?cls=${cls}`)).json()).abilities || []; } catch (_) { book = []; }
  const aimOf = id => { const b = book.find(a => a.id === id); return b ? b.target || 'enemy' : (RECIPES[cls][id].includes('ally') ? 'ally' : 'enemy'); };
  const nameOf = id => (book.find(a => a.id === id) || {}).name || id.replace(/_/g, ' ');
  const ids = Object.keys(RECIPES[cls] || {}).filter(id => !only || only.split(',').some(o => id.includes(o)))
    .filter(id => !(book.find(a => a.id === id) || {}).passive);
  const label = document.createElement('div');
  label.style.cssText = 'position:fixed;left:50%;top:14px;transform:translateX(-50%);font:600 18px Georgia,serif;color:#fff;background:#000b;padding:6px 14px;border-radius:6px;z-index:60;text-align:center;white-space:nowrap';
  document.body.appendChild(label);
  let i = -1, wait = 0, paused = false;
  function play(n) {
    i = ((n % ids.length) + ids.length) % ids.length;
    const id = ids[i], aim = aimOf(id);
    const r = recipeFor(RECIPES, id, cls, {});
    hero.root.position.set(0, 0, 0); hero.root.rotation.y = Math.PI / 2;
    const dst = aim === 'enemy' ? who(dummy) : aim === 'ally' ? who(ally, false) : null;
    const shape = aim === 'self' || aim === 'object' || aim === 'special' ? 'self' : aim === 'area' || aim === 'group' ? `nova:${r.radius || 6}` : 'ranged';
    const hits = aim === 'enemy' || aim === 'area' ? [who(left), who(right)] : [];
    director.play(r, { src: who(hero, false), dst, hits, e: { shape }, onLand: () => {
      for (const d of aim === 'enemy' ? [dummy, ...(r.land && ['nova', 'quake', 'blast'].includes(r.land.kind) ? [left, right] : [])] : aim === 'area' ? [left, right, dummy] : []) d.once('Hit_A', 0.05, 1.2);
    } });
    label.innerHTML = `<b>${i + 1}/${ids.length} · ${nameOf(id)}</b> <span style="font:12px monospace;color:#cde">${cls} · ${aim}<br>${RECIPES[cls][id]}</span>`;
    wait = Math.max(2.4, timeline(r, 7).end + 1.4);
    return { id, aim, land: timeline(r, aim === 'enemy' ? 7 : 0).land };
  }
  addEventListener('keydown', e => {
    if (e.key === 'ArrowRight') play(i + 1);
    else if (e.key === 'ArrowLeft') play(i - 1);
    else if (e.key === ' ') paused = !paused;
  });
  const manual = q.has('manual');
  engine.onTick(dt => {
    actors.forEach(a => a.update(dt));
    if (manual || paused) return;
    if ((wait -= dt) <= 0) play(i + 1);
  });
  if (manual) engine.setManual(true);
  engine.setMood('night', true);
  window.MH3D_gallery = { cls, ids, play, fx, director };
  console.log(`ability gallery: ${cls}, ${ids.length} abilities`);
  return new THREE.Vector3(3.5, 0, 0.5);
}

// /play?demo&gallery=mobfx[&jev][&only=fire,blow][&rank=normal|elite|boss][&cancel][&secs=1.6][&manual] —
// every creature ability (mobfx-hand.js; `jev`: the bosses' lines JEV drew, mobfx-table.js) wound up, let go and landed by four creatures of four
// families at once, each on a dummy of its own: its tell, its gathering power, its mark on the
// ground, its release. `cancel` breaks each wind-up instead (the interruption); ← → step, space
// pauses; `manual` stops the clock (MH3D.gallery.play(i, phase), then engine.step()).
export const MOBFX_SAMPLES = [
  { name: 'spider', short: 'a giant spider' }, { name: 'skeleton', short: 'a skeleton warrior' },
  { name: 'troll', short: 'a hulking troll' }, { name: 'shaman', short: 'a goblin shaman' },
];
export async function showMobFxGallery(engine, kits) {
  const q = new URLSearchParams(location.search);
  const only = q.get('only'), rank = q.get('rank') || 'boss', breakIt = q.has('cancel'), secs = Number(q.get('secs')) || 1.6;
  const [{ FX }, { Director }, { creatureRecipe, timeline }, { MOB_RECIPES }, { familyOf, TABLES }, { MOB_TABLE }] = await Promise.all(
    [import('./fx.js'), import('./fxdirector.js'), import('./abilityfx.js'), import('./mobfx-hand.js'), import('./mobfx.js'), import('./mobfx-table.js')]);
  const LINES = q.has('jev') ? MOB_TABLE : MOB_RECIPES;
  engine.timeScale = Number(q.get('speed')) || 1;
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(44, 30), new THREE.MeshStandardMaterial({ color: 0x4a4740, roughness: 1 }));
  floor.rotation.x = -Math.PI / 2; floor.position.set(9, 0, 0); floor.receiveShadow = true;
  engine.scene.add(floor);
  const fx = new FX(engine, document.querySelector('#fct'));
  const director = new Director({ fx, engine, getHero: () => null, chest: w => w.root.position.clone().setY(w.root.position.y + (w.ent && w.ent.plateY ? w.ent.plateY * 0.45 : 1.0)) });
  const actors = [], rows = [];
  for (let i = 0; i < MOBFX_SAMPLES.length; i++) {
    const m = MOBFX_SAMPLES[i], z = (i - 1.5) * 4.2;
    const look = creatureLook({ ...m, pv: i });
    const a = await spawnLook(look, { kits, seed: i });
    const fly = (look.beast ? look.beast.fly : look.fly) || 0;
    a.root.position.set(0, fly, z); a.root.rotation.y = Math.PI / 2;
    a.play('Idle', 0);
    engine.scene.add(a.root);
    const d = await spawnLook({ model: 'knight', flat: true, tint: 0x8a7a64 }, { kits });
    d.root.position.set(7, 0, z); d.root.rotation.y = -Math.PI / 2; d.play('Idle', 0);
    engine.scene.add(d.root);
    actors.push(a, d);
    const ent = { fly, look, data: m };
    rows.push({ src: { actor: a, root: a.root, mob: true, ent }, dst: { actor: d, root: d.root, mob: false }, family: familyOf(look, m), m });
  }
  const ids = Object.keys(LINES).filter(id => !only || only.split(',').some(o => id.includes(o)));
  const label = document.createElement('div');
  label.style.cssText = 'position:fixed;left:50%;top:14px;transform:translateX(-50%);font:600 18px Georgia,serif;color:#fff;background:#000b;padding:6px 14px;border-radius:6px;z-index:60;text-align:center;white-space:nowrap';
  document.body.appendChild(label);
  let i = -1, wait = 0, paused = false;
  const live = [];
  // phase: 'all' (wind up, then let go or break), 'charge' (only the wind-up), 'release' (only the release)
  function play(n, phase = 'all') {
    i = ((n % ids.length) + ids.length) % ids.length;
    const id = ids[i];
    for (const h of live.splice(0)) h.release();
    let end = 0;
    for (const row of rows) {
      const r = creatureRecipe(TABLES, id, row.family, {}, rank);
      const ally = r.flags.has('ally');
      const dst = ally ? row.src : row.dst;
      row.src.root.position.x = 0; row.src.root.rotation.y = Math.PI / 2;
      const go = () => director.play(r, { src: row.src, dst, hits: [], e: {}, onLand: () => { if (!ally) row.dst.actor.once('Hit_A', 0.05, 1.2); } });
      if (phase === 'release') { go(); continue; }
      const mark = fx.telegraph(dst.root.position.clone(), { radius: r.land && ['nova', 'quake'].includes(r.land.kind) ? 3.2 : 1.6, time: secs, color: breakIt ? 0xa45aff : 0xff3a28 });
      const h = director.charge(r, row.src, ally ? null : row.dst, secs, { kind: ally ? 'heal' : 'cast' });
      live.push(h);
      if (phase === 'charge') continue;
      fx.after(secs, () => {
        mark.cancel();
        if (breakIt) director.collapse(h, 'interrupt');
        else { h.release(); go(); }
      });
      end = Math.max(end, timeline(r, 7).end);
    }
    const line = LINES[id];
    label.innerHTML = `<b>${i + 1}/${ids.length} · ${id.replace(/_/g, ' ')}</b> <span style="font:12px monospace;color:#cde">${rank}${breakIt ? ' · broken' : ''} · ${rows.map(r => r.family).join(' / ')}<br>${line}</span>`;
    wait = (phase === 'all' ? secs : 0) + Math.max(2.2, end + 1.2);
    return { id, line };
  }
  addEventListener('keydown', e => {
    if (e.key === 'ArrowRight') play(i + 1);
    else if (e.key === 'ArrowLeft') play(i - 1);
    else if (e.key === ' ') paused = !paused;
  });
  const manual = q.has('manual');
  engine.onTick(dt => {
    actors.forEach(a => a.update(dt));
    if (manual || paused) return;
    if ((wait -= dt) <= 0) play(i + 1);
  });
  if (manual) engine.setManual(true);
  engine.setMood('night', true);
  window.MH3D_gallery = { ids, play, fx, director, rows };
  console.log(`mob fx gallery: ${ids.length} abilities, ${rows.map(r => `${r.m.short} (${r.family})`).join(', ')}`);
  return new THREE.Vector3(3.5, 0, 0);
}

// /play?demo&gallery=icons[&cls=mage] — every class's ability icons (hud/icons.js), labelled,
// and the menu's own icons: a development page for the painted icon set.
export async function showIconGallery() {
  const q = new URLSearchParams(location.search);
  const only = (q.get('cls') || '').toLowerCase();
  const [{ abilityIcon, uiIcon, PICTO }, { RECIPES }] = await Promise.all([import('./hud/icons.js'), import('./abilityfx-table.js')]);
  let book = {};
  const classes = Object.keys(RECIPES).filter(c => !only || c === only);
  await Promise.all(classes.map(async c => {
    try { book[c] = (await (await fetch(`/abilitybook?cls=${c}`)).json()).abilities || []; } catch (_) { book[c] = []; }
  }));
  const wrap = document.createElement('div');
  wrap.style.cssText = 'position:fixed;inset:0;overflow:auto;z-index:70;padding:18px 22px;background:radial-gradient(ellipse at 50% 0%,#1a2130,#07090e);font:13px var(--body);color:var(--ink)';
  const sec = (title, items) => `<div style="margin:0 0 18px"><div style="font:600 18px var(--title);letter-spacing:.12em;color:var(--gold-hi);text-transform:uppercase;margin:6px 0 10px">${title}</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(86px,1fr));gap:10px">${items.join('')}</div></div>`;
  const cell = (src, label) => `<div style="text-align:center"><img src="${src}" width="56" height="56" style="display:block;margin:0 auto 4px;border-radius:9px;box-shadow:0 0 0 1px #000,0 4px 10px #0008"><div style="font-size:11px;line-height:1.15;color:var(--ink-dim)">${label}</div></div>`;
  let html = '';
  for (const c of classes) {
    const ids = Object.keys(RECIPES[c]);
    html += sec(c, ids.map(id => {
      const b = (book[c] || []).find(a => a.id === id) || {};
      return cell(abilityIcon(id, c, { type: b.type || 'skill', passive: !!b.passive }), b.name || id.replace(/_/g, ' '));
    }));
  }
  if (!only) html += sec('the menu', ['helm', 'satchel', 'armor', 'book', 'scroll', 'map', 'gear', 'people', 'flee', 'sword', 'shield', 'banner'].map(n => cell(uiIcon(n, { size: 64 }), n)));
  wrap.innerHTML = html;
  document.body.appendChild(wrap);
  window.MH3D_icons = { count: wrap.querySelectorAll('img').length, picto: Object.keys(PICTO).length };
  return null;
}

// /play?demo&gallery=sounds — every sound (soundtable.js), the school stings, the ambience beds
// and the music, each a button that plays it: a listening pass for the whole set
export async function showSoundGallery() {
  const [{ sound }, T] = await Promise.all([import('./audio.js'), import('./soundtable.js')]);
  const wrap = document.createElement('div');
  wrap.style.cssText = 'position:fixed;inset:0;overflow:auto;z-index:70;padding:18px 22px;background:radial-gradient(ellipse at 50% 0%,#1a2130,#07090e);font:13px var(--body);color:var(--ink)';
  const sec = (title, items) => `<div style="margin:0 0 16px"><div style="font:600 17px var(--title);letter-spacing:.12em;color:var(--gold-hi);text-transform:uppercase;margin:6px 0 9px">${title}</div>
    <div style="display:flex;flex-wrap:wrap;gap:7px">${items.join('')}</div></div>`;
  const btn = (kind, key, label, extra = '') => `<button class="btn alt" data-k="${kind}" data-v="${key}" ${extra} style="width:auto;padding:6px 11px;margin:0;font-size:12px">${label || key}</button>`;
  const names = Object.keys(T.SOUNDS);
  const group = pre => names.filter(n => pre.some(p => n.startsWith(p)));
  const used = new Set();
  const take = list => list.filter(n => !used.has(n) && used.add(n));
  let html = `<p style="margin:0 0 12px;color:var(--ink-dim)">Click anywhere first (browsers start sound on a click). ${names.length} sounds, ${Object.keys(T.BEDS).length} ambience beds, ${T.MUSIC.length} tracks.</p>`;
  html += sec('blows and defence', take(group(['swing', 'shot', 'bolt', 'hit', 'crit', 'hurt', 'miss', 'dodge', 'parry', 'block', 'resist', 'clang'])).map(n => btn('s', n)));
  html += sec('what happens to someone', take(group(['heal', 'buff', 'debuff', 'stun', 'death', 'fall', 'hero_death', 'windup', 'resolve', 'slam', 'cancel', 'fizzle'])).map(n => btn('s', n)));
  html += sec('spells by school (charge · sting · big sting)', Object.keys(T.SCHOOLS).map(s => btn('school', s)));
  html += sec('getting about', take(group(['step', 'door', 'latch', 'lock', 'creak', 'hop', 'teleport'])).map(n => btn('s', n)));
  html += sec('the interface', take(names).map(n => btn('s', n)));
  html += sec('ambience beds', Object.keys(T.BEDS).map(b => btn('bed', b)).concat([btn('bed', '', 'stop')]));
  html += sec('music', T.MUSIC.map(m => btn('music', m)).concat([btn('music', '', 'stop')]));
  wrap.innerHTML = html;
  document.body.appendChild(wrap);
  wrap.addEventListener('click', e => {
    const b = e.target.closest('button[data-k]');
    if (!b) return;
    sound.unlock();
    const { k, v } = b.dataset;
    if (k === 's') sound.play(v);
    else if (k === 'school') {
      sound.play('charge', { school: v });
      setTimeout(() => sound.play('sting', { school: v, tier: 0 }), 500);
      setTimeout(() => sound.play('sting', { school: v, tier: 2 }), 1300);
    } else if (k === 'bed') sound.ambience(v || null);
    else if (k === 'music') { if (v) sound.playMusic(v, 1); else sound.stopMusic(1); }
  });
  window.MH3D_sounds = { sound, count: names.length, buttons: wrap.querySelectorAll('button').length };
  return null;
}

// /play?demo&gallery=gear[&only=tiers|kinds|heads|shields|capes|mixes][&cls=mage][&tier=3][&sex=female] —
// heroes dressed by equip.js: every class at tiers 0-5, each weapon kind, hat and helm on each
// head, every shield and cape, and bodies mixed by armour weight. For checking fit, seams,
// colours and the cost of a dressed hero (?perf). MH3D.gallery.actors for probes.
// what gearup puts on each class (tests/test_class_gear.py keeps it true to the server)
export const ENDGAME = {"warrior": {"v": 1, "main": {"k": "sword", "h": 2, "m": "steel", "t": 5, "lg": 99003}, "head": {"k": "horned", "m": "iron", "t": 4, "s": "warlords_battleplate"}, "body": {"w": 3, "m": "obsidian", "t": 4, "s": "warlords_battleplate"}, "arms": {"w": 3, "m": "obsidian", "t": 4, "s": "warlords_battleplate"}, "legs": {"w": 3, "m": "obsidian", "t": 4, "s": "warlords_battleplate"}, "back": {"k": "cloak", "v": "barbarian", "c": "grey", "t": 4, "s": "warlords_battleplate"}, "aura": "legendary", "set": "warlords_battleplate"}, "paladin": {"v": 1, "main": {"k": "sword", "h": 1, "m": "crystal", "t": 5, "lg": 99002}, "off": {"k": "shield", "v": "badge", "m": "gold", "t": 4, "s": "dawnward_aegis", "e": "holy"}, "head": {"k": "helm", "m": "gold", "t": 4, "s": "dawnward_aegis", "e": "holy"}, "body": {"w": 3, "m": "gold", "t": 4, "s": "dawnward_aegis", "e": "holy"}, "arms": {"w": 3, "m": "gold", "t": 4, "s": "dawnward_aegis", "e": "holy"}, "legs": {"w": 3, "m": "gold", "t": 4, "s": "dawnward_aegis", "e": "holy"}, "back": {"k": "cloak", "v": "knight", "c": "white", "t": 4, "s": "dawnward_aegis", "e": "holy"}, "aura": "legendary", "set": "dawnward_aegis"}, "cleric": {"v": 1, "main": {"k": "hammer", "h": 2, "m": "steel", "t": 5, "lg": 99016}, "off": {"k": "relic", "t": 4, "s": "radiant_choir", "e": "holy"}, "head": {"k": "hat", "v": "mitre", "c": "white", "t": 4, "s": "radiant_choir", "e": "holy"}, "body": {"w": 2, "m": "silver", "t": 4, "s": "radiant_choir", "e": "holy"}, "arms": {"w": 2, "m": "silver", "t": 4, "s": "radiant_choir", "e": "holy"}, "legs": {"w": 2, "m": "silver", "t": 4, "s": "radiant_choir", "e": "holy"}, "back": {"k": "cloak", "v": "knight", "c": "white", "t": 4, "s": "radiant_choir", "e": "holy"}, "aura": "legendary", "set": "radiant_choir"}, "ranger": {"v": 1, "main": {"k": "bow", "h": 2, "m": "wood_pale", "t": 5, "lg": 99021, "e": "holy"}, "quiver": 1, "head": {"k": "hood", "c": "green", "t": 4, "s": "wildwarden_garb", "e": "nature"}, "body": {"w": 1, "m": "leather", "t": 4, "s": "wildwarden_garb", "e": "nature"}, "arms": {"w": 1, "m": "leather", "t": 4, "s": "wildwarden_garb", "e": "nature"}, "legs": {"w": 1, "m": "leather", "t": 4, "s": "wildwarden_garb", "e": "nature"}, "back": {"k": "cloak", "v": "rogue", "c": "green", "t": 4, "s": "wildwarden_garb", "e": "nature"}, "aura": "legendary", "set": "wildwarden_garb"}, "thief": {"v": 1, "main": {"k": "sword", "h": 1, "m": "steel", "t": 5, "lg": 99017}, "head": {"k": "hat", "v": "cap", "c": "grey", "t": 4, "s": "nightblade_leathers"}, "body": {"w": 1, "m": "leather_tan", "t": 4, "s": "nightblade_leathers"}, "arms": {"w": 1, "m": "leather_tan", "t": 4, "s": "nightblade_leathers"}, "legs": {"w": 1, "m": "leather_tan", "t": 4, "s": "nightblade_leathers"}, "back": {"k": "cloak", "v": "rogue", "c": "grey", "t": 4, "s": "nightblade_leathers"}, "aura": "legendary", "set": "nightblade_leathers"}, "assassin": {"v": 1, "main": {"k": "dagger", "h": 1, "m": "steel", "m2": "wood_dark", "t": 5, "lg": 99013}, "head": {"k": "hood", "v": "masked", "c": "purple", "t": 4, "s": "black_lotus_veil"}, "body": {"w": 1, "m": "leather_black", "t": 4, "s": "black_lotus_veil"}, "arms": {"w": 0, "c": "black", "t": 4, "s": "black_lotus_veil"}, "legs": {"w": 1, "m": "leather_black", "t": 4, "s": "black_lotus_veil"}, "back": {"k": "cloak", "v": "mage", "c": "purple", "t": 4, "s": "black_lotus_veil", "e": "shadow"}, "aura": "legendary", "set": "black_lotus_veil"}, "bard": {"v": 1, "main": {"k": "sword", "h": 1, "m": "crystal", "t": 5, "lg": 99002}, "off": {"k": "instrument", "h": 1, "v": "lute", "m": "wood_dark", "m2": "obsidian", "t": 4, "s": "last_song_raiment"}, "head": {"k": "hat", "v": "brim", "c": "crimson", "t": 4, "s": "last_song_raiment"}, "body": {"w": 1, "m": "leather_red", "t": 4, "s": "last_song_raiment"}, "arms": {"w": 0, "c": "crimson", "t": 4, "s": "last_song_raiment"}, "legs": {"w": 0, "c": "crimson", "t": 4, "s": "last_song_raiment"}, "back": {"k": "cloak", "v": "rogue", "c": "crimson", "t": 4, "s": "last_song_raiment"}, "aura": "legendary", "set": "last_song_raiment"}, "mage": {"v": 1, "main": {"k": "staff", "h": 2, "v": "crystal", "m": "wood", "t": 5, "lg": 99005, "e": "arcane"}, "off": {"k": "orb", "t": 4, "s": "archmage_vestments", "e": "arcane"}, "head": {"k": "hat", "v": "wizard", "t": 4, "s": "archmage_vestments"}, "body": {"w": 0, "t": 4, "s": "archmage_vestments", "e": "arcane"}, "arms": {"w": 0, "t": 4, "s": "archmage_vestments"}, "legs": {"w": 0, "t": 4, "s": "archmage_vestments", "e": "arcane"}, "back": {"k": "cloak", "v": "mage", "t": 4, "s": "archmage_vestments", "e": "arcane"}, "aura": "legendary", "set": "archmage_vestments"}, "necromancer": {"v": 1, "main": {"k": "scythe", "h": 2, "m": "bone", "m2": "wood_pale", "t": 5, "lg": 99004}, "off": {"k": "skull", "t": 4, "s": "lichlord_shroud", "e": "frost"}, "head": {"k": "hood", "c": "black", "t": 4, "s": "lichlord_shroud"}, "body": {"w": 0, "c": "black", "t": 4, "s": "lichlord_shroud", "e": "frost"}, "arms": {"w": 0, "c": "black", "t": 4, "s": "lichlord_shroud", "e": "frost"}, "legs": {"w": 0, "c": "black", "t": 4, "s": "lichlord_shroud"}, "back": {"k": "cloak", "v": "mage", "c": "black", "t": 4, "s": "lichlord_shroud", "e": "frost"}, "aura": "legendary", "set": "lichlord_shroud"}};

export async function showGearGallery(engine) {
  const q = new URLSearchParams(location.search);
  const only = q.get('only'), onlyCls = q.get('cls'), onlyTier = q.get('tier'), sex = q.get('sex'), style = q.get('style');
  const [{ spawnDressed }, { starterLook, CLASS_BASE }, { FX }, { Adorn }] = await Promise.all([import('./equip.js'), import('./gearlook.js'), import('./fx.js'), import('./adorn.js')]);
  const CLASSES = Object.keys(CLASS_BASE).filter(c => !onlyCls || onlyCls.split(',').includes(c));
  const METAL = ['iron', 'steel', 'steel', 'gold', 'mithril', 'gold'];
  const LEATHER = ['leather', 'leather', 'leather_dark', 'leather_red', 'dragonhide', 'leather_black'];
  const CAPE = { warrior: 'barbarian', paladin: 'knight', cleric: 'knight', mage: 'mage', necromancer: 'mage', thief: 'rogue', assassin: 'rogue', ranger: 'rogue', bard: 'rogue' };
  const HEAD = { warrior: 'horned', paladin: 'helm', cleric: 'helm', mage: 'hat', necromancer: 'hood', thief: 'hood', assassin: 'hood', ranger: 'hood', bard: 'hat' };
  // a class's gear at a tier: better materials, colours, a cloak and a head piece as it rises
  const tierLook = (cls, t) => {
    const look = JSON.parse(JSON.stringify(starterLook(cls)));
    for (const k of ['main', 'off', 'head', 'body', 'arms', 'legs', 'back']) {
      const p = look[k];
      if (!p) continue;
      p.t = t;
      if (p.m && /iron|steel/.test(p.m)) p.m = METAL[t];
      else if (p.m && /leather/.test(p.m)) p.m = LEATHER[t];
    }
    if (t >= 2 && !look.back) look.back = { k: 'cloak', v: CAPE[cls], t };
    if (t >= 3 && !look.head) look.head = HEAD[cls] === 'hood' || HEAD[cls] === 'hat' ? { k: HEAD[cls], t } : { k: HEAD[cls], m: METAL[t], t };
    if (t >= 4 && look.main) look.main.e = t === 5 ? 'holy' : 'frost';
    if (t === 5) { for (const k of ['body', 'back']) if (look[k]) look[k].s = 'frostlords_mantle'; if (look.main) look.main.lg = 99001; look.aura = 'legendary'; }
    if (sex) look.sex = sex;
    if (style) look.style = style;              // ?style=archmage: a mage's chosen look
    look.sig = `gallery:${cls}:${t}:${sex || ''}:${style || ''}`;
    return look;
  };
  const rows = [];
  const want = s => !only || only.split(',').includes(s);
  if (want('tiers')) for (const cls of CLASSES) rows.push({ title: cls, items: [0, 1, 2, 3, 4, 5].filter(t => onlyTier == null || +onlyTier === t).map(t => ({ label: `${cls} t${t}`, cls, look: tierLook(cls, t) })) });
  const kindsOf = (k, h = 1) => ({ k, h, m: 'steel', t: 2 });
  if (want('kinds')) rows.push({ title: 'kinds', items: [['sword', 1], ['sword', 2], ['axe', 1], ['axe', 2], ['dagger', 1], ['mace', 1], ['hammer', 1], ['hammer', 2], ['bow', 2], ['crossbow', 1], ['crossbow', 2], ['staff', 2], ['wand', 1], ['spear', 2], ['polearm', 2], ['scythe', 2], ['pick', 1], ['whip', 1], ['claw', 1], ['thrown', 1]]
    .map(([k, h]) => ({ label: `${k}${h === 2 ? ' 2h' : ''}`, cls: 'paladin', look: { v: 1, sig: `kind:${k}:${h}`, main: k === 'bow' || k === 'staff' ? { k, h, m: 'wood', t: 2 } : kindsOf(k, h), body: { w: 2, m: 'steel', t: 2 } } })) });
  // held in the off hand: focuses, lights and instruments
  if (want('held')) rows.push({ title: 'held', items: [['orb'], ['censer'], ['lantern'], ['torch'], ['instrument', 'lute'], ['instrument', 'lyre'], ['instrument', 'harp'], ['instrument', 'flute'], ['instrument', 'drum'], ['instrument', 'horn'], ['book']]
    .map(([k, v]) => ({ label: v || k, cls: 'bard', look: { v: 1, sig: `held:${k}:${v}`, main: kindsOf('sword'), off: { k, v, h: 1, m: 'wood', m2: 'brass', t: 3 }, body: { w: 1, m: 'leather', t: 2 } } }))
    .concat(['lantern', 'torch'].map(k => ({ label: `${k} (light)`, cls: 'bard', look: { v: 1, sig: `light:${k}`, main: kindsOf('sword'), light: { k }, body: { w: 1, m: 'leather', t: 2 } } }))) });
  // renown: one class at each band (level 10 a cloak, 20 its emblem, 35 a mantle, 45 motes, prestige)
  if (want('renown')) for (const cls of (onlyCls ? CLASSES : ['warrior', 'mage', 'ranger'])) {
    rows.push({ title: `renown ${cls}`, items: [0, 1, 2, 3, 4, 5].map(rn => ({ label: `${cls} rn${rn}`, cls, look: { ...starterLook(cls), rn, sig: `renown:${cls}:${rn}` } })) });
  }
  // every race, in a warrior's and a mage's starting gear (skin and build), and humans' tones
  if (want('races')) for (const cls of (onlyCls ? CLASSES : ['warrior', 'mage'])) {
    rows.push({ title: `races ${cls}`, items: ['human', 'elf', 'dark_elf', 'half_orc', 'dwarf', 'halfling', 'gnome'].map(race => ({ label: `${race} ${cls}`, cls,
      look: { ...starterLook(cls), race, sig: `race:${cls}:${race}` } })).concat([0, 1, 2, 3].map(tone => ({ label: `human tone ${tone}`, cls,
      look: { ...starterLook(cls), race: 'human', tone, sig: `tone:${cls}:${tone}` } }))) });
  }
  // people their zone dressed (looks.js npcDress): the body their trade gives, their race, their gear
  if (want('people')) {
    const { creatureLook, npcDress } = await import('./looks.js');
    const P = [['the cityguard', { main: { k: 'sword', h: 1, m: 'steel', t: 1 }, off: { k: 'shield', v: 'round', m: 'iron', t: 1 } }],
      ['the dwarven smith', { main: { k: 'hammer', h: 1, m: 'iron', t: 1 }, body: { w: 1, m: 'leather', t: 1 } }],
      ['a drow assassin', { main: { k: 'dagger', h: 1, m: 'obsidian', t: 4, e: 'shadow' }, back: { k: 'cloak', v: 'rogue', c: 'black', t: 3 } }],
      ['the half-orc warrior', { main: { k: 'axe', h: 2, m: 'iron', t: 2 }, body: { w: 2, m: 'iron', t: 2 } }],
      ['the elven ranger', { main: { k: 'bow', h: 2, m: 'wood_pale', t: 3 }, quiver: 1 }],
      ['the gnome alchemist', { off: { k: 'orb', t: 2 } }],
      ['the halfling cook', { main: { k: 'dagger', h: 1, m: 'iron', t: 0 } }],
      ['the high priest', { main: { k: 'mace', h: 1, m: 'gold', t: 3 }, body: { w: 0, c: 'white', t: 3 } }],
      ['the knight templar', { main: { k: 'sword', h: 1, m: 'steel', t: 3 }, head: { k: 'helm', m: 'steel', t: 3 }, body: { w: 3, m: 'steel', t: 3 } }]];
    rows.push({ title: 'people', items: P.flatMap(([short, gear], i) => {
      const m = { name: short.split(' ').pop(), short, pv: 90000 + i, look: { v: 1, rn: 0, sig: `people:${i}`, ...gear } };
      const npc = npcDress(m, creatureLook(m));
      return npc ? [{ label: short, cls: npc.cls, look: npc.look, scale: npc.scale }] : [];
    }) });
  }
  // crowns and circlets on every head
  if (want('crowns')) rows.push({ title: 'crowns', items: ['paladin', 'warrior', 'mage', 'thief', 'ranger'].flatMap(cls => ['crown', 'circlet'].map(v => ({ label: `${v} on ${cls}`, cls,
    look: { v: 1, sig: `crown:${cls}:${v}`, head: { k: 'crown', v, m: v === 'crown' ? 'gold' : 'silver', t: 3 }, body: { w: CLASS_BASE[cls].w, m: 'steel', t: 2 } } }))) });
  if (want('heads')) rows.push({ title: 'heads', items: ['paladin', 'warrior', 'mage', 'thief'].flatMap(cls => ['helm', 'horned', 'hat', 'hood'].map(k => ({ label: `${k} on ${CLASS_BASE[cls].model}`, cls,
    look: { v: 1, sig: `head:${cls}:${k}`, head: k === 'helm' || k === 'horned' ? { k, m: 'steel', t: 2 } : { k, c: 'blue', t: 2 }, body: { w: CLASS_BASE[cls].w, m: 'steel', t: 2 } } }))) });
  if (want('shields')) rows.push({ title: 'shields', items: ['round', 'badge', 'square', 'spike'].flatMap(v => [1, 3].map(t => ({ label: `${v} t${t}`, cls: 'paladin',
    look: { v: 1, sig: `shield:${v}:${t}`, main: kindsOf('sword'), off: { k: 'shield', v, m: t > 2 ? 'gold' : 'iron', t }, body: { w: 2, m: 'steel', t: 2 } } }))) });
  if (want('capes')) rows.push({ title: 'capes', items: ['knight', 'barbarian', 'mage', 'rogue'].flatMap(v => ['red', 'black', 'set'].map(c => ({ label: `${v} ${c}`, cls: 'paladin',
    look: { v: 1, sig: `cape:${v}:${c}`, back: c === 'set' ? { k: 'cloak', v, s: 'chaos_weave', t: 3 } : { k: 'cloak', v, c, t: 2 }, body: { w: 2, m: 'steel', t: 2 } } }))) });
  // each class at the top, as gearup dresses it (class_gear.py): its own kind of gear
  if (want('endgame')) rows.push({ title: 'endgame', items: Object.entries(ENDGAME).filter(([c]) => !onlyCls || onlyCls.split(',').includes(c))
    .map(([cls, look]) => ({ label: cls, cls, look: { ...look, rn: 4, sig: `endgame:${cls}` } })) });
  // the hats and staves built in code (procgear.js): every shape, on the classes that wear them
  if (want('classgear')) rows.push({ title: 'class gear', items: [
    ...['wizard', 'brim', 'cap', 'mitre'].map((v, i) => { const cls = ['mage', 'bard', 'thief', 'cleric'][i];
      return { label: `${v} hat (${cls})`, cls, look: { ...starterLook(cls), head: { k: 'hat', v, c: ['violet', 'forest', 'brown', 'white'][i], t: 3 }, sig: `hat:${v}` } }; }),
    ...['crystal', 'skull', 'gnarled', 'plain'].map((v, i) => { const cls = ['mage', 'necromancer', 'mage', 'cleric'][i];
      return { label: `${v} staff`, cls, look: { ...starterLook(cls), main: { k: 'staff', h: 2, v, m: v === 'skull' ? 'wood_dark' : 'wood', t: 3 }, sig: `staff:${v}` } }; }),
  ] });
  if (want('mixes')) rows.push({ title: 'mixes', items: [
    { label: 'mage in plate', cls: 'mage', look: { v: 1, sig: 'mix:1', main: { k: 'staff', h: 2, m: 'wood', t: 3 }, body: { w: 3, m: 'steel', t: 3 }, legs: { w: 3, m: 'steel', t: 3 } } },
    { label: 'warrior in robes', cls: 'warrior', look: { v: 1, sig: 'mix:2', main: kindsOf('axe', 2), body: { w: 0, c: 'purple', t: 2 } } },
    { label: 'thief in plate', cls: 'thief', look: { v: 1, sig: 'mix:3', main: kindsOf('dagger'), off: kindsOf('dagger'), body: { w: 3, m: 'obsidian', t: 3 }, arms: { w: 1, m: 'leather_black', t: 3 } } },
    { label: 'paladin in leather', cls: 'paladin', look: { v: 1, sig: 'mix:4', main: kindsOf('sword'), body: { w: 0, c: 'white', t: 2 }, head: { k: 'hood', c: 'white', t: 2 } } },
    { label: 'ranger, bow', cls: 'ranger', look: { v: 1, sig: 'mix:5', main: { k: 'bow', h: 2, m: 'wood_red', t: 3 }, body: { w: 1, m: 'leather_dark', t: 3 }, quiver: 1, back: { k: 'cloak', v: 'rogue', c: 'forest', t: 3 } } },
    { label: 'bard, lute', cls: 'bard', look: { v: 1, sig: 'mix:6', main: kindsOf('sword'), off: { k: 'instrument', h: 1, m: 'wood_red', t: 3 }, body: { w: 1, m: 'leather_red', t: 3 }, head: { k: 'hat', c: 'orange', t: 3 } } },
  ] });
  const step = 3, gap = 3.8;
  const width = Math.max(...rows.map(r => r.items.length)) * step;
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(width + 8, rows.length * gap + 8), new THREE.MeshStandardMaterial({ color: 0x6f6a5f, roughness: 1 }));
  floor.rotation.x = -Math.PI / 2; floor.position.set(width / 2 - step / 2, 0, (rows.length - 1) * gap / 2); floor.receiveShadow = true;
  engine.scene.add(floor);
  const actors = [], labels = [];
  const label = (text, at, strong) => {
    const el = document.createElement('div');
    el.textContent = text;
    el.style.cssText = `position:fixed;left:0;top:0;font:${strong ? '600 13px' : '11px'} sans-serif;color:#fff;background:#000a;padding:1px 4px;border-radius:3px;pointer-events:none;white-space:nowrap;z-index:50`;
    document.body.appendChild(el);
    labels.push({ el, at });
  };
  for (let r = 0; r < rows.length; r++) {
    const z = r * gap;
    label(rows[r].title, new THREE.Vector3(-step * 1.2, 0, z), true);
    for (let i = 0; i < rows[r].items.length; i++) {
      const it = rows[r].items[i];
      const a = await spawnDressed(it.look, it.cls, { scale: it.scale });
      a.root.position.set(i * step, 0, z);
      a.play(a.idle || 'Idle', 0, 1);
      engine.scene.add(a.root);
      a.label = it.label;
      actors.push(a);
      label(it.label, new THREE.Vector3(i * step, -0.2, z + 0.9));
    }
  }
  const v = new THREE.Vector3();
  // what lingers round them (adorn.js): everyone in view is adorned here
  const fx = new FX(engine, document.body);
  const adorn = new Adorn(engine, fx);
  adorn.tier = 'gallery';
  let clock = 0;
  engine.onTick(dt => {
    clock += dt;
    actors.forEach(a => a.update(dt));
    adorn.update(dt, clock, null, actors);
    const cv = engine.renderer.domElement.getBoundingClientRect();
    for (const l of labels) {
      v.copy(l.at).project(engine.camera);
      l.el.style.display = v.z > 1 ? 'none' : '';
      l.el.style.transform = `translate(${(cv.left + (v.x + 1) / 2 * cv.width).toFixed(0)}px, ${(cv.top + (1 - v.y) / 2 * cv.height).toFixed(0)}px) translate(-50%, 0)`;
    }
  });
  window.MH3D_gallery = { actors, adorn, fx };
  engine.setMood('day', true);
  return new THREE.Vector3(width / 2 - step / 2, 0, (rows.length - 1) * gap / 2);
}

// /play?demo&gallery=corpses — the dead as loot.js lays them (corpse.js): a body of each kind
// (a model with a death clip, one without, bodies built in code, a person in their gear), darkened
// over its stain under the gold ring, and a hero's grave. MH3D.gallery.loot for probes.
export async function showCorpseGallery(engine, kits) {
  const [{ GroundLoot }, { Entities }] = await Promise.all([import('./loot.js'), import('./entities.js')]);
  const dead = ['a red dragon', 'a goblin', 'a large rat', 'the wolf', 'the cityguard', "a charred adventurer's skeleton",
    'the huge, poisonous spider', 'a giant web spider', 'a vampire bat', 'a green slime', 'Elowen'];
  const cols = 6, step = 3.4;
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(cols * step + 6, 2 * step + 8), new THREE.MeshStandardMaterial({ color: 0x6d6a60, roughness: 1 }));
  floor.rotation.x = -Math.PI / 2; floor.position.set((cols - 1) * step / 2, 0, step / 2); floor.receiveShadow = true;
  engine.scene.add(floor);
  const ents = new Entities(engine, document.createElement('div'), kits);
  const spot = i => new THREE.Vector3((i % cols) * step, 0, Math.floor(i / cols) * step);
  const keyIndex = new Map();
  const loot = new GroundLoot(engine, {
    slot: (v, key) => spot(keyIndex.get(key) || 0), icon: () => document.createElement('canvas'),
    body: (name, key) => ents.body({ name, short: name }, key), hero: name => name === 'Elowen' });
  const items = dead.map(n => ({ name: `corpse of ${n}`, short: `the corpse of ${n}`, type: 'container', contents: [], gold: 0 }));
  groundOrder(items).forEach((key, i) => keyIndex.set(key, i));
  loot.sync({ nearby: [{ vnum: 1, items }] });
  engine.onTick((dt, t) => loot.update(dt, t));
  window.MH3D_gallery = { loot };
  console.log('corpse gallery:', dead.join(', '));
  engine.setMood('day', true);
  return new THREE.Vector3((cols - 1) * step / 2, 0, step / 2);
}
// the keys loot.js gives these items (lootlogic.groundItems), in order
function groundOrder(items) {
  const seen = {};
  return items.map(it => { const base = `1:${it.name}`; seen[base] = (seen[base] || 0) + 1; return `i${base}#${seen[base]}`; });
}

// /play?demo&gallery=wards — the spells on a character while they last (wards.js): a hero for each
// ward, and a few worn together. MH3D_gallery.wards for probes.
export async function showWardGallery(engine) {
  const [{ spawnDressed }, { starterLook }, { FX }, { Wards }] = await Promise.all([import('./equip.js'), import('./gearlook.js'), import('./fx.js'), import('./wards.js')]);
  const SETS = [['shielded'], ['sanctuary'], ['divine_shield'], ['mana_shield'], ['armour_ward'], ['stoneskin'], ['ice_armor'], ['fire_shield'],
    ['barkskin'], ['fly'], ['haste'], ['regenerating'], ['prot_evil'], ['stunned'], ['bless', 'armour_ward', 'shielded', 'fly'], ['stoneskin', 'fire_shield', 'sanctuary', 'prot_good']];
  const CLS = ['mage', 'cleric', 'paladin', 'warrior', 'necromancer', 'ranger', 'thief', 'bard'];
  const cols = 8, step = 3, gap = 4;
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(cols * step + 6, 2 * gap + 8), new THREE.MeshStandardMaterial({ color: 0x6f6a5f, roughness: 1 }));
  floor.rotation.x = -Math.PI / 2; floor.position.set((cols - 1) * step / 2, 0, gap / 2); floor.receiveShadow = true;
  engine.scene.add(floor);
  const fx = new FX(engine, document.body);
  const wards = new Wards(engine, fx);
  wards.tier = 'gallery';
  const actors = [], labels = [];
  for (let i = 0; i < SETS.length; i++) {
    const cls = CLS[i % CLS.length];
    const a = await spawnDressed({ ...starterLook(cls), sig: `wards:${i}` }, cls);
    a.root.position.set((i % cols) * step, 0, Math.floor(i / cols) * gap);
    a.play(a.idle || 'Idle', 0, 1);
    engine.scene.add(a.root);
    actors.push([a, SETS[i]]);
    const el = document.createElement('div');
    el.textContent = SETS[i].join(' + ');
    el.style.cssText = 'position:fixed;left:0;top:0;font:11px sans-serif;color:#fff;background:#000a;padding:1px 4px;border-radius:3px;pointer-events:none;white-space:nowrap;z-index:50';
    document.body.appendChild(el);
    labels.push({ el, at: a.root.position.clone().setZ(a.root.position.z + 1.1).setY(-0.2) });
  }
  const v = new THREE.Vector3();
  let clock = 0;
  engine.onTick(dt => {
    clock += dt;
    for (const [a] of actors) a.update(dt);
    wards.update(dt, clock, null, [], actors);
    const cv = engine.renderer.domElement.getBoundingClientRect();
    for (const l of labels) {
      v.copy(l.at).project(engine.camera);
      l.el.style.display = v.z > 1 ? 'none' : '';
      l.el.style.transform = `translate(${(cv.left + (v.x + 1) / 2 * cv.width).toFixed(0)}px, ${(cv.top + (1 - v.y) / 2 * cv.height).toFixed(0)}px) translate(-50%, 0)`;
    }
  });
  window.MH3D_gallery = { actors, wards, fx };
  engine.setMood('day', true);
  return new THREE.Vector3((cols - 1) * step / 2, 0, gap / 2);
}

// /play?demo&gallery=bodies[&only=a,b] — the models made in Blender (tools/art3d/blender, art3d/bodies)
// at their own size beside a 1.8 m post, each playing its clips in turn (the clip's name under it).
export async function showBodyGallery(engine) {
  const { bodyIndexReady, spawnBody } = await import('./assets.js');
  const index = await bodyIndexReady();
  const only = new URLSearchParams(location.search).get('only');
  const names = Object.keys(index).sort().filter(n => !only || only.split(',').includes(n));
  const step = 4, cols = Math.max(1, Math.min(6, names.length));
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(cols * step + 8, Math.ceil(names.length / cols) * step + 8),
    new THREE.MeshStandardMaterial({ color: 0x6d6a60, roughness: 1 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.set((cols - 1) * step / 2, 0, (Math.ceil(names.length / cols) - 1) * step / 2);
  floor.receiveShadow = true;
  engine.scene.add(floor);
  const post = new THREE.Mesh(new THREE.BoxGeometry(0.08, 1.8, 0.08), new THREE.MeshStandardMaterial({ color: 0xd8c8a0 }));
  post.position.set(-1.6, 0.9, 0);
  engine.scene.add(post);
  const shown = [], labels = [];
  for (let i = 0; i < names.length; i++) {
    const a = await spawnBody(names[i]);
    a.root.position.set((i % cols) * step, 0, Math.floor(i / cols) * step);
    engine.scene.add(a.root);
    const el = document.createElement('div');
    el.style.cssText = 'position:fixed;left:0;top:0;font:11px sans-serif;color:#fff;background:#000a;padding:1px 4px;border-radius:3px;pointer-events:none;white-space:nowrap;z-index:50';
    document.body.appendChild(el);
    labels.push({ el, at: a.root.position.clone().setZ(a.root.position.z + 1.3) });
    shown.push({ a, name: names[i], clips: index[names[i]].anims || ['Idle'], at: 0, t: 0, el });
  }
  const v = new THREE.Vector3();
  const play = s => { const c = s.clips[s.at % s.clips.length]; s.a.play(c, 0.2, 1); s.el.textContent = `${s.name} · ${c}`; s.t = 0; };
  shown.forEach(play);
  engine.onTick(dt => {
    for (const s of shown) { s.a.update(dt); if ((s.t += dt) > 2.6) { s.at++; play(s); } }
    const cv = engine.renderer.domElement.getBoundingClientRect();
    for (const l of labels) {
      v.copy(l.at).project(engine.camera);
      l.el.style.display = v.z > 1 ? 'none' : '';
      l.el.style.transform = `translate(${(cv.left + (v.x + 1) / 2 * cv.width).toFixed(0)}px, ${(cv.top + (1 - v.y) / 2 * cv.height).toFixed(0)}px) translate(-50%, 0)`;
    }
  });
  window.MH3D_gallery = { bodies: shown };
  console.log('body gallery:', names.join(', '));
  engine.setMood('day', true);
  return new THREE.Vector3((cols - 1) * step / 2, 0, (Math.ceil(names.length / cols) - 1) * step / 2);
}
