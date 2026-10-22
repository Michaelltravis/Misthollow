# Misthollow Combat Guide

Master the art of combat in Misthollow! This guide covers everything from basic attacks to advanced class mechanics.

---

## ⚔️ Combat Basics

### Starting a Fight

To attack an enemy, use the `kill` command:

```bash
> kill goblin
You attack the goblin warrior!
You hit the goblin warrior for 12 damage!
The goblin warrior swings at you!
The goblin warrior hits you for 8 damage!
```

Combat continues automatically in **rounds** (every 2 seconds) until one side is dead or flees.

### The Combat Round

Each round, both combatants automatically attack. Your character will:
1. Make a basic attack (and extra attacks if you have Second/Third Attack)
2. Apply any active effects or procs
3. Regenerate a small amount of HP/Mana (based on position)

### Hitting and Missing

Your chance to hit depends on:
- **Hit Bonus** (from gear, stats, buffs)
- **Enemy Armor Class** (lower AC = harder to hit)
- **Your Stats** (DEX for accuracy, STR for power)

```
Attack Roll = d20 + Hit Bonus vs Enemy Defense
```

### Damage Calculation

When you hit, damage is calculated:
```
Base Damage (weapon dice) + Damage Bonus + Stat Bonus
```

**Damage Modifiers:**
- Critical hits deal double damage
- Backstab multiplies damage
- Abilities may add percentage bonuses
- Armor reduces incoming damage

---

## 🎯 Understanding Your Stats

| Stat | Combat Benefit |
|------|----------------|
| **STR** | Melee damage bonus, carrying capacity |
| **DEX** | Hit chance, armor class, dodge |
| **CON** | Maximum HP, HP regeneration |
| **INT** | Spell damage (casters), mana pool |
| **WIS** | Spell effectiveness, mana regen |
| **CHA** | Charm effects, vendor prices, bard songs |

### Armor Class (AC)

Lower AC = Better Defense

- Base AC is 100
- Armor reduces AC (leather: -20, plate: -80)
- Buffs like `armor` and `shield` further reduce AC
- Each 10 AC = ~1 defense point

---

## 🗡️ Combat Skills

### Universal Skills

| Skill | Description | Usage |
|-------|-------------|-------|
| `kick` | Basic kick attack | `kick` |
| `bash` | Shield bash (may stun) | `bash <target>` |
| `rescue` | Pull enemy off ally | `rescue <ally>` |
| `protect` | Intercept attacks on ally | `protect <ally>` |
| `disarm` | Knock weapon away | `disarm <target>` |

### The Second Attack / Third Attack

Higher-level characters gain extra attacks per round:
- **Second Attack** - 2 attacks per round
- **Third Attack** - 3 attacks per round

These trigger automatically in combat.

### Positioning Skills

| Skill | Effect |
|-------|--------|
| `hide` | Become hidden (out of combat) |
| `sneak` | Move without being noticed |
| `backstab` | Attack from hiding for bonus damage |
| `circle` | Move behind enemy for bonus attack |

---

## ✨ Combat Magic

### Casting in Combat

```bash
> cast fireball goblin
You hurl a fireball at the goblin!
The goblin is engulfed in flames for 45 damage!
```

### Spell Targeting

- **Offensive spells** - Require a target: `cast fireball orc`
- **Defensive spells** - Default to self: `cast armor` or `cast armor thorin`
- **Group spells** - Affect your whole party: `cast group_heal`
- **Area spells** - Strike every foe in the room: `cast 'meteor storm'`. In /play you **aim** them:
  the spell's key puts a circle (the blast's size) under the mouse and a ring round you (how far it
  can land); click to cast it there, or press the key again; right-click or Esc lets it go. Only the
  foes inside the circle are struck, so you can hit one pack without waking the rest of the room.
  Typed, an aimed cast is `cast 'meteor storm' @12,7` (where in the room, in metres). Each spell's
  blast and reach are in `spells.py` (`AIM_RADIUS`, `AIM_RANGE`: 16 m); Hallowed Ground keeps
  burning the ground it was cast on.

