"""
Misthollow World
===============
World management - zones, rooms, mobs, objects.
"""

import random

import os
import json
import time
import logging
import asyncio
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from player import Player

from config import Config
import msgkind
import web_hud
from time_system import GameTime
from weather import Weather

logger = logging.getLogger('Misthollow.World')


def zone_of(room) -> Optional[int]:
    """The number of the zone a room belongs to: the zone file that holds it. Never worked out
    from the vnum alone, since a zone may span many hundred-blocks (the atlas's Trade Road runs
    from 1301 to 19748); only a room not loaded from a zone falls back to vnum // 100."""
    if room is None:
        return None
    zone = getattr(room, 'zone', None)
    if zone is not None:
        return zone.number
    vnum = getattr(room, 'vnum', None)
    return vnum // 100 if isinstance(vnum, int) else None


_RENUMBER = None


def renumbered(vnum):
    """The room that stands in for one of ours the atlas re-lay removed (world/atlas/renumber.json),
    so a saved place (where a player logged out, their recall point) still lands nearby; any
    other vnum comes back unchanged."""
    global _RENUMBER
    if _RENUMBER is None:
        try:
            with open(os.path.join(Config.WORLD_DIR, 'atlas', 'renumber.json')) as f:
                _RENUMBER = {int(k): v for k, v in json.load(f).get('rooms', {}).items()}
        except (OSError, ValueError):
            _RENUMBER = {}
    try:
        return _RENUMBER.get(int(vnum), vnum)
    except (TypeError, ValueError):
        return vnum


