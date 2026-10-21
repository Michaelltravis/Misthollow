// Which body parts, pieces and colours dress a character, from the server's look summary
// (src/gear_look.py). Pure: no three.js, so tests/web/gearlook.test.mjs runs it in Node.
// equip.js turns a plan into one mesh from the equipment kit (art3d/chars/equip.glb, whose
// manifest equip.json says what every piece is and which palette columns it paints).
//
// A class keeps its silhouette: its body comes from its own model unless worn armour is two
// or more steps of weight away from what the class starts in (a mage in plate gets the
// knight's torso). Colours always follow the gear: metal and leather by material, cloth by
// the piece's colour, its named set, or the class's own colour; tier 0 is dull and worn.
// A race brings its skin and its build (RACE); a creature their zone dressed brings the body
// its trade gave it (look.base, looks.js npcDress).

// a class's own model, the armour weight it starts in (0 cloth, 1 leather, 2 mail, 3 plate),
// and whether it goes hooded when its head is bare
export const CLASS_BASE = {
  warrior: { model: 'barbarian', w: 2 }, paladin: { model: 'knight', w: 2 }, cleric: { model: 'knight', w: 1 },
  mage: { model: 'mage', w: 0 }, necromancer: { model: 'mage', w: 0 }, thief: { model: 'rogue', w: 1 },
  assassin: { model: 'rogue', w: 1, hood: true }, ranger: { model: 'rogue', w: 1, hood: true }, bard: { model: 'rogue', w: 1 },
};
// how each race looks: its skin (a palette ramp; a human keeps the model's own unless the look
// gives a tone) and its build, height and breadth (looks.js sizes its people alike)
export const RACE = {
  human: { h: 1, w: 1 },
  elf: { skin: 'skin_elf', h: 1.04, w: 0.94 },
  dark_elf: { skin: 'skin_drow', hair: 'white', h: 1.02, w: 0.94 },
  half_orc: { skin: 'skin_orc', h: 1.07, w: 1.12 },
  dwarf: { skin: 'skin_dwarf', h: 0.82, w: 1.12 },
  halfling: { skin: 'skin_tan', h: 0.72, w: 0.96 },
  gnome: { skin: 'skin_gnome', h: 0.66, w: 1 },
};
const TONES = ['skin_light', 'skin_tan', 'skin_brown', 'skin_dark'];
// a hero's sex: the face (the pack's one woman is the rogue, so a man of a rogue's trade wears
// the mage's) and a lighter build; an older character who never said keeps the class's own
export const SEX_BUILD = { female: { h: 0.97, w: 0.92 }, male: { h: 1, w: 1 } };
export const sexOf = look => { const s = String((look && look.sex) || '').toLowerCase(); return SEX_BUILD[s] ? s : null; };
export const raceOf = look => RACE[String((look && look.race) || 'human').toLowerCase().replace(/[\s-]+/g, '_')] || RACE.human;
const MODEL_W = { mage: 0, rogue: 1, barbarian: 2, knight: 3 };
const BY_WEIGHT = ['mage', 'rogue', 'barbarian', 'knight'];
export const baseOf = cls => CLASS_BASE[String(cls || '').toLowerCase()] || CLASS_BASE.paladin;

