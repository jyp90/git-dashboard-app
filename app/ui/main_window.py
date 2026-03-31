"""MainWindow — 사이드바 + v2 통합 탭 레이아웃."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
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
    """메인 윈도우 — 좌측 저장소 사이드바 + 우측 통합 탭 대시보드."""

    _REFRESH_INTERVAL_MS = 30_000

    def __init__(self, controller: WorkflowController) -> None:
        super().__init__()
        self._controller = controller
        self._v2_panels: dict[str, QWidget] = {}
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
        self.setMinimumSize(1100, 700)
        self.resize(1400, 860)

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFixedHeight(46)
        self.addToolBar(toolbar)

        title = QLabel("  Git Dashboard")
        title.setStyleSheet(
            "color:#e2e8f0; font-size:15px; font-weight:700; letter-spacing:0.3px;"
        )
        toolbar.addWidget(title)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

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

        toolbar.addWidget(QLabel("  "))

    def _setup_central(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background:#2d2d4a; }")

        # 좌측: 저장소 사이드바
        self._sidebar = RepoSidebar(self._controller)
        self._sidebar.repo_selected.connect(self._on_repo_selected)
        splitter.addWidget(self._sidebar)

        # 우측: v2 통합 탭
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #0f0f1a; }
            QTabBar::tab {
                background: #1a1a2e; color: #64748b;
                padding: 7px 18px; border: none; font-size: 12px;
            }
            QTabBar::tab:selected { background: #252540; color: #a5b4fc; border-bottom: 2px solid #6366f1; }
            QTabBar::tab:hover { background: #1e1e38; color: #94a3b8; }
        """)

        # ── 탭 0: 개요 (v1 DashboardPanel) ──
        self._dashboard = DashboardPanel(self._controller)
        self._tabs.addTab(self._dashboard, "📊  개요")

        # ── 탭 1: Commit Graph (F-13) ──
        self._tabs.addTab(self._make_lazy_tab("graph"), "🔀  커밋 그래프")

        # ── 탭 2: Diff Viewer (F-14) ──
        self._tabs.addTab(self._make_lazy_tab("diff"), "📋  Diff")

        # ── 탭 3: Stash (F-15) ──
        self._tabs.addTab(self._make_lazy_tab("stash"), "📦  Stash")

        # ── 탭 4: Worktree (신규) ──
        self._tabs.addTab(self._make_lazy_tab("worktree"), "🌿  Worktree")

        # ── 탭 5: Interactive Rebase (F-18) ──
        self._tabs.addTab(self._make_lazy_tab("rebase"), "🔁  Rebase")

        # ── 탭 6: Merge Conflict (F-19) ──
        self._tabs.addTab(self._make_lazy_tab("merge"), "⚡  충돌 해결")

        self._tabs.currentChanged.connect(self._on_tab_changed)

        splitter.addWidget(self._tabs)
        splitter.setSizes([190, 1210])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

    def _make_lazy_tab(self, name: str) -> QWidget:
        """탭 선택 시 지연 로드를 위한 플레이스홀더 위젯."""
        placeholder = QWidget()
        placeholder.setProperty("lazy_tab_name", name)
        placeholder.setStyleSheet("background: #0f0f1a;")
        lbl = QLabel("탭 클릭 시 로드됩니다...")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #475569; font-size: 13px;")
        QVBoxLayout(placeholder).addWidget(lbl)
        return placeholder

    def _load_tab(self, name: str) -> QWidget:
        """실제 v2 패널 로드 (lazy initialization)."""
        if name in self._v2_panels:
            return self._v2_panels[name]

        repo = self._controller.get_repository()

        if name == "graph":
            from app.domain.commit_graph_builder import CommitGraphBuilder
            from app.ui.commit_graph_view import CommitGraphView
            panel = QWidget()
            panel.setStyleSheet("background: #0f0f1a;")
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(0, 0, 0, 0)
            view = CommitGraphView()
            layout.addWidget(view)
            panel._graph_view = view
            panel._refresh = lambda: self._refresh_graph(view)
            if repo:
                self._refresh_graph(view)
            self._v2_panels[name] = panel

        elif name == "diff":
            from app.domain.diff_parser import DiffParser
            from app.ui.diff_viewer import DiffViewer
            from PyQt6.QtWidgets import QComboBox, QHBoxLayout
            panel = QWidget()
            panel.setStyleSheet("background: #0f0f1a;")
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(0, 0, 0, 0)
            # 파일 선택 바
            top = QHBoxLayout()
            top.setContentsMargins(8, 6, 8, 4)
            _DIFF_MODES = [
                ("📝  Working Tree",  "HEAD 대비 미커밋 변경사항  (git diff)"),
                ("📌  Staged",        "커밋 예정 스테이징 변경사항  (git diff --cached)"),
                ("🕐  최근 커밋",     "HEAD~1 → HEAD 커밋 변경  (git diff HEAD~1 HEAD)"),
            ]
            combo = QComboBox()
            combo.setStyleSheet(
                "QComboBox { background:#1e1e38; color:#a5b4fc; border:1px solid #3d3d6b;"
                "border-radius:4px; padding:4px 10px; font-size:12px; min-width:160px; }"
                "QComboBox::drop-down { border:none; width:20px; }"
                "QComboBox QAbstractItemView { background:#1a1a2e; color:#d4d4d4;"
                "selection-background-color:#312e81; border:1px solid #3d3d6b; }"
            )
            for label, _ in _DIFF_MODES:
                combo.addItem(label)

            diff_title = QLabel("비교:")
            diff_title.setStyleSheet("color:#64748b; font-size:12px;")
            top.addWidget(diff_title)
            top.addWidget(combo)

            desc_lbl = QLabel(_DIFF_MODES[0][1])
            desc_lbl.setStyleSheet("color:#475569; font-size:11px; margin-left:6px;")
            top.addWidget(desc_lbl)
            top.addStretch()
            layout.addLayout(top)

            sep = QWidget()
            sep.setFixedHeight(1)
            sep.setStyleSheet("background:#1e1e38;")
            layout.addWidget(sep)

            viewer = DiffViewer()
            layout.addWidget(viewer)
            if repo:
                parser = DiffParser(repo)

                def _load_diff(index: int) -> None:
                    try:
                        if index == 0:  # Working Tree
                            diffs = parser.parse_working_tree()
                        elif index == 1:  # Staged
                            diffs = parser.parse_staged()
                        else:  # 최근 커밋 (HEAD~1..HEAD)
                            commits = repo.get_commit_log(limit=2)
                            if len(commits) >= 2:
                                diffs = parser.parse_commit(commits[0].hash)
                            else:
                                diffs = []
                        if diffs:
                            viewer.set_diff(diffs[0])
                        else:
                            viewer.clear()
                    except Exception:
                        viewer.clear()

                def _on_diff_changed(index: int) -> None:
                    desc_lbl.setText(_DIFF_MODES[index][1])
                    _load_diff(index)

                combo.currentIndexChanged.connect(_on_diff_changed)
                _load_diff(0)  # 초기 로드

            self._v2_panels[name] = panel

        elif name == "stash":
            from app.domain.stash_manager import StashManager
            from app.ui.stash_panel import StashPanel
            if repo:
                mgr = StashManager(repo)
                panel = StashPanel(mgr)
            else:
                panel = QLabel("저장소를 선택하세요.")
                panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._v2_panels[name] = panel

        elif name == "worktree":
            from app.ui.worktree_panel import WorktreePanel
            panel = WorktreePanel(self._controller)
            self._v2_panels[name] = panel

        elif name == "rebase":
            from app.domain.rebase_orchestrator import RebaseOrchestrator
            from app.ui.rebase_dialog import RebaseDialog
            if repo:
                orc = RebaseOrchestrator(repo)
                panel = QWidget()
                panel.setStyleSheet("background: #0f0f1a;")
                layout = QVBoxLayout(panel)
                layout.setContentsMargins(0, 0, 0, 0)
                dialog = RebaseDialog(orc)
                dialog.setWindowFlags(Qt.WindowType.Widget)
                layout.addWidget(dialog)
            else:
                panel = QLabel("저장소를 선택하세요.")
                panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._v2_panels[name] = panel

        elif name == "merge":
            from app.domain.conflict_resolver import ConflictResolver
            from app.ui.merge_editor import MergeEditor
            if repo:
                resolver = ConflictResolver(repo)
                panel = MergeEditor(resolver)
                panel.load_conflicts()
            else:
                panel = QLabel("저장소를 선택하세요.")
                panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._v2_panels[name] = panel

        return self._v2_panels.get(name, QWidget())

    def _replace_tab(self, index: int, name: str) -> None:
        """플레이스홀더 탭을 실제 패널로 교체."""
        widget = self._tabs.widget(index)
        if widget and widget.property("lazy_tab_name") == name:
            real_panel = self._load_tab(name)
            self._tabs.removeTab(index)
            tab_labels = {
                "graph":    "🔀  커밋 그래프",
                "diff":     "📋  Diff",
                "stash":    "📦  Stash",
                "worktree": "🌿  Worktree",
                "rebase":   "🔁  Rebase",
                "merge":    "⚡  충돌 해결",
            }
            self._tabs.insertTab(index, real_panel, tab_labels.get(name, name))
            self._tabs.setCurrentIndex(index)

    def _refresh_graph(self, view) -> None:
        """커밋 그래프 비동기 갱신."""
        repo = self._controller.get_repository()
        if not repo:
            return
        from app.controller.git_worker import GitWorker
        from app.domain.commit_graph_builder import CommitGraphBuilder
        builder = CommitGraphBuilder(repo)

        def do_build():
            return builder.build(limit=200)

        worker = GitWorker(do_build)
        worker.result_ready.connect(view.set_graph)
        worker.start()
        self._graph_worker = worker  # GC 방지

    # ── 설정 ───────────────────────────────────────────────────────────────

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
        dialog.repos_changed.connect(self._on_repo_changed)
        dialog.exec()

    def _on_repo_changed(self) -> None:
        """저장소 변경 시 v2 패널 캐시 무효화."""
        self._v2_panels.clear()

    def _on_repo_selected(self, path: str) -> None:
        self._controller.switch_repository(path)
        self._sidebar.refresh()
        self._v2_panels.clear()  # 저장소 전환 시 패널 재생성

    def _on_tab_changed(self, index: int) -> None:
        """탭 전환 시 lazy load."""
        widget = self._tabs.widget(index)
        if widget is None:
            return
        name = widget.property("lazy_tab_name")
        if name:
            self._replace_tab(index, name)
        elif index == 0:
            pass  # DashboardPanel은 항상 살아있음

    def _on_branch_summary(self, summary: BranchSummary) -> None:
        active = self._controller.get_active_repo()
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
