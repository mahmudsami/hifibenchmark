#!/usr/bin/env python3
"""
Collect all *_eval.json and *_metrics.json files from results/mappings/
into a single CSV at results/csv/results.csv.

Filename convention:
    {genome}_{mapper}_err{error_rate}_len{read_length}_eval.json
    {genome}_{mapper}_err{error_rate}_len{read_length}_metrics.json
"""
import os, re, json, csv

BENCH_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPINGS_DIR = os.path.join(BENCH_DIR, "results", "mappings")
CSV_DIR      = os.path.join(BENCH_DIR, "results", "csv")

MAPPERS  = {"minimap2", "blend", "mapquik", "strobealign", "syncmer"}
EVAL_PAT = re.compile(
    r"^(?P<genome>.+)_(?P<mapper>minimap2|blend|mapquik|strobealign|syncmer)"
    r"_err(?P<err>[0-9.]+)_len(?P<len>[0-9]+)_eval\.json$"
)

CSV_FIELDS = [
    "genome", "mapper", "error_rate", "error_pct", "read_length",
    "total_reads", "mapped", "unmapped",
    "correct", "wrong_chr", "wrong_pos",
    "accuracy", "precision", "mapping_rate",
    "map_time_s", "wall_time_s", "peak_rss_mb",
]


def main():
    os.makedirs(CSV_DIR, exist_ok=True)

    rows = []
    for fname in sorted(os.listdir(MAPPINGS_DIR)):
        m = EVAL_PAT.match(fname)
        if not m:
            continue

        genome = m.group("genome")
        mapper = m.group("mapper")
        err    = m.group("err")
        rlen   = m.group("len")

        eval_path    = os.path.join(MAPPINGS_DIR, fname)
        metrics_path = os.path.join(MAPPINGS_DIR, fname.replace("_eval.json", "_metrics.json"))

        with open(eval_path) as f:
            eval_data = json.load(f)

        perf = {}
        if os.path.exists(metrics_path):
            with open(metrics_path) as f:
                perf = json.load(f)

        rows.append({
            "genome":       genome,
            "mapper":       mapper,
            "error_rate":   float(err),
            "error_pct":    round(float(err) * 100, 2),
            "read_length":  int(rlen),
            **eval_data,
            "map_time_s":   perf.get("map_time_s"),
            "wall_time_s":  perf.get("wall_time_s"),
            "peak_rss_mb":  perf.get("peak_rss_mb"),
        })

    if not rows:
        print("No eval files found in", MAPPINGS_DIR)
        return

    out_path = os.path.join(CSV_DIR, "results.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Collected {len(rows)} rows → {out_path}")


if __name__ == "__main__":
    main()
