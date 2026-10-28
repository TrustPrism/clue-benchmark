"""Export saved development outcomes for documentation, without model calls."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

FIELDS = {
    "abstained",
    "actual_microdollars",
    "agent",
    "ambiguous_evidence",
    "arm",
    "assignment_id",
    "case_id",
    "condition",
    "correct",
    "dispatched",
    "finish_reason",
    "input_tokens",
    "local_seconds",
    "maximum_microdollars",
    "model",
    "name",
    "outcome",
    "output_tokens",
    "protocol_valid",
    "repeat",
    "request_id",
    "returned_model",
    "schedule",
    "sufficient_evidence",
    "supported",
    "thinking_present",
    "thinking_tokens",
    "transport",
    "usage_known",
    "variant",
    "wall_seconds",
    "world_id",
}


def load(path):
    return json.loads(Path(path).read_text())


def provenance(path):
    return {
        "original_source": str(path),
        "original_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "sanitization": "Positive field allowlist; no observations, provider prose, receipts, credentials, authorizations or ledgers.",
    }


def project(rows):
    return [{key: row[key] for key in sorted(FIELDS & row.keys())} for row in rows]


def summarize(rows, keys):
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(key) for key in keys)].append(row)
    return [
        {
            **dict(zip(keys, identity, strict=True)),
            "assigned": len(group),
            "worlds": len({r["world_id"] for r in group}),
            "outcomes": dict(sorted(Counter(r["outcome"] for r in group).items())),
            "valid_actions": sum(r.get("protocol_valid") is True for r in group),
            "supported_correct": sum(
                r.get("supported") is True and r.get("correct") is True for r in group
            ),
            "output_tokens": sum(r.get("output_tokens") or 0 for r in group),
            "local_seconds": sum(r.get("local_seconds") or 0 for r in group),
        }
        for identity, group in sorted(grouped.items())
    ]


def export(output="docs/site/assets"):
    root = Path(output)
    source = Path("benchmarks/publication-screening-results.json")
    original = load(source)
    screening = {
        "study_id": "development-screening-2026-10-15",
        "provenance": provenance(source),
        "assigned": len(original["episodes"]),
        "accounting": original["accounting"],
        "episodes": project(original["episodes"]),
    }
    screening["summaries"] = summarize(
        screening["episodes"], ["model", "arm", "schedule"]
    )
    assert screening["assigned"] == 144
    outcomes = Counter(r["outcome"] for r in screening["episodes"])
    assert outcomes["interrupted_by_user"] == 2
    assert outcomes["unattempted"] == 42

    source = Path("runs/qwen-diagnostic-2026-10-15/analysis.json")
    original = load(source)
    diagnostic = {
        "study_id": "qwen-settings-diagnostic-2026-10-15",
        "provenance": provenance(source),
        "assigned": len(original["episodes"]),
        "episodes": project(original["episodes"]),
    }
    diagnostic["summaries"] = summarize(diagnostic["episodes"], ["variant"])
    assert diagnostic["assigned"] == 9
    assert len({r["world_id"] for r in diagnostic["episodes"]}) == 3
    assert sorted(s["valid_actions"] for s in diagnostic["summaries"]) == [2, 3, 3]
    assert all(s["supported_correct"] == 1 for s in diagnostic["summaries"])

    sampled = load(root / "qwen-sampled-screening.json")["episodes"]

    def slot(row):
        return (
            row["arm"],
            row["world_id"],
            row["condition"],
            row["agent"],
            row["repeat"],
        )

    lookup = {slot(row): row for row in sampled}
    returned = [
        row
        for row in screening["episodes"]
        if row["model"] == "qwen3.5-9b-8192"
        and row["outcome"] not in {"interrupted_by_user", "unattempted"}
    ]
    matched = [lookup[slot(row)] for row in returned]
    assert len(matched) == 29
    assert len({row["world_id"] for row in returned}) == 23
    assert sum(row["protocol_valid"] is True for row in matched) == 25
    assert sum(row["supported"] and row["correct"] for row in matched) == 12
    diagnostic["followup_reuse_note"] = (
        "All three sampled-8k diagnostic slots are carried forward in the later "
        "72-slot sampled panel; do not count them as fresh follow-up calls."
    )

    source = Path("runs/publication-v1-2026-10-15/evaluator/baseline-episodes.json")
    baselines = load(source)
    heuristic_source = source.with_name("construction-heuristic-summary.json")
    heuristic = load(heuristic_source)
    preparation_source = Path("benchmarks/publication-v1-preparation.json")
    preparation = load(preparation_source)
    offline = {
        "study_id": "offline-controls-2026-10-15",
        "model_calls": 0,
        "provenance": [
            provenance(source),
            provenance(heuristic_source),
            provenance(preparation_source),
        ],
        "prepared_bank": {
            key: preparation[key] for key in ["worlds", "variants", "bundles"]
        },
        "solver_controls": summarize(
            [r for r in baselines if r["baseline"] == "solver"],
            ["arm", "schedule"],
        ),
        "construction_heuristic": {
            "track": heuristic["track"],
            "arms": heuristic["arms"],
        },
    }
    burden = [
        row
        for row in heuristic["arms"]
        if row["arm"].startswith(("branching-", "equality_tree-"))
    ]
    assert len(burden) == 9
    assert all(r["assigned"] == r["supported"] == 6 for r in burden)

    for name, value in [
        ("development-screening.json", screening),
        ("qwen-settings-diagnostic.json", diagnostic),
        ("offline-controls.json", offline),
    ]:
        (root / name).write_text(json.dumps(value, indent=2) + "\n")

    families = [
        (
            "original-controls",
            "pilot.json",
            "Missing evidence, irrelevant volume and false-report count",
        ),
        (
            "high-thinking-controls",
            "hardness.json",
            "Structure, targeted corruption and truthful additions",
        ),
        (
            "flash-stress",
            "flash-limits.json",
            "Puzzle size, matched output budget and unavoidable-error development",
        ),
        (
            "fresh-hard-confirmation",
            "flash-hard-scale.json",
            "Fresh fixed-condition hard cases",
        ),
        (
            "initial-development-screening",
            "development-screening.json",
            "Initial burden, reliability, delivery and ambiguous controls",
        ),
        (
            "qwen-settings-diagnostic",
            "qwen-settings-diagnostic.json",
            "Thinking toggle and 8K versus 32K sampled output",
        ),
        (
            "sampled-qwen",
            "qwen-sampled-screening.json",
            "Complete sampled panel and matched completion/correctness comparison",
        ),
        (
            "nuisance-replication",
            "nuisance-extended-measurements.json",
            "Initial replication, final expansion and exploratory combination",
        ),
    ]
    index = {
        "schema_version": "clue-documentation-experiment-index-1",
        "updated": "2026-10-28",
        "scope": "Eight measured study families and separate offline controls; not a pooled leaderboard.",
        "definitions": {
            "assigned_slots": "Includes unavailable/unattempted or reused slots where the study defines them; not a count of fresh successful model calls.",
            "assigned_worlds": "Distinct world IDs within a family, including assigned unattempted worlds. Reused worlds across families must not be summed.",
        },
        "families": [
            {
                "id": identity,
                "question": question,
                "asset": name,
                "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
                "assigned_slots": len(load(root / name)["episodes"]),
                "assigned_worlds": len(
                    {row["world_id"] for row in load(root / name)["episodes"]}
                ),
            }
            for identity, name, question in families
        ],
        "offline_controls": {
            "asset": "offline-controls.json",
            "sha256": hashlib.sha256(
                (root / "offline-controls.json").read_bytes()
            ).hexdigest(),
            "model_calls": 0,
        },
    }
    (root / "experiment-source-index.json").write_text(
        json.dumps(index, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "screening_slots": 144,
                "diagnostic_slots": 9,
                "offline_heuristic_burden_arms": 9,
                "model_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    export()
