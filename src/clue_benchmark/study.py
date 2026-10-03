"""Content-addressed study preparation and failure-inclusive Inspect log export.

This module does not call a model. Constructing tasks and executing them are separate.
"""

import hashlib
import itertools
from importlib.metadata import version
from pathlib import Path

from .config import DATA_VERSION, VERSION, digest
from .dataset import read_cases
from .environment import TOPIC_MODES, protocol_version
from .evaluation import summarize
from .generation import validate_case

BUDGETS = (0.25, 0.5, 0.75, 1.0)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def implementation_hashes():
    return {p.name: sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))}


def _dataset(path, root):
    path = Path(path).resolve()
    cases = read_cases(path)
    if not cases or len({c["case_id"] for c in cases}) != len(cases):
        raise ValueError("empty dataset or duplicate case IDs")
    if any(
        not {"solution", "config", "world_group", "clues"} <= c.keys() for c in cases
    ):
        raise ValueError(
            "study preparation needs private evaluator records with world grouping"
        )
    for case in cases:
        validate_case(case)
    return {
        "path": str(path.relative_to(root)),
        "sha256": sha256(path),
        "cases": len(cases),
        "worlds": len({c["world_group"] for c in cases}),
    }, cases


def prepare_study(
    dev,
    test,
    root,
    models=(),
    repeats=3,
    topic_modes=("attribute",),
    prompt_styles=("standard",),
    generation_config=None,
):
    from .inspect_adapter import PROMPTS, model_settings

    root = Path(root).resolve()
    if type(repeats) is not int or repeats < 1:
        raise ValueError("repeats must be positive")
    for values, choices in ((topic_modes, TOPIC_MODES), (prompt_styles, PROMPTS)):
        if not values or len(set(values)) != len(values) or set(values) - set(choices):
            raise ValueError("invalid or repeated study condition")
    if len(set(models)) != len(models) or any(
        not isinstance(m, str) or "/" not in m or not m.strip() for m in models
    ):
        raise ValueError("models need distinct explicit provider/model identifiers")
    dev_record, dev_cases = _dataset(dev, root)
    test_record, test_cases = _dataset(test, root)
    if {c["world_group"] for c in dev_cases} & {c["world_group"] for c in test_cases}:
        raise ValueError("development/test world overlap")
    if {c["case_id"] for c in dev_cases} & {c["case_id"] for c in test_cases}:
        raise ValueError("development/test case overlap")
    settings = model_settings(generation_config)
    conditions = []
    for style in prompt_styles:
        conditions.append(
            dict(
                track="deduction",
                budget_fraction=1.0,
                topic_mode="targeted",
                selection_policy="agent",
                prompt_style=style,
            )
        )
        for mode, policy, budget in itertools.product(
            topic_modes, ("agent", "random"), BUDGETS
        ):
            conditions.append(
                dict(
                    track="investigation",
                    budget_fraction=budget,
                    topic_mode=mode,
                    selection_policy=policy,
                    prompt_style=style,
                )
            )
    plan = {
        "schema_version": "1.0",
        "software_version": VERSION,
        "dataset_version": DATA_VERSION,
        "status": "frozen" if models else "awaiting-model-selection",
        "datasets": {"dev": dev_record, "test": test_record},
        "implementation": implementation_hashes(),
        "lock_sha256": sha256(root / "uv.lock")
        if (root / "uv.lock").exists()
        else None,
        "dependencies": {name: version(name) for name in ("ortools", "inspect-ai")},
        "prompts": {style: PROMPTS[style] for style in prompt_styles},
        "models": list(models),
        "execution_split": "test",
        "selected_case_ids": [c["case_id"] for c in test_cases],
        "per_model_settings": {m: settings for m in models},
        "model_runtime_identities": {},
        "spending": None,
        "repeats": repeats,
        "conditions": conditions,
        "generation_config": settings,
        "token_limit": 32768,
        "time_limit_seconds": 120,
        "protocols": {
            mode: protocol_version(mode)
            for mode in sorted({condition["topic_mode"] for condition in conditions})
        },
        "primary_analysis": "Accuracy by size and all four budgets; agent-minus-random-schedule budget-averaged accuracy, paired and clustered by world.",
        "secondary_analysis": "Cell and held-out combination accuracy, missing answers, invalid requests, evidence use, latency, token usage, and descriptive error review.",
        "failure_policy": "Missing logs, missing answers, and failed samples count incorrect; report their counts separately. No silent sample exclusion.",
        "test_policy": "Freeze before model evaluation. Development diagnostics may inform the design. If tuning follows test inspection, use a fresh final test version.",
        "uncertainty": "Seeded world-cluster bootstrap; budget curves and slice intervals are descriptive, not independently corrected hypothesis tests.",
        "paid_calls": 0,
        "execution": "Preparation only. Model execution requires a separate explicit invocation and approved model/budget.",
        "episodes_per_model": len(test_cases) * len(conditions) * repeats,
    }
    return {**plan, "plan_id": digest(plan)}


