"""Generate study-ready clue banks with alpha/beta sampling and solver rejection."""

import argparse
from concurrent.futures import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
import json
import os
import random
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from clue_formatter import ClueFormatter
from clue_generator import ClueGenerator
from csp_solver import MysteryCSPSolver
from clue_metadata import (
    GENERATOR_VERSION,
    case_id_for_seed,
    decorate_clue,
    duplicate_stats,
)
from clue_validation import necessary_clues, validate_bank
from solvability_policy import generate_probabilistic_clue_set, profile_collisions
from world_sampler import WorldSampler

SEEDS = [
    1103,
    2202,
    3304,
    4404,
    5505,
    6606,
    7707,
    8808,
    9909,
    1413,
    1716,
    2323,
    2525,
    2727,
]
SUSPECTS_BY_COUNT = {
    3: ["James Hartley", "Eleanor Blackwood", "Margaret Finch"],
    4: [
        "James Hartley",
        "Eleanor Blackwood",
        "Margaret Finch",
        "Marcus Webb",
    ],
}
DOMAINS = {
    "weapon": [
        "Wrench",
        "Poison Vial",
        "Rope",
        "Bloody Handkerchief",
    ],
    "location": [
        "Master Bedroom",
        "Bathroom",
        "Study",
        "Kitchen",
    ],
    "motive": [
        "Inheritance",
        "Revenge",
        "Jealousy",
        "Blackmail",
    ],
    "time": [
        "Late Evening",
        "Midnight",
        "1:00 AM",
        "2:00 AM",
    ],
}

DIFFICULTY = {
    "easy": {
        "alpha": 0.95,
        "beta": 0.95,
        "target_clues": 5,
        "min_murderer_links": 1,
        "max_murderer_links": 2,
        "min_indirect_clues": 0,
        "min_unique_subset_size": 3,
        "require_indirect_essential": False,
        "max_attempts": 1000,
        "candidate_sample_size": 96,
    },
    "medium": {
        "alpha": 0.70,
        "beta": 0.75,
        "target_clues": 7,
        "min_murderer_links": 1,
        "max_murderer_links": 2,
        "max_positive_murderer_links": 1,
        "min_indirect_clues": 1,
        "min_unique_subset_size": 4,
        "require_indirect_essential": True,
        "max_attempts": 6000,
        "candidate_sample_size": 128,
    },
    "hard": {
        "alpha": 0.45,
        "beta": 0.55,
        "target_clues": 8,
        "min_murderer_links": 2,
        "max_murderer_links": 3,
        "max_positive_murderer_links": 1,
        "min_indirect_clues": 2,
        "min_unique_subset_size": 5,
        "require_indirect_essential": True,
        "max_attempts": 12000,
        "candidate_sample_size": 160,
    },
}

TARGETS_BY_SUSPECT_COUNT = {
    3: {"easy": 4, "medium": 6, "hard": 7},
    4: {"easy": 5, "medium": 7, "hard": 8},
}


def difficulty_for_suspect_count(suspect_count):
    difficulty = {
        name: params.copy()
        for name, params in DIFFICULTY.items()
    }
    for name, target in TARGETS_BY_SUSPECT_COUNT[suspect_count].items():
        difficulty[name]["target_clues"] = target
    return difficulty


