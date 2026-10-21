"""Learn by doing (owner's choice for skills and spells).

- Every class ability unlocks at a level (UNLOCK below, in the order of the class rosters in
  config.py and the spells' own level_required). Reaching it grants the ability at 50%: on a
  level-up, at login (characters made before this catch up) and when a character is made.
- Using an ability may improve it, up to 85% ("Mastered"): a chance of max(2, 20 - pct/5)% on
  a success and half that on a failure, for 1-2 points. Passives (dodge, parry, extra
  attacks) improve when they work, at a quarter of that chance (they work every round).
- Proficiency matters for every ability: a spell fizzles (100 - pct)/4 % of the time (50% ->
  12.5%, 85% -> 3.75%); ability damage and spell healing are x(0.85 + 0.3 * pct/100).
- A guild trainer teaches 85 -> 100 in 5% steps, each for (pct - 80) * 250 gold, or for a
  practice session left over from the old system (sessions are no longer handed out).
- book(cls) describes a class's abilities for the 3D client's spellbook (/abilitybook).
"""
import random

LEARN_AT = 50
BY_USE = 85
STEP = 5
PASSIVE = frozenset({'second_attack', 'third_attack', 'parry', 'shield_block', 'dodge', 'dual_wield'})
# one-off choices, not abilities you practise: they keep their own rules
CHOICES = frozenset({'doctrine', 'swear', 'evolve', 'oath'})
# skills used on yourself or the room, not aimed at a foe (the bar sends them without a target)
SELF_SKILLS = frozenset({'sneak', 'hide', 'cover_tracks', 'track', 'scan', 'scribe', 'drink_the_leyline', 'charge_release', 'detect_traps',
                         'lore', 'caltrops', 'snare', 'bone_shield', 'fade', 'slip_the_veil', 'countersong', 'encore',
                         'magnum_opus', 'rigged_dice', 'poison', 'evasion', 'divine_intervention', 'pick_lock',
                         'warpath', 'titans_wrath', 'perfect_crime', 'camouflage_master', 'camouflage', 'shadow_dance',
                         'shadow_blades_master', 'cold_blood', 'shadow_blade', 'envenom', 'alpha_pack', 'bestial_wrath',
                         'explosive_trap', 'unbroken_banner', 'seraphs_vigil', 'lich_ascension', 'heist',
                         'song_of_the_ages', 'thousand_shadows'})
# skills aimed at a friend (the targeted player, else yourself)
ALLY_SKILLS = frozenset({'rescue', 'absolution'})
# skills for your whole party (sent without a target)
GROUP_SKILLS = frozenset({'rallying_cry', 'divine_word'})
# the marquee abilities: earned through their class's quest (marquee.py), never by level;
# the level is when the quest is offered
QUEST_ABILITIES = {'unbroken_banner': 'The Unbroken Banner', 'singularity': 'The Heart of the Void',
                   'seraphs_vigil': 'The Lost Choir', 'wings_of_dawn': 'The Dawnless Chapel',
                   'lich_ascension': 'The First Phylactery', 'heist': 'The Last Score',
                   'heartseeker': 'The Last Wyvern', 'song_of_the_ages': 'The Unsung Verse',
                   'thousand_shadows': 'The Contract of Mirrors'}

