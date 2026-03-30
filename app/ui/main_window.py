"""MainWindow — 사이드바 + 통합 대시보드 레이아웃."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.controller.workflow_controller import WorkflowController
from app.domain.models import BranchSummary, SyncResult
from app.ui.dashboard_panel import DashboardPanel
from app.ui.repo_manager_dialog import RepoManagerDialog
from app.ui.repo_sidebar import RepoSidebar


class MainWindow(QMainWindow):
    """메인 윈도우 — 좌측 저장소 사이드바 + 우측 통합 대시보드."""

    _REFRESH_INTERVAL_MS = 30_000

    def __init__(self, controller: WorkflowController) -> None:
        super().__init__()
        self._controller = controller
        self._setup_window()
        self._setup_toolbar()
        self._setup_central()
        self._setup_statusbar()
        self._connect_signals()
        self._start_auto_refresh()
        self._controller.refresh_branch_summary()

    # ── 초기 설정 ──────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setWindowTitle("Git Dashboard")
        self.setMinimumSize(960, 640)
        self.resize(1200, 760)

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFixedHeight(46)
        self.addToolBar(toolbar)

        # 앱 이름
        title = QLabel("  Git Dashboard")
        title.setStyleSheet(
            "color:#e2e8f0; font-size:15px; font-weight:700; letter-spacing:0.3px;"
        )
        toolbar.addWidget(title)

        # 구분 공백
        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().horizontalPolicy(),
            spacer.sizePolicy().verticalPolicy(),
        )
        from PyQt6.QtWidgets import QSizePolicy
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # 저장소 관리 버튼 (툴바 우측)
        self._manage_btn = QPushButton("⊞  저장소 관리")
        self._manage_btn.setFixedHeight(30)
        self._manage_btn.setStyleSheet(
            "QPushButton { background:#252540; color:#818cf8;"
            "border:1px solid #3d3d6b; border-radius:6px; font-size:12px;"
            "padding:4px 12px; min-width:0; }"
            "QPushButton:hover { background:#2d2d50; border-color:#6366f1; color:#a5b4fc; }"
        )
        self._manage_btn.clicked.connect(self._open_repo_manager)
        toolbar.addWidget(self._manage_btn)

        # 약간의 여백
        toolbar.addWidget(QLabel("  "))

    def _setup_central(self) -> None:
        # 좌우 분할
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background:#2d2d4a; }")

        # 좌측: 저장소 사이드바
        self._sidebar = RepoSidebar(self._controller)
        self._sidebar.repo_selected.connect(self._on_repo_selected)
        splitter.addWidget(self._sidebar)

        # 우측: 통합 대시보드
        self._dashboard = DashboardPanel(self._controller)
        splitter.addWidget(self._dashboard)

        splitter.setSizes([190, 1010])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

    def _setup_statusbar(self) -> None:
        self._status_label = QLabel("준비")
        self.statusBar().addWidget(self._status_label)
        self._busy_label = QLabel()
        self.statusBar().addPermanentWidget(self._busy_label)

    def _connect_signals(self) -> None:
        c = self._controller
        c.branch_summary_ready.connect(self._on_branch_summary)
        c.sync_finished.connect(self._on_sync_finished)
        c.error_occurred.connect(self._on_error)
        c.task_running.connect(self._on_task_running)

    def _start_auto_refresh(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._controller.refresh_branch_summary)
        self._timer.start(self._REFRESH_INTERVAL_MS)

    # ── 이벤트 핸들러 ──────────────────────────────────────────────────────

    def _open_repo_manager(self) -> None:
        dialog = RepoManagerDialog(self._controller, self)
        dialog.repos_changed.connect(self._sidebar.refresh)
        dialog.exec()

    def _on_repo_selected(self, path: str) -> None:
        self._controller.switch_repository(path)
        self._sidebar.refresh()

    def _on_branch_summary(self, summary: BranchSummary) -> None:
        # 사이드바 상태 아이콘 업데이트
        active = self._controller._config.get_active_repo()
        if active:
            self._sidebar.update_repo_status(active.path, summary.status)
        status = summary.status.value.upper()
        self._status_label.setText(
            f"⎇ {summary.current}  ·  {status}  ·  ↑{summary.ahead} ↓{summary.behind}"
        )

    def _on_sync_finished(self, result: SyncResult) -> None:
        if result.success:
            self._controller.refresh_branch_summary()

    def _on_error(self, message: str) -> None:
        self._status_label.setText(f"오류: {message}")

    def _on_task_running(self, running: bool) -> None:
        self._busy_label.setText("⟳ 처리 중..." if running else "")
