#!/usr/bin/env bash
# Build dwi-ai-analysis.sif on clusters where /tmp is noexec (common on HPC).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_TMP="${BUILD_TMP:-$REPO_ROOT/containers/.build-tmp}"
OUT_SIF="${1:-$REPO_ROOT/containers/dwi-ai-analysis.sif}"

mkdir -p "$BUILD_TMP"
export APPTAINER_TMPDIR="$BUILD_TMP"
export TMPDIR="$BUILD_TMP"
export PROOT_TMP_DIR="$BUILD_TMP"

cd "$REPO_ROOT"
apptainer build --force "$OUT_SIF" containers/dwi-ai-analysis-build.def
echo "Built: $OUT_SIF ($(du -h "$OUT_SIF" | cut -f1))"
