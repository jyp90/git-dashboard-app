"""KeychainService 단위 테스트.

macOS security CLI를 mock하여 플랫폼 독립적으로 테스트한다.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

from app.domain.models import ScriptResult
from app.infrastructure.keychain_service import KeychainService


# ─── 헬퍼 ───────────────────────────────────────────────────────────────────

def _make_service(side_effects: list | None = None) -> tuple[KeychainService, MagicMock]:
    """_run_security_command를 mock한 KeychainService 반환."""
    svc = KeychainService()
    mock = MagicMock()
    if side_effects:
        mock.side_effect = side_effects
    svc._run_security_command = mock
    return svc, mock


def _ok(stdout: str = "") -> ScriptResult:
    return ScriptResult(success=True, stdout=stdout, stderr="", return_code=0)


def _fail(msg: str = "error") -> ScriptResult:
    return ScriptResult(success=False, stdout="", stderr=msg, return_code=1)


SECURITY_FIND_OUTPUT = """\
keychain: "/Users/user/Library/Keychains/login.keychain-db"
class: 0x00000010
attributes:
    0x00000007 <blob>="com.git-dashboard.git-credential.git.example.com"
    "acct"<blob>="jypark"
    "svce"<blob>="com.git-dashboard.git-credential.git.example.com"
"""

SECURITY_DUMP_OUTPUT = """\
keychain: "/Users/user/Library/Keychains/login.keychain-db"
attributes:
    "svce"<blob>="com.git-dashboard.git-credential.git.example.com"
    "acct"<blob>="jypark"
attributes:
    "svce"<blob>="unrelated.service"
    "acct"<blob>="other"
