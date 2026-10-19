"""
Auto-generated help for every spell, skill, and talent in Misthollow.

This module is the single source of truth for ability help text. Rather than
hand-maintaining hundreds of entries that drift out of sync with the code, it
*generates* help from the authoritative game data:

  - spells       -> spells.SPELLS               (mana/level/damage/affects/...)
  - talent trees -> talents.CLASS_TALENT_TREES  (per-talent descriptions)
  - class lists  -> config.Config.CLASSES       (who learns what)
  - skills       -> SKILL_PROSE (curated below) + class ownership

Curated prose layers nuance on top of the raw stats (how to *use* an ability,
combos, resource mechanics) where the numbers alone don't tell the story.
Everything else is described from its data so coverage is total.

`build_ability_help()` returns a {topic: entry} dict in the same shape as
help_data.HELP_TOPICS, and help_data merges it in at import time.
"""

# ---------------------------------------------------------------------------
# Ownership: who can learn each spell (class lists + talent unlocks)
# ---------------------------------------------------------------------------

def _spell_owners():
    """Map spell_key -> sorted list of classes that can access it."""
    owners = {}
    try:
        from config import Config
        for cls, data in Config.CLASSES.items():
            for sp in data.get('spells', []):
                owners.setdefault(sp, set()).add(cls)
    except Exception:
        pass
    try:
        from talents import CLASS_TALENT_TREES
        for cls, trees in CLASS_TALENT_TREES.items():
            for tree in trees:
                for t in tree['talents'].values():
                    unlock = (t.effects or {}).get('skill_unlock')
                    if unlock:
                        owners.setdefault(unlock, set()).add(cls)
    except Exception:
        pass
    return {k: sorted(v) for k, v in owners.items()}


def _skill_owners():
    """Map skill_key -> sorted list of classes that learn it."""
    owners = {}
    try:
        from config import Config
        for cls, data in Config.CLASSES.items():
            for sk in data.get('skills', []):
                owners.setdefault(sk, set()).add(cls)
    except Exception:
        pass
    return {k: sorted(v) for k, v in owners.items()}


# ---------------------------------------------------------------------------
# Human-readable rendering helpers
# ---------------------------------------------------------------------------

# How affect types read to a player.
_AFFECT_NAMES = {
    'sanctuary': 'halves incoming damage',
    'damroll': 'bonus damage',
    'hitroll': 'bonus to hit',
    'ac': 'improved armor',
    'armor': 'improved armor',
    'stunned': 'stun (cannot act)',
    'stun': 'stun (cannot act)',
    'rooted': 'rooted in place',
    'root': 'rooted in place',
    'slow': 'slowed',
    'haste': 'extra attack speed',
    'blind': 'blinded',
    'blindness': 'blinded',
    'poison': 'poison damage over time',
    'fear': 'feared (flees)',
    'sleep': 'asleep',
    'curse': 'cursed',
    'weaken': 'weakened (reduced strength)',
    'invisibility': 'invisible',
    'invisible': 'invisible',
    'fly': 'flying',
    'fireshield': 'burns melee attackers',
    'fire_shield': 'burns melee attackers',
    'iceshield': 'chills melee attackers',
    'shield': 'magical damage shield',
    'mana_shield': 'damage drains mana instead of HP',
    'stoneskin': 'stoneskin (absorbs hits)',
    'detect_invis': 'see invisible',
    'detect_magic': 'detect magic',
    'detect_evil': 'detect evil',
    'protection_evil': 'protection from evil',
    'protection_good': 'protection from good',
    'regeneration': 'healing over time',
    'regen': 'healing over time',
    'str': 'strength',
    'dex': 'dexterity',
    'int': 'intelligence',
    'wis': 'wisdom',
    'con': 'constitution',
    'save_spell': 'spell resistance',
}


def _affect_phrase(aff):
    """Render one affect dict as a short phrase, e.g. '+2 bonus damage'."""
    t = aff.get('type', '')
    name = _AFFECT_NAMES.get(t, t.replace('_', ' '))
    val = aff.get('value')
    if isinstance(val, (int, float)) and val not in (0, 1) and t not in (
            'sanctuary', 'mana_shield', 'stoneskin', 'fly', 'invisibility', 'invisible'):
        sign = '+' if val > 0 else ''
        return f"{sign}{val} {name}"
    return name


def _ticks(n):
    """A 'tick' is roughly the combat round / heartbeat; ~couple seconds."""
    return f"{n} round{'s' if n != 1 else ''}"


def _target_line(target):
    return {
        'offensive': 'Targets an enemy.',
        'defensive': 'Targets you or a friendly player.',
        'self': 'Affects only you.',
        'group': 'Affects your whole group.',
        'object': 'Targets an item.',
        'room': 'Affects everything in the room.',
        'area': 'Affects everything in the room.',
    }.get(target, 'See description for targeting.')


