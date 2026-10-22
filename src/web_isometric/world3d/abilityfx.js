// How every ability looks (owner: "ensure animations for skills, spells, and abilities are
// unique and themed for every class"). Pure data and functions, no three.js: the Node tests
// (tests/web/abilityfx.test.mjs) check against the server's books that every ability of every
// class has a line of its own, built from clips the rig really has.
//
// A recipe is one line in abilityfx-table.js:
//
//   'body | cast | travel | land | aura | flags'
//
//   body    the user's clip from CLIPS (`chop`), its speed (`chop*1.3`), a second clip played
//           after it (`aim>bow`), and a body motion from MOTIONS (`chop2 rise`)
//   cast    what gathers at the user while the clip winds up (CASTS)
//   travel  what goes from the user to the target when it is released (TRAVELS)
//   land    what happens where it arrives: the target, or the user for self and area
//           abilities (LANDS)
//   aura    what lingers afterwards on whoever it was for (AURAS)
//   flags   a school (fire, frost...: the core colour), g=<glyph> (the motif instead of the
//           class's), r=<metres> (area), t=<seconds> (aura), shake / shake+ / stop (hit-stop) /
//           flash (the screen washes with colour) / heavy / ally (an ally is the target)
//
// A token is `kind`, `kind:arg` (orbs:3, growth:vines, burst:coin) or `kind+` (bigger).
// `-` leaves a column empty. Colours come from the class (THEMES: sigils, glyphs, trails)
// and the school (the projectile's core and the impact), so a cleric's and a paladin's
// heal are told apart even where a recipe's shape is alike; no two abilities of one class
// share a shape (signature()).

export const THEMES = {
  warrior: { core: 0xffa040, accent: 0xdfe6ee, glyph: 'chevron', motif: 'star', sigil: 'crest', school: 'physical', slash: 0xffd6a0 },
  paladin: { core: 0xffd56a, accent: 0x8fc8ff, glyph: 'sun', motif: 'cross', sigil: 'sunwheel', school: 'holy', slash: 0xffe8a8 },
  cleric: { core: 0xfff0c8, accent: 0xff9ab8, glyph: 'feather', motif: 'petal', sigil: 'rosette', school: 'holy', slash: 0xfff4dc },
  mage: { core: 0xb070ff, accent: 0x6ae8ff, glyph: 'rune', motif: 'star', sigil: 'runeCircle', school: 'arcane', slash: 0xd0a8ff },
  necromancer: { core: 0x8aff6a, accent: 0xe8e2cc, glyph: 'skull', motif: 'bone', sigil: 'boneCircle', school: 'necrotic', slash: 0xb8ffa0 },
  thief: { core: 0xffd040, accent: 0xb8c0c8, glyph: 'coin', motif: 'die', sigil: 'coinRing', school: 'shadow', slash: 0xfff0b0 },
  assassin: { core: 0xe0203a, accent: 0x9a5ae0, glyph: 'dagger', motif: 'drop', sigil: 'crosshair', school: 'shadow', slash: 0xff5a6a },
  ranger: { core: 0x7ad048, accent: 0xffb040, glyph: 'leaf', motif: 'paw', sigil: 'leafRing', school: 'nature', slash: 0xc8f0a0 },
  bard: { core: 0xff5ad8, accent: 0x40e0d0, glyph: 'note', motif: 'notes', sigil: 'staffRing', school: 'sound', slash: 0xffb8f0 },
  creature: { core: 0xffffff, accent: 0xd8d8e8, glyph: 'star', motif: 'star', sigil: 'ring', school: 'arcane', slash: 0xffc0b0 },
};

