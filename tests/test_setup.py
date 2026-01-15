"""Tests for lib/setup.py - Project initialization and update."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from lib.setup import (
    create_config,
    git_init,
    git_update,
    setup_github,
    update_github_settings,
)


class TestCreateConfig:
    """Tests for create_config()."""

    def test_create_config_python(self, tmp_path):
        """Should create config for Python project."""
        success, msg = create_config(tmp_path, "test-project", "python")

        assert success is True
        config_file = tmp_path / ".claude" / ".devkit" / "config.json"
        assert config_file.exists()

        config = json.loads(config_file.read_text())
        assert config["project"]["name"] == "test-project"
        assert config["project"]["type"] == "python"
        assert config["project"]["version"] == "0.0.0"
        assert config["testing"]["framework"] == "pytest"

    def test_create_config_node(self, tmp_path):
        """Should create config for Node project."""
        success, msg = create_config(tmp_path, "test-node", "node")

        assert success is True
        config_file = tmp_path / ".claude" / ".devkit" / "config.json"
        config = json.loads(config_file.read_text())

        assert config["project"]["type"] == "node"
        assert config["testing"]["framework"] == "vitest"

    def test_create_config_with_github(self, tmp_path):
        """Should include GitHub URL when provided."""
        success, msg = create_config(
            tmp_path, "test-project", "python", github_repo="user/repo"
        )

        config_file = tmp_path / ".claude" / ".devkit" / "config.json"
        config = json.loads(config_file.read_text())

        assert config["github"]["url"] == "https://github.com/user/repo"

    def test_create_config_managed_files_python(self, tmp_path):
        """Should include Python-specific managed files."""
        create_config(tmp_path, "test", "python")

        config_file = tmp_path / ".claude" / ".devkit" / "config.json"
        config = json.loads(config_file.read_text())

        assert "ruff.toml" in config["managed"]["linters"]
        assert "release-python" in config["managed"]["github"][".github/workflows/release.yml"]["template"]

    def test_create_config_managed_files_node(self, tmp_path):
        """Should include Node-specific managed files."""
        create_config(tmp_path, "test", "node")

        config_file = tmp_path / ".claude" / ".devkit" / "config.json"
        config = json.loads(config_file.read_text())

        assert "ruff.toml" not in config["managed"]["linters"]
        assert "release-node" in config["managed"]["github"][".github/workflows/release.yml"]["template"]

    def test_create_config_creates_directory(self, tmp_path):
        """Should create .claude/.devkit directory if not exists."""
        assert not (tmp_path / ".claude").exists()

        create_config(tmp_path, "test", "python")

        assert (tmp_path / ".claude" / ".devkit").exists()


class TestGitInit:
    """Tests for git_init()."""

    def test_git_init_creates_git_repo(self, tmp_path, monkeypatch):
        """Should initialize git repository."""
        from lib.config import clear_cache

        clear_cache()
        monkeypatch.chdir(tmp_path)

        with patch("lib.setup.run_git") as mock_git:
            with patch("lib.setup.sync_all", return_value=[]):
                results = git_init(name="test", project_type="python")

        # Should have called git init
        mock_git.assert_any_call(["init"])

    def test_git_init_skips_if_git_exists(self, tmp_path, monkeypatch):
        """Should skip git init if .git exists."""
        from lib.config import clear_cache

        clear_cache()
        (tmp_path / ".git").mkdir()
        monkeypatch.chdir(tmp_path)

        with patch("lib.setup.run_git") as mock_git:
            with patch("lib.setup.sync_all", return_value=[]):
                results = git_init(name="test", project_type="python")

        # Should NOT have called git init
        init_calls = [c for c in mock_git.call_args_list if c[0] == (["init"],)]
        assert len(init_calls) == 0

    def test_git_init_creates_first_commit(self, tmp_path, monkeypatch):
        """Should create first commit."""
        from lib.config import clear_cache

        clear_cache()
        monkeypatch.chdir(tmp_path)

        with patch("lib.setup.run_git") as mock_git:
            with patch("lib.setup.sync_all", return_value=[]):
                results = git_init(name="test", project_type="python")

        # Should have called git add and commit
        mock_git.assert_any_call(["add", "-A"])
        mock_git.assert_any_call(["commit", "-m", "chore: initial commit"])

    def test_git_init_returns_results(self, tmp_path, monkeypatch):
        """Should return list of results."""
        from lib.config import clear_cache

        clear_cache()
        monkeypatch.chdir(tmp_path)

        with patch("lib.setup.run_git"):
            with patch("lib.setup.sync_all", return_value=[("file.txt", True, "Created")]):
                results = git_init(name="test", project_type="python")

        assert isinstance(results, list)
        assert all(len(r) == 3 for r in results)


class TestGitUpdate:
    """Tests for git_update()."""

    def test_git_update_requires_config(self, tmp_path, monkeypatch):
        """Should fail if no config exists."""
        from lib.config import clear_cache

        clear_cache()
        (tmp_path / ".claude").mkdir()
        monkeypatch.chdir(tmp_path)

        results = git_update()

        assert len(results) == 1
        assert results[0][1] is False
        assert "No config" in results[0][2] or "Config error" in results[0][2]

    def test_git_update_syncs_files(self, tmp_path, monkeypatch):
        """Should sync managed files."""
        from lib.config import clear_cache

        clear_cache()

        # Create config
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "github": {"url": ""},
            "managed": {},
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        with patch("lib.setup.sync_all", return_value=[("file.txt", True, "Synced")]) as mock_sync:
            results = git_update()

        mock_sync.assert_called_once()

    def test_git_update_updates_github_if_configured(self, tmp_path, monkeypatch):
        """Should update GitHub settings if URL configured."""
        from lib.config import clear_cache

        clear_cache()

        # Create config with GitHub URL
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "github": {"url": "https://github.com/user/repo"},
            "managed": {},
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        with patch("lib.setup.sync_all", return_value=[]):
            with patch("lib.setup.update_github_settings", return_value=[]) as mock_gh:
                results = git_update()

        mock_gh.assert_called_once_with("user/repo")


class TestSetupGithub:
    """Tests for setup_github()."""

    def test_setup_github_creates_repo(self):
        """Should create GitHub repo."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch("lib.setup.update_github_settings", return_value=[]):
                results = setup_github("user/repo")

        # Should have called gh repo create
        create_call = mock_run.call_args_list[0]
        assert "gh" in create_call[0][0]
        assert "repo" in create_call[0][0]
        assert "create" in create_call[0][0]

    def test_setup_github_handles_existing_repo(self):
        """Should handle existing repo by setting remote."""
        with patch("subprocess.run") as mock_run:
            # First call fails (repo exists), subsequent succeed
            mock_run.side_effect = [
                subprocess.CalledProcessError(1, "gh"),
                MagicMock(returncode=0),
                MagicMock(returncode=0),
            ]
            with patch("lib.setup.run_git") as mock_git:
                with patch("lib.setup.update_github_settings", return_value=[]):
                    results = setup_github("user/repo")

        # Should have tried to add remote
        mock_git.assert_any_call(["remote", "add", "origin", "https://github.com/user/repo.git"])


class TestUpdateGithubSettings:
    """Tests for update_github_settings()."""

    def test_update_github_settings_sets_squash_merge(self):
        """Should configure squash merge only."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            results = update_github_settings("user/repo")

        # Check for squash merge setting
        patch_call = mock_run.call_args_list[0]
        args = patch_call[0][0]
        assert "allow_squash_merge=true" in args
        assert "allow_merge_commit=false" in args

    def test_update_github_settings_sets_branch_protection(self):
        """Should configure branch protection."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            results = update_github_settings("user/repo")

        # Check for branch protection call
        protection_call = mock_run.call_args_list[1]
        args = protection_call[0][0]
        assert "branches/main/protection" in " ".join(args)

    def test_update_github_settings_handles_errors(self):
        """Should handle API errors gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "gh", stderr=b"API error")
            results = update_github_settings("user/repo")

        assert len(results) == 2
        assert results[0][1] is False
        assert results[1][1] is False


# Import subprocess for CalledProcessError
import subprocess