def _cast_syntax(key, data):
    name = data.get('name', key).lower()
    tgt = data.get('target')
    if tgt == 'offensive':
        return f"cast '{name}' <enemy>"
    if tgt == 'defensive':
        return f"cast '{name}' [target]"
    if tgt in ('self', 'group', 'room', 'area'):
        return f"cast '{name}'"
    if tgt == 'object':
        return f"cast '{name}' <item>"
    return f"cast '{name}' [target]"


# ---------------------------------------------------------------------------
# Class resource reminders (shown on a class's signature abilities)
# ---------------------------------------------------------------------------

CLASS_RESOURCE = {
    'warrior': 'Momentum — built by landing blows, spent on finishers.',
    'mage': 'Arcane Charges — built by casting, spent to empower spells.',
    'cleric': 'Faith — built by smiting and healing, spent on miracles.',
    'thief': 'Luck — built by tricks, gambled on big payoffs.',
    'ranger': 'Focus — regenerates over time, spent on shots.',
    'paladin': 'Holy Power — built by Dawnstrikes, spent on finishers.',
    'necromancer': 'Soul Shards — harvested from the dying, spent on death-magic.',
    'bard': 'Inspiration — built by performing, spent on crescendos.',
    'assassin': 'Intel — built by marking, spent to guarantee kills.',
}


# ---------------------------------------------------------------------------
# Curated prose: the *how to use it* layer for signature / special spells.
# Auto-generation handles everything not listed here from raw stats.
# ---------------------------------------------------------------------------

SPELL_PROSE = {
    # --- Necromancer: Soulbinder of the Mist (Soul Shards) ---
    'mistgrasp': "Seizes a foe in grave-mist: shadow damage that roots them in "
                 "place and banks 1 Soul Shard. Your bread-and-butter opener — "
                 "it locks a target down and starts building shards to spend.",
    'wraithfire': "Hurls bound spirits at a foe, consuming up to 5 banked Soul "
                  "Shards for bonus damage per shard. Cast it once you've stockpiled "
                  "shards from Mistgrasp/Mistrot for a burst payoff.",
    'mistrot': "A festering rot-curse that ticks damage over several rounds and "
               "releases a Soul Shard when the host finally dies. Apply it early; "
               "stack it on tough targets and let it feed your shard economy.",
    'sever_cord': "Execute finisher: against a foe below ~25% HP it reaps a massive "
                  "death-strike and refunds 3 Soul Shards. Save it to close out a "
                  "weakened enemy and refuel for the next fight.",
    'leechcraft': "Drains an enemy's life to heal you, banking any overheal toward a "
                  "Soul Shard. Sustains you in long fights.",
    'corpse_shield': "Wraps you in a ward of risen flesh that absorbs incoming "
                     "damage. Pop it before a big hit lands.",
    'summon_gargoyle': "Calls a stone gargoyle to fight at your side for a time. A "
                       "durable extra attacker for boss fights.",
    'soul_harvest': "Tears the souls from everything around you, converting the "
                    "carnage into a surge of Soul Shards. Best after an AoE pull.",
    'apocalypse_necro': "Your ultimate: unleashes a tide of death-magic across the "
                        "whole room. Long cooldown — open big pulls or bosses with it.",

    # --- Mage: Adept of the High Tower (Arcane Charges) ---
    'tower_echoes': "Conjures mirror-images of yourself that confuse foes and soak "
                    "attacks meant for you. A defensive opener.",
    'phase_step': "A short blink that teleports you a few rooms / out of melee. Use "
                  "it to reposition, escape a gank, or close distance.",
    'stepwise': "Measured arcane movement that shifts you safely past danger. The "
                "Tower's controlled answer to a blink.",
    'mirrorward': "Raises a reflective ward that bounces a portion of spell damage "
                  "back at casters. Strong against enemy mages.",
    'quicken': "Speeds your own casting for a short window — chain spells faster. "
               "Line it up before a burst rotation.",
    'rimeheart': "Frost mastery: empowers your cold spells and can flash-freeze a "
                 "target solid. Frost (Rimeward) mages' burst button.",
    'kindling_focus': "Stokes your inner fire so your flame spells hit harder for a "
                      "time. Fire (Emberweave) mages' ramp tool.",
    'resonance_burst': "Detonates your stored Arcane Charges in a single blast — the "
                       "more charges spent, the bigger the hit. Build charges with "
                       "Towerbolt, then unload.",

    # --- Cleric: Keeper of the Holy Order (Faith) ---
    'travelling_grace': "Lays a healing blessing that hops between wounded party "
                        "members, mending each in turn. Cast it on the most hurt "
                        "ally and let it bounce.",
    'shared_burden': "Links your group's life forces so damage is split evenly — no "
                     "one drops while the link holds. Use it during heavy AoE.",
    'font_of_the_vigil': "Plants a font of holy light in the room that party members "
                         "can draw healing from. Drop it before a big fight.",
    'serenity': "A potent self-heal and cleanse that restores a large chunk of HP "
                "and calms harmful effects. Your emergency button.",
    'cleansing_rite': "Strips harmful magic from everyone in the room at once. Great "
                      "answer to enemy debuffs and curses.",
    'divine_intervention': "Ultimate: shields your entire group from death for a "
                           "short, desperate window. Save it for a wipe-or-win moment.",

    # --- Paladin: Lightbringer (Holy Power) ---
    'hallowed_ground': "Consecrates the floor beneath you, searing enemies who stand "
                       "on it each round. Drop it where foes must fight you.",
    'dawnhammer': "Hurls a hammer of dawn-light that damages and stuns a foe. A "
                  "reliable Holy Power finisher and interrupt.",
    'ascendant_hour': "Ascend into a state of heightened holy power — boosted damage "
                      "and healing for the duration. Your offensive cooldown.",
    'verdict_of_the_order': "Ultimate judgement: an enormous single-target smite. "
                            "Long cooldown — reserve it for bosses.",
    'unfettered': "Frees you (or an ally) from movement-impairing effects and wards "
                  "against more. Cast it when rooted, slowed, or snared.",

    # --- Ranger: Silversong Warden (Focus) ---

    # --- Core / shared utility ---
    'heal': "Restores a large, fixed amount of health to the target. Your biggest "
            "single-target heal.",
    'group_heal': "Heals every member of your group at once. Best when several "
                  "allies are hurt.",
    'sanctuary': "Halves all incoming damage to the target for the duration — one of "
                 "the strongest defensive buffs in the game. Cast before tanking.",
    'fireball': "A staple ranged nuke: a burst of fire that scales with your level. "
                "Reliable single-target damage for mages.",
    'word_of_recall': "Whisks you home to your recall point. Cheap escape — but it "
                      "fails if you're fighting, so flee first.",
    'teleport': "Jumps you to a random location in the world. Cheap travel, "
                "unpredictable destination.",
    'resurrect': "Raises a dead player and restores lost experience. Cast it on a "
                 "corpse to bring an ally back.",
    'identify': "Reveals an item's hidden statistics and properties. Cast it before "
                "deciding what to wear or sell.",
    'enchant_weapon': "Permanently augments a weapon with bonus to-hit and damage. "
                      "Can fail on high attempts — enchant your best gear.",
}



