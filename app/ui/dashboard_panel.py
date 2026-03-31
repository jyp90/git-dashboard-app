"""DashboardPanel — 브랜치 상태 + 액션 + 커밋 로그를 하나로 통합한 대시보드."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.controller.workflow_controller import WorkflowController
from app.domain.models import BranchResult, BranchStatus, BranchSummary, Commit, PrCheckReport, SyncResult


class _Badge(QLabel):
    """상태 배지 레이블."""
    _COLORS = {
        BranchStatus.CLEAN:    ("#166534", "#4ade80", "CLEAN"),
        BranchStatus.DIRTY:    ("#78350f", "#fbbf24", "DIRTY"),
        BranchStatus.AHEAD:    ("#1e3a5f", "#60a5fa", "AHEAD"),
        BranchStatus.BEHIND:   ("#7f1d1d", "#f87171", "BEHIND"),
        BranchStatus.DIVERGED: ("#4c1d95", "#c084fc", "DIVERG"),
    }

    def set_status(self, status: BranchStatus) -> None:
        bg, fg, text = self._COLORS.get(status, ("#1e293b", "#94a3b8", "UNKNOWN"))
        self.setText(f" {text} ")
        self.setStyleSheet(
            f"background:{bg}; color:{fg}; border:1px solid {fg}40;"
            "border-radius:4px; padding:2px 8px; font-size:11px; font-weight:700; letter-spacing:0.5px;"
        )


class _SectionHeader(QLabel):
    """섹션 구분 헤더."""
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet(
            "color:#475569; font-size:10px; font-weight:700; letter-spacing:1.2px;"
            "padding:16px 0 6px 0; border-bottom:1px solid #1e1e38;"
        )


class _ActionButton(QPushButton):
    """대시보드 액션 버튼."""
    _STYLES = {
        "primary":  ("background:#4f46e5; color:white; border:none;",
                     "background:#4338ca; color:white; border:none;"),
        "success":  ("background:#166534; color:#4ade80; border:1px solid #15803d;",
                     "background:#14532d; color:#4ade80; border:1px solid #15803d;"),
        "warning":  ("background:#78350f; color:#fbbf24; border:1px solid #92400e;",
                     "background:#6b2d0a; color:#fbbf24; border:1px solid #92400e;"),
        "danger":   ("background:#7f1d1d; color:#f87171; border:1px solid #991b1b;",
                     "background:#6b1111; color:#f87171; border:1px solid #991b1b;"),
    }

    def __init__(self, text: str, variant: str = "primary", parent=None) -> None:
        super().__init__(text, parent)
        normal, hover = self._STYLES.get(variant, self._STYLES["primary"])
        self.setStyleSheet(
            f"QPushButton {{ {normal} border-radius:7px; padding:8px 16px;"
            f"font-size:13px; font-weight:500; min-width:0; }}"
            f"QPushButton:hover {{ {hover} }}"
            f"QPushButton:disabled {{ background:#1e1e38; color:#475569; border:none; }}"
        )
        self.setFixedHeight(36)


class DashboardPanel(QWidget):
    """통합 대시보드: 브랜치 상태 카드 + 빠른 액션 + 커밋 로그 + 브랜치 목록."""

    def __init__(self, controller: WorkflowController, parent=None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._setup_ui()
        self._connect_signals()

    # ── UI 구성 ───────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(0)

        # ── ① 브랜치 상태 카드 ──────────────────────────────────────────
        self._status_card = self._build_status_card()
        layout.addWidget(self._status_card)

        # ── ② 빠른 액션 버튼 열 ─────────────────────────────────────────
        layout.addWidget(_SectionHeader("QUICK ACTIONS"))
        layout.addSpacing(8)
        layout.addLayout(self._build_actions())
        layout.addSpacing(4)

        # ── ③ 메시지 레이블 ──────────────────────────────────────────────
        self._msg_label = QLabel("")
        self._msg_label.setStyleSheet("color:#4ade80; font-size:12px; padding:4px 0;")
        layout.addWidget(self._msg_label)

        # ── ④ 최근 커밋 ──────────────────────────────────────────────────
        layout.addWidget(_SectionHeader("RECENT COMMITS"))
        layout.addSpacing(8)
        self._commit_list = self._build_commit_list()
        layout.addWidget(self._commit_list)

        # ── ⑤ 브랜치 목록 ────────────────────────────────────────────────
        layout.addWidget(_SectionHeader("BRANCHES"))
        layout.addSpacing(8)
        branch_row = QHBoxLayout()
        branch_row.setSpacing(12)

        local_col = QVBoxLayout()
        local_lbl = QLabel("LOCAL")
        local_lbl.setStyleSheet("color:#64748b; font-size:10px; font-weight:600; letter-spacing:0.8px; margin-bottom:4px;")
        local_col.addWidget(local_lbl)
        self._local_list = self._build_branch_list()
        local_col.addWidget(self._local_list)
        branch_row.addLayout(local_col)

        remote_col = QVBoxLayout()
        remote_lbl = QLabel("REMOTE")
        remote_lbl.setStyleSheet("color:#64748b; font-size:10px; font-weight:600; letter-spacing:0.8px; margin-bottom:4px;")
        remote_col.addWidget(remote_lbl)
        self._remote_list = self._build_branch_list()
        remote_col.addWidget(self._remote_list)
        branch_row.addLayout(remote_col)

        layout.addLayout(branch_row)
        layout.addStretch()

    def _build_status_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background:#1a1a2e; border:1px solid #2d2d4a; border-radius:12px; }"
        )
        card.setMinimumHeight(80)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)

        # 브랜치 아이콘 + 이름
        icon = QLabel("⎇")
        icon.setStyleSheet("font-size:22px; color:#818cf8; margin-right:2px;")
        card_layout.addWidget(icon)

        self._branch_name = QLabel("—")
        self._branch_name.setStyleSheet(
            "font-size:20px; font-weight:700; color:#e2e8f0;"
            "font-family:'SF Mono','Menlo','Fira Code',monospace; margin-right:10px;"
        )
        card_layout.addWidget(self._branch_name)

        self._status_badge = _Badge("  —  ")
        card_layout.addWidget(self._status_badge)

        card_layout.addStretch()

        # ahead / behind 칩
        counters = QFrame()
        counters.setStyleSheet(
            "QFrame { background:#252540; border:1px solid #3d3d6b; border-radius:8px; }"
        )
        cnt_layout = QHBoxLayout(counters)
        cnt_layout.setContentsMargins(12, 6, 12, 6)
        cnt_layout.setSpacing(16)

        self._ahead_lbl = QLabel("↑ —")
        self._ahead_lbl.setStyleSheet("color:#4ade80; font-weight:600; font-size:14px;")
        self._behind_lbl = QLabel("↓ —")
        self._behind_lbl.setStyleSheet("color:#fbbf24; font-weight:600; font-size:14px;")
        cnt_layout.addWidget(self._ahead_lbl)
        cnt_layout.addWidget(self._behind_lbl)
        card_layout.addWidget(counters)

        return card

    def _build_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self._sync_btn = _ActionButton("↻  Sync Develop", "primary")
        self._sync_btn.setToolTip("origin/develop fetch → develop pull")
        self._sync_btn.clicked.connect(self._on_sync)
        row.addWidget(self._sync_btn)

        self._pr_btn = _ActionButton("🔍  PR Check", "success")
        self._pr_btn.setToolTip("커밋 컨벤션, 파일 변경 수, TODO 잔존 검사")
        self._pr_btn.clicked.connect(self._on_pr_check)
        row.addWidget(self._pr_btn)

        self._release_btn = _ActionButton("🚀  Release", "warning")
        self._release_btn.setToolTip("release/* 브랜치 생성 워크플로우")
        self._release_btn.clicked.connect(self._on_release)
        row.addWidget(self._release_btn)

        self._hotfix_btn = _ActionButton("🔥  Hotfix", "danger")
        self._hotfix_btn.setToolTip("hotfix/* 브랜치 생성 워크플로우")
        self._hotfix_btn.clicked.connect(self._on_hotfix)
        row.addWidget(self._hotfix_btn)

        self._hook_btn = _ActionButton("🔒  Pre-push", "primary")
        self._hook_btn.setToolTip("pre-push 훅 스크립트 실행 결과 확인 (F-10)")
        self._hook_btn.clicked.connect(self._on_pre_push)
        row.addWidget(self._hook_btn)

        row.addStretch()
        return row

    def _build_commit_list(self) -> QTableWidget:
        headers = ["Hash", "Commit Message", "Author", "Date"]
        w = QTableWidget(0, len(headers))
        w.setHorizontalHeaderLabels(headers)
        w.setFrameShape(QTableWidget.Shape.NoFrame)
        w.setFixedHeight(230)
        w.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        w.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        w.setShowGrid(False)
        w.verticalHeader().setVisible(False)
        w.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        w.horizontalHeader().setStretchLastSection(False)

        # 컬럼 너비
        w.setColumnWidth(0, 70)   # Hash
        w.setColumnWidth(2, 100)  # Author
        w.setColumnWidth(3, 100)  # Date
        w.horizontalHeader().setSectionResizeMode(1, w.horizontalHeader().ResizeMode.Stretch)

        w.setStyleSheet("""
            QTableWidget {
                background: #141428;
                border-radius: 8px;
                outline: none;
                gridline-color: transparent;
                font-family: 'SF Mono','Menlo','Fira Code',monospace;
                font-size: 12px;
                color: #94a3b8;
            }
            QTableWidget::item {
                padding: 0px 8px;
                border-bottom: 1px solid #1a1a38;
            }
            QTableWidget::item:hover { background: #1e1e38; color: #e2e8f0; }
            QTableWidget::item:selected { background: #312e81; color: #c7d2fe; }
            QHeaderView::section {
                background: #0f0f1f;
                color: #475569;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.8px;
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid #2d2d4a;
                text-transform: uppercase;
            }
        """)
        w.verticalHeader().setDefaultSectionSize(32)
        return w

    def _build_branch_list(self) -> QListWidget:
        w = QListWidget()
        w.setFrameShape(QListWidget.Shape.NoFrame)
        w.setFixedHeight(120)
        w.setStyleSheet("""
            QListWidget {
                background: #141428;
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 5px 10px;
                border-radius: 4px;
                font-family: 'SF Mono','Menlo',monospace;
                font-size: 12px;
                color: #64748b;
            }
            QListWidget::item:hover { background: #1e1e38; color: #94a3b8; }
        """)
        w.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return w

    # ── 시그널 연결 ────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        c = self._controller
        c.branch_summary_ready.connect(self._on_summary)
        c.sync_finished.connect(self._on_sync_result)
        c.pr_check_ready.connect(self._on_pr_check_result)
        c.branch_created.connect(self._on_branch_created)
        c.hook_result_ready.connect(self._on_hook_result)
        c.task_running.connect(self._on_busy)

    # ── 슬롯 ──────────────────────────────────────────────────────────────

    def _on_sync(self) -> None:
        self._msg_label.setText("")
        self._controller.sync_develop()

    def _on_summary(self, summary: BranchSummary) -> None:
        self._branch_name.setText(summary.current)
        self._status_badge.set_status(summary.status)
        dirty_icon = " ✦" if summary.is_dirty else ""
        self._ahead_lbl.setText(f"↑ {summary.ahead}{dirty_icon}")
        self._behind_lbl.setText(f"↓ {summary.behind}")

        # 브랜치 목록
        self._local_list.clear()
        for b in summary.local_branches:
            item = QListWidgetItem(f"* {b}" if b == summary.current else f"  {b}")
            if b == summary.current:
                item.setForeground(Qt.GlobalColor.green)
            self._local_list.addItem(item)

        self._remote_list.clear()
        for b in summary.remote_branches:
            self._remote_list.addItem(f"  {b}")

        # 커밋 로그 비동기 로드
        self._load_commits()

    def _load_commits(self) -> None:
        if not self._controller.has_repository():
            return
        from app.controller.git_worker import GitWorker
        self._commit_worker = GitWorker(
            lambda: self._controller.get_commit_log(limit=12)
        )
        self._commit_worker.result_ready.connect(self._show_commits)
        self._commit_worker.start()

    def _show_commits(self, commits: list[Commit]) -> None:
        self._commit_list.setRowCount(0)
        for c in commits:
            row = self._commit_list.rowCount()
            self._commit_list.insertRow(row)

            # Hash
            hash_item = QTableWidgetItem(c.short_hash)
            hash_item.setForeground(Qt.GlobalColor.darkCyan)
            self._commit_list.setItem(row, 0, hash_item)

            # Message
            msg_item = QTableWidgetItem(c.summary)
            self._commit_list.setItem(row, 1, msg_item)

            # Author
            author_item = QTableWidgetItem(c.author)
            author_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._commit_list.setItem(row, 2, author_item)

            # Date
            date_str = c.date.strftime("%m-%d %H:%M")
            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._commit_list.setItem(row, 3, date_item)

    def _on_sync_result(self, result: SyncResult) -> None:
        color = "#4ade80" if result.success else "#f87171"
        self._msg_label.setStyleSheet(f"color:{color}; font-size:12px; padding:4px 0;")
        self._msg_label.setText(result.message)

    def _on_pr_check(self) -> None:
        self._msg_label.setText("")
        self._controller.run_pr_check()

    def _on_pr_check_result(self, report: PrCheckReport) -> None:
        _PrCheckDialog(report, self).exec()

    def _on_release(self) -> None:
        version, ok = QInputDialog.getText(
            self, "Release 브랜치 생성", "버전 입력 (예: 1.2.0):"
        )
        if ok and version.strip():
            self._msg_label.setText("")
            self._controller.create_release_branch(version.strip())

    def _on_hotfix(self) -> None:
        issue_id, ok = QInputDialog.getText(
            self, "Hotfix 브랜치 생성", "이슈 ID 또는 설명 입력 (예: fix-login-crash):"
        )
        if ok and issue_id.strip():
            self._msg_label.setText("")
            self._controller.create_hotfix_branch(issue_id.strip())

    def _on_branch_created(self, result: BranchResult) -> None:
        color = "#4ade80" if result.success else "#f87171"
        self._msg_label.setStyleSheet(f"color:{color}; font-size:12px; padding:4px 0;")
        self._msg_label.setText(result.message)
        if result.success:
            self._controller.refresh_branch_summary()

    def _on_pre_push(self) -> None:
        self._msg_label.setText("")
        self._controller.run_pre_push_hook()

    def _on_hook_result(self, result) -> None:
        _HookResultDialog(result, self).exec()

    def _on_busy(self, running: bool) -> None:
        for btn in (self._sync_btn, self._pr_btn, self._release_btn,
                    self._hotfix_btn, self._hook_btn):
            btn.setEnabled(not running)
        self._sync_btn.setText("처리 중..." if running else "↻  Sync Develop")


class _PrCheckDialog(QDialog):
    """PR Check 결과 팝업."""

    _ICON = {True: "✅", False: "❌"}
    _CAT = {"convention": "커밋 컨벤션", "size": "변경 파일 수", "todo": "TODO 잔존"}

    def __init__(self, report: PrCheckReport, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PR Check 결과")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 전체 결과 헤더
        overall = "✅ PR 준비 완료" if report.passed else "❌ 수정 필요 항목 있음"
        color = "#4ade80" if report.passed else "#f87171"
        header = QLabel(f"<b>{overall}</b>   <span style='color:#64748b;font-size:12px'>{report.summary}</span>")
        header.setStyleSheet(f"color:{color}; font-size:15px; padding:4px 0;")
        header.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(header)

        # 항목별 결과
        result_text = QTextEdit()
        result_text.setReadOnly(True)
        result_text.setFixedHeight(160)
        result_text.setStyleSheet(
            "background:#141428; border-radius:8px; color:#94a3b8;"
            "font-family:'SF Mono','Menlo',monospace; font-size:12px; padding:8px;"
        )
        lines = []
        for item in report.items:
            icon = self._ICON[item.passed]
            cat = self._CAT.get(item.category, item.category)
            lines.append(f"{icon}  [{cat}]  {item.message}")
        result_text.setPlainText("\n".join(lines))
        layout.addWidget(result_text)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)


class _HookResultDialog(QDialog):
    """Pre-push 훅 실행 결과 팝업 (F-10)."""

    def __init__(self, result, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pre-push Hook 실행 결과")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        icon = "✅" if result.success else "❌"
        color = "#4ade80" if result.success else "#f87171"
        status_text = "훅 통과" if result.success else f"훅 실패 (exit {result.return_code})"
        header = QLabel(f"{icon}  {status_text}")
        header.setStyleSheet(f"color:{color}; font-size:15px; font-weight:700; padding:4px 0;")
        layout.addWidget(header)

        output_text = QTextEdit()
        output_text.setReadOnly(True)
        output_text.setFixedHeight(180)
        output_text.setStyleSheet(
            "background:#141428; border-radius:8px; color:#94a3b8;"
            "font-family:'SF Mono','Menlo',monospace; font-size:12px; padding:8px;"
        )
        combined = result.stdout or result.stderr or "(출력 없음)"
        output_text.setPlainText(combined)
        layout.addWidget(output_text)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)
