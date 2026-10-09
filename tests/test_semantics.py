import random
from itertools import product

import pytest
from ortools.sat.python import cp_model

from clue_benchmark import Config
from clue_benchmark.clue_formatter import ClueFormatter
from clue_benchmark.clue_generator import ClueGenerator
from clue_benchmark.logic import fact_key, truth, validate
from clue_benchmark.solver import Outcome, Solver, Unresolved

S = ["A", "B"]
D = {"weapon": ["Rope", "Knife"], "location": ["Study", "Hall"]}
WORLDS = [
    {s: dict(zip(D, values[i * 2 : i * 2 + 2])) for i, s in enumerate(S)}
    for values in product(*[D[a] for s in S for a in D])
]


def reference(c, w, m):
    t = c["type"]
    if t == "unary_positive":
        return w[c["suspect"]][c["attribute"]] == c["value"]
    if t == "unary_negative":
        return w[c["suspect"]][c["attribute"]] != c["value"]
    if t == "crime_positive":
        return w[m][c["attribute"]] == c["value"]
    if t == "crime_negative":
        return w[m][c["attribute"]] != c["value"]
    if t == "crime_same_as":
        return w[m][c["attribute"]] == w[c["suspect"]][c["attribute"]]
    if t == "crime_different_from":
        return w[m][c["attribute"]] != w[c["suspect"]][c["attribute"]]
    if t == "suspect_same_as":
        return w[c["suspect"]][c["attribute"]] == w[c["other_suspect"]][c["attribute"]]
    if t == "suspect_different_from":
        return w[c["suspect"]][c["attribute"]] != w[c["other_suspect"]][c["attribute"]]
    matching = [
        s for s in S if (w[s][c["attr1"]], w[s][c["attr2"]]) == (c["val1"], c["val2"])
    ]
    return len(matching) > 0 if t == "indirect_positive" else len(matching) == 0


def pool():
    clues = {}
    for w in WORLDS:
        for m in S:
            g = ClueGenerator(w, m, D)
            g.build_clue_pool(rng=random.Random(0))
            clues.update({fact_key(c): c for c in g.clue_pool})
    return list(clues.values())


def test_solver_matches_exhaustive_world_enumerator():
    clues = pool()
    rng = random.Random(1)
    banks = (
        [[]]
        + [[c] for c in clues]
        + [rng.sample(clues, rng.randrange(2, 8)) for _ in range(150)]
    )
    for bank in banks:
        expected = [
            m for m in S if any(all(reference(c, w, m) for c in bank) for w in WORLDS)
        ]
        solver = Solver(S, D)
        assert solver.feasible_candidates(bank) == expected, bank
        result = solver.check(bank)
        assert result.status == (
            {0: Outcome.INFEASIBLE, 1: Outcome.UNIQUE}.get(
                len(expected), Outcome.AMBIGUOUS
            )
        )
        if len(expected) == 1:
            assert result.murderer == expected[0]


@pytest.mark.parametrize("clue", pool())
def test_truth_matches_independent_semantics(clue):
    for world in WORLDS:
        for murderer in S:
            assert truth(clue, world, murderer) == reference(clue, world, murderer)


def test_existential_language_does_not_claim_implication():
    clue = dict(
        type="indirect_positive",
        attr1="weapon",
        val1="Rope",
        attr2="location",
        val2="Study",
    )
    world = {
        "A": {"weapon": "Rope", "location": "Study"},
        "B": {"weapon": "Rope", "location": "Hall"},
    }
    assert truth(clue, world, "A")
    assert (
        ClueFormatter.format(clue)
        == 'At least one suspect has "weapon" = "Rope" and "location" = "Study".'
    )
    assert (
        ClueFormatter.format({**clue, "type": "indirect_negative"})
        == 'No suspect has both "weapon" = "Rope" and "location" = "Study".'
    )


def test_unknown_solver_status_is_not_cached_as_infeasible(monkeypatch):
    solver = Solver(S, D)
    monkeypatch.setattr(cp_model.CpSolver, "solve", lambda *a, **k: cp_model.UNKNOWN)
    with pytest.raises(Unresolved):
        solver.check([])
    assert not solver.cache


def test_budget_and_invalid_clues():
    with pytest.raises(Unresolved):
        Solver(S, D, Config(max_solver_calls=1)).check([])
    with pytest.raises(ValueError):
        Solver(S, D).check([{"type": "nonsense"}])
    with pytest.raises(ValueError):
        validate(dict(type="crime_positive", attribute="weapon", value="Bad"), S, D)
    with pytest.raises(ValueError):
        validate(
            dict(type="crime_positive", attribute="weapon", value="Rope", extra=1), S, D
        )


def test_controlled_language_preserves_literals():
    import json
    import re

    for c in pool():
        text = ClueFormatter.format(c)
        quoted = [json.loads(token) for token in re.findall(r'"(?:[^"\\]|\\.)*"', text)]
        if c["type"].startswith("unary_"):
            assert quoted == [c["suspect"], c["attribute"], c["value"]]
            assert (" != " in text) == (c["type"] == "unary_negative")
        elif c["type"] in ("crime_positive", "crime_negative"):
            assert quoted == [c["attribute"], c["value"]]
            assert (" != " in text) == (c["type"] == "crime_negative")
        elif c["type"] in ("crime_same_as", "crime_different_from"):
            assert quoted == [c["attribute"], c["suspect"]]
            assert ("the same" in text) == (c["type"] == "crime_same_as")
        elif c["type"].startswith("suspect_"):
            assert quoted == [c["suspect"], c["other_suspect"], c["attribute"]]
            assert ("the same" in text) == (c["type"] == "suspect_same_as")
        else:
            assert quoted == [c["attr1"], c["val1"], c["attr2"], c["val2"]]
            assert text.startswith("At least one") == (c["type"] == "indirect_positive")
    c = {
        "type": "crime_positive",
        "attribute": "custom key",
        "value": 'A "quoted" Value',
    }
    assert 'A \\"quoted\\" Value' in ClueFormatter.format(c)


def test_partial_crime_constraints_native_crash_regression():
    import json
    from pathlib import Path

    data = json.loads(
        (Path(__file__).parent / "fixtures/element_crash.json").read_text()
    )
    solver = Solver(data["suspects"], data["domains"])
    assert solver.check(data["clues"]).status == Outcome.AMBIGUOUS
    assert solver.feasible_candidates(data["clues"]) == data["suspects"]
