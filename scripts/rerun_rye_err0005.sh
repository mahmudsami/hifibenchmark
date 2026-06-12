#!/usr/bin/env bash
# Re-run the rye err=0.005 block (all lengths × all mappers) that failed when
# Docker went down mid-run. Reuses the existing rye index. 1 thread / 10k reads.
set -uo pipefail
BENCH_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$BENCH_DIR/config.sh"
SCRIPTS="$BENCH_DIR/scripts"
G=rye; E=0.005
MAPPERS=(minimap2 blend mapquik syncmer)
LENS=(10000 15000 20000 25000)
log() { echo "[$(date '+%H:%M:%S')] $*"; }

for L in "${LENS[@]}"; do
  TAG="err${E}_len${L}"; TRUTH="$TRUTH_DIR/$G/${TAG}.tsv"
  # delete the failed (empty/missing) outputs so runners don't skip
  for M in "${MAPPERS[@]}"; do
    rm -f "$MAPPINGS_DIR/${G}_${M}_${TAG}".paf "$MAPPINGS_DIR/${G}_${M}_${TAG}".log \
          "$MAPPINGS_DIR/${G}_${M}_${TAG}"_metrics.json "$MAPPINGS_DIR/${G}_${M}_${TAG}"_eval.json
  done
  log "simulate  $G $E $L"
  python3 "$SCRIPTS/02_simulate_reads.py" "$G" "$E" "$L" "${NUM_READS:-100000}" >/dev/null 2>&1
  for M in "${MAPPERS[@]}"; do
    log "map $M  $G $E $L"
    bash "$SCRIPTS/04_run_${M}.sh" "$G" "$E" "$L" >/dev/null 2>&1
    PAF="$MAPPINGS_DIR/${G}_${M}_${TAG}.paf"
    EVAL="$MAPPINGS_DIR/${G}_${M}_${TAG}_eval.json"
    if [ -s "$PAF" ]; then
      python3 "$SCRIPTS/05_evaluate_mapping.py" "$TRUTH" "$PAF" "$EVAL" "$EVAL_TOLERANCE" | sed "s/^/    $M /" | grep accuracy
    else
      echo "    $M FAILED (no PAF)"
    fi
  done
  rm -f "$READS_DIR/$G/${TAG}.fastq.gz" "$READS_DIR/$G/${TAG}.fastq"
done

log "compute mapping-only time + collect + plot"
python3 "$SCRIPTS/compute_map_time.py" >/dev/null
python3 "$SCRIPTS/06_collect_results.py"
python3 "$SCRIPTS/07_plot_accuracy.py" >/dev/null
python3 "$SCRIPTS/08_plot_time_memory.py" >/dev/null
log "### RYE err0.005 RERUN DONE ###"
