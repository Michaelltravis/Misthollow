#!/usr/bin/env python3
"""Marquee balance: each class's marquee quest fought with the game's own combat code, alone and in
groups, on a simulated clock (no server, no sockets, no waiting: a quest takes about a second).

    python3 tools/balance/sim.py                         # every class, levels 45 and 50, parties of 1, 2, 3 and 6
    python3 tools/balance/sim.py --classes warrior,mage --levels 45 --party 1 --runs 2
    python3 tools/balance/sim.py --mode action           # the 3D client's real-time combat (skills a second apart)
    python3 tools/balance/sim.py --calibrate --levels 45,50,55,60 --runs 8     # measure CLASS_K and CLASS_D
    python3 tools/balance/sim.py --report docs/balance/table.md

What it does, per class, level and party size:
- builds heroes the way the game does (created at level 1, levelled up with the class's own dice,
  every ability their level has unlocked at PROF% from use) and dresses them from the world's
  own weapons and armour (the item at the --gear percentile of what each slot offers at their
  level, not the very best); a party is the quest's class and PARTY's others;
- spawns each stage's creatures exactly as the quest engine does (marquee._place, _kill_tick,
  _collect_tick, _ritual_tick, _trial_tick: health and damage from marquee_scale for the classes
  that embarked, a party's extra adds, a boss's tempo and the helpers it calls);
- fights each fight round by round with the real code. The heroes: their defensive buffs before
  it, then a heal when someone is low, else the strongest attack that isn't cooling down, and
  their swings (CombatHandler.one_round); the weakest foe first; a necromancer keeps a raised
  servant. The creatures: each turns on any of the party (marquee._engage), their wind-ups,
  specials and swings (mob_ai, bosses.py); a marked blow, a boss's telegraph or a pool on the
  floor is stepped out of, and a hunger kept moving through, with --dodge probability. The world's clocks run on through it (poison, affects, regeneration);
- a fight lost is fought again from the temple, against what is left of the foe (which has healed
  as creatures do out of a fight); a ritual starts over;
- counts the time: fights, resting back to health and mana between them (the game's regeneration,
  resting), and the way between the quest's places (the shortest walk through the world's rooms at
  --walk seconds a room, plus --travel minutes a leg for finding the way and reading);
- reports minutes, deaths, fights lost (and to what), each hero's damage per round against
  marquee_scale.dpr(level), and the most of their health each kind of fight took at its worst.

Its findings, and what they changed: docs/balance/marquee.md.
"""
import argparse
import asyncio
import logging
import os
import random
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, '..', '..', 'src'))
sys.path.insert(0, SRC)


# ---------------------------------------------------------------- a clock we turn ourselves
class Clock:
    def __init__(self):
        self.t = 1.9e9

    def time(self):
        return self.t

    def advance(self, secs):
        self.t += secs


CLOCK = Clock()
time.time = CLOCK.time            # every module's time.time() reads the simulated clock

ROUND = 3.0
NPC_DELAY = 1.3
VERBOSE = False
RETRIES = 3                       # a fight lost is fought again (from the temple) this many times
PROF = 80                         # how well a level 45-50 hero knows their abilities (used, not trained)
# of max health and mana a minute, resting (Player.regen_tick every 60 s and minor_regen_tick, a
# tenth of it, every 5 s; resting x1.5): Config.HP_REGEN_RATE 12% -> about 40% a minute
_RESTING = 1.5 * (1 + 0.10 * 60 / 5)
REST_HP = 0.12 * _RESTING
REST_MANA = 0.15 * _RESTING
PARTY = ['cleric', 'warrior', 'mage', 'ranger', 'bard', 'paladin']   # who joins a quest owner
CLASSES = ['warrior', 'mage', 'cleric', 'paladin', 'necromancer', 'thief', 'ranger', 'bard', 'assassin']


class Conn:
    """A hero's connection: what they were told (the rotation reads refusals from it)."""
    def __init__(self):
        self.lines = []

    async def send(self, message='', newline=True):
        self.lines.append(str(message))
        if len(self.lines) > 400:
            del self.lines[:200]

    async def send_prompt(self):
        pass


# ---------------------------------------------------------------- the world and its heroes
async def load_world():
    global REST_HP, REST_MANA
    logging.disable(logging.CRITICAL)
    from config import Config
    REST_HP, REST_MANA = Config.HP_REGEN_RATE * _RESTING, Config.MANA_REGEN_RATE * _RESTING
    from world import World
    world = World(Config())
    await world.load()
    world.web_map = None
    no_saves()
    import combat_hooks
    import mastery
    import brain
    combat_hooks.install()
    brain.install()               # (the threat hooks, as main.py has them)
    mastery.install()
    return world


def no_saves():
    """The simulation's heroes are never written to disk: an achievement (level 50, a boss)
    saves the player, and thousands of simulated heroes filled lib/players and the leaderboards."""
    from player import Player

    async def no_save(self, *a, **k):
        return None
    Player.save = no_save


def _score(proto):
    """How good an item is, roughly: a weapon by its average blow, armour by what it stops, both
    by what they add."""
    import re
    s = 0.0
    dice = proto.get('damage_dice')
    if proto.get('item_type') == 'weapon' and dice:
        m = re.match(r'(\d+)d(\d+)(?:\+(\d+))?', str(dice))
        if m:
            s += int(m.group(1)) * (int(m.group(2)) + 1) / 2 + int(m.group(3) or 0)
    s += float(proto.get('armor', 0) or 0) + float(proto.get('armor_bonus', 0) or 0) * 0.5
    # what it adds, as the game reads it (an endgame item's `effects` too); an `armor` affect
    # lowers armour class, so the lower the better
    from objects import effects_as_affects
    for a in list(proto.get('affects') or []) + effects_as_affects(proto.get('effects'))[0]:
        if not isinstance(a, dict):
            continue
        v = float(a.get('value', 0) or 0)
        t = a.get('type') or a.get('location')
        s += {'damroll': 2.0, 'hitroll': 1.0, 'hp': 0.08, 'str': 1.0, 'dex': 1.0, 'con': 1.0,
              'int': 0.6, 'wis': 0.6, 'armor': -0.5, 'mana': 0.03,
              'hp_regen': 0.1, 'mana_regen': 0.1, 'move_regen': 0.05}.get(t, 0.2) * v
    return s


