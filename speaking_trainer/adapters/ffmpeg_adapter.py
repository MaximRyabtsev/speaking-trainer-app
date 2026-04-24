from __future__ import annotations

import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from speaking_trainer.config.settings import AppSettings
from speaking_trainer.utils.subprocess_runner import assert_executable_file, run_capture


class FfmpegError(RuntimeError):
    pass


@dataclass(slots=True)
class RecordingProcess:
    process: subprocess.Popen[str]
    output_path: Path
    log_path: Path


class FfmpegAdapter:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def list_avfoundation_devices(self) -> str:
        assert_executable_file(self.settings.ffmpeg_path, "FFmpeg")
        result = run_capture([self.settings.ffmpeg_path, "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""], timeout=20)
        return result.combined_output.strip()

    def start_recording(self, output_path: Path, quality: str, log_path: Path) -> RecordingProcess:
        assert_executable_file(self.settings.ffmpeg_path, "FFmpeg")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        input_spec = f"{self.settings.camera_index}:{self.settings.microphone_index}"
        cmd = [self.settings.ffmpeg_path, "-y", "-hide_banner"]
        if quality == "720p":
            cmd += ["-f", "avfoundation", "-framerate", "30", "-video_size", "1280x720", "-i", input_spec, "-c:v", "h264_videotoolbox", "-b:v", "2500k", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output_path)]
        elif quality == "240p":
            cmd += ["-f", "avfoundation", "-framerate", "24", "-i", input_spec, "-vf", "scale=-2:240", "-c:v", "h264_videotoolbox", "-b:v", "600k", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(output_path)]
        else:
            raise ValueError("Video quality must be '240p' or '720p'.")
        log_file = log_path.open("w", encoding="utf-8")
        log_file.write("COMMAND:\n" + " ".join(cmd) + "\n\n")
        log_file.flush()
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=log_file, stderr=subprocess.STDOUT, text=True, bufsize=1)
        time.sleep(1.0)
        if proc.poll() is not None:
            log_file.close()
            raise FfmpegError("FFmpeg recording failed to start.\n\n" + log_path.read_text(encoding="utf-8", errors="replace")[-4000:])
        return RecordingProcess(proc, output_path, log_path)

    def stop_recording(self, recording: RecordingProcess, timeout_seconds: float = 10.0) -> None:
        proc = recording.process
        if proc.poll() is None:
            try:
                if proc.stdin:
                    proc.stdin.write("q\n")
                    proc.stdin.flush()
            except Exception:
                pass
            try:
                proc.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                try:
                    proc.send_signal(signal.SIGINT)
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()
                    proc.wait(timeout=5)
        self._validate_output(recording.output_path, recording.log_path)

    @staticmethod
    def _validate_output(output_path: Path, log_path: Path) -> None:
        if not output_path.exists() or output_path.stat().st_size < 1024:
            log = log_path.read_text(encoding="utf-8", errors="replace")[-4000:] if log_path.exists() else ""
            raise FfmpegError("Recording file was not created correctly.\n\n" + log)
