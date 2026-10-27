"""Bounded community construction, certified partitions and lazy nuisance data."""

import random
import time
from copy import deepcopy
from dataclasses import replace

from .clue_formatter import ClueFormatter
from .clue_generator import ClueGenerator
from .community_semantics import (
    Budget,
    certify,
    coalition_certificate,
    essential_subset,
    evaluate,
    minimum_subset,
    reliability_profile,
)
from .config import Config, digest
from .generation import generate
from .independent_oracle import holds
from .logic import fact_key, is_indirect, is_link
from .solver import Unresolved


def _report(clue):
    constraint = {k: v for k, v in clue.items() if k != "difficulty"}
    return {"report_id": digest(constraint), "constraint": constraint}


def _constructed(cfg, seed):
    rng = random.Random(seed)
    n = cfg.suspect_count
    suspects = [f"S{i + 1:02d}" for i in range(n)]
    culprit = rng.choice(suspects)
    innocents = [s for s in suspects if s != culprit]
    rng.shuffle(innocents)
    attr = next(iter(cfg.domains))
    zero, one = cfg.domains[attr][:2]
    world = {s: {a: rng.choice(vs) for a, vs in cfg.domains.items()} for s in suspects}
    for s in suspects:
        world[s][attr] = one if s == culprit else zero
    clues = [
        dict(type="crime_positive", attribute=attr, value=one),
        dict(type="unary_positive", suspect=innocents[0], attribute=attr, value=zero),
    ]
    return suspects, world, culprit, clues, innocents, attr