# ---------------------------------------------------------------------------
# Spell entry generation
# ---------------------------------------------------------------------------

def _spell_effect_summary(data):
    """Build mechanical 'what it does' lines from the spell's data fields."""
    bits = []
    dd = data.get('damage_dice')
    if dd:
        per = data.get('damage_per_level')
        elem = data.get('element')
        line = f"Damage: {dd}"
        if per:
            line += f" (+{per}/level)"
        if elem:
            line += f" {elem}"
        bits.append(line)
    hd = data.get('heal_dice')
    if hd:
        per = data.get('heal_per_level')
        line = f"Healing: {hd}"
        if per:
            line += f" (+{per}/level)"
        bits.append(line)
    if data.get('dot_damage') or data.get('damage_per_tick'):
        dot = data.get('dot_damage') or data.get('damage_per_tick')
        dur = data.get('dot_duration') or data.get('duration_ticks') or 0
        bits.append(f"Over time: {dot} per round for {_ticks(dur)}")
    if data.get('heal_per_tick'):
        dur = data.get('duration_ticks') or 0
        bits.append(f"Heals {data['heal_per_tick']} per round for {_ticks(dur)}")
    affects = data.get('affects') or []
    if affects:
        phrases = ", ".join(_affect_phrase(a) for a in affects)
        dur = data.get('duration_ticks')
        line = f"Applies: {phrases}"
        if data.get('ward'):
            line += " (15 to 30 minutes, longer as you level)"
        elif dur:
            line += f" ({_ticks(dur)})"
        bits.append(line)
    if data.get('bounces'):
        bits.append(f"Bounces to up to {data['bounces']} nearby targets")
    if data.get('cooldown'):
        bits.append(f"Cooldown: {data['cooldown']}s")
    if data.get('save'):
        bits.append(f"Target may save vs. {data['save']} to resist")
    return bits


def _gen_spell_entry(key, data, owners):
    name = data.get('name', key.replace('_', ' ').title())
    classes = owners.get(key, [])
    parts = []
    prose = SPELL_PROSE.get(key)
    if prose:
        parts.append(prose)
        parts.append("")
    # mechanical stat block
    parts.append(_target_line(data.get('target')))
    eff = _spell_effect_summary(data)
    if eff:
        parts.append("")
        parts.extend("  " + e for e in eff)
    # how to use
    parts.append("")
    parts.append("HOW TO USE: " + _cast_syntax(key, data))
    if len(classes) == 1 and classes[0] in CLASS_RESOURCE:
        parts.append("RESOURCE: " + CLASS_RESOURCE[classes[0]])
    if not classes:
        parts.append("(Utility / situational magic — not in a standard class list.)")
    return {
        'category': 'spell',
        'title': name,
        'syntax': _cast_syntax(key, data),
        'classes': [c.title() for c in classes] or ['Special'],
        'level': data.get('level_required', 1),
        'mana': data.get('mana_cost', 0),
        'description': "\n".join(parts),
    }


