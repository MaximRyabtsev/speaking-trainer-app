from __future__ import annotations

from speaking_trainer.adapters.llama_cpp_adapter import LocalLlamaCppAdapter
from speaking_trainer.config.settings import AppSettings


class QuestionGenerator:
    def __init__(self, settings: AppSettings) -> None:
        self.adapter = LocalLlamaCppAdapter(settings)

    def generate(self, source_text: str, count: int) -> list[str]:
        return self.adapter.generate_questions(source_text, count)
