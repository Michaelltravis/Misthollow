"""Distance in combat (combat v2, 3D client).

Positions are metres inside a room (x 0..24 east, z 0..15 south, the 3D client's layout).
The web client reports where its hero stands; the server moves the creatures in a fight
(melee closes in, archers and casters keep their distance) and every blow, skill and spell
checks range. Telnet players have no position and are always treated as in reach, so
nothing changes for them.

Design (owner: "think about the classes and what ranges make sense"):
  the ordinary blow follows the weapon in hand (owner: "ranged attacks follow weapon"): a bow
  shoots from up to 16 m, a crossbow 14, a thrown weapon 10, and an archer fights poorly
  point-blank; anything else swings at 2.5 m, closing gaps with charges, trips and throws.
  Mages and necromancers throw a weak bolt from 10 m whatever they hold, and cast from
  14-20 m, but their touch spells need 2.5 m; heals, blessings and songs reach allies at
  12-15 m; shouts and novas hit everything around the user, area spells everything around a
  point. Rangers start with a bow.
"""
import math
import re
import time

MELEE = 2.5          # a sword's reach, edge to edge, generous for a top-down view
POINT_BLANK = 3.0    # too close to draw a bow well

# the ordinary blow: (reach in metres, ranged?), by the weapon in hand (gear_look.py's kind),
# else by class (a caster's bolt; everyone else at arm's length)
WEAPON_RANGE = {'bow': (16.0, True), 'crossbow': (14.0, True), 'thrown': (10.0, True)}
AUTO_RANGE = {
    'warrior': (MELEE, False), 'paladin': (MELEE, False), 'cleric': (MELEE, False),
    'thief': (MELEE, False), 'assassin': (MELEE, False), 'bard': (MELEE, False),
    'ranger': (MELEE, False), 'mage': (10.0, True), 'necromancer': (10.0, True),
}

# per ability: (range in metres, shape)
#   'melee' / 'ranged' — hits the target if within range
#   'self'             — no target needed
#   'nova:R'           — everything within R of the user
#   'blast:R'          — everything within R of the target (target within range)
#   'cone:R'           — everything within R in front of the user (90 degrees)
#   'dash'             — closes from up to range to melee (charge)
ABILITY_RANGE = {
    # warrior
    'bash': (MELEE, 'melee'), 'cleave': (MELEE + 0.5, 'cone:3'), 'kick': (MELEE, 'melee'),
    'execute': (MELEE, 'melee'), 'rally': (0, 'nova:8'), 'rescue': (6.0, 'ranged'),
    'charge': (15.0, 'dash'),
    # paladin
    'censure': (MELEE, 'melee'), 'order_verdict': (MELEE, 'melee'), 'holy_smite': (14.0, 'ranged'),
    'absolution': (12.0, 'ranged'), 'halo_of_reckoning': (0, 'nova:5'), 'turn_undead': (8.0, 'cone:8'),
    # ranger
    'truesight_shot': (18.0, 'ranged'), 'wildbond_strike': (MELEE, 'melee'), 'loosing_storm': (16.0, 'blast:3.5'),
    'quarry_mark': (20.0, 'ranged'), 'call_lightning': (16.0, 'ranged'),
    # thief / assassin
    'backstab': (MELEE, 'melee'), 'circle': (MELEE, 'melee'), 'trip': (MELEE, 'melee'), 'low_blow': (MELEE, 'melee'),
    'pocket_sand': (5.0, 'ranged'), 'jackpot': (MELEE, 'melee'), 'mark': (15.0, 'ranged'), 'expose': (MELEE, 'melee'),
    'vital': (MELEE, 'melee'), 'feint': (MELEE, 'melee'), 'execute_contract': (MELEE, 'melee'), 'fade': (0, 'self'), 'cover_tracks': (0, 'self'),
    # mage
    'magic_missile': (18.0, 'ranged'), 'fireball': (16.0, 'blast:3'), 'lightning_bolt': (18.0, 'ranged'),
    'chill_touch': (MELEE, 'melee'), 'sleep': (12.0, 'ranged'), 'towerbolt': (20.0, 'ranged'),
    # necromancer
    'soul_bolt': (16.0, 'ranged'), 'soul_siphon': (10.0, 'ranged'), 'animate_dead': (0, 'self'),
    'soul_reap': (14.0, 'blast:4'),
    # cleric
    'cure_light': (12.0, 'ranged'), 'heal': (12.0, 'ranged'), 'bless': (12.0, 'ranged'),
    'flamestrike': (14.0, 'blast:3'),
    # bard
    'mockery': (14.0, 'ranged'), 'fascinate': (12.0, 'ranged'), 'crescendo': (0, 'nova:6'),
    'discordant_note': (7.0, 'cone:7'),
    # shots and leaps from the level 31-60 abilities and the talents (a bow skill used to
    # walk the hero up to melee range before loosing)
    'heroic_throw': (15.0, 'ranged'), 'knife_toss': (14.0, 'ranged'),
    'heroic_leap': (15.0, 'dash'), 'shadowstrike': (12.0, 'dash'), 'death_from_above': (10.0, 'dash'),
    'volley': (16.0, 'blast:5'), 'serpent_sting': (16.0, 'ranged'), 'black_arrow': (18.0, 'ranged'),
    'wyvern_sting': (16.0, 'ranged'),
    # the marquee abilities (marquee_abilities.py): an entry also lets them be typed with spaces
    # ("unbroken banner") and still be drawn in 3D
    'unbroken_banner': (0, 'self'), 'singularity': (16.0, 'blast:6'), 'seraphs_vigil': (0, 'self'),
    'wings_of_dawn': (0, 'nova:6'), 'lich_ascension': (0, 'self'), 'heist': (0, 'self'),
    'heartseeker': (20.0, 'ranged'), 'song_of_the_ages': (0, 'self'), 'thousand_shadows': (0, 'self'),
}
DEFAULT_SPELL = (14.0, 'ranged')
DEFAULT_SKILL = (MELEE, 'melee')

