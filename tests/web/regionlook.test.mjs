// Each region's cast over the picture (regionlook.js), against the regions the world has (world/regions.json).
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { REGION_TINT, NO_TINT, tintFor } from '../../src/web_isometric/world3d/regionlook.js';

const regions = JSON.parse(fs.readFileSync(new URL('../../world/regions.json', import.meta.url), 'utf8')).regions;

test('every region of the world has a cast, and no cast is for a region that is not', () => {
  assert.deepEqual(Object.keys(REGION_TINT).sort(), regions.map(r => r.id).sort());
});
test('a cast leans the picture, it does not repaint it', () => {
  for (const [id, t] of Object.entries(REGION_TINT)) {
    assert.equal(t.length, 3);
    for (const v of t) assert.ok(v >= 0.9 && v <= 1.1, `${id}: within a tenth of none`);
    const mean = (t[0] + t[1] + t[2]) / 3;
    assert.ok(Math.abs(mean - 1) < 0.02, `${id}: no brighter or darker overall`);
  }
});
test('no two regions look the same; the cold north is bluer than the lit Vale', () => {
  const seen = new Set(Object.values(REGION_TINT).map(t => t.join()));
  assert.equal(seen.size, Object.keys(REGION_TINT).length);
  assert.ok(REGION_TINT.frostmarch[2] > REGION_TINT.vale[2] && REGION_TINT.vale[0] > REGION_TINT.frostmarch[0]);
  assert.ok(REGION_TINT.reach[0] > REGION_TINT.reach[2], 'the Reach is ash red');
});
test('a zone in no region has no cast', () => {
  assert.deepEqual(tintFor(null), NO_TINT);
  assert.deepEqual(tintFor({ id: 'nowhere' }), NO_TINT);
  assert.deepEqual(tintFor({ id: 'vale' }), REGION_TINT.vale);
});
