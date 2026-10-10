import importlib.util
import json
from pathlib import Path

import pytest

from clue_benchmark.community_evaluation import NativeTransport, run_evaluation
from clue_benchmark.dataset import atomic_json

spec = importlib.util.spec_from_file_location(
    "hardness_suite", Path(__file__).parents[1] / "examples/hardness_suite.py"
)
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)


def model(context=1048576):
    return {
        "id": "fixture",
        "vendor": "google",
        "model": "fixture",
        "settings": {"max_output_tokens": 10},
        "context_tokens": context,
        "input_microdollars_per_million_tokens": 300000,
        "output_microdollars_per_million_tokens": 2500000,
    }


@pytest.fixture(scope="module")
def bank(tmp_path_factory):
    root = tmp_path_factory.mktemp("hardness-suite")
    suite.prepare(root, count=1, selected_groups=["reasoning-8", "near-solutions"])
    return root


def test_matched_hardness_controls_and_world_splits(bank):
    prepared = suite.check_suite(bank)
    assert len(prepared["bundles"]) == 5
    assert all(
        m["necessary_evidence"]["lower_bound"] == 8
        for m in prepared["measurements"]
        if m["group"] == "reasoning-8"
    )
    distances = {
        m["arm"]: m["true_core_structure"][
            "maximum_equality_distance_from_unary_anchor"
        ]
        for m in prepared["measurements"]
    }
    assert distances["equality_tree-8"] > distances["branching-8"]
    assert all(
        m["alternative_margin"] == 1
        for m in prepared["measurements"]
        if m["group"] == "near-solutions"
    )
    assert prepared["model_calls"] == 0
    by_world = {}
    for m in prepared["measurements"]:
        assert by_world.setdefault(m["world_id"], m["split"]) == m["split"]


def test_suite_total_spending_and_frozen_plans_are_offline(bank, tmp_path, monkeypatch):
    monkeypatch.setattr(
        NativeTransport, "call_authorized", lambda *_: pytest.fail("network called")
    )
    first = suite.plan(
        bank,
        [model()],
        tmp_path / "zero",
        repeats=2,
        input_views=["text_only", "structured_text"],
    )
    assert not first["fundable"] and first["network_calls"] == 0
    assert first["total_request_count"] == 20
    assert all(
        json.loads(p.read_text())["spending_ceiling_microdollars"] == 0
        for p in (tmp_path / "zero").glob("*.json")
        if p.name != "plans.json"
    )
    funded = suite.plan(
        bank,
        [model()],
        tmp_path / "funded",
        repeats=2,
        input_views=["text_only", "structured_text"],
        ceiling_microdollars=first["maximum_microdollars"],
    )
    assert funded["fundable"]
    assert (
        sum(j["maximum_microdollars"] for j in funded["jobs"])
        == first["maximum_microdollars"]
    )
    original = {p.name: p.read_text() for p in (tmp_path / "funded").glob("*.json")}
    with pytest.raises(ValueError, match="frozen plan differs"):
        suite.plan(
            bank,
            [model()],
            tmp_path / "funded",
            repeats=3,
            ceiling_microdollars=100000000,
        )
    assert original == {
        p.name: p.read_text() for p in (tmp_path / "funded").glob("*.json")
    }
    overflow = suite.plan(
        bank, [model(32)], tmp_path / "overflow", ceiling_microdollars=100000000
    )
    assert not overflow["fundable"] and not any(
        j["all_contexts_fit"] for j in overflow["jobs"]
    )


def test_analysis_preserves_assigned_failures_and_checks_request_identity(
    bank, tmp_path
):
    frozen = suite.plan(
        bank,
        [model()],
        tmp_path / "plans",
        selected_arms=["equality_tree-8"],
        repeats=3,
    )
    job = frozen["jobs"][0]
    p = json.loads((tmp_path / "plans" / (job["name"] + ".json")).read_text())
    planned = run_evaluation(p, bank / job["arm"], tmp_path / "unused")["requests"]
    result = {
        "plan_id": p["plan_id"],
        "episodes": [
            {
                **r,
                "correct": False,
                "supported": False,
                "protocol_valid": False,
                "transport": "provider_error",
            }
            for r in planned
        ],
    }
    result_path = tmp_path / "runs" / job["name"] / "results.json"
    atomic_json(result_path, result)
    analyzed = suite.analyze(
        bank, tmp_path / "plans", tmp_path / "runs", tmp_path / "analysis.json"
    )
    assert analyzed["complete"]
    assert analyzed["jobs"][0]["metrics"][0]["protocol_failures"] == 3
    assert analyzed["jobs"][0]["world_clusters"][0]["assigned"] == 3
    result["episodes"][0]["request_id"] = "another-job"
    atomic_json(result_path, result)
    with pytest.raises(ValueError, match="request identities mismatch"):
        suite.analyze(
            bank, tmp_path / "plans", tmp_path / "runs", tmp_path / "analysis.json"
        )
