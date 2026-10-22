# JEV review: boss ability looks

tools/jev_mobfx.py asked JEV how each boss ability reaches its foe, its school, what happens where it
lands, the body's tell and how big it is, and drew a line from the answers. These are the ones it
was not sure of (delivery below 0.5, impact below 0.3, or the check below 0.5 that
the look fits the warning). Until a line is written for one in `world3d/mobfx-hand.js`, /play draws it
by its kind. JEV's pick and its runners-up are given to start from.

134 drawn from JEV, 46 here.

## Abyssal Word (`abyssal_word`)
*the Thalassine Lich*: "The Thalassine Lich begins a word from the abyss!"
- unsure: impact 0.26
- JEV: curse (0.92; then projectile 0.03, beam 0.03), necrotic, lands hit (0.26; then burst 0.22, implode 0.13), tell gather, size 1
- its line would be: `long | glyphs | tether | hit | - | necrotic shake tell=gather`

## Avalanche (`avalanche`)
*Hrimgar the Frost Jarl*: "Hrimgar slams his axe into the mountainside!"
- unsure: delivery 0.31
- JEV: nova (0.31; then rain 0.29, sweep 0.15), frost, lands quake (0.83; then crack 0.11, shatter 0.03), tell rear, size 2
- its line would be: `cheer | rings | - | quake+ | - | frost shake+ r=4.5 tell=rear`

## Blight Wave (`blight_wave`)
*27016*: "The Blightlord spreads his arms, and rot spreads across the ground!"
- unsure: check 0.42
- JEV: nova (0.75; then eruption 0.18, sweep 0.05), necrotic, lands nova (0.50; then cloud 0.34, growth 0.04), tell gather, size 2
- its line would be: `cheer | rings | - | nova | - | necrotic shake+ r=4.5 tell=gather`

## Bribe the Mob (`bribe_the_mob`)
*Goblin King Grizznak*: "Grizznak tosses a fistful of gold into the air!"
- unsure: check 0.2
- JEV: projectile (0.52; then rain 0.33, weapon_strike 0.03), physical, lands hit (0.58; then swirl 0.09, burst 0.08), tell gather, size 1
- its line would be: `shoot | gather | orb:big | hit | - | physical shake tell=gather`

## Bring It Down (`bring_it_down`)
*Skarg the goblin warlord*: "Skarg hammers at a pillar to bring down the roof!"
- unsure: impact 0.27
- JEV: rain (0.88; then weapon_strike 0.07, eruption 0.03), physical, lands shatter (0.27; then crack 0.28, quake 0.18), tell rear, size 2
- its line would be: `raise | glyphs | rain | shatter+ | - | physical shake+ tell=rear`

## Call of the Swarm (`call_of_the_swarm`)
*the Rat King*: "The Rat King drums his tail on the floor in a rising frenzy!"
- unsure: check 0.46
- JEV: summon (0.64; then bite_claw 0.09, projectile 0.08), poison, lands hit (0.41; then growth 0.17, quake 0.11), tell shudder, size 1
- its line would be: `summon | sigil | - | pillar | - | poison shake tell=shudder`

## Castling (`castling`)
*the Black King* and 1 more: "The Black King calls for his rook!"
- unsure: delivery 0.24, check 0.25
- JEV: weapon_strike (0.24; then summon 0.27, charge_leap 0.23), physical, lands hit (0.78; then growth 0.05, burst 0.04), tell rear, size 1
- its line would be: `chop2 | dust | slash | hit | - | physical shake tell=rear`

## Crushing Grip (`crushing_grip`)
*the Kraken*: "A great tentacle coils toward you!"
- unsure: check 0.25
- JEV: weapon_strike (0.51; then bite_claw 0.38, eruption 0.03), physical, lands hit (0.59; then swirl 0.17, mark 0.10), tell coil, size 1
- its line would be: `chop2 | dust | slash | hit | - | physical shake tell=coil`

