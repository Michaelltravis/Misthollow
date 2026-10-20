"""Every line in the server's source that draws a frame (box characters, or ====/---- rules), as
the text it would send: f-string fields filled with a sample word, colour codes taken out. For the
check that /play draws each one in its own dress (hud/frames.js; tests/test_web_menus.py).

    python3 tools/audit/frame_lines.py [OUT.json]      ([{file, line, text}], or a count)
"""
import ast
import json
import os
import re
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src')
BOX = re.compile(r'[═║╔╗╚╝╠╣╦╩╬│┌┐└┘├┤─━]|={4,}|-{5,}|\+[-=]{3,}')
FILL = 'Sample Word'
# not the game's output: a script that writes Python source
SKIP_FILES = {'apply_wave2.py'}


def _repeat(node, names):
    """'═' * 60, H * W: the character drawn out (a width not known: 40)."""
    for s, n in ((node.left, node.right), (node.right, node.left)):
        ch = s.value if isinstance(s, ast.Constant) and isinstance(s.value, str) else names.get(getattr(s, 'id', None))
        if ch is not None:
            return ch * (n.value if isinstance(n, ast.Constant) and isinstance(n.value, int) else 40)
    return None


def render(node, names):
    """The text a string expression sends: fields as a sample word (kept to their width), colour
    codes gone, a name given a box character (H = '═') as that character."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out = ''
        for v in node.values:
            if isinstance(v, ast.Constant):
                out += v.value
                continue
            inner = v.value
            if isinstance(inner, ast.Subscript) and isinstance(inner.value, ast.Name) and inner.value.id == 'c':
                continue
            if isinstance(inner, ast.Name) and v.format_spec is None and (inner.id in names or re.search(r'colou?r$|_col$', inner.id)):
                out += names.get(inner.id, '')
                continue
            if isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.Mult):
                rep = _repeat(inner, names)
                if rep is not None:
                    out += rep
                    continue
            spec = ''.join(x.value for x in v.format_spec.values if isinstance(x, ast.Constant)) if v.format_spec else ''
            m = re.search(r'(\d+)', spec)
            out += (FILL * 3)[:int(m.group(1))].ljust(int(m.group(1))) if m else FILL
        return out
    if isinstance(node, ast.Name):
        # (a colour kept in a name, tier_color = c['red']: nothing to see)
        return '' if re.search(r'colou?r$|_col$', node.id) else names.get(node.id, FILL)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return render(node.left, names) + render(node.right, names)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _repeat(node, names) or ''
    return ''


def frame_lines(src=SRC):
    """[{file, line, text}] for every frame-drawing line of the server's source."""
    found, seen = [], set()
    for name in sorted(os.listdir(src)):
        if not name.endswith('.py') or name in SKIP_FILES:
            continue
        try:
            tree = ast.parse(open(os.path.join(src, name), encoding='utf-8').read())
        except SyntaxError:
            continue
        names, parent = {}, {}
        for n in ast.walk(tree):
            for ch in ast.iter_child_nodes(n):
                parent[ch] = n
            # a name given a box character (H = '═'; TL, TR = '╔', '╗' too)
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    pairs = [(t, n.value)] if isinstance(t, ast.Name) else (
                        list(zip(t.elts, n.value.elts)) if isinstance(t, ast.Tuple) and isinstance(n.value, ast.Tuple) else [])
                    for a, b in pairs:
                        if isinstance(a, ast.Name) and isinstance(b, ast.Constant) and isinstance(b.value, str) \
                                and BOX.search(b.value) and len(b.value) <= 3:
                            names[a.id] = b.value
        for node in ast.walk(tree):
            if not isinstance(node, (ast.JoinedStr, ast.Constant, ast.BinOp)):
                continue
            if isinstance(node, ast.Constant) and not isinstance(node.value, str):
                continue
            # only whole strings: not a piece of a larger one, a docstring, or a box character's name
            up = parent.get(node)
            if isinstance(up, (ast.JoinedStr, ast.FormattedValue, ast.Expr)):
                continue
            if isinstance(up, ast.BinOp) and isinstance(up.op, (ast.Add, ast.Mult)):
                continue
            # (and a map's cell: '─' if east-west else '│')
            short = isinstance(node, ast.Constant) and len(node.value) <= 3
            if short and (isinstance(up, (ast.Assign, ast.IfExp)) or (isinstance(up, ast.Tuple) and isinstance(parent.get(up), ast.Assign))):
                continue
            text = render(node, names)
            if not text or not BOX.search(text):
                continue
            # (colour codes, the world events' §R codes, a .format template's {cyan})
            text = re.sub(r'\x1b\[[0-9;]*m|§[A-Z]|\{[a-z_]+\}', '', text)
            for ln in text.replace('\r', '').split('\n'):
                key = (name, getattr(node, 'lineno', 0), ln)
                if BOX.search(ln) and key not in seen:
                    seen.add(key)
                    found.append({'file': name, 'line': key[1], 'text': ln})
    return found


if __name__ == '__main__':
    lines = frame_lines()
    if len(sys.argv) > 1:
        json.dump(lines, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(len(lines), 'frame lines in', len({x['file'] for x in lines}), 'files')
