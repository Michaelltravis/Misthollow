"""The regions of the world (src/regions.py, world/regions.json, docs/world/WORLD_SPINE.md), offline.

Every zone of the world is in exactly one region (but Limbo, the God Rooms and the marquee
creatures' list, which are not places); a zone's map tells /play its region.

    python3 tests/test_regions.py
"""
import asyncio
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'world'))
import test_webmove as tw  # noqa: E402

check, failures = tw.check, tw.failures


async def main():
    import logging
    logging.disable(logging.WARNING)
    import regions
    import regions_ledger as ledger
    check(not ledger.problems(ledger.zones()), 'every zone file is in exactly one region (tools/world/regions_ledger.py)')
    with open(regions.PATH, encoding='utf-8') as f:
        data = json.load(f)
    want = {r['id']: sorted(r['zones']) for r in data['regions']}
    check(want == {rid: sorted(v[3]) for rid, v in ledger.REGIONS.items()}, "world/regions.json is the ledger's own (run the ledger again after editing it)")
    regions.load()
    vale = regions.of(30)
    check(vale and vale['name'] == 'The Lantern Vale' and vale['line'] and vale['levels'] == [1, 10], f'the city is in the Lantern Vale ({vale})')
    check(regions.of(300)['id'] == 'reach', 'the Shattered Throne ends the Sundered Reach')
    check(regions.of(12) is None and regions.of(0) is None and regions.of('x') is None, 'the God Rooms and Limbo are in no region')

    # a broken file is no regions, not a crash
    bad = os.path.join(tempfile.mkdtemp(), 'regions.json')
    with open(bad, 'w', encoding='utf-8') as f:
        f.write('{"regions": [{"id": "a", "name": "A", "zones": [1, 2]}, {"name": "no id"}, {"id": "b", "name": "B", "zones": [2, "x", 3]}]}')
    got = regions.load(bad)
    check(sorted(got) == [1, 2, 3] and got[2]['id'] == 'a' and got[3]['id'] == 'b', 'a malformed region is skipped; a zone listed twice keeps its first')
    check(regions.load(os.path.join(tempfile.gettempdir(), 'no-such-regions.json')) == {}, 'no file: no regions')
    regions.load()

    from config import Config
    Config.PLAYER_DIR = tempfile.mkdtemp()
    from world import World
    import map_system
    build_zm = map_system.build_zonemap
    world = World(Config())
    await world.load()
    zm = map_system.build_zonemap(world, world.rooms[3001].zone.number)
    check(zm.get('region') and zm['region']['id'] == 'vale', "the city's map says its region")
    zm12 = map_system.build_zonemap(world, 12)
    check(zm12 is None or zm12.get('region') is None, "the God Rooms' map says none")
    named = [z for z in world.zones.values() if regions.of(z.number)]
    check(len(named) >= 120, f'{len(named)} loaded zones have a region')

    # ---- what zones are called in play (world/zone_names.json)
    check(world.zones[186].name == 'The Proving Halls' and world.zones[186].file_name == 'Newbie Zone', 'the first zone is the Proving Halls; its file keeps the old name')
    check(world.zones[408].name == 'The Lantern Road' and world.zones[30].name == 'Garathorm Inner City', 'a renamed zone and one that keeps its name')
    import re as _re
    borrowed = _re.compile(r'\b(Moria|Gondor|Olympus|Elvandar|Atuan|Salem|Hommlet|Drow City|Isle of Lag|Newbie)\b|\bI{1,2}$')
    left = sorted(z.name for z in world.zones.values() if regions.of(z.number) and borrowed.search(z.name))
    check(not left, f"no zone in a region is still called by a builder's numeral or another author's name ({left})")
    check(build_zm(world, 186)['name'] == 'The Proving Halls', "the zone's map says the new name")

    # ---- the Frostmarch lifted to 20-35 (world/zone_levels.json, regions.relevel)
    check(regions.new_level(3, {'add': 10, 'lo': 20, 'hi': 26}) == 20 and regions.new_level(14, {'add': 10, 'lo': 20, 'hi': 26}) == 24
          and regions.new_level(19, {'add': 10, 'lo': 20, 'hi': 26}) == 26 and regions.new_level(45, {'add': 10, 'lo': 20, 'hi': 26}) == 45,
          'a creature gains the levels, held in the band; one above it keeps its own')
    import statistics
    def spawned(znum):
        vs = {int(r.get('vnum') if isinstance(r, dict) else r) for room in world.zones[znum].rooms.values() for r in (getattr(room, 'mob_resets', None) or [])}
        return [world.mob_prototypes[v] for v in vs if v in world.mob_prototypes]
    for znum, lo in ((66, 20), (180, 22), (521, 24), (522, 28), (190, 30)):
        ps = spawned(znum)
        med = statistics.median(p['level'] for p in ps) if ps else 0
        # (a creature that also lives in an earlier zone keeps the level it was given there)
        under = [p for p in ps if p['level'] < lo]
        check(ps and len(under) <= 1 and med >= lo, f'{world.zones[znum].name}: its creatures are level {lo} and up (median {med}; {len(under)} shared with an earlier zone)')
    import population
    lifted = [p for p in spawned(522) if p.get('_releveled')]
    check(lifted and all((p.get('max_hp') or population._avg(p['hp_dice'])) >= population.numbers(p['level'], p.get('rank'))['max_hp'] * 0.95 for p in lifted),
          'a lifted creature has at least the health of its new level')
    check(not any(p.get('_releveled') for p in spawned(30)), 'a zone not in the file is as it was')

    # ---- the roads out: a quest to each region's gate, from Sage Aldric in the Temple
    from quests import QUEST_DEFINITIONS, QuestManager
    roads = {k: q for k, q in QUEST_DEFINITIONS.items() if k.startswith('road_')}
    check(len(roads) == 8 and {q['region'] for q in roads.values()} == {r['id'] for r in data['regions']} - {'beyond'}, 'one for every region with a road into it')
    aldric = [m for m in world.npcs if getattr(m, 'vnum', None) == 3200]
    check(bool(aldric) and aldric[0].room.vnum == 3001, 'Sage Aldric stands in the Temple')
    for k, q in roads.items():
        target = world.rooms.get(int(q['objectives'][0]['target']))
        check(target is not None and regions.of(target.zone.number)['id'] == q['region'], f"{q['name']}: its goal is a room of {q['region']}")
    young = hero_at_level = None
    from player import Player as _P
    young = _P.create_new(name='Roadtest', password=None, race='human', char_class='warrior', stats={k: 13 for k in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    young.level = 7
    offered = set(QuestManager.get_available_quests(young, 3200))
    check({'road_vale', 'road_marches', 'road_sundersea'} <= offered and 'road_reach' not in offered and 'road_deeproad' not in offered,
          f'at level 7 the near roads are offered, the far ones not ({sorted(k for k in offered if k.startswith("road_"))})')

    # ---- the roads' ends: each region's villain, told once its road is walked
    from mobs import Mobile as _M
    ends = {k: q for k, q in QUEST_DEFINITIONS.items() if k.startswith('story_')}
    trails = {k: q for k, q in QUEST_DEFINITIONS.items() if k.startswith('trail_') and q.get('region')}
    lits = {k: q for k, q in QUEST_DEFINITIONS.items() if k.startswith('lit_') and q.get('region')}
    check(len(ends) == 8 and all(q['after'] == 'trail_' + q['region'] and q['after'] in trails for q in ends.values()), "a story for each region, after its trail")
    check(len(trails) == 8 and all(q['after'] == 'road_' + q['region'] and q['after'] in roads and q['quest_giver'] == 3200 for q in trails.values()), "a trail for each road, after it")
    check(len(lits) == 8 and all(q['after'] == 'story_' + q['region'] and q['objectives'][0]['target'] == roads['road_' + q['region']]['objectives'][0]['target']
                                 for q in lits.values()), "and a last walk for each story, back to the road's own room")
    check(all(roads['road_' + q['region']]['level_min'] <= q['level_min'] <= ends['story_' + q['region']]['level_min'] for q in trails.values()),
          "a trail is of a level between its road and its story")
    said = [(_M.said_name(p.get('name'), p.get('short_desc')) or p.get('name') or '').lower() for p in world.mob_prototypes.values()]
    for k, q in ends.items():
        t = q['objectives'][0]['target']
        check(any(t in n for n in said), f"{q['name']}: there is a creature called by '{t}' to defeat")
    by_region = {}
    for m in world.npcs:
        z = getattr(getattr(m, 'room', None), 'zone', None)
        r = regions.of(z.number) if z is not None else None
        if r:
            by_region.setdefault(r['id'], []).append((m.name or '').lower())
    for k, q in trails.items():
        o = q['objectives'][0]
        n = sum(1 for name in by_region.get(q['region'], []) if o['target'] in name)
        check(n > o['required'], f"{q['name']}: {n} creatures called '{o['target']}' live in {q['region']} (it asks for {o['required']})")
    vet = _P.create_new(name='Endtest', password=None, race='human', char_class='warrior', stats={k: 13 for k in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    vet.level = 30
    check('story_marches' not in QuestManager.get_available_quests(vet, 3200), "the story is not told before its road is walked")
    vet.quests_completed = ['road_marches']
    got = QuestManager.get_available_quests(vet, 3200)
    check('trail_marches' in got and 'story_marches' not in got, "the road walked, the trail is told; the story not yet")
    vet.quests_completed = ['road_marches', 'trail_marches']
    got = QuestManager.get_available_quests(vet, 3200)
    check('story_marches' in got and 'story_frostmarch' not in got and 'lit_marches' not in got, "and is told after it (and only that region's)")
    vet.quests_completed = ['road_marches', 'trail_marches', 'story_marches']
    check('lit_marches' in QuestManager.get_available_quests(vet, 3200), "the villain fallen, the road is walked once more")

    # ---- a story is within a mortal's reach, and is not taken before its road by name either
    import prestige
    import test_atlas_engine as tae
    cap = prestige.get_max_level(vet)
    check(all(q['level_min'] <= cap for q in list(roads.values()) + list(ends.values()) + list(trails.values()) + list(lits.values())),
          f"every road and story can be offered at a level a hero reaches (the cap is {cap}: {sorted((k, q['level_min']) for k, q in ends.items() if q['level_min'] > cap)})")
    skip = _P.create_new(name='Skiptest', password=None, race='human', char_class='warrior', stats={k: 13 for k in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    skip.connection = tae.Conn()
    skip.level = 30
    await QuestManager.accept_quest(skip, 'story_vale')
    check(not QuestManager.has_active_quest(skip, 'story_vale') and 'another to finish first' in tae.said(skip, 2), '`quest accept story_vale` before its road is refused, and says why')
    skip.quests_completed = ['road_vale', 'trail_vale']
    await QuestManager.accept_quest(skip, 'story_vale')
    check(QuestManager.has_active_quest(skip, 'story_vale'), 'and taken once the road is walked')
    top = _P.create_new(name='Toptest', password=None, race='human', char_class='warrior', stats={k: 13 for k in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    top.level = cap
    top.quests_completed = ['road_deeproad', 'road_reach', 'trail_deeproad', 'trail_reach']
    got = QuestManager.get_available_quests(top, 3200)
    check('story_deeproad' in got and 'story_reach' in got, 'at the level cap the last two stories are offered')

    # ---- words of another author's world are said otherwise (world/words.json, regions.apply_words)
    fix = regions._replacer({'Lloth': 'Ishaleth', 'yochlol': 'silk-handmaiden'})
    check(fix('the Temple Of Lloth') == 'the Temple Of Ishaleth' and fix('a Yochlol waits') == 'a Silk-handmaiden waits' and fix('lloth temple') == 'Ishaleth temple',
          'whole words; a name keeps its capital, a common word takes the case it replaces')
    check(fix('slothful') == 'slothful' and fix('no such word') == 'no such word', 'never inside another word')
    import json as _json
    texts = []
    for r in world.rooms.values():
        texts += [r.name, r.description or ''] + list((getattr(r, 'extra_descs', None) or {}).values())
    texts.append(_json.dumps(list(world.mob_prototypes.values()), default=str))
    texts.append(_json.dumps(list(world.obj_prototypes.values()), default=str))
    left = [t[:60] for t in texts if _re.search(r'\b(lloth|lolth|yochlol)\b', str(t), _re.I)]
    check(not left, f"no room, creature or thing still says them ({left[:3]})")
    check(any('Ishaleth' in str(t) for t in texts), 'and the Umbral City has its own goddess')
    # the first zone's own names
    check(world.rooms[18600].name == 'The Arch Of The Proving Halls', "the first zone's arch is named for the Proving Halls")
    newbie = [t[:50] for t in ([r.name for r in world.zones[186].rooms.values()] + [_json.dumps(p, default=str) for v, p in world.mob_prototypes.items() if 18600 <= v < 18700]
              + [_json.dumps(p, default=str) for v, p in world.obj_prototypes.items() if 18600 <= v < 18700]) if _re.search(r'newbie', t, _re.I)]
    check(not newbie, f'nothing in the first zone is called a newbie any more ({newbie[:3]})')

    # ---- the bells at dusk: heard in the Lantern Vale, and nowhere else
    temple, square = world.rooms[3001], world.rooms[3005]
    check(regions.bells_line(temple) == regions.BELLS_INDOORS, 'in the Temple the bells come through the walls')
    check(regions.bells_line(square) == regions.BELLS_OUTDOORS, 'in the square they ring across the Vale')
    far = next(r for r in world.rooms.values() if regions.of(r.zone.number) and regions.of(r.zone.number)['id'] == 'reach')
    check(regions.bells_line(far) is None and regions.bells_line(None) is None, 'the Sundered Reach is out of earshot')
    import test_atlas_engine as tae
    from player import Player
    def hero_at(name, room):
        h = Player.create_new(name=name, password=None, race='human', char_class='warrior',
                              stats={k: 13 for k in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
        h.connection = tae.Conn()
        h.room = room
        world.players[name.lower()] = h
        return h
    near, away = hero_at('Bellnear', square), hero_at('Bellfar', far)
    heard = await regions.dusk_bells(world)
    check(heard == 1 and 'bells' in tae.said(near, 1).lower() and 'bells' not in tae.said(away, 3).lower(), 'at dusk those in the Vale are told, the others are not')

    # ---- a creature that attacks on sight does not wander into a peaceful room (mobs.wander_ai)
    import random as _rnd
    import mobs as _mobs
    from bosses import create_mob_from_prototype as _make
    calm = next(r for r in world.rooms.values() if 'peaceful' in r.flags and not (_mobs.KEEP_OUT & r.flags)
                and getattr(r, 'sector_type', '') not in _mobs.WATER_SECTORS)
    here = next(r for r in world.rooms.values() if r is not calm and 'peaceful' not in r.flags and r.exits)
    wolf = _make(next(iter(world.mob_prototypes.values())), world)
    wolf.special, wolf.owner, wolf.fighting, wolf.home_zone = None, None, None, None
    was_exits, was_rand = here.exits, _rnd.randint
    here.exits = {'north': {'room': calm}}
    _rnd.randint = lambda a, b: a
    try:
        wolf.flags = {'aggressive'}
        wolf.room = here
        here.characters.append(wolf)
        for _ in range(4):
            await wolf.wander_ai()
        check(wolf.room is here, 'a creature that attacks on sight stays out of a peaceful room')
        wolf.flags = set()
        for _ in range(4):
            await wolf.wander_ai()
            if wolf.room is not here:
                break
        check(wolf.room is calm, 'one that does not may walk in as before')
    finally:
        here.exits, _rnd.randint = was_exits, was_rand
        for r in (here, calm):
            if wolf in r.characters:
                r.characters.remove(wolf)
    print('ALL OK' if not failures else f'{len(failures)} FAILED')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
