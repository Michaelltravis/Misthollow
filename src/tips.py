"""
Misthollow Tips System
=====================
Provides helpful tips to players at appropriate moments.
"""

import random
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from player import Player

# Tips organized by category and trigger conditions
TIPS = {
    # New player tips (shown early in game)
    'newbie': [
        "Tip: Type 'help' to see help on any topic.",
        "Tip: Type 'score' to see your character stats.",
        "Tip: Type 'inventory' or 'i' to see what you're carrying.",
        "Tip: Type 'equipment' or 'eq' to see what you're wearing.",
        "Tip: Type 'consider <mob>' before fighting to gauge difficulty.",
        "Tip: Type 'look <object>' to examine things more closely.",
        "Tip: Type 'commands' to see a list of all available commands.",
        "Tip: Type 'achievements' to see your progress and goals.",
    ],
    
    # Combat tips
    'combat': [
        "Tip: Use 'flee' if a fight is going badly!",
        "Tip: Watch your HP in the prompt. Heal before it's too late!",
        "Tip: 'Consider' a mob first to see if you can handle it.",
        "Tip: Some mobs are aggressive and will attack on sight.",
        "Tip: Fighting higher level mobs gives bonus experience.",
        "Tip: Weapons with better damage dice deal more damage.",
        "Tip: Your armor class affects how often you get hit.",
    ],
    
    # Exploration tips
    'exploration': [
        "Tip: Type 'search' in some rooms to find hidden exits or items.",
        "Tip: Some exits are hidden and must be discovered.",
        "Tip: You gain bonus XP for exploring new rooms!",
        "Tip: Different terrain types affect movement speed.",
        "Tip: The 'map' command shows a web-based map of the area.",
        "Tip: Look around - room descriptions often contain hints.",
    ],
    
    # Economy tips
    'economy': [
        "Tip: Visit the bank in Garathorm to store your gold safely.",
        "Tip: 'Sell' items at shops to make money.",
        "Tip: 'List' shows what a shop has for sale.",
        "Tip: Different shops buy different types of items.",
        "Tip: 'Value <item>' shows what a shop will pay for it.",
    ],
    
    # Class tips (shown based on player class)
    'warrior': [
        "Tip: Warriors gain rage when dealing and taking damage.",
        "Tip: Use 'stance' to switch between combat stances.",
        "Tip: Berserk stance deals more damage but lowers defense.",
        "Tip: 'Warcry' boosts your party's combat effectiveness.",
    ],
    'mage': [
        "Tip: Mages gain arcane charges when casting offensive spells.",
        "Tip: Your INT stat increases spell damage.",
        "Tip: 'Spells' shows all spells you know.",
        "Tip: Memorize your spells' mana costs to manage resources.",
    ],
    'thief': [
        "Tip: Thieves build combo points with each attack.",
        "Tip: Use 'backstab' to start combat with massive damage.",
        "Tip: 'Hide' and 'sneak' help you move undetected.",
        "Tip: Your DEX stat affects your crit chance.",
    ],
    'cleric': [
        "Tip: Clerics gain divine favor when healing allies.",
        "Tip: 'Heal' is your bread and butter spell.",
        "Tip: Sanctuary spell greatly reduces damage taken.",
        "Tip: Turn undead to damage or destroy undead enemies.",
    ],
    'ranger': [
        "Tip: Rangers excel in outdoor environments.",
        "Tip: 'Track' helps you find creatures or players.",
        "Tip: Your pet fights alongside you in combat.",
        "Tip: Ranged attacks can hit enemies before they reach you.",
    ],
    'paladin': [
        "Tip: Paladins can use auras to buff nearby allies.",
        "Tip: 'Lay hands' provides powerful healing.",
        "Tip: Your alignment affects your holy abilities.",
        "Tip: Smite evil deals bonus damage to evil creatures.",
    ],
    'necromancer': [
        "Tip: Necromancers can raise undead servants.",
        "Tip: 'Soulstone' creates a powerful offhand item from corpses.",
        "Tip: 'Imbue' upgrades your soulstone using more corpses.",
        "Tip: Your servants gain themed abilities as you level.",
    ],
    'bard': [
        "Tip: Bards inspire allies with magical songs.",
        "Tip: Songs affect everyone in your group.",
        "Tip: CHA is your primary stat for song effectiveness.",
        "Tip: Mix songs for different situations.",
    ],
    
    # Survival tips
    'survival': [
        "Tip: Eat food to prevent starvation penalties.",
        "Tip: Drink water to stay hydrated.",
        "Tip: Rest to regenerate HP and mana faster.",
        "Tip: Save your game often by 'quit' and reconnecting.",
    ],
    
    # Social tips
    'social': [
        "Tip: Talk to NPCs with 'chat <npc> <message>'.",
        "Tip: 'Gossip' sends a message to all players online.",
        "Tip: 'Emote' lets you express actions creatively.",
        "Tip: 'Who' shows who else is playing.",
        "Tip: Use the 'newbie' channel to ask for help — friendly players are listening!",
        "Tip: 'Group invite <player>' to team up for tough fights!",
    ],

    # Systems tips (shown after players have some experience)
    'systems': [
        "Tip: Look for NPCs with [!] — they have quests for you!",
        "Tip: Type 'quests' to check your quest log and objectives.",
        "Tip: Try 'mine', 'forage', or 'fish' when you find resource nodes.",
        "Tip: Type 'achievements' to see goals and track your progress.",
        "Tip: At level 10, unlock your talent tree with 'talents'!",
        "Tip: Type 'help newbie' for a comprehensive new player guide.",
        "Tip: At level 20, you can recruit a companion to fight alongside you!",
        "Tip: Visit the PvP Arena for competitive combat against other players.",
    ],
}

