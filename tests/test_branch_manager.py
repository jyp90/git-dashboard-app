"""BranchManager 단위 테스트."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.domain.branch_manager import BranchManager
from app.domain.models import BranchResult, SyncResult
from app.infrastructure.git_repository import GitRepositoryError


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def manager(mock_repo):
    return BranchManager(mock_repo)


# ── sync_develop ─────────────────────────────────────────────────────────────

class TestSyncDevelop:
    def test_on_develop_pulls_and_returns_count(self, manager, mock_repo):
        mock_repo.get_current_branch.return_value = "develop"
        mock_repo.pull.return_value = 3
        result = manager.sync_develop()
        assert result.success
        assert result.commits_pulled == 3
        assert "3" in result.message

    def test_on_develop_already_up_to_date(self, manager, mock_repo):
        mock_repo.get_current_branch.return_value = "develop"
        mock_repo.pull.return_value = 0
        result = manager.sync_develop()
        assert result.success
        assert result.commits_pulled == 0
        assert "최신" in result.message

    def test_on_feature_branch_fetch_only(self, manager, mock_repo):
        mock_repo.get_current_branch.return_value = "feature/foo"
        result = manager.sync_develop()
        assert result.success
        assert result.commits_pulled == 0
        mock_repo.pull.assert_not_called()
        assert "fetch" in result.message.lower() or "origin" in result.message

    def test_fetch_error_returns_failure(self, manager, mock_repo):
        mock_repo.fetch.side_effect = GitRepositoryError("network error")
        result = manager.sync_develop()
        assert not result.success
        assert "network error" in result.message

    def test_generic_exception_returns_failure(self, manager, mock_repo):
        mock_repo.fetch.side_effect = RuntimeError("unexpected")
        result = manager.sync_develop()
        assert not result.success
        assert "동기화 실패" in result.message


# ── create_release_branch ────────────────────────────────────────────────────

class TestCreateReleaseBranch:
    def test_creates_with_develop_base(self, manager, mock_repo):
        mock_repo.get_branches.return_value = ["main", "develop", "feature/x"]
        result = manager.create_release_branch("1.2.0")
        mock_repo.create_branch.assert_called_once_with("release/1.2.0", "develop")
        assert result.success
        assert result.branch_name == "release/1.2.0"

    def test_creates_without_develop_uses_none(self, manager, mock_repo):
        mock_repo.get_branches.return_value = ["main"]
        result = manager.create_release_branch("1.0.0")
        mock_repo.create_branch.assert_called_once_with("release/1.0.0", None)
        assert result.success

    def test_already_exists_returns_failure(self, manager, mock_repo):
        mock_repo.get_branches.return_value = ["develop"]
        mock_repo.create_branch.side_effect = GitRepositoryError(
            "브랜치가 이미 존재합니다: release/1.0.0"
        )
        result = manager.create_release_branch("1.0.0")
        assert not result.success
        assert "이미 존재" in result.message

    def test_branch_name_format(self, manager, mock_repo):
        mock_repo.get_branches.return_value = []
        manager.create_release_branch("2.3.1")
        args = mock_repo.create_branch.call_args[0]
        assert args[0] == "release/2.3.1"


# ── create_hotfix_branch ─────────────────────────────────────────────────────

class TestCreateHotfixBranch:
    def test_creates_from_main(self, manager, mock_repo):
        mock_repo.get_branches.return_value = ["main", "develop"]
        result = manager.create_hotfix_branch("fix-login")
        mock_repo.create_branch.assert_called_once_with("hotfix/fix-login", "main")
        assert result.success
        assert result.branch_name == "hotfix/fix-login"

    def test_creates_from_master_when_no_main(self, manager, mock_repo):
        mock_repo.get_branches.return_value = ["master", "develop"]
        result = manager.create_hotfix_branch("fix-crash")
        mock_repo.create_branch.assert_called_once_with("hotfix/fix-crash", "master")
        assert result.success

    def test_creates_from_none_when_no_main_or_master(self, manager, mock_repo):
        mock_repo.get_branches.return_value = ["develop", "feature/x"]
        result = manager.create_hotfix_branch("issue-42")
        mock_repo.create_branch.assert_called_once_with("hotfix/issue-42", None)

    def test_prefers_main_over_master(self, manager, mock_repo):
        mock_repo.get_branches.return_value = ["main", "master", "develop"]
        manager.create_hotfix_branch("critical")
        args = mock_repo.create_branch.call_args[0]
        assert args[1] == "main"

    def test_failure_propagated(self, manager, mock_repo):
        mock_repo.get_branches.return_value = ["main"]
        mock_repo.create_branch.side_effect = GitRepositoryError("permission denied")
        result = manager.create_hotfix_branch("fix")
        assert not result.success
        assert "permission denied" in result.message
