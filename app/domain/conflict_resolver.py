"""ConflictResolver — Git 머지 충돌 파싱 + 해결 도메인 클래스."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.domain.models import ConflictFile, ConflictRegion

if TYPE_CHECKING:
    from app.infrastructure.git_repository import GitRepository


class ConflictResolver:
    """Git 머지 충돌을 파싱하고 해결을 지원한다.

    워크플로우:
    1. detect_conflicts(): 충돌 파일 목록 조회
    2. parse_conflict(): 충돌 마커(<<<, ===, >>>)를 파싱하여 ConflictFile 생성
    3. resolve_region(): 사용자 선택(ours/theirs/both/manual)을 반영
    4. save_resolution(): 해결된 내용으로 파일 저장
    5. mark_resolved(): git add로 해결 완료 마킹

    지원 충돌 형식:
    <<<<<<< HEAD
    ... ours ...
    ||||||| base  (diff3 모드)
    ... base ...
    =======
    ... theirs ...
    >>>>>>> branch-name
    """

    # 충돌 마커 패턴
    MARKER_OURS = re.compile(r"^<{7}(.*)$")      # <<<<<<< HEAD
    MARKER_BASE = re.compile(r"^\|{7}(.*)$")     # ||||||| base (diff3)
    MARKER_SEP = re.compile(r"^={7}$")           # =======
    MARKER_THEIRS = re.compile(r"^>{7}(.*)$")    # >>>>>>> branch

    def __init__(self, repository: "GitRepository") -> None:
        self._repo = repository

    def detect_conflicts(self) -> list[str]:
        """충돌 상태인 파일 경로 목록 반환.

        `git status --porcelain` 출력에서 'U' 상태 파일 추출.
        """
        try:
            raw = self._repo._repo.git.status("--porcelain")
        except Exception:
            return []

        conflicted = []
        for line in raw.splitlines():
            if len(line) < 2:
                continue
            xy = line[:2]
            path = line[3:].strip()
            # UU, AA, DD, AU, UA, DU, UD = conflict states
            if "U" in xy or xy in ("AA", "DD"):
                conflicted.append(path)
        return conflicted

    def parse_conflict(self, file_path: str) -> ConflictFile:
        """충돌 파일을 파싱하여 ConflictFile 생성.

        파싱 대상 마커:
        <<<<<<< HEAD (또는 브랜치명)
        ... ours content ...
        ||||||| base  (diff3 모드 선택적)
        ... base content ...
        =======
        ... theirs content ...
        >>>>>>> theirs_branch
        """
        full_path = self._repo.path / file_path
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            return ConflictFile(path=file_path)

        lines = content.splitlines(keepends=True)
        conflicts: list[ConflictRegion] = []
        non_conflict: list[tuple[int, int, str]] = []

        i = 0
        nc_start = 0

        while i < len(lines):
            line = lines[i].rstrip("\n")

            if self.MARKER_OURS.match(line):
                # non-conflict 구간 저장
                if nc_start < i:
                    non_conflict.append((nc_start, i, "".join(lines[nc_start:i])))

                conflict_start = i
                ours: list[str] = []
                base: list[str] = []
                theirs: list[str] = []
                mode = "ours"
                i += 1

                while i < len(lines):
                    l = lines[i].rstrip("\n")

                    if self.MARKER_BASE.match(l):
                        mode = "base"
                        i += 1
                        continue
                    if self.MARKER_SEP.match(l):
                        mode = "theirs"
                        i += 1
                        continue
                    if self.MARKER_THEIRS.match(l):
                        i += 1
                        break

                    if mode == "ours":
                        ours.append(lines[i])
                    elif mode == "base":
                        base.append(lines[i])
                    elif mode == "theirs":
                        theirs.append(lines[i])
                    i += 1

                conflict_end = i
                conflicts.append(ConflictRegion(
                    start_line=conflict_start,
                    end_line=conflict_end,
                    ours_content=ours,
                    base_content=base,
                    theirs_content=theirs,
                ))
                nc_start = i
            else:
                i += 1

        # 남은 non-conflict 구간
        if nc_start < len(lines):
            non_conflict.append((nc_start, len(lines), "".join(lines[nc_start:])))

        return ConflictFile(
            path=file_path,
            conflicts=conflicts,
            non_conflict_lines=non_conflict,
            total_conflicts=len(conflicts),
        )

    def resolve_region(
        self,
        file_path: str,
        region_index: int,
        resolution: str,
        manual_content: str | None = None,
    ) -> None:
        """충돌 영역 하나를 해결한다.

        Args:
            file_path: 파일 경로
            region_index: 충돌 영역 인덱스 (0-based)
            resolution: "ours" | "theirs" | "both" | "manual"
            manual_content: resolution="manual" 시 사용할 내용
        """
        conflict_file = self.parse_conflict(file_path)
        if region_index >= len(conflict_file.conflicts):
            raise IndexError(f"충돌 영역 {region_index}이 범위를 벗어남")

        full_path = self._repo.path / file_path
        content = full_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines(keepends=True)

        region = conflict_file.conflicts[region_index]
        resolved_lines = self._pick_resolution(region, resolution, manual_content)

        # 충돌 마커 블록을 해결된 내용으로 교체
        new_lines = lines[:region.start_line] + resolved_lines + lines[region.end_line:]
        full_path.write_text("".join(new_lines), encoding="utf-8")

    def save_resolution(self, file_path: str, resolved_content: str) -> None:
        """해결된 전체 내용으로 파일 저장."""
        full_path = self._repo.path / file_path
        full_path.write_text(resolved_content, encoding="utf-8")

    def mark_resolved(self, file_path: str) -> None:
        """git add로 충돌 해결 완료 처리."""
        try:
            self._repo._repo.index.add([file_path])
        except Exception as e:
            raise RuntimeError(f"git add 실패: {e}") from e

    def resolve_all(self, file_path: str, resolution: str) -> None:
        """파일의 모든 충돌을 동일한 방식으로 해결.

        Args:
            resolution: "ours" | "theirs" | "both"
        """
        conflict_file = self.parse_conflict(file_path)
        # 역순으로 처리해야 라인 번호가 유지됨
        for i in range(len(conflict_file.conflicts) - 1, -1, -1):
            self.resolve_region(file_path, i, resolution)

    # ─── 내부 헬퍼 ──────────────────────────────────────────────────────────

    def _pick_resolution(
        self,
        region: ConflictRegion,
        resolution: str,
        manual_content: str | None,
    ) -> list[str]:
        """resolution 선택에 따라 최종 라인 목록 반환."""
        if resolution == "ours":
            return list(region.ours_content)
        if resolution == "theirs":
            return list(region.theirs_content)
        if resolution == "both":
            return list(region.ours_content) + list(region.theirs_content)
        if resolution == "manual" and manual_content is not None:
            lines = manual_content.splitlines(keepends=True)
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            return lines
        # 기본: ours
        return list(region.ours_content)
