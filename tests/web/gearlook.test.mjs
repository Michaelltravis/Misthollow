// Heroes dressed in what they wear (world3d/gearlook.js plans, procgear.js shapes) against the
// equipment kit's manifest (art3d/chars/equip.json).   node --test tests/web/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { planLook, swingClips, starterLook, kitIndex, CLASS_BASE, PROC, rangedBlow, SEX_BUILD, STAFF_PIECE, PROC_PIECE } from '../../src/web_isometric/world3d/gearlook.js';
import { buildProc, buildAddon, SHAPES, ADDONS, MOTIFS, HANGING } from '../../src/web_isometric/world3d/procgear.js';

const ART = path.join(path.dirname(fileURLToPath(import.meta.url)), '../../src/web_isometric/art3d');
const kit = kitIndex(JSON.parse(fs.readFileSync(path.join(ART, 'chars/equip.json'), 'utf8')));
const CLASSES = Object.keys(CLASS_BASE);
const names = plan => plan.props.map(p => p.name);
const torso = plan => names(plan).find(n => n.endsWith('-Body'));

test("every class's starting look keeps its silhouette, and every piece it names is in the kit", () => {
  for (const cls of CLASSES) {
    const plan = planLook(starterLook(cls), cls, kit);
    assert.equal(torso(plan), `${CLASS_BASE[cls].model}-Body`, cls);
    for (const n of names(plan)) assert.ok(kit.pieces[n], `${cls}: ${n} is in the kit`);
    for (const pr of plan.procs) { assert.ok(SHAPES[pr.shape], `${cls}: ${pr.shape} can be built`); assert.ok(kit.pieces[pr.piece], `${pr.piece} lends its mount`); }
    const parts = names(plan).filter(n => /-(Head|HeadHooded|Body|ArmLeft|ArmRight|LegLeft|LegRight)$/.test(n));
    assert.equal(parts.length, 6, `${cls}: a whole body (${parts})`);
  }
});

test('armour two steps from the class changes the body; one step does not', () => {
  assert.equal(torso(planLook({ v: 1, sig: 'a', body: { w: 3, m: 'steel', t: 2 } }, 'mage', kit)), 'knight-Body', 'a mage in plate');
  assert.equal(torso(planLook({ v: 1, sig: 'b', body: { w: 0, c: 'red', t: 2 } }, 'warrior', kit)), 'mage-Body', 'a warrior in robes');
  assert.equal(torso(planLook({ v: 1, sig: 'c', body: { w: 3, m: 'steel', t: 2 } }, 'warrior', kit)), 'barbarian-Body', 'a warrior in plate stays a warrior');
  const legs = planLook({ v: 1, sig: 'd', body: { w: 0, t: 1 }, legs: { w: 3, m: 'iron', t: 1 } }, 'mage', kit);
  assert.ok(names(legs).includes('knight-LegLeft') && torso(legs) === 'mage-Body', 'plate greaves under robes');
});

test('a hood, a helm, a hat: the head', () => {
  assert.ok(names(planLook(starterLook('ranger'), 'ranger', kit)).includes('rogue-HeadHooded'), 'a ranger goes hooded');
  const helmed = names(planLook({ v: 1, sig: 'e', head: { k: 'helm', m: 'iron', t: 1 } }, 'ranger', kit));
  assert.ok(helmed.includes('rogue-Head') && helmed.includes('knight-Knight_Helmet'), 'a helmed ranger shows a face and a helm');
  assert.ok(names(planLook({ v: 1, sig: 'f', head: { k: 'hat', c: 'blue', t: 1 } }, 'mage', kit)).includes('mage-Mage_Hat'));
  const bare = names(planLook({ v: 1, sig: 'g', body: { w: 2, m: 'iron', t: 1 } }, 'warrior', kit));
  assert.ok(!bare.some(n => /Helmet|Hat|Cape/.test(n)), 'nothing worn, nothing drawn');
});

