"""Offline matched hardness demonstrations. No command dispatches model calls.

prepare builds certified bundles; plan freezes supplied model settings and
per-job conservative spending limits; analyze scores completed harness outputs.
"""

import argparse
import json
from collections import Counter, defaultdict, deque
from pathlib import Path

from clue_benchmark.community_bundle import (
    _screen,
    export_dataset,
    file_hash,
    load_evaluator_cases,
    source_hashes,
    validate_dataset,
    verify_manifest,
)
from clue_benchmark.community_config import CommunityConfig
from clue_benchmark.community_evaluation import (
    prepare_evaluation,
    run_evaluation,
    summarize,
)
from clue_benchmark.community_generation import build_core, generate_case
from clue_benchmark.config import digest
from clue_benchmark.dataset import atomic_json


def arms(root, count=10, seed=107):
    single = {"agent_count": 1, "minimum_coalition_size": 1}
    groups = {}
    for size in (8, 16, 32):
        groups[f"reasoning-{size}"] = {
            f"{family}-{size}": {
                "puzzle": {
                    "family": family,
                    "extra_clue_scope": "non_target_attributes",
                    "config": {"suspect_count": size, "clue_count": size + 6},
                },
                "evidence": {
                    "minimum_sufficient_clues": size,
                    "maximum_sufficient_clues": size,
                    "irrelevant_records": 100,
                },
                "distribution": single,
                "presentation": {"evidence_placement": "interleaved"},
            }
            for family in ("equality_tree", "branching")
        }

    def relational(attributes):
        return {
            "family": "redundant_paths",
            "attribute_mismatches": attributes - 2,
            "config": {
                "suspect_count": 8,
                "clue_count": 9 * attributes,
                "domains": {
                    f"attribute{i}": ["0", "1", "2"] for i in range(attributes)
                },
            },
        }

    groups["false-reports"] = {
        f"relational-{strategy}-false-{false}": {
            "puzzle": relational(7),
            "distribution": single,
            "evidence": {
                "false_reports": false,
                "corruption_allowance": 2,
                "corruption_strategy": strategy,
                "corruption_search_attempts": 8,
                **(
                    {"maximum_alternative_margin": 3 - false}
                    if strategy == "targeted"
                    else {}
                ),
            },
        }
        for strategy, false in (
            ("random", 0),
            ("random", 1),
            ("random", 2),
            ("targeted", 1),
            ("targeted", 2),
        )
    }
    groups["near-solutions"] = {
        f"near-decoys-{decoys}-noise-{noise}": {
            "puzzle": relational(5),
            "distribution": single,
            "evidence": {
                "corruption_allowance": 2,
                "connected_decoys": decoys,
                "maximum_alternative_margin": 1,
                "irrelevant_records": noise,
            },
            "presentation": {"evidence_placement": "interleaved"},
        }
        for decoys, noise in ((0, 0), (12, 0), (12, 1000))
    }
    groups["archive-position"] = {
        f"archive-{placement}": {
            "puzzle": {
                "family": "equality_tree",
                "extra_clue_scope": "non_target_attributes",
                "config": {"suspect_count": 8, "clue_count": 14},
            },
            "evidence": {
                "minimum_sufficient_clues": 8,
                "maximum_sufficient_clues": 8,
                "irrelevant_records": 1000,
            },
            "distribution": single,
            "presentation": {"evidence_placement": placement},
        }
        for placement in ("front", "middle", "end", "interleaved")
    }
    groups["distributed"] = {
        "distributed-eight": {
            "puzzle": {
                "family": "equality_tree",
                "extra_clue_scope": "non_target_attributes",
                "config": {"suspect_count": 16, "clue_count": 22},
            },
            "evidence": {
                "minimum_sufficient_clues": 16,
                "maximum_sufficient_clues": 16,
            },
            "distribution": {"agent_count": 8, "minimum_coalition_size": 8},
        }
    }
    for group in groups.values():
        for name, value in list(group.items()):
            value["dataset"] = {
                "count": count,
                "seed": seed,
                "output_directory": str(Path(root) / name),
                "certification_seconds": 5
                if value["puzzle"]["family"] == "redundant_paths"
                else 30,
            }
            group[name] = CommunityConfig.from_dict(value)
    return groups


