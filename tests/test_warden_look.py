"""A warrior's look, offline: the warden (tools/art3d/blender/models/warden.py) is a warrior's to
choose with `appearance` (or the Character window in /play), kept with the character and sent in
the look as `style`; a warrior is not asked it as they are made (only a mage is asked theirs).

    python3 tests/test_warden_look.py
"""
import asyncio
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
import test_webmove as tw  # noqa: E402

check, failures = tw.check, tw.failures
STATS = {s: 13 for s in ('str', 'int', 'wis', 'dex', 'con', 'cha')}


async def main():
    import logging
    logging.disable(logging.WARNING)
    from config import Config
    Config.PLAYER_DIR = tempfile.mkdtemp()
    import player as pl
    from player import Player
    from commands import CommandHandler
    import gear_look
    import test_atlas_engine as tae

    check(pl.looks_for('warrior') == ['warden'] and pl.looks_for('mage') == ['archmage'] and pl.looks_for('thief') == ['footpad'], "each class's looks")
    from config import Config as _C
    check(all(len(pl.looks_for(c)) == 1 for c in _C.CLASSES), f'every class has one look beyond its own ({sorted(c for c in _C.CLASSES if len(pl.looks_for(c)) != 1)})')
    check('warrior' not in pl.LOOK_ASKED and 'mage' in pl.LOOK_ASKED, 'a mage is asked as they are made; a warrior is not')
    check(all(set(pl.LOOK_WORDS[c]) == {'classic', *pl.looks_for(c)} for c in pl.LOOK_WORDS), 'every look has its line')

    w = Player.create_new(name='Wardtest', password=None, race='human', char_class='warrior', stats=STATS, world=None, sex='male')
    w.connection = tae.Conn()
    check(w.look_style == '' and 'style' not in gear_look.look_of(w), 'a new warrior has the classic look')
    await CommandHandler.cmd_appearance(w, ['warden'])
    check(w.look_style == 'warden' and gear_look.look_of(w).get('style') == 'warden', 'appearance warden: the look says so at once')
    await CommandHandler.cmd_appearance(w, ['archmage'])
    check(w.look_style == 'warden', "a mage's look is not a warrior's to take")
    await w.save()
    again = Player.load('Wardtest', None)
    if asyncio.iscoroutine(again):
        again = await again
    check(again is not None and again.look_style == 'warden', 'it is kept with the character')
    await CommandHandler.cmd_appearance(w, ['classic'])
    check(w.look_style == '' and 'style' not in gear_look.look_of(w), 'and classic takes it off')

    m = Player.create_new(name='Wardmage', password=None, race='human', char_class='mage', stats=STATS, world=None, look_style='warden')
    m.connection = tae.Conn()
    check('style' not in gear_look.look_of(m), "a mage saved with a warrior's look shows their own")

    print('ALL OK' if not failures else f'{len(failures)} FAILED')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
