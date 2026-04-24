#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
pyinstaller packaging/SpeakingTrainer.spec --clean --noconfirm
echo "Built app: $ROOT_DIR/dist/Speaking Trainer.app"
