"""Tests for lib/vercel.py - Vercel setup and management."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from lib.vercel import (
    check_vercel_cli,
    link_project,
    get_project_info,
    check_github_integration,
    sync_env_vars,
    vercel_connect,
    vercel_status,
)


class TestCheckVercelCli:
    """Tests for check_vercel_cli()."""

    def test_cli_installed_and_logged_in(self):
        """Should return success when CLI is installed and user is logged in."""
        with patch("subprocess.run") as mock_run:
            # First call: version check
            version_result = MagicMock()
            version_result.stdout = "Vercel CLI 50.1.3\n"
            # Second call: whoami
            whoami_result = MagicMock()
            whoami_result.stdout = "dfineio"

            mock_run.side_effect = [version_result, whoami_result]

            ok, msg = check_vercel_cli()

            assert ok is True
            assert "50.1.3" in msg
            assert "dfineio" in msg

    def test_cli_not_installed(self):
        """Should return failure when CLI is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            ok, msg = check_vercel_cli()

            assert ok is False
            assert "not installed" in msg

    def test_cli_not_logged_in(self):
        """Should return failure when not logged in."""
        with patch("subprocess.run") as mock_run:
            version_result = MagicMock()
            version_result.stdout = "Vercel CLI 50.1.3"

            mock_run.side_effect = [
                version_result,
                subprocess.CalledProcessError(1, "vercel"),
            ]

            ok, msg = check_vercel_cli()

            assert ok is False
            assert "not logged in" in msg


class TestLinkProject:
    """Tests for link_project()."""

    def test_already_linked(self, tmp_path):
        """Should detect already linked project."""
        vercel_dir = tmp_path / ".vercel"
        vercel_dir.mkdir()
        project_json = vercel_dir / "project.json"
        project_json.write_text(
            json.dumps(
                {
                    "projectId": "prj_123",
                    "orgId": "org_456",
                    "projectName": "my-project",
                }
            )
        )

        ok, msg = link_project(tmp_path)

        assert ok is True
        assert "Already linked" in msg
        assert "my-project" in msg

    def test_link_new_project(self, tmp_path):
        """Should link new project."""
        with patch("subprocess.run") as mock_run:

            def create_project_json(*args, **kwargs):
                # Simulate vercel link creating the directory
                vercel_dir = tmp_path / ".vercel"
                vercel_dir.mkdir(exist_ok=True)
                (vercel_dir / "project.json").write_text(json.dumps({"projectName": "new-project"}))
                return MagicMock(returncode=0)

            mock_run.side_effect = create_project_json

            ok, msg = link_project(tmp_path)

            assert ok is True
            assert "new-project" in msg
            mock_run.assert_called_once()

    def test_link_fails(self, tmp_path):
        """Should handle link failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "vercel", stderr="Error")

            ok, msg = link_project(tmp_path)

            assert ok is False
            assert "failed" in msg.lower()


class TestGetProjectInfo:
    """Tests for get_project_info()."""

    def test_no_vercel_dir(self, tmp_path):
        """Should return None when no .vercel directory."""
        result = get_project_info(tmp_path)
        assert result is None

    def test_reads_project_json(self, tmp_path):
        """Should read project info from project.json."""
        vercel_dir = tmp_path / ".vercel"
        vercel_dir.mkdir()
        (vercel_dir / "project.json").write_text(
            json.dumps(
                {
                    "projectId": "prj_123",
                    "orgId": "org_456",
                    "projectName": "test-project",
                }
            )
        )

        with patch("subprocess.run") as mock_run:
            # Mock the additional API calls
            mock_run.side_effect = [
                subprocess.CalledProcessError(1, "vercel"),  # project ls
                MagicMock(stdout="testuser"),  # whoami
            ]

            result = get_project_info(tmp_path)

        assert result is not None
        assert result["project_id"] == "prj_123"
        assert result["name"] == "test-project"


class TestCheckGithubIntegration:
    """Tests for check_github_integration()."""

    def test_github_remote_already_connected(self):
        """Should detect already connected GitHub remote."""
        with patch("subprocess.run") as mock_run:
            # First call: git remote get-url
            git_remote = MagicMock(stdout="git@github.com:user/repo.git")
            # Second call: vercel git ls (shows connected)
            vercel_git_ls = MagicMock(stdout="user/repo")

            mock_run.side_effect = [git_remote, vercel_git_ls]

            ok, msg = check_github_integration({"project_id": "123"})

            assert ok is True
            assert "user/repo" in msg

    def test_https_remote_auto_connect(self):
        """Should auto-connect HTTPS remote if not connected."""
        with patch("subprocess.run") as mock_run:
            # First call: git remote get-url
            git_remote = MagicMock(stdout="https://github.com/user/repo.git")
            # Second call: vercel git ls (fails - not connected)
            vercel_git_ls_fail = subprocess.CalledProcessError(1, "vercel")
            # Third call: vercel git connect (success)
            vercel_connect = MagicMock(returncode=0)

            mock_run.side_effect = [git_remote, vercel_git_ls_fail, vercel_connect]

            ok, msg = check_github_integration({"project_id": "123"})

            assert ok is True
            assert "user/repo" in msg

    def test_no_remote(self):
        """Should handle no remote."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")

            ok, msg = check_github_integration({"project_id": "123"})

            assert ok is False
            assert "No git remote" in msg

    def test_skip_auto_connect(self):
        """Should not auto-connect when disabled."""
        with patch("subprocess.run") as mock_run:
            # First call: git remote get-url
            git_remote = MagicMock(stdout="git@github.com:user/repo.git")
            # Second call: vercel git ls (fails - not connected)
            vercel_git_ls_fail = subprocess.CalledProcessError(1, "vercel")

            mock_run.side_effect = [git_remote, vercel_git_ls_fail]

            ok, msg = check_github_integration({"project_id": "123"}, auto_connect=False)

            assert ok is False
            assert "Not connected" in msg


