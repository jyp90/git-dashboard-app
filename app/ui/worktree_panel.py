"""WorktreePanel — git worktree 시각화 패널."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)

if TYPE_CHECKING:
    from app.controller.workflow_controller import WorkflowController


_STYLE_CARD = (
    "QFrame { background: #1a1a2e; border: none; border-radius: 8px; }"
)
_STYLE_MAIN = (
    "QFrame { background: #1c1c3a; border: none; border-radius: 8px; }"
)
_STYLE_LOCKED = (
    "QFrame { background: #1e1414; border: none; border-radius: 8px; }"
)


class _WorktreeCard(QFrame):
    """단일 worktree 카드 위젯."""

    def __init__(self, wt: dict, parent=None) -> None:
        super().__init__(parent)
        is_main = wt["is_main"]
        is_locked = wt["is_locked"]

        if is_main:
            self.setStyleSheet(_STYLE_MAIN)
        elif is_locked:
            self.setStyleSheet(_STYLE_LOCKED)
        else:
            self.setStyleSheet(_STYLE_CARD)
        self.setMinimumHeight(72)

        # 왼쪽 액센트 바 (색 블록으로 구분)
        accent_bar = QLabel()
        accent_bar.setFixedWidth(4)
        accent_color = "#0284c7" if is_main else ("#ef4444" if is_locked else "#334155")
        accent_bar.setStyleSheet(
            f"background: {accent_color}; border-radius: 2px; border: none;"
        )

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 16, 0)
        outer.setSpacing(0)
        outer.addWidget(accent_bar)

        inner = QHBoxLayout()
        inner.setContentsMargins(14, 12, 0, 12)
        inner.setSpacing(12)
        outer.addLayout(inner)

        # 아이콘
        icon = QLabel("🏠" if is_main else ("🔒" if is_locked else "🌿"))
        icon.setFont(QFont("Apple Color Emoji", 16))
        icon.setStyleSheet("border: none; background: transparent;")
        inner.addWidget(icon)

        # 텍스트 블록
        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        branch = wt.get("branch", "(unknown)")
        branch_lbl = QLabel(branch)
        branch_lbl.setStyleSheet(
            "color: #bae6fd; font-size: 13px; font-weight: 700;"
            "font-family: 'Menlo'; border: none; background: transparent;"
        )
        text_col.addWidget(branch_lbl)

        path = wt.get("path", "")
        path_lbl = QLabel(path)
        path_lbl.setStyleSheet(
            "color: #475569; font-size: 11px; border: none; background: transparent;"
        )
        path_lbl.setWordWrap(True)
        text_col.addWidget(path_lbl)

        inner.addLayout(text_col, 1)

        # 오른쪽: 커밋 해시 + 배지
        right = QVBoxLayout()
        right.setSpacing(4)
        right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        commit_lbl = QLabel(wt.get("commit", "???????"))
        commit_lbl.setStyleSheet(
            "color: #334155; font-size: 11px; font-family: 'Menlo';"
            "border: none; background: transparent;"
        )
        right.addWidget(commit_lbl, alignment=Qt.AlignmentFlag.AlignRight)

        if is_main:
            tag = QLabel("MAIN")
            tag.setStyleSheet(
                "background: #0c4a6e; color: #38bdf8;"
                "border-radius: 4px; padding: 2px 8px;"
                "font-size: 10px; font-weight: 700; border: none;"
            )
            right.addWidget(tag, alignment=Qt.AlignmentFlag.AlignRight)
        elif is_locked:
            tag = QLabel("LOCKED")
            tag.setStyleSheet(
                "background: #450a0a; color: #fca5a5;"
                "border-radius: 4px; padding: 2px 8px;"
                "font-size: 10px; font-weight: 700; border: none;"
            )
            right.addWidget(tag, alignment=Qt.AlignmentFlag.AlignRight)

        inner.addLayout(right)


class WorktreePanel(QWidget):
    """git worktree 목록 시각화 패널.

    연결된 모든 worktree를 카드 형태로 표시.
    새 worktree 추가 / 제거 버튼 제공.
    """

    worktree_changed = pyqtSignal()

    def __init__(self, controller: "WorkflowController", parent=None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        self.setStyleSheet("background: #0f0f1a; color: #d4d4d4;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # 헤더
        header_row = QHBoxLayout()
        title = QLabel("Worktree")
        title.setStyleSheet(
            "color: #e2e8f0; font-size: 15px; font-weight: 700; letter-spacing: 0.5px;"
        )
        header_row.addWidget(title)
        header_row.addStretch()

        refresh_btn = QPushButton("↻ 새로고침")
        refresh_btn.setFixedHeight(28)
        refresh_btn.setStyleSheet(
            "QPushButton { background: #252540; color: #38bdf8; border: 1px solid #3d3d6b; "
            "border-radius: 5px; padding: 2px 10px; font-size: 12px; }"
            "QPushButton:hover { background: #2d2d50; }"
        )
        refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(refresh_btn)

        add_btn = QPushButton("＋ 새 Worktree")
        add_btn.setFixedHeight(28)
        add_btn.setStyleSheet(
            "QPushButton { background: #1e3a5f; color: #60a5fa; border: 1px solid #1d4ed8; "
            "border-radius: 5px; padding: 2px 10px; font-size: 12px; }"
            "QPushButton:hover { background: #1e40af; color: #fff; }"
        )
        add_btn.clicked.connect(self._on_add)
        header_row.addWidget(add_btn)

        layout.addLayout(header_row)

        # 설명
        desc = QLabel(
            "각 worktree는 동일한 저장소의 다른 브랜치를 독립적으로 체크아웃합니다."
        )
        desc.setStyleSheet("color: #475569; font-size: 11px;")
        layout.addWidget(desc)

        # 카드 컨테이너
        self._cards_container = QVBoxLayout()
        self._cards_container.setSpacing(8)

        from PyQt6.QtWidgets import QScrollArea
        scroll_widget = QWidget()
        scroll_widget.setLayout(self._cards_container)
        scroll_widget.setStyleSheet("background: transparent;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_widget)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        layout.addWidget(scroll, 1)

        # 상태 레이블
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self._status_lbl)

    def refresh(self) -> None:
        """Worktree 목록 새로고침."""
        # 기존 카드 제거
        while self._cards_container.count():
            item = self._cards_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._controller.has_repository():
            empty = QLabel("저장소가 선택되지 않았습니다.")
            empty.setStyleSheet("color: #475569; padding: 20px;")
            self._cards_container.addWidget(empty)
            return

        worktrees = self._controller.get_worktrees()
        if not worktrees:
            empty = QLabel("연결된 worktree가 없습니다.")
            empty.setStyleSheet("color: #475569; padding: 20px;")
            self._cards_container.addWidget(empty)
            return

        for wt in worktrees:
            card = _WorktreeCard(wt)
            self._cards_container.addWidget(card)

        self._cards_container.addStretch()
        self._status_lbl.setText(f"총 {len(worktrees)}개 worktree")

    def _on_add(self) -> None:
        """새 worktree 추가."""
        if not self._controller.has_repository():
            QMessageBox.warning(self, "오류", "활성 저장소가 없습니다.")
            return

        branch, ok = QInputDialog.getText(
            self, "새 Worktree 추가", "브랜치 이름 (없으면 새 브랜치 생성):"
        )
        if not ok or not branch.strip():
            return

        import subprocess
        from pathlib import Path

        repo = self._controller.get_repository()
        if repo is None:
            return

        # 기본 경로: 저장소 부모 디렉토리에 브랜치명으로 폴더 생성
        parent = Path(repo.path).parent
        wt_path = str(parent / branch.strip().replace("/", "-"))

        try:
            result = subprocess.run(
                ["git", "worktree", "add", wt_path, branch.strip()],
                cwd=str(repo.path),
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                QMessageBox.information(
                    self, "성공", f"Worktree 생성 완료:\n{wt_path}"
                )
                self.refresh()
                self.worktree_changed.emit()
            else:
                QMessageBox.critical(
                    self, "실패", f"Worktree 생성 실패:\n{result.stderr}"
                )
        except Exception as e:
            QMessageBox.critical(self, "오류", str(e))
