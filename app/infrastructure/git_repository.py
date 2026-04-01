"""GitRepository — GitPython 기반 저장소 접근 추상화."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import git
from git import InvalidGitRepositoryError, NoSuchPathError

from app.domain.models import BranchSummary, Commit


class GitRepositoryError(Exception):
    """저장소 접근 관련 예외."""


class GitRepository:
    """GitPython 래핑. UI/Domain 계층에서 직접 git 명령 사용 금지."""

    def __init__(self, repo_path: str) -> None:
        self._path = Path(repo_path)
        try:
            self._repo = git.Repo(repo_path, search_parent_directories=True)
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            raise GitRepositoryError(f"Git 저장소를 찾을 수 없습니다: {repo_path}") from e

    @property
    def path(self) -> Path:
        return self._path

    def get_current_branch(self) -> str:
        """현재 체크아웃된 브랜치명 반환. HEAD detached 시 'HEAD' 반환."""
        try:
            return self._repo.active_branch.name
        except TypeError:
            return "HEAD (detached)"

    def get_branches(self, remote: bool = False) -> list[str]:
        """로컬 또는 리모트 브랜치 목록 반환."""
        if remote:
            return [ref.name for ref in self._repo.remotes[0].refs] if self._repo.remotes else []
        return [branch.name for branch in self._repo.branches]

    def get_commit_log(self, limit: int = 20) -> list[Commit]:
        """최근 N개 커밋 목록 반환."""
        commits = []
        for c in self._repo.iter_commits(max_count=limit):
            commits.append(
                Commit(
                    hash=c.hexsha,
                    short_hash=c.hexsha[:7],
                    message=c.message.strip(),
                    author=str(c.author),
                    date=datetime.fromtimestamp(c.authored_date),
                )
            )
        return commits

    def get_status(self) -> bool:
        """작업 디렉토리에 미커밋 변경사항이 있으면 True."""
        return self._repo.is_dirty(untracked_files=True)

    def get_ahead_behind(self, remote_branch: str = "origin/develop") -> tuple[int, int]:
        """현재 브랜치와 remote_branch 간 ahead/behind 커밋 수 반환."""
        try:
            current = self._repo.active_branch.name
            # git rev-list 로 계산
            ahead = list(self._repo.iter_commits(f"{remote_branch}..{current}"))
            behind = list(self._repo.iter_commits(f"{current}..{remote_branch}"))
            return len(ahead), len(behind)
        except Exception:
            return 0, 0

    def get_branch_summary(self) -> BranchSummary:
        """브랜치 상태 요약 반환 (BranchManager에서 사용)."""
        current = self.get_current_branch()
        ahead, behind = self.get_ahead_behind()
        is_dirty = self.get_status()
        local = self.get_branches(remote=False)
        remote = self.get_branches(remote=True)
        return BranchSummary(
            current=current,
            ahead=ahead,
            behind=behind,
            is_dirty=is_dirty,
            local_branches=local,
            remote_branches=remote,
        )

    def get_hook_path(self, hook_name: str) -> Path | None:
        """Git 훅 스크립트 경로 반환. 없거나 실행 불가면 None."""
        try:
            git_dir = Path(str(self._repo.git_dir))
            hook = git_dir / "hooks" / hook_name
            if hook.exists() and hook.is_file():
                return hook
        except Exception:
            pass
        return None

    def has_branch(self, name: str) -> bool:
        """로컬 브랜치 존재 여부 확인."""
        return name in [b.name for b in self._repo.branches]

    def create_branch(self, name: str, base: str | None = None) -> None:
        """브랜치 생성 후 체크아웃. base가 None이면 현재 HEAD 기준."""
        if self.has_branch(name):
            raise GitRepositoryError(f"브랜치가 이미 존재합니다: {name}")
        if base:
            candidates = [b for b in self._repo.branches if b.name == base]
            base_ref = candidates[0] if candidates else self._repo.active_branch
        else:
            base_ref = self._repo.active_branch
        new_branch = self._repo.create_head(name, base_ref)
        new_branch.checkout()

    def get_diff_stats(self, base_branch: str = "develop") -> dict:
        """현재 브랜치와 base_branch 간 변경 파일 통계 반환."""
        try:
            base = self._repo.commit(base_branch)
            head = self._repo.head.commit
            diff = base.diff(head)
            return {
                "files_changed": len(diff),
                "insertions": sum(d.diff.count(b"\n+") for d in diff if d.diff),
                "deletions": sum(d.diff.count(b"\n-") for d in diff if d.diff),
            }
        except Exception:
            return {"files_changed": 0, "insertions": 0, "deletions": 0}

    def get_recent_commit_messages(self, limit: int = 20) -> list[str]:
        """최근 N개 커밋 메시지 반환."""
        return [c.message.strip() for c in self._repo.iter_commits(max_count=limit)]

    def fetch(self) -> None:
        """origin 리모트 fetch."""
        if self._repo.remotes:
            self._repo.remotes.origin.fetch()

    def pull(self, branch: str = "develop") -> int:
        """지정 브랜치를 pull하고 당겨온 커밋 수 반환."""
        before = self._repo.head.commit
        origin = self._repo.remotes.origin
        origin.pull(branch)
        after = self._repo.head.commit
        return sum(1 for _ in self._repo.iter_commits(f"{before}..{after}"))

    # ─── v2.0 확장 메서드 ────────────────────────────────────────────────────

    def get_raw_diff(
        self,
        staged: bool = False,
        commit_hash: str | None = None,
        from_hash: str | None = None,
        to_hash: str | None = None,
        file_path: str | None = None,
    ) -> str:
        """git diff 원시 텍스트 반환.

        - staged=True: git diff --cached
        - commit_hash: git diff <hash>~1 <hash>
        - from_hash + to_hash: git diff <from>..<to>
        - 기본: git diff (working tree)
        """
        try:
            args = []
            if staged:
                args.append("--cached")
            elif commit_hash:
                args.extend([f"{commit_hash}~1", commit_hash])
            elif from_hash and to_hash:
                args.extend([from_hash, to_hash])

            if file_path:
                args.extend(["--", file_path])

            return self._repo.git.diff(*args)
        except Exception:
            return ""

    def get_commit_log_with_parents(self, limit: int = 200) -> list[dict]:
        """커밋 로그 + 부모 해시 목록 반환 (그래프 빌더용).

        Returns list of dicts: {hash, short_hash, message, author, date, parents}
        """
        result = []
        try:
            for c in self._repo.iter_commits(
                topo_order=True, max_count=limit, all=True
            ):
                result.append({
                    "hash": c.hexsha,
                    "short_hash": c.hexsha[:7],
                    "message": c.message.strip(),
                    "author": str(c.author),
                    "date": datetime.fromtimestamp(c.authored_date),
                    "parents": [p.hexsha for p in c.parents],
                })
        except Exception:
            pass
        return result

    def get_all_refs(self) -> dict[str, str]:
        """브랜치/태그명 → 커밋 해시 매핑 반환."""
        refs: dict[str, str] = {}
        try:
            for ref in self._repo.references:
                refs[ref.name] = ref.commit.hexsha
        except Exception:
            pass
        return refs

    def get_stash_list(self) -> list[dict]:
        """git stash list 파싱 결과 반환.

        Returns list of dicts: {index, message, branch, ref}
        """
        result = []
        try:
            raw = self._repo.git.stash("list", "--format=%gd|||%s|||%gs")
            for line in raw.splitlines():
                if not line.strip():
                    continue
                parts = line.split("|||")
                ref = parts[0].strip() if len(parts) > 0 else ""
                subject = parts[1].strip() if len(parts) > 1 else ""
                reflog_subject = parts[2].strip() if len(parts) > 2 else ""

                # stash@{0}: WIP on branch: message
                index = 0
                branch = "unknown"
                if ref.startswith("stash@{") and ref.endswith("}"):
                    try:
                        index = int(ref[7:-1])
                    except ValueError:
                        pass

                if reflog_subject.startswith("WIP on "):
                    branch = reflog_subject[7:].split(":")[0].strip()

                result.append({
                    "index": index,
                    "message": subject,
                    "branch": branch,
                    "ref": ref,
                })
        except Exception:
            pass
        return result

    def create_stash(self, message: str = "", include_untracked: bool = True) -> bool:
        """현재 변경사항을 stash로 저장."""
        try:
            args = ["push"]
            if include_untracked:
                args.append("--include-untracked")
            if message:
                args.extend(["-m", message])
            self._repo.git.stash(*args)
            return True
        except Exception:
            return False

    def apply_stash(self, index: int = 0, pop: bool = False) -> bool:
        """stash 적용 (apply 또는 pop)."""
        try:
            ref = f"stash@{{{index}}}"
            if pop:
                self._repo.git.stash("pop", ref)
            else:
                self._repo.git.stash("apply", ref)
            return True
        except Exception:
            return False

    def drop_stash(self, index: int) -> bool:
        """stash 삭제."""
        try:
            self._repo.git.stash("drop", f"stash@{{{index}}}")
            return True
        except Exception:
            return False

    def show_stash(self, index: int = 0) -> str:
        """stash 내용 diff 텍스트 반환."""
        try:
            return self._repo.git.stash("show", "-p", f"stash@{{{index}}}")
        except Exception:
            return ""

    def get_git_dir(self) -> str:
        """git 디렉토리 경로 반환 (.git 폴더)."""
        return str(self._repo.git_dir)

    def checkout_branch(self, branch_name: str) -> bool:
        """브랜치 체크아웃."""
        try:
            self._repo.git.checkout(branch_name)
            return True
        except Exception:
            return False

    def get_stash_count(self) -> int:
        """stash 개수 반환."""
        try:
            raw = self._repo.git.stash("list")
            return len([l for l in raw.splitlines() if l.strip()])
        except Exception:
            return 0

    def get_worktrees(self) -> list[dict]:
        """연결된 worktree 목록 반환.

        Returns:
            list of {"path": str, "branch": str, "commit": str, "is_main": bool, "is_locked": bool}
        """
        try:
            raw = self._repo.git.worktree("list", "--porcelain")
        except Exception:
            return []

        worktrees = []
        current: dict = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                if current:
                    worktrees.append(current)
                    current = {}
            elif line.startswith("worktree "):
                current["path"] = line[len("worktree "):]
            elif line.startswith("HEAD "):
                current["commit"] = line[5:12]  # short hash
            elif line.startswith("branch "):
                current["branch"] = line[7:].replace("refs/heads/", "")
            elif line == "bare":
                current["branch"] = "(bare)"
            elif line == "detached":
                current["branch"] = "(detached)"
            elif line == "locked":
                current["is_locked"] = True
        if current:
            worktrees.append(current)

        # 첫 번째가 main worktree
        for i, wt in enumerate(worktrees):
            wt.setdefault("branch", "(unknown)")
            wt.setdefault("commit", "???????")
            wt.setdefault("is_locked", False)
            wt["is_main"] = i == 0

        return worktrees

    # ─── F-20: Commit Workflow ───────────────────────────────────────────────

    def get_working_tree_status(self) -> list[dict]:
        """워킹 트리 파일별 Stage 상태 반환.

        Returns:
            list of {"path": str, "staged": bool, "unstaged": bool, "status": str}
            status: "M"(modified) | "A"(added) | "D"(deleted) | "R"(renamed) | "?"(untracked)
        """
        result: list[dict] = []
        try:
            # porcelain 형식: "XY path" (X=staged, Y=unstaged)
            raw = self._repo.git.status("--porcelain", "-u")
            for line in raw.splitlines():
                if not line:
                    continue
                x, y = line[0], line[1]
                path = line[3:]
                # rename 처리: "old -> new"
                if " -> " in path:
                    path = path.split(" -> ")[1]
                staged = x != " " and x != "?"
                unstaged = y != " " or x == "?"
                status = x if staged else (y if y != " " else "?")
                result.append({
                    "path": path.strip(),
                    "staged": staged,
                    "unstaged": unstaged,
                    "status": status,
                })
        except Exception:
            pass
        return result

    def stage_file(self, path: str) -> bool:
        """특정 파일 stage (git add)."""
        try:
            self._repo.git.add(path)
            return True
        except Exception:
            return False

    def unstage_file(self, path: str) -> bool:
        """특정 파일 unstage (git reset HEAD)."""
        try:
            self._repo.git.reset("HEAD", "--", path)
            return True
        except Exception:
            return False

    def stage_all(self) -> bool:
        """전체 변경사항 stage (git add -A)."""
        try:
            self._repo.git.add("-A")
            return True
        except Exception:
            return False

    def unstage_all(self) -> bool:
        """전체 stage 취소 (git reset HEAD)."""
        try:
            self._repo.git.reset("HEAD")
            return True
        except Exception:
            return False

    def discard_file(self, path: str) -> bool:
        """워킹 트리 변경사항 되돌리기 (git checkout -- path)."""
        try:
            self._repo.git.checkout("--", path)
            return True
        except Exception:
            return False

    def commit(self, message: str, amend: bool = False) -> tuple[bool, str]:
        """커밋 실행.

        Returns:
            (success: bool, message: str)
        """
        if not message.strip() and not amend:
            return False, "커밋 메시지를 입력하세요."
        try:
            args = ["commit"]
            if amend:
                args.append("--amend")
                if message.strip():
                    args.extend(["-m", message])
                else:
                    args.append("--no-edit")
            else:
                args.extend(["-m", message])
            result = self._repo.git.execute(["git"] + args)
            return True, result
        except Exception as e:
            return False, str(e)

    def get_last_commit_message(self) -> str:
        """마지막 커밋 메시지 반환 (amend 용)."""
        try:
            return self._repo.git.log("-1", "--format=%s%n%n%b").strip()
        except Exception:
            return ""

    def push(self, remote: str = "origin", branch: str | None = None) -> tuple[bool, str]:
        """git push 실행.

        Returns:
            (success: bool, message: str)
        """
        try:
            args = ["push", remote]
            if branch:
                args.append(branch)
            result = self._repo.git.execute(["git"] + args)
            return True, result or "Push 완료"
        except Exception as e:
            return False, str(e)
