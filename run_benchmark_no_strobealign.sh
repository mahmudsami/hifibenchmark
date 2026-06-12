#!/usr/bin/env bash
# Simulation benchmark WITHOUT strobealign.
#
# strobealign is a short-read mapper; on the repeat-rich T2T maize (Mo17) genome
# its per-read seed/candidate structures explode to ~27 GiB, exhausting the
# Docker VM (27.36 GiB) and thrashing. This entry point runs the identical
# simulation pipeline as run_benchmark.sh but with the strobealign arm dropped.
#
# Everything else (flags like --force, per-genome thread/read overrides, plots)
# is unchanged — it simply sets MAPPERS_OVERRIDE and delegates to run_benchmark.sh.
#
# Usage: run_benchmark_no_strobealign.sh [--force]

exec env MAPPERS_OVERRIDE="minimap2 blend mapquik syncmer" \
    bash "$(cd "$(dirname "$0")" && pwd)/run_benchmark.sh" "$@"
