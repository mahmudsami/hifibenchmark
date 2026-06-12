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
GENOMES=("human" "maize" "arabidopsis" "rye")

# Error rates as fractions (0.001 = 0.1 %, 0.005 = 0.5 %, 0.01 = 1 %)
ERROR_RATES=("0" "0.001" "0.005" "0.01")

# Mean read lengths in bp
READ_LENGTHS=("10000" "15000" "20000" "25000")

# Fraction of genome to cover when simulating (used only if NUM_READS is empty)
SIM_DEPTH="0.05"

# Fixed number of reads per simulation (per genome × error × length combo).
# Takes precedence over SIM_DEPTH. Leave empty to use depth-based counts.
NUM_READS="${NUM_READS:-100000}"

# Delete each combo's simulated reads after its mappers finish, to bound peak
# disk to one combo (reads are gzipped and regenerate deterministically).
# Set to 1 to keep all read files instead.
KEEP_READS="0"

# Threads for mapping tools
THREADS="${THREADS:-8}"

# Evaluation window: a mapping is "correct" if its start falls within
# EVAL_TOLERANCE bp of the true start
EVAL_TOLERANCE=1000
