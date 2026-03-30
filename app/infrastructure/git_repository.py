"""GitRepository — GitPython 기반 저장소 접근 추상화."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import git
from git import InvalidGitRepositoryError, NoSuchPathError

from app.domain.models import BranchSummary, Commit


class GitRepositoryError(Exception):
    """저장소 접근 관련 예외."""


class GitRepository:
    """GitPython 래핑. UI/Domain 계층에서 직접 git 명령 사용 금지."""

    def __init__(self, repo_path: str) -> None:
        self._path = Path(repo_path)
        try:
            self._repo = git.Repo(repo_path, search_parent_directories=True)
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            raise GitRepositoryError(f"Git 저장소를 찾을 수 없습니다: {repo_path}") from e

    @property
    def path(self) -> Path:
        return self._path

    def get_current_branch(self) -> str:
        """현재 체크아웃된 브랜치명 반환. HEAD detached 시 'HEAD' 반환."""
        try:
            return self._repo.active_branch.name
        except TypeError:
            return "HEAD (detached)"

    def get_branches(self, remote: bool = False) -> list[str]:
        """로컬 또는 리모트 브랜치 목록 반환."""
        if remote:
            return [ref.name for ref in self._repo.remotes[0].refs] if self._repo.remotes else []
        return [branch.name for branch in self._repo.branches]

    def get_commit_log(self, limit: int = 20) -> list[Commit]:
        """최근 N개 커밋 목록 반환."""
        commits = []
        for c in self._repo.iter_commits(max_count=limit):
            commits.append(
                Commit(
                    hash=c.hexsha,
                    short_hash=c.hexsha[:7],
                    message=c.message.strip(),
                    author=str(c.author),
                    date=datetime.fromtimestamp(c.authored_date),
                )
            )
        return commits

    def get_status(self) -> bool:
        """작업 디렉토리에 미커밋 변경사항이 있으면 True."""
        return self._repo.is_dirty(untracked_files=True)

    def get_ahead_behind(self, remote_branch: str = "origin/develop") -> tuple[int, int]:
        """현재 브랜치와 remote_branch 간 ahead/behind 커밋 수 반환."""
        try:
            current = self._repo.active_branch.name
            # git rev-list 로 계산
            ahead = list(self._repo.iter_commits(f"{remote_branch}..{current}"))
            behind = list(self._repo.iter_commits(f"{current}..{remote_branch}"))
            return len(ahead), len(behind)
        except Exception:
            return 0, 0

    def get_branch_summary(self) -> BranchSummary:
        """브랜치 상태 요약 반환 (BranchManager에서 사용)."""
        current = self.get_current_branch()
        ahead, behind = self.get_ahead_behind()
        is_dirty = self.get_status()
        local = self.get_branches(remote=False)
        remote = self.get_branches(remote=True)
        return BranchSummary(
            current=current,
            ahead=ahead,
            behind=behind,
            is_dirty=is_dirty,
            local_branches=local,
            remote_branches=remote,
        )

    def fetch(self) -> None:
        """origin 리모트 fetch."""
        if self._repo.remotes:
            self._repo.remotes.origin.fetch()

    def pull(self, branch: str = "develop") -> int:
        """지정 브랜치를 pull하고 당겨온 커밋 수 반환."""
        before = self._repo.head.commit
        origin = self._repo.remotes.origin
        origin.pull(branch)
        after = self._repo.head.commit
        return sum(1 for _ in self._repo.iter_commits(f"{before}..{after}"))
