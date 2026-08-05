#!/usr/bin/env bash
# Fail if staged or tracked repo files contain site-specific paths or subject IDs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PATTERNS=(
  'Gugger_Lab'
  'TBI011[0-9]+'
  '/mnt/nfs/'
  'smb://'
  'pndagiji@'
  'urmc-sh\.rochester\.edu'
  'dwi_test2'
)

files="$(git ls-files -c -o --exclude-standard)"
if [[ -z "$files" ]]; then
  exit 0
fi

failed=0
while IFS= read -r file; do
  [[ -f "$file" ]] || continue
  case "$file" in
    scripts/check_no_phi.sh|vendor/*) continue ;;
  esac
  for pat in "${PATTERNS[@]}"; do
    if grep -qE "$pat" "$file" 2>/dev/null; then
      echo "PHI/site-path check failed: $file matches /$pat/" >&2
      grep -nE "$pat" "$file" | head -3 >&2 || true
      failed=1
    fi
  done
done <<< "$files"

if [[ "$failed" -ne 0 ]]; then
  echo "Remove or gitignore sensitive paths/IDs before committing." >&2
  exit 1
fi

echo "OK: no site paths or subject ID patterns in tracked/staged files."
