#!/usr/bin/env bash
set -euo pipefail

REMOTE_URL="${1:-}"

if [[ -z "$REMOTE_URL" ]]; then
  cat >&2 <<'USAGE'
Usage:
  ./scripts/git_publish_first_time.sh git@github.com:YOUR_USERNAME/speaking-trainer-app.git

Create an empty remote repository first, then pass its SSH URL.
USAGE
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Remove local/generated cache files that may have come from zips or local runs.
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f \( -name "*.pyc" -o -name ".DS_Store" \) -delete

if [[ ! -d .git ]]; then
  git init
fi

git branch -M main

# Make sure ignored local folders are not tracked if the command is re-run.
git rm -r --cached .venv vendor dist build 2>/dev/null || true

git add .gitignore AGENTS.md README.md ARCHITECTURE.md pyproject.toml requirements.txt speaking_trainer scripts packaging sample_input docs .codex 2>/dev/null || true

echo "\n== Files staged for the first commit =="
git status --short

if git diff --cached --quiet; then
  echo "No staged changes to commit."
else
  git commit -m "Initial local speaking trainer app"
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi

echo "\n== Pushing to origin/main =="
git push -u origin main

echo "\nDone. Remote: $REMOTE_URL"
