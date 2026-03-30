"""BranchPanel — F-01 브랜치 상태 + F-02 원클릭 동기화 + F-04 브랜치 목록."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.controller.workflow_controller import WorkflowController
from app.domain.models import BranchStatus, BranchSummary, SyncResult


class _StatusBadge(QLabel):
    _COLOR_MAP = {
        BranchStatus.CLEAN: ("#27ae60", "CLEAN"),
        BranchStatus.DIRTY: ("#e67e22", "DIRTY"),
        BranchStatus.AHEAD: ("#2980b9", "AHEAD"),
        BranchStatus.BEHIND: ("#c0392b", "BEHIND"),
        BranchStatus.DIVERGED: ("#8e44ad", "DIVERGED"),
    }

    def set_status(self, status: BranchStatus) -> None:
        color, text = self._COLOR_MAP.get(status, ("#7f8c8d", "UNKNOWN"))
        self.setText(f"  {text}  ")
        self.setStyleSheet(
            f"background:{color}; color:white; border-radius:4px; padding:2px 6px; font-weight:bold;"
        )


class BranchPanel(QWidget):
    """브랜치 상태 표시 + 동기화 버튼 + 브랜치 목록."""

    def __init__(self, controller: WorkflowController, parent=None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── 상태 헤더 카드 ─────────────────────────────────────────────
        header = QFrame()
        header.setFrameShape(QFrame.Shape.StyledPanel)
        header.setMinimumHeight(64)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        # 브랜치 아이콘 + 이름
        branch_icon = QLabel("⎇")
        branch_icon.setStyleSheet("font-size:20px; color:#818cf8; margin-right:4px;")
        header_layout.addWidget(branch_icon)

        self._branch_label = QLabel("—")
        self._branch_label.setStyleSheet(
            "font-size:17px; font-weight:700; color:#e2e8f0; font-family:'SF Mono','Menlo',monospace;"
        )
        header_layout.addWidget(self._branch_label)

        self._status_badge = _StatusBadge()
        self._status_badge.setText("  —  ")
        header_layout.addWidget(self._status_badge)

        header_layout.addStretch()

        # ahead/behind 카운터
        counter_widget = QWidget()
        counter_widget.setStyleSheet(
            "background:#252540; border-radius:6px; padding:4px 10px;"
        )
        counter_layout = QHBoxLayout(counter_widget)
        counter_layout.setContentsMargins(8, 4, 8, 4)
        counter_layout.setSpacing(12)
        self._ahead_label = QLabel("↑ —")
        self._ahead_label.setStyleSheet("color:#10b981; font-weight:600; font-size:13px;")
        self._behind_label = QLabel("↓ —")
        self._behind_label.setStyleSheet("color:#f59e0b; font-weight:600; font-size:13px;")
        counter_layout.addWidget(self._ahead_label)
        counter_layout.addWidget(self._behind_label)
        header_layout.addWidget(counter_widget)

        layout.addWidget(header)

        # ── 액션 버튼 ──────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self._sync_btn = QPushButton("↻  Sync Develop")
        self._sync_btn.setToolTip("origin/develop을 fetch 후 develop 브랜치를 업데이트합니다")
        self._sync_btn.setFixedHeight(36)
        self._sync_btn.clicked.connect(self._on_sync_clicked)
        btn_layout.addWidget(self._sync_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ── 브랜치 목록 ────────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        local_group = QGroupBox("LOCAL BRANCHES")
        local_layout = QVBoxLayout(local_group)
        self._local_list = QListWidget()
        local_layout.addWidget(self._local_list)
        splitter.addWidget(local_group)

        remote_group = QGroupBox("REMOTE BRANCHES")
        remote_layout = QVBoxLayout(remote_group)
        self._remote_list = QListWidget()
        remote_layout.addWidget(self._remote_list)
        splitter.addWidget(remote_group)

        layout.addWidget(splitter, stretch=1)

        # ── 결과 메시지 ────────────────────────────────────────────────
        self._msg_label = QLabel("")
        self._msg_label.setStyleSheet("color: #27ae60;")
        layout.addWidget(self._msg_label)

    def _connect_signals(self) -> None:
        c = self._controller
        c.branch_summary_ready.connect(self._update_summary)
        c.sync_finished.connect(self._on_sync_result)
        c.task_running.connect(self._on_task_running)

    # ── 슬롯 ──────────────────────────────────────────────────────────────

    def _on_sync_clicked(self) -> None:
        self._msg_label.setText("")
        self._controller.sync_develop()

    def _update_summary(self, summary: BranchSummary) -> None:
        self._branch_label.setText(summary.current)
        self._status_badge.set_status(summary.status)
        dirty_icon = " ✦" if summary.is_dirty else ""
        self._ahead_label.setText(f"↑ {summary.ahead}{dirty_icon}")
        self._behind_label.setText(f"↓ {summary.behind}")

        self._local_list.clear()
        for b in summary.local_branches:
            item = QListWidgetItem(b)
            if b == summary.current:
                item.setText(f"* {b}")
                item.setForeground(Qt.GlobalColor.green)
            self._local_list.addItem(item)

        self._remote_list.clear()
        for b in summary.remote_branches:
            self._remote_list.addItem(b)

    def _on_sync_result(self, result: SyncResult) -> None:
        color = "#27ae60" if result.success else "#e74c3c"
        self._msg_label.setStyleSheet(f"color: {color};")
        self._msg_label.setText(result.message)

    def _on_task_running(self, running: bool) -> None:
        self._sync_btn.setEnabled(not running)
        self._sync_btn.setText("처리 중..." if running else "⟳ Sync Develop")
