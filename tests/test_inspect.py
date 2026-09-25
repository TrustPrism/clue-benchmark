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

from clue_benchmark.dataset import write_jsonl
from clue_benchmark.inspect_adapter import clue_benchmark


@pytest.mark.parametrize("track", ["deduction", "investigation"])
def test_mock_model_can_submit_without_answer_leak(case, tmp_path, track):
    path = tmp_path / "case.jsonl"
    write_jsonl(path, [case])
    seen = []

    def output(messages, tools, choice, config):
        # Only model-visible content is checked; private scoring targets stay in the harness.
        text = " ".join(m.text for m in messages)
        for field in [
            '"solution"',
            '"world"',
            '"seed"',
            '"solver_fields"',
            '"necessary_for_uniqueness"',
        ]:
            assert field not in text
        seen.append(text)
        if track == "investigation" and len(seen) == 1:
            call = ToolCall(
                id="request", function="request_clue", arguments={"query_id": "invalid"}
            )
        else:
            call = ToolCall(
                id="answer",
                function="submit_answer",
                arguments={"suspect_id": case["solution"]["murderer"]},
            )
        return ModelOutput(
            model="mockllm",
            choices=[
                ChatCompletionChoice(
                    message=ChatMessageAssistant(content="", tool_calls=[call]),
                    stop_reason="tool_calls",
                )
            ],
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        )

    logs = eval(
        clue_benchmark(str(path), track),
        model="mockllm/model",
        model_args={"custom_outputs": output},
        display="none",
        log_dir=str(tmp_path / "logs"),
    )
    assert logs[0].status == "success", logs[0].error
    sample = logs[0].samples[0]
    assert sample.scores["exact_suspect"].value == 1
    assert len(seen) == (2 if track == "investigation" else 1)
    if track == "investigation":
        assert sample.metadata["benchmark_result"]["invalid_actions"] == 1


def test_mock_missing_answer_scores_zero(case, tmp_path):
    path = tmp_path / "case.jsonl"
    write_jsonl(path, [case])
    response = ModelOutput.from_content("mockllm", "I cannot decide.")
    response.usage = ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2)
    logs = eval(
        clue_benchmark(str(path)),
        model="mockllm/model",
        model_args={"custom_outputs": [response]},
        display="none",
        log_dir=str(tmp_path / "logs"),
    )
    assert logs[0].status == "success"
    assert logs[0].samples[0].scores["exact_suspect"].value == 0
