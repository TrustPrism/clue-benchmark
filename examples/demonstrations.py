"""Prepare offline demonstrations and optional unexecuted model manifests.

python examples/demonstrations.py --output /path/to/output
Add --models /path/to/user-models.json --ceiling-microdollars N to prepare model
plans. This script has no execution option and never reads API credentials.
"""

import argparse
import json
from pathlib import Path

from clue_benchmark.community_bundle import generate_dataset, validate_dataset
from clue_benchmark.community_config import CommunityConfig
from clue_benchmark.dataset import atomic_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--models")
    parser.add_argument("--ceiling-microdollars", type=int)
    parser.add_argument(
        "--graph", choices=("star", "ring", "chain", "complete"), default="complete"
    )
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--message-reports", type=int, default=64)
    args = parser.parse_args()
    if args.models and args.ceiling_microdollars is None:
        parser.error("model plans require an explicit spending ceiling")
    results = []
    for size, noise in ((4, 0), (4, 100), (8, 0), (8, 100)):
        root = Path(args.output) / f"n{size}-noise{noise}"
        config = CommunityConfig.from_dict(
            {
                "puzzle": {
                    "family": "branching",
                    "config": {"suspect_count": size, "clue_count": size + 4},
                },
                "evidence": {
                    "irrelevant_records": noise,
                    "minimum_sufficient_clues": size,
                    "maximum_sufficient_clues": size,
                },
                "dataset": {
                    "count": args.count,
                    "seed": 7,
                    "output_directory": str(root),
                },
            }
        )
        manifest = generate_dataset(config)
        if not manifest["complete"]:
            raise RuntimeError("bounded generation incomplete; inspect rejection log")
        validation = validate_dataset(root)
        result = {
            "directory": str(root),
            "size": size,
            "nuisance_records": noise,
            "metrics": manifest["metrics"],
            "validation": validation["status"],
        }
        if args.models:
            from clue_benchmark.community_evaluation import prepare_evaluation

            models = json.loads(Path(args.models).read_text())
            plan = prepare_evaluation(
                root,
                models,
                spending_ceiling_microdollars=args.ceiling_microdollars,
                graph=args.graph,
                rounds=args.rounds,
                max_reports_per_message=args.message_reports,
            )
            atomic_json(root / "evaluation-plan.json", plan)
            result["unexecuted_plan_id"] = plan["plan_id"]
        results.append(result)
    atomic_json(
        Path(args.output) / "demonstrations.json",
        {
            "status": "offline_prepared",
            "model_calls": 0,
            "demonstrations": [
                "necessary evidence versus distractors",
                "complete versus independent versus shared evidence",
            ],
            "datasets": results,
        },
    )
    print(
        json.dumps({"status": "prepared", "datasets": len(results), "model_calls": 0})
    )


if __name__ == "__main__":
    main()