// what a class wears before it finds anything better (player.py's starting kits, as the
// server would describe them): character creation and the demo show this
export function starterLook(cls) {
  const c = String(cls || '').toLowerCase();
  const S = {
    warrior: { main: { k: 'sword', h: 1, m: 'steel' }, off: { k: 'shield', v: 'round', m: 'iron', m2: 'wood' }, head: { k: 'helm', m: 'iron' }, body: { w: 2, m: 'iron' }, legs: { w: 3, m: 'iron' } },
    paladin: { main: { k: 'sword', h: 1, m: 'steel' }, off: { k: 'shield', v: 'round', m: 'iron', m2: 'wood' }, body: { w: 2, m: 'iron' } },
    cleric: { main: { k: 'mace', h: 1, m: 'steel' }, body: { w: 1, m: 'leather' } },
    mage: { main: { k: 'staff', h: 2, m: 'wood_dark' }, off: { k: 'book' }, body: { w: 0 } },
    necromancer: { main: { k: 'staff', h: 2, m: 'wood_dark', m2: 'obsidian' }, body: { w: 0, c: 'black' } },
    thief: { main: { k: 'dagger', h: 1, m: 'steel' }, body: { w: 1, m: 'leather_tan' } },
    ranger: { main: { k: 'bow', h: 2, m: 'wood' }, body: { w: 1, m: 'leather_dark' }, quiver: 1 },
    bard: { main: { k: 'sword', h: 1, m: 'steel' }, off: { k: 'instrument', h: 1, m: 'wood' }, body: { w: 1, m: 'leather' } },
    assassin: { main: { k: 'dagger', h: 1, m: 'steel' }, body: { w: 1, m: 'leather_black' }, back: { k: 'cloak', v: 'rogue', c: 'black' } },
  }[c] || {};
  const look = { v: 1, rn: 0 };
  for (const [k, p] of Object.entries(S)) look[k] = typeof p === 'object' ? { t: 0, ...p } : p;
  look.sig = `starter:${c}`;
  return look;
}

// ---- pieces ----
const MAIN = {
  sword: h => (h === 2 ? 'knight-2H_Sword' : 'knight-1H_Sword'),
  axe: h => (h === 2 ? 'barbarian-2H_Axe' : 'barbarian-1H_Axe'),
  dagger: () => 'rogue-Knife', staff: () => 'mage-2H_Staff', wand: () => 'mage-1H_Wand',
  crossbow: h => (h === 2 ? 'rogue-2H_Crossbow' : 'rogue-1H_Crossbow'), thrown: () => 'rogue-Throwable',
};
// built in code (procgear.js): kind -> shape (an instrument by its variant)
export const PROC = { bow: 'bow', mace: 'mace', hammer: 'hammer', spear: 'spear', polearm: 'polearm', scythe: 'scythe',
  pick: 'pick', whip: 'whip', claw: 'claw', instrument: 'lute', orb: 'orb', relic: 'orb', skull: 'skull', censer: 'censer',
  lantern: 'lantern', torch: 'torch' };
const INSTRUMENT_SHAPES = new Set(['lute', 'lyre', 'harp', 'flute', 'drum', 'horn']);
// a staff by its head (gear_look.py STAFF_HEADS), else the class's own: a wizard's crystal, a
// necromancer's skull, a plain pilgrim's staff for anyone else (procgear.js staff_*)
export const STAFF_HEADS = new Set(['crystal', 'skull', 'gnarled', 'plain']);
const STAFF_OF = { mage: 'crystal', necromancer: 'skull' };
export const staffShape = (p, cls) => `staff_${STAFF_HEADS.has(p.v) ? p.v : STAFF_OF[String(cls || '').toLowerCase()] || 'plain'}`;
// staves and weapons the kit holds as pieces (made by Tripo, tools/art3d/tripo/, repainted onto
// the kit's palette by blender/models/tripo_prop.py): held in the right hand in place of the
// shape built in code
export const STAFF_PIECE = { staff_crystal: 'Tripo_Staff_Crystal', staff_skull: 'Tripo_Staff_Skull' };
export const PROC_PIECE = { mace: 'Tripo_Mace', spear: 'Tripo_Spear' };
// a hat by its shape (gear_look.py HATS), else the class's: casters the pack's wizard hat, the
// rest a brimmed hat with a feather; brim, cap and mitre are built in code (procgear.js)
const HAT_SHAPES = new Set(['wizard', 'brim', 'cap', 'mitre']);
const CASTERS = new Set(['mage', 'necromancer']);
export const hatShape = (p, cls) => (HAT_SHAPES.has(p.v) ? p.v : CASTERS.has(String(cls || '').toLowerCase()) ? 'wizard' : 'brim');
const HAT_ADDON = { brim: 'brimhat', cap: 'cap', mitre: 'mitre' };
export const procShape = p => (p.k === 'instrument' && INSTRUMENT_SHAPES.has(p.v) ? p.v : PROC[p.k]);
// a helm's plume, unless the helm has a colour of its own: one that stands out on steel and gold
const PLUME = { warrior: 'crimson', paladin: 'royal_blue', cleric: 'white', mage: 'violet', necromancer: 'black',
  thief: 'grey', assassin: 'black', ranger: 'forest', bard: 'magenta' };
