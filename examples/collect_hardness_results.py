"""Reanalyse saved hardness receipts offline; never contact providers.

Usage: python examples/collect_hardness_results.py --datasets runs/hardness-v2
  --plans runs/hardness-v2-plans --runs runs/hardness-model-results
  --output runs/hardness-model-results/measured-results.json
  --episodes runs/hardness-model-results/measured-episodes.jsonl
"""

import argparse
import importlib.util
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from clue_benchmark.community_bundle import file_hash
from clue_benchmark.community_evaluation import summarize
from clue_benchmark.config import digest
from clue_benchmark.dataset import atomic_json

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--datasets", type=Path, required=True)
parser.add_argument("--plans", type=Path, required=True)
parser.add_argument("--runs", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--episodes", type=Path, required=True)
parser.add_argument("--measured-date", default="2026-10-10")
parser.add_argument("--continuation", type=Path, action="append", default=[])
args = parser.parse_args()
RUN, PLANS = args.runs, args.plans
spec = importlib.util.spec_from_file_location(
    "suite", Path(__file__).with_name("hardness_suite.py")
)
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)
summary = json.loads((PLANS / "plans.json").read_text())
if len(summary["input_views"]) != 1:
    raise ValueError("This collector compares one input view at a time")
base = suite.analyze(
    args.datasets,
    PLANS,
    RUN,
    args.output.with_name(args.output.stem + "-clustered.json"),
)
metrics = []
episodes = []
sources = []
world_values = {}
original_plans = {
    job["name"]: json.loads((PLANS / (job["name"] + ".json")).read_text())
    for job in summary["jobs"]
}
replacements = {}
continuation_ids = []
for root in args.continuation:
    follow = json.loads((root / "continuation-plan.json").read_text())
    if (
        follow["continuation_id"]
        != digest({k: v for k, v in follow.items() if k != "continuation_id"})
        or follow["continuation_of"] != summary["plans_id"]
    ):
        raise ValueError("Continuation identity differs")
    continuation_ids.append(follow["continuation_id"])
    mappings = {m["continuation_request_id"]: m for m in follow["assignment_map"]}
    if len(mappings) != follow["request_count"]:
        raise ValueError("Duplicate continuation assignments")
    seen = set()
    for job in follow["jobs"]:
        frozen = json.loads((root / "plans" / (job["name"] + ".json")).read_text())
        if frozen["plan_id"] != job["plan_id"]:
            raise ValueError("Continuation plan differs")
        planned = suite.run_evaluation(
            frozen, root / "datasets" / job["arm"], root / "unused-dry-run"
        )["requests"]
        assignments = {e["request_id"]: e for e in planned}
        if len(assignments) != job["request_count"]:
            raise ValueError("Continuation request coverage differs")
        for ident, expected in assignments.items():
            mapping = mappings[ident]
            if mapping["continuation_job"] != job["name"]:
                raise ValueError("Continuation mapping refers to another job")
            if mapping["continuation_repeat"] != expected["repeat"]:
                raise ValueError("Continuation repetition differs")
            if any(mapping[k] != expected[k] for k in ("case_id", "model")):
                raise ValueError("Continuation mapping fields differ")
            original_plan = original_plans[mapping["original_job"]]
            protocol_fields = (
                "prompt",
                "input_view",
                "tool_access",
                "forwarding_policy_identity",
                "graph",
                "rounds",
                "max_reports_per_message",
            )
            if any(frozen[k] != original_plan[k] for k in protocol_fields):
                raise ValueError("Continuation changes the original protocol")
            model = next(m for m in frozen["models"] if m["id"] == expected["model"])
            if model != next(
                m for m in original_plan["models"] if m["id"] == expected["model"]
            ):
                raise ValueError("Continuation changes the original model settings")
            seen.add(ident)
        path = root / "evaluation" / job["name"] / "results.json"
        if not path.exists():
            continue
        result = json.loads(path.read_text())
        if (
            len(result["episodes"]) != job["request_count"]
            or result["plan_id"] != job["plan_id"]
            or {e["request_id"] for e in result["episodes"]} != set(assignments)
        ):
            raise ValueError("Continuation receipts differ from the assignments")
        sources.append(
            {
                "job": job["name"],
                "plan_id": job["plan_id"],
                "continuation_id": follow["continuation_id"],
                "result_hash": file_hash(path),
                "accounting": result["accounting"],
                "complete": result["complete"],
                "stopped_reason": result["stopped_reason"],
            }
        )
        for e in result["episodes"]:
            ident = e["request_id"]
            expected = assignments[ident]
            if any(
                e.get(k) != expected.get(k)
                for k in (
                    "case_id",
                    "world_id",
                    "model",
                    "condition",
                    "agent",
                    "repeat",
                    "input_token_upper_bound",
                    "maximum_microdollars",
                )
            ):
                raise ValueError("Continuation receipt fields differ")
            if not e.get("dispatched"):
                continue
            mapping = mappings[ident]
            original = mapping["original_request_id"]
            if original in replacements:
                raise ValueError("Multiple receipts replace one assignment")
            replacements[original] = {
                **e,
                "request_id": original,
                "repeat": mapping["original_repeat"],
                "execution_request_id": ident,
                "execution_plan_id": job["plan_id"],
                "execution_continuation_id": follow["continuation_id"],
                "original_job": mapping["original_job"],
            }
    if seen != set(mappings):
        raise ValueError("Continuation mapping coverage differs")
