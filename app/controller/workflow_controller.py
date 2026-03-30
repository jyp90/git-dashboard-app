"""WorkflowController — 유스케이스 조율, Signal/Slot 중개."""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from app.controller.git_worker import GitWorker
from app.domain.branch_manager import BranchManager
from app.domain.models import BranchSummary, Commit, PrCheckReport, RepoConfig, SyncResult, BranchResult
from app.infrastructure.config_store import ConfigStore
from app.infrastructure.git_repository import GitRepository, GitRepositoryError


class WorkflowController(QObject):
    """UI 이벤트를 받아 Domain/Infrastructure를 호출하고 결과를 시그널로 방출.

    UI는 이 컨트롤러의 공개 메서드와 시그널만 사용 — 내부 _repo/_config 직접 접근 금지.
    """

    # 브랜치 상태 업데이트
    branch_summary_ready = pyqtSignal(object)   # BranchSummary
    # 동기화 완료
    sync_finished = pyqtSignal(object)           # SyncResult
    # 브랜치 생성 완료
    branch_created = pyqtSignal(object)          # BranchResult
    # PR 체크 완료
    pr_check_ready = pyqtSignal(object)          # PrCheckReport
    # Pre-push 훅 실행 완료 (F-10)
    hook_result_ready = pyqtSignal(object)       # ScriptResult
    # 에러
    error_occurred = pyqtSignal(str)
    # 작업 진행 중
    task_running = pyqtSignal(bool)

    def __init__(self, config_store: ConfigStore, parent=None) -> None:
        super().__init__(parent)
        self._config = config_store
        self._repo: GitRepository | None = None
        self._branch_manager: BranchManager | None = None
        self._active_worker: GitWorker | None = None
        self._load_active_repo()

    def _load_active_repo(self) -> None:
        """ConfigStore에서 활성 저장소를 로드."""
        repo_cfg = self._config.get_active_repo()
        if repo_cfg:
            self._set_repository(repo_cfg.path)

    def _set_repository(self, path: str) -> None:
        try:
            self._repo = GitRepository(path)
            self._branch_manager = BranchManager(self._repo)
        except GitRepositoryError as e:
            self.error_occurred.emit(str(e))
            self._repo = None
            self._branch_manager = None

    def switch_repository(self, path: str) -> None:
        """활성 저장소 전환."""
        self._config.set_active_repo(path)
        self._set_repository(path)
        self.refresh_branch_summary()

    def _run_task(self, task) -> GitWorker | None:
        """QThread로 task 실행. 동시에 하나만 허용. 실행 불가 시 None 반환."""
        if self._active_worker and self._active_worker.isRunning():
            self.error_occurred.emit("이미 작업이 진행 중입니다.")
            return None
        worker = GitWorker(task)
        self._active_worker = worker
        self.task_running.emit(True)
        worker.finished.connect(lambda: self.task_running.emit(False))
        return worker

    # ── 공개 Facade API (UI에서 _config/_repo 직접 접근 대체) ─────────────

    def get_repositories(self) -> list[RepoConfig]:
        """등록된 저장소 목록 반환."""
        return self._config.get_repositories()

    def get_active_repo(self) -> RepoConfig | None:
        """현재 활성 저장소 반환."""
        return self._config.get_active_repo()

    def get_commit_log(self, limit: int = 20) -> list[Commit]:
        """현재 저장소의 커밋 로그 반환."""
        if not self._repo:
            return []
        return self._repo.get_commit_log(limit)

    def has_repository(self) -> bool:
        """활성 저장소가 있으면 True."""
        return self._repo is not None

    # ── 저장소 관리 ────────────────────────────────────────────────────────

    def add_repository(self, path: str, name: str) -> bool:
        """저장소 등록. 성공 시 True 반환."""
        try:
            GitRepository(path)  # 유효한 git 저장소인지 확인
        except GitRepositoryError as e:
            self.error_occurred.emit(str(e))
            return False
        self._config.add_repository(path, name)
        return True

    def remove_repository(self, path: str) -> None:
        """저장소 삭제."""
        self._config.remove_repository(path)
        # 삭제 후 활성 저장소가 없으면 다음 저장소로 전환
        active = self._config.get_active_repo()
        if active:
            self._set_repository(active.path)
        else:
            self._repo = None
            self._branch_manager = None

    def refresh_branch_summary(self) -> None:
        """브랜치 상태 비동기 갱신."""
        if not self._branch_manager:
            self.error_occurred.emit("저장소가 설정되지 않았습니다.")
            return
        worker = self._run_task(self._branch_manager.get_branch_summary)
        if worker is None:
            return
        worker.result_ready.connect(self.branch_summary_ready.emit)
        worker.error_occurred.connect(self.error_occurred.emit)
        worker.start()

    def sync_develop(self) -> None:
        """develop 브랜치 동기화 비동기 실행."""
        if not self._branch_manager:
            self.error_occurred.emit("저장소가 설정되지 않았습니다.")
            return
        worker = self._run_task(self._branch_manager.sync_develop)
        if worker is None:
            return
        worker.result_ready.connect(self.sync_finished.emit)
        worker.error_occurred.connect(self.error_occurred.emit)
        worker.start()

    def create_release_branch(self, version: str) -> None:
        """release 브랜치 생성 비동기 실행."""
        if not self._branch_manager:
            return
        worker = self._run_task(lambda: self._branch_manager.create_release_branch(version))
        if worker is None:
            return
        worker.result_ready.connect(self.branch_created.emit)
        worker.error_occurred.connect(self.error_occurred.emit)
        worker.start()

    def create_hotfix_branch(self, issue_id: str) -> None:
        """hotfix 브랜치 생성 비동기 실행."""
        if not self._branch_manager:
            return
        worker = self._run_task(lambda: self._branch_manager.create_hotfix_branch(issue_id))
        if worker is None:
            return
        worker.result_ready.connect(self.branch_created.emit)
        worker.error_occurred.connect(self.error_occurred.emit)
        worker.start()

    def run_pr_check(self) -> None:
        """PR 체크 비동기 실행."""
        if not self._repo:
            self.error_occurred.emit("저장소가 설정되지 않았습니다.")
            return
        from app.domain.pr_checker import PrChecker
        checker = PrChecker(self._repo)
        worker = self._run_task(checker.check)
        if worker is None:
            return
        worker.result_ready.connect(self.pr_check_ready.emit)
        worker.error_occurred.connect(self.error_occurred.emit)
        worker.start()

    def run_pre_push_hook(self) -> None:
        """pre-push 훅 스크립트 실행 비동기 (F-10)."""
        if not self._repo:
            self.error_occurred.emit("저장소가 설정되지 않았습니다.")
            return
        from app.domain.models import ScriptResult
        from app.infrastructure.script_runner import ScriptRunner
        hook_path = self._repo.get_hook_path("pre-push")
        if hook_path is None:
            self.hook_result_ready.emit(
                ScriptResult(True, "pre-push 훅이 설정되어 있지 않습니다.", "", 0)
            )
            return
        runner = ScriptRunner(hook_path.parent)
        repo_path = str(self._repo.path)
        worker = self._run_task(lambda: runner.run(hook_path.name, cwd=repo_path))
        if worker is None:
            return
        worker.result_ready.connect(self.hook_result_ready.emit)
        worker.error_occurred.connect(self.error_occurred.emit)
        worker.start()
