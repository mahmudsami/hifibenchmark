#!/usr/bin/env bash
# Prepare mapquik's reference, ONCE per genome.
#
# mapquik REQUIRES a single-line, uppercase FASTA: multi-line sequences are not
# supported (it reads only the first line of each record → ~1% mapping rate) and
# lowercase/soft-masked bases are not supported either. See
#   https://github.com/ekimb/mapquik#readme
#   https://github.com/ekimb/mapquik/issues/17#issuecomment-1895882175
#
# This rewrites data/references/<g>/genome.fa.gz (standard 60-col, soft-masked)
# into data/indexes/<g>/genome.mapquik.fa.gz (one line per sequence, uppercased).
# 04_run_mapquik.sh / 04_map_mapquik.sh point mapquik at this file.
#
# Usage: 04_index_mapquik.sh <genome>

set -euo pipefail
source "$(dirname "$0")/_runner_lib.sh"

GENOME="$1"
SRC="$REFS_DIR/$GENOME/genome.fa.gz"
OUT="$INDEX_DIR/$GENOME/genome.mapquik.fa.gz"

if [ -f "$OUT" ]; then
    echo "mapquik reference exists: $OUT — skipping (delete to rebuild)."
    exit 0
fi
if [ ! -f "$SRC" ]; then
    echo "Missing reference $SRC" >&2
    exit 1
fi

mkdir -p "$INDEX_DIR/$GENOME"
echo "Preparing single-line uppercase mapquik reference for $GENOME ..."
t0=$(date +%s)

# Streaming O(n) rewrite to single-line, uppercased-sequence FASTA. The reformat
# runs in Python (bytes.upper) because macOS's awk is ~7x slower here and
# dominates large-genome prep. gzip -1: mapquik reads any gzip level the same,
# and level 1 keeps recompression quick (no pigz on this host; disk is too tight
# for an uncompressed copy of the large genomes).
gzip -dc "$SRC" \
  | python3 "$BENCH_DIR/scripts/fasta_to_singleline.py" \
  | gzip -1 > "$OUT"

echo "mapquik reference saved: $OUT  ($(($(date +%s) - t0))s)"