test('colours follow the gear: material, tier, cloth, set', () => {
  const remapOf = (plan, name) => plan.props.find(p => p.name === name).remap;
  const col = name => kit.col(name);
  const steel = remapOf(planLook({ v: 1, sig: 'h', body: { w: 3, m: 'gold', t: 3 } }, 'paladin', kit), 'knight-Body');
  assert.ok(Object.values(steel).includes(col('gold')) && Object.values(steel).includes(col('gold~dark')), 'gold plate is gold');
  const worn = remapOf(planLook({ v: 1, sig: 'i', body: { w: 2, m: 'iron', t: 0 } }, 'paladin', kit), 'knight-Body');
  assert.ok(Object.values(worn).includes(col('iron~worn')), 'tier 0 is worn');
  const set = remapOf(planLook({ v: 1, sig: 'j', back: { k: 'cloak', v: 'knight', s: 'chaos_weave', t: 3 } }, 'paladin', kit), 'knight-Knight_Cape');
  assert.ok(Object.values(set).includes(col('set_chaos_weave')), 'a set cloak in the set colours');
  const cls = remapOf(planLook(starterLook('cleric'), 'cleric', kit), 'knight-Body');
  assert.ok(Object.values(cls).some(c => kit.columns[c].name.startsWith('class_cleric')), "no colour of its own: the class's");
  // every remap points at a column that exists, and the authored ramps have their variants
  for (const cls2 of CLASSES) for (const p of planLook(starterLook(cls2), cls2, kit).props) for (const to of Object.values(p.remap || {})) assert.ok(kit.columns[to], `${cls2} ${p.name} -> ${to}`);
  for (const m of ['steel', 'iron', 'gold', 'mithril', 'red', 'class_mage', 'set_frostlords_mantle']) for (const v of ['', '~worn', '~dark', '~worn~dark']) {
    if (/~dark/.test(v) && !/steel|iron|gold|mithril|red|class|set/.test(m)) continue;
    assert.ok(kit.col(m + v) != null, `${m + v} in the palette`);
  }
});

test('the swing follows the hand: two hands, two blades, a bow, a staff, nothing', () => {
  assert.ok(swingClips({ main: { k: 'sword', h: 2 } }, 'paladin', false).every(c => c.startsWith('2H_Melee')));
  assert.ok(swingClips({ main: { k: 'dagger', h: 1 }, off: { k: 'dagger', h: 1 } }, 'thief', false).every(c => c.startsWith('Dualwield')));
  assert.ok(swingClips({ main: { k: 'sword', h: 1 }, off: { k: 'shield' } }, 'warrior', false).every(c => c.startsWith('1H_Melee')));
  assert.deepEqual(swingClips({ main: { k: 'bow', h: 2 } }, 'ranger', true), ['2H_Ranged_Shoot']);
  assert.deepEqual(swingClips({ main: { k: 'sword', h: 1 } }, 'ranger', true), ['Throw'], 'a ranger with no bow throws');
  assert.deepEqual(swingClips({ main: { k: 'staff', h: 2 } }, 'mage', true), ['Spellcast_Shoot']);
  assert.ok(swingClips({}, 'warrior', false).every(c => c.startsWith('Unarmed')));
  assert.equal(planLook({ v: 1, sig: 'k', main: { k: 'axe', h: 2, m: 'steel', t: 1 } }, 'warrior', kit).idle, '2H_Melee_Idle');
});

// what a role of a built-in-code piece is painted with (as equip.js PROC_PAINT)
const PAINT = { wood: 'wood', wood_dark: 'wood_dark', wood_pale: 'wood_pale', metal: 'steel', metal_dark: 'steel~dark', leather: 'leather',
  string: 'white', hole: 'black', gem: 'gem_red', bone: 'bone', cloth: 'red', gold: 'gold', trim: 'gold', accent: 'white' };
