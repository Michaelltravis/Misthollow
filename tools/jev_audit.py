"""A second opinion on how the world is drawn, from JEV (TypeSafe's decision model): for every room,
which look its own words describe; for every creature, which body. JEV picks from the game's own
options and says how sure it is, so the report lists only the places where it is sure the game
drew something else. It changes nothing: each one is for a person to judge (a room or creature
judged right as it is goes in ACCEPT, a wrong one is fixed where it is decided: world/looks.json
for rooms, world3d/bestiary.js for creatures).

    python3 tools/jev_audit.py rooms [--zone N] [--limit N]
    python3 tools/jev_audit.py zones [--zone N]
    python3 tools/jev_audit.py shots DIR      (DIR holds <vnum>.jpg screenshots of rooms in /play)
    python3 tools/jev_audit.py creatures [--limit N]

A room can be drawn right by its own words and its zone still be wrong: every room of the Drow
City read as a cave, and the city of the dark elves was drawn as plain tunnels. So `zones` asks,
for each zone as a whole, whether the looks its rooms are drawn with show its setting.

The key: TYPESAFE_API_KEY in the environment, or (a cloud session) a network secret that adds it
to requests to api.typesafe.ai. Answers are kept in tools/audit/out/jev_*.json, so a run again
asks only what it hasn't asked before. The report goes to docs/JEV_REVIEW_<what>.md.
"""
import asyncio
import collections
import concurrent.futures
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'src'))
OUT = os.path.join(HERE, 'audit', 'out')
URL = 'https://api.typesafe.ai/v1/systemone'
MODEL = 'jev-latest'
SURE = 0.9          # JEV's confidence in its own pick
UNLIKELY = 0.05     # and the most it gives the game's pick, for a disagreement to be listed

# the looks a room can be drawn with (room_looks.py OVERRIDE_LOOKS), as JEV is told them
LOOKS = {
    'inside': 'an ordinary room inside a building: a house, shop, inn, temple, hall or tower room',
    'city': 'outdoors in a town or city: streets, plazas, markets, alleys, gates',
    'village': 'a small rural hamlet of cottages and lanes',
    'castle': 'a castle or fortress: its halls, keep, ramparts, courtyard or gatehouse',
    'field': 'open country: plains, grassland, farmland, meadows, a road through open land',
    'forest': 'woods: among trees, a forest path or clearing',
    'hills': 'rolling hills and downs',
    'mountain': 'mountain slopes, peaks, cliffs, ledges, passes',
    'desert': 'sand, dunes, dry wasteland',
    'snow': 'snowfields, glaciers, frozen open land',
    'shore': "a beach, a riverbank or lakeside: the water's edge",
    'swamp': 'marsh, bog, fen, mire',
    'volcanic': 'open volcanic land: ash, lava flows, a volcano',
    'cave': 'a natural cave, cavern or tunnel underground',
    'ice_cave': 'a cave of ice',
    'lava_cave': 'a cave with lava in it',
    'mine': 'a dug mine: shafts, tunnels, ore, timbers',
    'crypt': 'a tomb, catacomb, burial vault or barrow',
    'sewer': 'sewers and drains under a town',
    'dungeon': 'built underground: cells, prisons, cellars, vaults, underground halls',
    'web': 'a lair hung thick with giant spider webs',
    'necropolis': 'a city of the dead: open streets of tombs and mausoleums',
    'stones': 'a ring of standing stones under the sky',
    'camp': 'a camp: tents, a campfire, an encampment',
    'garden': 'a cultivated garden, orchard or park',
    'ruins': 'crumbling ruins open to the sky',
    'terrace': 'terraces cut in steps into a slope',
}

# the looks only the world decides (water and the like), as JEV is told them for a zone's summary
MORE_LOOKS = {
    'water_swim': 'shallow water you wade or swim', 'water_noswim': 'deep open water you need a boat for',
    'underwater': 'under the water: a sunken place', 'flying': 'open air, high up', 'drow': 'a drow city in a great cavern',
    'road': 'a road through open land', 'trail': 'a trail', 'air': 'open air',
}

