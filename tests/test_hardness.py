"""Hardness controls certify semantics; they never certify a model failure."""

import json
from copy import deepcopy
from dataclasses import replace
from itertools import product

import pytest

from clue_benchmark.community_bundle import (
    file_hash,
    generate_dataset,
    iter_cases,
    load_evaluator_cases,
    rows,
    validate_dataset,
)
from clue_benchmark.community_config import CommunityConfig
from clue_benchmark.community_evaluation import (
    _observations,
    prepare_evaluation,
    run_evaluation,
)
from clue_benchmark.community_generation import (
    _report,
    generate_case,
    iter_allocations,
    iter_reports,
)
from clue_benchmark.community_semantics import Budget, reliability_profile
from clue_benchmark.independent_oracle import holds, valid_world
from clue_benchmark.native_transport import NativeTransport
from clue_benchmark.solver import Unresolved


def paths_config(**evidence):
    return CommunityConfig.from_dict(
        {
            "puzzle": {
                "family": "redundant_paths",
                "config": {
                    "suspect_count": 6,
                    "clue_count": 35,
                    "domains": {f"attribute{i}": ["0", "1", "2"] for i in range(5)},
                },
            },
            "distribution": {"agent_count": 1, "minimum_coalition_size": 1},
            "evidence": evidence,
            "dataset": {"certification_seconds": 2},
        }
    )


@pytest.mark.parametrize("mode", ["repeated", "distinct"])
@pytest.mark.parametrize("cross_attribute", [True, False])
def test_violation_distances_match_exhaustive_worlds(mode, cross_attribute):
    suspects = ["A", "B"]
    domains = {"x": ["0", "1"], "y": ["0", "1"]}
    clues = [
        dict(type="unary_positive", suspect="A", attribute="x", value="0"),
        dict(type="crime_negative", attribute="x", value="0"),
        dict(type="suspect_same_as", suspect="A", other_suspect="B", attribute="y"),
        dict(type="crime_different_from", suspect="B", attribute="y"),
        dict(type="indirect_positive", attr1="x", val1="1", attr2="y", val2="0"),
    ]
    if not cross_attribute:
        clues = clues[:-1]
    case = {
        "suspects": suspects,
        "domains": domains,
        "assignment_mode": mode,
        "reports": [_report(c) for c in clues],
        "corruption_allowance": 1,
        "solution": {"murderer": "B"},
    }
    expected = {s: len(clues) for s in suspects}
    for values in product("01", repeat=4):
        world = {
            "A": dict(zip(domains, values[:2])),
            "B": dict(zip(domains, values[2:])),
        }
        assert valid_world(suspects, domains, world)
        if mode == "distinct" and any(world["A"][a] == world["B"][a] for a in domains):
            continue
        for s in suspects:
            expected[s] = min(expected[s], sum(not holds(c, world, s) for c in clues))
    profile = reliability_profile(case)
    assert profile["optimization_components"] == (
        "joint" if cross_attribute else "attributes"
    )
    assert {
        r["culprit"]: r["minimum_violations"] for r in profile["candidates"]
    } == expected
    case["reports"] += deepcopy(case["reports"])
    assert reliability_profile(case) == profile  # Copies do not create votes.
    with pytest.raises(Unresolved):
        reliability_profile(case, Budget(0))


def test_targeted_corruption_is_certified_and_improves_search_objective():
    random = generate_case(paths_config(false_reports=2), 107)
    targeted = generate_case(
        paths_config(
            false_reports=2,
            corruption_strategy="targeted",
            corruption_search_attempts=4,
            maximum_alternative_margin=1,
        ),
        107,
    )
    assert random["status"] == targeted["status"] == "ok"
    assert random["case"]["world_id"] == targeted["case"]["world_id"]
    assert len(targeted["certificate"]["false_report_ids"]) == 2
    assert targeted["certificate"]["reliability_profile"]["alternative_margin"] == 1
    assert (
        targeted["certificate"]["reliability_profile"]["alternative_margin"]
        <= random["certificate"]["reliability_profile"]["alternative_margin"]
    )
    assert targeted["certificate"]["corruption_search"]["attempts"] == 4
    for case in (random["case"], targeted["case"]):
        for attr in case["domains"]:
            mentioned = {
                c[key]
                for r in case["reports"]
                for c in [r["constraint"]]
                if c.get("attribute") == attr
                for key in ("suspect", "other_suspect")
                if key in c
            }
            assert mentioned == set(case["suspects"])


