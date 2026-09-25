"""Release integrity checks: proofs, split grouping, public allowlists, hashes."""

import hashlib
import json
from pathlib import Path

from clue_benchmark import public_puzzle, validate_case
from clue_benchmark.dataset import fingerprints, read_cases

root = Path(__file__).resolve().parents[1]
data = root / "data/v0.1"
manifest = json.loads((data / "manifest.json").read_text())
for path, expected in manifest["files"].items():
    assert hashlib.sha256((data / path).read_bytes()).hexdigest() == expected, path
worlds = set()
puzzles = set()
total = 0
for split, expected in [("dev", 90), ("test", 300)]:
    cases = read_cases(data / "private" / f"{split}.jsonl")
    assert len(cases) == expected
    public = read_cases(data / "public" / f"{split}.jsonl")
    assert public == [public_puzzle(c) for c in cases]
    for c in cases:
        validate_case(c)
        w, p = fingerprints(c)
        assert w == c["world_group"] and p == c["structure_group"]
        assert w not in worlds and p not in puzzles
        worlds.add(w)
        puzzles.add(p)
        total += 1
results = json.loads((root / "results/baselines.json").read_text())
assert results["manifest"]["episode_count"] == 9000
assert sum(row["episodes"] for row in results["summary"]) == 9000
assert not any(row["solver_errors"] for row in results["summary"])
assert all(
    row["accuracy"] == 1
    for row in results["summary"]
    if row["baseline"] == "reference"
    or row["baseline"] in ("round_robin", "random_investigation")
    and row["budget_fraction"] == 1
)
assert results["manifest"]["paid_calls"] == 0
assert (
    max(
        row["query_p95_ms"]
        for row in results["summary"]
        if row["query_p95_ms"] is not None
    )
    < 10
)
print(
    f"{total} cases verified; hashes, disjoint splits, public exports, 9000 summarized baseline episodes, and latency target passed."
)