# a zone as a whole: do its rooms' looks show its setting?
ZONE_FIT = {
    'right': "the looks drawn suit the zone's setting",
    'partly': 'the looks mostly suit it, but a notable share of its rooms are drawn with a look that does not',
    'generic': 'the zone has a distinctive setting (a city of some race, another plane, a special kind of place) '
               'that none of the looks shows: its rooms are drawn as ordinary caves, rooms or country',
    'wrong': 'most of the zone is drawn with looks that contradict its setting',
}
SETTINGS = {
    'town': 'an ordinary human town, village or city', 'castle': 'a castle, keep or fortress',
    'wilds': 'ordinary countryside: fields, woods, hills, mountains, rivers', 'dungeon': 'an ordinary dungeon, cave system or mine',
    'tomb': 'tombs, crypts, the dead', 'tower': "a wizard's tower or magical academy", 'temple': 'a temple, cathedral or monastery',
    'drow': 'a dark elf (drow) city in the Underdark', 'dwarf': 'a dwarven hold or mine-city', 'elf': 'an elven city or village among trees',
    'orc': 'an orc, goblin or ogre warren or camp', 'underdark': 'the Underdark: mind flayers, deep caverns, alien things',
    'hell': 'a hell, abyss or demon realm', 'plane': 'another plane: chaos, elemental, astral, the heavens, a dream',
    'olympus': 'the home of gods', 'fire': 'a land of fire, lava or volcanoes', 'ice': 'a frozen land of ice and snow',
    'desert': 'a desert, pyramid or oasis', 'sea': 'the sea, islands, ships or the coast', 'sunken': 'a sunken or underwater place',
    'swamp': 'a swamp or marsh', 'jungle': 'a jungle', 'machine': 'a clockwork, forge or industrial place',
    'arena': 'an arena or games', 'haunted': 'a haunted house or cursed place', 'garden': 'a garden or paradise',
    'other': 'none of these',
}

# a screenshot of a room as /play draws it, against the room's words and its zone's setting
SHOT_FIT = {
    'good': 'the picture shows this place, in keeping with its zone',
    'wrong_place': 'the wrong kind of place: indoors for outdoors, a cave for a building, land for water, a house for a cavern...',
    'wrong_style': "the right kind of place, but its style, furnishings or culture do not suit the zone (a homely house's "
                   "furniture in a castle, a temple, a tower or another plane; human things in an elven, dwarven or alien place)",
    'bare': 'the right kind of place, but bare and generic: nothing the words name is shown',
    'unreadable': 'too dark, blocked or broken to tell',
}

# the bodies creatures are drawn with, as JEV is told them (a person's models and the skeletons are
# one choice each: which one is the gear's business, not the body's)
BODIES = {
    'person': 'a person: human, elf, dwarf, halfling, orc, goblin warrior or any humanoid in clothes or armour',
    'skeleton': 'an animated skeleton',
    'zombie_m': 'a zombie, ghoul or walking corpse',
    'ghost': 'a ghost, spirit, wraith, spectre or shade',
    'goblin_m': 'a small goblin', 'kobold': 'a kobold', 'imp': 'an imp or small devil',
    'ogre': 'an ogre or giant', 'troll': 'a troll', 'yeti': 'a yeti or sasquatch', 'minotaur': 'a minotaur',
    'demon': 'a demon', 'fiend': 'a great fiend: a pit fiend, balor or demon lord',
    'elemental': 'an elemental, djinn or efreeti', 'mindflayer': 'a mind flayer', 'overmind': 'a master mind flayer',
    'beholder': 'a beholder: a floating eye', 'horror': 'a tentacled horror: octopus, otyugh, aberration',
    'skull': 'a floating skull or small hovering machine', 'myconid': 'a mushroom man',
    'treant': 'a treant: a walking tree', 'tree': 'a tree or plant that does not walk',
    'proc:slime': 'an ooze, slime, jelly or pudding', 'prop:chest': 'a mimic or an object come to life',
    'wolf': 'a wolf, dog, hound, jackal or fox', 'bear': 'a bear', 'cat': 'a small cat', 'lion': 'a big cat: lion, tiger, panther',
    'deer': 'a deer, stag, elk or antelope', 'horse': 'a horse, pony, mule or donkey', 'unicorn': 'a unicorn or pegasus',
    'camel': 'a camel', 'cow': 'a cow, bull or ox', 'pig': 'a pig or boar', 'sheep': 'a sheep or goat', 'rabbit': 'a rabbit or hare',
    'rat': 'a rat or mouse', 'rat_king': 'a giant rat lord', 'q_bat': 'a bat',
    'bird': 'a small or middling bird', 'eagle': 'an eagle, hawk or vulture', 'roc': 'a roc: a giant bird', 'chick': 'a chick or duckling',
    'penguin': 'a penguin',
    'snake': 'a snake', 'serpent': 'a great serpent or sea serpent', 'lizard': 'a lizard or salamander', 'crocodile': 'a crocodile or alligator',
    'turtle': 'a turtle or tortoise', 'frog': 'a frog or toad',
    'dragon': 'a dragon, drake or wyvern', 'frost_wyrm': 'a frost dragon', 'q_dragon': 'a small dragon or dragonet',
    'spider': 'a spider', 'spider_queen': 'a giant spider queen', 'scorpion': 'a scorpion', 'beetle': 'a beetle or crawling insect',
    'wasp': 'a wasp, bee or flying insect', 'stick_mother': 'a giant stick insect or mantis', 'crab': 'a crab or lobster',
    'fish': 'a fish', 'shark': 'a shark', 'whale': 'a whale', 'ray': 'a ray or manta', 'clam': 'a clam or oyster',
}


