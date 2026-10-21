"""
Misthollow Mobiles (NPCs)
========================
Non-player characters and monsters.
"""

import random
import time
import logging
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from world import World, Room

from config import Config
import re as _re
from player import Character
from affects import AffectManager
from regeneration import RegenerationCalculator


def zone_of(room):
    """The zone a room belongs to (world.zone_of: its zone file, not its vnum)."""
    from world import zone_of as _zone_of
    return _zone_of(room)


WATER_SECTORS = ('water_swim', 'water_noswim', 'water_surface')
KEEP_OUT = {'no_mob', 'imm_only'}     # rooms creatures never step into (no creatures; the God Rooms)
# townsfolk keep a day (docs/GAMEPLAY_POLISH.md, group 3): the streets they walk, the houses they
# go into at night
TOWN_LOOKS = {'city', 'village', 'camp', 'garden', 'terrace'}
# how far (rooms from where the chase began) a hunter follows before it gives up, heals and
# turns back home (the owner: "after a certain range they should stop chasing")
LEASH = {'hunter': 3, 'tracker': 5, 'boss': 6}

logger = logging.getLogger('Misthollow.Mobs')

# Equipment tables (vnums from zone_030_circlemud.json)
EQUIPMENT_TIERS = {
    'basic': {
        'weapons': {
            'warrior': [10, 12, 14],
            'mage': [34, 11],
            'rogue': [11, 14],
            'ranger': [13, 10],
            'cleric': [12],
            'default': [10, 11, 12, 13, 14],
        },
        'armor': {
            'guard': [30, 37, 32, 33],
            'warrior': [37, 30],
            'mage': [35],
            'rogue': [39],
            'ranger': [37],
            'cleric': [35],
            'default': [37],
            'clothes': [35],
        },
    },
    'intermediate': {
        'weapons': {
            'warrior': [80, 100, 101, 102, 105, 107, 108],
            'mage': [43, 109, 34],
            'rogue': [48, 86, 103, 106],
            'ranger': [104, 100, 108],
            'cleric': [91, 102],
            'default': [80, 100, 101, 102, 103, 104, 105, 107, 108, 109],
        },
        'armor': {
            'guard': [83, 81, 117, 82],
            'warrior': [81, 83],
            'mage': [44, 35],
            'rogue': [41, 49],
            'ranger': [41, 39],
            'cleric': [35, 44],
            'default': [81],
            'clothes': [35, 44],
        },
    },
    'advanced': {
        'weapons': {
            'warrior': [84, 101, 105, 107],
            'mage': [43, 109],
            'rogue': [88, 86, 106],
            'ranger': [104, 108],
            'cleric': [91, 102],
            'default': [84, 88, 91, 101, 105, 107],
        },
        'armor': {
            'guard': [115, 111, 117, 113],
            'warrior': [111, 115],
            'mage': [90, 44],
            'rogue': [87, 49],
            'ranger': [112, 87],
            'cleric': [90],
            'default': [111],
            'clothes': [90],
        },
    },
    'elite': {
        'weapons': {
            'warrior': [84, 101, 105, 107],
            'mage': [43, 109],
            'rogue': [88],
            'ranger': [104],
            'cleric': [91],
            'default': [84, 88, 91, 101, 105, 107],
        },
        'armor': {
            'guard': [115, 85, 117, 113, 118],
            'warrior': [85, 115, 119],
            'mage': [90, 89],
            'rogue': [87, 89],
            'ranger': [112, 118],
            'cleric': [90, 118],
            'default': [85],
            'clothes': [90],
        },
    },
}

EXTRA_LOOT_TABLES = {
    'basic': [200, 201],
    'intermediate': [202, 203, 204, 205],
    'advanced': [210, 211, 212, 213],
    'elite': [214, 215, 216, 217],
}


def spared(char) -> bool:
    """An immortal creatures leave alone: nohassle ("Mobs will ignore you") or wizinvis."""
    return bool(getattr(char, 'nohassle', False) or getattr(char, 'wizinvis', False))


