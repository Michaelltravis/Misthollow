// The world's murmurs in /play: sounds from where they come, creatures heard as cues, no chat line.
//   node --test tests/web/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { sourceOf, cueOf, labelOf, screenAngle } from '../../src/web_isometric/world3d/hud/ambient.js';
import { SOUNDS, FILES } from '../../src/web_isometric/world3d/soundtable.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const read = f => fs.readFileSync(path.join(ROOT, f), 'utf8');

test('a murmur sounds from its room, else its way, else about you', () => {
  const hero = { x: 100, z: 100 };
  assert.deepEqual(sourceOf({ room: 7 }, hero, v => (v === 7 ? { x: 5, z: 6 } : null)), { x: 5, z: 6 });
  assert.deepEqual(sourceOf({ dir: 'south' }, hero, () => null), { x: 100, z: 114 });
  const p = sourceOf({}, hero, () => null, () => 0.5);
  const d = Math.hypot(p.x - hero.x, p.z - hero.z);
  assert.ok(d >= 6 && d <= 12, `a place sound comes from close by (${d.toFixed(1)} m)`);
});

test('a creature heard gets a cue with what it is; a place sound gets none', () => {
  assert.deepEqual(cueOf({ key: 'presence', name: 'a gate guardian', dir: 'south', room: 22001, moving: true }),
    { label: 'Gate guardian', dir: 'south', room: 22001, moving: true });
  assert.equal(cueOf({ key: 'smithy', text: 'Hammer rings on anvil close by.' }), null);
  assert.equal(labelOf({}), 'Footsteps', 'unnamed: footsteps');
});

test('the edge arrow points the way on screen, whichever way the camera is turned', () => {
  const at = { x: 0, z: 0 };
  assert.ok(Math.abs(screenAngle(at, { x: 0, z: -10 }, 0)) < 1e-9, 'north is up, camera north up');
  assert.ok(Math.abs(screenAngle(at, { x: 10, z: 0 }, 0) - Math.PI / 2) < 1e-9, 'east is right');
  assert.ok(Math.abs(Math.abs(screenAngle(at, { x: 0, z: 10 }, 0)) - Math.PI) < 1e-9, 'south is down');
});

test('every ambient sound the server names is in the sound table, on the ambience bus, placed', () => {
  const lines = read('src/ambient_lines.py');
  const names = new Set([...lines.matchAll(/'(amb_[a-z_]+)'/g)].map(m => m[1]).concat(['amb_steps']));
  assert.ok(names.size >= 8, `the server names its sounds (${[...names]})`);
  const flat = n => (SOUNDS[n] && SOUNDS[n].layers ? SOUNDS[n].layers : [n]);
  for (const n of names) {
    assert.ok(SOUNDS[n], `${n} is in SOUNDS`);
    for (const k of flat(n)) {
      const d = SOUNDS[k];
      assert.ok(d && d.bus === 'amb' && d.pos, `${k}: on the ambience bus, placed in the world`);
      if (d.file) assert.ok(FILES[d.file], `${k}: its file ${d.file} exists`);
      if (d.synth) assert.match(read('src/web_isometric/world3d/audio.js'), new RegExp(`\\b${d.synth}: \\(`), `${k}: its synth ${d.synth} exists`);
    }
  }
});

test('wired: net.js relays the event, main.js plays it, the minimap pings, settings has captions', () => {
  assert.match(read('src/web_isometric/shared/net.js'), /payload\.type === 'ambient'\) MH\.bus\.emit\('ambient\.murmur', payload\)/);
  const main = read('src/web_isometric/world3d/main.js');
  assert.match(main, /MH\.bus\.on\('ambient\.murmur', m => \{ ambient\.on\(m\);/);
  // a creature heard next door flares its way out on the room card's compass (roomcard.js)
  assert.match(main, /const c = cueOf\(m\); if \(c && c\.dir\) roomCard\.ping\(c\.dir\)/);
  assert.match(main, /ambient\.update\(\)/);
  assert.match(read('src/web_isometric/world3d/hud/minimap.js'), /ping\(vnum, kind = 'danger'\)/);
  assert.match(read('src/web_isometric/world3d/play.html'), /data-set="ambcap"/);
});
