"""Community generation contracts, exact semantics, streaming and dispatch tests."""

import json
import tracemalloc
from dataclasses import replace

import pytest

from clue_benchmark.community_bundle import (
    file_hash,
    generate_dataset,
    iter_cases,
    rows,
    validate_dataset,
)
from clue_benchmark.community_config import CommunityConfig
from clue_benchmark.community_evaluation import (
    Ledger,
    forward_evidence,
    prepare_evaluation,
    run_evaluation,
)
from clue_benchmark.community_generation import (
    _report,
    generate_case,
    iter_allocations,
    score,
)
from clue_benchmark.community_semantics import (
    Budget,
    coalition_certificate,
    evaluate,
    exhaustive,
    minimum_subset,
)
from clue_benchmark.native_transport import NativeTransport
from clue_benchmark.provider_events import require_funding
from clue_benchmark.solver import Unresolved


def tiny():
    clues = [
        dict(type="crime_positive", attribute="x", value="1"),
        dict(type="unary_positive", suspect="A", attribute="x", value="0"),
    ]
    return {
        "suspects": ["A", "B"],
        "domains": {"x": ["0", "1"]},
        "solution": {"murderer": "B", "world": {"A": {"x": "0"}, "B": {"x": "1"}}},
        "assignment_mode": "repeated",
        "corruption_allowance": 0,
        "false_report_count": 0,
        "reports": [_report(c) for c in clues],
        "agent_count": 2,
        "nuisance_count": 0,
        "world_id": "tiny",
    }


def cfg(tmp_path, **overrides):
    value = {
        "puzzle": {"config": {"mutation_steps": 0}},
        "dataset": {
            "seed": 7,
            "output_directory": str(tmp_path),
            "certification_seconds": 30,
        },
    }
    for key, override in overrides.items():
        value.setdefault(key, {}).update(override)
    return CommunityConfig.from_dict(value)


@pytest.mark.parametrize("mode", ["repeated", "distinct"])
@pytest.mark.parametrize("allowance", [0, 1, 2])
def test_three_semantics_agree(mode, allowance):
    case = tiny()
    case["assignment_mode"] = mode
    case["corruption_allowance"] = allowance
    pool = case["reports"] + [
        _report(
            dict(type="suspect_same_as", suspect="A", other_suspect="B", attribute="x")
        ),
        _report(dict(type="unary_negative", suspect="B", attribute="x", value="0")),
    ]
    for mask in range(1 << len(pool)):
        reports = [r for i, r in enumerate(pool) if mask & (1 << i)]
        expected = exhaustive(case, reports)
        assert evaluate(case, reports)["candidates"] == expected
        assert evaluate(case, reports, engine="production")["candidates"] == expected


def test_existential_and_negative_encodings():
    case = tiny()
    case["domains"]["y"] = ["0", "1"]
    case["solution"]["world"]["A"]["y"] = "0"
    case["solution"]["world"]["B"]["y"] = "1"
    pool = [
        _report(dict(type=t, attr1="x", val1="0", attr2="y", val2="1"))
        for t in ("indirect_positive", "indirect_negative")
    ]
    for allowance in (0, 1, 2):
        case["corruption_allowance"] = allowance
        for reports in (pool[:1], pool[1:], pool, case["reports"] + pool):
            assert evaluate(case, reports)["candidates"] == exhaustive(case, reports)
            assert evaluate(case, reports, engine="production")[
                "candidates"
            ] == exhaustive(case, reports)


def test_distinct_rule_changes_answer_and_copies_not_votes():
    case = tiny()
    same = _report(
        dict(type="suspect_same_as", suspect="A", other_suspect="B", attribute="x")
    )
    assert evaluate(case, [same])["candidates"] == ["A", "B"]
    case["assignment_mode"] = "distinct"
    assert evaluate(case, [same])["candidates"] == []
    case["corruption_allowance"] = 1
    assert evaluate(case, [same, same, same])["candidates"] == ["A", "B"]


def test_coalitions_and_witnesses():
    case = tiny()
    allocation = {r["report_id"]: [i] for i, r in enumerate(case["reports"])}
    cert = coalition_certificate(case, allocation)
    assert cert["minimum_size"] == 2
    assert cert["minimal_sufficient_coalitions"] == [[0, 1]]
    assert all(
        len(c["witnesses"]) > 1 for c in cert["coalitions"] if not c["sufficient"]
    )
    case["agent_count"] = 3
    allocation = {
        case["reports"][0]["report_id"]: [0],
        case["reports"][1]["report_id"]: [1, 2],
    }
    assert coalition_certificate(case, allocation)["minimal_sufficient_coalitions"] == [
        [0, 1],
        [0, 2],
    ]


