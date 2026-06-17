#!/usr/bin/env bash
# Master benchmark runner.
# Calls each step in order for every (genome × error_rate × read_length) combo.
#
# Steps:
#   1  Download reference genomes
#   3  Prepare mapquik's single-line reference, once per genome
#   2  Simulate HiFi reads at an exact error rate (also writes truth TSV)
#   4  Map with each tool (minimap2 / blend / mapquik / synpact)
#   5  Evaluate each mapping
#   6  Collect all results into results/csv/results.csv
#   7  Plot accuracy & precision
#   8  Plot time & memory
#
# Prerequisites:
#   Docker images built (bash docker/build_images.sh)
#   Python packages                   — pip install psutil matplotlib numpy
#
# Usage: run_benchmark.sh [--force]
#   --force   re-simulate reads and re-map everything, ignoring cached outputs

set -euo pipefail
BENCH_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$BENCH_DIR/config.sh"

# Mappers to run. Override the set with MAPPERS_OVERRIDE="minimap2 blend ..."
if [ -n "${MAPPERS_OVERRIDE:-}" ]; then
    read -ra MAPPERS <<< "$MAPPERS_OVERRIDE"
else
    MAPPERS=("minimap2" "blend" "mapquik" "synpact")
fi
SCRIPTS="$BENCH_DIR/scripts"

# Parse flags
FORCE=0
for arg in "$@"; do
    [ "$arg" = "--force" ] && FORCE=1
done

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# need_index <genome> → returns 0 (true) if this genome's indexes must be
# (re)built, 1 (false) if they can be skipped. The indexes are deleted after
# mapping (to save disk), so a plain re-run would otherwise rebuild them even
# when nothing is left to do. Skip only when BOTH are already present:
#   (a) the index BUILD metrics for every index-building mapper, AND
#   (b) every mapping PAF for every error-rate × read-length × mapper combo.
need_index() {
    local genome="$1" m err len
    for m in "${MAPPERS[@]}"; do
        case "$m" in
            minimap2|blend|synpact)
                [ -f "$MAPPINGS_DIR/${genome}_${m}_index_metrics.json" ] || return 0 ;;
        esac
    done
    for err in "${ERROR_RATES[@]}"; do
        for len in "${READ_LENGTHS[@]}"; do
            for m in "${MAPPERS[@]}"; do
                [ -f "$MAPPINGS_DIR/${genome}_${m}_err${err}_len${len}.paf" ] || return 0
            done
        done
    done
    return 1   # all index + mapping outputs present → skip the build
}

# ── Step 1 — Download references ─────────────────────────────────────────────
log "Step 1: downloading references"
bash "$SCRIPTS/01_download_references.sh"

# ── Step 3 — Prepare mapquik's single-line reference ONCE per genome ──────────
# mapquik needs a single-line, uppercase FASTA. Building it up front (rather than
# lazily on the first mapquik run) avoids a multi-minute stall in the middle of
# the mapping loop; the per-genome rewrite is cached and skipped if it exists.
if printf '%s\n' "${MAPPERS[@]}" | grep -qx mapquik; then
    for GENOME in "${GENOMES[@]}"; do
        log "Step 3: prepare mapquik reference  genome=$GENOME"
        bash "$SCRIPTS/04_index_mapquik.sh" "$GENOME"
    done
fi

