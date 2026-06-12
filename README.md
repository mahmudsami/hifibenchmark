# hifibenchmark

A reproducible benchmark of long-read mappers on **PacBio HiFi** reads across four
plant/animal genomes, comparing mapping **accuracy**, **precision**, **speed**,
and **peak memory**.

**Mappers:** [minimap2](https://github.com/lh3/minimap2) ·
[BLEND](https://github.com/CMU-SAFARI/BLEND) ·
[mapquik](https://github.com/ekimb/mapquik) ·
[strobealign](https://github.com/ksahlin/strobealign) ·
[syncmer-hifi](https://github.com/mahmudsami/syncmer-hifi)

**Genomes** (all gapless / T2T-grade references):

| Genome | Reference | Source |
|--------|-----------|--------|
| Human | T2T-CHM13v2.0 | NCBI `GCF_009914755.1` |
| Maize | Mo17 T2T (`Zm-Mo17-REFERENCE-CAU-2.0`) | MaizeGDB |
| Arabidopsis | Col-CEN v1.2 | `schatzlab/Col-CEN` |
| Rye | Lo7_V3 | NCBI `GCA_965641915.1` |

Reads are produced by a deterministic, pure-Python HiFi simulator
(`scripts/02_simulate_reads.py`) that injects substitutions/indels at an exact
target error rate and writes the ground-truth coordinates directly — so accuracy
is evaluated against known truth (no pbsim/alignment needed). A separate
**real-data arm** maps real HiFi reads and evaluates by consensus-of-mappers.

## Requirements

- **Docker** with `linux/amd64` support. Allocate generous memory in Docker
  Desktop — **≥ 32 GB recommended** (strobealign on the repeat-rich maize genome
  peaks at ~26 GB; with less it will thrash or OOM — see *Notes*).
- **Python 3** with `psutil`, `matplotlib`, `numpy`:
  ```bash
  pip install psutil matplotlib numpy
  ```
- `curl`, `gzip`, `bash`. ~**60 GB free disk** for references + generated reads
  + indexes (reads for each combo are deleted after use to bound peak disk).

## Setup

```bash
# 1. Build the five mapper images (each clones its tool from GitHub at a pinned
#    commit — no local source dirs needed; takes a while the first time).
bash docker/build_images.sh
```

References are downloaded automatically on the first run (Step 1 of the pipeline).

## Run

```bash
# Full simulation benchmark: all 5 mappers × 4 genomes × 4 error rates × 4 read lengths
bash run_benchmark.sh                       # add --force to ignore cached outputs

# Variants (drop heavy mappers — see Notes on strobealign/maize):
bash run_benchmark_no_strobealign.sh            # minimap2, blend, mapquik, syncmer
bash run_benchmark_no_strobealign_no_minimap.sh # blend, mapquik, syncmer

# Real-data arm (real HiFi reads, consensus-of-mappers evaluation):
bash run_real_benchmark.sh
```

Outputs:

- `results/csv/results.csv` — per (genome, mapper, error, length): accuracy,
  precision, mapping rate, mapping time, peak RSS.
- `results/plots/<genome>_accuracy.png` and `_performance.png`.
- Real arm → `results/csv/results_real.csv`, `results/plots/real_benchmark.png`.

## Configuration

Edit `config.sh` to change the sweep:

- `GENOMES`, `ERROR_RATES`, `READ_LENGTHS`
- `NUM_READS` (reads per combo; default 100000)
- `THREADS` (mapping threads; default 8)
- `EVAL_TOLERANCE` (a mapping is correct if its start is within this many bp of truth)

## Pipeline steps

| Step | Script | Does |
|------|--------|------|
| 1 | `scripts/01_download_references.sh` | Download the four references |
| 2 | `scripts/02_simulate_reads.py` | Simulate HiFi reads + truth at an exact error rate |
| 3 | `scripts/04_index_mapquik.sh` | Prepare mapquik's single-line reference (once/genome) |
| 4 | `scripts/04_run_<tool>.sh` | Map with each tool (time + peak RSS) |
| 5 | `scripts/05_evaluate_mapping.py` | Score a mapping against truth |
| 6 | `scripts/06_collect_results.py` | Gather metrics → CSV |
| 7–8 | `scripts/07_plot_accuracy.py`, `08_plot_time_memory.py` | Plots |

To measure **mapping-only** peak memory (excluding index construction), use the
split `scripts/04_index_<tool>.sh` + `scripts/04_map_<tool>.sh` pairs — see
[`scripts/README_index_map_split.md`](scripts/README_index_map_split.md).

## Notes

- **strobealign is the in-development Rust rewrite** (`v0.18.0-alpha`, `main`),
  not a stable C++ release. On the repeat-rich **maize** T2T genome its mapping
  phase peaks at **~26 GB** (vs ~8 GB on older fragmented assemblies) and is
  several times slower. If your Docker VM has < ~28 GB it will thrash/OOM — use
  `run_benchmark_no_strobealign.sh`, or raise Docker's memory.
- **mapquik requires a single-line, uppercase FASTA**; feeding it the stock
  multi-line genome silently drops its mapping rate to ~1%. The pipeline prepares
  the correct reference automatically (`scripts/04_index_mapquik.sh`).
- Generated data (`data/`, `results/`) is git-ignored; everything regenerates
  deterministically from the scripts.

## Layout

```
config.sh                 # sweep parameters + directory layout
docker/                   # one Dockerfile per mapper + build_images.sh
scripts/                  # pipeline steps (download, simulate, map, eval, collect, plot)
run_benchmark.sh          # full simulation benchmark
run_real_benchmark.sh     # real-data arm
data/ , results/          # generated (git-ignored)
```
