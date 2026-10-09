"""Primary CLI, retained flat configurations and repository entry points."""

import ast
import json
from pathlib import Path

import pytest

from clue_benchmark import __version__
from clue_benchmark.cli import main


def test_dataset_commands_are_primary(capsys):
    with pytest.raises(SystemExit) as stopped:
        main(["--help"])
    assert stopped.value.code == 0
    help_text = capsys.readouterr().out
    assert "generate-dataset" in help_text and "run-community-evaluation" in help_text
    assert "run-study" not in help_text and "prepare-pilot" not in help_text
    with pytest.raises(SystemExit):
        main(["--version"])
    assert capsys.readouterr().out.strip() == __version__


def test_flat_generator_and_export_compatibility(tmp_path):
    config = tmp_path / "flat.json"
    config.write_text(json.dumps({"mutation_steps": 0}))
    bank = tmp_path / "bank.json"
    assert (
        main(
            ["generate", "--config", str(config), "--seed", "7", "--output", str(bank)]
        )
        == 0
    )
    assert main(["validate", str(bank)]) == 0
    public = tmp_path / "public.jsonl"
    assert main(["export", str(bank), "--output", str(public)]) == 0
    case = json.loads(public.read_text())
    assert set(case["clues"][0]) == {"clue_id", "text"}
    assert not set(case) & {"world", "solution", "murderer"}
    study = tmp_path / "study.json"
    assert main(["export", str(bank), "--format", "study", "--output", str(study)]) == 0
    assert json.loads(study.read_text())["states"][0]["world"]


def test_all_modules_serve_entry_points():
    root = Path(__file__).parents[1] / "src/clue_benchmark"
    dependencies = {}
    for path in root.glob("*.py"):
        dependencies[path.stem] = {
            node.module.split(".")[0]
            for node in ast.walk(ast.parse(path.read_text()))
            if isinstance(node, ast.ImportFrom) and node.level and node.module
        }
    referenced = {"__init__", "__main__"}
    pending = list(referenced)
    while pending:
        name = pending.pop()
        for dependency in dependencies[name]:
            assert dependency in dependencies, f"Missing package module: {dependency}"
            if dependency not in referenced:
                referenced.add(dependency)
                pending.append(dependency)
    assert referenced == set(dependencies), (
        "Remove modules unreachable from the public entry points"
    )