# the level each ability comes at, per class (spells with a level_required keep it)
UNLOCK = {
    'warrior': dict(strike=1, bash=1, kick=2, heroic_throw=3, cleave=4, rally=6, parry=8, charge=10, second_attack=12,
                    execute=14, rescue=16, shield_block=18, dodge=20, third_attack=26,
                    rallying_cry=32, shattering_blow=38, commanding_shout=44, heroic_leap=50, warpath=56,
                    titans_wrath=60, unbroken_banner=45),
    'mage': dict(magic_missile=1, armor=1, burning_hands=3, detect_magic=4, chill_touch=5, sleep=7, shield=8,
                 charge_release=9, lightning_bolt=10, identify=11, color_spray=12, invisibility=13,
                 drink_the_leyline=14, fireball=15, dodge=16, fly=17, scribe=18, block_door=19, towerbolt=20,
                 protection_from_evil=21, protection_from_good=21, ice_armor=22, enchant_weapon=23, mana_shield=24,
                 phase_step=25, stepwise=26, fire_shield=27, teleport=28, stoneskin=30, tower_echoes=32,
                 mirrorward=34, chain_lightning=36, quicken=38, meteor_swarm=40, resonance_burst=44,
                 rimeheart=50, kindling_focus=56, meteor_storm=60, singularity=45),
    'cleric': dict(holy_smite=1, cure_light=1, bless=2, armor=3, create_food=4, create_water=4, turn_undead=5,
                   cure_serious=6, remove_poison=7, word_of_recall=8, divine_word=9, shield_of_faith=10,
                   dispel_evil=11, cure_critical=12, remove_curse=13, barkskin=14, protection_from_evil=15,
                   dodge=16, harm=17, pyre_of_faith=18, break_door=19, sanctuary=20, heal=22, righteous_fury=23, summon=24,
                   aegis=25, flamestrike=26, divine_shield=27, group_heal=28, holy_aura=29, earthquake=30,
                   travelling_grace=32, divine_protection=34, resurrect=36, shared_burden=38, cleansing_rite=44,
                   font_of_the_vigil=50, serenity=56, divine_intervention=60, seraphs_vigil=45),
    'thief': dict(backstab=1, sneak=1, hide=2, pick_lock=3, knife_toss=3, steal=4, trip=5, dodge=6, circle=8, pocket_sand=10,
                  detect_traps=11, cover_tracks=7, low_blow=12, second_attack=14, evasion=16, caltrops=18, rigged_dice=20,
                  jackpot=24, nerve_strike=32, garrote=44, marked_for_death_thief=56, perfect_crime=60, heist=45),
    'ranger': dict(truesight_shot=1, track=1, scan=2, cure_light=3, sneak=4, quarry_mark=5, hide=6, faerie_fire=7,
                   tame=8, wildbond_strike=9, dodge=10, snare=11, entangle=12, second_attack=13, detect_magic=14,
                   barkskin=15, loosing_storm=16, dual_wield=18, briskness=20, call_lightning=22,
                   volley=32, camouflage_master=38, serpent_sting=44, alpha_pack=60, heartseeker=45),
    'paladin': dict(censure=1, cure_light=1, bash=2, bless=3, order_verdict=4, rescue=5, detect_evil=6,
                    turn_undead=7, absolution=8, parry=9, protection_from_evil=10, shield_of_faith=11,
                    cure_serious=13, second_attack=14, shield_block=15, halo_of_reckoning=16, dodge=18,
                    divine_shield=20, unfettered=32, hallowed_ground=38, dawnhammer=44, ascendant_hour=50,
                    divine_shield_master=56, verdict_of_the_order=60, wings_of_dawn=45),
    'necromancer': dict(soul_bolt=1, chill_touch=1, armor=2, weaken=3, soul_siphon=4, mistgrasp=5, leechcraft=6,
                        bone_shield=7, poison=8, animate_dead=9, blindness=10, shield=11, fear=12, enervation=13,
                        mistrot=14, wraithfire=15, protection_from_good=16, soul_reap=18, energy_drain=20,
                        sever_cord=24, corpse_shield=38, summon_gargoyle=50, soul_harvest=56, apocalypse_necro=60,
                        lich_ascension=45),
    'bard': dict(mockery=1, cure_light=1, fascinate=2, armor=3, lore=4, sleep=5, bless=6, discordant_note=7,
                 sneak=8, detect_magic=9, crescendo=10, pick_lock=11, countersong=12, charm_person=13, dodge=14,
                 slow=15, heroism=16, fear=17, encore=18, invisibility=19, haste=22, mass_charm=28,
                 refrain_of_hope=32, chord_of_disruption=38, epic_tale=44, siren_song=50, requiem=56,
                 magnum_opus=60, song_of_the_ages=45),
    'assassin': dict(backstab=1, mark=1, sneak=2, hide=3, cover_tracks=7, expose=4, vital=5, dodge=6, feint=8, poison=9, fade=10,
                     second_attack=12, execute_contract=14, evasion=16, dual_wield=18, slip_the_veil=20,
                     shadowstrike=32, fan_of_knives=38, rupture=44, shadow_blades_master=50,
                     vendetta_assassin=56, death_mark=60, thousand_shadows=45),
}

# a line for abilities the help prose doesn't describe
SHORT_DESC = {
    'strike': 'A clean weapon blow that builds Momentum.',
    'kick': 'A quick kick for extra damage.', 'bash': 'Slam a foe with your shield or body, stunning them briefly.',
    'rescue': 'Pull an ally out of danger, taking the blows yourself.', 'parry': 'Deflect blows with your weapon.',
    'dodge': 'Sidestep blows.', 'second_attack': 'A chance at a second swing each round.',
    'third_attack': 'A chance at a third swing each round.', 'dual_wield': 'Fight with a weapon in each hand.',
    'shield_block': 'Catch blows on your shield.', 'evasion': 'Avoid attacks entirely now and then.',
    'animate_dead': 'Raise a fallen foe as an undead servant that fights beside you.',
    'snare': 'Set a snare that catches a foe and holds it in place.',
}


