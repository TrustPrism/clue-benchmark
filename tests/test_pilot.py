import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("inspect_ai")
pytest.importorskip("google.genai")

from clue_benchmark.config import digest
from clue_benchmark.dataset import read_cases
from clue_benchmark.ledger import AccountingStop, BudgetStop, Ledger, execution_lock
from clue_benchmark.pilot import PILOT_MODELS, prepare_pilot, select_pilot_worlds
from clue_benchmark.providers import (
    GoogleProvider,
    OllamaProvider,
    ProtocolError,
    Reply,
    UsageError,
    checked_usage,
)
from clue_benchmark.runner import execution_cases, run_study
from clue_benchmark.study import prepare_study, study_tasks, verify_study

ROOT = Path(__file__).resolve().parents[1]
LOCAL_ID = {
    "digest": "sha256:pinned",
    "quantization": "Q4_K_M",
    "ollama_version": "0.34.0",
    "num_ctx": 32768,
    "context_capacity": 262144,
}


@pytest.fixture(scope="module")
def pilot():
    return prepare_pilot(
        ROOT / "data/v0.3/private/dev.jsonl",
        ROOT / "data/v0.3/private/test.jsonl",
        ROOT,
        LOCAL_ID,
    )


def freeze(plan):
    plan.pop("plan_id", None)
    plan["plan_id"] = digest(plan)
    return plan


def small_plan(pilot, tmp_path, models=PILOT_MODELS):
    p = copy.deepcopy(pilot)
    p.pop("study_kind")
    p["models"] = list(models)
    p["selected_case_ids"] = p["selected_case_ids"][:2]
    p["conditions"] = [p["conditions"][0], p["conditions"][1], p["conditions"][5]]
    p["execution_directory"] = str(tmp_path / "execution")
    return freeze(p)


def test_deterministic_world_selection_and_pairs(pilot):
    cases = read_cases(ROOT / "data/v0.3/private/dev.jsonl")
    a = select_pilot_worlds(cases)
    assert a == select_pilot_worlds(list(reversed(cases)))
    assert a != select_pilot_worlds(cases, seed=1)
    assert len(a) == 24
    for size in (4, 8, 12):
        worlds = {c["world_group"] for c in a if len(c["suspects"]) == size}
        assert len(worlds) == 4
        for w in worlds:
            pair = [c for c in a if c["world_group"] == w]
            assert len(pair) == 2
            assert sorted(len(c["clues"]) for c in pair) == [size + 4, size + 8]
    assert pilot["selected_case_ids"] == [c["case_id"] for c in a]
    assert len(pilot["conditions"]) == 9
    assert pilot["episodes_per_model"] == 216
    assert pilot["expected_episodes"] == 648
    assert pilot["datasets"]["test"]["cases"] == 744
    verify_study(pilot, ROOT)


def test_missing_pair_and_test_data_rejected():
    cases = read_cases(ROOT / "data/v0.3/private/dev.jsonl")
    with pytest.raises(ValueError, match="paired"):
        select_pilot_worlds(cases[1:])
    cases[0]["split"] = "test"
    with pytest.raises(ValueError, match="development"):
        select_pilot_worlds(cases)


def test_pilot_settings_and_full_study_unchanged(pilot):
    for m in PILOT_MODELS:
        settings = pilot["per_model_settings"][m]
        assert settings["temperature"] == 1.0
        assert settings["max_tokens"] == 4096
        assert settings["max_retries"] == 0
        assert settings["parallel_tool_calls"] is False
    assert pilot["time_limit_seconds"] == 600
    assert pilot["token_limit"] == 32768
    assert all(
        pilot["provider_settings"][m]["thinking_level"] == "medium"
        for m in PILOT_MODELS[:2]
    )
    assert pilot["provider_settings"][PILOT_MODELS[2]]["think"] is True
    tasks = list(study_tasks(pilot, ROOT))
    assert len(tasks) == 27
    assert all(len(t.dataset) == 24 for _, t in tasks)
    assert all(t.time_limit == 600 for _, t in tasks)
    full = prepare_study(
        ROOT / "data/v0.3/private/dev.jsonl",
        ROOT / "data/v0.3/private/test.jsonl",
        ROOT,
        ["mockllm/model"],
    )
    assert full["execution_split"] == "test"
    assert full["episodes_per_model"] == 744 * 9 * 3
    assert full["generation_config"]["temperature"] == 0
    assert full["time_limit_seconds"] == 120


