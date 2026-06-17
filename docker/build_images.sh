#!/usr/bin/env bash
# Build the four mapper images on linux/amd64. Run once before the benchmark.
#
# Usage: bash docker/build_images.sh
#
# All four mappers (minimap2 / blend / mapquik / synpact) clone their tool from
# public GitHub at a pinned commit (build context = docker/).

set -euo pipefail
BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

build() {
    local tag="$1" dockerfile="$2" context="$3"
    echo ""
    echo "=== Building $tag (linux/amd64) ==="
    docker build --platform linux/amd64 -t "$tag" -f "$dockerfile" "$context"
}

# All mappers: clone from public GitHub at a pinned commit (context = docker/).
build hifi-minimap2:latest "$BENCH_DIR/docker/Dockerfile.minimap2" "$BENCH_DIR/docker"
build hifi-blend:latest    "$BENCH_DIR/docker/Dockerfile.blend"    "$BENCH_DIR/docker"
build hifi-mapquik:latest  "$BENCH_DIR/docker/Dockerfile.mapquik"  "$BENCH_DIR/docker"
build hifi-synpact:latest  "$BENCH_DIR/docker/Dockerfile.synpact"  "$BENCH_DIR/docker"

echo ""
echo "Done. Images built:"
docker images | grep -E "hifi-minimap2|hifi-blend|hifi-mapquik|hifi-synpact"
