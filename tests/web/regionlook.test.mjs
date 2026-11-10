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

test('Nerathis, the Drowned King, has his own body; other kings do not borrow it', async () => {
  const { beastLook } = await import('../../src/web_isometric/world3d/bestiary.js');
  const index = JSON.parse(fs.readFileSync(new URL('../../src/web_isometric/art3d/bodies/index.json', import.meta.url), 'utf8'));
  assert.equal(beastLook('Nerathis, the Drowned King').body, 'drowned_king');
  assert.equal(beastLook('the drowned king').body, 'drowned_king');
  assert.equal(index.drowned_king.kind, 'boss');
  for (const clip of ['Idle', 'Walk', 'Bite_Front', 'HitRecieve', 'Death']) assert.ok(index.drowned_king.anims.includes(clip), clip);
  assert.notEqual((beastLook('the Sewer King') || {}).body, 'drowned_king');
  assert.equal(beastLook('King Welmar'), null);
});

test("where the mist rules, open country plays the dark tune; elsewhere music is by place, as before", async () => {
  const { musicFor } = await import('../../src/web_isometric/world3d/soundtable.js');
  assert.equal(musicFor({ theme: 'field' }), 'wilds');
  assert.equal(musicFor({ theme: 'field', region: 'vale' }), 'wilds');
  for (const r of ['reach', 'deeproad', 'beyond']) assert.equal(musicFor({ theme: 'field', region: r }), 'dark', r);
  assert.equal(musicFor({ theme: 'city', region: 'reach' }), 'town', 'a town there is still a town');
  assert.equal(musicFor({ theme: 'inside', interior: 'tavern', region: 'reach' }), 'inn');
  assert.equal(musicFor({ theme: 'cave', region: 'vale' }), 'dungeon');
});

test("a region's own stone, where a zone's words name none", async () => {
  const { stoneFor, REGION_STONE } = await import('../../src/web_isometric/world3d/regionlook.js');
  assert.deepEqual(stoneFor({ id: 'frostmarch' }), { stone: 'white' });
  assert.deepEqual(stoneFor({ id: 'deeproad' }), { stone: 'black' });
  assert.deepEqual(stoneFor({ id: 'reach' }), { stone: 'red' });
  assert.equal(stoneFor({ id: 'vale' }), null, 'the Vale keeps the grey of the kit');
  assert.equal(stoneFor(null), null);
  for (const id of Object.keys(REGION_STONE)) assert.ok(regions.some(r => r.id === id), `${id} is a region`);
});