def test_dry_run_never_constructs_provider_or_ledger(pilot, tmp_path):
    p = small_plan(pilot, tmp_path)

    def forbidden(*args):
        pytest.fail("dry run attempted provider construction")

    result = run_study(p, ROOT, dry_run=True, provider_factory=forbidden)
    assert result["generation_calls"] == 0
    assert result["expected_episodes"] == 18
    assert not (tmp_path / "execution").exists()
    p["execution_split"] = "test"
    p["study_kind"] = "exploratory-development-pilot"
    freeze(p)
    with pytest.raises(ValueError):
        execution_cases(p, ROOT)


class FakeProvider:
    def __init__(self, name, mode="valid"):
        self.name = name
        self.paid = name.startswith("google/")
        self.mode = mode
        self.calls = 0
        self.starts = []
        self.settings_seen = []

    def start(self, prompt):
        messages = [{"role": "user", "content": prompt}]
        self.starts.append(messages)
        return messages

    def add_results(self, messages, reply, results):
        messages.append(reply.assistant)
        messages.append({"role": "tool", "content": json.dumps(results)})

    def generate(self, messages, tools, max_output, timeout):
        self.calls += 1
        assert max_output <= 4096 and timeout <= 600
        text = json.dumps(messages)
        for forbidden in (
            '"solution"',
            '"world"',
            '"seed"',
            '"diagnostics"',
            '"solver_fields"',
            "SECRET",
        ):
            assert forbidden not in text
        probe = "Protocol compatibility probe" in text
        if probe:
            name = tools[0]
            args = (
                {"query_id": "q001"}
                if name == "request_clue"
                else {"suspect_id": "S01"}
            )
            if self.mode == "bad_probe":
                return Reply({}, [], checked_usage(2, 2, 1, 4), "fake")
        else:
            if self.mode == "missing_usage":
                return Reply({}, [], None, "fake")
            if self.mode == "timeout":
                raise TimeoutError()
            if self.mode == "quota":
                exc = RuntimeError("SECRET must never enter logs")
                exc.code = 429
                raise exc
            if "request_clue" in tools and not any(
                m["role"] == "tool" for m in messages
            ):
                observation = json.loads(messages[0]["content"].split("\n", 1)[1])
                name, args = (
                    "request_clue",
                    {"query_id": observation["queries"][0]["query_id"]},
                )
            else:
                name, args = (
                    "submit_answer",
                    {
                        "suspect_id": "invalid"
                        if self.mode == "invalid_answer"
                        else "S01"
                    },
                )
        return Reply(
            {"role": "assistant", "content": "native function call"},
            [(name, args)],
            checked_usage(2, 2, 1, 4),
            "fake-version",
        )


def factory_for(mode="valid", seen=None):
    providers = {} if seen is None else seen

    def factory(model, settings, identity):
        provider = FakeProvider(model, mode)
        provider.settings_seen.append(settings)
        providers[model] = provider
        return provider

    return factory


def test_native_mock_execution_and_resume_without_duplicates(pilot, tmp_path):
    plan = small_plan(pilot, tmp_path)
    providers = {}
    result = run_study(plan, ROOT, provider_factory=factory_for(seen=providers))
    assert result["manifest"]["status"] == "complete"
    assert len(result["episodes"]) == 18
    assert all(r["completion"] for r in result["episodes"])
    assert any(
        r["spent"] and r["requests"]
        for r in result["episodes"]
        if r["selection_policy"] == "agent"
    )
    assert all(p.calls == 2 + 8 for p in providers.values())
    assert result["ledger"]["settled_usd"] > 0
    assert all(p.starts[0] is not p.starts[1] for p in providers.values())
    again = {}
    resumed = run_study(plan, ROOT, provider_factory=factory_for(seen=again))
    assert all(p.calls == 0 for p in again.values())
    assert resumed["episodes"] == result["episodes"]
    assert resumed["ledger"]["requests"] == result["ledger"]["requests"]


