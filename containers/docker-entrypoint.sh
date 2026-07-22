#!/usr/bin/env bash
# Container entrypoint: standalone DK cohort analysis (no repo checkout required).
#
# Positional shorthand (like qsiprep/freesurfer bind-mount workflows):
#   apptainer run image.sif /connectomes /output
#
# Flag form:
#   apptainer run image.sif --root /connectomes --out /output
#
# Environment defaults (optional):
#   CONNECTOME_ROOT, OUTPUT_DIR
#
# Container-only:
#   --strength-only   skip volume/ and compare/ (volume AI is on by default)

set -euo pipefail

VERSION="${NODESTRENGTH_VERSION:-0.1.0}"

usage() {
  cat <<EOF
nodestrength ${VERSION} — DK node strength + interhemispheric AI + volume AI

Standalone analysis container. Mount host connectome and output directories,
then run with positional paths or flags. No Python install or repo checkout.

Usage:
  apptainer run [apptainer-flags] IMAGE.sif CONNECTOME_DIR OUTPUT_DIR [OPTIONS]
  apptainer run [apptainer-flags] IMAGE.sif --root CONNECTOME_DIR --out OUTPUT_DIR [OPTIONS]

Positional:
  CONNECTOME_DIR    Parent of sub-*/ folders with dk_connectome.csv
  OUTPUT_DIR        Writable directory for strength/, volume/, compare/

Environment (optional defaults):
  CONNECTOME_ROOT   Same as --root / first positional argument
  OUTPUT_DIR        Same as --out / second positional argument

Options:
  --strength-only   Skip volume AI (no volume/ or compare/)
  --include SUB ... Process only these subject IDs (with or without sub- prefix)
  --with-volume-ai  Force volume AI (already default in this image)
  --help            Show this message

Example:
  apptainer run --cleanenv \\
    -B /data/connectomes:/data/connectomes:ro \\
    -B /data/out:/data/out \\
    nodestrength_${VERSION}.sif \\
    /data/connectomes /data/out

Inputs per subject (under CONNECTOME_DIR/sub-XXX/):
  dk_connectome.csv   required — 84x84 symmetric connectome
  dk_nodes.mif        optional — required for volume AI (default on)

Package CLI inside the image: dk-ai-cohort, nodestrength
EOF
}

if [[ $# -eq 0 ]] || [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

strength_only=0
filtered=()

# Positional shorthand: CONNECTOME_DIR OUTPUT_DIR ...
if [[ "${1:-}" != --* ]] && [[ $# -ge 2 ]] && [[ "${2:-}" != --* ]]; then
  filtered+=(--root "$1" --out "$2")
  shift 2
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --strength-only)
      strength_only=1
      shift
      ;;
    *)
      filtered+=("$1")
      shift
      ;;
  esac
done

has_root=0
has_out=0
for ((i = 0; i < ${#filtered[@]}; i++)); do
  [[ "${filtered[i]}" == --root ]] && has_root=1
  [[ "${filtered[i]}" == --out ]] && has_out=1
done

if [[ "$has_root" -eq 0 && -n "${CONNECTOME_ROOT:-}" ]]; then
  filtered=(--root "$CONNECTOME_ROOT" "${filtered[@]}")
fi
if [[ "$has_out" -eq 0 && -n "${OUTPUT_DIR:-}" ]]; then
  filtered=(--out "$OUTPUT_DIR" "${filtered[@]}")
fi

if [[ "$strength_only" -eq 0 ]]; then
  has_volume_flag=0
  for arg in "${filtered[@]}"; do
    [[ "$arg" == --with-volume-ai ]] && has_volume_flag=1
  done
  if [[ "$has_volume_flag" -eq 0 ]]; then
    filtered+=(--with-volume-ai)
  fi
fi

exec dk-ai-cohort "${filtered[@]}"
