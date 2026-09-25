"""CLI: generation, validation, exports, suite creation, evaluation."""

import argparse
import json
from pathlib import Path

from .config import Config
from .dataset import (
    atomic_json,
    build_bank,
    create_suite,
    read_cases,
    study_export,
    write_jsonl,
)
from .environment import public_puzzle
from .generation import validate_case


def main():
    parser = argparse.ArgumentParser(prog="clue-benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--config")
    gen.add_argument("--seed", type=int, default=0)
    gen.add_argument("--suspects", type=int)
    gen.add_argument("--clues", type=int)
    gen.add_argument("--count", type=int, default=1)
    gen.add_argument("--workers", type=int, default=1)
    gen.add_argument("--output", required=True)
    val = sub.add_parser("validate")
    val.add_argument("input")
    exp = sub.add_parser("export")
    exp.add_argument("input")
    exp.add_argument("--format", choices=["public", "study"], default="public")
    exp.add_argument("--output", required=True)
    ev = sub.add_parser("evaluate")
    ev.add_argument("input")
    ev.add_argument("--repeats", type=int, default=1)
    ev.add_argument("--output", required=True)
    ev.add_argument("--summary-only", action="store_true")
    suite = sub.add_parser("suite")
    suite.add_argument("--output", default="data/v0.2")
    suite.add_argument("--workers", type=int, default=1)
    suite.add_argument("--dev", type=int, default=30)
    suite.add_argument("--test", type=int, default=100)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            config = json.loads(Path(args.config).read_text()) if args.config else {}
            if args.suspects is not None:
                config["suspect_count"] = args.suspects
            if args.clues is not None:
                config["clue_count"] = args.clues
            cfg = Config(**config)
            result = build_bank(cfg, args.count, args.seed, args.output, args.workers)
            print(
                json.dumps(
                    {"complete": result["complete"], "cases": len(result["cases"])}
                )
            )
            if not result["complete"]:
                raise SystemExit(2)
        elif args.command == "suite":
            if args.dev < 1 or args.test < 1:
                raise ValueError("positive split sizes required")
            print(
                json.dumps(create_suite(args.output, args.workers, args.dev, args.test))
            )
        else:
            cases = read_cases(args.input)
            if not cases:
                raise ValueError("no cases")
            if args.command == "validate":
                for c in cases:
                    validate_case(c)
                print(f"Validated {len(cases)} cases")
            elif args.command == "export":
                for c in cases:
                    validate_case(c)
                if args.format == "public":
                    write_jsonl(args.output, [public_puzzle(c) for c in cases])
                else:
                    atomic_json(args.output, study_export(cases))
            else:
                from .evaluation import evaluate

                for c in cases:
                    validate_case(c)
                result = evaluate(cases, args.repeats)
                episode_count = len(result["episodes"])
                if args.summary_only:
                    result["manifest"]["episode_count"] = episode_count
                    del result["episodes"]
                atomic_json(args.output, result)
                print(json.dumps({"episodes": episode_count, "output": args.output}))
    except (ValueError, RuntimeError) as exc:
        parser.exit(2, f"error: {exc}\n")
