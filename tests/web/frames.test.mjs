// The server's telnet frames, drawn in /play's dress (world3d/hud/frames.js).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { classify, framed, renderBox, formatLines, noteKind } from '../../src/web_isometric/world3d/hud/frames.js';

const L = t => ({ text: t, html: t.replace(/&/g, '&amp;').replace(/</g, '&lt;') });

test('rules, headings on rules, rows and plain lines', () => {
  for (const r of ['╔══════════╗', '╚══════════╝', '╠══════════╣', '+====================+', '+--------------------+', '══════════', '----------', '=========='])
    assert.equal(classify(r).t, 'rule', r);
  assert.deepEqual(classify('═══════ QUEST COMPLETE: The Rat ═══════'), { t: 'titled', title: 'QUEST COMPLETE: The Rat' });
  assert.equal(classify('---- Spells ----').title, 'Spells');
  assert.equal(classify('║ TUTORIAL COMPLETE: Awakening ║').t, 'row');
  assert.equal(classify('  |  *NPC* Notable figure encountered!  |').t, 'row');
  for (const t of ['You gain 50 experience!', 'Sage Aldric says, "Welcome."', 'A sword - 50 gold', 'Exits: north | south', '-- the end --x'])
    assert.equal(classify(t).t === 'rule' || classify(t).t === 'row', false, t);
});

