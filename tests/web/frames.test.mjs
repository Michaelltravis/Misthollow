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
