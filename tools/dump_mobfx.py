"""Every everyday creature ability the server can send a look for, for the 3D client's tests.

A creature's wind-ups (mob_ai's intents and the brain's spells, brain/cast.py) and its instant
heals and wards reach /play with an `fx` (combat_hooks.fx_key); tests/web/mobfx.test.mjs reads
the file this writes to check, without a running server, that each has a line of its own in
world3d/mobfx-hand.js. Bosses' scripted abilities (bosses.py) are not here: they come with phase 3.
    python3 tools/dump_mobfx.py           # write tests/web/fixtures/mobfx.json
    python3 tools/dump_mobfx.py --check   # exit 1 when it is out of date
"""
import ast
import json
import logging
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'src'))
OUT = os.path.join(ROOT, 'tests', 'web', 'fixtures', 'mobfx.json')
SRC = os.path.join(ROOT, 'src')


def _labels(path):
    """The names a module's intents are declared with: each {'label': '...'} literal, and the
    labels in mob_ai._choose_boss_intent's META ('aoe', 'Ground Slam', ...)."""
    with open(path, encoding='utf-8') as f:
        tree = ast.parse(f.read())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == 'label' and isinstance(v, ast.Constant):
                    out.append(v.value)
        elif isinstance(node, ast.Tuple) and len(node.elts) >= 2 and all(isinstance(e, ast.Constant) for e in node.elts[:2]):
            label = node.elts[1].value
            if node.elts[0].value in ('aoe', 'debuff', 'cast', 'heavy') and isinstance(label, str) and label[:1].isupper():
                out.append(node.elts[1].value)
    return out


def build():
    logging.disable(logging.CRITICAL)
    import combat_hooks
    import mob_ai
    from brain import cast
    rows = {}

    def add(label, source):
        key = combat_hooks.fx_key(label)
        rows.setdefault(key, {'fx': key, 'label': label, 'from': []})
        if source not in rows[key]['from']:
            rows[key]['from'].append(source)

    for key, (_verb, _mult, _mana, kind, _ticks) in cast.SPELLBOOK.items():
        add(key.replace('_', ' ').title(), f'brain/cast.py SPELLBOOK ({kind})')
    for spell in mob_ai.CASTER_OFFENSIVE:
        add(spell[0].replace('_', ' ').title(), 'mob_ai.CASTER_OFFENSIVE')
    for deb in mob_ai.CASTER_DEBUFFS:
        add(deb[0].replace('_', ' ').title(), 'mob_ai.CASTER_DEBUFFS')
    for label in _labels(os.path.join(SRC, 'mob_ai.py')):
        add(label, 'mob_ai intent')
    for label in _labels(os.path.join(SRC, 'brain', 'cast.py')):
        add(label, 'brain/cast.py intent')
    # what combat_hooks names itself (a caster's instant mending and ward)
    with open(os.path.join(SRC, 'combat_hooks.py'), encoding='utf-8') as f:
        for key in re.findall(r"fx='([a-z_]+)'", f.read()):
            add(key.replace('_', ' ').title(), 'combat_hooks instant')
    return {'abilities': sorted(rows.values(), key=lambda r: r['fx'])}


def main():
    text = json.dumps(build(), indent=1, sort_keys=True) + '\n'
    if '--check' in sys.argv:
        try:
            with open(OUT, encoding='utf-8') as f:
                same = f.read() == text
        except FileNotFoundError:
            same = False
        print('mobfx.json is current' if same else 'mobfx.json is out of date: python3 tools/dump_mobfx.py')
        sys.exit(0 if same else 1)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print(f'wrote {OUT}: {len(json.loads(text)["abilities"])} abilities')


if __name__ == '__main__':
    main()
