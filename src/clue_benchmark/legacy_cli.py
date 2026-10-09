"""Compatibility for the original generate, validate and export commands."""

import argparse
import json
from copy import deepcopy
from pathlib import Path

from .clue_formatter import ClueFormatter
from .config import Config
from .dataset import atomic_json, build_bank, read_cases, study_export, write_jsonl
from .generation import validate_case


def public_puzzle(case):
    return {
        "case_id": case["case_id"],
        "rules": "Exactly one suspect is the murderer. Every suspect has exactly one value per attribute. "
        "Different suspects may share values. The crime's attributes equal the murderer's attributes. "
        "All clues are truthful. Only the murderer, not the full world, must be uniquely identifiable.",
        "suspects": list(case["suspects"]),
        "domains": deepcopy(case["domains"]),
        "clues": [
            {"clue_id": f"c{i + 1:03d}", "text": ClueFormatter.format(c)}
            for i, c in enumerate(case["clues"])
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(prog="clue-benchmark", description=__doc__)
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
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            config = json.loads(Path(args.config).read_text()) if args.config else {}
            if args.suspects is not None:
                config["suspect_count"] = args.suspects
            if args.clues is not None:
                config["clue_count"] = args.clues
            result = build_bank(
                Config(**config), args.count, args.seed, args.output, args.workers
            )
            print(
                json.dumps(
                    {"complete": result["complete"], "cases": len(result["cases"])}
                )
            )
            return 0 if result["complete"] else 2
        cases = read_cases(args.input)
        if not cases:
            raise ValueError("no cases")
        for case in cases:
            validate_case(case)
        if args.command == "validate":
            print(f"Validated {len(cases)} cases")
        elif args.format == "public":
            write_jsonl(args.output, [public_puzzle(c) for c in cases])
        else:
            atomic_json(args.output, study_export(cases))
        return 0
    except (ValueError, RuntimeError, TypeError) as exc:
        parser.exit(2, f"error: {exc}\n")
