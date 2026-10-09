"""Corruption-aware integer and independently written one-hot encodings.

The encodings share CP-SAT, but no constraint builder. Direct enumeration is a
third, engine-independent reference for tiny worlds. Copies of a report are not
independent votes. Nuisance components have their own satisfiable namespaces.
"""

import time
from itertools import combinations, product
from math import prod

from ortools.sat.python import cp_model

from .config import digest
from .independent_oracle import holds, valid_world
from .logic import validate
from .solver import Unresolved


class Budget:
    def __init__(self, seconds=60, calls=20000):
        self.deadline = time.monotonic() + seconds
        self.max_calls = calls
        self.calls = 0
        self.solve_seconds = 0.0

    def check(self):
        if time.monotonic() >= self.deadline or self.calls >= self.max_calls:
            raise Unresolved("community certificate budget exhausted")

    def solve(self, model):
        self.check()
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = 0
        solver.parameters.max_time_in_seconds = max(
            0.000001, self.deadline - time.monotonic()
        )
        self.calls += 1
        started = time.monotonic()
        status = solver.solve(model)
        self.solve_seconds += time.monotonic() - started
        if status == cp_model.MODEL_INVALID:
            raise ValueError("invalid community model")
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.INFEASIBLE):
            raise Unresolved("community solver inconclusive")
        return status, solver


def core_reports(reports):
    unique = {}
    for r in reports:
        if r["report_id"] in unique and unique[r["report_id"]] != r:
            raise ValueError("conflicting copies of report")
        unique[r["report_id"]] = r
    return [r for r in unique.values() if r["constraint"]["type"] != "record_positive"]


def check_nuisance(reports):
    seen = set()
    report_ids = set()
    for r in reports:
        c = r["constraint"]
        if c["type"] != "record_positive":
            continue
        if r["report_id"] in report_ids:
            continue
        report_ids.add(r["report_id"])
        # One fresh variable per component: every subset is satisfiable, without
        # spending any corruption allowance or constraining a culprit variable.
        if (
            set(c) != {"type", "component", "variable", "value", "domain"}
            or c["component"] in seen
            or c["variable"] != "value"
            or c["domain"] != ["0", "1"]
            or c["value"] not in c["domain"]
        ):
            raise ValueError("nuisance component is not independent and satisfiable")
        seen.add(c["component"])


def _production(suspects, domains, reports, candidate, mode, allowance):
    model = cp_model.CpModel()
    xs = {
        (s, a): model.new_int_var(0, len(vs) - 1, f"{s}:{a}")
        for s in suspects
        for a, vs in domains.items()
    }
    if mode == "distinct":
        for a in domains:
            model.add_all_different([xs[s, a] for s in suspects])

    def eq(left, right):
        bit = model.new_bool_var("equality")
        model.add(left == right).only_enforce_if(bit)
        model.add(left != right).only_enforce_if(bit.Not())
        return bit

    truth_bits = []
    for r in reports:
        c = validate(r["constraint"], suspects, domains)
        t = c["type"]
        if t in (
            "unary_positive",
            "unary_negative",
            "crime_positive",
            "crime_negative",
        ):
            owner = c["suspect"] if t.startswith("unary") else candidate
            bit = eq(
                xs[owner, c["attribute"]], domains[c["attribute"]].index(c["value"])
            )
            truth_bits.append(bit if t.endswith("positive") else bit.Not())
        elif t in (
            "crime_same_as",
            "crime_different_from",
            "suspect_same_as",
            "suspect_different_from",
        ):
            left = candidate if t.startswith("crime") else c["other_suspect"]
            bit = eq(xs[left, c["attribute"]], xs[c["suspect"], c["attribute"]])
            truth_bits.append(bit if t.endswith("same_as") else bit.Not())
        else:
            pairs = []
            for s in suspects:
                p = eq(xs[s, c["attr1"]], domains[c["attr1"]].index(c["val1"]))
                q = eq(xs[s, c["attr2"]], domains[c["attr2"]].index(c["val2"]))
                both = model.new_bool_var("pair")
                model.add(both <= p)
                model.add(both <= q)
                model.add(both >= p + q - 1)
                pairs.append(both)
            exists = model.new_bool_var("exists")
            model.add(sum(pairs) >= 1).only_enforce_if(exists)
            model.add(sum(pairs) == 0).only_enforce_if(exists.Not())
            truth_bits.append(exists if t == "indirect_positive" else exists.Not())
    model.add(sum(1 - bit for bit in truth_bits) <= allowance)
    return model, xs