// the cloak a class's renown gives it (level 10) when it wears none
const RENOWN_CAPE = { warrior: 'knight', paladin: 'knight', cleric: 'knight', mage: 'mage', necromancer: 'mage',
  thief: 'rogue', assassin: 'rogue', ranger: 'rogue', bard: 'rogue' };
const OFFHAND = { sword: 'knight-1H_Sword_Offhand', axe: 'barbarian-1H_Axe_Offhand', dagger: 'rogue-Knife_Offhand' };
const SHIELD = { round: 'knight-Round_Shield', badge: 'knight-Badge_Shield', square: 'knight-Rectangle_Shield', spike: 'knight-Spike_Shield' };
const SHIELD_PAINTED = { round: 'kit-shield_round_color', badge: 'kit-shield_badge_color', square: 'kit-shield_square_color', spike: 'kit-shield_spikes_color' };
const HEAD = { helm: 'knight-Knight_Helmet', horned: 'barbarian-Barbarian_Hat', hat: 'mage-Mage_Hat' };
// the archmage's pieces besides the hat and staff (gear_look.py style 'archmage')
export const ARCHMAGE = ['Archmage_Robe', 'Archmage_Mantle', 'Archmage_Cuff_L', 'Archmage_Cuff_R', 'Archmage_Sash', 'Archmage_Beard'];
const CAPE = { knight: 'knight-Knight_Cape', barbarian: 'barbarian-Barbarian_Cape', mage: 'mage-Mage_Cape', rogue: 'rogue-Rogue_Cape' };
export const WEAPON_KINDS = new Set(['sword', 'axe', 'dagger', 'mace', 'hammer', 'spear', 'polearm', 'scythe', 'pick', 'claw', 'whip', 'staff', 'wand', 'crossbow', 'bow', 'thrown']);

// a hat made for one head sits a little differently on another (tuned in the gear gallery):
// `${piece}@${head model}` -> offset (bone-local metres) and scale
export const FIT = {
  'knight-Knight_Helmet@mage': { t: [0, 0.03, -0.04], s: 1.08 },
  'knight-Knight_Helmet@barbarian': { t: [0, 0.02, -0.01], s: 1.04 },
  'mage-Mage_Hat@knight': { t: [0, -0.03, 0.03], s: 0.95 },
  'mage-Mage_Hat@barbarian': { t: [0, 0, 0.02], s: 0.98 },
  'mage-Mage_Hat@rogue': { t: [0, -0.02, 0.02], s: 0.95 },
  'barbarian-Barbarian_Hat@mage': { t: [0, 0.03, -0.04], s: 1.07 },
  'barbarian-Barbarian_Hat@knight': { t: [0, 0, 0.01], s: 1.0 },
  'knight-Knight_Helmet@rogue': { t: [0, 0, 0], s: 1.0 },
};

// a leather and the lighter leather beside it
const LEATHER_PAIR = { leather: ['leather', 'leather_tan'], leather_tan: ['leather_tan', 'hide'], leather_dark: ['leather_dark', 'leather'],
  leather_black: ['leather_black', 'leather_dark'], leather_red: ['leather_red', 'leather'], hide: ['hide', 'leather_tan'],
  dragonhide: ['dragonhide', 'leather_dark'], snakeskin: ['snakeskin', 'leather_tan'] };

