import json

import pytest

from clue_benchmark import (
    evaluate_agent,
    export_public,
    generate_dataset,
    inspect_case,
    resolve_config,
)
from clue_benchmark.community_cli import main
from clue_benchmark.parameter_reference import explain_config, parameter_paths
from clue_benchmark.presets import NAMES
from clue_benchmark.replay import replay_example, write_report


@pytest.mark.parametrize("name", NAMES)
def test_packaged_preset_certifies(name, tmp_path):
    cfg = resolve_config(name=name, output=str(tmp_path / name))
    result = generate_dataset(cfg)
    assert result["complete"], result["rejections"]
    assert set(explain_config(cfg)) == parameter_paths()


def test_public_export_is_allowlisted_and_evaluation_is_separate(tmp_path):
    bundle = tmp_path / "bundle"
    generate_dataset(resolve_config(name="quickstart", output=str(bundle)))
    # Simulate a future field added to a valid public bundle, including nested metadata.
    import clue_benchmark.public_api as api

    original = api.iter_cases

    def extended(*args):
        for row in original(*args):
            row["solution"] = "must never escape"
            if "constraint" in row:
                row["constraint"]["private_label"] = "must never escape"
            yield row

    from unittest.mock import patch

    with patch.object(api, "iter_cases", extended):
        export_public(bundle, tmp_path / "agent.jsonl")
    text = (tmp_path / "agent.jsonl").read_text()
    assert "must never escape" not in text
    assert "solution" not in text and "certificate" not in text
    assert set(inspect_case(bundle)) >= {"reports", "rules", "suspects"}

    def agent(observation):
        observation["reports"].clear()
        return {"kind": "abstain"}

    result = evaluate_agent(bundle, agent)
    assert result["episodes"][0]["sufficient_evidence"]
    with pytest.raises(FileExistsError):
        export_public(bundle, tmp_path / "agent.jsonl")
    with pytest.raises(SystemExit) as error:
        main(
            [
                "export-public",
                str(bundle),
                "--agent",
                "20",
                "--output",
                str(tmp_path / "bad"),
            ]
        )
    assert error.value.code == 2
    assert not (tmp_path / "bad").exists()


def test_report_escapes_untrusted_text_and_keeps_exact_source(tmp_path):
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {"episodes": [{"world_id": "w", "text": "<script>alert(1)</script>"}]}
        )
    )
    write_report(source, tmp_path / "report")
    rendered = (tmp_path / "report/index.html").read_text()
    assert "<script>" not in rendered and "&lt;script&gt;" in rendered
    assert source.read_bytes() == (tmp_path / "report/source.json").read_bytes()


def test_distributed_replay_is_offline(tmp_path, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("network is forbidden")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = replay_example("distributed-evidence", tmp_path / "replay")
    episodes = result["episodes"]
    assert result["model_calls"] == 0 and result["independent_worlds"] == 8
    assert sum(r["sufficient"] for r in episodes if r["condition"] == "complete") == 8
    assert (
        sum(r["sufficient"] for r in episodes if r["condition"] == "independent") == 0
    )
    assert sum(r["sufficient"] for r in episodes if r["condition"] == "sharing") == 8
    with pytest.raises(ValueError, match="exists"):
        replay_example("distributed-evidence", tmp_path / "replay")


def test_cli_presets_and_errors(capsys):
    assert main(["presets", "list"]) == 0
    assert "quickstart" in json.loads(capsys.readouterr().out)
    with pytest.raises(SystemExit) as error:
        main(["generate-dataset", "--preset", "quickstart", "--config", "missing.json"])
    assert error.value.code == 2


def test_rendering_preserves_literal_ids_quotes_and_unicode():
    from clue_benchmark.community_config import PresentationConfig
    from clue_benchmark.community_generation import render_report

    report = {
        "report_id": "r",
        "constraint": {
            "type": "unary_positive",
            "suspect": "S01",
            "attribute": "S01",
            "value": 'S01 "café"',
        },
    }
    rendered = render_report(
        report, {"display_names": {"S01": 'Person "α"'}}, PresentationConfig()
    )
    assert '"S01"' in rendered["text"]
    assert "café" in rendered["text"] and "α" in rendered["text"]
    assert rendered["constraint"] == report["constraint"]
    assert 'S01 \\"café\\"' in rendered["text"]


def test_docs_cover_every_parameter():
    from pathlib import Path

    reference = (
        Path(__file__).parents[1] / "docs/site/reference/parameters.md"
    ).read_text()
    assert all(f"## `{path}`" in reference for path in parameter_paths())


def test_historical_counts_recompute_without_pooling(tmp_path):
    from clue_benchmark.results import replay_results

    result = replay_results(tmp_path / "counts")
    studies = result["studies"]
    fresh = studies["flash-hard-scale"]["panels"]
    assert len(fresh) == 1
    assert fresh[0]["assigned"] == 48 and fresh[0]["independent_worlds"] == 48
    assert fresh[0]["correct"] == 9 and fresh[0]["abstentions"] == 11
    assert fresh[0]["wrong_with_sufficient_evidence"] == 28
    qwen = studies["qwen-sampled-screening"]["panels"]
    assert sum(p["assigned"] for p in qwen) == 72
    assert sum(p["valid_actions"] for p in qwen) == 67
    assert sum(p["supported_correct"] for p in qwen) == 22
    assert sum(p["wrong_with_sufficient_evidence"] for p in qwen) == 15
    assert sum(p["appropriate_abstentions"] for p in qwen) == 11
    assert sum(p["unsupported_answers"] for p in qwen) == 19
    assert sum(p["reused_receipts"] for p in qwen) == 3
    for dose, count in [(0, 2), (100, 3), (1000, 5)]:
        panel = next(
            p
            for p in studies["pilot"]["panels"]
            if p["arm"] == f"burden-4-noise-{dose}"
            and p["model"] == "gemini-3.5-flash-lite-low"
        )
        assert panel["assigned"] == panel["independent_worlds"] == 5
        assert panel["correct"] == count
