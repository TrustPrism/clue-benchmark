"""Render receipt-based outcome figures; install .[figures] first."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot(report, output):
    if not report["complete"]:
        raise ValueError("The published figure requires a completed study")
    pairs = [
        ("32 necessary reports", "equality_tree-32", "branching-32", "Path", "Tree"),
        (
            "Two false reports",
            "relational-random-false-2",
            "relational-targeted-false-2",
            "Random",
            "Targeted",
        ),
        (
            "True connected additions",
            "near-decoys-0-noise-0",
            "near-decoys-12-noise-0",
            "0 extra",
            "12 extra",
        ),
    ]
    models = [
        ("gemini-3.5-flash-lite-high", "Flash-Lite"),
        ("gemini-3.8-flash-high", "Flash"),
    ]
    outcomes = [
        ("supported", "Correct, sufficient evidence", "#2475A8"),
        ("wrong_valid_answers", "Wrong answer", "#D77538"),
        ("abstentions", "Abstention", "#BEC7D0"),
        ("execution_failures", "Provider / protocol failure", "#70467F"),
    ]
    metrics = {(m["arm"], m["model"]): m for m in report["metrics"]}
    plt.rcParams.update({"font.size": 10, "svg.fonttype": "none"})
    fig, axes = plt.subplots(1, 3, figsize=(12.8, 5.4), sharey=True)
    for ax, (title, left, right, a, b) in zip(axes, pairs, strict=True):
        rows = [metrics[arm, model] for model, _ in models for arm in (left, right)]
        labels = [
            f"{label}\n{condition}" for _, label in models for condition in (a, b)
        ]
        bottom = [0.0] * len(rows)
        for key, label, color in outcomes:
            values = [100 * m[key] / m["assigned"] for m in rows]
            ax.bar(
                range(4), values, bottom=bottom, color=color, label=label, width=0.68
            )
            bottom = [v + w for v, w in zip(bottom, values, strict=True)]
        for x, m in enumerate(rows):
            ax.text(
                x, 102, f"{m['supported']}/{m['assigned']}", ha="center", fontsize=10
            )
        ax.set_title(title, pad=12)
        ax.set_xticks(range(4), labels)
        ax.set_ylim(0, 112)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(axis="y", alpha=0.2)
    axes[0].set_ylabel("Assigned attempts (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=2,
        bbox_to_anchor=(0.5, 0.09),
        frameon=False,
    )
    fig.suptitle(
        "Certified clue puzzles: measured Gemini outcomes", fontsize=15, y=0.98
    )
    fig.text(
        0.5,
        0.04,
        "10 paired worlds per comparison × 3 repeats; high thinking, 8,192 output tokens including thinking.\nRepeats are clustered by world. All views contain sufficient evidence. Small exploratory cohort.",
        ha="center",
        fontsize=9,
    )
    fig.subplots_adjust(top=0.84, bottom=0.30, wspace=0.14)
    output.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg"):
        fig.savefig(output.with_suffix("." + suffix), dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot(json.loads(args.results.read_text()), args.output)
