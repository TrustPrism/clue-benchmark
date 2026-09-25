"""Bounded data-quality diagnostics; these are not model difficulty labels."""

from collections import Counter
from dataclasses import replace
from itertools import combinations
from pathlib import Path

from clue_benchmark.config import Config
from clue_benchmark.dataset import atomic_json, read_cases
from clue_benchmark.logic import is_indirect
from clue_benchmark.solver import Outcome, Solver, Unresolved

root = Path(__file__).resolve().parents[1]
cases = read_cases(root / "data/v0.2/private/dev.jsonl") + read_cases(
    root / "data/v0.2/private/test.jsonl"
)
summary = []
for n in (4, 8, 12):
    group = [c for c in cases if len(c["suspects"]) == n]
    types = Counter(c["type"] for case in group for c in case["clues"])
    direct = 0
    necessity = []
    errors = 0
    for case in group:
        solver = Solver(
            case["suspects"],
            case["domains"],
            replace(Config(**case["config"]), generation_seconds=10),
        )
        try:
            direct += (
                solver.check([c for c in case["clues"] if not is_indirect(c)]).status
                == Outcome.UNIQUE
            )
            necessity.append(
                sum(
                    solver.check(case["clues"][:i] + case["clues"][i + 1 :]).status
                    != Outcome.UNIQUE
                    for i in range(len(case["clues"]))
                )
            )
        except Unresolved:
            errors += 1
    subset_results = []
    for case in [c for c in group if c["split"] == "dev"][:10]:
        solver = Solver(
            case["suspects"],
            case["domains"],
            replace(Config(**case["config"]), generation_seconds=10),
        )
        minimum = None
        status = "greater_than_3"
        try:
            for size in (1, 2, 3):
                if any(
                    solver.check(subset).status == Outcome.UNIQUE
                    for subset in combinations(case["clues"], size)
                ):
                    minimum = size
                    status = "exact"
                    break
        except Unresolved:
            status = "inconclusive"
        subset_results.append(
            {"case_id": case["case_id"], "minimum": minimum, "status": status}
        )
    summary.append(
        {
            "suspects": n,
            "cases": len(group),
            "clue_type_counts": dict(types),
            "direct_only_solvable": direct,
            "mean_necessary_clues": sum(necessity) / len(necessity)
            if necessity
            else None,
            "inconclusive": errors,
            "murderer_counts": dict(Counter(c["solution"]["murderer"] for c in group)),
            "bounded_subset_audit_first_10_dev": subset_results,
        }
    )
    print(n, "audited", flush=True)
atomic_json(
    root / "results/dataset-audit-v0.2.json",
    {
        "cells": summary,
        "claims": "Diagnostics, not calibrated reasoning difficulty. Subset search capped at size three and ten seconds per case.",
    },
)
