"""KeychainService — macOS Keychain Services 연동.

macOS `security` CLI를 subprocess로 래핑하여
Git 자격증명과 앱 설정을 안전하게 관리한다.
"""
from __future__ import annotations

import re
import subprocess

from app.domain.models import ScriptResult


class KeychainService:
    """macOS Keychain Services를 통해 자격증명과 앱 설정을 안전하게 관리한다.

    사용 기술: subprocess로 `security` CLI 명령 실행
    서비스명 네임스페이스: "com.git-dashboard.{category}.{key}"

    보안 원칙:
    - 메모리에 자격증명을 장기 보관하지 않음
    - 필요 시에만 Keychain에서 읽고 즉시 사용
    - 앱 삭제 시 Keychain 항목 정리 옵션 제공
    """

    SERVICE_PREFIX = "com.git-dashboard"
    CATEGORY_GIT_CREDENTIAL = "git-credential"
    CATEGORY_APP_SETTINGS = "app-settings"

    # ─── Git 자격증명 관리 ───────────────────────────────────────────────────

    def store_git_credential(self, remote_url: str, username: str, token: str) -> bool:
        """Git 리모트 자격증명을 Keychain에 저장.

        사용 예: AWS CodeCommit HTTPS 토큰, GitHub PAT
        서비스명: com.git-dashboard.git-credential.{remote_host}
        """
        service = self._git_service_name(remote_url)
        result = self._run_security_command([
            "add-generic-password",
            "-U",        # update if exists
            "-s", service,
            "-a", username,
            "-w", token,
        ])
        return result.success

    def get_git_credential(self, remote_url: str) -> tuple[str, str] | None:
        """Keychain에서 Git 자격증명 조회.

        Returns:
            (username, token) 또는 None
        """
        service = self._git_service_name(remote_url)

        # 먼저 메타데이터에서 account(username) 파싱
        meta = self._run_security_command([
            "find-generic-password",
            "-s", service,
        ])
        if not meta.success:
            return None

        username = self._parse_acct(meta.stdout + meta.stderr)
        if not username:
            return None

        # password 조회
        pw = self._run_security_command([
            "find-generic-password",
            "-s", service,
            "-a", username,
            "-w",
        ])
        if not pw.success:
            return None

        token = pw.stdout.strip()
        return (username, token) if token else None

    def delete_git_credential(self, remote_url: str) -> bool:
        """Git 자격증명 삭제."""
        service = self._git_service_name(remote_url)
        result = self._run_security_command([
            "delete-generic-password",
            "-s", service,
        ])
        return result.success

    def list_git_credentials(self) -> list[dict]:
        """저장된 모든 Git 자격증명 목록 (토큰 마스킹)."""
        result = self._run_security_command(["dump-keychain"])
        if not result.success:
            return []
        prefix = f"{self.SERVICE_PREFIX}.{self.CATEGORY_GIT_CREDENTIAL}"
        return self._parse_credential_entries(result.stdout, prefix)

    # ─── 앱 설정 보안 저장 ───────────────────────────────────────────────────

    def store_secure_setting(self, key: str, value: str) -> bool:
        """민감한 앱 설정을 Keychain에 저장.

        사용 예: Webhook URL, API 토큰
        서비스명: com.git-dashboard.app-settings.{key}
        """
        service = f"{self.SERVICE_PREFIX}.{self.CATEGORY_APP_SETTINGS}.{key}"
        result = self._run_security_command([
            "add-generic-password",
            "-U",
            "-s", service,
            "-a", "git-dashboard",
            "-w", value,
        ])
        return result.success

    def get_secure_setting(self, key: str) -> str | None:
        """Keychain에서 앱 설정 조회."""
        service = f"{self.SERVICE_PREFIX}.{self.CATEGORY_APP_SETTINGS}.{key}"
        result = self._run_security_command([
            "find-generic-password",
            "-s", service,
            "-a", "git-dashboard",
            "-w",
        ])
        if not result.success:
            return None
        value = result.stdout.strip()
        return value if value else None

    def delete_secure_setting(self, key: str) -> bool:
        """앱 설정 삭제."""
        service = f"{self.SERVICE_PREFIX}.{self.CATEGORY_APP_SETTINGS}.{key}"
        result = self._run_security_command([
            "delete-generic-password",
            "-s", service,
        ])
        return result.success

    # ─── Keychain 유틸리티 ───────────────────────────────────────────────────

    def cleanup_all(self) -> int:
        """앱 관련 모든 Keychain 항목 삭제 (앱 삭제 시 정리용)."""
        credentials = self.list_git_credentials()
        count = 0
        for cred in credentials:
            r = self._run_security_command([
                "delete-generic-password", "-s", cred["service"],
            ])
            if r.success:
                count += 1
        return count

    def is_available(self) -> bool:
        """macOS security CLI 사용 가능 여부 확인."""
        result = self._run_security_command(["version"])
        return result.success

    # ─── 내부 헬퍼 ──────────────────────────────────────────────────────────

    def _git_service_name(self, remote_url: str) -> str:
        """remote URL에서 호스트 추출 → 서비스명 생성."""
        host_match = re.match(r"https?://([^/]+)", remote_url)
        host = host_match.group(1) if host_match else remote_url.replace("/", "-").replace(":", "-")
        return f"{self.SERVICE_PREFIX}.{self.CATEGORY_GIT_CREDENTIAL}.{host}"

    def _run_security_command(self, args: list[str]) -> ScriptResult:
        """macOS security CLI 명령 실행."""
        try:
            proc = subprocess.run(
                ["security"] + args,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return ScriptResult(
                success=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                return_code=proc.returncode,
            )
        except FileNotFoundError:
            return ScriptResult.failure("security CLI not found (non-macOS?)")
        except subprocess.TimeoutExpired:
            return ScriptResult.failure("security command timed out")
        except Exception as e:
            return ScriptResult.failure(str(e))

    def _parse_acct(self, output: str) -> str | None:
        """security 출력에서 account(username) 파싱."""
        m = re.search(r'"acct"<blob>="([^"]+)"', output)
        return m.group(1) if m else None

    def _parse_credential_entries(self, dump_output: str, prefix: str) -> list[dict]:
        """security dump-keychain 출력에서 자격증명 목록 파싱."""
        entries = []
        for block in dump_output.split("attributes:"):
            if prefix not in block:
                continue
            svc_m = re.search(r'"svce"<blob>="([^"]+)"', block)
            acct_m = re.search(r'"acct"<blob>="([^"]+)"', block)
            if svc_m:
                entries.append({
                    "service": svc_m.group(1),
                    "username": acct_m.group(1) if acct_m else "unknown",
                    "token_masked": "****",
                })
        return entries
