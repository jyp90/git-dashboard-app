"""MergeController — MergeEditor ↔ ConflictResolver 워크플로우 조율."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from app.domain.conflict_resolver import ConflictResolver


class MergeController(QObject):
    """머지/Rebase 충돌 해결 워크플로우 컨트롤러.

    역할:
    - ConflictResolver를 통해 충돌 감지 및 해결 조율
    - MergeEditor UI와 ConflictResolver 도메인 연결
    - 충돌 자동 감지 (FileWatcherService의 merge_started/rebase_started 연동)
    - 모든 충돌 해결 완료 시 git add 자동 처리 시그널

    연결 패턴:
        FileWatcher.merge_started → controller.detect_conflicts()
        controller.conflicts_found(files) → MergeEditor 표시
        MergeEditor.all_resolved(path) → controller.on_file_resolved(path)
        controller.all_files_resolved → 머지/rebase continue 안내
    """

    conflicts_found = pyqtSignal(list)       # list[str] — 충돌 파일 경로 목록
    conflicts_cleared = pyqtSignal()         # 충돌 없음 (클린 상태)
    file_resolved = pyqtSignal(str)          # 단일 파일 해결 완료
    all_files_resolved = pyqtSignal()        # 모든 파일 해결 완료
    error_occurred = pyqtSignal(str)         # 오류 메시지

    def __init__(self, resolver: "ConflictResolver", parent=None) -> None:
        super().__init__(parent)
        self._resolver = resolver
        self._pending_files: set[str] = set()

    # ─── 공개 API ────────────────────────────────────────────────────────────

    def detect_conflicts(self) -> list[str]:
        """현재 충돌 파일 목록 감지 및 시그널 발생.

        Returns:
            충돌 파일 경로 목록 (빈 리스트 = 충돌 없음)
        """
        try:
            files = self._resolver.detect_conflicts()
        except Exception as e:
            self.error_occurred.emit(f"충돌 감지 실패: {e}")
            return []

        if files:
            self._pending_files = set(files)
            self.conflicts_found.emit(files)
        else:
            self._pending_files.clear()
            self.conflicts_cleared.emit()

        return files

    def resolve_file(self, file_path: str, resolution: str = "ours") -> bool:
        """파일의 모든 충돌을 일괄 해결.

        Args:
            file_path: 충돌 파일 경로
            resolution: "ours" | "theirs" | "both"

        Returns:
            True = 성공
        """
        try:
            self._resolver.resolve_all(file_path, resolution)
            self._resolver.mark_resolved(file_path)
            self._on_file_resolved(file_path)
            return True
        except Exception as e:
            self.error_occurred.emit(f"{file_path} 해결 실패: {e}")
            return False

    def mark_file_resolved(self, file_path: str) -> bool:
        """파일을 git add로 해결 완료 처리.

        MergeEditor에서 수동 해결 후 호출.
        """
        try:
            self._resolver.mark_resolved(file_path)
            self._on_file_resolved(file_path)
            return True
        except RuntimeError as e:
            self.error_occurred.emit(str(e))
            return False

    def get_conflict_summary(self) -> dict:
        """현재 충돌 상태 요약.

        Returns:
            {"total_files": int, "total_regions": int, "files": list[str]}
        """
        files = self._resolver.detect_conflicts()
        total_regions = 0
        for f in files:
            cf = self._resolver.parse_conflict(f)
            total_regions += cf.total_conflicts
        return {
            "total_files": len(files),
            "total_regions": total_regions,
            "files": files,
        }

    def resolve_all_ours(self) -> int:
        """모든 충돌을 'ours'로 자동 해결.

        Returns:
            해결된 파일 수
        """
        return self._resolve_all_with("ours")

    def resolve_all_theirs(self) -> int:
        """모든 충돌을 'theirs'로 자동 해결.

        Returns:
            해결된 파일 수
        """
        return self._resolve_all_with("theirs")

    # ─── 내부 ────────────────────────────────────────────────────────────────

    def _resolve_all_with(self, resolution: str) -> int:
        files = self._resolver.detect_conflicts()
        count = 0
        for f in files:
            if self.resolve_file(f, resolution):
                count += 1
        return count

    def _on_file_resolved(self, file_path: str) -> None:
        """단일 파일 해결 처리."""
        self._pending_files.discard(file_path)
        self.file_resolved.emit(file_path)
        if not self._pending_files:
            self.all_files_resolved.emit()
