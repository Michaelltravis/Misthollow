"""The rules creatures lived by before the brain, as its first policy (phase 0): out of a fight
Mobile.legacy_idle_ai (hunting, patrols, aggression, wandering), in one mob_ai's
_legacy_declare_intents and _legacy_mob_ai_tick. Each phase moves a part of them into the brain
behind its feature flag; this file goes when the last has (docs/MOB_AI.md)."""


async def idle(mob):
    return await mob.legacy_idle_ai()


async def declare(mob):
    import mob_ai
    return await mob_ai._legacy_declare_intents(mob)


async def combat_turn(mob):
    import mob_ai
    return await mob_ai._legacy_mob_ai_tick(mob)
