"""Pure offline replay of the fixed nuisance protocol and its final extension."""

import hashlib
import json
from collections import defaultdict
from importlib.resources import files
from pathlib import Path

from .config import VERSION, canonical
from .dataset import atomic_json
from .followup_analysis import paired_contrast


def summarize_phase(episodes):
    groups = defaultdict(list)
    for row in episodes:
        groups[row["burden"], row["model"], row["dose"]].append(row)
    panels, means = [], {}
    for (burden, model, dose), records in sorted(groups.items()):
        worlds = defaultdict(list)
        for row in records:
            worlds[row["world_id"]].append(row)
        if any(
            len(rows) != 2 or {r["repeat"] for r in rows} != {0, 1}
            for rows in worlds.values()
        ):
            raise ValueError("saved study has missing or repeated intentional attempts")
        world_means = {
            w: sum(bool(r["supported"]) for r in rows) / 2 for w, rows in worlds.items()
        }
        means[burden, model, dose] = world_means
        panels.append(
            {
                "burden": burden,
                "model": model,
                "dose": dose,
                "worlds": len(worlds),
                "assigned": len(records),
                "supported_correct": sum(bool(r["supported"]) for r in records),
                "assigned_accuracy": sum(world_means.values()) / len(world_means),
                "abstentions": sum(bool(r["abstained"]) for r in records),
                "wrong_answers": sum(
                    r["protocol_valid"] and not r["abstained"] and not r["correct"]
                    for r in records
                ),
                "protocol_failures": sum(not r["protocol_valid"] for r in records),
                "attempt_disagreement_worlds": sum(
                    len({canonical(r.get("answer")) for r in rows}) > 1
                    for rows in worlds.values()
                ),
                "settled_estimate_microdollars": sum(
                    r["actual_microdollars"] for r in records
                ),
                "input_tokens": sum(r["input_tokens"] for r in records),
                "output_tokens_including_thinking": sum(
                    r["output_tokens"] for r in records
                ),
                "latency_seconds": sum(r["wall_seconds"] for r in records),
            }
        )
    contrasts = []
    for burden, model in sorted({(b, m) for b, m, _ in means}):
        for dose in (100, 1000):
            result = paired_contrast(
                means[burden, model, 0], means[burden, model, dose]
            )
            result["unchanged_worlds"] = sum(
                change == 0 for change in result["per_world_changes"].values()
            )
            contrasts.append(
                {
                    "burden": burden,
                    "model": model,
                    "dose_minus_zero": dose,
                    "primary": burden == 4 and "flash-lite" in model and dose == 1000,
                    **result,
                }
            )
    for burden in (4, 8):
        lite = "gemini-3.5-flash-lite-low"
        flash = "gemini-3.8-flash-low"
        for dose in (100, 1000):
            effects = {
                model: {
                    w: v - means[burden, model, 0][w]
                    for w, v in means[burden, model, dose].items()
                }
                for model in (lite, flash)
            }
            contrasts.append(
                {
                    "burden": burden,
                    "between_models": "Flash minus Lite dose effect",
                    "dose_minus_zero": dose,
                    "primary": False,
                    **paired_contrast(effects[lite], effects[flash]),
                }
            )
    return {
        "worlds": len({r["world_id"] for r in episodes}),
        "assigned": len(episodes),
        "panels": panels,
        "contrasts": contrasts,
    }


def analyze_measurements(value):
    if value.get("schema_version") != "clue-nuisance-measurements-1":
        raise ValueError("unsupported nuisance measurement schema")
    episodes = value["episodes"]
    if len(episodes) != 144 or len({r["request_id"] for r in episodes}) != 144:
        raise ValueError("expected exactly 144 unique saved scored assignments")
    phases = {
        phase: summarize_phase([r for r in episodes if r["phase"] == phase])
        for phase in ("initial", "extension")
    }
    if (
        phases["initial"]["worlds"],
        phases["initial"]["assigned"],
        phases["extension"]["worlds"],
        phases["extension"]["assigned"],
    ) != (8, 96, 4, 48):
        raise ValueError("initial/extension phase denominators changed")
    initial_worlds = {r["world_id"] for r in episodes if r["phase"] == "initial"}
    if initial_worlds & {r["world_id"] for r in episodes if r["phase"] == "extension"}:
        raise ValueError("extension reused measured worlds")
    accounting = value["accounting"]
    if (
        accounting["held_microdollars"]
        or sum(r["actual_microdollars"] for r in episodes)
        + accounting["probe_microdollars_included_in_initial"]
        != accounting["combined_settled_microdollars"]
        or accounting["combined_settled_microdollars"]
        > accounting["combined_cap_microdollars"]
    ):
        raise ValueError("saved combined accounting is inconsistent")
    combined = summarize_phase(episodes)
    if (
        combined["worlds"] != 12
        or len(combined["panels"]) != 12
        or any(p["assigned"] != 12 or p["worlds"] != 6 for p in combined["panels"])
    ):
        raise ValueError("combined matched design is incomplete")
    return {
        "software_version": VERSION,
        "measurement_software_version": value["measurement_software_version"],
        "study_id": value["study_id"],
        "status": "complete",
        "model_calls": 0,
        "independent_worlds": 12,
        "assigned_slots": 144,
        "external_inference": False,
        "accounting": accounting,
        "phases": phases,
        "combined": combined,
        "panels": combined["panels"],
        "limitations": value["limitations"],
        "equivalence": "Not tested. Equal observed scores do not establish that effects are absent.",
        "source_manifest_ids": {
            "initial": value["initial_manifest_id"],
            "extension": value["extension_id"],
        },
    }


def replay_nuisance(output, figures=False):
    from .replay import write_report

    resources = files("clue_benchmark").joinpath("resources", "measured-results")
    raw = resources.joinpath("nuisance-followup.json").read_bytes()
    index = json.loads(resources.joinpath("index.json").read_text())[
        "nuisance-followup"
    ]
    if hashlib.sha256(raw).hexdigest() != index["sanitized_sha256"]:
        raise ValueError("saved nuisance measurements failed checksum verification")
    result = analyze_measurements(json.loads(raw))
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    atomic_json(root / "analysis.json", result)
    for phase, data in result["phases"].items():
        atomic_json(root / (phase + ".json"), data)
    write_report(root / "analysis.json", root / "report")
    if figures:
        from .result_figures import plot_nuisance

        plot_nuisance(result, root)
    return result