@pytest.mark.parametrize("model", [PILOT_MODELS[0], PILOT_MODELS[2]])
def test_invalid_final_answers_visible_and_exact_scored(pilot, tmp_path, model):
    plan = small_plan(pilot, tmp_path, [model])
    result = run_study(plan, ROOT, provider_factory=factory_for("invalid_answer"))
    assert all(
        r["correct"] == 0 and r["invalid_submission"] and r["invalid_actions"] == 1
        for r in result["episodes"]
    )


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("missing_usage", "missing_usage"),
        ("timeout", "timeout"),
        ("quota", "quota_error"),
    ],
)
@pytest.mark.parametrize("model", [PILOT_MODELS[0], PILOT_MODELS[2]])
def test_provider_failures_and_accounting_stop(pilot, tmp_path, mode, expected, model):
    plan = small_plan(pilot, tmp_path, [model])
    first = run_study(plan, ROOT, provider_factory=factory_for(mode))
    assert first["manifest"]["status"] == "incomplete"
    assert any(r["error"] == expected for r in first["episodes"])
    assert first["ledger"]["requests"][-1]["status"] == "uncertain"
    seen = {}
    resumed = run_study(plan, ROOT, provider_factory=factory_for(seen=seen))
    assert resumed["manifest"]["stop_reason"] == "accounting_stopped"
    assert not seen
    assert "SECRET" not in json.dumps(resumed)


def test_budget_exhaustion_before_request_and_persisted_resume(pilot, tmp_path):
    plan = small_plan(pilot, tmp_path, PILOT_MODELS[:2])
    plan["spending"]["combined_google_usd"] = 0.01
    freeze(plan)
    seen = {}
    result = run_study(plan, ROOT, provider_factory=factory_for(seen=seen))
    assert result["manifest"]["stop_reason"] == "budget_stopped"
    assert all(p.calls == 0 for p in seen.values())
    assert result["ledger"]["committed_usd"] == 0
    assert len(result["episodes"]) == 12
    assert all(r["correct"] == 0 for r in result["episodes"])


def test_failed_compatibility_stops_model_and_remains_separate(pilot, tmp_path):
    plan = small_plan(pilot, tmp_path)
    result = run_study(plan, ROOT, provider_factory=factory_for("bad_probe"))
    assert result["manifest"]["dispatched_episodes"] == 0
    assert len(result["episodes"]) == 18
    assert len(result["ledger"]["requests"]) == 3
    assert all(r["phase"] == "compatibility" for r in result["ledger"]["requests"])
    seen = {}
    run_study(plan, ROOT, provider_factory=factory_for(seen=seen))
    assert not seen


def test_ledger_durable_reservations_and_identity(pilot, tmp_path):
    plan = small_plan(pilot, tmp_path)
    path = tmp_path / "ledger.sqlite3"
    ledger = Ledger(path, plan)
    ledger.reserve("e", PILOT_MODELS[0], "scored", 100)
    assert ledger.begin_episode("e")
    ledger.close()
    ledger = Ledger(path, plan)
    assert ledger.committed() == 100
    with pytest.raises(AccountingStop):
        ledger.guard()
    assert not ledger.begin_episode("e")
    ledger.close()
    other = copy.deepcopy(plan)
    other["plan_id"] = "changed"
    with pytest.raises(ValueError, match="different manifest"):
        Ledger(path, other)
    with execution_lock(tmp_path / "lock"):
        with pytest.raises(RuntimeError, match="another"):
            with execution_lock(tmp_path / "lock"):
                pass


def test_reservation_cannot_overrun_ceiling(pilot, tmp_path):
    plan = small_plan(pilot, tmp_path)
    ledger = Ledger(tmp_path / "ledger", plan)
    with pytest.raises(BudgetStop):
        ledger.reserve("e", PILOT_MODELS[0], "scored", 50000001)
    rid = ledger.reserve("e", PILOT_MODELS[0], "scored", 2)
    with pytest.raises(AccountingStop):
        ledger.settle(rid, checked_usage(1, 1), 3)
    with pytest.raises(AccountingStop):
        ledger.guard()
    ledger.close()