_GEAR = {}


def gear_table(world):
    """Per slot, the world's weapons and armour with their level and score."""
    if _GEAR:
        return _GEAR
    from objects import Object
    for vnum, proto in world.obj_prototypes.items():
        if not isinstance(proto, dict) or proto.get('item_type') not in ('weapon', 'armor'):
            continue
        try:
            obj = Object.from_prototype(proto, world)
        except Exception:
            continue
        slot = 'wield' if proto.get('item_type') == 'weapon' else (obj.wear_slot or '')
        slot = {'neck': 'neck1', 'finger': 'finger1', 'wrist': 'wrist1'}.get(slot, slot)
        if not slot:
            continue
        lvl = int(proto.get('min_level') or proto.get('level') or 0)
        kind = ''
        if slot == 'wield':
            try:
                import gear_look
                kind = gear_look.weapon_piece(obj).get('k') or ''
            except Exception:
                pass
        _GEAR.setdefault(slot.rstrip('12'), []).append((lvl, _score(proto), vnum, kind))
    return _GEAR


# what a class wants in hand when the world offers it (the reach of its ordinary blow follows
# the weapon: combat_range.py), else the best of anything
WANTS = {'ranger': ('bow', 'crossbow')}


def dress(world, hero, level, pct):
    """Wear, in each slot, the item at the pct percentile of what that slot offers at this level."""
    from objects import create_object
    hero.equipment = {}
    want = WANTS.get(str(getattr(hero, 'char_class', '') or '').lower())
    for base, items in gear_table(world).items():
        fit = sorted((s, v) for lv, s, v, kind in items if lv <= level)
        if base == 'wield' and want:
            fit = sorted((s, v) for lv, s, v, kind in items if lv <= level and kind in want) or fit
        if not fit:
            continue
        n = 2 if base in ('neck', 'finger', 'wrist') else 1
        for k in range(n):
            i = min(len(fit) - 1, max(0, int(pct * (len(fit) - 1)) - k))
            obj = create_object(fit[i][1], world)
            if obj is None:
                continue
            slot = f'{base}{k + 1}' if n == 2 else base
            hero.equipment[slot] = obj


async def make_hero(world, cls, level, name, gear):
    from player import Player
    import mastery
    stats = {s: 13 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}
    prime = world.config.CLASSES.get(cls, {}).get('prime_stat', 'str')
    stats[prime] = 18
    for s in ('con', 'dex'):
        stats[s] = max(stats[s], 15)
    p = Player.create_new(name=name, password=None, race='human', char_class=cls, stats=stats, world=world)
    p.connection = Conn()
    for _ in range(level - 1):
        await p.level_up()
    mastery.grant_now(p)
    for store in (p.skills, p.spells):
        for a in list(store):
            store[a] = max(store[a], PROF)
    dress(world, p, level, gear)
    p.hp, p.mana, p.move = p.max_hp, p.max_mana, p.max_move
    world.players[name.lower()] = p
    return p


# ---------------------------------------------------------------- death, as the sim counts it
DEATHS = []
DEALT = {}          # hero name -> damage dealt to foes (every blow, skill and spell)


def patch_damage():
    from mobs import Mobile
    from player import Player
    orig_p = Player.take_damage

    async def hero_takes(self, amount, *args, **kwargs):
        result = await orig_p(self, amount, *args, **kwargs)
        self._low = min(getattr(self, '_low', self.hp), self.hp)      # the closest a fight came to killing them
        return result
    Player.take_damage = hero_takes
    orig = Mobile.take_damage

    async def take_damage(self, amount, *args, **kwargs):
        attacker = kwargs.get('attacker', args[0] if args else None)
        hp0 = self.hp
        result = await orig(self, amount, *args, **kwargs)
        if attacker is not None and hasattr(attacker, 'connection'):
            DEALT[attacker.name] = DEALT.get(attacker.name, 0) + max(0, hp0 - max(0, self.hp))
        return result
    Mobile.take_damage = take_damage


def patch_deaths(world):
    from player import Player
    from combat import CombatHandler

    async def player_die(self, killer=None):
        if getattr(self, 'position', None) == 'dead':
            return                       # already down (an area blow finds the body): once is a death
        DEATHS.append(self.name)
        self.hp = 0
        if self.fighting is not None and getattr(self.fighting, 'fighting', None) is self:
            self.fighting.fighting = None
        self.fighting = None
        self.position = 'dead'
        # out of the fight until the rest after it (nothing strikes a body)
        room = getattr(self, 'room', None)
        if room is not None and self in room.characters:
            room.characters.remove(self)
        for ch in list(room.characters if room else []):
            if getattr(ch, 'fighting', None) is self:
                ch.fighting = None

    Player.die = player_die
    orig = CombatHandler.handle_death.__func__

    async def handle_death(cls, killer, victim):
        if hasattr(victim, 'connection'):
            return
        victim.hp = 0
        room = getattr(victim, 'room', None)
        if room is not None and victim in room.characters:
            room.characters.remove(victim)
        if victim in world.npcs:
            world.npcs.remove(victim)
        for ch in list(room.characters if room else []):
            if getattr(ch, 'fighting', None) is victim:
                ch.fighting = None
    CombatHandler.handle_death = classmethod(handle_death)
    return orig


# ---------------------------------------------------------------- the rotation
_BOOK = {}


# spells that hold or turn a foe rather than hurt it: a player fighting a quest creature down
# doesn't lead with them (and the quest creatures are immune to the worst)
CONTROL = {'charm_person', 'charm_monster', 'sleep', 'fear', 'slow', 'fascinate', 'hold_person', 'blindness', 'turn_undead',
           'curse', 'weaken', 'silence', 'web', 'entangle', 'calm', 'faerie_fire', 'dispel_magic', 'disarm'}