# creatures: reach by role (mob_ai roles), and the distance they like to keep
ROLE_RANGE = {
    'archer': (15.0, 9.0), 'caster': (13.0, 8.0), 'healer': (12.0, 8.0), 'support': (12.0, 8.0),
}
MOB_MELEE = 2.2
MOB_SPEED = 3.4      # m/s closing in
NPC_PHASE_DELAY = 1.3   # creatures strike this long after heroes in a round (world.combat_tick)
ROOM_W, ROOM_H = 24.0, 15.0


def key(name):
    return str(name or '').strip().lower().replace(' ', '_').replace("'", '')


def ability_range(name, is_spell=False):
    return ABILITY_RANGE.get(key(name)) or (DEFAULT_SPELL if is_spell else DEFAULT_SKILL)


def wielded_kind(ch):
    """What kind of weapon is in hand ('bow', 'sword'...), as gear_look.py reads it; None."""
    eq = getattr(ch, 'equipment', None) or {}
    w = eq.get('wield') if isinstance(eq, dict) else None
    if w is None:
        return None
    kind = getattr(w, '_wield_kind', None)
    if kind is None:
        try:
            import gear_look
            kind = gear_look.weapon_piece(w).get('k') or ''
        except Exception:
            kind = ''
        try:
            w._wield_kind = kind            # an item's name does not change: read it once
        except Exception:
            pass
    return kind or None


def auto_range(ch):
    """(reach, ranged?) of a character's ordinary blow: the weapon's, else the class's."""
    weapon = WEAPON_RANGE.get(wielded_kind(ch))
    if weapon:
        return weapon
    return AUTO_RANGE.get(str(getattr(ch, 'char_class', '') or '').lower(), (MELEE, False))


def mob_reach(mob):
    """(reach, preferred distance) for a creature."""
    try:
        from map_system import _mob_roles
        roles = set(_mob_roles(mob))
    except Exception:
        roles = set()
    for role, rng in ROLE_RANGE.items():
        if role in roles:
            return rng
    return (MOB_MELEE, MOB_MELEE * 0.8)


def mob_style(mob):
    """How a ranged creature's ordinary attack looks: 'arrow' or 'bolt' (None: melee)."""
    try:
        from map_system import _mob_roles
        roles = set(_mob_roles(mob))
    except Exception:
        return None
    if 'archer' in roles:
        return 'arrow'
    if roles & {'caster', 'healer', 'support'}:
        return 'bolt'
    return None


