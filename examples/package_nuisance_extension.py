"""Assemble an offline reproduction archive; never include approvals/ledgers."""

import argparse
import importlib.util
import io
import json
import sqlite3
import tarfile
from pathlib import Path

from clue_benchmark.community_bundle import file_hash
from clue_benchmark.config import canonical
from clue_benchmark.dataset import atomic_json


def package(initial, extension, output):
    initial, extension, output = Path(initial), Path(extension), Path(output)
    if output.exists():
        raise ValueError("never replace an existing measured archive")
    summary = json.loads((extension / "execution-summary.json").read_text())
    plan = json.loads((extension / "extension-plan.json").read_text())
    study = json.loads((initial / "study.json").read_text())
    if summary["status"] != "completed" or summary["held_microdollars"]:
        raise ValueError("extension is not completely settled")
    total, request_ids = 0, set()
    for path in [
        *initial.glob("execution/**/requests.sqlite"),
        *extension.glob("execution/**/requests.sqlite"),
    ]:
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            for ident, status, actual, maximum in db.execute(
                "SELECT id,status,actual,maximum FROM requests"
            ):
                if (
                    status != "settled"
                    or type(actual) is not int
                    or not 0 <= actual <= maximum
                    or ident in request_ids
                ):
                    raise ValueError("unsettled or duplicate dispatch in accounting")
                total += actual
                request_ids.add(ident)
        finally:
            db.close()
    if (
        len(request_ids) != 146
        or total != summary["combined_settled_microdollars"]
        or total > 10_000_000
    ):
        raise ValueError("combined ledger total or request count differs")
    spec = importlib.util.spec_from_file_location(
        "safe_reports", Path(__file__).with_name("package_nuisance_followup.py")
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    index = {
        "study_id": "nuisance-followup-20261027-extended",
        "initial_manifest_id": study["manifest_id"],
        "extension_id": plan["extension_id"],
        "combined_settled_microdollars": total,
        "held_microdollars": 0,
        "combined_cap_microdollars": 10_000_000,
        "paid_dispatches": 146,
        "scored_assignments": 144,
        "rights_clearance": "pending; private artifact only",
        "included_sha256": {},
        "sanitized_report_original_sha256": {},
        "excluded": [
            "all authorization files/evidence",
            "all SQLite ledgers/locks",
            "credential files",
            "launchers reading credentials",
            "raw usage dictionaries/provider prose",
        ],
        "offline_replay": "PYTHONPATH=src python -m clue_benchmark examples replay nuisance-followup --output runs/replayed --figures",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:

        def add(path):
            path = Path(path)
            archive.add(path, arcname=str(path), recursive=False)
            index["included_sha256"][str(path)] = file_hash(path)

        def saved_json(path, value):
            data = (canonical(value) + "\n").encode()
            member = tarfile.TarInfo(str(path))
            member.size = len(data)
            member.mode = 0o644
            archive.addfile(member, io.BytesIO(data))

        for folder in [
            Path("src/clue_benchmark"),
            extension / "frozen-source/clue_benchmark",
        ]:
            for path in sorted(folder.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    add(path)
        for name in [
            "pyproject.toml",
            "LICENSING.md",
            "README.md",
            "examples/nuisance_extension.py",
            "examples/package_nuisance_extension.py",
            "examples/package_nuisance_followup.py",
            "benchmarks/nuisance-extended-measurements.json",
            "benchmarks/nuisance-extended-results.json",
        ]:
            add(name)
        add(initial / "study.json")
        add(extension / "extension-plan.json")
        for block in study["candidate_blocks"]:
            for job in block["jobs"]:
                directory = initial / job["directory"]
                for name in [
                    "manifest.json",
                    "cases.jsonl",
                    "partitions.jsonl",
                    "answers.jsonl",
                    "certificates.jsonl",
                    "plan.json",
                    "payloads.jsonl",
                ]:
                    add(directory / name)
                if (directory / "probe-plan.json").exists():
                    add(directory / "probe-plan.json")
        for phase in [initial, extension]:
            for saved in sorted((phase / "execution").glob("*/results.json")):
                value = json.loads(saved.read_text())
                saved_json(saved, helper.safe_report(value))
                index["sanitized_report_original_sha256"][str(saved)] = file_hash(saved)
    index["archive"] = {
        "path": str(output),
        "sha256": file_hash(output),
        "bytes": output.stat().st_size,
    }
    atomic_json(output.with_suffix(".index.json"), index)
    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("initial")
    parser.add_argument("extension")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = package(args.initial, args.extension, args.output)
    print(json.dumps(result["archive"]))
