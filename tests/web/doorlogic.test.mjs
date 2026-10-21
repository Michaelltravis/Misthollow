// What a door offers (world3d/doorlogic.js): the one-key prompt and the right-click menu.
//   node --test tests/web/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { doorPrompt, doorVerbs, doorAnchor } from '../../src/web_isometric/world3d/doorlogic.js';

const door = (o = {}) => ({ label: 'oak door', closed: true, locked: false, has_key: false, can_pick: false, keyless: false, ...o });

test('prompt: open, unlock with a key, pick, locked, close, nothing when broken', () => {
  assert.deepEqual(doorPrompt(door()).action, 'open');
  assert.equal(doorPrompt(door({ locked: true, has_key: true })).action, 'unlockopen');
  assert.equal(doorPrompt(door({ locked: true, keyless: true })).action, 'unlockopen');
  assert.equal(doorPrompt(door({ locked: true, can_pick: true })).action, 'pick');
  const locked = doorPrompt(door({ locked: true, key_name: 'a rusted watch-key' }));
  assert.equal(locked.action, null);
  assert.match(locked.text, /needs a rusted watch-key/);
  assert.equal(doorPrompt(door({ closed: false })).action, 'close');
  assert.equal(doorPrompt(door({ broken: true })), null);
  assert.equal(doorPrompt(door({ sealed: true })).action, null);
});

test('menu: the actions that make sense now', () => {
  const acts = info => doorVerbs(info).map(v => v.action);
  assert.deepEqual(acts(door()), ['open', 'knock', 'bash']);
  assert.deepEqual(acts(door({ keyless: true })), ['open', 'lock', 'knock', 'bash']);
  assert.deepEqual(acts(door({ locked: true, has_key: true })), ['unlockopen', 'unlock', 'knock', 'bash']);
  assert.deepEqual(acts(door({ locked: true, can_pick: true })), ['pick', 'knock', 'bash']);
  assert.deepEqual(acts(door({ locked: true })), [null, 'knock', 'bash']);
  assert.deepEqual(acts(door({ closed: false })), ['close']);
});

test('menu: the door spells for those who know them, and doors no force breaks', () => {
  const acts = info => doorVerbs(info).map(v => v.action);
  assert.deepEqual(acts(door({ can_block: true })), ['open', 'knock', 'bash', 'block']);
  assert.deepEqual(acts(door({ can_break: true })), ['open', 'knock', 'bash', 'break']);
  assert.deepEqual(acts(door({ can_block: true, sealed: true })), ['open', 'knock', 'bash']);
  assert.deepEqual(acts(door({ can_block: true, closed: false })), ['close']);
  const warded = doorVerbs(door({ arcane: true, can_break: true, can_block: true }));
  assert.deepEqual(warded.map(v => v.action), ['open', 'knock', null, 'block']);
  assert.match(warded[2].label, /old magic/);
  assert.match(doorVerbs(door({ material: 'iron' })).find(v => v.action === 'bash').label, /\(iron\)/);
});

test('anchor: the middle of the doorway on the room edge, or the stairs for a trapdoor', () => {
  const L = { gaps: { north: { x0: 9, x1: 14 }, east: { y0: 5, y1: 9 } }, stairsDown: { x: 7, y: 4 } };
  assert.deepEqual(doorAnchor(L, 'north', 24, 15), { x: 12, z: 0.15 });
  assert.deepEqual(doorAnchor(L, 'east', 24, 15), { x: 23.85, z: 7.5 });
  assert.deepEqual(doorAnchor(L, 'down', 24, 15), { x: 7.5, z: 4.5 });
  assert.equal(doorAnchor(L, 'up', 24, 15), null);
});
