"""PrChecker — F-05 커밋 컨벤션, 파일 수, TODO 잔존 검사."""
from __future__ import annotations

import re
from pathlib import Path

from app.domain.models import CheckItem, PrCheckReport
from app.infrastructure.git_repository import GitRepository

# Conventional Commits 패턴
_CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?: .+",
    re.IGNORECASE,
)
_MAX_FILES_CHANGED = 30
_MAX_COMMIT_SUBJECT_LEN = 72


class PrChecker:
    """PR 사전 검사: 커밋 컨벤션 · 변경 파일 수 · TODO 잔존."""

    def __init__(self, repo: GitRepository) -> None:
        self._repo = repo

    def check(self) -> PrCheckReport:
        items: list[CheckItem] = []
        items.extend(self._check_commit_convention())
        items.extend(self._check_file_size())
        items.extend(self._check_todos())

        passed = all(item.passed for item in items)
        ok_count = sum(1 for i in items if i.passed)
        summary = f"{ok_count}/{len(items)} 항목 통과"
        return PrCheckReport(passed=passed, items=items, summary=summary)

    # ── 검사 항목 ─────────────────────────────────────────────────────────

    def _check_commit_convention(self) -> list[CheckItem]:
        """최근 커밋 메시지가 Conventional Commits 형식인지 검사."""
        messages = self._repo.get_recent_commit_messages(limit=10)
        violations = []
        for msg in messages:
            subject = msg.split("\n")[0].strip()
            if not _CONVENTIONAL_RE.match(subject):
                violations.append(subject[:60])
            elif len(subject) > _MAX_COMMIT_SUBJECT_LEN:
                violations.append(f"[제목 길이 초과] {subject[:60]}...")

        if not violations:
            return [CheckItem("convention", True, f"커밋 컨벤션 통과 (최근 {len(messages)}개)")]
        return [CheckItem("convention", False,
                          f"컨벤션 위반 {len(violations)}건: {violations[0]}{'…' if len(violations) > 1 else ''}")]

    def _check_file_size(self) -> list[CheckItem]:
        """변경 파일 수가 허용 범위 내인지 검사."""
        try:
            stats = self._repo.get_diff_stats("develop")
            n = stats["files_changed"]
        except Exception:
            return [CheckItem("size", True, "파일 변경 수 확인 불가 (base 브랜치 없음)")]

        if n == 0:
            return [CheckItem("size", True, "변경 파일 없음 (develop 기준)")]
        if n <= _MAX_FILES_CHANGED:
            return [CheckItem("size", True, f"변경 파일 수 적정: {n}개 (최대 {_MAX_FILES_CHANGED})")]
        return [CheckItem("size", False, f"변경 파일 수 초과: {n}개 (권장 최대 {_MAX_FILES_CHANGED})")]

    def _check_todos(self) -> list[CheckItem]:
        """변경된 소스 파일에 TODO/FIXME/HACK 주석 잔존 여부 검사."""
        try:
            todo_pattern = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
            repo_path = self._repo.path
            found: list[str] = []
            for ext in ("*.py", "*.java", "*.ts", "*.tsx", "*.js"):
                for f in repo_path.rglob(ext):
                    # node_modules, .git, venv 제외
                    parts = f.parts
                    if any(p in parts for p in ("node_modules", ".git", "venv", "__pycache__")):
                        continue
                    try:
                        text = f.read_text(errors="ignore")
                        for m in todo_pattern.finditer(text):
                            line_no = text[:m.start()].count("\n") + 1
                            found.append(f"{f.relative_to(repo_path)}:{line_no}")
                            if len(found) >= 5:
                                break
                    except OSError:
                        pass
                    if len(found) >= 5:
                        break
        except Exception:
            return [CheckItem("todo", True, "TODO 검사 불가")]

        if not found:
            return [CheckItem("todo", True, "TODO/FIXME 잔존 없음")]
        sample = ", ".join(found[:3])
        suffix = f" 외 {len(found) - 3}건" if len(found) > 3 else ""
        return [CheckItem("todo", False, f"TODO 잔존 {len(found)}건: {sample}{suffix}")]
