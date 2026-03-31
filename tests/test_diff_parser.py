"""DiffParser 단위 테스트."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.domain.diff_parser import DiffParser
from app.domain.models import FileDiff, DiffHunk, DiffLine


# ─── 픽스처 ─────────────────────────────────────────────────────────────────

SIMPLE_DIFF = """\
diff --git a/app/main.py b/app/main.py
index abc1234..def5678 100644
--- a/app/main.py
+++ b/app/main.py
@@ -1,5 +1,6 @@
 import os
-import sys
+import sys
+import logging

 def main():
     pass
"""

MULTI_FILE_DIFF = """\
diff --git a/foo.py b/foo.py
index 1111111..2222222 100644
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,3 @@
 def foo():
-    return 1
+    return 2
diff --git a/bar.py b/bar.py
index 3333333..4444444 100644
--- a/bar.py
+++ b/bar.py
@@ -1,2 +1,3 @@
 def bar():
+    x = 1
     pass
"""

NEW_FILE_DIFF = """\
diff --git a/new_file.py b/new_file.py
new file mode 100644
index 0000000..abcdef0
--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,3 @@
+def hello():
+    print("hello")
+    return True
"""

DELETED_FILE_DIFF = """\
diff --git a/old_file.py b/old_file.py
deleted file mode 100644
index abcdef0..0000000
--- a/old_file.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def goodbye():
-    pass
"""

BINARY_DIFF = """\
diff --git a/image.png b/image.png
index abc..def 100644
Binary files a/image.png and b/image.png differ
"""

RENAMED_DIFF = """\
diff --git a/old_name.py b/new_name.py
similarity index 95%
rename from old_name.py
rename to new_name.py
index abc..def 100644
--- a/old_name.py
+++ b/new_name.py
@@ -1,3 +1,3 @@
 def func():
-    return "old"
+    return "new"
"""

MULTI_HUNK_DIFF = """\
diff --git a/big_file.py b/big_file.py
index aaa..bbb 100644
--- a/big_file.py
+++ b/big_file.py
@@ -1,4 +1,4 @@
 line1
-line2_old
+line2_new
 line3
 line4
@@ -10,4 +10,4 @@
 line10
-line11_old
+line11_new
 line12
 line13
