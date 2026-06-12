#!/usr/bin/env bash
# Download a subsample of REAL PacBio HiFi reads for one genome.
# Streams the public FASTQ and keeps the first N reads (cheap — only the needed
# prefix is transferred, the rest of the stream is dropped).
#
#   Human      : HG002 (GIAB) DeepConsensus HiFi, q20  — m64179e .../ccs reads
#   Maize      : B73 (Kim et al. 2020, SRR11606869)    — Sequel II HiFi reads
#   Arabidopsis: Col-0 HiFi (ERR13987671)
#   Rye (hifi) : Lo7 HiFi (ERR15194059)
#   Rye (dc)   : Lo7 DeepConsensus reads (set READSET=dc)
#
# Usage: 10_download_real_reads.sh <genome> [READSET]
#   READSET: "hifi" (default) or "dc" (DeepConsensus; only supported for rye)
#
# Output:
#   READSET=hifi : data/reads/<genome>/errreal_len100k.fastq
#   READSET=dc   : data/reads/<genome>/errdc_len100k.fastq

set -u
source "$(dirname "$0")/../config.sh"

GENOME="$1"
READSET="${2:-hifi}"
N_READS=100000

if [ "$READSET" = "dc" ]; then
    TAG="errdc_len100k"
else
    TAG="errreal_len100k"
fi
OUT="$READS_DIR/$GENOME/${TAG}.fastq"

case "${GENOME}_${READSET}" in
    human_hifi)       URL="https://storage.googleapis.com/brain-genomics-public/research/deepconsensus/data/v0.3/assembly_analysis/fastqs/HG002_24kb_2SMRT_cells.dc.v0.3.q20.fastq.gz" ;;
    maize_hifi)       URL="https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR116/069/SRR11606869/SRR11606869_subreads.fastq.gz" ;;
    arabidopsis_hifi) URL="https://ftp.sra.ebi.ac.uk/vol1/fastq/ERR139/071/ERR13987671/ERR13987671.fastq.gz" ;;
    rye_hifi)         URL="https://ftp.sra.ebi.ac.uk/vol1/fastq/ERR151/059/ERR15194059/ERR15194059.fastq.gz" ;;
    # Rye Lo7 PacBio Revio (DeepConsensus) reads — ERR15194060, BioProject PRJEB91463
    # "Unveiling centromeric retrotransposon dynamics through a near-complete rye genome assembly"
    # IPK Gatersleben, published 2025-07-04
    rye_dc)           URL="https://ftp.sra.ebi.ac.uk/vol1/fastq/ERR151/060/ERR15194060/ERR15194060.fastq.gz" ;;
    *) echo "ERROR: unknown genome/readset combination '${GENOME}/${READSET}'" >&2; exit 1 ;;
esac

if [ -f "$OUT" ]; then
    echo "Real reads already exist: $OUT — skipping."
    exit 0
fi

mkdir -p "$READS_DIR/$GENOME"
echo "Downloading $N_READS real HiFi reads for $GENOME ..."
echo "  source: $URL"

# Stream → gunzip → keep first N reads. head closing the pipe stops the transfer.
curl -s "$URL" | zcat 2>/dev/null | head -n $((N_READS * 4)) > "$OUT" || true

GOT=$(( $(wc -l < "$OUT") / 4 ))
if [ "$GOT" -lt 1000 ]; then
    echo "ERROR: only got $GOT reads — download failed." >&2
    rm -f "$OUT"
    exit 1
fi
echo "Saved $GOT reads → $OUT"
