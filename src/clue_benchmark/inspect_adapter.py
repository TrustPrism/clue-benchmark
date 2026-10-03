"""Optional Inspect integration. No paid model is selected by this module."""

import json
import math
import random
import time

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import GenerateConfig
from inspect_ai.scorer import Score, accuracy, scorer, stderr
from inspect_ai.solver import solver
from inspect_ai.tool import tool

from .config import VERSION
from .dataset import read_cases
from .environment import Environment, protocol_version, public_puzzle
from .generation import validate_case

PROMPT = (
    "Identify the murderer using only the supplied rules and evidence. "
    "Use submit_answer once with an exact suspect ID. Do not use external tools. "
    "For investigation, only revealed clues spend evidence budget. Invalid or exhausted "
    "requests count toward a separate request limit; each response shows current topic counts. "
    "The complete bank is solvable, but your budget may be insufficient. "
    "No free-form response is scored as an answer.\n"
)
PROMPTS = {
    "standard": PROMPT,
    "deliberate": PROMPT
    + "Check the logical consequences of the evidence before answering.\n",
}
SELECTION_POLICIES = ("agent", "random", "round_robin")
GENERATION_SETTINGS = {
    "temperature",
    "max_tokens",
    "max_retries",
    "top_p",
    "seed",
    "effort",
    "reasoning_effort",
    "reasoning_mode",
    "reasoning_tokens",
    "reasoning_summary",
    "reasoning_history",
    "verbosity",
    "parallel_tool_calls",
}


def model_settings(config=None):
    config = {} if config is None else config
    if not isinstance(config, dict):
        raise ValueError("generation settings must be an object")
    if set(config) - GENERATION_SETTINGS:
        raise ValueError(
            "unknown model generation setting or provider tools/fallbacks are forbidden"
        )
    if config.get("parallel_tool_calls", False) is not False:
        raise ValueError("benchmark tools must run sequentially")
    settings = {
        "temperature": 0,
        "max_tokens": 4096,
        "max_retries": 0,
        **config,
        "parallel_tool_calls": False,
    }
    if type(settings["max_tokens"]) is not int or settings["max_tokens"] < 1:
        raise ValueError("positive max_tokens required")
    if type(settings["max_retries"]) is not int or settings["max_retries"] < 0:
        raise ValueError("nonnegative max_retries required")
    if (
        type(settings["temperature"]) not in (int, float)
        or not math.isfinite(settings["temperature"])
        or not 0 <= settings["temperature"] <= 2
    ):
        raise ValueError("temperature must be in [0,2]")
    GenerateConfig(**settings)
    return settings


def prepare_environment(case, budget_fraction, topic_mode, selection_policy, seed):
    """Fixed schedules isolate inference on a subset from agent topic selection."""
    env = Environment(case, budget_fraction, topic_mode)
    if selection_policy == "agent":
        return env
    rng = random.Random(seed)
    cursor = 0
    while env.spent < env.budget:
        active = [q["query_id"] for q in env.observation()["queries"] if q["remaining"]]
        query = (
            rng.choice(active)
            if selection_policy == "random"
            else active[cursor % len(active)]
        )
        if selection_policy == "round_robin":
            ids = list(env._queries)
            while ids[cursor % len(ids)] not in active:
                cursor += 1
            query = ids[cursor % len(ids)]
            cursor += 1
        env.request_clue(query)
    return env


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
def play(cases, track, budget_fraction, topic_mode, selection_policy, request_seed):
    async def solve(state, generate):
        case = cases[str(state.sample_id)]
        env = prepare_environment(
            case, budget_fraction, topic_mode, selection_policy, request_seed
        )
        latencies = []

        @tool
        def request_clue():
            async def execute(query_id: str) -> str:
                """Request the next clue for a listed topic.

                Args:
                    query_id: Exact query ID from the observation.
                """
                started = time.perf_counter()
                response = env.request_clue(query_id)
                latencies.append((time.perf_counter() - started) * 1000)
                return json.dumps(response)

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
        if track == "investigation" and selection_policy == "agent":
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
                "spent": len(case["clues"]) if track == "deduction" else env.spent,
                "requests": env.requests,
                "invalid_actions": env.invalid_actions,
                "track": track,
                "budget_fraction": budget_fraction,
                "protocol_version": env.protocol_version,
                "topic_mode": topic_mode,
                "selection_policy": selection_policy,
                "missing_answer": env.answer is None,
                "missing_submission": not env.done,
                "invalid_submission": env.done and env.answer is None,
                "query_ms": latencies,
            }
        return state

    return solve


@task
def clue_benchmark(
    dataset: str,
    track: str = "deduction",
    budget_fraction: float = 1.0,
    topic_mode: str = "targeted",
    selection_policy: str = "agent",
    request_seed: int = 0,
    prompt_style: str = "standard",
    generation_config: dict | None = None,
    token_limit: int = 32768,
    time_limit: int = 120,
    run_metadata: dict | None = None,
    case_ids: list[str] | None = None,
):
    if track not in ("deduction", "investigation"):
        raise ValueError("invalid track")
    if selection_policy not in SELECTION_POLICIES:
        raise ValueError("invalid selection policy")
    if prompt_style not in PROMPTS:
        raise ValueError("invalid prompt style")
    if track == "deduction" and (budget_fraction != 1 or selection_policy != "agent"):
        raise ValueError("deduction uses full evidence and no request policy")
    version = protocol_version(topic_mode)
    cases = read_cases(dataset)
    if case_ids is not None:
        if not case_ids or len(set(case_ids)) != len(case_ids):
            raise ValueError("empty or duplicate selected case IDs")
        selected = set(case_ids)
        cases = [c for c in cases if c["case_id"] in selected]
        if {c["case_id"] for c in cases} != selected:
            raise ValueError("unknown selected case ID")
    for c in cases:
        validate_case(c)
    if len({c["case_id"] for c in cases}) != len(cases) or not cases:
        raise ValueError("empty dataset or duplicate case IDs")
    samples = []
    for c in cases:
        observation = (
            public_puzzle(c)
            if track == "deduction"
            else prepare_environment(
                c, budget_fraction, topic_mode, selection_policy, request_seed
            ).observation()
        )
        samples.append(
            Sample(
                id=c["case_id"],
                input=PROMPTS[prompt_style] + json.dumps(observation),
                target=c["solution"]["murderer"],
                metadata={
                    "world_group": c.get("world_group", c["case_id"]),
                    "suspects": len(c["suspects"]),
                    "cell": c.get("cell"),
                    "held_out": c.get("held_out", False),
                },
            )
        )
    return Task(
        dataset=samples,
        solver=play(
            {c["case_id"]: c for c in cases},
            track,
            budget_fraction,
            topic_mode,
            selection_policy,
            request_seed,
        ),
        scorer=exact_suspect(),
        config=GenerateConfig(**model_settings(generation_config)),
        message_limit=100,
        token_limit=token_limit,
        time_limit=time_limit,
        version=version,
        metadata={
            **(run_metadata or {}),
            "benchmark_version": VERSION,
            "protocol_version": version,
            "track": track,
            "budget_fraction": budget_fraction,
            "allowed_tools": "benchmark only",
            "prompt": PROMPTS[prompt_style],
            "prompt_style": prompt_style,
            "topic_mode": topic_mode,
            "selection_policy": selection_policy,
            "request_seed": request_seed,
        },
    )
