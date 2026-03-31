"""IdeBridgePanel — IntelliJ IDEA 연동 상태 / 설정 UI."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from app.infrastructure.ide_integration_service import IdeIntegrationService
    from app.infrastructure.file_watcher_service import FileWatcherService


_STYLE = """
QWidget { background-color: #1e1e1e; color: #d4d4d4; }
QGroupBox {
    border: 1px solid #3c3c3c; border-radius: 4px;
    margin-top: 8px; padding-top: 8px;
}
QGroupBox::title { color: #888; font-size: 11px; }
QPushButton {
    background: #3c3c3c; color: #d4d4d4;
    border: 1px solid #555; padding: 5px 14px;
    border-radius: 3px;
}
QPushButton:hover { background: #4a4a4a; }
QPushButton:disabled { background: #2a2a2a; color: #555; border-color: #333; }
"""

_BTN_PRIMARY = (
    "QPushButton { background: #2980b9; color: #fff; border: none; "
    "padding: 5px 14px; border-radius: 3px; }"
    "QPushButton:hover { background: #3498db; }"
    "QPushButton:disabled { background: #2a2a2a; color: #555; }"
)


class _StatusBadge(QLabel):
    """연결 상태 배지."""

    def set_ok(self, text: str) -> None:
        self.setText(f"✅  {text}")
        self.setStyleSheet("color: #2ecc71; font-weight: bold;")

    def set_warn(self, text: str) -> None:
        self.setText(f"⚠️  {text}")
        self.setStyleSheet("color: #f0b429; font-weight: bold;")

    def set_error(self, text: str) -> None:
        self.setText(f"❌  {text}")
        self.setStyleSheet("color: #e74c3c; font-weight: bold;")

    def set_info(self, text: str) -> None:
        self.setText(f"ℹ️  {text}")
        self.setStyleSheet("color: #4a9eff;")


class IdeBridgePanel(QWidget):
    """IntelliJ IDEA 연동 상태 표시 및 제어 패널.

    기능:
    - IDE 감지 상태 표시 (경로, 이름, 버전)
    - 현재 저장소 IDE에서 열기
    - FileWatcherService 시작/중지 토글
    - Git Hook 설치

    사용법:
        panel = IdeBridgePanel(ide_service, file_watcher, repo_path, parent)
        panel.set_repo_path(path)
    """

    open_in_ide_requested = pyqtSignal(str)      # file_path
    hooks_installed = pyqtSignal(str)             # repo_path

    def __init__(
        self,
        ide_service: "IdeIntegrationService",
        file_watcher: "FileWatcherService | None" = None,
        repo_path: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._ide = ide_service
        self._watcher = file_watcher
        self._repo_path = repo_path
        self._setup_ui()
        self.refresh()

        # 30초마다 IDE 상태 자동 갱신
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(30_000)

    # ─── UI 구성 ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setStyleSheet(_STYLE)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── IDE 연결 상태 ──
        ide_group = QGroupBox("IDE 연결 상태")
        ide_layout = QVBoxLayout(ide_group)

        self._ide_status = _StatusBadge()
        self._ide_status.setFont(QFont("Menlo", 12))
        ide_layout.addWidget(self._ide_status)

        self._ide_detail = QLabel()
        self._ide_detail.setStyleSheet("color: #888; font-size: 11px;")
        self._ide_detail.setWordWrap(True)
        ide_layout.addWidget(self._ide_detail)

        # IDE에서 열기 버튼
        open_row = QHBoxLayout()
        self._open_btn = QPushButton("IDE에서 프로젝트 열기")
        self._open_btn.setStyleSheet(_BTN_PRIMARY)
        self._open_btn.clicked.connect(self._on_open_project)
        open_row.addWidget(self._open_btn)
        open_row.addStretch()
        ide_layout.addLayout(open_row)
        layout.addWidget(ide_group)

        # ── File Watcher 상태 ──
        watcher_group = QGroupBox("File Watcher (Git 이벤트 감시)")
        watcher_layout = QVBoxLayout(watcher_group)

        self._watcher_status = _StatusBadge()
        self._watcher_status.setFont(QFont("Menlo", 12))
        watcher_layout.addWidget(self._watcher_status)

        watcher_btn_row = QHBoxLayout()
        self._watcher_toggle_btn = QPushButton("감시 시작")
        self._watcher_toggle_btn.clicked.connect(self._on_toggle_watcher)
        watcher_btn_row.addWidget(self._watcher_toggle_btn)
        watcher_btn_row.addStretch()
        watcher_layout.addLayout(watcher_btn_row)
        layout.addWidget(watcher_group)

        # ── Git Hook 설치 ──
        hook_group = QGroupBox("Git Hook 통합")
        hook_layout = QVBoxLayout(hook_group)

        hook_desc = QLabel(
            "post-commit / post-push hook을 설치하면\n"
            "커밋/푸시 이벤트를 Dashboard에서 즉시 감지합니다."
        )
        hook_desc.setStyleSheet("color: #888; font-size: 11px;")
        hook_layout.addWidget(hook_desc)

        hook_btn_row = QHBoxLayout()
        self._hook_btn = QPushButton("Git Hook 설치")
        self._hook_btn.setStyleSheet(_BTN_PRIMARY)
        self._hook_btn.clicked.connect(self._on_install_hooks)
        hook_btn_row.addWidget(self._hook_btn)
        hook_btn_row.addStretch()
        hook_layout.addLayout(hook_btn_row)
        layout.addWidget(hook_group)

        layout.addStretch()

    # ─── 공개 API ────────────────────────────────────────────────────────────

    def set_repo_path(self, path: str) -> None:
        """현재 저장소 경로 설정."""
        self._repo_path = path
        self._open_btn.setEnabled(self._ide.is_available() and bool(path))
        self._hook_btn.setEnabled(bool(path))

    def refresh(self) -> None:
        """IDE 및 File Watcher 상태 갱신."""
        self._refresh_ide_status()
        self._refresh_watcher_status()

    # ─── 내부 상태 갱신 ─────────────────────────────────────────────────────

    def _refresh_ide_status(self) -> None:
        info = self._ide.get_ide_info()
        if info.get("available"):
            name = info.get("name", "IDE")
            version = info.get("version") or ""
            path = info.get("path", "")
            self._ide_status.set_ok(f"{name} {version}".strip())
            self._ide_detail.setText(f"경로: {path}")
            self._open_btn.setEnabled(bool(self._repo_path))
        else:
            self._ide_status.set_error("IDE를 찾을 수 없음")
            self._ide_detail.setText(
                "IntelliJ IDEA 또는 JetBrains Toolbox를 설치하면 자동으로 감지됩니다."
            )
            self._open_btn.setEnabled(False)

    def _refresh_watcher_status(self) -> None:
        if self._watcher is None:
            self._watcher_status.set_warn("FileWatcherService 미연결")
            self._watcher_toggle_btn.setEnabled(False)
            return

        watched = self._watcher.watched_paths()
        if watched:
            self._watcher_status.set_ok(f"감시 중 ({len(watched)}개 경로)")
            self._watcher_toggle_btn.setText("감시 중지")
        else:
            self._watcher_status.set_warn("감시 중지됨")
            self._watcher_toggle_btn.setText("감시 시작")

    # ─── 이벤트 ─────────────────────────────────────────────────────────────

    def _on_open_project(self) -> None:
        if not self._repo_path:
            return
        ok = self._ide.open_project(self._repo_path)
        if not ok:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "열기 실패", "IDE에서 프로젝트를 열 수 없습니다.")
        else:
            self.open_in_ide_requested.emit(self._repo_path)

    def _on_toggle_watcher(self) -> None:
        if self._watcher is None:
            return
        if self._watcher.watched_paths():
            self._watcher.stop_watching()
        else:
            self._watcher.start_watching()
        self._refresh_watcher_status()

    def _on_install_hooks(self) -> None:
        if not self._repo_path:
            return
        ok = self._ide.setup_git_hooks(self._repo_path)
        from PyQt6.QtWidgets import QMessageBox
        if ok:
            QMessageBox.information(
                self,
                "설치 완료",
                f"Git Hook이 설치되었습니다.\n{self._repo_path}/.git/hooks/",
            )
            self.hooks_installed.emit(self._repo_path)
        else:
            QMessageBox.critical(self, "설치 실패", "Git Hook 설치에 실패했습니다.")
