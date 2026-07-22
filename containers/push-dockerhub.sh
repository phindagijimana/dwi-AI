#!/usr/bin/env bash
# Push nodestrength SIF to Docker Hub (OCI/ORAS).
#
# Prerequisites:
#   1. Docker Hub repo: https://hub.docker.com/r/phindagijimana321/nodestrength
#   2. Access token: hub.docker.com → Account Settings → Security → New Access Token
#   3. Login once:
#        podman login docker.io -u phindagijimana321
#
# Usage:
#   bash containers/push-dockerhub.sh
#   bash containers/push-dockerhub.sh /path/to/nodestrength_0.1.0.sif

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${1:-${REPO_ROOT}/containers/nodestrength_0.1.0.sif}"
VERSION="${NODESTRENGTH_VERSION:-0.1.0}"
USER="${DOCKERHUB_USER:-phindagijimana321}"

find_authfile() {
  local p
  for p in \
    "${REGISTRY_AUTH_FILE:-}" \
    "${DOCKER_AUTHFILE:-}" \
    "${XDG_RUNTIME_DIR:+$XDG_RUNTIME_DIR/containers/auth.json}" \
    "$HOME/.config/containers/auth.json" \
    "$HOME/.docker/config.json"; do
    if [[ -n "$p" && -f "$p" ]]; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

# Apptainer looks up index.docker.io; podman stores docker.io — normalize in a temp file.
prepare_authfile() {
  local src="$1"
  local dst
  dst="$(mktemp "${TMPDIR:-/tmp}/nodestrength-docker-auth.XXXXXX")"
  python3 - "$src" "$dst" <<'PY'
import json
import sys
from copy import deepcopy

src, dst = sys.argv[1:3]
with open(src, encoding="utf-8") as fh:
    data = json.load(fh)

auths = data.setdefault("auths", {})
for key in list(auths):
    if key in {"docker.io", "https://index.docker.io/v1/", "index.docker.io"}:
        entry = deepcopy(auths[key])
        auths.setdefault("docker.io", entry)
        auths.setdefault("https://index.docker.io/v1/", entry)
        auths.setdefault("index.docker.io", entry)

with open(dst, "w", encoding="utf-8") as fh:
    json.dump(data, fh)
PY
  echo "$dst"
}

if [[ ! -f "$IMAGE" ]]; then
  echo "Missing image: $IMAGE" >&2
  echo "Build first: bash containers/build.sh" >&2
  exit 1
fi

if [[ -n "${DOCKERHUB_TOKEN:-}" ]] && ! podman login --get-login docker.io &>/dev/null; then
  echo "$DOCKERHUB_TOKEN" | podman login docker.io -u "$USER" --password-stdin
fi

if ! podman login --get-login docker.io &>/dev/null; then
  echo "Not logged into Docker Hub. Run:" >&2
  echo "  podman login docker.io -u $USER" >&2
  exit 1
fi

SRC_AUTH="$(find_authfile || true)"
if [[ -z "$SRC_AUTH" ]]; then
  echo "Logged into podman but auth file not found." >&2
  echo "Try: export XDG_RUNTIME_DIR=\$XDG_RUNTIME_DIR && podman login docker.io -u $USER" >&2
  exit 1
fi

AUTH_TMP="$(prepare_authfile "$SRC_AUTH")"
trap 'rm -f "$AUTH_TMP"' EXIT

echo "Using auth file: $SRC_AUTH"
echo "Pushing $IMAGE → docker.io/${USER}/nodestrength:${VERSION}"

push_image() {
  local tag="$1"
  local uris=(
    "oras://index.docker.io/${USER}/nodestrength:${tag}"
    "oras://docker.io/${USER}/nodestrength:${tag}"
  )
  local uri err
  for uri in "${uris[@]}"; do
    err="$(mktemp)"
    if apptainer push --authfile "$AUTH_TMP" "$IMAGE" "$uri" 2>"$err"; then
      echo "  pushed via $uri"
      rm -f "$err"
      return 0
    fi
    echo "  warn: $uri failed ($(tail -1 "$err"))" >&2
    rm -f "$err"
  done
  return 1
}

push_image "$VERSION"
push_image latest

echo ""
echo "Published:"
echo "  https://hub.docker.com/r/${USER}/nodestrength"
echo ""
echo "Pull/run (Apptainer — SIF artifact on Docker Hub):"
echo "  apptainer pull nodestrength.sif oras://index.docker.io/${USER}/nodestrength:${VERSION}"
echo "  apptainer run nodestrength.sif /connectomes /output"
echo ""
echo "Note: this ORAS push stores a .sif artifact. For standard 'docker pull' / Docker"
echo "      runtime, use GitHub Actions (containers/README.md) to build a Docker image."
