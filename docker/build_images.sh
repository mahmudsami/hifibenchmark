#!/usr/bin/env bash
# Build Docker images for all four mappers on linux/amd64.
# Run this once before starting the benchmark.
#
# Usage: bash docker/build_images.sh

set -euo pipefail
BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

build() {
    local tag="$1" dockerfile="$2" context="$3"
    echo ""
    echo "=== Building $tag (linux/amd64) ==="
    docker build --platform linux/amd64 -t "$tag" -f "$dockerfile" "$context"
}

# All Dockerfiles clone their tool from GitHub at a pinned commit, so the build
# context is just docker/ for every image (no local source dirs needed).
build hifi-minimap2:latest     "$BENCH_DIR/docker/Dockerfile.minimap2"     "$BENCH_DIR/docker"
build hifi-blend:latest        "$BENCH_DIR/docker/Dockerfile.blend"        "$BENCH_DIR/docker"
build hifi-mapquik:latest      "$BENCH_DIR/docker/Dockerfile.mapquik"      "$BENCH_DIR/docker"
build hifi-syncmer-hifi:latest "$BENCH_DIR/docker/Dockerfile.syncmer_hifi" "$BENCH_DIR/docker"
build hifi-strobealign:latest  "$BENCH_DIR/docker/Dockerfile.strobealign"  "$BENCH_DIR/docker"

echo ""
echo "Done. Images built:"
docker images | grep -E "hifi-minimap2|hifi-blend|hifi-mapquik|hifi-syncmer-hifi|hifi-strobealign"