def _independent(suspects, domains, reports, candidate, mode, allowance):
    model = cp_model.CpModel()
    cells = {
        (s, a, v): model.new_bool_var(f"cell:{s}:{a}:{v}")
        for s in suspects
        for a, vs in domains.items()
        for v in vs
    }
    for s in suspects:
        for a, vs in domains.items():
            model.add_exactly_one(cells[s, a, v] for v in vs)
    if mode == "distinct":
        for a, vs in domains.items():
            for v in vs:
                model.add(sum(cells[s, a, v] for s in suspects) <= 1)
    violations = []
    for report in reports:
        c = report["constraint"]
        t = c["type"]
        if t.startswith("unary_") or t in ("crime_positive", "crime_negative"):
            owner = c["suspect"] if t.startswith("unary") else candidate
            matches = cells[owner, c["attribute"], c["value"]]
            violations.append(matches.Not() if t.endswith("positive") else matches)
        elif "same_as" in t or "different_from" in t:
            a = c["attribute"]
            owner = candidate if t.startswith("crime") else c["other_suspect"]
            intersections = []
            for v in domains[a]:
                intersection = model.new_bool_var("intersection")
                left, right = cells[owner, a, v], cells[c["suspect"], a, v]
                model.add_bool_and([left, right]).only_enforce_if(intersection)
                model.add_bool_or([left.Not(), right.Not()]).only_enforce_if(
                    intersection.Not()
                )
                intersections.append(intersection)
            same = model.new_bool_var("same")
            model.add(sum(intersections) == same)
            violations.append(same.Not() if t.endswith("same_as") else same)
        else:
            matches = []
            for s in suspects:
                both = model.new_bool_var("conjunction")
                p = cells[s, c["attr1"], c["val1"]]
                q = cells[s, c["attr2"], c["val2"]]
                model.add_bool_and([p, q]).only_enforce_if(both)
                model.add_bool_or([p.Not(), q.Not()]).only_enforce_if(both.Not())
                matches.append(both)
            present = model.new_bool_var("present")
            model.add_bool_or(matches).only_enforce_if(present)
            model.add(sum(matches) == 0).only_enforce_if(present.Not())
            violations.append(present.Not() if t == "indirect_positive" else present)
    model.add(sum(violations) <= allowance)
    return model, cells


def evaluate(case, reports=None, budget=None, engine="independent"):
    budget = budget or Budget()
    reports = case["reports"] if reports is None else reports
    check_nuisance(reports)
    reports = core_reports(reports)
    suspects, domains = case["suspects"], case["domains"]
    mode, allowance = case["assignment_mode"], case["corruption_allowance"]
    witnesses = {}
    builder = {"production": _production, "independent": _independent}[engine]
    for candidate in suspects:
        budget.check()
        model, cells = builder(suspects, domains, reports, candidate, mode, allowance)
        status, solver = budget.solve(model)
        if status == cp_model.INFEASIBLE:
            continue
        world = {
            s: {
                a: (
                    vs[solver.value(cells[s, a])]
                    if engine == "production"
                    else next(v for v in vs if solver.value(cells[s, a, v]))
                )
                for a, vs in domains.items()
            }
            for s in suspects
        }
        if not witness_valid(case, world, candidate, reports):
            raise AssertionError("corruption witness failed direct validation")
        witnesses[candidate] = world
    return {"status": "resolved", "candidates": list(witnesses), "witnesses": witnesses}


def witness_valid(case, world, culprit, reports=None):
    if culprit not in case["suspects"] or not valid_world(
        case["suspects"], case["domains"], world
    ):
        return False
    if case["assignment_mode"] == "distinct" and any(
        len({world[s][a] for s in case["suspects"]}) != len(case["suspects"])
        for a in case["domains"]
    ):
        return False
    reports = core_reports(case["reports"] if reports is None else reports)
    return (
        sum(not holds(r["constraint"], world, culprit) for r in reports)
        <= case["corruption_allowance"]
    )


def certify(case, budget=None):
    budget = budget or Budget()
    check_nuisance(case["reports"])
    production = evaluate(case, budget=budget, engine="production")
    independent = evaluate(case, budget=budget)
    if production["candidates"] != independent["candidates"]:
        raise AssertionError("community encodings disagree")
    world, culprit = case["solution"]["world"], case["solution"]["murderer"]
    if not witness_valid(case, world, culprit):
        raise ValueError("sampled world incompatible with published reliability rules")
    false_ids = sorted(
        [
            r["report_id"]
            for r in core_reports(case["reports"])
            if not holds(r["constraint"], world, culprit)
        ]
    )
    expected = case["false_report_count"]
    if len(false_ids) != expected:
        raise ValueError("sampled false report count mismatch")
    return {
        "status": "verified_unique"
        if len(independent["candidates"]) == 1
        else "verified_ambiguous",
        "case_hash": digest(case),
        "production_agrees": True,
        "candidates": independent["candidates"],
        "witnesses": independent["witnesses"],
        "false_report_ids": false_ids,
        "sampled_world_compatible": True,
        "nuisance_components": "independent_satisfiable",
        "shared_solver_engine": True,
        "complete_world_uniqueness": False,
    }