// a creature's kind (mobfx.js familyOf): the marks its abilities leave, its colours always its
// school's (so a lich's frostbolt and a shaman's are told apart by their glyphs and sigils, and
// any frost still reads as frost)
export const FAMILIES = {
  beast: { core: 0xffc0a0, accent: 0xe8d8c0, glyph: 'paw', motif: 'paw', sigil: 'crack', school: 'physical', slash: 0xffc0b0 },
  undead: { core: 0x8aff6a, accent: 0xd8e8c8, glyph: 'skull', motif: 'bone', sigil: 'boneCircle', school: 'necrotic', slash: 0xb8ffa0 },
  elemental: { core: 0x9fd8ff, accent: 0xffffff, glyph: 'shard', motif: 'wisp', sigil: 'runeCircle', school: 'arcane', slash: 0xc8e8ff },
  demon: { core: 0xff5a2a, accent: 0xffb040, glyph: 'flame', motif: 'eye', sigil: 'scorch', school: 'fire', slash: 0xff8a5a },
  insect: { core: 0xb8ff5a, accent: 0xe0f0a0, glyph: 'drop', motif: 'drop', sigil: 'ring', school: 'poison', slash: 0xd8ff9a },
  dragon: { core: 0xff7a2a, accent: 0xffd56a, glyph: 'flame', motif: 'shard', sigil: 'scorch', school: 'fire', slash: 0xffb070 },
  construct: { core: 0xc8ccd4, accent: 0xffe0a0, glyph: 'chevron', motif: 'shard', sigil: 'crest', school: 'physical', slash: 0xe8e0d0 },
  caster: { core: 0xc87aff, accent: 0x8fc8ff, glyph: 'rune', motif: 'star', sigil: 'runeCircle', school: 'arcane', slash: 0xd0a8ff },
};
// a class's theme, a creature family's, else the plain creature's
export const themeOf = cls => THEMES[cls] || FAMILIES[cls] || THEMES.creature;
export const isCreature = cls => !THEMES[cls] || cls === 'creature';

// short names for the rig's clips
export const CLIPS = {
  shoot: 'Spellcast_Shoot', raise: 'Spellcast_Raise', long: 'Spellcast_Long', summon: 'Spellcast_Summon', channel: 'Spellcasting',
  cheer: 'Cheer', taunt: 'Taunt', throw: 'Throw', interact: 'Interact', use: 'Use_Item', pickup: 'PickUp',
  block: 'Block', blockhit: 'Block_Attack', blocking: 'Blocking', kick: 'Unarmed_Melee_Attack_Kick', punch: 'Unarmed_Melee_Attack_Punch_A',
  chop: '1H_Melee_Attack_Chop', leapchop: '1H_Melee_Attack_Jump_Chop', diag: '1H_Melee_Attack_Slice_Diagonal',
  sweep: '1H_Melee_Attack_Slice_Horizontal', stab: '1H_Melee_Attack_Stab',
  chop2: '2H_Melee_Attack_Chop', slice2: '2H_Melee_Attack_Slice', spin2: '2H_Melee_Attack_Spin', stab2: '2H_Melee_Attack_Stab',
  dchop: 'Dualwield_Melee_Attack_Chop', dslice: 'Dualwield_Melee_Attack_Slice', dstab: 'Dualwield_Melee_Attack_Stab',
  aim: '1H_Ranged_Aiming', bow: '1H_Ranged_Shoot', aim2: '2H_Ranged_Aiming', bow2: '2H_Ranged_Shoot',
  dodgeL: 'Dodge_Left', dodgeR: 'Dodge_Right', dodgeB: 'Dodge_Backward', dodgeF: 'Dodge_Forward',
  sit: 'Sit_Floor_Down', awaken: 'Skeletons_Awaken_Standing', idle2h: '2H_Melee_Idle',
};
// when each clip lets go (seconds at speed 1): the blow lands, the spell leaves the hands
export const RELEASE = {
  shoot: 0.32, raise: 0.5, long: 0.62, summon: 0.6, channel: 0.5, cheer: 0.4, taunt: 0.38, throw: 0.3, interact: 0.38,
  use: 0.4, pickup: 0.42, block: 0.2, blockhit: 0.28, blocking: 0.25, kick: 0.24, punch: 0.2, chop: 0.3, leapchop: 0.45,
  diag: 0.26, sweep: 0.26, stab: 0.22, chop2: 0.4, slice2: 0.32, spin2: 0.42, stab2: 0.3, dchop: 0.3, dslice: 0.24,
  dstab: 0.2, aim: 0.35, bow: 0.22, aim2: 0.38, bow2: 0.26, dodgeL: 0.15, dodgeR: 0.15, dodgeB: 0.15, dodgeF: 0.15,
  sit: 0.5, awaken: 0.6, idle2h: 0.3,
};

