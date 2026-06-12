#!/usr/bin/env bash
# Re-run a chosen set of mappers across the whole simulation dataset for ONE
# genome, under current conditions. Regenerates reads per combo (deterministic)
# and deletes them after. Keeps results for mappers not listed.
#
# Usage: bash scripts/rerun_genome_mappers.sh <genome> <mapper> [mapper...]
#   e.g. bash scripts/rerun_genome_mappers.sh maize minimap2 blend mapquik

set -uo pipefail
BENCH_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$BENCH_DIR/config.sh"
SCRIPTS="$BENCH_DIR/scripts"
G="$1"; shift
MAPPERS=("$@")
ERRS=(0 0.001 0.005 0.01)
LENS=(10000 15000 20000 25000)
log() { echo "[$(date '+%H:%M:%S')] $*"; }

# drop old outputs for the chosen mappers
for M in "${MAPPERS[@]}"; do
  rm -f "$MAPPINGS_DIR/${G}_${M}_"err[0-9]*.paf "$MAPPINGS_DIR/${G}_${M}_"err[0-9]*.log \
        "$MAPPINGS_DIR/${G}_${M}_"err[0-9]*_metrics.json "$MAPPINGS_DIR/${G}_${M}_"err[0-9]*_eval.json
done

for E in "${ERRS[@]}"; do
  for L in "${LENS[@]}"; do
    TAG="err${E}_len${L}"; TRUTH="$TRUTH_DIR/$G/${TAG}.tsv"
    log "simulate  $G $E $L"
    python3 "$SCRIPTS/02_simulate_reads.py" "$G" "$E" "$L" "${NUM_READS:-100000}" >/dev/null 2>&1
    for M in "${MAPPERS[@]}"; do
      log "map $M  $G $E $L"
      bash "$SCRIPTS/04_run_${M}.sh" "$G" "$E" "$L" >/dev/null 2>&1
      PAF="$MAPPINGS_DIR/${G}_${M}_${TAG}.paf"
      EVAL="$MAPPINGS_DIR/${G}_${M}_${TAG}_eval.json"
      python3 "$SCRIPTS/05_evaluate_mapping.py" "$TRUTH" "$PAF" "$EVAL" "$EVAL_TOLERANCE" \
        | sed "s/^/    $M /" | grep -E "accuracy|$M map"
    done
    rm -f "$READS_DIR/$G/${TAG}.fastq.gz" "$READS_DIR/$G/${TAG}.fastq"
  done
done

log "compute mapping-only time + collect + plot"
python3 "$SCRIPTS/compute_map_time.py" >/dev/null
python3 "$SCRIPTS/06_collect_results.py"
python3 "$SCRIPTS/07_plot_accuracy.py"
python3 "$SCRIPTS/08_plot_time_memory.py"
log "### RERUN DONE: $G [${MAPPERS[*]}] ###"
