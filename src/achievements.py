"""
Achievement System for Misthollow

Tracks player accomplishments and awards titles/bonuses.
Achievements are checked on relevant events (kills, levels, exploration, etc.)
"""

import logging
from typing import Dict, List, Optional, TYPE_CHECKING, Any
from dataclasses import dataclass, field
from datetime import datetime

if TYPE_CHECKING:
    from player import Player

logger = logging.getLogger(__name__)


@dataclass
class Achievement:
    """Definition of an achievement."""
    id: str
    name: str
    description: str
    category: str  # combat, exploration, social, progression, collection, class, wealth
    icon: str  # emoji
    points: int  # achievement points
    target: int = 0  # target value for progress tracking (0 = no progress bar)
    reward_title: Optional[str] = None  # title player can display
    reward_title_prefix: Optional[str] = None  # prefix title
    reward_gold: int = 0
    reward_xp: int = 0
    reward_stat_bonus: Optional[Dict[str, int]] = None  # e.g. {'str': 1, 'con': 1}
    hidden: bool = False  # hidden until unlocked
    progress_key: Optional[str] = None  # key in achievement_progress dict


# Achievement definitions
ACHIEVEMENTS: Dict[str, Achievement] = {
    # === THE BESTIARY (docs/GAMEPLAY_POLISH.md group 4): creatures catalogued ===
    'bestiary_10': Achievement(id='bestiary_10', name='Field Notes', description='Catalogue 10 creatures in your bestiary',
                               category='exploration', icon='📖', points=10, target=10, progress_key='bestiary',
                               reward_gold=200, reward_xp=400),
    'bestiary_25': Achievement(id='bestiary_25', name='Naturalist', description='Catalogue 25 creatures in your bestiary',
                               category='exploration', icon='📖', points=20, target=25, progress_key='bestiary',
                               reward_gold=600, reward_xp=1500, reward_title='the Naturalist'),
    'bestiary_50': Achievement(id='bestiary_50', name='Beastwise', description='Catalogue 50 creatures in your bestiary',
                               category='exploration', icon='📖', points=30, target=50, progress_key='bestiary',
                               reward_gold=1500, reward_xp=5000, reward_title='the Beastwise', reward_stat_bonus={'wis': 1}),
    'bestiary_100': Achievement(id='bestiary_100', name='Keeper of Beasts', description='Catalogue 100 creatures in your bestiary',
                                category='exploration', icon='📖', points=50, target=100, progress_key='bestiary',
                                reward_gold=4000, reward_xp=15000, reward_title='Keeper of Beasts', reward_stat_bonus={'int': 1, 'wis': 1}),
    'bestiary_200': Achievement(id='bestiary_200', name='The Living Almanac', description='Catalogue 200 creatures in your bestiary',
                                category='exploration', icon='📖', points=100, target=200, progress_key='bestiary',
                                reward_gold=10000, reward_xp=40000, reward_title='the Living Almanac', reward_stat_bonus={'int': 2, 'wis': 2}),
    # === COMBAT ===
    'first_blood': Achievement(
        id='first_blood',
        name='First Blood',
        description='Defeat your first enemy',
        category='combat',
        icon='⚔️',
        points=5,
        target=1,
        progress_key='kills',
        reward_xp=50,
    ),
    'slayer_10': Achievement(
        id='slayer_10',
        name='Monster Slayer',
        description='Defeat 10 enemies',
        category='combat',
        icon='💀',
        points=10,
        target=10,
        progress_key='kills',
    ),
    'slayer_100': Achievement(
        id='slayer_100',
        name='Slayer',
        description='Defeat 100 enemies',
        category='combat',
        icon='💀',
        points=25,
        target=100,
        progress_key='kills',
        reward_title='the Slayer',
    ),
    'slayer_1000': Achievement(
        id='slayer_1000',
        name='Death Incarnate',
        description='Defeat 1000 enemies',
        category='combat',
        icon='☠️',
        points=50,
        target=1000,
        progress_key='kills',
        reward_title='Death Incarnate',
        reward_stat_bonus={'str': 1, 'dex': 1},
    ),
    'boss_slayer': Achievement(
        id='boss_slayer',
        name='Boss Hunter',
        description='Defeat your first boss',
        category='combat',
        icon='🐉',
        points=25,
        reward_xp=500,
        reward_title='the Boss Hunter',
    ),
    'dragon_slayer': Achievement(
        id='dragon_slayer',
        name='Dragon Slayer',
        description='Defeat a dragon',
        category='combat',
        icon='🐲',
        points=50,
        reward_title='the Dragon Slayer',
        reward_stat_bonus={'str': 2},
    ),
    'horseman_slayer': Achievement(
        id='horseman_slayer',
        name='Apocalypse Averted',
        description='Defeat all Four Horsemen',
        category='combat',
        icon='🏇',
        points=100,
        reward_title='Apocalypse Survivor',
        reward_stat_bonus={'str': 1, 'con': 1, 'dex': 1},
        hidden=True,
    ),
    'deathless': Achievement(
        id='deathless',
        name='Deathless',
        description='Reach level 10 without dying',
        category='combat',
        icon='🛡️',
        points=50,
        reward_title='the Deathless',
        reward_stat_bonus={'con': 2},
        hidden=True,
    ),
    'survivor': Achievement(
        id='survivor',
        name='Survivor',
        description='Die and return from the dead',
        category='combat',
        icon='💫',
        points=5,
    ),
    'death_10': Achievement(
        id='death_10',
        name='Familiar with Death',
        description='Die 10 times',
        category='combat',
        icon='👻',
        points=10,
        target=10,
        progress_key='deaths',
        hidden=True,
    ),

    # === EXPLORATION ===
    'explorer_10': Achievement(
        id='explorer_10',
        name='Explorer',
        description='Visit 10 different rooms',
        category='exploration',
        icon='🗺️',
        points=5,
        target=10,
        progress_key='rooms_visited',
    ),
    'explorer_100': Achievement(
        id='explorer_100',
        name='Wanderer',
        description='Visit 100 different rooms',
        category='exploration',
        icon='🗺️',
        points=15,
        target=100,
        progress_key='rooms_visited',
        reward_title='the Wanderer',
    ),
    'explorer_500': Achievement(
        id='explorer_500',
        name='Cartographer',
        description='Visit 500 different rooms',
        category='exploration',
        icon='🗺️',
        points=30,
        target=500,
        progress_key='rooms_visited',
        reward_title='the Cartographer',
        reward_stat_bonus={'wis': 1},
    ),
    'zone_complete': Achievement(
        id='zone_complete',
        name='Zone Master',
        description='Visit every room in a zone',
        category='exploration',
        icon='✅',
        points=20,
        reward_title='the Zone Master',
    ),
    'world_traveler': Achievement(
        id='world_traveler',
        name='World Traveler',
        description='Visit at least one room in every zone',
        category='exploration',
        icon='🌍',
        points=75,
        reward_title='World Traveler',
        reward_stat_bonus={'wis': 2, 'cha': 1},
    ),
    'midgaard_native': Achievement(
        id='midgaard_native',
        name='Garathorm Native',
        description='Visit every room in Garathorm',
        category='exploration',
        icon='🏰',
        points=25,
        reward_title='of Garathorm',
    ),
    'secret_room': Achievement(
        id='secret_room',
        name='Secret Seeker',
        description='Discover a hidden room',
        category='exploration',
        icon='🔍',
        points=15,
        hidden=True,
    ),
    'deathtrap_survivor': Achievement(
        id='deathtrap_survivor',
        name='Cheating Death',
        description='Enter a deathtrap and... well, die',
        category='exploration',
        icon='💀',
        points=5,
        hidden=True,
    ),

    # === PROGRESSION ===
    'level_5': Achievement(
        id='level_5',
        name='Apprentice Adventurer',
        description='Reach level 5',
        category='progression',
        icon='📈',
        points=10,
        target=5,
        progress_key='level',
        reward_gold=100,
    ),
    'level_10': Achievement(
        id='level_10',
        name='Journeyman',
        description='Reach level 10',
        category='progression',
        icon='📈',
        points=20,
        target=10,
        progress_key='level',
        reward_gold=250,
        reward_title='the Journeyman',
    ),
    'level_20': Achievement(
        id='level_20',
        name='Veteran',
        description='Reach level 20',
        category='progression',
        icon='📈',
        points=30,
        target=20,
        progress_key='level',
        reward_gold=500,
        reward_title='the Veteran',
    ),
    'level_30': Achievement(
        id='level_30',
        name='Elite',
        description='Reach level 30',
        category='progression',
        icon='📈',
        points=50,
        target=30,
        progress_key='level',
        reward_gold=1000,
        reward_title='the Elite',
    ),
    'level_40': Achievement(
        id='level_40',
        name='Champion',
        description='Reach level 40',
        category='progression',
        icon='🏆',
        points=75,
        target=40,
        progress_key='level',
        reward_gold=2000,
        reward_title='the Champion',
    ),
    'level_50': Achievement(
        id='level_50',
        name='Hero of the Realm',
        description='Reach level 50',
        category='progression',
        icon='👑',
        points=100,
        target=50,
        progress_key='level',
        reward_gold=5000,
        reward_title='Hero of the Realm',
        reward_stat_bonus={'str': 1, 'int': 1, 'wis': 1, 'dex': 1, 'con': 1, 'cha': 1},
    ),

    # === CLASS ===
    'master_warrior': Achievement(
        id='master_warrior',
        name='Master Warrior',
        description='Reach level 50 as a Warrior',
        category='class',
        icon='⚔️',
        points=75,
        reward_title='Master Warrior',
        reward_stat_bonus={'str': 2, 'con': 1},
    ),
    'master_mage': Achievement(
        id='master_mage',
        name='Master Mage',
        description='Reach level 50 as a Mage',
        category='class',
        icon='🔮',
        points=75,
        reward_title='Master Mage',
        reward_stat_bonus={'int': 2, 'wis': 1},
    ),
    'master_cleric': Achievement(
        id='master_cleric',
        name='Master Cleric',
        description='Reach level 50 as a Cleric',
        category='class',
        icon='✝️',
        points=75,
        reward_title='Master Cleric',
        reward_stat_bonus={'wis': 2, 'cha': 1},
    ),
    'master_thief': Achievement(
        id='master_thief',
        name='Master Thief',
        description='Reach level 50 as a Thief',
        category='class',
        icon='🗡️',
        points=75,
        reward_title='Master Thief',
        reward_stat_bonus={'dex': 2, 'cha': 1},
    ),
    'master_ranger': Achievement(
        id='master_ranger',
        name='Master Ranger',
        description='Reach level 50 as a Ranger',
        category='class',
        icon='🏹',
        points=75,
        reward_title='Master Ranger',
        reward_stat_bonus={'dex': 2, 'wis': 1},
    ),
    'master_paladin': Achievement(
        id='master_paladin',
        name='Master Paladin',
        description='Reach level 50 as a Paladin',
        category='class',
        icon='🛡️',
        points=75,
        reward_title='Master Paladin',
        reward_stat_bonus={'str': 1, 'wis': 1, 'cha': 1},
    ),
    'master_necromancer': Achievement(
        id='master_necromancer',
        name='Master Necromancer',
        description='Reach level 50 as a Necromancer',
        category='class',
        icon='💀',
        points=75,
        reward_title='Master Necromancer',
        reward_stat_bonus={'int': 2, 'con': 1},
    ),
    'master_bard': Achievement(
        id='master_bard',
        name='Master Bard',
        description='Reach level 50 as a Bard',
        category='class',
        icon='🎵',
        points=75,
        reward_title='Master Bard',
        reward_stat_bonus={'cha': 2, 'dex': 1},
    ),
    'master_assassin': Achievement(
        id='master_assassin',
        name='Master Assassin',
        description='Reach level 50 as an Assassin',
        category='class',
        icon='🔪',
        points=75,
        reward_title='Master Assassin',
        reward_stat_bonus={'dex': 2, 'int': 1},
    ),
    'talent_specialist': Achievement(
        id='talent_specialist',
        name='Talent Specialist',
        description='Max out a talent tree',
        category='class',
        icon='🌟',
        points=50,
        reward_title='the Specialist',
        reward_stat_bonus={'str': 1, 'int': 1},
    ),
    'doctrine_devoted': Achievement(
        id='doctrine_devoted',
        name='Doctrine Devoted',
        description='Evolve all 6 warrior abilities',
        category='class',
        icon='⚔️',
        points=75,
        reward_title='the Devoted',
        reward_stat_bonus={'str': 2, 'con': 2},
        hidden=True,
    ),

    # === SOCIAL ===
    'first_friend': Achievement(
        id='first_friend',
        name='First Friend',
        description='Join a group for the first time',
        category='social',
        icon='🤝',
        points=5,
        reward_xp=50,
    ),
    'group_victory': Achievement(
        id='group_victory',
        name='Team Player',
        description='Defeat an enemy while in a group',
        category='social',
        icon='👥',
        points=10,
    ),
    'tutorial_complete': Achievement(
        id='tutorial_complete',
        name='Graduate',
        description='Complete the tutorial',
        category='social',
        icon='🎓',
        points=10,
        reward_xp=100,
    ),
    'quest_5': Achievement(
        id='quest_5',
        name='Helpful Citizen',
        description='Complete 5 quests',
        category='social',
        icon='📜',
        points=15,
        target=5,
        progress_key='quests_done',
    ),
    'helpful': Achievement(
        id='helpful',
        name='Helpful',
        description='Complete 10 quests',
        category='social',
        icon='📜',
        points=25,
        target=10,
        progress_key='quests_done',
        reward_title='the Helpful',
    ),
    'quest_25': Achievement(
        id='quest_25',
        name='Quest Master',
        description='Complete 25 quests',
        category='social',
        icon='📜',
        points=35,
        target=25,
        progress_key='quests_done',
        reward_title='the Quest Master',
        reward_stat_bonus={'cha': 1},
    ),

    # === WEALTH ===
    'first_gold': Achievement(
        id='first_gold',
        name='First Fortune',
        description='Earn your first 100 gold',
        category='wealth',
        icon='💰',
        points=5,
        target=100,
        progress_key='gold_earned',
    ),
    'pocket_change': Achievement(
        id='pocket_change',
        name='Pocket Change',
        description='Earn a total of 1,000 gold',
        category='wealth',
        icon='💰',
        points=10,
        target=1000,
        progress_key='gold_earned',
    ),
    'wealthy': Achievement(
        id='wealthy',
        name='Rich',
        description='Earn a total of 10,000 gold',
        category='wealth',
        icon='💎',
        points=25,
        target=10000,
        progress_key='gold_earned',
        reward_title='the Rich',
    ),
    'dragons_hoard': Achievement(
        id='dragons_hoard',
        name="Dragon's Hoard",
        description='Earn a total of 100,000 gold',
        category='wealth',
        icon='👑',
        points=50,
        target=100000,
        progress_key='gold_earned',
        reward_title="Dragon's Hoard",
        reward_stat_bonus={'cha': 2},
        hidden=True,
    ),
    'hoarder': Achievement(
        id='hoarder',
        name='Hoarder',
        description='Have 50 items in your inventory',
        category='wealth',
        icon='🎒',
        points=10,
        hidden=True,
    ),
    'fully_equipped': Achievement(
        id='fully_equipped',
        name='Fully Equipped',
        description='Have equipment in every slot',
        category='wealth',
        icon='🛡️',
        points=15,
    ),
    'set_collector': Achievement(
        id='set_collector',
        name='Set Collector',
        description='Complete an equipment set',
        category='wealth',
        icon='👔',
        points=30,
        reward_title='the Collector',
    ),

    # === COLLECTION (lore) ===
    'bookworm': Achievement(
        id='bookworm',
        name='Bookworm',
        description='Read your first lore item',
        category='collection',
        icon='📖',
        points=5,
    ),
    'scholar': Achievement(
        id='scholar',
        name='Scholar',
        description='Read 10 different lore items',
        category='collection',
        icon='📚',
        points=20,
        target=10,
        progress_key='lore_read',
        reward_title='the Scholar',
    ),
    'loremaster': Achievement(
        id='loremaster',
        name='Loremaster',
        description='Read 50 different lore items',
        category='collection',
        icon='🏛️',
        points=50,
        target=50,
        progress_key='lore_read',
        reward_title='Loremaster',
        reward_stat_bonus={'int': 1, 'wis': 1},
    ),
}


