// The sky dial (world3d/hud/sky.js): the sun crosses by day, the moon by night in its phase; the
// weather has its icon, the warmth its band.   node --test tests/web/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { skyBody, weatherGlyph, tempBand, moonName, moonPath, arcPoint } from '../../src/web_isometric/world3d/hud/sky.js';
import { PICTO } from '../../src/web_isometric/world3d/hud/icons.js';
import { DRAW } from '../../src/web_isometric/world3d/glyphs.js';

test('the sun rises at six on the left, stands high at one, sets at eight; the moon has the night', () => {
  assert.deepEqual(skyBody(6), { body: 'sun', t: 0 });
  assert.equal(skyBody(13).body, 'sun');
  assert.ok(Math.abs(skyBody(13).t - 0.5) < 1e-9);
  assert.equal(skyBody(20).body, 'moon');
  assert.equal(skyBody(20).t, 0);
  assert.equal(skyBody(1).body, 'moon');
  assert.ok(skyBody(5).t > skyBody(1).t && skyBody(5).t < 1, 'the moon sets toward dawn');
  const left = arcPoint(0), top = arcPoint(0.5), right = arcPoint(1);
  assert.ok(left.x < top.x && top.x < right.x && top.y < left.y, 'the arc rises in the middle');
});

test('each sky has an icon the HUD can draw; a clear night shows the moon', () => {
  for (const sky of ['clear', 'partly_cloudy', 'overcast', 'rainy', 'stormy', 'snowy', 'foggy']) {
    for (const night of [false, true]) {
      const g = weatherGlyph({ sky }, night);
      assert.ok(PICTO[g] || DRAW[g], `${sky}${night ? ' at night' : ''}: ${g} is drawable`);
    }
  }
  assert.equal(weatherGlyph({ sky: 'clear' }, true), 'moon');
  assert.equal(weatherGlyph({ sky: 'rainy', precipitation: 'sleet' }), 'snow');
  assert.equal(weatherGlyph(null), null);
});

test('warmth in bands, the moon in words and in shape', () => {
  assert.deepEqual([10, 40, 65, 85, 100].map(tempBand), ['frigid', 'cold', 'mild', 'warm', 'hot']);
  assert.equal(moonName(0), 'New moon');
  assert.equal(moonName(0.5), 'Full moon');
  assert.equal(moonName(0.25), 'First quarter');
  for (const p of [0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9]) assert.match(moonPath(p), /^M0,-6 A6,6 0 0 [01] 0,6 A[\d.]+,6 0 0 [01] 0,-6Z$/);
});

test('the minimap has the dial in place of its hour; the old time line is gone from it', async () => {
  const fs = await import('node:fs');
  const html = fs.readFileSync(new URL('../../src/web_isometric/world3d/play.html', import.meta.url), 'utf8');
  const mm = html.slice(html.indexOf('<div id="minimap"'), html.indexOf('<div id="actionbar"'));
  assert.match(mm, /class="mm-sky"/);
  assert.doesNotMatch(mm, /mm-time/);
});
