"""Crowd control, the Misthollow way (features.tactics): no diminishing returns, two ideas instead.

Creatures learn your tricks. A creature remembers, for the fight, every school of hold that
landed on it (sleep, a root, a stun, blindness, a charm...): the same school again is resisted
by its profile's `adapt_rate` more each time (readable 15%, brutal 25%, bosses faster), up to
ADAPT_MAX, and it says so ("The troll's eyes narrow: it knows that frost now"). Another school
works as well as ever. It forgets when the fight is over.

Holds can be answered:
- `rouse <friend>`: shake a groupmate out of a stun or a magical sleep. It costs your next swing;
  once every ROUSE_EVERY seconds.
- fire burns away roots and webs: a fire blow or spell on someone entangled frees them;
- damage breaks sleep (a sleeper hit wakes) and a creature's charm (a mesmerised creature hit
  shakes it off, as in the old days).
"""
import asyncio
import time

ADAPT_MAX = 0.8
ROUSE_EVERY = 12.0
CREATURE_HOLDS = {'stunned', 'sleep', 'sleeping', 'charmed', 'entangled', 'slow', 'blind', 'silenced',
                  'paralyzed', 'feared'}
FIRE = {'fire', 'flame', 'burning'}

_school = None          # the school of the spell being applied (set around SpellHandler.apply_affect)


def _say(room, text):
    if room is None:
        return
    try:
        asyncio.get_event_loop().create_task(room.send_to_room(text))
    except Exception:
        pass


def resisted(mob, school) -> bool:
    """Whether a creature shrugs off a hold of this school (it has learned it); counts it if not."""
    import brain
    from .targeting import players_side
    if not brain.on('tactics') or players_side(mob) or not hasattr(mob, 'room'):
        return False
    b = brain.of(mob)
    seen = b.encounter.setdefault('cc_seen', {})
    n = seen.get(school, 0)
    chance = min(ADAPT_MAX, b.profile.get('adapt_rate', 0.15) * n)
    if n and b.rng.random() < chance:
        c = mob.config.COLORS
        _say(getattr(mob, 'room', None),
             f"{c['bright_yellow']}{mob.name}'s eyes narrow — it knows that {school} trick now and shrugs it off! "
             f"{c['yellow']}(try another kind){c['reset']}")
        b.note(f'resists {school}', chance, f'seen {n}x')
        return True
    seen[school] = n + 1
    b.encounter['fought_at'] = time.time()
    return False


def _wrap_affects():
    from spells import SpellHandler, SPELLS
    orig = SpellHandler.apply_affect.__func__

    async def apply_affect(cls, target, affect, duration, spell_name='unknown', caster_level=1, caster=None,
                           spell_key=None):
        global _school
        kind = (affect or {}).get('type')
        from .targeting import players_side
        if kind in CREATURE_HOLDS and caster is not None and players_side(caster) and not players_side(target):
            import combat_range as cr
            school = cr.spell_school(spell_key or spell_name, SPELLS.get(spell_key or ''), caster)
            if kind != 'stunned':                     # a stun is counted in CombatHandler.stun
                if resisted(target, school):
                    return
            prev, _school = _school, school
            try:
                return await orig(cls, target, affect, duration, spell_name, caster_level, caster, spell_key)
            finally:
                _school = prev
        return await orig(cls, target, affect, duration, spell_name, caster_level, caster, spell_key)

    SpellHandler.apply_affect = classmethod(apply_affect)


def _wrap_stun():
    from combat import CombatHandler
    orig = CombatHandler.stun.__func__

    def stun(cls, target, rounds=1):
        from .targeting import players_side
        if not players_side(target) and not cls.is_boss_mob(target):
            if resisted(target, _school or 'force'):
                return 'resist'
        return orig(cls, target, rounds)

    CombatHandler.stun = classmethod(stun)


