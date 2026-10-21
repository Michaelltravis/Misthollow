// The log's kinds (hud/logkinds.js): the server marks each line (msgkind.py), the page files the
// blow-by-blow in the Combat tab and keeps it out of All unless asked.
//   node --test tests/web/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { splitByKind } from '../../src/web_isometric/world3d/hud/logkinds.js';

test('lines are grouped by their kind, in order, the marks taken out', () => {
  const g = splitByKind([
    '<i data-k="combat"></i>You hurl a massive pyroblast!',
    '<i data-k="combat"></i>Your spell does <b>456</b> damage!',
    '<i data-k="reward"></i>You gain 209 experience points!',
    'The Bone Hall',
    '<i data-k="combat"></i>a skeletal sentry looks ill from Meteor Burn.',
  ]);
  assert.deepEqual(g.map(x => x.kind), ['combat', 'reward', '', 'combat']);
  assert.equal(g[0].html, 'You hurl a massive pyroblast!\nYour spell does <b>456</b> damage!');
  assert.ok(!g.some(x => x.html.includes('data-k')), 'no mark is left in the text');
});

test('a mark after a prompt still files the line (the prompt has no newline of its own)', () => {
  const g = splitByKind(['342/343hp 363/1041mp&gt; <i data-k="combat"></i>a skeletal sentry looks ill from Meteor Burn.']);
  assert.equal(g[0].kind, 'combat');
});

test('the page hides combat lines in All unless asked, and the Combat tab shows only them and rewards', async () => {
  const fs = await import('node:fs');
  const css = fs.readFileSync(new URL('../../src/web_isometric/world3d/hud/hud.css', import.meta.url), 'utf8');
  assert.match(css, /#log\[data-tab="all"\]:not\(\.with-combat\) > div\.k-combat/);
  assert.match(css, /#log\[data-tab="combat"\] > div:not\(\.k-combat\):not\(\.k-reward\)/);
  const html = fs.readFileSync(new URL('../../src/web_isometric/world3d/play.html', import.meta.url), 'utf8');
  assert.match(html, /data-tab="combat"/);
  assert.match(html, /data-set="combattext"/);
});

test('a line the HUD draws itself (msgkind.UI) stays in All, dimmed, and groups on its own', async () => {
  const g = splitByKind(['<i data-k="ui"></i>The sun rises on the eastern horizon.', 'The Bone Hall']);
  assert.deepEqual(g.map(x => x.kind), ['ui', '']);
  const fs = await import('node:fs');
  const css = fs.readFileSync(new URL('../../src/web_isometric/world3d/hud/hud.css', import.meta.url), 'utf8');
  assert.match(css, /#log \.k-ui \{ opacity: \.5/);
  assert.doesNotMatch(css, /data-tab="all"\][^{]*\.k-ui/, 'All never hides a ui line');
});
