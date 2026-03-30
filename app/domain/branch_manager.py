"""BranchManager — 브랜치 상태 분석 및 동기화 비즈니스 로직."""
from __future__ import annotations

from app.domain.models import BranchResult, BranchSummary, SyncResult
from app.infrastructure.git_repository import GitRepository, GitRepositoryError


class BranchManager:
    """Domain Layer: GitRepository 공개 API만 사용해 브랜치 도메인 로직 처리."""

    def __init__(self, repo: GitRepository) -> None:
        self._repo = repo

    def get_branch_summary(self) -> BranchSummary:
        """현재 브랜치 상태 요약 반환."""
        return self._repo.get_branch_summary()

    def sync_develop(self) -> SyncResult:
        """origin/develop을 fetch 후 develop 브랜치를 pull."""
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
            branches = self._repo.get_branches()
            base = "develop" if "develop" in branches else None
            self._repo.create_branch(branch_name, base)
            return BranchResult(success=True, branch_name=branch_name,
                                message=f"release 브랜치 생성: {branch_name}")
        except GitRepositoryError as e:
            return BranchResult(success=False, branch_name=branch_name, message=str(e))
        except Exception as e:
            return BranchResult(success=False, branch_name=branch_name, message=str(e))

    def create_hotfix_branch(self, issue_id: str) -> BranchResult:
        """hotfix/{issue_id} 브랜치 생성 (main/master 기반)."""
        branch_name = f"hotfix/{issue_id}"
        try:
            branches = self._repo.get_branches()
            base = next((b for b in ("main", "master") if b in branches), None)
            self._repo.create_branch(branch_name, base)
            return BranchResult(success=True, branch_name=branch_name,
                                message=f"hotfix 브랜치 생성: {branch_name}")
        except GitRepositoryError as e:
            return BranchResult(success=False, branch_name=branch_name, message=str(e))
        except Exception as e:
            return BranchResult(success=False, branch_name=branch_name, message=str(e))