def rotation(cls, level):
    """(enemy abilities strongest first, healing abilities) a hero of this level can use: no
    marquee abilities (they are the quest's reward), no pure control spells."""
    import mastery
    from spells import SPELLS
    key = (cls, level)
    if key not in _BOOK:
        quest = set(getattr(mastery, 'QUEST_ABILITIES', ()) or ())
        book = [e for e in mastery.book(cls) if not e.get('passive') and (e.get('level') or 99) <= level
                and e['id'] not in quest and e['id'] not in CONTROL]
        def hurts(e):
            if e.get('type') != 'spell':
                return True
            sp = SPELLS.get(e['id']) or {}
            return bool(sp.get('damage_dice') or sp.get('damage') or sp.get('damage_per_level'))
        enemy = [e for e in book if (e.get('target') or 'enemy') == 'enemy' and hurts(e)]
        enemy.sort(key=lambda e: -(e.get('level') or 0))
        import re
        mends = re.compile(r'heal|cure|mend|lay_on_hands|renew|restor|regenerat|rejuven')
        heals = [e for e in book if e.get('target') in ('ally', 'self', 'group') and mends.search(e['id'])]
        _BOOK[key] = (enemy, heals)
    return _BOOK[key]


# what a hero casts on themselves before a fight, if they have it (lasts the fight)
DEFENSIVE = ['summon_gargoyle', 'divine_shield', 'divine_protection', 'bone_shield', 'corpse_shield', 'mana_shield',
             'fire_shield', 'mirrorward', 'stoneskin', 'armor', 'sanctuary', 'shield', 'barkskin', 'ice_armor', 'blur',
             'bless', 'protection_from_evil', 'righteous_fury', 'evasion', 'rallying_cry',
             'tower_echoes', 'phase_step', 'stepwise', 'mirror_image', 'displacement', 'blink']


SERVANTS = 1       # a necromancer's raised dead (an hour each, from the last fight's corpses; up to level/10 + 1)


async def prepare(hero):
    """Before a fight: the hero's defensive buffs (a player puts them up before engaging), and a
    necromancer's servants (raised from the last fight's dead; they last an hour)."""
    import mastery
    from commands import CommandHandler
    if hero.char_class == 'necromancer' and hero.spells.get('animate_dead', 0) > 0:
        from pets import PetManager
        # the raised dead only: a gargoyle (Summon Gargoyle, a summon) stands beside them, not for one
        have = [p for p in PetManager.get_player_pets(hero) if p.is_alive and p.room is hero.room and p.pet_type == 'undead']
        for _ in range(SERVANTS - len(have)):
            await PetManager.summon_pet(hero, 'undead_warrior', duration_minutes=60)
    have = {e['id']: e for e in mastery.book(hero.char_class) if (e.get('level') or 99) <= hero.level}
    for a in DEFENSIVE:
        e = have.get(a)
        if e is None or (hero.skills.get(a, 0) <= 0 and hero.spells.get(a, 0) <= 0):
            continue
        cmd, args = _cmd(e)
        await CommandHandler.execute(hero, cmd, args)


def _cmd(entry):
    return ('cast', [f"'{entry['id'].replace('_', ' ')}'"]) if entry.get('type') == 'spell' else (entry['id'], [])


REFUSED = ("you don't know", 'huh?', 'not ready', 'cooldown', 'must wait', 'not enough', 'too exhausted',
           'you need', "can't", 'cannot', 'who?', 'not here', 'nobody', 'must be fighting', "aren't fighting")


async def act(hero, party, foes, stats):
    """One ability: a heal when someone in the party is low, else the strongest ready attack."""
    from commands import CommandHandler
    enemy, heals = rotation(hero.char_class, hero.level)
    low = min((h for h in party if h.hp > 0), key=lambda h: h.hp / max(1, h.max_hp), default=None)
    tries = []
    if heals and low is not None and low.hp < 0.5 * low.max_hp:
        tries += [(e, '' if (low is hero or e.get('target') == 'self') else low.name.lower()) for e in heals]
    target = hero.fighting
    if target is not None and target.hp > 0:
        kw = str(target.name).split()[-1].lower()
        tries += [(e, kw) for e in enemy]
    for e, who in tries[:8]:
        cmd, args = _cmd(e)
        before = len(hero.connection.lines)
        await CommandHandler.execute(hero, cmd, args + ([who] if who else []))
        said = ' '.join(hero.connection.lines[before:]).lower()
        if not any(w in said for w in REFUSED):
            stats['abilities'] = stats.get('abilities', 0) + 1
            return True
    return False


# ---------------------------------------------------------------- a fight
def heed_the_floor(h, tp, foes, dodge):
    """A boss's mechanics on the floor (boss_mechanics.py), heeded or not as a marked blow is: a
    pool is stepped out of (the hero fights on from beside its target, outside it), and against a
    hunger the hero keeps moving, each with the --dodge chance (decided once per pool, per round
    for the hunger)."""
    import math
    import combat_range as cr
    mechs = [m for f in foes if f.hp > 0 for m in getattr(f, 'mechanics', ())]
    avoid = []
    for m in mechs:
        for pl in getattr(m, 'pools', ()):
            if pl.get('x') is None:
                continue
            heed = pl.setdefault('heeded', {})
            if h.name not in heed:
                heed[h.name] = random.random() < dodge
            if heed[h.name]:
                avoid.append(pl)
    restless = any(type(m).__name__ == 'Hunger' for m in mechs) and random.random() < dodge
    p = cr.pos_of(h)
    inside = lambda x, z: any(math.hypot(x - pl['x'], z - pl['z']) <= pl['r'] for pl in avoid)
    if p is None or not (restless or inside(*p)):
        return
    start = random.randrange(12)
    for d in (1.2, 1.8, 2.2, 3.0, 4.0, 6.0, 9.0, 12.0):
        for k in range(12):
            a = (start + k) * math.pi / 6
            x, z = tp[0] + d * math.cos(a), tp[1] + d * math.sin(a)
            if not inside(x, z) and math.hypot(x - p[0], z - p[1]) >= 0.8:
                cr.set_pos(h, x, z)
                return


