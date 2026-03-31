"""RebaseDialog — Interactive Rebase GUI (drag & drop 커밋 순서 변경)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from app.domain.models import RebasePlan, RebaseStep

if TYPE_CHECKING:
    from app.domain.rebase_orchestrator import RebaseOrchestrator


# action 별 색상
ACTION_COLORS = {
    "pick":   "#4a9eff",
    "reword": "#f0b429",
    "squash": "#9b59b6",
    "fixup":  "#e67e22",
    "drop":   "#e74c3c",
    "edit":   "#2ecc71",
}

VALID_ACTIONS = ["pick", "reword", "squash", "fixup", "drop", "edit"]


class _StepItem(QListWidgetItem):
    """커밋 한 줄 = QListWidgetItem 확장."""

    def __init__(self, step: RebaseStep) -> None:
        super().__init__()
        self.step = step
        self._refresh()

    def _refresh(self) -> None:
        action = self.step.action
        msg = (self.step.new_message or self.step.original_message).split("\n")[0][:60]
        short = self.step.commit_hash[:7]
        self.setText(f"[{action:6s}] {short}  {msg}")
        color = ACTION_COLORS.get(action, "#aaaaaa")
        self.setForeground(QColor(color))

    def update_action(self, action: str) -> None:
        self.step = RebaseStep(
            action=action,
            commit_hash=self.step.commit_hash,
            original_message=self.step.original_message,
            new_message=self.step.new_message,
        )
        self._refresh()

    def update_message(self, message: str) -> None:
        self.step = RebaseStep(
            action=self.step.action,
            commit_hash=self.step.commit_hash,
            original_message=self.step.original_message,
            new_message=message or None,
        )
        self._refresh()


class RebaseDialog(QDialog):
    """Interactive Rebase 계획 편집 다이얼로그.

    사용법:
        dialog = RebaseDialog(orchestrator, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            plan = dialog.get_plan()
            orchestrator.execute(plan)
    """

    rebase_executed = pyqtSignal(bool)  # True=success

    def __init__(self, orchestrator: "RebaseOrchestrator", parent=None) -> None:
        super().__init__(parent)
        self._orchestrator = orchestrator
        self._plan: RebasePlan | None = None
        self._setup_ui()
        self._load_plan()

    # ─── UI 구성 ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle("Interactive Rebase")
        self.setMinimumSize(720, 500)
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 상단 안내
        hint = QLabel(
            "드래그로 순서 변경 | 더블클릭으로 메시지 편집 | 우측 패널에서 action 선택"
        )
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)

        # 인라인 경고 레이블 (dirty tree 등 오류 표시)
        self._warn_label = QLabel("")
        self._warn_label.setStyleSheet(
            "background: #3b1f00; color: #fbbf24; border: 1px solid #78350f;"
            "border-radius: 6px; padding: 6px 12px; font-size: 12px;"
        )
        self._warn_label.setVisible(False)
        self._warn_label.setWordWrap(True)
        layout.addWidget(self._warn_label)

        # 중앙 스플리터
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        # 왼쪽: 커밋 목록
        self._list = QListWidget()
        self._list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.setFont(QFont("Menlo", 12))
        self._list.setStyleSheet(
            "QListWidget { background: #252526; border: 1px solid #3c3c3c; }"
            "QListWidget::item:selected { background: #264f78; }"
        )
        self._list.currentItemChanged.connect(self._on_item_selected)
        self._list.itemDoubleClicked.connect(self._on_double_click)
        splitter.addWidget(self._list)

        # 오른쪽: 편집 패널
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)

        action_label = QLabel("Action:")
        action_label.setStyleSheet("color: #888; font-size: 11px;")
        right_layout.addWidget(action_label)

        self._action_combo = QComboBox()
        self._action_combo.addItems(VALID_ACTIONS)
        self._action_combo.setStyleSheet(
            "QComboBox { background: #3c3c3c; color: #d4d4d4; border: 1px solid #555; padding: 4px; }"
        )
        self._action_combo.currentTextChanged.connect(self._on_action_changed)
        right_layout.addWidget(self._action_combo)

        msg_label = QLabel("커밋 메시지 (reword 시 편집):")
        msg_label.setStyleSheet("color: #888; font-size: 11px; margin-top: 8px;")
        right_layout.addWidget(msg_label)

        self._msg_edit = QTextEdit()
        self._msg_edit.setFont(QFont("Menlo", 12))
        self._msg_edit.setStyleSheet(
            "QTextEdit { background: #252526; color: #d4d4d4; border: 1px solid #3c3c3c; }"
        )
        self._msg_edit.textChanged.connect(self._on_message_changed)
        right_layout.addWidget(self._msg_edit, 1)

        # 이동 버튼
        btn_row = QHBoxLayout()
        up_btn = QPushButton("↑ 위로")
        down_btn = QPushButton("↓ 아래로")
        up_btn.clicked.connect(self._move_up)
        down_btn.clicked.connect(self._move_down)
        for b in (up_btn, down_btn):
            b.setStyleSheet(
                "QPushButton { background: #3c3c3c; color: #d4d4d4; border: 1px solid #555; padding: 4px 10px; }"
                "QPushButton:hover { background: #4a4a4a; }"
            )
        btn_row.addWidget(up_btn)
        btn_row.addWidget(down_btn)
        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        splitter.addWidget(right)
        splitter.setSizes([480, 240])

        # 하단 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Rebase 실행")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._editing = False  # 메시지 편집 루프 방지

    # ─── 데이터 로드 ─────────────────────────────────────────────────────────

    def _load_plan(self) -> None:
        try:
            self._plan = self._orchestrator.prepare()
        except ValueError as e:
            self._warn_label.setText(f"⚠  {e}")
            self._warn_label.setVisible(True)
            self._plan = None
            return

        for step in self._plan.steps:
            self._list.addItem(_StepItem(step))

        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    # ─── 이벤트 ─────────────────────────────────────────────────────────────

    def _on_item_selected(self, current: QListWidgetItem | None, _) -> None:
        if not isinstance(current, _StepItem):
            return
        self._editing = True
        idx = VALID_ACTIONS.index(current.step.action) if current.step.action in VALID_ACTIONS else 0
        self._action_combo.setCurrentIndex(idx)
        msg = current.step.new_message or current.step.original_message
        self._msg_edit.setPlainText(msg)
        self._editing = False

    def _on_double_click(self, item: QListWidgetItem) -> None:
        if isinstance(item, _StepItem) and item.step.action == "pick":
            item.update_action("reword")
            self._action_combo.setCurrentText("reword")

    def _on_action_changed(self, action: str) -> None:
        if self._editing:
            return
        item = self._list.currentItem()
        if isinstance(item, _StepItem):
            item.update_action(action)

    def _on_message_changed(self) -> None:
        if self._editing:
            return
        item = self._list.currentItem()
        if isinstance(item, _StepItem) and item.step.action == "reword":
            item.update_message(self._msg_edit.toPlainText())

    def _move_up(self) -> None:
        row = self._list.currentRow()
        if row <= 0:
            return
        item = self._list.takeItem(row)
        self._list.insertItem(row - 1, item)
        self._list.setCurrentRow(row - 1)

    def _move_down(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= self._list.count() - 1:
            return
        item = self._list.takeItem(row)
        self._list.insertItem(row + 1, item)
        self._list.setCurrentRow(row + 1)

    # ─── 실행 ────────────────────────────────────────────────────────────────

    def _on_accept(self) -> None:
        plan = self.get_plan()
        if plan is None:
            self.reject()
            return
        self.accept()

    def get_plan(self) -> RebasePlan | None:
        """현재 편집된 RebasePlan 반환."""
        if self._plan is None:
            return None
        steps = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if isinstance(item, _StepItem):
                steps.append(item.step)
        return RebasePlan(base_commit=self._plan.base_commit, steps=steps)
