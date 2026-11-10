"""Who lives where (world/population, src/population.py), offline.

    python3 tests/test_population.py

The Castle of the Apocalypse II, as the owner laid it out: Kirgan the Destroyer holds the key to
the guardian's chamber; Pestilence just through the Inner Hall's door; War at the end of the
guardian chambers; Famine in the far guardian chambers (14163); Death the final boss.
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
    from player import Player
    from commands import CommandHandler as C
    from objects import create_object
    import population
    import test_atlas_engine as tae
    world = World(Config())
    await world.load()

    data = population.load()
    check(220 in data, 'the castle has its population file')
    check(population.apply(world, data) == [], 'every boss, room and door it names exists')
    where = {22100: 22100, 22070: 14151, 22071: 14158, 22072: 14163, 22073: 14153}
    names = {22100: 'Kirgan', 22070: 'Pestilence', 22071: 'War', 22072: 'Famine', 22073: 'Death'}
    for vnum, room in where.items():
        here = [m for m in world.npcs if getattr(m, 'vnum', None) == vnum]
        check(len(here) == 1 and here[0].room and here[0].room.vnum == room,
              f"{names[vnum]} is in {room} ({[m.room.vnum for m in here if m.room]})")
    resets = [r.vnum for r in world.rooms.values() for m in (r.mob_resets or []) if int(m.get('vnum', 0)) == 22071]
    check(resets == [14158], f'and spawns nowhere else ({resets})')

    # the Inner Hall's door: locked, Kirgan's key opens it
    ex = world.rooms[14150].exits['south']
    door = ex.get('door') or {}
    check(door.get('locked') and door.get('state') == 'closed' and door.get('key_vnum') == 22051,
          f"the Inner Hall's door is locked to the inner gate key ({door})")
    kirgan = world.mob_prototypes[22100]
    check('22051' in str(kirgan.get('boss_loot_table')) and "'chance': 100" in str(kirgan.get('boss_loot_table')).split('22051')[1][:20],
          'Kirgan always drops the key')
    h = Player.create_new(name='Keybearer', password=None, race='human', char_class='warrior',
                          stats={s: 13 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    h.connection = tae.Conn()
    h.room = world.rooms[14150]
    world.rooms[14150].characters.append(h)
    await C.execute(h, 'open', ['south'])
    check(door.get('state') == 'closed', 'without the key it stays shut')
    h.inventory.append(create_object(22051, world))
    await C.execute(h, 'unlock', ['south'])
    await C.execute(h, 'open', ['south'])
    check(not door.get('locked') and door.get('state') == 'open', f"with Kirgan's key it opens ({' '.join(h.connection.sent[-2:])[:120]})")

    # the wall's captain answers any watchman attacked on the wall, and goes back to his post after
    import allies
    from mobs import Mobile

    def mob_in(vnum, room=None):
        rooms = [world.rooms[room]] if room else world.rooms.values()
        return next((m for r in rooms for m in r.characters if isinstance(m, Mobile) and getattr(m, 'vnum', None) == vnum), None)
    captain = mob_in(40305, 2926)
    check(captain is not None and 'boss' in (captain.flags or ()), f'Captain Greywatch keeps the banner corner, a boss ({captain})')
    sentry = mob_in(40300)
    far = sentry is not None and captain not in [m for m, _r in allies.nearby_allies(sentry, 3, 99)]   # beyond an ordinary call
    check(sentry is not None, 'a sentry walks the wall')
    raider = Player.create_new(name='Wallraider', password=None, race='human', char_class='warrior',
                               stats={s: 13 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    raider.connection = tae.Conn()
    raider.room = sentry.room
    sentry.room.characters.append(raider)
    post = captain.room
    came = await allies.rally(sentry, raider)
    check(far and captain in came and captain.room is sentry.room and captain.fighting is raider,
          f'when a sentry is attacked the captain comes, from beyond an ordinary call ({far}), and fights')
    captain.fighting, captain.position = None, 'standing'
    await allies.return_to_post(captain)
    check(captain.room is post, 'with the fight done he goes back to the banner')
    raider.room.characters.remove(raider)

    guardian = mob_in(11057, 11010)
    check(guardian is not None and 'boss' in (guardian.flags or ()) and guardian.short_desc == 'the High Elven Guardian',
          f'the High Elven Guardian keeps the end of the fine path, a boss ({guardian})')

    # a room named for its owner has it: the guardians' chambers below Moria, a lair's beast in the
    # lair and not the tunnel beside it, the demon lord on his throne, the Sea King on his
    owners = {20581: 799650, 20588: 799651, 20578: 799652, 24858: 650507, 24899: 650506, 23513: 23508, 23506: 23504,
              16023: 796600, 14009: 796400, 14015: 796401, 7328: 795720, 15140: 799910, 15187: 799911, 24518: 797450,
              21737: 799740, 5827: 799880}
    missing = [(room, v) for room, v in owners.items() if mob_in(v, room) is None]
    check(not missing, f'every room named for its owner has it ({missing})')
    check(mob_in(650507, 24855) is None and mob_in(650506, 224824) is None, 'and Bone Gnasher and Estorgoth left the tunnel and the dead end')
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