def roster(cls):
    """[(ability, 'skill'|'spell')] of a class, in its own order (no one-off choices)."""
    from config import Config
    data = Config.CLASSES.get(str(cls or '').lower(), {})
    out, seen = [], set()
    for kind in ('skills', 'spells'):
        for a in data.get(kind, []):
            if a in CHOICES or a in seen:
                continue
            seen.add(a)
            out.append((a, 'skill' if kind == 'skills' else 'spell'))
    return out


def unlock_level(cls, ability):
    lv = UNLOCK.get(str(cls or '').lower(), {}).get(ability)
    if lv is not None:
        return lv
    try:
        from spells import SPELLS
        req = (SPELLS.get(ability) or {}).get('level_required')
        if req:
            return int(req)
    except Exception:
        pass
    return 50


def store_of(player, ability):
    """The dict an ability lives in (spells for spells, else skills)."""
    try:
        from spells import SPELLS
        if ability in SPELLS and ability not in (getattr(player, 'skills', None) or {}):
            return player.spells
    except Exception:
        pass
    return player.skills


def pct_of(player, ability):
    return max((getattr(player, 'skills', None) or {}).get(ability, 0), (getattr(player, 'spells', None) or {}).get(ability, 0))


def learnable(player):
    """Abilities the player's level has reached but the player doesn't know yet."""
    lvl = getattr(player, 'level', 1) or 1
    cls = getattr(player, 'char_class', '')
    return [(a, kind) for a, kind in roster(cls)
            if unlock_level(cls, a) <= lvl and pct_of(player, a) <= 0 and a not in QUEST_ABILITIES]


def grant_now(player):
    """Learn everything the level has reached, at 50% (no messages). Returns what was new."""
    new = learnable(player)
    for a, kind in new:
        (player.spells if kind == 'spell' else player.skills)[a] = LEARN_AT
    return new


async def grant(player, quiet=False):
    """grant_now, announced (a level-up), and pushed to the 3D client's spellbook."""
    new = grant_now(player)
    if new and not quiet and hasattr(player, 'send'):
        c = player.config.COLORS
        await player.send("")
        await player.send(f"{c['bright_yellow']}  ★ You learned something new! ★{c['reset']}")
        for a, kind in new:
            mark = '✦' if kind == 'spell' else '⚔'
            await player.send(f"    {c['white']}{mark} {name_of(a)}{c['reset']} {c['cyan']}— {describe(a)[:70]}{c['reset']}")
        await player.send(f"{c['yellow']}  Abilities grow as you use them, up to {BY_USE}%. "
                          f"Your guild's trainer teaches the rest.{c['reset']}")
        await player.send("")
    if new:
        await _push(player)
    return [a for a, _k in new]


def improve_chance(pct, ok=True, rate=1.0):
    """Percent chance that one use improves an ability at `pct`."""
    c = max(2.0, 20.0 - pct / 5.0)
    return (c if ok else c / 2.0) * rate


async def improve(player, ability, ok=True, rate=1.0):
    """A use of `ability` (ok: it worked) may make it better, up to BY_USE. Returns the new %."""
    if not hasattr(player, 'skills'):
        return None
    store = player.spells if ability in (getattr(player, 'spells', None) or {}) else player.skills
    cur = store.get(ability, 0)
    if cur <= 0 or cur >= BY_USE:
        return None
    try:
        player._mastery_hit = ability
    except Exception:
        pass
    if random.random() * 100 >= improve_chance(cur, ok, rate):
        return None
    new = min(BY_USE, cur + random.randint(1, 2))
    store[ability] = new
    c = player.config.COLORS
    note = ' — Mastered! A trainer can teach you the rest.' if new >= BY_USE else ''
    await player.send(f"{c['bright_green']}Your {name_of(ability).lower()} improves! ({new}%){note}{c['reset']}")
    wm = getattr(getattr(player, 'world', None), 'web_map', None)
    if wm:
        try:
            await wm.notify_event(player, {'type': 'improve', 'id': ability, 'pct': new})
        except Exception:
            pass
    return new


def fizzle_chance(pct):
    """Percent chance a spell known at `pct` fizzles."""
    return max(0.0, (100 - pct) / 4.0)


