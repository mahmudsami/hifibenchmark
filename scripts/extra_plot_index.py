#!/usr/bin/env python3
"""
EXTRA plot: index-BUILD resources (time + peak memory) per genome, as grouped
bar charts. Groups = genome, bars = index builder. Includes synpact built with a
single thread (`synpact1t`) alongside the default 8-thread synpact, to show the
thread-count time/memory trade-off — this extra series exists only here.

Reads results/csv/index_results.csv (produced by collect_index_results.py).

Usage:   python3 scripts/extra_plot_index.py
Output:  results/plots/index_resources.png / .pdf
"""
import os, csv
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH  = os.path.join(BENCH_DIR, "results", "csv", "index_results.csv")
PLOTS_DIR = os.path.join(BENCH_DIR, "results", "plots")

GENOME_ORDER = ["human", "human_y", "maize", "arabidopsis", "rye"]
GENOME_TITLE = {"human": "Human", "human_y": "Human-Y", "maize": "Maize",
                "arabidopsis": "Arabidopsis", "rye": "Rye"}
MAPPER_ORDER = ["minimap2", "blend", "synpact", "synpact1t"]
COLORS = {"minimap2": "#1f77b4", "blend": "#ff7f0e", "synpact": "#d62728", "synpact1t": "#7b1f1f"}
LABELS = {"minimap2": "minimap2", "blend": "BLEND",
          "synpact": "synpact (8t)", "synpact1t": "synpact (1t)"}

# (csv key, title, kind, scale)
PANELS = [
    ("index_time_s",      "Index build time (s)", "log",    1.0),
    ("index_peak_rss_mb", "Index peak RSS (GB)",  "linear", 1 / 1024.0),
]


def main():
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"CSV not found: {CSV_PATH}\nRun collect_index_results.py first.")
    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))

    # data[(genome, mapper)][key] = value
    data = defaultdict(dict)
    for r in rows:
        for key, *_ in PANELS:
            v = r.get(key)
            if v not in (None, ""):
                data[(r["genome"], r["mapper"])][key] = float(v)

    genomes = [g for g in GENOME_ORDER if any((g, m) in data for m in MAPPER_ORDER)]
    genomes += sorted({g for (g, _) in data} - set(genomes))
    present = {m for (_, m) in data}
    mappers = [m for m in MAPPER_ORDER if m in present]
    if not genomes or not mappers:
        raise SystemExit(f"No index rows in {CSV_PATH}")

    fig, axes = plt.subplots(1, len(PANELS), figsize=(6 * len(PANELS), 4.8))
    fig.suptitle("Index build resources — by genome & builder "
                 "(synpact shown at 8 and 1 threads)", fontsize=14, fontweight="bold")

    x = np.arange(len(genomes))
    width = 0.8 / len(mappers)

    for ax, (key, title, kind, scale) in zip(axes, PANELS):
        for mi, m in enumerate(mappers):
            vals = [data.get((g, m), {}).get(key, 0.0) * scale for g in genomes]
            offset = (mi - len(mappers) / 2 + 0.5) * width
            bars = ax.bar(x + offset, vals, width * 0.9, color=COLORS[m],
                          label=LABELS[m], alpha=0.9)
            for b, v in zip(bars, vals):
                if v > 0:
                    ax.text(b.get_x() + b.get_width() / 2, v,
                            f"{v:.0f}" if v >= 10 else f"{v:.1f}",
                            ha="center", va="bottom", fontsize=6, rotation=90)
        ax.set_title(title, fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels([GENOME_TITLE.get(g, g) for g in genomes],
                           rotation=20, ha="right", fontsize=8)
        ax.grid(axis="y", linewidth=0.3, alpha=0.6)
        ax.tick_params(labelsize=8)
        if kind == "log":
            ax.set_yscale("log")
        else:
            top = max((data.get((g, m), {}).get(key, 0.0) * scale
                       for g in genomes for m in mappers), default=1.0)
            ax.set_ylim(0, top * 1.18)

    axes[0].legend(fontsize=8, ncol=2, loc="upper left")
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    os.makedirs(PLOTS_DIR, exist_ok=True)
    out = os.path.join(PLOTS_DIR, "index_resources")
    fig.savefig(out + ".png", dpi=150, bbox_inches="tight")
    fig.savefig(out + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}.png")


if __name__ == "__main__":
    main()
