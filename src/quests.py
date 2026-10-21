"""
Quest System

Provides a simple quest system for kill/fetch quests with:
- Quest definitions (JSON format)
- Progress tracking
- Rewards (XP, gold, items)
- Quest giver NPCs
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING, Any
from dataclasses import dataclass, field


def _push(player):
    """/play's quest tracker follows a quest at once: a talk, a kill or a window opened moves
    no one, and the map payload (which carries the tracker) otherwise comes only with a move."""
    wm = getattr(getattr(player, 'world', None), 'web_map', None)
    if wm is None or not hasattr(wm, 'notify_player'):
        return
    try:
        import asyncio
        if hasattr(wm, 'has_play') and not wm.has_play(player):
            return
        asyncio.get_running_loop().create_task(wm.notify_player(player))
    except Exception:
        pass

async def _progress(player, quest, obj):
    """A step of an ordinary quest: the line (dimmed on /play), and a quest_progress event the
    page shows as a toast (the tracker follows by _push)."""
    import msgkind
    c = player.config.COLORS
    await msgkind.send_ui(player, f"{c['yellow']}Quest Progress: {obj.description} ({obj.current}/{obj.required}){c['reset']}")
    if obj.completed:
        await msgkind.send_ui(player, f"{c['bright_green']}Objective complete!{c['reset']}")
    wm = getattr(getattr(player, 'world', None), 'web_map', None)
    if wm is None or not hasattr(wm, 'has_play') or not wm.has_play(player):
        return
    try:
        await wm.notify_event(player, {'type': 'quest_progress', 'quest': getattr(quest, 'name', ''),
                                       'objective': obj.description, 'current': obj.current,
                                       'required': obj.required, 'done': bool(obj.completed)})
    except Exception:
        pass

if TYPE_CHECKING:
    from player import Player
    from mobs import Mobile

logger = logging.getLogger(__name__)


@dataclass
class QuestObjective:
    """A single quest objective (kill X, collect Y, etc.)."""
    type: str  # 'kill', 'collect', 'talk', 'visit', 'explore', 'escort'
    description: str
    target: str  # Mob name, item vnum, npc vnum, or room vnum
    current: int = 0
    required: int = 1
    completed: bool = False

    def check_progress(self) -> bool:
        """Check if objective is complete."""
        if self.current >= self.required:
            self.completed = True
        return self.completed

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'type': self.type,
            'description': self.description,
            'target': self.target,
            'current': self.current,
            'required': self.required,
            'completed': self.completed
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'QuestObjective':
        """Load from dictionary."""
        return cls(
            type=data['type'],
            description=data['description'],
            target=data['target'],
            current=data.get('current', 0),
            required=data.get('required', 1),
            completed=data.get('completed', False)
        )


@dataclass
class ActiveQuest:
    """An active quest that a player is working on."""
    quest_id: str
    name: str
    description: str
    quest_type: str
    objectives: List[QuestObjective]
    rewards: Dict[str, Any]
    started_at: datetime
    time_limit: Optional[int] = None  # Minutes

    def is_complete(self) -> bool:
        """Check if all objectives are complete."""
        return all(obj.completed for obj in self.objectives)

    def is_expired(self) -> bool:
        """Check if quest has expired (time limit)."""
        if not self.time_limit:
            return False
        elapsed = (datetime.now() - self.started_at).total_seconds() / 60
        return elapsed >= self.time_limit

    def get_progress_string(self) -> str:
        """Get a string representation of quest progress."""
        lines = []
        for i, obj in enumerate(self.objectives, 1):
            status = "✓" if obj.completed else " "
            lines.append(f"  [{status}] {obj.description} ({obj.current}/{obj.required})")
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'quest_id': self.quest_id,
            'name': self.name,
            'description': self.description,
            'quest_type': self.quest_type,
            'objectives': [obj.to_dict() for obj in self.objectives],
            'rewards': self.rewards,
            'started_at': self.started_at.isoformat(),
            'time_limit': self.time_limit
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ActiveQuest':
        """Load from dictionary."""
        return cls(
            quest_id=data['quest_id'],
            name=data['name'],
            description=data['description'],
            quest_type=data['quest_type'],
            objectives=[QuestObjective.from_dict(obj) for obj in data['objectives']],
            rewards=data['rewards'],
            started_at=datetime.fromisoformat(data['started_at']),
            time_limit=data.get('time_limit')
        )


@dataclass
class DialogueChoice:
    """A dialogue choice with optional effects."""
    text: str
    next_node: Optional[str] = None
    effects: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DialogueNode:
    """Dialogue node for NPC conversations."""
    text: str
    choices: List[DialogueChoice] = field(default_factory=list)
    end: bool = False


# Quest definitions (could be loaded from JSON files)
QUEST_DEFINITIONS = {
    # ========== THE TRIAL OF UNLEARNING (respec, all brackets) ==========
    # Completing any Trial resets your talents and frees you to choose a
    # new Path (lone wolf / fellowship). Difficulty scales by bracket.
    'trial_of_unlearning_novice': {
        'name': 'Trial of Unlearning',
        'description': 'Sage Aldric can cleanse what you have learned - if you prove your '
                       'humility. Walk to the temple altar and reflect.',
        'type': 'visit',
        'level_min': 1,
        'level_max': 19,
        'quest_giver': 3200,
        'objectives': [
            {'type': 'visit', 'description': 'Reflect at the temple altar', 'target': 3054, 'required': 1},
        ],
        'rewards': {'exp': 50, 'gold': 0, 'items': [], 'respec': True},
        'repeatable': True,
    },
    'trial_of_unlearning_adept': {
        'name': 'Trial of Unlearning',
        'description': 'The adept\'s trial: a pilgrimage beyond comfort. Visit the altar, '
                       'then stand at the gates of the city you defend.',
        'type': 'visit',
        'level_min': 20,
        'level_max': 39,
        'quest_giver': 3200,
        'objectives': [
            {'type': 'visit', 'description': 'Reflect at the temple altar', 'target': 3054, 'required': 1},
            {'type': 'visit', 'description': 'Stand outside the west gate', 'target': 3052, 'required': 1},
            {'type': 'visit', 'description': 'Stand outside the east gate', 'target': 3053, 'required': 1},
        ],
        'rewards': {'exp': 200, 'gold': 0, 'items': [], 'respec': True},
        'repeatable': True,
    },
    'trial_of_unlearning_master': {
        'name': 'Trial of Unlearning',
        'description': 'The master\'s trial: carry your doubts to the edge of the dragon\'s '
                       'domain and back. Few return unchanged.',
        'type': 'visit',
        'level_min': 40,
        'level_max': 70,
        'quest_giver': 3200,
        'objectives': [
            {'type': 'visit', 'description': 'Reflect at the temple altar', 'target': 3054, 'required': 1},
            {'type': 'visit', 'description': 'Reach the mountain pass of the Dragon\'s Domain', 'target': 8000, 'required': 1},
        ],
        'rewards': {'exp': 800, 'gold': 0, 'items': [], 'respec': True},
        'repeatable': True,
    },

    # ========== BEGINNER QUESTS (Level 1-10) ==========
    'rat_problem': {
        'name': 'Rat Problem',
        'description': 'The sewers are overrun with rats! Help clear them out before they spread disease.',
        'type': 'kill',
        'level_min': 1,
        'level_max': 8,
        'quest_giver': 7090,  # Skullcap the Rat-Catcher
        'objectives': [
            {'type': 'kill', 'description': 'Slay sewer rats', 'target': 'rat', 'required': 8}
        ],
        'rewards': {'exp': 300, 'gold': 75, 'items': []},
        'repeatable': True
    },
    'goblin_menace': {
        'name': 'The Goblin Menace',
        'description': "Goblins from Miden'Nir have been raiding the roads. Put an end to their threat!",
        'type': 'kill',
        'level_min': 3,
        'level_max': 12,
        'quest_giver': 6090,  # Ranger Thornwood
        'objectives': [
            {'type': 'kill', 'description': 'Slay goblins', 'target': 'goblin', 'required': 10}
        ],
        'rewards': {'exp': 600, 'gold': 150, 'items': []},
        'repeatable': False
    },


    'herbal_remedy': {
        'name': 'Herbal Remedy',
        'description': 'The healers need fresh herbs for their remedies. Gather them from the wilds.',
        'type': 'collect',
        'level_min': 1,
        'level_max': 10,
        'quest_giver': 3105,  # Mayor
        'objectives': [
            {'type': 'collect', 'description': 'Gather healing herbs', 'target': '9004', 'required': 3}
        ],
        'rewards': {'exp': 200, 'gold': 60, 'items': []},
        'repeatable': True
    },
    'scout_temple': {
        'name': 'Scout the Temple',
        'description': 'Make sure the Temple of Garathorm is safe. Report once you have visited.',
        'type': 'visit',
        'level_min': 1,
        'level_max': 12,
        'quest_giver': 3006,  # Captain Stolar
        'objectives': [
            {'type': 'visit', 'description': 'Visit the Temple of Garathorm', 'target': '3001', 'required': 1}
        ],
        'rewards': {'exp': 250, 'gold': 80, 'items': []},
        'repeatable': True
    },
    'message_for_mayor': {
        'name': 'Message for the Mayor',
        'description': 'Captain Stolar needs you to deliver a message to the Mayor of Garathorm.',
        'type': 'talk',
        'level_min': 2,
        'level_max': 15,
        'quest_giver': 3006,  # Captain Stolar
        'objectives': [
            {'type': 'talk', 'description': 'Speak with the Mayor', 'target': '3105', 'required': 1}
        ],
        'rewards': {'exp': 300, 'gold': 100, 'items': []},
        'repeatable': False
    },

    # ========== INTERMEDIATE QUESTS (Level 8-20) ==========
    'orc_invasion': {
        'name': 'Orc Invasion',
        'description': 'Orcs from the Enclave are preparing to attack! Strike first and thin their numbers.',
        'type': 'kill',
        'level_min': 8,
        'level_max': 18,
        'quest_giver': 10090,  # Scout Harken
        'objectives': [
            {'type': 'kill', 'description': 'Slay orcs', 'target': 'orc', 'required': 15}
        ],
        'rewards': {'exp': 1200, 'gold': 300, 'items': []},
        'repeatable': False
    },
    'spider_infestation': {
        'name': 'Spider Infestation',
        'description': 'Giant spiders have infested Arachnos! Clear them before they spread to the roads.',
        'type': 'kill',
        'level_min': 10,
        'level_max': 20,
        'quest_giver': 6090,  # Ranger Thornwood
        'objectives': [
            {'type': 'kill', 'description': 'Slay giant spiders', 'target': 'spider', 'required': 12}
        ],
        'rewards': {'exp': 1500, 'gold': 350, 'items': []},
        'repeatable': False
    },
    'moria_depths': {
        'name': 'Depths of Moria',
        'description': 'The orcs in Moria grow bold. Venture into the mines and reduce their numbers.',
        'type': 'kill',
        'level_min': 12,
        'level_max': 22,
        'quest_giver': 4050,  # Grimjaw the Prospector
        'objectives': [
            {'type': 'kill', 'description': 'Slay Moria orcs', 'target': 'orc', 'required': 20}
        ],
        'rewards': {'exp': 2000, 'gold': 500, 'items': []},
        'repeatable': False
    },

    # ========== ADVANCED QUESTS (Level 15-30) ==========
    'drow_threat': {
        'name': 'The Drow Threat',
        'description': 'Dark elves stir in the underground city. Investigate and eliminate their scouts.',
        'type': 'kill',
        'level_min': 15,
        'level_max': 28,
        'quest_giver': 6590,  # Zilara the Shadow Exile
        'objectives': [
            {'type': 'kill', 'description': 'Slay drow', 'target': 'drow', 'required': 10}
        ],
        'rewards': {'exp': 2500, 'gold': 600, 'items': []},
        'repeatable': False
    },
    'undead_purge': {
        'name': 'Undead Purge',
        'description': 'The Necropolis teems with undead abominations. Destroy them before they march on the living!',
        'type': 'kill',
        'level_min': 20,
        'level_max': 35,
        'quest_giver': 14090,  # Paladin Dawnguard
        'objectives': [
            {'type': 'kill', 'description': 'Destroy zombies', 'target': 'zombie', 'required': 10},
            {'type': 'kill', 'description': 'Destroy skeletons', 'target': 'skeleton', 'required': 10}
        ],
        'rewards': {'exp': 4000, 'gold': 1000, 'items': []},
        'repeatable': False
    },
    'desert_raiders': {
        'name': 'Desert Raiders',
        'description': 'Nomad raiders are attacking caravans in the Great Desert. End their reign of terror.',
        'type': 'kill',
        'level_min': 18,
        'level_max': 30,
        'quest_giver': 5290,  # Captain Varro
        'objectives': [
            {'type': 'kill', 'description': 'Slay nomad raiders', 'target': 'nomad', 'required': 15}
        ],
        'rewards': {'exp': 3000, 'gold': 800, 'items': []},
        'repeatable': False
    },

    # ========== ELITE QUESTS (Level 25-45) ==========
    'demon_hunter': {
        'name': 'Demon Hunter',
        'description': 'Demons have begun emerging from portals. Hunt them down before they grow too numerous!',
        'type': 'kill',
        'level_min': 25,
        'level_max': 45,
        'quest_giver': 16090,  # Arcanist Veyla
        'objectives': [
            {'type': 'kill', 'description': 'Slay demons', 'target': 'demon', 'required': 8}
        ],
        'rewards': {'exp': 6000, 'gold': 2000, 'items': []},
        'repeatable': False
    },
    'dragon_slayer': {
        'name': 'Dragon Slayer',
        'description': 'A dragon terrorizes the land! Only the bravest heroes dare face such a creature.',
        'type': 'kill',
        'level_min': 30,
        'level_max': 50,
        'quest_giver': 8090,  # Drakon the Dragon Hunter
        'objectives': [
            {'type': 'kill', 'description': 'Slay a dragon', 'target': 'dragon', 'required': 1}
        ],
        'rewards': {'exp': 10000, 'gold': 5000, 'items': []},
        'repeatable': False
    },
    'elemental_mastery': {
        'name': 'Elemental Mastery',
        'description': 'Rogue elementals threaten the balance of nature. Destroy them to restore order.',
        'type': 'kill',
        'level_min': 28,
        'level_max': 45,
        'quest_giver': 16090,  # Arcanist Veyla
        'objectives': [
            {'type': 'kill', 'description': 'Slay elementals', 'target': 'elemental', 'required': 6}
        ],
        'rewards': {'exp': 5000, 'gold': 1500, 'items': []},
        'repeatable': False
    },

    # ========== REPEATABLE DAILY QUESTS ==========
    'bounty_hunter': {
        'name': 'Bounty Hunter',
        'description': 'The city needs dangerous creatures culled. Hunt them for a reward.',
        'type': 'kill',
        'level_min': 5,
        'level_max': 50,
        'quest_giver': 3006,  # Captain Stolar
        'objectives': [
            {'type': 'kill', 'description': 'Slay dangerous creatures', 'target': 'any', 'required': 25}
        ],
        'rewards': {'exp': 1000, 'gold': 250, 'items': []},
        'repeatable': True
    },
    'sewer_cleanup': {
        'name': 'Sewer Cleanup',
        'description': 'The sewers always need cleaning. Help keep them clear of vermin.',
        'type': 'kill',
        'level_min': 1,
        'level_max': 15,
        'quest_giver': 7090,  # Skullcap the Rat-Catcher
        'objectives': [
            {'type': 'kill', 'description': 'Clear sewer creatures', 'target': 'any', 'required': 15}
        ],
        'rewards': {'exp': 400, 'gold': 100, 'items': []},
        'repeatable': True
    },

    # ========== HIDDEN DUNGEON QUEST CHAIN ==========
    'forgotten_passage': {
        'name': 'The Forgotten Passage',
        'description': 'Rumors speak of a hidden entrance near the Common Square. Investigate and report back.',
        'type': 'visit',
        'level_min': 10,
        'level_max': 30,
        'quest_giver': 7090,  # Skullcap the Rat-Catcher
        'objectives': [
            {'type': 'visit', 'description': 'Find the hidden passage', 'target': '3074', 'required': 1}
        ],
        'rewards': {'exp': 500, 'gold': 150, 'items': []},
        'repeatable': False,
        'next_quest': 'sewer_king'
    },
    'sewer_king': {
        'name': 'The Sewer King',
        'description': 'A monstrous rat-man called the Sewer King rules the depths. End his reign of terror!',
        'type': 'kill',
        'level_min': 12,
        'level_max': 25,
        'quest_giver': 7090,  # Skullcap the Rat-Catcher
        'objectives': [
            {'type': 'kill', 'description': 'Slay the Sewer King', 'target': 'sewer king', 'required': 1}
        ],
        'rewards': {'exp': 2000, 'gold': 500, 'items': []},
        'repeatable': False,
        'next_quest': 'shadow_assassin'
    },
    'shadow_assassin': {
        'name': 'The Shadow Assassin',
        'description': 'Something darker lurks beyond the Sewer King\'s domain. Hunt the shadow assassin!',
        'type': 'kill',
        'level_min': 18,
        'level_max': 30,
        'quest_giver': 7090,  # Skullcap the Rat-Catcher
        'objectives': [
            {'type': 'kill', 'description': 'Slay the Shadow Assassin', 'target': 'shadow assassin', 'required': 1}
        ],
        'rewards': {'exp': 3500, 'gold': 800, 'items': []},
        'repeatable': False,
        'next_quest': 'ancient_guardian'
    },
    'ancient_guardian': {
        'name': 'The Ancient Guardian',
        'description': 'An ancient golem guards something precious in the deepest vault. Defeat it and claim the treasure!',
        'type': 'kill',
        'level_min': 22,
        'level_max': 35,
        'quest_giver': 7090,  # Skullcap the Rat-Catcher
        'objectives': [
            {'type': 'kill', 'description': 'Defeat the Ancient Guardian', 'target': 'ancient guardian', 'required': 1}
        ],
        'rewards': {'exp': 5000, 'gold': 1500, 'items': [3128]},
        'repeatable': False
    },

    # ========== CITY PATROL QUESTS ==========
    'street_patrol': {
        'name': 'Street Patrol',
        'description': 'Pickpockets and urchins are causing trouble in the alleys. Help restore order.',
        'type': 'kill',
        'level_min': 3,
        'level_max': 12,
        'quest_giver': 3006,  # Captain Stolar
        'objectives': [
            {'type': 'kill', 'description': 'Deal with troublemakers', 'target': 'pickpocket', 'required': 3},
            {'type': 'kill', 'description': 'Chase off street urchins', 'target': 'street urchin', 'required': 5}
        ],
        'rewards': {'exp': 400, 'gold': 120, 'items': []},
        'repeatable': True
    },
    'tavern_trouble': {
        'name': 'Tavern Trouble',
        'description': 'The Grubby Inn is getting rowdy. Help calm things down before someone gets hurt.',
        'type': 'kill',
        'level_min': 2,
        'level_max': 10,
        'quest_giver': 3046,  # Bartender
        'objectives': [
            {'type': 'kill', 'description': 'Subdue drunk patrons', 'target': 'drunk patron', 'required': 3}
        ],
        'rewards': {'exp': 250, 'gold': 75, 'items': []},
        'repeatable': True
    },
    'rat_exterminator': {
        'name': 'Rat Exterminator',
        'description': 'Rats are infesting the lower passages. Clear them out!',
        'type': 'kill',
        'level_min': 1,
        'level_max': 8,
        'quest_giver': 3110,  # Temple Guide
        'objectives': [
            {'type': 'kill', 'description': 'Kill rats', 'target': 'rat', 'required': 10}
        ],
        'rewards': {'exp': 150, 'gold': 40, 'items': []},
        'repeatable': True
    },
    'bank_tour': {
        'name': 'Visit the Bank',
        'description': 'Learn about banking! Visit the First National Bank of Garathorm and check your balance.',
        'type': 'visit',
        'level_min': 1,
        'level_max': 10,
        'quest_giver': 3110,  # Temple Guide
        'objectives': [
            {'type': 'visit', 'description': 'Visit the bank', 'target': '3069', 'required': 1}
        ],
        'rewards': {'exp': 100, 'gold': 50, 'items': []},
        'repeatable': False
    },

    # ========== FOREST OF SHADOWS QUESTS ==========
    'forest_exploration': {
        'name': 'Into the Forest',
        'description': 'Explore the Forest of Shadows south of the west gate. Report back on what you find.',
        'type': 'visit',
        'level_min': 5,
        'level_max': 20,
        'quest_giver': 6090,  # Ranger Thornwood
        'objectives': [
            {'type': 'visit', 'description': 'Explore the forest edge', 'target': '20001', 'required': 1},
            {'type': 'visit', 'description': 'Find the hidden glade', 'target': '20010', 'required': 1}
        ],
        'rewards': {'exp': 400, 'gold': 100, 'items': []},
        'repeatable': False,
        'next_quest': 'wolf_hunt'
    },
    'wolf_hunt': {
        'name': 'Wolf Hunt',
        'description': 'The forest wolves are growing bold. Thin their numbers before they threaten travelers.',
        'type': 'kill',
        'level_min': 5,
        'level_max': 15,
        'quest_giver': 6090,  # Ranger Thornwood
        'objectives': [
            {'type': 'kill', 'description': 'Slay forest wolves', 'target': 'forest wolf', 'required': 8},
            {'type': 'kill', 'description': 'Slay dire wolves', 'target': 'dire wolf', 'required': 3}
        ],
        'rewards': {'exp': 600, 'gold': 200, 'items': []},
        'repeatable': True
    },
    'spider_infestation': {
        'name': 'Spider Infestation',
        'description': 'Giant spiders have taken over part of the forest. Clear them out!',
        'type': 'kill',
        'level_min': 6,
        'level_max': 18,
        'quest_giver': 6090,  # Ranger Thornwood
        'objectives': [
            {'type': 'kill', 'description': 'Kill giant spiders', 'target': 'giant spider', 'required': 10},
            {'type': 'kill', 'description': 'Kill venomous spiders', 'target': 'venomous spider', 'required': 5}
        ],
        'rewards': {'exp': 800, 'gold': 250, 'items': []},
        'repeatable': True,
        'next_quest': 'spider_queen'
    },
    'spider_queen': {
        'name': 'The Spider Queen',
        'description': 'The spiders are led by an ancient queen. Slay her to end the infestation for good!',
        'type': 'kill',
        'level_min': 10,
        'level_max': 20,
        'quest_giver': 6090,  # Ranger Thornwood
        'objectives': [
            {'type': 'kill', 'description': 'Slay the Spider Queen', 'target': 'spider queen', 'required': 1}
        ],
        'rewards': {'exp': 1500, 'gold': 400, 'items': [20003]},
        'repeatable': False
    },
    'alpha_challenge': {
        'name': 'Alpha Challenge',
        'description': 'The Alpha Wolf must be defeated to break the pack\'s grip on the forest.',
        'type': 'kill',
        'level_min': 12,
        'level_max': 22,
        'quest_giver': 6090,  # Ranger Thornwood
        'objectives': [
            {'type': 'kill', 'description': 'Defeat the Alpha Wolf', 'target': 'alpha wolf', 'required': 1}
        ],
        'rewards': {'exp': 2000, 'gold': 500, 'items': [20005]},
        'repeatable': False
    },

    # ========== MAIN STORY QUEST CHAIN ==========
    'awakening_echoes': {
        'name': 'Awakening Echoes',
        'description': 'You awaken with no memory. Find Captain Stolar, the city mentor, and seek answers.',
        'type': 'talk',
        'level_min': 1,
        'level_max': 10,
        'quest_giver': 3006,  # Captain Stolar (mentor)
        'objectives': [
            {'type': 'talk', 'description': 'Speak with Captain Stolar', 'target': '3006', 'required': 1}
        ],
        'rewards': {'exp': 200, 'gold': 50, 'items': []},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a1_awakening'
    },
    'first_steps': {
        'name': 'First Steps',
        'description': 'Prove you can stand on your own. Visit the Temple and swear the oath of service.',
        'type': 'visit',
        'level_min': 1,
        'level_max': 10,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'visit', 'description': 'Visit the Temple of Garathorm', 'target': '3001', 'required': 1}
        ],
        'rewards': {'exp': 250, 'gold': 75, 'items': []},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a1_first_steps'
    },
    'shadow_in_sewers': {
        'name': 'Shadow in the Sewers',
        'description': 'Something twisted is spreading beneath the city. Clear the sewers of tainted vermin.',
        'type': 'kill',
        'level_min': 2,
        'level_max': 10,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Slay sewer rats', 'target': 'rat', 'required': 6}
        ],
        'rewards': {'exp': 300, 'gold': 90, 'items': []},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a1_shadow'
    },
    'corrupted_heart': {
        'name': 'Corrupted Heart',
        'description': 'A corrupted goblin champion stalks the tunnels. End it and bring back proof.',
        'type': 'kill',
        'level_min': 4,
        'level_max': 12,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Slay the corrupted goblin', 'target': 'goblin', 'required': 1}
        ],
        'rewards': {'exp': 500, 'gold': 120, 'items': ['Tainted Sigil']},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a1_boss'
    },
    'whispers_of_dark': {
        'name': 'Whispers of Dark',
        'description': 'Report the sigil to the Mayor and learn of the growing darkness.',
        'type': 'talk',
        'level_min': 5,
        'level_max': 12,
        'quest_giver': 3105,  # Mayor
        'objectives': [
            {'type': 'talk', 'description': 'Speak with the Mayor', 'target': '3105', 'required': 1}
        ],
        'rewards': {'exp': 650, 'gold': 150, 'items': []},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a1_reveal'
    },
    'journey_outward': {
        'name': 'Journey Outward',
        'description': 'Travel beyond the walls and gather allies by thinning the orc ranks.',
        'type': 'kill',
        'level_min': 10,
        'level_max': 20,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Slay orc raiders', 'target': 'orc', 'required': 8}
        ],
        'rewards': {'exp': 1200, 'gold': 300, 'items': []},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a2_journey'
    },
    'forked_path': {
        'name': 'A Forked Path',
        'description': 'The realm demands a choice: aid the villages or chase forbidden power. Speak with the Mayor.',
        'type': 'talk',
        'level_min': 12,
        'level_max': 22,
        'quest_giver': 3105,
        'objectives': [
            {'type': 'talk', 'description': 'Consult the Mayor about your path', 'target': '3105', 'required': 1}
        ],
        'rewards': {'exp': 1400, 'gold': 350, 'items': []},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a2_choice'
    },
    'aid_ashgrove': {
        'name': 'Ashgrove Under Siege',
        'description': 'Aid the village of Ashgrove. Destroy the spider brood threatening the people.',
        'type': 'kill',
        'level_min': 13,
        'level_max': 22,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Slay giant spiders', 'target': 'spider', 'required': 8}
        ],
        'rewards': {'exp': 1600, 'gold': 400, 'items': ['Ashgrove Token']},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a2_aid'
    },
    'seize_relic': {
        'name': 'Relic of the Deep',
        'description': 'Seek the power hidden below. Drive back the drow scouts guarding the relic.',
        'type': 'kill',
        'level_min': 13,
        'level_max': 22,
        'quest_giver': 6590,
        'objectives': [
            {'type': 'kill', 'description': 'Slay drow scouts', 'target': 'drow', 'required': 6}
        ],
        'rewards': {'exp': 1700, 'gold': 450, 'items': ['Obsidian Relic']},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a2_relic'
    },
    'unmask_villain': {
        'name': 'Unmask the Villain',
        'description': 'Evidence points to a traitor within the realm. Return to Captain Stolar.',
        'type': 'talk',
        'level_min': 15,
        'level_max': 24,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'talk', 'description': 'Report your findings to Captain Stolar', 'target': '3006', 'required': 1}
        ],
        'rewards': {'exp': 2000, 'gold': 600, 'items': []},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a2_reveal'
    },
    'siege_prep': {
        'name': 'Gather the Siege',
        'description': 'The assault nears. Cut off desert raiders threatening supply lines.',
        'type': 'kill',
        'level_min': 20,
        'level_max': 30,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Slay nomad raiders', 'target': 'nomad', 'required': 10}
        ],
        'rewards': {'exp': 2600, 'gold': 800, 'items': []},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a3_prep'
    },
    'assault_stronghold': {
        'name': 'Assault the Stronghold',
        'description': 'Strike at the villain’s outer defenses and break the demon wardens.',
        'type': 'kill',
        'level_min': 22,
        'level_max': 30,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Slay demonic wardens', 'target': 'demon', 'required': 6}
        ],
        'rewards': {'exp': 3200, 'gold': 1000, 'items': []},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a3_assault'
    },
    'final_choice': {
        'name': 'The Final Choice',
        'description': 'Before the last battle, decide the fate of the realm. Speak with Captain Stolar.',
        'type': 'talk',
        'level_min': 24,
        'level_max': 30,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'talk', 'description': 'Make your final vow to Captain Stolar', 'target': '3006', 'required': 1}
        ],
        'rewards': {'exp': 3500, 'gold': 1200, 'items': []},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a3_choice'
    },
    'endgame': {
        'name': 'End of the Dark',
        'description': 'Confront the corrupted tyrant in their lair and end the darkness forever.',
        'type': 'kill',
        'level_min': 26,
        'level_max': 35,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Defeat the dark tyrant', 'target': 'dragon', 'required': 1}
        ],
        'rewards': {'exp': 6000, 'gold': 2500, 'items': ['Champion’s Sigil']},
        'repeatable': False,
        'chain_id': 'main_story',
        'chain_stage': 'a3_final'
    },

    # ========== SIDE QUEST CHAINS ==========
    'forest_whispers': {
        'name': 'Forest Whispers',
        'description': 'The forest spirits stir. Speak with the druidic envoy to learn more.',
        'type': 'talk',
        'level_min': 5,
        'level_max': 20,
        'quest_giver': 6090,
        'objectives': [
            {'type': 'talk', 'description': 'Speak with the druidic envoy', 'target': '3105', 'required': 1}
        ],
        'rewards': {'exp': 400, 'gold': 120, 'items': []},
        'repeatable': False,
        'chain_id': 'forest_spirits',
        'chain_stage': 'fs_intro'
    },
    'spirit_bloom': {
        'name': 'Spirit Bloom',
        'description': 'Purge the blighted growths threatening the forest spirits.',
        'type': 'kill',
        'level_min': 6,
        'level_max': 22,
        'quest_giver': 6090,
        'objectives': [
            {'type': 'kill', 'description': 'Destroy blighted creatures', 'target': 'any', 'required': 6}
        ],
        'rewards': {'exp': 700, 'gold': 200, 'items': ['Spirit Bloom']},
        'repeatable': False,
        'chain_id': 'forest_spirits',
        'chain_stage': 'fs_bloom'
    },
    'heart_of_the_wood': {
        'name': 'Heart of the Wood',
        'description': 'Return the Spirit Bloom and receive the forest’s blessing.',
        'type': 'talk',
        'level_min': 8,
        'level_max': 24,
        'quest_giver': 6090,
        'objectives': [
            {'type': 'talk', 'description': 'Return to the druidic envoy', 'target': '3105', 'required': 1}
        ],
        'rewards': {'exp': 900, 'gold': 280, 'items': ['Oakbound Charm']},
        'repeatable': False,
        'chain_id': 'forest_spirits',
        'chain_stage': 'fs_final'
    },
    'dwarven_lineage': {
        'name': 'Dwarven Lineage',
        'description': 'A dwarf elder seeks a lost family crest. Speak with Captain Stolar for leads.',
        'type': 'talk',
        'level_min': 8,
        'level_max': 24,
        'quest_giver': 4050,
        'objectives': [
            {'type': 'talk', 'description': 'Speak with Captain Stolar about the crest', 'target': '3006', 'required': 1}
        ],
        'rewards': {'exp': 500, 'gold': 150, 'items': []},
        'repeatable': False,
        'chain_id': 'dwarven_heritage',
        'chain_stage': 'dh_intro'
    },
    'mine_echoes': {
        'name': 'Echoes in the Mine',
        'description': 'Search the mines for the missing crest by driving back orcs.',
        'type': 'kill',
        'level_min': 10,
        'level_max': 26,
        'quest_giver': 4050,
        'objectives': [
            {'type': 'kill', 'description': 'Slay Moria orcs', 'target': 'orc', 'required': 12}
        ],
        'rewards': {'exp': 900, 'gold': 240, 'items': ['Dwarven Crest']},
        'repeatable': False,
        'chain_id': 'dwarven_heritage',
        'chain_stage': 'dh_mine'
    },
    'oath_of_stone': {
        'name': 'Oath of Stone',
        'description': 'Return the crest and swear the dwarven oath.',
        'type': 'talk',
        'level_min': 12,
        'level_max': 28,
        'quest_giver': 4050,
        'objectives': [
            {'type': 'talk', 'description': 'Return to Captain Stolar', 'target': '3006', 'required': 1}
        ],
        'rewards': {'exp': 1200, 'gold': 300, 'items': ['Stonebound Ring']},
        'repeatable': False,
        'chain_id': 'dwarven_heritage',
        'chain_stage': 'dh_final'
    },
    'shadows_inquiry': {
        'name': 'Shadows Inquiry',
        'description': 'Investigate a string of disappearances in the city.',
        'type': 'talk',
        'level_min': 6,
        'level_max': 22,
        'quest_giver': 3105,
        'objectives': [
            {'type': 'talk', 'description': 'Speak with the Mayor about the disappearances', 'target': '3105', 'required': 1}
        ],
        'rewards': {'exp': 450, 'gold': 140, 'items': []},
        'repeatable': False,
        'chain_id': 'city_mystery',
        'chain_stage': 'cm_intro'
    },
    'trail_of_ashes': {
        'name': 'Trail of Ashes',
        'description': 'Follow the trail to the smugglers by clearing out goblin thugs.',
        'type': 'kill',
        'level_min': 7,
        'level_max': 22,
        'quest_giver': 3105,
        'objectives': [
            {'type': 'kill', 'description': 'Slay goblin thugs', 'target': 'goblin', 'required': 8}
        ],
        'rewards': {'exp': 800, 'gold': 220, 'items': []},
        'repeatable': False,
        'chain_id': 'city_mystery',
        'chain_stage': 'cm_trail'
    },
    'the_last_witness': {
        'name': 'The Last Witness',
        'description': 'Confront the smuggler ringleader and learn the truth.',
        'type': 'talk',
        'level_min': 9,
        'level_max': 24,
        'quest_giver': 3105,
        'objectives': [
            {'type': 'talk', 'description': 'Return with the witness report', 'target': '3105', 'required': 1}
        ],
        'rewards': {'exp': 1100, 'gold': 300, 'items': ['Watcher’s Badge']},
        'repeatable': False,
        'chain_id': 'city_mystery',
        'chain_stage': 'cm_final'
    },
    'lost_lineage': {
        'name': 'Lost Lineage',
        'description': 'A traveler seeks their missing family. Offer your help.',
        'type': 'talk',
        'level_min': 8,
        'level_max': 25,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'talk', 'description': 'Speak with Captain Stolar', 'target': '3006', 'required': 1}
        ],
        'rewards': {'exp': 500, 'gold': 160, 'items': []},
        'repeatable': False,
        'chain_id': 'lost_lineage',
        'chain_stage': 'll_intro'
    },
    'blood_and_bond': {
        'name': 'Blood and Bond',
        'description': 'Retrieve proof of kinship by defeating the bandit captains.',
        'type': 'kill',
        'level_min': 10,
        'level_max': 26,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Slay bandit captains', 'target': 'nomad', 'required': 6}
        ],
        'rewards': {'exp': 900, 'gold': 260, 'items': ['Family Locket']},
        'repeatable': False,
        'chain_id': 'lost_lineage',
        'chain_stage': 'll_bond'
    },
    'homecoming': {
        'name': 'Homecoming',
        'description': 'Bring the proof to the traveler and decide their future.',
        'type': 'talk',
        'level_min': 12,
        'level_max': 28,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'talk', 'description': 'Return to Captain Stolar', 'target': '3006', 'required': 1}
        ],
        'rewards': {'exp': 1200, 'gold': 340, 'items': ['Traveler’s Cloak']},
        'repeatable': False,
        'chain_id': 'lost_lineage',
        'chain_stage': 'll_final'
    },
    'mercy_or_wrath': {
        'name': 'Mercy or Wrath',
        'description': 'A captured raider begs for mercy. Decide their fate.',
        'type': 'talk',
        'level_min': 14,
        'level_max': 30,
        'quest_giver': 3105,
        'objectives': [
            {'type': 'talk', 'description': 'Deliver your judgment', 'target': '3105', 'required': 1}
        ],
        'rewards': {'exp': 900, 'gold': 240, 'items': []},
        'repeatable': False,
        'chain_id': 'moral_dilemma',
        'chain_stage': 'md_choice'
    },
    'aftermath': {
        'name': 'Aftermath',
        'description': 'Deal with the consequences of your decision.',
        'type': 'kill',
        'level_min': 16,
        'level_max': 32,
        'quest_giver': 3105,
        'objectives': [
            {'type': 'kill', 'description': 'Face the raider’s allies', 'target': 'orc', 'required': 6}
        ],
        'rewards': {'exp': 1300, 'gold': 380, 'items': ['Judicator’s Token']},
        'repeatable': False,
        'chain_id': 'moral_dilemma',
        'chain_stage': 'md_final'
    },

    # ========== FACTION QUEST LINES ==========
    'midgaard_guard_duty': {
        'name': 'Guard Duty',
        'description': 'Garathorm needs watchful eyes. Patrol and drive off goblin raiders.',
        'type': 'kill',
        'level_min': 5,
        'level_max': 18,
        'quest_giver': 3002,
        'objectives': [
            {'type': 'kill', 'description': 'Slay goblin raiders', 'target': 'goblin', 'required': 6}
        ],
        'rewards': {'exp': 500, 'gold': 120, 'items': [], 'reputation': {'midgaard': 120}},
        'repeatable': False
    },
    'midgaard_city_watch': {
        'name': 'City Watch',
        'description': 'Help the City Watch root out thieves within Garathorm’s walls.',
        'type': 'kill',
        'level_min': 10,
        'level_max': 25,
        'quest_giver': 3002,
        'min_reputation': {'midgaard': 300},
        'objectives': [
            {'type': 'kill', 'description': 'Deal with thieves', 'target': 'thief', 'required': 6}
        ],
        'rewards': {'exp': 900, 'gold': 220, 'items': [], 'reputation': {'midgaard': 180}},
        'repeatable': False
    },
    'midgaard_honor_guard': {
        'name': 'Honor Guard',
        'description': 'Prove your loyalty by breaking an orcish warband outside the city.',
        'type': 'kill',
        'level_min': 16,
        'level_max': 35,
        'quest_giver': 3105,
        'min_reputation': {'midgaard': 600},
        'objectives': [
            {'type': 'kill', 'description': 'Slay orc warband members', 'target': 'orc', 'required': 10}
        ],
        'rewards': {'exp': 1400, 'gold': 400, 'items': [], 'reputation': {'midgaard': 240}},
        'repeatable': False
    },

    'elves_forest_wardens': {
        'name': 'Forest Wardens',
        'description': 'Protect the sacred forest from encroaching beasts.',
        'type': 'kill',
        'level_min': 6,
        'level_max': 20,
        'quest_giver': 4004,
        'objectives': [
            {'type': 'kill', 'description': 'Cull forest predators', 'target': 'wolf', 'required': 6}
        ],
        'rewards': {'exp': 600, 'gold': 140, 'items': [], 'reputation': {'elves': 120}},
        'repeatable': False
    },
    'elves_sacred_grove': {
        'name': 'Sacred Grove',
        'description': 'Purge corrupt creatures from the sacred grove.',
        'type': 'kill',
        'level_min': 12,
        'level_max': 26,
        'quest_giver': 4004,
        'min_reputation': {'elves': 300},
        'objectives': [
            {'type': 'kill', 'description': 'Destroy corrupted beasts', 'target': 'spider', 'required': 6}
        ],
        'rewards': {'exp': 950, 'gold': 260, 'items': [], 'reputation': {'elves': 200}},
        'repeatable': False
    },
    'elves_starlight_pact': {
        'name': 'Starlight Pact',
        'description': 'Complete the ancient rite under the stars for the Elven elders.',
        'type': 'talk',
        'level_min': 18,
        'level_max': 40,
        'quest_giver': 4004,
        'min_reputation': {'elves': 600},
        'objectives': [
            {'type': 'talk', 'description': 'Swear the Starlight Pact', 'target': '4004', 'required': 1}
        ],
        'rewards': {'exp': 1700, 'gold': 420, 'items': [], 'reputation': {'elves': 260}},
        'repeatable': False
    },

    'dwarves_iron_oath': {
        'name': 'The Iron Oath',
        'description': 'Aid the dwarves in keeping the trade routes safe.',
        'type': 'kill',
        'level_min': 6,
        'level_max': 22,
        'quest_giver': 3003,
        'objectives': [
            {'type': 'kill', 'description': 'Drive off cave raiders', 'target': 'goblin', 'required': 6}
        ],
        'rewards': {'exp': 620, 'gold': 160, 'items': [], 'reputation': {'dwarves': 120}},
        'repeatable': False
    },
    'dwarves_deep_delves': {
        'name': 'Deep Delves',
        'description': 'Clear the deep tunnels of lurking threats.',
        'type': 'kill',
        'level_min': 12,
        'level_max': 28,
        'quest_giver': 3003,
        'min_reputation': {'dwarves': 300},
        'objectives': [
            {'type': 'kill', 'description': 'Slay tunnel beasts', 'target': 'troll', 'required': 4}
        ],
        'rewards': {'exp': 980, 'gold': 280, 'items': [], 'reputation': {'dwarves': 200}},
        'repeatable': False
    },
    'dwarves_rune_forge': {
        'name': 'Rune Forge',
        'description': 'Assist in the forging of a rune-etched masterwork.',
        'type': 'talk',
        'level_min': 18,
        'level_max': 40,
        'quest_giver': 3003,
        'min_reputation': {'dwarves': 600},
        'objectives': [
            {'type': 'talk', 'description': 'Complete the forging ritual', 'target': '3003', 'required': 1}
        ],
        'rewards': {'exp': 1750, 'gold': 440, 'items': [], 'reputation': {'dwarves': 260}},
        'repeatable': False
    },

    'thieves_guild_cutpurse': {
        'name': 'Cutpurse Initiation',
        'description': 'Prove your worth by slipping past the city watch.',
        'type': 'visit',
        'level_min': 6,
        'level_max': 20,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'visit', 'description': 'Slip through Garathorm unnoticed', 'target': '3002', 'required': 1}
        ],
        'rewards': {'exp': 600, 'gold': 180, 'items': [], 'reputation': {'thieves_guild': 120}},
        'repeatable': False
    },
    'thieves_guild_silent_blade': {
        'name': 'Silent Blade',
        'description': 'Eliminate a dangerous informant without raising alarms.',
        'type': 'kill',
        'level_min': 12,
        'level_max': 28,
        'quest_giver': 3006,
        'min_reputation': {'thieves_guild': 300},
        'objectives': [
            {'type': 'kill', 'description': 'Deal with the informer', 'target': 'guard', 'required': 4}
        ],
        'rewards': {'exp': 980, 'gold': 320, 'items': [], 'reputation': {'thieves_guild': 200}},
        'repeatable': False
    },
    'thieves_guild_shadow_king': {
        'name': 'Shadow King',
        'description': 'Establish dominance over rival thieves in the undercity.',
        'type': 'kill',
        'level_min': 18,
        'level_max': 40,
        'quest_giver': 3006,
        'min_reputation': {'thieves_guild': 600},
        'objectives': [
            {'type': 'kill', 'description': 'Defeat rival cutthroats', 'target': 'thief', 'required': 8}
        ],
        'rewards': {'exp': 1750, 'gold': 480, 'items': [], 'reputation': {'thieves_guild': 260}},
        'repeatable': False
    },

    'mages_guild_apprentice': {
        'name': 'Apprentice Trials',
        'description': 'Complete the arcane trials set by the Mages Guild.',
        'type': 'collect',
        'level_min': 6,
        'level_max': 20,
        'quest_giver': 3001,
        'objectives': [
            {'type': 'collect', 'description': 'Gather arcane reagents', 'target': '9004', 'required': 3}
        ],
        'rewards': {'exp': 620, 'gold': 160, 'items': [], 'reputation': {'mages_guild': 120}},
        'repeatable': False
    },
    'mages_guild_archives': {
        'name': 'Arcane Archives',
        'description': 'Recover lost scrolls for the Mages Guild.',
        'type': 'collect',
        'level_min': 12,
        'level_max': 28,
        'quest_giver': 3001,
        'min_reputation': {'mages_guild': 300},
        'objectives': [
            {'type': 'collect', 'description': 'Recover ancient scrolls', 'target': '9005', 'required': 2}
        ],
        'rewards': {'exp': 980, 'gold': 280, 'items': [], 'reputation': {'mages_guild': 200}},
        'repeatable': False
    },
    'mages_guild_ascension': {
        'name': 'Arcane Ascension',
        'description': 'Pass the final trial to join the Conclave.',
        'type': 'talk',
        'level_min': 18,
        'level_max': 40,
        'quest_giver': 3001,
        'min_reputation': {'mages_guild': 600},
        'objectives': [
            {'type': 'talk', 'description': 'Complete the ascension rite', 'target': '3001', 'required': 1}
        ],
        'rewards': {'exp': 1750, 'gold': 460, 'items': [], 'reputation': {'mages_guild': 260}},
        'repeatable': False
    },

    # ========== TUTORIAL QUESTS ==========
    'tutorial_1_awakening': {
        'name': 'Awakening',
        'description': 'Speak with Sage Aldric at the Temple to begin your training. He is right here in the Temple with you. Simply type "talk aldric" to speak with him.',
        'type': 'tutorial',
        'level_min': 1,
        'level_max': 5,
        'quest_giver': 3200,
        'auto_start': True,
        'objectives': [
            {'type': 'talk', 'description': 'Speak with Sage Aldric (type "talk aldric")', 'target': '3200', 'required': 1}
        ],
        'rewards': {'exp': 50, 'gold': 10, 'items': [100]},
        'next_quest': 'tutorial_2_look_around',
        'repeatable': False
    },
    'tutorial_2_look_around': {
        'name': 'Eyes Open',
        'description': 'Learn to observe your surroundings by exploring near the Temple. Go {route:3001>3005} from the Temple to reach {name:3005}, then find {name:3054} ({route:3001>3054} from the Temple).',
        'type': 'tutorial',
        'level_min': 1,
        'level_max': 5,
        'quest_giver': 3200,
        'objectives': [
            {'type': 'visit', 'description': 'Visit {name:3005} (go {route:3001>3005} from the Temple)', 'target': '3005', 'required': 1},
            {'type': 'visit', 'description': 'Visit {name:3054} (go {route:3001>3054} from the Temple)', 'target': '3054', 'required': 1}
        ],
        'rewards': {'exp': 75, 'gold': 15, 'items': [3]},
        'next_quest': 'tutorial_3_know_thyself',
        'repeatable': False
    },
    'tutorial_3_know_thyself': {
        'name': 'Know Thyself',
        'description': 'Learn about your character by checking your stats, gear, and abilities. Try each of these commands: score, equipment, inventory, skills, and spells.',
        'type': 'tutorial',
        'level_min': 1,
        'level_max': 5,
        'quest_giver': 3200,
        'objectives': [
            {'type': 'command', 'description': 'Check your score (type "score")', 'target': 'score', 'required': 1},
            {'type': 'command', 'description': 'View your equipment (type "equipment")', 'target': 'equipment', 'required': 1},
            {'type': 'command', 'description': 'Check your inventory (type "inventory")', 'target': 'inventory', 'required': 1},
            {'type': 'command', 'description': 'View your skills (type "skills")', 'target': 'skills', 'required': 1},
            {'type': 'command', 'description': 'View your spells (type "spells")', 'target': 'spells', 'required': 1}
        ],
        'rewards': {'exp': 200, 'gold': 45, 'practices': 2, 'items': [101]},
        'next_quest': 'tutorial_5_combat',
        'repeatable': False
    },
    'tutorial_5_combat': {
        'name': 'Blood and Steel',
        'description': 'Learn combat by defeating a training dummy at {name:3078}. From the Temple, go {route:3001>3078}.',
        'type': 'tutorial',
        'level_min': 1,
        'level_max': 5,
        'quest_giver': 3200,
        'objectives': [
            {'type': 'visit', 'description': 'Go to {name:3078} ({route:3001>3078} from the Temple)', 'target': '3078', 'required': 1},
            {'type': 'kill', 'description': 'Defeat a training dummy (type "kill dummy")', 'target': 'dummy', 'required': 1}
        ],
        'rewards': {'exp': 150, 'gold': 30},
        'next_quest': 'tutorial_6_healing',
        'repeatable': False
    },
    'tutorial_6_healing': {
        'name': 'The Art of Survival',
        'description': 'Learn to recover from injuries. Try resting, standing back up, and eating food. You can do this anywhere.',
        'type': 'tutorial',
        'level_min': 1,
        'level_max': 5,
        'quest_giver': 3200,
        'objectives': [
            {'type': 'command', 'description': 'Rest to recover (type "rest")', 'target': 'rest', 'required': 1},
            {'type': 'command', 'description': 'Stand back up (type "stand")', 'target': 'stand', 'required': 1},
            {'type': 'command', 'description': 'Eat some food (type "eat bread" or similar)', 'target': 'eat', 'required': 1}
        ],
        'rewards': {'exp': 100, 'gold': 25},
        'next_quest': 'tutorial_7_shopping',
        'repeatable': False
    },
    'tutorial_7_shopping': {
        'name': 'Tools of the Trade',
        'description': 'Learn to buy and sell at shops. From the Temple, go {route:3001>3011} to reach {name:3011}.',
        'type': 'tutorial',
        'level_min': 1,
        'level_max': 5,
        'quest_giver': 3200,
        'objectives': [
            {'type': 'visit', 'description': 'Visit {name:3011} ({route:3001>3011} from the Temple)', 'target': '3011', 'required': 1},
            {'type': 'command', 'description': 'View shop inventory (type "list")', 'target': 'list', 'required': 1},
            {'type': 'command', 'description': 'Buy any item (type "buy <item>")', 'target': 'buy', 'required': 1}
        ],
        'rewards': {'exp': 125, 'gold': 100},
        'next_quest': 'tutorial_8_exploration',
        'repeatable': False
    },
    'tutorial_8_exploration': {
        'name': 'Into the Unknown',
        # progression-01: this used to send newcomers out the EAST gate, where the only
        # creatures are level-4 aggressive goblins; the rabbits, foxes and deer live in
        # the Light Forest beyond the WEST gate (6001 and the shaded paths north of it).
        'description': 'Venture beyond the city walls to the Light Forest and fight a creature there. From the Temple, go {route:3001>6001} to reach the forest trail. Try fighting a rabbit or a fox — they are safe for your level. Return to the Temple when done.',
        'type': 'tutorial',
        'level_min': 1,
        'level_max': 5,
        'quest_giver': 3200,
        'objectives': [
            {'type': 'visit', 'description': 'Reach the trail through the Light Forest ({route:3001>6001} from the Temple)', 'target': '6001', 'required': 1},
            {'type': 'kill', 'description': 'Defeat a creature in the forest (try "kill rabbit" or "kill fox" — the shaded path north has both)', 'target': 'any', 'required': 1},
            {'type': 'visit', 'description': 'Return to the Temple ({route:6001>3001})', 'target': '3001', 'required': 1}
        ],
        'rewards': {'exp': 300, 'gold': 150, 'title': 'the Initiated'},
        'next_quest': 'tutorial_9_newbie_zone',
        'repeatable': False
    },
    # ========== THE SHADOW CONSPIRACY (5-part Main Story Chain) ==========
    'shadow_conspiracy_1': {
        'name': 'Whispers in the Dark',
        'description': "People have been vanishing from Garathorm's streets at night. Captain Stolar suspects foul play. Investigate the disappearance sites and question witnesses.",
        'type': 'visit',
        'category': 'main_story',
        'level_min': 10,
        'level_max': 25,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'visit', 'description': 'Investigate the dark alley near the market', 'target': '3014', 'required': 1},
            {'type': 'visit', 'description': 'Search the abandoned warehouse district', 'target': '3069', 'required': 1},
            {'type': 'talk', 'description': 'Question the night watchman', 'target': '3006', 'required': 1}
        ],
        'rewards': {'exp': 800, 'gold': 200, 'items': []},
        'repeatable': False,
        'chain_id': 'shadow_conspiracy',
        'chain_stage': 'sc_investigate'
    },
    'shadow_conspiracy_2': {
        'name': 'Trail of Shadows',
        'description': "Strange ritual markings at the disappearance sites. Track the clues through the sewers and the forest — someone is leaving a trail of dark magic.",
        'type': 'kill',
        'category': 'main_story',
        'level_min': 12,
        'level_max': 25,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Slay shadow-tainted rats in the sewers', 'target': 'rat', 'required': 6},
            {'type': 'visit', 'description': 'Follow the ritual markings into the forest', 'target': '20010', 'required': 1},
            {'type': 'kill', 'description': 'Defeat the shadow scout', 'target': 'shadow', 'required': 1}
        ],
        'rewards': {'exp': 1200, 'gold': 350, 'items': ['Shadow Sigil Fragment']},
        'repeatable': False,
        'chain_id': 'shadow_conspiracy',
        'chain_stage': 'sc_trail'
    },
    'shadow_conspiracy_3': {
        'name': 'The Cultist Hideout',
        'description': "The shadow sigil leads to a hidden cultist hideout beneath the old ruins. Infiltrate their lair and discover the mastermind.",
        'type': 'kill',
        'category': 'main_story',
        'level_min': 14,
        'level_max': 28,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Defeat cultist acolytes', 'target': 'cultist', 'required': 8},
            {'type': 'kill', 'description': 'Slay the cultist warlock', 'target': 'warlock', 'required': 1},
        ],
        'rewards': {'exp': 2000, 'gold': 600, 'items': ['Cultist Cipher Key']},
        'repeatable': False,
        'chain_id': 'shadow_conspiracy',
        'chain_stage': 'sc_infiltrate'
    },
    'shadow_conspiracy_4': {
        'name': 'The Shadow Lord',
        'description': "The cultists serve a Shadow Lord who plans to tear open a rift to the Plane of Shadows. Stop the ritual and destroy him!",
        'type': 'kill',
        'category': 'main_story',
        'level_min': 16,
        'level_max': 30,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Defeat shadow guardians', 'target': 'shadow', 'required': 4},
            {'type': 'kill', 'description': 'Destroy the Shadow Lord', 'target': 'shadow lord', 'required': 1}
        ],
        'rewards': {'exp': 3500, 'gold': 1000, 'items': ['Shadowbane Amulet']},
        'repeatable': False,
        'chain_id': 'shadow_conspiracy',
        'chain_stage': 'sc_boss'
    },
    'shadow_conspiracy_5': {
        'name': 'Unraveling the Conspiracy',
        'description': "The Shadow Lord's dying words hint at a traitor within Garathorm's walls. Present evidence to the Mayor and expose the conspiracy.",
        'type': 'talk',
        'category': 'main_story',
        'level_min': 18,
        'level_max': 30,
        'quest_giver': 3105,
        'objectives': [
            {'type': 'talk', 'description': 'Present the evidence to the Mayor', 'target': '3105', 'required': 1},
            {'type': 'talk', 'description': 'Confront the traitor with Captain Stolar', 'target': '3006', 'required': 1}
        ],
        'rewards': {'exp': 4000, 'gold': 1500, 'reputation': {'midgaard': 500}},
        'repeatable': False,
        'chain_id': 'shadow_conspiracy',
        'chain_stage': 'sc_reveal'
    },

    # ========== RISE OF THE CLOCKWORK (3-part Dungeon Chain) ==========
    'clockwork_1': {
        'name': 'The Broken Automaton',
        'description': "A dwarven tinkerer found a broken automaton from the ancient Clockwork Foundry. Help gather repair parts from the ruins.",
        'type': 'collect',
        'category': 'dungeon',
        'level_min': 12,
        'level_max': 25,
        'quest_giver': 4050,
        'objectives': [
            {'type': 'kill', 'description': 'Salvage gears from clockwork wreckage', 'target': 'clockwork', 'required': 5},
            {'type': 'talk', 'description': 'Return parts to Grimjaw', 'target': '4050', 'required': 1}
        ],
        'rewards': {'exp': 1000, 'gold': 300, 'reputation': {'dwarves': 150}},
        'repeatable': False,
        'chain_id': 'clockwork_rising',
        'chain_stage': 'cw_repair'
    },
    'clockwork_2': {
        'name': 'Heart of the Foundry',
        'description': "The automaton stirs to life but its memory is corrupted. Venture into the sealed Clockwork Foundry and recover the master control rod from the Forge Guardian.",
        'type': 'kill',
        'category': 'dungeon',
        'level_min': 15,
        'level_max': 28,
        'quest_giver': 4050,
        'objectives': [
            {'type': 'kill', 'description': 'Destroy malfunctioning clockwork soldiers', 'target': 'clockwork', 'required': 10},
            {'type': 'kill', 'description': 'Defeat the Forge Guardian', 'target': 'forge guardian', 'required': 1}
        ],
        'rewards': {'exp': 2500, 'gold': 700, 'items': ['Clockwork Shield'], 'reputation': {'dwarves': 250}},
        'repeatable': False,
        'chain_id': 'clockwork_rising',
        'chain_stage': 'cw_foundry'
    },
    'clockwork_3': {
        'name': 'Activate the Core',
        'description': "With the control rod, reactivate the Foundry's central core. The ancient defense system will fight back — battle through to bring the Foundry online!",
        'type': 'kill',
        'category': 'dungeon',
        'level_min': 18,
        'level_max': 30,
        'quest_giver': 4050,
        'objectives': [
            {'type': 'kill', 'description': 'Defeat clockwork sentinels', 'target': 'sentinel', 'required': 6},
            {'type': 'kill', 'description': 'Destroy the Core Warden', 'target': 'core warden', 'required': 1}
        ],
        'rewards': {'exp': 4000, 'gold': 1200, 'items': ['Clockwork Companion Blueprint'],
                    'reputation': {'dwarves': 400}},
        'repeatable': False,
        'chain_id': 'clockwork_rising',
        'chain_stage': 'cw_core'
    },

    # ========== THE FACTION WAR (3-part Faction Chain) ==========
    'faction_war_1': {
        'name': 'Tensions Rise',
        'description': "The City Guard and the Thieves' Guild are on the brink of war. Both seek your aid. Hear both sides before choosing.",
        'type': 'talk',
        'category': 'faction',
        'level_min': 10,
        'level_max': 30,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'talk', 'description': "Hear the Guard's case from Captain Stolar", 'target': '3006', 'required': 1},
            {'type': 'talk', 'description': "Hear the Guild's case from the Mayor", 'target': '3105', 'required': 1}
        ],
        'rewards': {'exp': 600, 'gold': 150},
        'repeatable': False,
        'chain_id': 'faction_war',
        'chain_stage': 'fw_tensions'
    },
    'faction_war_2_guard': {
        'name': 'For the Guard!',
        'description': "You side with the Guard. Root out guild safe houses and arrest their enforcers.",
        'type': 'kill',
        'category': 'faction',
        'level_min': 12,
        'level_max': 30,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Defeat guild enforcers', 'target': 'thief', 'required': 8},
            {'type': 'kill', 'description': 'Capture the guild lieutenant', 'target': 'guild lieutenant', 'required': 1}
        ],
        'rewards': {'exp': 2000, 'gold': 600, 'items': ['Guard Captain Badge'],
                    'reputation': {'midgaard': 400, 'thieves_guild': -300}},
        'repeatable': False,
        'chain_id': 'faction_war',
        'chain_stage': 'fw_guard'
    },
    'faction_war_2_thieves': {
        'name': "Honor Among Thieves",
        'description': "You side with the Guild. Intercept guard patrols and steal evidence of their corruption.",
        'type': 'kill',
        'category': 'faction',
        'level_min': 12,
        'level_max': 30,
        'quest_giver': 3105,
        'objectives': [
            {'type': 'kill', 'description': 'Ambush corrupt guard patrols', 'target': 'guard', 'required': 8},
        ],
        'rewards': {'exp': 2000, 'gold': 800, 'items': ['Shadowstep Boots'],
                    'reputation': {'thieves_guild': 400, 'midgaard': -300}},
        'repeatable': False,
        'chain_id': 'faction_war',
        'chain_stage': 'fw_thieves'
    },
    'faction_war_3_guard': {
        'name': 'Justice Prevails',
        'description': "Storm the Thieves' Guild headquarters and arrest the Guildmaster!",
        'type': 'kill',
        'category': 'faction',
        'level_min': 15,
        'level_max': 35,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Fight through guild defenders', 'target': 'thief', 'required': 12},
            {'type': 'kill', 'description': 'Defeat the Guildmaster', 'target': 'guildmaster', 'required': 1}
        ],
        'rewards': {'exp': 4000, 'gold': 1500, 'items': ['Sword of Justice'],
                    'reputation': {'midgaard': 600}},
        'repeatable': False,
        'chain_id': 'faction_war',
        'chain_stage': 'fw_guard_finale'
    },
    'faction_war_3_thieves': {
        'name': 'The Great Heist',
        'description': "The ultimate caper: break into the Guard Armory and steal the Commander's war plans to ensure the Guild's survival.",
        'type': 'kill',
        'category': 'faction',
        'level_min': 15,
        'level_max': 35,
        'quest_giver': 3105,
        'objectives': [
            {'type': 'kill', 'description': 'Neutralize armory guards', 'target': 'guard', 'required': 10},
            {'type': 'talk', 'description': 'Deliver plans to the Guildmaster', 'target': '3105', 'required': 1}
        ],
        'rewards': {'exp': 4000, 'gold': 2000, 'items': ['Cloak of Shadows'],
                    'reputation': {'thieves_guild': 600}},
        'repeatable': False,
        'chain_id': 'faction_war',
        'chain_stage': 'fw_thieves_finale'
    },

    # ========== DAILY QUESTS ==========
    'daily_bounty': {
        'name': 'Bounty Board',
        'description': "The bounty board lists dangerous creatures that need culling. Check back daily!",
        'type': 'kill',
        'category': 'daily',
        'level_min': 3,
        'level_max': 50,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Slay bounty targets', 'target': 'any', 'required': 10}
        ],
        'rewards': {'exp': 500, 'gold': 150},
        'repeatable': True,
        'daily': True
    },
    'daily_gather': {
        'name': 'Gather Resources',
        'description': "The city stockpiles run low. Gather materials from the wilds.",
        'type': 'collect',
        'category': 'daily',
        'level_min': 3,
        'level_max': 50,
        'quest_giver': 3105,
        'objectives': [
            {'type': 'collect', 'description': 'Gather resource materials', 'target': '9004', 'required': 5}
        ],
        'rewards': {'exp': 400, 'gold': 120},
        'repeatable': True,
        'daily': True
    },
    'daily_arena': {
        'name': 'Arena Champion',
        'description': "Win arena matches to earn glory and coin!",
        'type': 'kill',
        'category': 'daily',
        'level_min': 5,
        'level_max': 50,
        'quest_giver': 3006,
        'objectives': [
            {'type': 'kill', 'description': 'Win arena matches', 'target': 'arena_win', 'required': 3}
        ],
        'rewards': {'exp': 600, 'gold': 200, 'arena_points': 50},
        'repeatable': True,
        'daily': True
    },

    'tutorial_9_newbie_zone': {
        'name': 'Proving Grounds',
        'description': 'Test your skills in the Newbie Zone! From the Temple, go {route:3001>3061} to reach {name:3061}, then {route:3061>18600} into the Newbie Zone. Defeat 3 creatures there, then return to the Temple.',
        'type': 'tutorial',
        'level_min': 1,
        'level_max': 7,
        'quest_giver': 3200,
        'objectives': [
            {'type': 'visit', 'description': 'Find {name:3061} ({route:3001>3061} from the Temple)', 'target': '3061', 'required': 1},
            {'type': 'visit', 'description': 'Enter the Newbie Zone ({route:3061>18600} from {name:3061})', 'target': '18600', 'required': 1},
            {'type': 'kill', 'description': 'Defeat 3 creatures in the Newbie Zone', 'target': 'any', 'required': 3},
            {'type': 'visit', 'description': 'Return to Sage Aldric at the Temple ({route:18600>3001})', 'target': '3001', 'required': 1}
        ],
        'rewards': {'exp': 500, 'gold': 200},
        'next_quest': 'tutorial_10_skills',
        'repeatable': False
    },
    'tutorial_10_skills': {
        'name': 'Inner Power',
        'description': 'Learn about your class abilities! Check your skills and spells, then use one in or out of combat. Each class has a unique resource — warriors build Rage, mages spend Mana, thieves build Combo Points, and more. Type "score" to see yours!',
        'type': 'tutorial',
        'level_min': 1,
        'level_max': 10,
        'quest_giver': 3200,
        'objectives': [
            {'type': 'command', 'description': 'Check your skills (type "skills")', 'target': 'skills', 'required': 1},
            {'type': 'command', 'description': 'Check your score to see your class resource (type "score")', 'target': 'score', 'required': 1},
        ],
        'rewards': {'exp': 150, 'gold': 50},
        'next_quest': 'tutorial_11_communication',
        'repeatable': False
    },
    'tutorial_11_communication': {
        'name': 'Finding Your Voice',
        'description': 'The Realms are more fun with friends! Learn to communicate with other players. Try the global chat channel and check out the newbie channel for help.',
        'type': 'tutorial',
        'level_min': 1,
        'level_max': 10,
        'quest_giver': 3200,
        'objectives': [
            {'type': 'command', 'description': 'See who is online (type "who")', 'target': 'who', 'required': 1},
            {'type': 'command', 'description': 'Check available channels (type "channel list")', 'target': 'channel', 'required': 1},
        ],
        'rewards': {'exp': 100, 'gold': 25},
        'next_quest': 'tutorial_12_quests_groups',
        'repeatable': False
    },
    'tutorial_12_quests_groups': {
        'name': 'Strength in Numbers',
        'description': 'Learn about quests and grouping! Look for NPCs with [!] above their name — they have quests for you. Check your quest log with "quests". You can also form groups with other players using "group invite <player>".',
        'type': 'tutorial',
        'level_min': 1,
        'level_max': 10,
        'quest_giver': 3200,
        'objectives': [
            {'type': 'command', 'description': 'Check your quest log (type "quests")', 'target': 'quests', 'required': 1},
            {'type': 'command', 'description': 'Learn about groups (type "group")', 'target': 'group', 'required': 1},
        ],
        'rewards': {'exp': 150, 'gold': 50},
        'repeatable': False
    },
}

# Quest chains with branching paths and stages
# ---------------------------------------------------------------- the way there, from the map
# Quest texts name rooms and ways as {name:VNUM} and {route:FROM>TO}; apply_routes fills them in
# from the world as it is loaded ("south twice, then west seven times"), so a tutorial's
# directions stay right however the world is laid out.
_TIMES = {2: 'twice', 3: 'three times', 4: 'four times', 5: 'five times', 6: 'six times', 7: 'seven times',
          8: 'eight times', 9: 'nine times', 10: 'ten times'}
_COMPASS = ('north', 'east', 'south', 'west', 'up', 'down')


def route_dirs(world, start: int, goal: int) -> Optional[List[str]]:
    """The fewest compass steps from one room to another on foot: no barred way into a land
    still being built, and no stepping out onto water while that takes a boat."""
    import collections
    import doors
    from config import Config
    rooms = getattr(world, 'rooms', {}) or {}
    if start not in rooms or goal not in rooms:
        return None
    wet = ('water_swim', 'water_noswim', 'water_surface')
    prev = {start: None}
    q = collections.deque([start])
    while q:
        v = q.popleft()
        if v == goal:
            break
        room = rooms[v]
        for d in _COMPASS:
            ex = (room.exits or {}).get(d)
            if not isinstance(ex, dict) or ex.get('hidden') or doors.is_seal(ex.get('door')):
                continue
            t = ex.get('to_room')
            if t not in rooms or t in prev or 'imm_only' in rooms[t].flags:    # (not through the God Rooms)
                continue
            if Config.WATER_NEEDS_BOAT and rooms[t].sector_type in wet and room.sector_type not in wet:
                continue
            prev[t] = (v, d)
            q.append(t)
    if goal not in prev:
        return None
    dirs, v = [], goal
    while prev[v] is not None:
        v, d = prev[v]
        dirs.append(d)
    return dirs[::-1]


def route_phrase(dirs: List[str]) -> str:
    """['south', 'south', 'west', 'west', 'west'] -> 'south twice, then west three times'."""
    runs = []
    for d in dirs:
        if runs and runs[-1][0] == d:
            runs[-1][1] += 1
        else:
            runs.append([d, 1])
    parts = [d if n == 1 else f"{d} {_TIMES.get(n, f'{n} times')}" for d, n in runs]
    if not parts:
        return 'nowhere: you are there'
    return parts[0] if len(parts) == 1 else ', '.join(parts[:-1]) + ', then ' + parts[-1]


def apply_routes(world) -> List[str]:
    """Fill every {route:A>B} and {name:V} in the quest texts from the loaded world. Returns the
    routes it could not find (the world check fails on any)."""
    import re as _re
    missing = []

    def name(m):
        room = world.rooms.get(int(m.group(1)))
        n = room.name if room else 'that place'
        # "the Temple Fountain" reads on in a sentence; "By The Temple Altar" needs its quotes
        return 'the ' + n[4:] if n.startswith('The ') else f'"{n}"'

    def route(m):
        a, b = int(m.group(1)), int(m.group(2))
        dirs = route_dirs(world, a, b)
        if dirs is None:
            missing.append(f'{a}>{b}')
            return 'the way the guide shows'
        return route_phrase(dirs)
    for qid, q in QUEST_DEFINITIONS.items():
        for holder in [q] + list(q.get('objectives') or []):
            tpl = holder.get('_template') or holder.get('description')
            if not isinstance(tpl, str) or ('{route:' not in tpl and '{name:' not in tpl):
                continue
            holder['_template'] = tpl
            text = _re.sub(r'\{route:(\d+)>(\d+)\}', route, tpl)
            holder['description'] = _re.sub(r'\{name:(\d+)\}', name, text)
    return missing


QUEST_CHAINS = {
    'main_story': {
        'name': 'The Shattered Crown',
        'start_stage': 'a1_awakening',
        'stages': {
            'a1_awakening': {'quest_id': 'awakening_echoes', 'next': 'a1_first_steps', 'act': 'Act I: The Awakening'},
            'a1_first_steps': {'quest_id': 'first_steps', 'next': 'a1_shadow', 'act': 'Act I: The Awakening'},
            'a1_shadow': {'quest_id': 'shadow_in_sewers', 'next': 'a1_boss', 'act': 'Act I: The Awakening'},
            'a1_boss': {'quest_id': 'corrupted_heart', 'next': 'a1_reveal', 'act': 'Act I: The Awakening'},
            'a1_reveal': {'quest_id': 'whispers_of_dark', 'next': 'a2_journey', 'act': 'Act I: The Awakening'},
            'a2_journey': {'quest_id': 'journey_outward', 'next': 'a2_choice', 'act': 'Act II: The Journey'},
            'a2_choice': {
                'quest_id': 'forked_path',
                'act': 'Act II: The Journey',
                'branches': {
                    'path': {
                        'aid': 'a2_aid',
                        'power': 'a2_relic'
                    }
                },
                'next': 'a2_aid'
            },
            'a2_aid': {'quest_id': 'aid_ashgrove', 'next': 'a2_reveal', 'act': 'Act II: The Journey'},
            'a2_relic': {'quest_id': 'seize_relic', 'next': 'a2_reveal', 'act': 'Act II: The Journey'},
            'a2_reveal': {'quest_id': 'unmask_villain', 'next': 'a3_prep', 'act': 'Act II: The Journey'},
            'a3_prep': {'quest_id': 'siege_prep', 'next': 'a3_assault', 'act': 'Act III: The Confrontation'},
            'a3_assault': {'quest_id': 'assault_stronghold', 'next': 'a3_choice', 'act': 'Act III: The Confrontation'},
            'a3_choice': {
                'quest_id': 'final_choice',
                'act': 'Act III: The Confrontation',
                'branches': {
                    'final_vow': {
                        'mercy': 'a3_final',
                        'wrath': 'a3_final'
                    }
                },
                'next': 'a3_final'
            },
            'a3_final': {'quest_id': 'endgame', 'next': None, 'act': 'Act III: The Confrontation'}
        }
    },
    'forest_spirits': {
        'name': 'Whispers of the Grove',
        'start_stage': 'fs_intro',
        'stages': {
            'fs_intro': {'quest_id': 'forest_whispers', 'next': 'fs_bloom'},
            'fs_bloom': {'quest_id': 'spirit_bloom', 'next': 'fs_final'},
            'fs_final': {'quest_id': 'heart_of_the_wood', 'next': None}
        }
    },
    'dwarven_heritage': {
        'name': 'Legacy of Stone',
        'start_stage': 'dh_intro',
        'stages': {
            'dh_intro': {'quest_id': 'dwarven_lineage', 'next': 'dh_mine'},
            'dh_mine': {'quest_id': 'mine_echoes', 'next': 'dh_final'},
            'dh_final': {'quest_id': 'oath_of_stone', 'next': None}
        }
    },
    'city_mystery': {
        'name': 'The Vanishing',
        'start_stage': 'cm_intro',
        'stages': {
            'cm_intro': {'quest_id': 'shadows_inquiry', 'next': 'cm_trail'},
            'cm_trail': {'quest_id': 'trail_of_ashes', 'next': 'cm_final'},
            'cm_final': {'quest_id': 'the_last_witness', 'next': None}
        }
    },
    'lost_lineage': {
        'name': 'Bloodlines',
        'start_stage': 'll_intro',
        'stages': {
            'll_intro': {'quest_id': 'lost_lineage', 'next': 'll_bond'},
            'll_bond': {'quest_id': 'blood_and_bond', 'next': 'll_final'},
            'll_final': {'quest_id': 'homecoming', 'next': None}
        }
    },
    'moral_dilemma': {
        'name': 'Judgment of Ashes',
        'start_stage': 'md_choice',
        'stages': {
            'md_choice': {'quest_id': 'mercy_or_wrath', 'next': 'md_final'},
            'md_final': {'quest_id': 'aftermath', 'next': None}
        }
    },
    'shadow_conspiracy': {
        'name': 'The Shadow Conspiracy',
        'start_stage': 'sc_investigate',
        'stages': {
            'sc_investigate': {'quest_id': 'shadow_conspiracy_1', 'next': 'sc_trail', 'act': 'Part 1: Investigation'},
            'sc_trail': {'quest_id': 'shadow_conspiracy_2', 'next': 'sc_infiltrate', 'act': 'Part 2: The Trail'},
            'sc_infiltrate': {'quest_id': 'shadow_conspiracy_3', 'next': 'sc_boss', 'act': 'Part 3: Infiltration'},
            'sc_boss': {'quest_id': 'shadow_conspiracy_4', 'next': 'sc_reveal', 'act': 'Part 4: Boss Fight'},
            'sc_reveal': {'quest_id': 'shadow_conspiracy_5', 'next': None, 'act': 'Part 5: The Truth'}
        }
    },
    'clockwork_rising': {
        'name': 'Rise of the Clockwork',
        'start_stage': 'cw_repair',
        'stages': {
            'cw_repair': {'quest_id': 'clockwork_1', 'next': 'cw_foundry', 'act': 'Part 1: Repair'},
            'cw_foundry': {'quest_id': 'clockwork_2', 'next': 'cw_core', 'act': 'Part 2: The Foundry'},
            'cw_core': {'quest_id': 'clockwork_3', 'next': None, 'act': 'Part 3: The Core'}
        }
    },
    'faction_war': {
        'name': 'The Faction War',
        'start_stage': 'fw_tensions',
        'stages': {
            'fw_tensions': {
                'quest_id': 'faction_war_1',
                'act': 'Part 1: Choose Your Side',
                'branches': {
                    'faction_side': {
                        'guard': 'fw_guard',
                        'thieves': 'fw_thieves'
                    }
                },
                'next': 'fw_guard'
            },
            'fw_guard': {'quest_id': 'faction_war_2_guard', 'next': 'fw_guard_finale', 'act': 'Part 2: Guard Path'},
            'fw_thieves': {'quest_id': 'faction_war_2_thieves', 'next': 'fw_thieves_finale', 'act': 'Part 2: Thieves Path'},
            'fw_guard_finale': {'quest_id': 'faction_war_3_guard', 'next': None, 'act': 'Part 3: Guard Finale'},
            'fw_thieves_finale': {'quest_id': 'faction_war_3_thieves', 'next': None, 'act': 'Part 3: Thieves Finale'}
        }
    }
}

# Dialogue trees keyed by NPC vnum
DIALOGUE_TREES = {
    3006: {
        'start': DialogueNode(
            text=(
                "The captain studies you with a steady gaze. 'You look like you've seen a ghost.'"
            ),
            choices=[
                DialogueChoice(
                    text="Who am I?",
                    next_node='memory',
                    effects=[{'type': 'set_flag', 'key': 'memory', 'value': 'fractured'}]
                ),
                DialogueChoice(
                    text="I'm ready to help.",
                    next_node='oath',
                    effects=[{'type': 'start_quest', 'quest_id': 'awakening_echoes'}]
                ),
                DialogueChoice(
                    text="Power is all that matters.",
                    next_node='power',
                    effects=[{'type': 'set_flag', 'key': 'path', 'value': 'power'}]
                )
            ]
        ),
        'memory': DialogueNode(
            text="'Your past is a storm. But your future is still yours to claim.'",
            choices=[
                DialogueChoice(
                    text="I'll help the realm.",
                    next_node='oath',
                    effects=[{'type': 'start_quest', 'quest_id': 'awakening_echoes'}]
                )
            ]
        ),
        'oath': DialogueNode(
            text="'Then take your first steps. The realm needs you.'",
            end=True
        ),
        'power': DialogueNode(
            text="'Power without purpose destroys. Choose carefully.'",
            end=True
        ),
        'final_vow': DialogueNode(
            text="'The tyrant falls tonight. Will you show mercy or wrath?'",
            choices=[
                DialogueChoice(
                    text="Mercy. The cycle must end.",
                    next_node='vow_mercy',
                    effects=[{'type': 'set_flag', 'key': 'final_vow', 'value': 'mercy'}]
                ),
                DialogueChoice(
                    text="Wrath. The realm needs fear.",
                    next_node='vow_wrath',
                    effects=[{'type': 'set_flag', 'key': 'final_vow', 'value': 'wrath'}]
                )
            ]
        ),
        'vow_mercy': DialogueNode(
            text="'Then strike true, and spare those who can change.'",
            end=True
        ),
        'vow_wrath': DialogueNode(
            text="'Then let them remember your fury.'",
            end=True
        )
    },
    3105: {
        'start': DialogueNode(
            text="The Mayor leans forward. 'The realm trembles, and we need champions.'",
            choices=[
                DialogueChoice(
                    text="I will aid the villages.",
                    next_node='aid',
                    effects=[{'type': 'set_flag', 'key': 'path', 'value': 'aid'}]
                ),
                DialogueChoice(
                    text="I seek the relics of power.",
                    next_node='power',
                    effects=[{'type': 'set_flag', 'key': 'path', 'value': 'power'}]
                )
            ]
        ),
        'aid': DialogueNode(
            text="'Then go. The people will sing your name.'",
            end=True
        ),
        'power': DialogueNode(
            text="'Dangerous, but the realm may need every edge.'",
            end=True
        )
    }
}


class QuestManager:
    """Manages quest state and progression."""

    @staticmethod
    def _get_chain_state(player: 'Player', chain_id: str, auto_init: bool = False) -> Dict[str, Any]:
        if not hasattr(player, 'quest_chains'):
            player.quest_chains = {}
        state = player.quest_chains.get(chain_id)
        if not state and auto_init:
            chain_def = QUEST_CHAINS.get(chain_id, {})
            state = {
                'stage': chain_def.get('start_stage'),
                'completed': False,
                'choices': {},
                'history': []
            }
            player.quest_chains[chain_id] = state
        return state

    @staticmethod
    def is_chain_quest_available(player: 'Player', quest_def: Dict[str, Any]) -> bool:
        chain_id = quest_def.get('chain_id')
        if not chain_id:
            return True
        chain_def = QUEST_CHAINS.get(chain_id)
        if not chain_def:
            return False
        stage = quest_def.get('chain_stage')
        state = QuestManager._get_chain_state(player, chain_id)
        if not state:
            return stage == chain_def.get('start_stage')
        if state.get('completed'):
            return False
        return state.get('stage') == stage

    @staticmethod
    def record_choice(player: 'Player', key: str, value: str):
        if not hasattr(player, 'quest_flags'):
            player.quest_flags = {}
        player.quest_flags[key] = value

    @staticmethod
    def advance_chain_from_quest(player: 'Player', quest_id: str):
        quest_def = QUEST_DEFINITIONS.get(quest_id)
        if not quest_def:
            return
        chain_id = quest_def.get('chain_id')
        if not chain_id:
            return
        chain_def = QUEST_CHAINS.get(chain_id, {})
        stage = quest_def.get('chain_stage')
        if not stage:
            return
        state = QuestManager._get_chain_state(player, chain_id, auto_init=True)
        stage_def = chain_def.get('stages', {}).get(stage, {})
        next_stage = stage_def.get('next')
        branches = stage_def.get('branches', {})
        for flag_key, branch_map in branches.items():
            choice = player.quest_flags.get(flag_key)
            if choice in branch_map:
                next_stage = branch_map[choice]
                break
        if next_stage:
            state['history'].append(stage)
            state['stage'] = next_stage
        else:
            state['history'].append(stage)
            state['stage'] = None
            state['completed'] = True

    @staticmethod
    async def handle_dialogue(player: 'Player', npc_vnum: int, choice_index: Optional[int] = None) -> bool:
        tree = DIALOGUE_TREES.get(npc_vnum)
        if not tree:
            return False

        if not hasattr(player, 'dialogue_state'):
            player.dialogue_state = {}

        node_id = player.dialogue_state.get(str(npc_vnum), 'start')
        node = tree.get(node_id) or tree.get('start')
        if not node:
            return False

        if choice_index is not None:
            if not node.choices:
                await player.send("There is nothing more to say.")
                return True
            if choice_index < 1 or choice_index > len(node.choices):
                await player.send("That is not a valid response.")
                return True
            choice = node.choices[choice_index - 1]
            for effect in choice.effects:
                effect_type = effect.get('type')
                if effect_type == 'set_flag':
                    QuestManager.record_choice(player, effect.get('key'), effect.get('value'))
                elif effect_type == 'start_quest':
                    await QuestManager.accept_quest(player, effect.get('quest_id'))
                elif effect_type == 'advance_chain':
                    chain_id = effect.get('chain_id')
                    stage = effect.get('stage')
                    if chain_id:
                        state = QuestManager._get_chain_state(player, chain_id, auto_init=True)
                        if stage:
                            state['stage'] = stage
                elif effect_type == 'toll':
                    # a ferryman's fare (rites.py): paid and carried, or refused
                    import rites
                    npc = next((ch for ch in (getattr(player.room, 'characters', None) or [])
                                if getattr(ch, 'vnum', None) == effect.get('npc')), None)
                    if npc is not None:
                        await rites.pay(player, npc)
                    player.dialogue_state.pop(str(npc_vnum), None)
                    return True
                elif effect_type == 'grant_reward':
                    exp = effect.get('exp', 0)
                    gold = effect.get('gold', 0)
                    if exp:
                        player.exp += exp
                    if gold:
                        player.gold += gold

            node_id = choice.next_node or 'start'
            player.dialogue_state[str(npc_vnum)] = node_id
            node = tree.get(node_id) or node

        c = player.config.COLORS
        await player.send(f"{c['bright_cyan']}{node.text}{c['reset']}")
        if node.choices and not node.end:
            await player.send(f"{c['yellow']}Responses:{c['reset']}")
            for idx, choice in enumerate(node.choices, 1):
                await player.send(f"  {idx}. {choice.text}")
            await player.send(f"{c['white']}Use 'talk <npc> <number>' to respond.{c['reset']}")
        if node.end:
            player.dialogue_state.pop(str(npc_vnum), None)
        return True

    @staticmethod
    def get_story_progress(player: 'Player') -> str:
        chain_def = QUEST_CHAINS.get('main_story')
        if not chain_def:
            return "No main story configured."
        state = QuestManager._get_chain_state(player, 'main_story')
        if not state:
            return "Main Story: Not started"
        stage = state.get('stage')
        if state.get('completed'):
            return "Main Story: Completed"
        if not stage:
            return "Main Story: Not started"
        stage_def = chain_def['stages'].get(stage, {})
        quest_id = stage_def.get('quest_id')
        quest_name = QUEST_DEFINITIONS.get(quest_id, {}).get('name', 'Unknown')
        act = stage_def.get('act', 'Main Story')
        return f"{act} - Current: {quest_name}"

    @staticmethod
    def _build_quest_giver_area_map(world) -> Dict[int, str]:
        area_map: Dict[int, str] = {}
        if not world:
            return area_map
        for zone in getattr(world, 'zones', {}).values():
            zone_name = getattr(zone, 'name', 'Unknown')
            for vnum in getattr(zone, 'mobs', {}).keys():
                try:
                    area_map[int(vnum)] = zone_name
                except (TypeError, ValueError):
                    continue
        return area_map

    @staticmethod
    def get_quest_area(player: 'Player', quest_id: Optional[str] = None, quest_def: Optional[Dict[str, Any]] = None) -> Optional[str]:
        if quest_def is None and quest_id:
            quest_def = QUEST_DEFINITIONS.get(quest_id, {})
        if not quest_def:
            return None
        area = quest_def.get('area') or quest_def.get('region') or quest_def.get('zone')
        if area:
            return area
        quest_giver = quest_def.get('quest_giver')
        world = getattr(player, 'world', None)
        if not quest_giver or not world:
            return None
        area_map = getattr(world, '_quest_giver_area_map', None)
        if area_map is None:
            area_map = QuestManager._build_quest_giver_area_map(world)
            setattr(world, '_quest_giver_area_map', area_map)
        try:
            return area_map.get(int(quest_giver))
        except (TypeError, ValueError):
            return None

    @staticmethod
    async def offer_quest(player: 'Player', quest_id: str):
        """
        Offer a quest to the player.

        Args:
            player: The player to offer the quest to
            quest_id: ID of the quest to offer
        """
        quest_def = QUEST_DEFINITIONS.get(quest_id)
        if not quest_def:
            logger.warning(f"Quest {quest_id} not found")
            return

        if not QuestManager.is_chain_quest_available(player, quest_def):
            return

        # Check if player already has this quest
        if QuestManager.has_active_quest(player, quest_id):
            await player.send("You are already working on this quest.")
            return

        # Check if player has completed this quest (and it's not repeatable)
        if not quest_def.get('repeatable', False) and quest_id in player.quests_completed:
            await player.send("You have already completed this quest.")
            return

        # Check level requirements
        if player.level < quest_def.get('level_min', 1):
            await player.send("You are not experienced enough for this quest.")
            return
        if player.level > quest_def.get('level_max', 50):
            await player.send("This quest is beneath your abilities.")
            return

        # Display quest offer
        c = player.config.COLORS
        await player.send(f"\r\n{c['bright_yellow']}Quest Available: {quest_def['name']}{c['reset']}")
        await player.send(f"{c['white']}{quest_def['description']}{c['reset']}\r\n")

        await player.send(f"{c['cyan']}Objectives:{c['reset']}")
        for obj in quest_def['objectives']:
            await player.send(f"  - {obj['description']} (0/{obj['required']})")

        await player.send(f"\r\n{c['green']}Rewards:{c['reset']}")
        if quest_def['rewards'].get('exp'):
            await player.send(f"  - {quest_def['rewards']['exp']} experience")
        if quest_def['rewards'].get('gold'):
            await player.send(f"  - {quest_def['rewards']['gold']} gold")
        if quest_def['rewards'].get('items'):
            await player.send(f"  - Special items")
        if quest_def['rewards'].get('reputation'):
            rep_lines = []
            for key, amount in quest_def['rewards']['reputation'].items():
                rep_lines.append(f"{key} {amount:+d}")
            await player.send(f"  - Reputation: {', '.join(rep_lines)}")

        await player.send(f"\r\n{c['yellow']}Type 'quest accept {quest_id}' to accept this quest.{c['reset']}\r\n")

    @staticmethod
    async def accept_quest(player: 'Player', quest_id: str):
        """
        Accept a quest.

        Args:
            player: The player accepting the quest
            quest_id: ID of the quest to accept
        """
        quest_def = QUEST_DEFINITIONS.get(quest_id)
        if not quest_def:
            await player.send("Unknown quest.")
            return

        if not QuestManager.is_chain_quest_available(player, quest_def):
            await player.send("That quest is not available right now.")
            return

        # Check daily quest cooldown
        if quest_def.get('daily') and not QuestManager.can_accept_daily(player, quest_id):
            await player.send("You've already completed this daily quest today. Come back tomorrow!")
            return

        # Create active quest
        objectives = [
            QuestObjective(
                type=obj['type'],
                description=obj['description'],
                target=str(obj['target']),
                required=obj['required']
            )
            for obj in quest_def['objectives']
        ]

        active_quest = ActiveQuest(
            quest_id=quest_id,
            name=quest_def['name'],
            description=quest_def['description'],
            quest_type=quest_def['type'],
            objectives=objectives,
            rewards=quest_def['rewards'],
            started_at=datetime.now(),
            time_limit=quest_def.get('time_limit')
        )

        if quest_def.get('chain_id'):
            state = QuestManager._get_chain_state(player, quest_def['chain_id'], auto_init=True)
            state['stage'] = quest_def.get('chain_stage', state.get('stage'))

        if not hasattr(player, 'active_quests'):
            player.active_quests = []
        player.active_quests.append(active_quest)
        _push(player)

        c = player.config.COLORS
        await player.send(f"{c['bright_green']}Quest accepted: {quest_def['name']}{c['reset']}")
        # Tutorial step prompt
        if quest_id.startswith('tutorial_'):
            first_obj = quest_def.get('objectives', [{}])[0]
            step_desc = first_obj.get('description')
            if step_desc:
                from quest_guide import for_player
                await player.send(f"{c['bright_cyan']}Tutorial step:{c['reset']} {for_player(player, step_desc)}")
        try:
            from tips import TipManager
            await TipManager.show_tutorial_hint(player, 'tutorial_quest_accept')
        except Exception:
            pass
        logger.info(f"{player.name} accepted quest {quest_id}")

    @staticmethod
    async def _tutorial_next_step(player: 'Player', quest: ActiveQuest):
        if not quest.quest_id.startswith('tutorial_'):
            return
        next_obj = next((obj for obj in quest.objectives if not obj.completed), None)
        c = player.config.COLORS
        if next_obj:
            from quest_guide import for_player
            await player.send(f"{c['bright_cyan']}Next step:{c['reset']} {for_player(player, next_obj.description)}")
        else:
            await player.send(f"{c['bright_green']}Tutorial step complete!{c['reset']}")

    @staticmethod
    async def check_quest_progress(player: 'Player', event_type: str, event_data: Dict):
        """
        Check and update quest progress based on an event.

        Args:
            player: The player whose quests to check
            event_type: Type of event ('kill', 'collect', 'talk', 'visit', 'explore')
            event_data: Data about the event
        """
        if not hasattr(player, 'active_quests'):
            return

        for quest in player.active_quests:
            for obj in quest.objectives:
                if obj.completed:
                    continue

                if obj.type == 'kill' and event_type == 'kill':
                    # Check if killed mob matches target
                    mob_name = event_data.get('mob_name', '').lower()
                    # 'any' target matches any mob kill
                    if obj.target.lower() == 'any' or obj.target.lower() in mob_name:
                        obj.current += 1
                        obj.check_progress()

                        c = player.config.COLORS
                        _push(player)
                        await _progress(player, quest, obj)

                        if obj.completed:
                            await QuestManager._tutorial_next_step(player, quest)

                elif obj.type == 'collect' and event_type == 'collect':
                    # Check if collected item matches target
                    item_vnum = str(event_data.get('item_vnum', ''))
                    item_name = event_data.get('item_name', '').lower()
                    target_name = obj.target.lower()
                    if obj.target == item_vnum or (item_name and target_name in item_name):
                        obj.current += 1
                        obj.check_progress()

                        c = player.config.COLORS
                        _push(player)
                        await _progress(player, quest, obj)

                        if obj.completed:
                            await QuestManager._tutorial_next_step(player, quest)

                elif obj.type == 'talk' and event_type == 'talk':
                    npc_vnum = str(event_data.get('npc_vnum', ''))
                    npc_name = event_data.get('npc_name', '').lower()
                    target_name = obj.target.lower()
                    if obj.target == npc_vnum or (npc_name and target_name in npc_name):
                        obj.current += 1
                        obj.check_progress()

                        c = player.config.COLORS
                        _push(player)
                        await _progress(player, quest, obj)

                        if obj.completed:
                            await QuestManager._tutorial_next_step(player, quest)

                elif obj.type in ('visit', 'explore') and event_type in ('visit', 'explore'):
                    room_vnum = str(event_data.get('room_vnum', ''))
                    if obj.target == room_vnum:
                        obj.current = max(obj.current, 1)
                        obj.check_progress()

                        c = player.config.COLORS
                        _push(player)
                        await _progress(player, quest, obj)

                        if obj.completed:
                            await QuestManager._tutorial_next_step(player, quest)

                elif obj.type == 'command' and event_type == 'command':
                    # Check if command matches target
                    cmd = event_data.get('command', '').lower()
                    target = obj.target.lower()
                    # Match if command starts with target (e.g., 'score' matches 'score', 'eat' matches 'eat bread')
                    if cmd == target or cmd.startswith(target):
                        obj.current += 1
                        obj.check_progress()

                        c = player.config.COLORS
                        _push(player)
                        await _progress(player, quest, obj)

                        if obj.completed:
                            await QuestManager._tutorial_next_step(player, quest)

            # Check if quest is complete
            if quest.is_complete():
                player.last_quest_progress_time = datetime.now()
                player.last_quest_hint_sent = False
                # Skip generic banner for tutorials (they auto-complete with their own banner)
                if not quest.quest_id.startswith('tutorial_'):
                    await QuestManager._notify_quest_complete(player, quest)

        # a tutorial step done in a fight (the training dummy) completes now, not at the
        # player's next command: the next step shows at once instead of "Return to Sage Aldric"
        for quest in [q for q in player.active_quests if q.quest_id.startswith('tutorial_') and q.is_complete()]:
            await QuestManager.auto_complete_tutorial_quest(player, quest)

    @staticmethod
    async def _notify_quest_complete(player: 'Player', quest: ActiveQuest):
        """Notify player that quest is complete."""
        c = player.config.COLORS
        await player.send(f"\r\n{c['bright_yellow']}╔══════════════════════════════════════════════════════════════╗{c['reset']}")
        await player.send(f"{c['bright_yellow']}║{c['bright_green']} QUEST COMPLETE: {quest.name:<45}{c['bright_yellow']}║{c['reset']}")
        await player.send(f"{c['bright_yellow']}╚══════════════════════════════════════════════════════════════╝{c['reset']}\r\n")
        await player.send(f"{c['white']}Return to the quest giver to claim your reward!{c['reset']}\r\n")

    @staticmethod
    async def complete_quest(player: 'Player', quest_id: str):
        """
        Complete a quest and grant rewards.

        Args:
            player: The player completing the quest
            quest_id: ID of the quest to complete
        """
        if not hasattr(player, 'active_quests'):
            await player.send("You have no active quests.")
            return

        # Find the quest
        quest = next((q for q in player.active_quests if q.quest_id == quest_id), None)
        if not quest:
            await player.send("You don't have that quest.")
            return

        if not quest.is_complete():
            await player.send("You haven't completed all objectives yet!")
            return

        # Grant rewards
        c = player.config.COLORS
        await player.send(f"\r\n{c['bright_green']}Quest Completed: {quest.name}{c['reset']}\r\n")

        # Trial of Unlearning: cleanse talents and free the path choice
        if (quest.rewards or {}).get('respec'):
            try:
                from talents import TalentManager
                refunded = TalentManager.reset_talents(player)
                player.path_switch_available = True
                await player.send(f"{c['bright_cyan']}The Trial cleanses you. "
                                  f"{refunded} talent point{'s' if refunded != 1 else ''} refunded - "
                                  f"and you may choose a new Path ('path' command).{c['reset']}")
            except Exception:
                pass

        if quest.rewards.get('exp'):
            await player.gain_exp(quest.rewards['exp'], source='quest')
            await player.send(f"{c['bright_yellow']}You gain {quest.rewards['exp']} experience!{c['reset']}")

        if quest.rewards.get('gold'):
            player.gold += quest.rewards['gold']
            await player.send(f"{c['yellow']}You receive {quest.rewards['gold']} gold!{c['reset']}")

        if quest.rewards.get('items'):
            await player.send(f"{c['bright_cyan']}You receive special items!{c['reset']}")
            # Create and give items to player
            for item_vnum in quest.rewards['items']:
                try:
                    from objects import create_object, create_preset_object
                    item = create_object(item_vnum, player.world) or create_preset_object(item_vnum)
                    if item:
                        if not hasattr(player, 'inventory'):
                            player.inventory = []
                        player.inventory.append(item)
                        await player.send(f"{c['cyan']}  → {item.short_desc}{c['reset']}")
                except Exception as e:
                    import logging
                    logging.getLogger('Misthollow.Quests').warning(f"Failed to give quest item {item_vnum}: {e}")

        # Quest completion bonus XP
        try:
            bonus = int(player.exp_to_level() * player.config.QUEST_XP_BONUS_PERCENT)
            if bonus > 0:
                await player.gain_exp(bonus, source='quest')
                await player.send(f"{c['bright_green']}Quest bonus: {bonus} XP!{c['reset']}")
        except Exception:
            pass

        # Reputation rewards
        if quest.rewards.get('reputation'):
            try:
                from factions import FactionManager
                await FactionManager.apply_reputation_changes(player, quest.rewards['reputation'], reason='Quest completion')
            except Exception:
                pass

        # Arena points reward
        if quest.rewards.get('arena_points'):
            player.arena_points = getattr(player, 'arena_points', 0) + quest.rewards['arena_points']
            await player.send(f"{c['bright_cyan']}You earn {quest.rewards['arena_points']} arena points!{c['reset']}")

        # Move quest to completed
        if not hasattr(player, 'quests_completed'):
            player.quests_completed = []
        player.quests_completed.append(quest_id)
        player.active_quests.remove(quest)
        _push(player)

        # Record daily quest completion
        quest_def = QUEST_DEFINITIONS.get(quest_id, {})
        if quest_def.get('daily'):
            QuestManager.record_daily_completion(player, quest_id)

        # Clear tracked quest if it was this one
        if getattr(player, 'tracked_quest', None) == quest_id:
            player.tracked_quest = None

        QuestManager.advance_chain_from_quest(player, quest_id)

        try:
            from achievements import AchievementManager
            await AchievementManager.check_quest_complete(player, quest_id)
        except Exception:
            pass
        
        # Journal entry for completed quest
        try:
            from journal import JournalManager
            quest_desc = quest.description or f"Completed the quest: {quest.name}"
            await JournalManager.record_quest(
                player, quest_id, quest.name, quest_desc
            )
        except Exception:
            pass

        await player.send(f"\r\n{c['green']}Quest reward claimed!{c['reset']}\r\n")
        logger.info(f"{player.name} completed quest {quest_id}")

    @staticmethod
    async def abandon_quest(player: 'Player', quest_id: str):
        """
        Abandon a quest.

        Args:
            player: The player abandoning the quest
            quest_id: ID of the quest to abandon
        """
        if not hasattr(player, 'active_quests'):
            await player.send("You have no active quests.")
            return

        quest = next((q for q in player.active_quests if q.quest_id == quest_id), None)
        if not quest:
            await player.send("You don't have that quest.")
            return

        player.active_quests.remove(quest)
        _push(player)

        c = player.config.COLORS
        await player.send(f"{c['red']}Quest abandoned: {quest.name}{c['reset']}")
        logger.info(f"{player.name} abandoned quest {quest_id}")

    @staticmethod
    def has_active_quest(player: 'Player', quest_id: str) -> bool:
        """Check if player has an active quest."""
        if not hasattr(player, 'active_quests'):
            return False
        return any(q.quest_id == quest_id for q in player.active_quests)

    @staticmethod
    def get_available_quests(player: 'Player', quest_giver_vnum: int) -> List[str]:
        """
        Get list of available quests from a quest giver.

        Args:
            player: The player checking for quests
            quest_giver_vnum: VNum of the quest giver NPC

        Returns:
            List of quest IDs
        """
        available = []
        for quest_id, quest_def in QUEST_DEFINITIONS.items():
            if quest_def.get('quest_giver') != quest_giver_vnum:
                continue

            # Check if already active
            if QuestManager.has_active_quest(player, quest_id):
                continue

            # Check if completed (and not repeatable)
            if not quest_def.get('repeatable', False) and quest_id in getattr(player, 'quests_completed', []):
                continue

            # Check chain availability
            if not QuestManager.is_chain_quest_available(player, quest_def):
                continue

            # Check level requirements
            if player.level < quest_def.get('level_min', 1):
                continue
            if player.level > quest_def.get('level_max', 50):
                continue

            # Check faction reputation requirements
            min_rep = quest_def.get('min_reputation')
            if min_rep:
                try:
                    from factions import FactionManager
                    ok = True
                    for faction_key, required in min_rep.items():
                        key = FactionManager.normalize_key(faction_key)
                        if not key:
                            continue
                        if FactionManager.get_reputation(player, key) < required:
                            ok = False
                            break
                    if not ok:
                        continue
                except Exception:
                    pass

            # Check daily quest cooldown
            if quest_def.get('daily') and not QuestManager.can_accept_daily(player, quest_id):
                continue

            available.append(quest_id)

        return available

    @staticmethod
    async def start_tutorial(player: 'Player'):
        """
        Start the tutorial quest chain for a new player.
        Called automatically when a new character enters the game.
        """
        # Check if player has already started or completed the tutorial
        if hasattr(player, 'quests_completed') and 'tutorial_1_awakening' in player.quests_completed:
            return  # Already completed first tutorial
        
        if QuestManager.has_active_quest(player, 'tutorial_1_awakening'):
            return  # Already has tutorial active
        
        # Check if any tutorial quest is active
        tutorial_quests = [q for q in getattr(player, 'active_quests', []) if q.quest_id.startswith('tutorial_')]
        if tutorial_quests:
            return  # Already on a tutorial quest
        
        # Start the first tutorial quest
        c = player.config.COLORS
        await player.send(f"\r\n{c['bright_cyan']}╔══════════════════════════════════════════════════════════════╗{c['reset']}")
        await player.send(f"{c['bright_cyan']}║{c['bright_yellow']}           WELCOME, NEW ADVENTURER!                           {c['bright_cyan']}║{c['reset']}")
        await player.send(f"{c['bright_cyan']}╠══════════════════════════════════════════════════════════════╣{c['reset']}")
        await player.send(f"{c['bright_cyan']}║{c['white']}  The Realms offer:                                          {c['bright_cyan']}║{c['reset']}")
        await player.send(f"{c['bright_cyan']}║{c['white']}    ⚔ Epic quests & story arcs    🛡 8 unique classes        {c['bright_cyan']}║{c['reset']}")
        await player.send(f"{c['bright_cyan']}║{c['white']}    🛠 Crafting & gathering       🐴 Mounts & companions     {c['bright_cyan']}║{c['reset']}")
        await player.send(f"{c['bright_cyan']}║{c['white']}    🏠 Player housing            🏟 PvP Arena               {c['bright_cyan']}║{c['reset']}")
        await player.send(f"{c['bright_cyan']}╚══════════════════════════════════════════════════════════════╝{c['reset']}")
        await player.send(f"\r\n{c['white']}Sage Aldric at the Temple can teach you the ways of the Realms.")
        await player.send(f"Type {c['bright_green']}hint{c['white']} anytime for guidance, or {c['bright_green']}help newbie{c['white']} for a full guide.{c['reset']}\r\n")
        
        # Auto-accept the first tutorial quest
        await QuestManager.accept_quest(player, 'tutorial_1_awakening')

    @staticmethod
    async def check_tutorial_progress(player: 'Player', command: str):
        """
        Track command usage for tutorial quest objectives.
        Called from command handler after each command.
        """
        if not hasattr(player, 'active_quests'):
            return
        
        # Check for command-type objectives
        await QuestManager.check_quest_progress(player, 'command', {'command': command.lower()})

    @staticmethod
    async def auto_complete_tutorial_quest(player: 'Player', quest: ActiveQuest):
        """
        Auto-complete a tutorial quest when all objectives are done.
        Tutorial quests don't require returning to the quest giver.
        """
        if not quest.quest_id.startswith('tutorial_'):
            return False
        
        if not quest.is_complete():
            return False
        
        # Auto-complete
        c = player.config.COLORS
        await player.send(f"\r\n{c['bright_green']}╔══════════════════════════════════════════════════════════════╗{c['reset']}")
        await player.send(f"{c['bright_green']}║ TUTORIAL COMPLETE: {quest.name:<41}║{c['reset']}")
        await player.send(f"{c['bright_green']}╚══════════════════════════════════════════════════════════════╝{c['reset']}\r\n")
        
        # Grant rewards
        if quest.rewards.get('exp'):
            await player.gain_exp(quest.rewards['exp'], source='tutorial')
            await player.send(f"{c['bright_yellow']}You gain {quest.rewards['exp']} experience!{c['reset']}")
        
        if quest.rewards.get('gold'):
            player.gold += quest.rewards['gold']
            await player.send(f"{c['yellow']}You receive {quest.rewards['gold']} gold!{c['reset']}")
        
        if quest.rewards.get('practices'):
            player.practices += quest.rewards['practices']
            await player.send(f"{c['bright_cyan']}You receive {quest.rewards['practices']} practice session"
                              f"{'s' if quest.rewards['practices'] != 1 else ''} — each pays your guild's trainer "
                              f"for a step of training past mastery.{c['reset']}")
        
        if quest.rewards.get('title'):
            player.title = quest.rewards['title']
            await player.send(f"{c['bright_magenta']}You have earned the title: {quest.rewards['title']}!{c['reset']}")
        
        if quest.rewards.get('items'):
            from objects import create_preset_object
            for item_vnum in quest.rewards['items']:
                try:
                    item = create_preset_object(item_vnum)
                    if item:
                        if not hasattr(player, 'inventory'):
                            player.inventory = []
                        player.inventory.append(item)
                        await player.send(f"{c['bright_cyan']}You receive {item.short_desc}!{c['reset']}")
                except Exception as e:
                    logger.warning(f"Failed to give tutorial reward item {item_vnum}: {e}")
        
        # Update quest progress timestamp
        player.last_quest_progress_time = datetime.now()
        player.last_quest_hint_sent = False
        
        # Move to completed
        if not hasattr(player, 'quests_completed'):
            player.quests_completed = []
        player.quests_completed.append(quest.quest_id)
        player.active_quests.remove(quest)
        _push(player)
        
        # Start next tutorial quest
        quest_def = QUEST_DEFINITIONS.get(quest.quest_id, {})
        next_quest = quest_def.get('next_quest')
        # Skip tutorial_4_skills since it's been merged into tutorial_3
        if next_quest == 'tutorial_4_skills':
            next_quest = 'tutorial_5_combat'
        if next_quest and next_quest in QUEST_DEFINITIONS:
            await player.send(f"\r\n{c['cyan']}New objective available...{c['reset']}\r\n")
            await QuestManager.accept_quest(player, next_quest)
        else:
            # Tutorial complete!
            await player.send(f"\r\n{c['bright_yellow']}╔══════════════════════════════════════════════════════════════╗{c['reset']}")
            await player.send(f"{c['bright_yellow']}║     CONGRATULATIONS! You have completed the tutorial!        ║{c['reset']}")
            await player.send(f"{c['bright_yellow']}║                                                              ║{c['reset']}")
            await player.send(f"{c['bright_yellow']}║  The Realms have so much more to offer:                     ║{c['reset']}")
            await player.send(f"{c['bright_yellow']}║    ⚔ Quests & story arcs — look for NPCs with [!]          ║{c['reset']}")
            await player.send(f"{c['bright_yellow']}║    🛠 Crafting & gathering — mine, forage, fish             ║{c['reset']}")
            await player.send(f"{c['bright_yellow']}║    🐴 Mounts, housing, achievements — as you grow!          ║{c['reset']}")
            await player.send(f"{c['bright_yellow']}║    🏟 PvP Arena — test yourself against other players       ║{c['reset']}")
            await player.send(f"{c['bright_yellow']}║                                                              ║{c['reset']}")
            await player.send(f"{c['bright_yellow']}║  Type 'help newbie' for a full guide, 'quests' for more!    ║{c['reset']}")
            await player.send(f"{c['bright_yellow']}╚══════════════════════════════════════════════════════════════╝{c['reset']}\r\n")
            
            # Post-tutorial guidance based on player level
            plevel = getattr(player, 'level', 1)
            if plevel < 5:
                await player.send(f"{c['bright_cyan']}Sage Aldric tells you, 'Venture to the Light Forest west of the city gates. Ranger Thornwood can guide your next steps. Check the quest board in Temple Square for more opportunities!'{c['reset']}\r\n")
            elif plevel < 10:
                await player.send(f"{c['bright_cyan']}Sage Aldric tells you, 'The Great Northern Forest to the north holds challenges worthy of your skill. Seek Borin the Wilderness Guide there. Or try the Orc Enclave if you crave real danger!'{c['reset']}\r\n")
            else:
                await player.send(f"{c['bright_cyan']}Sage Aldric tells you, 'You've outgrown my teachings, adventurer! Seek Grimjaw in the Mines of Moria, or travel east to the city of Thalos. Check the quest board in Temple Square for the full list of adventures!'{c['reset']}\r\n")
        
        return True

    # Static lookup for tutorial compass directions: {from_room: {target_room: direction_hint}}
    TUTORIAL_ROOM_HINTS = {
        # Directions to Temple Square (3005)
        '3001': {'3005': 'south', '3054': 'north', '3078': 'south', '3011': 'south', '3053': 'south', '3061': 'north', '18600': 'north'},
        '3005': {'3001': 'north', '3054': 'north', '3078': 'west', '3011': 'south', '3053': 'east', '3061': 'north', '18600': 'north'},
        '3054': {'3001': 'south', '3005': 'south', '3078': 'south', '3061': 'north', '18600': 'north'},
        '3059': {'3001': 'south', '3061': 'north', '18600': 'north'},
        '3060': {'3001': 'south', '3061': 'north', '18600': 'north'},
        '3061': {'3001': 'south', '18600': 'east'},
        '3004': {'3078': 'south', '3005': 'east', '3001': 'east'},
        '3014': {'3005': 'north', '3011': 'east', '3053': 'east', '3001': 'north'},
        '3015': {'3011': 'east', '3053': 'east', '3001': 'west'},
        '3016': {'3011': 'north', '3053': 'east', '3001': 'west'},
        '3041': {'3053': 'east', '3001': 'west'},
        '3078': {'3001': 'north', '3005': 'north'},
    }

    @staticmethod
    async def check_auto_hint(player: 'Player'):
        """Send a periodic hint if player hasn't made tutorial progress in 5+ minutes."""
        tutorial_quest = None
        for quest in getattr(player, 'active_quests', []):
            if quest.quest_id.startswith('tutorial_'):
                tutorial_quest = quest
                break
        
        if not tutorial_quest:
            return
        
        now = datetime.now()
        last_progress = getattr(player, 'last_quest_progress_time', None)
        if not last_progress:
            player.last_quest_progress_time = now
            return
        
        elapsed = (now - last_progress).total_seconds()
        if elapsed < 300:  # 5 minutes
            return
        
        # Only send once per 5-minute window
        if getattr(player, 'last_quest_hint_sent', False):
            return
        
        # Find first incomplete objective
        for obj in tutorial_quest.objectives:
            if not obj.completed:
                c = player.config.COLORS
                await player.send(
                    f"\r\n{c['bright_cyan']}[Hint] Your current objective: {obj.description}. "
                    f"Type 'hint' for directions.{c['reset']}"
                )
                player.last_quest_hint_sent = True
                # Reset timer so next hint comes in another 5 min
                player.last_quest_progress_time = now
                break

    @staticmethod
    async def show_compass_hint(player: 'Player'):
        """Show a subtle directional hint toward the tutorial objective room."""
        tutorial_quest = None
        for quest in getattr(player, 'active_quests', []):
            if quest.quest_id.startswith('tutorial_'):
                tutorial_quest = quest
                break
        
        if not tutorial_quest or not player.room:
            return
        
        current_room = str(player.room.vnum)
        
        # Find first incomplete visit objective
        for obj in tutorial_quest.objectives:
            if obj.completed or obj.type not in ('visit',):
                continue
            
            target_room = obj.target
            if current_room == target_room:
                continue  # Already here
            
            hints = QuestManager.TUTORIAL_ROOM_HINTS.get(current_room, {})
            direction = hints.get(target_room)
            if direction:
                c = player.config.COLORS
                await player.send(
                    f"{c['cyan']}You sense your objective lies to the {direction}.{c['reset']}"
                )
            break  # Only show one hint

    @staticmethod
    def get_quest_category(quest_id: str) -> str:
        """Return the display category for a quest."""
        quest_def = QUEST_DEFINITIONS.get(quest_id, {})
        # Explicit category
        cat = quest_def.get('category')
        if cat:
            return cat
        # Infer from chain or type
        chain_id = quest_def.get('chain_id')
        if chain_id == 'main_story':
            return 'main_story'
        if quest_def.get('daily'):
            return 'daily'
        if quest_def.get('type') == 'tutorial':
            return 'side'
        # Check if part of a chain
        if chain_id:
            chain_def = QUEST_CHAINS.get(chain_id, {})
            name = chain_def.get('name', '').lower()
            if 'faction' in name or 'guard' in name or 'thief' in name:
                return 'faction'
            if 'dungeon' in name or 'foundry' in name or 'clockwork' in name:
                return 'dungeon'
            return 'side'
        return 'side'

    @staticmethod
    def get_quest_giver_indicator(player, npc_vnum: int) -> str:
        """Return '!' if NPC has available quests, '?' if ready to turn in, '' otherwise."""
        # Check for quests ready to turn in
        for quest in getattr(player, 'active_quests', []):
            if quest.is_complete():
                quest_def = QUEST_DEFINITIONS.get(quest.quest_id, {})
                if quest_def.get('quest_giver') == npc_vnum:
                    return '?'
        # Check for available quests
        available = QuestManager.get_available_quests(player, npc_vnum)
        if available:
            return '!'
        return ''

    @staticmethod
    def can_accept_daily(player, quest_id: str) -> bool:
        """Check if player can accept a daily quest (not already done today)."""
        quest_def = QUEST_DEFINITIONS.get(quest_id, {})
        if not quest_def.get('daily'):
            return True
        daily_completions = getattr(player, 'daily_quest_completions', {})
        last_done = daily_completions.get(quest_id)
        if not last_done:
            return True
        from datetime import datetime
        try:
            last_dt = datetime.fromisoformat(last_done) if isinstance(last_done, str) else last_done
            now = datetime.now()
            return now.date() > last_dt.date()
        except Exception:
            return True

    @staticmethod
    def record_daily_completion(player, quest_id: str):
        """Record that a daily quest was completed today."""
        if not hasattr(player, 'daily_quest_completions'):
            player.daily_quest_completions = {}
        from datetime import datetime
        player.daily_quest_completions[quest_id] = datetime.now().isoformat()


# Quest category display info
QUEST_CATEGORY_INFO = {
    'main_story': {'name': 'Main Story', 'color': 'bright_yellow', 'icon': '★'},
    'side': {'name': 'Side Quests', 'color': 'bright_cyan', 'icon': '◆'},
    'daily': {'name': 'Daily', 'color': 'bright_green', 'icon': '↻'},
    'faction': {'name': 'Faction', 'color': 'bright_magenta', 'icon': '⚑'},
    'dungeon': {'name': 'Dungeon', 'color': 'bright_red', 'icon': '⚔'},
}
