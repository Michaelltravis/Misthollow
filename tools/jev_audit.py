"""A second opinion on how the world is drawn, from JEV (TypeSafe's decision model): for every room,
which look its own words describe; for every creature, which body. JEV picks from the game's own
options and says how sure it is, so the report lists only the places where it is sure the game
drew something else. It changes nothing: each one is for a person to judge (a room or creature
judged right as it is goes in ACCEPT, a wrong one is fixed where it is decided: world/looks.json
for rooms, world3d/bestiary.js for creatures).

    python3 tools/jev_audit.py rooms [--zone N] [--limit N]
    python3 tools/jev_audit.py creatures [--limit N]

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
    body = json.dumps({'model': MODEL, 'state': state,
                       'questions': {'q': {'type': 'choice', 'instructions': question, 'criteria': criteria}}}).encode()
    headers = {'Content-Type': 'application/json'}
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
    return rooms_mode(zone, limit) if what == 'rooms' else creatures_mode(limit)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
