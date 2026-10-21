"""
Mob Combat AI System
====================
Intelligent combat behaviors for mobs based on type, flags, and keywords.
Runs once per combat round for each fighting mob via mob_ai_tick().

AI Types (checked via flags or inferred from name/keywords):
- MOB_CASTER: Periodically casts offensive spells, heals self, buffs
- MOB_BOSS: Special ability rotation with cooldowns (AoE, enrage, summon, fear)
- MOB_PACK: Calls nearby same-type mobs for help when attacked
- MOB_HEALER: Prioritizes healing wounded allies in the room
- MOB_COWARD: Flees at low HP
"""

import random
import time
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mobs import Mobile

logger = logging.getLogger('Misthollow.MobAI')

# ---------------------------------------------------------------------------
# Flag / keyword classification
# ---------------------------------------------------------------------------

CASTER_KEYWORDS = {'mage', 'wizard', 'sorcerer', 'warlock', 'shaman', 'necromancer',
                   'witch', 'conjurer', 'enchanter', 'magus', 'druid'}
HEALER_KEYWORDS = {'priest', 'priestess', 'cleric', 'healer', 'acolyte', 'monk',
                   'bishop', 'chaplain', 'medic'}
PACK_KEYWORDS = {'wolf', 'wolves', 'rat', 'rats', 'goblin', 'kobold', 'gnoll',
                 'orc', 'hyena', 'jackal', 'bandit', 'brigand', 'pirate'}
COWARD_KEYWORDS = {'rabbit', 'deer', 'squirrel', 'chicken', 'fox', 'cat',
                   'mouse', 'fawn', 'sparrow', 'villager', 'peasant', 'beggar'}
GUARDED_KEYWORDS = {'guard', 'cityguard', 'knight', 'soldier', 'sentinel', 'sentry',
                    'legionnaire', 'defender', 'golem', 'turtle', 'crab', 'warden'}
BIG_KEYWORDS = {'ogre', 'troll', 'giant', 'bear', 'golem', 'minotaur', 'yeti',
                'cyclops', 'behemoth', 'ettin', 'juggernaut'}
TRAPSMITH_KEYWORDS = {'kobold', 'trapper', 'tinker', 'sapper', 'saboteur', 'poacher'}
ARCHER_KEYWORDS = {'archer', 'bowman', 'bowmen', 'crossbowman', 'marksman', 'longbowman', 'slinger'}
SUPPORT_KEYWORDS = {'bard', 'minstrel', 'drummer', 'skald', 'chanter', 'herald'}
AMBUSH_KEYWORDS = {'spider', 'stalker', 'lurker', 'assassin', 'panther', 'shadow',
                   'ambusher', 'creeper', 'widow'}


def _has_flag(mob, flag: str) -> bool:
    return flag in getattr(mob, 'flags', set())


def _name_lower(mob) -> str:
    # its keywords too, when it is called by its description (mobs.Mobile.said_name)
    return f"{getattr(mob, 'keyword_name', '') or ''} {getattr(mob, 'name', '')}".strip().lower()


def _keywords_set(mob) -> set:
    return set(getattr(mob, 'keywords', []))


def classify_mob(mob) -> set:
    """Return a set of AI role strings for the mob. Cached on ai_state."""
    ai_state = getattr(mob, 'ai_state', None)
    if ai_state is None:
        mob.ai_state = {}
        ai_state = mob.ai_state

    cached = ai_state.get('_ai_roles')
    if cached is not None:
        return cached

    # roles a population file gives it ("ai": {"roles": [...]}) are its roles; a bosses.py Boss
    # still runs its own rotation on top
    data_roles = (getattr(mob, 'ai_data', None) or {}).get('roles')
    if data_roles:
        roles = {str(r) for r in data_roles}
        try:
            from bosses import Boss
            if isinstance(mob, Boss):
                roles.add('scripted')
        except Exception:
            pass
        ai_state['_ai_roles'] = roles
        return roles

    roles = set()
    flags = getattr(mob, 'flags', set())
    name = _name_lower(mob)
    kws = _keywords_set(mob)
    name_words = set(name.split())
    all_words = kws | name_words

    # bosses.py Boss instances run their own telegraph/cast rotation via
    # Boss.process_ai — giving them the mob_ai 'boss' role too made two boss
    # ability systems fire on one mob
    try:
        from bosses import Boss
        is_boss_class = isinstance(mob, Boss)
    except Exception:
        is_boss_class = False

    # Explicit flags take priority
    if 'mob_caster' in flags or 'caster' in flags:
        roles.add('caster')
    # a boss's add (bosses.Boss._spawn_adds) is an add, whatever its file says: never the boss kit
    # on top (its own minions, slams and fear)
    is_add = getattr(mob, 'summoned_by', None) is not None
    if ('mob_boss' in flags or 'boss' in flags) and not is_boss_class and not is_add:
        roles.add('boss')
    if is_boss_class:
        roles.add('scripted')     # bosses.py's own rotation: never the bruiser's blows on top
    if 'mob_pack' in flags or 'pack' in flags:
        roles.add('pack')
    if 'mob_healer' in flags or 'healer_ai' in flags:
        roles.add('healer')
    if 'mob_coward' in flags:
        roles.add('coward')

    # Legacy special-attack mobs (poison bite, fire breath, paralyzing touch,
    # troll regen) — these fired from the old per-tick combat_ai; now owned here
    special = getattr(mob, 'special', None)
    if special in ('poison', 'firebreath', 'paralyze', 'regenerate') \
            or 'poison' in flags \
            or any(w in name for w in ('dragon', 'troll', 'spider', 'snake')):
        roles.add('legacy_special')

    # Disciplined/armored fighters periodically raise a GUARD that turns
    # blades aside — broken by a bash or kick (guarded-mob counterplay)
    if any(w in all_words for w in GUARDED_KEYWORDS) or 'shield' in name:
        roles.add('guarded')

    # Trapsmiths rig snares in their lairs while idle; ambushers strike from
    # cold with a devastating opener
    if all_words & TRAPSMITH_KEYWORDS:
        roles.add('trapsmith')
    if all_words & AMBUSH_KEYWORDS:
        roles.add('ambusher')

    # Infer from keywords / name
    if not roles & {'caster'}:
        if all_words & CASTER_KEYWORDS:
            roles.add('caster')
        elif getattr(mob, 'special', None) in ('necromancer', 'shaman', 'druid'):
            roles.add('caster')
    if not roles & {'healer'}:
        if all_words & HEALER_KEYWORDS:
            roles.add('healer')
    if not roles & {'pack'}:
        if all_words & PACK_KEYWORDS:
            roles.add('pack')
    if not roles & {'coward'}:
        if all_words & COWARD_KEYWORDS:
            roles.add('coward')
        elif 'wimpy' in flags and getattr(mob, 'level', 99) <= 8:
            roles.add('coward')

    # archers shoot from afar and supporters hang back (combat_range.ROLE_RANGE): with the brain's
    # tactics on, read from their words or a bow in hand
    import brain
    if brain.on('tactics'):
        try:
            import combat_range
            bow = combat_range.wielded_kind(mob) in combat_range.WEAPON_RANGE
        except Exception:
            bow = False
        if all_words & ARCHER_KEYWORDS or bow:
            roles.add('archer')
        if all_words & SUPPORT_KEYWORDS:
            roles.add('support')

    # Boss by HP threshold (never for bosses.py Boss instances — see above — nor for a marquee
    # quest's creatures: their health is sized to the party hunting them (marquee_scale), and the
    # boss kit — a slam on everyone in the room every 8 s, fear, adds — would ride along with it)
    if not roles & {'boss'} and not is_boss_class and not is_add and getattr(mob, 'marquee_tag', None) is None:
        if getattr(mob, 'max_hp', 0) > 5000:
            roles.add('boss')
        elif getattr(mob, 'is_boss', False):
            roles.add('boss')

    ai_state['_ai_roles'] = roles
    return roles


