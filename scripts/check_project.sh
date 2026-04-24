#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== Speaking Trainer lightweight checks =="

if [[ ! -d "speaking_trainer" ]]; then
  echo "ERROR: run this script from the project root or keep it in scripts/." >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: Python not found. Activate .venv first or set PYTHON_BIN." >&2
  exit 1
fi

"$PYTHON_BIN" -m compileall -q speaking_trainer

"$PYTHON_BIN" - <<'PY'
from pathlib import Path

from speaking_trainer.config.paths import app_support_dir, default_projects_dir, models_dir, settings_path
from speaking_trainer.config.settings import SettingsService

settings = SettingsService().load()

print("Python imports: OK")
print(f"App support: {app_support_dir()}")
print(f"Settings file: {settings_path()}")
print(f"Models dir: {models_dir()}")
print(f"Projects dir: {default_projects_dir()}")
print(f"Configured video quality: {settings.default_video_quality}")

checks = [
    ("ffmpeg", settings.ffmpeg_path),
    ("llama-cli", settings.llama_cli_path),
    ("whisper-cli", settings.whisper_cli_path),
    ("LLM model", settings.llm_model_path),
    ("Whisper model", settings.whisper_model_path),
]

for label, raw_path in checks:
    path = Path(raw_path).expanduser() if raw_path else None
    status = "OK" if path and path.exists() else "MISSING"
    print(f"{label}: {status} — {raw_path or '(not configured)'}")
PY

if [[ -d .git ]]; then
  printf "\n== Git short status ==\n"
  git status --short
fi

printf "\nChecks passed.\n"