# Tips shown after specific events
EVENT_TIPS = {
    'first_kill': "Great job on your first kill! Check 'achievements' to see your progress.",
    'first_death': "Don't worry about dying - you respawn at the temple with partial health.",
    'level_up': "Congratulations on leveling up! New abilities come with your level, and every ability grows as you use it.",
    'low_health': "Your health is low! Consider fleeing or using a healing item.",
    'new_zone': "You've entered a new area. 'Look' around to get your bearings.",
    'found_secret': "You found a secret! Keep searching - there may be more hidden things.",
}

# Contextual hints shown once per player at key moments
CONTEXTUAL_HINTS = {
    'gathering_room': "You notice resource nodes here! Try 'mine', 'forage', or 'fish' to gather materials for crafting.",
    'quest_giver': "This NPC has a [!] marker — they have a quest for you! Type 'talk <name>' to learn more.",
    'first_combat_resource': {
        'warrior': "As a warrior, you build Rage when dealing and taking damage. Spend it on powerful abilities!",
        'mage': "As a mage, you spend Mana to cast spells. Keep an eye on it with 'score'!",
        'thief': "As a thief, you build Combo Points with each attack. Spend them on finishing moves!",
        'cleric': "As a cleric, you earn Divine Favor when healing allies. It powers your strongest prayers!",
        'ranger': "As a ranger, you build Focus in combat. Use it for devastating precision attacks!",
        'paladin': "As a paladin, you radiate Holy Power. It fuels your smites and auras!",
        'bard': "As a bard, your Inspiration grows as you perform. Use it to empower your songs!",
        'necromancer': "As a necromancer, you harvest Soul Fragments from fallen foes. They fuel your dark arts!",
    },
    'level_10': "You've reached level 10! Type 'talents' to see your talent tree — customize your playstyle!",
    'level_20': "Level 20 unlocked! Type 'companion' to learn about companions that can fight alongside you.",
    'level_50': "Level 50 — the pinnacle! Prestige classes are now available. Type 'help prestige' to learn more.",
    # Tutorial step prompts (one-time, skippable)
    'tutorial_move': "New here? Use N/S/E/W (or 'n'/'s') to move. 'look' repeats a room description.",
    'tutorial_inventory': "Use 'inventory' to see your items. Try 'wield <weapon>' or 'wear <item>' to equip gear.",
    'tutorial_wield': "Wielded weapons boost your damage. Check 'score' for a quick combat readout.",
    'tutorial_quest_accept': "Quest accepted! Use 'quests' to track objectives, and 'hint' for guidance.",
}