def power(pct):
    """Damage and healing multiplier of an ability known at `pct` (0.85 at 0%, 1.15 at 100%)."""
    return 0.85 + 0.3 * max(0, min(100, pct)) / 100.0


def step_cost(pct):
    """Gold for a trainer's next 5% past mastery."""
    return max(1, int((pct - 80) * 250))


async def _push(player):
    """A fresh map payload, so the 3D client's spellbook and bar see the change at once."""
    wm = getattr(getattr(player, 'world', None), 'web_map', None)
    if wm and hasattr(wm, 'notify_player'):
        try:
            await wm.notify_player(player)
        except Exception:
            pass


# ------------------------------------------------------------------ names and descriptions
_SMALL = {'of', 'the', 'a', 'an', 'to', 'in', 'on', 'and', 'from'}
# ids that carry their class to stay unique, and names the words don't spell
NAMES = {'marked_for_death_thief': 'Marked for Death', 'vendetta_assassin': 'Vendetta', 'titans_wrath': "Titan's Wrath",
         'apocalypse_necro': 'Apocalypse', 'shadow_blades_master': 'Shadow Blades', 'seraphs_vigil': "Seraph's Vigil",
         'heist': 'The Heist of Ages'}


def name_of(ability):
    if ability in NAMES:
        return NAMES[ability]
    try:
        from spells import SPELLS
        n = (SPELLS.get(ability) or {}).get('name')
        if n:
            return n
    except Exception:
        pass
    words = ability.replace('_', ' ').split()
    return ' '.join(w if (i and w in _SMALL) else w.capitalize() for i, w in enumerate(words))


def _first_sentence(text, limit=150):
    """The opening sentence (two when the first is a mere "Passive.")."""
    t = ' '.join(str(text or '').split())
    if not t:
        return ''
    import re
    out = ''
    for m in re.finditer(r'.+?[.!](?=\s|$)', t):
        out = t[:m.end()]
        if len(out) >= 25:
            break
    out = out or t
    return out if len(out) <= limit else out[:limit - 1].rsplit(' ', 1)[0] + '…'


def describe(ability, fallback=''):
    """One or two sentences on what an ability does (the help prose, else its numbers)."""
    import re
    text = ''
    try:
        import help_abilities as ha
        prose = getattr(ha, 'SKILL_PROSE', {}).get(ability) or getattr(ha, 'SPELL_PROSE', {}).get(ability)
        if isinstance(prose, (tuple, list)):
            prose = prose[0] if prose else ''
        if prose:
            text = _first_sentence(prose)
        else:
            from spells import SPELLS
            if ability in SPELLS and hasattr(ha, '_spell_effect_summary'):
                parts = ha._spell_effect_summary(SPELLS[ability]) or []
                text = '; '.join(parts) if isinstance(parts, (list, tuple)) else str(parts)
    except Exception:
        text = ''
    if not text:
        try:
            from commands import CommandHandler
            doc = (getattr(CommandHandler, f'cmd_{ability}', None).__doc__ or '').strip().split('\n')[0]
            doc = re.sub(r'^CAPSTONE:\s*', '', doc)
            if doc and not doc.lower().startswith(('internal', 'usage')):
                text = doc[0].upper() + doc[1:].rstrip('.') + '.'
        except Exception:
            pass
    text = text or SHORT_DESC.get(ability, '') or fallback
    # the renamed abilities' prose remembers their old names: "(was Arcane Blast)"
    return re.sub(r'\s*\(was [^)]*\)', '', text).strip()


_TARGET = {'offensive': 'enemy', 'defensive': 'ally', 'self': 'self', 'room': 'area', 'group': 'group',
           'object': 'object', 'door': 'object', 'special': 'special'}


