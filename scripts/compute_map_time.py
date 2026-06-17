#!/usr/bin/env python3
"""
Derive MAPPING-ONLY time (excluding reference index construction) for every
mapping run and write it into the run's metrics JSON as "map_time_s".

How mapping-only time is obtained per tool (all from the container logs, so all
exclude Docker startup and index construction — i.e. the pure read-mapping phase
with the index already in memory):

  minimap2 / BLEND : "Real time: Z" − "[M::main::T*..] loaded/built the index"
                     (minimap2 builds its index on the fly; T is that build time)
  mapquik          : "Mapped query sequences in X(ms|s)"  (its own map-phase clock)
  synpact     : GNU time -v "Elapsed" − per-genome index-LOAD baseline
                     (synpact loads a prebuilt index; baseline measured separately)

Usage: python3 compute_map_time.py
Processes every *_metrics.json in results/mappings/ that has a matching *.log.
"""
import os, re, json, glob

BENCH_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPINGS_DIR = os.path.join(BENCH_DIR, "results", "mappings")

# synpact index-LOAD baselines (seconds), measured by mapping a 20-read
# file against the prebuilt LEAN index (Elapsed ≈ load time). The lean L3-L6
# index (~0.5 GB) loads in <1 s, vs ~9.5 s for the old L0-L6 index.
SYNPACT_LOAD_BASELINE = {"human": 0.8, "maize": 0.6}

MAPPERS = ["minimap2", "blend", "mapquik", "synpact"]

RE_REAL   = re.compile(r"Real time:\s*([\d.]+)\s*sec")
RE_INDEX  = re.compile(r"\[M::main::([\d.]+)\*[\d.]+\]\s*loaded/built the index")
RE_MQMAP  = re.compile(r"Mapped query sequences in\s*([\d.]+)\s*(ms|us|µs|s)\b")
RE_ELAPS  = re.compile(r"Elapsed \(wall clock\) time[^\n]*?(\d+:[\d.:]+)\s*$", re.M)


def hms_to_sec(s: str) -> float:
    parts = s.split(":")
    parts = [float(p) for p in parts]
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


def map_time_for(mapper: str, genome: str, log_path: str, wall: float = None):
    txt = open(log_path, "rt", errors="replace").read()

    if mapper in ("minimap2", "blend"):
        real  = RE_REAL.search(txt)
        idxs  = RE_INDEX.findall(txt)
        if real and idxs:
            return max(float(real.group(1)) - float(idxs[-1]), 0.01)

    elif mapper == "mapquik":
        m = RE_MQMAP.search(txt)
        if m:
            v, unit = float(m.group(1)), m.group(2)
            return v / 1000.0 if unit in ("ms",) else (v / 1e6 if unit in ("us", "µs") else v)

    elif mapper == "synpact":
        m = RE_ELAPS.search(txt)
        if m:
            elapsed = hms_to_sec(m.group(1))
            # time -v Elapsed can never exceed run_timed's wall; if a stale log
            # says otherwise, fall back to the trustworthy wall measurement.
            if wall is not None:
                elapsed = min(elapsed, wall)
            base = SYNPACT_LOAD_BASELINE.get(genome, 0.0)
            return max(elapsed - base, 0.01)

    return None


def main():
    n = 0
    for metrics_path in sorted(glob.glob(os.path.join(MAPPINGS_DIR, "*_metrics.json"))):
        base = os.path.basename(metrics_path)[:-len("_metrics.json")]
        # base = <genome>_<mapper>_<tag>
        mapper = next((m for m in MAPPERS if f"_{m}_" in f"_{base}_"), None)
        if mapper is None:
            continue
        genome = base.split("_")[0]
        log_path = os.path.join(MAPPINGS_DIR, base + ".log")
        if not os.path.exists(log_path):
            continue

        with open(metrics_path) as f:
            metrics = json.load(f)

        mt = map_time_for(mapper, genome, log_path, wall=metrics.get("wall_time_s"))
        if mt is None:
            print(f"  ! could not parse map time: {base}")
            continue

        # Safety net: mapping time can never exceed the total wall time.
        wall = metrics.get("wall_time_s")
        if wall is not None and mt > wall:
            mt = wall
        metrics["map_time_s"] = round(mt, 3)
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
        n += 1

    print(f"Updated map_time_s in {n} metrics files.")


if __name__ == "__main__":
    main()
