"""No incomplete-usage recovery without explicit authorization or full maxima."""

import importlib.util
from pathlib import Path

import pytest
from test_timeout_recovery import setup

from clue_benchmark.ledger import AccountingStop

spec = importlib.util.spec_from_file_location(
    "continue_reserved_study",
    Path(__file__).parents[1] / "scripts/continue_reserved_study.py",
)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


def test_incomplete_usage_requires_explicit_override(tmp_path):
    plan, ledger = setup(tmp_path, "missing_usage")
    plan["continuation_policy"]["failed_timeout_recovery"] = controller.POLICY
    with pytest.raises(ValueError, match="authorization"):
        controller.restore_reserved_failures(ledger, plan, tmp_path)
    ledger.close()


def test_authorized_failure_holds_maximum_and_preserves_score(tmp_path):
    plan, ledger = setup(tmp_path, "missing_usage")
    plan["continuation_policy"].update(
        failed_timeout_recovery=controller.POLICY, incomplete_usage_authorized=True
    )
    rid = ledger.reserve("failed", "google/fake", "scored", 787171, {"output_cap": 197})
    ledger.uncertain(rid, "missing_usage")
    old = ledger.episodes()
    audit = controller.restore_reserved_failures(ledger, plan, tmp_path)
    assert audit["held_failed_request_ids"] == [rid]
    assert ledger.committed() == 787171
    assert ledger.episodes() == old
    assert not ledger.begin_episode("failed")
    assert ledger.export()["requests"][0]["actual"] is None
    ledger.close()


def test_other_unclassified_errors_remain_stopped(tmp_path):
    plan, ledger = setup(tmp_path, "provider_error")
    plan["continuation_policy"].update(
        failed_timeout_recovery=controller.POLICY, incomplete_usage_authorized=True
    )
    rid = ledger.reserve("failed", "google/fake", "scored", 787171, {"output_cap": 197})
    ledger.uncertain(rid, "provider_error")
    with pytest.raises(AccountingStop):
        controller.restore_reserved_failures(ledger, plan, tmp_path)
    assert ledger.model("google/fake")["status"] == "accounting_stopped"
    ledger.close()
