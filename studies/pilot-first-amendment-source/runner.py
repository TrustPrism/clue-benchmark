"""Sequential native execution with a fail-closed, durable spending ledger."""

import itertools
import json
import os
import time
from datetime import date
from pathlib import Path

from .config import digest
from .dataset import atomic_json, read_cases
from .environment import public_puzzle
from .evaluation import summarize
from .inspect_adapter import PROMPTS, prepare_environment
from .investigation import clustered_interval
from .ledger import (
    AccountingStop,
    BudgetStop,
    Ledger,
    charge_microdollars,
    execution_lock,
)
from .providers import ProtocolError, UsageError, error_label, make_provider
from .study import strategy_gaps, verify_study


def execution_cases(plan, root):
    split = plan.get("execution_split", "test")
    cases = read_cases(Path(root) / plan["datasets"][split]["path"])
    selected = plan.get("selected_case_ids", [c["case_id"] for c in cases])
    if not selected or len(set(selected)) != len(selected):
        raise ValueError("selected case IDs must be nonempty and unique")
    lookup = {c["case_id"]: c for c in cases}
    if set(selected) - lookup.keys():
        raise ValueError("unknown selected case ID")
    if plan.get("study_kind") == "exploratory-development-pilot":
        if split != "dev" or any(lookup[c].get("split") != "dev" for c in selected):
            raise ValueError("pilot cannot execute test cases")
    return [lookup[c] for c in selected]


def declared_episodes(plan, cases):
    # The world/case schedule is identical across models; each call starts fresh.
    for model, repeat, condition, case in itertools.product(
        plan["models"], range(plan["repeats"]), plan["conditions"], cases
    ):
        yield (
            digest(
                [
                    plan.get("episode_id_namespace", plan["plan_id"]),
                    model,
                    repeat,
                    condition,
                    case["case_id"],
                ]
            ),
            {
                "case_id": case["case_id"],
                "world_group": case["world_group"],
                "cell": case.get("cell"),
                "held_out": case.get("held_out", False),
                "model": model,
                "repeat": repeat,
                "suspects": len(case["suspects"]),
                "baseline": model
                + "|"
                + digest(
                    {k: v for k, v in condition.items() if k != "budget_fraction"}
                )[:12],
                **condition,
            },
            case,
        )


def model_settings(plan, model):
    return {
        **plan.get("per_model_settings", {}).get(model, plan["generation_config"]),
        **plan.get("provider_settings", {}).get(model, {}),
    }


def request(
    provider,
    messages,
    tools,
    allowance,
    deadline,
    ledger,
    plan,
    episode,
    phase,
    input_bound=0,
):
    remaining_time = deadline - time.monotonic()
    if remaining_time <= 0:
        raise TimeoutError()
    if allowance <= 0:
        raise ProtocolError("episode token allowance exhausted")
    output_cap = min(
        model_settings(plan, provider.name)["max_tokens"], allowance - input_bound
    )
    if output_cap <= 0:
        raise ProtocolError("episode token allowance exhausted")
    identity = plan["model_runtime_identities"][provider.name]
    prices = plan["prices"]["models"].get(provider.name)
    # Reserve the entire declared input context plus the maximum output, rather
    # than trusting a tokenizer estimate or ignoring hidden thinking tokens.
    reserve = (
        charge_microdollars(
            {"input_tokens": identity["context_capacity"], "output_tokens": output_cap},
            prices,
        )
        if provider.paid
        else 0
    )
    request_id = ledger.reserve(episode, provider.name, phase, reserve)
    try:
        reply = provider.generate(messages, tools, output_cap, remaining_time)
        usage = reply.usage
        if not usage or any(
            type(usage.get(k)) is not int or usage[k] < 0
            for k in ("input_tokens", "output_tokens", "total_tokens")
        ):
            raise UsageError("missing usage")
        if usage["total_tokens"] != usage["input_tokens"] + usage["output_tokens"]:
            raise UsageError("inconsistent usage")
        actual = charge_microdollars(usage, prices) if provider.paid else 0
        ledger.settle(request_id, usage, actual)
        if usage["total_tokens"] > allowance or usage["output_tokens"] > output_cap:
            raise ProtocolError("provider exceeded episode or output token allowance")
        if usage["input_tokens"] + output_cap > identity.get(
            "num_ctx", identity["context_capacity"]
        ):
            raise ProtocolError("provider context capacity exceeded")
        return reply, actual / 1000000
    except BaseException as exc:
        ledger.uncertain(request_id, error_label(exc))
        raise