// (slam, rear, recoil: a creature's body, which has no spellcasting clips, says it instead)
export const MOTIONS = ['leap', 'dash', 'spin', 'spin2', 'hover', 'rise', 'backstep', 'blink', 'hop', 'lunge', 'sidestep', 'blinks',
  'slam', 'rear', 'recoil'];
// what a creature's body does while it winds up (tell=<one>): rears back, drops low, coils to
// spring, trembles, gathers power with lifted hands, or goes still as it glows
export const TELLS = ['rear', 'crouch', 'coil', 'shudder', 'gather', 'still'];
export const CASTS = ['sigil', 'gather', 'glyphs', 'motifs', 'flare', 'rings', 'smoke', 'embers', 'aim', 'charge', 'spiral', 'orbit', 'dust'];
export const TRAVELS = ['slash', 'orb', 'orbs', 'glyph', 'motif', 'bolt', 'sky', 'chain', 'ray', 'skyray', 'tether', 'link', 'arrow',
  'arrows', 'rain', 'rainglyph', 'meteor', 'meteors', 'wave', 'cone', 'blade', 'blades', 'shards', 'pierce'];
export const LANDS = ['hit', 'sparks', 'burst', 'motifs', 'fountain', 'nova', 'blast', 'pillar', 'sigil', 'crack', 'quake', 'growth',
  'cloud', 'bubble', 'mark', 'swirl', 'geyser', 'shatter', 'freeze', 'halo', 'wings', 'smoke', 'rings', 'dome', 'heal', 'implode',
  'clones'];
export const AURAS = ['orbit', 'runes', 'blades', 'halo', 'wings', 'bubble', 'shroud', 'fade', 'glow', 'embers', 'notes', 'motes',
  'frost', 'flames', 'leaves', 'stone', 'bark', 'mirror', 'ghost', 'sigil', 'rage', 'poison', 'bleed', 'banner', 'seraph', 'lich'];
export const SCHOOLS = ['fire', 'frost', 'lightning', 'arcane', 'holy', 'shadow', 'necrotic', 'nature', 'poison', 'sound', 'physical', 'blood'];
export const GROWTHS = ['vines', 'bones', 'ice', 'crystals', 'bars', 'thorns', 'stones', 'spikes', 'spears'];
// slash:wide (a broad sweep), :up (rising), :x (two crossing), :rev (a backhand), :3 (three quick)
export const SLASHES = ['wide', 'up', 'x', 'rev'];
export const FLAGS = ['shake', 'shake+', 'stop', 'flash', 'heavy', 'ally', 'wide'];
// the glyphs a token may name (glyphs.js draws them)
export const GLYPH_NAMES = ['dot', 'star', 'note', 'notes', 'skull', 'bone', 'cross', 'snow', 'bolt', 'leaf', 'feather', 'coin', 'die',
  'rune', 'sun', 'drop', 'flame', 'petal', 'shard', 'dagger', 'eye', 'chevron', 'paw', 'wisp', 'ring'];

// how long things take on their way (seconds), by travel kind; per metre for the flying ones
const FLIGHT = { orb: 1 / 20, orbs: 1 / 18, glyph: 1 / 16, motif: 1 / 16, arrow: 1 / 30, arrows: 1 / 28, blade: 1 / 24, blades: 1 / 22,
  shards: 1 / 26, wave: 1 / 14, link: 1 / 30, pierce: 1 / 45 };
