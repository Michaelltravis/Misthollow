// What /play sounds like: a pure-data table (no audio here; audio.js plays it, the Node tests
// read it). A sound is a recorded file (audio/sfx/<file>_<n>.mp3, one of `n` variants picked
// at random), a synth made in the browser (audio.js SYNTHS), or layers of both.
//   { file, n } | { synth, tier } | { layers: [key, ...] }  + vol (0..1), rate (± pitch spread),
//   bus ('sfx' | 'ui' | 'amb'), gap (min seconds between two of it), pos (placed in the world)

// recorded variants per file key (tools/audio/manifest.json; audio/files.json is checked against it)
export const FILES = {
  step_grass: 5, step_stone: 5, step_wood: 5, step_snow: 5, step_carpet: 5, step_dirt: 5,
  hit_punch: 5, hit_heavy: 5, hit_soft: 3, hit_blade: 3, parry: 4, block: 3, clang: 3, clang_heavy: 3,
  shatter: 3, shatter_big: 2, bell: 2, stone: 3, wood: 3,
  door_open: 2, door_close: 4, creak: 3, latch: 1, lock: 1, coins: 2, cloth: 4, belt: 3, leather: 3,
  book_open: 1, book_close: 1, book_flip: 3, draw_blade: 3,
  ui_click: 3, ui_select: 2, ui_open: 2, ui_close: 2, ui_confirm: 2, ui_error: 2, ui_toggle: 2,
  ui_drop: 2, ui_scroll: 1, ui_question: 1, ui_hover: 2, ui_pluck: 2, ui_bong: 1,
};

