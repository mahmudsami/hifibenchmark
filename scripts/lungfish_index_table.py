#!/usr/bin/env python3
"""
Build the lungfish index-time/memory table from the index-build logs that
lungfish_synpact_test.sh / lungfish_mm_sweep.sh write under results/lungfish/.

Scans results/lungfish/ for index logs (or *_index_metrics.json), extracts
index build time + peak RSS (GNU `time -v` or macOS `time -l`), adds the on-disk
index size, and writes results/lungfish/<genome>_index_results.csv.

Usage: python3 scripts/lungfish_index_table.py [genome]   # default lungfish_au
"""
import os, re, sys, csv, json, glob

BENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR   = os.path.join(BENCH_DIR, "results", "lungfish")
INDEX_DIR = os.path.join(BENCH_DIR, "data", "indexes")


def parse_time(txt):
    """(seconds, peak_rss_gb) from a time -l (macOS) or time -v (GNU) log."""
    rss = None
    m = re.search(r"(\d+)\s+maximum resident set size", txt) or \
        re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", txt)
    if m:
        rss = int(m.group(1)) / 1e9 if "kbytes" not in txt else int(m.group(1)) * 1024 / 1e9
    sec = None
    m = re.search(r"([\d.]+)\s+real", txt) or re.search(r"Real time:\s*([\d.]+)", txt)
    if m:
        sec = float(m.group(1))
    else:
        m = re.search(r"Elapsed \(wall clock\) time[^\n]*?(\d+):([\d.]+)", txt)
        if m:
            sec = int(m.group(1)) * 60 + float(m.group(2))
    return sec, rss


def index_size_gb(genome, mapper):
    pats = {
        "synpact":  [os.path.join(INDEX_DIR, genome, "synpact.idx")],
        "minimap2": glob.glob(os.path.join(INDEX_DIR, genome, "minimap2_*.mmi")),
    }.get(mapper, [])
    tot = sum(os.path.getsize(p) for p in pats if os.path.exists(p))
    return round(tot / 1e9, 2) if tot else None


def metric_for(genome, mapper):
    """Prefer a saved *_index_metrics.json; else parse a matching index log."""
    j = os.path.join(OUT_DIR, f"{genome}_{mapper}_index_metrics.json")
    if os.path.exists(j):
        d = json.load(open(j))
        sec = d.get("index_time_s") or d.get("wall_time_s")
        rss = d.get("peak_rss_mb")
        return sec, (rss / 1000 if rss else None)        # mb (decimal) → gb
    logs = glob.glob(os.path.join(OUT_DIR, f"{genome}_{mapper}*index*.log"))
    if mapper == "synpact" and not logs:
        logs = glob.glob(os.path.join(OUT_DIR, f"{genome}_index.log"))
    if logs:
        return parse_time(open(logs[0], errors="replace").read())
    return None, None


def main():
    genome = sys.argv[1] if len(sys.argv) > 1 else "lungfish_au"
    rows = []
    for mapper in ("minimap2", "synpact"):
        sec, rss = metric_for(genome, mapper)
        if sec is None and rss is None:
            continue
        rows.append({
            "mapper": mapper,
            "index_time_s": round(sec, 1) if sec else None,
            "index_peak_rss_gb": round(rss, 2) if rss else None,
            "index_size_gb": index_size_gb(genome, mapper),
        })
    if not rows:
        raise SystemExit(f"No index logs/metrics found in {OUT_DIR} for {genome}.")
    out = os.path.join(OUT_DIR, f"{genome}_index_results.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["mapper", "index_time_s", "index_peak_rss_gb", "index_size_gb"])
        w.writeheader(); w.writerows(rows)
    print(f"Wrote {len(rows)} rows → {out}")
    for r in rows:
        print(f"  {r['mapper']:<10} time={r['index_time_s']}s  rss={r['index_peak_rss_gb']}GB  size={r['index_size_gb']}GB")


if __name__ == "__main__":
    main()
