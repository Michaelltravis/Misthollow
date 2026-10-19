// Which steed each mount is (steed.js draws it): the creature kit's body, coat words and colour,
// its size beside its rider, and its extras. Pure, so Node can check it (tests/web/steeds.test.mjs).

// key -> [kit body, coat words, coat colour, height as a share of the rider's, extras]
export const STEEDS = {
  horse: ['horse', 'bay horse', 0x6b4a2e, 1.0, {}],
  warhorse: ['horse', 'grey horse', 0x6a6a70, 1.1, { barding: 0x7a2a22 }],
  armored_warhorse: ['horse', 'white horse', 0xc8c4bc, 1.1, { barding: 0x2a4a8a }],
  celestial_charger: ['horse', 'white horse', 0xf0ece0, 1.1, { barding: 0xe8c860, glow: 0xffe8a0 }],
  nightmare: ['horse', 'black infernal horse', 0x18141a, 1.1, { flames: true }],
  nightmare_steed: ['horse', 'black infernal horse', 0x18141a, 1.1, { flames: true }],
  clockwork_steed: ['horse', 'brass horse', 0xb8904a, 1.05, { brass: true }],
  donkey: ['horse', 'grey donkey', 0x8a8478, 0.8, {}],
  pony: ['horse', 'dappled pony', 0xd8ccb0, 0.8, {}],
  griffin: ['cat', 'golden lion', 0xc89a52, 0.95, { wings: 0xd8b880 }],
  manabound_gryphon: ['cat', 'blue', 0x5a7ac8, 0.95, { wings: 0x9ab8ff, glow: 0x8ab0ff }],
  mana_wyrm: ['horse', 'blue spectral', 0x4a6ad8, 1.0, { glow: 0x9ab8ff }],
  moonstag: ['deer', 'white silver stag', 0xdcdce8, 1.05, {}],
  stoneboar: ['pig', 'grey boar', 0x6a625a, 0.8, { barding: 0x5a5a62 }],
  merchant_camel: ['llama', 'tan camel', 0xc8a878, 1.15, {}],
  shadowpanther: ['cat', 'black panther', 0x1a1820, 0.8, {}],
  shadowcat: ['cat', 'grey', 0x5a5a62, 0.75, {}],
  dire_warg: ['wolf', 'black warg', 0x2a2622, 0.9, {}],
  riding_spider: ['wolf', 'black', 0x1e1a22, 0.8, { glow: 0x8a2aff }],
  drake_whelp: ['cat', 'red scaled', 0x8a2a1a, 0.85, { flames: true }],
  ancient_treant: ['cow', 'brown bark', 0x5a4028, 1.05, {}],
};
const DEFAULT = STEEDS.horse;
// where the saddle sits, as a share of the steed's height, by kit body
const BACK = { horse: 0.74, deer: 0.74, cat: 0.72, pig: 0.82, llama: 0.64, wolf: 0.72, cow: 0.76 };


