"""DiffController — Diff 관련 워크플로우 조율."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

from app.domain.diff_parser import DiffParser
from app.domain.models import DiffHunk, FileDiff

if TYPE_CHECKING:
    from app.infrastructure.git_repository import GitRepository


class DiffController(QObject):
    """Diff 관련 워크플로우를 조율한다.

    시그널:
    - diff_ready(list[FileDiff]): diff 파싱 완료
    - file_staged(str): 파일 스테이징 완료
    - file_unstaged(str): 파일 언스테이징 완료
    - error_occurred(str): 오류 발생
    """

    diff_ready = pyqtSignal(list)
    file_staged = pyqtSignal(str)
    file_unstaged = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, repository: "GitRepository", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._repo = repository
        self._parser = DiffParser(repository)

    def load_working_tree_diff(self) -> None:
        """워킹 트리 변경사항 로드 → diff_ready 시그널."""
        try:
            diffs = self._parser.parse_working_tree()
            self.diff_ready.emit(diffs)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def load_staged_diff(self) -> None:
        """스테이지된 변경사항 로드."""
        try:
            diffs = self._parser.parse_staged()
            self.diff_ready.emit(diffs)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def load_commit_diff(self, commit_hash: str) -> None:
        """특정 커밋의 변경사항 로드."""
        try:
            diffs = self._parser.parse_commit(commit_hash)
            self.diff_ready.emit(diffs)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stage_file(self, file_path: str) -> None:
        """파일 스테이징."""
        try:
            self._repo._repo.index.add([file_path])
            self.file_staged.emit(file_path)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def unstage_file(self, file_path: str) -> None:
        """파일 언스테이징."""
        try:
            self._repo._repo.index.reset(paths=[file_path])
            self.file_unstaged.emit(file_path)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stage_hunk(self, file_path: str, hunk: DiffHunk) -> None:
        """특정 hunk만 스테이징 (partial staging).

        git apply --cached를 사용하여 hunk 단위 스테이징.
        """
        try:
            patch = self._hunk_to_patch(file_path, hunk)
            self._repo._repo.git.apply("--cached", "-", input=patch)
            self.file_staged.emit(file_path)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def discard_file(self, file_path: str) -> None:
        """워킹 트리 변경사항 폐기 (git checkout --)."""
        try:
            self._repo._repo.git.checkout("--", file_path)
        except Exception as e:
            self.error_occurred.emit(str(e))

    # ─── 내부 헬퍼 ──────────────────────────────────────────────────────────

    def _hunk_to_patch(self, file_path: str, hunk: DiffHunk) -> str:
        """DiffHunk를 patch 형식 문자열로 변환."""
        lines = [
            f"--- a/{file_path}\n",
            f"+++ b/{file_path}\n",
            f"{hunk.header}\n",
        ]
        for line in hunk.lines:
            if line.type == "add":
                lines.append(f"+{line.content}\n")
            elif line.type == "delete":
                lines.append(f"-{line.content}\n")
            else:
                lines.append(f" {line.content}\n")
        return "".join(lines)