"""


# ─── _git_service_name ───────────────────────────────────────────────────────

class TestServiceNameGeneration:
    def test_https_url_extracts_host(self):
        svc = KeychainService()
        name = svc._git_service_name("https://git.example.com/repo")
        assert name == "com.git-dashboard.git-credential.git.example.com"

    def test_http_url_extracts_host(self):
        svc = KeychainService()
        name = svc._git_service_name("http://codecommit.ap-northeast-2.amazonaws.com/v1/repos")
        assert "codecommit" in name

    def test_non_url_fallback(self):
        svc = KeychainService()
        name = svc._git_service_name("ssh://git@example.com")
        assert "com.git-dashboard.git-credential" in name

    def test_service_prefix_present(self):
        svc = KeychainService()
        name = svc._git_service_name("https://github.com/user/repo")
        assert name.startswith("com.git-dashboard")


# ─── store_git_credential ────────────────────────────────────────────────────

class TestStoreGitCredential:
    def test_success_returns_true(self):
        svc, mock = _make_service()
        mock.return_value = _ok()
        assert svc.store_git_credential("https://example.com", "user", "token123") is True

    def test_failure_returns_false(self):
        svc, mock = _make_service()
        mock.return_value = _fail()
        assert svc.store_git_credential("https://example.com", "user", "token") is False

    def test_calls_add_generic_password(self):
        svc, mock = _make_service()
        mock.return_value = _ok()
        svc.store_git_credential("https://example.com", "user", "token123")
        args = mock.call_args[0][0]
        assert "add-generic-password" in args
        assert "-U" in args
        assert "user" in args
        assert "token123" in args

    def test_includes_update_flag(self):
        svc, mock = _make_service()
        mock.return_value = _ok()
        svc.store_git_credential("https://example.com", "user", "token")
        args = mock.call_args[0][0]
        assert "-U" in args


# ─── get_git_credential ──────────────────────────────────────────────────────

class TestGetGitCredential:
    def test_returns_username_and_token(self):
        svc, mock = _make_service()
        mock.side_effect = [
            _ok(SECURITY_FIND_OUTPUT),   # find metadata
            _ok("mytoken\n"),            # find password
        ]
        result = svc.get_git_credential("https://git.example.com/repo")
        assert result == ("jypark", "mytoken")

    def test_returns_none_when_not_found(self):
        svc, mock = _make_service()
        mock.return_value = _fail()
        assert svc.get_git_credential("https://example.com") is None

    def test_returns_none_when_no_account_parseable(self):
        svc, mock = _make_service()
        mock.side_effect = [
            _ok("no acct field here"),   # no account in output
            _ok("token"),
        ]
        assert svc.get_git_credential("https://example.com") is None

    def test_returns_none_when_password_fetch_fails(self):
        svc, mock = _make_service()
        mock.side_effect = [
            _ok(SECURITY_FIND_OUTPUT),
            _fail(),
        ]
        assert svc.get_git_credential("https://git.example.com/repo") is None

    def test_returns_none_when_empty_token(self):
        svc, mock = _make_service()
        mock.side_effect = [
            _ok(SECURITY_FIND_OUTPUT),
            _ok(""),   # empty password
        ]
        assert svc.get_git_credential("https://git.example.com/repo") is None


# ─── delete_git_credential ───────────────────────────────────────────────────

class TestDeleteGitCredential:
    def test_success_returns_true(self):
        svc, mock = _make_service()
        mock.return_value = _ok()
        assert svc.delete_git_credential("https://example.com") is True

    def test_failure_returns_false(self):
        svc, mock = _make_service()
        mock.return_value = _fail()
        assert svc.delete_git_credential("https://example.com") is False

    def test_calls_delete_generic_password(self):
        svc, mock = _make_service()
        mock.return_value = _ok()
        svc.delete_git_credential("https://example.com")
        args = mock.call_args[0][0]
        assert "delete-generic-password" in args


# ─── list_git_credentials ────────────────────────────────────────────────────

class TestListGitCredentials:
    def test_returns_list_of_credentials(self):
        svc, mock = _make_service()
        mock.return_value = _ok(SECURITY_DUMP_OUTPUT)
        result = svc.list_git_credentials()
        assert len(result) == 1
        assert result[0]["username"] == "jypark"

    def test_token_is_masked(self):
        svc, mock = _make_service()
        mock.return_value = _ok(SECURITY_DUMP_OUTPUT)
        result = svc.list_git_credentials()
        assert result[0]["token_masked"] == "****"

    def test_empty_when_dump_fails(self):
        svc, mock = _make_service()
        mock.return_value = _fail()
        assert svc.list_git_credentials() == []

    def test_filters_unrelated_services(self):
        svc, mock = _make_service()
        mock.return_value = _ok(SECURITY_DUMP_OUTPUT)
        result = svc.list_git_credentials()
        # "unrelated.service" should not appear
        services = [r["service"] for r in result]
        assert all("git-dashboard" in s for s in services)


# ─── store_secure_setting ────────────────────────────────────────────────────

class TestStoreSecureSetting:
    def test_success_returns_true(self):
        svc, mock = _make_service()
        mock.return_value = _ok()
        assert svc.store_secure_setting("webhook_url", "https://hook.example.com") is True

    def test_failure_returns_false(self):
        svc, mock = _make_service()
        mock.return_value = _fail()
        assert svc.store_secure_setting("key", "value") is False

    def test_service_name_includes_key(self):
        svc, mock = _make_service()
        mock.return_value = _ok()
        svc.store_secure_setting("my_api_key", "secret")
        args = mock.call_args[0][0]
        service_idx = args.index("-s") + 1
        assert "my_api_key" in args[service_idx]
        assert "app-settings" in args[service_idx]


# ─── get_secure_setting ──────────────────────────────────────────────────────

class TestGetSecureSetting:
    def test_returns_value(self):
        svc, mock = _make_service()
        mock.return_value = _ok("https://hook.example.com\n")
        result = svc.get_secure_setting("webhook_url")
        assert result == "https://hook.example.com"

    def test_returns_none_when_not_found(self):
        svc, mock = _make_service()
        mock.return_value = _fail()
        assert svc.get_secure_setting("nonexistent") is None

    def test_returns_none_when_empty(self):
        svc, mock = _make_service()
        mock.return_value = _ok("")
        assert svc.get_secure_setting("key") is None


# ─── delete_secure_setting ───────────────────────────────────────────────────

class TestDeleteSecureSetting:
    def test_success_returns_true(self):
        svc, mock = _make_service()
        mock.return_value = _ok()
        assert svc.delete_secure_setting("key") is True

    def test_failure_returns_false(self):
        svc, mock = _make_service()
        mock.return_value = _fail()
        assert svc.delete_secure_setting("key") is False


# ─── cleanup_all ─────────────────────────────────────────────────────────────

class TestCleanupAll:
    def test_cleanup_returns_count(self):
        svc, mock = _make_service()
        # list_git_credentials 반환용 dump
        mock.side_effect = [
            _ok(SECURITY_DUMP_OUTPUT),    # dump-keychain for list
            _ok(),                        # delete first entry
        ]
        count = svc.cleanup_all()
        assert count == 1

    def test_cleanup_empty_returns_zero(self):
        svc, mock = _make_service()
        mock.return_value = _ok("")
        count = svc.cleanup_all()
        assert count == 0


# ─── is_available ────────────────────────────────────────────────────────────

class TestIsAvailable:
    def test_returns_true_when_security_works(self):
        svc, mock = _make_service()
        mock.return_value = _ok("SecureTransport-60157.80.1")
        assert svc.is_available() is True

    def test_returns_false_when_security_fails(self):
        svc, mock = _make_service()
        mock.return_value = _fail()
        assert svc.is_available() is False


# ─── _run_security_command (예외 처리) ───────────────────────────────────────

class TestRunSecurityCommandExceptions:
    def test_file_not_found_returns_failure(self):
        svc = KeychainService()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = svc._run_security_command(["version"])
        assert result.success is False
        assert "not found" in result.stderr

    def test_timeout_returns_failure(self):
        import subprocess as sp
        svc = KeychainService()
        with patch("subprocess.run", side_effect=sp.TimeoutExpired(cmd="security", timeout=10)):
            result = svc._run_security_command(["version"])
        assert result.success is False
        assert "timed out" in result.stderr


# ─── _parse_acct ─────────────────────────────────────────────────────────────

class TestParseAcct:
    def test_parses_account_from_security_output(self):
        svc = KeychainService()
        output = '"acct"<blob>="myusername"'
        assert svc._parse_acct(output) == "myusername"

    def test_returns_none_when_no_acct(self):
        svc = KeychainService()
        assert svc._parse_acct("no account here") is None

    def test_handles_empty_string(self):
        svc = KeychainService()
        assert svc._parse_acct("") is None
