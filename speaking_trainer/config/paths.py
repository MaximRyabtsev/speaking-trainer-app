from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "SpeakingTrainer"


def app_support_dir() -> Path:
    override = os.environ.get("SPEAKING_TRAINER_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / "Library" / "Application Support" / APP_DIR_NAME


def models_dir() -> Path:
    return app_support_dir() / "models"


def default_projects_dir() -> Path:
    return Path.home() / "Documents" / "SpeakingTrainer" / "projects"


def settings_path() -> Path:
    return app_support_dir() / "settings.json"


def ensure_app_dirs() -> None:
    for path in [app_support_dir(), models_dir() / "llm", models_dir() / "whisper", default_projects_dir()]:
        path.mkdir(parents=True, exist_ok=True)


def bundled_resource_dir() -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    executable = Path(sys.executable).resolve()
    resources = executable.parent.parent / "Resources"
    if resources.exists():
        return resources
    return Path(__file__).resolve().parents[2]


def bundled_bin_dir() -> Path:
    return bundled_resource_dir() / "bin"


def project_vendor_bin_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "vendor" / "bin"
