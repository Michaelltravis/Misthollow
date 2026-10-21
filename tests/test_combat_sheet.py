"""The character sheet's combat numbers (map_system._combat_sheet) are the ones a round uses: a
swing's to-hit, its damage at the bottom and top of the dice, a critical's size, the chances that
turn a blow aside, the wards, and the creature being fought, offline.

    python3 tests/test_combat_sheet.py
"""
import asyncio
import logging
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import test_webmove as tw  # noqa: E402  (check(), failures)

check, failures = tw.check, tw.failures


class Conn:
    async def send(self, message='', newline=True):
        pass

    async def send_prompt(self):
        pass


async def main():
    logging.disable(logging.WARNING)
    from config import Config
    from world import World
    from objects import Object
    from player import Player, RESIST_KEYS
    from combat import CombatHandler as CH
    from bosses import create_mob_from_prototype
    from map_system import _combat_sheet, _dice_span
    world = World(Config())
    await world.load()
    room = world.rooms[3054] if 3054 in world.rooms else world.rooms[3001]

    def put(ch):
        ch.room = room
        room.characters.append(ch)

    check(_dice_span('2d6+4') == (6, 16) and _dice_span('3d4-1') == (2, 11) and _dice_span('1d8') == (1, 8), 'dice spans')
    check(_dice_span('junk') == (1, 6), "unreadable dice: roll_dice's 1d6")

    hero = Player.create_new(name='Tally', password=None, race='human', char_class='warrior',
                             stats={s: 14 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    hero.connection = Conn()
    hero.level = 20
    hero.max_hp = hero.hp = 400
    blade = Object(0, world)
    blade.name = blade.short_desc = 'a test sword'
    blade.item_type, blade.wear_slot, blade.damage_dice = 'weapon', 'wield', '2d7'
    ring = Object(0, world)
    ring.name = ring.short_desc = 'a test ring'
    ring.item_type, ring.wear_slot = 'armor', 'finger'
    ring.affects = [{'type': 'fire_resist', 'value': 30}]
    hero.equipment = {'wield': blade, 'finger1': ring}
    hero.skills = {'dodge': 60, 'parry': 40, 'second_attack': 50}
    put(hero)

    me = _combat_sheet(hero)
    check(me is not None, 'a player has a combat sheet')
    check(me['hit'] == hero.get_hit_bonus() + 20 // Config.PLAYER_LEVEL_HIT_DIV, f"to hit counts the level ({me['hit']})")
    check(me['crit'] == CH.crit_chance(hero) and me['crit_mult'] == 2.0, f"critical {me['crit']}% x{me['crit_mult']}")
    check(me['defense'] == 10 - hero.get_armor_class() // 10, f"blows need {me['defense']}")
    check(me['avoid'] == {k: max(0, v) for k, v in CH.avoid_chances(hero).items()} and me['avoid']['parry'] > 0 and me['avoid']['block'] == 0,
          f"avoidance: parry with a blade, no block without a shield ({me['avoid']})")
    check(set(me['resist']) == set(RESIST_KEYS) and me['resist']['fire'] == 30, f"every ward, fire 30 ({me['resist']})")
    check(me['extra'] == [{'name': 'Second attack', 'chance': 30, 'hit': hero.get_hit_bonus(), 'min': me['min'], 'max': me['max']}],
          f"second attack 50% comes 30% of rounds ({me['extra']})")
    check(me['foe'] is None, 'no foe out of a fight')
    check(_combat_sheet(create_mob_from_prototype(world.mob_prototypes[3062], world)) is None, 'a creature has none')

    # the sheet's damage is what a landed swing does: dice at their least and most, no critical
    mob = create_mob_from_prototype(world.mob_prototypes[3062], world)
    mob.max_hp = mob.hp = 10 ** 6
    mob.damage_reduction = 0
    put(mob)
    world.npcs.append(mob)
    hero.fighting, mob.fighting = mob, hero
    hero.position = mob.position = 'fighting'
    real = random.randint

    async def swing(attacker, defender, dice, d100):
        def fake(a, b):
            if (a, b) == (1, 20):
                return 20
            if (a, b) == (1, 100):
                return d100
            return a if dice == 'low' else b
        attacker.next_swing_at = 0
        attacker._swing_res, attacker._swing_amt = None, 0
        random.randint = fake
        try:
            await CH.one_round(attacker, defender)
        finally:
            random.randint = real
        return {'res': attacker._swing_res, 'amt': attacker._swing_amt}

    me = _combat_sheet(hero)
    for dice, want in (('low', me['min']), ('high', me['max'])):
        hero.momentum = 0
        r = await swing(hero, mob, dice, 100)
        check(r and r['res'] == 'hit' and r['amt'] == want, f"a {dice} swing deals {want} ({r})")
    hero.momentum = 0
    r = await swing(hero, mob, 'high', 1)
    check(r and r['res'] == 'crit' and r['amt'] == int(me['max'] * me['crit_mult']), f"a critical doubles it ({r})")

    f = me['foe']
    check(f and f['name'] == mob.name and f['ac'] == mob.get_armor_class() and f['hit'] == mob.get_hit_bonus(),
          f"the creature being fought, as it is ({f})")

    # a d100 of 1 is turned aside by the dodge the sheet shows
    if me['avoid']['dodge'] > 0:
        mob.stunned_rounds, mob.staggered_until, mob.poise = 0, 0, 0    # the critical broke its poise
        r = await swing(mob, hero, 'high', 1)
        check(r and r['res'] == 'dodge', f"the hero dodges ({r})")

    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
