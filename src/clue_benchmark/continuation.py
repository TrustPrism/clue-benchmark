"""Frozen, user-authorized development continuation with one cumulative budget."""

import json
import shutil
import sqlite3
from pathlib import Path

from .config import digest
from .dataset import atomic_json, read_cases
from .ledger import Ledger, execution_lock
from .pilot import PILOT_MODELS, prepare_pilot
from .study import sha256, verify_study


def prepare_continuation(
    previous, root, ceiling=25.0, execution_directory="results/pilot-v0.3-continued"
):
    root = Path(root)
    if previous["plan_id"] != digest(
        {k: v for k, v in previous.items() if k != "plan_id"}
    ):
        raise ValueError("previous manifest has changed")
    if not 0 < ceiling <= previous["spending"]["combined_google_usd"]:
        raise ValueError("continuation must lower or retain the cumulative ceiling")
    plan = prepare_pilot(
        root / previous["datasets"]["dev"]["path"],
        root / previous["datasets"]["test"]["path"],
        root,
        previous["model_runtime_identities"][PILOT_MODELS[2]],
        execution_directory,
    )
    for field in (
        "models",
        "repeats",
        "conditions",
        "datasets",
        "generation_config",
        "per_model_settings",
        "provider_settings",
        "model_runtime_identities",
        "prices",
        "token_limit",
        "time_limit_seconds",
        "prompts",
        "protocols",
        "lock_sha256",
        "dependencies",
    ):
        if plan.get(field) != previous.get(field):
            raise ValueError(
                "continuation changed frozen model or dataset settings: " + field
            )
    cases = read_cases(root / plan["datasets"]["dev"]["path"])
    if any(c["split"] != "dev" or c.get("held_out") for c in cases):
        raise ValueError("only development cases are authorized")
    all_ids = sorted(c["case_id"] for c in cases)
    pilot_ids = previous["selected_case_ids"]
    plan.update(
        study_kind="exploratory-development-continuation",
        selected_case_ids=all_ids,
        selected_world_ids=sorted({c["world_group"] for c in cases}),
        initial_pilot_case_ids=pilot_ids,
        model_case_ids={
            PILOT_MODELS[0]: all_ids,
            PILOT_MODELS[1]: all_ids,
            PILOT_MODELS[2]: pilot_ids,
        },
        episode_id_namespace=previous.get("episode_id_namespace", previous["plan_id"]),
        execution_schedule="paired-world-round-robin-v1",
        selection={
            "seed": 0,
            "google_worlds_per_size": 36,
            "local_worlds_per_size": 4,
            "retain_density_pair": True,
            "priority": "Complete original pilot first; rotate suspect sizes and paired conditions before expanding development coverage",
        },
        spending={
            "combined_google_usd": ceiling,
            "includes_compatibility_probes": True,
            "includes_prior_pilot_and_all_held_reservations": True,
        },
        continuation_policy={
            "hold_service_error_codes": [503],
            "local_accounting_independent": True,
            "automatic_retries": 0,
            "unknown_success_usage": "stop",
            "authorization": "User reported the prior failure as HTTP 503 and authorized continuation, then lowered this phase to $25 cumulative; preserve maximum failed-request reservations and keep the other $25 for a later study.",
        },
        prior_execution={
            "plan_id": previous["plan_id"],
            "directory": previous["execution_directory"],
            "implementation": previous["implementation"],
        },
        token_accounting_version="usage-headroom-v3",
        token_accounting={
            "google": "max(native count plus schema, prior reported input plus twice prior output plus new tool-result bytes), 12.5 percent headroom plus 1024 tokens",
            "ollama": "prior native prompt/eval usage plus new tool-result byte bound; initial UTF-8 bound plus 2048 overhead",
        },
        primary_analysis="Expanded development Gemini comparison excludes the original 12 diagnostic worlds. Paired conditions/models and world-clustered uncertainty; stopped and missing rows remain incorrect with separate coverage.",
        execution="Explicit user-authorized development continuation only; cumulative $25 including the original pilot. Qwen completes the original 24-case pilot. No test execution or second $25 allocation.",
    )
    for model in PILOT_MODELS[:2]:
        plan["provider_settings"][model]["input_safety_margin"] = 1024
    plan["episodes_by_model"] = {
        m: len(ids) * len(plan["conditions"]) * plan["repeats"]
        for m, ids in plan["model_case_ids"].items()
    }
    plan["expected_episodes"] = sum(plan["episodes_by_model"].values())
    plan.pop("episodes_per_model", None)
    plan.pop("plan_id", None)
    return {**plan, "plan_id": digest(plan)}


