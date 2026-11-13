#!/usr/bin/env bash
# Install pinned, checksum-verified copies of Trivy and Syft from their official GitHub releases.
# Pinned on purpose: a floating "latest" or a third-party setup action is a supply-chain risk.
# Usage: scripts/install-tools.sh trivy|syft ...
set -euo pipefail
TRIVY_VERSION=0.76.2
SYFT_VERSION=1.57.1

install_one() {
  local name=$1 ver url sums file
  case "$name" in
    trivy) ver=$TRIVY_VERSION
           base="https://github.com/aquasecurity/trivy/releases/download/v${ver}"
           file="trivy_${ver}_Linux-64bit.tar.gz"; sums="trivy_${ver}_checksums.txt" ;;
    syft)  ver=$SYFT_VERSION
           base="https://github.com/anchore/syft/releases/download/v${ver}"
           file="syft_${ver}_linux_amd64.tar.gz"; sums="syft_${ver}_checksums.txt" ;;
    *) echo "unknown tool $name" >&2; exit 1 ;;
  esac
  local tmp; tmp=$(mktemp -d)
  ( cd "$tmp"
    curl -sfLO "$base/$file"; curl -sfLO "$base/$sums"
    grep " $file\$" "$sums" | sha256sum -c -
    tar xzf "$file" "$name"
    sudo install -m 0755 "$name" /usr/local/bin/"$name" )
  rm -rf "$tmp"
  "$name" version 2>/dev/null | head -1 || "$name" --version | head -1
}

for t in "$@"; do install_one "$t"; done
