#!/usr/bin/env bash
# Backward-compatible wrapper — prefer containers/run_dkt_cohort.sh

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "${REPO_ROOT}/containers/run_dkt_cohort.sh" "$@"
