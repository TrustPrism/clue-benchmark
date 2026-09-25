"""Free, seeded baselines and world-clustered confidence intervals."""

import math
import platform
import random
import time
from collections import defaultdict
from dataclasses import replace

from .config import VERSION, Config
from .environment import PROTOCOL_VERSION, Environment
from .solver import Outcome, Solver, Unresolved


def _solver(case):
    config = replace(
        Config(**case["config"]), generation_seconds=60, max_solver_calls=50000
    )
    return Solver(case["suspects"], case["domains"], config)


def _answer(case, indices, rng):
    # Reference baselines have structured versions of revealed facts, never hidden facts.
    try:
        solver = _solver(case)
        revealed = [case["clues"][i] for i in indices]
        check = solver.check(revealed)
        if check.status == Outcome.UNIQUE:
            return check.murderer, None
        candidates = solver.feasible_candidates(revealed)
    except Unresolved:
        return None, "inconclusive"
    return (rng.choice(candidates) if candidates else None), None


def run_episode(case, baseline="reference", fraction=1.0, seed=0):
    rng = random.Random(seed)
    start = time.perf_counter()
    error = None
    latencies = []
    if baseline in ("random_answer", "reference"):
        if baseline == "random_answer":
            answer = rng.choice(case["suspects"])
        else:
            answer, error = _answer(case, list(range(len(case["clues"]))), rng)
        return {
            "correct": int(answer == case["solution"]["murderer"]),
            "spent": len(case["clues"]),
            "requests": 0,
            "invalid_actions": 0,
            "seconds": time.perf_counter() - start,
            "query_ms": [],
            "solver_error": error,
        }
    if baseline not in (
        "random_investigation",
        "round_robin",
        "topic_heuristic",
        "privileged_lookahead",
    ):
        raise ValueError("unknown baseline")
    env = Environment(case, fraction)
    cursor = 0
    while env.spent < env.budget:
        obs = env.observation()
        indices = [int(c["clue_id"][1:]) - 1 for c in obs["clues"]]
        candidates = _solver(case)
        try:
            check = candidates.check([case["clues"][i] for i in indices])
            if check.status == Outcome.UNIQUE:
                env.submit_answer(check.murderer)
                break
        except Unresolved:
            error = "inconclusive"
            break
        active = [q["query_id"] for q in obs["queries"] if q["remaining"]]
        if not active:
            break
        if baseline == "random_investigation":
            query = rng.choice(active)
        elif baseline == "round_robin":
            ids = [q["query_id"] for q in obs["queries"]]
            for _ in ids:
                query = ids[cursor % len(ids)]
                cursor += 1
                if query in active:
                    break
        elif baseline == "topic_heuristic":
            # Uses only public topic metadata and the currently feasible suspects.
            try:
                plausible = set(
                    candidates.feasible_candidates([case["clues"][i] for i in indices])
                )
            except Unresolved:
                plausible = set(case["suspects"])

            def priority(q):
                category = q["category"]
                if category == "suspect_attribute":
                    return (3 if q["suspect"] in plausible else 0, q["remaining"])
                return (
                    {
                        "crime_attribute": 4,
                        "crime_comparison": 2,
                        "suspect_comparison": 1,
                        "cross_attribute": 1,
                    }[category],
                    q["remaining"],
                )

            query = max((q for q in obs["queries"] if q["remaining"]), key=priority)[
                "query_id"
            ]
        else:
            # Privileged diagnostic: inspect the next hidden clue in every queue.
            # This is an upper-bound policy and is never an agent baseline.
            scored = []
            for q in active:
                next_index = env._remaining[q][0]
                try:
                    remaining = len(
                        candidates.feasible_candidates(
                            [case["clues"][i] for i in indices + [next_index]]
                        )
                    )
                except Unresolved:
                    remaining = len(case["suspects"])
                scored.append((remaining, q))
            query = min(scored)[1]
        t = time.perf_counter()
        env.request_clue(query)
        latencies.append((time.perf_counter() - t) * 1000)
    if not env.done:
        indices = [int(c["clue_id"][1:]) - 1 for c in env.observation()["clues"]]
        answer, answer_error = _answer(case, indices, rng)
        error = error or answer_error
        env.submit_answer(answer)
    return {
        **env.score(),
        "seconds": time.perf_counter() - start,
        "query_ms": latencies,
        "solver_error": error,
    }