def verify_study(plan, root, require_models=False):
    from .inspect_adapter import PROMPTS

    root = Path(root).resolve()
    if plan.get("plan_id") != digest({k: v for k, v in plan.items() if k != "plan_id"}):
        raise ValueError("study plan has changed")
    if (
        plan["implementation"] != implementation_hashes()
        or plan["software_version"] != VERSION
    ):
        raise ValueError("study implementation drift")
    if (
        plan["lock_sha256"] is not None
        and sha256(root / "uv.lock") != plan["lock_sha256"]
    ):
        raise ValueError("study dependency lock drift")
    if any(
        version(name) != expected for name, expected in plan["dependencies"].items()
    ):
        raise ValueError("study dependency version drift")
    for style, prompt in plan["prompts"].items():
        if PROMPTS.get(style) != prompt:
            raise ValueError("study prompt drift")
    for record in plan["datasets"].values():
        if sha256(root / record["path"]) != record["sha256"]:
            raise ValueError("study dataset drift")
    if require_models and not plan["models"]:
        raise ValueError(
            "select explicit models and freeze a new plan before execution"
        )
    return {
        "verified": True,
        "plan_id": plan["plan_id"],
        "ready_for_model_execution": bool(plan["models"]),
        "paid_calls": 0,
    }


def study_tasks(plan, root):
    """Yield declared Inspect tasks without invoking providers or loading credentials."""
    from .inspect_adapter import clue_benchmark

    verify_study(plan, root, require_models=True)
    for model, condition, repeat in itertools.product(
        plan["models"], plan["conditions"], range(plan["repeats"])
    ):
        metadata = {
            "study_plan_id": plan["plan_id"],
            "study_model": model,
            "study_repeat": repeat,
            "study_condition": condition,
        }
        yield (
            model,
            clue_benchmark(
                str(
                    Path(root)
                    / plan["datasets"][plan.get("execution_split", "test")]["path"]
                ),
                **condition,
                request_seed=repeat,
                generation_config=plan.get("per_model_settings", {}).get(
                    model, plan["generation_config"]
                ),
                case_ids=plan.get("model_case_ids", {}).get(
                    model, plan.get("selected_case_ids")
                ),
                token_limit=plan["token_limit"],
                time_limit=plan["time_limit_seconds"],
                run_metadata=metadata,
            ),
        )


