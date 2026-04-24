from __future__ import annotations

from pathlib import Path

from speaking_trainer.config.settings import AppSettings
from speaking_trainer.utils.subprocess_runner import assert_executable_file, run_capture


class AudioExtractorError(RuntimeError):
    pass


class AudioExtractor:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def extract_wav(self, video_path: Path, wav_path: Path, log_path: Path) -> Path:
        assert_executable_file(self.settings.ffmpeg_path, "FFmpeg")
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [self.settings.ffmpeg_path, "-y", "-hide_banner", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", str(wav_path)]
        result = run_capture(cmd, timeout=1800)
        log_path.write_text("COMMAND:\n" + " ".join(cmd) + "\n\nSTDOUT:\n" + result.stdout + "\n\nSTDERR:\n" + result.stderr, encoding="utf-8")
        if result.returncode != 0 or not wav_path.exists() or wav_path.stat().st_size < 1024:
            raise AudioExtractorError("FFmpeg audio extraction failed.\n\n" + result.stderr[-4000:])
        return wav_path
