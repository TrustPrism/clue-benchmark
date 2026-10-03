import copy
import json
from pathlib import Path

import pytest

from clue_benchmark import Config, generate
from clue_benchmark.config import digest
from clue_benchmark.dataset import write_jsonl
from clue_benchmark.environment import Environment, protocol_version
from clue_benchmark.evaluation import run_episode
from clue_benchmark.investigation import (
    compare_investigation,
    decision_opportunities,
    menu_prior_candidates,
    menu_prior_diagnostic,
)
from clue_benchmark.readiness import metadata_checks, readiness_report
from clue_benchmark.review import collect_reviews, prepare_review, review_template
from clue_benchmark.study import prepare_study, verify_study


def test_attribute_menu_groups_suspects_and_preserves_all_evidence(case):
    grouped = Environment(case, topic_mode="attribute")
    targeted = Environment(case)
    assert grouped.protocol_version == "2.1-experimental"
    assert targeted.protocol_version == "2.0"
    assert len(grouped.observation()["queries"]) <= len(
        targeted.observation()["queries"]
    )
    for env in (grouped, targeted):
        initial = env.observation()
        for q in initial["queries"]:
            for _ in range(q["remaining"]):
                env.request_clue(q["query_id"])
        assert (
            sorted(env.observation()["clues"], key=lambda c: c["clue_id"])
            == env._public["clues"]
        )
        assert env.spent == len(case["clues"])
    with pytest.raises(ValueError):
        protocol_version("bad")


def test_grouped_unary_menu_has_clear_label(case):
    case = copy.deepcopy(case)
    case["clues"] = [
        dict(type="unary_negative", suspect=s, attribute="weapon", value="Knife")
        for s in ("S01", "S02")
    ]
    env = Environment(case, topic_mode="attribute")
    q = env.observation()["queries"][0]
    assert q["topic"] == "Suspect attributes / weapon" and q["remaining"] == 2
    assert q["suspect"] is None
    assert len(env.observation()["queries"]) == 1


def test_menu_prior_uses_only_catalogue_and_grouping_removes_named_hint(case):
    observation = dict(
        suspects=["S01", "S02"], queries=[dict(suspect="S01", remaining=2)]
    )
    assert menu_prior_candidates(observation, "fewest") == ["S02"]
    assert menu_prior_candidates(observation, "most") == ["S01"]
    result = menu_prior_diagnostic([{**case, "world_group": "world"}])
    assert all(
        row["expected_accuracy"] == row["chance"]
        for row in result["rows"]
        if row["topic_mode"] == "attribute"
    )


@pytest.mark.parametrize("policy", ["random_clue", "topic_heuristic", "round_robin"])
def test_grouped_policy_solves_complete_bank(case, policy):
    result = run_episode(case, policy, topic_mode="attribute")
    assert result["correct"] == 1 and result["solver_error"] is None


def test_opportunity_diagnostic_and_all_budget_comparison(case):
    case = {**case, "world_group": "world"}
    diagnostic = decision_opportunities(case)
    assert all(r["complete"] for r in diagnostic["rows"])
    assert all(
        r["candidates_after_best"]
        <= r["candidates_after_worst"]
        <= r["candidates_before"]
        for r in diagnostic["rows"]
    )
    result = compare_investigation([case], repeats=1, diagnostic_per_size=0)
    assert result["manifest"]["episodes"] == 32
    assert {r["budget_fraction"] for r in result["summary"]} == {0.25, 0.5, 0.75, 1.0}
    assert all(
        r["accuracy"] == 1 for r in result["summary"] if r["budget_fraction"] == 1
    )
    assert len(result["paired_gaps"]) == 24


def test_inconclusive_comparisons_are_kept_and_counted(case, monkeypatch):
    import clue_benchmark.investigation as investigation

    monkeypatch.setattr(
        investigation,
        "run_episode",
        lambda *a: dict(
            correct=1,
            solver_error="inconclusive",
            spent=0,
            requests=0,
            invalid_actions=0,
            seconds=0,
            query_ms=[],
        ),
    )
    result = compare_investigation(
        [{**case, "world_group": "world"}], repeats=1, diagnostic_per_size=0
    )
    assert all(row["correct"] == 0 for row in result["episodes"])
    assert sum(row["solver_errors"] for row in result["summary"]) == 32


@pytest.fixture
def study_files(case, tmp_path):
    dev = {**copy.deepcopy(case), "world_group": "dev-world"}
    test = generate(Config(mutation_steps=0), 17)["case"]
    test["world_group"] = "test-world"
    write_jsonl(tmp_path / "dev.jsonl", [dev])
    write_jsonl(tmp_path / "test.jsonl", [test])
    return tmp_path, dev, test


