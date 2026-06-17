#!/usr/bin/env python3
"""
EXTRA lungfish plot: the 0.5 % error-rate slice of the minimap2-vs-synpact
comparison, laid out as a 2x2 grid of metrics (instead of a single vertical
column). x-axis = read length (kb), one line per mapper.

Reads results/lungfish/<genome>_<mapper>_err0.005_len<L>{_eval.json,.log}.

Usage:   python3 scripts/extra_plot_lungfish_err05.py [genome]   # default lungfish_au
Output:  results/lungfish/<genome>_err0.005_2x2.png / .pdf
"""
import os, sys, json, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR   = os.path.join(BENCH_DIR, "results", "lungfish")

ERR     = "0.005"                       # the 0.5 % slice
LENGTHS = [10000, 15000, 20000, 25000]
MAPPERS = ["minimap2", "synpact"]
COLORS  = {"minimap2": "#1f77b4", "synpact": "#d62728"}
MARKERS = {"minimap2": "o", "synpact": "D"}

# (metric_key, label, kind)  kind: pct | log
PANELS = [
    ("accuracy",    "Accuracy (%)",     "pct"),
    ("precision",   "Precision (%)",    "pct"),
    ("map_time_s",  "Mapping time (s)", "log"),
    ("peak_rss_gb", "Peak RSS (GB)",    "log"),
]


def parse_log(path):
    if not os.path.exists(path):
        return None, None
    txt = open(path, errors="replace").read()
    rss = None
    m = re.search(r"(\d+)\s+maximum resident set size", txt)
    if m:
        rss = int(m.group(1)) / 1e9
    else:
        m = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", txt)
        if m:
            rss = int(m.group(1)) * 1024 / 1e9
    t = re.search(r"([\d.]+)\s+real", txt)
    sec = float(t.group(1)) if t else None
    if sec is None:
        t = re.search(r"Elapsed \(wall clock\) time[^\n]*?(\d+):([\d.]+)", txt)
        if t:
            sec = int(t.group(1)) * 60 + float(t.group(2))
    return sec, rss


def load(genome):
    # data[mapper][read_len] = {metric: value}
    data = {m: {} for m in MAPPERS}
    for M in MAPPERS:
        for L in LENGTHS:
            tag = f"err{ERR}_len{L}"
            ev = os.path.join(OUT_DIR, f"{genome}_{M}_{tag}_eval.json")
            if not os.path.exists(ev):
                continue
            d = json.load(open(ev))
            sec, rss = parse_log(os.path.join(OUT_DIR, f"{genome}_{M}_{tag}.log"))
            data[M][L] = {
                "accuracy": d.get("accuracy"), "precision": d.get("precision"),
                "map_time_s": sec, "peak_rss_gb": rss,
            }
    return data


def main():
    genome = sys.argv[1] if len(sys.argv) > 1 else "lungfish_au"
    data = load(genome)
    if not any(data[m] for m in MAPPERS):
        raise SystemExit(f"No err{ERR} results in {OUT_DIR} for '{genome}'. Run the sweep first.")

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    fig.suptitle(f"{genome}: minimap2 (k28/w200) vs synpact @ {float(ERR)*100:g}% error",
                 fontsize=14, fontweight="bold")

    for ax, (key, label, kind) in zip(axes.flat, PANELS):
        band = []
        for M in MAPPERS:
            pts = sorted((L, data[M][L][key]) for L in LENGTHS
                         if L in data[M] and data[M][L].get(key) is not None)
            if not pts:
                continue
            xs = [L / 1000 for L, _ in pts]; ys = [v for _, v in pts]; band += ys
            ax.plot(xs, ys, color=COLORS[M], marker=MARKERS[M], markersize=6,
                    linewidth=1.8, label=M)
        ax.set_title(label, fontsize=11)
        ax.set_xlabel("Read length (kb)", fontsize=9)
        ax.grid(True, linewidth=0.3, alpha=0.6, which="both")
        ax.tick_params(labelsize=8)
        if kind == "log":
            ax.set_yscale("log")
        elif kind == "pct" and band:
            ax.ticklabel_format(axis="y", style="plain", useOffset=False)
            lo = min(band)
            ax.set_ylim(max(0, lo - (100 - lo) * 0.3 - 0.05), 100.0)

    axes.flat[0].legend(fontsize=9, loc="lower left")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"{genome}_err{ERR}_2x2")
    fig.savefig(out + ".png", dpi=150, bbox_inches="tight")
    fig.savefig(out + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}.png")


if __name__ == "__main__":
    main()
