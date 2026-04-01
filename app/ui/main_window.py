"""MainWindow — 사이드바 + v2 통합 탭 레이아웃."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.ui.design_system import C, T, QSS


class _EqualWidthTabBar(QTabBar):
    """탭바 전체 너비를 탭 수로 균등 분배.

    tabSizeHint 오버라이드 없이 setExpanding + minimumTabSizeHint로 구현.
    tabSizeHint를 직접 건드리면 setExpanding(True)와 충돌해 텍스트가 잘린다.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setExpanding(True)
        self.setUsesScrollButtons(False)
        self.setElideMode(Qt.TextElideMode.ElideNone)

    def minimumTabSizeHint(self, index: int) -> QSize:
        """최소 탭 너비 = 0 → setExpanding이 전체 공간을 균등 분배."""
        size = super().minimumTabSizeHint(index)
        size.setWidth(0)
        return size

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self.update)

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
        self.setStyleSheet(QSS.global_app())

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFixedHeight(48)
        toolbar.setStyleSheet(QSS.toolbar())
        self.addToolBar(toolbar)

        title = QLabel("  Git Dashboard")
        title.setStyleSheet(
            f"color:{C.TEXT_BRIGHT};font-size:{T.SIZE_XL};"
            f"font-weight:{T.WEIGHT_BOLD};letter-spacing:0.5px;"
        )
        toolbar.addWidget(title)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        _git_btn_style = QSS.button()

        self._fetch_btn = QPushButton("⟳  Fetch")
        self._fetch_btn.setFixedHeight(30)
        self._fetch_btn.setStyleSheet(_git_btn_style)
        self._fetch_btn.setToolTip("원격 저장소 정보 가져오기 (git fetch)")
        self._fetch_btn.clicked.connect(self._on_fetch)
        toolbar.addWidget(self._fetch_btn)

        self._pull_btn = QPushButton("↓  Pull")
        self._pull_btn.setFixedHeight(30)
        self._pull_btn.setStyleSheet(_git_btn_style)
        self._pull_btn.setToolTip("원격 변경사항 가져오기 (git pull)")
        self._pull_btn.clicked.connect(self._on_pull)
        toolbar.addWidget(self._pull_btn)

        self._push_btn = QPushButton("↑  Push")
        self._push_btn.setFixedHeight(30)
        self._push_btn.setStyleSheet(_git_btn_style)
        self._push_btn.setToolTip("변경사항 원격으로 보내기 (git push)")
        self._push_btn.clicked.connect(self._on_push)
        toolbar.addWidget(self._push_btn)

        toolbar.addWidget(QLabel("  "))

        self._manage_btn = QPushButton("⊞  저장소 관리")
        self._manage_btn.setFixedHeight(30)
        self._manage_btn.setStyleSheet(QSS.button_primary())
        self._manage_btn.clicked.connect(self._open_repo_manager)
        toolbar.addWidget(self._manage_btn)

        toolbar.addWidget(QLabel("  "))

    def _setup_central(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(QSS.splitter())

        # 좌측: 저장소 사이드바
        self._sidebar = RepoSidebar(self._controller)
        self._sidebar.repo_selected.connect(self._on_repo_selected)
        splitter.addWidget(self._sidebar)

        # 우측: v2 통합 탭
        self._tabs = QTabWidget()
        self._tabs.setTabBar(_EqualWidthTabBar())
        self._tabs.setStyleSheet(QSS.tabs())

        # ── 탭 0: 개요 (v1 DashboardPanel) ──
        self._dashboard = DashboardPanel(self._controller)
        self._tabs.addTab(self._dashboard, "📊 개요")

        # ── 탭 1: Commit Graph (F-13) ──
        self._tabs.addTab(self._make_lazy_tab("graph"), "🔀 그래프")

        # ── 탭 2: Diff Viewer (F-14) ──
        self._tabs.addTab(self._make_lazy_tab("diff"), "📋 변경사항")

        # ── 탭 3: Stash (F-15) ──
        self._tabs.addTab(self._make_lazy_tab("stash"), "📦 Stash")

        # ── 탭 4: Worktree (신규) ──
        self._tabs.addTab(self._make_lazy_tab("worktree"), "🌿 Worktree")

        # ── 탭 5: Interactive Rebase (F-18) ──
        self._tabs.addTab(self._make_lazy_tab("rebase"), "🔁 Rebase")

        # ── 탭 6: Merge Conflict (F-19) ──
        self._tabs.addTab(self._make_lazy_tab("merge"), "⚡ Conflict")

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
        placeholder.setStyleSheet(f"background:{C.BG_BASE};")
        lbl = QLabel("탭 클릭 시 로드됩니다...")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color:{C.TEXT_DISABLED};font-size:{T.SIZE_MD};")
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
            from app.ui.commit_panel import CommitPanel
            if repo:
                panel = CommitPanel(repo)
                panel.committed.connect(self._on_committed)
            else:
                panel = QLabel("저장소를 선택하세요.")
                panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
                "graph":    "🔀 그래프",
                "diff":     "📋 변경사항",
                "stash":    "📦 Stash",
                "worktree": "🌿 Worktree",
                "rebase":   "🔁 Rebase",
                "merge":    "⚡ Conflict",
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

        # Cmd+R: 현재 탭 새로고침
        shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        shortcut.activated.connect(self._refresh_current_tab)

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
        """저장소 변경 시 v2 패널 캐시 무효화 및 탭 리셋."""
        self._v2_panels.clear()
        self._reset_v2_tabs()

    def _on_repo_selected(self, path: str) -> None:
        self._controller.switch_repository(path)
        self._sidebar.refresh()
        self._v2_panels.clear()
        self._reset_v2_tabs()  # 탭 위젯도 플레이스홀더로 교체

    def _reset_v2_tabs(self) -> None:
        """v2 탭 위젯을 플레이스홀더로 교체 (저장소 전환 시 강제 재로드)."""
        _tab_info = [
            (1, "graph",    "🔀 그래프"),
            (2, "diff",     "📋 변경사항"),
            (3, "stash",    "📦 Stash"),
            (4, "worktree", "🌿 Worktree"),
            (5, "rebase",   "🔁 Rebase"),
            (6, "merge",    "⚡ Conflict"),
        ]
        self._tabs.blockSignals(True)
        for index, name, label in _tab_info:
            if index >= self._tabs.count():
                continue
            widget = self._tabs.widget(index)
            # 이미 플레이스홀더면 스킵
            if widget and widget.property("lazy_tab_name"):
                continue
            placeholder = self._make_lazy_tab(name)
            self._tabs.removeTab(index)
            self._tabs.insertTab(index, placeholder, label)
        self._tabs.blockSignals(False)

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

    def _on_fetch(self) -> None:
        """Fetch 실행."""
        repo = self._controller.get_repository()
        if not repo:
            return
        self._fetch_btn.setEnabled(False)
        self._status_label.setText("⟳ Fetch 중...")
        from app.controller.git_worker import GitWorker
        worker = GitWorker(repo.fetch)
        def _done(result):
            self._fetch_btn.setEnabled(True)
            self._controller.refresh_branch_summary()
            self._status_label.setText("✓ Fetch 완료")
        def _err(msg):
            self._fetch_btn.setEnabled(True)
            self._status_label.setText(f"Fetch 오류: {msg}")
        worker.result_ready.connect(_done)
        worker.error_occurred.connect(_err)
        worker.start()
        self._fetch_worker = worker

    def _on_pull(self) -> None:
        """Pull 실행."""
        repo = self._controller.get_repository()
        if not repo:
            return
        self._pull_btn.setEnabled(False)
        self._status_label.setText("⟳ Pull 중...")
        from app.controller.git_worker import GitWorker
        branch = repo.get_current_branch()
        worker = GitWorker(lambda: repo.pull(branch))
        def _done(result):
            self._pull_btn.setEnabled(True)
            self._controller.refresh_branch_summary()
            self._status_label.setText("✓ Pull 완료")
            self._refresh_commit_panel()
        def _err(msg):
            self._pull_btn.setEnabled(True)
            self._status_label.setText(f"Pull 오류: {msg}")
        worker.result_ready.connect(_done)
        worker.error_occurred.connect(_err)
        worker.start()
        self._pull_worker = worker

    def _on_push(self) -> None:
        """Push 실행."""
        repo = self._controller.get_repository()
        if not repo:
            return
        self._push_btn.setEnabled(False)
        self._status_label.setText("⟳ Push 중...")
        from app.controller.git_worker import GitWorker
        branch = repo.get_current_branch()
        worker = GitWorker(lambda: repo.push(branch=branch))
        def _done(result):
            self._push_btn.setEnabled(True)
            ok, msg = result if isinstance(result, tuple) else (True, "")
            if ok:
                self._controller.refresh_branch_summary()
                self._status_label.setText("✓ Push 완료")
            else:
                self._status_label.setText(f"Push 오류: {msg}")
        def _err(msg):
            self._push_btn.setEnabled(True)
            self._status_label.setText(f"Push 오류: {msg}")
        worker.result_ready.connect(_done)
        worker.error_occurred.connect(_err)
        worker.start()
        self._push_worker = worker

    def _on_committed(self) -> None:
        """Commit 완료 시 그래프/상태 갱신."""
        self._controller.refresh_branch_summary()
        panel = self._v2_panels.get("graph")
        if panel and hasattr(panel, "_graph_view"):
            self._refresh_graph(panel._graph_view)
        self._status_label.setText("✓ 커밋 완료")

    def _refresh_commit_panel(self) -> None:
        """CommitPanel 새로고침."""
        panel = self._v2_panels.get("diff")
        if panel and hasattr(panel, "refresh"):
            panel.refresh()

    def _refresh_current_tab(self) -> None:
        """Cmd+R: 현재 활성 탭을 새로고침."""
        index = self._tabs.currentIndex()
        widget = self._tabs.widget(index)
        if widget is None:
            return

        name = widget.property("lazy_tab_name")
        if name:
            # 아직 로드 안 된 플레이스홀더 → 로드
            self._replace_tab(index, name)
            return

        # 이미 로드된 탭: 탭별 새로고침
        if index == 0:
            # 개요 탭 → 브랜치 요약 갱신
            self._controller.refresh_branch_summary()
        elif index == 1:
            # 커밋 그래프 → graph view 재렌더
            panel = self._v2_panels.get("graph")
            if panel and hasattr(panel, "_graph_view"):
                self._refresh_graph(panel._graph_view)
        elif index == 2:
            # Diff 탭 → _reset_v2_tabs로 패널 교체 후 재로드
            placeholder = self._make_lazy_tab("diff")
            self._tabs.removeTab(2)
            self._tabs.insertTab(2, placeholder, "📋 변경사항")
            self._v2_panels.pop("diff", None)
            self._tabs.setCurrentIndex(2)
            self._replace_tab(2, "diff")
        elif index == 3:
            # Stash → refresh()
            panel = self._v2_panels.get("stash")
            if panel and hasattr(panel, "refresh"):
                panel.refresh()
        elif index == 5:
            # Rebase → 상태 갱신 시도
            pass

        # 공통: 브랜치 요약도 갱신
        self._controller.refresh_branch_summary()
        self._status_label.setText("↻ 새로고침 완료")
