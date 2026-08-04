#!/usr/bin/env bash
# Run DKT node-strength cohort via Singularity (repo convenience wrapper).
#
# Usage:
#   bash containers/run_dkt_cohort.sh CONNECTOME_DIR OUTPUT_DIR [FS_DIR] [OPTIONS]
#   CONNECTOME_ROOT=... OUTPUT_DIR=... bash containers/run_dkt_cohort.sh
#
# Options are passed through to the container (e.g. --strength-only, --include SUB).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "${REPO_ROOT}/containers/run.sh" "$@"