def _entry(cls, ability, kind, level, talent=None, note=''):
    import combat_range as cr
    e = {'id': ability, 'name': name_of(ability), 'type': kind, 'level': level, 'desc': describe(ability, note)}
    if talent:
        e['talent'] = talent
    if ability in QUEST_ABILITIES:
        e['quest'] = QUEST_ABILITIES[ability]
        e['marquee'] = True
    if ability in PASSIVE or (ability == 'evasion' and cls == 'thief'):
        e['passive'] = True
        return e
    if kind == 'spell':
        from spells import SPELLS
        sp = SPELLS.get(ability) or {}
        e['cost'] = sp.get('mana_cost')
        e['res'] = 'mana'
        tgt = _TARGET.get(sp.get('target'), 'enemy')
        e['target'] = tgt
        if tgt in ('enemy', 'ally'):
            e['range'] = cr.ability_range(ability, True)[0]
        from spells import AIM_RADIUS, AIM_RANGE
        if ability in AIM_RADIUS:
            # an area spell /play aims: the circle's radius and how far from you it may land
            e['radius'] = AIM_RADIUS[ability]
            e['range'] = AIM_RANGE
    else:
        rng, shape = cr.ABILITY_RANGE.get(ability, (None, None))
        if ability in SELF_SKILLS or shape == 'self':
            e['target'] = 'self'
        elif ability in GROUP_SKILLS:
            e['target'] = 'group'
        elif ability in ALLY_SKILLS:
            e['target'] = 'ally'
            e['range'] = rng or None
        elif str(shape or '').startswith('nova'):
            e['target'] = 'area'
            try:
                e['range'] = float(str(shape).split(':')[1])
            except (IndexError, ValueError):
                pass
        else:
            e['target'] = 'enemy'
            e['range'] = rng or cr.MELEE
        if cls == 'warrior':
            try:
                from warrior_abilities import ABILITY_COOLDOWNS
                if ability in ABILITY_COOLDOWNS:
                    e['cd'] = ABILITY_COOLDOWNS[ability]
            except Exception:
                pass
        if ability in QUEST_ABILITIES:
            try:
                from marquee_abilities import COOLDOWNS
                e['cd'] = COOLDOWNS.get(ability)
            except Exception:
                pass
    return e


_BOOKS = {}


def book(cls):
    """The class's abilities for the 3D client's spellbook: what each is, costs, reaches and
    unlocks at, plus the ones a talent can teach (static: the client fetches it once)."""
    cls = str(cls or '').lower()
    if cls in _BOOKS:
        return _BOOKS[cls]
    out = [_entry(cls, a, kind, unlock_level(cls, a)) for a, kind in roster(cls)]
    have = {e['id'] for e in out}
    try:
        from talents import CLASS_TALENT_TREES
        from spells import SPELLS
        for tree in CLASS_TALENT_TREES.get(cls, []):
            for t in tree['talents'].values():
                a = (getattr(t, 'effects', None) or {}).get('skill_unlock')
                if a and a not in have:
                    have.add(a)
                    out.append(_entry(cls, a, 'spell' if a in SPELLS else 'skill', None, talent=tree.get('name'),
                                      note=getattr(t, 'description', '') or ''))
    except Exception:
        pass
    _BOOKS[cls] = out
    return out


# ------------------------------------------------------------------ hooks
_REFUSED = ("you don't know", 'huh?', 'not ready', 'cooldown', 'must wait', 'not enough', 'too exhausted',
            'who?', 'not here', 'nobody', 'you need to', "can't do that", 'cannot do that', 'no one by that name',
            "aren't fighting", 'must be fighting', 'not fighting', 'you are already', 'only usable', 'must be in combat')
_FAILED = ('you fail', 'failed', 'you miss', 'misses', 'fumble', 'dodges', 'parries', 'blocks your', 'resists', 'evades')


def _methods():
    """{command method name: {abilities it performs}} over every class roster and talent."""
    from commands import CommandHandler
    import commands
    renames = getattr(commands, '_SKILL_RENAMES', {})
    abilities = set()
    from config import Config
    for cls in Config.CLASSES:
        abilities.update(a for a, kind in roster(cls) if kind == 'skill')
    try:
        from talents import CLASS_TALENT_TREES
        from spells import SPELLS
        for trees in CLASS_TALENT_TREES.values():
            for tree in trees:
                for t in tree['talents'].values():
                    a = (getattr(t, 'effects', None) or {}).get('skill_unlock')
                    if a and a not in SPELLS:
                        abilities.add(a)
    except Exception:
        pass
    out = {}
    for a in abilities - PASSIVE:
        names = {a, renames.get(a), CommandHandler.ALIASES.get(a), CommandHandler.COMMAND_ALIASES.get(a.replace('_', ''))}
        for n in filter(None, names):
            n = CommandHandler.ALIASES.get(n, n)
            if getattr(CommandHandler, f'cmd_{n}', None) is not None:
                out.setdefault(f'cmd_{n}', set()).add(a)
    return out


def _mine(player, candidates):
    """Which of a command's abilities belongs to this player (class roster, or a talent)."""
    cls = str(getattr(player, 'char_class', '') or '').lower()
    owned = {a for a, _k in roster(cls)}
    for a in candidates:
        if a in owned:
            return a, True
    for a in candidates:
        if pct_of(player, a) > 0:
            return a, False
    return None, False


