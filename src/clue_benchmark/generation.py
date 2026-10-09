"""One bounded generation API shared by both benchmark tracks."""

import random
import time
from collections import Counter
from importlib.metadata import version
from itertools import combinations

from .clue_generator import ClueGenerator
from .config import DATA_VERSION, Config, digest
from .logic import clean, fact_key, is_indirect, is_link, truth
from .solver import Outcome, Solver, Unresolved
from .world_sampler import WorldSampler


def _weight(c, config):
    if not is_indirect(c):
        return config.alpha
    return (1 - config.alpha) * (
        config.beta
        if c["type"] in ("indirect_positive", "crime_same_as", "suspect_same_as")
        else 1 - config.beta
    )


def _sample(pool, n, rng, config):
    pool = list(pool)
    out = []
    for _ in range(n):
        if not pool:
            break

        def category(c):
            return (
                "direct"
                if not is_indirect(c)
                else (
                    "positive"
                    if c["type"]
                    in ("indirect_positive", "crime_same_as", "suspect_same_as")
                    else "negative"
                )
            )

        counts = Counter(category(c) for c in pool)
        weights = [_weight(c, config) / counts[category(c)] for c in pool]
        c = rng.choices(pool, weights=weights if sum(weights) > 0 else None, k=1)[0]
        out.append(c)
        pool.remove(c)
    return out


def _constraints(clues, config, solver):
    links = sum(is_link(c) for c in clues)
    positive = sum(c["type"] == "crime_positive" for c in clues)
    if links < config.min_murderer_links:
        return False
    if config.max_murderer_links is not None and links > config.max_murderer_links:
        return False
    if (
        config.max_positive_murderer_links is not None
        and positive > config.max_positive_murderer_links
    ):
        return False
    if sum(is_indirect(c) for c in clues) < config.min_indirect_clues:
        return False
    if sum(c["type"].startswith("suspect_") for c in clues) < config.min_pairwise_clues:
        return False
    if solver.check(clues).status != Outcome.UNIQUE:
        return False
    for size in range(1, config.min_unique_subset_size):
        for subset in combinations(clues, size):
            if solver.check(subset).status == Outcome.UNIQUE:
                return False
    if config.require_indirect_essential:
        if (
            solver.check([c for c in clues if not is_indirect(c)]).status
            == Outcome.UNIQUE
        ):
            return False
        if not any(
            is_indirect(c)
            and solver.check(clues[:i] + clues[i + 1 :]).status != Outcome.UNIQUE
            for i, c in enumerate(clues)
        ):
            return False
    essential_type = {
        "pairwise": lambda c: c["type"].startswith("suspect_"),
        "cross_attribute": lambda c: (
            c["type"] in ("indirect_positive", "indirect_negative")
        ),
    }.get(config.reasoning_route)
    if essential_type and not any(
        essential_type(c)
        and solver.check(clues[:i] + clues[i + 1 :]).status != Outcome.UNIQUE
        for i, c in enumerate(clues)
    ):
        return False
    return True