const worn = (name, p) => (p && (p.t || 0) === 0 ? `${name}~worn` : name);
const darkOf = (name, p) => (p && (p.t || 0) === 0 ? `${name}~worn~dark` : `${name}~dark`);

// the cloth colour a piece is painted in: its named set, its own colour, its zone set's, else the class's
function clothOf(p, cls) {
  if (p && p.s) return `set_${p.s}`;
  if (p && p.c) return p.c;
  if (p && p.zc) return p.zc;
  return `class_${String(cls || 'paladin').toLowerCase()}`;
}

// finer gear, finer trim: silver at tier 2, gold from 3, a gold that shines on a legendary
function trimFor(p) {
  const t = (p && p.t) || 0;
  return t >= 5 ? 'gold~glow' : t >= 3 ? 'gold' : t === 2 ? 'silver' : null;
}
// a gem: its element, its set's, from tier 4 shining; a legendary shines holy if nothing else
export function gemFor(p, cls) {
  const t = (p && p.t) || 0;
  const base = p && p.e ? p.e : p && p.s ? `set_${p.s}_accent` : t >= 5 ? 'holy' : null;
  if (!base) return t >= 2 ? `class_${String(cls || 'paladin').toLowerCase()}` : null;
  return t >= 4 ? `${base}~glow` : base;
}
function withTrim(r, p) {
  const trim = trimFor(p);
  if (trim) { r.trim = trim; r.gold = trim; }
  return r;
}

// role -> ramp name, for each kind of piece
function armourRoles(a, cls) {
  const r = {};
  if (a && a.w >= 2 && a.m) { r.metal = worn(a.m, a); r.metal_dark = darkOf(a.m, a); }
  if (a && a.w === 1 && a.m) {
    const [main, light] = LEATHER_PAIR[a.m] || [a.m, a.m];
    r.leather = worn(main, a); r.leather_light = worn(light, a);
    r.metal = worn(main, a); r.metal_dark = worn('leather_dark', a);      // a heavier body in leather: its plates are boiled leather
  }
  const cloth = clothOf(a, cls);
  r.cloth = worn(cloth, a); r.cloth_dark = darkOf(cloth, a);
  return withTrim(r, a);
}
function weaponRoles(p, cls) {
  const r = {};
  const wooden = ['staff', 'bow', 'wand', 'instrument', 'orb', 'relic', 'skull', 'censer', 'lantern', 'torch'].includes(p.k);
  const metal = wooden ? p.m2 : p.m;
  const wood = wooden ? p.m : p.m2;
  if (metal) { r.metal = worn(metal, p); r.metal_dark = darkOf(metal, p); }
  if (wood) r.wood = worn(wood, p);
  const g = gemFor(p, cls);
  if (g) { r.gem = g; r.crystal = g; }
  if (p.k === 'lantern' || p.k === 'torch') r.gem = 'fire~glow';
  return withTrim(r, p);
}
function shieldRoles(p, cls) {
  const r = { metal: worn(p.m || 'iron', p), metal_dark: darkOf(p.m || 'iron', p) };
  if (p.m2) r.wood = worn(p.m2, p);
  r.gem = gemFor(p, cls) || `class_${String(cls || 'paladin').toLowerCase()}`;
  return withTrim(r, p);
}
function headRoles(p, cls) {
  if (p.k === 'hat' || p.k === 'hood') {
    const c = clothOf(p, cls), r = { cloth: worn(c, p), cloth_light: worn(c, p) };
    if (trimFor(p)) r.accent = trimFor(p);          // a finer hat's band in silver or gold
    return r;
  }
  if (p.m) return withTrim({ metal: worn(p.m, p), metal_dark: darkOf(p.m, p) }, p);
  return {};
}
function capeRoles(p, cls) {
  const c = clothOf(p, cls);
  const r = { cloth: worn(c, p), cloth_accent: worn(c, p), cloth_dark: darkOf(c, p) };
  if (p.s || p.c) r.leather_dark = worn(c, p);            // the fur cloak too, when it has a colour or a set
  return r;
}

