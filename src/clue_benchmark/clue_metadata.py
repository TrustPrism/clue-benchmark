"""Stable metadata and import records for generated clues."""

import hashlib
import json
from collections import Counter

GENERATOR_VERSION = "24"
SOLVER_UNIQUENESS_DEFINITION = "unique_murderer"
METADATA_KEYS = {
    "case_id",
    "clue_id",
    "clue_fact_id",
    "bank_tier",
    "clue_complexity",
    "clue_type",
    "formatted_text",
    "links_directly_to_murderer",
    "is_indirect",
    "necessary_for_uniqueness",
    "solver_fields",
}


def case_id_for_seed(seed):
    return f"case-{seed}-v{GENERATOR_VERSION}"


def solver_fields(clue):
    """Return the structured fields consumed by the CSP solver."""
    return {key: value for key, value in clue.items() if key != "difficulty"}


def _digest(payload):
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def clue_fact_id(clue):
    """Identify a logical fact independently of bank or presentation."""
    return f"fact-{_digest(solver_fields(clue))}"


def clue_id_for(case_id, bank_tier, fact_id, occurrence=0):
    return f"clue-{_digest([case_id, bank_tier, fact_id, occurrence])}"


def is_indirect_clue_type(clue_type):
    return clue_type in {
        "indirect_positive",
        "indirect_negative",
    }


def links_to_murderer(clue_type):
    return clue_type in {
        "crime_positive",
        "crime_negative",
        "crime_same_as",
        "crime_different_from",
    }


def decorate_clue(
    clue,
    case_id,
    bank_tier,
    formatted_text,
    necessary_for_uniqueness=False,
    occurrence=0,
):
    clue_type = clue["type"]
    fact_id = clue_fact_id(clue)
    return {
        "case_id": case_id,
        "clue_id": clue_id_for(case_id, bank_tier, fact_id, occurrence),
        "clue_fact_id": fact_id,
        "bank_tier": bank_tier,
        "clue_complexity": clue.get("difficulty", "unknown"),
        "clue_type": clue_type,
        "formatted_text": formatted_text,
        "links_directly_to_murderer": links_to_murderer(clue_type),
        "is_indirect": is_indirect_clue_type(clue_type),
        "necessary_for_uniqueness": necessary_for_uniqueness,
        "solver_fields": solver_fields(clue),
    }


def duplicate_stats(records):
    fact_counts = Counter(record["clue_fact_id"] for record in records)
    text_counts = Counter(record["formatted_text"] for record in records)
    return {
        "exact_duplicate_fact_count": sum(
            count - 1 for count in fact_counts.values() if count > 1
        ),
        "exact_duplicate_text_count": sum(
            count - 1 for count in text_counts.values() if count > 1
        ),
        "unique_fact_count": len(fact_counts),
        "unique_text_count": len(text_counts),
    }