# ---------------------------------------------------------------------------
# Curated skill prose. Skills are bespoke commands, so their mechanics can't be
# inferred from data the way spells can — each is described by hand here.
# {key: (description, syntax_or_None)}
# ---------------------------------------------------------------------------

SKILL_PROSE = {
    # --- passives shared across classes ---
    'second_attack': ("Passive. Grants a chance at a second melee swing each round. "
                      "Practice it up to attack more often.", None),
    'third_attack': ("Passive. Grants a chance at a third melee swing each round, on "
                     "top of Second Attack.", None),
    'dual_wield': ("Passive. Lets you fight with a weapon in each hand. Wield a "
                   "second one-handed weapon to gain its extra attack.", None),
    'parry': ("Passive. A chance to deflect incoming melee with your weapon. Higher "
              "skill parries more often.", None),
    'dodge': ("Passive. A chance to sidestep incoming melee. Scales with Dexterity "
              "and skill.", None),
    'shield_block': ("Passive. A chance to block an attack with an equipped shield, "
                     "negating the hit.", None),
    'evasion': ("Passive. A chance to avoid attacks entirely. The rogue's answer to "
                "heavy armor — keep it high.", None),

    # --- warrior (Momentum) ---
    'strike': ("Your basic Momentum-builder: a clean weapon blow. Use it to start a "
               "chain and bank Momentum for finishers.", "strike <target>"),
    'bash': ("Slam a foe with your shield/body to stun them briefly and interrupt "
             "their action. Great for stopping a caster.", "bash <target>"),
    'cleave': ("A sweeping blow that strikes your target and others fighting you. "
               "Your main multi-target Momentum builder.", "cleave"),
    'heroic_throw': ("Hurl a throwing axe at a foe up to 15 m away: a little damage and the fight "
                     "is on. In /play it reaches into the next room and draws the foe to you.", "heroic_throw <target>"),
    'charge': ("Rush a distant enemy, closing the gap and stunning on impact. A "
               "classic opener — starts the fight on your terms.", "charge <target>"),
    'rally': ("A battle-shout that bolsters you and your group. Pop it before a tough "
              "pull for the buff.", "rally"),
    'execute': ("Finisher: a devastating blow against a wounded foe (low HP), spending "
                "Momentum for big damage. Close out kills with it.", "execute <target>"),
    'doctrine': ("Choose your Martial Doctrine — Iron Wall, Berserker, or Warlord — "
                 "reshaping how your abilities behave. Type 'doctrine' to see options "
                 "and 'doctrine <name>' to commit.", "doctrine [name]"),
    'swear': ("Swear a martial oath that grants a lasting passive edge tied to your "
              "Doctrine. Use 'swear' to view available oaths.", "swear [oath]"),
    'evolve': ("Evolve one of your signature abilities into a stronger named form "
               "(e.g. Whirlwind -> Bloodwhirl). Type 'evolve' to see what you can "
               "upgrade.", "evolve [ability]"),
    'kick': ("A quick kick for extra unarmed damage on your turn. Cheap filler that "
             "builds a little Momentum.", "kick <target>"),
    'rescue': ("Throw yourself in front of an ally, taking the enemy's aggression onto "
               "you. The tank's most important button — save squishies with it.",
               "rescue <ally>"),

    # --- mage (Arcane Charges) ---
    'scribe': ("Scribe a spell into a scroll or your spellbook for later use. Lets you "
               "prepare and share magic.", "scribe <spell>"),
    'towerbolt': ("Signature bolt of the High Tower (was Arcane Blast): heavy arcane "
                  "damage that builds an Arcane Charge each cast. Your main "
                  "charge-builder.", "towerbolt <target>"),
    'charge_release': ("Discharge your stored Arcane Charges in one barrage (was "
                       "Arcane Barrage) — damage scales with charges spent. Build with "
                       "Towerbolt, then release.", "charge_release <target>"),
    'drink_the_leyline': ("Tap the leyline to rapidly restore your mana (was "
                          "Evocation). Channel it when you're running dry mid-fight.",
                          "drink_the_leyline"),

    # --- cleric (Faith) ---
    'turn_undead': ("Channel holy power to damage, fear, or destroy undead enemies. "
                    "Far stronger against the risen — your tool in crypts.",
                    "turn_undead"),
    'holy_smite': ("A bolt of divine fire that builds Faith. Your reliable ranged "
                   "attack and Faith-builder.", "holy_smite <target>"),
    'divine_word': ("Speak a word of power that smites enemies or empowers allies "
                    "depending on your focus. Spends Faith.", "divine_word <target>"),
    'pyre_of_faith': ("Sets a foe ablaze with sacred fire (was Holy Fire): immediate "
                      "damage plus a burning DoT. Apply early and let it tick.",
                      "pyre_of_faith <target>"),

    # --- thief (Luck) ---
    'backstab': ("A lethal opening strike from stealth/behind for multiplied damage. "
                 "Only works as an opener — hide or sneak first.", "backstab <target>"),
    'sneak': ("Move unseen so you can slip past or set up an ambush. Toggle it on; "
              "fast movement or attacks break it.", "sneak"),
    'hide': ("Melt into the shadows in the current room, becoming unseen until you "
             "act. Pairs with Backstab.", "hide"),
    'steal': ("Pick a target's pocket for gold or an item. Failure angers them — high "
              "risk, high reward.", "steal <item> <target>"),
    'pick_lock': ("Pick a locked door or chest open without a key. Needs decent skill "
                  "for tougher locks.", "pick <direction|container>"),
    'cover_tracks': ("Sweep away your trail: anything already hunting you that is not in sight "
                     "loses it, and for a few minutes you leave none (hunters lose your trail, "
                     "creatures notice you only from half as far, those you flee give up for "
                     "longer, a theft leaves no trace; no footprints in /play). Best with sneak.",
                     "cover_tracks"),
    'detect_traps': ("Spot traps on doors, chests, and floors before they spring on "
                     "you. Keep it practiced when delving dungeons.", "detect_traps"),
    'knife_toss': ("Flick a knife at a foe up to 14 m away: a little damage and the fight is "
                   "on. In /play it reaches into the next room and draws the foe to you.", "knife_toss <target>"),
    'pocket_sand': ("Cheap Trick (was Pocket Sand): fling grit to blind a foe and buy "
                    "yourself an escape or a free backstab.", "pocket_sand <target>"),
    'low_blow': ("A dirty strike below the belt that staggers and debilitates the "
                 "target. Spends Luck for a nasty hit.", "low_blow <target>"),
    'rigged_dice': ("Loaded Odds (was Rigged Dice): stack the odds in your favor, "
                    "raising your crit/Luck generation for a short streak.",
                    "rigged_dice"),
    'jackpot': ("The Big Score (was Jackpot): gamble your banked Luck on a massive "
                "payoff hit — the more Luck, the bigger the score.", "jackpot <target>"),
    'circle': ("Circle behind a foe you're already fighting to land a backstab-style "
               "strike mid-combat. No stealth required.", "circle <target>"),
    'trip': ("Sweep a target's legs to knock them down, costing them their next "
             "action. Good interrupt and setup.", "trip <target>"),

    # --- ranger (Focus) ---
    'track': ("Follow a creature's or player's trail through the world, pointing you "
              "toward your quarry.", "track <name>"),
    'scan': ("Peer into adjacent rooms to see who and what lies ahead before you walk "
             "in. Scout safely.", "scan [direction]"),
    'truesight_shot': ("A patient, perfectly-aimed shot (was Aimed Shot): high "
                       "single-target damage that spends Focus. Your hardest hitter.",
                       "truesight_shot <target>"),
    'wildbond_strike': ("Command your bonded beast to savage a target (was Kill "
                        "Command). Your pet's burst — tame a companion first.",
                        "wildbond_strike <target>"),
    'loosing_storm': ("A storm of arrows (was Rapid Fire): rapid multi-hit fire that "
                      "spends Focus. Great burst on a single target.",
                      "loosing_storm <target>"),
    'quarry_mark': ("Mark your quarry (was Hunter's Mark): the target takes more "
                    "damage from you and can't lose you easily. Open with it.",
                    "quarry_mark <target>"),
    'tame': ("Tame a wild beast into a loyal companion that fights beside you. Core of "
             "the Beast-bond ranger.", "tame <beast>"),

    # --- paladin (Holy Power) ---
    'censure': ("A righteous smite that builds Holy Power (was Smite). Your reliable "
                "Holy Power generator.", "censure <target>"),
    'oath': ("Swear a paladin's oath, binding you to a code that grants a lasting "
             "blessing. Type 'oath' to review choices.", "oath [name]"),
    'order_verdict': ("Verdict of the Order (was Templar's Verdict): a Holy Power "
                      "finisher that delivers heavy holy damage. Spend 3 Holy Power "
                      "for the full hit.", "order_verdict <target>"),
    'absolution': ("Absolution (was Word of Glory): convert Holy Power into a strong "
                   "heal for yourself or an ally. Your self-sustain finisher.",
                   "absolution [target]"),
    'halo_of_reckoning': ("Halo of Reckoning (was Divine Storm): a spinning holy "
                          "nova that strikes every enemy around you. Spend Holy Power "
                          "to clear packs.", "halo_of_reckoning"),

    # --- necromancer (Soul Shards) ---
    'soul_bolt': ("A bolt of soul-energy that builds a Soul Shard on cast. Your basic "
                  "ranged attack and shard-builder.", "soul_bolt <target>"),
    'soul_siphon': ("Drain a foe's life and soul (was Drain Soul): damages them, heals "
                    "you, and feeds your shard pool.", "soul_siphon <target>"),
    'bone_shield': ("Ring yourself with whirling bone that absorbs incoming hits. Pop "
                    "it before you take damage.", "bone_shield"),
    'soul_reap': ("Reap a wounded foe with a shard-fueled scythe finisher. Spends Soul "
                  "Shards for big execute damage.", "soul_reap <target>"),

    # --- bard (Inspiration) ---
    'lore': ("Recall lore about an item, creature, or place — identifying properties "
             "and history. The bard's knowledge.", "lore <subject>"),
    'countersong': ("Sing a counter-melody that disrupts enemy spellcasting and shields "
                    "your group from magic.", "countersong"),
    'fascinate': ("Captivate an enemy with performance, holding them transfixed and "
                  "out of the fight. A soft crowd-control.", "fascinate <target>"),
    'mockery': ("Hurl a cutting verbal jab that demoralizes a foe, lowering their "
                "effectiveness. Builds Inspiration.", "mockery <target>"),
    'crescendo': ("Build your performance to a crescendo, spending Inspiration for a "
                  "powerful burst effect. Your payoff button.", "crescendo"),
    'encore': ("Repeat your last performance/song immediately, extending its benefit. "
               "Great for keeping a buff up.", "encore"),
    'discordant_note': ("Strike a jarring note that damages and disrupts enemies who "
                        "hear it. Offensive Inspiration spender.",
                        "discordant_note <target>"),

    # --- assassin (Intel) ---
    'mark': ("Contract Mark (was Mark): place an Intel mark on a target, the first "
             "step toward a guaranteed kill. Open every contract with it.",
             "mark <target>"),
    'expose': ("Read the Mark (was Expose): study your marked target to reveal a "
               "weakness, raising your damage against them and building Intel.",
               "expose <target>"),
    'vital': ("Strike a vital point on a marked foe for amplified, often crippling "
              "damage. Your precision Intel spender.", "vital <target>"),
    'execute_contract': ("Fulfil the Contract (was Execute Contract): cash in your "
                         "built-up Intel marks for a near-guaranteed killing strike on "
                         "a weakened target.", "execute_contract <target>"),
    'feint': ("A feinting strike that drops the target's guard and your own threat. "
              "Sets up a safer follow-up.", "feint <target>"),
    'fade': ("Vanish (was Fade): drop out of sight instantly, breaking combat and "
             "resetting to stealth. Your escape/reset.", "fade"),
    'slip_the_veil': ("Slip the Veil (was Shadow Step): teleport through shadow to "
                      "appear behind your target, ready to backstab. Gap-closer and "
                      "opener.", "slip_the_veil <target>"),
    'poison': ("Apply a deadly poison to your blade so strikes inflict damage over "
               "time. Coat up before a fight.", "poison [weapon]"),
    # --- the marquee abilities, each earned through its class's quest (marquee.py) ---
    'unbroken_banner': ("Marquee. Plant a war banner: foes beside you reel and every foe turns "
                        "on you; for five rounds you and your allies deal a quarter more, shake "
                        "off stuns and fear and mend. Three-minute cooldown.", "unbroken banner"),
    'singularity': ("Marquee. Tear a hole in the world: every foe is dragged to one point "
                    "and crushed there for two rounds, then it implodes and leaves them "
                    "slowed. Bosses only stagger. Three-minute cooldown.", "singularity [target]"),
    'seraphs_vigil': ("Marquee. Call down a seraph for six rounds: each round it heals whoever "
                      "beside you is most wounded, and while it stands each of you survives one "
                      "killing blow. Three-minute cooldown.", "seraphs vigil"),
    'wings_of_dawn': ("Marquee. Rise on wings of light and crash down: radiant damage to every "
                      "foe within six metres, a quarter of their health back to every ally "
                      "beside you and a shield of light on each. Three-minute cooldown.", "wings of dawn"),
    'lich_ascension': ("Marquee. Six rounds as a lich: spells cost half, soul bolts split to a "
                       "second foe, a quarter of what you deal drains back to you, and death is "
                       "turned away once. Three-minute cooldown.", "lich ascension"),
    'heist': ("Marquee. The Heist of Ages: gone in smoke and behind every foe at once — each is "
              "struck from behind and relieved of half the gold it carries, and your next three "
              "swings land as criticals. Three-minute cooldown.", "heist"),
    'heartseeker': ("Marquee. Draw for a breath, then loose one arrow through every foe on its "
                    "line: a deep wound, a mark that makes them take a fifth more for four rounds, "
                    "and two rounds held where they stand. Three-minute cooldown.", "heartseeker [target]"),
    'song_of_the_ages': ("Marquee. Five rounds of the Song of the Ages: your allies' abilities come "
                         "back twice as fast and they deal and heal a fifth more; your foes slow, and "
                         "the last note stuns them. Three-minute cooldown.", "song of the ages"),
    'thousand_shadows': ("Marquee. Your shadow splits into a thousand: for three rounds they strike "
                         "every foe around you, and the last of them finishes the weakest (a boss "
                         "takes a heavier blow instead). Three-minute cooldown.", "thousand shadows"),
}


