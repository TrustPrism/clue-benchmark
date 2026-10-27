"""One outcome-independent extension of the closed October 27 study.

Prepare/execute only against preserved original package sources. The combined
allowance is $10 INCLUDING the original study, not a fresh $10 per phase.
"""

import argparse
import fcntl
import json
import random
import shutil
import sqlite3
from pathlib import Path

from clue_benchmark.community_bundle import file_hash, source_hashes
from clue_benchmark.community_evaluation import _cost, check_plan, run_evaluation
from clue_benchmark.config import digest
from clue_benchmark.dataset import atomic_json
from clue_benchmark.followup_runner import checked_jobs

CAP = 10_000_000


def closed_prior(root):
    """Prove every old slot is settled, identity-valid and non-replayable."""
    root = Path(root)
    study = json.loads((root / "study.json").read_text())
    jobs = checked_jobs(root, study)
    seen, total, identities = set(), 0, []
    for index, (job, plan) in enumerate(jobs):
        ledger = (
            root
            / "execution"
            / ("probe" if index == 0 else job["directory"])
            / "requests.sqlite"
        )
        if not ledger.is_file():
            raise ValueError("initial study is not fully settled")
        db = sqlite3.connect(ledger.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            rows = db.execute(
                "SELECT id,status,maximum,actual,result FROM requests ORDER BY id"
            ).fetchall()
            ledger_id = db.execute("SELECT id FROM identity").fetchone()[0]
        finally:
            db.close()
        expected = run_evaluation(
            plan, root / job["directory"], root / "unused", dry_run=True
        )["requests"]
        if (
            ledger_id != plan["plan_id"]
            or {r[0] for r in rows} != {r["request_id"] for r in expected}
            or len(rows) != plan["max_requests"]
        ):
            raise ValueError(
                "initial ledger does not contain exactly its assigned slots"
            )
        models = {m["id"]: m for m in plan["models"]}
        for ident, status, maximum, actual, saved in rows:
            if (
                status != "settled"
                or type(actual) is not int
                or not 0 <= actual <= maximum
                or ident in seen
            ):
                raise ValueError(
                    "initial study has unresolved, breached or repeated requests"
                )
            receipt = json.loads(saved)
            model = models[receipt["model"]]
            if (
                not receipt["usage_known"]
                or receipt["returned_model"] != model["identity"]
                or _cost(model, receipt["input_tokens"], receipt["output_tokens"])
                != actual
            ):
                raise ValueError("initial accounting or returned identity differs")
            seen.add(ident)
            total += actual
        identities.append(
            {
                "plan_id": plan["plan_id"],
                "rows_sha256": digest(rows),
                "requests": len(rows),
            }
        )
    if len(seen) != study["assigned_calls"] + 2:
        raise ValueError("initial cohort is not closed")
    return {
        "manifest_id": study["manifest_id"],
        "settled_microdollars": total,
        "held_microdollars": 0,
        "closed_requests": len(seen),
        "ledgers": identities,
    }


def enforce_total(prior, ceilings):
    if (
        prior["held_microdollars"] != 0
        or any(type(c) is not int or c < 0 for c in ceilings)
        or prior["settled_microdollars"] + sum(ceilings) > CAP
    ):
        raise ValueError(
            "initial settled usage plus extension maximum exceeds combined $10 cap"
        )
    return prior["settled_microdollars"] + sum(ceilings)


def prepare(initial, output):
    initial, output = Path(initial), Path(output)
    prior = closed_prior(initial)
    study = json.loads((initial / "study.json").read_text())
    chosen = {b["world_id"] for b in study["selected_blocks"]}
    unused = [b for b in study["candidate_blocks"] if b["world_id"] not in chosen]
    if len(unused) != 4 or [b["burden"] for b in unused].count(4) != 2:
        raise ValueError("expected exactly four previously screened unmeasured worlds")
    for block in unused:
        for job in block["jobs"]:
            if (initial / "execution" / job["directory"]).exists():
                raise ValueError("extension candidate already has model outcomes")
            plan = json.loads((initial / job["directory"] / "plan.json").read_text())
            check_plan(plan, initial / job["directory"])
            if (
                file_hash(initial / job["directory"] / "payloads.jsonl")
                != job["payloads_sha256"]
            ):
                raise ValueError("exact payload changed")
    maximum = enforce_total(
        prior, [j["ceiling_microdollars"] for b in unused for j in b["jobs"]]
    )
    output.mkdir(parents=True, exist_ok=False)
    rng = random.Random(0)
    rng.shuffle(unused)
    for block in unused:
        rng.shuffle(block["jobs"])
    frozen = output / "frozen-source" / "clue_benchmark"
    shutil.copytree(
        Path(__import__("clue_benchmark").__file__).parent,
        frozen,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    plan = {
        "schema_version": "clue-nuisance-extension-1",
        "initial_root": str(initial),
        "prior": prior,
        "sources": source_hashes(),
        "runner_sha256": file_hash(__file__),
        "selected_blocks": unused,
        "scored_calls": 48,
        "new_probe_calls": 0,
        "cap_microdollars": CAP,
        "extension_maximum_microdollars": maximum - prior["settled_microdollars"],
        "combined_maximum_microdollars": maximum,
        "primary_endpoint": study["primary_endpoint"],
        "interpretation": "One final post-result expansion using every remaining pre-generated world. Report initial/extension phases separately and combined descriptive estimates; no equivalence or powered-confirmation claim.",
        "selection": "All four unmeasured original seed-prefix candidates, irrespective of prior model outcomes. No further paid expansion.",
        "authorization": "actual user explicitly requested one more expansion under the combined $10 cap",
    }
    plan["extension_id"] = digest(plan)
    atomic_json(output / "extension-plan.json", plan)
    return plan


def execute(output, authorization):
    output = Path(output)
    plan = json.loads((output / "extension-plan.json").read_text())
    if (
        plan["extension_id"]
        != digest({k: v for k, v in plan.items() if k != "extension_id"})
        or file_hash(__file__) != plan["runner_sha256"]
        or source_hashes() != plan["sources"]
    ):
        raise ValueError("frozen extension runner/source identity changed")
    expected = {
        "schema_version": "clue-extension-authorization-1",
        "extension_id": plan["extension_id"],
        "combined_cap_microdollars": CAP,
        "new_max_requests": 48,
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
            "actual human extension-bound execution authorization required"
        )
    initial = Path(plan["initial_root"])
    with (
        (initial / "execution/study.lock").open("a") as initial_lock,
        (output / "extension.lock").open("a") as extension_lock,
    ):
        fcntl.flock(initial_lock, fcntl.LOCK_EX)
        fcntl.flock(extension_lock, fcntl.LOCK_EX)
        prior = closed_prior(initial)
        if prior != plan["prior"]:
            raise ValueError("closed initial accounting changed")
        jobs = [j for b in plan["selected_blocks"] for j in b["jobs"]]
        enforce_total(prior, [j["ceiling_microdollars"] for j in jobs])
        reports = []
        for job in jobs:
            child = json.loads((initial / job["directory"] / "plan.json").read_text())
            check_plan(child, initial / job["directory"])
            if (
                child["plan_id"] != job["plan_id"]
                or child["spending_ceiling_microdollars"] != job["ceiling_microdollars"]
                or file_hash(initial / job["directory"] / "payloads.jsonl")
                != job["payloads_sha256"]
            ):
                raise ValueError("extension child or payload changed")
            auth = {
                "schema_version": "clue-community-authorization-1",
                "plan_id": child["plan_id"],
                "approved_by": authorization["approved_by"],
                "approved_at": authorization["approved_at"],
                "spending_ceiling_microdollars": child["spending_ceiling_microdollars"],
                "max_requests": child["max_requests"],
            }
            report = run_evaluation(
                child,
                initial / job["directory"],
                output / "execution" / job["directory"],
                dry_run=False,
                authorization=auth,
            )
            reports.append(report)
            atomic_json(
                output / "progress.json",
                {
                    "completed_children": len(reports),
                    "total_children": 12,
                    "initial_settled_microdollars": prior["settled_microdollars"],
                    "extension_settled_microdollars": sum(
                        r["accounting"]["settled_microdollars"] for r in reports
                    ),
                    "held_microdollars": sum(
                        r["accounting"]["held_microdollars"] for r in reports
                    ),
                },
            )
            if not report["complete"]:
                break
        result = {
            "extension_id": plan["extension_id"],
            "status": "completed"
            if len(reports) == 12 and all(r["complete"] for r in reports)
            else "stopped",
            "prior": prior,
            "reports": reports,
            "combined_settled_microdollars": prior["settled_microdollars"]
            + sum(r["accounting"]["settled_microdollars"] for r in reports),
            "held_microdollars": sum(
                r["accounting"]["held_microdollars"] for r in reports
            ),
            "combined_cap_microdollars": CAP,
        }
        atomic_json(output / "execution-summary.json", result)
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("initial")
    p.add_argument("--output", required=True)
    p = sub.add_parser("execute")
    p.add_argument("directory")
    p.add_argument("--authorization", required=True)
    args = parser.parse_args()
    result = (
        prepare(args.initial, args.output)
        if args.command == "prepare"
        else execute(args.directory, json.loads(Path(args.authorization).read_text()))
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in {"selected_blocks", "sources", "reports", "prior"}
            }
        )
    )
