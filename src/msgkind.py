"""What kind of line the server is sending, for the web page (/play) to sort its log.

The 3D client draws a fight: every swing, spell, wound, stagger, fizzle and death has its
animation and its rising number (combat_events.py). Its chat log then needn't repeat it all, so
each line sent to a web connection carries a hidden mark of its kind, `ESC ] K:<kind> BEL`, at
its start (web_client.py turns it into an empty <i data-k="kind"> the page reads):

  combat  the blow-by-blow: what was printed while a swing, a skill or a spell was resolving
          (combat_events' action is open), and the lines the fight prints outside one (a wound
          over time ticking, an effect wearing off, a charge gained, a creature's health bar)
  reward  what a kill pays: experience, the streak and rested bonuses, reputation, the gold
  ui      what the page draws itself (web_hud.py): the sun rising, the sky, hunger, a posture,
          a breath held, mail waiting, a world event; the sender asks for it (send(kind=UI)) and
          the log keeps the line, dimmed

Everything else is unmarked: the room, speech, quests, loot, and the refusals a player has to
read ("You don't have enough mana."), even when they come in the middle of a fight. Telnet never
sees a mark.
"""
import re

MARK = '\x1b]K:{}\x07'
UI = 'ui'

REWARD_RE = re.compile(
    r'(You gain [\d,]+ experience|^Bonuses: |Reputation with .+: [+-]\d|gold coins? from the corpse|'
    r'You receive [\d,]+ (?:experience|exp)|☠ .+ is DEAD!|You killed )', re.I)
# a refusal or a question the player must read, whatever is going on around it
REFUSAL_RE = re.compile(
    r"^(?:You (?:don't|do not|can't|cannot|can not|must|need|lack|aren't|are not|have no|are too|are already|"
    r"haven't|feel too)|Not enough|There is no|There's no|They aren't here|Nobody|No one|Who\b|What\b|"
    r"Huh\?|Cast what|Use what|That (?:spell|skill|ability)|.*\bon cooldown\b|.*\bisn't ready\b)", re.I)
# the fight's own lines when no action is open (ticks, procs, charges, a health bar)
COMBAT_RE = re.compile(
    r'(looks ill from |You shudder from the poison|You take \d+ damage from |You heal \d+ HP from |The effect of .+ wears off|'
    # (the health bar is ten cells, combat.get_health_bar: a menu's longer bar, reputation's, is not the fight)
    r'Arcane charges? |\[Arcane Charges: |fizzles|STAGGERED|\[[█░▓▒ ]{10}\]|\[\d+ damage\]|'
    r'\*\*\* CRITICAL|OBLITERATES|ANNIHILATES|DEVASTATES|MASSACRES|^[💥💤✨🔥❄⚡🩸☠🌀🛡]\s|'
    r'^[\w\' -]+ attacks (?:you|[A-Z]\w+)!$|^You attack .+!$)')

# speech is never hidden (a boss's taunt in the middle of its blow included)
SPEECH_RE = re.compile(r"(\b(?:says?|yells?|shouts?|screams?|whispers?|tells? (?:you|the group))\b[,:]? ['\"]|^You (?:say|tell)|\bsays,)", re.I)
# a room described (an ability that carries you somewhere, a flee): the whole look stays
LOOK_RE = re.compile(r'(Obvious exits|\[ ?Exits?:|^Exits?:)', re.I | re.M)
_ANSI = re.compile(r'\x1b\[[0-9;]*m')


def kind_of(line, in_action=False):
    """'combat', 'reward' or None for one line of text (colour codes and all)."""
    plain = _ANSI.sub('', line).strip()
    if not plain:
        return None
    if REWARD_RE.search(plain):
        return 'reward'
    if REFUSAL_RE.match(plain) or SPEECH_RE.search(plain):
        return None
    # a row of a menu's box is the menu, not the fight (skills' bars looked like a health bar),
    # whatever is going on: /play draws the box whole (hud/frames.js)
    if plain[0] in '║│|╔╚╠╟╞╒╘┌└├':
        return None
    if in_action or COMBAT_RE.search(plain):
        return 'combat'
    return None


def in_action():
    """Whether this task is inside a combat action (a swing, a skill, a spell resolving)."""
    try:
        import combat_events
        return combat_events._open() is not None
    except Exception:
        return False


def mark(message, kind=None):
    """The message with each of its lines marked by kind (for a web connection); a kind asked
    for marks every line that has text."""
    act = kind is None and in_action() and not LOOK_RE.search(_ANSI.sub('', message))
    out = []
    for line in message.split('\n'):
        if kind:
            k = kind if _ANSI.sub('', line).strip() else None
        else:
            k = kind_of(line, act)
        out.append(MARK.format(k) + line if k else line)
    return '\n'.join(out)