# ---------------------------------------------------------------------------
# Skill entry generation
# ---------------------------------------------------------------------------

def _gen_skill_entry(key, owners):
    classes = owners.get(key, [])
    prose, syntax = SKILL_PROSE.get(key, (None, None))
    name = key.replace('_', ' ').title()
    if not prose:
        prose = (f"A {name} ability. Use it in combat or exploration as your "
                 f"situation calls for.")
    if not syntax:
        syntax = key.replace('_', ' ')
    parts = [prose, "", "HOW TO USE: " + syntax]
    if len(classes) == 1 and classes[0] in CLASS_RESOURCE:
        parts.append("RESOURCE: " + CLASS_RESOURCE[classes[0]])
    parts.append("")
    parts.append("It grows as you use it, up to 85%; your guild's trainer teaches the rest.")
    return {
        'category': 'skill',
        'title': name,
        'syntax': syntax,
        'classes': [c.title() for c in classes] or ['Various'],
        'description': "\n".join(parts),
    }


# ---------------------------------------------------------------------------
# Talent tree entry generation (per-tree + per-class + overview)
# ---------------------------------------------------------------------------

# How many points must already be spent in a tree to reach each tier.
_TIER_REQ = {1: 0, 2: 5, 3: 10, 4: 15, 5: 20}


