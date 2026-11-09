// The banner's words for a region of the world (hud/regionsay.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { bannerSays, levelsText } from '../../src/web_isometric/world3d/hud/regionsay.js';

const vale = { id: 'vale', name: 'The Lantern Vale', line: 'Where the lanterns still hold the mist back.', levels: [1, 10] };
const marches = { id: 'marches', name: 'The Marches', line: 'The road, and the keeps that were raised to guard it.', levels: [8, 20] };

test('arriving: the region is named and its line said', () => {
  assert.deepEqual(bannerSays('Garathorm Inner City', vale, null), { region: 'The Lantern Vale', line: vale.line });
});
test('another zone of the same region: named, the line not said again', () => {
  assert.deepEqual(bannerSays('Plains', vale, 'vale'), { region: 'The Lantern Vale', line: '' });
});
test('crossing into another region: its line is said', () => {
  assert.deepEqual(bannerSays('Trade Road', marches, 'vale'), { region: 'The Marches', line: marches.line });
});
test("a room's own banner, and a zone in no region, say nothing of regions", () => {
  assert.deepEqual(bannerSays('', vale, null), { region: '', line: '' });
  assert.deepEqual(bannerSays('God Rooms', null, 'vale'), { region: '', line: '' });
});
test("a region's levels for the map", () => {
  assert.equal(levelsText(marches), 'levels 8–20');
  assert.equal(levelsText(null), '');
  assert.equal(levelsText({ name: 'x' }), '');
});
