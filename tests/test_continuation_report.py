"""Guard against outcome-based selection in the post-hoc whole-world comparison."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "report_continuation", Path(__file__).parents[1] / "scripts/report_continuation.py"
)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def world(models=("a", "b")):
    return [
        {"model": m, "world_group": "w", "error": None, "correct": 0}
        for m in models
        for _ in range(18)
    ]


def test_complete_world_keeps_scored_failures():
    rows = world()
    rows[0]["error"] = "token_limit"
    rows[1]["error"] = "service_unavailable"
    assert report.complete_worlds(rows, ["a", "b"]) == ["w"]


def test_complete_world_excludes_unfunded_or_inflight_schedule():
    for error in (
        "missing_episode",
        "interrupted_episode",
        "in_progress",
        "budget_stopped",
    ):
        rows = world()
        rows[0]["error"] = error
        assert report.complete_worlds(rows, ["a", "b"]) == []


def test_complete_world_requires_every_shared_model():
    assert report.complete_worlds(world(("a",)), ["a", "b"]) == []
    assert report.complete_worlds(world()[:-1], ["a", "b"]) == []
