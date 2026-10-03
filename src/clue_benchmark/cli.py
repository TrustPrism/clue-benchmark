"""CLI: generation, validation, exports, suite creation, evaluation."""

import argparse
import json
from pathlib import Path

from .config import Config
from .dataset import (
    atomic_json,
    build_bank,
    create_suite,
    create_suite_v03,
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
    ev.add_argument("--include-privileged", action="store_true")
    suite = sub.add_parser("suite")
    suite.add_argument("--output", default="data/v0.2")
    suite.add_argument("--workers", type=int, default=1)
    suite.add_argument("--dev", type=int, default=30)
    suite.add_argument("--test", type=int, default=100)
    suite3 = sub.add_parser("suite-v03")
    suite3.add_argument("--output", default="data/v0.3")
    suite3.add_argument("--workers", type=int, default=1)
    suite3.add_argument("--dev-worlds", type=int, default=12)
    suite3.add_argument("--test-worlds", type=int, default=28)
    audit = sub.add_parser("audit")
    audit.add_argument("input", nargs="+")
    audit.add_argument("--output", required=True)
    audit.add_argument("--max-solver-calls", type=int, default=1200)
    audit.add_argument("--trajectory", action="store_true")
    review = sub.add_parser("review-packet")
    review.add_argument("input")
    review.add_argument("--output", required=True)
    review.add_argument("--per-cell", type=int, default=2)
    duplicates = sub.add_parser("duplicate-audit")
    duplicates.add_argument("input", nargs="+")
    duplicates.add_argument("--output", required=True)
    comparison = sub.add_parser("compare-investigation")
    comparison.add_argument("input")
    comparison.add_argument("--repeats", type=int, default=3)
    comparison.add_argument("--output", required=True)
    comparison.add_argument("--summary-only", action="store_true")
    preparation = sub.add_parser("prepare-study")
    preparation.add_argument("--dev", required=True)
    preparation.add_argument("--test", required=True)
    preparation.add_argument("--root", default=".")
    preparation.add_argument("--model", action="append", default=[])
    preparation.add_argument("--repeats", type=int, default=3)
    preparation.add_argument(
        "--topic-mode", action="append", choices=["targeted", "attribute"]
    )
    preparation.add_argument(
        "--prompt-style", action="append", choices=["standard", "deliberate"]
    )
    preparation.add_argument("--generation-config")
    preparation.add_argument("--output", required=True)
    for command in ("study-check", "study-export"):
        check = sub.add_parser(command)
        check.add_argument("plan")
        check.add_argument("--root", default=".")
        if command == "study-export":
            check.add_argument("logs", nargs="+")
            check.add_argument("--output", required=True)
    review_preparation = sub.add_parser("prepare-review")
    review_preparation.add_argument("input", nargs="+")
    review_preparation.add_argument("--output", required=True)
    review_preparation.add_argument("--template")
    review_check = sub.add_parser("review-check")
    review_check.add_argument("packet")
    review_check.add_argument("responses", nargs="*")
    review_check.add_argument("--output", required=True)
    review_check.add_argument("--cases", nargs="*")
    review_check.add_argument("--require-approved", action="store_true")
    ready = sub.add_parser("readiness")
    ready.add_argument("dataset")
    ready.add_argument("--output", required=True)
    ready.add_argument("--review-report")
    ready.add_argument("--study-results")
    ready.add_argument("--public", action="store_true")
    args = parser.parse_args()
    try:
        if args.command in ("prepare-study", "study-check", "study-export"):
            from .study import export_study, prepare_study, verify_study

            if args.command == "prepare-study":
                settings = (
                    json.loads(Path(args.generation_config).read_text())
                    if args.generation_config
                    else None
                )
                plan = prepare_study(
                    args.dev,
                    args.test,
                    args.root,
                    args.model,
                    args.repeats,
                    args.topic_mode or ("attribute",),
                    args.prompt_style or ("standard",),
                    settings,
                )
                atomic_json(args.output, plan)
                print(
                    json.dumps(
                        {
                            "plan_id": plan["plan_id"],
                            "status": plan["status"],
                            "paid_calls": 0,
                        }
                    )
                )
            else:
                plan = json.loads(Path(args.plan).read_text())
                if args.command == "study-check":
                    print(json.dumps(verify_study(plan, args.root)))
                else:
                    from inspect_ai.log import read_eval_log

                    result = export_study(
                        plan, args.root, [read_eval_log(path) for path in args.logs]
                    )
                    atomic_json(args.output, result)
                    print(json.dumps(result["manifest"]))
            return
        if args.command in (
            "prepare-review",
            "review-check",
            "readiness",
            "compare-investigation",
        ):
            if args.command == "prepare-review":
                from .review import prepare_review, review_template

                cases = [c for path in args.input for c in read_cases(path)]
                for c in cases:
                    validate_case(c)
                packet = prepare_review(cases)
                atomic_json(args.output, packet)
                if args.template:
                    atomic_json(args.template, review_template(packet))
                print(
                    json.dumps(
                        {
                            "packet_id": packet["packet_id"],
                            "items": len(packet["items"]),
                            "status": packet["status"],
                        }
                    )
                )
            elif args.command == "review-check":
                from .review import collect_reviews

                packet = json.loads(Path(args.packet).read_text())
                responses = [json.loads(Path(p).read_text()) for p in args.responses]
                cases = [c for p in args.cases or [] for c in read_cases(p)]
                report = collect_reviews(packet, responses, cases)
                atomic_json(args.output, report)
                print(
                    json.dumps(
                        {
                            "status": report["status"],
                            "reviewers": len(report["reviewers"]),
                            "blocking_issues": report["blocking_issues"],
                        }
                    )
                )
                if args.require_approved and report["status"] != "approved":
                    raise SystemExit(2)
            elif args.command == "readiness":
                from .readiness import readiness_report

                review = (
                    json.loads(Path(args.review_report).read_text())
                    if args.review_report
                    else None
                )
                results = (
                    json.loads(Path(args.study_results).read_text())
                    if args.study_results
                    else None
                )
                report = readiness_report(args.dataset, review, results)
                atomic_json(args.output, report)
                print(json.dumps(report))
                if args.public and not report["public_release_ready"]:
                    raise SystemExit(2)
            else:
                from .investigation import compare_investigation

                cases = read_cases(args.input)
                for c in cases:
                    validate_case(c)
                report = compare_investigation(cases, args.repeats)
                if args.summary_only:
                    del report["episodes"]
                atomic_json(args.output, report)
                print(json.dumps(report["manifest"]))
            return
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
        elif args.command == "suite-v03":
            manifest = create_suite_v03(
                args.output, args.workers, args.dev_worlds, args.test_worlds
            )
            print(
                json.dumps(
                    {
                        "version": manifest["version"],
                        "worlds": manifest["worlds"],
                        "cases": manifest["cases"],
                        "output": args.output,
                    }
                )
            )
        else:
            cases = (
                [case for path in args.input for case in read_cases(path)]
                if args.command in ("audit", "duplicate-audit")
                else read_cases(args.input)
            )
            if not cases:
                raise ValueError("no cases")
            if args.command == "duplicate-audit":
                from .audit import duplicate_report

                atomic_json(args.output, duplicate_report(cases))
                print(json.dumps({"cases": len(cases), "output": args.output}))
            elif args.command == "audit":
                from .audit import audit_suite

                for c in cases:
                    validate_case(c)
                result = audit_suite(cases, args.max_solver_calls, args.trajectory)
                atomic_json(args.output, result)
                print(json.dumps({"cases": len(cases), "output": args.output}))
            elif args.command == "review-packet":
                from .audit import human_review_packet

                for c in cases:
                    validate_case(c)
                atomic_json(args.output, human_review_packet(cases, args.per_cell))
                print(json.dumps({"cases": len(cases), "output": args.output}))
            elif args.command == "validate":
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
                result = evaluate(cases, args.repeats, args.include_privileged)
                episode_count = len(result["episodes"])
                if args.summary_only:
                    result["manifest"]["episode_count"] = episode_count
                    del result["episodes"]
                atomic_json(args.output, result)
                print(json.dumps({"episodes": episode_count, "output": args.output}))
    except (ValueError, RuntimeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    except ImportError as exc:
        parser.exit(
            2,
            f"error: install the optional dependencies required by this command: {exc}\n",
        )
