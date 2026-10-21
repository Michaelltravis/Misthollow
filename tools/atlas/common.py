"""Shared pieces of the atlas tools: loading the atlas and our world, room-name likeness, and the
hand-kept overrides (world/atlas/overrides.json) that the owner's review edits."""
import difflib
import glob
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ATLAS_DIR = os.path.join(ROOT, 'world', 'atlas')
ZONES_DIR = os.path.join(ROOT, 'world', 'zones')
# where the tools write (a test points this at a scratch folder to compare without overwriting)
OUT_DIR = os.environ.get('ATLAS_OUT') or ATLAS_DIR
# the last commit with our world as it was before the re-lay: the matcher and the builder read
# "our rooms" from it, so they give the same answer after world/zones has been rebuilt
PRE_RELAY_REV = 'c6bcadb'
COMPASS = ('north', 'east', 'south', 'west', 'up', 'down')
OPPOSITE = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east', 'up': 'down', 'down': 'up'}
STEP = {'north': (0, 1), 'south': (0, -1), 'east': (1, 0), 'west': (-1, 0)}   # atlas axes: north is +y

# atlas terrain -> the game's sector types (new rooms only; ours keep their own)
SECTOR = {'inside': 'inside', 'city': 'city', 'forest': 'forest', 'field': 'field',
          'shallow water': 'water_swim', 'deep water': 'water_noswim', 'hills': 'hills',
          'mountain': 'mountain', 'unknown': 'inside'}
# names that say a room is under a roof or under ground, whatever the atlas coded it (it coded
# the Tunnel of Sticks as forest and the Orc Tunnels as hills)
UNDER = re.compile(r'\b(tunnel|tunnels|cave|caves|cavern|caverns|mine|mines|mined|shaft|crypt|tomb|tombs|'
                   r'catacomb|catacombs|sewer|sewers|dungeon|cell|cellar|vault|passage|passageway|corridor|'
                   r'hall|hallway|chamber|room|stair|stairs|stairway|staircase|labyrinth|maze|grotto|lair|'
                   r'burrow|pit|undercroft|basement|kitchen|bedroom|library|closet|study|office|shop|store|'
                   r'tavern|inn|bar|temple|chapel|church|cathedral|shrine|guild|barracks|armoury|armory)\b')
WATER_SECTORS = ('water_swim', 'water_noswim', 'water_surface')


def norm(name):
    """A room name reduced for comparing: lower case, Midgaard read as Garathorm, small words and
    punctuation gone."""
    s = (name or '').lower().replace('midgaard', 'garathorm')
    s = re.sub(r'[‐-―]', '-', s)
    s = re.sub(r"[^a-z0-9' -]+", ' ', s)
    s = re.sub(r"\b(the|a|an|of|in|on|at|to|by|and)\b", ' ', s)
    return ' '.join(s.replace("'", '').split())


def likeness(a, b):
    """0..1: how alike two room names are (spelling and shared words)."""
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    wa, wb = set(a.split()), set(b.split())
    jac = len(wa & wb) / len(wa | wb) if wa | wb else 0
    return max(ratio, jac)


def load_atlas():
    with open(os.path.join(ATLAS_DIR, 'bedlam.json'), encoding='utf-8') as f:
        atlas = json.load(f)
    atlas['rooms'] = {int(v): r for v, r in atlas['rooms'].items()}
    atlas['areas'] = {int(a): v for a, v in atlas['areas'].items()}
    return atlas


