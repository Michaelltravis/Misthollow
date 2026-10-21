"""The marquee quests (push 7): one per class, offered at level 45 by the class's trainer, ending
in a private trial; solo about two hours, harder for each member who embarks.

Offline: the scaling (health, damage, adds, tempo, rewards) by the number who embarked; a solo
quest's foes add up to about two hours with travel; Unbroken Banner is earned, never learned by
level, and its command refuses another class and a running cooldown.
Live (needs ./run.sh and the gauntlet accounts) — see live() below.
    python3 tests/test_marquee.py [--offline]
"""
import asyncio
import json
import os
import re
import sys
import time
import types

import aiohttp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import test_webmove as tw  # noqa: E402  (Telnet helper, check(), failures)
import gauntlet_accounts  # noqa: E402  (the test characters, made if missing)

check, failures = tw.check, tw.failures


def fake_player(**kw):
    sent = []

    async def send(msg='', *a, **k):
        sent.append(str(msg))
    from config import Config
    p = types.SimpleNamespace(level=46, char_class='warrior', skills={}, spells={}, send=send, sent=sent, affects=[],
                              config=types.SimpleNamespace(COLORS=Config.COLORS), world=None, room=None, group=None,
                              name='Ann', hp=500, max_hp=500)
    for k, v in kw.items():
        setattr(p, k, v)
    return p


async def offline():
    import marquee_scale as ms
    check(ms.health_factor(1) == 1 and abs(ms.health_factor(3) - 2.6) < 1e-9 and abs(ms.health_factor(6) - 5.0) < 1e-9,
          'health x1 alone, x2.6 for three, x5 for six')
    check(abs(ms.damage_factor(6) - 1.5) < 1e-9 and ms.extra_adds(1) == 0 and ms.extra_adds(3) == 1 and ms.extra_adds(6) == 2,
          'damage +10% a hero, one extra add a wave for every two more')
    check(ms.tempo(1) == 1 and ms.tempo(6) < 0.8, 'a boss acts sooner for a bigger party')
    check(ms.party_level(45, [52, 50]) == 49 and ms.party_level(58, [45]) == 58 and ms.party_level(40) == 45,
          "the quest's level: the owner's, or the party's average if higher, 45-60")
    solo = ms.minutes('elite', 46, 1)
    six = ms.minutes('elite', 46, 6)
    check(0.9 < solo < 1.4 and six < solo, f'an elite takes ~1 min alone ({solo:.2f}), a little less for six ({six:.2f})')
    boss = ms.minutes('boss', 47, 1)
    check(2.5 < boss < 3.5, f'the trial boss takes ~3 minutes alone ({boss:.1f})')
    check(ms.gold_reward(1000, 3) == 2000 and ms.exp_reward(1000, 3) == 2600, 'rewards grow with the party')

    import mastery
    from config import Config
    check('unbroken_banner' in [a for a, _k in mastery.roster('warrior')] and mastery.unlock_level('warrior', 'unbroken_banner') == 45,
          "Unbroken Banner is in the warrior's book at level 45")
    p = fake_player(level=60)
    mastery.grant_now(p)
    check('unbroken_banner' not in p.skills, 'reaching level 60 does not teach it: it is earned through the quest')
    e = next(x for x in mastery.book('warrior') if x['id'] == 'unbroken_banner')
    check(e.get('quest') == 'The Unbroken Banner' and e.get('marquee') and e.get('target') == 'self',
          f"the book says how it is earned ({e.get('quest')}) and it needs no target")

    import marquee_abilities as ma
    mage = fake_player(char_class='mage')
    await ma.unbroken_banner(mage, [])
    check(any('only a warrior can' in s and 'cannot' in s for s in mage.sent),
          'another class is refused (in words that keep it from animating or counting as a use)')
    w = fake_player(marquee_cd={'unbroken_banner': __import__('time').time() + 200})
    await ma.unbroken_banner(w, [])
    check(any('not ready yet' in s for s in w.sent), 'a running cooldown is refused (and the cooldown is saved on the character)')


def _world_player(world, name, room, **kw):
    """A stand-in for a Player in a real loaded world (enough for marquee.py)."""
    sent = []

    async def send(msg='', *a, **k):
        sent.append(str(msg))

    async def save():
        pass

    async def gain_exp(amount, source='other', breakdown=None):
        p.exp += amount
    from config import Config
    p = types.SimpleNamespace(name=name, account_name=name.lower(), level=46, char_class='warrior', skills={}, spells={},
                              send=send, sent=sent, save=save, gain_exp=gain_exp, exp=0, gold=0, affects=[], position='standing',
                              config=types.SimpleNamespace(COLORS=Config.COLORS), world=world, room=None, group=None,
                              hp=600, max_hp=600, marquee=None, marquee_help=None, marquee_cd={}, fighting=None,
                              connection=None, is_immortal=False)
    for k, v in kw.items():
        setattr(p, k, v)
    world.players[name.lower()] = p
    put(p, world.rooms[room])
    return p


