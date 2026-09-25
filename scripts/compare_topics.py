"""Paired world-clustered comparison chosen on development data: 75% evidence."""

import argparse
import json
import random
from collections import defaultdict

from clue_benchmark.dataset import atomic_json, read_cases
from clue_benchmark.evaluation import run_episode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output", required=True)
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
    cases = read_cases(args.input)
    grouped = defaultdict(list)
    for case in cases:
        for repeat in range(args.repeats):
            seed = int(case["case_id"][:12], 16) + repeat
            random_result = run_episode(case, "random_investigation", 0.75, seed)
            heuristic_result = run_episode(case, "topic_heuristic", 0.75, seed)
            if random_result["solver_error"] or heuristic_result["solver_error"]:
                raise RuntimeError("inconclusive symbolic comparison")
            grouped[len(case["suspects"]), case["world_group"]].append(
                heuristic_result["correct"] - random_result["correct"]
            )
    rows = []
    for n in sorted({n for n, _ in grouped}):
        differences = [
            sum(values) / len(values)
            for (size, _), values in grouped.items()
            if size == n
        ]
        rng = random.Random(0)
        bootstrap = sorted(
            sum(rng.choices(differences, k=len(differences))) / len(differences)
            for _ in range(10000)
        )
        rows.append(
            {
                "suspects": n,
                "worlds": len(differences),
                "heuristic_minus_random_accuracy": sum(differences) / len(differences),
                "cluster_bootstrap_ci95": [bootstrap[250], bootstrap[9750]],
            }
        )
    atomic_json(
        args.output,
        {
            "budget_fraction": 0.75,
            "selection": "Chosen after development-run inspection; held-out confirmation",
            "repeats": args.repeats,
            "policies": ["topic_heuristic", "random_investigation"],
            "rows": rows,
            "limitations": "Symbolic policies read structured revealed clues; no model language parsing or paid calls.",
        },
    )
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
