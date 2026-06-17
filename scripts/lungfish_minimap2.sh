#!/usr/bin/env bash
# minimap2 vs synpact on the lungfish for ONE combo, on the SAME reads.
# minimap2: k=28 (its max), w=200, index BUILT ONCE and stored (-d, -I batched),
# then mapped against the stored .mmi (so mapping time excludes indexing, like
# synpact). A single whole-genome .mmi here is ~22 GB (the 4-bit reference floor),
# built in -I 8G batches so build RAM stays bounded.
#
# Usage: lungfish_minimap2.sh [genome] [error_rate] [read_length] [k] [w]
set -uo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"
MM="${MINIMAP2:-/opt/homebrew/bin/minimap2}"
SYNPACT="${SYNPACT:-/Users/sami/synpact/target/release/synpact}"
case "$(uname)" in Darwin) TF="-l";; *) TF="-v";; esac

G="${1:-lungfish_au}"; E="${2:-0.005}"; L="${3:-20000}"; K="${4:-28}"; W="${5:-200}"
TAG="err${E}_len${L}"
REFGZ="data/references/$G/genome.fa.gz"; REF="data/references/$G/genome.fa"
READS="data/reads/$G/${TAG}.fastq.gz"; TRUTH="data/truth/$G/${TAG}.tsv"
IDX="data/indexes/$G/synpact.idx"
MMI="data/indexes/$G/minimap2_k${K}_w${W}.mmi"
OUT="results/lungfish"; mkdir -p "$OUT" "data/indexes/$G"
log(){ echo "[$(date '+%H:%M:%S')] $*"; }

# 1. reads+truth (regenerate only if missing; faidx needs the FASTA transiently)
if [ ! -f "$READS" ] || [ ! -f "$TRUTH" ]; then
    log "decompressing reference (transient) ..."; gzip -dc "$REFGZ" > "$REF"
    rm -f "$READS" "$TRUTH"
    log "simulating reads $TAG ..."; python3 scripts/simulate_reads_faidx.py "$G" "$E" "$L" 100000
    rm -f "$REF" "$REF.fai"; log "removed transient FASTA"
else
    log "reusing existing reads/truth for $TAG"
fi

# 2. build + STORE the minimap2 index once (-I batched so build RAM is bounded)
if [ ! -f "$MMI" ]; then
    log "building minimap2 index → $MMI (k=$K w=$W -I 8G) ..."
    /usr/bin/time $TF "$MM" -x map-hifi -k "$K" -w "$W" -I 8G -d "$MMI" "$REFGZ" \
        > "$OUT/${G}_minimap2_k${K}_w${W}_index.log" 2>&1
fi
log "minimap2 index: $(du -h "$MMI" | awk '{print $1}')"

# 3. map against the stored .mmi (k/w come from the index; map-only timing)
log "minimap2 --map against stored .mmi ..."
/usr/bin/time $TF "$MM" -x map-hifi --secondary=no -t 8 "$MMI" "$READS" \
    > "$OUT/${G}_minimap2_${TAG}.paf" 2> "$OUT/${G}_minimap2_${TAG}.log"

# 4. synpact on the SAME reads (reuse prebuilt index)
log "synpact --map (same reads) ..."
/usr/bin/time $TF "$SYNPACT" --map "$READS" "$IDX" -o "$OUT/${G}_synpact_${TAG}.paf" --threads 8 \
    2> "$OUT/${G}_synpact_${TAG}.log"

# 5. evaluate both vs the same truth
for M in minimap2 synpact; do
    python3 scripts/05_evaluate_mapping.py "$TRUTH" "$OUT/${G}_${M}_${TAG}.paf" "$OUT/${G}_${M}_${TAG}_eval.json" 1000 >/dev/null 2>&1
done

# 6. report
echo; echo "==== $G $TAG  (minimap2 k=$K w=$W, stored .mmi  vs  synpact) — same reads ===="
printf "%-10s %9s %7s %8s %8s %8s\n" "mapper" "maprate%" "acc%" "prec%" "map_s" "rss_GB"
for M in minimap2 synpact; do
    python3 - "$OUT/${G}_${M}_${TAG}_eval.json" "$OUT/${G}_${M}_${TAG}.log" "$M" <<'PY'
import sys,json,re,os
ev=json.load(open(sys.argv[1])); txt=open(sys.argv[2]).read() if os.path.exists(sys.argv[2]) else ""
m=re.search(r'(\d+)\s+maximum resident set size',txt)
rss=int(m.group(1))/1e9 if m else 0
t=re.search(r'([\d.]+)\s+real',txt); sec=float(t.group(1)) if t else 0
print("%-10s %8.3f %7.2f %8.3f %8.1f %8.2f"%(sys.argv[3],ev['mapping_rate'],ev['accuracy'],ev['precision'],sec,rss))
PY
done
echo "minimap2 index build (one-time):"; grep -iE '(\d+)\s+maximum resident|real ' "$OUT/${G}_minimap2_k${K}_w${W}_index.log" 2>/dev/null | sed 's/^/  /'
echo "disk free: $(df -h . | tail -1 | awk '{print $4}')"
