from __future__ import annotations

from pathlib import Path

from speaking_trainer.adapters.ffmpeg_adapter import FfmpegAdapter, RecordingProcess
from speaking_trainer.config.settings import AppSettings


class VideoRecorder:
    def __init__(self, settings: AppSettings) -> None:
        self.adapter = FfmpegAdapter(settings)
        self._current: RecordingProcess | None = None

    def list_devices(self) -> str:
        return self.adapter.list_avfoundation_devices()

    def start(self, output_path: Path, quality: str, log_path: Path) -> None:
        if self._current is not None:
            raise RuntimeError("Recording is already running.")
        self._current = self.adapter.start_recording(output_path, quality, log_path)

    def stop(self) -> None:
        if self._current is None:
            return
        try:
            self.adapter.stop_recording(self._current)
        finally:
            self._current = None
