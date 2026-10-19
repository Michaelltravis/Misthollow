// Riding in /play (Push 34): every mount the server knows has a steed the creature kit can build,
// and the controller and main loop use the payload's speed.
//   node --test tests/web/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { STEEDS, steedSpec, MOUNT_LOOK, mountLook, bulkFor } from '../../src/web_isometric/world3d/steedlogic.js';
import { kinRecipe } from '../../src/web_isometric/world3d/kinrecipe.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const serverMounts = () => {
  const src = fs.readFileSync(path.join(ROOT, 'src/mounts.py'), 'utf8');
  const keys = new Set();
  for (const m of src.matchAll(/'key': '([a-z_]+)'/g)) keys.add(m[1]);
  for (const m of src.matchAll(/_faction_mount\('([a-z_]+)'/g)) keys.add(m[1]);
  keys.add('nightmare_steed');
  return [...keys];
};

test('every mount the server knows has a steed', () => {
  const missing = serverMounts().filter(k => !STEEDS[k]);
  assert.deepEqual(missing, []);
});

test("every steed's body is one the creature kit builds, with a saddle on its back", () => {
  for (const key of Object.keys(STEEDS)) {
    const s = steedSpec(key);
    const r = kinRecipe(s.body, s.words, 7, s.tint);
    assert.ok(r && r.plan, `${key}: the kit builds a ${s.body}`);
    assert.ok(s.back > 0.4 && s.back < 1, `${key}: its saddle sits on its back (${s.back})`);
    assert.ok(s.height >= 0.7 && s.height <= 1.2, `${key}: sized beside its rider (${s.height})`);
  }
  assert.equal(steedSpec('no_such_mount').body, 'horse', 'an unknown mount is drawn as a horse');
});

