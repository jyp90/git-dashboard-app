"""FileWatcherService 단위 테스트.

QFileSystemWatcher를 mock하여 PyQt6 display 없이 테스트한다.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ─── PyQt6 mock setup ────────────────────────────────────────────────────────
# QFileSystemWatcher + QTimer를 mock하여 headless 테스트 가능하게 함

import sys
from unittest.mock import MagicMock

# PyQt6 모듈 전체를 mock
_qt_mock = MagicMock()
_qobject_mock = MagicMock
_qobject_mock.__init_subclass__ = classmethod(lambda cls, **kwargs: None)

# QObject를 실제 Python 클래스로 모킹
class MockQObject:
    def __init__(self, *args, **kwargs):
        pass

class MockQTimer(MockQObject):
    def __init__(self, *args, **kwargs):
        self._single_shot = False
        self._timeout_callbacks = []
        self.timeout = MagicMock()
        self.timeout.connect = MagicMock(side_effect=self._connect_timeout)

    def setSingleShot(self, val):
        self._single_shot = val

    def start(self, ms=0):
        pass

    def stop(self):
        pass

    def _connect_timeout(self, cb):
        self._timeout_callbacks.append(cb)

    def fire(self):
        for cb in self._timeout_callbacks:
            cb()

class MockQFileSystemWatcher(MockQObject):
    def __init__(self, *args, **kwargs):
        self._files: list[str] = []
        self._dirs: list[str] = []
        self.fileChanged = MagicMock()
        self.fileChanged.connect = MagicMock()
        self.directoryChanged = MagicMock()
        self.directoryChanged.connect = MagicMock()

    def addPaths(self, paths):
        for p in paths:
            if p not in self._files:
                self._files.append(p)

    def addPath(self, path):
        if path not in self._files:
            self._files.append(path)

    def removePaths(self, paths):
        for p in paths:
            if p in self._files:
                self._files.remove(p)
            if p in self._dirs:
                self._dirs.remove(p)

    def files(self):
        return list(self._files)

    def directories(self):
        return list(self._dirs)

# Patch PyQt6 before importing FileWatcherService
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtCore'] = MagicMock(
    QObject=MockQObject,
    QTimer=MockQTimer,
    QFileSystemWatcher=MockQFileSystemWatcher,
    pyqtSignal=MagicMock(return_value=MagicMock()),
)

# Now import the service
from app.infrastructure.file_watcher_service import FileWatcherService


# ─── 픽스처 ─────────────────────────────────────────────────────────────────

@pytest.fixture
def git_repo(tmp_path):
    """임시 .git 디렉토리가 있는 fake 저장소."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "refs").mkdir()
    (git_dir / "refs" / "heads").mkdir()
    (git_dir / "refs" / "remotes").mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/develop\n")
    (git_dir / "COMMIT_EDITMSG").write_text("initial commit\n")
    return tmp_path


def _make_watcher(repo_path) -> FileWatcherService:
    """FileWatcherService 생성 (mock QFileSystemWatcher 사용)."""
    svc = object.__new__(FileWatcherService)
    svc._repo_path = Path(repo_path)
    svc._git_dir = Path(repo_path) / ".git"
    svc._watcher = MockQFileSystemWatcher()
    svc._debounce_timer = MockQTimer()
    svc._debounce_timer.timeout.connect(svc._flush_events if hasattr(svc, '_flush_events') else lambda: None)
    svc._pending_paths = set()

    # Signal mocks
    svc.commit_detected = MagicMock()
    svc.branch_changed = MagicMock()
    svc.push_detected = MagicMock()
    svc.stash_changed = MagicMock()
    svc.merge_started = MagicMock()
    svc.rebase_started = MagicMock()
    svc.repository_changed = MagicMock()
    return svc


# ─── start_watching / stop_watching ─────────────────────────────────────────