def structural_profile(case):
    """Shortest equality distance from explicit unary anchors, not proof depth."""
    graph = defaultdict(set)
    distance, queue = {}, deque()
    for r in case["reports"]:
        c = r["constraint"]
        if c["type"] == "unary_positive":
            key = c["suspect"], c["attribute"]
            distance[key] = 0
            queue.append(key)
        elif c["type"] == "suspect_same_as":
            left, right = (
                (c["suspect"], c["attribute"]),
                (c["other_suspect"], c["attribute"]),
            )
            graph[left].add(right)
            graph[right].add(left)
    while queue:
        node = queue.popleft()
        for other in sorted(graph[node]):
            if other not in distance:
                distance[other] = distance[node] + 1
                queue.append(other)
    return {
        "maximum_equality_distance_from_unary_anchor": max(
            distance.values(), default=0
        ),
        "report_types": dict(Counter(r["constraint"]["type"] for r in case["reports"])),
    }


def matched(results, group):
    cases = [r["case"] for r in results.values()]
    if len({c["world_id"] for c in cases}) != 1:
        raise ValueError("matched conditions changed the world")
    if group == "false-reports":
        original = None
        for result in results.values():
            restored = {r["report_id"] for r in result["case"]["reports"]}
            for change in result["certificate"]["corruptions"]:
                restored.remove(change["false_report_id"])
                restored.add(change["original_report_id"])
            original = restored if original is None else original
            if restored != original or result["case"]["corruption_allowance"] != 2:
                raise ValueError(
                    "false-report contrast changed the original reports/rules"
                )
    if group == "archive-position":
        if len({c["case_id"] for c in cases}) != 1:
            raise ValueError("position contrast changed evidence")
    if group.startswith("reasoning-"):
        backgrounds = []
        for c in cases:
            attr = next(
                r["constraint"]["attribute"]
                for r in c["reports"]
                if r["constraint"]["type"] == "crime_positive"
            )
            backgrounds.append(
                {
                    r["report_id"]
                    for r in c["reports"]
                    if attr
                    not in (
                        r["constraint"].get("attribute"),
                        r["constraint"].get("attr1"),
                        r["constraint"].get("attr2"),
                    )
                }
            )
        if any(b != backgrounds[0] for b in backgrounds[1:]):
            raise ValueError("topology comparison changed background facts")
    if group == "near-solutions":
        base = min(cases, key=lambda c: len(c["reports"]))
        baseline = {r["report_id"] for r in base["reports"]}
        sets = [set(r["report_id"] for r in c["reports"]) for c in cases]
        if any(not baseline <= s for s in sets) or sets[1] != sets[2]:
            raise ValueError("decoy/volume contrast changed original evidence")


def prepare(root, count=10, seed=107, attempts_per_world=20, selected_groups=None):
    if type(count) is not int or count < 1 or attempts_per_world < 1:
        raise ValueError("positive count and search budget required")
    root = Path(root)
    groups = arms(root, count, seed)
    if selected_groups is not None:
        if not selected_groups or set(selected_groups) - set(groups):
            raise ValueError("unknown/empty group selection")
        groups = {g: groups[g] for g in selected_groups}
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
        raise ValueError("suite inputs changed; use a new output directory")
    atomic_json(cp / "identity.json", identity)
    bundles, matching, rejections, measurements = {}, [], {}, []
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
            matched(results, group_name)
            fingerprints = {n: _screen(r["case"]) for n, r in results.items()}
            if any(
                w in seen[n][0] or p in seen[n][1] for n, (w, p) in fingerprints.items()
            ):
                rejected["matched_group_isomorphism_duplicate"] += 1
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
                "bounded matched generation incomplete; receipts retained for resume"
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
            validate_dataset(directory)
            bundles[name] = {
                "manifest_hash": file_hash(directory / "manifest.json"),
                "group": group_name,
                "worlds": manifest["worlds"],
            }
            by_case = {c["case_id"]: c for c in load_evaluator_cases(directory)}
            for metric in manifest["metrics"]:
                case = by_case[metric["case_id"]]
                certificate = case["saved_certificate"]["certificate"]
                cost = metric["necessary_evidence"]
                profile = certificate.get("reliability_profile", {})
                measurements.append(
                    {
                        "arm": name,
                        "group": group_name,
                        "world_id": case["world_id"],
                        "split": case["split"],
                        "seed": next(
                            w["seed"]
                            for w in manifest["worlds"]
                            if w["case_id"] == case["case_id"]
                        ),
                        "case_id": case["case_id"],
                        "words": metric["words"],
                        "tokens": metric["tokens"],
                        "reports": metric["total_reports"],
                        "core_reports": metric["core_reports"],
                        "necessary_evidence": {
                            k: cost[k] for k in ("status", "lower_bound", "upper_bound")
                        },
                        "alternative_margin": profile.get("alternative_margin"),
                        "minimum_coalition_size": certificate["coalition"][
                            "minimum_size"
                        ],
                        "false_reports": len(certificate["false_report_ids"]),
                        "true_core_structure": structural_profile(
                            build_core(
                                config,
                                case["seed"]
                                if "seed" in case
                                else next(
                                    w["seed"]
                                    for w in manifest["worlds"]
                                    if w["case_id"] == case["case_id"]
                                ),
                            )
                        ),
                        "certification_solver_seconds": metric[
                            "certification_solver_seconds"
                        ],
                    }
                )
    splits = defaultdict(set)
    for m in measurements:
        splits[m["world_id"]].add(m["split"])
    if any(len(s) != 1 for s in splits.values()):
        raise ValueError("world variants crossed splits")
    suite = {
        "schema_version": "clue-hardness-suite-1",
        "preparation_script_hash": file_hash(__file__),
        "count_per_arm": count,
        "seed": seed,
        "bundles": bundles,
        "matched_worlds": matching,
        "rejections": rejections,
        "measurements": measurements,
        "model_calls": 0,
        "model_results": "pending",
    }
    suite["suite_id"] = digest(suite)
    atomic_json(root / "suite.json", suite)
    return suite


