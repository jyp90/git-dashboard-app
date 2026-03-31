"""FileWatcherService — .git 디렉토리 변경 감지 서비스."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtCore import QFileSystemWatcher


class FileWatcherService(QObject):
    """.git 디렉토리의 파일 변경을 감지하여
    IDE에서 수행한 Git 작업을 실시간으로 반영한다.

    감시 대상:
    - .git/refs/heads/*   → 브랜치 변경 감지
    - .git/HEAD           → 체크아웃 감지
    - .git/COMMIT_EDITMSG → 커밋 감지
    - .git/refs/stash     → stash 변경 감지
    - .git/MERGE_HEAD     → 머지 진행 감지
    - .git/REBASE_HEAD    → rebase 진행 감지

    사용 기술: QFileSystemWatcher (PyQt6 내장)
    500ms 디바운스로 이벤트 폭주 방지
    """

    # ─── 시그널 ──────────────────────────────────────────────────────────────
    commit_detected = pyqtSignal()
    branch_changed = pyqtSignal(str)
    push_detected = pyqtSignal()
    stash_changed = pyqtSignal()
    merge_started = pyqtSignal()
    rebase_started = pyqtSignal()
    repository_changed = pyqtSignal()

    DEBOUNCE_MS = 500

    def __init__(self, repo_path: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._repo_path = Path(repo_path)
        self._git_dir = self._repo_path / ".git"
        self._watcher = QFileSystemWatcher(self)
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._flush_events)
        self._pending_paths: set[str] = set()

        self._watcher.fileChanged.connect(self._on_file_changed)
        self._watcher.directoryChanged.connect(self._on_directory_changed)

    def start_watching(self) -> None:
        """감시 시작: 대상 파일/디렉토리 등록."""
        if not self._git_dir.exists():
            return

        paths_to_watch: list[str] = []

        # 파일 감시 대상
        for rel in [
            "HEAD",
            "COMMIT_EDITMSG",
            "MERGE_HEAD",
            "REBASE_HEAD",
            "refs/stash",
        ]:
            p = self._git_dir / rel
            paths_to_watch.append(str(p))

        # 디렉토리 감시 대상
        for rel in ["refs/heads", "refs/remotes"]:
            p = self._git_dir / rel
            paths_to_watch.append(str(p))

        self._watcher.addPaths(paths_to_watch)

    def stop_watching(self) -> None:
        """감시 중지."""
        files = self._watcher.files()
        dirs = self._watcher.directories()
        if files:
            self._watcher.removePaths(files)
        if dirs:
            self._watcher.removePaths(dirs)
        self._debounce_timer.stop()
        self._pending_paths.clear()

    def watched_paths(self) -> list[str]:
        """현재 감시 중인 경로 목록 반환."""
        return list(self._watcher.files()) + list(self._watcher.directories())

    # ─── 이벤트 핸들러 ───────────────────────────────────────────────────────

    def _on_file_changed(self, path: str) -> None:
        """파일 변경 이벤트 — 디바운스 후 분류."""
        self._pending_paths.add(path)
        # 파일이 재생성되는 경우 watcher에서 제거될 수 있어 재등록 필요
        if not Path(path).exists():
            return
        if path not in self._watcher.files():
            self._watcher.addPath(path)
        self._debounce_timer.start(self.DEBOUNCE_MS)

    def _on_directory_changed(self, path: str) -> None:
        """디렉토리 변경 이벤트 — 디바운스 후 분류."""
        self._pending_paths.add(path)
        self._debounce_timer.start(self.DEBOUNCE_MS)

    def _flush_events(self) -> None:
        """디바운스 타이머 만료 → 대기 중인 이벤트 분류 후 시그널 발출."""
        paths = set(self._pending_paths)
        self._pending_paths.clear()

        emitted_general = False
        for path in paths:
            self._classify_and_emit(path)
            emitted_general = True

        if emitted_general:
            self.repository_changed.emit()

    def _classify_and_emit(self, path: str) -> None:
        """변경된 경로를 분석하여 적절한 시그널 발출."""
        p = Path(path)
        git_dir = self._git_dir

        # .git/COMMIT_EDITMSG → 커밋 감지
        if p == git_dir / "COMMIT_EDITMSG":
            self.commit_detected.emit()
            return

        # .git/HEAD → 체크아웃 감지
        if p == git_dir / "HEAD":
            branch = self._read_head_branch()
            self.branch_changed.emit(branch)
            return

        # .git/refs/stash → stash 변경
        if p == git_dir / "refs" / "stash":
            self.stash_changed.emit()
            return

        # .git/MERGE_HEAD → 머지 진행
        if p == git_dir / "MERGE_HEAD":
            self.merge_started.emit()
            return

        # .git/REBASE_HEAD → rebase 진행
        if p == git_dir / "REBASE_HEAD":
            self.rebase_started.emit()
            return

        # .git/refs/heads/* 또는 refs/remotes/* → 브랜치/푸시 변경
        refs_heads = git_dir / "refs" / "heads"
        refs_remotes = git_dir / "refs" / "remotes"
        try:
            p.relative_to(refs_heads)
            # heads 디렉토리 변경 → push or branch create/delete
            self.push_detected.emit()
        except ValueError:
            pass

    def _read_head_branch(self) -> str:
        """현재 HEAD 브랜치명 반환."""
        try:
            head = (self._git_dir / "HEAD").read_text().strip()
            if head.startswith("ref: refs/heads/"):
                return head[len("ref: refs/heads/"):]
            return head[:7]  # detached HEAD
        except Exception:
            return "unknown"