// How each mount looks on its real body (bodies/*.glb, steed.js): the body, its coat (tint), its
// size beside the rider (1: the saddle at the rider's own ordinary height), its tack (tack.js:
// leather, war (a caparison), dark (a black caparison), plate, pack), the cloth and trim colours,
// and what marks it out (fx: hellfire, celestial, steam, arcane, moon, shadow, embers, leaves;
// wings; metal; ghost: see-through; plume: a war mount's plume colour)
export const MOUNT_LOOK = {
  horse: { body: 'horse', coat: 0x7a4a2a, tack: 'leather', cloth: 0x2a4a7a, trim: 0xc8a050 },
  warhorse: { body: 'horse', size: 1.1, coat: 0x6e6e74, tack: 'war', cloth: 0x8a1e1e, trim: 0xd8b04a },
  armored_warhorse: { body: 'horse', size: 1.1, coat: 0xd8d4cc, tack: 'war', plate: true, cloth: 0x1e3a7a, trim: 0xe0c060 },
  celestial_charger: { body: 'unicorn', size: 1.12, coat: 0xfff8ec, tack: 'war', cloth: 0xf2ead8, trim: 0xffcc40, plume: 0xffffff, glow: 0xffe8a0, fx: 'celestial' },
  nightmare: { body: 'horse', size: 1.1, coat: 0x141016, tack: 'dark', cloth: 0x1a0e0e, trim: 0xa01a08, fx: 'hellfire', eyes: 0xff5a10 },
  nightmare_steed: { body: 'horse', size: 1.1, coat: 0x141016, tack: 'dark', cloth: 0x1a0e0e, trim: 0xa01a08, fx: 'hellfire', eyes: 0xff5a10 },
  clockwork_steed: { body: 'horse', size: 1.05, coat: 0xd0a050, metal: true, tack: 'plate', steel: 0xb88a3a, trim: 0x6a4a2a, fx: 'steam', eyes: 0x6ae0ff },
  donkey: { body: 'horse', size: 0.84, coat: 0x8a8478, tack: 'pack', cloth: 0x7a5a3a, trim: 0x5a3a2a },
  pony: { body: 'horse', size: 0.86, coat: 0xd8ccb0, tack: 'leather', cloth: 0x3a7a3a, trim: 0xc8a050 },
  griffin: { body: 'lion', coat: 0xc89a52, wings: 0xe8d4a8, tack: 'leather', cloth: 0x7a2a22, trim: 0xd8b04a },
  manabound_gryphon: { body: 'lion', coat: 0x5a7ac8, wings: 0xa8c4ff, glow: 0x8ab0ff, tack: 'leather', cloth: 0x2a2a6a, trim: 0x9ab8ff, fx: 'arcane' },
  mana_wyrm: { body: 'dragon', size: 1.05, coat: 0x4a6ad8, ghost: 0.82, glow: 0x9ab8ff, tack: 'leather', cloth: 0x2a2a6a, trim: 0x9ab8ff, fx: 'arcane' },
  moonstag: { body: 'deer', size: 1.05, coat: 0xe8e8f4, glow: 0xc8d8ff, tack: 'leather', cloth: 0x3a4a7a, trim: 0xd8e0ff, fx: 'moon' },
  stoneboar: { body: 'pig', size: 0.95, coat: 0x6a625a, tack: 'war', plate: true, steel: 0x8a8a90, cloth: 0x4a4a52, trim: 0xa08a60 },
  merchant_camel: { body: 'camel', size: 0.95, coat: 0xc8a878, tack: 'pack', cloth: 0xa83a2a, trim: 0xe8c060 },
  shadowpanther: { body: 'lion', size: 0.95, coat: 0x1a1820, tack: 'dark', cloth: 0x1a1428, trim: 0x8a4ad8, fx: 'shadow', eyes: 0xb07aff },
  shadowcat: { body: 'lion', size: 0.9, coat: 0x5a5a62, tack: 'leather', cloth: 0x2a2a32, trim: 0x8a8a9a, fx: 'shadow' },
  dire_warg: { body: 'wolf', size: 1.0, coat: 0x2a2622, tack: 'leather', cloth: 0x4a1a1a, trim: 0xa08060, eyes: 0xffc040 },
  riding_spider: { body: 'spider', size: 0.85, coat: 0x2a2430, eyes: 0xc070ff, tack: 'leather', cloth: 0x2a1a3a, trim: 0x8a2aff, fx: 'arcane' },
  drake_whelp: { body: 'dragon', size: 0.95, coat: 0x8a2a1a, tack: 'leather', cloth: 0x2a1a12, trim: 0xd8a040, fx: 'embers', eyes: 0xffa020 },
  ancient_treant: { body: 'treant', size: 1.0, coat: 0x6a4a2a, tack: 'leather', cloth: 0x3a5a2a, trim: 0x8aa04a, fx: 'leaves' },
};
export const mountLook = key => MOUNT_LOOK[key] || MOUNT_LOOK.horse;

export function steedSpec(key) {
  const [body, words, tint, height, extra] = STEEDS[key] || DEFAULT;
  return { key, body, words, tint, height, extra, back: BACK[body] || 0.72 };
}
