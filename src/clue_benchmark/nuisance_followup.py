"""Offline, preregistered nuisance-dose preparation. Never opens credentials."""

import random
from pathlib import Path

from .community_bundle import (
    _screen,
    export_dataset,
    file_hash,
    load_evaluator_cases,
    rows,
    source_hashes,
    validate_dataset,
)
from .community_config import CommunityConfig
from .community_evaluation import _observations, prepare_evaluation, run_evaluation
from .community_generation import generate_case, iter_nuisance, render_report
from .config import canonical, digest
from .dataset import atomic_json
from .native_adapters import request_payload

CAP = 10_000_000
PROBES = 500_000
MODELS = ("gemini-3.5-flash-lite", "gemini-3.8-flash")


def select_cohort(blocks):
    """Largest balanced seed prefix fitting every maximum, before outcomes."""
    for count in (12, 10, 8, 6):
        chosen = blocks[:count]
        if len(chosen) == count and all(b["context_fits"] for b in chosen):
            maximum = sum(b["maximum_microdollars"] for b in chosen)
            if maximum <= CAP - PROBES:
                return chosen
    return []


def matched(results, configs):
    base = results[0]
    for result, config in zip(results, configs, strict=True):
        if result["status"] != "ok":
            raise ValueError("unaccepted matched candidate")
        case = result["case"]
        for key in ("world_id", "solution", "reports", "domains", "display_names"):
            if case[key] != base["case"][key]:
                raise ValueError("dose changed " + key)
        for bound in ("lower_bound", "upper_bound"):
            if (
                result["certificate"]["minimum_subset"][bound]
                != base["certificate"]["minimum_subset"][bound]
            ):
                raise ValueError("dose changed evidence bounds")
        rendered = [
            render_report(r, case, config.presentation) for r in case["reports"]
        ]
        if rendered != [
            render_report(r, base["case"], configs[0].presentation)
            for r in base["case"]["reports"]
        ]:
            raise ValueError("dose changed core text")
        for nuisance in iter_nuisance(case):
            c = nuisance["constraint"]
            if c["type"] != "record_positive" or c["value"] not in c["domain"]:
                raise ValueError("invalid independent nuisance component")
    if (
        list(iter_nuisance(results[1]["case"]))
        != list(iter_nuisance(results[2]["case"]))[:100]
    ):
        raise ValueError("nuisance prefix changed")