// the role -> palette column remap of one piece
function remapOf(kit, name, roles) {
  const piece = kit.pieces[name];
  if (!piece) return null;
  const out = {};
  for (const [col, role] of Object.entries(piece.cols)) {
    const target = roles[role];
    if (!target) continue;
    const to = kit.col(target);
    if (to != null && to !== +col) out[col] = to;
  }
  return out;
}

const mountOf = (kit, piece) => kit.pieces[piece] && kit.pieces[piece].mount;

// A look -> {key, parts, props: [{name, remap, fit}], procs: [{shape, piece (whose mount it
// borrows), look, roles}], addons: [{kind, on (a piece) | bone, spot, roles, ...}], glow, adorn, idle}
export function planLook(look, cls, kit) {
  look = look || starterLook(cls);
  cls = String(cls || '').toLowerCase();
  // a creature dressed by its zone keeps the body its trade gave it (looks.js): look.base
  const base = look.base ? { ...baseOf(cls), ...look.base } : baseOf(cls);
  const rn = look.rn || 0;
  // measured from what the class starts in (a cleric's knight body stands for leather), then
  // arms and legs from what the torso stands for
  const torso = look.body && Math.abs(look.body.w - base.w) >= 2 ? BY_WEIGHT[look.body.w] : base.model;
  const refW = torso === base.model ? base.w : MODEL_W[torso];
  const limb = a => (a && Math.abs(a.w - refW) >= 2 ? BY_WEIGHT[a.w] : torso);
  const arms = limb(look.arms), legs = limb(look.legs);
  const hooded = look.head ? look.head.k === 'hood' : base.hood;
  const sex = look.base ? null : sexOf(look);       // a creature their zone dressed keeps its trade's body
  const headModel = sex === 'female' ? 'rogue' : sex === 'male' && base.model === 'rogue' ? 'mage' : base.model;
  const props = [], procs = [], addons = [];
  const add = (name, roles, fit) => {
    if (!kit.pieces[name]) return null;
    props.push({ name, remap: remapOf(kit, name, roles || {}), fit: fit || null });
    return name;
  };
  const gemOr = (p, fallback) => gemFor(p, cls) || fallback;

  // the body: the class's head, torso, arms and legs from whichever models the armour asks for
  const bodyRoles = armourRoles(look.body, cls);
  const headPart = hooded ? 'rogue-HeadHooded' : `${headModel}-Head`;
  const parts = [
    // a hood in its own colour, or the class's
    [headPart, hooded ? headRoles(look.head || { k: 'hood', t: 1 }, cls) : {}],
    [`${torso}-Body`, bodyRoles],
    [`${arms}-ArmLeft`, look.arms ? armourRoles(look.arms, cls) : bodyRoles],
    [`${arms}-ArmRight`, look.arms ? armourRoles(look.arms, cls) : bodyRoles],
    [`${legs}-LegLeft`, look.legs ? armourRoles(look.legs, cls) : bodyRoles],
    [`${legs}-LegRight`, look.legs ? armourRoles(look.legs, cls) : bodyRoles],
  ];
  // the race's skin (and a dark elf's white hair) on every part of the body
  const race = raceOf(look);
  const flesh = {};
  // the archmage, a mage who chose that look (gear_look.py `style`): white hair and brows to match
  // the beard, the robe to the ankles, mantle, cuffs and sash (the Blender pieces,
  // tools/art3d/blender/models/archmage.py), the tall hat unless a helm, a crown or a hood is worn,
  // and the moon staff whenever a staff is held
  const archmage = !look.base && String(look.style || '') === 'archmage' && cls === 'mage';
  const archHat = archmage && !hooded && !(look.head && ['helm', 'horned', 'crown'].includes(look.head.k));
  const skin = look.tone != null ? TONES[Math.abs(look.tone) % TONES.length] : race.skin;
  if (skin) flesh.skin = skin;
  if (race.hair) flesh.hair = race.hair;
  if (archmage) flesh.hair = 'fur_white';
  for (const [name, roles] of parts) add(name, { ...roles, ...flesh });
  if (archmage) for (const piece of ARCHMAGE) add(piece, {});
  if (archHat) add('Archmage_Hat', {});

  // the main hand: a piece from the pack, or a shape built in code; finer ones get a pommel stone
  const m = look.main;
  if (m && m.k === 'staff' && archmage) add('Archmage_Staff', {});
  else if (m && m.k === 'staff') {
    const shape = staffShape(m, cls);
    if (!(STAFF_PIECE[shape] && add(STAFF_PIECE[shape], weaponRoles(m, cls)))) procs.push({ shape, piece: 'knight-1H_Sword', look: m, roles: weaponRoles(m, cls) });
  }
  else if (m) {
    const shape = procShape(m);
    if (shape && PROC_PIECE[shape] && add(PROC_PIECE[shape], weaponRoles(m, cls))) {
      // (the kit's own piece)
    } else if (shape) procs.push({ shape, piece: m.k === 'bow' ? 'knight-1H_Sword_Offhand' : 'knight-1H_Sword', look: m, roles: weaponRoles(m, cls) });
    else if (MAIN[m.k]) {
      const name = add(m.h === 2 && m.k === 'sword' && (m.t || 0) >= 3 ? 'kit-sword_2handed_color' : MAIN[m.k](m.h), weaponRoles(m, cls));
      if (name && (m.t || 0) >= 2 && !['crossbow', 'thrown', 'staff'].includes(m.k)) addons.push({ kind: 'gem', on: name, spot: 'pommel', roles: { gem: gemOr(m, 'gem_red') } });
    }
  }
  // the off hand: a shield (a boss on a finer one), a second weapon, or something held
  const o = look.off;
  const bowInLeft = m && m.k === 'bow';
  if (o && !bowInLeft) {
    if (o.k === 'shield') {
      const v = SHIELD[o.v] ? o.v : 'round';
      const name = add((o.t || 0) >= 2 || o.s ? SHIELD_PAINTED[v] : v === 'round' && o.m2 ? 'barbarian-Barbarian_Round_Shield' : SHIELD[v], shieldRoles(o, cls));
      if (name && (o.t || 0) >= 2) addons.push({ kind: 'boss', on: name, spot: 'front', roles: { metal: (o.t || 0) >= 3 ? 'gold' : worn(o.m || 'iron', o), gem: gemOr(o, `class_${cls}`) } });
    } else if (OFFHAND[o.k] || (WEAPON_KINDS.has(o.k) && !procShape(o))) {
      const name = add(OFFHAND[o.k] || 'rogue-Knife_Offhand', weaponRoles(o, cls));
      if (name && (o.t || 0) >= 2) addons.push({ kind: 'gem', on: name, spot: 'pommel', roles: { gem: gemOr(o, 'gem_red') } });
    } else if (procShape(o)) procs.push({ shape: procShape(o), piece: 'knight-1H_Sword_Offhand', look: o, roles: weaponRoles(o, cls) });
    else if (o.k === 'book') add('mage-Spellbook', o.c ? { cloth_accent: worn(o.c, o) } : {});
  }
  // the head: a helm (a crest on a finer one), a hat, a hood, a crown
  const h = look.head;
  const hat = h && h.k === 'hat' ? hatShape(h, cls) : null;
  if (archHat && (!h || h.k === 'hat')) {
    // (the archmage's own hat stands for any hat)
  } else if (hat && HAT_ADDON[hat]) {
    const c = clothOf(h, cls);
    addons.push({ kind: HAT_ADDON[hat], on: headPart, bone: 'head', spot: 'crown', hat: true,
      roles: { cloth: worn(c, h), trim: trimFor(h) || darkOf(c, h), accent: h.e ? gemFor(h, cls) : PLUME[cls] || 'white' } });
  } else if (h && HEAD[h.k]) {
    const name = add(HEAD[h.k], headRoles(h, cls), FIT[`${HEAD[h.k]}@${headModel}`]);
    if (name && h.k === 'helm' && (h.t || 0) >= 2) addons.push({ kind: 'crest', on: name, spot: 'top', roles: { cloth: h.s || h.c ? clothOf(h, cls) : PLUME[cls] || 'crimson' } });
  }
  // a masked cowl: a cloth over the face below the eyes, in the cowl's own colour
  if (hooded && h && h.v === 'masked') {
    const c = clothOf(h, cls);
    addons.push({ kind: 'facemask', on: headPart, bone: 'head', spot: 'crown', mask: true, roles: { cloth: darkOf(c, h), trim: trimFor(h) || worn(c, h) } });
  }
  if (h && h.k === 'crown') addons.push({ kind: 'crown', on: headPart, bone: 'head', spot: 'crown', variant: h.v,
    roles: { metal: worn(h.m || 'gold', h), gem: gemOr(h, 'gem_red') } });
  // the back: a cloak (or, from level 10, the class's own), the class's emblem on it from level 20
  let cape = null;
  if (look.back) cape = add(CAPE[look.back.v] || CAPE.rogue, capeRoles(look.back, cls));
  else if (rn >= 1) cape = add(CAPE[RENOWN_CAPE[cls] || 'rogue'], capeRoles({ k: 'cloak', t: 1 }, cls));
  if (cape && rn >= 2) addons.push({ kind: 'emblem', on: cape, spot: 'back', motif: cls, roles: { gold: rn >= 5 ? 'gold~glow' : rn >= 4 ? 'gold' : 'silver' } });
  if (look.quiver || (m && m.k === 'bow')) add('kit-quiver', {});
  // the shoulders: pauldrons on fine heavy armour, a mantle from level 35
  const b = look.body;
  if (!archmage && ((b && b.w >= 2 && (b.t || 0) >= 3) || rn >= 3)) {
    // fine heavy armour in its own metal; else a mantle in the class's colour, trimmed as renown rises
    const mantle = b && b.w >= 2 && b.m && (b.t || 0) >= 3 ? { metal: worn(b.m, b), metal_dark: trimFor(b) || darkOf(b.m, b) }
      : { metal: clothOf(b && (b.s || b.c) ? b : {}, cls), metal_dark: rn >= 4 ? 'gold' : 'silver' };
    for (const side of ['l', 'r']) {
      addons.push({ kind: 'pauldron', on: `${arms}-Arm${side === 'l' ? 'Left' : 'Right'}`, bone: `upperarm${side}`, spot: 'shoulder',
        side: side === 'l' ? 1 : -1, spikes: !!(b && (b.t || 0) >= 4 && b.w >= 2), roles: mantle });
    }
  }
  // a light: a lantern at the hip, a torch in a free hand
  const light = look.light && look.light.k;
  if (light === 'lantern') addons.push({ kind: 'lantern', shape: true, bone: 'hips', spot: 'hip', roles: { gem: 'fire~glow', metal_dark: 'black_iron' } });
  const handFree = !o && !(m && (m.h === 2 || m.k === 'bow'));
  if (light === 'torch' && handFree) procs.push({ shape: 'torch', piece: 'knight-1H_Sword_Offhand', look: { k: 'torch', t: 1 }, roles: { gem: 'fire~glow' } });

  const twoHanded = m && (m.h === 2 || ['spear', 'polearm', 'scythe'].includes(m.k)) && !['bow', 'crossbow', 'staff'].includes(m.k);
  const key = `${look.sig || JSON.stringify(look)}|${cls}`;
  // what shines (equip.js lights the ~glow columns), and what lingers round the hero (adorn.js)
  const all = [...props.flatMap(p => Object.values(p.remap || {}).map(c => kit.columns[c] && kit.columns[c].name)),
    ...procs.flatMap(p => Object.values(p.roles)), ...addons.flatMap(a => Object.values(a.roles || {}))];
  const legendary = look.aura === 'legendary' || Object.values(look).some(p => p && typeof p === 'object' && p.t === 5);
  const glow = all.some(n => String(n || '').endsWith('~glow')) ? (legendary ? 1.3 : 1) : 0;
  const adorn = {
    motes: rn >= 4 ? `class_${cls}` : null,
    aura: look.aura || null,
    legendary,
    element: (m && m.e && (m.t || 0) >= 4) ? m.e : null,
    hand: m && m.k === 'bow' ? 'handslotl' : 'handslotr',     // where the weapon's sparks come from
    set: look.set || null,
  };
  return { key, parts: parts.map(p => p[0]), props, procs, addons, glow, adorn, build: { h: race.h * (sex ? SEX_BUILD[sex].h : 1), w: race.w * (sex ? SEX_BUILD[sex].w : 1) },
    idle: twoHanded ? '2H_Melee_Idle' : 'Idle' };
}