# ---------------------------------------------------------------------------
# Caster AI
# ---------------------------------------------------------------------------

CASTER_OFFENSIVE = [
    ('fireball',       'hurls a crackling fireball at',      2.5, 30),
    ('lightning_bolt',  'calls down lightning upon',          2.0, 25),
    ('ice_storm',      'conjures a storm of ice shards at',  1.8, 20),
    ('shadow_bolt',    'fires a bolt of shadow at',          1.5, 15),
    ('magic_missile',  'launches magic missiles at',         1.2, 10),
]

CASTER_DEBUFFS = [
    ('blindness', 'gestures and a blinding flash engulfs', 'blinded_rounds', 2),
    ('weaken',    'whispers a curse of weakness upon',     None, 0),
    ('slow',      'weaves a spell of lethargy around',     'stunned_rounds', 1),
]


def _silenced(mob):
    """Silenced (Chord of Disruption) or deafened (a bard's symphony): no spells."""
    return bool((getattr(mob, 'affect_flags', None) or set()) & {'silenced', 'deafened'})


async def _caster_tick(mob, target):
    """Caster mob AI: heal self, buff, or offensive spell."""
    if mob.mana < 10 or _silenced(mob):
        return False
    import brain
    if brain.on('tactics'):
        # its ward is a real affect that runs out, once a fight (brain/cast.py); heals and spells
        # are declared, but for a trivial fight's quick instant ones below
        from brain import cast
        if await cast.ward(mob, brain.of(mob)):
            return True
        if not _intent_exempt(mob, target):
            return False
        mob.ai_state['buffed'] = True        # (the ward stands for the old, permanent buff)

    c = mob.config.COLORS
    now = time.time()
    cd = mob.ai_state.setdefault('spell_cd', 0)
    if now < cd:
        return False

    hp_pct = mob.hp / max(1, mob.max_hp)

    # Self-heal at <40% HP
    if hp_pct < 0.4 and mob.mana >= 25:
        heal = random.randint(mob.level * 2, mob.level * 5)
        mob.hp = min(mob.max_hp, mob.hp + heal)
        mob.mana -= 25
        mob.ai_state['spell_cd'] = now + 6
        await mob.room.send_to_room(
            f"{c['bright_cyan']}{mob.name} chants a healing incantation and wounds close! [+{heal} HP]{c['reset']}"
        )
        return True

    # Buff self once per fight
    if not mob.ai_state.get('buffed') and mob.mana >= 15:
        mob.ai_state['buffed'] = True
        mob.ai_state['spell_cd'] = now + 4
        mob.mana -= 15
        # Give a minor buff
        mob.armor_class -= 10
        mob.damroll += 2
        await mob.room.send_to_room(
            f"{c['bright_magenta']}{mob.name} murmurs arcane words and a shimmering aura surrounds them!{c['reset']}"
        )
        return True

    # Offensive/debuff casts are DECLARED an round ahead (declare_intents) so
    # players can react; this direct path only runs for trivial fights that
    # bypass the intent system entirely.
    if not _intent_exempt(mob, target):
        return False

    # 60% chance to cast offensive spell (was 35% at 10Hz via the old
    # combat_ai path — this runs once per 4s round now)
    if random.randint(1, 100) > 60:
        return False

    # Debuff (20% of casts, if target not already debuffed)
    if random.randint(1, 100) <= 20 and CASTER_DEBUFFS:
        deb = random.choice(CASTER_DEBUFFS)
        if deb[2] and getattr(target, deb[2], 0) <= 0:
            mob.ai_state['spell_cd'] = now + 5
            await _cast_debuff(mob, target, deb)
            return True

    # Offensive spell
    for spell in CASTER_OFFENSIVE:
        if mob.mana >= spell[3]:
            mob.ai_state['spell_cd'] = now + 4
            await _cast_offensive(mob, target, spell)
            return True

    return False


async def _cast_debuff(mob, target, deb):
    """Execute a caster debuff (shared by the instant path and intent resolve)."""
    spell_name, msg, attr, val = deb
    c = mob.config.COLORS
    mob.mana = max(0, mob.mana - 15)
    if attr and getattr(target, attr, 0) <= 0:
        # brace = standing firm: resists the stun/blind family
        if attr in ('stunned_rounds', 'blinded_rounds') and _braced(target):
            await mob.room.send_to_room(
                f"{c['cyan']}{getattr(target, 'name', 'Someone')} stands braced — "
                f"the {spell_name.replace('_', ' ')} washes over them harmlessly!{c['reset']}"
            )
            return
        setattr(target, attr, val)
    await mob.room.send_to_room(
        f"{c['bright_magenta']}{mob.name} {msg} {target.name}!{c['reset']}"
    )
    if hasattr(target, 'send'):
        await target.send(f"{c['yellow']}You feel the effects of {spell_name.replace('_', ' ')}!{c['reset']}")


