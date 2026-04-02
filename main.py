"""Git Dashboard — 애플리케이션 진입점."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from app.controller.workflow_controller import WorkflowController
from app.infrastructure.config_store import ConfigStore
from app.ui.main_window import MainWindow
from app.ui.menu_bar_app import MenuBarApp

_INSTANCE_KEY = "GitDashboard-SingleInstance"


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


def _is_already_running() -> bool:
    """이미 실행 중인 인스턴스에 신호를 보내고 True 반환."""
    socket = QLocalSocket()
    socket.connectToServer(_INSTANCE_KEY)
    if socket.waitForConnected(300):
        socket.write(b"raise")
        socket.flush()
        socket.disconnectFromServer()
        return True
    return False


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Git Dashboard")
    app.setOrganizationName("jypark")

    # 중복 실행 방지
    if _is_already_running():
        sys.exit(0)

    # 단일 인스턴스 서버 등록
    server = QLocalServer()
    QLocalServer.removeServer(_INSTANCE_KEY)  # 이전 비정상 종료 잔여 소켓 정리
    server.listen(_INSTANCE_KEY)

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

    def _on_new_connection() -> None:
        """두 번째 실행 시도 → 기존 창 앞으로."""
        conn = server.nextPendingConnection()
        if conn:
            conn.close()
        window.show()
        window.raise_()
        window.activateWindow()

    server.newConnection.connect(_on_new_connection)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