test('every mount has a real animated body, its tack and its marks', () => {
  const index = JSON.parse(fs.readFileSync(path.join(ROOT, 'src/web_isometric/art3d/bodies/index.json'), 'utf8'));
  const bodies = new Set(Object.keys(index.bodies || index));
  const TACK = new Set(['leather', 'war', 'dark', 'plate', 'pack']);
  const FX = new Set(['hellfire', 'celestial', 'steam', 'arcane', 'moon', 'shadow', 'embers', 'leaves']);
  for (const key of serverMounts()) {
    const L = MOUNT_LOOK[key];
    assert.ok(L, `${key}: has a look`);
    assert.ok(bodies.has(L.body), `${key}: its body ${L.body} is in bodies/index.json`);
    assert.ok(TACK.has(L.tack), `${key}: its tack ${L.tack}`);
    assert.ok(!L.fx || FX.has(L.fx), `${key}: its marks ${L.fx}`);
    assert.ok(!L.size || (L.size >= 0.8 && L.size <= 1.3), `${key}: sized beside its rider`);
  }
  assert.equal(mountLook('no_such_mount').body, 'horse', 'an unknown mount is a horse');
  const steed = fs.readFileSync(path.join(ROOT, 'src/web_isometric/world3d/steed.js'), 'utf8');
  assert.match(steed, /spawnBody\(/, 'the steed is a real creature body');
  assert.match(steed, /buildTack\(/, 'dressed in its tack');
  assert.match(steed, /kitSteed\(/, 'with the kit steed until the body loads');
});

test('horses are thickened along their bones, by the names three.js gives them', () => {
  // three.js drops the dots from glTF names: fl0.L arrives as fl0L
  for (const b of ['horse', 'unicorn']) {
    assert.ok(bulkFor(b, 'fl0L') > 1.5 && bulkFor(b, 'hl1R') > 1.5, `${b}: sturdy legs`);
    assert.ok(bulkFor(b, 'spine') > 1.2 && bulkFor(b, 'neck') > 1.2, `${b}: a deep barrel, a heavy neck`);
  }
  assert.equal(bulkFor('wolf', 'fl0L'), 1, 'other bodies keep their own build');
  const steed = fs.readFileSync(path.join(ROOT, 'src/web_isometric/world3d/steed.js'), 'utf8');
  assert.match(steed, /new THREE\.Float32BufferAttribute\(Q\.count \* 3, 3\)/, 'packed positions are unpacked before they are pushed out');
  for (const k of ['horse', 'warhorse', 'nightmare', 'celestial_charger']) assert.ok(MOUNT_LOOK[k].size >= 1.15, `${k}: a big horse`);
});

test('the hero runs as fast as the server says, and sits while riding', () => {
  const read = f => fs.readFileSync(path.join(ROOT, 'src/web_isometric/world3d', f), 'utf8');
  const ctl = read('controller.js'), main = read('main.js'), ents = read('entities.js');
  assert.match(ctl, /\* \(this\.speedMul \|\| 1\)/, 'the run is multiplied by the speed');
  assert.match(ctl, /this\.mounted\) this\.actor\.play\('Idle'/, 'a rider plays their idle (the legs are posed by steed.js)');
  assert.match(main, /riding\.pose\(/, 'the hero is posed astride each frame');
  assert.match(ents, /e\.riding\.pose\(/, 'and so is everyone else riding');
  const steed = read('steed.js');
  assert.match(steed, /export function ridePose/, 'the riding pose');
  assert.ok(!/Sit_Floor/.test(ctl + main + ents + read('demo.js')), 'no rider sits cross-legged any more');
  assert.match(main, /ctl\.speedMul = .*p\.speed/, "main sets the speed from the payload's");
  assert.match(main, /mountRider\(hero, key/, 'main seats the hero on their steed');
  assert.match(ents, /mountRider\(e\.actor, w\.data\.mount/, 'other players ride theirs too');
});

test('you get up and down from /play: R, the menu horseshoe, the riding chip, the hero menu', async () => {
  const read = f => fs.readFileSync(path.join(ROOT, 'src/web_isometric/world3d', f), 'utf8');
  const hud = read('hud/hud.js'), html = read('play.html');
  assert.match(hud, /k === 'r' \|\| k === 'R'\) \{ rideToggle\(\)/, 'R toggles riding');
  // the server decides up or down (`mount toggle`, tests/test_mounts.py): the page's copy of
  // whether you ride can be a payload behind, and asking for the wrong one did nothing
  assert.match(hud, /send\('mount toggle'\)/, 'R asks the server to toggle');
  assert.doesNotMatch(hud, /if \(p\.mount\) send\('dismount'\)/, 'not by the page guessing which');
  assert.match(hud, /You own no mount/, 'owning none: it says where to get one');
  assert.match(html, /data-act="ride" data-icon="horseshoe"[^>]*data-key="R"/, 'a menu button for it');
  assert.match(hud, /\[data-act="ride"\]'\)\.addEventListener\('click', \(\) => rideToggle\(\)\)/, 'the button rides or dismounts');
  assert.match(html, /id="riding"/, 'a chip by the portrait while riding');
  assert.match(hud, /paintRiding\(p\)/, 'painted from the payload');
  const { verbsFor } = await import('../../src/web_isometric/world3d/hud/verbs.js');
  const labels = m => m.items.map(i => i.label);
  const up = verbsFor({ kind: 'self' }, { mount: { key: 'griffin', name: 'a griffin' } });
  assert.ok(up.items.some(i => i.cmd === 'dismount'), `riding: the hero menu offers Dismount (${labels(up)})`);
  const down = verbsFor({ kind: 'self' }, { mounts: [{ key: 'griffin', name: 'a griffin' }, { key: 'horse', name: 'a horse' }] });
  assert.ok(down.items.some(i => i.cmd === 'mount griffin') && down.items.some(i => i.cmd === 'mount horse'), 'on foot: Mount each one owned');
  const none = verbsFor({ kind: 'self' }, {});
  assert.ok(!none.items.some(i => /^(dis)?mount/.test(i.cmd || '')), 'owning none: neither');
});