def put(ch, room):
    if getattr(ch, 'room', None) is not None and ch in ch.room.characters:
        ch.room.characters.remove(ch)
    ch.room = room
    room.characters.append(ch)


def said(p, text):
    return any(text in s for s in p.sent)


async def drive(world, marquee, cls):
    """Play one class's whole quest offline with a stand-in, each stage the way a player does it:
    the offer, the talk, the kills, the gathering, the warden, the ritual, the trial, the return."""
    import marquee_quests as mq
    q = mq.QUESTS[cls]
    name = f'Drv{cls[:5].capitalize()}'
    p = _world_player(world, name, q['giver_room'], level=47, char_class=cls)
    gm = next(ch for ch in world.rooms[q['giver_room']].characters if getattr(ch, 'vnum', None) == q['giver'])
    await marquee.on_talk(p, gm)
    offered = said(p, f"A marquee quest: {q['name']}")
    await marquee.accept(p)
    m = p.marquee
    run = marquee.RUNS[name.lower()]
    trouble = []
    for idx, st in enumerate(q['stages']):
        if m is None or m.get('stage') != idx:
            trouble.append(f"stage {idx + 1} ({st['title']}) not reached")
            break
        k = st['kind']
        if k == 'talk':
            put(p, world.rooms[st['room']])
            await marquee._step()
            npc = next((ch for ch in p.room.characters if getattr(ch, 'vnum', None) == st['npc']), None)
            if npc is None:
                trouble.append(f"no {st['npc']} to speak with")
                break
            await marquee.on_talk(p, npc)
        elif k == 'visit':
            for v in st['visits']:
                put(p, world.rooms[v['room']])
                await marquee._step()
        elif k == 'kill':
            for i, sp in enumerate(st['spawns']):
                put(p, world.rooms[sp['room']])
                await marquee._step()
                mob = next((x for x in run.mobs if x.marquee_tag.get('slot') == i), None)
                if mob is None:
                    trouble.append(f"nothing placed at {sp['room']}")
                    break
                mob.hp = 0
                await marquee.fallen(mob, p)
        elif k == 'collect':
            put(p, world.rooms[st['rooms'][0]])
            for _ in range(80):
                if m.get('stage') != idx:
                    break
                await marquee._step()
                run.respawn = {}
                x = next((x for x in run.mobs if marquee._alive(x)), None)
                if x is not None:
                    x.hp = 0
                    await marquee.fallen(x, p)
        elif k == 'ritual':
            put(p, world.rooms[st['room']])
            await marquee.plant(p)
            if run.ritual is None:
                trouble.append(f"`marquee {st['verb']}` did not begin the ritual")
                break
            run.ritual['start'] -= st['seconds'] + 10
            await marquee._step()
            for x in list(run.mobs):
                x.hp = 0
            await marquee._step()
        elif k == 'trial':
            put(p, world.rooms[st['room']])
            await marquee.enter_trial(p)
            t = run.trial
            if t is None:
                trouble.append('the trial did not open')
                break
            for w in t.tpl['waves']:
                put(p, t.rooms[w['room']])
                await marquee._step()
                for x in list(run.mobs):
                    x.hp = 0
                await marquee._step()
            put(p, t.rooms[t.tpl['boss']['room']])
            await marquee._step()
            if t.boss is None:
                trouble.append('no boss in the trial')
                break
            t.boss.hp = 0
            await marquee._step()
            await marquee.leave_trial(p)
        elif k == 'return':
            put(p, world.rooms[q['giver_room']])
            await marquee.on_talk(p, gm)
    learned = p.skills.get(q['ability']) == 50 and p.marquee is None
    check(offered and learned and not trouble, f"{cls}: {q['name']} played through all {len(q['stages'])} stages teaches "
                                               f"{q['ability']} ({trouble})")
    world.players.pop(name.lower(), None)
    if p.room is not None and p in p.room.characters:
        p.room.characters.remove(p)


