"""Audited source-only amendments preserve spending and episode identities."""

import json
from pathlib import Path

from .config import digest
from .ledger import Ledger, execution_lock
from .study import verify_study


def amend_ledger(previous, amended, root):
    verify_study(amended, root, require_models=True)
    if previous["plan_id"] != digest(
        {k: v for k, v in previous.items() if k != "plan_id"}
    ):
        raise ValueError("previous manifest has changed")
    fields = (
        "models",
        "repeats",
        "conditions",
        "selected_case_ids",
        "execution_split",
        "datasets",
        "generation_config",
        "per_model_settings",
        "provider_settings",
        "model_runtime_identities",
        "spending",
        "prices",
        "execution_directory",
        "token_limit",
        "time_limit_seconds",
        "prompts",
        "protocols",
        "lock_sha256",
        "dependencies",
    )
    if any(previous.get(k) != amended.get(k) for k in fields):
        raise ValueError(
            "amendment cannot change selection, settings, limits, prices, or funding"
        )
    if amended.get("episode_id_namespace") != previous.get(
        "episode_id_namespace", previous["plan_id"]
    ):
        raise ValueError("amendment must preserve every episode identity")
    amendment = amended.get("execution_amendment", {})
    if amendment.get("previous_plan_id") != previous["plan_id"] or not amendment.get(
        "reason"
    ):
        raise ValueError("source amendment needs its preceding manifest and a reason")
    output = Path(root) / previous["execution_directory"]
    with execution_lock(output / "runner.lock"):
        ledger = Ledger(output / "ledger.sqlite3", previous)
        try:
            ledger.guard()
            # All dispatched requests must be settled before changing identity.
            before = ledger.export()
            count = len(ledger.episodes())
            with ledger.db:
                for episode, result in ledger.episodes().items():
                    result.setdefault("source_plan_id", previous["plan_id"])
                    result.setdefault("token_accounting_version", "byte-bound-v1")
                    ledger.db.execute(
                        "UPDATE episodes SET result=? WHERE id=?",
                        (json.dumps(result), episode),
                    )
                for row in ledger.db.execute("SELECT * FROM models").fetchall():
                    # A source-only fix may resume an accounted stop with its
                    # original compatible probe. Unresolved usage is rejected
                    # above; incompatible/unfinished probes stay stopped.
                    if row["status"] == "accounting_stopped":
                        path = (
                            output
                            / "logs"
                            / (digest(row["id"]) + "-compatibility.json")
                        )
                        probe = json.loads(path.read_text())
                        if probe.get("compatible") is not True:
                            raise ValueError(
                                "cannot restore compatibility without its original probe"
                            )
                        ledger.db.execute(
                            "UPDATE models SET status='compatible',result=? WHERE id=?",
                            (json.dumps(probe), row["id"]),
                        )
                ledger.db.execute(
                    "UPDATE metadata SET value=? WHERE key='plan_id'",
                    (amended["plan_id"],),
                )
                ledger.db.execute("DROP TRIGGER IF EXISTS maintenance_stop")
            after = ledger.export()
            if (
                before["requests"] != after["requests"]
                or before["committed_usd"] != after["committed_usd"]
            ):
                raise RuntimeError("amendment altered request accounting")
            return {
                "previous_plan_id": previous["plan_id"],
                "plan_id": amended["plan_id"],
                "preserved_episodes": count,
                "preserved_committed_usd": after["committed_usd"],
                "generation_calls": 0,
            }
        finally:
            ledger.close()
