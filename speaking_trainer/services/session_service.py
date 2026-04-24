from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from speaking_trainer.adapters.whisper_cpp_adapter import LocalWhisperCppAdapter
from speaking_trainer.config.settings import AppSettings
from speaking_trainer.models.domain import Project, Question, TrainingSession
from speaking_trainer.services.audio_extractor import AudioExtractor
from speaking_trainer.services.exporter import Exporter
from speaking_trainer.services.video_recorder import VideoRecorder


class SessionService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.recorder = VideoRecorder(settings)
        self.exporter = Exporter()
        self.audio_extractor = AudioExtractor(settings)
        self.transcriber = LocalWhisperCppAdapter(settings)
        self.session: TrainingSession | None = None
        self._started_at: float | None = None
        self._current_index = 0
        self._quality = settings.default_video_quality

    @property
    def current_question(self) -> Question:
        if not self.session:
            raise RuntimeError("No active session.")
        return self.session.questions[self._current_index]

    def start(self, project: Project, quality: str) -> TrainingSession:
        if not project.questions:
            raise ValueError("Cannot start session without questions.")
        self._quality = quality
        session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        directory = project.directory / "sessions" / session_id
        logs = directory / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        questions = [Question(q.index, q.text, None) for q in project.questions]
        session = TrainingSession(session_id, directory, directory / "session.mp4", questions)
        self.recorder.start(session.video_path, quality, logs / "recording.log")
        self.session = session
        self._started_at = time.monotonic()
        self._current_index = 0
        self.session.questions[0].shown_at_seconds = 0.0
        self.exporter.save_question_timestamps(self.session)
        return session

    def advance_or_finish(self) -> bool:
        if not self.session or self._started_at is None:
            raise RuntimeError("No active session.")
        if self._current_index >= len(self.session.questions) - 1:
            return False
        self._current_index += 1
        self.session.questions[self._current_index].shown_at_seconds = time.monotonic() - self._started_at
        self.exporter.save_question_timestamps(self.session)
        return True

    def stop_recording(self) -> TrainingSession:
        if not self.session:
            raise RuntimeError("No active session.")
        self.recorder.stop()
        self.exporter.save_question_timestamps(self.session)
        return self.session

    def post_process(self, project: Project) -> dict[str, Path]:
        if not self.session:
            raise RuntimeError("No active session.")
        session = self.session
        logs = session.directory / "logs"
        wav = session.directory / "audio.wav"
        self.audio_extractor.extract_wav(session.video_path, wav, logs / "audio_extract.log")
        transcript = self.transcriber.transcribe(wav, session.directory / "transcript", logs / "transcription.log")
        target_transcript = session.directory / "transcript.txt"
        if transcript.resolve() != target_transcript.resolve():
            target_transcript.write_text(transcript.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
            transcript = target_transcript
        transcript_md = session.directory / "transcript.md"
        self.exporter.save_transcript_md(transcript, transcript_md)
        q_path = self.exporter.save_question_timestamps(session)
        self.exporter.save_manifest(session, {"app_version": "0.1.0", "created_at": session.session_id, "project_id": project.project_id, "source_file": project.source_file_name, "question_count": project.question_count, "video_quality": self._quality, "video_file": str(session.video_path), "questions_file": str(q_path), "transcript_file": str(transcript), "models": {"llm": self.settings.llm_model_path, "stt": self.settings.whisper_model_path}})
        if self.settings.cleanup_temp_audio:
            try:
                wav.unlink(missing_ok=True)
            except Exception:
                pass
        return {"session_dir": session.directory, "video": session.video_path, "questions": q_path, "transcript_txt": transcript, "transcript_md": transcript_md}
