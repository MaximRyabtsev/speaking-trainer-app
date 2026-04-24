#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR_BIN="$ROOT_DIR/vendor/bin"
VENDOR_SRC="$ROOT_DIR/vendor/src"
mkdir -p "$VENDOR_BIN" "$VENDOR_SRC"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required for this helper script: https://brew.sh"
  exit 1
fi

brew install ffmpeg cmake git || true
if command -v ffmpeg >/dev/null 2>&1; then cp "$(command -v ffmpeg)" "$VENDOR_BIN/ffmpeg" || true; fi

cd "$VENDOR_SRC"
if [ ! -d llama.cpp ]; then git clone https://github.com/ggml-org/llama.cpp.git; fi
cd llama.cpp
git pull --ff-only || true
cmake -B build -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j "$(sysctl -n hw.logicalcpu)"
LLAMA_BIN="$(find build -type f -name llama-cli | head -n 1)"
[ -n "$LLAMA_BIN" ] && cp "$LLAMA_BIN" "$VENDOR_BIN/llama-cli"

cd "$VENDOR_SRC"
if [ ! -d whisper.cpp ]; then git clone https://github.com/ggml-org/whisper.cpp.git; fi
cd whisper.cpp
git pull --ff-only || true
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j "$(sysctl -n hw.logicalcpu)"
WHISPER_BIN="$(find build -type f -name whisper-cli | head -n 1)"
[ -n "$WHISPER_BIN" ] && cp "$WHISPER_BIN" "$VENDOR_BIN/whisper-cli"

echo "Installed tools into $VENDOR_BIN"
ls -la "$VENDOR_BIN"
