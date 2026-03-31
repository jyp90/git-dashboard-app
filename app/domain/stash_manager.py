"""StashManager — Git stash 작업 관리."""
from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

from app.domain.models import FileDiff, StashEntry

if TYPE_CHECKING:
    from app.infrastructure.git_repository import GitRepository


class StashManager:
    """Git stash 작업을 관리한다."""

    def __init__(self, repository: "GitRepository") -> None:
        self._repo = repository

    def list_stashes(self) -> list[StashEntry]:
        """모든 stash 항목 조회."""
        raw_list = self._repo.get_stash_list()
        result = []
        for item in raw_list:
            result.append(StashEntry(
                index=item["index"],
                message=item["message"],
                branch=item["branch"],
                date=datetime.now(),   # stash list에서 날짜 파싱은 별도 구현 필요
                files_changed=0,
            ))
        return result

    def create_stash(self, message: str = "", include_untracked: bool = True) -> StashEntry | None:
        """현재 변경사항을 stash로 저장.

        Returns:
            생성된 StashEntry, 실패 시 None
        """
        success = self._repo.create_stash(message=message, include_untracked=include_untracked)
        if not success:
            return None

        stashes = self.list_stashes()
        return stashes[0] if stashes else None

    def apply_stash(self, index: int = 0, pop: bool = False) -> bool:
        """stash 적용 (apply=유지, pop=삭제).

        Args:
            index: stash@{index}
            pop: True면 pop(적용 후 삭제), False면 apply(적용 후 유지)
        """
        return self._repo.apply_stash(index=index, pop=pop)

    def drop_stash(self, index: int) -> bool:
        """stash 삭제."""
        return self._repo.drop_stash(index=index)

    def show_stash(self, index: int = 0) -> list[FileDiff]:
        """stash 내용 미리보기 (FileDiff 리스트).

        DiffParser를 직접 임포트하지 않고 raw diff를 파싱하기 위해
        내부에서 lazy import한다.
        """
        raw = self._repo.show_stash(index=index)
        if not raw:
            return []

        from app.domain.diff_parser import DiffParser
        parser = DiffParser(self._repo)
        return parser.parse_raw(raw)

    def get_stash_count(self) -> int:
        """현재 stash 개수."""
        return len(self.list_stashes())
