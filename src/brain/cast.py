"""How creatures cast (features.tactics): spells from SPELLS, every one declared a round ahead.

- A caster knows the spells its role lists by level (world/ai_profiles.json roles.caster.spells).
  A harm spell lands through mob_ai._cast_offensive (its damage the creature's own, calibrated
  curve; resistance, reflection and the terrain as before). A hex puts the spell's own affects on
  its target through SpellHandler.apply_affect: a real blindness, slow, root or weakness with a
  duration, which Unfettered wards off, a cleanse lifts and the `rouse` of a friend can break
  (cc.py). The old "slow" was a lost turn.
- A creature never stacks more than its profile's `cc_chain` holds on one player in CC_WINDOW
  seconds (readable 1, brutal 3): a stun-lock isn't clever, it's tedious.
- Healers (and a hurt caster) heal by prayer, declared and interruptible, never instantly.
- Disrupt: an elite (or, in a brutal zone, a caster) that sees a player healing its foes fixes
  its eyes on them and gathers a word of silence: declared, interruptible, a few seconds' silence.
- A caster's ward is a real affect that runs out (armor), once a fight; no more permanent armour.

Every choice uses the brain's own dice (brain.rng): the world's random.* is never drawn on here.
"""
import time

# spell: (what it does to its target, harm multiplier, mana, kind, hex duration in affect ticks of 6 s)
SPELLBOOK = {
    'magic_missile':  ('launches magic missiles at',          1.2, 10, 'harm', 0),
    'chill_touch':    ('lays a freezing hand on',             1.3, 12, 'harm', 0),
    'burning_hands':  ('lashes out with burning hands at',    1.5, 15, 'harm', 0),
    'shadow_bolt':    ('fires a bolt of shadow at',           1.5, 15, 'harm', 0),
    'ice_storm':      ('conjures a storm of ice shards at',   1.8, 20, 'harm', 0),
    'lightning_bolt': ('calls down lightning upon',           2.0, 25, 'harm', 0),
    'fireball':       ('hurls a crackling fireball at',       2.5, 30, 'harm', 0),
    'weaken':         ('whispers a curse of weakness upon',   0, 15, 'hex', 4),
    'curse':          ('spits a withering curse at',          0, 15, 'hex', 4),
    'blindness':      ('gestures and a blinding flash engulfs', 0, 15, 'hex', 1),
    'slow':           ('weaves a spell of lethargy around',   0, 15, 'hex', 2),
    'entangle':       ('calls grasping roots up around',      0, 15, 'hex', 1),
}
HOLDS = {'blind', 'slow', 'entangled', 'sleep', 'sleeping', 'stunned', 'paralyzed', 'charmed', 'silenced', 'feared'}
CC_WINDOW = 18.0
HEAL_MANA = 15
DISRUPT_EVERY = 20.0
WARD = ('armor', 10)                # a caster's ward: the spell, and affect ticks it lasts


def _rng(mob):
    import brain
    return brain.of(mob).rng


def known(mob, b, kind=None) -> list:
    """The spells this creature's roles give it at its level, strongest harm last."""
    out = []
    for role in sorted(b.roles):
        bands = (b.profile.get('spells') if role == 'caster' else None) or {}
        for at, names in bands.items():
            if int(at) <= int(getattr(mob, 'level', 1) or 1):
                out += [n for n in names if n in SPELLBOOK and n not in out]
    if kind:
        out = [n for n in out if SPELLBOOK[n][3] == kind]
    return sorted(out, key=lambda n: SPELLBOOK[n][1])


def holds_on(target, now=None) -> int:
    """Holds creatures put on this player in the last CC_WINDOW seconds."""
    now = time.time() if now is None else now
    log = [t for t in (getattr(target, '_held_at', None) or []) if now - t < CC_WINDOW]
    try:
        target._held_at = log
    except AttributeError:
        pass
    return len(log)


def _note_hold(target):
    try:
        target._held_at = (getattr(target, '_held_at', None) or []) + [time.time()]
    except AttributeError:
        pass


def _under(target, key):
    """Already under this hex (its own affects)."""
    from spells import SPELLS
    flags = getattr(target, 'affect_flags', None) or set()
    names = {getattr(a, 'name', None) for a in (getattr(target, 'affects', None) or [])}
    sp = SPELLS.get(key) or {}
    return sp.get('name') in names or any(a.get('type') in flags for a in sp.get('affects') or [])


