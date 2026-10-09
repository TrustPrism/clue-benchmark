"""Meaningful matched-cohort, context, budget, and dispatch guard checks."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from clue_benchmark.community_bundle import iter_cases, rows
from clue_benchmark.community_evaluation import NativeTransport

spec = importlib.util.spec_from_file_location(
    "pilot_suite", Path(__file__).parents[1] / "examples" / "pilot_suite.py"
)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def model(context=1048576):
    return {
        "id": "mock-gemini",
        "vendor": "google",
        "model": "mock-gemini",
        "settings": {"max_output_tokens": 8},
        "context_tokens": context,
        "input_microdollars_per_million_tokens": 300000,
        "output_microdollars_per_million_tokens": 2500000,
    }


@pytest.fixture(scope="module")
def bank(tmp_path_factory):
    root = tmp_path_factory.mktemp("pilot")
    pilot.prepare(root, count=1)
    return root


def test_matched_controls_and_public_views(bank):
    suite = pilot.check_suite(bank)
    assert len(suite["bundles"]) == 10
    for burden in (4, 8):
        worlds, evidence = [], []
        for noise in (0, 100, 1000):
            arm = bank / f"burden-{burden}-noise-{noise}"
            answer = next(rows(arm / "answers.jsonl"))
            worlds.append(answer["world_id"])
            evidence.append(set(answer["core_report_ids"]))
            cert = next(rows(arm / "certificates.jsonl"))["certificate"][
                "minimum_subset"
            ]
            assert cert["lower_bound"] == cert["upper_bound"] == burden
            for record in iter_cases(arm, agent_id=0):
                assert (
                    not {
                        "solution",
                        "certificate",
                        "false_report_ids",
                        "nuisance_count",
                    }
                    & record.keys()
                )
        assert len(set(worlds)) == 1
        assert all(e == evidence[0] for e in evidence)
    diagnostics = json.loads((bank / "diagnostics.json").read_text())
    for row in diagnostics["information_controls"]:
        if (
            row["condition"] == "complete"
            or row["condition"] == "sharing"
            and (row["graph"] == "star" or row["rounds"] == 3)
        ):
            assert row["sufficient"]
        else:
            assert not row["sufficient"]
    assert all(
        r["reliability_aware_solver_unique"] for r in diagnostics["corruption_controls"]
    )
    for false in range(3):
        answer = next(rows(bank / f"false-{false}" / "answers.jsonl"))
        assert len(answer["false_report_ids"]) == false
        public = next(iter_cases(bank / f"false-{false}"))
        assert public["corruption_allowance"] == 2


def test_offline_context_and_single_total_budget(bank, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline preparation dispatched a provider")

    monkeypatch.setattr(NativeTransport, "call_authorized", forbidden)
    with pytest.raises(ValueError, match="context overflow"):
        pilot.plan_pilot(bank, [model(32)], 20000000)
    with pytest.raises(ValueError, match="exceeds ceiling"):
        pilot.plan_pilot(bank, [model()], 1)
    plan = pilot.plan_pilot(bank, [model()], 20000000, interval_seconds=0)
    assert sum(j["ceiling_microdollars"] for j in plan["jobs"]) == 20000000
    assert plan["max_requests"] == 18
    assert plan["conservative_maximum_microdollars"] <= 20000000
    frozen = {p.name: p.read_text() for p in (bank / "plans").glob("*.json")}
    with pytest.raises(ValueError, match="existing job plan differs"):
        pilot.plan_pilot(bank, [model()], 20000000, repeats=2, interval_seconds=0)
    assert frozen == {p.name: p.read_text() for p in (bank / "plans").glob("*.json")}
    with pytest.raises(PermissionError, match="pilot-bound approval"):
        pilot.run_pilot(bank, {})


def test_authorized_mock_run_and_resume_never_dispatches_twice(bank, monkeypatch):
    plan = pilot.plan_pilot(bank, [model()], 20000000, interval_seconds=0)
    calls = []

    def mock(self, payload, permit):
        permit.check(self.vendor, payload)
        calls.append(payload)
        return {
            "modelVersion": "mock-gemini",
            "candidates": [
                {
                    "content": {
                        "parts": [{"functionCall": {"name": "abstain", "args": {}}}]
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 1,
                "candidatesTokenCount": 1,
                "thoughtsTokenCount": 0,
                "totalTokenCount": 2,
            },
        }

    monkeypatch.setattr(NativeTransport, "call_authorized", mock)
    auth = {
        "schema_version": "clue-pilot-authorization-1",
        "pilot_id": plan["pilot_id"],
        "approved_by": "test",
        "approved_at": "test",
        "spending_ceiling_microdollars": 20000000,
        "max_requests": plan["max_requests"],
    }
    result = pilot.run_pilot(bank, auth)
    assert result["status"] == "complete"
    assert len(calls) == 18
    assert all(c["supported_accuracy_delta"] == 0 for c in result["contrasts"])
    pilot.run_pilot(bank, auth)
    assert len(calls) == 18


def test_world_clustered_contrasts_and_unmatched_rejection():
    a = [{"world_id": "A", "supported": True}] * 4 + [
        {"world_id": "B", "supported": False}
    ]
    b = [{"world_id": "A", "supported": False}, {"world_id": "B", "supported": False}]
    assert pilot.contrast(a, b)["supported_accuracy_delta"] == -0.5
    with pytest.raises(ValueError, match="same assigned worlds"):
        pilot.contrast(a, b[:1])


def test_unknown_usage_stops_all_jobs_and_resume(bank, tmp_path, monkeypatch):
    root = tmp_path / "held"
    shutil.copytree(
        bank,
        root,
        ignore=shutil.ignore_patterns("evaluation", "preflight", "pilot-results.json"),
    )
    plan = pilot.plan_pilot(root, [model()], 20000000, interval_seconds=0)
    calls = []

    def unknown(self, payload, permit):
        permit.check(self.vendor, payload)
        calls.append(payload)
        return {"candidates": []}  # No receipt: retain reservation and stop.

    monkeypatch.setattr(NativeTransport, "call_authorized", unknown)
    auth = {
        "schema_version": "clue-pilot-authorization-1",
        "pilot_id": plan["pilot_id"],
        "approved_by": "test",
        "approved_at": "test",
        "spending_ceiling_microdollars": 20000000,
        "max_requests": plan["max_requests"],
    }
    result = pilot.run_pilot(root, auth)
    assert result["status"] == "partial"
    assert len(calls) == 1
    assert len(result["missing_jobs"]) == 13
    report = json.loads(next((root / "evaluation").glob("*/results.json")).read_text())
    assert report["accounting"]["held_microdollars"] > 0
    pilot.run_pilot(root, auth)
    assert len(calls) == 1
