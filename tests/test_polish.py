#!/usr/bin/env python3
"""Player-experience polish (the owner: "complete all the suggested fixes"):

- a dark room is dark in /play: the zone map payload says how the player sees it
  (map_system._sight): dark or not, a light carried, able to see at all;
- a caster's mana stays in its orb, its class resource as pips (hud.js CASTERS), and big numbers
  are shortened on the orbs (200000 -> 200k);
- exit signs fade with distance and in a fight (terrain.js LABEL_FADE), and Tab keeps to the
  hero's own room first (main.js);
- combat numbers: where they show, their size and screen shake are settings, with a colour key;
  bursts of small hits add up; the shake grows with the blow;
- rooms: ice and lava caves, a zone's own stone and light (zone_tone.py), set pieces laid out by
  hand (setpieces.py, world/setpieces.json).

    python3 tests/test_polish.py
"""
import asyncio
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
WEB = os.path.join(HERE, '..', 'src', 'web_isometric', 'world3d')

FAILED = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok:
        FAILED.append(what)


def src(name):
    return open(os.path.join(WEB, name), encoding='utf-8').read()


async def main():
    logging.disable(logging.WARNING)
    from config import Config
    from world import World
    from player import Player
    import map_system
    world = World(Config())
    await world.load()
    p = Player.create_new(name='Lumen', password=None, race='human', char_class='cleric',
                          stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    p.world = world
    dark = next(r for r in world.rooms.values() if 'dark' in (r.flags or []))
    p.room = dark
    s = map_system._sight(p)
    check(s == {'dark': True, 'light': False, 'see': False}, f'a dark room, no light: dark and unseen ({s})')
    p.room = world.rooms[3001]
    check(map_system._sight(p) == {'dark': False}, 'a lit room is not dark')
    p.room = dark
    real = Player.has_light_source
    Player.has_light_source = lambda self: True
    try:
        s = map_system._sight(p)
        check(s['dark'] and s['light'] and s['see'], f'carrying a light: dark, lit, seen ({s})')
    finally:
        Player.has_light_source = real
    payload = map_system.build_zonemap  # (the payloads carry it)
    ms = open(map_system.__file__, encoding='utf-8').read()
    check(ms.count("'sight': _sight(player)") == 2, 'both player payloads carry the sight')

    hud = src('hud/hud.js')
    check("const CASTERS = new Set(['mage', 'necromancer', 'cleric', 'paladin', 'bard'])" in hud and 'classRes && !caster' in hud,
          "a caster's orb is its mana, a fighter's its resource")
    check('compact(p.hp)' in hud, 'orbs shorten big numbers')
    check('LABEL_FADE.combat' in src('main.js') and 'export const LABEL_FADE' in src('terrain.js'), 'exit signs fade with distance and in a fight')
    check('e.vnum === heroRoom.vnum' in src('main.js'), "Tab keeps to the hero's own room first")
    check('engine.darkness' in src('main.js') and 'darkness: 0' in src('engine.js'), 'the engine darkens a dark room')

    # ---- batch 2: combat numbers and feel
    html = src('play.html')
    check(all(f'data-set="{k}"' in html for k in ('sct', 'sctsize', 'shake')) and 'id="sct-key"' in html,
          'settings: combat numbers, their size, screen shake, the colour key')
    fx, combat = src('fx.js'), src('combat.js')
    check("this.opts.sct === 'off'" in fx and 'if (!this.opts.shake) return;' in fx and '* this.opts.size' in fx, 'fx obeys the settings')
    check('×${last.n}' in combat, 'a burst of small hits adds up in one number')
    check('bite * 1.6' in combat and 'killing ? 110' in combat, 'the shake and the pause grow with the blow')

    # ---- dying says what it cost and where you wake
    import combat_events as ev
    sent = []
    real = ev.emit_private
    ev.emit_private = lambda ch, k, src=None, dst=None, **f: sent.append(dict(k=k, **f))
    try:
        v = Player.create_new(name='Mortis', password=None, race='human', char_class='warrior',
                              stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
        v.world, v.room = world, world.rooms[3001]
        world.rooms[3001].characters.append(v)
        v.exp, v.gold = 10000, 1000
        await v.die(None) if hasattr(v, 'die') else None
    finally:
        ev.emit_private = real
    f = next((e for e in sent if e['k'] == 'fallen'), None)
    check(f is not None and f['exp'] > 0 and f['gold'] == 50 and f['wake'], f'the death card is told the cost and where you wake ({f})')
    check("Slain by ${d.killer}" in src('hud/hud.js'), 'the death card shows them')

    # ---- batch 3: gear and loot
    inv = src('hud/inventory.js')
    check("import { compare } from '../gearcompare.js'" in inv and 'up-badge' in inv and 'tt-cmp' in inv,
          'tooltips compare with what you wear; better pieces carry a green arrow')
    check('tooltip(r.item, MH.state && MH.state.player)' in src('hud/lootwin.js'), "a corpse's loot window compares too")
    loot = src('loot.js')
    check('rarityBeam(' in loot and 'bestRarity(g.item.contents)' in loot, 'drops and rich corpses show a beam of their rarity')

    # ---- batch 4: where to go for an ordinary quest
    import datetime
    import quest_guide
    from quests import ActiveQuest, QuestObjective, QUEST_DEFINITIONS as Q

    def give(qid):
        d = Q[qid]
        return ActiveQuest(quest_id=qid, name=d['name'], description=d['description'], quest_type=d['type'],
                           objectives=[QuestObjective(**{k: v for k, v in o.items() if not k.startswith('_')}) for o in d['objectives']], rewards=d['rewards'],
                           started_at=datetime.datetime.now())
    g = Player.create_new(name='Wayfarer', password=None, race='human', char_class='warrior',
                          stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    g.world, g.room = world, world.rooms[3001]
    visit = next(k for k, q in Q.items() if q.get('objectives') and q['objectives'][0]['type'] == 'visit' and str(q['objectives'][0]['target']) == '3054')
    g.active_quests = [give(visit)]
    b = map_system._quest_block(g)
    check(b and b['kind'] == 'quest' and b['where']['vnum'] == 3054 and b['where']['dir'], f'a visit quest: the room, and the first step there ({b and b.get("where")})')
    g.active_quests = [give('message_for_mayor')]
    w = map_system._quest_block(g)['where']
    check(w and w['steps'] > 0 and w['dir'], f'a talk quest: the way to the one to speak with ({w})')
    q = give('message_for_mayor')
    for o in q.objectives:
        o.completed = True
    g.active_quests = [q]
    b = map_system._quest_block(g)
    check(b['title'].startswith('Return to ') and b.get('where'), f"done: back to the quest's giver ({b['title']})")
    g.active_quests = []
    check(map_system._quest_block(g) is None, 'no quest, no tracker')
    check('zone.passageWorld(heroRoom, w.dir)' in src('main.js'), 'a gold arrow by the hero points the way out of the room')

    # ---- batch 5: rooms drawn as their words say: ice and fire caves, a zone's own stone and
    # light, set pieces laid out by hand
    import room_looks
    import zone_tone
    import setpieces
    check({'ice_cave', 'lava_cave'} <= room_looks.UNDERGROUND, 'ice and lava caves are roofed, underground looks')
    check(world.rooms[20572].look == 'ice_cave' and world.rooms[20597].look == 'lava_cave', 'an ice cave and a lava cave drawn so')
    check(zone_tone.read(['A hall of black stone.'] * 8) == {'stone': 'black'}, 'a zone of black stone is black')
    check(zone_tone.read(['A dark room.'] * 8 + ['White marble.']) is None, 'a stray mention is no tone')
    check(zone_tone.read(['Green ghost-fire burns.'] * 6) == {'light': 'ghost'}, 'ghost-fire is a ghost light')
    toned = [r for r in world.rooms.values() if getattr(r, 'tone', None)]
    check(0 < len(toned) < len(world.rooms) / 4, f'some zones have a tone, most none ({len(toned)} rooms)')
    sp = setpieces.load()
    throne = world.rooms[24527]
    check(throne.setpiece == {'light': sp['24527']['light']} and throne.features[0]['x'] == 12, 'the Throne of Shadows is laid out by hand, with its light')
    zm = map_system.build_zonemap(world, throne.zone.number)
    room = next((r for r in zm['rooms'] if r.get('vnum') == 24527), None)
    check(room and room.get('setpiece') and room.get('features') and 'tone' in room, 'the zone map carries set pieces and tones')
    check('TONE_STONE[layout.tone.stone]' in src('terrain.js') and 'TONE_LIGHT[L.tone.light]' in src('main.js'), "/play tints a zone's stone and light")

    # ---- batch 6: the tutorial in /play (found playing it as a newcomer)
    check(quest_guide.web_text('Check your score (type "score")') == 'Check your score: open your Character sheet (C)',
          'a "type score" step says which window to open')
    g.room = world.rooms[3001]
    g.active_quests = [give('tutorial_3_know_thyself')]
    b = map_system._quest_block(g)
    check('(C)' in b['title'] and 'where' not in b, f"a step done where you stand: how, and no arrow ({b['title']})")
    from commands import CommandHandler
    sent = []
    g.send = lambda *a, **k: asyncio.sleep(0, sent.append(a))
    await CommandHandler.cmd_uiseen(g, ['character'])
    q = g.active_quests[0]
    check(all(o.completed for o in q.objectives if o.target in ('score', 'equipment')), 'opening the Character sheet counts as score and equipment')
    await CommandHandler.cmd_uiseen(g, ['spellbook'])
    check(all(o.completed for o in q.objectives if o.target in ('skills', 'spells')), 'opening the Spellbook counts as skills and spells')
    g.active_quests = [give('tutorial_9_newbie_zone')]
    for o in g.active_quests[0].objectives[:2]:
        o.completed = True
    g.room = world.rooms[18600]
    b = map_system._quest_block(g)
    check(b.get('where') and b['where']['steps'] >= 0, f'"defeat any 3 creatures": the way to the nearest fair fight ({b.get("where")})')
    hud = src('hud/hud.js')
    check('uiseen ${name}' in hud, 'the HUD tells the server when a window opens')
    net = open(os.path.join(WEB, '..', 'shared', 'net.js'), encoding='utf-8').read()
    check("MH.bus.emit('connection.lost')" in net and 'MH.awaitServer' in net and 'connection.lost' in src('main.js') and "classList.contains('done') ? $('#resume-btn').click()" in src('hud/login.js'),
          'a dropped connection waits for the server and signs back in')

    zm = map_system.build_zonemap(world, world.rooms[3001].zone.number)
    temple = next(r for r in zm['rooms'] if r['vnum'] == 3001)
    up = temple['exits'].get('up') or {}
    check(up.get('imm') is True and 'if (e.imm) delete r.exits[d]' in src('zone.js'),
          "the Temple's stairs to the God Rooms are not drawn for players who can't take them")
    check('.xbar.unused' in src('hud/hud.css') and "classList.toggle('unused'" in src('hud/hud.js'),
          'an extra action bar with nothing on it stays faded until used')
    msgs = []
    class Conn:
        is_web = True
    g.connection = Conn()
    check(quest_guide.for_player(g, 'Rest to recover (type "rest")') == 'Rest to recover: right-click yourself, then Rest',
          'the chat log words tutorial steps for /play too')
    g.connection = None

    # a quest that moves on where you stand (a talk, a window, a kill) refreshes the tracker now
    pushed = []

    class WM:
        def has_play(self, pl):
            return True

        async def notify_player(self, pl):
            pushed.append(pl.name)
    real_wm = getattr(world, 'web_map', None)
    world.web_map = WM()
    try:
        g.active_quests = [give('tutorial_3_know_thyself')]
        await CommandHandler.cmd_uiseen(g, ['inventory'])
        await asyncio.sleep(0)
        check(pushed, f'a step done in place sends the tracker at once ({pushed})')
    finally:
        world.web_map = real_wm

    # the training dummy falls: the tutorial step completes there and then, the next one begins
    from quests import QuestManager
    g.active_quests = [give('tutorial_5_combat')]
    g.active_quests[0].objectives[0].completed = True
    g.active_quests[0].objectives[0].current = 1
    await QuestManager.check_quest_progress(g, 'kill', {'mob_vnum': 3078, 'mob_name': 'a training dummy', 'mob_keywords': 'dummy training'})
    ids = [q.quest_id for q in g.active_quests]
    check('tutorial_5_combat' not in ids and 'tutorial_6_healing' in ids, f'a tutorial kill completes the step at once ({ids})')

    # lighter dark rooms and dim moods (the owner: "too dark in some of the rooms"), and a
    # Brightness setting on top
    eng = src('engine.js')
    check("lit ? 0.35 : eyes ? 0.35 : 0.6" in src('main.js') and '(1 - 0.75 * darkNow)' in eng,
          'a dark room keeps most of its light with a lantern, and some without')
    check("data-set=\"bright\"" in open(os.path.join(WEB, 'play.html'), encoding='utf-8').read()
          and "settings.brightness" in src('main.js') and '(api.brightness || 1)' in eng,
          'Settings -> Brightness lightens the whole picture')

    # the server on a laptop (the owner: "super laggy"): creatures where no player is think one
    # tick in ten, and a zone reset counts the world's creatures once, not once per reset line
    near = next(n for n in world.npcs if n.room and n.room.zone is world.rooms[3001].zone)
    far = next(n for n in world.npcs if n.room and n.room.zone is not world.rooms[3001].zone
               and all(getattr(getattr(e.get('room') if isinstance(e, dict) else None, 'zone', None), 'number', None)
                       != world.rooms[3001].zone.number for e in (n.room.exits or {}).values()))
    calls = {'near': 0, 'far': 0}

    async def count_near():
        calls['near'] += 1

    async def count_far():
        calls['far'] += 1
    near.process_ai, far.process_ai = count_near, count_far
    world.players['wayfarer'] = g
    g.room = world.rooms[3001]
    try:
        for _ in range(world.NPC_SLEEP_EVERY):
            await world.process_npcs()
    finally:
        world.players.pop('wayfarer', None)
        del near.process_ai, far.process_ai
    check(calls == {'near': world.NPC_SLEEP_EVERY, 'far': 1}, f'creatures by a player think every tick, the rest one in ten ({calls})')
    import time as _t
    for z in world.zones.values():
        z.age = z.lifespan
    t0 = _t.perf_counter()
    await world.zone_reset_tick()
    took = _t.perf_counter() - t0
    check(took < 3, f'a reset of every zone takes a moment, not seconds of a frozen server ({took:.2f}s; was ~8s)')

    # the owner's machine drew in software ("Microsoft Basic Render Driver", 3 fps): /play notices,
    # drops to Low and says why; far rooms are kept but not drawn; exit signs no longer overlap
    main_js = src('main.js')
    check('basic render driver|swiftshader|llvmpipe' in main_js and "engine.setQuality('low')" in main_js,
          'a browser drawing without a graphics card gets Low quality and a word on why')
    check('r.built.group.visible = far <= 3' in src('zone.js'), 'rooms kept for the way back are not drawn past the fog')
    check('x + inward * 4' in src('terrain.js'), "an exit's sign stands inside its own room, clear of the one across the edge")

    # combat numbers stay longer (the owner: "fades pretty fast"), weighted, with a setting and a cap
    fxs = src('fx.js')
    check('TEXT_LIFE = 1.45' in fxs and 'LANE_MAX = 7' in fxs and 'data-set="sctlife"' in open(os.path.join(WEB, 'play.html'), encoding='utf-8').read(),
          'combat numbers stay up longer, crits longest, with a Number duration setting and a cap on the crowd')

    # reaching into the next room (reach.py): a shot or a bolt across an open way pulls the
    # creature in; never melee, a sentinel, a closed door, a peaceful room, nor for telnet
    import reach
    import combat_range as cr
    from bosses import create_mob_from_prototype
    here, there = world.rooms[3002], world.rooms[3003]
    check(reach.joined(world, here, there) == 'east', 'the Temple Square and the market street are joined by an open way')
    mage = Player.create_new(name='Reacher', password=None, race='human', char_class='mage',
                             stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    mage.world, mage.room, mage.connection = world, here, object()
    here.characters.append(mage)
    told = []

    async def note(m, *a, **k):
        told.append(m)
    mage.send = note
    beast = create_mob_from_prototype(next(iter(world.mob_prototypes.values())), world)
    beast.flags = set(f for f in (beast.flags or ()) if f not in ('sentinel', 'boss'))
    beast.special, beast._web_uid, beast.owner = None, 990001, None

    def put(x):
        if beast.room is not None and beast in beast.room.characters:
            beast.room.characters.remove(beast)
        beast.room = there
        there.characters.append(beast)
        cr.set_pos(beast, x, 7.5)
    world.npcs.append(beast)
    put(2.0)
    mage.web_pos = (here.vnum, 22.0, 7.5)
    check(abs(reach.distance(world, mage, beast) - 4.0) < 0.01, 'distance is measured across the edge (4 m)')
    await reach.webpull(mage, ['#990001', 'attack'])
    check(beast.room is here and cr.pos_of(beast) == (23.0, 7.5), f"a mage's bolt pulls it in to the nearest point ({cr.pos_of(beast)})")
    import allies
    check(reach.pulled(beast), 'a creature pulled from afar is marked so')
    import asyncio as _aio
    check(_aio.get_event_loop() and (await allies.rally(beast, mage)) == [], 'and calls no friends to the fight (only the one aimed at comes)')
    beast.pulled_at = 0
    put(20.0)
    await reach.webpull(mage, ['#990001', 'attack'])
    check(beast.room is there and 'out of reach' in told[-1], "beyond the bolt's 10 m it stays")
    beast.web_pos = None          # a creature the server has no place for: measured where the screen shows it
    await reach.webpull(mage, ['#990001', 'attack', '@3.0,7.5'])
    check(beast.room is here, f"measured where the screen draws it (5 m), not its room's middle ({told[-1][:60]})")
    beast.pulled_at = 0
    put(2.0)
    await reach.webpull(mage, ['#990001', 'bash'])
    check(beast.room is there, 'a melee skill pulls nothing (the hero walks in)')
    beast.flags.add('sentinel')
    await reach.webpull(mage, ['#990001', 'attack'])
    check(beast.room is there and 'post' in told[-1], 'a creature that keeps its post is not pulled')
    beast.flags.discard('sentinel')
    ex = here.exits['east']
    had = ex.get('door')
    ex['door'] = {'name': 'door', 'state': 'closed'}
    await reach.webpull(mage, ['#990001', 'attack'])
    check(beast.room is there, 'not through a closed door')
    if had is None:
        ex.pop('door')
    else:
        ex['door'] = had
    there.flags.add('peaceful')
    await reach.webpull(mage, ['#990001', 'attack'])
    check(beast.room is there, 'not into a peaceful room')
    there.flags.discard('peaceful')
    came = reach.pull_area(mage, (23.5, 7.5), 4.0)
    check(beast in came and beast.room is here, 'an aimed circle across the edge catches it')
    put(2.0)
    check(reach.pull_area(beast, (2.0, 7.5), 30.0) == [], "a creature's own spell pulls no one")
    mage.web_pos = None
    await reach.webpull(mage, ['#990001', 'attack'])
    check(beast.room is there, 'a player with no position (telnet) keeps the old rules')
    # only what is aimed at a foe pulls, as the hero's own class book says
    import mastery
    for cls in ('warrior', 'paladin', 'cleric', 'ranger', 'mage', 'necromancer', 'thief', 'assassin', 'bard'):
        hero = Player.create_new(name='Probe' + cls[:3].title(), password=None, race='human', char_class=cls,
                                 stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
        wrong = [e['id'] for e in mastery.book(cls) if reach.action_range(hero, e['id'])[1] and e.get('target') not in (None, 'enemy')]
        check(not wrong, f'{cls}: no heal, blessing or self ability pulls ({wrong})')
    sin = Player.create_new(name='Probesin', password=None, race='human', char_class='assassin',
                            stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    check(not reach.action_range(sin, 'poison')[1] and reach.action_range(mage, 'magic_missile')[1],
          "an assassin's weapon poison pulls nothing; a mage's magic missile does")
    # a leap or a charge carries the hero over instead (the client sends the room move first,
    # then the ability: commands from one connection run in order)
    from commands import CommandHandler
    war = Player.create_new(name='Leaper', password=None, race='human', char_class='warrior',
                            stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    war.world, war.room, war.connection, war.level = world, here, object(), 50
    war.send = note
    here.characters.append(war)
    war.web_pos = (here.vnum, 22.0, 7.5)
    if beast.room is not there:
        put(2.0)
    hp0 = beast.hp
    await CommandHandler.execute(war, 'webmove', ['3002', '3003', 'east'])
    await CommandHandler.execute(war, 'heroic_leap', ['#990001'])
    check(war.room is there and beast.room is there and beast.hp < hp0,
          f'Heroic Leap from the next room lands on it ({war.room.vnum}, {hp0} -> {beast.hp})')
    check(all(cr.ABILITY_RANGE[k][1] == 'dash' for k in ('heroic_leap', 'charge', 'shadowstrike', 'death_from_above')),
          'the leaps and charges are dashes (the client carries the hero over for them)')
    for ch in (war, beast):
        ch.fighting = None
    # warriors and thieves throw: Heroic Throw and Knife Toss reach the next room and pull
    for who, ab in (('warrior', 'heroic_throw'), ('thief', 'knife_toss')):
        hero = Player.create_new(name='Thrower' + who[:3].title(), password=None, race='human', char_class=who,
                                 stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
        hero.level = 3
        mastery.grant_now(hero)
        check(ab in hero.skills and reach.action_range(hero, ab)[1] and reach.action_range(hero, ab)[0] >= 14,
              f'a {who} has {ab} at level 3, and it reaches the next room')
    war.fighting = None
    if beast.room is not there:
        put(2.0)
    war.room.characters.remove(war)
    war.room, war.web_pos = here, (here.vnum, 22.0, 7.5)
    here.characters.append(war)
    war.skills['heroic_throw'] = 50
    war.heroic_throw_cooldown = 0
    hp0 = beast.hp
    await reach.webpull(war, ['#990001', 'heroic_throw'])
    await CommandHandler.execute(war, 'heroic_throw', ['#990001'])
    check(beast.room is here and beast.hp < hp0, f'Heroic Throw pulls it in and wounds it ({hp0} -> {beast.hp})')
    for ch in (war, beast):
        ch.fighting = None
    # an aimed circle may land deep in the next room (no need to step in first)
    put(10.0)
    mage.web_pos = (here.vnum, 22.0, 7.5)
    aim = CommandHandler._aim_for(mage, 'meteor_storm', (34.0, 7.5))
    check(aim and aim[0] == 34.0, f'a meteor aimed 12 m away, 10 m into the next room, lands there ({aim})')
    from spells import SpellHandler
    caught = SpellHandler.foes_in_room(mage, aim)
    check(beast in caught and beast.room is here, 'what it catches there charges in and is struck')
    mage.web_pos = None
    check(CommandHandler._aim_for(mage, 'meteor_storm', (34.0, 7.5))[0] == 24.0, 'without a position the circle stays in the room')
    mage.web_pos = (here.vnum, 22.0, 7.5)
    war.room.characters.remove(war)
    beast.room.characters.remove(beast)
    world.npcs.remove(beast)
    here.characters.remove(mage)
    check('reachAcross(t, range, pulls)' in src('main.js') and 'webpull ${refFor(t)}' in src('main.js') and 'strikesFrom(' in src('hud/hud.js'),
          '/play strikes across an open way from where the hero stands, and shows what reaches')
    ents_src = src('entities.js')
    check('moveTo(e, vnum, at = null)' in ents_src and 'this.moveTo(e, w.vnum, w.data)' in ents_src
          and 'this.moveTo(e, payload.vnum, m)' in ents_src and 'e.rush' in ents_src,
          '/play: a creature pulled in from next door runs across to where the server put it (no snap to a spawn spot)')
    check('expectPull(' in src('main.js') and 'this.ents.landing(' in src('combat.js') and 'holdUntil' in ents_src,
          '/play: a pulled creature stays put until the shot or spell reaches it, then charges')
    check('leapAcross(t, then)' in src('main.js') and "ab.shape === 'dash'" in src('hud/hud.js'),
          '/play leaps across an open way, and lights the leaps that reach')

    # open ground (wilds.py): an opened zone's side-by-side outdoor rooms join up
    import wilds
    import map_system
    zm60 = map_system.build_zonemap(world, 60)
    wild = [(r['vnum'], d, e['to']) for r in zm60['rooms'] for d, e in r['exits'].items() if e.get('wild')]
    check(zm60.get('wild') and len(wild) >= 20, f'the Plains are opened: {len(wild)} new ways between side-by-side outdoor rooms')
    cell = {r['vnum']: r['cell'] for r in zm60['rooms']}
    bad = [w for w in wild if not (wilds.open_ground(world.rooms[w[0]]) and wilds.open_ground(world.rooms[w[2]])
           and [cell[w[2]][0] - cell[w[0]][0], cell[w[2]][1] - cell[w[0]][1]] == list(wilds.STEP[w[1]])
           and world.rooms[w[2]].exits[wilds.BACK[w[1]]]['to_room'] == w[0])]
    check(not bad, f'each joins two outdoor rooms side by side on the map, both ways ({bad[:3]})')
    check(not any(e.get('wild') for z in wilds.CLOSED_ZONES for r in (map_system.build_zonemap(world, z) or {'rooms': []})['rooms']
                  for e in r['exits'].values()), 'a zone kept closed (the God Rooms) keeps its ways as written')
    opened = sum(1 for z in world.zones if (map_system.build_zonemap(world, z) or {}).get('wild'))
    check(opened > 100, f'every zone is opened ({opened})')
    v, d, t = wild[0]
    check(reach.joined(world, world.rooms[v], world.rooms[t]) == d, 'reach and pulls follow a new way')
    walker = Player.create_new(name='Wanderer', password=None, race='human', char_class='warrior',
                               stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    walker.world, walker.room, walker.connection = world, world.rooms[v], object()
    walker.send = note
    world.rooms[v].characters.append(walker)
    walker.move = walker.max_move = 500
    await CommandHandler.execute(walker, 'webmove', [str(v), str(t), d])
    check(walker.room is world.rooms[t], f'a player walks across it ({v} {d} -> {walker.room.vnum})')
    walker.room.characters.remove(walker)
    check('room.zoneRef.wild' in src('terrain.js') and 'this.wild = !!zm.wild' in src('zone.js'),
          "/play: an opened zone's land runs on past its edge")

    # a living world (phase 4): an aggressive creature sees a hero across an open way and comes;
    # its own kind follows when it wanders
    # (out in the open: a pair of the Plains' rooms joined by a new way, each 3 m from the edge)
    hv, hd, tv = wild[0]
    here, there = world.rooms[hv], world.rooms[tv]
    edge = {'east': ((21.0, 7.5), (3.0, 7.5)), 'west': ((3.0, 7.5), (21.0, 7.5)),
            'south': ((12.0, 12.0), (12.0, 3.0)), 'north': ((12.0, 3.0), (12.0, 12.0))}[hd]
    seer = Player.create_new(name='Seen', password=None, race='human', char_class='warrior',
                             stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    seer.world, seer.room, seer.connection, seer.level = world, here, object(), 30
    seer.send = note
    here.characters.append(seer)
    seer.web_pos = (here.vnum, *edge[0])
    wolf = create_mob_from_prototype(next(iter(world.mob_prototypes.values())), world)
    wolf.flags = set(f for f in (wolf.flags or ()) if f not in ('sentinel', 'boss')) | {'aggressive'}
    wolf.special, wolf.owner, wolf.fighting, wolf.level = None, None, None, 30
    wolf.room = there
    there.characters.append(wolf)
    cr.set_pos(wolf, *edge[1])
    world.npcs.append(wolf)
    import mobs as _mobs
    check(reach.noticed(world, wolf, spared=_mobs.spared) is seer, f'an aggressive creature sees a hero 6 m off across an open way ({hv} {hd} {tv})')
    seer.flags.add('hidden')
    check(reach.noticed(world, wolf) is None, 'not one hiding')
    seer.flags.discard('hidden')
    cr.set_pos(wolf, *(23.0 - edge[1][0], edge[1][1]) if hd in ('east', 'west') else (edge[1][0], 14.0 - edge[1][1]))
    check(reach.noticed(world, wolf) is None, 'nor one too far off')
    cr.set_pos(wolf, *edge[1])
    came = await wolf._charge_next_door()
    check(came and wolf.room is here and wolf.fighting is seer, 'it charges in and attacks')
    for ch in (wolf, seer):
        ch.fighting = None
        # (the fight it began may have moved either: a flee, a death)
        if ch.room is not None and ch in ch.room.characters:
            ch.room.characters.remove(ch)
    if wolf in world.npcs:
        world.npcs.remove(wolf)
    # a herd: its kind idling where it was may follow it
    import random as _random
    proto = next(iter(world.mob_prototypes.values()))
    herd = [create_mob_from_prototype(proto, world) for _ in range(3)]
    for m in herd:
        m.flags = set(f for f in (m.flags or ()) if f != 'sentinel')
        m.fighting, m.owner, m.room, m.home_zone = None, None, there, None
        there.characters.append(m)
    _state = _random.getstate()
    _random.seed(1)
    there.characters.remove(herd[0])
    herd[0].room = here
    here.characters.append(herd[0])
    await herd[0]._herd_follows(there, 'west', here, 'east')
    _random.setstate(_state)
    followed = sum(1 for m in herd[1:] if m.room is here)
    check(followed >= 1, f'its own kind follows it ({followed} of 2)')
    for m in herd:
        m.room.characters.remove(m)
    check('e.then = e.goal; e.goal = gate' in src('entities.js'), '/play: a wanderer goes through the opening between two rooms, not the wall')
    check('new FarView(this)' in src('zone.js') and 'farSight' in src('engine.js') and 'export const FAR' in src('far.js'),
          '/play: rooms past the built ones are drawn cheaply, the haze lies further off outdoors')
    check('addGhost(zm' in src('zone.js') and 'nextDoor(zone)' in src('main.js') and 'h.seamless' in src('main.js'),
          '/play: the zones next door are drawn past the border and walked into without a load or a fade')

    # running away (the owner: "after a certain range they should stop chasing"): a creature fled
    # from leaves the hero alone a while; a hunter goes only so far from where the chase began,
    # then gives up, heals and walks back
    here, there = world.rooms[hv], world.rooms[tv]
    runner = Player.create_new(name='Runner', password=None, race='human', char_class='warrior',
                               stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    runner.world, runner.room, runner.connection, runner.level = world, here, object(), 30
    runner.send = note
    here.characters.append(runner)
    runner.web_pos = (here.vnum, *edge[0])
    wolf2 = create_mob_from_prototype(next(iter(world.mob_prototypes.values())), world)
    wolf2.flags = set(f for f in (wolf2.flags or ()) if f not in ('sentinel', 'boss')) | {'aggressive'}
    wolf2.special, wolf2.owner, wolf2.fighting, wolf2.level = None, None, None, 30
    wolf2.room = there
    there.characters.append(wolf2)
    cr.set_pos(wolf2, *edge[1])
    check(reach.noticed(world, wolf2) is runner, 'before: it sees the hero next door')
    reach.lost(wolf2, runner)
    check(reach.noticed(world, wolf2) is None, 'a hero who fled from it is left alone a while (no charging straight back)')
    wolf2.lost_quarry = {}
    there.characters.remove(wolf2)
    here.characters.remove(runner)
    # the leash: a hunter whose prey is 5 rooms from where the chase began gives up
    import mobs as _m
    start = world.rooms[6001]
    far = next(r for r in (world.rooms[v] for v in sorted(world.rooms)) if r.zone is start.zone
               and wolf2._steps_between(start, r, 5) == 5 and not (_m.KEEP_OUT & r.flags))
    hunter = create_mob_from_prototype(next(iter(world.mob_prototypes.values())), world)
    hunter.flags = set(f for f in (hunter.flags or ()) if f not in ('sentinel', 'boss', 'tracker')) | {'hunter'}
    hunter.special, hunter.owner, hunter.fighting, hunter.home_zone = None, None, None, None
    hunter.room = start
    start.characters.append(hunter)
    runner.room = far
    far.characters.append(runner)
    hunter.add_grudge(runner, 10)
    hunter.hp = max(1, hunter.max_hp // 3)
    took = await hunter.hunting_ai()
    check(took and hunter.hunting_target is None and runner.name not in hunter.grudge_list,
          f'past its leash ({_m.LEASH["hunter"]} rooms; the hero is 5 off) a hunter gives up the chase')
    check(hunter.hp == hunter.max_hp, 'and heals (no wearing it down by leading it about)')
    # it had already followed two rooms out: it walks back to where it began
    step1 = next(ex['room'] for ex in start.exits.values() if isinstance(ex, dict) and ex.get('room') is not None
                 and not (_m.KEEP_OUT & ex['room'].flags))
    start.characters.remove(hunter)
    hunter.room = step1
    step1.characters.append(hunter)
    hunter.returning, hunter._home_clock = start, 0
    for _ in range(40):
        await hunter._return_home()
        if hunter.room is start:
            break
    check(hunter.room is start and hunter.returning is None, 'and walks back to where the chase began')
    hunter.room.characters.remove(hunter)
    far.characters.remove(runner)

    # a refused pull says why once: the attack or spell the client sends straight after it is let go
    from commands import CommandHandler
    import time as _time
    sayer = Player.create_new(name='Refused', password=None, race='human', char_class='mage',
                              stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    sayer.world, sayer.room, sayer.connection = world, here, object()
    here.characters.append(sayer)
    heard = []

    async def hear(m, *a, **k):
        heard.append(m)
    sayer.send = hear
    sayer.web_pos = (here.vnum, 22.0, 7.5)
    put(20.0)
    await reach.webpull(sayer, ['#990001', 'attack'])
    n = len(heard)
    check(n == 1 and 'out of reach (' in heard[0] and beast.room is there, f'a refused pull says why, with the distance ({heard[-1:]})')
    await CommandHandler.execute(sayer, 'kill', ['#990001'])
    check(len(heard) == n, 'and the attack sent after it adds no "whom?" of its own')
    await CommandHandler.execute(sayer, 'kill', ['nosuchthing'])
    check(len(heard) > n, 'the next command after that is heard as ever')
    sayer._pull_refused = _time.monotonic() - 5
    n = len(heard)
    await CommandHandler.execute(sayer, 'kill', ['nosuchthing'])
    check(len(heard) > n, 'and a refusal long past swallows nothing')
    here.characters.remove(sayer)

    # Pocket Sand opens a fight (not only mid-fight)
    field = world.rooms[6001]
    rogue = Player.create_new(name='Sander', password=None, race='human', char_class='thief',
                              stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    rogue.world, rogue.room, rogue.connection = world, field, None
    rogue.send = hear
    field.characters.append(rogue)
    mark = create_mob_from_prototype(next(iter(world.mob_prototypes.values())), world)
    mark.flags = set(f for f in (mark.flags or ()) if f not in ('sentinel', 'boss'))
    mark.special, mark.owner, mark.fighting = None, None, None
    mark.room = field
    field.characters.append(mark)
    rogue.luck_points = 5
    await CommandHandler.cmd_pocket_sand(rogue, [mark.name.split()[0]])
    check(getattr(mark, 'blinded_rounds', 0) >= 2 and rogue.fighting is mark,
          f'Pocket Sand thrown out of a fight blinds the foe and starts the fight ({heard[-1][:50]})')
    field.characters.remove(mark)
    field.characters.remove(rogue)
    rogue.fighting = None
    check('if (known && joined && e.kind === \'mob\') e.charging = true;' in src('entities.js') and 'ents.onCharge' in src('main.js')
          and "growl:" in src('soundtable.js') and 'growl:' in src('audio.js'),
          'a creature charging in from next door snarls and kicks up dust as it sets off')

    # the poison's ticks are fight lines (the Combat tab, not All)
    import msgkind
    check(msgkind.kind_of('\x1b[32mYou shudder from the poison in your veins! (5 damage)\x1b[0m') == 'combat',
          'a poison tick goes to the Combat tab')

    # the tracker: tutorials leave it past the first levels; Hide (or the journal) chooses
    import quest_guide
    from quests import QuestManager, QUEST_DEFINITIONS
    vet = Player.create_new(name='Veteran', password=None, race='human', char_class='warrior',
                            stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    vet.world, vet.room = world, world.rooms[3001]
    vet.send = hear
    vet.active_quests = []
    other = next(k for k, d in QUEST_DEFINITIONS.items() if d.get('type') != 'tutorial' and not k.startswith('tutorial_')
                 and d.get('objectives') and not d.get('chain_id') and not d.get('daily'))
    await QuestManager.accept_quest(vet, 'tutorial_3_know_thyself')
    vet.level = 3
    b = quest_guide.guide_block(vet)
    check(b and b['id'] == 'tutorial_3_know_thyself', 'a new hero is guided through the tutorial')
    vet.level = 60
    check(quest_guide.guide_block(vet) is None, 'a level-60 hero has no tutorial on the tracker')
    await QuestManager.accept_quest(vet, other)
    b = quest_guide.guide_block(vet)
    check(b and b['id'] == other, f'the tracker follows their real quest instead ({other})')
    await CommandHandler.execute(vet, 'webtrack', ['hide', other])
    check(quest_guide.guide_block(vet) is None and vet.quest_tracking == {other: False}, 'Hide takes a quest off the tracker')
    await CommandHandler.execute(vet, 'webtrack', ['show', 'tutorial_3_know_thyself'])
    b = quest_guide.guide_block(vet)
    check(b and b['id'] == 'tutorial_3_know_thyself', 'and the journal can put one back (even a tutorial)')
    check('qt-hide' in src('hud/quest.js') and 'jr-track' in src('hud/journal.js'), 'the tracker has Hide, the journal Track / Hide')
    check('#xbars .slot.empty .key { opacity: 0;' in open(os.path.join(WEB, 'hud', 'hud.css'), encoding='utf-8').read(),
          "an extra bar's empty slots keep their key labels hidden until pointed at or dragged onto")
    check('canReach: (e, id, r)' in src('main.js') and 'updateMarks(' in src('combatcues.js'),
          'hovering an ability marks the creatures next door it would reach')

    # townsfolk keep a day (docs/GAMEPLAY_POLISH.md group 3): in at night, out by day
    import random as _rnd
    street = next(r for r in world.rooms.values() if getattr(r, 'look', None) in _m.TOWN_LOOKS and any(
        isinstance(ex, dict) and ex.get('room') is not None and _m.Mobile._indoors(ex['room']) and not ex.get('door')
        and not (_m.KEEP_OUT & ex['room'].flags) for ex in (r.exits or {}).values()))
    folk = create_mob_from_prototype(next(p for p in world.mob_prototypes.values()
                                          if 'aggressive' not in (p.get('flags') if isinstance(p, dict) else getattr(p, 'flags', ())) ), world)
    folk.flags = set(f for f in (folk.flags or ()) if f not in ('sentinel', 'aggressive', 'boss'))
    folk.special, folk.owner, folk.fighting, folk.home_zone = None, None, None, None
    folk.room = street
    street.characters.append(folk)
    was_hour, was_rand = world.game_time.hour, _rnd.randint
    _rnd.randint = lambda a, b: a
    try:
        world.game_time.hour = 23
        for _ in range(5):
            await folk.wander_ai()
            if folk.room is not street:
                break
        check(_m.Mobile._indoors(folk.room), f'at night one of the townsfolk goes into a house ({street.vnum} -> {folk.room.vnum})')
        home = folk.room
        await folk.wander_ai()
        check(folk.room is home, 'and stays in for the night')
        world.game_time.hour = 12
        for _ in range(5):
            await folk.wander_ai()
            if folk.room is not home:
                break
        check(not _m.Mobile._indoors(folk.room), 'by day it comes back out')
    finally:
        world.game_time.hour, _rnd.randint = was_hour, was_rand
        folk.room.characters.remove(folk)
    sayer.room, sayer.explored_rooms = here, {here.vnum}
    p_w = map_system.build_map_payload(sayer, mode='zone')
    check(isinstance(p_w.get('weather'), dict) and 'sky' in p_w.get('weather', {}), 'the payload carries the zone\'s weather for /play to draw')

    # reasons to keep playing (docs/GAMEPLAY_POLISH.md group 4)
    import nodes, elites, bounties, crafting
    from quests import QUEST_DEFINITIONS
    from achievements import AchievementManager
    spot_room = next(r for r in world.rooms.values() if (nodes.node_of(r) or {}).get('k') == 'herb' and not r.characters)
    n1, n2 = nodes.node_of(spot_room), nodes.node_of(spot_room)
    check(n1 == n2 and 3 <= n1['x'] <= 21 and 3 <= n1['z'] <= 12, f'a herb patch sits in the same place for everyone ({spot_room.vnum}: {n1})')
    picker = Player.create_new(name='Picker', password=None, race='human', char_class='ranger',
                               stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    picker.world, picker.room, picker.move, picker.inventory = world, spot_room, 100, []
    heard.clear()
    picker.send = hear
    was_ri = _rnd.randint
    _rnd.randint = lambda a, b: b          # (the worst luck: an ordinary forage would fail)
    try:
        await crafting.cmd_forage(picker, [])
    finally:
        _rnd.randint = was_ri
    check(len(picker.inventory) == 2 and not nodes.ready(spot_room), f'a herb patch gives surely and twice, then is spent ({len(picker.inventory)} found)')
    entry = next(e for e in map_system._nearby_entities(picker) if e['vnum'] == spot_room.vnum)
    check(entry.get('node', {}).get('ready') is False, 'and /play is told it is spent')
    spot_room.node_ready_at = 0
    beast = next(m for m in world.npcs if elites.eligible(m))
    hp0 = beast.max_hp
    name = elites.promote(beast, world, 'grizzled')
    check(beast.elite and beast.max_hp == int(hp0 * 2.5) and 'grizzled' in name and 'elite' in map_system._wards(beast),
          f'a rare elite: its own name, tougher, a gold glow in /play ({name})')
    bounties._day = None
    bounties.refresh(world)
    posted = [QUEST_DEFINITIONS[q]['name'] for q, *_ in bounties.BANDS if q in QUEST_DEFINITIONS]
    check(len(posted) == 3 and all(QUEST_DEFINITIONS[q].get('daily') for q, *_ in bounties.BANDS),
          f'the bounty board posts three named daily bounties ({posted})')
    reader = Player.create_new(name='Reader', password=None, race='human', char_class='mage',
                               stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    reader.world, reader.room = world, here
    reader.send = hear
    import journal
    for i in range(10):
        await journal.JournalManager.discover_creature(reader, f'test{i}', f'creature {i}', 'seen', silent=True)
    check('bestiary_10' in (getattr(reader, 'achievements', None) or {}), 'ten creatures catalogued: the bestiary\'s first milestone, rewarded')

    # guidance (docs/GAMEPLAY_POLISH.md group 5): what the step wants, picked out in the world;
    # a ping seen by the group
    hunter2 = Player.create_new(name='Seeker', password=None, race='human', char_class='warrior',
                                stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    hunter2.world, hunter2.room, hunter2.active_quests, hunter2.level = world, world.rooms[3001], [], 20
    hunter2.send = hear
    await QuestManager.accept_quest(hunter2, 'bounty_novice')
    b = quest_guide.guide_block(hunter2)
    check(b and b.get('want', {}).get('t') == 'kill' and b['want']['target'] == QUEST_DEFINITIONS['bounty_novice']['objectives'][0]['target'],
          f"the tracker says what the step wants, for /play to ring it in gold ({b and b.get('want')})")
    got = []

    class _WM:
        async def notify_event(self, who, ev):
            got.append((who.name, ev))

        async def notify_player(self, who):
            pass
    was_wm = getattr(world, 'web_map', None)
    world.web_map = _WM()
    try:
        await CommandHandler.execute(hunter2, 'webping', ['3001', '12.0', '7.5'])
        await CommandHandler.execute(hunter2, 'webping', ['3001', '1', '1'])
    finally:
        world.web_map = was_wm
    check(len(got) == 1 and got[0][1]['type'] == 'world_ping' and got[0][1]['vnum'] == 3001,
          f'a ping goes to the player (and their group), once a second at most ({len(got)})')

    # walking out of a fight in /play (combat.walk_out); telnet still flees. And the buff bar is
    # told at once when an affect lands (affects._push_affects)
    from combat import CombatHandler
    street = world.rooms[3002]
    way = next(d for d, ex in street.exits.items() if isinstance(ex, dict) and ex.get('room') is not None
               and not ex.get('door') and street.exits[d]['room'].admits(sayer) if hasattr(street.exits[d]['room'], 'admits'))
    walker = Player.create_new(name='Walker', password=None, race='human', char_class='warrior',
                               stats={s: 16 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}, world=world)
    walker.world, walker.room, walker.level, walker.send = world, street, 30, hear
    walker.hp = walker.max_hp = 5000
    street.characters.append(walker)
    brute = create_mob_from_prototype(next(iter(world.mob_prototypes.values())), world)
    brute.flags = set(f for f in (brute.flags or ()) if f not in ('sentinel', 'boss'))
    brute.special, brute.owner = None, None
    brute.room = street
    street.characters.append(brute)
    world.npcs.append(brute)
    walker.fighting, brute.fighting, walker.position, brute.position = brute, walker, 'fighting', 'fighting'
    walker.web_pos = None
    await CommandHandler.cmd_move(walker, way)
    check(walker.room is street and 'Flee' in ' '.join(heard[-2:]), 'a telnet hero in a fight still has to flee')
    walker.web_pos = (street.vnum, 12.0, 7.5)
    await CommandHandler.cmd_move(walker, way)
    check(walker.room is not street and walker.fighting is None and brute.fighting is None,
          f'a /play hero walks out of the fight into the next room ({way})')
    check(walker.name in (brute.grudge_list or {}), 'and the foe holds a grudge (it may come after them)')
    for ch in (walker, brute):
        if ch.room and ch in ch.room.characters:
            ch.room.characters.remove(ch)
    world.npcs.remove(brute)
    pushed = []

    class _WM2:
        def has_play(self, who):
            return True

        async def notify_player(self, who):
            pushed.append(who.name)
    was_wm = getattr(world, 'web_map', None)
    world.web_map = _WM2()
    try:
        from affects import AffectManager
        walker.connection = object()
        for k in range(3):
            AffectManager.apply_affect(walker, {'name': 'armor', 'type': AffectManager.TYPE_MODIFY_STAT,
                                                'applies_to': 'armor_class', 'value': -5, 'duration': 10})
        await asyncio.sleep(0.3)
    finally:
        world.web_map = was_wm
    check(pushed == ['Walker'], f'a buff landing is sent to /play at once, once for a spell of several affects ({pushed})')

    print(f"\n{'ALL OK' if not FAILED else f'{len(FAILED)} FAILED'}")
    sys.exit(1 if FAILED else 0)


if __name__ == '__main__':
    asyncio.run(main())
