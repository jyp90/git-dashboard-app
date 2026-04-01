"""CommitPanel — Stage/Unstage/Commit 워크플로우 패널 (SourceTree 스타일)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.diff_parser import DiffParser
from app.ui.design_system import C, T, QSS
from app.ui.diff_viewer import DiffViewer

if TYPE_CHECKING:
    from app.infrastructure.git_repository import GitRepository


def _btn(text: str, variant: str = "default") -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(28)
    styles = {
        "default": QSS.button(
            bg=C.BG_ACTIVE,
            fg=C.ACCENT_LIGHT,
            border=C.BORDER_STRONG,
            bg_hover=C.BG_PRESSED,
            fg_hover=C.TEXT_BRIGHT,
            border_hover=C.ACCENT,
            font_size=T.SIZE_SM,
        ),
        "success": QSS.button_success(font_size=T.SIZE_BASE),
        "danger":  QSS.button_danger(font_size=T.SIZE_SM),
    }
    b.setStyleSheet(styles.get(variant, styles["default"]))
    return b


class CommitPanel(QWidget):
    """Stage → Commit 워크플로우 패널.

    레이아웃:
    ┌──────────────────┬─────────────────────────────────┐
    │ Unstaged (N) [⬆] │                                 │
    │  M file.py    ⬆  │         Diff Viewer             │
    │──────────────────│   (선택한 파일의 변경사항 표시)    │
    │ Staged (N)   [⬇] │                                 │
    │  M config.py  ⬇  │                                 │
    ├──────────────────┴─────────────────────────────────┤
    │ [□ Amend]  메시지: [________________________] [Commit] │
    └────────────────────────────────────────────────────┘
    """

    committed = pyqtSignal()   # 커밋 완료 시그널

    def __init__(self, repo: "GitRepository", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._parser = DiffParser(repo)
        self._unstaged: list[dict] = []
        self._staged: list[dict] = []
        self._setup_ui()
        self.refresh()

    # ── UI 구성 ───────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"background:{C.BG_BASE};color:{C.TEXT_PRIMARY};")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 상단 새로고침 바 ──
        top = QHBoxLayout()
        top.setContentsMargins(12, 7, 10, 5)
        lbl = QLabel("변경사항")
        lbl.setStyleSheet(
            f"color:{C.TEXT_SECONDARY};font-size:{T.SIZE_MD};"
            f"font-weight:{T.WEIGHT_SEMI};"
        )
        top.addWidget(lbl)
        top.addStretch()
        refresh_btn = _btn("↻ 새로고침")
        refresh_btn.clicked.connect(self.refresh)
        top.addWidget(refresh_btn)
        root.addLayout(top)

        sep0 = self._separator()
        root.addWidget(sep0)

        # ── 메인: 파일 목록 + Diff ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle{{background:{C.BORDER_SUBTLE};}}")

        # 좌측: 파일 목록 패널
        left = QWidget()
        left.setStyleSheet("background:transparent;")
        left.setMinimumWidth(200)
        left.setMaximumWidth(300)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # ── Staged 섹션 (위) ── SourceTree 레이아웃: Staged가 상단
        staged_header = self._section_header("Staged", "⬇ 모두 Unstage")
        self._staged_count = staged_header[0]
        unstage_all_btn = staged_header[1]
        unstage_all_btn.clicked.connect(self._on_unstage_all)
        left_layout.addLayout(staged_header[2])

        self._staged_list = self._make_file_list()
        self._staged_list.currentRowChanged.connect(
            lambda row: self._on_file_selected(row, staged=True)
        )
        self._staged_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._staged_list.customContextMenuRequested.connect(
            lambda pos: self._on_staged_context(pos)
        )
        left_layout.addWidget(self._staged_list)

        left_layout.addWidget(self._separator())

        # ── Unstaged 섹션 (아래) ── SourceTree 레이아웃: Unstaged가 하단
        unstaged_header = self._section_header("Unstaged", "⬆ 모두 Stage")
        self._unstaged_count = unstaged_header[0]
        stage_all_btn = unstaged_header[1]
        stage_all_btn.clicked.connect(self._on_stage_all)
        left_layout.addLayout(unstaged_header[2])

        self._unstaged_list = self._make_file_list()
        self._unstaged_list.currentRowChanged.connect(
            lambda row: self._on_file_selected(row, staged=False)
        )
        self._unstaged_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._unstaged_list.customContextMenuRequested.connect(
            lambda pos: self._on_unstaged_context(pos)
        )
        left_layout.addWidget(self._unstaged_list)

        splitter.addWidget(left)

        # 우측: Diff Viewer
        self._viewer = DiffViewer()
        splitter.addWidget(self._viewer)
        splitter.setSizes([250, 800])
        root.addWidget(splitter, 1)

        # ── 하단 커밋 바 ──
        root.addWidget(self._separator())
        bottom = self._build_commit_bar()
        root.addLayout(bottom)

    def _section_header(self, title: str, btn_text: str) -> tuple:
        """섹션 헤더 (라벨 + 카운트 + 버튼) → (count_label, button, layout)"""
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 8, 5)
        count_lbl = QLabel(f"{title} (0)")
        count_lbl.setStyleSheet(
            f"color:{C.TEXT_MUTED};font-size:{T.SIZE_XS};"
            f"font-weight:{T.WEIGHT_BOLD};letter-spacing:0.8px;"
            f"text-transform:uppercase;"
        )
        layout.addWidget(count_lbl)
        layout.addStretch()
        btn = _btn(btn_text)
        btn.setFixedHeight(22)
        layout.addWidget(btn)
        return count_lbl, btn, layout

    def _make_file_list(self) -> QListWidget:
        lst = QListWidget()
        lst.setFrameShape(QListWidget.Shape.NoFrame)
        lst.setStyleSheet(QSS.list_widget())
        return lst

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{C.BORDER_SUBTLE};border:none;")
        return sep

    def _build_commit_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 7, 10, 9)
        layout.setSpacing(8)

        self._amend_cb = QCheckBox("Amend")
        self._amend_cb.setStyleSheet(
            f"QCheckBox{{color:{C.TEXT_MUTED};font-size:{T.SIZE_SM};}}"
            f"QCheckBox::indicator{{width:14px;height:14px;border:1px solid {C.BORDER_STRONG};"
            f"border-radius:3px;background:{C.BG_RAISED};}}"
            f"QCheckBox::indicator:checked{{background:{C.ACCENT};border-color:{C.ACCENT};}}"
        )
        self._amend_cb.toggled.connect(self._on_amend_toggled)
        layout.addWidget(self._amend_cb)

        msg_lbl = QLabel("메시지:")
        msg_lbl.setStyleSheet(f"color:{C.TEXT_MUTED};font-size:{T.SIZE_SM};")
        layout.addWidget(msg_lbl)

        self._msg_input = QTextEdit()
        self._msg_input.setMaximumHeight(56)
        self._msg_input.setPlaceholderText("커밋 메시지를 입력하세요 (첫 줄이 제목)")
        self._msg_input.setStyleSheet(
            f"QTextEdit{{background:{C.BG_RAISED};color:{C.TEXT_PRIMARY};"
            f"border:1px solid {C.BORDER_DEFAULT};"
            f"border-radius:4px;padding:4px 8px;"
            f"font-size:{T.SIZE_BASE};font-family:{T.FAMILY_MONO};}}"
            f"QTextEdit:focus{{border-color:{C.ACCENT};}}"
        )
        self._msg_input.textChanged.connect(self._update_commit_btn)
        layout.addWidget(self._msg_input, 1)

        self._commit_btn = _btn("✓  Commit", "success")
        self._commit_btn.setFixedWidth(90)
        self._commit_btn.setFixedHeight(40)
        self._commit_btn.setEnabled(False)
        self._commit_btn.clicked.connect(self._on_commit)
        layout.addWidget(self._commit_btn)

        return layout

    # ── 데이터 갱신 ───────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """파일 상태 목록 새로고침."""
        status = self._repo.get_working_tree_status()
        self._unstaged = [f for f in status if f["unstaged"]]
        self._staged = [f for f in status if f["staged"]]

        self._populate_list(self._unstaged_list, self._unstaged)
        self._populate_list(self._staged_list, self._staged)

        self._unstaged_count.setText(f"Unstaged ({len(self._unstaged)})")
        self._staged_count.setText(f"Staged ({len(self._staged)})")

        self._update_commit_btn()
        self._viewer.clear()

    def _populate_list(self, lst: QListWidget, files: list[dict]) -> None:
        lst.clear()
        for f in files:
            icon = {"M": "M", "A": "+", "D": "－", "R": "R", "?": "?"}.get(f["status"], "M")
            item = QListWidgetItem(f"{icon}  {f['path']}")
            item.setData(Qt.ItemDataRole.UserRole, f["path"])
            lst.addItem(item)

    # ── 이벤트 핸들러 ─────────────────────────────────────────────────────────

    def _on_file_selected(self, row: int, staged: bool) -> None:
        files = self._staged if staged else self._unstaged
        if row < 0 or row >= len(files):
            return
        path = files[row]["path"]
        try:
            if staged:
                diffs = self._parser.parse_staged()
            else:
                diffs = self._parser.parse_working_tree()
            match = [d for d in diffs if (d.new_path == path or d.old_path == path)]
            if match:
                self._viewer.set_diff(match[0])
            else:
                self._viewer.clear()
        except Exception:
            self._viewer.clear()

    def _on_stage_all(self) -> None:
        if self._repo.stage_all():
            self.refresh()

    def _on_unstage_all(self) -> None:
        if self._repo.unstage_all():
            self.refresh()

    def _on_unstaged_context(self, pos) -> None:
        item = self._unstaged_list.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.setStyleSheet(QSS.context_menu())
        stage_act = menu.addAction(f"⬆  Stage: {path}")
        discard_act = menu.addAction(f"✕  변경사항 되돌리기")
        action = menu.exec(self._unstaged_list.mapToGlobal(pos))
        if action == stage_act:
            if self._repo.stage_file(path):
                self.refresh()
        elif action == discard_act:
            reply = QMessageBox.question(
                self, "변경사항 되돌리기",
                f"'{path}'의 변경사항을 되돌릴까요?\n(되돌릴 수 없습니다)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                if self._repo.discard_file(path):
                    self.refresh()

    def _on_staged_context(self, pos) -> None:
        item = self._staged_list.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.setStyleSheet(QSS.context_menu())
        unstage_act = menu.addAction(f"⬇  Unstage: {path}")
        action = menu.exec(self._staged_list.mapToGlobal(pos))
        if action == unstage_act:
            if self._repo.unstage_file(path):
                self.refresh()

    def _on_amend_toggled(self, checked: bool) -> None:
        if checked:
            # 마지막 커밋 메시지 불러오기
            try:
                last_msg = self._repo.get_last_commit_message()
                self._msg_input.setPlainText(last_msg)
            except Exception:
                pass
        self._update_commit_btn()

    def _update_commit_btn(self) -> None:
        has_staged = len(self._staged) > 0
        has_msg = bool(self._msg_input.toPlainText().strip())
        amend = self._amend_cb.isChecked()
        self._commit_btn.setEnabled((has_staged and has_msg) or amend)

    def _on_commit(self) -> None:
        msg = self._msg_input.toPlainText().strip()
        amend = self._amend_cb.isChecked()
        ok, result = self._repo.commit(msg, amend=amend)
        if ok:
            self._msg_input.clear()
            self._amend_cb.setChecked(False)
            self.refresh()
            self.committed.emit()
        else:
            QMessageBox.warning(self, "Commit 실패", result)