const FIXED = { slash: 0.1, bolt: 0.06, sky: 0.12, chain: 0.12, ray: 0.08, skyray: 0.2, tether: 0.3, rain: 0.62, rainglyph: 0.62,
  meteor: 0.78, meteors: 0.95, cone: 0.24 };

function tok(s) {
  s = String(s || '').trim();
  if (!s || s === '-') return null;
  const big = s.endsWith('+');
  if (big) s = s.slice(0, -1);
  const i = s.indexOf(':');
  return { kind: i < 0 ? s : s.slice(0, i), arg: i < 0 ? null : s.slice(i + 1), big };
}
const tokStr = t => (t ? `${t.kind}${t.arg != null ? ':' + t.arg : ''}${t.big ? '+' : ''}` : '-');

// a recipe line -> {clip, speed, then, motion, cast, travel, land, aura, school, glyph, radius, time, flags}
export function parse(line) {
  const cols = String(line).split('|').map(s => s.trim());
  const [body = '', cast, travel, land, aura, flags = ''] = cols;
  const [clipPart = '', motion = null] = body.split(/\s+/);
  const [first, second] = clipPart.split('>');
  const [clip, speed] = first.split('*');
  const [then, thenSpeed] = second ? second.split('*') : [null, null];
  const r = { clip, speed: speed ? Number(speed) : 1, then: then || null, thenSpeed: thenSpeed ? Number(thenSpeed) : 1, motion: motion || null,
    cast: tok(cast), travel: tok(travel), land: tok(land), aura: tok(aura), school: null, glyph: null, radius: null, time: null, tell: null, flags: new Set(), cols: cols.length };
  for (const f of flags.split(/\s+/).filter(Boolean)) {
    if (SCHOOLS.includes(f)) r.school = f;
    else if (f.startsWith('tell=')) r.tell = f.slice(5);
    else if (f.startsWith('g=')) r.glyph = f.slice(2);
    else if (f.startsWith('r=')) r.radius = Number(f.slice(2));
    else if (f.startsWith('t=')) r.time = Number(f.slice(2));
    else r.flags.add(f);
  }
  return r;
}

// what is wrong with a line (empty: nothing); `clips` are the rig's clip names
export function validate(line, clips = null) {
  const r = parse(line), out = [];
  if (r.cols !== 6) out.push(`needs 6 columns, has ${r.cols}`);
  for (const c of [r.clip, r.then].filter(Boolean)) {
    if (!CLIPS[c]) out.push(`unknown clip ${c}`);
    else if (clips && !clips.includes(CLIPS[c])) out.push(`the rig has no ${CLIPS[c]}`);
  }
  if (!(r.speed > 0.3 && r.speed < 3) || !(r.thenSpeed > 0.3 && r.thenSpeed < 3)) out.push('speed out of range');
  if (r.motion && !MOTIONS.includes(r.motion)) out.push(`unknown motion ${r.motion}`);
  const check = (t, list, col) => { if (t && !list.includes(t.kind)) out.push(`unknown ${col} ${t.kind}`); };
  check(r.cast, CASTS, 'cast'); check(r.travel, TRAVELS, 'travel'); check(r.land, LANDS, 'land'); check(r.aura, AURAS, 'aura');
  for (const t of [r.travel, r.land, r.aura]) {
    if (!t || t.arg == null) continue;
    if (t.kind === 'growth') { if (!GROWTHS.includes(t.arg)) out.push(`unknown growth ${t.arg}`); }
    else if (t.kind === 'slash') { if (!SLASHES.includes(t.arg) && !/^[23]$/.test(t.arg)) out.push(`unknown slash ${t.arg}`); }
    else if (/^\d+$/.test(t.arg)) { if (Number(t.arg) < 1 || Number(t.arg) > 24) out.push(`count ${t.arg} out of range`); }
    else if (t.arg === 'big') { /* orb:big */ }
    else if (!GLYPH_NAMES.includes(t.arg)) out.push(`unknown glyph ${t.arg}`);
  }
  if (r.glyph && !GLYPH_NAMES.includes(r.glyph)) out.push(`unknown glyph ${r.glyph}`);
  if (r.tell && !TELLS.includes(r.tell)) out.push(`unknown tell ${r.tell}`);
  for (const f of r.flags) if (!FLAGS.includes(f)) out.push(`unknown flag ${f}`);
  return out;
}

