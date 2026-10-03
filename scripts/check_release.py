"""Private release integrity: solver proofs, paired splits, public allowlists, hashes."""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from clue_benchmark import public_puzzle, validate_case
from clue_benchmark.config import DATA_VERSION, VERSION
from clue_benchmark.dataset import fingerprints, read_cases, reproduce_case
from clue_benchmark.environment import PROTOCOL_VERSION
from clue_benchmark.readiness import metadata_checks

root = Path(__file__).resolve().parents[1]
data = root / "data/v0.3"
manifest = json.loads((data / "manifest.json").read_text())
assert manifest["version"] == DATA_VERSION
assert manifest["status"] == "private-preview" and manifest["license"] == "pending"
assert manifest["worlds"] == 480 and manifest["cases"] == 960
for path, expected in manifest["files"].items():
    assert hashlib.sha256((data / path).read_bytes()).hexdigest() == expected, path

worlds = defaultdict(list)
puzzles = set()
for split, expected in (("dev", 216), ("test", 744)):
    cases = read_cases(data / "private" / f"{split}.jsonl")
    assert len(cases) == expected
    public = read_cases(data / "public" / f"{split}.jsonl")
    assert public == [public_puzzle(c) for c in cases]
    for case in cases:
        validate_case(case)
        reproduce_case(case)
        world, puzzle = fingerprints(case)
        assert (world, puzzle) == (case["world_group"], case["structure_group"])
        assert puzzle not in puzzles
        puzzles.add(puzzle)
        worlds[world].append((split, case))
assert len(worlds) == 480
for pair in worlds.values():
    assert len(pair) == 2
    assert pair[0][0] == pair[1][0]
    assert pair[0][1]["cell"] == pair[1][1]["cell"]
    assert pair[0][1]["solution"] == pair[1][1]["solution"]
    n = len(pair[0][1]["suspects"])
    assert sorted(len(case["clues"]) for _, case in pair) == [n + 4, n + 8]

results = json.loads((root / "results/baselines-v0.3-test.json").read_text())
# The frozen v0.3 baseline was measured with software 0.3.0. New software must
# preserve the data and protocol; historical result manifests stay immutable.
assert results["manifest"]["version"] in ("0.3.0", VERSION)
assert results["manifest"]["protocol_version"] == PROTOCOL_VERSION
assert results["manifest"]["episode_count"] == 744 * 14
assert sum(row["episodes"] for row in results["summary"]) == 744 * 14
assert not any(row["solver_errors"] for row in results["summary"])
assert all(
    row["accuracy"] == 1
    for row in results["summary"]
    if row["baseline"] == "reference"
    or row["baseline"] in ("round_robin", "random_investigation", "topic_heuristic")
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
structure = json.loads((root / "results/structure-v0.3.json").read_text())
assert len(structure["rows"]) == 960
assert all(row["complete"] for row in structure["rows"])
performance = json.loads((root / "results/performance-v0.3.json").read_text())
assert performance["version"] == DATA_VERSION
assert performance["generation"]["cases"] == 960
assert performance["evaluation"]["clue_response_p95_ms"] < 10
metadata = json.loads((data / "croissant.json").read_text())
metadata_status = metadata_checks(data)
assert metadata_status["required_fields_present"]
assert metadata_status["distribution_hashes_match"]
assert all(
    entry["sha256"] == manifest["files"][entry["contentUrl"]]
    for entry in metadata["distribution"]
)
plan_path = root / "studies/readiness-v0.3.json"
if plan_path.exists():
    from clue_benchmark.study import verify_study

    plan = json.loads(plan_path.read_text())
    verify_study(plan, root)
    assert plan["paid_calls"] == 0 and plan["status"] == "awaiting-model-selection"
    assert not plan["models"]
print(
    "960 cases verified; paired splits, hashes, public exports, symbolic baselines, and latency target passed."
)
