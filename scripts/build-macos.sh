#!/bin/bash
# PDF Compare - macOS Build Script
# Usage: ./scripts/build-macos.sh
#
# For code signing and notarization, set these environment variables:
#   APPLE_SIGNING_IDENTITY  - e.g. "Developer ID Application: Your Name (TEAM_ID)"
#   APPLE_ID                - Your Apple ID email
#   APPLE_PASSWORD          - App-specific password (NOT your Apple ID password)
#                             Generate at https://appleid.apple.com/account/manage → App-Specific Passwords
#   APPLE_TEAM_ID           - Your 10-character Team ID
#
# Without these variables, the app builds unsigned (fine for local use).

set -euo pipefail

echo ""
echo "=== PDF Compare - macOS Build ==="
echo ""

# --- Build Sidecar ---
echo "[1/2] Building pdfdiff sidecar..."
cd pdfdiff
pip install -e '.[dev]' --quiet
pyinstaller pdfdiff.spec --noconfirm
cd ..

TARGET=$(rustc -vV | grep host | cut -d' ' -f2)
cp pdfdiff/dist/pdfdiff "src-tauri/binaries/pdfdiff-${TARGET}"
echo "  Sidecar copied to binaries/pdfdiff-${TARGET}"

# --- Build Tauri App ---
echo ""
echo "[2/2] Building Tauri app..."

if [ -n "${APPLE_SIGNING_IDENTITY:-}" ]; then
    echo "  Code signing enabled: ${APPLE_SIGNING_IDENTITY}"
    if [ -n "${APPLE_ID:-}" ] && [ -n "${APPLE_PASSWORD:-}" ] && [ -n "${APPLE_TEAM_ID:-}" ]; then
        echo "  Notarization enabled"
    else
        echo "  Notarization disabled (missing APPLE_ID, APPLE_PASSWORD, or APPLE_TEAM_ID)"
    fi
else
    echo "  Building unsigned (set APPLE_SIGNING_IDENTITY for code signing)"
fi

npx tauri build

echo ""
echo "=== Build Complete! ==="
DMG=$(find src-tauri/target/release/bundle/dmg -name "*.dmg" 2>/dev/null | head -1)
if [ -n "$DMG" ]; then
    echo "DMG: $DMG"
else
    echo "Check src-tauri/target/release/bundle/ for build output."
fi
echo ""