const paint = role => { assert.ok(PAINT[role], `a role equip.js can paint: ${role}`); return (kit.col(PAINT[role]) + 0.5) / kit.N; };
function whole(g, what) {
  const verts = g.position.length / 3;
  assert.ok(verts > 10 && verts < 3000, `${what}: ${verts} vertices`);
  assert.ok(g.index.every(i => i < verts), `${what}: indices in range`);
  assert.ok([...g.position, ...g.normal, ...g.uv].every(Number.isFinite), `${what}: finite`);
  for (let i = 0; i < g.uv.length; i += 2) {
    const c = g.uv[i] * kit.N - 0.5;
    assert.ok(Math.abs(c - Math.round(c)) < 1e-4 && kit.columns[Math.round(c)], `${what}: u on a column centre`);
  }
  // every face looks out: wound the way its normals point (the material draws front faces only)
  const P = q => [g.position[q * 3], g.position[q * 3 + 1], g.position[q * 3 + 2]];
  for (let t = 0; t < g.index.length; t += 3) {
    const [i, j, k] = [g.index[t], g.index[t + 1], g.index[t + 2]];
    const [a, b, c] = [P(i), P(j), P(k)];
    const u = b.map((v, x) => v - a[x]), w = c.map((v, x) => v - a[x]);
    const n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]];
    if (Math.hypot(...n) < 1e-12) continue;
    const dot = [0, 1, 2].reduce((sum, x) => sum + n[x] * (g.normal[i * 3 + x] + g.normal[j * 3 + x] + g.normal[k * 3 + x]), 0);
    assert.ok(dot > 0, `${what}: face ${t / 3} is wound inward`);
  }
}

test('shapes built in code are whole, and painted from real palette columns', () => {
  for (const shape of new Set([...Object.values(PROC), ...Object.keys(SHAPES)])) whole(buildProc(shape, { t: 1, h: 2 }, paint), shape);
});

test('hanging things turn over in the hand: a lantern hangs below a hip, out past a hand', () => {
  for (const shape of HANGING) {
    const down = buildProc(shape, {}, paint), out = buildProc(shape, {}, paint, { flip: true });
    const ys = a => Array.from({ length: a.position.length / 3 }, (_, i) => a.position[i * 3 + 1]);
    assert.ok(Math.max(...ys(down)) < 0.05 && Math.min(...ys(out)) > -0.05, `${shape} hangs one way, then the other`);
    whole(out, `${shape} turned`);         // and still facing out
  }
});

test('add-ons are whole: a gem, a boss, a crest, pauldrons, crowns, every class\'s emblem', () => {
  const at = { p: [0, 1, -0.3], r: 0.14, rz: 0.4, lean: 0.12, side: -1, spikes: true };
  for (const kind of Object.keys(ADDONS)) whole(buildAddon(kind, { ...at, r: kind === 'crown' ? 0.45 : at.r }, paint), kind);
  whole(buildAddon('crown', { ...at, r: 0.45, variant: 'circlet' }, paint), 'circlet');
  for (const [cls, poly] of Object.entries(MOTIFS)) {
    const g = buildAddon('emblem', { ...at, motif: cls }, paint);
    whole(g, `${cls} emblem`);
    // both faces cut whole (n - 2 triangles each) and a rim of n quads
    assert.equal(g.index.length / 3, 2 * (poly.length - 2) + 2 * poly.length, `${cls}: the emblem's outline is filled`);
  }
});

const kinds = plan => plan.addons.map(a => a.kind).sort();
const kitted = (look, cls = 'paladin') => {
  const plan = planLook({ v: 1, ...look }, cls, kit);
  for (const a of plan.addons) {
    assert.ok(ADDONS[a.kind] || (a.shape && SHAPES[a.kind]), `${a.kind} can be built`);
    if (a.on) assert.ok(kit.pieces[a.on] && plan.props.some(p => p.name === a.on), `${a.kind} sits on ${a.on}, which is worn`);
    assert.ok(['pommel', 'front', 'top', 'crown', 'back', 'shoulder', 'hip'].includes(a.spot), `${a.kind}: a spot equip.js knows (${a.spot})`);
    for (const to of Object.values(a.roles || {})) assert.ok(kit.col(to) != null, `${a.kind}: ${to} is in the palette`);
  }
  return plan;
};

