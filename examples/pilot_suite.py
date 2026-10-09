"""Matched, offline demonstrations and a separately authorized model pilot.

prepare -> plan (offline preflight) -> run (fresh approval) -> analyze.
No command creates an authorization or chooses models implicitly.
"""

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from clue_benchmark.community_bundle import (
    _screen,
    export_dataset,
    file_hash,
    load_evaluator_cases,
    rows,
    source_hashes,
    validate_dataset,
    verify_manifest,
)
from clue_benchmark.community_config import CommunityConfig
from clue_benchmark.community_evaluation import (
    _observations,
    check_plan,
    prepare_evaluation,
    run_evaluation,
)
from clue_benchmark.community_generation import generate_case
from clue_benchmark.community_semantics import evaluate
from clue_benchmark.config import digest
from clue_benchmark.dataset import atomic_json


def arms(root, count, seed):
    """One-factor contrasts; clue burden uses separate suspect-size strata."""
    groups = {}
    for burden in (4, 8):
        group = {}
        for noise in (0, 100, 1000):
            name = f"burden-{burden}-noise-{noise}"
            group[name] = {
                "puzzle": {
                    "family": "branching",
                    "config": {"suspect_count": burden, "clue_count": burden + 4},
                },
                "evidence": {
                    "minimum_sufficient_clues": burden,
                    "maximum_sufficient_clues": burden,
                    "irrelevant_records": noise,
                },
                "distribution": {"agent_count": 1, "minimum_coalition_size": 1},
            }
        groups[f"burden-{burden}"] = group
    groups["false-reports"] = {
        f"false-{false}": {
            "puzzle": {
                "config": {
                    "suspect_count": 4,
                    "clue_count": 30,
                    "domains": {f"attribute{i}": ["0", "1", "2"] for i in range(6)},
                    "enabled_types": ["crime_positive", "unary_positive"],
                    "mutation_steps": 0,
                }
            },
            "evidence": {"false_reports": false, "corruption_allowance": 2},
            "distribution": {"agent_count": 1, "minimum_coalition_size": 1},
        }
        for false in (0, 1, 2)
    }
    groups["distributed"] = {
        "distributed": {
            "puzzle": {
                "family": "branching",
                "config": {"suspect_count": 8, "clue_count": 12},
            },
            "evidence": {"minimum_sufficient_clues": 8, "maximum_sufficient_clues": 8},
            "distribution": {"agent_count": 4, "minimum_coalition_size": 4},
        }
    }
    for group in groups.values():
        for name, value in list(group.items()):
            value["dataset"] = {
                "count": count,
                "seed": seed,
                "output_directory": str(Path(root) / name),
                "certification_seconds": 5 if name.startswith("false-") else 30,
            }
            group[name] = CommunityConfig.from_dict(value)
    return groups


def paired(results, group):
    cases = [r["case"] for r in results.values()]
    if len({c["world_id"] for c in cases}) != 1:
        raise ValueError("matched conditions changed the sampled world")
    if group.startswith("burden-"):
        facts = [{r["report_id"] for r in c["reports"]} for c in cases]
        if any(f != facts[0] for f in facts[1:]):
            raise ValueError("noise contrast changed target-component evidence")
    if group == "false-reports":
        base = {r["report_id"] for r in results["false-0"]["case"]["reports"]}
        for result in results.values():
            case = result["case"]
            changes = result["certificate"]["corruptions"]
            restored = {r["report_id"] for r in case["reports"]}
            for change in changes:
                restored.remove(change["false_report_id"])
                restored.add(change["original_report_id"])
            if restored != base or case["corruption_allowance"] != 2:
                raise ValueError(
                    "false-report contrast changed the original core/rules"
                )


