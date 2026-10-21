"""
Misthollow Companion System
==========================
Hireable NPC companions that adventure alongside players.
"""

import random
import logging
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from player import Player
    from world import World
    from mobs import Mobile

from mobs import Mobile
from config import Config

logger = logging.getLogger('Misthollow.Companions')

# Companion type definitions
COMPANION_TYPE_CONFIG: Dict[str, Dict] = {
    'Fighter': {
        'mob_class': 'warrior',
        'damage_dice': '2d6',
        'skills': {
            'second_attack': 60,
            'third_attack': 25,
            'bash': 45,
        },
        'spells': {},
        'cost_mult': 1.0,
    },
    'Healer': {
        'mob_class': 'cleric',
        'damage_dice': '1d6',
        'skills': {
            'second_attack': 30,
        },
        'spells': {
            'cure_light': 75,
            'cure_serious': 65,
            'cure_critical': 55,
            'heal': 40,
            'bless': 50,
        },
        'cost_mult': 1.2,
    },
    'Mage': {
        'mob_class': 'mage',
        'damage_dice': '1d4',
        'skills': {},
        'spells': {
            'magic_missile': 80,
            'burning_hands': 70,
            'chill_touch': 65,
            'lightning_bolt': 55,
            'fireball': 50,
        },
        'cost_mult': 1.35,
    },
    'Rogue': {
        'mob_class': 'rogue',
        'damage_dice': '1d6',
        'skills': {
            'backstab': 70,
            'sneak': 60,
            'hide': 50,
            'second_attack': 40,
        },
        'spells': {},
        'cost_mult': 1.15,
    },
    'Ranger': {
        'mob_class': 'ranger',
        'damage_dice': '1d8',
        'skills': {
            'second_attack': 55,
        },
        'spells': {
            'cure_light': 50,
            'barkskin': 45,
        },
        'cost_mult': 1.1,
    },
}

MAX_COMPANIONS = 3


