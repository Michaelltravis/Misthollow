"""Every spell and ability does what it says (offline: a loaded world, no server).

    python3 tests/test_spells_audit.py

- every spell in every class book, cast the way the 3D bar casts it (cast '<id>' [target]) on a
  groupmate or a foe as the spell asks, visibly does something (health, an affect, a pet, a
  move, what it reports) or says honestly why not; none errors;
- a group spell reaches the groupmate; a room spell strikes the foes and spares the groupmate;
- a spell's cooldown holds (and nothing is spent on a refused cast); cast takes the name the
  spellbook shows ('Cinderlance' for pyroblast); Identify reports the item;
- what spells leave is read: Mirrorward turns a spell back, sanctuary halves a blow,
  invulnerability stops it, a mana shield draws on mana, a stun costs turns, a charmed creature
  stops fighting, a silenced one can't cast, Unfettered's ward refuses a slow;
- no command is defined twice (only the last copy ever ran); every class-book skill is a command.
"""
import asyncio
import ast
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'balance'))
import test_webmove as tw  # noqa: E402  (check(), failures)

check, failures = tw.check, tw.failures
ANSI = re.compile(r'\x1b\[[0-9;]*m')
CLASSES = ['mage', 'cleric', 'paladin', 'necromancer', 'ranger', 'bard', 'assassin']
# what a spell may honestly answer when there is nothing for it to do here
HONEST = ('no magical effects', 'not cursed', 'not poisoned', 'whom?', 'need at least', 'legends whisper',
          'item:', 'glows with magical', 'conjure', 'create fresh water', 'frost power surges', 'lifts 0',
          'font of the vigil', 'sanctify the ground', 'there is nothing here', "no closed door here")


def said(h):
    return ' / '.join(ANSI.sub('', l).strip() for l in h.connection.lines if l.strip())


def state(chars, room):
    out = []
    for ch in chars:
        out.append((ch.hp, getattr(ch, 'mana', 0), sorted((a.name, a.applies_to) for a in getattr(ch, 'affects', [])),
                    getattr(ch, 'stunned_rounds', 0), getattr(ch, 'fighting', None) is not None, getattr(ch, 'room', None) is room))
    return out, len(room.characters), len(room.items)


