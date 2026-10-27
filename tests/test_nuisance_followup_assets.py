import importlib.util
from pathlib import Path

import pytest


def package_module():
    path = Path(__file__).parents[1] / "examples/package_nuisance_followup.py"
    spec = importlib.util.spec_from_file_location("package_nuisance_followup", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_receipt_distribution_copy_excludes_private_and_raw_fields():
    source = {
        "plan_id": "frozen",
        "complete": True,
        "stopped_reason": None,
        "accounting": {"settled_microdollars": 12, "held_microdollars": 0},
        "authorization": "PRIVATE",
        "episodes": [
            {
                "request_id": "call-1",
                "correct": True,
                "supported": True,
                "actual_microdollars": 12,
                "authorization": "PRIVATE",
                "native_calls": [{"secret": "PRIVATE"}],
                "receipt": {
                    "vendor": "google",
                    "counters": {
                        "prompt_token_count": 10,
                        "thoughts_token_count": 0,
                        "private": "PRIVATE",
                    },
                    "raw_usage": {"unexpected": "PRIVATE"},
                },
            }
        ],
    }
    clean = package_module().safe_report(source)
    assert "PRIVATE" not in str(clean)
    assert "native_calls" not in clean["episodes"][0]
    assert clean["episodes"][0]["receipt"]["counters"] == {
        "prompt_token_count": 10,
        "thoughts_token_count": 0,
    }
    assert clean["episodes"][0]["actual_microdollars"] == 12
    assert source["authorization"] == "PRIVATE"


def test_measured_archive_never_overwrites_existing_file(tmp_path):
    target = tmp_path / "measured.tar.gz"
    target.write_bytes(b"preserve-original")
    with pytest.raises(ValueError, match="never replace"):
        package_module().package(tmp_path, tmp_path, target)
    assert target.read_bytes() == b"preserve-original"
