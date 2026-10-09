import json
import random
from copy import deepcopy
from dataclasses import replace

import pytest

from clue_benchmark import Config, generate, validate_case
from clue_benchmark.dataset import atomic_json, build_bank, fingerprints, study_export
from clue_benchmark.logic import is_indirect
from clue_benchmark.solver import Outcome, Solver


@pytest.mark.parametrize("n,k", [(4, 8), (8, 12), (12, 16)])
def test_generation_and_reference_solution(n, k):
    for seed in range(3):
        result = generate(Config(suspect_count=n, clue_count=k), seed)
        assert result["status"] == "ok", result
        assert validate_case(result["case"])
        assert len(result["case"]["clues"]) == k


def test_determinism_and_local_randomness(case):
    random.seed(987)
    before = random.getstate()
    assert generate(Config(), 42)["case"] == case
    assert random.getstate() == before
    changed = generate(replace(Config(), mutation_steps=0), 42)["case"]
    assert changed["case_id"] != case["case_id"]


def test_failures_are_bounded_and_do_not_relax_constraints():
    result = generate(
        Config(enabled_types=("unary_positive",), max_attempts=2, mutation_steps=0), 1
    )
    assert result["status"] == "failed" and result["case"] is None
    assert result["diagnostics"]["attempts"] == 2
    result = generate(Config(max_solver_calls=1, max_attempts=2), 1)
    assert result["status"] == "failed"
    result = generate(Config(generation_seconds=1e-9), 1)
    assert result["status"] == "failed"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"alpha": 2},
        {"beta": float("nan")},
        {"max_attempts": 0},
        {"clue_count": True},
        {"domains": {"a": ["x", "x"]}},
        {"domains": {"a": ["x"]}},
        {"enabled_types": ["bad"]},
        {"min_indirect_clues": 99},
        {"max_murderer_links": 0},
        {"suspect_count": 1},
    ],
)
def test_bad_configuration(kwargs):
    with pytest.raises((ValueError, TypeError)):
        Config(**kwargs)


def test_parallel_and_resumed_generation_match(tmp_path):
    config = Config(mutation_steps=2)
    one = build_bank(config, 3, 901, tmp_path / "one.json", workers=1)
    two = build_bank(config, 3, 901, tmp_path / "two.json", workers=2)
    assert one["cases"] == two["cases"]
    assert one["cases"][0]["seed"] == 901
    partial = deepcopy(one)
    partial["cases"] = one["cases"][:1]
    partial["diagnostics"] = one["diagnostics"][:1]
    partial["next_seed"] = 902
    partial["complete"] = False
    atomic_json(tmp_path / "resume.json", partial)
    resumed = build_bank(config, 3, 901, tmp_path / "resume.json", workers=2)
    assert resumed["cases"] == one["cases"]
    with pytest.raises(ValueError):
        build_bank(replace(config, alpha=0.1), 3, 901, tmp_path / "one.json")


def test_duplicate_screen_ignores_suspect_and_value_names(case):
    renamed = deepcopy(case)
    names = {s: f"Person{i}" for i, s in enumerate(case["suspects"])}
    values = {
        a: {v: f"V{i}" for i, v in enumerate(vs)} for a, vs in case["domains"].items()
    }
    renamed["suspects"] = [names[s] for s in case["suspects"]]
    renamed["domains"] = {a: list(m.values()) for a, m in values.items()}
    renamed["solution"]["world"] = {
        names[s]: {a: values[a][v] for a, v in attrs.items()}
        for s, attrs in case["solution"]["world"].items()
    }
    renamed["solution"]["murderer"] = names[case["solution"]["murderer"]]
    for c in renamed["clues"]:
        if "suspect" in c:
            c["suspect"] = names[c["suspect"]]
        for a, v in [("attribute", "value"), ("attr1", "val1"), ("attr2", "val2")]:
            if v in c:
                c[v] = values[c[a]][c[v]]
    assert fingerprints(case) == fingerprints(renamed)


def test_tampered_case_rejected(case):
    bad = deepcopy(case)
    bad["solution"]["murderer"] = next(
        s for s in case["suspects"] if s != case["solution"]["murderer"]
    )
    with pytest.raises(ValueError):
        validate_case(bad)


def test_compatibility_export(case):
    bank = study_export([case])["states"][0]["clues"]["benchmark"]
    assert len(bank["records"]) == len(bank["raw_items"]) == len(bank["items"])
    assert isinstance(bank["items"][0], str)
    assert bank["records"][0]["necessary_for_uniqueness"] is None


def test_configuration_roundtrip_preserves_generation():
    original = Config()
    loaded = Config(**json.loads(json.dumps(original.to_dict(), sort_keys=True)))
    assert original.fingerprint == loaded.fingerprint
    assert generate(original, 555)["case"] == generate(loaded, 555)["case"]


def test_sampling_weights_change_verified_banks():
    low_direct = Config(
        suspect_count=12, clue_count=16, alpha=0, beta=0, mutation_steps=0
    )
    high_direct = replace(low_direct, alpha=1)
    negative = [generate(low_direct, seed)["case"] for seed in range(20)]
    direct = [generate(high_direct, seed)["case"] for seed in range(20)]
    assert all(negative) and all(direct)
    assert sum(is_indirect(c) for case in negative for c in case["clues"]) > sum(
        is_indirect(c) for case in direct for c in case["clues"]
    )
    positive = [
        generate(replace(low_direct, beta=1), seed)["case"] for seed in range(20)
    ]
    assert all(positive)
    assert sum(
        c["type"] in ("indirect_positive", "crime_same_as")
        for case in positive
        for c in case["clues"]
    ) > sum(
        c["type"] in ("indirect_positive", "crime_same_as")
        for case in negative
        for c in case["clues"]
    )


@pytest.mark.parametrize("n,k", [(4, 8), (8, 12), (12, 16)])
def test_release_policy_requires_relationship_reasoning(n, k):
    config = Config(
        suspect_count=n,
        clue_count=k,
        min_indirect_clues=2,
        require_indirect_essential=True,
    )
    for seed in range(10):
        result = generate(config, seed)
        assert result["status"] == "ok", result
        case = result["case"]
        assert validate_case(case)
        direct = [c for c in case["clues"] if not is_indirect(c)]
        solver = Solver(case["suspects"], case["domains"], config)
        assert solver.check(direct).status == Outcome.AMBIGUOUS
