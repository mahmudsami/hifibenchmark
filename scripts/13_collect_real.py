#!/usr/bin/env python3
"""
Collect the real-data (consensus-eval) results into results/csv/results_real.csv.

Reads, per genome × mapper:
    results/mappings/<genome>_<mapper>_errreal_len100k_eval.json
    results/mappings/<genome>_<mapper>_errreal_len100k_metrics.json
"""
import os, json, csv

BENCH_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPINGS_DIR = os.path.join(BENCH_DIR, "results", "mappings")
CSV_DIR      = os.path.join(BENCH_DIR, "results", "csv")
GENOMES      = ["human", "maize", "arabidopsis", "rye"]
MAPPERS      = ["minimap2", "blend", "strobealign", "strobeclust", "syncmer", "mapquik"]

# Each entry: (genome, readset_label, tag)
# rye has two readsets: standard HiFi and DeepConsensus
READSETS = (
    [(g, "hifi", "errreal_len100k") for g in GENOMES]
    + [("rye", "deepconsensus", "errdc_len100k")]
)

FIELDS = [
    "genome", "readset", "mapper",
    "total_reads", "consensus_reads", "mapped", "mapped_in_consensus", "correct",
    "accuracy", "precision", "mapping_rate",
    "map_time_s", "wall_time_s", "peak_rss_mb",
]


def main():
    os.makedirs(CSV_DIR, exist_ok=True)
    rows = []
    for genome, readset, tag in READSETS:
        for mapper in MAPPERS:
            eval_path    = os.path.join(MAPPINGS_DIR, f"{genome}_{mapper}_{tag}_eval.json")
            metrics_path = os.path.join(MAPPINGS_DIR, f"{genome}_{mapper}_{tag}_metrics.json")
            if not os.path.exists(eval_path):
                continue
            with open(eval_path) as f:
                ev = json.load(f)
            perf = {}
            if os.path.exists(metrics_path):
                with open(metrics_path) as f:
                    perf = json.load(f)
            rows.append({
                "genome": genome, "readset": readset, "mapper": mapper,
                **{k: ev.get(k) for k in (
                    "total_reads", "consensus_reads", "mapped", "mapped_in_consensus",
                    "correct", "accuracy", "precision", "mapping_rate")},
                "map_time_s":  perf.get("map_time_s"),
                "wall_time_s": perf.get("wall_time_s"),
                "peak_rss_mb": perf.get("peak_rss_mb"),
            })

    if not rows:
        print("No real-data eval files found.")
        return

    out_path = os.path.join(CSV_DIR, "results_real.csv")
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"Collected {len(rows)} rows → {out_path}")


if __name__ == "__main__":
    main()
