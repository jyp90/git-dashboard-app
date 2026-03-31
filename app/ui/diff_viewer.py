"""DiffViewer — 파일 변경사항 시각화 위젯."""
from __future__ import annotations

from enum import Enum

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.domain.models import DiffHunk, DiffLine, FileDiff
from app.ui.syntax_highlighter import SyntaxHighlighter


class DiffViewer(QWidget):
    """파일 변경사항을 시각적으로 표시하는 위젯.

    모드:
    1. Inline (Unified): 단일 패널, 삭제=빨강 배경, 추가=초록 배경
    2. Side-by-Side: 좌=원본, 우=변경본, 동기 스크롤

    구조:
    ┌─────────────────────────────────────────┐
    │ [Inline ◉] [Side-by-Side ○]  📄 file.py │
    ├─────────────────────────────────────────┤
    │  10 │  10 │   def foo():                │
    │  11 │     │ - old_line = True  ← 빨강   │
    │     │  11 │ + new_line = False ← 초록   │
    └─────────────────────────────────────────┘
    """

    class ViewMode(Enum):
        INLINE = "inline"
        SIDE_BY_SIDE = "side_by_side"

    # 색상 (다크 테마)
    COLOR_ADD_BG = QColor("#1e3a1e")
    COLOR_DEL_BG = QColor("#3a1e1e")
    COLOR_ADD_FG = QColor("#7ec8a0")
    COLOR_DEL_FG = QColor("#f47067")
    COLOR_HUNK_BG = QColor("#1c2d3a")
    COLOR_LINE_NO = QColor("#858585")

    file_selected = pyqtSignal(str)  # 파일 경로 선택 시그널

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_diff: FileDiff | None = None
        self._mode = self.ViewMode.INLINE
        self._highlighter_left: SyntaxHighlighter | None = None
        self._highlighter_right: SyntaxHighlighter | None = None
        self._setup_ui()

    def set_diff(self, file_diff: FileDiff) -> None:
        """FileDiff를 뷰어에 표시."""
        self._current_diff = file_diff
        self._file_label.setText(f"📄 {file_diff.new_path}")
        language = SyntaxHighlighter.detect_language(file_diff.new_path)
        if self._mode == self.ViewMode.INLINE:
            self._render_inline(file_diff, language)
        else:
            self._render_side_by_side(file_diff, language)

    def set_view_mode(self, mode: "DiffViewer.ViewMode") -> None:
        """뷰 모드 변경."""
        self._mode = mode
        if mode == self.ViewMode.INLINE:
            self._btn_inline.setChecked(True)
            self._editor_right.hide()
            self._splitter.setSizes([1, 0])
        else:
            self._btn_side.setChecked(True)
            self._editor_right.show()
            self._splitter.setSizes([1, 1])

        if self._current_diff:
            self.set_diff(self._current_diff)

    def clear(self) -> None:
        """뷰어 초기화."""
        self._editor_left.clear()
        self._editor_right.clear()
        self._file_label.setText("")
        self._current_diff = None

    # ─── UI 초기화 ───────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 툴바
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)

        self._btn_inline = QPushButton("Inline")
        self._btn_inline.setCheckable(True)
        self._btn_inline.setChecked(True)
        self._btn_inline.clicked.connect(lambda: self.set_view_mode(self.ViewMode.INLINE))

        self._btn_side = QPushButton("Side-by-Side")
        self._btn_side.setCheckable(True)
        self._btn_side.clicked.connect(lambda: self.set_view_mode(self.ViewMode.SIDE_BY_SIDE))

        self._file_label = QLabel("")
        self._file_label.setStyleSheet("color: #cccccc; padding: 0 8px;")

        toolbar_layout.addWidget(self._btn_inline)
        toolbar_layout.addWidget(self._btn_side)
        toolbar_layout.addWidget(self._file_label)
        toolbar_layout.addStretch()
        layout.addWidget(toolbar)

        # 에디터 영역
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        self._editor_left = self._make_editor()
        self._editor_right = self._make_editor()
        self._editor_right.hide()

        self._splitter.addWidget(self._editor_left)
        self._splitter.addWidget(self._editor_right)
        layout.addWidget(self._splitter)

        # 동기 스크롤 연결
        self._editor_left.verticalScrollBar().valueChanged.connect(
            self._editor_right.verticalScrollBar().setValue
        )
        self._editor_right.verticalScrollBar().valueChanged.connect(
            self._editor_left.verticalScrollBar().setValue
        )

        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'JetBrains Mono', 'Menlo', 'Monaco', monospace;
                font-size: 13px;
                border: none;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555;
                padding: 2px 8px;
                border-radius: 3px;
            }
            QPushButton:checked {
                background-color: #0e639c;
                border-color: #0e639c;
            }
        """)

    def _make_editor(self) -> QPlainTextEdit:
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Menlo", 12)
        font.setFixedPitch(True)
        editor.setFont(font)
        return editor

    # ─── 렌더링 ──────────────────────────────────────────────────────────────

    def _render_inline(self, file_diff: FileDiff, language: str = "plain") -> None:
        """Inline 모드 렌더링."""
        self._editor_left.clear()
        cursor = self._editor_left.textCursor()

        if self._highlighter_left:
            self._highlighter_left.setDocument(None)
        self._highlighter_left = SyntaxHighlighter(self._editor_left.document(), language)

        if file_diff.is_binary:
            self._append_text(cursor, "  [Binary file]\n", QColor("#888888"))
            return

        for hunk in file_diff.hunks:
            # hunk 헤더
            self._append_text(cursor, hunk.header + "\n", self.COLOR_HUNK_BG, bg=self.COLOR_HUNK_BG)
            for line in hunk.lines:
                self._append_diff_line(cursor, line)

        self._editor_left.setTextCursor(QTextCursor(self._editor_left.document()))

    def _render_side_by_side(self, file_diff: FileDiff, language: str = "plain") -> None:
        """Side-by-Side 모드 렌더링."""
        self._editor_left.clear()
        self._editor_right.clear()

        if self._highlighter_left:
            self._highlighter_left.setDocument(None)
        if self._highlighter_right:
            self._highlighter_right.setDocument(None)

        self._highlighter_left = SyntaxHighlighter(self._editor_left.document(), language)
        self._highlighter_right = SyntaxHighlighter(self._editor_right.document(), language)

        if file_diff.is_binary:
            for editor in (self._editor_left, self._editor_right):
                c = editor.textCursor()
                self._append_text(c, "  [Binary file]\n", QColor("#888888"))
            return

        cursor_l = self._editor_left.textCursor()
        cursor_r = self._editor_right.textCursor()

        for hunk in file_diff.hunks:
            self._append_text(cursor_l, hunk.header + "\n", self.COLOR_HUNK_BG, bg=self.COLOR_HUNK_BG)
            self._append_text(cursor_r, hunk.header + "\n", self.COLOR_HUNK_BG, bg=self.COLOR_HUNK_BG)

            for line in hunk.lines:
                if line.type == "add":
                    self._append_text(cursor_l, "\n", QColor("#d4d4d4"))  # 빈 줄 (좌측)
                    self._append_text(cursor_r, f"+ {line.content}\n", self.COLOR_ADD_FG, bg=self.COLOR_ADD_BG)
                elif line.type == "delete":
                    self._append_text(cursor_l, f"- {line.content}\n", self.COLOR_DEL_FG, bg=self.COLOR_DEL_BG)
                    self._append_text(cursor_r, "\n", QColor("#d4d4d4"))  # 빈 줄 (우측)
                else:
                    text = f"  {line.content}\n"
                    self._append_text(cursor_l, text, QColor("#d4d4d4"))
                    self._append_text(cursor_r, text, QColor("#d4d4d4"))

    def _append_diff_line(self, cursor: QTextCursor, line: DiffLine) -> None:
        """diff 라인 하나를 커서에 추가."""
        if line.type == "add":
            prefix = "+ "
            fg = self.COLOR_ADD_FG
            bg = self.COLOR_ADD_BG
        elif line.type == "delete":
            prefix = "- "
            fg = self.COLOR_DEL_FG
            bg = self.COLOR_DEL_BG
        elif line.type == "context":
            prefix = "  "
            fg = QColor("#d4d4d4")
            bg = None
        else:
            prefix = "  "
            fg = QColor("#888888")
            bg = None

        self._append_text(cursor, f"{prefix}{line.content}\n", fg, bg=bg)

    def _append_text(
        self,
        cursor: QTextCursor,
        text: str,
        fg: QColor,
        bg: QColor | None = None,
    ) -> None:
        """서식 있는 텍스트를 커서에 추가."""
        fmt = QTextCharFormat()
        fmt.setForeground(fg)
        if bg:
            fmt.setBackground(bg)
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text, fmt)
