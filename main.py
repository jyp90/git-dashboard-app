"""Git Dashboard — 애플리케이션 진입점."""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from app.controller.workflow_controller import WorkflowController
from app.infrastructure.config_store import ConfigStore
from app.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Git Dashboard")
    app.setOrganizationName("jypark")

    config = ConfigStore()
    controller = WorkflowController(config)
    window = MainWindow(controller)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
