// The characters' own light (charlight.js) and the big map's opening zoom (minimap.js fitZoom).
import test from 'node:test';
import assert from 'node:assert/strict';
import { charLightFor } from '../../src/web_isometric/world3d/charlight.js';
import { fitZoom, ZOOM_MIN } from '../../src/web_isometric/world3d/hud/minimap.js';

test('characters get more of their own light the darker the place', () => {
  const day = charLightFor({ hemi: 1.15, sunI: 2.6 });
  const crypt = charLightFor({ hemi: 0.65, sunI: 0.5 });
  const dark = charLightFor({ hemi: 0.65, sunI: 0.5, darkness: 0.6 });
  assert.ok(day.light > crypt.light && crypt.light > dark.light);
  assert.ok(day.fill < crypt.fill && crypt.fill < dark.fill, 'fill grows in the dark');
  assert.ok(day.rim < crypt.rim && crypt.rim < dark.rim, 'so does the rim');
  assert.ok(day.fill <= 0.05, 'by day the sun does the work');
  assert.ok(dark.fill <= 0.2 && dark.rim <= 1.2, 'never so much that a body glows');
});

test("a boss's gloom counts as dark", () => {
  assert.ok(charLightFor({ hemi: 1, sunI: 1, gloom: 1 }).fill > charLightFor({ hemi: 1, sunI: 1 }).fill);
});

test('the big map opens on the whole zone', () => {
  const zone = cells => ({ rooms: new Map(cells.map(([cx, cy], i) => [i, { cx, cy }])) });
  const wide = zone([[0, 0], [39, 0], [0, 9]]);
  const z = fitZoom(wide, 800, 500, 37.4, 23.8, { min: ZOOM_MIN, max: 1.6 });
  assert.ok(40 * 37.4 * z <= 800 && 10 * 23.8 * z <= 500, 'all of it fits');
  assert.ok(40 * 37.4 * z > 800 * 0.8, 'and fills most of the width');
  assert.equal(fitZoom(zone([[0, 0], [1, 0]]), 800, 500, 37.4, 23.8, { min: ZOOM_MIN, max: 1.6 }), 1.6, 'a tiny zone is not blown up');
  assert.equal(fitZoom(zone([]), 800, 500, 37.4, 23.8), 1, 'no rooms: left as it is');
});
