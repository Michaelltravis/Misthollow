"""Daily bounties (docs/GAMEPLAY_POLISH.md, group 4): the bounty board (the giver of the old
'daily_bounty', the Garathorm guard post) posts three named contracts a day, one for each band
of level, each on a creature that roams the world in numbers: slay so many of it, for gold and
experience by its level. They are ordinary daily quests (quests.py `daily`), so the journal
offers them, the tracker guides to the nearest of the creature (quest_guide.py) and each can be
done once a day; tomorrow brings three new ones. Refreshed at load and with the weather
(world.weather_tick)."""
import datetime
import random
import re

BANDS = (('bounty_novice', "A Novice's Bounty", 2, 15), ('bounty_veteran', "A Veteran's Bounty", 15, 35),
         ('bounty_champion', "A Champion's Bounty", 35, 60))
GIVER = 3006
NOT = {'boss', 'sentinel', 'shopkeeper', 'trainer', 'peaceful', 'nokill', 'no_kill', 'healer', 'banker', 'innkeeper'}
# no price is put on the town's own people nor on its harmless beasts
TOWNSFOLK = re.compile(r'\b(guard|guards|guardsman|watchman|soldier|citizen|merchant|shopkeeper|priest|priestess|child|peasant|'
                       r'villager|farmer|king|queen|prince|princess|captain|mayor|elder|clerk|squirrel|rabbit|hare|deer|doe|'
                       r'fawn|songbird|sparrow|butterfly|duckling|chick|kitten|lamb|sheep|cow|chicken)\b', re.I)
_day = None


def _candidates(world, lo, hi):
    """Creatures in the band that live in the world in numbers: {short name: (level, count)}."""
    seen = {}
    for m in getattr(world, 'npcs', []):
        flags = set(str(f).lower() for f in (getattr(m, 'flags', None) or ()))
        if flags & NOT or getattr(m, 'owner', None) is not None or getattr(m, 'special', None):
            continue
        lvl = getattr(m, 'level', 0) or 0
        name = (getattr(m, 'short_desc', None) or '').strip()
        if not (lo <= lvl <= hi) or not name or getattr(m, 'room', None) is None or TOWNSFOLK.search(name):
            continue
        if 'aggressive' not in flags and not getattr(m, 'hunts', False):
            continue
        key = name.lower()
        for art in ('a ', 'an ', 'the '):
            if key.startswith(art):
                key = key[len(art):]
        if len(key) < 3 or len(key.split()) > 4:
            continue
        lv, n = seen.get(key, (lvl, 0))
        seen[key] = (max(lv, lvl), n + 1)
    return {k: v for k, v in seen.items() if v[1] >= 3}


def refresh(world, today=None):
    """Post today's three bounties (once a day; again when the day turns)."""
    global _day
    from quests import QUEST_DEFINITIONS
    today = today or datetime.date.today()
    if _day == today and all(b[0] in QUEST_DEFINITIONS for b in BANDS):
        return False
    _day = today
    rnd = random.Random(today.toordinal())
    for qid, title, lo, hi in BANDS:
        pool = sorted(_candidates(world, lo, hi).items())
        if not pool:
            QUEST_DEFINITIONS.pop(qid, None)
            continue
        name, (lvl, count) = rnd.choice(pool)
        need = min(count, rnd.randint(4, 7))
        QUEST_DEFINITIONS[qid] = {
            'name': f"{title}: {name.title()}",
            'description': f"The bounty board posts a price on {name}: they have grown too many and too bold. "
                           f"Slay {need} and come back for the reward. (A new bounty is posted each day.)",
            'type': 'kill', 'category': 'daily', 'level_min': lo, 'level_max': hi + 5,
            'quest_giver': GIVER,
            'objectives': [{'type': 'kill', 'description': f"Slay {need} {name}", 'target': name, 'required': need}],
            'rewards': {'exp': int(lvl * 45 * need), 'gold': int(lvl * 12 * need)},
            'repeatable': True, 'daily': True,
        }
    return True