def _proof_scaffold(world, murderer, domains, rng, config):
    """Build a short, mixed proof that excludes each innocent suspect.

    Direct exclusions need a crime-value anchor. A relationship exclusion does
    not, so alpha controls a genuine construction choice rather than fillers.
    Positive relationship anchors use beta and require a supporting unary fact.
    """
    attrs = list(domains)
    innocents = [s for s in world if s != murderer]
    differences = {
        s: [a for a in attrs if world[s][a] != world[murderer][a]] for s in innocents
    }
    if config.reasoning_route in ("pairwise", "cross_attribute"):
        candidates = []
        for target in innocents:
            for attribute in differences[target]:
                if config.reasoning_route == "pairwise":
                    for reference in world:
                        if reference == target:
                            continue
                        same = world[target][attribute] == world[reference][attribute]
                        matches_crime = (
                            world[reference][attribute] == world[murderer][attribute]
                        )
                        if same or matches_crime:
                            candidates.append((target, attribute, reference, same))
                else:
                    for other in differences[target]:
                        if other == attribute:
                            continue
                        if not any(
                            attrs[attribute] == world[target][attribute]
                            and attrs[other] == world[murderer][other]
                            for attrs in world.values()
                        ):
                            candidates.append((target, attribute, other))
        if not candidates:
            return []
        chosen = rng.choice(candidates)
        target, attribute = chosen[:2]
        if config.reasoning_route == "pairwise":
            reference, same = chosen[2:]
            special = [
                dict(
                    type="suspect_same_as" if same else "suspect_different_from",
                    suspect=target,
                    other_suspect=reference,
                    attribute=attribute,
                ),
                dict(
                    type="unary_positive",
                    suspect=reference,
                    attribute=attribute,
                    value=world[reference][attribute],
                ),
                dict(
                    type="crime_positive",
                    attribute=attribute,
                    value=world[murderer][attribute],
                ),
            ]
        else:
            other = chosen[2]
            special = [
                dict(
                    type="unary_positive",
                    suspect=target,
                    attribute=attribute,
                    value=world[target][attribute],
                ),
                dict(
                    type="crime_positive", attribute=other, value=world[murderer][other]
                ),
                dict(
                    type="indirect_negative",
                    attr1=attribute,
                    val1=world[target][attribute],
                    attr2=other,
                    val2=world[murderer][other],
                ),
            ]
        # Other suspects receive separate exclusions, leaving the selected route
        # as the only constructed explanation for this target.
        for s in innocents:
            if s != target:
                special.append(
                    dict(
                        type="crime_different_from",
                        suspect=s,
                        attribute=rng.choice(differences[s]),
                    )
                )
        return list({fact_key(c): c for c in special}.values())
    direct, relational = [], []
    can_direct = {"unary_positive", "crime_positive"} <= set(config.enabled_types)
    can_relational = "crime_different_from" in config.enabled_types
    for s in innocents:
        if can_direct and (not can_relational or rng.random() < config.alpha):
            direct.append(s)
        elif can_relational:
            relational.append(s)
        else:
            return []

    # Choose the fewest crime attributes covering all direct exclusions.
    covers = [
        group
        for size in range(len(attrs) + 1)
        for group in combinations(attrs, size)
        if all(any(a in differences[s] for a in group) for s in direct)
    ]
    minimum = min(map(len, covers))
    anchors = rng.choice([group for group in covers if len(group) == minimum])
    clues = []
    for s in direct:
        a = rng.choice([a for a in anchors if a in differences[s]])
        clues.append(
            dict(type="unary_positive", suspect=s, attribute=a, value=world[s][a])
        )
    for s in relational:
        clues.append(
            dict(
                type="crime_different_from",
                suspect=s,
                attribute=rng.choice(differences[s]),
            )
        )
    for a in anchors:
        matching = [s for s in innocents if world[s][a] == world[murderer][a]]
        if (
            matching
            and "crime_same_as" in config.enabled_types
            and rng.random() < config.beta
        ):
            reference = rng.choice(matching)
            clues.extend(
                [
                    dict(
                        type="unary_positive",
                        suspect=reference,
                        attribute=a,
                        value=world[reference][a],
                    ),
                    dict(type="crime_same_as", suspect=reference, attribute=a),
                ]
            )
        else:
            clues.append(
                dict(type="crime_positive", attribute=a, value=world[murderer][a])
            )
    return list({fact_key(c): c for c in clues}.values())


