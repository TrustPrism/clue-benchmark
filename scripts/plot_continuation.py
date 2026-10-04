"""Static scientific figures from saved analysis; independent of the model runtime."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

COLORS = {
    "google/gemini-3.8-flash": "#24547c",
    "google/gemini-3.5-flash-lite": "#457f6c",
    "ollama/qwen3.5:9b": "#ad733a",
}


def label(model):
    return model.split("/", 1)[1]


def save(fig, output, name):
    fig.savefig(output / (name + ".png"), dpi=180)
    fig.savefig(output / (name + ".svg"))
    plt.close(fig)


def curves(cells, cohort, output):
    entries = [
        r for r in cells if r["cohort"] == cohort and r["track"] == "investigation"
    ]
    fig, axes = plt.subplots(1, 3, figsize=(12, 5.2), sharey=True)
    plotted = False
    for ax, n in zip(axes, (4, 8, 12)):
        own = [r for r in entries if r["suspects"] == n]
        sizes = sorted({r["worlds"] for r in own})
        counts = ",".join(map(str, sizes)) if sizes else "0"
        ax.set_title(f"{n} suspects · {counts} worlds")
        for model, color in COLORS.items():
            for policy, style in (("agent", "-"), ("random", "--")):
                points = [
                    next(
                        (
                            r
                            for r in own
                            if r["model"] == model
                            and r["selection_policy"] == policy
                            and r["budget_fraction"] == b
                        ),
                        None,
                    )
                    for b in (0.25, 0.5, 0.75, 1.0)
                ]
                if not any(points):
                    continue
                plotted = True
                y = np.array([r["accuracy"] * 100 if r else np.nan for r in points])
                lo = np.array([r["ci95"][0] * 100 if r else np.nan for r in points])
                hi = np.array([r["ci95"][1] * 100 if r else np.nan for r in points])
                ax.errorbar(
                    [25, 50, 75, 100],
                    y,
                    yerr=[np.maximum(0, y - lo), np.maximum(0, hi - y)],
                    color=color,
                    marker="o" if policy == "agent" else "s",
                    linestyle=style,
                    linewidth=1.5,
                    capsize=3,
                    markersize=4,
                    label=f"{label(model)} / {'investigation' if policy == 'agent' else 'random evidence'}",
                )
        if not own:
            ax.text(
                0.5,
                0.5,
                "No fully attempted cells",
                transform=ax.transAxes,
                ha="center",
                color="#666666",
                fontsize=9,
            )
        ax.set_xticks([25, 50, 75, 100])
        ax.set_xlim(20, 105)
        ax.set_ylim(-3, 103)
        ax.set_xlabel("Evidence budget (%)")
        ax.grid(axis="y", alpha=0.18)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Exact-answer accuracy (%)")
    handles, labels = [], []
    for ax in axes:
        h, names = ax.get_legend_handles_labels()
        for handle, name in zip(h, names):
            if name not in labels:
                handles.append(handle)
                labels.append(name)
    title = (
        "Original 12-world pilot"
        if cohort == "initial_pilot"
        else "Expanded development · fully attempted matched worlds"
    )
    fig.suptitle(f"{title} · exploratory", fontsize=13, y=0.98)
    if plotted:
        fig.legend(
            handles,
            labels,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.91),
            ncol=2,
            frameon=False,
            fontsize=8,
        )
    fig.subplots_adjust(top=0.66, bottom=0.25, wspace=0.18)
    fig.text(
        0.04,
        0.065,
        "Source: first-$25 development continuation. Only fully attempted cells are plotted; missing cells are unplotted.\nErrors count incorrect. Bars: seeded world-clustered 95% percentile bootstrap; degenerate intervals can occur.\nInvestigation and random evidence differ in interaction/thinking overhead. Historical amendments and resource stops preclude a clean ranking.",
        fontsize=7.5,
        color="#444444",
    )
    save(
        fig,
        output,
        "initial-pilot-curves"
        if cohort == "initial_pilot"
        else "expanded-matched-curves",
    )


def deduction(cells, output):
    entries = [
        r for r in cells if r["cohort"] == "initial_pilot" and r["track"] == "deduction"
    ]
    fig, ax = plt.subplots(figsize=(9, 5.3))
    for i, (model, color) in enumerate(COLORS.items()):
        for j, n in enumerate((4, 8, 12)):
            row = next(
                (r for r in entries if r["model"] == model and r["suspects"] == n), None
            )
            pos = j + (i - 1) * 0.25
            if row is None:
                ax.text(
                    pos,
                    4,
                    "incomplete",
                    rotation=90,
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color=color,
                )
                continue
            y, lo, hi = (
                row["accuracy"] * 100,
                row["ci95"][0] * 100,
                row["ci95"][1] * 100,
            )
            ax.bar(pos, y, 0.23, color=color, label=label(model) if j == 0 else None)
            ax.errorbar(
                pos,
                y,
                yerr=[[max(0, y - lo)], [max(0, hi - y)]],
                fmt="none",
                color="#333333",
                capsize=3,
            )
            ax.text(
                pos,
                y + 2,
                f"{row['correct']}/{row['episodes']}",
                ha="center",
                fontsize=8,
            )
    ax.set_xticks([0, 1, 2], ["4", "8", "12"])
    ax.set_xlabel("Number of suspects")
    ax.set_ylabel("Exact-answer accuracy (%)")
    ax.set_ylim(0, 113)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.grid(axis="y", alpha=0.18)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    fig.legend(
        handles=[Patch(color=c, label=label(m)) for m, c in COLORS.items()],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.90),
        ncol=3,
        frameon=False,
        fontsize=9,
    )
    fig.suptitle(
        "Complete-evidence deduction · original shared development pilot",
        fontsize=12,
        y=0.97,
    )
    fig.subplots_adjust(top=0.84, bottom=0.28)
    fig.text(
        0.06,
        0.065,
        "Only fully attempted eight-case cells are plotted; four paired worlds per suspect size. Errors and missing final answers count incorrect.\nBars: world-clustered 95% percentile bootstrap. Uniform outcomes can give degenerate intervals.\nNative tool, resource and historical accounting failures prevent a clean reasoning ranking; test cases remain unexecuted.",
        fontsize=7.5,
        color="#444444",
    )
    save(fig, output, "initial-pilot-deduction")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("summary")
    args = parser.parse_args()
    path = Path(args.summary)
    analysis = json.loads(path.read_text())
    for cohort in ("initial_pilot", "expanded_development"):
        curves(analysis["plot_cells"], cohort, path.parent)
    deduction(analysis["plot_cells"], path.parent)
    print(
        json.dumps(
            {"figures": 3, "matplotlib": matplotlib.__version__, "generation_calls": 0}
        )
    )


if __name__ == "__main__":
    main()