async def engine():
    """The quest engine on the real world, with stand-in players: offer, accept, every stage of
    the warrior's quest, the party's size in every foe, credit for any member's kill, outsiders
    kept out, the private trial opened, won and closed."""
    import logging
    logging.disable(logging.INFO)
    import json as _json
    from config import Config
    from world import World
    import marquee
    import marquee_quests as mq
    import marquee_scale as ms
    world = World(Config())
    await world.load()
    world.web_map = None

    async def no_loop():
        return None
    marquee._loop = no_loop                 # the test drives the ticks itself
    marquee.install(world)
    q = mq.QUESTS['warrior']

    # every quest's data points at things that exist, and its trial hangs together
    import mastery
    import marquee_abilities as ma
    for cls, qq in mq.QUESTS.items():
        bad = []
        for st in qq['stages']:
            for v in [st.get('room'), *[sp['room'] for sp in st.get('spawns', [])], *st.get('rooms', []),
                      *[r['room'] for r in st.get('visits', [])]]:
                if v is not None and v not in world.rooms:
                    bad.append(f"room {v} ({st['title']})")
            for v in [st.get('npc'), st.get('mob'), st.get('adds'), *[sp['vnum'] for sp in st.get('spawns', [])],
                      *[w['vnum'] for w in st.get('waves', [])]]:
                if v is not None and v not in world.mob_prototypes:
                    bad.append(f"creature {v} ({st['title']})")
        trial = next((st['trial'] for st in qq['stages'] if st['kind'] == 'trial'), None)
        tpl = marquee._template(trial)
        keys = {r['key'] for r in tpl['rooms']}
        if not (tpl['entrance'] in keys and all(w['room'] in keys for w in tpl['waves']) and tpl['boss']['room'] in keys
                and all(ex['to'] in keys for r in tpl['rooms'] for ex in r['exits'].values())):
            bad.append('trial rooms')
        for vnum in {v for w in tpl['waves'] for v, _n in w['mobs']} | {tpl['boss']['vnum']}:
            if vnum not in world.mob_prototypes:
                bad.append(f'trial creature {vnum}')
        if not (world.mob_prototypes.get(tpl['boss']['vnum']) or {}).get('boss_config'):
            bad.append('the trial boss has no boss config')
        giver = world.mob_prototypes.get(qq['giver']) or {}
        if giver.get('special') != 'guildmaster' or qq['ability'] not in ma.ABILITIES or \
                mastery.QUEST_ABILITIES.get(qq['ability']) != qq['name']:
            bad.append('giver / ability / book')
        check(not bad, f"{cls}: {qq['name']} points at real rooms and creatures, its trial hangs together ({bad})")
    tpl = marquee._template('warrior')

    # too young: a hint; at 45: the offer
    gm = next(ch for ch in world.rooms[q['giver_room']].characters if getattr(ch, 'vnum', None) == q['giver'])
    kid = _world_player(world, 'Kid', q['giver_room'], level=30)
    await marquee.on_talk(kid, gm)
    check(said(kid, 'level 45') and not said(kid, 'marquee accept'), 'below level 45 the guildmaster says to come back')
    ann = _world_player(world, 'Ann', q['giver_room'], level=46)
    await marquee.on_talk(ann, gm)
    check(said(ann, 'A marquee quest: The Unbroken Banner') and said(ann, "marquee accept"), 'at 46 the guildmaster offers the quest')
    check(marquee.indicator(ann, q['giver']) == '!', "a '!' over the guildmaster")
    mage = _world_player(world, 'Mia', q['giver_room'], level=50, char_class='mage')
    await marquee.accept(mage)
    check(mage.marquee is None, 'another class cannot take the warrior quest')

    await marquee.accept(ann)
    m = ann.marquee
    check(m and m['n'] == 1 and m['party'] == ['Ann'] and m['stage'] == 0, 'accepted alone: a party of one')
    b = marquee.quest_block(ann)
    check(b['title'] == 'The Fallen Standard' and b['where']['vnum'] == 22005 and b['stage'] == 1 and b['of'] == 7,
          f"the tracker block: stage 1 of 7, marked at the West Wall Path ({b['where']})")
    j = marquee.journal_entry(ann)
    check(j['marquee'] and j['teaches'] == 'Unbroken Banner', 'the journal lists it, with what it teaches')

    # 1 talk: the figure is there (placed if need be) and speaking to it moves the quest on
    put(ann, world.rooms[22005])
    await marquee._step()
    crusader = next(ch for ch in world.rooms[22005].characters if getattr(ch, 'vnum', None) == 22098)
    await marquee.on_talk(ann, crusader)
    check(m['stage'] == 1, 'speaking with the dying crusader ends stage 1')

    # 2 kill: each war-chief appears when you come near, made for the party
    run = marquee.RUNS['ann']
    for i, sp in enumerate(q['stages'][1]['spawns']):
        put(ann, world.rooms[sp['room']])
        await marquee._step()
        chief = next(x for x in run.mobs if x.marquee_tag.get('slot') == i)
        if i == 0:
            check(chief.max_hp == ms.foe_health('elite', m['level'], 1, 'warrior') and chief.hp == chief.max_hp,
                  f"a war-chief's health is made for one ({chief.max_hp})")
            check(not any(x.marquee_tag.get('escort') is not None for x in run.mobs), 'alone: no thralls with it')
            stranger = _world_player(world, 'Sam', sp['room'], level=50)
            hit = await chief.take_damage(500, stranger)
            check(chief.hp == chief.max_hp and not hit and said(stranger, "belongs to Ann's quest"),
                  "someone outside the party cannot hurt it")
            put(stranger, world.rooms[3001])
        chief.hp = 0
        await marquee.fallen(chief, ann)
    check(m['stage'] == 2, 'three war-chiefs down: stage 2 done')

    # 3 collect: shades in the ash; about half give a core
    st = q['stages'][2]
    put(ann, world.rooms[st['rooms'][0]])
    import random as _r
    _r.seed(4)
    for _ in range(40):
        if m['stage'] != 2:
            break
        await marquee._step()
        run.respawn = {}
        shade = next((x for x in run.mobs if marquee._alive(x)), None)
        if shade is not None:
            shade.hp = 0
            await marquee.fallen(shade, ann)
    check(m['stage'] == 3, 'enough ember cores: stage 3 done')

    # 4 the warden: a boss, faster for a bigger party
    put(ann, world.rooms[6908])
    await marquee._step()
    smith = next(x for x in run.mobs if x.marquee_tag.get('slot') == 0)
    check(getattr(smith, 'boss_config', None) is not None and smith.max_hp == ms.foe_health('warden', m['level'], 1, 'warrior'),
          'the Cinder Smith is a boss made for one')
    smith.hp = 0
    await marquee.fallen(smith, ann)
    check(m['stage'] == 4, 'the Cinder Smith down: stage 4 done')

    # 5 the ritual: plant, hold, slay what comes; leaving breaks it
    put(ann, world.rooms[8002])
    await marquee.plant(ann)
    check(run.ritual is not None, 'the banner is planted')
    put(ann, world.rooms[8001])
    await marquee._step()
    check(run.ritual is None and said(ann, 'The banner topples'), 'walking away breaks the ritual')
    put(ann, world.rooms[8002])
    await marquee.plant(ann)
    run.ritual['start'] -= 40           # thirty seconds held
    await marquee._step()
    waves = [x for x in run.mobs if x.marquee_tag.get('wave') is not None]
    check(len(waves) == 7, f'three waves of drakelings came (7: {len(waves)})')
    for x in waves:
        x.hp = 0
    await marquee._step()
    check(m['stage'] == 5, 'held and cleared: stage 5 done')

    # 6 the trial: a private copy; gates open as the waves fall; the boss; it closes behind you
    await marquee.enter_trial(ann)
    t = run.trial
    check(t is not None and ann.room is t.rooms['wall'] and ann.room.vnum // 100 == t.zone.number and t.zone.number >= 7000,
          f'inside the trial (zone {t and t.zone.number})')
    check(getattr(ann.room, 'instance_exit', None) == 8002, 'its rooms name the way back (a save there comes back at the gate)')
    gate = ann.room.exits['north']['door']
    check(gate['state'] == 'closed' and gate['locked'], 'the portcullis is locked until the wave falls')
    for wave in range(3):
        room = t.rooms[tpl['waves'][wave]['room']]
        put(ann, room)
        await marquee._step()
        foes = [x for x in run.mobs if x.marquee_tag.get('wave') == wave]
        check(len(foes) == sum(c for _v, c in tpl['waves'][wave]['mobs']), f'wave {wave + 1}: {len(foes)} foes')
        for x in foes:
            x.hp = 0
        await marquee._step()
    check(t.rooms['wall'].exits['north']['door']['state'] == 'open' and t.rooms['breach'].exits['north']['door']['state'] == 'open',
          'both gates opened')
    put(ann, t.rooms['keep'])
    await marquee._step()
    check(t.boss is not None and t.boss.max_hp == ms.foe_health('boss', m['level'], 1, 'warrior'), "Gorrund waits in the keep")
    t.boss.hp = 0
    await marquee._step()
    check(m['stage'] == 6 and t.won, 'Gorrund down: the trial is won')
    vnums = [r.vnum for r in t.rooms.values()]
    await marquee.leave_trial(ann)
    check(ann.room.vnum == 8002, 'trial leave: back at the gate')
    for _ in range(2):
        t.empty_since = (t.empty_since or 0) - 10
        await marquee._step()
    check(run.trial is None and not any(v in world.rooms for v in vnums), 'the empty trial closed and its rooms left the world')

    # 7 home: the guildmaster teaches it
    put(ann, world.rooms[q['giver_room']])
    check(marquee.indicator(ann, q['giver']) == '?', "a '?' over the guildmaster when you come home")
    await marquee.on_talk(ann, gm)
    check(ann.skills.get('unbroken_banner') == 50 and ann.marquee is None and 'ann' not in marquee.RUNS,
          'the guildmaster teaches Unbroken Banner (50%); the quest is done')
    ann.sent.clear()
    await marquee.on_talk(ann, gm)
    check(not said(ann, 'A marquee quest') and marquee.eligible(ann) == 'learned', 'it is not offered again once learned')

    # a party of three: embarking fixes the size; every foe is made for it; any member's kill counts
    bo = _world_player(world, 'Bo', q['giver_room'], level=52, connection=True, char_class='mage')
    cy = _world_player(world, 'Cy', q['giver_room'], level=50, connection=True, char_class='cleric')
    lea = _world_player(world, 'Lea', q['giver_room'], level=46, connection=True)
    grp = types.SimpleNamespace(members=[lea, bo, cy], leader=lea)
    for p in (lea, bo, cy):
        p.group = grp
    await marquee.accept(lea)
    check('lea' in marquee.VOTES and said(bo, "marquee join"), 'the group beside her is asked to embark')
    await marquee.answer(bo, True)
    await marquee.answer(cy, True)
    m3 = lea.marquee
    check(m3 and m3['n'] == 3 and m3['party'] == ['Lea', 'Bo', 'Cy'] and bo.marquee_help['owner'] == 'Lea',
          'three embarked: the party is fixed at three')
    check(m3['level'] == 49, f"the quest's level is the party's average when higher ({m3['level']})")
    check(m3['classes'] == ['warrior', 'mage', 'cleric'], f"and who embarked is kept (its foes are made for them: {m3['classes']})")
    m3['stage'] = 1
    run3 = marquee.RUNS['lea']
    put(bo, world.rooms[22030])
    await marquee._step()
    chief = next(x for x in run3.mobs if x.marquee_tag.get('slot') == 0)
    party = ['warrior', 'mage', 'cleric']
    check(chief.max_hp == ms.foe_health('elite', 49, 3, party) and abs(chief._dmg_scale - ms.foe_damage_scale('elite', 3, party, 49)) < 1e-9
          and chief.max_hp < ms.foe_health('elite', 49, 3, 'warrior'),
          f'made for three: x2.6 health, +20% damage, sized to a warrior, a mage and a cleric ({chief.max_hp})')
    check(sum(1 for x in run3.mobs if x.marquee_tag.get('escort') == 0) == 1, 'and one thrall at its side')
    chief.hp = 0
    await marquee.fallen(chief, bo)
    check(m3['progress']['dead'][0], "a helper's kill counts for the quest")
    put(bo, world.rooms[22024])
    await marquee._step()
    chief2 = next(x for x in run3.mobs if x.marquee_tag.get('slot') == 1)
    del world.players['lea']                # the owner drops out mid-fight
    await chief2.take_damage(300, bo)
    check(chief2.hp < chief2.max_hp, 'with the owner away, a helper can still fight what is already out')
    world.players['lea'] = lea
    await marquee.abandon(cy)
    check(cy.marquee_help is None and m3['n'] == 3 and 'Cy' not in m3['party'], 'a helper may leave; the quest stays as hard')
    await marquee.abandon(lea, confirm=True)
    check(lea.marquee is None and bo.marquee_help is None and not run3.mobs, 'abandoned: foes gone, helpers released')

    # every other class's quest, played through
    for cls in ('mage', 'cleric', 'paladin', 'necromancer', 'thief', 'ranger', 'bard', 'assassin'):
        await drive(world, marquee, cls)
    logging.disable(logging.NOTSET)