def family(drawn):
    if drawn.startswith('person:'):
        return 'person'
    if drawn.startswith('undead:'):
        return 'skeleton'
    if drawn.startswith('prop:'):
        return 'prop:chest'
    if drawn in ('q_slime',):
        return 'proc:slime'
    return drawn


def ask(state, question, criteria, tries=4):
    req_body = {'model': MODEL, 'state': state,
                'questions': {'q': {'type': 'choice', 'instructions': question, 'criteria': criteria}}}
    headers = {'Content-Type': 'application/json'}
    # a picture (state '_image': a path to a JPEG): sent as an image asset the state refers to,
    # not as text (a data: URI in the state is read as so many characters, never seen)
    if state.get('_image'):
        import base64
        import uuid
        ref = f'img-{uuid.uuid4()}'
        path = state['_image']
        req_body['state'] = {**{k: v for k, v in state.items() if k != '_image'}, 'screenshot': ref}
        req_body['assets'] = {ref: {'type': 'image', 'format': 'jpg', 'data_base64': base64.b64encode(open(path, 'rb').read()).decode()}}
        headers['TypeSafe-Danger-Zone-Images'] = 'true'
    body = json.dumps(req_body).encode()
    if os.environ.get('TYPESAFE_API_KEY'):
        headers['Authorization'] = 'Bearer ' + os.environ['TYPESAFE_API_KEY']
    for i in range(tries):
        try:
            req = urllib.request.Request(URL, data=body, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.loads(r.read())
            a = res['answers']['q']
            return {'choice': a['choice'], 'confidence': a.get('confidence'), 'p': a.get('probabilities', {}),
                    'tokens': res.get('usage', {}).get('input_tokens', 0)}
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403, 422):
                raise SystemExit(f'JEV refused the request ({e.code}): {e.read()[:300]!r}')
            time.sleep(2 ** i)
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
            time.sleep(2 ** i)
    return None


def run(items, question, criteria, cache_name, workers=8):
    """items: {id: state}. Returns {id: answer}, asking only what the cache lacks."""
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, cache_name)
    cache = json.load(open(path)) if os.path.exists(path) else {}
    todo = [k for k in items if str(k) not in cache]
    print(f'{len(items)} to judge, {len(items) - len(todo)} already answered, asking {len(todo)}')
    done = 0
    with concurrent.futures.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(ask, items[k], question, criteria): k for k in todo}
        for f in concurrent.futures.as_completed(futs):
            ans = f.result()
            if ans:
                cache[str(futs[f])] = ans
            done += 1
            if done % 200 == 0:
                json.dump(cache, open(path, 'w'))
                print(f'  {done}/{len(todo)}')
    json.dump(cache, open(path, 'w'))
    return cache


def disagreements(items, answers, current):
    out = []
    for k, now in current.items():
        a = answers.get(str(k))
        if not a or a['choice'] == now:
            continue
        if (a['confidence'] or 0) >= SURE and a['p'].get(now, 0) <= UNLIKELY:
            out.append((k, now, a['choice'], a['confidence']))
    return out


async def load_rooms(zone):
    import logging
    logging.disable(logging.WARNING)
    from config import Config
    from world import World
    world = World(Config())
    await world.load()
    rooms = [r for r in world.rooms.values() if r.look in LOOKS]
    if zone is not None:
        rooms = [r for r in rooms if getattr(getattr(r, 'zone', None), 'number', None) == zone]
    return rooms


