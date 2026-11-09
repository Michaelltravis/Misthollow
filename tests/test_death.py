"""What dying costs, and where a flight may go, offline.

A player slain in a fight wakes at the temple with their pack: death's price is the exp and the
5% of their gold that Player.die() takes. They leave no corpse (one used to lie at the temple,
where die() had already moved them, holding the whole pack and a copy of their gold). A death
trap kills. Nobody flees through a shut door or into a death trap, and a save caught below 1 hp
loads at 1.

    python3 tests/test_death.py
"""
import asyncio
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
import test_webmove as tw  # noqa: E402

check, failures = tw.check, tw.failures


async def main():
    import logging
    logging.disable(logging.WARNING)
    from config import Config
    Config.PLAYER_DIR = tempfile.mkdtemp()
    from world import World
    from bosses import create_mob_from_prototype
    from player import Player
    from combat import CombatHandler
    from commands import CommandHandler
    from objects import Object
    import test_atlas_engine as tae
    world = World(Config())
    await world.load()

    def hero_at(name, vnum):
        h = Player.create_new(name=name, password=None, race='human', char_class='warrior',
                              stats={s: 13 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
        h.connection = tae.Conn()
        h.room = world.rooms[vnum]
        h.room.characters.append(h)
        world.players[name.lower()] = h
        return h

    def thing(name):
        o = Object(0, world)
        o.name = o.short_desc = name
        return o

    # ---- slain in a fight, away from the temple
    temple = world.rooms[3001]
    fight_room = next(r for r in world.rooms.values() if r.zone is temple.zone and r is not temple
                      and not ({'peaceful', 'deathtrap', 'death'} & set(r.flags)))
    hero = hero_at('Deathtest', fight_room.vnum)
    hero.inventory.extend(thing(n) for n in ('a test sword', 'a test loaf', 'a test key'))
    carried = len(hero.inventory)
    hero.gold = 1000
    proto = next(p for p in world.mob_prototypes.values() if not p.get('boss_config') and not p.get('shop_config'))
    mob = create_mob_from_prototype(dict(proto), world)
    mob.room = fight_room
    fight_room.characters.append(mob)
    corpses_before = [o for o in temple.items if 'corpse of Deathtest' in getattr(o, 'name', '')]
    hero.hp = 0
    await hero.die(mob)
    await CombatHandler.handle_death(mob, hero)
    check(hero.room is temple, 'the slain wake at the temple')
    check(len(hero.inventory) == carried, f'with their pack ({len(hero.inventory)} of {carried} things)')
    check(hero.gold == 950, f'less 5% of their gold ({hero.gold} of 1000)')
    check(hero.hp >= 1 and hero.position == 'standing', 'alive and on their feet')
    corpses = [o for r in (temple, fight_room) for o in r.items if 'corpse of Deathtest' in getattr(o, 'name', '')]
    check(len(corpses) == len(corpses_before), 'and leave no corpse holding a copy of it all')

    # ---- a death trap kills
    trap = next((r for r in world.rooms.values() if ({'deathtrap', 'death'} & set(r.flags))
                 and any(e and e.get('room') for e in r.exits.values())), None)
    if trap:
        side, way = next(((r, d) for r in world.rooms.values() for d, e in r.exits.items()
                          if e and e.get('room') is trap and not e.get('door')), (None, None))
    if trap and side:
        faller = hero_at('Trapfall', side.vnum)
        faller.dex = -100               # no last-second save
        faller.gold = 1000
        deaths = getattr(faller, 'deaths', 0) or 0
        await CommandHandler.cmd_move(faller, way)
        check(faller.room is not trap and faller.room is faller.recall_room(), 'a death trap kills: its victim wakes at the temple')
        check((getattr(faller, 'deaths', 0) or 0) == deaths + 1, 'and the death is counted')
        check(faller.gold == 950, f'for the usual price, not all their gold ({faller.gold} of 1000)')

        # ---- nobody flees into one
        check(not CombatHandler._may_take(faller, {'room': trap}), 'no flight into a death trap')
    else:
        check(False, 'a death trap with an open way in, to test with')
    open_room = fight_room
    check(CombatHandler._may_take(hero, {'room': open_room}), 'an open way may be fled through')
    check(not CombatHandler._may_take(hero, {'room': open_room, 'door': {'name': 'door', 'state': 'closed'}}), 'a shut door may not')
    check(CombatHandler._may_take(hero, {'room': open_room, 'door': {'name': 'door', 'state': 'open'}}), 'an open door may')
    check(CombatHandler._may_take(hero, {'room': open_room, 'door': {'name': 'door', 'state': 'closed', 'broken': True}}), 'nor does a broken one stop anyone')

    # ---- a save caught mid-death
    hero.hp = -7
    await hero.save()
    again = Player.load('Deathtest', world) if hasattr(Player, 'load') else None
    if asyncio.iscoroutine(again):
        again = await again
    check(again is not None and again.hp >= 1, f'a save below 1 hp loads at 1 ({getattr(again, "hp", None)})')

    print('ALL OK' if not failures else f'{len(failures)} FAILED')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
