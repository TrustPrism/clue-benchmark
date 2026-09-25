"""Measure both engines with matched N/K and no minimum-subset requirement."""

import argparse
import json
import math
import platform
import resource
import statistics
import subprocess
import sys
from pathlib import Path

from clue_benchmark import Config, generate
from clue_benchmark.dataset import atomic_json

p = argparse.ArgumentParser()
p.add_argument("--seeds", type=int, default=5)
p.add_argument("--output", default="results/performance.json")
args = p.parse_args()
root = Path(__file__).resolve().parents[1]
rows = []
code = """
import json,random,time
from world_sampler import WorldSampler
from clue_generator import ClueGenerator
from csp_solver import MysteryCSPSolver
from solvability_policy import generate_probabilistic_clue_set
n,k,seed=map(int,__import__('sys').argv[1:]);rng=random.Random(seed)
d={a:[str(x) for x in range(4)] for a in ['weapon','location','motive','time']}
s=[f'S{x+1:02d}' for x in range(n)];start=time.perf_counter()
w,m=WorldSampler(d).sample_world(s,True,rng=rng);b=ClueGenerator(w,m,d);b.build_clue_pool(rng=rng)
r=generate_probabilistic_clue_set(b.clue_pool,MysteryCSPSolver(s,d,w,m),.7,.75,k,rng,max_attempts=64,candidate_sample_size=96)
print(json.dumps({'status':'ok' if r else 'failed','seconds':time.perf_counter()-start}))
"""
for n, k in [(4, 8), (8, 12), (12, 16)]:
    for seed in range(args.seeds):
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code, str(n), str(k), str(seed)],
                cwd=root / "legacy",
                capture_output=True,
                text=True,
                timeout=30,
            )
            legacy = (
                json.loads(proc.stdout)
                if proc.returncode == 0
                else {"status": "error", "seconds": None, "error": proc.stderr[-200:]}
            )
        except subprocess.TimeoutExpired:
            legacy = {"status": "timeout", "seconds": 30}
        cfg = Config(
            suspect_count=n,
            clue_count=k,
            domains={
                a: [str(x) for x in range(4)]
                for a in ["weapon", "location", "motive", "time"]
            },
        )
        result = generate(cfg, seed)
        rows.extend(
            [
                dict(engine="legacy", n=n, k=k, seed=seed, **legacy),
                dict(
                    engine="benchmark",
                    n=n,
                    k=k,
                    seed=seed,
                    status=result["status"],
                    seconds=result["diagnostics"]["seconds"],
                ),
            ]
        )
        print(n, seed, legacy["status"], result["status"], flush=True)
summary = []
for engine in ["legacy", "benchmark"]:
    for n in [4, 8, 12]:
        group = [x for x in rows if x["engine"] == engine and x["n"] == n]
        times = sorted(x["seconds"] for x in group if x["status"] == "ok")
        summary.append(
            dict(
                engine=engine,
                n=n,
                accepted=len(times),
                attempted=len(group),
                median=statistics.median(times) if times else None,
                p95=times[math.ceil(0.95 * len(times)) - 1] if times else None,
            )
        )
atomic_json(
    args.output,
    dict(
        hardware=dict(
            platform=platform.platform(),
            machine=platform.machine(),
            python=platform.python_version(),
            cpu=platform.processor(),
            cpu_count=__import__("os").cpu_count(),
        ),
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        summary=summary,
        runs=rows,
        caveat="Small paired generation microbenchmark; algorithms differ in sampling distribution. Legacy timeout includes subprocess startup. RSS is current process only (macOS bytes).",
    ),
)
