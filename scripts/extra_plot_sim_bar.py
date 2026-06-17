#!/usr/bin/env python3
"""
EXTRA simulation plot: a single (error rate, read length) operating point shown
as grouped bar charts — one subplot per metric (2x2), with human / maize / rye
as the x-axis groups and one bar per mapper within each group.

Defaults to error rate 0.5 % and read length 20 kb. Reads results/csv/results.csv.

Usage:   python3 scripts/extra_plot_sim_bar.py [error_rate] [read_length]
         (e.g. 0.005 20000 — the defaults)
Output:  results/plots/sim_bar_err<E>_len<L>.png / .pdf
"""
import os, sys, csv
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH  = os.path.join(BENCH_DIR, "results", "csv", "results.csv")
PLOTS_DIR = os.path.join(BENCH_DIR, "results", "plots")

GENOMES      = ["human", "maize", "rye"]
GENOME_TITLE = {"human": "Human", "maize": "Maize", "rye": "Rye"}
MAPPER_ORDER = ["minimap2", "blend", "synpact", "mapquik"]
COLORS = {"minimap2": "#1f77b4", "blend": "#ff7f0e", "synpact": "#d62728", "mapquik": "#9467bd"}
LABELS = {"minimap2": "minimap2", "blend": "BLEND", "synpact": "synpact", "mapquik": "mapquik"}

# (csv key, title, kind, scale)   kind: pct | log | linear
PANELS = [
    ("accuracy",    "Accuracy (%)",     "pct",    1.0),
    ("precision",   "Precision (%)",    "pct",    1.0),
    ("map_time_s",  "Mapping time (s)", "log",    1.0),
    ("peak_rss_mb", "Peak RSS (GB)",    "linear", 1 / 1024.0),
]


def main():
    err = sys.argv[1] if len(sys.argv) > 1 else "0.005"
    length = sys.argv[2] if len(sys.argv) > 2 else "20000"

    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"CSV not found: {CSV_PATH}\nRun 06_collect_results.py first.")
    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))

    # data[(genome, mapper)][key] = value
    data = defaultdict(dict)
    for r in rows:
        if r["error_rate"] == err and r["read_length"] == length:
            for key, *_ in PANELS:
                v = r.get(key)
                data[(r["genome"], r["mapper"])][key] = float(v) if v not in (None, "") else 0.0

    present = {m for (_, m) in data}
    mappers = [m for m in MAPPER_ORDER if m in present]
    if not mappers:
        raise SystemExit(f"No rows for error_rate={err}, read_length={length} in {CSV_PATH}")

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    fig.suptitle(f"Simulation @ {float(err)*100:g}% error, {int(length)//1000} kb reads "
                 f"— genomes × mappers", fontsize=14, fontweight="bold")

    x = np.arange(len(GENOMES))
    width = 0.8 / len(mappers)

    for ax, (key, title, kind, scale) in zip(axes.flat, PANELS):
        for mi, m in enumerate(mappers):
            vals = [data.get((g, m), {}).get(key, 0.0) * scale for g in GENOMES]
            offset = (mi - len(mappers) / 2 + 0.5) * width
            bars = ax.bar(x + offset, vals, width * 0.9, color=COLORS[m],
                          label=LABELS[m], alpha=0.9)
            for b, v in zip(bars, vals):
                if v > 0:
                    ax.text(b.get_x() + b.get_width() / 2, v,
                            f"{v:.1f}" if v < 100 else f"{v:.0f}",
                            ha="center", va="bottom", fontsize=6, rotation=90)
        ax.set_title(title, fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels([GENOME_TITLE[g] for g in GENOMES])
        ax.grid(axis="y", linewidth=0.3, alpha=0.6)
        ax.tick_params(labelsize=8)
        if kind == "pct":
            ax.set_ylim(0, 112)
        elif kind == "log":
            ax.set_yscale("log")
        else:
            top = max((data.get((g, m), {}).get(key, 0.0) * scale
                       for g in GENOMES for m in mappers), default=1.0)
            ax.set_ylim(0, top * 1.18)

    axes.flat[0].legend(fontsize=8, ncol=2, loc="lower left")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    os.makedirs(PLOTS_DIR, exist_ok=True)
    out = os.path.join(PLOTS_DIR, f"sim_bar_err{err}_len{length}")
    fig.savefig(out + ".png", dpi=150, bbox_inches="tight")
    fig.savefig(out + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}.png")


if __name__ == "__main__":
    main()