export const SOUNDS = {
  // ---- blows ----
  swing:        { synth: 'whoosh', vol: 0.55, gap: 0.05, pos: true },
  swing_heavy:  { synth: 'whoosh', tier: 2, vol: 0.65, pos: true },
  shot:         { synth: 'bowstring', vol: 0.6, pos: true },
  bolt:         { synth: 'zap', vol: 0.45, pos: true },
  hit:          { file: 'hit_punch', vol: 0.55, rate: 0.12, gap: 0.04, pos: true },
  hit_blade:    { file: 'hit_blade', vol: 0.5, rate: 0.1, pos: true },
  hit_heavy:    { file: 'hit_heavy', vol: 0.7, rate: 0.08, pos: true },
  crit:         { layers: ['hit_heavy', 'crit_ring'] },
  crit_ring:    { synth: 'ring', vol: 0.4, pos: true },
  hurt:         { layers: ['hit_soft', 'hurt_grunt'] },
  hit_soft:     { file: 'hit_soft', vol: 0.6, rate: 0.1, pos: true },
  hurt_grunt:   { synth: 'thud', vol: 0.45 },
  miss:         { synth: 'whiff', vol: 0.35, pos: true },
  dodge:        { synth: 'whiff', tier: 2, vol: 0.4, pos: true },
  parry:        { file: 'parry', vol: 0.55, rate: 0.1, pos: true },
  block:        { file: 'block', vol: 0.6, rate: 0.08, pos: true },
  resist:       { synth: 'shimmer', vol: 0.3, pos: true },
  // ---- what happens to someone ----
  heal:         { synth: 'heal', vol: 0.45, gap: 0.15, pos: true },
  buff:         { synth: 'buff', vol: 0.4, gap: 0.2, pos: true },
  debuff:       { synth: 'debuff', vol: 0.4, gap: 0.2, pos: true },
  stun:         { synth: 'stun', vol: 0.45, pos: true },
  death:        { layers: ['hit_heavy', 'fall'] },
  fall:         { synth: 'fall', vol: 0.5, pos: true },
  hero_death:   { synth: 'death', vol: 0.8 },
  // ---- a creature's big blow ----
  windup:       { synth: 'windup', vol: 0.55, pos: true },
  resolve:      { layers: ['slam', 'hit_heavy'] },
  slam:         { synth: 'slam', vol: 0.75, pos: true },
  cancel:       { file: 'clang', vol: 0.55, pos: true },
  fizzle:       { synth: 'fizzle', vol: 0.35, pos: true },
  growl:        { synth: 'growl', vol: 0.6, gap: 0.6, pos: true },
  alert:        { synth: 'alert', vol: 0.5, gap: 0.4, pos: true },
  rain:         { synth: 'rain', vol: 0.7, gap: 1, bus: 'amb' },
  thunder:      { synth: 'thunder', vol: 0.9, gap: 2, bus: 'amb' },
  flutter:      { synth: 'flutter', vol: 0.6, gap: 0.5, pos: true },
  heartbeat:    { synth: 'heartbeat', vol: 0.8, bus: 'ui', gap: 0.3 },
  // ---- skills and spells, by phase (school stings from the 2D client, fx-schools.js) ----
  charge:       { synth: 'charge', vol: 0.32, pos: true },
  travel:       { synth: 'whoosh', tier: 3, vol: 0.4, pos: true },
  sting:        { synth: 'school', vol: 0.8, pos: true },
  aura:         { synth: 'shimmer', vol: 0.28, pos: true },
  shatter:      { file: 'shatter', vol: 0.45, pos: true },
  shatter_big:  { file: 'shatter_big', vol: 0.55, pos: true },
  bell:         { file: 'bell', vol: 0.35, pos: true },
  stone:        { file: 'stone', vol: 0.5, pos: true },
  wood:         { file: 'wood', vol: 0.5, pos: true },
  clang:        { file: 'clang', vol: 0.5, pos: true },
  // ---- getting about ----
  step_grass:   { file: 'step_grass', vol: 0.22, rate: 0.08 },
  step_stone:   { file: 'step_stone', vol: 0.2, rate: 0.08 },
  step_wood:    { file: 'step_wood', vol: 0.22, rate: 0.08 },
  step_snow:    { file: 'step_snow', vol: 0.24, rate: 0.08 },
  step_carpet:  { file: 'step_carpet', vol: 0.2, rate: 0.08 },
  step_dirt:    { file: 'step_dirt', vol: 0.2, rate: 0.08 },
  step_water:   { synth: 'splash', vol: 0.3 },
  door_open:    { layers: ['latch', 'door_open_body'] },
  door_open_body: { file: 'door_open', vol: 0.55, pos: true },
  door_close:   { file: 'door_close', vol: 0.55, pos: true },
  latch:        { file: 'latch', vol: 0.5, pos: true },
  lock:         { file: 'lock', vol: 0.55, pos: true },
  creak:        { file: 'creak', vol: 0.4, pos: true },
  // ---- the world's murmurs (ambient.js; the server's ambient_lines.py names them): placed
  // where they come from, on the ambience bus ----
  amb_anvil:    { file: 'clang', vol: 0.22, rate: 0.06, gap: 1, bus: 'amb', pos: true },
  amb_bell:     { file: 'bell', vol: 0.3, rate: 0.03, gap: 2, bus: 'amb', pos: true },
  amb_creak:    { file: 'creak', vol: 0.25, rate: 0.08, gap: 1, bus: 'amb', pos: true },
  amb_door:     { file: 'door_close', vol: 0.28, rate: 0.12, gap: 1, bus: 'amb', pos: true },
  amb_coins:    { file: 'coins', vol: 0.25, gap: 1, bus: 'amb', pos: true },
  amb_chain:    { file: 'clang_heavy', vol: 0.14, rate: 0.25, gap: 1, bus: 'amb', pos: true },
  amb_cart:     { layers: ['amb_cart_wood', 'amb_cart_roll'] },
  amb_cart_wood: { file: 'wood', vol: 0.2, rate: 0.15, gap: 1, bus: 'amb', pos: true },
  amb_cart_roll: { synth: 'rumble', vol: 0.5, gap: 1, bus: 'amb', pos: true },
  amb_crowd:    { synth: 'murmur', vol: 0.7, gap: 1, bus: 'amb', pos: true },
  amb_drip:     { synth: 'drip', vol: 0.6, gap: 0.5, bus: 'amb', pos: true },
  amb_wind:     { synth: 'gust', vol: 0.7, gap: 1, bus: 'amb', pos: true },
  amb_steps:    { synth: 'steps', vol: 0.8, gap: 1, bus: 'amb', pos: true },
  hop:          { synth: 'hop', vol: 0.4 },
  teleport:     { synth: 'teleport', vol: 0.5 },
  // ---- the interface ----
  ui_click:     { file: 'ui_click', vol: 0.35, bus: 'ui', gap: 0.03 },
  ui_hover:     { file: 'ui_hover', vol: 0.12, bus: 'ui', gap: 0.06 },
  ui_open:      { file: 'ui_open', vol: 0.35, bus: 'ui' },
  ui_close:     { file: 'ui_close', vol: 0.35, bus: 'ui' },
  ui_confirm:   { file: 'ui_confirm', vol: 0.4, bus: 'ui' },
  ui_error:     { file: 'ui_error', vol: 0.35, bus: 'ui', gap: 0.4 },
  ui_toggle:    { file: 'ui_toggle', vol: 0.35, bus: 'ui' },
  ui_drop:      { file: 'ui_drop', vol: 0.4, bus: 'ui' },
  ui_offer:     { file: 'ui_bong', vol: 0.45, bus: 'ui' },
  book_open:    { file: 'book_open', vol: 0.5, bus: 'ui' },
  book_close:   { file: 'book_close', vol: 0.5, bus: 'ui' },
  book_flip:    { file: 'book_flip', vol: 0.45, bus: 'ui', gap: 0.1 },
  bag_open:     { file: 'leather', vol: 0.5, bus: 'ui' },
  equip:        { file: 'belt', vol: 0.5, bus: 'ui' },
  cloth:        { file: 'cloth', vol: 0.45, bus: 'ui' },
  coins:        { file: 'coins', vol: 0.5, bus: 'ui', gap: 0.2 },
  draw:         { file: 'draw_blade', vol: 0.45 },
  levelup:      { synth: 'fanfare', vol: 0.6, bus: 'ui' },
  quest_done:   { synth: 'fanfare', tier: 2, vol: 0.55, bus: 'ui' },
  quest_stage:  { synth: 'chime', vol: 0.45, bus: 'ui' },
  toast:        { file: 'ui_pluck', vol: 0.25, bus: 'ui', gap: 0.5 },
  improve:      { synth: 'chime', tier: 2, vol: 0.4, bus: 'ui' },
};

