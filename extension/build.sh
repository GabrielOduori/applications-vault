#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VERSION=$(grep '"version"' manifest.json | head -1 | sed 's/.*: *"\(.*\)".*/\1/')
DIST_DIR="dist"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

echo "Building Application Vault Extension v${VERSION}"
echo "================================================"

# --- Chrome (MV3) ---
echo ""
echo "Packing Chrome extension..."
CHROME_DIR="$DIST_DIR/chrome"
mkdir -p "$CHROME_DIR"

cp manifest.json "$CHROME_DIR/"
cp -r src "$CHROME_DIR/"
cp -r icons "$CHROME_DIR/"

# Create zip for Chrome Web Store upload
(cd "$CHROME_DIR" && zip -r "../application-vault-chrome-v${VERSION}.zip" . -x ".*")
echo "  -> dist/application-vault-chrome-v${VERSION}.zip"

# --- Firefox (MV2) ---
echo ""
echo "Packing Firefox extension..."
FIREFOX_DIR="$DIST_DIR/firefox"
mkdir -p "$FIREFOX_DIR"

cp manifest.firefox.json "$FIREFOX_DIR/manifest.json"
cp -r src "$FIREFOX_DIR/"
cp -r icons "$FIREFOX_DIR/"

# Create zip (.xpi is just a zip) for Firefox
(cd "$FIREFOX_DIR" && zip -r "../application-vault-firefox-v${VERSION}.xpi" . -x ".*")
echo "  -> dist/application-vault-firefox-v${VERSION}.xpi"

echo ""
echo "Done! Extension packages are in extension/dist/"
echo ""
echo "To install:"
echo "  Chrome:  chrome://extensions → Enable Developer Mode → Load unpacked → select dist/chrome/"
echo "           Or upload the .zip to Chrome Web Store"
echo "  Firefox: about:debugging → This Firefox → Load Temporary Add-on → select dist/firefox/manifest.json"
echo "           Or upload the .xpi to addons.mozilla.org"