class TestSyncEnvVars:
    """Tests for sync_env_vars()."""

    def test_no_env_file(self, tmp_path):
        """Should skip when no .env.local exists."""
        results = sync_env_vars(tmp_path)

        assert len(results) == 1
        assert results[0][1] is True
        assert "No .env.local" in results[0][2]

    def test_skips_sensitive_vars(self, tmp_path):
        """Should skip sensitive variables."""
        env_file = tmp_path / ".env.local"
        env_file.write_text("""
DATABASE_URL=postgres://localhost
API_SECRET_KEY=secret123
AUTH_TOKEN=token456
NEXT_PUBLIC_APP_NAME=MyApp
""")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="")

            results = sync_env_vars(tmp_path)

        # Should have skipped SECRET_KEY and TOKEN
        skipped = [r for r in results if "Skipped" in r[2]]
        assert len(skipped) >= 2

    def test_detects_existing_vars(self, tmp_path):
        """Should detect already set variables."""
        env_file = tmp_path / ".env.local"
        env_file.write_text("EXISTING_VAR=value")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout='{"key": "EXISTING_VAR"}')

            results = sync_env_vars(tmp_path)

        already_set = [r for r in results if "Already set" in r[2]]
        assert len(already_set) >= 1


class TestVercelConnect:
    """Tests for vercel_connect()."""

    def test_fails_if_cli_not_installed(self):
        """Should fail early if CLI not installed."""
        with patch("lib.vercel.check_vercel_cli") as mock_cli:
            mock_cli.return_value = (False, "Not installed")

            results = vercel_connect()

            assert len(results) == 1
            assert results[0][1] is False

    def test_full_workflow(self, tmp_path, monkeypatch):
        """Should run full workflow."""
        monkeypatch.chdir(tmp_path)

        # Create .git directory (needed for project root detection)
        (tmp_path / ".git").mkdir()

        # Create .vercel directory
        vercel_dir = tmp_path / ".vercel"
        vercel_dir.mkdir()
        (vercel_dir / "project.json").write_text(
            json.dumps(
                {
                    "projectId": "prj_123",
                    "projectName": "test",
                }
            )
        )

        with patch("lib.vercel.check_vercel_cli") as mock_cli:
            with patch("lib.vercel.check_github_integration") as mock_gh:
                with patch("lib.vercel.check_production_domain") as mock_domain:
                    with patch("lib.vercel.check_neon_integration") as mock_neon:
                        with patch("lib.vercel.get_project_info") as mock_info:
                            mock_cli.return_value = (True, "CLI OK")
                            mock_gh.return_value = (True, "GitHub OK")
                            mock_domain.return_value = (True, "example.com")
                            mock_neon.return_value = (True, "Neon OK")
                            mock_info.return_value = {"name": "test", "org": "user"}

                            results = vercel_connect(sync_env=False)

        assert len(results) >= 4
        assert all(r[1] for r in results)


class TestVercelStatus:
    """Tests for vercel_status()."""

    def test_returns_status_dict(self, tmp_path, monkeypatch):
        """Should return status dictionary."""
        monkeypatch.chdir(tmp_path)

        with patch("lib.vercel.check_vercel_cli") as mock_cli:
            mock_cli.return_value = (True, "50.1.3 (logged in as user)")

            status = vercel_status()

        assert isinstance(status, dict)
        assert "linked" in status
        assert "cli_version" in status
