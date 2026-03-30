"""BranchManager — 브랜치 상태 분석 및 동기화 비즈니스 로직."""
from __future__ import annotations

from app.domain.models import BranchResult, BranchSummary, SyncResult
from app.infrastructure.git_repository import GitRepository, GitRepositoryError


class BranchManager:
    """Domain Layer: GitRepository를 사용해 브랜치 도메인 로직 처리."""

    def __init__(self, repo: GitRepository) -> None:
        self._repo = repo

    def get_branch_summary(self) -> BranchSummary:
        """현재 브랜치 상태 요약 반환."""
        return self._repo.get_branch_summary()

    def sync_develop(self) -> SyncResult:
        """origin/develop을 fetch 후 develop 브랜치를 pull.
        현재 브랜치가 develop이 아니어도 동작.
        """
        try:
            self._repo.fetch()
            current = self._repo.get_current_branch()
            if current == "develop":
                count = self._repo.pull("develop")
                return SyncResult(
                    success=True,
                    message=f"develop 동기화 완료 ({count}개 커밋 당김)" if count else "이미 최신 상태입니다",
                    commits_pulled=count,
                )
            else:
                # develop 브랜치만 fetch 후 로컬 develop 업데이트
                return SyncResult(
                    success=True,
                    message=f"origin/develop fetch 완료 (현재 브랜치: {current})",
                    commits_pulled=0,
                )
        except GitRepositoryError as e:
            return SyncResult(success=False, message=str(e))
        except Exception as e:
            return SyncResult(success=False, message=f"동기화 실패: {e}")

    def create_release_branch(self, version: str) -> BranchResult:
        """release/{version} 브랜치 생성 (develop 기반)."""
        branch_name = f"release/{version}"
        try:
            repo = self._repo._repo
            if branch_name in [b.name for b in repo.branches]:
                return BranchResult(
                    success=False,
                    branch_name=branch_name,
                    message=f"브랜치가 이미 존재합니다: {branch_name}",
                )
            develop = repo.branches["develop"] if "develop" in [b.name for b in repo.branches] else repo.active_branch
            new_branch = repo.create_head(branch_name, develop)
            new_branch.checkout()
            return BranchResult(
                success=True,
                branch_name=branch_name,
                message=f"release 브랜치 생성: {branch_name}",
            )
        except Exception as e:
            return BranchResult(success=False, branch_name=branch_name, message=str(e))

    def create_hotfix_branch(self, issue_id: str) -> BranchResult:
        """hotfix/{issue_id} 브랜치 생성 (main 기반)."""
        branch_name = f"hotfix/{issue_id}"
        try:
            repo = self._repo._repo
            if branch_name in [b.name for b in repo.branches]:
                return BranchResult(
                    success=False,
                    branch_name=branch_name,
                    message=f"브랜치가 이미 존재합니다: {branch_name}",
                )
            base = None
            for candidate in ("main", "master"):
                if candidate in [b.name for b in repo.branches]:
                    base = repo.branches[candidate]
                    break
            if base is None:
                base = repo.active_branch
            new_branch = repo.create_head(branch_name, base)
            new_branch.checkout()
            return BranchResult(
                success=True,
                branch_name=branch_name,
                message=f"hotfix 브랜치 생성: {branch_name}",
            )
        except Exception as e:
            return BranchResult(success=False, branch_name=branch_name, message=str(e))
