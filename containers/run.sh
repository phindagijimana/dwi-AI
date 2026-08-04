#!/usr/bin/env bash
# Standalone runner for nodestrength Apptainer/Singularity images.
# Copy this script next to nodestrength_*.sif — no repo checkout required.
#
# Usage:
#   ./run.sh CONNECTOME_DIR OUTPUT_DIR [FS_DIR] [--strength-only] [--include SUB ...]
#   CONNECTOME_ROOT=/data/in OUTPUT_DIR=/data/out FS_ROOT=/data/fs ./run.sh
#
# Environment:
#   SIF              Path to .sif (default: nodestrength_0.1.0.sif beside this script)
#   CONNECTOME_ROOT  Connectome parent directory (one folder per subject)
#   OUTPUT_DIR       Writable output directory
#   FS_ROOT          Optional FreeSurfer SUBJECTS_DIR

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${NODESTRENGTH_VERSION:-0.1.0}"
SIF="${SIF:-${SCRIPT_DIR}/nodestrength_${VERSION}.sif}"

if [[ ! -f "$SIF" ]]; then
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
  FS="${FS_ROOT:-}"
  EXTRA=("$@")
elif [[ $# -ge 2 ]]; then
  CONNECT="$1"
  OUT="$2"
  shift 2
  FS=""
  if [[ $# -ge 1 && "${1:-}" != --* ]]; then
    FS="$1"
    shift
  fi
  EXTRA=("$@")
else
  cat <<EOF >&2
Usage: $0 CONNECTOME_DIR OUTPUT_DIR [FS_DIR] [container flags...]
   or: CONNECTOME_ROOT=... OUTPUT_DIR=... [FS_ROOT=...] $0 [container flags...]

Example:
  $0 /path/to/dkt_connectomes /path/to/node_strength_results
  $0 /path/to/dkt_connectomes /path/to/out /path/to/freesurfer/subjects
EOF
  exit 1
fi

BINDS=(-B "$CONNECT:$CONNECT:ro" -B "$OUT:$OUT")
ARGS=("$CONNECT" "$OUT")
if [[ -n "$FS" ]]; then
  BINDS+=(-B "$FS:$FS:ro")
  ARGS+=("$FS")
fi

exec apptainer run --cleanenv \
  "${BINDS[@]}" \
  "$SIF" \
  "${ARGS[@]}" \
  "${EXTRA[@]}"
