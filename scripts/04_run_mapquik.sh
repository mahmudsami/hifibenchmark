#!/usr/bin/env bash
# Map reads with mapquik via Docker (linux/amd64 image), record wall time and peak RSS.
#
# Usage: 04_run_mapquik.sh <genome> <error_rate> <read_length>
#
# Prerequisites:
#   - build the image once:  bash docker/build_images.sh
#   - prepare the reference:  04_index_mapquik.sh <genome>   (done here if missing)
#
# IMPORTANT: mapquik needs a single-line, uppercase FASTA — feeding it the stock
# multi-line, soft-masked genome.fa.gz silently drops the mapping rate to ~1%.
# We therefore map against the prepared data/indexes/<g>/genome.mapquik.fa.gz.

set -euo pipefail
source "$(dirname "$0")/../config.sh"

GENOME="$1"
ERR="$2"
LEN="$3"

TAG="err${ERR}_len${LEN}"
OUT_PAF="$MAPPINGS_DIR/${GENOME}_mapquik_${TAG}.paf"
METRICS="$MAPPINGS_DIR/${GENOME}_mapquik_${TAG}_metrics.json"

if [ -f "$OUT_PAF" ]; then
    echo "Already mapped: $OUT_PAF — skipping."
    exit 0
fi

# Ensure the single-line uppercase reference exists (build it once if needed).
MQ_REF_HOST="$INDEX_DIR/$GENOME/genome.mapquik.fa.gz"
if [ ! -f "$MQ_REF_HOST" ]; then
    bash "$BENCH_DIR/scripts/04_index_mapquik.sh" "$GENOME"
fi

# Translate host paths to in-container paths (/bench mirrors $BENCH_DIR)
C_REF="/bench/data/indexes/$GENOME/genome.mapquik.fa.gz"
if [ -f "$READS_DIR/$GENOME/${TAG}.fastq.gz" ]; then
    C_READS="/bench/data/reads/$GENOME/${TAG}.fastq.gz"
else
    C_READS="/bench/data/reads/$GENOME/${TAG}.fastq"
fi
# mapquik writes <prefix>.paf itself (not stdout); prefix = OUT_PAF without .paf
C_PREFIX="/bench/results/mappings/${GENOME}_mapquik_${TAG}"
LOG="$MAPPINGS_DIR/${GENOME}_mapquik_${TAG}.log"   # container logs (have "Maximum RSS")

echo "Running mapquik (Docker): genome=$GENOME err=$ERR len=$LEN"

# mapquik writes its PAF to <prefix>.paf; its logs (incl. "Maximum RSS") go to stdout/stderr → LOG
python3 "$BENCH_DIR/scripts/run_timed.py" "$METRICS" \
    docker run --rm \
        --platform linux/amd64 \
        -v "${BENCH_DIR}:/bench" \
        hifi-mapquik:latest \
        "$C_READS" \
        --reference "$C_REF" \
        --threads "$THREADS" \
        --prefix "$C_PREFIX" \
    > "$LOG" 2>&1

# Overwrite host-measured RSS with the tool's true in-container peak
python3 "$BENCH_DIR/scripts/parse_peak_rss.py" "$METRICS" "$LOG"

echo "Done: $OUT_PAF"
