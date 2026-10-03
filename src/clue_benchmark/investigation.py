"""Paired menu/policy diagnostics, with privileged next-clue effects kept separate."""

import random
from collections import defaultdict

from .config import DATA_VERSION, VERSION, digest
from .environment import Environment, protocol_version
from .evaluation import _solver, run_episode, summarize
from .solver import Unresolved
from .study import BUDGETS


def clustered_interval(values, resamples=2000):
    rng = random.Random(0)
    draws = sorted(
        sum(rng.choices(values, k=len(values))) / len(values) for _ in range(resamples)
    )
    return [
        draws[int(0.025 * resamples)],
        draws[min(resamples - 1, int(0.975 * resamples))],
    ]


def menu_prior_candidates(observation, strategy="fewest"):
    """A shortcut probe using only public topic labels and capacities, without clues."""
    if strategy not in ("fewest", "most"):
        raise ValueError("unknown menu prior strategy")
    counts = {s: 0 for s in observation["suspects"]}
    for query in observation["queries"]:
        if query["suspect"] is not None:
            counts[query["suspect"]] += query["remaining"]
    target = (min if strategy == "fewest" else max)(counts.values())
    return [suspect for suspect, count in counts.items() if count == target]


def menu_prior_diagnostic(cases):
    rows = []
    for mode in ("targeted", "attribute"):
        for strategy in ("fewest", "most"):
            groups = defaultdict(lambda: defaultdict(list))
            for case in cases:
                candidates = menu_prior_candidates(
                    Environment(case, topic_mode=mode).observation(), strategy
                )
                expected = (
                    1 / len(candidates)
                    if case["solution"]["murderer"] in candidates
                    else 0
                )
                groups[len(case["suspects"])][case["world_group"]].append(expected)
            for size, worlds in sorted(groups.items()):
                values = [sum(v) / len(v) for v in worlds.values()]
                rows.append(
                    dict(
                        topic_mode=mode,
                        strategy=strategy,
                        suspects=size,
                        worlds=len(values),
                        expected_accuracy=sum(values) / len(values),
                        chance=1 / size,
                        world_cluster_ci95=clustered_interval(values),
                    )
                )
    return {
        "method": "Guess among suspects with fewest/most publicly named unary evidence items; uniform tie expectation computed analytically. No clue content or hidden world used to select suspects.",
        "interpretation": "Measures answer-correlated catalogue metadata from generator sampling; it is a shortcut diagnostic, not logical evidence or a model result.",
        "rows": rows,
    }


def paired_policy_gaps(rows):
    lookup = {
        (
            r["case_id"],
            r["repeat"],
            r["topic_mode"],
            r["baseline"],
            r["budget_fraction"],
        ): r
        for r in rows
    }
    groups = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row["baseline"] != "topic_heuristic":
            continue
        for comparison in ("random_investigation", "random_clue", "round_robin"):
            other = lookup[
                row["case_id"],
                row["repeat"],
                row["topic_mode"],
                comparison,
                row["budget_fraction"],
            ]
            key = (
                row["suspects"],
                row["topic_mode"],
                comparison,
                row["budget_fraction"],
            )
            groups[key][row["world_group"]].append(row["correct"] - other["correct"])
    result = []
    for (n, mode, comparison, budget), worlds in sorted(groups.items()):
        values = [sum(v) / len(v) for v in worlds.values()]
        result.append(
            dict(
                suspects=n,
                topic_mode=mode,
                comparison=comparison,
                budget_fraction=budget,
                worlds=len(values),
                heuristic_minus_comparison=sum(values) / len(values),
                world_cluster_ci95=clustered_interval(values),
            )
        )
    return result


