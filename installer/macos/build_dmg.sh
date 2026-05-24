#!/usr/bin/env bash
# ==========================================================================
#  TRPG Log Converter Pro - macOS DMG Builder
#
#  Usage:
#      installer/macos/build_dmg.sh
#
#  Pre-requisites:
#    - dist/TRPG_Converter_Pro.app must exist (produced by scripts/build.py)
#    - Either ``create-dmg`` (`brew install create-dmg`) for a polished DMG,
#      OR plain ``hdiutil`` as a fallback (built into macOS).
#
#  Output:
#      dist/installer/TRPG_Converter_Pro_<version>.dmg
# ==========================================================================
set -euo pipefail

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"
APP="$ROOT/dist/TRPG_Converter_Pro.app"
OUT_DIR="$ROOT/dist/installer"

# Read version from the single source.
VERSION="$( cd "$ROOT" && python3 -c "from core.version import __version__; print(__version__)" )"
DMG="$OUT_DIR/TRPG_Converter_Pro_${VERSION}.dmg"
VOL_NAME="TRPG Converter Pro ${VERSION}"

if [ ! -d "$APP" ]; then
  echo "error: $APP not found. Run scripts/build.py first." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
rm -f "$DMG"

# ── Preferred path: create-dmg gives a polished window with custom layout. ──
if command -v create-dmg >/dev/null 2>&1; then
  echo "Using create-dmg..."
  create-dmg \
    --volname "$VOL_NAME" \
    --volicon "$ROOT/resources/icon.icns" \
    --window-pos 200 120 \
    --window-size 660 400 \
    --icon-size 100 \
    --icon "TRPG_Converter_Pro.app" 160 200 \
    --hide-extension "TRPG_Converter_Pro.app" \
    --app-drop-link 500 200 \
    --no-internet-enable \
    "$DMG" "$APP"
else
  # ── Fallback: pure hdiutil. Plain but functional. ──
  echo "create-dmg not found; using hdiutil fallback (install via 'brew install create-dmg' for polished DMG)"
  STAGING="$(mktemp -d)"
  cp -R "$APP" "$STAGING/"
  ln -s /Applications "$STAGING/Applications"

  hdiutil create \
    -volname "$VOL_NAME" \
    -srcfolder "$STAGING" \
    -ov \
    -format UDZO \
    "$DMG"
  rm -rf "$STAGING"
fi

echo ""
echo "DMG built: $DMG"
ls -lh "$DMG"
