"""Combat v2 wiring: structured events and distance, laid over the existing combat code.

The combat code prints its log from ~120 places; rather than touching each, a few choke
points are wrapped once at startup (install()):

  CombatHandler.one_round   reach check (no blow lands from out of reach; the 3D client is
                            told to close in), then one 'attack' event per swing with its
                            result read from the very lines the log printed
  Player/Mobile.take_damage one 'dmg' event per wound with the amount actually applied (so
                            spells, damage over time and creature specials all show numbers);
                            a ranger shooting point-blank does reduced damage
  CombatHandler.handle_death, Player.die   'death'
  CommandHandler.execute    class abilities: range check first (nothing is spent when out
                            of reach), then an 'ability' event ahead of the wounds it caused;
                            every other class ability (and the extras below) gets its event
                            too, so each has its own look in 3D (sneaking and hiding are
                            shown only to the one doing it)
  mob_ai                    wind-ups get a ground area and a 'windup' event; when they land,
                            anyone who has stepped out of the area is spared ('resolve')

Positions and ranges live in combat_range.py; the event transport in combat_events.py.
Telnet players have no position, so for them every range check passes.
"""
import asyncio
import contextvars
import itertools
import logging
import time

import combat_events as ev
import combat_range as cr

logger = logging.getLogger('Misthollow')
_installed = False


def _is_player(ch):
    return hasattr(ch, 'account_name')


# the captures the running task is inside (asyncio gives each task its own copy of the context)
_CAPTURING = contextvars.ContextVar('combat_hooks_capturing', default=frozenset())
_capture_ids = itertools.count(1)


def _capture(ch, lines):
    """Record what `ch` is sent while a wrapped call runs (it is still delivered). Only what the
    call itself sends is recorded: a line another task sends meanwhile (the action tick's "You
    are stunned and cannot attack!") was taken for the skill's refusal, and a kick that landed
    lost its cooldown and its event."""
    if ch is None or not hasattr(ch, 'send'):
        return lambda: None
    had = 'send' in getattr(ch, '__dict__', {})
    own = ch.__dict__.get('send') if had else None
    real = ch.send
    me = next(_capture_ids)

    async def send(msg='', *a, **k):
        if me in _CAPTURING.get():
            lines.append(str(msg))
        return await real(msg, *a, **k)

    try:
        ch.send = send
    except Exception:
        return lambda: None
    _CAPTURING.set(_CAPTURING.get() | {me})

    def restore():
        _CAPTURING.set(_CAPTURING.get() - {me})
        try:
            if had:
                ch.send = own
            else:
                del ch.send
        except Exception:
            pass
    return restore


def _hold_output(ch, lines):
    """Keep what `ch` is sent while a wrapped call runs, undelivered (see _wrap_execute)."""
    if ch is None or not hasattr(ch, 'send'):
        return lambda: None
    had = 'send' in getattr(ch, '__dict__', {})
    own = ch.__dict__.get('send') if had else None

    async def send(msg='', *a, **k):
        lines.append((msg, a, k))

    try:
        ch.send = send
    except Exception:
        return lambda: None

    def restore():
        try:
            if had:
                ch.send = own
            else:
                del ch.send
        except Exception:
            pass
    return restore


_NOT_FIGHTING = ('must be fighting', "aren't fighting anyone", 'not fighting anyone', 'you need to be fighting',
                 'only usable in combat', 'must be in combat')


def _plain(lines):
    import re
    return re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', ' '.join(lines)).lower()


def _outcome(text):
    if 'parr' in text:
        return 'parry'
    if 'block' in text and 'with your shield' in text or 'blocks your attack' in text or 'you block' in text:
        return 'block'
    if any(w in text for w in ('dodge', 'evade', 'untouchable', 'sidestep')):
        return 'dodge'
    if 'miss' in text or 'swing blindly' in text or 'swings blindly' in text:
        return 'miss'
    return None


def _weapon_kind(ch):
    eq = getattr(ch, 'equipment', None) or {}
    w = eq.get('wield') if isinstance(eq, dict) else None
    return getattr(w, 'weapon_type', None) if w else None


def _reach_of(ch):
    """(reach in metres, ranged?) of a combatant's ordinary blow."""
    if _is_player(ch):
        return cr.auto_range(ch)
    reach, _prefer = cr.mob_reach(ch)
    return reach, reach > cr.MELEE + 0.5


