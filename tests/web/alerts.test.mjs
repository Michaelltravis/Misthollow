// What waits and what is going on (world3d/hud/alerts.js): unread mail, world events counting
// down, a quest's step as a toast.   node --test tests/web/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fmtLeft, chipOf, progressText } from '../../src/web_isometric/world3d/hud/alerts.js';
import { PICTO } from '../../src/web_isometric/world3d/hud/icons.js';
import { DRAW } from '../../src/web_isometric/world3d/glyphs.js';

test('time left, short', () => {
  assert.equal(fmtLeft(45), '45s');
  assert.equal(fmtLeft(720), '12m');
  assert.equal(fmtLeft(3900), '1h 5m');
  assert.equal(fmtLeft(-5), '0s');
});

test('a world event is a chip that counts down from when it was told', () => {
  const inv = chipOf({ kind: 'invasion', label: 'Invasion', where: 'Midgaard', left: 600, wave: 2, waves: 5 }, 60);
  assert.equal(inv.left, 540);
  assert.equal(inv.text, '9m');
  assert.equal(inv.sub, 'Midgaard · wave 2/5 · 9m left');
  assert.equal(chipOf({ kind: 'double_xp', label: 'Double experience', left: 30 }, 0).sub, '30s left');
  assert.equal(chipOf({ kind: 'double_xp', left: 30 }, 40).left, 0, 'an event run out shows no time');
  for (const kind of ['invasion', 'world_boss', 'treasure_hunt', 'double_xp', 'weather', 'other']) {
    const { icon } = chipOf({ kind, left: 1 });
    assert.ok(PICTO[icon] || DRAW[icon], `${kind}: ${icon} is drawable`);
  }
  assert.ok(PICTO.envelope, 'the envelope is drawable');
});

test("a quest's step reads as a toast", () => {
  assert.equal(progressText({ objective: 'Rats slain', current: 3, required: 5 }), 'Rats slain 3/5');
  assert.equal(progressText({ objective: 'Rats slain', current: 5, required: 5, done: true }), 'Rats slain — done!');
});

test('wired: the minimap has the alerts row; main listens for events and quest steps; the envelope opens the mail', async () => {
  const fs = await import('node:fs');
  const read = p => fs.readFileSync(new URL(`../../${p}`, import.meta.url), 'utf8');
  assert.match(read('src/web_isometric/world3d/play.html'), /class="mm-alerts hidden"/);
  const main = read('src/web_isometric/world3d/main.js');
  assert.match(main, /MH\.bus\.on\('world\.event', e => alerts\.setEvents\(e\.events\)\)/);
  assert.match(main, /MH\.bus\.on\('quest\.progress'/);
  assert.match(main, /openMail: \(\) => hud\.openPanel\('mail'\)/);
  assert.match(read('src/web_isometric/world3d/hud/hud.js'), /name === 'mail'\) services\.show\('mail'\)/);
});