def export_study(plan, root, logs):
    """Keep every declared episode in the denominator, including missing/failed ones."""
    verify_study(plan, root, require_models=True)
    cases = {
        c["case_id"]: c
        for c in read_cases(
            Path(root) / plan["datasets"][plan.get("execution_split", "test")]["path"]
        )
        if not plan.get("selected_case_ids")
        or c["case_id"] in plan["selected_case_ids"]
    }
    observed = {}
    log_records = []
    for log in logs:
        meta = log.eval.metadata or {}
        if meta.get("study_plan_id") != plan["plan_id"]:
            raise ValueError("log is not bound to this study plan")
        model, condition, repeat = (
            meta["study_model"],
            meta["study_condition"],
            meta["study_repeat"],
        )
        if (
            model not in plan["models"]
            or condition not in plan["conditions"]
            or repeat not in range(plan["repeats"])
        ):
            raise ValueError("undeclared model or study condition")
        if log.eval.model != model:
            raise ValueError("logged model differs from frozen model identifier")
        actual_settings = log.plan.config.model_dump(exclude_none=True)
        if actual_settings != plan.get("per_model_settings", {}).get(
            model, plan["generation_config"]
        ):
            raise ValueError("logged generation settings differ from frozen settings")
        if (
            log.eval.config.token_limit != plan["token_limit"]
            or log.eval.config.time_limit != plan["time_limit_seconds"]
            or log.eval.config.message_limit != 100
            or log.eval.config.token_limit_type not in (None, "all")
            or log.eval.config.epochs not in (None, 1)
            or log.eval.task_version != plan["protocols"][condition["topic_mode"]]
            or meta.get("prompt") != plan["prompts"][condition["prompt_style"]]
        ):
            raise ValueError(
                "logged limits, protocol, or prompt differ from frozen plan"
            )
        log_records.append(
            {
                "model": log.eval.model,
                "status": log.status,
                "condition": condition,
                "repeat": repeat,
                "location": str(log.location) if log.location else None,
                "generation_config": actual_settings,
                "task_version": log.eval.task_version,
            }
        )
        for sample in log.samples or []:
            key = (model, digest(condition), repeat, str(sample.id))
            if str(sample.id) not in cases or key in observed or sample.epoch != 1:
                raise ValueError("unknown/duplicate sample or undeclared epoch")
            observed[key] = sample
    rows = []
    for model, condition, repeat, case in itertools.product(
        plan["models"], plan["conditions"], range(plan["repeats"]), cases.values()
    ):
        key = (model, digest(condition), repeat, case["case_id"])
        sample = observed.get(key)
        result = (sample.metadata or {}).get("benchmark_result", {}) if sample else {}
        error = (
            "missing_log" if sample is None else "model_error" if sample.error else None
        )
        if sample is not None and not result:
            error = error or "missing_benchmark_result"
        answer = result.get("answer")
        label = (
            model
            + "|"
            + digest({k: v for k, v in condition.items() if k != "budget_fraction"})[
                :12
            ]
        )
        usage = list((sample.model_usage or {}).values()) if sample else []
        rows.append(
            {
                "case_id": case["case_id"],
                "world_group": case["world_group"],
                "cell": case.get("cell"),
                "held_out": case.get("held_out", False),
                "baseline": label,
                "model": model,
                **condition,
                "repeat": repeat,
                "suspects": len(case["suspects"]),
                "correct": int(
                    error is None and answer == case["solution"]["murderer"]
                ),
                "missing_answer": answer is None,
                "missing_submission": result.get("missing_submission", True),
                "invalid_submission": result.get("invalid_submission", False),
                "error": error,
                "spent": result.get("spent", 0),
                "requests": result.get("requests", 0),
                "invalid_actions": result.get("invalid_actions", 0),
                "seconds": (sample.total_time or 0) if sample else 0,
                "latency_available": sample is not None
                and sample.total_time is not None,
                "query_ms": result.get("query_ms", []),
                "solver_error": None,
                "tokens": {
                    field: sum(getattr(u, field) for u in usage)
                    for field in ("input_tokens", "output_tokens", "total_tokens")
                }
                if usage
                else None,
            }
        )
    summary = summarize(rows)
    for entry in summary:
        group = [
            r
            for r in rows
            if (r["baseline"], r["suspects"], r["budget_fraction"])
            == (entry["baseline"], entry["suspects"], entry["budget_fraction"])
        ]
        entry.update(
            {
                k: group[0][k]
                for k in (
                    "model",
                    "track",
                    "topic_mode",
                    "selection_policy",
                    "prompt_style",
                )
            }
        )
        entry["missing_answers"] = sum(r["missing_answer"] for r in group)
        entry["missing_submissions"] = sum(r["missing_submission"] for r in group)
        entry["invalid_submissions"] = sum(r["invalid_submission"] for r in group)
        entry["model_errors_or_missing_logs"] = sum(
            r["error"] is not None for r in group
        )
        entry["tokens"] = (
            {
                field: sum(r["tokens"][field] for r in group if r["tokens"] is not None)
                for field in ("input_tokens", "output_tokens", "total_tokens")
            }
            if any(r["tokens"] is not None for r in group)
            else None
        )
        entry["episodes_with_token_usage"] = sum(r["tokens"] is not None for r in group)
        timed = [r["seconds"] for r in group if r["latency_available"]]
        entry["mean_seconds"] = sum(timed) / len(timed) if timed else None
        entry["episodes_with_latency"] = len(timed)
    return {
        "manifest": {
            "plan_id": plan["plan_id"],
            "test_sha256": plan["datasets"]["test"]["sha256"],
            "execution_split": plan.get("execution_split", "test"),
            "execution_sha256": plan["datasets"][plan.get("execution_split", "test")][
                "sha256"
            ],
            "expected_episodes": len(rows),
            "observed_samples": len(observed),
            "models": plan["models"],
            "logs": log_records,
            "failure_policy": plan["failure_policy"],
        },
        "summary": summary,
        "paired_strategy_gaps": strategy_gaps(rows),
        "cell_accuracy": cell_accuracy(rows),
        "episodes": rows,
    }


