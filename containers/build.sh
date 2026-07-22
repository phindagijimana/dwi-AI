#!/usr/bin/env bash
# Build dwi-ai-analysis.sif on clusters where /tmp is noexec (common on HPC).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_TMP="${BUILD_TMP:-$REPO_ROOT/containers/.build-tmp}"
VERSION="${NODESTRENGTH_VERSION:-0.1.0}"
OUT_SIF="${1:-$REPO_ROOT/containers/nodestrength_${VERSION}.sif}"
LEGACY_SIF="$REPO_ROOT/containers/dwi-ai-analysis.sif"

mkdir -p "$BUILD_TMP"
export APPTAINER_TMPDIR="$BUILD_TMP"
export TMPDIR="$BUILD_TMP"
export PROOT_TMP_DIR="$BUILD_TMP"

cd "$REPO_ROOT"
apptainer build --force "$OUT_SIF" containers/dwi-ai-analysis-build.def
ln -sf "$(basename "$OUT_SIF")" "$LEGACY_SIF"
echo "Built: $OUT_SIF ($(du -h "$OUT_SIF" | cut -f1))"
echo "Symlink: $LEGACY_SIF -> $(basename "$OUT_SIF")"
