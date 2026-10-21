"""Mounts carry you faster (Push 34), offline.

    python3 tests/test_mounts.py
"""
import asyncio
import os
import random
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
    from commands import CommandHandler
    from mounts import MountManager, MOUNT_TEMPLATES, travel_speed, TRAVEL_CAP, BOSS_MOUNTS, boss_mount_drop
    from factions import FACTIONS
    from map_system import build_map_payload
    from bosses import create_mob_from_prototype
    import test_atlas_engine as tae
    world = World(Config())
    await world.load()

    def hero(name, at=3001):
        h = Player.create_new(name=name, password=None, race='human', char_class='warrior',
                              stats={s: 13 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
        h.connection = tae.Conn()
        h.room = world.rooms[at]
        world.rooms[at].characters.append(h)
        world.players[name.lower()] = h
        h.max_move = h.move = 500
        return h

    # ---- how fast you go
    h = hero('Rider')
    check(travel_speed(h) == 1.0, 'on foot you go at walking pace')
    h.mount = MountManager.create_mount('horse')
    check(abs(travel_speed(h) - 1.35) < 0.01, f'a horse carries you 35% faster ({travel_speed(h)})')
    h.mount = MountManager.create_mount('griffin')
    check(abs(travel_speed(h) - 1.6) < 0.01, f'a griffin 60% ({travel_speed(h)})')
    h.mount.loyalty = 0
    check(abs(travel_speed(h) - 1.3) < 0.01, f'a neglected mount half as much ({travel_speed(h)})')
    h.mount.loyalty = 100
    h.affect_flags.add('haste')
    h.equipment['feet'] = __import__('legendary').create_legendary(99008, world)      # threshold walkers
    check(travel_speed(h) == round(1 + TRAVEL_CAP, 3), f'never more than +80% ({travel_speed(h)})')
    h.affect_flags.discard('haste')
    del h.equipment['feet']
    h.explored_rooms = {h.room.vnum}
    payload = build_map_payload(h)
    sp = (payload.get('player') or {}).get('speed')
    check(sp and abs(sp - travel_speed(h)) < 1e-6, f'the map payload says how fast the hero goes ({sp})')

    # ---- every mount a faction gives exists, and every template has a speed
    missing = [m for f in FACTIONS.values() for m in (f.exalted_rewards or {}).get('mounts', []) if m not in MOUNT_TEMPLATES]
    check(not missing, f'every faction mount exists ({missing})')
    check(all(MountManager.create_mount(k).travel > 0 for k in MOUNT_TEMPLATES), 'every mount has a travel speed')

    # ---- what moving costs
    h.mount = MountManager.create_mount('horse')
    target = next(world.rooms[ex['to_room']] for ex in h.room.exits.values() if isinstance(ex, dict) and ex.get('to_room') in world.rooms)
    on_foot = Player.create_new(name='Walker', password=None, race='human', char_class='warrior',
                                stats={s: 13 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    on_foot.room = h.room
    walk = sum(CommandHandler._calculate_move_cost(on_foot, target) for _ in range(10))
    ride = sum(CommandHandler._calculate_move_cost(h, target) for _ in range(10))
    check(ride <= walk // 2 + 1 and ride < walk, f'riding halves what moving costs, even on easy ground ({walk} on foot, {ride} riding)')

    # ---- loyalty
    h.mount.loyalty = 100
    for _ in range(10):
        await h.regen_tick()
    check(h.mount.loyalty == 95, f'a ridden mount grows hungry, a point every other minute ({h.mount.loyalty})')
    h.gold = 100
    await CommandHandler.cmd_feed(h, [])
    check(h.mount.loyalty == 100, 'feeding restores it')

    # ---- ride: a speedwalk
    check(CommandHandler.ride_steps(['n', 'n', '3e']) == ['north', 'north', 'east', 'east', 'east'], 'ride n n 3e')
    check(CommandHandler.ride_steps(['nnee']) == ['north', 'north', 'east', 'east'], 'ride nnee')
    check(len(CommandHandler.ride_steps(['20n'])) == 10, 'at most ten steps')
    # find a straight line of three open rooms to ride
    def line(v, d, n):
        out = [v]
        for _ in range(n):
            ex = world.rooms[out[-1]].exits.get(d)
            to = ex.get('to_room') if isinstance(ex, dict) else None
            if to not in world.rooms or (isinstance(ex.get('door'), dict)):
                return None
            out.append(to)
        return out
    start = next(((v, d) for v in world.rooms for d in ('north', 'east') if line(v, d, 3)
                  and all(not any('aggressive' in (getattr(m, 'flags', None) or ()) for m in world.rooms[x].characters) for x in line(v, d, 3))
                  and world.rooms[v].sector_type not in ('water_swim', 'water_noswim', 'underwater')
                  and all(world.rooms[x].sector_type not in ('water_swim', 'water_noswim', 'underwater') for x in line(v, d, 3))
                  and world.rooms[v].admits(h)), None)
    if start:
        v, d = start
        path = line(v, d, 3)
        h.room.characters.remove(h)
        h.room = world.rooms[v]
        h.room.characters.append(h)
        h.fighting = None
        h.position = 'standing'
        await CommandHandler.cmd_ride(h, [d[0] * 3])
        check(h.room.vnum == path[-1], f'ride {d[0] * 3} rides three rooms ({v} -> {h.room.vnum}, want {path[-1]})')
    h.mount = None
    await CommandHandler.cmd_ride(h, ['n'])
    check('mounted' in ' '.join(h.connection.sent[-1:]), 'riding needs a mount')

    # ---- a boss's mount
    boss_v, (key, _) = next(iter(BOSS_MOUNTS.items()))
    if boss_v in world.mob_prototypes:
        boss = create_mob_from_prototype(dict(world.mob_prototypes[boss_v]), world)
        real = random.randint
        random.randint = lambda a, b: a
        try:
            won = await boss_mount_drop(h, boss)
        finally:
            random.randint = real
        check(won == key and MountManager.get_owned_mount_data(h, key), f'beating the boss can win its {key}')
        again = await boss_mount_drop(h, boss)
        check(again is None, 'but only once')
    # ---- a one-time gift (world/grants.json), and givemount
    import grants
    g = hero('Gifted')
    gifts = {'gifted': {'mounts': ['griffin', 'horse', 'no_such_beast'], 'ride': 'griffin'}}
    lines = grants.apply_grants(g, gifts)
    check(MountManager.get_owned_mount_data(g, 'griffin') and MountManager.get_owned_mount_data(g, 'horse')
          and g.mount and g.mount.key == 'griffin', f'a gift gives its mounts and puts them on one ({lines})')
    check(not any('no_such_beast' in l for l in lines), 'an unknown mount is skipped')
    again = grants.apply_grants(g, gifts)
    check(again == [] and len(g.owned_mounts) == 2, 'and is given only once')
    check('xtc' in grants.load_grants() and 'griffin' in grants.load_grants()['xtc']['mounts'], 'XTC has a griffin waiting')
    xtc = grants.load_grants()['xtc']
    check(xtc.get('explore_all') and xtc.get('waypoints_all'), 'and the whole map')
    m = hero('Mapper')
    from travel import WAYPOINTS
    lines = grants.apply_grants(m, {'mapper': {'explore_all': True, 'waypoints_all': True}})
    open_rooms = {r.vnum for r in world.rooms.values() if 'imm_only' not in (r.flags or ()) and not getattr(r.zone, 'sealed', False)}
    check(open_rooms <= m.explored_rooms and not any('imm_only' in (world.rooms[v].flags or ()) for v in m.explored_rooms),
          f'a map gift charts every open room, not the God Rooms ({len(m.explored_rooms)})')
    check(set(WAYPOINTS) <= m.discovered_waypoints, 'and every waypoint')
    check(grants.apply_grants(m, {'mapper': {'explore_all': True, 'waypoints_all': True}}) == [], 'once')
    g2 = hero('Placed')
    grants.apply_grants(g2, {'placed': {'room': 14804}})
    check(g2.room_vnum == 14804, 'a gift can set where they wake (XTC: the way down into the Tunnel of Sticks)')
    check(grants.load_grants()['xtc'].get('room') == 14804, "XTC's gift wakes them at 14804")
    check(grants.load_grants()['xtc'].get('gearup') is True, "and kits them out for the endgame")
    k = hero('Kitted')
    k.level = 5
    grants.apply_grants(k, {'kitted': {'gearup': True}})
    world.players.pop('kitted', None)
    await world.add_player(k)
    from prestige import get_max_level
    check(k.level == get_max_level(k) and getattr(k.equipment.get('wield'), 'rarity', '') == 'legendary' and k.mount,
          f'a gearup gift levels, gears and mounts them on entering the world (level {k.level})')
    # ---- given part by part: an edit gives only what's new (never re-mounts you)
    pp = hero('Parts')
    grants.apply_grants(pp, {'parts': {'mounts': ['griffin'], 'ride': 'griffin'}})
    await CommandHandler.cmd_dismount(pp, [])
    lines = grants.apply_grants(pp, {'parts': {'mounts': ['griffin'], 'ride': 'griffin', 'gold': 7}})
    check(pp.mount is None and lines == ['You are given 7 gold.'], f'adding gold to a gift gives the gold, and leaves them on foot ({lines})')
    old = hero('Oldgift')
    gift = {'mounts': ['horse'], 'ride': 'horse'}
    old.grants_received = [grants.grant_key('Oldgift', gift)]
    check(grants.apply_grants(old, {'oldgift': gift}) == [] and old.mount is None, 'a gift given whole before is had in every part')
    check(grants.apply_grants(old, {'oldgift': dict(gift, gold=5)}) == ['You are given 5 gold.'], 'and only a new part is given after')
    xg = grants.load_grants()['xtc']
    xr = hero('Xtc')
    xr.grants_received = [grants.grant_key('Xtc', xg)]
    check(grants.apply_grants(xr) == [] and xr.mount is None, "XTC's gift, had whole, gives nothing more (no griffin again)")

    # ---- an immortal gift makes the account it names an admin one (accounts.py: every character
    # has an account; the gift makes none)
    from accounts import Account
    import accounts
    real_dir = accounts.ACCOUNTS_DIR
    accounts.ACCOUNTS_DIR = tempfile.mkdtemp()
    try:
        check(grants.load_grants()['deckard'].get('immortal') is True, "Deckard's gift was given as true (before the account rule)")
        dk = hero('Deckard')
        dk.password_hash = 'x$hash'
        check(grants.apply_grants(dk, entering=True) == [] and not dk.is_immortal and not os.listdir(accounts.ACCOUNTS_DIR),
              'a true immortal gift now gives nothing, and makes no account')
        gift = {'deckard': {'immortal': 'deckard'}}
        dk.grants_received = []
        dk.account_name = 'deckard'
        a = Account('deckard'); a.characters = ['Deckard']; a.save()
        check(grants.apply_grants(dk, gift) == [] and not dk.is_immortal, 'not while logging in (only on entering the world)')
        lines = grants.apply_grants(dk, gift, entering=True)
        check(Account.load('deckard').is_admin and dk.is_immortal and any('immortal' in l for l in lines),
              f'a character on the account its gift names makes that account an admin one ({lines})')
        check(grants.apply_grants(dk, gift, entering=True) == [], 'once')
        other = hero('Deckard2')
        other.name = 'Deckard'
        other.grants_received = []
        other.account_name = 'squat'
        a2 = Account('squat'); a2.characters = ['Deckard']; a2.save()
        check(grants.apply_grants(other, gift, entering=True) == [] and not Account.load('squat').is_admin,
              "a Deckard on another account (the name taken by someone else) is never made immortal")
    finally:
        accounts.ACCOUNTS_DIR = real_dir

    # ---- mount last: R in /play
    r = hero('Rlast')
    await CommandHandler.cmd_mount(r, ['last'])
    check(r.mount is None and 'own any mounts' in ' '.join(r.connection.sent[-1:]), 'owning none, mount last says so')
    r.owned_mounts = [{'key': 'horse', 'loyalty': 100}, {'key': 'griffin', 'loyalty': 100}]
    await CommandHandler.cmd_mount(r, ['last'])
    check(r.mount and r.mount.key == 'griffin', 'never ridden: mount last takes the fastest')
    await CommandHandler.cmd_dismount(r, [])
    await CommandHandler.cmd_mount(r, ['horse'])
    await CommandHandler.cmd_dismount(r, [])
    check(r.mount is None and r.last_mount == 'horse', 'dismount gets you down, and it remembers the horse')
    await CommandHandler.cmd_mount(r, ['last'])
    check(r.mount and r.mount.key == 'horse', 'mount last: back on the horse')
    # attacked on horseback: down off the mount, and nothing raised (this took the server down)
    from combat import CombatHandler
    from bosses import create_mob_from_prototype
    await CommandHandler.cmd_mount(r, ['griffin'] if r.mount is None else [])
    if r.mount is None:
        await CommandHandler.cmd_mount(r, ['horse'])
    rider_mount = r.mount
    gob = create_mob_from_prototype(dict(world.mob_prototypes[3501]), world)
    gob.room = r.room
    r.room.characters.append(gob)
    world.npcs.append(gob)
    try:
        await CombatHandler.start_combat(gob, r)
        raised = None
    except Exception as e:
        raised = e
    check(raised is None and rider_mount is not None and (r.mount is None or r.mount.combat_ok),
          f"attacked on horseback: off the horse, nothing raised ({raised!r})")
    r.fighting = None; r.position = 'standing'
    gob.fighting = None
    r.room.characters.remove(gob)
    world.npcs.remove(gob)
    await CommandHandler.cmd_mount(r, ['horse']) if r.mount is None else None
    # R sends `mount toggle`: the server, not the page's copy of the state, decides up or down
    await CommandHandler.cmd_mount(r, ['toggle'])
    check(r.mount is None, 'mount toggle while riding: down')
    await CommandHandler.cmd_mount(r, ['toggle'])
    check(r.mount and r.mount.key == 'horse', 'mount toggle on foot: up on the last ridden')
    await r.save()
    check(Player.load('Rlast').last_mount == 'horse', 'the save keeps the mount last ridden')
    r.explored_rooms = {r.room.vnum}
    pl = build_map_payload(r).get('player') or {}
    check(sorted(m['key'] for m in pl.get('mounts', [])) == ['griffin', 'horse'] and pl.get('mount', {}).get('key') == 'horse',
          f"the payload lists the mounts owned and the one ridden ({pl.get('mounts')})")

    imm = hero('Imm')
    real = Player.is_immortal
    Player.is_immortal = property(lambda self: True)
    try:
        await CommandHandler.cmd_givemount(imm, ['rider', 'nightmare'])
    finally:
        Player.is_immortal = real
    check(h.mount and h.mount.key == 'nightmare' and MountManager.get_owned_mount_data(h, 'nightmare'), 'givemount gives and mounts')
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
