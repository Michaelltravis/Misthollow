"""When a creature thinks, and what thinking costs.

Phase 0 keeps the old cadence exactly (world.process_npcs): a creature that is fighting, or is in
a zone a player is in or looks into, thinks every tick; any other thinks one tick in SLEEP_EVERY,
each on its own turn (its place in world.npcs). Later phases give alert, idle and sleeping
creatures their own intervals here.

STATS counts how long the creatures' thinking takes per tick (the immortal "brainstat"), and a
tick that takes longer than SLOW_MS is logged, at most once a minute.
"""
import logging
import time

logger = logging.getLogger('Misthollow.Brain')

SLEEP_EVERY = 10
SLOW_MS = 20.0


def due(npc, index, tick, awake_zones, every=SLEEP_EVERY) -> bool:
    """Whether this creature thinks this tick (index: its place in world.npcs)."""
    if (index + tick) % every == 0:
        return True
    if getattr(npc, 'fighting', None):
        return True
    room = getattr(npc, 'room', None)
    return getattr(getattr(room, 'zone', None), 'number', None) in awake_zones


class Stats:
    def __init__(self):
        self.reset()
        self._warned = 0.0

    def reset(self):
        self.ticks = 0
        self.thought = 0
        self.ms_total = 0.0
        self.ms_max = 0.0
        self.since = time.time()

    def record(self, ms, thought):
        self.ticks += 1
        self.thought += thought
        self.ms_total += ms
        if ms > self.ms_max:
            self.ms_max = ms
        if ms > SLOW_MS:
            now = time.monotonic()
            if now - self._warned > 60:
                self._warned = now
                logger.warning(f"brain: creatures took {ms:.1f} ms of one tick ({thought} thought)")

    def lines(self) -> list:
        if not self.ticks:
            return ['No ticks counted yet.']
        return [f"{self.ticks} ticks since {time.strftime('%H:%M:%S', time.localtime(self.since))}",
                f"  {self.ms_total / self.ticks:.2f} ms a tick on average, {self.ms_max:.1f} ms at most",
                f"  {self.thought / self.ticks:.0f} creatures think in a tick on average"]


STATS = Stats()
