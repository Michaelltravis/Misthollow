// Your own action bar and the spellbook's bookkeeping (world3d/abilities.js).
//   node --test tests/web/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { SLOTS, MAIN, EXTRA, keyOf, slotForKey, rankOf, cleanBar, defaultBar, placeNew, putOnBar, takeOffBar, keepUnseen, diffAbilities, costLine } from '../../src/web_isometric/world3d/abilities.js';

const ab = (id, o = {}) => ({ id, name: id, type: 'skill', pct: 50, level: 1, known: true, ...o });
const LIST = [ab('bash'), ab('kick', { level: 3 }), ab('cleave', { level: 5 }), ab('rally', { level: 9 }), ab('charge', { known: false, pct: 0, level: 20 })];

test('ranks by proficiency: learned at 50%, mastered by use at 85%, perfected by a trainer', () => {
  assert.equal(rankOf(50), 'Novice');
  assert.equal(rankOf(72), 'Adept');
  assert.equal(rankOf(85), 'Mastered');
  assert.equal(rankOf(100), 'Perfected');
  assert.equal(rankOf(0), 'Not learned');
});

test('a first bar follows the class order, then the level each ability came at', () => {
  const bar = defaultBar(LIST, ['cleave', 'bash']);
  assert.equal(bar.length, SLOTS);
  assert.deepEqual(bar.slice(0, 5), ['cleave', 'bash', 'kick', 'rally', null], 'unknown abilities stay off');
});

test("the server's bar keeps only what you know, once each, always SLOTS long", () => {
  const bar = cleanBar(['kick', 'charge', 'kick', 'ghost', null, 'bash'], LIST);
  assert.deepEqual(bar.slice(0, 6), ['kick', null, null, null, null, 'bash']);
  assert.equal(bar.length, SLOTS);
  assert.equal(cleanBar(null, LIST).every(x => x === null), true);
});

test('new abilities fill the first free slots; moving one swaps it with what was there', () => {
  const start = putOnBar(new Array(SLOTS).fill(null), 'bash', 1);
  const { bar, placed } = placeNew(start, ['kick', 'bash', 'cleave']);
  assert.deepEqual(placed, [{ id: 'kick', slot: 0 }, { id: 'cleave', slot: 2 }], 'already on the bar: left alone');
  const moved = putOnBar(bar, 'cleave', 0);
  assert.deepEqual(moved.slice(0, 3), ['cleave', 'bash', 'kick']);
  assert.deepEqual(takeOffBar(moved, 1).slice(0, 3), ['cleave', null, 'kick']);
  const full = new Array(SLOTS).fill('x').map((x, i) => `a${i}`);
  assert.deepEqual(placeNew(full, ['late']).placed, [], 'a full bar takes nothing');
});

test('between payloads: what was learned and what improved', () => {
  const next = LIST.map(a => a.id === 'kick' ? { ...a, pct: 53 } : a.id === 'charge' ? { ...a, known: true, pct: 50 } : a);
  assert.deepEqual(diffAbilities(LIST, next), { learned: ['charge'], improved: [{ id: 'kick', from: 50, to: 53 }] });
  assert.deepEqual(diffAbilities(null, LIST).learned.length, 4, 'the first payload learns everything (callers skip it)');
});

test('the cost line reads like a tooltip', () => {
  assert.equal(costLine({ cost: 15, res: 'mana', cd: 6, range: 14 }), '15 mana · 6 s cooldown · 14 m');
  assert.equal(costLine({ cd: 120, target: 'self' }), '2 min cooldown · yourself');
  assert.equal(costLine({ range: 2.5 }), 'melee');
});