def choose(mob, b, target):
    """A caster's declared spell for this round, or None (mob_ai._choose_caster_intent's gates kept)."""
    import mob_ai
    now = time.time()
    if mob.mana < 10 or now < mob.ai_state.get('spell_cd', 0) or mob_ai._silenced(mob):
        return None
    if mob.hp < 0.4 * mob.max_hp and mob.mana >= HEAL_MANA + 10:
        return heal_intent(mob, b, mob)
    if not b.encounter.get('warded'):
        return None                                   # this round goes to its ward (_caster_tick)
    rng = b.rng
    if rng.random() > min(0.95, 0.6 * b.profile.get('special_rate', 1.0)):
        return None
    p = b.profile
    hexes = [h for h in known(mob, b, 'hex') if not _under(target, h)]
    if hexes and hasattr(target, 'connection') and holds_on(target, now) < p.get('cc_chain', 1):
        pick = None
        try:
            import combat_range as cr
            d = cr.distance(mob, target)
        except Exception:
            d = None
        if 'entangle' in hexes and d is not None and d > 6 and rng.random() < 0.5:
            pick = 'entangle'                         # it keeps its distance: root it
        elif rng.random() < 0.2:
            pick = rng.choice(hexes)
        if pick:
            mob.ai_state['spell_cd'] = now + 5
            return {'kind': 'debuff', 'label': pick.replace('_', ' ').title(), 'interruptible': True,
                    'ability': ('mob_hex', pick),
                    'telegraph': f'{mob.name} begins weaving a hex, fingers tracing sickly glowing sigils!'}
    harms = [h for h in known(mob, b, 'harm') if mob.mana >= SPELLBOOK[h][2]]
    if not harms:
        return None
    flags = getattr(target, 'affect_flags', None) or set()
    if p.get('root_and_nuke') and 'entangled' in flags:
        harms.sort(key=lambda n: -SPELLBOOK[n][1])   # it holds them still: the biggest it has
    else:
        harms.reverse()
    try:
        from environment import get_env
        env = get_env(mob.room)
        if env['water'] and getattr(mob.room, 'frozen_until', 0) <= now:
            harms.sort(key=lambda s: 0 if 'lightning' in s else 1)
        elif env['webbed'] and getattr(mob.room, 'burning_until', 0) <= now \
                and mob.hp < mob.max_hp * 0.6 and rng.random() < 0.25:
            harms.sort(key=lambda s: 0 if 'fire' in s else 1)
    except Exception:
        pass
    key = harms[0]
    verb, mult, mana, _, _ = SPELLBOOK[key]
    mob.ai_state['spell_cd'] = now + 4
    return {'kind': 'cast', 'label': key.replace('_', ' ').title(), 'interruptible': True,
            'ability': ('caster_offensive', (key, verb, mult, mana)),
            'telegraph': f'{mob.name} begins an incantation — arcane power crackles around it!'}


async def ward(mob, b):
    """A caster's ward (armor), once a fight, as a real affect that runs out. True if it cast it."""
    if b.encounter.get('warded') or mob.mana < 15:
        return False
    b.encounter['warded'] = True
    from spells import SPELLS, SpellHandler
    sp = SPELLS.get(WARD[0]) or {}
    for a in sp.get('affects') or ():
        await SpellHandler.apply_affect(mob, dict(a), WARD[1], sp.get('name', 'armor'), getattr(mob, 'level', 1),
                                        caster=mob, spell_key=WARD[0])
    mob.mana -= 15
    mob.ai_state['spell_cd'] = time.time() + 4
    c = mob.config.COLORS
    await mob.room.send_to_room(f"{c['bright_magenta']}{mob.name} murmurs arcane words and a shimmering aura surrounds them!{c['reset']}")
    return True


async def resolve_hex(mob, target, key):
    """A declared hex lands: the spell's own affects, for its duration."""
    from spells import SPELLS, SpellHandler
    import mob_ai
    c = mob.config.COLORS
    verb, _, mana, _, ticks = SPELLBOOK[key]
    mob.mana = max(0, mob.mana - mana)
    label = key.replace('_', ' ')
    if mob_ai._braced(target):
        await mob.room.send_to_room(f"{c['cyan']}{target.name} stands braced — the {label} washes over them harmlessly!{c['reset']}")
        return
    sp = SPELLS.get(key) or {}
    if SpellHandler._immune(target, sp):
        await mob.room.send_to_room(f"{c['cyan']}{target.name} is untouched by the {label}.{c['reset']}")
        return
    held = False
    for a in sp.get('affects') or ():
        await SpellHandler.apply_affect(target, dict(a), ticks, sp.get('name', label), getattr(mob, 'level', 1),
                                        caster=mob, spell_key=key)
        held = held or a.get('type') in HOLDS
    if held:
        _note_hold(target)
    await mob.room.send_to_room(f"{c['bright_magenta']}{mob.name} {verb} {target.name}!{c['reset']}")
    if hasattr(target, 'send'):
        tip = ' (a friend can rouse you; Unfettered or a cleansing lifts it)' if held else ''
        await target.send(f"{c['yellow']}You feel the effects of {label}!{tip}{c['reset']}")


