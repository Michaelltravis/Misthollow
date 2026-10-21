"""
Discovery Journal System for Misthollow
Tracks player discoveries, lore, NPCs met, and exploration progress.
Compatible with the existing journal list format.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Any


class JournalManager:
    """
    Static manager for journal-related operations.
    Works with player.journal (list of dicts) format.
    """
    
    # Category display info
    CATEGORY_ICONS = {
        'lore': '📜',
        'secret': '🔮', 
        'npc': '👤',
        'area': '🗺️',
        'bestiary': '📖',
        'quest': '⚔️',
        'achievement': '🏆',
        'general': '📝'
    }
    
    CATEGORY_COLORS = {
        'lore': 'bright_yellow',
        'secret': 'bright_magenta',
        'npc': 'bright_cyan',
        'area': 'bright_green',
        'bestiary': 'bright_red',
        'quest': 'bright_white',
        'achievement': 'bright_yellow',
        'general': 'white'
    }
    
    CATEGORY_NAMES = {
        'lore': 'Lore & History',
        'secret': 'Secrets',
        'npc': 'Notable Figures',
        'area': 'Explored Regions',
        'bestiary': 'Bestiary',
        'quest': 'Completed Quests',
        'achievement': 'Achievements',
        'general': 'General'
    }
    
    DISCOVERY_MESSAGES = {
        'lore': 'New lore discovered!',
        'secret': 'Secret uncovered!',
        'npc': 'Notable figure encountered!',
        'area': 'New area discovered!',
        'bestiary': 'Creature catalogued!',
        'quest': 'Quest completed!',
        'achievement': 'Achievement unlocked!',
        'general': 'Journal updated!'
    }
    
    @staticmethod
    def _ensure_journal(player):
        """Ensure player has journal data structures."""
        if not hasattr(player, 'journal') or player.journal is None:
            player.journal = []
        if not hasattr(player, 'journal_keys'):
            # Build keys from existing entries
            player.journal_keys = set()
            for entry in player.journal:
                if isinstance(entry, dict) and 'key' in entry:
                    player.journal_keys.add(entry['key'])
        if not player.__dict__.get('_journal_people_named'):
            player.__dict__['_journal_people_named'] = True     # once a session
            JournalManager._retitle_people(player)

    @staticmethod
    def _retitle_people(player):
        """People met before the journal named them as the game shows them kept their keyword
        ("guildmaster", four of them alike, each with Thrain's lore): name them again from the
        creature their entry was made for."""
        protos = getattr(getattr(player, 'world', None), 'mob_prototypes', None) or {}
        thrain = NOTABLE_NPCS['guildmaster_thrain']
        for e in player.journal:
            if not isinstance(e, dict) or e.get('category') != 'npc':
                continue
            title, key = str(e.get('title') or ''), str(e.get('key') or '')
            vnum = key[4:].split('_', 1)[0] if key.startswith('npc:') else ''
            proto = protos.get(int(vnum)) if vnum.isdigit() else None
            shown = str((proto or {}).get('short_desc') or '').strip()
            if not shown or not title or title[:1] != title[:1].lower() or shown.lower() == title.lower():
                continue
            e['title'] = shown[:1].upper() + shown[1:]
            if e.get('content') == thrain['content'] and 'thrain' not in shown.lower():
                desc = (proto or {}).get('description') or (proto or {}).get('long_desc') or 'A resident of the realm.'
                e['content'] = e['text'] = desc
    
    @staticmethod
    def get_stats(player) -> dict:
        """Get journal statistics for a player."""
        JournalManager._ensure_journal(player)
        
        entries = player.journal
        
        # Count by category
        cats = {}
        for e in entries:
            if isinstance(e, dict):
                cat = e.get('category', 'general')
                cats[cat] = cats.get(cat, 0) + 1
        
        return {
            'total_entries': len(entries),
            'lore_discovered': cats.get('lore', 0),
            'secrets_found': cats.get('secret', 0),
            'npcs_met': cats.get('npc', 0),
            'areas_discovered': cats.get('area', 0),
            'bestiary_entries': cats.get('bestiary', 0),
            'quests_completed': cats.get('quest', 0),
            'achievements': cats.get('achievement', 0),
            'unread': sum(1 for e in entries if isinstance(e, dict) and not e.get('read', False))
        }
    
    @staticmethod
    def get_entries(player, category: str = None, limit: int = None) -> List[dict]:
        """Get journal entries, optionally filtered by category."""
        JournalManager._ensure_journal(player)
        
        entries = [e for e in player.journal if isinstance(e, dict)]
        
        if category:
            entries = [e for e in entries if e.get('category') == category]
        
        # Sort by time (newest first)
        entries = sorted(entries, key=lambda e: e.get('time', ''), reverse=True)
        
        if limit:
            entries = entries[:limit]
        
        # Return as simple Entry objects for compatibility
        return [SimpleEntry(e) for e in entries]
    
    @staticmethod
    def has_entry(player, key: str) -> bool:
        """Check if player has discovered a specific entry by key."""
        JournalManager._ensure_journal(player)
        return key in player.journal_keys
    
    @staticmethod
    def mark_read(player, entry=None):
        """Mark entries as read."""
        JournalManager._ensure_journal(player)
        
        if entry:
            # Find and mark specific entry
            for e in player.journal:
                if isinstance(e, dict) and e.get('key') == getattr(entry, 'key', None):
                    e['read'] = True
                    break
        else:
            # Mark all as read
            for e in player.journal:
                if isinstance(e, dict):
                    e['read'] = True
    
    @staticmethod
    async def add_entry(player, category: str, key: str, title: str, content: str,
                        location: str = None, metadata: dict = None,
                        silent: bool = False) -> bool:
        """
        Add a journal entry for the player.
        Returns True if new entry, False if already exists.
        """
        JournalManager._ensure_journal(player)
        
        # Check if already discovered
        if key in player.journal_keys:
            return False
        
        # Get location from player if not provided
        if not location and hasattr(player, 'room') and player.room:
            location = player.room.name
        
        entry = {
            'time': datetime.now().isoformat(),
            'category': category,
            'key': key,
            'title': title,
            'text': content,  # 'text' for backward compat with existing journal display
            'content': content,
            'location': location or 'Unknown',
            'metadata': metadata or {},
            'read': False
        }
        
        player.journal.append(entry)
        player.journal_keys.add(key)
        
        # Keep journal size manageable
        if len(player.journal) > 500:
            # Remove oldest non-keyed entries first
            player.journal = [e for e in player.journal if isinstance(e, dict) and e.get('key')][-500:]
        
        if not silent:
            await JournalManager.show_discovery(player, entry)
        
        return True
    
    @staticmethod
    async def show_discovery(player, entry: dict):
        """Show a beautiful discovery notification."""
        c = player.config.COLORS
        cat = entry.get('category', 'general')
        title = entry.get('title', 'Discovery')
        
        icon = JournalManager.CATEGORY_ICONS.get(cat, '📝')
        color = JournalManager.CATEGORY_COLORS.get(cat, 'white')
        msg = JournalManager.DISCOVERY_MESSAGES.get(cat, 'Discovery!')
        
        # ASCII fallbacks for terminals without Unicode
        ascii_icons = {
            '📜': '*LORE*',
            '🔮': '*SECRET*',
            '👤': '*NPC*',
            '🗺️': '*AREA*',
            '📖': '*BESTIARY*',
            '⚔️': '*QUEST*',
            '🏆': '*ACHIEVEMENT*',
            '📝': '*NOTE*'
        }
        
        display_icon = ascii_icons.get(icon, icon)

        # /play: one line, which its windows set apart as a journal note (hud/frames.js noteKind);
        # the journal is a window there (L)
        if getattr(getattr(player, 'connection', None), 'is_web', False):
            what = msg.rstrip('!. ').lower()
            await player.send(f"{c[color]}New in your journal: {c['bright_white']}{title}{c['reset']}{c[color]} ({what}){c['reset']}")
            return

        await player.send("")
        await player.send(f"{c[color]}  +{'=' * 54}+{c['reset']}")
        await player.send(f"{c[color]}  |  {display_icon} {msg:^44}  |{c['reset']}")
        await player.send(f"{c[color]}  +{'-' * 54}+{c['reset']}")
        await player.send(f"{c[color]}  |{c['reset']}  {c['bright_white']}{title[:50]:^50}{c['reset']}  {c[color]}|{c['reset']}")
        await player.send(f"{c[color]}  +{'=' * 54}+{c['reset']}")
        await player.send(f"{c['cyan']}  Type 'journal' to view your discoveries.{c['reset']}")
        await player.send("")
    
    # =========================================================================
    # Convenience methods for specific discovery types
    # =========================================================================
    
    @staticmethod
    async def discover_lore(player, key: str, title: str, content: str,
                            location: str = None, silent: bool = False) -> bool:
        """Record a lore discovery."""
        return await JournalManager.add_entry(
            player, 'lore', f'lore:{key}', title, content, location, silent=silent
        )
    
    @staticmethod
    async def discover_secret(player, key: str, title: str, content: str,
                              location: str = None, silent: bool = False) -> bool:
        """Record a secret discovery."""
        return await JournalManager.add_entry(
            player, 'secret', f'secret:{key}', title, content, location, silent=silent
        )
    
    @staticmethod
    async def discover_npc(player, npc_key: str, npc_name: str, content: str,
                           location: str = None, silent: bool = False) -> bool:
        """Record meeting a notable NPC."""
        return await JournalManager.add_entry(
            player, 'npc', f'npc:{npc_key}', npc_name, content, location, silent=silent
        )
    
    @staticmethod
    async def discover_area(player, zone_id: str, zone_name: str, content: str,
                            silent: bool = False) -> bool:
        """Record discovering a new zone/area."""
        return await JournalManager.add_entry(
            player, 'area', f'area:{zone_id}', zone_name, content, zone_name, silent=silent
        )
    
    @staticmethod
    async def discover_creature(player, mob_key: str, mob_name: str, content: str,
                                location: str = None, metadata: dict = None,
                                silent: bool = False) -> bool:
        """Record a creature for the bestiary (and its milestones: achievements.py)."""
        new = await JournalManager.add_entry(
            player, 'bestiary', f'mob:{mob_key}', mob_name, content, location,
            metadata=metadata, silent=silent
        )
        if new:
            try:
                from achievements import AchievementManager
                await AchievementManager.check_bestiary(player, JournalManager.get_stats(player)['bestiary_entries'])
            except Exception:
                pass
        return new
    
    @staticmethod
    async def record_quest(player, quest_id: str, quest_name: str, content: str,
                           silent: bool = False) -> bool:
        """Record quest completion."""
        return await JournalManager.add_entry(
            player, 'quest', f'quest:{quest_id}', quest_name, content, silent=silent
        )
    
    @staticmethod
    async def record_achievement(player, achievement_id: str, title: str, content: str,
                                 silent: bool = False) -> bool:
        """Record an achievement."""
        return await JournalManager.add_entry(
            player, 'achievement', f'ach:{achievement_id}', title, content, silent=silent
        )


class SimpleEntry:
    """Simple wrapper to give dict entries object-like access for cmd_journal compatibility."""
    def __init__(self, data: dict):
        self._data = data
        self.category = data.get('category', 'general')
        self.key = data.get('key', '')
        self.title = data.get('title', data.get('text', '')[:50])
        self.content = data.get('content', data.get('text', ''))
        self.text = data.get('text', data.get('content', ''))
        self.time = data.get('time', '')
        self.location = data.get('location', 'Unknown')
        self.read = data.get('read', False)
        self.metadata = data.get('metadata', {})
    
    def __getattr__(self, name):
        return self._data.get(name)


# =========================================================================
# Pre-defined lore entries that can be discovered in the world
# =========================================================================

WORLD_LORE = {
    'midgaard_founding': {
        'title': 'The Founding of Garathorm',
        'content': '''Long ago, when the world was young and the gods still walked among 
mortals, the great city of Garathorm was founded at the crossroads of the four 
winds. Its walls were blessed by divine hands, and for centuries it has stood 
as a beacon of civilization against the darkness that lurks beyond.'''
    },
    'high_tower_mystery': {
        'title': 'The High Tower of Magic',
        'content': '''The High Tower was built by Archmage Valdris the Eternal, who is 
said to still dwell within its highest chambers. Few who enter its maze-like 
halls ever return, and those who do speak of impossible geometries and rooms 
that exist outside of time itself.'''
    },
    'moria_fall': {
        'title': 'The Fall of Moria',
        'content': '''The dwarven kingdom of Moria once rivaled even Garathorm in its 
glory. But greed drove the miners too deep, and they awakened something ancient 
and terrible. Now only goblins and worse things dwell in those abandoned halls.'''
    },
    'sewer_rats': {
        'title': 'The Sewer Kingdoms',
        'content': '''Beneath the streets of Garathorm lies a vast network of ancient 
sewers. Some say they predate the city itself. The rats that dwell there have 
grown large and cunning, and rumors persist of a Rat King who rules the 
darkness below.'''
    },
    'thalos_curse': {
        'title': 'The Curse of Thalos',
        'content': '''The desert city of Thalos was once green and fertile, until its 
rulers offended the sun god with their hubris. In a single day, the land was 
transformed to sand, and the people were cursed to eternal thirst.'''
    },
    'drow_exile': {
        'title': 'The Drow Below',
        'content': '''Cast out from the elven kingdoms for their dark practices, the 
drow retreated beneath the earth. There they built new cities of black stone, 
lit by phosphorescent fungi. They remember the surface world, and they do not 
forget their grudges.'''
    },
    'haon_dor_spirits': {
        'title': 'Spirits of Haon-Dor',
        'content': '''The forest of Haon-Dor is one of the oldest in the world. Its 
trees remember when the first elves walked beneath their boughs. Those who 
travel quietly and respectfully may glimpse the ancient spirits that still 
protect these woods.'''
    },
    'chessboard_legend': {
        'title': 'The Wizard\'s Game',
        'content': '''A mad wizard once created a living chessboard as a test for 
would-be heroes. The pieces are enchanted constructs, bound to their squares 
for eternity. It is said that defeating the Black King grants a single wish.'''
    },
    'pyramid_builders': {
        'title': 'The Great Pyramid',
        'content': '''Who built the Great Pyramid? Some say it was the ancient pharaohs, 
others claim it predates humanity itself. Its chambers hold treasures beyond 
imagination, but also traps that have claimed countless lives. The mummies that 
guard its halls do not rest easy.'''
    },
    'orc_invasion': {
        'title': 'The Orc Wars',
        'content': '''Generations ago, the orc hordes swept down from the mountains in 
a tide of destruction. It took the combined might of all the free peoples to 
push them back. Now they lurk in their enclave, nursing their grudges and 
waiting for another chance.'''
    }
}

# Pre-defined notable NPCs
NOTABLE_NPCS = {
    'sage_aldric': {
        'title': 'Sage Aldric',
        'content': '''The ancient Sage Aldric serves as guide to new adventurers in 
Garathorm. His eyes hold the wisdom of centuries, and he is said to have once 
walked with the gods themselves. He asks for nothing but attention from those 
he teaches.'''
    },
    'guildmaster_thrain': {
        'title': 'Guildmaster Thrain',
        'content': '''Thrain is the gruff but fair master of the Adventurer\'s Guild. 
He has slain dragons, delved dungeons, and survived the Wars of Shadow. Now 
he passes on his knowledge to the next generation of heroes.'''
    },
    'puff_dragon': {
        'title': 'Puff the Dragon',
        'content': '''This peculiar little dragon can occasionally be found around 
Garathorm. Despite being a dragon, Puff seems friendly and curious about 
mortals. Some say he is actually a polymorphed wizard; others claim he is 
the last of an ancient breed.'''
    },
    'receptionist': {
        'title': 'The Guild Receptionist',
        'content': '''Always present at the Adventurer\'s Guild desk, she processes 
registrations and maintains the guild records. Rumor has it she knows every 
adventurer who has ever passed through Garathorm - the living and the dead.'''
    }
}

# Pre-defined secrets
WORLD_SECRETS = {
    'temple_hidden_room': {
        'title': 'The Hidden Shrine',
        'content': '''Behind a loose stone in the temple lies a forgotten shrine to an 
old god. Those who leave an offering here may receive an unexpected blessing.'''
    },
    'sewer_treasure': {
        'title': 'The Smuggler\'s Cache',
        'content': '''In the deepest part of the sewers, an old smuggler hid his 
life\'s fortune before the city guard caught up with him. The treasure 
remains unclaimed to this day.'''
    },
    'tower_passage': {
        'title': 'The Secret Passage',
        'content': '''Behind a seemingly ordinary wall in the High Tower, a hidden 
passage leads to chambers that do not appear on any map. What secrets do the 
mages hide there?'''
    }
}