def test_corruption_multicover_minimum_and_redundant_shortcut():
    case = tiny()
    assert minimum_subset(case)["upper_bound"] == 2
    case["reports"].append(
        _report(dict(type="crime_different_from", suspect="A", attribute="x"))
    )
    # This is entailed by the original core, but establishes the target alone.
    assert minimum_subset(case)["upper_bound"] == 1
    case["corruption_allowance"] = 1
    assert minimum_subset(case)["upper_bound"] == 3


@pytest.mark.parametrize(
    "bad",
    [
        {"evidence": {"false_reports": 3}},
        {"evidence": {"false_reports": 2, "corruption_allowance": 1}},
        {"distribution": {"agent_count": 9}},
        {"distribution": {"agent_count": 1}},
        {"evidence": {"answerability": "ambiguous"}},
        {"puzzle": {"assignment_mode": "distinct", "config": {"suspect_count": 5}}},
        {"puzzle": {"family": "branching", "assignment_mode": "distinct"}},
        {"dataset": {"splits": {"development": 0.5}}},
        {"presentation": {"minimum_words": 20, "maximum_words": 10}},
    ],
)
def test_invalid_configuration(bad):
    with pytest.raises(ValueError):
        CommunityConfig.from_dict(bad)


def test_failure_does_not_change_requests(tmp_path):
    config = cfg(tmp_path, distribution={"per_agent_quotas": [1, 1]})
    result = generate_case(config, 7)
    assert result["status"] == "rejected"
    assert "quotas" in result["diagnostics"]["reason"]
    with pytest.raises(Unresolved):
        evaluate(tiny(), budget=Budget(0))


@pytest.mark.parametrize("false_reports", [0, 1, 2])
def test_generated_recoverable_corruption(tmp_path, false_reports):
    config = cfg(
        tmp_path,
        puzzle={
            "config": {
                "suspect_count": 2,
                "domains": {f"a{i}": ["0", "1"] for i in range(6)},
                "clue_count": 18,
                "enabled_types": ["unary_positive", "crime_positive"],
                "mutation_steps": 0,
                "max_attempts": 2,
            }
        },
        evidence={"false_reports": false_reports},
        distribution={"agent_count": 1, "minimum_coalition_size": 1},
    )
    result = generate_case(config, 7)
    assert result["status"] == "ok", result
    assert len(result["certificate"]["false_report_ids"]) == false_reports
    assert result["certificate"]["candidates"] == [
        result["case"]["solution"]["murderer"]
    ]
    assert result["certificate"]["minimum_subset"]["status"] == "exact"


@pytest.mark.parametrize("family", ["equality_tree", "branching"])
def test_constructed_families(tmp_path, family):
    config = cfg(
        tmp_path,
        puzzle={"family": family, "config": {"clue_count": 4, "mutation_steps": 0}},
    )
    result = generate_case(config, 7)
    assert result["status"] == "ok", result
    assert result["certificate"]["minimum_subset"]["upper_bound"] == 4


def test_distinct_generation(tmp_path):
    result = generate_case(cfg(tmp_path, puzzle={"assignment_mode": "distinct"}), 7)
    assert result["status"] == "ok", result
    world = result["case"]["solution"]["world"]
    assert all(
        len({w[a] for w in world.values()}) == 4 for a in result["case"]["domains"]
    )


def test_entailed_generation_and_presentation(tmp_path):
    config = cfg(
        tmp_path,
        evidence={"entailed_clues": 1, "irrelevant_records": 4},
        presentation={
            "theme": "investigation",
            "template": "expanded",
            "minimum_words": 500,
        },
    )
    result = generate_case(config, 7)
    assert result["status"] == "ok", result
    assert len(result["case"]["reports"]) == 9
    assert result["case"]["presentation_metrics"]["words"] == 500
    quotas = [0, 0]
    for _, owners in iter_allocations(result["case"], result["partition"]):
        for a in owners:
            quotas[a] += 1
    assert quotas == result["partition"]["per_agent_quotas"]


