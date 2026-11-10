// The spells on a character, shown while they last (world3d/wards.js), and one buff icon a spell
// (hud/buffs.js).   node --test tests/web/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { readFileSync } from 'node:fs';
import { register } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const THREE_URL = pathToFileURL(path.join(HERE, '../../src/web_isometric/vendor/three/three.module.min.js')).href;
register('data:text/javascript,' + encodeURIComponent(
  `export async function resolve(s, c, next) { return s === 'three' ? { url: ${JSON.stringify(THREE_URL)}, shortCircuit: true } : next(s, c); }`));
const THREE = await import('three');
const { WARDS, wardPlan, planKey, Wards, HAZE } = await import('../../src/web_isometric/world3d/wards.js');
const { HARMS, emitHarms } = await import('../../src/web_isometric/world3d/harms.js');
const { buffList, auraBase, plateAuras } = await import('../../src/web_isometric/world3d/hud/buffs.js');

test('a plan: the strongest shell, two orbits at most, a ring, motes, flying', () => {
  const p = wardPlan(['shielded', 'sanctuary', 'stoneskin', 'fire_shield', 'ice_armor', 'prot_evil', 'bless', 'fly', 'nonsense']);
  assert.equal(p.shell, WARDS.sanctuary.shell, 'sanctuary outshines a shield');
  assert.deepEqual(p.orbits.map(o => o.kind), ['stone', 'flame']);
  assert.equal(p.ring, WARDS.prot_evil.ring);
  assert.equal(p.motes.length, 1);
  assert.equal(p.hover, true);
  assert.equal(planKey(['fly', 'nonsense', 'bless']), 'bless,fly');
  assert.equal(planKey(['nonsense']), '');
});

test('every ward the server sends has a look (map_system.WARD_FLAGS, WARD_NAMES)', () => {
  const src = readFileSync(path.join(HERE, '../../src/map_system.py'), 'utf8');
  const flags = src.match(/WARD_FLAGS = frozenset\(\{([^}]*)\}\)/)[1].match(/'([a-z_]+)'/g).map(s => s.slice(1, -1));
  const names = [...src.match(/WARD_NAMES = \{([^}]*)\}/)[1].matchAll(/: '([a-z_]+)'/g)].map(m => m[1]);
  for (const k of [...flags, ...names]) assert.ok(WARDS[k], `${k} is drawn`);
});

const body = () => {
  const root = new THREE.Group();
  const m = new THREE.Mesh(new THREE.BoxGeometry(0.6, 1.8, 0.4), new THREE.MeshStandardMaterial());
  m.position.y = 0.9;
  root.add(m);
  const scene = new THREE.Scene();
  scene.add(root);
  return { root, m };
};
const fx = { near: () => true, p: { emit() {} }, glyph() {} };

test('every harm the server names has a look, and each emitter puts something out', () => {
  const src = readFileSync(path.join(HERE, '../../src/map_system.py'), 'utf8');
  const named = [...src.matchAll(/return '([a-z]+)'/g)].map(m => m[1]).filter(k => ['burning', 'bleeding', 'frozen', 'cursed'].includes(k));
  const flags = Object.values(Object.fromEntries([...src.match(/STATUS_FLAGS = \{([^}]*)\}/)[1].matchAll(/'([a-z_]+)': '([a-z_]+)'/g)].map(m => [m[1], m[2]])));
  for (const k of [...new Set([...named, ...flags, 'poisoned'])]) assert.ok(WARDS[k], `${k} has a look`);
  for (const kind of Object.keys(HARMS)) {
    let n = 0;
    const count = { near: () => true, p: { emit: () => n++ }, glyph: () => n++ };
    const s = { h: 1.8, w: 0.8 };
    for (let i = 0; i < 40; i++) emitHarms([kind], count, body().root, s, 0.1, 0);
    assert.ok(n >= 2, `${kind}: ${n} in 4 s`);
  }
});

