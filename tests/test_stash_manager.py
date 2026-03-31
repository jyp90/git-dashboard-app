"""StashManager 단위 테스트."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch, call

import pytest

from app.domain.stash_manager import StashManager
from app.domain.models import StashEntry


# ─── 헬퍼 ───────────────────────────────────────────────────────────────────

def _make_manager(stash_list=None, create_ok=True, apply_ok=True, drop_ok=True, show_raw=""):
    repo = MagicMock()
    repo.get_stash_list.return_value = stash_list or []
    repo.create_stash.return_value = create_ok
    repo.apply_stash.return_value = apply_ok
    repo.drop_stash.return_value = drop_ok
    repo.show_stash.return_value = show_raw
    return StashManager(repo), repo


SAMPLE_STASH_LIST = [
    {"index": 0, "message": "stash@{0}: WIP on develop: fix login", "branch": "develop", "ref": "stash@{0}"},
    {"index": 1, "message": "stash@{1}: WIP on feature/foo: add bar", "branch": "feature/foo", "ref": "stash@{1}"},
]


# ─── list_stashes ────────────────────────────────────────────────────────────

class TestListStashes:
    def test_empty_stash_returns_empty_list(self):
        manager, _ = _make_manager(stash_list=[])
        assert manager.list_stashes() == []

    def test_returns_stash_entries(self):
        manager, _ = _make_manager(stash_list=SAMPLE_STASH_LIST)
        result = manager.list_stashes()
        assert len(result) == 2

    def test_stash_entry_type(self):
        manager, _ = _make_manager(stash_list=SAMPLE_STASH_LIST)
        result = manager.list_stashes()
        assert all(isinstance(e, StashEntry) for e in result)

    def test_first_stash_index(self):
        manager, _ = _make_manager(stash_list=SAMPLE_STASH_LIST)
        result = manager.list_stashes()
        assert result[0].index == 0

    def test_second_stash_index(self):
        manager, _ = _make_manager(stash_list=SAMPLE_STASH_LIST)
        result = manager.list_stashes()
        assert result[1].index == 1

    def test_stash_branch(self):
        manager, _ = _make_manager(stash_list=SAMPLE_STASH_LIST)
        result = manager.list_stashes()
        assert result[0].branch == "develop"
        assert result[1].branch == "feature/foo"

    def test_calls_repo_get_stash_list(self):
        manager, repo = _make_manager()
        manager.list_stashes()
        repo.get_stash_list.assert_called_once()


# ─── create_stash ────────────────────────────────────────────────────────────

class TestCreateStash:
    def test_create_success_returns_stash_entry(self):
        manager, repo = _make_manager(
            stash_list=SAMPLE_STASH_LIST,
            create_ok=True,
        )
        result = manager.create_stash(message="my stash")
        assert result is not None
        assert isinstance(result, StashEntry)

    def test_create_failure_returns_none(self):
        manager, _ = _make_manager(create_ok=False)
        result = manager.create_stash()
        assert result is None

    def test_create_calls_repo_with_message(self):
        manager, repo = _make_manager(stash_list=SAMPLE_STASH_LIST)
        manager.create_stash(message="test message")
        repo.create_stash.assert_called_once_with(
            message="test message",
            include_untracked=True,
        )

    def test_create_with_include_untracked_false(self):
        manager, repo = _make_manager(stash_list=SAMPLE_STASH_LIST)
        manager.create_stash(include_untracked=False)
        repo.create_stash.assert_called_once_with(
            message="",
            include_untracked=False,
        )

    def test_create_empty_stash_list_returns_none(self):
        manager, repo = _make_manager(stash_list=[], create_ok=True)
        result = manager.create_stash()
        assert result is None


# ─── apply_stash ─────────────────────────────────────────────────────────────

class TestApplyStash:
    def test_apply_success_returns_true(self):
        manager, _ = _make_manager(apply_ok=True)
        assert manager.apply_stash(0) is True

    def test_apply_failure_returns_false(self):
        manager, _ = _make_manager(apply_ok=False)
        assert manager.apply_stash(0) is False

    def test_apply_calls_repo_with_index(self):
        manager, repo = _make_manager()
        manager.apply_stash(index=2)
        repo.apply_stash.assert_called_once_with(index=2, pop=False)

    def test_pop_calls_repo_with_pop_true(self):
        manager, repo = _make_manager()
        manager.apply_stash(index=0, pop=True)
        repo.apply_stash.assert_called_once_with(index=0, pop=True)

    def test_apply_default_index_zero(self):
        manager, repo = _make_manager()
        manager.apply_stash()
        repo.apply_stash.assert_called_once_with(index=0, pop=False)


# ─── drop_stash ──────────────────────────────────────────────────────────────

class TestDropStash:
    def test_drop_success_returns_true(self):
        manager, _ = _make_manager(drop_ok=True)
        assert manager.drop_stash(0) is True

    def test_drop_failure_returns_false(self):
        manager, _ = _make_manager(drop_ok=False)
        assert manager.drop_stash(0) is False

    def test_drop_calls_repo_with_index(self):
        manager, repo = _make_manager()
        manager.drop_stash(index=3)
        repo.drop_stash.assert_called_once_with(index=3)


# ─── show_stash ──────────────────────────────────────────────────────────────

SAMPLE_STASH_DIFF = """\
diff --git a/test.py b/test.py
index abc..def 100644
--- a/test.py
+++ b/test.py
@@ -1,2 +1,3 @@
 def test():
+    x = 1
     pass
"""


class TestShowStash:
    def test_show_empty_stash_returns_empty_list(self):
        manager, _ = _make_manager(show_raw="")
        result = manager.show_stash(0)
        assert result == []

    def test_show_stash_returns_file_diffs(self):
        manager, repo = _make_manager(show_raw=SAMPLE_STASH_DIFF)
        result = manager.show_stash(0)
        assert len(result) == 1
        assert result[0].old_path == "test.py"

    def test_show_calls_repo_with_index(self):
        manager, repo = _make_manager(show_raw="")
        manager.show_stash(index=2)
        repo.show_stash.assert_called_once_with(index=2)


# ─── get_stash_count ─────────────────────────────────────────────────────────

class TestGetStashCount:
    def test_empty_returns_zero(self):
        manager, _ = _make_manager(stash_list=[])
        assert manager.get_stash_count() == 0

    def test_two_stashes_returns_two(self):
        manager, _ = _make_manager(stash_list=SAMPLE_STASH_LIST)
        assert manager.get_stash_count() == 2
