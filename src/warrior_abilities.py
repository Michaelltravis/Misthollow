"""
Warrior Martial Doctrines + Ability Evolution + Momentum System
===============================================================
Replaces the old combo chain system entirely.
"""

import time
import random
import logging
from typing import TYPE_CHECKING, Optional, Dict, List, Tuple

if TYPE_CHECKING:
    from player import Player, Character

from config import Config

logger = logging.getLogger('Misthollow.Warrior')

# ============================================================================
# CONSTANTS
# ============================================================================

WARRIOR_ABILITIES = ['strike', 'bash', 'cleave', 'charge', 'rally', 'execute']

DOCTRINES = {
    'iron_wall': {
        'name': 'Iron Wall',
        'description': 'Defensive mastery. Shields, taunts, and outlasting your enemies.',
        'flavor': 'You are the unbreakable line. Let them crash against you like waves on stone.',
        'momentum_bonus': '+2% damage reduction per Momentum point',
    },
    'berserker': {
        'name': 'Berserker',
        'description': 'Reckless offense. Trade your own blood for devastating power.',
        'flavor': 'Pain is fuel. Every wound makes you stronger. Every scar, a trophy.',
        'momentum_bonus': '+2% lifesteal per Momentum point',
    },
    'warlord': {
        'name': 'Warlord',
        'description': 'Tactical mastery. CC, debuffs, and group utility.',
        'flavor': 'The battlefield is a chess board. You see ten moves ahead.',
        'momentum_bonus': '+1 round debuff duration per 3 Momentum',
    },
}

EVOLUTION_THRESHOLDS = [50, 150, 300]

# Evolution data: ability -> threshold -> doctrine -> (evolution_name, description)
# Each ability has 3 tiers of evolution, each doctrine-specific.
EVOLUTION_TREE = {
    'strike': {
        50: {
            'iron_wall': ('shield_strike', '1.2x damage, generates shield absorbing 10% of damage for 3 rounds'),
            'berserker': ('brutal_strike', '2.5x damage but costs 5% of max HP'),
            'warlord': ('precision_strike', '1.8x damage, applies "exposed" (-10% AC for 3 rounds)'),
        },
        150: {
            'iron_wall': ('aegis_strike', 'Shield absorbs 20%, reflects 5% damage'),
            'berserker': ('savage_strike', '3x damage, costs 8% HP but heals 50% of damage dealt'),
            'warlord': ('analytical_strike', '2x damage, exposed stacks up to 3 times'),
        },
        300: {
            'iron_wall': ('immortal_strike', 'Shield absorbs 30%, if shield breaks deals AoE damage'),
            'berserker': ('deathwish_strike', '4x damage, costs 10% HP, if kill heals to full'),
            'warlord': ('mastermind_strike', '2.5x damage, exposed slows and reduces target damage 10%'),
        },
    },
    'bash': {
        50: {
            'iron_wall': ('fortress_bash', 'Stun + self shield 15% max HP for 3 rounds'),
            'berserker': ('skull_crack', '2x damage if target already stunned'),
            'warlord': ('concussive_bash', 'Stun target + daze adjacent mobs 1 round'),
        },
        150: {
            'iron_wall': ('bastion_bash', 'Shield 25% max HP, taunt'),
            'berserker': ('cranial_devastation', '3x if stunned, 25% chance to stun even if immune'),
            'warlord': ('shockwave_bash', 'AoE stun 1 round'),
        },
        300: {
            'iron_wall': ('unbreakable_bash', 'Shield 35% max HP, reflect stuns back'),
            'berserker': ('execution_bash', 'Instant kill if target <10% HP and stunned'),
            'warlord': ('domination_bash', 'AoE stun 2 rounds + disarm'),
        },
    },
    'cleave': {
        50: {
            'iron_wall': ('bulwark_sweep', '0.8x + knockback/aggro all'),
            'berserker': ('bloodwhirl', '1.2x all but bleed self 3% HP/round for 2 rounds'),
            'warlord': ('surgical_cleave', '1x + armor shred -5 AC each for 3 rounds'),
        },
        150: {
            'iron_wall': ('iron_tempest', '1x + knockback + 10% DR 2 rounds'),
            'berserker': ('blood_cyclone', '1.5x, bleed self 5% but lifesteal 20% of total dealt'),
            'warlord': ('anatomical_rend', '1.2x, -10 AC, extends existing debuffs by 1 round'),
        },
        300: {
            'iron_wall': ('aegis_storm', '1.2x + knockback + 20% DR + taunt 3 rounds'),
            'berserker': ('deathstorm', '2x all, bleed self 8%, if any die heal 25% max'),
            'warlord': ('grand_strategy', '1.5x, -15 AC, group members get +5% damage vs targets'),
        },
    },
    'charge': {
        50: {
            'iron_wall': ('ironclad_advance', '+20 temp armor for 3 rounds after charge'),
            'berserker': ('reckless_charge', '3x damage but take 10% max HP self-damage'),
            'warlord': ('flanking_rush', '1.5x + disorient: target misses next attack'),
        },
        150: {
            'iron_wall': ('juggernaut', '+30 armor, also knocks back other mobs'),
            'berserker': ('death_from_above', '4x, 15% self-damage, AoE damage to adjacent'),
            'warlord': ('tactical_insertion', '2x, disorient 2 rounds, +20% dodge for 2 rounds'),
        },
        300: {
            'iron_wall': ('unstoppable_force', '+40 armor, knockback, CC immune 2 rounds'),
            'berserker': ('extinction_event', '5x, 20% self, AoE 2x to all, if any die reset charge CD'),
            'warlord': ('checkmate', '3x, disorient 3 rounds, target abilities cost double for 3'),
        },
    },
    'rally': {
        50: {
            'iron_wall': ('stand_your_ground', 'Heal 20% + taunt all in room 2 rounds'),
            'berserker': ('blood_frenzy', 'No heal, +30% damage for 3 rounds, costs 10% HP'),
            'warlord': ('battle_orders', 'Heal 10% to self AND all group members'),
        },
        150: {
            'iron_wall': ('immovable_object', 'Heal 30%, taunt, +25% DR 2 rounds'),
            'berserker': ('berserker_rage', '+50% damage 3 rounds, costs 15% HP, immune to fear'),
            'warlord': ('inspiring_command', 'Heal 15% group, +10% damage group 3 rounds'),
        },
        300: {
            'iron_wall': ('eternal_guardian', 'Heal 40%, taunt, +35% DR, survive death once in 3 rounds'),
            'berserker': ('war_incarnate', '+75% damage 4 rounds, costs 20% HP, immune debuffs, lifesteal 15%'),
            'warlord': ('supreme_command', 'Heal 20% group, +15% dmg +10% DR group 4 rounds, cleanse 1 debuff'),
        },
    },
    'execute': {
        50: {
            'iron_wall': ('merciful_end', '3x, if kills: gain shield = 20% of target max HP'),
            'berserker': ('overkill', '4x, excess damage splashes to all others at 50%'),
            'warlord': ('subjugate', '3x, if would kill: 50% chance target surrenders for bonus XP/gold'),
        },
        150: {
            'iron_wall': ('righteous_execution', '4x, shield 30% of target max, shield heals you slowly'),
            'berserker': ('massacre', '5x, splash 75%, each kill extends Unstoppable by 1 round'),
            'warlord': ('total_domination', '4x, surrender chance 75%, surrendered mobs drop bonus loot'),
        },
        300: {
            'iron_wall': ('divine_judgment', '5x, shield 40%, nearby allies also get shield'),
            'berserker': ('annihilation', '6x, splash 100%, each kill gives +10% damage rest of combat'),
            'warlord': ('absolute_authority', '5x, 100% surrender or kill, surrendered become temp followers'),
        },
    },
}