async def _cast_offensive(mob, target, spell):
    """Execute a caster attack spell (shared by the instant path and intent resolve)."""
    spell_name, msg, mult, mana_cost = spell
    c = mob.config.COLORS
    base_dmg = random.randint(mob.level, mob.level * 3)
    damage = int(base_dmg * mult)
    # A declared spell is meant to be ANSWERED (interrupt) or survived once, not to
    # end the fight from above half health: progression-01's caster tier had a
    # "Moderate" level-12 mage fireballing a level-10 warrior for 82-90 on 73-82 HP.
    # Non-boss casters cap a single spell at 60% of a player's max HP, after the
    # same toughness mitigation a heavy blow gets; bosses keep their full numbers.
    if hasattr(target, 'send') and not getattr(mob, 'is_boss', False) and 'boss' not in (getattr(mob, 'flags', None) or []):
        try:
            from combat import CombatHandler
            damage = CombatHandler.mitigate_incoming(target, damage)
        except Exception:
            pass
        damage = max(1, min(damage, int(getattr(target, 'max_hp', damage) * 0.6)))
    # it burns, freezes or shocks as its school: what a worn resistance answers to
    import combat_range
    school = combat_range.harm_school(spell_name)
    mob.mana = max(0, mob.mana - mana_cost)
    # Mirrorward (spells.py, spell_reflect): the spell turns back on its caster, and the ward is spent
    if 'spell_reflect' in (getattr(target, 'affect_flags', None) or set()):
        from affects import AffectManager
        for a in list(getattr(target, 'affects', []) or []):
            if a.applies_to == 'spell_reflect':
                AffectManager.remove_affect(target, a)
        await mob.room.send_to_room(f"{c['bright_cyan']}{target.name}'s ward flings {mob.name}'s spell back! [{damage}]{c['reset']}")
        if await mob.take_damage(damage, target, school):
            from combat import CombatHandler
            await CombatHandler.handle_death(target, mob)
        return
    # the target's spell resistance (a percent, worn gear's among it) blunts it, as a hero's spell
    resist = int(getattr(target, 'spell_resist', 0) or 0)
    if resist > 0:
        damage = max(1, int(damage * (100 - min(75, resist)) / 100))
    await mob.room.send_to_room(
        f"{c['bright_magenta']}{mob.name} {msg} {target.name}! [{damage}]{c['reset']}"
    )
    if hasattr(target, 'send'):
        await target.send(f"{c['bright_red']}{mob.name}'s spell hits you for {damage} damage!{c['reset']}")
    killed = await target.take_damage(damage, mob, school)
    if killed:
        from combat import CombatHandler
        await CombatHandler.handle_death(mob, target)
        return
    # mob spells work the terrain too: their lightning splashes the pool,
    # their fire can torch the webs — the room is nobody's ally by default
    try:
        from environment import elemental_cast
        await elemental_cast(mob, target, spell_name, mob.room)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Boss AI
# ---------------------------------------------------------------------------

BOSS_ABILITIES = [
    # (name, cooldown_secs, hp_threshold_max, handler_name)
    ('aoe_slam',     8,  1.0, '_boss_aoe_slam'),
    ('fear',         15, 1.0, '_boss_fear'),
    ('summon_adds',  25, 0.6, '_boss_summon_adds'),
    ('enrage',       0,  0.25, '_boss_enrage'),  # One-time at 25% HP
]


async def _boss_aoe_slam(mob, target):
    """AoE slam hitting all players in room."""
    c = mob.config.COLORS
    damage = random.randint(mob.level * 2, mob.level * 5)
    await mob.room.send_to_room(
        f"\n{c['bright_red']}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{c['reset']}\n"
        f"{c['bright_red']}  💥 {mob.name} SLAMS the ground!{c['reset']}\n"
        f"{c['bright_red']}  The earth trembles beneath your feet!{c['reset']}\n"
        f"{c['bright_red']}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{c['reset']}"
    )
    for char in list(mob.room.characters):
        if char == mob or not hasattr(char, 'connection'):
            continue
        actual_dmg = random.randint(int(damage * 0.7), damage)
        # declared-intent counterplay: sidestep avoids, brace halves
        actual_dmg = await _mitigate_hit(mob, char, actual_dmg)
        if actual_dmg is None:
            continue
        if hasattr(char, 'send'):
            await char.send(f"{c['bright_red']}The shockwave hits you for {actual_dmg} damage!{c['reset']}")
        killed = await char.take_damage(actual_dmg, mob)
        if killed:
            from combat import CombatHandler
            await CombatHandler.handle_death(mob, char)
    return True


async def _boss_fear(mob, target):
    """Fear: stun target for 1-2 rounds."""
    c = mob.config.COLORS
    await mob.room.send_to_room(
        f"\n{c['bright_yellow']}  😱 {mob.name} lets out a TERRIFYING roar!{c['reset']}\n"
        f"{c['bright_yellow']}  A wave of primal fear washes over the room!{c['reset']}"
    )
    for char in list(mob.room.characters):
        if char == mob or not hasattr(char, 'connection'):
            continue
        if _braced(char):
            # standing braced = steeled nerves; the fear breaks against you
            if hasattr(char, 'send'):
                await char.send(f"{c['cyan']}Braced and unshakable, you stare the terror down!{c['reset']}")
            continue
        if random.randint(1, 100) <= 60:  # 60% chance to be feared
            rounds = random.randint(1, 2)
            char.stunned_rounds = getattr(char, 'stunned_rounds', 0) + rounds
            if hasattr(char, 'send'):
                await char.send(f"{c['bright_yellow']}You are frozen with fear for {rounds} round(s)!{c['reset']}")
        else:
            if hasattr(char, 'send'):
                await char.send(f"{c['cyan']}You steel your nerves against the fear!{c['reset']}")
    return True


async def _boss_summon_adds(mob, target):
    """Summon 1-2 adds (temporary mobs) to fight."""
    c = mob.config.COLORS
    await mob.room.send_to_room(
        f"\n{c['bright_red']}  🔥 {mob.name} raises a hand and dark energy surges forth!{c['reset']}\n"
        f"{c['bright_red']}  \"Come, my minions! Destroy them!\"{c['reset']}"
    )
    # only while fewer than four of its minions still stand (as bosses.py's summons: a long fight
    # mustn't fill the room)
    mine = [a for a in getattr(mob, '_minions', []) if a.hp > 0 and a.room is not None and a in a.room.characters]
    if len(mine) >= 4:
        mob._minions = mine
        return False
    num_adds = random.randint(1, 2)
    from mobs import Mobile
    for i in range(num_adds):
        add = Mobile(0, mob.world)
        mine.append(add)
        if getattr(mob, '_dmg_scale', 1) != 1:
            add._dmg_scale = mob._dmg_scale      # weighed like its summoner's blows
        add.name = f"summoned minion"
        add.short_desc = "a summoned minion"
        add.long_desc = "A dark minion writhes with malevolent energy."
        add.keywords = ['minion', 'summoned']
        add.level = max(1, mob.level - 5)
        add.max_hp = mob.max_hp // 6
        add.hp = add.max_hp
        add.damage_dice = f"{max(1, add.level // 3)}d6+{add.level}"
        add.hitroll = add.level
        add.damroll = add.level // 2
        add.armor_class = 100 - add.level * 2
        add.flags = {'summoned'}
        add.str = 10 + add.level // 5
        add.dex = 10 + add.level // 5
        add.con = 10 + add.level // 5
        add.room = mob.room
        mob.room.characters.append(add)
        if mob.world and hasattr(mob.world, 'npcs'):
            mob.world.npcs.append(add)
        # Start fighting the target
        add.fighting = target
        add.position = 'fighting'
        await mob.room.send_to_room(
            f"{c['red']}A {add.name} materializes and attacks {target.name}!{c['reset']}"
        )
    mob._minions = mine
    return True


