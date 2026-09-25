"""Bounded representative candidate counts along the public deduction clue order."""

import argparse
import json
import math
from collections import defaultdict

from clue_benchmark.audit import audit_case
from clue_benchmark.dataset import atomic_json, read_cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    cases = [case for path in args.inputs for case in read_cases(path)]
    by_cell_density = defaultdict(list)
    for case in cases:
        by_cell_density[case.get("cell"), len(case["clues"])].append(case)
    selected = [
        min(group, key=lambda case: case["case_id"])
        for _, group in sorted(by_cell_density.items())
    ]
    rows = []
    for case in selected:
        audit = audit_case(case, max_solver_calls=1200, trajectory=True)
        if not audit["complete"]:
            raise RuntimeError(f"inconclusive candidate trajectory: {case['case_id']}")
        path = audit["candidate_trajectory"]
        rows.append(
            {
                "case_id": case["case_id"],
                "cell": case.get("cell"),
                "suspects": len(case["suspects"]),
                "clues": len(case["clues"]),
                "candidate_counts": {
                    str(fraction): path[math.ceil((len(path) - 1) * fraction)]
                    for fraction in (0, 0.25, 0.5, 0.75, 1.0)
                },
            }
        )
    summary = []
    for n in sorted({row["suspects"] for row in rows}):
        group = [row for row in rows if row["suspects"] == n]
        summary.append(
            {
                "suspects": n,
                "sample_cases": len(group),
                "mean_candidates": {
                    key: sum(row["candidate_counts"][key] for row in group) / len(group)
                    for key in ("0", "0.25", "0.5", "0.75", "1.0")
                },
            }
        )
    atomic_json(
        args.output,
        {
            "selection": "Lowest case ID per cell and clue density; 72 representative cases",
            "order": "Stored deduction clue order; not an adaptive investigation policy",
            "rows": rows,
            "summary": summary,
        },
    )
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
