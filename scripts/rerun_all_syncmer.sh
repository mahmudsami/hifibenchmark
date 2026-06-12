#!/usr/bin/env bash
# Re-run syncmer-hifi for ALL datasets with the current binary.
# Rebuilds every index (LCP/index structure changed). Keeps minimap2/BLEND/
# mapquik results. Simulation for all 4 genomes + real arm.
#   human/maize/arabidopsis : 8 threads, 100k reads
#   rye                     : 1 thread, 10k reads (memory)
set -uo pipefail
BENCH_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$BENCH_DIR/scripts"
log() { echo "[$(date '+%H:%M:%S')] === $* ==="; }

# ── Simulation: re-run syncmer per genome (each rebuilds its index) ───────────
for G in human maize arabidopsis; do
    log "SIM syncmer $G (8 threads, 100k)"
    bash "$SCRIPTS/rerun_human_syncmer.sh" "$G"
done
log "SIM syncmer rye (1 thread, 10k)"
THREADS=1 NUM_READS=10000 bash "$SCRIPTS/rerun_human_syncmer.sh" rye

# ── Real arm: drop real syncmer PAFs so they re-map with the new binary ───────
log "REAL: clearing old syncmer real PAFs"
for G in human maize arabidopsis rye; do
    rm -f "$BENCH_DIR/results/mappings/${G}_syncmer_errreal_len100k".*
done
log "REAL benchmark (1 thread; reuses rebuilt indexes + existing minimap2/blend/mapquik)"
THREADS=1 bash "$BENCH_DIR/run_real_benchmark.sh"

log "### ALL SYNCMER RERUN DONE ###"
