#!/usr/bin/env bash
# Build every tool's index for every genome, once. Run this before the
# 04_map_* scripts so mapping-phase peak RSS excludes index construction.
#
# Usage: 04_build_all_indexes.sh [genome ...]   (default: all in config.sh)

set -euo pipefail
HERE="$(dirname "$0")"
source "$HERE/_runner_lib.sh"

TARGETS=("$@")
[ ${#TARGETS[@]} -eq 0 ] && TARGETS=("${GENOMES[@]}")

for g in "${TARGETS[@]}"; do
    echo "===== indexing $g ====="
    bash "$HERE/04_index_minimap2.sh"    "$g"
    bash "$HERE/04_index_blend.sh"       "$g"
    bash "$HERE/04_index_strobealign.sh" "$g"
    bash "$HERE/04_index_syncmer.sh"     "$g"
    bash "$HERE/04_index_mapquik.sh"     "$g"
done

echo "All indexes built. Note: mapquik has no serialized index — 04_index_mapquik"
echo "only prepares its required single-line FASTA; its peak RSS still includes"
echo "the in-memory k-min-mer index it rebuilds every run."
