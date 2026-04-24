# AGENTS.md — Speaking Trainer

## Project purpose

This is a local-first macOS desktop application for practicing English speaking from a `.txt`, `.md`, or `.markdown` input file.

The app:
- imports plain text or Markdown only;
- generates 5 or 10 open-ended English speaking questions using local `llama.cpp` / `llama-cli`;
- records one full webcam + microphone session using FFmpeg;
- advances questions with Space only;
- transcribes after the session using local `whisper.cpp` / `whisper-cli`;
- exports one video, questions with timestamps, transcript TXT/MD, and a session manifest.

## Hard product constraints

Preserve these unless the user explicitly asks otherwise:

- Target platform: the owner's Mac M1 with 8 GB RAM.
- Offline-first: no cloud/API dependency in the default workflow.
- No PDF input, no OCR, no live transcription, no analytics, no answer scoring.
- Models are external and must not be bundled into the app or committed to git.
- UI should stay minimal and practical.
- During a training session, do not run heavy LLM/STT work. Only show questions, record video/audio, and store timestamps.
- Transcription must happen only after the session ends.
- Video output is one complete session file, not per-question clips.

## Important directories

- `speaking_trainer/ui/` — PySide6 UI.
- `speaking_trainer/services/` — app workflow services.
- `speaking_trainer/adapters/` — wrappers around FFmpeg, llama.cpp, whisper.cpp.
- `speaking_trainer/config/` — path and settings handling.
- `speaking_trainer/models/` — domain dataclasses, not ML model files.
- `scripts/` — local setup/build/install scripts.
- `packaging/` — PyInstaller macOS app spec.
- `sample_input/` — tiny example files only.

## Local paths used by the app

External models live outside the repository:

```text
~/Library/Application Support/SpeakingTrainer/models/
├── llm/model.gguf
└── whisper/ggml-base.en.bin
```

Session outputs live outside the repository:

```text
~/Documents/SpeakingTrainer/projects/
```

Never commit model files, recorded videos, transcripts, generated session folders, `vendor/`, `.venv/`, `dist/`, or `build/`.

## Development commands

Create environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run app in development:

```bash
source .venv/bin/activate
python -m speaking_trainer.main
```

Install/build local tools:

```bash
./scripts/install_local_tools_macos.sh
```

Build `.app`:

```bash
source .venv/bin/activate
./scripts/build_macos_app.sh
```

Run lightweight checks before committing Python changes:

```bash
source .venv/bin/activate
python -m compileall -q speaking_trainer
./scripts/check_project.sh
```

If `scripts/check_project.sh` is unavailable, at minimum run:

```bash
python -m compileall -q speaking_trainer
```

## llama.cpp adapter rules

The `llama_cpp_adapter.py` file is fragile because `llama-cli` can enter an interactive prompt loop depending on model/template/build version.

When editing it:
- do not assume `llama-cli` exits by itself;
- keep timeout protection;
- keep stdout/stderr capture isolated from the terminal;
- keep log filtering for `ggml`, `llama_`, `Metal`, `GPU`, token stats, prompt stats, and similar technical lines;
- never convert technical logs into user-facing questions;
- never implement recursive self-retry that asks the model to fix its own output indefinitely;
- prefer: one model call → parse → clean → if too few questions, fill locally with safe generic speaking questions.

## FFmpeg/recording rules

- macOS recording uses AVFoundation device indexes.
- Keep 240p and 720p quality options.
- Recording must include microphone audio, because transcription depends on it.
- Do not block the UI thread while FFmpeg is running.
- Preserve one full `session.mp4` per session.

## Whisper/transcription rules

- Use local `whisper-cli` only.
- Transcribe after recording has fully stopped.
- Keep English language mode.
- Do not add analysis, scoring, filler-word detection, or timestamped transcript unless the user requests it.

## UI rules

Keep the UI simple:
- file selection;
- 5/10 question choice;
- 240p/720p choice;
- generated questions preview;
- Start;
- training screen with one question;
- Space means next question;
- processing screen;
- result buttons.

Do not add complex navigation, dashboards, history views, charts, or analytics unless explicitly requested.

## Dependency rules

- Ask before adding new production dependencies.
- Prefer Python standard library where reasonable.
- Do not introduce a database unless the data model becomes more complex.
- Do not require Ollama as a system dependency; direct `llama.cpp` is preferred.

## Done criteria for code changes

A change is done only when:
- syntax checks pass;
- the app still starts with `python -m speaking_trainer.main`;
- generated outputs remain in `~/Documents/SpeakingTrainer/projects/`;
- no models/binaries/videos are committed;
- user-facing errors are clear enough to debug missing model/tool paths;
- macOS local-first behavior is preserved.