## Crushing Tide (`crushing_tide`)
*Nerathis, the Drowned King*: "Nerathis raises his arms, and the water above you darkens!"
- unsure: check 0.33
- JEV: rain (0.59; then nova 0.32, eruption 0.05), physical, lands pillar (0.38; then nova 0.20, quake 0.12), tell gather, size 2
- its line would be: `raise | glyphs | rain | pillar+ | - | physical shake+ r=4.5 tell=gather`

## Dark Litany (`dark_litany`)
*the Black Priest*: "The Black Priest chants, and the shadows deepen around you!"
- unsure: impact 0.20
- JEV: nova (0.92; then curse 0.05, sweep 0.02), shadow, lands nova (0.20; then swirl 0.15, burst 0.14), tell gather, size 2
- its line would be: `cheer | rings | - | nova | - | shadow shake+ r=4.5 tell=gather`

## Deep Freeze (`deep_freeze`)
*the Winter Witch*: "The Winter Witch begins to freeze your blood!"
- unsure: delivery 0.34
- JEV: beam (0.34; then curse 0.37, projectile 0.14), frost, lands freeze (1.00; then hit 0.00, blast 0.00), tell gather, size 1
- its line would be: `raise | flare | ray | freeze | - | frost shake tell=gather`

## Den Collapse (`den_collapse`)
*Grubbak the stable troll*: "Grubbak slams its shoulder into the den roof!"
- unsure: delivery 0.39
- JEV: rain (0.39; then nova 0.38, sweep 0.09), physical, lands crack (0.37; then quake 0.29, implode 0.15), tell coil, size 2
- its line would be: `raise | glyphs | rain | crack+ | - | physical shake+ r=4 tell=coil`

## Doom (`doom`)
*Doctor Ilmeric Vane, the Mad Botanist* and 43 more: "Doctor Ilmeric Vane, the Mad Botanist begins something terrible!"
- unsure: impact 0.29
- JEV: curse (0.64; then projectile 0.10, beam 0.09), nature, lands hit (0.29; then growth 0.25, mark 0.24), tell gather, size 1
- its line would be: `long | glyphs | tether | hit | - | nature shake tell=gather`

## Dream Lash (`dream_lash`)
*Rand the Dreamer*: "Rand flings out a hand, and the shadows lash at you!"
- unsure: delivery 0.38
- JEV: projectile (0.38; then beam 0.21, weapon_strike 0.13), shadow, lands hit (0.71; then swirl 0.10, growth 0.09), tell gather, size 1
- its line would be: `shoot | gather | orb | hit | - | shadow shake tell=gather`

## Drowning Grasp (`drowning_grasp`)
*Nerathis, the Drowned King*: "Water coils around your throat!"
- unsure: delivery 0.47, check 0.36
- JEV: eruption (0.47; then projectile 0.20, curse 0.16), necrotic, lands swirl (0.93; then growth 0.03, mark 0.02), tell coil, size 1
- its line would be: `raise | sigil | - | swirl | - | necrotic shake tell=coil`

## Drowning Tide (`drowning_tide`)
*the Thalassine Lich*: "The Thalassine Lich lifts its staff, and the sea rushes in!"
- unsure: check 0.48
- JEV: nova (0.82; then eruption 0.12, rain 0.02), necrotic, lands nova (0.33; then geyser 0.27, pillar 0.12), tell gather, size 2
- its line would be: `cheer | rings | - | nova | - | necrotic shake+ r=4.5 tell=gather`

## Eternal Sleep (`eternal_sleep`)
*Ramses the Damned*: "Ramses begins the rite of eternal sleep!"
- unsure: impact 0.26
- JEV: curse (0.82; then beam 0.09, weapon_strike 0.05), necrotic, lands hit (0.26; then freeze 0.27, mark 0.26), tell still, size 1
- its line would be: `long | glyphs | tether | hit | - | necrotic shake tell=still`

## Grave Grip (`grave_grip`)
*the Lord of the House*: "The Lord of the House reaches for your throat!"
- unsure: delivery 0.39, check 0.43
- JEV: weapon_strike (0.39; then bite_claw 0.43, eruption 0.07), necrotic, lands hit (0.50; then swirl 0.19, growth 0.10), tell coil, size 1
- its line would be: `chop2 | dust | slash | hit | - | necrotic shake tell=coil`

