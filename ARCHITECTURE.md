# Architecture

## Principle

During training the app only:

1. shows one question,
2. records webcam + microphone,
3. saves the timestamp when each question appears.

Generation happens before the session. Transcription happens after the session. This keeps Mac M1 8 GB smooth.

## Flow

```text
TXT/MD file
  ↓
DocumentImporter
  ↓
ProjectService saves source.txt
  ↓
QuestionGenerator → llama.cpp
  ↓
Training screen + SessionService
  ↓
VideoRecorder → FFmpeg
  ↓
Space timestamps via time.monotonic()
  ↓
AudioExtractor → WAV
  ↓
Transcriber → whisper.cpp
  ↓
Exporter → TXT/MD/JSON files
```

## Main modules

- `ui/main_window.py` — screen flow and user actions.
- `ui/settings_dialog.py` — local paths, device indexes, model paths.
- `services/project_service.py` — project folders and source/question saving.
- `services/session_service.py` — recording lifecycle and post-processing.
- `adapters/llama_cpp_adapter.py` — local question generation.
- `adapters/ffmpeg_adapter.py` — camera/mic recording and device listing.
- `adapters/whisper_cpp_adapter.py` — local transcription.

## Storage

Plain files and JSON. No SQLite because the MVP has no search, users, analytics, or long-term progress dashboard.

## Extension points

- Add PDF importer later inside `DocumentImporter`.
- Add OpenAI-compatible fallback as another LLM adapter.
- Add answer analysis after `transcript.txt` is created.
- Add video slicing using saved timestamps.
