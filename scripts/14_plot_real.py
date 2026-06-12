#!/usr/bin/env python3
"""
Plot the real-data benchmark from results/csv/results_real.csv.

One figure with four panels (mappers on the x-axis, grouped by genome):
    Accuracy (%) | Precision (%) | Wall time (s) | Peak RSS (MB)

Saves to results/plots/real_benchmark.png
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

# Canonical display order + labels; the x-axis uses whichever of these the CSV
# actually contains (so mapquik shows up automatically once it's in the real arm).
MAPPER_ORDER = ["minimap2", "blend", "strobealign", "syncmer", "mapquik"]
LABELS  = {"minimap2": "minimap2", "blend": "BLEND", "strobealign": "strobealign",
           "syncmer": "syncmer", "mapquik": "mapquik"}

# Key: (genome, readset) — rye gets two entries
GROUP_COLORS = {
    ("human",       "hifi"):         "#4c72b0",
    ("maize",       "hifi"):         "#dd8452",
    ("arabidopsis", "hifi"):         "#55a868",
    ("rye",         "hifi"):         "#c44e52",
    ("rye",         "deepconsensus"): "#9b59b6",
}
GROUP_LABELS = {
    ("human",       "hifi"):         "Human",
    ("maize",       "hifi"):         "Maize",
    ("arabidopsis", "hifi"):         "Arabidopsis",
    ("rye",         "hifi"):         "Rye (HiFi)",
    ("rye",         "deepconsensus"): "Rye (DC)",
}
GROUP_ORDER = [
    ("human", "hifi"), ("maize", "hifi"), ("arabidopsis", "hifi"),
    ("rye", "hifi"), ("rye", "deepconsensus"),
]

PANELS = [
    ("accuracy",    "Accuracy vs consensus (%)"),
    ("precision",   "Precision vs consensus (%)"),
    ("map_time_s",  "Mapping time (s, index excluded)"),
    ("peak_rss_mb", "Peak RSS (MB)"),
]


def main():
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"CSV not found: {CSV_PATH}\nRun 13_collect_real.py first.")

    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))

    # data[(genome, readset)][mapper][field]
    data = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        readset = r.get("readset", "hifi")
        group = (r["genome"], readset)
        for key, _ in PANELS:
            data[group][r["mapper"]][key] = float(r[key]) if r[key] not in (None, "") else 0.0

    groups = [g for g in GROUP_ORDER if g in data] + [g for g in data if g not in GROUP_ORDER]

    # Keep only mappers actually present in the CSV, in canonical order.
    present = {r["mapper"] for r in rows}
    MAPPERS = [m for m in MAPPER_ORDER if m in present]

    fig, axes = plt.subplots(1, len(PANELS), figsize=(5 * len(PANELS), 4.5))
    fig.suptitle("Real HiFi reads — mapper benchmark (~100k reads/genome, consensus truth)",
                 fontsize=14, fontweight="bold")

    x = np.arange(len(MAPPERS))
    width = 0.8 / max(len(groups), 1)

    for ax, (key, title) in zip(axes, PANELS):
        for gi, group in enumerate(groups):
            vals = [data[group].get(m, {}).get(key, 0.0) for m in MAPPERS]
            offset = (gi - len(groups) / 2 + 0.5) * width
            ax.bar(x + offset, vals, width=width * 0.9,
                   color=GROUP_COLORS.get(group, "grey"),
                   label=GROUP_LABELS.get(group, str(group)), alpha=0.88)
        ax.set_title(title, fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels([LABELS[m] for m in MAPPERS], rotation=30, ha="right", fontsize=8)
        ax.grid(axis="y", linewidth=0.4, alpha=0.6)
        ax.tick_params(labelsize=8)
        if key in ("accuracy", "precision"):
            ax.set_ylim(0, 103)
        ax.legend(fontsize=8)

    plt.tight_layout()
    os.makedirs(PLOTS_DIR, exist_ok=True)
    out = os.path.join(PLOTS_DIR, "real_benchmark")
    fig.savefig(out + ".png", dpi=150, bbox_inches="tight")
    fig.savefig(out + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
