"""DiffParser — unified diff 텍스트를 구조화된 객체로 파싱."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.domain.models import DiffHunk, DiffLine, FileDiff

if TYPE_CHECKING:
    from app.infrastructure.git_repository import GitRepository


class DiffParser:
    """git diff 출력을 FileDiff 리스트로 파싱한다.

    지원 형식:
    - unified diff (git diff)
    - staged diff (git diff --cached)
    - commit diff (git diff <hash>~1 <hash>)
    - 파일 간 diff (git diff -- <path>)
    """

    def __init__(self, repository: "GitRepository") -> None:
        self._repo = repository

    # ─── Public API ─────────────────────────────────────────────────────────

    def parse_working_tree(self) -> list[FileDiff]:
        """워킹 트리 변경사항 파싱."""
        raw = self._repo.get_raw_diff(staged=False)
        return self._parse_unified_diff(raw)

    def parse_staged(self) -> list[FileDiff]:
        """스테이지된 변경사항 파싱."""
        raw = self._repo.get_raw_diff(staged=True)
        return self._parse_unified_diff(raw)

    def parse_commit(self, commit_hash: str) -> list[FileDiff]:
        """특정 커밋의 변경사항 파싱."""
        raw = self._repo.get_raw_diff(commit_hash=commit_hash)
        return self._parse_unified_diff(raw)

    def parse_range(self, from_hash: str, to_hash: str) -> list[FileDiff]:
        """커밋 범위의 변경사항 파싱."""
        raw = self._repo.get_raw_diff(from_hash=from_hash, to_hash=to_hash)
        return self._parse_unified_diff(raw)

    def parse_raw(self, raw_diff: str) -> list[FileDiff]:
        """raw diff 문자열을 직접 파싱 (테스트/외부 입력용)."""
        return self._parse_unified_diff(raw_diff)

    # ─── Internal ────────────────────────────────────────────────────────────

    def _parse_unified_diff(self, raw_diff: str) -> list[FileDiff]:
        """unified diff 텍스트를 FileDiff 리스트로 변환."""
        if not raw_diff.strip():
            return []

        result: list[FileDiff] = []
        current_file: FileDiff | None = None
        current_hunk: DiffHunk | None = None
        old_line = 0
        new_line = 0

        for line in raw_diff.splitlines():
            # ── 새 파일 diff 시작 ──────────────────────────────────────────
            if line.startswith("diff --git "):
                if current_file is not None:
                    if current_hunk is not None:
                        current_file.hunks.append(current_hunk)
                        current_hunk = None
                    result.append(current_file)

                match = re.match(r"diff --git a/(.*) b/(.*)", line)
                old_path = match.group(1) if match else ""
                new_path = match.group(2) if match else ""
                current_file = FileDiff(
                    old_path=old_path,
                    new_path=new_path,
                    status="modified",
                )
                continue

            if current_file is None:
                continue

            # ── 파일 상태 마커 ────────────────────────────────────────────
            if line.startswith("new file mode"):
                current_file.status = "added"
                continue
            if line.startswith("deleted file mode"):
                current_file.status = "deleted"
                continue
            if line.startswith("similarity index "):
                m = re.match(r"similarity index (\d+)%", line)
                if m:
                    current_file.similarity = int(m.group(1))
                    current_file.status = "renamed"
                continue
            if line.startswith("rename to "):
                current_file.new_path = line[len("rename to "):]
                continue
            if "Binary files" in line:
                current_file.is_binary = True
                continue
            if line.startswith("--- ") or line.startswith("+++ "):
                continue
            if line.startswith("index "):
                continue

            # ── hunk 헤더 ─────────────────────────────────────────────────
            if line.startswith("@@ "):
                if current_hunk is not None:
                    current_file.hunks.append(current_hunk)

                m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)", line)
                if m:
                    old_start = int(m.group(1))
                    old_count = int(m.group(2)) if m.group(2) is not None else 1
                    new_start = int(m.group(3))
                    new_count = int(m.group(4)) if m.group(4) is not None else 1
                    current_hunk = DiffHunk(
                        old_start=old_start,
                        old_count=old_count,
                        new_start=new_start,
                        new_count=new_count,
                        header=line,
                    )
                    old_line = old_start
                    new_line = new_start
                continue

            if current_hunk is None:
                continue

            # ── diff 라인 파싱 ────────────────────────────────────────────
            if line.startswith("+"):
                current_hunk.lines.append(DiffLine(
                    type="add",
                    content=line[1:],
                    old_line_no=None,
                    new_line_no=new_line,
                ))
                new_line += 1
            elif line.startswith("-"):
                current_hunk.lines.append(DiffLine(
                    type="delete",
                    content=line[1:],
                    old_line_no=old_line,
                    new_line_no=None,
                ))
                old_line += 1
            elif line.startswith(" "):
                current_hunk.lines.append(DiffLine(
                    type="context",
                    content=line[1:],
                    old_line_no=old_line,
                    new_line_no=new_line,
                ))
                old_line += 1
                new_line += 1
            elif line.startswith("\\"):
                # "\ No newline at end of file" — 무시
                pass

        # 마지막 파일/hunk 처리
        if current_file is not None:
            if current_hunk is not None:
                current_file.hunks.append(current_hunk)
            result.append(current_file)

        return result