def generate(config: Config, seed: int, *, fixed_world=None):
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    config = Config(**config.to_dict())
    rng = random.Random(seed)
    start = time.monotonic()
    deadline = start + config.generation_seconds
    suspects = [f"S{i + 1:02d}" for i in range(config.suspect_count)]
    rejects = Counter()
    calls = 0
    if fixed_world is not None:
        world, murderer = fixed_world
        if (
            set(world) != set(suspects)
            or murderer not in suspects
            or any(
                set(attrs) != set(config.domains)
                or any(attrs[a] not in config.domains[a] for a in config.domains)
                for attrs in world.values()
            )
        ):
            raise ValueError("invalid fixed world")
        if any(world[s] == world[murderer] for s in suspects if s != murderer):
            raise ValueError("murderer profile is not unique")
    for attempt in range(1, config.max_attempts + 1):
        if time.monotonic() >= deadline:
            rejects["generation_timeout"] += 1
            break
        if calls >= config.max_solver_calls:
            rejects["solver_budget"] += 1
            break
        if fixed_world is None:
            try:
                world, murderer = WorldSampler(config.domains).sample_world(
                    suspects,
                    True,
                    max_attempts=1000,
                    rng=rng,
                    active_values_per_attribute=config.active_values_per_attribute,
                )
            except RuntimeError:
                rejects["world_sampling_exhausted"] += 1
                break
        builder = ClueGenerator(world, murderer, config.domains)
        builder.build_clue_pool(rng=rng)
        unique = {
            fact_key(c): clean(c)
            for c in builder.clue_pool
            if c["type"] in config.enabled_types
        }
        pool = [unique[k] for k in sorted(unique)]
        pool_keys = {id(c): key for key, c in unique.items()}
        if len(pool) < config.clue_count:
            rejects["insufficient_pool"] += 1
            break
        solver = Solver(suspects, config.domains, config, deadline)
        solver.calls = calls
        scaffold = _proof_scaffold(world, murderer, config.domains, rng, config)
        if not scaffold:
            rejects["proof_route_unavailable"] += 1
            if fixed_world is not None:
                break
            continue
        if len(scaffold) + config.min_pairwise_clues > config.clue_count:
            rejects["scaffold_size"] += 1
            continue
        keys = {fact_key(c) for c in scaffold}
        pairwise = _sample(
            [
                c
                for c in pool
                if c["type"].startswith("suspect_") and fact_key(c) not in keys
            ],
            config.min_pairwise_clues,
            rng,
            config,
        )
        keys.update(fact_key(c) for c in pairwise)
        clues = (
            scaffold
            + pairwise
            + _sample(
                [c for c in pool if fact_key(c) not in keys],
                config.clue_count - len(scaffold) - len(pairwise),
                rng,
                config,
            )
        )
        try:
            # Weighted replacements retain verified uniqueness; constraints are checked at the end.
            for _ in range(config.mutation_steps):
                index = rng.randrange(len(clues))
                keys = {fact_key(c) for c in clues}
                available = [c for c in pool if pool_keys[id(c)] not in keys]
                if not available:
                    break
                proposed = clues.copy()
                proposed[index] = _sample(available, 1, rng, config)[0]
                if solver.check(proposed).status == Outcome.UNIQUE:
                    clues = proposed
            if not _constraints(clues, config, solver):
                rejects["constraints"] += 1
                continue
            result = solver.check(clues)
            if result.murderer != murderer or not all(
                truth(c, world, murderer) for c in clues
            ):
                raise AssertionError("truth or murderer mismatch")
            rng.shuffle(clues)
            body = {
                "suspects": suspects,
                "domains": config.domains,
                "clues": clues,
                "solution": {"murderer": murderer, "world": world},
            }
            return {
                "status": "ok",
                "case": {
                    **body,
                    "case_id": digest({"body": body, "config": config.fingerprint})[
                        :24
                    ],
                    "seed": seed,
                    "config": config.to_dict(),
                    "generator_version": DATA_VERSION,
                    "solver_version": version("ortools"),
                },
                "diagnostics": {
                    "seed": seed,
                    "attempts": attempt,
                    "solver_calls": solver.calls,
                    "rejections": dict(rejects),
                    "seconds": time.monotonic() - start,
                    "clue_types": dict(Counter(c["type"] for c in clues)),
                },
            }
        except Unresolved as exc:
            rejects[str(exc)] += 1
        finally:
            calls = solver.calls
    return {
        "status": "failed",
        "case": None,
        "diagnostics": {
            "seed": seed,
            "attempts": attempt,
            "solver_calls": calls,
            "rejections": dict(rejects),
            "seconds": time.monotonic() - start,
        },
    }


def validate_case(case):
    config = Config(**case["config"])
    suspects = case["suspects"]
    domains = case["domains"]
    clues = case["clues"]
    if len(suspects) != config.suspect_count or len(set(suspects)) != len(suspects):
        raise ValueError("invalid suspects")
    if domains != config.domains or len(clues) != config.clue_count:
        raise ValueError("configuration mismatch")
    world = case["solution"]["world"]
    murderer = case["solution"]["murderer"]
    if set(world) != set(suspects) or murderer not in suspects:
        raise ValueError("invalid solution")
    for attrs in world.values():
        if set(attrs) != set(domains) or any(
            attrs[a] not in domains[a] for a in domains
        ):
            raise ValueError("invalid world")
    from .logic import validate

    for c in clues:
        validate(c, suspects, domains)
        if c["type"] not in config.enabled_types or not truth(c, world, murderer):
            raise ValueError("untruthful or disabled clue")
    if len({fact_key(c) for c in clues}) != len(clues):
        raise ValueError("duplicate facts")
    solver = Solver(suspects, domains, config)
    if (
        not _constraints(clues, config, solver)
        or solver.check(clues).murderer != murderer
    ):
        raise ValueError("invalid uniqueness/constraints")
    return True
