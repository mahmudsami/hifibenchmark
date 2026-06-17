#!/usr/bin/env python3
"""
EXTRA real-data plot: both rye read sets (HiFi + DeepConsensus) compared as
grouped bar charts — one subplot per metric (Accuracy, Mapping time, Peak
memory), with the two rye read sets as the x-axis groups and one bar per mapper.

Reads results/csv/results_real.csv.

Usage:   python3 scripts/extra_plot_real_rye.py
Output:  results/plots/real_rye.png / .pdf
"""
import os, csv
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH  = os.path.join(BENCH_DIR, "results", "csv", "results_real.csv")
PLOTS_DIR = os.path.join(BENCH_DIR, "results", "plots")

READSETS      = ["hifi", "deepconsensus"]
READSET_TITLE = {"hifi": "Rye (HiFi)", "deepconsensus": "Rye (DeepConsensus)"}
MAPPER_ORDER  = ["minimap2", "blend", "synpact", "mapquik"]
COLORS = {"minimap2": "#1f77b4", "blend": "#ff7f0e", "synpact": "#d62728", "mapquik": "#9467bd"}
LABELS = {"minimap2": "minimap2", "blend": "BLEND", "synpact": "synpact", "mapquik": "mapquik"}

# (csv key, title, kind, scale)
PANELS = [
    ("accuracy",    "Accuracy vs consensus (%)", "pct",    1.0),
    ("map_time_s",  "Mapping time (s)",          "log",    1.0),
    ("peak_rss_mb", "Peak RSS (GB)",             "linear", 1 / 1024.0),
]


def main():
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"CSV not found: {CSV_PATH}\nRun 13_collect_real.py first.")
    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))

    # data[(readset, mapper)][key] = value
    data = defaultdict(dict)
    for r in rows:
        if r["genome"] == "rye" and r.get("readset") in READSETS:
            for key, *_ in PANELS:
                v = r.get(key)
                data[(r["readset"], r["mapper"])][key] = float(v) if v not in (None, "") else 0.0

    present = {m for (_, m) in data}
    mappers = [m for m in MAPPER_ORDER if m in present]
    if not mappers:
        raise SystemExit("No rye rows found in results_real.csv")

    fig, axes = plt.subplots(1, len(PANELS), figsize=(5 * len(PANELS), 4.6))
    fig.suptitle("Rye real reads — HiFi vs DeepConsensus, by mapper",
                 fontsize=14, fontweight="bold")

    x = np.arange(len(READSETS))
    width = 0.8 / len(mappers)

    for ax, (key, title, kind, scale) in zip(axes, PANELS):
        for mi, m in enumerate(mappers):
            vals = [data.get((rs, m), {}).get(key, 0.0) * scale for rs in READSETS]
            offset = (mi - len(mappers) / 2 + 0.5) * width
            bars = ax.bar(x + offset, vals, width * 0.9, color=COLORS[m],
                          label=LABELS[m], alpha=0.9)
            for b, v in zip(bars, vals):
                if v > 0:
                    ax.text(b.get_x() + b.get_width() / 2, v,
                            f"{v:.1f}" if v < 100 else f"{v:.0f}",
                            ha="center", va="bottom", fontsize=7, rotation=90)
        ax.set_title(title, fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels([READSET_TITLE[rs] for rs in READSETS])
        ax.grid(axis="y", linewidth=0.3, alpha=0.6)
        ax.tick_params(labelsize=8)
        if kind == "pct":
            ax.set_ylim(0, 112)
        elif kind == "log":
            ax.set_yscale("log")
        else:
            top = max((data.get((rs, m), {}).get(key, 0.0) * scale
                       for rs in READSETS for m in mappers), default=1.0)
            ax.set_ylim(0, top * 1.18)

    axes[0].legend(fontsize=8, ncol=2, loc="lower left")
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    os.makedirs(PLOTS_DIR, exist_ok=True)
    out = os.path.join(PLOTS_DIR, "real_rye")
    fig.savefig(out + ".png", dpi=150, bbox_inches="tight")
    fig.savefig(out + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}.png")


if __name__ == "__main__":
    main()
