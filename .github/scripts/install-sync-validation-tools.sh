#!/usr/bin/env bash
set -euo pipefail

readonly HADOLINT_VERSION="v2.12.0"

missing=()
command -v direnv >/dev/null 2>&1 || missing+=(direnv)
command -v rg >/dev/null 2>&1 || missing+=(ripgrep)
command -v shellcheck >/dev/null 2>&1 || missing+=(shellcheck)
if [ "${#missing[@]}" -gt 0 ]; then
  sudo apt-get update
  sudo apt-get install -y "${missing[@]}"
fi

if ! command -v hadolint >/dev/null 2>&1; then
  arch="$(uname -m)"
  case "$arch" in
    x86_64|amd64) asset="hadolint-Linux-x86_64" ;;
    aarch64|arm64) asset="hadolint-Linux-arm64" ;;
    *) echo "Unsupported architecture for hadolint: $arch" >&2; exit 2 ;;
  esac
  download="$(mktemp)"
  trap 'rm -f "$download"' EXIT
  curl -fsSL \
    -o "$download" \
    "https://github.com/hadolint/hadolint/releases/download/${HADOLINT_VERSION}/${asset}"
  sudo install -m 0755 "$download" /usr/local/bin/hadolint
  rm -f "$download"
  trap - EXIT
fi

hadolint --version
