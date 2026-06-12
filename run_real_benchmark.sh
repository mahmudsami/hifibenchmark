#!/usr/bin/env bash
# Real-data benchmark arm: map real PacBio HiFi reads with all four tools and
# evaluate by consensus-of-mappers (real reads have no ground truth).
#
# Steps:
#   10  Download ~100k real HiFi reads per genome (human HG002, maize B73)
#   04  Map with each tool (reuses the simulation Docker runners, tag=real/100k)
#   12  Consensus-of-mappers evaluation per genome
#   13  Collect → results/csv/results_real.csv
#   14  Plot   → results/plots/real_benchmark.png
#
# Prerequisites: Docker images built (bash docker/build_images.sh),
#                references downloaded, syncmer-hifi index built (reused from sim arm).
#
# Usage: run_real_benchmark.sh [--force]
#   --force   re-map everything, ignoring cached PAFs (keeps the downloaded reads)

set -euo pipefail
BENCH_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$BENCH_DIR/config.sh"

SCRIPTS="$BENCH_DIR/scripts"
MAPPERS=("minimap2" "blend" "strobealign" "syncmer" "mapquik")
REAL_ERR="real"   # pseudo error-rate token → tag "errreal_len100k"
REAL_LEN="100k"
REAL_TAG="err${REAL_ERR}_len${REAL_LEN}"
DC_ERR="dc"       # DeepConsensus token → tag "errdc_len100k" (rye only)
DC_TAG="err${DC_ERR}_len${REAL_LEN}"

FORCE=0
for arg in "$@"; do
    [ "$arg" = "--force" ] && FORCE=1
done

# Real datasets only exist for these genomes (HG002 human, B73 maize).
REAL_GENOMES=(human maize arabidopsis rye)

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── Prepare mapquik's single-line reference ONCE per genome (before any step 4).
# mapquik needs a single-line, uppercase FASTA; building it up front avoids a
# stall on the first mapquik run and is cached/skipped if it already exists.
if printf '%s\n' "${MAPPERS[@]}" | grep -qx mapquik; then
    for GENOME in "${REAL_GENOMES[@]}"; do
        log "Prepare mapquik reference  genome=$GENOME"
        bash "$SCRIPTS/04_index_mapquik.sh" "$GENOME"
    done
fi

for GENOME in "${REAL_GENOMES[@]}"; do
    # Step 10 — download real reads
    log "Step 10: download real reads  genome=$GENOME"
    bash "$SCRIPTS/10_download_real_reads.sh" "$GENOME"

    # --force: drop cached mapping outputs (keep the downloaded reads)
    if [ "$FORCE" = "1" ]; then
        rm -f "$MAPPINGS_DIR/${GENOME}"_*_"${REAL_TAG}".paf \
              "$MAPPINGS_DIR/${GENOME}"_*_"${REAL_TAG}".log \
              "$MAPPINGS_DIR/${GENOME}"_*_"${REAL_TAG}"_metrics.json \
              "$MAPPINGS_DIR/${GENOME}"_*_"${REAL_TAG}"_eval.json
    fi

    # Step 4 — map with each tool (reuses simulation runners)
    for MAPPER in "${MAPPERS[@]}"; do
        log "Step 4: map  mapper=$MAPPER genome=$GENOME (real)"
        bash "$SCRIPTS/04_run_${MAPPER}.sh" "$GENOME" "$REAL_ERR" "$REAL_LEN"
    done

    # Step 12 — consensus evaluation
    log "Step 12: consensus eval  genome=$GENOME tag=$REAL_TAG"
    python3 "$SCRIPTS/12_eval_consensus.py" "$GENOME" "$REAL_TAG" "$EVAL_TOLERANCE"
done

# ── Rye DeepConsensus readset ─────────────────────────────────────────────────
log "=== Rye DeepConsensus readset (tag=$DC_TAG) ==="

log "Step 10: download rye DC reads"
bash "$SCRIPTS/10_download_real_reads.sh" rye dc

if [ "$FORCE" = "1" ]; then
    rm -f "$MAPPINGS_DIR/rye"_*_"${DC_TAG}".paf \
          "$MAPPINGS_DIR/rye"_*_"${DC_TAG}".log \
          "$MAPPINGS_DIR/rye"_*_"${DC_TAG}"_metrics.json \
          "$MAPPINGS_DIR/rye"_*_"${DC_TAG}"_eval.json
fi

for MAPPER in "${MAPPERS[@]}"; do
    log "Step 4: map  mapper=$MAPPER genome=rye (DC)"
    bash "$SCRIPTS/04_run_${MAPPER}.sh" rye "$DC_ERR" "$REAL_LEN"
done

log "Step 12: consensus eval  genome=rye tag=$DC_TAG"
python3 "$SCRIPTS/12_eval_consensus.py" rye "$DC_TAG" "$EVAL_TOLERANCE"

# Derive mapping-only time (index excluded) from the tool logs
log "Computing mapping-only time"
python3 "$SCRIPTS/compute_map_time.py"

# Step 13 — collect CSV
log "Step 13: collecting real-data results"
python3 "$SCRIPTS/13_collect_real.py"

# Step 14 — plot
log "Step 14: plotting real-data results"
python3 "$SCRIPTS/14_plot_real.py"

log "Real-data benchmark complete."
log "  CSV  : $CSV_DIR/results_real.csv"
log "  Plot : $PLOTS_DIR/real_benchmark.png"
