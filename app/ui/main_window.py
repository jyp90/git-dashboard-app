"""MainWindow — 탭 기반 메인 윈도우."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.controller.workflow_controller import WorkflowController
from app.domain.models import BranchSummary, SyncResult
from app.ui.branch_panel import BranchPanel
from app.ui.commit_log_panel import CommitLogPanel


class MainWindow(QMainWindow):
    """애플리케이션 메인 윈도우.

    WorkflowController와 연결되어 UI 이벤트를 컨트롤러로 전달하고
    컨트롤러 시그널을 받아 UI를 업데이트한다.
    """

    _REFRESH_INTERVAL_MS = 30_000  # 30초마다 자동 갱신

    def __init__(self, controller: WorkflowController) -> None:
        super().__init__()
        self._controller = controller
        self._setup_window()
        self._setup_toolbar()
        self._setup_tabs()
        self._setup_statusbar()
        self._connect_signals()
        self._start_auto_refresh()
        # 초기 데이터 로드
        self._controller.refresh_branch_summary()

    # ── 초기 설정 ──────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setWindowTitle("Git Dashboard")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("메인 툴바")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 저장소 선택 콤보박스
        toolbar.addWidget(QLabel("저장소: "))
        self._repo_combo = QComboBox()
        self._repo_combo.setMinimumWidth(200)
        self._repo_combo.currentIndexChanged.connect(self._on_repo_changed)
        toolbar.addWidget(self._repo_combo)
        self._refresh_repo_list()

    def _setup_tabs(self) -> None:
        self._tabs = QTabWidget()
        self._branch_panel = BranchPanel(self._controller)
        self._commit_panel = CommitLogPanel(self._controller)

        self._tabs.addTab(self._branch_panel, "브랜치")
        self._tabs.addTab(self._commit_panel, "커밋 로그")
        # Phase 2에서 추가될 탭들 (플레이스홀더)
        self._tabs.addTab(QWidget(), "PR 체크")
        self._tabs.addTab(QWidget(), "워크플로우")

        self.setCentralWidget(self._tabs)

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

    def _refresh_repo_list(self) -> None:
        self._repo_combo.blockSignals(True)
        self._repo_combo.clear()
        for repo in self._controller._config.get_repositories():
            self._repo_combo.addItem(repo.name, userData=repo.path)
            if repo.is_active:
                self._repo_combo.setCurrentText(repo.name)
        self._repo_combo.blockSignals(False)

    def _on_repo_changed(self, index: int) -> None:
        if index < 0:
            return
        path = self._repo_combo.currentData()
        if path:
            self._controller.switch_repository(path)

    def _on_branch_summary(self, summary: BranchSummary) -> None:
        status = summary.status.value.upper()
        self._status_label.setText(f"{summary.current}  [{status}]  ↑{summary.ahead} ↓{summary.behind}")

    def _on_sync_finished(self, result: SyncResult) -> None:
        self._status_label.setText(result.message)
        if result.success:
            self._controller.refresh_branch_summary()

    def _on_error(self, message: str) -> None:
        self._status_label.setText(f"오류: {message}")

    def _on_task_running(self, running: bool) -> None:
        self._busy_label.setText("처리 중..." if running else "")