class Room:
    """A room in the MUD world."""
    
    def __init__(self, vnum: int):
        self.vnum = vnum
        self.zone = None
        self.name = "An Empty Room"
        self.description = "You see nothing special."
        self.sector_type = "inside"
        self.flags = set()
        self.exits = {}  # direction -> {to_room, description, door, key}
        self.extra_descs = {}  # keyword -> description
        self.hidden_items = []  # [{vnum, search_difficulty, requires_light, requires_detect_magic, reveal_message}, ...]
        self.puzzles = []  # Puzzle definitions for this room
        self.zone_mechanic = None  # a hazard its zone states on it (zone_hazards.py)
        self.map = None  # its place on the zone's map, {x, y, z} (the atlas's; north is +y)
        self.stated_look = None  # a look its zone states (room_looks.py)
        self.look, self.look_why = None, None

        # Contents
        self.characters = []  # Players and NPCs in room
        self.items = []  # Objects in room
        self.gold = 0  # Gold coins on the floor
        
        # Reset data
        self.mob_resets = []  # Mobs that spawn here
        self.obj_resets = []  # Objects that spawn here
        
        self.config = Config()
        
    def is_dark(self, game_time: Optional[GameTime]) -> bool:
        """Determine if the room is currently dark based on time/flags."""
        if 'dark' in self.flags:
            return True
        if 'lit' in self.flags:     # lit day and night (a quest's private trial)
            return False

        if not game_time:
            return False

        if not game_time.is_night():
            return False

        # Outdoors sectors are dark at night
        outdoor_sectors = {
            'field', 'forest', 'hills', 'mountain', 'water_swim', 'water_noswim',
            'flying', 'desert', 'swamp'
        }
        return self.sector_type in outdoor_sectors

    def admits(self, ch) -> bool:
        """Whether ch may be here: a room only immortals may enter (the God Rooms, `imm_only`) or
        a room of a land sealed until built takes immortals only; creatures never count as
        immortal. The flag is looked at first, since asking whether someone is immortal reads
        their account from disk."""
        if 'imm_only' not in self.flags and not getattr(self.zone, 'sealed', False):
            return True
        try:
            return bool(getattr(ch, 'is_immortal', False))
        except Exception:
            return False

    def get_visible_exits(self, player: Optional['Player'] = None) -> Dict[str, dict]:
        """Return exits visible to the player (hidden exits require discovery)."""
        visible = {}
        for direction, exit_data in self.exits.items():
            if not exit_data:
                continue
            if exit_data.get('hidden'):
                if player and hasattr(player, 'discovered_exits') and (self.vnum, direction) in player.discovered_exits:
                    visible[direction] = exit_data
            else:
                visible[direction] = exit_data
        return visible

    async def show_to(self, player: 'Player', force_exits: bool = False):
        """Display the room to a player."""
        c = self.config.COLORS

        # Can't see room details while sleeping
        if hasattr(player, 'position') and player.position == 'sleeping':
            await player.send("You can't see anything, you're sleeping!")
            return

        # Day/night visibility check
        game_time = None
        if hasattr(player, 'world') and player.world:
            game_time = player.world.game_time
        is_too_dark = self.is_dark(game_time) and hasattr(player, 'can_see_in_dark') and not player.can_see_in_dark()
        
        if is_too_dark:
            # In darkness: show only that it's dark and available exits (can feel walls)
            await player.send(f"{c['blue']}It is pitch black. You can't see a thing.{c['reset']}")
            # Still show exits - you can feel your way around
            visible_exits = self.get_visible_exits(player)
            exit_strings = []
            for direction, exit_data in visible_exits.items():
                if exit_data and 'door' in exit_data:
                    door = exit_data['door']
                    state = door.get('state', 'open')
                    if state == 'closed':
                        # Can feel a closed door but not see details
                        exit_strings.append(f"{c['yellow']}{direction}[blocked]{c['green']}")
                    else:
                        exit_strings.append(direction)
                else:
                    exit_strings.append(direction)
            if exit_strings:
                await player.send(f"{c['green']}[ Exits: {' '.join(exit_strings)} ]{c['reset']}")
            else:
                await player.send(f"{c['yellow']}[ Exits: None ]{c['reset']}")
            await player.send(f"{c['cyan']}Hint: Equip a light source or cast a light spell.{c['reset']}")
            return

        # Weather visibility effects (outdoors only)
        outdoor_sectors = {
            'field', 'forest', 'hills', 'mountain', 'water_swim', 'water_noswim',
            'flying', 'desert', 'swamp'
        }
        if self.zone and self.sector_type in outdoor_sectors:
            weather = self.zone.weather
            if weather:
                vision_mod = weather.get_vision_modifier()
                if vision_mod < 0.6:
                    await player.send(f"{c['blue']}Visibility is severely reduced by the weather.{c['reset']}")
                    await player.send(f"{c['cyan']}{self.name}{c['reset']}")
                    await player.send(f"{c['white']}You can barely make out your surroundings.{c['reset']}")
                    visible_exits = self.get_visible_exits(player)
                    exit_strings = []
                    for direction, exit_data in visible_exits.items():
                        if exit_data and 'door' in exit_data:
                            door = exit_data['door']
                            state = door.get('state', 'open')
                            door_name = door.get('name', 'door')
                            if state == 'closed':
                                if door.get('locked'):
                                    exit_strings.append(f"{c['red']}{direction}[{door_name}:locked]{c['green']}")
                                elif door.get('picked'):
                                    exit_strings.append(f"{c['yellow']}{direction}[{door_name}:picked]{c['green']}")
                                else:
                                    exit_strings.append(f"{c['yellow']}{direction}[{door_name}:closed]{c['green']}")
                            else:
                                exit_strings.append(direction)
                        else:
                            exit_strings.append(direction)
                    if exit_strings:
                        await player.send(f"{c['green']}[ Exits: {' '.join(exit_strings)} ]{c['reset']}")
                    else:
                        await player.send(f"{c['yellow']}[ Exits: None ]{c['reset']}")
                    return
                elif vision_mod < 1.0:
                    await player.send(f"{c['blue']}Visibility is reduced by the weather.{c['reset']}")

        # Room name
        vnum_str = f" {c['yellow']}[{self.vnum}]{c['reset']}" if getattr(player, 'show_room_vnums', False) else ""
        await player.send(f"{c['cyan']}{self.name}{vnum_str}{c['reset']}")
        
        # Dynamic atmospheric description based on time/weather
        try:
            from atmosphere import AtmosphereManager
            weather = self.zone.weather if self.zone else None
            atmosphere = AtmosphereManager.get_atmosphere(self, game_time, weather)
            if atmosphere:
                await player.send(f"{c['blue']}{atmosphere}{c['reset']}")
        except Exception:
            pass
        
        # Description
        desc = self.description or ""
        if getattr(player, 'brief_mode', False):
            # First sentence or 200 chars
            sentences = desc.split('.')
            if len(sentences) >= 2:
                brief_desc = sentences[0] + '.' + sentences[1] + '.'
            elif sentences and sentences[0]:
                brief_desc = sentences[0] + '.'
            else:
                brief_desc = desc
            if len(brief_desc) > 500:
                brief_desc = brief_desc[:500] + '...'
            await player.send(f"{c['white']}{brief_desc}{c['reset']}")
        else:
            await player.send(f"{c['white']}{desc}{c['reset']}")

        # Puzzle prompts
        try:
            from puzzles import PuzzleManager
            await PuzzleManager.announce_room_puzzles(player)
        except Exception:
            pass
        
        # Exits (only show if autoexit enabled or explicitly requested)
        if force_exits or getattr(player, 'autoexit', False):
            visible_exits = self.get_visible_exits(player)
            exit_strings = []
            for direction, exit_data in visible_exits.items():
                if exit_data and 'door' in exit_data:
                    door = exit_data['door']
                    state = door.get('state', 'open')
                    door_name = door.get('name', 'door')
                    if state == 'closed':
                        if door.get('locked'):
                            # Red for locked
                            exit_strings.append(f"{c['red']}{direction}[{door_name}:locked]{c['green']}")
                        elif door.get('picked'):
                            # Yellow for picked (closed but lock broken)
                            exit_strings.append(f"{c['yellow']}{direction}[{door_name}:picked]{c['green']}")
                        else:
                            # Yellow for closed but unlocked
                            exit_strings.append(f"{c['yellow']}{direction}[{door_name}:closed]{c['green']}")
                    else:
                        # Open door - show in normal color
                        exit_strings.append(direction)
                else:
                    exit_strings.append(direction)
            if exit_strings:
                await player.send(f"{c['green']}[ Exits: {' '.join(exit_strings)} ]{c['reset']}")
            else:
                await player.send(f"{c['yellow']}[ Exits: None ]{c['reset']}")
            
        # Gold in room
        if self.gold > 0:
            if self.gold == 1:
                await player.send(f"{c['yellow']}A single gold coin lies here.{c['reset']}")
            else:
                await player.send(f"{c['yellow']}A pile of {self.gold} gold coins lies here.{c['reset']}")

        # Items in room
        for item in self.items:
            try:
                from legendary import get_rarity_color, RARITY_TIERS
                rarity = getattr(item, 'rarity', 'common') or 'common'
                rcolor = c.get(RARITY_TIERS.get(rarity, {}).get('color_code', 'yellow'), c['yellow'])
                await player.send(f"{rcolor}{item.room_desc}{c['reset']}")
            except Exception:
                await player.send(f"{c['yellow']}{item.room_desc}{c['reset']}")

        # Display case for collections in player housing
        try:
            from housing import HouseManager
            if HouseManager.in_house(player):
                from collection_system import CollectionManager
                case_lines = CollectionManager.get_display_case_lines(player)
                for line in case_lines:
                    await player.send(line)
        except Exception:
            pass
            
        # Characters in room (excluding player)
        for char in self.characters:
            if char != player:
                fighting_msg = ""
                # CircleMUD-style: show who this character is fighting
                if hasattr(char, 'fighting') and char.fighting:
                    if char.fighting == player:
                        fighting_msg = f" {c['red']}[fighting YOU!]{c['reset']}"
                    else:
                        fighting_msg = f" {c['yellow']}[fighting {char.fighting.name}]{c['reset']}"
                # Also note if player is fighting this character
                elif hasattr(player, 'fighting') and player.fighting == char:
                    fighting_msg = f" {c['red']}[your target]{c['reset']}"

                # Check if player has labeled this character
                label_msg = ""
                if hasattr(player, 'target_labels') and player.target_labels:
                    for label_name, labeled_char in player.target_labels.items():
                        if labeled_char == char:
                            label_msg = f" {c['bright_yellow']}({label_name}){c['reset']}"
                            break

                # Color NPCs by type/disposition so they stand out from the room text
                if hasattr(char, 'owner') and char.owner:
                    # Pet/summon
                    if char.owner == player:
                        char_color = c['bright_magenta']  # Your pets
                        owner_tag = f" {c['green']}(yours){c['reset']}"
                    else:
                        char_color = c['magenta']  # Other player's pets
                        owner_tag = f" {c['yellow']}({char.owner.name}'s){c['reset']}"
                else:
                    owner_tag = ""
                    mob_flags = set(getattr(char, 'flags', set()) or [])
                    mob_name  = getattr(char, 'name', '')
                    mob_align = getattr(char, 'alignment', 0)

                    if 'boss' in mob_flags:
                        # Boss — bright magenta, unmistakable
                        char_color = c['bright_magenta']
                    elif 'aggressive' in mob_flags or 'aggro' in mob_flags:
                        # Attacks on sight — bright red, danger
                        char_color = c['bright_red']
                    elif 'shopkeeper' in mob_flags or 'friendly' in mob_flags or 'vendor' in mob_flags or mob_align >= 500:
                        # Safe/friendly NPC — bright green
                        char_color = c['bright_green']
                    elif mob_name and not mob_name.startswith(('a ', 'an ', 'the ', 'some ')):
                        # Named NPC (e.g. "Theron the Hunter", "Grimclaw") — bright yellow
                        char_color = c['bright_yellow']
                    else:
                        # Generic neutral mob — yellow (visible but not alarming)
                        char_color = c['yellow']

                # Randomly visible sneaking mobs
                sneak_indicator = ""
                try:
                    flags = getattr(char, 'flags', set())
                    if 'sneaking' in flags and char != player:
                        perc = player.get_perception() if hasattr(player, 'get_perception') else 10
                        # Harder to see sneaking characters
                        if random.randint(1, 100) > min(95, 30 + perc * 2):
                            continue
                        # If we can see them, show they're sneaking
                        sneak_indicator = f" {c['bright_black']}(sneaking){c['reset']}"
                except Exception:
                    pass
                
                # Quest giver indicator (! or ?)
                quest_indicator = ""
                if hasattr(char, 'vnum') and not hasattr(char, 'connection'):
                    try:
                        from quests import QuestManager
                        qi = QuestManager.get_quest_giver_indicator(player, char.vnum)
                        if qi == '!':
                            quest_indicator = f" {c['bright_yellow']}[!]{c['reset']}"
                        elif qi == '?':
                            quest_indicator = f" {c['bright_green']}[?]{c['reset']}"
                    except Exception:
                        pass

                # Build the character description line
                if hasattr(char, 'fighting') and char.fighting:
                    # CircleMUD style: replace desc with fighting message
                    if char.fighting == player:
                        desc = f"{char.name} is here, fighting YOU!"
                        await player.send(f"{c['red']}{desc}{owner_tag}{label_msg}{sneak_indicator}{c['reset']}")
                    else:
                        desc = f"{char.name} is here, fighting {char.fighting.name}."
                        await player.send(f"{char_color}{desc}{owner_tag}{label_msg}{sneak_indicator}{c['reset']}")
                elif hasattr(char, 'long_desc'):
                    # Show mob keyword hint so players know what to target
                    name_hint = ""
                    if hasattr(char, 'vnum') and not hasattr(char, 'connection'):
                        name_hint = f" {c['white']}({char.name}){c['reset']}"
                    await player.send(f"{char_color}{char.long_desc}{c['reset']}{name_hint}{quest_indicator}{owner_tag}{label_msg}{fighting_msg}{sneak_indicator}")
                elif hasattr(char, 'connection') and char.connection:
                    # Player character - show title and prestige class
                    title_str = getattr(char, 'title', '') or ''
                    prestige = getattr(char, 'prestige_class', None)
                    prestige_str = f" {c['bright_yellow']}[{prestige}]{c['reset']}" if prestige else ""
                    await player.send(f"{c['bright_green']}{char.name} {title_str}{prestige_str} is standing here.{label_msg}{fighting_msg}{sneak_indicator}{c['reset']}")
                else:
                    await player.send(f"{char_color}{char.name} is standing here.{quest_indicator}{owner_tag}{label_msg}{fighting_msg}{sneak_indicator}{c['reset']}")

                # Show active debuffs/buffs on the character (limited, flavorful)
                if hasattr(char, 'affects') and char.affects:
                    debuff_messages = []
                    for affect in char.affects:
                        if affect.type == 'dot' and affect.name == 'poison':
                            debuff_messages.append(f"{c['green']}{char.name} looks sick and pale.{c['reset']}")
                        elif affect.type == 'flag':
                            if affect.applies_to == 'blind':
                                debuff_messages.append(f"{c['yellow']}{char.name} seems blinded.{c['reset']}")
                            elif affect.applies_to == 'silenced':
                                debuff_messages.append(f"{c['magenta']}{char.name} is unnaturally quiet.{c['reset']}")
                            elif affect.applies_to == 'sanctuary':
                                debuff_messages.append(f"{c['white']}{char.name} glows with a holy aura.{c['reset']}")
                            elif affect.applies_to == 'fly':
                                debuff_messages.append(f"{c['cyan']}{char.name} is levitating above the ground.{c['reset']}")
                            elif affect.applies_to == 'stoneskin':
                                debuff_messages.append(f"{c['white']}{char.name}'s skin looks like stone.{c['reset']}")
                            elif affect.applies_to == 'invisible':
                                # Don't show if the viewer can't detect invisible
                                if hasattr(player, 'affect_flags') and 'detect_invisible' in player.affect_flags:
                                    debuff_messages.append(f"{c['cyan']}{char.name} shimmers faintly in the air.{c['reset']}")
                        elif affect.type == 'modify_stat':
                            if affect.name == 'weakened':
                                debuff_messages.append(f"{c['red']}{char.name} looks weakened!{c['reset']}")
                            elif affect.name == 'slowed':
                                debuff_messages.append(f"{c['blue']}{char.name} is moving sluggishly!{c['reset']}")

                    for msg in debuff_messages:
                        await player.send(msg)

                # Detect Evil (spells.py): evil shows to the one who looks for it
                if ('detect_evil' in (getattr(player, 'affect_flags', None) or set())
                        and (getattr(char, 'alignment', 0) or 0) <= -350):
                    await player.send(f"{c['red']}{char.name} is wreathed in a dull red aura.{c['reset']}")
                    
    async def send_to_room(self, message: str, exclude: List = None, wake_sleepers: bool = False):
        """Send a message to everyone in the room (sleeping players don't see messages unless wake_sleepers=True)."""
        exclude = exclude or []
        for char in self.characters:
            if char not in exclude and hasattr(char, 'send'):
                # Skip sleeping players unless it's important enough to wake them
                if not wake_sleepers and getattr(char, 'position', 'standing') == 'sleeping':
                    continue
                await char.send(message)
                
    def get_exit(self, direction: str) -> Optional['Room']:
        """Get the room in a given direction."""
        exit_data = self.exits.get(direction)
        if not exit_data:
            return None
        return exit_data.get('room')
        
    def to_dict(self) -> dict:
        """Convert room to dictionary for saving."""
        exits = {}
        for d, e in self.exits.items():
            if not e:
                continue
            ex = dict(e)
            # Remove runtime-only references
            if 'room' in ex:
                ex.pop('room')
            # the bar across a sealed zone's way in is made at load, never saved
            if 'door' in ex:
                import doors
                door = doors.unsealed_door(e)
                if door:
                    # (its material and magic come from doors.json at load; a seal is for now)
                    ex['door'] = {k: v for k, v in door.items() if k not in doors.NOT_SAVED}
                else:
                    ex.pop('door')
            ex.pop('_unsealed_door', None)
            exits[d] = ex
        out = {
            'vnum': self.vnum,
            'name': self.name,
            'description': self.description,
            'sector_type': self.sector_type,
            'flags': list(self.flags),
            'exits': exits,
            'extra_descs': self.extra_descs,
            'hidden_items': self.hidden_items,
            'puzzles': self.puzzles,
            'mob_resets': self.mob_resets,
            'obj_resets': self.obj_resets,
        }
        if self.map:
            out['map'] = dict(self.map)
        if getattr(self, 'stated_look', None):
            out['look'] = self.stated_look
        return out
        
    # some zones (90, 100, 110, 130, 160) were written with `title` and `terrain`
    TERRAIN_SECTORS = {'indoors': 'inside', 'underground': 'cave', 'undead': 'dungeon', 'planar': 'mountain',
                       'water_surface': 'water_swim'}

    @classmethod
    def from_dict(cls, data: dict) -> 'Room':
        """Create a room from dictionary data."""
        room = cls(data['vnum'])
        room.name = data.get('name') or data.get('title') or 'An Empty Room'
        room.description = data.get('description', '')
        terrain = data.get('terrain')
        room.sector_type = data.get('sector_type') or (cls.TERRAIN_SECTORS.get(terrain, terrain) if terrain else 'inside')
        room.flags = set(data.get('flags', []))
        # how the 3D client draws it, when the zone says so outright (room_looks.py)
        room.stated_look = data.get('look')
        
        # Process exits and convert flag-based door format to door objects
        room.exits = {}
        for direction, exit_data in data.get('exits', {}).items():
            if exit_data:
                # Copy the exit data
                processed_exit = dict(exit_data)

                # Normalize legacy exit key
                if 'room_vnum' in processed_exit and 'to_room' not in processed_exit:
                    processed_exit['to_room'] = processed_exit['room_vnum']

                # Check for door flags and convert to door object
                exit_flags = list(exit_data.get('flags', []))  # Make a copy
                if 'door' in exit_flags or exit_data.get('door'):
                    # Has a door - create door object if not exists
                    if 'door' not in processed_exit or not isinstance(processed_exit.get('door'), dict):
                        door_name = exit_data.get('keyword', 'door').split()[0] if exit_data.get('keyword') else 'door'
                        processed_exit['door'] = {
                            'name': door_name,
                            'state': 'closed' if 'closed' in exit_flags else 'open',
                            'locked': 'locked' in exit_flags,
                            'pickproof': 'pickproof' in exit_flags,
                            'key': exit_data.get('key'),
                        }
                    else:
                        # Door object exists, ensure it has proper state from flags
                        door = processed_exit['door']
                        if 'closed' in exit_flags and door.get('state') != 'open':
                            door['state'] = 'closed'
                        if 'locked' in exit_flags:
                            door['locked'] = True
                    
                    # Remove door-related flags since they're now in the door object
                    # This prevents the flags from overriding the door object state
                    for flag in ['door', 'closed', 'locked', 'pickproof']:
                        if flag in exit_flags:
                            exit_flags.remove(flag)
                    processed_exit['flags'] = exit_flags
                
                room.exits[direction] = processed_exit
        
        room.extra_descs = data.get('extra_descs', {})
        room.hidden_items = data.get('hidden_items', [])
        room.puzzles = data.get('puzzles', [])
        room.zone_mechanic = data.get('zone_mechanic')   # the deep, the dark (zone_hazards.py)
        room.mob_resets = data.get('mob_resets', [])
        room.obj_resets = data.get('obj_resets', [])
        room.map = data.get('map') or None
        return room