# ---------------------------------------------------------------- heals, declared
def _wounded_kin(mob):
    from .targeting import players_side
    best, best_pct = None, 1.0
    for ch in mob.room.characters:
        if ch is mob or players_side(ch) or not getattr(ch, 'is_alive', True) or getattr(ch, 'hp', 0) <= 0:
            continue
        if getattr(ch, 'fighting', None) is mob or 'charmed' in (getattr(ch, 'affect_flags', None) or ()):
            continue
        pct = ch.hp / max(1, ch.max_hp)
        if pct < best_pct and pct < 0.7:
            best, best_pct = ch, pct
    if mob.hp / max(1, mob.max_hp) < min(best_pct, 0.6):
        best = mob
    return best


def heal_intent(mob, b, who):
    if who is None or mob.mana < HEAL_MANA:
        return None
    mob.ai_state['spell_cd'] = time.time() + 5
    on = 'itself' if who is mob else who.name
    return {'kind': 'heal', 'label': 'Healing Prayer', 'interruptible': True, 'ability': ('mob_heal', who),
            'target': who, 'telegraph': f'{mob.name} begins a healing prayer over {on}!'}


def choose_heal(mob, b):
    """A healer's declared heal on the most wounded of its own side (or itself), or None."""
    if 'healer' not in b.roles or mob.mana < HEAL_MANA or time.time() < mob.ai_state.get('heal_cd', 0):
        return None
    import mob_ai
    if mob_ai._silenced(mob):
        return None
    who = _wounded_kin(mob)
    if who is None:
        return None
    mob.ai_state['heal_cd'] = time.time() + 5
    return heal_intent(mob, b, who)


async def resolve_heal(mob, who):
    c = mob.config.COLORS
    if who is None or getattr(who, 'hp', 0) <= 0 or who.room is not mob.room:
        await mob.room.send_to_room(f"{c['yellow']}{mob.name}'s prayer finds no one to mend and fades.{c['reset']}")
        return
    rng = _rng(mob)
    lv = int(getattr(mob, 'level', 1) or 1)
    heal = int(rng.randint(lv * 2, lv * 5) * 1.5)      # declared and answerable: a little more than the old instant one
    who.hp = min(who.max_hp, who.hp + heal)
    mob.mana = max(0, mob.mana - HEAL_MANA)
    if who is mob:
        await mob.room.send_to_room(f"{c['bright_cyan']}{mob.name} finishes the prayer and its wounds close! [+{heal} HP]{c['reset']}")
    else:
        await mob.room.send_to_room(f"{c['bright_cyan']}{mob.name} finishes the prayer and {who.name}'s wounds close! [+{heal} HP]{c['reset']}")


# ---------------------------------------------------------------- Disrupt: silence for your healer
def choose_disrupt(mob, b):
    """An elite or better (a caster too, in a brutal zone) silences the player who heals its foes."""
    now = time.time()
    p = b.profile
    able = p.get('rank') in ('elite', 'sub-boss', 'boss') or ('caster' in b.roles and p.get('tier') == 'brutal')
    if not able or p.get('focus_healers', 0) <= 0 or now < b.encounter.get('disrupt_at', 0):
        return None
    from .targeting import valid
    healed = b.encounter.get('healed') or {}
    lately = [(t, h) for h, t in healed.items() if now - t <= 10 and valid(mob, h) and hasattr(h, 'connection')]
    if not lately:
        return None
    healer = max(lately, key=lambda x: (b.threat.get(x[1]), x[0]))[1]
    if 'silenced' in (getattr(healer, 'affect_flags', None) or ()):
        return None
    b.encounter['disrupt_at'] = now + DISRUPT_EVERY
    return {'kind': 'disrupt', 'label': 'Disrupt', 'interruptible': True, 'ability': ('disrupt', healer),
            'target': healer, 'telegraph': f'{mob.name} fixes its eyes on {healer.name}, gathering a word of silence!'}


async def resolve_disrupt(mob, healer):
    from spells import SpellHandler
    import mob_ai
    c = mob.config.COLORS
    from .targeting import valid
    if not valid(mob, healer):
        await mob.room.send_to_room(f"{c['yellow']}{mob.name}'s word of silence finds no one.{c['reset']}")
        return
    if mob_ai._braced(healer):
        await mob.room.send_to_room(f"{c['cyan']}{healer.name} steels their mind — the word of silence breaks on them!{c['reset']}")
        return
    await SpellHandler.apply_affect(healer, {'type': 'silenced', 'value': 1}, 1, 'Disrupt', getattr(mob, 'level', 1), caster=mob)
    _note_hold(healer)
    await mob.room.send_to_room(f"{c['bright_magenta']}{mob.name} speaks a word of silence — {healer.name}'s voice dies in their throat!{c['reset']}")
    if hasattr(healer, 'send'):
        await healer.send(f"{c['yellow']}You are silenced! (a few seconds; a friend can't rouse this one away){c['reset']}")
