import pytest

from clue_benchmark import Environment, public_puzzle
from clue_benchmark.evaluation import run_episode, summarize

FORBIDDEN = {
    "solution",
    "world",
    "seed",
    "config",
    "solver_fields",
    "necessary_for_uniqueness",
    "diagnostics",
    "generator_version",
    "solver_version",
}


def assert_public(obj):
    if isinstance(obj, dict):
        assert not (set(obj) & FORBIDDEN)
        for v in obj.values():
            assert_public(v)
    if isinstance(obj, list):
        for v in obj:
            assert_public(v)


def test_public_allowlist(case):
    assert_public(public_puzzle(case))
    env = Environment(case)
    assert_public(env.observation())
    assert env.observation()["clues"] == []
    response = env.request_clue(env.observation()["queries"][0]["query_id"])
    assert_public(response)
    response["clue"]["text"] = "corrupted"
    assert env.observation()["clues"][0]["text"] != "corrupted"


def test_budget_invalid_actions_and_terminal_states(case):
    env = Environment(case, 0.25)
    assert env.budget == 2
    assert env.request_clue("bad")["error"] == "invalid_or_exhausted_query"
    env.request_clue([])
    assert env.spent == 2 and env.invalid_actions == 2
    assert env.request_clue("bad")["error"] == "budget_exhausted"
    assert env.score()["correct"] == 0
    env.submit_answer(case["solution"]["murderer"])
    assert env.score()["correct"] == 1
    assert env.submit_answer("wrong")["error"] == "episode_finished"
    assert env.request_clue("bad")["error"] == "episode_finished"
    assert env.reset()["spent"] == 0
    assert env.score()["correct"] == 0


def test_every_clue_reachable_at_full_budget(case):
    env = Environment(case)
    for q in env.observation()["queries"]:
        for _ in range(q["remaining"]):
            env.request_clue(q["query_id"])
    got = {c["clue_id"] for c in env.observation()["clues"]}
    assert got == {c["clue_id"] for c in public_puzzle(case)["clues"]}
    assert env.spent == len(case["clues"])


@pytest.mark.parametrize(
    "baseline", ["reference", "random_investigation", "round_robin"]
)
def test_full_budget_reference_accuracy(case, baseline):
    result = run_episode(case, baseline, 1.0, 42)
    assert result["correct"] == 1
    assert result["solver_error"] is None


def test_world_clustered_intervals():
    rows = [
        dict(
            baseline="x",
            suspects=4,
            budget_fraction=1.0,
            world_group="same",
            correct=x,
            query_ms=[],
            spent=2,
            seconds=0.1,
            invalid_actions=0,
            solver_error=None,
        )
        for x in [0, 1]
    ]
    result = summarize(rows)[0]
    assert result["worlds"] == 1 and result["episodes"] == 2
    assert result["accuracy"] == 0.5 and result["ci95"] == [0.5, 0.5]
