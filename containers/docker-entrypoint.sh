#!/usr/bin/env bash
# Container entrypoint: standalone DK cohort analysis (no repo checkout required).
#
# Positional shorthand (like qsiprep/freesurfer bind-mount workflows):
#   apptainer run image.sif /connectomes /output [/freesurfer]
#
# Flag form:
#   apptainer run image.sif --root /connectomes --out /output [--fs-root /freesurfer]
#
# Environment defaults (optional):
#   CONNECTOME_ROOT, OUTPUT_DIR, FS_ROOT
#
# Container-only:
#   --strength-only   skip volume/ and compare/ (volume AI is on by default)
#   --no-report       skip clinical PDF reports (reports on by default in image)

set -euo pipefail

VERSION="${NODESTRENGTH_VERSION:-0.1.0}"

usage() {
  cat <<EOF
nodestrength ${VERSION} — DK node strength + interhemispheric AI + volume AI

Standalone analysis container. Mount host connectome and output directories,
then run with positional paths or flags. No Python install or repo checkout.

Usage:
  apptainer run [apptainer-flags] IMAGE.sif CONNECTOME_DIR OUTPUT_DIR [FS_DIR] [OPTIONS]
  apptainer run [apptainer-flags] IMAGE.sif --root CONNECTOME_DIR --out OUTPUT_DIR [--fs-root FS_DIR] [OPTIONS]

Positional:
  CONNECTOME_DIR    Parent folder: one subfolder per subject with connectome CSV
  OUTPUT_DIR        Writable directory for strength/, volume/, compare/, reports/
  FS_DIR            Optional FreeSurfer SUBJECTS_DIR (for dk_nodes.mif lookup)

Environment (optional defaults):
  CONNECTOME_ROOT   Same as --root / first positional argument
  OUTPUT_DIR        Same as --out / second positional argument
  FS_ROOT           Same as --fs-root / third positional argument

Options:
  --strength-only   Skip volume AI (no volume/ or compare/)
  --no-report       Skip clinical PDF reports (default: on)
  --include SUB ... Process only these subject IDs (with or without sub- prefix)
  --with-volume-ai  Force volume AI (already default in this image)
  --fs-root DIR     FreeSurfer SUBJECTS_DIR (alternative to third positional)
  --help            Show this message

Example:
  apptainer run --cleanenv \\
    -B /data/connectomes:/data/connectomes:ro \\
    -B /data/freesurfer:/data/freesurfer:ro \\
    -B /data/out:/data/out \\
    nodestrength_${VERSION}.sif \\
    /data/connectomes /data/out /data/freesurfer

Outputs per subject:
  strength/ volume/ compare/   analysis CSVs (intra AI included)
  reports/<subject>/figures/   full PNG visualization gallery
  reports/<subject>/report.pdf   lean clinical summary PDF

Inputs per subject folder under CONNECTOME_DIR:
  dkt_connectome.csv  required — 84x84 symmetric connectome per subject folder
  dk_nodes.mif        optional — under connectome folder or FS_DIR/<subject>/

Legacy connectome names still accepted: dk_connectome.csv, connectome.csv.
Package CLI inside the image: dkt-ai-cohort, nodestrength (dk-ai-cohort alias)
EOF
}

if [[ $# -eq 0 ]] || [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

strength_only=0
no_report=0
filtered=()

# Positional shorthand: CONNECTOME_DIR OUTPUT_DIR [FS_DIR] ...
if [[ "${1:-}" != --* ]] && [[ $# -ge 2 ]] && [[ "${2:-}" != --* ]]; then
  filtered+=(--root "$1" --out "$2")
  shift 2
  if [[ $# -ge 1 ]] && [[ "${1:-}" != --* ]]; then
    filtered+=(--fs-root "$1")
    shift
  fi
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
    --no-report)
      no_report=1
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
has_fs=0
for ((i = 0; i < ${#filtered[@]}; i++)); do
  [[ "${filtered[i]}" == --root ]] && has_root=1
  [[ "${filtered[i]}" == --out ]] && has_out=1
  [[ "${filtered[i]}" == --fs-root ]] && has_fs=1
done

if [[ "$has_root" -eq 0 && -n "${CONNECTOME_ROOT:-}" ]]; then
  filtered=(--root "$CONNECTOME_ROOT" "${filtered[@]}")
fi
if [[ "$has_out" -eq 0 && -n "${OUTPUT_DIR:-}" ]]; then
  filtered=(--out "$OUTPUT_DIR" "${filtered[@]}")
fi
if [[ "$has_fs" -eq 0 && -n "${FS_ROOT:-}" ]]; then
  filtered+=(--fs-root "$FS_ROOT")
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

if [[ "$no_report" -eq 0 ]]; then
  has_report_flag=0
  for arg in "${filtered[@]}"; do
    [[ "$arg" == --report ]] && has_report_flag=1
  done
  if [[ "$has_report_flag" -eq 0 ]]; then
    filtered+=(--report)
  fi
fi

exec dkt-ai-cohort "${filtered[@]}"
