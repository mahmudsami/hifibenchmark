#!/usr/bin/env bash
# Build the five mapper images on linux/amd64. Run once before the benchmark.
#
# Usage: bash docker/build_images.sh
#
# minimap2 / blend / mapquik / strobealign clone their tool from public GitHub at
# a pinned commit (build context = docker/). syncmer-hifi is a private/unpublished
# method, so its image is built from a LOCAL source checkout:
#
#   SYNCMER_HIFI_SRC=/path/to/syncmer-hifi bash docker/build_images.sh
#
# Defaults to $HOME/syncmer-hifi. If that source isn't present, the other four
# images still build and the script just warns about the syncmer image.

set -euo pipefail
BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYNCMER_HIFI_SRC="${SYNCMER_HIFI_SRC:-$HOME/syncmer-hifi}"

build() {
    local tag="$1" dockerfile="$2" context="$3"
    echo ""
    echo "=== Building $tag (linux/amd64) ==="
    docker build --platform linux/amd64 -t "$tag" -f "$dockerfile" "$context"
}

# Public mappers: clone from GitHub at a pinned commit (context = docker/).
build hifi-minimap2:latest    "$BENCH_DIR/docker/Dockerfile.minimap2"    "$BENCH_DIR/docker"
build hifi-blend:latest       "$BENCH_DIR/docker/Dockerfile.blend"       "$BENCH_DIR/docker"
build hifi-mapquik:latest     "$BENCH_DIR/docker/Dockerfile.mapquik"     "$BENCH_DIR/docker"
build hifi-strobealign:latest "$BENCH_DIR/docker/Dockerfile.strobealign" "$BENCH_DIR/docker"

# Private method: build from a local source checkout.
if [ -f "$SYNCMER_HIFI_SRC/Cargo.toml" ]; then
    build hifi-syncmer-hifi:latest "$BENCH_DIR/docker/Dockerfile.syncmer_hifi" "$SYNCMER_HIFI_SRC"
else
    echo ""
    echo "WARNING: syncmer-hifi source not found at '$SYNCMER_HIFI_SRC'."
    echo "         Set SYNCMER_HIFI_SRC=/path/to/syncmer-hifi to build that image."
    echo "         (The other four mapper images were built.)"
fi

echo ""
echo "Done. Images built:"
docker images | grep -E "hifi-minimap2|hifi-blend|hifi-mapquik|hifi-syncmer-hifi|hifi-strobealign"
