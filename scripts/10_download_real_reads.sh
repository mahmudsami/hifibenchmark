#!/usr/bin/env bash
# Download a subsample of REAL PacBio HiFi reads for one genome.
# Streams the public FASTQ and keeps the first N reads (cheap — only the needed
# prefix is transferred, the rest of the stream is dropped).
#
#   Human      : HG002 PacBio Revio HiFi (HPRC, SRR34290932) — CCS reads, ~16.5 kb
#   Maize      : Mo17 HiFi (SRR15447414) — matches the Mo17 T2T reference
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
    # HG002 Revio HiFi reads (CCS, ~16.5 kb), study PRJNA1283554 "HG002 HiFi
    # sequencing for HPRC", public 2025-07-06. The "_subreads" in the ENA path is
    # ENA's default filename — the content is genuine HiFi (16.5 kb mean length).
    human_hifi)       URL="https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR342/032/SRR34290932/SRR34290932_subreads.fastq.gz" ;;
    # Mo17 HiFi (CCS) reads, study "Zea mays Mo17 Genome sequencing and assembly"
    # — the same inbred line as the Mo17 T2T reference (Zm-Mo17-REFERENCE-CAU-2.0),
    # so reads and reference match. (The previous B73 reads were mapped against the
    # Mo17 reference — two highly divergent inbred lines — which unfairly depressed
    # maize mapping rates.) "_subreads" is ENA's default filename; content is HiFi.
    maize_hifi)       URL="https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR154/014/SRR15447414/SRR15447414_subreads.fastq.gz" ;;
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
