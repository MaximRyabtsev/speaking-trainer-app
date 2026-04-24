from __future__ import annotations

from pathlib import Path

from speaking_trainer.config.settings import AppSettings
from speaking_trainer.utils.subprocess_runner import assert_executable_file, run_capture


class WhisperCppError(RuntimeError):
    pass


class LocalWhisperCppAdapter:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def transcribe(self, wav_path: Path, output_base: Path, log_path: Path) -> Path:
        assert_executable_file(self.settings.whisper_cli_path, "whisper-cli")
        assert_executable_file(self.settings.whisper_model_path, "Whisper model")
        output_base.parent.mkdir(parents=True, exist_ok=True)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [self.settings.whisper_cli_path, "-m", self.settings.whisper_model_path, "-f", str(wav_path), "-l", "en", "-otxt", "-of", str(output_base)]
        result = run_capture(cmd, timeout=60 * 60)
        log_path.write_text("COMMAND:\n" + " ".join(cmd) + "\n\nSTDOUT:\n" + result.stdout + "\n\nSTDERR:\n" + result.stderr, encoding="utf-8")
        if result.returncode != 0:
            raise WhisperCppError("whisper-cli failed.\n\n" + result.stderr[-4000:])
        transcript = output_base.with_suffix(".txt")
        if not transcript.exists():
            candidates = sorted(output_base.parent.glob(output_base.name + "*.txt"))
            if not candidates:
                raise WhisperCppError("whisper-cli finished, but transcript .txt was not found.")
            transcript = candidates[0]
        return transcript
