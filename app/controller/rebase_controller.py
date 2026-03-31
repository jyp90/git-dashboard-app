"""RebaseController — RebaseDialog ↔ RebaseOrchestrator 워크플로우 조율."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, QThread, pyqtSignal

if TYPE_CHECKING:
    from app.domain.models import RebasePlan
    from app.domain.rebase_orchestrator import RebaseOrchestrator


class _RebaseWorker(QThread):
    """Rebase 실행을 별도 스레드에서 처리."""

    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, orchestrator: "RebaseOrchestrator", plan: "RebasePlan") -> None:
        super().__init__()
        self._orc = orchestrator
        self._plan = plan

    def run(self) -> None:
        try:
            success = self._orc.execute(self._plan)
            msg = "Rebase가 완료되었습니다." if success else "Rebase 실행 중 오류가 발생했습니다."
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, str(e))


class RebaseController(QObject):
    """Interactive Rebase 워크플로우 컨트롤러.

    역할:
    - RebaseDialog에서 사용자가 편집한 RebasePlan을 받아 실행
    - 실행 중 상태를 시그널로 전파
    - 오류 시 자동 abort (RebaseOrchestrator 위임)
    - Conflict 발생 시 MergeController에 handoff 신호

    연결 패턴:
        dialog.accepted → controller.execute_plan(plan)
        controller.rebase_started → UI 비활성화
        controller.rebase_completed → UI 갱신
        controller.conflict_detected → MergeController 활성화
    """

    rebase_started = pyqtSignal()                # 실행 시작
    rebase_completed = pyqtSignal(bool, str)     # success, message
    conflict_detected = pyqtSignal(list)          # list[str] — 충돌 파일 목록
    status_updated = pyqtSignal(dict)             # rebase progress dict

    def __init__(
        self,
        orchestrator: "RebaseOrchestrator",
        conflict_resolver=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._orc = orchestrator
        self._resolver = conflict_resolver
        self._worker: _RebaseWorker | None = None

    # ─── 공개 API ────────────────────────────────────────────────────────────

    def execute_plan(self, plan: "RebasePlan") -> None:
        """RebasePlan을 비동기 실행.

        Args:
            plan: RebaseDialog.get_plan()에서 반환된 편집된 계획
        """
        if not plan or not plan.steps:
            return

        self.rebase_started.emit()
        self._worker = _RebaseWorker(self._orc, plan)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def abort(self) -> bool:
        """진행 중인 Rebase 중단."""
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()
        return self._orc.abort()

    def continue_rebase(self) -> bool:
        """충돌 해결 후 Rebase 계속."""
        success = self._orc.continue_rebase()
        self.rebase_completed.emit(success, "continue" if success else "continue 실패")
        return success

    def get_status(self) -> dict | None:
        """현재 Rebase 진행 상태 조회 및 시그널 발생."""
        status = self._orc.get_rebase_status()
        if status is not None:
            self.status_updated.emit(status)
        return status

    def prepare_plan(self, onto: str = "HEAD~10") -> "RebasePlan | None":
        """RebasePlan 초안 생성 (UI 진입점)."""
        try:
            return self._orc.prepare(onto)
        except ValueError as e:
            self.rebase_completed.emit(False, str(e))
            return None

    # ─── 내부 ────────────────────────────────────────────────────────────────

    def _on_worker_finished(self, success: bool, message: str) -> None:
        """Worker 완료 핸들러."""
        if not success:
            # Rebase가 conflict로 중단된 경우 감지
            status = self._orc.get_rebase_status()
            if status is not None:
                # rebase-merge/apply 디렉토리 존재 = conflict 상태
                conflict_files = (
                    self._resolver.detect_conflicts()
                    if self._resolver is not None
                    else []
                )
                self.conflict_detected.emit(conflict_files)
                return

        self.rebase_completed.emit(success, message)
        self._worker = None