# the quest's foes as a room shows them (their long line, or "<name> is here, fighting YOU!")
FOES = (('siegeman', 'siegeman'), ('siege hound', 'hound'), ('gorrund', 'gorrund'), ('drakeling', 'drakeling'))


def foe_in(look, words=None):
    for line in look.splitlines():
        low = line.lower()
        if low.startswith('the corpse') or (' here' not in low and ' strains forward' not in low):
            continue
        for key, word in (words or FOES):
            if key in low:
                return word
    return None


async def fight_here(tn, limit=240, words=None):
    """Fight every quest foe standing here (by its room line), restoring when low."""
    t0 = time.time()
    log = ''
    while time.time() - t0 < limit:
        look = await tn.cmd('look', 0.8)
        word = foe_in(look, words)
        if not word:
            return log
        out = await tn.cmd(f'kill {word}', 1.0)
        for _ in range(40):
            if 'is DEAD' in out:
                break
            chunk = await tn.read(1.5)
            out += chunk
            hp = re.findall(r'(\d+)/(\d+)hp', chunk)
            if hp and int(hp[-1][0]) < int(hp[-1][1]) // 2:
                await tn.cmd('restore', 0.3)
        log += out
    return log


RAISED = {}   # what live() changed on Gauntlet: field -> the value it had


