"""Rebuild the v0.3 suite and measure generation throughput, memory, and clue latency."""

import argparse
import json
import math
import os
import platform
import resource
import statistics
import time
from collections import Counter
from pathlib import Path

from clue_benchmark.dataset import atomic_json, create_suite_v03, read_cases
from clue_benchmark.environment import Environment


def percentile(values, fraction):
    values = sorted(values)
    return values[math.ceil(fraction * len(values)) - 1] if values else None


def rss_bytes(kind):
    amount = resource.getrusage(kind).ru_maxrss
    return amount if platform.system() == "Darwin" else amount * 1024


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    root = Path(args.output_root)
    start = time.perf_counter()
    manifest = create_suite_v03(root, workers=args.workers)
    wall_seconds = time.perf_counter() - start
    accepted_seconds = []
    rejections = Counter()
    for path in root.glob("checkpoints/*.json"):
        state = json.loads(path.read_text())
        for job in state["diagnostics"]:
            for detail in job.get("details") or []:
                rejections.update(detail["rejections"])
                if job["status"] == "ok":
                    accepted_seconds.append(detail["seconds"])
    cases = read_cases(root / "private/test.jsonl")[:100]
    latency_ms = []
    for case in cases:
        env = Environment(case)
        for query in env.observation()["queries"]:
            for _ in range(query["remaining"]):
                begin = time.perf_counter()
                env.request_clue(query["query_id"])
                latency_ms.append((time.perf_counter() - begin) * 1000)
    report = {
        "version": manifest["version"],
        "hardware": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "cpu": platform.processor(),
            "cpu_count": os.cpu_count(),
            "workers": args.workers,
        },
        "generation": {
            "worlds": manifest["worlds"],
            "cases": manifest["cases"],
            "attempted_world_seeds": sum(
                c["attempted_seeds"] for c in manifest["cells"]
            ),
            "statuses": dict(
                sum((Counter(c["statuses"]) for c in manifest["cells"]), Counter())
            ),
            "internal_rejections": dict(rejections),
            "wall_seconds": wall_seconds,
            "accepted_cases_per_minute": 60 * manifest["cases"] / wall_seconds,
            "accepted_case_median_seconds": statistics.median(accepted_seconds),
            "accepted_case_p95_seconds": percentile(accepted_seconds, 0.95),
            "parent_peak_rss_bytes": rss_bytes(resource.RUSAGE_SELF),
            "child_peak_rss_bytes": rss_bytes(resource.RUSAGE_CHILDREN),
        },
        "evaluation": {
            "sample_cases": len(cases),
            "request_count": len(latency_ms),
            "clue_response_p95_ms": percentile(latency_ms, 0.95),
            "excludes_model_latency": True,
        },
        "caveat": "Two-worker full-suite run includes checkpoint I/O and validation. Per-case times are accepted generator calls. Memory peaks are OS process maxima. V0.2 used a different case distribution.",
    }
    atomic_json(args.report, report)
    print(json.dumps({"wall_seconds": wall_seconds, "cases": manifest["cases"]}))


if __name__ == "__main__":
    main()
