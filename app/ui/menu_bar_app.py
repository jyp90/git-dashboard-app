"""MenuBarApp — F-08 macOS 메뉴바 상주 (QSystemTrayIcon 기반)."""
from __future__ import annotations

import os
from PyQt6.QtCore import QTimer, QRectF, QPointF, Qt
from PyQt6.QtGui import (
    QIcon, QPixmap, QColor, QPainter, QPen, QBrush, QPainterPath
)
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from app.controller.workflow_controller import WorkflowController
from app.domain.models import BranchStatus

_ICON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "resources", "icons", "menu_icon.png",
)


def _make_tray_icon(status_color: str | None = None) -> QIcon:
    """Git 브랜치 아이콘 생성.

    status_color가 주어지면 base 이미지 위에 상태 표시 뱃지를 그림.
    """
    SIZE = 28

    # base: PNG 파일 사용, 없으면 fallback
    if os.path.isfile(_ICON_PATH):
        base = QPixmap(_ICON_PATH).scaled(
            SIZE, SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    else:
        base = QPixmap(SIZE, SIZE)
        base.fill(QColor(0, 0, 0, 0))

    if not status_color:
        return QIcon(base)

    # 상태 뱃지 오버레이 (우하단 5px 원)
    result = base.copy()
    p = QPainter(result)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r = 4
    x, y = SIZE - r - 1, SIZE - r - 1
    p.setPen(QPen(QColor("#0f0f1a"), 1.2))
    p.setBrush(QBrush(QColor(status_color)))
    p.drawEllipse(QPointF(x, y), r, r)
    p.end()
    return QIcon(result)


_STATUS_COLORS = {
    BranchStatus.CLEAN:    "#22c55e",
    BranchStatus.DIRTY:    "#f59e0b",
    BranchStatus.AHEAD:    "#60a5fa",
    BranchStatus.BEHIND:   "#f87171",
    BranchStatus.DIVERGED: "#c084fc",
}


class MenuBarApp:
    """macOS 메뉴바 상주 아이콘 (QSystemTrayIcon 기반).

    MainWindow와 독립적으로 트레이에서 기본 상태 표시 및 액션 제공.
    """

    def __init__(self, controller: WorkflowController, main_window) -> None:
        self._controller = controller
        self._main_window = main_window
        self._tray: QSystemTrayIcon | None = None
        self._current_branch = "—"
        self._current_status: BranchStatus | None = None

        if QSystemTrayIcon.isSystemTrayAvailable():
            self._setup_tray()
            self._connect_signals()

    def _setup_tray(self) -> None:
        self._tray = QSystemTrayIcon(_make_tray_icon(None))
        self._tray.setToolTip("Git Dashboard")
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.setContextMenu(self._build_menu())
        self._tray.show()

    def _build_menu(self) -> QMenu:
        menu = QMenu()

        self._status_action = menu.addAction("⎇  —")
        self._status_action.setEnabled(False)
        menu.addSeparator()

        sync_action = menu.addAction("↻  Sync Develop")
        sync_action.triggered.connect(self._controller.sync_develop)

        pr_action = menu.addAction("🔍  PR Check")
        pr_action.triggered.connect(self._controller.run_pr_check)

        menu.addSeparator()

        show_action = menu.addAction("대시보드 열기")
        show_action.triggered.connect(self._show_window)

        menu.addSeparator()

        quit_action = menu.addAction("종료")
        quit_action.triggered.connect(QApplication.quit)

        return menu

    def _connect_signals(self) -> None:
        self._controller.branch_summary_ready.connect(self._on_summary)
        self._controller.sync_finished.connect(self._on_sync_finished)

    def _on_summary(self, summary) -> None:
        prev_status = self._current_status
        self._current_branch = summary.current
        self._current_status = summary.status

        color = _STATUS_COLORS.get(summary.status)
        if self._tray:
            self._tray.setIcon(_make_tray_icon(color))
            self._tray.setToolTip(
                f"Git Dashboard  ⎇ {summary.current}  {summary.status.value.upper()}"
            )
        if self._status_action:
            status_text = summary.status.value.upper()
            self._status_action.setText(
                f"⎇  {summary.current}   ·   {status_text}   ↑{summary.ahead} ↓{summary.behind}"
            )

        # F-11: 상태 변경 시 알림 (최초 로드 제외)
        if prev_status is not None and self._tray and prev_status != summary.status:
            self._notify_status_change(summary)

    def _notify_status_change(self, summary) -> None:
        """F-11 — 브랜치 상태 변경 시 macOS 알림."""
        if not self._tray:
            return
        if summary.status == BranchStatus.BEHIND:
            self._tray.showMessage(
                "Git Dashboard",
                f"⬇  {summary.current}: {summary.behind}개 커밋 뒤처짐",
                QSystemTrayIcon.MessageIcon.Warning,
                4000,
            )
        elif summary.status == BranchStatus.DIVERGED:
            self._tray.showMessage(
                "Git Dashboard",
                f"⚡  {summary.current}: 브랜치 충돌 위험 — Sync 필요",
                QSystemTrayIcon.MessageIcon.Critical,
                5000,
            )

    def _on_sync_finished(self, result) -> None:
        """F-11 — 동기화 완료 알림."""
        if not self._tray:
            return
        if result.success and result.commits_pulled > 0:
            self._tray.showMessage(
                "Git Dashboard",
                f"✅  동기화 완료 ({result.commits_pulled}개 커밋)",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _show_window(self) -> None:
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def hide_to_tray(self) -> None:
        """메인 윈도우를 숨기고 트레이에만 상주."""
        if self._tray:
            self._main_window.hide()
            self._tray.showMessage(
                "Git Dashboard",
                "트레이에서 계속 실행 중입니다.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
