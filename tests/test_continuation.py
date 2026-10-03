import copy
import json
from pathlib import Path

import pytest
from test_pilot import LOCAL_ID, ROOT, FakeProvider, factory_for, freeze, small_plan

from clue_benchmark.config import digest
from clue_benchmark.continuation import initialize_continuation, prepare_continuation
from clue_benchmark.dataset import atomic_json
from clue_benchmark.ledger import AccountingStop, Ledger, execution_lock
from clue_benchmark.pilot import PILOT_MODELS, prepare_pilot
from clue_benchmark.runner import declared_episodes, execution_cases, run_study


@pytest.fixture(scope="module")
def pilot():
    return prepare_pilot(
        ROOT / "data/v0.3/private/dev.jsonl",
        ROOT / "data/v0.3/private/test.jsonl",
        ROOT,
        LOCAL_ID,
    )


def continued_small(pilot, tmp_path):
    plan = small_plan(pilot, tmp_path)
    plan["continuation_policy"] = {
        "hold_service_error_codes": [503],
        "local_accounting_independent": True,
    }
    plan["initial_pilot_case_ids"] = plan["selected_case_ids"]
    plan["execution_schedule"] = "paired-world-round-robin-v1"
    freeze(plan)
    Ledger(Path(plan["execution_directory"]) / "ledger.sqlite3", plan).close()
    return plan


def test_continuation_freezes_asymmetric_expansion_and_preserves_pilot(pilot):
    plan = prepare_continuation(pilot, ROOT)
    assert plan["spending"]["combined_google_usd"] == 25
    assert plan["expected_episodes"] == 4104
    assert plan["episodes_by_model"] == dict(zip(PILOT_MODELS, (1944, 1944, 216)))
    assert plan["initial_pilot_case_ids"] == pilot["selected_case_ids"]
    assert plan["provider_settings"][PILOT_MODELS[0]]["input_safety_margin"] == 1024
    cases = execution_cases(plan, ROOT)
    episodes = list(declared_episodes(plan, cases))
    assert len(episodes) == 4104
    assert len({e for e, _, _ in episodes}) == 4104
    initial = set(pilot["selected_case_ids"])
    first_expansion = next(
        i for i, (_, row, _) in enumerate(episodes) if row["case_id"] not in initial
    )
    assert first_expansion == 648
    assert all(
        row["case_id"] not in initial for _, row, _ in episodes[first_expansion:]
    )
    old_ids = {e for e, _, _ in declared_episodes(pilot, execution_cases(pilot, ROOT))}
    assert old_ids == {e for e, _, _ in episodes[:648]}
    assert {row["execution_split"] for row in [plan]} == {"dev"}


def test_service_503_holds_maximum_without_retry_or_erasing_failure(pilot, tmp_path):
    plan = continued_small(pilot, tmp_path)
    providers = {}

    class Once503(FakeProvider):
        failed = False

        def generate(self, messages, tools, max_output, timeout):
            if (
                "Protocol compatibility probe" not in json.dumps(messages)
                and not self.failed
            ):
                self.failed = True
                exc = RuntimeError("SECRET provider URL must stay out of reports")
                exc.code = 503
                raise exc
            return super().generate(messages, tools, max_output, timeout)

    def factory(model, settings, identity):
        providers[model] = Once503(model)
        return providers[model]

    result = run_study(plan, ROOT, provider_factory=factory)
    held = [r for r in result["ledger"]["requests"] if r["status"] == "held"]
    assert len(held) == 3
    assert all(r["http_status"] == 503 and r["actual"] is None for r in held)
    assert (
        result["ledger"]["committed_usd"]
        == result["ledger"]["settled_usd"]
        + result["ledger"]["unresolved_reservations_usd"]
    )
    assert sum(row["error"] == "service_unavailable" for row in result["episodes"]) == 3
    assert result["manifest"]["dispatched_episodes"] == 18
    for held_request in held:
        assert (
            sum(
                r["episode"] == held_request["episode"]
                for r in result["ledger"]["requests"]
            )
            == 1
        )
    assert "SECRET" not in json.dumps(result)
    again = run_study(plan, ROOT, provider_factory=factory_for())
    assert result["ledger"]["requests"] == again["ledger"]["requests"]