test('finer gear, finer detail: a pommel stone and a boss at 2, a plume, and pauldrons on heavy armour at 3', () => {
  const at = t => ({ sig: `fine${t}`, main: { k: 'sword', h: 1, m: 'steel', t }, off: { k: 'shield', v: 'round', m: 'iron', t }, head: { k: 'helm', m: 'steel', t }, body: { w: 3, m: 'steel', t } });
  assert.deepEqual(kinds(kitted(at(1))), [], 'tier 1: plain');
  assert.deepEqual(kinds(kitted(at(2))), ['boss', 'crest', 'gem']);
  assert.deepEqual(kinds(kitted(at(3))), ['boss', 'crest', 'gem', 'pauldron', 'pauldron']);
  const pauldrons = kitted(at(3)).addons.filter(a => a.kind === 'pauldron');
  assert.deepEqual(pauldrons.map(a => a.side).sort(), [-1, 1], 'one on each shoulder');
  assert.ok(pauldrons.every(a => a.on.includes('-Arm')), 'measured from the arm it sits on');
  const robed = kitted({ sig: 'robes3', body: { w: 0, c: 'blue', t: 3 } }, 'mage');
  assert.ok(!kinds(robed).includes('pauldron'), 'robes get no pauldrons');
  // the trim brightens with the tier
  const trim = t => kitted(at(t)).props.find(p => p.name === 'kit-shield_round_color');
  assert.ok(Object.values(trim(3).remap).includes(kit.col('gold')), 'a fine shield is trimmed in gold');
  assert.equal(kitted({ sig: 'pl', head: { k: 'helm', m: 'steel', t: 2 } }, 'paladin').addons[0].roles.cloth, 'royal_blue', "a paladin's plume");
});

test('crowns, circlets and lights', () => {
  const crown = kitted({ sig: 'cr', head: { k: 'crown', v: 'circlet', m: 'silver', t: 3 } }, 'ranger');
  assert.deepEqual(crown.addons.map(a => [a.kind, a.variant, a.on, a.spot]), [['crown', 'circlet', 'rogue-Head', 'crown']], 'a circlet round the head');
  const lantern = kitted({ sig: 'ln', main: { k: 'sword', h: 1, m: 'steel', t: 1 }, light: { k: 'lantern' } });
  assert.ok(lantern.addons.some(a => a.kind === 'lantern' && a.shape && a.spot === 'hip'), 'a lantern at the hip');
  assert.ok(lantern.glow > 0, 'and it is lit');
  const torch = kitted({ sig: 'tr', main: { k: 'sword', h: 1, m: 'steel', t: 1 }, light: { k: 'torch' } });
  assert.ok(torch.procs.some(p => p.shape === 'torch' && p.piece.endsWith('_Offhand')), 'a torch in the free hand');
  const busy = kitted({ sig: 'tb', main: { k: 'sword', h: 1, m: 'steel', t: 1 }, off: { k: 'shield', v: 'round', m: 'iron', t: 1 }, light: { k: 'torch' } });
  assert.ok(!busy.procs.some(p => p.shape === 'torch'), 'no hand free, no torch');
  const held = kitted({ sig: 'hl', off: { k: 'lantern', h: 1, t: 2 } }, 'cleric');
  assert.ok(held.procs.some(p => p.shape === 'lantern'), 'a lantern carried in the hand');
});

test('renown: a cloak at 10, its emblem at 20, a mantle at 35, motes at 45, a shining emblem at prestige', () => {
  const at = rn => kitted({ ...starterLook('warrior'), rn, sig: `rn${rn}` }, 'warrior');
  const cape = plan => plan.props.some(p => /_Cape$/.test(p.name));
  assert.ok(!cape(at(0)) && cape(at(1)), 'level 10: a cloak');
  assert.deepEqual(kinds(at(1)), []);
  assert.deepEqual(kinds(at(2)), ['emblem'], 'level 20: the class emblem on it');
  assert.equal(at(2).addons[0].motif, 'warrior');
  assert.deepEqual(kinds(at(3)), ['emblem', 'pauldron', 'pauldron'], 'level 35: a mantle');
  assert.ok(!at(3).adorn.motes && at(4).adorn.motes === 'class_warrior', 'level 45: motes in the class colour');
  assert.equal(at(4).addons.find(a => a.kind === 'emblem').roles.gold, 'gold');
  assert.equal(at(5).addons.find(a => a.kind === 'emblem').roles.gold, 'gold~glow', 'prestige: the emblem shines');
  assert.ok(at(5).glow > 0 && at(4).glow === 0);
  // a cloak they wear keeps its own look, and takes the emblem
  const own = kitted({ ...starterLook('assassin'), rn: 2, sig: 'own' }, 'assassin');
  assert.ok(own.props.some(p => p.name === 'rogue-Rogue_Cape') && kinds(own).includes('emblem'));
});

