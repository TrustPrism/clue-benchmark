"""Post-hoc evaluator-only diagnostics; no generation or model observations."""

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from clue_benchmark.config import Config, digest
from clue_benchmark.dataset import atomic_json, read_cases
from clue_benchmark.investigation import clustered_interval
from clue_benchmark.solver import Solver, Unresolved


def revealed_ids(log, allowed):
    prompt = log["transcript"][0]["text"]
    observation = json.loads(prompt.split("\n", 1)[1])
    found = {c["clue_id"] for c in observation["clues"]}
    for turn in log["transcript"]:
        if turn.get("role") == "tool" and turn.get("name") == "request_clue":
            clue = turn.get("result", {}).get("clue")
            if clue is not None:
                found.add(clue["clue_id"])
    if found - set(allowed):
        raise ValueError("native transcript contains an undeclared clue")
    return sorted(found)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plan")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root)
    plan = json.loads(Path(args.plan).read_text())
    output = root / plan["execution_directory"]
    result = json.loads((output / "results.json").read_text())
    if result["manifest"]["plan_id"] != plan["plan_id"]:
        raise ValueError("results are bound to another manifest")
    cases = {
        c["case_id"]: c for c in read_cases(root / plan["datasets"]["dev"]["path"])
    }
    cache_path = output / "evidence-feasibility-cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    rows = []
    for source in result["episodes"]:
        if source["error"] in ("missing_episode", "interrupted_episode", "in_progress"):
            continue
        row = {
            k: source[k]
            for k in (
                "episode_id",
                "case_id",
                "world_group",
                "model",
                "suspects",
                "track",
                "selection_policy",
                "budget_fraction",
                "answer",
                "correct",
                "completion",
                "error",
            )
        }
        row["analysis_cohort"] = source.get("analysis_cohort", "initial_pilot")
        row["diagnostic_error"] = None
        path = output / "logs" / (source["episode_id"] + ".json")
        if not path.exists():
            row["diagnostic_error"] = "missing_native_log"
            rows.append(row)
            continue
        case = cases[source["case_id"]]
        lookup = {f"c{i + 1:03d}": c for i, c in enumerate(case["clues"])}
        ids = revealed_ids(json.loads(path.read_text()), lookup)
        key = digest([case["case_id"], ids])
        if key not in cache:
            cfg = replace(
                Config(**case["config"]), generation_seconds=10.0, max_solver_calls=100
            )
            solver = Solver(case["suspects"], case["domains"], cfg)
            try:
                feasible = solver.feasible_candidates([lookup[c] for c in ids])
                if case["solution"]["murderer"] not in feasible:
                    raise ValueError("revealed evidence excludes the true murderer")
                cache[key] = feasible
            except Unresolved:
                row["diagnostic_error"] = "inconclusive_solver"
                rows.append(row)
                continue
        feasible = cache[key]
        row.update(
            revealed_clue_ids=ids,
            revealed_clues=len(ids),
            feasible_candidates=len(feasible),
            identifying_evidence=len(feasible) == 1,
            submitted_answer_consistent=(source["answer"] in feasible)
            if source["answer"] is not None
            else None,
        )
        rows.append(row)
    groups = defaultdict(list)
    for row in rows:
        groups[
            row["analysis_cohort"],
            row["model"],
            row["suspects"],
            row["track"],
            row["selection_policy"],
            row["budget_fraction"],
        ].append(row)
    summary = []
    for key, members in sorted(groups.items()):
        available = [r for r in members if r["diagnostic_error"] is None]
        answers = [r for r in available if r["answer"] is not None]
        identifiable = [r for r in available if r["identifying_evidence"]]
        worlds = defaultdict(list)
        for row in available:
            worlds[row["world_group"]].append(int(row["identifying_evidence"]))
        values = [sum(v) / len(v) for v in worlds.values()]
        summary.append(
            dict(
                zip(
                    (
                        "analysis_cohort",
                        "model",
                        "suspects",
                        "track",
                        "selection_policy",
                        "budget_fraction",
                    ),
                    key,
                )
            )
            | {
                "dispatched_episodes": len(members),
                "resolved_diagnostics": len(available),
                "unknown_diagnostics": len(members) - len(available),
                "identifying_evidence_rate": sum(
                    r["identifying_evidence"] for r in available
                )
                / len(available)
                if available
                else None,
                "worlds": len(worlds),
                "identifying_evidence_world_cluster_ci95": clustered_interval(values)
                if values
                else None,
                "mean_feasible_candidates": sum(
                    r["feasible_candidates"] for r in available
                )
                / len(available)
                if available
                else None,
                "submitted_answers": len(answers),
                "inconsistent_submitted_answers": sum(
                    not r["submitted_answer_consistent"] for r in answers
                ),
                "identifiable_episodes": len(identifiable),
                "correct_when_identifiable": sum(r["correct"] for r in identifiable),
                "mean_revealed_clues": sum(r["revealed_clues"] for r in available)
                / len(available)
                if available
                else None,
            }
        )
    atomic_json(cache_path, cache)
    atomic_json(
        output / "evidence-diagnostics.json",
        {
            "plan_id": plan["plan_id"],
            "results_sha256": hashlib.sha256(
                (output / "results.json").read_bytes()
            ).hexdigest(),
            "analysis": "Post-hoc exploratory evaluator-only analysis; not a pre-registered primary result",
            "method": "Exact CP-SAT feasibility using only clues actually present in native observations; no hidden world attributes provided to the solver or models",
            "limitations": "Diagnosed dispatched episodes only; truncated evidence, early submission, and token stops affect identifiability. Random controls still differ in interaction overhead. Conditional correctness is subject to selection. Inconclusive solver results are unknown, never proofs.",
            "rows": rows,
            "summary": summary,
            "generation_calls": 0,
        },
    )
    print(
        json.dumps(
            {
                "diagnosed_episodes": len(rows),
                "cached_evidence_sets": len(cache),
                "unknown": sum(r["diagnostic_error"] is not None for r in rows),
                "generation_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