class Companion(Mobile):
    """Hireable companion that follows a player."""

    def __init__(self, vnum: int, world: 'World', owner: 'Player', companion_type: str = 'Fighter'):
        super().__init__(vnum, world)
        self.owner = owner
        self.companion_type = companion_type
        self.config = Config()

        # Core companion stats
        self.loyalty = 100  # 0-100
        self.morale = 100   # 0-100
        self.payment = 0
        self.daily_upkeep = 0
        self.scale_with_owner = True
        self.permadeath = False
        self.respawn_room_vnum = getattr(owner, 'recall_point', self.config.STARTING_ROOM)

        # Companion state
        self.order = 'follow'
        self.ai_state = {}
        self.flags.add('companion')

        # Skills and spells
        self.skills: Dict[str, int] = {}
        self.spells: Dict[str, int] = {}

        # Initialize stats and loadout
        self._apply_type_config()

    async def send(self, message: str, newline: bool = True, kind: str = None):
        """Companion doesn't receive messages directly."""
        # Suppress self-directed messaging to avoid confusion.
        return

    def _apply_type_config(self):
        """Apply configuration based on companion type."""
        cfg = COMPANION_TYPE_CONFIG.get(self.companion_type, COMPANION_TYPE_CONFIG['Fighter'])
        self.damage_dice = cfg.get('damage_dice', '1d6')
        self.skills = dict(cfg.get('skills', {}))
        self.spells = dict(cfg.get('spells', {}))

    def initialize_level(self, level: int):
        """Initialize stats based on level."""
        self.level = max(1, level)
        self.max_hp = self.roll_dice(f'{self.level}d10+{self.level * 5}')
        self.hp = self.max_hp
        self.max_mana = self.level * 10
        self.mana = self.max_mana
        self.max_move = 100
        self.move = self.max_move

        # Base stats
        self.str = 10 + self.level // 5
        self.int = 10 + self.level // 5
        self.wis = 10 + self.level // 5
        self.dex = 10 + self.level // 5
        self.con = 10 + self.level // 5
        self.cha = 10 + self.level // 5
        self.armor_class = 100 - self.level * 2

        # Equipment
        mob_class = COMPANION_TYPE_CONFIG.get(self.companion_type, {}).get('mob_class', 'warrior')
        proto = {'mob_class': mob_class, 'role': 'companion'}
        self.auto_equip(proto)

    def sync_level_with_owner(self):
        """Scale companion level to owner if enabled."""
        if not self.scale_with_owner or not self.owner:
            return

        desired_level = max(1, getattr(self.owner, 'level', 1))
        if self.level != desired_level:
            self.initialize_level(desired_level)

    def to_dict(self) -> Dict:
        """Serialize companion for saving."""
        return {
            'kind': 'companion',
            'name': self.name,
            'short_desc': self.short_desc,
            'long_desc': self.long_desc,
            'level': self.level,
            'hp': self.hp,
            'max_hp': self.max_hp,
            'mana': self.mana,
            'max_mana': self.max_mana,
            'damage_dice': self.damage_dice,
            'loyalty': self.loyalty,
            'morale': self.morale,
            'payment': self.payment,
            'daily_upkeep': self.daily_upkeep,
            'companion_type': self.companion_type,
            'order': self.order,
            'scale_with_owner': self.scale_with_owner,
            'permadeath': self.permadeath,
            'respawn_room_vnum': self.respawn_room_vnum,
        }

    @classmethod
    def from_dict(cls, data: Dict, world: 'World', owner: 'Player') -> 'Companion':
        """Deserialize companion from saved data."""
        companion_type = data.get('companion_type', 'Fighter')
        companion = cls(0, world, owner, companion_type)
        companion.name = data.get('name', companion_type)
        companion.short_desc = data.get('short_desc', companion.name)
        companion.long_desc = data.get('long_desc', f"{companion.name} stands here.")
        companion.initialize_level(data.get('level', 1))
        companion.hp = data.get('hp', companion.max_hp)
        companion.max_hp = data.get('max_hp', companion.max_hp)
        companion.mana = data.get('mana', companion.max_mana)
        companion.max_mana = data.get('max_mana', companion.max_mana)
        companion.damage_dice = data.get('damage_dice', companion.damage_dice)
        companion.loyalty = data.get('loyalty', 100)
        companion.morale = data.get('morale', 100)
        companion.payment = data.get('payment', 0)
        companion.daily_upkeep = data.get('daily_upkeep', 0)
        companion.order = data.get('order', 'follow')
        companion.scale_with_owner = data.get('scale_with_owner', True)
        companion.permadeath = data.get('permadeath', False)
        from world import renumbered
        companion.respawn_room_vnum = renumbered(data.get('respawn_room_vnum', companion.respawn_room_vnum))
        return companion

    async def die(self, killer=None):
        """Handle companion death."""
        await super().die(killer)

        # Remove from combat
        if self.fighting:
            self.fighting.fighting = None
            self.fighting = None

        # Remove from room/world
        if self.room and self in self.room.characters:
            self.room.characters.remove(self)
        if self.owner and hasattr(self.owner, 'world') and self in self.owner.world.npcs:
            self.owner.world.npcs.remove(self)

        # Handle permadeath vs respawn
        if self.owner and hasattr(self.owner, 'companions'):
            if self.permadeath:
                if self in self.owner.companions:
                    self.owner.companions.remove(self)
            else:
                # Respawn at tavern/recall point (never in a room it may not be in: the
                # God Rooms, a sealed land; then the owner's recall room, or the temple)
                respawn_room = self.owner.world.rooms.get(self.respawn_room_vnum)
                if respawn_room is None or not respawn_room.admits(self):
                    respawn_room = (self.owner.recall_room() if hasattr(self.owner, 'recall_room')
                                    else self.owner.world.rooms.get(self.config.STARTING_ROOM))
                if respawn_room:
                    self.room = respawn_room
                    self.hp = self.max_hp
                    self.mana = self.max_mana
                    self.position = 'standing'
                    respawn_room.characters.append(self)
                    self.owner.world.npcs.append(self)
                    self.order = 'stay'
                    self.ai_state['staying'] = True

    async def process_ai(self):
        """Companion AI behavior."""
        if not self.is_alive:
            return

        # Sync level if needed
        self.sync_level_with_owner()

        # Morale decay when injured
        if self.hp < self.max_hp * 0.3:
            self.morale = max(0, self.morale - 1)

        # Flee if morale too low
        if self.is_fighting and self.morale <= 10:
            await self.flee()
            self.order = 'stay'
            self.ai_state['staying'] = True
            return

        # Follow owner unless ordered to stay
        if self.owner and self.order == 'follow' and not self.ai_state.get('staying', False):
            await self._follow_owner()

        # Determine combat target
        target = None
        if self.owner and getattr(self.owner, 'fighting', None):
            target = self.owner.fighting
        elif self.owner and getattr(self.owner, 'target', None):
            if self.owner.target and self.owner.target.room == self.room:
                target = self.owner.target

        # If ordered to attack a specific target
        ordered_target = self.ai_state.get('ordered_target')
        if ordered_target and ordered_target.room == self.room:
            target = ordered_target

        if not target:
            self.ai_state.pop('backstabbed', None)
            self.ai_state.pop('backstab_target', None)

        # Drop invalid combat targets
        if self.is_fighting and (not self.fighting or not self.fighting.is_alive or self.fighting.room != self.room):
            self.fighting = None

        # Switch to owner's current target if different
        if target and self.is_fighting and self.fighting and self.fighting != target:
            self.fighting = None

        # Healer behavior
        if self.companion_type == 'Healer' and self.owner and self.owner.room == self.room:
            if self.order in ('heal', 'follow', 'defend'):
                await self._attempt_heal_owner()

        # Mage offensive casting
        if self.companion_type == 'Mage' and target and self.mana >= 10:
            if random.randint(1, 100) <= 40:
                await self._cast_offensive_spell(target)
                return

        # Rogue backstab on combat start
        if self.companion_type == 'Rogue' and target and not self.is_fighting:
            if self.ai_state.get('backstab_target') != target:
                self.ai_state['backstabbed'] = False
                self.ai_state['backstab_target'] = target
            if not self.ai_state.get('backstabbed'):
                from combat import CombatHandler
                self.ai_state['backstabbed'] = True
                await CombatHandler.do_backstab(self, target)
                return

        # Auto-attack owner's target
        if target and target.is_alive and not self.is_fighting:
            from combat import CombatHandler
            await CombatHandler.start_combat(self, target)

    async def _follow_owner(self):
        if not self.owner or not self.owner.room:
            return

        if self.room == self.owner.room:
            return

        if self.room and self in self.room.characters:
            self.room.characters.remove(self)

        self.room = self.owner.room
        self.owner.room.characters.append(self)

    async def _attempt_heal_owner(self):
        if not self.owner or not self.owner.room:
            return
        if self.owner.room != self.room:
            return

        hp_pct = self.owner.hp / max(1, self.owner.max_hp)
        if hp_pct > 0.75:
            return

        from spells import SpellHandler

        # Pick healing spell based on health
        if hp_pct < 0.25 and 'heal' in self.spells:
            spell = 'heal'
        elif hp_pct < 0.45 and 'cure_critical' in self.spells:
            spell = 'cure_critical'
        elif hp_pct < 0.65 and 'cure_serious' in self.spells:
            spell = 'cure_serious'
        else:
            spell = 'cure_light' if 'cure_light' in self.spells else None

        if not spell:
            return

        await SpellHandler.cast_spell(self, spell, self.owner.name)

    async def _cast_offensive_spell(self, target):
        if not target or not target.is_alive:
            return

        from spells import SpellHandler
        spell_list = [s for s in self.spells.keys() if s in ('magic_missile', 'burning_hands', 'chill_touch', 'lightning_bolt', 'fireball')]
        if not spell_list:
            return

        spell = random.choice(spell_list)
        await SpellHandler.cast_spell(self, spell, target.name)


