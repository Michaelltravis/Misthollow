// The lantern posts by the world's roads (lanternposts.js): which rooms have one, and how its lantern stands.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { postFor, postCell } from '../../src/web_isometric/world3d/lanternposts.js';

const regions = JSON.parse(fs.readFileSync(new URL('../../world/regions.json', import.meta.url), 'utf8')).regions.map(r => r.id);
const share = (region, sector = 'field', flags = []) => {
  let n = 0, states = new Set();
  for (let v = 1000; v < 3000; v++) { const p = postFor({ vnum: v, sector, flags, region }); if (p) { n++; states.add(p.state); } }
  return { part: n / 2000, states: [...states] };
};

test('the Vale is lit, and has the most posts', () => {
  const vale = share('vale');
  assert.deepEqual(vale.states, ['lit']);
  assert.ok(vale.part > 0.4 && vale.part < 0.6, `about every second room (${vale.part})`);
  for (const r of regions) if (r !== 'vale') assert.ok(share(r).part < vale.part, `${r} has fewer`);
});
test('beyond the Vale the lanterns are out; where the mist rules they burn cold', () => {
  for (const r of ['marches', 'greenreach', 'stonemarch', 'frostmarch', 'sundersea']) assert.deepEqual(share(r).states, ['dark'], r);
  for (const r of ['deeproad', 'reach', 'beyond']) assert.deepEqual(share(r).states, ['cold'], r);
});
test('every region of the world has a rule', () => {
  for (const r of regions) assert.ok(share(r).part > 0.15, `${r} has posts`);
});
test('a peaceful room keeps its lantern lit wherever it stands, but nothing warms a cold one', () => {
  assert.deepEqual(share('marches', 'city', ['peaceful']).states, ['lit']);
  assert.deepEqual(share('reach', 'field', ['peaceful']).states, ['cold']);
});
test('no post indoors, underground, on water, in a death trap or in no region', () => {
  assert.equal(share('vale', 'inside').part, 0);
  assert.equal(share('vale', 'water_swim').part, 0);
  assert.equal(share('vale', 'field', ['indoors']).part, 0);
  assert.equal(share('vale', 'field', ['deathtrap']).part, 0);
  assert.equal(share(null).part, 0);
  assert.equal(share('nowhere').part, 0);
});
test('a room has the same post every time it is built', () => {
  assert.deepEqual(postFor({ vnum: 3005, sector: 'city', region: 'vale' }), postFor({ vnum: 3005, sector: 'city', region: 'vale' }));
});
test('the post stands on open ground near a corner, never in a narrow way', () => {
  const W = 24, H = 15;
  const open = (x, y) => x >= 1 && y >= 1 && x < W - 1 && y < H - 1;
  const c = postCell(3005, W, H, open);
  assert.ok(c && open(c.x, c.y));
  assert.ok([c.x, W - 1 - c.x].some(d => d <= 5) && [c.y, H - 1 - c.y].some(d => d <= 5), 'near a corner');
  // a corridor one cell wide has no place for it
  assert.equal(postCell(3005, W, H, (x, y) => y === 7 && x >= 1 && x < W - 1), null);
  assert.equal(postCell(3005, W, H, () => false), null);
});
