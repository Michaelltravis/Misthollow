"""
Affect Management System

This module provides a comprehensive system for managing temporary effects (buffs/debuffs)
on characters. Affects can modify stats, add flags, or apply damage/healing over time.

The system fixes the original broken affects implementation where buffs never expired.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Dict, Any, Optional
import logging

if TYPE_CHECKING:
    from player import Character

logger = logging.getLogger(__name__)


@dataclass
class Affect:
    """
    Represents a temporary effect on a character.

    Attributes:
        name: Spell/skill name that created this affect
        type: Type of affect ('modify_stat', 'flag', 'dot', 'hot')
        applies_to: What the affect modifies (stat name, flag name, etc.)
        value: Magnitude of the effect (can be positive or negative)
        duration: Total duration in ticks
        remaining: Ticks remaining before expiration
        caster_level: Level of the caster (for dispel calculations)
        source: Optional identifier of who/what cast this
    """
    name: str
    type: str
    applies_to: str
    value: int
    duration: int
    remaining: int
    caster_level: int = 1
    source: Optional[str] = None

    def __post_init__(self):
        """Ensure remaining is set to duration if not specified."""
        if self.remaining == 0 and self.duration > 0:
            self.remaining = self.duration


def _push_affects(character):
    """A character's affects changed: /play is told at once (the map payload otherwise comes only
    with a move). The player's own page gets its buff bar; everyone else in the room sees a change
    on the body (a sleeper lying down under its Zzz, a ward's glow: _push_room). Coalesced: a
    spell that sets several affects sends one payload."""
    wm = getattr(getattr(character, 'world', None), 'web_map', None)
    if wm is None or not hasattr(wm, 'notify_player'):
        return
    try:
        import asyncio
        loop = asyncio.get_running_loop()
    except Exception:
        return
    if getattr(character, '_affect_push', None) is not None:
        return
    def go():
        character._affect_push = None
        if hasattr(character, 'connection') and (not hasattr(wm, 'has_play') or wm.has_play(character)):
            loop.create_task(wm.notify_player(character))
        _push_room(wm, loop, character)
    try:
        character._affect_push = loop.call_later(0.12, go)
    except Exception:
        pass


def _push_room(wm, loop, character):
    """The others in the room see what changed on a body: only when what /play draws of it (its
    wards, lying asleep or standing) is different from what was last sent."""
    room = getattr(character, 'room', None)
    if room is None or not hasattr(wm, 'notify_room'):
        return
    try:
        from map_system import _wards
        sig = (tuple(_wards(character)), getattr(character, 'position', 'standing'))
    except Exception:
        return
    if getattr(character, '_shown_body', None) == sig:
        return
    character._shown_body = sig
    loop.create_task(wm.notify_room(room, skip=character))


def _tick_event(character, affect, amount, heal=False):
    """Show a tick on the 3D client (combat_hooks.tick_event); never let drawing break a tick."""
    try:
        from combat_hooks import tick_event
        tick_event(character, affect, amount, heal)
    except Exception:
        pass


def _wore_off(character, affect):
    try:
        from combat_hooks import wore_off
        wore_off(character, affect)
    except Exception:
        pass


class AffectManager:
    """
    Manages the application, removal, and ticking of affects on characters.

    This is a static utility class that handles all affect-related operations.
    """

    # Affect type constants
    TYPE_MODIFY_STAT = 'modify_stat'
    TYPE_STAT = TYPE_MODIFY_STAT      # the name the level 31-60 abilities use
    TYPE_FLAG = 'flag'
    TYPE_DOT = 'dot'  # Damage over time
    TYPE_HOT = 'hot'  # Healing over time

    # Valid stat names that can be modified
    VALID_STATS = {
        'str', 'int', 'wis', 'dex', 'con', 'cha',
        'hit', 'damage', 'armor_class', 'hitroll', 'damroll',
        'max_hp', 'max_mana', 'max_move',
        'saving_throw', 'spell_resist', 'damage_reduction',
        # percentage riders consumed by combat/spell/regen math
        'crit_chance', 'spell_power', 'heal_power', 'mana_regen',
    }

    # Valid flag names
    VALID_FLAGS = {
        'sanctuary', 'invisible', 'detect_invisible', 'detect_magic',
        'sense_life', 'waterwalk', 'fly', 'haste', 'slow',
        'blind', 'poisoned', 'paralyzed', 'stunned', 'feared',
        'silenced', 'regenerating', 'diseased', 'marked',
        'spirit_link', 'damage_redirect_pet',
        # New defensive flags
        'stoneskin', 'mirror_image', 'displacement', 'mana_shield',
        'ice_armor', 'fire_shield', 'spell_reflect', 'blink',
        'prot_evil', 'prot_good', 'divine_shield', 'invulnerable',
        'detect_evil', 'charmed', 'entangled', 'sleeping',
        'combustion', 'presence_of_mind', 'arcane_power',
        'guardian_spirit', 'beacon_of_light', 'holy_shield',
        'divine_guardian', 'aegis_ward', 'shadowform',
        'armour_ward', 'briskness', 'shielded', 'deafened', 'tracks_covered'
    }

    @staticmethod
    def apply_affect(character: 'Character', affect_data: Dict[str, Any]) -> Affect:
        """
        Apply a new affect to a character.

        Args:
            character: The character to apply the affect to
            affect_data: Dictionary containing affect parameters:
                - name: str (required)
                - type: str (required)
                - applies_to: str (required)
                - value: int (required)
                - duration: int (required, in ticks)
                - caster_level: int (optional, default 1)
                - source: str (optional)

        Returns:
            The created Affect object
        """
        # cast again on the same character, a spell is refreshed, not doubled: the copy it already
        # holds (the same spell, on the same thing, of the same kind) gives way to the new one
        for old in [a for a in getattr(character, 'affects', None) or []
                    if a.name == affect_data['name'] and a.applies_to == affect_data['applies_to']
                    and a.type == affect_data['type']]:
            AffectManager.remove_affect(character, old)

        # Create the affect object
        affect = Affect(
            name=affect_data['name'],
            type=affect_data['type'],
            applies_to=affect_data['applies_to'],
            value=affect_data['value'],
            duration=affect_data['duration'],
            remaining=affect_data['duration'],
            caster_level=affect_data.get('caster_level', 1),
            source=affect_data.get('source')
        )

        # Validate affect type
        if affect.type not in [AffectManager.TYPE_MODIFY_STAT, AffectManager.TYPE_FLAG,
                               AffectManager.TYPE_DOT, AffectManager.TYPE_HOT]:
            logger.warning(f"Invalid affect type '{affect.type}' for {affect.name}")
            return affect

        # Apply the affect based on type
        if affect.type == AffectManager.TYPE_MODIFY_STAT:
            AffectManager._apply_stat_modification(character, affect)
        elif affect.type == AffectManager.TYPE_FLAG:
            AffectManager._apply_flag(character, affect)

        # Add to character's affects list
        character.affects.append(affect)
        _push_affects(character)

        logger.debug(f"Applied affect '{affect.name}' to {character.name} "
                    f"({affect.type}: {affect.applies_to} = {affect.value}, "
                    f"duration: {affect.duration} ticks)")

        return affect

    @staticmethod
    def _apply_stat_modification(character: 'Character', affect: Affect):
        """Apply a stat modification to the character."""
        stat_name = affect.applies_to

        if stat_name not in AffectManager.VALID_STATS:
            logger.warning(f"Invalid stat name '{stat_name}' for affect {affect.name}")
            return

        # Modify the stat (riders like spell_power start at 0 when absent)
        if True:
            current_value = getattr(character, stat_name, 0)
            new_value = current_value + affect.value
            setattr(character, stat_name, new_value)
            logger.debug(f"  Modified {stat_name}: {current_value} -> {new_value}")

    @staticmethod
    def stat_bonus(character: 'Character', stat_name: str):
        """How much the character's active stat affects add to one stat right now."""
        return sum(a.value for a in (getattr(character, 'affects', None) or [])
                   if a.type == AffectManager.TYPE_MODIFY_STAT and a.applies_to == stat_name
                   and isinstance(a.value, (int, float)))

    @staticmethod
    def _apply_flag(character: 'Character', affect: Affect):
        """Apply a flag to the character."""
        flag_name = affect.applies_to

        if flag_name not in AffectManager.VALID_FLAGS:
            logger.warning(f"Invalid flag name '{flag_name}' for affect {affect.name}")
            return

        # Add the flag
        if not hasattr(character, 'affect_flags'):
            character.affect_flags = set()
        character.affect_flags.add(flag_name)
        # a magical sleep lays the body down (whatever cast it: Sleep, a lullaby, a creature's spell)
        if flag_name == 'sleeping' and (getattr(character, 'hp', 1) or 0) > 0:
            character.position = 'sleeping'
        logger.debug(f"  Added flag: {flag_name}")

    @staticmethod
    def remove_affect(character: 'Character', affect: Affect):
        """
        Remove an affect from a character, reverting its effects.

        Args:
            character: The character to remove the affect from
            affect: The affect to remove
        """
        if affect not in character.affects:
            logger.warning(f"Attempted to remove non-existent affect '{affect.name}' "
                          f"from {character.name}")
            return

        # Revert the affect based on type
        if affect.type == AffectManager.TYPE_MODIFY_STAT:
            AffectManager._revert_stat_modification(character, affect)
        elif affect.type == AffectManager.TYPE_FLAG:
            AffectManager._revert_flag(character, affect)

        # Remove from affects list
        character.affects.remove(affect)
        _push_affects(character)

        logger.debug(f"Removed affect '{affect.name}' from {character.name}")

    @staticmethod
    def _revert_stat_modification(character: 'Character', affect: Affect):
        """Revert a stat modification from the character."""
        stat_name = affect.applies_to

        if hasattr(character, stat_name):
            current_value = getattr(character, stat_name)
            new_value = current_value - affect.value
            setattr(character, stat_name, new_value)
            logger.debug(f"  Reverted {stat_name}: {current_value} -> {new_value}")

    @staticmethod
    def _revert_flag(character: 'Character', affect: Affect):
        """Remove a flag from the character."""
        flag_name = affect.applies_to

        if hasattr(character, 'affect_flags') and flag_name in character.affect_flags:
            character.affect_flags.remove(flag_name)
            # ...and when it lifts (worn off, cleansed, struck awake) the sleeper gets up again
            if flag_name == 'sleeping' and getattr(character, 'position', None) == 'sleeping':
                character.position = 'fighting' if getattr(character, 'fighting', None) else 'standing'
            logger.debug(f"  Removed flag: {flag_name}")

    @staticmethod
    async def _dot_kills(character, amount):
        """Damage over time may finish a creature: the blow that would leave it at nothing is dealt
        as a wound from whoever it is fighting, who gets the kill. A player is never killed by
        it (lingering poison after a fight stops at 1 health). Returns None when the tick goes on
        as usual, 'dealt' when the wound was dealt here (and the creature lived), 'dead'."""
        if hasattr(character, 'connection') or amount < character.hp:
            return None
        killer = getattr(character, 'fighting', None)
        if killer is None or getattr(killer, 'hp', 0) <= 0:
            return None
        from combat import CombatHandler
        if await character.take_damage(amount, killer, 'poison'):
            await CombatHandler.handle_death(killer, character)
            return 'dead'
        return 'dealt'

    @staticmethod
    def _dot_amount(character, affect):
        """A lingering harm's tick, less what a player's worn gear turns aside of its kind
        (poison, burning, plague...: combat_range.harm_school; a bleed is a wound, unwarded)."""
        amount = affect.value
        if amount > 1 and hasattr(character, 'resistance'):
            try:
                import combat_range
                resist = character.resistance(combat_range.harm_school(affect.name))
            except Exception:
                resist = 0
            if resist:
                amount = max(1, int(amount * (100 - resist) / 100))
        return amount

    @staticmethod
    async def tick_affects(character: 'Character', poison_only: bool = False):
        """
        Process affects for one tick, decrementing durations and removing expired affects.
        Also applies DOT/HOT effects.

        This should be called every 5 seconds from the regeneration tick.
        Can also be called with poison_only=True every 2.5 seconds for poison damage.

        Args:
            character: The character whose affects to tick
            poison_only: If True, only process poison (DOT) damage, don't decrement durations
        """
        affects_to_remove = []

        for affect in character.affects[:]:  # Copy list to allow modification
            # Only process DOT effects if poison_only is True
            if poison_only:
                if affect.type == AffectManager.TYPE_DOT and affect.name == 'poison':
                    # Damage over time
                    amount = AffectManager._dot_amount(character, affect)
                    fate = await AffectManager._dot_kills(character, amount)
                    if fate == 'dead':
                        return
                    if fate == 'dealt':
                        continue
                    old_hp = character.hp
                    character.hp = max(1, character.hp - amount)
                    damage_dealt = old_hp - character.hp

                    if damage_dealt > 0:
                        _tick_event(character, affect, damage_dealt)
                        # Notify the character
                        if hasattr(character, 'send'):
                            await character.send(f"\x1b[32mYou shudder from the poison in your veins! ({damage_dealt} damage)\x1b[0m")

                        # Notify the room
                        if hasattr(character, 'room') and character.room:
                            await character.room.send_to_room(
                                f"\x1b[32m{character.name} looks ill from poison.\x1b[0m",
                                exclude=[character]
                            )
                continue

            # Full tick processing
            # Decrement remaining duration
            affect.remaining -= 1

            # Apply DOT/HOT effects
            if affect.type == AffectManager.TYPE_DOT:
                # Damage over time
                amount = AffectManager._dot_amount(character, affect)
                fate = await AffectManager._dot_kills(character, amount)
                if fate == 'dead':
                    return
                old_hp = character.hp
                if fate is None:
                    character.hp = max(1, character.hp - amount)
                damage_dealt = old_hp - character.hp

                if damage_dealt > 0:
                    _tick_event(character, affect, damage_dealt)
                    # Notify the character
                    if hasattr(character, 'send'):
                        await character.send(f"\x1b[32mYou take {damage_dealt} damage from {affect.name}!\x1b[0m")

                    # Notify the room
                    if hasattr(character, 'room') and character.room:
                        if affect.name == 'poison':
                            await character.room.send_to_room(
                                f"\x1b[32m{character.name} looks ill from poison.\x1b[0m",
                                exclude=[character]
                            )
                        else:
                            await character.room.send_to_room(
                                f"{character.name} looks ill from {affect.name}.",
                                exclude=[character]
                            )
            elif affect.type == AffectManager.TYPE_HOT:
                # Healing over time
                heal_amount = min(affect.value, character.max_hp - character.hp)
                character.hp += heal_amount
                _tick_event(character, affect, heal_amount, heal=True)
                if hasattr(character, 'send') and heal_amount > 0:
                    await character.send(f"You heal {heal_amount} HP from {affect.name}.")

            # Check if affect has expired
            if affect.remaining <= 0:
                affects_to_remove.append(affect)

                # Notify the character that the affect has worn off
                if hasattr(character, 'send'):
                    await character.send(f"The effect of {affect.name} wears off.")
                _wore_off(character, affect)

        # Remove expired affects (not during poison-only ticks)
        if not poison_only:
            for affect in affects_to_remove:
                AffectManager.remove_affect(character, affect)

    @staticmethod
    def has_affect(character: 'Character', affect_name: str) -> bool:
        """
        Check if a character has a specific affect.

        Args:
            character: The character to check
            affect_name: Name of the affect to look for

        Returns:
            True if the character has the affect, False otherwise
        """
        return any(affect.name == affect_name for affect in character.affects)

    @staticmethod
    def get_affect(character: 'Character', affect_name: str) -> Optional[Affect]:
        """
        Get a specific affect from a character.

        Args:
            character: The character to check
            affect_name: Name of the affect to find

        Returns:
            The Affect object if found, None otherwise
        """
        for affect in character.affects:
            if affect.name == affect_name:
                return affect
        return None

    @staticmethod
    def remove_affect_by_name(character: 'Character', affect_name: str) -> bool:
        """
        Remove a specific affect by name.

        Args:
            character: The character to remove the affect from
            affect_name: Name of the affect to remove

        Returns:
            True if an affect was removed, False otherwise
        """
        affect = AffectManager.get_affect(character, affect_name)
        if affect:
            AffectManager.remove_affect(character, affect)
            return True
        return False

    @staticmethod
    def save_affects(character: 'Character') -> List[Dict[str, Any]]:
        """
        Serialize a character's affects for saving.

        Args:
            character: The character whose affects to save

        Returns:
            List of affect dictionaries suitable for JSON serialization
        """
        affects_data = []
        for affect in character.affects:
            affects_data.append({
                'name': affect.name,
                'type': affect.type,
                'applies_to': affect.applies_to,
                'value': affect.value,
                'duration': affect.duration,
                'remaining': affect.remaining,
                'caster_level': affect.caster_level,
                'source': affect.source
            })
        return affects_data

    @staticmethod
    def load_affects(character: 'Character', affects_data: List[Dict[str, Any]]):
        """
        Load affects from saved data.

        Args:
            character: The character to load affects onto
            affects_data: List of affect dictionaries from save data
        """
        # Clear existing affects
        character.affects = []

        # Initialize affect_flags if needed
        if not hasattr(character, 'affect_flags'):
            character.affect_flags = set()

        # Load each affect
        for affect_data in affects_data:
            # Create the affect object
            affect = Affect(
                name=affect_data['name'],
                type=affect_data['type'],
                applies_to=affect_data['applies_to'],
                value=affect_data['value'],
                duration=affect_data['duration'],
                remaining=affect_data['remaining'],
                caster_level=affect_data.get('caster_level', 1),
                source=affect_data.get('source')
            )

            # Apply the affect
            if affect.type == AffectManager.TYPE_MODIFY_STAT:
                AffectManager._apply_stat_modification(character, affect)
            elif affect.type == AffectManager.TYPE_FLAG:
                AffectManager._apply_flag(character, affect)

            # Add to character's affects list
            character.affects.append(affect)

        logger.debug(f"Loaded {len(affects_data)} affects for {character.name}")

    @staticmethod
    def clear_all_affects(character: 'Character'):
        """
        Remove all affects from a character (useful for dispel magic).

        Args:
            character: The character to clear affects from
        """
        # Copy the list since we're modifying it
        for affect in character.affects[:]:
            AffectManager.remove_affect(character, affect)

        logger.debug(f"Cleared all affects from {character.name}")

    @staticmethod
    def dispel_affects(character: 'Character', dispel_level: int) -> int:
        """
        Attempt to dispel affects based on caster level.

        Args:
            character: The character to dispel affects from
            dispel_level: Level of the dispel attempt

        Returns:
            Number of affects dispelled
        """
        dispelled_count = 0

        for affect in character.affects[:]:
            # Affects with lower or equal caster level can be dispelled
            if affect.caster_level <= dispel_level:
                AffectManager.remove_affect(character, affect)
                dispelled_count += 1

        logger.debug(f"Dispelled {dispelled_count} affects from {character.name} "
                    f"(dispel level: {dispel_level})")

        return dispelled_count
