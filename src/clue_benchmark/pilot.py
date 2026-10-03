"""Exploratory development pilot; preparation never invokes model generation."""

import random
from collections import defaultdict
from importlib.metadata import version

from .config import digest
from .dataset import read_cases
from .study import prepare_study

PILOT_MODELS = (
    "google/gemini-3.8-flash",
    "google/gemini-3.5-flash-lite",
    "ollama/qwen3.5:9b",
)
PRICE_SNAPSHOT = {
    "source": "https://ai.google.dev/gemini-api/docs/pricing",
    "retrieved_on": "2026-10-03",
    "service": "standard synchronous text API; no caching, grounding, batch, flex, or priority",
    "thinking": "output price includes thinking tokens",
    "valid_through": "2026-12-31",
    "models": {
        PILOT_MODELS[0]: {"input_per_million": 0.75, "output_per_million": 3.75},
        PILOT_MODELS[1]: {"input_per_million": 0.30, "output_per_million": 2.50},
    },
}


def select_pilot_worlds(cases, seed=0, per_size=4):
    if type(seed) is not int or type(per_size) is not int or per_size < 1:
        raise ValueError("integer seed and positive world count required")
    worlds = defaultdict(list)
    for case in cases:
        if case.get("split", "dev") != "dev" or case.get("held_out", False):
            raise ValueError("pilot selection requires development cases")
        worlds[case["world_group"]].append(case)
    by_size = defaultdict(list)
    for world, pair in sorted(worlds.items()):
        n = len(pair[0]["suspects"])
        if (
            len(pair) != 2
            or any(len(c["suspects"]) != n for c in pair)
            or pair[0]["solution"] != pair[1]["solution"]
            or sorted(len(c["clues"]) for c in pair) != [n + 4, n + 8]
        ):
            raise ValueError("world must retain its two paired clue-density variants")
        by_size[n].append(world)
    rng = random.Random(seed)
    chosen = []
    for size in (4, 8, 12):
        if len(by_size[size]) < per_size:
            raise ValueError("insufficient development worlds at each size")
        chosen.extend(rng.sample(by_size[size], per_size))
    selected = sorted(
        (c for w in chosen for c in worlds[w]), key=lambda c: c["case_id"]
    )
    return selected


def prepare_pilot(
    dev, test, root, local_identity, execution_directory="results/pilot-v0.3"
):
    common = {"temperature": 1.0, "max_tokens": 4096, "max_retries": 0}
    plan = prepare_study(
        dev, test, root, PILOT_MODELS, repeats=1, generation_config=common
    )
    selected = select_pilot_worlds(read_cases(dev))
    from .inspect_adapter import model_settings

    if local_identity is not None and (
        not local_identity.get("digest")
        or local_identity.get("quantization") != "Q4_K_M"
        or local_identity.get("num_ctx") != 32768
        or not local_identity.get("ollama_version")
    ):
        raise ValueError(
            "local identity must pin digest, Q4_K_M, Ollama version, and context"
        )
    plan.update(
        schema_version="1.1",
        study_kind="exploratory-development-pilot",
        execution_split="dev",
        selected_case_ids=[c["case_id"] for c in selected],
        selected_world_ids=sorted({c["world_group"] for c in selected}),
        selection={"seed": 0, "worlds_per_size": 4, "retain_density_pair": True},
        per_model_settings={
            model: model_settings(
                {
                    **common,
                    **(
                        {"reasoning_effort": "medium"}
                        if model.startswith("google/")
                        else {"top_p": 0.95}
                    ),
                }
            )
            for model in PILOT_MODELS
        },
        provider_settings={
            PILOT_MODELS[0]: {"thinking_level": "medium"},
            PILOT_MODELS[1]: {"thinking_level": "medium"},
            PILOT_MODELS[2]: {
                "think": True,
                "top_k": 20,
                "presence_penalty": 1.5,
                "repeat_penalty": 1.0,
                "thinking_accounting": "Ollama eval_count includes thinking; separate count unavailable",
            },
        },
        model_runtime_identities={
            **{
                m: {
                    "requested_model": m.split("/", 1)[1],
                    "context_capacity": 1048576,
                    "returned_version": "recorded for every response where available",
                }
                for m in PILOT_MODELS[:2]
            },
            PILOT_MODELS[2]: local_identity,
        },
        local_runtime_pinned=local_identity is not None,
        spending={"combined_google_usd": 50.0, "includes_compatibility_probes": True},
        prices=PRICE_SNAPSHOT,
        execution_directory=execution_directory,
        time_limit_seconds=600,
        episodes_per_model=216,
        expected_episodes=648,
        compatibility_policy="Native clue request and final submission, usage/thinking accounting, context limits, and runtime identity must pass before scoring. Stop incompatible models; no substitution or emulation.",
        test_policy="744 test cases remain untouched by model execution; this development pilot may inform a newly frozen full study.",
        latency_policy="Hosted versus local latency is descriptive and is not a model capability ranking.",
        execution="Preparation and dry runs make no generation calls. Explicit run-study invocation is required; this manifest authorizes only the development pilot.",
    )
    plan["dependencies"]["google-genai"] = version("google-genai")
    del plan["plan_id"]
    return {**plan, "plan_id": digest(plan)}
