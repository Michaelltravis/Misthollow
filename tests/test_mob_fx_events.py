"""A creature's abilities reach the 3D client with their look (combat_hooks: the `fx` key), offline:

    python3 tests/test_mob_fx_events.py

- a wind-up's 'windup', its 'resolve' (aimed at whom it was meant for) and a broken one's
  'cancel' each carry `fx`, the ability's name in lower_snake (world3d/mobfx-hand.js);
- the release comes ahead of the wounds it caused, so /play raises the numbers when it lands;
- a declared spell is shown by its resolve alone (no second 'spell'); an instant one gets its own;
- what a declared hex, prayer or word of silence did, and a caster's ward, get 'debuff' /
  'heal' / 'buff' events with their fx;
- the events change nothing the fight does (combat_hooks only reads what changed).
"""
import asyncio
import logging
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import test_webmove as tw  # noqa: E402  (check(), failures)
from test_action_combat import Conn, FakeMap, put  # noqa: E402

check, failures = tw.check, tw.failures


async def main():
    logging.disable(logging.WARNING)
    from config import Config
    from world import World
    from player import Player
    import combat_hooks
    import combat_range as cr
    import mob_ai
    import brain
    from brain import cast
    from bosses import create_mob_from_prototype

    world = World(Config())
    await world.load()
    wm = FakeMap()
    world.web_map = wm
    combat_hooks.install()
    brain.install()
    random.seed(11)
    ROOM = world.rooms[3054] if 3054 in world.rooms else world.rooms[3001]

    def hero(name, level=30):
        p = Player(world)
        p.name, p.char_class, p.level = name, 'cleric', level
        p.max_hp = p.hp = 900
        p.connection = Conn()
        p.world = world
        world.players[name.lower()] = p
        put(p, ROOM)
        cr.set_pos(p, 12, 7)
        return p

    def foe(vnum=3062, hp=5000):
        mob = create_mob_from_prototype(world.mob_prototypes[vnum], world)
        mob.max_hp = mob.hp = hp
        mob.mana = mob.max_mana = 500
        put(mob, ROOM)
        world.npcs.append(mob)
        cr.set_pos(mob, 13, 7)
        mob.ai_state = {}
        return mob

    def fight(a, b):
        a.fighting, b.fighting = b, a
        a.position = b.position = 'fighting'

    async def resolve(mob, intent):
        wm.full = []
        mob.pending_intent = dict(intent, declared_at=0)
        await mob_ai._resolve_intent(mob)
        await asyncio.sleep(0.02)
        return list(wm.full)

    def first(events, k, **match):
        for i, e in enumerate(events):
            if e.get('k') == k and all(e.get(f) == v for f, v in match.items()):
                return i, e
        return -1, None

    check(combat_hooks.fx_key('Fire Breath') == 'fire_breath' and combat_hooks.fx_key("Night's Embrace") == 'nights_embrace'
          and combat_hooks.fx_key('Power Word: Kill') == 'power_word_kill' and combat_hooks.fx_key('Magic Missile') == 'magic_missile',
          "fx_key: a name in lower_snake ('Fire Breath' -> fire_breath)")

    ace, brute = hero('Ace'), foe()
    brute.level = ace.level + 2          # (a trivial fight declares nothing: mob_ai._intent_exempt)
    fight(ace, brute)

    # ---------------- a heavy blow: the release ahead of its wound, aimed at whom it was for
    hp0 = ace.hp
    evs = await resolve(brute, {'kind': 'heavy', 'label': 'Crushing Blow', 'interruptible': False, 'ability': ('bruiser', None)})
    ri, rel = first(evs, 'resolve')
    di, _ = first(evs, 'dmg')
    check(rel is not None and rel.get('fx') == 'crushing_blow', f"a resolve carries its fx ({rel and rel.get('fx')})")
    check(rel is not None and rel.get('dst') == {'p': 'Ace'}, '...aimed at whom it was meant for')
    check(ace.hp < hp0 and 0 <= ri < di, f'...and comes ahead of the wound it caused (resolve {ri}, dmg {di})')

    # ---------------- a declared spell: its resolve shows it, not a second 'spell'
    key = ('fireball', *cast.SPELLBOOK['fireball'][:1], cast.SPELLBOOK['fireball'][1], cast.SPELLBOOK['fireball'][2])
    evs = await resolve(brute, {'kind': 'cast', 'label': 'Fireball', 'interruptible': True, 'ability': ('caster_offensive', key)})
    _, rel = first(evs, 'resolve')
    check(rel is not None and rel.get('fx') == 'fireball', 'a declared fireball resolves with fx fireball')
    check(first(evs, 'spell')[1] is None, '...and sends no second spell event (the client would throw it twice)')
    # an instant one (a trivial fight's, mob_ai._caster_tick) still gets its own
    wm.full = []
    await mob_ai._cast_offensive(brute, ace, key)
    await asyncio.sleep(0.02)
    _, sp = first(wm.full, 'spell')
    check(sp is not None and sp.get('fx') == 'fireball', 'an instant spell sends its spell event, with fx')

    # ---------------- a hex lands: the debuff after its release
    for a in list(getattr(ace, 'affects', []) or []):
        ace.affects.remove(a)
    evs = await resolve(brute, {'kind': 'debuff', 'label': 'Weaken', 'interruptible': True, 'ability': ('mob_hex', 'weaken')})
    ri, rel = first(evs, 'resolve')
    di, deb = first(evs, 'debuff')
    check(rel is not None and rel.get('fx') == 'weaken', 'a hex resolves with its fx')
    check(deb is not None and deb.get('fx') == 'weaken' and deb.get('dst') == {'p': 'Ace'} and ri < di,
          f"...and what it did follows: a debuff on its target ({deb})")

    # ---------------- a prayer mends: its heal, with the amount
    brute.hp = brute.max_hp // 3
    evs = await resolve(brute, {'kind': 'heal', 'label': 'Healing Prayer', 'interruptible': True, 'ability': ('mob_heal', brute), 'target': brute})
    _, heal = first(evs, 'heal', fx='healing_prayer')
    check(heal is not None and heal.get('amt', 0) > 0 and heal.get('dst') == heal.get('src'), f'a prayer that lands sends its heal ({heal})')

    # ---------------- a word of silence for your healer
    evs = await resolve(brute, {'kind': 'disrupt', 'label': 'Disrupt', 'interruptible': True, 'ability': ('disrupt', ace), 'target': ace})
    _, deb = first(evs, 'debuff', fx='disrupt')
    check(deb is not None and deb.get('name') == 'Silenced', f'Disrupt that lands sends a Silenced debuff ({deb})')

    # ---------------- a caster's ward, once a fight
    shaman = foe()
    fight(ace, shaman)
    wm.full = []
    b = brain.of(shaman)
    b.encounter.pop('warded', None)
    done = await cast.ward(shaman, b)
    await asyncio.sleep(0.02)
    _, buff = first(wm.full, 'buff', fx='ward')
    check(done and buff is not None and buff.get('dst') == buff.get('src'), f'a ward sends its buff on the caster ({buff})')

    # ---------------- a wind-up names its look; a broken one too
    wm.full = []
    brute.pending_intent = None
    fight(ace, brute)
    for _ in range(14):
        if brute.pending_intent:
            break
        brute.ai_state.pop('heavy_cd', None)
        await mob_ai.declare_intents(brute)
    await asyncio.sleep(0.02)
    _, wind = first(wm.full, 'windup')
    check(wind is not None and wind.get('fx') == combat_hooks.fx_key(wind.get('label')), f"a windup carries its fx ({wind and wind.get('fx')})")
    if brute.pending_intent:
        wm.full = []
        label = brute.pending_intent['label']
        brute.pending_intent = None            # kicked: an interrupt clears it outside its own resolution
        await asyncio.sleep(0.02)
        _, cancel = first(wm.full, 'cancel')
        check(cancel is not None and cancel.get('fx') == combat_hooks.fx_key(label) and cancel.get('school'),
              f'a broken wind-up names what broke apart ({cancel})')

    # ================================================================ bosses (bosses.py)
    import time
    from bosses import Boss
    proto = next(p for p in world.mob_prototypes.values() if (p.get('boss_config') or {}).get('abilities'))
    boss = Boss.from_prototype(proto, world)
    boss.max_hp = boss.hp = 50000
    put(boss, ROOM)
    world.npcs.append(boss)
    cr.set_pos(boss, 13, 7)
    bo = hero('Bo')
    fight(bo, boss)
    boss.ai_state['combat_start'] = time.time()

    async def boss_start(ability):
        wm.full = []
        await boss._start_ability(ability)
        await asyncio.sleep(0.02)
        return list(wm.full)

    async def boss_land():
        wm.full = []
        boss.ai_state['cast']['resolve_at'] = 0
        await boss._handle_cast(time.time())
        await asyncio.sleep(0.02)
        return list(wm.full)

    # a wound-up spell you can break: its look, its kind, aimed at its target, ahead of its wound
    word = {'name': 'Power Word: Kill', 'telegraph': 'A word of ending!', 'cast_time': 2, 'cooldown': 0,
            'damage_dice': '4d8+15', 'interruptible': True}
    evs = await boss_start(word)
    _, wind = first(evs, 'windup')
    check(wind is not None and wind.get('fx') == 'power_word_kill' and wind.get('kind') == 'cast',
          f"a boss's wind-up carries its fx, a spell you can break as 'cast' ({wind and (wind.get('fx'), wind.get('kind'))})")
    hp0 = bo.hp
    evs = await boss_land()
    ri, rel = first(evs, 'resolve')
    di, _ = first(evs, 'dmg')
    check(rel is not None and rel.get('fx') == 'power_word_kill' and rel.get('dst') == {'p': 'Bo'},
          "...its resolve names the look and whom it was for")
    check(bo.hp < hp0 and 0 <= ri < di, f'...and comes ahead of the wound (resolve {ri}, dmg {di})')

    # broken: the cancel names what broke apart
    await boss_start(word)
    boss.ai_state['cast']['interrupted'] = True
    evs = await boss_land()
    _, cancel = first(evs, 'cancel')
    check(cancel is not None and cancel.get('fx') == 'power_word_kill' and cancel.get('school'), f'an interrupted one cancels with its fx ({cancel})')

    # an area blow at once: an 'ability' around the boss, ahead of its wounds
    stomp = {'name': 'Tail Sweep', 'telegraph': 'A tail!', 'cast_time': 0, 'cooldown': 0, 'damage_dice': '2d6+2', 'aoe': True, 'radius': 4.5}
    evs = await boss_start(stomp)
    ai, ab = first(evs, 'ability')
    di, _ = first(evs, 'dmg')
    check(ab is not None and ab.get('fx') == 'tail_sweep' and ab.get('kind') == 'aoe' and str(ab.get('shape', '')).startswith('nova'),
          f'an instant area blow sends an ability event around the boss ({ab})')
    check(0 <= ai < di, f'...ahead of its wounds (ability {ai}, dmg {di})')

    # a heal and a ward on itself
    boss.hp = boss.max_hp // 2
    evs = await boss_start({'name': 'Dark Mending', 'cast_time': 0, 'cooldown': 0, 'heal_pct': 10, 'magic_immune_duration': 3})
    _, heal = first(evs, 'heal')
    _, ward = first(evs, 'buff', fx='nullifying_aura')
    check(heal is not None and heal.get('amt', 0) > 0 and heal.get('fx') == 'dark_mending', f'a boss healing itself sends its heal ({heal})')
    check(ward is not None, 'a nullifying aura sends its buff')

    # phases, enrage, help called
    boss.boss_config = dict(boss.boss_config, phases=[{'threshold': 60, 'message': 'The ground splits!'}])
    boss.phase_index = 0
    boss.hp = int(boss.max_hp * 0.5)
    wm.full = []
    await boss._check_phase_transitions()
    await asyncio.sleep(0.02)
    _, ph = first(wm.full, 'phase')
    check(ph is not None and ph.get('n') == 1 and ph.get('label') == 'The ground splits!', f'a new phase sends its moment ({ph})')
    boss.enrage_time, boss.ai_state['enraged'] = 1, False
    wm.full = []
    await boss._handle_enrage(time.time() + 5)
    await asyncio.sleep(0.02)
    check(first(wm.full, 'enrage')[1] is not None, 'enraging sends its moment')
    add_vnum = next(v for v, p in world.mob_prototypes.items() if not p.get('boss_config'))
    wm.full = []
    await boss._spawn_adds({add_vnum: 2})
    await asyncio.sleep(0.02)
    _, summon = first(wm.full, 'summon')
    check(summon is not None and len(summon.get('adds') or []) == 2 and summon.get('school') in ('necrotic', 'shadow'),
          f'calling help sends who came, to rise from the ground ({summon})')

    print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED'}")
    return not failures


if __name__ == '__main__':
    sys.exit(0 if asyncio.run(main()) else 1)
