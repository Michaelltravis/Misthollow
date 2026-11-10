# Ostragoth and the Starbringer

The Castle of Ostragoth (zone 470) ends in two fights. Ostragoth, the vampire lord, is the castle's own
boss (level 21) and is fought in his bedchamber. His star-key opens the House of Death below the castle,
where the Starbringer is chained. The Starbringer is a level-60 raid, built for a group at the level cap.

Data: `world/population/zone_470.json` (`lairs`, `bosses`, `creatures`, `items`) and
`world/zones/zone_470.json` (the rooms, the two doors, Ostragoth's words). Code: `src/lairs.py`.
Test: `tests/test_lairs.py`.

## Ostragoth, the vampire lord: the King's Chamber (8403)

**He comes when you walk in.** Ostragoth is not standing in the room. When a player walks into the King's
Chamber, these steps follow (`lairs.on_enter`):

1. The black iron door south slams shut and bolts. It bolts on both sides, can't be picked and is sealed
   by magic, so no key, pick, bash or spell opens it. The antechamber hears it slam.
2. A great black bat bursts in through the curtains and circles the bed.
3. The bat drops and becomes Ostragoth, who attacks whoever walked in.

Followers walk in with their leader. An immortal walking in wakes nothing.

**The only ways out are a recall, a summons, or his death.** While the room is sealed:

| Way out | Sealed lair |
|---|---|
| Walking, fleeing, escaping | No: the door is bolted (and trying it costs no parting blows) |
| Opening, unlocking, picking, bashing the door | No |
| Portals (`enter`), fast travel, `home`, the Teleport spell, Shadow Step | No |
| `recall` or Word of Recall | **Yes, even mid-fight** |
| Being summoned by someone outside | **Yes, even mid-fight** |
| Dying | Yes |
| Being summoned *in*, teleporting or shadow-stepping *in* | No |

If no living player is left inside, Ostragoth turns into a cloud of bats and flies out through the
curtains, and the door opens. He comes back at full health for the next player who walks in. When he
dies, the door opens and he drops his star-key every time. After that the chamber stays empty until the
castle resets.

**The fight.** He is sized like every zone boss (`bosses.size_zone_boss`), with 3,743 health and his
blows weighted at 0.15. In the balance sim that costs a lone level-21 hero a median of about half their
health, over 2.3 to 4.9 minutes. The sim never interrupts his Blood Drain, so a player who breaks it ends
the fight sooner.

| When | What | How to answer it |
|---|---|---|
| Always | **Crimson Lash**: a talon strike on his target (1.2 s wind-up) | Dodge |
| Always | **Night's Embrace**: shadows rush in around him (2.5 s, 4.5 m) | Get clear of him |
| Always | **Blood Drain**: he bites, healing 6% of his health (3 s) | Interrupt it (bash or kick) |
| Always | **Blood Pools**: a pool of blood under a fighter every 10 s | Step out |
| As he weakens | The candles go out one by one (gloom) | |
| 60% | He bursts into bats and three vampire bats come in | Kill the adds |
| 60% onward | **Grave Hex**: his old sorcery (2.5 s) | Interrupt it |
| 30% | Three more bats come, and his **Thirst** starts: anyone standing still is drained | Keep moving |
| 3 minutes | He enrages (×1.5) | |

## The Starbringer: the House of Death (8424)

This is a fallen star that Ostragoth bound under his house and fed on for centuries. It hangs over the
ring of fused glass in the middle of the room. The way in is the starred iron door north of the Cave of
Wailing (8423). It is locked to Ostragoth's key and can't be picked, bashed or broken by magic. Looking at
the door warns players to bring a great company.

The Starbringer keeps its own numbers (`"raid": true`), so it is not sized for one hero. It has 120,000
health and enrages at 7 minutes (×2). In the balance sim, eight level-60 heroes who stayed in the fight
dealt about 700 damage a second, so 120,000 is about three minutes of pure damage, nearer five with the
mechanics and adds. The sim can't measure a raid properly: its heroes never interrupt, and they flee when
low and never come back. Treat these numbers as a starting point for a real playtest.

| Phase | What | How to answer it |
|---|---|---|
| Always | **Comet Lance** on its target (1.5 s, every 12 s) | Dodge |
| Always | **Corona** around it (3 s, 4.5 m, every 20 s) | Get away from it |
| Always | **Starfall** under a fighter every 6 s | Step out |
| As it weakens | Its light dies (gloom) | |
| 70%, 50%, 25% | Three burning star-motes (level 58) each time | Kill the adds |
| Below 70% | **Event Horizon**: immune to magic for 8 s | Casters switch to blades |
| Below 40% | **Gravity Well**: anyone standing still is crushed | Keep moving |
| Below 40% | **Supernova** (4 s, the whole room) | **Interrupt it**, or it will likely wipe the group. Interrupted, it leaves the Starbringer exposed for 6 s |

Loot: Dawnshard, a blade of starmetal (slash, +4 hit and damage); the Mantle of the Fallen Star (about the
body, +60 health and +2 constitution); and the Ring of the Last Star (+2 intelligence and +2 wisdom). Each
drops 40% of the time.

## Adding another lair

Add an entry to a zone's population file under `lairs`. It needs the boss (`vnum`), the room, and a
`herald` that flies in first. You can also give it the lines it says (`seal`, `heard`, `arrive`,
`transform`, `freed`, `retreat`, `held`, `barred`) and its `mechanics`. Every door of the room seals. A
door that should start open needs a door on both sides in the zone file.
