"""Git Dashboard — 애플리케이션 진입점."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from app.controller.workflow_controller import WorkflowController
from app.infrastructure.config_store import ConfigStore
from app.ui.main_window import MainWindow


def _load_stylesheet() -> str:
    qss_path = Path(__file__).parent / "resources" / "styles" / "dark_theme.qss"
    if qss_path.exists():
        return qss_path.read_text(encoding="utf-8")
    return ""


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Git Dashboard")
    app.setOrganizationName("jypark")

    # 다크 테마 적용
    stylesheet = _load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    config = ConfigStore()
    controller = WorkflowController(config)
    window = MainWindow(controller)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
