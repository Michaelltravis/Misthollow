"""
Misthollow Combat System
=======================
Handles all combat mechanics.
"""

import random
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from player import Character, Player

from config import Config

logger = logging.getLogger('Misthollow.Combat')


def cap_first(s: str) -> str:
    """A name at the start of a line: "a rotting orc ghoul" -> "A rotting orc ghoul"."""
    return s[:1].upper() + s[1:] if s else s


class CombatHandler:
    """Handles combat mechanics."""

    config = Config()

    @classmethod
    def _ng_modifier(cls, player) -> float:
        cycle = getattr(player, 'ng_plus_cycle', 0) or 0
        nightmare = getattr(player, 'nightmare_mode', False)
        if cycle <= 0:
            return 1.0
        return 1.0 + (0.15 * cycle) + (0.25 if nightmare else 0.0)

    @classmethod
    def _apply_ng_scaling(cls, npc, player):
        cycle = getattr(player, 'ng_plus_cycle', 0) or 0
        if cycle <= 0:
            return
        nightmare = getattr(player, 'nightmare_mode', False)
        if not hasattr(npc, 'ng_base_stats'):
            npc.ng_base_stats = {
                'max_hp': npc.max_hp,
                'hp': npc.hp,
                'level': npc.level,
                'armor_class': npc.armor_class,
                'hitroll': npc.hitroll,
                'damroll': npc.damroll,
            }
            npc.ng_scaled_cycle = 0
            npc.ng_scaled_nightmare = False

        if npc.ng_scaled_cycle >= cycle and npc.ng_scaled_nightmare == nightmare:
            return

        base = npc.ng_base_stats
        mult = 1.0 + (0.25 * cycle) + (0.25 if nightmare else 0.0)
        npc.max_hp = max(1, int(base['max_hp'] * mult))
        npc.hp = min(npc.max_hp, max(1, int(base['hp'] * mult)))
        npc.level = base['level'] + cycle
        npc.armor_class = base['armor_class'] - (5 * cycle)
        npc.hitroll = base['hitroll'] + (2 * cycle)
        npc.damroll = base['damroll'] + (2 * cycle)
        npc.ng_scaled_cycle = cycle
        npc.ng_scaled_nightmare = nightmare

    # ------------------------------------------------------------------
    # Fight pacing helpers (see Config "Fight pacing")
    # ------------------------------------------------------------------
    @classmethod
    def is_player(cls, ch) -> bool:
        return hasattr(ch, 'connection')

    @classmethod
    def is_boss_mob(cls, ch) -> bool:
        if cls.is_player(ch):
            return False
        return bool(getattr(ch, 'is_boss', False)) or 'boss' in getattr(ch, 'flags', set())

    @classmethod
    def stun(cls, target, rounds: int = 1) -> str:
        """A stun (bash, kidney shot, a paralysing touch, a spell): the target loses its next
        turn(s), which one_round counts down, and a creature its wind-up. A boss only staggers.
        Returns 'stun' or 'stagger'."""
        if cls.is_boss_mob(target):
            target.staggered_until = max(getattr(target, 'staggered_until', 0) or 0, time.time() + 1.5)
            return 'stagger'
        target.stunned_rounds = max(getattr(target, 'stunned_rounds', 0) or 0, max(1, int(rounds)))
        if not cls.is_player(target) and getattr(target, 'pending_intent', None):
            target.pending_intent = None
        return 'stun'

    @classmethod
    def player_toughness(cls, player) -> float:
        """Level-scaled damage reduction a player enjoys against NPC damage."""
        lvl = getattr(player, 'level', 1) or 1
        return min(cls.config.PLAYER_TOUGHNESS_CAP, lvl * cls.config.PLAYER_TOUGHNESS_PER_LEVEL)

    @classmethod
    def mitigate_incoming(cls, defender, damage: int) -> int:
        """Apply hero toughness to damage an NPC deals to a player."""
        if damage <= 0 or not cls.is_player(defender):
            return damage
        return max(1, int(round(damage * (1.0 - cls.player_toughness(defender)))))

    @classmethod
    def scale_player_weapon_damage(cls, attacker, dice_damage: int) -> int:
        """Weapon dice scale with level so a level-30 hero is not swinging a
        level-1 sword: dice x (1 + level*mult) + level//div."""
        lvl = getattr(attacker, 'level', 1) or 1
        dmg = int(dice_damage * (1.0 + lvl * cls.config.PLAYER_DAMAGE_MULT_PER_LEVEL)) \
            + int(lvl * cls.config.PLAYER_DAMAGE_FLAT_PER_LEVEL)
        # a legendary's standing '+N% damage' (procs.equip_totals)
        pct = attacker.get_equipment_bonus('damage_pct') if hasattr(attacker, 'get_equipment_bonus') else 0
        return int(dmg * (100 + pct) / 100) if pct else dmg

    @classmethod
    def crit_chance(cls, attacker) -> int:
        """Percent chance a blow lands critical: 5, +1 per 2 DEX above 10, +1 per 2 levels, +10 for
        a thief and +5 for a warrior or ranger, at most 50; spell riders (Icy Veins etc.) push past
        that, to 85. A creature's burst is telegraphed (wind-ups), not rolled: MOB_CRIT_CHANCE."""
        if not cls.is_player(attacker):
            return cls.config.MOB_CRIT_CHANCE
        chance = 5 + (getattr(attacker, 'dex', 10) - 10) // 2 + (getattr(attacker, 'level', 0) or 0) // 2
        chance += {'thief': 10, 'warrior': 5, 'ranger': 5}.get(str(getattr(attacker, 'char_class', '')).lower(), 0)
        rider = getattr(attacker, 'crit_chance', 0)
        return min(85, min(chance, 50) + max(0, rider))

    @classmethod
    def crit_mult(cls, attacker) -> float:
        """What a critical multiplies a blow by: double, a thief's 225%."""
        return 2.25 if str(getattr(attacker, 'char_class', '')).lower() == 'thief' else 2.0

    @classmethod
    def avoid_chances(cls, defender) -> dict:
        """Percent chances a defender turns a blow aside, tried in this order: dodge (a quarter of
        the skill, shield magic, what DB adds over armour, Kill or Be Killed, Slippery), parry (a
        quarter of the skill and what PB adds; wielding), shield block (three tenths of the skill;
        a shield worn) and evasion (a fifth of the skill and shield magic, at least 5)."""
        out = {'dodge': 0, 'parry': 0, 'block': 0, 'evasion': 0}
        skills = getattr(defender, 'skills', None)
        if not isinstance(skills, dict):
            return out
        equipment = getattr(defender, 'equipment', None) or {}
        shield_bonus = defender.get_shield_evasion_bonus() if hasattr(defender, 'get_shield_evasion_bonus') else 0
        dodge = int(skills.get('dodge', 0) * 0.25) + shield_bonus
        # DB weighting: shield magic + armor weight + stance should influence dodge chance
        try:
            base_db = 100 - defender.get_armor_class() if hasattr(defender, 'get_armor_class') else 0
            eff_db = defender.get_db_value() if hasattr(defender, 'get_db_value') else base_db
            dodge += max(-10, min(10, (eff_db - base_db) // 2))
        except Exception:
            pass
        try:
            from talents import TalentManager
            if TalentManager.has_talent(defender, 'kill_or_be_killed'):     # +1% per Intel point
                dodge += getattr(defender, 'intel_points', 0)
            dodge += TalentManager.get_talent_rank(defender, 'slippery')   # thief
        except Exception:
            pass
        out['dodge'] = dodge
        if equipment.get('wield'):
            parry = int(skills.get('parry', 0) * 0.25)
            try:
                # PB weighting: stance + parry/shield synergy should influence parry reliability
                base_pb = int(getattr(defender, 'damage_reduction', 0))
                eff_pb = defender.get_pb_value() if hasattr(defender, 'get_pb_value') else base_pb
                parry += max(-8, min(8, (eff_pb - base_pb)))
            except Exception:
                pass
            out['parry'] = parry
        if equipment.get('shield'):
            out['block'] = int(skills.get('shield_block', 0) * 0.3)
        evasion = skills.get('evasion', 0)
        if evasion:
            out['evasion'] = max(5, int(evasion * 0.2) + shield_bonus)
        return out

    @classmethod
    def cap_boss_swing(cls, attacker, defender, damage: int) -> int:
        """Boss fights always last several exchanges: one weapon swing never
        removes more than BOSS_SWING_CAP_PCT of a boss's max HP."""
        if not cls.is_player(attacker) or not cls.is_boss_mob(defender):
            return damage
        cap = max(1, int(getattr(defender, 'max_hp', 1) * cls.config.BOSS_SWING_CAP_PCT))
        return min(damage, cap)

    @classmethod
    def prime_poise(cls, mob):
        """Set the stagger budget for a fresh mob (mobs.py only fills it when unset)."""
        if cls.is_player(mob) or getattr(mob, 'max_poise', 0):
            return
        mob.max_poise = cls.config.POISE_BASE + (getattr(mob, 'level', 1) or 1) // cls.config.POISE_LEVEL_DIV
        mob.poise = 0

    @classmethod
    async def check_low_hp(cls, player):
        """Exactly one warning per fight when HP first drops under LOW_HP_WARN_PCT."""
        if not cls.is_player(player) or not hasattr(player, 'send'):
            return
        if getattr(player, '_low_hp_warned', False):
            return
        if player.max_hp > 0 and 0 < player.hp < player.max_hp * cls.config.LOW_HP_WARN_PCT:
            player._low_hp_warned = True
            c = cls.config.COLORS
            import msgkind   # (/play reddens the screen's edge: the line comes dimmed)
            await msgkind.send_ui(player, f"{c['bright_red']}Your health is low! Flee now, or brace for the next heavy blow.{c['reset']}")

    # Damage word -> (3rd-person verb, adjective) for grammatical hit lines:
    #   attacker:  "Your slash wounds the rat! [20 damage]"
    #   defender:  "the rat's wounding bite hits you! [20 damage]"
    DAMAGE_FORMS = {
        'miss': ('misses', 'feeble'), 'tickle': ('tickles', 'feeble'),
        'barely scratch': ('barely scratches', 'glancing'), 'scratch': ('scratches', 'light'),
        'nick': ('nicks', 'quick'), 'graze': ('grazes', 'grazing'), 'hit': ('hits', 'solid'),
        'injure': ('injures', 'painful'), 'wound': ('wounds', 'wounding'), 'maul': ('mauls', 'mauling'),
        'decimate': ('decimates', 'brutal'), 'devastate': ('devastates', 'devastating'),
        'maim': ('maims', 'maiming'), 'MUTILATE': ('MUTILATES', 'MUTILATING'),
        'DISMEMBER': ('DISMEMBERS', 'DISMEMBERING'), 'MASSACRE': ('MASSACRES', 'MASSACRING'),
        'OBLITERATE': ('OBLITERATES', 'OBLITERATING'),
        '*** ANNIHILATE ***': ('*** ANNIHILATES ***', 'ANNIHILATING'),
    }
    # weapon verb -> noun for "Your <noun> ..." lines
    WEAPON_NOUNS = {
        'hit': 'blow', 'sting': 'sting', 'whip': 'lash', 'slash': 'slash', 'bite': 'bite',
        'bludgeon': 'blow', 'crush': 'crushing blow', 'pound': 'pounding blow', 'claw': 'claw',
        'maul': 'mauling', 'thrash': 'thrashing', 'pierce': 'thrust', 'blast': 'blast',
        'punch': 'punch', 'stab': 'stab', 'slice': 'slice', 'cleave': 'cleave', 'smash': 'smash',
    }

    NPC_ATTACK_NOUNS = ('blow', 'strike', 'swing')
    RANGED_NOUNS = {'ranger': 'arrow', 'mage': 'arcane bolt', 'necromancer': 'shadow bolt'}

    @classmethod
    def damage_forms(cls, damage_word: str, you_verb: str, attacker=None) -> tuple:
        """Return (noun, 3rd-person verb, adjective) for a hit line."""
        verb, adj = cls.DAMAGE_FORMS.get(damage_word, (damage_word + 's', damage_word))
        noun = cls.WEAPON_NOUNS.get(you_verb, 'blow')
        if attacker is not None and cls.is_player(attacker):
            # combat v2: archers and casters fight from range, so their ordinary blow is a shot
            noun = cls.RANGED_NOUNS.get(str(getattr(attacker, 'char_class', '')).lower(), noun)
        if attacker is not None and not cls.is_player(attacker) and you_verb == 'hit':
            # unarmed NPCs: rotate the noun so the same line never repeats
            i = (getattr(attacker, '_hit_noun_i', -1) + 1) % len(cls.NPC_ATTACK_NOUNS)
            attacker._hit_noun_i = i
            noun = cls.NPC_ATTACK_NOUNS[i]
        return noun, verb, adj

    @classmethod
    def _rotate(cls, ch, key: str, n: int) -> int:
        """Round-robin template index per character: consecutive hit lines
        always use different phrasing (no identical line two rounds running)."""
        i = (getattr(ch, key, -1) + 1) % n
        setattr(ch, key, i)
        return i

    @classmethod
    def attacker_hit_line(cls, attacker, target_name, noun, verb, adj, tail) -> str:
        i = cls._rotate(attacker, '_hit_line_i', 3)
        if i == 0:
            return f"Your {noun} {verb} {target_name}! {tail}"
        if i == 1:
            return f"Your {noun} lands squarely and {verb} {target_name}! {tail}"
        return f"Your {noun} connects — it {verb} {target_name}! {tail}"

    @classmethod
    def defender_hit_line(cls, defender, attacker_name, noun, verb, adj, tail) -> str:
        i = cls._rotate(defender, '_taken_line_i', 3)
        if i == 0:
            return f"{attacker_name}'s {adj} {noun} hits you! {tail}"
        if i == 1:
            return f"{attacker_name}'s {noun} hits you — it {verb} you! {tail}"
        return f"{attacker_name}'s {noun} hits home, a {adj} one! {tail}"

    @classmethod
    def get_health_color(cls, health_pct: float) -> str:
        """Get color code based on health percentage."""
        c = cls.config.COLORS
        if health_pct > 75:
            return c['bright_green']
        elif health_pct > 50:
            return c['green']
        elif health_pct > 25:
            return c['yellow']
        elif health_pct > 10:
            return c['red']
        else:
            return c['bright_red']

    @classmethod
    def get_health_bar(cls, health_pct: float) -> str:
        """Get a visual health bar based on health percentage."""
        bar_length = 10
        filled = int((health_pct / 100) * bar_length)
        empty = bar_length - filled
        return f"[{'█' * filled}{'░' * empty}]"

    @classmethod
    def get_flee_chance(cls, player: 'Player') -> int:
        """Calculate flee chance for a player (0-95)."""
        dex = getattr(player, 'dex', 10)
        wil = getattr(player, 'wil', 10)
        base = 50 + (dex - 10) * 2

        # Willpower adds composure under pressure (capped so it doesn't dominate)
        base += max(-4, min(8, wil - 10))

        stance = getattr(player, 'stance', 'normal')
        if stance == 'defensive':
            base += 5
        elif stance == 'aggressive':
            base -= 5
        if getattr(player, 'move', 0) < cls.config.FLEE_MOVE_COST:
            return 0
        return max(5, min(95, base))

    @classmethod
    def get_escape_chance(cls, player: 'Player') -> int:
        """Calculate directed escape chance based on skill + dex + willpower."""
        skill = 0
        if hasattr(player, 'skills'):
            if 'escape' in player.skills:
                skill = player.skills.get('escape', 0)
            elif 'slip' in player.skills:
                skill = player.skills.get('slip', 0)

        dex = getattr(player, 'dex', 10)
        wil = getattr(player, 'wil', 10)
        wil_mod = max(-3, min(6, wil - 10))

        base = (25 + (dex - 10) + wil_mod) if skill <= 0 else (skill + (dex - 10) + wil_mod)
        if getattr(player, 'move', 0) < cls.config.ESCAPE_MOVE_COST:
            return 0
        return max(5, min(95, base))

    @classmethod
    def get_rescue_chance(cls, rescuer: 'Player', ally: 'Player' = None, attacker: 'Character' = None) -> int:
        """Calculate rescue chance based on skill, stats, and stance."""
        if hasattr(rescuer, 'get_skill_level'):
            skill = rescuer.get_skill_level('rescue')
        else:
            skill = getattr(getattr(rescuer, 'skills', {}), 'get', lambda *_: 0)('rescue', 0)
        base = skill + (getattr(rescuer, 'str', 10) - 10) * 2 + (getattr(rescuer, 'dex', 10) - 10)
        stance = getattr(rescuer, 'stance', 'normal')
        if stance == 'defensive':
            base += 6
        elif stance == 'aggressive':
            base -= 4
        if getattr(rescuer, 'move', 0) < cls.config.COMBAT_MOVE_COST:
            base -= 10
        if ally is not None and getattr(rescuer, 'protecting', None) == ally:
            base += 4
        return max(5, min(95, base))

    @classmethod
    def get_protect_chance(cls, protector: 'Player', target: 'Player' = None, attacker: 'Character' = None) -> int:
        """Calculate protection intercept chance based on skills and stats."""
        if hasattr(protector, 'get_skill_level'):
            rescue = protector.get_skill_level('rescue')
            block = protector.get_skill_level('shield_block')
        else:
            skills = getattr(protector, 'skills', {})
            rescue = skills.get('rescue', 0)
            block = skills.get('shield_block', 0)
        base = max(rescue, int(block * 0.75))
        base += (getattr(protector, 'str', 10) - 10) * 2
        base += (getattr(protector, 'con', 10) - 10) * 2
        stance = getattr(protector, 'stance', 'normal')
        if stance == 'defensive':
            base += 8
        elif stance == 'aggressive':
            base -= 4
        if getattr(protector, 'move', 0) < cls.config.FLEE_MOVE_COST:
            base -= 12
        return max(5, min(95, base))

    @classmethod
    def get_flee_risk_label(cls, chance: int) -> str:
        if chance >= 75:
            return 'low'
        if chance >= 55:
            return 'medium'
        return 'high'

    @classmethod
    def get_escape_risk_label(cls, chance: int) -> str:
        if chance >= 75:
            return 'low'
        if chance >= 55:
            return 'medium'
        return 'high'

    @classmethod
    async def call_guards_for_help(cls, guard: 'Character', attacker: 'Character'):
        """Guard calls for help - nearby guards within 3 rooms come to assist."""
        if not guard.room:
            return

        c = cls.config.COLORS

        # Announce the call for help
        await guard.room.send_to_room(
            f"{c['bright_yellow']}{guard.name} shouts 'GUARDS! HELP!'{c['reset']}"
        )

        # Find guards within 3 rooms using BFS
        from collections import deque
        visited = {guard.room.vnum}
        queue = deque([(guard.room, 0)])  # (room, distance)
        guards_to_summon = []

        while queue:
            current_room, distance = queue.popleft()

            if distance > 3:
                continue

            # Check for guards in this room (but not the original guard)
            for char in current_room.characters:
                if char == guard:
                    continue
                if not hasattr(char, 'flags'):
                    continue
                # Must be a helper guard, not already fighting, and not a player
                if 'helper' in char.flags and not char.is_fighting and not hasattr(char, 'connection'):
                    # Check if it's a guard-type mob (cityguard, guard, etc.)
                    if 'guard' in char.name.lower():
                        guards_to_summon.append((char, current_room, distance))

            # Explore adjacent rooms (only if distance < 3)
            if distance < 3:
                for direction, exit_data in current_room.exits.items():
                    if not exit_data or not exit_data.get('room'):
                        continue
                    # Don't go through closed doors
                    if 'door' in exit_data:
                        door = exit_data['door']
                        if door.get('state') == 'closed':
                            continue
                    target_room = exit_data['room']
                    if target_room.vnum not in visited:
                        visited.add(target_room.vnum)
                        queue.append((target_room, distance + 1))

        # Summon the guards (move them to the fight)
        for summoned_guard, from_room, distance in guards_to_summon:
            # Remove from old room
            if summoned_guard in from_room.characters:
                from_room.characters.remove(summoned_guard)
                await from_room.send_to_room(
                    f"{c['cyan']}{summoned_guard.name} rushes off to answer the call!{c['reset']}"
                )

            # Add to guard's room
            summoned_guard.room = guard.room
            guard.room.characters.append(summoned_guard)
            await guard.room.send_to_room(
                f"{c['bright_cyan']}{summoned_guard.name} arrives to help!{c['reset']}"
            )

            # Start combat with the attacker
            if not summoned_guard.is_fighting:
                summoned_guard.fighting = attacker
                summoned_guard.position = 'fighting'

    @classmethod
    async def start_combat(cls, attacker: 'Character', defender: 'Character', first_strike: bool = True):
        """Initiate combat between two characters (first_strike=False: an ability opens
        the fight and is the first blow, so no ordinary swing goes with it)."""
        # Safety: don't start combat with dead targets
        if not defender or defender.hp <= 0:
            return
        if not attacker or attacker.hp <= 0:
            return
        # a toll-keeper (rites.py) carries people across; no one fights him
        if 'no_attack' in (getattr(defender, 'flags', None) or []) and hasattr(attacker, 'connection'):
            c = cls.config.COLORS
            await attacker.send(f"{c['yellow']}{defender.name[:1].upper() + defender.name[1:]} does not even look at your weapon. "
                                f"Whatever power keeps the crossing keeps him too.{c['reset']}")
            return
        # a creature with helpers (population.py) calls them when a player attacks it
        if getattr(defender, 'helpers', None) and hasattr(attacker, 'connection') and not getattr(defender, 'fighting', None):
            try:
                import allies
                await allies.rally(defender, attacker)
            except Exception:
                logger.debug('rally failed', exc_info=True)

        # Auto-dismount non-combat mounts
        for combatant in (attacker, defender):
            if hasattr(combatant, 'mount') and combatant.mount:
                from mounts import MountManager
                if MountManager.should_auto_dismount(combatant):
                    mount_name = combatant.mount.name
                    combatant.mount = None
                    if hasattr(combatant, 'send'):
                        # its own colours: `c` is not set yet here (attacked on horseback, this
                        # raised and took the whole server down)
                        cc = combatant.config.COLORS
                        await combatant.send(f"{cc['yellow']}You quickly dismount from {mount_name} as combat begins!{cc['reset']}")
                        try:
                            from commands import CommandHandler
                            await CommandHandler._riding_changed(combatant)     # the 3D clients redraw the rider now
                        except Exception:
                            logger.debug('riding notify failed', exc_info=True)

        attacker.fighting = defender
        # a defender already fighting someone alive here keeps swinging at them (CircleMUD's
        # set_fighting): a second attacker no longer steals your blows mid-fight
        foe = getattr(defender, 'fighting', None)
        if not (foe is not None and foe is not attacker and getattr(foe, 'hp', 0) > 0
                and getattr(foe, 'room', None) is getattr(defender, 'room', None)):
            defender.fighting = attacker
        attacker.position = 'fighting'
        defender.position = 'fighting'
        # Auto-target when entering combat
        if hasattr(attacker, 'target') and (not attacker.target or attacker.target not in attacker.room.characters):
            attacker.target = defender
        if hasattr(defender, 'target') and (not defender.target or defender.target not in defender.room.characters):
            defender.target = attacker

        # Auto-mark for assassin Intel when entering combat
        if (getattr(attacker, 'char_class', '').lower() == 'assassin'
                and not getattr(attacker, 'intel_target', None)
                and hasattr(attacker, 'send')):
            attacker.intel_target = defender
            attacker.intel_points = 0
            attacker.intel_thresholds = {}
            c_temp = cls.config.COLORS
            await attacker.send(f"{c_temp['cyan']}You automatically mark {defender.name} for study.{c_temp['reset']}")

        # Break stealth for both combatants
        if hasattr(attacker, 'flags'):
            attacker.flags.discard('hidden')
            attacker.flags.discard('sneaking')
        if hasattr(defender, 'flags'):
            defender.flags.discard('hidden')
            defender.flags.discard('sneaking')

        c = cls.config.COLORS

        if hasattr(attacker, 'send'):
            await attacker.send(f"{c['bright_red']}You attack {defender.name}!{c['reset']}")
        if hasattr(defender, 'send'):
            await defender.send(f"\r\n{c['bright_red']}{attacker.name} attacks you!{c['reset']}")
        if attacker.room:
            await attacker.room.send_to_room(
                f"{c['red']}{attacker.name} attacks {defender.name}!{c['reset']}",
                exclude=[attacker, defender]
            )

        # First combat contextual hint about class resource
        try:
            from tips import TipManager
            if hasattr(attacker, 'connection'):
                await TipManager.show_contextual_hint(attacker, 'first_combat_resource')
        except Exception:
            pass

        # Apply NG+ scaling to NPCs facing NG+ players
        if hasattr(attacker, 'connection') and not hasattr(defender, 'connection'):
            cls._apply_ng_scaling(defender, attacker)
        if hasattr(defender, 'connection') and not hasattr(attacker, 'connection'):
            cls._apply_ng_scaling(attacker, defender)

        # Guards call for help when attacked (helper flag)
        if hasattr(defender, 'flags') and 'helper' in defender.flags:
            await cls.call_guards_for_help(defender, attacker)

        # Fight pacing: stagger budget for the mob, one low-HP warning per fight
        for ch in (attacker, defender):
            cls.prime_poise(ch)
            if cls.is_player(ch):
                ch._low_hp_warned = False
                ch._low_health_tip_shown = True   # combat owns the low-HP warning now

        # First strike
        if first_strike:
            await cls.one_round(attacker, defender)

        # a player who was just attacked hears about it at once (their 3D client targets
        # the attacker with the first blow, not a round later)
        if cls.is_player(defender):
            try:
                wm = getattr(getattr(defender, 'world', None), 'web_map', None)
                if wm:
                    await wm.notify_combat(defender)
            except Exception:
                pass

    @classmethod
    async def one_round(cls, attacker: 'Character', defender: 'Character'):
        """Process one round of combat."""
        # Safety check: if either is dead, end combat
        if not attacker.is_alive or not defender.is_alive:
            await cls.end_combat(attacker, defender)
            return

        # Safety check: if defender is None or not in world, end combat
        if defender is None:
            attacker.fighting = None
            if attacker.position == 'fighting':
                attacker.position = 'standing'
            return

        # Safety check: if defender has no room (removed from world), end combat
        if not hasattr(defender, 'room') or defender.room is None:
            attacker.fighting = None
            if attacker.position == 'fighting':
                attacker.position = 'standing'
            return

        # Safety check: if not in same room, end combat
        if attacker.room != defender.room:
            await cls.end_combat(attacker, defender)
            return

        if not attacker.is_fighting or attacker.fighting != defender:
            return

        c = cls.config.COLORS
        # what became of this swing (combat_hooks and action_combat read it): None = no turn,
        # 'skip' = the turn was lost, else miss / dodge / parry / block / hit / crit
        attacker._swing_res = 'skip'
        attacker._swing_amt = 0

        # One low-HP warning per fight (covers heavies resolved in mob_ai too)
        await cls.check_low_hp(attacker)

        # A mob whose declared heavy/aoe intent just resolved spent its round
        # on that special — no auto-attack on top (see mob_ai._resolve_intent)
        if getattr(attacker, '_skip_autoattack', False):
            attacker._skip_autoattack = False
            return

        # A slowed creature (marquee_abilities) swings only every other round or so
        if not cls.is_player(attacker) and time.time() < getattr(attacker, 'slowed_until', 0) and random.random() < 0.5:
            return

        # what a spell holds them with (spells.py affects): paralysis or fear costs the turn, a
        # charmed creature won't fight at all, slow and entanglement cost every other swing, a
        # fumble one in four
        held = getattr(attacker, 'affect_flags', None) or set()
        # a bard's discord (song_debuffs: a percent chance to fumble the swing)
        fumble = int((getattr(attacker, 'song_debuffs', None) or {}).get('fumble', 0) or 0)
        if fumble > 0 and random.randint(1, 100) <= fumble:
            attacker._swing_res = 'skip'
            return
        if held:
            cc = cls.config.COLORS
            if 'paralyzed' in held:
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{cc['yellow']}You are paralyzed and cannot move!{cc['reset']}")
                attacker._swing_res = 'skip'
                return
            if 'charmed' in held and not cls.is_player(attacker):
                attacker.fighting = None
                if attacker.position == 'fighting':
                    attacker.position = 'standing'
                return
            if 'feared' in held:
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{cc['yellow']}You are too terrified to strike!{cc['reset']}")
                attacker._swing_res = 'skip'
                return
            if ('slow' in held or 'entangled' in held) and random.random() < 0.5:
                attacker._swing_res = 'skip'
                return
            if 'fumble' in held and random.random() < 0.25:
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{cc['yellow']}You fumble your attack!{cc['reset']}")
                attacker._swing_res = 'skip'
                return

        # A sidestepping player spent the round entirely on evasion
        if getattr(attacker, 'sidestep_skip_attack', False):
            attacker.sidestep_skip_attack = False
            if hasattr(attacker, 'send'):
                await attacker.send(f"{c['cyan']}You are focused entirely on evasion this round!{c['reset']}")
            return

        # Combat movement cost (fatigue)
        fatigue_penalty = 0
        if hasattr(attacker, 'connection'):
            move_cost = cls.config.COMBAT_MOVE_COST
            if move_cost > 0:
                attacker.move = max(0, attacker.move - move_cost)
            if attacker.move <= 0:
                fatigue_penalty = cls.config.COMBAT_FATIGUE_HIT_PENALTY
                last_notice = getattr(attacker, '_winded_notice_until', 0)
                if time.time() > last_notice:
                    attacker._winded_notice_until = time.time() + 8
                    if hasattr(attacker, 'send'):
                        await attacker.send(f"{c['yellow']}You're winded and your attacks slow!{c['reset']}")

        # Auto-combat skills/spells
        if hasattr(attacker, 'autocombat') and attacker.autocombat:
            await cls.auto_combat(attacker)

        # Stun check: stunned attackers skip their turn (Unstoppable immune)
        if getattr(attacker, 'stunned_rounds', 0) > 0:
            if getattr(attacker, 'unstoppable_rounds', 0) > 0:
                attacker.stunned_rounds = 0
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{c['bright_yellow']}★ Unstoppable! You resist the stun! ★{c['reset']}")
            else:
                attacker.stunned_rounds -= 1
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{c['yellow']}You are stunned and cannot attack!{c['reset']}")
                return

        # Blind check: blinded attackers have 50% miss chance
        blinded = getattr(attacker, 'blinded_rounds', 0) > 0
        if blinded:
            attacker.blinded_rounds -= 1
            if attacker.blinded_rounds <= 0:
                attacker.blinded_until = 0
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{c['green']}Your vision clears!{c['reset']}")

        # Marked man: target takes 10% more damage
        marked_man_bonus = 1.0
        if getattr(defender, 'marked_man_until', 0) > time.time():
            marked_man_bonus = 1.10

        # Thief rigged dice: consume guaranteed crit
        force_crit = False
        if getattr(attacker, 'rigged_dice_hits', 0) > 0:
            force_crit = True
            attacker.rigged_dice_hits -= 1

        # Bone shield check on defender
        if getattr(defender, 'bone_shield_charges', 0) > 0 and time.time() < getattr(defender, 'bone_shield_until', 0):
            # Will be checked after damage calc
            pass

        # Calculate hits
        hit_roll = random.randint(1, 20) + attacker.get_hit_bonus()
        if cls.is_player(attacker):
            hit_roll += (getattr(attacker, 'level', 1) or 1) // cls.config.PLAYER_LEVEL_HIT_DIV
        if fatigue_penalty:
            hit_roll -= fatigue_penalty
        if blinded:
            if random.randint(1, 100) <= 50:
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{c['yellow']}You swing blindly and miss!{c['reset']}")
                if hasattr(defender, 'send'):
                    await defender.send(f"{c['cyan']}{attacker.name} swings blindly!{c['reset']}")
                attacker._swing_res = 'miss'
                return

        # Defensive skills (dodge/parry/shield block/blur)
        now = time.time()
        # Blur reduces hit chance
        if getattr(defender, 'blur_until', 0) > now:
            hit_roll -= 2
        # Feint debuff on defender
        if getattr(defender, 'ai_state', {}).get('feinted_until', 0) > now and getattr(defender.ai_state, 'feinted_by', None) == attacker:
            hit_roll += 2

        # Weather visibility penalty (outdoors only)
        outdoor_sectors = {
            'field', 'forest', 'hills', 'mountain', 'water_swim', 'water_noswim',
            'flying', 'desert', 'swamp'
        }
        if attacker.room and attacker.room.zone and attacker.room.sector_type in outdoor_sectors:
            weather = attacker.room.zone.weather
            if weather:
                vision_mod = weather.get_vision_modifier()
                if vision_mod < 1.0:
                    hit_roll -= int((1.0 - vision_mod) * 6)

            # World event fog penalty
            try:
                world = getattr(attacker, 'world', None)
                if world and hasattr(world, 'event_manager') and world.event_manager:
                    hit_roll -= world.event_manager.get_fog_accuracy_penalty()
            except Exception:
                pass

        # Lower AC = better armor = harder to hit (higher defense)
        defense = 10 - (defender.get_armor_class() // 10)

        # Ghost passive: 50% dodge after big hit
        if getattr(defender, 'ghost_dodge_until', 0) > time.time():
            if random.randint(1, 100) <= 50:
                if hasattr(defender, 'send'):
                    await defender.send(f"{c['cyan']}Your ghostly reflexes let you dodge!{c['reset']}")
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{c['yellow']}{defender.name} dodges like a ghost!{c['reset']}")
                attacker._swing_res = 'dodge'
                return

        # Assassin Evasion (100% dodge)
        now = time.time()
        if getattr(defender, 'evasion_until', 0) > now:
            if hasattr(defender, 'send'):
                await defender.send(f"{c['cyan']}You effortlessly evade {attacker.name}'s attack!{c['reset']}")
            if hasattr(attacker, 'send'):
                await attacker.send(f"{c['yellow']}{defender.name} is untouchable!{c['reset']}")
            attacker._swing_res = 'dodge'
            return

        # Illusions and phasing (spells.py: Tower Echoes / mirror image, Phase Step /
        # displacement, Stepwise / blink): some blows find only an image or empty air
        dflags = getattr(defender, 'affect_flags', None) or set()
        veil = (25 if 'mirror_image' in dflags else 0) + (15 if 'displacement' in dflags else 0) + (20 if 'blink' in dflags else 0)
        if veil and random.randint(1, 100) <= min(40, veil):     # stacked, never more than two in five
            if hasattr(defender, 'send'):
                await defender.send(f"{c['cyan']}{attacker.name}'s blow strikes only an image of you!{c['reset']}")
            if hasattr(attacker, 'send'):
                await attacker.send(f"{c['yellow']}Your blow passes through an image of {defender.name}!{c['reset']}")
            attacker._swing_res = 'dodge'
            return

        # Shadow Step dodge (one-time)
        if getattr(defender, 'shadowstep_dodge', False):
            defender.shadowstep_dodge = False
            if hasattr(defender, 'send'):
                await defender.send(f"{c['cyan']}You dodge the attack from the shadows!{c['reset']}")
            if hasattr(attacker, 'send'):
                await attacker.send(f"{c['yellow']}{defender.name} dodges from the shadows!{c['reset']}")
            attacker._swing_res = 'dodge'
            return

        # Avoidance checks
        if hasattr(defender, 'skills'):
            # passives work a fraction of their proficiency (dodge 50% -> 12%, mastered 85% -> 21%)
            # and grow a little each time they work (mastery.py); avoid_chances has the sums
            import mastery
            avoid = cls.avoid_chances(defender)
            dodge = avoid['dodge']
            if dodge and random.randint(1, 100) <= dodge:
                await mastery.improve(defender, 'dodge', rate=0.25)
                if hasattr(defender, 'send'):
                    await defender.send(f"{c['cyan']}You dodge {attacker.name}'s attack!{c['reset']}")
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{c['yellow']}{defender.name} dodges your attack!{c['reset']}")
                # Ranger Focus gain on dodge (+15)
                if hasattr(defender, 'focus') and getattr(defender, 'char_class', '').lower() == 'ranger':
                    old_focus = defender.focus
                    defender.focus = min(100, defender.focus + 15)
                    if defender.focus > old_focus and hasattr(defender, 'send'):
                        await defender.send(f"{c['bright_green']}[Focus: {defender.focus}/100]{c['reset']}")

                # Thief luck on dodge
                if hasattr(defender, 'luck_points') and getattr(defender, 'char_class', '').lower() == 'thief':
                    gain = 1
                    try:
                        from talents import TalentManager
                        gain += TalentManager.get_talent_rank(defender, 'fortune_favors')
                    except Exception:
                        pass
                    if defender.luck_points < 10:
                        defender.luck_points = min(10, defender.luck_points + gain)
                        if hasattr(defender, 'send'):
                            await defender.send(f"{c['bright_yellow']}[Luck: {defender.luck_points}/10]{c['reset']}")
                    # Luck counterattack: dodge + luck >= 5 = free hit
                    if defender.luck_points >= 5:
                        weapon = defender.equipment.get('wield') if hasattr(defender, 'equipment') else None
                        if weapon and hasattr(weapon, 'damage_dice'):
                            counter_dmg = cls.roll_dice(weapon.damage_dice) + defender.get_damage_bonus()
                        else:
                            counter_dmg = random.randint(1, 6) + defender.get_damage_bonus()
                        counter_dmg = max(1, counter_dmg)
                        if hasattr(defender, 'send'):
                            await defender.send(f"{c['bright_green']}Lucky counterattack! [{counter_dmg}]{c['reset']}")
                        if hasattr(attacker, 'send'):
                            await attacker.send(f"{c['red']}{defender.name} counters! [{counter_dmg}]{c['reset']}")
                        await attacker.take_damage(counter_dmg, defender)
                attacker._swing_res = 'dodge'
                return
            parry = avoid['parry']
            if parry and random.randint(1, 100) <= parry:
                await mastery.improve(defender, 'parry', rate=0.25)
                if hasattr(defender, 'send'):
                    await defender.send(f"{c['cyan']}You parry {attacker.name}'s attack!{c['reset']}")
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{c['yellow']}{defender.name} parries your attack!{c['reset']}")
                # Thief luck on parry
                if hasattr(defender, 'luck_points') and getattr(defender, 'char_class', '').lower() == 'thief':
                    if defender.luck_points < 10:
                        defender.luck_points = min(10, defender.luck_points + 1)
                        if hasattr(defender, 'send'):
                            await defender.send(f"{c['bright_yellow']}[Luck: {defender.luck_points}/10]{c['reset']}")
                attacker._swing_res = 'parry'
                return
            sblock = avoid['block']
            if sblock and random.randint(1, 100) <= sblock:
                await mastery.improve(defender, 'shield_block', rate=0.25)
                if hasattr(defender, 'send'):
                    await defender.send(f"{c['cyan']}You block the attack with your shield!{c['reset']}")
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{c['yellow']}{defender.name} blocks your attack!{c['reset']}")
                attacker._swing_res = 'block'
                return
            # Evasion (chance to avoid entirely)
            if avoid['evasion'] and random.randint(1, 100) <= avoid['evasion']:
                await mastery.improve(defender, 'evasion', rate=0.25)
                if hasattr(defender, 'send'):
                    await defender.send(f"{c['cyan']}You evade the attack!{c['reset']}")
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{c['yellow']}{defender.name} evades your attack!{c['reset']}")
                attacker._swing_res = 'dodge'
                return

        if hit_roll >= defense:
            # Calculate damage
            weapon = attacker.equipment.get('wield') if hasattr(attacker, 'equipment') else None

            if weapon and hasattr(weapon, 'damage_dice'):
                damage = cls.roll_dice(weapon.damage_dice)
            else:
                # Bare hands
                damage = random.randint(1, 3)

            # Hero scaling: weapon dice grow with level (pacing)
            if cls.is_player(attacker):
                damage = cls.scale_player_weapon_damage(attacker, damage)

            damage += attacker.get_damage_bonus()

            # A mob mid wind-up is gathering itself: its auto-swing is lighter
            if not cls.is_player(attacker) and getattr(attacker, 'pending_intent', None):
                damage = max(1, int(damage * cls.config.MOB_WINDUP_AUTOATTACK_MULT))

            # PERFECT STRIKE: the player timed cmd_swing to the round's sweet
            # spot — this swing lands +30% and chips double poise (the
            # _poise_bonus_hit flag is consumed in Mobile.take_damage)
            perfect_hit = False
            if getattr(attacker, 'perfect_next', False):
                attacker.perfect_next = False
                attacker._poise_bonus_hit = True
                perfect_hit = True
                damage = int(damage * 1.3)

            if fatigue_penalty:
                damage = max(1, int(damage * (1.0 - cls.config.COMBAT_FATIGUE_DAMAGE_PENALTY)))

            # Warrior stance modifiers removed — warriors now use Combo Chain system

            # Apply talent passive bonuses
            if hasattr(attacker, 'talents') and attacker.talents:
                try:
                    from talents import TalentManager
                    talent_dmg_bonus = TalentManager.get_talent_bonus(attacker, 'damage_mod')
                    if talent_dmg_bonus > 0:
                        damage = int(damage * (1 + talent_dmg_bonus / 100))
                except Exception:
                    pass

            # Warrior Momentum damage bonus (+5% per point)
            if getattr(attacker, 'char_class', '').lower() == 'warrior' and getattr(attacker, 'momentum', 0) > 0:
                mom_mult = 1.0 + getattr(attacker, 'momentum', 0) * 0.05
                damage = int(damage * mom_mult)

            # Warrior damage buff (from rally evolutions)
            if getattr(attacker, 'warrior_dmg_bonus', 0) > 0 and getattr(attacker, 'warrior_dmg_bonus_rounds', 0) > 0:
                damage = int(damage * (1 + attacker.warrior_dmg_bonus))

            # Berserker momentum lifesteal
            if getattr(attacker, 'war_doctrine', None) == 'berserker' and getattr(attacker, 'momentum', 0) > 0:
                lifesteal_pct = getattr(attacker, 'momentum', 0) * 0.02
                heal = int(damage * lifesteal_pct)
                if heal > 0:
                    attacker.hp = min(attacker.max_hp, attacker.hp + heal)

            # Boss enrage bonus
            if getattr(attacker, 'is_boss', False) and getattr(attacker, 'ai_state', None):
                if attacker.ai_state.get('enraged'):
                    enrage_mult = getattr(attacker, 'enrage_multiplier', 1.5)
                    damage = int(damage * enrage_mult)

            # Boss vulnerability window
            if getattr(defender, 'is_boss', False):
                vulnerable_until = getattr(defender, 'ai_state', {}).get('vulnerable_until', 0)
                if time.time() < vulnerable_until:
                    damage = int(damage * 1.5)

            # NG+ enemy damage scaling
            if not hasattr(attacker, 'connection') and hasattr(defender, 'connection'):
                damage = int(damage * cls._ng_modifier(defender))

            # Pack flanking + ambush openers (NPC attackers; helpers self-guard)
            if not hasattr(attacker, 'connection'):
                try:
                    from mob_ai import pack_bonus, consume_ambush
                    flank = pack_bonus(attacker, defender)
                    if flank > 1.0:
                        damage = int(damage * flank)
                    amb = consume_ambush(attacker)
                    if amb > 1.0:
                        damage = int(damage * amb)
                        if attacker.room:
                            await attacker.room.send_to_room(
                                f"{c['bright_red']}🗡 {attacker.name} strikes from AMBUSH!{c['reset']}")
                except Exception:
                    pass

            # Sleeping targets take more damage
            if getattr(defender, 'position', '') == 'sleeping':
                damage = int(damage * 1.5)

            # Vendetta bonus (assassin ability - doubles all damage to target)
            vendetta_attacker = getattr(defender, 'vendetta_target', None)
            if vendetta_attacker and vendetta_attacker == attacker:
                bonus_pct = getattr(defender, 'vendetta_bonus', 100)
                damage = int(damage * (1 + bonus_pct / 100))

            # Basic vendetta (non-assassin version)
            if getattr(defender, 'vendetta_from', None) == attacker:
                damage = int(damage * 1.3)

            damage = max(1, damage)

            # Evasion/tumble mitigation
            if hasattr(defender, 'skills'):
                evasion = defender.skills.get('evasion', 0)
                if evasion and random.randint(1, 100) <= evasion:
                    damage = int(damage * 0.7)
            if getattr(defender, 'tumble_until', 0) > time.time():
                damage = int(damage * 0.8)

            # Assassin Feint: attacker's target takes 30% less damage
            if getattr(defender, 'feint_until', 0) > time.time() and getattr(defender, 'feint_reduction', 0) > 0:
                damage = int(damage * (1 - defender.feint_reduction))

            # Deadly Patience: Intel >= 6 grants 15% DR
            try:
                from talents import TalentManager
                if TalentManager.has_talent(defender, 'deadly_patience') and getattr(defender, 'intel_points', 0) >= 6:
                    damage = int(damage * 0.85)
            except Exception:
                pass

            # Numbing Toxin: poisoned targets deal less damage
            try:
                from talents import TalentManager
                if hasattr(defender, 'char_class') and defender.char_class.lower() == 'assassin':
                    pass  # defender is assassin, check if ATTACKER is poisoned
                nt_rank = TalentManager.get_talent_rank(defender, 'numbing_toxin')
                if nt_rank > 0:
                    # Check if attacker is poisoned
                    attacker_poisoned = False
                    if hasattr(attacker, 'affects'):
                        for aff in attacker.affects:
                            aff_name = getattr(aff, 'name', '') if hasattr(aff, 'name') else aff.get('name', '') if isinstance(aff, dict) else ''
                            if 'poison' in aff_name.lower():
                                attacker_poisoned = True
                                break
                    if attacker_poisoned:
                        reductions = {1: 0.03, 2: 0.06, 3: 0.10}
                        damage = int(damage * (1 - reductions.get(nt_rank, 0.10)))
            except Exception:
                pass

            # Expose Weakness: target takes 15% more damage from this player
            if hasattr(attacker, 'expose_target') and attacker.expose_target == defender:
                if getattr(attacker, 'expose_until', 0) > time.time():
                    damage = int(damage * 1.15)

            damage = max(1, damage)

            # Critical hit check - percentage based
            # Base 5% + 1% per 2 DEX above 10 + 0.5% per level
            # Critical hit check - percentage based (crit_chance has the sums)
            is_crit = force_crit or (random.randint(1, 100) <= cls.crit_chance(attacker))
            if is_crit:
                damage = int(damage * cls.crit_mult(attacker))
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{c['bright_yellow']}*** CRITICAL HIT! ***{c['reset']}")

            # Apply marked_man bonus (thief low blow talent)
            damage = int(damage * marked_man_bonus)

            # Bone shield absorption (necromancer)
            if getattr(defender, 'bone_shield_charges', 0) > 0 and time.time() < getattr(defender, 'bone_shield_until', 0):
                absorb_max = getattr(defender, 'bone_shield_absorb', 500)
                absorbed = min(damage, absorb_max)
                damage -= absorbed
                defender.bone_shield_charges -= 1
                if hasattr(defender, 'send'):
                    await defender.send(f"{c['cyan']}Bone Shield absorbs {absorbed} damage! ({defender.bone_shield_charges} charges left){c['reset']}")
                if defender.bone_shield_charges <= 0:
                    defender.bone_shield_until = 0
                    if hasattr(defender, 'send'):
                        await defender.send(f"{c['yellow']}Your Bone Shield shatters!{c['reset']}")
                if damage <= 0:
                    if hasattr(attacker, 'send'):
                        await attacker.send(f"{c['yellow']}{defender.name}'s bone shield absorbs the blow!{c['reset']}")
                    attacker._swing_res = 'block'
                    return
            damage = max(1, damage)

            # Pacing: boss swing cap, hero toughness vs NPC hits
            damage = cls.cap_boss_swing(attacker, defender, damage)
            if not cls.is_player(attacker):
                damage = cls.mitigate_incoming(defender, damage)
            attacker._swing_res = 'crit' if is_crit else 'hit'
            attacker._swing_amt = damage

            # Heavy hits and crits chip double poise (consumed in Mobile.take_damage)
            exploiting_stagger = False
            if cls.is_player(attacker) and not cls.is_player(defender):
                if is_crit or damage >= getattr(defender, 'max_hp', 1) * cls.config.POISE_HEAVY_HIT_PCT:
                    attacker._poise_bonus_hit = True
                exploiting_stagger = time.time() < getattr(defender, 'staggered_until', 0)

            damage_word = cls.get_damage_word(damage)
            damage_color = cls.get_damage_color(damage)

            # Get weapon verb
            weapon_type = 'hit'
            if weapon and hasattr(weapon, 'weapon_type'):
                weapon_type = weapon.weapon_type
            you_verb, they_verb = cls.get_weapon_verb(weapon_type)
            hit_noun, hit_verb, hit_adj = cls.damage_forms(damage_word, you_verb, attacker)

            # Send messages with enhanced formatting
            # Build Intel suffix for assassins with marked targets
            intel_suffix = ""
            if (hasattr(attacker, 'intel_target') and attacker.intel_target == defender
                    and getattr(attacker, 'char_class', '').lower() == 'assassin'):
                intel_pts = getattr(attacker, 'intel_points', 0)
                intel_suffix = f" {c['cyan']}(Intel: {intel_pts}/10){c['reset']}"

            if hasattr(attacker, 'send'):
                if perfect_hit:
                    await attacker.send(f"{c['bright_yellow']}★ PERFECT STRIKE!{c['reset']}")
                if exploiting_stagger:
                    await attacker.send(f"{c['bright_yellow']}You press the opening while {defender.name} reels — wide open!{c['reset']}")
                if getattr(attacker, 'compact_mode', False):
                    await attacker.send(f"{c['green']}You {you_verb} {defender.name}. {damage_color}[{damage}]{c['reset']}{intel_suffix}")
                else:
                    line = cls.attacker_hit_line(attacker, defender.name, hit_noun, hit_verb, hit_adj,
                                                 f"{damage_color}[{damage} damage]")
                    await attacker.send(f"{c['green']}{line}{c['reset']}{intel_suffix}")
            if hasattr(defender, 'send'):
                if getattr(defender, 'compact_mode', False):
                    await defender.send(f"{c['red']}{attacker.name} {they_verb} you. {damage_color}[{damage}]{c['reset']}")
                else:
                    line = cls.defender_hit_line(defender, attacker.name, hit_noun, hit_verb, hit_adj,
                                                 f"{damage_color}[{damage} damage]")
                    await defender.send(f"{c['red']}{line}{c['reset']}")

            # Bystander message
            try:
                if attacker.room:
                    bystander_msg = f"{c['white']}{attacker.name} {they_verb} {defender.name}.{c['reset']}"
                    await attacker.room.send_to_room(
                        bystander_msg,
                        exclude=[attacker, defender]
                    )
                    # Arena spectator broadcast
                    try:
                        from arena import ArenaManager
                        await ArenaManager.handle_arena_combat_message(attacker, defender, bystander_msg)
                    except Exception:
                        pass
            except Exception:
                pass

            # Path system: lone wolf DR / fellowship coordination, then lifesteal
            try:
                from paths import PathManager
                damage = PathManager.modify_damage(attacker, defender, damage)
            except Exception:
                pass

            # Apply damage (flagged as a weapon auto-swing: a raised GUARD only
            # blunts these — class abilities and spells punch through)
            attacker._weapon_swing = True
            killed = await defender.take_damage(damage, attacker)
            attacker._weapon_swing = False
            try:
                from paths import PathManager
                await PathManager.after_damage(attacker, defender, damage)
            except Exception:
                pass

            # Assassin Intel accumulation on hit
            if not killed and hasattr(attacker, 'intel_target') and attacker.intel_target == defender:
                if getattr(attacker, 'char_class', '').lower() == 'assassin':
                    intel_gain = 1
                    old_intel = attacker.intel_points
                    attacker.intel_points = min(10, attacker.intel_points + intel_gain)
                    if attacker.intel_points > old_intel and hasattr(attacker, 'send'):
                        await attacker.send(f"{c['cyan']}[Intel: {attacker.intel_points}/10]{c['reset']}")
                        # Threshold messages
                        thresholds = getattr(attacker, 'intel_thresholds', {})
                        tname = defender.name
                        if attacker.intel_points >= 3 and not thresholds.get(3):
                            thresholds[3] = True
                            await attacker.send(f"{c['bright_green']}You spot an opening in {tname}'s defenses! [Expose Weakness unlocked]{c['reset']}")
                        if attacker.intel_points >= 6 and not thresholds.get(6):
                            thresholds[6] = True
                            await attacker.send(f"{c['bright_yellow']}You've mapped {tname}'s vital points! [Vital Strike unlocked]{c['reset']}")
                        if attacker.intel_points >= 10 and not thresholds.get(10):
                            thresholds[10] = True
                            await attacker.send(f"{c['bright_red']}You know exactly how to kill {tname}. [Execute Contract unlocked]{c['reset']}")
                        attacker.intel_thresholds = thresholds

            # Ghost passive: big hit triggers 50% dodge
            if not killed and hasattr(defender, 'char_class') and defender.char_class.lower() == 'assassin':
                try:
                    from talents import TalentManager
                    if TalentManager.has_talent(defender, 'ghost') and damage > defender.max_hp * 0.2:
                        defender.ghost_dodge_until = time.time() + 4  # ~1 round
                        if hasattr(defender, 'send'):
                            await defender.send(f"{c['cyan']}Ghost triggers! 50% dodge for 1 round.{c['reset']}")
                except Exception:
                    pass

            # Decrement vendetta ticks
            if getattr(defender, 'vendetta_ticks', 0) > 0:
                defender.vendetta_ticks -= 1
                if defender.vendetta_ticks <= 0:
                    defender.vendetta_target = None
                    defender.vendetta_bonus = 0
                    defender.vendetta_from = None
                    if hasattr(attacker, 'send'):
                        c = attacker.config.COLORS
                        await attacker.send(f"{c['yellow']}Your Vendetta has expired.{c['reset']}")

            # Add grudge for hunting AI (mob remembers who attacked them)
            if hasattr(defender, 'add_grudge') and hasattr(attacker, 'connection'):
                # Defender is a mob, attacker is a player
                defender.add_grudge(attacker, damage)

            # Thief Luck generation on hit
            if hasattr(attacker, 'luck_points') and hasattr(attacker, 'char_class'):
                if attacker.char_class.lower() == 'thief':
                    luck_chance = 15
                    try:
                        from talents import TalentManager
                        luck_chance += TalentManager.get_talent_rank(attacker, 'lucky_strikes') * 3
                        # Hot streak: consecutive luck gains increase chance
                        hs_rank = TalentManager.get_talent_rank(attacker, 'hot_streak')
                        luck_chance += getattr(attacker, 'luck_streak', 0) * hs_rank * 2
                    except Exception:
                        pass
                    gained_luck = False
                    if is_crit:
                        # Crits always grant luck
                        gain = 1
                        try:
                            from talents import TalentManager
                            if TalentManager.has_talent(attacker, 'loaded_dice'):
                                gain = 2
                        except Exception:
                            pass
                        if attacker.luck_points < 10:
                            attacker.luck_points = min(10, attacker.luck_points + gain)
                            gained_luck = True
                    elif random.randint(1, 100) <= luck_chance:
                        if attacker.luck_points < 10:
                            attacker.luck_points = min(10, attacker.luck_points + 1)
                            gained_luck = True
                    if gained_luck:
                        attacker.luck_streak = getattr(attacker, 'luck_streak', 0) + 1
                        if hasattr(attacker, 'send'):
                            await attacker.send(f"{c['bright_yellow']}[Luck: {attacker.luck_points}/10]{c['reset']}")
                        # Lucky break: at 10, next hit is auto-crit
                        try:
                            from talents import TalentManager
                            if attacker.luck_points >= 10 and TalentManager.has_talent(attacker, 'lucky_break'):
                                attacker.rigged_dice_hits = max(getattr(attacker, 'rigged_dice_hits', 0), 1)
                        except Exception:
                            pass
                    else:
                        attacker.luck_streak = 0
                    # Rigged dice guaranteed crits (consume)
                    # (handled above in crit section... we'll hook it in crit calc)

            # Paladin Holy Power generation on hit
            if hasattr(attacker, 'holy_power') and hasattr(attacker, 'char_class'):
                if attacker.char_class.lower() == 'paladin':
                    hp_chance = 30
                    try:
                        from talents import TalentManager
                        hp_chance += TalentManager.get_talent_rank(attacker, 'benediction') * 3
                    except Exception:
                        pass
                    if getattr(attacker, 'active_oath', None) == 'vengeance':
                        hp_chance += 10
                    elif getattr(attacker, 'active_oath', None) == 'justice':
                        hp_chance += 5
                    if random.randint(1, 100) <= hp_chance and attacker.holy_power < 5:
                        attacker.holy_power = min(5, attacker.holy_power + 1)
                        if hasattr(attacker, 'send'):
                            await attacker.send(f"{c['bright_yellow']}[Holy Power: {attacker.holy_power}/5]{c['reset']}")

            # Cleric Faith generation (shadow form: damage builds faith)
            if hasattr(attacker, 'faith') and hasattr(attacker, 'char_class'):
                if attacker.char_class.lower() == 'cleric' and getattr(attacker, 'shadow_form', False):
                    if attacker.faith < 10:
                        attacker.faith = min(10, attacker.faith + 1)
                        if hasattr(attacker, 'send'):
                            await attacker.send(f"{c['bright_magenta']}[Faith: {attacker.faith}/10]{c['reset']}")

            # Warrior rage generation removed — warriors now use Combo Chain system
            # (rage attribute kept for save compatibility but unused)

            # Ranger focus generation on hit
            if hasattr(attacker, 'focus') and hasattr(attacker, 'char_class'):
                if attacker.char_class.lower() == 'ranger':
                    focus_gain = 8
                    # Bonus focus on marked target
                    if getattr(attacker, 'hunters_mark_target', None) == defender:
                        focus_gain += 5
                    # Talent: master_marksman
                    try:
                        from talents import TalentManager
                        focus_gain += TalentManager.get_talent_rank(attacker, 'master_marksman') * 2
                    except Exception:
                        pass
                    old_focus = attacker.focus
                    attacker.focus = min(100, attacker.focus + focus_gain)
                    for threshold in [25, 50, 75, 100]:
                        if old_focus < threshold <= attacker.focus:
                            if hasattr(attacker, 'send'):
                                await attacker.send(f"{c['bright_green']}[Focus: {attacker.focus}/100]{c['reset']}")
                            break

            # Bard inspiration generation on hit (33% chance)
            if hasattr(attacker, 'inspiration') and hasattr(attacker, 'char_class'):
                if attacker.char_class.lower() == 'bard':
                    if random.randint(1, 100) <= 33 and attacker.inspiration < 10:
                        attacker.inspiration = min(10, attacker.inspiration + 1)
                        if hasattr(attacker, 'send'):
                            await attacker.send(f"{c['bright_yellow']}[Inspiration: {attacker.inspiration}/10]{c['reset']}")

            # Necromancer Soul Shard generation on hit (15% chance)
            if hasattr(attacker, 'soul_shards') and hasattr(attacker, 'char_class'):
                if attacker.char_class.lower() == 'necromancer':
                    if random.randint(1, 100) <= 15 and attacker.soul_shards < 10:
                        attacker.soul_shards = min(10, attacker.soul_shards + 1)
                        if hasattr(attacker, 'send'):
                            await attacker.send(f"{c['bright_magenta']}[Soul Shards: {attacker.soul_shards}/10]{c['reset']}")

            # Thief combo point generation on hit
            if hasattr(attacker, 'combo_points') and hasattr(attacker, 'char_class'):
                if attacker.char_class.lower() == 'thief':
                    if attacker.combo_target != defender:
                        attacker.combo_points = 0  # Reset if switching targets
                        attacker.combo_target = defender
                    if attacker.combo_points < 5:
                        attacker.combo_points += 1

            # what the gear does by itself (procs.py): on every weapon blow that lands
            if not killed:
                import procs
                await procs.on_hit(attacker, defender, weapon)
                killed = getattr(defender, 'hp', 0) <= 0

            # Apply poison effects from envenomed weapon
            if not killed and weapon and hasattr(weapon, 'envenomed') and weapon.envenomed:
                await cls.apply_poison_effect(attacker, defender, weapon)

            # Show defender health to attacker (if attacker is a player)
            if hasattr(attacker, 'send') and not killed and not getattr(attacker, 'compact_mode', False):
                health_pct = (defender.hp / defender.max_hp) * 100
                health_color = cls.get_health_color(health_pct)
                health_bar = cls.get_health_bar(health_pct)
                await attacker.send(f"{c['cyan']}{defender.name} {health_color}{health_bar} [{defender.hp}/{defender.max_hp}]{c['reset']}")

            if killed:
                await cls.handle_death(attacker, defender)
        else:
            attacker._swing_res = 'miss'
            # Miss - with variety
            miss_messages_attacker = [
                f"You miss {defender.name}.",
                f"Your attack misses {defender.name}.",
                f"{defender.name} dodges your attack!",
                f"You swing at {defender.name} but miss!",
                f"Your attack goes wide!",
            ]
            miss_messages_defender = [
                f"{attacker.name} misses you.",
                f"You dodge {attacker.name}'s attack!",
                f"{attacker.name}'s attack goes wide!",
                f"You sidestep {attacker.name}'s strike!",
                f"{attacker.name} swings and misses!",
            ]
            if hasattr(attacker, 'send'):
                await attacker.send(f"{c['yellow']}{random.choice(miss_messages_attacker)}{c['reset']}")
            if hasattr(defender, 'send'):
                if getattr(defender, 'compact_mode', False):
                    await defender.send(f"{c['cyan']}{attacker.name} misses.{c['reset']}")
                else:
                    await defender.send(f"{c['cyan']}{random.choice(miss_messages_defender)}{c['reset']}")

            # Bystander miss message
            try:
                if attacker.room:
                    await attacker.room.send_to_room(
                        f"{c['white']}{attacker.name} misses {defender.name}.{c['reset']}",
                        exclude=[attacker, defender]
                    )
            except Exception:
                pass

        # Extra swings: a share of their proficiency (second attack 50% -> 30% of rounds), and
        # they grow a little each time they come (mastery.py)
        import mastery
        if hasattr(attacker, 'skills') and 'second_attack' in attacker.skills:
            if random.randint(1, 100) <= int(attacker.skills['second_attack'] * 0.6):
                await mastery.improve(attacker, 'second_attack', rate=0.25)
                await cls.bonus_attack(attacker, defender)

        if hasattr(attacker, 'skills') and 'third_attack' in attacker.skills:
            if random.randint(1, 100) <= int(attacker.skills['third_attack'] * 0.3):
                await mastery.improve(attacker, 'third_attack', rate=0.25)
                await cls.bonus_attack(attacker, defender)

        if hasattr(attacker, 'skills') and 'dual_wield' in attacker.skills:
            if attacker.equipment.get('dual_wield') and random.randint(1, 100) <= int(attacker.skills['dual_wield'] * 0.6):
                await mastery.improve(attacker, 'dual_wield', rate=0.25)
                await cls.offhand_attack(attacker, defender)

        # haste (Quicken, Rimeheart, a song, or worn gear that quickens): an extra swing about
        # every other round
        hasted = 'haste' in (getattr(attacker, 'affect_flags', None) or set()) or (
            hasattr(attacker, 'gear_hasted') and attacker.gear_hasted())
        if hasted and defender.is_alive and random.random() < 0.5:
            await cls.bonus_attack(attacker, defender)

        # Titan's Wrath (the warrior's capstone): every swing cleaves through the foes around them
        if time.time() < getattr(attacker, 'titans_wrath_until', 0):
            from spells import SpellHandler
            for other in SpellHandler.foes_in_room(attacker):
                if other is not defender and other.is_alive:
                    await cls.bonus_attack(attacker, other)

        # the rest of the round: rituals, pets, a companion, a burning mount (an action-mode
        # swing leaves them to the 3-s round: action_combat.py)
        if not getattr(attacker, '_swing_only', False):
            await cls.round_extras(attacker, defender)

    @classmethod
    async def round_extras(cls, attacker: 'Character', defender: 'Character'):
        """What a round brings besides the swing: ritual time, pets and their pacts, a combat
        companion, a mount's fire aura."""
        c = cls.config.COLORS
        # Ritual duration and channeling check
        if getattr(attacker, 'channeling_ritual', False):
            ritual_duration = getattr(attacker, 'ritual_duration', 0)
            if ritual_duration > 0:
                attacker.ritual_duration -= 1
            else:
                # Ritual ends
                attacker.channeling_ritual = False
                await attacker.send(f"{c['yellow']}Your dark ritual fades.{c['reset']}")

        # Pet attacks (if attacker has pets)
        if hasattr(attacker, 'world'):
            from pets import PetManager
            pets = PetManager.get_player_pets(attacker)
            for pet in pets:
                if pet.room == attacker.room and pet.is_alive:
                    # Decrement death pact duration
                    if hasattr(pet, 'death_pact_duration') and pet.death_pact_duration > 0:
                        pet.death_pact_duration -= 1
                        if pet.death_pact_duration <= 0:
                            # Pact expired
                            if hasattr(pet, 'death_pact_master') and pet.death_pact_master:
                                master = pet.death_pact_master
                                if hasattr(master, 'send'):
                                    await master.send(f"{c['yellow']}Your death pact with {pet.name} fades.{c['reset']}")
                                master.death_pact_target = None
                            pet.death_pact_master = None

                    # Apply ritual buff HP regen (5% per round)
                    if hasattr(pet, 'ritual_buff_duration') and pet.ritual_buff_duration > 0:
                        pet.ritual_buff_duration -= 1
                        regen = int(pet.max_hp * 0.05)
                        if regen > 0 and pet.hp < pet.max_hp:
                            old_hp = pet.hp
                            pet.hp = min(pet.max_hp, pet.hp + regen)
                            if pet.hp > old_hp:
                                await attacker.send(f"{c['bright_green']}{pet.name} regenerates {pet.hp - old_hp} HP from dark ritual!{c['reset']}")

                        if pet.ritual_buff_duration <= 0:
                            pet.ritual_bonuses = {}

                    # Trigger pet special abilities via AI
                    if hasattr(pet, 'ai_combat_tick'):
                        pet.target = defender  # Set target for abilities
                        pet.fighting = defender  # This makes is_fighting return True
                        await pet.ai_combat_tick()

                    # Pet joins combat to help owner
                    if not pet.is_fighting or random.randint(1, 100) <= 50:  # 50% chance per round
                        await cls.pet_attack(pet, defender)

        # Combat companion attacks (class-based companion)
        if hasattr(attacker, 'combat_companion') and attacker.combat_companion:
            cc = attacker.combat_companion
            if cc.is_alive and cc.behavior != 'passive' and defender.is_alive:
                cc_dmg = cc.get_damage()
                if cc_dmg > 0:
                    # Defend mode: companion absorbs some damage instead
                    if cc.behavior == 'defend':
                        if hasattr(attacker, 'send'):
                            await attacker.send(f"{c['cyan']}{cc.name} guards you vigilantly.{c['reset']}")
                    else:
                        if hasattr(attacker, 'send'):
                            await attacker.send(f"{c['green']}{cc.name} {cc.attack_desc} {defender.name}! [{cc_dmg}]{c['reset']}")
                        if hasattr(defender, 'send'):
                            await defender.send(f"{c['red']}{cc.name} {cc.attack_desc} you! [{cc_dmg}]{c['reset']}")
                        killed = await defender.take_damage(cc_dmg, attacker)
                        if killed:
                            await cls.handle_death(attacker, defender)

        # Mount fire aura (nightmare) — deals fire damage to attacker's target
        if hasattr(attacker, 'mount') and attacker.mount and getattr(attacker.mount, 'fire_aura', False):
            if defender.is_alive:
                fire_dmg = random.randint(3, 8) + attacker.level // 3
                if hasattr(attacker, 'send'):
                    await attacker.send(f"{c['bright_red']}Your {attacker.mount.name}'s flames sear {defender.name}! [{fire_dmg}]{c['reset']}")
                if hasattr(defender, 'send'):
                    await defender.send(f"{c['bright_red']}Flames from {attacker.mount.name} burn you! [{fire_dmg}]{c['reset']}")
                killed = await defender.take_damage(fire_dmg, attacker, 'fire')
                if killed:
                    await cls.handle_death(attacker, defender)

        # Combat companion takes damage when in defend mode (absorbs 15% of damage dealt to owner)
        if hasattr(defender, 'combat_companion') and defender.combat_companion:
            cc = defender.combat_companion
            if cc.is_alive and cc.behavior == 'defend':
                # This is handled on the defender side — companion absorbs some incoming hits
                pass  # Actual absorption is applied in take_damage override if needed

    @classmethod
    async def auto_combat(cls, player: 'Player'):
        """Automatically use skills/spells based on player settings."""
        if not getattr(player, 'autocombat', False) or not player.is_fighting:
            return

        now = time.time()
        if now - getattr(player, 'last_autocombat_time', 0) < 1.8:
            return

        player.last_autocombat_time = now
        settings = getattr(player, 'auto_combat_settings', {})
        if not settings:
            return

        # Heal if below threshold
        try:
            heal_threshold = settings.get('heal_threshold', 35)
            hp_pct = (player.hp / player.max_hp) * 100 if player.max_hp > 0 else 0
            if hp_pct <= heal_threshold and settings.get('use_spells', True):
                heal_spells = settings.get('spell_priority', [])
                for spell in heal_spells:
                    if spell not in player.spells:
                        continue
                    spell_info = None
                    try:
                        from spells import SPELLS
                        spell_info = SPELLS.get(spell)
                    except Exception:
                        pass
                    if spell_info and spell_info.get('target') != 'defensive' and spell_info.get('target') != 'self':
                        continue

                    cooldown_key = f"spell:{spell}"
                    if player.auto_combat_cooldowns.get(cooldown_key, 0) > now:
                        continue

                    from spells import SpellHandler
                    await SpellHandler.cast_spell(player, spell)
                    player.auto_combat_cooldowns[cooldown_key] = now + 8
                    return
        except Exception:
            pass

        target = player.fighting
        if not target:
            return

        # Offensive spells
        if settings.get('use_spells', True):
            for spell in settings.get('spell_priority', []):
                if spell not in player.spells:
                    continue
                try:
                    from spells import SPELLS
                    spell_info = SPELLS.get(spell)
                    if not spell_info or spell_info.get('target') != 'offensive':
                        continue
                except Exception:
                    continue

                cooldown_key = f"spell:{spell}"
                if player.auto_combat_cooldowns.get(cooldown_key, 0) > now:
                    continue

                from spells import SpellHandler
                await SpellHandler.cast_spell(player, spell, target.name)
                player.auto_combat_cooldowns[cooldown_key] = now + 8
                return

        # Skills
        if settings.get('use_skills', True):
            skill_map = {
                'kick': cls.do_kick,
                'bash': cls.do_bash,
            }
            for skill in settings.get('skill_priority', []):
                if skill not in player.skills:
                    continue
                if skill not in skill_map:
                    continue

                cooldown_key = f"skill:{skill}"
                if player.auto_combat_cooldowns.get(cooldown_key, 0) > now:
                    continue

                await skill_map[skill](player)
                player.auto_combat_cooldowns[cooldown_key] = now + 6
                return

    @classmethod
    async def pet_attack(cls, pet: 'Character', defender: 'Character'):
        """Process a pet attack."""
        if not pet.is_alive or not defender.is_alive:
            return

        c = cls.config.COLORS

        # Calculate hit
        hit_roll = random.randint(1, 20) + pet.get_hit_bonus()
        # Lower AC = better armor = harder to hit (higher defense)
        defense = 10 - (defender.get_armor_class() // 10)

        if hit_roll >= defense:
            # Calculate damage
            damage = cls.roll_dice(pet.damage_dice) if hasattr(pet, 'damage_dice') else random.randint(1, 4)
            damage += pet.get_damage_bonus()

            special_attack = None
            if getattr(pet, 'role', None) == 'rogue' and random.randint(1, 100) <= 25:
                bonus = max(1, pet.level // 2) + random.randint(1, 4)
                damage += bonus
                special_attack = 'backstabs'

            damage = max(1, damage)

            damage_word = cls.get_damage_word(damage)
            attack_word = special_attack or damage_word

            # Send messages
            await pet.room.send_to_room(
                f"{c['green']}{pet.name} {attack_word} {defender.name}! [{damage}]{c['reset']}"
            )

            # Apply damage
            killed = await defender.take_damage(damage, pet)
            if killed:
                await cls.handle_death(pet, defender)
        else:
            # Miss
            await pet.room.send_to_room(
                f"{c['yellow']}{pet.name} misses {defender.name}.{c['reset']}"
            )

    @classmethod
    async def bonus_attack(cls, attacker: 'Character', defender: 'Character'):
        """Process a bonus attack."""
        if not attacker.is_alive or not defender.is_alive:
            return

        c = cls.config.COLORS
        hit_roll = random.randint(1, 20) + attacker.get_hit_bonus()
        # Lower AC = better armor = harder to hit (higher defense)
        defense = 10 - (defender.get_armor_class() // 10)

        if hit_roll >= defense:
            weapon = attacker.equipment.get('wield') if hasattr(attacker, 'equipment') else None

            if weapon and hasattr(weapon, 'damage_dice'):
                damage = cls.roll_dice(weapon.damage_dice)
            else:
                damage = random.randint(1, 3)

            if cls.is_player(attacker):
                damage = cls.scale_player_weapon_damage(attacker, damage)
            damage += attacker.get_damage_bonus()
            damage = max(1, damage)
            damage = cls.cap_boss_swing(attacker, defender, damage)
            if not cls.is_player(attacker):
                damage = cls.mitigate_incoming(defender, damage)
            damage_word = cls.get_damage_word(damage)
            wtype = getattr(weapon, 'weapon_type', 'hit') if weapon else 'hit'
            hit_noun, hit_verb, hit_adj = cls.damage_forms(damage_word, cls.get_weapon_verb(wtype)[0])

            if hasattr(attacker, 'send'):
                if getattr(attacker, 'compact_mode', False):
                    await attacker.send(f"{c['green']}You hit {defender.name}. [{damage}]{c['reset']}")
                else:
                    await attacker.send(f"{c['green']}Your follow-up {hit_noun} {hit_verb} {defender.name}! [{damage} damage]{c['reset']}")
            if hasattr(defender, 'send'):
                if getattr(defender, 'compact_mode', False):
                    await defender.send(f"{c['red']}{attacker.name} hits you. [{damage}]{c['reset']}")
                else:
                    await defender.send(f"{c['red']}{attacker.name}'s {hit_adj} follow-up {hit_noun} hits you! [{damage} damage]{c['reset']}")

            attacker._weapon_swing = True
            killed = await defender.take_damage(damage, attacker)
            attacker._weapon_swing = False
            if killed:
                await cls.handle_death(attacker, defender)
            else:
                import procs
                await procs.on_hit(attacker, defender, weapon)

    @classmethod
    async def offhand_attack(cls, attacker: 'Character', defender: 'Character'):
        """Process an off-hand dual wield attack."""
        if not attacker.is_alive or not defender.is_alive:
            return

        c = cls.config.COLORS
        hit_roll = random.randint(1, 20) + attacker.get_hit_bonus() - 2
        defense = 10 - (defender.get_armor_class() // 10)

        if hit_roll >= defense:
            weapon = attacker.equipment.get('dual_wield') if hasattr(attacker, 'equipment') else None
            if weapon and hasattr(weapon, 'damage_dice'):
                damage = int(cls.roll_dice(weapon.damage_dice) * 0.75)
            else:
                damage = random.randint(1, 2)
            if cls.is_player(attacker):
                damage = cls.scale_player_weapon_damage(attacker, damage)
            damage += int(attacker.get_damage_bonus() * 0.5)
            damage = max(1, damage)
            damage = cls.cap_boss_swing(attacker, defender, damage)
            damage_word = cls.get_damage_word(damage)
            _, hit_verb, hit_adj = cls.damage_forms(damage_word, 'hit')

            if hasattr(attacker, 'send'):
                await attacker.send(f"{c['green']}Your off-hand blow {hit_verb} {defender.name}! [{damage} damage]{c['reset']}")
            if hasattr(defender, 'send'):
                await defender.send(f"{c['red']}{attacker.name}'s {hit_adj} off-hand blow hits you! [{damage} damage]{c['reset']}")

            attacker._weapon_swing = True
            killed = await defender.take_damage(damage, attacker)
            attacker._weapon_swing = False
            if killed:
                await cls.handle_death(attacker, defender)
            else:
                import procs
                await procs.on_hit(attacker, defender, weapon)
        else:
            if hasattr(attacker, 'send'):
                await attacker.send(f"{c['yellow']}Your off-hand misses {defender.name}.{c['reset']}")
            if hasattr(defender, 'send'):
                await defender.send(f"{c['cyan']}{attacker.name}'s off-hand misses you.{c['reset']}")

    @classmethod
    async def handle_death(cls, killer: 'Character', victim: 'Character'):
        """Handle a combat death. Whatever goes wrong in the rewards, a slain creature still dies:
        it once stood on at 0 hp, with no corpse, when something after the "is DEAD!" failed."""
        try:
            await cls._handle_death(killer, victim)
        except Exception:
            logger.exception(f"handle_death: {getattr(killer, 'name', '?')} killing {getattr(victim, 'name', '?')}")
            try:
                await cls._death_fallback(killer, victim)
            except Exception:
                logger.exception('death fallback')

    @classmethod
    async def _death_fallback(cls, killer, victim):
        """The least a death must do when handle_death failed part-way: a creature leaves a corpse
        with what it carried, the fight ends, and it is gone from the room and the world."""
        if hasattr(victim, 'connection') or getattr(victim, 'hp', 1) > 0:
            return
        room = victim.room
        if room is None or victim not in room.characters:
            return
        if not any(getattr(o, 'name', '') == f"corpse of {victim.name}" for o in room.items):
            from objects import Object
            corpse = Object(0, getattr(killer, 'world', None))
            corpse.name = f"corpse of {victim.name}"
            corpse.short_desc = f"the corpse of {victim.name}"
            corpse.room_desc = f"The corpse of {victim.name} lies here."
            corpse.item_type = 'container'
            corpse.capacity = 1000
            corpse.container_flags = ['closeable']
            corpse.state = 'open'
            corpse.gold = max(0, getattr(victim, 'gold', 0) or 0)
            corpse.contents = list(getattr(victim, 'inventory', None) or [])
            if hasattr(victim, 'inventory'):
                victim.inventory.clear()
            corpse.decay_timer = 50
            room.items.append(corpse)
        try:
            await cls.end_combat(killer, victim)
        except Exception:
            logger.exception('death fallback: end_combat')
        for ch in list(room.characters):
            if getattr(ch, 'fighting', None) is victim:
                ch.fighting = None
                if getattr(ch, 'position', '') == 'fighting':
                    ch.position = 'standing'
        if victim in room.characters:
            room.characters.remove(victim)
        world = getattr(killer, 'world', None)
        if world is not None and victim in getattr(world, 'npcs', []):
            world.npcs.remove(victim)
        web_map = getattr(world, 'web_map', None) if world else None
        if web_map:
            for ch in list(room.characters):
                if hasattr(ch, 'connection'):
                    await web_map.notify_combat(ch)

    @classmethod
    async def _handle_death(cls, killer: 'Character', victim: 'Character'):
        # Guard against double-death processing
        if getattr(victim, '_death_processed', False):
            return
        victim._death_processed = True

        # A dying mob's declared wind-up dies with it
        if getattr(victim, 'pending_intent', None):
            victim.pending_intent = None

        # Announce the kill up front so the fight has a clear, readable end
        # (NPC deaths otherwise skipped Mobile.die's "is DEAD!" line)
        if not cls.is_player(victim) and getattr(victim, 'position', '') != 'dead':
            victim.position = 'dead'
            c_d = cls.config.COLORS
            if hasattr(killer, 'send'):
                await killer.send(f"{c_d['bright_red']}☠ {cap_first(victim.name)} is DEAD! You killed {victim.name}.{c_d['reset']}")
            if victim.room:
                await victim.room.send_to_room(
                    f"{c_d['red']}{cap_first(victim.name)} is DEAD!{c_d['reset']}", exclude=[killer])

        # Arena PvP intercept — no real death in arena
        try:
            from arena import ArenaManager
            if hasattr(killer, 'connection') and hasattr(victim, 'connection'):
                if await ArenaManager.handle_arena_death(killer, victim):
                    victim._death_processed = False
                    return
        except Exception:
            pass

        # Reset Intel for any assassin whose intel_target was the victim
        if victim.room:
            for char in victim.room.characters:
                if hasattr(char, 'intel_target') and char.intel_target == victim:
                    char.intel_target = None
                    char.intel_points = 0
                    char.intel_thresholds = {}

        # Adrenaline passive: kill restores 20% HP
        try:
            from talents import TalentManager
            if hasattr(killer, 'char_class') and killer.char_class.lower() == 'assassin':
                if TalentManager.has_talent(killer, 'adrenaline'):
                    heal = int(killer.max_hp * 0.20)
                    killer.hp = min(killer.max_hp, killer.hp + heal)
                    if hasattr(killer, 'send'):
                        c_k = killer.config.COLORS
                        await killer.send(f"{c_k['bright_green']}Adrenaline! You recover {heal} HP!{c_k['reset']}")
        except Exception:
            pass
        
        c = cls.config.COLORS

        # Duel check — if this is a duel, end it at 1 HP instead of death
        if hasattr(killer, 'dueling') and killer.dueling == victim:
            victim.hp = 1
            await cls.end_combat(killer, victim)
            wager = getattr(killer, 'duel_wager_amount', 0)
            if wager > 0:
                victim.gold = max(0, victim.gold - wager)
                killer.gold += wager
            if victim.room:
                await victim.room.send_to_room(
                    f"{c['bright_yellow']}═══ DUEL OVER ═══ {killer.name} defeats {victim.name}!"
                    + (f" ({wager} gold changes hands!)" if wager else "")
                    + f"{c['reset']}"
                )
            killer.dueling = None
            victim.dueling = None
            killer.duel_wager_amount = 0
            victim.duel_wager_amount = 0
            return
        if hasattr(victim, 'dueling') and victim.dueling == killer:
            victim.hp = 1
            await cls.end_combat(killer, victim)
            wager = getattr(victim, 'duel_wager_amount', 0)
            if wager > 0:
                victim.gold = max(0, victim.gold - wager)
                killer.gold += wager
            if victim.room:
                await victim.room.send_to_room(
                    f"{c['bright_yellow']}═══ DUEL OVER ═══ {killer.name} defeats {victim.name}!"
                    + (f" ({wager} gold changes hands!)" if wager else "")
                    + f"{c['reset']}"
                )
            killer.dueling = None
            victim.dueling = None
            killer.duel_wager_amount = 0
            victim.duel_wager_amount = 0
            return

        # who the kill is for: the killer, or the master of a pet (read by the drops below)
        exp_recipient = killer.owner if getattr(killer, 'owner', None) and hasattr(killer.owner, 'gain_exp') else killer

        # Ensure equipped items are lootable (a creature's: a fallen hero keeps what they wear;
        # their corpse holds what they carried and their gold)
        if hasattr(victim, 'equipment') and hasattr(victim, 'inventory') and not cls.is_player(victim):
            for item in list(victim.equipment.values()):
                if item:
                    victim.inventory.append(item)
            victim.equipment.clear()

        # Chance-based extra loot drops from loot_table
        if not hasattr(victim, 'connection') and hasattr(victim, 'loot_table') and hasattr(victim, 'inventory'):
            loot_table = getattr(victim, 'loot_table', [])
            # Support both old format (list) and new format (list of dicts with chance)
            if loot_table:
                from objects import create_object, create_preset_object
                for entry in loot_table:
                    if isinstance(entry, dict):
                        vnum = entry.get('vnum')
                        chance = entry.get('chance', 100)
                        if random.randint(1, 100) <= chance:
                            loot_obj = create_object(vnum, killer.world if hasattr(killer, 'world') else None) or create_preset_object(vnum)
                            if loot_obj:
                                victim.inventory.append(loot_obj)
                    else:
                        # Old format: just vnum with loot_chance
                        loot_chance = getattr(victim, 'loot_chance', 100)
                        if random.randint(1, 100) <= loot_chance:
                            loot_obj = create_object(entry, killer.world if hasattr(killer, 'world') else None) or create_preset_object(entry)
                            if loot_obj:
                                victim.inventory.append(loot_obj)
                                break  # Old format: one drop only

        # Legendary item drop check for bosses
        if not hasattr(victim, 'connection') and hasattr(victim, 'inventory'):
            try:
                from legendary import get_legendary_drop_for_boss, create_legendary, announce_legendary_drop
                leg_vnum = get_legendary_drop_for_boss(victim)
                if leg_vnum:
                    leg_item = create_legendary(leg_vnum, killer.world if hasattr(killer, 'world') else None)
                    if leg_item:
                        victim.inventory.append(leg_item)
                        # Server-wide announcement
                        killer_name = getattr(exp_recipient, 'name', getattr(killer, 'name', 'Someone'))
                        world = getattr(killer, 'world', None) or getattr(exp_recipient, 'world', None)
                        await announce_legendary_drop(world, killer_name, leg_item.short_desc)
            except Exception as e:
                logger.debug(f"Legendary drop check error: {e}")

        # a boss's rare mount (mounts.BOSS_MOUNTS)
        if not hasattr(victim, 'connection') and hasattr(exp_recipient, 'owned_mounts'):
            try:
                from mounts import boss_mount_drop
                await boss_mount_drop(exp_recipient, victim)
            except Exception:
                logger.exception('boss mount drop')

        # On-kill procs (procs.py)
        try:
            import procs
            await procs.on_kill(exp_recipient, victim)
        except Exception:
            logger.exception('on-kill procs')

        # Universal rare drop chance for all mobs (consumables/gold)
        if not hasattr(victim, 'connection') and hasattr(victim, 'inventory'):
            mob_level = getattr(victim, 'level', 1)
            # 5% base + 1% per 5 mob levels (max 15% at level 50)
            rare_chance = 5 + (mob_level // 5)
            if random.randint(1, 100) <= rare_chance:
                from objects import create_object, create_preset_object
                # Common drops: healing potion, mana potion, food, gold bonus
                common_drops = [3134, 3135, 3101, 3130]  # heal pot, mana pot, bread, meat pie
                drop_vnum = random.choice(common_drops)
                drop_obj = create_object(drop_vnum, killer.world if hasattr(killer, 'world') else None) or create_preset_object(drop_vnum)
                if drop_obj:
                    victim.inventory.append(drop_obj)
                else:
                    # Fallback: bonus gold
                    bonus_gold = random.randint(5, 10) * mob_level
                    if hasattr(victim, 'gold'):
                        victim.gold += bonus_gold

        # Award experience to killer (or owner if killer is a pet)
        exp_recipient = killer
        # If killer is a pet, give exp to owner instead
        if hasattr(killer, 'owner') and killer.owner and hasattr(killer.owner, 'gain_exp'):
            exp_recipient = killer.owner
            # Notify owner their pet got the kill
            if hasattr(exp_recipient, 'send'):
                await exp_recipient.send(f"{c['cyan']}{killer.name} slays {victim.name}!{c['reset']}")

        if hasattr(exp_recipient, 'gain_exp') and hasattr(victim, 'exp'):
            exp_base = getattr(victim, 'exp', 100)
            victim_level = getattr(victim, 'level', 1)

            # Double XP world event check
            try:
                world = getattr(exp_recipient, 'world', None)
                if world and hasattr(world, 'event_manager') and world.event_manager and world.event_manager.has_double_xp():
                    exp_base = int(exp_base * 2)
            except Exception:
                pass

            # New Game+ reward scaling: enemies already hit harder per cycle/
            # nightmare (see _ng_modifier), so the payout scales to match —
            # otherwise NG+ is strictly worse. Applies to XP and looted gold.
            try:
                ng = cls._ng_modifier(exp_recipient)
                if ng > 1.0:
                    exp_base = int(exp_base * ng)
                    if hasattr(victim, 'gold') and getattr(victim, 'gold', 0) > 0:
                        victim.gold = int(victim.gold * ng)
            except Exception:
                pass

            # --- GROUP XP SHARING ---
            group = getattr(exp_recipient, 'group', None)
            if group and len(group.members) > 1:
                # Distribute XP among group members in the same room
                exp_shares = group.get_exp_share(exp_base, room=exp_recipient.room)
                for member, share in exp_shares.items():
                    if not hasattr(member, 'gain_exp'):
                        continue
                    member_level = getattr(member, 'level', 1)
                    level_diff = victim_level - member_level
                    if level_diff >= 5:
                        m_mult = 1.5
                    elif level_diff >= 3:
                        m_mult = 1.3
                    elif level_diff >= 1:
                        m_mult = 1.15
                    elif level_diff >= -2:
                        m_mult = 1.0 if level_diff >= 0 else 0.8
                    elif level_diff >= -4:
                        m_mult = 0.5
                    elif level_diff >= -7:
                        m_mult = 0.25
                    else:
                        m_mult = 0.1
                    member_base = int(share * m_mult)
                    m_bonuses = {'kill': member_base}
                    # Boss bonus
                    if getattr(victim, 'is_boss', False):
                        bb = int(member_base * member.config.BOSS_XP_BONUS_PERCENT)
                        if bb > 0:
                            m_bonuses['boss'] = bb
                    # Kill streak (only for the actual killer)
                    if member == exp_recipient and hasattr(member, 'kill_streak'):
                        member.kill_streak = max(0, member.kill_streak) + 1
                        if hasattr(member, 'best_kill_streak'):
                            member.best_kill_streak = max(member.best_kill_streak, member.kill_streak)
                        streak_mult = min(member.config.STREAK_XP_BONUS_CAP,
                                          member.kill_streak * member.config.STREAK_XP_BONUS_PER_KILL)
                        sb = int(member_base * streak_mult)
                        if sb > 0:
                            m_bonuses['streak'] = sb
                    # Rested XP
                    if hasattr(member, 'rested_xp') and member.rested_xp > 0:
                        rb = min(member.rested_xp, member_base)
                        member.rested_xp -= rb
                        if rb > 0:
                            m_bonuses['rested'] = rb
                    total_gain = sum(m_bonuses.values())
                    if total_gain > 0:
                        try:
                            from paths import PathManager
                            total_gain = int(total_gain * PathManager.xp_bonus(member))
                        except Exception:
                            pass
                        await member.gain_exp(total_gain, breakdown=m_bonuses)
                        if hasattr(member, 'send'):
                            await member.send(f"{c['bright_yellow']}You gain {total_gain} experience points!{c['reset']}")
                            bp = []
                            if m_bonuses.get('boss'):
                                bp.append(f"Boss +{m_bonuses['boss']}")
                            if m_bonuses.get('streak'):
                                bp.append(f"Streak +{m_bonuses['streak']}")
                            if m_bonuses.get('rested'):
                                bp.append(f"Rested +{m_bonuses['rested']}")
                            extra_members = len(exp_shares) - 1
                            if extra_members > 0:
                                bp.append(f"Group +{extra_members * 10}%")
                            if bp:
                                await member.send(f"{c['cyan']}Bonuses: {', '.join(bp)}{c['reset']}")
            else:
                # Solo XP (original logic)
                killer_level = getattr(exp_recipient, 'level', 1)
                level_diff = victim_level - killer_level
                if level_diff >= 5:
                    exp_mult = 1.5
                elif level_diff >= 3:
                    exp_mult = 1.3
                elif level_diff >= 1:
                    exp_mult = 1.15
                elif level_diff >= -2:
                    exp_mult = 1.0 if level_diff >= 0 else 0.8
                elif level_diff >= -4:
                    exp_mult = 0.5
                elif level_diff >= -7:
                    exp_mult = 0.25
                else:
                    exp_mult = 0.1

                exp_base = int(exp_base * exp_mult)
                bonuses = {'kill': exp_base}

                boss_bonus = 0
                if getattr(victim, 'is_boss', False):
                    boss_bonus = int(exp_base * exp_recipient.config.BOSS_XP_BONUS_PERCENT)
                    if boss_bonus > 0:
                        bonuses['boss'] = boss_bonus

                streak_bonus = 0
                if hasattr(exp_recipient, 'kill_streak'):
                    exp_recipient.kill_streak = max(0, exp_recipient.kill_streak) + 1
                    if hasattr(exp_recipient, 'best_kill_streak'):
                        exp_recipient.best_kill_streak = max(exp_recipient.best_kill_streak, exp_recipient.kill_streak)
                    streak_mult = min(exp_recipient.config.STREAK_XP_BONUS_CAP,
                                      exp_recipient.kill_streak * exp_recipient.config.STREAK_XP_BONUS_PER_KILL)
                    streak_bonus = int(exp_base * streak_mult)
                    if streak_bonus > 0:
                        bonuses['streak'] = streak_bonus

                rested_bonus = 0
                if hasattr(exp_recipient, 'rested_xp') and exp_recipient.rested_xp > 0:
                    rested_bonus = min(exp_recipient.rested_xp, exp_base)
                    exp_recipient.rested_xp -= rested_bonus
                    if rested_bonus > 0:
                        bonuses['rested'] = rested_bonus

                total_gain = sum(bonuses.values())
                try:
                    from paths import PathManager
                    total_gain = int(total_gain * PathManager.xp_bonus(exp_recipient))
                except Exception:
                    pass
                await exp_recipient.gain_exp(total_gain, breakdown=bonuses)
                if hasattr(exp_recipient, 'send'):
                    await exp_recipient.send(f"{c['bright_yellow']}You gain {total_gain} experience points!{c['reset']}")
                    bonus_parts = []
                    if boss_bonus:
                        bonus_parts.append(f"Boss +{boss_bonus}")
                    if streak_bonus:
                        bonus_parts.append(f"Streak +{streak_bonus}")
                    if rested_bonus:
                        bonus_parts.append(f"Rested +{rested_bonus}")
                    if bonus_parts:
                        await exp_recipient.send(f"{c['cyan']}Bonuses: {', '.join(bonus_parts)}{c['reset']}")

        # Check quest progress for kills (use exp_recipient for pet kills)
        quest_holder = exp_recipient if 'exp_recipient' in dir() else killer
        if hasattr(quest_holder, 'active_quests') and hasattr(victim, 'name'):
            from quests import QuestManager
            await QuestManager.check_quest_progress(
                quest_holder, 'kill', {'mob_name': victim.name, 'mob_vnum': getattr(victim, 'vnum', 0)}
            )

        # Check kill achievements
        if hasattr(exp_recipient, 'connection'):
            try:
                from achievements import AchievementManager
                await AchievementManager.check_kill(exp_recipient, victim)
            except Exception as e:
                logger.debug(f"Achievement check error: {e}")

        # Faction reputation: explicit mob faction tag AND auto-gain from mob keywords
        if hasattr(killer, 'connection'):
            try:
                from factions import FactionManager
                # Legacy explicit faction tag
                faction_key = FactionManager.normalize_key(getattr(victim, 'faction', None))
                if faction_key:
                    rep_data = getattr(victim, 'faction_rep', None)
                    if isinstance(rep_data, dict):
                        await FactionManager.apply_reputation_changes(killer, rep_data, reason='Slaying a faction member')
                    else:
                        amount = rep_data if isinstance(rep_data, int) else -10
                        await FactionManager.apply_reputation_change(killer, faction_key, amount, reason='Slaying a faction member')
                # Auto-gain from mob name/keywords (new faction system)
                await FactionManager.on_mob_kill(killer, victim)
            except Exception:
                pass

        # Bestiary journal entry (first kill of this creature type)
        if hasattr(killer, 'connection'):
            try:
                from journal import JournalManager
                mob_key = f"{getattr(victim, 'vnum', 0)}_{getattr(victim, 'name', 'unknown').lower().replace(' ', '_')}"
                mob_name = getattr(victim, 'name', 'Unknown Creature')
                mob_level = getattr(victim, 'level', 1)
                mob_desc = getattr(victim, 'description', '') or getattr(victim, 'long_desc', '') or f"A level {mob_level} creature."
                location = killer.room.name if killer.room else 'Unknown'

                # Build a more detailed bestiary entry
                bestiary_content = f"{mob_desc}\n\nLevel: {mob_level}"
                if getattr(victim, 'is_boss', False):
                    bestiary_content += " (Boss)"

                await JournalManager.discover_creature(
                    killer, mob_key, mob_name, bestiary_content,
                    location=location,
                    metadata={'level': mob_level, 'vnum': getattr(victim, 'vnum', 0)}
                )
            except Exception:
                pass

            # Boss-specific achievements and titles
            if getattr(victim, 'is_boss', False):
                boss_achievement = getattr(victim, 'boss_achievement', None)
                if boss_achievement:
                    await AchievementManager.unlock(killer, boss_achievement)
                    try:
                        from collection_system import CollectionManager
                        await CollectionManager.record_trophy(killer, boss_achievement)
                    except Exception:
                        pass
                boss_title = getattr(victim, 'boss_title', None)
                if boss_title and hasattr(killer, 'title'):
                    killer.title = boss_title
                    if hasattr(killer, 'send'):
                        await killer.send(f"{c['bright_magenta']}You are now known as {boss_title}!{c['reset']}")

        # Necromancer Soul Shard generation on kill
        if hasattr(killer, 'soul_shards') and hasattr(killer, 'char_class'):
            if killer.char_class.lower() == 'necromancer':
                gain = 1
                # Undead kills grant +2
                if 'undead' in getattr(victim, 'flags', set()) or 'undead' in getattr(victim, 'race', '').lower():
                    gain = 2
                if killer.soul_shards < 10:
                    killer.soul_shards = min(10, killer.soul_shards + gain)
                    if hasattr(killer, 'send'):
                        await killer.send(f"{c['bright_cyan']}[Soul Shards: {killer.soul_shards}/10]{c['reset']}")

        # Bard Inspiration from group member kills
        if hasattr(killer, 'group') and killer.group:
            for member in killer.group.members:
                if hasattr(member, 'char_class') and str(member.char_class).lower() == 'bard':
                    if hasattr(member, 'inspiration') and member.room == killer.room:
                        if member.inspiration < 10:
                            member.inspiration = min(10, member.inspiration + 1)
                            if hasattr(member, 'send'):
                                await member.send(f"{c['bright_yellow']}[Inspiration: {member.inspiration}/10] (ally kill){c['reset']}")

        # Thief Luck decay after combat (reset streak)
        if hasattr(killer, 'luck_streak') and hasattr(killer, 'char_class'):
            if killer.char_class.lower() == 'thief':
                killer.luck_streak = 0
                killer.second_chance_used = False

        # Cleric Faith from holy kills
        if hasattr(killer, 'faith') and hasattr(killer, 'char_class'):
            if killer.char_class.lower() == 'cleric' and not getattr(killer, 'shadow_form', False):
                if killer.faith < 10:
                    killer.faith = min(10, killer.faith + 1)
                    if hasattr(killer, 'send'):
                        await killer.send(f"{c['bright_yellow']}[Faith: {killer.faith}/10]{c['reset']}")

        # Soul Harvest for necromancers (legacy system)
        if hasattr(killer, 'char_class') and killer.char_class == 'necromancer':
            # learned as a spell (the necromancer's book), once as a skill
            skill_level = max(getattr(killer, 'skills', {}).get('soul_harvest', 0), getattr(killer, 'spells', {}).get('soul_harvest', 0))
            if skill_level > 0:
                # Calculate chance and max fragments based on skill level
                if skill_level < 26:
                    chance = 25
                    max_frags = 3
                    duration = 600  # 10 minutes
                elif skill_level < 51:
                    chance = 30
                    max_frags = 4
                    duration = 600
                elif skill_level < 76:
                    chance = 35
                    max_frags = 5
                    duration = 600
                else:
                    chance = 40
                    max_frags = 5
                    duration = 900  # 15 minutes

                if random.randint(1, 100) <= chance:
                    if not hasattr(killer, 'soul_fragments'):
                        killer.soul_fragments = 0
                    if not hasattr(killer, 'soul_fragment_expires'):
                        killer.soul_fragment_expires = 0

                    import time
                    now = time.time()

                    if killer.soul_fragments < max_frags:
                        killer.soul_fragments += 1
                        killer.soul_fragment_expires = now + duration

                        if hasattr(killer, 'send'):
                            await killer.send(
                                f"{c['bright_cyan']}You harvest a soul fragment! ({killer.soul_fragments}/{max_frags}){c['reset']}"
                            )
                            if killer.soul_fragments >= max_frags:
                                await killer.send(
                                    f"{c['yellow']}Soul fragments at maximum!{c['reset']}"
                                )

        # Handle gold and autoloot
        gold_looted = False
        items_looted = []
        # a group here shares what falls: the gold split among the members present, the items by
        # the group's loot mode (round-robin hands them out in turn; a roll leaves the worthwhile
        # ones in the corpse for need/greed; free-for-all is the killer's autoloot as alone)
        party = []
        if hasattr(killer, 'connection') and not hasattr(victim, 'connection'):
            try:
                from groups import present_members
                party = present_members(killer)
            except Exception:
                party = []
        if party and getattr(victim, 'gold', 0) > 0:
            await killer.group.split_gold(victim.gold, among=party)
            victim.gold = 0
            gold_looted = True
        if party and killer.group.loot_mode == 'roundrobin' and getattr(victim, 'inventory', None):
            for item in list(victim.inventory):
                looter = killer.group.next_looter(party)
                victim.inventory.remove(item)
                looter.inventory.append(item)
                items_looted.append(item)
                for m in party:
                    if hasattr(m, 'send'):
                        await m.send(f"{c['bright_cyan']}{'You receive' if m is looter else looter.name + ' receives'} {item.short_desc} (round-robin).{c['reset']}")

        # Check for autoloot_gold setting
        if hasattr(victim, 'gold') and victim.gold > 0:
            if hasattr(killer, 'gold'):
                # Autoloot gold is on by default for players
                if hasattr(killer, 'autoloot_gold') and killer.autoloot_gold:
                    killer.gold += victim.gold
                    if hasattr(killer, 'send'):
                        await killer.send(f"{c['yellow']}You get {victim.gold} gold coins from the corpse.{c['reset']}")
                    try:
                        from combat_hooks import reward_event
                        reward_event(killer, 'gold', amt=int(victim.gold), total=int(killer.gold))
                    except Exception:
                        pass
                    # Achievement: gold earned
                    try:
                        from achievements import AchievementManager
                        await AchievementManager.check_gold(killer, victim.gold)
                    except Exception:
                        pass
                    victim.gold = 0  # Remove gold so it doesn't appear in corpse
                    gold_looted = True

        # Check for autoloot items
        if hasattr(killer, 'autoloot') and killer.autoloot and hasattr(victim, 'inventory'):
            if hasattr(killer, 'inventory'):
                from groups import _worth_rolling
                for item in list(victim.inventory):
                    if party and killer.group.loot_mode == 'roll' and _worth_rolling(item):
                        continue                    # left in the corpse for the group's roll
                    victim.inventory.remove(item)
                    killer.inventory.append(item)
                    items_looted.append(item)
                    try:
                        from collection_system import CollectionManager
                        await CollectionManager.record_item(killer, item)
                    except Exception:
                        pass
                    if hasattr(killer, 'send'):
                        await killer.send(f"{c['bright_cyan']}You get {item.short_desc} from the corpse.{c['reset']}")

        # NG+ exclusive loot chance
        if hasattr(killer, 'connection') and getattr(killer, 'ng_plus_cycle', 0) > 0:
            chance = 8 + (2 * killer.ng_plus_cycle)
            if getattr(killer, 'nightmare_mode', False):
                chance += 6
            if random.randint(1, 100) <= chance:
                from objects import create_preset_object
                ng_item = create_preset_object(9400)
                if ng_item:
                    if hasattr(killer, 'inventory'):
                        killer.inventory.append(ng_item)
                        if hasattr(killer, 'send'):
                            await killer.send(f"{c['bright_magenta']}You recover {ng_item.short_desc} from the fallen!{c['reset']}")
                        try:
                            from collection_system import CollectionManager
                            await CollectionManager.record_item(killer, ng_item)
                        except Exception:
                            pass

        # Create corpse with remaining items (if not autolooted)
        if victim.room and hasattr(victim, 'inventory'):
            from objects import Object
            corpse = Object(0, killer.world if hasattr(killer, 'world') else None)
            corpse.name = f"corpse of {victim.name}"
            corpse.short_desc = f"the corpse of {victim.name}"
            corpse.room_desc = f"The corpse of {victim.name} lies here."
            corpse.item_type = 'container'
            corpse.capacity = 1000  # Large capacity for corpses
            corpse.container_flags = ['closeable']
            corpse.state = 'open'  # Corpses start open

            # Add remaining gold to corpse if not autolooted
            if hasattr(victim, 'gold') and victim.gold > 0 and not gold_looted:
                corpse.gold = victim.gold
            else:
                corpse.gold = 0

            # whatever nobody took goes into the corpse
            corpse.contents = list(victim.inventory)
            victim.inventory.clear()

            # Player corpses last longer (10 min), mob corpses 5 min
            if hasattr(victim, 'connection'):
                corpse.decay_timer = 100  # ~10 min real time (player)
                # leave a memorial for graphical clients
                try:
                    from gravestones import GravestoneRegistry
                    GravestoneRegistry.record(victim.room.vnum, victim.name, getattr(killer, 'name', 'something'))
                except Exception:
                    pass
            else:
                corpse.decay_timer = 50  # ~5 min real time (mob)
            victim.room.items.append(corpse)
            # modern group loot: worthwhile drops go to a need/greed/pass roll
            if hasattr(killer, 'connection') and getattr(killer, 'group', None) and not hasattr(victim, 'connection'):
                try:
                    from groups import start_rolls
                    await start_rolls(killer, corpse)
                except Exception as e:
                    logger.warning(f"loot roll failed: {e}")

        # End combat
        await cls.end_combat(killer, victim)

        # Procedural dungeon boss completion
        if hasattr(killer, 'connection') and getattr(victim, 'is_dungeon_boss', False):
            from procedural import get_dungeon_manager
            manager = get_dungeon_manager()
            dungeon = manager.active_dungeons.get(killer.name)
            if dungeon and dungeon.get('id') == getattr(victim, 'dungeon_id', None):
                await manager.complete_dungeon(killer, dungeon)

        # Remove NPC from world if it's a mob
        dead_room = victim.room
        if not hasattr(victim, 'connection'):  # It's an NPC
            if victim.room and victim in victim.room.characters:
                victim.room.characters.remove(victim)
            if hasattr(killer, 'world') and victim in killer.world.npcs:
                killer.world.npcs.remove(victim)

        # Push a fresh combat/room update to any connected players in the room so
        # the web client removes the slain mob immediately (its sprite + target
        # frame would otherwise linger with stale HP until the next combat tick
        # or a room change). Covers kills landed outside the regular combat tick.
        try:
            world = getattr(killer, 'world', None) or getattr(exp_recipient, 'world', None)
            web_map = getattr(world, 'web_map', None) if world else None
            if web_map and dead_room:
                for ch in list(getattr(dead_room, 'characters', [])):
                    if hasattr(ch, 'connection'):
                        await web_map.notify_combat(ch)
        except Exception:
            pass

    @classmethod
    async def end_combat(cls, char1: 'Character', char2: 'Character'):
        """End combat between two characters."""
        if char1.fighting == char2:
            char1.fighting = None
            if char1.position == 'fighting':
                char1.position = 'standing'

        if char2.fighting == char1:
            char2.fighting = None
            if char2.position == 'fighting':
                char2.position = 'standing'

        # Clear intent/reaction combat state so nothing dangles into the next
        # fight (mob wind-ups, player brace/sidestep windows)
        for ch in (char1, char2):
            if getattr(ch, 'pending_intent', None):
                ch.pending_intent = None
            if getattr(ch, 'brace_until', 0):
                ch.brace_until = 0
            if getattr(ch, 'sidestep_until', 0):
                ch.sidestep_until = 0
            if getattr(ch, 'sidestep_skip_attack', False):
                ch.sidestep_skip_attack = False
            if getattr(ch, '_low_hp_warned', False):
                ch._low_hp_warned = False
            # Re-arm ambush openers for NPCs once combat ends (only the
            # ambusher role ever consumes the flag)
            if not hasattr(ch, 'connection') and getattr(ch, 'ai_state', None) is not None:
                ch.ai_state['ambush'] = True

    @classmethod
    async def attempt_flee(cls, player: 'Player', auto: bool = False):
        """Attempt to flee from combat."""
        if not player.is_fighting:
            # If mobs are still attacking, set fighting to one of them
            if player.room:
                attackers = [ch for ch in player.room.characters if hasattr(ch, 'fighting') and ch.fighting == player]
                if attackers:
                    player.fighting = attackers[0]
                    player.position = 'fighting'
                else:
                    return
            else:
                return

        c = cls.config.COLORS
        now = time.time()
        if now < getattr(player, 'flee_cooldown_until', 0):
            if not auto:
                remaining = int(max(0, getattr(player, 'flee_cooldown_until', 0) - now))
                await player.send(f"{c['yellow']}You need {remaining}s before you can flee again.{c['reset']}")
            return

        # Check for available exits (not into a room closed to you, nor through a sealed land's bar)
        available_exits = [d for d, e in player.room.exits.items() if e and e.get('room') and cls._may_take(player, e)]

        if not available_exits:
            await player.send(f"{c['red']}There's nowhere to flee to!{c['reset']}")
            return

        if player.move < cls.config.FLEE_MOVE_COST:
            if not auto:
                await player.send(f"{c['red']}You're too winded to flee!{c['reset']}")
            return
        player.move = max(0, player.move - cls.config.FLEE_MOVE_COST)

        # Chance to flee based on dexterity
        flee_chance = cls.get_flee_chance(player)
        flee_risk = cls.get_flee_risk_label(flee_chance)
        wil = getattr(player, 'wil', 10)
        composure = max(0, min(2, (wil - 10) // 4))
        flee_cd = max(1, cls.config.FLEE_COOLDOWN_SECONDS - composure)
        player.flee_cooldown_until = now + flee_cd

        if auto:
            await player.send(f"{c['yellow']}You panic and try to flee ({flee_risk} risk)!{c['reset']}")

        if random.randint(1, 100) <= flee_chance:
            direction = random.choice(available_exits)
            enemy = player.fighting
            cls._got_away(player)

            await cls.end_combat(player, enemy)

            await player.send(f"{c['yellow']}You flee {direction}!{c['reset']}")
            await player.room.send_to_room(
                f"{player.name} flees {direction}!",
                exclude=[player]
            )

            # Move player
            from commands import CommandHandler
            await CommandHandler.cmd_move(player, direction)

            # Lose some experience
            exp_loss = int(player.exp * 0.01)
            player.exp = max(0, player.exp - exp_loss)
            await player.send(f"{c['yellow']}You lose {exp_loss} experience points.{c['reset']}")
        else:
            await player.send(f"{c['red']}You fail to flee ({flee_risk} risk)!{c['reset']}")

    @staticmethod
    def _got_away(player):
        """Fled or escaped: the creatures fighting them let them go a while (reach.lost: they
        do not spot them next door and charge straight back)."""
        try:
            import reach
            for ch in list(getattr(player.room, 'characters', ()) or ()):
                if not hasattr(ch, 'connection') and getattr(ch, 'fighting', None) is player:
                    reach.lost(ch, player)
        except Exception:
            pass

    @staticmethod
    def _may_take(player, exit_data) -> bool:
        """An exit a fleeing or escaping player may take, as walking would allow it: not into a
        room only immortals may enter (the God Rooms), nor through the bar of a sealed land."""
        import doors
        room = exit_data.get('room')
        if room is None:
            return False
        if doors.is_seal(exit_data.get('door')) and not getattr(player, 'is_immortal', False):
            return False
        return not ('imm_only' in room.flags and not room.admits(player))

    @classmethod
    async def attempt_escape(cls, player: 'Player', direction: str):
        """Attempt a directed escape from combat."""
        if not player.is_fighting:
            return False

        c = cls.config.COLORS
        now = time.time()
        if now < getattr(player, 'escape_cooldown_until', 0):
            remaining = int(max(0, getattr(player, 'escape_cooldown_until', 0) - now))
            await player.send(f"{c['yellow']}You need {remaining}s before you can escape again.{c['reset']}")
            return False

        exit_data = player.room.exits.get(direction)
        if not exit_data or not exit_data.get('room') or not cls._may_take(player, exit_data):
            await player.send(f"{c['red']}You can't escape that way!{c['reset']}")
            return False

        if player.move < cls.config.ESCAPE_MOVE_COST:
            await player.send(f"{c['red']}You're too winded to escape that way!{c['reset']}")
            return False
        player.move = max(0, player.move - cls.config.ESCAPE_MOVE_COST)

        escape_chance = cls.get_escape_chance(player)
        escape_risk = cls.get_escape_risk_label(escape_chance)
        wil = getattr(player, 'wil', 10)
        composure = max(0, min(2, (wil - 10) // 4))
        escape_cd = max(1, cls.config.ESCAPE_COOLDOWN_SECONDS - composure)
        player.escape_cooldown_until = now + escape_cd

        if random.randint(1, 100) > escape_chance:
            await player.send(f"{c['yellow']}You fail to escape ({escape_risk} risk).{c['reset']}")
            return False

        enemy = player.fighting
        cls._got_away(player)
        await cls.end_combat(player, enemy)
        await player.send(f"{c['green']}You escape {direction}!{c['reset']}")
        await player.room.send_to_room(
            f"{player.name} escapes {direction}.",
            exclude=[player]
        )

        from commands import CommandHandler
        await CommandHandler.cmd_move(player, direction)
        return True

    @classmethod
    async def walk_out(cls, player: 'Player') -> bool:
        """A /play hero walks out of a fight into the next room: each foe fighting them gets a
        parting blow (one swing) as they turn their back, then the fight is broken off. The foes
        keep their grudge (a hunter follows; an aggressive creature across the open land may see
        them and come on: reach.noticed), so it is no free escape, as a flee is. False if the
        parting blows felled the hero."""
        c = cls.config.COLORS
        room = player.room
        foes = [ch for ch in (room.characters if room else []) if getattr(ch, 'fighting', None) is player and ch.is_alive]
        if player.fighting and player.fighting not in foes and player.fighting.is_alive:
            foes.append(player.fighting)
        for foe in foes:
            if foe.room is room and getattr(foe, 'fighting', None) is player and foe.is_alive and player.is_alive:
                await cls.bonus_attack(foe, player)
        if not player.is_alive or player.hp <= 0:
            return False
        for foe in foes:
            await cls.end_combat(player, foe)
            if hasattr(foe, 'add_grudge'):
                foe.add_grudge(player, 1)
        player.fighting = None
        if player.position == 'fighting':
            player.position = 'standing'
        await player.send(f"{c['yellow']}You break away from the fight.{c['reset']}")
        if room and foes:
            await room.send_to_room(f"{player.name} breaks away from the fight.", exclude=[player])
        return True

    @classmethod
    async def attempt_disengage(cls, player: 'Player') -> bool:
        """Attempt to disengage when not the primary target."""
        if not player.is_fighting:
            return False

        c = cls.config.COLORS
        now = time.time()
        if now < getattr(player, 'disengage_cooldown_until', 0):
            remaining = int(max(0, getattr(player, 'disengage_cooldown_until', 0) - now))
            await player.send(f"{c['yellow']}You need {remaining}s before you can disengage again.{c['reset']}")
            return False

        # Can't disengage if any enemies are still focusing you
        if player.room:
            attackers = [ch for ch in player.room.characters if hasattr(ch, 'fighting') and ch.fighting == player]
            if attackers:
                await player.send(f"{c['red']}Enemies are focused on you. Try flee or escape.{c['reset']}")
                return False

        if player.move < cls.config.DISENGAGE_MOVE_COST:
            await player.send(f"{c['red']}You're too winded to disengage!{c['reset']}")
            return False
        player.move = max(0, player.move - cls.config.DISENGAGE_MOVE_COST)

        wil = getattr(player, 'wil', 10)
        composure = max(0, min(1, (wil - 10) // 5))
        disengage_cd = max(1, cls.config.DISENGAGE_COOLDOWN_SECONDS - composure)
        player.disengage_cooldown_until = now + disengage_cd
        player.fighting = None
        if player.position == 'fighting':
            player.position = 'standing'
        await player.send(f"{c['green']}You disengage from combat.{c['reset']}")
        if player.room:
            await player.room.send_to_room(
                f"{player.name} disengages from the fight.",
                exclude=[player]
            )
        return True

    @classmethod
    async def do_kick(cls, player: 'Player', target: 'Character' = None):
        """Execute kick skill."""
        c = cls.config.COLORS

        # Use provided target or current fighting target
        if target is None:
            if not player.is_fighting:
                return
            target = player.fighting

        # Start combat if not already fighting
        if not player.is_fighting:
            await cls.start_combat(player, target)
        skill_level = player.get_skill_level('kick')

        # Check if kick lands
        if random.randint(1, 100) <= skill_level:
            damage = random.randint(1, player.level) + (player.str - 10) // 2
            damage = max(1, damage)
            damage_word = cls.get_damage_word(damage)

            if getattr(player, 'compact_mode', False):
                await player.send(f"{c['bright_green']}You kick {target.name}. [{damage}]{c['reset']}")
            else:
                await player.send(f"{c['bright_green']}Your kick {damage_word} {target.name}! [{damage}]{c['reset']}")
            if hasattr(target, 'send'):
                if getattr(target, 'compact_mode', False):
                    await target.send(f"{c['bright_red']}{player.name} kicks you. [{damage}]{c['reset']}")
                else:
                    await target.send(f"{c['bright_red']}{player.name}'s kick {damage_word} you! [{damage}]{c['reset']}")

            await cls.break_guard(player, target)
            killed = await target.take_damage(damage, player)
            if killed:
                await cls.handle_death(player, target)
        else:
            await player.send(f"{c['yellow']}Your kick misses {target.name}!{c['reset']}")

    @classmethod
    async def break_guard(cls, player: 'Player', target: 'Character'):
        """A heavy blow (bash/kick family) SHATTERS a raised guard and rocks
        the target's poise — the taught counter to guarded mobs."""
        if time.time() >= getattr(target, 'guard_until', 0):
            return
        target.guard_until = 0
        target.poise = getattr(target, 'poise', 0) + 2
        c = cls.config.COLORS
        if getattr(target, 'room', None):
            await target.room.send_to_room(
                f"{c['bright_yellow']}💥 {player.name}'s heavy blow SHATTERS {target.name}'s guard!{c['reset']}"
            )

    @classmethod
    async def do_bash(cls, player: 'Player', target: 'Character' = None):
        """Execute bash skill."""
        c = cls.config.COLORS

        # Use provided target or current fighting target
        if target is None:
            if not player.is_fighting:
                return
            target = player.fighting

        # Start combat if not already fighting
        if not player.is_fighting:
            await cls.start_combat(player, target)
        skill_level = player.get_skill_level('bash')

        if random.randint(1, 100) <= skill_level:
            bash_die = max(1, player.level // 2)
            damage = random.randint(1, bash_die) + (player.str - 10) // 2
            damage = max(1, damage)
            damage_word = cls.get_damage_word(damage)

            if getattr(player, 'compact_mode', False):
                await player.send(f"{c['bright_green']}You bash {target.name}. [{damage}]{c['reset']}")
            else:
                await player.send(f"{c['bright_green']}You bash {target.name} to the ground! [{damage}]{c['reset']}")
            if hasattr(target, 'send'):
                if getattr(target, 'compact_mode', False):
                    await target.send(f"{c['bright_red']}{player.name} bashes you. [{damage}]{c['reset']}")
                else:
                    await target.send(f"{c['bright_red']}{player.name} bashes you to the ground! [{damage}]{c['reset']}")

            # Bash can stun for a round (a boss keeps its feet)
            if random.randint(1, 100) <= 30 and not cls.is_boss_mob(target):
                cls.stun(target, 1)
                await player.send(f"{c['bright_yellow']}{target.name} is stunned!{c['reset']}")

            await cls.break_guard(player, target)
            killed = await target.take_damage(damage, player)
            if killed:
                await cls.handle_death(player, target)
            else:
                # a solid bash can knock them into the room's hazards
                try:
                    from environment import try_shove
                    await try_shove(player, target, player.room)
                except Exception:
                    pass
        else:
            await player.send(f"{c['yellow']}You fail to bash {target.name}!{c['reset']}")
            # Failed bash can make you fall
            if random.randint(1, 100) <= 20:
                await player.send(f"{c['red']}You fall to the ground!{c['reset']}")
                player.position = 'sitting'

    @classmethod
    async def do_backstab(cls, player: 'Player', target: 'Character') -> bool:
        """Execute backstab skill."""
        c = cls.config.COLORS
        skill_level = player.get_skill_level('backstab')

        # Must have a piercing weapon
        weapon = player.equipment.get('wield')
        if not weapon or getattr(weapon, 'weapon_type', '') not in ('stab', 'pierce'):
            await player.send(f"{c['red']}You need a piercing weapon to backstab!{c['reset']}")
            return False

        # Stealth/detection rolls
        env_bonus = 0
        try:
            if player.room and hasattr(player.room, 'is_dark') and player.room.is_dark(player.world.game_time):
                env_bonus += 20
            if player.room and player.room.sector_type in ('forest', 'swamp'):
                env_bonus += 10
        except Exception:
            pass
        if hasattr(player, 'has_light_source') and player.has_light_source():
            env_bonus -= 25

        sneak_skill = player.get_skill_level('sneak')
        hide_skill = player.get_skill_level('hide')
        stealth_roll = sneak_skill + (hide_skill // 2) + player.dex + env_bonus + random.randint(1, 20)
        target_wis = getattr(target, 'wis', 10)
        target_dex = getattr(target, 'dex', 10)
        detect_roll = ((target_wis + target_dex) // 2) + getattr(target, 'level', 1) + random.randint(1, 20)
        detected = detect_roll > stealth_roll

        # Success chance
        level_diff = player.level - getattr(target, 'level', player.level)
        chance = skill_level + (player.dex - target_dex) + (level_diff * 2)
        if 'hidden' in getattr(player, 'flags', set()):
            chance += 10
        if 'sneaking' in getattr(player, 'flags', set()):
            chance += 5
        if env_bonus > 0:
            chance += 5
        if detected:
            chance -= 20
        chance = max(5, min(95, chance))

        if random.randint(1, 100) <= chance:
            # Backstab does multiplied damage
            base_damage = cls.roll_dice(weapon.damage_dice) if hasattr(weapon, 'damage_dice') else random.randint(1, 4)
            multiplier = 2 + (player.level // 10)
            if 'hidden' in getattr(player, 'flags', set()):
                multiplier += 0.5
            if 'sneaking' in getattr(player, 'flags', set()):
                multiplier += 0.25
            if env_bonus > 0:
                multiplier += 0.25
            if env_bonus < 0:
                multiplier -= 0.5
            if detected:
                multiplier -= 0.5
            multiplier = max(1.0, multiplier)

            damage = int(base_damage * multiplier) + player.get_damage_bonus()
            # Gear backstab bonus (percentage of base damage)
            bs_bonus = player.get_equipment_bonus('backstab')
            if bs_bonus:
                damage += int(base_damage * (bs_bonus / 100))

            # Sleeping targets take extra damage
            if getattr(target, 'position', '') == 'sleeping':
                damage = int(damage * 1.5)

            # Rare execution (non-boss)
            flags = getattr(target, 'flags', set()) or set()
            is_boss = ('boss' in flags) or getattr(target, 'boss', False) or getattr(target, 'is_boss', False) or getattr(target, 'level', 0) >= 40
            if not is_boss:
                exec_chance = 0.5  # base %
                if level_diff >= 5:
                    exec_chance = min(1.5, exec_chance + 0.5)
                if level_diff < 0:
                    exec_chance = max(0.25, exec_chance * 0.5)
                if random.random() * 100 < exec_chance:
                    await player.send(f"{c['bright_red']}*** EXECUTION! ***{c['reset']}")
                    damage = max(damage, getattr(target, 'hp', 1))

            # Shadow Mend: stealth damage heals 10%
            try:
                from talents import TalentManager
                if TalentManager.has_talent(player, 'shadow_mend'):
                    if 'hidden' in getattr(player, 'flags', set()) or 'sneaking' in getattr(player, 'flags', set()):
                        heal = int(damage * 0.10)
                        if heal > 0:
                            player.hp = min(player.max_hp, player.hp + heal)
                            await player.send(f"{c['bright_green']}Shadow Mend heals you for {heal} HP!{c['reset']}")
            except Exception:
                pass

            await player.send(f"{c['bright_green']}You backstab {target.name}! [{damage}]{c['reset']}")
            if hasattr(target, 'send'):
                await target.send(f"{c['bright_red']}{player.name} backstabs you! [{damage}]{c['reset']}")
            await player.room.send_to_room(
                f"{player.name} backstabs {target.name}!",
                exclude=[player, target]
            )

            # Auto-mark target for Intel on backstab
            if getattr(player, 'char_class', '').lower() == 'assassin':
                if not getattr(player, 'intel_target', None) or player.intel_target != target:
                    player.intel_target = target
                    player.intel_points = 0
                    player.intel_thresholds = {}
                    await player.send(f"{c['cyan']}You automatically mark {target.name} for study.{c['reset']}")

            killed = await target.take_damage(damage, player)

            # Assassin Intel from backstab
            if hasattr(player, 'intel_target') and player.intel_target == target and not killed:
                if getattr(player, 'char_class', '').lower() == 'assassin':
                    from_stealth = 'hidden' in getattr(player, 'flags', set()) or 'sneaking' in getattr(player, 'flags', set())
                    try:
                        from talents import TalentManager
                        intel_backstab_talent = TalentManager.has_talent(player, 'intel_backstab')
                    except Exception:
                        intel_backstab_talent = False
                    if from_stealth and intel_backstab_talent:
                        intel_gain = 3
                    elif from_stealth:
                        intel_gain = 3
                    else:
                        intel_gain = 1
                    old_intel = player.intel_points
                    player.intel_points = min(10, player.intel_points + intel_gain)
                    if player.intel_points > old_intel:
                        await player.send(f"{c['cyan']}[Intel: {player.intel_points}/10]{c['reset']}")
                        thresholds = getattr(player, 'intel_thresholds', {})
                        tname = target.name
                        if player.intel_points >= 3 and not thresholds.get(3):
                            thresholds[3] = True
                            await player.send(f"{c['bright_green']}You spot an opening in {tname}'s defenses! [Expose Weakness unlocked]{c['reset']}")
                        if player.intel_points >= 6 and not thresholds.get(6):
                            thresholds[6] = True
                            await player.send(f"{c['bright_yellow']}You've mapped {tname}'s vital points! [Vital Strike unlocked]{c['reset']}")
                        if player.intel_points >= 10 and not thresholds.get(10):
                            thresholds[10] = True
                            await player.send(f"{c['bright_red']}You know exactly how to kill {tname}. [Execute Contract unlocked]{c['reset']}")
                        player.intel_thresholds = thresholds

            if killed:
                await cls.handle_death(player, target)
            else:
                # Start combat
                await cls.start_combat(player, target)
            return True
        else:
            await player.send(f"{c['yellow']}You fail to backstab {target.name}!{c['reset']}")
            # Failed backstab starts combat anyway
            await cls.start_combat(player, target)
            return False

    @classmethod
    def roll_dice(cls, dice_str: str) -> int:
        """Roll dice from a string like '2d6+4'."""
        try:
            # Parse dice string
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
            return total + bonus

        except Exception:
            return random.randint(1, 6)

    @classmethod
    async def do_envenom(cls, player: 'Player'):
        """Apply poison to weapon for extra damage."""
        c = cls.config.COLORS
        skill_level = player.get_skill_level('envenom')

        weapon = player.equipment.get('wield')
        if not weapon:
            await player.send(f"{c['red']}You need to wield a weapon to envenom it!{c['reset']}")
            return

        # Check for existing poison
        if hasattr(weapon, 'envenomed') and weapon.envenomed:
            await player.send(f"{c['yellow']}Your weapon is already envenomed!{c['reset']}")
            return

        # Find poison vial in inventory (respect preferred poison type if set)
        poison_vial = None
        poison_type = None
        preferred = getattr(player, 'preferred_poison_type', None)
        for item in player.inventory:
            if hasattr(item, 'item_type') and item.item_type == 'poison':
                item_type = getattr(item, 'poison_type', 'venom')
                if preferred and item_type != preferred:
                    continue
                poison_vial = item
                poison_type = item_type
                break

        # fallback to any poison vial if preferred not found
        if not poison_vial:
            for item in player.inventory:
                if hasattr(item, 'item_type') and item.item_type == 'poison':
                    poison_vial = item
                    poison_type = getattr(item, 'poison_type', 'venom')
                    break

        if not poison_vial:
            await player.send(f"{c['red']}You need a poison vial to envenom your weapon!{c['reset']}")
            await player.send(f"{c['yellow']}Hint: Buy poison vials from alchemists or rogue trainers.{c['reset']}")
            player.preferred_poison_type = None
            return

        # Get poison configuration
        poison_config = cls.config.POISON_TYPES.get(poison_type, cls.config.POISON_TYPES['venom'])

        # Cost move points
        if player.move < 10:
            await player.send(f"{c['red']}You are too exhausted to apply poison!{c['reset']}")
            return
        player.move -= 10

        if random.randint(1, 100) <= skill_level:
            # Success! Apply poison to weapon
            weapon.envenomed = True
            weapon.poison_type = poison_type
            weapon.poison_config = poison_config
            weapon.envenom_charges = 5 + (player.level // 3)  # Number of hits

            # Remove poison vial from inventory
            player.inventory.remove(poison_vial)

            # Success messages
            color_code = c.get(poison_config['color'], c['bright_green'])
            await player.send(
                f"{color_code}You carefully coat your {weapon.name} with {poison_config['name']}!{c['reset']}\n"
                f"{c['cyan']}Your weapon gleams with toxic energy. ({weapon.envenom_charges} charges){c['reset']}"
            )
            await player.room.send_to_room(
                f"{player.name} carefully applies a {poison_config['color']} substance to their weapon.",
                exclude=[player]
            )
            player.preferred_poison_type = None
        else:
            await player.send(f"{c['yellow']}You fumble and fail to properly apply the poison!{c['reset']}")
            # Failed envenom - chance to poison yourself
            if random.randint(1, 100) <= 15:
                await player.send(f"{c['red']}The {poison_config['name']} touches your skin! You feel ill!{c['reset']}")
                # Remove poison vial anyway (it was wasted)
                player.inventory.remove(poison_vial)
                # Apply poison effect to self
                from affects import AffectManager
                if poison_config.get('effect') == 'poison':
                    affect_data = {
                        'name': 'poison',
                        'type': AffectManager.TYPE_DOT,
                        'applies_to': 'hp',
                        'value': poison_config.get('damage', 2),
                        'duration': poison_config.get('duration', 5),
                        'caster_level': player.level
                    }
                    AffectManager.apply_affect(player, affect_data)
                elif poison_config.get('effect') == 'blind':
                    affect_data = {
                        'name': 'blindness',
                        'type': AffectManager.TYPE_FLAG,
                        'applies_to': 'blind',
                        'value': 1,
                        'duration': poison_config.get('duration', 5),
                        'caster_level': player.level
                    }
                    AffectManager.apply_affect(player, affect_data)
            player.preferred_poison_type = None

    @classmethod
    async def apply_poison_effect(cls, attacker: 'Character', victim: 'Character', weapon):
        """Apply poison effect from envenomed weapon on hit."""
        from affects import AffectManager
        c = cls.config.COLORS

        # Get poison configuration
        poison_type = getattr(weapon, 'poison_type', 'venom')
        poison_config = getattr(weapon, 'poison_config', cls.config.POISON_TYPES['venom'])

        # Decrement charges
        weapon.envenom_charges -= 1

        # Get color for messages
        color_code = c.get(poison_config.get('color', 'green'), c['bright_green'])

        # Send poison hit messages
        if hasattr(attacker, 'send'):
            await attacker.send(f"{color_code}{poison_config['hit_message']}{c['reset']}")
        if hasattr(victim, 'send'):
            await victim.send(f"{color_code}{poison_config['victim_message']}{c['reset']}")

        # Room message
        if hasattr(attacker, 'room') and attacker.room:
            room_msg = poison_config['room_message'].format(
                attacker=attacker.name,
                victim=victim.name
            )
            await attacker.room.send_to_room(f"{color_code}{room_msg}{c['reset']}", exclude=[attacker, victim])

        # Apply poison effect based on type
        effect_type = poison_config.get('effect', 'poison')

        if effect_type == 'poison':
            # Damage over time
            affect_data = {
                'name': 'poison',
                'type': AffectManager.TYPE_DOT,
                'applies_to': 'hp',
                'value': poison_config.get('damage', 3),
                'duration': poison_config.get('duration', 8),
                'caster_level': getattr(attacker, 'level', 1)
            }
            AffectManager.apply_affect(victim, affect_data)

        elif effect_type == 'blind':
            # Blindness effect
            affect_data = {
                'name': 'blindness',
                'type': AffectManager.TYPE_FLAG,
                'applies_to': 'blind',
                'value': 1,
                'duration': poison_config.get('duration', 6),
                'caster_level': getattr(attacker, 'level', 1)
            }
            AffectManager.apply_affect(victim, affect_data)

        elif effect_type == 'extra_damage':
            # Immediate extra damage
            extra_damage = poison_config.get('damage', 15)
            await victim.take_damage(extra_damage, attacker, 'poison')
            if hasattr(victim, 'send'):
                await victim.send(f"{color_code}The venom burns! ({extra_damage} additional damage){c['reset']}")

        elif effect_type == 'silence':
            # Silence effect
            affect_data = {
                'name': 'silence',
                'type': AffectManager.TYPE_FLAG,
                'applies_to': 'silenced',
                'value': 1,
                'duration': poison_config.get('duration', 5),
                'caster_level': getattr(attacker, 'level', 1)
            }
            AffectManager.apply_affect(victim, affect_data)

        elif effect_type == 'slow':
            # Slow effect (reduces dexterity)
            affect_data = {
                'name': 'slowed',
                'type': AffectManager.TYPE_MODIFY_STAT,
                'applies_to': 'dex',
                'value': poison_config.get('penalty', -2),
                'duration': poison_config.get('duration', 7),
                'caster_level': getattr(attacker, 'level', 1)
            }
            AffectManager.apply_affect(victim, affect_data)

        elif effect_type == 'weaken':
            # Weaken effect (reduces strength)
            stat = poison_config.get('stat', 'str')
            affect_data = {
                'name': 'weakened',
                'type': AffectManager.TYPE_MODIFY_STAT,
                'applies_to': stat,
                'value': poison_config.get('penalty', -3),
                'duration': poison_config.get('duration', 6),
                'caster_level': getattr(attacker, 'level', 1)
            }
            AffectManager.apply_affect(victim, affect_data)

        # Check if weapon poison is depleted
        if weapon.envenom_charges <= 0:
            weapon.envenomed = False
            weapon.poison_type = None
            weapon.poison_config = None
            weapon.envenom_charges = 0

            if hasattr(attacker, 'send'):
                await attacker.send(f"{c['yellow']}The poison on your {weapon.name} has been depleted.{c['reset']}")

    @classmethod
    async def do_assassinate(cls, player: 'Player', target: 'Character'):
        """Execute a deadly assassination attack - high damage if undetected."""
        c = cls.config.COLORS
        skill_level = player.get_skill_level('assassinate')

        # Must not be in combat
        if player.is_fighting:
            await player.send(f"{c['red']}You cannot assassinate while in combat!{c['reset']}")
            return

        # Target must not be fighting
        if target.is_fighting:
            await player.send(f"{c['red']}Your target is too alert to assassinate!{c['reset']}")
            return

        # Must have a piercing weapon
        weapon = player.equipment.get('wield')
        if not weapon or getattr(weapon, 'weapon_type', '') not in ('stab', 'pierce'):
            await player.send(f"{c['red']}You need a piercing weapon to assassinate!{c['reset']}")
            return

        # Check if player is hidden
        is_hidden = hasattr(player, 'affects') and 'hide' in player.affects

        # Check if target is marked (bonus damage)
        is_marked = hasattr(target, 'affects') and 'marked' in target.affects
        mark_bonus = 1.5 if is_marked else 1.0

        # Higher chance if hidden
        bonus = 20 if is_hidden else 0

        if random.randint(1, 100) <= skill_level + bonus:
            # Assassination damage - massive multiplier
            base_damage = cls.roll_dice(weapon.damage_dice) if hasattr(weapon, 'damage_dice') else random.randint(2, 8)
            multiplier = 4 + (player.level // 8)
            if is_hidden:
                multiplier += 2  # Extra damage from stealth

            damage = int(base_damage * multiplier * mark_bonus) + player.get_damage_bonus() * 2

            # Remove hide
            if is_hidden:
                from affects import AffectManager
                AffectManager.remove_affect_by_name(player, 'hide')

            # Clear mark if present
            if is_marked:
                from affects import AffectManager
                AffectManager.remove_affect_by_name(target, 'marked')
                await player.send(f"{c['magenta']}Your mark flares as you strike!{c['reset']}")

            await player.send(f"{c['bright_red']}You strike {target.name} in a vital spot! [{damage}]{c['reset']}")
            if hasattr(target, 'send'):
                await target.send(f"{c['bright_red']}{player.name} strikes you from the shadows! [{damage}]{c['reset']}")
            await player.room.send_to_room(
                f"{c['red']}{player.name} emerges from the shadows and strikes {target.name} viciously!{c['reset']}",
                exclude=[player, target]
            )

            killed = await target.take_damage(damage, player)
            if killed:
                await cls.handle_death(player, target)
            else:
                await cls.start_combat(player, target)
        else:
            await player.send(f"{c['yellow']}Your assassination attempt fails!{c['reset']}")
            if is_hidden:
                from affects import AffectManager
                AffectManager.remove_affect_by_name(player, 'hide')
            await cls.start_combat(player, target)

    @classmethod
    async def do_garrote(cls, player: 'Player', target: 'Character'):
        """Strangle a target from behind, silencing and damaging over time."""
        c = cls.config.COLORS
        skill_level = player.get_skill_level('garrote')

        # Must not be in combat
        if player.is_fighting:
            await player.send(f"{c['red']}You cannot garrote while in combat!{c['reset']}")
            return

        if target.is_fighting:
            await player.send(f"{c['red']}Your target is too alert to garrote!{c['reset']}")
            return

        # Check if player is hidden (better chance)
        is_hidden = hasattr(player, 'affects') and 'hide' in player.affects
        bonus = 15 if is_hidden else 0

        if random.randint(1, 100) <= skill_level + bonus:
            # Remove hide
            if is_hidden:
                from affects import AffectManager
                AffectManager.remove_affect_by_name(player, 'hide')

            # Apply garrote effect
            damage = random.randint(player.level // 2, player.level) + (player.dex - 10) // 2

            await player.send(f"{c['bright_red']}You wrap a garrote around {target.name}'s throat! [{damage}]{c['reset']}")
            if hasattr(target, 'send'):
                await target.send(f"{c['bright_red']}{player.name} wraps something around your throat! You can't breathe!{c['reset']}")
            await player.room.send_to_room(
                f"{player.name} garrotes {target.name} from behind!",
                exclude=[player, target]
            )

            # Apply silence effect
            from affects import AffectManager
            affect_data = {
                'name': 'silence',
                'type': AffectManager.TYPE_FLAG,
                'applies_to': 'silenced',
                'value': 1,
                'duration': 3,
                'caster_level': player.level
            }
            AffectManager.apply_affect(target, affect_data)

            killed = await target.take_damage(damage, player)
            if killed:
                await cls.handle_death(player, target)
            else:
                await cls.start_combat(player, target)
        else:
            await player.send(f"{c['yellow']}Your garrote attempt fails!{c['reset']}")
            if is_hidden:
                from affects import AffectManager
                AffectManager.remove_affect_by_name(player, 'hide')
            await cls.start_combat(player, target)

    @classmethod
    async def do_shadow_step(cls, player: 'Player', target: 'Character'):
        """Teleport behind a target, ending up hidden."""
        c = cls.config.COLORS
        skill_level = player.get_skill_level('shadow_step')

        if player.is_fighting:
            await player.send(f"{c['red']}You cannot shadow step while in combat!{c['reset']}")
            return

        # Cost move points
        if player.move < 20:
            await player.send(f"{c['red']}You are too exhausted to shadow step!{c['reset']}")
            return
        player.move -= 20

        if random.randint(1, 100) <= skill_level:
            await player.send(f"{c['magenta']}You dissolve into shadow and reappear behind {target.name}!{c['reset']}")
            await player.room.send_to_room(
                f"{player.name} dissolves into shadows...",
                exclude=[player]
            )

            # If target is in different room, move there
            if target.room != player.room:
                # Remove from current room
                if player in player.room.characters:
                    player.room.characters.remove(player)
                # Add to target's room
                target.room.characters.append(player)
                player.room = target.room

                await target.room.send_to_room(
                    f"Shadows coalesce as {player.name} appears from nowhere!",
                    exclude=[player]
                )

            # Apply hide effect
            from affects import AffectManager
            affect_data = {
                'name': 'hide',
                'type': AffectManager.TYPE_FLAG,
                'applies_to': 'hidden',
                'value': 1,
                'duration': 2,
                'caster_level': player.level
            }
            AffectManager.apply_affect(player, affect_data)

            await player.send(f"{c['cyan']}You are now hidden behind {target.name}.{c['reset']}")
        else:
            await player.send(f"{c['yellow']}You fail to step through the shadows!{c['reset']}")

    @classmethod
    async def do_mark_target(cls, player: 'Player', target: 'Character'):
        """Mark a target for death, increasing damage against them."""
        c = cls.config.COLORS
        skill_level = player.get_skill_level('mark_target')

        # Check if already marked
        if hasattr(target, 'affects') and 'marked' in target.affects:
            await player.send(f"{c['yellow']}{target.name} is already marked for death!{c['reset']}")
            return

        # Cost mana
        if player.mana < 5:
            await player.send(f"{c['red']}You don't have enough energy to mark a target!{c['reset']}")
            return
        player.mana -= 5

        if random.randint(1, 100) <= skill_level:
            from affects import AffectManager
            duration = 10 + (player.level // 5)
            affect_data = {
                'name': 'marked',
                'type': AffectManager.TYPE_FLAG,
                'applies_to': 'marked',
                'value': 1,
                'duration': duration,
                'caster_level': player.level
            }
            AffectManager.apply_affect(target, affect_data)

            await player.send(f"{c['magenta']}You mark {target.name} for death. A dark aura surrounds them.{c['reset']}")
            if hasattr(target, 'send'):
                await target.send(f"{c['magenta']}You feel a chill as {player.name} marks you for death!{c['reset']}")
            await player.room.send_to_room(
                f"A dark aura briefly surrounds {target.name}.",
                exclude=[player, target]
            )
        else:
            await player.send(f"{c['yellow']}You fail to mark {target.name}.{c['reset']}")

    @classmethod
    def get_damage_word(cls, damage: int) -> str:
        """Get a descriptive word for damage amount (CircleMUD style)."""
        if damage <= 0:
            return "miss"
        elif damage <= 2:
            return "tickle"
        elif damage <= 4:
            return "barely scratch"
        elif damage <= 6:
            return "scratch"
        elif damage <= 8:
            return "nick"
        elif damage <= 10:
            return "graze"
        elif damage <= 14:
            return "hit"
        elif damage <= 18:
            return "injure"
        elif damage <= 22:
            return "wound"
        elif damage <= 26:
            return "maul"
        elif damage <= 32:
            return "decimate"
        elif damage <= 40:
            return "devastate"
        elif damage <= 50:
            return "maim"
        elif damage <= 65:
            return "MUTILATE"
        elif damage <= 80:
            return "DISMEMBER"
        elif damage <= 100:
            return "MASSACRE"
        elif damage <= 140:
            return "OBLITERATE"
        else:
            return "*** ANNIHILATE ***"

    @classmethod
    def get_damage_color(cls, damage: int) -> str:
        """Get color code for damage amount."""
        c = Config().COLORS
        if damage <= 4:
            return c['white']
        elif damage <= 12:
            return c['green']
        elif damage <= 24:
            return c['yellow']
        elif damage <= 48:
            return c['bright_yellow']
        elif damage <= 80:
            return c['bright_red']
        else:
            return c['bright_magenta']

    @classmethod
    def get_weapon_verb(cls, weapon_type: str) -> tuple:
        """Get attack verb based on weapon type (CircleMUD style). Returns (you_verb, they_verb)."""
        verbs = {
            # CircleMUD standard weapon types
            'hit': ('hit', 'hits'),
            'sting': ('sting', 'stings'),
            'whip': ('whip', 'whips'),
            'slash': ('slash', 'slashes'),
            'bite': ('bite', 'bites'),
            'bludgeon': ('bludgeon', 'bludgeons'),
            'crush': ('crush', 'crushes'),
            'pound': ('pound', 'pounds'),
            'claw': ('claw', 'claws'),
            'maul': ('maul', 'mauls'),
            'thrash': ('thrash', 'thrashes'),
            'pierce': ('pierce', 'pierces'),
            'blast': ('blast', 'blasts'),
            'punch': ('punch', 'punches'),
            'stab': ('stab', 'stabs'),
            # Additional types
            'slice': ('slice', 'slices'),
            'cleave': ('cleave', 'cleaves'),
            'smash': ('smash', 'smashes'),
        }
        return verbs.get(weapon_type, ('hit', 'hits'))
