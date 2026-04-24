from __future__ import annotations

import subprocess
from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QButtonGroup, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QRadioButton, QStackedWidget, QTextEdit, QVBoxLayout, QWidget

from speaking_trainer.config.settings import AppSettings, SettingsService
from speaking_trainer.models.domain import Project, TrainingSession
from speaking_trainer.services.project_service import ProjectService
from speaking_trainer.services.question_generator import QuestionGenerator
from speaking_trainer.services.session_service import SessionService
from speaking_trainer.ui.settings_dialog import SettingsDialog
from speaking_trainer.ui.workers import Worker


class MainWindow(QMainWindow):
    def __init__(self, settings_service: SettingsService, initial_settings: AppSettings) -> None:
        super().__init__()
        self.setWindowTitle("Speaking Trainer")
        self.settings_service = settings_service
        self.settings = initial_settings
        self.thread_pool = QThreadPool.globalInstance()
        self.current_project: Project | None = None
        self.current_source_text = ""
        self.session_service: SessionService | None = None
        self.last_outputs: dict[str, Path] = {}
        self.selected_file: Path | None = None
        self.stack = QStackedWidget(); self.setCentralWidget(self.stack)
        self.project_page = self._build_project_page(); self.questions_page = self._build_questions_page(); self.training_page = self._build_training_page(); self.processing_page = self._build_processing_page(); self.results_page = self._build_results_page()
        for page in [self.project_page, self.questions_page, self.training_page, self.processing_page, self.results_page]: self.stack.addWidget(page)
        action = QAction("Settings", self); action.setShortcut(QKeySequence.Preferences); action.triggered.connect(self._open_settings); self.menuBar().addAction(action)
        self._refresh_settings_summary(); self.stack.setCurrentWidget(self.project_page)

    def _page_container(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(32, 28, 32, 28); layout.setSpacing(18); return page, layout

    def _build_project_page(self) -> QWidget:
        page, layout = self._page_container()
        title = QLabel("Speaking Trainer"); title.setStyleSheet("font-size: 28px; font-weight: 700;"); layout.addWidget(title)
        subtitle = QLabel("Load an English TXT/MD file, generate speaking questions locally, then record your practice session."); subtitle.setWordWrap(True); layout.addWidget(subtitle)
        self.settings_summary = QLabel(); self.settings_summary.setWordWrap(True); self.settings_summary.setFrameShape(QFrame.Shape.StyledPanel); self.settings_summary.setStyleSheet("padding: 10px;"); layout.addWidget(self.settings_summary)
        file_row = QHBoxLayout(); self.file_label = QLabel("No file selected"); choose_file_btn = QPushButton("Choose TXT/MD file"); choose_file_btn.clicked.connect(self._choose_input_file); file_row.addWidget(self.file_label, 1); file_row.addWidget(choose_file_btn); layout.addLayout(file_row)
        layout.addWidget(QLabel("Number of questions")); q_row = QHBoxLayout(); self.q5_radio = QRadioButton("5"); self.q10_radio = QRadioButton("10"); self.q5_radio.setChecked(True); self.question_group = QButtonGroup(self); self.question_group.addButton(self.q5_radio); self.question_group.addButton(self.q10_radio); q_row.addWidget(self.q5_radio); q_row.addWidget(self.q10_radio); q_row.addStretch(1); layout.addLayout(q_row)
        quality_row = QHBoxLayout(); quality_row.addWidget(QLabel("Video quality")); self.quality_combo = QComboBox(); self.quality_combo.addItems(["720p", "240p"]); quality_row.addWidget(self.quality_combo); quality_row.addStretch(1); layout.addLayout(quality_row)
        idx = self.quality_combo.findText(self.settings.default_video_quality)
        if idx >= 0: self.quality_combo.setCurrentIndex(idx)
        action_row = QHBoxLayout(); settings_btn = QPushButton("Settings"); settings_btn.clicked.connect(self._open_settings); self.generate_btn = QPushButton("Generate Questions"); self.generate_btn.clicked.connect(self._generate_questions); action_row.addWidget(settings_btn); action_row.addStretch(1); action_row.addWidget(self.generate_btn); layout.addLayout(action_row); layout.addStretch(1); return page

    def _build_questions_page(self) -> QWidget:
        page, layout = self._page_container(); title = QLabel("Generated questions"); title.setStyleSheet("font-size: 24px; font-weight: 700;"); layout.addWidget(title)
        self.questions_text = QTextEdit(); self.questions_text.setReadOnly(True); layout.addWidget(self.questions_text, 1)
        row = QHBoxLayout(); back = QPushButton("Back"); back.clicked.connect(lambda: self.stack.setCurrentWidget(self.project_page)); start = QPushButton("Start"); start.clicked.connect(self._start_training); row.addWidget(back); row.addStretch(1); row.addWidget(start); layout.addLayout(row); return page

    def _build_training_page(self) -> QWidget:
        page, layout = self._page_container(); self.recording_label = QLabel("Recording ●"); self.recording_label.setStyleSheet("font-size: 16px; font-weight: 700;"); layout.addWidget(self.recording_label)
        self.training_counter_label = QLabel("Question 1 / 5"); self.training_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.training_counter_label.setStyleSheet("font-size: 18px;"); layout.addWidget(self.training_counter_label)
        self.training_question_label = QLabel(""); self.training_question_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.training_question_label.setWordWrap(True); self.training_question_label.setStyleSheet("font-size: 32px; font-weight: 700;"); layout.addWidget(self.training_question_label, 1)
        self.training_hint_label = QLabel("Press Space for next question"); self.training_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(self.training_hint_label); return page

    def _build_processing_page(self) -> QWidget:
        page, layout = self._page_container(); title = QLabel("Processing session"); title.setStyleSheet("font-size: 24px; font-weight: 700;"); layout.addWidget(title); self.processing_label = QLabel("Extracting audio and transcribing locally..."); self.processing_label.setWordWrap(True); layout.addWidget(self.processing_label); layout.addStretch(1); return page

    def _build_results_page(self) -> QWidget:
        page, layout = self._page_container(); title = QLabel("Session completed"); title.setStyleSheet("font-size: 24px; font-weight: 700;"); layout.addWidget(title)
        self.results_text = QTextEdit(); self.results_text.setReadOnly(True); layout.addWidget(self.results_text, 1)
        row = QHBoxLayout()
        for label, key in [("Open video", "video"), ("Open transcript", "transcript_txt"), ("Open questions", "questions"), ("Open session folder", "session_dir")]:
            btn = QPushButton(label); btn.clicked.connect(lambda _checked=False, k=key: self._open_path(self.last_outputs.get(k))); row.addWidget(btn)
        new_btn = QPushButton("New project"); new_btn.clicked.connect(self._reset_to_project); row.addStretch(1); row.addWidget(new_btn); layout.addLayout(row); return page

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if self.stack.currentWidget() == self.training_page and event.key() == Qt.Key.Key_Space:
            self._advance_training(); event.accept(); return
        super().keyPressEvent(event)

    def _choose_input_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose TXT/MD file", str(Path.home()), "Text files (*.txt *.md *.markdown)")
        if path: self.selected_file = Path(path); self.file_label.setText(path)

    def _question_count(self) -> int: return 10 if self.q10_radio.isChecked() else 5

    def _generate_questions(self) -> None:
        if self.selected_file is None:
            QMessageBox.warning(self, "No file", "Choose a .txt or .md file first."); return
        self.generate_btn.setEnabled(False); self.generate_btn.setText("Generating..."); count = self._question_count()
        def task() -> tuple[Project, str]:
            project_service = ProjectService(self.settings); project, source_text = project_service.create_project_from_file(self.selected_file, count); questions = QuestionGenerator(self.settings).generate(source_text, count); project_service.attach_questions(project, questions); return project, source_text
        worker = Worker(task); worker.signals.finished.connect(self._on_questions_generated); worker.signals.error.connect(self._on_task_error); self.thread_pool.start(worker)

    def _on_questions_generated(self, result: object) -> None:
        self.generate_btn.setEnabled(True); self.generate_btn.setText("Generate Questions"); project, source_text = result  # type: ignore[misc]
        self.current_project = project; self.current_source_text = source_text; self.questions_text.setPlainText("\n\n".join(f"{q.index}. {q.text}" for q in project.questions)); self.stack.setCurrentWidget(self.questions_page)

    def _start_training(self) -> None:
        if self.current_project is None: return
        self.session_service = SessionService(self.settings)
        try: session = self.session_service.start(self.current_project, self.quality_combo.currentText())
        except Exception as exc: QMessageBox.critical(self, "Recording failed", str(exc)); return
        self._render_current_question(session); self.stack.setCurrentWidget(self.training_page)

    def _render_current_question(self, session: TrainingSession | None = None) -> None:
        if not self.session_service: return
        sess = session or self.session_service.session
        if not sess: return
        q = self.session_service.current_question; self.training_counter_label.setText(f"Question {q.index} / {len(sess.questions)}"); self.training_question_label.setText(q.text); self.training_hint_label.setText("Press Space to finish" if q.index == len(sess.questions) else "Press Space for next question")

    def _advance_training(self) -> None:
        if not self.session_service: return
        try: advanced = self.session_service.advance_or_finish()
        except Exception as exc: QMessageBox.critical(self, "Session error", str(exc)); return
        if advanced: self._render_current_question()
        else: self._finish_training()

    def _finish_training(self) -> None:
        if not self.session_service or not self.current_project: return
        self.stack.setCurrentWidget(self.processing_page)
        def task() -> dict[str, Path]:
            assert self.session_service and self.current_project
            self.session_service.stop_recording(); return self.session_service.post_process(self.current_project)
        worker = Worker(task); worker.signals.finished.connect(self._on_processing_finished); worker.signals.error.connect(self._on_task_error); self.thread_pool.start(worker)

    def _on_processing_finished(self, result: object) -> None:
        self.last_outputs = result  # type: ignore[assignment]
        self.results_text.setPlainText("Created files:\n\n" + "\n".join(f"{k}: {v}" for k, v in self.last_outputs.items())); self.stack.setCurrentWidget(self.results_page)

    def _on_task_error(self, traceback_text: str) -> None:
        self.generate_btn.setEnabled(True); self.generate_btn.setText("Generate Questions")
        msg = QMessageBox(self); msg.setIcon(QMessageBox.Icon.Critical); msg.setWindowTitle("Error"); msg.setText("The operation failed."); msg.setDetailedText(traceback_text); msg.exec()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.settings_service, self.settings, self)
        if dialog.exec(): self.settings = self.settings_service.load(); self._refresh_settings_summary()

    def _refresh_settings_summary(self) -> None:
        missing = []
        if not self.settings.llm_model_path: missing.append("LLM model")
        if not self.settings.whisper_model_path: missing.append("Whisper model")
        warning = "\nMissing: " + ", ".join(missing) if missing else ""
        self.settings_summary.setText(f"Local mode. Models are external.\nFFmpeg: {self.settings.ffmpeg_path}\nllama-cli: {self.settings.llama_cli_path}\nwhisper-cli: {self.settings.whisper_cli_path}\nProjects: {self.settings.projects_dir}\nCamera index: {self.settings.camera_index}; Microphone index: {self.settings.microphone_index}{warning}")

    def _reset_to_project(self) -> None:
        self.current_project = None; self.current_source_text = ""; self.session_service = None; self.last_outputs = {}; self.selected_file = None; self.file_label.setText("No file selected"); self.stack.setCurrentWidget(self.project_page)

    @staticmethod
    def _open_path(path: Path | None) -> None:
        if path and Path(path).exists(): subprocess.run(["open", str(path)], check=False)
