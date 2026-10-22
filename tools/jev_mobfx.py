"""How every boss's abilities look in /play, read by JEV (TypeSafe's decision model) from the
ability's own words: its name, its warning, its area and wind-up, and the creature that uses it.

    python3 tools/jev_mobfx.py            # ask what isn't cached, write world3d/mobfx-table.js and the review
    python3 tools/jev_mobfx.py --dry      # build from the cache only (no requests)
    python3 tools/jev_mobfx.py --limit 10 # ask about the first 10 only (a trial)

JEV only judges; code draws. For each ability one request asks, together:
  delivery   how it reaches its foe (DELIVERY: a weapon blow, a breath, an eruption, a curse...)
  school     its harm's colour (abilityfx.js SCHOOLS)
  impact     what happens where it lands (IMPACT, the recipe's land column)
  growth     what rises from the ground, should the impact be a growth (asked alongside, used then)
  tell       what the body does while it winds up (TELLS)
  intensity  how big it is (a Score: minor .. cataclysmic), which sets sizes, shake and hit-stop
and code turns the answers into a recipe line (line()): always one abilityfx.js accepts. A second
request asks whether that look, told in words, fits what the ability's warning says happens.

What is sure goes into the table; what isn't (a split delivery, an impact JEV hardly prefers, a
look the check doubts) is listed in docs/JEV_REVIEW_MOBFX.md and in the table's MOB_REVIEW, and is
drawn by its kind until a person writes its line into mobfx-hand.js (which always wins). The
mob brain's everyday abilities have hand lines already and are never asked about.

The key: TYPESAFE_API_KEY in the environment (as tools/jev_audit.py). Answers are kept in
tools/audit/out/jev_mobfx.json, keyed by the questions' version, so a run again asks only what
it hasn't, and changing a question asks again.
"""
import concurrent.futures
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from jev_audit import URL, MODEL, OUT  # noqa: E402  (the same service, model and cache folder)

TABLE = os.path.join(ROOT, 'src', 'web_isometric', 'world3d', 'mobfx-table.js')
HAND = os.path.join(ROOT, 'src', 'web_isometric', 'world3d', 'mobfx-hand.js')
REVIEW = os.path.join(ROOT, 'docs', 'JEV_REVIEW_MOBFX.md')
CACHE = os.path.join(OUT, 'jev_mobfx.json')
VERSION = 'v2'           # bump when a question changes: its answers are asked again

# what makes a line sure enough to draw without a person's look (tune on the review)
SURE_DELIVERY = 0.5      # JEV's confidence in how it reaches its foe
SURE_IMPACT = 0.3        # ...and in what happens where it lands (more options, flatter)
FITS = 0.5               # the check: this look fits the warning

