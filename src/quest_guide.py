"""Where to go next for an ordinary quest, for /play's tracker, minimap mark and ground arrow.

A marquee quest has its own tracker block (marquee.quest_block); every other quest (kill, talk,
visit, collect, the tutorial) had none, so the 3D client showed nothing and pointed nowhere. This
builds the same block for the player's first unfinished quest:

  {'id', 'name', 'stage', 'of', 'title', 'objectives': [{text, have, need, done}],
   'where': {'vnum', 'name', 'steps', 'dir'}, 'kind': 'quest'}

`where` is the nearest room (by walking, from where the player stands) that holds what the current
objective wants: a creature of that name to kill, the person to talk to, the room to visit, the
thing to collect lying there or carried by someone there. When every objective is done it is the
quest's giver, to turn it in. `dir` is the first step of the way there (None when already there).
"""
import re
from collections import deque

MAX_ROOMS = 600          # how far the search walks (a zone or two around the player)

# the tutorial is written for telnet ('Check your score (type "score")'); /play does the same
# things with windows and menus, so the tracker says that instead (the window's opening counts:
# commands.py cmd_uiseen)
WEB_HOW = {
    'score': 'open your Character sheet (C)', 'equipment': 'open your Character sheet (C)',
    'inventory': 'open your Bags (I)', 'skills': 'open your Spellbook (K)', 'spells': 'open your Spellbook (K)',
    'quests': 'open your Journal (L)', 'who': 'open the Players list (P)', 'group': 'open the Players list (P)',
    'list': 'right-click the shopkeeper, then Shop', 'buy': 'buy anything in the shop window',
    'rest': 'right-click yourself, then Rest', 'stand': 'right-click yourself, then Stand up',
    'eat': 'open your Bags (I), pick some food, then Eat', 'talk': 'right-click them, then Talk',
    'kill': 'Tab to target it, F to attack', 'channel': 'type "channel list" in the chat box',
    'journal': 'open your Journal (L)', 'map': 'open the Map (M)', 'help': 'open Help (H)',
    'look': 'right-click it, then Look', 'examine': 'right-click it, then Look',
}
TYPED = re.compile(r'\s*\((?:type|try) "(\w+)[^)]*\)')
# the same in any line the server sends /play: '(type "x")' or "(type 'x')" anywhere in it, and a
# sentence "Type 'journal' to view your discoveries." where /play opens a window for it instead
TYPED_ANY = re.compile(r"""\s*\((?:[Tt]ype|[Tt]ry) (["'])(\w+)[^)]*?\1\)""")
TYPE_TO = re.compile(r"""\b([Tt])ype (["'])(\w+)[^"'\n]*?\2( to [^.!\n\x1b]+)""")
# and a shopkeeper's "Type LIST to see my wares" (the command in capitals, no quotes)
TYPE_CAPS = re.compile(r"""\b[Tt]ype ([A-Z]{2,})( to [^.!'"\n\x1b]+)""")


def for_player(player, text):
    """An objective's words as this player plays: the /play wording on the web bridge."""
    conn = getattr(player, 'connection', None)
    return web_text(text) if getattr(conn, 'is_web', False) else text


def web_text(text):
    """An objective's words for /play: '(type "score")' becomes how to do it with the HUD."""
    m = TYPED.search(text or '')
    if not m or m.group(1).lower() not in WEB_HOW:
        return text
    return f"{text[:m.start()]}: {WEB_HOW[m.group(1).lower()]}{text[m.end():]}"


