#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="Speaking Trainer.app"
DIST_APP="$ROOT_DIR/dist/$APP_NAME"
TARGET_APP="/Applications/$APP_NAME"

cd "$ROOT_DIR"

echo "==> Speaking Trainer macOS installer"
echo "Project: $ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "==> Creating Python virtual environment"
  if command -v python3.12 >/dev/null 2>&1; then
    python3.12 -m venv .venv
  else
    python3 -m venv .venv
  fi
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installing Python dependencies"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

missing=0
for bin in ffmpeg llama-cli whisper-cli; do
  if [[ ! -x "$ROOT_DIR/vendor/bin/$bin" ]]; then
    echo "WARNING: missing or non-executable vendor/bin/$bin"
    missing=1
  fi
done

if [[ "$missing" == "1" ]]; then
  echo ""
  echo "Some local tools are missing. Run this first:"
  echo "  ./scripts/install_local_tools_macos.sh"
  echo ""
  echo "Continuing anyway; the app can still be built, but recording/LLM/transcription may not work."
fi

echo "==> Building .app"
./scripts/build_macos_app.sh

if [[ ! -d "$DIST_APP" ]]; then
  echo "ERROR: build did not create $DIST_APP" >&2
  exit 1
fi

echo "==> Ad-hoc signing app for local macOS launch"
if command -v codesign >/dev/null 2>&1; then
  codesign --force --deep --sign - "$DIST_APP" || true
else
  echo "WARNING: codesign not found; skipping signing"
fi

echo "==> Installing to /Applications"
if [[ -d "$TARGET_APP" ]]; then
  echo "Removing previous app from /Applications"
  sudo rm -rf "$TARGET_APP"
fi
sudo ditto "$DIST_APP" "$TARGET_APP"

echo "==> Removing quarantine flag, if present"
sudo xattr -dr com.apple.quarantine "$TARGET_APP" 2>/dev/null || true

echo "==> Done"
echo "Installed: $TARGET_APP"
echo ""
echo "Opening app..."
open "$TARGET_APP"
