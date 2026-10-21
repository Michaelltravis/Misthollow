"""Ostragoth's lair and the Starbringer, offline (lairs.py, world/population/zone_470.json).

Ostragoth is not in the world until someone walks into his bedchamber (8403). Then the black iron
door slams and bolts (on both sides, pickproof and magically sealed), a great black bat flies in
and becomes him, and he falls on whoever came in. While it is sealed no one walks, portals,
travels or teleports out, and no one is summoned in; a recall (even mid-fight) or a summons out
takes you away, and if the room empties he leaves as he came, whole, and the door opens. His
death opens it too, drops his star-key, and he does not come again until the castle resets. The
key opens the House of Death (8424), where the Starbringer waits: a raid at the level cap, its
numbers its own.

    python3 tests/test_lairs.py
"""
import asyncio
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
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
    import tempfile
    Config.PLAYER_DIR = tempfile.mkdtemp()
    from world import World
    from player import Player
    from commands import CommandHandler as C
    from combat import CombatHandler
    from spells import SpellHandler
    import doors
    import lairs
    import travel
    world = World(Config())
    await world.load()
    real_immortal = Player.is_immortal
    Player.is_immortal = property(lambda self: getattr(self, '_test_imm', False))
    lairs.ARRIVE_DELAY, lairs.TURN_DELAY, lairs.WATCH = 0.05, 0.05, 0.02

    def hero(name, level=21):
        h = Player.create_new(name=name, password=None, race='human', char_class='warrior',
                              stats={s: 13 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
        h.connection = Said()
        h.level = level
        h.hp = h.max_hp = 5000
        h.mana = h.max_mana = h.move = h.max_move = 1000
        world.players[h.name.lower()] = h
        return h

    def put(h, room):
        if h.room and h in h.room.characters:
            h.room.characters.remove(h)
        h.room = room
        room.characters.append(h)

    said = lambda h, k=6: ' '.join(h.connection.sent[-k:])
    of = lambda v: [m for m in world.npcs if getattr(m, 'vnum', None) == v]
    chamber, ante, house, cave = (world.rooms[v] for v in (8403, 8396, 8424, 8423))
    door = chamber.exits['south']['door']

    async def settle(secs=0.3):
        await asyncio.sleep(secs)

    # ---- at load: no Ostragoth anywhere, his door open, the Starbringer behind a starred door
    lair = lairs.lair_of(chamber)
    check(lair is not None and lair.vnum == 647006 and not of(647006), 'Ostragoth waits in no room: he comes to his lair')
    check(door['state'] == 'open' and not door.get('locked') and ante.exits['north']['door']['state'] == 'open',
          "the King's Chamber has a black iron door, open")
    star = house.exits['south']['door']
    check(star['state'] == 'closed' and star['locked'] and doors.key_vnum(star) == 747005 and star.get('pickproof') and star.get('arcane')
          and cave.exits['north']['door']['locked'], "the House of Death is shut behind a starred door only Ostragoth's key opens")
    sb = of(647007)
    check(len(sb) == 1 and sb[0].room is house and sb[0].is_boss and sb[0].raid and sb[0].max_hp == 120000
          and not getattr(sb[0], 'zone_sized', False), f'the Starbringer in the House of Death, a raid with its own numbers ({sb[0].max_hp if sb else 0})')
    check([m.spec['type'] for m in sb[0].mechanics] == ['plague_pools', 'waves', 'gloom', 'hunger']
          and sb[0].mechanics[3].spec['below'] == 40, 'the Starbringer: starfall, its motes, its light dying, and its pull below 40%')
    proto = world.mob_prototypes[647006]
    check({'vnum': 747005, 'chance': 100} in proto['loot_table'] and proto['short_desc'] == 'Ostragoth, the vampire lord',
          'Ostragoth, the vampire lord, always carries his star-key')

    # ---- an immortal walks in: nothing stirs
    imm = hero('Lairimm')
    imm._test_imm = True
    put(imm, ante)
    await C.cmd_move(imm, 'north')
    await settle()
    check(imm.room is chamber and not lair.sealed and not of(647006), 'an immortal walks in and nothing stirs')
    put(imm, world.rooms[3001])

    # ---- a hero walks in: the door slams, a bat flies in, and becomes Ostragoth
    ann = hero('Lairann')
    out = hero('Lairout')
    put(ann, ante)
    put(out, ante)
    await C.cmd_move(ann, 'north')
    await asyncio.sleep(0.01)
    check(lair.sealed and door['state'] == 'closed' and door['locked'] and door.get('magically_blocked') and door.get('pickproof')
          and ante.exits['north']['door']['locked'] and ante.exits['north']['door'].get('pickproof'),
          'the door slams and bolts behind her, on both sides, pickproof and sealed')
    check('slams shut' in said(out), f'next door they hear it slam ({said(out, 2)})')
    await asyncio.sleep(0.07)
    bats = [m for m in chamber.characters if getattr(m, 'vnum', None) == 647009]
    check(bats or 'great black bat' in said(ann), 'a great black bat bursts in')
    await settle()
    boss = of(647006)
    check(len(boss) == 1 and boss[0].room is chamber and boss[0].fighting is ann and not of(647009),
          'the bat becomes Ostragoth, and he falls on her')
    check('Ostragoth rises' in ' '.join(ann.connection.sent), 'she sees him rise')
    boss = boss[0]
    check([m.spec['type'] for m in boss.mechanics] == ['waves', 'plague_pools', 'gloom', 'hunger'] and boss.mechanics[3].spec['below'] == 30,
          "his bats, blood pools, the dark, and his thirst below 30%")
    check(getattr(boss, 'zone_sized', False) and boss.max_hp > 3000, f'sized as the castle boss ({boss.max_hp})')

    # ---- no way out but recall, a summons, or his death
    await C.cmd_move(ann, 'south')
    check(ann.room is chamber and 'locked' in said(ann, 2), 'she cannot walk out: the door is bolted')
    await C.cmd_open(ann, ['door'])
    check(door['state'] == 'closed', 'nor open it')
    ok, msg = travel.can_travel(ann)
    check(not ok, f'nor travel ({msg})')
    held = lairs.holds(ann)
    ann.connection.sent.clear()
    await C.cmd_enter(ann, [])
    check(held and held in said(ann), 'nor step into a portal')
    await SpellHandler.handle_special_spell(ann, None, {'special': 'teleport'})
    check(ann.room is chamber, 'nor teleport')
    await C.cmd_move(out, 'north')
    check(out.room is ante, 'and no one walks in to her')
    late = hero('Lairlate')
    put(late, ante)
    await SpellHandler.handle_special_spell(ann, 'Lairlate', {'special': 'summon_player'})
    check(late.room is ante, 'nor is anyone summoned in')

    # ---- a summons takes her out; the room empty, he leaves whole and the door opens
    await SpellHandler.handle_special_spell(out, 'Lairann', {'special': 'summon_player'})
    check(ann.room is ante and ann.fighting is None, 'a summons takes her out, mid-fight')
    await settle()
    check(not of(647006) and not lair.sealed and door['state'] == 'open' and not door.get('locked') and not door.get('magically_blocked')
          and not door.get('pickproof'), 'with no one to feed on he flies off, and the door opens')

    # ---- again: recall, mid-fight, takes her out
    await C.cmd_move(ann, 'north')
    await settle()
    check(len(of(647006)) == 1 and ann.is_fighting, 'he comes again, whole')
    await C.cmd_recall(ann, [])
    check(ann.room is not chamber and not ann.is_fighting, f'recall takes her out of the fight ({said(ann, 2)})')
    await settle()
    check(not of(647006) and not lair.sealed, 'and he goes')

    # ---- his death opens the door, drops the key, and he waits for the castle's reset
    put(ann, ante)
    await C.cmd_move(ann, 'north')
    await settle()
    boss = of(647006)[0]
    boss.hp = 0
    await CombatHandler.handle_death(ann, boss)
    await settle()
    check(not lair.sealed and door['state'] == 'open' and lair.slain_at, 'his death opens the door')
    corpse = [o for o in chamber.items if 'corpse' in getattr(o, 'name', '')]
    keys = [i for o in corpse for i in (getattr(o, 'contents', None) or [])] + list(chamber.items)
    check(any(getattr(i, 'vnum', None) == 747005 for i in keys), 'and he leaves his star-key')
    await C.cmd_move(ann, 'south')
    await C.cmd_move(ann, 'north')
    await settle()
    check(not of(647006) and not lair.sealed, 'he does not come again before the castle resets')
    chamber.zone.last_reset_at = time.time() + 1
    check(lair.waiting(chamber), 'after it resets he waits again')
    lair.slain_at = time.time() + 2      # (the test leaves him unwoken)

    # ---- the key opens the House of Death
    from objects import create_object
    ann.inventory.append(create_object(747005, world))
    put(ann, cave)
    await C.cmd_unlock(ann, ['north'])
    check(not star['locked'] and not cave.exits['north']['door']['locked'], f"Ostragoth's key unlocks the starred door ({said(ann, 2)})")

    Player.is_immortal = real_immortal
    print(f"\n{len(failures)} failed" if failures else '\nall passed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