async def main():
    import sim                      # tools/balance: the world and its heroes, on a simulated clock
    from commands import CommandHandler
    from bosses import create_mob_from_prototype
    from groups import Group
    from objects import Object, create_object
    from affects import AffectManager
    import mastery
    import combat_range as cr
    from spells import SPELLS, SpellHandler
    world = await sim.load_world()
    room = world.rooms[3054]

    def clear():
        for ch in list(room.characters):
            room.characters.remove(ch)
        room.items[:] = []

    def foe(hp=5000):
        m = create_mob_from_prototype(dict(world.mob_prototypes[3062]), world)
        m.max_hp = m.hp = hp
        m.level = 55
        m.alignment = -500
        sim._put(m, room)
        world.npcs.append(m)
        return m

    async def scene(cls):
        clear()
        caster = await sim.make_hero(world, cls, 60, f'Au{cls[:3].title()}', 0.75)
        ally = await sim.make_hero(world, 'cleric', 60, 'Aually', 0.75)
        for h in (caster, ally):
            sim._put(h, room)
            h.max_mana = h.mana = 20000
        ally.hp = ally.max_hp // 2
        g = Group(caster)
        g.add_member(ally)
        caster.group = ally.group = g
        a, b = foe(), foe()
        cr.set_pos(caster, 10, 7); cr.set_pos(ally, 10.5, 7.5); cr.set_pos(a, 11.2, 7); cr.set_pos(b, 11.6, 7.8)
        a.fighting = caster; a.position = 'fighting'
        caster.fighting = a; caster.position = 'fighting'
        corpse = Object(0, world)
        corpse.name = 'corpse of a fido'; corpse.short_desc = 'the corpse of a fido'
        corpse.item_type = 'container'; corpse.contents = []
        room.items.append(corpse)
        bread = create_object(3010, world)
        caster.inventory.append(bread)
        return caster, ally, a, b, bread

    def done(*chars):
        for ch in chars:
            world.players.pop(getattr(ch, 'name', '').lower(), None)
            if ch in world.npcs:
                world.npcs.remove(ch)

    # ---- every book spell, cast as the bar casts it
    silent, errors, seen = [], [], set()
    for cls in CLASSES:
        for e in mastery.book(cls):
            if e.get('type') != 'spell' or e['id'] in seen or e['id'] not in SPELLS:
                continue
            seen.add(e['id'])
            spell = SPELLS[e['id']]
            caster, ally, a, b, bread = await scene(cls)
            caster.spells[e['id']] = 100
            pet = None
            if spell.get('target') == 'pet':
                from pets import PetManager
                pet = await PetManager.summon_pet(caster, 'undead_warrior', duration_minutes=5)
            args = [f"'{e['id'].replace('_', ' ')}'"]
            t = spell.get('target')
            if t == 'offensive':
                args.append(a.name.split()[-1].lower())
            elif t == 'defensive':
                args.append(ally.name.lower())
            elif t == 'object':
                args.append(bread.name.split()[-1].lower())
            elif t == 'pet' and pet is not None:
                args.append(pet.name.split()[-1].lower())
            chars = [caster, ally, a, b] + ([pet] if pet else [])
            before = state(chars, room)
            caster.connection.lines.clear()
            await CommandHandler.execute(caster, 'cast', args)
            text = said(caster).lower()
            if 'something went wrong' in text:
                errors.append(e['id'])
            elif state(chars, room) == before and not any(w in text for w in HONEST):
                silent.append((e['id'], text[:80]))
            done(caster, ally, a, b, *( [pet] if pet else []))
    check(not errors, f'no book spell errors when cast ({errors})')
    check(not silent, f'every book spell does something or says why not ({len(seen)} spells; silent: {silent})')

    # ---- a group spell reaches the group; a room spell the foes, never the groupmate
    caster, ally, a, b, _ = await scene('bard')
    caster.spells.update(song_of_battle=100, chord_of_disruption=100)
    await CommandHandler.execute(caster, 'cast', ["'song of battle'"])
    check(any(x.applies_to == 'damroll' for x in ally.affects), "a group spell (Song of Battle) reaches the groupmate")
    hp = ally.hp
    await CommandHandler.execute(caster, 'cast', ["'chord of disruption'"])
    check('silenced' in (a.affect_flags or set()) and 'silenced' not in (caster.affect_flags or set()) and ally.hp == hp,
          'a room spell (Chord of Disruption) silences the foe, not the bard or the groupmate')
    done(caster, ally, a, b)
    caster, ally, a, b, _ = await scene('cleric')
    caster.spells['earthquake'] = 100
    hp, ahp = ally.hp, a.hp
    await CommandHandler.execute(caster, 'cast', ["'earthquake'"])
    check(a.hp < ahp and ally.hp == hp, f'Earthquake shakes the foe and spares the groupmate ({ahp}->{a.hp}, ally {hp}->{ally.hp})')
    done(caster, ally, a, b)

    # ---- cooldowns hold; display names cast; identify reports
    caster, ally, a, b, bread = await scene('mage')
    caster.spells.update(meteor_storm=100, pyroblast=100, identify=100)
    await CommandHandler.execute(caster, 'cast', ["'meteor storm'"])
    mana = caster.mana
    caster.connection.lines.clear()
    await CommandHandler.execute(caster, 'cast', ["'meteor storm'"])
    check('not ready yet' in said(caster).lower() and caster.mana == mana,
          f"a spell on its cooldown is refused and costs nothing ({said(caster)[:60]})")
    check(caster.spell_cd.get('meteor_storm', 0) > sim.CLOCK.t + 100, "…and the cooldown is kept on the character (2 minutes)")
    caster.connection.lines.clear()
    hp0 = a.hp
    await CommandHandler.execute(caster, 'cast', ["'cinderlance'", a.name.split()[-1].lower()])
    check(a.hp < hp0 or 'fizzle' in said(caster).lower(), f"cast takes the spellbook's name: 'Cinderlance' is pyroblast ({said(caster)[:70]})")
    caster.connection.lines.clear()
    await CommandHandler.execute(caster, 'cast', ["'identify'", bread.name.split()[-1].lower()])
    check('item:' in said(caster).lower(), 'Identify reports the item')
    done(caster, ally, a, b)

    # ---- what spells leave is read
    caster, ally, a, b, _ = await scene('mage')
    caster.spells.update(mirrorward=100, fireball=100)
    await CommandHandler.execute(caster, 'cast', ["'mirrorward'"])
    other = await sim.make_hero(world, 'mage', 60, 'Aurival', 0.75)
    sim._put(other, room)
    other.spells['fireball'] = 100
    other.mana = 5000
    hp = other.hp
    await CommandHandler.execute(other, 'cast', ["'fireball'", caster.name.lower()])
    check(other.hp < hp and 'spell_reflect' not in (caster.affect_flags or set()),
          'Mirrorward turns a spell back on its caster, and is spent')
    done(other)
    caster.hp = caster.max_hp
    AffectManager.apply_affect(caster, {'name': 'Sanctuary', 'type': 'flag', 'applies_to': 'sanctuary', 'value': 1, 'duration': 5})
    hp = caster.hp
    await caster.take_damage(40, a, 'physical')
    check(hp - caster.hp == 20, f'sanctuary halves a blow (40 -> {hp - caster.hp})')
    AffectManager.apply_affect(caster, {'name': 'Divine Shield', 'type': 'flag', 'applies_to': 'invulnerable', 'value': 1, 'duration': 5})
    hp = caster.hp
    await caster.take_damage(500, a, 'physical')
    check(caster.hp == hp, 'invulnerability stops the blow')
    for x in list(caster.affects):
        AffectManager.remove_affect(caster, x)
    # cast again, a spell is refreshed, not doubled: one copy, its duration renewed, its bonus once
    hr = caster.hitroll
    AffectManager.apply_affect(caster, {'name': 'bless', 'type': 'modify_stat', 'applies_to': 'hitroll', 'value': 2, 'duration': 3})
    caster.affects[-1].remaining = 1
    AffectManager.apply_affect(caster, {'name': 'bless', 'type': 'modify_stat', 'applies_to': 'hitroll', 'value': 2, 'duration': 3})
    blessed = [x for x in caster.affects if x.name == 'bless']
    check(len(blessed) == 1 and blessed[0].remaining == 3 and caster.hitroll == hr + 2,
          f'a spell cast again is refreshed, not doubled ({len(blessed)} copies, +{caster.hitroll - hr} hitroll)')
    for x in list(caster.affects):
        AffectManager.remove_affect(caster, x)
    # a ward (the shields, fly) lasts 15 minutes at level 1 and 30 by level 50: one tick is 6 seconds
    from spells import ward_ticks
    check(ward_ticks(1) * 6 >= 15 * 60 and ward_ticks(50) * 6 == 30 * 60 and ward_ticks(60) == ward_ticks(50),
          f'wards last 15 to 30 minutes ({ward_ticks(1) * 6 // 60}-{ward_ticks(50) * 6 // 60} min)')
    caster.spells.update(fly=100, shield=100)
    caster.mana = caster.max_mana = 5000
    for sp in ('fly', 'shield'):
        await CommandHandler.execute(caster, 'cast', [f"'{sp}'", caster.name.lower()])
        caster.spell_cd = {}
    held = {x.applies_to: x.duration for x in caster.affects}
    want = ward_ticks(caster.level)
    check(held.get('fly') == want and held.get('shielded') == want,
          f'fly and shield, cast, last as a ward at the caster\'s level ({held.get("fly")}, {held.get("shielded")}; {want})')
    from map_system import _wards
    check({'fly', 'shielded'} <= set(_wards(caster)), f'the map payload shows them on the body (wards {_wards(caster)})')
    for x in list(caster.affects):
        AffectManager.remove_affect(caster, x)
    AffectManager.apply_affect(caster, {'name': 'Mana Shield', 'type': 'flag', 'applies_to': 'mana_shield', 'value': 1, 'duration': 5})
    hp, mana = caster.hp, caster.mana
    await caster.take_damage(40, a, 'physical')
    check(hp - caster.hp == 20 and mana - caster.mana == 20, f'a mana shield draws half the blow from mana ({hp - caster.hp} health, {mana - caster.mana} mana)')
    await SpellHandler.apply_affect(a, {'type': 'stunned', 'value': 1}, 2, 'Deep Freeze', 60, caster=caster)
    check(a.stunned_rounds == 2, f'a stun costs the creature its turns ({a.stunned_rounds})')
    from combat import CombatHandler
    hp = caster.hp
    await CombatHandler.one_round(a, caster)
    check(caster.hp == hp and a.stunned_rounds == 1, 'a stunned creature loses its swing')
    a.stunned_rounds = 0
    # a bash stuns for a round (it once left the creature 'stunned' for the rest of the fight,
    # and a boss so stunned never cast, enraged or changed phase again); a boss keeps its feet
    import random
    roll = random.randint
    random.randint = lambda lo, hi: lo      # every roll succeeds
    try:
        caster.skills['bash'] = 100
        await CombatHandler.do_bash(caster, a)
        check(a.stunned_rounds == 1 and a.position != 'stunned', f'a bash stuns for one round ({a.stunned_rounds}, {a.position})')
        a.stunned_rounds = 0
        a.is_boss = True
        await CombatHandler.do_bash(caster, a)
        check(not a.stunned_rounds and a.position != 'stunned', f'a boss keeps its feet under a bash ({a.stunned_rounds}, {a.position})')
        check(CombatHandler.stun(a, 2) == 'stagger' and not a.stunned_rounds, 'any other stun only staggers a boss')
        a.is_boss = False
    finally:
        random.randint = roll
    await SpellHandler.apply_affect(a, {'type': 'charmed', 'value': 1}, 4, 'Charm', 60, caster=caster)
    check(a.fighting is None, 'a charmed creature stops fighting')
    hp = caster.hp
    a.fighting = caster
    await CombatHandler.one_round(a, caster)
    check(caster.hp == hp and a.fighting is None, '…and does not swing while the charm holds')
    import mob_ai
    await SpellHandler.apply_affect(b, {'type': 'silenced', 'value': 1}, 4, 'Chord', 60, caster=caster)
    b.mana = 500
    check(mob_ai._silenced(b) and mob_ai._choose_caster_intent(b, caster) is None, 'a silenced creature casts nothing')
    caster.spells['unfettered'] = 100
    await CommandHandler.execute(caster, 'cast', ["'unfettered'"])
    await SpellHandler.apply_affect(caster, {'type': 'slow', 'value': 1}, 4, 'Crypt Winter', 60, caster=b)
    check('slow' not in (caster.affect_flags or set()), "Unfettered's ward refuses a new slow")
    done(caster, ally, a, b)

    # ---- damage over time finishes a creature (credited to whoever it fights), never a player
    caster, ally, a, b, _ = await scene('necromancer')
    a.hp = 5
    AffectManager.apply_affect(a, {'name': 'plague', 'type': AffectManager.TYPE_DOT, 'applies_to': 'hp', 'value': 12, 'duration': 3})
    await AffectManager.tick_affects(a)
    check(a.hp <= 0 or a not in room.characters, f'a creature dies of its wounds (hp {a.hp})')
    caster.hp = 5
    AffectManager.apply_affect(caster, {'name': 'poison', 'type': AffectManager.TYPE_DOT, 'applies_to': 'hp', 'value': 12, 'duration': 3})
    await AffectManager.tick_affects(caster)
    check(caster.hp == 1, f'a player is never killed by it ({caster.hp})')
    done(caster, ally, a, b)

    # ---- the bone knight: its shield wall rests between uses and comes down out of a fight, and
    # its taunt turns the creatures on its owner's side onto it, never a groupmate
    from pets import PetManager
    caster, ally, a, b, _ = await scene('necromancer')
    knight = await PetManager.summon_pet(caster, 'undead_warrior', duration_minutes=60)
    ally.fighting = b; ally.position = 'fighting'
    b.fighting = ally; b.position = 'fighting'
    knight.fighting = knight.target = a
    await knight.use_special_ability('shield_wall')
    check(knight.shield_wall_active == 3 and a.fighting is knight and b.fighting is knight and ally.fighting is b,
          f"the shield wall turns the creatures on its owner and their group onto the knight, not a groupmate "
          f"(a on {getattr(a.fighting, 'name', None)}, b on {getattr(b.fighting, 'name', None)}, ally on {getattr(ally.fighting, 'name', None)})")
    knight.shield_wall_active = 0
    await knight.use_special_ability('shield_wall')
    check(knight.shield_wall_active == 0, 'the wall rests before it can be raised again (it was up two rounds in three)')
    for _ in range(6):
        await knight.ai_combat_tick()
    check(getattr(knight, 'shield_wall_cd', 0) == 0, f'…for six rounds ({getattr(knight, "shield_wall_cd", None)} left)')
    knight.shield_wall_active = 3
    knight.fighting = knight.target = None
    await knight.ai_combat_tick()
    check(knight.shield_wall_active == 0, 'out of a fight the wall comes down')
    for pet in PetManager.get_player_pets(caster):
        if pet in room.characters:
            room.characters.remove(pet)
    done(caster, ally, a, b, knight)

    # ---- no command defined twice; every class-book skill is a command
    src = open(os.path.join(HERE, '..', 'src', 'commands.py')).read()
    tree = ast.parse(src)
    handler = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CommandHandler')
    counts = collections.Counter(i.name for i in handler.body if isinstance(i, (ast.FunctionDef, ast.AsyncFunctionDef)))
    dup = sorted(k for k, v in counts.items() if v > 1)
    check(not dup, f'no command is defined twice (only the last copy ran): {dup}')
    import marquee_abilities as ma
    unknown = []
    for cls in ['warrior', 'thief'] + CLASSES:
        for e in mastery.book(cls):
            if e.get('type') == 'spell' or e.get('passive') or e['id'] in ma.ABILITIES:
                continue
            name = CommandHandler.ALIASES.get(e['id'], e['id'])
            if not hasattr(CommandHandler, f'cmd_{name}') and not hasattr(CommandHandler, f"cmd_{name.replace('_', '')}"):
                unknown.append(f"{cls}:{e['id']}")
    check(not unknown, f'every class-book skill is a command ({unknown})')

    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    asyncio.run(main())
