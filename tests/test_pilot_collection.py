"""Offline continuation merges preserve failures and original denominators."""

import importlib.util
from pathlib import Path

import pytest

from clue_benchmark.config import digest
from clue_benchmark.dataset import atomic_json

spec = importlib.util.spec_from_file_location(
    "collect_pilot_results",
    Path(__file__).parents[1] / "examples" / "collect_pilot_results.py",
)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def request(ident, case):
    return {
        "request_id": ident,
        "case_id": case,
        "world_id": case,
        "model": "mock",
        "condition": "complete",
        "agent": 0,
        "repeat": 0,
        "maximum_microdollars": 100,
        "input_token_upper_bound": 200,
    }


def write(root, requests, episodes, parent=None, mapping=None):
    plan = {
        "suite_id": "suite",
        "models": [],
        "max_requests": len(requests),
        "jobs": [{"job": "job", "plan_id": "job-plan", "requests": len(requests)}],
    }
    if parent:
        plan.update(continuation_of=parent, assignment_map=mapping)
    plan["pilot_id"] = digest(plan)
    atomic_json(root / "pilot-plan.json", plan)
    atomic_json(root / "preflight/job.json", {"requests": requests})
    atomic_json(
        root / "evaluation/job/results.json",
        {"plan_id": "job-plan", "episodes": episodes},
    )
    return plan


@pytest.fixture
def partial(tmp_path):
    requests = [request("failed", "world-1"), request("untouched", "world-2")]
    failure = {**requests[0], "dispatched": True, "usage_known": False}
    administrative = {**requests[1], "dispatched": False, "correct": False}
    original = tmp_path / "original"
    plan = write(original, requests, [failure, administrative])
    follow = tmp_path / "continuation"
    new = {**requests[1], "request_id": "new-id"}
    success = {
        **new,
        "dispatched": True,
        "usage_known": True,
        "actual_microdollars": 10,
        "correct": True,
        "supported": True,
        "protocol_valid": True,
    }
    mapping = [
        {
            "original_request_id": "untouched",
            "continuation_request_id": "new-id",
            "original_job": "job",
            "continuation_job": "job",
        }
    ]
    write(follow, [new], [success], plan["pilot_id"], mapping)
    return original, follow


def test_merge_keeps_failure_hold_and_all_assigned_denominators(partial):
    original, follow = partial
    before = (original / "evaluation/job/results.json").read_bytes()
    report = collector.collect(original, [follow])
    assert report["status"] == "all_assignments_dispatched"
    assert report["assigned"] == report["dispatched"] == 2
    assert report["settled"] == 1
    assert report["settled_microdollars"] == 10
    assert report["unknown_usage_reserved_microdollars"] == 100
    assert report["metrics"][0]["assigned_correctness"] == 0.5
    assert report["metrics"][0]["settled_correctness"] == 1
    assert (original / "evaluation/job/results.json").read_bytes() == before


def test_pending_is_separate_from_observed_failure(partial):
    report = collector.collect(partial[0])
    assert report["status"] == "partial"
    assert report["not_attempted"] == 1
    assert report["metrics"][0]["settled_correctness"] is None
    assert report["metrics"][0]["settled_incorrect"] == 0


def test_continuation_cannot_replace_dispatched_failure(partial):
    original, follow = partial
    plan, requests, episodes, _ = collector.inputs(follow)
    changed = {**requests["new-id"], "case_id": "world-1", "world_id": "world-1"}
    mapping = [{**plan["assignment_map"][0], "original_request_id": "failed"}]
    write(follow, [changed], [], plan["continuation_of"], mapping)
    with pytest.raises(ValueError, match="dispatched request"):
        collector.collect(original, [follow])


def test_continuation_cannot_change_original_assignment(partial):
    original, follow = partial
    plan, requests, episodes, _ = collector.inputs(follow)
    changed = {**requests["new-id"], "model": "different-model"}
    write(follow, [changed], [], plan["continuation_of"], plan["assignment_map"])
    with pytest.raises(ValueError, match="changes original"):
        collector.collect(original, [follow])


def test_same_assignment_cannot_be_added_twice(partial):
    original, follow = partial
    with pytest.raises(ValueError, match="duplicate continuation|dispatched request"):
        collector.collect(original, [follow, follow])