def _gen_talent_entries():
    entries = {}
    try:
        from talents import CLASS_TALENT_TREES, TREE_IDENTITY_PASSIVES
    except Exception:
        return entries

    for cls, trees in CLASS_TALENT_TREES.items():
        tree_titles = []
        for tree in trees:
            tname = tree['name']
            tree_titles.append(tname)
            lines = [tree.get('description', ''), ""]
            # group talents by tier
            by_tier = {}
            for t in tree['talents'].values():
                by_tier.setdefault(t.tier, []).append(t)
            for tier in sorted(by_tier):
                req = _TIER_REQ.get(tier, (tier - 1) * 5)
                lines.append(f"--- Tier {tier} (needs {req} points in tree) ---")
                for t in sorted(by_tier[tier], key=lambda x: x.name):
                    rank = f" [max rank {t.max_rank}]" if t.max_rank > 1 else ""
                    lines.append(f"  {t.name}{rank}")
                    lines.append(f"    {t.description}")
                    if t.requires:
                        lines.append(f"    Requires: {', '.join(t.requires)}")
                lines.append("")
            # identity passive
            ident = (TREE_IDENTITY_PASSIVES.get(cls, {}) or {}).get(tname)
            if ident:
                lines.append(f"IDENTITY: spend 25+ points here to unlock this tree's "
                             f"signature passive.")
            lines.append("")
            lines.append(f"Spend points with 'talent <name>'. See HELP TALENTS for the "
                         f"system overview.")
            key = tname.lower().replace(' ', '_').replace("'", "")
            entries[key] = {
                'category': 'talent',
                'title': f"{tname} ({cls.title()} Talent Tree)",
                'syntax': "talent <talent name>",
                'description': "\n".join(lines),
            }
        # per-class talent overview, e.g. 'mage talents'
        ov = [f"The {cls.title()} has three talent trees. Specialize by pouring points "
              f"into one, or hybridize across them:", ""]
        for tree in trees:
            ov.append(f"  {tree['name']} — {tree.get('description', '')}")
            ov.append(f"      (HELP {tree['name'].upper()})")
        ov.append("")
        ov.append("You earn 1 talent point per level from level 5 on. Reaching 25 "
                  "points in a single tree unlocks its identity passive.")
        ov.append("See HELP TALENTS for full rules. Spend with 'talent <name>'; review "
                  "with 'talents'.")
        entries[f"{cls}_talents"] = {
            'category': 'talent',
            'title': f"{cls.title()} Talent Trees",
            'syntax': "talents",
            'description': "\n".join(ov),
        }

    # general overview
    entries['talents'] = {
        'category': 'talent',
        'title': 'Talents',
        'syntax': "talents  |  talent <name>  |  untalent",
        'description': (
            "Talents let you customize your class beyond its baseline abilities.\n\n"
            "EARNING POINTS:\n"
            "  - You gain 1 talent point per level starting at level 5.\n"
            "  - Spend them with 'talent <talent name>'.\n"
            "  - Review your trees and spent points with 'talents'.\n\n"
            "TREES & TIERS:\n"
            "  - Each class has three trees (warriors use Martial Doctrines instead).\n"
            "  - Higher tiers unlock as you invest more points in that tree:\n"
            "    Tier 1 (0 pts), 2 (5), 3 (10), 4 (15), 5 (20).\n"
            "  - Many talents have multiple ranks — point in them repeatedly.\n\n"
            "IDENTITY PASSIVES:\n"
            "  - Reach 25 points in one tree to unlock its signature identity passive,\n"
            "    a powerful capstone that defines your specialization.\n\n"
            "RESPEC:\n"
            "  - You can reset and re-spend your points (see 'untalent' / your\n"
            "    guildmaster) to try a different build.\n\n"
            "Type 'help <tree name>' (e.g. HELP EMBERWEAVE) for a full talent list."
        ),
    }
    return entries


