"""ConfigStore 유닛 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.infrastructure.config_store import ConfigStore


@pytest.fixture
def store(tmp_path: Path) -> ConfigStore:
    return ConfigStore(config_dir=tmp_path)


class TestAddRemoveRepo:
    def test_add_repository(self, store):
        store.add_repository("/some/path", "my-repo")
        repos = store.get_repositories()
        assert len(repos) == 1
        assert repos[0].name == "my-repo"

    def test_duplicate_not_added(self, store):
        store.add_repository("/path", "repo")
        store.add_repository("/path", "repo2")
        assert len(store.get_repositories()) == 1

    def test_remove_repository(self, store):
        store.add_repository("/path", "repo")
        store.remove_repository("/path")
        assert store.get_repositories() == []

    def test_first_repo_is_active(self, store):
        store.add_repository("/path", "repo")
        active = store.get_active_repo()
        assert active is not None
        assert active.path == "/path"


class TestActiveRepo:
    def test_set_active_repo(self, store):
        store.add_repository("/a", "a")
        store.add_repository("/b", "b")
        store.set_active_repo("/b")
        active = store.get_active_repo()
        assert active.path == "/b"

    def test_no_repos_returns_none(self, store):
        assert store.get_active_repo() is None


class TestPersistence:
    def test_data_persists(self, tmp_path):
        store1 = ConfigStore(config_dir=tmp_path)
        store1.add_repository("/path", "repo")

        store2 = ConfigStore(config_dir=tmp_path)
        assert len(store2.get_repositories()) == 1

    def test_theme_persists(self, tmp_path):
        store1 = ConfigStore(config_dir=tmp_path)
        store1.set_theme("light")

        store2 = ConfigStore(config_dir=tmp_path)
        assert store2.get_theme() == "light"