### Cooldowns

No ability waits more than **two minutes** between uses: a fight lasts a minute or two, so a
capstone (Meteor Storm, Verdict of the Order, Magnum Opus, Divine Intervention, Apocalypse, Titan's
Wrath, Perfect Crime, Alpha Pack, Death Mark) comes round every fight or two, not once an evening.
Two exceptions wait **three minutes**: the class ultimates earned from the marquee quests
(Singularity, Unbroken Banner, Lich Ascension...) and the paladin's Divine Shield (full
invulnerability). Anything already at two minutes or less is unchanged.

### Fights on screen (/play)

In the 3D client a fight is shown, not told. Every swing, spell, wound, stagger, fizzle and death
has its animation and its rising number (`combat_events.py`), so the chat log doesn't repeat it:
- **The log's kinds.** The server marks each line it sends to a web page (`msgkind.py`):
  - **combat:** what is printed while a swing, a skill or a spell resolves, and the fight's own
    lines outside one (a wound over time ticking, a charge gained, an effect wearing off, a
    creature's health bar);
  - **reward:** a kill's experience, streak and rested bonuses, reputation and gold.

  Combat and reward lines live in the chat's **Combat** tab and stay out of **All** unless
  *Settings → Combat text* is on. Refusals ("You don't have enough mana."), speech and a room's
  description are never hidden. Telnet is unchanged.
- **Commands from the bar.** A spell or attack sent from the bar echoes into the Combat tab, and
  a key held down casts once, not twice.
- **Wounds over time.** A burn, a poison or any damage over time rises as a small number in its
  school's colour each tick, and the target frame shows a chip for each thing lingering on the
  creature (a burn, a poison, a slow...). Healing over time rises in green.
- **Charges.** A mage's arcane charges are pips under the health and mana bars. They pop in as they
  are gained and flare as they are spent. The cap is the same everywhere: five, or six with
  Arcane Mastery (the spell's count and Arcane Blast's used to disagree).
- **Effects ending.** When a shield or blessing wears off, its name fades over your head and its icon
  goes.
- **Scrolling combat text** (`world3d/sctlogic.js`, `fx.js` `lane`):
  - **Over what you strike:** your numbers rise in the colour of their harm: fire orange, frost
    ice-blue, lightning pale blue, arcane violet, holy gold, shadow purple, nature and poison green,
    necrotic pale green, blood crimson. A physical blow is cream, or the element of your weapon once
    it glows (tier 4 and up, like its trail). Crits are bigger, outlined and punched in with a
    "!". A spell's or skill's name rides small above its first number ("PYROBLAST 508").
  - **Over your hero:** a column of what happens to you, in order, each new line pushing the older
    ones up:
    - damage taken, in red, glowing in its harm's colour;
    - heals in green, heals over time smaller;
    - Dodge, Parry, Block, Resist and Miss;
    - buffs gained ("+Combustion") and lost ("−Mana Shield");
    - charges gained ("+1 Arcane Charge");
    - control effects ("Stunned!").
- **A kill's rewards** (`combat_hooks`: `xp`, `gold`, `rep` events), drawn, and their lines are filed
  with the fight's:
  - **Experience:** "+209 XP" rises in gold over the fallen creature. The XP bar fills, and the gain
    floats over it with its bonuses as chips (Streak +27, Rested +91). Quest experience fills the
    bar the same way.
  - **Gold:** coins fly from the creature to your pack, and "+330" pops on the pack button.
  - **Reputation:** a small card per faction on the right ("Garathorm Guard +16 · Unfriendly"); a new
    standing is shown in gold ("now Neutral").
- **Creatures cast as heroes do** (`world3d/mobfx-hand.js`, `mobfx.js`). Each creature ability has
  a recipe in the heroes' six columns. Its events (`windup`, `resolve`, `cancel`, `spell`, `heal`,
  `buff`, `debuff`) carry `fx`, the ability's name in lower_snake (`combat_hooks.fx_key`):
  - **The wind-up** is a charge. Its body gives a tell: it rears back, drops low, coils, trembles,
    or raises its hands. What gathers at it builds for the whole wind-up, and it glows in the
    school's colour, a heavy blow smouldering red, brighter as the moment nears. The ground mark
    says what to do: **violet**, break it (kick, bash, silence); **red**, step out or brace.
  - **The release** is that ability's own throw and landing, aimed where the server says. Its
    numbers rise when it arrives. Whoever stepped out of the mark gets "Evaded!".
  - **Broken** (kicked, staggered, snared), what it gathered bursts apart and the creature reels.
  - **Marks by kind:** a creature leaves its family's marks (beast, undead, elemental, demon, insect,
    dragon, construct, caster). Its colours stay its school's, so frost reads as frost on anything.
  - **Size by rank:** a boss gets every flourish. An elite shakes the view a little. An ordinary
    creature's spells are plain (no shake, hit-stop or flash), so your own spells stay the
    brightest thing in the fight.
  - **Checking them:** `/play?demo&gallery=mobfx` plays each ability on four creatures of four
    families (`&cancel` breaks them instead, `&rank=normal|elite|boss`). `tools/dump_mobfx.py` lists
    what the server can send, and `tests/web/mobfx.test.mjs` checks each one has a line.