def test_impossible_alternative_margin_rejects_without_relaxation():
    result = generate_case(
        paths_config(corruption_allowance=2, maximum_alternative_margin=1), 107
    )
    assert result["status"] == "rejected"
    assert result["diagnostics"]["reason"] == "alternative_margin_requirement_unmet"


def test_connected_decoys_are_target_constraints_and_revalidated(tmp_path):
    cfg = paths_config(connected_decoys=6, false_reports=2)
    cfg = replace(cfg, dataset=replace(cfg.dataset, output_directory=str(tmp_path)))
    assert generate_dataset(cfg)["complete"]
    assert validate_dataset(tmp_path)["status"] == "verified"
    saved = next(rows(tmp_path / "certificates.jsonl"))
    decoys = saved["certificate"]["connected_decoys"]
    assert len(decoys["reports"]) == 6
    assert all(
        r["constraint"]["type"].startswith("suspect_") for r in decoys["reports"]
    )
    assert len(next(load_evaluator_cases(tmp_path))["reports"]) == 41
    # Recomputed file hashes cannot conceal incorrect evaluator distances.
    saved["certificate"]["reliability_profile"]["alternative_margin"] += 1
    path = tmp_path / "certificates.jsonl"
    path.write_text(json.dumps(saved) + "\n")
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    manifest["files"][path.name] = file_hash(path)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="distance mismatch"):
        validate_dataset(tmp_path)


@pytest.mark.parametrize("placement", ["front", "middle", "end", "interleaved"])
def test_placement_preserves_reports_ownership_and_world(tmp_path, placement):
    cfg = CommunityConfig.from_dict(
        {
            "puzzle": {"family": "equality_tree", "config": {"clue_count": 4}},
            "evidence": {"irrelevant_records": 12},
            "presentation": {"evidence_placement": placement},
            "dataset": {"output_directory": str(tmp_path), "seed": 107},
        }
    )
    result = generate_case(cfg, 107)
    assert result["status"] == "ok"
    reports = list(iter_reports(result["case"]))
    allocations = list(iter_allocations(result["case"], result["partition"]))
    assert [r["report_id"] for r in reports] == [rid for rid, _ in allocations]
    positions = [
        i for i, r in enumerate(reports) if r["constraint"]["type"] != "record_positive"
    ]
    assert (
        positions
        == {
            "front": [0, 1, 2, 3],
            "middle": [6, 7, 8, 9],
            "end": [12, 13, 14, 15],
            "interleaved": [2, 5, 9, 12],
        }[placement]
    )
    assert generate_dataset(cfg)["complete"]
    assert validate_dataset(tmp_path)["status"] == "verified"
    case = next(load_evaluator_cases(tmp_path))
    model = {
        "id": "fixture",
        "vendor": "openai",
        "model": "fixture",
        "settings": {"max_output_tokens": 100},
        "context_tokens": 100000,
        "input_microdollars_per_million_tokens": 0,
        "output_microdollars_per_million_tokens": 0,
    }
    plan = prepare_evaluation(
        tmp_path, [model], conditions=["complete"], input_view="text_only"
    )
    observation = next(_observations(case, plan, "complete"))[1]
    assert [r["report_id"] for r in observation["reports"]] == [
        r["report_id"] for r in reports
    ]
    assert all(set(r) == {"report_id", "text"} for r in observation["reports"])
    default_plan = prepare_evaluation(tmp_path, [model], conditions=["complete"])
    assert default_plan["plan_id"] != plan["plan_id"]
    assert (
        next(_observations(case, default_plan, "complete"))[2]
        == next(_observations(case, plan, "complete"))[2]
    )

    def adapter(header, reports, ownership, limits):
        views = [[] for _ in range(header["agent_count"])]
        for report, (rid, owners) in zip(reports, ownership, strict=True):
            assert report["report_id"] == rid
            assert (
                not {"solution", "false_report_ids", "reliability_profile"}
                & report.keys()
            )
            for owner in owners:
                views[owner].append(rid)
        return {"evidence": views, "messages": []}

    adapter.identity = "hardness-placement-fixture"
    sharing = prepare_evaluation(
        tmp_path,
        [model],
        conditions=["sharing"],
        forwarding_policy_identity=adapter.identity,
    )
    assert (
        run_evaluation(
            sharing, tmp_path, tmp_path / "adapter", forwarding_policy=adapter
        )["network_calls"]
        == 0
    )


