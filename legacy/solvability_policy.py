import random
from itertools import combinations


def clue_signature(clue):
    return tuple(sorted(clue.items()))


def profile_collisions(suspects, world, murderer):
    murderer_profile = world[murderer]
    return [
        suspect
        for suspect in suspects
        if suspect != murderer and world[suspect] == murderer_profile
    ]


def clue_category(clue):
    clue_type = clue["type"]
    if clue_type in ["unary_positive", "unary_negative", "crime_positive"]:
        return "direct"
    if clue_type in ["indirect_positive", "crime_same_as"]:
        return "indirect_positive"
    if clue_type in ["indirect_negative", "crime_negative", "crime_different_from"]:
        return "indirect_negative"
    return "unknown"


def is_murderer_linking_clue(clue):
    return clue["type"] in [
        "crime_positive",
        "crime_negative",
        "crime_same_as",
        "crime_different_from",
    ]


def is_positive_murderer_linking_clue(clue):
    return clue["type"] == "crime_positive"


def is_indirect_clue(clue):
    return clue_category(clue) in ["indirect_positive", "indirect_negative"]


def count_values(items):
    counts = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return counts


def sample_alpha_beta_categories(alpha, beta, target_total, rng=None):
    rng = rng or random
    categories = []
    for _ in range(target_total):
        if rng.random() < alpha:
            categories.append("direct")
        elif rng.random() < beta:
            categories.append("indirect_positive")
        else:
            categories.append("indirect_negative")
    return categories


def choose_weighted_guided_clue(
    candidates,
    selected,
    solver,
    rng,
    candidate_sample_size,
    min_unique_subset_size=1,
):
    if len(candidates) > candidate_sample_size:
        candidates = rng.sample(candidates, candidate_sample_size)

    scored = []
    for clue in candidates:
        score = clue_elimination_score(clue, selected, solver.true_world, solver.suspects)
        scored.append((score, clue))

    if not scored:
        return None

    max_score = max(score for score, _ in scored)
    best_band = [clue for score, clue in scored if score == max_score]
    return rng.choice(best_band)


def clue_elimination_score(clue, selected, world, suspects):
    """Cheap guidance score; final validity is still checked by the CSP solver."""
    clue_type = clue["type"]

    if clue_type == "crime_positive":
        attr, value = clue["attribute"], clue["value"]
        return 6 + sum(1 for suspect in suspects if world[suspect][attr] != value)

    if clue_type == "crime_negative":
        attr, value = clue["attribute"], clue["value"]
        return 4 + sum(1 for suspect in suspects if world[suspect][attr] == value)

    if clue_type == "crime_same_as":
        suspect, attr = clue["suspect"], clue["attribute"]
        value = world[suspect][attr]
        return 5 + sum(1 for candidate in suspects if world[candidate][attr] != value)

    if clue_type == "crime_different_from":
        suspect, attr = clue["suspect"], clue["attribute"]
        value = world[suspect][attr]
        return 5 + sum(1 for candidate in suspects if world[candidate][attr] == value)

    murderer_constraints = [
        c for c in selected if is_murderer_linking_clue(c)
    ]
    if clue_type in ["unary_positive", "unary_negative"] and murderer_constraints:
        return 3

    if clue_type in ["indirect_positive", "indirect_negative"]:
        return 2

    return 1


def any_subset_solves(clues, solver, max_subset_size):
    if max_subset_size <= 0:
        return False

    limit = min(max_subset_size, len(clues))
    for size in range(1, limit + 1):
        for subset in combinations(clues, size):
            if solver.is_unique(list(subset)):
                return True
    return False


def minimal_unique_subset_size(clues, solver):
    for size in range(1, len(clues) + 1):
        for subset in combinations(clues, size):
            if solver.is_unique(list(subset)):
                return size
    return None


def passes_difficulty_constraints(
    clues,
    solver,
    min_indirect_clues=0,
    max_murderer_links=None,
    max_positive_murderer_links=None,
    min_unique_subset_size=1,
    require_indirect_essential=False,
):
    indirect_count = sum(1 for clue in clues if is_indirect_clue(clue))
    murderer_link_count = sum(1 for clue in clues if is_murderer_linking_clue(clue))
    positive_murderer_link_count = sum(
        1 for clue in clues if is_positive_murderer_linking_clue(clue)
    )

    if indirect_count < min_indirect_clues:
        return False, "too_few_indirect_clues"
    if max_murderer_links is not None and murderer_link_count > max_murderer_links:
        return False, "too_many_murderer_links"
    if (
        max_positive_murderer_links is not None
        and positive_murderer_link_count > max_positive_murderer_links
    ):
        return False, "too_many_positive_murderer_links"
    if any_subset_solves(clues, solver, min_unique_subset_size - 1):
        return False, "small_subset_solves"

    if require_indirect_essential:
        direct_only = [clue for clue in clues if not is_indirect_clue(clue)]
        if solver.is_unique(direct_only):
            return False, "direct_only_solves"

        for i, clue in enumerate(clues):
            if is_indirect_clue(clue):
                without_clue = clues[:i] + clues[i + 1:]
                if not solver.is_unique(without_clue):
                    return True, None
        return False, "no_indirect_clue_is_essential"

    return True, None


