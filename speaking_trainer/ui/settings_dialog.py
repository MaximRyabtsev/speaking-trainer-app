from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QCheckBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QPlainTextEdit, QSpinBox, QVBoxLayout, QWidget

from speaking_trainer.config.settings import AppSettings, SettingsService
from speaking_trainer.services.video_recorder import VideoRecorder
from speaking_trainer.ui.workers import Worker


class SettingsDialog(QDialog):
    def __init__(self, settings_service: SettingsService, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.settings_service = settings_service
        self.settings = settings
        self.thread_pool = QThreadPool.globalInstance()
        self.ffmpeg_edit = self._path_edit(settings.ffmpeg_path)
        self.llama_edit = self._path_edit(settings.llama_cli_path)
        self.whisper_cli_edit = self._path_edit(settings.whisper_cli_path)
        self.llm_model_edit = self._path_edit(settings.llm_model_path)
        self.whisper_model_edit = self._path_edit(settings.whisper_model_path)
        self.projects_dir_edit = self._path_edit(settings.projects_dir)
        self.camera_index_edit = QLineEdit(settings.camera_index)
        self.microphone_index_edit = QLineEdit(settings.microphone_index)
        self.context_spin = QSpinBox(); self.context_spin.setRange(1024, 32768); self.context_spin.setSingleStep(512); self.context_spin.setValue(settings.llm_context_size)
        self.max_chars_spin = QSpinBox(); self.max_chars_spin.setRange(1000, 100000); self.max_chars_spin.setSingleStep(1000); self.max_chars_spin.setValue(settings.llm_max_chars)
        self.cleanup_check = QCheckBox("Delete temporary extracted audio after transcription"); self.cleanup_check.setChecked(settings.cleanup_temp_audio)
        form = QFormLayout()
        self._add_file_row(form, "FFmpeg", self.ffmpeg_edit)
        self._add_file_row(form, "llama-cli", self.llama_edit)
        self._add_file_row(form, "whisper-cli", self.whisper_cli_edit)
        self._add_file_row(form, "LLM model .gguf", self.llm_model_edit)
        self._add_file_row(form, "Whisper model", self.whisper_model_edit)
        self._add_dir_row(form, "Projects directory", self.projects_dir_edit)
        form.addRow("Camera index", self.camera_index_edit)
        form.addRow("Microphone index", self.microphone_index_edit)
        form.addRow("LLM context size", self.context_spin)
        form.addRow("Max source chars for LLM", self.max_chars_spin)
        form.addRow("", self.cleanup_check)
        self.devices_output = QPlainTextEdit(); self.devices_output.setReadOnly(True); self.devices_output.setMinimumHeight(160)
        list_devices_btn = QPushButton("List AVFoundation devices"); list_devices_btn.clicked.connect(self._list_devices)
        save_btn = QPushButton("Save"); save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        buttons = QHBoxLayout(); buttons.addStretch(1); buttons.addWidget(cancel_btn); buttons.addWidget(save_btn)
        layout = QVBoxLayout(self)
        intro = QLabel("Select local tools and external model files. After this the app can work offline."); intro.setWordWrap(True)
        layout.addWidget(intro); layout.addLayout(form); layout.addWidget(list_devices_btn); layout.addWidget(self.devices_output); layout.addLayout(buttons)
        self.resize(760, 680)

    @staticmethod
    def _path_edit(value: str) -> QLineEdit:
        edit = QLineEdit(value); edit.setMinimumWidth(460); return edit

    def _add_file_row(self, form: QFormLayout, label: str, edit: QLineEdit) -> None:
        browse = QPushButton("Browse"); browse.clicked.connect(lambda: self._browse_file(edit))
        row = QHBoxLayout(); row.addWidget(edit); row.addWidget(browse); form.addRow(label, row)

    def _add_dir_row(self, form: QFormLayout, label: str, edit: QLineEdit) -> None:
        browse = QPushButton("Browse"); browse.clicked.connect(lambda: self._browse_dir(edit))
        row = QHBoxLayout(); row.addWidget(edit); row.addWidget(browse); form.addRow(label, row)

    def _browse_file(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select file", str(Path.home()))
        if path: edit.setText(path)

    def _browse_dir(self, edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select directory", str(Path.home()))
        if path: edit.setText(path)

    def _collect(self) -> AppSettings:
        return replace(self.settings, ffmpeg_path=self.ffmpeg_edit.text().strip(), llama_cli_path=self.llama_edit.text().strip(), whisper_cli_path=self.whisper_cli_edit.text().strip(), llm_model_path=self.llm_model_edit.text().strip(), whisper_model_path=self.whisper_model_edit.text().strip(), projects_dir=self.projects_dir_edit.text().strip(), camera_index=self.camera_index_edit.text().strip() or "0", microphone_index=self.microphone_index_edit.text().strip() or "0", llm_context_size=int(self.context_spin.value()), llm_max_chars=int(self.max_chars_spin.value()), cleanup_temp_audio=self.cleanup_check.isChecked())

    def _save(self) -> None:
        self.settings_service.save(self._collect())
        self.accept()

    def _list_devices(self) -> None:
        self.devices_output.setPlainText("Listing devices...")
        settings = self._collect()
        worker = Worker(lambda: VideoRecorder(settings).list_devices())
        worker.signals.finished.connect(lambda result: self.devices_output.setPlainText(str(result)))
        worker.signals.error.connect(lambda err: self.devices_output.setPlainText(err))
        self.thread_pool.start(worker)
