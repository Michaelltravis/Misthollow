// The land round an outdoor room (world3d/skirt.js): it fills only empty cells, and no two rooms'
// land lies on the same ground.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { skirtPatches } from '../../src/web_isometric/world3d/skirt.js';

const W = 24, H = 15;
// the patches of the room at cell (cx, cy), the taken cells given absolutely
const planAt = (cx, cy, taken, wild = true) =>
  skirtPatches({ ox: cx * W, oz: cy * H, W, H, wild, empty: (dx, dy) => !taken.has(`${cx + dx},${cy + dy}`) });
const plan = (taken, wild = true) => planAt(0, 0, taken, wild);
// the cells a patch covers any part of
const cellsUnder = ([x0, z0, w, d]) => {
  const out = new Set();
  for (let cx = Math.floor(x0 / W); cx * W < x0 + w - 1e-6; cx++)
    for (let cy = Math.floor(z0 / H); cy * H < z0 + d - 1e-6; cy++) out.add(`${cx},${cy}`);
  return out;
};
const meet = (a, b) => Math.min(a[0] + a[2], b[0] + b[2]) - Math.max(a[0], b[0]) > 1e-6
  && Math.min(a[1] + a[3], b[1] + b[3]) - Math.max(a[1], b[1]) > 1e-6;
// a scatter of taken cells on a 6x6 board, the same for the same i
const board = i => {
  const taken = new Set();
  for (let x = 0; x < 6; x++) for (let y = 0; y < 6; y++) if (((i * 2654435761 + (x * 7 + y) * 40503) >>> 9) % 3 === 0) taken.add(`${x},${y}`);
  return taken;
};

test('alone in an opened zone: the land runs on a cell and a half every way', () => {
  const ps = plan(new Set(['0,0']));
  assert.equal(ps.length, 8);
  for (const p of ps.filter(p => p[4] === 'c')) assert.deepEqual([p[2], p[3]], [W * 1.5, H * 1.5]);
});

test('a corner never reaches over a room a cell across and two cells down (Before The Gates Of Mahn-Tor)', () => {
  // the mountain room On The Cliffside sat at [11,1], the gates at [12,3]: one across, two down
  const taken = new Set(['0,0', '1,2']);
  const ps = plan(taken);
  for (const p of ps) assert.ok(!cellsUnder(p).has('1,2'), `patch ${p} covers the room at 1,2`);
  // the empty ground the corner used to reach is still land: one room or the other's
  const both = [...ps, ...planAt(1, 2, taken)];
  for (const [x, z] of [[1.25, 1.25], [1.75, 1.25], [2.25, 1.25], [1.25, 1.75]])
    assert.ok(both.some(p => meet(p, [x * W - 0.1, z * H - 0.1, 0.2, 0.2])), `ground at ${x},${z} is land`);
});

test('the strip in front of a room is its own, not the land of the room round the corner (A Leader Strand)', () => {
  // The Tether Path's neighbour at [11,9] grew trees in the cell south of A Leader Strand at [12,8]
  const taken = new Set(['0,0', '1,-1']);
  const corner = planAt(0, 0, taken), strand = planAt(1, -1, taken);
  const front = [W, 0, W, H / 2];     // the half of cell (1,0) next to A Leader Strand
  for (const p of corner) assert.ok(!meet(p, front), `the room round the corner lays ${p} in front of it`);
  assert.ok(strand.some(p => p[4] === 'z' && p[5] === 1 && meet(p, front)), 'A Leader Strand fills it');
});

test('no patch covers a taken cell, wherever the neighbours stand', () => {
  for (let i = 0; i < 300; i++) {
    const taken = board(i);
    for (const k of taken) {
      const [cx, cy] = k.split(',').map(Number);
      for (const p of planAt(cx, cy, taken)) for (const c of cellsUnder(p)) assert.ok(!taken.has(c), `${k}: patch ${p} covers taken ${c}`);
    }
  }
});

test('no two rooms lay land on the same ground', () => {
  for (const wild of [false, true]) for (let i = 0; i < 300; i++) {
    const taken = board(i);
    const all = [...taken].flatMap(k => { const [cx, cy] = k.split(',').map(Number); return planAt(cx, cy, taken, wild).map(p => [k, p]); });
    for (let a = 0; a < all.length; a++) for (let b = a + 1; b < all.length; b++)
      if (all[a][0] !== all[b][0]) assert.ok(!meet(all[a][1], all[b][1]), `${all[a][0]} ${all[a][1]} and ${all[b][0]} ${all[b][1]} (${wild ? 'opened' : 'plain'})`);
  }
});

test('a piece keeps the whole patch it was cut from, so a mountain still rises from its room', () => {
  const ps = plan(new Set(['0,0', '1,-1']));
  for (const p of ps) {
    const [x0, z0, w, d, , , base] = p;
    assert.ok(x0 >= base[0] - 1e-9 && z0 >= base[1] - 1e-9 && x0 + w <= base[0] + base[2] + 1e-9 && z0 + d <= base[1] + base[3] + 1e-9, `${p} inside ${base}`);
  }
});

test('outside an opened zone the land fills half the empty cell', () => {
  for (const p of plan(new Set(['0,0']), false)) assert.ok(p[2] <= W / 2 + 1e-9 || p[3] <= H / 2 + 1e-9);
});