def enforce_category_minimums(categories, target_total, rng, min_murderer_links, min_indirect_clues):
    adjusted = list(categories)
    adjustment_count = 0

    if adjusted.count("direct") < min_murderer_links:
        replaceable = [i for i, category in enumerate(adjusted) if category != "direct"]
        rng.shuffle(replaceable)
        for index in replaceable[: min_murderer_links - adjusted.count("direct")]:
            adjusted[index] = "direct"
            adjustment_count += 1

    indirect_count = sum(1 for category in adjusted if category != "direct")
    if indirect_count < min_indirect_clues:
        replaceable = [i for i, category in enumerate(adjusted) if category == "direct"]
        rng.shuffle(replaceable)
        needed = min_indirect_clues - indirect_count
        for index in replaceable[:needed]:
            adjusted[index] = "indirect_positive" if rng.random() < 0.5 else "indirect_negative"
            adjustment_count += 1

    return adjusted[:target_total], adjustment_count


def generate_probabilistic_clue_set(
    clue_pool,
    solver,
    alpha,
    beta,
    target_total,
    rng=None,
    max_attempts=500,
    min_murderer_links=1,
    max_murderer_links=None,
    max_positive_murderer_links=None,
    min_indirect_clues=0,
    min_unique_subset_size=1,
    require_indirect_essential=False,
    candidate_sample_size=1000,
):
    """Generate a solvable bank via alpha/beta sampling + solver rejection.

    Category plans are sampled from alpha/beta. Clue choice within each sampled
    category is randomized but biased toward clues that reduce feasible
    murderers, which keeps rejection practical at small clue budgets.
    """
    rng = rng or random
    pools = {
        "direct": [c for c in clue_pool if clue_category(c) == "direct"],
        "indirect_positive": [
            c for c in clue_pool if clue_category(c) == "indirect_positive"
        ],
        "indirect_negative": [
            c for c in clue_pool if clue_category(c) == "indirect_negative"
        ],
    }
    murderer_link_pool = [
        c for c in clue_pool if is_murderer_linking_clue(c)
    ]

    for attempt in range(1, max_attempts + 1):
        sampled_categories = sample_alpha_beta_categories(
            alpha,
            beta,
            target_total,
            rng,
        )
        sampled_categories, constraint_adjustments = enforce_category_minimums(
            sampled_categories,
            target_total,
            rng,
            min_murderer_links,
            min_indirect_clues,
        )

        clues = []
        selected_keys = set()
        murderer_link_count = 0
        positive_murderer_link_count = 0

        for index, category in enumerate(sampled_categories):
            remaining_categories = sampled_categories[index:]
            slots_remaining = len(remaining_categories)

            candidates = [
                c for c in pools[category]
                if clue_signature(c) not in selected_keys
            ]
            links_needed = min_murderer_links - murderer_link_count
            if links_needed >= slots_remaining:
                candidates = [
                    c for c in murderer_link_pool
                    if (
                        clue_signature(c) not in selected_keys
                        and clue_category(c) == category
                    )
                ]
                if (
                    max_positive_murderer_links is not None
                    and positive_murderer_link_count >= max_positive_murderer_links
                ):
                    candidates = [
                        c for c in candidates
                        if not is_positive_murderer_linking_clue(c)
                    ]
            elif (
                category == "direct"
                and max_murderer_links is not None
                and murderer_link_count >= max_murderer_links
            ):
                candidates = [
                    c for c in candidates
                    if not is_murderer_linking_clue(c)
                ]
            elif (
                category == "direct"
                and max_positive_murderer_links is not None
                and positive_murderer_link_count >= max_positive_murderer_links
            ):
                candidates = [
                    c for c in candidates
                    if not is_positive_murderer_linking_clue(c)
                ]

            if not candidates:
                candidates = [
                    c for c in clue_pool
                    if clue_signature(c) not in selected_keys
                ]
                constraint_adjustments += 1
            if not candidates:
                break

            clue = choose_weighted_guided_clue(
                candidates,
                clues,
                solver,
                rng,
                candidate_sample_size,
                min_unique_subset_size,
            )
            if clue is None:
                break

            clues.append(clue)
            selected_keys.add(clue_signature(clue))
            if is_murderer_linking_clue(clue):
                murderer_link_count += 1
            if is_positive_murderer_linking_clue(clue):
                positive_murderer_link_count += 1

        if len(clues) != target_total:
            continue
        if murderer_link_count < min_murderer_links:
            continue
        if max_murderer_links is not None and murderer_link_count > max_murderer_links:
            continue
        if (
            max_positive_murderer_links is not None
            and positive_murderer_link_count > max_positive_murderer_links
        ):
            continue

        if not solver.is_unique(clues):
            continue

        passes_constraints, rejection_reason = passes_difficulty_constraints(
            clues,
            solver,
            min_indirect_clues,
            max_murderer_links,
            max_positive_murderer_links,
            min_unique_subset_size,
            require_indirect_essential,
        )
        if not passes_constraints:
            continue

        clue_types = [clue["type"] for clue in clues]
        return {
            "items": clues,
            "attempts": attempt,
            "murderer_link_count": murderer_link_count,
            "positive_murderer_link_count": positive_murderer_link_count,
            "indirect_clue_count": sum(1 for clue in clues if is_indirect_clue(clue)),
            "minimal_unique_subset_size": minimal_unique_subset_size(clues, solver),
            "sampled_category_counts": count_values(sampled_categories),
            "clue_type_counts": count_values(clue_types),
            "constraint_adjustments": constraint_adjustments,
            "candidate_sample_size": candidate_sample_size,
            "rejection_reason": rejection_reason,
        }

    return None
