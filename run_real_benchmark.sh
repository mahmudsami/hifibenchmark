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
#                references downloaded, synpact index built (reused from sim arm).
#
# Usage: run_real_benchmark.sh [--force]
#   --force   re-map everything, ignoring cached PAFs (keeps the downloaded reads)

set -euo pipefail
BENCH_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$BENCH_DIR/config.sh"

SCRIPTS="$BENCH_DIR/scripts"

# Mappers to run. Override the set with MAPPERS_OVERRIDE="minimap2 blend ..."
if [ -n "${MAPPERS_OVERRIDE:-}" ]; then
    read -ra MAPPERS <<< "$MAPPERS_OVERRIDE"
else
    MAPPERS=("minimap2" "blend" "synpact" "mapquik")
fi
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

# need_index <genome> <tag>...  → returns 0 (true) if this genome's indexes must
# be (re)built, 1 (false) if they can be skipped. Because the indexes are deleted
# after mapping (to save disk), a plain re-run would otherwise rebuild them even
# when nothing is left to do. Skip only when BOTH are already collected:
#   (a) the index BUILD metrics for every index-building mapper, AND
#   (b) every mapping PAF for every readset × mapper.
# If either is missing, the index is needed (to measure it, or to map against it).
need_index() {
    local genome="$1"; shift
    local tags=("$@") m tag
    for m in "${MAPPERS[@]}"; do
        case "$m" in
            minimap2|blend|synpact)
                [ -f "$MAPPINGS_DIR/${genome}_${m}_index_metrics.json" ] || return 0 ;;
        esac
    done
    for tag in "${tags[@]}"; do
        for m in "${MAPPERS[@]}"; do
            [ -f "$MAPPINGS_DIR/${genome}_${m}_${tag}.paf" ] || return 0
        done
    done
    return 1   # all index + mapping measurements present → skip the build
}

# One pass per genome: build that genome's indexes, map every readset against
# them, then delete the indexes — so only ONE genome's indexes sit on disk at a
# time (disk is tight). mapquik's single-line reference and the prebuilt indexes
# all live under data/indexes/<genome>/ and are removed together at the end of
# the iteration. Rye's DeepConsensus readset is handled inside the rye iteration
# (before cleanup) so it reuses rye's index instead of forcing a rebuild.
for GENOME in "${REAL_GENOMES[@]}"; do
    # Readsets to map for this genome: the standard real HiFi set, plus rye's
    # DeepConsensus set. Each entry is "<download-readset-arg> <err-token> <tag>".
    READSETS=("hifi $REAL_ERR $REAL_TAG")
    TAGS=("$REAL_TAG")
    if [ "$GENOME" = "rye" ]; then
        READSETS+=("dc $DC_ERR $DC_TAG")
        TAGS+=("$DC_TAG")
    fi

    # Build indexes only if needed. On a completed re-run (all index + mapping
    # measurements already on disk) the build — and the deleted indexes' rebuild —
    # is skipped entirely. --force always rebuilds (it drops mapping outputs).
    if [ "$FORCE" != "1" ] && ! need_index "$GENOME" "${TAGS[@]}"; then
        log "Skip indexing: index + mapping measurements already collected for genome=$GENOME"
    else
        # Prepare mapquik's single-line reference (cached/skipped if present).
        # Built here, just before mapping, rather than up front for all genomes —
        # keeps only this genome's reformatted FASTA on disk.
        if printf '%s\n' "${MAPPERS[@]}" | grep -qx mapquik; then
            log "Prepare mapquik reference  genome=$GENOME"
            bash "$SCRIPTS/04_index_mapquik.sh" "$GENOME"
        fi

        # Build each mapper's index for THIS genome (measured → index_results.csv).
        # mapquik indexes inline, so it has no build step here.
        for IDXM in "${MAPPERS[@]}"; do
            case "$IDXM" in
                minimap2|blend|synpact)
                    log "Index: build $IDXM  genome=$GENOME"
                    bash "$SCRIPTS/04_index_${IDXM}.sh" "$GENOME" ;;
            esac
        done
    fi

    for RS in "${READSETS[@]}"; do
        read -r DLARG ERRTOK TAG <<< "$RS"

        # Step 10 — download this readset's reads
        log "Step 10: download reads  genome=$GENOME tag=$TAG"
        bash "$SCRIPTS/10_download_real_reads.sh" "$GENOME" "$DLARG"

        # --force: drop cached mapping outputs (keep the downloaded reads)
        if [ "$FORCE" = "1" ]; then
            rm -f "$MAPPINGS_DIR/${GENOME}"_*_"${TAG}".paf \
                  "$MAPPINGS_DIR/${GENOME}"_*_"${TAG}".log \
                  "$MAPPINGS_DIR/${GENOME}"_*_"${TAG}"_metrics.json \
                  "$MAPPINGS_DIR/${GENOME}"_*_"${TAG}"_eval.json
        fi

        # Step 4 — map with each tool (reuses simulation runners)
        for MAPPER in "${MAPPERS[@]}"; do
            log "Step 4: map  mapper=$MAPPER genome=$GENOME tag=$TAG"
            if [ "$MAPPER" = "mapquik" ]; then
                bash "$SCRIPTS/04_run_mapquik.sh" "$GENOME" "$ERRTOK" "$REAL_LEN"
            else
                bash "$SCRIPTS/04_map_${MAPPER}.sh" "$GENOME" "$ERRTOK" "$REAL_LEN"
            fi
        done

        # Step 12 — consensus evaluation
        log "Step 12: consensus eval  genome=$GENOME tag=$TAG"
        python3 "$SCRIPTS/12_eval_consensus.py" "$GENOME" "$TAG" "$EVAL_TOLERANCE"
    done

    # Free disk: drop this genome's prebuilt indexes (and mapquik reference) now
    # that every readset has mapped. Build time/RSS/size were stamped into the
    # index metrics JSON at build time, so nothing reported is lost. Bounds peak
    # index disk to one genome. Set KEEP_INDEXES=1 to retain them.
    if [ "${KEEP_INDEXES:-0}" != "1" ]; then
        log "Cleanup: removing prebuilt indexes for genome=$GENOME"
        rm -rf "$INDEX_DIR/$GENOME"
    fi
done

# Derive mapping-only time (index excluded) from the tool logs
log "Computing mapping-only time"
python3 "$SCRIPTS/compute_map_time.py"

# Step 13 — collect CSV
log "Step 13: collecting real-data results"
python3 "$SCRIPTS/13_collect_real.py"
log "Step 13: collecting index build time/memory → index_results.csv"
python3 "$SCRIPTS/collect_index_results.py"

# Step 14 — plot
log "Step 14: plotting real-data results"
python3 "$SCRIPTS/14_plot_real.py"

# Extra: both rye read sets (HiFi + DeepConsensus) × mappers
log "Extra plot: rye HiFi vs DeepConsensus"
python3 "$SCRIPTS/extra_plot_real_rye.py" || true

log "Real-data benchmark complete."
log "  CSV  : $CSV_DIR/results_real.csv"
log "  Plot : $PLOTS_DIR/real_benchmark.png"
