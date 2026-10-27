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


def plot_nuisance(result, output):
    """Display phases separately and a clearly labeled exploratory aggregate."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root = Path(output)
    for metric, title, ylabel, name in [
        (
            "assigned_accuracy",
            "Supported accuracy",
            "Supported correct / assigned (%)",
            "nuisance-accuracy",
        ),
        (
            "settled_estimate_microdollars",
            "Cost of added context",
            "Estimated USD / assigned call",
            "nuisance-cost",
        ),
    ]:
        fig, axes = plt.subplots(2, 3, figsize=(13, 7), constrained_layout=True)
        for column, (phase, label) in enumerate(
            [
                ("initial", "Initial: four worlds/stratum"),
                ("extension", "Extension: two worlds/stratum"),
                ("combined", "Combined: six worlds/stratum"),
            ]
        ):
            panels = (
                result["combined"]["panels"]
                if phase == "combined"
                else result["phases"][phase]["panels"]
            )
            for row, burden in enumerate((4, 8)):
                ax = axes[row, column]
                for model, model_label in [
                    ("gemini-3.5-flash-lite-low", "Flash-Lite"),
                    ("gemini-3.8-flash-low", "Flash"),
                ]:
                    records = [
                        next(
                            p
                            for p in panels
                            if (p["burden"], p["model"], p["dose"])
                            == (burden, model, d)
                        )
                        for d in (0, 100, 1000)
                    ]
                    ys = [
                        p[metric] * 100
                        if metric == "assigned_accuracy"
                        else p[metric] / p["assigned"] / 1e6
                        for p in records
                    ]
                    ax.plot(range(3), ys, marker="o", label=model_label)
                    if metric == "assigned_accuracy":
                        for x, y, p in zip(range(3), ys, records, strict=True):
                            ax.annotate(
                                f"{p['supported_correct']}/{p['assigned']}",
                                (x, y),
                                xytext=(0, -14 if model_label == "Flash-Lite" else 6),
                                textcoords="offset points",
                                ha="center",
                                fontsize=9,
                            )
                ax.set_xticks(range(3), ["0", "100", "1,000"])
                ax.set_xlabel("Independent nuisance records")
                ax.set_ylabel(ylabel)
                ax.set_title(f"{label}\n{burden} necessary reports", fontsize=10)
                ax.spines[["top", "right"]].set_visible(False)
                if metric == "assigned_accuracy":
                    ax.set_ylim(-5, 115)
        axes[1, 2].legend(loc="lower left")
        fig.suptitle(
            title + " · two attempts per world · combined estimate is exploratory",
            fontsize=13,
        )
        for extension in ("png", "svg"):
            fig.savefig(root / (name + "." + extension), dpi=160)
        plt.close(fig)
