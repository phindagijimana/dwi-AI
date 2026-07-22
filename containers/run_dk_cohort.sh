#!/usr/bin/env bash
# Run DK node-strength + strength AI + volume AI (default) via Singularity.
#
# Usage:
#   export SIF=/path/to/dwi-ai-analysis.sif
#   bash containers/run_dk_cohort.sh
#   bash containers/run_dk_cohort.sh --include TBI011204
#   bash containers/run_dk_cohort.sh --strength-only   # skip volume/compare

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${NODESTRENGTH_VERSION:-0.1.0}"
SIF="${SIF:-${REPO_ROOT}/containers/nodestrength_${VERSION}.sif}"
CONNECT="${CONNECT:-${CONNECTOME_ROOT:-/mnt/nfs/Gugger_Lab/NIR/dwi_test2/dk_connectomes}}"
OUT="${OUT:-${OUTPUT_DIR:-/mnt/nfs/Gugger_Lab/NIR/dwi_test2/node_strength_results}}"

if [[ ! -f "$SIF" ]]; then
  legacy="${REPO_ROOT}/containers/dwi-ai-analysis.sif"
  if [[ -f "$legacy" ]]; then
    SIF="$legacy"
  else
    echo "Missing image: $SIF" >&2
    echo "Build with: bash containers/build.sh" >&2
    exit 1
  fi
fi

exec apptainer run --cleanenv \
  -B "$CONNECT:$CONNECT:ro" \
  -B "$OUT:$OUT" \
  "$SIF" \
  "$CONNECT" "$OUT" \
  "$@"