### Mana Management

- Spells cost mana
- Mana regenerates over time (faster when resting)
- Out of mana? Use melee attacks or potions!

### Key Combat Spells by Type

**Damage:**
```bash
cast magic_missile <target>  # Low damage, reliable
cast fireball <target>       # High fire damage
cast lightning_bolt <target> # High electric damage
cast flamestrike <target>    # Holy fire damage
```

**Healing:**
```bash
cast cure_light              # Small heal (10 mana)
cast cure_serious            # Medium heal (20 mana)
cast heal                    # Full heal (50 mana)
cast group_heal              # Heal party (80 mana)
```

**Buffs (cast before combat!):**
```bash
cast armor                   # -20 AC
cast shield                  # -10 AC, blocks magic missiles
cast bless                   # +2 hit, +1 damage
cast sanctuary               # Reduce damage taken
cast haste                   # Faster attacks
```

---

## 🔴 Class Combat Mechanics

### ⚔️ Warrior: Rage System

Warriors build **Rage** during combat by dealing and taking damage.

```
╔═══════════════════════════════════════════╗
║  Rage: ████████░░░░░░░░░░░░ 40/100        ║
╚═══════════════════════════════════════════╝
```

**Rage Abilities:**
| Ability | Rage Cost | Effect |
|---------|-----------|--------|
| `execute` | 15 | Massive damage to targets below 20% HP |
| `rampage` | 20 | Bonus damage after killing blow |
| `warcry` | 10 | Buff yourself and nearby allies |
| `ignorepain` | 8 | Reduce incoming damage |

**Stances:**
```bash
> stance battle      # Balanced offense/defense
> stance berserk     # +25% damage, +15% damage taken
> stance defensive   # -25% damage, -15% damage taken
> stance precision   # -10% damage, +15% crit chance, +4 hit
```

### 🗡️ Thief: Combo Points

Thieves build **Combo Points** with attacks and spend them on finishers.

```
Combo Points: ● ● ● ○ ○ (3/5)
```

**Builders (add combo points):**
- Backstab (from stealth)
- Sinister Strike
- Basic attacks (chance)

**Finishers (spend combo points):**
| Finisher | Min CP | Effect |
|----------|--------|--------|
| `eviscerate` | 1+ | Damage (scales with CP) |
| `kidneyshot` | 4+ | Stun target |
| `slicedice` | 3+ | Attack speed buff |

