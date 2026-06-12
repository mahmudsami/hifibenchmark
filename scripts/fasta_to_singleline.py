#!/usr/bin/env python3
"""
Stream a FASTA from stdin to stdout, rewriting each record onto a single line
with its sequence uppercased (headers keep their original case). This is the
format mapquik requires (multi-line / lowercase inputs make it map ~1%).

Used by 04_index_mapquik.sh. Pure byte I/O with bytes.upper() — ~7x faster than
the equivalent macOS awk one-liner, which dominates large-genome prep time.

    gzip -dc genome.fa.gz | fasta_to_singleline.py | gzip -1 > genome.mapquik.fa.gz
"""
import sys


def main() -> None:
    out = sys.stdout.buffer
    first = True
    for line in sys.stdin.buffer:
        if line[:1] == b">":
            if not first:
                out.write(b"\n")        # terminate the previous record's line
            out.write(line)             # header: original case + its own newline
            first = False
        else:
            out.write(line.rstrip(b"\n").upper())
    if not first:
        out.write(b"\n")


if __name__ == "__main__":
    main()
