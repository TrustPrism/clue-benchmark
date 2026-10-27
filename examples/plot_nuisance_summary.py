"""Make the documentation overview from saved measurements; no model calls."""

import argparse
import json
from pathlib import Path


def plot_summary(source, output, mobile=False):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    result = json.loads(Path(source).read_text())
    panels = result["combined"]["panels"]
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "text.color": "#203731",
            "axes.labelcolor": "#60706a",
            "xtick.color": "#60706a",
            "ytick.color": "#60706a",
            "axes.edgecolor": "#dbe3dd",
            "svg.hashsalt": "clue-nuisance-summary",
        }
    ):
        fig, axes = plt.subplots(
            2 if mobile else 1,
            1 if mobile else 2,
            figsize=(5.3, 7.2) if mobile else (10, 4.6),
            sharey=True,
        )
        fig.set_facecolor("white")
        for ax, burden in zip(axes, (4, 8), strict=True):
            ax.set_title(f"{burden} necessary reports", loc="left", pad=22)
            ax.set_axisbelow(True)
            ax.grid(axis="y", color="#e7ece5")
            for model, label, color, marker in [
                ("gemini-3.5-flash-lite-low", "Flash-Lite", "#166557", "o"),
                ("gemini-3.8-flash-low", "Flash", "#b46b35", "s"),
            ]:
                rows = [
                    next(
                        panel
                        for panel in panels
                        if (panel["burden"], panel["model"], panel["dose"])
                        == (burden, model, dose)
                    )
                    for dose in (0, 100, 1000)
                ]
                values = [p["supported_correct"] / p["assigned"] * 100 for p in rows]
                ax.plot(
                    range(3),
                    values,
                    color=color,
                    marker=marker,
                    markersize=7,
                    linewidth=2.5,
                    label=label,
                )
                for x, y, row in zip(range(3), values, rows, strict=True):
                    ax.annotate(
                        f"{row['supported_correct']}/{row['assigned']}",
                        (x, y),
                        xytext=(0, -23 if label == "Flash-Lite" else 11),
                        textcoords="offset points",
                        ha="center",
                        color=color,
                        fontsize=11,
                        fontweight="medium",
                    )
            ax.set_xticks(range(3), ["0", "100", "1,000"])
            ax.set_xlabel("Extra irrelevant records", labelpad=12)
            ax.set_xlim(-0.18, 2.18)
            ax.set_ylim(0, 118)
            ax.set_yticks([0, 25, 50, 75, 100])
            ax.yaxis.set_major_formatter(PercentFormatter())
            ax.spines[["top", "right"]].set_visible(False)
        axes[0].set_ylabel("Supported accuracy", labelpad=12)
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False)
        if mobile:
            fig.subplots_adjust(
                left=0.16, right=0.95, top=0.92, bottom=0.12, hspace=0.65
            )
        else:
            fig.subplots_adjust(
                left=0.09, right=0.97, top=0.84, bottom=0.24, wspace=0.22
            )
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(destination, metadata={"Date": None}, bbox_inches="tight")
        if destination.suffix == ".svg":
            destination.write_text(
                "\n".join(line.rstrip() for line in destination.read_text().splitlines())
                + "\n"
            )
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="benchmarks/nuisance-extended-results.json")
    parser.add_argument("--output", default="docs/site/assets/nuisance-summary.svg")
    parser.add_argument("--mobile", action="store_true")
    args = parser.parse_args()
    plot_summary(args.source, args.output, mobile=args.mobile)
