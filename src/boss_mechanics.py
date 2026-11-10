"""What makes a boss fight more than trading blows (the owner: "special abilities for npcs/mob
bosses, interesting room dynamics"). A boss's `mechanics` (from its zone's population file,
world/population/zone_<n>.json) run beside its abilities every AI tick (bosses.Boss.process_ai):

  plague_pools   drops pools of plague at a fighter's feet; standing in one sickens you (step out)
  call_guards    at health thresholds, the zone's creatures nearby rush in (and more are raised)
  hunger         all who stand still starve: health and stamina drain unless you keep moving
  waves          at health thresholds, a wave of servants rises
  gloom          the room darkens as the boss weakens (the 3D client dims its light)

Any of them given "below": <health %> waits for the fight's last stretch (Ostragoth's thirst at 30%).

The 3D client sees them as events: 'hazard' (a lasting danger zone on the ground, with the STEP
OUT cue), 'gloom' (how dark), and the boss's own windups and adds.
"""
import math
import random
import time

POOL_TICK = 2.0
POOL_ARM = 1.5       # a pool burns only after this long: the STEP OUT cue has a moment to be heeded


def _fighters(boss):
    room = boss.room
    return [c for c in (room.characters if room else []) if hasattr(c, 'connection') and getattr(c, 'hp', 0) > 0]


def _pos(ch):
    try:
        import combat_range as cr
        return cr.pos_of(ch)
    except Exception:
        return None


def _emit(boss, k, dst=None, **f):
    try:
        import combat_events as ev
        ev.emit(boss.room, k, src=boss, dst=dst, **f)
    except Exception:
        pass


async def _say(boss, text):
    if boss.room:
        await boss.room.send_to_room(text)


class Mechanic:
    def __init__(self, spec):
        self.spec = spec

    def reset(self, boss):
        pass

    async def tick(self, boss, now):
        pass


class PlaguePools(Mechanic):
    """Pools of plague where a fighter stands; once one settles (POOL_ARM), a sickness each POOL_TICK
    to all inside."""
    def reset(self, boss):
        self.pools, self.next, self.hurt_at = [], 0, 0

    async def tick(self, boss, now):
        if not hasattr(self, 'pools'):
            self.reset(boss)
        s = self.spec
        self.pools = [p for p in self.pools if p['until'] > now]
        if now >= self.next:
            self.next = now + float(s.get('every', 9))
            who = random.choice(_fighters(boss) or [None])
            if who is not None:
                p = _pos(who)
                r, last = float(s.get('radius', 2.4)), float(s.get('last', 14))
                if p is None:
                    last = min(last, 4.5)    # nowhere known (a telnet fighter): it catches them a moment only
                pool = {'x': p[0] if p else None, 'z': p[1] if p else None, 'r': r, 'until': now + last, 'on': who,
                        'from': now + POOL_ARM}
                self.pools.append(pool)
                area = {'shape': 'circle', 'r': r, 'x': round(p[0], 2), 'z': round(p[1], 2)} if p else None
                _emit(boss, 'hazard', dst=who, label=s.get('label', 'Plague Pool'), area=area, ms=int(last * 1000),
                      school=s.get('school', 'poison'), id=f"pool{int(now * 1000) % 100000}")
                await _say(boss, f"{boss.name} spits a pool of seething plague at {who.name}'s feet! Get out of it!")
        live = [pl for pl in self.pools if pl.get('from', 0) <= now]
        if now - self.hurt_at < POOL_TICK or not live:
            return
        self.hurt_at = now
        for ch in _fighters(boss):
            p = _pos(ch)
            inside = any((p and pl['x'] is not None and math.hypot(p[0] - pl['x'], p[1] - pl['z']) <= pl['r'])
                         or (pl['x'] is None and pl['on'] is ch) for pl in live)
            if not inside:
                continue
            dmg = max(1, int(ch.max_hp * float(self.spec.get('pct', 0.04))))
            await ch.send(f"The plague pool burns you! [{dmg}]")
            await ch.take_damage(dmg, boss, self.spec.get('school', 'poison'))


