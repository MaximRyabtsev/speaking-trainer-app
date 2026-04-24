from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from speaking_trainer.config.paths import ensure_app_dirs
from speaking_trainer.config.settings import SettingsService
from speaking_trainer.ui.main_window import MainWindow


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("Speaking Trainer")
    app.setOrganizationName("Local")
    ensure_app_dirs()
    settings_service = SettingsService()
    window = MainWindow(settings_service, settings_service.load())
    window.resize(920, 640)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
