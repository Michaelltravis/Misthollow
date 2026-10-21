"""The deep and the dark, offline (zone_hazards.py): under the Sunken Temple's water a hero holds
their breath, an air pocket fills the lungs, and once the air is gone the water drowns them; the
Pressure Chamber crushes. Water breathing gear (the Pearl, the Coral Plate) answers both. In the
Shadowspire Citadel each room deepens the shadow corruption, the torchlit halls ease it, at 75%
the hero's shadow peels away and attacks, and leaving sheds it; the Amulet of Light answers it.
A worn instrument's song power makes a bard's songs stronger.

    python3 tests/test_zone_hazards.py
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import test_webmove as tw  # noqa: E402  (check(), failures)

check, failures = tw.check, tw.failures


class Said:
    def __init__(self):
        self.sent = []

    async def send(self, message='', newline=True):
        self.sent.append(str(message))

    async def send_prompt(self):
        pass


async def main():
    logging.disable(logging.WARNING)
    from config import Config
    from world import World
    from objects import Object
    from player import Player
    from mobs import Mobile
    import zone_hazards as zh
    from map_system import _gear_wards
    world = World(Config())
    await world.load()

    def obj(vnum):
        return Object.from_prototype(world.obj_prototypes[vnum], world)

    def hero(name, cls='warrior'):
        h = Player.create_new(name=name, password=None, race='human', char_class=cls,
                              stats={s: 13 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
        h.connection = Said()
        h.set_base('max_hp', 100000)
        h.hp = h.max_hp
        world.players[name.lower()] = h
        return h

    async def enter(h, vnum):
        if h.room and h in h.room.characters:
            h.room.characters.remove(h)
        h.room = world.rooms[vnum]
        h.room.characters.append(h)
        await zh.on_enter(h, h.room)

    async def ticks(h, n):
        for _ in range(n):
            h._breath_at = 0      # a tick's worth of time has passed
            await zh.tick(world)

    said = lambda h, k=6: ' '.join(h.connection.sent[-k:])

    # the zones' own data reaches the rooms
    check((world.rooms[24000].zone_mechanic or {}).get('type') == 'drowning_timer', 'the Submerged Archway states the drowning rule')
    check((world.rooms[24002].zone_mechanic or {}).get('type') == 'air_pocket', 'the Coral Garden is an air pocket')
    check((world.rooms[24500].zone_mechanic or {}).get('type') == 'shadow_corruption', "the Citadel's gates state its corruption")

    # ---- the deep
    diver = hero('Diver')
    await enter(diver, 24001)
    check(diver._breath == zh.AIR_TICKS and 'deep breath' in said(diver), f'going under, a hero holds their breath ({diver._breath})')
    await ticks(diver, zh.AIR_TICKS)
    check(diver._breath == 0 and diver.hp == diver.max_hp, f'the air runs out over a minute, without harm ({diver._breath}, {diver.max_hp - diver.hp})')
    await ticks(diver, 1)
    check(diver.max_hp - diver.hp == 25 and 'lungs burn' in said(diver), f'then the water drowns: 25 a tick in the Temple ({diver.max_hp - diver.hp})')
    await enter(diver, 24002)
    check(diver._breath == zh.AIR_TICKS and 'gulp' in said(diver), 'an air pocket fills the lungs again')
    await enter(diver, 24001)
    hp = diver.hp
    await enter(diver, 24007)
    await ticks(diver, 1)
    check(hp - diver.hp == 40, f'the Pressure Chamber crushes: 40 a tick ({hp - diver.hp})')
    await enter(diver, 6808)
    check(diver._breath is None and 'surface' in said(diver), 'climbing out, the hero breathes again')

    pearl = hero('Pearldiver')
    pearl.equipment = {'hold': obj(24003)}            # the Pearl of Water Breathing
    await enter(pearl, 24007)
    await ticks(pearl, zh.AIR_TICKS + 3)
    check(pearl.hp == pearl.max_hp and getattr(pearl, '_breath', None) is None,
          f'the Pearl of Water Breathing: no drowning, no crushing ({pearl.max_hp - pearl.hp})')
    pearl.equipment = {'body': obj(24002)}            # Coral Plate
    check(zh.breathes_water(pearl) and 'breathes water' in _gear_wards(pearl), 'Coral Plate breathes water too, and score says so')

    reliquary = hero('Reliquary')
    await enter(reliquary, 28501)
    await ticks(reliquary, zh.AIR_TICKS + 1)
    check(reliquary.max_hp - reliquary.hp == 30, f'the Drowned Reliquary drowns at its own 30 ({reliquary.max_hp - reliquary.hp})')
    pockets = [v for v, r in world.rooms.items() if r.zone and r.zone.number == 285 and (r.zone_mechanic or {}).get('type') == 'air_pocket']
    check(len(pockets) >= 4, f'the Reliquary has air pockets along the way ({sorted(pockets)})')
    for h in (diver, pearl, reliquary):
        h.room.characters.remove(h)

    # ---- the dark
    seeker = hero('Seeker')
    await enter(seeker, 24500)
    check(seeker._corruption == 5 and 'Shadow corruption: 5%' in said(seeker), f'each room of the Citadel adds 5% ({seeker._corruption})')
    await enter(seeker, 24501)
    await enter(seeker, 24502)                        # torchlit: eases 10
    check(seeker._corruption == 0 and 'torchlight' in said(seeker), f'a torchlit hall eases it ({seeker._corruption})')
    await enter(seeker, 24514)
    check(seeker._corruption == 25, f'the Corruption Chamber adds 25 ({seeker._corruption})')
    seeker._corruption = 70
    npcs = len(world.npcs)
    await enter(seeker, 24513 if 24513 in world.rooms else 24501)
    shadow = world.npcs[-1] if len(world.npcs) > npcs else None
    check(shadow is not None and isinstance(shadow, Mobile) and shadow.room is seeker.room and "Seeker's shadow" in shadow.short_desc,
          f"at 75% the hero's shadow peels away ({getattr(shadow, 'short_desc', None)})")
    check(seeker._corruption == 37 and 'peels away' in said(seeker), f'and takes half the corruption with it ({seeker._corruption})')
    await enter(seeker, 6711)
    check(seeker._corruption == 0, 'leaving the Citadel sheds it')
    check(shadow is not None and shadow not in world.npcs and shadow not in shadow.room.characters,
          "and the hero's shadow fades with it")

    warded = hero('Warded')
    warded.equipment = {'neck1': obj(24503)}          # the Amulet of Light
    await enter(warded, 24500)
    await enter(warded, 24514)
    check(getattr(warded, '_corruption', 0) == 0 and 'corruption immune' in _gear_wards(warded),
          'the Amulet of Light: no corruption, and score says so')
    for h in (seeker, warded):
        h.room.characters.remove(h)

    # ---- the Foundry's steam and levers
    from commands import CommandHandler as C
    stoker = hero('Stoker')
    await enter(stoker, 24803)                        # Steam Tunnel Alpha: on
    check('Steam roars' in said(stoker), 'a live steam tunnel warns as you enter')
    await ticks(stoker, 0)
    stoker._steam_at = 0
    await zh.tick(world)
    check(stoker.max_hp - stoker.hp == 35, f'and scalds: 35 a tick ({stoker.max_hp - stoker.hp})')
    await enter(stoker, 24810)                        # Beta: off until alpha is pulled
    stoker.hp = stoker.max_hp; stoker._steam_at = 0
    await zh.tick(world)
    check(stoker.hp == stoker.max_hp and 'cold' in said(stoker), 'Steam Tunnel Beta is cold at first')
    await enter(stoker, 24806)
    check('pull lever' in said(stoker), 'a lever room says what to do')
    await C.cmd_pull(stoker, ['lever'])
    check(not zh.steam_on(world.rooms[24803]) and zh.steam_on(world.rooms[24810]),
          'pulling the alpha lever sends the steam from Tunnel Alpha into Tunnel Beta')
    await C.cmd_pull(stoker, ['lever'])
    check(zh.steam_on(world.rooms[24803]) and not zh.steam_on(world.rooms[24810]), 'pulling it again sends it back')
    await enter(stoker, 24819)
    await C.cmd_pull(stoker, ['valve'])
    check(not zh.steam_on(world.rooms[24818]), 'the gamma valves shut Tunnel Gamma down, clearing the way to the Furnace Core')
    zh._pulled[world.rooms[24819]] -= zh.STEAM_BACK
    await zh.tick(world)
    check(zh.steam_on(world.rooms[24818]) and not zh.lever_pulled(world.rooms[24819]),
          f'after {zh.STEAM_BACK // 60} minutes the pressure builds back and the lever springs up')
    stoker.room.characters.remove(stoker)

    # ---- the citadel's secret ways
    seeker2 = hero('Mirrorer')
    seeker2.equipment = {'neck1': obj(24503)}         # (corruption aside)
    mirror = world.rooms[24505]
    check(mirror.exits['down'].get('hidden') and 'down' not in mirror.get_visible_exits(seeker2),
          'the Mirror Chamber hides its way down')
    await enter(seeker2, 24505)
    check('Touch the mirror' in said(seeker2), 'and gives its hint')
    await C.cmd_touch(seeker2, ['wall'])
    check('Nothing happens' in said(seeker2, 1), 'touching something else does nothing')
    await C.cmd_touch(seeker2, ['mirror'])
    check('down' in mirror.get_visible_exits(seeker2) and (24505, 'down') in seeker2.discovered_exits,
          'touching the mirror opens the way down, for this hero')
    check('down' not in mirror.get_visible_exits(diver), 'and only for them')
    await enter(seeker2, 24512)
    await C.cmd_read(seeker2, ['tome'])
    check('up' in world.rooms[24512].get_visible_exits(seeker2), 'reading the shadow tome reveals the way up')
    seeker2.room.characters.remove(seeker2)

    # ---- song power
    bard = hero('Singer', 'bard')
    ally = hero('Listener')
    bard.room = ally.room = world.rooms[3001]
    world.rooms[3001].characters += [bard, ally]
    from spells import BARD_SONGS
    song = BARD_SONGS['courage']                      # +2 to hit, +1 damage
    await bard._apply_song_to_allies(song, 1.0)
    plain = ally.song_bonuses.get('hitroll')
    bard.equipment = {'hold': obj(29055)}             # the Lyre of Orbits: song power 5
    check(bard.get_equipment_bonus('song_power') == 5 and 'songs +50%' in _gear_wards(bard), 'the Lyre of Orbits gives song power 5, and score says so')
    bard.performing, bard.performance_ticks, bard.encore_active = 'courage', 1, False
    bard.mana = bard.max_mana = 1000
    ally.song_bonuses = {}
    await bard.process_performance_tick()              # the song's own tick, as the game runs it
    check((plain, ally.song_bonuses.get('hitroll')) == (2, 3), f'a song with the lyre is half again as strong: +2 -> +3 to hit ({plain}, {ally.song_bonuses.get("hitroll")})')
    for h in (bard, ally):
        world.rooms[3001].characters.remove(h)

    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