def test_study_preparation_never_selects_provider_or_accepts_drift(study_files):
    root, _, _ = study_files
    plan = prepare_study(root / "dev.jsonl", root / "test.jsonl", root)
    assert verify_study(plan, root)["paid_calls"] == 0
    assert plan["status"] == "awaiting-model-selection"
    assert plan["episodes_per_model"] == 27
    with pytest.raises(ValueError, match="select explicit"):
        verify_study(plan, root, require_models=True)
    changed = copy.deepcopy(plan)
    changed["repeats"] += 1
    with pytest.raises(ValueError, match="plan has changed"):
        verify_study(changed, root)
    (root / "test.jsonl").write_text((root / "test.jsonl").read_text() + "\n")
    with pytest.raises(ValueError, match="dataset drift"):
        verify_study(plan, root)


def test_study_rejects_world_overlap_and_unknown_settings(study_files):
    root, dev, test = study_files
    with pytest.raises(ValueError, match="unknown model generation"):
        prepare_study(
            root / "dev.jsonl",
            root / "test.jsonl",
            root,
            generation_config={"made_up_setting": 1},
        )
    test["world_group"] = dev["world_group"]
    write_jsonl(root / "test.jsonl", [test])
    with pytest.raises(ValueError, match="world overlap"):
        prepare_study(root / "dev.jsonl", root / "test.jsonl", root)


def test_review_packet_no_private_fields_and_real_coverage(case):
    packet = prepare_review([case])
    text = json.dumps(packet)
    for key in ("solution", "world", "seed", "config", "diagnostics"):
        assert '"' + key + '"' not in text
    assert collect_reviews(packet, [])["status"] == "pending"
    assert review_template(packet)["reviewer"]["human"] is False
    responses = [
        {
            "packet_id": packet["packet_id"],
            "reviewer": {"id": name, "human": True, "independent": True},
            "completed_at": "2026-10-02",
            "reviews": [
                {
                    "review_id": i["review_id"],
                    "wording_clear": True,
                    "topic_expectation_clear": True,
                    "issues": [],
                }
                for i in packet["items"]
            ],
        }
        for name in ("test-reviewer-a", "test-reviewer-b")
    ]
    assert collect_reviews(packet, responses)["status"] == "approved"
    responses[0]["reviews"][0]["wording_clear"] = False
    assert collect_reviews(packet, responses)["blocking_issues"] == 1
    assert collect_reviews(packet, responses)["status"] == "pending"
    responses[0]["reviewer"]["human"] = False
    with pytest.raises(ValueError, match="attestations"):
        collect_reviews(packet, responses)


def test_review_rejects_stale_packet_and_bad_answer(case):
    packet = prepare_review([case])
    response = dict(
        packet_id="stale",
        reviewer={"id": "reviewer", "human": True, "independent": True},
        completed_at="2026-10-02",
        reviews=[],
    )
    with pytest.raises(ValueError, match="different packet"):
        collect_reviews(packet, [response])
    response["packet_id"] = packet["packet_id"]
    response["reviews"] = [
        dict(
            review_id=i["review_id"],
            wording_clear=True,
            topic_expectation_clear=True,
            answer="wrong",
        )
        for i in packet["items"]
    ]
    report = collect_reviews(packet, [response], [case])
    assert report["incorrect_answers_for_adjudication"] == len(packet["items"])
    packet["items"][0]["queries"][0]["topic"] = "changed"
    with pytest.raises(ValueError, match="packet changed"):
        collect_reviews(packet, [])


def test_empty_review_packet_cannot_approve_itself(case):
    packet = prepare_review([case])
    packet["items"] = []
    packet["packet_id"] = digest({k: v for k, v in packet.items() if k != "packet_id"})
    with pytest.raises(ValueError, match="nonempty packet"):
        collect_reviews(packet, [])


def test_private_readiness_does_not_claim_public_or_model_validation():
    root = Path(__file__).resolve().parents[1]
    checks = metadata_checks(root / "data/v0.3")
    assert checks["distribution_hashes_match"]
    report = readiness_report(root / "data/v0.3")
    assert not report["public_release_ready"] and not report["model_evidence_available"]
    assert all(g["status"] == "pending" for g in report["public_release_gates"])


def test_official_metadata_loader_reads_public_records():
    mlc = pytest.importorskip("mlcroissant")
    root = Path(__file__).resolve().parents[1] / "data/v0.3"
    metadata = json.loads((root / "croissant.json").read_text())
    dataset = mlc.Dataset(
        jsonld=metadata,
        mapping={
            f["@id"]: (root / f["contentUrl"]).resolve()
            for f in metadata["distribution"]
        },
    )
    for split, expected in (("dev", 216), ("test", 744)):
        records = list(dataset.records(record_set=split))
        assert len(records) == expected
        assert records[0][f"{split}/case_id"].decode()
        assert records[0][f"{split}/suspects"]