async def unraise():
    """Gauntlet as it was before live() raised it."""
    if not RAISED:
        return
    tn = tw.Telnet()
    await tn.open()
    for field, value in RAISED.items():
        if value is not None:
            await tn.cmd(f'set gauntlet {field} {value}', 0.5)
    for line in ('restore', 'save', 'quit'):
        await tn.cmd(line, 0.5)
    tn.w.close()
    RAISED.clear()


async def live():
    """The warrior's quest on the running server with the test warrior (level 60, an immortal for
    the jumps): offer, accept, the first stage, the tracker in the map payload and the journal,
    a jump to the trial, the trial fought through (waves, gates, Gorrund), the return, the ability."""
    await gauntlet_accounts.ensure()
    tn = tw.Telnet()
    await tn.open()
    # the quest is offered from level 45 and live_group's foes are sized for 60: a Gauntlet below
    # that is raised as live_classes raises its characters, and put back by unraise()
    await tn.cmd('save', 0.6)
    was = gauntlet_accounts.saved('Gauntlet') or {}
    if (was.get('level') or 0) < 60:
        RAISED.update({f: was.get(k) for f, k in (('level', 'level'), ('maxhp', 'max_hp'), ('damroll', 'damroll'), ('hitroll', 'hitroll'))})
        for line in ('set gauntlet level 60', 'set gauntlet maxhp 900', 'set gauntlet damroll 150', 'set gauntlet hitroll 40'):
            await tn.cmd(line, 0.5)
    for line in ('wake', 'stand', 'restore', 'marquee forget'):
        await tn.cmd(line, 0.5)
    await tn.cmd('goto 3023', 0.8)
    text = await tn.cmd('talk guildmaster', 1.2)
    check('A marquee quest: The Unbroken Banner' in text, 'the guildmaster offers the quest')
    text = await tn.cmd('marquee accept', 1.2)
    check('You set out alone' in text and 'The Fallen Standard (1/7)' in text, 'accepted alone: stage 1 of 7')

    async with aiohttp.ClientSession() as http:
        async with http.ws_connect(f'ws://{tw.HOST}:{tw.MAP}/') as ws:
            await ws.send_str(tw.subscribe(tw.CHAR))
            block = None
            for _ in range(40):
                msg = await asyncio.wait_for(ws.receive(), timeout=10)
                d = json.loads(msg.data) if msg.type == aiohttp.WSMsgType.TEXT else {}
                if d.get('type') == 'map_data':
                    block = d['player'].get('quest')
                    break
    check(block and block['title'] == 'The Fallen Standard' and (block.get('where') or {}).get('vnum') == 22005,
          f"the map payload carries the tracker ({block and block['title']}, marked {block and block.get('where')})")
    journal = tw.get_json(f'/quests?player={tw.CHAR}&t={tw.TOKEN}')
    mq_entry = next((q for q in journal.get('active', []) if q.get('marquee')), None)
    check(mq_entry and mq_entry['teaches'] == 'Unbroken Banner', 'the journal lists the marquee quest first')

    await tn.cmd('goto 22005', 2.5)
    text = await tn.cmd('talk crusader', 1.5)
    check('The Banner-Reavers (2/7)' in text, 'speaking with the dying crusader: stage 2')

    await tn.cmd('marquee stage 6', 0.8)
    await tn.cmd('goto 8002', 1.0)
    text = await tn.cmd('trial enter', 2.0)
    check('The Last Bastion - The Outer Wall' in text, 'trial enter: inside the Last Bastion')
    for step, (way, into) in enumerate((('north', 'The Breach'), ('north', 'The Keep'), (None, None))):
        await tn.read(3.5)
        # (a raised Gauntlet with a short sword takes about 4 minutes over Gorrund: the
        # budget is twice that, and the helper returns as soon as the room is clear)
        log = await fight_here(tn, limit=480)
        if step == 1:                       # the breach has a second wave
            await tn.read(3.0)
            log += await fight_here(tn)
        if way:
            await tn.read(1.6)              # the gate opens on the quest's next tick
            text = await tn.cmd(way, 1.5)
            ok = f'The Last Bastion - {into}' in text
            check(ok, f'the gate opened after the wave: {way} into {into}' + ('' if ok else f'\n{text[-900:]}'))
    await tn.read(1.6)
    text = await tn.cmd('marquee', 1.0)
    check('The Last Lesson (7/7)' in text, 'Gorrund down: the last stage')
    text = await tn.cmd('trial leave', 1.5)
    check("Dragon's Gate" in text, 'trial leave: back at the gate')
    await tn.cmd('goto 3023', 1.0)
    text = await tn.cmd('talk guildmaster', 2.0)
    check('You learned Unbroken Banner' in text, 'home: the guildmaster teaches Unbroken Banner')
    text = await tn.cmd('unbroken banner', 1.2)
    check('UNBROKEN' in text, 'and it works')
    text = await tn.cmd('unbroken banner', 1.0)
    check('not ready yet' in text, 'with its long cooldown')
    for line in ('marquee forget', 'recall', 'save', 'quit'):
        await tn.cmd(line, 0.6)
    tn.w.close()