# ── Steps 2-5 — One pass per combination ─────────────────────────────────────
for GENOME in "${GENOMES[@]}"; do
    REF="$REFS_DIR/$GENOME/genome.fa.gz"

    # Same settings for every genome: 8 threads, 100k reads (rye no longer reduced)
    export THREADS="${THREADS:-8}"
    export NUM_READS="${NUM_READS:-100000}"

    # Build each mapper's index ONCE per genome, recording build time + peak RSS
    # (→ index_results.csv). minimap2/blend/synpact map against this
    # prebuilt index below, so the per-combo mapping metrics exclude indexing and
    # the index is not rebuilt 16×. mapquik indexes inline → no build step here.
    # Skipped entirely on a completed re-run (all index + mapping outputs present),
    # so the deleted indexes aren't rebuilt for nothing. --force always rebuilds.
    if [ "$FORCE" != "1" ] && ! need_index "$GENOME"; then
        log "Skip indexing: index + mapping outputs already exist for genome=$GENOME"
    else
        for IDXM in "${MAPPERS[@]}"; do
            case "$IDXM" in
                minimap2|blend|synpact)
                    log "Index: build $IDXM  genome=$GENOME"
                    bash "$SCRIPTS/04_index_${IDXM}.sh" "$GENOME" ;;
            esac
        done
    fi

    for ERR in "${ERROR_RATES[@]}"; do
        for LEN in "${READ_LENGTHS[@]}"; do
            TAG="err${ERR}_len${LEN}"
            READS_GZ="$READS_DIR/$GENOME/${TAG}.fastq.gz"
            READS_FQ="$READS_DIR/$GENOME/${TAG}.fastq"
            TRUTH="$TRUTH_DIR/$GENOME/${TAG}.tsv"

            # --force: drop all cached outputs for this combo so they regenerate
            if [ "$FORCE" = "1" ]; then
                rm -f "$READS_GZ" "$READS_FQ" "$TRUTH" \
                      "$MAPPINGS_DIR/${GENOME}"_*_"${TAG}".paf \
                      "$MAPPINGS_DIR/${GENOME}"_*_"${TAG}".log \
                      "$MAPPINGS_DIR/${GENOME}"_*_"${TAG}"_metrics.json \
                      "$MAPPINGS_DIR/${GENOME}"_*_"${TAG}"_eval.json
            fi

            # Do we need to (re)simulate? Only if some mapper still lacks a PAF.
            NEED=0
            for MAPPER in "${MAPPERS[@]}"; do
                [ -f "$MAPPINGS_DIR/${GENOME}_${MAPPER}_${TAG}.paf" ] || NEED=1
            done

            # Step 2 — Simulate reads (gzipped; also writes ground-truth TSV)
            if [ "$NEED" = "1" ]; then
                log "Step 2: simulate  genome=$GENOME err=$ERR len=$LEN n_reads=${NUM_READS:-depth}"
                python3 "$SCRIPTS/02_simulate_reads.py" "$GENOME" "$ERR" "$LEN" ${NUM_READS:+$NUM_READS}
            fi

            # Steps 4-5 — Map and evaluate for each tool
            for MAPPER in "${MAPPERS[@]}"; do
                OUT_PAF="$MAPPINGS_DIR/${GENOME}_${MAPPER}_${TAG}.paf"
                EVAL_JSON="$MAPPINGS_DIR/${GENOME}_${MAPPER}_${TAG}_eval.json"

                # Step 4 — Map. mapquik indexes inline (04_run_mapquik); the rest
                # map against the prebuilt index (04_map_*) → mapping-only metrics.
                log "Step 4: map  mapper=$MAPPER genome=$GENOME err=$ERR len=$LEN"
                if [ "$MAPPER" = "mapquik" ]; then
                    bash "$SCRIPTS/04_run_mapquik.sh" "$GENOME" "$ERR" "$LEN"
                else
                    bash "$SCRIPTS/04_map_${MAPPER}.sh" "$GENOME" "$ERR" "$LEN"
                fi

                # Step 5 — Evaluate (needs only truth + PAF, not the reads)
                if [ -f "$OUT_PAF" ] && [ ! -f "$EVAL_JSON" ]; then
                    log "Step 5: evaluate  mapper=$MAPPER genome=$GENOME err=$ERR len=$LEN"
                    python3 "$SCRIPTS/05_evaluate_mapping.py" \
                        "$TRUTH" "$OUT_PAF" "$EVAL_JSON" "$EVAL_TOLERANCE"
                fi
            done

            # Free disk: drop this combo's reads (truth kept; reads regenerate
            # deterministically on demand). Bounds peak disk to one combo.
            if [ "${KEEP_READS:-0}" != "1" ]; then
                rm -f "$READS_GZ" "$READS_FQ"
            fi
        done
    done

    # Free disk: drop this genome's prebuilt indexes now that every combo has
    # mapped against them. Build time/RSS/size were stamped into the index
    # metrics JSON at build time, so nothing reported is lost. Bounds peak index
    # disk to one genome. Set KEEP_INDEXES=1 to retain them.
    if [ "${KEEP_INDEXES:-0}" != "1" ]; then
        log "Cleanup: removing prebuilt indexes for genome=$GENOME"
        rm -rf "$INDEX_DIR/$GENOME"
    fi
done

# ── Derive mapping-only time (index excluded) from the tool logs ─────────────
log "Computing mapping-only time"
python3 "$SCRIPTS/compute_map_time.py"

# ── Step 6 — Collect results into CSV ────────────────────────────────────────
log "Step 6: collecting results"
python3 "$SCRIPTS/06_collect_results.py"
log "Step 6: collecting index build time/memory → index_results.csv"
python3 "$SCRIPTS/collect_index_results.py"

# ── Step 7 — Plot accuracy and precision ─────────────────────────────────────
log "Step 7: plotting accuracy"
python3 "$SCRIPTS/07_plot_accuracy.py"

# ── Step 8 — Plot time and memory ────────────────────────────────────────────
log "Step 8: plotting performance"
python3 "$SCRIPTS/08_plot_time_memory.py"

log "Benchmark complete."
log "  CSV   : $CSV_DIR/results.csv"
log "  Plots : $PLOTS_DIR/"
