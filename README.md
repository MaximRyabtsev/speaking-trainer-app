# Speaking Trainer

Local-first macOS desktop app for practicing English speaking from a TXT or MD file.

## What it does

- Imports `.txt`, `.md`, `.markdown` files.
- Generates exactly 5 or 10 open-ended English speaking questions using local `llama.cpp`.
- Records one full webcam + microphone session with FFmpeg.
- Moves to the next question with Space.
- Transcribes after the session using local `whisper.cpp`.
- Exports video, questions with timestamps, transcript TXT/MD, and a session manifest.

No PDF input, no OCR, no live transcription, no analytics, no answer scoring, no cloud dependency.

## Recommended setup for Mac M1 8 GB

- Python 3.11 or 3.12
- PySide6
- FFmpeg
- llama.cpp `llama-cli`
- whisper.cpp `whisper-cli`
- LLM: small instruct GGUF model, for example 1B-2B Q4
- STT: whisper.cpp `base.en` model

Models are stored outside the app:

```text
~/Library/Application Support/SpeakingTrainer/models/
├── llm/model.gguf
└── whisper/ggml-base.en.bin
```

## Development run

```bash
cd speaking-trainer-app
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m speaking_trainer.main
```

## Tools

The app looks for tools in this order:

1. `Speaking Trainer.app/Contents/Resources/bin/`
2. `vendor/bin/` inside this repository
3. `/opt/homebrew/bin/`
4. `/usr/local/bin/`
5. system `PATH`
6. manually selected Settings paths

You can build/copy local tools into `vendor/bin`:

```bash
./scripts/install_local_tools_macos.sh
```

## Build `.app`

```bash
source .venv/bin/activate
./scripts/build_macos_app.sh
```

Output:

```text
dist/Speaking Trainer.app
```

The app is unsigned. For personal use, right-click → Open if macOS blocks it.

## Output folder

```text
~/Documents/SpeakingTrainer/projects/
└── project_id/
    ├── source.txt
    ├── project.json
    ├── questions.json
    ├── questions.txt
    └── sessions/
        └── session_id/
            ├── session.mp4
            ├── question_timestamps.txt
            ├── question_timestamps.json
            ├── transcript.txt
            ├── transcript.md
            ├── session_manifest.json
            └── logs/
```

## Device setup

Open Settings → List AVFoundation devices.

FFmpeg lists devices as indexes. Use those indexes in:

```text
Camera index
Microphone index
```

For example:

```text
Camera index: 0
Microphone index: 0
```
