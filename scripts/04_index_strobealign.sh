#!/usr/bin/env bash
# Build (and time) a strobealign index, ONCE per genome.
# strobealign writes the index (<ref>.r<bucket>.sti) next to the reference FASTA;
# 04_map_strobealign.sh then loads it with --use-index so its peak RSS reflects
# mapping only — not index construction.
#
# Usage: 04_index_strobealign.sh <genome> [read_length]
#
# read_length picks strobealign's seeding parameters. For this benchmark all
# read lengths (10k–25k) fall in the same internal bucket, so one index per
# genome serves every length; the default 15000 is representative.

set -euo pipefail
source "$(dirname "$0")/_runner_lib.sh"

GENOME="$1"
LEN="${2:-15000}"

C_REF="$(container_ref "$GENOME")"
# strobealign derives the .sti filename from the reference + internal bucket.
INDEX_GLOB="$REFS_DIR/$GENOME/genome.fa.gz".r*.sti
METRICS="$MAPPINGS_DIR/${GENOME}_strobealign_index_metrics.json"
LOG="$MAPPINGS_DIR/${GENOME}_strobealign_index.log"

if compgen -G "$INDEX_GLOB" > /dev/null; then
    echo "Index exists: $(echo $INDEX_GLOB) — skipping (delete to rebuild)."
    exit 0
fi

echo "Building strobealign index for $GENOME (r=$LEN) ..."

# -i: create index only (no mapping).
python3 "$BENCH_DIR/scripts/run_timed.py" "$METRICS" \
    "${DOCKER_RUN[@]}" hifi-strobealign:latest \
        strobealign -i -r "$LEN" -t "$THREADS" "$C_REF" \
    > /dev/null 2> "$LOG"

parse_peak "$METRICS" "$LOG"
echo "Index saved: $(echo $INDEX_GLOB)"
