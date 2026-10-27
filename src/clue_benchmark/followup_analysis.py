"""Assigned-denominator, world-paired follow-up analysis; no provider imports."""

import itertools
import json
import random
from collections import defaultdict
from pathlib import Path

from .community_evaluation import run_evaluation
from .config import canonical
from .dataset import atomic_json
from .followup_runner import checked_jobs


def paired_contrast(left, right):
    if set(left) != set(right) or not left:
        raise ValueError("paired contrasts require the same nonempty world IDs")
    differences = [right[w] - left[w] for w in sorted(left)]
    n = len(differences)
    if n > 12:
        raise ValueError("exact analysis limited to this preregistered small study")
    mean = sum(differences) / n
    rng = random.Random(0)
    bootstrap = sorted(
        sum(rng.choice(differences) for _ in differences) / n for _ in range(2000)
    )
    exact = sum(
        abs(sum(sign * d for sign, d in zip(signs, differences, strict=True)) / n)
        >= abs(mean) - 1e-12
        for signs in itertools.product((-1, 1), repeat=n)
    ) / (2**n)
    return {
        "worlds": n,
        "per_world_changes": dict(zip(sorted(left), differences, strict=True)),
        "mean_change": mean,
        "world_cluster_bootstrap_95_interval": [bootstrap[49], bootstrap[1949]],
        "exact_two_sided_p": exact,
        "randomization_resolution": 1 / 2**n,
        "gained_worlds": sum(d > 0 for d in differences),
        "lost_worlds": sum(d < 0 for d in differences),
        "interpretation": "Descriptive small-world analysis, not a powered confirmatory test or mechanism identification.",
    }


def analyze_followup(root, output):
    root, output = Path(root), Path(output)
    study = json.loads((root / "study.json").read_text())
    plans = checked_jobs(root, study)
    block_by_job = {
        job["directory"]: block
        for block in study["selected_blocks"]
        for job in block["jobs"]
    }
    slots, accounting = [], {"settled_microdollars": 0, "held_microdollars": 0}
    for index, (job, plan) in enumerate(plans):
        saved = (
            root
            / "execution"
            / ("probe" if index == 0 else job["directory"])
            / "results.json"
        )
        observed = {}
        if saved.exists():
            report = json.loads(saved.read_text())
            if report["plan_id"] != plan["plan_id"]:
                raise ValueError("saved report belongs to another plan")
            for key in accounting:
                accounting[key] += report["accounting"][key]
            observed = {r["request_id"]: r for r in report["episodes"]}
        if index == 0:
            continue
        draft = run_evaluation(
            plan, root / job["directory"], root / "unused", dry_run=True
        )
        for assignment in draft["requests"]:
            result = observed.get(assignment["request_id"])
            dose = int(job["directory"].rsplit("-dose-", 1)[1])
            slots.append(
                {
                    **assignment,
                    **(result or {}),
                    "burden": block_by_job[job["directory"]]["burden"],
                    "dose": dose,
                    "assignment_status": "observed"
                    if result
                    and result.get(
                        "dispatched",
                        result.get("transport") != "not_attempted_administrative",
                    )
                    else "never_dispatched",
                }
            )
    complete = bool(slots) and all(s["assignment_status"] == "observed" for s in slots)
    summaries, contrasts = [], []
    groups = defaultdict(list)
    for slot in slots:
        groups[slot["burden"], slot["model"], slot["dose"]].append(slot)
    means = {}
    for (burden, model, dose), records in sorted(groups.items()):
        worlds = defaultdict(list)
        for row in records:
            worlds[row["world_id"]].append(row)
        means[burden, model, dose] = {
            world: sum(bool(r.get("supported")) for r in rs) / len(rs)
            for world, rs in worlds.items()
        }
        returned = [r for r in records if r.get("transport") == "ok"]
        summaries.append(
            {
                "burden": burden,
                "model": model,
                "dose": dose,
                "assigned": len(records),
                "worlds": len(worlds),
                "observed": sum(r["assignment_status"] == "observed" for r in records),
                "supported_correct": sum(bool(r.get("supported")) for r in records)
                if complete
                else None,
                "assigned_accuracy": sum(bool(r.get("supported")) for r in records)
                / len(records)
                if complete
                else None,
                "returned_only_accuracy": sum(
                    bool(r.get("supported")) for r in returned
                )
                / len(returned)
                if returned
                else None,
                "returned_denominator": len(returned),
                "attempt_disagreement_worlds": sum(
                    len({canonical(r.get("answer")) for r in rs}) > 1
                    for rs in worlds.values()
                )
                if complete
                else None,
            }
        )
    if complete:
        for burden, model in sorted({(b, m) for b, m, _ in means}):
            for dose in (100, 1000):
                contrasts.append(
                    {
                        "burden": burden,
                        "model": model,
                        "dose_minus_zero": dose,
                        "primary": burden == 4
                        and "flash-lite" in model
                        and dose == 1000,
                        **paired_contrast(
                            means[burden, model, 0], means[burden, model, dose]
                        ),
                    }
                )
        for burden in (4, 8):
            models = sorted({m for b, m, _ in means if b == burden})
            lite = next(m for m in models if "flash-lite" in m)
            flash = next(m for m in models if "flash-lite" not in m)
            for dose in (100, 1000):
                effects = {}
                for model in (lite, flash):
                    effects[model] = {
                        world: value - means[burden, model, 0][world]
                        for world, value in means[burden, model, dose].items()
                    }
                contrasts.append(
                    {
                        "burden": burden,
                        "between_models": "Flash minus Lite noise effect",
                        "dose_minus_zero": dose,
                        "primary": False,
                        **paired_contrast(effects[lite], effects[flash]),
                    }
                )
    report = {
        "manifest_id": study["manifest_id"],
        "status": "complete" if complete else "incomplete_or_unexecuted",
        "independent_worlds": study["independent_worlds"],
        "assigned_slots": len(slots),
        "dispatched_slots": sum(s["assignment_status"] == "observed" for s in slots),
        "accounting_includes_probes": accounting,
        "primary_and_secondary_contrasts": contrasts,
        "panels": summaries,
        "episodes": slots,
        "external_inference": False,
        "interpretation": "Never-dispatched slots are not observed failures. Incomplete panels have no completed-study accuracy or paired effect estimate.",
    }
    output.mkdir(parents=True, exist_ok=False)
    atomic_json(output / "analysis.json", report)
    (output / "per-call.jsonl").write_text("".join(canonical(s) + "\n" for s in slots))
    return report
