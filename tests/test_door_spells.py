"""Doors and the spells for them, offline: a door is made of something (its name, else its zone's
profile in world/doors.json, else wood) and that decides how much force breaks it; an arcane door
holds against any bash and any Break Door. Mages seal doors with Block Door, clerics break them
with Break Door (wood at once, iron in more than one casting, a mage's seal too); a door spell
that cannot take hold costs no mana, and from the /play bar it finds the room's one closed door.

    python3 tests/test_door_spells.py
"""
import asyncio
import logging
import os
import sys

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
    from world import World
    from player import Player
    from commands import CommandHandler as C
    import doors
    import mastery
    world = World(Config())
    await world.load()

    # ---- what doors are made of
    def one_door(pred):
        """A room with exactly one door, that door matching pred, and no one standing in it."""
        for room in world.rooms.values():
            ds = list(doors.doors_in(room))
            if len(ds) == 1 and pred(ds[0][2]) and not room.characters and doors.other_side(room, ds[0][0])[2] is not None:
                return room, ds[0][0], ds[0][2]
        return None, None, None
    wood_room, wood_dir, wood = one_door(lambda d: d['material'] == 'wood' and not d['arcane'] and not d.get('locked') and not doors.is_seal(d))
    iron_room, iron_dir, iron = one_door(lambda d: d['material'] == 'iron' and not d['arcane'] and not d.get('locked') and not doors.is_seal(d))
    arc_room, arc_dir, arc = one_door(lambda d: d['arcane'] and not d.get('locked'))
    check(wood is not None and iron is not None and arc is not None, 'there are wooden, iron and arcane doors to try')
    check(doors.material_of({'name': 'door steel'}) == ('iron', False) and doors.material_of({'name': 'tomb'})[0] == 'stone'
          and doors.material_of({'name': 'curtain'})[0] == 'cloth' and doors.material_of({'name': 'gate diamond'}) == ('stone', True),
          'a door\'s name says what it is: steel is iron, a tomb stone, a curtain cloth, a diamond gate arcane')
    check(doors.material_of({'name': 'door'}, {'material': 'stone'})[0] == 'stone' and doors.material_of({'name': 'door'})[0] == 'wood',
          'a plain door is what its zone says, else wood')
    tower = [door for r in world.rooms.values() if r.zone and r.zone.number == 25 for _d, _e, door in doors.doors_in(r)]
    check(tower and all(d['arcane'] for d in tower), f'every door in the High Tower of Magic is arcane ({len(tower)})')
    check(doors.strength({'material': 'stone'}) > doors.strength({'material': 'iron'}) > doors.strength({'material': 'oak'}) > doors.strength({'material': 'wood'}),
          'stone outlasts iron, iron oak, oak wood')

    def hero(name, cls, level=19):
        h = Player.create_new(name=name, password=None, race='human', char_class=cls,
                              stats={s: 13 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
        h.connection = Said()
        h.level = level
        h.mana = h.max_mana = 1000
        return h

    def put(h, room):
        if h.room and h in h.room.characters:
            h.room.characters.remove(h)
        h.room = room
        room.characters.append(h)

    said = lambda h, k=4: ' '.join(h.connection.sent[-k:])

    # ---- who learns them, and when
    check(mastery.unlock_level('mage', 'block_door') == 19 and ('block_door', 'spell') in mastery.roster('mage'),
          'mages learn Block Door at level 19')
    check(mastery.unlock_level('cleric', 'break_door') == 19 and ('break_door', 'spell') in mastery.roster('cleric'),
          'clerics learn Break Door at level 19')

    # ---- an arcane door holds against force
    brute = hero('Brute', 'warrior')
    put(brute, arc_room)
    doors.apply(arc_room, arc_dir, state='closed')
    await C._bash_door(brute, arc_dir)
    check(arc.get('hp') is None and 'Old magic' in said(brute), f'no bash dents an arcane door ({said(brute, 1)[:80]})')

    # ---- Block Door
    mage = hero('Sealer', 'mage')
    mage.spells['block_door'] = 100
    put(mage, wood_room)
    doors.apply(wood_room, wood_dir, state='open')
    await C.execute(mage, 'cast', ["'block door'", wood_dir])
    check(mage.mana == 1000 and 'close it first' in said(mage), f'an open door cannot be sealed, and costs nothing ({said(mage, 1)[:80]})')
    doors.apply(wood_room, wood_dir, state='closed')
    check(doors.view(wood, set(), mage).get('can_block'), 'the door menu offers Block Door to a mage who knows it')
    await C.execute(mage, 'cast', ["'block door'"])            # from the bar: the room's one closed door
    check(wood.get('sealed_until', 0) > 0 and mage.mana < 1000, f'cast with no way named, it seals the room\'s one closed door ({said(mage, 2)[:100]})')
    passer = hero('Passer', 'warrior')
    put(passer, wood_room)
    await C.execute(passer, 'open', [wood_dir])
    check(wood.get('state') == 'closed' and 'sealed by magic' in said(passer), 'no one opens a sealed door')

    # ---- Break Door
    priest = hero('Breaker', 'cleric')
    priest.spells['break_door'] = 100
    put(priest, wood_room)
    await C.execute(priest, 'cast', ["'break door'", wood_dir])
    check(wood.get('broken') and wood.get('state') == 'open', f'a wooden door, sealed and all, bursts at one casting ({said(priest, 2)[:100]})')
    put(priest, iron_room)
    doors.apply(iron_room, iron_dir, state='closed', locked=False)
    priest.mana = 1000
    await C.execute(priest, 'cast', ["'break door'", iron_dir])
    held = iron.get('state') == 'closed' and (iron.get('hp') or 0) > 0
    for _ in range(4):
        if iron.get('broken'):
            break
        await C.execute(priest, 'cast', ["'break door'", iron_dir])
    check(held and iron.get('broken'), f'an iron door holds through the first casting, then breaks ({iron.get("hp")})')
    put(priest, arc_room)
    priest.mana = 1000
    await C.execute(priest, 'cast', ["'break door'", arc_dir])
    check(priest.mana == 1000 and not arc.get('broken') and 'Old magic' in said(priest), 'Break Door does nothing to an arcane door, and costs nothing')
    check(doors.view(arc, set(), priest).get('arcane') and doors.view(arc, set(), priest).get('can_break'),
          'the door menu knows the door is arcane, and that the cleric knows Break Door')

    # ---- what else no force breaks: a quest's gate (magically blocked)
    put(priest, iron_room)
    doors.apply(iron_room, iron_dir, state='closed', broken=None, hp=None)
    iron['magically_blocked'] = True
    priest.mana = 1000
    await C.execute(priest, 'cast', ["'break door'", iron_dir])
    await C._bash_door(brute if brute.room is iron_room else priest, iron_dir)
    check(priest.mana == 1000 and not iron.get('broken') and iron.get('hp') is None, 'a quest gate (magically blocked) takes no prayer and no bash')
    iron.pop('magically_blocked', None)

    # ---- a seal is as strong as its mage, and /play hears of it at once
    novice, archmage = hero('Novice', 'mage', 19), hero('Archmage', 'mage', 60)
    for m in (novice, archmage):
        m.spells['block_door'] = 100
    put(novice, iron_room)
    await C.execute(novice, 'cast', ["'block door'", iron_dir])
    weak = C._door_max_hp(iron)
    check(doors.public(iron_room.vnum, iron_dir, iron).get('sealed'), 'a door event says the door is sealed (so /play shows it at once)')
    iron['sealed_until'] = 0
    put(archmage, iron_room)
    await C.execute(archmage, 'cast', ["'block door'", iron_dir])
    check(C._door_max_hp(iron) > weak, f"an archmage's seal takes more breaking than a novice's ({weak} -> {C._door_max_hp(iron)})")
    iron['sealed_until'] = 0
    doors.apply(iron_room, iron_dir, state='open')
    await C.execute(novice, 'cast', ["'block door'", iron_dir])
    check(not iron.get('sealed_until') and 'close it first' in said(novice), 'an open door cannot be sealed')

    # ---- what load works out about a door is never written back to a zone file
    saved = iron_room.to_dict() if hasattr(iron_room, 'to_dict') else None
    sdoor = (saved or {}).get('exits', {}).get(iron_dir, {}).get('door', {}) if saved else {}
    check(saved is None or not any(k in sdoor for k in doors.NOT_SAVED), f'a saved room keeps no material, magic or seal on its doors ({sorted(sdoor)})')

    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
