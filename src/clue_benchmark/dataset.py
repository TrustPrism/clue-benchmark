"""Ordered parallel generation, atomic checkpoints, and conservative duplicate screening."""

import json
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from importlib.metadata import version
from pathlib import Path

from .config import DATA_VERSION, Config, digest
from .environment import public_puzzle
from .generation import generate, validate_case


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        json.dump(value, f, sort_keys=True, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def _graph_hash(case, world=False):
    # WL isomorphism-invariant screening; collisions reject extra cases conservatively.
    colors = {}
    neighbors = {}

    def node(key, color):
        colors[key] = digest(color)
        neighbors.setdefault(key, [])

    def edge(a, b):
        neighbors[a].append(b)
        neighbors[b].append(a)

    for s in case["suspects"]:
        node(("s", s), "suspect")
    for a, values in case["domains"].items():
        for v in values:
            node(("v", a, v), ("value", a))
    if world:
        for s, attrs in case["solution"]["world"].items():
            for a, v in attrs.items():
                edge(("s", s), ("v", a, v))
    else:
        for i, c in enumerate(case["clues"]):
            key = ("c", i)
            node(key, ("clue", c["type"]))
            if "suspect" in c:
                edge(key, ("s", c["suspect"]))
            if "value" in c:
                edge(key, ("v", c["attribute"], c["value"]))
            elif "attribute" in c:
                attr = ("a", c["attribute"])
                if attr not in colors:
                    node(attr, ("attribute", c["attribute"]))
                edge(key, attr)
            if "attr1" in c:
                edge(key, ("v", c["attr1"], c["val1"]))
                edge(key, ("v", c["attr2"], c["val2"]))
    for _ in range(8):
        colors = {
            k: digest((colors[k], sorted(colors[n] for n in neighbors[k])))
            for k in colors
        }
    return digest(sorted(colors.values()))


def fingerprints(case):
    return _graph_hash(case, True), _graph_hash(case)


def _job(args):
    return generate(Config(**args[0]), args[1])


def build_bank(config, count, seed, path, workers=1, max_candidates=None):
    if type(count) is not int or count < 1 or type(workers) is not int or workers < 1:
        raise ValueError("positive count/workers required")
    max_candidates = max_candidates if max_candidates is not None else count * 20
    if type(max_candidates) is not int or max_candidates < count:
        raise ValueError("max_candidates must be >= count")
    signature = {
        "config": config.to_dict(),
        "version": DATA_VERSION,
        "solver_version": version("ortools"),
        "count": count,
        "start_seed": seed,
        "max_candidates": max_candidates,
    }
    # Normalize tuples before comparing a loaded JSON document.
    signature = json.loads(json.dumps(signature))
    path = Path(path)
    if path.exists():
        state = json.loads(path.read_text())
        if state.get("signature") != signature:
            raise ValueError("checkpoint configuration/version mismatch")
    else:
        state = {
            "signature": signature,
            "next_seed": seed,
            "cases": [],
            "diagnostics": [],
            "complete": False,
        }
    worlds = set()
    puzzles = set()
    for c in state["cases"]:
        w, p = fingerprints(c)
        if w in worlds or p in puzzles:
            raise ValueError("duplicate in checkpoint")
        worlds.add(w)
        puzzles.add(p)
    executor = (
        ProcessPoolExecutor(max_workers=workers, max_tasks_per_child=12)
        if workers > 1
        else None
    )
    try:
        while (
            len(state["cases"]) < count and state["next_seed"] < seed + max_candidates
        ):
            size = min(
                workers,
                count - len(state["cases"]),
                seed + max_candidates - state["next_seed"],
            )
            jobs = [
                (config.to_dict(), s)
                for s in range(state["next_seed"], state["next_seed"] + size)
            ]
            results = executor.map(_job, jobs) if executor else map(_job, jobs)
            for result in results:
                info = result["diagnostics"]
                info["status"] = result["status"]
                if result["status"] == "ok":
                    c = result["case"]
                    w, p = fingerprints(c)
                    if w in worlds or p in puzzles:
                        info["status"] = "duplicate"
                    else:
                        worlds.add(w)
                        puzzles.add(p)
                        c["world_group"] = w
                        c["structure_group"] = p
                        state["cases"].append(c)
                state["diagnostics"].append(info)
                state["next_seed"] += 1
                state["complete"] = len(state["cases"]) == count
                atomic_json(path, state)
    finally:
        if executor:
            executor.shutdown()
    return state


def read_cases(path):
    path = Path(path)
    if path.suffix == ".jsonl":
        return [
            json.loads(line) for line in path.read_text().splitlines() if line.strip()
        ]
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    if "cases" in data:
        return data["cases"]
    if "case" in data:
        return [data["case"]] if data["case"] else []
    raise ValueError("expected case list, result, checkpoint, or JSONL")


def write_jsonl(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(x, sort_keys=True) + "\n" for x in records)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def study_export(cases):
    from .clue_formatter import ClueFormatter
    from .clue_metadata import decorate_clue

    return {
        "version": "benchmark-0.1",
        "uniqueness_definition": "unique_murderer",
        "states": [
            {
                "case_id": c["case_id"],
                "seed": c["seed"],
                "murderer": c["solution"]["murderer"],
                "world": c["solution"]["world"],
                "clues": {
                    "benchmark": {
                        "count": len(c["clues"]),
                        "raw_items": c["clues"],
                        "items": [ClueFormatter.format(x) for x in c["clues"]],
                        "records": [
                            decorate_clue(
                                x,
                                c["case_id"],
                                "benchmark",
                                ClueFormatter.format(x),
                                necessary_for_uniqueness=None,
                            )
                            for x in c["clues"]
                        ],
                    }
                },
            }
            for c in cases
        ],
    }


def create_suite(root, workers=1, dev=30, test=100):
    root = Path(root)
    all_cases = []
    summaries = []
    seen_worlds = set()
    seen_puzzles = set()
    for n, k in ((4, 8), (8, 12), (12, 16)):
        config = Config(suspect_count=n, clue_count=k)
        state = build_bank(
            config,
            dev + test,
            100000 + n * 10000,
            root / "checkpoints" / f"n{n}.json",
            workers,
        )
        if not state["complete"]:
            raise RuntimeError(f"underfilled n={n}; inspect checkpoint diagnostics")
        for i, c in enumerate(state["cases"]):
            if c["world_group"] in seen_worlds or c["structure_group"] in seen_puzzles:
                raise ValueError("cross-cell duplicate")
            seen_worlds.add(c["world_group"])
            seen_puzzles.add(c["structure_group"])
            validate_case(c)
            all_cases.append({**c, "split": "dev" if i < dev else "test"})
        summaries.append(
            {
                "suspects": n,
                "clues": k,
                "config": config.to_dict(),
                "attempted_seeds": len(state["diagnostics"]),
                "statuses": dict(Counter(x["status"] for x in state["diagnostics"])),
            }
        )
    for split in ("dev", "test"):
        cases = [c for c in all_cases if c["split"] == split]
        write_jsonl(root / "private" / f"{split}.jsonl", cases)
        write_jsonl(
            root / "public" / f"{split}.jsonl", [public_puzzle(c) for c in cases]
        )
    manifest = {
        "version": DATA_VERSION,
        "status": "private-preview",
        "license": "pending",
        "dev_per_size": dev,
        "test_per_size": test,
        "cells": summaries,
        "cases": len(all_cases),
        "solver_version": version("ortools"),
        "files": {
            str(p.relative_to(root)): __import__("hashlib")
            .sha256(p.read_bytes())
            .hexdigest()
            for p in sorted(root.glob("*/*.jsonl"))
        },
    }
    atomic_json(root / "manifest.json", manifest)
    return manifest
