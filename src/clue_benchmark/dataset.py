"""Ordered parallel generation, atomic checkpoints, and conservative duplicate screening."""

import json
import os
import random
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from importlib.metadata import version
from pathlib import Path

from .config import DATA_VERSION, DEFAULT_DOMAINS, TYPES, Config, digest
from .environment import public_puzzle
from .generation import generate, validate_case
from .world_sampler import WorldSampler


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        json.dump(value, f, sort_keys=True, separators=(",", ":"))
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def _graph_data(case, world=False):
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
            if "other_suspect" in c:
                edge(key, ("s", c["other_suspect"]))
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
    return colors, neighbors


def _refined_colors(colors, neighbors):
    colors = dict(colors)
    for _ in range(8):
        colors = {
            k: digest((colors[k], sorted(colors[n] for n in neighbors[k])))
            for k in colors
        }
    return colors


def _graph_hash(case, world=False):
    # WL isomorphism-invariant screening; collisions reject extra cases conservatively.
    initial, neighbors = _graph_data(case, world)
    colors = _refined_colors(initial, neighbors)
    return digest(sorted(colors.values()))


def exact_isomorphic(left, right, world=False, max_states=100000):
    """Confirm a close structural match; return None if the search is bounded out."""
    lc, le = _graph_data(left, world)
    rc, re = _graph_data(right, world)
    if len(lc) != len(rc):
        return False
    lc = _refined_colors(lc, le)
    rc = _refined_colors(rc, re)
    if Counter(lc.values()) != Counter(rc.values()):
        return False
    right_by_color = {}
    for node, color in rc.items():
        right_by_color.setdefault(color, []).append(node)
    order = sorted(lc, key=lambda node: (len(right_by_color[lc[node]]), -len(le[node])))
    mapped = {}
    used = set()
    states = 0

    def search(i):
        nonlocal states
        if i == len(order):
            return True
        if states >= max_states:
            return None
        node = order[i]
        for other in right_by_color[lc[node]]:
            if other in used or len(le[node]) != len(re[other]):
                continue
            if any(
                (neighbor in le[node]) != (mapped[neighbor] in re[other])
                for neighbor in mapped
            ):
                continue
            mapped[node] = other
            used.add(other)
            states += 1
            answer = search(i + 1)
            if answer is True or answer is None:
                return answer
            used.remove(other)
            del mapped[node]
        return False

    return search(0)


def fingerprints(case):
    return _graph_hash(case, True), _graph_hash(case)


def _job(args):
    return generate(Config(**args[0]), args[1])


def _paired_job(args):
    low, high, seed = args
    low, high = Config(**low), Config(**high)
    suspects = [f"S{i + 1:02d}" for i in range(low.suspect_count)]
    try:
        fixed = WorldSampler(low.domains).sample_world(
            suspects,
            True,
            max_attempts=1000,
            rng=random.Random(seed),
            active_values_per_attribute=low.active_values_per_attribute,
        )
    except RuntimeError:
        return {"status": "world_sampling_exhausted", "cases": None, "seed": seed}
    results = [
        generate(cfg, seed * 2 + i, fixed_world=fixed)
        for i, cfg in enumerate((low, high))
    ]
    for result in results:
        if result["status"] == "ok":
            result["case"]["world_seed"] = seed
    return {
        "status": "ok"
        if all(r["status"] == "ok" for r in results)
        else "generation_failed",
        "cases": [r["case"] for r in results]
        if all(r["status"] == "ok" for r in results)
        else None,
        "seed": seed,
        "details": [r["diagnostics"] for r in results],
    }


