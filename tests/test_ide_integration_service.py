"""IdeIntegrationService 단위 테스트."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from app.infrastructure.ide_integration_service import IdeIntegrationService


# ─── 헬퍼 ───────────────────────────────────────────────────────────────────

def _make_service(ide_path: str | None = "/usr/local/bin/idea") -> IdeIntegrationService:
    """IDE 경로를 직접 주입한 서비스."""
    svc = IdeIntegrationService.__new__(IdeIntegrationService)
    svc._ide_path = ide_path
    return svc


# ─── is_available ────────────────────────────────────────────────────────────

class TestIsAvailable:
    def test_true_when_ide_path_set(self):
        svc = _make_service("/usr/local/bin/idea")
        assert svc.is_available() is True

    def test_false_when_no_ide_path(self):
        svc = _make_service(None)
        assert svc.is_available() is False


# ─── get_ide_info ────────────────────────────────────────────────────────────

class TestGetIdeInfo:
    def test_returns_unavailable_when_no_path(self):
        svc = _make_service(None)
        info = svc.get_ide_info()
        assert info["available"] is False
        assert info["path"] is None

    def test_returns_path_when_available(self):
        svc = _make_service("/usr/local/bin/idea")
        with patch.object(svc, "_get_ide_version", return_value="2024.1"):
            info = svc.get_ide_info()
        assert info["available"] is True
        assert info["path"] == "/usr/local/bin/idea"

    def test_detects_pycharm_name(self):
        svc = _make_service("/Applications/PyCharm.app/Contents/MacOS/pycharm")
        with patch.object(svc, "_get_ide_version", return_value=None):
            info = svc.get_ide_info()
        assert info["name"] == "PyCharm"

    def test_detects_webstorm_name(self):
        svc = _make_service("/path/to/webstorm")
        with patch.object(svc, "_get_ide_version", return_value=None):
            info = svc.get_ide_info()
        assert info["name"] == "WebStorm"

    def test_detects_community_edition(self):
        svc = _make_service("/Applications/IntelliJ IDEA CE.app/Contents/MacOS/idea")
        with patch.object(svc, "_get_ide_version", return_value=None):
            info = svc.get_ide_info()
        assert "Community" in info["name"]

    def test_default_name_intellij(self):
        svc = _make_service("/usr/local/bin/idea")
        with patch.object(svc, "_get_ide_version", return_value=None):
            info = svc.get_ide_info()
        assert "IntelliJ" in info["name"]


# ─── open_project ────────────────────────────────────────────────────────────

class TestOpenProject:
    def test_returns_false_when_no_ide(self):
        svc = _make_service(None)
        assert svc.open_project("/path/to/project") is False

    def test_returns_true_on_success(self):
        svc = _make_service("/usr/local/bin/idea")
        with patch("subprocess.Popen") as mock_popen:
            result = svc.open_project("/path/to/project")
        assert result is True
        mock_popen.assert_called_once()

    def test_calls_popen_with_project_path(self):
        svc = _make_service("/usr/local/bin/idea")
        with patch("subprocess.Popen") as mock_popen:
            svc.open_project("/my/project")
        args = mock_popen.call_args[0][0]
        assert "/my/project" in args

    def test_returns_false_on_exception(self):
        svc = _make_service("/usr/local/bin/idea")
        with patch("subprocess.Popen", side_effect=OSError("not found")):
            result = svc.open_project("/path")
        assert result is False


# ─── open_file ───────────────────────────────────────────────────────────────

class TestOpenFile:
    def test_returns_false_when_no_ide(self):
        svc = _make_service(None)
        assert svc.open_file("/path/file.py") is False

    def test_returns_true_on_success(self):
        svc = _make_service("/usr/local/bin/idea")
        with patch("subprocess.Popen"):
            result = svc.open_file("/path/file.py")
        assert result is True

    def test_includes_line_number(self):
        svc = _make_service("/usr/local/bin/idea")
        with patch("subprocess.Popen") as mock_popen:
            svc.open_file("/path/file.py", line=42)
        args = mock_popen.call_args[0][0]
        assert "--line" in args
        assert "42" in args

    def test_no_line_flag_when_line_zero(self):
        svc = _make_service("/usr/local/bin/idea")
        with patch("subprocess.Popen") as mock_popen:
            svc.open_file("/path/file.py", line=0)
        args = mock_popen.call_args[0][0]
        assert "--line" not in args


# ─── setup_git_hooks ─────────────────────────────────────────────────────────

class TestSetupGitHooks:
    def test_returns_false_when_no_git_dir(self, tmp_path):
        svc = _make_service()
        assert svc.setup_git_hooks(str(tmp_path / "nonexistent")) is False

    def test_creates_hook_files(self, tmp_path):
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True)
        (tmp_path / ".git").mkdir(exist_ok=True)

        svc = _make_service()
        result = svc.setup_git_hooks(str(tmp_path))
        assert result is True

        for hook in ["post-commit", "post-push"]:
            hook_path = tmp_path / ".git" / "hooks" / hook
            assert hook_path.exists()
            assert hook_path.stat().st_mode & 0o111  # executable

    def test_hook_content_is_valid_sh(self, tmp_path):
        (tmp_path / ".git" / "hooks").mkdir(parents=True)
        svc = _make_service()
        svc.setup_git_hooks(str(tmp_path))
        hook = (tmp_path / ".git" / "hooks" / "post-commit").read_text()
        assert hook.startswith("#!/bin/sh")


# ─── _discover_ide ───────────────────────────────────────────────────────────

class TestDiscoverIde:
    def test_finds_idea_in_path(self):
        with patch("shutil.which", return_value="/usr/local/bin/idea"):
            svc = IdeIntegrationService()
        assert svc._ide_path == "/usr/local/bin/idea"

    def test_returns_none_when_not_found(self):
        with patch("shutil.which", return_value=None), \
             patch("os.path.isfile", return_value=False):
            svc = IdeIntegrationService()
        assert svc._ide_path is None

    def test_finds_from_known_paths(self, tmp_path):
        fake_idea = tmp_path / "idea"
        fake_idea.touch()
        fake_idea.chmod(0o755)

        original_paths = IdeIntegrationService.IDE_SEARCH_PATHS
        IdeIntegrationService.IDE_SEARCH_PATHS = [str(fake_idea)]
        try:
            with patch("shutil.which", return_value=None):
                svc = IdeIntegrationService()
            assert svc._ide_path == str(fake_idea)
        finally:
            IdeIntegrationService.IDE_SEARCH_PATHS = original_paths


# ─── _detect_ide_name ────────────────────────────────────────────────────────

class TestDetectIdeName:
    def test_pycharm(self):
        svc = _make_service()
        assert svc._detect_ide_name("/path/pycharm") == "PyCharm"

    def test_webstorm(self):
        svc = _make_service()
        assert svc._detect_ide_name("/path/webstorm") == "WebStorm"

    def test_intellij_ce(self):
        svc = _make_service()
        name = svc._detect_ide_name("/Applications/IntelliJ IDEA CE.app/Contents/MacOS/idea")
        assert "Community" in name

    def test_intellij_default(self):
        svc = _make_service()
        assert svc._detect_ide_name("/usr/local/bin/idea") == "IntelliJ IDEA"