async def _boss_enrage(mob, target):
    """Enrage at low HP — permanent damage boost."""
    if mob.ai_state.get('enraged'):
        return False
    c = mob.config.COLORS
    mob.ai_state['enraged'] = True
    mob.enrage_multiplier = 1.5
    # Also boost hitroll
    mob.hitroll += 5
    mob.damroll += 5
    await mob.room.send_to_room(
        f"\n{c['bright_red']}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{c['reset']}\n"
        f"{c['bright_red']}  🔥🔥🔥 {mob.name} ENRAGES! 🔥🔥🔥{c['reset']}\n"
        f"{c['bright_red']}  Eyes blazing with fury, attacks grow savage!{c['reset']}\n"
        f"{c['bright_red']}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{c['reset']}"
    )
    return True

_BOSS_HANDLERS = {
    '_boss_aoe_slam': _boss_aoe_slam,
    '_boss_fear': _boss_fear,
    '_boss_summon_adds': _boss_summon_adds,
    '_boss_enrage': _boss_enrage,
}


async def _boss_tick(mob, target):
    """Boss mob AI: rotate through special abilities on cooldown.

    In real fights the damaging abilities are DECLARED a round ahead
    (declare_intents) so players can react; this direct path executes them
    only for trivial fights. Enrage (a self-buff with no counterplay) always
    fires instantly.
    """
    now = time.time()
    cooldowns = mob.ai_state.setdefault('boss_cooldowns', {})
    hp_pct = mob.hp / max(1, mob.max_hp)
    exempt = _intent_exempt(mob, target)

    for ability_name, cd_secs, hp_max, handler_name in BOSS_ABILITIES:
        # Check HP threshold
        if hp_pct > hp_max:
            continue
        # Check cooldown
        if now < cooldowns.get(ability_name, 0):
            continue
        # Enrage is one-time
        if ability_name == 'enrage' and mob.ai_state.get('enraged'):
            continue
        # Non-enrage abilities go through the intent system in real fights
        if ability_name != 'enrage' and not exempt:
            continue

        handler = _BOSS_HANDLERS.get(handler_name)
        if handler:
            result = await handler(mob, target)
            if result:
                cooldowns[ability_name] = now + cd_secs
                return True

    return False


# ---------------------------------------------------------------------------
# Pack AI
# ---------------------------------------------------------------------------

async def _pack_tick(mob, target):
    """Pack mob: call for help from nearby same-type mobs (once per fight)."""
    if mob.ai_state.get('pack_called'):
        return False
    mob.ai_state['pack_called'] = True

    if not mob.room:
        return False
    import reach
    if reach.pulled(mob):
        return False       # struck from the next room (reach.py): only the one aimed at comes

    c = mob.config.COLORS
    called = 0
    mob_vnum = getattr(mob, 'vnum', None)
    mob_name_base = _name_lower(mob).split()[0] if _name_lower(mob) else ''

    # Check current room and adjacent rooms
    rooms_to_check = [mob.room]
    for direction, exit_data in mob.room.exits.items():
        if exit_data and exit_data.get('room'):
            rooms_to_check.append(exit_data['room'])

    for room in rooms_to_check:
        for char in list(room.characters):
            if char == mob or char.is_fighting:
                continue
            if not hasattr(char, 'vnum'):
                continue
            # Same vnum or same name base
            is_same = (mob_vnum and char.vnum == mob_vnum) or \
                      (mob_name_base and _name_lower(char).startswith(mob_name_base))
            if not is_same:
                continue

            # Move to room if in adjacent room
            if char.room != mob.room:
                if char in char.room.characters:
                    char.room.characters.remove(char)
                char.room = mob.room
                mob.room.characters.append(char)
                await mob.room.send_to_room(
                    f"{c['red']}{char.name} rushes in to help!{c['reset']}"
                )

            # Join the fight
            char.fighting = target
            char.position = 'fighting'
            called += 1
            if called >= 3:
                break
        if called >= 3:
            break

    if called > 0:
        await mob.room.send_to_room(
            f"{c['bright_red']}{mob.name} howls for help and {called} ally{'s' if called != 1 else ''} join the fight!{c['reset']}"
        )
        return True
    return False


# ---------------------------------------------------------------------------
# Healer AI
# ---------------------------------------------------------------------------

async def _healer_tick(mob, target):
    """Healer mob: prioritize healing wounded allies in the room."""
    if mob.mana < 15:
        return False
    import brain
    if brain.on('tactics') and not _intent_exempt(mob, target):
        return False        # a prayer, declared a round ahead and interruptible (brain/cast.py)

    now = time.time()
    cd = mob.ai_state.setdefault('heal_cd', 0)
    if now < cd:
        return False

    c = mob.config.COLORS

    # Find the most wounded ally (non-player NPC in same room, fighting)
    best_ally = None
    best_pct = 1.0
    import brain
    own_side = brain.on('threat')        # (brain/: never a player's pet, nor one it fights)
    if own_side:
        from brain.targeting import players_side
    for char in mob.room.characters:
        if char == mob or hasattr(char, 'connection'):
            continue
        if not char.is_alive:
            continue
        if own_side and (players_side(char) or getattr(char, 'fighting', None) is mob
                         or 'charmed' in (getattr(char, 'affect_flags', None) or ())):
            continue
        pct = char.hp / max(1, char.max_hp)
        if pct < best_pct and pct < 0.7:
            best_pct = pct
            best_ally = char

    # Also consider healing self
    self_pct = mob.hp / max(1, mob.max_hp)
    if self_pct < best_pct and self_pct < 0.6:
        best_ally = mob

    if best_ally is None:
        return False

    heal = random.randint(mob.level * 2, mob.level * 5)
    best_ally.hp = min(best_ally.max_hp, best_ally.hp + heal)
    mob.mana -= 15
    mob.ai_state['heal_cd'] = now + 5

    if best_ally == mob:
        await mob.room.send_to_room(
            f"{c['bright_cyan']}{mob.name} chants a prayer and heals themselves! [+{heal} HP]{c['reset']}"
        )
    else:
        await mob.room.send_to_room(
            f"{c['bright_cyan']}{mob.name} lays hands on {best_ally.name} and heals their wounds! [+{heal} HP]{c['reset']}"
        )
    return True


