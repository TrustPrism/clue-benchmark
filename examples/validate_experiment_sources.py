"""Check the public experiment catalog and recount outcomes; no model calls."""

import hashlib
import json
from collections import Counter
from pathlib import Path


def validate(root="docs/site/assets"):
    root = Path(root)
    index = json.loads((root / "experiment-source-index.json").read_text())
    expected = {
        "original-controls": (270, 21),
        "high-thinking-controls": (360, 30),
        "flash-stress": (40, 32),
        "fresh-hard-confirmation": (48, 48),
        "initial-development-screening": (144, 36),
        "qwen-settings-diagnostic": (9, 3),
        "sampled-qwen": (72, 36),
        "nuisance-replication": (144, 12),
    }
    assert {family["id"] for family in index["families"]} == set(expected)
    saved = {}
    report = {}
    for record in [*index["families"], index["offline_controls"]]:
        path = root / record["asset"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
        value = json.loads(path.read_text())
        if "id" not in record:
            assert value["model_calls"] == 0
            continue
        identity = record["id"]
        rows = value["episodes"]
        shape = len(rows), len({row["world_id"] for row in rows})
        assert shape == expected[identity]
        assert shape == (record["assigned_slots"], record["assigned_worlds"])
        saved[identity] = rows
        report[identity] = {"assigned_slots": shape[0], "assigned_worlds": shape[1]}

    fresh = saved["fresh-hard-confirmation"]
    assert sum(row["correct"] for row in fresh) == 9
    assert sum(row["abstained"] for row in fresh) == 11
    initial = saved["initial-development-screening"]
    statuses = Counter(row["outcome"] for row in initial)
    assert statuses["interrupted_by_user"] == 2
    assert statuses["unattempted"] == 42
    assert statuses["protocol_failure"] == 16
    assert statuses["supported_correct"] == 54
    diagnostic = saved["qwen-settings-diagnostic"]
    assert Counter(row["outcome"] for row in diagnostic) == {
        "supported_correct": 3,
        "other_answer": 5,
        "protocol_failure": 1,
    }
    sampled = saved["sampled-qwen"]
    assert Counter(row["outcome"] for row in sampled) == {
        "supported_correct": 22,
        "wrong_with_sufficient_evidence": 15,
        "appropriate_abstention": 11,
        "unsupported_correct_guess": 2,
        "unsupported_wrong_answer": 17,
        "protocol_failure": 5,
    }
    phases = Counter(row["phase"] for row in saved["nuisance-replication"])
    assert phases == {"initial": 96, "extension": 48}
    return {"families": report, "hashes": "verified", "model_calls": 0}


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