def web_line(text):
    """Any line the server sends /play (server.Connection.send), its telnet hints in /play's
    words: a '(type "x")' after what to do becomes how to do it with the HUD, and "Type 'x' to
    ..." becomes "Open your ... to ..." where a window does it. A hint /play has no other way
    for stays as it is (the chat box takes commands)."""
    if not text or ('ype ' not in text and 'ry ' not in text and 'YPE ' not in text):
        return text

    def paren(m):
        how = WEB_HOW.get(m.group(2).lower())
        return f": {how}" if how else m.group(0)

    def sentence(m):
        # ("Type 'journal' to ..." / "simply type "talk aldric" to speak with him": the HUD's way,
        # capitalised as the word it stands for)
        how = WEB_HOW.get(m.group(3).lower())
        if not how or (not how.startswith('open ') and how.startswith('type ')):
            return m.group(0)
        head = how[0].upper() if m.group(1) == 'T' else how[0]
        return f"{head}{how[1:]}{m.group(4)}"

    def caps(m):
        how = WEB_HOW.get(m.group(1).lower())
        return f"{how[0].upper()}{how[1:]}{m.group(2)}" if how else m.group(0)

    return TYPE_CAPS.sub(caps, TYPE_TO.sub(sentence, TYPED_ANY.sub(paren, text)))


def _words(s):
    return set(str(s or '').lower().replace(',', ' ').split())


def _fair_game(ch, level):
    """A creature a player of `level` can fight for a "defeat any creature" step: not a
    shopkeeper, trainer or other peaceful sort, and not far above them."""
    flags = set(str(f).lower() for f in (getattr(ch, 'flags', None) or []))
    if flags & {'shopkeeper', 'peaceful', 'nokill', 'no_kill', 'sentinel_guard', 'trainer', 'healer', 'banker', 'innkeeper'}:
        return False
    if getattr(ch, 'special', None) in ('shopkeeper', 'trainer', 'guildmaster', 'banker', 'healer'):
        return False
    return getattr(ch, 'level', 1) <= max(3, level + 2)


def _mob_matches(ch, target, level=1):
    """A creature that answers to `target`: its vnum, or a word of its name ('any': one a
    player of `level` can fight)."""
    if getattr(ch, 'is_player', False) or hasattr(ch, 'account_name'):
        return False
    if getattr(ch, 'hp', 1) <= 0:
        return False
    t = str(target or '').strip().lower()
    if not t:
        return False
    if t == 'any':
        return _fair_game(ch, level)
    if t.isdigit():
        return str(getattr(ch, 'vnum', '')) == t
    names = _words(getattr(ch, 'name', '')) | _words(getattr(ch, 'short_desc', '')) | _words(getattr(ch, 'keywords', ''))
    return t in names or any(w.rstrip('s') == t.rstrip('s') for w in names)


def _item_here(room, vnum):
    for it in getattr(room, 'items', None) or getattr(room, 'objects', None) or []:
        if str(getattr(it, 'vnum', '')) == vnum:
            return True
    for ch in getattr(room, 'characters', None) or []:
        if getattr(ch, 'is_player', False):
            continue
        for it in getattr(ch, 'inventory', None) or []:
            if str(getattr(it, 'vnum', '')) == vnum:
                return True
    return False


def _wanted(room, kind, target, level=1):
    """Whether `room` holds what an objective of `kind` wants."""
    t = str(target or '').strip()
    if kind in ('visit', 'explore'):
        return t.isdigit() and getattr(room, 'vnum', None) == int(t)
    if kind in ('kill', 'talk', 'escort'):
        if kind == 'kill' and t == 'any' and 'peaceful' in [str(f).lower() for f in getattr(room, 'flags', None) or []]:
            return False
        return any(_mob_matches(ch, t, level) for ch in getattr(room, 'characters', None) or [])
    if kind == 'collect':
        return t.isdigit() and _item_here(room, t)
    return False


def _exits(room):
    for d, e in (getattr(room, 'exits', None) or {}).items():
        if not e:
            continue
        nxt = e.get('room') if isinstance(e, dict) else None
        if nxt is not None:
            yield d, nxt


