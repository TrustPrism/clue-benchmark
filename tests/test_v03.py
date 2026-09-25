import json

from clue_benchmark import Config, generate, validate_case
from clue_benchmark.audit import audit_case, human_review_packet
from clue_benchmark.dataset import (
    build_paired_bank,
    create_suite_v03,
    exact_isomorphic,
    fingerprints,
    reproduce_case,
)
from clue_benchmark.environment import Environment


def test_pairwise_clues_and_private_audit():
    config = Config(min_pairwise_clues=2, mutation_steps=0)
    result = generate(config, 23)
    assert result["status"] == "ok"
    case = result["case"]
    assert validate_case(case)
    assert sum(c["type"].startswith("suspect_") for c in case["clues"]) >= 2
    audit = audit_case(case, trajectory=True)
    assert audit["complete"]
    assert audit["candidate_trajectory"][0] == 4
    assert audit["candidate_trajectory"][-1] == 1
    assert 0 <= audit["essential_cross_attribute"] <= audit["clues"]


def test_controlled_routes_have_essential_relations():
    for route, field in (
        ("pairwise", "essential_suspect_comparison"),
        ("cross_attribute", "essential_cross_attribute"),
    ):
        config = Config(
            reasoning_route=route,
            min_pairwise_clues=2 if route == "pairwise" else 0,
            mutation_steps=0,
        )
        result = generate(config, 0)
        assert result["status"] == "ok", result
        assert audit_case(result["case"])[field] > 0


def test_typed_topics_group_all_pairs_by_attribute(case):
    case = json.loads(json.dumps(case))
    case["clues"] = [
        {
            "type": "suspect_same_as",
            "suspect": "S01",
            "other_suspect": "S02",
            "attribute": "weapon",
        },
        {
            "type": "suspect_different_from",
            "suspect": "S02",
            "other_suspect": "S03",
            "attribute": "weapon",
        },
    ]
    env = Environment(case)
    queries = env.observation()["queries"]
    assert len(queries) == 1
    assert queries[0]["category"] == "suspect_comparison"
    assert queries[0]["remaining"] == 2
    assert "S01" not in queries[0]["topic"]
    q = queries[0]["query_id"]
    first = env.request_clue(q)["clue"]
    assert first == Environment(case).request_clue(q)["clue"]
    assert first != env.request_clue(q)["clue"]


def test_paired_worlds_resume_and_workers(tmp_path):
    low = Config(clue_count=8, mutation_steps=0, min_pairwise_clues=2)
    high = Config(clue_count=12, mutation_steps=0, min_pairwise_clues=2)
    one = build_paired_bank(low, high, 2, 8123, tmp_path / "one.json")
    two = build_paired_bank(low, high, 2, 8123, tmp_path / "two.json", workers=2)
    resumed = build_paired_bank(low, high, 2, 8123, tmp_path / "one.json", workers=2)
    assert one["pairs"] == two["pairs"] == resumed["pairs"]
    for pair in one["pairs"]:
        assert pair[0]["solution"] == pair[1]["solution"]
        assert pair[0]["world_group"] == pair[1]["world_group"]
        assert reproduce_case(pair[0])["case_id"] == pair[0]["case_id"]


def test_exact_isomorphism_and_review_packet(case):
    copy = json.loads(json.dumps(case))
    assert exact_isomorphic(case, copy)
    assert exact_isomorphic(case, copy, world=True)
    copy["clues"][0]["type"] = (
        "crime_negative"
        if copy["clues"][0]["type"] == "crime_positive"
        else "crime_positive"
    )
    assert fingerprints(case) != fingerprints(copy)
    packet = human_review_packet([case])
    assert len(packet) == 1 and packet[0]["reviewer_signoff"] is None
    assert "solution" not in json.dumps(packet)


def test_pairwise_renaming_keeps_structural_identity():
    case = generate(Config(min_pairwise_clues=2, mutation_steps=0), 23)["case"]
    renamed = json.loads(json.dumps(case))
    names = {suspect: f"P{i}" for i, suspect in enumerate(case["suspects"])}
    renamed["suspects"] = [names[s] for s in case["suspects"]]
    renamed["solution"]["murderer"] = names[case["solution"]["murderer"]]
    renamed["solution"]["world"] = {
        names[s]: attrs for s, attrs in case["solution"]["world"].items()
    }
    for clue in renamed["clues"]:
        for field in ("suspect", "other_suspect"):
            if field in clue:
                clue[field] = names[clue[field]]
    assert fingerprints(case) == fingerprints(renamed)
    assert exact_isomorphic(case, renamed)


def test_small_factorial_suite_has_paired_splits(tmp_path):
    manifest = create_suite_v03(tmp_path, dev_worlds=1, test_worlds=3)
    assert manifest["worlds"] == 48 and manifest["cases"] == 96
    assert len(manifest["cells"]) == 36
    dev = [
        json.loads(x) for x in (tmp_path / "private/dev.jsonl").read_text().splitlines()
    ]
    test = [
        json.loads(x)
        for x in (tmp_path / "private/test.jsonl").read_text().splitlines()
    ]
    assert len(dev) == 18 and len(test) == 78
    assert not ({c["world_group"] for c in dev} & {c["world_group"] for c in test})