**Example Rotation:**
```bash
> hide
You slip into the shadows.

> backstab orc
You backstab the orc for 85 damage! (2 combo points)

> circle
You circle behind the orc! (1 combo point)

> kidneyshot
You kidney shot the orc! Stunned for 4 seconds!
```

### ✝️ Cleric: Divine Favor

Clerics build **Divine Favor** through healing and turning undead.

```
Divine Favor: ★★★☆☆ (60/100)
```

**Building Divine Favor:**
- Healing allies
- Turn Undead ability
- Prayer (out of combat)

**Spending Divine Favor:**
```bash
> holysmite zombie
You channel divine wrath into the zombie for 120 holy damage!
(Costs Divine Favor)
```

### ⚜️ Paladin: Auras & Seals

**Auras (one active at a time):**
```bash
> aura devotion      # Increased armor for nearby allies
> aura protection    # Damage reduction for nearby allies  
> aura retribution   # Reflect damage to attackers
```

**Lay on Hands:**
```bash
> layhands           # Powerful self-heal (long cooldown)
> layhands thorin    # Heal an ally
```

### 🏹 Ranger: Animal Companions

Rangers can tame animal companions to fight alongside them.

**Taming:**
```bash
> tame wolf
You begin taming the grey wolf...
The grey wolf becomes your loyal companion!
```

**Companion Types:**
| Animal | Specialty |
|--------|-----------|
| Wolf | Balanced damage |
| Bear | Tank (high HP) |
| Hawk | Fast attacks, interrupts |
| Cat | Stealth, high crit |
| Boar | Charge, stuns |

**Managing Companions:**
```bash
> companion          # View companion status
> companion attack   # Command to attack
> companion stay     # Hold position
> companion dismiss  # Release companion
```

### 💀 Necromancer: Undead Minions

Necromancers raise undead servants from corpses.

```bash
> raise warrior
You raise a skeletal warrior from the corpse!

> raise healer
You raise a spectral healer from the corpse!
```

**Minion Types:**
| Type | Role |
|------|------|
| Warrior | Melee tank |
| Healer | Heals you and other minions |
| Caster | Ranged magic damage |
| Rogue | Stealth attacks, debuffs |

**Soulstone:**
Hold a soulstone for bonus INT and to store souls for later raising.

### 🎵 Bard: Songs

Bards maintain one song at a time, providing buffs to nearby allies.

```bash
> perform courage
You begin performing Song of Courage!
Your allies feel emboldened! (+2 hit, +2 damage)
```

**Song Types:**
| Song | Effect |
|------|--------|
| Courage | +hit/damage to allies |
| Defense | +AC to allies |
| Speed | +attack speed to allies |
| Healing | Regen HP over time |
| Mana | Regen mana over time |

**Encore:**
```bash
> encore
You extend your current performance!
```

---

## 📊 Combat States

### Positions

| Position | Regen Rate | Combat |
|----------|------------|--------|
| Standing | Normal | Can fight |
| Sitting | +50% | Can't fight |
| Resting | +100% | Can't fight |
| Sleeping | +150% | Can't fight, vulnerable |
| Fighting | Minimal | In combat |

Change position:
```bash
> sit        # Sit down
> rest       # Rest (faster regen)
> sleep      # Sleep (fastest regen)
> stand      # Stand up
> wake       # Wake from sleep
```

### Fleeing Combat

When things go badly, run!

```bash
> flee
You flee north!
You lose 10 experience points.
```

**Flee Mechanics:**
- Random exit direction
- May fail if stunned/slowed
- Costs experience points
- Better than dying!

---

## 🎯 Combat Tips

### Before Combat

1. **Buff up!** Cast protective spells:
   ```bash
   cast armor
   cast bless
   cast sanctuary
   ```

2. **Check your opponent:**
   ```bash
   consider troll
   > "This could be difficult."
   ```

3. **Heal to full:**
   ```bash
   cast cure_serious
   ```

### During Combat

