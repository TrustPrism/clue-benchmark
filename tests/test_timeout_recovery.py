"""Recovery must preserve failure scores and unknown maximum costs."""

import importlib.util
import json
from pathlib import Path

import pytest

from clue_benchmark.config import digest
from clue_benchmark.ledger import AccountingStop, Ledger

spec = importlib.util.spec_from_file_location(
    "continue_saved_study",
    Path(__file__).parents[1] / "scripts/continue_saved_study.py",
)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
MODEL = "google/fake"


def setup(tmp_path, error="timeout"):
    plan = {
        "plan_id": "frozen",
        "spending": {"combined_google_usd": 25},
        "continuation_policy": {
            "failed_timeout_recovery": controller.POLICY,
            "local_accounting_independent": True,
        },
    }
    ledger = Ledger(tmp_path / "ledger.sqlite3", plan)
    log = tmp_path / "logs" / (digest(MODEL) + "-compatibility.json")
    log.parent.mkdir()
    log.write_text(json.dumps({"compatible": True}))
    ledger.model_status(MODEL, "accounting_stopped", {"error": "accounting_stopped"})
    ledger.begin_episode("failed")
    ledger.finish_episode(
        "failed", {"model": MODEL, "error": error, "correct": 0, "answer": None}
    )
    return plan, ledger


def test_timeout_holds_full_maximum_and_never_replays_episode(tmp_path):
    plan, ledger = setup(tmp_path)
    rid = ledger.reserve("failed", MODEL, "scored", 324813, {"output_cap": 4096})
    ledger.uncertain(rid, "timeout")
    # A simultaneous free call must not be held, cancelled or repriced.
    local = ledger.reserve("local-running", "ollama/fake", "scored", 0)
    before = ledger.episodes()
    audit = controller.restore_timeouts(ledger, plan, tmp_path)
    assert audit["generation_calls"] == audit["failed_episodes_replayed"] == 0
    assert audit["held_timeout_request_ids"] == [rid]
    rows = ledger.export()["requests"]
    assert rows[0]["status"] == "held" and rows[0]["actual"] is None
    assert rows[0]["http_status"] is None  # Never mislabel a timeout as HTTP 503.
    assert rows[1]["id"] == local and rows[1]["status"] == "reserved"
    assert ledger.committed() == 324813
    assert ledger.episodes() == before and not ledger.begin_episode("failed")
    ledger.guard([MODEL])
    assert ledger.model(MODEL)["status"] == "compatible"
    assert controller.restore_timeouts(ledger, plan, tmp_path) is None
    ledger.close()


def test_successful_response_missing_usage_stays_stopped(tmp_path):
    plan, ledger = setup(tmp_path, "missing_usage")
    rid = ledger.reserve("failed", MODEL, "scored", 324813, {"output_cap": 4096})
    ledger.uncertain(rid, "missing_usage")
    before = ledger.export()
    with pytest.raises(AccountingStop, match="non-timeout"):
        controller.restore_timeouts(ledger, plan, tmp_path)
    assert ledger.export() == before
    ledger.close()


def test_accounted_preflight_timeout_resumes_without_new_charge(tmp_path):
    plan, ledger = setup(tmp_path)
    before = ledger.export()["requests"]
    audit = controller.restore_timeouts(ledger, plan, tmp_path)
    assert audit["held_timeout_request_ids"] == []
    assert ledger.export()["requests"] == before
    ledger.close()


def test_incompatible_protocol_stop_is_not_restored(tmp_path):
    plan, ledger = setup(tmp_path, "protocol_incompatible")
    assert controller.restore_timeouts(ledger, plan, tmp_path) is None
    assert ledger.model(MODEL)["status"] == "accounting_stopped"
    ledger.close()


def test_family_guard_pause_can_resume_after_timeout_is_held(tmp_path):
    plan, ledger = setup(tmp_path)
    rid = ledger.reserve("failed", MODEL, "scored", 324813, {"output_cap": 4096})
    ledger.uncertain(rid, "timeout")
    other = "google/other"
    (tmp_path / "logs" / (digest(other) + "-compatibility.json")).write_text(
        json.dumps({"compatible": True})
    )
    ledger.model_status(other, "accounting_stopped", {})
    ledger.begin_episode("previous-other")
    ledger.finish_episode(
        "previous-other", {"model": other, "error": None, "correct": 1}
    )
    audit = controller.restore_timeouts(ledger, plan, tmp_path)
    assert set(audit["resumed_models"]) == {MODEL, other}
    assert ledger.model(other)["status"] == "compatible"
    assert ledger.committed() == 324813
    ledger.close()
