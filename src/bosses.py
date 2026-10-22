"""
Misthollow Boss Framework
========================
Bosses extend Mobile with phases, telegraphed abilities, adds, and enrage timers.
"""

import random
import time
import logging
from typing import Dict, List, Optional

from mobs import Mobile
from combat import CombatHandler


def fx_key(label):
    """An ability's look in 3D (combat_hooks.fx_key)."""
    from combat_hooks import fx_key as key
    return key(label)


def _plain(msg):
    """A room line without its colour codes (a phase's message, shown over the boss)."""
    import re
    return re.sub(r'\x1b\[[0-9;]*[A-Za-z]|\{[a-zA-Z_]+\}', '', str(msg or '')).strip()

logger = logging.getLogger('Misthollow.Bosses')


class Boss(Mobile):
    """Boss mob with special mechanics."""

    def __init__(self, vnum: int, world):
        super().__init__(vnum, world)
        self.is_boss = True
        self.boss_id = None
        self.boss_title = None
        self.boss_achievement = None
        self.boss_config: Dict = {}

        self.phase_index = 0
        self.abilities: List[Dict] = []
        self.ability_interval = 4.0
        self.enrage_time = None
        self.enrage_multiplier = 1.0

        self.ai_state = {
            'cooldowns': {},
            'cast': None,
            'combat_start': None,
            'next_ability_time': 0,
            'vulnerable_until': 0,
            'enraged': False,
            'magic_immune_until': 0,
        }

    @classmethod
    def from_prototype(cls, proto: dict, world) -> 'Boss':
        boss = cls(proto.get('vnum', 0), world)
        Mobile.apply_prototype(boss, proto, world)
        boss._apply_boss_config(proto)
        if not proto.get('marquee_sized'):      # a quest's creatures are sized where they are placed
            size_zone_boss(boss)
        return boss

    def _apply_boss_config(self, proto: dict):
        self.boss_id = proto.get('boss_id') or proto.get('name', '').lower().replace(' ', '_')
        self.boss_title = proto.get('boss_title')
        self.boss_achievement = proto.get('boss_achievement')
        self.boss_config = proto.get('boss_config', {})

        self.abilities = self.boss_config.get('abilities', [])
        self.ability_interval = self.boss_config.get('ability_interval', 4.0)
        self.enrage_time = self.boss_config.get('enrage_time')
        self.enrage_multiplier = self.boss_config.get('enrage_multiplier', 1.5)
        # what makes the fight more than blows (boss_mechanics.py: pools, guards, hunger, waves, gloom)
        try:
            import boss_mechanics
            self.mechanics = boss_mechanics.build(proto.get('mechanics'))
        except Exception:
            self.mechanics = []

        # Override loot table if boss specific
        boss_loot = proto.get('boss_loot_table') or self.boss_config.get('loot_table')
        if boss_loot:
            self.loot_table = boss_loot
            self.loot_chance = proto.get('boss_loot_chance', 80)

    def _hp_pct(self) -> float:
        if self.max_hp <= 0:
            return 0
        return (self.hp / self.max_hp) * 100

    def is_vulnerable(self) -> bool:
        return time.time() < self.ai_state.get('vulnerable_until', 0)

    def has_cast(self) -> bool:
        return self.ai_state.get('cast') is not None

    async def process_ai(self):
        if not self.is_alive:
            return
        if self.position in ('sleeping', 'stunned', 'incapacitated'):
            return
        if not self.is_fighting:
            # Reset combat-only state when out of combat
            self.ai_state['cast'] = None
            self.ai_state['combat_start'] = None
            self.ai_state['next_ability_time'] = 0
            self.ai_state['vulnerable_until'] = 0
            self.ai_state['enraged'] = False
            for m in getattr(self, 'mechanics', ()):
                m.reset(self)
            # with the brain's pursuit on, a boss notices who walks in, and resets when they leave
            import brain
            if brain.on('pursuit'):
                await brain.think_own(self)
            return

        now = time.time()
        if not self.ai_state.get('combat_start'):
            self.ai_state['combat_start'] = now

        await self._check_phase_transitions()
        for m in getattr(self, 'mechanics', ()):
            try:
                await m.tick(self, now)
            except Exception:
                logger.exception(f'{self.name}: mechanic {m.spec.get("type")}')
        await self._handle_enrage(now)
        await self._handle_cast(now)

        if self.ai_state.get('cast'):
            return

        if now < self.ai_state.get('next_ability_time', 0):
            return

        ability = self._select_ability()
        if ability:
            await self._start_ability(ability)
            self.ai_state['next_ability_time'] = now + self.ability_interval

    async def _check_phase_transitions(self):
        phases = self.boss_config.get('phases', [])
        if not phases:
            return
        hp_pct = self._hp_pct()
        for idx, phase in enumerate(phases):
            threshold = phase.get('threshold')
            if threshold is None:
                continue
            if hp_pct <= threshold and idx >= self.phase_index:
                self.phase_index = idx + 1
                msg = phase.get('message')
                if msg and self.room:
                    await self.room.send_to_room(msg)
                # the 3D client: the boss roars, the ground breaks, the view jolts (combat.js phase)
                self._emit('phase', n=self.phase_index, label=_plain(msg) or None)
                spawn = phase.get('spawn_adds')
                if spawn:
                    await self._spawn_adds(spawn)

    async def _handle_enrage(self, now: float):
        if not self.enrage_time or self.ai_state.get('enraged'):
            return
        if now - self.ai_state.get('combat_start', now) >= self.enrage_time:
            self.ai_state['enraged'] = True
            if self.room:
                await self.room.send_to_room(f"{self.name} roars and becomes enraged!")
                self._emit('enrage')

    def _select_ability(self) -> Optional[Dict]:
        now = time.time()
        hp_pct = self._hp_pct()
        available = []
        for ability in self.abilities:
            name = ability.get('name')
            if not name:
                continue
            phase = ability.get('phase')
            if phase is not None and phase != self.phase_index:
                continue
            min_phase = ability.get('min_phase')
            if min_phase is not None and self.phase_index < min_phase:
                continue
            max_phase = ability.get('max_phase')
            if max_phase is not None and self.phase_index > max_phase:
                continue
            hp_gate = ability.get('hp_pct')
            if hp_gate is not None and hp_pct > hp_gate:
                continue
            cooldown = ability.get('cooldown', 0)
            next_ready = self.ai_state['cooldowns'].get(name, 0)
            if now < next_ready:
                continue
            available.append(ability)

        if not available:
            return None
        return random.choice(available)

    async def _start_ability(self, ability: Dict):
        name = ability.get('name')
        cast_time = ability.get('cast_time', 0)
        telegraph = ability.get('telegraph')
        target = self._select_target(ability)

        if telegraph and self.room:
            await self.room.send_to_room(telegraph)

        if ability.get('summon'):
            # more help only while fewer than twice the call still stand: it was endless, and a
            # long fight (a zone boss sized for a lone hero) filled the room with them
            await self._spawn_adds(ability['summon'], cap=2 * self._count(ability['summon']))

        if cast_time and cast_time > 0:
            area = self._cast_area(ability, target)
            self.ai_state['cast'] = {
                'ability': ability,
                'resolve_at': time.time() + cast_time,
                'target': target,
                'interrupted': False,
                'area': area,
            }
            # the 3D client marks the ground it will land on (and calls STEP OUT)
            try:
                import combat_events as ev
                from combat_hooks import fx_school
                ev.emit(self.room, 'windup', src=self, dst=target, label=name, kind=self._kind(ability),
                        ms=int(cast_time * 1000), area=area, school=fx_school(self._ability_school(ability)),
                        interruptible=bool(ability.get('interruptible')) or None, fx=fx_key(name))
            except Exception:
                pass
        else:
            # at once: its look goes ahead of the wounds it causes (as a skill's: combat_hooks)
            await self._released(ability, target, None, 'ability')

        cooldown = ability.get('cooldown', 0)
        if name:
            self.ai_state['cooldowns'][name] = time.time() + cooldown

    async def _handle_cast(self, now: float):
        cast = self.ai_state.get('cast')
        if not cast:
            return
        if now < cast['resolve_at']:
            return
        ability = cast['ability']
        target = cast.get('target')

        if cast.get('interrupted'):
            if self.room:
                await self.room.send_to_room(f"{self.name}'s {ability.get('name')} is interrupted!")
            self.ai_state['cast'] = None
            self._emit('cancel', label=ability.get('name'), reason='stagger' if ability.get('vulnerable_after') else 'interrupt',
                       fx=fx_key(ability.get('name')), school=self._fx_school(ability))
            await self._apply_vulnerability(ability)
            return

        try:
            await self._released(ability, target, cast.get('area'), 'resolve')
        finally:
            self.ai_state['cast'] = None      # resolved or not, it is over (a failed one must not freeze the boss)

    async def _released(self, ability: Dict, target, area, k):
        """Land an ability, and tell the 3D client: its 'resolve' (a wound-up one) or 'ability' (an
        instant one) goes ahead of the wounds it caused, aimed at whom it was for, so its numbers
        rise when it arrives; then what it did to the boss itself (a heal, a ward)."""
        room = self.room
        hp0 = self.hp
        self._resolving_area, self._spared = area, []
        try:
            import combat_events as ev
        except Exception:
            ev = None
        if ev is None or room is None:
            try:
                await self._resolve_ability(ability, target)
            finally:
                self._resolving_area, self._spared = None, []
            return
        with ev.hold():
            mark = ev.mark(room)
            try:
                await self._resolve_ability(ability, target)
            finally:
                spared = self._spared
                self._resolving_area, self._spared = None, []
                name = ability.get('name')
                fields = dict(label=name, kind=self._kind(ability), school=self._fx_school(ability), fx=fx_key(name))
                if k == 'resolve':
                    fields.update(area=area, dodged=[ev.ref(c) for c in spared] or None)
                else:
                    fields.update(ability=name, shape=f"nova:{float(ability.get('radius', 4.5)):g}" if ability.get('aoe') else None)
                try:
                    ev.emit_at(room, mark, k, src=self, dst=target, **fields)
                    if self.hp > hp0:
                        ev.emit(room, 'heal', src=self, dst=self, amt=int(self.hp - hp0), school='holy', fx=fx_key(name))
                    if ability.get('magic_immune_duration'):
                        ev.emit(room, 'buff', src=self, dst=self, name='Nullifying Aura', school='arcane', fx='nullifying_aura')
                except Exception:
                    pass

    async def _resolve_ability(self, ability: Dict, target):
        if not self.room:
            return

        name = ability.get('name', 'attack')
        damage = self._calculate_ability_damage(ability)
        dodgeable = ability.get('dodge', False)
        interruptible = ability.get('interruptible', False)
        aoe = ability.get('aoe', False)

        targets = []
        if aoe:
            targets = [c for c in self.room.characters if hasattr(c, 'connection') and c.is_alive]
        elif target:
            targets = [target]

        for tgt in targets:
            if dodgeable and self._did_dodge(tgt):
                if hasattr(tgt, 'send'):      # a pet holding the boss has nobody to tell
                    await tgt.send(f"You dodge {self.name}'s {name}!")
                continue
            # stepped out of the marked ground: the blow hits only earth
            if self._clear_of(getattr(self, '_resolving_area', None), tgt):
                if hasattr(tgt, 'send'):      # a pet holding the boss has nobody to tell
                    await tgt.send(f"You are clear of {self.name}'s {name} — it hits only ground!")
                getattr(self, '_spared', []).append(tgt)
                continue

            if damage > 0:
                if hasattr(tgt, 'send'):      # a pet holding the boss has nobody to tell
                    await tgt.send(f"{self.name}'s {name} hits you! [{damage}]")
                await tgt.take_damage(damage, self, self._ability_school(ability))

        if ability.get('heal_pct'):
            heal_amount = int(self.max_hp * (ability['heal_pct'] / 100))
            self.hp = min(self.max_hp, self.hp + heal_amount)
        if ability.get('heal_amount'):
            self.hp = min(self.max_hp, self.hp + int(ability['heal_amount']))

        if ability.get('magic_immune_duration'):
            self.ai_state['magic_immune_until'] = time.time() + ability['magic_immune_duration']
            if self.room:
                await self.room.send_to_room(f"{self.name} is surrounded by a nullifying aura!")

        if ability.get('vulnerable_after'):
            await self._apply_vulnerability(ability)

        if interruptible and ability.get('on_success_message') and self.room:
            await self.room.send_to_room(ability['on_success_message'])

    def _cast_area(self, ability: Dict, target):
        """Where a wound-up ability will land, in room metres (None without positions):
        around the boss for an area blow, where the target stood for a single one."""
        try:
            import combat_range as cr
            if ability.get('aoe'):
                p = cr.pos_of(self)
                return {'shape': 'circle', 'r': float(ability.get('radius', 4.5)), 'x': round(p[0], 2), 'z': round(p[1], 2)} if p else None
            p = cr.pos_of(target) if target is not None else None
            return {'shape': 'circle', 'r': float(ability.get('radius', 2.2)), 'x': round(p[0], 2), 'z': round(p[1], 2)} if p else None
        except Exception:
            return None

    @staticmethod
    def _clear_of(area, tgt) -> bool:
        if not area or area.get('x') is None:
            return False
        try:
            import combat_range as cr
            p = cr.pos_of(tgt)
        except Exception:
            return False
        if p is None:
            return False
        return ((p[0] - area['x']) ** 2 + (p[1] - area['z']) ** 2) ** 0.5 > area.get('r', 2) + 0.35

    def _emit(self, k, **fields):
        try:
            import combat_events as ev
            ev.emit(self.room, k, src=self, **fields)
        except Exception:
            pass

    @staticmethod
    def _kind(ability: Dict) -> str:
        """What the 3D client is told it is (combat.js, reactions.js): a blow over an area, a spell
        you can break, else a heavy blow."""
        if ability.get('aoe'):
            return 'aoe'
        return 'cast' if ability.get('interruptible') else 'heavy'

    def _fx_school(self, ability: Dict) -> str:
        from combat_hooks import fx_school
        return fx_school(self._ability_school(ability))

    def _summon_school(self) -> str:
        """The colour a boss's adds rise in (combat_hooks.summon_school)."""
        from combat_hooks import summon_school
        return summon_school(self)

    @staticmethod
    def _ability_school(ability: Dict) -> str:
        """The harm an ability deals (what worn resistances answer to): its own `element`, else
        what its name says (Frost Breath, Plague Touch; a blow is physical)."""
        import combat_range
        return combat_range.harm_school(ability.get('name'), ability.get('element'))

    def _calculate_ability_damage(self, ability: Dict) -> int:
        if ability.get('damage_dice'):
            damage = CombatHandler.roll_dice(ability['damage_dice'])
        elif 'damage' in ability:
            if isinstance(ability.get('damage'), list):
                dmg_min, dmg_max = ability['damage']
                damage = random.randint(dmg_min, dmg_max)
            else:
                damage = int(ability.get('damage', 0))
        elif any(ability.get(k) for k in ('summon', 'heal_pct', 'heal_amount', 'magic_immune_duration')):
            damage = 0      # a call for help, a heal, a ward: no blow of its own
        else:
            damage = max(5, self.level * 2)

        if self.ai_state.get('enraged'):
            damage = int(damage * self.enrage_multiplier)

        return max(0, damage)

    def _select_target(self, ability: Dict):
        if not self.room:
            return None
        if ability.get('aoe'):
            return None
        if self.fighting and self.fighting in self.room.characters:
            return self.fighting
        # fallback to any player in room
        players = [c for c in self.room.characters if hasattr(c, 'connection')]
        return random.choice(players) if players else None

    async def _apply_vulnerability(self, ability: Dict):
        duration = ability.get('vulnerable_after') or 0
        if duration <= 0:
            return
        self.ai_state['vulnerable_until'] = time.time() + duration
        if self.room:
            await self.room.send_to_room(f"{self.name} looks exposed!")

    def _did_dodge(self, target) -> bool:
        dodge_until = getattr(target, 'dodging_until', 0)
        if time.time() <= dodge_until:
            target.dodging_until = 0
            return True
        return False

    @staticmethod
    def _count(spawn_config) -> int:
        if isinstance(spawn_config, dict):
            return sum(int(n) for n in spawn_config.values())
        return len(spawn_config) if isinstance(spawn_config, list) else 1

    async def _spawn_adds(self, spawn_config, cap=None):
        """Bring in a boss's adds. cap: a summoning ability's limit on its own callers still
        standing (a phase's adds always come, and don't count)."""
        if not self.room:
            return
        if cap is not None:
            self._called = [a for a in getattr(self, '_called', []) if a.hp > 0 and a.room is not None and a in a.room.characters]
            if len(self._called) >= cap:
                return
        if isinstance(spawn_config, dict):
            spawn_items = list(spawn_config.items())
        elif isinstance(spawn_config, list):
            spawn_items = [(vnum, 1) for vnum in spawn_config]
        else:
            spawn_items = [(spawn_config, 1)]

        from mobs import Mobile
        spawned = []
        for vnum, count in spawn_items:
            proto = self.world.mob_prototypes.get(int(vnum))
            if not proto:
                continue
            for _ in range(count):
                add = Mobile.from_prototype(proto, self.world)
                add.summoned_by = self                    # an add, whatever its file says (mob_ai roles)
                if getattr(self, '_dmg_scale', 1) != 1:
                    add._dmg_scale = self._dmg_scale      # weighed like the boss (a quest's own re-weighs below)
                spawned.append(add)
                add.room = self.room
                add.home_room = self.room
                add.home_zone = self.home_zone
                self.room.characters.append(add)
                self.world.npcs.append(add)
                if self.fighting:
                    add.fighting = self.fighting
                    add.position = 'fighting'

        if cap is not None:
            self._called = getattr(self, '_called', []) + spawned
        # the 3D client: they rise out of the ground around the boss (combat.js summon)
        if spawned:
            try:
                import combat_events as ev
                self._emit('summon', school=self._summon_school(), adds=[ev.ref(a) for a in spawned])
            except Exception:
                pass
        # a quest's boss (marquee.py): its adds belong to the quest too
        hook = getattr(self, 'on_adds', None)
        if hook and spawned:
            try:
                hook(spawned)
            except Exception:
                pass
        await self.room.send_to_room("Reinforcements rush into the fight!")

    def can_dodge(self) -> bool:
        cast = self.ai_state.get('cast')
        if not cast:
            return False
        ability = cast.get('ability', {})
        return ability.get('dodge', False)

    def mark_dodging(self, player):
        cast = self.ai_state.get('cast')
        if not cast:
            return
        resolve_at = cast.get('resolve_at', time.time() + 1)
        player.dodging_until = max(resolve_at, time.time() + 1)

    def can_interrupt(self) -> bool:
        cast = self.ai_state.get('cast')
        if not cast:
            return False
        ability = cast.get('ability', {})
        return ability.get('interruptible', False)

    def attempt_interrupt(self, player) -> bool:
        cast = self.ai_state.get('cast')
        if not cast or not self.can_interrupt():
            return False
        # Chance based on bash/kick or base
        bash = player.skills.get('bash', 0) if hasattr(player, 'skills') else 0
        kick = player.skills.get('kick', 0) if hasattr(player, 'skills') else 0
        base = max(bash, kick, 25)
        bonus = (getattr(player, 'str', 10) - 10) * 2
        chance = min(95, base + bonus)

        if random.randint(1, 100) <= chance:
            cast['interrupted'] = True
            return True
        return False


