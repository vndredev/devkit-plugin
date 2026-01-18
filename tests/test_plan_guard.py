"""Tests for events/plan_guard.py - Plan Guard hook."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from events.plan_guard import (
    get_plan_marker_path,
    is_plan_approved,
    is_plan_required_branch,
)


class TestIsPlanRequiredBranch:
    """Tests for is_plan_required_branch()."""

    def test_feat_branch_requires_plan(self):
        """Should require plan for feat/* branches."""
        assert is_plan_required_branch("feat/add-feature") is True
        assert is_plan_required_branch("feat/login") is True
        assert is_plan_required_branch("feat/user-auth-system") is True

    def test_refactor_branch_requires_plan(self):
        """Should require plan for refactor/* branches."""
        assert is_plan_required_branch("refactor/cleanup") is True
        assert is_plan_required_branch("refactor/extract-utils") is True

    def test_fix_branch_does_not_require_plan(self):
        """Should not require plan for fix/* branches."""
        assert is_plan_required_branch("fix/bug-123") is False
        assert is_plan_required_branch("fix/typo") is False

    def test_chore_branch_does_not_require_plan(self):
        """Should not require plan for chore/* branches."""
        assert is_plan_required_branch("chore/update-deps") is False
        assert is_plan_required_branch("chore/cleanup") is False

    def test_main_branch_does_not_require_plan(self):
        """Should not require plan for main branch."""
        assert is_plan_required_branch("main") is False

    def test_docs_branch_does_not_require_plan(self):
        """Should not require plan for docs/* branches."""
        assert is_plan_required_branch("docs/readme") is False

    def test_test_branch_does_not_require_plan(self):
        """Should not require plan for test/* branches."""
        assert is_plan_required_branch("test/add-tests") is False


class TestGetPlanMarkerPath:
    """Tests for get_plan_marker_path()."""

    def test_returns_correct_path_for_feat_branch(self, tmp_path, monkeypatch):
        """Should return correct marker path for feat branch."""
        monkeypatch.chdir(tmp_path)

        path = get_plan_marker_path("feat/add-feature")

        expected = tmp_path / ".claude" / ".plan-approved-feat-add-feature"
        assert path == expected

    def test_returns_correct_path_for_refactor_branch(self, tmp_path, monkeypatch):
        """Should return correct marker path for refactor branch."""
        monkeypatch.chdir(tmp_path)

        path = get_plan_marker_path("refactor/cleanup")

        expected = tmp_path / ".claude" / ".plan-approved-refactor-cleanup"
        assert path == expected

    def test_sanitizes_slash_in_branch_name(self, tmp_path, monkeypatch):
        """Should replace slashes with dashes in marker filename."""
        monkeypatch.chdir(tmp_path)

        path = get_plan_marker_path("feat/nested/branch")

        expected = tmp_path / ".claude" / ".plan-approved-feat-nested-branch"
        assert path == expected


class TestIsPlanApproved:
    """Tests for is_plan_approved()."""

    def test_returns_false_when_marker_missing(self, tmp_path, monkeypatch):
        """Should return False when marker file doesn't exist."""
        monkeypatch.chdir(tmp_path)

        result = is_plan_approved("feat/add-feature")

        assert result is False

    def test_returns_true_when_marker_exists(self, tmp_path, monkeypatch):
        """Should return True when marker file exists."""
        monkeypatch.chdir(tmp_path)

        # Create the marker file
        marker_dir = tmp_path / ".claude"
        marker_dir.mkdir(parents=True)
        (marker_dir / ".plan-approved-feat-add-feature").touch()

        result = is_plan_approved("feat/add-feature")

        assert result is True


class TestPlanMarkerCreation:
    """Tests for create_plan_marker() in plan.py."""

    def test_creates_marker_for_feat_branch(self, tmp_path, monkeypatch):
        """Should create marker file for feat branch."""
        from events.plan import create_plan_marker

        monkeypatch.chdir(tmp_path)

        create_plan_marker("feat/add-feature")

        marker = tmp_path / ".claude" / ".plan-approved-feat-add-feature"
        assert marker.exists()

    def test_creates_marker_for_refactor_branch(self, tmp_path, monkeypatch):
        """Should create marker file for refactor branch."""
        from events.plan import create_plan_marker

        monkeypatch.chdir(tmp_path)

        create_plan_marker("refactor/cleanup")

        marker = tmp_path / ".claude" / ".plan-approved-refactor-cleanup"
        assert marker.exists()

    def test_does_not_create_marker_for_fix_branch(self, tmp_path, monkeypatch):
        """Should not create marker file for fix branch."""
        from events.plan import create_plan_marker

        monkeypatch.chdir(tmp_path)

        create_plan_marker("fix/bug-123")

        marker = tmp_path / ".claude" / ".plan-approved-fix-bug-123"
        assert not marker.exists()

    def test_does_not_create_marker_for_main_branch(self, tmp_path, monkeypatch):
        """Should not create marker file for main branch."""
        from events.plan import create_plan_marker

        monkeypatch.chdir(tmp_path)

        create_plan_marker("main")

        # .claude directory should not even be created
        claude_dir = tmp_path / ".claude"
        assert not claude_dir.exists() or not any(claude_dir.glob(".plan-approved-*"))

    def test_creates_parent_directory_if_needed(self, tmp_path, monkeypatch):
        """Should create .claude directory if it doesn't exist."""
        from events.plan import create_plan_marker

        monkeypatch.chdir(tmp_path)
        # Ensure .claude doesn't exist
        assert not (tmp_path / ".claude").exists()

        create_plan_marker("feat/new-feature")

        marker = tmp_path / ".claude" / ".plan-approved-feat-new-feature"
        assert marker.exists()


class TestPlanGuardIntegration:
    """Integration tests for plan_guard hook behavior."""

    def test_blocks_edit_on_feat_branch_without_marker(self, tmp_path, monkeypatch):
        """Should block edits on feat branch without plan marker."""
        from lib.config import clear_cache

        clear_cache()

        # Setup config
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "hooks": {"plan_guard": {"enabled": True}},
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        # Check that plan is required and not approved
        assert is_plan_required_branch("feat/add-feature") is True
        assert is_plan_approved("feat/add-feature") is False

    def test_allows_edit_on_feat_branch_with_marker(self, tmp_path, monkeypatch):
        """Should allow edits on feat branch with plan marker."""
        from lib.config import clear_cache

        clear_cache()

        # Setup config
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "hooks": {"plan_guard": {"enabled": True}},
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        # Create marker
        (tmp_path / ".claude" / ".plan-approved-feat-add-feature").touch()
        monkeypatch.chdir(tmp_path)

        # Check that plan is approved
        assert is_plan_required_branch("feat/add-feature") is True
        assert is_plan_approved("feat/add-feature") is True

    def test_allows_edit_on_fix_branch_without_marker(self, tmp_path, monkeypatch):
        """Should allow edits on fix branch without plan marker."""
        from lib.config import clear_cache

        clear_cache()

        # Setup config
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "hooks": {"plan_guard": {"enabled": True}},
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        # fix/* doesn't require plan
        assert is_plan_required_branch("fix/bug-123") is False
