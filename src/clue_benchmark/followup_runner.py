"""Single-allowance, sequential wrapper over durable no-repeat native ledgers.

Only actual human-supplied manifest-bound authorization enables execution.
No authorization files are produced. Dry runs never construct a provider client.
"""

import json
from pathlib import Path

from .community_bundle import file_hash
from .community_evaluation import check_plan, run_evaluation
from .config import digest
from .nuisance_followup import CAP, PROBES


def checked_jobs(root, study):
    if study.get("manifest_id") != digest(
        {k: v for k, v in study.items() if k != "manifest_id"}
    ):
        raise ValueError("follow-up manifest identity mismatch")
    if study.get("status") != "prepared_pending_access_and_authorization":
        raise ValueError("no affordable complete frozen design")
    jobs = [study["probe_job"]] + [
        job for block in study["selected_blocks"] for job in block["jobs"]
    ]
    plans = []
    for job in jobs:
        relative = Path(job["directory"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("job path escapes study")
        directory = Path(root) / relative
        plan = json.loads((directory / job.get("plan_file", "plan.json")).read_text())
        check_plan(plan, directory)
        if (
            "payloads_sha256" in job
            and file_hash(directory / "payloads.jsonl") != job["payloads_sha256"]
        ):
            raise ValueError("frozen native payload hash mismatch")
        if (
            plan["plan_id"] != job["plan_id"]
            or plan["spending_ceiling_microdollars"] != job["ceiling_microdollars"]
        ):
            raise ValueError("child plan changed")
        if plan["retries"] != 0 or any(
            m.get("identity") != m["model"] for m in plan["models"]
        ):
            raise ValueError(
                "follow-up requires zero retries and exact model identities"
            )
        plans.append((job, plan))
    if (
        jobs[0]["ceiling_microdollars"] > PROBES
        or sum(j["ceiling_microdollars"] for j in jobs[1:]) > CAP - PROBES
        or sum(j["ceiling_microdollars"] for j in jobs) > CAP
    ):
        raise ValueError("combined child and probe ceilings exceed the study allowance")
    return plans


def run_followup(root, authorization=None, *, dry_run=True, transports=None):
    root = Path(root)
    study = json.loads((root / "study.json").read_text())
    plans = checked_jobs(root, study)
    if dry_run:
        requests = []
        for job, plan in plans:
            result = run_evaluation(
                plan, root / job["directory"], root / "unused", dry_run=True
            )
            requests.extend(result["requests"])
        if not all(r["context_fits"] for r in requests):
            raise ValueError("frozen matched context no longer fits")
        return {
            "status": "dry_run",
            "manifest_id": study["manifest_id"],
            "model_calls": 0,
            "requests": len(requests),
            "combined_ceiling_microdollars": sum(
                p["spending_ceiling_microdollars"] for _, p in plans
            ),
            "external_inference": False,
        }
    expected = {
        "schema_version": "clue-followup-authorization-1",
        "manifest_id": study["manifest_id"],
        "spending_ceiling_microdollars": CAP,
        "max_requests": study["assigned_calls"] + 2,
    }
    if (
        not isinstance(authorization, dict)
        or set(authorization) != set(expected) | {"approved_by", "approved_at"}
        or any(authorization[k] != v for k, v in expected.items())
        or any(
            not isinstance(authorization[k], str) or not authorization[k].strip()
            for k in ("approved_by", "approved_at")
        )
    ):
        raise PermissionError(
            "new human manifest-bound follow-up authorization required"
        )
    import fcntl

    # Keep one fixed directory/ledger per immutable child. A fresh process walks
    # them in the same order; any unknown held request stops before later jobs.
    execution = root / "execution"
    execution.mkdir(exist_ok=True)
    reports = []
    with (execution / "study.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for index, (job, plan) in enumerate(plans):
            child_auth = {
                "schema_version": "clue-community-authorization-1",
                "plan_id": plan["plan_id"],
                "approved_by": authorization["approved_by"],
                "approved_at": authorization["approved_at"],
                "spending_ceiling_microdollars": plan["spending_ceiling_microdollars"],
                "max_requests": plan["max_requests"],
            }
            result = run_evaluation(
                plan,
                root / job["directory"],
                execution / ("probe" if index == 0 else job["directory"]),
                dry_run=False,
                authorization=child_auth,
                transports=transports,
            )
            reports.append(result)
            if not result["complete"]:
                break
            if index == 0 and (
                len(result["episodes"]) != 2
                or not all(
                    e.get("protocol_valid") and e.get("usage_known")
                    for e in result["episodes"]
                )
            ):
                break
    return {
        "status": "completed"
        if len(reports) == len(plans) and all(r["complete"] for r in reports)
        else "stopped",
        "reports": reports,
        "manifest_id": study["manifest_id"],
        "combined_ceiling_microdollars": sum(
            p["spending_ceiling_microdollars"] for _, p in plans
        ),
    }
