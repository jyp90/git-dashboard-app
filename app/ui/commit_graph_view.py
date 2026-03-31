"""CommitGraphView — SourceTree 스타일 커밋 그래프 위젯."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QWheelEvent,
)
from PyQt6.QtWidgets import QAbstractScrollArea, QScrollBar, QWidget

from app.domain.models import GraphLayout, GraphNode
from app.ui.graph_renderer import GraphRenderer


class CommitGraphView(QAbstractScrollArea):
    """커밋 그래프를 렌더링하는 스크롤 가능한 커스텀 위젯.

    구조:
    ┌──────────────────────────────────────────────────────────┐
    │ [그래프 영역]  │  Hash  │  Message         │ Author │Date│
    │  ●─────●      │ a1b2c3 │ feat: login ...  │ jypark │1h │
    │  │     │      │ d4e5f6 │ fix: typo        │ jypark │2h │
    │  ●─┬───●      │ g7h8i9 │ Merge develop... │ jypark │3h │
    └──────────────────────────────────────────────────────────┘

    왼쪽: QPainter 그래프 (GraphRenderer 위임)
    오른쪽: 커밋 정보 (hash, message, author, date)
    클릭 시 commit_selected 시그널 → DiffViewer 연동
    """

    commit_selected = pyqtSignal(str)         # 커밋 해시
    commit_range_selected = pyqtSignal(str, str)  # 범위 선택

    # 컬럼 너비
    COL_HASH_W = 70
    COL_MSG_W = 400
    COL_AUTHOR_W = 140
    COL_DATE_W = 100

    # 헤더
    HEADER_HEIGHT = 24
    COL_BG = QColor("#252526")
    COL_TEXT = QColor("#cccccc")
    SEL_BG = QColor("#094771")
    ROW_ALT_BG = QColor("#1e1e1e")
    ROW_BG = QColor("#252526")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout: GraphLayout | None = None
        self._renderer = GraphRenderer()
        self._selected_hash: str | None = None
        self._hover_hash: str | None = None

        self.setMouseTracking(True)
        self.verticalScrollBar().setSingleStep(GraphRenderer.ROW_HEIGHT)
        self.setStyleSheet("background-color: #1e1e1e; border: none;")

    def set_graph(self, layout: GraphLayout) -> None:
        """GraphLayout을 설정하고 뷰를 갱신."""
        self._layout = layout
        if layout.nodes:
            total_h = len(layout.nodes) * GraphRenderer.ROW_HEIGHT + self.HEADER_HEIGHT
            self.verticalScrollBar().setRange(0, max(0, total_h - self.viewport().height()))
        self.viewport().update()

    def clear(self) -> None:
        """그래프 초기화."""
        self._layout = None
        self._selected_hash = None
        self.verticalScrollBar().setRange(0, 0)
        self.viewport().update()

    def selected_hash(self) -> str | None:
        return self._selected_hash

    # ─── 이벤트 오버라이드 ───────────────────────────────────────────────────

    def paintEvent(self, event: QPaintEvent) -> None:
        """전체 위젯 페인트."""
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        vp = self.viewport().rect()
        scroll_y = self.verticalScrollBar().value()

        # 배경
        painter.fillRect(vp, QColor("#1e1e1e"))

        if not self._layout or not self._layout.nodes:
            painter.setPen(QColor("#888888"))
            painter.drawText(vp, Qt.AlignmentFlag.AlignCenter, "No commits to display")
            return

        graph_w = self._renderer.graph_width(self._layout.max_columns)

        # 헤더
        self._draw_header(painter, graph_w, vp.width())

        # 행 영역 클립 (헤더 아래부터)
        painter.save()
        clip = QRect(0, self.HEADER_HEIGHT, vp.width(), vp.height() - self.HEADER_HEIGHT)
        painter.setClipRect(clip)

        # 그래프 영역 렌더링
        graph_clip = QRect(0, 0, graph_w, vp.height() - self.HEADER_HEIGHT)
        painter.translate(0, self.HEADER_HEIGHT)
        self._renderer.render(painter, self._layout, graph_clip, scroll_y, self._selected_hash)
        painter.translate(0, -self.HEADER_HEIGHT)

        # 커밋 정보 행 렌더링
        self._draw_rows(painter, graph_w, scroll_y, vp.width())

        painter.restore()
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """클릭 → 커밋 선택."""
        node = self._hit_test(event.pos())
        if node:
            self._selected_hash = node.commit.hash
            self.commit_selected.emit(node.commit.hash)
            self.viewport().update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """마우스 오버 → hover 효과."""
        node = self._hit_test(event.pos())
        new_hash = node.commit.hash if node else None
        if new_hash != self._hover_hash:
            self._hover_hash = new_hash
            self.viewport().update()

    # ─── 내부 렌더링 ─────────────────────────────────────────────────────────

    def _draw_header(self, painter: QPainter, graph_w: int, total_w: int) -> None:
        """컬럼 헤더 그리기."""
        rect = QRect(0, 0, total_w, self.HEADER_HEIGHT)
        painter.fillRect(rect, self.COL_BG)

        font = QFont("Helvetica", 11)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(self.COL_TEXT)

        x = graph_w
        for label, w in [("Hash", self.COL_HASH_W), ("Message", self.COL_MSG_W),
                          ("Author", self.COL_AUTHOR_W), ("Date", self.COL_DATE_W)]:
            painter.drawText(QRect(x + 4, 0, w, self.HEADER_HEIGHT), Qt.AlignmentFlag.AlignVCenter, label)
            x += w

    def _draw_rows(self, painter: QPainter, graph_w: int, scroll_y: int, total_w: int) -> None:
        """커밋 정보 행들 그리기."""
        if not self._layout:
            return

        rh = GraphRenderer.ROW_HEIGHT
        first = scroll_y // rh
        last = (scroll_y + self.viewport().height()) // rh + 1
        last = min(last, len(self._layout.nodes))

        font = QFont("Menlo", 11)
        painter.setFont(font)

        for i in range(first, last):
            node = self._layout.nodes[i]
            y = self.HEADER_HEIGHT + i * rh - scroll_y
            row_rect = QRect(graph_w, y, total_w - graph_w, rh)

            # 행 배경
            if node.commit.hash == self._selected_hash:
                painter.fillRect(row_rect.adjusted(-graph_w, 0, 0, 0), self.SEL_BG)
            elif i % 2 == 0:
                painter.fillRect(row_rect, self.ROW_ALT_BG)

            painter.setPen(QColor("#cccccc"))
            x = graph_w

            # Hash
            painter.drawText(QRect(x + 4, y, self.COL_HASH_W - 4, rh),
                             Qt.AlignmentFlag.AlignVCenter,
                             node.commit.short_hash)
            x += self.COL_HASH_W

            # Message
            msg = node.commit.summary
            painter.drawText(QRect(x + 4, y, self.COL_MSG_W - 4, rh),
                             Qt.AlignmentFlag.AlignVCenter,
                             msg)
            x += self.COL_MSG_W

            # Author
            painter.drawText(QRect(x + 4, y, self.COL_AUTHOR_W - 4, rh),
                             Qt.AlignmentFlag.AlignVCenter,
                             node.commit.author[:20])
            x += self.COL_AUTHOR_W

            # Date
            date_str = node.commit.date.strftime("%m/%d %H:%M")
            painter.drawText(QRect(x + 4, y, self.COL_DATE_W - 4, rh),
                             Qt.AlignmentFlag.AlignVCenter,
                             date_str)

    def _hit_test(self, pos: QPoint) -> GraphNode | None:
        """클릭 위치에서 GraphNode 반환."""
        if not self._layout:
            return None
        scroll_y = self.verticalScrollBar().value()
        y = pos.y() - self.HEADER_HEIGHT + scroll_y
        if y < 0:
            return None
        idx = y // GraphRenderer.ROW_HEIGHT
        if 0 <= idx < len(self._layout.nodes):
            return self._layout.nodes[idx]
        return None
