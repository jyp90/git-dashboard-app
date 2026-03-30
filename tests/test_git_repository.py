"""GitRepository 유닛 테스트 — 실제 Git 저장소 대신 임시 저장소 사용."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from app.infrastructure.git_repository import GitRepository, GitRepositoryError


@pytest.fixture
def tmp_repo(tmp_path: Path):
    """임시 Git 저장소 생성 (기본 커밋 포함)."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True, capture_output=True)
    (tmp_path / "README.md").write_text("# test")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "feat: initial commit"], check=True, capture_output=True)
    return tmp_path


class TestGitRepositoryInit:
    def test_valid_repo(self, tmp_repo):
        repo = GitRepository(str(tmp_repo))
        assert repo.path == tmp_repo

    def test_invalid_path_raises(self, tmp_path):
        with pytest.raises(GitRepositoryError):
            GitRepository(str(tmp_path / "nonexistent"))

    def test_non_git_dir_raises(self, tmp_path):
        with pytest.raises(GitRepositoryError):
            GitRepository(str(tmp_path))


class TestBranchInfo:
    def test_get_current_branch(self, tmp_repo):
        repo = GitRepository(str(tmp_repo))
        # git init 기본 브랜치는 master 또는 main
        branch = repo.get_current_branch()
        assert isinstance(branch, str)
        assert len(branch) > 0

    def test_get_local_branches(self, tmp_repo):
        repo = GitRepository(str(tmp_repo))
        branches = repo.get_branches(remote=False)
        assert isinstance(branches, list)
        assert len(branches) >= 1

    def test_get_remote_branches_empty(self, tmp_repo):
        repo = GitRepository(str(tmp_repo))
        remote = repo.get_branches(remote=True)
        assert remote == []  # 리모트 없는 로컬 저장소


class TestCommitLog:
    def test_get_commit_log(self, tmp_repo):
        repo = GitRepository(str(tmp_repo))
        commits = repo.get_commit_log(limit=10)
        assert len(commits) == 1
        assert commits[0].message == "feat: initial commit"
        assert len(commits[0].short_hash) == 7

    def test_multiple_commits(self, tmp_repo):
        (tmp_path := tmp_repo / "b.txt").write_text("b")
        subprocess.run(["git", "-C", str(tmp_repo), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_repo), "commit", "-m", "feat: second"], check=True, capture_output=True)
        repo = GitRepository(str(tmp_repo))
        commits = repo.get_commit_log(limit=10)
        assert len(commits) == 2


class TestRepoStatus:
    def test_clean_repo(self, tmp_repo):
        repo = GitRepository(str(tmp_repo))
        assert repo.get_status() is False

    def test_dirty_repo(self, tmp_repo):
        (tmp_repo / "dirty.txt").write_text("untracked")
        repo = GitRepository(str(tmp_repo))
        assert repo.get_status() is True


class TestBranchSummary:
    def test_get_branch_summary(self, tmp_repo):
        repo = GitRepository(str(tmp_repo))
        summary = repo.get_branch_summary()
        assert summary.ahead == 0
        assert summary.behind == 0
        assert summary.is_dirty is False
        assert len(summary.local_branches) >= 1
