#!/usr/bin/env bash
# Re-run synpact for ALL datasets with the current binary.
# Rebuilds every index (LCP/index structure changed). Keeps minimap2/BLEND/
# mapquik results. Simulation for all 4 genomes + real arm.
#   all genomes: 8 threads, 100k reads
set -uo pipefail
BENCH_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$BENCH_DIR/scripts"
log() { echo "[$(date '+%H:%M:%S')] === $* ==="; }

# ── Simulation: re-run synpact per genome (each rebuilds its index) ───────────
for G in human maize arabidopsis rye; do
    log "SIM synpact $G (8 threads, 100k)"
    bash "$SCRIPTS/rerun_human_synpact.sh" "$G"
done

# ── Real arm: drop real synpact PAFs so they re-map with the new binary ───────
log "REAL: clearing old synpact real PAFs"
for G in human maize arabidopsis rye; do
    rm -f "$BENCH_DIR/results/mappings/${G}_synpact_errreal_len100k".*
done
log "REAL benchmark (8 threads; reuses rebuilt indexes + existing minimap2/blend/mapquik)"
bash "$BENCH_DIR/run_real_benchmark.sh"

log "### ALL SYNPACT RERUN DONE ###"