// the shape of a recipe, without its colours: no two abilities of a class may share one
export function signature(r) {
  if (typeof r === 'string') r = parse(r);
  return [`${r.clip}${r.then ? '>' + r.then : ''}`, r.motion || '-', tokStr(r.cast), tokStr(r.travel), tokStr(r.land), tokStr(r.aura)].join('|');
}

// when it lets go and when it lands (seconds from the start), over `dist` metres
export function timeline(r, dist = 6) {
  let release = (RELEASE[r.clip] || 0.35) / (r.speed || 1);
  if (r.then) release += 0.3 / (r.speed || 1) + (RELEASE[r.then] || 0.3) / (r.thenSpeed || 1);
  if (r.motion === 'leap') release = Math.max(release, 0.5);
  else if (r.motion === 'rise') release = Math.max(release, 0.7);
  else if (r.motion === 'slam') release = Math.max(release, 0.42);
  else if (r.motion === 'dash') release = Math.max(release, 0.3);
  else if (r.motion === 'blink' || r.motion === 'blinks') release = Math.max(release, 0.22);
  const t = r.travel;
  const travel = !t ? 0 : FIXED[t.kind] != null ? FIXED[t.kind] : (FLIGHT[t.kind] || 1 / 20) * dist * (t.arg === 'big' ? 1.35 : 1);
  const land = release + travel;
  return { release, travel, land, end: land + 0.6 };
}

// a song, an elemental, a servant, an aura: the word chooses the colour
export const VARIANT_SCHOOL = {
  fire: 'fire', water: 'frost', earth: 'nature', air: 'lightning',
  knight: 'necrotic', wraith: 'shadow', lich: 'frost', stalker: 'poison',
  devotion: 'holy', protection: 'holy', retribution: 'fire', concentration: 'arcane', crusader: 'holy',
  courage: 'holy', battle_hymn: 'blood', dirge: 'shadow', discord: 'arcane', rest: 'frost', lullaby: 'frost',
  inspiration: 'nature', destruction: 'fire',
};

// what an unknown ability (a creature's special, something added later) looks like, by what
// the event says about it
function fallbackLine(ev = {}, cls = '') {
  const shape = String(ev.shape || ''), school = ev.school || themeOf(cls).school;
  if (shape === 'self') return `raise | glyphs | - | - | glow | ${school}`;
  if (shape.startsWith('nova')) return `cheer | rings | - | nova | - | ${school}`;
  if (shape.startsWith('cone')) return `long | - | cone | - | - | ${school}`;
  if (shape === 'dash') return `leapchop dash | dust | - | crack | - | ${school}`;
  // a creature's wind-up, by the kind of thing it is (mob_ai intents: combat_hooks 'windup')
  const kind = String(ev.kind || '');
  if (kind === 'heavy') return `chop2 slam | dust | - | crack | - | ${school} shake tell=rear`;
  if (kind === 'aoe') return `spin2 | dust | - | quake | - | ${school} shake tell=crouch`;
  if (kind === 'debuff') return `long | glyphs | tether | mark | - | ${school} tell=gather`;
  if (kind === 'heal') return `raise | sigil | - | heal | - | ${ev.school || 'holy'} ally tell=gather`;
  if (kind === 'disrupt') return `taunt | rings | ray | rings | - | sound tell=still`;
  if (ev.k === 'spell' || kind === 'cast' || shape.startsWith('blast')) {
    return ({
      fire: 'shoot | gather | orb | blast | - | fire', frost: 'shoot | - | shards:3 | freeze | - | frost',
      lightning: 'shoot | flare | bolt | hit+ | - | lightning', holy: 'raise | flare | - | pillar | - | holy',
      necrotic: 'shoot | - | glyph:skull | burst:skull | - | necrotic', shadow: 'shoot | smoke | orb | burst:eye | - | shadow',
      poison: 'shoot | - | glyph:drop | cloud | - | poison', nature: 'throw | - | - | growth:vines | - | nature',
      sound: 'taunt | rings | - | burst:note | - | sound', blood: 'shoot | - | orb | burst:drop | - | blood',
    })[school] || `shoot | - | orb | hit | - | ${school}`;
  }
  if (shape === 'ranged') return `throw | - | glyph | hit | - | ${school}`;
  return `chop | - | slash | hit | - | ${school}`;
}

