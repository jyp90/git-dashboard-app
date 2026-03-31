"""RebaseOrchestrator 단위 테스트."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from app.domain.models import RebasePlan, RebaseStep
from app.domain.rebase_orchestrator import RebaseOrchestrator


# ─── 헬퍼 ───────────────────────────────────────────────────────────────────

def _make_commit(hash_: str, msg: str = "feat: commit") -> dict:
    return {
        "hash": hash_,
        "short_hash": hash_[:7],
        "message": msg,
        "author": "jypark",
        "date": datetime(2024, 1, 1),
        "parents": [],
    }


def _make_orchestrator(commits=None, is_dirty=False, git_dir="/tmp/.git"):
    repo = MagicMock()
    repo.get_status.return_value = is_dirty
    repo.get_commit_log_with_parents.return_value = commits or []
    repo.path = Path("/tmp/repo")
    repo.get_git_dir.return_value = git_dir
    return RebaseOrchestrator(repo), repo


SAMPLE_COMMITS = [
    _make_commit("aaa0001", "feat: add login"),
    _make_commit("bbb0002", "fix: login typo"),
    _make_commit("ccc0003", "feat: add dashboard"),
    _make_commit("ddd0004", "WIP: temp"),
    _make_commit("eee0005", "chore: cleanup"),
]


# ─── prepare ─────────────────────────────────────────────────────────────────

class TestPrepare:
    def test_returns_rebase_plan(self):
        orc, _ = _make_orchestrator(commits=SAMPLE_COMMITS)
        plan = orc.prepare("HEAD~5")
        assert isinstance(plan, RebasePlan)

    def test_all_steps_have_pick_action(self):
        orc, _ = _make_orchestrator(commits=SAMPLE_COMMITS)
        plan = orc.prepare("HEAD~5")
        assert all(s.action == "pick" for s in plan.steps)

    def test_steps_have_correct_hashes(self):
        orc, _ = _make_orchestrator(commits=SAMPLE_COMMITS)
        plan = orc.prepare("HEAD~5")
        hashes = [s.commit_hash for s in plan.steps]
        assert "aaa0001" in hashes

    def test_steps_have_messages(self):
        orc, _ = _make_orchestrator(commits=SAMPLE_COMMITS)
        plan = orc.prepare("HEAD~5")
        msgs = [s.original_message for s in plan.steps]
        assert "feat: add login" in msgs

    def test_raises_on_dirty_working_tree(self):
        orc, _ = _make_orchestrator(commits=SAMPLE_COMMITS, is_dirty=True)
        with pytest.raises(ValueError, match="dirty"):
            orc.prepare()

    def test_empty_commits_returns_empty_plan(self):
        orc, _ = _make_orchestrator(commits=[])
        plan = orc.prepare("HEAD~0")
        assert plan.steps == []

    def test_base_commit_set(self):
        orc, _ = _make_orchestrator(commits=SAMPLE_COMMITS)
        plan = orc.prepare("HEAD~3")
        assert plan.base_commit == "HEAD~3"

    def test_default_onto_is_head10(self):
        orc, repo = _make_orchestrator(commits=SAMPLE_COMMITS)
        plan = orc.prepare()
        assert plan.base_commit == "HEAD~10"


# ─── _generate_todo_content ─────────────────────────────────────────────────

class TestGenerateTodoContent:
    def test_pick_line_format(self):
        orc, _ = _make_orchestrator()
        plan = RebasePlan(
            base_commit="HEAD~1",
            steps=[RebaseStep("pick", "aaa0001", "feat: add login")],
        )
        content = orc._generate_todo_content(plan)
        assert "pick aaa0001 feat: add login" in content

    def test_squash_action(self):
        orc, _ = _make_orchestrator()
        plan = RebasePlan(
            base_commit="HEAD~2",
            steps=[
                RebaseStep("pick", "aaa0001", "feat: feature"),
                RebaseStep("squash", "bbb0002", "fix: squash me"),
            ],
        )
        content = orc._generate_todo_content(plan)
        assert "squash bbb0002" in content

    def test_drop_action(self):
        orc, _ = _make_orchestrator()
        plan = RebasePlan(
            base_commit="HEAD~1",
            steps=[RebaseStep("drop", "ccc0003", "WIP: skip")],
        )
        content = orc._generate_todo_content(plan)
        assert "drop ccc0003" in content

    def test_new_message_used_for_reword(self):
        orc, _ = _make_orchestrator()
        plan = RebasePlan(
            base_commit="HEAD~1",
            steps=[RebaseStep("reword", "aaa0001", "original", new_message="updated msg")],
        )
        content = orc._generate_todo_content(plan)
        assert "updated msg" in content

    def test_invalid_action_skipped(self):
        orc, _ = _make_orchestrator()
        plan = RebasePlan(
            base_commit="HEAD~1",
            steps=[RebaseStep("invalid_action", "aaa0001", "msg")],
        )
        content = orc._generate_todo_content(plan)
        assert "invalid_action" not in content

    def test_long_message_truncated_to_72(self):
        orc, _ = _make_orchestrator()
        long_msg = "feat: " + "x" * 100
        plan = RebasePlan(
            base_commit="HEAD~1",
            steps=[RebaseStep("pick", "aaa0001", long_msg)],
        )
        content = orc._generate_todo_content(plan)
        # action + hash + space = 13 chars, message should be max 72
        line = content.strip().split("\n")[0]
        # message part (after "pick aaa0001 ") should be <= 72
        msg_part = line[len("pick aaa0001 "):]
        assert len(msg_part) <= 72

    def test_ends_with_newline(self):
        orc, _ = _make_orchestrator()
        plan = RebasePlan(
            base_commit="HEAD~1",
            steps=[RebaseStep("pick", "aaa0001", "msg")],
        )
        content = orc._generate_todo_content(plan)
        assert content.endswith("\n")

    def test_multiline_message_uses_first_line(self):
        orc, _ = _make_orchestrator()
        plan = RebasePlan(
            base_commit="HEAD~1",
            steps=[RebaseStep("pick", "aaa0001", "first line\nsecond line\nthird")],
        )
        content = orc._generate_todo_content(plan)
        assert "first line" in content
        assert "second line" not in content


# ─── abort / continue ────────────────────────────────────────────────────────

class TestAbortContinue:
    def test_abort_calls_git_rebase_abort(self):
        orc, _ = _make_orchestrator()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = orc.abort()
        assert result is True
        cmd = mock_run.call_args[0][0]
        assert "rebase" in cmd
        assert "--abort" in cmd

    def test_abort_returns_false_on_error(self):
        orc, _ = _make_orchestrator()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = orc.abort()
        assert result is False

    def test_abort_handles_exception(self):
        orc, _ = _make_orchestrator()
        with patch("subprocess.run", side_effect=Exception("error")):
            result = orc.abort()
        assert result is False

    def test_continue_calls_git_rebase_continue(self):
        orc, _ = _make_orchestrator()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = orc.continue_rebase()
        assert result is True
        cmd = mock_run.call_args[0][0]
        assert "--continue" in cmd


# ─── get_rebase_status ───────────────────────────────────────────────────────

class TestGetRebaseStatus:
    def test_returns_none_when_not_rebasing(self, tmp_path):
        orc, _ = _make_orchestrator(git_dir=str(tmp_path))
        assert orc.get_rebase_status() is None

    def test_returns_status_when_rebase_merge_exists(self, tmp_path):
        rebase_dir = tmp_path / "rebase-merge"
        rebase_dir.mkdir()
        (rebase_dir / "msgnum").write_text("2\n")
        (rebase_dir / "end").write_text("5\n")
        (rebase_dir / "head-name").write_text("refs/heads/feature\n")

        orc, _ = _make_orchestrator(git_dir=str(tmp_path))
        status = orc.get_rebase_status()
        assert status is not None
        assert status["step"] == 2
        assert status["total"] == 5

    def test_returns_status_when_rebase_apply_exists(self, tmp_path):
        rebase_dir = tmp_path / "rebase-apply"
        rebase_dir.mkdir()
        (rebase_dir / "msgnum").write_text("1\n")
        (rebase_dir / "end").write_text("3\n")
        (rebase_dir / "head-name").write_text("refs/heads/main\n")

        orc, _ = _make_orchestrator(git_dir=str(tmp_path))
        status = orc.get_rebase_status()
        assert status is not None
        assert status["step"] == 1


# ─── _parse_n ────────────────────────────────────────────────────────────────

class TestParseN:
    def test_head_tilde_5(self):
        orc, _ = _make_orchestrator()
        assert orc._parse_n("HEAD~5") == 5

    def test_head_tilde_10(self):
        orc, _ = _make_orchestrator()
        assert orc._parse_n("HEAD~10") == 10

    def test_branch_name_defaults_to_10(self):
        orc, _ = _make_orchestrator()
        assert orc._parse_n("develop") == 10

    def test_invalid_format_defaults_to_10(self):
        orc, _ = _make_orchestrator()
        assert orc._parse_n("HEAD~abc") == 10


# ─── _write_sequence_editor_script ──────────────────────────────────────────

class TestWriteSequenceEditorScript:
    def test_creates_executable_script(self, tmp_path):
        orc, _ = _make_orchestrator()
        path = orc._write_sequence_editor_script("pick abc1234 msg\n")
        try:
            assert os.path.exists(path)
            assert os.access(path, os.X_OK)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_script_starts_with_shebang(self, tmp_path):
        orc, _ = _make_orchestrator()
        path = orc._write_sequence_editor_script("pick abc1234 msg\n")
        try:
            content = Path(path).read_text()
            assert content.startswith("#!/bin/sh")
        finally:
            if os.path.exists(path):
                os.unlink(path)