def prepare(root, count=8, seed=7, attempts_per_world=30):
    if type(count) is not int or count < 1 or attempts_per_world < 1:
        raise ValueError("positive count and search budget required")
    root = Path(root)
    groups = arms(root, count, seed)
    cp = root / ".community-checkpoints"
    cp.mkdir(parents=True, exist_ok=True)
    identity = {
        "sources": source_hashes(),
        "script": file_hash(__file__),
        "configs": {n: c.fingerprint for g in groups.values() for n, c in g.items()},
        "attempts_per_world": attempts_per_world,
    }
    if (cp / "identity.json").exists() and json.loads(
        (cp / "identity.json").read_text()
    ) != identity:
        raise ValueError("pilot inputs changed; use a new output directory")
    atomic_json(cp / "identity.json", identity)
    bundles, matching, rejections = {}, [], {}
    for group_name, group in groups.items():
        accepted = {name: [] for name in group}
        seen = {name: (set(), set()) for name in group}
        rejected = Counter()
        for candidate in range(seed, seed + count * attempts_per_world):
            results, paths = {}, {}
            for name, config in group.items():
                path = cp / f"{name}-{candidate}.json"
                if not path.exists():
                    atomic_json(path, generate_case(config, candidate))
                paths[name] = path
                results[name] = json.loads(path.read_text())
            failures = [
                f"{n}:{r['diagnostics']['reason']}"
                for n, r in results.items()
                if r["status"] != "ok"
            ]
            if failures:
                rejected.update(failures)
                continue
            paired(results, group_name)
            fingerprints = {name: _screen(r["case"]) for name, r in results.items()}
            if any(
                w in seen[n][0] or p in seen[n][1] for n, (w, p) in fingerprints.items()
            ):
                rejected["matched_group_duplicate"] += 1
                continue
            for name, (world, puzzle) in fingerprints.items():
                seen[name][0].add(world)
                seen[name][1].add(puzzle)
                accepted[name].append(paths[name])
            matching.append(
                {
                    "group": group_name,
                    "seed": candidate,
                    "world_id": next(iter(results.values()))["case"]["world_id"],
                    "cases": {n: r["case"]["case_id"] for n, r in results.items()},
                }
            )
            if len(next(iter(accepted.values()))) == count:
                break
        rejections[group_name] = dict(rejected)
        if len(next(iter(accepted.values()))) != count:
            atomic_json(
                root / "incomplete.json",
                {
                    "group": group_name,
                    "accepted": len(next(iter(accepted.values()))),
                    "rejections": rejections,
                },
            )
            raise RuntimeError(
                "bounded matched generation incomplete; retained receipts permit resume"
            )
        for name, config in group.items():
            directory = root / name
            directory.mkdir(exist_ok=True)
            manifest = export_dataset(config, accepted[name], directory)
            manifest.update(
                {
                    "complete": True,
                    "matched_group": group_name,
                    "rejections": dict(rejected),
                    "checkpoint_identity": identity,
                }
            )
            atomic_json(directory / "manifest.json", manifest)
            validated = validate_dataset(directory)
            if validated["status"] != "verified":
                raise ValueError("pilot bundle did not pass independent validation")
            bundles[name] = {
                "manifest_hash": file_hash(directory / "manifest.json"),
                "worlds": manifest["worlds"],
            }
    suite = {
        "schema_version": "clue-pilot-suite-1",
        "preparation_script_hash": file_hash(__file__),
        "count_per_arm": count,
        "seed": seed,
        "bundles": bundles,
        "matched_worlds": matching,
        "rejections": rejections,
        "model_calls": 0,
        "model_results": "pending",
    }
    suite["suite_id"] = digest(suite)
    atomic_json(root / "suite.json", suite)
    audit(root, suite)
    return suite


def check_suite(root):
    root = Path(root)
    suite = json.loads((root / "suite.json").read_text())
    if suite["suite_id"] != digest({k: v for k, v in suite.items() if k != "suite_id"}):
        raise ValueError("suite identity mismatch")
    for name, bundle in suite["bundles"].items():
        verify_manifest(root / name)
        if file_hash(root / name / "manifest.json") != bundle["manifest_hash"]:
            raise ValueError("frozen pilot bundle changed")
    return suite