class Zone:
    """A zone containing rooms, mobs, and objects."""
    
    def __init__(self, number: int):
        self.number = number
        self.name = "Unknown Zone"
        self.builders = ""
        self.lifespan = 2  # Reset ticks (each tick = 15 real minutes; 2 = 30 min)
        self.reset_mode = 2  # 0=never, 1=empty, 2=always
        self.top = 0  # Highest vnum in zone
        self.age = 0  # Ticks since last reset
        self.reset_interval_seconds = self.lifespan * 900
        self.last_reset_at = None
        self.next_reset_at = None

        self.rooms: Dict[int, Room] = {}
        self.mobs: Dict[int, dict] = {}  # mob prototypes
        self.objects: Dict[int, dict] = {}  # object prototypes
        self.sealed = False  # a land still being built: its ways in are barred (doors.seal_zones)

        # Initialize weather for this zone
        self.weather = Weather(number)
        
    def to_dict(self) -> dict:
        """Convert zone to dictionary for saving."""
        out = {
            'number': self.number,
            'name': self.name,
            'builders': self.builders,
            'reset_time': self.lifespan * 900,  # Save as seconds for from_dict
            'reset_mode': self.reset_mode,
            'top': self.top,
            'rooms': {vnum: room.to_dict() for vnum, room in self.rooms.items()},
            'mobs': self.mobs,
            'objects': self.objects,
        }
        if self.sealed:
            out['sealed'] = True
        return out
        
    @classmethod
    def from_dict(cls, data: dict) -> 'Zone':
        """Create a zone from dictionary data."""
        zone = cls(data['number'])
        zone.name = data.get('name', 'Unknown Zone')
        zone.builders = data.get('builders', '')

        # Handle both old format (lifespan in minutes) and new format (reset_time in seconds)
        # zone_reset_tick is called every 900 seconds (15 minutes), so zone.age increments every 15 minutes
        if 'reset_time' in data:
            # New format: reset_time in seconds, convert to 15-minute units
            reset_time_seconds = data['reset_time']
            zone.lifespan = max(1, round(reset_time_seconds / 900))
        else:
            # Old format: lifespan already in the correct unit (but was probably intended as minutes)
            # Since zone.age increments every 15 minutes, we need to adjust
            lifespan_value = data.get('lifespan', 30)
            # Treat old lifespan values as minutes, convert to 15-minute units
            zone.lifespan = max(1, round(lifespan_value / 15))
        zone.reset_interval_seconds = zone.lifespan * 900

        zone.reset_mode = data.get('reset_mode', 2)
        zone.top = data.get('top', 0)
        zone.sealed = bool(data.get('sealed'))
        
        # Load rooms
        for vnum_str, room_data in data.get('rooms', {}).items():
            room = Room.from_dict(room_data)
            room.zone = zone
            zone.rooms[int(vnum_str)] = room
            
        zone.mobs = data.get('mobs', {})
        zone.objects = data.get('objects', {})
        
        return zone


