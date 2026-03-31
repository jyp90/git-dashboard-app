"""MergeEditor — 3-Way Merge 충돌 해결 위젯."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.models import ConflictFile, ConflictRegion

if TYPE_CHECKING:
    from app.domain.conflict_resolver import ConflictResolver


# ─── 색상 ─────────────────────────────────────────────────────────────────────
OURS_BG   = QColor("#1e3a1e")   # 진한 초록
THEIRS_BG = QColor("#3a1e1e")   # 진한 빨강
BASE_BG   = QColor("#2a2a1e")   # 진한 노랑
CONFLICT_MARKER_FG = QColor("#ff6b6b")


class _ConflictItem(QListWidgetItem):
    """파일 목록의 한 항목."""
    def __init__(self, path: str, count: int) -> None:
        super().__init__(f"{path}  ({count} conflict{'s' if count > 1 else ''})")
        self.path = path
        self.count = count


class _RegionPanel(QWidget):
    """단일 충돌 영역 표시 패널 (ours / base / theirs + 해결 버튼)."""

    resolved = pyqtSignal(int, str, str)  # region_index, resolution, manual_content

    def __init__(self, region_index: int, region: ConflictRegion, parent=None) -> None:
        super().__init__(parent)
        self._region_index = region_index
        self._region = region
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        # 헤더
        header = QLabel(f"Conflict #{self._region_index + 1}")
        header.setStyleSheet("color: #ff6b6b; font-weight: bold; font-size: 12px;")
        layout.addWidget(header)

        # 3-패널
        row = QHBoxLayout()
        row.setSpacing(4)

        self._ours_edit   = self._make_editor("HEAD (ours)", OURS_BG, self._region.ours_content)
        self._base_edit   = self._make_editor("Base",         BASE_BG,  self._region.base_content)
        self._theirs_edit = self._make_editor("Theirs",       THEIRS_BG, self._region.theirs_content)

        row.addWidget(self._ours_edit)
        if self._region.base_content:
            row.addWidget(self._base_edit)
        row.addWidget(self._theirs_edit)
        layout.addLayout(row)

        # 해결 버튼
        btn_row = QHBoxLayout()
        ours_btn   = self._make_btn("Ours 선택",   "#2ecc71", lambda: self._emit("ours"))
        theirs_btn = self._make_btn("Theirs 선택", "#e74c3c", lambda: self._emit("theirs"))
        both_btn   = self._make_btn("Both",        "#f0b429", lambda: self._emit("both"))

        btn_row.addWidget(ours_btn)
        btn_row.addWidget(theirs_btn)
        btn_row.addWidget(both_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #3c3c3c;")
        layout.addWidget(line)

    def _make_editor(self, title: str, bg: QColor, lines: list[str]) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(2)

        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {bg.lighter(150).name()}; font-size: 10px;")
        vl.addWidget(lbl)

        edit = QTextEdit()
        edit.setReadOnly(True)
        edit.setFont(QFont("Menlo", 11))
        edit.setMaximumHeight(120)
        edit.setStyleSheet(
            f"QTextEdit {{ background: {bg.name()}; color: #d4d4d4; "
            f"border: 1px solid #3c3c3c; }}"
        )
        edit.setPlainText("".join(lines) if lines else "(empty)")
        vl.addWidget(edit)
        return w

    def _make_btn(self, text: str, color: str, handler) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(
            f"QPushButton {{ background: {color}; color: #fff; border: none; "
            f"padding: 3px 10px; border-radius: 3px; font-size: 11px; }}"
            f"QPushButton:hover {{ background: {color}; }}"
        )
        btn.clicked.connect(handler)
        return btn

    def _emit(self, resolution: str) -> None:
        self.resolved.emit(self._region_index, resolution, "")


class MergeEditor(QWidget):
    """머지 충돌 해결 전체 뷰.

    왼쪽: 충돌 파일 목록
    오른쪽: 선택 파일의 충돌 영역 목록 + 해결 버튼

    사용법:
        editor = MergeEditor(conflict_resolver, parent)
        editor.load_conflicts()
    """

    all_resolved = pyqtSignal(str)   # 파일 경로 (모든 충돌 해결 시)

    def __init__(self, resolver: "ConflictResolver", parent=None) -> None:
        super().__init__(parent)
        self._resolver = resolver
        self._current_file: str | None = None
        self._setup_ui()

    # ─── UI ─────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # 왼쪽: 파일 목록
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)

        file_label = QLabel("충돌 파일")
        file_label.setStyleSheet("color: #888; font-size: 11px;")
        ll.addWidget(file_label)

        self._file_list = QListWidget()
        self._file_list.setStyleSheet(
            "QListWidget { background: #252526; border: 1px solid #3c3c3c; }"
            "QListWidget::item:selected { background: #264f78; }"
        )
        self._file_list.currentItemChanged.connect(self._on_file_selected)
        ll.addWidget(self._file_list)

        # Mark Resolved 버튼
        self._mark_btn = QPushButton("Git Add (Resolved)")
        self._mark_btn.setEnabled(False)
        self._mark_btn.setStyleSheet(
            "QPushButton { background: #2ecc71; color: #fff; border: none; padding: 5px; }"
            "QPushButton:hover { background: #27ae60; }"
            "QPushButton:disabled { background: #3c3c3c; color: #666; }"
        )
        self._mark_btn.clicked.connect(self._on_mark_resolved)
        ll.addWidget(self._mark_btn)

        splitter.addWidget(left)

        # 오른쪽: 충돌 영역
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)

        region_label = QLabel("충돌 영역")
        region_label.setStyleSheet("color: #888; font-size: 11px;")
        rl.addWidget(region_label)

        self._region_scroll = QWidget()
        self._region_layout = QVBoxLayout(self._region_scroll)
        self._region_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._region_layout.setSpacing(0)

        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._region_scroll)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #3c3c3c; }")
        rl.addWidget(scroll)

        splitter.addWidget(right)
        splitter.setSizes([200, 520])

    # ─── 공개 API ────────────────────────────────────────────────────────────

    def load_conflicts(self) -> int:
        """충돌 파일 목록 로드. 반환값: 충돌 파일 수."""
        self._file_list.clear()
        paths = self._resolver.detect_conflicts()
        for path in paths:
            cf = self._resolver.parse_conflict(path)
            self._file_list.addItem(_ConflictItem(path, cf.total_conflicts))
        if self._file_list.count() > 0:
            self._file_list.setCurrentRow(0)
        return len(paths)

    # ─── 이벤트 ─────────────────────────────────────────────────────────────

    def _on_file_selected(self, current: QListWidgetItem | None, _) -> None:
        if not isinstance(current, _ConflictItem):
            return
        self._current_file = current.path
        self._render_regions(current.path)
        self._mark_btn.setEnabled(True)

    def _render_regions(self, file_path: str) -> None:
        # 기존 위젯 제거
        while self._region_layout.count():
            item = self._region_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cf = self._resolver.parse_conflict(file_path)
        if not cf.conflicts:
            lbl = QLabel("충돌 없음 — 이미 해결되었습니다.")
            lbl.setStyleSheet("color: #2ecc71; padding: 12px;")
            self._region_layout.addWidget(lbl)
            return

        for i, region in enumerate(cf.conflicts):
            panel = _RegionPanel(i, region)
            panel.resolved.connect(self._on_region_resolved)
            self._region_layout.addWidget(panel)

    def _on_region_resolved(self, region_index: int, resolution: str, _: str) -> None:
        if self._current_file is None:
            return
        try:
            self._resolver.resolve_region(self._current_file, region_index, resolution)
        except Exception as e:
            QMessageBox.critical(self, "해결 실패", str(e))
            return

        # 재렌더링
        self._render_regions(self._current_file)

        # 남은 충돌 체크
        cf = self._resolver.parse_conflict(self._current_file)
        if cf.total_conflicts == 0:
            self.all_resolved.emit(self._current_file)

    def _on_mark_resolved(self) -> None:
        if self._current_file is None:
            return
        cf = self._resolver.parse_conflict(self._current_file)
        if cf.total_conflicts > 0:
            QMessageBox.warning(
                self,
                "미해결 충돌",
                f"{cf.total_conflicts}개의 충돌이 남아 있습니다.\n모두 해결 후 git add 하세요.",
            )
            return
        try:
            self._resolver.mark_resolved(self._current_file)
            QMessageBox.information(self, "완료", f"{self._current_file} git add 완료")
            self.load_conflicts()
        except RuntimeError as e:
            QMessageBox.critical(self, "오류", str(e))