def class_abilities():
    """Every ability any class can learn (rosters and talents): the ones these rules govern."""
    from config import Config
    out = set()
    for cls in Config.CLASSES:
        out.update(a for a, _k in roster(cls))
    try:
        from talents import CLASS_TALENT_TREES
        for trees in CLASS_TALENT_TREES.values():
            for tree in trees:
                for t in tree['talents'].values():
                    a = (getattr(t, 'effects', None) or {}).get('skill_unlock')
                    if a:
                        out.add(a)
    except Exception:
        pass
    return out


def install():
    """Gate class abilities by what the character has learned, and let each use improve it."""
    from commands import CommandHandler
    from player import Player

    def wrap(method_name, candidates):
        orig = getattr(CommandHandler, method_name)

        async def run(cls, player, args, *rest, **kw):
            if not hasattr(player, 'skills') or not hasattr(player, 'char_class'):
                return await orig(player, args, *rest, **kw)
            ability, in_roster = _mine(player, candidates)
            if ability is None:
                return await orig(player, args, *rest, **kw)
            pct = pct_of(player, ability)
            if in_roster and pct <= 0:
                c = player.config.COLORS
                lvl = unlock_level(player.char_class, ability)
                if ability in QUEST_ABILITIES:
                    when = (f"it is earned through {QUEST_ABILITIES[ability]}, which your guild's trainer "
                            f"offers from level {lvl}")
                else:
                    when = f"it comes at level {lvl}" if lvl > (player.level or 1) else "type 'skills' to see what you know"
                await player.send(f"{c['yellow']}You don't know {name_of(ability).lower()} yet — {when}.{c['reset']}")
                return
            # watch what the ability says (refused? missed?), passing everything through
            lines = []
            had = 'send' in player.__dict__
            prev_send = player.__dict__.get('send')
            inner = player.send

            async def tee(msg='', *a, **k):
                lines.append(str(msg))
                return await inner(msg, *a, **k)
            player.send = tee
            player._mastery_hit = None
            prev_scale = getattr(player, '_ability_scale', 1)
            player._ability_scale = power(pct)
            try:
                result = await orig(player, args, *rest, **kw)
            finally:
                player._ability_scale = prev_scale
                if had:
                    player.send = prev_send
                else:
                    try:
                        del player.send
                    except AttributeError:
                        pass
            text = ' '.join(lines).lower()
            if getattr(player, '_mastery_hit', None) != ability and not any(w in text for w in _REFUSED):
                await improve(player, ability, ok=not any(w in text for w in _FAILED))
            return result

        setattr(CommandHandler, method_name, classmethod(run))

    for method_name, candidates in _methods().items():
        wrap(method_name, candidates)

    # the old improve paths (sneak, hide, backstab, picking a lock...) follow the same rules
    # for class abilities; crafting and gathering keep their own
    governed = class_abilities()
    orig_skill, orig_spell = Player.improve_skill, Player.improve_spell

    async def improve_skill(self, skill_name, difficulty=5):
        if skill_name in governed:
            await improve(self, skill_name, ok=True)
        else:
            await orig_skill(self, skill_name, difficulty)

    async def improve_spell(self, spell_name):
        if spell_name in governed:
            await improve(self, spell_name, ok=True)
        else:
            await orig_spell(self, spell_name)

    Player.improve_skill = improve_skill
    Player.improve_spell = improve_spell


_GUILDS = {}


def guild_of(world, cls):
    """(room vnum, room name, trainer name) of the trainer who teaches a class, or None."""
    cls = str(cls or '').lower()
    if cls in _GUILDS:
        return _GUILDS[cls]
    found = None
    protos = getattr(world, 'mob_prototypes', {}) or {}
    teachers = {v: p for v, p in protos.items()
                if p.get('special') in ('trainer', 'guildmaster')
                and cls in [t.strip().lower() for t in str(p.get('trains_class') or '').split(',')]}
    for room in (getattr(world, 'rooms', {}) or {}).values():
        for r in getattr(room, 'mob_resets', None) or []:
            v = r.get('vnum') if isinstance(r, dict) else None
            if v in teachers:
                found = (room.vnum, getattr(room, 'name', ''), teachers[v].get('short_desc') or teachers[v].get('name', 'the trainer'))
                break
        if found:
            break
    _GUILDS[cls] = found
    return found