async def live_group():
    """Two players: the group beside the warrior is asked to embark; who joins makes every foe
    harder (x1.8 health for two); giving the quest up releases the helper."""
    import marquee_scale as ms
    import test_multiplayer as tmu
    g = await tmu.Raw('gauntlet', 'Gauntlet').open()
    b = await tmu.Raw('gauntletb', 'Gauntletb').open()
    for line in ('wake', 'stand', 'restore', 'marquee forget', 'group leave', 'goto 3023'):
        await g.cmd(line, 0.5)
    for line in ('wake', 'stand', 'marquee leave', 'group leave', 'goto 3023'):
        await b.cmd(line, 0.5)
    await g.cmd('group invite gauntletb', 0.8)
    await b.cmd('group accept', 0.8)
    text = await g.cmd('marquee accept', 1.0)
    check('You ask Gauntletb to embark' in text, 'accepting asks the group member beside you to embark')
    text = tmu.ANSI.sub('', await b.read(0.8))
    check('marquee join' in text, 'the member is asked to join')
    await b.cmd('marquee join', 1.0)
    text = await g.read(1.0)
    check('2 embarked' in text, f"both set out: two embarked ({text.strip().splitlines()[-2:] if text.strip() else ''})")
    text = await b.cmd('marquee', 0.8)
    check('The Fallen Standard' in text and 'with Gauntlet' in text, "the helper sees the quest they share")
    await g.cmd('marquee stage 2', 0.8)
    await g.cmd('goto 22030', 1.0)
    await g.read(3.5)
    text = await g.cmd('kill warchief', 1.5)
    hp = re.findall(r'Banner-Reaver war-\s*chief: \d+/(\d+)', text)      # (the prompt may wrap inside the name)
    want = ms.foe_health('elite', 60, 2, 'warrior')
    check(hp and int(hp[-1]) == want, f'a war-chief made for two: {hp[-1] if hp else "?"} health (x1.8 = {want})')
    await g.cmd('restore', 0.4)
    await g.cmd('marquee abandon confirm', 1.0)
    text = await b.read(1.0)
    check('gives up the quest' in text, 'giving it up tells the helper')
    text = await b.cmd('marquee', 0.8)
    check('no marquee quest' in text, 'and releases them')
    for line in ('group leave', 'recall', 'save', 'quit'):
        await b.cmd(line, 0.5)
        await g.cmd(line, 0.5)
    g.w.close()
    b.w.close()