def build_core(config, seed):
    cfg = Config(**config.puzzle.config)
    family = config.puzzle.family
    rng = random.Random(seed)
    if family == "redundant_paths":
        suspects = [f"S{i + 1:02d}" for i in range(cfg.suspect_count)]
        culprit = rng.choice(suspects)
        world = {s: {} for s in suspects}
        clues = []
        attributes = list(cfg.domains)
        available = {
            a: rng.sample(vs, cfg.active_values_per_attribute or len(vs))
            for a, vs in cfg.domains.items()
        }
        for attr in attributes:
            world[culprit][attr] = rng.choice(available[attr])
        for s in suspects:
            if s == culprit:
                continue
            different = set(
                rng.sample(
                    attributes, config.puzzle.attribute_mismatches or len(attributes)
                )
            )
            for attr in attributes:
                world[s][attr] = (
                    rng.choice(
                        [v for v in available[attr] if v != world[culprit][attr]]
                    )
                    if attr in different
                    else world[culprit][attr]
                )
        for attr in attributes:
            culprit_value = world[culprit][attr]
            groups = {}
            for s in suspects:
                groups.setdefault(world[s][attr], []).append(s)
            clues.append(
                dict(type="crime_positive", attribute=attr, value=culprit_value)
            )
            for value, members in groups.items():
                rng.shuffle(members)
                clues.append(
                    dict(
                        type="unary_positive",
                        suspect=members[0],
                        attribute=attr,
                        value=value,
                    )
                )
                clues += [
                    dict(
                        type="suspect_same_as",
                        suspect=right,
                        other_suspect=left,
                        attribute=attr,
                    )
                    for left, right in zip(members, members[1:])
                ]
    elif family in ("equality_tree", "branching"):
        suspects, world, culprit, clues, innocents, attr = _constructed(cfg, seed)
        for i, s in enumerate(innocents[1:], 1):
            parent = (
                innocents[(i - 1) // 2] if family == "branching" else innocents[i - 1]
            )
            clues.append(
                dict(
                    type="suspect_same_as",
                    suspect=s,
                    other_suspect=parent,
                    attribute=attr,
                )
            )
        builder = ClueGenerator(world, culprit, cfg.domains)
        builder.build_clue_pool(rng)
        existing = {fact_key(c) for c in clues}
        pool = [
            c
            for c in builder.clue_pool
            if c["type"] in cfg.enabled_types and fact_key(c) not in existing
        ]
        if config.puzzle.extra_clue_scope == "non_target_attributes":
            pool = [
                c
                for c in pool
                if not c["type"].startswith("crime_")
                and attr not in (c.get("attribute"), c.get("attr1"), c.get("attr2"))
            ]
        if len(pool) < cfg.clue_count - len(clues):
            raise ValueError("insufficient pool for exact constructed clue count")
        clues += rng.sample(pool, cfg.clue_count - len(clues))
    else:
        if family != "standard":
            cfg = replace(cfg, reasoning_route=family)
        fixed = None
        if config.puzzle.assignment_mode == "distinct":
            suspects = [f"S{i + 1:02d}" for i in range(cfg.suspect_count)]
            world = {s: {} for s in suspects}
            for a, vs in cfg.domains.items():
                values = rng.sample(vs, cfg.suspect_count)
                for s, v in zip(suspects, values):
                    world[s][a] = v
            fixed = (world, rng.choice(suspects))
        result = generate(cfg, seed, fixed_world=fixed)
        if result["status"] != "ok":
            raise ValueError(
                "core_generation_failed:" + str(result["diagnostics"]["rejections"])
            )
        base = result["case"]
        suspects, world, culprit, clues = (
            base["suspects"],
            base["solution"]["world"],
            base["solution"]["murderer"],
            base["clues"],
        )
    # All old count/essentialness controls also apply to constructed routes.
    if len(clues) != cfg.clue_count:
        raise ValueError("core clue count mismatch")
    links = sum(is_link(c) for c in clues)
    if (
        links < cfg.min_murderer_links
        or (cfg.max_murderer_links is not None and links > cfg.max_murderer_links)
        or (
            cfg.max_positive_murderer_links is not None
            and sum(c["type"] == "crime_positive" for c in clues)
            > cfg.max_positive_murderer_links
        )
        or sum(is_indirect(c) for c in clues) < cfg.min_indirect_clues
        or sum(c["type"].startswith("suspect_") for c in clues) < cfg.min_pairwise_clues
    ):
        raise ValueError("constructed family cannot satisfy requested legacy quotas")
    return {
        "suspects": suspects,
        "domains": cfg.domains,
        "solution": {"murderer": culprit, "world": world},
        "assignment_mode": config.puzzle.assignment_mode,
        "corruption_allowance": 0,
        "false_report_count": 0,
        "reports": [_report(c) for c in clues],
        "motif_family": family,
        "agent_count": config.distribution.agent_count,
    }


def _entailed(case, count, config, rng, budget, relational_only=False):
    if not count:
        return []
    builder = ClueGenerator(
        case["solution"]["world"], case["solution"]["murderer"], case["domains"]
    )
    builder.build_clue_pool(rng)
    existing = {r["report_id"] for r in case["reports"]}
    seen_facts = {fact_key(r["constraint"]) for r in case["reports"]}
    extras = []
    for c in builder.clue_pool:
        budget.check()
        if c["type"] not in config.puzzle.config["enabled_types"]:
            continue
        if relational_only and c["type"] not in (
            "suspect_same_as",
            "suspect_different_from",
        ):
            continue
        if relational_only and fact_key(c) in seen_facts:
            continue
        r = _report(c)
        if r["report_id"] in existing:
            continue
        negation = deepcopy(c)
        pairs = {
            "unary_positive": "unary_negative",
            "crime_positive": "crime_negative",
            "crime_same_as": "crime_different_from",
            "suspect_same_as": "suspect_different_from",
            "indirect_positive": "indirect_negative",
        }
        inverse = pairs | {v: k for k, v in pairs.items()}
        negation["type"] = inverse[c["type"]]
        # Truthful core plus negation being infeasible proves the added fact.
        trial = case["reports"] + [_report(negation)]
        if evaluate(case, trial, budget)["candidates"] == []:
            extras.append(r)
            existing.add(r["report_id"])
            seen_facts.add(fact_key(c))
            if len(extras) == count:
                return extras
    raise ValueError("insufficient distinct core-entailed clues")


def _targeted_corruption(case, config, rng, budget):
    """Bounded search minimizes distance to a wrong explanation, not model score."""
    best = None
    for attempt in range(config.evidence.corruption_search_attempts):
        budget.check()
        trial = deepcopy(case)
        changes = _corrupt(
            trial,
            config.evidence.false_reports,
            rng,
            config.puzzle.config["enabled_types"],
        )
        trial["false_report_count"] = config.evidence.false_reports
        trial["corruption_allowance"] = config.evidence.corruption_allowance
        profile = reliability_profile(trial, budget)
        allowed = [
            r["culprit"]
            for r in profile["candidates"]
            if r["minimum_violations"] <= trial["corruption_allowance"]
        ]
        if allowed != [case["solution"]["murderer"]]:
            continue
        key = (
            profile["nearest_alternative_violations"],
            digest(sorted(trial["reports"], key=lambda r: r["report_id"])),
        )
        if best is None or key < best[0]:
            best = (key, trial["reports"], changes, profile, attempt)
    if best is None:
        raise ValueError("targeted corruption search found no unique instance")
    case["reports"] = best[1]
    return (
        best[2],
        best[3],
        {
            "attempts": config.evidence.corruption_search_attempts,
            "selected_attempt": best[4],
            "objective": "minimum_wrong_culprit_violations",
        },
    )


def _corrupt(case, count, rng, enabled):
    if not count:
        return []
    inverse = {
        "unary_positive": "unary_negative",
        "crime_positive": "crime_negative",
        "crime_same_as": "crime_different_from",
        "suspect_same_as": "suspect_different_from",
        "indirect_positive": "indirect_negative",
    }
    inverse |= {v: k for k, v in inverse.items()}
    slots = list(range(len(case["reports"])))
    rng.shuffle(slots)
    changes = []
    existing = {r["report_id"] for r in case["reports"]}
    for index in slots:
        old = case["reports"][index]
        original = old["constraint"]
        c = deepcopy(original)
        c["type"] = inverse[c["type"]]
        proposals = [c] if c["type"] in enabled else []
        if "value" in original:
            proposals += [
                {**original, "value": v}
                for v in case["domains"][original["attribute"]]
                if v != original["value"]
            ]
        rng.shuffle(proposals)
        candidates = [
            p
            for p in proposals
            if _report(p)["report_id"] not in existing
            and not holds(p, case["solution"]["world"], case["solution"]["murderer"])
        ]
        if not candidates:
            continue
        c = candidates[0]
        r = _report(c)
        assert not holds(c, case["solution"]["world"], case["solution"]["murderer"])
        changes.append(
            {"original_report_id": old["report_id"], "false_report_id": r["report_id"]}
        )
        case["reports"][index] = r
        existing.remove(old["report_id"])
        existing.add(r["report_id"])
        if len(changes) == count:
            return changes
    raise ValueError("unavailable nonduplicate corruption using enabled clue types")


def _take_owners(remaining, records_left, replication, rng=None):
    if (
        sum(remaining) != records_left * replication
        or max(remaining, default=0) > records_left
        or min(remaining, default=0) < 0
    ):
        raise ValueError("infeasible allocation quotas")
    mandatory = [i for i, q in enumerate(remaining) if q == records_left and q > 0]
    others = [i for i, q in enumerate(remaining) if q > 0 and i not in mandatory]
    if rng is None:
        others.sort(key=lambda i: (-remaining[i], i))
    else:
        rng.shuffle(others)
    owners = mandatory + others[: replication - len(mandatory)]
    if len(mandatory) > replication or len(owners) != replication:
        raise ValueError("infeasible allocation quotas")
    for i in owners:
        remaining[i] -= 1
    return sorted(owners)


def partition(case, config, seed, budget=None):
    budget = budget or Budget(
        config.dataset.certification_seconds, config.dataset.max_solver_calls
    )
    dc = config.distribution
    n, core_count = dc.agent_count, len(case["reports"])
    noise = config.evidence.irrelevant_records
    total = core_count + noise
    shared_noise = min(noise, dc.shared_reports)
    shared_core = dc.shared_reports - shared_noise
    if shared_core > core_count:
        raise ValueError("shared report count exceeds final bank")
    private_total = total - dc.shared_reports
    incidences = dc.shared_reports * n + private_total * dc.private_replication
    quotas = dc.per_agent_quotas
    if quotas is None:
        quotas = [incidences // n + int(i < incidences % n) for i in range(n)]
    if sum(quotas) != incidences or any(
        q < dc.shared_reports or q > total for q in quotas
    ):
        raise ValueError("infeasible per-agent quotas")
    rng = random.Random(seed)
    for _ in range(dc.max_attempts):
        budget.check()
        shared_ids = set(
            r["report_id"] for r in rng.sample(case["reports"], shared_core)
        )
        remaining = [q - dc.shared_reports for q in quotas]
        records_left = private_total
        order = list(case["reports"])
        rng.shuffle(order)
        allocation = {}
        for r in order:
            rid = r["report_id"]
            if rid in shared_ids:
                allocation[rid] = list(range(n))
            else:
                allocation[rid] = _take_owners(
                    remaining, records_left, dc.private_replication, rng
                )
                records_left -= 1
        cert = coalition_certificate(case, allocation, budget)
        if cert["minimum_size"] != dc.minimum_coalition_size:
            continue
        nuisance_recipe = {
            "count": noise,
            "shared_prefix": shared_noise,
            "remaining_quotas": remaining,
            "private_replication": dc.private_replication,
            "agent_count": n,
        }
        body = {
            "core_allocation": allocation,
            "nuisance_recipe": nuisance_recipe,
            "per_agent_quotas": quotas,
            "shared_reports": dc.shared_reports,
            "total_reports": total,
            "shared_fraction": dc.shared_reports / total,
            "private_fraction": private_total / total,
            "private_replication": dc.private_replication,
        }
        overlaps = [[0] * n for _ in range(n)]

        def observe(owners):
            for left in owners:
                for right in owners:
                    overlaps[left][right] += 1

        for owners in allocation.values():
            observe(owners)
        rest = list(remaining)
        left = noise - shared_noise
        for index in range(noise):
            if index < shared_noise:
                owners = list(range(n))
            else:
                owners = _take_owners(rest, left, dc.private_replication)
                left -= 1
            observe(owners)
        body["realized_overlap"] = overlaps
        return {**body, "partition_id": digest(body), "certificate": cert}
    raise ValueError("partition search exhausted without requested coalition size")


def iter_nuisance(case):
    for index in range(case["nuisance_count"]):
        c = {
            "type": "record_positive",
            "component": digest([case["world_id"], "component", index]),
            "variable": "value",
            "value": str(index % 2),
            "domain": ["0", "1"],
        }
        yield {"report_id": digest(c), "constraint": c}


def merge_evidence(core, nuisance, count, placement="front"):
    """Place a bounded core inside an arbitrarily long, ordered nuisance stream."""
    core = list(core)
    nuisance = iter(nuisance)
    consumed = 0
    for index, report in enumerate(core):
        stop = {
            "front": 0,
            "middle": count // 2,
            "end": count,
            "interleaved": (index + 1) * count // (len(core) + 1),
        }[placement]
        while consumed < stop:
            yield next(nuisance)
            consumed += 1
        yield report
    yield from nuisance


def iter_reports(case):
    yield from merge_evidence(
        case["reports"],
        iter_nuisance(case),
        case["nuisance_count"],
        case.get("evidence_placement", "front"),
    )


def iter_nuisance_allocations(case, partition_data):
    recipe = partition_data["nuisance_recipe"]
    remaining = list(recipe["remaining_quotas"])
    records_left = recipe["count"] - recipe["shared_prefix"]
    for i, r in enumerate(iter_nuisance(case)):
        if i < recipe["shared_prefix"]:
            owners = list(range(recipe["agent_count"]))
        else:
            owners = _take_owners(
                remaining, records_left, recipe["private_replication"]
            )
            records_left -= 1
        yield r["report_id"], owners
    if any(remaining):
        raise ValueError("nuisance quota recipe did not settle")


def iter_allocations(case, partition_data):
    core = [
        (r["report_id"], partition_data["core_allocation"][r["report_id"]])
        for r in case["reports"]
    ]
    yield from merge_evidence(
        core,
        iter_nuisance_allocations(case, partition_data),
        case["nuisance_count"],
        case.get("evidence_placement", "front"),
    )


def render_report(report, case, presentation):
    c = report["constraint"]
    if c["type"] == "record_positive":
        text = f'Record {c["component"]}: its independent value equals "{c["value"]}".'
    else:
        # Translate suspect fields before formatting. Literal domain/attribute
        # strings may themselves equal an internal ID and must remain untouched.
        displayed = dict(c)
        for key in ("suspect", "other_suspect"):
            if key in displayed:
                displayed[key] = case["display_names"][displayed[key]]
        text = ClueFormatter.format(displayed)
        if presentation.theme == "investigation":
            text = (
                text.replace("The murderer", "The responsible entity")
                .replace("suspect", "entity")
                .replace("Suspect", "Entity")
            )
    if presentation.template == "expanded":
        text = "The following statement is part of the investigation record. " + text
    return {**report, "text": text}


def render_case(case, config, tokenizer=None):
    p = config.presentation
    if p.evidence_placement != "front":
        case["evidence_placement"] = p.evidence_placement
    labels = list(range(1, len(case["suspects"]) + 1))
    random.Random(p.naming_seed).shuffle(labels)
    case["display_names"] = {
        s: f"{'Person' if p.theme == 'mystery' else 'Entity'} {i}"
        for s, i in zip(case["suspects"], labels)
    }
    if p.clue_order == "shuffle":
        random.Random(int(digest([case["seed"], "order"]), 16)).shuffle(case["reports"])
    else:
        case["reports"].sort(
            key=lambda r: r["report_id"], reverse=p.clue_order == "reverse"
        )
    case["padding"] = ""
    texts = [render_report(r, case, p)["text"] for r in case["reports"]]
    word_count = sum(len(t.split()) for t in texts)
    # Nuisance text has fixed tokenization-independent word length.
    if case["nuisance_count"]:
        first = next(iter_nuisance(case))
        word_count += case["nuisance_count"] * len(
            render_report(first, case, p)["text"].split()
        )
    if p.minimum_words is not None and word_count < p.minimum_words:
        words = [
            "Archive",
            "context",
            "contains",
            "no",
            "additional",
            "factual",
            "claims",
        ]
        missing = p.minimum_words - word_count
        case["padding"] = " ".join(words[i % len(words)] for i in range(missing))
        word_count += missing
    if p.maximum_words is not None and word_count > p.maximum_words:
        raise ValueError("word bound cannot contain requested evidence")
    token_count = None
    if tokenizer is not None:
        # Count the actual serialized presentation as one string, including BPE
        # boundary effects. This is optional and explicitly not a chat-token count.
        text = "\n".join(
            [render_report(r, case, p)["text"] for r in iter_reports(case)]
            + [case["padding"]]
        )
        token_count = len(tokenizer(text))
    if any(v is not None for v in (p.minimum_tokens, p.maximum_tokens)):
        if tokenizer is None:
            raise ValueError("token bounds require a supplied tokenizer")
        if (
            p.minimum_tokens is not None
            and token_count < p.minimum_tokens
            or p.maximum_tokens is not None
            and token_count > p.maximum_tokens
        ):
            raise ValueError("presentation does not satisfy token bounds")
    case["presentation_metrics"] = {
        "words": word_count,
        "tokens": token_count,
        "token_scope": "joined report text plus padding",
    }
    case["presentation_id"] = digest(
        [
            case["case_id"],
            config.presentation.__dict__,
            case["display_names"],
            [r["report_id"] for r in case["reports"]],
            case["padding"],
        ]
    )
    return case


def generate_case(config, seed, tokenizer=None):
    """One candidate, explicit failure; dataset generation owns bounded retries."""
    try:
        budget = Budget(
            config.dataset.certification_seconds, config.dataset.max_solver_calls
        )
        construction_started = time.monotonic()
        case = build_core(config, seed)
        construction_seconds = time.monotonic() - construction_started
        core_cert = certify(case, budget)
        if core_cert["status"] != "verified_unique":
            raise ValueError("core not uniquely solvable")
        cfg = Config(**config.puzzle.config)
        if cfg.require_indirect_essential and not any(
            is_indirect(r["constraint"])
            and evaluate(case, case["reports"][:i] + case["reports"][i + 1 :], budget)[
                "candidates"
            ]
            != [case["solution"]["murderer"]]
            for i, r in enumerate(case["reports"])
        ):
            raise ValueError("essential indirect clue requirement not satisfied")
        rng = random.Random(seed)
        case["reports"] += _entailed(
            case, config.evidence.entailed_clues, config, rng, budget
        )
        decoy_basis = list(case["reports"])
        decoys = _entailed(
            case,
            config.evidence.connected_decoys,
            config,
            rng,
            budget,
            relational_only=True,
        )
        case["reports"] += decoys
        profile, search = None, None
        if (
            config.evidence.corruption_strategy == "targeted"
            and config.evidence.false_reports
        ):
            changes, profile, search = _targeted_corruption(case, config, rng, budget)
        else:
            changes = _corrupt(
                case, config.evidence.false_reports, rng, cfg.enabled_types
            )
        case["false_report_count"] = config.evidence.false_reports
        case["corruption_allowance"] = config.evidence.corruption_allowance
        case["nuisance_count"] = config.evidence.irrelevant_records
        case["seed"] = seed
        case["world_id"] = digest(
            [case["solution"], case["domains"], case["assignment_mode"]]
        )
        case["case_id"] = digest(
            [
                case["world_id"],
                sorted(case["reports"], key=lambda r: r["report_id"]),
                case["corruption_allowance"],
                case["nuisance_count"],
            ]
        )
        final = certify(case, budget)
        desired = "verified_" + config.evidence.answerability
        if final["status"] != desired:
            raise ValueError("final_answerability_mismatch")
        if (
            config.puzzle.family == "redundant_paths"
            or config.evidence.maximum_alternative_margin is not None
        ):
            profile = profile or reliability_profile(case, budget)
        if config.evidence.maximum_alternative_margin is not None and (
            profile["alternative_margin"] > config.evidence.maximum_alternative_margin
        ):
            raise ValueError("alternative_margin_requirement_unmet")
        subset_budget = Budget(
            max(0.001, (budget.deadline - time.monotonic()) * 0.4),
            max(1, budget.max_calls - budget.calls),
        )
        try:
            if (
                config.puzzle.family in ("equality_tree", "branching")
                and (
                    len(case["reports"]) == cfg.suspect_count
                    or config.evidence.minimum_sufficient_clues == cfg.suspect_count
                )
                and not case["corruption_allowance"]
            ) or config.evidence.minimum_sufficient_clues == len(case["reports"]):
                selected = (
                    case["reports"][: cfg.suspect_count]
                    if config.puzzle.family in ("equality_tree", "branching")
                    and not case["corruption_allowance"]
                    else case["reports"]
                )
                cost = essential_subset(case, subset_budget, selected)
            else:
                cost = minimum_subset(case, subset_budget)
        finally:
            budget.calls += subset_budget.calls
            budget.solve_seconds += subset_budget.solve_seconds
        cost["report_order"] = [r["report_id"] for r in case["reports"]]
        lo = config.evidence.minimum_sufficient_clues
        if lo is None:
            lo = (
                cfg.min_unique_subset_size
                if config.evidence.answerability == "unique"
                else None
            )
        hi = config.evidence.maximum_sufficient_clues
        if (
            lo is not None and (cost["lower_bound"] is None or cost["lower_bound"] < lo)
        ) or (
            hi is not None and (cost["upper_bound"] is None or cost["upper_bound"] > hi)
        ):
            raise ValueError("sufficient_clue_requirement_unproved")
        part = partition(case, config, seed, budget)
        case = render_case(case, config, tokenizer)
        final["case_hash"] = digest(case)
        return {
            "status": "ok",
            "case": case,
            "partition": part,
            "certificate": {
                **final,
                "minimum_subset": cost,
                "coalition": part["certificate"],
                "core_certificate": core_cert,
                "corruptions": changes,
                **({"reliability_profile": profile} if profile else {}),
                **({"corruption_search": search} if search else {}),
                **(
                    {
                        "connected_decoys": {
                            "truthful_basis": decoy_basis,
                            "reports": decoys,
                        }
                    }
                    if decoys
                    else {}
                ),
            },
            "diagnostics": {
                "solver_calls": budget.calls,
                "certification_solver_seconds": budget.solve_seconds,
                "core_construction_seconds": construction_seconds,
            },
        }
    except (ValueError, Unresolved) as exc:
        return {
            "status": "unknown" if isinstance(exc, Unresolved) else "rejected",
            "case": None,
            "diagnostics": {"reason": str(exc)},
        }


def public_case(case):
    return {
        "case_id": case["case_id"],
        "world_id": case["world_id"],
        "presentation_id": case["presentation_id"],
        "split": case["split"],
        "suspects": case["suspects"],
        "domains": case["domains"],
        "display_names": case["display_names"],
        "assignment_mode": case["assignment_mode"],
        "agent_count": case["agent_count"],
        "corruption_allowance": case["corruption_allowance"],
        "padding": case["padding"],
        "rules": "Choose one responsible suspect. Crime attributes equal that suspect's attributes. "
        "All statements are report constraints; at most the published allowance of distinct reports may be false. "
        "Independent record components share no variables with the suspects. Attribute assignments obey assignment_mode.",
        "total_reports": len(case["reports"]) + case["nuisance_count"],
    }


def score(case, response, evidence, budget=None):
    state = evaluate(case, evidence, budget)
    target = response.get("target") if isinstance(response, dict) else None
    abstain = isinstance(response, dict) and response == {"kind": "abstain"}
    valid = abstain or (
        isinstance(response, dict)
        and set(response) == {"kind", "target"}
        and response["kind"] == "answer"
        and target in case["suspects"]
    )
    return {
        "correct": valid and not abstain and target == case["solution"]["murderer"],
        "supported": valid and not abstain and state["candidates"] == [target],
        "abstained": abstain,
        "protocol_valid": valid,
        "ambiguous_evidence": len(state["candidates"]) > 1,
        "possible_culprits": state["candidates"],
        "sufficient_evidence": state["candidates"] == [case["solution"]["murderer"]],
    }
