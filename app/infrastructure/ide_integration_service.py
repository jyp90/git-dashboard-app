"""IdeIntegrationService — IntelliJ IDEA 연동 서비스."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class IdeIntegrationService:
    """IntelliJ IDEA와의 양방향 통합을 관리한다.

    연동 방식:
    1. IDE → Dashboard: FileWatcherService로 .git 디렉토리 변경 감지
    2. Dashboard → IDE: IntelliJ CLI(`idea`)로 프로젝트/파일 열기

    지원 IDE:
    - IntelliJ IDEA (Community / Ultimate)
    - JetBrains Toolbox를 통해 설치된 IDE
    """

    # JetBrains IDE CLI 탐색 경로 (macOS)
    IDE_SEARCH_PATHS = [
        "/usr/local/bin/idea",
        "/Applications/IntelliJ IDEA.app/Contents/MacOS/idea",
        "/Applications/IntelliJ IDEA CE.app/Contents/MacOS/idea",
        str(Path.home() / "Library/Application Support/JetBrains/Toolbox/scripts/idea"),
        str(Path.home() / "Library/Application Support/JetBrains/Toolbox/scripts/pycharm"),
        str(Path.home() / "Library/Application Support/JetBrains/Toolbox/scripts/webstorm"),
    ]

    def __init__(self) -> None:
        self._ide_path: str | None = None
        self._discover_ide()

    def is_available(self) -> bool:
        """IntelliJ CLI가 사용 가능한지 확인."""
        return self._ide_path is not None

    def get_ide_info(self) -> dict:
        """IDE 이름, 버전, 경로 정보 반환."""
        if not self._ide_path:
            return {"available": False, "path": None, "name": None, "version": None}

        name = self._detect_ide_name(self._ide_path)
        version = self._get_ide_version()
        return {
            "available": True,
            "path": self._ide_path,
            "name": name,
            "version": version,
        }

    # ─── Dashboard → IDE ────────────────────────────────────────────────────

    def open_project(self, project_path: str) -> bool:
        """IntelliJ에서 프로젝트 열기."""
        if not self._ide_path:
            return False
        try:
            subprocess.Popen(
                [self._ide_path, project_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False

    def open_file(self, file_path: str, line: int = 0) -> bool:
        """IntelliJ에서 특정 파일 열기 (줄 번호 지정 가능)."""
        if not self._ide_path:
            return False
        try:
            args = [self._ide_path]
            if line > 0:
                args.extend(["--line", str(line)])
            args.append(file_path)
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def run_in_terminal(self, command: str, project_path: str) -> bool:
        """IntelliJ 내장 터미널에서 명령 실행.

        JetBrains REST API (localhost:63342)를 통해 터미널 명령 전달.
        API 미사용 시 AppleScript로 fallback.
        """
        # REST API 시도
        if self._try_rest_api_terminal(command):
            return True
        # AppleScript fallback
        return self._try_applescript_terminal(command, project_path)

    def setup_git_hooks(self, repo_path: str) -> bool:
        """post-commit, post-push 훅 설치.

        IDE에서 커밋/푸시 시 대시보드가 .git 변경을 FileWatcherService로 감지.
        (추가로 hook 파일에 신호 기록)
        """
        git_dir = Path(repo_path) / ".git"
        if not git_dir.exists():
            return False

        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        hook_content = "#!/bin/sh\n# git-dashboard hook\n# FileWatcherService will detect .git changes automatically\nexit 0\n"
        try:
            for hook_name in ["post-commit", "post-push"]:
                hook_path = hooks_dir / hook_name
                hook_path.write_text(hook_content)
                hook_path.chmod(0o755)
            return True
        except Exception:
            return False

    # ─── 내부 헬퍼 ──────────────────────────────────────────────────────────

    def _discover_ide(self) -> None:
        """시스템에서 IntelliJ CLI 탐색."""
        # 1. PATH에서 idea 탐색
        in_path = shutil.which("idea")
        if in_path:
            self._ide_path = in_path
            return

        # 2. 알려진 경로 탐색
        for path in self.IDE_SEARCH_PATHS:
            expanded = os.path.expanduser(path)
            if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
                self._ide_path = expanded
                return

        self._ide_path = None

    def _detect_ide_name(self, path: str) -> str:
        """경로에서 IDE 이름 추론."""
        lower = path.lower()
        if "pycharm" in lower:
            return "PyCharm"
        if "webstorm" in lower:
            return "WebStorm"
        if "ce" in lower or "community" in lower:
            return "IntelliJ IDEA Community"
        return "IntelliJ IDEA"

    def _get_ide_version(self) -> str | None:
        """IDE 버전 조회."""
        if not self._ide_path:
            return None
        try:
            result = subprocess.run(
                [self._ide_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return None

    def _try_rest_api_terminal(self, command: str) -> bool:
        """JetBrains REST API로 터미널 명령 실행 시도."""
        try:
            import urllib.request
            import json
            url = "http://127.0.0.1:63342/api/terminal/run"
            data = json.dumps({"command": command}).encode()
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _try_applescript_terminal(self, command: str, project_path: str) -> bool:
        """AppleScript를 통한 터미널 명령 실행 fallback."""
        try:
            script = f'tell application "Terminal" to do script "{command}"'
            subprocess.run(["osascript", "-e", script], timeout=5, check=True)
            return True
        except Exception:
            return False
