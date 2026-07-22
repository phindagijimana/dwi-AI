#!/usr/bin/env bash
# Container entrypoint: run DK cohort analysis with volume AI enabled by default.
#
# Volume AI reads dk_nodes.mif (MRtrix label grid) via nodestrength.mif — no
# MRtrix binary required inside the container.
#
# Usage (same as run_dk_ai_cohort.py, plus container-only flag):
#   ... --root /data/connectomes --out /data/out
#   ... --root /data/connectomes --out /data/out --strength-only   # skip volume/

set -euo pipefail

strength_only=0
filtered=()
for arg in "$@"; do
  case "$arg" in
    --strength-only)
      strength_only=1
      ;;
    *)
      filtered+=("$arg")
      ;;
  esac
done

if [[ "$strength_only" -eq 0 ]]; then
  has_volume_flag=0
  for arg in "${filtered[@]}"; do
    [[ "$arg" == "--with-volume-ai" ]] && has_volume_flag=1
  done
  if [[ "$has_volume_flag" -eq 0 ]]; then
    filtered+=("--with-volume-ai")
  fi
fi

exec python /app/scripts/run_dk_ai_cohort.py "${filtered[@]}"