# The same advice for a /play player, who has windows and keys rather than a command line: a tip
# that names a typed command is said as what to press (for_play). A tip not listed reads the same.
PLAY_TIPS = {
    "Tip: Type 'help' to see help on any topic.": "Tip: Press H for help on any topic.",
    "Tip: Type 'score' to see your character stats.": "Tip: Press C to see your character sheet.",
    "Tip: Type 'inventory' or 'i' to see what you're carrying.": "Tip: Press I to see what you're carrying.",
    "Tip: Type 'equipment' or 'eq' to see what you're wearing.": "Tip: Press I: what you wear is on the figure beside your pack.",
    "Tip: Type 'consider <mob>' before fighting to gauge difficulty.": "Tip: Target a creature (Tab or a click): its frame says how hard a fight it is.",
    "Tip: Type 'look <object>' to examine things more closely.": "Tip: Right-click a creature or a thing to see what you can do with it.",
    "Tip: Type 'commands' to see a list of all available commands.": "Tip: Press H for the full list of what you can do.",
    "Tip: Type 'achievements' to see your progress and goals.": "Tip: Press Y for your almanac: achievements, progress and goals.",
    "Tip: Use 'flee' if a fight is going badly!": "Tip: The running figure at the end of your bar flees a fight that is going badly!",
    "Tip: Watch your HP in the prompt. Heal before it's too late!": "Tip: Watch the red orb. Heal before it's too late!",
    "Tip: 'Consider' a mob first to see if you can handle it.": "Tip: A creature's frame says how it compares with you: look before you swing.",
    "Tip: Type 'search' in some rooms to find hidden exits or items.": "Tip: Typing 'search' in the chat line finds hidden exits or items in some rooms.",
    "Tip: The 'map' command shows a web-based map of the area.": "Tip: Press M for the map of the zone and of the world.",
    "Tip: 'Sell' items at shops to make money.": "Tip: Right-click a shopkeeper to trade: the Sell tab turns loot into gold.",
    "Tip: 'List' shows what a shop has for sale.": "Tip: Right-click a shopkeeper to see what they sell.",
    "Tip: 'Value <item>' shows what a shop will pay for it.": "Tip: A shop's Sell tab shows what it will pay for each thing you carry.",
    "Tip: 'Spells' shows all spells you know.": "Tip: Press K for your spellbook: every spell you know.",
    "Tip: Save your game often by 'quit' and reconnecting.": "Tip: Your hero is saved as you play; Log out is in Settings (O).",
    "Tip: 'Who' shows who else is playing.": "Tip: Press P to see who else is playing.",
    "Tip: Type 'quests' to check your quest log and objectives.": "Tip: Press L for your quest journal; the tracker on the right shows the next step.",
    "Tip: Type 'achievements' to see goals and track your progress.": "Tip: Press Y for your almanac: goals and your progress.",
    "Tip: At level 10, unlock your talent tree with 'talents'!": "Tip: At level 10 your talent tree opens: press N!",
    "Tip: Type 'help newbie' for a comprehensive new player guide.": "Tip: Press H and look up 'newbie' for a new player guide.",
    "Great job on your first kill! Check 'achievements' to see your progress.": "Great job on your first kill! Your almanac (Y) shows your progress.",
    "You've entered a new area. 'Look' around to get your bearings.": "You've entered a new area. The map (M) shows where you are.",
    "This NPC has a [!] marker — they have a quest for you! Type 'talk <name>' to learn more.": "This one has a quest for you! Right-click them, then Talk.",
    "As a mage, you spend Mana to cast spells. Keep an eye on it with 'score'!": "As a mage, you spend Mana to cast spells. Keep an eye on the blue orb!",
    "You've reached level 10! Type 'talents' to see your talent tree — customize your playstyle!": "You've reached level 10! Press N to see your talent tree — customize your playstyle!",
    "Level 50 — the pinnacle! Prestige classes are now available. Type 'help prestige' to learn more.": "Level 50 — the pinnacle! Prestige classes are now available: press G for your legend.",
    "New here? Use N/S/E/W (or 'n'/'s') to move. 'look' repeats a room description.": "New here? W, A, S and D move you, or click where you want to go.",
    "Use 'inventory' to see your items. Try 'wield <weapon>' or 'wear <item>' to equip gear.": "Press I to see your items. Drag a weapon or a piece of armour onto the figure to equip it.",
    "Wielded weapons boost your damage. Check 'score' for a quick combat readout.": "Wielded weapons boost your damage. Your character sheet (C) has the numbers.",
    "You notice resource nodes here! Try 'mine', 'forage', or 'fish' to gather materials for crafting.": "You notice resource nodes here! Click one to gather materials for crafting.",
    "Tip: Try 'mine', 'forage', or 'fish' when you find resource nodes.": "Tip: Click a resource node (ore, herbs, a fishing spot) to gather from it.",
    "Quest accepted! Use 'quests' to track objectives, and 'hint' for guidance.": "Quest accepted! The tracker on the right shows the next step; your journal (L) has them all.",
}


