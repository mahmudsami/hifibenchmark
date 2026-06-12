#!/usr/bin/env bash
# Build (and time) a minimap2 map-hifi index, ONCE per genome.
# The matching mapper (04_map_minimap2.sh) loads this index, so its peak RSS
# reflects mapping only — not index construction.
#
# Usage: 04_index_minimap2.sh <genome>

set -euo pipefail
source "$(dirname "$0")/_runner_lib.sh"

GENOME="$1"

INDEX_HOST="$INDEX_DIR/$GENOME/minimap2_maphifi.mmi"
C_INDEX="/bench/data/indexes/$GENOME/minimap2_maphifi.mmi"
C_REF="$(container_ref "$GENOME")"
METRICS="$MAPPINGS_DIR/${GENOME}_minimap2_index_metrics.json"
LOG="$MAPPINGS_DIR/${GENOME}_minimap2_index.log"

if [ -f "$INDEX_HOST" ]; then
    echo "Index exists: $INDEX_HOST — skipping (delete to rebuild)."
    exit 0
fi

mkdir -p "$INDEX_DIR/$GENOME"
echo "Building minimap2 map-hifi index for $GENOME ..."

python3 "$BENCH_DIR/scripts/run_timed.py" "$METRICS" \
    "${DOCKER_RUN[@]}" hifi-minimap2:latest \
        minimap2 -x map-hifi -t "$THREADS" -d "$C_INDEX" "$C_REF" \
    > /dev/null 2> "$LOG"

parse_peak "$METRICS" "$LOG"
echo "Index saved: $INDEX_HOST"