# ------------------------------------------------------------------ the round
def _wrap_one_round():
    from combat import CombatHandler
    orig = CombatHandler.one_round.__func__

    async def one_round(cls, attacker, defender):
        room = getattr(attacker, 'room', None)
        if room is None or defender is None:
            return await orig(cls, attacker, defender)
        reach, ranged = _reach_of(attacker)
        d = cr.distance(attacker, defender)
        if d is not None and d > reach + 0.4 and getattr(attacker, 'fighting', None) is defender:
            # out of reach: no blow this round. Creatures close in on their own
            # (combat_range.move_tick); a hero is told, and the 3D client walks in.
            if _is_player(attacker):
                now = time.time()
                if now - getattr(attacker, '_oor_said', 0) > 6:
                    attacker._oor_said = now
                    c = attacker.config.COLORS
                    await attacker.send(f"{c['yellow']}{defender.name} is out of reach ({d:.0f} m) — "
                                        f"{'close in' if not ranged else 'get within ' + str(int(reach)) + ' m'}!{c['reset']}")
                ev.emit(room, 'oor', src=attacker, dst=defender, need=round(reach, 1), dist=round(d, 1), auto=True)
            return
        # a bow loosed point-blank lands poorly
        scale = 0.6 if ranged and _is_player(attacker) and d is not None and d < cr.POINT_BLANK else 1
        if scale != 1:
            attacker._dmg_scale = scale
        lines = []
        undo_a, undo_d = _capture(attacker, lines), _capture(defender, lines)
        hp0 = getattr(defender, 'hp', 0)
        attacker._swing_res = None
        with ev.hold():
            mark = ev.mark(room)
            try:
                await orig(cls, attacker, defender)
            finally:
                undo_a(); undo_d()
                if scale != 1:
                    attacker._dmg_scale = 1
            text = _plain(lines)
            wounded = getattr(defender, 'hp', 0) < hp0
            # the round says what became of the swing (combat.py _swing_res); its words are the
            # fallback for a round that didn't say
            told = getattr(attacker, '_swing_res', None)
            if told in ('hit', 'crit', 'miss', 'dodge', 'parry', 'block'):
                res = told
            elif told == 'skip':
                res = None
            else:
                res = ('crit' if 'critical hit' in text else 'hit') if wounded or 'damage]' in text else _outcome(text)
            if res:
                ev.emit_at(room, mark, 'attack', src=attacker, dst=defender, res=res, ranged=ranged or None,
                           weapon=_weapon_kind(attacker), perfect=('perfect strike' in text) or None,
                           style=cr.mob_style(attacker) if ranged and not _is_player(attacker) else None)
        if scale != 1 and wounded and _is_player(attacker) and time.time() - getattr(attacker, '_pb_said', 0) > 9:
            attacker._pb_said = time.time()
            c = attacker.config.COLORS
            tip = ("Too close for a clean shot — step back to draw properly." if cr.wielded_kind(attacker) in cr.WEAPON_RANGE
                   else "Too close to shape your bolts — step back to cast cleanly.")
            await attacker.send(f"{c['yellow']}{tip}{c['reset']}")
        # what the swing came to: None (no turn), {'res': 'skip'} (the turn was lost) or the blow
        outcome = told or res
        if not outcome:
            return None
        import action_combat
        action_combat.turn_taken(attacker)
        return {'res': outcome, 'amt': getattr(attacker, '_swing_amt', 0) if outcome in ('hit', 'crit') else 0,
                'perfect': 'perfect strike' in text}

    CombatHandler.one_round = classmethod(one_round)


# ------------------------------------------------------------------ wounds and deaths
def _wrap_take_damage(klass):
    orig = klass.take_damage

    async def take_damage(self, amount, *args, **kwargs):
        attacker = kwargs.get('attacker', args[0] if args else None)
        dtype = kwargs.get('damage_type', args[1] if len(args) > 1 else 'physical')
        # a point-blank bow (_dmg_scale) and how well the ability is known (mastery.py)
        scale = (getattr(attacker, '_dmg_scale', 1) * getattr(attacker, '_ability_scale', 1)) if attacker is not None else 1
        if scale != 1:
            amount = max(1, int(amount * scale))
        room = getattr(self, 'room', None)
        hp0 = getattr(self, 'hp', 0)
        result = await orig(self, amount, *args, **kwargs)
        dealt = hp0 - getattr(self, 'hp', hp0)
        if dealt > 0 and room is not None:
            ev.emit(room, 'dmg', src=attacker, dst=self, amt=int(dealt), left=max(0, int(getattr(self, 'hp', 0))),
                    school=None if dtype in (None, 'physical', 'magic') else fx_school(str(dtype)))
        return result

    klass.take_damage = take_damage