# ─── Class-Based Combat Companions (unlocked at level 20) ─────────

COMBAT_COMPANION_TYPES: Dict[str, Dict] = {
    'warrior': {
        'name': 'War Hound',
        'short_desc': 'a fierce war hound',
        'long_desc': 'A massive armored war hound stands here, growling menacingly.',
        'companion_type': 'Fighter',
        'damage_dice': '2d6',
        'base_hp_mult': 0.6,       # 60% of player max_hp
        'damage_scale': 0.30,      # ~30% of player DPS
        'attack_desc': 'lunges and bites',
        'special': 'knockdown',    # chance to stun
    },
    'assassin': {
        'name': 'Shadow Cat',
        'short_desc': 'a sleek shadow cat',
        'long_desc': 'A dark-furred cat crouches in the shadows, eyes gleaming.',
        'companion_type': 'Rogue',
        'damage_dice': '2d5',
        'base_hp_mult': 0.45,
        'damage_scale': 0.30,
        'attack_desc': 'slashes with razor claws',
        'special': 'bleed',
    },
    'mage': {
        'name': 'Arcane Familiar',
        'short_desc': 'an arcane familiar',
        'long_desc': 'A shimmering arcane construct hovers here, crackling with energy.',
        'companion_type': 'Mage',
        'damage_dice': '2d4',
        'base_hp_mult': 0.35,
        'damage_scale': 0.30,
        'attack_desc': 'zaps with arcane bolts',
        'special': 'mana_regen',   # helps owner regen mana
    },
    'ranger': {
        'name': 'Timber Wolf',
        'short_desc': 'a loyal timber wolf',
        'long_desc': 'A large timber wolf pads alongside its master, ears alert.',
        'companion_type': 'Fighter',
        'damage_dice': '2d6',
        'base_hp_mult': 0.55,
        'damage_scale': 0.30,
        'attack_desc': 'snarls and bites',
        'special': 'track',
    },
    'cleric': {
        'name': 'Guardian Spirit',
        'short_desc': 'a glowing guardian spirit',
        'long_desc': 'A translucent spirit shimmers with holy light.',
        'companion_type': 'Healer',
        'damage_dice': '1d6',
        'base_hp_mult': 0.40,
        'damage_scale': 0.20,
        'attack_desc': 'smites with holy light',
        'special': 'heal_owner',
    },
    'thief': {
        'name': 'Street Urchin',
        'short_desc': 'a nimble street urchin',
        'long_desc': 'A quick-fingered urchin lurks nearby, ready to help.',
        'companion_type': 'Rogue',
        'damage_dice': '2d4',
        'base_hp_mult': 0.40,
        'damage_scale': 0.30,
        'attack_desc': 'stabs with a shiv',
        'special': 'pickpocket',
    },
    'paladin': {
        'name': 'Celestial Stag',
        'short_desc': 'a radiant celestial stag',
        'long_desc': 'A magnificent stag with glowing antlers stands here.',
        'companion_type': 'Fighter',
        'damage_dice': '2d5',
        'base_hp_mult': 0.50,
        'damage_scale': 0.25,
        'attack_desc': 'charges with radiant antlers',
        'special': 'aura_heal',
    },
    'necromancer': {
        'name': 'Shade Wraith',
        'short_desc': 'a hovering shade wraith',
        'long_desc': 'A dark wraith hovers silently, tendrils of shadow drifting from it.',
        'companion_type': 'Mage',
        'damage_dice': '2d5',
        'base_hp_mult': 0.40,
        'damage_scale': 0.30,
        'attack_desc': 'drains with shadow tendrils',
        'special': 'lifedrain',
    },
    'bard': {
        'name': 'Dancing Sprite',
        'short_desc': 'a tiny dancing sprite',
        'long_desc': 'A mischievous sprite dances in the air, trailing sparkles.',
        'companion_type': 'Healer',
        'damage_dice': '1d6',
        'base_hp_mult': 0.35,
        'damage_scale': 0.20,
        'attack_desc': 'zings with fae sparks',
        'special': 'inspire',
    },
}


