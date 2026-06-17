#!/usr/bin/env bash
# Shared helpers for the separated index/map runner scripts (04_index_* / 04_map_*).
#
# These split the original 04_run_* scripts into two phases so that the mapping
# phase's peak RSS reflects ONLY mapping (loading a pre-built index + aligning),
# not index construction. Build the index once with an 04_index_* script, then
# map any number of read sets with the matching 04_map_* script.
#
# Source this after setting nothing; it pulls in config.sh itself.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/config.sh"

# Common `docker run` prefix (host $BENCH_DIR is mounted at /bench).
DOCKER_RUN=(docker run --rm --platform linux/amd64 -v "${BENCH_DIR}:/bench")

# container_reads <genome> <tag> -> echoes the in-container reads path (prefers .gz)
container_reads() {
    local genome="$1" tag="$2"
    if [ -f "$READS_DIR/$genome/${tag}.fastq.gz" ]; then
        echo "/bench/data/reads/$genome/${tag}.fastq.gz"
    else
        echo "/bench/data/reads/$genome/${tag}.fastq"
    fi
}

# In-container reference path for a genome.
container_ref() {
    echo "/bench/data/references/$1/genome.fa.gz"
}

# Patch a metrics JSON's peak_rss_mb with the true in-container value from a log.
parse_peak() {
    python3 "$BENCH_DIR/scripts/parse_peak_rss.py" "$1" "$2"
}

# record_index_size <metrics_json> <path-or-glob>...
# Stamp the on-disk index size (MB) into the metrics JSON right after building,
# so the index can be deleted later (to bound peak disk) without losing
# index_size_mb — collect_index_results.py reads it back from the JSON.
record_index_size() {
    local metrics="$1"; shift
    python3 - "$metrics" "$@" <<'PY'
import sys, os, glob, json
metrics = sys.argv[1]
total = 0
for pat in sys.argv[2:]:
    for p in glob.glob(pat):
        if os.path.isfile(p):
            total += os.path.getsize(p)
if not os.path.exists(metrics):
    sys.exit(0)
with open(metrics) as f:
    d = json.load(f)
d["index_size_mb"] = round(total / 1024 / 1024, 1) if total else None
with open(metrics, "w") as f:
    json.dump(d, f, indent=2)
print(f"  index_size_mb ← {d['index_size_mb']}")
PY
}