def rooms_mode(zone, limit):
    rooms = asyncio.run(load_rooms(zone))[:limit]
    items = {r.vnum: {'zone': getattr(getattr(r, 'zone', None), 'name', ''), 'room': r.name,
                      'description': ' '.join(str(r.description or '').split())[:900]} for r in rooms}
    answers = run(items, 'Which of these looks should this room be drawn with, going by its own name and description?',
                  LOOKS, 'jev_rooms.json')
    current = {r.vnum: r.look for r in rooms}
    why = {r.vnum: getattr(r, 'look_why', None) for r in rooms}
    bad = disagreements(items, answers, current)
    by_zone = collections.defaultdict(list)
    for k, now, pick, conf in bad:
        by_zone[items[k]['zone']].append((k, now, pick, conf))
    lines = ['# JEV review: room looks', '',
             f'JEV judged {len(answers)} rooms against the look the game draws. Listed: the {len(bad)} where it',
             f'is at least {SURE:.0%} sure of another look and gives the drawn one {UNLIKELY:.0%} or less.',
             'Nothing is changed by this list; `stated` rooms were set by hand or by the build-out.', '']
    for zn, rows in sorted(by_zone.items(), key=lambda kv: -len(kv[1])):
        lines.append(f'## {zn or "?"} ({len(rows)})')
        lines.append('')
        lines.append('| room | name | drawn | JEV | sure | set by |')
        lines.append('|---|---|---|---|---|---|')
        for k, now, pick, conf in sorted(rows):
            lines.append(f'| {k} | {items[k]["room"]} | {now} | {pick} | {conf:.2f} | {why[k] or "rules"} |')
        lines.append('')
    return report('ROOMS', lines, answers, bad)


async def load_zones(zone):
    import logging
    logging.disable(logging.WARNING)
    from config import Config
    from world import World
    world = World(Config())
    await world.load()
    by = collections.defaultdict(list)
    for r in world.rooms.values():
        z = getattr(r, 'zone', None)
        n = getattr(z, 'number', None)
        if n is not None and (zone is None or n == zone):
            by[(n, getattr(z, 'name', ''))].append(r)
    return by


