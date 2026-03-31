"""ConfigStore — ~/.git-dashboard/config.json 관리."""
from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import RepoConfig


class ConfigStore:
    """앱 설정을 JSON 파일로 영속화."""

    _DEFAULT_DIR = Path.home() / ".git-dashboard"
    _CONFIG_FILE = "config.json"

    def __init__(self, config_dir: Path | None = None) -> None:
        self._dir = config_dir or self._DEFAULT_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / self._CONFIG_FILE
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {"repositories": [], "theme": "dark"}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False))

    def get_repositories(self) -> list[RepoConfig]:
        return [
            RepoConfig(name=r["name"], path=r["path"], is_active=r.get("is_active", False))
            for r in self._data.get("repositories", [])
        ]

    def add_repository(self, path: str, name: str) -> None:
        repos = self._data.setdefault("repositories", [])
        if any(r["path"] == path for r in repos):
            return
        repos.append({"name": name, "path": path, "is_active": not repos})
        self._save()

    def remove_repository(self, path: str) -> None:
        self._data["repositories"] = [
            r for r in self._data.get("repositories", []) if r["path"] != path
        ]
        self._save()

    def get_active_repo(self) -> RepoConfig | None:
        for r in self.get_repositories():
            if r.is_active:
                return r
        repos = self.get_repositories()
        return repos[0] if repos else None

    def set_active_repo(self, path: str) -> None:
        for r in self._data.get("repositories", []):
            r["is_active"] = r["path"] == path
        self._save()

    def get_theme(self) -> str:
        return self._data.get("theme", "dark")

    def rename_repository(self, path: str, new_name: str) -> None:
        for r in self._data.get("repositories", []):
            if r["path"] == path:
                r["name"] = new_name
                break
        self._save()

    def set_theme(self, theme: str) -> None:
        self._data["theme"] = theme
        self._save()