def audit(root, suite):
    """Engine controls diagnose information availability, not model competence."""
    root = Path(root)
    result = {"status": "offline_controls", "model_calls": 0, "arms": []}
    for name in suite["bundles"]:
        manifest = verify_manifest(root / name)
        certificates = list(rows(root / name / "certificates.jsonl"))
        metrics = manifest["metrics"]
        result["arms"].append(
            {
                "arm": name,
                "worlds": len(metrics),
                "total_reports": sorted({m["total_reports"] for m in metrics}),
                "words": [
                    min(m["words"] for m in metrics),
                    max(m["words"] for m in metrics),
                ],
                "necessary_evidence_bounds": [
                    [
                        r["certificate"]["minimum_subset"]["lower_bound"],
                        r["certificate"]["minimum_subset"]["upper_bound"],
                    ]
                    for r in certificates
                ],
                "all_unique": all(
                    r["certificate"]["status"] == "verified_unique"
                    for r in certificates
                ),
                "minimum_sufficient_coalition": sorted(
                    {
                        r["certificate"]["coalition"]["minimum_size"]
                        for r in certificates
                    }
                ),
            }
        )
    controls = []
    for case in load_evaluator_cases(root / "distributed"):
        manifest = verify_manifest(root / "distributed")
        for graph, rounds_count in (
            ("star", 1),
            ("ring", 1),
            ("chain", 1),
            ("chain", 3),
        ):
            plan = {
                "dataset_config": manifest["config"],
                "prompt": "Identify the responsible suspect.",
                "models": [{"context_tokens": 1048576}],
                "graph": graph,
                "rounds": rounds_count,
                "max_reports_per_message": 64,
            }
            for condition in ("complete", "independent", "sharing"):
                for agent, _, evidence, messages, _ in _observations(
                    case, plan, condition
                ):
                    possible = evaluate(case, evidence)["candidates"]
                    controls.append(
                        {
                            "world_id": case["world_id"],
                            "graph": graph,
                            "rounds": rounds_count,
                            "condition": condition,
                            "agent": agent,
                            "possible_answers": len(possible),
                            "sufficient": len(possible) == 1,
                            "solver_action": "answer"
                            if len(possible) == 1
                            else "abstain",
                            "messages": len(messages),
                        }
                    )
    result["information_controls"] = controls
    corruption_controls = []
    for name in ("false-0", "false-1", "false-2"):
        for case in load_evaluator_cases(root / name):
            correct_rules = evaluate(case, case["reports"])["candidates"]
            naive_rules = evaluate(
                {**case, "corruption_allowance": 0}, case["reports"]
            )["candidates"]
            corruption_controls.append(
                {
                    "arm": name,
                    "world_id": case["world_id"],
                    "reliability_aware_solver_unique": len(correct_rules) == 1,
                    "assume_all_true_possible_answers": len(naive_rules),
                    "assume_all_true_recovers_answer": naive_rules == correct_rules,
                }
            )
    result["corruption_controls"] = corruption_controls
    result["interpretation"] = (
        "Solver controls verify availability only; no LLM performance is measured."
    )
    atomic_json(root / "diagnostics.json", result)
    return result


def schedules(suite):
    for name in suite["bundles"]:
        if name == "distributed":
            yield name + "-reference", name, {"conditions": ("complete", "independent")}
            for graph, rounds_count in (
                ("star", 1),
                ("ring", 1),
                ("chain", 1),
                ("chain", 3),
            ):
                yield (
                    f"{name}-{graph}-{rounds_count}",
                    name,
                    {
                        "conditions": ("sharing",),
                        "graph": graph,
                        "rounds": rounds_count,
                    },
                )
        else:
            yield name, name, {"conditions": ("complete",)}