## Immolation (`immolation`)
*the Ember Sovereign*: "The Ember Sovereign begins to burn from within!"
- unsure: delivery 0.21
- JEV: beam (0.21; then projectile 0.24, curse 0.16), fire, lands blast (0.50; then burst 0.23, hit 0.10), tell shudder, size 1
- its line would be: `raise | flare | ray | blast | - | fire shake tell=shudder`

## Last Rites (`last_rites`)
*the Abbot's Ghost* and 1 more: "The Abbot's Ghost begins the last rites!"
- unsure: delivery 0.39, impact 0.27
- JEV: curse (0.39; then beam 0.30, projectile 0.13), necrotic, lands hit (0.27; then mark 0.23, burst 0.22), tell gather, size 1
- its line would be: `long | glyphs | tether | hit | - | necrotic shake tell=gather`

## Lose Your Way (`lose_your_way`)
*the mazekeeper*: "The Mazekeeper begins to twist the paths around you!"
- unsure: check 0.44
- JEV: curse (0.77; then eruption 0.10, weapon_strike 0.04), arcane, lands swirl (0.65; then mark 0.14, growth 0.06), tell gather, size 1
- its line would be: `long | glyphs | tether | swirl | - | arcane shake tell=gather`

## Maelstrom (`maelstrom`)
*the Kraken*: "The Kraken churns the water into a maelstrom!"
- unsure: delivery 0.40, check 0.18
- JEV: eruption (0.40; then nova 0.30, sweep 0.07), physical, lands swirl (0.74; then implode 0.14, pillar 0.04), tell coil, size 1
- its line would be: `raise | sigil | - | swirl | - | physical shake tell=coil`

## Mind Spike (`mind_spike`)
*the mighty beholder*: "Psychic energy ripples from the beholder!"
- unsure: check 0.46
- JEV: nova (0.99; then beam 0.01, weapon_strike 0.00), shadow, lands nova (0.51; then burst 0.18, hit 0.15), tell gather, size 2
- its line would be: `cheer | rings | - | nova | - | shadow shake+ tell=gather`

## Mutagen Burst (`mutagen_burst`)
*Elstar*: "Elstar hurls a flask of bubbling green liquid!"
- unsure: check 0.45
- JEV: projectile (0.62; then nova 0.34, breath_cone 0.01), poison, lands blast (0.30; then burst 0.26, cloud 0.17), tell gather, size 2
- its line would be: `shoot | gather | orb:big | blast+ | - | poison shake+ tell=gather`

## Night Terror (`night_terror`)
*Rand the Dreamer*: "Rand screams in his sleep, and the room twists!"
- unsure: impact 0.23
- JEV: nova (1.00; then weapon_strike 0.00, bite_claw 0.00), shadow, lands nova (0.23; then quake 0.26, burst 0.12), tell shudder, size 2
- its line would be: `cheer | rings | - | nova | - | shadow shake+ r=4.5 tell=shudder`

## Open the Gate (`open_the_gate`)
*the Master Summoner*: "The Master Summoner begins the great invocation!"
- unsure: delivery 0.26, impact 0.17
- JEV: summon (0.26; then beam 0.28, projectile 0.17), arcane, lands pillar (0.17; then burst 0.18, growth 0.17), tell gather, size 1
- its line would be: `summon | sigil | - | pillar | - | arcane shake tell=gather`

## Overload (`overload`)
*Archon Prime*: "Archon Prime's core glows white-hot!"
- unsure: delivery 0.47
- JEV: beam (0.47; then projectile 0.21, weapon_strike 0.19), fire, lands blast (0.69; then hit 0.19, burst 0.06), tell gather, size 2
- its line would be: `raise | flare | ray | blast+ | - | fire shake+ tell=gather`