def probe(provider, plan, ledger, output):
    """A non-scored synthetic exchange tests both native tools and history."""
    probe_id = "compatibility:" + provider.name
    limit = plan["token_limit"]
    deadline = time.monotonic() + plan["time_limit_seconds"]
    query = "q001"
    prompt = (
        "Protocol compatibility probe, not a scored puzzle. "
        "Use request_clue with query_id q001 now. After receiving its response, "
        "use submit_answer with suspect_id S01. Do not write free-form answers. "
        "The two identifiers are protocol test values."
    )
    messages = provider.start(prompt)
    transcript = [{"role": "user", "text": prompt}]
    usage_total = 0
    versions = []
    costs = 0.0
    for stage, expected, args in (
        ("clue", "request_clue", {"query_id": query}),
        ("answer", "submit_answer", {"suspect_id": "S01"}),
    ):
        reply, cost = request(
            provider,
            messages,
            [expected],
            limit - usage_total,
            deadline,
            ledger,
            plan,
            probe_id,
            "compatibility",
        )
        usage_total += reply.usage["total_tokens"]
        costs += cost
        versions.append(reply.model_version)
        transcript.append(
            {
                "stage": stage,
                "text": reply.text,
                "calls": reply.calls,
                "usage": reply.usage,
                "returned_model_version": reply.model_version,
            }
        )
        atomic_json(
            output / "logs" / (digest(provider.name) + "-compatibility.json"),
            {"compatible": False, "transcript": transcript},
        )
        if reply.calls != [(expected, args)]:
            raise ProtocolError("native clue request or final submission probe failed")
        response = (
            {
                "clue": {"clue_id": "c001", "text": "A protocol test clue."},
                "remaining_budget": 0,
            }
            if stage == "clue"
            else {"accepted": True, "done": True}
        )
        provider.add_results(messages, reply, [(expected, response)])
    loaded = (
        provider.check_loaded_context()
        if hasattr(provider, "check_loaded_context")
        else None
    )
    return {
        "compatible": True,
        "tokens": usage_total,
        "cost_usd": costs,
        "returned_model_versions": versions,
        "access_identity": getattr(provider, "access_identity", None),
        "loaded_runtime": loaded,
        "transcript": transcript,
    }


