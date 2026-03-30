"""ScriptRunner — scripts/ 폴더의 쉘 스크립트를 subprocess로 래핑."""
from __future__ import annotations

import subprocess
from pathlib import Path

from app.domain.models import ScriptResult


class ScriptRunner:
    """scripts/ 디렉터리의 쉘 스크립트를 직접 수정 없이 실행."""

    def __init__(self, scripts_dir: Path | None = None) -> None:
        self._scripts_dir = scripts_dir or (Path(__file__).parents[2] / "scripts")

    def run(self, script_name: str, *args: str, cwd: str | None = None) -> ScriptResult:
        """scripts/{script_name}을 실행하고 ScriptResult 반환."""
        script_path = self._scripts_dir / script_name
        if not script_path.exists():
            return ScriptResult.failure(f"스크립트를 찾을 수 없습니다: {script_path}")

        try:
            result = subprocess.run(
                [str(script_path), *args],
                capture_output=True,
                text=True,
                cwd=cwd or str(self._scripts_dir.parent),
                timeout=120,
            )
            return ScriptResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ScriptResult.failure("스크립트 실행 타임아웃 (120초)")
        except OSError as e:
            return ScriptResult.failure(f"스크립트 실행 오류: {e}")

    def list_scripts(self) -> list[str]:
        """사용 가능한 스크립트 목록 반환."""
        if not self._scripts_dir.exists():
            return []
        return [f.name for f in self._scripts_dir.iterdir() if f.suffix in (".sh", ".bash", ".zsh")]