def build_paired_bank(
    low,
    high,
    count,
    seed,
    path,
    workers=1,
    max_candidates=None,
    excluded_worlds=(),
    excluded_puzzles=(),
):
    """Generate two clue densities for each fixed world in seed order."""
    if type(count) is not int or count < 1 or type(workers) is not int or workers < 1:
        raise ValueError("positive count/workers required")
    if (
        low.suspect_count != high.suspect_count
        or low.domains != high.domains
        or low.active_values_per_attribute != high.active_values_per_attribute
        or low.clue_count >= high.clue_count
    ):
        raise ValueError(
            "paired configurations must share world controls and increase clue count"
        )
    max_candidates = max_candidates or count * 40
    signature = json.loads(
        json.dumps(
            {
                "low": low.to_dict(),
                "high": high.to_dict(),
                "version": DATA_VERSION,
                "solver_version": version("ortools"),
                "count": count,
                "start_seed": seed,
                "max_candidates": max_candidates,
            }
        )
    )
    path = Path(path)
    if path.exists():
        state = json.loads(path.read_text())
        if state.get("signature") != signature:
            raise ValueError("checkpoint configuration/version mismatch")
    else:
        state = {
            "signature": signature,
            "next_seed": seed,
            "pairs": [],
            "diagnostics": [],
            "complete": False,
        }
    worlds = set(excluded_worlds)
    puzzles = set(excluded_puzzles)
    world_cases = {}
    puzzle_cases = {}
    for pair in state["pairs"]:
        for case in pair:
            w, p = fingerprints(case)
            if w in set(excluded_worlds) or p in set(excluded_puzzles):
                raise ValueError("checkpoint conflicts with earlier cells")
            worlds.add(w)
            if p in puzzles:
                raise ValueError("duplicate puzzle in checkpoint")
            puzzles.add(p)
            world_cases[w] = case
            puzzle_cases[p] = case
    executor = (
        ProcessPoolExecutor(max_workers=workers, max_tasks_per_child=12)
        if workers > 1
        else None
    )
    try:
        while (
            len(state["pairs"]) < count and state["next_seed"] < seed + max_candidates
        ):
            size = min(
                workers,
                count - len(state["pairs"]),
                seed + max_candidates - state["next_seed"],
            )
            jobs = [
                (low.to_dict(), high.to_dict(), s)
                for s in range(state["next_seed"], state["next_seed"] + size)
            ]
            results = (
                executor.map(_paired_job, jobs) if executor else map(_paired_job, jobs)
            )
            for result in results:
                info = {
                    "seed": result["seed"],
                    "status": result["status"],
                    "details": result.get("details"),
                }
                if result["status"] == "ok":
                    pair = result["cases"]
                    hashes = [fingerprints(c) for c in pair]
                    if hashes[0][0] != hashes[1][0]:
                        raise AssertionError("paired worlds diverged")
                    if hashes[0][0] in worlds or any(p in puzzles for _, p in hashes):
                        matches = []
                        if hashes[0][0] in world_cases:
                            matches.append(
                                exact_isomorphic(
                                    pair[0], world_cases[hashes[0][0]], world=True
                                )
                            )
                        for case, (_, p) in zip(pair, hashes):
                            if p in puzzle_cases:
                                matches.append(exact_isomorphic(case, puzzle_cases[p]))
                        info["status"] = (
                            "duplicate"
                            if True in matches
                            else "isomorphism_inconclusive"
                            if None in matches
                            else "wl_collision"
                            if matches
                            else "cross_cell_screen"
                        )
                    else:
                        worlds.add(hashes[0][0])
                        for case, (w, p) in zip(pair, hashes):
                            puzzles.add(p)
                            world_cases[w] = case
                            puzzle_cases[p] = case
                            case["world_group"] = w
                            case["structure_group"] = p
                        state["pairs"].append(pair)
                state["diagnostics"].append(info)
                state["next_seed"] += 1
                state["complete"] = len(state["pairs"]) == count
                atomic_json(path, state)
    finally:
        if executor:
            executor.shutdown()
    return state


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
    world_cases = {}
    puzzle_cases = {}
    for c in state["cases"]:
        w, p = fingerprints(c)
        if w in worlds or p in puzzles:
            raise ValueError("duplicate in checkpoint")
        worlds.add(w)
        puzzles.add(p)
        world_cases[w] = c
        puzzle_cases[p] = c
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
                        matches = []
                        if w in world_cases:
                            matches.append(
                                exact_isomorphic(c, world_cases[w], world=True)
                            )
                        if p in puzzle_cases:
                            matches.append(exact_isomorphic(c, puzzle_cases[p]))
                        info["status"] = (
                            "duplicate"
                            if True in matches
                            else "isomorphism_inconclusive"
                            if None in matches
                            else "wl_collision"
                        )
                    else:
                        worlds.add(w)
                        puzzles.add(p)
                        world_cases[w] = c
                        puzzle_cases[p] = c
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


def reproduce_case(case):
    """Recreate a paired case from its private world and clue seeds."""
    if "world_seed" not in case:
        raise ValueError("case has no world seed")
    config = Config(**case["config"])
    suspects = [f"S{i + 1:02d}" for i in range(config.suspect_count)]
    fixed = WorldSampler(config.domains).sample_world(
        suspects,
        True,
        max_attempts=1000,
        rng=random.Random(case["world_seed"]),
        active_values_per_attribute=config.active_values_per_attribute,
    )
    result = generate(config, case["seed"], fixed_world=fixed)
    if result["status"] != "ok":
        raise RuntimeError("recorded case did not regenerate")
    reproduced = {**result["case"], "world_seed": case["world_seed"]}
    expected = {
        key: value
        for key, value in case.items()
        if key not in ("split", "cell", "held_out", "world_group", "structure_group")
    }
    if reproduced != expected:
        raise ValueError("regenerated case differs from recorded case")
    return reproduced


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
        config = Config(
            suspect_count=n,
            clue_count=k,
            min_indirect_clues=2,
            require_indirect_essential=True,
        )
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