def check_suite(root):
    root = Path(root)
    suite = json.loads((root / "suite.json").read_text())
    if suite["suite_id"] != digest({k: v for k, v in suite.items() if k != "suite_id"}):
        raise ValueError("suite identity mismatch")
    for name, bundle in suite["bundles"].items():
        verify_manifest(root / name)
        if file_hash(root / name / "manifest.json") != bundle["manifest_hash"]:
            raise ValueError("bundle changed since preparation")
    return suite


def plan(
    root,
    models,
    output,
    *,
    selected_arms=None,
    repeats=3,
    input_views=("text_only",),
    ceiling_microdollars=0,
):
    root, output = Path(root), Path(output)
    suite = check_suite(root)
    names = list(suite["bundles"]) if selected_arms is None else list(selected_arms)
    if not names or len(set(names)) != len(names) or set(names) - set(suite["bundles"]):
        raise ValueError("invalid arm selection")
    if not input_views or len(set(input_views)) != len(input_views):
        raise ValueError("input views must be nonempty and distinct")
    if type(ceiling_microdollars) is not int or ceiling_microdollars < 0:
        raise ValueError("nonnegative suite ceiling required")
    jobs, total_bound = [], 0
    for name in names:
        schedules = [("complete", {"conditions": ["complete"]})]
        if name == "distributed-eight":
            schedules += [
                ("private", {"conditions": ["independent"]}),
                ("star-one", {"conditions": ["sharing"], "graph": "star", "rounds": 1}),
                (
                    "ring-three",
                    {"conditions": ["sharing"], "graph": "ring", "rounds": 3},
                ),
                (
                    "chain-seven",
                    {"conditions": ["sharing"], "graph": "chain", "rounds": 7},
                ),
            ]
        for view in input_views:
            for label, schedule in schedules:
                p = prepare_evaluation(
                    root / name,
                    models,
                    repeats=repeats,
                    input_view=view,
                    minimum_request_interval_seconds=10,
                    **schedule,
                )
                dry = run_evaluation(p, root / name, output / "unused-dry-run")
                bound = sum(r["maximum_microdollars"] for r in dry["requests"])
                total_bound += bound
                jobs.append(
                    {
                        "name": f"{name}-{label}-{view}",
                        "arm": name,
                        "plan": p,
                        "request_count": dry["expected_requests"],
                        "maximum_microdollars": bound,
                        "all_contexts_fit": all(
                            r["context_fits"] for r in dry["requests"]
                        ),
                    }
                )
    fundable = total_bound <= ceiling_microdollars and all(
        j["all_contexts_fit"] for j in jobs
    )
    documents = {}
    for job in jobs:
        p = job.pop("plan")
        p["spending_ceiling_microdollars"] = (
            job["maximum_microdollars"] if fundable else 0
        )
        p["plan_id"] = digest({k: v for k, v in p.items() if k != "plan_id"})
        documents[output / (job["name"] + ".json")] = p
        job["plan_id"] = p["plan_id"]
    summary = {
        "schema_version": "clue-hardness-plans-1",
        "suite_id": suite["suite_id"],
        "jobs": jobs,
        "repeats": repeats,
        "input_views": list(input_views),
        "total_request_count": sum(j["request_count"] for j in jobs),
        "maximum_microdollars": total_bound,
        "suite_ceiling_microdollars": ceiling_microdollars,
        "fundable": fundable,
        "network_calls": 0,
        "authorization": "not_granted",
    }
    summary["plans_id"] = digest(summary)
    documents[output / "plans.json"] = summary
    for path, value in documents.items():
        if path.exists() and json.loads(path.read_text()) != value:
            raise ValueError("existing frozen plan differs; use a new output directory")
    for path, value in documents.items():
        atomic_json(path, value)
    return summary


