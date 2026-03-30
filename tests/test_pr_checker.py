"""PrChecker 단위 테스트."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.domain.models import PrCheckReport
from app.domain.pr_checker import PrChecker


@pytest.fixture
def mock_repo(tmp_path):
    repo = MagicMock()
    repo.path = tmp_path
    return repo


@pytest.fixture
def checker(mock_repo):
    return PrChecker(mock_repo)


# ── PrCheckReport 모델 ────────────────────────────────────────────────────────

class TestPrCheckReportModel:
    def test_empty_classmethod(self):
        report = PrCheckReport.empty()
        assert report.passed
        assert report.items == []
        assert report.summary == "검사 항목 없음"

    def test_failed_report_is_false(self):
        from app.domain.models import CheckItem
        report = PrCheckReport(
            passed=False,
            items=[CheckItem("convention", False, "WIP commit")],
            summary="0/1 통과",
        )
        assert not report.passed


# ── 커밋 컨벤션 검사 ──────────────────────────────────────────────────────────

class TestCommitConvention:
    def test_valid_conventional_commits_pass(self, checker, mock_repo):
        mock_repo.get_recent_commit_messages.return_value = [
            "feat(auth): add login endpoint",
            "fix(ui): resolve button alignment",
            "chore: update dependencies",
            "refactor: extract helper function",
        ]
        mock_repo.get_diff_stats.return_value = {"files_changed": 2, "insertions": 10, "deletions": 1}
        report = checker.check()
        convention = next(i for i in report.items if i.category == "convention")
        assert convention.passed

    def test_invalid_commit_messages_fail(self, checker, mock_repo):
        mock_repo.get_recent_commit_messages.return_value = [
            "WIP some work",
            "fixed stuff",
            "updated things",
        ]
        mock_repo.get_diff_stats.return_value = {"files_changed": 0}
        report = checker.check()
        convention = next(i for i in report.items if i.category == "convention")
        assert not convention.passed
        assert "위반" in convention.message

    def test_empty_commit_list_passes(self, checker, mock_repo):
        mock_repo.get_recent_commit_messages.return_value = []
        mock_repo.get_diff_stats.return_value = {"files_changed": 0}
        report = checker.check()
        convention = next(i for i in report.items if i.category == "convention")
        assert convention.passed

    def test_mixed_commits_reports_violations(self, checker, mock_repo):
        mock_repo.get_recent_commit_messages.return_value = [
            "feat: valid",
            "bad commit message",
        ]
        mock_repo.get_diff_stats.return_value = {"files_changed": 1, "insertions": 5, "deletions": 0}
        report = checker.check()
        convention = next(i for i in report.items if i.category == "convention")
        assert not convention.passed


# ── 파일 변경 수 검사 ─────────────────────────────────────────────────────────

class TestFileSizeCheck:
    def test_within_limit_passes(self, checker, mock_repo):
        mock_repo.get_recent_commit_messages.return_value = ["feat: ok"]
        mock_repo.get_diff_stats.return_value = {"files_changed": 10, "insertions": 50, "deletions": 5}
        report = checker.check()
        size = next(i for i in report.items if i.category == "size")
        assert size.passed

    def test_zero_files_passes(self, checker, mock_repo):
        mock_repo.get_recent_commit_messages.return_value = ["feat: ok"]
        mock_repo.get_diff_stats.return_value = {"files_changed": 0, "insertions": 0, "deletions": 0}
        report = checker.check()
        size = next(i for i in report.items if i.category == "size")
        assert size.passed

    def test_exceeds_limit_fails(self, checker, mock_repo):
        mock_repo.get_recent_commit_messages.return_value = ["feat: ok"]
        mock_repo.get_diff_stats.return_value = {"files_changed": 50, "insertions": 500, "deletions": 100}
        report = checker.check()
        size = next(i for i in report.items if i.category == "size")
        assert not size.passed
        assert "50" in size.message

    def test_exactly_at_limit_passes(self, checker, mock_repo):
        mock_repo.get_recent_commit_messages.return_value = ["feat: ok"]
        mock_repo.get_diff_stats.return_value = {"files_changed": 30, "insertions": 100, "deletions": 20}
        report = checker.check()
        size = next(i for i in report.items if i.category == "size")
        assert size.passed

    def test_diff_stats_exception_passes_gracefully(self, checker, mock_repo):
        mock_repo.get_recent_commit_messages.return_value = ["feat: ok"]
        mock_repo.get_diff_stats.side_effect = Exception("no base branch")
        report = checker.check()
        size = next(i for i in report.items if i.category == "size")
        assert size.passed  # graceful fallback


# ── TODO 잔존 검사 ───────────────────────────────────────────────────────────

class TestTodoCheck:
    def test_no_todos_passes(self, checker, mock_repo, tmp_path):
        mock_repo.path = tmp_path
        mock_repo.get_recent_commit_messages.return_value = ["feat: ok"]
        mock_repo.get_diff_stats.return_value = {"files_changed": 1}
        # 파일 생성 (TODO 없음)
        (tmp_path / "clean.py").write_text("def hello():\n    return 'world'\n")
        report = checker.check()
        todo = next(i for i in report.items if i.category == "todo")
        assert todo.passed

    def test_todo_comment_fails(self, checker, mock_repo, tmp_path):
        mock_repo.path = tmp_path
        mock_repo.get_recent_commit_messages.return_value = ["feat: ok"]
        mock_repo.get_diff_stats.return_value = {"files_changed": 1}
        (tmp_path / "dirty.py").write_text("# TODO: fix this later\nx = 1\n")
        report = checker.check()
        todo = next(i for i in report.items if i.category == "todo")
        assert not todo.passed
        assert "dirty.py" in todo.message

    def test_fixme_comment_fails(self, checker, mock_repo, tmp_path):
        mock_repo.path = tmp_path
        mock_repo.get_recent_commit_messages.return_value = ["feat: ok"]
        mock_repo.get_diff_stats.return_value = {"files_changed": 1}
        (tmp_path / "code.py").write_text("# FIXME: broken logic\npass\n")
        report = checker.check()
        todo = next(i for i in report.items if i.category == "todo")
        assert not todo.passed


# ── 전체 리포트 ───────────────────────────────────────────────────────────────

class TestFullReport:
    def test_all_pass_report_is_passed(self, checker, mock_repo):
        mock_repo.get_recent_commit_messages.return_value = ["feat: clean"]
        mock_repo.get_diff_stats.return_value = {"files_changed": 5, "insertions": 20, "deletions": 2}
        report = checker.check()
        assert isinstance(report, PrCheckReport)
        assert len(report.items) == 3  # convention, size, todo
        assert report.summary.endswith("통과")

    def test_summary_format(self, checker, mock_repo):
        mock_repo.get_recent_commit_messages.return_value = ["feat: ok"]
        mock_repo.get_diff_stats.return_value = {"files_changed": 2}
        report = checker.check()
        assert "/" in report.summary
        assert "통과" in report.summary
