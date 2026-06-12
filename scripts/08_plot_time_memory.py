#!/usr/bin/env python3
"""
Plot wall time and peak memory from results/csv/results.csv.

For each genome, produces one figure:
  • Rows  : metric (Wall time (s), Peak RSS (MB))
  • Cols  : error rate (0.1 %, 0.5 %, 1 %)
  • X-axis: read length (kb)
  • Bars  : grouped by mapper

Saves to results/plots/{genome}_performance.png
"""
import os, csv
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

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

PERF_METRICS = [
    ("map_time_s",   "Mapping time (s, index excluded)"),
    ("peak_rss_mb",  "Peak RSS (MB)"),
]


def load_csv(path: str) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def group_data(rows: list[dict]) -> dict:
    """Index: data[genome][mapper][error_pct][read_length] = {metric: value}"""
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for row in rows:
        g    = row["genome"]
        m    = row["mapper"]
        epct = float(row["error_pct"])
        rlen = int(row["read_length"])
        data[g][m][epct][rlen] = {
            "map_time_s":  float(row["map_time_s"]) if row.get("map_time_s") else None,
            "peak_rss_mb": float(row["peak_rss_mb"]) if row["peak_rss_mb"] else None,
        }
    return data


def plot_genome(genome: str, data: dict, error_pcts: list, read_lengths: list, mappers: list) -> None:
    n_metrics = len(PERF_METRICS)
    n_errors  = len(error_pcts)

    fig, axes = plt.subplots(
        n_metrics, n_errors,
        figsize=(4.5 * n_errors, 3.5 * n_metrics),
        sharex=True,
    )
    if n_metrics == 1:
        axes = [axes]

    fig.suptitle(f"Mapping Performance — {genome.capitalize()} genome", fontsize=14, fontweight="bold")

    bar_width  = 0.8 / max(len(mappers), 1)
    x_positions = np.arange(len(read_lengths))

    for col, epct in enumerate(error_pcts):
        for row, (metric_key, metric_label) in enumerate(PERF_METRICS):
            ax = axes[row][col]

            for i, mapper in enumerate(mappers):
                values = []
                for rlen in read_lengths:
                    v = data.get(mapper, {}).get(epct, {}).get(rlen, {}).get(metric_key)
                    values.append(v if v is not None else 0)

                offset = (i - len(mappers) / 2 + 0.5) * bar_width
                bars = ax.bar(
                    x_positions + offset,
                    values,
                    width=bar_width * 0.9,
                    color=MAPPER_COLORS.get(mapper, "grey"),
                    label=MAPPER_LABELS.get(mapper, mapper),
                    alpha=0.85,
                )

            ax.set_xticks(x_positions)
            ax.set_xticklabels([f"{r // 1000}k" for r in read_lengths], fontsize=8)
            ax.set_xlabel("Read length" if row == n_metrics - 1 else "")
            ax.set_ylabel(metric_label if col == 0 else "")
            ax.set_title(f"Error rate {epct:.1f}%" if row == 0 else "")
            ax.grid(axis="y", linewidth=0.4, alpha=0.6)
            ax.tick_params(labelsize=8)

            if row == 0 and col == n_errors - 1:
                ax.legend(fontsize=8, framealpha=0.8)

    plt.tight_layout()
    os.makedirs(PLOTS_DIR, exist_ok=True)
    out = os.path.join(PLOTS_DIR, f"{genome}_performance")
    fig.savefig(out + ".png", dpi=150, bbox_inches="tight")
    fig.savefig(out + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


def main():
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"CSV not found: {CSV_PATH}\nRun 06_collect_results.py first.")

    rows         = load_csv(CSV_PATH)
    data         = group_data(rows)
    genomes      = sorted({r["genome"] for r in rows})
    error_pcts   = sorted({float(r["error_pct"]) for r in rows})
    read_lengths = sorted({int(r["read_length"]) for r in rows})
    mappers      = [m for m in MAPPER_COLORS if m in {r["mapper"] for r in rows}]

    for genome in genomes:
        plot_genome(genome, data[genome], error_pcts, read_lengths, mappers)


if __name__ == "__main__":
    main()