def for_play(player, text):
    """`text` as a /play player should read it (PLAY_TIPS); telnet players read it as written."""
    if isinstance(text, str) and getattr(getattr(player, 'connection', None), 'is_web', False):
        return PLAY_TIPS.get(text, text)
    return text


class TipManager:
    """Manages tip delivery to players."""
    
    # Track tips shown to avoid repeats
    _shown_tips = {}  # player_name -> set of tip texts
    
    @classmethod
    def get_tip(cls, player: 'Player', category: str = None) -> Optional[str]:
        """Get a random tip for the player, optionally from a specific category."""
        
        # Get player's shown tips
        shown = cls._shown_tips.get(player.name, set())
        
        # Determine which categories to pull from
        categories = []
        if category:
            categories = [category]
        else:
            # Default categories
            categories = ['newbie', 'exploration', 'survival']
            
            # Add class-specific tips
            char_class = str(getattr(player, 'char_class', '')).lower()
            if char_class in TIPS:
                categories.append(char_class)
            
            # Add combat tips if player has been in combat
            if hasattr(player, 'achievement_progress'):
                if player.achievement_progress.get('kills', 0) > 0:
                    categories.append('combat')
        
        # Collect all applicable tips
        available = []
        for cat in categories:
            if cat in TIPS:
                for tip in TIPS[cat]:
                    if tip not in shown:
                        available.append(tip)
        
        if not available:
            # All tips shown, reset
            cls._shown_tips[player.name] = set()
            for cat in categories:
                if cat in TIPS:
                    available.extend(TIPS[cat])
        
        if available:
            tip = random.choice(available)
            if player.name not in cls._shown_tips:
                cls._shown_tips[player.name] = set()
            cls._shown_tips[player.name].add(tip)
            return tip
        
        return None
    
    @classmethod
    async def maybe_show_tip(cls, player: 'Player', chance: float = 0.1) -> bool:
        """Maybe show a tip to the player (default 10% chance)."""
        if random.random() > chance:
            return False
        
        tip = cls.get_tip(player)
        if tip:
            c = player.config.COLORS
            await player.send(f"\r\n{c['cyan']}{for_play(player, tip)}{c['reset']}\r\n")
            return True
        return False
    
    @classmethod
    async def show_event_tip(cls, player: 'Player', event: str):
        """Show a tip for a specific event."""
        if event in EVENT_TIPS:
            c = player.config.COLORS
            await player.send(f"\r\n{c['bright_cyan']}{for_play(player, EVENT_TIPS[event])}{c['reset']}\r\n")

    # Track which contextual hints each player has seen
    _contextual_shown = {}  # player_name -> set of hint keys

    @classmethod
    async def show_contextual_hint(cls, player: 'Player', hint_key: str) -> bool:
        """Show a one-time contextual hint. Returns True if hint was shown."""
        shown = cls._contextual_shown.get(player.name, set())
        # Also check player's persistent hints_shown attribute
        persistent = getattr(player, 'hints_shown', set())
        if hint_key in shown or hint_key in persistent:
            return False

        hint = CONTEXTUAL_HINTS.get(hint_key)
        if hint is None:
            return False

        # Handle dict hints (class-specific)
        if isinstance(hint, dict):
            char_class = str(getattr(player, 'char_class', '')).lower()
            hint = hint.get(char_class)
            if not hint:
                return False

        c = player.config.COLORS
        await player.send(f"\r\n{c['bright_cyan']}💡 {for_play(player, hint)}{c['reset']}\r\n")

        # Mark as shown
        if player.name not in cls._contextual_shown:
            cls._contextual_shown[player.name] = set()
        cls._contextual_shown[player.name].add(hint_key)
        if not hasattr(player, 'hints_shown'):
            player.hints_shown = set()
        player.hints_shown.add(hint_key)
        return True

    @classmethod
    def _tutorial_active(cls, player: 'Player') -> bool:
        """Return True if tutorial hints should be shown for this player."""
        if getattr(player, 'tutorial_hints_enabled', True) is False:
            return False
        if getattr(player, 'level', 1) > 10:
            return False
        completed = set(getattr(player, 'quests_completed', []) or [])
        if 'tutorial_12_quests_groups' in completed:
            return False
        return True

    @classmethod
    async def show_tutorial_hint(cls, player: 'Player', hint_key: str) -> bool:
        """Show a tutorial hint if the player is still in the tutorial flow."""
        if not cls._tutorial_active(player):
            return False
        return await cls.show_contextual_hint(player, hint_key)
