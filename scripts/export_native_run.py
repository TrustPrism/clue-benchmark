"""Export a consistent saved-run snapshot without any model requests."""

import argparse
import json
from pathlib import Path

from clue_benchmark.dataset import atomic_json
from clue_benchmark.ledger import Ledger
from clue_benchmark.runner import execution_cases, export_run
from clue_benchmark.study import verify_study


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plan")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root)
    plan = json.loads(Path(args.plan).read_text())
    verify_study(plan, root, require_models=True)
    output = root / plan["execution_directory"]
    if not (output / "ledger.sqlite3").exists():
        raise ValueError("saved ledger required; export cannot initialize spending")
    ledger = Ledger(output / "ledger.sqlite3", plan)
    try:
        ledger.db.execute("BEGIN")
        result = export_run(plan, execution_cases(plan, root), ledger)
        costs = result["ledger"]
        ledger.db.rollback()
        atomic_json(output / "results.json", result)
        atomic_json(output / "cost-ledger.json", costs)
        print(
            json.dumps(
                {
                    "manifest": result["manifest"],
                    "settled_usd": costs["settled_usd"],
                    "held_or_unresolved_usd": costs["unresolved_reservations_usd"],
                    "committed_usd": costs["committed_usd"],
                    "remaining_usd": costs["remaining_usd"],
                    "generation_calls": 0,
                }
            )
        )
    finally:
        ledger.close()


if __name__ == "__main__":
    main()
