"""Proposed explicit incomplete-usage recovery: hold maxima and use fresh episodes.

This controller changes no native tools, generations, scoring, or token settings.
It never retries an episode or treats missing usage as a zero charge. A frozen,
user-authorized policy allows failed timeouts to be held at their full maximum;
Only explicit authorization permits incomplete usage to be held; other unresolved errors still stop paid execution.
"""

import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path

from clue_benchmark.config import digest
from clue_benchmark.dataset import atomic_json
from clue_benchmark.ledger import AccountingStop, Ledger, execution_lock
from clue_benchmark.runner import run_study
from clue_benchmark.study import verify_study

POLICY = "maximum-hold-incomplete-usage-v1"


def restore_reserved_failures(ledger, plan, output):
    if plan.get("continuation_policy", {}).get("failed_timeout_recovery") != POLICY:
        raise ValueError("explicit frozen timeout policy required")
    if (
        plan.get("continuation_policy", {}).get("incomplete_usage_authorized")
        is not True
    ):
        raise ValueError("explicit incomplete-usage authorization required")
    requests = ledger.export()["requests"]
    observed = ledger.episodes()
    latest = {}
    for item in ledger.db.execute("SELECT result FROM episodes ORDER BY rowid"):
        if item[0]:
            row = json.loads(item[0])
            latest[row["model"]] = row
    models = []
    probes = {}
    for row in ledger.export()["models"]:
        m = row["id"]
        if (
            m.startswith("google/")
            and row["status"] == "accounting_stopped"
            and latest.get(m, {}).get("error") in ("timeout", "missing_usage")
        ):
            probe = json.loads(
                (output / "logs" / (digest(m) + "-compatibility.json")).read_text()
            )
            if probe.get("compatible") is not True:
                raise AccountingStop("original native compatibility proof required")
            probes[m] = probe
            models.append(m)
    unresolved = [
        q
        for q in requests
        if q["model"].startswith("google/") and q["status"] in ("reserved", "uncertain")
    ]
    for q in unresolved:
        if (
            q["status"] != "uncertain"
            or q["error"] not in ("timeout", "missing_usage")
            or q["actual"] is not None
            or q["model"] not in models
            or observed.get(q["episode"], {}).get("error")
            not in ("timeout", "missing_usage")
        ):
            raise AccountingStop("unresolved non-timeout usage must remain stopped")
        if q["reserved"] <= 0 or not q["config"]:
            raise AccountingStop("missing conservative timeout reservation")
    if not models:
        return None
    # Another paid model can be paused by the family guard before a new episode
    # begins. Restore that pause only after every unknown charge is a validated
    # failed timeout, and never restore a protocol/usage incompatibility.
    for state in ledger.export()["models"]:
        m = state["id"]
        if (
            m.startswith("google/")
            and state["status"] == "accounting_stopped"
            and m not in models
            and m in latest
            and latest[m].get("error") in (None, "token_limit", "service_unavailable")
        ):
            probe = json.loads(
                (output / "logs" / (digest(m) + "-compatibility.json")).read_text()
            )
            if probe.get("compatible") is not True:
                raise AccountingStop("original native compatibility proof required")
            models.append(m)
            probes[m] = probe
    before = {
        "committed_usd": ledger.committed() / 1e6,
        "requests": len(requests),
        "episodes": len(observed),
    }
    ledger.db.execute("BEGIN IMMEDIATE")
    try:
        for q in unresolved:
            ledger.db.execute(
                "UPDATE requests SET status='held',held_reason=? WHERE id=? AND status='uncertain'",
                (
                    "User-authorized incomplete-usage failure recovery; full maximum retained; no episode/request retry",
                    q["id"],
                ),
            )
        for m in models:
            ledger.db.execute(
                "UPDATE models SET status='compatible',result=? WHERE id=?",
                (json.dumps(probes[m]), m),
            )
        ledger.db.commit()
    except BaseException:
        ledger.db.rollback()
        raise
    after = ledger.export()
    if (
        before["committed_usd"] != after["committed_usd"]
        or before["requests"] != len(after["requests"])
        or before["episodes"] != len(ledger.episodes())
        or observed != ledger.episodes()
    ):
        raise RuntimeError(
            "recovery must preserve costs, requests, episodes and scores"
        )
    audit = {
        "plan_id": plan["plan_id"],
        "policy": POLICY,
        "held_failed_request_ids": [q["id"] for q in unresolved],
        "resumed_models": models,
        **before,
        "generation_calls": 0,
        "failed_episodes_replayed": 0,
        "maximum_charge_retained": True,
    }
    path = output / "accounting-recovery.json"
    records = json.loads(path.read_text()) if path.exists() else {"events": []}
    records["events"].append(audit)
    atomic_json(path, records)
    return audit