// combat events (combat_events.py `k`) -> the sound at the moment it is drawn; null = silent
// (its sound comes from another moment: a wound's blow, a move's footsteps)
export const EVENTS = {
  attack: 'swing', ability: null, spell: null, dmg: null, heal: 'heal', buff: 'buff', debuff: 'debuff',
  windup: 'windup', resolve: 'resolve', cancel: 'cancel', death: 'death', stun: 'stun', oor: null,
  fizzle: 'fizzle', move: null, proc: 'sting',
};
// where a blow arrives (combat.js land), by its result
export const LANDS = {
  hit: 'hit', crit: 'crit', miss: 'miss', dodge: 'dodge', parry: 'parry', block: 'block',
  resist: 'resist', immune: 'resist',
};

// a skill's or spell's school: its sting (synth) and what it strikes like (a recorded impact)
export const SCHOOLS = {
  fire: { impact: 'hit_heavy' }, frost: { impact: 'shatter' }, lightning: { impact: null },
  holy: { impact: 'bell' }, shadow: { impact: null }, necrotic: { impact: null }, blood: { impact: 'hit_soft' },
  poison: { impact: null }, nature: { impact: 'wood' }, sound: { impact: null }, song: { impact: null },
  arcane: { impact: null }, physical: { impact: 'hit_heavy' }, earth: { impact: 'stone' },
};
export const schoolOf = s => (SCHOOLS[s] ? s : s === 'necrotic' ? 'shadow' : 'arcane');