# ---- positions ----
def pos_of(ch):
    """(x, z) in the combatant's current room, or None if unknown (telnet players)."""
    p = getattr(ch, 'web_pos', None)
    room = getattr(ch, 'room', None)
    if not p or not room or p[0] != getattr(room, 'vnum', None):
        return None
    return (p[1], p[2])


def set_pos(ch, x, z):
    room = getattr(ch, 'room', None)
    if room is None:
        return
    x = max(1.0, min(ROOM_W - 1.0, float(x)))
    z = max(1.0, min(ROOM_H - 1.0, float(z)))
    ch.web_pos = (room.vnum, x, z)


def distance(a, b):
    """Metres between two combatants, or None when either has no position."""
    pa, pb = pos_of(a), pos_of(b)
    if pa is None or pb is None:
        return None
    return math.hypot(pa[0] - pb[0], pa[1] - pb[1])


def in_reach(a, b, reach):
    d = distance(a, b)
    return True if d is None else d <= reach


def within(center, others, radius):
    """Combatants within radius of a point (x, z); unknown positions count as inside."""
    out = []
    for o in others:
        p = pos_of(o)
        if p is None or math.hypot(p[0] - center[0], p[1] - center[1]) <= radius:
            out.append(o)
    return out


def mob_seed(room, mobs):
    """Adopt the client's placement of creatures that have no position yet (both clients
    compute the same spots from the room layout, so the first report is as good as any)."""
    by_id = {}
    try:
        from map_system import _mob_uid
        for ch in getattr(room, 'characters', []) or []:
            if not hasattr(ch, 'account_name'):
                by_id[_mob_uid(ch)] = ch
    except Exception:
        return
    for m in mobs[:40]:
        try:
            mob = by_id.get(int(m.get('id')))
            if mob is not None and pos_of(mob) is None:
                set_pos(mob, float(m.get('x')), float(m.get('z')))
        except (TypeError, ValueError, AttributeError):
            continue


def round_seconds():
    try:
        from config import Config
        return float(getattr(Config, 'COMBAT_ROUND_SECONDS', 3.0))
    except Exception:
        return 3.0


# ---- what school a spell belongs to (the 3D client picks its colours and shapes) ----
_SCHOOL_WORDS = (
    ('fire', 'fire'), ('flame', 'fire'), ('burn', 'fire'), ('meteor', 'fire'), ('pyro', 'fire'), ('inferno', 'fire'),
    ('ice', 'frost'), ('frost', 'frost'), ('cold', 'frost'), ('freeze', 'frost'), ('chill', 'frost'), ('winter', 'frost'), ('blizzard', 'frost'),
    ('lightning', 'lightning'), ('shock', 'lightning'), ('thunder', 'lightning'), ('storm', 'lightning'), ('spark', 'lightning'),
    ('heal', 'holy'), ('cure', 'holy'), ('holy', 'holy'), ('smite', 'holy'), ('bless', 'holy'), ('divine', 'holy'),
    ('sanctuary', 'holy'), ('light', 'holy'), ('judg', 'holy'), ('radiant', 'holy'), ('prayer', 'holy'),
    ('soul', 'necrotic'), ('death', 'necrotic'), ('drain', 'necrotic'), ('corpse', 'necrotic'), ('undead', 'necrotic'), ('bone', 'necrotic'),
    ('shadow', 'shadow'), ('dark', 'shadow'), ('void', 'shadow'), ('curse', 'shadow'), ('fear', 'shadow'), ('blind', 'shadow'),
    ('poison', 'poison'), ('acid', 'poison'), ('venom', 'poison'), ('plague', 'poison'),
    ('earth', 'nature'), ('quake', 'nature'), ('thorn', 'nature'), ('root', 'nature'), ('entangle', 'nature'), ('nature', 'nature'),
    ('song', 'sound'), ('sonic', 'sound'), ('mock', 'sound'), ('discord', 'sound'), ('crescendo', 'sound'), ('fascinate', 'sound'),
    ('missile', 'arcane'), ('arcane', 'arcane'), ('mana', 'arcane'), ('magic', 'arcane'),
)
_CLASS_SCHOOL = {'cleric': 'holy', 'paladin': 'holy', 'necromancer': 'necrotic', 'bard': 'sound', 'ranger': 'nature',
                 'mage': 'arcane', 'warrior': 'physical', 'thief': 'shadow', 'assassin': 'shadow'}


