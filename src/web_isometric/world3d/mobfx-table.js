// Written by tools/jev_mobfx.py: do not edit by hand (a line in mobfx-hand.js wins over one here).
// JEV judged each boss ability from its own words (its name, warning, area and creature); code drew the
// line. 134 sure; 46 left for a person (MOB_REVIEW, docs/JEV_REVIEW_MOBFX.md), drawn by
// their kind until one writes their line into mobfx-hand.js.
export const MOB_TABLE = {
  acid_gout: 'shoot | smoke | cone | hit | - | poison shake tell=rear', // the Deep Dragon: breath_cone 0.84, fits 0.57
  arcane_bolt: 'shoot | gather | orb | hit | - | arcane shake tell=gather', // Elstar: projectile 0.73, fits 0.92
  arcane_storm: 'cheer | rings | - | burst+ | - | arcane shake+ r=4.5 tell=gather', // Redferne the Wizard: nova 1.00, fits 0.94
  arcane_torrent: 'cheer | rings | - | nova | - | arcane shake+ r=4.5 tell=gather', // the Grand Mistress: nova 1.00, fits 0.89
  backhand: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // Grondar, the Hill Giant Chieftain: weapon_strike 1.00, fits 0.89
  barrow_blade: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // a barrow wight: weapon_strike 1.00, fits 0.89
  barrow_curse: 'long | glyphs | tether | mark | - | necrotic shake tell=gather', // the Barrow King: curse 0.99, fits 0.87
  berserk: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // the raider chieftain: weapon_strike 0.92, fits 0.83
  bident: 'chop2 | dust | slash | hit | - | necrotic shake tell=rear', // Hades, Lord of the Dead: weapon_strike 0.66, fits 0.84
  black_sermon: 'cheer | rings | - | nova | - | necrotic shake+ r=4.5 tell=gather', // the Hollow Bishop: nova 0.97, fits 0.73
  blizzard: 'cheer | rings | - | swirl | - | frost shake+ r=4.5 tell=gather', // the Winter Witch: nova 0.98, fits 0.91
  bog_gas: 'cheer | rings | - | cloud | - | poison shake+ r=4.5 tell=gather', // the Bog Witch: nova 0.77, fits 0.87
  bone_claw: 'stab lunge | - | slash:x | hit | - | physical shake tell=rear', // the dracolich: bite_claw 0.95, fits 0.94
  bone_club_smash: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // Grubbak the stable troll: weapon_strike 1.00, fits 0.93
  bone_dagger: 'chop2 | dust | slash | hit | - | necrotic shake tell=coil', // Morticia: weapon_strike 0.58, fits 0.87
  bone_spike: 'raise | sigil | - | growth:bones | - | necrotic shake tell=gather', // Gorbash the Bone King: eruption 1.00, fits 0.93
  bone_storm: 'cheer | rings | - | swirl | - | necrotic shake+ r=4.5 tell=gather', // the Bone-Crowned Sovereign: nova 0.84, fits 0.76
  boulder_hurl: 'shoot | gather | orb:big | hit | - | physical shake tell=rear', // Grondar, the Hill Giant Chieftain: projectile 1.00, fits 0.86
  branch_lash: 'chop2 | dust | slash | hit | - | nature shake tell=rear', // the Stick Mother: weapon_strike 0.92, fits 0.78
  breath_of_winter: 'shoot | smoke | cone | freeze | - | frost shake tell=rear', // Hrimgar the Frost Jarl: breath_cone 0.87, fits 0.90
  brimstone_burst: 'cheer | rings | - | blast+ | - | fire shake+ r=4.5 tell=gather', // the Master Summoner: nova 0.95, fits 0.85
  brine_bolt: 'shoot | gather | orb | hit | - | lightning shake tell=gather', // the Thalassine Lich: projectile 0.86, fits 0.72
  broadside: 'cheer | rings | - | blast+ | - | physical shake+ r=4.5 tell=rear', // Captain Blackhand: nova 0.62, fits 0.54
  caustic_breath: 'shoot | smoke | cone | cloud | - | poison shake+ tell=rear', // Verdraxx the Green Dragon: breath_cone 0.79, fits 0.95
  censer_blow: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // the false Canon: weapon_strike 0.99, fits 0.80
  challenge: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // the First Hero: weapon_strike 0.98, fits 0.93
  checkmate: 'cheer | rings | - | nova | - | arcane shake+ r=4.5 tell=gather', // the Black King: nova 0.87, fits 0.68
  cinder_lance: 'shoot | gather | orb | hit | - | fire shake tell=gather', // the Ember Sovereign: projectile 1.00, fits 0.93
  cleave: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // the raider chieftain: weapon_strike 1.00, fits 0.92
  cleaver_chop: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // Skarg the goblin warlord: weapon_strike 1.00, fits 0.94
  cocoon: 'long | glyphs | tether | swirl | - | poison shake tell=coil', // the Spider Queen: curse 0.92, fits 0.69
  cold_wind: 'cheer | rings | - | freeze+ | - | frost shake+ r=4.5 tell=rear', // the Lord of the House: nova 0.99, fits 0.92
  crown_smash: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // Goblin King Grizznak: weapon_strike 1.00, fits 0.88
  crozier_strike: 'chop2 | dust | slash | hit | - | necrotic shake tell=gather', // the Hollow Bishop: weapon_strike 0.99, fits 0.86
  crushing_bite: 'stab lunge | - | slash:x | hit | - | frost shake tell=rear', // the Ice Leviathan: bite_claw 1.00, fits 0.91
  crushing_coils: 'stab lunge | - | slash:x | hit | - | physical shake tell=coil', // the Deep Dragon: bite_claw 0.61, fits 0.84
  curse_of_the_pharaohs: 'cheer | rings | - | mark | - | necrotic shake+ r=4.5 tell=gather', // Ramses the Damned: nova 0.56, fits 0.78
  cutlass: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // Captain Blackhand: weapon_strike 1.00, fits 0.94
  death_knell: 'long | glyphs | tether | mark | - | necrotic shake+ tell=gather', // the Bone-Crowned Sovereign: curse 0.78, fits 0.87
  disintegration_ray: 'raise | flare | ray | shatter+ | - | arcane shake+ tell=still', // the mighty beholder: beam 1.00, fits 0.90
  diving_strike: 'leapchop leap | dust | - | hit | - | physical shake tell=rear', // the Wyvern Matriarch: charge_leap 0.73, fits 0.60
  dragonfire: 'shoot | embers | cone | blast+ | - | fire shake+ tell=rear', // Aglandiir: breath_cone 0.70, fits 0.93
  draining_touch: 'chop2 | dust | slash | hit | - | necrotic shake tell=gather', // a barrow wight: weapon_strike 0.78, fits 0.70
  drowning_curse: 'long | glyphs | tether | mark | - | necrotic shake tell=gather', // the Bog Witch: curse 0.98, fits 0.58
  eclipse: 'raise | flare | ray | implode+ | - | shadow shake+ tell=gather', // Shadow Lord Malachar: beam 0.74, fits 0.87
  eruption: 'raise | sigil | - | quake+ | - | fire shake+ r=4.5 tell=crouch', // the Cinder Tyrant: eruption 0.99, fits 0.92
  exiles_cleave: 'spin2 spin | dust | - | hit+ | - | physical shake+ r=3.5 tell=crouch', // Yarick the Outcast: sweep 0.97, fits 0.95
  finger_of_death: 'raise | flare | ray | hit | - | necrotic shake tell=gather', // Morthul the Lich Lord: beam 0.65, fits 0.57
  firestorm: 'raise | glyphs | meteors | pillar | - | fire shake tell=gather', // the Cinder Tyrant: rain 0.65, fits 0.79
  flail_of_ages: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // Ramses the Damned: weapon_strike 1.00, fits 0.90
  freezing_spray: 'shoot | smoke | cone | freeze+ | - | frost shake+ tell=rear', // the Ice Leviathan: breath_cone 0.84, fits 0.92
  fury: 'spin2 spin | dust | - | nova | - | nature shake+ r=4.5 tell=crouch', // Doctor Ilmeric Vane, the Mad Botanist: sweep 0.87, fits 0.80
  gale: 'cheer | rings | - | nova | - | physical shake+ r=4.5 tell=crouch', // Farrot the great roc: nova 0.95, fits 0.80
  gnashing_bite: 'stab lunge | - | slash:x | hit | - | poison shake tell=coil', // the Rat King: bite_claw 1.00, fits 0.82
  gore: 'stab lunge | - | slash:x | hit | - | blood shake tell=coil', // King Minos the Minotaur: bite_claw 0.88, fits 0.82
  granite_talons: 'stab lunge | - | slash:x | hit | - | physical shake tell=rear', // the Gargoyle Lord: bite_claw 0.92, fits 0.89
  grave_bloom: 'raise | sigil | - | quake+ | - | necrotic shake+ r=4.5 tell=gather', // Morticia: eruption 0.88, fits 0.89
  grave_chill: 'shoot | smoke | cone | freeze+ | - | frost shake+ tell=rear', // a barrow wight: breath_cone 0.60, fits 0.75
  grave_cleave: 'spin2 spin | dust | - | hit+ | - | physical shake+ r=4.5 tell=rear', // Gorbash the Bone King: sweep 0.97, fits 0.86
  grave_wind: 'cheer | rings | - | cloud | - | necrotic shake+ r=4.5 tell=rear', // the Barrow King: nova 0.77, fits 0.66
  gravity_collapse: 'cheer | rings | - | implode+ | - | arcane shake+ r=4.5 tell=gather', // the Eclipse Regent: nova 0.61, fits 0.86
  hellbolt: 'shoot | gather | orb | hit | - | fire shake tell=gather', // the Master Summoner: projectile 0.52, fits 0.76
  helm_of_darkness: 'cheer | rings | - | nova | - | shadow shake+ r=5 tell=gather', // Hades, Lord of the Dead: nova 0.96, fits 0.54
  heros_cleave: 'spin2 spin | dust | - | hit+ | - | physical shake+ r=4 tell=rear', // the First Hero: sweep 0.88, fits 0.94
  hex: 'long | glyphs | tether | mark | - | necrotic shake tell=gather', // the Bog Witch: curse 0.89, fits 0.85
  horde_roar: 'cheer | rings | - | nova | - | sound shake+ r=4.5 tell=rear', // Grukthar the Goblin King: nova 1.00, fits 0.82
  ice_axe: 'chop2 | dust | slash | hit | - | frost shake tell=rear', // Hrimgar the Frost Jarl: weapon_strike 1.00, fits 0.96
  ice_lance: 'shoot | gather | shards:3 | hit | - | frost shake tell=gather', // the Winter Witch: projectile 0.99, fits 0.95
  inferno: 'shoot | embers | cone | blast | - | fire shake tell=rear', // Aglandiir: breath_cone 0.77, fits 0.66
  iron_sword: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // the Barrow King: weapon_strike 1.00, fits 0.94
  judgement: 'chop2 | dust | slash | hit | - | holy shake tell=rear', // King Welmar: weapon_strike 0.98, fits 0.90
  judgement_of_the_dead: 'long | glyphs | tether | mark | - | necrotic shake tell=gather', // Hades, Lord of the Dead: curse 0.88, fits 0.72
  kingsblade: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // King Welmar: weapon_strike 0.99, fits 0.91
  labyrinth_roar: 'cheer | rings | - | hit | - | sound shake tell=rear', // King Minos the Minotaur: nova 0.69, fits 0.70
  last_stand: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // the First Hero: weapon_strike 0.93, fits 0.84
  lightning_breath: 'shoot | smoke | cone | blast+ | - | lightning shake+ tell=rear', // Aurexus the Bronze Dragon: breath_cone 0.56, fits 0.95
  lightning_lance: 'raise | flare | skyray | hit | - | lightning shake tell=gather', // Redferne the Wizard: beam 0.51, fits 0.77
  lloths_wrath: 'cheer | rings | - | nova | - | arcane shake+ r=4.5 tell=gather', // the High Priestess of Lloth: nova 0.95, fits 0.82
  marrow_blade: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // the Bone-Crowned Sovereign: weapon_strike 1.00, fits 0.71
  molten_blade: 'chop2 | dust | slash | hit | - | fire shake tell=rear', // the Cinder Tyrant: weapon_strike 1.00, fits 0.94
  necrotic_breath: 'cheer | rings | - | cloud | - | necrotic shake+ r=4.5 tell=rear', // the dracolich: nova 0.53, fits 0.81
  pack_fury: 'stab lunge | - | slash:x | hit | - | physical shake tell=coil', // the alpha wolf: bite_claw 0.65, fits 0.79
  piston_fist: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // Archon Prime: weapon_strike 1.00, fits 0.93
  plague_squall: 'cheer | rings | - | cloud | - | poison shake+ r=4.5 tell=rear', // the Rat King: nova 0.99, fits 0.88
  pommel_crack: 'chop2 | dust | slash | crack | - | physical shake tell=coil', // Yarick the Outcast: weapon_strike 0.90, fits 0.58
  possession: 'long | glyphs | tether | swirl | - | necrotic shake tell=shudder', // the Lord of the House: curse 0.78, fits 0.61
  powder_keg: 'shoot | gather | orb | blast | - | fire shake tell=gather', // Captain Blackhand: projectile 0.62, fits 0.75
  pyre_surge: 'cheer | rings | - | blast+ | - | fire shake+ r=4.5 tell=gather', // the Ember Sovereign: nova 0.96, fits 0.96
  rending_claw: 'stab lunge | - | slash:x | hit | - | physical shake tell=rear', // Aglandiir: bite_claw 0.95, fits 0.90
  rending_claws: 'stab lunge | - | slash:x | hit | - | physical shake tell=rear', // Verdraxx the Green Dragon: bite_claw 0.97, fits 0.83
  rite_of_terror: 'long | glyphs | tether | hit | - | shadow shake tell=gather', // the High Priest of Terror: curse 0.59, fits 0.89
  royal_decree: 'cheer | rings | - | nova | - | holy shake+ r=4.5 tell=rear', // King Welmar: nova 0.85, fits 0.73
  royal_rebuke: 'chop2 | dust | slash | hit | - | physical shake tell=gather', // the Black King: weapon_strike 1.00, fits 0.90
  royal_tantrum: 'cheer | rings | - | quake+ | - | sound shake+ r=4.5 tell=crouch', // Goblin King Grizznak: nova 0.96, fits 0.81
  sacrificial_knife: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // the Black Priest: weapon_strike 0.98, fits 0.88
  savage_howl: 'cheer | rings | - | nova | - | sound shake+ r=4.5 tell=rear', // the alpha wolf: nova 1.00, fits 0.85
  scimitar_of_fire: 'chop2 | dust | slash | hit | - | fire shake tell=rear', // the Great Ifrit: weapon_strike 1.00, fits 0.92
  serpent_whip: 'chop2 | dust | slash | hit | - | physical shake tell=coil', // the High Priestess of Lloth: weapon_strike 0.97, fits 0.74
  shadow_nova: 'cheer | rings | - | nova | - | shadow shake+ r=4.5 tell=gather', // Shadow Lord Malachar: nova 1.00, fits 0.87
  skullsplitter: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // Grukthar the Goblin King: weapon_strike 1.00, fits 0.74
  smokeless_flame: 'cheer | rings | - | blast+ | - | fire shake+ r=4.5 tell=rear', // the Great Ifrit: nova 0.75, fits 0.90
  snatch: 'stab lunge | - | slash:x | hit | - | physical shake tell=rear', // Farrot the great roc: bite_claw 0.77, fits 0.72
  soul_storm: 'cheer | rings | - | swirl | - | necrotic shake+ r=4.5 tell=gather', // Morthul the Lich Lord: nova 0.99, fits 0.80
  spellblade: 'chop2 | dust | slash | hit | - | arcane shake tell=gather', // the Grand Mistress: weapon_strike 0.69, fits 0.87
  splinter_storm: 'cheer | rings | - | shatter+ | - | nature shake+ r=4.5 tell=shudder', // the Stick Mother: nova 0.97, fits 0.95
  stampede: 'leapchop leap | dust | - | quake+ | - | physical shake+ heavy r=4.5 tell=coil', // King Minos the Minotaur: charge_leap 0.66, fits 0.91
  starfall: 'raise | glyphs | rain | hit | - | arcane shake tell=gather', // the Eclipse Regent: rain 0.74, fits 0.76
  stone_fist: 'chop2 | dust | slash | hit | - | physical shake tell=rear', // the mazekeeper: weapon_strike 1.00, fits 0.82
  summon_the_dark: 'raise | flare | ray | pillar | - | shadow shake tell=gather', // the Black Priest: beam 0.60, fits 0.90
  sundering_blade: 'chop2 | dust | slash | shatter | - | arcane shake tell=rear', // the Shattered Emperor: weapon_strike 1.00, fits 0.91
  talon_rake: 'stab lunge | - | slash:x | hit | - | physical shake tell=rear', // Farrot the great roc: bite_claw 0.75, fits 0.86
  tentacle_sweep: 'spin2 spin | dust | - | hit+ | - | physical shake+ r=4.5 tell=crouch', // the Kraken: sweep 0.99, fits 0.86
  the_eye_opens: 'raise | flare | ray | hit | - | arcane shake tell=gather', // the false Canon: beam 0.92, fits 0.82
  thorn_lash: 'chop2 | dust | slash | hit | - | nature shake tell=rear', // 27016: weapon_strike 0.92, fits 0.57
  throat_bite: 'stab lunge | - | slash:x | hit | - | physical shake tell=crouch', // the alpha wolf: bite_claw 0.97, fits 0.73
  transmute: 'long | glyphs | tether | swirl | - | arcane shake tell=gather', // Elstar: curse 0.75, fits 0.64
  trident_of_the_deep: 'chop2 | dust | slash | hit | - | physical shake tell=gather', // Nerathis, the Drowned King: weapon_strike 0.54, fits 0.71
  twisted_blade: 'chop2 | dust | slash | hit | - | arcane shake tell=rear', // the Lord of Chaos: weapon_strike 0.99, fits 0.60
  umbral_blade: 'chop2 | dust | slash | hit | - | shadow shake tell=gather', // Shadow Lord Malachar: weapon_strike 0.98, fits 0.79
  unholy_sermon: 'cheer | rings | - | nova | - | necrotic shake+ r=4.5 tell=gather', // the false Canon: nova 0.96, fits 0.72
  unholy_word: 'cheer | rings | - | nova | - | necrotic shake+ r=4.5 tell=gather', // the Abbot\'s Ghost: nova 0.78, fits 0.80
  unmaking_wave: 'cheer | rings | - | shatter+ | - | arcane shake+ r=4.5 tell=gather', // the Lord of Chaos: nova 0.98, fits 0.93
  venom_fang: 'stab lunge | - | slash:x | hit | - | poison shake tell=coil', // the Spider Queen: bite_claw 0.71, fits 0.93
  venom_sting: 'stab lunge | - | slash:x | hit | - | poison shake tell=crouch', // the Wyvern Matriarch: bite_claw 0.99, fits 0.81
  waking_nightmare: 'long | glyphs | tether | hit | - | shadow shake tell=still', // Rand the Dreamer: curse 0.67, fits 0.73
  war_screech: 'cheer | rings | - | nova | - | sound shake+ r=4.5 tell=rear', // Skarg the goblin warlord: nova 1.00, fits 0.85
  warcry: 'cheer | rings | - | nova | - | sound shake+ r=4.5 tell=rear', // the raider chieftain: nova 1.00, fits 0.85
  warlords_fury: 'chop2 | dust | slash | hit | - | physical shake tell=coil', // Grukthar the Goblin King: weapon_strike 0.75, fits 0.89
  wave_of_dread: 'cheer | rings | - | nova | - | shadow shake+ r=4.5 tell=gather', // the High Priest of Terror: nova 0.99, fits 0.75
  web_trap: 'shoot | gather | orb:big | swirl | - | physical shake tell=gather', // Zyraxxis the Spider Queen: projectile 0.60, fits 0.55
  wing_buffet: 'spin2 spin | dust | - | hit+ | - | physical shake+ r=4.5 tell=rear', // the Wyvern Matriarch: sweep 0.51, fits 0.74
  wither: 'long | glyphs | tether | mark | - | necrotic shake tell=gather', // 27016: curse 0.83, fits 0.74
  word_of_unmaking: 'long | glyphs | tether | shatter | - | arcane shake tell=gather', // the Grand Mistress: curse 0.86, fits 0.89
  world_breaker: 'chop2 slam | dust | slash | shatter+ | - | arcane shake+ heavy tell=gather', // the Shattered Emperor: weapon_strike 0.52, fits 0.79
};
// boss abilities JEV wasn't sure of (drawn by their kind)
export const MOB_REVIEW = [
  'abyssal_word',
  'avalanche',
  'blight_wave',
  'bribe_the_mob',
  'bring_it_down',
  'call_of_the_swarm',
  'castling',
  'crushing_grip',
  'crushing_tide',
  'dark_litany',
  'deep_freeze',
  'den_collapse',
  'doom',
  'dream_lash',
  'drowning_grasp',
  'drowning_tide',
  'eternal_sleep',
  'grave_grip',
  'immolation',
  'last_rites',
  'lose_your_way',
  'maelstrom',
  'mind_spike',
  'mutagen_burst',
  'night_terror',
  'open_the_gate',
  'overload',
  'petrifying_gaze',
  'poison_spit',
  'power_word_kill',
  'raise_the_guild',
  'rewrite',
  'rift_cascade',
  'shadow_lash',
  'shape_of_terror',
  'shifting_walls',
  'soul_drain',
  'steam_vent',
  'stone_dive',
  'tail_sweep',
  'thunderclap',
  'total_eclipse',
  'undertow',
  'unmaking',
  'web_spray',
  'whispered_doubt',
];
