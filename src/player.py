"""
Misthollow Player
================
Player character class with stats, combat, inventory, etc.
"""

import json
import os
import hashlib
import random
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from world import World
    from room import Room

from config import Config
from affects import AffectManager
from regeneration import RegenerationCalculator

logger = logging.getLogger('Misthollow.Player')


# the looks a hero may choose beyond their class's own (gear_look.py `style`): the archmage is a mage's
LOOK_STYLES = {'archmage': ('mage',)}

class Character:
    """Base class for all characters (players and NPCs)."""
    
    def __init__(self):
        self.name = "Unknown"
        self.room = None
        self.hp = 100
        self.max_hp = 100
        self.mana = 100
        self.max_mana = 100
        self.move = 100
        self.max_move = 100
        
        # Stats
        self.str = 10
        self.int = 10
        self.wis = 10
        self.dex = 10
        self.con = 10
        self.cha = 10
        
        # Combat
        self.level = 1
        self.exp = 0
        self.gold = 0
        self.alignment = 0
        self.armor_class = 100
        self.hitroll = 0
        self.damroll = 0
        self.damage_reduction = 0  # % reduction from affects
        
        # State
        self.position = 'standing'
        self.fighting = None
        self.stance = 'normal'
        self.wimpy = 0
        self.flee_cooldown_until = 0
        self.escape_cooldown_until = 0
        self.disengage_cooldown_until = 0
        self.rescue_cooldown_until = 0
        self.protect_cooldown_until = 0
        self.protecting = None
        self.second_wind_until = 0
        self.second_wind_cooldown_until = 0
        
        # Equipment and inventory
        self.inventory = []
        self.equipment = {}

        # Affects
        self.affects = []
        self.affect_flags = set()  # Flags applied by affects (sanctuary, invisible, etc.)

    def get_armor_weight(self) -> int:
        """Total weight of equipped armor pieces (used for absorption penalties)."""
        total = 0
        for item in getattr(self, 'equipment', {}).values():
            if not item:
                continue
            if getattr(item, 'item_type', '') == 'armor':
                total += getattr(item, 'weight', 0)
        return total

    def get_shield_evasion_bonus(self) -> int:
        """Evasion bonus from shield-style magical effects."""
        try:
            bonuses = self.config.SHIELD_EVASION_BONUSES
        except Exception:
            from config import Config
            bonuses = Config.SHIELD_EVASION_BONUSES
        if not hasattr(self, 'affect_flags'):
            return 0
        return max((bonuses.get(flag, 0) for flag in self.affect_flags), default=0)

    def get_db_value(self) -> int:
        """Derived Dodge/Avoidance value (MUME-style DB analogue)."""
        base_db = 100 - self.get_armor_class()
        stance = getattr(self, 'stance', 'normal')
        stance_mods = self.config.STANCE_MODIFIERS.get(stance, self.config.STANCE_MODIFIERS['normal'])
        stance_db = int(stance_mods.get('db', 0))
        shield_magic = self.get_shield_evasion_bonus()
        dodge_skill = int(getattr(self, 'skills', {}).get('dodge', 0)) // 5
        dodge_item = self.get_equipment_bonus('dodge')
        wt = self.get_armor_weight()
        softcap = int(getattr(self.config, 'ARMOR_WEIGHT_DB_SOFTCAP', 20))
        weight_penalty = max(0, wt - softcap) // 2
        return base_db + stance_db + shield_magic + dodge_skill + dodge_item - weight_penalty

    def get_pb_value(self) -> int:
        """Derived Parry/Block mitigation value (MUME-style PB analogue)."""
        base_pb = int(getattr(self, 'damage_reduction', 0))
        stance = getattr(self, 'stance', 'normal')
        stance_mods = self.config.STANCE_MODIFIERS.get(stance, self.config.STANCE_MODIFIERS['normal'])
        stance_pb = int(stance_mods.get('pb', 0))
        parry_skill = int(getattr(self, 'skills', {}).get('parry', 0)) // 8
        shield_block = int(getattr(self, 'skills', {}).get('shield_block', 0)) // 10
        wt = self.get_armor_weight()
        softcap = int(getattr(self.config, 'ARMOR_WEIGHT_PB_SOFTCAP', 24))
        weight_penalty = max(0, wt - softcap) // 3
        pb = base_pb + stance_pb + parry_skill + shield_block - weight_penalty
        return max(0, min(80, pb))

    def get_db_breakdown(self) -> dict:
        """Return DB components for tactical/stat display."""
        base_db = 100 - self.get_armor_class()
        stance = getattr(self, 'stance', 'normal')
        stance_mods = self.config.STANCE_MODIFIERS.get(stance, self.config.STANCE_MODIFIERS['normal'])
        stance_db = int(stance_mods.get('db', 0))
        shield_magic = self.get_shield_evasion_bonus()
        dodge_skill = int(getattr(self, 'skills', {}).get('dodge', 0)) // 5
        dodge_item = self.get_equipment_bonus('dodge')

        # Cap per-source contribution so no single source dominates DB
        cap_shield = int(getattr(self.config, 'DB_CAP_SHIELD_MAGIC', 12))
        cap_dodge_skill = int(getattr(self.config, 'DB_CAP_DODGE_SKILL', 20))
        cap_dodge_item = int(getattr(self.config, 'DB_CAP_DODGE_ITEM', 15))
        cap_stance = int(getattr(self.config, 'DB_CAP_STANCE', 8))
        cap_weight = int(getattr(self.config, 'DB_CAP_WEIGHT_PENALTY', 30))

        shield_magic = max(-5, min(cap_shield, shield_magic))
        dodge_skill = max(0, min(cap_dodge_skill, dodge_skill))
        dodge_item = max(-8, min(cap_dodge_item, dodge_item))
        stance_db = max(-cap_stance, min(cap_stance, stance_db))

        wt = self.get_armor_weight()
        softcap = int(getattr(self.config, 'ARMOR_WEIGHT_DB_SOFTCAP', 20))
        weight_penalty = max(0, wt - softcap) // 2
        weight_penalty = min(cap_weight, weight_penalty)

        total = base_db + stance_db + shield_magic + dodge_skill + dodge_item - weight_penalty
        return {
            'total': total,
            'base': base_db,
            'stance': stance_db,
            'shield': shield_magic,
            'dodge_skill': dodge_skill,
            'dodge_item': dodge_item,
            'weight_penalty': weight_penalty,
        }

    def get_pb_breakdown(self) -> dict:
        """Return PB components for tactical/stat display."""
        base_pb = int(getattr(self, 'damage_reduction', 0))
        stance = getattr(self, 'stance', 'normal')
        stance_mods = self.config.STANCE_MODIFIERS.get(stance, self.config.STANCE_MODIFIERS['normal'])
        stance_pb = int(stance_mods.get('pb', 0))
        parry_skill = int(getattr(self, 'skills', {}).get('parry', 0)) // 8
        shield_block = int(getattr(self, 'skills', {}).get('shield_block', 0)) // 10

        # Cap per-source contribution so PB remains predictable
        cap_stance = int(getattr(self.config, 'PB_CAP_STANCE', 12))
        cap_parry = int(getattr(self.config, 'PB_CAP_PARRY', 15))
        cap_shield_block = int(getattr(self.config, 'PB_CAP_SHIELD_BLOCK', 10))
        cap_weight = int(getattr(self.config, 'PB_CAP_WEIGHT_PENALTY', 20))

        stance_pb = max(-cap_stance, min(cap_stance, stance_pb))
        parry_skill = max(0, min(cap_parry, parry_skill))
        shield_block = max(0, min(cap_shield_block, shield_block))

        wt = self.get_armor_weight()
        softcap = int(getattr(self.config, 'ARMOR_WEIGHT_PB_SOFTCAP', 24))
        weight_penalty = max(0, wt - softcap) // 3
        weight_penalty = min(cap_weight, weight_penalty)

        total = max(0, min(80, base_pb + stance_pb + parry_skill + shield_block - weight_penalty))
        return {
            'total': total,
            'base': base_pb,
            'stance': stance_pb,
            'parry': parry_skill,
            'shield_block': shield_block,
            'weight_penalty': weight_penalty,
        }

    @property
    def is_alive(self):
        return self.hp > 0
        
    @property
    def is_fighting(self):
        return self.fighting is not None

    @property
    def is_immortal(self) -> bool:
        """Check if this player has immortal/admin privileges."""
        if not self.account_name:
            return False
        try:
            from accounts import Account
            account = Account.load(self.account_name)
            return account and account.is_admin
        except Exception:
            return False
        
    def get_soulstone_bonus_int(self) -> int:
        """Return INT bonus from a held soulstone (if any)."""
        try:
            stone = self.equipment.get('hold') if hasattr(self, 'equipment') else None
            if stone and (getattr(stone, 'is_soulstone', False) or ('soulstone' in getattr(stone, 'flags', set()))):
                return int(getattr(stone, 'soulstone_bonus_int', 3))
        except Exception:
            pass
        return 0

    def get_paladin_auras(self) -> set:
        """Return active paladin auras affecting this character.
        
        Checks group members and other characters in the same room.
        """
        auras = set()
        try:
            chars_to_check = set()
            if self.room:
                chars_to_check.update(getattr(self.room, 'characters', []))
            # Also check group members in same room
            group = getattr(self, 'group', None)
            if group:
                for m in group.members:
                    if m.room == self.room:
                        chars_to_check.add(m)
            for char in chars_to_check:
                if hasattr(char, 'char_class') and str(char.char_class).lower() == 'paladin':
                    aura = getattr(char, 'active_aura', None)
                    if aura:
                        auras.add(aura)
        except Exception:
            pass
        return auras

    def get_hit_bonus(self):
        """Calculate total hit bonus (to hit / THAC0)."""
        bonus = self.hitroll
        
        # Equipment hitroll bonus
        bonus += self.get_equipment_bonus('hitroll')

        # DEX is primary factor for accuracy (dodging, precision)
        effective_dex = self.gear_stat('dex')
        bonus += (effective_dex - 10) // 2

        # STR provides minor bonus (raw power helping land blows)
        effective_str = self.gear_stat('str')
        bonus += (effective_str - 10) // 4

        # INT provides bonus for tactical awareness (mainly for casters)
        if hasattr(self, 'char_class'):
            if str(self.char_class).lower() in ('mage', 'necromancer', 'cleric'):
                effective_int = self.gear_stat('int') + self.get_soulstone_bonus_int()
                bonus += (effective_int - 10) // 3

        # Bard song bonuses
        if hasattr(self, 'song_bonuses') and self.song_bonuses:
            bonus += self.song_bonuses.get('hitroll', 0)
            bonus += self.song_bonuses.get('warcry_hitroll', 0)  # Warrior war cry

        # Bard song debuffs (for mobs)
        if hasattr(self, 'song_debuffs') and self.song_debuffs:
            bonus += self.song_debuffs.get('hitroll', 0)  # Negative value

        # Stance modifiers
        try:
            stance = getattr(self, 'stance', 'normal')
            stance_mods = self.config.STANCE_MODIFIERS.get(stance, self.config.STANCE_MODIFIERS['normal'])
            bonus += stance_mods.get('hit', 0)
        except Exception:
            pass

        # Talent bonuses
        try:
            from talents import TalentManager
            bonus += int(TalentManager.get_talent_bonus(self, 'stat_bonus', 'hit_chance'))
            # Ranged hit bonus when using bows/crossbows
            weapon = self.equipment.get('wield') if hasattr(self, 'equipment') else None
            if weapon and getattr(weapon, 'weapon_type', '') in ('bow', 'crossbow', 'ranged'):
                bonus += int(TalentManager.get_talent_bonus(self, 'stat_bonus', 'ranged_hit'))
        except Exception:
            pass

        return bonus

    def get_damage_bonus(self):
        """Calculate total damage bonus."""
        bonus = self.damroll
        
        # Equipment damroll bonus
        bonus += self.get_equipment_bonus('damroll')

        # STR is primary factor for damage
        effective_str = self.gear_stat('str')
        bonus += (effective_str - 10) // 2

        # DEX provides minor damage bonus (precision strikes for finesse classes)
        if hasattr(self, 'char_class'):
            if str(self.char_class).lower() in ('thief', 'assassin', 'ranger'):
                effective_dex = self.gear_stat('dex')
                bonus += (effective_dex - 10) // 5

        # Bard song bonuses
        if hasattr(self, 'song_bonuses') and self.song_bonuses:
            bonus += self.song_bonuses.get('damroll', 0)
            bonus += self.song_bonuses.get('warcry_damroll', 0)  # Warrior war cry

        # Bard song debuffs (for mobs)
        if hasattr(self, 'song_debuffs') and self.song_debuffs:
            bonus += self.song_debuffs.get('damroll', 0)  # Negative value

        # Mount combat bonus (war horse, nightmare)
        if hasattr(self, 'mount') and self.mount and hasattr(self.mount, 'damroll_bonus'):
            bonus += self.mount.damroll_bonus

        # Stance modifiers
        try:
            stance = getattr(self, 'stance', 'normal')
            stance_mods = self.config.STANCE_MODIFIERS.get(stance, self.config.STANCE_MODIFIERS['normal'])
            bonus += stance_mods.get('dam', 0)
        except Exception:
            pass

        return bonus
        
    def get_armor_class(self):
        """Calculate effective armor class."""
        ac = self.armor_class
        ac -= (self.dex - 10) // 2 * 10  # Dexterity bonus
        
        # Equipment bonuses
        for slot, item in self.equipment.items():
            if item and hasattr(item, 'armor'):
                ac -= item.armor
        
        # Stance modifiers
        try:
            stance = getattr(self, 'stance', 'normal')
            stance_mods = self.config.STANCE_MODIFIERS.get(stance, self.config.STANCE_MODIFIERS['normal'])
            ac += stance_mods.get('ac', 0)
        except Exception:
            pass

        # Paladin Devotion Aura (nearby allies)
        if 'devotion' in self.get_paladin_auras():
            ac -= 15
        
        # Equipment affect bonuses for armor
        ac += self.get_equipment_bonus('armor')
                
        return max(ac, -100)  # Cap at -100

    def get_equipment_bonus(self, stat: str) -> int:
        """Get total bonus for a stat from all equipped items + set bonuses."""
        bonus = 0
        for slot, item in getattr(self, 'equipment', {}).items():
            if item and hasattr(item, 'affects') and item.affects:
                for affect in item.affects:
                    if isinstance(affect, dict):
                        # Newer format: affects list with type/value
                        if affect.get('type') == stat:
                            bonus += affect.get('value', 0)
                        # Legacy format: modify_stat + applies_to
                        if affect.get('type') == 'modify_stat' and affect.get('applies_to') == stat:
                            bonus += affect.get('value', 0)
                    elif hasattr(affect, 'type') and hasattr(affect, 'applies_to'):
                        if affect.type == 'modify_stat' and affect.applies_to == stat:
                            bonus += getattr(affect, 'value', 0)
        # Add set bonuses
        bonus += self.get_set_bonus(stat)
        return bonus

    def get_set_bonus(self, stat: str) -> int:
        """Get set bonuses for a given stat."""
        try:
            from sets import get_set_bonus
        except Exception:
            return 0
        
        # Count equipped pieces by set_id
        set_counts = {}
        for slot, item in getattr(self, 'equipment', {}).items():
            if item and getattr(item, 'set_id', None):
                set_id = item.set_id
                if isinstance(set_id, str) and set_id.isdigit():
                    set_id = int(set_id)
                set_counts[set_id] = set_counts.get(set_id, 0) + 1
        
        total = 0
        for set_id, pieces in set_counts.items():
            # always-on bonuses
            bonuses = get_set_bonus(set_id, pieces, in_zone=False)
            total += bonuses.get(stat, 0)
            # in-zone bonuses
            if self.room and self.room.zone and getattr(self.room.zone, 'number', None) == set_id:
                bonuses_in = get_set_bonus(set_id, pieces, in_zone=True)
                total += bonuses_in.get(stat, 0)
        return total

    def gear_stat(self, stat: str) -> int:
        """An attribute with what worn gear adds to it. A creature's gear counts only where this
        is asked (its blows); a player's attributes count their gear everywhere (Player)."""
        return getattr(self, stat, 0) + self.get_equipment_bonus(stat)

    def get_effective_stat(self, stat: str) -> int:
        """Get effective stat value including equipment bonuses and debuffs."""
        total = self.gear_stat(stat)
        # Achievement stat bonuses
        try:
            from achievements import AchievementManager
            total += AchievementManager.get_stat_bonus(self, stat)
        except Exception:
            pass
        # Hunger debuff: -2 STR when starving
        if stat == 'str' and getattr(self, 'hunger', 168) <= 0:
            total -= 2
        # Thirst debuff: -2 DEX when parched
        if stat == 'dex' and getattr(self, 'thirst', 60) <= 0:
            total -= 2
        return total


# ---------------------------------------------------------------- what worn gear adds
# A player's attributes and maxima count their worn gear everywhere: `player.con` is their own
# constitution plus every worn piece's (and its set's), `player.max_hp` their own health plus
# their gear's. Their own (the base) is what is saved and what levels and spells move; gear adds
# only while it is worn. Items name a stat short or long ('con', 'constitution') and health, mana
# and moves by any of their names. A creature's attributes stay its own (Character.gear_stat).
GEAR_STATS = {
    'str': ('str', 'strength'), 'dex': ('dex', 'dexterity'), 'con': ('con', 'constitution'),
    'int': ('int', 'intelligence'), 'wis': ('wis', 'wisdom'), 'cha': ('cha', 'charisma'),
    'max_hp': ('hp', 'max_hp', 'hitpoints'), 'max_mana': ('mana', 'max_mana'), 'max_move': ('move', 'max_move'),
    # a percent chance to shrug off a spell's hold, and a percent off its damage (spells.py)
    'spell_resist': ('spell_resist', 'magic_resist'),
}

# What share of each kind of harm a player's gear (and sets) turns aside, by school
# (combat_range.spell_school's names; 'cold' is frost). Items name it '<kind>_resist'; a shadow
# ward also turns death magic. Never more than RESIST_CAP percent.
RESIST_KEYS = {
    'fire': ('fire_resist',), 'frost': ('cold_resist', 'frost_resist', 'ice_resist'),
    'lightning': ('lightning_resist', 'electric_resist', 'shock_resist'), 'poison': ('poison_resist', 'acid_resist'),
    'disease': ('disease_resist',), 'shadow': ('shadow_resist',), 'necrotic': ('necrotic_resist', 'shadow_resist'),
    'holy': ('holy_resist',), 'arcane': ('arcane_resist',), 'nature': ('nature_resist', 'earth_resist'), 'sound': ('sound_resist',),
}
# set bonuses named the old way: (what the game reads, by how much)
SET_STAT_AS = {'armor_class': ('armor', -5), 'curse_resist': ('spell_resist', 1)}
RESIST_ALIASES = {'cold': 'frost', 'ice': 'frost', 'electric': 'lightning', 'shock': 'lightning', 'acid': 'poison',
                  'plague': 'disease', 'earth': 'nature', 'negative': 'necrotic', 'death': 'necrotic', 'dark': 'shadow'}
