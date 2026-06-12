#!/usr/bin/env bash
# Build (and time) the syncmer-hifi index, ONCE per genome. 04_map_syncmer.sh
# loads it so its peak RSS reflects mapping only — not index construction.
#
# Usage: 04_index_syncmer.sh <genome>

set -euo pipefail
source "$(dirname "$0")/_runner_lib.sh"

GENOME="$1"

INDEX_HOST="$INDEX_DIR/$GENOME/syncmer_hifi.idx"
C_INDEX="/bench/data/indexes/$GENOME/syncmer_hifi.idx"
C_REF="$(container_ref "$GENOME")"
METRICS="$MAPPINGS_DIR/${GENOME}_syncmer_index_metrics.json"
LOG="$MAPPINGS_DIR/${GENOME}_syncmer_index.log"

if [ -f "$INDEX_HOST" ]; then
    echo "Index exists: $INDEX_HOST — skipping (delete to rebuild)."
    exit 0
fi

mkdir -p "$INDEX_DIR/$GENOME"
echo "Building syncmer-hifi index for $GENOME ..."

python3 "$BENCH_DIR/scripts/run_timed.py" "$METRICS" \
    "${DOCKER_RUN[@]}" hifi-syncmer-hifi:latest \
        syncmer-hifi --build-index "$C_REF" "$C_INDEX" --threads "$THREADS" \
    > /dev/null 2> "$LOG"

parse_peak "$METRICS" "$LOG"
echo "Index saved: $INDEX_HOST"
