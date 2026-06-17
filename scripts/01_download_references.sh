#!/usr/bin/env bash
# Download reference genomes.
#   Human       : T2T-CHM13v2.0 (gapless; NCBI GCF_009914755.1)
#   Maize       : Mo17 T2T (gapless; Zm-Mo17-REFERENCE-CAU-2.0, MaizeGDB)
#   Arabidopsis : Col-CEN v1.2 (gapless Col-0 T2T; schatzlab/Col-CEN)
#   Rye         : Lo7_V3 near-complete (GCA_965641915.1; contig N50 128 Mb)
#
# Skips download if the FASTA already exists.

set -euo pipefail
source "$(dirname "$0")/../config.sh"

HUMAN_URL="https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/009/914/755/GCF_009914755.1_T2T-CHM13v2.0/GCF_009914755.1_T2T-CHM13v2.0_genomic.fna.gz"
MAIZE_URL="https://download.maizegdb.org/Zm-Mo17-REFERENCE-CAU-2.0/Zm-Mo17-REFERENCE-CAU-2.0.fa.gz"
ARABIDOPSIS_URL="https://raw.githubusercontent.com/schatzlab/Col-CEN/main/v1.2/Col-CEN_v1.2.fasta.gz"
RYE_URL="https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/965/641/915/GCA_965641915.1_lpSecCere.Lo7.IPK.v3/GCA_965641915.1_lpSecCere.Lo7.IPK.v3_genomic.fna.gz"

download_if_missing() {
    local url="$1"
    local dest="$2"
    if [ -f "$dest" ]; then
        echo "Already exists: $dest"
        return
    fi
    mkdir -p "$(dirname "$dest")"
    echo "Downloading $(basename "$dest") ..."
    curl -L --retry 3 --progress-bar -o "$dest" "$url"
    echo "Saved: $dest"
}

download_if_missing "$HUMAN_URL" "$REFS_DIR/human/genome.fa.gz"
download_if_missing "$MAIZE_URL" "$REFS_DIR/maize/genome.fa.gz"
download_if_missing "$ARABIDOPSIS_URL" "$REFS_DIR/arabidopsis/genome.fa.gz"
download_if_missing "$RYE_URL" "$REFS_DIR/rye/genome.fa.gz"

# human_y: the T2T-CHM13v2.0 Y chromosome (NC_060948.1) extracted from the human
# reference — a small, highly repetitive (ampliconic/satellite) stress test.
HUMAN_Y="$REFS_DIR/human_y/genome.fa.gz"
if [ -f "$HUMAN_Y" ]; then
    echo "Already exists: $HUMAN_Y"
else
    echo "Extracting chrY (NC_060948.1) → $HUMAN_Y ..."
    mkdir -p "$REFS_DIR/human_y"
    # NC_060948.1 is the last record in CHM13v2.0, so print from its header to EOF
    gzip -dc "$REFS_DIR/human/genome.fa.gz" \
        | awk '/^>NC_060948.1/{p=1} p' | gzip -1 > "$HUMAN_Y"
    echo "Saved: $HUMAN_Y"
fi

echo "References ready."