def exhaustive(case, reports=None, maximum_worlds=1000000):
    coordinates = [(s, a) for s in case["suspects"] for a in case["domains"]]
    if prod(len(case["domains"][a]) for _, a in coordinates) > maximum_worlds:
        raise Unresolved("exhaustive reference size limit")
    witnesses = {}
    for values in product(*(case["domains"][a] for _, a in coordinates)):
        world = {s: {} for s in case["suspects"]}
        for (s, a), value in zip(coordinates, values):
            world[s][a] = value
        for culprit in case["suspects"]:
            if culprit not in witnesses and witness_valid(
                case, world, culprit, reports
            ):
                witnesses[culprit] = world
    return [s for s in case["suspects"] if s in witnesses]


def minimum_subset(case, budget=None):
    """Counterexample multicover: exclude each alternative by > k violations.

    A missing report consumes no corruption allowance. Every lower bound is an
    optimal hitting-multicover solve; upper bounds are verified sufficient sets.
    """
    budget = budget or Budget()
    reports = core_reports(case["reports"])
    target = case["solution"]["murderer"]
    if evaluate(case, reports, budget)["candidates"] != [target]:
        return {
            "status": "not_applicable",
            "lower_bound": None,
            "upper_bound": None,
            "report_ids": [],
        }
    lower, selected, cuts = 0, list(range(len(reports))), []
    try:
        while True:
            budget.check()
            master = cp_model.CpModel()
            bits = [master.new_bool_var(f"select:{i}") for i in range(len(reports))]
            for cut in cuts:
                master.add(
                    sum(bits[i] for i in cut["violated"]) > case["corruption_allowance"]
                )
            master.minimize(sum(bits))
            status, solver = budget.solve(master)
            if status != cp_model.OPTIMAL:
                break
            proposal = [i for i, bit in enumerate(bits) if solver.value(bit)]
            lower = len(proposal)
            state = evaluate(case, [reports[i] for i in proposal], budget)
            if state["candidates"] == [target]:
                selected = proposal
                return {
                    "status": "exact",
                    "lower_bound": lower,
                    "upper_bound": lower,
                    "report_ids": [reports[i]["report_id"] for i in selected],
                    "cuts": cuts,
                }
            for culprit, world in state["witnesses"].items():
                if culprit == target:
                    continue
                violated = [
                    i
                    for i, r in enumerate(reports)
                    if not holds(r["constraint"], world, culprit)
                ]
                if len(violated) <= case["corruption_allowance"]:
                    raise AssertionError("alternative contradicts full-bank uniqueness")
                cuts.append({"culprit": culprit, "world": world, "violated": violated})
    except Unresolved:
        pass
    return {
        "status": "bounded",
        "lower_bound": lower,
        "upper_bound": len(selected),
        "report_ids": [reports[i]["report_id"] for i in selected],
        "cuts": cuts,
    }


def coalition_certificate(case, allocation, budget=None):
    budget = budget or Budget()
    ids = [r["report_id"] for r in case["reports"]]
    if set(allocation) != set(ids) or any(
        not owners
        or len(owners) != len(set(owners))
        or any(type(a) is not int or not 0 <= a < case["agent_count"] for a in owners)
        for owners in allocation.values()
    ):
        raise ValueError("allocation must cover every report with valid owners")
    reports = core_reports(case["reports"])
    results, sufficient = [], []
    cache = {}
    target = case["solution"]["murderer"]
    for size in range(case["agent_count"] + 1):
        for team in combinations(range(case["agent_count"]), size):
            available = [
                r for r in reports if set(team) & set(allocation[r["report_id"]])
            ]
            key = tuple(sorted(r["report_id"] for r in available))
            if key not in cache:
                cache[key] = evaluate(case, available, budget)
            state = cache[key]
            solved = state["candidates"] == [target]
            if solved:
                sufficient.append(team)
            results.append(
                {
                    "agents": list(team),
                    "sufficient": solved,
                    "candidates": state["candidates"],
                    "witnesses": state["witnesses"],
                }
            )
    minimal = [
        list(t) for t in sufficient if not any(set(u) < set(t) for u in sufficient)
    ]
    return {
        "status": "exact",
        "minimum_size": min(map(len, sufficient), default=None),
        "minimal_sufficient_coalitions": minimal,
        "coalitions": results,
        "allocation_hash": digest(allocation),
    }
