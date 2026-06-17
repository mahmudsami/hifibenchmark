#!/usr/bin/env python3
"""
Streaming, faidx-based HiFi read simulator for VERY LARGE genomes.

The default simulator (02_simulate_reads.py) loads the whole reference into RAM,
which is impossible for genomes like the lungfishes (Australian ~35 Gb, African
~40 Gb, South American ~87 Gb). This version instead builds a FASTA index (.fai)
and samples each read by SEEKING to a random position in the file, so peak memory
is O(read length) — independent of genome size.

Output is byte-for-byte the same shape as 02_simulate_reads.py (read names `r{i}`,
FASTQ, and a truth TSV `read_name\tchr\tstart\tend`), so 05_evaluate_mapping.py
and the rest of the pipeline work unchanged.

Usage:
    simulate_reads_faidx.py <genome> <error_rate> <read_length> [n_reads]
      genome      : folder under data/references/  (e.g. lungfish_au)
      error_rate  : fraction, e.g. 0.005 = 0.5 %
      read_length : mean read length in bp, e.g. 20000
      n_reads     : fixed read count (else depth-based)

Requires an UNCOMPRESSED reference at data/references/<genome>/genome.fa
(plain gzip is not seekable). For a gzipped download, decompress once:
    gzip -dc genome.fa.gz > genome.fa
A samtools-compatible <genome>.fa.fai is written next to it on first run.
"""
import sys, os, gzip, random, hashlib

# ── Tunable constants (kept identical to 02_simulate_reads.py) ────────────────
MIN_CONTIG  = 50_000
LEN_SD_FRAC = 0.05
DEPTH       = 0.05
MAX_N_FRAC  = 0.10
SUB_INS_DEL = (2, 1, 1)
QUAL_CHAR   = "I"

BENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS_DIR  = os.path.join(BENCH_DIR, "data", "references")
READS_DIR = os.path.join(BENCH_DIR, "data", "reads")
TRUTH_DIR = os.path.join(BENCH_DIR, "data", "truth")

BASES = "ACGT"
_COMP = str.maketrans("ACGTNacgtn", "TGCANtgcan")


def revcomp(seq: str) -> str:
    return seq.translate(_COMP)[::-1]


def inject_errors(seq: str, n_err: int, rng: random.Random) -> str:
    """Apply exactly n_err substitution/insertion/deletion events (sub:ins:del = 2:1:1)."""
    if n_err <= 0:
        return seq
    L = len(seq)
    err_pos = set(rng.sample(range(L), min(n_err, L)))
    sub_w, ins_w, del_w = SUB_INS_DEL
    total_w = sub_w + ins_w + del_w
    out = []
    for i, b in enumerate(seq):
        if i not in err_pos:
            out.append(b)
            continue
        r = rng.randrange(total_w)
        if r < sub_w:
            choices = [x for x in BASES if x != b]
            out.append(rng.choice(choices) if choices else b)
        elif r < sub_w + ins_w:
            out.append(b)
            out.append(rng.choice(BASES))
        # else deletion → emit nothing
    return "".join(out)


def build_faidx(fa_path: str) -> list:
    """Return [(name, length, offset, linebases, linewidth), ...], building a .fai
    next to the FASTA if absent. Mirrors `samtools faidx` (one byte-accurate pass;
    intermediate sequence lines of a contig must share one width — standard FASTA)."""
    fai_path = fa_path + ".fai"
    if os.path.exists(fai_path) and os.path.getmtime(fai_path) >= os.path.getmtime(fa_path):
        recs = []
        with open(fai_path) as f:
            for line in f:
                n, ln, off, lb, lw = line.rstrip("\n").split("\t")
                recs.append((n, int(ln), int(off), int(lb), int(lw)))
        return recs

    print(f"Building FASTA index → {fai_path} (one streaming pass) ...", flush=True)
    recs = []
    name = None
    length = seq_off = linebases = linewidth = 0
    first_seq = False
    short_seen = False
    with open(fa_path, "rb") as f:
        offset = 0
        for line in f:
            if line[:1] == b">":
                if name is not None:
                    recs.append((name, length, seq_off, linebases, linewidth))
                name = line[1:].split()[0].decode()
                offset += len(line)
                seq_off = offset
                length = linebases = linewidth = 0
                first_seq = True
                short_seen = False
            else:
                lw = len(line)
                lb = len(line.rstrip(b"\r\n"))
                if first_seq:
                    linebases, linewidth = lb, lw
                    first_seq = False
                elif lb != linebases:
                    # only the final line of a contig may be shorter
                    if short_seen or lb > linebases:
                        sys.exit(f"ERROR: inconsistent line length in {name} near byte {offset} "
                                 f"(faidx needs uniform line widths). Re-wrap the FASTA.")
                    short_seen = True
                length += lb
                offset += lw
    if name is not None:
        recs.append((name, length, seq_off, linebases, linewidth))

    with open(fai_path, "w") as out:
        for r in recs:
            out.write("\t".join(map(str, r)) + "\n")
    return recs