class Mobile(Character):
    """Non-player character (mob)."""
    
    def __init__(self, vnum: int, world: 'World'):
        super().__init__()
        self.vnum = vnum
        self.world = world
        self.config = Config()

        # Loot/equipment metadata
        self.role = None
        self.mob_class = None
        self.loot_table = []
        self.loot_chance = 0
        
        # Mob-specific attributes
        self.short_desc = "a generic mob"
        self.long_desc = "A generic mob stands here."
        self.description = ""
        self.keywords = []  # List of keywords for targeting
        
        # Behavior flags
        self.flags = set()
        self.special = None  # Special behavior (shopkeeper, healer, etc.)

        # Faction (used by faction_aggressive_ai)
        self.faction = None
        self.faction_rep = None
        
        # AI state
        self.hate_list = []  # Characters this mob is angry at
        self.memory = {}  # Remember things about players
        self.home_room = None
        self.home_zone = None  # Zone number this mob belongs to
        self.ai_config = {}  # AI configuration (patrol routes, behaviors, etc.)
        self.ai_state = {}  # Runtime AI state (patrol index, buffed status, etc.)
        self.ai_controller = None  # AIController instance
        
        # Hunting AI state
        self.grudge_list = {}  # {player_name: {'target': player, 'time': timestamp, 'damage': total_damage}}
        self.hunting_target = None  # Currently hunting this player
        self.hunt_cooldown = 0  # Ticks until can move again while hunting
        self.last_known_room = None  # Last room we saw the target in

        # Combat
        self.damage_dice = '1d4'
        
    @staticmethod
    def said_name(name: str, short: str) -> Optional[str]:
        """What a creature is called in play when its name is a list of keywords ("ogre wandering
        brute giant", the build-out's way): its description ("a wandering ogre"). None when the name
        already reads as one: a single word ("rat") or the description itself."""
        name, short = (name or '').strip(), (short or '').strip()
        if len(name.split()) < 2 or not short or short.endswith(('.', '!')):
            return None
        bare = _re.sub(r'^(a|an|the|some)\s+', '', short, flags=_re.I)
        return None if name.lower() in (short.lower(), bare.lower()) else short

    @staticmethod
    def apply_prototype(mob: 'Mobile', proto: dict, world: 'World') -> 'Mobile':
        """Apply prototype data onto an existing mob instance."""
        mob.name = proto.get('name', 'a creature')
        mob.short_desc = proto.get('short_desc', mob.name)
        # a name written as keywords is said as the description (chat, combat lines, corpses); the
        # words stay its keywords, for targeting, reputation and the 3D body (keyword_name)
        mob.keyword_name = mob.name
        mob.name = Mobile.said_name(mob.name, mob.short_desc) or mob.name
        mob.long_desc = proto.get('long_desc', f"{mob.name} is here.")
        mob.description = proto.get('description', '')
        # a zone's population (population.py): its rank, the route it walks, who it calls when hit
        mob.rank = proto.get('rank')
        mob.patrol_route = list(proto.get('patrol_route') or []) or None
        mob.helpers = proto.get('helpers')

        # Generate keywords from name, short_desc, and long_desc for better targeting
        # Remove common articles/verbs and split into words
        stop_words = {'a', 'an', 'the', 'is', 'are', 'its', 'it', 'of', 'and', 'or',
                      'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from', 'up', 'out',
                      'as', 'into', 'through', 'here', 'there', 'this', 'that', 'has',
                      'was', 'were', 'been', 'being', 'have', 'had', 'having', 'do',
                      'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
                      'shall', 'can', 'stands', 'sitting', 'standing', 'drifts', 'lurks',
                      'walks', 'paces', 'hovers', 'floats', 'lies', 'rests'}
        keywords = set()
        for text in [mob.keyword_name, mob.short_desc, mob.long_desc]:
            words = text.lower().replace(',', '').replace('.', '').replace('!', '').replace("'", '').split()
            for word in words:
                if word not in stop_words and len(word) > 2:
                    keywords.add(word)
        # Also add explicit keywords from zone data if present
        if proto.get('keywords'):
            for kw in proto['keywords']:
                keywords.add(kw.lower())
        mob.keywords = list(keywords)

        mob.level = proto.get('level', 1)
        mob.alignment = proto.get('alignment', 0)
        mob.gold = proto.get('gold', 0)
        mob.exp = proto.get('exp', mob.level * 100)

        # Parse HP: use explicit max_hp if set, otherwise roll hp_dice
        explicit_hp = proto.get('max_hp', 0)
        if explicit_hp and explicit_hp > 0:
            mob.max_hp = explicit_hp
        else:
            hp_dice = proto.get('hp_dice', f'{mob.level}d10+{mob.level * 5}')
            mob.max_hp = Mobile.roll_dice(hp_dice)
        mob.hp = mob.max_hp

        # Mana and movement
        mob.max_mana = mob.level * 10
        mob.mana = mob.max_mana
        mob.max_move = 100
        mob.move = mob.max_move

        # Parse damage dice
        mob.damage_dice = proto.get('damage_dice', '1d6')

        # Stats based on level
        mob.str = 10 + mob.level // 5
        mob.int = 10 + mob.level // 5
        mob.wis = 10 + mob.level // 5
        mob.dex = 10 + mob.level // 5
        mob.con = 10 + mob.level // 5
        mob.cha = 10 + mob.level // 5

        # Armor class: use zone data if present (zone files say `armor_class`; a few older ones
        # `ac`), otherwise derive from level
        mob.armor_class = proto.get('armor_class', proto.get('ac', 100 - mob.level * 2))

        # Hitroll and damroll from zone data (default to level-based)
        mob.hitroll = proto.get('hitroll', mob.level // 2)
        mob.damroll = proto.get('damroll', mob.level // 3)

        # Flags
        mob.flags = set(proto.get('flags', []))
        mob.special = proto.get('special')
        # service NPCs hold their post: a guildmaster who wanders into the
        # sewers (or chases someone there) breaks the whole guild
        if mob.special in ('guildmaster', 'trainer', 'shopkeeper', 'healer', 'banker', 'postmaster'):
            mob.flags.add('sentinel')
        mob.talk_responses = proto.get('talk_responses', {})
        mob.trains_class = proto.get('trains_class')  # For guildmasters

        # Companion hire data
        mob.hireable = proto.get('hireable', False)
        mob.companion_type = proto.get('companion_type')
        mob.companion_level = proto.get('companion_level', mob.level)
        mob.hire_cost = proto.get('hire_cost')
        mob.upkeep_cost = proto.get('upkeep_cost')
        mob.companion_scale = proto.get('companion_scale', True)

        # Faction reputation metadata
        mob.faction = proto.get('faction')
        mob.faction_rep = proto.get('faction_rep')  # int or dict for multi-faction impacts
        mob.min_rep_talk = proto.get('min_rep_talk')
        mob.min_rep_talk_level = proto.get('min_rep_talk_level')
        mob.min_rep_shop = proto.get('min_rep_shop')
        mob.min_rep_shop_level = proto.get('min_rep_shop_level')

        # Load AI configuration
        mob.ai_config = proto.get('ai_config', {})

        # Create AI controller if AI config exists
        if mob.ai_config:
            from ai import AIController
            mob.ai_controller = AIController.create_from_config(mob, mob.ai_config)

        # Load equipment
        equipment_data = proto.get('equipment', {})
        if equipment_data:
            from objects import create_object, create_preset_object
            for slot, obj_vnum in equipment_data.items():
                # Create object from vnum using the objects module function
                obj = create_object(obj_vnum, world) or create_preset_object(obj_vnum)
                if obj:
                    mob.equipment[slot] = obj

        # Random equipment rolls (optional)
        equip_rolls = proto.get('equipment_rolls', [])
        if equip_rolls:
            from objects import create_object, create_preset_object
            import random
            for roll in equip_rolls:
                vnum = roll.get('vnum')
                slot = roll.get('slot')
                chance = roll.get('chance', 100)
                if vnum and slot and random.randint(1, 100) <= chance:
                    obj = create_object(vnum, world) or create_preset_object(vnum)
                    if obj:
                        mob.equipment[slot] = obj

        # gear the zone gave them by name is shown on their body in /play (gear_look.py)
        mob.own_gear = bool(mob.equipment)

        # Auto-equip if no explicit equipment provided
        if not equipment_data and proto.get('auto_equip', True):
            mob.auto_equip(proto)

        # What the zone gave it to carry (keys, coins, gear: dropped when it dies) and the drops
        # its zone wrote for it (each at its chance). Both lay unread until Push 32, so nothing a
        # zone handed a creature ever dropped. A shopkeeper's wares are its shop, not its pockets.
        if not getattr(mob, '_proto_loaded', False):
            mob._proto_loaded = True
            from objects import create_object, create_preset_object
            if not (proto.get('shop_config') and mob.special == 'shopkeeper'):
                for entry in proto.get('inventory') or []:
                    vnum = entry.get('vnum') if isinstance(entry, dict) else entry
                    try:
                        vnum = int(vnum)
                    except (TypeError, ValueError):
                        continue
                    obj = create_object(vnum, world) or create_preset_object(vnum)
                    if obj and getattr(obj, 'item_type', '') not in ('fountain', 'furniture'):
                        mob.inventory.append(obj)
            if proto.get('loot_table'):
                mob.loot_table = list(proto['loot_table'])
                mob.loot_chance = proto.get('loot_chance', 20)

        # Ensure loot table exists for NPCs
        if not mob.loot_table:
            tier = mob.get_level_tier(mob.level)
            mob.loot_table = EXTRA_LOOT_TABLES.get(tier, EXTRA_LOOT_TABLES['basic'])
            mob.loot_chance = 20

        # Initialize shop if this mob is a shopkeeper
        shop_config = proto.get('shop_config')
        if shop_config and mob.special == 'shopkeeper':
            from shops import ShopManager
            ShopManager.create_shop(mob, shop_config, world)

        return mob

    @classmethod
    def from_prototype(cls, proto: dict, world: 'World') -> 'Mobile':
        """Create a mobile from a prototype dictionary."""
        mob = cls(proto.get('vnum', 0), world)
        return cls.apply_prototype(mob, proto, world)
        
    @staticmethod
    def roll_dice(dice_str: str) -> int:
        """Roll dice from a string like '2d6+4'."""
        try:
            if '+' in dice_str:
                dice_part, bonus = dice_str.split('+')
                bonus = int(bonus)
            elif '-' in dice_str:
                dice_part, penalty = dice_str.split('-')
                bonus = -int(penalty)
            else:
                dice_part = dice_str
                bonus = 0
                
            num_dice, die_size = dice_part.split('d')
            num_dice = int(num_dice)
            die_size = int(die_size)
            
            total = sum(random.randint(1, die_size) for _ in range(num_dice))
            return max(1, total + bonus)
            
        except Exception:
            return random.randint(10, 50)

    @staticmethod
    def get_level_tier(level: int) -> str:
        if level <= 10:
            return 'basic'
        if level <= 20:
            return 'intermediate'
        if level <= 30:
            return 'advanced'
        return 'elite'

    @staticmethod
    def detect_role_and_class(proto: dict, mob: 'Mobile') -> (str, str, bool):
        name = f"{mob.name} {mob.short_desc}".lower()
        flags = set(proto.get('flags', []))

        role = proto.get('role') or proto.get('mob_role') or ''
        if not role:
            if mob.special == 'shopkeeper':
                role = 'shopkeeper'
            elif 'guard' in name or 'guardian' in name or 'cityguard' in name:
                role = 'guard'
            else:
                role = 'monster'

        mob_class = proto.get('class') or proto.get('mob_class') or proto.get('char_class') or ''
        if not mob_class:
            if 'caster' in flags or mob.special in ('necromancer', 'shaman', 'druid'):
                mob_class = 'mage'
            elif any(k in name for k in ['mage', 'wizard', 'sorcerer']):
                mob_class = 'mage'
            elif any(k in name for k in ['cleric', 'priest', 'paladin']):
                mob_class = 'cleric'
            elif any(k in name for k in ['ranger', 'archer', 'hunter']):
                mob_class = 'ranger'
            elif any(k in name for k in ['thief', 'assassin', 'rogue', 'bandit']):
                mob_class = 'rogue'
            else:
                mob_class = 'warrior'

        is_boss = bool(proto.get('boss')) or 'boss' in flags or 'boss' in name
        if not is_boss and mob.level >= 30 and any(k in name for k in ['dragon', 'lord', 'queen', 'king', 'overlord', 'demon', 'arch']):
            is_boss = True

        return role, mob_class, is_boss

    def equip_object(self, obj):
        """Equip an object into the appropriate slot."""
        if not obj:
            return
        if getattr(obj, 'item_type', None) == 'weapon':
            if 'wield' not in self.equipment:
                self.equipment['wield'] = obj
            return
        if getattr(obj, 'item_type', None) == 'armor' and getattr(obj, 'wear_slot', None):
            if obj.wear_slot not in self.equipment:
                self.equipment[obj.wear_slot] = obj

    def auto_equip(self, proto: dict):
        """Assign equipment based on role/class/level."""
        role, mob_class, is_boss = self.detect_role_and_class(proto, self)
        self.role = role
        self.mob_class = mob_class

        tier = self.get_level_tier(self.level)
        tier_data = EQUIPMENT_TIERS.get(tier, EQUIPMENT_TIERS['basic'])

        if role == 'shopkeeper':
            armor_list = tier_data['armor'].get('clothes', [])
            if armor_list:
                from objects import create_object, create_preset_object
                armor_vnum = random.choice(armor_list)
                obj = create_object(armor_vnum, self.world) or create_preset_object(armor_vnum)
                self.equip_object(obj)
            return

        # Guards get armor + weapon
        if role == 'guard':
            weapon_list = tier_data['weapons'].get(mob_class, tier_data['weapons']['default'])
            armor_list = tier_data['armor'].get('guard', [])
        else:
            weapon_list = tier_data['weapons'].get(mob_class, tier_data['weapons']['default'])
            armor_list = tier_data['armor'].get(mob_class, tier_data['armor']['default'])

        if is_boss and tier != 'elite':
            tier = 'elite'
            tier_data = EQUIPMENT_TIERS['elite']
            weapon_list = tier_data['weapons'].get(mob_class, tier_data['weapons']['default'])
            armor_list = tier_data['armor'].get('guard' if role == 'guard' else mob_class, tier_data['armor']['default'])

        from objects import create_object, create_preset_object
        if weapon_list and 'wield' not in self.equipment:
            weapon_vnum = random.choice(weapon_list)
            weapon = create_object(weapon_vnum, self.world) or create_preset_object(weapon_vnum)
            self.equip_object(weapon)

        # Equip armor pieces (if any)
        for armor_vnum in armor_list:
            if len(self.equipment) > 6:
                break
            armor = create_object(armor_vnum, self.world) or create_preset_object(armor_vnum)
            self.equip_object(armor)

        # Bosses get an extra special item
        if is_boss:
            for extra_vnum in [118, 220]:
                extra = create_object(extra_vnum, self.world) or create_preset_object(extra_vnum)
                self.equip_object(extra)

        # Loot tables for extra drops
        self.loot_table = EXTRA_LOOT_TABLES.get(tier, EXTRA_LOOT_TABLES['basic'])
        self.loot_chance = 50 if is_boss else 20
            
    async def process_ai(self):
        """Process mob AI behaviors."""
        if not self.is_alive:
            return

        if self.position in ('sleeping', 'stunned', 'incapacitated'):
            return

        # Use advanced AI controller if available
        if self.ai_controller:
            await self.ai_controller.process()
            return

        # Otherwise, use simple fallback AI
        # While fighting, combat actions are owned EXCLUSIVELY by mob_ai_tick
        # (world.combat_tick, once per 4s round). process_ai runs every 0.1s
        # tick, so calling combat_ai here rolled specials/spells ~10x/sec on
        # top of the round AI — mobs double-acted wildly.
        if self.is_fighting:
            return

        # a chase it gave up: it walks back to where the chase began
        if getattr(self, 'returning', None) is not None:
            if await self._return_home():
                return

        # Hunting AI - track players who attacked us
        if await self.hunting_ai():
            return

        # Trapsmiths rig their lair while idle (~once per 30s of ticks)
        if self.room and random.random() < 0.003:
            try:
                from mob_ai import classify_mob
                if 'trapsmith' in classify_mob(self) and not getattr(self.room, 'mob_traps', None):
                    from environment import mob_rig_trap
                    await mob_rig_trap(self, self.room)
                    return
            except Exception:
                pass

        # Tracking AI - follow detected sneaking targets briefly
        import time
        track_target = self.ai_state.get('track_target') if hasattr(self, 'ai_state') else None
        track_until = self.ai_state.get('track_until', 0) if hasattr(self, 'ai_state') else 0
        if track_target and time.time() < track_until and track_target.is_alive:
            # Do not move if sentinel
            if 'sentinel' not in self.flags and self.room and track_target.room and track_target.room != self.room:
                # If target is in adjacent room, move there
                for direction, exit_data in self.room.exits.items():
                    if exit_data and exit_data.get('room') == track_target.room and not (KEEP_OUT & track_target.room.flags):
                        old_room = self.room
                        await old_room.send_to_room(f"{self.name} slips {direction}, tracking a scent.")
                        if self in old_room.characters:
                            old_room.characters.remove(self)
                        self.room = exit_data['room']
                        self.room.characters.append(self)
                        await self.room.send_to_room(f"{self.name} arrives, eyes scanning the shadows.")
                        opposite = self.config.DIRECTIONS.get(direction, {}).get('opposite', 'somewhere')
                        await self._notify_move(old_room, self.room, direction, opposite)
                        return
            # If target is in same room, let normal AI handle aggression
        else:
            if hasattr(self, 'ai_state'):
                self.ai_state.pop('track_target', None)
                self.ai_state.pop('track_until', None)

        # Hostile faction attack on sight
        if await self.faction_aggressive_ai():
            return

        # a patrol walks its route, room by room, a step every few seconds (population.py)
        if getattr(self, 'patrol_route', None) and not self.fighting:
            if await self.patrol_ai():
                return

        # Random chance to act each tick (2% = ~0.2 actions/sec at 10 tps)
        if random.randint(1, 100) > 2:
            return

        # one who came from afar to help (allies.py) goes back to its post first
        if getattr(self, '_post', None) is not None:
            import allies
            if await allies.return_to_post(self):
                return

        # Check for aggressive behavior
        if 'aggressive' in self.flags:
            await self.aggressive_ai()
            return

        # Check for special behaviors
        if self.special:
            await self.special_ai()
            return

        # Wander behavior
        if 'sentinel' not in self.flags:
            await self.wander_ai()
    
    def add_grudge(self, player: 'Character', damage: int = 0):
        """Add or update grudge against a player who attacked us."""
        import time
        player_name = player.name
        
        if player_name in self.grudge_list:
            self.grudge_list[player_name]['damage'] += damage
            self.grudge_list[player_name]['time'] = time.time()
            self.grudge_list[player_name]['target'] = player
        else:
            self.grudge_list[player_name] = {
                'target': player,
                'time': time.time(),
                'damage': damage,
                'last_room': player.room
            }
        
        # Set as hunting target if we're a hunter type
        if 'hunter' in self.flags or 'tracker' in self.flags or 'boss' in self.flags:
            if not self.hunting_target or not self.hunting_target.is_alive:
                self.hunting_target = player
                self.last_known_room = player.room
                # the leash is measured from here (where the fight was picked)
                self.chase_from = self.room
    
    def clear_grudge(self, player_name: str = None):
        """Clear grudge(s)."""
        if player_name:
            self.grudge_list.pop(player_name, None)
            if self.hunting_target and self.hunting_target.name == player_name:
                self.hunting_target = None
        else:
            self.grudge_list.clear()
            self.hunting_target = None
    
    async def hunting_ai(self) -> bool:
        """
        Hunt players who attacked us.
        Returns True if we took an action (moved or attacked).
        """
        import time
        
        # Only hunt if we're a hunter/tracker/boss type
        if not ('hunter' in self.flags or 'tracker' in self.flags or 'boss' in self.flags):
            return False
        
        # Sentinels don't move to hunt
        if 'sentinel' in self.flags:
            return False
        
        # Check hunt cooldown
        if self.hunt_cooldown > 0:
            self.hunt_cooldown -= 1
            return False
        
        # Clean up old grudges (expire after 5 minutes)
        now = time.time()
        expired = [name for name, data in self.grudge_list.items() 
                   if now - data['time'] > 300]
        for name in expired:
            self.clear_grudge(name)
        
        # No grudges, no hunting
        if not self.grudge_list:
            if self.hunting_target and self.room:
                c = self.config.COLORS
                await self.room.send_to_room(
                    f"{c['yellow']}{self.name} growls and gives up the hunt.{c['reset']}"
                )
            self.hunting_target = None
            return False
        
        # Pick highest-damage target if current target is gone
        if not self.hunting_target or not self.hunting_target.is_alive:
            best_target = None
            best_damage = 0
            for name, data in self.grudge_list.items():
                target = data['target']
                if target and target.is_alive and data['damage'] > best_damage:
                    best_target = target
                    best_damage = data['damage']
            self.hunting_target = best_target
        
        if not self.hunting_target:
            return False
        
        target = self.hunting_target

        # the leash: past its reach from where the chase began, it gives up, heals and turns back
        home = getattr(self, 'chase_from', None) or self.room
        self.chase_from = home
        reach = max([n for f, n in LEASH.items() if f in self.flags] or [LEASH['hunter']])
        if target.room is not self.room and self._steps_between(home, target.room, reach) is None:
            await self._give_up_chase(target)
            return True

        # a trail swept away (stealth.py): out of sight, the hunter may lose it at each step
        if target.room is not self.room:
            import stealth
            if stealth.covered(target) and random.random() < stealth.LOSE_EACH_STEP:
                words = stealth.lose_trail(self, target)
                if self.room:
                    c = self.config.COLORS
                    await self.room.send_to_room(f"{c['yellow']}{self.name} {words}.{c['reset']}")
                return True

        # If target is in the same room, attack!
        if target.room == self.room:
            if not self.is_fighting:
                c = self.config.COLORS
                await self.room.send_to_room(
                    f"{c['bright_red']}{self.name} snarls and attacks {target.name}!{c['reset']}"
                )
                from combat import CombatHandler
                await CombatHandler.start_combat(self, target)
            return True
        
        # Update last known room if target is visible somewhere
        if target.room:
            self.last_known_room = target.room
        
        # Try to move toward the target
        path = await self.find_path_to_target(target)
        if path:
            direction = path[0]
            moved = await self.hunt_move(direction)
            if moved:
                self.hunt_cooldown = 2  # Wait 2 ticks before moving again
                return True

        # Path blocked and the prey is right through a door? POUND ON IT.
        # Barricades and seals buy time, not safety — you HEAR it coming.
        for d, ex in self.room.exits.items():
            if not ex or ex.get('room') is not target.room or 'door' not in ex:
                continue
            door = ex['door']
            import doors
            if door.get('state') != 'closed' or doors.unbreakable(door):
                continue           # (an arcane door, a quest gate: no force breaks them, doors.py)
            from commands import CommandHandler
            c = self.config.COLORS
            max_hp = CommandHandler._door_max_hp(door)
            door.setdefault('hp', max_hp)
            door['hp'] -= getattr(self, 'str', 12) * 2 + self.level + random.randint(0, 10)
            name = door.get('name', 'door')
            if door['hp'] <= 0:
                await CommandHandler._break_door_open(self, self.room, d, ex, door, self.config)
            else:
                await self.room.send_to_room(
                    f"{c['bright_red']}{self.name} slams against the {name} {d}! BOOM!{c['reset']}"
                )
                if target.room:
                    await target.room.send_to_room(
                        f"{c['bright_red']}💥 BOOM! Something heavy pounds against the {name}!{c['reset']}"
                    )
            self.hunt_cooldown = 2
            return True

        return False
    
    def _steps_between(self, a, b, limit):
        """Rooms from a to b by open ways (no closed doors), within `limit` steps, else None."""
        if a is None or b is None:
            return None
        if a is b:
            return 0
        from collections import deque
        seen, q = {a.vnum}, deque([(a, 0)])
        while q:
            room, n = q.popleft()
            if n >= limit:
                continue
            for ex in (room.exits or {}).values():
                to = ex.get('room') if isinstance(ex, dict) else None
                if to is None or to.vnum in seen:
                    continue
                door = ex.get('door')
                if isinstance(door, dict) and door.get('state') == 'closed':
                    continue
                if to is b:
                    return n + 1
                seen.add(to.vnum)
                q.append((to, n + 1))
        return None

    async def _give_up_chase(self, target):
        """Too far from home: drop the chase and the grudge, heal, and head back."""
        c = self.config.COLORS
        if self.room:
            await self.room.send_to_room(f"{c['yellow']}{self.name} gives up the chase and turns back.{c['reset']}")
        self.clear_grudge(getattr(target, 'name', None))
        self.hunting_target = None
        if getattr(self, 'fighting', None) is target:
            self.fighting = None
        self.hp = max(self.hp, getattr(self, 'max_hp', self.hp))   # (no wearing it down by leading it about)
        home = getattr(self, 'chase_from', None)
        self.returning = home if home is not None and home is not self.room else None
        self.chase_from = None

    async def _return_home(self):
        """A step back toward where a given-up chase began (every few ticks); True if it moved."""
        home = self.returning
        if self.fighting or self.room is None or home is None or self.room is home:
            self.returning = None
            return False
        self._home_clock = getattr(self, '_home_clock', 0) - 1
        if self._home_clock > 0:
            return False
        self._home_clock = 15
        for d, ex in (self.room.exits or {}).items():
            to = ex.get('room') if isinstance(ex, dict) else None
            if to is None or (KEEP_OUT & to.flags):
                continue
            door = ex.get('door')
            if isinstance(door, dict) and door.get('state') == 'closed':
                continue
            here = self._steps_between(self.room, home, 12)
            there = self._steps_between(to, home, 12)
            if here is None or there is None or there >= here:
                continue
            old = self.room
            await old.send_to_room(f"{self.name} heads back {d}.")
            old.characters.remove(self)
            self.room = to
            to.characters.append(self)
            opposite = self.config.DIRECTIONS.get(d, {}).get('opposite', 'somewhere')
            await to.send_to_room(f"{self.name} arrives from the {opposite}.")
            await self._notify_move(old, to, d, opposite)
            if to is home:
                self.returning = None
            return True
        self.returning = None             # (no way back: it stays where it is)
        return False

    async def find_path_to_target(self, target: 'Character') -> list:
        """
        Find a path to the target using BFS.
        Respects zone boundaries and closed doors.
        Returns list of directions or empty list.
        """
        if not self.room or not target.room:
            return []
        
        # Don't chase outside our zone (unless we're a boss)
        target_zone = zone_of(target.room)
        if self.home_zone is not None and target_zone != self.home_zone:
            if 'boss' not in self.flags:
                return []
        
        # BFS to find path
        from collections import deque
        
        visited = {self.room.vnum}
        queue = deque([(self.room, [])])
        max_distance = 10 if 'tracker' in self.flags else 5
        if 'boss' in self.flags:
            max_distance = 15
        
        while queue:
            current_room, path = queue.popleft()
            
            if len(path) >= max_distance:
                continue
            
            for direction, exit_data in current_room.exits.items():
                if not exit_data:
                    continue
                
                next_room = exit_data.get('room')
                if not next_room or next_room.vnum in visited:
                    continue
                
                # Check for closed doors
                if 'door' in exit_data:
                    door = exit_data['door']
                    if door.get('state') == 'closed':
                        # barricades and arcane seals block PATHING for everyone
                        # (a blocked hunter pounds the door down instead)
                        if door.get('barricaded_until', 0) > time.time() or door.get('sealed_until', 0) > time.time():
                            continue
                        # Mobs can't open locked doors
                        if door.get('locked'):
                            continue
                        # Boss mobs can bash through closed (unlocked) doors
                        if 'boss' in self.flags:
                            pass  # Can proceed
                        else:
                            continue  # Regular mobs blocked by closed doors
                
                # Don't enter no_mob rooms (nor the God Rooms)
                if KEEP_OUT & next_room.flags:
                    continue
                
                # Check zone boundaries (unless boss)
                if self.home_zone is not None and 'boss' not in self.flags:
                    room_zone = zone_of(next_room)
                    if room_zone != self.home_zone:
                        continue
                
                visited.add(next_room.vnum)
                new_path = path + [direction]
                
                # Found target!
                if next_room == target.room:
                    return new_path
                
                queue.append((next_room, new_path))
        
        return []
    
    async def hunt_move(self, direction: str) -> bool:
        """Move in a direction while hunting. Returns True if successful."""
        if not self.room or direction not in self.room.exits:
            return False
        
        exit_data = self.room.exits[direction]
        if not exit_data:
            return False
        
        target_room = exit_data.get('room')
        if not target_room:
            return False
        
        # Don't hunt outside home zone (unless no home zone set)
        if self.home_zone is not None:
            target_zone = zone_of(target_room)
            if target_zone != self.home_zone:
                return False
        
        # Don't enter no_mob rooms (nor the God Rooms)
        if KEEP_OUT & target_room.flags:
            return False
        
        # Check for closed doors
        if 'door' in exit_data:
            door = exit_data['door']
            if door.get('state') == 'closed':
                door_name = door.get('name', 'door')
                if door.get('locked'):
                    if self.room:
                        c = self.config.COLORS
                        await self.room.send_to_room(
                            f"{c['yellow']}{self.name} rattles the locked {door_name}, but it holds.{c['reset']}"
                        )
                    return False
                # Boss can bash through
                if 'boss' in self.flags:
                    c = self.config.COLORS
                    await self.room.send_to_room(
                        f"{c['bright_red']}{self.name} smashes through the {door_name}!{c['reset']}"
                    )
                    import doors
                    doors.apply(self.room, direction, state='open')     # both sides, pushed
                else:
                    if self.room:
                        c = self.config.COLORS
                        await self.room.send_to_room(
                            f"{c['yellow']}{self.name} pushes against the closed {door_name}, but it won't budge.{c['reset']}"
                        )
                    return False
        
        # Leave message
        c = self.config.COLORS
        await self.room.send_to_room(
            f"{c['yellow']}{self.name} stalks {direction}, hunting for prey.{c['reset']}"
        )
        old_room = self.room
        self.room.characters.remove(self)
        
        # Enter new room
        self.room = target_room
        target_room.characters.append(self)
        
        opposite = self.config.DIRECTIONS.get(direction, {}).get('opposite', 'somewhere')
        await target_room.send_to_room(
            f"{c['bright_red']}{self.name} arrives from the {opposite}, eyes searching!{c['reset']}"
        )
        # graphical clients see the hunter move (it used to stay drawn where it was)
        try:
            await self._notify_move(old_room, target_room, direction, opposite)
        except Exception:
            pass
        return True
            
    async def combat_ai(self):
        """AI behavior during combat."""
        if not self.fighting or not self.fighting.is_alive:
            self.fighting = None
            self.position = 'standing'
            return
            
        # Cast spells if caster
        if 'caster' in self.flags and self.mana > 20:
            if random.randint(1, 100) <= 30:
                await self.cast_mob_spell()
                return
                
        # Special attacks
        if random.randint(1, 100) <= 20:
            await self.special_attack()
            
    async def faction_aggressive_ai(self) -> bool:
        """Attack on sight if faction reputation is hostile."""
        if not self.room or not getattr(self, 'faction', None):
            return False

        # Don't attack in peaceful rooms
        if 'peaceful' in self.room.flags:
            return False

        try:
            from factions import FactionManager
            from combat import CombatHandler
        except Exception:
            return False

        for char in list(self.room.characters):
            if char == self or not hasattr(char, 'connection') or char.is_fighting or spared(char):
                continue
            faction_key = FactionManager.normalize_key(self.faction)
            if not faction_key:
                continue
            if FactionManager.is_hostile(char, faction_key):
                await CombatHandler.start_combat(self, char)
                return True

        return False

    async def aggressive_ai(self):
        """Check for and attack valid targets."""
        if not self.room:
            return

        # Find potential targets (excluding hidden/sneaking players who pass their check)
        targets = []
        for char in self.room.characters:
            if char == self or not hasattr(char, 'connection') or spared(char):
                continue

            # Skip if this mob is blinded or asleep
            if getattr(self, 'position', '') == 'sleeping' or 'blind' in getattr(self, 'affect_flags', set()):
                return

            # Check if player is hidden or sneaking
            if 'hidden' in char.flags or 'sneaking' in char.flags:
                env_bonus = 0
                try:
                    if self.room and self.room.is_dark(self.world.game_time):
                        env_bonus += 20
                    if self.room.sector_type in ('forest', 'swamp'):
                        env_bonus += 10
                except Exception:
                    pass
                if hasattr(char, 'has_light_source') and char.has_light_source():
                    env_bonus -= 25

                # Mob detection vs player stealth
                detection = (self.level * 3) + getattr(self, 'detect_bonus', 0) + random.randint(1, 20)
                stealth = max(char.skills.get('hide', 0), char.skills.get('sneak', 0)) + env_bonus + random.randint(1, 20)

                if stealth >= detection:
                    continue

                # Mob detected the player! Reveal them
                if 'hidden' in char.flags:
                    char.flags.remove('hidden')
                    c = self.config.COLORS
                    await char.send(f"{c['yellow']}{self.name} spots you!{c['reset']}")
                    await self.room.send_to_room(
                        f"{c['yellow']}{self.name} spots {char.name} hiding!{c['reset']}",
                        exclude=[char]
                    )

            targets.append(char)

        if not targets:
            # none here: a hero in the open next door may be seen, and charged (reach.py)
            await self._charge_next_door()
            return

        # Don't attack if room is peaceful
        if 'peaceful' in self.room.flags:
            return

        # In city zones, don't attack players more than 5 levels below the mob
        if self.room and getattr(self.room, 'sector_type', '') == 'city':
            targets = [t for t in targets if self.level - t.level <= 5]
            if not targets:
                return

        # Pick a random target
        target = random.choice(targets)

        # Announce and attack
        c = self.config.COLORS
        await self.room.send_to_room(
            f"{c['bright_red']}{self.name} attacks {target.name}!{c['reset']}"
        )

        from combat import CombatHandler
        await CombatHandler.start_combat(self, target)
        
    async def _charge_next_door(self):
        """An aggressive creature that sees a hero across an open way (reach.noticed) runs at
        them and attacks (docs/OPEN_WORLD.md, phase 4: the land is one place)."""
        import reach
        world = getattr(self, 'world', None)
        if world is None or getattr(self, 'patrol_route', None):
            return False
        target = reach.noticed(world, self, spared=spared)
        if target is None or not reach.bring(world, self, target.room):
            return False
        c = self.config.COLORS
        await self.room.send_to_room(f"{c['bright_red']}{self.name} spots {target.name} and attacks!{c['reset']}")
        from combat import CombatHandler
        await CombatHandler.start_combat(self, target)
        return True

    def _lives_in_water(self) -> bool:
        """A creature of the water (flagged aquatic or swimming, or set in a water room): it may
        wander the water, where the rest keep to land."""
        flags = set(getattr(self, 'flags', None) or ())
        if flags & {'aquatic', 'swim', 'water', 'fish'}:
            return True
        home = getattr(self, 'home_room', None)
        return getattr(home, 'sector_type', '') in WATER_SECTORS

    async def wander_ai(self):
        """Randomly move to adjacent rooms."""
        if not self.room or not self.room.exits:
            return
        
        # Sentinel mobs don't wander
        if 'sentinel' in self.flags:
            return
            
        # Get valid exits
        valid_exits = []
        for direction, exit_data in self.room.exits.items():
            if exit_data and exit_data.get('room'):
                # Don't walk through closed doors
                if 'door' in exit_data:
                    door = exit_data['door']
                    if door.get('state') == 'closed':
                        continue
                target_room = exit_data['room']
                # Don't wander into no_mob rooms (nor the God Rooms)
                if KEEP_OUT & target_room.flags:
                    continue
                # Don't wander out of home zone (unless no home zone set)
                if self.home_zone is not None:
                    target_zone = zone_of(target_room)
                    if target_zone != self.home_zone:
                        continue
                # nor out onto the water, unless it lives there
                if (Config.WATER_NEEDS_BOAT and getattr(target_room, 'sector_type', '') in WATER_SECTORS
                        and not self._lives_in_water()):
                    continue
                valid_exits.append((direction, target_room))
                    
        if not valid_exits:
            return

        # townsfolk keep a day: at night they make for a house and stay in; by day they come out
        routine = self._townsfolk_day(valid_exits)
        if routine is not None:
            valid_exits, wander_chance = routine
            if not valid_exits or random.randint(1, 100) > wander_chance:
                return
            direction, target_room = random.choice(valid_exits)
            # (one that went in for the night comes out again by day; one that came out stays out)
            self._sheltered = self._indoors(target_room)
            return await self._wander_to(direction, target_room)

        # Determine wander chance based on flags
        # slow_wander = 1% chance (fidos, etc)
        # normal = 3% chance
        if 'slow_wander' in self.flags:
            wander_chance = 1
        else:
            wander_chance = 3
            
        if random.randint(1, 100) > wander_chance:
            return
            
        direction, target_room = random.choice(valid_exits)
        await self._wander_to(direction, target_room)

    @staticmethod
    def _indoors(room):
        return 'indoors' in (room.flags or ()) or getattr(room, 'look', None) == 'inside'

    def _townsfolk_day(self, valid_exits):
        """For one of the town's folk (a peaceable creature of the streets): the ways it may take
        now and how keen it is ([(direction, room)], percent a tick), or None for any other
        creature. At night one out in the streets makes for a house next door (eagerly) and one
        indoors stays in; by day one indoors goes back out (now and then)."""
        flags = self.flags or set()
        if 'aggressive' in flags or 'sentinel' in flags or getattr(self, 'owner', None) is not None or self.fighting:
            return None
        here = self.room
        if not (self._indoors(here) or getattr(here, 'look', None) in TOWN_LOOKS):
            return None
        if not any(getattr(r, 'look', None) in TOWN_LOOKS or self._indoors(r) for _d, r in valid_exits):
            return None
        game_time = getattr(getattr(self, 'world', None), 'game_time', None)
        if game_time is None:
            return None
        night = game_time.is_night()
        inside = self._indoors(here)
        if night:
            if inside:
                return [], 0
            homes = [(d, r) for d, r in valid_exits if self._indoors(r)]
            return (homes, 25) if homes else (valid_exits, 3)
        if inside and getattr(self, '_sheltered', False):
            out = [(d, r) for d, r in valid_exits if not self._indoors(r)]
            return (out, 8) if out else None
        return None

    async def _wander_to(self, direction, target_room):
        """Walk out of this room the way given, as wandering does (with its herd)."""
        # Leave current room
        old_room = self.room
        await self.room.send_to_room(f"{self.name} leaves {direction}.")
        self.room.characters.remove(self)
        
        # Enter new room
        self.room = target_room
        target_room.characters.append(self)
        
        opposite = self.config.DIRECTIONS.get(direction, {}).get('opposite', 'somewhere')
        await target_room.send_to_room(f"{self.name} arrives from the {opposite}.")
        await self._notify_move(old_room, target_room, direction, opposite)
        await self._herd_follows(old_room, direction, target_room, opposite)

    async def _herd_follows(self, old_room, direction, target_room, opposite):
        """Its own kind (the same creature) idling in the room it left may go with it, a few at
        most: a herd moves together, a pack roams together (docs/OPEN_WORLD.md, phase 4)."""
        vnum = getattr(self, 'vnum', None)
        if vnum is None or 'herd_no' in self.flags:
            return
        went = 0
        for m in list(old_room.characters):
            if went >= 3:
                break
            if (m is self or getattr(m, 'vnum', None) != vnum or hasattr(m, 'connection') or m.fighting
                    or 'sentinel' in m.flags or getattr(m, 'patrol_route', None) or getattr(m, 'owner', None) is not None
                    or getattr(m, 'home_zone', None) not in (None, zone_of(target_room)) or random.random() > 0.6):
                continue
            old_room.characters.remove(m)
            m.room = target_room
            target_room.characters.append(m)
            await old_room.send_to_room(f"{m.name} follows {direction}.")
            await target_room.send_to_room(f"{m.name} arrives from the {opposite}.")
            await m._notify_move(old_room, target_room, direction, opposite)
            went += 1

    async def patrol_ai(self) -> bool:
        """Step to the next room of the patrol route (there and back along it); True if it moved."""
        import time as _t
        now = _t.time()
        if now < getattr(self, '_patrol_next', 0):
            return False
        self._patrol_next = now + random.uniform(6, 10)
        route = self.patrol_route
        here = getattr(self.room, 'vnum', None)
        if here not in route:
            return False
        i = route.index(here)
        step = getattr(self, '_patrol_dir', 1)
        if not 0 <= i + step < len(route):
            step = -step
        self._patrol_dir = step
        to = route[i + step]
        for direction, ex in (self.room.exits or {}).items():
            target = ex.get('room') if isinstance(ex, dict) else None
            if target is None or target.vnum != to:
                continue
            door = ex.get('door')
            if isinstance(door, dict) and door.get('state') == 'closed':
                return False
            old = self.room
            await old.send_to_room(f"{self.name} marches {direction}.")
            old.characters.remove(self)
            self.room = target
            target.characters.append(self)
            opposite = self.config.DIRECTIONS.get(direction, {}).get('opposite', 'somewhere')
            await target.send_to_room(f"{self.name} marches in from the {opposite}.")
            await self._notify_move(old, target, direction, opposite)
            return True
        return False

    async def _notify_move(self, old_room, new_room, direction, opposite):
        """Tell graphical clients in both rooms: live roster + travel arrows.
        Without this, a wandering NPC's icon sticks on screen until the
        player happens to move."""
        web_map = getattr(self.world, 'web_map', None)
        if not web_map:
            return
        try:
            await web_map.notify_room(old_room, {
                'type': 'mob_move', 'action': 'leave', 'name': self.name,
                'dir': direction, 'vnum': getattr(old_room, 'vnum', None)})
            await web_map.notify_room(new_room, {
                'type': 'mob_move', 'action': 'arrive', 'name': self.name,
                'dir': opposite, 'vnum': getattr(new_room, 'vnum', None)})
        except Exception:
            pass
        # heard next door (a patrol passing): a cue for /play players one room away
        try:
            from ambient import AmbientManager
            await AmbientManager.creature_moved(self.world, self, new_room)
        except Exception:
            pass
        
    async def special_ai(self):
        """Handle special mob behaviors."""
        if self.special == 'healer':
            await self.healer_ai()
        elif self.special == 'shopkeeper':
            pass  # Shopkeepers handled by commands
        elif self.special == 'trainer':
            pass  # Trainers handled by commands
        elif self.special == 'flavor_npc':
            pass  # Flavor NPCs - atmosphere only, no AI behavior
        elif self.special == 'druid':
            await self.druid_ai()
            
    async def healer_ai(self):
        """Healer NPC AI - offer healing to wounded players."""
        if not self.room:
            return
            
        for char in self.room.characters:
            if hasattr(char, 'connection'):  # Is a player
                if char.hp < char.max_hp * 0.5:
                    c = self.config.COLORS
                    await char.send(f"\r\n{c['bright_cyan']}{self.name} says, 'You look wounded, traveler. Say \"heal\" and I shall aid you.'{c['reset']}")
                    break
                    
    async def druid_ai(self):
        """Druid NPC AI."""
        if not self.room:
            return
            
        if random.randint(1, 100) <= 5:
            messages = [
                "hums a tune that seems to resonate with the forest.",
                "touches a nearby tree and whispers ancient words.",
                "scatters seeds that seem to glow faintly.",
                "communes silently with nature.",
            ]
            c = self.config.COLORS
            await self.room.send_to_room(f"{c['green']}{self.name} {random.choice(messages)}{c['reset']}")
            
    async def cast_mob_spell(self):
        """Cast a spell during combat."""
        if not self.fighting:
            return
            
        c = self.config.COLORS
        target = self.fighting
        
        # Different spells based on mob type
        if self.special == 'necromancer':
            spells = ['chill_touch', 'energy_drain', 'fear']
        elif self.special == 'shaman':
            spells = ['poison', 'blindness', 'weaken']
        elif 'dragon' in self.name.lower():
            spells = ['fireball', 'fear']
        else:
            spells = ['magic_missile', 'chill_touch']
            
        spell = random.choice(spells)
        
        # Calculate damage
        damage = random.randint(self.level, self.level * 3)
        
        await self.room.send_to_room(
            f"{c['bright_magenta']}{self.name} casts {spell.replace('_', ' ')}!{c['reset']}"
        )
        
        if hasattr(target, 'send'):
            await target.send(f"{c['bright_red']}{self.name}'s spell hits you for {damage} damage!{c['reset']}")
            
        self.mana -= 20
        
        killed = await target.take_damage(damage, self)
        if killed:
            from combat import CombatHandler
            await CombatHandler.handle_death(self, target)
            
    async def special_attack(self):
        """Perform a special attack based on mob type."""
        if not self.fighting:
            return
            
        c = self.config.COLORS
        target = self.fighting
        
        attack_type = None
        damage_mult = 1.0
        
        if 'poison' in self.flags or self.special == 'poison':
            attack_type = 'poisons'
            damage_mult = 0.5
            # Apply poison DOT effect
            from affects import AffectManager
            if not any(a.get('name') == 'poison' for a in getattr(target, 'affects', [])):
                AffectManager.apply_affect(target, {
                    'name': 'poison',
                    'type': AffectManager.TYPE_DOT,
                    'applies_to': 'hp',
                    # weighed like its blows (a zone boss's or a quest creature's _dmg_scale)
                    'value': max(1, round((3 + self.level // 5) * (getattr(self, '_dmg_scale', 1) or 1))),
                    'duration': 4,
                    'caster_level': self.level
                })
                if hasattr(target, 'send'):
                    await target.send(f"{c['green']}You feel poison coursing through your veins!{c['reset']}")
        elif 'dragon' in self.name.lower() or self.special == 'firebreath':
            attack_type = 'breathes fire on'
            damage_mult = 2.0
        elif 'troll' in self.name.lower() or self.special == 'regenerate':
            # Trolls regenerate during combat (poison blocks it)
            affect_flags = getattr(self, 'affect_flags', set())
            if 'poisoned' in affect_flags:
                await self.room.send_to_room(
                    f"{c['bright_magenta']}{self.name} tries to regenerate but the poison prevents it!{c['reset']}"
                )
            else:
                # ~4% of max HP per proc (was 10%, which let trolls out-heal a
                # whole party); capped so high-HP trolls/bosses don't spike, and
                # only echoed when it's a meaningful heal so it stops spamming
                regen = min(self.max_hp // 25, 150)
                if 'diseased' in affect_flags:
                    regen = regen // 4
                healed = min(regen, self.max_hp - self.hp)
                self.hp += healed
                if healed >= 5:
                    await self.room.send_to_room(
                        f"{c['green']}{self.name}'s wounds slowly close.{c['reset']}"
                    )
            return
        elif self.special == 'paralyze':
            attack_type = 'tries to paralyze'
            if random.randint(1, 100) <= 20:
                from combat import CombatHandler
                CombatHandler.stun(target, 1)
                await self.room.send_to_room(
                    f"{c['yellow']}{target.name} is paralyzed!{c['reset']}"
                )
            return
            
        if attack_type:
            damage = int(self.roll_dice(self.damage_dice) * damage_mult)
            await self.room.send_to_room(
                f"{c['bright_red']}{self.name} {attack_type} {target.name}! [{damage}]{c['reset']}"
            )
            
            killed = await target.take_damage(damage, self, {'poisons': 'poison', 'breathes fire on': 'fire'}.get(attack_type, 'physical'))
            if killed:
                from combat import CombatHandler
                await CombatHandler.handle_death(self, target)
                
    async def take_damage(self, amount: int, attacker: 'Character' = None, damage_type: str = 'physical') -> bool:
        """Take damage, return True if killed."""
        damage_type = damage_type or 'physical'
        import time as _time
        _now = _time.time()

        # STAGGERED: poise broken — reeling and wide open (+50% damage taken)
        if amount > 0 and _now < getattr(self, 'staggered_until', 0):
            amount = int(amount * 1.5)
        # GUARDED: shield raised — weapon auto-swings are mostly turned aside.
        # Class abilities and spells punch through, and any concussive skill
        # (bash/kick/trip/smite...) SHATTERS the guard (CombatHandler.break_guard).
        elif amount > 0 and damage_type == 'physical' \
                and getattr(attacker, '_weapon_swing', False) \
                and _now < getattr(self, 'guard_until', 0):
            turned = amount - max(1, int(amount * 0.4))
            amount = max(1, int(amount * 0.4))
            if turned > 2 and hasattr(self, 'room') and self.room and random.random() < 0.5:
                c = Config().COLORS
                await self.room.send_to_room(
                    f"{c['cyan']}{self.name}'s guard turns the blow aside! (-{turned}) "
                    f"{c['yellow']}A heavy bash or kick could break it.{c['reset']}"
                )

        # Absorb shields (divine_shield / stoneskin / armour_ward)
        try:
            absorb_allowed = damage_type == 'physical' or damage_type in Config.ABSORB_MAGIC_TYPES
            for affect in self.affects[:]:
                if affect.applies_to in ('divine_shield', 'stoneskin', 'armour_ward') and amount > 0 and absorb_allowed:
                    absorbed = min(amount, affect.value)
                    affect.value -= absorbed
                    amount -= absorbed
                    if absorbed > 0 and hasattr(self, 'room') and self.room:
                        c = Config().COLORS
                        await self.room.send_to_room(
                            f"{c['cyan']}{self.name}'s {affect.applies_to.replace('_',' ')} absorbs {absorbed} damage!{c['reset']}"
                        )
                    if affect.value <= 0:
                        from affects import AffectManager
                        AffectManager.remove_affect(self, affect)
        except Exception:
            pass

        # what spells leave on a creature (spells.py): invulnerable takes nothing, sanctuary
        # halves the blow; a charm breaks the moment it is struck; a fire shield (or a fire
        # elemental's flame) burns a melee attacker
        wards = getattr(self, 'affect_flags', None) or set()
        if amount > 0 and 'invulnerable' in wards:
            return False
        if amount > 0 and 'sanctuary' in wards:
            amount = max(1, amount // 2)
        if 'charmed' in wards:
            from affects import AffectManager
            for a in list(getattr(self, 'affects', []) or []):
                if a.applies_to == 'charmed':
                    AffectManager.remove_affect(self, a)
        if (amount > 0 and attacker is not None and damage_type == 'physical' and attacker is not self
                and ('fire_shield' in wards or 'fire_shield' in (getattr(self, 'flags', None) or ()))
                and getattr(attacker, 'hp', 0) > 0):
            burn = max(2, min(25, amount // 8))
            if hasattr(attacker, 'resistance'):      # a hero's fire ward
                burn = max(1, burn * (100 - attacker.resistance('fire')) // 100)
            attacker.hp -= burn
            if hasattr(attacker, 'send'):
                await attacker.send(f"{Config().COLORS['red']}{self.name}'s flames sear you! [{burn}]{Config().COLORS['reset']}")
            if attacker.hp <= 0 and hasattr(attacker, 'die'):
                await attacker.die(self)

        # Shield Wall damage reduction (50% while active)
        if hasattr(self, 'shield_wall_active') and self.shield_wall_active > 0:
            original = amount
            amount = int(amount * 0.5)
            if hasattr(self, 'room') and self.room:
                c = Config().COLORS
                await self.room.send_to_room(
                    f"{c['cyan']}{self.name}'s shield absorbs some of the blow! (-{original - amount}){c['reset']}"
                )

        # Damage reduction from affects
        if amount > 0 and hasattr(self, 'damage_reduction') and self.damage_reduction > 0:
            reduced = max(1, int(amount * (self.damage_reduction / 100.0)))
            amount = max(0, amount - reduced)

        # Paladin Protection Aura (nearby allies): 10% damage reduction
        if amount > 0 and 'protection' in self.get_paladin_auras():
            reduced = max(1, int(amount * 0.10))
            amount = max(0, amount - reduced)

        # Paladin Retribution Aura (nearby allies): thorns damage to attacker
        if amount > 0 and attacker and 'retribution' in self.get_paladin_auras():
            thorn = max(2, min(20, int(amount * 0.10)))
            if hasattr(attacker, 'resistance'):      # a hero's holy ward
                thorn = max(1, thorn * (100 - attacker.resistance('holy')) // 100)
            try:
                attacker.hp -= thorn
                if hasattr(attacker, 'send'):
                    c = Config().COLORS
                    await attacker.send(f"{c['magenta']}Retribution burns you for {thorn} damage!{c['reset']}")
                if attacker.hp <= 0 and hasattr(attacker, 'die'):
                    await attacker.die(self)
            except Exception:
                pass
        
        self.hp -= amount

        # Check for death
        if self.hp <= 0:
            if not getattr(self, '_dying', False):
                self._dying = True
                if attacker:
                    from combat import CombatHandler
                    await CombatHandler.handle_death(attacker, self)
                else:
                    await self.die(attacker)
            return True

        # POISE: player hits chip the mob's balance; break it and the mob is
        # STAGGERED — loses its round and takes +50% while the window lasts.
        # A perfect-timed strike (cmd_swing) chips double. Poise grows after
        # each stagger so the loop has diminishing returns within one fight.
        if amount > 0 and attacker is not None and hasattr(attacker, 'connection') \
                and _now >= getattr(self, 'staggered_until', 0):
            if not getattr(self, 'max_poise', 0):
                self.max_poise = 3 + getattr(self, 'level', 1) // 4
            chip = 2 if getattr(attacker, '_poise_bonus_hit', False) else 1
            attacker._poise_bonus_hit = False
            self.poise = getattr(self, 'poise', 0) + chip
            if self.poise >= self.max_poise:
                self.poise = 0
                self.max_poise = int(self.max_poise * 1.5) + 1
                self.stunned_rounds = getattr(self, 'stunned_rounds', 0) + 1
                self.staggered_until = _now + 1.5 * Config.COMBAT_ROUND_SECONDS
                self.guard_until = 0          # a broken stance drops any guard
                self.pending_intent = None    # ...and interrupts any wind-up
                if hasattr(self, 'room') and self.room:
                    c = Config().COLORS
                    await self.room.send_to_room(
                        f"{c['bright_yellow']}💥 {self.name} reels — STAGGERED! Strike now!{c['reset']}"
                    )

        # Wimpy mobs flee at low health (but not if dead)
        if 'wimpy' in self.flags and self.hp < self.max_hp * 0.2:
            if self.fighting:
                self.fighting.fighting = None
            self.fighting = None
            self.position = 'standing'
            # Try to flee
            await self.flee()
            return False
            
        return False
        
    async def flee(self):
        """Attempt to flee from combat."""
        if not self.room or not self.room.exits:
            return
            
        valid_exits = []
        for d, e in self.room.exits.items():
            if not e or not e.get('room'):
                continue
            if KEEP_OUT & e['room'].flags:
                continue
            # Don't flee through closed doors
            if 'door' in e and e['door'].get('state') == 'closed':
                continue
            valid_exits.append((d, e['room']))
        
        if valid_exits:
            direction, target_room = random.choice(valid_exits)

            c = self.config.COLORS
            await self.room.send_to_room(f"{c['yellow']}{self.name} flees {direction}!{c['reset']}")

            old_room = self.room
            exit_used = old_room.exits.get(direction)
            self.room.characters.remove(self)
            self.room = target_room
            target_room.characters.append(self)

            # a fleeing COWARD slams the door behind it — chase or cut it off
            try:
                from mob_ai import classify_mob
                if exit_used and 'door' in exit_used and exit_used['door'].get('state') == 'open' \
                        and not exit_used['door'].get('broken') and 'coward' in classify_mob(self):
                    import doors
                    doors.apply(old_room, direction, state='closed')     # both sides, pushed
                    name = doors.label(exit_used['door'])
                    await old_room.send_to_room(f"{c['yellow']}{self.name} SLAMS the {name} shut behind it!{c['reset']}")
            except Exception:
                pass

    async def die(self, killer: 'Character' = None):
        """Handle mob death."""
        if self.fighting:
            self.fighting.fighting = None
            self.fighting = None
            
        self.position = 'dead'
        
        c = self.config.COLORS
        if self.room:
            await self.room.send_to_room(
                f"{c['red']}{self.name[:1].upper() + self.name[1:]} is DEAD!{c['reset']}"
            )
            
    async def regen_tick(self):
        """Regenerate HP/mana and process affects."""
        # Process affects (damage over time, healing over time, expiration)
        await AffectManager.tick_affects(self)

        if not self.is_fighting:
            # Regen for mobs: 5% for normal mobs, capped at 500 for bosses/high-HP mobs
            regen_amt = max(1, self.max_hp // 20)
            if self.max_hp > 5000:
                regen_amt = min(regen_amt, 500)  # Cap regen for bosses
            # Poison halves regen, disease quarters it
            affect_flags = getattr(self, 'affect_flags', set())
            if 'poisoned' in affect_flags:
                regen_amt = regen_amt // 2
            if 'diseased' in affect_flags:
                regen_amt = regen_amt // 4
            self.hp = min(self.max_hp, self.hp + regen_amt)
            self.mana = min(self.max_mana, self.mana + max(1, self.max_mana // 10))
            
    def get_hit_bonus(self):
        """Calculate hit bonus (to hit / THAC0)."""
        bonus = getattr(self, 'hitroll', 0) or (self.level // 2)
        # DEX is primary factor for accuracy
        bonus += (self.dex - 10) // 2
        # STR provides minor bonus
        bonus += (self.str - 10) // 4
        try:
            from config import Config
            stance = getattr(self, 'stance', 'normal')
            stance_mods = Config.STANCE_MODIFIERS.get(stance, Config.STANCE_MODIFIERS['normal'])
            bonus += stance_mods.get('hit', 0)
        except Exception:
            pass
        return bonus

    def get_damage_bonus(self):
        """Calculate damage bonus."""
        bonus = getattr(self, 'damroll', 0) or (self.level // 4)
        # STR is primary factor for damage
        bonus += (self.str - 10) // 2
        try:
            from config import Config
            stance = getattr(self, 'stance', 'normal')
            stance_mods = Config.STANCE_MODIFIERS.get(stance, Config.STANCE_MODIFIERS['normal'])
            bonus += stance_mods.get('dam', 0)
        except Exception:
            pass
        return bonus
        
    def get_armor_class(self):
        """Get effective armor class (lower is better)."""
        ac = self.armor_class
        # DEX improves AC (makes you harder to hit)
        ac -= (self.dex - 10) // 2 * 10
        try:
            from config import Config
            stance = getattr(self, 'stance', 'normal')
            stance_mods = Config.STANCE_MODIFIERS.get(stance, Config.STANCE_MODIFIERS['normal'])
            ac += stance_mods.get('ac', 0)
        except Exception:
            pass
        return ac