# a test character of each class (on the gauntletb account) and how to start a fight for its ability
CLASS_CHARS = {'mage': ('gauntletb', 'Probemage'), 'cleric': ('gauntletb', 'Probecleric'),
               'paladin': ('gauntletb', 'Probepaladin'), 'necromancer': ('gauntletb', 'Probenecro'),
               'thief': ('gauntletb', 'Probethief'), 'ranger': ('gauntletb', 'Proberanger'),
               'bard': ('gauntletb', 'Probebard'), 'assassin': ('gauntlet', 'Probeassn')}
LEARNED = {'singularity': 'Singularity', 'seraphs_vigil': "Seraph's Vigil", 'wings_of_dawn': 'Wings of Dawn',
           'lich_ascension': 'Lich Ascension', 'heist': 'The Heist of Ages', 'heartseeker': 'Heartseeker',
           'song_of_the_ages': 'Song of the Ages', 'thousand_shadows': 'Thousand Shadows'}
USED = {'singularity': 'singularity opens', 'seraphs_vigil': 'SERAPH', 'wings_of_dawn': 'DAWN', 'lich_ascension': 'ASCEND',
        'heist': 'behind every one of them', 'heartseeker': 'draw the Heartseeker', 'song_of_the_ages': 'Song of the Ages',
        'thousand_shadows': 'thousand of them'}
# the word that finds each guildmaster with `talk`
GM_WORD = {3031: 'paladin', 3033: 'necromancer', 3030: 'ranger', 3032: 'bard'}


