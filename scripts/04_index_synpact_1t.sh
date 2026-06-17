#!/usr/bin/env bash
# Build the synpact index with a SINGLE thread, ONCE per genome, purely to record
# index-build time + peak RSS for the index-resources plot (the 8-thread build in
# 04_index_synpact.sh is the one actually used for mapping). The 1-thread index is
# identical in content, so it is deleted right after timing — only the metrics are
# kept.
#
# Writes results/mappings/<genome>_synpact1t_index_metrics.json
# Usage: 04_index_synpact_1t.sh <genome>

set -euo pipefail
source "$(dirname "$0")/_runner_lib.sh"

GENOME="$1"

INDEX_HOST="$INDEX_DIR/$GENOME/synpact_1t.idx"
C_INDEX="/bench/data/indexes/$GENOME/synpact_1t.idx"
C_REF="$(container_ref "$GENOME")"
METRICS="$MAPPINGS_DIR/${GENOME}_synpact1t_index_metrics.json"
LOG="$MAPPINGS_DIR/${GENOME}_synpact1t_index.log"

# Resumable: the metrics JSON (not the throwaway index) is the artifact, so skip
# when it already exists. Delete it to re-measure.
if [ -f "$METRICS" ]; then
    echo "synpact 1-thread index metrics exist: $METRICS — skipping (delete to re-measure)."
    exit 0
fi

mkdir -p "$INDEX_DIR/$GENOME"
echo "Building synpact index (1 thread) for $GENOME ..."

python3 "$BENCH_DIR/scripts/run_timed.py" "$METRICS" \
    "${DOCKER_RUN[@]}" hifi-synpact:latest \
        synpact --build-index "$C_REF" "$C_INDEX" --threads 1 \
    > /dev/null 2> "$LOG"

parse_peak "$METRICS" "$LOG"
record_index_size "$METRICS" "$INDEX_HOST"
rm -f "$INDEX_HOST"   # mapping uses the 8-thread synpact.idx; only metrics are kept
echo "synpact 1-thread index metrics saved: $METRICS"
