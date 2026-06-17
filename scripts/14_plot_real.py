#!/usr/bin/env python3
"""
Plot the real-data benchmark from results/csv/results_real.csv.

Grid layout matching the simulation plots (_plot_grid.py): one ROW per genome
(rye split into HiFi + DeepConsensus), one COLUMN per metric. Each cell is a bar
chart with one bar per mapper, colored consistently with the simulation figures.

    rows    = genome / readset
    columns = Mapping rate | Accuracy | Precision | Mapping time | Peak RSS
    bars    = one per mapper

Saves to results/plots/real_benchmark.{png,pdf}
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

# Canonical mapper order + colors/labels, matching the simulation grid so the
# two figure sets are visually consistent. The x-axis of each cell uses whichever
# of these the CSV actually contains (mapquik appears automatically).
MAPPER_ORDER  = ["minimap2", "blend", "synpact", "mapquik"]
MAPPER_COLORS = {
    "minimap2": "#1f77b4", "blend": "#ff7f0e",
    "synpact": "#d62728", "mapquik": "#9467bd",
}
LABELS = {"minimap2": "minimap2", "blend": "BLEND",
          "synpact": "synpact", "mapquik": "mapquik"}

# Row key: (genome, readset) — rye gets two rows.
GROUP_LABELS = {
    ("human",       "hifi"):          "Human",
    ("maize",       "hifi"):          "Maize",
    ("arabidopsis", "hifi"):          "Arabidopsis",
    ("rye",         "hifi"):          "Rye (HiFi)",
    ("rye",         "deepconsensus"): "Rye (DC)",
}
GROUP_ORDER = [
    ("human", "hifi"), ("maize", "hifi"), ("arabidopsis", "hifi"),
    ("rye", "hifi"), ("rye", "deepconsensus"),
]

# (csv key, column title, is_percent, scale)
PANELS = [
    ("mapping_rate", "Mapping rate (%)",            True,  1.0),
    ("accuracy",     "Accuracy vs consensus (%)",   True,  1.0),
    ("precision",    "Precision vs consensus (%)",  True,  1.0),
    ("map_time_s",   "Mapping time (s)",            False, 1.0),
    ("peak_rss_mb",  "Peak RSS (GB)",               False, 1 / 1024.0),
]


def main():
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"CSV not found: {CSV_PATH}\nRun 13_collect_real.py first.")

    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))

    # data[(genome, readset)][mapper][key] = value (scaled later)
    data = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        group = (r["genome"], r.get("readset", "hifi"))
        for key, *_ in PANELS:
            v = r.get(key)
            data[group][r["mapper"]][key] = float(v) if v not in (None, "") else 0.0

    groups  = [g for g in GROUP_ORDER if g in data] + [g for g in data if g not in GROUP_ORDER]
    present = {r["mapper"] for r in rows}
    MAPPERS = [m for m in MAPPER_ORDER if m in present]

    nrows, ncols = len(groups), len(PANELS)
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.0 * ncols, 2.2 * nrows),
                             squeeze=False)
    fig.suptitle("Real HiFi reads — mapper benchmark (~100k reads/genome, consensus truth)\n"
                 "rows = genome · columns = metric",
                 fontsize=13, fontweight="bold")

    x = np.arange(len(MAPPERS))
    for ri, group in enumerate(groups):
        for ci, (key, title, is_pct, scale) in enumerate(PANELS):
            ax = axes[ri][ci]
            vals   = [data[group].get(m, {}).get(key, 0.0) * scale for m in MAPPERS]
            colors = [MAPPER_COLORS.get(m, "grey") for m in MAPPERS]
            bars = ax.bar(x, vals, color=colors, width=0.72, alpha=0.88)

            if ri == 0:
                ax.set_title(title, fontsize=10)
            if ci == 0:
                ax.set_ylabel(GROUP_LABELS.get(group, str(group)),
                              fontsize=10, fontweight="bold")
            ax.set_xticks(x)
            if ri == nrows - 1:
                ax.set_xticklabels([LABELS[m] for m in MAPPERS],
                                   rotation=30, ha="right", fontsize=7)
            else:
                ax.set_xticklabels([])
            ax.grid(axis="y", linewidth=0.3, alpha=0.6)
            ax.tick_params(labelsize=7)

            if is_pct:
                # Bars from a 0 baseline (honest), but annotate exact values so
                # near-100% bars stay distinguishable.
                ax.set_ylim(0, 108)
                for b, v in zip(bars, vals):
                    ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}",
                            ha="center", va="bottom", fontsize=6)
            else:
                # Log y for time/memory: spans range widely across mappers, same
                # convention as the simulation map_time/peak_rss figures.
                ax.set_yscale("log")
                nz = [v for v in vals if v > 0]
                if nz:
                    ax.set_ylim(min(nz) / 2.0, max(nz) * 2.5)
                for b, v in zip(bars, vals):
                    if v > 0:
                        ax.text(b.get_x() + b.get_width() / 2, v * 1.08,
                                f"{v:.0f}" if v >= 10 else f"{v:.1f}",
                                ha="center", va="bottom", fontsize=6)

    # Single shared legend (mapper → color).
    handles = [plt.Rectangle((0, 0), 1, 1, color=MAPPER_COLORS.get(m, "grey")) for m in MAPPERS]
    fig.legend(handles, [LABELS[m] for m in MAPPERS],
               loc="upper right", fontsize=8, ncol=len(MAPPERS))

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    os.makedirs(PLOTS_DIR, exist_ok=True)
    out = os.path.join(PLOTS_DIR, "real_benchmark")
    fig.savefig(out + ".png", dpi=150, bbox_inches="tight")
    fig.savefig(out + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}.png")


if __name__ == "__main__":
    main()