used_replacements = set()
for job in summary["jobs"]:
    p = RUN / job["name"] / "results.json"
    frozen = json.loads((PLANS / (job["name"] + ".json")).read_text())
    if frozen["conditions"] != ["complete"]:
        raise ValueError("This collector requires complete-information jobs")
    planned = suite.run_evaluation(
        frozen, args.datasets / job["arm"], PLANS / "unused-dry-run"
    )["requests"]
    assignments = {e["request_id"]: e for e in planned}
    result = (
        json.loads(p.read_text())
        if p.exists()
        else {
            "complete": False,
            "episodes": [
                {
                    **e,
                    "dispatched": False,
                    "transport": "not_attempted",
                    "correct": False,
                    "supported": False,
                    "protocol_valid": False,
                }
                for e in planned
            ],
        }
    )
    for index, episode in enumerate(result["episodes"]):
        ident = episode["request_id"]
        if ident in replacements:
            if episode.get("dispatched"):
                raise ValueError(
                    "Cannot replace a dispatched request, including failure"
                )
            replacement = replacements[ident]
            if replacement["original_job"] != job["name"]:
                raise ValueError("Replacement belongs to another original job")
            result["episodes"][index] = replacement
            used_replacements.add(ident)
    identity_fields = (
        "case_id",
        "world_id",
        "model",
        "condition",
        "agent",
        "repeat",
        "input_token_upper_bound",
        "maximum_microdollars",
    )
    for episode in result["episodes"]:
        expected = assignments[episode["request_id"]]
        if any(episode.get(k) != expected.get(k) for k in identity_fields):
            raise ValueError("Receipt fields differ from the frozen assignment")
    split_map = {w["world_id"]: w["split"] for w in frozen["worlds"]}
    if p.exists():
        original_result = json.loads(p.read_text())
        sources.append(
            {
                "job": job["name"],
                "plan_id": job["plan_id"],
                "result_hash": file_hash(p),
                "accounting": original_result["accounting"],
                "complete": original_result["complete"],
                "stopped_reason": original_result["stopped_reason"],
            }
        )
    for e in result["episodes"]:
        episodes.append({"job": job["name"], "arm": job["arm"], **e})
    modelnames = sorted(set(e["model"] for e in result["episodes"]))
    for model in modelnames:
        es = [e for e in result["episodes"] if e["model"] == model]
        cap = next(
            m["settings"]["max_output_tokens"]
            for m in frozen["models"]
            if m["id"] == model
        )
        byworld = defaultdict(list)
        for e in es:
            byworld[e["world_id"]].append(e)
        if all(e.get("dispatched") for e in es):
            world_values[job["arm"], model] = {
                w: sum(bool(e.get("supported")) for e in values) / len(values)
                for w, values in byworld.items()
            }
        lat = [
            e["wall_seconds"]
            for e in es
            if e.get("dispatched") and e.get("wall_seconds") is not None
        ]
        metrics.append(
            {
                "arm": job["arm"],
                "job": job["name"],
                "model": model,
                "max_output_tokens": cap,
                "assigned": len(es),
                "worlds": len(byworld),
                "returned_models": sorted(
                    {e["returned_model"] for e in es if e.get("returned_model")}
                ),
                "evaluator_unresolved": sum(
                    e.get("evaluator_status") == "unknown" for e in es
                ),
                "unattempted": sum(not e.get("dispatched", False) for e in es),
                "cap_terminations": sum(
                    e.get("receipt", {}).get("finish_reason") == "MAX_TOKENS"
                    for e in es
                ),
                "near_output_cap_responses": sum(
                    (e.get("output_tokens") or 0) >= 0.95 * cap for e in es
                ),
                "split_results": {
                    split: {
                        "assigned": sum(split_map[e["world_id"]] == split for e in es),
                        "correct": sum(
                            e.get("correct", False)
                            for e in es
                            if split_map[e["world_id"]] == split
                        ),
                        "supported": sum(
                            e.get("supported", False)
                            for e in es
                            if split_map[e["world_id"]] == split
                        ),
                    }
                    for split in sorted(set(split_map.values()))
                },
                "dispatched": sum(e.get("dispatched", False) for e in es),
                "usage_known": sum(e.get("usage_known", False) for e in es),
                "correct": sum(e.get("correct", False) for e in es),
                "supported": sum(e.get("supported", False) for e in es),
                "abstentions": sum(e.get("abstained", False) for e in es),
                "protocol_failures": sum(
                    e.get("usage_known", False) and not e.get("protocol_valid", False)
                    for e in es
                ),
                "execution_failures": sum(
                    e.get("dispatched", False) and not e.get("protocol_valid", False)
                    for e in es
                ),
                "provider_failures": sum(
                    e.get("dispatched", False) and not e.get("usage_known", False)
                    for e in es
                ),
                "wrong_valid_answers": sum(
                    e.get("protocol_valid", False)
                    and not e.get("correct", False)
                    and not e.get("abstained", False)
                    for e in es
                ),
                "finish_reasons": dict(
                    Counter(
                        e.get("receipt", {}).get("finish_reason", "unavailable")
                        for e in es
                        if e.get("dispatched")
                    )
                ),
                "transport_statuses": dict(
                    Counter(e.get("transport", "unavailable") for e in es)
                ),
                "actual_microdollars": sum(e.get("actual_microdollars", 0) for e in es),
                "input_tokens": sum(e.get("input_tokens") or 0 for e in es),
                "output_tokens": sum(e.get("output_tokens") or 0 for e in es),
                "thinking_tokens": sum(e.get("thinking_tokens") or 0 for e in es),
                "mean_latency_seconds": statistics.mean(lat) if lat else None,
                "maximum_latency_seconds": max(lat) if lat else None,
                "maximum_observed_input_tokens": max(
                    (e.get("input_tokens") or 0 for e in es), default=0
                ),
                "maximum_observed_output_tokens": max(
                    (e.get("output_tokens") or 0 for e in es), default=0
                ),
                "worlds_solved_all_repeats": sum(
                    all(e.get("supported", False) for e in values)
                    for values in byworld.values()
                ),
                "worlds_failed_all_repeats": sum(
                    all(not e.get("supported", False) for e in values)
                    for values in byworld.values()
                ),
                "worlds_mixed": sum(
                    any(e.get("supported", False) for e in values)
                    and not all(e.get("supported", False) for e in values)
                    for values in byworld.values()
                ),
            }
        )