def fetch(f, rec, start: int, want: int) -> str:
    """Random-access bases [start, start+want) from an open FASTA handle via seek."""
    _, clen, offset, linebases, linewidth = rec
    nbases = min(want, clen - start)
    start_byte = offset + (start // linebases) * linewidth + (start % linebases)
    f.seek(start_byte)
    # read enough bytes to cover nbases plus the newlines interleaved within them
    nbytes = nbases + (nbases // linebases) + 16
    raw = f.read(nbytes).replace(b"\n", b"").replace(b"\r", b"")
    return raw[:nbases].decode("ascii", "replace").upper()


def find_reference(genome: str) -> str:
    base = os.path.join(REFS_DIR, genome)
    for name in ("genome_clean.fa", "genome.fa"):
        path = os.path.join(base, name)
        if os.path.exists(path):
            return path
    if os.path.exists(os.path.join(base, "genome.fa.gz")):
        sys.exit(f"ERROR: only a gzipped reference in {base}. This simulator needs an "
                 f"uncompressed, seekable FASTA. Run:\n    gzip -dc {base}/genome.fa.gz > {base}/genome.fa")
    sys.exit(f"ERROR: no reference found in {base} (looked for genome_clean.fa, genome.fa)")


def main():
    if len(sys.argv) not in (4, 5):
        sys.exit("Usage: simulate_reads_faidx.py <genome> <error_rate> <read_length> [n_reads]")

    genome = sys.argv[1]
    err    = float(sys.argv[2])
    mean   = int(sys.argv[3])
    n_reads_arg = int(sys.argv[4]) if len(sys.argv) > 4 else None
    tag    = f"err{sys.argv[2]}_len{sys.argv[3]}"

    fastq_path = os.path.join(READS_DIR, genome, f"{tag}.fastq.gz")
    truth_path = os.path.join(TRUTH_DIR, genome, f"{tag}.tsv")
    if os.path.exists(fastq_path) and os.path.exists(truth_path):
        print(f"Reads + truth already exist for {tag} — skipping.")
        return
    os.makedirs(os.path.join(READS_DIR, genome), exist_ok=True)
    os.makedirs(os.path.join(TRUTH_DIR, genome), exist_ok=True)

    ref_path = find_reference(genome)
    print(f"Reference: {ref_path}")
    recs = [r for r in build_faidx(ref_path) if r[1] >= MIN_CONTIG]
    if not recs:
        sys.exit(f"ERROR: no contigs >= {MIN_CONTIG} bp in {ref_path}")

    names   = [r[0] for r in recs]
    lengths = [r[1] for r in recs]
    by_name = {r[0]: r for r in recs}
    genome_len = sum(lengths)

    n_reads = n_reads_arg if n_reads_arg else max(1, int(DEPTH * genome_len / mean))
    len_sd  = max(1, int(mean * LEN_SD_FRAC))
    # deterministic seed (Python's hash() is per-process randomized → don't use it),
    # so regenerating the same (genome, err, len) always yields the SAME reads.
    seed = int.from_bytes(hashlib.sha1(f"{genome}|{err}|{mean}".encode()).digest()[:8], "big")
    rng = random.Random(seed)
    print(f"Genome={genome}  contigs={len(names)}  size={genome_len:,} bp")
    print(f"Simulating {n_reads:,} reads  mean_len={mean}  sd={len_sd}  error={err*100:.2f}%  (faidx/streaming)")

    written = 0
    with open(ref_path, "rb") as ref, \
         gzip.open(fastq_path, "wt", compresslevel=1) as fq, \
         open(truth_path, "w") as tr:
        tr.write("read_name\tchr\tstart\tend\n")
        idx = 0
        while written < n_reads:
            chrom = rng.choices(names, weights=lengths, k=1)[0]
            rec   = by_name[chrom]
            clen  = rec[1]

            L = int(rng.gauss(mean, len_sd))
            L = max(mean // 2, min(L, mean * 2, clen))
            if L < 100:
                continue

            start = rng.randint(0, clen - L)
            sub   = fetch(ref, rec, start, L)
            if len(sub) < L or sub.count("N") > MAX_N_FRAC * L:
                continue

            n_err = round(L * err)
            read  = inject_errors(sub, n_err, rng)
            if rng.random() < 0.5:
                read = revcomp(read)

            name = f"r{idx}"
            fq.write(f"@{name}\n{read}\n+\n{QUAL_CHAR * len(read)}\n")
            tr.write(f"{name}\t{chrom}\t{start}\t{start + L}\n")
            idx += 1
            written += 1
            if written % 10000 == 0:
                print(f"  {written:,}/{n_reads:,}", flush=True)

    print(f"Wrote {written:,} reads → {fastq_path}")
    print(f"Wrote {written:,} truth rows → {truth_path}")


if __name__ == "__main__":
    main()
