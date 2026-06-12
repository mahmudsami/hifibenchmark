#!/usr/bin/env python3
"""
Plot accuracy and precision from results/csv/results.csv.

For each genome, produces one figure:
  • Rows  : metric (Accuracy %, Precision %)
  • Cols  : read length (10 k, 15 k, 20 k, 25 k)
  • X-axis: error rate (%)
  • Lines : one per mapper

Saves to results/plots/{genome}_accuracy.png
"""
import os
import csv
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BENCH_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH   = os.path.join(BENCH_DIR, "results", "csv", "results.csv")
PLOTS_DIR  = os.path.join(BENCH_DIR, "results", "plots")

MAPPER_COLORS = {
    "minimap2":         "#1f77b4",
    "blend":            "#ff7f0e",
    "strobealign":      "#2ca02c",
    "syncmer":          "#d62728",
    "mapquik":          "#9467bd",
}
MAPPER_LABELS = {
    "minimap2":         "minimap2",
    "blend":            "BLEND",
    "strobealign":      "strobealign",
    "syncmer":          "syncmer",
    "mapquik":          "mapquik",
}
MARKERS = {"minimap2": "o", "blend": "s", "strobealign": "^", "syncmer": "D", "mapquik": "v"}

METRICS = [("accuracy", "Accuracy (%)"), ("precision", "Precision (%)")]


def load_csv(path: str) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def group_data(rows: list[dict]) -> dict:
    """Index: data[genome][mapper][read_length][error_pct] = {metric: value}"""
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for row in rows:
        g   = row["genome"]
        m   = row["mapper"]
        rlen = int(row["read_length"])
        epct = float(row["error_pct"])
        data[g][m][rlen][epct] = {
            "accuracy":     float(row["accuracy"]),
            "precision":    float(row["precision"]),
            "mapping_rate": float(row["mapping_rate"]),
        }
    return data


def plot_genome(genome: str, data: dict, read_lengths: list, mappers: list) -> None:
    n_metrics = len(METRICS)
    n_lengths = len(read_lengths)

    fig, axes = plt.subplots(
        n_metrics, n_lengths,
        figsize=(4.5 * n_lengths, 3.5 * n_metrics),
        sharex=True,
    )
    # Ensure 2-D indexing even when n_metrics == 1
    if n_metrics == 1:
        axes = [axes]

    fig.suptitle(f"Mapping Quality — {genome.capitalize()} genome", fontsize=14, fontweight="bold")

    for col, rlen in enumerate(read_lengths):
        for row, (metric_key, metric_label) in enumerate(METRICS):
            ax = axes[row][col]

            for mapper in mappers:
                mapper_data = data.get(mapper, {}).get(rlen, {})
                if not mapper_data:
                    continue
                xs = sorted(mapper_data.keys())
                ys = [mapper_data[x][metric_key] for x in xs]
                ax.plot(
                    xs, ys,
                    color=MAPPER_COLORS.get(mapper, "grey"),
                    marker=MARKERS.get(mapper, "o"),
                    linewidth=1.8,
                    markersize=6,
                    label=MAPPER_LABELS.get(mapper, mapper),
                )

            # Auto-zoom to span ALL plotted mappers so even a low performer
            # (e.g. mapquik on the repeat-rich rye genome, ~25 %) stays visible
            # rather than running off the bottom of the axis.
            vals = [
                data.get(mp, {}).get(rlen, {}).get(ep, {}).get(metric_key)
                for mp in mappers
                for ep in data.get(mp, {}).get(rlen, {})
            ]
            vals = [v for v in vals if v is not None]
            if vals:
                ax.set_ylim(max(0.0, min(vals) - 2.0), 100.3)
            else:
                ax.set_ylim(0, 100.3)

            ax.set_xlabel("Error rate (%)" if row == n_metrics - 1 else "")
            ax.set_ylabel(metric_label if col == 0 else "")
            ax.set_title(f"{rlen // 1000} kb reads" if row == 0 else "")
            ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.2g"))
            ax.grid(axis="y", linewidth=0.4, alpha=0.6)
            ax.tick_params(labelsize=8)

            if row == 0 and col == n_lengths - 1:
                ax.legend(fontsize=8, loc="lower left", framealpha=0.8)

    plt.tight_layout()
    os.makedirs(PLOTS_DIR, exist_ok=True)
    out = os.path.join(PLOTS_DIR, f"{genome}_accuracy")
    fig.savefig(out + ".png", dpi=150, bbox_inches="tight")
    fig.savefig(out + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


def main():
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"CSV not found: {CSV_PATH}\nRun 06_collect_results.py first.")

    rows        = load_csv(CSV_PATH)
    data        = group_data(rows)
    genomes     = sorted({r["genome"] for r in rows})
    read_lengths = sorted({int(r["read_length"]) for r in rows})
    mappers     = [m for m in MAPPER_COLORS if m in {r["mapper"] for r in rows}]

    for genome in genomes:
        plot_genome(genome, data[genome], read_lengths, mappers)


if __name__ == "__main__":
    main()