DELIVERY = {
    'weapon_strike': 'a blow with a weapon, fist or limb at one foe: a cleave, a smash, a slash, a punch, a kick',
    'bite_claw': 'teeth, claws, fangs, horns, a tail or a sting striking one foe',
    'charge_leap': 'the creature rushes, charges, tramples, leaps or pounces onto its foe',
    'sweep': 'a blow that sweeps all around the creature: a tail sweep, a spinning cleave, a whirl of blades, a stomp that shakes the ground about it',
    'projectile': 'something thrown, shot or spat at one foe that flies to it: a bolt, an orb, a dart, a spear, a boulder, a glob of venom',
    'beam': 'a ray, beam, gaze or bolt of lightning that reaches its target at once, a straight line of light or darkness',
    'breath_cone': 'breath or a spray in a cone in front of the creature: fire breath, a frost breath, web spray, a gout of acid, a cloud breathed out',
    'eruption': 'the ground or air where the foe stands erupts: pillars of fire, spikes, geysers, a pool, roots or hands grasping from below',
    'nova': 'a burst, shockwave, scream, howl or storm spreading outward from the creature itself to everyone near',
    'rain': 'things fall from above onto an area: meteors, hail, falling stones, a rain of arrows, blood or fire',
    'curse': 'a spell laid upon a foe rather than a missile: a curse, hex, fear, word of power, life drain, charm, cocoon, binding, a whispered doubt',
    'self_buff': 'the creature strengthens, shields, heals, hardens or transforms itself',
    'summon': 'the creature calls, raises or summons helpers to fight beside it',
}
SCHOOL = {
    'physical': 'plain force: steel, claws, stone, weight, a blow',
    'fire': 'fire, flame, heat, lava, burning',
    'frost': 'ice, frost, cold, snow, freezing water',
    'lightning': 'lightning, thunder, storm, shock',
    'arcane': 'raw magic, force, the void, starlight, time or space bending',
    'holy': 'holy light, judgement, radiance, the divine',
    'shadow': 'darkness, shadow, fear, madness, the mind',
    'necrotic': 'death, rot, undeath, souls, draining life',
    'nature': 'plants, roots, thorns, beasts, earth that grows',
    'poison': 'venom, acid, disease, plague, toxic gas',
    'sound': 'sound, song, a roar or scream that wounds',
    'blood': 'blood, gore, bleeding, a frenzy of wounds',
}
IMPACT = {
    'hit': 'a plain, sharp impact on the target',
    'blast': 'an explosion with a shockwave and a scorched mark on the ground',
    'burst': 'a burst of glyphs and sparks scattering from the target',
    'pillar': 'a column of energy or light slamming down or rising up on the spot',
    'crack': 'the ground cracks open under a heavy blow, dust thrown up',
    'quake': 'the ground heaves and breaks in a wide circle, stones rising',
    'growth': 'something rises out of the ground at the spot: roots, bones, ice, crystals, bars, thorns, stones or spikes',
    'cloud': 'a lingering cloud of gas, spores, smoke or venom engulfs the spot',
    'freeze': 'the target is frozen: ice crusts over it and spikes of ice rise',
    'shatter': 'shards fly apart: something breaks into pieces',
    'mark': 'a sign hangs over the target and a sigil circles under it: it is marked, cursed or bound',
    'swirl': 'motes or glyphs spiral up around the target, wrapping it',
    'smoke': 'a billow of dark smoke where it lands',
    'implode': 'everything is pulled inward to a dark point that collapses',
    'geyser': 'a jet of energy or liquid bursts straight up from the ground',
    'nova': 'rings of force spread outward across the ground from the spot',
}
GROWTH = {
    'vines': 'vines or roots', 'bones': 'bones or grasping skeletal hands', 'ice': 'ice', 'crystals': 'crystals',
    'bars': 'bars or a cage', 'thorns': 'thorns or brambles', 'stones': 'rocks and stones', 'spikes': 'spikes or blades of metal',
    'spears': 'spears of light',
}
TELL = {
    'rear': 'it rears back or draws itself up tall, chest out, to strike or breathe',
    'crouch': 'it drops low and wide, gathering itself to sweep or spring',
    'coil': 'it coils, head down, tensed to lunge',
    'shudder': 'it trembles and shakes as something builds inside it',
    'gather': 'it raises its hands, staff or head and gathers power, as a spellcaster does',
    'still': 'it goes utterly still and stares, focusing',
}
INTENSITY = [
    'Minor: a quick jab or a small spell, barely more than an ordinary blow',
    'Notable: a strong special attack that hurts one foe noticeably',
    'Major: a devastating blow or spell that can maim, or that hits everyone nearby',
    'Cataclysmic: an ultimate, world-shaking attack meant to wipe out a whole party',
]

