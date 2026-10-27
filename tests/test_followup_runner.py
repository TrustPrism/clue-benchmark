import shutil

import pytest

from clue_benchmark import generate_dataset, resolve_config
from clue_benchmark.community_evaluation import prepare_evaluation
from clue_benchmark.config import digest
from clue_benchmark.dataset import atomic_json
from clue_benchmark.followup_runner import checked_jobs, run_followup
from clue_benchmark.native_transport import NativeTransport
from clue_benchmark.nuisance_followup import CAP, PROBES


@pytest.fixture
def study(tmp_path):
    bank = tmp_path / "bank"
    generate_dataset(resolve_config(name="quickstart", output=str(bank)))
    models = [
        {
            "id": name,
            "vendor": "google",
            "model": name,
            "identity": name,
            "settings": {
                "max_output_tokens": 4096,
                "temperature": 0,
                "thinking_level": "low",
            },
            "context_tokens": 1048576,
            "input_microdollars_per_million_tokens": 300000,
            "output_microdollars_per_million_tokens": 2500000,
        }
        for name in ("gemini-3.5-flash-lite", "gemini-3.8-flash")
    ]
    jobs = []
    for label, repeats, ceiling in [("probe", 1, PROBES), ("scored", 2, 100000)]:
        path = tmp_path / label
        shutil.copytree(bank, path)
        plan = prepare_evaluation(
            path,
            models,
            conditions=["complete"],
            repeats=repeats,
            spending_ceiling_microdollars=ceiling,
            max_requests=2 * repeats,
        )
        atomic_json(path / "plan.json", plan)
        jobs.append(
            {
                "directory": label,
                "plan_id": plan["plan_id"],
                "ceiling_microdollars": ceiling,
            }
        )
    value = {
        "status": "prepared_pending_access_and_authorization",
        "probe_job": jobs[0],
        "selected_blocks": [{"jobs": jobs[1:]}],
        "assigned_calls": 4,
    }
    value["manifest_id"] = digest(value)
    atomic_json(tmp_path / "study.json", value)
    return tmp_path, value


def authorization(value):
    # Fixture approval authorizes mocked transport only, never live calls.
    return {
        "schema_version": "clue-followup-authorization-1",
        "manifest_id": value["manifest_id"],
        "approved_by": "offline-test-fixture",
        "approved_at": "fixture",
        "spending_ceiling_microdollars": CAP,
        "max_requests": 6,
    }


def response(payload):
    return {
        "modelVersion": payload["model"],
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


def test_dry_run_never_constructs_provider(study, monkeypatch):
    root, value = study

    def forbidden(*args, **kwargs):
        raise AssertionError("dry run touched provider")

    monkeypatch.setattr(NativeTransport, "__init__", forbidden)
    result = run_followup(root)
    assert result["requests"] == 6 and result["model_calls"] == 0
    assert not (root / "execution").exists()
    with pytest.raises(PermissionError, match="human manifest-bound"):
        run_followup(root, dry_run=False)


def test_mock_resume_never_replays_intentional_attempts(study, monkeypatch):
    root, value = study
    calls = []

    def mock(self, payload, permit):
        permit.check(self.vendor, payload)
        calls.append(payload)
        return response(payload)

    monkeypatch.setattr(NativeTransport, "call_authorized", mock)
    result = run_followup(root, authorization(value), dry_run=False)
    assert result["status"] == "completed" and len(calls) == 6
    result = run_followup(root, authorization(value), dry_run=False)
    assert result["status"] == "completed" and len(calls) == 6


def test_unknown_probe_usage_stops_entire_study_and_resume(study, monkeypatch):
    root, value = study
    calls = []

    def unknown(self, payload, permit):
        permit.check(self.vendor, payload)
        calls.append(payload)
        return {"modelVersion": payload["model"], "candidates": []}

    monkeypatch.setattr(NativeTransport, "call_authorized", unknown)
    assert (
        run_followup(root, authorization(value), dry_run=False)["status"] == "stopped"
    )
    assert len(calls) == 1
    assert (
        run_followup(root, authorization(value), dry_run=False)["status"] == "stopped"
    )
    assert len(calls) == 1
    assert not (root / "execution/scored").exists()


def test_combined_ceiling_and_manifest_tampering_rejected(study):
    root, value = study
    value["selected_blocks"][0]["jobs"][0]["ceiling_microdollars"] = CAP
    value["manifest_id"] = digest(
        {k: v for k, v in value.items() if k != "manifest_id"}
    )
    with pytest.raises(ValueError, match="child plan changed"):
        checked_jobs(root, value)