test('what shines: an element from tier 4, a legendary brighter, and what lingers round them', () => {
  const sword = (t, e, extra = {}) => kitted({ sig: `sh${t}${e}`, main: { k: 'sword', h: 1, m: 'steel', t, e }, ...extra });
  assert.equal(sword(3, 'fire').glow, 0, 'tier 3: a fire gem, unlit');
  const four = sword(4, 'fire');
  assert.equal(four.glow, 1);
  assert.equal(four.addons.find(a => a.kind === 'gem').roles.gem, 'fire~glow');
  assert.equal(four.adorn.element, 'fire');
  const legend = sword(5, 'frost', { aura: 'legendary' });
  assert.ok(legend.glow > 1 && legend.adorn.legendary && legend.adorn.aura === 'legendary');
  const bow = kitted({ sig: 'bw', main: { k: 'bow', h: 2, m: 'wood', t: 4, e: 'nature' } }, 'ranger');
  assert.equal(bow.adorn.hand, 'handslotl', "a bow's sparks come from the hand that holds it");
  assert.ok(!sword(2).adorn.motes && !sword(2).adorn.element && !sword(2).adorn.legendary, 'plain gear: nothing lingers');
});

test('race: its skin on every part of the body, its build, a dark elf\'s white hair', async () => {
  const { RACE, raceOf } = await import('../../src/web_isometric/world3d/gearlook.js');
  for (const race of ['human', 'elf', 'dark_elf', 'half_orc', 'dwarf', 'halfling', 'gnome']) assert.ok(RACE[race], race);
  assert.equal(raceOf({ race: 'Half-Orc' }), RACE.half_orc, 'the server\'s spelling is understood');
  const dwarf = kitted({ ...starterLook('warrior'), race: 'dwarf', sig: 'dw' }, 'warrior');
  const skinned = dwarf.props.filter(p => /-(Head|HeadHooded|Body|ArmLeft|ArmRight|LegLeft|LegRight)$/.test(p.name));
  for (const p of skinned) {
    const skinCols = Object.entries(kit.pieces[p.name].cols).filter(([, role]) => role === 'skin').map(([c]) => +c);
    for (const c of skinCols) assert.equal(p.remap[c], kit.col('skin_dwarf'), `${p.name}: dwarf skin`);
  }
  assert.ok(dwarf.build.h < 0.9 && dwarf.build.w > 1, 'a dwarf is short and broad');
  const drow = kitted({ ...starterLook('mage'), race: 'dark_elf', sig: 'de' }, 'mage');
  const head = drow.props.find(p => p.name === 'mage-Head');
  assert.ok(Object.values(head.remap).includes(kit.col('white')) && Object.values(head.remap).includes(kit.col('skin_drow')));
  const human = kitted({ ...starterLook('mage'), race: 'human', sig: 'hu' }, 'mage');
  assert.ok(!human.props.some(p => Object.values(p.remap || {}).includes(kit.col('skin_light'))), 'a human keeps the model\'s skin');
  const toned = kitted({ ...starterLook('mage'), race: 'human', tone: 3, sig: 'ht' }, 'mage');
  assert.ok(toned.props.some(p => Object.values(p.remap || {}).includes(kit.col('skin_dark'))), '…unless given a tone');
  assert.deepEqual(human.build, { h: 1, w: 1 });
});