def test_bundle_public_boundaries_resume_and_worker_order(tmp_path):
    one = cfg(tmp_path / "one", dataset={"count": 2})
    two = cfg(tmp_path / "two", dataset={"count": 2, "workers": 2})
    first = generate_dataset(one)
    second = generate_dataset(two)
    assert first["complete"] and second["complete"]
    assert first["files"] == second["files"]
    assert generate_dataset(one)["files"] == first["files"]
    assert validate_dataset(one.dataset.output_directory)["status"] == "verified"
    public = list(iter_cases(one.dataset.output_directory, agent_id=0))
    assert not any(
        set(r)
        & {"solution", "false_report_ids", "certificate", "minimum_subset", "coalition"}
        for r in public
    )
    changed = replace(
        one, presentation=replace(one.presentation, theme="investigation")
    )
    with pytest.raises(ValueError, match="identity changed"):
        generate_dataset(changed)


def test_structural_holdout_and_schema_hashes(tmp_path):
    config = cfg(
        tmp_path,
        puzzle={"family": "branching", "config": {"clue_count": 4}},
        dataset={"holdout_families": ["branching"]},
    )
    manifest = generate_dataset(config)
    assert manifest["worlds"][0]["split"] == "transfer"
    with (tmp_path / "cases.jsonl").open("a") as f:
        f.write("{}\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_dataset(tmp_path)


@pytest.mark.parametrize("mutation", ["ownership", "text", "nuisance"])
def test_recomputed_hashes_do_not_replace_semantic_validation(tmp_path, mutation):
    assert generate_dataset(cfg(tmp_path, evidence={"irrelevant_records": 2}))[
        "complete"
    ]
    name = "partitions.jsonl" if mutation == "ownership" else "cases.jsonl"
    path = tmp_path / name
    records = list(rows(path))
    if mutation == "ownership":
        records[0]["owners"] = [0, 1]
    elif mutation == "text":
        records[1]["text"] = "The answer is someone else."
    else:
        row = next(
            r
            for r in records
            if r.get("constraint", {}).get("type") == "record_positive"
        )
        row["constraint"]["value"] = "1"
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][name] = file_hash(path)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        validate_dataset(tmp_path)


def test_presentation_variants_preserve_world_and_split(tmp_path):
    manifests = []
    for i, (theme, order, template) in enumerate(
        (("mystery", "canonical", "compact"), ("investigation", "reverse", "expanded"))
    ):
        config = cfg(
            tmp_path / str(i),
            presentation={
                "theme": theme,
                "naming_seed": i,
                "clue_order": order,
                "template": template,
            },
        )
        manifest = generate_dataset(config)
        assert validate_dataset(config.dataset.output_directory)["status"] == "verified"
        manifests.append(manifest)
    a, b = (m["worlds"][0] for m in manifests)
    assert a["world_id"] == b["world_id"] and a["split"] == b["split"]
    assert a["presentation_id"] != b["presentation_id"]


def test_tokenizer_contract_and_ambiguous_bundle(tmp_path):
    def tokenizer(text):
        return text.split()

    tokenizer.identity = "test-whitespace-1"
    configuration = cfg(tmp_path / "tokens", presentation={"minimum_tokens": 1})
    with pytest.raises(ValueError, match="token bounds"):
        generate_dataset(configuration)
    manifest = generate_dataset(configuration, tokenizer)
    assert manifest["complete"] and manifest["metrics"][0]["tokens"] > 0
    tokenizer.identity = "different-1"
    with pytest.raises(ValueError, match="identity changed"):
        generate_dataset(configuration, tokenizer)
    ambiguous = cfg(
        tmp_path / "ambiguous",
        evidence={"false_reports": 1, "answerability": "ambiguous"},
        distribution={"minimum_coalition_size": None},
    )
    assert generate_dataset(ambiguous)["complete"]
    assert (
        validate_dataset(ambiguous.dataset.output_directory)["cases"][0]["status"]
        == "verified_ambiguous"
    )


def test_corrupted_preset_bundle_survives_report_shuffle(tmp_path):
    from pathlib import Path

    value = json.loads(
        (Path(__file__).parents[1] / "examples/corrupted.json").read_text()
    )
    value["dataset"]["output_directory"] = str(tmp_path)
    assert generate_dataset(CommunityConfig.from_dict(value))["complete"]
    assert validate_dataset(tmp_path)["cases"][0]["status"] == "verified_unique"


def test_50000_streaming_records(tmp_path):
    config = cfg(
        tmp_path, evidence={"irrelevant_records": 49992}, dataset={"large_corpus": True}
    )
    tracemalloc.start()
    try:
        manifest = generate_dataset(config)
        assert manifest["complete"]
        assert (
            sum(r["kind"] == "report" for r in rows(tmp_path / "cases.jsonl")) == 50000
        )
        assert validate_dataset(tmp_path)["status"] == "verified"
        _, peak = tracemalloc.get_traced_memory()
        assert peak < 24 * 1024 * 1024
    finally:
        tracemalloc.stop()
    assert manifest["metrics"][0]["necessary_evidence"]["upper_bound"] < 50000


