"""CommitGraphBuilder 단위 테스트."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.domain.commit_graph_builder import CommitGraphBuilder
from app.domain.models import GraphLayout, GraphNode, GraphEdge


# ─── 헬퍼 ───────────────────────────────────────────────────────────────────

def _make_commit(hash_: str, parents: list[str], message: str = "msg") -> dict:
    return {
        "hash": hash_,
        "short_hash": hash_[:7],
        "message": message,
        "author": "author",
        "date": datetime(2024, 1, 1),
        "parents": parents,
    }


def _make_builder(commits: list[dict], refs: dict | None = None) -> CommitGraphBuilder:
    repo = MagicMock()
    repo.get_commit_log_with_parents.return_value = commits
    repo.get_all_refs.return_value = refs or {}
    return CommitGraphBuilder(repo)


# ─── 빈 저장소 ───────────────────────────────────────────────────────────────

class TestEmptyRepository:
    def test_empty_commits_returns_empty_layout(self):
        builder = _make_builder([])
        layout = builder.build()
        assert isinstance(layout, GraphLayout)
        assert layout.nodes == []
        assert layout.edges == []
        assert layout.max_columns == 0


# ─── 단일 직선 히스토리 ──────────────────────────────────────────────────────

class TestLinearHistory:
    """A ← B ← C (C가 최신)"""

    def setup_method(self):
        commits = [
            _make_commit("C", ["B"]),
            _make_commit("B", ["A"]),
            _make_commit("A", []),
        ]
        self.builder = _make_builder(commits)
        self.layout = self.builder.build()

    def test_returns_three_nodes(self):
        assert len(self.layout.nodes) == 3

    def test_all_nodes_in_lane_0(self):
        for node in self.layout.nodes:
            assert node.column == 0

    def test_has_two_edges(self):
        assert len(self.layout.edges) == 2

    def test_all_edges_straight(self):
        for edge in self.layout.edges:
            assert edge.edge_type == "straight"

    def test_max_columns_is_1(self):
        assert self.layout.max_columns == 1

    def test_nodes_have_correct_hashes(self):
        hashes = [n.commit.hash for n in self.layout.nodes]
        assert "A" in hashes
        assert "B" in hashes
        assert "C" in hashes


# ─── 머지 커밋 ───────────────────────────────────────────────────────────────

class TestMergeCommit:
    """
    M ← A, B  (M이 A와 B를 머지한 커밋)
    A ← base
    B ← base
    """

    def setup_method(self):
        commits = [
            _make_commit("M", ["A", "B"]),   # merge commit
            _make_commit("A", ["base"]),
            _make_commit("B", ["base"]),
            _make_commit("base", []),
        ]
        self.builder = _make_builder(commits)
        self.layout = self.builder.build()

    def test_merge_node_is_marked(self):
        merge_node = next(n for n in self.layout.nodes if n.commit.hash == "M")
        assert merge_node.is_merge is True

    def test_non_merge_nodes_not_marked(self):
        non_merge = [n for n in self.layout.nodes if n.commit.hash != "M"]
        assert all(not n.is_merge for n in non_merge)

    def test_merge_commit_has_two_parents(self):
        merge_node = next(n for n in self.layout.nodes if n.commit.hash == "M")
        assert len(merge_node.parents) == 2

    def test_edges_include_merge_in(self):
        edge_types = {e.edge_type for e in self.layout.edges}
        assert "merge_in" in edge_types

    def test_max_columns_at_least_2(self):
        assert self.layout.max_columns >= 2


# ─── 분기 히스토리 ───────────────────────────────────────────────────────────

class TestBranchHistory:
    """
    main:    A ← B ← C
    feature:     └── D ← E
    (D, E는 B에서 분기)
    """

    def setup_method(self):
        commits = [
            _make_commit("C", ["B"]),
            _make_commit("E", ["D"]),
            _make_commit("B", ["A"]),
            _make_commit("D", ["B"]),
            _make_commit("A", []),
        ]
        self.builder = _make_builder(commits)
        self.layout = self.builder.build()

    def test_five_nodes_returned(self):
        assert len(self.layout.nodes) == 5

    def test_b_and_d_different_lanes(self):
        node_b = next(n for n in self.layout.nodes if n.commit.hash == "B")
        node_d = next(n for n in self.layout.nodes if n.commit.hash == "D")
        # B는 lane 0, D는 다른 lane
        assert node_b.column != node_d.column

    def test_at_least_two_columns(self):
        assert self.layout.max_columns >= 2


# ─── 레인 할당 알고리즘 ──────────────────────────────────────────────────────

class TestLaneAssignment:
    def test_first_commit_in_lane_0(self):
        commits = [_make_commit("A", [])]
        builder = _make_builder(commits)
        layout = builder.build()
        assert layout.nodes[0].column == 0

    def test_linear_all_same_lane(self):
        commits = [
            _make_commit("C", ["B"]),
            _make_commit("B", ["A"]),
            _make_commit("A", []),
        ]
        builder = _make_builder(commits)
        layout = builder.build()
        cols = [n.column for n in layout.nodes]
        assert all(c == 0 for c in cols)

    def test_merge_parent_gets_new_lane(self):
        commits = [
            _make_commit("M", ["A", "B"]),
            _make_commit("A", []),
            _make_commit("B", []),
        ]
        builder = _make_builder(commits)
        layout = builder.build()
        node_a = next(n for n in layout.nodes if n.commit.hash == "A")
        node_b = next(n for n in layout.nodes if n.commit.hash == "B")
        # A와 B는 다른 lane에 있어야 함
        assert node_a.column != node_b.column

    def test_no_duplicate_lanes(self):
        """같은 row의 커밋들이 서로 다른 lane을 사용해야 함."""
        commits = [
            _make_commit("M", ["A", "B"]),
            _make_commit("A", ["root"]),
            _make_commit("B", ["root"]),
            _make_commit("root", []),
        ]
        builder = _make_builder(commits)
        layout = builder.build()
        # 모든 노드의 lane_map에서 중복 없는지 확인
        lane_by_hash = {n.commit.hash: n.column for n in layout.nodes}
        # A와 B는 다른 lane
        assert lane_by_hash["A"] != lane_by_hash["B"]


# ─── 엣지 생성 ───────────────────────────────────────────────────────────────

class TestEdgeGeneration:
    def test_linear_edges_connect_parent_child(self):
        commits = [
            _make_commit("B", ["A"]),
            _make_commit("A", []),
        ]
        builder = _make_builder(commits)
        layout = builder.build()
        assert len(layout.edges) == 1
        edge = layout.edges[0]
        assert edge.child_hash == "B"
        assert edge.parent_hash == "A"

    def test_edge_type_straight_for_same_lane(self):
        commits = [
            _make_commit("B", ["A"]),
            _make_commit("A", []),
        ]
        builder = _make_builder(commits)
        layout = builder.build()
        assert layout.edges[0].edge_type == "straight"

    def test_root_commit_no_edges(self):
        commits = [_make_commit("A", [])]
        builder = _make_builder(commits)
        layout = builder.build()
        assert len(layout.edges) == 0

    def test_merge_has_merge_in_edge(self):
        commits = [
            _make_commit("M", ["A", "B"]),
            _make_commit("A", []),
            _make_commit("B", []),
        ]
        builder = _make_builder(commits)
        layout = builder.build()
        edge_types = {e.edge_type for e in layout.edges}
        assert "merge_in" in edge_types


# ─── 브랜치 팁 감지 ──────────────────────────────────────────────────────────

class TestBranchTips:
    def test_branch_tip_marked(self):
        commits = [
            _make_commit("C", ["B"]),
            _make_commit("B", ["A"]),
            _make_commit("A", []),
        ]
        refs = {"refs/heads/main": "C"}
        builder = _make_builder(commits, refs=refs)
        layout = builder.build()
        node_c = next(n for n in layout.nodes if n.commit.hash == "C")
        assert node_c.is_branch_tip is True
        assert node_c.branch_name == "main"

    def test_non_tip_not_marked(self):
        commits = [
            _make_commit("C", ["B"]),
            _make_commit("B", ["A"]),
            _make_commit("A", []),
        ]
        refs = {"refs/heads/main": "C"}
        builder = _make_builder(commits, refs=refs)
        layout = builder.build()
        node_b = next(n for n in layout.nodes if n.commit.hash == "B")
        assert node_b.is_branch_tip is False

    def test_no_refs_no_branch_tips(self):
        commits = [_make_commit("A", [])]
        builder = _make_builder(commits, refs={})
        layout = builder.build()
        assert not layout.nodes[0].is_branch_tip


# ─── 색상 팔레트 ─────────────────────────────────────────────────────────────

class TestColorPalette:
    def test_branch_colors_populated(self):
        commits = [
            _make_commit("B", ["A"]),
            _make_commit("A", []),
        ]
        builder = _make_builder(commits)
        layout = builder.build()
        assert len(layout.branch_colors) > 0

    def test_color_values_are_hex_strings(self):
        commits = [_make_commit("A", [])]
        builder = _make_builder(commits)
        layout = builder.build()
        for color in layout.branch_colors.values():
            assert color.startswith("#")
            assert len(color) == 7

    def test_color_index_within_palette(self):
        commits = [_make_commit("A", [])]
        builder = _make_builder(commits)
        layout = builder.build()
        for node in layout.nodes:
            assert 0 <= node.color_index < len(CommitGraphBuilder.BRANCH_COLORS)


# ─── 대용량 히스토리 ─────────────────────────────────────────────────────────

class TestLargeHistory:
    def test_100_linear_commits(self):
        commits = []
        hashes = [f"h{i:04d}" for i in range(100)]
        for i, h in enumerate(hashes):
            parent = [hashes[i + 1]] if i < len(hashes) - 1 else []
            commits.append(_make_commit(h, parent))

        builder = _make_builder(commits)
        layout = builder.build()
        assert len(layout.nodes) == 100
        assert layout.max_columns == 1

    def test_limit_parameter(self):
        commits = [_make_commit(f"h{i}", [f"h{i+1}"] if i < 49 else []) for i in range(50)]
        repo = MagicMock()
        repo.get_commit_log_with_parents.return_value = commits
        repo.get_all_refs.return_value = {}
        builder = CommitGraphBuilder(repo)
        builder.build(limit=50)
        repo.get_commit_log_with_parents.assert_called_once_with(limit=50)