async def live_classes(classes=('mage', 'cleric', 'paladin', 'necromancer'), fight='mage'):
    """Each class's quest on the server with its test character: the offer and acceptance at its
    guildmaster, a jump to the trial (entered and left), the return that teaches the marquee
    ability, and the ability used on a foe; one class fights its trial through."""
    import marquee_quests as mq
    import test_multiplayer as tmu
    for cls in classes:
        q = mq.QUESTS[cls]
        account, who = CLASS_CHARS[cls]
        me = who.lower()
        p = await tmu.Raw(account, who).open()
        for line in ('wake', 'stand', f'set {me} level 50', f'set {me} maxhp 900', f'set {me} maxmana 900',
                     f'set {me} damroll 150', f'set {me} hitroll 40', 'restore', 'marquee forget', f"goto {q['giver_room']}"):
            await p.cmd(line, 0.6)
        word = GM_WORD.get(q['giver'], 'guildmaster')
        n = len(q['stages'])
        trial_at = next(i for i, st in enumerate(q['stages']) if st['kind'] == 'trial')
        text = await p.cmd(f'talk {word}', 1.2)
        check(f"A marquee quest: {q['name']}" in text, f"{cls}: the guildmaster offers {q['name']}")
        text = await p.cmd('marquee accept', 1.2)
        check('You set out alone' in text and f"{q['stages'][0]['title']} (1/{n})" in text, f'{cls}: accepted, stage 1 of {n}')
        gate = q['stages'][trial_at]['room']
        await p.cmd(f'marquee stage {trial_at + 1}', 0.8)
        await p.cmd(f'goto {gate}', 1.2)
        text = await p.cmd('trial enter', 2.0)
        tpl = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'world', 'marquee', 'trials', f'{cls}.json')))
        check(tpl['rooms'][0]['name'] in text, f"{cls}: inside the trial ({tpl['rooms'][0]['name']})")
        if cls == fight:
            for step, (way, into) in enumerate((('north', tpl['rooms'][1]['name']), ('north', tpl['rooms'][2]['name']), (None, None))):
                await p.read(3.5)
                log = await fight_here(p, words=TRIAL_FOES[cls])
                if step == 1:
                    await p.read(3.0)
                    log += await fight_here(p, words=TRIAL_FOES[cls])
                if way:
                    await p.read(1.6)
                    text = await p.cmd(way, 1.5)
                    check(into in text, f'{cls}: the gate opened after the wave ({into})')
            await p.read(1.6)
            text = await p.cmd('marquee', 1.0)
            check(f"{q['stages'][-1]['title']} ({n}/{n})" in text, f"{cls}: the trial's boss is down: the last stage")
        text = await p.cmd('trial leave', 1.5)
        check('fades' in text or 'thins' in text or 'stand at' in text, f'{cls}: out of the trial again')
        await p.cmd(f'marquee stage {n}', 0.8)
        await p.cmd(f"goto {q['giver_room']}", 1.0)
        text = await p.cmd(f'talk {word}', 2.0)
        check(f"You learned {LEARNED[q['ability']]}" in text, f"{cls}: the guildmaster teaches {LEARNED[q['ability']]}")
        # use it on a foe
        await p.cmd('goto 3054', 0.8)
        await p.cmd('mload 9704', 0.8)
        await p.cmd('kill siegeman', 1.0)
        text = await p.cmd(q['ability'].replace('_', ' '), 1.6)
        check(USED[q['ability']] in text and 'Something went wrong' not in text,
              f"{cls}: {LEARNED[q['ability']]} used in a fight ({' / '.join(l for l in text.splitlines() if l.strip())[:120]})")
        text = await p.cmd(q['ability'].replace('_', ' '), 1.0)
        check('not ready' in text, f'{cls}: and then it is on its cooldown')
        for line in ('purge', 'restore', 'marquee forget', 'recall', 'save', 'quit'):
            await p.cmd(line, 0.6)
        p.w.close()   # (logged out, not left linkdead: the next test logs into the same account)


# the trial's foes by the words a room shows them with
TRIAL_FOES = {'mage': (('sentinel', 'sentinel'), ('gravity mote', 'mote'), ('vaelith', 'vaelith')),
              'ranger': (('thorn-stalker', 'stalker'), ('hatchling', 'hatchling'), ('gloomfang', 'gloomfang'))}


async def main():
    await offline()
    await engine()
    if '--offline' not in sys.argv:
        try:
            await live()
            await live_group()
        finally:
            await unraise()
        await live_classes()
        await live_classes(('thief', 'ranger', 'bard', 'assassin'), fight='ranger')
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
