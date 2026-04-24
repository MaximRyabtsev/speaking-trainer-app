from __future__ import annotations

from pathlib import Path
from typing import Any

from speaking_trainer.models.domain import Project, Question, TrainingSession
from speaking_trainer.utils.json_io import write_json
from speaking_trainer.utils.timecode import format_timecode


class Exporter:
    def save_project_files(self, project: Project, source_text: str) -> None:
        project.directory.mkdir(parents=True, exist_ok=True)
        project.source_text_path.write_text(source_text, encoding="utf-8")
        write_json(project.directory / "project.json", {"project_id": project.project_id, "title": project.title, "source_file_name": project.source_file_name, "question_count": project.question_count})

    def save_questions(self, project: Project) -> None:
        write_json(project.directory / "questions.json", {"question_count": project.question_count, "questions": [{"index": q.index, "text": q.text, "shown_at_seconds": q.shown_at_seconds} for q in project.questions]})
        (project.directory / "questions.txt").write_text(self._questions_txt(project.questions), encoding="utf-8")

    def save_question_timestamps(self, session: TrainingSession) -> Path:
        path = session.directory / "question_timestamps.txt"
        path.write_text(self._questions_txt(session.questions), encoding="utf-8")
        write_json(session.directory / "question_timestamps.json", {"questions": [{"index": q.index, "text": q.text, "shown_at_seconds": q.shown_at_seconds, "timecode": format_timecode(q.shown_at_seconds or 0)} for q in session.questions]})
        return path

    def save_transcript_md(self, transcript_txt_path: Path, transcript_md_path: Path) -> None:
        text = transcript_txt_path.read_text(encoding="utf-8", errors="replace").strip()
        transcript_md_path.write_text("# Transcript\n\n" + text + "\n", encoding="utf-8")

    def save_manifest(self, session: TrainingSession, data: dict[str, Any]) -> None:
        write_json(session.directory / "session_manifest.json", data)

    @staticmethod
    def _questions_txt(questions: list[Question]) -> str:
        lines: list[str] = []
        for q in questions:
            lines.append(f"{format_timecode(q.shown_at_seconds or 0)} — Question {q.index}")
            lines.append(q.text)
            lines.append("")
        return "\n".join(lines).strip() + "\n"