def play_episode(provider, plan, ledger, episode, row, case, output):
    started = time.monotonic()
    deadline = started + plan["time_limit_seconds"]
    env = prepare_environment(
        case,
        row["budget_fraction"],
        row["topic_mode"],
        row["selection_policy"],
        row["repeat"],
    )
    observation = (
        public_puzzle(case) if row["track"] == "deduction" else env.observation()
    )
    prompt = PROMPTS[row["prompt_style"]] + json.dumps(observation)
    messages = provider.start(prompt)
    transcript = [{"role": "user", "text": prompt}]
    tools = ["submit_answer"]
    if row["track"] == "investigation" and row["selection_policy"] == "agent":
        tools.insert(0, "request_clue")
    totals = {k: 0 for k in ("input_tokens", "output_tokens", "total_tokens")}
    thinking = 0
    thinking_available = True
    cost = 0.0
    error = None
    versions = []
    latencies = []
    fatal = None
    try:
        for _ in range(env.max_requests + 2 if row["track"] == "investigation" else 2):
            allowance = plan["token_limit"] - totals["total_tokens"]
            # Google counts the native conversation and tool schema directly;
            # opaque thought signatures are not estimated from their byte size.
            if hasattr(provider, "input_tokens_bound"):
                input_bound = provider.input_tokens_bound(messages, tools)
            else:
                input_bound = (
                    len(json.dumps(messages, ensure_ascii=False).encode()) + 2048
                )
            identity = plan["model_runtime_identities"][provider.name]
            capacity = identity.get("num_ctx", identity["context_capacity"])
            if input_bound >= min(allowance, capacity):
                error = "token_limit"
                break
            reply, charged = request(
                provider,
                messages,
                tools,
                allowance,
                deadline,
                ledger,
                plan,
                episode,
                "scored",
                input_bound=input_bound,
            )
            cost += charged
            for key in totals:
                totals[key] += reply.usage[key]
            if reply.usage.get("thinking_tokens") is None:
                thinking_available = False
            else:
                thinking += reply.usage["thinking_tokens"]
            versions.append(reply.model_version)
            transcript.append(
                {
                    "role": "assistant",
                    "text": reply.text,
                    "calls": reply.calls,
                    "usage": reply.usage,
                    "returned_model_version": reply.model_version,
                }
            )
            atomic_json(
                output / "logs" / (episode + ".json"),
                {
                    "episode_id": episode,
                    "plan_id": plan["plan_id"],
                    "model": provider.name,
                    "transcript": transcript,
                },
            )
            if time.monotonic() >= deadline:
                raise TimeoutError()
            if not reply.calls:
                break
            results = []
            for name, args in reply.calls:
                t = time.monotonic()
                if name not in tools or not isinstance(args, dict):
                    env.invalid_actions += 1
                    result = {"error": "invalid_action"}
                elif name == "request_clue" and set(args) == {"query_id"}:
                    result = env.request_clue(args["query_id"])
                    latencies.append((time.monotonic() - t) * 1000)
                elif name == "submit_answer" and set(args) == {"suspect_id"}:
                    result = env.submit_answer(args["suspect_id"])
                else:
                    env.invalid_actions += 1
                    result = {"error": "invalid_arguments"}
                results.append((name, result))
                transcript.append({"role": "tool", "name": name, "result": result})
                if env.done:
                    break
            if env.done:
                break
            provider.add_results(messages, reply, results)
    except (BudgetStop, AccountingStop) as exc:
        error = (
            "budget_stopped" if isinstance(exc, BudgetStop) else "accounting_stopped"
        )
        fatal = exc
    except Exception as exc:
        error = error_label(exc)
        if isinstance(exc, UsageError) or provider.paid:
            fatal = AccountingStop("request accounting unavailable; execution stopped")
    result = {
        **row,
        "correct": int(error is None and env.answer == case["solution"]["murderer"]),
        "answer": env.answer,
        "source_plan_id": plan["plan_id"],
        "token_accounting_version": "usage-bound-v2",
        "missing_answer": env.answer is None,
        "missing_submission": not env.done,
        "invalid_submission": env.done and env.answer is None,
        "completion": env.done and error is None,
        "spent": len(case["clues"]) if row["track"] == "deduction" else env.spent,
        "requests": env.requests,
        "invalid_actions": env.invalid_actions,
        "seconds": time.monotonic() - started,
        "query_ms": latencies,
        "solver_error": None,
        "error": error,
        "tokens": {
            **totals,
            "thinking_tokens": thinking if thinking_available else None,
        },
        "cost_usd": cost,
        "returned_model_versions": versions,
    }
    atomic_json(
        output / "logs" / (episode + ".json"),
        {
            "episode_id": episode,
            "plan_id": plan["plan_id"],
            "model": provider.name,
            "transcript": transcript,
            "result": result,
        },
    )
    ledger.finish_episode(episode, result)
    if fatal:
        raise fatal
    return result


def paired_model_gaps(rows):
    lookup = {
        (
            r["model"],
            r["case_id"],
            r["repeat"],
            digest(
                {
                    k: r[k]
                    for k in (
                        "track",
                        "budget_fraction",
                        "topic_mode",
                        "selection_policy",
                        "prompt_style",
                    )
                }
            ),
        ): r
        for r in rows
    }
    models = sorted({r["model"] for r in rows})
    result = []
    for a, b in itertools.combinations(models, 2):
        groups = {}
        for row in rows:
            if row["model"] != a:
                continue
            cond = {
                k: row[k]
                for k in (
                    "track",
                    "budget_fraction",
                    "topic_mode",
                    "selection_policy",
                    "prompt_style",
                )
            }
            other = lookup[b, row["case_id"], row["repeat"], digest(cond)]
            key = (row["suspects"], digest(cond))
            entry = groups.setdefault(key, {"condition": cond, "worlds": {}})
            entry["worlds"].setdefault(row["world_group"], []).append(
                row["correct"] - other["correct"]
            )
        for (size, _), entry in groups.items():
            values = [sum(v) / len(v) for v in entry["worlds"].values()]
            result.append(
                {
                    "model_a": a,
                    "model_b": b,
                    "suspects": size,
                    **entry["condition"],
                    "worlds": len(values),
                    "accuracy_a_minus_b": sum(values) / len(values),
                    "world_cluster_ci95": clustered_interval(values),
                }
            )
    return result