# a delivery's body (clip and motion), what gathers, and what flies (abilityfx.js columns)
SHAPE = {
    'weapon_strike': ('chop2', None, 'dust', 'slash'),
    'bite_claw': ('stab', 'lunge', None, 'slash:x'),
    'charge_leap': ('leapchop', 'leap', 'dust', None),
    'sweep': ('spin2', 'spin', 'dust', None),
    'projectile': ('shoot', None, 'gather', 'orb'),
    'beam': ('raise', None, 'flare', 'ray'),
    'breath_cone': ('shoot', None, 'smoke', 'cone'),
    'eruption': ('raise', None, 'sigil', None),
    'nova': ('cheer', None, 'rings', None),
    'rain': ('raise', None, 'glyphs', 'rain'),
    'curse': ('long', None, 'glyphs', 'tether'),
    'self_buff': ('raise', None, 'spiral', None),
    'summon': ('summon', None, 'sigil', None),
}
# what lingers on a creature that strengthens itself, by school
SELF_AURA = {'fire': 'flames', 'frost': 'frost', 'shadow': 'shroud', 'holy': 'halo', 'physical': 'rage', 'nature': 'bark',
             'necrotic': 'ghost', 'poison': 'poison', 'blood': 'bleed', 'sound': 'notes', 'lightning': 'glow', 'arcane': 'runes'}


def line(a):
    """The recipe line for JEV's answers `a` ({delivery, school, impact, growth, tell, intensity, and
    the ability's own radius}): body | cast | travel | land | aura | flags."""
    d, school, size = a['delivery'], a['school'], a['intensity']
    clip, motion, cast, travel = SHAPE[d]
    big = size >= 2
    land = a['impact']
    aura = None
    if d == 'weapon_strike' and big:
        motion = 'slam'
    if d in ('projectile', 'beam', 'breath_cone', 'curse', 'eruption') and school == 'fire' and cast == 'smoke':
        cast = 'embers'
    if d == 'projectile':
        travel = {'frost': 'shards:3', 'physical': 'orb:big', 'necrotic': 'glyph', 'shadow': 'orb'}.get(school, 'orb:big' if big else 'orb')
    if d == 'beam' and school == 'lightning':
        travel = 'skyray'
    if d == 'rain' and school == 'fire':
        travel = 'meteors'
    if d == 'self_buff':
        land, aura = None, SELF_AURA.get(school, 'glow')
    if d == 'summon' and land in ('hit', 'burst', 'blast'):
        land = 'pillar'
    if land == 'growth':
        land = f"growth:{a.get('growth') or 'stones'}"
    elif land and big and land not in ('mark', 'swirl', 'smoke', 'cloud', 'nova'):
        land += '+'
    flags = [school]
    if size == 1:
        flags.append('shake')
    elif size == 2:
        flags += ['shake+'] + (['heavy'] if d in ('weapon_strike', 'bite_claw', 'charge_leap') else [])
    elif size >= 3:
        flags += ['shake+', 'stop', 'flash']
    if d == 'self_buff':
        flags.append('ally')
    # an area's reach, for what spreads over the ground (on a breath it would be the cone's length,
    # and a bolt's flight has none)
    if a.get('radius') and d in ('nova', 'sweep', 'rain', 'eruption', 'charge_leap'):
        flags.append(f"r={a['radius']:g}")
    flags.append(f"tell={a['tell']}")
    body = clip + (f' {motion}' if motion else '')
    return ' | '.join([body, cast or '-', travel or '-', land or '-', aura or '-', ' '.join(flags)])


def told(a):
    """The look, in words, for the check."""
    parts = [f"The creature {TELL[a['tell']].split(': ')[0].replace('it ', '', 1)} while it winds up."]
    parts.append(f"Then: {DELIVERY[a['delivery']].split(':')[0]}, in {SCHOOL[a['school']].split(',')[0]}.")
    if a['delivery'] != 'self_buff':
        imp = IMPACT[a['impact']]
        if a['impact'] == 'growth':
            imp = f"{GROWTH.get(a.get('growth') or 'stones')} rise out of the ground at the spot"
        parts.append(f'Where it lands: {imp}.')
    parts.append(['It is a small effect.', 'It is a strong effect.', 'It is a huge effect that shakes the view.',
                  'It is an overwhelming effect: the view shakes, freezes a moment and flashes.'][a['intensity']])
    return ' '.join(parts)