// footsteps by what is underfoot
export function surfaceFor({ theme, zoneKey, snowy, icy, interior } = {}) {
  if (snowy || icy || theme === 'snow' || theme === 'ice_cave' || zoneKey === 'frozen') return 'step_snow';
  // a room's look (room_looks.py) before its zone's
  if (['cave', 'mine', 'crypt', 'sewer', 'volcanic', 'lava_cave'].includes(theme)) return 'step_stone';
  if (theme === 'desert' || theme === 'shore') return 'step_dirt';
  if (theme === 'inside') return interior === 'tavern' || interior === 'house' || interior === 'bedroom' || interior === 'library' ? 'step_wood'
    : interior === 'throne' || interior === 'temple' ? 'step_carpet' : 'step_stone';
  if (theme === 'city' || theme === 'castle' || theme === 'necropolis' || theme === 'drow' || theme === 'dungeon' || theme === 'cave' || theme === 'mountain') return 'step_stone';
  if (theme === 'forest' || theme === 'field' || theme === 'hills' || theme === 'village' || theme === 'camp' || theme === 'garden' || theme === 'stones' || zoneKey === 'meadow' || zoneKey === 'elven') return 'step_grass';
  return 'step_dirt';
}

// music by the zone's look; fights bring in the battle track
export const MUSIC = ['town', 'wilds', 'inn', 'dungeon', 'dark', 'battle'];
const DARK = new Set(['web', 'darkforest', 'swamp', 'necropolis', 'darkcastle', 'voidstar', 'volcanic', 'drow']);
const DUNGEON = new Set(['sewer', 'mines', 'dwarvenhall', 'clockwork', 'arcane']);
const TOWN = new Set(['midgaard', 'rome', 'sandstone', 'castle', 'temple', 'chessboard']);
export function musicFor({ theme, zoneKey, dark, interior } = {}) {
  if (theme === 'inside' && interior === 'tavern') return 'inn';
  if (theme === 'crypt' || theme === 'volcanic' || theme === 'web' || theme === 'necropolis' || theme === 'drow') return 'dark';
  if (theme === 'cave' || theme === 'mine' || theme === 'sewer') return 'dungeon';
  if (DARK.has(zoneKey)) return 'dark';
  if (theme === 'castle') return 'town';
  if (DUNGEON.has(zoneKey) || dark || theme === 'dungeon' || theme === 'cave') return 'dungeon';
  if (TOWN.has(zoneKey) || theme === 'city' || theme === 'inside') return 'town';
  return 'wilds';
}