def export_run(plan, cases, ledger):
    observed = ledger.episodes()
    rows = []
    request_records = ledger.export()["requests"]
    for episode, row, _ in declared_episodes(plan, cases):
        rows.append(
            {
                **row,
                "episode_id": episode,
                "correct": 0,
                "spent": 0,
                "requests": 0,
                "invalid_actions": 0,
                "seconds": 0,
                "query_ms": [],
                "solver_error": None,
                "missing_answer": True,
                "missing_submission": True,
                "invalid_submission": False,
                "completion": False,
                "tokens": None,
                "cost_usd": 0,
                "error": "missing_episode",
                **observed.get(episode, {}),
            }
        )
    # The ledger is authoritative even if a crash occurs after settlement but
    # before the episode transcript/result is saved.
    for row in rows:
        calls = [q for q in request_records if q["episode"] == row["episode_id"]]
        if calls:
            row["cost_usd"] = sum(q["actual"] or 0 for q in calls) / 1000000
            row["unresolved_cost_reservation_usd"] = (
                sum(q["reserved"] for q in calls if q["actual"] is None) / 1000000
            )
            accounted = [q["usage"] for q in calls if q["usage"] is not None]
            row["tokens"] = (
                {
                    k: sum(u[k] for u in accounted)
                    for k in ("input_tokens", "output_tokens", "total_tokens")
                }
                if accounted
                else None
            )
            if row["tokens"] is not None:
                row["tokens"]["thinking_tokens"] = (
                    sum(u["thinking_tokens"] for u in accounted)
                    if all(u.get("thinking_tokens") is not None for u in accounted)
                    else None
                )
            row["usage_complete"] = len(accounted) == len(calls)
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
                    "selection_policy",
                    "topic_mode",
                    "prompt_style",
                )
            }
        )
        entry.update(
            completion_rate=sum(r["completion"] for r in group) / len(group),
            missing_answers=sum(r["missing_answer"] for r in group),
            invalid_submissions=sum(r["invalid_submission"] for r in group),
            errors=sum(r["error"] is not None for r in group),
            cost_usd=sum(r["cost_usd"] for r in group),
        )
        available = [r for r in group if r["tokens"] is not None]
        entry["tokens"] = (
            {
                k: sum(r["tokens"][k] for r in available)
                for k in ("input_tokens", "output_tokens", "total_tokens")
            }
            if available
            else None
        )
        timed = [r["seconds"] for r in group if r["episode_id"] in observed]
        entry["mean_seconds"] = sum(timed) / len(timed) if timed else None
    costs = {}
    for model in plan["models"]:
        measured = [
            r
            for r in rows
            if r["model"] == model
            and r["tokens"] is not None
            and r["error"] != "budget_stopped"
        ]
        worlds = {}
        for row in measured:
            worlds.setdefault(row["world_group"], []).append(row["cost_usd"])
        values = [sum(v) / len(v) for v in worlds.values()]
        full_count = plan["datasets"]["test"]["cases"] * len(plan["conditions"]) * 3
        costs[model] = {
            "measured_episodes": len(measured),
            "proposed_full_test_episodes": full_count,
            "proposed_full_test_repeats": 3,
            "estimated_usd": sum(r["cost_usd"] for r in measured)
            / len(measured)
            * full_count
            if measured
            else None,
            "mean_episode_cost_world_cluster_ci95": clustered_interval(values)
            if values
            else None,
            "limitations": "Exploratory extrapolation; development selection, incomplete runs, repeats, changing prices, and test distribution can change costs. Local electricity and hardware costs are excluded.",
        }
    missing = sum(r["error"] == "missing_episode" for r in rows)
    return {
        "manifest": {
            "plan_id": plan["plan_id"],
            "execution_split": plan.get("execution_split", "test"),
            "expected_episodes": len(rows),
            "dispatched_episodes": len(observed),
            "missing_episodes": missing,
            "status": "complete"
            if not missing and len(observed) == len(rows)
            else "incomplete",
            "exploratory": plan.get("study_kind") == "exploratory-development-pilot",
            "execution_amendment": plan.get("execution_amendment"),
            "latency_policy": plan.get("latency_policy"),
            "failure_policy": plan["failure_policy"],
        },
        "summary": summary,
        "paired_strategy_gaps": strategy_gaps(rows),
        "paired_model_gaps": paired_model_gaps(rows),
        "larger_study_cost_estimate": costs,
        "episodes": rows,
        "ledger": ledger.export(),
    }


