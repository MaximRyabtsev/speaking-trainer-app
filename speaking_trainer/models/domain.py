from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Question:
    index: int
    text: str
    shown_at_seconds: float | None = None


@dataclass(slots=True)
class Project:
    project_id: str
    title: str
    directory: Path
    source_file_name: str
    source_text_path: Path
    question_count: int
    questions: list[Question] = field(default_factory=list)


@dataclass(slots=True)
class TrainingSession:
    session_id: str
    directory: Path
    video_path: Path
    questions: list[Question]
