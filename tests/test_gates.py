"""Every zone given a population, and the zones just outside Garathorm's gates, offline (world/population/zone_{72,408,50,200,79}.json):
the Sewer's Rat King, the Trade Road's wardens, outlaws, Black Jory and the Barrow King, the
dracolich and the myconids under the mountain, the Forest of Shadows' pack and brood, and
Redferne in his sky-house.

    python3 tests/test_gates.py
"""
import asyncio
import collections
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
    import allies
    import population
    import bosses
    import marquee_scale
    world = World(Config())
    await world.load()
    npcs = lambda v: [m for m in world.npcs if getattr(m, 'vnum', None) == v]
    count = collections.Counter(getattr(m, 'vnum', None) for m in world.npcs)

    # ---- every population file: each boss in its room, a boss, with its mechanics; each rank
    # given holds (and lifts the creature to the rank's numbers); each patrol walks its own route
    for z, d in sorted(population.load().items()):
        for b in d.get('bosses') or []:
            ms = npcs(int(b['vnum']))
            want = [m['type'] for m in b.get('mechanics') or []]
            check(len(ms) == 1 and ms[0].room.vnum == int(b['room']) and getattr(ms[0], 'is_boss', False)
                  and [m.spec['type'] for m in ms[0].mechanics] == want and getattr(ms[0], 'rank', None) in (None, 'boss'),
                  f'zone {z}: {b["why"]} ({want})')
        # a lair's boss is in no room until someone walks in (lairs.py): made as he will be, he is a
        # boss with his mechanics and rank
        import lairs
        in_lair = {int(b['vnum']) for b in d.get('lairs') or []}
        for b in d.get('lairs') or []:
            m = bosses.create_mob_from_prototype(world.mob_prototypes[int(b['vnum'])], world)
            want = [x['type'] for x in b.get('mechanics') or []]
            check(not npcs(int(b['vnum'])) and lairs.lair_of(world.rooms[int(b['room'])]) is not None
                  and getattr(m, 'is_boss', False) and [x.spec['type'] for x in m.mechanics] == want
                  and getattr(m, 'rank', None) == 'boss' and getattr(m, 'zone_sized', False),
                  f'zone {z}: {b["why"]} ({want})')
        for v, c in (d.get('creatures') or {}).items():
            if c.get('rank') and 'name' not in c and int(v) not in in_lair:
                ms = npcs(int(v))
                floor = population.numbers(ms[0].level, c['rank'])['max_hp'] * 0.95 if ms else 0
                if ms and getattr(ms[0], 'zone_sized', False):
                    # a zone boss's health is the sizing's, whatever its rank says (bosses.size_zone_boss)
                    floor = int(bosses.ZONE_BOSS_ROUNDS * marquee_scale.dpr(ms[0].level))
                check(ms and all(getattr(m, 'rank', None) == c['rank'] and m.max_hp >= floor for m in ms),
                      f'zone {z}: {v} is {c["rank"]} ({count[int(v)]} of them, {ms[0].max_hp if ms else 0} health)')
        for p in d.get('patrols') or []:
            walkers = [m for m in npcs(int(p['vnum'])) if getattr(m, 'patrol_route', None) == p['route']]
            check(len(walkers) == 1, f'zone {z}: {p["why"]} ({len(p["route"])} rooms)')
    # ---- a patrol walks
    w = next(m for m in npcs(40800) if m.patrol_route[0] == 9768)
    w._patrol_next = 0
    check(await w.patrol_ai() and w.room.vnum == w.patrol_route[1], 'a warden rides on along the Trade Road')
    # ---- helpers
    jory = npcs(40810)[0]
    check(jory.room.vnum == 19742 and jory.rank == 'sub-boss' and jory.helpers['group'] == 'outlaws', 'Black Jory holds the clearing, and whistles for outlaws')
    king = npcs(72000)[0]
    check(king.room.vnum == 7320 and king.max_hp > 5 * npcs(7207)[0].max_hp, 'the Rat King at the Lair End, far tougher than his rats')
    rat = npcs(7002)[0]
    came = allies.nearby_allies(rat, 2, 5)
    check(all(getattr(m, 'helpers', {}).get('group') == 'sewer_rats' for m, _ in came), f'only rats answer a rat ({len(came)})')
    check(npcs(5014)[0].rank == 'sub-boss' and len(npcs(50000)) == 3, 'the myconid shaman and its three sentries')
    check(npcs(79002) and npcs(79003) and npcs(79000)[0].room.vnum == 7911, "Redferne's household, and Redferne in his bedroom")
    # ---- the next ring out
    check(npcs(2537)[0].room.vnum == 2590 and npcs(2537)[0].rank == 'boss', 'the Master Summoner in his Pentagram Chamber')
    crier = next(m for m in world.npcs if getattr(m, 'vnum', None) == 5433)
    came = allies.nearby_allies(crier, 3, 5)
    check(all(getattr(m, 'vnum', None) in (5461, 5462, 5482, 5463) for m, _ in came), f'in New Thalos only the guard answers ({len(came)})')
    check(npcs(40050)[0].room.vnum == 4044, 'Grondar in the Hill Giant Cave')
    grukthar = npcs(3503)[0]
    check(grukthar.rank == 'boss', 'Grukthar the Goblin King a boss')
    check(npcs(120501)[0].room.vnum == 12204 and npcs(120500)[0].room.vnum == 8892, 'the High Priest of Terror in his temple, the Pallid Herald in Lost Carcosa')
    # ---- the World of Chaos and Ghenna, built and opened together (world/atlas/overrides.json)
    chaos, ghenna = world.zones[475], world.zones[481]
    check(not getattr(chaos, 'sealed', False) and not getattr(ghenna, 'sealed', False), 'the World of Chaos and Ghenna are open')
    down = world.rooms[16258].exits.get('down') or {}
    check(down.get('room') is world.rooms[9901] and not down.get('door'), 'from the island in the Lake of Blood a way leads down to Ghenna, unbarred')
    check(npcs(47530)[0].room.vnum == 16252 and npcs(9910)[0].room.vnum == 9937, 'the Lord of Chaos in the Hall of Pillars; the Deep Dragon in its lair')
    # ---- the archive-backed batch: the Elven Village's original creatures back, and the bosses
    chief = [m for m in world.npcs if 'chief of the elven guard' in (m.short_desc or '').lower()]
    check(chief and chief[0].rank == 'sub-boss' and chief[0].room.zone.number == 110, 'the Chief of the elven guard is back in the Elven Village')
    check(npcs(6450)[0].room.vnum == 6411, 'Rand the Dreamer in the Master Bedroom')
    check(npcs(3305)[0].rank == 'boss' and npcs(6210)[0].rank == 'boss', 'Aglandiir and Elstar are bosses')
    ramses = npcs(5317)[0]
    check(ramses.room.vnum == 5332 and [m.spec['type'] for m in ramses.mechanics] == ['hunger', 'gloom'], 'Ramses in his tomb, his curse starving the still')
    # ---- Mahn-Tor Keep: the folk its rooms are named for stand in them
    for name, where in (('darkoth', "Darkoth's Dark Study"), ('tyrgoth', "Tyrgoth's Inner Sanctum"), ('sumaron', "Sumaron's Sanctum"),
                        ('amyrok', "Amyrok's Arcane Study"), ('nasturn', "Nasturn's Humble Abode"),
                        ('dorgar', "Dorgar's Dismal Domicile"), ('belrak', "Belrak's Green Room")):
        folk = [m for m in world.npcs if name in (m.name or '').lower() and getattr(m, 'room', None) is not None]
        check(len(folk) == 1 and folk[0].room.name == where, f'{name.title()} in {where}')
    # ---- the rest of ring 2
    check(npcs(8003)[0].room.vnum == 8003 and npcs(7304)[0].room.vnum == 7352, 'Scorathax in the Treasure Cavern; the Master Mindflayer in its sanctum')
    check(npcs(644103)[0].room.vnum == 8742 and npcs(47150)[0].room.vnum == 8357, 'the barrow wight in the Barrow Mound; the Black Priest before the Dark Castle')
    newbie = [m for m in world.npcs if getattr(m, 'room', None) is not None and m.room.zone.number == 186]
    check(not any(getattr(m, 'is_boss', False) for m in newbie), 'the Newbie Zone has no boss')
    # ---- ring 3
    check(npcs(5200)[0].room.vnum == 5250 and npcs(90500)[0].room.vnum == 9018, 'the beholder in the Temple of Thalos; the Bog Witch in her hut')
    check(npcs(6114)[0].room.vnum == 6134 and npcs(6704)[0].rank == 'boss', 'the Queen spider in her den; the raider chieftain a boss')
    grizz = npcs(23513)[0]
    check(grizz.room.name == 'The Goblin Throne Room' and grizz.rank == 'boss', 'Grizznak on his throne')
    check(world.rooms[8742].look == 'crypt', 'the Barrow Mound looks like a barrow')
    # ---- ring 3, the wilds
    check(npcs(18009)[0].room.vnum == 18024 and npcs(27016)[0].room.vnum == 27022, 'the alpha wolf in its den; the Blightlord at the Heart of Corruption')
    check(npcs(16025)[0].room.vnum == 16025 and npcs(47250)[0].room.name == 'On The Mountain Top', 'Kaleidos in its lair; the Wyvern Matriarch on Ravenmist')
    check(npcs(52150)[0].room.name == 'The End of The Winterwood', 'the Winter Witch at the end of the Winterwood')
    # ---- MiNar, the southern sea, Arachnos
    check(npcs(43550)[0].room.name == "Farrot's Nest" and npcs(45150)[0].room.zone.number == 451, 'Farrot in her nest; the Ice Leviathan in the southern sea')
    check(npcs(6314)[0].room.vnum == 6399 and npcs(6302)[0].rank == 'sub-boss', 'Zyraxxis in the Lair of Arachnos; Yevaud a sub-boss')
    # ---- the dwarven holds, the Frostspire, the monastery, the Tunnel of Sticks
    check(npcs(6516)[0].room.vnum == 6553 and npcs(10050)[0].room.name == 'Hall of the Mountain King', 'the Mazekeeper at the maze\'s end; Skarg in the Mountain King\'s hall')
    check(npcs(19010)[0].room.vnum == 19011 and npcs(19007)[0].room.vnum == 19038, 'Vyrkothas on the summit; the Frozen King in his vault')
    mother = npcs(21050)[0]
    check(npcs(23812)[0].rank == 'boss' and mother.room.zone.number == 210, "the Abbot's Ghost a boss; the Stick Mother deep in the tunnel")
    # ---- the Ashlands, the Sunken Coast, the upper tower, Nereus, Minos
    tyrant = npcs(6950)[0]
    check(tyrant.room.vnum == 6907 and npcs(6805)[0].rank == 'boss', 'the Cinder Tyrant at the Magma Flows; Captain Blackhand a boss')
    mistress = npcs(2564)[0]
    check(mistress.room.vnum == 2677 and len(npcs(24006)) == 1, 'the Grand Mistress in the Audience Chamber; one Kraken')
    minos = npcs(907)[0]
    check(minos.room.vnum == 934 and len(npcs(904)) == 1, 'King Minos on his throne; Woundwort only once')
    # ---- the end-game zones: every boss fights with abilities and mechanics
    for v in (24505, 24805, 28020, 28520, 29020, 29520, 30020):
        b = npcs(v)[0]
        check(getattr(b, 'is_boss', False) and b.abilities and b.mechanics, f'{b.name}: a boss with abilities and mechanics')
    # ---- opened: Garathorm's districts, Hommlet's upper rooms, the Haunted House, Ancalador
    shut = [z for z in (431, 517, 420, 418, 423, 482, 479) if getattr(world.zones[z], 'sealed', False)]
    check(not shut, f'the districts and the new zones are open ({shut})')
    canon = npcs(42310)[0]
    lord = npcs(48210)[0]
    check(canon.room.vnum == 8244 and lord.room.vnum == 1924, 'the false Canon in his chambers; the Lord of the House in the master bedroom')
    morticia = [m for m in world.npcs if 'morticia' in (m.name or '').lower()]
    check(morticia and morticia[0].rank == 'boss', 'Morticia rules the Bloodstone guild')
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