@pytest.mark.parametrize("provider_name", ["google", "ollama"])
def test_native_transport_tools_settings_and_usage(monkeypatch, provider_name):
    settings = {
        "temperature": 1.0,
        "thinking_level": "medium",
        "max_tokens": 4096,
        "think": True,
        "top_p": 0.95,
        "top_k": 20,
        "presence_penalty": 1.5,
        "repeat_penalty": 1.0,
    }
    seen = []
    if provider_name == "google":
        from google import genai
        from google.genai import types

        monkeypatch.setenv("GOOGLE_API_KEY", "SECRET")
        signature = b"opaque-thought-signature"
        assistant = types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        name="request_clue", args={"query_id": "q001"}
                    ),
                    thought_signature=signature,
                )
            ],
        )

        def generate(**kwargs):
            seen.append(kwargs)
            return SimpleNamespace(
                usage_metadata=SimpleNamespace(
                    prompt_token_count=2,
                    candidates_token_count=2,
                    thoughts_token_count=1,
                    total_token_count=5,
                ),
                candidates=[SimpleNamespace(content=assistant)],
                model_version="returned-version",
            )

        model = SimpleNamespace(
            get=lambda **kw: SimpleNamespace(
                input_token_limit=1048576,
                output_token_limit=65536,
                supported_actions=["generateContent"],
                name="models/gemini-3.8-flash",
                version="stable",
            ),
            generate_content=generate,
            count_tokens=lambda **kwargs: SimpleNamespace(total_tokens=2),
        )

        def client(**kwargs):
            assert kwargs["http_options"].retry_options.attempts == 1
            return SimpleNamespace(models=model)

        monkeypatch.setattr(genai, "Client", client)
        provider = GoogleProvider(
            PILOT_MODELS[0], settings, {"context_capacity": 1048576}
        )
    else:
        import clue_benchmark.providers as module

        monkeypatch.setattr(module, "ollama_identity", lambda m: LOCAL_ID)

        def local(endpoint, payload, timeout):
            seen.append(payload)
            return {
                "model": "qwen3.5:9b",
                "prompt_eval_count": 2,
                "eval_count": 3,
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "request_clue",
                                "arguments": {"query_id": "q001"},
                            }
                        }
                    ],
                },
            }

        monkeypatch.setattr(module, "local_json", local)
        provider = OllamaProvider(PILOT_MODELS[2], settings, LOCAL_ID)
    messages = provider.start("public protocol values")
    reply = provider.generate(messages, ["request_clue"], 4096, 600)
    assert reply.calls == [("request_clue", {"query_id": "q001"})]
    assert reply.usage["total_tokens"] == 5
    assert provider.input_tokens_bound(messages, ["request_clue"]) > 0
    provider.add_results(
        messages, reply, [("request_clue", {"clue": {"text": "Allowed observation"}})]
    )
    if provider_name == "google":
        config = seen[0]["config"]
        assert config.automatic_function_calling.disable
        assert config.thinking_config.thinking_level.value == "MEDIUM"
        assert config.http_options.retry_options.attempts == 1
        assert messages[1] is assistant
        assert messages[1].parts[0].thought_signature == signature
    else:
        assert seen[0]["think"] is True
        assert seen[0]["options"]["num_ctx"] == 32768
        assert seen[0]["stream"] is False
        assert messages[-1]["role"] == "tool"


@pytest.mark.parametrize("values", [(None, 1), (1, None), (-1, 1), (1, True)])
def test_missing_usage_is_never_assumed_zero(values):
    with pytest.raises(UsageError):
        checked_usage(*values)


def test_runtime_drift_prevents_native_execution(monkeypatch):
    import clue_benchmark.providers as module

    monkeypatch.setattr(
        module, "ollama_identity", lambda m: {**LOCAL_ID, "digest": "changed"}
    )
    with pytest.raises(ProtocolError, match="drift"):
        OllamaProvider(PILOT_MODELS[2], {}, LOCAL_ID)


