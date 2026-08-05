#!/usr/bin/env bash
# Build the nodestrength Apptainer image (one SIF; legacy name is a symlink only).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_TMP="${BUILD_TMP:-$REPO_ROOT/containers/.build-tmp}"
VERSION="${NODESTRENGTH_VERSION:-0.1.0}"
OUT_SIF="${1:-$REPO_ROOT/containers/nodestrength_${VERSION}.sif}"
LEGACY_SIF="$REPO_ROOT/containers/dwi-ai-analysis.sif"
CANONICAL_BASE="$(basename "$OUT_SIF")"

mkdir -p "$BUILD_TMP"
export APPTAINER_TMPDIR="$BUILD_TMP"
export TMPDIR="$BUILD_TMP"
export PROOT_TMP_DIR="$BUILD_TMP"

cd "$REPO_ROOT"
apptainer build --force "$OUT_SIF" containers/nodestrength-build.def

# Legacy alias must never be a second copy of the image on disk.
if [[ -e "$LEGACY_SIF" && ! -L "$LEGACY_SIF" ]]; then
  echo "Removing duplicate legacy file (keeping one image): $LEGACY_SIF" >&2
  rm -f "$LEGACY_SIF"
fi
ln -sf "$CANONICAL_BASE" "$LEGACY_SIF"

bash containers/verify-image.sh "$OUT_SIF"
echo "Built: $OUT_SIF ($(du -h "$OUT_SIF" | cut -f1))"
echo "Legacy symlink: $LEGACY_SIF -> $CANONICAL_BASE (same container)"
