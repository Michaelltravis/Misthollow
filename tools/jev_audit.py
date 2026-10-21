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

# a second opinion on a case let stand by hand: JEV is shown the reviewer's reason with the case
FAIR = {'fair': 'the reason holds: what is drawn is a fair way to show this', 'unfair': 'the reason does not hold: it should be drawn differently'}

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
        nows = now if isinstance(now, set) else {now}     # (a room drawn as more than one look at once)
        a = answers.get(str(k))
        if not a or a['choice'] in nows:
            continue
        if (a['confidence'] or 0) >= SURE and all(a['p'].get(n, 0) <= UNLIKELY for n in nows):
            out.append((k, '/'.join(sorted(nows)), a['choice'], a['confidence']))
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
    # (an indoor room of a castle-styled zone is drawn as a castle's: zone_tone.py interior)
    # (and a snowfield whose words name a wood or a mountainside is drawn with trees through it or
    # cliffs round it: room_looks.py SNOW_WOOD, SNOW_PEAK)
    from room_looks import SNOW_WOOD, SNOW_PEAK

    def drawn(r):
        text = f'{r.name} {r.description}'
        if r.look == 'inside' and (getattr(r, 'tone', None) or {}).get('interior') == 'castle':
            return {'inside', 'castle'}
        if r.look == 'snow':
            return {'snow'} | ({'forest'} if SNOW_WOOD.search(text) else set()) | ({'mountain'} if SNOW_PEAK.search(text) else set())
        return {r.look}
    current = {r.vnum: drawn(r) for r in rooms}
    why = {r.vnum: getattr(r, 'look_why', None) for r in rooms}
    bad = disagreements(items, answers, current)
    # reviewed and accepted as they are, each with its reason (tools/audit/accepted.json)
    acc_path = os.path.join(HERE, 'audit', 'accepted.json')
    accepted = (json.load(open(acc_path)).get('rooms') or {}) if os.path.exists(acc_path) else {}
    taken = [b for b in bad if str(b[0]) in accepted]
    # (each one let stand goes back to JEV with its reason; one it does not hold fair is listed again)
    fair = run({k: {**items[k], 'drawn as': ', '.join(sorted(now)), 'why it is drawn so': accepted[str(k)]} for k, now, _p, _c in taken},
               '`drawn as` is the look the game draws this room with and `why it is drawn so` a reviewer\'s reason for '
               'letting it stand against another pick. Does the reason hold?', FAIR, 'jev_rooms_fair.json')
    unfair = {int(k) for k, a in fair.items() if a['choice'] == 'unfair' and int(k) in {b[0] for b in taken}}
    taken = [b for b in taken if b[0] not in unfair]
    bad = [b for b in bad if str(b[0]) not in accepted or b[0] in unfair]
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
    lines += [f'## Accepted as they are ({len(taken)})', '',
              f'JEV was shown each with its reason and held it fair ({len(taken)} of {len(taken) + len(unfair)}); those it did not are listed above.', '',
              '| room | name | drawn | JEV | why |', '|---|---|---|---|---|']
    lines += [f'| {k} | {items[k]["room"]} | {now} | {pick} | {accepted[str(k)]} |' for k, now, pick, conf in sorted(taken)]
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
    # (keyed by what is drawn too: a zone whose looks change is asked again)
    import hashlib
    states = {n: zone_state(name, rooms) for (n, name), rooms in by.items()}
    for (n, name), rooms in by.items():
        styles = collections.Counter((getattr(r, 'tone', None) or {}).get('interior') for r in rooms if r.look == 'inside')
        if styles and next(iter(styles)) is not None:
            states[n]['indoor rooms drawn in the style of'] = f'{next(iter(styles))} (not a plain house)'
    items = {f'{n}@' + hashlib.md5(json.dumps(st, sort_keys=True).encode()).hexdigest()[:8]: st for n, st in states.items()}
    key_of = {n: k for k in items for n in [int(k.split('@')[0])]}
    fit = run(items, 'Do the looks this zone\'s rooms are drawn with show its setting? Judge the zone as a whole, '
              'by its name, its rooms\' names and words, against what is drawn.', ZONE_FIT, 'jev_zones_fit.json')
    setting = run(items, "What is this zone's setting?", SETTINGS, 'jev_zones_setting.json')
    rows = []
    for (n, name), rooms in sorted(by.items()):
        f, st = fit.get(key_of.get(n, '')), setting.get(key_of.get(n, ''))
        if not f:
            continue
        top = ', '.join(f'{k} {c}' for k, c in collections.Counter(r.look for r in rooms).most_common(4))
        rows.append((f['choice'], f.get('confidence') or 0, n, name, len(rooms), st and st['choice'], top))
    order = {'wrong': 0, 'generic': 1, 'partly': 2, 'right': 3}
    rows.sort(key=lambda r: (order[r[0]], -r[1]))
    # reviewed and accepted as they are, each with its reason (tools/audit/accepted.json)
    acc_path = os.path.join(HERE, 'audit', 'accepted.json')
    accepted = (json.load(open(acc_path)).get('zones') or {}) if os.path.exists(acc_path) else {}
    lines = ['# JEV review: zones', '',
             'For each zone as a whole, JEV judged whether the looks its rooms are drawn with show its setting',
             f'({len(rows)} zones). Worst first. Nothing is changed by this list.', '',
             '| verdict | sure | zone | name | rooms | setting | drawn (top looks) |', '|---|---|---|---|---|---|---|']
    for v, c, n, name, k, st, top in rows:
        lines.append(f'| {v} | {c:.2f} | {n} | {name} | {k} | {st} | {top} |')
    taken = [r for r in rows if r[0] != 'right' and str(r[2]) in accepted]
    fair = run({key_of[r[2]]: {**items[key_of[r[2]]], 'why it is drawn so': accepted[str(r[2])]} for r in taken},
               '`why it is drawn so` is a reviewer\'s reason for letting this zone\'s looks stand. Does the reason hold?',
               FAIR, 'jev_zones_fair.json')
    asked = {key_of[r[2]] for r in taken}
    unfair = {int(k.split('@')[0]) for k, a in fair.items() if a['choice'] == 'unfair' and k in asked}
    taken = [r for r in taken if r[2] not in unfair]
    lines += ['', f'## Accepted as they are ({len(taken)})', '',
              f'JEV was shown each with its reason and held it fair ({len(taken)} of {len(taken) + len(unfair)}).', '',
              '| zone | name | verdict | why |', '|---|---|---|---|']
    lines += [f'| {r[2]} | {r[3]} | {r[0]} {r[1]:.2f} | {accepted[str(r[2])]} |' for r in taken]
    answers = {**{'f' + k: v for k, v in fit.items() if k in items}, **{'s' + k: v for k, v in setting.items() if k in items}}
    return report('ZONES', lines, answers, [r for r in rows if r[0] != 'right' and (str(r[2]) not in accepted or r[2] in unfair)])