def _break_free(ch, dealt, dtype):
    """What a blow undoes: fire frees the entangled; any hurt wakes a sleeper, breaks a charm."""
    from spells import SpellHandler
    flags = getattr(ch, 'affect_flags', None) or set()
    room = getattr(ch, 'room', None)
    c = ch.config.COLORS
    if str(dtype or '').lower() in FIRE and ('entangled' in flags or time.time() < (getattr(ch, 'rooted_until', 0) or 0)):
        SpellHandler._cleanse(ch, {'entangled'})
        ch.rooted_until = 0
        _say(room, f"{c['bright_red']}The flames burn away what bound {ch.name}!{c['reset']}")
    if 'sleeping' in flags or getattr(ch, 'position', None) == 'sleeping' and any(
            getattr(a, 'applies_to', None) == 'sleeping' for a in getattr(ch, 'affects', None) or []):
        SpellHandler._cleanse(ch, {'sleeping'})
        if getattr(ch, 'position', None) == 'sleeping':
            ch.position = 'fighting' if getattr(ch, 'fighting', None) else 'standing'
        _say(room, f"{c['yellow']}{ch.name} jolts awake!{c['reset']}")
    if 'charmed' in flags and not hasattr(ch, 'connection'):
        SpellHandler._cleanse(ch, {'charmed'})
        _say(room, f"{c['yellow']}{ch.name} shakes off the spell that held it!{c['reset']}")


def _wrap_damage(klass):
    orig = klass.take_damage

    async def take_damage(self, amount, *args, **kwargs):
        import brain
        if not brain.on('tactics'):
            return await orig(self, amount, *args, **kwargs)
        dtype = kwargs.get('damage_type', args[1] if len(args) > 1 else 'physical')
        hp0 = getattr(self, 'hp', 0)
        result = await orig(self, amount, *args, **kwargs)
        if hp0 - getattr(self, 'hp', hp0) > 0 and getattr(self, 'hp', 0) > 0:
            try:
                _break_free(self, hp0 - self.hp, dtype)
            except Exception:
                pass
        return result

    klass.take_damage = take_damage


async def rouse(player, args) -> bool:
    """rouse <friend>: shake a groupmate out of a stun or a sleep. False: not in play (Huh?)."""
    import brain
    if not brain.on('tactics'):
        return False
    from spells import SpellHandler
    c = player.config.COLORS
    if not args:
        await player.send("Rouse whom? (rouse <friend>)")
        return True
    who = player.find_target_in_room(' '.join(args))
    if who is None or who is player or not hasattr(who, 'connection'):
        await player.send("You can only rouse a friend standing here.")
        return True
    flags = getattr(who, 'affect_flags', None) or set()
    stunned = (getattr(who, 'stunned_rounds', 0) or 0) > 0
    asleep = 'sleeping' in flags or getattr(who, 'position', None) == 'sleeping'
    if not stunned and not asleep:
        await player.send(f"{who.name} needs no rousing.")
        return True
    now = time.time()
    left = getattr(player, 'rouse_cooldown_until', 0) - now
    if left > 0:
        await player.send(f"{c['yellow']}You can rouse someone again in {left:.0f}s.{c['reset']}")
        return True
    player.rouse_cooldown_until = now + ROUSE_EVERY
    player._skip_autoattack = True                 # it costs your next swing
    who.stunned_rounds = 0
    if asleep:
        SpellHandler._cleanse(who, {'sleeping'})
        if who.position == 'sleeping':
            who.position = 'fighting' if getattr(who, 'fighting', None) else 'standing'
    await player.send(f"{c['bright_green']}You shake {who.name} back to their senses!{c['reset']}")
    await who.send(f"{c['bright_green']}{player.name} shakes you back to your senses!{c['reset']}")
    if player.room:
        await player.room.send_to_room(f"{c['green']}{player.name} shakes {who.name} back to their senses!{c['reset']}",
                                       exclude=[player, who])
    return True


async def cmd_rouse(cls, player, args):
    """Shake a stunned or sleeping friend back to their senses (help rouse)."""
    if not await rouse(player, args):
        await player.send("Huh?")


def install():
    from mobs import Mobile
    from player import Player
    from commands import CommandHandler
    _wrap_affects()
    _wrap_stun()
    _wrap_damage(Mobile)
    _wrap_damage(Player)
    CommandHandler.cmd_rouse = classmethod(cmd_rouse)
