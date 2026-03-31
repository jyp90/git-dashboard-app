"""StashPanel — Stash 관리 UI 위젯 (앱 테마 적용)."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.domain.models import FileDiff, StashEntry
from app.domain.stash_manager import StashManager
from app.ui.diff_viewer import DiffViewer


def _action_btn(text: str, variant: str = "default") -> QPushButton:
    """공통 액션 버튼 팩토리."""
    btn = QPushButton(text)
    btn.setFixedHeight(30)
    styles = {
        "default": (
            "QPushButton { background:#252540; color:#a5b4fc; border:1px solid #3d3d6b;"
            "border-radius:5px; padding:2px 14px; font-size:12px; }"
            "QPushButton:hover { background:#2d2d50; color:#c7d2fe; }"
            "QPushButton:disabled { color:#3d3d6b; border-color:#2d2d4a; }"
        ),
        "success": (
            "QPushButton { background:#14342a; color:#4ade80; border:1px solid #166534;"
            "border-radius:5px; padding:2px 14px; font-size:12px; }"
            "QPushButton:hover { background:#1a4535; }"
            "QPushButton:disabled { color:#2d4a3a; border-color:#1e3a2a; }"
        ),
        "danger": (
            "QPushButton { background:#2d1010; color:#f87171; border:1px solid #7f1d1d;"
            "border-radius:5px; padding:2px 14px; font-size:12px; }"
            "QPushButton:hover { background:#3a1515; }"
            "QPushButton:disabled { color:#4a2020; border-color:#4a1a1a; }"
        ),
        "primary": (
            "QPushButton { background:#1e3a5f; color:#60a5fa; border:1px solid #1d4ed8;"
            "border-radius:5px; padding:2px 14px; font-size:12px; }"
            "QPushButton:hover { background:#1e40af; color:#fff; }"
        ),
    }
    btn.setStyleSheet(styles.get(variant, styles["default"]))
    return btn


class StashPanel(QWidget):
    """Stash 목록 + 액션 + Diff 미리보기 패널.

    Apply: stash 내용을 현재 브랜치에 적용 (stash 목록 유지)
    Pop:   Apply 후 stash 목록에서 자동 삭제
    Drop:  현재 브랜치에 적용하지 않고 stash만 삭제
    """

    stash_applied = pyqtSignal(int)
    stash_dropped = pyqtSignal(int)
    stash_created = pyqtSignal()

    def __init__(self, stash_manager: StashManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mgr = stash_manager
        self._setup_ui()
        self.refresh()

    # ── UI 구성 ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setStyleSheet("background: #0f0f1a; color: #d4d4d4;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # ── 헤더 ──
        header_row = QHBoxLayout()
        title = QLabel("Stash")
        title.setStyleSheet(
            "color:#e2e8f0; font-size:15px; font-weight:700; letter-spacing:0.5px;"
        )
        header_row.addWidget(title)
        header_row.addStretch()

        refresh_btn = _action_btn("↻ 새로고침")
        refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(refresh_btn)

        new_btn = _action_btn("＋ 새 Stash", "primary")
        new_btn.setToolTip("현재 미커밋 변경사항을 stash로 임시 저장")
        new_btn.clicked.connect(self._on_new_stash)
        header_row.addWidget(new_btn)
        layout.addLayout(header_row)

        # ── 설명 ──
        desc = QLabel(
            "Stash는 커밋하지 않은 변경사항을 임시 저장합니다. "
            "브랜치 전환 전 작업을 보관할 때 유용합니다."
        )
        desc.setStyleSheet("color:#475569; font-size:11px;")
        layout.addWidget(desc)

        # ── 분할 영역 ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background:#2d2d4a; }")

        # 왼쪽: stash 목록
        list_widget = QWidget()
        list_widget.setStyleSheet("background: transparent;")
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(4)

        list_header = QLabel("저장된 Stash 목록")
        list_header.setStyleSheet(
            "color:#64748b; font-size:10px; font-weight:700; letter-spacing:0.8px;"
            "padding-bottom:4px;"
        )
        list_layout.addWidget(list_header)

        self._list = QListWidget()
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        self._list.setStyleSheet("""
            QListWidget {
                background: #141428;
                border-radius: 8px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-bottom: 1px solid #1a1a38;
                color: #94a3b8;
                font-size: 12px;
                font-family: 'Menlo', monospace;
            }
            QListWidget::item:hover { background: #1e1e38; color: #e2e8f0; }
            QListWidget::item:selected { background: #312e81; color: #c7d2fe; }
        """)
        self._list.currentRowChanged.connect(self._on_selection_changed)
        list_layout.addWidget(self._list)

        self._empty_lbl = QLabel("저장된 Stash가 없습니다.\n\n'＋ 새 Stash' 버튼으로 현재 변경사항을 저장하세요.")
        self._empty_lbl.setStyleSheet("color:#475569; font-size:12px; padding:20px;")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setVisible(False)
        list_layout.addWidget(self._empty_lbl)
        splitter.addWidget(list_widget)

        # 오른쪽: diff 미리보기
        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        preview_header = QLabel("변경 내용 미리보기")
        preview_header.setStyleSheet(
            "color:#64748b; font-size:10px; font-weight:700; letter-spacing:0.8px;"
            "padding-bottom:4px;"
        )
        right_layout.addWidget(preview_header)
        self._diff_viewer = DiffViewer()
        right_layout.addWidget(self._diff_viewer)
        splitter.addWidget(right_widget)

        splitter.setSizes([280, 520])
        layout.addWidget(splitter, 1)

        # ── 구분선 ──
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#1e1e38; border:none;")
        layout.addWidget(sep)

        # ── 액션 버튼 바 ──
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self._btn_apply = _action_btn("✓  Apply", "success")
        self._btn_apply.setToolTip("선택한 stash를 현재 브랜치에 적용 (stash 목록 유지)")
        self._btn_apply.clicked.connect(self._on_apply)
        btn_bar.addWidget(self._btn_apply)

        self._btn_pop = _action_btn("⬆  Pop", "default")
        self._btn_pop.setToolTip("선택한 stash를 적용하고 stash 목록에서 삭제")
        self._btn_pop.clicked.connect(self._on_pop)
        btn_bar.addWidget(self._btn_pop)

        self._btn_drop = _action_btn("✕  Drop", "danger")
        self._btn_drop.setToolTip("선택한 stash를 삭제 (적용 없이 제거)")
        self._btn_drop.clicked.connect(self._on_drop)
        btn_bar.addWidget(self._btn_drop)

        btn_bar.addStretch()

        legend = QLabel("Apply: 적용 후 유지  ·  Pop: 적용 후 삭제  ·  Drop: 적용 없이 삭제")
        legend.setStyleSheet("color:#334155; font-size:10px;")
        btn_bar.addWidget(legend)

        layout.addLayout(btn_bar)

    # ── 데이터 갱신 ────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """stash 목록 새로고침."""
        self._list.clear()
        stashes = self._mgr.list_stashes()

        has_stash = len(stashes) > 0
        self._list.setVisible(has_stash)
        self._empty_lbl.setVisible(not has_stash)
        self._btn_apply.setEnabled(has_stash)
        self._btn_pop.setEnabled(has_stash)
        self._btn_drop.setEnabled(has_stash)

        for entry in stashes:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, entry.index)
            branch_text = (
                f"  on {entry.branch}"
                if entry.branch and entry.branch != "unknown"
                else ""
            )
            item.setText(f"stash@{{{entry.index}}}{branch_text}\n  {entry.message}")
            self._list.addItem(item)

    # ── 이벤트 핸들러 ──────────────────────────────────────────────────────

    def _on_selection_changed(self, row: int) -> None:
        if row < 0:
            self._diff_viewer.clear()
            return
        item = self._list.item(row)
        if not item:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        diffs = self._mgr.show_stash(index)
        if diffs:
            self._diff_viewer.set_diff(diffs[0])
        else:
            self._diff_viewer.clear()

    def _on_apply(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        if self._mgr.apply_stash(index=index, pop=False):
            self.stash_applied.emit(index)
            self.refresh()
        else:
            QMessageBox.warning(self, "Apply 실패", f"stash@{{{index}}} 적용 실패\n충돌이 있을 수 있습니다.")

    def _on_pop(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        if self._mgr.apply_stash(index=index, pop=True):
            self.stash_applied.emit(index)
            self.stash_dropped.emit(index)
            self.refresh()
        else:
            QMessageBox.warning(self, "Pop 실패", f"stash@{{{index}}} pop 실패\n충돌이 있을 수 있습니다.")

    def _on_drop(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        reply = QMessageBox.question(
            self, "Stash 삭제 확인",
            f"stash@{{{index}}}를 삭제할까요?\n(작업 내용이 영구 삭제됩니다)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self._mgr.drop_stash(index=index):
            self.stash_dropped.emit(index)
            self.refresh()
        else:
            QMessageBox.warning(self, "Drop 실패", f"stash@{{{index}}} 삭제 실패")

    def _on_new_stash(self) -> None:
        dialog = _StashMessageDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            message = dialog.message()
            entry = self._mgr.create_stash(message=message)
            if entry:
                self.stash_created.emit()
                self.refresh()
            else:
                QMessageBox.warning(
                    self, "Stash 생성 실패",
                    "변경사항이 없거나 stash 생성에 실패했습니다."
                )

    def _selected_index(self) -> int | None:
        item = self._list.currentItem()
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)


class _StashMessageDialog(QDialog):
    """stash 메시지 입력 다이얼로그."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("새 Stash 생성")
        self.setFixedWidth(420)
        self.setStyleSheet("background:#1a1a2e; color:#d4d4d4;")
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        lbl = QLabel("Stash 메시지 (선택사항)")
        lbl.setStyleSheet("color:#94a3b8; font-size:12px; font-weight:600;")
        layout.addWidget(lbl)

        self._input = QLineEdit()
        self._input.setPlaceholderText("WIP: 작업 중인 내용 설명...")
        self._input.setMinimumHeight(34)
        self._input.setStyleSheet(
            "QLineEdit { background:#252540; color:#e2e8f0; border:1px solid #3d3d6b;"
            "border-radius:6px; padding:4px 10px; font-size:13px; }"
            "QLineEdit:focus { border-color:#6366f1; }"
        )
        layout.addWidget(self._input)

        hint = QLabel("미입력 시 'WIP on <브랜치명>' 형식으로 자동 저장됩니다.")
        hint.setStyleSheet("color:#475569; font-size:11px;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("저장")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def message(self) -> str:
        return self._input.text().strip()