## Petrifying Gaze (`petrifying_gaze`)
*the Gargoyle Lord*: "The Gargoyle Lord's eyes begin to glow a dull grey!"
- unsure: check 0.36
- JEV: beam (0.98; then curse 0.02, weapon_strike 0.00), arcane, lands freeze (0.54; then mark 0.18, hit 0.09), tell still, size 2
- its line would be: `raise | flare | ray | freeze+ | - | arcane shake+ tell=still`

## Poison Spit (`poison_spit`)
*Zyraxxis the Spider Queen*: "The Spider Queen gurgles, venom pooling in her maw!"
- unsure: delivery 0.35
- JEV: breath_cone (0.35; then breath_cone 0.40, nova 0.20), poison, lands cloud (0.80; then nova 0.07, hit 0.06), tell rear, size 2
- its line would be: `shoot | smoke | cone | cloud | - | poison shake+ tell=rear`

## Power Word: Kill (`power_word_kill`)
*Morthul the Lich Lord*: "Morthul begins to speak a word of ending!"
- unsure: impact 0.25
- JEV: curse (0.98; then beam 0.02, weapon_strike 0.00), necrotic, lands shatter (0.25; then implode 0.26, hit 0.23), tell gather, size 2
- its line would be: `long | glyphs | tether | shatter+ | - | necrotic shake+ tell=gather`

## Raise the Guild (`raise_the_guild`)
*Morticia*: "Morticia begins a chant to raise the dead!"
- unsure: delivery 0.45
- JEV: summon (0.45; then eruption 0.18, curse 0.16), necrotic, lands growth (0.90; then hit 0.05, burst 0.01), tell gather, size 1
- its line would be: `summon | sigil | - | growth:bones | - | necrotic shake tell=gather`

## Rewrite (`rewrite`)
*the Lord of Chaos*: "The Lord of Chaos begins to rewrite the world around you!"
- unsure: delivery 0.45, impact 0.23
- JEV: curse (0.45; then beam 0.29, eruption 0.08), arcane, lands swirl (0.23; then burst 0.26, mark 0.11), tell gather, size 2
- its line would be: `long | glyphs | tether | swirl | - | arcane shake+ tell=gather`

## Rift Cascade (`rift_cascade`)
*the Shattered Emperor*: "The Shattered Emperor splits the air, and the rift pours out!"
- unsure: impact 0.29
- JEV: nova (0.88; then eruption 0.05, rain 0.04), arcane, lands shatter (0.29; then nova 0.31, blast 0.11), tell gather, size 2
- its line would be: `cheer | rings | - | shatter+ | - | arcane shake+ r=4.5 tell=gather`

## Shadow Lash (`shadow_lash`)
*the High Priest of Terror*: "The High Priest of Terror cracks a whip of living shadow!"
- unsure: check 0.48
- JEV: weapon_strike (0.92; then projectile 0.03, beam 0.02), shadow, lands hit (0.91; then crack 0.04, growth 0.01), tell rear, size 1
- its line would be: `chop2 | dust | slash | hit | - | shadow shake tell=rear`

## Shape of Terror (`shape_of_terror`)
*the Deep Dragon*: "The Deep Dragon swells to its full size and rears over you!"
- unsure: impact 0.21
- JEV: nova (0.73; then sweep 0.15, curse 0.07), shadow, lands hit (0.21; then nova 0.24, quake 0.19), tell rear, size 2
- its line would be: `cheer | rings | - | hit+ | - | shadow shake+ r=4.5 tell=rear`

## Shifting Walls (`shifting_walls`)
*the mazekeeper*: "The Mazekeeper spreads his hands, and the walls lurch!"
- unsure: check 0.4
- JEV: nova (0.71; then sweep 0.16, eruption 0.11), physical, lands quake (0.59; then growth 0.18, nova 0.13), tell gather, size 2
- its line would be: `cheer | rings | - | quake+ | - | physical shake+ r=4.5 tell=gather`

## Soul Drain (`soul_drain`)
*the Abbot's Ghost* and 1 more: "The Abbot's Ghost reaches for your soul!"
- unsure: delivery 0.41
- JEV: curse (0.41; then weapon_strike 0.20, bite_claw 0.15), necrotic, lands hit (0.47; then mark 0.16, swirl 0.14), tell gather, size 1
- its line would be: `long | glyphs | tether | hit | - | necrotic shake tell=gather`

