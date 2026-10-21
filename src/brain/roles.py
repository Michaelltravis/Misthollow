"""What a creature is in a fight: the roles a population file gives it ("ai": {"roles": [...]}),
else the ones read from its flags, words and name (mob_ai.classify_mob, which honours the data
roles itself so every older caller sees the same set)."""


def roles_for(mob) -> set:
    import mob_ai
    return mob_ai.classify_mob(mob)