def _wrap_deaths():
    from combat import CombatHandler
    from player import Player
    orig = CombatHandler.handle_death.__func__

    async def handle_death(cls, killer, victim, *a, **k):
        if victim is not None and getattr(victim, 'room', None) is not None and not getattr(victim, '_death_evented', False):
            try:
                victim._death_evented = True
            except Exception:
                pass
            ev.emit(victim.room, 'death', src=killer, dst=victim)
        return await orig(cls, killer, victim, *a, **k)

    CombatHandler.handle_death = classmethod(handle_death)
    orig_die = Player.die

    async def die(self, *a, **k):
        if getattr(self, 'room', None) is not None:
            ev.emit(self.room, 'death', dst=self)
        return await orig_die(self, *a, **k)

    Player.die = die


# ------------------------------------------------------------------ class abilities
# class abilities that are in no class's book (combo finishers, lay on hands, raising the
# dead...) and how they are aimed, so the 3D client animates them too
EXTRA_ABILITIES = {      # command: (aimed at, the classes that use it)
    'mortal_strike': ('enemy', 'warrior'), 'protect': ('ally', 'warrior paladin'),
    'eviscerate': ('enemy', 'thief'), 'kidneyshot': ('enemy', 'thief'), 'slicedice': ('self', 'thief'),
    'fade': ('self', 'thief'),       # (vanish) the assassin's fade, which thieves use too
    'layhands': ('ally', 'paladin'), 'aura': ('self', 'paladin'),
    'raise': ('self', 'necromancer'), 'animate': ('self', 'necromancer cleric'), 'imbue': ('self', 'necromancer'),
    'ritual': ('self', 'necromancer'), 'soulstone': ('self', 'necromancer'),
    'summon': ('self', 'mage'), 'shadowform': ('self', 'cleric'), 'perform': ('self', 'bard'),
}
# the marquee abilities' later moments, played as abilities of their own (marquee_abilities.BEATS)
try:
    from marquee_abilities import BEATS as _BEATS
    EXTRA_ABILITIES.update(_BEATS)
except Exception:
    pass
# the argument picks how these look (a song, an elemental, an aura): it goes in the event
VARIANT_ABILITIES = frozenset({'perform', 'summon', 'raise', 'aura'})
# moves nobody else should see you make
PRIVATE_ABILITIES = frozenset({'sneak', 'hide', 'camouflage', 'camouflage_master'})
_SHAPE_OF_AIM = {'self': 'self', 'area': 'nova:8', 'group': 'nova:12', 'ally': 'ranged', 'object': 'self',
                 'special': 'self', 'enemy': 'melee'}
_BY_METHOD = None


def _canonical(cmd):
    from commands import CommandHandler
    c = CommandHandler.ALIASES.get(cmd, cmd)
    return CommandHandler.COMMAND_ALIASES.get(c, c)


def _joined(cmd, args):
    """The command that really runs for multi-word input ("song of the ages", "unbroken
    banner") — joined the way CommandHandler.execute joins it — and the args left over."""
    from commands import CommandHandler
    c = str(_canonical(cmd) or '').lower()
    words = [str(a).lower() for a in (args or [])]
    for n in (3, 2):
        if len(words) >= n and getattr(CommandHandler, f"cmd_{'_'.join([c] + words[:n])}", None):
            return '_'.join([c] + words[:n]), list(args[n:])
    if words and not getattr(CommandHandler, f'cmd_{c}', None) and getattr(CommandHandler, f'cmd_{c}_{words[0]}', None):
        return f'{c}_{words[0]}', list(args[1:])
    return cmd, list(args or [])


# what a refused skill or cast says (no animation; in action mode its cooldown second comes back)
_REFUSALS = ("you don't know", 'huh?', 'not ready', 'cooldown', 'must wait', 'not enough',
             'too exhausted', 'you need', "can't", 'cannot', 'who?', 'not here', 'nobody')


