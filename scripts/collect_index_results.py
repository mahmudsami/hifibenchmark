#!/usr/bin/env python3
"""
Collect index-BUILD time and memory into results/csv/index_results.csv.

For every mapper that builds a real index (minimap2, blend, synpact
— NOT mapquik, which indexes inline), the 04_index_*.sh scripts write
    results/mappings/<genome>_<mapper>_index_metrics.json   {wall_time_s, peak_rss_mb}
This gathers them, adds the on-disk index size, and writes one table:
    genome, mapper, index_time_s, index_peak_rss_mb, index_size_mb
"""
import os, re, json, csv

BENCH_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPINGS_DIR = os.path.join(BENCH_DIR, "results", "mappings")
INDEX_DIR    = os.path.join(BENCH_DIR, "data", "indexes")
REFS_DIR     = os.path.join(BENCH_DIR, "data", "references")
CSV_DIR      = os.path.join(BENCH_DIR, "results", "csv")

INDEX_MAPPERS = ["minimap2", "blend", "synpact"]   # mapquik excluded
PAT = re.compile(r"^(?P<genome>.+)_(?P<mapper>minimap2|blend|synpact)_index_metrics\.json$")


def index_size_mb(genome, mapper):
    """On-disk index size in MB (None if absent)."""
    candidates = {
        "minimap2":    [os.path.join(INDEX_DIR, genome, "minimap2_maphifi.mmi")],
        "blend":       [os.path.join(INDEX_DIR, genome, "blend_maphifi.bl")],
        "synpact":     [os.path.join(INDEX_DIR, genome, "synpact.idx")],
    }.get(mapper, [])
    total = sum(os.path.getsize(p) for p in candidates if os.path.exists(p))
    return round(total / 1024 / 1024, 1) if total else None


def main():
    os.makedirs(CSV_DIR, exist_ok=True)
    rows = []
    for fname in sorted(os.listdir(MAPPINGS_DIR)) if os.path.isdir(MAPPINGS_DIR) else []:
        m = PAT.match(fname)
        if not m:
            continue
        genome, mapper = m.group("genome"), m.group("mapper")
        with open(os.path.join(MAPPINGS_DIR, fname)) as f:
            d = json.load(f)
        # Prefer the size stamped at build time (the index may since have been
        # deleted to bound disk); fall back to measuring it on disk if present.
        size_mb = d.get("index_size_mb")
        if size_mb is None:
            size_mb = index_size_mb(genome, mapper)
        rows.append({
            "genome":            genome,
            "mapper":            mapper,
            "index_time_s":      d.get("wall_time_s"),
            "index_peak_rss_mb": d.get("peak_rss_mb"),
            "index_size_mb":     size_mb,
        })

    rows.sort(key=lambda r: (r["genome"], INDEX_MAPPERS.index(r["mapper"])
                             if r["mapper"] in INDEX_MAPPERS else 99))
    out = os.path.join(CSV_DIR, "index_results.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["genome", "mapper", "index_time_s",
                                          "index_peak_rss_mb", "index_size_mb"])
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} index rows → {out}")
    if rows:
        print(f"  {'genome':<12} {'mapper':<11} {'time_s':>8} {'rss_mb':>9} {'size_mb':>9}")
        for r in rows:
            print(f"  {r['genome']:<12} {r['mapper']:<11} "
                  f"{str(r['index_time_s']):>8} {str(r['index_peak_rss_mb']):>9} {str(r['index_size_mb']):>9}")


if __name__ == "__main__":
    main()