def initialize_continuation(previous, plan, root, held_request_ids):
    root = Path(root)
    verify_study(plan, root, require_models=True)
    if (
        plan["prior_execution"]["plan_id"] != previous["plan_id"]
        or plan["initial_pilot_case_ids"] != previous["selected_case_ids"]
    ):
        raise ValueError("continuation must preserve its preceding pilot")
    source = root / previous["execution_directory"]
    target = root / plan["execution_directory"]
    if target.resolve() == source.resolve() or (target / "ledger.sqlite3").exists():
        raise ValueError(
            "continuation needs a new directory and cannot reset an existing ledger"
        )
    target.mkdir(parents=True, exist_ok=True)
    with execution_lock(source / "runner.lock"):
        with (
            sqlite3.connect(source / "ledger.sqlite3") as src,
            sqlite3.connect(target / "ledger.sqlite3") as dst,
        ):
            src.backup(dst)
        source_hash = sha256(source / "ledger.sqlite3")
        shutil.copytree(source / "logs", target / "logs")
    ledger = Ledger(target / "ledger.sqlite3", previous)
    try:
        before = ledger.export()
        if ledger.committed() > int(plan["spending"]["combined_google_usd"] * 1000000):
            raise ValueError("prior commitment exceeds the new cumulative ceiling")
        unresolved = {
            r["id"]
            for r in before["requests"]
            if r["status"] in ("reserved", "uncertain")
        }
        if unresolved != set(held_request_ids):
            raise ValueError(
                "every unresolved request must have explicit user-reported 503 evidence"
            )
        ledger.policy = plan["continuation_policy"]
        for rid in held_request_ids:
            ledger.hold(
                rid,
                503,
                "User reported HTTP 503 and authorized continuation; full maximum retained; no retry",
            )
        with ledger.db:
            for episode, result in ledger.episodes().items():
                result.setdefault("source_plan_id", previous["plan_id"])
                ledger.db.execute(
                    "UPDATE episodes SET result=? WHERE id=?",
                    (json.dumps(result), episode),
                )
            for row in before["models"]:
                if row["status"] == "accounting_stopped":
                    evidence = json.loads(
                        (
                            source
                            / "logs"
                            / (digest(row["id"]) + "-compatibility.json")
                        ).read_text()
                    )
                    if evidence.get("compatible") is not True:
                        raise ValueError("native compatibility evidence unavailable")
                    evidence["inherited_from_plan_id"] = previous["plan_id"]
                    ledger.model_status(row["id"], "compatible", evidence)
            ledger.db.execute(
                "UPDATE metadata SET value=? WHERE key='plan_id'", (plan["plan_id"],)
            )
            ledger.db.execute(
                "UPDATE metadata SET value=? WHERE key='ceiling'",
                (str(int(plan["spending"]["combined_google_usd"] * 1000000)),),
            )
        ledger.ceiling = int(plan["spending"]["combined_google_usd"] * 1000000)
        after = ledger.export()
        if before["committed_usd"] != after["committed_usd"] or len(
            before["requests"]
        ) != len(after["requests"]):
            raise RuntimeError("continuation altered prior request accounting")
        audit = {
            "previous_plan_id": previous["plan_id"],
            "plan_id": plan["plan_id"],
            "source_ledger_sha256": source_hash,
            "preserved_episodes": len(ledger.episodes()),
            "preserved_requests": len(before["requests"]),
            "preserved_committed_usd": after["committed_usd"],
            "held_request_ids": held_request_ids,
            "new_cumulative_ceiling_usd": after["ceiling_usd"],
            "generation_calls": 0,
        }
        atomic_json(target / "continuation-audit.json", audit)
        return audit
    finally:
        ledger.close()
