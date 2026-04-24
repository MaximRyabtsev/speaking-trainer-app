from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from speaking_trainer.config.paths import bundled_bin_dir, default_projects_dir, models_dir, project_vendor_bin_dir, settings_path


def _find_executable(name: str) -> str:
    for candidate in [bundled_bin_dir() / name, project_vendor_bin_dir() / name, Path("/opt/homebrew/bin") / name, Path("/usr/local/bin") / name]:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return shutil.which(name) or name


def _first_existing_model(*relative_candidates: str) -> str:
    base = models_dir()
    for rel in relative_candidates:
        candidate = base / rel
        if candidate.exists():
            return str(candidate)
    return ""


@dataclass(slots=True)
class AppSettings:
    ffmpeg_path: str
    llama_cli_path: str
    whisper_cli_path: str
    llm_model_path: str
    whisper_model_path: str
    projects_dir: str
    camera_index: str = "0"
    microphone_index: str = "0"
    default_video_quality: str = "720p"
    llm_context_size: int = 4096
    llm_max_chars: int = 12000
    cleanup_temp_audio: bool = True

    @classmethod
    def defaults(cls) -> "AppSettings":
        return cls(
            ffmpeg_path=_find_executable("ffmpeg"),
            llama_cli_path=_find_executable("llama-cli"),
            whisper_cli_path=_find_executable("whisper-cli"),
            llm_model_path=_first_existing_model("llm/model.gguf"),
            whisper_model_path=_first_existing_model("whisper/ggml-base.en.bin", "whisper/ggml-small.en.bin", "whisper/model.bin"),
            projects_dir=str(default_projects_dir()),
        )


class SettingsService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings_path()

    def load(self) -> AppSettings:
        defaults = AppSettings.defaults()
        if not self.path.exists():
            self.save(defaults)
            return defaults
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            merged: dict[str, Any] = asdict(defaults)
            merged.update(raw)
            return AppSettings(**merged)
        except Exception:
            try:
                self.path.replace(self.path.with_suffix(".broken.json"))
            except Exception:
                pass
            self.save(defaults)
            return defaults

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(settings), indent=2, ensure_ascii=False), encoding="utf-8")