def model():
    return {
        "id": "fixture",
        "vendor": "openai",
        "model": "explicit-fixture",
        "settings": {"max_output_tokens": 100},
        "context_tokens": 100000,
        "input_microdollars_per_million_tokens": 1000000,
        "output_microdollars_per_million_tokens": 2000000,
    }


def auth(plan):
    return {
        "schema_version": "clue-community-authorization-1",
        "plan_id": plan["plan_id"],
        "approved_by": "test fixture only",
        "approved_at": "2026-10-09",
        "spending_ceiling_microdollars": plan["spending_ceiling_microdollars"],
        "max_requests": plan["max_requests"],
    }


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / "bundle"
    assert generate_dataset(cfg(root))["complete"]
    return root


def reply(target, usage=True):
    raw = {
        "model": "explicit-fixture",
        "status": "completed",
        "output": [
            {
                "type": "function_call",
                "name": "answer",
                "arguments": json.dumps({"target": target}),
            }
        ],
    }
    if usage:
        raw["usage"] = {
            "input_tokens": 100,
            "output_tokens": 10,
            "total_tokens": 110,
            "output_tokens_details": {"reasoning_tokens": 0},
        }
    return raw


def test_dry_run_has_no_credentials_or_calls(bundle, tmp_path, monkeypatch):
    monkeypatch.setattr(
        NativeTransport, "_request", lambda *_: pytest.fail("network called")
    )
    plan = prepare_evaluation(bundle, [model()], spending_ceiling_microdollars=1000000)
    result = run_evaluation(plan, bundle, tmp_path / "run")
    assert result["network_calls"] == 0 and result["expected_requests"] == 4
    assert not (tmp_path / "run" / "requests.sqlite").exists()
    with pytest.raises(PermissionError):
        run_evaluation(plan, bundle, tmp_path / "run", dry_run=False)
    with pytest.raises(PermissionError):
        require_funding()
    with pytest.raises(PermissionError):
        NativeTransport("openai")({})


def test_public_forwarding_adapter_and_delivery_checks(bundle, tmp_path):
    def adapter(header, reports, ownership, limits):
        assert not set(header) & {"solution", "certificate", "false_report_ids"}
        assert all("text" in r and "truth" not in r for r in reports)
        views = [[], []]
        for rid, owners in ownership:
            for agent in owners:
                views[agent].append(rid)
        return {"evidence": views, "messages": []}

    adapter.identity = "test-private-only-1"
    plan = prepare_evaluation(
        bundle,
        [model()],
        conditions=["sharing"],
        forwarding_policy_identity=adapter.identity,
    )
    assert (
        run_evaluation(plan, bundle, tmp_path / "run", forwarding_policy=adapter)[
            "network_calls"
        ]
        == 0
    )
    with pytest.raises(ValueError, match="adapter identity"):
        run_evaluation(plan, bundle, tmp_path / "run")

    def invalid(header, reports, ownership, limits):
        return {"evidence": [["forged-report"], []], "messages": []}

    invalid.identity = adapter.identity
    with pytest.raises(ValueError, match="undelivered"):
        run_evaluation(plan, bundle, tmp_path / "run", forwarding_policy=invalid)


def test_mock_live_and_no_retry_resume(bundle, tmp_path):
    plan = prepare_evaluation(bundle, [model()], spending_ceiling_microdollars=1000000)
    calls = []

    def transport(payload):
        calls.append(payload)
        return reply("S01")

    output = tmp_path / "run"
    result = run_evaluation(
        plan,
        bundle,
        output,
        dry_run=False,
        authorization=auth(plan),
        transports={"fixture": transport},
    )
    assert result["complete"] and len(calls) == 4
    assert len(result["episodes"]) == 4
    assert all(e["calls"] == 1 for e in result["episodes"])
    run_evaluation(
        plan,
        bundle,
        output,
        dry_run=False,
        authorization=auth(plan),
        transports={"fixture": transport},
    )
    assert len(calls) == 4


