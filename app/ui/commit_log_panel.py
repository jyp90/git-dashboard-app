"""CommitLogPanel — F-03 최근 커밋 로그 뷰어."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.controller.workflow_controller import WorkflowController
from app.domain.models import Commit


class CommitLogPanel(QWidget):
    """커밋 로그를 테이블로 표시 (hash, 메시지, 작성자, 날짜)."""

    def __init__(self, controller: WorkflowController, parent=None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # 툴바
        bar = QHBoxLayout()
        self._refresh_btn = QPushButton("↻ 새로고침")
        self._refresh_btn.clicked.connect(self._load_commits)
        bar.addWidget(self._refresh_btn)
        bar.addStretch()
        self._count_label = QLabel("")
        bar.addWidget(self._count_label)
        layout.addLayout(bar)

        # 커밋 테이블
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Hash", "메시지", "작성자", "날짜"])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table, stretch=1)

    def _connect_signals(self) -> None:
        # branch_summary_ready 시 커밋도 갱신
        self._controller.branch_summary_ready.connect(lambda _: self._load_commits())

    def _load_commits(self) -> None:
        if not self._controller.has_repository():
            return
        from app.controller.git_worker import GitWorker
        worker = GitWorker(lambda: self._controller.get_commit_log(limit=20))
        worker.result_ready.connect(self._show_commits)
        worker.start()
        # worker 참조 유지 (GC 방지)
        self._worker = worker

    def _show_commits(self, commits: list[Commit]) -> None:
        self._table.setRowCount(0)
        for row, c in enumerate(commits):
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(c.short_hash))
            self._table.setItem(row, 1, QTableWidgetItem(c.summary))
            self._table.setItem(row, 2, QTableWidgetItem(c.author))
            self._table.setItem(row, 3, QTableWidgetItem(c.date.strftime("%Y-%m-%d %H:%M")))
        self._count_label.setText(f"{len(commits)}개 커밋")
