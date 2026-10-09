"""Shared JSON helpers, structural screening and flat-generator compatibility."""

import json
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from importlib.metadata import version
from pathlib import Path

from .config import DATA_VERSION, Config, digest
from .generation import generate


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
