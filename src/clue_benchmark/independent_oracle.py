"""Direct world checks independent of production constraint builders.

Corruption-aware integer and Boolean solver encodings are in community_semantics.
"""


def holds(clue, world, culprit):
    t = clue["type"]
    if t in ("unary_positive", "unary_negative", "crime_positive", "crime_negative"):
        owner = clue["suspect"] if t.startswith("unary") else culprit
        match = world[owner][clue["attribute"]] == clue["value"]
        return match == t.endswith("positive")
    if t in (
        "crime_same_as",
        "crime_different_from",
        "suspect_same_as",
        "suspect_different_from",
    ):
        left = culprit if t.startswith("crime") else clue["other_suspect"]
        match = (
            world[left][clue["attribute"]] == world[clue["suspect"]][clue["attribute"]]
        )
        return match == t.endswith("same_as")
    if t in ("indirect_positive", "indirect_negative"):
        count = sum(
            (v[clue["attr1"]], v[clue["attr2"]]) == (clue["val1"], clue["val2"])
            for v in world.values()
        )
        return (count > 0) == (t == "indirect_positive")
    raise ValueError("Unknown clue type")


def valid_world(suspects, domains, world):
    return set(world) == set(suspects) and all(
        set(world[s]) == set(domains)
        and all(world[s][a] in domains[a] for a in domains)
        for s in suspects
    )
