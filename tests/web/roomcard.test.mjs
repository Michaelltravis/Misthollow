// The room card under the minimap (world3d/hud/roomcard.js): a compass of the ways out, the kind of
// place, what holds there; the place's bite on screen.   node --test tests/web/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { compassSpokes, exitsText, roomBadges, sectorOf, envOf, breathBubbles } from '../../src/web_isometric/world3d/hud/roomcard.js';
import { PICTO } from '../../src/web_isometric/world3d/hud/icons.js';
import { DRAW } from '../../src/web_isometric/world3d/glyphs.js';

const door = (o = {}) => ({ name: 'door', label: 'oak door', state: 'closed', locked: false, broken: false, has_key: false, ...o });

test('each way out has its state; hidden ways stay unshown', () => {
  const sp = compassSpokes({
    north: { to_room: 1 }, east: { to_room: 2, door: door() }, south: { to_room: 3, door: door({ locked: true }) },
    west: { to_room: 4, door: door({ locked: true, has_key: true }) }, up: { to_room: 5, deathtrap: true },
    down: { to_room: 6, to_zone: 'The Sewers' }, northeast: { to_room: 7, hidden: true },
    southwest: { to_room: 8, door: door({ sealed: true }) }, southeast: { to_room: 9, door: door({ state: 'open' }) },
  });
  assert.deepEqual(Object.fromEntries(Object.entries(sp).map(([d, s]) => [d, s.state])),
    { north: 'open', east: 'door', south: 'locked', west: 'locked', up: 'death', down: 'zone', southwest: 'sealed', southeast: 'open' });
  assert.equal(sp.west.key, true);
  assert.equal(sp.south.key, false);
  assert.ok(!('northeast' in sp), 'a hidden way is not told');
  const t = exitsText(sp);
  assert.match(t, /^N: open/);
  assert.match(t, /W: oak door, locked \(you have the key\)/);
  assert.match(t, /Up: DEATH lies that way/);
  assert.match(t, /Down: into The Sewers/);
  assert.equal(exitsText({}), 'No way out that you can see');
});

test("the room's flags as badges; the sector as its own; each drawable", () => {
  const b = roomBadges({ flags: ['peaceful', 'dark', 'no_magic', 'no_recall', 'indoors'], sector: 'city' });
  assert.deepEqual(b.map(x => x.icon), ['dove', 'eye', 'rune', 'scroll', 'house']);
  assert.ok(b.find(x => x.icon === 'eye').off && !b.find(x => x.icon === 'dove').off);
  assert.ok(!roomBadges({ flags: ['indoors'], sector: 'inside' }).length, "indoors isn't said twice inside");
  for (const s of ['inside', 'city', 'field', 'forest', 'hills', 'mountain', 'water_swim', 'water_noswim', 'underwater', 'flying', 'desert', 'swamp', 'dungeon']) {
    const o = sectorOf(s);
    assert.ok(o && (PICTO[o.icon] || DRAW[o.icon]), `${s}: ${o && o.icon} is drawable`);
  }
  for (const x of b) assert.ok(PICTO[x.icon] || DRAW[x.icon], `${x.icon} is drawable`);
  assert.match(sectorOf('water_noswim').label, /boat/);
});

test('the bite: a burning room is hot, frozen or snow is cold (outdoors), under water is the deep', () => {
  assert.equal(envOf({ env: { burning: true } }, null).hot, true);
  assert.equal(envOf({ env: { frozen: true } }, null).cold, true);
  assert.equal(envOf({ sector: 'field', flags: [] }, { temperature: 98 }).hot, true);
  assert.equal(envOf({ sector: 'inside', flags: ['indoors'] }, { temperature: 98 }).hot, false, 'a roof keeps the sun off');
  assert.equal(envOf({ sector: 'field', flags: [] }, { sky: 'snowy', temperature: 30 }).cold, true);
  assert.equal(envOf({ sector: 'underwater' }, null).under, true);
  assert.deepEqual(envOf({ sector: 'field', flags: [] }, { temperature: 65, sky: 'clear' }), { under: false, hot: false, cold: false });
});

test('a held breath is a row of bubbles; none when breathing freely', () => {
  assert.equal(breathBubbles(null), null);
  const b = breathBubbles({ left: 3, max: 10 });
  assert.equal(b.length, 10);
  assert.equal(b.filter(x => x.full).length, 3);
});

test('the minimap holds the card; the screen has the bite, the breath and the corruption', async () => {
  const fs = await import('node:fs');
  const html = fs.readFileSync(new URL('../../src/web_isometric/world3d/play.html', import.meta.url), 'utf8');
  for (const id of ['class="mm-card"', 'class="mm-badges"', 'id="env-vignette"', 'id="breath"', 'id="corruption"']) assert.ok(html.includes(id), id);
});