class CombatCompanion:
    """A class-based combat companion that fights alongside the player."""

    def __init__(self, owner: 'Player', companion_key: str):
        self.owner = owner
        self.companion_key = companion_key
        cfg = COMBAT_COMPANION_TYPES.get(companion_key, COMBAT_COMPANION_TYPES['warrior'])
        self.name = cfg['name']
        self.short_desc = cfg['short_desc']
        self.long_desc = cfg['long_desc']
        self.damage_dice = cfg['damage_dice']
        self.base_hp_mult = cfg.get('base_hp_mult', 0.5)
        self.damage_scale = cfg.get('damage_scale', 0.30)
        self.attack_desc = cfg.get('attack_desc', 'attacks')
        self.special = cfg.get('special', None)

        # State
        self.hp = 1
        self.max_hp = 1
        self.level = 1
        self.behavior = 'attack'   # attack, defend, passive
        self.knocked_out = False
        self.ko_timer = 0           # ticks until revive

        self.sync_to_owner()

    def sync_to_owner(self):
        """Scale stats to owner level."""
        if not self.owner:
            return
        self.level = max(1, self.owner.level)
        old_max = self.max_hp
        self.max_hp = max(10, int(self.owner.max_hp * self.base_hp_mult))
        if old_max != self.max_hp:
            self.hp = self.max_hp
        if self.knocked_out:
            self.hp = 0

    @property
    def is_alive(self):
        return self.hp > 0 and not self.knocked_out

    def get_damage(self) -> int:
        """Calculate companion damage (~30% of player DPS)."""
        from mobs import Mobile
        base = Mobile.roll_dice(self.damage_dice)
        # Scale with level
        level_bonus = self.level // 3
        total = base + level_bonus
        # Defend mode: half damage
        if self.behavior == 'defend':
            total = max(1, total // 2)
        elif self.behavior == 'passive':
            total = 0
        return max(0, total)

    def take_damage(self, amount: int, attacker=None, damage_type: str = 'physical') -> bool:
        """Take damage. Returns True if knocked out."""
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.knocked_out = True
            self.ko_timer = 30  # revives after ~30 ticks of rest
            return True
        return False

    def try_revive(self):
        """Attempt revive during rest."""
        if self.knocked_out:
            self.ko_timer -= 1
            if self.ko_timer <= 0:
                self.knocked_out = False
                self.hp = self.max_hp // 2
                return True
        return False

    def rest_revive(self):
        """Instantly revive when owner rests/sleeps."""
        if self.knocked_out:
            self.knocked_out = False
            self.hp = self.max_hp
            self.ko_timer = 0
            return True
        return False

    def to_dict(self) -> dict:
        return {
            'kind': 'combat_companion',
            'companion_key': self.companion_key,
            'hp': self.hp,
            'max_hp': self.max_hp,
            'level': self.level,
            'behavior': self.behavior,
            'knocked_out': self.knocked_out,
            'ko_timer': self.ko_timer,
        }

    @classmethod
    def from_dict(cls, data: dict, owner: 'Player') -> 'CombatCompanion':
        cc = cls(owner, data.get('companion_key', 'warrior'))
        cc.hp = data.get('hp', cc.max_hp)
        cc.max_hp = data.get('max_hp', cc.max_hp)
        cc.behavior = data.get('behavior', 'attack')
        cc.knocked_out = data.get('knocked_out', False)
        cc.ko_timer = data.get('ko_timer', 0)
        return cc

    @staticmethod
    def can_unlock(player) -> bool:
        """Check if player meets requirements for a combat companion."""
        return player.level >= 20

    @staticmethod
    def get_available_type(player) -> Optional[str]:
        """Get the combat companion type for the player's class."""
        char_class = getattr(player, 'char_class', 'warrior').lower()
        if char_class in COMBAT_COMPANION_TYPES:
            return char_class
        return 'warrior'  # fallback


class CompanionManager:
    """Hiring and management for companions."""

    @staticmethod
    def get_player_companions(player: 'Player') -> List[Companion]:
        if not hasattr(player, 'companions'):
            return []
        return [c for c in player.companions if isinstance(c, Companion)]

    @staticmethod
    def count_companions(player: 'Player') -> int:
        return len(CompanionManager.get_player_companions(player))

    @staticmethod
    def calculate_cost(level: int, companion_type: str) -> Dict[str, int]:
        cfg = COMPANION_TYPE_CONFIG.get(companion_type, COMPANION_TYPE_CONFIG['Fighter'])
        base = 15 * max(1, level)
        hire_cost = int(base * cfg.get('cost_mult', 1.0))
        upkeep = max(5, int(hire_cost * 0.12))
        return {'hire_cost': hire_cost, 'upkeep': upkeep}

    @staticmethod
    async def hire_companion(player: 'Player', target: 'Mobile') -> Optional[Companion]:
        c = player.config.COLORS

        if CompanionManager.count_companions(player) >= MAX_COMPANIONS:
            await player.send(f"{c['red']}You cannot manage more than {MAX_COMPANIONS} companions.{c['reset']}")
            return None

        if not getattr(target, 'hireable', False):
            await player.send(f"{c['yellow']}{target.name} is not looking for work.{c['reset']}")
            return None

        companion_type = getattr(target, 'companion_type', 'Fighter')
        level = getattr(target, 'companion_level', target.level)
        scale = getattr(target, 'companion_scale', True)

        cost_info = CompanionManager.calculate_cost(level, companion_type)
        hire_cost = getattr(target, 'hire_cost', cost_info['hire_cost'])
        upkeep = getattr(target, 'upkeep_cost', cost_info['upkeep'])

        if player.gold < hire_cost:
            await player.send(f"{c['red']}You need {hire_cost} gold to hire {target.name}.{c['reset']}")
            return None

        # Pay and hire
        player.gold -= hire_cost

        companion = Companion(0, player.world, player, companion_type)
        companion.name = target.name
        companion.short_desc = target.short_desc
        companion.long_desc = target.long_desc
        companion.scale_with_owner = scale
        companion.initialize_level(level if not scale else player.level)
        companion.payment = hire_cost
        companion.daily_upkeep = upkeep
        companion.order = 'follow'

        if not hasattr(player, 'companions'):
            player.companions = []
        player.companions.append(companion)

        # Remove hireable NPC from world
        if target.room and target in target.room.characters:
            target.room.characters.remove(target)
        if target in player.world.npcs:
            player.world.npcs.remove(target)

        # Add companion to room/world
        companion.room = player.room
        if player.room:
            player.room.characters.append(companion)
        player.world.npcs.append(companion)

        await player.send(f"{c['green']}You hire {companion.name} as a {companion_type}. Upkeep: {upkeep} gold/day.{c['reset']}")
        return companion

    @staticmethod
    async def dismiss_companion(player: 'Player', companion: Companion):
        c = player.config.COLORS
        if companion.room and companion in companion.room.characters:
            companion.room.characters.remove(companion)
        if companion in player.world.npcs:
            player.world.npcs.remove(companion)
        if hasattr(player, 'companions') and companion in player.companions:
            player.companions.remove(companion)
        await player.send(f"{c['yellow']}{companion.name} nods and departs.{c['reset']}")

    @staticmethod
    async def apply_daily_upkeep(world: 'World'):
        """Charge upkeep once per in-game day."""
        c = Config().COLORS
        for player in world.players.values():
            if not hasattr(player, 'companions'):
                continue

            # Ensure only once per day
            current_day = (world.game_time.year, world.game_time.month, world.game_time.day)
            if getattr(player, 'last_companion_upkeep_day', None) == current_day:
                continue

            companions = CompanionManager.get_player_companions(player)
            if not companions:
                player.last_companion_upkeep_day = current_day
                continue

            total_upkeep = sum(cmp.daily_upkeep for cmp in companions)
            if total_upkeep <= 0:
                player.last_companion_upkeep_day = current_day
                continue

            if player.gold >= total_upkeep:
                player.gold -= total_upkeep
                await player.send(f"{c['cyan']}You pay {total_upkeep} gold to maintain your companions.{c['reset']}")
            else:
                await player.send(f"{c['red']}You cannot afford your companions' upkeep! Morale drops.{c['reset']}")
                for cmp in companions:
                    cmp.morale = max(0, cmp.morale - 10)
                    cmp.loyalty = max(0, cmp.loyalty - 5)
                    if cmp.morale <= 0:
                        await CompanionManager.dismiss_companion(player, cmp)

            player.last_companion_upkeep_day = current_day

    @staticmethod
    def find_companion(player: 'Player', name: str) -> Optional[Companion]:
        for cmp in CompanionManager.get_player_companions(player):
            if name.lower() in cmp.name.lower():
                return cmp
        return None

    @staticmethod
    async def order_companion(player: 'Player', companion: Companion, action: str, target_name: str = ''):
        c = player.config.COLORS
        action = action.lower()

        if action in ('follow', 'stay', 'defend', 'heal', 'attack'):
            companion.order = action
            if action == 'stay':
                companion.ai_state['staying'] = True
            else:
                companion.ai_state['staying'] = False

            # Clear ordered target unless explicitly attacking
            if action != 'attack' and 'ordered_target' in companion.ai_state:
                companion.ai_state.pop('ordered_target', None)

            if action == 'attack' and target_name:
                # Find target in room
                target = None
                for char in player.room.characters:
                    if char != player and target_name.lower() in char.name.lower():
                        target = char
                        break
                if target:
                    companion.ai_state['ordered_target'] = target
                else:
                    await player.send(f"{c['yellow']}You don't see {target_name} here.{c['reset']}")
                    return

            await player.send(f"{c['green']}{companion.name} acknowledges your order.{c['reset']}")
        else:
            await player.send(f"{c['yellow']}Valid orders: attack, defend, follow, stay, heal{c['reset']}")
