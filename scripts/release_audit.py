"""Private release manifest and bounded secret/path scan; never publishes."""

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
import zipfile
from pathlib import Path

PATTERNS = {
    "google_api_key": re.compile(rb"AIza[0-9A-Za-z_-]{35}"),
    "provider_secret": re.compile(rb"sk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "local_home_path": re.compile(rb"/(?:Users|home)/[A-Za-z0-9_.-]+/"),
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def inspect_bytes(name, data):
    return [
        {"file": name, "finding": kind, "count": len(pattern.findall(data))}
        for kind, pattern in PATTERNS.items()
        if pattern.search(data)
    ]


def history_scan():
    # Inspect every reachable blob once. Do not print matching content or secrets.
    entries = subprocess.check_output(
        ["git", "rev-list", "--objects", "--all"], text=True
    ).splitlines()
    findings, count = [], 0
    process = subprocess.Popen(
        ["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    try:
        for entry in entries:
            oid, _, name = entry.partition(" ")
            process.stdin.write((oid + "\n").encode())
            process.stdin.flush()
            header = process.stdout.readline().decode().split()
            size = int(header[2])
            data = process.stdout.read(size)
            process.stdout.read(1)
            if header[1] == "blob":
                count += 1
                findings.extend(
                    {"revision_blob": oid, **r} for r in inspect_bytes(name, data)
                )
    finally:
        process.stdin.close()
        process.stdout.close()
        process.wait()
    return {
        "reachable_blobs_scanned": count,
        "findings": findings,
        "scope": "Pattern scan only; manual privacy, history and ownership review remains required.",
    }


def scan_archives():
    result = {}
    for path in sorted(Path("benchmarks/data").glob("*.tar.gz")):
        findings, skipped, scanned = [], [], 0
        with tarfile.open(path) as archive:
            for member in archive:
                if not member.isfile():
                    if not member.isdir():
                        findings.append(
                            {
                                "file": member.name,
                                "finding": "archive_link_or_special_member",
                            }
                        )
                    continue
                scanned += 1
                tail, detected = b"", set()
                with archive.extractfile(member) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        data = tail + chunk
                        detected.update(
                            kind
                            for kind, pattern in PATTERNS.items()
                            if pattern.search(data)
                        )
                        tail = data[-256:]
                findings.extend(
                    {"file": member.name, "finding": kind} for kind in sorted(detected)
                )
                if any(
                    part in {".community-checkpoints", "authorization.json"}
                    for part in Path(member.name).parts
                ) or member.name.endswith((".sqlite", ".sqlite3")):
                    findings.append(
                        {"file": member.name, "finding": "private_operational_member"}
                    )
        result[str(path)] = {
            "sha256": sha(path),
            "bytes": path.stat().st_size,
            "files_scanned": scanned,
            "findings": findings,
            "unscanned_members": skipped,
            "distribution_clearance": "pending manual review; immutable original preserved",
        }
    return result


def audit(output, history=False):
    artifacts, findings = {}, []
    for path in sorted(Path("dist").glob("*0.5.0rc1*")):
        artifacts[str(path)] = {"sha256": sha(path), "bytes": path.stat().st_size}
        limit = 5_000_000 if path.suffix == ".whl" else 10_000_000
        if path.stat().st_size >= limit:
            raise ValueError("distribution exceeds size target: " + str(path))
        if path.suffix == ".whl":
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    findings.extend(
                        inspect_bytes(str(path) + ":" + name, archive.read(name))
                    )
                    if any(
                        part in {"runs", ".env.local", ".community-checkpoints"}
                        for part in Path(name).parts
                    ) or name.endswith(".sqlite"):
                        findings.append(
                            {
                                "file": str(path) + ":" + name,
                                "finding": "operational_file",
                            }
                        )
        else:
            with tarfile.open(path) as archive:
                for member in archive:
                    if member.isfile():
                        findings.extend(
                            inspect_bytes(
                                str(path) + ":" + member.name,
                                archive.extractfile(member).read(),
                            )
                        )
    manifest = {
        "schema_version": "clue-private-release-manifest-1",
        "software_version": "0.5.0rc1",
        "source_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "source_tree": {
            str(p): sha(p)
            for p in sorted(Path("src/clue_benchmark").rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts
        },
        "artifacts": artifacts,
        "docs": {
            str(p): sha(p) for p in sorted(Path("site").rglob("*")) if p.is_file()
        },
        "sanitized_results_index": json.loads(
            Path("src/clue_benchmark/resources/measured-results/index.json").read_text()
        ),
        "archive_inventory": scan_archives(),
        "artifact_scan_findings": findings,
        "history_scan": history_scan() if history else {"status": "not_requested"},
        "license_state": "ownership clearance pending; no new license grant",
        "public_release_ready": False,
        "external_gates": [
            "manifest-bound follow-up execution approval and native access/identity probes",
            "two independent rules/template readers",
            "outside installed-wheel reproduction",
            "ownership/contributor/provider-output redistribution clearance",
            "manual source/history/archive privacy and license review",
            "organization channel access, hosted dataset/Croissant validation and final publication approval",
        ],
    }
    Path(output).write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "manifest": output,
                "artifacts": artifacts,
                "artifact_findings": len(findings),
                "public_release_ready": False,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="release/release-manifest.json")
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    audit(args.output, args.history)