# ---------------------------------------------------------------- the abilities
def fx_key(label):
    return re.sub(r'[^a-z0-9]+', '_', str(label or '').lower().replace("'", '')).strip('_')


def prototypes():
    """{vnum: creature} from world/zones (a population file may give a boss by its vnum alone)."""
    out = {}

    def visit(o):
        if isinstance(o, dict):
            if o.get('vnum') is not None and o.get('short_desc') and o.get('hp_dice'):
                out[str(o['vnum'])] = o
            for v in o.values():
                visit(v)
        elif isinstance(o, list):
            for v in o:
                visit(v)

    for path in glob.glob(os.path.join(ROOT, 'world', 'zones', '*.json')):
        with open(path, encoding='utf-8') as f:
            visit(json.load(f))
    return out


def boss_abilities():
    """{fx: {label, uses: [{creature, ability}]}} for every boss ability in world/population."""
    out = {}
    protos = prototypes()

    def visit(o, key=None):
        if isinstance(o, dict):
            bc = o.get('boss_config')
            if isinstance(bc, dict):
                o = {**protos.get(str(o.get('vnum') or key), {}), **{k: v for k, v in o.items() if v}}
                who = {'name': o.get('short_desc') or o.get('name') or str(key), 'race': o.get('race'),
                       'level': o.get('level'),
                       'description': ' '.join(f"{o.get('long_desc') or ''} {o.get('description') or ''}".split())[:500]}
                for ab in bc.get('abilities') or []:
                    k = fx_key(ab.get('name'))
                    if k:
                        out.setdefault(k, {'label': ab.get('name'), 'uses': []})['uses'].append({'creature': who, 'ability': ab})
            for k, v in o.items():
                visit(v, k)
        elif isinstance(o, list):
            for v in o:
                visit(v, key)

    for path in sorted(glob.glob(os.path.join(ROOT, 'world', 'population', '*.json'))):
        with open(path, encoding='utf-8') as f:
            visit(json.load(f))
    return out


def hand_keys():
    with open(HAND, encoding='utf-8') as f:
        return set(re.findall(r'^\s+([a-z0-9_]+): \'', f.read(), re.M))


def state_of(item):
    """What JEV is told about one ability: its first use in full, and who else uses it."""
    first = item['uses'][0]
    ab = first['ability']
    area = (f"everyone within {ab.get('radius', 4.5):g} m of the creature" if ab.get('aoe') else 'one foe')
    return {
        'ability': {
            'name': item['label'],
            'warning': ab.get('telegraph') or '',
            'strikes': area,
            'wind_up_seconds': ab.get('cast_time'),
            'can_be_interrupted': bool(ab.get('interruptible')),
            'can_be_dodged': bool(ab.get('dodge')),
            'damage_dice': ab.get('damage_dice'),
        },
        'creature': first['creature'],
        'also_used_by': sorted({u['creature']['name'] for u in item['uses'][1:]})[:6],
    }


def questions():
    return {
        'delivery': {'type': 'choice', 'instructions': (
            'The `ability` is a special attack of the `creature` in a fantasy game, to be animated in 3D. Judging by its '
            '`name` and its `warning` (what players are told is coming), how does it reach its foe?'), 'criteria': DELIVERY},
        'school': {'type': 'choice', 'instructions': (
            'What kind of harm is the `ability` of the `creature`, judging by its `name`, its `warning` and the creature? '
            'This decides the colour of its animation.'), 'criteria': SCHOOL},
        'impact': {'type': 'choice', 'instructions': (
            'When the `ability` of the `creature` lands, which of these effects shows best what its `name` and `warning` say '
            'happens to its target or the ground where it strikes?'), 'criteria': IMPACT},
        'growth': {'type': 'choice', 'instructions': (
            'If something were to rise out of the ground where the `ability` of the `creature` lands, which of these '
            'fits it best?'), 'criteria': GROWTH},
        'tell': {'type': 'choice', 'instructions': (
            'While the `creature` winds up its `ability` (the moment its `warning` describes), what should its body do, '
            'so a player can read what is coming?'), 'criteria': TELL},
        'intensity': {'type': 'score', 'instructions': (
            'How big and dangerous is the `ability`, judging by its name, its warning, its damage dice and whom it strikes?'),
            'criteria': INTENSITY},
    }