test('the tutorial box and the journal discovery box are banners, frame and all gone', () => {
  const tut = renderBox(['╔══════════════════════════════╗', '║ TUTORIAL COMPLETE: Awakening ║', '╚══════════════════════════════╝'].map(L));
  assert.match(tut, /class="tx-banner"/);
  assert.match(tut, /tx-banner-t">TUTORIAL COMPLETE: Awakening</);
  assert.doesNotMatch(tut, /[╔║═]/);
  const npc = renderBox(['  +' + '='.repeat(54) + '+', '  |  *NPC* Notable figure encountered!  |', '  +' + '-'.repeat(54) + '+', '  |      Sage Aldric      |', '  +' + '='.repeat(54) + '+'].map(L));
  assert.match(npc, /tx-banner-t">Notable figure encountered!</);
  assert.match(npc, /tx-banner-s">Sage Aldric</);
  assert.doesNotMatch(npc.replace(/<[^>]*>/g, ''), /\*NPC\*|[+|=]/);
});

test('a score sheet is a panel: rows in step, inner rules hairlines, the frame gone', () => {
  const W = 30;
  const lines = ['╔' + '═'.repeat(W) + '╗', '║ Gauntlet the Novice          ║', '╠' + '═'.repeat(W) + '╣', '║ Race: Human   Class: Warrior ║',
    '║ HP: 20/20     Mana: 10/10    ║', '║ Str: 14  Int: 10  Wis: 11    ║', '╚' + '═'.repeat(W) + '╝'].map(L);
  const html = renderBox(lines);
  assert.match(html, /^<div class="tx-panel">/);
  assert.equal((html.match(/class="tx-row"/g) || []).length, 4);
  assert.equal((html.match(/class="tx-sep"/g) || []).length, 1);
  assert.doesNotMatch(html, /[╔╗╚╝╠╣═║]/);
  assert.match(html, /Race: Human {3}Class: Warrior/, 'the spacing that keeps it in step stays');
});

test("a table's column bars stay, faint; the ansi colours round them are kept", () => {
  const row = { text: '║ Sword │ 50 gold ║', html: '<span class="ansi-cyan">║</span> Sword <span class="ansi-cyan">│</span> 50 gold <span class="ansi-cyan">║</span>' };
  const html = renderBox([L('╔══════════════════╗'), row, L('║ Shield │ 30 gold║'), L('║ Helm │ 20 gold  ║'), L('║ Boots │ 9 gold  ║'), L('╚══════════════════╝')]);
  assert.match(html, /tx-panel/);
  assert.match(html, /<span class="ansi-cyan"><span class="tx-bar">│<\/span><\/span>/);
  assert.equal((html.match(/║/g) || []).length, 0);
});

test('a reply at once: boxes gathered, a title between rules a heading, plain lines kept', () => {
  const out = formatLines(['Objective complete!', '╔════════════╗', '║ TUTORIAL COMPLETE ║', '╚════════════╝', 'You gain 50 experience!',
    '======', 'HELP: SCORE', '======', 'Shows your stats.'].map(L));
  assert.deepEqual(out.map(o => o.box), [false, true, false, true, false]);
  assert.match(out[1].html, /tx-banner/);
  assert.match(out[3].html, /tx-head">HELP: SCORE</);
  assert.ok(framed('╚════════════╝') && framed('║ x ║') && !framed('hello'));
});

test('a talk reply tells what happened to you apart from what they say', () => {
  assert.equal(noteKind('You gain 50 experience!'), 'reward');
  assert.equal(noteKind('You receive 10 gold!'), 'reward');
  assert.equal(noteKind('Quest accepted: Eyes Open'), 'quest');
  assert.equal(noteKind('Tutorial step: Visit the Temple Fountain'), 'quest');
  assert.equal(noteKind('Objective complete!'), 'quest');
  assert.equal(noteKind('Sage Aldric says, "Go well."'), '');
});

test('a telnet progress bar is a meter of the same width', async () => {
  const { meters } = await import('../../src/web_isometric/world3d/hud/frames.js');
  const html = meters('Strike  [<span class="g">█████</span>░░░░░]  50%');
  assert.match(html, /class="tx-meter" style="width:12ch"><i style="width:50%">/);
  assert.match(html, /50%$/);
  assert.equal(meters('[level 4]'), '[level 4]', 'brackets that are not a bar stay');
  assert.equal(meters('[ ]'), '[ ]');
});

test("a bar without brackets is a meter too; a map's lone path bar is not a box", async () => {
  const { meters, classify, formatLines } = await import('../../src/web_isometric/world3d/hud/frames.js');
  assert.match(meters('Rage: ░░░░░░░░░░ 0/100'), /tx-meter" style="width:10ch"><i style="width:0%"/);
  assert.match(meters('Rage: ██████░░░░ 60/100'), /width:60%/);
  assert.equal(meters('a ░░ b'), 'a ░░ b', 'two cells are not a bar');
  assert.equal(classify('    |    ').t, 'text');
  assert.equal(classify('   ?@-! ?~-?').t, 'text');
  assert.match(formatLines([{ text: 'Rep [██░░░░]', html: 'Rep [██░░░░]' }])[0].html, /tx-meter/, 'a whole reply turns its bars into meters too');
});

test('the talk window: their words, notes of what happened to you, banners; quiet when they say nothing', async () => {
  const { talkHtml } = await import('../../src/web_isometric/world3d/hud/talk.js');
  const html = talkHtml(['Sage Aldric says, "Well met."', 'Objective complete!', '╔════════════╗', '║ TUTORIAL COMPLETE ║', '╚════════════╝', 'You gain 50 experience!']);
  assert.match(html, /^<p>Sage Aldric says/);
  assert.match(html, /<p class="tx-note quest">Objective complete!<\/p>/);
  assert.match(html, /tx-banner-t">TUTORIAL COMPLETE</);
  assert.match(html, /<p class="tx-note reward">You gain 50 experience!<\/p>/);
  const quiet = talkHtml(['New in your journal: guildmaster (notable figure encountered)']);
  assert.match(quiet, /^<p class="tk-quiet">They have nothing to say\.<\/p><p class="tx-note journal">/);
});

test('a list set in columns with spaces is drawn fixed-width; prose is not', async () => {
  const { classify, formatLines } = await import('../../src/web_isometric/world3d/hud/frames.js');
  for (const t of ['  horse         2000 gold  A reliable riding horse.', '  Autoattack    OFF', 'absolution    accept    account', '  Bash          50%'])
    assert.equal(classify(t).t, 'cols', t);
  for (const t of ['Your abilities grow as you use them.  Your trainer teaches the rest.', 'Available for purchase:', 'You are carrying:', 'A sentence  with  odd spacing in a very long first part of the line that goes on'])
    assert.notEqual(classify(t).t, 'cols', t);
  const out = formatLines(['Available for purchase:', '  horse   2000 gold', '  pony    900 gold', 'Done.'].map(t => ({ text: t, html: t })));
  assert.deepEqual(out.map(o => o.box), [false, true, false]);
  assert.match(out[1].html, /^<div class="tx-cols"><div>  horse   2000 gold<\/div><div>  pony    900 gold<\/div><\/div>$/);
});

test("a line's leading prompt goes and the rest stays; an indented line amid a list is one of its rows", async () => {
  const { unprompt, formatLines } = await import('../../src/web_isometric/world3d/hud/frames.js');
  const { readTalk } = await import('../../src/web_isometric/world3d/hud/talk.js');
  assert.equal(unprompt('<span class="a">20/20hp 128/128mp 158/158mv&gt; </span>the pilgrim leaves north.'), '<span class="a"></span>the pilgrim leaves north.');
  assert.equal(unprompt('the pilgrim leaves north.'), 'the pilgrim leaves north.');
  assert.deepEqual(readTalk("You greet the waiter.\n20/20hp 9/9mp 9/9mv> waiter says, 'Welcome!'").says, ["waiter says, 'Welcome!'"]);
  const out = formatLines(['  horse      2000 gold', '  manabound_gryphon A gryphon bound', '  pony       900 gold'].map(t => ({ text: t, html: t })));
  assert.equal(out.length, 1, 'one block, the single-spaced row in it');
});

test("the shop names an item's kind as a player says it", async () => {
  const { typeName } = await import('../../src/web_isometric/world3d/hud/shop.js');
  assert.equal(typeName('drinkcon'), 'drink');
  assert.equal(typeName('food'), 'food');
  assert.equal(typeName('magic_item'), 'magic item');
  assert.equal(typeName(undefined), '');
});

test("a mount for sale says its speed once", async () => {
  const { forSale } = await import('../../src/web_isometric/world3d/hud/stable.js');
  assert.equal(forSale({ description: 'A reliable riding horse. +35% speed.', travel: 35 }), 'A reliable riding horse. +35% speed.');
  assert.equal(forSale({ description: 'A reliable donkey.', travel: 15 }), 'A reliable donkey. · +15% speed');
  assert.equal(forSale({ description: 'A griffin. +60% speed, and it flies.', travel: 60, can_fly: true }), 'A griffin. +60% speed, and it flies.');
});

test("a label and its value set apart is a row; a status strung with ' | ' is a phrase", async () => {
  const { classify } = await import('../../src/web_isometric/world3d/hud/frames.js');
  assert.equal(classify('Level 11:      23,140 XP').t, 'cols');
  assert.equal(classify('Threat: DEADLY  |  Level: 10 vs You 1  |  XP: suicide').t, 'text');
  assert.equal(classify('Current streak: 1 days').t, 'text');
  assert.equal(classify('Note:  this sentence is a long explanation that goes on and on').t, 'text');
});

test("a sentence between two rules stays a sentence; a status strung with ' | ' stays prose, indented or not", async () => {
  const { formatLines, classify, isTitle } = await import('../../src/web_isometric/world3d/hud/frames.js');
  assert.ok(isTitle('Daily Login Status') && !isTitle('No players found.'));
  const out = formatLines(['══════════', 'No players found.', '══════════'].map(t => ({ text: t, html: t })));
  assert.ok(!out.some(o => /tx-head/.test(o.html)), 'no heading made of a sentence');
  assert.equal(classify('  Kills: 0  |  Rooms explored: 627  |  Secrets: 0').t, 'text');
});