test('the main bar and three extra bars: 40 slots, keys 1-8, Shift, Alt, Alt+Shift, and one to click', () => {
  assert.equal(SLOTS, 40);
  assert.equal(MAIN, 16);
  assert.deepEqual(EXTRA, [[16, 24], [24, 32], [32, 40]]);
  assert.deepEqual([0, 7, 8, 15, 16, 23, 24, 31, 32, 39].map(i => keyOf(i)), ['1', '8', 'S1', 'S8', 'A1', 'A8', 'AS1', 'AS8', '', '']);
  assert.equal(keyOf(17, true), 'Alt+2');
  assert.equal(slotForKey(1), 0);
  assert.equal(slotForKey(3, { shift: true }), 10);
  assert.equal(slotForKey(1, { alt: true }), 16);
  assert.equal(slotForKey(8, { alt: true, shift: true }), 31);
  assert.equal(slotForKey(9), -1);
});

test('an old 16-slot bar comes back as 40; a first bar fills only the main bar; new abilities fill bars that show', () => {
  const old = cleanBar(['bash', 'kick', ...new Array(14).fill(null)], LIST);
  assert.equal(old.length, 40);
  assert.deepEqual(old.slice(0, 2), ['bash', 'kick']);
  const many = Array.from({ length: 30 }, (_, i) => ab(`a${i}`, { level: i }));
  const first = defaultBar(many);
  assert.equal(first.filter(Boolean).length, MAIN, 'the extra bars start empty: they are yours to fill');
  const fullMain = new Array(SLOTS).fill(null).map((_, i) => (i < MAIN ? `m${i}` : null));
  assert.deepEqual(placeNew(fullMain, ['late'], MAIN).placed, [], 'with no extra bar showing, nothing is hidden away');
  assert.deepEqual(placeNew(fullMain, ['late'], MAIN + 8).placed, [{ id: 'late', slot: 16 }], 'with one, the new ability goes to bar 3');
  assert.deepEqual(putOnBar(fullMain, 'm0', 33).slice(32, 34), [null, 'm0'], 'any slot of any bar takes an ability');
});

test('a locked bar keeps what is on it: nothing dragged off, swapped out, dropped on or placed', () => {
  const bar = new Array(SLOTS).fill(null);
  bar[0] = 'bash'; bar[16] = 'kick'; bar[17] = 'cleave';
  const locked = i => i >= 16 && i < 24;              // bar 3 locked
  assert.deepEqual(putOnBar(bar, 'trip', 18, locked), bar, 'nothing dropped onto a locked bar');
  assert.deepEqual(putOnBar(bar, 'kick', 1, locked), bar, 'nothing pulled off it to another bar');
  assert.deepEqual(putOnBar(bar, 'bash', 16, locked), bar, 'nor swapped in from another');
  assert.deepEqual(takeOffBar(bar, 17, locked), bar, 'nor taken off');
  assert.deepEqual(putOnBar(bar, 'bash', 2, locked).slice(0, 3), [null, null, 'bash'], 'an unlocked bar moves freely');
  const full = bar.map((x, i) => (i < MAIN ? x || `m${i}` : x));
  assert.deepEqual(placeNew(full, ['late'], MAIN + 8, locked).placed, [], 'a new ability does not land on a locked bar');
  assert.deepEqual(placeNew(full, ['late'], MAIN + 16, locked).placed, [{ id: 'late', slot: 24 }], 'it goes to the next one that is free');
});

test('a change to the bar keeps what this client could not see', () => {
  const arranged = new Array(SLOTS).fill(null);
  arranged[0] = 'bash'; arranged[3] = 'fireball'; arranged[20] = 'heal';
  const shown = arranged.map(x => (x === 'fireball' ? null : x));       // the book had not come yet
  const next = putOnBar(shown, 'kick', 1);
  const sent = keepUnseen(next, arranged, shown);
  assert.equal(sent[3], 'fireball', 'the unseen ability is still where it was');
  assert.deepEqual([sent[0], sent[1], sent[20]], ['bash', 'kick', 'heal']);
  assert.equal(keepUnseen(putOnBar(shown, 'kick', 3), arranged, shown)[3], 'kick', 'what you put in its slot wins');
  assert.equal(keepUnseen(takeOffBar(shown, 0), arranged, shown)[0], null, 'what you took off stays off');
});
