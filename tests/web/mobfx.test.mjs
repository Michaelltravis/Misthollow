// A creature's own abilities in /play (world3d/mobfx-hand.js, mobfx.js), checked against what the
// server can send (tests/web/fixtures/mobfx.json, written by tools/dump_mobfx.py) without a
// running server.
//   node --test tests/web/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { MOB_RECIPES } from '../../src/web_isometric/world3d/mobfx-hand.js';
import { MOB_TABLE } from '../../src/web_isometric/world3d/mobfx-table.js';
import { familyOf, mobRecipe, TABLES } from '../../src/web_isometric/world3d/mobfx.js';
import { FAMILIES, THEMES, TELLS, validate, signature, creatureRecipe, forRank, rankOf, parse } from '../../src/web_isometric/world3d/abilityfx.js';

const SENT = JSON.parse(readFileSync(new URL('./fixtures/mobfx.json', import.meta.url))).abilities;
const CLIPS = JSON.parse(readFileSync(new URL('./fixtures/abilitybook.json', import.meta.url))).clips;

test('every everyday creature ability the server sends has a line of its own', () => {
  const missing = SENT.filter(a => !MOB_RECIPES[a.fx]).map(a => `${a.fx} (${a.from.join(', ')})`);
  assert.deepEqual(missing, []);
});

test('no hand line is left over from an ability no creature has', () => {
  const sent = new Set(SENT.map(a => a.fx));
  assert.deepEqual(Object.keys(MOB_RECIPES).filter(id => !sent.has(id)), []);
});

test('every line (hand and generated) parses and names clips the rig has, a known tell', () => {
  const bad = [];
  for (const [id, line] of [...Object.entries(MOB_RECIPES), ...Object.entries(MOB_TABLE)]) {
    const problems = validate(line, CLIPS);
    if (problems.length) bad.push(`${id}: ${problems.join(', ')}`);
    const r = parse(line);
    if (r.tell && !TELLS.includes(r.tell)) bad.push(`${id}: tell ${r.tell}`);
  }
  assert.deepEqual(bad, []);
});

test('no two creature abilities look alike', () => {
  const seen = new Map();
  for (const [id, line] of Object.entries(MOB_RECIPES)) {
    const sig = signature(line);
    assert.ok(!seen.has(sig), `${id} looks like ${seen.get(sig)} (${sig})`);
    seen.set(sig, id);
  }
});

test('a wind-up the server names but no line knows still gets a legal look by its kind', () => {
  for (const kind of ['heavy', 'aoe', 'cast', 'debuff', 'heal', 'disrupt', '']) {
    for (const fam of [...Object.keys(FAMILIES), 'creature']) {
      const r = creatureRecipe(TABLES, `nothing_called_${kind}`, fam, { k: 'resolve', kind });
      assert.equal(r.known, false);
      assert.ok(r.clip, `${kind}/${fam} has a body`);
    }
  }
});

test('families: a creature leaves its kind\'s marks, its colours stay its school\'s', () => {
  assert.equal(familyOf({ beast: { body: 'wolf', mob: 'wolf' } }, { name: 'wolf' }), 'beast');
  assert.equal(familyOf({ beast: { body: 'spider', proc: 'spider' } }, { name: 'spider' }), 'insect');
  assert.equal(familyOf({ beast: { mob: 'ghost', body: 'elemental' } }, { name: 'fire elemental' }), 'elemental');
  assert.equal(familyOf({ model: 'skeleton_warrior', why: 'undead' }, { name: 'skeleton' }), 'undead');
  assert.equal(familyOf({ model: 'mage' }, { short: 'a goblin shaman' }), 'caster');
  assert.equal(familyOf({ model: 'knight', flat: true }, { name: 'golem' }), 'construct');
  assert.equal(familyOf({ model: 'barbarian' }, { short: 'an antelope herder' }), 'creature', 'no prefix matches (ant, imp)');
  for (const [fam, t] of Object.entries(FAMILIES)) {
    assert.ok(!THEMES[fam], `${fam} is not a class`);
    for (const k of ['glyph', 'motif', 'sigil', 'school']) assert.ok(t[k], `${fam} has a ${k}`);
  }
});

test('rank: a boss gets every flourish, an elite a little shake, an ordinary creature none', () => {
  const r = parse(MOB_RECIPES.crushing_blow);
  const boss = forRank(r, 'boss'), elite = forRank(r, 'elite'), plain = forRank(r, 'normal');
  assert.ok(boss.flags.has('shake+') && boss.flags.has('stop') && boss.land.big);
  assert.ok(elite.flags.has('shake') && !elite.flags.has('shake+') && !elite.flags.has('stop'));
  assert.ok(!['shake', 'shake+', 'stop', 'flash'].some(f => plain.flags.has(f)) && !plain.land.big && plain.calm);
  assert.ok(r.flags.has('shake+'), 'the parsed line itself is untouched');
  // a ward keeps its mark at any rank (it is how you see it is on)
  assert.ok(forRank(parse(MOB_RECIPES.ward), 'normal').aura);
  assert.equal(rankOf({ boss: true }), 'boss');
  assert.equal(rankOf({ rank: 'sub-boss' }), 'elite');
  assert.equal(rankOf({ rank: 'elite' }), 'elite');
  assert.equal(rankOf({}), 'normal');
});

test('mobRecipe: a creature on screen gets its family once, and its rank\'s cut', () => {
  const ent = { look: { beast: { body: 'troll', mob: 'troll' } }, data: { name: 'troll', boss: true } };
  const r = mobRecipe('crushing_blow', { ent, mob: true }, {});
  assert.equal(ent.family, 'beast');
  assert.equal(r.cls, 'beast');
  assert.ok(r.known && r.flags.has('shake+'));
  const plain = mobRecipe('crushing_blow', { ent: { look: {}, data: { name: 'thug' } }, mob: true }, {});
  assert.ok(!plain.flags.has('shake+'));
});
