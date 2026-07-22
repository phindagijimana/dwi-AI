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
SIF="${SIF:-${REPO_ROOT}/containers/dwi-ai-analysis.sif}"
CONNECT="${CONNECT:-/mnt/nfs/Gugger_Lab/NIR/dwi_test2/dk_connectomes}"
OUT="${OUT:-/mnt/nfs/Gugger_Lab/NIR/dwi_test2/node_strength_results}"

if [[ ! -f "$SIF" ]]; then
  echo "Missing image: $SIF" >&2
  echo "Build with: docker build -t dwi-ai-analysis:latest $REPO_ROOT" >&2
  echo "Then: apptainer build $SIF docker-daemon://dwi-ai-analysis:latest" >&2
  exit 1
fi

exec apptainer run --cleanenv \
  -B "$CONNECT:$CONNECT:ro" \
  -B "$OUT:$OUT" \
  "$SIF" \
  --root "$CONNECT" \
  --out  "$OUT" \
  "$@"