test('male or female: the face (the pack\'s one woman is the rogue) and a lighter build; unsaid, the class\'s own', () => {
  const head = plan => names(plan).find(n => /-(Head|HeadHooded)$/.test(n));
  for (const cls of CLASSES) {
    const look = starterLook(cls);
    const plain = planLook(look, cls, kit), her = planLook({ ...look, sex: 'female' }, cls, kit), him = planLook({ ...look, sex: 'male' }, cls, kit);
    const hooded = CLASS_BASE[cls].hood;
    assert.equal(head(plain), hooded ? 'rogue-HeadHooded' : `${CLASS_BASE[cls].model}-Head`, `${cls}: one who never said keeps the class's face`);
    assert.equal(head(her), hooded ? 'rogue-HeadHooded' : 'rogue-Head', `${cls}: a woman's face (a hood still hides it)`);
    assert.equal(head(him), hooded ? 'rogue-HeadHooded' : CLASS_BASE[cls].model === 'rogue' ? 'mage-Head' : `${CLASS_BASE[cls].model}-Head`, `${cls}: a man's face`);
    assert.equal(torso(her), torso(plain), `${cls}: the class keeps its body`);
    assert.ok(her.build.w < plain.build.w && her.build.h < plain.build.h && him.build.w === plain.build.w, `${cls}: her build is lighter`);
    for (const n of [...names(her), ...names(him)]) assert.ok(kit.pieces[n], `${cls}: ${n} is in the kit`);
  }
  const dwarf = planLook({ ...starterLook('warrior'), race: 'dwarf', sex: 'female' }, 'warrior', kit);
  assert.ok(Math.abs(dwarf.build.h - 0.82 * SEX_BUILD.female.h) < 1e-9, 'race and sex together');
  const npc = planLook({ ...starterLook('warrior'), base: { model: 'knight', w: 3 }, sex: 'female' }, 'warrior', kit);
  assert.equal(head(npc), 'knight-Head', "a creature their zone dressed keeps its trade's body");
});

test('people the world dressed: their trade\'s body, their race, their gear', async () => {
  const { npcDress, creatureLook } = await import('../../src/web_isometric/world3d/looks.js');
  const guardLook = { v: 1, rn: 0, sig: 'g1', main: { k: 'sword', h: 1, m: 'steel', t: 1 } };
  const guard = { name: 'cityguard', short: 'the cityguard', pv: 3060, look: guardLook };
  const npc = npcDress(guard, creatureLook(guard));
  assert.ok(npc, 'a guard their zone armed is dressed');
  assert.equal(npc.cls, 'paladin');
  assert.equal(npc.look.base.model, 'knight', "the body looks.js gives a guard");
  assert.ok(npc.look.race === 'human' && npc.look.tone >= 0 && npc.look.rn === 0);
  const plan = kitted(npc.look, npc.cls);
  assert.ok(plan.props.some(p => p.name === 'knight-Body') && plan.props.some(p => p.name === 'knight-1H_Sword'), 'in a knight\'s body, with its sword');
  const dwarf = { name: 'smith', short: 'the dwarven smith', pv: 9, look: { v: 1, rn: 0, sig: 'd1', main: { k: 'hammer', h: 1, m: 'iron', t: 1 } } };
  const d = npcDress(dwarf, creatureLook(dwarf));
  assert.equal(d.look.race, 'dwarf');
  assert.equal(d.scale, 1, 'a dwarf\'s height comes with its race, not twice');
  const wolf = { name: 'wolf', short: 'a grey wolf', pv: 10, look: guardLook };
  assert.equal(npcDress(wolf, creatureLook(wolf)), null, 'a wolf handed a sword stays a wolf');
  assert.equal(npcDress({ name: 'baker', short: 'the baker', pv: 3001 }, creatureLook({ name: 'baker', short: 'the baker' })), null, 'no gear: the body looks.js gives');
  const a = npcDress({ ...guard }, creatureLook(guard)), b = npcDress({ ...guard, pv: 3061 }, creatureLook(guard));
  assert.ok(a.look.sig !== guardLook.sig && a.look.sig.startsWith(guardLook.sig), 'its own signature (body, race, tone)');
  assert.ok(typeof b.look.tone === 'number');
});

