#!/usr/bin/env python3
"""A slept body in /play: a magical sleep lays the body down and its waking stands it up again,
whatever cast it (affects.py: the 'sleeping' flag carries the position), and the room is told of
the change on the body at once (affects._push_room), once per change it can see.

    python3 tests/test_sleep_body.py
"""
import asyncio
import os
import sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))

FAILED = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok:
        FAILED.append(what)


class FakeMap:
    def __init__(self):
        self.rooms, self.players = [], []

    async def notify_room(self, room, event=None, skip=None):
        self.rooms.append((room, skip))

    async def notify_player(self, player):
        self.players.append(player)

    def has_play(self, player):
        return True


async def main():
    from affects import AffectManager
    from spells import SpellHandler
    from map_system import _wards

    wm = FakeMap()
    room = SimpleNamespace(vnum=1, characters=[])
    mob = SimpleNamespace(name='goblin', hp=20, max_hp=20, level=3, affects=[], affect_flags=set(),
                          position='standing', fighting=None, flags=[], room=room,
                          world=SimpleNamespace(web_map=wm))
    room.characters.append(mob)

    await SpellHandler.apply_affect(mob, {'type': 'sleep', 'value': 1}, 2, 'sleep', 30, spell_key='sleep')
    check(mob.position == 'sleeping', 'Sleep lays the creature down')
    check('asleep' in _wards(mob), '...and it wears the Zzz (ward asleep)')
    await asyncio.sleep(0.2)
    check(len(wm.rooms) == 1 and wm.rooms[0] == (room, mob), '...and the room is told at once, once')

    await SpellHandler.apply_affect(mob, {'type': 'sleep', 'value': 1}, 2, 'sleep', 30, spell_key='sleep')
    check(mob.position == 'sleeping', 'cast again, it sleeps on (the refresh does not wake it)')
    await asyncio.sleep(0.2)
    check(len(wm.rooms) == 1, '...and the room hears nothing new: nothing on the body changed')

    AffectManager.apply_affect(mob, {'name': 'giant strength', 'type': AffectManager.TYPE_MODIFY_STAT,
                                     'applies_to': 'str', 'value': 1, 'duration': 5})
    await asyncio.sleep(0.2)
    check(len(wm.rooms) == 1, 'an affect that does not show on the body sends no room push')

    sleep = next(a for a in mob.affects if a.applies_to == 'sleeping')
    AffectManager.remove_affect(mob, sleep)
    check(mob.position == 'standing', 'when the sleep wears off the creature stands up')
    check('asleep' not in _wards(mob), '...without its Zzz')
    await asyncio.sleep(0.2)
    check(len(wm.rooms) == 2, '...and the room sees it get up')

    foe = SimpleNamespace(name='Hero', hp=10)
    mob.fighting = foe
    await SpellHandler.apply_affect(mob, {'type': 'sleep', 'value': 1}, 2, 'sleep', 30, spell_key='sleep')
    SpellHandler._cleanse(mob, {'sleeping'})
    check(mob.position == 'fighting', 'a sleeper cleansed mid-fight is back fighting')

    # a player who lay down to sleep is not stood up by some other spell lifting
    me = SimpleNamespace(name='Ann', hp=10, affects=[], affect_flags=set(), position='sleeping',
                         fighting=None, room=room, world=SimpleNamespace(web_map=wm), connection=object())
    AffectManager.apply_affect(me, {'name': 'armor', 'type': AffectManager.TYPE_FLAG,
                                    'applies_to': 'armour_ward', 'value': 1, 'duration': 5})
    AffectManager.remove_affect(me, me.affects[0])
    check(me.position == 'sleeping', 'a player asleep by choice sleeps on when another spell ends')
    await asyncio.sleep(0.2)
    check(me in wm.players, "...and the player's own page still hears of their affects")

    print(f"\n{'ALL OK' if not FAILED else str(len(FAILED)) + ' FAILED'}")
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
