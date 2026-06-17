#!/usr/bin/env python3
"""
Shared layout for the per-metric benchmark plots.

One figure PER METRIC (not per genome). In each figure:
    rows    = error rate
    columns = genome
    x-axis  = read length (kb)     ← same axis convention as the lungfish plot
    lines   = one per mapper
"""
import os, csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH  = os.path.join(BENCH_DIR, "results", "csv", "results.csv")
PLOTS_DIR = os.path.join(BENCH_DIR, "results", "plots")

MAPPER_COLORS = {
    "minimap2": "#1f77b4", "blend": "#ff7f0e",
    "synpact": "#d62728", "mapquik": "#9467bd",
}
MAPPER_LABELS = {
    "minimap2": "minimap2", "blend": "BLEND",
    "synpact": "synpact", "mapquik": "mapquik",
}
MARKERS = {"minimap2": "o", "blend": "s", "synpact": "D", "mapquik": "v"}
GENOME_ORDER = ["human", "human_y", "maize", "arabidopsis", "rye"]


def load_rows():
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"CSV not found: {CSV_PATH}\nRun 06_collect_results.py first.")
    with open(CSV_PATH) as f:
        return list(csv.DictReader(f))


def plot_metric(rows, key, label, pct=False, scale=1.0, logy=False, out_name=None):
    """Render results/plots/<out_name or key>.png for one metric column."""
    data = {}                                   # (genome, err_pct, read_len, mapper) -> value
    genomes, errs, lens, mappers = set(), set(), set(), set()
    for r in rows:
        v = r.get(key)
        if v in (None, ""):
            continue
        g, ep, rl, m = r["genome"], float(r["error_pct"]), int(r["read_length"]), r["mapper"]
        data[(g, ep, rl, m)] = float(v) * scale
        genomes.add(g); errs.add(ep); lens.add(rl); mappers.add(m)
    if not data:
        print(f"  (no data for {key} — skipped)")
        return

    genomes = [g for g in GENOME_ORDER if g in genomes] + sorted(genomes - set(GENOME_ORDER))
    errs    = sorted(errs)
    lens    = sorted(lens)
    mappers = [m for m in MAPPER_COLORS if m in mappers]

    nrows, ncols = len(errs), len(genomes)
    fig, axes = plt.subplots(nrows, ncols, figsize=(2.9 * ncols, 2.5 * nrows),
                             squeeze=False, sharex=True)
    fig.suptitle(f"{label} — error rate (rows) × genome (cols)", fontsize=14, fontweight="bold")

    for ri, ep in enumerate(errs):
        for ci, g in enumerate(genomes):
            ax = axes[ri][ci]
            band = []
            for m in mappers:
                pts = sorted((rl, data[(g, ep, rl, m)]) for rl in lens if (g, ep, rl, m) in data)
                if not pts:
                    continue
                xs = [rl / 1000 for rl, _ in pts]; ys = [y for _, y in pts]; band += ys
                ax.plot(xs, ys, color=MAPPER_COLORS[m], marker=MARKERS.get(m, "o"),
                        markersize=5, linewidth=1.5, label=MAPPER_LABELS.get(m, m))
            if ri == 0:
                ax.set_title(g, fontsize=10)
            if ci == 0:
                ax.set_ylabel(f"{ep:g}% err\n{label}", fontsize=8)
            if ri == nrows - 1:
                ax.set_xlabel("Read length (kb)", fontsize=8)
            ax.grid(True, linewidth=0.3, alpha=0.6, which="both")
            ax.tick_params(labelsize=7)
            if logy:
                ax.set_yscale("log")
            else:
                # show actual values, not matplotlib's "+1e2" offset notation
                # (which made the near-100% precision panels look broken)
                ax.ticklabel_format(axis="y", style="plain", useOffset=False)
                # zoom the % panels to the data band so 99–100 isn't a flat line;
                # cap the top at exactly 100 so no gridline/tick exceeds 100%
                if pct and band:
                    lo = min(band)
                    ax.set_ylim(max(0, lo - (100 - lo) * 0.3 - 0.05), 100.0)

    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=8, ncol=len(mappers))
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    os.makedirs(PLOTS_DIR, exist_ok=True)
    out = os.path.join(PLOTS_DIR, out_name or key)
    fig.savefig(out + ".png", dpi=150, bbox_inches="tight")
    fig.savefig(out + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}.png")
