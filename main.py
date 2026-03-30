"""Git Dashboard — 애플리케이션 진입점."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from app.controller.workflow_controller import WorkflowController
from app.infrastructure.config_store import ConfigStore
from app.ui.main_window import MainWindow
from app.ui.menu_bar_app import MenuBarApp


def _resource_base() -> Path:
    """PyInstaller 번들 환경과 개발 환경 모두에서 리소스 루트 경로 반환."""
    if getattr(sys, "frozen", False):
        # PyInstaller .app 번들 내부: _MEIPASS 기준
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent


def _load_stylesheet() -> str:
    qss_path = _resource_base() / "resources" / "styles" / "dark_theme.qss"
    if qss_path.exists():
        return qss_path.read_text(encoding="utf-8")
    return ""


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Git Dashboard")
    app.setOrganizationName("jypark")

    # 윈도우 닫아도 트레이에 상주
    app.setQuitOnLastWindowClosed(False)

    # 다크 테마 적용
    stylesheet = _load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    config = ConfigStore()
    controller = WorkflowController(config)
    window = MainWindow(controller)

    # 메뉴바 트레이 초기화 (시스템 트레이 지원 시)
    tray_app = MenuBarApp(controller, window)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
