#!/usr/bin/env python3
"""
Evaluate a single PAF mapping against a truth TSV, write a JSON metrics file.

Usage:
    python3 05_evaluate_mapping.py <truth.tsv> <mapped.paf> <out.json> [tolerance=1000]

truth.tsv format  : read_name  chr  start  end   (tab-separated, header optional)
PAF format        : standard minimap2/synpact PAF
tolerance         : a mapping is "correct" if mapped_start ∈ [true_start-tol, true_end+tol]
"""
import sys, os, json, gzip


def load_truth(tsv_path: str) -> dict:
    """Return dict: read_name → (chr, start, end)."""
    truth = {}
    opener = gzip.open if tsv_path.endswith(".gz") else open
    with opener(tsv_path, "rt") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("read_name"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            truth[parts[0]] = (parts[1], int(parts[2]), int(parts[3]))
    return truth


def best_mappings(paf_path: str, truth: dict) -> dict:
    """Return dict: read_name → (target, rstart, mapq) | None (unmapped)."""
    best = {}
    opener = gzip.open if paf_path.endswith(".gz") else open
    with opener(paf_path, "rt") as f:
        for line in f:
            if not line.strip():
                continue
            parts = line.split("\t")
            rname = parts[0]

            # Normalize name: strip /1 /2 suffixes used by some simulators
            if rname not in truth:
                base = rname.rstrip("/12").rstrip("/")
                rname = base if base in truth else rname

            if rname not in truth:
                continue

            # Unmapped record (< 12 fields or target == *)
            if len(parts) < 12 or parts[5] == "*":
                best.setdefault(rname, None)
                continue

            target = parts[5]
            rstart = int(parts[7])
            mapq   = int(parts[11])

            cur = best.get(rname)
            if cur is None or mapq > cur[2]:
                best[rname] = (target, rstart, mapq)

    return best


def compute_metrics(best: dict, truth: dict, tol: int) -> dict:
    mapped = unmapped = correct = wrong_chr = wrong_pos = 0

    for rname, entry in best.items():
        if rname not in truth:
            continue
        true_chr, true_start, true_end = truth[rname]
        if entry is None:
            unmapped += 1
            continue
        mapped += 1
        target, rstart, _ = entry
        if target != true_chr:
            wrong_chr += 1
        elif true_start - tol <= rstart <= true_end + tol:
            correct += 1
        else:
            wrong_pos += 1

    # Reads in truth not seen at all in PAF → unmapped
    for rname in truth:
        if rname not in best:
            unmapped += 1

    total = mapped + unmapped
    return {
        "total_reads":   total,
        "mapped":        mapped,
        "unmapped":      unmapped,
        "correct":       correct,
        "wrong_chr":     wrong_chr,
        "wrong_pos":     wrong_pos,
        "accuracy":      round(100.0 * correct / total,  4) if total  > 0 else 0.0,
        "precision":     round(100.0 * correct / mapped, 4) if mapped > 0 else 0.0,
        "mapping_rate":  round(100.0 * mapped  / total,  4) if total  > 0 else 0.0,
    }


def main():
    if len(sys.argv) < 4:
        sys.exit("Usage: 05_evaluate_mapping.py <truth.tsv> <mapped.paf> <out.json> [tolerance=1000]")

    truth_path = sys.argv[1]
    paf_path   = sys.argv[2]
    out_path   = sys.argv[3]
    tol        = int(sys.argv[4]) if len(sys.argv) > 4 else 1000

    truth   = load_truth(truth_path)
    best    = best_mappings(paf_path, truth)
    metrics = compute_metrics(best, truth, tol)

    with open(out_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"  accuracy     : {metrics['accuracy']:.2f}%")
    print(f"  precision    : {metrics['precision']:.2f}%")
    print(f"  mapping rate : {metrics['mapping_rate']:.2f}%")
    print(f"  → {out_path}")


if __name__ == "__main__":
    main()
