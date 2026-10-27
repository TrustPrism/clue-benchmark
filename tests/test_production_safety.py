import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from clue_benchmark import evaluate_agent, generate_dataset, resolve_config
from clue_benchmark.community_evaluation import (
    Ledger,
    prepare_evaluation,
    run_evaluation,
)
from clue_benchmark.dataset import atomic_json
from clue_benchmark.replay import write_report


def test_atomic_json_concurrent_writers_never_publish_partial_json(tmp_path):
    path = tmp_path / "saved.json"

    def write(index):
        atomic_json(path, {"writer": index, "records": list(range(1000))})

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(write, range(30)))
    assert len(json.loads(path.read_text())["records"]) == 1000
    assert not list(tmp_path.glob("*.tmp"))
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        atomic_json(path, {"wrong": True}, overwrite=False)
    assert path.read_bytes() == original


def test_completed_generation_never_rewrites_files_or_reexecutes(tmp_path, monkeypatch):
    config = resolve_config(name="quickstart", output=str(tmp_path / "bank"))
    initial = generate_dataset(config)
    paths = list((tmp_path / "bank").glob("*.json*"))
    mtimes = {p.name: p.stat().st_mtime_ns for p in paths}

    def forbidden(*args, **kwargs):
        raise AssertionError("completed generation reran solver")

    monkeypatch.setattr("clue_benchmark.community_bundle.generate_case", forbidden)
    assert generate_dataset(config) == initial
    assert {p.name: p.stat().st_mtime_ns for p in paths} == mtimes


def test_unrelated_existing_bundle_is_not_overwritten(tmp_path):
    root = tmp_path / "bank"
    root.mkdir()
    (root / "cases.jsonl").write_text("preserve")
    with pytest.raises(ValueError, match="checkpoint"):
        generate_dataset(resolve_config(name="quickstart", output=str(root)))
    assert (root / "cases.jsonl").read_text() == "preserve"


def test_existing_evaluator_output_rejects_before_callback(tmp_path):
    output = tmp_path / "scored.json"
    output.write_text("preserve")

    def forbidden(*args):
        raise AssertionError("agent called despite occupied output")

    with pytest.raises(ValueError, match="output exists"):
        evaluate_agent(tmp_path / "missing", forbidden, output=output)
    assert output.read_text() == "preserve"


def test_lost_reservation_race_cannot_dispatch(tmp_path, monkeypatch):
    bank = tmp_path / "bank"
    generate_dataset(resolve_config(name="quickstart", output=str(bank)))
    model = {
        "id": "fixture",
        "vendor": "google",
        "model": "fixture",
        "settings": {"max_output_tokens": 8},
        "context_tokens": 1000000,
        "input_microdollars_per_million_tokens": 0,
        "output_microdollars_per_million_tokens": 0,
    }
    plan = prepare_evaluation(bank, [model], conditions=["complete"], max_requests=1)
    auth = {
        "schema_version": "clue-community-authorization-1",
        "plan_id": plan["plan_id"],
        "approved_by": "offline-fixture",
        "approved_at": "fixture",
        "spending_ceiling_microdollars": 0,
        "max_requests": 1,
    }
    monkeypatch.setattr(Ledger, "reserve", lambda *args: False)

    def forbidden(*args):
        raise AssertionError("duplicate request was dispatched")

    result = run_evaluation(
        plan,
        bank,
        tmp_path / "evaluation",
        dry_run=False,
        authorization=auth,
        transports={"fixture": forbidden},
    )
    assert not result["complete"]
    assert "no duplicate dispatch" in result["stopped_reason"]
    assert all(not e.get("dispatched") for e in result["episodes"])


@pytest.mark.parametrize(
    "value", [[], {"episodes": [1]}, {"studies": {"bad": {"panels": []}}}]
)
def test_malformed_report_leaves_no_output(tmp_path, value):
    source = tmp_path / "source.json"
    source.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        write_report(source, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_exclusive_evaluation_directory_lock_prevents_concurrent_launch(tmp_path):
    import fcntl

    bank = tmp_path / "bank"
    generate_dataset(resolve_config(name="quickstart", output=str(bank)))
    model = {
        "id": "fixture",
        "vendor": "google",
        "model": "fixture",
        "settings": {"max_output_tokens": 8},
        "context_tokens": 1000000,
        "input_microdollars_per_million_tokens": 0,
        "output_microdollars_per_million_tokens": 0,
    }
    plan = prepare_evaluation(bank, [model], conditions=["complete"], max_requests=1)
    auth = {
        "schema_version": "clue-community-authorization-1",
        "plan_id": plan["plan_id"],
        "approved_by": "offline-fixture",
        "approved_at": "fixture",
        "spending_ceiling_microdollars": 0,
        "max_requests": 1,
    }
    output = tmp_path / "evaluation"
    output.mkdir()
    with (output / ".evaluation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(PermissionError, match="another evaluation"):
            run_evaluation(plan, bank, output, dry_run=False, authorization=auth)
    assert not (output / "requests.sqlite").exists()


def test_two_plan_identities_cannot_share_one_ledger(tmp_path):
    with ThreadPoolExecutor(2) as pool:

        def claim(identity):
            try:
                ledger = Ledger(tmp_path / "shared.sqlite", {"plan_id": identity})
                ledger.close()
                return True
            except ValueError:
                return False

        results = list(pool.map(claim, ["plan-a", "plan-b"]))
    assert sum(results) == 1
