#!/usr/bin/env bash
# Map reads with minimap2 against a PRE-BUILT index, recording wall time and the
# mapping-only peak RSS (index construction is excluded — see 04_index_minimap2.sh).
#
# Usage: 04_map_minimap2.sh <genome> <error_rate> <read_length>

set -euo pipefail
source "$(dirname "$0")/_runner_lib.sh"

GENOME="$1"; ERR="$2"; LEN="$3"
TAG="err${ERR}_len${LEN}"

INDEX_HOST="$INDEX_DIR/$GENOME/minimap2_maphifi.mmi"
C_INDEX="/bench/data/indexes/$GENOME/minimap2_maphifi.mmi"
OUT_PAF="$MAPPINGS_DIR/${GENOME}_minimap2_${TAG}.paf"
METRICS="$MAPPINGS_DIR/${GENOME}_minimap2_${TAG}_metrics.json"
LOG="$MAPPINGS_DIR/${GENOME}_minimap2_${TAG}.log"
C_READS="$(container_reads "$GENOME" "$TAG")"

# Already mapped → skip before requiring the index. The index is deleted after
# mapping to save disk, so on a completed re-run it is legitimately absent; a
# present PAF means the work is done regardless.
if [ -f "$OUT_PAF" ]; then
    echo "Already mapped: $OUT_PAF — skipping."
    exit 0
fi
if [ ! -f "$INDEX_HOST" ]; then
    echo "Missing index $INDEX_HOST — run: 04_index_minimap2.sh $GENOME" >&2
    exit 1
fi

echo "Mapping minimap2 (pre-built index): genome=$GENOME err=$ERR len=$LEN"

# Passing the .mmi (not the FASTA) makes minimap2 load the index instead of
# building it, so /usr/bin/time -v's peak RSS is the mapping-phase footprint.
python3 "$BENCH_DIR/scripts/run_timed.py" "$METRICS" \
    "${DOCKER_RUN[@]}" hifi-minimap2:latest \
        minimap2 -x map-hifi --secondary=no -t "$THREADS" "$C_INDEX" "$C_READS" \
    > "$OUT_PAF" 2> "$LOG"

parse_peak "$METRICS" "$LOG"
echo "Done: $OUT_PAF"