test('the weapon decides the blow from afar: a bow shoots whoever holds it; a caster throws a bolt', () => {
  assert.equal(rangedBlow({ main: { k: 'bow', h: 2 } }, 'warrior').kind, 'shot', 'a warrior with a bow shoots');
  assert.equal(rangedBlow({ main: { k: 'sword', h: 1 } }, 'ranger'), null, 'a ranger with a sword swings');
  assert.equal(rangedBlow(starterLook('ranger'), 'ranger').kind, 'shot', 'a ranger starts with a bow');
  assert.equal(rangedBlow({ main: { k: 'staff', h: 2 } }, 'mage').kind, 'bolt');
  assert.equal(rangedBlow({}, 'necromancer').school, 'necrotic', 'a bolt with nothing in hand');
  assert.equal(rangedBlow({ main: { k: 'crossbow', h: 1 } }, 'mage').kind, 'shot', 'a mage with a crossbow shoots it');
  assert.equal(rangedBlow(null, 'thief'), null);
});

// ---- class-styled gear (class_gear.py): hats and staves built in code, and every class at the top ----
test("a hat by its shape, else the class's: a caster's wizard hat, a bard's brim; brim, cap and mitre built in code", async () => {
  const { hatShape } = await import('../../src/web_isometric/world3d/gearlook.js');
  assert.equal(hatShape({ k: 'hat' }, 'mage'), 'wizard');
  assert.equal(hatShape({ k: 'hat' }, 'bard'), 'brim');
  assert.equal(hatShape({ k: 'hat', v: 'mitre' }, 'mage'), 'mitre');
  const kinds = { brim: 'brimhat', cap: 'cap', mitre: 'mitre' };
  for (const [v, kind] of Object.entries(kinds)) {
    const plan = planLook({ v: 1, sig: `hat:${v}`, head: { k: 'hat', v, c: 'forest', t: 2 } }, 'bard', kit);
    const ad = plan.addons.find(a => a.kind === kind);
    assert.ok(ad && ad.spot === 'crown' && ad.hat, `${v}: an add-on round the head`);
    assert.ok(!names(plan).includes('mage-Mage_Hat'), `${v}: not the wizard hat`);
    assert.ok(ADDONS[kind], `${kind} can be built`);
    whole(buildAddon(kind, { p: [0, 1, 0], r: 0.4, rz: 0.37 }, paint), kind);
  }
  assert.ok(names(planLook({ v: 1, sig: 'hat:w', head: { k: 'hat', v: 'wizard', t: 2 } }, 'bard', kit)).includes('mage-Mage_Hat'));
});

test("a staff by its head, else the class's: a mage's crystal, a necromancer's skull", async () => {
  const { staffShape } = await import('../../src/web_isometric/world3d/gearlook.js');
  assert.equal(staffShape({ k: 'staff' }, 'mage'), 'staff_crystal');
  assert.equal(staffShape({ k: 'staff' }, 'necromancer'), 'staff_skull');
  assert.equal(staffShape({ k: 'staff' }, 'cleric'), 'staff_plain');
  assert.equal(staffShape({ k: 'staff', v: 'gnarled' }, 'mage'), 'staff_gnarled');
  for (const head of ['crystal', 'skull', 'gnarled', 'plain']) {
    const plan = planLook({ v: 1, sig: `staff:${head}`, main: { k: 'staff', h: 2, v: head, m: 'wood', t: 2 } }, 'mage', kit);
    const made = STAFF_PIECE[`staff_${head}`];
    if (made && kit.pieces[made]) {
      assert.ok(names(plan).includes(made) && !plan.procs.some(p => String(p.shape).startsWith('staff')), `${head}: the kit's own piece`);
      continue;
    }
    const pr = plan.procs.find(p => p.shape === `staff_${head}`);
    assert.ok(pr && kit.pieces[pr.piece], `${head}: built in code on a sword's mount`);
    const a = buildProc(pr.shape, pr.look, paint);
    whole(a, pr.shape);
    const ys = [...a.position].filter((_, i) => i % 3 === 1);
    assert.ok(Math.max(...ys) - Math.min(...ys) > 1.5, `${head}: as long as a staff`);
  }
});

