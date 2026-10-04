"""One-time local completion watcher; makes no model requests or new allocations."""

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from clue_benchmark.dataset import atomic_json
from clue_benchmark.study import verify_study


class StepFailed(RuntimeError):
    pass


def process_identity(pid):
    response = subprocess.run(
        ["ps", "-p", str(pid), "-o", "lstart=", "-o", "stat="],
        capture_output=True,
        text=True,
        check=False,
    )
    identity = response.stdout.strip()
    return (
        " ".join(identity.split()[:-1])
        if response.returncode == 0 and identity and "Z" not in identity.split()[-1]
        else None
    )


def saved_status(output):
    with sqlite3.connect(f"file:{output / 'ledger.sqlite3'}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN")
        finished = db.execute(
            "SELECT count(*) FROM episodes WHERE result IS NOT NULL"
        ).fetchone()[0]
        inflight = db.execute(
            "SELECT count(*) FROM episodes WHERE status='started'"
        ).fetchone()[0]
        committed = db.execute(
            "SELECT COALESCE(sum(COALESCE(actual,reserved)),0) FROM requests"
        ).fetchone()[0]
        ceiling = int(
            db.execute("SELECT value FROM metadata WHERE key='ceiling'").fetchone()[0]
        )
        assert ceiling == 25000000 and committed <= ceiling
        return {
            "finished": finished,
            "in_progress": inflight,
            "committed_usd": committed / 1e6,
            "ceiling_usd": ceiling / 1e6,
            "models": [dict(r) for r in db.execute("SELECT id,status FROM models")],
        }


