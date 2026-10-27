"""CLI for the separately versioned community dataset and evaluation modes."""

import argparse
import json
from pathlib import Path

from .community_bundle import generate_dataset, profile_dataset, validate_dataset
from .config import VERSION
from .dataset import atomic_json
from .presets import NAMES, preset, resolve_config


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="clue-benchmark",
        description="Generate, certify, export and evaluate configurable clue datasets.",
        epilog="Flat puzzle compatibility commands: generate, validate, export.",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("generate-dataset", "profile-dataset"):
        p = sub.add_parser(name)
        source = p.add_mutually_exclusive_group(required=True)
        source.add_argument("--config")
        source.add_argument("--preset", choices=NAMES)
        p.add_argument("--output")
        p.add_argument("--workers", type=int)
    p = sub.add_parser(
        "analyze-nuisance-followup",
        help="Offline assigned-slot and paired-world reanalysis",
    )
    p.add_argument("directory")
    p.add_argument("--output", required=True)
    p = sub.add_parser(
        "run-nuisance-followup",
        help="Dry-run by default; one combined allowance and human manifest authorization",
    )
    p.add_argument("directory")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--authorization")
    p = sub.add_parser(
        "prepare-nuisance-followup",
        help="Offline only; does not authorize or dispatch inference",
    )
    p.add_argument("--output", required=True)
    p.add_argument("--models", required=True)
    p.add_argument("--prior-bank", nargs="+", required=True)
    p = sub.add_parser("presets", help="Packaged, offline named configurations")
    modes = p.add_subparsers(dest="preset_command", required=True)
    modes.add_parser("list")
    modes.add_parser("show").add_argument("name", choices=NAMES)
    p = sub.add_parser("explain-config")
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--preset", choices=NAMES)
    source.add_argument("--config")
    p.add_argument("--output")
    p.add_argument("--workers", type=int)
    p = sub.add_parser(
        "export-public", help="Only permitted evidence; no evaluator files"
    )
    p.add_argument("directory")
    p.add_argument("--agent", type=int, default=0)
    p.add_argument("--output", required=True)
    p = sub.add_parser("inspect-case", help="Inspect public evidence only")
    p.add_argument("directory")
    p.add_argument("--case-id")
    p.add_argument("--agent", type=int, default=0)
    p = sub.add_parser("examples")
    modes = p.add_subparsers(dest="example_command", required=True)
    p = modes.add_parser("replay")
    p.add_argument(
        "name",
        choices=["distributed-evidence", "measured-results", "nuisance-followup"],
    )
    p.add_argument(
        "--figures",
        action="store_true",
        help="Optional matplotlib figures for measured-results",
    )
    p.add_argument("--output", required=True)
    p = sub.add_parser(
        "unpack-archive",
        help="Explicit local checksummed reproduction archive; refuses links/traversal",
    )
    p.add_argument("archive")
    p.add_argument("--sha256", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--maximum-bytes", type=int, default=1_000_000_000)
    p = sub.add_parser("report", help="Offline JSON and escaped local HTML")
    p.add_argument("source")
    p.add_argument("--output", required=True)
    p = sub.add_parser("validate-dataset")
    p.add_argument("directory")
    p = sub.add_parser("prepare-community-evaluation")
    p.add_argument("directory")
    p.add_argument(
        "--models",
        required=True,
        help="JSON list; models, settings, limits, and prices must be explicit",
    )
    p.add_argument("--output", required=True)
    p.add_argument(
        "--conditions", nargs="+", default=["complete", "independent", "sharing"]
    )
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument(
        "--input-view",
        choices=["structured_text", "text_only"],
        default="structured_text",
    )
    p.add_argument(
        "--graph", choices=["star", "ring", "chain", "complete"], default="complete"
    )
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--message-reports", type=int, default=64)
    p.add_argument("--ceiling-microdollars", type=int, required=True)
    p.add_argument("--max-requests", type=int, default=10000)
    p = sub.add_parser("run-community-evaluation")
    p.add_argument("plan")
    p.add_argument("--dataset", required=True)
    p.add_argument("--output", required=True)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--authorization",
        help="human-supplied, plan-bound authorization JSON; never generated by this command",
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "analyze-nuisance-followup":
            from .followup_analysis import analyze_followup

            result = analyze_followup(args.directory, args.output)
            print(
                json.dumps(
                    {k: v for k, v in result.items() if k not in {"episodes", "panels"}}
                )
            )
        elif args.command == "run-nuisance-followup":
            from .followup_runner import run_followup

            auth = (
                json.loads(Path(args.authorization).read_text())
                if args.authorization
                else None
            )
            result = run_followup(
                args.directory, authorization=auth, dry_run=not args.execute
            )
            print(json.dumps({k: v for k, v in result.items() if k != "reports"}))
            if result["status"] == "stopped":
                return 2
        elif args.command == "prepare-nuisance-followup":
            from .nuisance_followup import prepare_followup

            result = prepare_followup(
                args.output, json.loads(Path(args.models).read_text()), args.prior_bank
            )
            print(
                json.dumps(
                    {
                        k: v
                        for k, v in result.items()
                        if k
                        not in {
                            "candidate_blocks",
                            "selected_blocks",
                            "sources",
                            "rejections",
                            "prior_banks",
                        }
                    }
                )
            )
            if result["status"] == "unaffordable_or_incomplete":
                return 2
        elif args.command == "presets":
            result = (
                {name: preset(name)["purpose"] for name in NAMES}
                if args.preset_command == "list"
                else {
                    **preset(args.name),
                    "resolved": resolve_config(name=args.name).to_dict(),
                }
            )
            print(json.dumps(result))
        elif args.command == "explain-config":
            from .parameter_reference import explain_config

            config = resolve_config(
                name=args.preset,
                path=args.config,
                output=args.output,
                workers=args.workers,
            )
            print(
                json.dumps(
                    {
                        "software_version": VERSION,
                        "config": config.to_dict(),
                        "parameters": explain_config(config),
                    }
                )
            )
        elif args.command == "export-public":
            from .public_api import export_public

            print(json.dumps(export_public(args.directory, args.output, args.agent)))
        elif args.command == "inspect-case":
            from .public_api import inspect_case

            print(json.dumps(inspect_case(args.directory, args.case_id, args.agent)))
        elif args.command == "examples":
            from .replay import replay_example

            if args.name == "nuisance-followup":
                from .research_results import replay_nuisance

                result = replay_nuisance(args.output, figures=args.figures)
            elif args.name == "measured-results":
                from .results import replay_results

                result = replay_results(args.output, figures=args.figures)
            else:
                if args.figures:
                    raise ValueError("--figures is supported for measured-results only")
                result = replay_example(args.name, args.output)
            print(
                json.dumps(
                    {
                        k: v
                        for k, v in result.items()
                        if k
                        not in {"episodes", "studies", "phases", "combined", "panels"}
                    }
                )
            )
        elif args.command == "unpack-archive":
            from .archives import unpack_archive

            print(
                json.dumps(
                    unpack_archive(
                        args.archive, args.sha256, args.output, args.maximum_bytes
                    )
                )
            )
        elif args.command == "report":
            from .replay import write_report

            print(json.dumps(write_report(args.source, args.output)))
        elif args.command in ("generate-dataset", "profile-dataset"):
            config = resolve_config(
                name=args.preset,
                path=args.config,
                output=args.output,
                workers=args.workers,
            )
            result = (
                generate_dataset(config)
                if args.command == "generate-dataset"
                else profile_dataset(config)
            )
            print(
                json.dumps(
                    {
                        "complete": result["complete"],
                        "output": config.dataset.output_directory,
                        "cases": len(result.get("worlds", result.get("cases", []))),
                        "rejections": result["rejections"],
                    }
                )
            )
            if args.command == "profile-dataset":
                atomic_json(
                    Path(config.dataset.output_directory) / "profile.json", result
                )
            if not result["complete"]:
                return 2
        elif args.command == "validate-dataset":
            result = validate_dataset(args.directory)
            print(
                json.dumps({"status": result["status"], "cases": len(result["cases"])})
            )
        elif args.command == "prepare-community-evaluation":
            from .community_evaluation import prepare_evaluation

            models = json.loads(Path(args.models).read_text())
            plan = prepare_evaluation(
                args.directory,
                models,
                conditions=args.conditions,
                repeats=args.repeats,
                graph=args.graph,
                rounds=args.rounds,
                max_reports_per_message=args.message_reports,
                spending_ceiling_microdollars=args.ceiling_microdollars,
                max_requests=args.max_requests,
                input_view=args.input_view,
            )
            atomic_json(args.output, plan)
            print(
                json.dumps(
                    {
                        "plan_id": plan["plan_id"],
                        "external_inference": False,
                        "output": args.output,
                    }
                )
            )
        else:
            from .community_evaluation import run_evaluation

            plan = json.loads(Path(args.plan).read_text())
            authorization = (
                json.loads(Path(args.authorization).read_text())
                if args.authorization
                else None
            )
            result = run_evaluation(
                plan,
                args.dataset,
                args.output,
                dry_run=not args.execute,
                authorization=authorization,
            )
            if not args.execute:
                # A dry run writes only its report, never a dispatch ledger.
                atomic_json(Path(args.output) / "dry-run.json", result)
            print(
                json.dumps(
                    {
                        k: v
                        for k, v in result.items()
                        if k not in ("requests", "episodes", "summary")
                    }
                )
            )
            if args.execute and not result["complete"]:
                return 2
        return 0
    except (ValueError, TypeError, OSError, RuntimeError, KeyError, EOFError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
