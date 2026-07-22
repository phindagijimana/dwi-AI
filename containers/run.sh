#!/usr/bin/env bash
# Standalone runner for nodestrength Apptainer/Singularity images.
# Copy this script next to nodestrength_*.sif — no repo checkout required.
#
# Usage:
#   ./run.sh CONNECTOME_DIR OUTPUT_DIR [--strength-only] [--include SUB ...]
#   CONNECTOME_ROOT=/data/in OUTPUT_DIR=/data/out ./run.sh
#
# Environment:
#   SIF              Path to .sif (default: nodestrength_0.1.0.sif beside this script)
#   CONNECTOME_ROOT  Connectome parent directory (sub-*/dk_connectome.csv)
#   OUTPUT_DIR       Writable output directory

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${NODESTRENGTH_VERSION:-0.1.0}"
SIF="${SIF:-${SCRIPT_DIR}/nodestrength_${VERSION}.sif}"

if [[ ! -f "$SIF" ]]; then
  # Backward-compatible name from earlier builds
  if [[ -f "${SCRIPT_DIR}/dwi-ai-analysis.sif" ]]; then
    SIF="${SCRIPT_DIR}/dwi-ai-analysis.sif"
  else
    echo "Missing image: $SIF" >&2
    echo "Place nodestrength_${VERSION}.sif in ${SCRIPT_DIR} or set SIF=" >&2
    exit 1
  fi
fi

if [[ -n "${CONNECTOME_ROOT:-}" && -n "${OUTPUT_DIR:-}" ]]; then
  CONNECT="$CONNECTOME_ROOT"
  OUT="$OUTPUT_DIR"
elif [[ $# -ge 2 ]]; then
  CONNECT="$1"
  OUT="$2"
  shift 2
else
  cat <<EOF >&2
Usage: $0 CONNECTOME_DIR OUTPUT_DIR [container flags...]
   or: CONNECTOME_ROOT=... OUTPUT_DIR=... $0 [container flags...]

Example:
  $0 /path/to/dk_connectomes /path/to/node_strength_results
EOF
  exit 1
fi

exec apptainer run --cleanenv \
  -B "$CONNECT:$CONNECT:ro" \
  -B "$OUT:$OUT" \
  "$SIF" \
  "$CONNECT" "$OUT" \
  "$@"
