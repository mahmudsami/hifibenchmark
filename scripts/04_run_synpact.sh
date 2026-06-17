#!/usr/bin/env bash
# Map reads with synpact (default selector) via Docker, recording wall time
# and peak RSS. Builds the lean index once per genome (whichever combo runs
# first), then reuses it.
#
# Usage: 04_run_synpact.sh <genome> <error_rate> <read_length>
#
# For mapping-only peak RSS (index construction excluded), use the split pair
# 04_index_synpact.sh + 04_map_synpact.sh instead.

set -euo pipefail
source "$(dirname "$0")/../config.sh"

GENOME="$1"; ERR="$2"; LEN="$3"
MAPPER="synpact"

TAG="err${ERR}_len${LEN}"
OUT_PAF="$MAPPINGS_DIR/${GENOME}_${MAPPER}_${TAG}.paf"
METRICS="$MAPPINGS_DIR/${GENOME}_${MAPPER}_${TAG}_metrics.json"
LOG="$MAPPINGS_DIR/${GENOME}_${MAPPER}_${TAG}.log"
INDEX_HOST="$INDEX_DIR/$GENOME/synpact.idx"

C_REF="/bench/data/references/$GENOME/genome.fa.gz"
if [ -f "$READS_DIR/$GENOME/${TAG}.fastq.gz" ]; then
    C_READS="/bench/data/reads/$GENOME/${TAG}.fastq.gz"
else
    C_READS="/bench/data/reads/$GENOME/${TAG}.fastq"
fi
C_INDEX="/bench/data/indexes/$GENOME/synpact.idx"
C_OUT_PAF="/bench/results/mappings/${GENOME}_${MAPPER}_${TAG}.paf"

DOCKER="docker run --rm --platform linux/amd64 -v ${BENCH_DIR}:/bench hifi-synpact:latest"

# Build the lean index once per genome (new binary default skips L0-L2 → ~0.5 GB)
if [ ! -f "$INDEX_HOST" ]; then
    echo "Building synpact lean index for $GENOME (Docker) ..."
    mkdir -p "$INDEX_DIR/$GENOME"
    $DOCKER synpact --build-index "$C_REF" "$C_INDEX" --threads "$THREADS"
    echo "Index saved: $INDEX_HOST"
fi

if [ -f "$OUT_PAF" ]; then
    echo "Already mapped: $OUT_PAF — skipping."
    exit 0
fi

echo "Running synpact (Docker): genome=$GENOME err=$ERR len=$LEN"

python3 "$BENCH_DIR/scripts/run_timed.py" "$METRICS" \
    $DOCKER \
        synpact \
            --map "$C_READS" "$C_INDEX" \
            -o "$C_OUT_PAF" \
            --threads "$THREADS" \
    > /dev/null 2> "$LOG"

python3 "$BENCH_DIR/scripts/parse_peak_rss.py" "$METRICS" "$LOG"
echo "Done: $OUT_PAF"
