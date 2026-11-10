#!/usr/bin/env python3
"""What creatures are called in play (mobs.Mobile.said_name): a name written as keywords ("ogre
wandering brute giant", the build-out's way) is said as the description ("a wandering ogre") in chat,
combat lines and corpses; the words stay its keywords for targeting, reputation and the 3D body.

    python3 tests/test_mob_names.py
"""
import asyncio
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))

FAILED = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok:
        FAILED.append(what)


async def main():
    import logging
    logging.disable(logging.WARNING)
    from mobs import Mobile
    said = Mobile.said_name
    check(said('ogre wandering brute giant', 'a wandering ogre') == 'a wandering ogre', 'a keyword list is said as its description')
    check(said('gorak drillmaster sergeant master', 'Gorak the Drillmaster') == 'Gorak the Drillmaster', 'a named creature by its name')
    check(said('rat', 'the sewer rat') == 'the sewer rat', 'a one-word name is said as its fuller description')
    check(said('dragon', 'the baby dragon') == 'the baby dragon', '"dragon" is "the baby dragon" in the log, as on its nameplate')
    check(said('rat', 'the rat') is None and said('rat', 'a rat') is None, 'a description that only adds an article changes nothing')
    check(said('grimtooth', 'the weaponsmith') is None, 'a one-word name its description does not hold stays (a proper name)')
    check(said('wyvern hatchling', 'a wyvern hatchling') is None, 'a name that is already the description stays')
    check(said('giant spider', 'A giant spider lurks here.') is None, 'a room sentence is no name')

    from config import Config
    from world import World
    from factions import FactionManager
    from player import Player
    from map_system import _kw
    world = World(Config())
    await world.load()
    ghouls = [m for m in world.npcs if getattr(m, 'keyword_name', '') == 'ghoul rotting orc']
    check(bool(ghouls), "Morkai's rotting orc ghouls are in the world")
    if ghouls:
        g = ghouls[0]
        check(g.name == g.short_desc and 'ghoul rotting orc' not in g.name, f'and are called by their description ({g.name!r})')
        check(all(w in g.keywords for w in ('ghoul', 'rotting', 'orc')), 'their keywords stay')
        check(Player.matches_character(None, g, 'ghoul') and Player.matches_character(None, g, 'orc'), '"kill ghoul" and "kill orc" still find one')
        check('orc' in FactionManager.kill_words(g), 'killing one still counts as killing an orc')
        check(_kw(g) == 'ghoul rotting orc', 'the 3D client is sent the keywords for its body')
    plain = [m for m in world.npcs if getattr(m, 'keyword_name', None) == m.name]
    check(bool(plain) and _kw(plain[0]) is None, 'a creature whose name reads already sends no keywords')
    print(f"\n{'ALL OK' if not FAILED else f'{len(FAILED)} FAILED'}")
    sys.exit(1 if FAILED else 0)


if __name__ == '__main__':
    asyncio.run(main())