def _ability_of(cmd, args):
    """(ability key, remaining args) when a command is a ranged-checked class ability."""
    c = _canonical(cmd)
    if args:
        combo = f"{c}_{args[0]}".lower()
        if combo in cr.ABILITY_RANGE:
            return combo, args[1:]
    if c and c.lower() in cr.ABILITY_RANGE and c.lower() not in ('heal', 'bless', 'sleep'):
        return c.lower(), args
    return None, args


def _class_ability(player, cmd):
    """The book id of any other class ability a command performs (renamed ones too:
    `aimed_shot` is the truesight shot), an extra (eviscerate, lay on hands), else None."""
    global _BY_METHOD
    import mastery
    if _BY_METHOD is None:
        _BY_METHOD = mastery._methods()
    c = str(_canonical(cmd) or '').lower()
    cands = _BY_METHOD.get(f'cmd_{c}')
    if cands:
        mine, _owned = mastery._mine(player, cands)
        return mine or (c if c in cands else sorted(cands)[0])
    return c if c in EXTRA_ABILITIES else None


def aim_of(ability, cls=None):
    """enemy | ally | self | area | group: what an ability is aimed at (its book entry)."""
    import mastery
    entry = next((e for e in mastery.book(cls) if e['id'] == ability), None) if cls else None
    if entry is None and ability in EXTRA_ABILITIES:
        return EXTRA_ABILITIES[ability][0]
    return (entry or {}).get('target', 'enemy')


def event_shape(ability, cls=None):
    """How an ability is aimed, for its event: its range entry, else what its book says."""
    if ability in cr.ABILITY_RANGE:
        return cr.ABILITY_RANGE[ability][1]
    return _SHAPE_OF_AIM.get(aim_of(ability, cls), 'melee')


def _ref_word(player, arg):
    """'#12' -> a keyword (or 'N.keyword') naming that creature in the player's room."""
    if not (isinstance(arg, str) and arg.startswith('#') and arg[1:].isdigit()):
        return arg
    finder = getattr(player, 'find_target_in_room', None)
    ch = finder(arg) if finder else None
    room = getattr(player, 'room', None)
    if ch is None or room is None:
        return arg
    words = [w for w in str(getattr(ch, 'name', '') or '').lower().replace(',', ' ').split() if w.isalpha()]
    matches = getattr(player, 'matches_character', None)
    for kw in words or ['mob']:
        same = [c for c in room.characters if c is not player and (matches(c, kw) if matches else kw in str(getattr(c, 'name', '')).lower())]
        if ch in same:
            n = same.index(ch) + 1
            return kw if n == 1 else f'{n}.{kw}'
    return arg