def create_suite_v03(root, workers=1, dev_worlds=12, test_worlds=28):
    """Private, paired factorial suite; the five-attribute/high-reuse cell is held out."""
    if min(dev_worlds, test_worlds) < 1 or dev_worlds + test_worlds < 4:
        raise ValueError(
            "positive splits and at least four worlds per factor cell required"
        )
    root = Path(root)
    all_cases = []
    cells = []
    seen_worlds = set()
    seen_puzzles = set()
    for n in (4, 8, 12):
        for schema in ("four", "five"):
            domains = {k: list(v) for k, v in DEFAULT_DOMAINS.items()}
            if schema == "five":
                domains["route"] = ["North", "South", "East", "West"]
            for reuse in ("full", "high"):
                active = None if reuse == "full" else 2
                held_out = schema == "five" and reuse == "high"
                total = dev_worlds + test_worlds
                route_counts = {
                    "standard": (total + 1) // 2,
                    "pairwise": total // 4,
                }
                route_counts["cross_attribute"] = total - sum(route_counts.values())
                dev_counts = {
                    "standard": (dev_worlds + 1) // 2,
                    "pairwise": dev_worlds // 4,
                }
                dev_counts["cross_attribute"] = dev_worlds - sum(dev_counts.values())
                for relations in ("standard", "pairwise", "cross_attribute"):
                    enabled = (
                        tuple(t for t in TYPES if not t.startswith("suspect_"))
                        if relations != "pairwise"
                        else TYPES
                    )
                    common = dict(
                        suspect_count=n,
                        domains=domains,
                        enabled_types=enabled,
                        active_values_per_attribute=active,
                        min_pairwise_clues=2 if relations == "pairwise" else 0,
                        reasoning_route=relations,
                        mutation_steps=0,
                        max_attempts=16,
                        max_solver_calls=1500,
                        generation_seconds=20.0,
                    )
                    low = Config(clue_count=n + 4, **common)
                    high = Config(clue_count=n + 8, **common)
                    count = route_counts[relations]
                    cell_id = f"n{n}-{schema}-{reuse}-{relations}"
                    seed = (
                        300000
                        + n * 100000
                        + (schema == "five") * 20000
                        + (reuse == "high") * 10000
                        + {"standard": 0, "pairwise": 3000, "cross_attribute": 6000}[
                            relations
                        ]
                    )
                    state = build_paired_bank(
                        low,
                        high,
                        count,
                        seed,
                        root / "checkpoints" / f"{cell_id}.json",
                        workers,
                        excluded_worlds=seen_worlds,
                        excluded_puzzles=seen_puzzles,
                    )
                    if not state["complete"]:
                        raise RuntimeError(
                            f"underfilled {cell_id}; inspect checkpoint diagnostics"
                        )
                    for i, pair in enumerate(state["pairs"]):
                        split = (
                            "test" if held_out or i >= dev_counts[relations] else "dev"
                        )
                        for case in pair:
                            w, p = case["world_group"], case["structure_group"]
                            if p in seen_puzzles:
                                raise ValueError("cross-cell duplicate puzzle")
                            if w in seen_worlds and not any(
                                old["world_group"] == w and old["cell"] == cell_id
                                for old in all_cases
                            ):
                                raise ValueError("cross-cell duplicate world")
                            seen_worlds.add(w)
                            seen_puzzles.add(p)
                            validate_case(case)
                            all_cases.append(
                                {
                                    **case,
                                    "split": split,
                                    "cell": cell_id,
                                    "held_out": held_out,
                                }
                            )
                    cells.append(
                        {
                            "cell": cell_id,
                            "low_config": low.to_dict(),
                            "high_config": high.to_dict(),
                            "worlds": count,
                            "held_out": held_out,
                            "attempted_seeds": len(state["diagnostics"]),
                            "statuses": dict(
                                Counter(x["status"] for x in state["diagnostics"])
                            ),
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
        "design": "paired worlds; size x attribute schema x value reuse x relation regime",
        "held_out": "five attributes and high value reuse (test only)",
        "dev_worlds_per_nonheldout_cell": dev_worlds,
        "test_worlds_per_cell": test_worlds,
        "worlds": len(seen_worlds),
        "cases": len(all_cases),
        "cells": cells,
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