def find(player, test):
    """The nearest room (walking from the player's) for which test(room) holds: (room, steps,
    first direction), or None."""
    start = getattr(player, 'room', None)
    if start is None:
        return None
    if test(start):
        return start, 0, None
    seen = {id(start)}
    q = deque([(start, 0, None)])
    n = 0
    while q and n < MAX_ROOMS:
        room, steps, first = q.popleft()
        n += 1
        for d, nxt in _exits(room):
            if id(nxt) in seen:
                continue
            seen.add(id(nxt))
            try:
                if not nxt.admits(player):
                    continue
            except Exception:
                pass
            f = first or d
            if test(nxt):
                return nxt, steps + 1, f
            q.append((nxt, steps + 1, f))
    return None


def _giver(quest_id):
    try:
        from quests import QUEST_DEFINITIONS
        return (QUEST_DEFINITIONS.get(quest_id) or {}).get('quest_giver')
    except Exception:
        return None


def _giver_name(player, vnum):
    try:
        proto = player.world.mob_prototypes.get(int(vnum))
    except Exception:
        proto = None
    if not proto:
        return None
    name = proto.get('short_desc') if isinstance(proto, dict) else getattr(proto, 'short_desc', None)
    return name or (proto.get('name') if isinstance(proto, dict) else getattr(proto, 'name', None))


# the tutorial is for the first levels: past this level its quests leave the tracker (they stay in
# the journal); and the player's own choice (Hide on the tracker, Track / Hide in the journal:
# player.quest_tracking {quest id: bool}) overrides either way
TUTORIAL_UNTIL = 10


def tutorial(q):
    """Whether a quest (an active Quest) is one of the tutorial's."""
    qid = str(getattr(q, 'quest_id', '') or '')
    if qid.startswith('tutorial_'):
        return True
    try:
        from quests import QUEST_DEFINITIONS
        return (QUEST_DEFINITIONS.get(qid) or {}).get('type') == 'tutorial'
    except Exception:
        return False


def tracked(player, q):
    """Whether the tracker follows this quest."""
    chosen = (getattr(player, 'quest_tracking', None) or {}).get(q.quest_id)
    if chosen is not None:
        return bool(chosen)
    return not (tutorial(q) and (getattr(player, 'level', 1) or 1) > TUTORIAL_UNTIL)


def guide_block(player):
    """The tracker block for the player's first unfinished ordinary quest (None: none)."""
    quests = [q for q in getattr(player, 'active_quests', None) or [] if q.objectives and tracked(player, q)]
    if not quests:
        return None
    q = next((q for q in quests if not q.is_complete()), quests[0])
    objs = q.objectives
    current = next((o for o in objs if not o.completed), None)
    b = {'id': q.quest_id, 'name': q.name, 'kind': 'quest',
         'stage': (objs.index(current) + 1) if current else len(objs), 'of': len(objs),
         'title': web_text(current.description) if current else 'Return to the one who gave you this quest',
         'objectives': [{'text': web_text(o.description), 'have': o.current, 'need': o.required, 'done': bool(o.completed)} for o in objs],
         'party': []}
    # what the step wants, for /play to pick out in the world (cues: a gold ring under the
    # creature to slay or speak with, the thing to pick up)
    if current is not None and current.type in ('kill', 'talk', 'collect') and str(current.target or '').lower() not in ('', 'any'):
        b['want'] = {'t': current.type, 'target': str(current.target)}
    if current is not None and current.type == 'command':
        hit = None                    # done where you stand: the title says how
    elif current is not None:
        lvl = getattr(player, 'level', 1) or 1
        hit = find(player, lambda r: _wanted(r, current.type, current.target, lvl))
    else:
        giver = _giver(q.quest_id)
        hit = find(player, lambda r: _wanted(r, 'talk', giver)) if giver else None
        name = _giver_name(player, giver)
        if name:
            b['title'] = f'Return to {name}'
    if hit:
        room, steps, first = hit
        b['where'] = {'vnum': room.vnum, 'name': room.name, 'steps': steps, 'dir': first}
    return b