class TestStartStopWatching:
    def test_start_adds_paths(self, git_repo):
        svc = _make_watcher(git_repo)
        svc.start_watching()
        watched = svc._watcher.files() + svc._watcher.directories()
        assert len(watched) > 0

    def test_start_watches_head(self, git_repo):
        svc = _make_watcher(git_repo)
        svc.start_watching()
        watched = svc._watcher.files()
        head_path = str(git_repo / ".git" / "HEAD")
        assert head_path in watched

    def test_start_watches_commit_editmsg(self, git_repo):
        svc = _make_watcher(git_repo)
        svc.start_watching()
        watched = svc._watcher.files()
        assert any("COMMIT_EDITMSG" in p for p in watched)

    def test_stop_clears_paths(self, git_repo):
        svc = _make_watcher(git_repo)
        svc.start_watching()
        svc.stop_watching()
        # After stop, no paths watched
        assert len(svc._watcher.files()) == 0

    def test_stop_clears_pending(self, git_repo):
        svc = _make_watcher(git_repo)
        svc._pending_paths = {"some/path"}
        svc.stop_watching()
        assert len(svc._pending_paths) == 0

    def test_no_error_when_git_dir_missing(self, tmp_path):
        svc = _make_watcher(tmp_path)
        svc.start_watching()  # should not raise
        assert len(svc._watcher.files()) == 0


# ─── 이벤트 분류 테스트 ──────────────────────────────────────────────────────

class TestClassifyAndEmit:
    def test_commit_editmsg_emits_commit_detected(self, git_repo):
        svc = _make_watcher(git_repo)
        path = str(git_repo / ".git" / "COMMIT_EDITMSG")
        svc._classify_and_emit(path)
        svc.commit_detected.emit.assert_called_once()

    def test_head_change_emits_branch_changed(self, git_repo):
        svc = _make_watcher(git_repo)
        path = str(git_repo / ".git" / "HEAD")
        svc._classify_and_emit(path)
        svc.branch_changed.emit.assert_called_once()

    def test_stash_change_emits_stash_changed(self, git_repo):
        svc = _make_watcher(git_repo)
        stash_path = git_repo / ".git" / "refs" / "stash"
        stash_path.write_text("abc123\n")
        svc._classify_and_emit(str(stash_path))
        svc.stash_changed.emit.assert_called_once()

    def test_merge_head_emits_merge_started(self, git_repo):
        svc = _make_watcher(git_repo)
        merge_path = git_repo / ".git" / "MERGE_HEAD"
        merge_path.write_text("abc123\n")
        svc._classify_and_emit(str(merge_path))
        svc.merge_started.emit.assert_called_once()

    def test_rebase_head_emits_rebase_started(self, git_repo):
        svc = _make_watcher(git_repo)
        rebase_path = git_repo / ".git" / "REBASE_HEAD"
        rebase_path.write_text("abc123\n")
        svc._classify_and_emit(str(rebase_path))
        svc.rebase_started.emit.assert_called_once()

    def test_refs_heads_dir_emits_push_detected(self, git_repo):
        svc = _make_watcher(git_repo)
        heads_path = str(git_repo / ".git" / "refs" / "heads")
        svc._classify_and_emit(heads_path)
        svc.push_detected.emit.assert_called_once()


# ─── _flush_events ───────────────────────────────────────────────────────────

class TestFlushEvents:
    def test_flush_emits_repository_changed(self, git_repo):
        svc = _make_watcher(git_repo)
        commit_path = str(git_repo / ".git" / "COMMIT_EDITMSG")
        svc._pending_paths = {commit_path}
        svc._flush_events()
        svc.repository_changed.emit.assert_called()

    def test_flush_clears_pending_paths(self, git_repo):
        svc = _make_watcher(git_repo)
        svc._pending_paths = {"some/path"}
        svc._flush_events()
        assert len(svc._pending_paths) == 0

    def test_flush_with_empty_pending_does_not_emit(self, git_repo):
        svc = _make_watcher(git_repo)
        svc._pending_paths = set()
        svc._flush_events()
        svc.repository_changed.emit.assert_not_called()


# ─── _read_head_branch ───────────────────────────────────────────────────────

class TestReadHeadBranch:
    def test_reads_branch_from_head(self, git_repo):
        (git_repo / ".git" / "HEAD").write_text("ref: refs/heads/develop\n")
        svc = _make_watcher(git_repo)
        assert svc._read_head_branch() == "develop"

    def test_reads_feature_branch(self, git_repo):
        (git_repo / ".git" / "HEAD").write_text("ref: refs/heads/feature/login\n")
        svc = _make_watcher(git_repo)
        assert svc._read_head_branch() == "feature/login"

    def test_detached_head_returns_short_hash(self, git_repo):
        (git_repo / ".git" / "HEAD").write_text("abc1234def5678901234\n")
        svc = _make_watcher(git_repo)
        result = svc._read_head_branch()
        assert len(result) <= 7

    def test_missing_head_returns_unknown(self, tmp_path):
        svc = _make_watcher(tmp_path)
        assert svc._read_head_branch() == "unknown"
