"""A creature's threat table: who it means to kill, and how badly.

Damage, healing of its foes and taunts raise a name; time and distance let it fade. A taunt also
FIXATES: for a few seconds the taunter is the target whatever the numbers say. Entries are kept by
the character itself (a name is not unique between a player and a creature), and forgotten when
the character dies or leaves the fight.

Who adds how much (features.threat; brain.install hooks them up):
- a blow or a spell that hurts the creature: the damage dealt, times the attacker's CLASS_MOD
  (a warrior's blows count half again, an Iron Wall warrior's twice; a thief's less; a pet's
  three times, so a necromancer's servant still holds what it fights);
- healing someone the creature is fighting: HEAL_SHARE of the health restored, shared among the
  creatures fighting the one healed;
- a taunt (taunt, Commanding Shout, Rally's evolutions, the Unbroken Banner, rescue): above the
  top, and held a while.
Entries fade by DECAY_PER_SEC, so the opening blows don't decide a long fight on their own.
"""
import time

CLASS_MOD = {'warrior': 1.5, 'paladin': 1.3, 'thief': 0.8, 'assassin': 0.8}
IRON_WALL = 2.0          # a warrior of the Iron Wall doctrine (warrior_abilities.DOCTRINES)
PET = 3.0                # a player's creature hounds what it fights: a necromancer's servant holds it
HEAL_SHARE = 0.5         # threat per point of health healed on a foe of the creature
DECAY_PER_SEC = 0.006    # about a fifth gone in a minute of fighting


def threat_mod(ch) -> float:
    """How much a character's damage counts for (players by class, a player's creature PET)."""
    if not hasattr(ch, 'connection'):
        from .targeting import owned
        return PET if owned(ch) else 1.0
    cls = str(getattr(ch, 'char_class', '') or '').lower()
    if cls == 'warrior' and getattr(ch, 'war_doctrine', None) == 'iron_wall':
        return IRON_WALL
    return CLASS_MOD.get(cls, 1.0)


class ThreatTable:
    TAUNT_MARGIN = 1.10      # a taunt puts the taunter this far above the top

    def __init__(self):
        self._threat = {}            # character -> threat
        self.fixated_on = None
        self.fixated_until = 0.0
        self._faded_at = None

    def fade(self, now=None):
        """Decay by the time since the last fade (DECAY_PER_SEC)."""
        now = time.time() if now is None else now
        if self._faded_at is not None and now > self._faded_at:
            self.decay(min(1.0, DECAY_PER_SEC * (now - self._faded_at)))
        self._faded_at = now

    def __len__(self):
        return len(self._threat)

    def __contains__(self, ch):
        return ch in self._threat

    def add(self, ch, amount):
        if ch is None or amount <= 0:
            return
        self._threat[ch] = self._threat.get(ch, 0.0) + float(amount)

    def get(self, ch):
        return self._threat.get(ch, 0.0)

    def forget(self, ch):
        self._threat.pop(ch, None)
        if self.fixated_on is ch:
            self.fixated_on, self.fixated_until = None, 0.0

    def clear(self):
        self._threat.clear()
        self.fixated_on, self.fixated_until = None, 0.0
        self._faded_at = None

    def decay(self, share):
        """Let every entry fade by `share` (0..1), dropping those that are next to nothing."""
        keep = 1.0 - share
        for ch in list(self._threat):
            v = self._threat[ch] * keep
            if v < 0.5:
                del self._threat[ch]
            else:
                self._threat[ch] = v

    def ranked(self):
        """[(character, threat)], the most threatening first."""
        return sorted(self._threat.items(), key=lambda t: -t[1])

    def top(self, now=None):
        """The taunter while a taunt holds, else the most threatening, else None."""
        now = time.time() if now is None else now
        if self.fixated_on is not None and now < self.fixated_until:
            return self.fixated_on
        r = self.ranked()
        return r[0][0] if r else None

    def taunt(self, ch, secs, now=None):
        """The taunter goes above the top (by TAUNT_MARGIN) and holds the creature for secs."""
        now = time.time() if now is None else now
        r = self.ranked()
        top = r[0][1] if r else 0.0
        self._threat[ch] = max(self._threat.get(ch, 0.0), top * self.TAUNT_MARGIN, 1.0)
        self.fixated_on, self.fixated_until = ch, now + secs
