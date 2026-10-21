// The body under the player frame (world3d/hud/body.js): hunger, thirst and stamina meters warn
// where the server's lines warn; a posture is a button to get up.   node --test tests/web/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { needLevel, postureAction, postureOf, meters, NEED } from '../../src/web_isometric/world3d/hud/body.js';
import { PICTO } from '../../src/web_isometric/world3d/hud/icons.js';
import { DRAW } from '../../src/web_isometric/world3d/glyphs.js';

test('hunger and thirst warn where Player.hunger_thirst_tick does; stamina by its share', () => {
  assert.equal(needLevel(100, 168, 'hunger'), 'ok');
  assert.equal(needLevel(48, 168, 'hunger'), 'low');
  assert.equal(needLevel(24, 168, 'hunger'), 'crit');
  assert.equal(needLevel(24, 60, 'thirst'), 'low');
  assert.equal(needLevel(12, 60, 'thirst'), 'crit');
  assert.equal(needLevel(50, 100, 'move'), 'ok');
  assert.equal(needLevel(20, 100, 'move'), 'low');
  assert.equal(needLevel(5, 100, 'move'), 'crit');
});

test('getting up: stand from a seat or rest, wake from sleep, nothing when standing', () => {
  assert.equal(postureAction('sitting'), 'stand');
  assert.equal(postureAction('resting'), 'stand');
  assert.equal(postureAction('sleeping'), 'wake');
  assert.equal(postureAction('standing'), null);
  assert.equal(postureOf('standing'), null);
  for (const pos of ['sitting', 'resting', 'sleeping']) assert.ok(PICTO[postureOf(pos).icon] || DRAW[postureOf(pos).icon], `${pos} has an icon`);
  for (const n of Object.values(NEED)) assert.ok(PICTO[n.icon] || DRAW[n.icon], `${n.label} has an icon`);
});

test('the meters come from the player block, filled by share', () => {
  const m = meters({ hunger: 84, max_hunger: 168, thirst: 6, max_thirst: 60, move: 90, max_move: 100, hunger_state: 'Peckish' });
  assert.deepEqual(m.map(x => x.kind), ['hunger', 'thirst', 'move']);
  assert.equal(m[0].fill, 0.5);
  assert.equal(m[1].level, 'crit');
  assert.equal(m[0].state, 'Peckish');
  assert.deepEqual(meters({ move: 5, max_move: 10 }).map(x => x.kind), ['move'], 'a block without needs shows stamina only');
});