class World:
    """The game world."""
    
    def __init__(self, config: Config):
        self.config = config
        self.zones: Dict[int, Zone] = {}
        self.rooms: Dict[int, Room] = {}
        self.mob_prototypes: Dict[int, dict] = {}
        self.obj_prototypes: Dict[int, dict] = {}

        self.players: Dict[str, 'Player'] = {}  # Online players
        self.npcs: List = []  # All loaded NPCs

        # Initialize game time system
        self.game_time = GameTime()

        # World events manager (initialized after load)
        self.event_manager = None
        
    async def load(self):
        """Load the world from files."""
        logger.info("Loading world...")
        
        # Load zones
        zones_dir = os.path.join(self.config.WORLD_DIR, 'zones')
        
        if os.path.exists(zones_dir):
            for filename in os.listdir(zones_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(zones_dir, filename)
                    await self.load_zone_file(filepath)
        else:
            logger.warning(f"Zones directory not found: {zones_dir}")
            
        # If no zones loaded, create default world. Only treat this as a
        # fresh install when there were no zone files at all — if files
        # exist but every one failed to load, that's data corruption and
        # rebuilding (let alone saving) the tiny default world on top of
        # it would make things worse.
        if not self.zones:
            zone_files = (
                [f for f in os.listdir(zones_dir) if f.endswith('.json')]
                if os.path.exists(zones_dir) else []
            )
            if zone_files:
                logger.error(
                    f"{len(zone_files)} zone files exist in {zones_dir} but "
                    f"none loaded — refusing to build the default world over "
                    f"them. Fix the zone files (or restore them with "
                    f"'git checkout -- world/zones/') and restart."
                )
                raise RuntimeError("Zone files present but none could be loaded")
            logger.info("No zones found, creating default world...")
            await self.create_default_world()
            
        # Link room exits
        self.link_exits()
        # who lives where, zone by zone (world/population: bosses in their rooms, doors to keys)
        try:
            import population
            population.apply(self)
        except Exception as e:
            logger.error(f"population failed: {e}")
        # secret ways hidden until found (zone_hazards.py: Shadowspire's mirror door and library)
        try:
            import zone_hazards
            zone_hazards.seed(self)
        except Exception:
            logger.exception('zone hazards seed')
        # rites of passage (world/rites.json): keyed gates and their keepers, toll-keepers
        try:
            import rites
            rites.apply(self)
        except Exception as e:
            logger.error(f"rites failed: {e}")
        # Tidy the imported door data (both sides agree) and remember the reset state
        try:
            import doors
            doors.normalize(self)
            doors.seal_zones(self)          # lands still being built: their ways in barred
        except Exception as e:
            logger.error(f"door normalize failed: {e}")
        # rooms that store their place on the map (the atlas's): say what disagrees with it
        try:
            from map_system import check_stored_cells
            problems = check_stored_cells(self)
            for p in problems[:20]:
                logger.warning(f"map: {p}")
            if len(problems) > 20:
                logger.warning(f"map: ...and {len(problems) - 20} more")
        except Exception as e:
            logger.error(f"map check failed: {e}")

        # Canary check: if zone 30 loaded but looks like the tiny default-world
        # stub (the old bootstrap bug overwrote real zone files with it), the
        # big Garathorm - Market Square, the gates, the sewers - is missing.
        # Try to self-heal from git, then reload once.
        if not getattr(self, '_world_heal_attempted', False) and self._world_looks_corrupted():
            self._world_heal_attempted = True
            logger.error(
                "WORLD DATA CORRUPTED: zone 30 is the 13-room stub town, not "
                "Northern Garathorm (Market Square/sewers missing). Attempting "
                "automatic restore from git..."
            )
            if self._restore_world_from_git():
                logger.error("Restore succeeded - reloading world.")
                self.zones.clear()
                self.rooms.clear()
                self.mob_prototypes.clear()
                self.obj_prototypes.clear()
                await self.load()
                return
            raise RuntimeError(
                "World data is the corrupted stub and automatic restore failed. "
                "Run: git checkout -- world/zones/   then restart the server."
            )

        # Seed puzzles
        try:
            from puzzles import PuzzleManager
            PuzzleManager.seed_world(self)
        except Exception:
            pass
        
        # Reset zones (spawn mobs and objects)
        await self.reset_all_zones()

        # Spawn faction NPCs
        try:
            from factions import spawn_faction_npcs
            spawn_faction_npcs(self)
        except Exception as e:
            logger.warning(f"Failed to spawn faction NPCs: {e}")
        
        # Initialize world events system
        from world_events import WorldEventManager
        self.event_manager = WorldEventManager(self)

        # Register legendary item prototypes
        try:
            from legendary import LEGENDARY_ITEMS
            for vnum, proto in LEGENDARY_ITEMS.items():
                if vnum not in self.obj_prototypes:
                    self.obj_prototypes[vnum] = proto
        except Exception as e:
            logger.warning(f"Failed to register legendary items: {e}")

        # every item's level, from the creatures that wear and drop it (gear_look.py: how the
        # 3D client draws gear, and the level the tooltips show)
        try:
            import gear_look
            gear_look.build_item_levels(self)
        except Exception as e:
            logger.warning(f"Failed to work out item levels: {e}")
        # what each room looks like in 3D (room_looks.py: a cave looks like a cave)
        try:
            import room_looks
            room_looks.classify(self)
            room_looks.strip_filler(self)     # no "stale air" under open sky or the sea
            room_looks.scrub_filler(self)     # nor "bird calls in the canopy" down a sewer pipe
            import room_features
            room_features.annotate(self)      # what its words say stands in it (standing stones, altars...)
            import zone_tone
            zone_tone.annotate(self)          # a zone's stone and light, from its rooms' words
            import setpieces
            setpieces.annotate(self)          # landmark and boss rooms laid out by hand
        except Exception as e:
            logger.warning(f"Failed to work out room looks: {e}")
        # open ground (wilds.py): side-by-side outdoor rooms of the opened zones join up (after the
        # looks: whether a room is open country is its look; before the tutorials' routes)
        try:
            import wilds
            wilds.apply(self)
        except Exception as e:
            logger.error(f"open ground failed: {e}")

        # how many of each set's pieces one hero can wear (sets.py: every tier can be reached)
        try:
            import sets
            sets.build_set_caps(self)
        except Exception as e:
            logger.warning(f"Failed to work out set sizes: {e}")

        # the tutorials' directions, from the map as it is ("south twice, then west three times")
        try:
            import quests
            for missing in quests.apply_routes(self):
                logger.warning(f"quest route not found: {missing}")
        except Exception as e:
            logger.warning(f"Failed to work out quest routes: {e}")

        # the day's bounties on the bounty board (bounties.py)
        try:
            import bounties
            bounties.refresh(self)
        except Exception as e:
            logger.warning(f"Failed to post the bounties: {e}")

        logger.info(f"World loaded: {len(self.zones)} zones, {len(self.rooms)} rooms")
        
    def zone_of_vnum(self, vnum: int) -> int:
        """The zone a room vnum belongs to: the zone holding that room, or for a vnum not built
        yet, the zone whose rooms already span it (else vnum // 100)."""
        room = self.rooms.get(vnum)
        if room is not None and room.zone is not None:
            return room.zone.number
        for number, zone in self.zones.items():
            if zone.rooms and min(zone.rooms) <= vnum <= max(zone.rooms) and number == vnum // 100:
                return number
        return vnum // 100

    def _world_looks_corrupted(self):
        """True when zone 30 is present but is the default-world stub: the
        real Northern Garathorm has 70+ rooms including 3054 (Temple Altar)
        and sewer links; the stub has 13 rooms and neither."""
        z30 = self.zones.get(30)
        if not z30:
            return False
        return len(z30.rooms) < 30 and 3054 not in self.rooms

    def _restore_world_from_git(self):
        """Best-effort `git checkout -- world/zones/` to recover clobbered
        zone files. Returns True when the canary room is back on disk."""
        import subprocess
        repo = os.path.dirname(self.config.WORLD_DIR)
        try:
            subprocess.run(
                ['git', 'checkout', '--', 'world/zones/'],
                cwd=repo, capture_output=True, timeout=30, check=True,
            )
        except Exception as e:
            logger.error(f"git restore failed: {e}")
            return False
        try:
            with open(os.path.join(self.config.WORLD_DIR, 'zones', 'zone_030.json')) as f:
                return '"3054"' in f.read()
        except Exception:
            return False

    async def load_zone_file(self, filepath: str):
        """Load a zone from a JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            zone = Zone.from_dict(data)
            self.zones[zone.number] = zone
            
            # Add rooms to global lookup
            for vnum, room in zone.rooms.items():
                self.rooms[vnum] = room
                
            # Add mob/object prototypes
            for vnum_str, mob_data in zone.mobs.items():
                self.mob_prototypes[int(vnum_str)] = mob_data
            for vnum_str, obj_data in zone.objects.items():
                self.obj_prototypes[int(vnum_str)] = obj_data
                
            logger.info(f"Loaded zone {zone.number}: {zone.name} ({len(zone.rooms)} rooms)")
            
        except Exception as e:
            logger.error(f"Error loading zone file {filepath}: {e}")
            
    def link_exits(self):
        """Link room exits to actual room objects and ensure doors exist on both sides."""
        from config import Config
        config = Config()
        
        for room in self.rooms.values():
            for direction, exit_data in room.exits.items():
                if exit_data and 'to_room' in exit_data:
                    target_vnum = exit_data['to_room']
                    if target_vnum in self.rooms:
                        target_room = self.rooms[target_vnum]
                        exit_data['room'] = target_room
                        
                        # If this exit has a door, ensure the other side has it too
                        if 'door' in exit_data and exit_data['door']:
                            opposite = config.DIRECTIONS.get(direction, {}).get('opposite')
                            if opposite and opposite in target_room.exits:
                                other_exit = target_room.exits[opposite]
                                if other_exit and 'door' not in other_exit:
                                    # Copy the door to the other side
                                    other_exit['door'] = dict(exit_data['door'])
                        
    async def create_default_world(self):
        """Create a default fantasy world."""
        from world_builder import WorldBuilder
        builder = WorldBuilder(self)
        await builder.build_default_world()
        
    async def reset_all_zones(self):
        """Reset all zones (spawn mobs/objects), the world's creatures counted once for them all."""
        counts = self._creature_counts()
        for zone in self.zones.values():
            await self.reset_zone(zone, counts)
            
    def _creature_counts(self):
        """Every zone's creatures by vnum (a creature counts for its home zone and the zone it
        stands in), and the patrols walking each route: for resetting many zones at once."""
        from collections import Counter, defaultdict
        by_zone = defaultdict(Counter)
        patrols = Counter()
        for npc in self.npcs:
            v = getattr(npc, 'vnum', None)
            if v is None:
                continue
            here = getattr(getattr(getattr(npc, 'room', None), 'zone', None), 'number', None)
            home = getattr(npc, 'home_zone', None)
            for z in {home, here} - {None}:
                by_zone[z][v] += 1
            if getattr(npc, 'patrol_route', None):
                patrols[(v, repr(list(npc.patrol_route)))] += 1
        return by_zone, patrols

    async def reset_zone(self, zone: Zone, counts=None):
        """Reset a single zone (`counts`: _creature_counts() when resetting many at once)."""
        from bosses import create_mob_from_prototype
        from objects import create_object
        from collections import Counter

        # the zone's creatures by vnum, counted once (not the whole world rescanned for every
        # reset line: ~27,000 lines x ~4,500 creatures froze the server for seconds at each reset)
        if counts is not None:
            in_zone, patrols = counts[0][zone.number], counts[1]
        else:
            in_zone = Counter(npc.vnum for npc in self.npcs
                              if getattr(npc, 'vnum', None) is not None
                              and (getattr(npc, 'home_zone', None) == zone.number
                                   or (npc.room and npc.room.zone == zone)))
            patrols = None

        for room in zone.rooms.values():
            # Spawn mobs
            for mob_reset in room.mob_resets:
                mob_vnum = mob_reset.get('vnum')
                max_count = mob_reset.get('max', 1)
                max_existing = mob_reset.get('max_existing')
                
                # existing mobs of this vnum in the zone (prevents dupes when they wander)
                current = in_zone[mob_vnum]
                if max_existing is not None and in_zone[mob_vnum] >= max_existing:
                    continue

                route = mob_reset.get('route')
                if route:       # a patrol (population.py): one walks each route
                    max_count = 1
                    if patrols is None:
                        patrols = Counter((getattr(n, 'vnum', None), repr(list(n.patrol_route))) for n in self.npcs
                                          if getattr(n, 'patrol_route', None))
                    current = patrols[(mob_vnum, repr(list(route)))]

                if current < max_count:
                    proto = self.mob_prototypes.get(mob_vnum)
                    if proto:
                        mob = create_mob_from_prototype(proto, self)
                        if route:
                            mob.patrol_route = list(route)
                        mob.room = room
                        mob.home_room = room  # Set home room for AI
                        mob.home_zone = zone.number  # Set home zone for movement restrictions
                        room.characters.append(mob)
                        self.npcs.append(mob)
                        in_zone[mob_vnum] += 1
                        if route:
                            patrols[(mob_vnum, repr(list(route)))] += 1
                        self._ensure_shop(mob)  # stock shopkeepers with role-appropriate goods
                        
            # Spawn objects
            for obj_reset in room.obj_resets:
                obj_vnum = obj_reset.get('vnum')
                max_count = obj_reset.get('max', 1)
                
                # Count existing objects of this type
                current = sum(1 for item in room.items 
                            if hasattr(item, 'vnum') and item.vnum == obj_vnum)
                
                if current < max_count:
                    obj = create_object(obj_vnum, self)
                    if obj:
                        room.items.append(obj)

        # doors go back to how the zone starts (not where a player stands)
        try:
            import doors
            doors.reset_zone(self, zone)
        except Exception as e:
            logger.debug(f"door reset failed in zone {getattr(zone, 'number', '?')}: {e}")

        zone.age = 0
        zone.last_reset_at = time.time()
        zone.next_reset_at = zone.last_reset_at + zone.reset_interval_seconds
        
    # role keyword -> item_types the shop sells
    _SHOP_ROLES = [
        (('baker', 'bread'), ['food']),
        (('butcher', 'meat'), ['food']),
        (('grocer', 'green', 'produce'), ['food', 'drink', 'drinkcon']),
        (('weaponsmith', 'weapon', 'fletcher', 'bowyer', 'blade'), ['weapon']),
        (('blacksmith', 'smith'), ['weapon', 'armor']),
        (('armourer', 'armorer', 'armor', 'leather'), ['armor']),
        (('tailor', 'clothier', 'robe'), ['armor']),
        (('wizard', 'mage', 'magic', 'sorcer', 'witch', 'conjurer', 'enchant'), ['scroll', 'potion', 'wand', 'staff']),
        (('alchemist', 'apothecary', 'potion', 'herbalist'), ['potion', 'drink']),
        (('jewel', 'gem', 'jeweler'), ['treasure']),
        (('tavern', 'bartender', 'innkeeper', 'barkeep', 'bar', 'pub'), ['drink', 'drinkcon', 'food']),
        (('captain', 'guard', 'quartermaster'), ['weapon', 'armor']),
        (('general', 'merchant', 'trader', 'pawn', 'peddler', 'vendor', 'shopkeep', 'keeper', 'clerk', 'salesman'),
         ['food', 'drink', 'drinkcon', 'light', 'container', 'other', 'treasure']),
    ]

    def _shop_role(self, name: str):
        n = (name or '').lower()
        for keys, sells in self._SHOP_ROLES:
            if any(k in n for k in keys):
                buys = list(dict.fromkeys(sells + ['treasure', 'other']))
                return sells, buys
        # sensible default: a general store
        return (['food', 'drink', 'light', 'container', 'other', 'treasure'], ['treasure', 'other', 'weapon', 'armor'])

    def _ensure_shop(self, mob):
        """Make sure every shopkeeper carries a proper, role-appropriate stock.
        Many zone shop_configs are thin (a weaponsmith selling one dagger) or
        have malformed buy lists; this enriches an existing shop up to a full
        selection drawn from the world's objects, and creates one outright for
        any shopkeeper that has none."""
        if getattr(mob, 'special', '') != 'shopkeeper':
            return
        try:
            from shops import ShopManager
            from objects import create_object
            TARGET = 12
            # lazily index object prototypes by item_type
            if not hasattr(self, '_obj_by_type'):
                self._obj_by_type = {}
                for ov, op in self.obj_prototypes.items():
                    t = str(op.get('item_type') or op.get('type') or 'other').lower()
                    self._obj_by_type.setdefault(t, []).append(ov)
            sells_types, buys_types = self._shop_role(getattr(mob, 'name', ''))
            zlow = (mob.vnum // 100) * 100
            zhigh = zlow + 99
            candidates = []
            for t in sells_types:
                pool = self._obj_by_type.get(t, [])
                local = [v for v in pool if zlow <= v <= zhigh]
                for v in (local if local else pool):
                    if v not in candidates:
                        candidates.append(v)
            shop = ShopManager.shops.get(mob.vnum)
            if shop:
                if getattr(shop, '_autostocked', False):
                    return   # already enriched once; don't re-stock every reset
                shop._autostocked = True
                # repair a malformed/empty buy list (e.g. a vnum where a type belongs)
                if not shop.buy_types or any(not str(b).isalpha() for b in shop.buy_types):
                    shop.buy_types = buys_types
                have = set(getattr(shop, 'sells_vnums', []) or [])
                for v in candidates:
                    if len(shop.inventory) >= TARGET:
                        break
                    if v in have:
                        continue
                    obj = create_object(v, self)
                    if obj:
                        shop.inventory.append(obj)
                        shop.sells_vnums.append(v)
                        have.add(v)
                logger.info(f"Stocked shop for {getattr(mob, 'name', '?')} (vnum {mob.vnum}) -> {len(shop.inventory)} items")
            else:
                sells = candidates[:TARGET]
                if sells:
                    ShopManager.create_shop(mob, {'sells': sells, 'buys': buys_types}, self)
        except Exception as e:
            logger.warning(f"_ensure_shop failed for {getattr(mob, 'name', '?')}: {e}")

    def get_room(self, vnum: int) -> Optional[Room]:
        """Get a room by vnum."""
        return self.rooms.get(vnum)

    def login_room(self, player) -> Optional[Room]:
        """Where a player comes into the world: the room they left, while it exists and they may
        be there; else (a private trial closed while they were away, the God Rooms, a land sealed
        until built) their recall room, or the temple."""
        room = self.get_room(getattr(player, 'room_vnum', None) or self.config.STARTING_ROOM)
        if room is None or not room.admits(player):
            room = (player.recall_room() if hasattr(player, 'recall_room') else None) \
                or self.get_room(self.config.STARTING_ROOM)
        return room
        
    async def add_player(self, player: 'Player'):
        """Add a player to the world."""
        self.players[player.name.lower()] = player

        # Spawn persistent companions
        if hasattr(player, 'companions') and player.companions:
            from pets import Pet
            from companions import Companion
            for companion in player.companions:
                if isinstance(companion, Pet) and companion.is_persistent:
                    # Add companion to world
                    companion.room = player.room
                    player.room.characters.append(companion)
                    self.npcs.append(companion)
                    logger.info(f"Spawned companion: {companion.name} for {player.name}")
                elif isinstance(companion, Companion):
                    companion.room = player.room
                    player.room.characters.append(companion)
                    self.npcs.append(companion)
                    logger.info(f"Spawned companion: {companion.name} for {player.name}")

        # a one-time gift given at load (grants.py): tell them, once they can hear it; a character
        # made just now (or whose account came after the load) is given theirs here
        notes = list(player.__dict__.pop('_grant_notes', None) or [])
        try:
            import grants
            notes += grants.apply_grants(player, entering=True)
        except Exception:
            logger.exception('grants')
        if player.__dict__.pop('_grant_save', False):
            try:
                await player.save()          # the account a gift made them, remembered
            except Exception:
                logger.exception('grant save')
        if notes:
            c = Config().COLORS
            for line in notes:
                await player.send(f"{c['bright_yellow']}{line}{c['reset']}")
        if player.__dict__.pop('_grant_gearup', False):
            try:
                from commands import CommandHandler
                report = await CommandHandler.gear_up(player)
                c = Config().COLORS
                await player.send(f"{c['bright_yellow']}The gods kit you out for the hardest roads: {', '.join(report)}.{c['reset']}")
            except Exception:
                logger.exception('grant gearup')
        logger.info(f"Player entered world: {player.name}")

    async def remove_player(self, player: 'Player'):
        """Remove a player from the world."""
        # Remove persistent companions from world (but keep in player's companion list)
        if hasattr(player, 'companions') and player.companions:
            from pets import Pet
            from companions import Companion
            for companion in player.companions:
                if isinstance(companion, Pet) and companion.is_persistent:
                    if companion.room and companion in companion.room.characters:
                        companion.room.characters.remove(companion)
                    if companion in self.npcs:
                        self.npcs.remove(companion)
                    logger.info(f"Removed companion: {companion.name} for {player.name}")
                elif isinstance(companion, Companion):
                    if companion.room and companion in companion.room.characters:
                        companion.room.characters.remove(companion)
                    if companion in self.npcs:
                        self.npcs.remove(companion)
                    logger.info(f"Removed companion: {companion.name} for {player.name}")

        # only this very character: a newer session of the same name stays in the world
        if self.players.get(player.name.lower()) is player:
            del self.players[player.name.lower()]

        left_room = player.room
        if player.room and player in player.room.characters:
            player.room.characters.remove(player)

        logger.info(f"Player left world: {player.name}")
        # bystanders' graphical clients drop the departed player immediately
        wm = getattr(self, 'web_map', None)
        if wm and left_room:
            try:
                await wm.notify_room(left_room, {'type': 'player_move', 'name': player.name, 'action': 'leave', 'from': getattr(left_room, 'vnum', None)})
            except Exception:
                pass
        
    def get_player(self, name: str) -> Optional['Player']:
        """Get an online player by name."""
        return self.players.get(name.lower())
        
    async def combat_tick(self):
        """Process combat for all fighting characters."""
        from combat import CombatHandler

        # Round heartbeat: cmd_swing's perfect-strike timing window is judged
        # against when this round actually began
        self.last_combat_round = time.time()

        # Intent pre-pass: fighting mobs DECLARE their next special before the
        # player phase runs, so this round's web push (notify_combat below)
        # carries the wind-up with a full round left to react. The intent
        # resolves next round in mob_ai_tick.
        from mob_ai import declare_intents
        from environment import check_player_traps, tick as env_tick
        import action_combat
        for npc in list(self.npcs):
            if npc.is_fighting and npc.fighting is not None and not action_combat.on_clock(npc):
                try:
                    # a fighting mob can stumble into a player-laid trap
                    if getattr(npc.room, 'player_traps', None) and __import__('random').random() < 0.30:
                        await check_player_traps(npc, npc.room)
                    await declare_intents(npc)
                except Exception as e:
                    logger.debug(f"declare_intents failed for {npc.name}: {e}")
        # burning rooms cook everyone inside
        try:
            await env_tick(self)
        except Exception as e:
            logger.debug(f"environment tick failed: {e}")
        # the deep drowns, and crushes (zone_hazards.py)
        try:
            import zone_hazards
            await zone_hazards.tick(self)
        except Exception:
            logger.exception('zone hazards tick')

        # Process player combat
        for player in list(self.players.values()):
            # If mobs are attacking the player, set fighting target to one of them
            if not player.is_fighting and player.room:
                attackers = [ch for ch in player.room.characters if hasattr(ch, 'fighting') and ch.fighting == player]
                if attackers:
                    player.fighting = attackers[0]
                    player.position = 'fighting'
                elif player.position == 'fighting':
                    # Clear stuck combat state
                    player.position = 'standing'

            # Autoattack if enabled
            if getattr(player, 'autoattack', False) and not player.is_fighting:
                target = getattr(player, 'target', None)
                if target and player.room and target in player.room.characters:
                    if not hasattr(target, 'connection') and 'peaceful' not in player.room.flags:
                        await CombatHandler.start_combat(player, target)

            if player.is_fighting:
                # Check if target is still valid
                if player.fighting is None or player.fighting.hp <= 0 or player.fighting not in player.room.characters:
                    player.fighting = None
                    player.position = 'standing'
                    continue
                if action_combat.active(player):
                    # action mode (action_combat.py): the swings are on the player's own clock;
                    # the round still brings rituals, pets, a companion, a burning mount
                    await CombatHandler.round_extras(player, player.fighting)
                elif not action_combat.round_skips(player):
                    await CombatHandler.one_round(player, player.fighting)
                # Send prompt after combat round so player always sees HP
                if hasattr(player, 'connection') and player.connection:
                    await player.connection.send_prompt()
                # Push live vitals to graphical web clients every round
                if getattr(self, 'web_map', None):
                    try:
                        await self.web_map.notify_combat(player)
                    except Exception as e:
                        logger.debug(f"notify_combat failed for {player.name}: {e}")

        # Creatures strike a beat after the heroes (combat v2): the exchange alternates on
        # screen and in the log instead of every blow landing in the same instant.
        try:
            from combat_range import NPC_PHASE_DELAY
            loop = asyncio.get_running_loop()
            loop.call_later(NPC_PHASE_DELAY, lambda: asyncio.ensure_future(self._npc_combat_phase()))
        except Exception as e:
            logger.debug(f"npc phase scheduling failed, running inline: {e}")
            await self._npc_combat_phase()

    async def _npc_combat_phase(self):
        """The creatures' half of a combat round (see combat_tick)."""
        from combat import CombatHandler
        from mob_ai import mob_ai_tick
        import action_combat
        rooms = set()
        for npc in list(self.npcs):
            # a creature fighting an action-mode player takes its turns on its own clock
            if npc.is_fighting and action_combat.round_skips(npc):
                continue
            if npc.is_fighting:
                # Check if target is still valid
                if npc.fighting is None or npc.fighting.hp <= 0 or (hasattr(npc.fighting, 'room') and npc.fighting not in npc.room.characters):
                    npc.fighting = None
                    npc.position = 'standing'
                    continue
                # Run intelligent mob AI before the auto-attack round
                try:
                    await mob_ai_tick(npc)
                except Exception as e:
                    logger.debug(f"Mob AI error for {npc.name}: {e}")
                # Re-check fighting state (AI may have caused flee/death)
                if not npc.is_fighting or not npc.fighting:
                    continue
                try:
                    await CombatHandler.one_round(npc, npc.fighting)
                except Exception as e:
                    logger.debug(f"npc round failed for {getattr(npc, 'name', '?')}: {e}")
                if getattr(npc, 'room', None) is not None:
                    rooms.add(npc.room)
        # the heroes' vitals after the creatures struck, at once (not next round)
        if getattr(self, 'web_map', None):
            for room in rooms:
                for ch in list(getattr(room, 'characters', []) or []):
                    if hasattr(ch, 'account_name'):
                        try:
                            await self.web_map.notify_combat(ch)
                        except Exception:
                            pass
                
    async def affect_tick(self):
        """Process DOT/HOT effects and decrement durations."""
        from affects import AffectManager

        for player in self.players.values():
            await AffectManager.tick_affects(player)

        for npc in self.npcs:
            if hasattr(npc, 'affects'):
                await AffectManager.tick_affects(npc)

    async def poison_tick(self):
        """Process poison damage for all characters (faster tick)."""
        from affects import AffectManager

        for player in self.players.values():
            # Only process poison DOT effects, don't decrement durations
            await AffectManager.tick_affects(player, poison_only=True)

        for npc in self.npcs:
            # Only process poison DOT effects, don't decrement durations
            await AffectManager.tick_affects(npc, poison_only=True)

    async def regen_tick(self):
        """Process regeneration for all characters."""
        c = Config().COLORS
        for player in self.players.values():
            await player.regen_tick()
            # Notify players with tick notifications enabled
            if getattr(player, 'show_ticks', False):
                await player.send(f"{c['cyan']}[TICK - Regen]{c['reset']}")

        for npc in self.npcs:
            if hasattr(npc, 'regen_tick'):
                await npc.regen_tick()

    async def minor_regen_tick(self):
        """Process small between-tick regeneration for all characters."""
        for player in self.players.values():
            if hasattr(player, 'minor_regen_tick'):
                await player.minor_regen_tick()

    async def zone_reset_tick(self):
        """Check and reset zones as needed (the world's creatures counted once for them all)."""
        counts = None
        for zone in self.zones.values():
            zone.age += 1
            if zone.age >= zone.lifespan:
                if zone.reset_mode == 1 and any(p.room and p.room.zone == zone for p in self.players.values()):
                    continue        # reset only when empty
                if zone.reset_mode in (1, 2):
                    if counts is None:
                        counts = self._creature_counts()
                    await self.reset_zone(zone, counts)

    async def time_tick(self):
        """Process game time advancement."""
        old_hour = self.game_time.hour
        old_day = (self.game_time.year, self.game_time.month, self.game_time.day)

        # Advance time by 1 second
        self.game_time.advance_tick(1)

        # Check if hour changed
        if self.game_time.hour != old_hour:
            # Get time announcement for significant events (the page draws the sun's arc, so the
            # line stays in its log, dimmed); hunger and thirst drain in Player.hunger_thirst_tick
            announcement = self.game_time.get_time_announcement()
            if announcement:
                # Announce to all players
                c = self.config.COLORS
                for player in self.players.values():
                    await msgkind.send_ui(player, f"\r\n{c['yellow']}{announcement}{c['reset']}\r\n")
                logger.info(f"Time: {self.game_time.get_time_string()}")
            await web_hud.push_sky(self)

            # Process NPC schedules (shopkeepers open/close, etc.)
            try:
                from npc_schedules import schedule_tick
                await schedule_tick(self)
            except Exception as e:
                logger.debug(f"NPC schedule error: {e}")

        # what the page draws of each player (web_hud.py), sent when it changed
        await web_hud.tick(self)

        # Daily upkeep for companions
        new_day = (self.game_time.year, self.game_time.month, self.game_time.day)
        if new_day != old_day:
            from companions import CompanionManager
            await CompanionManager.apply_daily_upkeep(self)

    async def weather_tick(self):
        """Process weather updates for all zones (and, as often: a rare elite may turn up where
        someone plays, elites.py; the day's bounties are posted, bounties.py)."""
        try:
            import elites, bounties
            bounties.refresh(self)
            await elites.tick(self)
        except Exception as e:
            logger.warning(f"elites/bounties tick failed: {e}")
        for zone in self.zones.values():
            if zone.number > 0:  # Skip Limbo (zone 0)
                old_weather = zone.weather.sky_condition
                zone.weather.update_weather(self.game_time)

                # Announce significant weather changes to players in the zone
                if zone.weather.sky_condition != old_weather:
                    c = self.config.COLORS
                    weather_desc = zone.weather.get_weather_desc()

                    for player in self.players.values():
                        if player.room and player.room.zone == zone:
                            await msgkind.send_ui(player, f"\r\n{c['cyan']}{weather_desc}{c['reset']}\r\n")
                    await web_hud.push_sky(self, zone)

    async def pet_tick(self):
        """Process pet timers and expiration."""
        from pets import PetManager
        await PetManager.pet_tick(self)

    async def decay_tick(self):
        """Process corpse decay and ground item decay.
        
        Corpses decay after ~5 minutes real time (50 ticks at 6s/tick).
        When a corpse decays, its contents drop to the ground.
        Ground items (non-permanent) decay after 2-3 MUD days (~30 min real time).
        """
        for room in self.rooms.values():
            if not hasattr(room, 'items'):
                continue
            items_to_remove = []
            items_to_add = []
            
            for item in room.items:
                # Initialize decay timer if not set
                if not hasattr(item, 'decay_timer'):
                    if 'corpse' in getattr(item, 'name', '').lower():
                        item.decay_timer = 50  # ~5 min at 6s per tick
                    elif getattr(item, 'item_type', '') in ('key',):
                        item.decay_timer = 300  # Keys last longer (~30 min)
                    elif hasattr(item, '_permanent') and item._permanent:
                        item.decay_timer = -1  # Never decay (zone resets)
                    else:
                        item.decay_timer = -1  # Don't decay zone-spawned items
                
                if item.decay_timer < 0:
                    continue  # Permanent item
                    
                item.decay_timer -= 1
                
                if item.decay_timer <= 0:
                    if 'corpse' in getattr(item, 'name', '').lower():
                        # Corpse decays — drop contents to ground
                        contents = getattr(item, 'contents', [])
                        for contained in contents:
                            contained.decay_timer = 500  # ~50 min for dropped items
                            items_to_add.append(contained)
                        # Notify players in room
                        for char in room.characters:
                            if hasattr(char, 'send'):
                                c = char.config.COLORS
                                await char.send(f"{c['yellow']}{item.short_desc} decays, leaving behind its contents.{c['reset']}")
                    else:
                        # Regular item decays
                        for char in room.characters:
                            if hasattr(char, 'send'):
                                c = char.config.COLORS
                                await char.send(f"{c['yellow']}{item.short_desc} crumbles to dust.{c['reset']}")
                    items_to_remove.append(item)
            
            for item in items_to_remove:
                room.items.remove(item)
            for item in items_to_add:
                room.items.append(item)

    # creatures where no player is (nor in the next room) think this many times more slowly:
    # running every creature in the world ten times a second was most of an idle server's CPU
    NPC_SLEEP_EVERY = 10

    def _awake_zones(self):
        """The zones a player is in or looks into (the rooms next to theirs)."""
        zones = set()
        for pl in self.players.values():
            room = getattr(pl, 'room', None)
            if room is None:
                continue
            zones.add(getattr(room.zone, 'number', None))
            for ed in (room.exits or {}).values():
                nxt = ed.get('room') if isinstance(ed, dict) else None
                if nxt is not None:
                    zones.add(getattr(getattr(nxt, 'zone', None), 'number', None))
        return zones

    async def process_npcs(self):
        """Process NPC AI. One creature's error is logged and the rest go on: before, one (a
        creature attacking a rider) took the whole server down. Creatures in zones no player is
        in (or next to) run one tick in NPC_SLEEP_EVERY, each on its own turn."""
        from brain import scheduler
        self._npc_tick = (getattr(self, '_npc_tick', 0) + 1) % self.NPC_SLEEP_EVERY
        awake = self._awake_zones()
        t0, thought = time.perf_counter(), 0
        for i, npc in enumerate(list(self.npcs)):
            if not scheduler.due(npc, i, self._npc_tick, awake, self.NPC_SLEEP_EVERY):     # (brain/scheduler.py)
                continue
            if hasattr(npc, 'process_ai'):
                thought += 1
                try:
                    await npc.process_ai()
                except Exception:
                    logger.exception(f"AI of {getattr(npc, 'name', npc)} (vnum {getattr(npc, 'vnum', '?')}) failed")
        scheduler.STATS.record((time.perf_counter() - t0) * 1000.0, thought)
                
    async def autosave(self):
        """Autosave all players."""
        for player in self.players.values():
            await player.save()
        logger.info(f"Autosaved {len(self.players)} players")
        
    async def save_all(self):
        """Save all players on shutdown."""
        for player in self.players.values():
            await player.save()
        logger.info(f"Saved all {len(self.players)} players")
        
    async def broadcast(self, message: str, exclude: List = None, kind: str = None):
        """Broadcast a message to all players (kind: msgkind.UI for a line the page also draws)."""
        exclude = exclude or []
        for player in self.players.values():
            if player not in exclude:
                if kind == msgkind.UI:
                    await msgkind.send_ui(player, f"\r\n{message}\r\n")
                else:
                    await player.send(f"\r\n{message}\r\n")
