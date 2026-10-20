// The land round an outdoor room (world3d/skirt.js): it fills only empty cells.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { skirtPatches } from '../../src/web_isometric/world3d/skirt.js';

const W = 24, H = 15;
const plan = (taken, wild = true) => skirtPatches({ ox: 0, oz: 0, W, H, wild, empty: (dx, dy) => !taken.has(`${dx},${dy}`) });
// the cells (room-relative) a patch covers any part of
const cellsUnder = ([x0, z0, w, d]) => {
  const out = new Set();
  for (let cx = Math.floor(x0 / W); cx * W < x0 + w - 1e-6; cx++)
    for (let cy = Math.floor(z0 / H); cy * H < z0 + d - 1e-6; cy++) out.add(`${cx},${cy}`);
  return out;
};

test('alone in an opened zone: the land runs on a cell and a half every way', () => {
  const ps = plan(new Set());
  assert.equal(ps.length, 8);
  for (const p of ps.filter(p => p[4] === 'c')) assert.deepEqual([p[2], p[3]], [W * 1.5, H * 1.5]);
});

test('a corner never reaches over a room a cell across and two cells down (Before The Gates Of Mahn-Tor)', () => {
  // the mountain room On The Cliffside sat at [11,1], the gates at [12,3]: one across, two down
  const ps = plan(new Set(['1,2']));
  for (const p of ps) assert.ok(!cellsUnder(p).has('1,2'), `patch ${p} covers the room at 1,2`);
  const se = ps.find(p => p[4] === 'c' && p[0] >= W && p[1] >= H);
  assert.deepEqual([se[2], se[3]], [W * 1.5, H / 2], 'still runs on eastward, where it is empty');
});

test('no patch covers a taken cell, wherever the neighbours stand', () => {
  const around = [];
  for (let dx = -2; dx <= 2; dx++) for (let dy = -2; dy <= 2; dy++) if (dx || dy) around.push(`${dx},${dy}`);
  for (let i = 0; i < 400; i++) {
    const taken = new Set(around.filter((_, k) => ((i * 2654435761 + k * 40503) >>> 7) % 5 === 0));
    for (const p of plan(taken)) for (const c of cellsUnder(p)) assert.ok(!taken.has(c), `patch ${p} covers taken ${c} (${[...taken]})`);
  }
});

test('outside an opened zone the land fills half the empty cell', () => {
  for (const p of plan(new Set(), false)) assert.ok(p[2] <= W / 2 + 1e-9 || p[3] <= H / 2 + 1e-9);
});
