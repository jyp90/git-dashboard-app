"""RebaseOrchestrator — Interactive Rebase GUI 지원 도메인 클래스."""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from app.domain.models import RebasePlan, RebaseStep

if TYPE_CHECKING:
    from app.infrastructure.git_repository import GitRepository


class RebaseOrchestrator:
    """Interactive Rebase를 GUI에서 실행 가능하도록 관리한다.

    워크플로우:
    1. prepare(): 대상 커밋 범위를 분석하여 RebasePlan 초안 생성
    2. 사용자가 UI에서 plan 수정 (순서 변경, action 변경, 메시지 편집)
    3. execute(): 수정된 plan을 git rebase --interactive에 전달

    안전 장치:
    - 실행 전 현재 HEAD를 reflog로 기록
    - 실패 시 git rebase --abort 자동 실행
    - dirty working tree 시 실행 거부
    """

    VALID_ACTIONS = frozenset({"pick", "reword", "squash", "fixup", "drop", "edit"})

    def __init__(self, repository: "GitRepository") -> None:
        self._repo = repository

    def prepare(self, onto: str = "HEAD~10") -> RebasePlan:
        """rebase 대상 커밋을 분석하여 RebasePlan 초안 생성.

        Args:
            onto: rebase 기준점. "HEAD~N" 형식 또는 브랜치명/커밋 해시.

        Returns:
            RebasePlan: 각 커밋에 기본 action="pick"으로 초기화된 plan.

        Raises:
            ValueError: dirty working tree 시
        """
        if self._repo.get_status():
            raise ValueError(
                "미커밋 변경사항이 있어 Rebase를 시작할 수 없습니다.\n"
                "Stash 탭에서 변경사항을 임시 저장(Stash)한 후 다시 시도하세요."
            )

        commits = self._get_commits_since(onto)
        steps = [
            RebaseStep(
                action="pick",
                commit_hash=c["hash"],
                original_message=c["message"],
                new_message=None,
            )
            for c in commits
        ]
        return RebasePlan(base_commit=onto, steps=steps)

    def execute(self, plan: RebasePlan) -> bool:
        """plan을 실행한다.

        구현: GIT_SEQUENCE_EDITOR 환경변수를 설정하여
        git rebase -i에 plan을 자동 전달.
        (에디터 대신 스크립트가 todo 파일을 덮어쓰는 방식)

        Returns:
            True = 성공, False = 실패 (자동 abort 수행)
        """
        if not plan.steps:
            return False

        todo_content = self._generate_todo_content(plan)
        script_path = self._write_sequence_editor_script(todo_content)

        try:
            env = os.environ.copy()
            env["GIT_SEQUENCE_EDITOR"] = script_path

            result = subprocess.run(
                ["git", "rebase", "-i", plan.base_commit],
                cwd=str(self._repo.path),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                self.abort()
                return False

            return True

        except subprocess.TimeoutExpired:
            self.abort()
            return False
        except Exception:
            self.abort()
            return False
        finally:
            try:
                os.unlink(script_path)
            except OSError:
                pass

    def abort(self) -> bool:
        """진행 중인 rebase 중단."""
        try:
            result = subprocess.run(
                ["git", "rebase", "--abort"],
                cwd=str(self._repo.path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception:
            return False

    def continue_rebase(self) -> bool:
        """충돌 해결 후 rebase 계속."""
        try:
            result = subprocess.run(
                ["git", "rebase", "--continue"],
                cwd=str(self._repo.path),
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ, "GIT_EDITOR": "true"},  # 메시지 편집 스킵
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_rebase_status(self) -> dict | None:
        """현재 rebase 진행 상태.

        Returns:
            None: rebase 진행 중이 아님
            dict: {"step": int, "total": int, "current_hash": str}
        """
        git_dir = Path(self._repo.get_git_dir())
        rebase_merge = git_dir / "rebase-merge"
        rebase_apply = git_dir / "rebase-apply"

        rebase_dir = None
        if rebase_merge.exists():
            rebase_dir = rebase_merge
        elif rebase_apply.exists():
            rebase_dir = rebase_apply
        else:
            return None

        try:
            msgnum = int((rebase_dir / "msgnum").read_text().strip())
            end = int((rebase_dir / "end").read_text().strip())
            head_name = (rebase_dir / "head-name").read_text().strip()
            return {
                "step": msgnum,
                "total": end,
                "head_name": head_name,
            }
        except Exception:
            return {"step": 0, "total": 0, "head_name": "unknown"}

    # ─── 내부 헬퍼 ──────────────────────────────────────────────────────────

    def _get_commits_since(self, onto: str) -> list[dict]:
        """onto 이후의 커밋 목록 반환 (newest first)."""
        return self._repo.get_commit_log_with_parents(limit=50)[:self._parse_n(onto)]

    def _parse_n(self, onto: str) -> int:
        """HEAD~N 형식에서 N 추출. 기본 10."""
        if onto.startswith("HEAD~"):
            try:
                return int(onto[5:])
            except ValueError:
                pass
        return 10

    def _generate_todo_content(self, plan: RebasePlan) -> str:
        """plan을 git-rebase-todo 형식 문자열로 변환.

        형식:
            pick abc1234 feat: message
            squash def5678 fix: message
        """
        lines = []
        for step in plan.steps:
            if step.action not in self.VALID_ACTIONS:
                continue
            msg = (step.new_message or step.original_message).split("\n")[0][:72]
            short_hash = step.commit_hash[:7]
            lines.append(f"{step.action} {short_hash} {msg}")
        return "\n".join(lines) + "\n"

    def _write_sequence_editor_script(self, todo_content: str) -> str:
        """GIT_SEQUENCE_EDITOR로 사용할 임시 셸 스크립트 작성.

        스크립트는 git이 전달하는 todo 파일을 우리 내용으로 덮어씀.
        """
        # todo 내용을 별도 임시 파일에 저장
        with tempfile.NamedTemporaryFile(mode="w", suffix=".todo", delete=False) as todo_f:
            todo_f.write(todo_content)
            todo_path = todo_f.name

        # 셸 스크립트 작성: 인자로 받은 파일(git todo)을 우리 내용으로 교체
        script_content = f'#!/bin/sh\ncp "{todo_path}" "$1"\nrm -f "{todo_path}"\n'
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False, prefix="git_dashboard_rebase_"
        ) as script_f:
            script_f.write(script_content)
            script_path = script_f.name

        os.chmod(script_path, 0o755)
        return script_path