if used_replacements != set(replacements):
    raise ValueError("Continuation refers to unknown original assignments")
if len(episodes) != summary["total_request_count"] or len(
    {e["request_id"] for e in episodes}
) != len(episodes):
    raise ValueError("Original assignment coverage differs")
contrasts = []
pairs = [
    ("equality_tree-32", "branching-32"),
    ("relational-random-false-2", "relational-targeted-false-2"),
    ("near-decoys-0-noise-0", "near-decoys-12-noise-0"),
]
for left, right in pairs:
    for model in sorted(set(m["model"] for m in metrics)):
        if (left, model) not in world_values or (right, model) not in world_values:
            continue
        a, b = world_values[left, model], world_values[right, model]
        assert set(a) == set(b)
        differences = [b[w] - a[w] for w in sorted(a)]
        rng = random.Random(107)
        boot = sorted(
            statistics.mean(rng.choice(differences) for _ in differences)
            for _ in range(5000)
        )
        contrasts.append(
            {
                "model": model,
                "reference": left,
                "comparison": right,
                "paired_worlds": len(a),
                "mean_supported_accuracy_difference": statistics.mean(differences),
                "paired_world_bootstrap_95_interval": [boot[124], boot[4874]],
                "scope": "descriptive exploratory paired-world bootstrap; no multiplicity adjustment or significance claim",
            }
        )