// ambience beds (from the 2D client, immersion.js): a filtered-noise room tone [band Hz, level]
// and a recurring call (birds, drips, clanks, hums) by the zone's look
export const BEDS = {
  forest:     { wind: [320, 0.016], chirp: { f: [900, 1500], every: [2.5, 7], dur: 0.12, vol: 0.022 } },
  meadow:     { wind: [380, 0.014], chirp: { f: [900, 1600], every: [2, 6], dur: 0.1, vol: 0.02 } },
  autumn:     { wind: [300, 0.02], chirp: { f: [700, 1100], every: [5, 12], dur: 0.14, vol: 0.016 } },
  darkforest: { wind: [220, 0.018], chirp: { f: [300, 500], every: [6, 14], dur: 0.4, vol: 0.018 } },
  elven:      { wind: [420, 0.012], chirp: { f: [1100, 1700], every: [3, 8], dur: 0.16, vol: 0.018 } },
  swamp:      { wind: [180, 0.016], chirp: { f: [220, 420], every: [3, 8], dur: 0.25, vol: 0.02 } },
  midgaard:   { wind: [500, 0.010], chirp: { f: [400, 800], every: [4, 10], dur: 0.18, vol: 0.012 } },
  sandstone:  { wind: [450, 0.012], chirp: { f: [500, 900], every: [5, 12], dur: 0.15, vol: 0.012 } },
  rome:       { wind: [480, 0.010], chirp: { f: [500, 900], every: [5, 12], dur: 0.15, vol: 0.012 } },
  temple:     { wind: [240, 0.010], chirp: { f: [520, 660], every: [8, 18], dur: 1.0, vol: 0.012 } },
  sewer:      { wind: [140, 0.014], chirp: { f: [1300, 2100], every: [1.5, 5], dur: 0.05, vol: 0.025, drip: true } },
  mines:      { wind: [110, 0.016], chirp: { f: [1100, 1900], every: [3, 9], dur: 0.06, vol: 0.02, drip: true } },
  dwarvenhall:{ wind: [150, 0.014], chirp: { f: [200, 320], every: [4, 9], dur: 0.2, vol: 0.02 } },
  drow:       { wind: [120, 0.016], chirp: { f: [1500, 2400], every: [4, 11], dur: 0.05, vol: 0.018, drip: true } },
  desert:     { wind: [520, 0.02], chirp: null },
  frozen:     { wind: [600, 0.024], chirp: { f: [800, 1300], every: [8, 18], dur: 0.3, vol: 0.012 } },
  volcanic:   { wind: [90, 0.02], chirp: { f: [140, 240], every: [3, 8], dur: 0.4, vol: 0.022 } },
  necropolis: { wind: [160, 0.018], chirp: { f: [260, 380], every: [7, 16], dur: 0.8, vol: 0.014 } },
  sunken:     { wind: [200, 0.018], chirp: { f: [600, 1000], every: [2, 6], dur: 0.3, vol: 0.018 } },
  clockwork:  { wind: [260, 0.012], chirp: { f: [320, 540], every: [1.2, 3], dur: 0.08, vol: 0.018 } },
  voidstar:   { wind: [80, 0.014], chirp: { f: [1800, 2600], every: [4, 10], dur: 0.5, vol: 0.012 } },
  arcane:     { wind: [100, 0.012], chirp: { f: [1600, 2400], every: [3, 8], dur: 0.4, vol: 0.014 } },
  castle:     { wind: [340, 0.012], chirp: null },
  darkcastle: { wind: [200, 0.018], chirp: { f: [180, 300], every: [6, 15], dur: 0.6, vol: 0.014 } },
  chessboard: { wind: [260, 0.008], chirp: null },
};
// a room with no zone look of its own: a bed by its terrain
const BED_OF_THEME = { forest: 'forest', field: 'meadow', hills: 'meadow', swamp: 'swamp', desert: 'desert',
  cave: 'mines', dungeon: 'sewer', city: 'midgaard', inside: 'castle', mountain: 'frozen', water_swim: 'sunken',
  water_noswim: 'sunken', underwater: 'sunken' };
// a room's look (room_looks.py) says more than its zone's old theme
export const LOOK_BED = { cave: 'mines', mine: 'mines', sewer: 'sewer', crypt: 'necropolis', dungeon: 'sewer',
  snow: 'frozen', desert: 'desert', volcanic: 'volcanic', shore: 'sunken', stones: 'meadow', village: 'meadow', camp: 'meadow', garden: 'meadow', ruins: 'desert', terrace: 'castle', ice_cave: 'frozen', lava_cave: 'volcanic', swamp: 'swamp', web: 'darkforest', castle: 'castle', necropolis: 'necropolis', drow: 'drow' };
export function bedFor({ theme, zoneKey } = {}) {
  if (LOOK_BED[theme]) return LOOK_BED[theme];
  if (theme === 'inside') return 'castle';                     // indoors: a quiet room tone
  return BEDS[zoneKey] ? zoneKey : BED_OF_THEME[theme] || 'meadow';
}

// how many voices at once, by graphics quality (low-end machines get fewer)
export const VOICES = { low: 10, medium: 16, high: 24 };
