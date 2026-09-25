"""Clue schema and independent executable semantics."""

from .config import TYPES, canonical

FIELDS = {
    "unary_positive": {"suspect", "attribute", "value"},
    "unary_negative": {"suspect", "attribute", "value"},
    "crime_positive": {"attribute", "value"},
    "crime_negative": {"attribute", "value"},
    "crime_same_as": {"suspect", "attribute"},
    "crime_different_from": {"suspect", "attribute"},
    "indirect_positive": {"attr1", "val1", "attr2", "val2"},
    "indirect_negative": {"attr1", "val1", "attr2", "val2"},
}


def clean(clue):
    t = clue.get("type")
    if t not in TYPES:
        raise ValueError(f"unknown clue type {t}")
    if set(clue) - ({"type", "difficulty"} | FIELDS[t]):
        raise ValueError("unknown clue fields")
    if not FIELDS[t] <= set(clue):
        raise ValueError("missing clue fields")
    return {k: clue[k] for k in sorted({"type"} | FIELDS[t])}


def validate(clue, suspects, domains):
    c = clean(clue)
    if "suspect" in c and c["suspect"] not in suspects:
        raise ValueError("unknown suspect")
    for attr_key, val_key in (
        ("attribute", "value"),
        ("attr1", "val1"),
        ("attr2", "val2"),
    ):
        if attr_key in c:
            attr = c[attr_key]
            if attr not in domains:
                raise ValueError("unknown attribute")
            if val_key in c and c[val_key] not in domains[attr]:
                raise ValueError("unknown value")
    if "attr1" in c and c["attr1"] == c["attr2"]:
        raise ValueError("indirect attributes must differ")
    return c


def truth(c, world, murderer):
    t = c["type"]
    if t.startswith("unary_"):
        eq = world[c["suspect"]][c["attribute"]] == c["value"]
        return eq if t == "unary_positive" else not eq
    if t in ("crime_positive", "crime_negative"):
        eq = world[murderer][c["attribute"]] == c["value"]
        return eq if t == "crime_positive" else not eq
    if t in ("crime_same_as", "crime_different_from"):
        eq = world[murderer][c["attribute"]] == world[c["suspect"]][c["attribute"]]
        return eq if t == "crime_same_as" else not eq
    if t in ("indirect_positive", "indirect_negative"):
        exists = any(
            v[c["attr1"]] == c["val1"] and v[c["attr2"]] == c["val2"]
            for v in world.values()
        )
        return exists if t == "indirect_positive" else not exists
    raise ValueError("unknown clue type")


def fact_key(c):
    c = clean(c)
    if "attr1" in c and (c["attr1"], c["val1"]) > (c["attr2"], c["val2"]):
        c["attr1"], c["attr2"] = c["attr2"], c["attr1"]
        c["val1"], c["val2"] = c["val2"], c["val1"]
    return canonical(c)


def is_link(c):
    return c["type"].startswith("crime_")


def is_indirect(c):
    return c["type"] in (
        "indirect_positive",
        "indirect_negative",
        "crime_same_as",
        "crime_different_from",
        "crime_negative",
    )