def test_harder_dry_run_never_contacts_provider(tmp_path, monkeypatch):
    monkeypatch.setattr(
        NativeTransport, "_request", lambda *_: pytest.fail("network called")
    )
    cfg = paths_config(
        false_reports=2, corruption_strategy="targeted", corruption_search_attempts=2
    )
    cfg = replace(cfg, dataset=replace(cfg.dataset, output_directory=str(tmp_path)))
    assert generate_dataset(cfg)["complete"]
    model = {
        "id": "fixture",
        "vendor": "google",
        "model": "fixture",
        "settings": {"max_output_tokens": 100},
        "context_tokens": 100000,
        "input_microdollars_per_million_tokens": 0,
        "output_microdollars_per_million_tokens": 0,
    }
    plan = prepare_evaluation(tmp_path, [model], input_view="text_only", repeats=3)
    assert run_evaluation(plan, tmp_path, tmp_path / "dry")["network_calls"] == 0
    assert not (tmp_path / "dry/requests.sqlite").exists()


@pytest.mark.parametrize(
    "bad",
    [
        {"evidence": {"corruption_strategy": "magic"}},
        {"evidence": {"corruption_search_attempts": 0}},
        {"evidence": {"maximum_alternative_margin": 0}},
        {"presentation": {"evidence_placement": "hidden"}},
        {"puzzle": {"family": "redundant_paths", "config": {"clue_count": 8}}},
    ],
)
def test_invalid_hardness_controls(bad):
    with pytest.raises(ValueError):
        CommunityConfig.from_dict(bad)


def test_large_necessary_core_and_cross_worker_reproduction(tmp_path):
    cfg = CommunityConfig.from_dict(
        {
            "puzzle": {
                "family": "equality_tree",
                "extra_clue_scope": "non_target_attributes",
                "config": {"suspect_count": 32, "clue_count": 38},
            },
            "evidence": {
                "minimum_sufficient_clues": 32,
                "maximum_sufficient_clues": 32,
            },
            "distribution": {"agent_count": 1, "minimum_coalition_size": 1},
            "dataset": {
                "seed": 107,
                "count": 2,
                "output_directory": str(tmp_path / "one"),
            },
        }
    )
    first = generate_dataset(cfg)
    second = generate_dataset(
        replace(
            cfg,
            dataset=replace(
                cfg.dataset, workers=2, output_directory=str(tmp_path / "two")
            ),
        )
    )
    assert first["complete"] and second["complete"]
    assert first["files"] == second["files"]
    assert all(
        m["necessary_evidence"]["lower_bound"]
        == m["necessary_evidence"]["upper_bound"]
        == 32
        for m in first["metrics"]
    )
    assert validate_dataset(tmp_path / "one")["status"] == "verified"


def test_50000_interleaved_bundle_streams_without_evaluator_leaks(tmp_path):
    import tracemalloc

    cfg = CommunityConfig.from_dict(
        {
            "puzzle": {"family": "equality_tree", "config": {"clue_count": 4}},
            "evidence": {"irrelevant_records": 49996},
            "presentation": {"evidence_placement": "interleaved"},
            "dataset": {"large_corpus": True, "output_directory": str(tmp_path)},
        }
    )
    tracemalloc.start()
    try:
        assert generate_dataset(cfg)["complete"]
        assert validate_dataset(tmp_path)["status"] == "verified"
        positions = []
        count = 0
        for row in iter_cases(tmp_path):
            assert (
                not {
                    "solution",
                    "reliability_profile",
                    "connected_decoys",
                    "false_report_ids",
                }
                & row.keys()
            )
            if row["kind"] == "report":
                if row["constraint"]["type"] != "record_positive":
                    positions.append(count)
                count += 1
        assert count == 50000 and positions == [9999, 19999, 29999, 39999]
        assert tracemalloc.get_traced_memory()[1] < 24 * 1024 * 1024
    finally:
        tracemalloc.stop()
