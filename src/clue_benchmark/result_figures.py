"""Optional scientific plots, using only recomputed historical assignment counts."""

from pathlib import Path


def plot_results(result, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root = Path(output)
    panels = result["studies"]["pilot"]["panels"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for model, label in [
        ("gemini-3.5-flash-lite-low", "Flash-Lite"),
        ("gemini-3.8-flash-low", "Flash"),
    ]:
        rows = [
            next(
                p
                for p in panels
                if p["model"] == model and p["arm"] == f"burden-4-noise-{dose}"
            )
            for dose in (0, 100, 1000)
        ]
        values = [p["correct"] / p["assigned"] for p in rows]
        axes[0].plot(range(3), values, marker="o", label=label)
        for x, y, p in zip(range(3), values, rows, strict=True):
            axes[0].annotate(
                f"{p['correct']}/{p['assigned']}",
                (x, y),
                xytext=(0, -16 if model.endswith("lite-low") else 7),
                textcoords="offset points",
                ha="center",
            )
        axes[1].plot(
            range(3),
            [
                p["known_estimate_microdollars"] / p["assigned"] / 1_000_000
                for p in rows
            ],
            marker="o",
            label=label,
        )
    for ax in axes:
        ax.set_xticks(range(3), ["0", "100", "1,000"])
        ax.set_xlabel("Independent nuisance records")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Assigned-denominator accuracy")
    axes[0].set_ylim(-0.05, 1.15)
    axes[0].set_title("Same five worlds; one attempt per dose")
    axes[1].set_ylabel("Estimated USD per assigned call")
    axes[1].set_title("Receipt estimates; not provider invoices")
    axes[1].legend()
    fig.suptitle("Historical four-report stratum · low thinking · 4,096 output tokens")
    fig.savefig(root / "paired-accuracy-and-cost.svg")
    plt.close(fig)
    return str(root / "paired-accuracy-and-cost.svg")