def prepare_followup(output, models, prior_banks=(), attempts_per_stratum=180):
    """Freeze exact native payloads, maximum reservations and rejection receipts.

    Output must be new. Model prices must be reviewed against the dated official
    source before use; account access and native probes remain a separate gate.
    No paid runner is exposed here: child plans are preparation assets only.
    """
    if [m["model"] for m in models] != list(MODELS):
        raise ValueError("exact motivating model profiles required, in declared order")
    for model in models:
        if model["vendor"] != "google" or model["settings"] != {
            "max_output_tokens": 4096,
            "temperature": 0,
            "thinking_level": "low",
        }:
            raise ValueError(
                "follow-up requires low thinking, temperature zero, 4096 tokens"
            )
    models = [{**m, "identity": m["model"]} for m in models]
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    seen = set()
    prior = {}
    for bank in prior_banks:
        # Stream core-only fingerprints. Some historical manifests contain GBs
        # of per-report diagnostics; screening never needs to load those arrays.
        directory = Path(bank)
        prior[str(bank)] = {
            name: file_hash(directory / name)
            for name in ("cases.jsonl", "answers.jsonl")
        }
        answers = {
            row["case_id"]: row["solution"] for row in rows(directory / "answers.jsonl")
        }
        current = None
        for row in rows(directory / "cases.jsonl"):
            if row["kind"] == "case":
                if current is not None:
                    seen.update(_screen(current))
                current = {**row, "solution": answers[row["case_id"]], "reports": []}
            elif row["constraint"]["type"] != "record_positive":
                current["reports"].append(row)
        if current is not None:
            seen.update(_screen(current))
    blocks, rejections = [], []
    pools = {4: [], 8: []}
    for burden in (4, 8):
        for seed in range(20261027, 20261027 + attempts_per_stratum):
            configs, results = [], []
            for dose in (0, 100, 1000):
                cfg = CommunityConfig.from_dict(
                    {
                        "puzzle": {
                            "family": "branching",
                            "config": {
                                "suspect_count": burden,
                                "clue_count": burden + 4,
                            },
                        },
                        "evidence": {
                            "minimum_sufficient_clues": burden,
                            "maximum_sufficient_clues": burden,
                            "irrelevant_records": dose,
                            "corruption_allowance": 0,
                        },
                        "distribution": {"agent_count": 1, "minimum_coalition_size": 1},
                        "presentation": {"evidence_placement": "front"},
                        "dataset": {"count": 1, "seed": seed},
                    }
                )
                configs.append(cfg)
                results.append(generate_case(cfg, seed))
            failures = [
                r["diagnostics"].get("reason") for r in results if r["status"] != "ok"
            ]
            if failures:
                rejections.append({"burden": burden, "seed": seed, "reasons": failures})
                continue
            matched(results, configs)
            fingerprints = set(_screen(results[0]["case"]))
            if fingerprints & seen:
                rejections.append(
                    {
                        "burden": burden,
                        "seed": seed,
                        "reasons": ["structural_duplicate"],
                    }
                )
                continue
            seen.update(fingerprints)
            jobs, maximum, fits = [], 0, True
            for dose, cfg, result in zip((0, 100, 1000), configs, results, strict=True):
                name = f"burden-{burden}-seed-{seed}-dose-{dose}"
                directory = root / name
                directory.mkdir()
                receipt = directory / "candidate.json"
                atomic_json(receipt, result)
                manifest = export_dataset(cfg, [receipt], directory)
                manifest["complete"] = True
                atomic_json(directory / "manifest.json", manifest)
                validate_dataset(directory)
                plan = prepare_evaluation(
                    directory,
                    models,
                    conditions=["complete"],
                    repeats=2,
                    spending_ceiling_microdollars=0,
                )
                dry = run_evaluation(
                    plan, directory, directory / "unused", dry_run=True
                )
                held = sum(r["maximum_microdollars"] for r in dry["requests"])
                fits &= all(r["context_fits"] for r in dry["requests"])
                maximum += held
                plan["spending_ceiling_microdollars"] = held
                plan["max_requests"] = len(dry["requests"])
                plan["plan_id"] = digest(
                    {k: v for k, v in plan.items() if k != "plan_id"}
                )
                atomic_json(directory / "plan.json", plan)
                payloads = []
                for case in load_evaluator_cases(directory):
                    for _, obs, _, _, _ in _observations(case, plan, "complete"):
                        for repeat in range(2):
                            for model in models:
                                payload = request_payload(
                                    model["vendor"],
                                    model["model"],
                                    obs,
                                    "answering",
                                    model["settings"],
                                )
                                payloads.append(
                                    {
                                        "repeat": repeat,
                                        "model": model["id"],
                                        "observation_hash": digest(obs),
                                        "payload_hash": digest(payload),
                                        "payload": payload,
                                    }
                                )
                (directory / "payloads.jsonl").write_text(
                    "".join(canonical(p) + "\n" for p in payloads)
                )
                jobs.append(
                    {
                        "directory": name,
                        "plan_id": plan["plan_id"],
                        "ceiling_microdollars": held,
                        "payloads_sha256": file_hash(directory / "payloads.jsonl"),
                    }
                )
            pools[burden].append(
                {
                    "world_id": results[0]["case"]["world_id"],
                    "seed": seed,
                    "burden": burden,
                    "jobs": jobs,
                    "maximum_microdollars": maximum,
                    "context_fits": fits,
                }
            )
            if len(pools[burden]) == 6:
                break
    for pair in zip(pools[4], pools[8]):
        blocks.extend(pair)
    chosen = select_cohort(blocks)
    order = list(chosen)
    rng = random.Random(0)
    rng.shuffle(order)
    for block in order:
        rng.shuffle(block["jobs"])
    report = {
        "study_id": "nuisance-followup-20261027",
        "status": "prepared_pending_access_and_authorization"
        if chosen
        else "unaffordable_or_incomplete",
        "sources": source_hashes(),
        "prior_banks": prior,
        "rejections": rejections,
        "candidate_blocks": blocks,
        "selected_blocks": order,
        "independent_worlds": len(chosen),
        "assigned_calls": len(chosen) * 12,
        "primary_endpoint": "four-report Lite: mean within-world two-attempt accuracy at 1000 minus 0 nuisance records",
        "secondary_endpoints": [
            "100 minus 0",
            "eight-report stratum",
            "Flash dose contrasts",
            "paired between-model difference",
        ],
        "study_cap_microdollars": CAP,
        "probe_reserve_microdollars": PROBES,
        "scored_maximum_microdollars": sum(b["maximum_microdollars"] for b in chosen),
        "settled_microdollars": 0,
        "unresolved_holds_microdollars": 0,
        "paid_calls": 0,
        "execution_gate": "Account access, exact identity and compatibility probes; human manifest-bound authorization. Preparation is not a permit. Child plans must not be launched independently.",
    }
    if chosen:
        probe_directory = root / chosen[0]["jobs"][0]["directory"]
        probe_plan = prepare_evaluation(
            probe_directory,
            models,
            conditions=["complete"],
            repeats=1,
            spending_ceiling_microdollars=PROBES,
            max_requests=2,
        )
        atomic_json(probe_directory / "probe-plan.json", probe_plan)
        report["probe_job"] = {
            "directory": str(probe_directory.relative_to(root)),
            "plan_file": "probe-plan.json",
            "plan_id": probe_plan["plan_id"],
            "ceiling_microdollars": PROBES,
        }
    report["manifest_id"] = digest(report)
    atomic_json(root / "study.json", report)
    return report
