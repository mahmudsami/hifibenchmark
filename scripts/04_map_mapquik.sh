#!/usr/bin/env bash
# Map reads with mapquik against the prepared single-line reference, recording
# wall time and peak RSS.
#
# NOTE: unlike the other mappers, mapquik has no serialized index — it rebuilds
# its k-min-mer index in memory at every run. So its peak RSS NECESSARILY
# includes index construction; this is "mapping-only" only in the sense of using
# the correctly-formatted reference (see 04_index_mapquik.sh). The 04_index_/
# 04_map_ split is kept for naming symmetry with the other tools.
#
# Usage: 04_map_mapquik.sh <genome> <error_rate> <read_length>

set -euo pipefail
source "$(dirname "$0")/_runner_lib.sh"

GENOME="$1"; ERR="$2"; LEN="$3"
TAG="err${ERR}_len${LEN}"

MQ_REF_HOST="$INDEX_DIR/$GENOME/genome.mapquik.fa.gz"
C_REF="/bench/data/indexes/$GENOME/genome.mapquik.fa.gz"
OUT_PAF="$MAPPINGS_DIR/${GENOME}_mapquik_${TAG}.paf"
METRICS="$MAPPINGS_DIR/${GENOME}_mapquik_${TAG}_metrics.json"
LOG="$MAPPINGS_DIR/${GENOME}_mapquik_${TAG}.log"
C_PREFIX="/bench/results/mappings/${GENOME}_mapquik_${TAG}"
C_READS="$(container_reads "$GENOME" "$TAG")"

if [ ! -f "$MQ_REF_HOST" ]; then
    echo "Missing reference $MQ_REF_HOST — run: 04_index_mapquik.sh $GENOME" >&2
    exit 1
fi
if [ -f "$OUT_PAF" ]; then
    echo "Already mapped: $OUT_PAF — skipping."
    exit 0
fi

echo "Mapping mapquik (single-line reference): genome=$GENOME err=$ERR len=$LEN"

# mapquik writes <prefix>.paf itself; its logs (incl. "Maximum RSS") go to LOG.
python3 "$BENCH_DIR/scripts/run_timed.py" "$METRICS" \
    "${DOCKER_RUN[@]}" hifi-mapquik:latest \
        "$C_READS" \
        --reference "$C_REF" \
        --threads "$THREADS" \
        --prefix "$C_PREFIX" \
    > "$LOG" 2>&1

parse_peak "$METRICS" "$LOG"
echo "Done: $OUT_PAF"
