#!/usr/bin/env bash
# Verify nodestrength ships as ONE Apptainer image with an optional legacy symlink.
#
# Canonical:  containers/nodestrength_<version>.sif  (real file)
# Legacy:     containers/dwi-ai-analysis.sif         (symlink only — never a second copy)
#
# Usage: bash containers/verify-image.sh [path/to/nodestrength_0.1.0.sif]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${NODESTRENGTH_VERSION:-0.1.0}"
CANONICAL="${1:-$REPO_ROOT/containers/nodestrength_${VERSION}.sif}"
LEGACY="$REPO_ROOT/containers/dwi-ai-analysis.sif"
CANONICAL_BASE="$(basename "$CANONICAL")"

if [[ ! -f "$CANONICAL" ]]; then
  echo "ERROR: canonical image missing: $CANONICAL" >&2
  echo "Build with: bash containers/build.sh" >&2
  exit 1
fi

if [[ -e "$LEGACY" && ! -L "$LEGACY" ]]; then
  echo "ERROR: $LEGACY is a regular file (duplicate image)." >&2
  echo "Remove it and recreate the symlink: bash containers/build.sh" >&2
  exit 1
fi

if [[ -L "$LEGACY" ]]; then
  LINK_TARGET="$(readlink "$LEGACY")"
  if [[ "$LINK_TARGET" != "$CANONICAL_BASE" ]]; then
    echo "ERROR: legacy symlink points to '$LINK_TARGET', expected '$CANONICAL_BASE'" >&2
    exit 1
  fi
  LEGACY_REAL="$(readlink -f "$LEGACY")"
  CANONICAL_REAL="$(readlink -f "$CANONICAL")"
  if [[ "$LEGACY_REAL" != "$CANONICAL_REAL" ]]; then
    echo "ERROR: legacy symlink does not resolve to the canonical image" >&2
    exit 1
  fi
fi

echo "OK: one nodestrength image"
echo "  canonical: $CANONICAL ($(du -h "$CANONICAL" | cut -f1))"
if [[ -L "$LEGACY" ]]; then
  echo "  legacy:    $LEGACY -> $LINK_TARGET (same file)"
else
  echo "  legacy:    (no symlink — optional; run build.sh to create)"
fi