def strategy_gaps(rows):
    from .investigation import clustered_interval

    lookup = {
        (
            r["model"],
            r["prompt_style"],
            r["case_id"],
            r["repeat"],
            r["topic_mode"],
            r["selection_policy"],
            r["budget_fraction"],
        ): r
        for r in rows
        if r["track"] == "investigation"
    }
    grouped = {}
    for r in rows:
        if r["track"] != "investigation" or r["selection_policy"] != "agent":
            continue
        comparison = lookup[
            r["model"],
            r["prompt_style"],
            r["case_id"],
            r["repeat"],
            r["topic_mode"],
            "random",
            r["budget_fraction"],
        ]
        key = (r["model"], r["prompt_style"], r["topic_mode"], r["suspects"])
        grouped.setdefault(key, {}).setdefault(r["world_group"], []).append(
            r["correct"] - comparison["correct"]
        )
    result = []
    for (model, prompt, mode, size), worlds in sorted(grouped.items()):
        values = [sum(v) / len(v) for v in worlds.values()]
        result.append(
            dict(
                model=model,
                prompt_style=prompt,
                topic_mode=mode,
                suspects=size,
                worlds=len(values),
                agent_minus_random_schedule_budget_average=sum(values) / len(values),
                world_cluster_ci95=clustered_interval(values),
            )
        )
    return result


def cell_accuracy(rows):
    groups = {}
    for row in rows:
        key = (row["baseline"], row["cell"], row["budget_fraction"])
        groups.setdefault(key, {}).setdefault(row["world_group"], []).append(
            row["correct"]
        )
    from .investigation import clustered_interval

    return [
        {
            "baseline": label,
            "cell": cell,
            "budget_fraction": budget,
            "worlds": len(worlds),
            "accuracy": sum(sum(v) / len(v) for v in worlds.values()) / len(worlds),
            "world_cluster_ci95": clustered_interval(
                [sum(v) / len(v) for v in worlds.values()]
            ),
        }
        for (label, cell, budget), worlds in groups.items()
    ]