1. **Use skills!** Don't just auto-attack:
   ```bash
   kick
   bash
   cast fireball troll
   ```

2. **Watch your HP:**
   ```
   HP: 45/150 - Time to heal or flee!
   ```

3. **Know when to run:**
   ```bash
   flee
   ```

### After Combat

1. **Loot the corpse:**
   ```bash
   get all corpse
   ```

2. **Heal up:**
   ```bash
   rest
   cast cure_light
   ```

3. **Check for quests:**
   ```bash
   quest log
   ```

---

## ⚡ Status Effects

### Buffs (Good)

| Effect | Benefit |
|--------|---------|
| Blessed | +hit, +damage |
| Hasted | Faster attacks |
| Sanctuary | Reduced damage |
| Invisible | Enemies can't see you |
| Protected | Magic resistance |

### Debuffs (Bad)

| Effect | Penalty |
|--------|---------|
| Poisoned | Damage over time |
| Blinded | Reduced hit chance |
| Slowed | Slower attacks |
| Weakened | Reduced damage |
| Stunned | Can't act |
| Feared | Forced to flee |

### Removing Debuffs

```bash
cast remove_poison    # Cure poison
cast cure_blindness   # Cure blindness
cast remove_curse     # Remove curses
quaff antidote        # Drink cure potion
```

---

## 👥 Group Combat

### Forming a Group

```bash
> group thorin
You invite Thorin to your group.

> group
Group Leader: You
Members:
  - Thorin (Warrior) [100%]
  - Gandalf (Mage) [100%]
```

### Group Tactics

**Tank and Spank:**
1. Warrior attacks first (gets aggro)
2. DPS attacks second
3. Healer keeps tank alive

**Assist:**
```bash
> assist thorin
You rush to assist Thorin!
```

**Protect:**
```bash
> protect gandalf
You move to protect Gandalf.
```

**Rescue:**
```bash
> rescue gandalf
You heroically rescue Gandalf!
The orc turns to attack you instead.
```

### Group Communication

```bash
> gtell Heal me please!
[Group] You: Heal me please!
```

---

## 🏆 Boss Fights

Boss monsters have special mechanics:

### Boss Indicators
- Named enemies with titles
- Higher HP pools
- Special abilities
- Better loot!

### Common Boss Mechanics

| Mechanic | Description | Counter |
|----------|-------------|---------|
| Enrage | +damage at low HP | Burn fast |
| AoE Attack | Hits everyone | Spread out |
| Summon Adds | Spawns minions | Kill adds |
| Heal | Heals itself | Interrupt |
| Stun | Disables tank | Have backup |

### Boss Tips

1. **Bring a group** - Most bosses need 3+ players
2. **Know the fight** - Learn mechanics first
3. **Assign roles** - Tank, heals, DPS
4. **Prepare** - Full buffs, potions ready
5. **Communicate** - Use group chat

---

## 📈 Improving Combat Performance

### Gear Upgrades

Better equipment = better combat:
- Higher damage weapons
- Lower AC armor
- +hit and +damage bonuses

### Skill Practice

```bash
> practice kick
You improve your kicking! Kick: 75% -> 80%
```

Higher skill = more effective abilities.

### Talent Points

Spend talent points to unlock new abilities:
```bash
> talents
> talent learn execute
You learn Execute!
```

### Consumables

Stock up on potions!
```bash
> quaff healing
You feel much better!

> quaff mana
Your mind feels refreshed!
```

---

## 🎮 Combat Commands Quick Reference

```
ATTACKING           DEFENDING           SUPPORT
─────────────       ─────────────       ─────────────
kill <target>       flee                rescue <ally>
kick                consider <mob>      protect <ally>
bash <target>       cast sanctuary      assist <ally>
backstab <target>   rest                cast group_heal
cast <spell>        quaff potion        gtell <message>

CLASS SPECIFIC
─────────────────────────────────────────────────────
Warriors: stance, execute, rampage, warcry
Thieves: combo, eviscerate, kidneyshot, slicedice
Clerics: turnundead, holysmite, divinefavor
Paladins: aura, layhands, smite
Rangers: companion, track, tame
Necros: raise, soulstone
Bards: perform, encore, fascinate
```

