"""Domain models — 순수 Python dataclass, PyQt6 의존성 없음."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


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
