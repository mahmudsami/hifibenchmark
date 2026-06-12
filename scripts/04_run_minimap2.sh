#!/usr/bin/env bash
# Map reads with minimap2 via Docker (linux/amd64 image), record wall time and peak RSS.
#
# Usage: 04_run_minimap2.sh <genome> <error_rate> <read_length>
#
# Prerequisites: build the image once with:
#   bash docker/build_images.sh

set -euo pipefail
source "$(dirname "$0")/../config.sh"

GENOME="$1"
ERR="$2"
LEN="$3"

TAG="err${ERR}_len${LEN}"
OUT_PAF="$MAPPINGS_DIR/${GENOME}_minimap2_${TAG}.paf"
METRICS="$MAPPINGS_DIR/${GENOME}_minimap2_${TAG}_metrics.json"

if [ -f "$OUT_PAF" ]; then
    echo "Already mapped: $OUT_PAF — skipping."
    exit 0
fi

# Translate host paths to in-container paths (/bench mirrors $BENCH_DIR)
C_REF="/bench/data/references/$GENOME/genome.fa.gz"
if [ -f "$READS_DIR/$GENOME/${TAG}.fastq.gz" ]; then
    C_READS="/bench/data/reads/$GENOME/${TAG}.fastq.gz"
else
    C_READS="/bench/data/reads/$GENOME/${TAG}.fastq"
fi
LOG="$MAPPINGS_DIR/${GENOME}_minimap2_${TAG}.log"   # stderr: minimap2 + /usr/bin/time -v

echo "Running minimap2 (Docker): genome=$GENOME err=$ERR len=$LEN"

# Image ENTRYPOINT is "/usr/bin/time -v"; first arg is the tool. PAF → stdout, logs → stderr.
python3 "$BENCH_DIR/scripts/run_timed.py" "$METRICS" \
    docker run --rm \
        --platform linux/amd64 \
        -v "${BENCH_DIR}:/bench" \
        hifi-minimap2:latest \
        minimap2 \
            -x map-hifi \
            --secondary=no \
            -t "$THREADS" \
            "$C_REF" "$C_READS" \
    > "$OUT_PAF" 2> "$LOG"

# Overwrite host-measured RSS with the in-container peak (from /usr/bin/time -v)
python3 "$BENCH_DIR/scripts/parse_peak_rss.py" "$METRICS" "$LOG"

echo "Done: $OUT_PAF"
