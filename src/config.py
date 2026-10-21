"""
Misthollow Configuration
=======================
Game settings and constants.
"""

import os

class Config:
    """Game configuration settings."""
    
    # Server Settings
    PORT = 4000
    HOST = '0.0.0.0'
    MAX_PLAYERS = 100
    TICKS_PER_SECOND = 10
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    WORLD_DIR = os.path.join(BASE_DIR, 'world')
    PLAYER_DIR = os.path.join(BASE_DIR, 'lib', 'players')
    LOG_DIR = os.path.join(BASE_DIR, 'log')

    # Web map settings
    MAP_PORT = 4001
    MAP_HOST = '0.0.0.0'
    MAP_PUBLIC_HOST = '72.35.132.11'
    MAP_VIEW_SIZE = 11

    # Admin dashboard: this machine only unless the owner opts in (set MISTHOLLOW_ADMIN_HOST,
    # e.g. to 0.0.0.0). Its API always needs the admin token: see README, "Admin dashboard".
    ADMIN_DASHBOARD_PORT = 4002
    ADMIN_DASHBOARD_HOST = os.environ.get('MISTHOLLOW_ADMIN_HOST', '127.0.0.1')
    
    # Game Settings
    STARTING_ROOM = 3001  # Temple of Garathorm equivalent
    VOID_ROOM = 1  # Limbo
    MORTAL_START_ROOM = 3001
    IMMORTAL_START_ROOM = 1200
    
    # Level Settings
    MAX_MORTAL_LEVEL = 60
    MAX_IMMORTAL_LEVEL = 70
    IMMORTAL_LEVEL = 61
    
    # High-level XP multiplier (levels 31-60 use slower progression)
    HIGH_LEVEL_EXP_MULTIPLIER = 1.6
    HIGH_LEVEL_THRESHOLD = 30

    # Email / password reset (SMTP)
    SMTP_HOST = None
    SMTP_PORT = 587
    SMTP_USER = None
    SMTP_PASS = None
    SMTP_FROM = None
    SMTP_TLS = True
    PASSWORD_RESET_TTL_HOURS = 24
    
    # Combat Settings
    PULSE_VIOLENCE = 2  # (unused; see COMBAT_ROUND_SECONDS)
    # Combat v2 (3D client): a round every 3 s (was 4 s "for readability" — the 3D client
    # now makes a round readable with animation). Heroes strike at the start of a round,
    # creatures NPC_PHASE_DELAY (combat_range.py) later, so blows alternate. Windows that
    # used to be hard-coded for 4 s scale with this.
    COMBAT_ROUND_SECONDS = 3.0
    BRAIN = True                 # mob brains (src/brain/); False (or MH_BRAIN=0) runs the old rules alone
    # Real-time combat for the 3D client (action_combat.py): a /play player who asks for it
    # swings on their own 3-s clock (first blow on the key press), skills behind a 1-s global
    # cooldown, creatures on staggered clocks with 2-s wind-ups. False: everyone fights in rounds.
    ACTION_COMBAT = True
    PULSE_MOBILE = 10  # seconds between mob actions

    # Combat stance modifiers (offense vs defense tradeoff)
    STANCE_MODIFIERS = {
        # Pass 2 tuning targets:
        # - Aggressive assassins should land meaningfully more (OB up) but feel squishier (DB/PB down)
        # - Defensive tanks should mitigate noticeably more (PB up) while losing some kill pressure (OB down)
        'aggressive': {'hit': 4, 'dam': 4, 'ac': 12, 'db': -6, 'pb': -8},
        'normal': {'hit': 0, 'dam': 0, 'ac': 0, 'db': 0, 'pb': 0},
        'defensive': {'hit': -3, 'dam': -2, 'ac': -12, 'db': 6, 'pb': 10},
    }

    # DB/PB weight handling
    ARMOR_WEIGHT_DB_SOFTCAP = 20
    ARMOR_WEIGHT_PB_SOFTCAP = 24

    # DB contribution caps (pass 2)
    DB_CAP_SHIELD_MAGIC = 12
    DB_CAP_DODGE_SKILL = 20
    DB_CAP_DODGE_ITEM = 15
    DB_CAP_STANCE = 8
    DB_CAP_WEIGHT_PENALTY = 30

    # PB contribution caps (pass 2)
    PB_CAP_STANCE = 12
    PB_CAP_PARRY = 15
    PB_CAP_SHIELD_BLOCK = 10
    PB_CAP_WEIGHT_PENALTY = 20

    # Movement economy (combat/escape)
    COMBAT_MOVE_COST = 1
    FLEE_MOVE_COST = 10
    ESCAPE_MOVE_COST = 12
    DISENGAGE_MOVE_COST = 6
    COMBAT_FATIGUE_HIT_PENALTY = 2
    COMBAT_FATIGUE_DAMAGE_PENALTY = 0.10

    # Fight pacing (gauntlet playability-01). Mob DATA stays untouched; these
    # rules shape how a fight feels: a level-appropriate duel lasts 8-20
    # rounds, mob burst is telegraphed rather than random, and staggers are
    # reachable. All applied in combat.py / mob_ai.py.
    PLAYER_LEVEL_HIT_DIV = 3              # players add level//3 to their hit roll
    PLAYER_DAMAGE_MULT_PER_LEVEL = 0.22   # weapon dice x (1 + level * this)
    PLAYER_DAMAGE_FLAT_PER_LEVEL = 0.6    # ...plus level*0.6 flat (keeps low rolls from stalling a fight)
    PLAYER_TOUGHNESS_PER_LEVEL = 0.0185   # damage reduction vs NPC hits per level
    PLAYER_TOUGHNESS_CAP = 0.60
    MOB_CRIT_CHANCE = 5                   # NPC random crits are rare: burst comes from wind-ups
    MOB_WINDUP_AUTOATTACK_MULT = 0.5      # a mob gathering a heavy swings lighter that round
    BOSS_SWING_CAP_PCT = 0.10             # no single player swing takes >10% of a boss's HP
    HEAVY_BLOW_MULT = 2.2                 # crushing blow = 2.2x a full average hit
    SWEEP_BLOW_MULT = 1.7
    HEAVY_STUN_CHANCE = 15                # % chance an unbraced crushing blow also stuns
    POISE_BASE = 3                        # stagger budget: POISE_BASE + level//POISE_LEVEL_DIV hits
    POISE_LEVEL_DIV = 8
    POISE_HEAVY_HIT_PCT = 0.08            # a hit >= 8% of max HP (or a crit) chips double poise
    LOW_HP_WARN_PCT = 0.25                # one warning per fight when HP first drops below this
    WINDUP_FIRST_ROUND_CHANCE = 100       # opening wind-up is guaranteed
    WINDUP_CHANCE = 75                    # per-round chance once the cooldown is up
    WINDUP_COOLDOWN_MIN = 10              # seconds from declaration to next eligible declaration
    WINDUP_COOLDOWN_MAX = 14              #   (resolution is +4s, so ~every 3-4 rounds)

    FLEE_COOLDOWN_SECONDS = 6
    ESCAPE_COOLDOWN_SECONDS = 8
    DISENGAGE_COOLDOWN_SECONDS = 6
    RESCUE_COOLDOWN_SECONDS = 6
    PROTECT_INTERCEPT_COOLDOWN_SECONDS = 4

    # Second Wind (mobility recovery)
    SECOND_WIND_COOLDOWN_SECONDS = 60
    SECOND_WIND_RESTORE_PCT = 0.25
    SECOND_WIND_BUFF_SECONDS = 30
    SECOND_WIND_REGEN_BONUS = 0.5

    # Briskness (mobility surge)
    BRISKNESS_INSTANT_PCT = 0.20
    BRISKNESS_REGEN_BONUS = 0.35
    BRISKNESS_DURATION_TICKS = 18
    BRISKNESS_WILDERNESS_BONUS = 0.20

    # Absorption shields (spells._scale_absorb_value). 2 a level, not 4: at 4 a level-45 mage's
    # stoneskin and armour ward held 369 against 191 health, so elites never got through
    ABSORB_LEVEL_BONUS = 2
    ABSORB_PROF_SCALING = 0.5
    ABSORB_ARMOR_SOFTCAP = 20
    ABSORB_ARMOR_PENALTY_PER_WEIGHT = 0.02
    ABSORB_ARMOR_MAX_PENALTY = 0.40
    ABSORB_MAGIC_TYPES = {'magic', 'fire', 'cold', 'lightning', 'acid', 'arcane', 'holy', 'shadow',
                          # a spell's school (combat_range.spell_school): every school a ward absorbs
                          'frost', 'necrotic', 'poison', 'nature', 'sound', 'disease'}

    # Going out on the water takes a boat or a raft, and creatures keep off it unless they live
    # there. On since the world was re-laid on the atlas: every place that matters is checked to
    # be reachable with a raft bought on the way (tests/test_world_atlas.py).
    WATER_NEEDS_BOAT = True

    # Shield-style evasion bonuses
    SHIELD_EVASION_BONUSES = {
        'shielded': 4,
        'holy_shield': 6,
        'divine_shield': 6,
        'aegis_ward': 4,
    }
    
    # Character Creation
    STARTING_GOLD = 100
    STARTING_EXPERIENCE = 0
    
    # Stat Limits
    MAX_STAT = 25
    MIN_STAT = 3
    
    # Experience multipliers by level
    EXP_MULTIPLIER = 1.4
    BASE_EXP = 800

    # Bonus XP settings
    EXPLORATION_XP_BASE = 40
    EXPLORATION_XP_PER_LEVEL = 5
    QUEST_XP_BONUS_PERCENT = 0.05  # 5% of next level XP
    BOSS_XP_BONUS_PERCENT = 0.50   # 50% bonus for boss kills
    STREAK_XP_BONUS_PER_KILL = 0.02  # 2% per streak stack
    STREAK_XP_BONUS_CAP = 0.30       # 30% cap

    # Rested XP settings
    RESTED_XP_RATE = 0.02  # 2% of next level XP per hour offline
    RESTED_XP_CAP = 0.50   # 50% of next level XP

    # Travel settings
    TRAVEL_COOLDOWN_SECONDS = 60
    
    # Regeneration rates (per tick)
    # Base regen rates (% of max per 60s tick) - multiplied by position
    # Standing=1x, Sitting=1.25x, Resting=1.5x, Sleeping=2x, Fighting=0.5x
    HP_REGEN_RATE = 0.12      # 12% base → 24% sleeping
    MANA_REGEN_RATE = 0.15    # 15% base → 30% sleeping  
    MOVE_REGEN_RATE = 0.20    # 20% base → 40% sleeping

    # Tick intervals (seconds)
    AFFECT_TICK_SECONDS = 6    # DOT/HOT effects tick rate
    POISON_TICK_SECONDS = 3    # Poison tick rate (faster feedback)
    
    # Colors (ANSI)
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'black': '\033[30m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'bright_black': '\033[90m',  # Dark gray
        'bright_red': '\033[91m',
        'bright_green': '\033[92m',
        'bright_yellow': '\033[93m',
        'bright_blue': '\033[94m',
        'bright_magenta': '\033[95m',
        'bright_cyan': '\033[96m',
        'bright_white': '\033[97m',
    }
    
    # Race definitions
    RACES = {
        'human': {
            'perception_bonus': 1,
            'name': 'Human',
            'description': 'Versatile and adaptable, humans excel in all professions.',
            'stat_mods': {'str': 0, 'int': 0, 'wis': 0, 'dex': 0, 'con': 0, 'cha': 1},
            'size': 'medium',
            'abilities': ['quick_learner'],
        },
        'elf': {
            'perception_bonus': 2,
            'name': 'Elf',
            'description': 'Graceful and wise, elves are masters of magic and archery.',
            'stat_mods': {'str': -1, 'int': 2, 'wis': 1, 'dex': 2, 'con': -2, 'cha': 1},
            'size': 'medium',
            'abilities': ['infravision', 'resist_charm'],
        },
        'dwarf': {
            'perception_bonus': 1,
            'name': 'Dwarf',
            'description': 'Stout and hardy, dwarves are renowned warriors and craftsmen.',
            'stat_mods': {'str': 1, 'int': -1, 'wis': 1, 'dex': -1, 'con': 3, 'cha': -1},
            'size': 'small',
            'abilities': ['infravision', 'resist_poison', 'resist_magic'],
        },
        'halfling': {
            'perception_bonus': 2,
            'name': 'Halfling',
            'description': 'Small and nimble, halflings are excellent thieves and scouts.',
            'stat_mods': {'str': -2, 'int': 0, 'wis': 0, 'dex': 3, 'con': 0, 'cha': 1},
            'size': 'small',
            'abilities': ['sneak_bonus', 'resist_fear'],
        },
        'half_orc': {
            'perception_bonus': 0,
            'name': 'Half-Orc',
            'description': 'Strong and fierce, half-orcs are formidable warriors.',
            'stat_mods': {'str': 3, 'int': -2, 'wis': -1, 'dex': 0, 'con': 2, 'cha': -2},
            'size': 'medium',
            'abilities': ['infravision', 'berserk'],
        },
        'gnome': {
            'perception_bonus': 2,
            'name': 'Gnome',
            'description': 'Clever and curious, gnomes have an affinity for illusion magic.',
            'stat_mods': {'str': -2, 'int': 2, 'wis': 0, 'dex': 1, 'con': 0, 'cha': 0},
            'size': 'small',
            'abilities': ['infravision', 'illusion_bonus'],
        },
        'dark_elf': {
            'name': 'Dark Elf',
            'description': 'Mysterious and deadly, dark elves wield shadow magic.',
            'stat_mods': {'str': 0, 'int': 2, 'wis': 0, 'dex': 2, 'con': -1, 'cha': -1},
            'size': 'medium',
            'abilities': ['infravision', 'faerie_fire', 'light_sensitivity'],
        },
    }
    
    # Class definitions
    CLASSES = {
        'warrior': {
            'name': 'Warrior',
            'description': 'Masters of combat, warriors excel in melee and defense.',
            'prime_stat': 'str',
            'hit_dice': 12,
            'mana_dice': 2,
            'move_dice': 6,
            'thac0_progression': 'fast',
            'save_progression': 'warrior',
            'skills': ['strike', 'bash', 'cleave', 'charge', 'rally', 'execute', 'heroic_throw',
                      'doctrine', 'swear', 'evolve',
                      'kick', 'rescue', 'second_attack', 'third_attack', 'parry', 'shield_block', 'dodge',
                      # level 31-60 (56 and 60 are reached through prestige)
                      'rallying_cry', 'shattering_blow', 'commanding_shout', 'heroic_leap', 'warpath', 'titans_wrath',
                      # the marquee ability: earned through the warrior's quest (marquee.py)
                      'unbroken_banner'],
            'spells': [],
            # Warriors also gain rage abilities: execute (15), rampage (20), warcry (10), ignorepain (8)
            # And can switch stances: battle, berserk, defensive, precision
            # Level 31-60: rallying_cry (32), shattering_blow (38), commanding_shout (44),
            #              heroic_leap (50), warpath (56), titans_wrath (60)
        },
        'mage': {
            'name': 'Mage',
            'description': 'Wielders of arcane power, mages command devastating spells.',
            'prime_stat': 'int',
            'hit_dice': 4,
            'mana_dice': 12,
            'move_dice': 4,
            'thac0_progression': 'slow',
            'save_progression': 'mage',
            'skills': ['scribe', 'charge_release', 'drink_the_leyline', 'towerbolt', 'dodge', 'singularity'],
            'spells': ['magic_missile', 'burning_hands', 'chill_touch', 'fireball', 'lightning_bolt',
                      'sleep', 'color_spray', 'teleport', 'fly', 'invisibility', 'detect_magic',
                      'identify', 'enchant_weapon', 'meteor_swarm', 'chain_lightning', 'block_door',
                      # Defensive spells
                      'armor', 'shield', 'stoneskin', 'tower_echoes', 'phase_step', 'mana_shield',
                      'ice_armor', 'fire_shield', 'mirrorward', 'stepwise',
                      'protection_from_evil', 'protection_from_good',
                      # Level 31-60 spells
                      'quicken', 'resonance_burst', 'rimeheart', 'kindling_focus', 'meteor_storm'],
            # Level 31-60: mana_shield (32), time_warp (38), arcane_explosion (44),
            #              icy_veins (50), combustion_master (56), meteor_storm (60)
        },
        'cleric': {
            'name': 'Cleric',
            'description': 'Divine servants who heal allies and smite the undead.',
            'prime_stat': 'wis',
            'hit_dice': 8,
            'mana_dice': 8,
            'move_dice': 4,
            'thac0_progression': 'medium',
            'save_progression': 'cleric',
            'skills': ['turn_undead', 'holy_smite', 'dodge', 'divine_word',
                      'pyre_of_faith', 'divine_intervention', 'seraphs_vigil'],
            'spells': ['cure_light', 'cure_serious', 'cure_critical', 'heal', 'group_heal',
                      'bless', 'armor', 'sanctuary', 'remove_curse', 'remove_poison',
                      'create_food', 'create_water', 'summon', 'word_of_recall', 'resurrect',
                      'harm', 'dispel_evil', 'earthquake', 'flamestrike', 'break_door',
                      # Defensive spells
                      'shield_of_faith', 'divine_shield', 'barkskin', 'righteous_fury',
                      'divine_protection', 'aegis', 'holy_aura', 'protection_from_evil',
                      # Level 31-60 spells
                      'travelling_grace', 'shared_burden', 'cleansing_rite', 'font_of_the_vigil',
                      'serenity', 'divine_intervention'],
            # Clerics build Divine Favor through healing/turning undead, spend on holy_smite
            # Level 31-60: prayer_of_mending (32), spirit_link (38), mass_dispel (44),
            #              lightwell (50), serenity (56), divine_intervention (60)
        },
        'thief': {
            'name': 'Thief',
            'description': 'Cunning rogues who strike from the shadows.',
            'prime_stat': 'dex',
            'hit_dice': 6,
            'mana_dice': 2,
            'move_dice': 8,
            'thac0_progression': 'medium',
            'save_progression': 'thief',
            'skills': ['backstab', 'sneak', 'hide', 'steal', 'pick_lock', 'detect_traps', 'cover_tracks',
                      'second_attack', 'dodge', 'evasion', 'pocket_sand', 'low_blow', 'knife_toss',
                      'rigged_dice', 'jackpot', 'circle', 'trip', 'caltrops',
                      # level 31-60 (56 and 60 are reached through prestige)
                      'nerve_strike', 'garrote', 'marked_for_death_thief', 'perfect_crime', 'heist'],
            'spells': [],
            # Thieves use combo points: backstab/attacks build points, finishers spend them
            # Finishers: eviscerate (1+), kidney_shot (4+), slice_dice (3+)
            # Level 31-60: nerve_strike (32), shadow_dance (38), garrote (44),
            #              evasion_master (50), marked_for_death_thief (56), perfect_crime (60)
        },
        'ranger': {
            'name': 'Ranger',
            'description': 'Wilderness warriors who blend combat prowess with nature magic.',
            'prime_stat': 'dex',
            'hit_dice': 10,
            'mana_dice': 4,
            'move_dice': 8,
            'thac0_progression': 'fast',
            'save_progression': 'warrior',
            # progression-01: a new character learns the first THREE skills, so the
            # class's button-3 attack must sit among them (a level-1 ranger had track,
            # sneak and hide — no way to fight but the sword)
            'skills': ['truesight_shot', 'track', 'sneak', 'hide', 'second_attack', 'dual_wield', 'dodge', 'scan',
                      'wildbond_strike', 'loosing_storm', 'quarry_mark', 'tame',
                      'snare',
                      # level 31-60 (56 and 60 are reached through prestige)
                      'volley', 'camouflage_master', 'serpent_sting', 'alpha_pack', 'heartseeker'],
            'spells': ['cure_light', 'detect_magic', 'faerie_fire', 'call_lightning',
                      'barkskin', 'entangle', 'briskness'],
            # Rangers can tame animal companions: wolf, bear, hawk, cat, boar
            # Level 31-60: volley (32), camouflage_master (38), serpent_sting (44),
            #              rapid_fire (50), kill_command (56), alpha_pack (60)
        },
        'paladin': {
            'name': 'Paladin',
            'description': 'Holy warriors who combine martial skill with divine power.',
            'prime_stat': 'str',
            'hit_dice': 10,
            'mana_dice': 4,
            'move_dice': 4,
            'thac0_progression': 'fast',
            'save_progression': 'warrior',
            'skills': ['censure', 'rescue', 'bash', 'turn_undead', 'second_attack',
                      'oath', 'order_verdict', 'absolution', 'halo_of_reckoning',
                      'dodge', 'parry', 'shield_block', 'wings_of_dawn'],   # censure first: it is the paladin's button 3
            'spells': ['cure_light', 'cure_serious', 'bless', 'detect_evil', 'protection_from_evil',
                      'shield_of_faith', 'divine_shield',
                      # Level 31-60 spells
                      'unfettered', 'hallowed_ground', 'dawnhammer',
                      'ascendant_hour', 'divine_shield_master', 'verdict_of_the_order'],
            # Paladins use auras (devotion, protection, retribution) and lay_hands ability
            # Level 31-60: hand_of_freedom (32), consecration (38), hammer_of_justice (44),
            #              avenging_wrath_master (50), divine_shield_master (56), crusaders_judgment (60)
        },
        'necromancer': {
            'name': 'Necromancer',
            'description': 'Dark mages who command the forces of death and undeath.',
            'prime_stat': 'int',
            'hit_dice': 4,
            'mana_dice': 10,
            'move_dice': 4,
            'thac0_progression': 'slow',
            'save_progression': 'mage',
            'skills': ['soul_bolt', 'soul_siphon', 'bone_shield', 'soul_reap', 'lich_ascension'],
            'spells': ['chill_touch', 'animate_dead', 'leechcraft', 'enervation',
                      'mistgrasp', 'sever_cord', 'energy_drain',
                      'poison', 'weaken', 'blindness', 'fear', 'armor', 'shield',
                      'protection_from_good',
                      # Level 31-60 spells
                      'wraithfire', 'corpse_shield', 'mistrot', 'summon_gargoyle',
                      'soul_harvest', 'apocalypse_necro'],
            # Level 31-60: death_coil (32), corpse_shield (38), plague_strike (44),
            #              summon_gargoyle (50), soul_harvest (56), apocalypse_necro (60)
        },
        'bard': {
            'name': 'Bard',
            'description': 'Charismatic performers who inspire allies with magical songs.',
            'prime_stat': 'cha',
            'hit_dice': 6,
            'mana_dice': 6,
            'move_dice': 6,
            'thac0_progression': 'medium',
            'save_progression': 'thief',
            # progression-01: a level-1 bard with sneak, pick_lock and lore died ten
            # times on the newcomer ladder; mockery and fascinate are its fight
            'skills': ['mockery', 'fascinate', 'sneak', 'pick_lock', 'lore', 'countersong', 'dodge',
                      'crescendo', 'encore', 'magnum_opus', 'discordant_note', 'song_of_the_ages'],
            'spells': ['charm_person', 'sleep', 'invisibility', 'haste', 'slow',
                      'cure_light', 'detect_magic', 'heroism', 'fear', 'mass_charm',
                      'bless', 'armor',
                      # Level 31-60 spells
                      'refrain_of_hope', 'chord_of_disruption', 'epic_tale', 'siren_song',
                      'requiem', 'magnum_opus'],
            # Bards also learn songs automatically based on level (see BARD_SONGS in spells.py)
            # Level 31-60: hymn_of_hope (32), chord_of_disruption (38), epic_tale (44),
            #              siren_song (50), requiem (56), magnum_opus (60)
        },
        'assassin': {
            'name': 'Assassin',
            'description': 'Deadly killers who specialize in eliminating targets with lethal precision.',
            'prime_stat': 'dex',
            'hit_dice': 8,
            'mana_dice': 2,
            'move_dice': 10,
            'thac0_progression': 'fast',
            'save_progression': 'thief',
            'skills': ['backstab', 'mark', 'expose', 'vital', 'execute_contract',
                      'feint', 'evasion', 'fade', 'slip_the_veil',
                      'sneak', 'hide', 'cover_tracks', 'dual_wield', 'second_attack', 'dodge', 'poison',
                      # level 31-60 (56 and 60 are reached through prestige)
                      'shadowstrike', 'fan_of_knives', 'rupture', 'shadow_blades_master', 'vendetta_assassin', 'death_mark',
                      'thousand_shadows'],
            'spells': [],
            # Level 31-60: shadowstrike (32), fan_of_knives (38), rupture (44),
            #              shadow_blades_master (50), vendetta_assassin (56), death_mark (60)
        },
    }
    
    # Equipment slots
    WEAR_SLOTS = [
        'light',      # Light source
        'finger1',    # First ring
        'finger2',    # Second ring  
        'neck1',      # First neck slot
        'neck2',      # Second neck slot
        'body',       # Body armor
        'head',       # Helmet
        'legs',       # Leg armor
        'feet',       # Boots
        'hands',      # Gloves
        'arms',       # Arm guards
        'shield',     # Shield
        'about',      # Cloak/cape
        'waist',      # Belt
        'wrist1',     # First wrist
        'wrist2',     # Second wrist
        'wield',      # Main weapon
        'hold',       # Held item
        'dual_wield', # Off-hand weapon
    ]
    
    # Item types
    ITEM_TYPES = [
        'light', 'scroll', 'wand', 'staff', 'weapon', 'treasure', 'armor',
        'potion', 'worn', 'other', 'trash', 'container', 'note', 'drink',
        'key', 'food', 'money', 'boat', 'fountain', 'portal'
    ]
    
    # Weapon types
    WEAPON_TYPES = [
        'hit', 'sting', 'whip', 'slash', 'bite', 'bludgeon', 'crush',
        'pound', 'claw', 'maul', 'thrash', 'pierce', 'blast', 'punch',
        'stab', 'slice', 'cleave', 'smash'
    ]
    
    # Sector types (terrain)
    SECTOR_TYPES = {
        'inside': {'move_cost': 1, 'description': 'Indoors'},
        'city': {'move_cost': 1, 'description': 'City streets'},
        'field': {'move_cost': 1, 'description': 'Open field'},
        'forest': {'move_cost': 2, 'description': 'Dense forest'},
        'hills': {'move_cost': 2, 'description': 'Rolling hills'},
        'mountain': {'move_cost': 3, 'description': 'Steep mountains'},
        'water_swim': {'move_cost': 2, 'description': 'Shallow water'},
        'water_noswim': {'move_cost': 10, 'description': 'Deep water'},
        'underwater': {'move_cost': 3, 'description': 'Underwater'},
        'flying': {'move_cost': 1, 'description': 'Flying'},
        'desert': {'move_cost': 2, 'description': 'Arid desert'},
        'swamp': {'move_cost': 3, 'description': 'Murky swamp'},
        'dungeon': {'move_cost': 1, 'description': 'Dungeon corridor'},
    }

    # Terrain movement cost modifiers (scaffolding for future terrain-based rules)
    TERRAIN_MOVE_COST_MODIFIERS = {
        sector: 1.0 for sector in SECTOR_TYPES
    }
    
    # Position states
    POSITIONS = ['dead', 'mortally_wounded', 'incapacitated', 'stunned',
                 'sleeping', 'resting', 'sitting', 'fighting', 'standing']
    
    # Directions (cardinal only: n/s/e/w/u/d)
    DIRECTIONS = {
        'north': {'opposite': 'south', 'abbrev': 'n'},
        'east': {'opposite': 'west', 'abbrev': 'e'},
        'south': {'opposite': 'north', 'abbrev': 's'},
        'west': {'opposite': 'east', 'abbrev': 'w'},
        'up': {'opposite': 'down', 'abbrev': 'u'},
        'down': {'opposite': 'up', 'abbrev': 'd'},
    }

    # Poison Types for Envenom
    POISON_TYPES = {
        'venom': {
            'name': 'Deadly Venom',
            'description': 'A vial of deadly poison that causes damage over time',
            'effect': 'poison',
            'damage': 3,
            'duration': 8,
            'color': 'green',
            'hit_message': 'Your poisoned blade delivers venom!',
            'victim_message': 'You feel poison coursing through your veins!',
            'room_message': '{attacker} strikes {victim} with a poisoned blade!'
        },
        'neurotoxin': {
            'name': 'Blinding Neurotoxin',
            'description': 'A paralytic toxin that blinds the target',
            'effect': 'blind',
            'duration': 6,
            'color': 'yellow',
            'hit_message': 'Your neurotoxin strikes true!',
            'victim_message': 'You are blinded by the neurotoxin!',
            'room_message': '{attacker} blinds {victim} with a toxic strike!'
        },
        'viper_venom': {
            'name': 'Viper Venom',
            'description': 'Potent snake venom causing severe agony',
            'effect': 'extra_damage',
            'damage': 15,
            'color': 'red',
            'hit_message': 'Your viper venom burns through their flesh!',
            'victim_message': 'Excruciating pain shoots through your body!',
            'room_message': '{attacker}\'s viper venom causes {victim} to writhe in agony!'
        },
        'silencer': {
            'name': 'Silencing Toxin',
            'description': 'A magical poison that seals the vocal cords',
            'effect': 'silence',
            'duration': 5,
            'color': 'magenta',
            'hit_message': 'Your silencing toxin takes effect!',
            'victim_message': 'Your throat constricts! You cannot speak!',
            'room_message': '{attacker} strikes {victim} with a silencing toxin!'
        },
        'torpor': {
            'name': 'Torpor Poison',
            'description': 'A sedative poison that slows reactions',
            'effect': 'slow',
            'duration': 7,
            'penalty': -2,
            'color': 'blue',
            'hit_message': 'Your torpor poison slows their movements!',
            'victim_message': 'Your limbs feel sluggish and heavy!',
            'room_message': '{attacker}\'s poison slows {victim}\'s movements!'
        },
        'nightshade': {
            'name': 'Essence of Nightshade',
            'description': 'A dark essence that weakens the body',
            'effect': 'weaken',
            'duration': 6,
            'penalty': -3,
            'stat': 'str',
            'color': 'black',
            'hit_message': 'Nightshade essence saps their strength!',
            'victim_message': 'Your muscles feel weak and useless!',
            'room_message': '{attacker}\'s nightshade weakens {victim}!'
        },
        'hemotoxin': {
            'name': 'Crimson Hemotoxin',
            'description': 'A blood poison that causes severe internal bleeding',
            'effect': 'poison',
            'damage': 5,
            'duration': 6,
            'color': 'bright_red',
            'hit_message': 'Your hemotoxin causes internal bleeding!',
            'victim_message': 'You taste blood as the hemotoxin attacks your veins!',
            'room_message': '{attacker}\'s hemotoxin causes {victim} to bleed profusely!'
        }
    }

    # Ensure directories exist
    @classmethod
    def ensure_directories(cls):
        """Create required directories if they don't exist."""
        for directory in [cls.PLAYER_DIR, cls.LOG_DIR]:
            os.makedirs(directory, exist_ok=True)

# Create directories on import
Config.ensure_directories()