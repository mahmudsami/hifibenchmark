#!/usr/bin/env bash
# Build (and time) a BLEND map-hifi index, ONCE per genome.
# The matching mapper (04_map_blend.sh) loads this index so its peak RSS
# reflects mapping only — not index construction.
#
# Usage: 04_index_blend.sh <genome>

set -euo pipefail
source "$(dirname "$0")/_runner_lib.sh"

GENOME="$1"

INDEX_HOST="$INDEX_DIR/$GENOME/blend_maphifi.bl"
C_INDEX="/bench/data/indexes/$GENOME/blend_maphifi.bl"
C_REF="$(container_ref "$GENOME")"
METRICS="$MAPPINGS_DIR/${GENOME}_blend_index_metrics.json"
LOG="$MAPPINGS_DIR/${GENOME}_blend_index.log"

if [ -f "$INDEX_HOST" ]; then
    echo "Index exists: $INDEX_HOST — skipping (delete to rebuild)."
    exit 0
fi

mkdir -p "$INDEX_DIR/$GENOME"
echo "Building BLEND map-hifi index for $GENOME ..."

# BLEND is a minimap2 derivative: -d dumps the index and exits.
python3 "$BENCH_DIR/scripts/run_timed.py" "$METRICS" \
    "${DOCKER_RUN[@]}" hifi-blend:latest \
        -x map-hifi -t "$THREADS" -d "$C_INDEX" "$C_REF" \
    > /dev/null 2> "$LOG"

parse_peak "$METRICS" "$LOG"
echo "Index saved: $INDEX_HOST"