def analyze(root, plans_root, run_root, output):
    """Use the harness's complete assigned denominator, including failures."""
    suite = check_suite(root)
    plans_root = Path(plans_root)
    plans = json.loads((plans_root / "plans.json").read_text())
    if plans["suite_id"] != suite["suite_id"] or plans["plans_id"] != digest(
        {k: v for k, v in plans.items() if k != "plans_id"}
    ):
        raise ValueError("plan suite changed")
    groups, missing = [], []
    for job in plans["jobs"]:
        path = Path(run_root) / job["name"] / "results.json"
        if not path.exists():
            missing.append(job["name"])
            continue
        result = json.loads(path.read_text())
        if result["plan_id"] != job["plan_id"]:
            raise ValueError("run belongs to another plan")
        episodes = result["episodes"]
        frozen = json.loads((plans_root / (job["name"] + ".json")).read_text())
        planned = run_evaluation(
            frozen, Path(root) / job["arm"], plans_root / "unused-dry-run"
        )["requests"]
        if len(episodes) != job["request_count"] or len(
            {e["request_id"] for e in episodes}
        ) != len(episodes):
            raise ValueError("assigned request coverage mismatch")
        if {e["request_id"] for e in episodes} != {r["request_id"] for r in planned}:
            raise ValueError("assigned request identities mismatch")
        worlds = defaultdict(list)
        for e in episodes:
            worlds[e["model"], e["world_id"]].append(e)
        clusters = [
            {
                "model": model,
                "world_id": world,
                "assigned": len(es),
                "correct_fraction": sum(e.get("correct", False) for e in es) / len(es),
                "supported_fraction": sum(e.get("supported", False) for e in es)
                / len(es),
            }
            for (model, world), es in worlds.items()
        ]
        groups.append(
            {
                "job": job["name"],
                "metrics": summarize(episodes),
                "world_clusters": clusters,
            }
        )
    report = {
        "schema_version": "clue-hardness-results-1",
        "suite_id": suite["suite_id"],
        "jobs": groups,
        "missing_jobs": missing,
        "complete": not missing,
        "inference": "descriptive only; repetitions and agent views cluster by world",
    }
    atomic_json(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--output", required=True)
    p.add_argument("--count", type=int, default=10)
    p.add_argument("--seed", type=int, default=107)
    p.add_argument("--groups", nargs="+")
    p.add_argument("--attempts-per-world", type=int, default=20)
    p = sub.add_parser("plan")
    p.add_argument("--datasets", required=True)
    p.add_argument("--models", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--arms", nargs="+")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--input-views", nargs="+", default=["text_only"])
    p.add_argument("--ceiling-microdollars", type=int, default=0)
    p = sub.add_parser("analyze")
    p.add_argument("--datasets", required=True)
    p.add_argument("--plans", required=True)
    p.add_argument("--runs", required=True)
    p.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(
            args.output, args.count, args.seed, args.attempts_per_world, args.groups
        )
        print(
            json.dumps(
                {
                    "suite_id": result["suite_id"],
                    "bundles": len(result["bundles"]),
                    "count_per_arm": result["count_per_arm"],
                    "model_calls": 0,
                }
            )
        )
    elif args.command == "plan":
        result = plan(
            args.datasets,
            json.loads(Path(args.models).read_text()),
            args.output,
            selected_arms=args.arms,
            repeats=args.repeats,
            input_views=args.input_views,
            ceiling_microdollars=args.ceiling_microdollars,
        )
        print(json.dumps({k: v for k, v in result.items() if k != "jobs"}))
    else:
        result = analyze(args.datasets, args.plans, args.runs, args.output)
        print(
            json.dumps(
                {"complete": result["complete"], "missing_jobs": result["missing_jobs"]}
            )
        )


if __name__ == "__main__":
    main()
