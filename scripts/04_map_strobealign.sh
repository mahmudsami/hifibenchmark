#!/usr/bin/env bash
# Map reads with strobealign against a PRE-BUILT index (--use-index), recording
# wall time and the mapping-only peak RSS (index construction excluded — see
# 04_index_strobealign.sh).
#
# Usage: 04_map_strobealign.sh <genome> <error_rate> <read_length>

set -euo pipefail
source "$(dirname "$0")/_runner_lib.sh"

GENOME="$1"; ERR="$2"; LEN="$3"
TAG="err${ERR}_len${LEN}"

C_REF="$(container_ref "$GENOME")"
INDEX_GLOB="$REFS_DIR/$GENOME/genome.fa.gz".r*.sti
OUT_PAF="$MAPPINGS_DIR/${GENOME}_strobealign_${TAG}.paf"
METRICS="$MAPPINGS_DIR/${GENOME}_strobealign_${TAG}_metrics.json"
LOG="$MAPPINGS_DIR/${GENOME}_strobealign_${TAG}.log"
C_READS="$(container_reads "$GENOME" "$TAG")"

if ! compgen -G "$INDEX_GLOB" > /dev/null; then
    echo "Missing index for $GENOME — run: 04_index_strobealign.sh $GENOME" >&2
    exit 1
fi
if [ -f "$OUT_PAF" ] && [ -s "$OUT_PAF" ]; then
    echo "Already mapped: $OUT_PAF — skipping."
    exit 0
fi

# -r must match the index bucket so strobealign finds the .sti (numeric only;
# for non-numeric tags strobealign auto-detects, which still hits the bucket).
if [[ "$LEN" =~ ^[0-9]+$ ]]; then
    READ_LEN_ARG="-r $LEN"
else
    READ_LEN_ARG=""
fi

echo "Mapping strobealign (pre-built index): genome=$GENOME err=$ERR len=$LEN"

# --use-index loads the on-disk .sti instead of rebuilding; /usr/bin/time -v's
# peak RSS is then the mapping-phase footprint.
python3 "$BENCH_DIR/scripts/run_timed.py" "$METRICS" \
    "${DOCKER_RUN[@]}" hifi-strobealign:latest \
        strobealign -x --use-index -t "$THREADS" $READ_LEN_ARG "$C_REF" "$C_READS" \
    > "$OUT_PAF" 2> "$LOG"

parse_peak "$METRICS" "$LOG"
echo "Done: $OUT_PAF"