CHECK = {'type': 'noul', 'instructions': (
    'The `ability` of the `creature` is to be animated as the `look` describes. Does that animation show what the '
    "ability's `name` and `warning` say happens, closely enough that a player who read the warning would recognise it?"),
    'criteria': {'true': 'the look fits: the same kind of attack, harm and landing the warning promises',
                 'false': 'the look contradicts the warning: a different kind of attack, element or landing'}}


def system_one(state, qs, tries=4):
    body = json.dumps({'model': MODEL, 'state': state, 'questions': qs}).encode()
    headers = {'Content-Type': 'application/json'}
    if os.environ.get('TYPESAFE_API_KEY'):
        headers['Authorization'] = 'Bearer ' + os.environ['TYPESAFE_API_KEY']
    for i in range(tries):
        try:
            req = urllib.request.Request(URL, data=body, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.loads(r.read())
            return res['answers'], res.get('usage', {})
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403, 422):
                raise SystemExit(f'JEV refused the request ({e.code}): {e.read()[:300]!r}')
            time.sleep(2 ** i)
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
            time.sleep(2 ** i)
    return None, None


def judge(item):
    """JEV's answers for one ability, its line and the check's verdict."""
    st = state_of(item)
    ans, use = system_one(st, questions())
    if not ans:
        return None
    pick = {k: ans[k]['choice'] for k in ('delivery', 'school', 'impact', 'growth', 'tell')}
    pick['intensity'] = int(round(ans['intensity']['score']))
    ab = item['uses'][0]['ability']
    pick['radius'] = ab.get('radius') if ab.get('aoe') else None
    look = told(pick)
    chk, use2 = system_one({**st, 'look': look}, {'fits': CHECK})
    return {
        'answers': pick, 'line': line(pick), 'look': look,
        'conf': {k: ans[k].get('confidence') for k in ('delivery', 'school', 'impact', 'tell', 'intensity')},
        'second': {k: sorted(ans[k].get('probabilities', {}).items(), key=lambda x: -x[1])[1:3] for k in ('delivery', 'impact')},
        'fits': chk['fits']['noul'] if chk else None,
        'tokens': (use or {}).get('input_tokens', 0) + (use2 or {}).get('input_tokens', 0),
    }


def sure(j):
    c = j['conf']
    why = []
    if (c['delivery'] or 0) < SURE_DELIVERY:
        why.append(f"delivery {c['delivery']:.2f}")
    if j['answers']['delivery'] != 'self_buff' and (c['impact'] or 0) < SURE_IMPACT:
        why.append(f"impact {c['impact']:.2f}")
    if j['fits'] is None or j['fits'] < FITS:
        why.append(f"check {j['fits'] if j['fits'] is None else round(j['fits'], 2)}")
    return why


