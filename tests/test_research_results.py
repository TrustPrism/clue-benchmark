import json
import socket
from copy import deepcopy
from importlib.resources import files

import pytest

from clue_benchmark.research_results import analyze_measurements, replay_nuisance


def measurements():
    return json.loads(
        files("clue_benchmark")
        .joinpath("resources/measured-results/nuisance-followup.json")
        .read_text()
    )


def test_combined_and_separate_phases_have_fixed_denominators(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline replay attempted network")

    monkeypatch.setattr(socket, "socket", forbidden)
    result = replay_nuisance(tmp_path / "replay")
    assert result["model_calls"] == 0
    assert result["phases"]["initial"]["assigned"] == 96
    assert result["phases"]["extension"]["assigned"] == 48
    assert result["combined"]["assigned"] == 144
    assert result["combined"]["worlds"] == 12
    assert all(p["worlds"] == 6 and p["assigned"] == 12 for p in result["panels"])
    lite = [
        p for p in result["panels"] if p["burden"] == 4 and "flash-lite" in p["model"]
    ]
    assert [p["supported_correct"] for p in lite] == [10, 9, 10]
    primary = next(c for c in result["combined"]["contrasts"] if c["primary"])
    assert primary["mean_change"] == 0
    assert primary["world_cluster_bootstrap_95_interval"] == [-0.25, 0.25]
    assert primary["unchanged_worlds"] == 4
    assert result["accounting"]["combined_settled_microdollars"] == 6961763
    assert result["accounting"]["held_microdollars"] == 0
    rendered = (tmp_path / "replay/report/index.html").read_text()
    assert all(
        label in rendered
        for label in [
            "Initial phase",
            "Extension phase",
            "Combined exploratory estimate",
        ]
    )


def test_replay_refuses_duplicate_slots_reused_worlds_and_bad_accounting():
    original = measurements()
    duplicate = deepcopy(original)
    duplicate["episodes"][1]["request_id"] = duplicate["episodes"][0]["request_id"]
    with pytest.raises(ValueError, match="unique"):
        analyze_measurements(duplicate)
    changed = deepcopy(original)
    changed["accounting"]["combined_settled_microdollars"] -= 1
    with pytest.raises(ValueError, match="accounting"):
        analyze_measurements(changed)
    extra = deepcopy(original)
    extra["episodes"].pop()
    with pytest.raises(ValueError, match="144"):
        analyze_measurements(extra)
