"""Offline replay and figures for the October 27 nuisance follow-up.

Never dispatches provider requests. Requires the exact frozen package source
used to prepare and run the study, plus its preserved input and receipt files.
"""

import argparse
import csv
import json
from pathlib import Path

from clue_benchmark.community_bundle import file_hash
from clue_benchmark.config import canonical
from clue_benchmark.dataset import atomic_json
from clue_benchmark.followup_analysis import analyze_followup
from clue_benchmark.replay import write_report


def analyse(root, output, figures=False):
    root, output = Path(root), Path(output)
    report = analyze_followup(root, output)
    episodes = report["episodes"]
    summary = (
        json.loads((root / "execution-summary.json").read_text())
        if (root / "execution-summary.json").exists()
        else None
    )
    report["study_id"] = "nuisance-followup-20261027"
    report["execution_status"] = summary["status"] if summary else "not_recorded"
    frozen_study = json.loads((root / "study.json").read_text())
    first_job = frozen_study["selected_blocks"][0]["jobs"][0]
    report["models"] = json.loads(
        (root / first_job["directory"] / "plan.json").read_text()
    )["models"]
    report["provenance"] = {
        "source_snapshot_index": "release/followup-preflight.json",
        "frozen_manifest_sha256": file_hash(root / "study.json"),
        "scored_calls": len(episodes),
        "probe_calls": 2,
        "output_cap_including_thinking": 4096,
        "temperature": 0,
        "thinking": "low",
        "input_view": "structured_text",
        "independent_worlds_per_stratum": 4,
        "attempts_per_world_model_dose": 2,
        "pricing_date": "2026-10-27",
    }
    report["outcomes"] = {
        "observed_scored_slots": sum(
            e["assignment_status"] == "observed" for e in episodes
        ),
        "never_dispatched_slots": sum(
            e["assignment_status"] == "never_dispatched" for e in episodes
        ),
        "transport_failures": sum(
            e["assignment_status"] == "observed" and e.get("transport") != "ok"
            for e in episodes
        ),
        "protocol_failures": sum(
            e["assignment_status"] == "observed" and not e.get("protocol_valid")
            for e in episodes
        ),
        "unnecessary_abstentions": sum(
            bool(e.get("abstained")) and bool(e.get("sufficient_evidence"))
            for e in episodes
        ),
        "wrong_valid_answers": sum(
            bool(e.get("protocol_valid"))
            and not e.get("correct")
            and not e.get("abstained")
            for e in episodes
        ),
    }
    for panel in report["panels"]:
        rows = [
            e
            for e in episodes
            if (e["burden"], e["model"], e["dose"])
            == (panel["burden"], panel["model"], panel["dose"])
        ]
        panel.update(
            {
                "input_tokens": sum(e.get("input_tokens") or 0 for e in rows),
                "output_tokens_including_thinking": sum(
                    e.get("output_tokens") or 0 for e in rows
                ),
                "thinking_tokens": sum(e.get("thinking_tokens") or 0 for e in rows),
                "latency_seconds": sum(e.get("wall_seconds") or 0 for e in rows),
                "settled_estimate_microdollars": sum(
                    e.get("actual_microdollars") or 0 for e in rows
                ),
                "correct": sum(bool(e.get("correct")) for e in rows),
                "abstentions": sum(bool(e.get("abstained")) for e in rows),
                "protocol_failures": sum(
                    e["assignment_status"] == "observed" and not e.get("protocol_valid")
                    for e in rows
                ),
            }
        )
    # Keep originals in the private run; reports are safe distribution copies.
    for episode in episodes:
        episode.pop("native_calls", None)
        if "receipt" in episode:
            episode["receipt"] = {
                key: value
                for key, value in episode["receipt"].items()
                if key
                in {
                    "vendor",
                    "finish_reason",
                    "provider_status_code",
                    "usage_present",
                    "thinking_separately_observed",
                    "counters",
                    "derived_counters",
                    "invalid_counters",
                }
            }
    (output / "per-call.jsonl").write_text(
        "".join(canonical(episode) + "\n" for episode in episodes)
    )
    atomic_json(output / "analysis.json", report)
    with (output / "panels.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(report["panels"][0]))
        writer.writeheader()
        writer.writerows(report["panels"])
    changes = []
    for contrast in report["primary_and_secondary_contrasts"]:
        if "between_models" not in contrast:
            for world, change in contrast["per_world_changes"].items():
                if change:
                    rows = [
                        e
                        for e in episodes
                        if e["world_id"] == world
                        and e["model"] == contrast["model"]
                        and e["dose"] in (0, contrast["dose_minus_zero"])
                    ]
                    changes.append(
                        {
                            "world_id": world,
                            "burden": contrast["burden"],
                            "model": contrast["model"],
                            "dose_minus_zero": contrast["dose_minus_zero"],
                            "change": change,
                            "observed_actions": [
                                {
                                    "dose": e["dose"],
                                    "repeat": e["repeat"],
                                    "answer": e.get("answer"),
                                    "supported": e.get("supported"),
                                    "finish_reason": e.get("receipt", {}).get(
                                        "finish_reason"
                                    ),
                                    "output_tokens_including_thinking": e.get(
                                        "output_tokens"
                                    ),
                                }
                                for e in rows
                            ],
                            "interpretation": "Observable final actions only; no claim about unavailable internal thoughts.",
                        }
                    )
    atomic_json(output / "changed-worlds.json", changes)
    write_report(output / "analysis.json", output / "report")
    if figures and report["status"] == "complete":
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        models = [
            ("gemini-3.5-flash-lite-low", "Flash-Lite"),
            ("gemini-3.8-flash-low", "Flash"),
        ]
        for metric, ylabel, title, filename in [
            (
                "assigned_accuracy",
                "Supported correct / assigned (%)",
                "Supported accuracy",
                "paired-accuracy",
            ),
            (
                "settled_estimate_microdollars",
                "Receipt-based estimate (USD / assigned call)",
                "Cost of additional context",
                "cost",
            ),
        ]:
            fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
            for burden, ax in zip((4, 8), axes, strict=True):
                for model, label in models:
                    rows = [
                        next(
                            p
                            for p in report["panels"]
                            if (p["burden"], p["model"], p["dose"])
                            == (burden, model, dose)
                        )
                        for dose in (0, 100, 1000)
                    ]
                    values = [
                        p[metric] * 100
                        if metric == "assigned_accuracy"
                        else p[metric] / p["assigned"] / 1_000_000
                        for p in rows
                    ]
                    ax.plot(range(3), values, marker="o", label=label)
                    if metric == "assigned_accuracy":
                        for x, y, p in zip(range(3), values, rows, strict=True):
                            ax.annotate(
                                f"{p['supported_correct']}/{p['assigned']}",
                                (x, y),
                                xytext=(0, -16 if label == "Flash-Lite" else 7),
                                textcoords="offset points",
                                ha="center",
                            )
                    if metric == "assigned_accuracy":
                        ax.set_ylim(-5, 115)
                ax.set_xticks(range(3), ["0", "100", "1,000"])
                ax.set_xlabel("Independent nuisance records")
                ax.set_ylabel(ylabel)
                ax.set_title(f"{burden} necessary reports · four independent worlds")
                ax.spines[["top", "right"]].set_visible(False)
            axes[1].legend()
            fig.suptitle(title + " · two attempts per world/model/dose · low thinking")
            for extension in ("svg", "png"):
                fig.savefig(output / (filename + "." + extension), dpi=160)
            plt.close(fig)
    checksums = {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    atomic_json(output / "checksums.json", checksums)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--output", required=True)
    parser.add_argument("--figures", action="store_true")
    args = parser.parse_args()
    result = analyse(args.directory, args.output, args.figures)
    print(
        canonical(
            {
                k: result[k]
                for k in (
                    "status",
                    "independent_worlds",
                    "assigned_slots",
                    "dispatched_slots",
                    "accounting_includes_probes",
                    "outcomes",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
