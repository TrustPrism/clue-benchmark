"""Create an indexed local reproduction copy without approvals or ledgers."""

import argparse
import io
import json
import tarfile
from pathlib import Path

from clue_benchmark.community_bundle import file_hash
from clue_benchmark.config import canonical
from clue_benchmark.dataset import atomic_json

EPISODE_FIELDS = {
    "request_id",
    "world_id",
    "case_id",
    "model",
    "condition",
    "agent",
    "repeat",
    "messages",
    "forwarded_reports",
    "input_token_upper_bound",
    "maximum_microdollars",
    "context_fits",
    "transport",
    "returned_model",
    "wall_seconds",
    "calls",
    "dispatched",
    "input_tokens",
    "output_tokens",
    "thinking_tokens",
    "usage_known",
    "correct",
    "supported",
    "protocol_valid",
    "abstained",
    "ambiguous_evidence",
    "possible_culprits",
    "sufficient_evidence",
    "answer",
    "actual_microdollars",
    "evaluator_status",
}


def safe_report(value):
    result = {
        k: value[k]
        for k in (
            "plan_id",
            "complete",
            "stopped_reason",
            "accounting",
            "all_assigned_failures_retained",
        )
        if k in value
    }
    result["episodes"] = []
    for episode in value["episodes"]:
        row = {k: v for k, v in episode.items() if k in EPISODE_FIELDS}
        receipt = episode.get("receipt", {})
        row["receipt"] = {
            k: receipt[k]
            for k in (
                "vendor",
                "finish_reason",
                "provider_status_code",
                "usage_present",
                "thinking_separately_observed",
            )
            if k in receipt
        }
        row["receipt"]["counters"] = {
            k: v
            for k, v in receipt.get("counters", {}).items()
            if v is None or type(v) is int
        }
        result["episodes"].append(row)
    return result


def package(root, analysis, output):
    root, analysis, output = Path(root), Path(analysis), Path(output)
    if output.exists():
        raise ValueError("archive exists; never replace a measured release")
    study = json.loads((root / "study.json").read_text())
    summary = json.loads((root / "execution-summary.json").read_text())
    if summary["status"] != "completed":
        raise ValueError(
            "only a completed run can be packaged as a completed reproduction"
        )
    # Each original remains private; generated distribution copies are explicit.
    index = {
        "study_id": study["study_id"],
        "manifest_id": study["manifest_id"],
        "included_original_hashes": {},
        "sanitized_reports": {},
        "excluded": [
            "authorization.json",
            "authorization-evidence.json",
            "execute_authorized.py",
            "all SQLite dispatch ledgers and lock files",
            "nonselected candidate worlds",
            "raw provider usage dictionaries/native call objects",
        ],
        "rights_clearance": "pending; local private reproduction copy only",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:

        def add(path, name=None):
            path = Path(path)
            name = str(path) if name is None else name
            index["included_original_hashes"][name] = file_hash(path)
            archive.add(path, arcname=name, recursive=False)

        def add_json(name, value):
            data = (canonical(value) + "\n").encode()
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = 0o644
            archive.addfile(member, io.BytesIO(data))

        add(root / "study.json")
        for path in sorted(Path("src/clue_benchmark").glob("*.py")):
            if file_hash(path) != study["sources"][path.name]:
                raise ValueError("source drift while packaging")
            add(path)
        add(Path("examples/analyse_nuisance_followup.py"))
        # Needed only for future local installation; no credential is included.
        for name in ("pyproject.toml", "LICENSING.md", "README.md"):
            add(Path(name))
        jobs = [("probe", study["probe_job"])] + [
            (j["directory"], j) for b in study["selected_blocks"] for j in b["jobs"]
        ]
        seen = set()
        for execution_name, job in jobs:
            directory = root / job["directory"]
            if directory not in seen:
                seen.add(directory)
                for name in (
                    "manifest.json",
                    "cases.jsonl",
                    "partitions.jsonl",
                    "answers.jsonl",
                    "certificates.jsonl",
                    "plan.json",
                    "payloads.jsonl",
                ):
                    add(directory / name)
                if (directory / "probe-plan.json").exists():
                    add(directory / "probe-plan.json")
            original = root / "execution" / execution_name / "results.json"
            sanitized = safe_report(json.loads(original.read_text()))
            add_json(str(original), sanitized)
            index["sanitized_reports"][str(original)] = {
                "original_sha256": file_hash(original),
                "policy": "Positive episode/receipt field allowlist; counters restricted to integers/null. Approvals, ledgers, native call objects and raw usage omitted.",
            }
        add_json(
            str(root / "execution-summary.json"),
            {
                "status": summary["status"],
                "manifest_id": summary["manifest_id"],
                "combined_ceiling_microdollars": summary[
                    "combined_ceiling_microdollars"
                ],
                "reports": [safe_report(r) for r in summary["reports"]],
            },
        )
        for path in sorted(analysis.rglob("*")):
            if path.is_file():
                add(path)
        add_json("SANITIZATION.json", index)
    index["archive"] = {
        "path": str(output),
        "sha256": file_hash(output),
        "bytes": output.stat().st_size,
    }
    index["offline_replay"] = (
        "PYTHONPATH=src python examples/analyse_nuisance_followup.py runs/nuisance-followup-20261027-rc1 --output runs/offline-replayed --figures"
    )
    atomic_json(output.with_suffix(".index.json"), index)
    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = package(args.directory, args.analysis, args.output)
    print(json.dumps(result["archive"]))
