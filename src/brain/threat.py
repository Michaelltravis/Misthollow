"""A creature's threat table: who it means to kill, and how badly.

Damage, healing of its foes and taunts raise a name; time and distance let it fade. A taunt also
FIXATES: for a few seconds the taunter is the target whatever the numbers say. Entries are kept by
the character itself (a name is not unique between a player and a creature), and forgotten when
the character dies or leaves the fight.

Phase 0 keeps the table and shows it (the immortal "brain" command); nothing reads it to choose
a target yet (features.threat, phase 1a).
"""
import time


class ThreatTable:
    TAUNT_MARGIN = 1.10      # a taunt puts the taunter this far above the top

    def __init__(self):
        self._threat = {}            # character -> threat
        self.fixated_on = None
        self.fixated_until = 0.0

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