# ---------------------------------------------------------------------------
# Legacy redirects: old WoW-derived names point at their reforged versions so
# muscle memory and old guides still find the right help.
# ---------------------------------------------------------------------------

_LEGACY_SPELL_REDIRECT = {
    'death_grip': ('mistgrasp', 'Mistgrasp'),
    'death_coil': ('wraithfire', 'Wraithfire'),
    'plague_strike': ('mistrot', 'Mistrot'),
    'prayer_of_mending': ('travelling_grace', 'Travelling Grace'),
    'lightwell': ('font_of_the_vigil', 'Font of the Vigil'),
    'consecration': ('hallowed_ground', 'Hallowed Ground'),
    'crusaders_judgment': ('verdict_of_the_order', 'Verdict of the Order'),
    'hymn_of_hope': ('refrain_of_hope', 'Refrain of Hope'),
    'icy_veins': ('rimeheart', 'Rimeheart'),
    'combustion_master': ('kindling_focus', 'Kindling Focus'),
    'mass_dispel': ('cleansing_rite', 'Cleansing Rite'),
    'time_warp': ('quicken', 'Quicken'),
    'vampiric_touch': ('leechcraft', 'Leechcraft'),
    'avenging_wrath_master': ('ascendant_hour', 'Ascendant Hour'),
    'hammer_of_justice': ('dawnhammer', 'Dawnhammer'),
    'spell_reflection': ('mirrorward', 'Mirrorward'),
    'arcane_explosion': ('resonance_burst', 'Resonance Burst'),
}

