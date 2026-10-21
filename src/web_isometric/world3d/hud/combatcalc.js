// The character sheet's combat calculator: what a fight with a creature comes to, worked the way
// the server works a round (combat.py one_round, bonus_attack, offhand_attack; Player.take_damage,
// Mobile.take_damage). `me` is the map payload's player.combat block (map_system._combat_sheet);
// a foe is { level, ac, hit, min, max, hp, pb, boss, kind }. Averages treat a blow's damage as even
// across its range; nothing here changes the character.

// a d20 plus `hit` reaching `need` (no natural 1 or 20)
export const landChance = (hit, need) => Math.max(0, Math.min(20, 21 - Math.max(1, need - hit))) / 20;
// what a blow's d20 + hit must reach against this armour (lower is better)
export const defenseOf = ac => 10 - Math.floor(ac / 10);
// Python's round(): halves go to the even neighbour
const pyRound = x => { const f = Math.floor(x), d = x - f; return d > 0.5 ? f + 1 : d < 0.5 ? f : (f % 2 ? f + 1 : f); };
const range = (lo, hi) => { const out = []; for (let d = Math.max(0, lo); d <= Math.max(lo, hi); d++) out.push(d); return out; };
const mean = xs => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0;

// A creature of this level as its zone leaves it when it says nothing (mobs.py from_prototype):
// attributes 10 + level/5, armour 100 less 2 a level and its dexterity, a bare-handed 1d3, health
// level d10 + 5 a level.
export function typicalFoe(level) {
  const L = Math.max(1, Math.floor(level) || 1), s = Math.floor(L / 5), dam = Math.floor(L / 3) + Math.floor(s / 2);
  return { level: L, ac: 100 - 2 * L - Math.floor(s / 2) * 10, hit: Math.floor(L / 2) + Math.floor(s / 2) + Math.floor(s / 4),
    min: 1 + dam, max: 3 + dam, hp: Math.round(L * 10.5), pb: 0, boss: false, kind: 'physical' };
}

// what one of your landed blows takes from the foe: a boss loses no more than a tenth of its
// health to one swing, then its own damage reduction
export function dealt(d, foe, me) {
  if (foe.boss && foe.maxHp) d = Math.min(d, Math.max(1, Math.floor(foe.maxHp * (me.boss_cap ?? 0.1))));
  if (foe.pb > 0 && d > 0) d = Math.max(0, d - Math.max(1, Math.floor(d * foe.pb / 100)));
  return d;
}

// what a creature's blow of `raw` damage leaves you after hero toughness, the ward of its kind and
// your parry/block (PB), in the order the server takes them
export function taken(raw, me, kind = 'physical') {
  let d = raw;
  if (d <= 0) return 0;
  d = Math.max(1, pyRound(d * (1 - (me.toughness || 0) / 100)));
  const r = kind && kind !== 'physical' ? Math.min(75, (me.resist || {})[kind] || 0) : 0;
  if (r && d > 1) d = Math.max(1, Math.floor(d * (100 - r) / 100));
  if (me.pb > 0 && d > 0) d = Math.max(0, d - Math.max(1, Math.floor(d * me.pb / 100)));
  return d;
}

// the chance a creature's swing gets past dodge, parry, shield block and evasion (tried in turn)
export function avoidChance(me) {
  const a = me.avoid || {};
  return 1 - ['dodge', 'parry', 'block', 'evasion'].reduce((p, k) => p * (1 - Math.max(0, Math.min(100, a[k] || 0)) / 100), 1);
}

export function fight(me, foe, myHp) {
  const need = defenseOf(foe.ac);
  // your swing: lands, rolls, maybe a critical
  const land = landChance(me.hit, need);
  const crit = (me.crit || 0) / 100, mult = me.crit_mult || 2;
  const rolls = range(me.min, me.max);
  const perHit = mean(rolls.map(d => (1 - crit) * dealt(d, foe, me) + crit * dealt(Math.floor(d * mult), foe, me)));
  let perRound = land * perHit;
  const extras = (me.extra || []).map(e => {
    const l = landChance(e.hit, need), avg = mean(range(e.min, e.max).map(d => dealt(d, foe, me)));
    perRound += (e.chance / 100) * l * avg;
    return { name: e.name, chance: e.chance, land: l, avg };
  });
  // its swing: past your avoidance, then your armour; softened by evasion, sometimes critical
  const avoid = avoidChance(me);
  const theirLand = (1 - avoid) * landChance(foe.hit, me.defense);
  const soft = Math.min(100, me.soften || 0) / 100, fcrit = (me.foe_crit ?? 5) / 100;
  const blow = d => {
    const one = x => (1 - fcrit) * taken(x, me, foe.kind) + fcrit * taken(x * 2, me, foe.kind);
    return (1 - soft) * one(d) + soft * one(Math.floor(d * 0.7));
  };
  const foeRolls = range(foe.min, foe.max);
  const takenPerHit = mean(foeRolls.map(blow));
  const takenPerRound = theirLand * takenPerHit;
  const toKill = perRound > 0 ? Math.ceil(Math.max(1, foe.hp) / perRound) : Infinity;
  const toFall = takenPerRound > 0 ? Math.ceil(Math.max(1, myHp) / takenPerRound) : Infinity;
  return {
    need, land, perHit, perRound, extras, crit: me.crit || 0,
    // what its landed blow would be with nothing of yours in the way (its criticals counted)
    avoid, theirLand, rawPerHit: mean(foeRolls) * (1 + fcrit), takenPerHit, takenPerRound,
    toKill, toFall, win: toKill <= toFall,
    hpLeft: Number.isFinite(toKill) ? Math.max(0, Math.round(myHp - takenPerRound * toKill)) : 0,
  };
}