def summarize(rows, bootstrap=1000):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["baseline"], row["suspects"], row["budget_fraction"])].append(row)
    results = []
    for key, group in sorted(groups.items()):
        clusters = defaultdict(list)
        for row in group:
            clusters[row["world_group"]].append(row["correct"])
        values = [sum(x) / len(x) for x in clusters.values()]
        rng = random.Random(0)
        samples = sorted(
            sum(rng.choices(values, k=len(values))) / len(values)
            for _ in range(bootstrap)
        )
        latencies = sorted(x for row in group for x in row["query_ms"])
        results.append(
            dict(
                baseline=key[0],
                suspects=key[1],
                budget_fraction=key[2],
                episodes=len(group),
                worlds=len(values),
                accuracy=sum(values) / len(values),
                ci95=[
                    samples[int(0.025 * bootstrap)],
                    samples[min(bootstrap - 1, int(0.975 * bootstrap))],
                ],
                mean_clues=sum(x["spent"] for x in group) / len(group),
                mean_requests=sum(x["requests"] for x in group) / len(group),
                invalid_actions=sum(x["invalid_actions"] for x in group),
                mean_seconds=sum(x["seconds"] for x in group) / len(group),
                query_p95_ms=latencies[math.ceil(0.95 * len(latencies)) - 1]
                if latencies
                else None,
                solver_errors=sum(x["solver_error"] is not None for x in group),
                tokens=None,
            )
        )
    return results


def budget_averages(summary):
    """Average investigation accuracy across the four declared evidence budgets."""
    groups = defaultdict(dict)
    for row in summary:
        groups[(row["baseline"], row["suspects"])][row["budget_fraction"]] = row[
            "accuracy"
        ]
    fractions = (0.25, 0.5, 0.75, 1.0)
    return [
        {
            "baseline": baseline,
            "suspects": suspects,
            "budget_averaged_accuracy": sum(values[f] for f in fractions) / 4,
        }
        for (baseline, suspects), values in sorted(groups.items())
        if all(f in values for f in fractions)
    ]


def evaluate(cases, repeats=1, include_privileged=False):
    if repeats < 1:
        raise ValueError("repeats must be positive")
    rows = []
    for case in cases:
        baselines = [
            "random_answer",
            "reference",
            "random_investigation",
            "round_robin",
            "topic_heuristic",
        ]
        if include_privileged:
            baselines.append("privileged_lookahead")
        for baseline in baselines:
            fractions = (
                (1.0,)
                if baseline in ("random_answer", "reference")
                else (0.25, 0.5, 0.75, 1.0)
            )
            for fraction in fractions:
                for repeat in range(repeats):
                    seed = int(case["case_id"][:12], 16) + repeat
                    rows.append(
                        {
                            "case_id": case["case_id"],
                            "world_group": case.get("world_group", case["case_id"]),
                            "baseline": baseline,
                            "suspects": len(case["suspects"]),
                            "budget_fraction": fraction,
                            "repeat": repeat,
                            **run_episode(case, baseline, fraction, seed),
                        }
                    )
    summary = summarize(rows)
    return {
        "manifest": {
            "version": VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "model": "none; deterministic symbolic baselines",
            "paid_calls": 0,
            "repeats": repeats,
            "reference_access": "structured revealed clues; no hidden-world access for inference",
            "privileged_diagnostic_included": include_privileged,
        },
        "summary": summary,
        "budget_averages": budget_averages(summary),
        "episodes": rows,
    }