def amend(previous, plan, root):
    """Change only the frozen failed-timeout policy; local native execution is unchanged."""
    verify_study(plan, root, require_models=True)
    if previous["plan_id"] != digest(
        {k: v for k, v in previous.items() if k != "plan_id"}
    ):
        raise ValueError("preceding manifest digest differs")
    allowed = {
        "plan_id",
        "continuation_policy",
        "execution_controller",
        "execution_amendment",
    }
    if any(
        previous.get(k) != plan.get(k)
        for k in set(previous) | set(plan)
        if k not in allowed
    ):
        raise ValueError(
            "timeout amendment cannot alter cases, costs, limits or native settings"
        )
    if (
        plan.get("execution_amendment", {}).get("previous_plan_id")
        != previous["plan_id"]
    ):
        raise ValueError("preceding plan must be declared")
    output = Path(root) / plan["execution_directory"]
    with execution_lock(output / "runner-google.lock"):
        ledger = Ledger(output / "ledger.sqlite3", previous)
        try:
            # Record the original state before any model/accounting recovery.
            atomic_json(
                output / "amendments" / "before-usage-recovery-cost-ledger.json",
                ledger.export(),
            )
            restored = restore_reserved_failures(ledger, plan, output)
            if not restored:
                raise ValueError("no accounted timeout to restore")
            with ledger.db:
                ledger.db.execute(
                    "UPDATE metadata SET value=? WHERE key='plan_id'",
                    (plan["plan_id"],),
                )
            atomic_json(
                output / "usage-recovery-amendment-audit.json",
                {
                    "previous_plan_id": previous["plan_id"],
                    "plan_id": plan["plan_id"],
                    "reason": plan["execution_amendment"]["reason"],
                    "preserved_committed_usd": ledger.committed() / 1e6,
                    "preserved_episode_ids": True,
                    "active_local_runner_uses_preceding_plan": True,
                    "native_implementation_unchanged": True,
                    "generation_calls": 0,
                },
            )
        finally:
            ledger.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plan")
    parser.add_argument("--root", default=".")
    parser.add_argument("--amend-from")
    args = parser.parse_args()
    root = Path(args.root)
    plan = json.loads(Path(args.plan).read_text())
    if (
        plan.get("continuation_policy", {}).get("incomplete_usage_authorized")
        is not True
    ):
        raise ValueError("proposed incomplete-usage recovery is not authorized")
    controller = plan.get("execution_controller", {})
    if (
        controller.get("sha256")
        != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    ):
        raise ValueError("frozen controller implementation differs")
    if args.amend_from:
        amend(json.loads(Path(args.amend_from).read_text()), plan, root)
        print(
            json.dumps({"amendment_applied": True, "generation_calls": 0}), flush=True
        )
        return
    verify_study(plan, root, require_models=True)
    output = root / plan["execution_directory"]
    if not (output / "ledger.sqlite3").exists():
        raise ValueError("existing paid ledger required")
    had_key = "GOOGLE_API_KEY" in os.environ
    if not had_key:
        os.environ["GOOGLE_API_KEY"] = getpass.getpass(
            "Google API key (hidden input): "
        )
    try:
        while True:
            result = run_study(
                plan,
                root,
                models=[m for m in plan["models"] if m.startswith("google/")],
                progress=lambda row: print(json.dumps(row), flush=True),
            )
            with execution_lock(output / "runner-google.lock"):
                ledger = Ledger(output / "ledger.sqlite3", plan)
                try:
                    audit = restore_reserved_failures(ledger, plan, output)
                except AccountingStop:
                    print(
                        json.dumps(
                            {
                                "stop": "unresolved_unclassified_usage",
                                "committed_usd": ledger.committed() / 1e6,
                            }
                        ),
                        flush=True,
                    )
                    return
                finally:
                    ledger.close()
            if not audit:
                print(
                    json.dumps(
                        {
                            "stop": result["manifest"].get(
                                "stop_reason", "paid_schedule_finished"
                            ),
                            "committed_usd": result["ledger"]["committed_usd"],
                        }
                    ),
                    flush=True,
                )
                return
            print(json.dumps({"recovery": audit}), flush=True)
    finally:
        if not had_key:
            os.environ.pop("GOOGLE_API_KEY", None)


if __name__ == "__main__":
    main()
