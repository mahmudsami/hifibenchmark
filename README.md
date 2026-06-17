# hifibenchmark

A reproducible benchmark of long-read mappers on **PacBio HiFi** reads across
gapless / T2T-grade plant and animal genomes, comparing mapping **accuracy**,
**precision**, **speed**, and **peak memory**.

**Mappers:** [minimap2](https://github.com/lh3/minimap2) ·
[BLEND](https://github.com/CMU-SAFARI/BLEND) ·
[mapquik](https://github.com/ekimb/mapquik) ·
[synpact](https://github.com/mahmudsami/synpact)

The benchmark has three arms:

1. **Simulation** (`run_benchmark.sh`) — simulated HiFi reads with *known* truth,
   swept over error rate and read length. The primary accuracy benchmark.
2. **Real data** (`run_real_benchmark.sh`) — real public HiFi reads with no
   truth, evaluated by consensus-of-mappers.
3. **Lungfish** (`scripts/lungfish_*.sh`) — a large-genome (~35 Gb) stress test,
   run natively, comparing only minimap2 and synpact.

---

## Genomes & references

All references are gapless / T2T-grade and downloaded automatically on the first
run (`scripts/01_download_references.sh`).

| Genome | Reference | Accession / source |
|--------|-----------|--------------------|
| Human | T2T-CHM13v2.0 | NCBI `GCF_009914755.1` |
| Human-Y | chrY of T2T-CHM13v2.0 (`NC_060948.1`), extracted | derived from the human reference |
| Maize | Mo17 T2T (`Zm-Mo17-REFERENCE-CAU-2.0`) | MaizeGDB |
| Arabidopsis | Col-CEN v1.2 (Col-0 T2T) | `schatzlab/Col-CEN` |
| Rye | Lo7_V3 (near-complete) | NCBI `GCA_965641915.1` |

`human_y` is a small, highly repetitive (ampliconic/satellite) stress-test
genome used only in the simulation arm.

## Real HiFi read datasets

Used by the real-data arm; streamed from ENA/SRA and the first ~100 k reads kept
(`scripts/10_download_real_reads.sh`). Reads are matched to the same line as the
reference, so divergence reflects mapper behaviour rather than cross-line variation.

| Genome | Reads | Accession | Matches reference? |
|--------|-------|-----------|--------------------|
| Human | HG002 PacBio **Revio** HiFi (HPRC) | `SRR34290932` | HG002 vs CHM13 — cross-individual (~0.1 %); CHM13v2.0's chrY *is* HG002's |
| Maize | Mo17 HiFi | `SRR15447414` | ✅ same line as Mo17 reference |
| Arabidopsis | Col-0 HiFi | `ERR13987671` | ✅ same line as Col-CEN |
| Rye (HiFi) | Lo7 **Revio** HiFi | `ERR15194059` | ✅ same line as Lo7 |
| Rye (DeepConsensus) | Lo7 **Revio** DeepConsensus | `ERR15194060` | ✅ same line as Lo7 |

> ENA stores these FASTQs under a `_subreads.fastq.gz` filename by default; the
> content is genuine HiFi/CCS (mean read length ~15–20 kb, per-base Q ≥ 20).

---

## The benchmarks explained

### 1. Simulation arm — `run_benchmark.sh`

The primary accuracy benchmark, run against **known ground truth**.

- A deterministic, pure-Python HiFi simulator (`scripts/02_simulate_reads.py`)
  draws reads from the reference and injects substitutions/indels at an **exact**
  target error rate, writing the true genomic coordinates of every read directly.
  No pbsim/alignment is needed — accuracy is scored against the truth file.
- **Sweep:** every combination of
  - genome ∈ {human, human_y, maize, arabidopsis, rye}
  - error rate ∈ {0 %, 0.1 %, 0.5 %, 1 %}
  - read length ∈ {10, 15, 20, 25} kb
  - mapper ∈ {minimap2, BLEND, mapquik, synpact}

  at 100 000 reads per combination.
- **Scoring** (`scripts/05_evaluate_mapping.py`): a read is *correct* if its
  reported start is within `EVAL_TOLERANCE` (1000 bp) of its true start.
  Reports accuracy, precision, mapping rate, mapping-only time and peak RSS.
- **Outputs:** `results/csv/results.csv`, plus grid plots
  `results/plots/{accuracy,precision,map_time,peak_rss}.png`
  (rows = error rate, columns = genome).

### 2. Real-data arm — `run_real_benchmark.sh`

Real reads have no ground truth, so this arm uses a **consensus-of-mappers**
evaluation (`scripts/12_eval_consensus.py`): for each read, a locus is accepted
as "truth" only where ≥ 2 mapper families place it on the same chromosome within
tolerance; every tool is then scored against that consensus.

- Genomes: human, maize, arabidopsis, rye (no human_y). Rye is run twice — once
  with standard HiFi reads and once with the DeepConsensus readset.
- **Outputs:** `results/csv/results_real.csv` and the grid figure
  `results/plots/real_benchmark.png` (rows = genome/readset, columns = metric).

### 3. Lungfish arm — `scripts/lungfish_*.sh`

A standalone, **native (non-Docker)** stress test on a ~35 Gb lungfish genome —
an order of magnitude larger than the other references — comparing **minimap2 vs
synpact** only. It checks index-build feasibility and mapping under extreme
memory/disk pressure (the scripts decompress transiently and delete intermediate
files to stay within disk). Outputs land in `results/lungfish/`.

---

## Requirements

- **Docker** with `linux/amd64` support. Allocate generous memory in Docker
  Desktop — **≥ 16 GB recommended** (minimap2 on the human genome peaks at ~12 GB).
- **Python 3** with `psutil`, `matplotlib`, `numpy`:
  ```bash
  pip install psutil matplotlib numpy
  ```
- `curl`, `gzip`, `bash`. ~**60 GB free disk** for references + generated reads +
  indexes. Per-combo reads and per-genome indexes are deleted after use to bound
  peak disk (see *Configuration*).
- The lungfish arm additionally needs a native `synpact` and `minimap2` binary
  and far more disk; it is independent of the Docker arms.

## Setup

```bash
# Build the four mapper images (slow the first time). All four mappers clone
# their tool from public GitHub at a pinned commit.
bash docker/build_images.sh
```

References download automatically on the first pipeline run.

## Running

```bash
# Simulation arm: 5 genomes × 4 error rates × 4 read lengths × 4 mappers
bash run_benchmark.sh                 # add --force to ignore cached outputs

# Real-data arm: real HiFi reads + consensus-of-mappers evaluation
bash run_real_benchmark.sh            # add --force to re-map (keeps downloaded reads)

# Subset the mappers in either arm via MAPPERS_OVERRIDE, e.g. drop minimap2:
MAPPERS_OVERRIDE="blend mapquik synpact" bash run_benchmark.sh
```

Both arms are **resumable**: cached reads, mappings and evaluations are skipped,
and on a fully-completed re-run the per-genome index build is skipped entirely.

## Configuration

Edit `config.sh`:

| Variable | Meaning | Default |
|----------|---------|---------|
| `GENOMES`, `ERROR_RATES`, `READ_LENGTHS` | the simulation sweep | see file |
| `NUM_READS` | reads per combination | 100000 |
| `THREADS` | mapping/indexing threads | 8 |
| `EVAL_TOLERANCE` | max bp from truth to count a hit as correct | 1000 |
| `KEEP_READS` | keep each combo's reads (`0` = delete to save disk) | 1 |
| `KEEP_INDEXES` | keep each genome's indexes (`0` = delete after its mapping finishes) | 0 |

With `KEEP_INDEXES=0` (the default), an index's build time, peak RSS and on-disk
size are recorded into its metrics JSON *before* deletion, so nothing reported is
lost and only one genome's indexes sit on disk at a time.

## How mapping-only memory is measured

To make peak RSS reflect **mapping alone** (not index construction), index build
and mapping are split: `scripts/04_index_<tool>.sh` builds and times the index
once per genome (→ `results/csv/index_results.csv`), and
`scripts/04_map_<tool>.sh` maps every read set against that pre-built index.
mapquik has no serialized index — it builds its k-min-mer index inline each run.
See [`scripts/README_index_map_split.md`](scripts/README_index_map_split.md).

## Pipeline steps

| Step | Script | Does |
|------|--------|------|
| 1 | `scripts/01_download_references.sh` | Download the references |
| 2 | `scripts/02_simulate_reads.py` | Simulate HiFi reads + truth at an exact error rate |
| 3 | `scripts/04_index_mapquik.sh` | Prepare mapquik's single-line reference (once/genome) |
| 4a | `scripts/04_index_<tool>.sh` | Build + time each tool's index (once/genome) |
| 4b | `scripts/04_map_<tool>.sh` / `04_run_mapquik.sh` | Map (mapping-only time + peak RSS) |
| 5 | `scripts/05_evaluate_mapping.py` | Score a mapping against truth (simulation arm) |
| 6 | `scripts/06_collect_results.py` | Gather simulation metrics → `results.csv` |
| 7–8 | `scripts/07_plot_accuracy.py`, `08_plot_time_memory.py` | Simulation plots |
| 10 | `scripts/10_download_real_reads.sh` | Fetch real HiFi reads (real arm) |
| 12 | `scripts/12_eval_consensus.py` | Consensus-of-mappers scoring (real arm) |
| 13–14 | `scripts/13_collect_real.py`, `14_plot_real.py` | Real-arm CSV + plot |

The appendix tables for the paper are generated straight from the result CSVs by
`scripts/make_appendix_tables.py` → `paper/appendix_tables.tex`.

## Notes

- **mapquik requires a single-line, uppercase FASTA**; feeding it the stock
  multi-line genome silently drops its mapping rate to ~1 %. The pipeline prepares
  the correct reference automatically (`scripts/04_index_mapquik.sh`).
- **Real reads are line-matched to the reference** (see the table above) so that
  measured accuracy reflects the mapper, not cross-cultivar/individual divergence.
- Generated data (`data/`, `results/`) is git-ignored; everything regenerates
  deterministically from the scripts.

## Extra plots

Focused figures generated on top of the standard grid plots:

| Script | Output | Shows |
|--------|--------|-------|
| `scripts/extra_plot_sim_bar.py [err] [len]` | `results/plots/sim_bar_err<E>_len<L>.png` | One operating point (default 0.5 % err, 20 kb) as 2×2 metric bar charts; groups = human/maize/rye, bars = mappers |
| `scripts/extra_plot_real_rye.py` | `results/plots/real_rye.png` | Both rye read sets (HiFi + DeepConsensus) across accuracy / mapping time / peak RSS, bars = mappers |
| `scripts/extra_plot_lungfish_err05.py [genome]` | `results/lungfish/<genome>_err0.005_2x2.png` | The 0.5 %-error slice of minimap2-vs-synpact as a 2×2 metric grid (x = read length) |
| `scripts/extra_plot_index.py` | `results/plots/index_resources.png` | Index build time + peak RSS per genome, bars = builders — including **synpact at 1 thread** (`synpact1t`) next to the default 8-thread synpact |

The simulation bar, real-rye and index-resources plots run automatically at the
end of `run_benchmark.sh` / `run_real_benchmark.sh`; the lungfish one is run
manually after the sweep.

The index-resources plot needs an extra single-thread synpact index build, which
the pipeline now performs per genome (`scripts/04_index_synpact_1t.sh`, metrics
only — the 8-thread index is what mapping uses) and records as the `synpact1t`
rows in `results/csv/index_results.csv`.

## Layout

```
config.sh                 # sweep parameters + directory layout
docker/                   # one Dockerfile per mapper + build_images.sh
scripts/                  # pipeline steps (download, simulate, index, map, eval, collect, plot)
run_benchmark.sh          # simulation arm
run_real_benchmark.sh     # real-data arm
scripts/lungfish_*.sh     # large-genome stress test (native)
paper/appendix_tables.tex # auto-generated results tables
data/ , results/          # generated (git-ignored)
```