test('combat feel: the knock, the punch, the notice, the heartbeat, the deaths are wired', () => {
  const W = p => readFileSync(path.join(HERE, '../../src/web_isometric/world3d', p), 'utf8');
  assert.match(W('combat.js'), /this\.ents\.knock\(dst\.ent, src\.root\.position/);
  assert.match(W('engine.js'), /punch: m =>/);
  assert.match(W('main.js'), /if \(fresh\) notice\(e\);/);
  assert.match(W('main.js'), /sound\.play\('heartbeat'\)/);
  assert.match(W('entities.js'), /deathStyle\(e\.data\.name, e\.data\.short/);
  assert.match(W('play.html'), /data-set="autolootgold"/);
});

test('harms on the body: the strongest glow; a frost or hold slows or stops it; a sleeper slumps; the blind wear a band', () => {
  const p = wardPlan(['poisoned', 'burning', 'frozen', 'asleep', 'feared', 'blinded', 'bleeding']);
  assert.equal(p.tint, WARDS.frozen.tint, 'frost outshines burn and poison');
  assert.equal(p.rate, 0.2);
  assert.ok(p.slump && p.tremble && p.band);
  assert.deepEqual(p.fx.sort(), ['bleed', 'burn', 'fear', 'frost', 'poison', 'zzz']);
  const w = new Wards({ quality: { name: 'high' } }, fx);
  const a = body();
  const stand = a.m.rotation.x;
  w.update(0.1, 1, a, ['asleep', 'blinded', 'feared']);
  assert.equal(a.root.userData.animRate, 0.3, 'a sleeper moves slowly');
  assert.ok(a.m.rotation.x > stand + 0.2, 'and slumps forward');
  assert.ok(a.root.children.some(c => c.name === 'ward_band'), 'the blind wear a band');
  w.update(0.1, 1.1, a, []);
  assert.equal(a.root.userData.animRate, undefined);
  assert.ok(Math.abs(a.m.rotation.x - stand) < 1e-6 && Math.abs(a.m.position.x) < 1e-6, 'all of it taken off again');
});

test('poisoned: green bubbles rise off the body and a haze hangs about it, for as long as it lasts', () => {
  assert.equal(wardPlan(['poisoned']).tint, WARDS.poisoned.tint);
  assert.deepEqual(wardPlan(['poisoned']).fx, ['poison']);
  const seen = { bubbles: 0, haze: 0 };
  const watch = { near: () => true, p: { emit: (_p, o) => { if (o.color === HAZE) seen.haze++; } }, glyph: (_p, o) => { if (o.glyph === 'bubble') seen.bubbles++; } };
  const w = new Wards({ quality: { name: 'high' } }, watch);
  const a = body();
  const skin = a.m.material;
  for (let i = 0; i < 30; i++) w.update(0.1, i * 0.1, a, ['poisoned']);
  assert.ok(seen.bubbles > 10 && seen.haze > 5, `bubbles ${seen.bubbles}, haze ${seen.haze}`);
  assert.ok(a.m.material !== skin && a.m.material.emissive.g > 0.5, 'the body glows a sickly green');
  const slow = { bubbles: 0 };
  const w2 = new Wards({ quality: { name: 'high' } }, { near: () => true, p: { emit() {} }, glyph: () => slow.bubbles++ });
  const b2 = body();
  for (let i = 0; i < 6; i++) w2.update(0.5, i * 0.5, b2, ['poisoned']);
  assert.ok(slow.bubbles >= 12, `a slow machine (2 frames a second) sees the bubbles too (${slow.bubbles})`);
  w.update(0.1, 4, a, []);
  assert.equal(a.m.material, skin, 'its own skin back when the poison wears off');
  const was = { ...seen };
  for (let i = 0; i < 10; i++) w.update(0.1, 4 + i * 0.1, a, []);
  assert.deepEqual(seen, was, 'and stops when it wears off');
  const src = readFileSync(path.join(HERE, '../../src/web_isometric/world3d/combat.js'), 'utf8');
  assert.match(src, /poisonTick\(e, school\)\) this\.wince\(dst, p\)/, 'each tick of it makes the body wince');
});

test('worn while it lasts: a shell and orbit on the body, flying lifts it, and all of it goes when the spell ends', () => {
  const w = new Wards({ quality: { name: 'high' } }, fx);
  const a = body();
  w.update(0.1, 1, a, ['shielded', 'stoneskin', 'fly']);
  const parts = a.root.children.filter(c => /^ward_/.test(c.name)).map(c => c.name);
  assert.ok(parts.includes('ward_shell') && parts.includes('ward_stone') && parts.includes('ward_wind'), parts.join(','));
  assert.ok(a.m.position.y > 0.9 + 0.25, `flying lifts the body (${a.m.position.y.toFixed(2)})`);
  w.update(0.1, 1.1, a, ['stoneskin']);              // the shield and the flight end
  assert.ok(!a.root.children.some(c => c.name === 'ward_shell'), 'the shell is gone');
  assert.ok(Math.abs(a.m.position.y - 0.9) < 1e-6, 'back on the ground');
  w.update(0.1, 1.2, a, []);
  assert.equal(a.root.children.filter(c => /^ward_/.test(c.name)).length, 0, 'nothing left');
});

test('others are warded nearest first, within the budget; invisibility only shows on yourself', () => {
  const w = new Wards({ quality: { name: 'low' } }, fx);
  const hero = body();
  const others = Array.from({ length: 6 }, (_, i) => { const b = body(); b.root.position.x = i + 1; return [b, ['shielded', 'invisible']]; });
  w.update(0.1, 1, hero, ['invisible'], others);
  assert.equal(w.on.size, 4, 'the hero and the three nearest (low)');
  assert.ok(w.on.get(others[0][0]).plan.fade === false && w.on.get(hero).plan.fade === true);
  assert.ok(hero.m.material.transparent && hero.m.material.opacity < 0.5, 'you see yourself faint');
  w.update(0.1, 1.1, hero, [], others);
  assert.equal(hero.m.material.opacity, 1, 'and whole again');
});

test('mounting while flying: the saddle sets the height (steed.js takes the hover off)', () => {
  const src = readFileSync(path.join(HERE, '../../src/web_isometric/world3d/steed.js'), 'utf8');
  assert.match(src, /const hover = rider\.root\.userData\.wardLift \|\| 0;/);
  assert.match(src, /c\.position\.y - hover/);
});

test('one buff icon a spell: Armor\'s two affects show once, with the longer time', () => {
  const list = buffList([
    { name: 'armor', applies_to: 'ac', remaining: 90, duration: 150 },
    { name: 'armor', applies_to: 'armour_ward', remaining: 120, duration: 150 },
    { name: 'Bless', remaining: 10, duration: 24 }, { name: 'bless', remaining: 5, duration: 24 }, null, {}]);
  assert.deepEqual(list.map(a => [a.name, a.remaining]), [['armor', 120], ['Bless', 10]]);
});

test('a nameplate\'s auras (map_system._auras): debuffs first, each its share of time left', () => {
  const list = plateAuras([
    { n: 'bless', h: 0, r: 6, d: 12 }, { n: 'poison', h: 1, r: 3, d: 8 }, { n: 'Shield Wall_invuln', h: 0, r: 0, d: 0 },
    { n: 'curse', h: 1, r: 20, d: 10 }, null, { h: 1 }]);
  assert.deepEqual(list.map(a => [a.id, a.bad]), [['poison', true], ['curse', true], ['bless', false], ['shield_wall', false]]);
  assert.equal(list[0].frac, 3 / 8);
  assert.equal(list[0].secs, 18);
  assert.equal(list[1].frac, 1, 'never more than full');
  assert.equal(list[3].secs, null, 'no time on one with no length');
  assert.equal(list[3].label, 'Shield Wall invuln');
  assert.equal(plateAuras(Array.from({ length: 12 }, (_, i) => ({ n: `s${i}` }))).length, 8);
  assert.deepEqual(plateAuras(undefined), []);
  assert.equal(auraBase('Divine Shield_damage'), 'divine_shield');
});
