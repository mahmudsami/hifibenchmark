#!/usr/bin/env python3
"""
Consensus-of-mappers evaluation for REAL reads (no ground truth).

For one genome, reads the mappers' PAFs and builds a per-read "consensus
truth": a locus accepted only where >= MIN_AGREE mappers place the read on the
same chromosome within TOL bp of each other. Each tool is then scored against
that consensus.

Usage:
    python3 12_eval_consensus.py <genome> [tag=errreal_len100k] [tol=1000] [min_agree=2]

Reads : results/mappings/<genome>_<mapper>_<tag>.paf
Writes: results/mappings/<genome>_<mapper>_<tag>_eval.json   (per tool)
"""
import sys, os, json, statistics

BENCH_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPINGS_DIR = os.path.join(BENCH_DIR, "results", "mappings")
MAPPERS      = ["minimap2", "blend", "synpact", "mapquik"]
DEFAULT_TAG  = "errreal_len100k"

# Consensus is counted per ALGORITHM FAMILY, not per mapper. Each mapper here is
# its own family; agreement needs >= min_agree DISTINCT families.
FAMILY = {
    "minimap2": "minimap2", "blend": "blend",
    "synpact": "synpact", "mapquik": "mapquik",
}


def best_per_read(paf_path: str) -> dict:
    """read_name -> (chr, start) for the highest-MAPQ alignment."""
    best = {}
    if not os.path.exists(paf_path):
        return best
    with open(paf_path) as f:
        for line in f:
            p = line.split("\t")
            if len(p) < 12 or p[5] == "*":
                continue
            name, chrom, start, mapq = p[0], p[5], int(p[7]), int(p[11])
            cur = best.get(name)
            if cur is None or mapq > cur[2]:
                best[name] = (chrom, start, mapq)
    return {n: (c, s) for n, (c, s, _) in best.items()}


def consensus_locus(placements: list, tol: int, min_agree: int):
    """placements: list of (family, chr, start). Return (chr, rep_start) for the
    locus agreed by the most DISTINCT families (>= min_agree), else None.
    Counting distinct families prevents variants of one algorithm from
    validating each other."""
    best = None  # (n_families, chrom, rep_start)
    for fi, ci, si in placements:
        grp = [(fj, sj) for (fj, cj, sj) in placements if cj == ci and abs(sj - si) <= tol]
        nfam = len({fj for fj, _ in grp})
        if nfam >= min_agree and (best is None or nfam > best[0]):
            best = (nfam, ci, int(statistics.median(s for _, s in grp)))
    return None if best is None else (best[1], best[2])


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: 12_eval_consensus.py <genome> [tag=errreal_len100k] [tol=1000] [min_agree=2]")
    genome    = sys.argv[1]
    TAG       = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_TAG
    tol       = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    min_agree = int(sys.argv[4]) if len(sys.argv) > 4 else 2

    # Load each tool's best placements
    tool_best = {m: best_per_read(os.path.join(MAPPINGS_DIR, f"{genome}_{m}_{TAG}.paf"))
                 for m in MAPPERS}

    # Universe of reads = every read any tool emitted
    all_reads = set()
    for m in MAPPERS:
        all_reads.update(tool_best[m])
    total_reads = len(all_reads)

    # Build consensus truth
    truth = {}
    for r in all_reads:
        placements = [(FAMILY[m], tool_best[m][r][0], tool_best[m][r][1])
                      for m in MAPPERS if r in tool_best[m]]
        loc = consensus_locus(placements, tol, min_agree)
        if loc is not None:
            truth[r] = loc
    n_consensus = len(truth)

    print(f"[{genome}] reads emitted by >=1 tool: {total_reads:,}")
    print(f"[{genome}] reads with consensus truth (>= {min_agree} agree, tol {tol}): {n_consensus:,}")

    # Score each tool against the consensus
    for m in MAPPERS:
        bm = tool_best[m]
        mapped_in_consensus = correct = 0
        for r, (tc, ts) in truth.items():
            if r not in bm:
                continue
            mapped_in_consensus += 1
            c, s = bm[r]
            if c == tc and abs(s - ts) <= tol:
                correct += 1

        accuracy  = round(100.0 * correct / n_consensus, 4) if n_consensus else 0.0
        precision = round(100.0 * correct / mapped_in_consensus, 4) if mapped_in_consensus else 0.0
        map_rate  = round(100.0 * len(bm) / total_reads, 4) if total_reads else 0.0

        out = {
            "total_reads":           total_reads,
            "consensus_reads":       n_consensus,
            "mapped":                len(bm),
            "mapped_in_consensus":   mapped_in_consensus,
            "correct":               correct,
            "accuracy":              accuracy,    # correct / consensus_reads
            "precision":             precision,   # correct / mapped_in_consensus
            "mapping_rate":          map_rate,    # mapped / all emitted reads
        }
        out_path = os.path.join(MAPPINGS_DIR, f"{genome}_{m}_{TAG}_eval.json")
        with open(out_path, "w") as f:
            json.dump(out, f, indent=2)
        print(f"  {m:<13} acc={accuracy:6.2f}%  prec={precision:6.2f}%  maprate={map_rate:6.2f}%")


if __name__ == "__main__":
    main()
