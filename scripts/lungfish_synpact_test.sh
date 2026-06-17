#!/usr/bin/env bash
# Standalone synpact-ONLY test on a very large genome (e.g. lungfish) — NOT part
# of the main benchmark. Native (no Docker). Does the full chain for ONE combo:
#   decompress → faidx-simulate → build synpact index → map → evaluate
# and reports accuracy, mapping time, and peak RSS for the index build and the map.
#
# Memory note: the faidx simulator is O(read length); the synpact INDEX BUILD is
# the heavy step on a 35 Gb genome — this is what may or may not fit in host RAM.
#
# Prereq: data/references/<genome>/genome.fa.gz already downloaded.
# Usage:  scripts/lungfish_synpact_test.sh [genome] [error_rate] [read_length] [n_reads]
#         defaults: lungfish_au 0.005 20000 100000

set -uo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"

SYNPACT="${SYNPACT:-/Users/sami/synpact/target/release/synpact}"
TIME_BIN="${TIME_BIN:-/usr/bin/time}"
case "$(uname)" in Darwin) TFLAG="-l";; *) TFLAG="-v";; esac   # macOS -l / GNU -v
THREADS="${THREADS:-8}"               # mapping threads
INDEX_THREADS="${INDEX_THREADS:-1}"   # index-build threads (1 → lower peak memory)

G="${1:-lungfish_au}"; E="${2:-0.005}"; L="${3:-20000}"; N="${4:-100000}"
TAG="err${E}_len${L}"
REFGZ="data/references/$G/genome.fa.gz"
REF="data/references/$G/genome.fa"
IDX="data/indexes/$G/synpact.idx"
READS="data/reads/$G/${TAG}.fastq.gz"
TRUTH="data/truth/$G/${TAG}.tsv"
OUT="results/lungfish"; mkdir -p "$OUT" "data/indexes/$G"
PAF="$OUT/${G}_synpact_${TAG}.paf"
log(){ echo "[$(date '+%H:%M:%S')] $*"; }

# Disk policy: keep ONLY the compressed reference on disk. The faidx simulator
# needs an uncompressed, seekable FASTA, so decompress TRANSIENTLY just for the
# simulation, then delete it. synpact builds its index straight from the .gz.

# 1+2. simulate reads (decompress transiently for the faidx simulator)
if [ ! -f "$READS" ]; then
    DECOMPRESSED_HERE=0
    if [ ! -f "$REF" ]; then
        [ -f "$REFGZ" ] || { echo "ERROR: missing $REFGZ" >&2; exit 1; }
        log "decompressing reference → $REF (transient, for the simulator) ..."
        gzip -dc "$REFGZ" > "$REF"; DECOMPRESSED_HERE=1
    fi
    log "simulating $N reads ($TAG) with faidx simulator ..."
    python3 scripts/simulate_reads_faidx.py "$G" "$E" "$L" "$N"
    if [ "$DECOMPRESSED_HERE" = 1 ]; then
        log "removing transient decompressed FASTA to free disk for the index build"
        rm -f "$REF" "$REF.fai"
    fi
fi

# 3. build synpact index from the COMPRESSED reference (timed + peak RSS).
#    Uses the .gz so the 33 GB decompressed copy need not sit alongside the
#    index build's scratch — disk, not RAM, is the constraint on huge genomes.
BUILD_REF="$REFGZ"; [ -f "$BUILD_REF" ] || BUILD_REF="$REF"
if [ ! -f "$IDX" ]; then
    log "building synpact index from $BUILD_REF with $INDEX_THREADS thread(s) ..."
    log "disk free before build: $(df -h . | tail -1 | awk '{print $4}')"
    $TIME_BIN $TFLAG "$SYNPACT" --build-index "$BUILD_REF" "$IDX" --threads "$INDEX_THREADS" \
        > "$OUT/${G}_index.log" 2>&1 || { echo "INDEX BUILD FAILED — see $OUT/${G}_index.log"; tail -8 "$OUT/${G}_index.log"; exit 1; }
fi
log "index: $(du -h "$IDX" | awk '{print $1}')"

# 4. map (timed + peak RSS)
log "mapping with synpact ..."
$TIME_BIN $TFLAG "$SYNPACT" --map "$READS" "$IDX" -o "$PAF" --threads "$THREADS" \
    > "$OUT/${G}_map_${TAG}.log" 2>&1

# 5. evaluate accuracy vs truth
log "evaluating accuracy ..."
python3 scripts/05_evaluate_mapping.py "$TRUTH" "$PAF" "$OUT/${G}_${TAG}_eval.json" 1000

# 6. report
echo
echo "==================== RESULTS: $G $TAG ===================="
echo "[index build]"; grep -iE 'maximum resident|real ' "$OUT/${G}_index.log" | sed 's/^/  /'
echo "[mapping]";     grep -iE 'maximum resident|real |Elapsed|Real time' "$OUT/${G}_map_${TAG}.log" | sed 's/^/  /'
echo "[accuracy]";    cat "$OUT/${G}_${TAG}_eval.json"
echo "=========================================================="

# index build time/memory table (minimap2 + synpact, excl. mapquik)
python3 scripts/lungfish_index_table.py "$G" || true
