"""CommitGraphBuilder — Git 커밋 히스토리를 DAG 레이아웃으로 변환."""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.models import Commit, GraphEdge, GraphLayout, GraphNode

if TYPE_CHECKING:
    from app.infrastructure.git_repository import GitRepository


class CommitGraphBuilder:
    """Git 커밋 히스토리를 DAG(Directed Acyclic Graph)로 변환하고
    각 커밋의 lane(열) 배치를 계산한다.

    알고리즘: 토폴로지 정렬 + Lane 할당
    - git log --topo-order로 커밋 순서 확보 (newest first)
    - 각 커밋에 lane(column)을 할당하여 교차 최소화
    - 머지 커밋은 두 lane을 연결하는 곡선으로 표현
    """

    # 브랜치별 색상 팔레트 (SourceTree 스타일)
    BRANCH_COLORS = [
        "#6366f1",  # Indigo  (develop)
        "#22c55e",  # Green   (main)
        "#f59e0b",  # Amber   (feature)
        "#ef4444",  # Red     (hotfix)
        "#06b6d4",  # Cyan    (release)
        "#a855f7",  # Purple
        "#ec4899",  # Pink
        "#14b8a6",  # Teal
    ]

    def __init__(self, repository: "GitRepository") -> None:
        self._repo = repository

    def build(self, limit: int = 200) -> GraphLayout:
        """커밋 히스토리를 읽어 GraphLayout을 생성한다.

        Steps:
        1. git log --topo-order --parents로 커밋+부모 정보 수집
        2. 각 커밋에 대해 lane 할당 (활성 lane 추적)
        3. 머지/분기 edge 계산
        4. GraphLayout 반환
        """
        raw_commits = self._repo.get_commit_log_with_parents(limit=limit)
        if not raw_commits:
            return GraphLayout(nodes=[], edges=[], max_columns=0)

        refs = self._repo.get_all_refs()
        branch_tips = self._detect_branch_tips(refs)

        lane_map = self._assign_lanes(raw_commits)
        color_map = self._assign_colors(raw_commits, lane_map)

        child_map = self._build_child_map(raw_commits)
        nodes = self._build_nodes(raw_commits, lane_map, color_map, branch_tips, child_map)
        edges = self._build_edges(raw_commits, lane_map, color_map)

        max_columns = max((n.column for n in nodes), default=0) + 1
        branch_colors = {i: self.BRANCH_COLORS[i % len(self.BRANCH_COLORS)] for i in range(max_columns)}

        return GraphLayout(
            nodes=nodes,
            edges=edges,
            max_columns=max_columns,
            branch_colors=branch_colors,
        )

    # ─── Lane 할당 ───────────────────────────────────────────────────────────

    def _assign_lanes(self, commits: list[dict]) -> dict[str, int]:
        """Lane 할당 알고리즘.

        active_lanes[i] = 해당 lane이 추적 중인 다음 예상 커밋 해시 (None = 빈 lane)

        처리 규칙 (newest → oldest):
        1. 현재 커밋이 active_lanes에 있으면 그 lane을 사용
        2. 없으면 빈 lane 또는 새 lane 할당
        3. 첫 번째 부모는 현재 lane 계승
        4. 추가 부모(merge)는 새 lane 할당
        5. 이미 tracked된 부모는 중복 lane 생성 안 함
        """
        active_lanes: list[str | None] = []
        lane_map: dict[str, int] = {}

        for commit in commits:
            hash_ = commit["hash"]
            parents = commit["parents"]

            # 1. 현재 커밋의 lane 찾기
            if hash_ in active_lanes:
                lane_idx = active_lanes.index(hash_)
            else:
                # 빈 slot 찾거나 새 lane 추가
                try:
                    lane_idx = active_lanes.index(None)
                except ValueError:
                    lane_idx = len(active_lanes)
                    active_lanes.append(None)

            lane_map[hash_] = lane_idx

            # 2. 현재 커밋의 lane 해제
            active_lanes[lane_idx] = None

            # 3. 중복 참조 제거 (같은 커밋이 여러 lane에 있으면 첫 번째만 유지)
            for i, tracked in enumerate(active_lanes):
                if tracked == hash_ and i != lane_idx:
                    active_lanes[i] = None

            # 4. 부모에 lane 할당
            if parents:
                first_parent = parents[0]
                # 첫 번째 부모가 아직 tracked 안 됐으면 현재 lane 계승
                if first_parent not in active_lanes:
                    active_lanes[lane_idx] = first_parent

                # 추가 부모들(merge)은 빈 lane 또는 새 lane
                for parent in parents[1:]:
                    if parent not in active_lanes:
                        try:
                            free_idx = active_lanes.index(None)
                            active_lanes[free_idx] = parent
                        except ValueError:
                            active_lanes.append(parent)

        return lane_map

    def _assign_colors(self, commits: list[dict], lane_map: dict[str, int]) -> dict[str, int]:
        """lane 인덱스를 컬러 인덱스로 매핑.

        같은 lane은 같은 색상을 사용한다.
        """
        return {
            commit["hash"]: lane_map[commit["hash"]] % len(self.BRANCH_COLORS)
            for commit in commits
        }

    # ─── 그래프 구성 ─────────────────────────────────────────────────────────

    def _build_child_map(self, commits: list[dict]) -> dict[str, list[str]]:
        """커밋 해시 → 자식 커밋 해시 목록 매핑."""
        child_map: dict[str, list[str]] = {c["hash"]: [] for c in commits}
        for commit in commits:
            for parent_hash in commit["parents"]:
                if parent_hash in child_map:
                    child_map[parent_hash].append(commit["hash"])
        return child_map

    def _build_nodes(
        self,
        commits: list[dict],
        lane_map: dict[str, int],
        color_map: dict[str, int],
        branch_tips: dict[str, str],   # commit_hash → branch_name
        child_map: dict[str, list[str]],
    ) -> list[GraphNode]:
        nodes = []
        for raw in commits:
            hash_ = raw["hash"]
            from datetime import datetime
            commit = Commit(
                hash=hash_,
                short_hash=raw["short_hash"],
                message=raw["message"],
                author=raw["author"],
                date=raw["date"],
            )
            nodes.append(GraphNode(
                commit=commit,
                column=lane_map[hash_],
                color_index=color_map[hash_],
                parents=raw["parents"],
                children=child_map.get(hash_, []),
                is_merge=len(raw["parents"]) >= 2,
                is_branch_tip=hash_ in branch_tips,
                branch_name=branch_tips.get(hash_),
            ))
        return nodes

    def _build_edges(
        self,
        commits: list[dict],
        lane_map: dict[str, int],
        color_map: dict[str, int],
    ) -> list[GraphEdge]:
        """각 커밋의 부모-자식 연결 edge 생성."""
        commit_set = {c["hash"] for c in commits}
        edges = []
        for commit in commits:
            child_hash = commit["hash"]
            child_col = lane_map[child_hash]
            child_color = color_map[child_hash]

            for i, parent_hash in enumerate(commit["parents"]):
                if parent_hash not in commit_set:
                    continue
                parent_col = lane_map[parent_hash]

                if parent_col == child_col:
                    edge_type = "straight"
                elif i == 0:
                    # 첫 번째 부모가 다른 lane에 있으면 branch_out
                    edge_type = "branch_out"
                else:
                    # 두 번째 이상 부모 = merge_in
                    edge_type = "merge_in"

                edges.append(GraphEdge(
                    parent_hash=parent_hash,
                    child_hash=child_hash,
                    column_from=child_col,
                    column_to=parent_col,
                    color_index=child_color,
                    edge_type=edge_type,
                ))
        return edges

    # ─── 유틸리티 ────────────────────────────────────────────────────────────

    def _detect_branch_tips(self, refs: dict[str, str]) -> dict[str, str]:
        """커밋 해시 → 브랜치명 매핑 (refs/heads/* 기준)."""
        tips: dict[str, str] = {}
        for ref_name, commit_hash in refs.items():
            # refs/heads/branch-name 또는 단순 branch-name
            if "tags/" in ref_name:
                continue
            branch = ref_name.replace("refs/heads/", "").replace("refs/remotes/", "")
            tips[commit_hash] = branch
        return tips