def solve_seed(seed, suspects, difficulty):
    started = time.perf_counter()
    seed_rng = random.Random(seed)
    world, murderer = WorldSampler(DOMAINS).sample_world(
        suspects,
        require_unique_murderer_profile=True,
        rng=seed_rng,
    )

    clue_gen = ClueGenerator(world, murderer, DOMAINS)
    pool_size = clue_gen.build_clue_pool(rng=seed_rng)
    solver = MysteryCSPSolver(suspects, DOMAINS, world, murderer)

    case_id = case_id_for_seed(seed)
    state_full = {
        "case_id": case_id,
        "seed": seed,
        "murderer": murderer,
        "world": world,
        "clues": {},
    }

    diagnostics = {
        "generator_version": GENERATOR_VERSION,
        "solver_version": _solver_version(),
        "seed": seed,
        "pool_size": pool_size,
        "murderer_profile_collisions": profile_collisions(suspects, world, murderer),
        "counts": {},
        "generation_attempts": {},
        "clue_type_counts": {},
        "sampled_category_counts": {},
        "minimal_unique_subset_sizes": {},
        "clue_complexity_counts": {},
        "duplicate_counts": {},
        "generation_duration_seconds": None,
        "status": "ok",
    }

    for diff_name, params in difficulty.items():
        rng = random.Random(seed * 1009 + len(diff_name) * 97)
        result = generate_probabilistic_clue_set(
            clue_gen.clue_pool,
            solver,
            params["alpha"],
            params["beta"],
            params["target_clues"],
            rng,
            max_attempts=params.get("max_attempts", 10000),
            min_murderer_links=params.get("min_murderer_links", 1),
            max_murderer_links=params.get("max_murderer_links"),
            max_positive_murderer_links=params.get("max_positive_murderer_links"),
            min_indirect_clues=params.get("min_indirect_clues", 0),
            min_unique_subset_size=params.get("min_unique_subset_size", 1),
            require_indirect_essential=params.get("require_indirect_essential", False),
            candidate_sample_size=params.get("candidate_sample_size", 18),
        )

        if result is None or not solver.is_unique(result["items"]):
            diagnostics["status"] = "failed"
            diagnostics["reason"] = f"{diff_name} did not produce unique clues"
            diagnostics["generation_duration_seconds"] = (
                time.perf_counter() - started
            )
            return None, diagnostics

        raw = result["items"]
        text = [ClueFormatter.format(c) for c in raw]
        necessary = necessary_clues(raw, solver)
        records = [
            decorate_clue(
                clue,
                case_id,
                diff_name,
                formatted_text,
                necessary_for_uniqueness=necessary[index],
            )
            for index, (clue, formatted_text) in enumerate(zip(raw, text))
        ]
        valid, reason = validate_bank(records, raw, world, murderer, solver)
        if not valid:
            diagnostics["status"] = "failed"
            diagnostics["reason"] = reason
            diagnostics["generation_duration_seconds"] = (
                time.perf_counter() - started
            )
            return None, diagnostics

        bank_duplicates = duplicate_stats(records)

        state_full["clues"][diff_name] = {
            "bank_tier": diff_name,
            "alpha": params["alpha"],
            "beta": params["beta"],
            "target_clues": params["target_clues"],
            "count": len(raw),
            "generation_attempts": result["attempts"],
            "murderer_link_count": result["murderer_link_count"],
            "positive_murderer_link_count": result["positive_murderer_link_count"],
            "indirect_clue_count": result["indirect_clue_count"],
            "minimal_unique_subset_size": result["minimal_unique_subset_size"],
            "clue_type_counts": result["clue_type_counts"],
            "clue_complexity_counts": {
                complexity: sum(
                    1 for clue in raw
                    if clue.get("difficulty") == complexity
                )
                for complexity in sorted(
                    {clue.get("difficulty", "unknown") for clue in raw}
                )
            },
            "sampled_category_counts": result["sampled_category_counts"],
            "constraint_adjustments": result["constraint_adjustments"],
            "candidate_sample_size": result["candidate_sample_size"],
            "is_unique_solution": True,
            "items": text,
            "raw_items": raw,
            "records": records,
            "duplicate_stats": bank_duplicates,
            "validation": {
                "truthful_for_generated_world": True,
                "solver_compatible": True,
                "unique_murderer": True,
                "uniqueness_definition": "unique_murderer",
            },
        }
        diagnostics["counts"][diff_name] = len(raw)
        diagnostics["generation_attempts"][diff_name] = result["attempts"]
        diagnostics["clue_type_counts"][diff_name] = result["clue_type_counts"]
        diagnostics["clue_complexity_counts"][diff_name] = (
            state_full["clues"][diff_name]["clue_complexity_counts"]
        )
        diagnostics["duplicate_counts"][diff_name] = bank_duplicates
        diagnostics["sampled_category_counts"][diff_name] = (
            result["sampled_category_counts"]
        )
        diagnostics["minimal_unique_subset_sizes"][diff_name] = (
            result["minimal_unique_subset_size"]
        )

    cross_bank_facts = [
        record["clue_fact_id"]
        for bank in state_full["clues"].values()
        for record in bank["records"]
    ]
    cross_bank_stats = duplicate_stats(
        [
            {"clue_fact_id": fact_id, "formatted_text": fact_id}
            for fact_id in cross_bank_facts
        ]
    )
    diagnostics["duplicate_counts"]["across_banks"] = cross_bank_stats
    diagnostics["generation_duration_seconds"] = time.perf_counter() - started
    state_full["metadata"] = {
        "generator_version": GENERATOR_VERSION,
        "solver_version": diagnostics["solver_version"],
        "generation_seed": seed,
        "generation_duration_seconds": diagnostics["generation_duration_seconds"],
        "uniqueness_definition": "unique_murderer",
        "manual_import_ready": True,
    }
    return state_full, diagnostics


