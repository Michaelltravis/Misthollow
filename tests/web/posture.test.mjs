// How a body shows the server's posture (world3d/posture.js): resting sits down, sleeping lies
// down, and both get up again; the clips are the rig's own.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { poseFor, postureChange, bodyPosition } from '../../src/web_isometric/world3d/posture.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

test('resting and sitting sit on the floor; sleeping lies down; the rest stand', () => {
  assert.equal(poseFor('resting').loop, 'Sit_Floor_Idle');
  assert.equal(poseFor('sitting').loop, 'Sit_Floor_Idle');
  assert.equal(poseFor('sleeping').loop, 'Lie_Idle');
  for (const p of ['standing', 'fighting', 'dead', undefined, null]) assert.equal(poseFor(p), null, String(p));
});

test('getting down, getting up, and nothing when nothing changes', () => {
  assert.deepEqual(postureChange('standing', 'resting'), { once: 'Sit_Floor_Down', loop: 'Sit_Floor_Idle' });
  assert.deepEqual(postureChange('standing', 'sleeping'), { once: 'Lie_Down', loop: 'Lie_Idle' });
  assert.deepEqual(postureChange('resting', 'standing'), { once: 'Sit_Floor_StandUp', loop: null });
  assert.deepEqual(postureChange('sleeping', 'standing'), { once: 'Lie_StandUp', loop: null });
  assert.deepEqual(postureChange('resting', 'sleeping'), { once: null, loop: 'Lie_Idle' });
  assert.equal(postureChange('resting', 'sitting'), null);
  assert.equal(postureChange('standing', 'fighting'), null);
  assert.equal(postureChange('standing', 'standing'), null);
});

test('a creature lies down only when a spell holds it asleep; a player as the server says', () => {
  assert.equal(bodyPosition('mob', { position: 'sleeping' }), 'sleeping');
  for (const p of ['standing', 'fighting', 'resting', 'sitting', undefined]) assert.equal(bodyPosition('mob', { position: p }), 'standing', String(p));
  assert.equal(bodyPosition('player', { position: 'resting' }), 'resting');
  assert.equal(bodyPosition('player', { position: 'sleeping' }), 'sleeping');
  assert.equal(bodyPosition('player', {}), 'standing');
});

test('a slept creature and the hero mid-fight are told their posture and wards', () => {
  const ms = fs.readFileSync(path.join(ROOT, 'src', 'map_system.py'), 'utf8');
  const combat = ms.slice(ms.indexOf('def build_combat_payload'), ms.indexOf('_ZONEMAP_CACHE'));
  assert.equal((combat.match(/'wards': _wards\((entity|player)\)/g) || []).length, 3, 'mobs, other players and the hero');
  assert.equal((combat.match(/'position': getattr\((entity|player), 'position'/g) || []).length, 3);
});

test('every clip a posture plays is in the rig', () => {
  const glb = fs.readFileSync(path.join(ROOT, 'src/web_isometric/art3d/chars/rig_anims.glb'));
  const len = glb.readUInt32LE(12);
  const names = new Set(JSON.parse(glb.subarray(20, 20 + len).toString('utf8')).animations.map(a => a.name));
  for (const p of ['resting', 'sleeping']) for (const k of ['loop', 'down', 'up']) assert.ok(names.has(poseFor(p)[k]), `${p} ${k}: ${poseFor(p)[k]}`);
});

test('the hero and other players take their posture from the payload', () => {
  const src = f => fs.readFileSync(path.join(ROOT, 'src', f), 'utf8');
  assert.match(src('web_isometric/world3d/main.js'), /ctl\.setPosture\(payload\.player\.position\)/);
  assert.match(src('web_isometric/world3d/entities.js'), /this\.posture\(e, bodyPosition\(e\.kind, w\.data\)\)/);
  assert.match(src('map_system.py'), /'position': getattr\(entity, 'position', 'standing'\)/);
});