def test_source_amendment_preserves_cost_and_episode_identity(pilot, tmp_path):
    from clue_benchmark.amendment import amend_ledger
    from clue_benchmark.dataset import atomic_json

    previous = small_plan(pilot, tmp_path, PILOT_MODELS[:1])
    output = Path(previous["execution_directory"])
    ledger = Ledger(output / "ledger.sqlite3", previous)
    rid = ledger.reserve("fixed-episode", PILOT_MODELS[0], "scored", 100)
    ledger.settle(rid, checked_usage(1, 1), 1)
    ledger.begin_episode("fixed-episode")
    ledger.finish_episode(
        "fixed-episode",
        {"correct": 0, "error": "token_limit", "source_plan_id": "original-source"},
    )
    ledger.model_status(PILOT_MODELS[0], "accounting_stopped", {"error": "maintenance"})
    ledger.db.execute(
        "CREATE TRIGGER maintenance_stop BEFORE INSERT ON requests BEGIN SELECT RAISE(ABORT,'maintenance'); END"
    )
    ledger.db.commit()
    atomic_json(
        output / "logs" / (digest(PILOT_MODELS[0]) + "-compatibility.json"),
        {"compatible": True},
    )
    ledger.close()
    amended = copy.deepcopy(previous)
    amended["episode_id_namespace"] = previous["plan_id"]
    amended["execution_amendment"] = {
        "previous_plan_id": previous["plan_id"],
        "reason": "Replace byte estimate with native counts",
    }
    freeze(amended)
    changed = copy.deepcopy(amended)
    changed["spending"]["combined_google_usd"] = 49
    freeze(changed)
    with pytest.raises(ValueError, match="cannot change"):
        amend_ledger(previous, changed, ROOT)
    result = amend_ledger(previous, amended, ROOT)
    assert result["preserved_episodes"] == 1
    assert result["preserved_committed_usd"] == 0.000001
    ledger = Ledger(output / "ledger.sqlite3", amended)
    assert not ledger.begin_episode("fixed-episode")
    assert ledger.model(PILOT_MODELS[0])["status"] == "compatible"
    assert ledger.episodes()["fixed-episode"]["source_plan_id"] == "original-source"
    ledger.guard()
    ledger.close()


def test_google_count_tokens_uses_real_developer_sdk_schema(monkeypatch):
    import httpx
    from google.genai import types

    seen = []

    def handle(request):
        seen.append(request)
        if str(request.url).endswith(":countTokens"):
            body = json.loads(request.content)
            assert "tools" not in body
            assert "generateContentRequest" not in body
            return httpx.Response(200, json={"totalTokens": 2})
        return httpx.Response(
            200,
            json={
                "name": "models/gemini-3.8-flash",
                "version": "stable",
                "inputTokenLimit": 1048576,
                "outputTokenLimit": 65536,
                "supportedGenerationMethods": ["generateContent"],
            },
        )

    monkeypatch.setenv("GOOGLE_API_KEY", "SECRET")
    from google import genai

    real_client = genai.Client

    def client(**kwargs):
        kwargs["http_options"].httpx_client = httpx.Client(
            transport=httpx.MockTransport(handle)
        )
        return real_client(**kwargs)

    monkeypatch.setattr(genai, "Client", client)
    provider = GoogleProvider(
        PILOT_MODELS[0], {"max_tokens": 4096}, {"context_capacity": 1048576}
    )
    provider.last_usage = None
    provider.last_result_bound = 0
    messages = [
        types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        name="request_clue", args={"query_id": "q001"}
                    ),
                    thought_signature=b"opaque" * 20000,
                )
            ],
        )
    ]
    assert provider.input_tokens_bound(messages, ["request_clue"]) < 1024
    assert len(seen) == 2
    provider.last_usage = checked_usage(10000, 2000, 1800)
    provider.last_result_bound = 512
    assert provider.input_tokens_bound(messages, ["request_clue"]) >= 12768
