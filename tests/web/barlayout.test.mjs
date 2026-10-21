// Where the extra action bars float (world3d/barlayout.js): on screen, never over the main bar
// or each other at first, and whatever odd thing localStorage hands back falls to the defaults.
//   node --test tests/web/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { BAR_COUNT, barSize, defaultPos, clamp, parse, serialize, defaults, overlaps, slotLocked } from '../../src/web_isometric/world3d/barlayout.js';

test('a bar is kept wholly on screen', () => {
  const s = barSize(false, 1);
  assert.deepEqual(clamp({ x: -50, y: -9 }, s, 1280, 720), { x: 0, y: 0 });
  assert.deepEqual(clamp({ x: 5000, y: 5000 }, s, 1280, 720), { x: 1280 - Math.round(s.w), y: 720 - Math.round(s.h) });
  const v = barSize(true, 1);
  assert.ok(v.h > v.w, 'turned, it stands tall');
});

test('the bars first sit above the main bar, stacked, apart', () => {
  for (const [vw, vh, ui] of [[1280, 720, 0.85], [1920, 1080, 1.05], [1000, 640, 0.72]]) {
    const s = barSize(false, ui);
    const rects = Array.from({ length: BAR_COUNT }, (_, i) => ({ ...defaultPos(i, vw, vh, { ui }), w: s.w, h: s.h }));
    const main = { x: 0, y: vh - 170 * ui, w: vw, h: 170 * ui };
    for (const r of rects) {
      assert.ok(r.x >= 0 && r.y >= 0 && r.x + r.w <= vw + 1 && r.y + r.h <= vh + 1, `on screen at ${vw}x${vh}`);
      assert.ok(!overlaps(r, main), `clear of the main bar at ${vw}x${vh}`);
    }
    for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) assert.ok(!overlaps(rects[i], rects[j]), `bars ${i} and ${j} apart`);
  }
});

test('the saved layout round-trips; junk falls to the defaults', () => {
  const l = defaults();
  assert.equal(l.count, 1, 'one extra bar shows at first');
  l.count = 3;
  l.bars[1] = { x: 40.4, y: 300, vertical: true, locked: true };
  assert.deepEqual(parse(serialize(l)), { count: 3, mainLocked: false, bars: [null, { x: 40, y: 300, vertical: true, locked: true }, null] });
  for (const junk of [null, '', '{', '"x"', '[]', '{"count": 9}', '{"count": -1, "bars": "no"}', '{"bars": [{"x": "a"}]}']) {
    const p = parse(junk);
    assert.ok(p.count >= 0 && p.count <= BAR_COUNT && p.bars.length === BAR_COUNT, `junk ${junk}`);
    assert.ok(p.bars.every(b => b === null || (Number.isFinite(b.x) && Number.isFinite(b.y))));
  }
});

test('a lock on each bar, the main bar too, kept and read back', () => {
  const l = defaults();
  l.mainLocked = true;
  l.bars[1] = { x: 10, y: 20, vertical: false, locked: true };
  const back = parse(serialize(l));
  assert.equal(back.mainLocked, true);
  assert.equal(slotLocked(back, 0), true, 'the main bar');
  assert.equal(slotLocked(back, 15), true);
  assert.equal(slotLocked(back, 16), false, 'bar 3 is not locked');
  assert.equal(slotLocked(back, 24), true, 'bar 4 is');
  assert.equal(slotLocked(back, 31), true);
  assert.equal(slotLocked(back, 32), false);
  assert.equal(parse('{"count":1}').mainLocked, false, 'an old layout: unlocked');
});
