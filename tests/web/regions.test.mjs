// The banner's words for a region of the world (hud/regionsay.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { bannerSays, levelsText, mapSays } from '../../src/web_isometric/world3d/hud/regionsay.js';

const vale = { id: 'vale', name: 'The Lantern Vale', line: 'Where the lanterns still hold the mist back.', levels: [1, 10] };
const marches = { id: 'marches', name: 'The Marches', line: 'The road, and the keeps that were raised to guard it.', levels: [8, 20] };

test('arriving: the region is named and its line said', () => {
  assert.deepEqual(bannerSays('Garathorm Inner City', vale, null), { region: 'The Lantern Vale', line: vale.line, danger: false });
});
test('another zone of the same region: named, the line not said again', () => {
  assert.deepEqual(bannerSays('Plains', vale, 'vale'), { region: 'The Lantern Vale', line: '', danger: false });
});
test('crossing into another region: its line is said', () => {
  assert.deepEqual(bannerSays('Trade Road', marches, 'vale'), { region: 'The Marches', line: marches.line, danger: false });
});
test("a room's own banner, and a zone in no region, say nothing of regions", () => {
  assert.deepEqual(bannerSays('', vale, null), { region: '', line: '', danger: false });
  assert.deepEqual(bannerSays('God Rooms', null, 'vale'), { region: '', line: '', danger: false });
});
test("a region's levels for the map", () => {
  assert.equal(levelsText(marches), 'levels 8–20');
  assert.equal(levelsText(null), '');
  assert.equal(levelsText({ name: 'x' }), '');
});

test("a zone far beyond the hero says so, in the place of the region's line", () => {
  const far = bannerSays('The Necropolis of Eternal Night', vale, null, { zone: 31, hero: 6 });
  assert.ok(far.danger && /beyond you/.test(far.line) && /31/.test(far.line));
  assert.equal(far.region, 'The Lantern Vale');
  const near = bannerSays('Plains', vale, null, { zone: 8, hero: 6 });
  assert.ok(!near.danger && near.line === vale.line, 'a zone within reach says the region as before');
  assert.ok(!bannerSays('Plains', vale, 'vale', { zone: 13, hero: 6 }).danger, 'seven levels over is not yet beyond');
  assert.ok(bannerSays('Plains', vale, 'vale', { zone: 14, hero: 6 }).danger, 'eight is');
  assert.ok(!bannerSays('Plains', vale, null, { zone: null, hero: 6 }).danger, 'a zone with no creatures warns of nothing');
  assert.ok(bannerSays('God Rooms', null, null, { zone: 40, hero: 2 }).danger, 'with or without a region');
});

test('the map says a region, its levels, and a zone that lies outside them', () => {
  const marches = { id: 'marches', name: 'The Marches', levels: [8, 20] };
  assert.equal(mapSays(marches, 14), 'The Marches · levels 8–20');
  assert.equal(mapSays(marches, 25), 'The Marches · levels 8–20 · here about level 25');
  assert.equal(mapSays(marches, null), 'The Marches · levels 8–20');
  assert.equal(mapSays(null, 40), 'about level 40');
  assert.equal(mapSays(null, null), '');
});