def _wrap_execute():
    from commands import CommandHandler
    orig = CommandHandler.execute.__func__

    async def execute(cls, player, cmd, args):
        # "#12" (the 3D client's exact creature id) becomes the keyword every command's own
        # target matching understands ("wolf", or "2.wolf" when another wolf comes first)
        if args and any(isinstance(a, str) and a.startswith('#') and a[1:].isdigit() for a in args):
            args = [_ref_word(player, a) for a in args]
        name, rest = (None, args)
        try:
            if _is_player(player) and getattr(player, 'room', None) is not None and cmd:
                # typed with spaces ("wings of dawn") it is the joined command that runs
                jcmd, jargs = _joined(cmd, list(args or []))
                name, rest = _ability_of(jcmd, jargs)
                if not name:
                    # every other class ability: no reach to check, but the 3D client draws it
                    name, rest = _class_ability(player, jcmd), jargs
        except Exception:
            name = None
        # action mode (action_combat.py): skills and casts one a second; a refused one gives
        # its second back
        import action_combat
        gcd = action_combat.gcd_applies(player, cmd, name)
        if gcd:
            if await action_combat.gcd_refuse(player):
                return
            gcd_before = getattr(player, 'gcd_until', 0)
            action_combat.gcd_start(player)
        if not name:
            if not gcd:
                return await orig(cls, player, cmd, args)
            cast_lines = []
            undo_cast = _capture(player, cast_lines)
            try:
                return await orig(cls, player, cmd, args)
            finally:
                undo_cast()
                if any(w in _plain(cast_lines) for w in _REFUSALS):
                    player.gcd_until = gcd_before
                action_combat.tell(player)
        klass = str(getattr(player, 'char_class', '') or '').lower()
        rng, shape = cr.ABILITY_RANGE.get(name) or (None, event_shape(name, klass))
        target = None
        if rest:
            try:
                target = player.find_target_in_room(rest[0])
            except Exception:
                target = None
        ally = aim_of(name, klass) == 'ally'
        if target is None:
            # a heal or a guard with nobody named is for yourself; anything else for your foe
            target = player if ally else getattr(player, 'fighting', None)
        room = player.room
        d = (cr.distance(player, target) if rng is not None and target is not None and shape not in ('self',)
             and not shape.startswith('nova') else None)
        if d is not None and d > rng + 0.4:
            c = player.config.COLORS
            label = name.replace('_', ' ')
            await player.send(f"{c['yellow']}{target.name} is too far for {label} ({d:.0f} m; it reaches {rng:g} m).{c['reset']}")
            ev.emit(room, 'oor', src=player, dst=target, ability=name, need=rng, dist=round(d, 1))
            if gcd:
                player.gcd_until = gcd_before     # nothing was used: no cooldown
                action_combat.tell(player)
            return
        lines = []
        # one hold around the whole use (an opener's refusal, the fight it starts, the real use):
        # its mark and its wounds stay in this action, so the ability leads them
        with ev.hold():
            mark = ev.mark(room)
            opener = (target is not None and not _is_player(target) and getattr(player, 'fighting', None) is None
                      and getattr(target, 'room', None) is room and getattr(target, 'hp', 0) > 0
                      and shape != 'self' and not shape.startswith('nova'))
            if opener:
                # Not yet fighting: many skills refuse ("You must be fighting!"). Aimed at a
                # creature in reach, the skill opens the fight instead, as its first blow.
                held = []
                undo = _hold_output(player, held)
                try:
                    with ev.hold():
                        await orig(cls, player, cmd, args)
                finally:
                    undo()
                if any(w in _plain([m for m, _a, _k in held]) for w in _NOT_FIGHTING):
                    from combat import CombatHandler
                    await CombatHandler.start_combat(player, target, first_strike=False)
                    opener = False      # now fighting: use it for real below
                else:
                    for m, a, k in held:
                        await player.send(m, *a, **k)
                    lines = [m for m, _a, _k in held]
            if not opener:
                undo = _capture(player, lines)
                try:
                    with ev.hold():
                        await orig(cls, player, cmd, args)
                finally:
                    undo()
            text = _plain(lines)
            if any(w in text for w in _REFUSALS):
                if gcd:
                    player.gcd_until = gcd_before
                    action_combat.tell(player)
                return   # refused by the ability itself: no animation
            if gcd:
                action_combat.tell(player)
            tgt = target if target is not None else getattr(player, 'fighting', None)
            res = _outcome(text) if not ally else None
            if shape == 'dash' and tgt is not None and cr.pos_of(tgt) is not None:
                tx, tz = cr.pos_of(tgt)
                px, pz = cr.pos_of(player) or (tx, tz)
                dx, dz = px - tx, pz - tz
                dd = max(0.01, (dx * dx + dz * dz) ** 0.5)
                cr.set_pos(player, tx + dx / dd * 1.4, tz + dz / dd * 1.4)
            variant = str(rest[0]).lower()[:24] if name in VARIANT_ABILITIES and rest else None
            if name in PRIVATE_ABILITIES:
                ev.emit_private(player, 'ability', src=player, ability=name, shape=shape)
                return
            ev.emit_at(room, mark, 'ability', src=player, dst=tgt if shape not in ('self',) else None,
                       ability=name, res=res, shape=shape, variant=variant)

    CommandHandler.execute = classmethod(execute)


# ------------------------------------------------------------------ creature wind-ups
def _area_for(mob, intent):
    """Where a declared special will land, in room metres (None without positions)."""
    target = getattr(mob, 'fighting', None)
    mp, tp = cr.pos_of(mob), cr.pos_of(target) if target is not None else None
    kind = intent.get('kind')
    if kind == 'aoe' and mp:
        return {'shape': 'circle', 'r': 4.0, 'on': 'src', 'x': round(mp[0], 2), 'z': round(mp[1], 2)}
    if kind in ('heavy', 'cast') and tp:
        # the blow (or the bolt) comes down where you stood when it began
        return {'shape': 'circle', 'r': 2.0 if kind == 'heavy' else 1.7, 'x': round(tp[0], 2), 'z': round(tp[1], 2)}
    return None


