"""Bounded CP-SAT checks: unresolved results are never uniqueness proofs."""

import time
from dataclasses import dataclass
from enum import Enum

from ortools.sat.python import cp_model

from .config import Config
from .logic import fact_key, validate


class Unresolved(RuntimeError):
    pass


class Outcome(str, Enum):
    UNIQUE = "unique"
    AMBIGUOUS = "ambiguous"
    INFEASIBLE = "infeasible"


@dataclass(frozen=True)
class Check:
    status: Outcome
    murderer: str | None = None


class Solver:
    def __init__(self, suspects, domains, config=None, deadline=None):
        self.suspects = list(suspects)
        self.domains = domains
        self.config = config or Config()
        self.deadline = deadline or time.monotonic() + self.config.generation_seconds
        self.calls = 0
        self.cache = {}

    def model(self, clues):
        model = cp_model.CpModel()
        xs = {
            s: {
                a: model.new_int_var(0, len(v) - 1, f"{s}_{a}")
                for a, v in self.domains.items()
            }
            for s in self.suspects
        }
        m = model.new_int_var(0, len(self.suspects) - 1, "murderer")
        crime = {
            a: model.new_int_var(0, len(v) - 1, f"crime_{a}")
            for a, v in self.domains.items()
        }
        # Conditional equalities avoid a reproducible OR-Tools 9.15
        # ExpandElement native crash on partially constrained crime attributes.
        choices = []
        for i, suspect in enumerate(self.suspects):
            selected = model.new_bool_var(f"murderer_is_{i}")
            choices.append(selected)
            model.add(m == i).only_enforce_if(selected)
            model.add(m != i).only_enforce_if(selected.Not())
            for attribute in self.domains:
                model.add(crime[attribute] == xs[suspect][attribute]).only_enforce_if(
                    selected
                )
        model.add_exactly_one(choices)
        for raw in clues:
            c = validate(raw, self.suspects, self.domains)
            t = c["type"]
            if t in (
                "unary_positive",
                "unary_negative",
                "crime_positive",
                "crime_negative",
            ):
                a = c["attribute"]
                value = self.domains[a].index(c["value"])
                var = xs[c["suspect"]][a] if t.startswith("unary") else crime[a]
                model.add(var == value if t.endswith("positive") else var != value)
            elif t in ("crime_same_as", "crime_different_from"):
                a = c["attribute"]
                left = crime[a]
                right = xs[c["suspect"]][a]
                model.add(left == right if t == "crime_same_as" else left != right)
            else:
                a, b = c["attr1"], c["attr2"]
                v, w = (
                    self.domains[a].index(c["val1"]),
                    self.domains[b].index(c["val2"]),
                )
                matches = []
                for s in self.suspects:
                    if t == "indirect_negative":
                        model.add_forbidden_assignments([xs[s][a], xs[s][b]], [(v, w)])
                    else:
                        eq1 = model.new_bool_var("eq1")
                        eq2 = model.new_bool_var("eq2")
                        both = model.new_bool_var("both")
                        model.add(xs[s][a] == v).only_enforce_if(eq1)
                        model.add(xs[s][a] != v).only_enforce_if(eq1.Not())
                        model.add(xs[s][b] == w).only_enforce_if(eq2)
                        model.add(xs[s][b] != w).only_enforce_if(eq2.Not())
                        model.add_implication(both, eq1)
                        model.add_implication(both, eq2)
                        model.add_bool_or([eq1.Not(), eq2.Not(), both])
                        matches.append(both)
                if t == "indirect_positive":
                    model.add_bool_or(matches)
        return model, m

    def _solve(self, model):
        left = self.deadline - time.monotonic()
        if left <= 0 or self.calls >= self.config.max_solver_calls:
            raise Unresolved("solver budget exhausted")
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = 0
        solver.parameters.max_time_in_seconds = min(left, self.config.solver_seconds)
        solver.parameters.max_deterministic_time = self.config.solver_work
        self.calls += 1
        status = solver.solve(model)
        if status == cp_model.MODEL_INVALID:
            raise ValueError("invalid CP-SAT model")
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.INFEASIBLE):
            raise Unresolved("solver inconclusive")
        return status, solver

    def check(self, clues):
        if time.monotonic() >= self.deadline:
            raise Unresolved("solver deadline exhausted")
        key = tuple(sorted(fact_key(c) for c in clues))
        if key in self.cache:
            return self.cache[key]
        model, m = self.model(clues)
        status, solver = self._solve(model)
        if status == cp_model.INFEASIBLE:
            result = Check(Outcome.INFEASIBLE)
        else:
            first = solver.value(m)
            model.add(m != first)
            status, _ = self._solve(model)
            result = (
                Check(Outcome.UNIQUE, self.suspects[first])
                if status == cp_model.INFEASIBLE
                else Check(Outcome.AMBIGUOUS)
            )
        self.cache[key] = result
        return result

    def feasible_candidates(self, clues):
        result = []
        for i, s in enumerate(self.suspects):
            model, m = self.model(clues)
            model.add(m == i)
            status, _ = self._solve(model)
            if status != cp_model.INFEASIBLE:
                result.append(s)
        return result
