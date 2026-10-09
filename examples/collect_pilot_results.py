"""Offline collection across frozen pilots; dispatched failures are immutable.

Continuation plans must explicitly map each new request to an untouched original
assignment. This tool reads saved receipts only and cannot contact providers.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from clue_benchmark.community_bundle import file_hash
from clue_benchmark.config import digest
from clue_benchmark.dataset import atomic_json

IDENTITY = ("case_id", "world_id", "model", "condition", "agent", "repeat")


def read(path):
    return json.loads(Path(path).read_text())


def inputs(root):
    root = Path(root)
    plan = read(root / "pilot-plan.json")
    if digest({k: v for k, v in plan.items() if k != "pilot_id"}) != plan["pilot_id"]:
        raise ValueError("pilot digest differs")
    assignments, episodes, receipts = {}, {}, {}
    for job in plan["jobs"]:
        dry = read(root / "preflight" / f"{job['job']}.json")
        if len(dry["requests"]) != job["requests"]:
            raise ValueError("assignment count differs")
        for request in dry["requests"]:
            ident = request["request_id"]
            if ident in assignments:
                raise ValueError("duplicate assignment")
            assignments[ident] = {**request, "job": job["job"]}
        path = root / "evaluation" / job["job"] / "results.json"
        if not path.exists():
            continue
        report = read(path)
        if report["plan_id"] != job["plan_id"]:
            raise ValueError("receipt plan differs")
        receipts[str(path)] = file_hash(path)
        for episode in report["episodes"]:
            ident = episode["request_id"]
            assignment = assignments.get(ident)
            if (
                ident in episodes
                or assignment is None
                or assignment["job"] != job["job"]
                or any(episode.get(k) != assignment.get(k) for k in IDENTITY)
            ):
                raise ValueError("receipt assignment differs")
            episodes[ident] = episode
    if len(assignments) != plan["max_requests"]:
        raise ValueError("pilot assignment count differs")
    return plan, assignments, episodes, receipts


def collect(original, continuations=()):
    plan, assignments, episodes, receipts = inputs(original)
    mapped = set()
    continuation_ids = []
    for root in continuations:
        follow, new_assignments, new_episodes, new_receipts = inputs(root)
        if follow.get("continuation_of") != plan["pilot_id"]:
            raise ValueError("continuation parent differs")
        continuation_ids.append(follow["pilot_id"])
        seen = set()
        for mapping in follow["assignment_map"]:
            old, new = (
                mapping["original_request_id"],
                mapping["continuation_request_id"],
            )
            if old in mapped or new in seen:
                raise ValueError("duplicate continuation mapping")
            if old not in assignments or new not in new_assignments:
                raise ValueError("unknown continuation assignment")
            if episodes.get(old, {}).get("dispatched"):
                raise ValueError(
                    "cannot replace a dispatched request, including failure"
                )
            before, after = assignments[old], new_assignments[new]
            if (
                before["job"] != mapping["original_job"]
                or after["job"] != mapping["continuation_job"]
                or any(before.get(k) != after.get(k) for k in IDENTITY)
                or before["maximum_microdollars"] != after["maximum_microdollars"]
                or before["input_token_upper_bound"] != after["input_token_upper_bound"]
            ):
                raise ValueError("continuation changes original assignment")
            mapped.add(old)
            seen.add(new)
            episode = new_episodes.get(new)
            if episode and episode.get("dispatched"):
                episodes[old] = {
                    **episode,
                    "request_id": old,
                    "execution_request_id": new,
                    "execution_pilot_id": follow["pilot_id"],
                }
        if seen != set(new_assignments):
            raise ValueError("continuation mapping is incomplete")
        receipts.update(new_receipts)

    groups = defaultdict(list)
    for ident, assignment in assignments.items():
        groups[assignment["job"], assignment["model"], assignment["condition"]].append(
            (assignment, episodes.get(ident, {}))
        )
    metrics = []
    for (job, model, condition), rows in sorted(groups.items()):
        sent = [e for _, e in rows if e.get("dispatched")]
        settled = [e for e in sent if e.get("usage_known")]
        correct = sum(bool(e.get("correct")) for e in sent)
        metrics.append(
            {
                "job": job,
                "model": model,
                "condition": condition,
                "worlds": len({a["world_id"] for a, _ in rows}),
                "assigned": len(rows),
                "dispatched": len(sent),
                "settled": len(settled),
                "not_attempted": len(rows) - len(sent),
                "correct": correct,
                "supported_correct": sum(bool(e.get("supported")) for e in sent),
                "assigned_correctness": correct / len(rows),
                "settled_correctness": (
                    sum(bool(e.get("correct")) for e in settled) / len(settled)
                    if settled
                    else None
                ),
                "settled_incorrect": sum(
                    e.get("protocol_valid")
                    and not e.get("correct")
                    and not e.get("abstained")
                    for e in settled
                ),
                "settled_abstentions": sum(bool(e.get("abstained")) for e in settled),
                "dispatched_protocol_failures": sum(
                    not e.get("protocol_valid") for e in sent
                ),
                "unknown_usage": sum(not e.get("usage_known") for e in sent),
                "settled_microdollars": sum(e["actual_microdollars"] for e in settled),
                "unknown_usage_reserved_microdollars": sum(
                    e["maximum_microdollars"] for e in sent if not e.get("usage_known")
                ),
                "input_tokens": sum(e.get("input_tokens") or 0 for e in settled),
                "output_tokens": sum(e.get("output_tokens") or 0 for e in settled),
            }
        )
    return {
        "schema_version": "clue-pilot-collected-1",
        "status": "all_assignments_dispatched"
        if all(r["not_attempted"] == 0 for r in metrics)
        else "partial",
        "pilot_id": plan["pilot_id"],
        "suite_id": plan["suite_id"],
        "continuation_ids": continuation_ids,
        "models": plan["models"],
        "assigned": len(assignments),
        "dispatched": sum(r["dispatched"] for r in metrics),
        "settled": sum(r["settled"] for r in metrics),
        "not_attempted": sum(r["not_attempted"] for r in metrics),
        "settled_microdollars": sum(r["settled_microdollars"] for r in metrics),
        "unknown_usage_reserved_microdollars": sum(
            r["unknown_usage_reserved_microdollars"] for r in metrics
        ),
        "metrics": metrics,
        "source_receipt_hashes": receipts,
        "interpretation": (
            "Assigned correctness retains dispatched failures and pending assignments "
            "in the denominator. Pending assignments are not observed model errors. "
            "Settled correctness is descriptive and can be biased by partial coverage. "
            "Provider errors are separate from incorrect answers. "
            "Worlds, rather than variants or agent calls, are the sampling units."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--continuation", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = collect(args.original, args.continuation)
    atomic_json(args.output, report)
    print(json.dumps({k: report[k] for k in ("status", "assigned", "settled")}))


if __name__ == "__main__":
    main()