def spell_school(name, spell=None, caster=None):
    el = (spell or {}).get('element') if isinstance(spell, dict) else None
    if el:
        return {'cold': 'frost', 'ice': 'frost'}.get(el, el)
    n = key(name)
    for word, school in _SCHOOL_WORDS:
        if word in n:
            return school
    req = (spell or {}).get('class_required') if isinstance(spell, dict) else None
    if isinstance(req, (list, tuple)) and req:
        req = req[0]
    cls = str(req or getattr(caster, 'char_class', '') or '').lower()
    return _CLASS_SCHOOL.get(cls, 'arcane')


# ---- what kind of harm a creature's ability, a lingering effect or a hazard does ----
# (worn gear's resistances answer to it, Player.resistance). Each word is matched against the
# start of a word of the name (a word of three letters or fewer only against a whole word: 'ice'
# is not 'device'), first match in this order: the blows first ('Blade Storm', 'Mirror Blade'),
# then the element before how it comes ('Frost Breath' is frost; a breath naming none is fire).
_HARM_WORDS = (
    ('blade', 'physical'), ('shockwave', 'physical'), ('shatter', 'physical'),
    ('censure', 'holy'), ('gilded', 'holy'), ('holy', 'holy'), ('smite', 'holy'), ('divine', 'holy'), ('radiant', 'holy'),
    ('necrotic', 'necrotic'), ('soul', 'necrotic'), ('death', 'necrotic'), ('drain', 'necrotic'), ('wail', 'necrotic'),
    ('wasting', 'necrotic'), ('hunger', 'necrotic'), ('wither', 'necrotic'), ('decay', 'necrotic'), ('mistrot', 'necrotic'),
    ('plague', 'disease'), ('pestilen', 'disease'), ('disease', 'disease'), ('miasma', 'disease'), ('blight', 'disease'), ('rot', 'disease'),
    ('poison', 'poison'), ('venom', 'poison'), ('toxic', 'poison'), ('acid', 'poison'), ('serpent', 'poison'),
    ('shadow', 'shadow'), ('black', 'shadow'), ('eclipse', 'shadow'), ('fallen', 'shadow'), ('severing', 'shadow'),
    ('ashen', 'shadow'), ('void', 'shadow'), ('dark', 'shadow'), ('curse', 'shadow'),
    ('psychic', 'arcane'), ('mind', 'arcane'), ('disintegrat', 'arcane'), ('arcane', 'arcane'), ('mirror', 'arcane'),
    ('prismatic', 'arcane'), ('elemental', 'arcane'), ('color', 'arcane'), ('starfall', 'arcane'), ('event', 'arcane'),
    ('accounting', 'arcane'), ('debt', 'arcane'), ('missile', 'arcane'), ('magic', 'arcane'),
    ('frost', 'frost'), ('permafrost', 'frost'), ('ice', 'frost'), ('icy', 'frost'), ('cold', 'frost'), ('chill', 'frost'),
    ('freez', 'frost'), ('blizzard', 'frost'), ('avalanche', 'frost'),
    ('lightning', 'lightning'), ('thunder', 'lightning'), ('storm', 'lightning'), ('shock', 'lightning'), ('spark', 'lightning'),
    ('fire', 'fire'), ('flame', 'fire'), ('inferno', 'fire'), ('searing', 'fire'), ('burn', 'fire'), ('meteor', 'fire'),
    ('bomb', 'fire'), ('slag', 'fire'), ('smoulder', 'fire'), ('magma', 'fire'), ('lava', 'fire'),
    ('vine', 'nature'), ('entangle', 'nature'), ('thorn', 'nature'), ('bramble', 'nature'), ('root', 'nature'),
    ('bell', 'sound'), ('peal', 'sound'), ('discord', 'sound'), ('silence', 'sound'), ('cry', 'sound'), ('roar', 'sound'),
    ('sonic', 'sound'), ('requiem', 'sound'), ('shriek', 'sound'), ('scream', 'sound'), ('howl', 'sound'),
    ('breath', 'fire'),
)
_HARM_ALIASES = {'cold': 'frost', 'ice': 'frost', 'acid': 'poison', 'electric': 'lightning', 'psychic': 'arcane'}