def fx_school(school):
    """A kind of harm as the 3D client draws it (a disease looks like poison)."""
    return {'disease': 'poison', 'cold': 'frost'}.get(school, school)


def tick_event(character, affect, amount, heal=False):
    """A wound (or a mending) over time as the 3D client draws it: the same event as a blow's,
    with the name of what is doing it (`dot`), so the number rises small in its school's colour.
    (A tick lowers health itself, past take_damage, so it would otherwise go unseen.)"""
    room = getattr(character, 'room', None)
    if room is None or amount <= 0:
        return
    name = getattr(affect, 'name', '') or ''
    if heal:
        ev.emit(room, 'heal', dst=character, amt=int(amount), school='nature', dot=name)
    else:
        ev.emit(room, 'dmg', dst=character, amt=int(amount), left=max(0, int(getattr(character, 'hp', 0))),
                school=_school_of_label(name), dot=name)


def wore_off(character, affect):
    """An effect on a player has ended: their page fades it (a word over them, its icon gone)."""
    name = getattr(affect, 'name', None) or str(affect or '')
    if name and (hasattr(character, 'account_name') or getattr(character, 'is_player', False)):
        ev.emit_private(character, 'fade', dst=character, name=name)


def _wrap_gain_exp(klass):
    """Every experience gain tells the player's page (an 'xp' event): how much, its bonuses
    (boss, streak, rested), where it came from, and where the bar stands after it, so the XP bar
    fills as the number rises (and a new level is known at once)."""
    orig = klass.gain_exp

    async def gain_exp(self, amount, *args, **kwargs):
        level0 = getattr(self, 'level', 1)
        result = await orig(self, amount, *args, **kwargs)
        if amount and amount > 0 and getattr(self, 'room', None) is not None:
            breakdown = kwargs.get('breakdown') or (args[1] if len(args) > 1 else None) or {}
            source = 'kill' if breakdown.get('kill') else (kwargs.get('source') or (args[0] if args else 'other'))
            try:
                from map_system import _exp_thresholds
                floor, nxt = _exp_thresholds(self)
            except Exception:
                floor, nxt = 0, 0
            bonus = {k: int(v) for k, v in breakdown.items() if k in ('boss', 'streak', 'rested') and v}
            ev.emit_private(self, 'xp', dst=self, amt=int(amount), src_kind=str(source), bonus=bonus or None,
                            exp=int(getattr(self, 'exp', 0) or 0), floor=floor, next=nxt,
                            up=getattr(self, 'level', 1) if getattr(self, 'level', 1) != level0 else None)
        return result
    klass.gain_exp = gain_exp


def reward_event(player, k, **fields):
    """A kill's other rewards for the player's page: 'gold' (amt), 'rep' (faction, amt, standing)."""
    if getattr(player, 'room', None) is not None and (hasattr(player, 'account_name') or getattr(player, 'is_player', False)):
        ev.emit_private(player, k, dst=player, **fields)


def _watch_charges(klass):
    """A mage's arcane charges, watched: every change (gained, spent, decayed) tells their page
    at once ('res' event), so the pips by the portrait keep up without waiting for a refresh."""
    def get(self):
        return self.__dict__.get('_arcane_charges', 0)

    def put(self, value):
        old = self.__dict__.get('_arcane_charges', 0)
        self.__dict__['_arcane_charges'] = value
        if value != old and getattr(self, 'room', None) is not None:
            try:
                from spells import arcane_max
                ev.emit_private(self, 'res', dst=self, name='arcane', v=int(value or 0), max=arcane_max(self),
                                spent=bool(value < old))
            except Exception:
                pass
    klass.arcane_charges = property(get, put)


def _school_of_label(label):
    # the harm it deals (combat_range.harm_school); a summoning wind-up looks necrotic
    school = cr.harm_school(label)
    if school == 'physical' and 'summon' in (label or '').lower():
        return 'necrotic'
    return fx_school(school)


