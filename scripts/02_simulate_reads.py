#!/usr/bin/env python3
"""
Custom exact-error HiFi read simulator.

Draws reads from a reference genome and injects substitutions + insertions +
deletions at an EXACT target error rate. Because the simulator chooses every
read's origin, it writes the ground-truth TSV directly — no alignment/MAF
parsing needed.

Usage:
    python3 02_simulate_reads.py <genome> <error_rate> <read_length>
      genome      : human | maize  (folder under data/references/)
      error_rate  : fraction, e.g. 0.001 = 0.1 %
      read_length : mean read length in bp, e.g. 15000

Outputs:
    data/reads/<genome>/err<error_rate>_len<read_length>.fastq
    data/truth/<genome>/err<error_rate>_len<read_length>.tsv
        (read_name  chr  start  end   — 0-based, end exclusive)

Reads the reference from the first of these that exists:
    genome_clean.fa, genome.fa, genome.fa.gz
"""
import sys, os, gzip, random

# ── Tunable constants ─────────────────────────────────────────────────────────
MIN_CONTIG     = 50_000      # ignore contigs shorter than this
LEN_SD_FRAC    = 0.05        # read-length stddev as a fraction of the mean
DEPTH          = 0.05        # genome fraction sampled (n_reads ≈ DEPTH·G/len)
MAX_N_FRAC     = 0.10        # resample a read if it has more N than this
SUB_INS_DEL    = (2, 1, 1)   # relative frequency of substitution:insertion:deletion
QUAL_CHAR      = "I"         # FASTQ quality (Phred ~40)

BENCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS_DIR  = os.path.join(BENCH_DIR, "data", "references")
READS_DIR = os.path.join(BENCH_DIR, "data", "reads")
TRUTH_DIR = os.path.join(BENCH_DIR, "data", "truth")

BASES = "ACGT"
_COMP = str.maketrans("ACGTNacgtn", "TGCANtgcan")


def find_reference(genome: str) -> str:
    base = os.path.join(REFS_DIR, genome)
    for name in ("genome_clean.fa", "genome.fa", "genome.fa.gz"):
        path = os.path.join(base, name)
        if os.path.exists(path):
            return path
    sys.exit(f"ERROR: no reference found in {base} (looked for genome_clean.fa, genome.fa, genome.fa.gz)")


def load_genome(path: str) -> list:
    """Return list of (chrom_name, uppercase_sequence) for contigs ≥ MIN_CONTIG."""
    opener = gzip.open if path.endswith(".gz") else open
    contigs = []
    name = None
    chunks = []

    def flush():
        if name is not None:
            seq = "".join(chunks).upper()
            if len(seq) >= MIN_CONTIG:
                contigs.append((name, seq))

    with opener(path, "rt") as f:
        for line in f:
            if line.startswith(">"):
                flush()
                name = line[1:].split()[0]   # first token after '>'
                chunks = []
            else:
                chunks.append(line.strip())
    flush()

    if not contigs:
        sys.exit(f"ERROR: no contigs ≥ {MIN_CONTIG} bp in {path}")
    return contigs


def revcomp(seq: str) -> str:
    return seq.translate(_COMP)[::-1]


def inject_errors(seq: str, n_err: int, rng: random.Random) -> str:
    """Apply exactly n_err substitution/insertion/deletion events at distinct positions."""
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
        if r < sub_w:                       # substitution → a different base
            choices = [x for x in BASES if x != b]
            out.append(rng.choice(choices) if choices else b)
        elif r < sub_w + ins_w:             # insertion → keep base, add one
            out.append(b)
            out.append(rng.choice(BASES))
        else:                               # deletion → emit nothing
            pass
    return "".join(out)


def main():
    if len(sys.argv) not in (4, 5):
        sys.exit("Usage: 02_simulate_reads.py <genome> <error_rate> <read_length> [n_reads]")

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
    print(f"Loading reference: {ref_path}")
    contigs = load_genome(ref_path)

    names   = [c[0] for c in contigs]
    seqs    = {c[0]: c[1] for c in contigs}
    lengths = [len(c[1]) for c in contigs]
    genome_len = sum(lengths)

    # Fixed read count if given (4th arg), else fall back to depth-based.
    n_reads = n_reads_arg if n_reads_arg else max(1, int(DEPTH * genome_len / mean))
    len_sd  = max(1, int(mean * LEN_SD_FRAC))

    rng = random.Random(hash((genome, err, mean)) & 0xFFFFFFFF)
    print(f"Genome={genome}  contigs={len(names)}  size={genome_len:,} bp")
    print(f"Simulating {n_reads:,} reads  mean_len={mean}  sd={len_sd}  error={err*100:.2f}%")

    written = 0
    with gzip.open(fastq_path, "wt", compresslevel=1) as fq, open(truth_path, "w") as tr:
        tr.write("read_name\tchr\tstart\tend\n")
        idx = 0
        while written < n_reads:
            chrom = rng.choices(names, weights=lengths, k=1)[0]
            cseq  = seqs[chrom]
            clen  = len(cseq)

            L = int(rng.gauss(mean, len_sd))
            L = max(mean // 2, min(L, mean * 2, clen))
            if L < 100:
                continue

            start = rng.randint(0, clen - L)
            sub   = cseq[start:start + L]

            if sub.count("N") > MAX_N_FRAC * L:
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

    print(f"Wrote {written:,} reads → {fastq_path}")
    print(f"Wrote {written:,} truth rows → {truth_path}")


if __name__ == "__main__":
    main()