def harm_school(name, element=None):
    """The school of harm a named ability, breath, lingering effect or hazard deals ('physical'
    for a blow); an ability's own `element` says it outright."""
    if element:
        el = str(element).lower()
        return _HARM_ALIASES.get(el, el)
    words = re.findall(r'[a-z]+', str(name or '').lower())
    for word, school in _HARM_WORDS:
        if any(w == word or (len(word) > 3 and w.startswith(word)) for w in words):
            return school
    return 'physical'


async def spell_out_of_range(caster, target, spell_name, spell):
    """True (and the caster is told why) when `target` is beyond the spell's reach. Called
    before any mana is spent."""
    if target is None or target is caster:
        return False
    rng, shape = ability_range(spell_name, True)
    if shape == 'self' or shape.startswith('nova'):
        return False
    d = distance(caster, target)
    if d is None or d <= rng + 0.4:
        return False
    try:
        c = caster.config.COLORS
        label = (spell or {}).get('name') or str(spell_name).replace('_', ' ')
        await caster.send(f"{c['yellow']}{target.name} is too far for {label} ({d:.0f} m; it reaches {rng:g} m).{c['reset']}")
        import combat_events as ev
        ev.emit(caster.room, 'oor', src=caster, dst=target, ability=key(spell_name), need=rng, dist=round(d, 1))
    except Exception:
        pass
    return True


# ---- creatures in a fight move: melee closes in, archers and casters keep their distance ----
def move_tick(world, dt):
    import combat_events as ev
    moved_rooms = {}
    for npc in list(getattr(world, 'npcs', []) or []):
        tgt = getattr(npc, 'fighting', None)
        if tgt is None or getattr(npc, 'room', None) is None or getattr(tgt, 'room', None) is not npc.room:
            continue
        now = time.time()
        if now < getattr(npc, 'staggered_until', 0) or getattr(npc, 'stunned_rounds', 0) > 0:
            continue
        if now < getattr(npc, 'rooted_until', 0):
            continue      # rooted (marquee_abilities): held where it stands
        if getattr(npc, 'pending_intent', None):
            continue      # winding up: it plants its feet, so the marked ground stays where it is
        slow = 0.5 if now < getattr(npc, 'slowed_until', 0) else 1.0
        mp, tp = pos_of(npc), pos_of(tgt)
        if mp is None or tp is None:
            continue
        reach, prefer = mob_reach(npc)
        dx, dz = tp[0] - mp[0], tp[1] - mp[1]
        d = math.hypot(dx, dz)
        if d < 1e-3:
            continue
        step = 0.0
        if reach <= MELEE + 0.5:
            if d > reach * 0.85:
                step = min(MOB_SPEED * slow * dt, d - reach * 0.75)
        else:
            if d < prefer * 0.55:
                step = -min(MOB_SPEED * 0.8 * slow * dt, prefer * 0.6 - d)      # back off to shoot
            elif d > reach * 0.95:
                step = min(MOB_SPEED * slow * dt, d - reach * 0.85)
        if abs(step) < 0.02:
            continue
        nx, nz = mp[0] + dx / d * step, mp[1] + dz / d * step
        # keep a little room between creatures crowding the same hero
        for other in npc.room.characters:
            if other is npc or hasattr(other, 'account_name'):
                continue
            op = pos_of(other)
            if op is None:
                continue
            ox, oz = nx - op[0], nz - op[1]
            od = math.hypot(ox, oz)
            if 0 < od < 1.1:
                nx += ox / od * (1.1 - od) * 0.5
                nz += oz / od * (1.1 - od) * 0.5
        set_pos(npc, nx, nz)
        p = pos_of(npc)
        moved_rooms.setdefault(npc.room.vnum, (npc.room, []))[1].append((npc, p))
    for vnum, (room, items) in moved_rooms.items():
        for npc, p in items:
            ev.emit(room, 'move', src=npc, x=round(p[0], 2), z=round(p[1], 2))
