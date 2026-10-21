"""Where threat comes from (features.threat; threat.py has the numbers):

- Mobile.take_damage: the health a creature lost, times the attacker's class modifier;
- SpellHandler.apply_spell: health the player's side got back while creatures fought them, as
  threat on the healer, shared among those creatures (a group heal counts every one it healed).

Installed after combat_hooks, so the damage counted is what the blow really took.
"""
import time

from . import threat as threat_mod


def _wrap_damage():
    from mobs import Mobile
    orig = Mobile.take_damage

    async def take_damage(self, amount, *args, **kwargs):
        import brain
        if not brain.on('threat'):
            return await orig(self, amount, *args, **kwargs)
        attacker = kwargs.get('attacker', args[0] if args else None)
        hp0 = getattr(self, 'hp', 0)
        result = await orig(self, amount, *args, **kwargs)
        dealt = hp0 - getattr(self, 'hp', hp0)
        if dealt > 0 and attacker is not None and attacker is not self and brain._thinks_for_itself(self):
            from .targeting import players_side
            if players_side(attacker):
                b = brain.of(self)
                b.threat.add(attacker, dealt * threat_mod.threat_mod(attacker))
                b.encounter['fought_at'] = time.time()
        return result

    Mobile.take_damage = take_damage


def _wrap_heals():
    from spells import SpellHandler
    orig = SpellHandler.apply_spell.__func__

    async def apply_spell(cls, caster, target, spell, spell_name):
        import brain
        from .targeting import players_side
        room = getattr(caster, 'room', None)
        if not brain.on('threat') or room is None or not players_side(caster):
            return await orig(cls, caster, target, spell, spell_name)
        before = {ch: getattr(ch, 'hp', 0) for ch in room.characters if players_side(ch)}
        result = await orig(cls, caster, target, spell, spell_name)
        now = time.time()
        for ch, hp0 in before.items():
            gain = getattr(ch, 'hp', 0) - hp0
            if gain <= 0 or ch.room is not room:
                continue
            foes = [m for m in room.characters
                    if getattr(m, 'fighting', None) is ch and not players_side(m) and getattr(m, 'hp', 0) > 0]
            for m in foes:
                b = brain.of(m)
                b.threat.add(caster, gain * threat_mod.HEAL_SHARE / len(foes))
                b.encounter.setdefault('healed', {})[caster] = now
                b.encounter['fought_at'] = now
        return result

    SpellHandler.apply_spell = classmethod(apply_spell)


def install():
    _wrap_damage()
    _wrap_heals()
