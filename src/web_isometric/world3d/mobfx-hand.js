// How a creature's own abilities look, by hand (the owner: "mobs react similarly with their
// spells and abilities"). Keyed by the ability's `fx` (combat_hooks.fx_key: its name in
// lower_snake), in abilityfx.js's six columns; tell=<TELLS> is what its body does while it winds
// up. A line here wins over the ones tools/jev_mobfx.py writes (mobfx-table.js). The colours are
// the school's and the marks the creature's family's (abilityfx.js FAMILIES), so one line serves
// a goblin shaman and a lich alike; its rank cuts it down (forRank).
//
//   node --test tests/web/mobfx.test.mjs   checks every line, and that every everyday ability
//                                           (tests/web/fixtures/mobfx.json) has one
export const MOB_RECIPES = {
  // a caster's harm spells (brain/cast.py SPELLBOOK, mob_ai.CASTER_OFFENSIVE)
  magic_missile: 'shoot | glyphs | orbs:3 | sparks | - | arcane tell=gather',
  chill_touch: 'stab lunge | spiral | - | freeze | - | frost tell=gather',
  burning_hands: 'long | embers | cone | burst | - | fire tell=gather',
  shadow_bolt: 'shoot | smoke | orb | burst:eye | - | shadow tell=gather',
  ice_storm: 'raise | rings | rain | freeze+ | - | frost tell=gather',
  lightning_bolt: 'raise | flare | skyray | hit+ | - | lightning shake tell=still',
  fireball: 'shoot | gather | orb:big | blast+ | - | fire shake tell=gather',
  // its hexes: a tether, a mark, a flash, roots
  weaken: 'long | glyphs | tether | mark | - | shadow tell=gather',
  curse: 'shoot | smoke | glyph:skull | burst:skull | - | necrotic tell=gather',
  blindness: 'raise | flare | - | burst:eye | - | holy flash tell=still',
  slow: 'long | spiral | link | swirl | - | arcane tell=gather',
  entangle: 'throw | dust | - | growth:vines | - | nature tell=crouch',
  // a healer's prayer, a caster's quick mending and its ward, a word of silence for your healer
  healing_prayer: 'raise | sigil | - | heal | - | holy ally tell=gather',
  healing_incantation: 'long | motifs | - | fountain | - | nature ally',
  ward: 'raise | rings | - | - | bubble | arcane ally',
  disrupt: 'taunt | rings | ray | rings | - | sound tell=still',
  // a creature's own specials (mob_ai._choose_legacy_intent): a dragon's breath, a spider's or
  // a snake's fangs, a ghoul's numbing touch
  fire_breath: 'shoot | embers | cone+ | blast | - | fire shake tell=rear',
  venomous_strike: 'stab lunge | - | slash | cloud | - | poison tell=coil',
  paralyzing_touch: 'stab | charge | link | mark | - | lightning tell=still',
  // a bruiser's big blows (brace or step out) and a pack's lunge as one
  crushing_blow: 'chop2 slam | dust | - | crack+ | - | physical shake+ stop tell=rear',
  sweeping_blow: 'spin2 spin | dust | - | quake | - | physical shake+ wide tell=crouch',
  coordinated_lunge: 'leapchop lunge | dust | slash:3 | hit+ | - | blood tell=crouch',
  // a boss wrapping itself in a ward no spell gets through (bosses.py magic_immune_duration)
  nullifying_aura: 'raise | sigil+ | - | - | bubble+ | arcane ally tell=still',
  // a creature that counts as a boss without a script of its own (mob_ai.BOSS_ABILITIES)
  ground_slam: 'chop2 slam | dust | - | quake+ | - | physical shake+ stop tell=coil',
  terrifying_roar: 'taunt | rings | - | nova | - | shadow shake tell=rear',
  summon_minions: 'summon | sigil | - | pillar | - | necrotic tell=gather',
};
