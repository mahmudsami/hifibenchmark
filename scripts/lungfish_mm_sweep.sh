#!/usr/bin/env bash
# minimap2 (k28/w200, stored .mmi) vs synpact on ALL 16 combos of the lungfish,
# same reads per combo. Two phases because the 33 GB decompressed reference and
# the 21 GB .mmi can't fit on disk together:
#   Phase 1: remove .mmi, decompress reference, simulate all reads, delete reference
#   Phase 2: (re)build + store the .mmi, then map+eval each combo with both mappers
set -uo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"
MM="${MINIMAP2:-/opt/homebrew/bin/minimap2}"
SYNPACT="${SYNPACT:-/Users/sami/synpact/target/release/synpact}"
G=lungfish_au; K=28; W=200
ERRS=(0 0.001 0.005 0.01); LENS=(10000 15000 20000 25000)
REFGZ="data/references/$G/genome.fa.gz"; REF="data/references/$G/genome.fa"
IDX="data/indexes/$G/synpact.idx"; MMI="data/indexes/$G/minimap2_k${K}_w${W}.mmi"
OUT="results/lungfish"; mkdir -p "$OUT"
log(){ echo "[$(date '+%H:%M:%S')] $* | disk $(df -h . | tail -1 | awk '{print $4}')"; }

# ── PHASE 1 — simulate every combo's reads (faidx needs the uncompressed FASTA) ─
log "PHASE 1: removing .mmi to make room for the decompressed reference"
rm -f "$MMI"
if [ -f "$REF" ]; then log "reusing existing decompressed reference"; else log "decompressing reference"; gzip -dc "$REFGZ" > "$REF"; fi
for E in "${ERRS[@]}"; do for L in "${LENS[@]}"; do
    R="data/reads/$G/err${E}_len${L}.fastq.gz"
    if [ -f "$R" ]; then log "reads err${E}_len${L} exist — skip"; continue; fi
    log "simulate err${E}_len${L}"
    python3 scripts/simulate_reads_faidx.py "$G" "$E" "$L" 100000 >/dev/null 2>&1 || log "  SIM FAILED err${E}_len${L}"
done; done
log "deleting decompressed reference"
rm -f "$REF" "$REF.fai"

# ── PHASE 2 — build/store .mmi, map + evaluate both mappers per combo ───────────
log "PHASE 2: building + storing minimap2 index (k=$K w=$W -I 8G)"
/usr/bin/time -l "$MM" -x map-hifi -k "$K" -w "$W" -I 8G -d "$MMI" "$REFGZ" \
    > "$OUT/${G}_minimap2_k${K}_w${W}_index.log" 2>&1
log "minimap2 index: $(du -h "$MMI" | awk '{print $1}')"

for E in "${ERRS[@]}"; do for L in "${LENS[@]}"; do
    TAG="err${E}_len${L}"; R="data/reads/$G/${TAG}.fastq.gz"; T="data/truth/$G/${TAG}.tsv"
    [ -f "$R" ] || { log "no reads for $TAG — skip"; continue; }
    log "map minimap2 $TAG"
    /usr/bin/time -l "$MM" -x map-hifi --secondary=no -t 8 "$MMI" "$R" \
        > "$OUT/${G}_minimap2_${TAG}.paf" 2> "$OUT/${G}_minimap2_${TAG}.log"
    log "map synpact $TAG"
    /usr/bin/time -l "$SYNPACT" --map "$R" "$IDX" -o "$OUT/${G}_synpact_${TAG}.paf" --threads 8 \
        2> "$OUT/${G}_synpact_${TAG}.log"
    for M in minimap2 synpact; do
        python3 scripts/05_evaluate_mapping.py "$T" "$OUT/${G}_${M}_${TAG}.paf" "$OUT/${G}_${M}_${TAG}_eval.json" 1000 >/dev/null 2>&1
    done
    # reads are KEPT (not deleted) so they don't need regenerating again
done; done
log "### lungfish minimap2-vs-synpact sweep DONE ###"

# index build time/memory table (minimap2 + synpact, excl. mapquik)
python3 scripts/lungfish_index_table.py "$G" || true