"""


def _make_parser(raw_diff: str = "") -> DiffParser:
    """mock GitRepository를 사용하는 DiffParser 생성."""
    repo = MagicMock()
    repo.get_raw_diff.return_value = raw_diff
    return DiffParser(repo)


# ─── 기본 파싱 테스트 ────────────────────────────────────────────────────────

class TestDiffParserBasic:
    def test_empty_diff_returns_empty_list(self):
        parser = _make_parser("")
        result = parser.parse_raw("")
        assert result == []

    def test_whitespace_only_returns_empty_list(self):
        parser = _make_parser()
        assert parser.parse_raw("   \n  \n") == []

    def test_simple_diff_returns_one_file(self):
        parser = _make_parser()
        result = parser.parse_raw(SIMPLE_DIFF)
        assert len(result) == 1

    def test_simple_diff_file_path(self):
        parser = _make_parser()
        result = parser.parse_raw(SIMPLE_DIFF)
        assert result[0].old_path == "app/main.py"
        assert result[0].new_path == "app/main.py"

    def test_simple_diff_status_modified(self):
        parser = _make_parser()
        result = parser.parse_raw(SIMPLE_DIFF)
        assert result[0].status == "modified"

    def test_simple_diff_has_one_hunk(self):
        parser = _make_parser()
        result = parser.parse_raw(SIMPLE_DIFF)
        assert len(result[0].hunks) == 1

    def test_simple_diff_not_binary(self):
        parser = _make_parser()
        result = parser.parse_raw(SIMPLE_DIFF)
        assert result[0].is_binary is False


# ─── 라인 타입 파싱 ──────────────────────────────────────────────────────────

class TestDiffLineTypes:
    def setup_method(self):
        self.parser = _make_parser()
        self.result = self.parser.parse_raw(SIMPLE_DIFF)
        self.hunk = self.result[0].hunks[0]

    def test_has_context_lines(self):
        context = [l for l in self.hunk.lines if l.type == "context"]
        assert len(context) > 0

    def test_has_add_lines(self):
        added = [l for l in self.hunk.lines if l.type == "add"]
        assert len(added) > 0

    def test_has_delete_lines(self):
        deleted = [l for l in self.hunk.lines if l.type == "delete"]
        assert len(deleted) > 0

    def test_add_line_has_new_line_no(self):
        added = [l for l in self.hunk.lines if l.type == "add"]
        for line in added:
            assert line.new_line_no is not None
            assert line.old_line_no is None

    def test_delete_line_has_old_line_no(self):
        deleted = [l for l in self.hunk.lines if l.type == "delete"]
        for line in deleted:
            assert line.old_line_no is not None
            assert line.new_line_no is None

    def test_context_line_has_both_line_nos(self):
        context = [l for l in self.hunk.lines if l.type == "context"]
        for line in context:
            assert line.old_line_no is not None
            assert line.new_line_no is not None


# ─── 멀티 파일 diff ──────────────────────────────────────────────────────────

class TestMultiFileDiff:
    def test_two_files_returned(self):
        parser = _make_parser()
        result = parser.parse_raw(MULTI_FILE_DIFF)
        assert len(result) == 2

    def test_first_file_path(self):
        parser = _make_parser()
        result = parser.parse_raw(MULTI_FILE_DIFF)
        assert result[0].old_path == "foo.py"

    def test_second_file_path(self):
        parser = _make_parser()
        result = parser.parse_raw(MULTI_FILE_DIFF)
        assert result[1].old_path == "bar.py"


# ─── 파일 상태 파싱 ──────────────────────────────────────────────────────────

class TestFileStatus:
    def test_new_file_status_added(self):
        parser = _make_parser()
        result = parser.parse_raw(NEW_FILE_DIFF)
        assert result[0].status == "added"

    def test_new_file_has_add_lines(self):
        parser = _make_parser()
        result = parser.parse_raw(NEW_FILE_DIFF)
        lines = result[0].hunks[0].lines
        assert all(l.type == "add" for l in lines)

    def test_deleted_file_status(self):
        parser = _make_parser()
        result = parser.parse_raw(DELETED_FILE_DIFF)
        assert result[0].status == "deleted"

    def test_deleted_file_has_delete_lines(self):
        parser = _make_parser()
        result = parser.parse_raw(DELETED_FILE_DIFF)
        lines = result[0].hunks[0].lines
        assert all(l.type == "delete" for l in lines)

    def test_binary_file_detected(self):
        parser = _make_parser()
        result = parser.parse_raw(BINARY_DIFF)
        assert result[0].is_binary is True

    def test_binary_file_no_hunks(self):
        parser = _make_parser()
        result = parser.parse_raw(BINARY_DIFF)
        assert len(result[0].hunks) == 0

    def test_renamed_file_status(self):
        parser = _make_parser()
        result = parser.parse_raw(RENAMED_DIFF)
        assert result[0].status == "renamed"

    def test_renamed_file_similarity(self):
        parser = _make_parser()
        result = parser.parse_raw(RENAMED_DIFF)
        assert result[0].similarity == 95


# ─── 멀티 hunk ───────────────────────────────────────────────────────────────

class TestMultiHunk:
    def test_two_hunks_in_one_file(self):
        parser = _make_parser()
        result = parser.parse_raw(MULTI_HUNK_DIFF)
        assert len(result[0].hunks) == 2

    def test_first_hunk_start_line(self):
        parser = _make_parser()
        result = parser.parse_raw(MULTI_HUNK_DIFF)
        assert result[0].hunks[0].old_start == 1
        assert result[0].hunks[0].new_start == 1

    def test_second_hunk_start_line(self):
        parser = _make_parser()
        result = parser.parse_raw(MULTI_HUNK_DIFF)
        assert result[0].hunks[1].old_start == 10
        assert result[0].hunks[1].new_start == 10


# ─── GitRepository 연동 ──────────────────────────────────────────────────────

class TestDiffParserWithRepo:
    def test_parse_working_tree_calls_get_raw_diff(self):
        repo = MagicMock()
        repo.get_raw_diff.return_value = SIMPLE_DIFF
        parser = DiffParser(repo)
        result = parser.parse_working_tree()
        repo.get_raw_diff.assert_called_once_with(staged=False)
        assert len(result) == 1

    def test_parse_staged_calls_staged_flag(self):
        repo = MagicMock()
        repo.get_raw_diff.return_value = ""
        parser = DiffParser(repo)
        parser.parse_staged()
        repo.get_raw_diff.assert_called_once_with(staged=True)

    def test_parse_commit_passes_hash(self):
        repo = MagicMock()
        repo.get_raw_diff.return_value = ""
        parser = DiffParser(repo)
        parser.parse_commit("abc1234")
        repo.get_raw_diff.assert_called_once_with(commit_hash="abc1234")

    def test_parse_range_passes_hashes(self):
        repo = MagicMock()
        repo.get_raw_diff.return_value = ""
        parser = DiffParser(repo)
        parser.parse_range("aaa", "bbb")
        repo.get_raw_diff.assert_called_once_with(from_hash="aaa", to_hash="bbb")


# ─── 라인 번호 정확성 ────────────────────────────────────────────────────────

class TestLineNumbers:
    def test_new_file_line_numbers_start_at_1(self):
        parser = _make_parser()
        result = parser.parse_raw(NEW_FILE_DIFF)
        lines = result[0].hunks[0].lines
        assert lines[0].new_line_no == 1
        assert lines[1].new_line_no == 2
        assert lines[2].new_line_no == 3

    def test_deleted_file_old_line_numbers(self):
        parser = _make_parser()
        result = parser.parse_raw(DELETED_FILE_DIFF)
        lines = result[0].hunks[0].lines
        assert lines[0].old_line_no == 1
        assert lines[1].old_line_no == 2

    def test_hunk_line_count_field(self):
        parser = _make_parser()
        result = parser.parse_raw(SIMPLE_DIFF)
        hunk = result[0].hunks[0]
        assert hunk.old_start == 1
        assert hunk.old_count == 5
        assert hunk.new_start == 1
        assert hunk.new_count == 6