def shots_mode(folder):
    shots = {int(f[:-4]): os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.jpg') and f[:-4].isdigit()}
    by = asyncio.run(load_zones(None))
    room_of = {r.vnum: (n, name, r) for (n, name), rooms in by.items() for r in rooms}
    setting_cache = os.path.join(OUT, 'jev_zones_setting.json')
    setting = json.load(open(setting_cache)) if os.path.exists(setting_cache) else {}
    # (keys are 'zone@state'; any answer for the zone will do: its setting doesn't change with its looks)
    setting = {**{k.split('@')[0]: v for k, v in setting.items()}, **{k: v for k, v in setting.items() if '@' not in k}}
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
    # for every shot not judged good: the look JEV would draw the room with, from the picture and
    # the words together (the report's last column; a pin in world/looks.json is the fix)
    looks = {**LOOKS, 'underwater': MORE_LOOKS['underwater'], 'foundry': 'a clockwork foundry: machines, pipes, furnaces'}
    unsure = {k: v for k, v in items.items() if k in answers and answers[k]['choice'] != 'good'}
    better = run(unsure, '`screenshot` is the room as the game draws it now. Going by its own name and description, '
                 'which of these looks should it be drawn with?', looks, 'jev_shots_look.json', workers=4)
    # for every shot judged bare: the one thing its words name that the picture lacks most, of the
    # things the client can draw (room_features.py), or nothing it could draw
    from room_features import FEATURES
    things = {k: k.replace('_', ' ') for k, *_ in FEATURES}
    things['nothing'] = 'nothing the words name is missing from the picture'
    things['other'] = 'something else, not in this list'
    bare = {k: v for k, v in items.items() if k in answers and answers[k]['choice'] == 'bare'}
    lacking = run(bare, '`screenshot` is the room as the game draws it now. Of the things this room\'s own words name, '
                  'which one is most plainly missing from the picture?', things, 'jev_shots_missing.json', workers=4)
    # and the plain question for each one judged bare: of the things its words name that the game
    # draws (room_features.py), does the picture show them? (bare is a judgement of the whole;
    # this says whether the room's own things are there to be seen)
    shown_q = {'all': 'every one of them can be seen in the picture', 'some': 'some can be seen, some cannot',
               'none': 'none of them can be seen'}
    named = {k: v for k, v in bare.items() if getattr(room_of[int(k.split('@')[0])][2], 'features', None)}
    shown = run({k: {**v, 'things its words name': ', '.join(f['k'].replace('_', ' ') for f in room_of[int(k.split('@')[0])][2].features)}
                 for k, v in named.items()},
                '`screenshot` is the room as the game draws it. Can the things listed in `things its words name` be seen in it?',
                shown_q, 'jev_shots_shown.json', workers=4)
    # and for those whose missing thing is none of the features: which piece of scenery it is
    scenery = {'trees': 'trees or woods', 'rocks': 'rocks, boulders or cliffs', 'river': 'a river, stream or flowing water',
               'waterfall': 'a waterfall', 'lake': 'a lake, pool or still water', 'bridge': 'a bridge', 'boat': 'a boat, ship or dock',
               'gate': 'a gate, door or archway', 'stairs': 'stairs or steps', 'building': 'a building, house or hut',
               'wall': 'a wall, tower or rampart', 'mist': 'mist, fog or smoke', 'ice': 'ice or snow', 'fire': 'fire or lava',
               'webs': 'spider webs', 'roots': 'roots, vines or creepers', 'mirrors': 'mirrors or glass', 'bell': 'a bell',
               'machine': 'machinery, gears or pipes', 'sea_life': 'coral, kelp, shells or fish', 'reeds': 'reeds, rushes or tall grass',
               'path': 'a road, path or track', 'light': 'a glow, light or luminous thing', 'stalls': 'market stalls or wares',
               'nothing': 'nothing the words name is missing', 'other': 'something else'}
    other = {k: v for k, v in bare.items() if (lacking.get(k) or {}).get('choice') == 'other'}
    unlisted = run(other, '`screenshot` is the room as the game draws it now. Of the things this room\'s own words name, '
                   'which one is most plainly missing from the picture?', scenery, 'jev_shots_scenery.json', workers=4)
    rows = []
    for key, a in answers.items():
        if key not in items:
            continue              # an older shot of the room
        v = int(key.split('@')[0])
        zn, zname, r = room_of[v]
        b = better.get(key)
        rows.append((a['choice'], a.get('confidence') or 0, zn, zname, v, r.name, r.look,
                     f"{b['choice']} {b.get('confidence') or 0:.2f}" if b else ''))
    order = {k: i for i, k in enumerate(['wrong_place', 'wrong_style', 'bare', 'unreadable', 'good'])}
    rows.sort(key=lambda r: (order.get(r[0], 9), -r[1]))
    # what is left to fix: a shot judged the wrong place or style, unless JEV's own pick of a look
    # is the one drawn (the look is right: what it wants is more detail) or it was reviewed and
    # accepted (tools/audit/accepted.json, with the reason)
    acc_path = os.path.join(HERE, 'audit', 'accepted.json')
    accepted = (json.load(open(acc_path)).get('shots') or {}) if os.path.exists(acc_path) else {}
    wrong = [r for r in rows if r[0] in ('wrong_place', 'wrong_style')]
    # (an indoor room of a castle-styled zone is drawn as a castle's hall: zone_tone.py interior)
    def drawn_as(r):
        rm = room_of[r[4]][2]
        if r[6] == 'necropolis':
            return {'necropolis', 'city'}            # (a city of the dead is drawn with its own city look)
        return {r[6], 'castle'} if r[6] == 'inside' and (getattr(rm, 'tone', None) or {}).get('interior') == 'castle' else {r[6]}
    confirmed = [r for r in wrong if r[7] and r[7].split()[0] in drawn_as(r)]
    taken = [r for r in wrong if r not in confirmed and str(r[4]) in accepted]
    # a second opinion on each one accepted: JEV sees the shot with the reason it was let stand
    keyed = {k: v for k, v in items.items() if int(k.split('@')[0]) in {r[4] for r in taken}}
    # (keyed by the reason too: a reason reworded is asked again)
    import hashlib
    rkey = lambda k: f"{k}#{hashlib.md5(accepted[k.split('@')[0]].encode()).hexdigest()[:6]}"
    fair = run({rkey(k): {**v, 'why it is drawn so': accepted[k.split('@')[0]]} for k, v in keyed.items()},
               '`screenshot` is the room as the game draws it; `why it is drawn so` is a reviewer\'s reason for letting it stand. '
               'Does the reason hold?', FAIR, 'jev_shots_fair.json', workers=4)
    unfair = {int(k.split('@')[0]) for k, a in fair.items() if k in {rkey(x) for x in keyed} and a['choice'] == 'unfair'}
    todo = [r for r in wrong if r not in confirmed and (r not in taken or r[4] in unfair)]
    taken = [r for r in taken if r[4] not in unfair]
    head = '| verdict | sure | zone | room | name | look | JEV would draw |'
    lines = ['# JEV review: rooms as drawn', '',
             f'JEV looked at {len(rows)} screenshots of rooms in /play, each against its own words and its zone\'s setting',
             f'({dict(collections.Counter(r[0] for r in rows))}). Nothing is changed by this list.', '',
             f'## To fix ({len(todo)})', '', head, '|---|---|---|---|---|---|---|']
    lines += [f'| {r[0]} | {r[1]:.2f} | {r[2]} {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} |' for r in todo]
    lines += ['', f'## The look confirmed ({len(confirmed)})', '',
              "Judged the wrong place or style, but the look JEV would draw is the one drawn: what it wants is detail.", '',
              head, '|---|---|---|---|---|---|---|']
    lines += [f'| {r[0]} | {r[1]:.2f} | {r[2]} {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} |' for r in confirmed]
    lines += ['', f'## Accepted as they are ({len(taken)})', '',
              f'JEV was shown each with its reason and held it fair ({len(taken)} of {len(taken) + len(unfair)}); '
              'those it did not are under To fix.', '', '| room | name | look | why |', '|---|---|---|---|']
    lines += [f'| {r[4]} | {r[5]} | {r[6]} | {accepted[str(r[4])]} |' for r in taken]
    lines += ['', '## Bare: what the words name that the picture lacks', '',
              'Last column: whether JEV can see, in the picture, the things the room\'s words name that the game draws.', '',
              '| room | name | look | missing | drawn features | shown |', '|---|---|---|---|---|---|']
    feats = {r.vnum: [f['k'] for f in (getattr(r, 'features', None) or [])] for _z, _n, r in room_of.values()}
    for key in sorted(bare):
        m = lacking.get(key)
        if not m:
            continue
        v = int(key.split('@')[0])
        sh = shown.get(key)
        u = unlisted.get(key)
        miss = f"{m['choice']} {m.get('confidence') or 0:.2f}" + (f" ({u['choice']} {u.get('confidence') or 0:.2f})" if u else '')
        lines.append(f"| {v} | {room_of[v][2].name} | {room_of[v][2].look} | {miss} | {', '.join(feats.get(v, [])) or '-'} | {sh['choice'] if sh else '-'} |")
    lines += ['', '## All', '', head, '|---|---|---|---|---|---|---|']
    lines += [f'| {r[0]} | {r[1]:.2f} | {r[2]} {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} |' for r in rows]
    return report('SHOTS', lines, answers, todo)


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
