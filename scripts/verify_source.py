"""Verify the imported source is unchanged; never writes to it."""

import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = Path("/Users/neevgupta/texas/trustprism/clue-generator")
manifest = json.loads((root / "PROVENANCE.json").read_text())
assert all(
    hashlib.sha256((source / p).read_bytes()).hexdigest() == sha
    for p, sha in manifest["imported_sha256"].items()
)
assert (
    subprocess.check_output(
        ["git", "status", "--porcelain=v1", "-uall"], cwd=source, text=True
    )
    == manifest["source_status"]
)
assert (
    subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    == manifest["source_commit"]
)
assert (
    subprocess.check_output(
        ["git", "remote", "get-url", "origin"], cwd=source, text=True
    ).strip()
    == manifest["source_repository"] + ".git"
)
print("Original imported files, HEAD, remote, and Git status are unchanged.")
