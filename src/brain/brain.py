"""One creature's brain: what it is (roles, profile), what it is doing (mode), whom it hates
(threat) and its own dice.

Made the first time the creature thinks (brain.of) and kept on it as mob._brain. Its dice are a
random.Random of its own, seeded from the creature's vnum and when it was made, so the brain's
choices never draw on the world's random.* (the balance sims replay that one exactly).
"""
import random
import time
from collections import deque

from .threat import ThreatTable


class Brain:
    __slots__ = ('mob', 'roles', 'profile', 'mode', 'threat', 'rng', 'decisions', 'encounter', 'born', 'last_target')

    def __init__(self, mob):
        from . import roles as roles_mod, profile as profile_mod
        self.mob = mob
        self.roles = roles_mod.roles_for(mob)
        self.profile = profile_mod.resolve(mob, self.roles)
        self.mode = 'legacy'
        self.threat = ThreatTable()
        self.born = time.time()
        self.rng = random.Random(hash((getattr(mob, 'vnum', 0), id(mob))))
        self.decisions = deque(maxlen=5)     # (when, what, score, why), newest last
        self.encounter = {}                  # cooldowns and once-a-fight flags, cleared on reset
        self.last_target = None              # the target it last chose (targeting.py)

    def note(self, what, score=None, why=''):
        self.decisions.append((time.time(), what, score, why))

    def reset_encounter(self):
        self.encounter.clear()
        self.threat.clear()
        self.last_target = None

    def describe(self) -> list:
        """Lines for the immortal "brain" command."""
        m, p = self.mob, self.profile
        out = [f"{getattr(m, 'name', m)} (vnum {getattr(m, 'vnum', '?')})  mode {self.mode}",
               f"  tier {p.get('tier')}  rank {p.get('rank')}  roles {', '.join(sorted(self.roles)) or '-'}"]
        keys = ('leash_rooms', 'chase_secs', 'assist_rooms', 'assist_count', 'target_stickiness',
                'focus_healers', 'cc_chain', 'windup_action_s', 'room_windup_cap')
        out.append('  ' + '  '.join(f"{k} {p.get(k)}" for k in keys if k in p))
        if len(self.threat):
            now = time.time()
            fix = self.threat.fixated_on if now < self.threat.fixated_until else None
            out.append('  threat: ' + ', '.join(
                f"{getattr(ch, 'name', ch)} {v:.0f}{' (taunted)' if ch is fix else ''}"
                for ch, v in self.threat.ranked()[:6]))
        else:
            out.append('  threat: none')
        if self.decisions:
            out.append('  last decisions:')
            for t, what, s, why in self.decisions:
                sc = f" {s:.2f}" if isinstance(s, (int, float)) else ''
                out.append(f"    {time.time() - t:5.1f}s ago  {what}{sc}  {why}")
        return out
