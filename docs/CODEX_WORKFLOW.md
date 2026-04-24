# Codex workflow for Speaking Trainer

## Install Codex CLI

```bash
npm i -g @openai/codex
```

Then from the repository root:

```bash
cd ~/Desktop/speaking-trainer-app
codex
```

The first run asks you to sign in.

## Recommended first prompt

```text
Read AGENTS.md, README.md, and ARCHITECTURE.md. Summarize the project, the hard constraints, and the safest commands to verify changes. Do not edit files yet.
```

## Good task prompts

### Fix a bug

```text
Bug: describe the exact behavior and paste the terminal output.
Follow AGENTS.md. Make the smallest safe change. Preserve offline-first behavior. After editing, run python -m compileall -q speaking_trainer and summarize the diff.
```

### Add a setting

```text
Add a simple setting for ____. Keep the UI minimal. Do not add new production dependencies. Update README if user-facing behavior changes. Run lightweight checks.
```

### Review before committing

```text
Review the uncommitted diff for regressions. Pay special attention to llama-cli interactive mode, log filtering, macOS paths, and whether any large/generated files are accidentally staged.
```

## Recommended Codex habits

- Start Codex from the repository root.
- Keep tasks small: one bug or feature per session.
- Paste actual logs when debugging local tools.
- Ask Codex to inspect `git diff` before you commit.
- Do not let Codex commit models, binaries, session videos, transcripts, `.venv`, `vendor`, `dist`, or `build`.

## Useful commands inside Codex

Ask Codex to run these when relevant:

```bash
python -m compileall -q speaking_trainer
./scripts/check_project.sh
git status --short
git diff --stat
git diff
```

## Safe model/tool assumptions

Codex should assume the project is designed for:

- Mac M1 8 GB;
- Python + PySide6;
- local `llama.cpp`, `whisper.cpp`, and FFmpeg;
- no default cloud/API dependency;
- models stored outside the repo.