def zone_state(name, rooms):
    looks = collections.Counter(r.look for r in rooms)
    meaning = {**LOOKS, **MORE_LOOKS}
    names = list(dict.fromkeys(r.name for r in sorted(rooms, key=lambda r: r.vnum)))
    step = max(1, len(names) // 40)
    descs = [r for r in sorted(rooms, key=lambda r: r.vnum) if r.description][::max(1, len(rooms) // 6)][:6]
    return {'zone': name, 'rooms': len(rooms),
            'drawn as': [f'{n} rooms: {k} ({meaning.get(k, k)})' for k, n in looks.most_common()],
            'room names': names[::step][:40],
            'some rooms': [f'{r.name}: ' + ' '.join(str(r.description).split())[:260] for r in descs]}


def zones_mode(zone):
    by = asyncio.run(load_zones(zone))
    by = {k: v for k, v in by.items() if len(v) >= 3 and k[0] not in (0, 12)}   # not Limbo or the God Rooms
    items = {f'{n}': zone_state(name, rooms) for (n, name), rooms in by.items()}
    fit = run(items, 'Do the looks this zone\'s rooms are drawn with show its setting? Judge the zone as a whole, '
              'by its name, its rooms\' names and words, against what is drawn.', ZONE_FIT, 'jev_zones_fit.json')
    setting = run(items, "What is this zone's setting?", SETTINGS, 'jev_zones_setting.json')
    rows = []
    for (n, name), rooms in sorted(by.items()):
        f, st = fit.get(str(n)), setting.get(str(n))
        if not f:
            continue
        top = ', '.join(f'{k} {c}' for k, c in collections.Counter(r.look for r in rooms).most_common(4))
        rows.append((f['choice'], f.get('confidence') or 0, n, name, len(rooms), st and st['choice'], top))
    order = {'wrong': 0, 'generic': 1, 'partly': 2, 'right': 3}
    rows.sort(key=lambda r: (order[r[0]], -r[1]))
    lines = ['# JEV review: zones', '',
             'For each zone as a whole, JEV judged whether the looks its rooms are drawn with show its setting',
             f'({len(rows)} zones). Worst first. Nothing is changed by this list.', '',
             '| verdict | sure | zone | name | rooms | setting | drawn (top looks) |', '|---|---|---|---|---|---|---|']
    for v, c, n, name, k, st, top in rows:
        lines.append(f'| {v} | {c:.2f} | {n} | {name} | {k} | {st} | {top} |')
    answers = {**{'f' + k: v for k, v in fit.items()}, **{'s' + k: v for k, v in setting.items()}}
    return report('ZONES', lines, answers, [r for r in rows if r[0] != 'right'])


def shots_mode(folder):
    shots = {int(f[:-4]): os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.jpg') and f[:-4].isdigit()}
    by = asyncio.run(load_zones(None))
    room_of = {r.vnum: (n, name, r) for (n, name), rooms in by.items() for r in rooms}
    setting_cache = os.path.join(OUT, 'jev_zones_setting.json')
    setting = json.load(open(setting_cache)) if os.path.exists(setting_cache) else {}
    items = {}
    for v, path in shots.items():
        if v not in room_of:
            continue
        zn, zname, r = room_of[v]
        st = setting.get(str(zn), {}).get('choice')
        # (keyed by the shot's time too: a room shot again after a fix is asked again)
        items[f'{v}@{int(os.path.getmtime(path))}'] = {'zone': zname, 'zone setting': SETTINGS.get(st, st) if st else None, 'room': r.name,
                    'description': ' '.join(str(r.description or '').split())[:600],
                    '_image': path}
    answers = run(items, '`screenshot` is the room as the game draws it, seen from above (the small figure is the player). '
                  'Does the picture show this room, in keeping with its zone?', SHOT_FIT, 'jev_shots.json', workers=4)
    rows = []
    for key, a in answers.items():
        if key not in items:
            continue              # an older shot of the room
        v = int(key.split('@')[0])
        zn, zname, r = room_of[v]
        rows.append((a['choice'], a.get('confidence') or 0, zn, zname, v, r.name, r.look))
    order = {k: i for i, k in enumerate(['wrong_place', 'wrong_style', 'bare', 'unreadable', 'good'])}
    rows.sort(key=lambda r: (order.get(r[0], 9), -r[1]))
    lines = ['# JEV review: rooms as drawn', '',
             f'JEV looked at {len(rows)} screenshots of rooms in /play, each against its own words and its zone\'s setting.',
             'Worst first. Nothing is changed by this list.', '',
             '| verdict | sure | zone | room | name | look |', '|---|---|---|---|---|---|']
    for v, c, zn, zname, vn, name, look in rows:
        lines.append(f'| {v} | {c:.2f} | {zn} {zname} | {vn} | {name} | {look} |')
    return report('SHOTS', lines, answers, [r for r in rows if r[0] != 'good'])


def creatures_mode(limit):
    out = subprocess.run(['node', os.path.join(HERE, 'qc_bestiary.mjs'), '--json'], capture_output=True, text=True, check=True)
    mobs = json.loads(out.stdout)[:limit]
    items = {m['pv']: {'name': m['short'] or m['name'], 'keywords': m['name'], 'description': m['long']} for m in mobs}
    answers = run(items, 'Which of these bodies should this creature be drawn with, going by its name and description?',
                  BODIES, 'jev_creatures.json')
    current = {m['pv']: family(m['drawn']) for m in mobs}
    bad = disagreements(items, answers, current)
    lines = ['# JEV review: creature bodies', '',
             f'JEV judged {len(answers)} creatures against the body the game draws. Listed: the {len(bad)} where it',
             f'is at least {SURE:.0%} sure of another body and gives the drawn one {UNLIKELY:.0%} or less.',
             'Nothing is changed by this list.', '',
             '| mob | name | drawn | JEV | sure |', '|---|---|---|---|---|']
    for k, now, pick, conf in sorted(bad, key=lambda r: (r[1], r[2], r[0])):
        lines.append(f'| {k} | {items[k]["name"]} | {now} | {pick} | {conf:.2f} |')
    return report('CREATURES', lines, answers, bad)


def report(what, lines, answers, bad):
    tokens = sum(a.get('tokens', 0) for a in answers.values())
    lines += ['', f'_{tokens:,} input tokens over all answers (about ${tokens * 0.042 / 1e6:.2f} at $0.042 per million)._']
    path = os.path.join(ROOT, 'docs', f'JEV_REVIEW_{what}.md')
    open(path, 'w').write('\n'.join(lines) + '\n')
    print(f'{len(bad)} to review -> {os.path.relpath(path, ROOT)}; {tokens:,} input tokens')
    return 0


def main(argv):
    what = argv[0] if argv else 'rooms'
    zone = int(argv[argv.index('--zone') + 1]) if '--zone' in argv else None
    limit = int(argv[argv.index('--limit') + 1]) if '--limit' in argv else None
    if what == 'zones':
        return zones_mode(zone)
    if what == 'shots':
        return shots_mode(argv[1])
    return rooms_mode(zone, limit) if what == 'rooms' else creatures_mode(limit)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