RESIST_CAP = 75


def school_of_damage(damage_type):
    """A damage type as a school a resistance answers to (None: a blow, or plain magic)."""
    kind = str(damage_type or 'physical').lower()
    kind = RESIST_ALIASES.get(kind, kind)
    return kind if kind in RESIST_KEYS else None


def _gear_stat(name):
    """A player attribute that is its base plus what worn gear adds. Writing it moves the base by
    as much as the value moved (a level's gain, a spell's +2 and its -2 when it ends);
    Player.set_base() sets the base outright."""
    def get(self):
        return self.__dict__.get('_base', {}).get(name, 0) + self.gear_bonus(name)

    def put(self, value):
        self.__dict__.setdefault('_base', {})[name] = value - self.gear_bonus(name)
    return property(get, put)


class Player(Character):
    """Player character class."""
    
    def __init__(self, world: 'World' = None):
        super().__init__()
        self.world = world
        self.config = Config()
        self.connection = None
        
        # Player-specific attributes
        self.password_hash = ""
        self.account_name = None  # Link to account for multi-character
        self.race = "human"
        self.sex = "neutral"  # male, female, or neutral
        self.look_style = ""  # a mage's look in 3D: "" (classic) or "archmage" (gear_look.py)
        self.char_class = "warrior"
        self.title = "the Adventurer"
        
        self.room_vnum = self.config.STARTING_ROOM
        
        # Progression
        self.practices = 0
        self.trains = 0
        
        # Skills and spells
        self.skills = {}
        self.spells = {}
        self.talents = {}  # Talent tree points
        
        # Quest tracking
        self.quests_completed = []
        self.quest_flags = {}
        self.quest_chains = {}  # chain_id -> {stage, completed, choices, history}
        self.dialogue_state = {}  # npc_vnum -> dialogue node id
        self.active_quests = []  # List of ActiveQuest objects
        self.daily_quest_completions = {}  # quest_id -> ISO datetime string
        self.tracked_quest = None  # quest_id being tracked in prompt

        # Procedural dungeon tracking
        self.active_dungeon = None

        # Group/following
        self.group = None  # Group object if in a group
        self.following = None  # Player being followed

        # Player flags
        self.flags = set()

        # Command system
        self.last_command = ""  # For ! repeat
        self.custom_aliases = {}  # Personal alias system
        self.target = None  # Current combat target for targeting system
        self.target_labels = {}  # Label system: {"DEAD": character_obj, "TANK": char_obj}

        # Autoloot settings
        self.autoloot = False  # Automatically loot items from corpses
        self.autoloot_gold = True  # Automatically loot gold from corpses (default on)
        self.autogold = True  # Automatically pick up gold from the ground

        # Auto-combat settings
        self.autoattack = False  # Automatically attack your target
        self.autocombat = False  # Automatically use skills/spells in combat
        self.auto_combat_settings = {
            'heal_threshold': 35,  # Percent HP
            'use_skills': True,
            'use_spells': True,
            'skill_priority': ['bash', 'kick'],
            'spell_priority': ['heal', 'cure_critical', 'cure_serious', 'cure_light', 'fireball', 'lightning_bolt', 'magic_missile'],
        }
        self.auto_combat_cooldowns = {}
        self.last_autocombat_time = 0

        # Display modes
        self.brief_mode = False  # Shorter room descriptions
        self.compact_mode = False  # Less combat spam
        self.autoexit = True  # Show exits on room entry
        self.show_room_vnums = False  # Show room vnum numbers
        self.ai_chat_enabled = True  # AI NPC chat enabled
        self.prompt_enabled = True   # Show prompt

        # Recall system
        self.recall_point = 3001  # Default recall point (Temple of Garathorm)
        # the marquee quest (marquee.py): the quest you run or help with, and the marquee
        # abilities' long cooldowns (marquee_abilities.py), kept across logins
        self.marquee = None
        self.marquee_help = None
        self.marquee_cd = {}
        self.spell_cd = {}          # spell -> when it may be cast again (SPELLS 'cooldown')
        self.last_death = None      # {'exp': lost, 'at': when}: what a resurrection gives back
        self.autorecall_hp = None  # HP threshold for automatic recall
        self.autorecall_is_percent = False  # Whether autorecall_hp is a percentage

        # Travel system
        self.discovered_waypoints = set()
        self.travel_cooldown_until = 0

        # XP bonuses & tracking
        self.rested_xp = 0
        self.kill_streak = 0
        self.best_kill_streak = 0
        self.xp_breakdown = {
            'kill': 0,
            'exploration': 0,
            'quest': 0,
            'boss': 0,
            'streak': 0,
            'rested': 0,
            'other': 0,
        }

        # Hunger/Thirst System (game-time based, realistic timescales)
        self.hunger = 168  # Max 168 game hours = 1 week (0 = starving)
        self.thirst = 60  # Max 60 game hours = 2.5 days (0 = dying of thirst)
        self.max_hunger = 168
        self.max_thirst = 60
        self.last_hunger_hour = 0  # Track last game hour for hunger
        self.last_thirst_hour = 0  # Track last game hour for thirst
        
        # Banking System
        self.bank_gold = 0  # Gold stored in the bank

        # Mount System
        self.mount = None  # Currently mounted creature (Mount dataclass or None)
        self.owned_mounts = []  # List of owned mount dicts [{key, loyalty}, ...]
        self.last_mount = None  # the mount last ridden (`mount last`, the R key in /play)

        # Companion System
        self.companions = []
        self.last_companion_upkeep_day = None

        # Combat Companion (class-based, unlocked at level 20)
        self.combat_companion = None  # CombatCompanion instance or None

        # Bard Performance System
        self.performing = None          # Current song key being performed

        # UI settings
        self.ascii_ui = False           # Use ASCII-only UI (no box drawing)
        self.performance_ticks = 0      # How long currently performing
        self.encore_active = False      # Encore boost active
        self.encore_ticks = 0           # Encore duration remaining
        self.last_countersong = 0       # Cooldown tracking (timestamp)
        self.last_encore = 0            # Cooldown tracking (timestamp)
        self.lullaby_saves = {}         # Track cumulative lullaby penalties per target

        # Warrior Rage & Stance System (legacy - kept for save compat)
        self.rage = 0                   # Current rage (unused for warriors now)
        self.max_rage = 100             # Maximum rage
        self.stance = 'normal'          # Current stance (legacy)
        self.ignore_pain_absorb = 0     # Damage absorption remaining
        self.ignore_pain_ticks = 0      # Duration remaining
        self.last_warcry = 0            # Cooldown tracking (timestamp)
        self.last_battleshout = 0       # Cooldown tracking (timestamp)

        # Warrior Martial Doctrine + Momentum System
        self.war_doctrine = None        # 'iron_wall', 'berserker', 'warlord', or None
        self.momentum = 0              # 0-10 momentum resource
        self.ability_usage = {}        # Track uses per ability for evolution
        self.ability_evolutions = {}   # Track evolution name per ability
        self.last_warrior_ability = None  # Last ability used (for momentum)
        self.unstoppable_rounds = 0    # CC immunity counter
        self.warrior_shield = 0        # Absorb shield from abilities
        self.warrior_shield_rounds = 0
        self.warrior_dr_bonus = 0      # Temp DR from abilities
        self.warrior_dr_rounds = 0
        self.warrior_temp_armor = 0
        self.warrior_temp_armor_rounds = 0
        self.warrior_damage_buff = 0
        self.warrior_damage_buff_rounds = 0
        self.warrior_death_save_rounds = 0

        # Legacy combo chain (kept for save compat, unused)
        self.chain_count = 0
        self.chain_sequence = []
        self.chain_last_type = None
        self.chain_decay_time = 0.0
        self.chain_bonuses = {}

        # Ranger Companion & Tracking System
        self.animal_companion = None    # Companion Mobile object
        self.companion_type = None      # 'wolf', 'bear', 'hawk', 'cat', 'boar'
        self.tracking_target = None     # Mob type being tracked
        self.tracking_vnum = None       # Specific mob vnum if tracking individual
        self.last_scan = 0              # Cooldown tracking (timestamp)

        # Paladin Aura & Holy Power System
        self.active_aura = None         # Current aura: devotion, protection, retribution
        self.lay_hands_used = False     # Daily lay hands (resets on rest)
        self.last_smite = 0             # Cooldown tracking (timestamp)

        # Mage Arcane Charges System
        self.arcane_charges = 0         # Arcane charges (0-5)
        self.max_arcane_charges = 5
        self.charge_decay_time = 0      # Timestamp for out-of-combat decay

        # Ranger Focus System
        self.focus = 0                  # Current focus (0-100)
        self.hunters_mark_target = None  # Marked prey reference

        # Bard Inspiration System
        self.inspiration = 0            # Current inspiration (0-10)
        self.active_song = None          # Current song being played
        self.song_targets = []           # Players affected by current song

        # Thief Combo Point System
        self.combo_points = 0           # Current combo points (0-5)
        self.combo_target = None        # Target combo points are built on

        # Assassin Intel System
        self.intel_target = None        # Mob currently marked for Intel
        self.intel_points = 0           # Intel accumulated (0-10)
        self.intel_thresholds = {}      # Track which thresholds triggered
        self.expose_until = 0           # Timestamp: target takes 15% more dmg
        self.expose_target = None       # Who is exposed
        self.feint_until = 0            # Timestamp: feint damage reduction active
        self.feint_reduction = 0.0      # Feint reduction amount
        self.evasion_until = 0          # Timestamp: 100% dodge
        self.shadowstep_dodge = False   # Next attack dodged
        self.mark_cooldown = 0
        self.expose_cooldown = 0
        self.vital_cooldown = 0
        self.execute_cooldown = 0
        self.feint_cooldown = 0
        self.evasion_cooldown = 0
        self.vanish_cooldown = 0
        self.shadowstep_cooldown = 0

        # Cleric Divine Favor System (legacy)
        self.divine_favor = 0           # Divine favor points (0-100)
        self.last_turn_undead = 0       # Cooldown tracking (timestamp)

        # === CLASS REWORK WAVE 1 RESOURCES ===

        # Thief Luck System (Scoundrel)
        self.luck_points = 0            # Current luck (0-10)
        self.luck_streak = 0            # Consecutive lucky hits
        self.rigged_dice_hits = 0       # Remaining guaranteed crits from rigged_dice
        self.pocket_sand_cooldown = 0
        self.low_blow_cooldown = 0
        self.rigged_dice_cooldown = 0
        self.jackpot_cooldown = 0
        self.second_chance_used = False # Once per fight

        # Necromancer Soul Shard System
        self.soul_shards = 0            # Current soul shards (0-10)
        self.active_minion = None       # Summoned minion reference
        self.bone_shield_charges = 0    # Remaining bone shield charges
        self.bone_shield_until = 0      # Bone shield expiry timestamp
        self.soul_bolt_cooldown = 0
        self.drain_soul_cooldown = 0
        self.bone_shield_cooldown = 0
        self.soul_reap_cooldown = 0

        # Paladin Holy Power System
        self.holy_power = 0             # Current holy power (0-5)
        self.active_oath = None         # 'vengeance', 'devotion', 'justice', or None
        self.divine_storm_cooldown = 0

        # Cleric Faith System
        self.faith = 0                  # Current faith (0-10)
        self.shadow_form = False        # Shadow form toggle
        self.divine_word_cooldown = 0
        self.holy_fire_cooldown = 0
        self.divine_intervention_cooldown = 0
        self.holy_fire_dot_target = None
        self.holy_fire_dot_ticks = 0
        self.holy_fire_dot_damage = 0

        # Blind/stun tracking for combat (used by thief abilities)
        self.blinded_until = 0          # Timestamp when blind expires
        self.blinded_rounds = 0         # Rounds of blind remaining
        self.stunned_rounds = 0         # Rounds of stun remaining

        # Rent/Storage System
        self.storage = []  # Items in storage (inn locker)
        self.storage_location = None  # Room vnum where storage is located

        # Achievements
        self.achievements = {}
        self.achievement_progress = {}
        self.explored_rooms = set()
        self.discovered_exits = set()
        self.secret_rooms_found = set()

        # Puzzles & collections
        self.puzzle_state = {}
        self.collection_progress = {}
        self.collections_completed = []

        # New Game+ tracking
        self.ng_plus_cycle = 0
        self.nightmare_mode = False

        # Lore & Journal
        self.discovered_lore = set()
        self.lore_catalog = {}
        self.journal = []
        self.journal_keys = set()  # For fast lookup of discovered entries

        # Housing
        self.house_vnum = None
        self.house_storage = []

        # Faction reputation
        self.reputation = {}
        self.faction_rewards = {}
        self.grants_received = []   # one-time gifts already given (grants.py)
        try:
            from factions import FactionManager
            FactionManager.ensure_player_reputation(self)
        except Exception:
            pass

        # Prestige Class System
        self.prestige_class = None      # Prestige class key (e.g., 'champion', 'archmage')
        self.prestige_cooldowns = {}    # Ability cooldowns {ability_key: timestamp}

        # Arena PvP stats
        self.arena_wins = 0
        self.arena_losses = 0
        self.arena_rating = 1000
        self.arena_highest_rating = 1000
        self.arena_points = 0

        # Timestamps
        self.created_at = datetime.now()
        self.last_login = datetime.now()
        self.last_logout = datetime.now()
        self.total_playtime = 0

    def has_light_source(self) -> bool:
        """Check if the player has an active light source equipped or held."""
        # Light slot
        light_item = self.equipment.get('light') if hasattr(self, 'equipment') else None
        if light_item:
            if getattr(light_item, 'covered', False):
                return False
            if getattr(light_item, 'light_lit', True) is False:
                return False
            item_type = getattr(light_item, 'item_type', None)
            light_hours = getattr(light_item, 'light_hours', 0)
            if item_type == 'light' or light_hours > 0 or light_hours == -1:
                return True

        # Held item can also be a light source
        held_item = self.equipment.get('hold') if hasattr(self, 'equipment') else None
        if held_item:
            if getattr(held_item, 'covered', False):
                return False
            if getattr(held_item, 'light_lit', True) is False:
                return False
            item_type = getattr(held_item, 'item_type', None)
            light_hours = getattr(held_item, 'light_hours', 0)
            if item_type == 'light' or light_hours > 0 or light_hours == -1:
                return True

        return False

    def get_perception(self) -> int:
        """Derived perception stat for detecting stealth."""
        wis = getattr(self, 'wis', 10)
        dex = getattr(self, 'dex', 10)
        level = getattr(self, 'level', 1)
        # Base perception
        per = int((wis + dex) / 2 + (level / 5))
        # Race bonuses
        try:
            race_info = self.config.RACES.get(self.race, {})
            per += race_info.get('perception_bonus', 0)
        except Exception:
            pass
        # Class bonuses
        if getattr(self, 'char_class', '') in ('thief', 'assassin', 'ranger'):
            per += 2
        return per

    def get_skill_level(self, skill: str) -> int:
        """Base skill level plus equipment and stat bonuses for that skill."""
        base = 0
        try:
            base = self.skills.get(skill, 0)
        except Exception:
            base = 0

        stat_map = {
            'dodge': 'dex',
            'evasion': 'dex',
            'parry': 'dex',
            'shield_block': 'str',
            'bash': 'str',
            'kick': 'str',
            'cleave': 'str',
            'charge': 'str',
            'execute': 'str',
            'backstab': 'dex',
            'sneak': 'dex',
            'hide': 'dex',
            'pick_lock': 'dex',
            'steal': 'dex',
            'track': 'wis',
            'tame': 'wis',
        }
        stat_bonus = 0
        stat_key = stat_map.get(skill)
        if stat_key and hasattr(self, stat_key):
            stat_bonus = (getattr(self, stat_key) - 10) // 2

        return base + self.get_equipment_bonus(skill) + stat_bonus

    def can_see_in_dark(self) -> bool:
        """Determine if the player can see in dark conditions."""
        if self.has_light_source():
            return True

        race_abilities = self.config.RACES.get(self.race, {}).get('abilities', [])
        if 'infravision' in race_abilities:
            return True

        if hasattr(self, 'affect_flags') and 'infravision' in self.affect_flags:
            return True
        if self.get_equipment_bonus('detect_all'):      # a legendary's all-seeing eye
            return True

        # Rogue night vision (thief/assassin) via high perception
        if getattr(self, 'char_class', '') in ('thief', 'assassin'):
            if self.get_perception() >= 14:
                return True

        return False

    # ==================== WARRIOR DOCTRINE SYSTEM ====================
    # See warrior_abilities.py for full implementation

    def add_journal_entry(self, text: str, category: str = None):
        """Add a journal entry for the player."""
        if not hasattr(self, 'journal') or self.journal is None:
            self.journal = []
        entry = {
            'time': datetime.now().isoformat(),
            'text': text,
            'category': category
        }
        self.journal.append(entry)
        # Keep journal size manageable
        if len(self.journal) > 200:
            self.journal = self.journal[-200:]
        
    # ---- what worn gear adds (GEAR_STATS) ----
    def _gear_totals(self) -> dict:
        """Every affect type's total over worn gear and its sets' bonuses, reckoned again only
        when what is worn changes (or the zone, for a set's home-zone bonus)."""
        eq = self.__dict__.get('equipment') or {}
        room = self.__dict__.get('room')
        zone = getattr(getattr(room, 'zone', None), 'number', None) if room is not None else None
        sig = (zone,) + tuple((id(it), getattr(it, 'vnum', None), len(getattr(it, 'affects', None) or ()))
                              for it in eq.values() if it)
        cache = self.__dict__.get('_gear_cache')
        if cache is not None and cache[0] == sig:
            return cache[1]
        totals, sets = {}, {}
        for it in eq.values():
            if not it:
                continue
            for a in getattr(it, 'affects', None) or ():
                if isinstance(a, dict):
                    kind = a.get('applies_to') if a.get('type') == 'modify_stat' else a.get('type')
                    value = a.get('value', 0)
                elif getattr(a, 'type', None) == 'modify_stat':
                    kind, value = getattr(a, 'applies_to', None), getattr(a, 'value', 0)
                else:
                    continue
                if kind and isinstance(value, (int, float)):
                    totals[kind] = totals.get(kind, 0) + value
            sid = getattr(it, 'set_id', None)
            if sid:
                sid = int(sid) if isinstance(sid, str) and sid.isdigit() else sid
                sets[sid] = sets.get(sid, 0) + 1
        if sets:
            try:
                from sets import get_set_bonus
            except Exception:
                get_set_bonus = None
            for sid, pieces in sets.items() if get_set_bonus else ():
                for in_zone in (False, True) if zone == sid else (False,):
                    for kind, value in (get_set_bonus(sid, pieces, in_zone=in_zone) or {}).items():
                        if isinstance(value, (int, float)):
                            # a set's armour class is better armour (lower AC: a negative
                            # 'armor', as items give it); a curse ward is a spell ward
                            kind, value = SET_STAT_AS.get(kind, (kind, 1))[0], value * SET_STAT_AS.get(kind, (kind, 1))[1]
                            totals[kind] = totals.get(kind, 0) + value
        # what legendaries' standing procs add (procs.equip_totals)
        try:
            import procs
            for kind, value in procs.equip_totals([it for it in eq.values() if it]).items():
                totals[kind] = totals.get(kind, 0) + value
        except Exception:
            logger.exception('equip procs')
        self.__dict__['_gear_cache'] = (sig, totals)
        return totals

    def get_equipment_bonus(self, stat: str) -> int:
        """Total of one affect type over worn gear and its sets' bonuses."""
        return self._gear_totals().get(stat, 0)

    def gear_bonus(self, name: str) -> int:
        """What worn gear adds to an attribute or a maximum, under any of its names."""
        totals = self._gear_totals()
        return sum(totals.get(k, 0) for k in GEAR_STATS.get(name, (name,)))

    def gear_stat(self, stat: str) -> int:
        """A player's attributes count their gear already."""
        return getattr(self, stat, 0)

    def base_stat(self, name: str) -> int:
        """An attribute or maximum without what gear adds (what is saved)."""
        return self.__dict__.get('_base', {}).get(name, 0)

    def set_base(self, name: str, value) -> None:
        """Set an attribute's or maximum's own value outright, whatever is worn."""
        self.__dict__.setdefault('_base', {})[name] = value

    def resistance(self, damage_type) -> int:
        """The percent of this kind of harm worn gear turns aside (0 for blows and plain magic)."""
        school = school_of_damage(damage_type)
        if school is None:
            return 0
        totals = self._gear_totals()
        return max(0, min(RESIST_CAP, int(sum(totals.get(k, 0) for k in RESIST_KEYS[school]))))

    def gear_saves(self) -> int:
        """What gear adds to a saving throw (spells.py _saves: a d20, higher is better). Items give
        saves the old way, a percent where lower is better: -10 is two points on the d20."""
        totals = self._gear_totals()
        return int(round(-(totals.get('saves', 0) + totals.get('saving_spell', 0)) / 5))

    def gear_hasted(self) -> bool:
        """Worn gear that quickens (an item flagged 'haste', or a haste affect)."""
        if self._gear_totals().get('haste', 0) > 0:
            return True
        return any('haste' in (getattr(it, 'flags', None) or ()) for it in (self.__dict__.get('equipment') or {}).values() if it)

    def clamp_vitals(self) -> None:
        """Health, mana and moves can't stay above maxima that fell (gear taken off)."""
        for cur, top in (('hp', 'max_hp'), ('mana', 'max_mana'), ('move', 'max_move')):
            limit = getattr(self, top)
            if getattr(self, cur, 0) > limit:
                setattr(self, cur, limit)

    @classmethod
    def create_new(cls, name: str, password: str, race: str, char_class: str, 
                   stats: Dict[str, int], world: 'World', sex: str = 'neutral', look_style: str = '') -> 'Player':
        """Create a new player character."""
        player = cls(world)
        player.name = name
        player.set_password(password)
        player.race = race
        player.char_class = char_class
        player.sex = sex if sex in ('male', 'female') else 'neutral'
        player.look_style = look_style if look_style in LOOK_STYLES else ''
        
        # Set stats (their own: gear comes later and adds while worn)
        for stat in ('str', 'int', 'wis', 'dex', 'con', 'cha'):
            player.set_base(stat, stats[stat])
        
        # Calculate derived stats based on class
        class_data = player.config.CLASSES[char_class]
        # HP: 12-22 range based on class and constitution
        # progression-01: a level-1 bard or thief rolled 13-14 HP and died to level-1
        # creatures; the first ten minutes must not hinge on a CON roll — floor at 16
        player.set_base('max_hp', max(16, 12 + class_data['hit_dice'] // 2 + (player.con - 10) // 2))
        # Mana: ~100 base, scales with INT + WIS
        player.set_base('max_mana', 100 + class_data['mana_dice'] * 5 + (player.int + player.wis - 20) * 2)
        # Moves: 100+ base, scales with constitution
        player.set_base('max_move', 100 + class_data['move_dice'] * 5 + player.con * 2)
        
        player.hp = player.max_hp
        player.mana = player.max_mana
        player.move = player.max_move
        
        # Starting resources
        player.gold = player.config.STARTING_GOLD
        player.exp = player.config.STARTING_EXPERIENCE
        player.practices = 0          # abilities grow by use now (mastery.py)
        player.trains = 0
        
        # Learn the level-1 abilities, at 50%
        import mastery
        mastery.grant_now(player)
            
        # Give starting equipment
        player._give_starting_equipment()
        
        logger.info(f"Created new character: {name} ({race} {char_class})")
        return player
        
    def _give_starting_equipment(self):
        """Give starting equipment based on class."""
        from objects import create_object, create_preset_object

        def _make(vnum):
            """Create object from preset first (starter gear), then world fallback."""
            obj = create_preset_object(vnum)
            if not obj:
                obj = create_object(vnum, self.world if hasattr(self, 'world') else None)
            return obj

        # Everyone gets basic items
        bread = _make(1)  # Bread
        if bread:
            self.inventory.append(bread)

        waterskin = _make(2)  # Waterskin
        if waterskin:
            self.inventory.append(waterskin)

        torch = _make(3)  # Torch
        if torch:
            self.inventory.append(torch)

        # Class-specific equipment sets
        equipment_sets = {
            'warrior': {
                'wield': 10,    # Short sword
                'head': 30,     # Iron helmet
                'body': 31,     # Chainmail
                'legs': 32,     # Iron greaves
                'shield': 33,   # Wooden shield
            },
            'mage': {
                'wield': 34,    # Wooden staff
                'body': 35,     # Cloth robes
                'hold': 36,     # Spellbook
            },
            'cleric': {
                'wield': 12,    # Mace
                'body': 37,     # Leather armor
                'neck1': 38,    # Holy symbol
            },
            'thief': {
                'wield': 11,    # Dagger
                'body': 39,     # Leather jerkin
                'hold': 40,     # Lockpicks
            },
            'ranger': {
                'wield': 13,    # Short bow
                'body': 41,     # Studded leather
                'hold': 42,     # Quiver of arrows
            },
            'paladin': {
                'wield': 10,    # Short sword
                'body': 31,     # Chainmail
                'shield': 33,   # Wooden shield
                'neck1': 38,    # Holy symbol
            },
            'necromancer': {
                'wield': 43,    # Dark staff
                'body': 44,     # Dark robes
                'neck1': 45,    # Unholy symbol
            },
            'bard': {
                'wield': 14,    # Rapier
                'body': 46,     # Leather vest
                'hold': 47,     # Lute
            },
            'assassin': {
                'wield': 48,    # Stiletto
                'body': 49,     # Black leather armor
                'about': 50,    # Dark cloak
                'hold': 51,     # Poison vial
            },
        }

        # Equip class-specific gear
        class_equipment = equipment_sets.get(self.char_class, {})
        for slot, vnum in class_equipment.items():
            item = _make(vnum)
            if item:
                self.equipment[slot] = item
            
    def set_password(self, password: str):
        """Set the player's password (salted PBKDF2, security.py). No password (a character
        made from the account menu) leaves the hash empty: it opens through the account."""
        import security
        self.password_hash = security.hash_password(password) if password else ""
        
    async def check_password(self, password: str) -> bool:
        """Check if the password matches; an old-style hash is upgraded (saved with the
        character)."""
        import security
        ok, rehash = await security.verify_async(self.password_hash, password)
        if ok and rehash:
            self.password_hash = await security.hash_async(password)
        return ok
        
    async def send(self, message: str, newline: bool = True, kind: str = None):
        """Send a message to the player (kind: msgkind.UI for a line the page also draws)."""
        if self.connection:
            if kind:
                await self.connection.send(message, newline, kind=kind)
            else:
                await self.connection.send(message, newline)
            
    def _save_companions(self) -> List[Dict]:
        """Save persistent companions to dict format."""
        if not hasattr(self, 'companions'):
            return []

        companions_data = []
        from pets import Pet
        from companions import Companion

        for companion in self.companions:
            if isinstance(companion, Companion):
                companions_data.append(companion.to_dict())
            elif isinstance(companion, Pet) and companion.is_persistent:
                comp_data = {
                    'kind': 'pet',
                    'name': companion.name,
                    'short_desc': companion.short_desc,
                    'long_desc': companion.long_desc,
                    'level': companion.level,
                    'hp': companion.hp,
                    'max_hp': companion.max_hp,
                    'damage_dice': companion.damage_dice,
                    'loyalty': getattr(companion, 'loyalty', 100),
                    'experience': getattr(companion, 'experience', 0),
                    'pet_level': getattr(companion, 'pet_level', 1),
                    'pet_type': companion.pet_type,
                    'role': getattr(companion, 'role', None),
                    'special_abilities': getattr(companion, 'special_abilities', []),
                    'flags': list(getattr(companion, 'flags', set())),
                    'timer': getattr(companion, 'timer', None),
                }
                companions_data.append(comp_data)

        return companions_data

    async def save(self):
        """Save the player to disk."""
        data = {
            'name': self.name,
            'password_hash': self.password_hash,
            'account_name': self.account_name,
            'race': self.race,
            'char_class': self.char_class,
            'sex': self.sex,
            'look_style': self.look_style,
            'title': self.title,
            'level': self.level,
            'exp': self.exp,
            'gold': self.gold,
            'alignment': self.alignment,
            'hp': self.hp,
            # their own maxima and attributes: what gear adds comes back with the gear
            'max_hp': self.base_stat('max_hp'),
            'mana': self.mana,
            'max_mana': self.base_stat('max_mana'),
            'move': self.move,
            'max_move': self.base_stat('max_move'),
            'str': self.base_stat('str'),
            'int': self.base_stat('int'),
            'wis': self.base_stat('wis'),
            'dex': self.base_stat('dex'),
            'con': self.base_stat('con'),
            'cha': self.base_stat('cha'),
            'armor_class': self.armor_class,
            'hitroll': self.hitroll,
            'damroll': self.damroll,
            'practices': self.practices,
            'trains': self.trains,
            # a private trial's rooms vanish with it: such a room names the way back (instance_exit)
            'room_vnum': (getattr(self.room, 'instance_exit', None) or self.room.vnum) if self.room else self.config.STARTING_ROOM,
            'skills': self.skills,
            'spells': self.spells,
            'talents': getattr(self, 'talents', {}),
            'quest_tracking': dict(getattr(self, 'quest_tracking', None) or {}),
            'path': getattr(self, 'path', None),
            'path_switch_available': getattr(self, 'path_switch_available', False),
            'quests_completed': self.quests_completed,
            'quest_flags': self.quest_flags,
            'quest_chains': self.quest_chains,
            'dialogue_state': self.dialogue_state,
            'active_quests': [q.to_dict() for q in self.active_quests],
            'daily_quest_completions': getattr(self, 'daily_quest_completions', {}),
            'tracked_quest': getattr(self, 'tracked_quest', None),
            'flags': list(self.flags),
            'inventory': [item.to_dict() for item in self.inventory],
            'equipment': {slot: item.to_dict() if item else None
                         for slot, item in self.equipment.items()},
            'affects': AffectManager.save_affects(self),
            'companions': self._save_companions(),
            'custom_aliases': self.custom_aliases,
            'web_bar': getattr(self, 'web_bar', None),   # the 3D client's action bar, as arranged
            'autoloot': self.autoloot,
            'autoloot_gold': self.autoloot_gold,
            'autogold': self.autogold,
            'autoattack': self.autoattack,
            'autocombat': self.autocombat,
            'auto_combat_settings': self.auto_combat_settings,
            'brief_mode': self.brief_mode,
            'compact_mode': self.compact_mode,
            'stance': getattr(self, 'stance', 'normal'),
            'wimpy': getattr(self, 'wimpy', 0),
            'show_room_vnums': self.show_room_vnums,
            'autoexit': self.autoexit,
            'recall_point': self.recall_point,
            'marquee': self.marquee,
            'marquee_help': self.marquee_help,
            'marquee_cd': self.marquee_cd,
            'spell_cd': {k: v for k, v in (self.spell_cd or {}).items() if v > time.time()},
            'last_death': self.last_death,
            'autorecall_hp': self.autorecall_hp,
            'autorecall_is_percent': self.autorecall_is_percent,
            'hunger': self.hunger,
            'thirst': self.thirst,
            'max_hunger': self.max_hunger,
            'max_thirst': self.max_thirst,
            'last_hunger_hour': self.last_hunger_hour,
            'last_thirst_hour': self.last_thirst_hour,
            'owned_mounts': self.owned_mounts,
            'last_mount': getattr(self, 'last_mount', None),
            'active_mount': self.mount.to_dict() if self.mount else None,
            'combat_companion': self.combat_companion.to_dict() if self.combat_companion else None,
            'last_companion_upkeep_day': self.last_companion_upkeep_day,
            'storage': [item.to_dict() for item in self.storage],
            'storage_location': self.storage_location,
            'achievements': self.achievements,
            'achievement_progress': self.achievement_progress,
            'available_titles': getattr(self, 'available_titles', []),
            'lore_read': list(getattr(self, 'lore_read', set())),
            'explored_rooms': list(self.explored_rooms),
            'discovered_exits': [list(x) for x in self.discovered_exits],
            'secret_rooms_found': list(self.secret_rooms_found),
            'discovered_lore': list(self.discovered_lore),
            'lore_catalog': self.lore_catalog,
            'journal': self.journal,
            'journal_keys': list(self.journal_keys),
            'puzzle_state': self.puzzle_state,
            'collection_progress': self.collection_progress,
            'collections_completed': self.collections_completed,
            'ng_plus_cycle': self.ng_plus_cycle,
            'nightmare_mode': self.nightmare_mode,
            'house_vnum': self.house_vnum,
            'house_storage': [item.to_dict() for item in self.house_storage],
            'reputation': self.reputation,
            'faction_rewards': self.faction_rewards,
            'grants_received': list(getattr(self, 'grants_received', []) or []),
            'discovered_waypoints': list(self.discovered_waypoints),
            'travel_cooldown_until': self.travel_cooldown_until,
            'rested_xp': self.rested_xp,
            'kill_streak': self.kill_streak,
            'best_kill_streak': self.best_kill_streak,
            'xp_breakdown': self.xp_breakdown,
            'stats': getattr(self, 'stats', {}),
            'daily_bonus': getattr(self, 'daily_bonus', {}),
            'visited_rooms': list(getattr(self, 'visited_rooms', set())),
            'horsemen_killed': list(getattr(self, 'horsemen_killed', set())),
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat(),
            'last_logout': self.last_logout.isoformat(),
            'last_host': getattr(self, 'last_host', 'Unknown'),
            'total_playtime': self.total_playtime,
            'rent_data': getattr(self, 'rent_data', None),
            # Warrior Doctrine System
            'war_doctrine': getattr(self, 'war_doctrine', None),
            'momentum': getattr(self, 'momentum', 0),
            'ability_usage': getattr(self, 'ability_usage', {}),
            'ability_evolutions': getattr(self, 'ability_evolutions', {}),
            'last_warrior_ability': getattr(self, 'last_warrior_ability', None),
            'unstoppable_rounds': getattr(self, 'unstoppable_rounds', 0),
            # Prestige Class System
            'prestige_class': getattr(self, 'prestige_class', None),
            # Arena PvP stats
            'arena_wins': getattr(self, 'arena_wins', 0),
            'arena_losses': getattr(self, 'arena_losses', 0),
            'arena_rating': getattr(self, 'arena_rating', 1000),
            'arena_highest_rating': getattr(self, 'arena_highest_rating', 1000),
            'arena_points': getattr(self, 'arena_points', 0),
            # Crafting system
            'known_recipes': getattr(self, 'known_recipes', None),
            'crafting_levels': getattr(self, 'crafting_levels', None),
            'crafting_xp': getattr(self, 'crafting_xp', None),
            # Social system
            'friends_list': getattr(self, 'friends_list', []),
            'ignore_list': getattr(self, 'ignore_list', []),
            'player_notes': getattr(self, 'player_notes', {}),
            'disabled_channels': list(getattr(self, 'disabled_channels', set())),
            'friend_notify': getattr(self, 'friend_notify', True),
        }
        # stats are saved without the buffs on them: the buffs are saved too and loading
        # applies them again (saved with them inside, a buff stuck for good after a relog)
        for stat in AffectManager.VALID_STATS:
            if isinstance(data.get(stat), (int, float)) and not isinstance(data.get(stat), bool):
                bonus = AffectManager.stat_bonus(self, stat)
                if bonus:
                    data[stat] = data[stat] - bonus

        filepath = os.path.join(self.config.PLAYER_DIR, f"{self.name.lower()}.json")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.debug(f"Saved player: {self.name}")

    @staticmethod
    def exists(name: str) -> bool:
        """Check if a player file exists."""
        filepath = os.path.join(Config.PLAYER_DIR, f"{name.lower()}.json")
        return os.path.exists(filepath)
    
    @staticmethod
    def get_info(name: str) -> Optional[dict]:
        """Get raw player info from file without loading full player object.
        Used for account menu displays without updating last_login."""
        filepath = os.path.join(Config.PLAYER_DIR, f"{name.lower()}.json")
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return {
                'name': data.get('name', name),
                'race': data.get('race', 'Human'),
                'char_class': data.get('char_class', 'warrior'),
                'level': data.get('level', 1),
                'hp': data.get('hp', 100),
                'max_hp': data.get('max_hp', 100),
                'mana': data.get('mana', 100),
                'max_mana': data.get('max_mana', 100),
                'gold': data.get('gold', 0),
                'exp': data.get('exp', 0),
                'room': data.get('room', 3001),
                'stats': data.get('stats', {}),
                'skills': data.get('skills', {}),
                'spells': data.get('spells', {}),
                'kills': data.get('kills', 0),
                'deaths': data.get('deaths', 0),
                'hitroll': data.get('hitroll', 0),
                'damroll': data.get('damroll', 0),
                'last_login': data.get('last_login'),
                'last_host': data.get('last_host', 'Unknown'),
                'created_at': data.get('created_at'),
            }
        except Exception:
            return None
        
    @classmethod
    def load(cls, name: str, world: 'World' = None) -> Optional['Player']:
        """Load a player from disk. World is optional for info-only loads."""
        filepath = os.path.join(Config.PLAYER_DIR, f"{name.lower()}.json")
        
        if not os.path.exists(filepath):
            return None
            
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            from world import renumbered

            player = cls(world)

            # Load all attributes
            player.name = data['name']
            player.password_hash = data['password_hash']
            player.account_name = data.get('account_name')
            player.race = data['race']
            player.char_class = data['char_class']
            player.sex = data.get('sex', 'neutral') if data.get('sex') in ('male', 'female') else 'neutral'
            player.look_style = data.get('look_style', '') if data.get('look_style') in LOOK_STYLES else ''
            player.title = data.get('title', 'the Adventurer')
            player.level = data['level']
            player.exp = data['exp']
            player.gold = data['gold']
            player.alignment = data.get('alignment', 0)
            player.hp = data['hp']
            player.mana = data['mana']
            player.move = data['move']
            for name in ('max_hp', 'max_mana', 'max_move', 'str', 'int', 'wis', 'dex', 'con', 'cha'):
                player.set_base(name, data[name])
            player.armor_class = data.get('armor_class', 100)
            player.hitroll = data.get('hitroll', 0)
            player.damroll = data.get('damroll', 0)
            player.practices = data.get('practices', 0)
            player.trains = data.get('trains', 0)
            player.room_vnum = renumbered(data.get('room_vnum', Config.STARTING_ROOM))
            player.skills = data.get('skills', {})
            player.spells = data.get('spells', {})
            # Combat reinvention: migrate renamed ability keys so existing
            # characters keep their learned abilities at equal power.
            LEGACY_ABILITY_MAP = {
                # Necromancer (Soulbinder)
                'death_grip': 'mistgrasp', 'death_coil': 'wraithfire',
                'plague_strike': 'mistrot', 'finger_of_death': 'sever_cord',
                # Mage (Adept of the High Tower)
                'blink': 'stepwise', 'displacement': 'phase_step',
                'mirror_image': 'tower_echoes', 'spell_reflection': 'mirrorward',
                'time_warp': 'quicken', 'icy_veins': 'rimeheart',
                'combustion_master': 'kindling_focus', 'arcane_explosion': 'resonance_burst',
                # Cleric (Keeper of the Holy Order)
                'prayer_of_mending': 'travelling_grace', 'spirit_link': 'shared_burden',
                'lightwell': 'font_of_the_vigil',
                # Paladin (Lightbringer)
                'consecration': 'hallowed_ground', 'hammer_of_justice': 'dawnhammer',
                'avenging_wrath_master': 'ascendant_hour', 'crusaders_judgment': 'verdict_of_the_order',
                'hand_of_freedom': 'unfettered',
                # Final de-WoW pass (learnable spells)
                'vampiric_touch': 'leechcraft', 'hymn_of_hope': 'refrain_of_hope',
                'mass_dispel': 'cleansing_rite',
            }
            for old_key, new_key in LEGACY_ABILITY_MAP.items():
                if old_key in player.spells:
                    player.spells.setdefault(new_key, player.spells.pop(old_key))
                else:
                    player.spells.pop(old_key, None)
            # Skill renames (combat reinvention, skill pass) — migrate skills
            LEGACY_SKILL_MAP = {
                'aimed_shot': 'truesight_shot', 'kill_command': 'wildbond_strike',
                'rapid_fire': 'loosing_storm', 'hunters_mark': 'quarry_mark',
                'arcane_barrage': 'charge_release', 'arcane_blast': 'towerbolt',
                'evocation': 'drink_the_leyline',
                'shadow_step': 'slip_the_veil', 'vanish': 'fade',
                'holy_fire': 'pyre_of_faith',
                'templars_verdict': 'order_verdict', 'word_of_glory': 'absolution',
                'divine_storm': 'halo_of_reckoning', 'smite': 'censure',
                'avatar_of_war': 'war_incarnate', 'drain_soul': 'soul_siphon',
            }
            for old_key, new_key in LEGACY_SKILL_MAP.items():
                if old_key in player.skills:
                    player.skills.setdefault(new_key, player.skills.pop(old_key))
            player.talents = data.get('talents', {})
            player.quest_tracking = dict(data.get('quest_tracking', {}) or {})
            player.path = data.get('path', None)
            player.path_switch_available = data.get('path_switch_available', False)
            player.quests_completed = data.get('quests_completed', [])
            player.quest_flags = data.get('quest_flags', {})
            player.quest_chains = data.get('quest_chains', {})
            player.dialogue_state = data.get('dialogue_state', {})

            # Load active quests
            from quests import ActiveQuest
            player.active_quests = [ActiveQuest.from_dict(q) for q in data.get('active_quests', [])]
            player.daily_quest_completions = data.get('daily_quest_completions', {})
            player.tracked_quest = data.get('tracked_quest', None)

            player.flags = set(data.get('flags', []))
            player.custom_aliases = data.get('custom_aliases', {})
            player.web_bar = data.get('web_bar')
            player.autoloot = data.get('autoloot', False)
            player.autoloot_gold = data.get('autoloot_gold', True)
            player.autogold = data.get('autogold', True)
            player.autoattack = data.get('autoattack', False)
            player.autocombat = data.get('autocombat', False)
            player.auto_combat_settings = data.get('auto_combat_settings', player.auto_combat_settings)
            player.brief_mode = data.get('brief_mode', False)
            player.show_room_vnums = bool(data.get('show_room_vnums', False))
            player.compact_mode = data.get('compact_mode', False)
            player.stance = data.get('stance', 'normal')
            player.wimpy = data.get('wimpy', 0)
            player.autoexit = data.get('autoexit', True)
            player.recall_point = renumbered(data.get('recall_point', 3001))
            player.marquee = data.get('marquee')
            player.marquee_help = data.get('marquee_help')
            player.marquee_cd = data.get('marquee_cd') or {}
            player.spell_cd = data.get('spell_cd') or {}
            player.last_death = data.get('last_death')
            player.autorecall_hp = data.get('autorecall_hp', None)
            player.autorecall_is_percent = data.get('autorecall_is_percent', False)
            player.hunger = data.get('hunger', 168)
            player.thirst = data.get('thirst', 60)
            player.max_hunger = data.get('max_hunger', 168)
            player.max_thirst = data.get('max_thirst', 60)
            player.last_hunger_hour = data.get('last_hunger_hour', 0)
            player.last_thirst_hour = data.get('last_thirst_hour', 0)
            player.owned_mounts = data.get('owned_mounts', [])
            player.last_mount = data.get('last_mount')
            # Restore active mount
            active_mount_data = data.get('active_mount')
            if active_mount_data:
                from mounts import MountManager
                player.mount = MountManager.load_mount(active_mount_data)
            # a one-time gift waiting for them (world/grants.json), told when they enter the world
            player.grants_received = list(data.get('grants_received', []) or [])
            # Restore combat companion
            combat_comp_data = data.get('combat_companion')
            if combat_comp_data:
                from companions import CombatCompanion
                player.combat_companion = CombatCompanion.from_dict(combat_comp_data, player)
            player.last_companion_upkeep_day = data.get('last_companion_upkeep_day', None)

            from objects import Object

            # Load storage
            player.storage = [Object.from_dict(item_data, world)
                            for item_data in data.get('storage', [])
                            if item_data]
            player.storage_location = renumbered(data.get('storage_location', None))

            # Load achievements
            player.achievements = data.get('achievements', {})
            player.achievement_progress = data.get('achievement_progress', {})
            player.available_titles = data.get('available_titles', [])
            player.lore_read = set(data.get('lore_read', []))
            player.explored_rooms = set(data.get('explored_rooms', []))
            player.discovered_exits = set(tuple(x) for x in data.get('discovered_exits', []))
            player.secret_rooms_found = set(data.get('secret_rooms_found', []))
            player.discovered_lore = set(data.get('discovered_lore', []))
            player.lore_catalog = data.get('lore_catalog', {})
            player.journal = data.get('journal', [])
            player.journal_keys = set(data.get('journal_keys', []))
            # Rebuild keys from existing journal entries if not saved
            if not player.journal_keys and player.journal:
                for entry in player.journal:
                    if isinstance(entry, dict) and 'key' in entry:
                        player.journal_keys.add(entry['key'])
            player.puzzle_state = data.get('puzzle_state', {})
            player.collection_progress = data.get('collection_progress', {})
            player.collections_completed = data.get('collections_completed', [])
            player.ng_plus_cycle = data.get('ng_plus_cycle', 0)
            player.nightmare_mode = data.get('nightmare_mode', False)

            # Travel + XP bonuses
            player.discovered_waypoints = set(data.get('discovered_waypoints', []))
            player.travel_cooldown_until = data.get('travel_cooldown_until', 0)
            player.rested_xp = data.get('rested_xp', 0)
            player.kill_streak = data.get('kill_streak', 0)
            player.best_kill_streak = data.get('best_kill_streak', 0)
            player.xp_breakdown = data.get('xp_breakdown', player.xp_breakdown)
            
            # Stats and daily bonus
            player.stats = data.get('stats', {})
            player.daily_bonus = data.get('daily_bonus', {})
            player.visited_rooms = set(data.get('visited_rooms', []))
            player.horsemen_killed = set(data.get('horsemen_killed', []))

            # Load housing
            player.house_vnum = data.get('house_vnum', None)
            player.house_storage = [Object.from_dict(item_data, world)
                                   for item_data in data.get('house_storage', [])
                                   if item_data]

            # Load faction reputation
            player.reputation = data.get('reputation', {})
            player.faction_rewards = data.get('faction_rewards', {})
            try:
                from factions import FactionManager
                FactionManager.ensure_player_reputation(player)
            except Exception:
                pass

            # Load affects using AffectManager
            affects_data = data.get('affects', [])
            if affects_data and isinstance(affects_data[0], dict) if affects_data else False:
                # New format - use AffectManager
                AffectManager.load_affects(player, affects_data)
            else:
                # Old format - clear old broken affects
                player.affects = []
                player.affect_flags = set()

            # Load inventory
            player.inventory = [Object.from_dict(item_data, world) 
                               for item_data in data.get('inventory', [])
                               if item_data]
            
            # Load equipment
            player.equipment = {}
            for slot, item_data in data.get('equipment', {}).items():
                if item_data:
                    player.equipment[slot] = Object.from_dict(item_data, world)
                else:
                    player.equipment[slot] = None

            # Load companions (persistent pets or hirelings)
            player.companions = []
            companions_data = data.get('companions', [])
            if companions_data:
                from pets import Pet
                from companions import Companion
                for comp_data in companions_data:
                    kind = comp_data.get('kind', 'pet') if isinstance(comp_data, dict) else 'pet'
                    if kind == 'companion' or 'companion_type' in comp_data:
                        companion = Companion.from_dict(comp_data, world, player)
                        player.companions.append(companion)
                    else:
                        # Create pet from saved data
                        pet_type = comp_data.get('pet_type', 'companion')
                        pet = Pet(0, world, player, pet_type)
                        pet.name = comp_data['name']
                        pet.short_desc = comp_data['short_desc']
                        pet.long_desc = comp_data['long_desc']
                        pet.level = comp_data['level']
                        pet.hp = comp_data['hp']
                        pet.max_hp = comp_data['max_hp']
                        pet.damage_dice = comp_data['damage_dice']
                        pet.loyalty = comp_data.get('loyalty', 100)
                        pet.experience = comp_data.get('experience', 0)
                        pet.pet_level = comp_data.get('pet_level', 1)
                        pet.role = comp_data.get('role')
                        pet.special_abilities = comp_data.get('special_abilities', [])
                        pet.flags = set(comp_data.get('flags', []))
                        pet.timer = comp_data.get('timer')  # Restore remaining duration
                        pet.is_persistent = True

                        player.companions.append(pet)
                        # Companions will be added to world when player enters game

            # Parse timestamps
            player.created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
            player.last_logout = datetime.fromisoformat(data.get('last_logout', datetime.now().isoformat()))
            player.last_login = datetime.now()
            player.total_playtime = data.get('total_playtime', 0)
            player.rent_data = data.get('rent_data', None)

            # Warrior Doctrine System
            player.war_doctrine = data.get('war_doctrine', None)
            player.momentum = data.get('momentum', 0)
            player.ability_usage = data.get('ability_usage', {})
            player.ability_evolutions = data.get('ability_evolutions', {})
            # migrate renamed evolution forms (whirlwind/avatar_of_war)
            _EVO_RENAME = {'whirlwind': 'bloodwhirl', 'avatar_of_war': 'war_incarnate'}
            if isinstance(player.ability_evolutions, dict):
                for _k, _v in list(player.ability_evolutions.items()):
                    if _v in _EVO_RENAME:
                        player.ability_evolutions[_k] = _EVO_RENAME[_v]
            player.last_warrior_ability = data.get('last_warrior_ability', None)
            player.unstoppable_rounds = data.get('unstoppable_rounds', 0)

            # Arena PvP stats
            # Prestige Class System
            player.prestige_class = data.get('prestige_class', None)
            player.prestige_cooldowns = {}

            player.arena_wins = data.get('arena_wins', 0)
            player.arena_losses = data.get('arena_losses', 0)
            player.arena_rating = data.get('arena_rating', 1000)
            player.arena_highest_rating = data.get('arena_highest_rating', 1000)
            player.arena_points = data.get('arena_points', 0)

            # Crafting system
            try:
                from crafting import load_crafting_data
                load_crafting_data(player, {
                    'known_recipes': data.get('known_recipes'),
                    'crafting_levels': data.get('crafting_levels'),
                    'crafting_xp': data.get('crafting_xp'),
                })
            except Exception:
                pass

            # Social system
            player.friends_list = data.get('friends_list', [])
            player.ignore_list = data.get('ignore_list', [])
            player.player_notes = data.get('player_notes', {})
            player.disabled_channels = set(data.get('disabled_channels', []))
            player.friend_notify = data.get('friend_notify', True)

            # Rested XP from time offline
            try:
                offline_seconds = max(0, (player.last_login - player.last_logout).total_seconds())
                offline_hours = offline_seconds / 3600.0
                max_rested = int(player.exp_to_level() * player.config.RESTED_XP_CAP)
                gain = int(player.exp_to_level() * player.config.RESTED_XP_RATE * offline_hours)
                if gain > 0:
                    player.rested_xp = min(max_rested, player.rested_xp + gain)
            except Exception:
                pass
            
            # a one-time gift waiting for them (world/grants.json), given once everything is read
            # (so the map it reveals isn't overwritten), told when they enter the world
            if world is not None:
                try:
                    import grants
                    player._grant_notes = grants.apply_grants(player)
                except Exception:
                    logger.exception('grants')

            logger.info(f"Loaded player: {player.name}")
            return player
            
        except Exception as e:
            logger.error(f"Error loading player {name}: {e}")
            return None
            
    async def execute_command(self, cmd: str, args: List[str]):
        """Execute a player command."""
        from commands import CommandHandler
        await CommandHandler.execute(self, cmd, args)
        await self.sync_room()

    async def sync_room(self):
        """After anything that may have moved this player (a teleport, a portal, recall,
        being summoned...): if the 3D client last saw them elsewhere, chart the room and
        send it the new one. Walks already do this; this catches every other way."""
        room = getattr(self, 'room', None)
        wm = getattr(getattr(self, 'world', None), 'web_map', None)
        if room is None or wm is None or getattr(self, '_web_last_vnum', None) == room.vnum:
            return
        try:
            if getattr(self, 'explored_rooms', None) is not None:
                self.explored_rooms.add(room.vnum)
            await wm.notify_player(self)
        except Exception:
            logger.debug('sync_room failed', exc_info=True)
        
    async def do_look(self, args: List[str]):
        """Look at the room or an object."""
        if not self.room:
            await self.send("You are floating in the void...")
            return

        # Can't see anything while sleeping
        if self.position == 'sleeping':
            await self.send("You can't see anything, you're sleeping!")
            return

        if not args:
            # Look at room
            await self.room.show_to(self, force_exits=True)
        else:
            # Check for "look in <container>" syntax
            args_str = ' '.join(args).lower()
            if args_str.startswith('in ') or ' in ' in args_str:
                # Handle both "in chest" and "item in chest" patterns
                if args_str.startswith('in '):
                    container_name = args_str[3:].strip()  # Remove "in " from start
                else:
                    parts = args_str.split(' in ', 1)
                    container_name = parts[1].strip()

                # Find container or drink container in room or inventory
                container = None
                drink_container = None
                for item in self.inventory + self.room.items:
                    if container_name in item.name.lower():
                        if hasattr(item, 'item_type'):
                            if item.item_type == 'container':
                                container = item
                                break
                            elif item.item_type == 'drink':
                                drink_container = item
                                break

                c = self.config.COLORS

                # Handle drink containers (waterskins, canteens, etc.)
                if drink_container:
                    liquid = getattr(drink_container, 'liquid', 'water')
                    drinks = getattr(drink_container, 'drinks', 0)
                    max_drinks = getattr(drink_container, 'max_drinks', 20)
                    
                    await self.send(f"{c['cyan']}You look inside {drink_container.short_desc}:{c['reset']}")
                    
                    if drinks <= 0:
                        await self.send(f"  {c['white']}It is empty.{c['reset']}")
                    else:
                        # Calculate fullness percentage
                        if max_drinks > 0:
                            pct = (drinks / max_drinks) * 100
                        else:
                            pct = 100 if drinks > 0 else 0
                        
                        # Describe fullness
                        if pct >= 90:
                            fullness = "full"
                            color = c['bright_cyan']
                        elif pct >= 60:
                            fullness = "more than half full"
                            color = c['cyan']
                        elif pct >= 40:
                            fullness = "about half full"
                            color = c['yellow']
                        elif pct >= 20:
                            fullness = "less than half full"
                            color = c['yellow']
                        else:
                            fullness = "nearly empty"
                            color = c['red']
                        
                        await self.send(f"  {color}It contains {liquid} and is {fullness}.{c['reset']}")
                        await self.send(f"  {c['white']}({drinks}/{max_drinks} drinks remaining){c['reset']}")
                    return

                if not container and not drink_container:
                    await self.send(f"You don't see a '{container_name}' that you can look inside here.")
                    return

                # Check if container is closed
                if hasattr(container, 'is_closed') and container.is_closed:
                    await self.send(f"The {container.short_desc} is closed.")
                    return

                # Show container contents
                await self.send(f"{c['cyan']}Inside {container.short_desc}:{c['reset']}")

                # Check for gold
                if hasattr(container, 'gold') and container.gold > 0:
                    await self.send(f"  {c['yellow']}{container.gold} gold coins{c['reset']}")

                # Check for items
                if hasattr(container, 'contents') and container.contents:
                    for cont_item in container.contents:
                        await self.send(f"  {cont_item.short_desc}")
                elif not hasattr(container, 'gold') or container.gold == 0:
                    await self.send(f"  {c['white']}Nothing.{c['reset']}")

                return

            # Look at something specific
            target = ' '.join(args).lower()

            # Expand direction abbreviations
            dir_abbrevs = {'n': 'north', 's': 'south', 'e': 'east', 'w': 'west', 'u': 'up', 'd': 'down'}
            if target in dir_abbrevs:
                target = dir_abbrevs[target]

            # Check directions FIRST - look into adjacent rooms
            if target in self.config.DIRECTIONS:
                exit_data = self.room.exits.get(target)
                if not exit_data:
                    await self.send("There is no exit in that direction.")
                    return

                c = self.config.COLORS

                # Check for closed door
                if 'door' in exit_data:
                    door = exit_data['door']
                    if door.get('state') == 'closed':
                        door_name = door.get('name', 'door')
                        await self.send(f"{c['yellow']}The {door_name} is closed.{c['reset']}")
                        return

                # Look into the next room
                next_room = exit_data.get('room')
                if next_room:
                    game_time = self.world.game_time if hasattr(self, 'world') and self.world else None
                    if hasattr(next_room, 'is_dark') and next_room.is_dark(game_time) and not self.can_see_in_dark():
                        await self.send(f"{c['blue']}It is too dark to see that way.{c['reset']}")
                        return

                    await self.send(f"{c['cyan']}You look {target}...{c['reset']}\n")
                    await self.send(f"{c['bright_yellow']}{next_room.name}{c['reset']}")

                    # Show exit description if available
                    exit_desc = exit_data.get('description', '')
                    if exit_desc:
                        await self.send(f"{c['white']}{exit_desc}{c['reset']}")

                    # Show brief room description (first 2 sentences or 200 chars)
                    desc = next_room.description
                    if desc:
                        # Get first two sentences
                        sentences = desc.split('.')
                        if len(sentences) >= 2:
                            brief_desc = sentences[0] + '.' + sentences[1] + '.'
                        else:
                            brief_desc = sentences[0] + '.'
                        if len(brief_desc) > 200:
                            brief_desc = desc[:200] + '...'
                        await self.send(f"{c['white']}{brief_desc}{c['reset']}")
                    elif not exit_desc:
                        # No description at all - generate generic one from room name
                        await self.send(f"{c['white']}You see {next_room.name.lower()}.{c['reset']}")

                    # Show characters in that room
                    if next_room.characters:
                        await self.send(f"\n{c['green']}You see:{c['reset']}")
                        for char in next_room.characters:
                            mob_flags = set(getattr(char, 'flags', set()) or [])
                            mob_name  = getattr(char, 'name', '')
                            mob_align = getattr(char, 'alignment', 0)
                            if hasattr(char, 'owner') and char.owner:
                                peek_color = c['bright_magenta']
                            elif 'boss' in mob_flags:
                                peek_color = c['bright_magenta']
                            elif 'aggressive' in mob_flags or 'aggro' in mob_flags:
                                peek_color = c['bright_red']
                            elif 'shopkeeper' in mob_flags or 'friendly' in mob_flags or mob_align >= 500:
                                peek_color = c['bright_green']
                            elif mob_name and not mob_name.startswith(('a ', 'an ', 'the ', 'some ')):
                                peek_color = c['bright_yellow']
                            elif hasattr(char, 'connection'):
                                peek_color = c['bright_green']
                            else:
                                peek_color = c['yellow']
                            label = getattr(char, 'short_desc', None) or mob_name
                            await self.send(f"  {peek_color}{label}{c['reset']}")

                    # Show obvious items
                    if next_room.items:
                        item_count = len(next_room.items)
                        if item_count > 0:
                            await self.send(f"{c['yellow']}You notice {item_count} item(s) there.{c['reset']}")
                else:
                    # Room not linked - try to fetch by vnum
                    to_room = exit_data.get('to_room')
                    if to_room and hasattr(self, 'world') and self.world:
                        next_room = self.world.rooms.get(to_room)
                        if next_room:
                            await self.send(f"{c['cyan']}You look {target}...{c['reset']}\n")
                            await self.send(f"{c['bright_yellow']}{next_room.name}{c['reset']}")
                            if next_room.description:
                                brief_desc = next_room.description[:200]
                                if len(next_room.description) > 200:
                                    brief_desc += '...'
                                await self.send(f"{c['white']}{brief_desc}{c['reset']}")
                            return
                    # Fallback to exit description
                    desc = exit_data.get('description', '')
                    if desc:
                        await self.send(f"You see {desc}.")
                    else:
                        await self.send(f"You see an exit leading {target}.")
                return

            # Check for doors by name (trapdoor, gate, door, etc.)
            for direction, exit_data in self.room.exits.items():
                if exit_data and 'door' in exit_data:
                    door = exit_data['door']
                    door_name = door.get('name', 'door')
                    if target in door_name.lower() or door_name.lower() in target:
                        c = self.config.COLORS
                        state = door.get('state', 'open')
                        await self.send(f"{c['cyan']}You examine the {door_name} ({direction}):{c['reset']}")
                        
                        # Describe appearance
                        door_desc = door.get('description', f"A sturdy {door_name}.")
                        await self.send(f"{c['white']}{door_desc}{c['reset']}")
                        
                        # State info
                        state_info = []
                        if state == 'closed':
                            state_info.append(f"{c['yellow']}closed{c['reset']}")
                        else:
                            state_info.append(f"{c['green']}open{c['reset']}")
                        if door.get('locked'):
                            state_info.append(f"{c['red']}locked{c['reset']}")
                        if door.get('picked'):
                            state_info.append(f"{c['magenta']}lock picked{c['reset']}")
                        if door.get('broken'):
                            state_info.append(f"{c['red']}broken{c['reset']}")
                        
                        await self.send(f"It is currently: {', '.join(state_info)}")
                        return

            # Check characters in room (with numbered targeting: 2.guardian)
            char_target = self.find_target_in_room(target)
            if char_target:
                await self.show_character(char_target)
                return

            # Check items in inventory
            for item in self.inventory:
                if target.lower() in item.name.lower():
                    await self.send(item.get_description())
                    # If it's a container, show contents too
                    if hasattr(item, 'item_type') and item.item_type == 'container':
                        await self._show_container_contents(item)
                    # If it's a drink container, show fill level
                    elif hasattr(item, 'item_type') and item.item_type == 'drink':
                        await self._show_drink_contents(item)
                    return

            # Check items in room
            for item in self.room.items:
                if target.lower() in item.name.lower():
                    await self.send(item.get_description())
                    # If it's a container, show contents too
                    if hasattr(item, 'item_type') and item.item_type == 'container':
                        await self._show_container_contents(item)
                    # If it's a drink container, show fill level
                    elif hasattr(item, 'item_type') and item.item_type == 'drink':
                        await self._show_drink_contents(item)
                    return

            await self.send(f"You don't see '{target}' here.")

    async def _show_container_contents(self, container):
        """Show what's inside a container."""
        c = self.config.COLORS

        # Check if container is closed
        if hasattr(container, 'is_closed') and container.is_closed:
            await self.send(f"{c['yellow']}The {container.short_desc} is closed.{c['reset']}")
            return

        await self.send(f"\n{c['cyan']}Inside {container.short_desc}:{c['reset']}")

        has_contents = False

        # Check for gold
        if hasattr(container, 'gold') and container.gold > 0:
            await self.send(f"  {c['yellow']}{container.gold} gold coins{c['reset']}")
            has_contents = True

        # Check for items
        if hasattr(container, 'contents') and container.contents:
            for cont_item in container.contents:
                await self.send(f"  {cont_item.short_desc}")
            has_contents = True

        if not has_contents:
            await self.send(f"  {c['white']}Nothing.{c['reset']}")

    async def _show_drink_contents(self, drink_item):
        """Show the contents and fill level of a drink container."""
        c = self.config.COLORS
        liquid = getattr(drink_item, 'liquid', 'water')
        drinks = getattr(drink_item, 'drinks', 0)
        max_drinks = getattr(drink_item, 'max_drinks', 20)
        
        await self.send(f"\n{c['cyan']}Contents:{c['reset']}")
        
        if drinks <= 0:
            await self.send(f"  {c['white']}It is empty.{c['reset']}")
        else:
            # Calculate fullness percentage
            if max_drinks > 0:
                pct = (drinks / max_drinks) * 100
            else:
                pct = 100 if drinks > 0 else 0
            
            # Describe fullness
            if pct >= 90:
                fullness = "full"
                color = c['bright_cyan']
            elif pct >= 60:
                fullness = "more than half full"
                color = c['cyan']
            elif pct >= 40:
                fullness = "about half full"
                color = c['yellow']
            elif pct >= 20:
                fullness = "less than half full"
                color = c['yellow']
            else:
                fullness = "nearly empty"
                color = c['red']
            
            await self.send(f"  {color}Contains {liquid}, {fullness}.{c['reset']}")
            await self.send(f"  {c['white']}({drinks}/{max_drinks} drinks remaining){c['reset']}")

    async def show_character(self, char: 'Character'):
        """Show details about a character."""
        c = self.config.COLORS
        
        # Check if player has labeled this character
        label_msg = ""
        if hasattr(self, 'target_labels') and self.target_labels:
            for label_name, labeled_char in self.target_labels.items():
                if labeled_char == char:
                    label_msg = f" {c['bright_yellow']}({label_name}){c['reset']}"
                    break
        
        # Determine color for this NPC
        mob_flags = set(getattr(char, 'flags', set()) or [])
        mob_name  = getattr(char, 'name', '')
        mob_align = getattr(char, 'alignment', 0)
        if hasattr(char, 'connection'):
            char_color = c['bright_green']
        elif hasattr(char, 'owner') and char.owner:
            char_color = c['bright_magenta']
        elif 'boss' in mob_flags:
            char_color = c['bright_magenta']
        elif 'aggressive' in mob_flags or 'aggro' in mob_flags:
            char_color = c['bright_red']
        elif 'shopkeeper' in mob_flags or 'friendly' in mob_flags or mob_align >= 500:
            char_color = c['bright_green']
        elif mob_name and not mob_name.startswith(('a ', 'an ', 'the ', 'some ')):
            char_color = c['bright_yellow']
        else:
            char_color = c['yellow']

        if hasattr(char, 'long_desc'):
            await self.send(f"{char_color}{char.long_desc}{c['reset']}{label_msg}")
        else:
            await self.send(f"{char_color}You see {char.name}.{c['reset']}{label_msg}")
            
        # Show condition
        hp_pct = char.hp / char.max_hp if char.max_hp > 0 else 0
        if hp_pct >= 1.0:
            condition = "is in excellent condition"
        elif hp_pct >= 0.9:
            condition = "has a few scratches"
        elif hp_pct >= 0.75:
            condition = "has some small wounds"
        elif hp_pct >= 0.5:
            condition = "has quite a few wounds"
        elif hp_pct >= 0.30:
            condition = "has some big nasty wounds"
        elif hp_pct >= 0.15:
            condition = "looks pretty hurt"
        else:
            condition = "is in awful condition"
            
        await self.send(f"{c['white']}{char.name} {condition}.{c['reset']}")
        
        # Show affects with flavorful descriptions
        affect_descriptions = []
        affect_flags = getattr(char, 'affect_flags', set())
        
        if 'blind' in affect_flags or 'blinded' in affect_flags:
            affect_descriptions.append(f"{c['magenta']}{char.name} stumbles around blindly, arms outstretched, searching for something to grab onto.{c['reset']}")
        if 'poisoned' in affect_flags:
            affect_descriptions.append(f"{c['green']}{char.name} looks sickly, with a greenish pallor and beads of sweat.{c['reset']}")
        if 'stunned' in affect_flags:
            affect_descriptions.append(f"{c['yellow']}{char.name} sways unsteadily, looking dazed and confused.{c['reset']}")
        if 'sleeping' in affect_flags or char.position == 'sleeping':
            affect_descriptions.append(f"{c['blue']}{char.name} is fast asleep, oblivious to the world.{c['reset']}")
        if 'paralyzed' in affect_flags:
            affect_descriptions.append(f"{c['red']}{char.name} stands frozen in place, unable to move a muscle.{c['reset']}")
        if 'feared' in affect_flags:
            affect_descriptions.append(f"{c['yellow']}{char.name} cowers in terror, eyes wide with fear.{c['reset']}")
        if 'silenced' in affect_flags:
            affect_descriptions.append(f"{c['cyan']}{char.name} opens their mouth but no sound comes out.{c['reset']}")
        if 'charmed' in affect_flags:
            affect_descriptions.append(f"{c['magenta']}{char.name} has a dreamy, vacant look in their eyes.{c['reset']}")
        if 'entangled' in affect_flags:
            affect_descriptions.append(f"{c['green']}{char.name} struggles against vines and roots wrapped around their limbs.{c['reset']}")
        if 'slow' in affect_flags:
            affect_descriptions.append(f"{c['cyan']}{char.name} moves with unnatural slowness, as if wading through honey.{c['reset']}")
        if 'haste' in affect_flags or (hasattr(char, 'gear_hasted') and char.gear_hasted()):
            affect_descriptions.append(f"{c['bright_cyan']}{char.name} moves with supernatural speed, almost blurring.{c['reset']}")
        if 'sanctuary' in affect_flags:
            affect_descriptions.append(f"{c['bright_white']}{char.name} is surrounded by a shimmering white aura.{c['reset']}")
        if 'invisible' in affect_flags:
            affect_descriptions.append(f"{c['white']}{char.name} flickers in and out of visibility.{c['reset']}")
        if 'fly' in affect_flags:
            affect_descriptions.append(f"{c['cyan']}{char.name} hovers slightly off the ground.{c['reset']}")
        if 'stoneskin' in affect_flags:
            affect_descriptions.append(f"{c['white']}{char.name}'s skin has a grey, rocky texture.{c['reset']}")
        if 'fire_shield' in affect_flags:
            affect_descriptions.append(f"{c['bright_red']}{char.name} is wreathed in flickering flames.{c['reset']}")
        if 'ice_armor' in affect_flags:
            affect_descriptions.append(f"{c['bright_cyan']}{char.name} is encased in a layer of frost and ice.{c['reset']}")
        
        for desc in affect_descriptions:
            await self.send(desc)
        
        # Show active spell affects
        affects = getattr(char, 'affects', [])
        if affects:
            buff_names = []
            debuff_names = []
            debuff_keywords = [
                'pain', 'curse', 'poison', 'slow', 'blind', 'stun', 'wound', 'bleed', 
                'burn', 'rend', 'sunder', 'enervation', 'weaken', 'chill', 'drain',
                'fear', 'sleep', 'entangle', 'root', 'snare', 'silence', 'doom',
                'plague', 'disease', 'wither', 'decay', 'corrupt', 'hex', 'jinx',
                'debilitate', 'cripple', 'hamstring', 'daze', 'confuse', 'disorient',
                'vulnerability', 'expose', 'mark', 'faerie_fire', 'shadow_word'
            ]
            for affect in affects:
                # Handle both Affect objects and dicts
                name = getattr(affect, 'name', None) or affect.get('name', 'unknown') if isinstance(affect, dict) else 'unknown'
                if not name or name == 'unknown':
                    continue
                # Categorize as buff or debuff
                if any(neg in name.lower() for neg in debuff_keywords):
                    debuff_names.append(name.replace('_', ' ').title())
                else:
                    buff_names.append(name.replace('_', ' ').title())
            
            if buff_names:
                await self.send(f"{c['bright_green']}Buffs: {', '.join(buff_names)}{c['reset']}")
            if debuff_names:
                await self.send(f"{c['bright_red']}Afflictions: {', '.join(debuff_names)}{c['reset']}")
        
        # Show equipment if player
        if hasattr(char, 'equipment') and char.equipment:
            await self.send(f"{c['cyan']}{char.name} is using:{c['reset']}")
            for slot, item in char.equipment.items():
                if item:
                    await self.send(f"  <{slot}>: {item.short_desc}")

    def find_target_in_room(self, target_name: str):
        """
        Find a target in the room with numbered targeting support.
        Supports: "goblin", "1.goblin", "2.goblin", labels, etc.
        Returns: Character object or None
        """
        if not target_name or not self.room:
            return None

        # the 3D client names creatures exactly: "#12" is map_system's id for one live mob
        if target_name.startswith('#') and target_name[1:].isdigit():
            uid = int(target_name[1:])
            for char in self.room.characters:
                if char is not self and getattr(char, '_web_uid', None) == uid:
                    return char
            return None

        # Check labels first (case-insensitive)
        label_upper = target_name.upper()
        if label_upper in self.target_labels:
            labeled_char = self.target_labels[label_upper]
            # Verify the labeled character is still in the room
            if labeled_char in self.room.characters:
                return labeled_char
            else:
                # Character left/died, remove stale label
                del self.target_labels[label_upper]

        # Check for numbered target (e.g., "1.goblin", "2.goblin")
        target_number = 1
        if '.' in target_name:
            parts = target_name.split('.', 1)
            if parts[0].isdigit():
                target_number = int(parts[0])
                target_name = parts[1]

        # Find matching characters
        matches = []
        for char in self.room.characters:
            if char != self and self.matches_character(char, target_name):
                matches.append(char)

        # Return the nth match (1-indexed)
        if target_number <= len(matches):
            return matches[target_number - 1]

        return None

    def matches_character(self, char, target_name: str) -> bool:
        """
        Check if a character matches the target name.
        Checks name, short_desc, and keywords.
        """
        target_lower = target_name.lower()

        # Check name
        if target_lower in char.name.lower():
            return True

        # Check short_desc
        if hasattr(char, 'short_desc') and target_lower in char.short_desc.lower():
            return True

        # Check keywords list (for mobs)
        if hasattr(char, 'keywords') and char.keywords:
            if target_lower in char.keywords:
                return True
            # Also check if target is part of any keyword
            for keyword in char.keywords:
                if target_lower in keyword or keyword in target_lower:
                    return True

        return False

    def find_item_in_room(self, item_name: str):
        """
        Find an item in the room with numbered targeting support.
        Supports: "sword", "1.sword", "2.sword", etc.
        Returns: Item object or None
        """
        if not item_name or not self.room:
            return None

        # Check for numbered target (e.g., "1.chest", "2.chest")
        target_number = 1
        if '.' in item_name:
            parts = item_name.split('.', 1)
            if parts[0].isdigit():
                target_number = int(parts[0])
                item_name = parts[1]

        # Find matching items
        matches = []
        for item in self.room.items:
            if item_name.lower() in item.name.lower():
                matches.append(item)

        # Return the nth match (1-indexed)
        if target_number <= len(matches):
            return matches[target_number - 1]

        return None

    def find_container(self, container_name: str):
        """
        Find a container in the room or inventory with numbered targeting support.
        Supports: "corpse", "1.corpse", "2.corpse", etc.
        Returns: Container item or None
        """
        if not container_name:
            return None

        # Check for numbered target (e.g., "1.corpse", "2.corpse")
        target_number = 1
        if '.' in container_name:
            parts = container_name.split('.', 1)
            if parts[0].isdigit():
                target_number = int(parts[0])
                container_name = parts[1]

        # Find matching containers in room and inventory
        matches = []
        for item in self.room.items + self.inventory:
            if hasattr(item, 'item_type') and item.item_type == 'container':
                if container_name.lower() in item.name.lower():
                    matches.append(item)

        # Return the nth match (1-indexed)
        if target_number <= len(matches):
            return matches[target_number - 1]

        return None

    async def gain_exp(self, amount: int, source: str = 'other', breakdown: Dict[str, int] = None):
        """Gain experience points."""
        if amount <= 0:
            return

        if not hasattr(self, 'xp_breakdown') or self.xp_breakdown is None:
            self.xp_breakdown = {
                'kill': 0,
                'exploration': 0,
                'quest': 0,
                'boss': 0,
                'streak': 0,
                'rested': 0,
                'other': 0,
            }

        if breakdown:
            for key, value in breakdown.items():
                if value <= 0:
                    continue
                self.xp_breakdown[key] = self.xp_breakdown.get(key, 0) + value
        else:
            self.xp_breakdown[source] = self.xp_breakdown.get(source, 0) + amount

        self.exp += amount

        # Check for level up (respect prestige level cap)
        from prestige import get_max_level
        max_lvl = get_max_level(self)
        while self.exp >= self.exp_to_level() and self.level < max_lvl:
            await self.level_up()

    def recall_room(self):
        """Where recall, death and a lost saved place send you: your recall point while it
        still exists and you may be there (not the God Rooms or a sealed land, unless you're
        immortal), otherwise the temple."""
        world = getattr(self, 'world', None)
        if world is None:
            return None
        room = world.get_room(getattr(self, 'recall_point', None) or 0)
        if room is None or not room.admits(self):
            room = world.get_room(self.config.STARTING_ROOM)
        return room

    def exp_to_level(self) -> int:
        """Calculate experience needed for next level.
        
        Levels 1-30: Use standard EXP_MULTIPLIER (1.4x)
        Levels 31-60: Use HIGH_LEVEL_EXP_MULTIPLIER (1.6x) for slower progression
        """
        threshold = getattr(self.config, 'HIGH_LEVEL_THRESHOLD', 30)

        # Easy to start: the first four levels are a ramp, not the full curve.
        # progression-01 measured level 2 at 9.5 min on the 800-xp base (70-140
        # xp per newcomer kill); 2-3 kills a level puts level 5 near 15 minutes.
        ramp = getattr(self.config, 'NEWCOMER_EXP', (250, 350, 500, 650))
        if self.level <= len(ramp):
            return int(ramp[self.level - 1])
        if self.level <= threshold:
            # Standard progression for levels 1-30
            return int(self.config.BASE_EXP * (self.config.EXP_MULTIPLIER ** (self.level - 1)))
        else:
            # Calculate XP at level 30 as base for high-level progression
            level_30_xp = int(self.config.BASE_EXP * (self.config.EXP_MULTIPLIER ** (threshold - 1)))
            # Apply higher multiplier for levels beyond 30
            levels_beyond = self.level - threshold
            high_multiplier = getattr(self.config, 'HIGH_LEVEL_EXP_MULTIPLIER', 1.6)
            return int(level_30_xp * (high_multiplier ** levels_beyond))
        
    async def level_up(self):
        """Level up the player with an epic celebration!"""
        old_level = self.level
        self.level += 1
        
        class_data = self.config.CLASSES[self.char_class]
        
        # Gain HP
        # progression-01: two level-10 warriors forged the same way rolled 53 and 85
        # max HP — a 1..d roll per level is the widest variance in the game. Floor
        # the roll at half the hit die so levels are a gain, not a lottery.
        hd = class_data['hit_dice']
        hp_gain = random.randint(max(1, hd // 2), hd) + (self.con - 10) // 4
        self.max_hp += max(1, hp_gain)
        self.hp = self.max_hp
        
        # Gain mana
        mana_gain = random.randint(1, class_data['mana_dice']) + (self.int - 10) // 4
        self.max_mana += max(0, mana_gain)
        self.mana = self.max_mana
        
        # Gain move
        move_gain = random.randint(1, class_data['move_dice']) + (self.dex - 10) // 4
        self.max_move += max(0, move_gain)
        self.move = self.max_move
        
        # (no practice sessions any more: abilities grow as they are used, mastery.py)
        
        c = self.config.COLORS
        
        # Epic level-up display! (/play has its own: the starfield comes dimmed, the gains below stay)
        from msgkind import send_ui
        await self.send(f"\r\n")
        await send_ui(self, f"{c['bright_yellow']}    *  .  *       *  .    .  *    .   *   .     *")
        await send_ui(self, f"  .    *    .  *    .   *   . *  .    *    .")
        await send_ui(self, f"       .  *    L E V E L   U P !    *  .       ")
        await send_ui(self, f"  *  .    .  *    .   *   . *  .    *    .  *")
        await send_ui(self, f"    .   *    *  .  *       *  .    .  *    .{c['reset']}")
        await self.send(f"")
        
        # Level milestone messages
        milestone_msgs = {
            5: "You're getting the hang of this!",
            10: "A true adventurer emerges!",
            15: "Your reputation grows...",
            20: "Heroes speak your name!",
            25: "Legends are made of this!",
            30: "You walk among the elite!",
            40: "A force of nature!",
            50: "MAXIMUM POWER ACHIEVED!"
        }
        
        # Class-specific level titles
        class_titles = {
            'warrior': {5: 'Fighter', 10: 'Veteran', 15: 'Swordmaster', 20: 'Champion', 30: 'Warlord', 40: 'Battlemaster'},
            'mage': {5: 'Apprentice', 10: 'Conjurer', 15: 'Magician', 20: 'Warlock', 30: 'Archmage', 40: 'Grand Magus'},
            'cleric': {5: 'Acolyte', 10: 'Adept', 15: 'Priest', 20: 'High Priest', 30: 'Bishop', 40: 'Cardinal'},
            'thief': {5: 'Footpad', 10: 'Cutpurse', 15: 'Burglar', 20: 'Assassin', 30: 'Shadow', 40: 'Nightblade'},
            'ranger': {5: 'Scout', 10: 'Tracker', 15: 'Pathfinder', 20: 'Strider', 30: 'Ranger Lord', 40: 'Beastmaster'},
            'paladin': {5: 'Squire', 10: 'Knight', 15: 'Crusader', 20: 'Templar', 30: 'Holy Champion', 40: 'Paragon'},
            'bard': {5: 'Minstrel', 10: 'Troubadour', 15: 'Entertainer', 20: 'Virtuoso', 30: 'Maestro', 40: 'Legendsinger'},
            'necromancer': {5: 'Cultist', 10: 'Gravecaller', 15: 'Bonelord', 20: 'Deathbringer', 30: 'Lich Aspirant', 40: 'Master of Death'}
        }
        
        # Check for new title
        new_title = None
        titles = class_titles.get(self.char_class.lower(), {})
        for lvl in sorted(titles.keys(), reverse=True):
            if self.level >= lvl and old_level < lvl:
                new_title = titles[lvl]
                break
        
        await self.send(f"{c['bright_cyan']}╔══════════════════════════════════════════════════════════════╗{c['reset']}")
        await self.send(f"{c['bright_cyan']}║{c['bright_yellow']}         ★ LEVEL {self.level:>2} ACHIEVED! ★                            {c['bright_cyan']}║{c['reset']}")
        await self.send(f"{c['bright_cyan']}╠══════════════════════════════════════════════════════════════╣{c['reset']}")
        await self.send(f"{c['bright_cyan']}║{c['reset']}                                                              {c['bright_cyan']}║{c['reset']}")
        await self.send(f"{c['bright_cyan']}║{c['reset']}  {c['bright_green']}Health:  {c['white']}+{hp_gain:<3}{c['reset']}  {c['green']}({self.max_hp} total){c['reset']}                           {c['bright_cyan']}║{c['reset']}")
        await self.send(f"{c['bright_cyan']}║{c['reset']}  {c['bright_cyan']}Mana:    {c['white']}+{mana_gain:<3}{c['reset']}  {c['cyan']}({self.max_mana} total){c['reset']}                           {c['bright_cyan']}║{c['reset']}")
        await self.send(f"{c['bright_cyan']}║{c['reset']}  {c['bright_yellow']}Move:    {c['white']}+{move_gain:<3}{c['reset']}  {c['yellow']}({self.max_move} total){c['reset']}                           {c['bright_cyan']}║{c['reset']}")
        await self.send(f"{c['bright_cyan']}║{c['reset']}                                                              {c['bright_cyan']}║{c['reset']}")
        
        # Milestone message
        for lvl, msg in milestone_msgs.items():
            if self.level == lvl:
                await self.send(f"{c['bright_cyan']}║{c['reset']}  {c['bright_yellow']}{msg:^56}{c['reset']}  {c['bright_cyan']}║{c['reset']}")
                await self.send(f"{c['bright_cyan']}║{c['reset']}                                                              {c['bright_cyan']}║{c['reset']}")
                break
        
        # New title
        if new_title:
            await self.send(f"{c['bright_cyan']}║{c['reset']}  {c['bright_magenta']}★ NEW TITLE: {new_title:^40} ★{c['reset']}  {c['bright_cyan']}║{c['reset']}")
            await self.send(f"{c['bright_cyan']}║{c['reset']}                                                              {c['bright_cyan']}║{c['reset']}")
        
        await self.send(f"{c['bright_cyan']}╚══════════════════════════════════════════════════════════════╝{c['reset']}")
        await self.send(f"")
        
        # Announce to room
        if self.room:
            await self.room.send_to_room(
                f"{c['bright_yellow']}★ {self.name} has reached level {self.level}! ★{c['reset']}",
                exclude=[self]
            )
        
        # Show level up tip
        try:
            from tips import TipManager
            await TipManager.show_event_tip(self, 'level_up')
            # Contextual hints at milestone levels
            if self.level == 10:
                await TipManager.show_contextual_hint(self, 'level_10')
            elif self.level == 20:
                await TipManager.show_contextual_hint(self, 'level_20')
            elif self.level == 50:
                await TipManager.show_contextual_hint(self, 'level_50')
        except Exception:
            pass
        
        # Check for new skills/spells
        await self.check_new_abilities()
        
        # Check level achievements
        try:
            from achievements import AchievementManager
            await AchievementManager.check_level(self)
        except Exception:
            pass

        # a new band of renown (levels 10, 20, 35, 45): the 3D clients around see it (gear_look.py)
        try:
            import gear_look
            await gear_look.touch(self)
        except Exception:
            pass

    async def check_new_abilities(self):
        """Learn everything this level has reached, at 50%, announced (mastery.py)."""
        import mastery
        await mastery.grant(self)

    def get_damage_message(self, damage: int) -> str:
        """Get a message describing the damage amount."""
        if damage <= 0:
            return "miss"
        elif damage <= 4:
            return "scratch"
        elif damage <= 8:
            return "graze"
        elif damage <= 12:
            return "hit"
        elif damage <= 16:
            return "wound"
        elif damage <= 20:
            return "maul"
        elif damage <= 28:
            return "decimate"
        elif damage <= 36:
            return "devastate"
        elif damage <= 48:
            return "maim"
        elif damage <= 64:
            return "MUTILATE"
        elif damage <= 80:
            return "MASSACRE"
        elif damage <= 100:
            return "OBLITERATE"
        else:
            return "*** ANNIHILATE ***"
            
    async def take_damage(self, amount: int, attacker: 'Character' = None, damage_type: str = 'physical') -> bool:
        """Take damage, return True if killed."""
        c = self.config.COLORS
        damage_type = damage_type or 'physical'
        # worn gear turns aside part of fire, frost, poison, shadow... (Player.resistance)
        resist = self.resistance(damage_type) if amount > 1 else 0
        if resist:
            kept = max(1, int(amount * (100 - resist) / 100))
            if amount - kept > 0:
                await self.send(f"{c['cyan']}Your gear turns aside {amount - kept} of the {school_of_damage(damage_type)} damage.{c['reset']}")
            amount = kept

        flags = getattr(self, 'affect_flags', set())
        # Corpse Shield: a necromancer's pet absorbs part of every blow
        if amount > 1 and 'damage_redirect_pet' in flags:
            from affects import AffectManager
            aff = AffectManager.get_affect(self, 'corpse_shield') or AffectManager.get_affect(self, 'Corpse Shield')
            pct = getattr(aff, 'value', 50) if aff else 50
            pet = next((c2 for c2 in (getattr(self, 'companions', None) or [])
                        if getattr(c2, 'hp', 0) > 0 and getattr(c2, 'room', None) == self.room), None)
            if pet:
                redirected = max(1, amount * max(10, min(90, pct)) // 100)
                amount -= redirected
                pet.hp -= redirected
                await self.send(f"{c['green']}Your corpse shield diverts {redirected} damage to {pet.name}!{c['reset']}")
                if pet.hp <= 0:
                    pet.hp = 0
                    await self.send(f"{c['yellow']}{pet.name} is torn apart absorbing the blow!{c['reset']}")
                    if pet.room and pet in pet.room.characters:
                        pet.room.characters.remove(pet)
                    if hasattr(self, 'companions') and pet in self.companions:
                        self.companions.remove(pet)

        # Spirit Link: linked groupmates shoulder part of each other's pain
        if amount > 3 and 'spirit_link' in flags and getattr(self, 'group', None):
            linked = [m for m in getattr(self.group, 'members', [])
                      if m is not self and getattr(m, 'hp', 0) > 1
                      and 'spirit_link' in getattr(m, 'affect_flags', set())
                      and getattr(m, 'room', None) == self.room]
            if linked:
                share = (amount * 30 // 100) // len(linked)
                if share > 0:
                    amount -= share * len(linked)
                    for m in linked:
                        m.hp = max(1, m.hp - share)   # the link never kills
                        if hasattr(m, 'send'):
                            await m.send(f"{c['cyan']}The spirit link draws {share} of {self.name}'s pain into you.{c['reset']}")
                    await self.send(f"{c['cyan']}Your linked spirits absorb {share * len(linked)} damage.{c['reset']}")
        
        # Player protection intercept - check if any ally is protecting this player
        if attacker and self.room and amount > 0:
            now = time.time()
            protectors = []
            for char in self.room.characters:
                if char == self or char == attacker:
                    continue
                if getattr(char, 'protecting', None) != self:
                    continue
                if getattr(char, 'hp', 0) <= 0:
                    continue
                if hasattr(char, 'connection') and char.connection is None:
                    char.protecting = None
                    continue
                if getattr(char, 'is_fighting', False):
                    continue
                if now < getattr(char, 'protect_cooldown_until', 0):
                    continue
                protectors.append(char)
            if protectors:
                from combat import CombatHandler
                best = None
                best_chance = 0
                for protector in protectors:
                    chance = CombatHandler.get_protect_chance(protector, self, attacker)
                    if chance > best_chance:
                        best = protector
                        best_chance = chance
                if best and random.randint(1, 100) <= best_chance:
                    best.protect_cooldown_until = now + self.config.PROTECT_INTERCEPT_COOLDOWN_SECONDS
                    await self.send(f"{c['bright_green']}{best.name} leaps in front of you, taking the blow!{c['reset']}")
                    if hasattr(best, 'send'):
                        await best.send(f"{c['bright_green']}You intercept the attack meant for {self.name}!{c['reset']}")
                    if hasattr(attacker, 'send'):
                        await attacker.send(f"{c['red']}{best.name} intercepts your attack on {self.name}!{c['reset']}")
                    await self.room.send_to_room(
                        f"{c['cyan']}{best.name} throws themselves in front of {self.name}!{c['reset']}",
                        exclude=[self, best]
                    )

                    # Skill progression hook
                    try:
                        if hasattr(best, 'improve_skill'):
                            rescue_skill = best.skills.get('rescue', 0) if hasattr(best, 'skills') else 0
                            block_skill = best.skills.get('shield_block', 0) if hasattr(best, 'skills') else 0
                            skill_to_improve = 'shield_block' if block_skill >= rescue_skill and block_skill > 0 else 'rescue'
                            await best.improve_skill(skill_to_improve, difficulty=7)
                    except Exception:
                        pass

                    # Protector takes damage and optionally engages attacker
                    best.hp -= amount
                    if not getattr(best, 'is_fighting', False):
                        best.fighting = attacker
                        best.position = 'fighting'
                        if hasattr(best, 'target'):
                            best.target = attacker

                    # Check if protector died
                    if best.hp <= 0:
                        best.protecting = None
                        await self.room.send_to_room(
                            f"{c['red']}{best.name} collapses from the intercepted blow!{c['reset']}"
                        )
                        if hasattr(best, 'die'):
                            await best.die(attacker)
                    return False

        # Pet protection intercept - check if any pet is protecting this player
        if attacker and self.room and amount > 0:
            from pets import PetManager
            now = time.time()
            for char in self.room.characters:
                # Check if this is a pet protecting us
                if hasattr(char, 'ai_state') and hasattr(char, 'owner'):
                    protecting = char.ai_state.get('protecting')
                    if protecting == self and char.hp > 0 and not char.is_fighting:
                        if hasattr(char.owner, 'connection') and char.owner.connection is None:
                            continue
                        if now < getattr(char, 'protect_cooldown_until', 0):
                            continue
                        # 60% chance to intercept, higher if pet has shield_wall ability
                        intercept_chance = 60
                        if hasattr(char, 'special_abilities') and 'shield_wall' in char.special_abilities:
                            intercept_chance = 75
                        
                        if random.randint(1, 100) <= intercept_chance:
                            char.protect_cooldown_until = now + self.config.PROTECT_INTERCEPT_COOLDOWN_SECONDS
                            # Pet intercepts the attack!
                            await self.send(f"{c['bright_green']}{char.name} leaps in front of you, taking the blow!{c['reset']}")
                            await char.owner.send(f"{c['bright_green']}{char.name} intercepts an attack on {self.name}!{c['reset']}")
                            
                            # Announce to room
                            await self.room.send_to_room(
                                f"{c['cyan']}{char.name} throws itself in front of {self.name}!{c['reset']}",
                                exclude=[self, char.owner]
                            )
                            
                            # Pet takes damage and engages attacker
                            char.hp -= amount
                            
                            # Start combat between pet and attacker
                            if not char.is_fighting:
                                from combat import CombatHandler
                                await CombatHandler.start_combat(char, attacker)
                            
                            # Switch attacker's target to pet
                            if hasattr(attacker, 'fighting') and attacker.fighting == self:
                                attacker.fighting = char
                            
                            # Check if pet died
                            if char.hp <= 0:
                                await self.room.send_to_room(
                                    f"{c['red']}{char.name} collapses from the intercepted blow!{c['reset']}"
                                )
                                # Handle pet death
                                if char in self.room.characters:
                                    self.room.characters.remove(char)
                                if hasattr(char.owner, 'world') and hasattr(char.owner.world, 'npcs'):
                                    if char in char.owner.world.npcs:
                                        char.owner.world.npcs.remove(char)
                            
                            return False  # Player takes no damage
        
        # Absorb shields (divine_shield / stoneskin / armour_ward)
        try:
            absorb_allowed = damage_type == 'physical' or damage_type in self.config.ABSORB_MAGIC_TYPES
            for affect in self.affects[:]:
                if affect.applies_to in ('divine_shield', 'stoneskin', 'armour_ward') and amount > 0 and absorb_allowed:
                    absorbed = min(amount, affect.value)
                    affect.value -= absorbed
                    amount -= absorbed
                    if absorbed > 0:
                        await self.send(f"{c['cyan']}{affect.applies_to.replace('_',' ').title()} absorbs {absorbed} damage!{c['reset']}")
                    if affect.value <= 0:
                        from affects import AffectManager
                        AffectManager.remove_affect(self, affect)
        except Exception:
            pass

        # protections spells leave (spells.py): invulnerable takes nothing; sanctuary halves the
        # blow; protection from evil (good) a sixth of an evil (good) attacker's; divine guardian
        # a fifth; a mana shield draws half of what is left from mana
        wards = getattr(self, 'affect_flags', None) or set()
        if wards and amount > 0:
            if 'invulnerable' in wards:
                await self.send(f"{c['bright_yellow']}The blow breaks on your divine protection!{c['reset']}")
                return False
            if 'sanctuary' in wards:
                amount = max(1, amount // 2)
            align = getattr(attacker, 'alignment', 0) or 0
            if ('prot_evil' in wards and align <= -350) or ('prot_good' in wards and align >= 350):
                amount = max(1, amount - amount // 6)
            if 'divine_guardian' in wards:
                amount = max(1, amount - amount // 5)
            if 'mana_shield' in wards and getattr(self, 'mana', 0) > 0:
                drawn = min(amount // 2, self.mana)
                if drawn > 0:
                    self.mana -= drawn
                    amount -= drawn
                    await self.send(f"{c['cyan']}Your mana shield takes {drawn} of the blow.{c['reset']}")
            # a fire shield burns a melee attacker; ice armor may numb them (slowed a round)
            if attacker is not None and damage_type == 'physical' and getattr(attacker, 'hp', 0) > 0 and attacker is not self:
                if 'fire_shield' in wards:
                    burn = max(2, min(25, amount // 8))
                    attacker.hp -= burn
                    await self.send(f"{c['red']}Your fire shield sears {attacker.name}! [{burn}]{c['reset']}")
                    if attacker.hp <= 0:
                        from combat import CombatHandler
                        await CombatHandler.handle_death(self, attacker)
                if 'ice_armor' in wards and random.random() < 0.25:
                    attacker.slowed_until = max(getattr(attacker, 'slowed_until', 0) or 0, time.time() + 3)

        # what worn gear does when struck (procs.py): dread, a blow turned back, a frost aura
        if amount > 0 and attacker is not None and damage_type == 'physical':
            import procs
            await procs.on_defend(self, attacker, amount, damage_type)

        # Warrior Ignore Pain absorption
        if hasattr(self, 'ignore_pain_absorb') and self.ignore_pain_absorb > 0:
            absorbed = min(amount, self.ignore_pain_absorb)
            self.ignore_pain_absorb -= absorbed
            amount -= absorbed
            if absorbed > 0:
                await self.send(f"{c['cyan']}Ignore Pain absorbs {absorbed} damage!{c['reset']}")
            if self.ignore_pain_absorb <= 0:
                await self.send(f"{c['yellow']}Your Ignore Pain fades.{c['reset']}")
                self.ignore_pain_ticks = 0

        # Warrior shield absorption (from doctrine abilities)
        if amount > 0 and getattr(self, 'warrior_shield', 0) > 0:
            absorbed = min(amount, self.warrior_shield)
            self.warrior_shield -= absorbed
            amount -= absorbed
            if absorbed > 0:
                await self.send(f"{c['cyan']}Your shield absorbs {absorbed} damage!{c['reset']}")
            if self.warrior_shield <= 0:
                self.warrior_shield_rounds = 0

        # Warrior temporary DR bonus (from doctrine abilities)
        if amount > 0 and getattr(self, 'warrior_dr_bonus', 0) > 0:
            reduced = max(1, int(amount * (self.warrior_dr_bonus / 100.0)))
            amount = max(0, amount - reduced)

        # Warrior doctrine momentum DR (Iron Wall: +2% per momentum)
        if amount > 0 and getattr(self, 'war_doctrine', None) == 'iron_wall':
            momentum_dr = getattr(self, 'momentum', 0) * 0.02
            if momentum_dr > 0:
                reduced = max(1, int(amount * momentum_dr))
                amount = max(0, amount - reduced)

        # Warrior death save (Eternal Guardian)
        # Guardian Spirit (spells.py): the blow that would kill heals instead (30%), once
        if amount >= self.hp and 'guardian_spirit' in (getattr(self, 'affect_flags', None) or set()):
            from affects import AffectManager
            for a in list(self.affects):
                if a.applies_to == 'guardian_spirit':
                    AffectManager.remove_affect(self, a)
            amount = 0
            self.hp = max(self.hp, int(self.max_hp * 0.3))
            await self.send(f"{c['bright_white']}Your guardian spirit catches you as you fall!{c['reset']}")
        # Divine Intervention (spells.py): for its window nothing brings them below 1 health
        if amount >= self.hp and time.time() < (getattr(self, 'death_ward_until', 0) or 0):
            amount = max(0, self.hp - 1)
            await self.send(f"{c['bright_yellow']}Divine intervention holds you to life!{c['reset']}")
        if amount >= self.hp and getattr(self, 'warrior_death_save_rounds', 0) > 0:
            amount = self.hp - 1
            self.warrior_death_save_rounds = 0
            await self.send(f"{c['bright_cyan']}Your Eternal Guardian saves you from death!{c['reset']}")
        # a cocoon (procs.cheat_death): once a day the killing blow is turned aside
        if amount >= self.hp > 0:
            import procs
            if await procs.cheat_death(self):
                amount = 0

        # Damage reduction / PB mitigation (affects + stance + parry/shield skill interactions)
        effective_pb = self.get_pb_value() if hasattr(self, 'get_pb_value') else int(getattr(self, 'damage_reduction', 0))
        if amount > 0 and effective_pb > 0:
            reduced = max(1, int(amount * (effective_pb / 100.0)))
            amount = max(0, amount - reduced)
            await self.send(f"{c['cyan']}You shrug off {reduced} damage!{c['reset']}")
        
        # Warrior rage gain on damage taken removed — warriors use Combo Chain system
        # Death Pact damage sharing - split damage 50/50 with bonded pet
        if hasattr(self, 'death_pact_target') and self.death_pact_target:
            pet = self.death_pact_target
            if hasattr(pet, 'death_pact_duration') and pet.death_pact_duration > 0 and pet.hp > 0:
                pet_damage = amount // 2
                player_damage = amount - pet_damage
                
                # Pet takes its share
                pet.hp -= pet_damage
                await self.send(f"{c['magenta']}Your death pact splits {pet_damage} damage to {pet.name}!{c['reset']}")
                
                # Check if pet died from the shared damage
                if pet.hp <= 0:
                    # Backlash damage!
                    backlash = int(self.max_hp * 0.2)
                    await self.send(f"{c['bright_red']}Your death pact shatters as {pet.name} falls!{c['reset']}")
                    await self.send(f"{c['bright_red']}Backlash deals {backlash} damage to you!{c['reset']}")
                    amount = player_damage + backlash  # Add backlash to damage
                    
                    # Clear the pact
                    pet.death_pact_master = None
                    pet.death_pact_duration = 0
                    self.death_pact_target = None
                    
                    # Handle pet death
                    if hasattr(pet, 'room') and pet.room:
                        await pet.room.send_to_room(
                            f"{pet.name} crumbles into dust!",
                            exclude=[self]
                        )
                        if pet in pet.room.characters:
                            pet.room.characters.remove(pet)
                    if hasattr(self, 'world') and hasattr(self.world, 'npcs'):
                        if pet in self.world.npcs:
                            self.world.npcs.remove(pet)
                else:
                    amount = player_damage

        # Paladin Protection Aura (nearby allies): 10% damage reduction
        if amount > 0 and 'protection' in self.get_paladin_auras():
            reduced = max(1, int(amount * 0.10))
            amount = max(0, amount - reduced)
            await self.send(f"{c['cyan']}Holy protection absorbs {reduced} damage!{c['reset']}")

        # Paladin Retribution Aura (nearby allies): thorns damage to attacker
        if amount > 0 and attacker and 'retribution' in self.get_paladin_auras():
            thorn = max(2, min(20, int(amount * 0.10)))
            try:
                attacker.hp -= thorn
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{c['magenta']}Retribution burns you for {thorn} damage!{c['reset']}")
                await self.send(f"{c['magenta']}Retribution scorches {attacker.name} for {thorn} damage!{c['reset']}")
                if attacker.hp <= 0 and hasattr(attacker, 'die'):
                    await attacker.die(self)
            except Exception:
                pass
        
        self.hp -= amount

        # Low health warning tip (25% threshold, once per session)
        if self.hp > 0 and self.hp < self.max_hp * 0.25:
            if not getattr(self, '_low_health_tip_shown', False):
                self._low_health_tip_shown = True
                try:
                    from tips import TipManager
                    await TipManager.show_event_tip(self, 'low_health')
                except Exception:
                    pass

        # Auto-flee (wimpy)
        if self.hp > 0 and self.is_fighting:
            wimpy = getattr(self, 'wimpy', 0)
            if wimpy and self.hp <= wimpy:
                try:
                    now = time.time()
                    if now >= getattr(self, 'auto_flee_cooldown_until', 0):
                        self.auto_flee_cooldown_until = now + 3
                        from combat import CombatHandler
                        await CombatHandler.attempt_flee(self, auto=True)
                except Exception:
                    pass

        # Check for autorecall
        if hasattr(self, 'autorecall_hp') and self.autorecall_hp is not None and self.hp > 0:
            threshold = self.autorecall_hp
            if hasattr(self, 'autorecall_is_percent') and self.autorecall_is_percent:
                threshold = int((self.autorecall_hp / 100.0) * self.max_hp)

            if self.hp <= threshold and self.is_fighting:
                # Trigger autorecall
                c = self.config.COLORS
                await self.send(f"\r\n{c['bright_red']}>>> AUTORECALL TRIGGERED <<<{c['reset']}")
                await self.send(f"{c['yellow']}Your HP dropped below {threshold}!{c['reset']}\r\n")

                # Stop fighting
                if self.fighting:
                    self.fighting.fighting = None
                    self.fighting = None
                self.position = 'standing'

                # Recall (same as cmd_recall but without the fighting check)
                recall_room = self.recall_room()

                if recall_room and self.room != recall_room:
                    old_room = self.room
                    if old_room:
                        await old_room.send_to_room(
                            f"{c['bright_cyan']}{self.name} disappears in a flash of light!{c['reset']}",
                            exclude=[self]
                        )
                        old_room.characters.remove(self)

                    self.room = recall_room
                    recall_room.characters.append(self)

                    await self.send(f"{c['bright_cyan']}You recall to safety!{c['reset']}")
                    await self.send("")
                    await recall_room.show_to(self)

                    await recall_room.send_to_room(
                        f"{c['bright_cyan']}{self.name} appears in a flash of light!{c['reset']}",
                        exclude=[self]
                    )

                    # Autorecall succeeded, don't die
                    return False

        if self.hp <= 0:
            await self.die(attacker)
            return True
        return False
        
    async def die(self, killer: 'Character' = None):
        """Handle player death."""
        import random
        c = self.config.COLORS
        # a new death: CombatHandler.handle_death (which runs after this) handles each one once
        self._death_processed = False
        
        # Stop fighting
        if self.fighting:
            self.fighting.fighting = None
            self.fighting = None

        # Reset kill streak
        self.kill_streak = 0

        # Reset Intel on death
        self.intel_target = None
        self.intel_points = 0
        self.intel_thresholds = {}
            
        self.position = 'dead'
        
        # Track deaths
        if not hasattr(self, 'deaths'):
            self.deaths = 0
        self.deaths += 1
        
        # Check death achievements
        try:
            from achievements import AchievementManager
            await AchievementManager.check_death(self)
        except Exception:
            pass

        # Procedural dungeon death handling
        if getattr(self, 'active_dungeon', None):
            from procedural import get_dungeon_manager
            await get_dungeon_manager().on_player_death(self)
        
        # Varied death messages
        death_messages = [
            "You have been KILLED!",
            "Your vision fades to black...",
            "You collapse, defeated!",
            "Death claims you!",
            "You fall into darkness...",
        ]
        await self.send(f"\r\n{c['bright_red']}{random.choice(death_messages)}{c['reset']}")
        await self.send(f"{c['red']}You feel your soul slipping away...{c['reset']}\r\n")
        
        if self.room:
            killer_name = killer.name if killer else "something"
            await self.room.send_to_room(
                f"{c['red']}{self.name} has been slain by {killer_name}!{c['reset']}",
                exclude=[self]
            )
            
        # Scale exp loss by level (lower levels lose less)
        # Level 1-10: 2%, 11-20: 3%, 21-30: 4%, 31+: 5%
        if self.level <= 10:
            exp_percent = 0.02
        elif self.level <= 20:
            exp_percent = 0.03
        elif self.level <= 30:
            exp_percent = 0.04
        else:
            exp_percent = 0.05
            
        exp_loss = int(self.exp * exp_percent)
        self.exp = max(0, self.exp - exp_loss)
        self.last_death = {'exp': exp_loss, 'at': time.time()}     # a resurrection gives it back
        # a death on a marquee quest goes in the quest's log (marquee_log.py: what real quests take)
        try:
            import marquee
            import marquee_log
            _owner, _m, _role = marquee.quest_of(self)
            if _m:
                marquee_log.record('death', self, _m, who=self.name, owner_name=_owner)
        except Exception:
            pass
        if exp_loss > 0:
            await self.send(f"{c['yellow']}You lose {exp_loss} experience points.{c['reset']}")
        
        # Drop gold (5% instead of 10%)
        gold_drop = int(self.gold * 0.05)
        if gold_drop > 0:
            self.gold -= gold_drop
            await self.send(f"{c['yellow']}You drop {gold_drop} gold coins.{c['reset']}")
            
        # Restore with partial HP/mana/move (not just 1)
        self.hp = max(1, self.max_hp // 4)  # 25% HP
        self.mana = max(1, self.max_mana // 4)  # 25% mana
        self.move = max(1, self.max_move // 2)  # 50% move
        self.position = 'standing'
        
        # Clear negative affects on death
        if hasattr(self, 'affects'):
            bad_affects = ['poison', 'blind', 'stun', 'paralyze', 'fear', 'slow']
            if isinstance(self.affects, dict):
                self.affects = {k: v for k, v in self.affects.items() if k not in bad_affects}
            elif isinstance(self.affects, list):
                # Handle both dict affects and Affect objects
                self.affects = [a for a in self.affects if getattr(a, 'name', a.get('name', '') if isinstance(a, dict) else '') not in bad_affects]
        
        # Move to temple/recall point. The removal must be safe: a hunting mob can
        # finish a player whose room list no longer holds them (a dropped
        # connection mid-hunt), and an unguarded remove() here took the whole
        # server down (progression-01 tier runs).
        if self.room and self in self.room.characters:
            self.room.characters.remove(self)
        
        temple = self.recall_room()
        if temple:
            self.room = temple
            temple.characters.append(self)
            
        # the 3D client's death card says what it cost and where you wake (combat_hooks.reward_event)
        try:
            from combat_hooks import reward_event
            reward_event(self, 'fallen', killer=(killer.name if killer else None), exp=int(exp_loss), gold=int(gold_drop),
                         wake=(temple.name if temple else None))
        except Exception:
            pass
        await self.send(f"\r\n{c['white']}You feel yourself being pulled back to the material plane...{c['reset']}")
        await self.send(f"{c['cyan']}The gods have granted you another chance.{c['reset']}\r\n")
        
        # Show death tip for first few deaths
        if self.deaths <= 3:
            try:
                from tips import TipManager
                await TipManager.show_event_tip(self, 'first_death')
            except Exception:
                pass
        await self.do_look([])
        
    async def regen_tick(self):
        """Regenerate HP/mana/move and process affects."""
        # Process bard performance
        await self.process_performance_tick()

        # a ridden mount grows hungry, a point of loyalty every other minute (feeding restores it);
        # a neglected one carries you slower (Mount.travel_bonus)
        if getattr(self, 'mount', None) is not None and hasattr(self.mount, 'tick_loyalty'):
            self._mount_minutes = (getattr(self, '_mount_minutes', 0) or 0) + 1
            if self._mount_minutes % 2 == 0:
                before = self.mount.loyalty
                self.mount.tick_loyalty()
                if before > 25 >= self.mount.loyalty:
                    c = self.config.COLORS
                    await self.send(f"{c['yellow']}{self.mount.name.capitalize()} is hungry and flagging. (feed it){c['reset']}")

        # Warrior Momentum decay out of combat
        if hasattr(self, 'momentum') and self.momentum > 0:
            if not self.is_fighting:
                self.momentum = max(0, self.momentum - 1)

        # Thief Luck decay out of combat
        if hasattr(self, 'luck_points') and self.luck_points > 0:
            if not self.is_fighting and getattr(self, 'char_class', '').lower() == 'thief':
                self.luck_points = max(0, self.luck_points - 1)

        # Warrior Unstoppable rounds decrement (in combat)
        if hasattr(self, 'unstoppable_rounds') and self.unstoppable_rounds > 0:
            if self.is_fighting:
                self.unstoppable_rounds -= 1
                if self.unstoppable_rounds <= 0:
                    c = self.config.COLORS
                    await self.send(f"{c['yellow']}Your Unstoppable state fades.{c['reset']}")

        # Warrior ability buff/shield decay
        if getattr(self, 'warrior_shield_rounds', 0) > 0:
            self.warrior_shield_rounds -= 1
            if self.warrior_shield_rounds <= 0:
                self.warrior_shield = 0
        if getattr(self, 'warrior_dr_rounds', 0) > 0:
            self.warrior_dr_rounds -= 1
            if self.warrior_dr_rounds <= 0:
                self.warrior_dr_bonus = 0
        if getattr(self, 'warrior_temp_armor_rounds', 0) > 0:
            self.warrior_temp_armor_rounds -= 1
            if self.warrior_temp_armor_rounds <= 0:
                self.warrior_temp_armor = 0
        if getattr(self, 'warrior_damage_buff_rounds', 0) > 0:
            self.warrior_damage_buff_rounds -= 1
            if self.warrior_damage_buff_rounds <= 0:
                self.warrior_damage_buff = 0
        if getattr(self, 'warrior_death_save_rounds', 0) > 0:
            self.warrior_death_save_rounds -= 1

        # Mage arcane charge decay out of combat (1 per 15s)
        if hasattr(self, 'arcane_charges') and self.arcane_charges > 0:
            if not self.is_fighting:
                import time as _time
                now = _time.time()
                if now >= getattr(self, 'charge_decay_time', 0):
                    self.arcane_charges = max(0, self.arcane_charges - 1)
                    self.charge_decay_time = now + 15

        # Ranger passive focus gen in combat (+5 per round)
        if hasattr(self, 'focus') and hasattr(self, 'char_class'):
            if self.char_class.lower() == 'ranger' and self.is_fighting:
                old_focus = self.focus
                self.focus = min(100, self.focus + 5)
                c = self.config.COLORS
                for threshold in [25, 50, 75, 100]:
                    if old_focus < threshold <= self.focus:
                        await self.send(f"{c['bright_green']}[Focus: {self.focus}/100]{c['reset']}")
                        break

        # Bard inspiration from performance
        if hasattr(self, 'inspiration') and hasattr(self, 'char_class'):
            if self.char_class.lower() == 'bard' and getattr(self, 'performing', None):
                if self.inspiration < 10:
                    self.inspiration = min(10, self.inspiration + 1)
                    c = self.config.COLORS
                    await self.send(f"{c['bright_yellow']}[Inspiration: {self.inspiration}/10]{c['reset']}")
        
        # Warrior ignore pain tick decay
        if hasattr(self, 'ignore_pain_ticks') and self.ignore_pain_ticks > 0:
            self.ignore_pain_ticks -= 1
            if self.ignore_pain_ticks <= 0:
                self.ignore_pain_absorb = 0
        
        # Song/warcry bonus expiration
        if hasattr(self, 'song_bonuses') and self.song_bonuses:
            expires = self.song_bonuses.get('expires', 0)
            warcry_expires = self.song_bonuses.get('warcry_expires', 0)
            
            if expires > 0:
                self.song_bonuses['expires'] = expires - 1
                if self.song_bonuses['expires'] <= 0:
                    # Clear bard song bonuses
                    for key in ['hitroll', 'damroll', 'haste', 'all_stats', 'xp_bonus', 'source', 'expires']:
                        self.song_bonuses.pop(key, None)
            
            if warcry_expires > 0:
                self.song_bonuses['warcry_expires'] = warcry_expires - 1
                if self.song_bonuses['warcry_expires'] <= 0:
                    # Clear warcry bonuses
                    self.song_bonuses.pop('warcry_hitroll', None)
                    self.song_bonuses.pop('warcry_damroll', None)
                    self.song_bonuses.pop('warcry_expires', None)

        # Position affects regen
        position_mult = {
            'sleeping': 2.0,
            'resting': 1.5,
            'sitting': 1.25,
            'standing': 1.0,
            'fighting': 0.5,
        }
        mult = position_mult.get(self.position, 1.0)

        # Get game time and weather for enhanced regen calculations
        game_time = None
        weather = None
        if hasattr(self, 'world') and self.world:
            game_time = self.world.game_time
            if self.room and self.room.zone and hasattr(self.room.zone, 'weather'):
                weather = self.room.zone.weather

        # Calculate enhanced regeneration
        hp_regen = RegenerationCalculator.calculate_hp_regen(
            self, self.config.HP_REGEN_RATE, mult, game_time, weather
        )
        mana_regen = RegenerationCalculator.calculate_mana_regen(
            self, self.config.MANA_REGEN_RATE, mult, game_time, weather
        )
        move_regen = RegenerationCalculator.calculate_move_regen(
            self, self.config.MOVE_REGEN_RATE, mult, game_time, weather
        )

        # Apply regeneration
        self.hp = min(self.max_hp, self.hp + hp_regen)
        self.mana = min(self.max_mana, self.mana + mana_regen)
        self.move = min(self.max_move, self.move + move_regen)

        # Process hunger and thirst consumption
        await self.hunger_thirst_tick()

    async def minor_regen_tick(self):
        """Small between-tick regeneration (fraction of full regen)."""
        # 10% of normal regen every minor tick
        game_time = self.world.game_time if hasattr(self, 'world') and self.world else None
        weather = None
        if self.room and self.room.zone and hasattr(self.room.zone, 'weather'):
            weather = self.room.zone.weather
        mult = {
            'sleeping': 2.0,
            'resting': 1.5,
            'sitting': 1.25,
            'standing': 1.0,
            'fighting': 0.5,
        }.get(self.position, 1.0)
        hp_regen = int(RegenerationCalculator.calculate_hp_regen(
            self, self.config.HP_REGEN_RATE * 0.10, mult, game_time, weather
        ))
        mana_regen = int(RegenerationCalculator.calculate_mana_regen(
            self, self.config.MANA_REGEN_RATE * 0.10, mult, game_time, weather
        ))
        move_regen = int(RegenerationCalculator.calculate_move_regen(
            self, self.config.MOVE_REGEN_RATE * 0.10, mult, game_time, weather
        ))
        self.hp = min(self.max_hp, self.hp + hp_regen)
        self.mana = min(self.max_mana, self.mana + mana_regen)
        self.move = min(self.max_move, self.move + move_regen)

    async def process_performance_tick(self):
        """Process bard performance effects each tick."""
        if not self.performing:
            return
        
        c = self.config.COLORS
        
        from spells import BARD_SONGS
        import random
        
        song = BARD_SONGS.get(self.performing)
        if not song:
            self.performing = None
            return
        
        # Calculate mana cost (doubled during encore)
        mana_cost = song['mana_per_tick']
        if self.encore_active:
            mana_cost *= 2
        
        # Check if we have enough mana
        if self.mana < mana_cost:
            await self.send(f"{c['yellow']}You run out of energy to continue your performance!{c['reset']}")
            await self._end_performance()
            return
        
        # Drain mana
        self.mana -= mana_cost
        self.performance_ticks += 1
        
        # Process encore duration
        if self.encore_active:
            self.encore_ticks -= 1
            if self.encore_ticks <= 0:
                self.encore_active = False
                await self.send(f"{c['cyan']}Your encore fades back to normal performance.{c['reset']}")
        
        # Calculate effect multiplier (an encore doubles it; a worn instrument's song power adds
        # a tenth per point: the Lyre of Orbits' 5 sings half again as strong)
        effect_mult = 2.0 if self.encore_active else 1.0
        effect_mult *= 1 + max(0, self.get_equipment_bonus('song_power')) / 10
        
        # Apply song effects based on target type
        target_type = song.get('target', 'allies')
        
        if target_type == 'allies':
            await self._apply_song_to_allies(song, effect_mult)
        elif target_type == 'enemies':
            await self._apply_song_to_enemies(song, effect_mult)
        
        # Tick message (every 3 ticks)
        if self.performance_ticks % 3 == 0:
            await self.send(f"{c['bright_magenta']}{song.get('tick_self', '♪ You continue performing... ♪')}{c['reset']}")
            if self.room:
                await self.room.send_to_room(
                    song.get('tick_room', '♪ $n continues performing... ♪').replace('$n', self.name),
                    exclude=[self]
                )

    async def _apply_song_to_allies(self, song, effect_mult):
        """Apply beneficial song effects to allies in the room."""
        if not self.room:
            return
        
        c = self.config.COLORS
        
        # Check if song only works out of combat
        if song.get('combat_only') == False and self.is_fighting:
            await self.send(f"{c['yellow']}Your song of rest has no effect during combat.{c['reset']}")
            return
        
        affects = song.get('affects', [])
        
        for char in self.room.characters:
            # Skip enemies (mobs that are hostile or fighting us)
            from mobs import Mobile
            if isinstance(char, Mobile) and (char.is_fighting or getattr(char, 'is_hostile', False)):
                continue
            
            # Apply effects
            for affect in affects:
                affect_type = affect['type']
                value = int(affect['value'] * effect_mult)
                
                if affect_type == 'hitroll':
                    # Temporary combat bonus (applied in combat calculations)
                    if not hasattr(char, 'song_bonuses'):
                        char.song_bonuses = {}
                    char.song_bonuses['hitroll'] = value
                    char.song_bonuses['source'] = self.name
                    char.song_bonuses['expires'] = 2  # Expires in 2 ticks if not refreshed
                
                elif affect_type == 'damroll':
                    if not hasattr(char, 'song_bonuses'):
                        char.song_bonuses = {}
                    char.song_bonuses['damroll'] = value
                    char.song_bonuses['expires'] = 2
                
                elif affect_type == 'haste':
                    if not hasattr(char, 'song_bonuses'):
                        char.song_bonuses = {}
                    char.song_bonuses['haste'] = value
                    char.song_bonuses['expires'] = 2
                
                elif affect_type == 'hp_regen':
                    # Bonus regeneration (percentage)
                    if not self.is_fighting:
                        regen_bonus = int((char.max_hp * value / 100) * 0.05)  # 50% of normal 5% regen
                        char.hp = min(char.max_hp, char.hp + regen_bonus)
                
                elif affect_type == 'mana_regen':
                    if not self.is_fighting:
                        regen_bonus = int((char.max_mana * value / 100) * 0.05)
                        char.mana = min(char.max_mana, char.mana + regen_bonus)
                
                elif affect_type == 'move_regen':
                    if not self.is_fighting:
                        regen_bonus = int((char.max_move * value / 100) * 0.05)
                        char.move = min(char.max_move, char.move + regen_bonus)
                
                elif affect_type == 'all_stats':
                    if not hasattr(char, 'song_bonuses'):
                        char.song_bonuses = {}
                    char.song_bonuses['all_stats'] = value
                    char.song_bonuses['expires'] = 2
                
                elif affect_type == 'xp_bonus':
                    if not hasattr(char, 'song_bonuses'):
                        char.song_bonuses = {}
                    char.song_bonuses['xp_bonus'] = value
                    char.song_bonuses['expires'] = 2

    async def _apply_song_to_enemies(self, song, effect_mult):
        """Apply debuff song effects to enemies in the room."""
        if not self.room:
            return
        
        c = self.config.COLORS
        import random
        
        from mobs import Mobile
        
        affects = song.get('affects', [])
        special = song.get('special')
        damage_dice = song.get('damage_per_tick')
        
        for char in self.room.characters:
            # Only affect mobs
            if not isinstance(char, Mobile):
                continue
            
            # Apply stat debuffs
            for affect in affects:
                affect_type = affect['type']
                value = int(affect['value'] * effect_mult)
                
                if affect_type in ('hitroll', 'damroll', 'saving_throw'):
                    if not hasattr(char, 'song_debuffs'):
                        char.song_debuffs = {}
                    char.song_debuffs[affect_type] = value
                    char.song_debuffs['expires'] = 2
                
                elif affect_type == 'fumble':
                    if not hasattr(char, 'song_debuffs'):
                        char.song_debuffs = {}
                    char.song_debuffs['fumble'] = value
                    char.song_debuffs['expires'] = 2
                
                elif affect_type == 'deafen':
                    # Chance to deafen
                    if random.randint(1, 100) <= value:
                        from affects import AffectManager
                        affect_data = {
                            'name': 'deafened',
                            'type': AffectManager.TYPE_FLAG,
                            'applies_to': 'deafened',
                            'value': 1,
                            'duration': 3,
                            'caster_level': self.level
                        }
                        AffectManager.apply_affect(char, affect_data)
                        await self.send(f"{c['bright_cyan']}{char.name} is deafened by your symphony!{c['reset']}")
            
            # Handle special effects
            if special == 'sleep':
                # Lullaby - cumulative sleep chance
                target_id = id(char)
                if target_id not in self.lullaby_saves:
                    self.lullaby_saves[target_id] = 0
                
                penalty = song.get('save_penalty_per_tick', 5)
                self.lullaby_saves[target_id] += penalty
                
                # Base 30% chance + cumulative penalty
                sleep_chance = 30 + self.lullaby_saves[target_id]
                if random.randint(1, 100) <= sleep_chance:
                    from affects import AffectManager
                    affect_data = {
                        'name': 'sleep',
                        'type': AffectManager.TYPE_FLAG,
                        'applies_to': 'sleeping',
                        'value': 1,
                        'duration': 3 + (self.level // 10),
                        'caster_level': self.level
                    }
                    AffectManager.apply_affect(char, affect_data)
                    char.position = 'sleeping'
                    await self.send(f"{c['bright_magenta']}{char.name} falls asleep to your lullaby!{c['reset']}")
                    if self.room:
                        await self.room.send_to_room(
                            f"{char.name} falls asleep!",
                            exclude=[self]
                        )
                    # Remove from combat
                    if char.is_fighting:
                        char.fighting = None
                        char.fighting = None
            
            elif special == 'sonic_damage':
                # Symphony of destruction - deal damage
                if damage_dice:
                    damage = self._roll_dice(damage_dice)
                    damage = int(damage * effect_mult)
                    await self.send(f"{c['bright_red']}Your symphony tears at {char.name}! [{damage}]{c['reset']}")
                    killed = await char.take_damage(damage, self)
                    if killed:
                        from combat import CombatHandler
                        await CombatHandler.handle_death(self, char)

    def _roll_dice(self, dice_str: str) -> int:
        """Roll dice from string like '2d6'."""
        import random
        try:
            if '+' in dice_str:
                dice_part, bonus = dice_str.split('+')
                bonus = int(bonus)
            else:
                dice_part = dice_str
                bonus = 0
            
            num, sides = dice_part.split('d')
            total = sum(random.randint(1, int(sides)) for _ in range(int(num)))
            return total + bonus
        except Exception:
            return random.randint(1, 6)

    async def _end_performance(self):
        """End the current performance."""
        from spells import BARD_SONGS
        c = self.config.COLORS
        
        song = BARD_SONGS.get(self.performing, {})
        
        await self.send(f"{c['cyan']}{song.get('end_self', 'Your song ends.')}{c['reset']}")
        if self.room:
            await self.room.send_to_room(
                song.get('end_room', '$n stops playing.').replace('$n', self.name),
                exclude=[self]
            )
        
        self.performing = None
        self.performance_ticks = 0
        self.encore_active = False
        self.encore_ticks = 0
        self.lullaby_saves = {}

    async def hunger_thirst_tick(self):
        """Process hunger and thirst consumption based on game time (1 point per game hour)."""
        c = self.config.COLORS

        # Get current game time
        if not hasattr(self, 'world') or not self.world or not hasattr(self.world, 'game_time'):
            return

        from msgkind import send_ui
        current_hour = self.world.game_time.total_hours()
        # only the hours lived through drain: a new character, one back from away, or a clock
        # set back starts counting from now
        for attr in ('last_hunger_hour', 'last_thirst_hour'):
            last = getattr(self, attr, 0) or 0
            if last <= 0 or not 0 <= current_hour - last <= 2:
                setattr(self, attr, current_hour)

        # Decrease hunger by 1 per game hour (hungry after 24 hours, starving after 1 week)
        if current_hour != self.last_hunger_hour:
            hours_passed = current_hour - self.last_hunger_hour
            if hours_passed > 0:
                self.hunger = max(0, self.hunger - hours_passed)
                self.last_hunger_hour = current_hour

                # Warnings and penalties based on hunger level
                if self.hunger == 0:
                    await send_ui(self, f"{c['red']}You are starving! Your strength wanes.{c['reset']}")
                    # Starving: apply debuff (reduced regen, -2 STR) instead of damage
                    # Debuff is checked in regen/combat — no HP loss from hunger

                elif self.hunger <= 24:  # Less than 1 day of food
                    if self.hunger == 24:
                        await send_ui(self, f"{c['yellow']}You are extremely hungry!{c['reset']}")

                elif self.hunger <= 48:  # Less than 2 days of food
                    if self.hunger == 48:
                        await send_ui(self, f"{c['yellow']}You are hungry.{c['reset']}")

        # Decrease thirst by 1 per game hour (critical after 2.5 days = 60 hours)
        if current_hour != self.last_thirst_hour:
            hours_passed = current_hour - self.last_thirst_hour
            if hours_passed > 0:
                self.thirst = max(0, self.thirst - hours_passed)
                self.last_thirst_hour = current_hour

                # Warnings and penalties based on thirst level
                if self.thirst == 0:
                    await send_ui(self, f"{c['bright_red']}You are parched! Your focus falters.{c['reset']}")
                    # Dehydrated: apply debuff (reduced regen, -2 DEX) instead of damage
                    # Debuff is checked in regen/combat — no HP loss from thirst

                elif self.thirst <= 12:  # Less than half day of water
                    if self.thirst == 12:
                        await send_ui(self, f"{c['yellow']}You are extremely thirsty!{c['reset']}")

                elif self.thirst <= 24:  # Less than 1 day of water
                    if self.thirst == 24:
                        await send_ui(self, f"{c['yellow']}You are thirsty.{c['reset']}")

    def get_hunger_condition(self) -> str:
        """Get description of hunger condition (max 168 hours = 1 week)."""
        if self.hunger == 0:
            return "Starving"
        elif self.hunger <= 24:  # Less than 1 day
            return "Famished"
        elif self.hunger <= 48:  # 1-2 days
            return "Hungry"
        elif self.hunger <= 84:  # 2-3.5 days
            return "Peckish"
        else:
            return "Satiated"

    def get_thirst_condition(self) -> str:
        """Get description of thirst condition (max 60 hours = 2.5 days)."""
        if self.thirst == 0:
            return "Parched"
        elif self.thirst <= 12:  # Less than half day
            return "Dehydrated"
        elif self.thirst <= 24:  # 12-24 hours
            return "Thirsty"
        elif self.thirst <= 36:  # 1-1.5 days
            return "Dry"
        else:
            return "Quenched"

    async def improve_skill(self, skill_name: str, difficulty: int = 5):
        """Attempt to improve a skill through use.

        Args:
            skill_name: Name of the skill to improve
            difficulty: Base difficulty (1-10, higher = harder to improve)
        """
        c = self.config.COLORS

        # Check if player has the skill
        if skill_name not in self.skills:
            return

        current_prof = self.skills[skill_name]

        # Can't improve past 95% through use (need practice for last 5%)
        if current_prof >= 95:
            return

        # Calculate improvement chance
        # Lower proficiency = easier to improve
        # Higher difficulty = harder to improve
        base_chance = max(1, 15 - difficulty - (current_prof // 10))

        # Roll for improvement
        if random.randint(1, 100) <= base_chance:
            improvement = random.randint(1, 3)
            old_prof = current_prof
            self.skills[skill_name] = min(95, current_prof + improvement)

            await self.send(f"{c['green']}You feel more skilled at {skill_name.replace('_', ' ')}! ({old_prof}% -> {self.skills[skill_name]}%){c['reset']}")

    async def improve_spell(self, spell_name: str):
        """Attempt to improve a spell through casting.

        Args:
            spell_name: Name of the spell to improve
        """
        c = self.config.COLORS

        # Check if player has the spell
        if spell_name not in self.spells:
            return

        current_prof = self.spells[spell_name]

        # Can't improve past 95% through use (need practice for last 5%)
        if current_prof >= 95:
            return

        # Calculate improvement chance (harder to improve spells than skills)
        base_chance = max(1, 10 - (current_prof // 12))

        # Roll for improvement
        if random.randint(1, 100) <= base_chance:
            improvement = random.randint(1, 2)
            old_prof = current_prof
            self.spells[spell_name] = min(95, current_prof + improvement)

            await self.send(f"{c['bright_cyan']}Your knowledge of {spell_name.replace('_', ' ')} deepens! ({old_prof}% -> {self.spells[spell_name]}%){c['reset']}")


# a player's attributes and maxima count their worn gear (GEAR_STATS); installed after the class
# so the class body keeps the builtin str() and int()
for _name in GEAR_STATS:
    setattr(Player, _name, _gear_stat(_name))
del _name