def check_credentials(root, paths):
    pattern = re.compile(rb"(?:AIza[0-9A-Za-z_-]{20,}|AQ\.[0-9A-Za-z_-]{20,})")
    for relative in paths:
        path = root / relative
        if path.is_file() and pattern.search(path.read_bytes()):
            raise StepFailed(
                "credential pattern found in a deliverable; publication stopped"
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plan")
    parser.add_argument("--root", default=".")
    parser.add_argument("--paid-pid", type=int, required=True)
    parser.add_argument("--local-pid", type=int, required=True)
    parser.add_argument("--plot-python", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text())
    output = root / plan["execution_directory"]
    state_path = output / "completion-state.json"
    assert plan["spending"]["combined_google_usd"] == 25
    verify_study(plan, root, require_models=True)
    identities = {p: process_identity(p) for p in (args.paid_pid, args.local_pid)}
    verification = {
        "model_requests_by_finalizer": 0,
        "second_allocation_executed": False,
        "checks": {},
    }

    def state(phase, **kwargs):
        atomic_json(
            state_path,
            {
                "phase": phase,
                "updated_utc": datetime.now(timezone.utc).isoformat(),
                "plan_id": plan["plan_id"],
                **kwargs,
            },
        )

    def run(name, command):
        state("finalizing", step=name)
        response = subprocess.run(
            command, cwd=root, capture_output=True, text=True, check=False
        )
        if response.returncode:
            raise StepFailed(
                f"{name} failed with status {response.returncode}; saved artifacts preserved"
            )
        verification["checks"][name] = {
            "passed": True,
            "output": response.stdout[-3000:],
        }
        return response.stdout

    try:
        while any(
            identity is not None and process_identity(pid) == identity
            for pid, identity in identities.items()
        ):
            state("running", **saved_status(output))
            time.sleep(30)
        # Kernel locks must also be clear before final export. Native controller
        # can release its family lock between recovery rounds, so PIDs are primary.
        from clue_benchmark.ledger import execution_lock

        with (
            execution_lock(output / "runner-google.lock"),
            execution_lock(output / "runner-ollama.lock"),
        ):
            status = saved_status(output)
        python = str(root / ".venv/bin/python")
        run(
            "aggregate_export", [python, "scripts/export_native_run.py", str(plan_path)]
        )
        run(
            "evidence_diagnostics",
            [python, "scripts/evidence_diagnostics.py", str(plan_path)],
        )
        run(
            "scientific_report",
            [python, "scripts/report_continuation.py", str(plan_path), "--final"],
        )
        run(
            "static_scientific_figures",
            [
                args.plot_python,
                "scripts/plot_continuation.py",
                str(output / "analysis-summary.json"),
            ],
        )
        run("automated_tests", [python, "-m", "pytest", "-q"])
        run("lint", [str(root / ".venv/bin/ruff"), "check", "src", "tests", "scripts"])
        run(
            "format",
            [
                str(root / ".venv/bin/ruff"),
                "format",
                "--check",
                "src",
                "tests",
                "scripts",
            ],
        )
        run("release_integrity", [python, "scripts/check_release.py"])
        run("original_source_provenance", [python, "scripts/verify_source.py"])
        original_sha = hashlib.sha256(
            (root / "results/pilot-v0.3/ledger.sqlite3").read_bytes()
        ).hexdigest()
        assert (
            original_sha
            == "44d730d5285dc8574080bf308589c9656517789fcbf8988f3da38e3caa3d1334"
        )
        verify_study(plan, root, require_models=True)
        assert (
            hashlib.sha256(
                (root / plan["execution_controller"]["path"]).read_bytes()
            ).hexdigest()
            == plan["execution_controller"]["sha256"]
        )
        result = json.loads((output / "results.json").read_text())
        episodes = result["episodes"]
        requests = result["ledger"]["requests"]
        assert len({r["episode_id"] for r in episodes}) == 4104
        assert len({r["id"] for r in requests}) == len(requests)
        assert (
            result["ledger"]["ceiling_usd"] == 25
            and result["ledger"]["committed_usd"] <= 25
        )
        assert not any(r["case_id"] not in plan["selected_case_ids"] for r in episodes)
        assert all(
            r["actual"] is None or r["actual"] <= r["reserved"] for r in requests
        )
        original_costs = json.loads(
            (root / "results/pilot-v0.3/cost-ledger.json").read_text()
        )["requests"]
        current = {r["id"]: r for r in requests}
        for row in original_costs:
            assert all(
                row[k] == current[row["id"]][k]
                for k in (
                    "id",
                    "episode",
                    "model",
                    "phase",
                    "reserved",
                    "actual",
                    "usage",
                    "error",
                    "created",
                )
            )
        verification.update(
            original_ledger_sha256=original_sha,
            original_requests_preserved=len(original_costs),
            frozen_controller_verified=True,
            no_duplicate_episode_ids=True,
            no_test_model_execution=True,
            **status,
        )
        privacy = run(
            "repository_privacy", [python, "/private/tmp/clue-private-github-check.py"]
        )
        if not any(
            json.loads(line).get("private") is True
            for line in privacy.splitlines()
            if line.startswith("{")
        ):
            raise StepFailed("repository privacy was not verified; publication stopped")
        verification["repository_private"] = True
        files = subprocess.check_output(
            ["git", "ls-files", "--modified", "--others", "--exclude-standard"],
            cwd=root,
            text=True,
        ).splitlines()
        check_credentials(root, files)
        verification["credential_pattern_scan"] = "passed"
        atomic_json(output / "verification.json", verification)
        state(
            "complete",
            **status,
            report="docs/pilot-continuation-results.md",
            repository_private=True,
            second_allocation_executed=False,
        )
        checksums = {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(output.rglob("*"))
            if p.is_file()
            and p.suffix in (".json", ".png", ".svg")
            and p.name not in ("artifact-checksums.json", "completion-state.json")
        }
        atomic_json(
            output / "artifact-checksums.json",
            {
                "plan_id": plan["plan_id"],
                "files": checksums,
                "authoritative_resume_state": "ledger.sqlite3 and any SQLite sidecars are local, ignored by Git",
                "generation_calls": 0,
            },
        )
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=root, text=True
        ).strip()
        if branch != "codex/research-readiness":
            raise StepFailed("unexpected branch; automatic publication stopped")
        targets = [
            ".gitignore",
            "scripts/export_native_run.py",
            "scripts/evidence_diagnostics.py",
            "scripts/report_continuation.py",
            "scripts/plot_continuation.py",
            "scripts/continue_saved_study.py",
            "scripts/finalize_continuation.py",
            "tests/test_evidence_diagnostics.py",
            "tests/test_continuation_report.py",
            "tests/test_timeout_recovery.py",
            "tests/test_completion_watcher.py",
            "studies/pilot-v0.3-timeout-recovery.json",
            "studies/amendments/pre-timeout-controller-check.json",
            "docs/pilot-continuation.md",
            "docs/pilot-continuation-results.md",
            "docs/next-study-proposal.md",
            "README.md",
            "CHANGELOG.md",
            "results/pilot-v0.3-continued",
        ]
        if str(plan_path) not in targets:
            targets.append(str(plan_path))
        for optional in (
            "scripts/continue_reserved_study.py",
            "tests/test_reserved_failure_recovery.py",
            "studies/pilot-v0.3-reserved-recovery-proposal.json",
        ):
            if (root / optional).exists():
                targets.append(optional)
        subprocess.run(
            ["git", "add", "--", *targets], cwd=root, check=True, capture_output=True
        )
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root).returncode:
            run(
                "commit",
                [
                    "git",
                    "commit",
                    "-m",
                    "Record first-$25 continuation results and revised study proposal",
                ],
            )
        run("push", ["git", "push", "origin", branch])
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
        # Keep the publication receipt outside the immutable committed artifacts.
        atomic_json(
            "/private/tmp/clue-continuation-completion.json",
            {
                "status": "complete",
                "commit": commit,
                "report": str(root / "docs/pilot-continuation-results.md"),
                **status,
            },
        )
        state(
            "complete",
            **status,
            commit=commit,
            report="docs/pilot-continuation-results.md",
            repository_private=True,
            second_allocation_executed=False,
        )
        print(json.dumps({"completed": True, "commit": commit, **status}), flush=True)
    except Exception as exc:
        # Do not serialize arbitrary exception strings or credentials.
        state(
            "failed",
            error_type=type(exc).__name__,
            safe_reason=str(exc)
            if isinstance(exc, StepFailed)
            else "Completion verification requires inspection; raw exception omitted",
        )
        print(
            json.dumps({"completed": False, "error_type": type(exc).__name__}),
            flush=True,
        )
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
