from __future__ import annotations

from datetime import datetime
from pathlib import Path

from speaking_trainer.config.settings import AppSettings
from speaking_trainer.models.domain import Project, Question
from speaking_trainer.services.document_importer import DocumentImporter
from speaking_trainer.services.exporter import Exporter
from speaking_trainer.utils.text import slugify


class ProjectService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.importer = DocumentImporter()
        self.exporter = Exporter()

    def create_project_from_file(self, source_path: Path, question_count: int) -> tuple[Project, str]:
        source_text = self.importer.import_text(source_path)
        project_id = f"{slugify(source_path.stem)}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        directory = Path(self.settings.projects_dir).expanduser() / project_id
        project = Project(project_id=project_id, title=source_path.stem, directory=directory, source_file_name=source_path.name, source_text_path=directory / "source.txt", question_count=question_count)
        self.exporter.save_project_files(project, source_text)
        return project, source_text

    def attach_questions(self, project: Project, raw_questions: list[str]) -> Project:
        project.questions = [Question(index=i + 1, text=text) for i, text in enumerate(raw_questions)]
        self.exporter.save_questions(project)
        return project
