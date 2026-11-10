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

    # ---- a pupil who set the lessons down is taken back (quests.resume_tutorial)
    from quests import QuestManager
    pupil = hero_at('Pupiltest', 3001)
    check(QuestManager.next_tutorial(pupil) == 'tutorial_1_awakening', 'a newcomer starts at the first lesson')
    pupil.quests_completed = ['tutorial_1_awakening', 'tutorial_2_look_around', 'tutorial_3_know_thyself']
    pupil.active_quests = []
    check(QuestManager.next_tutorial(pupil) == 'tutorial_5_combat', 'the next is the first undone (the merged fourth is skipped)')
    check(await QuestManager.resume_tutorial(pupil) and QuestManager.has_active_quest(pupil, 'tutorial_5_combat'), 'Aldric gives it to one with none in hand')
    check(not await QuestManager.resume_tutorial(pupil), 'not a second while one is in hand')
    pupil.active_quests = []
    pupil.level = 12
    check(not await QuestManager.resume_tutorial(pupil), 'nor to one past level 10')

    # ---- catching your breath between fights (Player.catch_breath)
    rest = hero_at('Resttest', 3001)
    rest.max_hp, rest.hp = 100, 20
    rest.fighting = None
    rest.position = 'standing'
    check(rest.catch_breath() == 0, 'the first calm tick gives nothing yet')
    check(rest.catch_breath() == 5 and rest.hp == 25, 'from the second, a twentieth of their health a tick')
    rest.fighting = mob
    check(rest.catch_breath() == 0 and rest.hp == 25, 'not in a fight')
    rest.fighting = None
    check(rest.catch_breath() == 0, 'and the calm is counted afresh after one')
    rest.hp = 99
    rest.catch_breath()
    check(rest.hp == 100, 'never past full')

    # ---- newcomers: loot picked up, and running at a fifth of their health until they choose
    new = hero_at('Newtest', 3001)
    check(new.autoloot is True, 'a new hero picks up what their kills carried')
    new.max_hp, new.level = 40, 1
    check(new.wimpy_now() == 8, f'a newcomer runs at a fifth of their health ({new.wimpy_now()})')
    new.level = 6
    check(new.wimpy_now() == 0, 'past level 5 only if they set it')
    new.level = 2
    await CommandHandler.cmd_wimpy(new, ['0'])
    check(new.wimpy_set and new.wimpy_now() == 0, '`wimpy 0` turns it off, for good')
    await CommandHandler.cmd_wimpy(new, ['12'])
    check(new.wimpy_now() == 12, 'and their own number is kept')

    # ---- waking where you left, unless you left it dying
    wild = fight_room
    low = hero_at('Lowtest', wild.vnum)
    low.max_hp, low.hp, low.room_vnum = 100, 20, wild.vnum
    check(world.login_room(low) is low.recall_room(), 'under three tenths of their health in a wild room: they wake at the temple')
    low.hp = 60
    check(world.login_room(low) is wild, 'hale, they wake where they left')
    low.hp, low.room_vnum = 5, 3001
    check(world.login_room(low) is world.rooms[3001], 'a peaceful room is safe to wake in, however hurt')

    # ---- the first ten levels' creatures carry less health (Mobile.early_health)
    from mobs import Mobile
    check(abs(Mobile.early_health(1) - 0.6) < 1e-9 and Mobile.early_health(10) == 1.0 and Mobile.early_health(40) == 1.0, 'six tenths at level 1, the whole from level 10')
    check(0.7 < Mobile.early_health(4) < 0.76, f'a level-4 creature about three quarters ({Mobile.early_health(4):.2f})')
    check(Mobile.early_health(3, {'boss_config': {}}) == 1.0 and Mobile.early_health(3, {'rank': 'elite'}) == 1.0, 'bosses and elites keep theirs')
    dragon = create_mob_from_prototype(dict(world.mob_prototypes[18603]), world)
    check(50 <= dragon.max_hp <= 70, f'the baby dragon (level 4, 86 by its dice) has about 63 ({dragon.max_hp})')

    print('ALL OK' if not failures else f'{len(failures)} FAILED')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