---

Now get out there and slay some monsters! ⚔️🐉

---

## 🔧 DEVELOPMENT NOTES: Combat System Gaps

*Last updated: February 6, 2026*

### Implemented ✅

| Feature | Status | Notes |
|---------|--------|-------|
| Basic attack loop | ✅ | Hit/miss/damage per round |
| Armor Class | ✅ | Lower AC = harder to hit |
| Avoidance | ✅ | Dodge, parry, block, riposte |
| Multi-attack | ✅ | Second/third attack by skill |
| Critical hits | ✅ | 2x damage multiplier |
| Pet combat | ✅ | Auto-assist, modes, orders |
| Cooldowns | ✅ Partial | Per-ability, needs display command |
| Taunt | ✅ Basic | Single-target threat |

### Class Systems ✅

All 9 classes have unique resource systems:

| Class | Resource | Mechanic |
|-------|----------|----------|
| Warrior | Rage | Builds on hit/being hit, powers abilities |
| Thief | Combo Points | Build with attacks, spend on finishers |
| Cleric | Divine Favor | Builds through healing, unlocks miracles |
| Paladin | Holy Power + Auras | Stacking power + passive buffs |
| Necromancer | Soul Essence | Harvested from kills, powers undead |
| Ranger | Focus | Concentration for precision abilities |
| Bard | Rhythm | Stacks from performances, buffs songs |
| Mage | Arcane Charges | Build for burst damage |
| Assassin | Combo + Poison | Build combo, apply lethal poisons |

### Not Yet Implemented 🔴

#### Priority 1: Core Combat
| Feature | Difficulty | Impact |
|---------|------------|--------|
| **Damage Types** | Medium | Physical, fire, cold, lightning, holy, shadow, nature, arcane |
| **Resistances** | Medium | Per-mob/player vulnerability/resistance to damage types |
| **Threat Table** | High | Proper aggro management for tanking |
| **Interrupt/Counterspell** | Medium | Stop casts, require timing |
| **CC Diminishing Returns** | Medium | Repeated CC becomes less effective |

#### Priority 2: Quality of Life
| Feature | Difficulty | Impact |
|---------|------------|--------|
| **`cooldowns` command** | Low | Show all active cooldowns |
| **Combat log** | Low | Detailed damage breakdown |
| **Target lock** | Low | Maintain focus on one enemy |
| **Assist improvements** | Low | Better party coordination |

#### Priority 3: Missing Class Abilities
| Class | Missing Abilities |
|-------|------------------|
| Warrior | Charge (gap close), Shield Wall (party defense), Execute (low HP) |
| Mage | Polymorph (CC), Counterspell, Blink (escape) |
| Thief | Traps, Blind, Distract |
| Ranger | Freezing Trap, Misdirection |
| Cleric | Power Word: Shield, Penance |
| Paladin | Hammer of Justice (ranged stun) |
| Necromancer | Army of the Dead, Anti-Magic Shell |
| Bard | Silencing Song, Mass Dispel |
| Assassin | Smoke Bomb, Garrote silence |

#### Priority 4: Boss Mechanics
| Feature | Description |
|---------|-------------|
| Phase transitions | Bosses change behavior at HP thresholds |
| Telegraphed attacks | Warning before big hits |
| Add spawning | Boss summons helpers |
| Positioning | Frontal cleave, back attacks |
| Enrage timers | Soft/hard enrage for DPS checks |

### Recommended Next Steps

1. **Add damage types + resistances** - Foundation for interesting combat
2. **Implement `cooldowns` command** - Critical for players
3. **Build threat table** - Required for proper tank/healer/DPS
4. **Add missing class abilities** - Fill out rotations
