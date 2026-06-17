#!/usr/bin/env bash
# Sweep error rates × read lengths for the lungfish, reusing the ALREADY-BUILT
# synpact index. Disk-safe: decompress the reference once (faidx needs it), then
# per combo simulate → map → evaluate → delete that combo's reads. Keeps truth +
# eval + per-combo timing/memory.
#
# Usage: lungfish_sweep.sh [genome]   (default lungfish_au)
set -uo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"
SYNPACT="${SYNPACT:-/Users/sami/synpact/target/release/synpact}"
case "$(uname)" in Darwin) TFLAG="-l";; *) TFLAG="-v";; esac
G="${1:-lungfish_au}"
ERRS=(0 0.001 0.005 0.01); LENS=(10000 15000 20000 25000)
REF="data/references/$G/genome.fa"; REFGZ="data/references/$G/genome.fa.gz"
IDX="data/indexes/$G/synpact.idx"; OUT="results/lungfish"; mkdir -p "$OUT"
log(){ echo "[$(date '+%H:%M:%S')] $*"; }

[ -f "$IDX" ] || { echo "ERROR: index $IDX missing — run lungfish_synpact_test.sh first"; exit 1; }

# decompress the reference once (transient; deleted at the end)
DECOMP=0
if [ ! -f "$REF" ]; then
    log "decompressing $REFGZ → $REF (once) ..."; gzip -dc "$REFGZ" > "$REF"; DECOMP=1
    log "disk free after decompress: $(df -h . | tail -1 | awk '{print $4}')"
fi

for E in "${ERRS[@]}"; do for L in "${LENS[@]}"; do
    TAG="err${E}_len${L}"
    EVAL="$OUT/${G}_${TAG}_eval.json"
    READS="data/reads/$G/${TAG}.fastq.gz"; TRUTH="data/truth/$G/${TAG}.tsv"
    PAF="$OUT/${G}_synpact_${TAG}.paf"; MT="$OUT/${G}_map_${TAG}.log"
    [ -f "$EVAL" ] && { log "$TAG already evaluated — skipping"; continue; }

    log "simulate $TAG"
    python3 scripts/simulate_reads_faidx.py "$G" "$E" "$L" 100000 >/dev/null 2>&1 \
        || { echo "  sim FAILED $TAG"; continue; }
    log "map $TAG"
    /usr/bin/time $TFLAG "$SYNPACT" --map "$READS" "$IDX" -o "$PAF" --threads 8 > "$MT" 2>&1
    python3 scripts/05_evaluate_mapping.py "$TRUTH" "$PAF" "$EVAL" 1000 >/dev/null 2>&1
    rm -f "$READS"            # free reads (keep truth + eval + timing)
done; done

[ "$DECOMP" = 1 ] && { rm -f "$REF" "$REF.fai"; log "removed transient $REF"; }

# ── summary table ─────────────────────────────────────────────────────────────
echo; echo "==== synpact on $G : accuracy / mapping time / peak RSS ===="
printf "%-22s %8s %8s %9s %8s %8s\n" "combo" "maprate" "acc%" "prec%" "map_s" "rss_GB"
for E in "${ERRS[@]}"; do for L in "${LENS[@]}"; do
    TAG="err${E}_len${L}"; EVAL="$OUT/${G}_${TAG}_eval.json"; MT="$OUT/${G}_map_${TAG}.log"
    [ -f "$EVAL" ] || continue
    python3 - "$EVAL" "$MT" "$TAG" <<'PY'
import sys,json,re
ev=json.load(open(sys.argv[1])); txt=open(sys.argv[2]).read() if __import__('os').path.exists(sys.argv[2]) else ""
m=re.search(r'maximum resident set size\D+(\d+)',txt); rss=int(m.group(1))/1e9 if m else 0
t=re.search(r'([\d.]+)\s+real',txt); sec=float(t.group(1)) if t else 0
print("%-22s %7.3f%% %7.2f %8.3f %8.1f %8.2f"%(sys.argv[3],ev['mapping_rate'],ev['accuracy'],ev['precision'],sec,rss))
PY
done; done
echo "disk free: $(df -h . | tail -1 | awk '{print $4}')"