def _wrap_mob_ai():
    import mob_ai
    orig_declare = mob_ai.declare_intents

    async def declare_intents(mob):
        before = getattr(mob, 'pending_intent', None)
        # a creature only winds up a special it can deliver: a smash or a sweep from beside
        # you, a spell from within its casting range (it plants its feet while winding up)
        tgt = getattr(mob, 'fighting', None)
        d = cr.distance(mob, tgt) if tgt is not None and not before else None
        if d is not None and d > cr.mob_reach(mob)[0] + 1.5:
            return
        await orig_declare(mob)
        intent = getattr(mob, 'pending_intent', None)
        if intent and intent is not before and getattr(mob, 'room', None) is not None:
            intent['area'] = _area_for(mob, intent)
            import action_combat
            ms = (int(intent.get('windup_action', action_combat.WINDUP) * 1000) if action_combat.on_clock(mob)
                  else int((cr.round_seconds() + cr.NPC_PHASE_DELAY) * 1000))
            if time.time() < getattr(mob, 'slowed_until', 0):
                # slowed (marquee_abilities): the wind-up takes a round longer, and its mark says so
                intent['declared_at'] = intent.get('declared_at', time.time()) + cr.round_seconds()
                ms += int(cr.round_seconds() * 1000)
            ev.emit(mob.room, 'windup', src=mob, dst=intent.get('target') or getattr(mob, 'fighting', None), label=intent.get('label'),
                    kind=intent.get('kind'), ms=ms, area=intent['area'], school=_school_of_label(intent.get('label')),
                    interruptible=bool(intent.get('interruptible')) or None)

    mob_ai.declare_intents = declare_intents

    orig_resolve = mob_ai._resolve_intent

    async def _resolve_intent(mob):
        intent = getattr(mob, 'pending_intent', None)
        mob._resolving_intent = intent
        room = getattr(mob, 'room', None)
        with ev.hold():
            mark = ev.mark(room) if room is not None else None
            try:
                return await orig_resolve(mob)
            finally:
                mob._resolving_intent = None
                if intent and room is not None:
                    dodged = getattr(mob, '_dodged_by_position', None) or []
                    mob._dodged_by_position = []
                    ev.emit_at(room, mark, 'resolve', src=mob, label=intent.get('label'), kind=intent.get('kind'),
                               area=intent.get('area'), school=_school_of_label(intent.get('label')),
                               dodged=[ev.ref(c) for c in dodged] or None)

    mob_ai._resolve_intent = _resolve_intent

    # stepping out of the marked ground beats the blow (before brace/sidestep rolls)
    orig_mitigate = mob_ai._mitigate_hit

    async def _mitigate_hit(mob, char, damage):
        intent = getattr(mob, '_resolving_intent', None) or {}
        area = intent.get('area')
        if area and _outside(mob, char, area):
            c = mob.config.COLORS
            await mob.room.send_to_room(
                f"{c['bright_cyan']}{getattr(char, 'name', 'Someone')} is clear of {mob.name}'s {intent.get('label', 'blow')} — it hits only ground!{c['reset']}")
            lst = getattr(mob, '_dodged_by_position', None)
            if lst is None:
                mob._dodged_by_position = lst = []
            lst.append(char)
            return None
        return await orig_mitigate(mob, char, damage)

    mob_ai._mitigate_hit = _mitigate_hit

    orig_cast = mob_ai._cast_offensive

    async def _cast_offensive(mob, target, spell):
        intent = getattr(mob, '_resolving_intent', None) or {}
        area = intent.get('area')
        room = getattr(mob, 'room', None)
        name = spell[0] if isinstance(spell, (tuple, list)) else spell
        if room is not None:
            ev.emit(room, 'spell', src=mob, dst=target, spell=str(name), school=_school_of_label(str(name)))
        if area and target is not None and _outside(mob, target, area):
            c = mob.config.COLORS
            await room.send_to_room(f"{c['bright_cyan']}{target.name} slips out of the blast — {mob.name}'s spell scorches empty ground!{c['reset']}")
            return
        return await orig_cast(mob, target, spell)

    mob_ai._cast_offensive = _cast_offensive