test("a weapon the kit holds as a piece is held in place of the shape built in code, in the item's colours", () => {
  for (const [shape, made] of Object.entries(PROC_PIECE)) {
    if (!kit.pieces[made]) continue;
    const plan = planLook({ v: 1, sig: `made:${shape}`, main: { k: shape, h: 1, m: 'gold', t: 3 } }, 'cleric', kit);
    assert.ok(names(plan).includes(made) && !plan.procs.some(p => p.shape === shape), `${shape}: the kit's own piece`);
    const remap = plan.props.find(p => p.name === made).remap;
    assert.ok(Object.values(remap).includes(kit.col('gold')), `${shape}: a gold one is gold`);
  }
  assert.ok(names(planLook(starterLook('cleric'), 'cleric', kit)).includes(PROC_PIECE.mace) || !kit.pieces[PROC_PIECE.mace], "a cleric's own mace");
});

test('every class as gearup dresses it (gallery ENDGAME, kept true by tests/test_class_gear.py) is drawn as its class', async () => {
  const { ENDGAME } = await import('../../src/web_isometric/world3d/gallery.js').catch(() => ({}));
  if (!ENDGAME) return;          // gallery.js needs three.js: the Python test checks the data instead
  for (const [cls, look] of Object.entries(ENDGAME)) {
    const plan = planLook({ ...look, sig: `endgame:${cls}` }, cls, kit);
    assert.equal(torso(plan), `${CLASS_BASE[cls].model}-Body`, `${cls} keeps its own body`);
  }
});

test("a masked cowl draws a cloth over the face below the eyes (the assassin's), whole", () => {
  const plan = planLook({ v: 1, sig: 'mask', head: { k: 'hood', v: 'masked', c: 'purple', t: 3 } }, 'assassin', kit);
  const ad = plan.addons.find(a => a.kind === 'facemask');
  assert.ok(ad && ad.mask && ad.on === 'rogue-HeadHooded', 'a face mask on the hooded head');
  whole(buildAddon('facemask', { p: [0, 1, 0], r: 0.45, rz: 0.4 }, paint), 'facemask');
  assert.ok(!planLook({ v: 1, sig: 'nomask', head: { k: 'hood', c: 'purple', t: 3 } }, 'assassin', kit).addons.some(a => a.kind === 'facemask'), 'a plain hood has none');
});

// the archmage (gear_look.py style 'archmage', for a mage): the Blender pieces, white hair and
// brows, its own hat unless a helm is worn, the moon staff for any staff
test('the archmage: a mage who chose it wears the Blender pieces, white-haired; anyone else does not', async () => {
  const { ARCHMAGE } = await import('../../src/web_isometric/world3d/gearlook.js');
  const kit = kitIndex(JSON.parse(fs.readFileSync(path.join(ART, 'chars/equip.json'), 'utf8')));
  for (const p of [...ARCHMAGE, 'Archmage_Hat', 'Archmage_Staff']) assert.ok(kit.pieces[p], `the kit has ${p}`);
  const names = plan => plan.props.map(p => p.name);
  const a = planLook({ ...starterLook('mage'), style: 'archmage', sig: 'a' }, 'mage', kit);
  for (const p of [...ARCHMAGE, 'Archmage_Hat', 'Archmage_Staff']) assert.ok(names(a).includes(p), `wears ${p}`);
  assert.ok(!a.procs.some(p => String(p.shape).startsWith('staff')), 'the moon staff, not a staff built in code');
  const head = a.props.find(p => p.name === 'mage-Head');
  assert.ok(Object.values(head.remap).some(c => kit.columns[c].name === 'fur_white'), 'white hair and brows');
  const helm = planLook({ ...starterLook('mage'), style: 'archmage', head: { k: 'helm', m: 'iron', t: 1 }, sig: 'h' }, 'mage', kit);
  assert.ok(!names(helm).includes('Archmage_Hat') && names(helm).includes('knight-Knight_Helmet'), 'a helm instead of the hat');
  const classic = planLook({ ...starterLook('mage'), sig: 'c' }, 'mage', kit);
  assert.ok(!names(classic).some(n => n.startsWith('Archmage')), 'the classic mage is as it was');
  const warrior = planLook({ ...starterLook('warrior'), style: 'archmage', sig: 'w' }, 'warrior', kit);
  assert.ok(!names(warrior).some(n => n.startsWith('Archmage')), 'not a mage: no archmage');
});
