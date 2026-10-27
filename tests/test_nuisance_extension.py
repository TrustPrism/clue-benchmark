import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest


def extension_module():
    path = Path(__file__).parents[1] / "examples/nuisance_extension.py"
    spec = importlib.util.spec_from_file_location("nuisance_extension", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_combined_cap_counts_old_spend_not_a_fresh_allowance():
    extension = extension_module()
    prior = {"settled_microdollars": 4731671, "held_microdollars": 0}
    assert extension.enforce_total(prior, [4668756]) == 9400427
    with pytest.raises(ValueError, match="combined"):
        extension.enforce_total(prior, [5268330])
    with pytest.raises(ValueError, match="combined"):
        extension.enforce_total({**prior, "held_microdollars": 1}, [1])


@pytest.mark.parametrize(
    "status", ["settled", "held_unknown", "dispatched", "resource_breach"]
)
def test_prior_must_have_all_slots_closed_and_exact_receipt_cost(
    tmp_path, monkeypatch, status
):
    extension = extension_module()
    (tmp_path / "study.json").write_text(
        json.dumps({"assigned_calls": 0, "manifest_id": "old-manifest"})
    )
    model = {
        "id": "fixture",
        "identity": "fixture-version",
        "input_microdollars_per_million_tokens": 1000000,
        "output_microdollars_per_million_tokens": 1000000,
    }
    plan = {"plan_id": "old-plan", "max_requests": 2, "models": [model]}
    monkeypatch.setattr(
        extension, "checked_jobs", lambda *args: [({"directory": "bank"}, plan)]
    )
    monkeypatch.setattr(
        extension,
        "run_evaluation",
        lambda *args, **kwargs: {
            "requests": [{"request_id": "one"}, {"request_id": "two"}]
        },
    )
    root = tmp_path / "execution/probe"
    root.mkdir(parents=True)
    db = sqlite3.connect(root / "requests.sqlite")
    db.executescript(
        'CREATE TABLE identity (id TEXT); INSERT INTO identity VALUES ("old-plan"); CREATE TABLE requests (id TEXT,status TEXT,maximum INTEGER,actual INTEGER,result TEXT);'
    )
    receipt = json.dumps(
        {
            "model": "fixture",
            "usage_known": True,
            "returned_model": "fixture-version",
            "input_tokens": 1,
            "output_tokens": 1,
        }
    )
    db.executemany(
        "INSERT INTO requests VALUES (?,?,?,?,?)",
        [("one", status, 3, 2, receipt), ("two", "settled", 3, 2, receipt)],
    )
    db.commit()
    db.close()
    if status == "settled":
        result = extension.closed_prior(tmp_path)
        assert result["settled_microdollars"] == 4 and result["closed_requests"] == 2
    else:
        with pytest.raises(ValueError, match="unresolved"):
            extension.closed_prior(tmp_path)