def plan_pilot(root, models, ceiling, repeats=1, interval_seconds=10):
    """Divide a SINGLE ceiling across immutable plans; never $20 per arm."""
    root = Path(root)
    suite = check_suite(root)
    if type(ceiling) is not int or ceiling < 1 or interval_seconds < 0:
        raise ValueError("positive ceiling and nonnegative request interval required")
    drafts = []
    for job, arm, settings in schedules(suite):
        plan = prepare_evaluation(
            root / arm,
            models,
            repeats=repeats,
            minimum_request_interval_seconds=interval_seconds,
            **settings,
        )
        dry = run_evaluation(plan, root / arm, root / "preflight" / job, dry_run=True)
        preflights = dry["requests"]
        if any(not p["context_fits"] for p in preflights):
            raise ValueError(
                "context overflow: pilot preparation stopped before any model call"
            )
        drafts.append(
            (
                job,
                arm,
                settings,
                sum(p["maximum_microdollars"] for p in preflights),
                len(preflights),
            )
        )
    required = sum(item[3] for item in drafts)
    if required > ceiling:
        raise ValueError(
            f"conservative pilot maximum {required} exceeds ceiling {ceiling}; explicitly reduce count/repeats"
        )
    remainder = ceiling - required
    jobs = []
    for index, (job, arm, settings, maximum, requests) in enumerate(drafts):
        allocation = (
            maximum + remainder // len(drafts) + (index < remainder % len(drafts))
        )
        plan = prepare_evaluation(
            root / arm,
            models,
            repeats=repeats,
            spending_ceiling_microdollars=allocation,
            max_requests=requests,
            minimum_request_interval_seconds=interval_seconds,
            **settings,
        )
        path = root / "plans" / f"{job}.json"
        if path.exists() and json.loads(path.read_text()) != plan:
            raise ValueError(
                "existing job plan differs; use a separate suite directory"
            )
        atomic_json(path, plan)
        jobs.append(
            {
                "job": job,
                "arm": arm,
                "plan_id": plan["plan_id"],
                "ceiling_microdollars": allocation,
                "requests": requests,
                "conservative_maximum_microdollars": maximum,
            }
        )
    pilot = {
        "schema_version": "clue-pilot-evaluation-1",
        "runner_hash": file_hash(__file__),
        "suite_id": suite["suite_id"],
        "jobs": jobs,
        "models": models,
        "repeats": repeats,
        "spending_ceiling_microdollars": ceiling,
        "max_requests": sum(j["requests"] for j in jobs),
        "conservative_maximum_microdollars": required,
        "minimum_request_interval_seconds": interval_seconds,
        "model_calls": 0,
        "authorization": "pending",
    }
    pilot["pilot_id"] = digest(pilot)
    path = root / "pilot-plan.json"
    if path.exists() and json.loads(path.read_text()) != pilot:
        raise ValueError(
            "existing pilot plan differs; keep frozen plans in a separate suite directory"
        )
    atomic_json(path, pilot)
    return pilot


def run_pilot(root, authorization):
    root = Path(root)
    suite = check_suite(root)
    pilot = json.loads((root / "pilot-plan.json").read_text())
    if (
        pilot["pilot_id"] != digest({k: v for k, v in pilot.items() if k != "pilot_id"})
        or pilot["suite_id"] != suite["suite_id"]
        or pilot["runner_hash"] != file_hash(__file__)
    ):
        raise ValueError("frozen pilot identity changed")
    expected = {
        "schema_version": "clue-pilot-authorization-1",
        "pilot_id": pilot["pilot_id"],
        "spending_ceiling_microdollars": pilot["spending_ceiling_microdollars"],
        "max_requests": pilot["max_requests"],
    }
    if (
        set(authorization) != set(expected) | {"approved_by", "approved_at"}
        or any(authorization[k] != v for k, v in expected.items())
        or any(
            not isinstance(authorization[k], str) or not authorization[k].strip()
            for k in ("approved_by", "approved_at")
        )
    ):
        raise PermissionError("new explicit pilot-bound approval required")
    plans = []
    for job in pilot["jobs"]:
        plan = json.loads((root / "plans" / f"{job['job']}.json").read_text())
        check_plan(plan, root / job["arm"])
        if (
            plan["plan_id"] != job["plan_id"]
            or plan["spending_ceiling_microdollars"] != job["ceiling_microdollars"]
        ):
            raise ValueError("pilot job changed")
        plans.append(plan)
    if (
        sum(p["spending_ceiling_microdollars"] for p in plans)
        > pilot["spending_ceiling_microdollars"]
    ):
        raise ValueError("job ceilings exceed the total pilot ceiling")
    if any(m["vendor"] != "google" for m in pilot["models"]):
        raise ValueError("paced reference runner supports Gemini only")
    for job, plan in zip(pilot["jobs"], plans, strict=True):
        auth = {
            **authorization,
            "schema_version": "clue-community-authorization-1",
            "plan_id": plan["plan_id"],
            "spending_ceiling_microdollars": plan["spending_ceiling_microdollars"],
            "max_requests": plan["max_requests"],
        }
        auth.pop("pilot_id")
        report = run_evaluation(
            plan,
            root / job["arm"],
            root / "evaluation" / job["job"],
            dry_run=False,
            authorization=auth,
        )
        if not report["complete"]:
            break  # Unknown usage/protocol accounting stops the entire pilot.
    return analyze(root)


