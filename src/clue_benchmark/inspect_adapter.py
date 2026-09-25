"""Optional Inspect integration. No paid model is selected by this module."""

import json

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import GenerateConfig
from inspect_ai.scorer import Score, accuracy, scorer, stderr
from inspect_ai.solver import solver
from inspect_ai.tool import tool

from .config import VERSION
from .dataset import read_cases
from .environment import PROTOCOL_VERSION, Environment, public_puzzle
from .generation import validate_case

PROMPT = (
    "Identify the murderer using only the supplied rules and evidence. "
    "Use submit_answer once with an exact suspect ID. Do not use external tools. "
    "For investigation, only revealed clues spend evidence budget. Invalid or exhausted "
    "requests count toward a separate request limit; each response shows current topic counts. "
    "The complete bank is solvable, but your budget may be insufficient. "
    "No free-form response is scored as an answer.\n"
)


@scorer(metrics=[accuracy(), stderr()])
def exact_suspect():
    async def score(state, target):
        result = state.metadata.get("benchmark_result", {})
        return Score(
            value=int(result.get("answer") == target.text),
            answer=result.get("answer") or "",
            metadata=result,
        )

    return score


@solver
def play(cases, track, budget_fraction):
    async def solve(state, generate):
        case = cases[str(state.sample_id)]
        env = Environment(case, budget_fraction)

        @tool
        def request_clue():
            async def execute(query_id: str) -> str:
                """Request the next clue for a listed topic.

                Args:
                    query_id: Exact query ID from the observation.
                """
                return json.dumps(env.request_clue(query_id))

            return execute

        @tool
        def submit_answer():
            async def execute(suspect_id: str) -> str:
                """Submit your one final answer and end the episode.

                Args:
                    suspect_id: Exact suspect ID from the observation.
                """
                response = env.submit_answer(suspect_id)
                state.completed = True
                return json.dumps(response)

            return execute

        state.tools = [submit_answer()]
        if track == "investigation":
            state.tools.insert(0, request_clue())
        # One model response per iteration; never invoke the model again after submission.
        try:
            for _ in range(env.max_requests + 2 if track == "investigation" else 2):
                state = await generate(
                    state, tool_calls="single", parallel_tool_calls=False
                )
                if env.done or state.completed or not state.output.message.tool_calls:
                    break
        finally:
            state.metadata["benchmark_result"] = {
                "answer": env.answer,
                "spent": env.spent,
                "requests": env.requests,
                "invalid_actions": env.invalid_actions,
                "track": track,
                "budget_fraction": budget_fraction,
                "protocol_version": PROTOCOL_VERSION,
            }
        return state

    return solve


@task
def clue_benchmark(
    dataset: str, track: str = "deduction", budget_fraction: float = 1.0
):
    if track not in ("deduction", "investigation"):
        raise ValueError("invalid track")
    cases = read_cases(dataset)
    for c in cases:
        validate_case(c)
    samples = []
    for c in cases:
        observation = (
            public_puzzle(c)
            if track == "deduction"
            else Environment(c, budget_fraction).observation()
        )
        samples.append(
            Sample(
                id=c["case_id"],
                input=PROMPT + json.dumps(observation),
                target=c["solution"]["murderer"],
                metadata={
                    "world_group": c.get("world_group", c["case_id"]),
                    "suspects": len(c["suspects"]),
                },
            )
        )
    return Task(
        dataset=samples,
        solver=play({c["case_id"]: c for c in cases}, track, budget_fraction),
        scorer=exact_suspect(),
        config=GenerateConfig(
            temperature=0, max_tokens=4096, parallel_tool_calls=False
        ),
        message_limit=100,
        token_limit=32768,
        time_limit=120,
        version=PROTOCOL_VERSION,
        metadata={
            "benchmark_version": VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "track": track,
            "budget_fraction": budget_fraction,
            "allowed_tools": "benchmark only",
            "prompt": PROMPT,
        },
    )
