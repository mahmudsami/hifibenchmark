#!/usr/bin/env python3
"""
Compare minimap2 vs synpact on the lungfish sweep (results/lungfish/).

Reads, per mapper × error_rate × read_length:
    results/lungfish/<genome>_<mapper>_err<E>_len<L>_eval.json   (accuracy/precision/mapping_rate)
    results/lungfish/<genome>_<mapper>_err<E>_len<L>.log         (map time + peak RSS; time -l or -v)

One figure: rows = metric (accuracy, precision, mapping time, peak RSS),
cols = error rate, x-axis = read length (kb), one line per mapper.

Usage:  python3 scripts/plot_lungfish_compare.py [genome]   # default lungfish_au
Output: results/lungfish/<genome>_minimap2_vs_synpact.png / .pdf
"""
import os, sys, json, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR   = os.path.join(BENCH_DIR, "results", "lungfish")

ERRORS  = ["0", "0.001", "0.005", "0.01"]
LENGTHS = [10000, 15000, 20000, 25000]
MAPPERS = ["minimap2", "synpact"]
COLORS  = {"minimap2": "#1f77b4", "synpact": "#d62728"}
MARKERS = {"minimap2": "o", "synpact": "D"}

# (metric_key, label, kind)  kind: "pct" (cap 100, zoom) | "log" (log y)
PANELS = [
    ("accuracy",     "Accuracy (%)",     "pct"),
    ("precision",    "Precision (%)",    "pct"),
    ("map_time_s",   "Mapping time (s)", "log"),
    ("peak_rss_gb",  "Peak RSS (GB)",    "log"),
]


def parse_log(path):
    if not os.path.exists(path):
        return None, None
    txt = open(path, errors="replace").read()
    m = re.search(r"(\d+)\s+maximum resident set size", txt) or \
        re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", txt)
    rss = None
    if m:
        rss = int(m.group(1)) / 1e9 if "kbytes" not in txt else int(m.group(1)) * 1024 / 1e9
    t = re.search(r"([\d.]+)\s+real", txt)
    sec = float(t.group(1)) if t else None
    if sec is None:
        t = re.search(r"Elapsed \(wall clock\) time[^\n]*?(\d+):([\d.]+)", txt)
        if t:
            sec = int(t.group(1)) * 60 + float(t.group(2))
    return sec, rss


def load(genome):
    # data[mapper][err_pct][read_len] = {metric: value}
    data = {m: {} for m in MAPPERS}
    for M in MAPPERS:
        for E in ERRORS:
            for L in LENGTHS:
                tag = f"err{E}_len{L}"
                ev = os.path.join(OUT_DIR, f"{genome}_{M}_{tag}_eval.json")
                if not os.path.exists(ev):
                    continue
                d = json.load(open(ev))
                sec, rss = parse_log(os.path.join(OUT_DIR, f"{genome}_{M}_{tag}.log"))
                data[M].setdefault(float(E) * 100, {})[L] = {
                    "accuracy": d.get("accuracy"), "precision": d.get("precision"),
                    "mapping_rate": d.get("mapping_rate"), "map_time_s": sec, "peak_rss_gb": rss,
                }
    return data


def main():
    genome = sys.argv[1] if len(sys.argv) > 1 else "lungfish_au"
    data = load(genome)
    if not any(data[m] for m in MAPPERS):
        raise SystemExit(f"No results in {OUT_DIR} for '{genome}'. Run the sweep first.")
    errs = sorted({ep for m in MAPPERS for ep in data[m]})

    nrows, ncols = len(PANELS), len(errs)
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.0 * ncols, 2.6 * nrows), squeeze=False, sharex=True)
    fig.suptitle(f"{genome}: minimap2 (k28/w200) vs synpact", fontsize=14, fontweight="bold")

    for ri, (key, label, kind) in enumerate(PANELS):
        for ci, ep in enumerate(errs):
            ax = axes[ri][ci]
            band = []
            for M in MAPPERS:
                pts = sorted((L, data[M].get(ep, {}).get(L, {}).get(key))
                             for L in LENGTHS if data[M].get(ep, {}).get(L, {}).get(key) is not None)
                if not pts:
                    continue
                xs = [L / 1000 for L, _ in pts]; ys = [v for _, v in pts]; band += ys
                ax.plot(xs, ys, color=COLORS[M], marker=MARKERS[M], markersize=5, linewidth=1.6, label=M)
            if ri == 0:
                ax.set_title(f"{ep:g}% error", fontsize=10)
            if ci == 0:
                ax.set_ylabel(label, fontsize=9)
            if ri == nrows - 1:
                ax.set_xlabel("Read length (kb)", fontsize=8)
            ax.grid(True, linewidth=0.3, alpha=0.6, which="both")
            ax.tick_params(labelsize=7)
            if kind == "log":
                ax.set_yscale("log")
            elif kind == "pct" and band:
                ax.ticklabel_format(axis="y", style="plain", useOffset=False)
                lo = min(band)
                ax.set_ylim(max(0, lo - (100 - lo) * 0.3 - 0.05), 100.0)

    h, l = axes[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper right", fontsize=9)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(OUT_DIR, f"{genome}_minimap2_vs_synpact")
    fig.savefig(out + ".png", dpi=150, bbox_inches="tight")
    fig.savefig(out + ".pdf", bbox_inches="tight")
    print(f"Saved: {out}.png")


if __name__ == "__main__":
    main()
