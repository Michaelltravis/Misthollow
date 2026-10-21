// The character sheet's combat calculator (world3d/hud/combatcalc.js) works a blow the way the
// server does (combat.py one_round; Player.take_damage; Mobile.take_damage).
//   node --test tests/web/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { landChance, defenseOf, typicalFoe, taken, dealt, avoidChance, fight } from '../../src/web_isometric/world3d/hud/combatcalc.js';

const ME = {
  hit: 8, damroll: 3, min: 6, max: 12, crit: 10, crit_mult: 2, extra: [],
  ac: 40, defense: 6, avoid: { dodge: 10, parry: 0, block: 0, evasion: 0 },
  toughness: 18.5, pb: 10, resist: { fire: 40, frost: 0 }, soften: 0, foe_crit: 5, boss_cap: 0.1, round_secs: 3,
};

test('a d20 against armour, as one_round rolls it', () => {
  assert.equal(defenseOf(100), 0);
  assert.equal(defenseOf(-35), 14, 'floor division, as Python: -35 // 10 is -4');
  assert.equal(landChance(0, 11), 0.5, 'an 11 needed: ten faces of twenty');
  assert.equal(landChance(5, 1), 1, 'no natural 1 misses');
  assert.equal(landChance(0, 20), 0.05);
  assert.equal(landChance(0, 21), 0, 'and no natural 20 hits');
});

test('a typical creature is what mobs.py makes of a zone that says nothing', () => {
  const f = typicalFoe(20);       // str/dex 14: hit 10 + 2 + 1, armour 60 - 20, damage 1d3 + 6 + 2
  assert.deepEqual([f.ac, f.hit, f.min, f.max, f.hp], [40, 13, 9, 11, 210]);
  assert.equal(typicalFoe(1).ac, 98);
});

test('a creature blow: toughness, then the ward of its kind, then PB', () => {
  assert.equal(taken(20, ME), 15, '20 x 0.815 -> 16; PB takes at least one');
  assert.equal(taken(20, ME, 'fire'), 8, '16; fire 40% -> 9; PB one more');
  assert.equal(taken(20, ME, 'frost'), 15, 'no frost ward');
  assert.equal(taken(20, { ...ME, resist: { fire: 99 } }, 'fire'), 3, 'wards stop at 75%: 16 -> 4; PB one more');
  assert.equal(taken(1, ME), 0, 'a scratch: toughness leaves 1, PB takes it');
});

test('your blow on a boss is capped at a tenth of its health, then its absorb', () => {
  const boss = { boss: true, maxHp: 500, pb: 20 };
  assert.equal(dealt(200, boss, ME), 40, 'capped to 50, absorb 20% takes 10');
  assert.equal(dealt(30, { pb: 0 }, ME), 30);
});

test('avoidance is tried in turn', () => {
  assert.equal(avoidChance({ avoid: { dodge: 50, parry: 50 } }), 0.75);
  assert.equal(avoidChance({ avoid: {} }), 0);
});

test('a fight, worked both ways', () => {
  const foe = { level: 10, ac: 80, hit: 5, min: 4, max: 4, hp: 100, pb: 0, boss: false, kind: 'physical' };
  const r = fight(ME, foe, 120);
  assert.equal(r.need, 2);
  assert.equal(r.land, 1);
  assert.ok(Math.abs(r.perHit - 9 * 1.1) < 1e-9, 'damage 6..12 averages 9; criticals add a tenth');
  assert.equal(r.toKill, Math.ceil(100 / r.perRound));
  // it: lands 0.9 x (21 - 1)/20; 4 -> toughness 3 -> PB 2; a critical 8 -> 7 -> 6
  assert.ok(Math.abs(r.theirLand - 0.9) < 1e-9);
  assert.ok(Math.abs(r.takenPerHit - (0.95 * 2 + 0.05 * 6)) < 1e-9);
  assert.ok(Math.abs(r.rawPerHit - 4 * 1.05) < 1e-9, 'struck: its blow with its criticals, before your defences');
  assert.equal(r.win, true);
  // extra swings add their share
  const two = fight({ ...ME, extra: [{ name: 'Second attack', chance: 50, hit: 8, min: 6, max: 12 }] }, foe, 120);
  assert.ok(Math.abs(two.perRound - (r.perRound + 0.5 * 9)) < 1e-9);
  // a blow that can never land never kills
  assert.equal(fight({ ...ME, hit: -40 }, foe, 120).toKill, Infinity);
});