## Steam Vent (`steam_vent`)
*Archon Prime*: "Archon Prime opens its vents with a deafening hiss!"
- unsure: check 0.44
- JEV: nova (0.97; then breath_cone 0.03, weapon_strike 0.00), fire, lands cloud (0.36; then blast 0.31, nova 0.15), tell shudder, size 2
- its line would be: `cheer | rings | - | cloud | - | fire shake+ r=4.5 tell=shudder`

## Stone Dive (`stone_dive`)
*the Gargoyle Lord*: "The Gargoyle Lord leaps into the air and folds its wings to dive!"
- unsure: impact 0.27
- JEV: charge_leap (0.92; then nova 0.03, sweep 0.02), physical, lands crack (0.27; then hit 0.29, quake 0.28), tell crouch, size 2
- its line would be: `leapchop leap | dust | - | crack+ | - | physical shake+ heavy r=4.5 tell=crouch`

## Tail Sweep (`tail_sweep`)
*Verdraxx the Green Dragon*: "Verdraxx coils her great tail to sweep the lair!"
- unsure: check 0.46
- JEV: sweep (0.79; then bite_claw 0.17, weapon_strike 0.02), physical, lands hit (0.83; then quake 0.07, crack 0.04), tell coil, size 1
- its line would be: `spin2 spin | dust | - | hit | - | physical shake tell=coil`

## Thunderclap (`thunderclap`)
*Aurexus the Bronze Dragon*: "Aurexus slams the ground in a thunderous clap!"
- unsure: delivery 0.23, impact 0.23
- JEV: eruption (0.23; then nova 0.24, beam 0.15), lightning, lands quake (0.23; then hit 0.23, blast 0.21), tell crouch, size 1
- its line would be: `raise | sigil | - | quake | - | lightning shake tell=crouch`

## Total Eclipse (`total_eclipse`)
*the Eclipse Regent*: "The Eclipse Regent begins to blot out every star!"
- unsure: impact 0.29
- JEV: beam (0.79; then curse 0.05, projectile 0.04), arcane, lands implode (0.29; then hit 0.29, pillar 0.28), tell gather, size 2
- its line would be: `raise | flare | ray | implode+ | - | arcane shake+ tell=gather`

## Undertow (`undertow`)
*the Ice Leviathan*: "The Ice Leviathan dives, dragging the water after it!"
- unsure: delivery 0.30
- JEV: charge_leap (0.30; then bite_claw 0.33, eruption 0.23), frost, lands implode (0.55; then pillar 0.11, swirl 0.10), tell coil, size 1
- its line would be: `leapchop leap | dust | - | implode | - | frost shake tell=coil`

## Unmaking (`unmaking`)
*Redferne the Wizard*: "Redferne begins to weave a spell of unmaking!"
- unsure: delivery 0.36
- JEV: beam (0.36; then curse 0.41, projectile 0.18), arcane, lands shatter (0.65; then implode 0.15, burst 0.09), tell gather, size 1
- its line would be: `raise | flare | ray | shatter | - | arcane shake tell=gather`

## Web Spray (`web_spray`)
*the Spider Queen* and 1 more: "The Spider Queen rears and sprays sticky webbing everywhere!"
- unsure: impact 0.26, check 0.35
- JEV: breath_cone (0.75; then nova 0.21, sweep 0.01), poison, lands mark (0.26; then swirl 0.27, cloud 0.23), tell rear, size 2
- its line would be: `shoot | smoke | cone | mark | - | poison shake+ tell=rear`

## Whispered Doubt (`whispered_doubt`)
*the Great Ifrit*: "The Great Ifrit begins to whisper, and your resolve wavers!"
- unsure: check 0.48
- JEV: curse (1.00; then weapon_strike 0.00, bite_claw 0.00), shadow, lands mark (0.37; then hit 0.40, swirl 0.14), tell gather, size 1
- its line would be: `long | glyphs | tether | mark | - | shadow shake tell=gather`
