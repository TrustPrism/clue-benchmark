"""Offline example: evaluate your own callable on complete or private evidence.

python examples/evaluate_public_agent.py --dataset runs/basic \
  --agent evaluate_public_agent:always_abstain --output runs/scored.json

The callable sees only public fields. This is an API boundary, not process-level
isolation: run untrusted agent code in a separate sandbox with only public files.
"""

import argparse
import importlib

from clue_benchmark.public_api import evaluate_agent


def always_abstain(observation):
    return {"kind": "abstain"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--agent", required=True, help="importable.module:callable")
    parser.add_argument("--agent-id", type=int)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    module, name = args.agent.rsplit(":", 1)
    evaluate_agent(
        args.dataset,
        getattr(importlib.import_module(module), name),
        args.output,
        args.agent_id,
    )


if __name__ == "__main__":
    main()