def _wrap_intent_cancel(Mobile):
    """A wind-up can be broken before it lands: a stagger, a kick, a snare, death, the fight
    ending. Whatever clears a creature's pending intent outside its own resolution sends a
    'cancel', so the client takes the marked ground away at once."""
    def get(self):
        return self.__dict__.get('_pending_intent')

    def set_(self, value):
        old = self.__dict__.get('_pending_intent')
        self.__dict__['_pending_intent'] = value
        if not old or value is not None or getattr(self, '_resolving_intent', None) is old:
            return
        room = getattr(self, 'room', None)
        if room is None:
            return
        now = time.time()
        if getattr(self, 'hp', 1) <= 0 or getattr(self, 'position', '') == 'dead':
            reason = 'death'
        elif getattr(self, 'staggered_until', 0) > now:
            reason = 'stagger'
        elif getattr(self, 'fighting', None) is None:
            reason = 'end'
        elif getattr(self, 'stunned_rounds', 0) > 0:
            reason = 'snare'
        else:
            reason = 'interrupt'
        ev.emit(room, 'cancel', src=self, label=old.get('label'), reason=reason)

    Mobile.pending_intent = property(get, set_)


def _wrap_stuns(Character):
    """Stuns (bash, trips, snares, a stagger...) are set in many places as stunned_rounds;
    whenever it rises, the client gets a 'stun' with how long the stars should circle."""
    def get(self):
        return self.__dict__.get('_stunned_rounds', 0)

    def set_(self, value):
        old = self.__dict__.get('_stunned_rounds', 0) or 0
        self.__dict__['_stunned_rounds'] = value
        try:
            if (value or 0) > old and getattr(self, 'room', None) is not None and getattr(self, 'hp', 1) > 0:
                ev.emit(self.room, 'stun', dst=self, secs=round(min(4, value) * cr.round_seconds(), 1))
        except Exception:
            pass

    Character.stunned_rounds = property(get, set_)


def _outside(mob, char, area):
    p = cr.pos_of(char)
    if p is None:
        return False
    # the marked ground stays where it was marked (a creature winding up does not move)
    c = (area['x'], area['z']) if area.get('x') is not None else cr.pos_of(mob)
    if c is None:
        return False
    return ((p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2) ** 0.5 > area.get('r', 2) + 0.35


# ------------------------------------------------------------------ spells and heals
def _wrap_spells():
    from spells import SpellHandler
    orig_apply = SpellHandler.apply_spell.__func__

    async def apply_spell(cls, caster, target, spell, spell_name):
        room = getattr(caster, 'room', None)
        tgt = target if target is not None and target is not caster and not isinstance(target, str) else None
        hp0 = getattr(target, 'hp', None) if target is not None and not isinstance(target, str) else None
        lines = []
        undo = _capture(caster, lines)
        with ev.hold():
            mark = ev.mark(room) if room is not None else None
            try:
                result = await orig_apply(cls, caster, target, spell, spell_name)
            finally:
                undo()
            if room is not None:
                # the cast goes ahead of the wounds it caused, with how it went
                text = _plain(lines)
                res = ('resist' if any(w in text for w in ('resists your spell', 'shrugs off', 'unaffected'))
                       else 'immune' if 'immune' in text else None)
                # an aimed area spell lands where the caster put it: its centre and reach
                aim = getattr(caster, '_aim', None)
                ev.emit_at(room, mark, 'spell', src=caster, dst=tgt, spell=spell_name, res=res,
                           school=cr.spell_school(spell_name, spell, caster),
                           shape=f'blast:{aim[2]:g}' if aim else cr.ability_range(spell_name, True)[1],
                           at=[aim[0], aim[1]] if aim else None)
            if target is not None and hp0 is not None and getattr(target, 'hp', hp0) > hp0 and room is not None:
                ev.emit(room, 'heal', src=caster, dst=target, amt=int(target.hp - hp0), school=cr.spell_school(spell_name, spell, caster))
        return result

    SpellHandler.apply_spell = classmethod(apply_spell)


def install():
    global _installed
    if _installed:
        return
    _installed = True
    from player import Player, Character
    from mobs import Mobile
    for step in (_wrap_one_round, lambda: _wrap_take_damage(Player), lambda: _wrap_take_damage(Mobile),
                 _wrap_deaths, _wrap_execute, _wrap_mob_ai, _wrap_spells, lambda: _wrap_intent_cancel(Mobile),
                 lambda: _wrap_stuns(Character), lambda: _watch_charges(Player), lambda: _wrap_gain_exp(Player)):
        try:
            step()
        except Exception as e:
            logger.error(f"combat_hooks: {getattr(step, '__name__', 'step')} failed: {e}")
    logger.info("combat v2 hooks installed (events + range)")
