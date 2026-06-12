#!/usr/bin/env bash
# Simulation benchmark WITHOUT strobealign and WITHOUT minimap2.
#
# Runs only blend, mapquik, and syncmer. strobealign exhausts the Docker VM on
# the repeat-rich T2T maize (see run_benchmark_no_strobealign.sh); this variant
# additionally drops minimap2 (e.g. to focus on the remaining mappers or to save
# time). Identical pipeline otherwise — sets MAPPERS_OVERRIDE and delegates to
# run_benchmark.sh, so flags like --force still work.
#
# Usage: run_benchmark_no_strobealign_no_minimap.sh [--force]

exec env MAPPERS_OVERRIDE="blend mapquik syncmer" \
    bash "$(cd "$(dirname "$0")" && pwd)/run_benchmark.sh" "$@"