def run_study(plan, root, dry_run=False, provider_factory=make_provider, progress=None):
    verify_study(plan, root, require_models=True)
    cases = execution_cases(plan, root)
    if dry_run:
        return {
            "plan_id": plan["plan_id"],
            "dry_run": True,
            "generation_calls": 0,
            "execution_split": plan.get("execution_split", "test"),
            "cases": len(cases),
            "worlds": len({c["world_group"] for c in cases}),
            "models": plan["models"],
            "episodes_per_model": len(cases)
            * len(plan["conditions"])
            * plan["repeats"],
            "expected_episodes": len(plan["models"])
            * len(cases)
            * len(plan["conditions"])
            * plan["repeats"],
            "local_runtime_pinned": plan.get("local_runtime_pinned"),
            "spending": plan.get("spending"),
        }
    if (
        not plan.get("spending")
        or not plan.get("prices")
        or not plan.get("execution_directory")
    ):
        raise ValueError(
            "native execution needs frozen spending, prices, runtime identities, and execution directory; re-prepare the plan"
        )
    if date.today().isoformat() > plan["prices"]["valid_through"]:
        raise ValueError("frozen pricing expired; prepare a new study")
    if any(not plan["model_runtime_identities"].get(m) for m in plan["models"]):
        raise ValueError("pin all runtime identities before execution")
    output = Path(root) / plan["execution_directory"]
    with execution_lock(output / "runner.lock"):
        ledger = Ledger(output / "ledger.sqlite3", plan)
        stopped = None
        try:
            ledger.guard()
            for model in plan["models"]:
                prior = ledger.model(model)
                if prior and prior["status"] in (
                    "incompatible",
                    "probe_started",
                    "budget_stopped",
                    "accounting_stopped",
                ):
                    continue
                if (
                    provider_factory is make_provider
                    and model.startswith("google/")
                    and not os.environ.get("GOOGLE_API_KEY")
                ):
                    ledger.model_status(
                        model,
                        "credential_unavailable",
                        {"error": "GOOGLE_API_KEY unavailable; no calls made"},
                    )
                    continue
                try:
                    provider = provider_factory(
                        model,
                        model_settings(plan, model),
                        plan["model_runtime_identities"][model],
                    )
                    if not prior or prior["status"] != "compatible":
                        ledger.model_status(
                            model,
                            "probe_started",
                            {
                                "error": "interrupted probes are not automatically repeated"
                            },
                        )
                        compatibility = probe(provider, plan, ledger, output)
                        atomic_json(
                            output / "logs" / (digest(model) + "-compatibility.json"),
                            compatibility,
                        )
                        ledger.model_status(model, "compatible", compatibility)
                        if progress:
                            progress({"model": model, "compatibility": "passed"})
                except (BudgetStop, AccountingStop) as exc:
                    stopped = (
                        "budget_stopped"
                        if isinstance(exc, BudgetStop)
                        else "accounting_stopped"
                    )
                    ledger.model_status(model, stopped, {"error": stopped})
                    break
                except Exception as exc:
                    ledger.model_status(
                        model, "incompatible", {"error": error_label(exc)}
                    )
                    try:
                        ledger.guard()
                    except AccountingStop:
                        stopped = "accounting_stopped"
                        break
                    if progress:
                        progress(
                            {
                                "model": model,
                                "compatibility": "failed",
                                "error": error_label(exc),
                            }
                        )
                    continue
                for episode, row, case in declared_episodes(
                    {**plan, "models": [model]}, cases
                ):
                    if not ledger.begin_episode(episode):
                        continue
                    try:
                        result = play_episode(
                            provider, plan, ledger, episode, row, case, output
                        )
                    except (BudgetStop, AccountingStop) as exc:
                        stopped = (
                            "budget_stopped"
                            if isinstance(exc, BudgetStop)
                            else "accounting_stopped"
                        )
                        ledger.model_status(model, stopped, {"error": stopped})
                        break
                    if progress:
                        progress(
                            {
                                "model": model,
                                "episode_id": episode,
                                "correct": result["correct"],
                                "error": result["error"],
                            }
                        )
                if stopped:
                    break
        except AccountingStop:
            stopped = "accounting_stopped"
        finally:
            result = export_run(plan, cases, ledger)
            if stopped:
                result["manifest"]["status"] = "incomplete"
                result["manifest"]["stop_reason"] = stopped
            atomic_json(output / "results.json", result)
            atomic_json(output / "cost-ledger.json", ledger.export())
            ledger.close()
        return result
