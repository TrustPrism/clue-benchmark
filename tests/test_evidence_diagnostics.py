import importlib.util
import json
from pathlib import Path

import pytest


def load_script():
    path = Path(__file__).resolve().parents[1] / "scripts/evidence_diagnostics.py"
    spec = importlib.util.spec_from_file_location("evidence_diagnostics", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revealed_evidence_uses_only_initial_observation_and_successful_tools():
    script = load_script()
    log = {
        "transcript": [
            {
                "role": "user",
                "text": "Fixed prompt\n" + json.dumps({"clues": [{"clue_id": "c001"}]}),
            },
            {"role": "assistant", "calls": [["request_clue", {"query_id": "q001"}]]},
            {
                "role": "tool",
                "name": "request_clue",
                "result": {"error": "unknown_query_id"},
            },
            {
                "role": "tool",
                "name": "request_clue",
                "result": {"clue": {"clue_id": "c002"}},
            },
            {
                "role": "tool",
                "name": "request_clue",
                "result": {"clue": {"clue_id": "c002"}},
            },
        ]
    }
    assert script.revealed_ids(log, {"c001", "c002", "c003"}) == ["c001", "c002"]


def test_unknown_clue_cannot_enter_evidence_oracle():
    script = load_script()
    log = {
        "transcript": [
            {
                "role": "user",
                "text": "Prompt\n" + json.dumps({"clues": [{"clue_id": "unknown"}]}),
            }
        ]
    }
    with pytest.raises(ValueError, match="undeclared clue"):
        script.revealed_ids(log, {"c001"})