# ---------------------------------------------------------------------------
# Coward AI
# ---------------------------------------------------------------------------

async def _coward_tick(mob, target):
    """Cowardly mob: flee when HP drops below 30%."""
    hp_pct = mob.hp / max(1, mob.max_hp)
    if hp_pct > 0.3:
        return False

    c = mob.config.COLORS
    await mob.room.send_to_room(
        f"{c['yellow']}{mob.name} panics and tries to flee!{c['reset']}"
    )

    # End combat
    if mob.fighting:
        if mob.fighting.fighting == mob:
            mob.fighting.fighting = None
    mob.fighting = None
    mob.position = 'standing'
    await mob.flee()
    return True


# ---------------------------------------------------------------------------
# Declared intents — a mob telegraphs its next special ONE ROUND AHEAD and the
# players get a real window to react (brace / sidestep / interrupt, see
# commands.py). declare_intents() runs in a pre-pass at the top of
# world.combat_tick — BEFORE the player phase — so the same tick's web push
# carries the intent with a full round left on the clock. mob_ai_tick()
# resolves a ripe intent the following round.
# ---------------------------------------------------------------------------

INTENT_WINDUP = 3.0        # min seconds between declaration and resolution
INTENT_ROOM_CAP = 2        # max simultaneous wind-ups per room (readability)


def _room_cap(mob):
    """The room's cap on wind-ups: INTENT_ROOM_CAP, or the creature's profile with tactics on
    (readable 2, brutal 3; never above brain/profile INVARIANTS)."""
    import brain
    if brain.on('tactics'):
        return int(brain.of(mob).profile.get('room_windup_cap', INTENT_ROOM_CAP))
    return INTENT_ROOM_CAP


async def _announce(mob, intent):
    """Say a declared wind-up aloud, with how to answer it."""
    c = mob.config.COLORS
    if intent['kind'] in ('heavy', 'aoe'):
        tip = ' (brace or sidestep!)'
    elif intent.get('interruptible'):
        tip = ' (interrupt it!)'
    else:
        tip = ''
    await mob.room.send_to_room(
        f"{c['bright_yellow']}⚠ {intent['telegraph']}{c['yellow']}{tip}{c['reset']}"
    )


def _intent_exempt(mob, target) -> bool:
    """Trivial fights skip the declare/react loop so grinding stays fast."""
    return getattr(mob, 'level', 1) <= getattr(target, 'level', 1) - 8


def _braced(char) -> bool:
    return time.time() < getattr(char, 'brace_until', 0)


def _sidestep_roll(char) -> bool:
    """One evasion roll for a character in the sidestep window (dodge formula)."""
    if time.time() >= getattr(char, 'sidestep_until', 0):
        return False
    skill = char.skills.get('dodge', 0) if hasattr(char, 'skills') else 0
    bonus = (getattr(char, 'dex', 10) - 10) * 2
    return random.randint(1, 100) <= min(95, max(25, skill + bonus))