async def fight(world, room, party, foes, mode, dodge, stats, max_secs=1800):
    """Fight until one side is down; returns the seconds it took."""
    from combat import CombatHandler
    import combat_range as cr
    import mob_ai
    from bosses import Boss
    for i, h in enumerate(party):
        _put(h, room)
        cr.set_pos(h, 10 + i * 0.7, 7)
    for h in party:
        if h.hp > 0:
            await prepare(h)
    # a quest creature turns on a member of the party in its room, any of them (marquee._engage)
    anyone = lambda: random.choice([h for h in party if h.hp > 0] or [None])
    waiting = [f for f in foes if getattr(f, '_arrive_at', 0) > 0]
    foes = [f for f in foes if f not in waiting]

    def arrive(f, j):
        f._hp_start = f.hp
        _put(f, room)
        world.npcs.append(f)
        cr.set_pos(f, 11.5 + (j % 3) * 0.8, 7 + (j // 3) * 0.8)
        f.fighting = anyone()
        f.position = 'fighting'
    for j, f in enumerate(foes):
        arrive(f, j)
    t0 = CLOCK.t
    # the world's own clocks run on through the fight (main.py): poison every 3 s, affects (damage
    # and healing over time, durations) every 6 s, a hero's small regen every 5 s and the full
    # one every 60 s — at a fighter's half rate. Each starts somewhere in its cycle.
    ticks = {k: t0 + random.uniform(0, every) for k, every in TICKS.items()}
    done = lambda: (not [f for f in foes if f.hp > 0] and not waiting) or not [h for h in party if h.hp > 0]
    while not done() and CLOCK.t - t0 < max_secs:
        await world_ticks(ticks, party, foes)
        for f in [f for f in waiting if CLOCK.t - t0 >= f._arrive_at]:
            waiting.remove(f)
            foes.append(f)
            arrive(f, len(foes))
        # a foe that fled is chased down (a player follows it): back in the fight
        for f in foes:
            if f.hp > 0 and getattr(f, 'room', None) is not room:
                _put(f, room)
                cr.set_pos(f, 11.5, 7)
                f.fighting = anyone()
                f.position = 'fighting'
        # adds a boss called in join the fight
        for ch in list(room.characters):
            if not hasattr(ch, 'connection') and ch.hp > 0 and ch not in foes and getattr(ch, 'fighting', None) in party:
                ch._hp_start = ch.hp
                foes.append(ch)
        # what a player picks: the weakest first (a boss's adds before the boss, one of a wave
        # at a time), and they stay on it until it falls
        alive = sorted((f for f in foes if f.hp > 0), key=lambda f: f.hp)
        for h in party:
            if h.hp <= 0:
                continue
            if h.fighting is None or h.fighting.hp <= 0 or (alive and h.fighting.hp > 3 * alive[0].max_hp and alive[0] is not h.fighting):
                h.fighting = alive[0] if alive else None
                h.position = 'fighting'
            if h.fighting is None:
                continue
            # close in on the target (a player walks up to what they fight; casters too, the
            # creatures would come to them anyway)
            tp = cr.pos_of(h.fighting)
            if tp is not None:
                cr.set_pos(h, tp[0] - 1.2, tp[1])
                heed_the_floor(h, tp, foes, dodge)
            uses = 1 if mode == 'rounds' else 3      # a skill a round typed, a second apart in real time
            for _ in range(uses):
                if not await act(h, party, foes, stats):
                    break
            if h.fighting is not None and h.fighting.hp > 0:
                await CombatHandler.one_round(h, h.fighting)
        # a wind-up is stepped out of, or not: a creature's marked blow, and a boss's telegraphed
        # ability (on everyone it would catch)
        for f in foes:
            it = getattr(f, 'pending_intent', None)
            if f.hp > 0 and it and CLOCK.t + NPC_DELAY - it.get('declared_at', CLOCK.t) >= mob_ai.INTENT_WINDUP:
                tgt = f.fighting
                if tgt is not None and random.random() < dodge:
                    cr.set_pos(tgt, 2, 2)
            cast = (getattr(f, 'ai_state', None) or {}).get('cast') if isinstance(f, Boss) else None
            if f.hp > 0 and cast and cast.get('resolve_at', 0) <= CLOCK.t + NPC_DELAY:
                caught = [h for h in party if h.hp > 0] if cast['ability'].get('aoe') else [cast.get('target')]
                for tgt in caught:
                    if tgt is not None and random.random() < dodge:
                        cr.set_pos(tgt, 2, 2)
        CLOCK.advance(NPC_DELAY)
        for f in foes:
            if f.hp <= 0 or f.fighting is None or f.fighting.hp <= 0:
                if f.hp > 0:
                    f.fighting = anyone()
                if f.hp <= 0 or f.fighting is None:
                    continue
            try:
                if isinstance(f, Boss):
                    await f.process_ai()
                await mob_ai.mob_ai_tick(f)
                if f.fighting is not None and f.hp > 0:
                    await CombatHandler.one_round(f, f.fighting)
            except Exception as e:
                _error(e)
        CLOCK.advance(ROUND - NPC_DELAY)
        for f in foes:
            if f.hp > 0 and f.fighting is not None:
                try:
                    await mob_ai.declare_intents(f)
                except Exception as e:
                    _error(e)
        stats['rounds'] = stats.get('rounds', 0) + 1
    # everything the foes lost (blows, spells, and the damage over time no blow is credited with)
    stats['foe_loss'] = stats.get('foe_loss', 0) + sum(max(0, getattr(f, '_hp_start', f.hp) - max(0, f.hp)) for f in foes)
    for f in foes:
        if f in room.characters:
            room.characters.remove(f)
        if f in world.npcs:
            world.npcs.remove(f)
    for h in party:
        h.fighting = None
        if h.position != 'dead':
            h.position = 'standing'
    return CLOCK.t - t0


_ERRORS = set()


def _error(e):
    """A creature's turn that raised: the game's own bug (the server would log it). Said once."""
    import traceback
    where = traceback.extract_tb(e.__traceback__)[-1]
    key = (type(e).__name__, str(e), where.filename, where.lineno)
    if key not in _ERRORS:
        _ERRORS.add(key)
        print(f"  ! {type(e).__name__}: {e} ({os.path.basename(where.filename)}:{where.lineno})", file=sys.stderr)


TICKS = {'poison': 3.0, 'affects': 6.0, 'minor': 5.0, 'regen': 60.0}


async def world_ticks(ticks, party, foes):
    """Whatever of the world's periodic ticks fell due since the last call, for the fight's own
    heroes and creatures (World.poison_tick, affect_tick, minor_regen_tick, regen_tick)."""
    from affects import AffectManager
    for k, every in TICKS.items():
        while ticks[k] <= CLOCK.t:
            ticks[k] += every
            heroes = [h for h in party if h.hp > 0]
            live = [f for f in foes if f.hp > 0 and getattr(f, 'room', None) is not None]
            for ch in heroes + live:
                try:
                    if k == 'poison':
                        await AffectManager.tick_affects(ch, poison_only=True)
                    elif k == 'affects':
                        await AffectManager.tick_affects(ch)
                    elif k == 'minor' and ch in heroes:
                        await ch.minor_regen_tick()
                    elif k == 'regen':
                        await ch.regen_tick()
                except Exception as e:
                    _error(e)


def _put(ch, room):
    old = getattr(ch, 'room', None)
    if old is not None and ch in old.characters:
        old.characters.remove(ch)
    ch.room = room
    room.characters.append(ch)


def rest(party):
    """Minutes resting back to full health and mana (the game's regen), the dead revived."""
    need = 0.0
    for h in party:
        if h.hp <= 0:
            h.hp = 1
            h.position = 'standing'
        need = max(need, (1 - h.hp / max(1, h.max_hp)) / REST_HP,
                   (1 - h.mana / max(1, h.max_mana)) / REST_MANA if h.max_mana else 0)
        h.hp, h.mana, h.move = h.max_hp, h.max_mana, h.max_move
        for attr in ('stunned_rounds', 'blinded_rounds'):
            setattr(h, attr, 0)
    # their servants mend as creatures do out of a fight (Mobile.regen_tick: 5% a minute)
    from pets import PetManager
    for h in party:
        for pet in PetManager.get_player_pets(h):
            if pet.hp > 0:
                pet.hp = min(pet.max_hp, pet.hp + int(need * max(1, pet.max_hp // 20)))
    return need


# ---------------------------------------------------------------- a quest
def spawn(world, vnum, kind, level, n, cls):
    """A quest creature, made as marquee._place makes it (cls: the quest's class, or the classes
    of everyone who embarked)."""
    import copy
    import marquee_scale as ms
    from marquee import _HOSTILE
    from bosses import create_mob_from_prototype
    proto = world.mob_prototypes.get(vnum)
    if not proto:
        return None
    p = dict(proto)
    p['flags'] = [f for f in proto.get('flags', []) if f not in _HOSTILE]
    p['max_hp'] = ms.foe_health(kind, level, n, cls)
    p['level'] = ms.foe_level(int(proto.get('level', 45)), level)
    if proto.get('boss_config'):
        cfg = copy.deepcopy(proto['boss_config'])
        cfg['ability_interval'] = round(cfg.get('ability_interval', 4.0) * ms.tempo(n), 2)
        extra = ms.extra_adds(n)
        if extra:
            for ph in cfg.get('phases', []):
                if ph.get('spawn_adds'):
                    ph['spawn_adds'] = {k: v + extra for k, v in ph['spawn_adds'].items()}
            for ab in cfg.get('abilities', []):
                if ab.get('summon'):
                    ab['summon'] = {k: v + extra for k, v in ab['summon'].items()}
        p['boss_config'] = cfg
    mob = create_mob_from_prototype(p, world)
    mob.hp = mob.max_hp
    mob._dmg_scale = ms.foe_damage_scale(kind, n, cls, level)
    mob.marquee_tag = {'kind': kind}
    if getattr(mob, 'boss_config', None) is not None:
        # the helpers a boss calls in are made lighter than itself (marquee._adopt)
        def adopt(adds, level=level, n=n, cls=cls):
            for a in adds:
                a.max_hp = a.hp = ms.foe_health('add', level, n, cls)
                a._dmg_scale = ms.foe_damage_scale('add', n, cls, level)
                a.marquee_tag = {'kind': 'add', 'add': True}
        mob.on_adds = adopt
    return mob


def fights_of(world, cls, n=1):
    """A class's quest for n who embarked, stage by stage, with the creatures the quest engine puts
    out (marquee._kill_tick, _ritual_tick, _trial_tick: a party gets extra_adds more): {label,
    groups [[(vnum, kind, count[, at])]], rooms (the places the stage takes the party, in order),
    where (the room each group is fought in), inside (rooms walked within a trial)}."""
    import json
    import marquee_quests as mq
    import marquee_scale as ms
    extra = ms.extra_adds(n)
    q = mq.QUESTS[cls]
    load = lambda v: v if isinstance(v, list) else json.loads(v)
    out = []
    for st in q['stages']:
        kind = st['kind']
        stage = {'label': f"{kind}: {st.get('objective', '')[:40]}", 'groups': [], 'rooms': [], 'where': [], 'inside': 0}
        if kind == 'talk':
            stage['rooms'] = [st['room']]
        elif kind == 'visit':
            stage['rooms'] = [v['room'] for v in load(st['visits'])]
        elif kind == 'return':
            stage['rooms'] = [q['giver_room']]
        elif kind == 'kill':
            spawns = load(st['spawns'])
            stage['label'] = f"kill: {(st.get('objective') or spawns[0].get('label', ''))[:40]}"
            for sp in spawns:
                g = [(sp['vnum'], sp.get('kind', 'elite'), 1)]
                if st.get('adds') and extra:
                    g.append((st['adds'], 'minion', extra))
                stage['groups'].append(g)
                stage['where'].append(sp['room'])
            stage['rooms'] = [sp['room'] for sp in spawns]
        elif kind == 'collect':
            # kill until enough have dropped what is wanted; a room keeps per_room of them up at
            # once (one more 3 s after each falls), so they come in that many at a time, and the
            # party moves on to the next room when one has given what it will
            kills = got = 0
            while got < st['need']:
                kills += 1
                if random.randint(1, 100) <= st.get('chance', 50):
                    got += 1
            per = max(1, st.get('per_room', 2))
            rooms = list(st.get('rooms', [])) or [None]
            for i in range(0, kills, per):
                stage['groups'].append([(st['mob'], 'minion', min(per, kills - i))])
                stage['where'].append(rooms[min(len(rooms) - 1, i // (per * 2))])
            stage['rooms'] = sorted(set(stage['where']), key=stage['where'].index)
        elif kind == 'ritual':
            stage['groups'] = [[(w['vnum'], 'wave', w.get('count', 1) + extra, w.get('at', 0)) for w in load(st['waves'])]]
            stage['where'] = [st['room']]
            stage['rooms'] = [st['room']]
        elif kind == 'trial':
            tpl = json.load(open(os.path.join(SRC, '..', 'world', 'marquee', 'trials', f"{st.get('trial', cls)}.json")))
            # its waves (each fought on its own), then the boss
            stage['groups'] = [[(vnum, 'wave', count + (extra if j == 0 else 0)) for j, (vnum, count) in enumerate(w.get('mobs', []))]
                               for w in load(tpl.get('waves', []))]
            if (tpl.get('boss') or {}).get('vnum'):
                stage['groups'].append([(tpl['boss']['vnum'], 'boss', 1)])
            stage['where'] = [st['room']] * len(stage['groups'])
            stage['rooms'] = [st['room']]
            stage['inside'] = len(load(tpl.get('rooms', [])))
        out.append(stage)
    return q['giver_room'], out


_DIST = {}


def steps(world, a, b):
    """Rooms walked from a to b by the shortest way a mortal may walk (exits as the world has them;
    doors ignored, but not the bar of a land sealed until built, nor the God Rooms)."""
    if a is None or b is None or a == b:
        return 0
    if a not in _DIST:
        from collections import deque
        import doors
        seen = {a: 0}
        todo = deque([a])
        while todo:
            v = todo.popleft()
            room = world.rooms.get(v)
            for ex in (getattr(room, 'exits', None) or {}).values():
                to = ex.get('to_room') if isinstance(ex, dict) else getattr(ex, 'to_room', None)
                if isinstance(ex, dict) and doors.is_seal(ex.get('door')):
                    continue
                if to is not None and to not in seen and to in world.rooms and 'imm_only' not in world.rooms[to].flags:
                    seen[to] = seen[v] + 1
                    todo.append(to)
        _DIST[a] = seen
    return _DIST[a].get(b, UNREACHABLE)


UNREACHABLE = 40          # rooms, when the map has no way through (a portal, a one-way exit)
WALK = 4.0                # seconds a room takes to cross, on average (the 3D client's walk; telnet is quicker)


async def run_quest(world, cls, level, n, mode, dodge, travel, gear, seed, walk=None):
    """One quest played through: travel is the minutes each leg costs besides the walking (finding
    the way, reading, talking), walk the seconds a room takes to cross."""
    walk = WALK if walk is None else walk
    random.seed(seed)
    DEATHS.clear()
    DEALT.clear()
    room = world.rooms.get(3054) or next(iter(world.rooms.values()))
    party = [await make_hero(world, cls, level, f'Sim{cls[:3].title()}{seed}a', gear)]
    for i in range(1, n):
        mate = PARTY[(i - 1) % len(PARTY)]
        party.append(await make_hero(world, mate, level, f'Sim{mate[:3].title()}{seed}{chr(97 + i)}', gear))
    classes = [h.char_class for h in party]      # who embarked: the creatures are made for them
    stages = []
    stats = {}
    if VERBOSE:
        for h in party:
            w = h.equipment.get('wield')
            print(f"  {h.name} {h.char_class} L{h.level}: hp {h.max_hp} mana {h.max_mana} ac {h.get_armor_class()} "
                  f"hit +{h.get_hit_bonus()} dam +{h.get_damage_bonus()} weapon {getattr(w, 'damage_dice', None)} "
                  f"({len(h.equipment)} slots worn), {len(rotation(h.char_class, level)[0])} attacks, "
                  f"{len(rotation(h.char_class, level)[1])} heals")
    home, quest = fights_of(world, cls, n)
    respawn = getattr(world.config, 'STARTING_ROOM', None) or getattr(world.config, 'MORTAL_START_ROOM', 3001)
    pos = home
    for stage in quest:
        label, groups = stage['label'], stage['groups']
        secs_fight = 0.0
        mins_rest = 0.0
        mins_back = 0.0
        # the way there: each of the stage's places in turn, by the shortest way
        mins_walk = 0.0
        for r in stage['rooms']:
            mins_walk += travel + steps(world, pos, r) * walk / 60
            pos = r
        mins_walk += stage['inside'] * walk / 60
        for gi, g in enumerate(groups):
            def make():
                out = []
                for vnum, kind, count, *at in g:
                    for _ in range(count):
                        m = spawn(world, vnum, kind, level, n, classes)
                        if m is not None:
                            m._arrive_at = at[0] if at else 0      # a ritual's later waves come later
                            out.append(m)
                return out
            foes = make()
            if not foes:
                continue
            ritual = any(len(x) > 3 for x in g)
            kinds = {k for _v, k, *_ in g}
            kind = 'boss' if 'boss' in kinds else 'warden' if 'warden' in kinds else 'elite' if 'elite' in kinds else sorted(kinds)[0]
            for attempt in range(1 + RETRIES):
                hp_before = {h.name: h.hp for h in party}
                for h in party:
                    h._low = h.hp
                secs_fight += await fight(world, room, party, foes, mode, dodge, stats)
                # how close the fight came to killing them: the most of their health it took at
                # any point (a healer who mends back up still counts the low point; the dead, all)
                lost = [1.0 if h.hp <= 0 else min(1.0, (hp_before[h.name] - min(h._low, h.hp)) / max(1, h.max_hp)) for h in party]
                stats.setdefault('lost', {}).setdefault(kind, []).append(max(lost))
                wiped = not [h for h in party if h.hp > 0]
                rested = rest(party)
                mins_rest += rested
                left = [f for f in foes if f.hp > 0]
                if not left or not wiped:
                    break
                stats.setdefault('lost_to', {}).setdefault(kind, 0)
                stats['lost_to'][kind] += 1
                # beaten: back from the temple to what is left of it, which has healed while
                # nobody fought it (Mobile.regen_tick: 5% a minute, at most 500 for a big one); a
                # ritual starts over
                stats['retries'] = stats.get('retries', 0) + 1
                back = travel + (steps(world, respawn, stage['where'][gi]) + stage['inside']) * walk / 60
                mins_back += back
                away = rested + back
                if ritual:
                    foes = make()
                    continue
                for f in left:
                    f.hp = min(f.max_hp, f.hp + int(away * (min(500, f.max_hp // 20) if f.max_hp > 5000 else max(1, f.max_hp // 20))))
                    f.fighting = None
                    if getattr(f, 'ai_state', None) is not None and hasattr(f, 'boss_config'):
                        # out of the fight a boss forgets it (Boss.process_ai): no cast, no enrage
                        f.ai_state.update(cast=None, combat_start=None, next_ability_time=0, vulnerable_until=0, enraged=False)
                foes = left
            else:
                stats['stuck'] = stats.get('stuck', 0) + 1
        stages.append({'stage': label, 'fight': secs_fight / 60, 'rest': mins_rest, 'travel': mins_walk + mins_back})
        if VERBOSE:
            print(f"    {label:48} fights {len(groups):2}  fighting {secs_fight / 60:5.1f} min  resting {mins_rest:5.1f} min  "
                  f"deaths so far {len(DEATHS)}  abilities used {stats.get('abilities', 0)}")
    from pets import PetManager
    for h in party:
        for pet in PetManager.get_player_pets(h):
            if pet in world.npcs:
                world.npcs.remove(pet)
            if pet.room is not None and pet in pet.room.characters:
                pet.room.characters.remove(pet)
        world.players.pop(h.name.lower(), None)
        if h.room is not None and h in h.room.characters:
            h.room.characters.remove(h)
    owner = party[0]
    rounds = max(1, stats.get('rounds', 1))
    # alone, all the foes lost is the hero's (damage over time included); in a party each hero's
    # share is what their own blows, skills and spells took (damage over time isn't credited)
    party_dpr = stats.get('foe_loss', 0) / rounds
    return {'stages': stages, 'deaths': list(DEATHS), 'retries': stats.get('retries', 0), 'stuck': stats.get('stuck', 0),
            'lost_to': dict(stats.get('lost_to', {})), 'owner_dpr': party_dpr if n == 1 else DEALT.get(owner.name, 0) / rounds,
            'party_dpr': party_dpr,
            'lost': {k: statistics.mean(v) for k, v in stats.get('lost', {}).items()}}


# ---------------------------------------------------------------- the report
def summarize(results):
    import marquee_scale as ms
    rows = []
    for (cls, level, n), runs in sorted(results.items()):
        tot = [sum(s['fight'] + s['rest'] + s['travel'] for s in r['stages']) for r in runs]
        fight = [sum(s['fight'] for s in r['stages']) for r in runs]
        lost = {}
        for r in runs:
            for k, v in r.get('lost', {}).items():
                lost.setdefault(k, []).append(v)
        rows.append({'class': cls, 'level': level, 'party': n, 'total_min': statistics.mean(tot), 'fight_min': statistics.mean(fight),
                     'deaths': statistics.mean(len(r['deaths']) for r in runs),
                     'retries': statistics.mean(r.get('retries', 0) for r in runs), 'stuck': sum(r.get('stuck', 0) for r in runs),
                     'lost_to': {k: sum(r.get('lost_to', {}).get(k, 0) for r in runs) / len(runs) for k in {k for r in runs for k in r.get('lost_to', {})}},
                     'walk': statistics.mean(sum(s['travel'] for s in r['stages']) for r in runs),
                     'rest': statistics.mean(sum(s['rest'] for s in r['stages']) for r in runs),
                     'owner_dpr': statistics.mean(r['owner_dpr'] for r in runs), 'dpr_ref': ms.dpr(level),
                     'lost': {k: statistics.mean(v) for k, v in lost.items()}})
    return rows


def table(rows):
    out = ['| class | level | party | minutes in all | fighting | resting | on the way | deaths | fights lost (to) | '
           'hero damage/round | dpr() | health at worst: elite / warden / wave / boss |',
           '|---|---|---|---|---|---|---|---|---|---|---|---|']
    pct = lambda d, k: f"{100 * d[k]:.0f}%" if k in d else '-'
    for r in rows:
        L = r.get('lost', {})
        to = ', '.join(f"{k} {v:.1f}" for k, v in sorted(r.get('lost_to', {}).items(), key=lambda x: -x[1]) if v)
        out.append(f"| {r['class']} | {r['level']} | {r['party']} | {r['total_min']:.0f} | {r['fight_min']:.0f} | {r['rest']:.0f} | "
                   f"{r['walk']:.0f} | {r['deaths']:.1f} | {r['retries']:.1f}{' (' + to + ')' if to else ''}"
                   f"{' stuck ' + str(r['stuck']) if r['stuck'] else ''} | {r['owner_dpr']:.0f} | {r['dpr_ref']:.0f} | "
                   f"{pct(L, 'elite')} / {pct(L, 'warden')} / {pct(L, 'wave')} / {pct(L, 'boss')} |")
    return '\n'.join(out)


def _crossing(curve, target):
    """The x at which a rising (x, y) curve first reaches target (linear between grid points)."""
    for (x0, y0), (x1, y1) in zip(curve, curve[1:]):
        if y0 < target <= y1:
            return x0 + (x1 - x0) * (target - y0) / max(1e-9, y1 - y0)
    return curve[0][0] if curve[0][1] >= target else curve[-1][0]


async def calibrate(world, a):
    """What marquee_scale's per-class numbers should be, measured: CLASS_K from each class's own
    damage against the median hero's (dpr), then CLASS_D, the share of the creatures' damage at
    which a lone hero's trial boss costs them --target of their health at its worst (a lost
    attempt counts as all of it) or the quest kills them --max-deaths times, whichever comes
    first, found on a grid of shares at each level and averaged."""
    import marquee_scale as ms
    classes = a.classes.split(',')
    levels = [int(x) for x in a.levels.split(',')]
    grid = [float(x) for x in a.grid.split(',')]
    dprs = {}
    for cls in classes:
        for level in levels:
            runs = [await run_quest(world, cls, level, 1, a.mode, a.dodge, a.travel, a.gear, seed=3000 + r, walk=a.walk) for r in range(a.runs)]
            dprs[(cls, level)] = statistics.mean(r['owner_dpr'] for r in runs)
    print('damage per round, alone:')
    for level in levels:
        row = {c: dprs[(c, level)] for c in classes}
        print(f"  L{level}: median {statistics.median(row.values()):.0f} (dpr() {ms.dpr(level):.0f}) " +
              ' '.join(f"{c} {v:.0f}" for c, v in row.items()))
    k = {c: statistics.mean(dprs[(c, L)] / ms.dpr(L) for L in levels) for c in classes}
    print('CLASS_K measured:', {c: round(v, 2) for c, v in k.items()}, '(in use:', {c: ms.CLASS_K.get(c) for c in classes}, ')')
    d_of = {}
    for cls in classes:
        keep = ms.CLASS_D.get(cls, 1.0)
        found = []
        for level in levels:
            curve = []
            for d in grid:
                ms.CLASS_D[cls] = d
                runs = [await run_quest(world, cls, level, 1, a.mode, a.dodge, a.travel, a.gear, seed=2000 + r, walk=a.walk) for r in range(a.runs)]
                boss = statistics.mean(r['lost'].get('boss', 0) for r in runs)
                curve.append((d, boss, statistics.mean(len(r['deaths']) for r in runs)))
            x = min(_crossing([(d, b) for d, b, _ in curve], a.target), _crossing([(d, dd) for d, _, dd in curve], a.max_deaths))
            found.append(x)
            print(f"  {cls:12} L{level}: boss cost by share " + ' '.join(f"{d:g}:{100 * b:.0f}%/{dd:.1f}d" for d, b, dd in curve) +
                  f"  -> {x:.2f}", flush=True)
        ms.CLASS_D[cls] = keep
        d_of[cls] = statistics.mean(found)
    print('CLASS_D measured:', {c: round(v, 2) for c, v in d_of.items()})


async def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--classes', default=','.join(CLASSES))
    ap.add_argument('--levels', default='45,50')
    ap.add_argument('--party', default='1,2,3,6')
    ap.add_argument('--runs', type=int, default=1)
    ap.add_argument('--mode', choices=['rounds', 'action'], default='rounds')
    ap.add_argument('--dodge', type=float, default=0.6, help='chance a hero steps out of a marked blow')
    ap.add_argument('--travel', type=float, default=1.0, help='minutes each leg costs besides walking (finding the way, reading)')
    ap.add_argument('--walk', type=float, default=WALK, help='seconds a room takes to cross')
    ap.add_argument('--gear', type=float, default=0.75, help='percentile of the gear a slot offers at the level')
    ap.add_argument('--report', default=None, help='write the table (markdown) here too')
    ap.add_argument('--verbose', action='store_true', help='each hero and each stage')
    ap.add_argument('--foe-damage', default='', help="try other creature damage shares, e.g. elite=0.8,boss=0.6")
    ap.add_argument('--class-damage', default='', help="try other per-class shares (CLASS_D), e.g. mage=0.6")
    ap.add_argument('--calibrate', action='store_true', help="measure CLASS_K and CLASS_D (alone, --levels, --runs each)")
    ap.add_argument('--target', type=float, default=0.65, help="--calibrate: the share of a lone hero's health the boss should cost")
    ap.add_argument('--max-deaths', type=float, default=0.5, help="--calibrate: ...or the deaths a lone hero's quest may cost")
    ap.add_argument('--grid', default='0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.2,1.4,1.7,2.0', help="--calibrate: the CLASS_D values tried")
    a = ap.parse_args()
    import marquee_scale as ms
    for opt, table_ in ((a.foe_damage, ms.FOE_DAMAGE), (a.class_damage, ms.CLASS_D)):
        for kv in filter(None, opt.split(',')):
            k, v = kv.split('=')
            table_[k.strip()] = float(v)
    global VERBOSE
    VERBOSE = a.verbose
    world = await load_world()
    patch_deaths(world)
    patch_damage()
    if a.calibrate:
        await calibrate(world, a)
        return
    results = {}
    for cls in a.classes.split(','):
        for level in [int(x) for x in a.levels.split(',')]:
            for n in [int(x) for x in a.party.split(',')]:
                for r in range(a.runs):
                    res = await run_quest(world, cls, level, n, a.mode, a.dodge, a.travel, a.gear, seed=1000 + r, walk=a.walk)
                    results.setdefault((cls, level, n), []).append(res)
                    print(f"{cls:12} L{level} x{n} run {r + 1}: "
                          f"{sum(s['fight'] + s['rest'] + s['travel'] for s in res['stages']):.0f} min "
                          f"(fighting {sum(s['fight'] for s in res['stages']):.0f}), deaths {len(res['deaths'])}, "
                          f"fights lost {res['retries']}{' STUCK' if res['stuck'] else ''}, "
                          f"hero {res['owner_dpr']:.0f}/round", flush=True)
    rows = summarize(results)
    print('\n' + table(rows))
    if a.report:
        os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
        with open(a.report, 'w') as f:
            f.write(table(rows) + '\n')


if __name__ == '__main__':
    asyncio.run(main())