class AchievementManager:
    """Manages achievement tracking and unlocking."""

    # ----------------------------- progress helpers -----------------------------

    @classmethod
    def _get_progress(cls, player: 'Player', key: str) -> int:
        """Return current progress value for a given key."""
        if not hasattr(player, 'achievement_progress'):
            player.achievement_progress = {}
        return player.achievement_progress.get(key, 0)

    @classmethod
    def _set_progress(cls, player: 'Player', key: str, value: int):
        if not hasattr(player, 'achievement_progress'):
            player.achievement_progress = {}
        player.achievement_progress[key] = value

    @classmethod
    def _inc_progress(cls, player: 'Player', key: str, amount: int = 1) -> int:
        cur = cls._get_progress(player, key) + amount
        cls._set_progress(player, key, cur)
        return cur

    # ----------------------------- stat bonuses --------------------------------

    @classmethod
    def get_stat_bonus(cls, player: 'Player', stat: str) -> int:
        """Get total stat bonus from all earned achievements."""
        if not hasattr(player, 'achievements'):
            return 0
        total = 0
        for ach_id in player.achievements:
            ach = ACHIEVEMENTS.get(ach_id)
            if ach and ach.reward_stat_bonus and stat in ach.reward_stat_bonus:
                total += ach.reward_stat_bonus[stat]
        return total

    # ----------------------------- event hooks ---------------------------------

    @classmethod
    async def check_kill(cls, player: 'Player', victim) -> None:
        """Check kill-related achievements."""
        if not hasattr(player, 'stats'):
            player.stats = {}
        player.stats['kills'] = player.stats.get('kills', 0) + 1
        kills = player.stats['kills']
        cls._set_progress(player, 'kills', kills)

        # Kill milestones
        if kills >= 1:
            await cls.unlock(player, 'first_blood')
        if kills >= 10:
            await cls.unlock(player, 'slayer_10')
        if kills >= 100:
            await cls.unlock(player, 'slayer_100')
        if kills >= 1000:
            await cls.unlock(player, 'slayer_1000')

        # Boss kill
        if hasattr(victim, 'flags') and 'boss' in victim.flags:
            await cls.unlock(player, 'boss_slayer')

            victim_name = getattr(victim, 'name', '').lower()
            if 'dragon' in victim_name:
                await cls.unlock(player, 'dragon_slayer')

            horsemen = ['pestilence', 'war', 'famine', 'death']
            for horseman in horsemen:
                if horseman in victim_name:
                    if not hasattr(player, 'horsemen_killed'):
                        player.horsemen_killed = set()
                    player.horsemen_killed.add(horseman)
                    if len(player.horsemen_killed) >= 4:
                        await cls.unlock(player, 'horseman_slayer')
                    break

        # Group kill
        if hasattr(player, 'group') and player.group:
            await cls.unlock(player, 'group_victory')

    @classmethod
    async def check_level(cls, player: 'Player') -> None:
        """Check level-related achievements."""
        level = player.level
        cls._set_progress(player, 'level', level)

        if level >= 5:
            await cls.unlock(player, 'level_5')
        if level >= 10:
            await cls.unlock(player, 'level_10')
            # Deathless check
            deaths = getattr(player, 'stats', {}).get('deaths', 0)
            if deaths == 0:
                await cls.unlock(player, 'deathless')
        if level >= 20:
            await cls.unlock(player, 'level_20')
        if level >= 30:
            await cls.unlock(player, 'level_30')
        if level >= 40:
            await cls.unlock(player, 'level_40')
        if level >= 50:
            await cls.unlock(player, 'level_50')
            # Class mastery
            class_map = {
                'warrior': 'master_warrior', 'mage': 'master_mage',
                'cleric': 'master_cleric', 'thief': 'master_thief',
                'ranger': 'master_ranger', 'paladin': 'master_paladin',
                'necromancer': 'master_necromancer', 'bard': 'master_bard',
                'assassin': 'master_assassin',
            }
            ach_id = class_map.get(getattr(player, 'char_class', '').lower())
            if ach_id:
                await cls.unlock(player, ach_id)

    @classmethod
    async def check_death(cls, player: 'Player') -> None:
        """Check death-related achievements."""
        if not hasattr(player, 'stats'):
            player.stats = {}
        player.stats['deaths'] = player.stats.get('deaths', 0) + 1
        deaths = player.stats['deaths']
        cls._set_progress(player, 'deaths', deaths)

        if deaths >= 1:
            await cls.unlock(player, 'survivor')
        if deaths >= 10:
            await cls.unlock(player, 'death_10')

    @classmethod
    async def check_exploration(cls, player: 'Player', room_vnum: int) -> None:
        """Check exploration-related achievements."""
        if not hasattr(player, 'visited_rooms'):
            player.visited_rooms = set()

        player.visited_rooms.add(room_vnum)
        visited = len(player.visited_rooms)
        cls._set_progress(player, 'rooms_visited', visited)

        if visited >= 10:
            await cls.unlock(player, 'explorer_10')
        if visited >= 100:
            await cls.unlock(player, 'explorer_100')
        if visited >= 500:
            await cls.unlock(player, 'explorer_500')

        # Zone completion checks (lightweight — only when world available)
        await cls._check_zone_completion(player, room_vnum)

    @classmethod
    async def _check_zone_completion(cls, player: 'Player', room_vnum: int) -> None:
        """Check if the player has visited all rooms in any zone, or all zones."""
        world = getattr(player, 'world', None)
        if not world:
            return
        room = getattr(player, 'room', None)
        if not room or not hasattr(room, 'zone') or not room.zone:
            return

        zone = room.zone
        zone_rooms = set()
        try:
            for r in zone.rooms.values():
                zone_rooms.add(r.vnum)
        except Exception:
            return

        if not zone_rooms:
            return

        visited = getattr(player, 'visited_rooms', set())
        if zone_rooms.issubset(visited):
            await cls.unlock(player, 'zone_complete')
            # Garathorm special
            zone_name = getattr(zone, 'name', '').lower()
            if 'garathorm' in zone_name or 'midgaard' in zone_name or 'midgard' in zone_name:
                await cls.unlock(player, 'midgaard_native')

        # World traveler: visited at least one room in every zone
        try:
            all_zones = list(world.zones.values()) if hasattr(world, 'zones') else []
            if all_zones and len(all_zones) >= 3:  # need at least 3 zones to be meaningful
                zones_visited = 0
                for z in all_zones:
                    z_rooms = set()
                    try:
                        for r in z.rooms.values():
                            z_rooms.add(r.vnum)
                    except Exception:
                        continue
                    if z_rooms and z_rooms & visited:
                        zones_visited += 1
                if zones_visited >= len(all_zones):
                    await cls.unlock(player, 'world_traveler')
        except Exception:
            pass

    @classmethod
    async def check_gold(cls, player: 'Player', amount: int = 0) -> None:
        """Check gold-related achievements. amount = gold just earned (positive)."""
        if amount > 0:
            cls._inc_progress(player, 'gold_earned', amount)

        earned = cls._get_progress(player, 'gold_earned')

        if earned >= 100:
            await cls.unlock(player, 'first_gold')
        if earned >= 1000:
            await cls.unlock(player, 'pocket_change')
        if earned >= 10000:
            await cls.unlock(player, 'wealthy')
        if earned >= 100000:
            await cls.unlock(player, 'dragons_hoard')

    @classmethod
    async def check_quest_complete(cls, player: 'Player', quest_id: str) -> None:
        """Check quest-related achievements."""
        if not hasattr(player, 'stats'):
            player.stats = {}
        player.stats['quests_completed'] = player.stats.get('quests_completed', 0) + 1
        quests = player.stats['quests_completed']
        cls._set_progress(player, 'quests_done', quests)

        if quest_id.startswith('tutorial_9'):
            await cls.unlock(player, 'tutorial_complete')

        if quests >= 5:
            await cls.unlock(player, 'quest_5')
        if quests >= 10:
            await cls.unlock(player, 'helpful')
        if quests >= 25:
            await cls.unlock(player, 'quest_25')

    @classmethod
    async def check_group_join(cls, player: 'Player') -> None:
        """Called when a player joins a group."""
        await cls.unlock(player, 'first_friend')

    @classmethod
    async def check_equipment(cls, player: 'Player') -> None:
        """Check equipment-related achievements."""
        slots = ['head', 'neck', 'body', 'arms', 'hands', 'waist', 'legs',
                 'feet', 'wield', 'shield', 'held', 'about', 'wrist', 'finger']
        filled = sum(1 for slot in slots if player.equipment.get(slot))
        if filled >= 10:
            await cls.unlock(player, 'fully_equipped')
        if len(player.inventory) >= 50:
            await cls.unlock(player, 'hoarder')

    @classmethod
    async def check_talent_mastery(cls, player: 'Player') -> None:
        """Check if the player has maxed a talent tree."""
        try:
            from talents import TalentManager
            if TalentManager.has_maxed_tree(player):
                await cls.unlock(player, 'talent_specialist')
        except Exception:
            pass

    @classmethod
    async def check_doctrine_devoted(cls, player: 'Player') -> None:
        """Check if a warrior has evolved all 6 abilities."""
        evolutions = getattr(player, 'ability_evolutions', {})
        if len(evolutions) >= 6:
            await cls.unlock(player, 'doctrine_devoted')

    @classmethod
    async def check_secret_room(cls, player: 'Player') -> None:
        await cls.unlock(player, 'secret_room')

    @classmethod
    async def check_deathtrap(cls, player: 'Player') -> None:
        await cls.unlock(player, 'deathtrap_survivor')

    @classmethod
    async def record_lore_found(cls, player: 'Player', item) -> None:
        if not hasattr(player, 'lore_read'):
            player.lore_read = set()
        item_vnum = getattr(item, 'vnum', None)
        if item_vnum and item_vnum not in player.lore_read:
            player.lore_read.add(item_vnum)
            count = len(player.lore_read)
            cls._set_progress(player, 'lore_read', count)
            if count >= 1:
                await cls.unlock(player, 'bookworm')
            if count >= 10:
                await cls.unlock(player, 'scholar')
            if count >= 50:
                await cls.unlock(player, 'loremaster')

    @classmethod
    async def record_secret_found(cls, player: 'Player', room_vnum: int) -> None:
        if not hasattr(player, 'secret_rooms_found'):
            player.secret_rooms_found = set()
        player.secret_rooms_found.add(room_vnum)
        await cls.check_secret_room(player)

    # ----------------------------- unlock & display ----------------------------

    @classmethod
    async def check_bestiary(cls, player: 'Player', count: int) -> None:
        """The bestiary's milestones: so many creatures catalogued (journal.py)."""
        cls._set_progress(player, 'bestiary', count)
        for aid, a in ACHIEVEMENTS.items():
            if a.progress_key == 'bestiary' and count >= (a.target or 0):
                await cls.unlock(player, aid)

    @classmethod
    async def unlock(cls, player: 'Player', achievement_id: str) -> bool:
        """Unlock an achievement for a player."""
        if achievement_id not in ACHIEVEMENTS:
            return False

        if not hasattr(player, 'achievements'):
            player.achievements = {}

        if achievement_id in player.achievements:
            return False

        achievement = ACHIEVEMENTS[achievement_id]

        player.achievements[achievement_id] = {
            'earned': True,
            'progress': achievement.target or 1,
            'timestamp': datetime.now().isoformat(),
            'points': achievement.points,
        }

        c = player.config.COLORS

        # Announcement to player
        await player.send(f"\n{c['bright_yellow']}★ ACHIEVEMENT UNLOCKED ★{c['reset']}")
        await player.send(f"{c['bright_cyan']}{achievement.icon} {achievement.name}{c['reset']}")
        await player.send(f"{c['white']}{achievement.description}{c['reset']}")
        await player.send(f"{c['yellow']}+{achievement.points} achievement points{c['reset']}")
        wm = getattr(getattr(player, 'world', None), 'web_map', None)
        if wm:
            try:
                await wm.notify_event(player, {'type': 'world_achievement', 'name': achievement.name, 'icon': achievement.icon,
                                               'desc': achievement.description, 'points': achievement.points,
                                               'title': achievement.reward_title or achievement.reward_title_prefix})
            except Exception:
                pass

        # Grant rewards
        if achievement.reward_xp > 0:
            if hasattr(player, 'gain_exp'):
                await player.gain_exp(achievement.reward_xp, source='other')
            else:
                player.exp = getattr(player, 'exp', 0) + achievement.reward_xp
            await player.send(f"{c['bright_green']}+{achievement.reward_xp} XP{c['reset']}")

        if achievement.reward_gold > 0:
            player.gold += achievement.reward_gold
            await player.send(f"{c['bright_yellow']}+{achievement.reward_gold} gold{c['reset']}")

        if achievement.reward_stat_bonus:
            parts = []
            for stat, val in achievement.reward_stat_bonus.items():
                parts.append(f"+{val} {stat.upper()}")
            await player.send(f"{c['bright_green']}Stat bonus: {', '.join(parts)} (permanent){c['reset']}")

        title = achievement.reward_title or achievement.reward_title_prefix
        if title:
            if not hasattr(player, 'available_titles'):
                player.available_titles = []
            if title not in player.available_titles:
                player.available_titles.append(title)
                await player.send(f"{c['bright_magenta']}New title unlocked: '{title}'{c['reset']}")

        await player.send("")

        # Broadcast to room
        if getattr(player, 'room', None):
            await player.room.send_to_room(
                f"{c['bright_yellow']}★ {player.name} earned the achievement: "
                f"{achievement.icon} {achievement.name}! ★{c['reset']}",
                exclude=[player]
            )

        # Broadcast to server for rare achievements (50+ points)
        if achievement.points >= 50 and hasattr(player, 'world') and player.world:
            try:
                await player.world.broadcast(
                    f"{c['bright_yellow']}★★★ {player.name} earned: "
                    f"{achievement.icon} {achievement.name}! ★★★{c['reset']}",
                    exclude=[player]
                )
            except Exception:
                pass

        # Save
        try:
            await player.save()
        except Exception:
            pass

        logger.info(f"Player {player.name} unlocked achievement: {achievement.name}")
        return True

    @classmethod
    def get_player_points(cls, player: 'Player') -> int:
        if not hasattr(player, 'achievements'):
            return 0
        return sum(a.get('points', 0) for a in player.achievements.values())

    @classmethod
    def get_player_achievements(cls, player: 'Player') -> List[str]:
        if not hasattr(player, 'achievements'):
            return []
        return list(player.achievements.keys())

    @classmethod
    def _progress_bar(cls, current: int, target: int, width: int = 15) -> str:
        """Render a progress bar like [████░░░░░░] 40%"""
        if target <= 0:
            return ""
        pct = min(100, int((current / target) * 100))
        filled = int((pct / 100) * width)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}] {pct}%"

    @classmethod
    async def show_achievements(cls, player: 'Player', category: Optional[str] = None) -> None:
        """Show achievements to player with progress bars."""
        c = player.config.COLORS

        unlocked = cls.get_player_achievements(player)
        total_points = cls.get_player_points(player)
        max_points = sum(a.points for a in ACHIEVEMENTS.values())

        await player.send(f"\n{c['bright_cyan']}═══════════════════════════════════════{c['reset']}")
        await player.send(f"{c['bright_cyan']}         ★ ACHIEVEMENTS ★{c['reset']}")
        await player.send(f"{c['bright_cyan']}═══════════════════════════════════════{c['reset']}")
        await player.send(f"{c['yellow']}Points: {total_points}/{max_points}{c['reset']}")
        await player.send(f"{c['white']}Unlocked: {len(unlocked)}/{len(ACHIEVEMENTS)}{c['reset']}")
        await player.send("")

        # Group by category
        categories = {}
        for ach_id, ach in ACHIEVEMENTS.items():
            if category and ach.category != category:
                continue
            if ach.category not in categories:
                categories[ach.category] = []
            categories[ach.category].append((ach_id, ach))

        category_names = {
            'combat': '⚔️ Combat',
            'exploration': '🗺️ Exploration',
            'progression': '📈 Progression',
            'class': '🎓 Class',
            'social': '👥 Social',
            'wealth': '💰 Wealth',
            'collection': '📚 Collection',
        }

        cat_order = ['combat', 'exploration', 'progression', 'class', 'social', 'wealth', 'collection']
        for cat in cat_order:
            if cat not in categories:
                continue
            achievements = categories[cat]
            cat_name = category_names.get(cat, cat.title())
            await player.send(f"{c['bright_white']}{cat_name}{c['reset']}")

            for ach_id, ach in achievements:
                is_unlocked = ach_id in unlocked

                if ach.hidden and not is_unlocked:
                    await player.send(f"  {c['bright_black']}??? - Hidden achievement{c['reset']}")
                    continue

                if is_unlocked:
                    status = f"{c['bright_green']}✓{c['reset']}"
                    name_color = c['bright_white']
                else:
                    status = f"{c['bright_black']}○{c['reset']}"
                    name_color = c['white']

                points_str = f"{c['yellow']}[{ach.points}]{c['reset']}"

                # Build progress info
                progress_str = ""
                if not is_unlocked and ach.target > 0 and ach.progress_key:
                    current = cls._get_progress(player, ach.progress_key)
                    progress_str = f" {c['cyan']}{cls._progress_bar(current, ach.target)}{c['reset']}"

                reward_hints = []
                if ach.reward_title:
                    reward_hints.append(f"title: {ach.reward_title}")
                if ach.reward_stat_bonus:
                    parts = [f"+{v}{k[:3]}" for k, v in ach.reward_stat_bonus.items()]
                    reward_hints.append(' '.join(parts))
                reward_str = f" {c['bright_black']}({', '.join(reward_hints)}){c['reset']}" if reward_hints else ""

                await player.send(f"  {status} {ach.icon} {name_color}{ach.name}{c['reset']} {points_str}{progress_str}{reward_str}")
                await player.send(f"      {c['bright_black']}{ach.description}{c['reset']}")

            await player.send("")

        await player.send(f"{c['bright_cyan']}═══════════════════════════════════════{c['reset']}")

    @classmethod
    async def show_titles(cls, player: 'Player') -> None:
        """Show available titles from achievements."""
        c = player.config.COLORS
        titles = getattr(player, 'available_titles', [])
        if not titles:
            await player.send(f"{c['yellow']}You haven't earned any titles yet. Complete achievements to unlock titles!{c['reset']}")
            return

        await player.send(f"\n{c['bright_cyan']}═══ Available Titles ═══{c['reset']}")
        current = getattr(player, 'title', 'the Adventurer')
        for i, title in enumerate(titles, 1):
            marker = f" {c['bright_green']}(current){c['reset']}" if title == current else ""
            await player.send(f"  {c['white']}{i}. {c['bright_yellow']}{title}{c['reset']}{marker}")
        await player.send(f"\n{c['cyan']}Use 'title <name>' to set your title, or 'title none' for default.{c['reset']}")

    @classmethod
    async def set_title(cls, player: 'Player', title_text: str) -> None:
        """Set the player's title from earned titles."""
        c = player.config.COLORS
        titles = getattr(player, 'available_titles', [])

        if title_text.lower() in ('none', 'default', 'reset'):
            player.title = 'the Adventurer'
            await player.send(f"{c['bright_green']}Title reset to 'the Adventurer'.{c['reset']}")
            return

        # Try matching by number
        try:
            idx = int(title_text) - 1
            if 0 <= idx < len(titles):
                player.title = titles[idx]
                await player.send(f"{c['bright_green']}Title set to '{player.title}'.{c['reset']}")
                return
        except ValueError:
            pass

        # Try matching by name (case-insensitive partial)
        lower = title_text.lower()
        for title in titles:
            if lower in title.lower():
                player.title = title
                await player.send(f"{c['bright_green']}Title set to '{player.title}'.{c['reset']}")
                return

        await player.send(f"{c['red']}You haven't earned that title. Use 'title' to see available titles.{c['reset']}")