@pytest.mark.parametrize("tool_tokens", [None, 1])
def test_google_omitted_zero_thinking_settles_once_and_tool_usage_stops(
    bundle, tmp_path, tool_tokens
):
    m = {**model(), "vendor": "google"}
    plan = prepare_evaluation(bundle, [m], spending_ceiling_microdollars=1000000)
    calls = []

    def transport(payload):
        calls.append(payload)
        usage = {
            "promptTokenCount": 10,
            "candidatesTokenCount": 2,
            "totalTokenCount": 12,
        }
        if tool_tokens is not None:
            usage["toolUsePromptTokenCount"] = tool_tokens
        return {
            "modelVersion": "explicit-fixture",
            "usageMetadata": usage,
            "candidates": [
                {
                    "content": {
                        "parts": [{"functionCall": {"name": "abstain", "args": {}}}]
                    }
                }
            ],
        }

    output = tmp_path / "google"
    report = run_evaluation(
        plan,
        bundle,
        output,
        dry_run=False,
        authorization=auth(plan),
        transports={"fixture": transport},
    )
    assert report["complete"] == (tool_tokens is None)
    assert len(calls) == (4 if tool_tokens is None else 1)
    assert report["episodes"][0]["native_calls"] == [
        {"name": "abstain", "arguments": {}}
    ]
    if tool_tokens is None:
        assert report["accounting"]["settled_microdollars"] == 56
        assert report["accounting"]["held_microdollars"] == 0
        assert all(e["abstained"] for e in report["episodes"])
    else:
        assert report["summary"][0]["unknown_usage_episodes"] == 1
        assert report["accounting"]["held_microdollars"] > 0
    run_evaluation(
        plan,
        bundle,
        output,
        dry_run=False,
        authorization=auth(plan),
        transports={"fixture": transport},
    )
    assert len(calls) == (4 if tool_tokens is None else 1)


@pytest.mark.parametrize(
    "failure",
    ["unknown", "provider_error", "timeout", "budget", "interruption", "overflow"],
)
def test_failures_count_and_stop_without_retries(bundle, tmp_path, failure):
    m = model()
    if failure == "overflow":
        m["context_tokens"] = 200
    plan = prepare_evaluation(
        bundle, [m], spending_ceiling_microdollars=0 if failure == "budget" else 1000000
    )
    output = tmp_path / "failure"
    calls = []

    def transport(payload):
        calls.append(payload)
        if failure == "timeout":
            raise TimeoutError()
        if failure == "provider_error":
            return {
                "transport_status": "provider_error",
                "error": {"status_code": 400, "message": "credential-fixture"},
            }
        return reply("S01", usage=False)

    if failure == "interruption":
        ledger = Ledger(output / "requests.sqlite", plan)
        first = run_evaluation(plan, bundle, output)["requests"][0]
        ledger.reserve(first["request_id"], first["maximum_microdollars"])
        ledger.close()
    result = run_evaluation(
        plan,
        bundle,
        output,
        dry_run=False,
        authorization=auth(plan),
        transports={"fixture": transport},
    )
    assert len(result["episodes"]) == 4
    assert not any(e["supported"] for e in result["episodes"])
    assert len(calls) == (
        1 if failure in ("unknown", "provider_error", "timeout") else 0
    )
    if failure == "provider_error":
        assert result["episodes"][0]["receipt"]["provider_status_code"] == 400
        assert "credential-fixture" not in json.dumps(result)
        assert result["accounting"]["held_microdollars"] > 0
    run_evaluation(
        plan,
        bundle,
        output,
        dry_run=False,
        authorization=auth(plan),
        transports={"fixture": transport},
    )
    assert len(calls) == (
        1 if failure in ("unknown", "provider_error", "timeout") else 0
    )


def test_forwarding_rounds_and_discussion():
    case = tiny()
    part = {
        "core_allocation": {r["report_id"]: [i] for i, r in enumerate(case["reports"])},
        "nuisance_recipe": {
            "count": 0,
            "shared_prefix": 0,
            "remaining_quotas": [0, 0],
            "private_replication": 1,
            "agent_count": 2,
        },
    }
    initial = forward_evidence(case, part, rounds=0)
    assert all(len(v) == 1 for v in initial["evidence"])
    shared = forward_evidence(
        case, part, graph="chain", rounds=1, max_reports_per_message=1
    )
    assert all(len(v) == 2 for v in shared["evidence"])
    with pytest.raises(ValueError, match="discussion"):
        forward_evidence(
            case, part, discussion={(0, 0): "long"}, max_discussion_characters=1
        )
    assert (
        score(case, {"kind": "answer", "target": "B"}, initial["evidence"][0])[
            "supported"
        ]
        is False
    )
    assert (
        score(case, {"kind": "answer", "target": "B"}, shared["evidence"][0])[
            "supported"
        ]
        is True
    )
