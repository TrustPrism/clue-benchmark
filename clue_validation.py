"""Truth, metadata, and solver validation for generated clue banks."""

from clue_metadata import METADATA_KEYS, clue_fact_id, solver_fields


def clue_is_true(clue, world, murderer):
    clue_type = clue["type"]
    if clue_type == "unary_positive":
        return world[clue["suspect"]][clue["attribute"]] == clue["value"]
    if clue_type == "unary_negative":
        return world[clue["suspect"]][clue["attribute"]] != clue["value"]
    if clue_type == "crime_positive":
        return world[murderer][clue["attribute"]] == clue["value"]
    if clue_type == "crime_negative":
        return world[murderer][clue["attribute"]] != clue["value"]
    if clue_type == "crime_same_as":
        return (
            world[murderer][clue["attribute"]]
            == world[clue["suspect"]][clue["attribute"]]
        )
    if clue_type == "crime_different_from":
        return (
            world[murderer][clue["attribute"]]
            != world[clue["suspect"]][clue["attribute"]]
        )
    if clue_type == "indirect_positive":
        return any(
            attrs[clue["attr1"]] == clue["val1"]
            and attrs[clue["attr2"]] == clue["val2"]
            for attrs in world.values()
        )
    if clue_type == "indirect_negative":
        return all(
            not (
                attrs[clue["attr1"]] == clue["val1"]
                and attrs[clue["attr2"]] == clue["val2"]
            )
            for attrs in world.values()
        )
    raise ValueError(f"unknown clue type: {clue_type}")


def validate_clue_record(record, world, murderer, solver):
    missing = METADATA_KEYS - set(record)
    if missing:
        return False, f"missing metadata fields: {sorted(missing)}"

    structured = record["solver_fields"]
    if record["clue_fact_id"] != clue_fact_id(structured):
        return False, "clue_fact_id does not match solver fields"
    if record["clue_type"] != structured.get("type"):
        return False, "clue_type does not match solver fields"
    if not clue_is_true(structured, world, murderer):
        return False, "clue is not true for generated world"
    if not solver.is_true_murderer_feasible([structured]):
        return False, "clue excludes the true murderer in the solver"
    return True, None


def validate_bank(records, raw_items, world, murderer, solver):
    if len(records) != len(raw_items):
        return False, "record/raw clue count mismatch"

    for record in records:
        valid, reason = validate_clue_record(record, world, murderer, solver)
        if not valid:
            return False, reason

    if not solver.is_unique(raw_items):
        return False, "bank does not identify a unique murderer"
    return True, None


def necessary_clues(raw_items, solver):
    """Mark clues whose removal makes the bank non-unique."""
    return [
        not solver.is_unique(raw_items[:index] + raw_items[index + 1:])
        for index in range(len(raw_items))
    ]
