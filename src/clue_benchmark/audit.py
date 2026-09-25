"""Bounded, private structural diagnostics; none of these labels imply model difficulty."""

import random
from collections import Counter, defaultdict
from dataclasses import replace

from .config import Config
from .dataset import exact_isomorphic, fingerprints
from .environment import Environment
from .solver import Outcome, Solver, Unresolved

CROSS_TYPES = {"indirect_positive", "indirect_negative"}
DIRECT_TYPES = {"unary_positive", "unary_negative", "crime_positive", "crime_negative"}


def audit_case(case, max_solver_calls=1200, trajectory=False):
    """Return measured logical properties, or explicit incompleteness on solver limits."""
    cfg = replace(
        Config(**case["config"]),
        generation_seconds=60.0,
        max_solver_calls=max_solver_calls,
    )
    solver = Solver(case["suspects"], case["domains"], cfg)
    clues = case["clues"]
    env = Environment(case)
    capacities = [q["remaining"] for q in env.observation()["queries"]]
    result = {
        "case_id": case["case_id"],
        "world_group": case.get("world_group", case["case_id"]),
        "suspects": len(case["suspects"]),
        "clues": len(clues),
        "clue_types": dict(Counter(c["type"] for c in clues)),
        "topics": len(capacities),
        "singleton_topic_fraction": sum(n == 1 for n in capacities) / len(capacities),
        "maximum_topic_capacity": max(capacities),
        "complete": False,
    }
    try:
        if solver.check(clues).status != Outcome.UNIQUE:
            raise ValueError("audit requires a unique complete puzzle")
        essential = [
            i
            for i in range(len(clues))
            if solver.check(clues[:i] + clues[i + 1 :]).status != Outcome.UNIQUE
        ]
        result["essential_clues"] = len(essential)
        result["essential_cross_attribute"] = sum(
            clues[i]["type"] in CROSS_TYPES for i in essential
        )
        result["essential_suspect_comparison"] = sum(
            clues[i]["type"].startswith("suspect_") for i in essential
        )
        direct = [c for c in clues if c["type"] in DIRECT_TYPES]
        result["direct_only_unique"] = solver.check(direct).status == Outcome.UNIQUE
        no_exoneration = [c for c in clues if c["type"] != "crime_different_from"]
        result["without_named_exonerations_unique"] = (
            solver.check(no_exoneration).status == Outcome.UNIQUE
        )
        core = list(clues)
        for clue in clues:
            reduced = [c for c in core if c is not clue]
            if solver.check(reduced).status == Outcome.UNIQUE:
                core = reduced
        result["greedy_irreducible_core_size"] = len(core)
        if trajectory:
            result["candidate_trajectory"] = [
                len(solver.feasible_candidates(clues[:i]))
                for i in range(len(clues) + 1)
            ]
        result["complete"] = True
    except Unresolved as exc:
        result["incomplete_reason"] = str(exc)
    result["solver_calls"] = solver.calls
    return result


def audit_suite(cases, max_solver_calls=1200, trajectory=False):
    rows = [audit_case(c, max_solver_calls, trajectory) for c in cases]
    groups = defaultdict(list)
    for row in rows:
        groups[row["suspects"]].append(row)
    summary = []
    for n, group in sorted(groups.items()):
        complete = [x for x in group if x["complete"]]
        summary.append(
            {
                "suspects": n,
                "cases": len(group),
                "audited": len(complete),
                "inconclusive": len(group) - len(complete),
                "direct_only_unique_fraction": (
                    sum(x["direct_only_unique"] for x in complete) / len(complete)
                    if complete
                    else None
                ),
                "essential_cross_attribute_fraction": (
                    sum(x["essential_cross_attribute"] > 0 for x in complete)
                    / len(complete)
                    if complete
                    else None
                ),
                "mean_irreducible_core_size": (
                    sum(x["greedy_irreducible_core_size"] for x in complete)
                    / len(complete)
                    if complete
                    else None
                ),
                "mean_singleton_topic_fraction": (
                    sum(x["singleton_topic_fraction"] for x in group) / len(group)
                ),
            }
        )
    return {"rows": rows, "summary": summary}


def human_review_packet(cases, per_cell=2, seed=0):
    """Create public-only examples with explicit wording and query review questions."""
    rng = random.Random(seed)
    groups = defaultdict(list)
    for case in cases:
        groups[case.get("cell", f"n{len(case['suspects'])}")].append(case)
    packet = []
    for cell, members in sorted(groups.items()):
        for case in rng.sample(members, min(per_cell, len(members))):
            env = Environment(case)
            packet.append(
                {
                    "cell": cell,
                    "case_id": case["case_id"],
                    "deduction": env._public,
                    "investigation_topics": env.observation()["queries"],
                    "review_questions": [
                        "Does every clue have one unambiguous reading under the rules?",
                        "Would each topic label lead you to expect the kinds of clues it contains?",
                        "Are any clues redundant in wording or misleading despite being logically correct?",
                    ],
                    "reviewer_signoff": None,
                }
            )
    return packet


def duplicate_report(cases, max_near_pairs=50):
    """Exact isomorphism for WL matches, plus candidates for manual near-duplicate review."""
    by_hash = defaultdict(list)
    by_shape = defaultdict(list)
    for case in cases:
        _, puzzle_hash = fingerprints(case)
        by_hash[puzzle_hash].append(case)
        shape = (len(case["suspects"]), len(case["domains"]), len(case["clues"]))
        by_shape[shape].append(case)
    exact = []
    inconclusive = []
    for members in by_hash.values():
        for i, left in enumerate(members):
            for right in members[i + 1 :]:
                same = exact_isomorphic(left, right)
                item = [left["case_id"], right["case_id"]]
                if same is True:
                    exact.append(item)
                elif same is None:
                    inconclusive.append(item)
    near = []
    for members in by_shape.values():
        vectors = []
        for case in members:
            features = Counter(
                (
                    c["type"],
                    c.get("attribute"),
                    tuple(sorted((c["attr1"], c["attr2"]))) if "attr1" in c else None,
                )
                for c in case["clues"]
            )
            vectors.append(features)
        for i, left in enumerate(members):
            for j in range(i + 1, len(members)):
                if len(near) >= max_near_pairs:
                    break
                right = members[j]
                if left.get("world_group") is not None and left.get(
                    "world_group"
                ) == right.get("world_group"):
                    continue  # paired variants are intentionally related
                keys = vectors[i].keys() | vectors[j].keys()
                shared = sum(min(vectors[i][k], vectors[j][k]) for k in keys)
                union = sum(max(vectors[i][k], vectors[j][k]) for k in keys)
                similarity = shared / union if union else 1.0
                if similarity >= 0.85:
                    near.append(
                        {
                            "cases": [left["case_id"], right["case_id"]],
                            "feature_similarity": similarity,
                        }
                    )
            if len(near) >= max_near_pairs:
                break
    return {
        "cases": len(cases),
        "exact_isomorphic_pairs": exact,
        "isomorphism_inconclusive_pairs": inconclusive,
        "near_structure_review_candidates": near,
        "near_metric": "multiset Jaccard over clue type and attribute; not semantic equivalence",
    }
