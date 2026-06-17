#!/usr/bin/env bash
# Central configuration for the HiFi mapper benchmark.
# Edit this file to match your environment before running.

BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Data directories ──────────────────────────────────────────────────────────
DATA_DIR="$BENCH_DIR/data"
REFS_DIR="$DATA_DIR/references"
READS_DIR="$DATA_DIR/reads"
TRUTH_DIR="$DATA_DIR/truth"
INDEX_DIR="$DATA_DIR/indexes"

# ── Results directories ───────────────────────────────────────────────────────
RESULTS_DIR="$BENCH_DIR/results"
MAPPINGS_DIR="$RESULTS_DIR/mappings"
CSV_DIR="$RESULTS_DIR/csv"
PLOTS_DIR="$RESULTS_DIR/plots"

# Mappers run inside Docker (see docker/build_images.sh); no host tool paths are
# needed. Reads are produced by the pure-Python simulator scripts/02_simulate_reads.py
# (no pbsim/QSHMM dependency).

# ── Benchmark parameters ──────────────────────────────────────────────────────
GENOMES=("human" "human_y" "maize" "arabidopsis" "rye")

# Error rates as fractions (0.001 = 0.1 %, 0.005 = 0.5 %, 0.01 = 1 %)
ERROR_RATES=("0" "0.001" "0.005" "0.01")

# Mean read lengths in bp
READ_LENGTHS=("10000" "15000" "20000" "25000")

# Fraction of genome to cover when simulating (used only if NUM_READS is empty)
SIM_DEPTH="0.05"

# Fixed number of reads per simulation (per genome × error × length combo).
# Takes precedence over SIM_DEPTH. Leave empty to use depth-based counts.
NUM_READS="${NUM_READS:-100000}"

# Keep simulated reads after each combo's mappers finish (set to 0 to delete
# them and bound peak disk to one combo). Reads are kept so they stay matched to
# their truth: the simulator is NOT reproducible across runs (its RNG seed uses
# Python's per-process-randomized hash()), so a deleted read set cannot be
# regenerated identically — only alongside a fresh, different truth.
KEEP_READS="1"

# Delete each genome's prebuilt indexes once all of that genome's mapping combos
# finish (set to 1 to keep them). Indexes are large; build time, peak RSS, and
# on-disk size are stamped into <genome>_<mapper>_index_metrics.json at build
# time (record_index_size), so they can be removed without losing any reported
# metric. Bounds peak index disk to a single genome instead of all genomes at
# once. A later --force re-run rebuilds any index it needs.
KEEP_INDEXES="${KEEP_INDEXES:-0}"

# Threads for mapping tools
THREADS="${THREADS:-8}"

# Evaluation window: a mapping is "correct" if its start falls within
# EVAL_TOLERANCE bp of the true start
EVAL_TOLERANCE=1000
