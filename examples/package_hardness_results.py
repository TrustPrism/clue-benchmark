"""Package certified inputs and saved receipts, without credentials or approvals."""

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

from clue_benchmark.community_bundle import verify_manifest
from clue_benchmark.config import digest
from clue_benchmark.dataset import atomic_json


def package(datasets, plans, runs, output, index, continuations=()):
    summary = json.loads((plans / "plans.json").read_text())
    suite = json.loads((datasets / "suite.json").read_text())
    for obj, key in ((summary, "plans_id"), (suite, "suite_id")):
        if obj[key] != digest({k: v for k, v in obj.items() if k != key}):
            raise ValueError("Frozen identity mismatch")
    if summary["suite_id"] != suite["suite_id"]:
        raise ValueError("Plans refer to a different dataset suite")
    files = {"datasets/suite.json": datasets / "suite.json"}
    for arm, metadata in sorted(suite["bundles"].items()):
        verify_manifest(datasets / arm)
        manifest = datasets / arm / "manifest.json"
        if (
            hashlib.sha256(manifest.read_bytes()).hexdigest()
            != metadata["manifest_hash"]
        ):
            raise ValueError("Bundle differs from the frozen suite")
        for name in (
            "cases.jsonl",
            "partitions.jsonl",
            "answers.jsonl",
            "certificates.jsonl",
            "manifest.json",
        ):
            files[f"datasets/{arm}/{name}"] = datasets / arm / name
    for source in sorted((datasets / "source-snapshot").glob("*.py")):
        files[f"datasets/source-snapshot/{source.name}"] = source
    files["plans/plans.json"] = plans / "plans.json"
    missing, stopped = [], []
    for job in summary["jobs"]:
        frozen_path = plans / (job["name"] + ".json")
        frozen = json.loads(frozen_path.read_text())
        if frozen["plan_id"] != job["plan_id"] or frozen["plan_id"] != digest(
            {k: v for k, v in frozen.items() if k != "plan_id"}
        ):
            raise ValueError("Evaluation plan identity differs")
        result_path = runs / job["name"] / "results.json"
        files[f"plans/{job['name']}.json"] = frozen_path
        if not result_path.exists():
            missing.append(job["name"])
            continue
        result = json.loads(result_path.read_text())
        if result["plan_id"] != job["plan_id"]:
            raise ValueError("Results belong to a different plan")
        if not result["complete"]:
            stopped.append(job["name"])
        if len(result["episodes"]) != job["request_count"]:
            raise ValueError("Assigned result coverage differs")
        files[f"results/{job['name']}/results.json"] = result_path
    continuation_ids = []
    for number, root in enumerate(continuations):
        follow_path = root / "continuation-plan.json"
        follow = json.loads(follow_path.read_text())
        if (
            follow["continuation_id"]
            != digest({k: v for k, v in follow.items() if k != "continuation_id"})
            or follow["continuation_of"] != summary["plans_id"]
        ):
            raise ValueError("Continuation differs from its original study")
        continuation_ids.append(follow["continuation_id"])
        prefix = f"continuation-{number}"
        files[f"{prefix}/continuation-plan.json"] = follow_path
        for job in follow["jobs"]:
            manifest = root / "datasets" / job["arm"] / "manifest.json"
            verify_manifest(manifest.parent)
            if (
                hashlib.sha256(manifest.read_bytes()).hexdigest()
                != job["bundle_manifest_hash"]
            ):
                raise ValueError("Continuation bundle changed")
            for name in (
                "cases.jsonl",
                "partitions.jsonl",
                "answers.jsonl",
                "certificates.jsonl",
                "manifest.json",
            ):
                files[f"{prefix}/datasets/{job['arm']}/{name}"] = manifest.parent / name
            frozen_path = root / "plans" / (job["name"] + ".json")
            frozen = json.loads(frozen_path.read_text())
            if frozen["plan_id"] != job["plan_id"] or frozen["plan_id"] != digest(
                {k: v for k, v in frozen.items() if k != "plan_id"}
            ):
                raise ValueError("Continuation plan changed")
            files[f"{prefix}/plans/{job['name']}.json"] = frozen_path
            result_path = root / "evaluation" / job["name"] / "results.json"
            if not result_path.exists():
                missing.append(f"{prefix}/{job['name']}")
                continue
            result = json.loads(result_path.read_text())
            if (
                result["plan_id"] != job["plan_id"]
                or len(result["episodes"]) != job["request_count"]
            ):
                raise ValueError("Continuation result coverage differs")
            if not result["complete"]:
                stopped.append(f"{prefix}/{job['name']}")
            files[f"{prefix}/evaluation/{job['name']}/results.json"] = result_path
    output.parent.mkdir(parents=True, exist_ok=True)
    inventory = {}
    with output.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as gz:
            with tarfile.open(
                fileobj=gz, mode="w|", format=tarfile.USTAR_FORMAT
            ) as tar:
                for name, path in sorted(files.items()):
                    data = path.read_bytes()
                    entry = tarfile.TarInfo(name)
                    entry.size = len(data)
                    entry.mode = 0o644
                    entry.mtime = 0
                    tar.addfile(entry, io.BytesIO(data))
                    inventory[name] = {
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "bytes": len(data),
                    }
    report = {
        "schema_version": "clue-hardness-reproduction-1",
        "suite_id": suite["suite_id"],
        "plans_id": summary["plans_id"],
        "archive": output.name,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "compressed_bytes": output.stat().st_size,
        "uncompressed_file_bytes": sum(v["bytes"] for v in inventory.values()),
        "files": inventory,
        "contains_evaluator_data": True,
        "excluded": ["credentials", "authorizations", "request ledgers", "checkpoints"],
        "measured_arms": [j["arm"] for j in summary["jobs"]],
        "continuation_ids": continuation_ids,
        "missing_original_or_continuation_result_files": missing,
        "stopped_original_or_continuation_jobs": stopped,
        "completion_scope": "Raw historical files; use the collector to determine combined assignment coverage.",
        "scope": "Full 19-arm certified bank; only the six planned arms have model receipts.",
    }
    atomic_json(index, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("datasets", "plans", "runs", "output", "index"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--continuation", type=Path, action="append", default=[])
    args = parser.parse_args()
    report = package(
        args.datasets, args.plans, args.runs, args.output, args.index, args.continuation
    )
    print(json.dumps({k: v for k, v in report.items() if k != "files"}, indent=2))
