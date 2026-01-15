"""Tests for lib/git.py - Git operations."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from core.errors import GitError
from lib.git import git_branch, git_commit, git_status, is_protected_branch, run_git


class TestRunGit:
    """Tests for run_git()."""

    def test_run_git_success(self):
        """Should return output on success."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="output\n", returncode=0)

            result = run_git(["status"])

            assert result == "output"
            mock_run.assert_called_once()

    def test_run_git_with_args(self):
        """Should pass arguments to git command."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)

            run_git(["commit", "-m", "message"])

            args = mock_run.call_args[0][0]
            assert args == ["git", "commit", "-m", "message"]

    def test_run_git_with_cwd(self, tmp_path):
        """Should use cwd parameter."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)

            run_git(["status"], cwd=tmp_path)

            assert mock_run.call_args[1]["cwd"] == tmp_path

    def test_run_git_raises_on_failure(self):
        """Should raise GitError on command failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git", stderr="error message")

            with pytest.raises(GitError) as exc_info:
                run_git(["invalid-command"])

            assert "failed" in str(exc_info.value)

    def test_run_git_strips_output(self):
        """Should strip whitespace from output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="  output  \n\n", returncode=0)

            result = run_git(["status"])

            assert result == "output"


class TestGitStatus:
    """Tests for git_status()."""

    def test_git_status_parses_staged_files(self):
        """Should detect staged files."""
        with patch("lib.git.run_git") as mock_run:
            mock_run.return_value = "M  staged.py\nA  added.py"

            result = git_status()

            assert "staged.py" in result["staged"]
            assert "added.py" in result["staged"]

    def test_git_status_parses_modified_files(self):
        """Should detect modified files."""
        with patch("lib.git.run_git") as mock_run:
            mock_run.return_value = " M modified.py"

            result = git_status()

            assert "modified.py" in result["modified"]

    def test_git_status_parses_untracked_files(self):
        """Should detect untracked files."""
        with patch("lib.git.run_git") as mock_run:
            mock_run.return_value = "?? untracked.py"

            result = git_status()

            assert "untracked.py" in result["untracked"]

    def test_git_status_parses_mixed_status(self):
        """Should parse mixed status output."""
        with patch("lib.git.run_git") as mock_run:
            mock_run.return_value = "M  staged.py\n M modified.py\n?? untracked.py\nMM both.py"

            result = git_status()

            assert "staged.py" in result["staged"]
            assert "modified.py" in result["modified"]
            assert "untracked.py" in result["untracked"]
            assert "both.py" in result["staged"]
            assert "both.py" in result["modified"]

    def test_git_status_empty_repo(self):
        """Should handle empty status."""
        with patch("lib.git.run_git") as mock_run:
            mock_run.return_value = ""

            result = git_status()

            assert result["staged"] == []
            assert result["modified"] == []
            assert result["untracked"] == []

    def test_git_status_returns_dict_structure(self):
        """Should return correct dict structure."""
        with patch("lib.git.run_git") as mock_run:
            mock_run.return_value = ""

            result = git_status()

            assert "staged" in result
            assert "modified" in result
            assert "untracked" in result


class TestGitBranch:
    """Tests for git_branch()."""

    def test_git_branch_returns_name(self):
        """Should return branch name."""
        with patch("lib.git.run_git") as mock_run:
            mock_run.return_value = "main"

            result = git_branch()

            assert result == "main"

    def test_git_branch_feature_branch(self):
        """Should return feature branch name."""
        with patch("lib.git.run_git") as mock_run:
            mock_run.return_value = "feat/new-feature"

            result = git_branch()

            assert result == "feat/new-feature"


class TestGitCommit:
    """Tests for git_commit()."""

    def test_git_commit_success(self):
        """Should return success on commit."""
        with patch("lib.git.run_git") as mock_run:
            mock_run.return_value = ""

            success, msg = git_commit("test commit")

            assert success is True
            assert "Commit created" in msg

    def test_git_commit_with_co_author(self):
        """Should include co-author in message."""
        with patch("lib.git.run_git") as mock_run:
            mock_run.return_value = ""

            git_commit("test commit", co_author="Test <test@example.com>")

            call_args = mock_run.call_args[0][0]
            message = call_args[2]  # -m argument
            assert "Co-Authored-By: Test <test@example.com>" in message

    def test_git_commit_failure(self):
        """Should return failure on error."""
        with patch("lib.git.run_git") as mock_run:
            mock_run.side_effect = GitError("nothing to commit")

            success, msg = git_commit("test commit")

            assert success is False
            assert "nothing to commit" in msg


class TestIsProtectedBranch:
    """Tests for is_protected_branch()."""

    def test_is_protected_branch_main(self):
        """Should detect main as protected."""
        with patch("lib.git.git_branch") as mock_branch:
            mock_branch.return_value = "main"

            result = is_protected_branch()

            assert result is True

    def test_is_protected_branch_master(self):
        """Should detect master as protected."""
        with patch("lib.git.git_branch") as mock_branch:
            mock_branch.return_value = "master"

            result = is_protected_branch()

            assert result is True

    def test_is_protected_branch_feature(self):
        """Should not detect feature branch as protected."""
        with patch("lib.git.git_branch") as mock_branch:
            mock_branch.return_value = "feat/new-feature"

            result = is_protected_branch()

            assert result is False

    def test_is_protected_branch_custom_list(self):
        """Should use custom protected list."""
        with patch("lib.git.git_branch") as mock_branch:
            mock_branch.return_value = "develop"

            result = is_protected_branch(protected=["main", "develop"])

            assert result is True

    def test_is_protected_branch_not_in_custom_list(self):
        """Should not protect branch not in custom list."""
        with patch("lib.git.git_branch") as mock_branch:
            mock_branch.return_value = "main"

            result = is_protected_branch(protected=["production"])

            assert result is False