# Zone bosses (the dungeon bosses of the world's zones; world_events.py's event bosses are another
# thing) are sized for a lone hero at their level, like a marquee trial's boss (docs/balance/marquee.md,
# "Zone bosses"). Their files were written for far weaker heroes: a party of three felled every one
# of the first 20 in 2-6 rounds for 0-15% of its health (111 now, with the populated zones' bosses).
# Health is ZONE_BOSS_ROUNDS of what the median hero of the boss's level deals (marquee_scale.dpr):
# about two minutes alone, under one for three.
# Each boss's own blows and abilities are then weighed (ZONE_BOSS_DAMAGE, measured with
# tools/balance/bosses.py --calibrate) so that a lone hero at its level loses about half their
# health at the worst moment: the frailest classes most of it. Bosses above the mortal level cap
# keep their files' numbers (raid fights), and a marquee quest's creatures are sized where they
# are placed (marquee_scale).
ZONE_BOSS_ROUNDS = 40
# vnum -> share of the boss's own blows, abilities, poison and adds, measured (--calibrate --runs 2):
# a file with no damage dice hits with 1d6, a caster's kit can hit nine times too hard, and a boss
# whose followers or waves come (boss_mechanics.py) holds out longer, so its blows weigh less
ZONE_BOSS_DAMAGE = {
    3610: 0.39,     # L10 the Black King
    3611: 0.38,     # L10 the White King
    20007: 0.34,    # L12 spider queen
    641606: 0.2,    # L13 Lord Khal, the necromancer
    644906: 0.43,   # L13 the fire spirit of the crest
    20008: 0.61,    # L14 alpha wolf
    3014: 0.6,      # L15 sewer king
    6114: 0.48,     # L15 the Queen spider
    6210: 0.19,     # L15 Elstar
    18009: 0.67,    # L15 the alpha wolf
    42310: 0.44,    # L16 the false Canon
    642606: 0.5,    # L16 Hrungar the hill giant
    644103: 0.49,   # L16 a barrow wight
    643907: 0.58,   # L17 Hyperion, the Chained Titan
    648806: 0.55,   # L17 Vhaz'ul, demon of the abyss
    43550: 0.28,    # L18 Farrot the great roc
    47150: 0.28,    # L18 the Black Priest
    72000: 0.7,     # L18 the Rat King
    642406: 0.65,   # L18 Aldric Vane, the skeletal crypt lord
    645207: 0.56,   # L18 the Scaled Beast of Zaebos
    645306: 0.24,   # L18 Zikrak, the Kobold Shaman
    40050: 0.5,     # L20 Grondar, the Hill Giant Chieftain
    45150: 0.65,    # L20 the Ice Leviathan
    48210: 0.54,    # L20 the Lord of the House
    52150: 0.25,    # L20 the Winter Witch
    90500: 0.24,    # L20 the Bog Witch
    647408: 0.29,   # L20 Ilvareth, the Cave Elf King
    652207: 0.41,   # L20 Hrimgar, the Frost Giant King
    645407: 0.48,   # L21 the Pale Man, a bone-white ogre lord
    645506: 0.45,   # L21 Aldric, the Barrow-King
    646507: 0.49,   # L21 a towering balrog
    647006: 0.17,   # L21 Ostragoth, the sorcerer-lord
    650206: 0.29,   # L21 Zhaarok, the draconian high priest
    2537: 0.39,     # L22 the Master Summoner
    3503: 0.59,     # L22 the Goblin King (and his goblins)
    6450: 0.24,     # L22 Rand the Dreamer
    641406: 0.25,   # L22 Doctor Ilmeric Vane, the Mad Botanist
    641906: 0.15,   # L22 Maelgrim the Pale, high priest of the cult
    644506: 0.33,   # L22 Brogg Skullsplitter, the Ogre Chieftain
    645806: 0.47,   # L22 Lord Aldric Varok, a vampire
    648007: 0.46,   # L22 Lord Aldric Tudor, the Pale Master
    649906: 0.15,   # L22 Phaeton, master of the Academy
    651806: 0.09,   # L22 Malvoran, the Master Necromancer
    47902: 0.53,    # L23 Morticia
    646107: 0.45,   # L23 Acrasia, the ghost queen of the tombs
    5010: 0.71,     # L24 the dracolich
    66050: 0.56,    # L24 Hrimgar the Frost Jarl
    643607: 0.24,   # L24 Baron Kalveh, lord of the fief
    646406: 0.33,   # L24 Overseer Harrok the Corrupted
    3016: 1.48,     # L25 ancient guardian
    10050: 0.41,    # L25 Skarg the goblin warlord
    23513: 0.28,    # L25 Goblin King Grizznak
    43130: 0.29,    # L25 the Hollow Bishop
    642906: 0.48,   # L25 the Ancient Champion
    644706: 0.25,   # L25 the Lord of Mahn-Tor
    649106: 0.25,   # L25 Morvoct, the goblin warlord
    649506: 0.55,   # L25 the Judge of the Dead
    649606: 0.41,   # L25 the Lag Wyrm
    907: 0.68,      # L26 King Minos the Minotaur
    6314: 0.49,     # L26 the Spider Queen
    13130: 0.39,    # L26 Nerathis, the Drowned King
    47250: 0.23,    # L26 the Wyvern Matriarch
    646706: 0.38,   # L27 Asmolov the ogre warlord
    647607: 0.08,   # L27 Ulgrathar, the High Druid
    647807: 0.38,   # L27 Machk-Gyi, the fire lord
    5318: 0.11,     # L28 the Necromancer
    19007: 0.58,    # L28 frozen dwarven king
    51200: 0.42,    # L28 the High Priestess of Lloth
    79000: 0.17,    # L28 Redferne the Wizard
    6516: 0.2,      # L29 the mazekeeper
    3305: 0.37,     # L30 Aglandiir
    7304: 0.48,     # L30 master mindflayer
    19010: 0.24,    # L30 Vyrkothas the Frost Wyrm
    40820: 0.64,    # L30 the Barrow King
    42030: 0.32,    # L30 the First Hero
    47530: 0.33,    # L30 the Lord of Chaos
    651906: 0.09,   # L31 Archmagus Vorlath the Gilded
    9910: 0.83,     # L33 the Deep Dragon
    15001: 0.83,    # L33 King Welmar
    120501: 0.44,   # L34 the High Priest of Terror
    652006: 0.56,   # L34 Hadrec Vael, the cursed Warden
    6704: 0.76,     # L35 the raider chieftain
    23812: 0.5,     # L35 the Abbot's Ghost
    27015: 1.69,    # L36 Grimclaw the Great Bear (no damage dice in its file)
    5317: 0.96,     # L38 Ramses the Damned
    21050: 0.75,    # L38 the Stick Mother
    27010: 1.58,    # L40 the Oakfather (no damage dice in its file)
    27016: 0.37,    # L40 the Blightlord
    650106: 0.29,   # L42 Karrak, the stone troll of the deep shaft
    650306: 0.23,   # L43 Hrodgar Ironcrown, the usurper king
    5360: 0.92,     # L44 Aurexus the Bronze Dragon
    650507: 0.36,   # L44 Bone Gnasher
    5200: 0.76,     # L45 beholder
    6805: 0.76,     # L45 Captain Blackhand
    14050: 0.58,    # L45 Morthul the Lich Lord
    650706: 0.58,   # L46 the Vampire Lord
    650806: 0.52,   # L46 Durgrim, the undead Dwarf King
    14030: 0.58,    # L47 Verdraxx the Green Dragon
    650906: 0.32,   # L49 Gorrakh the Rock-Eater, a stone troll
    2564: 0.58,     # L50 the Grand Mistress
    8003: 0.28,     # L50 Scorathax the Red Dragon
    16025: 0.63,    # L50 Kaleidos the Prismatic Dragon
    24006: 0.67,    # L50 the Kraken
    6950: 0.59,     # L52 the Cinder Tyrant
    651217: 0.3,    # L52 Orschnag the orc king
    24505: 0.36,    # L55 Shadow Lord Malachar
    651407: 0.28,   # L55 Moloch, the Ancient Demon Lord
    651505: 0.24,   # L55 Malgrath, High Priest of Orcus
    22030: 1.11,    # L60 gate guardian
    22031: 1.11,    # L60 gate guardian
    24805: 0.2,     # L60 Archon Prime
}


def size_zone_boss(boss):
    """A zone boss's health and the weight of its blows. Its health is the sizing's, whatever its
    file or its rank in a population file says: the old files were written for far weaker heroes,
    a population rank lifts a boss to eleven times a regular's health (about 1.45 times this), and
    a few designed files hold five or seven times it (a fight of ten minutes or more alone)."""
    import marquee_scale as ms
    from config import Config
    level = getattr(boss, 'level', 1) or 1
    if level > getattr(Config, 'MAX_MORTAL_LEVEL', 60) or 9700 <= (getattr(boss, 'vnum', 0) or 0) <= 9799:
        return                  # a raid boss, or a marquee quest's own (marquee_quests.py: 9700-9799)
    want = int(ZONE_BOSS_ROUNDS * ms.dpr(level))
    boss.max_hp = boss.hp = want
    share = ZONE_BOSS_DAMAGE.get(getattr(boss, 'vnum', None))
    if share:
        boss._dmg_scale = share
    boss.zone_sized = True


def create_mob_from_prototype(proto: dict, world) -> Mobile:
    """Factory to create boss or normal mob."""
    if proto.get('boss') or 'boss' in proto.get('flags', []):
        return Boss.from_prototype(proto, world)
    return Mobile.from_prototype(proto, world)
