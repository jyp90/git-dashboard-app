"""ConflictResolver 단위 테스트."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from app.domain.conflict_resolver import ConflictResolver
from app.domain.models import ConflictFile, ConflictRegion


# ─── 헬퍼 ───────────────────────────────────────────────────────────────────

def _make_resolver(git_status_output="", repo_path="/tmp/repo"):
    repo = MagicMock()
    repo._repo.git.status.return_value = git_status_output
    repo.path = Path(repo_path)
    return ConflictResolver(repo), repo


SIMPLE_CONFLICT = """\
line before
<<<<<<< HEAD
ours line 1
ours line 2
=======
theirs line 1
>>>>>>> feature
line after
"""

DIFF3_CONFLICT = """\
<<<<<<< HEAD
ours content
||||||| base
base content
=======
theirs content
>>>>>>> branch
"""

MULTI_CONFLICT = """\
start
<<<<<<< HEAD
a1
=======
b1
>>>>>>> feat
middle
<<<<<<< HEAD
a2
=======
b2
>>>>>>> feat
end
"""

NO_CONFLICT = """\
normal line 1
normal line 2
normal line 3
"""


# ─── detect_conflicts ────────────────────────────────────────────────────────

class TestDetectConflicts:
    def test_returns_uu_file(self):
        resolver, _ = _make_resolver("UU src/main.py")
        result = resolver.detect_conflicts()
        assert "src/main.py" in result

    def test_returns_aa_file(self):
        resolver, _ = _make_resolver("AA src/main.py")
        result = resolver.detect_conflicts()
        assert "src/main.py" in result

    def test_returns_dd_file(self):
        resolver, _ = _make_resolver("DD src/main.py")
        result = resolver.detect_conflicts()
        assert "src/main.py" in result

    def test_returns_au_file(self):
        resolver, _ = _make_resolver("AU src/main.py")
        result = resolver.detect_conflicts()
        assert "src/main.py" in result

    def test_returns_ua_file(self):
        resolver, _ = _make_resolver("UA src/main.py")
        result = resolver.detect_conflicts()
        assert "src/main.py" in result

    def test_ignores_modified_file(self):
        resolver, _ = _make_resolver(" M src/main.py")
        result = resolver.detect_conflicts()
        assert "src/main.py" not in result

    def test_returns_empty_on_clean_status(self):
        resolver, _ = _make_resolver("")
        result = resolver.detect_conflicts()
        assert result == []

    def test_returns_empty_on_git_exception(self):
        resolver, repo = _make_resolver()
        repo._repo.git.status.side_effect = Exception("git error")
        result = resolver.detect_conflicts()
        assert result == []

    def test_multiple_conflict_files(self):
        resolver, _ = _make_resolver("UU file1.py\nUU file2.py\n M clean.py")
        result = resolver.detect_conflicts()
        assert len(result) == 2
        assert "file1.py" in result
        assert "file2.py" in result

    def test_ignores_short_lines(self):
        resolver, _ = _make_resolver("U")
        result = resolver.detect_conflicts()
        assert result == []


# ─── parse_conflict ──────────────────────────────────────────────────────────

class TestParseConflict:
    def test_returns_conflict_file_instance(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, repo = _make_resolver(repo_path=str(tmp_path))
        result = resolver.parse_conflict("test.py")
        assert isinstance(result, ConflictFile)

    def test_detects_one_conflict_region(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        cf = resolver.parse_conflict("test.py")
        assert len(cf.conflicts) == 1

    def test_total_conflicts_count(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        cf = resolver.parse_conflict("test.py")
        assert cf.total_conflicts == 1

    def test_ours_content_parsed(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        cf = resolver.parse_conflict("test.py")
        ours = "".join(cf.conflicts[0].ours_content)
        assert "ours line 1" in ours

    def test_theirs_content_parsed(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        cf = resolver.parse_conflict("test.py")
        theirs = "".join(cf.conflicts[0].theirs_content)
        assert "theirs line 1" in theirs

    def test_diff3_base_content_parsed(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(DIFF3_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        cf = resolver.parse_conflict("test.py")
        base = "".join(cf.conflicts[0].base_content)
        assert "base content" in base

    def test_diff3_base_empty_without_marker(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        cf = resolver.parse_conflict("test.py")
        assert cf.conflicts[0].base_content == []

    def test_multi_conflict_detects_two_regions(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(MULTI_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        cf = resolver.parse_conflict("test.py")
        assert len(cf.conflicts) == 2

    def test_no_conflict_returns_empty(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(NO_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        cf = resolver.parse_conflict("test.py")
        assert cf.conflicts == []

    def test_file_not_found_returns_empty_conflict_file(self, tmp_path):
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        cf = resolver.parse_conflict("nonexistent.py")
        assert cf.conflicts == []
        assert cf.path == "nonexistent.py"

    def test_non_conflict_lines_present(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        cf = resolver.parse_conflict("test.py")
        # "line before" and "line after" should be in non_conflict_lines
        all_nc = "".join(text for _, _, text in cf.non_conflict_lines)
        assert "line before" in all_nc
        assert "line after" in all_nc

    def test_start_line_less_than_end_line(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        cf = resolver.parse_conflict("test.py")
        region = cf.conflicts[0]
        assert region.start_line < region.end_line


# ─── resolve_region ──────────────────────────────────────────────────────────

class TestResolveRegion:
    def test_resolve_ours(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        resolver.resolve_region("test.py", 0, "ours")
        result = f.read_text()
        assert "ours line 1" in result
        assert "<<<<<<< HEAD" not in result

    def test_resolve_theirs(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        resolver.resolve_region("test.py", 0, "theirs")
        result = f.read_text()
        assert "theirs line 1" in result
        assert "=======" not in result

    def test_resolve_both_contains_both(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        resolver.resolve_region("test.py", 0, "both")
        result = f.read_text()
        assert "ours line 1" in result
        assert "theirs line 1" in result

    def test_resolve_manual(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        resolver.resolve_region("test.py", 0, "manual", manual_content="custom resolution\n")
        result = f.read_text()
        assert "custom resolution" in result

    def test_raises_index_error_on_invalid_index(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        with pytest.raises(IndexError):
            resolver.resolve_region("test.py", 99, "ours")

    def test_non_conflict_lines_preserved(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        resolver.resolve_region("test.py", 0, "ours")
        result = f.read_text()
        assert "line before" in result
        assert "line after" in result


# ─── save_resolution ─────────────────────────────────────────────────────────

class TestSaveResolution:
    def test_writes_content_to_file(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("old content")
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        resolver.save_resolution("test.py", "new content\n")
        assert f.read_text() == "new content\n"

    def test_overwrites_conflict_markers(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SIMPLE_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        resolver.save_resolution("test.py", "clean content\n")
        assert "<<<<<<< HEAD" not in f.read_text()


# ─── mark_resolved ───────────────────────────────────────────────────────────

class TestMarkResolved:
    def test_calls_git_index_add(self):
        resolver, repo = _make_resolver()
        resolver.mark_resolved("src/main.py")
        repo._repo.index.add.assert_called_once_with(["src/main.py"])

    def test_raises_runtime_error_on_failure(self):
        resolver, repo = _make_resolver()
        repo._repo.index.add.side_effect = Exception("git error")
        with pytest.raises(RuntimeError, match="git add 실패"):
            resolver.mark_resolved("src/main.py")


# ─── resolve_all ─────────────────────────────────────────────────────────────

class TestResolveAll:
    def test_resolves_all_conflicts(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(MULTI_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        resolver.resolve_all("test.py", "ours")
        result = f.read_text()
        assert "<<<<<<< HEAD" not in result
        assert "=======" not in result

    def test_ours_content_preserved(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(MULTI_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        resolver.resolve_all("test.py", "ours")
        result = f.read_text()
        assert "a1" in result
        assert "a2" in result

    def test_theirs_resolution(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(MULTI_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        resolver.resolve_all("test.py", "theirs")
        result = f.read_text()
        assert "b1" in result
        assert "b2" in result

    def test_no_conflict_no_error(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(NO_CONFLICT)
        resolver, _ = _make_resolver(repo_path=str(tmp_path))
        resolver.resolve_all("test.py", "ours")  # should not raise
        assert f.read_text() == NO_CONFLICT


# ─── _pick_resolution ────────────────────────────────────────────────────────

class TestPickResolution:
    def _make_region(self):
        return ConflictRegion(
            start_line=0,
            end_line=5,
            ours_content=["ours\n"],
            base_content=["base\n"],
            theirs_content=["theirs\n"],
        )

    def test_ours(self):
        resolver, _ = _make_resolver()
        region = self._make_region()
        result = resolver._pick_resolution(region, "ours", None)
        assert result == ["ours\n"]

    def test_theirs(self):
        resolver, _ = _make_resolver()
        region = self._make_region()
        result = resolver._pick_resolution(region, "theirs", None)
        assert result == ["theirs\n"]

    def test_both(self):
        resolver, _ = _make_resolver()
        region = self._make_region()
        result = resolver._pick_resolution(region, "both", None)
        assert "ours\n" in result
        assert "theirs\n" in result

    def test_manual_with_content(self):
        resolver, _ = _make_resolver()
        region = self._make_region()
        result = resolver._pick_resolution(region, "manual", "manual content")
        assert any("manual content" in line for line in result)

    def test_manual_none_falls_back_to_ours(self):
        resolver, _ = _make_resolver()
        region = self._make_region()
        result = resolver._pick_resolution(region, "manual", None)
        assert result == ["ours\n"]

    def test_unknown_resolution_falls_back_to_ours(self):
        resolver, _ = _make_resolver()
        region = self._make_region()
        result = resolver._pick_resolution(region, "unknown", None)
        assert result == ["ours\n"]

    def test_manual_content_ends_with_newline(self):
        resolver, _ = _make_resolver()
        region = self._make_region()
        result = resolver._pick_resolution(region, "manual", "no newline")
        assert result[-1].endswith("\n")
