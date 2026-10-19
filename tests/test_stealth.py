#!/usr/bin/env python3
"""Cover Tracks (docs/STEALTH.md, stealth.py): a thief's or an assassin's way of leaving no trail.

    python3 tests/test_stealth.py
"""
import asyncio
import logging
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))

FAILED = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok:
        FAILED.append(what)


async def main():
    logging.disable(logging.WARNING)
    from config import Config
    from world import World
    from player import Player
    from commands import CommandHandler
    from bosses import create_mob_from_prototype
    import mastery, map_system, reach, stealth
    world = World(Config())
    await world.load()
    check(mastery.unlock_level('thief', 'cover_tracks') == 7 and mastery.unlock_level('assassin', 'cover_tracks') == 7,
          'thieves and assassins learn Cover Tracks at level 7')
    check(any(e['id'] == 'cover_tracks' for e in mastery.book('thief')), "it is in the thief's spellbook (and on the bar in /play)")

    heard = []

    async def hear(m, *a, **k):
        heard.append(m)
    here = world.rooms[3001]
    thief = Player.create_new(name='Sly', password=None, race='human', char_class='thief',
                              stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    thief.world, thief.room, thief.level, thief.send = world, here, 20, hear
    thief.skills['cover_tracks'] = 80
    here.characters.append(thief)
    # a hunter with a grudge, two rooms off
    away = next(r for r in world.rooms.values() if r is not here and r.zone is here.zone and not r.characters)
    hunter = create_mob_from_prototype(next(iter(world.mob_prototypes.values())), world)
    hunter.flags = set(f for f in (hunter.flags or ()) if f not in ('sentinel', 'boss')) | {'hunter'}
    hunter.special, hunter.owner, hunter.fighting, hunter.level = None, None, None, 10
    hunter.room = away
    away.characters.append(hunter)
    world.npcs.append(hunter)
    hunter.add_grudge(thief, 10)
    check(thief.name in hunter.grudge_list, 'a hunter holds a grudge against the thief')
    was = random.random, random.randint
    random.random, random.randint = (lambda: 0.0), (lambda a, b: a)
    try:
        await CommandHandler.execute(thief, 'cover', ['tracks'])
    finally:
        random.random, random.randint = was
    check(stealth.covered(thief), f"'cover tracks' sweeps the trail ({heard[-1][:60] if heard else ''})")
    check(thief.name not in hunter.grudge_list and hunter.hunting_target is not thief,
          'the hunter out of sight loses the trail at once')
    check('tracks_covered' in map_system._wards(thief), '/play is told (no footprints, a faint dust at the feet)')
    n = len(heard)
    await CommandHandler.execute(thief, 'cover_tracks', [])
    check(len(heard) > n and 'wait' in heard[-1], 'not again at once (a cooldown)')
    # a hunter that picks the trail up again loses it as it goes
    hunter.add_grudge(thief, 10)
    random.random = lambda: 0.0
    try:
        await hunter.hunting_ai()
    finally:
        random.random = was[0]
    check(thief.name not in hunter.grudge_list, 'a hunter on a covered trail loses it as it hunts')
    # fled from: left alone twice as long
    reach.lost(hunter, thief, 30)
    left = hunter.lost_quarry[thief.name] - time.time()
    check(55 < left <= 60, f'a creature fled from leaves the covered hero alone twice as long ({left:.0f}s)')
    # not mid-fight
    thief.cover_tracks_cooldown = 0
    thief.fighting = hunter
    n = len(heard)
    await stealth.cover_tracks(thief)
    check('steel' in heard[-1], 'no sweeping a trail mid-fight')
    thief.fighting = None
    away.characters.remove(hunter)
    world.npcs.remove(hunter)
    here.characters.remove(thief)
    print(f"\n{'ALL OK' if not FAILED else f'{len(FAILED)} FAILED'}")
    sys.exit(1 if FAILED else 0)


if __name__ == '__main__':
    asyncio.run(main())
