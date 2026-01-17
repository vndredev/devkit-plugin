"""Tests for lib/marketplace.py."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.marketplace import (
    DEFAULT_MARKETPLACE_DIR,
    DEFAULT_MARKETPLACE_REPO,
    get_github_username,
    get_marketplace_config,
    get_marketplace_local_dir,
    rename_local_marketplace,
)


class TestGetGitHubUsername:
    """Tests for get_github_username()."""

    def test_extracts_from_https_remote(self):
        """Should extract username from HTTPS remote URL."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "https://github.com/testuser/repo.git\n"
            mock_run.return_value.returncode = 0

            username = get_github_username()

            assert username == "testuser"

    def test_extracts_from_ssh_remote(self):
        """Should extract username from SSH remote URL."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "git@github.com:testuser/repo.git\n"
            mock_run.return_value.returncode = 0

            username = get_github_username()

            assert username == "testuser"

    def test_falls_back_to_gh_cli(self):
        """Should fall back to gh CLI if git remote fails."""
        import subprocess

        with patch("subprocess.run") as mock_run:
            # First call (git remote) fails
            mock_run.side_effect = [
                subprocess.CalledProcessError(1, "git"),
                type("Result", (), {"stdout": "ghuser\n", "returncode": 0})(),
            ]

            username = get_github_username()

            assert username == "ghuser"

    def test_returns_none_if_all_fail(self):
        """Should return None if all methods fail."""
        import subprocess

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")

            username = get_github_username()

            assert username is None


class TestGetMarketplaceLocalDir:
    """Tests for get_marketplace_local_dir()."""

    def test_returns_standard_path(self):
        """Should return ~/dev/claude-marketplace path."""
        path = get_marketplace_local_dir()

        assert path == Path.home() / "dev" / DEFAULT_MARKETPLACE_DIR
        assert str(path).endswith("claude-marketplace")

    def test_ignores_username_parameter(self):
        """Should ignore username parameter (backwards compat)."""
        path = get_marketplace_local_dir(username="someuser")

        # Should still return standard path
        assert path == Path.home() / "dev" / DEFAULT_MARKETPLACE_DIR


class TestRenameLocalMarketplace:
    """Tests for rename_local_marketplace()."""

    def test_renames_directory(self, tmp_path):
        """Should rename source directory to target."""
        old_dir = tmp_path / "old-marketplace"
        old_dir.mkdir()
        (old_dir / "plugins").mkdir()

        new_dir = tmp_path / "claude-marketplace"

        success, msg = rename_local_marketplace(old_dir, new_dir)

        assert success is True
        assert not old_dir.exists()
        assert new_dir.exists()
        assert (new_dir / "plugins").exists()

    def test_fails_if_source_missing(self, tmp_path):
        """Should fail if source directory doesn't exist."""
        old_dir = tmp_path / "nonexistent"
        new_dir = tmp_path / "new"

        success, msg = rename_local_marketplace(old_dir, new_dir)

        assert success is False
        assert "not found" in msg

    def test_succeeds_if_target_exists(self, tmp_path):
        """Should succeed if target already exists."""
        old_dir = tmp_path / "old"
        old_dir.mkdir()
        new_dir = tmp_path / "new"
        new_dir.mkdir()

        success, msg = rename_local_marketplace(old_dir, new_dir)

        assert success is True
        assert "already exists" in msg


class TestGetMarketplaceConfig:
    """Tests for get_marketplace_config()."""

    def test_returns_config_dict(self):
        """Should return marketplace configuration dict."""
        with patch("lib.marketplace.get_github_username") as mock_user:
            mock_user.return_value = "testuser"

            config = get_marketplace_config()

            assert config["username"] == "testuser"
            assert config["repo_name"] == DEFAULT_MARKETPLACE_REPO
            assert "claude-marketplace" in config["local_dir"]

    def test_uses_provided_username(self):
        """Should use provided username over auto-detect."""
        config = get_marketplace_config(username="explicit-user")

        assert config["username"] == "explicit-user"

    def test_uses_unknown_if_no_username(self):
        """Should use 'unknown' if username cannot be detected."""
        with patch("lib.marketplace.get_github_username") as mock_user:
            mock_user.return_value = None

            config = get_marketplace_config()

            assert config["username"] == "unknown"