class CallGuards(Mechanic):
    """At each health threshold, nearby creatures of the zone rush to the boss's side; raised
    ones fill out the count."""
    def reset(self, boss):
        self.done = set()

    async def tick(self, boss, now):
        if not hasattr(self, 'done'):
            self.reset(boss)
        pct = boss._hp_pct()
        for t in self.spec.get('at', [75, 40]):
            if pct <= t and t not in self.done:
                self.done.add(t)
                await self._call(boss)

    async def _call(self, boss):
        s, room = self.spec, boss.room
        want = int(s.get('count', 3))
        came = []
        # breadth-first, a few rooms out, the zone's own creatures who are free to come
        seen, frontier = {room.vnum}, [(room, None)]
        for _ in range(int(s.get('rooms', 2))):
            nxt = []
            for r, _first in frontier:
                for d, ex in (r.exits or {}).items():
                    to = ex.get('room') if isinstance(ex, dict) else None
                    if to is None or to.vnum in seen or to.zone is not room.zone:
                        continue
                    seen.add(to.vnum)
                    nxt.append((to, d))
                    for m in list(to.characters):
                        if len(came) >= want:
                            break
                        if hasattr(m, 'connection') or getattr(m, 'is_boss', False) or getattr(m, 'fighting', None):
                            continue
                        if getattr(m, 'special', None) in ('shopkeeper', 'innkeeper', 'banker', 'receptionist'):
                            continue
                        came.append((m, to))
            frontier = nxt
        await _say(boss, s.get('shout', f"{boss.name} bellows a rallying cry! The halls answer!"))
        target = boss.fighting
        for m, frm in came:
            frm.characters.remove(m)
            m.room = room
            room.characters.append(m)
            await room.send_to_room(f"{m.name} rushes in to {boss.name}'s side!")
            if target is not None:
                m.fighting, m.position = target, 'fighting'
            try:
                await m._notify_move(frm, room, 'somewhere', 'somewhere')
            except Exception:
                pass
        missing = want - len(came)
        if missing > 0 and s.get('raise'):
            await boss._spawn_adds({int(v): max(1, missing // len(s['raise'])) for v in s['raise']})


class Hunger(Mechanic):
    """Every few seconds, whoever has not moved starves (health and stamina); moving spares you."""
    def reset(self, boss):
        self.next, self.last, self.warned = 0, {}, 0

    async def tick(self, boss, now):
        if not hasattr(self, 'last'):
            self.reset(boss)
        if now < self.next:
            return
        s = self.spec
        self.next = now + float(s.get('every', 3))
        if now - self.warned > 20:
            self.warned = now
            await _say(boss, s.get('warn', f"{boss.name}'s hunger gnaws at all who stand still. Keep moving!"))
        for ch in _fighters(boss):
            p, was = _pos(ch), self.last.get(ch.name)
            self.last[ch.name] = p
            moved = p is not None and was is not None and math.hypot(p[0] - was[0], p[1] - was[1]) >= float(s.get('still', 0.8))
            if moved:
                continue
            k = 0.5 if p is None else 1.0          # a telnet fighter, who cannot step, starves slower
            dmg = max(1, int(ch.max_hp * float(s.get('pct', 0.025)) * k))
            ch.move = max(0, getattr(ch, 'move', 0) - int(s.get('stamina', 10) * k))
            school = s.get('school', 'necrotic')
            await ch.send(f"{s.get('hit', 'Hunger hollows you out!')} [{dmg}]")
            _emit(boss, 'debuff', dst=ch, label=s.get('label', 'Starving'), school=school)
            await ch.take_damage(dmg, boss, school)


class Waves(Mechanic):
    """At each health threshold, a wave of servants rises."""
    def reset(self, boss):
        self.done = set()

    async def tick(self, boss, now):
        if not hasattr(self, 'done'):
            self.reset(boss)
        pct = boss._hp_pct()
        for t in self.spec.get('at', [75, 50, 25]):
            if pct <= t and t not in self.done:
                self.done.add(t)
                await _say(boss, self.spec.get('shout', f"{boss.name} raises a hand, and the dead answer!"))
                await boss._spawn_adds({int(k): int(v) for k, v in (self.spec.get('adds') or {}).items()})


class Gloom(Mechanic):
    """The room darkens as the boss weakens (and lifts when the fight ends)."""
    def reset(self, boss):
        if getattr(self, 'level', 0):
            _emit(boss, 'gloom', level=0)
        self.level = 0

    async def tick(self, boss, now):
        if not hasattr(self, 'level'):
            self.level = 0
        want = round((1 - boss._hp_pct() / 100) * float(self.spec.get('max', 0.85)), 1)
        if want >= self.level + 0.2:
            self.level = want
            _emit(boss, 'gloom', level=want)
            if want >= 0.4:
                await _say(boss, self.spec.get('shout', f"The light gutters and dies around {boss.name}..."))


KINDS = {'plague_pools': PlaguePools, 'call_guards': CallGuards, 'hunger': Hunger, 'waves': Waves, 'gloom': Gloom}


def build(specs):
    return [KINDS[s['type']](s) for s in (specs or []) if s.get('type') in KINDS]