def _solver_version():
    try:
        return version("ortools")
    except PackageNotFoundError:
        return "unknown"


def write_output(path, suspects_count, difficulty, diagnostics, states_full):
    out_full = {
        "version": 24,
        "generation_policy": "alpha_beta_weighted_sampling_with_solver_rejection",
        "suspect_count": suspects_count,
        "difficulty_params": difficulty,
        "constraints": {
            "fixed_seeds": [state["seed"] for state in states_full],
            "independently_solvable_per_bank": True,
            "unique_murderer_profile_required": True,
            "min_murderer_linking_clues_per_bank": 1,
            "solvability_check": "CSP unique murderer validation",
            "alpha_beta_controls": "full bank clue sampling before rejection",
            "medium_hard_direct_only_solve_rejected": True,
            "hard_requires_indirect_reasoning": True,
            "uniqueness_definition": "unique_murderer",
            "manual_import_metadata": "clue_records",
        },
        "diagnostics": diagnostics,
        "states": states_full,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out_full, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suspects", type=int, choices=[3, 4], default=4)
    parser.add_argument(
        "--output-prefix",
        default="generated_puzzle_states_study",
    )
    parser.add_argument(
        "--target-states",
        type=int,
        default=25,
        help="number of fully verified banks to produce",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=min(8, max(1, (os.cpu_count() or 2) - 1)),
        help="number of parallel worker threads",
    )
    args = parser.parse_args()
    if args.target_states < 1:
        parser.error("--target-states must be positive")
    if args.workers < 1:
        parser.error("--workers must be positive")

    suspects = SUSPECTS_BY_COUNT[args.suspects]
    difficulty = difficulty_for_suspect_count(args.suspects)
    states_full = []
    diagnostics = []
    attempted_seeds = set()

    existing_path = Path(f"{args.output_prefix}.json")
    if existing_path.exists():
        with existing_path.open("r", encoding="utf-8") as f:
            existing = json.load(f)
        if (
            existing.get("suspect_count") == args.suspects
            and existing.get("version") == 24
        ):
            reusable_states = existing.get("states", [])
            reusable = all(
                state.get("metadata", {}).get("manual_import_ready")
                and state.get("metadata", {}).get("generator_version") == GENERATOR_VERSION
                and all(
                    "records" in bank
                    for bank in state.get("clues", {}).values()
                )
                for state in reusable_states
            )
            states_full = reusable_states if reusable else []
            diagnostics = [
                info for info in existing.get("diagnostics", [])
                if info.get("status") == "ok"
            ] if reusable else []
            if reusable:
                attempted_seeds.update(
                    info.get("seed") for info in existing.get("diagnostics", [])
                )

    for seed in SEEDS:
        attempted_seeds.add(seed)

    full_path = f"{args.output_prefix}.json"

    candidate_seed = 3030
    seed_queue = [seed for seed in SEEDS if seed not in attempted_seeds]

    try:
        executor = ProcessPoolExecutor(max_workers=args.workers)
    except PermissionError:
        executor = ThreadPoolExecutor(max_workers=args.workers)

    with executor:
        while len(states_full) < args.target_states:
            batch_size = min(
                args.workers * 2,
                args.target_states - len(states_full),
            )
            batch = []
            while len(batch) < batch_size:
                if seed_queue:
                    seed = seed_queue.pop(0)
                else:
                    while candidate_seed in attempted_seeds:
                        candidate_seed += 1
                    seed = candidate_seed
                    candidate_seed += 1
                attempted_seeds.add(seed)
                batch.append(seed)

            futures = {
                executor.submit(solve_seed, seed, suspects, difficulty): seed
                for seed in batch
            }
            for future in as_completed(futures):
                seed = futures[future]
                result, info = future.result()
                diagnostics.append(info)
                if result is None:
                    print(
                        f"Seed {seed}: FAILED ({info.get('reason')})",
                        flush=True,
                    )
                    continue

                states_full.append(result)
                print(
                    f"Seed {seed}: OK "
                    f"E/M/H={info['counts']['easy']}/"
                    f"{info['counts']['medium']}/{info['counts']['hard']} "
                    f"({len(states_full)}/{args.target_states})",
                    flush=True,
                )

            write_output(
                full_path,
                args.suspects,
                difficulty,
                diagnostics,
                states_full,
            )

    print(f"File written: {full_path}", flush=True)
    print(
        f"Solved states: {len(states_full)} / {args.target_states}",
        flush=True,
    )


if __name__ == "__main__":
    main()