# Reverse lookup: evolution_name -> (base_ability, threshold)
EVOLUTION_LOOKUP = {}
for ability, thresholds in EVOLUTION_TREE.items():
    for threshold, doctrines in thresholds.items():
        for doctrine, (evo_name, desc) in doctrines.items():
            EVOLUTION_LOOKUP[evo_name] = (ability, threshold, doctrine)

# Ability cooldowns (seconds)
ABILITY_COOLDOWNS = {
    'strike': 4, 'bash': 8, 'cleave': 10, 'charge': 12, 'rally': 15, 'execute': 15,
}

# Base damage multipliers
ABILITY_BASE_MULT = {
    'strike': 1.5, 'bash': 1.0, 'cleave': 0.8, 'charge': 1.5, 'rally': 0, 'execute': 3.0,
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_evolution_chain(ability: str, doctrine: str) -> List[str]:
    """Get the ordered evolution names for an ability under a doctrine."""
    chain = []
    for threshold in EVOLUTION_THRESHOLDS:
        data = EVOLUTION_TREE.get(ability, {}).get(threshold, {}).get(doctrine)
        if data:
            chain.append(data[0])  # evolution name
    return chain


def get_current_evolution_tier(player, ability: str) -> int:
    """Return 0 (base), 1 (tier 1 evo), 2 (tier 2), 3 (tier 3)."""
    evo = getattr(player, 'ability_evolutions', {}).get(ability)
    if not evo:
        return 0
    # Find which tier this evolution belongs to
    for ability_key, thresholds in EVOLUTION_TREE.items():
        if ability_key != ability:
            continue
        for i, threshold in enumerate(EVOLUTION_THRESHOLDS):
            for doctrine, (evo_name, desc) in thresholds.get(threshold, {}).items():
                if evo_name == evo:
                    return i + 1
    return 0


def get_effective_ability_name(player, ability: str) -> str:
    """Get the display name of the ability (evolved or base)."""
    evo = getattr(player, 'ability_evolutions', {}).get(ability)
    return evo if evo else ability


def get_next_evolution_threshold(player, ability: str) -> Optional[int]:
    """Get the next evolution threshold for an ability, or None if maxed."""
    current_tier = get_current_evolution_tier(player, ability)
    if current_tier >= len(EVOLUTION_THRESHOLDS):
        return None
    return EVOLUTION_THRESHOLDS[current_tier]


def can_evolve(player, ability: str) -> bool:
    """Check if player can evolve this ability right now."""
    doctrine = getattr(player, 'war_doctrine', None)
    if not doctrine:
        return False
    usage = getattr(player, 'ability_usage', {}).get(ability, 0)
    next_threshold = get_next_evolution_threshold(player, ability)
    if next_threshold is None:
        return False
    return usage >= next_threshold


def get_momentum_bar(momentum: int) -> str:
    """Generate momentum display bar."""
    filled = '█' * momentum
    empty = '░' * (10 - momentum)
    return f"[Momentum: {filled}{empty} {momentum}/10]"


def get_momentum_damage_mult(player) -> float:
    """Get damage multiplier from momentum."""
    momentum = getattr(player, 'momentum', 0)
    return 1.0 + (momentum * 0.05)


def get_momentum_speed_reduction(player) -> float:
    """Get combat delay reduction from momentum (fraction to subtract)."""
    momentum = getattr(player, 'momentum', 0)
    return momentum * 0.03


def apply_momentum(player, ability_name: str):
    """Apply momentum gain/reset based on ability used."""
    import time as _time
    last = getattr(player, 'last_warrior_ability', None)
    now = _time.time()
    perfect = now < getattr(player, 'perfect_form_until', 0)            # talent: +2, never reset
    presence = perfect or now < getattr(player, 'warlords_presence_until', 0)   # talent: never reset
    if ability_name == last and not presence:
        # Same ability twice — reset
        player.momentum = 0
    else:
        # Different ability — gain +1
        player.momentum = min(10, getattr(player, 'momentum', 0) + (2 if perfect else 1))
    player.last_warrior_ability = ability_name

    # Check for Unstoppable trigger
    if player.momentum >= 10 and getattr(player, 'unstoppable_rounds', 0) <= 0:
        player.unstoppable_rounds = 4
        return True  # Signal that unstoppable was triggered
    return False


def berserker_self_damage(player, pct: float) -> int:
    """Apply self-damage from berserker abilities. Returns damage dealt. Cannot kill."""
    amount = max(1, int(player.max_hp * pct))
    player.hp = max(1, player.hp - amount)
    return amount


def get_weapon_damage(player) -> int:
    """Get base weapon damage roll: the weapon's dice grown with the warrior's level, as an
    ordinary swing's are (CombatHandler.scale_player_weapon_damage), plus the damage bonus."""
    from combat import CombatHandler
    weapon = player.equipment.get('wield') if hasattr(player, 'equipment') else None
    if weapon and hasattr(weapon, 'damage_dice'):
        dice = CombatHandler.roll_dice(weapon.damage_dice)
    else:
        dice = random.randint(1, 6)
    if CombatHandler.is_player(player):
        dice = CombatHandler.scale_player_weapon_damage(player, dice)
    return dice + player.get_damage_bonus()


async def apply_damage_to_target(player, target, damage: int, ability_name: str = '') -> bool:
    """Apply damage to target with momentum multiplier. Returns True if killed."""
    from combat import CombatHandler
    c = Config.COLORS
    
    # Apply momentum damage bonus
    damage = int(damage * get_momentum_damage_mult(player))
    
    # Apply Unstoppable bonus (all abilities get +25% during Unstoppable)
    if getattr(player, 'unstoppable_rounds', 0) > 0:
        damage = int(damage * 1.25)
    
    damage = max(1, damage)
    
    dmg_word = CombatHandler.get_damage_word(damage)
    dmg_color = CombatHandler.get_damage_color(damage)
    # "Your bash nicks the zombie!", not "nick": the word list is in the first person
    dmg_verb = CombatHandler.DAMAGE_FORMS.get(dmg_word, (dmg_word + 's', dmg_word))[0]

    if hasattr(player, 'send'):
        await player.send(f"{c['bright_green']}Your {ability_name} {dmg_verb} {target.name}! {dmg_color}[{damage}]{c['reset']}")
    if hasattr(target, 'send'):
        await target.send(f"{c['bright_red']}{player.name}'s {ability_name} {dmg_verb} you! {dmg_color}[{damage}]{c['reset']}")
    if player.room:
        await player.room.send_to_room(
            f"{c['white']}{player.name}'s {ability_name} hits {target.name}. [{damage}]{c['reset']}",
            exclude=[player, target]
        )
    
    killed = await target.take_damage(damage, player)
    
    if not killed and hasattr(player, 'send'):
        health_pct = (target.hp / target.max_hp) * 100 if target.max_hp > 0 else 0
        health_color = CombatHandler.get_health_color(health_pct)
        health_bar = CombatHandler.get_health_bar(health_pct)
        await player.send(f"{c['cyan']}{target.name} {health_color}{health_bar} [{target.hp}/{target.max_hp}]{c['reset']}")
    
    return killed


async def handle_kill(player, target):
    """Handle death after warrior ability kill."""
    from combat import CombatHandler
    await CombatHandler.handle_death(player, target)


def increment_usage(player, ability: str):
    """Increment ability usage counter."""
    if not hasattr(player, 'ability_usage'):
        player.ability_usage = {a: 0 for a in WARRIOR_ABILITIES}
    player.ability_usage[ability] = player.ability_usage.get(ability, 0) + 1


# ============================================================================
# ABILITY IMPLEMENTATIONS
# ============================================================================

async def do_strike(player, args: list):
    """Strike ability."""
    c = Config.COLORS
    
    if not player.is_fighting:
        # Try to start combat
        if args:
            target = player.find_target_in_room(' '.join(args))
            if not target:
                await player.send("Strike whom?")
                return
            from combat import CombatHandler
            await CombatHandler.start_combat(player, target)
        else:
            await player.send("You aren't fighting anyone!")
            return
    
    target = player.fighting
    if not target or not target.is_alive:
        await player.send("Your target is already dead!")
        return
    
    # Cooldown check
    now = time.time()
    cd_key = 'strike_cd'
    if now < getattr(player, cd_key, 0):
        remaining = getattr(player, cd_key, 0) - now
        await player.send(f"{c['yellow']}Strike is on cooldown ({remaining:.1f}s).{c['reset']}")
        return
    
    # Get evolution
    evo = getattr(player, 'ability_evolutions', {}).get('strike')
    ability_display = evo or 'strike'
    
    # Calculate damage based on evolution
    base_dmg = get_weapon_damage(player)
    mult = 1.5  # base strike
    self_cost_pct = 0
    shield_pct = 0
    apply_exposed = False
    heal_pct = 0
    
    if evo == 'shield_strike':
        mult = 1.2; shield_pct = 0.10
    elif evo == 'brutal_strike':
        mult = 2.5; self_cost_pct = 0.05
    elif evo == 'precision_strike':
        mult = 1.8; apply_exposed = True
    elif evo == 'aegis_strike':
        mult = 1.2; shield_pct = 0.20
    elif evo == 'savage_strike':
        mult = 3.0; self_cost_pct = 0.08; heal_pct = 0.50
    elif evo == 'analytical_strike':
        mult = 2.0; apply_exposed = True
    elif evo == 'immortal_strike':
        mult = 1.2; shield_pct = 0.30
    elif evo == 'deathwish_strike':
        mult = 4.0; self_cost_pct = 0.10
    elif evo == 'mastermind_strike':
        mult = 2.5; apply_exposed = True
    
    damage = max(1, int(base_dmg * mult))
    
    # Self-damage (berserker)
    if self_cost_pct > 0:
        self_dmg = berserker_self_damage(player, self_cost_pct)
        await player.send(f"{c['red']}The strike costs you {self_dmg} HP!{c['reset']}")
    
    # Apply momentum
    unstoppable_triggered = apply_momentum(player, 'strike')
    if unstoppable_triggered:
        await player.send(f"{c['bright_yellow']}*** UNSTOPPABLE! ***{c['reset']}")
    
    increment_usage(player, 'strike')
    
    # Apply damage
    killed = await apply_damage_to_target(player, target, damage, ability_display.replace('_', ' '))
    
    # Post-damage effects
    if not killed:
        # Shield generation
        if shield_pct > 0:
            shield_amount = int(damage * shield_pct)
            player.warrior_shield = getattr(player, 'warrior_shield', 0) + shield_amount
            player.warrior_shield_rounds = 3
            await player.send(f"{c['cyan']}You gain a shield absorbing {shield_amount} damage!{c['reset']}")
        
        # Exposed debuff
        if apply_exposed:
            stacks = getattr(target, 'exposed_stacks', 0)
            max_stacks = 3 if evo in ('analytical_strike', 'mastermind_strike') else 1
            if stacks < max_stacks:
                target.exposed_stacks = stacks + 1
                target.exposed_rounds = 3
                await player.send(f"{c['yellow']}{target.name} is exposed! (-10% AC per stack, {target.exposed_stacks} stacks){c['reset']}")
        
        # Heal from savage_strike
        if heal_pct > 0 and evo == 'savage_strike':
            heal = int(damage * heal_pct)
            player.hp = min(player.max_hp, player.hp + heal)
            await player.send(f"{c['bright_green']}You heal {heal} HP from the carnage!{c['reset']}")
    else:
        # Deathwish kill heal
        if evo == 'deathwish_strike':
            player.hp = player.max_hp
            await player.send(f"{c['bright_green']}The kill fills you with vitality! Full HP restored!{c['reset']}")
        await handle_kill(player, target)
    
    # Set cooldown
    cd = ABILITY_COOLDOWNS['strike']
    cd *= (1.0 - get_momentum_speed_reduction(player))
    setattr(player, cd_key, now + max(1.0, cd))
    
    await _show_momentum(player)


async def do_bash(player, args: list):
    """Bash ability."""
    c = Config.COLORS
    
    if not player.is_fighting:
        if args:
            target = player.find_target_in_room(' '.join(args))
            if not target:
                await player.send("Bash whom?")
                return
            from combat import CombatHandler
            await CombatHandler.start_combat(player, target)
        else:
            await player.send("You aren't fighting anyone!")
            return
    
    target = player.fighting
    if not target or not target.is_alive:
        return
    
    now = time.time()
    cd_key = 'bash_cd'
    if now < getattr(player, cd_key, 0):
        remaining = getattr(player, cd_key, 0) - now
        await player.send(f"{c['yellow']}Bash is on cooldown ({remaining:.1f}s).{c['reset']}")
        return
    
    evo = getattr(player, 'ability_evolutions', {}).get('bash')
    ability_display = evo or 'bash'
    base_dmg = get_weapon_damage(player)
    mult = 1.0
    stun_rounds = 1
    shield_pct = 0
    
    if evo == 'skull_crack':
        if getattr(target, 'stunned_rounds', 0) > 0:
            mult = 2.0
    elif evo == 'cranial_devastation':
        if getattr(target, 'stunned_rounds', 0) > 0:
            mult = 3.0
        elif random.randint(1, 100) <= 25:
            stun_rounds = 1  # stun even if immune
    elif evo == 'execution_bash':
        if getattr(target, 'stunned_rounds', 0) > 0:
            hp_pct = (target.hp / target.max_hp) * 100 if target.max_hp > 0 else 100
            if hp_pct < 10:
                mult = 999  # instant kill
    elif evo == 'fortress_bash':
        shield_pct = 0.15
    elif evo == 'bastion_bash':
        shield_pct = 0.25
    elif evo == 'unbreakable_bash':
        shield_pct = 0.35
    elif evo in ('concussive_bash', 'shockwave_bash', 'domination_bash'):
        pass  # AoE stun handled below
    
    damage = max(1, int(base_dmg * mult))
    
    unstoppable_triggered = apply_momentum(player, 'bash')
    if unstoppable_triggered:
        await player.send(f"{c['bright_yellow']}*** UNSTOPPABLE! ***{c['reset']}")
    
    increment_usage(player, 'bash')

    # a bash SHATTERS a raised guard (guarded-mob counterplay)
    from combat import CombatHandler
    await CombatHandler.break_guard(player, target)
    killed = await apply_damage_to_target(player, target, damage, ability_display.replace('_', ' '))
    if not killed:
        # a solid bash can knock them into the room's hazards
        try:
            from environment import try_shove
            await try_shove(player, target, player.room)
        except Exception:
            pass
    
    if not killed:
        # Stun
        if getattr(target, 'unstoppable_rounds', 0) <= 0:
            target.stunned_rounds = max(getattr(target, 'stunned_rounds', 0), stun_rounds)
            await player.send(f"{c['bright_yellow']}{target.name} is stunned!{c['reset']}")
        
        # Shield
        if shield_pct > 0:
            shield_amount = int(player.max_hp * shield_pct)
            player.warrior_shield = getattr(player, 'warrior_shield', 0) + shield_amount
            player.warrior_shield_rounds = 3
            await player.send(f"{c['cyan']}You gain a shield for {shield_amount}!{c['reset']}")
        
        # AoE stun effects
        if evo in ('concussive_bash', 'shockwave_bash', 'domination_bash'):
            aoe_stun = 1 if evo != 'domination_bash' else 2
            for mob in list(player.room.characters):
                if mob != player and mob != target and mob.is_alive and hasattr(mob, 'hp'):
                    if not hasattr(mob, 'connection'):  # Only mobs
                        mob.stunned_rounds = max(getattr(mob, 'stunned_rounds', 0), aoe_stun)
            await player.send(f"{c['bright_yellow']}Nearby enemies are stunned!{c['reset']}")
    else:
        await handle_kill(player, target)
    
    cd = ABILITY_COOLDOWNS['bash']
    cd *= (1.0 - get_momentum_speed_reduction(player))
    setattr(player, cd_key, now + max(1.0, cd))
    await _show_momentum(player)


async def do_cleave(player, args: list):
    """Cleave - hit all enemies."""
    c = Config.COLORS
    
    if not player.is_fighting and not args:
        await player.send("You aren't fighting anyone!")
        return
    
    if not player.is_fighting and args:
        target = player.find_target_in_room(' '.join(args))
        if not target:
            await player.send("Cleave whom?")
            return
        from combat import CombatHandler
        await CombatHandler.start_combat(player, target)
    
    now = time.time()
    cd_key = 'cleave_cd'
    if now < getattr(player, cd_key, 0):
        remaining = getattr(player, cd_key, 0) - now
        await player.send(f"{c['yellow']}Cleave is on cooldown ({remaining:.1f}s).{c['reset']}")
        return
    
    evo = getattr(player, 'ability_evolutions', {}).get('cleave')
    ability_display = evo or 'cleave'
    
    # Determine multiplier and effects
    mult = 0.8
    self_bleed_pct = 0
    lifesteal_pct = 0
    ac_shred = 0
    dr_bonus = 0
    
    if evo == 'bulwark_sweep': mult = 0.8
    elif evo == 'bloodwhirl': mult = 1.2; self_bleed_pct = 0.03
    elif evo == 'surgical_cleave': mult = 1.0; ac_shred = 5
    elif evo == 'iron_tempest': mult = 1.0; dr_bonus = 10
    elif evo == 'blood_cyclone': mult = 1.5; self_bleed_pct = 0.05; lifesteal_pct = 0.20
    elif evo == 'anatomical_rend': mult = 1.2; ac_shred = 10
    elif evo == 'aegis_storm': mult = 1.2; dr_bonus = 20
    elif evo == 'deathstorm': mult = 2.0; self_bleed_pct = 0.08
    elif evo == 'grand_strategy': mult = 1.5; ac_shred = 15
    
    # Self bleed
    if self_bleed_pct > 0:
        self_dmg = berserker_self_damage(player, self_bleed_pct)
        await player.send(f"{c['red']}The exertion costs you {self_dmg} HP!{c['reset']}")
    
    unstoppable_triggered = apply_momentum(player, 'cleave')
    if unstoppable_triggered:
        await player.send(f"{c['bright_yellow']}*** UNSTOPPABLE! ***{c['reset']}")
    
    increment_usage(player, 'cleave')
    
    # Hit all enemies
    targets = [ch for ch in player.room.characters
               if ch != player and ch.is_alive and not hasattr(ch, 'connection')]
    
    if not targets:
        await player.send("There are no enemies to cleave!")
        cd = ABILITY_COOLDOWNS['cleave']
        setattr(player, cd_key, now + max(1.0, cd))
        return
    
    total_damage = 0
    any_killed = False
    for t in list(targets):
        base_dmg = get_weapon_damage(player)
        damage = max(1, int(base_dmg * mult))
        killed = await apply_damage_to_target(player, t, damage, ability_display.replace('_', ' '))
        total_damage += damage
        if killed:
            any_killed = True
            await handle_kill(player, t)
        elif ac_shred > 0:
            t.armor_class = getattr(t, 'armor_class', 100) + ac_shred  # Higher AC = worse
            await player.send(f"{c['yellow']}{t.name}'s armor is shredded!{c['reset']}")
    
    # Lifesteal
    if lifesteal_pct > 0 and total_damage > 0:
        heal = int(total_damage * lifesteal_pct)
        player.hp = min(player.max_hp, player.hp + heal)
        await player.send(f"{c['bright_green']}You drain {heal} HP from your enemies!{c['reset']}")
    
    # DR bonus
    if dr_bonus > 0:
        player.warrior_dr_bonus = dr_bonus
        player.warrior_dr_rounds = 2 if evo != 'aegis_storm' else 3
        await player.send(f"{c['cyan']}You gain {dr_bonus}% damage reduction!{c['reset']}")
    
    # Deathstorm heal on kill
    if evo == 'deathstorm' and any_killed:
        heal = int(player.max_hp * 0.25)
        player.hp = min(player.max_hp, player.hp + heal)
        await player.send(f"{c['bright_green']}The carnage heals you for {heal} HP!{c['reset']}")
    
    cd = ABILITY_COOLDOWNS['cleave']
    cd *= (1.0 - get_momentum_speed_reduction(player))
    setattr(player, cd_key, now + max(1.0, cd))
    await _show_momentum(player)


async def do_charge(player, args: list):
    """Charge - rush to target."""
    c = Config.COLORS
    
    if not args:
        await player.send("Charge whom?")
        return
    
    target = player.find_target_in_room(' '.join(args))
    if not target:
        await player.send("You don't see them here.")
        return
    
    if player.is_fighting and player.fighting == target:
        await player.send(f"{c['yellow']}You're already fighting {target.name}!{c['reset']}")
        return
    
    now = time.time()
    cd_key = 'charge_cd'
    if now < getattr(player, cd_key, 0):
        remaining = getattr(player, cd_key, 0) - now
        await player.send(f"{c['yellow']}Charge is on cooldown ({remaining:.1f}s).{c['reset']}")
        return
    
    evo = getattr(player, 'ability_evolutions', {}).get('charge')
    ability_display = evo or 'charge'
    base_dmg = get_weapon_damage(player)
    mult = 1.5
    self_cost_pct = 0
    temp_armor = 0
    
    if evo == 'ironclad_advance': temp_armor = 20
    elif evo == 'reckless_charge': mult = 3.0; self_cost_pct = 0.10
    elif evo == 'flanking_rush': mult = 1.5
    elif evo == 'juggernaut': temp_armor = 30
    elif evo == 'death_from_above': mult = 4.0; self_cost_pct = 0.15
    elif evo == 'tactical_insertion': mult = 2.0
    elif evo == 'unstoppable_force': temp_armor = 40
    elif evo == 'extinction_event': mult = 5.0; self_cost_pct = 0.20
    elif evo == 'checkmate': mult = 3.0
    
    if self_cost_pct > 0:
        self_dmg = berserker_self_damage(player, self_cost_pct)
        await player.send(f"{c['red']}The charge costs you {self_dmg} HP!{c['reset']}")
    
    # Start combat if not already fighting
    if not player.is_fighting:
        from combat import CombatHandler
        await CombatHandler.start_combat(player, target)
    else:
        player.fighting = target
    
    unstoppable_triggered = apply_momentum(player, 'charge')
    if unstoppable_triggered:
        await player.send(f"{c['bright_yellow']}*** UNSTOPPABLE! ***{c['reset']}")
    
    increment_usage(player, 'charge')
    
    damage = max(1, int(base_dmg * mult))
    killed = await apply_damage_to_target(player, target, damage, ability_display.replace('_', ' '))
    
    if not killed:
        # Stun
        if getattr(target, 'unstoppable_rounds', 0) <= 0:
            target.stunned_rounds = max(getattr(target, 'stunned_rounds', 0), 1)
            await player.send(f"{c['bright_yellow']}{target.name} is stunned!{c['reset']}")
        
        # Temp armor
        if temp_armor > 0:
            player.warrior_temp_armor = temp_armor
            player.warrior_temp_armor_rounds = 3
            await player.send(f"{c['cyan']}You gain +{temp_armor} temporary armor!{c['reset']}")
        
        # Disorient (flanking/tactical/checkmate)
        if evo in ('flanking_rush', 'tactical_insertion', 'checkmate'):
            rounds = 1 if evo == 'flanking_rush' else (2 if evo == 'tactical_insertion' else 3)
            target.disoriented_rounds = rounds
            await player.send(f"{c['yellow']}{target.name} is disoriented for {rounds} rounds!{c['reset']}")
    else:
        await handle_kill(player, target)
    
    cd = ABILITY_COOLDOWNS['charge']
    cd *= (1.0 - get_momentum_speed_reduction(player))
    setattr(player, cd_key, now + max(1.0, cd))
    await _show_momentum(player)


async def do_rally(player, args: list):
    """Rally - self buff/recovery."""
    c = Config.COLORS
    
    now = time.time()
    cd_key = 'rally_cd'
    if now < getattr(player, cd_key, 0):
        remaining = getattr(player, cd_key, 0) - now
        await player.send(f"{c['yellow']}Rally is on cooldown ({remaining:.1f}s).{c['reset']}")
        return
    
    evo = getattr(player, 'ability_evolutions', {}).get('rally')
    ability_display = evo or 'rally'
    
    unstoppable_triggered = apply_momentum(player, 'rally')
    if unstoppable_triggered:
        await player.send(f"{c['bright_yellow']}*** UNSTOPPABLE! ***{c['reset']}")
    
    increment_usage(player, 'rally')
    
    heal_pct = 0.15
    self_cost_pct = 0
    damage_buff = 0
    damage_buff_rounds = 0
    group_heal = False
    dr_bonus = 0
    taunt = False
    
    if evo == 'stand_your_ground': heal_pct = 0.20; taunt = True
    elif evo == 'blood_frenzy': heal_pct = 0; self_cost_pct = 0.10; damage_buff = 30; damage_buff_rounds = 3
    elif evo == 'battle_orders': heal_pct = 0.10; group_heal = True
    elif evo == 'immovable_object': heal_pct = 0.30; taunt = True; dr_bonus = 25
    elif evo == 'berserker_rage': heal_pct = 0; self_cost_pct = 0.15; damage_buff = 50; damage_buff_rounds = 3
    elif evo == 'inspiring_command': heal_pct = 0.15; group_heal = True; damage_buff = 10; damage_buff_rounds = 3
    elif evo == 'eternal_guardian': heal_pct = 0.40; taunt = True; dr_bonus = 35
    elif evo == 'war_incarnate': heal_pct = 0; self_cost_pct = 0.20; damage_buff = 75; damage_buff_rounds = 4
    elif evo == 'supreme_command': heal_pct = 0.20; group_heal = True; damage_buff = 15; damage_buff_rounds = 4; dr_bonus = 10
    
    # Self-cost
    if self_cost_pct > 0:
        self_dmg = berserker_self_damage(player, self_cost_pct)
        await player.send(f"{c['red']}The rally costs you {self_dmg} HP!{c['reset']}")
    
    # Heal
    if heal_pct > 0:
        heal = int(player.max_hp * heal_pct)
        player.hp = min(player.max_hp, player.hp + heal)
        await player.send(f"{c['bright_green']}You rally and heal {heal} HP!{c['reset']}")
        
        if group_heal and player.group:
            for member in player.group.members:
                if member != player and member.room == player.room:
                    gheal = int(member.max_hp * heal_pct)
                    member.hp = min(member.max_hp, member.hp + gheal)
                    if hasattr(member, 'send'):
                        await member.send(f"{c['bright_green']}{player.name}'s rally heals you for {gheal} HP!{c['reset']}")
    
    # Damage buff
    if damage_buff > 0:
        player.warrior_damage_buff = damage_buff
        player.warrior_damage_buff_rounds = damage_buff_rounds
        await player.send(f"{c['bright_yellow']}+{damage_buff}% damage for {damage_buff_rounds} rounds!{c['reset']}")
        
        if group_heal and damage_buff > 0 and player.group:
            for member in player.group.members:
                if member != player and member.room == player.room:
                    member.warrior_damage_buff = damage_buff
                    member.warrior_damage_buff_rounds = damage_buff_rounds
    
    # DR
    if dr_bonus > 0:
        player.warrior_dr_bonus = dr_bonus
        player.warrior_dr_rounds = 2
        await player.send(f"{c['cyan']}+{dr_bonus}% damage reduction!{c['reset']}")
    
    # Taunt
    if taunt and player.room:
        import brain
        if brain.on('threat'):
            for mob in brain.enemies_of(player):     # those fighting your side (brain/)
                brain.taunted(mob, player, 6.0)
        else:
            for mob in player.room.characters:
                if mob != player and hasattr(mob, 'fighting') and not hasattr(mob, 'connection'):
                    mob.fighting = player
        await player.send(f"{c['yellow']}You taunt all enemies!{c['reset']}")
    
    # Eternal guardian death save
    if evo == 'eternal_guardian':
        player.warrior_death_save_rounds = 3
        await player.send(f"{c['bright_cyan']}If you would die in the next 3 rounds, you survive with 1 HP!{c['reset']}")
    
    cd = ABILITY_COOLDOWNS['rally']
    cd *= (1.0 - get_momentum_speed_reduction(player))
    setattr(player, cd_key, now + max(1.0, cd))
    await _show_momentum(player)


async def do_execute(player, args: list):
    """Execute - finisher on low HP targets."""
    c = Config.COLORS
    
    if not player.is_fighting:
        if args:
            target = player.find_target_in_room(' '.join(args))
            if not target:
                await player.send("Execute whom?")
                return
            # Check HP threshold before starting combat
            hp_pct = (target.hp / target.max_hp) * 100 if target.max_hp > 0 else 100
            if hp_pct > 25:
                await player.send(f"{c['yellow']}{target.name} must be below 25% HP to execute!{c['reset']}")
                return
            from combat import CombatHandler
            await CombatHandler.start_combat(player, target)
        else:
            await player.send("You aren't fighting anyone!")
            return
    
    target = player.fighting
    if not target or not target.is_alive:
        return
    
    hp_pct = (target.hp / target.max_hp) * 100 if target.max_hp > 0 else 100
    if hp_pct > 25:
        await player.send(f"{c['yellow']}{target.name} must be below 25% HP to execute! (Currently {hp_pct:.0f}%){c['reset']}")
        return
    
    now = time.time()
    cd_key = 'execute_cd'
    if now < getattr(player, cd_key, 0):
        remaining = getattr(player, cd_key, 0) - now
        await player.send(f"{c['yellow']}Execute is on cooldown ({remaining:.1f}s).{c['reset']}")
        return
    
    evo = getattr(player, 'ability_evolutions', {}).get('execute')
    ability_display = evo or 'execute'
    base_dmg = get_weapon_damage(player)
    mult = 3.0
    
    if evo == 'merciful_end': mult = 3.0
    elif evo == 'overkill': mult = 4.0
    elif evo == 'subjugate': mult = 3.0
    elif evo == 'righteous_execution': mult = 4.0
    elif evo == 'massacre': mult = 5.0
    elif evo == 'total_domination': mult = 4.0
    elif evo == 'divine_judgment': mult = 5.0
    elif evo == 'annihilation': mult = 6.0
    elif evo == 'absolute_authority': mult = 5.0
    
    unstoppable_triggered = apply_momentum(player, 'execute')
    if unstoppable_triggered:
        await player.send(f"{c['bright_yellow']}*** UNSTOPPABLE! ***{c['reset']}")
    
    increment_usage(player, 'execute')
    
    damage = max(1, int(base_dmg * mult))
    target_max_hp = target.max_hp
    killed = await apply_damage_to_target(player, target, damage, ability_display.replace('_', ' '))
    
    if killed:
        # Post-kill effects
        if evo in ('merciful_end', 'righteous_execution', 'divine_judgment'):
            shield_pcts = {'merciful_end': 0.20, 'righteous_execution': 0.30, 'divine_judgment': 0.40}
            shield_amount = int(target_max_hp * shield_pcts.get(evo, 0.20))
            player.warrior_shield = getattr(player, 'warrior_shield', 0) + shield_amount
            player.warrior_shield_rounds = 5
            await player.send(f"{c['cyan']}You gain a shield for {shield_amount}!{c['reset']}")
        
        if evo in ('overkill', 'massacre', 'annihilation'):
            excess = damage - target.max_hp  # rough approximation
            splash_pcts = {'overkill': 0.50, 'massacre': 0.75, 'annihilation': 1.00}
            splash_pct = splash_pcts.get(evo, 0.50)
            if excess > 0:
                splash_dmg = int(excess * splash_pct)
                for mob in list(player.room.characters):
                    if mob != player and mob.is_alive and not hasattr(mob, 'connection') and mob != target:
                        mob_killed = await mob.take_damage(splash_dmg, player)
                        await player.send(f"{c['red']}Splash damage hits {mob.name} for {splash_dmg}!{c['reset']}")
                        if mob_killed:
                            await handle_kill(player, mob)
        
        await handle_kill(player, target)
    
    cd = ABILITY_COOLDOWNS['execute']
    cd *= (1.0 - get_momentum_speed_reduction(player))
    setattr(player, cd_key, now + max(1.0, cd))
    await _show_momentum(player)


async def _show_momentum(player):
    """Show momentum status after ability use."""
    c = Config.COLORS
    momentum = getattr(player, 'momentum', 0)
    bar = get_momentum_bar(momentum)
    doctrine = getattr(player, 'war_doctrine', None)
    
    doctrine_bonus = ""
    if doctrine == 'iron_wall':
        dr = momentum * 2
        doctrine_bonus = f" DR:{dr}%"
    elif doctrine == 'berserker':
        ls = momentum * 2
        doctrine_bonus = f" LS:{ls}%"
    elif doctrine == 'warlord':
        ext = momentum // 3
        if ext > 0:
            doctrine_bonus = f" Debuff:+{ext}r"
    
    await player.send(f"{c['bright_yellow']}{bar}{doctrine_bonus}{c['reset']}")


# ============================================================================
# COMMAND HANDLERS (called from commands.py)
# ============================================================================

async def cmd_doctrine(player, args: list):
    """Show current doctrine and progression."""
    c = Config.COLORS
    doctrine = getattr(player, 'war_doctrine', None)
    
    if not doctrine:
        await player.send(f"{c['yellow']}You have not sworn to a War Doctrine.{c['reset']}")
        await player.send(f"{c['white']}Use 'swear <doctrine>' to choose: iron_wall, berserker, warlord{c['reset']}")
        await player.send(f"{c['white']}Type 'help doctrine' for details on each path.{c['reset']}")
        return
    
    doc_info = DOCTRINES[doctrine]
    momentum = getattr(player, 'momentum', 0)
    
    await player.send(f"\r\n{c['bright_cyan']}═══ War Doctrine: {doc_info['name']} ═══{c['reset']}")
    await player.send(f"{c['white']}{doc_info['description']}{c['reset']}")
    await player.send(f"{c['bright_yellow']}{get_momentum_bar(momentum)}{c['reset']}")
    await player.send(f"")
    await player.send(f"{c['cyan']}Abilities:{c['reset']}")
    
    usage = getattr(player, 'ability_usage', {})
    evolutions = getattr(player, 'ability_evolutions', {})
    
    for ability in WARRIOR_ABILITIES:
        uses = usage.get(ability, 0)
        evo = evolutions.get(ability)
        tier = get_current_evolution_tier(player, ability)
        next_thresh = get_next_evolution_threshold(player, ability)
        
        evo_display = f" → {c['bright_green']}{evo}{c['reset']}" if evo else ""
        
        if next_thresh:
            progress = f"({uses}/{next_thresh})"
            if uses >= next_thresh:
                progress = f"{c['bright_yellow']}READY TO EVOLVE!{c['reset']}"
        else:
            progress = f"({uses} uses, MAXED)"
        
        tier_stars = '★' * tier + '☆' * (3 - tier)
        await player.send(f"  {c['white']}{ability:<8}{c['reset']} [{tier_stars}] {progress}{evo_display}")
    
    await player.send(f"\r\n{c['white']}Use 'evolve' to see evolution details, 'evolve <ability>' to evolve.{c['reset']}")


async def cmd_swear(player, args: list):
    """Swear to a war doctrine."""
    c = Config.COLORS
    
    if not args:
        await player.send(f"{c['yellow']}Swear to which doctrine? iron_wall, berserker, or warlord{c['reset']}")
        return
    
    doctrine = args[0].lower()
    if doctrine not in DOCTRINES:
        await player.send(f"{c['red']}Unknown doctrine. Choose: iron_wall, berserker, warlord{c['reset']}")
        return
    
    current = getattr(player, 'war_doctrine', None)
    
    if current == doctrine:
        await player.send(f"{c['yellow']}You are already sworn to {DOCTRINES[doctrine]['name']}.{c['reset']}")
        return
    
    if current:
        # Check for confirmation
        if not getattr(player, '_swear_confirm', None) == doctrine:
            await player.send(f"{c['bright_red']}WARNING: Switching doctrines resets ALL ability evolutions!{c['reset']}")
            await player.send(f"{c['yellow']}Type 'swear {doctrine}' again to confirm.{c['reset']}")
            player._swear_confirm = doctrine
            return
        
        # Reset evolutions
        player.ability_evolutions = {a: None for a in WARRIOR_ABILITIES}
        player._swear_confirm = None
        await player.send(f"{c['red']}Your ability evolutions have been reset.{c['reset']}")
    
    player.war_doctrine = doctrine
    doc_info = DOCTRINES[doctrine]
    
    await player.send(f"\r\n{c['bright_yellow']}═══════════════════════════════════════════{c['reset']}")
    await player.send(f"{c['bright_yellow']}  You swear the oath of {doc_info['name']}!{c['reset']}")
    await player.send(f"{c['bright_yellow']}═══════════════════════════════════════════{c['reset']}")
    await player.send(f"{c['white']}\"{doc_info['flavor']}\"{c['reset']}")
    await player.send(f"{c['cyan']}Momentum bonus: {doc_info['momentum_bonus']}{c['reset']}")


async def cmd_evolve(player, args: list):
    """Show or perform ability evolution."""
    c = Config.COLORS
    doctrine = getattr(player, 'war_doctrine', None)
    
    if not doctrine:
        await player.send(f"{c['yellow']}You must swear a doctrine first. Use 'swear <doctrine>'.{c['reset']}")
        return
    
    usage = getattr(player, 'ability_usage', {})
    evolutions = getattr(player, 'ability_evolutions', {})
    
    if not args:
        # Show all evolution status
        await player.send(f"\r\n{c['bright_cyan']}═══ Ability Evolution ({DOCTRINES[doctrine]['name']}) ═══{c['reset']}")
        
        for ability in WARRIOR_ABILITIES:
            uses = usage.get(ability, 0)
            evo = evolutions.get(ability)
            tier = get_current_evolution_tier(player, ability)
            next_thresh = get_next_evolution_threshold(player, ability)
            
            await player.send(f"\r\n  {c['bright_white']}{ability.upper()}{c['reset']} (Tier {tier}/3, {uses} uses)")
            
            if evo:
                await player.send(f"    Current: {c['bright_green']}{evo}{c['reset']}")
            
            if next_thresh:
                if uses >= next_thresh:
                    await player.send(f"    {c['bright_yellow']}★ READY TO EVOLVE! Use 'evolve {ability}' ★{c['reset']}")
                else:
                    await player.send(f"    Next evolution at {next_thresh} uses ({uses}/{next_thresh})")
                    # Preview next evolution
                    evo_data = EVOLUTION_TREE.get(ability, {}).get(next_thresh, {}).get(doctrine)
                    if evo_data:
                        await player.send(f"    Preview: {c['cyan']}{evo_data[0]}{c['reset']} - {evo_data[1]}")
            else:
                await player.send(f"    {c['bright_green']}FULLY EVOLVED{c['reset']}")
        return
    
    # Evolve specific ability
    ability = args[0].lower()
    if ability not in WARRIOR_ABILITIES:
        await player.send(f"{c['red']}Unknown ability. Choose: {', '.join(WARRIOR_ABILITIES)}{c['reset']}")
        return
    
    if not can_evolve(player, ability):
        uses = usage.get(ability, 0)
        next_thresh = get_next_evolution_threshold(player, ability)
        if next_thresh is None:
            await player.send(f"{c['yellow']}{ability} is already fully evolved.{c['reset']}")
        else:
            await player.send(f"{c['yellow']}{ability} needs {next_thresh} uses to evolve ({uses}/{next_thresh}).{c['reset']}")
        return
    
    # Perform evolution
    next_thresh = get_next_evolution_threshold(player, ability)
    evo_data = EVOLUTION_TREE.get(ability, {}).get(next_thresh, {}).get(doctrine)
    
    if not evo_data:
        await player.send(f"{c['red']}No evolution available for {ability} under {doctrine}.{c['reset']}")
        return
    
    evo_name, evo_desc = evo_data
    
    if not hasattr(player, 'ability_evolutions'):
        player.ability_evolutions = {a: None for a in WARRIOR_ABILITIES}
    
    player.ability_evolutions[ability] = evo_name
    
    await player.send(f"\r\n{c['bright_yellow']}═══════════════════════════════════════════════════{c['reset']}")
    await player.send(f"{c['bright_yellow']}  ★ ABILITY EVOLVED! ★{c['reset']}")
    await player.send(f"{c['bright_yellow']}═══════════════════════════════════════════════════{c['reset']}")
    await player.send(f"{c['white']}  {ability.upper()} → {c['bright_green']}{evo_name}{c['reset']}")
    await player.send(f"{c['cyan']}  {evo_desc}{c['reset']}")
    await player.send(f"{c['bright_yellow']}═══════════════════════════════════════════════════{c['reset']}")

    # Achievement: Doctrine Devoted
    try:
        from achievements import AchievementManager
        await AchievementManager.check_doctrine_devoted(player)
    except Exception:
        pass


# ============================================================================
# SAVE/LOAD HELPERS
# ============================================================================

def get_save_data(player) -> dict:
    """Get warrior-specific data for save."""
    return {
        'war_doctrine': getattr(player, 'war_doctrine', None),
        'momentum': getattr(player, 'momentum', 0),
        'ability_usage': getattr(player, 'ability_usage', {a: 0 for a in WARRIOR_ABILITIES}),
        'ability_evolutions': getattr(player, 'ability_evolutions', {a: None for a in WARRIOR_ABILITIES}),
        'last_warrior_ability': getattr(player, 'last_warrior_ability', None),
        'unstoppable_rounds': getattr(player, 'unstoppable_rounds', 0),
    }


def load_save_data(player, data: dict):
    """Load warrior-specific data from save."""
    player.war_doctrine = data.get('war_doctrine', None)
    player.momentum = data.get('momentum', 0)
    player.ability_usage = data.get('ability_usage', {a: 0 for a in WARRIOR_ABILITIES})
    player.ability_evolutions = data.get('ability_evolutions', {a: None for a in WARRIOR_ABILITIES})
    player.last_warrior_ability = data.get('last_warrior_ability', None)
    player.unstoppable_rounds = data.get('unstoppable_rounds', 0)


def init_warrior_attrs(player):
    """Initialize warrior attributes on a player."""
    if not hasattr(player, 'war_doctrine'):
        player.war_doctrine = None
    if not hasattr(player, 'momentum'):
        player.momentum = 0
    if not hasattr(player, 'ability_usage'):
        player.ability_usage = {a: 0 for a in WARRIOR_ABILITIES}
    if not hasattr(player, 'ability_evolutions'):
        player.ability_evolutions = {a: None for a in WARRIOR_ABILITIES}
    if not hasattr(player, 'last_warrior_ability'):
        player.last_warrior_ability = None
    if not hasattr(player, 'unstoppable_rounds'):
        player.unstoppable_rounds = 0
    if not hasattr(player, 'warrior_shield'):
        player.warrior_shield = 0
    if not hasattr(player, 'warrior_shield_rounds'):
        player.warrior_shield_rounds = 0
