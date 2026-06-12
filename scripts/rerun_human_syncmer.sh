#!/usr/bin/env bash
# Re-run syncmer-hifi on the whole human simulation dataset with the current
# binary. Keeps existing minimap2/BLEND/mapquik results; rebuilds the lean human
# index once; regenerates reads per combo (deterministic) and deletes them after
# to bound disk.
#
# Usage: bash scripts/rerun_human_syncmer.sh

set -uo pipefail
BENCH_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$BENCH_DIR/config.sh"
SCRIPTS="$BENCH_DIR/scripts"
G="${1:-human}"
ERRS=(0 0.001 0.005 0.01)
LENS=(10000 15000 20000 25000)
log() { echo "[$(date '+%H:%M:%S')] $*"; }

# Force a fresh lean index with the current binary
rm -f "$INDEX_DIR/$G/syncmer_hifi.idx"
# Drop old syncmer outputs so they regenerate (keep minimap2/blend/mapquik)
rm -f "$MAPPINGS_DIR/${G}"_syncmer_err[0-9]*

for E in "${ERRS[@]}"; do
  for L in "${LENS[@]}"; do
    TAG="err${E}_len${L}"
    TRUTH="$TRUTH_DIR/$G/${TAG}.tsv"
    log "simulate  $G $E $L"
    python3 "$SCRIPTS/02_simulate_reads.py" "$G" "$E" "$L" "${NUM_READS:-100000}" >/dev/null 2>&1
    log "map syncmer  $G $E $L"
    bash "$SCRIPTS/04_run_syncmer.sh" "$G" "$E" "$L" >/dev/null 2>&1
    PAF="$MAPPINGS_DIR/${G}_syncmer_${TAG}.paf"
    EVAL="$MAPPINGS_DIR/${G}_syncmer_${TAG}_eval.json"
    python3 "$SCRIPTS/05_evaluate_mapping.py" "$TRUTH" "$PAF" "$EVAL" "$EVAL_TOLERANCE" \
      | sed "s/^/    syncmer /"
    rm -f "$READS_DIR/$G/${TAG}.fastq.gz" "$READS_DIR/$G/${TAG}.fastq"
  done
done

log "compute mapping-only time + collect + plot"
python3 "$SCRIPTS/compute_map_time.py" >/dev/null
python3 "$SCRIPTS/06_collect_results.py"
python3 "$SCRIPTS/07_plot_accuracy.py"
python3 "$SCRIPTS/08_plot_time_memory.py"
log "### HUMAN SYNCMER RERUN DONE ###"
