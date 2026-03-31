#!/usr/bin/env bash
# Build pdfdiff sidecar binary for Tauri.
#
# Usage:
#   cd pdfdiff && ./build.sh
#
# Requires: pip install pyinstaller
# Output: dist/pdfdiff (or dist/pdfdiff.exe on Windows)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Installing dependencies..."
pip install -e ".[dev]" --quiet

echo "Building pdfdiff binary..."
pyinstaller pdfdiff.spec --clean --noconfirm

# Determine target triple for Tauri sidecar naming
ARCH="$(uname -m)"
OS="$(uname -s)"

case "$OS" in
    Darwin)
        case "$ARCH" in
            arm64) TARGET="aarch64-apple-darwin" ;;
            x86_64) TARGET="x86_64-apple-darwin" ;;
        esac
        ;;
    Linux)
        TARGET="${ARCH}-unknown-linux-gnu"
        ;;
esac

SIDECAR_DIR="../src-tauri/binaries"
mkdir -p "$SIDECAR_DIR"

BINARY="dist/pdfdiff"
DEST="$SIDECAR_DIR/pdfdiff-${TARGET}"

cp "$BINARY" "$DEST"
chmod +x "$DEST"

echo "Sidecar binary copied to: $DEST"
echo "Done."