// ---- the ordinary blow from afar (combat_range.py): a bow, a crossbow or a thrown weapon
// shoots whoever holds it; a mage or a necromancer throws a bolt whatever they hold ----
const WEAPON_SHOT = { bow: { kind: 'shot', school: 'physical' }, crossbow: { kind: 'shot', school: 'physical' },
  thrown: { kind: 'shot', school: 'physical' } };
const CASTER_BOLT = { mage: { kind: 'bolt', school: 'arcane', size: 0.16 }, necromancer: { kind: 'bolt', school: 'necrotic', size: 0.16 } };
export function rangedBlow(look, cls) {
  const k = look && look.main && look.main.k;
  return WEAPON_SHOT[k] || CASTER_BOLT[String(cls || '').toLowerCase()] || null;
}

// ---- the swing: what the hand holds decides the blow ----
const ONE_H = ['1H_Melee_Attack_Chop', '1H_Melee_Attack_Slice_Diagonal', '1H_Melee_Attack_Slice_Horizontal'];
const TWO_H = ['2H_Melee_Attack_Chop', '2H_Melee_Attack_Slice', '2H_Melee_Attack_Stab'];
const DUAL = ['Dualwield_Melee_Attack_Stab', 'Dualwield_Melee_Attack_Slice', 'Dualwield_Melee_Attack_Chop'];
// ranged: whether the blow was a shot or a bolt (rangedBlow: the weapon in hand, else a caster's bolt)
export function swingClips(look, cls, ranged) {
  cls = String(cls || '').toLowerCase();
  const m = look && look.main, o = look && look.off;
  if (ranged) {
    if (m && m.k === 'crossbow') return [m.h === 2 ? '2H_Ranged_Shoot' : '1H_Ranged_Shoot'];
    if (m && m.k === 'bow') return ['2H_Ranged_Shoot'];
    if (/mage|necro|cleric/.test(cls) || (m && ['staff', 'wand'].includes(m.k))) return ['Spellcast_Shoot'];
    return ['Throw'];
  }
  if (!m) return ['Unarmed_Melee_Attack_Punch_A', 'Unarmed_Melee_Attack_Kick'];
  if (o && WEAPON_KINDS.has(o.k) && o.k !== 'bow') return DUAL;
  if (m.k === 'spear' || m.k === 'polearm') return ['2H_Melee_Attack_Stab', '2H_Melee_Attack_Slice'];
  if (m.h === 2 || m.k === 'scythe') return TWO_H;
  if (m.k === 'dagger' || m.k === 'claw') return ['1H_Melee_Attack_Stab', '1H_Melee_Attack_Slice_Diagonal'];
  return ONE_H;
}

// the manifest (equip.json), indexed for planLook
export function kitIndex(manifest) {
  const cols = new Map(manifest.columns.map((c, i) => [c.name, i]));
  return { ...manifest, N: manifest.palette.cols, col: name => (cols.has(name) ? cols.get(name) : null) };
}
