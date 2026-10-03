import copy

import pytest

pytest.importorskip("inspect_ai")
from inspect_ai import eval
from inspect_ai.model import (
    ChatCompletionChoice,
    ChatMessageAssistant,
    ModelOutput,
    ModelUsage,
)
from inspect_ai.tool import ToolCall

from clue_benchmark import Config, generate
from clue_benchmark.dataset import write_jsonl
from clue_benchmark.inspect_adapter import model_settings
from clue_benchmark.study import export_study, prepare_study, study_tasks


@pytest.mark.parametrize(
    "config",
    [
        {"internal_tools": {}},
        {"fallback_models": ["provider/other"]},
        {"extra_headers": {"example": "not-a-credential"}},
        {"parallel_tool_calls": True},
        {"max_tokens": 0},
        {"temperature": "high"},
    ],
)
def test_study_cannot_add_provider_tools_or_invalid_settings(config):
    with pytest.raises(ValueError):
        model_settings(config)


def test_mock_frozen_study_both_menus_and_missing_logs(case, tmp_path):
    dev = {**copy.deepcopy(case), "world_group": "dev-world"}
    test = {
        **generate(Config(mutation_steps=0), 17)["case"],
        "world_group": "test-world",
    }
    write_jsonl(tmp_path / "dev.jsonl", [dev])
    write_jsonl(tmp_path / "test.jsonl", [test])
    plan = prepare_study(
        tmp_path / "dev.jsonl",
        tmp_path / "test.jsonl",
        tmp_path,
        models=["mockllm/model"],
        repeats=1,
        topic_modes=("targeted", "attribute"),
    )

    def output(messages, tools, choice, config):
        text = " ".join(m.text for m in messages)
        for field in (
            '"solution"',
            '"world"',
            '"seed"',
            '"config"',
            '"solver_fields"',
            '"diagnostics"',
        ):
            assert field not in text
        return ModelOutput(
            model="mockllm",
            choices=[
                ChatCompletionChoice(
                    message=ChatMessageAssistant(
                        content="",
                        tool_calls=[
                            ToolCall(
                                id="answer",
                                function="submit_answer",
                                arguments={"suspect_id": test["solution"]["murderer"]},
                            )
                        ],
                    ),
                    stop_reason="tool_calls",
                )
            ],
            usage=ModelUsage(input_tokens=3, output_tokens=2, total_tokens=5),
        )

    logs = []
    for model, task in study_tasks(plan, tmp_path):
        logs.extend(
            eval(
                task,
                model=model,
                model_args={"custom_outputs": output},
                display="none",
                log_dir=str(tmp_path / "logs"),
            )
        )
    assert all(log.status == "success" for log in logs)
    result = export_study(plan, tmp_path, logs)
    assert result["manifest"]["expected_episodes"] == 17
    assert result["manifest"]["observed_samples"] == 17
    assert all(r["correct"] == 1 for r in result["episodes"])
    assert sum(s["tokens"]["total_tokens"] for s in result["summary"]) == 17 * 5
    assert len(result["paired_strategy_gaps"]) == 2
    assert all(
        r["agent_minus_random_schedule_budget_average"] == 0
        for r in result["paired_strategy_gaps"]
    )
    for row in result["episodes"]:
        if row["selection_policy"] == "random":
            assert row["spent"] > 0 and row["requests"] > 0
        if row["track"] == "deduction":
            assert row["spent"] == len(test["clues"])
    incomplete = export_study(plan, tmp_path, logs[:1])
    assert incomplete["manifest"]["expected_episodes"] == 17
    assert sum(r["correct"] for r in incomplete["episodes"]) == 1
    assert sum(r["error"] == "missing_log" for r in incomplete["episodes"]) == 16
    with pytest.raises(ValueError, match="duplicate sample"):
        export_study(plan, tmp_path, logs + logs[:1])
    changed = copy.deepcopy(logs[:1])
    changed[0].plan.config.temperature = 1
    with pytest.raises(ValueError, match="generation settings"):
        export_study(plan, tmp_path, changed)
    changed = copy.deepcopy(logs[:1])
    changed[0].eval.config.token_limit = 100
    with pytest.raises(ValueError, match="limits, protocol, or prompt"):
        export_study(plan, tmp_path, changed)


def test_mock_missing_answer_is_scored_and_token_usage_recorded(case, tmp_path):
    dev = {**copy.deepcopy(case), "world_group": "dev-world"}
    test = {
        **generate(Config(mutation_steps=0), 17)["case"],
        "world_group": "test-world",
    }
    write_jsonl(tmp_path / "dev.jsonl", [dev])
    write_jsonl(tmp_path / "test.jsonl", [test])
    plan = prepare_study(
        tmp_path / "dev.jsonl",
        tmp_path / "test.jsonl",
        tmp_path,
        ["mockllm/model"],
        repeats=1,
    )
    model, task = next(study_tasks(plan, tmp_path))
    response = ModelOutput.from_content("mockllm", "I cannot decide.")
    response.usage = ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2)
    logs = eval(
        task,
        model=model,
        model_args={"custom_outputs": [response]},
        display="none",
        log_dir=str(tmp_path / "logs"),
    )
    result = export_study(plan, tmp_path, logs)
    assert all(r["correct"] == 0 for r in result["episodes"])
    assert result["episodes"][0]["missing_answer"] is True
    assert result["episodes"][0]["tokens"]["total_tokens"] == 2


def test_provider_failure_is_kept_in_declared_denominator(case, tmp_path):
    dev = {**copy.deepcopy(case), "world_group": "dev-world"}
    test = {
        **generate(Config(mutation_steps=0), 17)["case"],
        "world_group": "test-world",
    }
    write_jsonl(tmp_path / "dev.jsonl", [dev])
    write_jsonl(tmp_path / "test.jsonl", [test])
    plan = prepare_study(
        tmp_path / "dev.jsonl",
        tmp_path / "test.jsonl",
        tmp_path,
        ["mockllm/model"],
        repeats=1,
    )
    model, task = next(study_tasks(plan, tmp_path))

    def failure(*args):
        raise RuntimeError("Synthetic provider failure")

    logs = eval(
        task,
        model=model,
        model_args={"custom_outputs": failure},
        display="none",
        log_dir=str(tmp_path / "logs"),
        fail_on_error=False,
        retry_on_error=0,
        max_retries=0,
    )
    result = export_study(plan, tmp_path, logs)
    assert result["manifest"]["expected_episodes"] == 9
    assert result["episodes"][0]["error"] == "model_error"
    assert all(row["correct"] == 0 for row in result["episodes"])
