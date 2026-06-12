# Separated indexing / mapping runners

The original `04_run_<tool>.sh` scripts build the reference index *inline* at
mapping time, so their reported peak RSS mixes index construction with mapping.
These `04_index_<tool>.sh` / `04_map_<tool>.sh` pairs split the two phases so the
mapping metrics capture **mapping-only** peak memory (loading a pre-built index +
aligning), excluding the index-construction peak.

## Workflow

```bash
# 1. Build every index once (per genome)
bash scripts/04_build_all_indexes.sh                 # or pass specific genomes

# 2. Map against the pre-built index (mapping-only peak RSS)
bash scripts/04_map_minimap2.sh    human 0.001 15000
bash scripts/04_map_blend.sh       human 0.001 15000
bash scripts/04_map_strobealign.sh human 0.001 15000
bash scripts/04_map_syncmer.sh     human 0.001 15000
bash scripts/04_map_mapquik.sh     human 0.001 15000   # see mapquik caveat below
```

The `04_map_*` scripts write the same `*_metrics.json` / `*.paf` filenames as the
original runners, so `06_collect_results.py` and evaluation are unchanged — the
only difference is that `peak_rss_mb` now reflects mapping alone.

## Per-tool index mechanism

| Tool        | Index build            | Map uses                 | Index location                         |
|-------------|------------------------|--------------------------|----------------------------------------|
| minimap2    | `minimap2 -d`          | loads `.mmi`             | `data/indexes/<g>/minimap2_maphifi.mmi`|
| blend       | `blend -d`             | loads `.bl`              | `data/indexes/<g>/blend_maphifi.bl`    |
| strobealign | `strobealign -i`       | `--use-index`            | `data/references/<g>/genome.fa.gz.r*.sti` |
| syncmer     | `--build-index`        | `--map <reads> <idx>`    | `data/indexes/<g>/syncmer_hifi.idx`    |
| mapquik     | prepare single-line FASTA | inline k-min-mer index | `data/indexes/<g>/genome.mapquik.fa.gz` |

**mapquik** has no serialized index — it rebuilds its k-min-mer index in memory
every run, so its peak RSS necessarily includes index construction (no true
mapping-only split). What `04_index_mapquik.sh` *does* provide is mandatory:
mapquik requires a **single-line, uppercase** FASTA, and feeding it the stock
multi-line, soft-masked `genome.fa.gz` silently collapses its mapping rate to
~1%. Both `04_run_mapquik.sh` and `04_map_mapquik.sh` map against the prepared
reference (and build it automatically if missing). The master runners
(`run_benchmark.sh`, `run_real_benchmark.sh`) prepare it **once per genome up
front**, before the step-4 mapping loop, so there's no mid-benchmark stall. The
rewrite runs in Python (`fasta_to_singleline.py`, ~7x faster than macOS awk) and
writes `gzip -1` (mapquik reads any level identically).
See <https://github.com/ekimb/mapquik/issues/17#issuecomment-1895882175>.

Index-build metrics are written to `*_<tool>_index_metrics.json` for reference.