def test_success_without_usage_stops_paid_but_local_can_complete(pilot, tmp_path):
    plan = continued_small(pilot, tmp_path)
    paid = run_study(
        plan,
        ROOT,
        provider_factory=factory_for("missing_usage"),
        models=PILOT_MODELS[:2],
    )
    assert paid["manifest"]["stop_reason"] == "accounting_stopped"
    before = paid["ledger"]["committed_usd"]
    local = run_study(
        plan, ROOT, provider_factory=factory_for(), models=[PILOT_MODELS[2]]
    )
    local_rows = [r for r in local["episodes"] if r["model"] == PILOT_MODELS[2]]
    assert all(r["completion"] for r in local_rows)
    assert local["ledger"]["committed_usd"] == before
    assert any(r["status"] == "uncertain" for r in local["ledger"]["requests"])


def test_paid_model_filters_share_a_lock(pilot, tmp_path):
    plan = continued_small(pilot, tmp_path)
    output = Path(plan["execution_directory"])
    with execution_lock(output / "runner-google.lock"):
        with pytest.raises(RuntimeError, match="another study runner"):
            run_study(
                plan, ROOT, provider_factory=factory_for(), models=[PILOT_MODELS[1]]
            )


def test_per_model_cases_must_be_declared(pilot, tmp_path):
    plan = continued_small(pilot, tmp_path)
    plan["model_case_ids"] = {PILOT_MODELS[0]: ["unknown"]}
    freeze(plan)
    with pytest.raises(ValueError, match="subset"):
        run_study(plan, ROOT, dry_run=True)


def test_ledger_copy_lowers_ceiling_keeps_unknown_cost_and_episode_identity(
    pilot, tmp_path
):
    previous = copy.deepcopy(pilot)
    previous["execution_directory"] = str(tmp_path / "original")
    freeze(previous)
    output = Path(previous["execution_directory"])
    ledger = Ledger(output / "ledger.sqlite3", previous)
    rid = ledger.reserve("failed", PILOT_MODELS[1], "scored", 324813)
    ledger.uncertain(rid, "provider_error")
    ledger.begin_episode("finished")
    ledger.finish_episode("finished", {"correct": 0})
    ledger.model_status(PILOT_MODELS[1], "accounting_stopped", {})
    atomic_json(
        output / "logs" / (digest(PILOT_MODELS[1]) + "-compatibility.json"),
        {"compatible": True},
    )
    before = ledger.export()
    ledger.close()
    plan = prepare_continuation(
        previous, ROOT, execution_directory=str(tmp_path / "continued")
    )
    audit = initialize_continuation(previous, plan, ROOT, [rid])
    assert audit["preserved_committed_usd"] == 0.324813
    assert audit["new_cumulative_ceiling_usd"] == 25
    old = Ledger(output / "ledger.sqlite3", previous)
    assert old.export() == before
    with pytest.raises(AccountingStop):
        old.guard()
    old.close()
    new = Ledger(Path(plan["execution_directory"]) / "ledger.sqlite3", plan)
    new.guard()
    assert new.export()["requests"][0]["actual"] is None
    assert new.export()["requests"][0]["status"] == "held"
    assert not new.begin_episode("finished")
    assert new.model(PILOT_MODELS[1])["status"] == "compatible"
    new.close()


def test_missing_prior_ledger_cannot_reset_continuation_budget(pilot, tmp_path):
    plan = continued_small(pilot, tmp_path)
    (Path(plan["execution_directory"]) / "ledger.sqlite3").unlink()
    with pytest.raises(ValueError, match="audited prior ledger"):
        run_study(plan, ROOT, provider_factory=factory_for())


def test_token_guard_covers_observed_58_token_overrun():
    from types import SimpleNamespace

    from google.genai import types

    from clue_benchmark.providers import GoogleProvider, checked_usage

    provider = object.__new__(GoogleProvider)
    provider.client = SimpleNamespace(
        models=SimpleNamespace(
            count_tokens=lambda **kw: SimpleNamespace(total_tokens=2)
        )
    )
    provider.types = types
    provider.model = "gemini-3.8-flash"
    provider.last_usage = checked_usage(3930, 3955, 3933)
    provider.last_result_bound = 476
    provider.settings = {}
    messages = [
        types.Content(
            role="user", parts=[types.Part(text="Native conversation history")]
        )
    ]
    old_bound = provider.input_tokens_bound(messages, ["request_clue", "submit_answer"])
    assert old_bound == 8617
    assert old_bound < 8692  # Actual input of the recorded failing request.
    provider.settings = {"input_safety_margin": 1024}
    assert (
        provider.input_tokens_bound(messages, ["request_clue", "submit_answer"]) > 8692
    )
