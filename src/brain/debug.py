"""Immortal commands for looking inside creatures' heads.

    brain <creature>    its tier, rank, roles, profile numbers, threat table and last decisions
    brainstat [reset]   how long the creatures' thinking takes per tick
"""


async def cmd_brain(cls, player, args):
    """Show what a creature here is thinking (immortal)."""
    c = player.config.COLORS
    if not getattr(player, 'is_immortal', False):
        await player.send("Huh?")
        return
    if not args:
        await player.send("Whose brain? (brain <creature>)")
        return
    from mobs import Mobile
    mob = player.find_target_in_room(' '.join(args))
    if not isinstance(mob, Mobile):
        await player.send("No creature like that here.")
        return
    import brain
    lines = brain.of(mob).describe()
    await player.send(f"{c['bright_cyan']}{lines[0]}{c['reset']}")
    for ln in lines[1:]:
        await player.send(ln)


async def cmd_brainstat(cls, player, args):
    """How long the creatures' thinking takes per tick (immortal). "brainstat reset" starts over."""
    if not getattr(player, 'is_immortal', False):
        await player.send("Huh?")
        return
    from .scheduler import STATS
    if args and args[0].lower() == 'reset':
        STATS.reset()
        await player.send("Brain timings reset.")
        return
    for ln in STATS.lines():
        await player.send(ln)


def install():
    from commands import CommandHandler
    CommandHandler.cmd_brain = classmethod(cmd_brain)
    CommandHandler.cmd_brainstat = classmethod(cmd_brainstat)