# ---------------------------------------------------------------- writing
def write(items, judged):
    keep, review = {}, {}
    for k in sorted(items):
        j = judged.get(k)
        if not j:
            review[k] = ['not asked yet']
            continue
        j['line'] = line(j['answers'])        # (drawn again from the answers: a change to line() needs no asking)
        why = sure(j)
        (review.__setitem__(k, why) if why else keep.__setitem__(k, j))
    q = lambda s: s.replace('\\', '\\\\').replace("'", "\\'")
    out = ['// Written by tools/jev_mobfx.py: do not edit by hand (a line in mobfx-hand.js wins over one here).',
           '// JEV judged each boss ability from its own words (its name, warning, area and creature); code drew the',
           f'// line. {len(keep)} sure; {len(review)} left for a person (MOB_REVIEW, docs/JEV_REVIEW_MOBFX.md), drawn by',
           '// their kind until one writes their line into mobfx-hand.js.',
           'export const MOB_TABLE = {']
    for k, j in keep.items():
        who = items[k]['uses'][0]['creature']['name']
        out.append(f"  {k}: '{q(j['line'])}', // {q(who)}: {j['answers']['delivery']} {j['conf']['delivery']:.2f}, fits {j['fits']:.2f}")
    out.append('};')
    out.append('// boss abilities JEV wasn\'t sure of (drawn by their kind)')
    out.append('export const MOB_REVIEW = [')
    for k in review:
        out.append(f"  '{k}',")
    out.append('];')
    with open(TABLE, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(out) + '\n')

    md = ['# JEV review: boss ability looks', '',
          'tools/jev_mobfx.py asked JEV how each boss ability reaches its foe, its school, what happens where it',
          'lands, the body\'s tell and how big it is, and drew a line from the answers. These are the ones it',
          f'was not sure of (delivery below {SURE_DELIVERY}, impact below {SURE_IMPACT}, or the check below {FITS} that',
          'the look fits the warning). Until a line is written for one in `world3d/mobfx-hand.js`, /play draws it',
          'by its kind. JEV\'s pick and its runners-up are given to start from.', '',
          f'{len(keep)} drawn from JEV, {len(review)} here.', '']
    for k, why in review.items():
        it, j = items[k], judged.get(k)
        ab = it['uses'][0]['ability']
        md.append(f"## {it['label']} (`{k}`)")
        md.append(f"*{it['uses'][0]['creature']['name']}*{' and ' + str(len(it['uses']) - 1) + ' more' if len(it['uses']) > 1 else ''}: "
                  f"\"{ab.get('telegraph', '')}\"")
        md.append(f"- unsure: {', '.join(why)}")
        if j:
            sec = lambda name: ', '.join(f'{n} {p:.2f}' for n, p in j['second'][name])
            md.append(f"- JEV: {j['answers']['delivery']} ({j['conf']['delivery']:.2f}; then {sec('delivery')}), "
                      f"{j['answers']['school']}, lands {j['answers']['impact']} ({j['conf']['impact']:.2f}; then {sec('impact')}), "
                      f"tell {j['answers']['tell']}, size {j['answers']['intensity']}")
            md.append(f"- its line would be: `{j['line']}`")
        md.append('')
    with open(REVIEW, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(md))
    return keep, review


def main():
    dry = '--dry' in sys.argv
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    hand = hand_keys()
    items = {k: v for k, v in boss_abilities().items() if k not in hand}
    os.makedirs(OUT, exist_ok=True)
    cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
    todo = [k for k in sorted(items) if f'{VERSION}:{k}' not in cache][:limit]
    print(f'{len(items)} boss abilities (not counting {len(hand)} with hand lines); {len(todo)} to ask' + (' (dry: none asked)' if dry else ''))
    if not dry and todo:
        done, tokens = 0, 0
        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            futs = {ex.submit(judge, items[k]): k for k in todo}
            for f in concurrent.futures.as_completed(futs):
                j = f.result()
                if j:
                    cache[f'{VERSION}:{futs[f]}'] = j
                    tokens += j['tokens']
                done += 1
                if done % 25 == 0:
                    json.dump(cache, open(CACHE, 'w', encoding='utf-8'))
                    print(f'  {done}/{len(todo)}')
        json.dump(cache, open(CACHE, 'w', encoding='utf-8'))
        print(f'asked {done}, {tokens} input tokens')
    judged = {k: cache[f'{VERSION}:{k}'] for k in items if f'{VERSION}:{k}' in cache}
    keep, review = write(items, judged)
    print(f'wrote {os.path.relpath(TABLE, ROOT)}: {len(keep)} lines; {len(review)} for review in {os.path.relpath(REVIEW, ROOT)}')


if __name__ == '__main__':
    main()