_LEGACY_SKILL_REDIRECT = {
    'aimed_shot': ('truesight_shot', 'Truesight Shot'),
    'kill_command': ('wildbond_strike', 'Wildbond Strike'),
    'rapid_fire': ('loosing_storm', 'Loosing Storm'),
    'hunters_mark': ('quarry_mark', 'Quarry Mark'),
    'arcane_barrage': ('charge_release', 'Charge Release'),
    'arcane_blast': ('towerbolt', 'Towerbolt'),
    'evocation': ('drink_the_leyline', 'Drink the Leyline'),
    'shadow_step': ('slip_the_veil', 'Slip the Veil'),
    'shadowstep': ('slip_the_veil', 'Slip the Veil'),
    'vanish': ('fade', 'Fade'),
    'holy_fire': ('pyre_of_faith', 'Pyre of Faith'),
    'templars_verdict': ('order_verdict', 'Verdict of the Order'),
    'word_of_glory': ('absolution', 'Absolution'),
    'divine_storm': ('halo_of_reckoning', 'Halo of Reckoning'),
    'smite': ('censure', 'Censure'),
    'drain_soul': ('soul_siphon', 'Soul Siphon'),
    'avatar_of_war': ('war_incarnate', 'War Incarnate'),
}


def _redirect_entry(new_key, new_title, kind):
    return {
        'category': kind,
        'title': new_title,
        'syntax': f"help {new_key}",
        'description': (f"This {kind} has been reforged for Misthollow and is now "
                        f"called {new_title}.\n\nSee HELP {new_key.upper()} for full "
                        f"details on how to use it."),
    }


# ---------------------------------------------------------------------------
# Assembler
# ---------------------------------------------------------------------------

def build_ability_help():
    """Return {topic: entry} for every spell, skill, and talent tree."""
    entries = {}

    # spells
    try:
        from spells import SPELLS
        spell_owners = _spell_owners()
        for key, data in SPELLS.items():
            entries[key] = _gen_spell_entry(key, data, spell_owners)
    except Exception:
        pass

    # skills (don't clobber a same-named spell topic)
    skill_owners = _skill_owners()
    for key in skill_owners:
        if key in entries:
            continue
        entries[key] = _gen_skill_entry(key, skill_owners)

    # talents
    entries.update(_gen_talent_entries())

    # legacy redirects (only if the new target actually exists)
    for old, (new, title) in _LEGACY_SPELL_REDIRECT.items():
        if new in entries:
            entries[old] = _redirect_entry(new, title, 'spell')
    for old, (new, title) in _LEGACY_SKILL_REDIRECT.items():
        if new in entries:
            entries[old] = _redirect_entry(new, title, 'skill')

    return entries