def _zone_files(rev):
    """(path, text) of every zone file: the working tree's, or a commit's."""
    if rev is None:
        for path in sorted(glob.glob(os.path.join(ZONES_DIR, 'zone_*.json'))):
            with open(path, encoding='utf-8') as f:
                yield path, f.read()
        return
    import subprocess
    names = subprocess.run(['git', 'ls-tree', '--name-only', rev, 'world/zones/'], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.split()
    for name in sorted(n for n in names if re.match(r'world/zones/zone_\d+\.json$', n)):
        text = subprocess.run(['git', 'show', f'{rev}:{name}'], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout
        yield os.path.join(ROOT, name), text


def load_world(rev=None):
    """Our zones: {zone number: zone dict} and {vnum: room} where each room carries `_zone`, a
    plain `_name` and `_sector` (zones 90-160 write `title` and `terrain`), and `_exits`
    {direction: vnum} for the compass ways. `rev`: read them as they were at that commit
    (PRE_RELAY_REV: our world before the re-lay) instead of the working tree."""
    zones, rooms = {}, {}
    for path, text in _zone_files(rev):
        z = json.loads(text)
        z['_file'] = os.path.relpath(path, ROOT).replace(os.sep, '/')   # (the same on Windows)
        zones[z['number']] = z
        for key, r in (z.get('rooms') or {}).items():
            vnum = int(r.get('vnum', key))
            r['_zone'] = z['number']
            r['_name'] = (r.get('name') or r.get('title') or '').strip()
            r['_sector'] = r.get('sector_type') or r.get('terrain') or ''
            ex, named = {}, {}
            for d, e in (r.get('exits') or {}).items():
                to = e.get('to_room') if isinstance(e, dict) else e
                try:
                    to = int(to)
                except (TypeError, ValueError):
                    continue
                (ex if d in COMPASS else named)[d] = to
            r['_exits'], r['_named_exits'] = ex, named
            rooms[vnum] = r
    return zones, rooms


def load_overrides():
    path = os.path.join(ATLAS_DIR, 'overrides.json')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def write_json(path, data, rows=None):
    """JSON with one entry per line under the `rows` keys (readable diffs), else indented."""
    with open(path, 'w', encoding='utf-8') as f:
        if not rows:
            json.dump(data, f, indent=1, ensure_ascii=False)
            f.write('\n')
            return
        f.write('{\n')
        keys = list(data.keys())
        for i, k in enumerate(keys):
            v = data[k]
            end = ',\n' if i < len(keys) - 1 else '\n'
            if k in rows and isinstance(v, dict):
                body = ',\n'.join(f' {json.dumps(str(kk))}: {json.dumps(vv, ensure_ascii=False)}' for kk, vv in v.items())
                f.write(f'{json.dumps(k)}: {{\n{body}\n}}{end}')
            elif k in rows and isinstance(v, list):
                body = ',\n'.join(f' {json.dumps(vv, ensure_ascii=False)}' for vv in v)
                f.write(f'{json.dumps(k)}: [\n{body}\n]{end}')
            else:
                f.write(f'{json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}{end}')
        f.write('}\n')


def load_content(zones):
    """What our zones put in their rooms: {room vnum: {'mobs': [vnum...], 'objs': [vnum...]}}, and
    every creature and item prototype by vnum. Rooms place them with `mob_resets`/`obj_resets`;
    a few zones list zone-wide `resets` (two spellings); zones 90-160 keep creatures in
    `mobiles`."""
    import collections as _c
    placed = _c.defaultdict(lambda: {'mobs': [], 'objs': []})
    mobs, objs = {}, {}

    def vn(x):
        try:
            return int(x.get('vnum') if isinstance(x, dict) else x)
        except (TypeError, ValueError):
            return None
    for z in zones.values():
        for key in ('mobs', 'mobiles'):
            for k, m in (z.get(key) or {}).items():
                v = vn(m) or int(k)
                mobs[v] = m
        for k, o in (z.get('objects') or {}).items():
            objs[vn(o) or int(k)] = o
        for k, r in (z.get('rooms') or {}).items():
            v = int(r.get('vnum', k))
            for x in r.get('mob_resets') or []:
                if vn(x) is not None:
                    placed[v]['mobs'].append(vn(x))
            for x in r.get('obj_resets') or []:
                if vn(x) is not None:
                    placed[v]['objs'].append(vn(x))
        for rs in z.get('resets') or []:
            kind = rs.get('type') or {'M': 'mob', 'O': 'obj'}.get(rs.get('command'))
            room = rs.get('room') or rs.get('room_vnum')
            what = rs.get('vnum') or rs.get('mob_vnum') or rs.get('obj_vnum')
            if kind in ('mob', 'obj') and room and what:
                placed[int(room)]['mobs' if kind == 'mob' else 'objs'].append(int(what))
    return placed, mobs, objs


def load_population(placed, mobs):
    """Fold in who world/population puts where (src/population.py applies it when the game loads,
    after the zone files): its creatures join `mobs`, its spawns, fill, patrols' first rooms and
    bosses join `placed`. Returns the vnums it places as bosses, and the zones it says want none
    ({zone: why})."""
    bosses, no_boss = set(), {}
    for path in sorted(glob.glob(os.path.join(ROOT, 'world', 'population', 'zone_*.json'))):
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        if d.get('no_boss'):
            no_boss[int(d['zone'])] = d['no_boss']
        for k, c in (d.get('creatures') or {}).items():
            mobs[int(k)] = {**(mobs.get(int(k)) or {}), **c}
            if c.get('rank') == 'boss':
                bosses.add(int(k))
        for key in ('spawns', 'fill'):
            for sp in d.get(key) or []:
                for rv in sp.get('rooms') or []:
                    placed[int(rv)]['mobs'].append(int(sp['vnum']))
        for pt in d.get('patrols') or []:
            if pt.get('route'):
                placed[int(pt['route'][0])]['mobs'].append(int(pt['vnum']))
        for b in d.get('bosses') or []:
            placed[int(b['room'])]['mobs'].append(int(b['vnum']))
            bosses.add(int(b['vnum']))
    return bosses, no_boss


def carried(mob):
    """The items a creature carries, wears or drops (its inventory, equipment and loot tables)."""
    out = []
    for key in ('inventory', 'equipment', 'loot_table', 'boss_loot_table', 'equipment_rolls'):
        xs = mob.get(key) or []
        for x in (xs.values() if isinstance(xs, dict) else xs):
            try:
                out.append(int(x.get('vnum') if isinstance(x, dict) else x))
            except (TypeError, ValueError):
                pass
    return out


def level_of(mob):
    try:
        return int(mob.get('level') or 0)
    except (TypeError, ValueError):
        return 0


def is_boss(vnum, mob, boss_vnums=()):
    sp = mob.get('special')
    return bool(mob.get('boss_config') or vnum in boss_vnums or sp == 'boss'
                or (isinstance(sp, dict) and sp.get('type') == 'boss') or 'boss' in (mob.get('flags') or []))


def zone_boss_vnums():
    """Mob vnums the zone-boss table names (src/bosses.py ZONE_BOSS_DAMAGE)."""
    text = open(os.path.join(ROOT, 'src', 'bosses.py'), encoding='utf-8').read()
    start = text.find('ZONE_BOSS_DAMAGE = {')
    body = text[start:text.find('}', start)]
    return {int(x) for x in re.findall(r'^\s*(\d+)\s*:', body, re.M)}