const norm = s => String(s || '').toLowerCase().replace(/[\s'-]+/g, '_');
const cache = new Map();

// the recipe for an ability used by someone of a class (no class: a creature): the class's
// own line, else one built from what the event says; `table` is abilityfx-table.js
export function recipeFor(table, id, cls, ev = {}) {
  const key = norm(id), c = THEMES[norm(cls)] ? norm(cls) : 'creature';
  const line = (table[c] && table[c][key]) || null;
  const ck = line ? `${c}:${key}` : `${c}:?${key}:${ev.k || ''}:${ev.shape || ''}:${ev.school || ''}`;
  if (cache.has(ck)) return cache.get(ck);
  const r = parse(line || fallbackLine(ev, c));
  r.id = key; r.cls = c; r.known = !!line;
  cache.set(ck, r);
  return r;
}

// a creature's ability (its `fx`, combat_hooks.fx_key): the first of `tables` with a line for it
// (mobfx-hand.js, then the lines tools/jev_mobfx.py writes), else one from what the event says;
// drawn in its family's marks (FAMILIES) and cut to its rank (forRank)
export function creatureRecipe(tables, id, family, ev = {}, rank = 'normal') {
  const key = norm(id), fam = FAMILIES[family] ? family : 'creature';
  const line = tables.map(t => t && t[key]).find(Boolean) || null;
  const ck = `mob:${fam}:${rank}:${line ? key : `?${key}:${ev.k || ''}:${ev.shape || ''}:${ev.school || ''}`}`;
  if (cache.has(ck)) return cache.get(ck);
  const r = forRank(parse(line || fallbackLine(ev, fam)), rank);
  r.id = key; r.cls = fam; r.known = !!line;
  cache.set(ck, r);
  return r;
}

// the owner: a creature's spells look as big as its rank. A boss gets every flourish; an elite
// shakes the view a little; an ordinary creature's are readable but plain, so the hero's own
// stay the brightest thing in the fight (no shake, no hit-stop or flash, nothing in its large
// size, nothing lingering)
export const RANKS = ['normal', 'elite', 'boss'];
export function rankOf(data = {}) {
  if (data.boss) return 'boss';
  return data.rank === 'elite' || data.rank === 'sub-boss' ? 'elite' : 'normal';
}
export function forRank(r, rank = 'normal') {
  if (rank === 'boss') return r;
  const out = { ...r, flags: new Set(r.flags) };
  for (const f of ['stop', 'flash']) out.flags.delete(f);
  if (out.flags.delete('shake+') && rank === 'elite') out.flags.add('shake');
  if (rank === 'normal') {
    out.calm = true;               // (its landing doesn't shake the view either: fxdirector.js land)
    out.flags.delete('shake');
    for (const k of ['cast', 'travel', 'land', 'aura']) if (out[k] && out[k].big) out[k] = { ...out[k], big: false };
    // a lasting ward or curse keeps its mark (it is how you see it is on); a flourish goes
    if (out.aura && !out.flags.has('ally')) out.aura = null;
  }
  return out;
}
