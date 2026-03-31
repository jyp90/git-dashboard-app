"""Domain models — 순수 Python dataclass, PyQt6 의존성 없음."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING


class BranchStatus(Enum):
    CLEAN = "clean"
    DIRTY = "dirty"
    AHEAD = "ahead"
    BEHIND = "behind"
    DIVERGED = "diverged"


@dataclass
class Commit:
    hash: str
    short_hash: str
    message: str
    author: str
    date: datetime

    @property
    def summary(self) -> str:
        return self.message.split("\n")[0][:72]


@dataclass
class BranchSummary:
    current: str
    ahead: int
    behind: int
    is_dirty: bool
    local_branches: list[str] = field(default_factory=list)
    remote_branches: list[str] = field(default_factory=list)

    @property
    def status(self) -> BranchStatus:
        if self.is_dirty:
            return BranchStatus.DIRTY
        if self.ahead > 0 and self.behind > 0:
            return BranchStatus.DIVERGED
        if self.ahead > 0:
            return BranchStatus.AHEAD
        if self.behind > 0:
            return BranchStatus.BEHIND
        return BranchStatus.CLEAN


@dataclass
class CheckItem:
    category: str  # "convention" | "size" | "todo"
    passed: bool
    message: str


@dataclass
class PrCheckReport:
    passed: bool
    items: list[CheckItem] = field(default_factory=list)
    summary: str = ""

    @classmethod
    def empty(cls) -> "PrCheckReport":
        return cls(passed=True, items=[], summary="검사 항목 없음")


@dataclass
class ScriptResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int

    @classmethod
    def failure(cls, message: str) -> "ScriptResult":
        return cls(success=False, stdout="", stderr=message, return_code=1)


@dataclass
class RepoConfig:
    name: str
    path: str
    is_active: bool = False


@dataclass
class SyncResult:
    success: bool
    message: str
    commits_pulled: int = 0


@dataclass
class BranchResult:
    success: bool
    branch_name: str
    message: str


# ─── F-14: Diff 모델 ────────────────────────────────────────────────────────

@dataclass
class DiffLine:
    """diff의 한 줄."""
    type: str           # "add" | "delete" | "context" | "header"
    content: str
    old_line_no: int | None
    new_line_no: int | None


@dataclass
class DiffHunk:
    """하나의 diff hunk (@@ 블록)."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: list[DiffLine] = field(default_factory=list)


@dataclass
class FileDiff:
    """하나의 파일에 대한 diff 결과."""
    old_path: str
    new_path: str
    status: str         # "modified" | "added" | "deleted" | "renamed"
    hunks: list[DiffHunk] = field(default_factory=list)
    is_binary: bool = False
    similarity: int | None = None


# ─── F-15: Stash 모델 ───────────────────────────────────────────────────────

@dataclass
class StashEntry:
    """하나의 stash 항목."""
    index: int
    message: str
    branch: str
    date: datetime
    files_changed: int = 0


# ─── F-13: 커밋 그래프 모델 ─────────────────────────────────────────────────

@dataclass
class GraphNode:
    """그래프의 한 노드 = 한 커밋."""
    commit: Commit
    column: int
    color_index: int
    parents: list[str]
    children: list[str] = field(default_factory=list)
    is_merge: bool = False
    is_branch_tip: bool = False
    branch_name: str | None = None


@dataclass
class GraphEdge:
    """두 노드를 잇는 간선."""
    parent_hash: str
    child_hash: str
    column_from: int
    column_to: int
    color_index: int
    edge_type: str      # "straight" | "merge_in" | "branch_out"


@dataclass
class GraphLayout:
    """전체 그래프 레이아웃 결과."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    max_columns: int
    branch_colors: dict[int, str] = field(default_factory=dict)


# ─── F-18: Rebase 모델 ──────────────────────────────────────────────────────

@dataclass
class RebaseStep:
    """rebase의 각 단계."""
    action: str         # "pick" | "reword" | "squash" | "fixup" | "drop" | "edit"
    commit_hash: str
    original_message: str
    new_message: str | None = None


@dataclass
class RebasePlan:
    """Interactive rebase 실행 계획."""
    base_commit: str
    steps: list[RebaseStep] = field(default_factory=list)


# ─── F-19: Conflict 모델 ────────────────────────────────────────────────────

@dataclass
class ConflictRegion:
    """하나의 충돌 영역 (<<<, ===, >>> 블록)."""
    start_line: int
    end_line: int
    ours_content: list[str]
    base_content: list[str]      # diff3 모드 시 BASE 내용
    theirs_content: list[str]


@dataclass
class ConflictFile:
    """충돌이 발생한 파일."""
    path: str
    conflicts: list[ConflictRegion] = field(default_factory=list)
    non_conflict_lines: list[tuple[int, int, str]] = field(default_factory=list)
    total_conflicts: int = 0
