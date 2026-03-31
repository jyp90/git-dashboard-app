"""GraphRenderer — QPainter 기반 커밋 그래프 렌더링 엔진."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
)

from app.domain.models import GraphEdge, GraphLayout, GraphNode


class GraphRenderer:
    """QPainter 기반 커밋 그래프 렌더링 엔진.

    렌더링 요소:
    1. Lane Lines: 브랜치별 세로 직선 (컬러)
    2. Nodes: 커밋 = 원, 머지 = 큰 원
    3. Edges: 부모-자식 연결선 (직선/베지어 곡선)
    4. Labels: 브랜치명 태그, HEAD 마커
    5. Selection: 선택된 커밋 하이라이트
    """

    # 레이아웃 상수
    ROW_HEIGHT = 32
    GRAPH_LANE_WIDTH = 16
    NODE_RADIUS = 5
    MERGE_NODE_RADIUS = 7
    GRAPH_LEFT_MARGIN = 10
    TEXT_LEFT_OFFSET = 8
    LABEL_HEIGHT = 18
    LABEL_RADIUS = 4
    LABEL_MAX_CHARS = 14       # 브랜치 라벨 최대 문자 수
    LABEL_RESERVE_W = 90       # 브랜치 라벨 예약 공간 (px)

    def render(
        self,
        painter: QPainter,
        layout: GraphLayout,
        viewport_rect: QRect,
        scroll_offset: int,
        selected_hash: str | None = None,
    ) -> None:
        """전체 그래프를 painter에 렌더링.

        Args:
            painter: QPainter 인스턴스
            layout: GraphLayout (CommitGraphBuilder 결과)
            viewport_rect: 현재 표시 영역
            scroll_offset: 세로 스크롤 오프셋 (px)
            selected_hash: 선택된 커밋 해시
        """
        if not layout.nodes:
            return

        first_row = scroll_offset // self.ROW_HEIGHT
        last_row = (scroll_offset + viewport_rect.height()) // self.ROW_HEIGHT + 1
        last_row = min(last_row, len(layout.nodes))

        # 각 노드의 y 좌표 계산 (전체 범위)
        row_y: dict[str, int] = {}
        for i, node in enumerate(layout.nodes):
            row_y[node.commit.hash] = i * self.ROW_HEIGHT + self.ROW_HEIGHT // 2

        # 엣지 그리기
        self._draw_edges(painter, layout.edges, row_y, layout.branch_colors, scroll_offset, viewport_rect)

        # 노드 그리기 (viewport 내 노드만)
        visible_nodes = layout.nodes[first_row:last_row]
        self._draw_nodes(painter, visible_nodes, row_y, layout.branch_colors, scroll_offset, selected_hash)

    def _draw_edges(
        self,
        painter: QPainter,
        edges: list[GraphEdge],
        row_y: dict[str, int],
        branch_colors: dict[int, str],
        scroll_offset: int,
        viewport_rect: QRect,
    ) -> None:
        """엣지 렌더링."""
        for edge in edges:
            if edge.child_hash not in row_y or edge.parent_hash not in row_y:
                continue

            child_y = row_y[edge.child_hash] - scroll_offset
            parent_y = row_y[edge.parent_hash] - scroll_offset

            # 화면 밖 엣지 컬링
            min_y = min(child_y, parent_y)
            max_y = max(child_y, parent_y)
            if max_y < 0 or min_y > viewport_rect.height():
                continue

            color = QColor(branch_colors.get(edge.color_index, "#6366f1"))
            pen = QPen(color, 2, Qt.PenStyle.SolidLine)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)

            child_x = self._lane_x(edge.column_from)
            parent_x = self._lane_x(edge.column_to)

            if edge.edge_type == "straight":
                painter.drawLine(child_x, child_y, parent_x, parent_y)
            else:
                self._bezier_curve(painter, child_x, child_y, parent_x, parent_y)

    def _draw_nodes(
        self,
        painter: QPainter,
        nodes: list[GraphNode],
        row_y: dict[str, int],
        branch_colors: dict[int, str],
        scroll_offset: int,
        selected_hash: str | None,
    ) -> None:
        """노드 렌더링."""
        for node in nodes:
            y = row_y[node.commit.hash] - scroll_offset
            x = self._lane_x(node.column)
            color = QColor(branch_colors.get(node.color_index, "#6366f1"))
            radius = self.MERGE_NODE_RADIUS if node.is_merge else self.NODE_RADIUS

            # 선택된 노드 글로우 효과
            if selected_hash and node.commit.hash == selected_hash:
                glow = QPen(color, 1)
                glow_color = QColor(color)
                glow_color.setAlpha(60)
                painter.setPen(glow)
                painter.setBrush(QBrush(glow_color))
                painter.drawEllipse(QPoint(x, y), radius + 4, radius + 4)

            # 노드 원
            painter.setPen(QPen(color, 2))
            painter.setBrush(QBrush(color if not node.is_merge else QColor("#1e1e1e")))
            painter.drawEllipse(QPoint(x, y), radius, radius)

            # 머지 노드: 내부 작은 원
            if node.is_merge:
                painter.setBrush(QBrush(color))
                painter.drawEllipse(QPoint(x, y), radius - 3, radius - 3)

            # 브랜치 팁 라벨
            if node.is_branch_tip and node.branch_name:
                label_x = x + radius + 4
                self._draw_branch_label(painter, node.branch_name, label_x, y, color)

    def _draw_branch_label(
        self,
        painter: QPainter,
        branch_name: str,
        x: int,
        y: int,
        color: QColor,
    ) -> None:
        """브랜치명 태그 (둥근 사각형 배지)."""
        # 긴 이름 truncate
        if len(branch_name) > self.LABEL_MAX_CHARS:
            branch_name = branch_name[: self.LABEL_MAX_CHARS - 1] + "…"
        font = QFont("Menlo", 10)
        painter.setFont(font)
        fm = painter.fontMetrics()
        text_w = fm.horizontalAdvance(branch_name)
        padding = 4

        rect = QRect(x, y - self.LABEL_HEIGHT // 2, text_w + padding * 2, self.LABEL_HEIGHT)

        # 배지 배경
        bg = QColor(color)
        bg.setAlpha(40)
        painter.setPen(QPen(color, 1))
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(rect, self.LABEL_RADIUS, self.LABEL_RADIUS)

        # 텍스트
        painter.setPen(QPen(color))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, branch_name)

    def _bezier_curve(
        self,
        painter: QPainter,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
    ) -> None:
        """QPainterPath를 이용한 베지어 곡선."""
        path = QPainterPath()
        path.moveTo(x1, y1)
        mid_y = (y1 + y2) // 2
        path.cubicTo(x1, mid_y, x2, mid_y, x2, y2)
        painter.drawPath(path)

    def graph_width(self, max_columns: int) -> int:
        """그래프 영역 총 너비 계산 (브랜치 라벨 공간 포함)."""
        return (
            self.GRAPH_LEFT_MARGIN
            + max_columns * self.GRAPH_LANE_WIDTH
            + self.TEXT_LEFT_OFFSET
            + self.LABEL_RESERVE_W
        )

    def _lane_x(self, lane: int) -> int:
        """lane 인덱스 → x 좌표."""
        return self.GRAPH_LEFT_MARGIN + lane * self.GRAPH_LANE_WIDTH + self.GRAPH_LANE_WIDTH // 2
