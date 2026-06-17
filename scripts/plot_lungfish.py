#!/usr/bin/env python3
"""
Plot the synpact lungfish sweep (results/lungfish/).

Reads, per error_rate x read_length combo:
    results/lungfish/<genome>_err<E>_len<L>_eval.json     (accuracy/precision/mapping_rate)
    results/lungfish/<genome>_map_err<E>_len<L>.log       (map time + peak RSS, time -l or -v)

Produces a 2x2 figure (Accuracy, Precision, Mapping rate, Mapping time), x-axis =
error rate (%), one line per read length. Peak RSS is reported in the suptitle
(it's flat across combos — dominated by loading the index).

Usage:
    python3 scripts/plot_lungfish.py [genome]      # default: lungfish_au
Output:
    results/lungfish/<genome>_sweep.png  and  .pdf
"""
import os, sys, json, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR   = os.path.join(BENCH_DIR, "results", "lungfish")

ERRORS  = ["0", "0.001", "0.005", "0.01"]            # fraction tokens (filenames)
LENGTHS = [10000, 15000, 20000, 25000]
# one line per error rate (x-axis = read length); keyed by error percent
ERR_COLORS = {0.0: "#1f77b4", 0.1: "#2ca02c", 0.5: "#ff7f0e", 1.0: "#d62728"}

PANELS = [
    ("accuracy",    "Accuracy (%)"),
    ("precision",   "Precision (%)"),
    ("peak_rss_gb", "Peak RSS (GB)"),
    ("map_time_s",  "Mapping time (s)"),
]


def parse_map_log(path):
    """Return (map_time_s, peak_rss_gb) from a `/usr/bin/time -l` (macOS) or
    `-v` (GNU) log; missing values come back as None."""
    if not os.path.exists(path):
        return None, None
    txt = open(path, errors="replace").read()
    # peak RSS — macOS: "<bytes> maximum resident set size"; GNU: "Maximum resident set size (kbytes): N"
    rss = None
    m = re.search(r"(\d+)\s+maximum resident set size", txt)
    if m:
        rss = int(m.group(1)) / 1e9
    else:
        m = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", txt)
        if m:
            rss = int(m.group(1)) * 1024 / 1e9
    # wall time — macOS: "X.XX real"; GNU: "Elapsed (wall clock) time ... m:ss"
    sec = None
    m = re.search(r"([\d.]+)\s+real", txt)
    if m:
        sec = float(m.group(1))
    else:
        m = re.search(r"Elapsed \(wall clock\) time[^\n]*?(\d+):([\d.]+)", txt)
        if m:
            sec = int(m.group(1)) * 60 + float(m.group(2))
    return sec, rss


def load(genome):
    """data[length][error_pct] = {metric: value}; plus list of peak RSS seen."""
    data = {L: {} for L in LENGTHS}
    rss_all = []
    for E in ERRORS:
        for L in LENGTHS:
            tag = f"err{E}_len{L}"
            ev_path = os.path.join(OUT_DIR, f"{genome}_{tag}_eval.json")
            if not os.path.exists(ev_path):
                continue
            ev = json.load(open(ev_path))
            sec, rss = parse_map_log(os.path.join(OUT_DIR, f"{genome}_map_{tag}.log"))
            if rss is not None:
                rss_all.append(rss)
            data[L][float(E) * 100] = {
                "accuracy":    ev.get("accuracy"),
                "precision":   ev.get("precision"),
                "map_time_s":  sec,
                "peak_rss_gb": rss,
            }
    return data, rss_all


def main():
    genome = sys.argv[1] if len(sys.argv) > 1 else "lungfish_au"
    data, rss_all = load(genome)
    if not any(data[L] for L in LENGTHS):
        raise SystemExit(f"No results found in {OUT_DIR} for genome '{genome}'. Run the sweep first.")

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    fig.suptitle(f"synpact on {genome} — sweep", fontsize=14, fontweight="bold")

    for ax, (key, label) in zip(axes.flat, PANELS):
        all_vals = []
        for E in ERRORS:
            ep = float(E) * 100
            pts = sorted((L, data[L][ep][key]) for L in LENGTHS
                         if ep in data[L] and data[L][ep].get(key) is not None)
            if not pts:
                continue
            xs = [L / 1000 for L, _ in pts]; ys = [v for _, v in pts]
            all_vals += ys
            ax.plot(xs, ys, marker="o", linewidth=1.8, markersize=6,
                    color=ERR_COLORS[ep], label=f"{ep:g}%")
        ax.set_xlabel("Read length (kb)")
        ax.set_ylabel(label)
        ax.grid(True, linewidth=0.4, alpha=0.6)
        # zoom the % panels to the data band so 99.7–100 isn't a flat line at the top
        if key in ("accuracy", "precision") and all_vals:
            lo = min(all_vals)
            ax.set_ylim(max(0, lo - (100 - lo) * 0.3 - 0.05), 100.0)
            ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    axes.flat[0].legend(title="Error rate", fontsize=8, loc="lower left")

    plt.tight_layout()
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"{genome}_sweep")
    fig.savefig(out + ".png", dpi=150, bbox_inches="tight")
    fig.savefig(out + ".pdf", bbox_inches="tight")
    print(f"Saved: {out}.png / .pdf")


if __name__ == "__main__":
    main()
