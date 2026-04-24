from __future__ import annotations

from pathlib import Path

from speaking_trainer.utils.text import normalize_plain_text


class UnsupportedDocumentError(ValueError):
    pass


class DocumentImporter:
    SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown"}

    def import_text(self, file_path: Path) -> str:
        path = file_path.expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Input file does not exist: {path}")
        if path.suffix.lower() not in self.SUPPORTED_SUFFIXES:
            raise UnsupportedDocumentError("Only .txt and .md input files are supported.")
        text = normalize_plain_text(path.read_text(encoding="utf-8", errors="replace"))
        if len(text) < 30:
            raise ValueError("The input text is too short to generate useful speaking questions.")
        return text