def decision_opportunities(case, topic_mode="targeted"):
    """Oracle diagnostic on random prefixes; unequal one-step gains are not proof of an optimal policy."""
    env = Environment(case, topic_mode=topic_mode)
    solver = _solver(case)
    rng = random.Random(int(case["case_id"][:12], 16))
    checkpoints = {max(0, int(len(case["clues"]) * f)) for f in (0, 0.25, 0.5, 0.75)}
    rows = []
    while env.spent < env.budget:
        if env.spent in checkpoints:
            revealed = [case["clues"][i] for i in env._seen]
            row = {"spent": env.spent, "complete": False}
            try:
                before = len(solver.feasible_candidates(revealed))
                after = [
                    len(
                        solver.feasible_candidates(revealed + [case["clues"][items[0]]])
                    )
                    for items in env._remaining.values()
                    if items
                ]
                row.update(
                    candidates_before=before,
                    candidates_after_best=min(after),
                    candidates_after_worst=max(after),
                    active_topics=len(after),
                    unequal_next_clue_gains=min(after) != max(after),
                    complete=True,
                )
            except Unresolved as exc:
                row["error"] = str(exc)
            rows.append(row)
        env.request_clue(
            rng.choice([q for q, items in env._remaining.items() if items])
        )
    return {
        "case_id": case["case_id"],
        "world_group": case["world_group"],
        "suspects": len(case["suspects"]),
        "topic_mode": topic_mode,
        "rows": rows,
    }


def compare_investigation(
    cases, repeats=3, topic_modes=("targeted", "attribute"), diagnostic_per_size=3
):
    if type(repeats) is not int or repeats < 1 or not cases:
        raise ValueError("positive repeats and nonempty cases required")
    if len({c["case_id"] for c in cases}) != len(cases):
        raise ValueError("duplicate case IDs")
    if len(set(topic_modes)) != len(topic_modes) or not topic_modes:
        raise ValueError("distinct topic modes required")
    for mode in topic_modes:
        protocol_version(mode)
    rows, menus = [], []
    policies = ("random_investigation", "random_clue", "round_robin", "topic_heuristic")
    for case in cases:
        for mode in topic_modes:
            capacities = [
                q["remaining"]
                for q in Environment(case, topic_mode=mode).observation()["queries"]
            ]
            menus.append(
                dict(
                    case_id=case["case_id"],
                    suspects=len(case["suspects"]),
                    topic_mode=mode,
                    singleton_topic_fraction=sum(c == 1 for c in capacities)
                    / len(capacities),
                    topics=len(capacities),
                    maximum_capacity=max(capacities),
                )
            )
            for policy in policies:
                for budget in BUDGETS:
                    for repeat in range(repeats):
                        result = run_episode(
                            case,
                            policy,
                            budget,
                            int(case["case_id"][:12], 16) + repeat,
                            mode,
                        )
                        rows.append(
                            {
                                **result,
                                "case_id": case["case_id"],
                                "world_group": case["world_group"],
                                "suspects": len(case["suspects"]),
                                "topic_mode": mode,
                                "baseline": policy,
                                "budget_fraction": budget,
                                "repeat": repeat,
                                "correct": int(
                                    result["correct"] and result["solver_error"] is None
                                ),
                            }
                        )
    summaries = []
    for mode in topic_modes:
        summaries.extend(
            {**s, "topic_mode": mode}
            for s in summarize([r for r in rows if r["topic_mode"] == mode])
        )
    selected = defaultdict(list)
    for case in sorted(cases, key=lambda c: c["case_id"]):
        if len(selected[len(case["suspects"])]) < diagnostic_per_size:
            selected[len(case["suspects"])].append(case)
    opportunities = [
        decision_opportunities(c, mode)
        for group in selected.values()
        for c in group
        for mode in topic_modes
    ]
    return {
        "manifest": {
            "software_version": VERSION,
            "dataset_version": DATA_VERSION,
            "case_bank_hash": digest(cases),
            "cases": len(cases),
            "worlds": len({c["world_group"] for c in cases}),
            "repeats": repeats,
            "episodes": len(rows),
            "paid_calls": 0,
            "protocols": {m: protocol_version(m) for m in topic_modes},
            "analysis": "All budgets and policies declared together; exploratory development diagnostics.",
            "solver_limits": "60 seconds and 50000 calls per episode; 10 seconds/2 deterministic work units per solve.",
            "failure_policy": "Inconclusive episodes count incorrect and are reported; no exclusions.",
        },
        "summary": summaries,
        "paired_gaps": paired_policy_gaps(rows),
        "menus": menus,
        "menu_prior_diagnostic": menu_prior_diagnostic(cases),
        "privileged_decision_opportunities": opportunities,
        "diagnostic_limitations": "Uses hidden next clues to measure immediate candidate reduction. It is not an agent baseline, optimal strategy, or proof-depth metric; equal immediate gains can hide future differences.",
        "episodes": rows,
    }