def contrast(left, right):
    """Average repetitions/agents within each world, then paired world bootstrap."""

    def values(episodes):
        groups = defaultdict(list)
        for e in episodes:
            groups[e["world_id"]].append(float(bool(e.get("supported"))))
        return {w: sum(v) / len(v) for w, v in groups.items()}

    a, b = values(left), values(right)
    if not a or set(a) != set(b):
        raise ValueError("paired contrast requires the same assigned worlds")
    differences = [b[w] - a[w] for w in sorted(a)]
    rng = random.Random(0)
    samples = sorted(
        sum(rng.choice(differences) for _ in differences) / len(differences)
        for _ in range(2000)
    )
    return {
        "worlds": len(differences),
        "supported_accuracy_delta": sum(differences) / len(differences),
        "descriptive_paired_world_bootstrap_95_interval": [samples[49], samples[1949]],
    }


def analyze(root):
    root = Path(root)
    suite = check_suite(root)
    jobs, missing = {}, []
    for job, arm, _ in schedules(suite):
        path = root / "evaluation" / job / "results.json"
        if path.exists():
            jobs[job] = json.loads(path.read_text())
        else:
            missing.append(job)
    result = {
        "status": "model_results_pending"
        if not jobs
        else "partial"
        if missing or any(not r["complete"] for r in jobs.values())
        else "complete",
        "missing_jobs": missing,
        "summaries": {j: r["summary"] for j, r in jobs.items()},
        "contrasts": [],
    }
    comparisons = [
        (f"burden-{b}-noise-0", "complete", f"burden-{b}-noise-{n}", "complete")
        for b in (4, 8)
        for n in (100, 1000)
    ]
    comparisons += [("false-0", "complete", f"false-{f}", "complete") for f in (1, 2)]
    comparisons += [
        ("distributed-reference", "complete", "distributed-reference", "independent")
    ]
    comparisons += [
        ("distributed-chain-1", "sharing", "distributed-chain-3", "sharing"),
        ("distributed-star-1", "sharing", "distributed-ring-1", "sharing"),
    ]
    for j1, c1, j2, c2 in comparisons:
        if j1 not in jobs or j2 not in jobs:
            continue
        models = {e["model"] for e in jobs[j1]["episodes"]} & {
            e["model"] for e in jobs[j2]["episodes"]
        }
        for model in sorted(models):
            a, b = (
                [
                    e
                    for e in jobs[j]["episodes"]
                    if e["model"] == model and e["condition"] == c
                ]
                for j, c in ((j1, c1), (j2, c2))
            )
            result["contrasts"].append(
                {
                    "model": model,
                    "reference": j1 + "/" + c1,
                    "comparison": j2 + "/" + c2,
                    **contrast(a, b),
                }
            )
    result["interpretation"] = (
        "Small exploratory pilot; all assigned failures remain in denominators. No significance or frontier-weakness claim."
    )
    atomic_json(root / "pilot-results.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "plan", "run", "analyze"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--models")
    parser.add_argument("--ceiling-microdollars", type=int)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--authorization")
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.output, args.count, args.seed)
    elif args.command == "plan":
        if not args.models or args.ceiling_microdollars is None:
            parser.error("plan requires explicit models and a total ceiling")
        result = plan_pilot(
            args.output,
            json.loads(Path(args.models).read_text()),
            args.ceiling_microdollars,
            args.repeats,
        )
    elif args.command == "run":
        if not args.authorization:
            parser.error("run requires fresh pilot-bound authorization")
        result = run_pilot(
            args.output, json.loads(Path(args.authorization).read_text())
        )
    else:
        result = analyze(args.output)
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k
                in (
                    "status",
                    "suite_id",
                    "pilot_id",
                    "max_requests",
                    "model_calls",
                    "conservative_maximum_microdollars",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