account = {
    "settled_microdollars": sum(
        s["accounting"]["settled_microdollars"] for s in sources
    ),
    "held_microdollars": sum(s["accounting"]["held_microdollars"] for s in sources),
    "unknown_receipts": sum(s["accounting"]["unknown_receipts"] for s in sources),
    "assigned_requests": summary["total_request_count"],
    "dispatched_requests": sum(e.get("dispatched", False) for e in episodes),
    "settled_requests": sum(e.get("usage_known", False) for e in episodes),
    "not_attempted_requests": sum(not e.get("dispatched", False) for e in episodes),
    "assignment_records": len(episodes),
    "missing_original_result_jobs": base["missing_jobs"],
}
report = {
    "schema_version": "clue-hardness-measured-results-1",
    "measured_date": args.measured_date,
    "plans_id": summary["plans_id"],
    "suite_id": summary["suite_id"],
    "complete": all(e.get("dispatched", False) for e in episodes),
    "all_receipts_settled": all(e.get("usage_known", False) for e in episodes),
    "continuation_ids": continuation_ids,
    "all_assigned_failures_retained": True,
    "distinct_underlying_worlds": len({e["world_id"] for e in episodes}),
    "models": json.loads((PLANS / (summary["jobs"][0]["name"] + ".json")).read_text())[
        "models"
    ],
    "input_views": summary["input_views"],
    "repeats": summary["repeats"],
    "suite_ceiling_microdollars": summary["suite_ceiling_microdollars"],
    "conservative_maximum_microdollars": summary["maximum_microdollars"],
    "accounting": account,
    "metrics": metrics,
    "metric_definitions": {
        "protocol_failures": "Known-usage responses with an invalid protocol flag.",
        "provider_failures": "Dispatched requests without a known usage receipt; inspect transport status.",
        "execution_failures": "Dispatched requests with no valid protocol response, including provider failures.",
        "clustered_metrics": "Original harness summary; its raw protocol-failure count also includes missing responses.",
        "complete": "All original assignments dispatched; does not imply every receipt settled.",
    },
    "contrasts": contrasts,
    "source_receipts": sources,
    "clustered_metrics": [
        {
            "job": job["name"],
            "metrics": summarize([e for e in episodes if e["job"] == job["name"]]),
        }
        for job in summary["jobs"]
    ],
    "limits": [
        "Small cohorts; repetitions are clustered by world.",
        "Finite model-specific output caps including thinking; record cap/protocol failures separately.",
        "Model aliases were used; returned model identities are preserved per assignment.",
        "No adaptive model-guided case selection; exploratory development and test results should be separated.",
        "This comparison does not establish performance of other frontier models.",
    ],
}
report["report_id"] = digest(report)
atomic_json(args.output, report)
args.episodes.parent.mkdir(parents=True, exist_ok=True)
with args.episodes.open("w") as f:
    for e in episodes:
        f.write(json.dumps(e, separators=(",", ":"), sort_keys=True) + "\n")
print(
    json.dumps(
        {
            "complete": report["complete"],
            "accounting": account,
            "output": str(args.output),
            "episodes": str(args.episodes),
        },
        indent=2,
    )
)