async def _mitigate_hit(mob, char, damage):
    """Apply brace/sidestep to a resolving heavy/aoe hit.
    Returns the final damage, or None when fully avoided."""
    c = mob.config.COLORS
    name = getattr(char, 'name', 'Someone')
    if _sidestep_roll(char):
        await mob.room.send_to_room(
            f"{c['bright_cyan']}{name} sidesteps at the last instant — the blow finds only air!{c['reset']}"
        )
        # the RIPOSTE: a sidestep costs you this round's attack, so a clean one
        # pays it back — your next strike lands perfectly (progression-01
        # mastery v3: without this the reaction layer lost tempo and never
        # out-performed brace + bash)
        if hasattr(char, 'send') and not getattr(char, 'perfect_next', False):
            char.perfect_next = True
            await char.send(f"{c['bright_yellow']}RIPOSTE — you slip the blow and read the opening: your next strike will land PERFECTLY!{c['reset']}")
        return None
    # hero toughness (same reduction the auto-attack path applies)
    try:
        from combat import CombatHandler
        damage = CombatHandler.mitigate_incoming(char, damage)
    except Exception:
        pass
    if _braced(char):
        if hasattr(char, 'send'):
            await char.send(f"{c['cyan']}You brace against the impact — it glances off you! (halved){c['reset']}")
        return max(1, damage // 2)
    return damage


def _full_hit(mob) -> int:
    """One average-strength auto-hit (dice + the mob's damage bonus) — the
    unit a heavy blow is measured in, so a wind-up is always scarier than a
    plain swing regardless of how the zone wrote the dice."""
    try:
        base = mob.roll_dice(mob.damage_dice)
    except Exception:
        base = random.randint(mob.level, max(mob.level, mob.level * 2))
    try:
        base += max(0, mob.get_damage_bonus())
    except Exception:
        base += getattr(mob, 'damroll', 0)
    return max(1, base)


def _choose_boss_intent(mob, target):
    """Pick the boss's next declared ability (enrage stays instant)."""
    now = time.time()
    cooldowns = mob.ai_state.setdefault('boss_cooldowns', {})
    hp_pct = mob.hp / max(1, mob.max_hp)
    META = {
        'aoe_slam':    ('aoe', 'Ground Slam', False,
                        '{name} coils low and raises both fists — the very air trembles!'),
        'fear':        ('debuff', 'Terrifying Roar', True,
                        "{name}'s chest swells as it draws in a deep, rumbling breath..."),
        'summon_adds': ('cast', 'Summon Minions', True,
                        '{name} begins chanting, dark energy gathering at its fingertips!'),
    }
    for ability_name, cd_secs, hp_max, handler_name in BOSS_ABILITIES:
        if ability_name == 'enrage' or ability_name not in META:
            continue
        if hp_pct > hp_max or now < cooldowns.get(ability_name, 0):
            continue
        kind, label, interruptible, telegraph = META[ability_name]
        cooldowns[ability_name] = now + cd_secs   # cooldown commits at declaration
        return {'kind': kind, 'label': label, 'interruptible': interruptible,
                'ability': ('boss', handler_name),
                'telegraph': telegraph.format(name=mob.name)}
    return None


def _choose_caster_intent(mob, target):
    """Pick the caster's next declared offensive/debuff spell (heal/buff stay instant).
    With the brain's tactics on, real spells from its role's book (brain/cast.py)."""
    import brain
    if brain.on('tactics'):
        from brain import cast
        return cast.choose(mob, brain.of(mob), target)
    now = time.time()
    if mob.mana < 10 or now < mob.ai_state.get('spell_cd', 0) or _silenced(mob):
        return None
    hp_pct = mob.hp / max(1, mob.max_hp)
    # leave the round free for the instant self-heal / first-buff paths
    if (hp_pct < 0.4 and mob.mana >= 25) or not mob.ai_state.get('buffed'):
        return None
    if random.randint(1, 100) > 60:
        return None
    if random.randint(1, 100) <= 20:
        deb = random.choice(CASTER_DEBUFFS)
        if deb[2] and getattr(target, deb[2], 0) <= 0:
            mob.ai_state['spell_cd'] = now + 5
            return {'kind': 'debuff', 'label': deb[0].replace('_', ' ').title(),
                    'interruptible': True, 'ability': ('caster_debuff', deb),
                    'telegraph': f'{mob.name} begins weaving a hex, fingers tracing sickly glowing sigils!'}
    # smart casters read the ROOM: lightning when the prey stands in water,
    # and a desperate arsonist will torch a webbed chamber with you in it
    spells = list(CASTER_OFFENSIVE)
    try:
        from environment import get_env
        env = get_env(mob.room)
        if env['water'] and getattr(mob.room, 'frozen_until', 0) <= now:
            spells.sort(key=lambda s: 0 if 'lightning' in s[0] else 1)
        elif env['webbed'] and getattr(mob.room, 'burning_until', 0) <= now \
                and mob.hp < mob.max_hp * 0.6 and random.randint(1, 100) <= 25:
            spells.sort(key=lambda s: 0 if 'fire' in s[0] else 1)
    except Exception:
        pass
    for spell in spells:
        if mob.mana >= spell[3]:
            mob.ai_state['spell_cd'] = now + 4
            return {'kind': 'cast', 'label': spell[0].replace('_', ' ').title(),
                    'interruptible': True, 'ability': ('caster_offensive', spell),
                    'telegraph': f'{mob.name} begins an incantation — arcane power crackles around it!'}
    return None


def _legacy_kind(mob):
    """Which legacy special this mob declares (None = instant-only, e.g. troll regen)."""
    special = getattr(mob, 'special', None)
    name = _name_lower(mob)
    flags = getattr(mob, 'flags', set())
    if special == 'firebreath' or 'dragon' in name:
        return 'firebreath'
    if special == 'paralyze':
        return 'paralyze'
    if special == 'poison' or 'poison' in flags or 'spider' in name or 'snake' in name:
        return 'poison'
    return None


def _choose_legacy_intent(mob, target):
    which = _legacy_kind(mob)
    if not which:
        return None
    now = time.time()
    if now < mob.ai_state.get('legacy_cd', 0):
        return None
    if random.randint(1, 100) > 35:
        return None
    mob.ai_state['legacy_cd'] = now + 8   # ~2 rounds
    if which == 'firebreath':
        return {'kind': 'heavy', 'label': 'Fire Breath', 'interruptible': False,
                'ability': ('legacy', 'firebreath'),
                'telegraph': f'{mob.name} rears back, flames licking between its jaws!'}
    if which == 'paralyze':
        return {'kind': 'debuff', 'label': 'Paralyzing Touch', 'interruptible': True,
                'ability': ('legacy', 'paralyze'),
                'telegraph': f'{mob.name} reaches out, numbing energy trailing from its touch...'}
    return {'kind': 'heavy', 'label': 'Venomous Strike', 'interruptible': False,
            'ability': ('legacy', 'poison'),
            'telegraph': f'{mob.name} bares dripping fangs, venom beading at their tips!'}


def _pack_allies(mob, target):
    """Same-species packmates in the room fighting the same prey."""
    if not mob.room:
        return []
    myname = _name_lower(mob)
    return [ch for ch in mob.room.characters
            if ch is not mob and not hasattr(ch, 'connection')
            and getattr(ch, 'fighting', None) is target
            and _name_lower(ch) == myname]


def pack_bonus(attacker, defender):
    """Flanking: pack hunters hit harder for every packmate on the same prey
    (+10% each, capped +30%). Returns a damage multiplier."""
    try:
        if hasattr(attacker, 'connection'):
            return 1.0
        if 'pack' not in classify_mob(attacker):
            return 1.0
        n = len(_pack_allies(attacker, defender))
        return 1.0 + 0.10 * min(3, n)
    except Exception:
        return 1.0


def consume_ambush(attacker):
    """An ambusher's first strike from cold hits like a backstab (×1.8).
    Returns the multiplier and consumes the ambush (re-armed on combat end)."""
    try:
        if hasattr(attacker, 'connection'):
            return 1.0
        ai = getattr(attacker, 'ai_state', None)
        if not isinstance(ai, dict):
            return 1.0
        if 'ambusher' not in classify_mob(attacker):
            return 1.0
        if not ai.get('ambush', True):  # missing flag = never fought = armed
            return 1.0
        ai['ambush'] = False
        return 1.8
    except Exception:
        return 1.0


def _choose_pack_intent(mob, target):
    """With packmates on the prey, the pack winds up a COORDINATED LUNGE —
    they strike as one, and the whole pile can be braced or sidestepped."""
    allies = _pack_allies(mob, target)
    if len(allies) < 1:
        return None
    now = time.time()
    if now < mob.ai_state.get('lunge_cd', 0):
        return None
    if random.randint(1, 100) > 35:
        return None
    mob.ai_state['lunge_cd'] = now + 16
    n = 1 + min(2, len(allies))
    return {'kind': 'heavy', 'label': 'Coordinated Lunge', 'interruptible': False,
            'ability': ('pack_lunge', n),
            'telegraph': f'{mob.name} and its pack fan out, moving as ONE...'}


async def _resolve_pack_lunge(mob, target, n):
    c = mob.config.COLORS
    from combat import CombatHandler
    try:
        base = mob.roll_dice(mob.damage_dice)
    except Exception:
        base = random.randint(mob.level, max(mob.level, mob.level * 2))
    damage = int(base * 1.1 * n) + getattr(mob, 'damroll', 0)
    dmg = await _mitigate_hit(mob, target, damage)
    if dmg is None:
        return
    await mob.room.send_to_room(
        f"{c['bright_red']}🐺 The pack strikes as one — {n} sets of fangs hit {target.name} together! [{dmg}]{c['reset']}"
    )
    if await target.take_damage(dmg, mob):
        await CombatHandler.handle_death(mob, target)


def _choose_bruiser_intent(mob, target):
    """Role-less mobs wind up a crushing blow every few rounds; hulking brutes
    sweep the whole area instead — the client paints a danger zone you can
    physically walk out of (cmd_evade)."""
    now = time.time()
    cfg = mob.config
    if now < mob.ai_state.get('heavy_cd', 0):
        return None
    # The opening wind-up is guaranteed (a read on the foe in the first
    # seconds); after that, roughly every 3-4 rounds.
    chance = cfg.WINDUP_CHANCE if 'heavy_cd' in mob.ai_state else cfg.WINDUP_FIRST_ROUND_CHANCE
    if random.randint(1, 100) > chance:
        return None
    mob.ai_state['heavy_cd'] = now + random.randint(cfg.WINDUP_COOLDOWN_MIN, cfg.WINDUP_COOLDOWN_MAX)
    big = bool(set(_name_lower(mob).split()) & BIG_KEYWORDS)
    name = mob.name
    if big and random.randint(1, 100) <= 60:
        return {'kind': 'aoe', 'label': 'Sweeping Blow', 'interruptible': False,
                'ability': ('bruiser', 'sweep'),
                'telegraph': random.choice([
                    f'{name} winds up a great SWEEPING blow — get clear!',
                    f'{name} rears back, both arms wide, and winds up a SWEEPING blow!',
                    f'{name} drops low and winds up to SWEEP the whole area — get clear!',
                ])}
    return {'kind': 'heavy', 'label': 'Crushing Blow', 'interruptible': False,
            'ability': ('bruiser', None),
            'telegraph': random.choice([
                f'{name} plants its feet and rears back for a crushing blow!',
                f'{name} draws back, muscles bunching, and winds up a crushing blow!',
                f"{name} rears back — a crushing blow is coming!",
            ])}


async def declare_intents(mob):
    """Pre-pass (top of world.combat_tick): a fighting mob with no pending
    wind-up may choose and DECLARE its next special. It resolves next round.
    The creature's brain decides (brain.declare); combat_hooks wraps this name."""
    import brain
    return await brain.declare(mob)


async def _legacy_declare_intents(mob):
    """declare_intents as it was before the brain (brain/legacy.py)."""
    if getattr(mob, 'pending_intent', None):
        return
    if not mob.is_fighting or not mob.fighting or not mob.room:
        return
    target = mob.fighting
    if not getattr(target, 'is_alive', False):
        return
    if not hasattr(mob, 'ai_state') or mob.ai_state is None:
        mob.ai_state = {}
    if _intent_exempt(mob, target):
        return
    if time.time() < getattr(mob, 'staggered_until', 0):
        return   # reeling — in no state to wind anything up
    # keep pack fights readable: at most a couple of wind-ups at once
    pending = sum(1 for ch in mob.room.characters if getattr(ch, 'pending_intent', None))
    if pending >= _room_cap(mob):
        return

    roles = classify_mob(mob)

    # A disciplined foe READS your rhythm: arming a perfect strike (cmd_swing)
    # can invite a counter — the guard snaps up before your blow lands. This
    # runs in the pre-pass, i.e. BEFORE the player phase resolves the strike,
    # so the duel actually plays out: telegraph → counter → breaker.
    if 'guarded' in roles and getattr(target, 'perfect_next', False):
        now = time.time()
        if now >= mob.ai_state.get('guard_cd', 0) and now >= getattr(mob, 'staggered_until', 0) \
                and random.randint(1, 100) <= 60:
            mob.guard_until = now + 8.0
            mob.ai_state['guard_cd'] = now + 20
            c = mob.config.COLORS
            await mob.room.send_to_room(
                f"{c['bright_cyan']}🛡 {mob.name} reads your rhythm and snaps into a guard!{c['reset']}"
            )
            return

    intent = None
    if 'boss' in roles:
        intent = _choose_boss_intent(mob, target)
    if intent is None and 'caster' in roles:
        intent = _choose_caster_intent(mob, target)
    if intent is None and 'legacy_special' in roles:
        intent = _choose_legacy_intent(mob, target)
    if intent is None and 'pack' in roles:
        intent = _choose_pack_intent(mob, target)
    if intent is None and not roles & {'boss', 'caster', 'legacy_special', 'scripted'}:
        intent = _choose_bruiser_intent(mob, target)
    if intent is None:
        return

    intent['declared_at'] = time.time()
    mob.pending_intent = intent
    await _announce(mob, intent)


async def _resolve_legacy(mob, target, which):
    c = mob.config.COLORS
    from combat import CombatHandler
    if which == 'firebreath':
        damage = int(mob.roll_dice(mob.damage_dice) * 2.0)
        dmg = await _mitigate_hit(mob, target, damage)
        if dmg is None:
            return
        await mob.room.send_to_room(
            f"{c['bright_red']}{mob.name} breathes a torrent of fire over {target.name}! [{dmg}]{c['reset']}"
        )
        if await target.take_damage(dmg, mob, 'fire'):
            await CombatHandler.handle_death(mob, target)
    elif which == 'poison':
        damage = max(1, int(mob.roll_dice(mob.damage_dice) * 0.5))
        dmg = await _mitigate_hit(mob, target, damage)
        if dmg is None:
            return
        await mob.room.send_to_room(
            f"{c['bright_red']}{mob.name} sinks venomous fangs into {target.name}! [{dmg}]{c['reset']}"
        )
        try:
            from affects import AffectManager
            already = any((a.get('name') if isinstance(a, dict) else getattr(a, 'name', '')) == 'poison'
                          for a in getattr(target, 'affects', []))
            if not already:
                AffectManager.apply_affect(target, {
                    'name': 'poison', 'type': AffectManager.TYPE_DOT, 'applies_to': 'hp',
                    # weighed like its blows (a zone boss's or a quest creature's _dmg_scale)
                    'value': max(1, round((3 + mob.level // 5) * (getattr(mob, '_dmg_scale', 1) or 1))),
                    'duration': 4, 'caster_level': mob.level,
                })
                if hasattr(target, 'send'):
                    await target.send(f"{c['green']}You feel poison coursing through your veins!{c['reset']}")
        except Exception:
            pass
        if await target.take_damage(dmg, mob, 'poison'):
            await CombatHandler.handle_death(mob, target)
    else:   # paralyze
        if _braced(target) or _sidestep_roll(target):
            await mob.room.send_to_room(
                f"{c['cyan']}{target.name} shrugs off {mob.name}'s numbing touch!{c['reset']}"
            )
            return
        if random.randint(1, 100) <= 35:
            from combat import CombatHandler
            CombatHandler.stun(target, 1)
            await mob.room.send_to_room(f"{c['yellow']}{target.name} is paralyzed!{c['reset']}")
        else:
            await mob.room.send_to_room(
                f"{c['yellow']}{target.name} twists away from the paralyzing touch!{c['reset']}"
            )


async def _resolve_bruiser(mob, target, variant=None):
    c = mob.config.COLORS
    from combat import CombatHandler
    base = _full_hit(mob)
    if variant == 'sweep':
        # area sweep: hits every player in the room; sidestep/brace/evade all
        # mitigate (the web client auto-evades when you're physically clear)
        damage = int(base * mob.config.SWEEP_BLOW_MULT)
        await mob.room.send_to_room(
            f"{c['bright_red']}{mob.name}'s SWEEPING blow scythes across the area!{c['reset']}"
        )
        for char in list(mob.room.characters):
            if char is mob or not hasattr(char, 'connection'):
                continue
            dmg = await _mitigate_hit(mob, char, damage)
            if dmg is None:
                continue
            if hasattr(char, 'send'):
                await char.send(f"{c['bright_red']}The sweep smashes into you! [{dmg}]{c['reset']}")
            if await char.take_damage(dmg, mob):
                await CombatHandler.handle_death(mob, char)
        return
    damage = int(base * mob.config.HEAVY_BLOW_MULT)
    dmg = await _mitigate_hit(mob, target, damage)
    if dmg is None:
        return
    await mob.room.send_to_room(
        f"{c['bright_red']}{mob.name}'s crushing blow slams into {target.name}! [{dmg}]{c['reset']}"
    )
    if not _braced(target) and random.randint(1, 100) <= mob.config.HEAVY_STUN_CHANCE:
        target.stunned_rounds = getattr(target, 'stunned_rounds', 0) + 1
        if hasattr(target, 'send'):
            await target.send(f"{c['yellow']}The impact leaves you reeling — stunned!{c['reset']}")
    if await target.take_damage(dmg, mob):
        await CombatHandler.handle_death(mob, target)
        return
    # full symmetry: their heavy blow can knock YOU into the room's hazards
    try:
        from environment import try_shove
        if not _braced(target):
            await try_shove(mob, target, mob.room)
    except Exception:
        pass


async def _resolve_intent(mob):
    """Execute (or fizzle) the mob's declared intent. Called from mob_ai_tick
    one round after declaration; an interrupt clears pending_intent before we
    ever get here."""
    intent = getattr(mob, 'pending_intent', None)
    mob.pending_intent = None
    if not intent:
        return False
    c = mob.config.COLORS
    target = mob.fighting
    what, arg = intent['ability']
    if what in ('mob_heal', 'disrupt') and mob.room:
        from brain import cast
        await (cast.resolve_heal if what == 'mob_heal' else cast.resolve_disrupt)(mob, arg)
        return True
    if not target or not getattr(target, 'is_alive', False) or not mob.room:
        if mob.room:
            await mob.room.send_to_room(
                f"{c['yellow']}{mob.name}'s {intent['label']} finds no target and fizzles.{c['reset']}"
            )
        return True

    if intent['kind'] in ('heavy', 'aoe'):
        mob._skip_autoattack = True   # the special IS this round's attack
        # a massive impact can SHATTER frozen ice under the whole fight
        try:
            from environment import heavy_impact
            await heavy_impact(mob.room)
        except Exception:
            pass

    if what == 'boss':
        handler = _BOSS_HANDLERS.get(arg)
        if handler:
            await handler(mob, target)
    elif what == 'caster_offensive':
        await _cast_offensive(mob, target, arg)
    elif what == 'caster_debuff':
        await _cast_debuff(mob, target, arg)
    elif what == 'mob_hex':
        from brain import cast
        await cast.resolve_hex(mob, target, arg)
    elif what == 'legacy':
        await _resolve_legacy(mob, target, arg)
    elif what == 'bruiser':
        await _resolve_bruiser(mob, target, arg)
    elif what == 'pack_lunge':
        await _resolve_pack_lunge(mob, target, arg)
    return True


# ---------------------------------------------------------------------------
# Main entry point — called each combat round per fighting mob
# ---------------------------------------------------------------------------

async def mob_ai_tick(mob):
    """
    Run intelligent combat AI for a fighting mob.
    Called once per combat round from world.combat_tick().
    Returns True if the mob took a special action this round.
    The creature's brain decides (brain.combat_turn).
    """
    import brain
    return await brain.combat_turn(mob)


async def _legacy_mob_ai_tick(mob):
    """mob_ai_tick as it was before the brain (brain/legacy.py)."""
    held = getattr(mob, 'affect_flags', None) or set()
    if held & {'paralyzed', 'charmed', 'feared'} or (getattr(mob, 'stunned_rounds', 0) or 0) > 0:
        return False       # held by a spell (spells.py): no special this round either
    if not mob.is_fighting or not mob.fighting or not mob.room:
        mob.pending_intent = None   # never leave a wind-up dangling
        return False

    target = mob.fighting
    if not target.is_alive:
        return False

    # Ensure ai_state dict exists
    if not hasattr(mob, 'ai_state') or mob.ai_state is None:
        mob.ai_state = {}

    # A declared intent owns this mob's special action: resolve it once ripe
    # (it was declared in a previous round's pre-pass); otherwise it is still
    # winding up and the mob takes no other special action this round.
    intent = getattr(mob, 'pending_intent', None)
    if intent:
        if time.time() - intent.get('declared_at', 0) >= INTENT_WINDUP:
            await _resolve_intent(mob)
        return True

    roles = classify_mob(mob)
    if not roles:
        return False

    # Priority order: coward > healer > boss > pack > caster
    # Coward check first (survival)
    if 'coward' in roles:
        if await _coward_tick(mob, target):
            return True

    # Healer checks allies
    if 'healer' in roles:
        if await _healer_tick(mob, target):
            return True

    # Boss abilities
    if 'boss' in roles:
        if await _boss_tick(mob, target):
            return True

    # Pack call for help (one-time)
    if 'pack' in roles:
        if await _pack_tick(mob, target):
            return True

    # Caster spells
    if 'caster' in roles:
        if await _caster_tick(mob, target):
            return True

    # Troll-style regeneration (instant — its counter is poison, not a reaction).
    # Declared legacy specials (fire breath etc.) go through declare_intents.
    if 'legacy_special' in roles and _legacy_kind(mob) is None:
        if random.randint(1, 100) <= 30:
            await mob.special_attack()
            return True

    # Disciplined fighters raise a GUARD: physical damage mostly turned aside
    # for two rounds. The taught counter is a bash/kick (break_guard).
    if 'guarded' in roles:
        now = time.time()
        if now >= mob.ai_state.get('guard_cd', 0) \
                and now >= getattr(mob, 'staggered_until', 0) \
                and random.randint(1, 100) <= 45:
            mob.guard_until = now + 8.0          # ~2 rounds
            mob.ai_state['guard_cd'] = now + 20  # ~5 rounds between guards
            c = mob.config.COLORS
            await mob.room.send_to_room(
                f"{c['bright_cyan']}🛡 {mob.name} locks into a defensive guard! "
                f"{c['yellow']}(a heavy bash or kick can break it){c['reset']}"
            )
            return True

    return False
