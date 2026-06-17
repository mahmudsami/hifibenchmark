#!/usr/bin/env bash
# Map reads with synpact against the PRE-BUILT index, recording wall time
# and the mapping-only peak RSS (index construction excluded — see
# 04_index_synpact.sh).
#
# Usage: 04_map_synpact.sh <genome> <error_rate> <read_length>

set -euo pipefail
source "$(dirname "$0")/_runner_lib.sh"

GENOME="$1"; ERR="$2"; LEN="$3"
MAPPER="synpact"
TAG="err${ERR}_len${LEN}"

INDEX_HOST="$INDEX_DIR/$GENOME/synpact.idx"
C_INDEX="/bench/data/indexes/$GENOME/synpact.idx"
OUT_PAF="$MAPPINGS_DIR/${GENOME}_${MAPPER}_${TAG}.paf"
C_OUT_PAF="/bench/results/mappings/${GENOME}_${MAPPER}_${TAG}.paf"
METRICS="$MAPPINGS_DIR/${GENOME}_${MAPPER}_${TAG}_metrics.json"
LOG="$MAPPINGS_DIR/${GENOME}_${MAPPER}_${TAG}.log"
C_READS="$(container_reads "$GENOME" "$TAG")"

# Already mapped → skip before requiring the index. The index is deleted after
# mapping to save disk, so on a completed re-run it is legitimately absent; a
# present PAF means the work is done regardless.
if [ -f "$OUT_PAF" ]; then
    echo "Already mapped: $OUT_PAF — skipping."
    exit 0
fi
if [ ! -f "$INDEX_HOST" ]; then
    echo "Missing index $INDEX_HOST — run: 04_index_synpact.sh $GENOME" >&2
    exit 1
fi

echo "Mapping synpact (pre-built index): genome=$GENOME err=$ERR len=$LEN"

python3 "$BENCH_DIR/scripts/run_timed.py" "$METRICS" \
    "${DOCKER_RUN[@]}" hifi-synpact:latest \
        synpact --map "$C_READS" "$C_INDEX" -o "$C_OUT_PAF" \
            --threads "$THREADS" \
    > /dev/null 2> "$LOG"

parse_peak "$METRICS" "$LOG"
echo "Done: $OUT_PAF"
