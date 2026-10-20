// How a body shows the server's posture (world3d/posture.js): resting sits down, sleeping lies
// down, and both get up again; the clips are the rig's own.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { poseFor, postureChange } from '../../src/web_isometric/world3d/posture.js';

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

test('every clip a posture plays is in the rig', () => {
  const glb = fs.readFileSync(path.join(ROOT, 'src/web_isometric/art3d/chars/rig_anims.glb'));
  const len = glb.readUInt32LE(12);
  const names = new Set(JSON.parse(glb.subarray(20, 20 + len).toString('utf8')).animations.map(a => a.name));
  for (const p of ['resting', 'sleeping']) for (const k of ['loop', 'down', 'up']) assert.ok(names.has(poseFor(p)[k]), `${p} ${k}: ${poseFor(p)[k]}`);
});

test('the hero and other players take their posture from the payload', () => {
  const src = f => fs.readFileSync(path.join(ROOT, 'src', f), 'utf8');
  assert.match(src('web_isometric/world3d/main.js'), /ctl\.setPosture\(payload\.player\.position\)/);
  assert.match(src('web_isometric/world3d/entities.js'), /this\.posture\(e, w\.data\.position\)/);
  assert.match(src('map_system.py'), /'position': getattr\(entity, 'position', 'standing'\)/);
});
