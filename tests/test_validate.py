"""Tests for events/validate.py - Git validation."""

import json
from unittest.mock import patch

import pytest

from events.validate import validate_branch_name, validate_commit_message

# Default templates for testing (same as in validate.py defaults)
BRANCH_INVALID_TPL = "Branch '{branch}' should match: {pattern}"
COMMIT_INVALID_TPL = "Commit should match: type(scope): message (types: {types})"
SCOPE_INVALID_TPL = "Unknown scope '{scope}'. Allowed: {allowed}"


class TestValidateBranchName:
    """Tests for validate_branch_name()."""

    def test_validate_branch_name_valid_feat(self, tmp_path, monkeypatch):
        """Should accept valid feat branch."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {
                "protected_branches": ["main"],
                "conventions": {"types": ["feat", "fix"]},
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_branch_name("feat/add-feature", BRANCH_INVALID_TPL)

        assert valid is True

    def test_validate_branch_name_valid_fix(self, tmp_path, monkeypatch):
        """Should accept valid fix branch."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {
                "protected_branches": ["main"],
                "conventions": {"types": ["feat", "fix"]},
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_branch_name("fix/bug-123", BRANCH_INVALID_TPL)

        assert valid is True

    def test_validate_branch_name_protected_main(self, tmp_path, monkeypatch):
        """Should accept protected branch."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {"protected_branches": ["main"]},
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_branch_name("main", BRANCH_INVALID_TPL)

        assert valid is True

    def test_validate_branch_name_invalid_format(self, tmp_path, monkeypatch):
        """Should reject invalid branch format."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {
                "protected_branches": ["main"],
                "conventions": {"types": ["feat", "fix"]},
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_branch_name("invalid-branch", BRANCH_INVALID_TPL)

        assert valid is False

    def test_validate_branch_name_invalid_type(self, tmp_path, monkeypatch):
        """Should reject unknown branch type."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {
                "protected_branches": ["main"],
                "conventions": {"types": ["feat", "fix"]},
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_branch_name("unknown/branch", BRANCH_INVALID_TPL)

        assert valid is False

    def test_validate_branch_name_with_dashes(self, tmp_path, monkeypatch):
        """Should accept branch with dashes in description."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {
                "protected_branches": ["main"],
                "conventions": {"types": ["feat", "fix", "chore"]},
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_branch_name("chore/update-dependencies-v2", BRANCH_INVALID_TPL)

        assert valid is True


class TestValidateCommitMessage:
    """Tests for validate_commit_message()."""

    def test_validate_commit_message_valid_simple(self, tmp_path, monkeypatch):
        """Should accept valid simple commit."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {
                "conventions": {
                    "types": ["feat", "fix"],
                    "scopes": {"mode": "off"},
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_commit_message("feat: add new feature", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL)

        assert valid is True

    def test_validate_commit_message_valid_with_scope(self, tmp_path, monkeypatch):
        """Should accept valid commit with scope."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {
                "conventions": {
                    "types": ["feat", "fix"],
                    "scopes": {
                        "mode": "strict",
                        "allowed": ["core", "lib"],
                        "internal": [],
                    },
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_commit_message("fix(core): fix bug", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL)

        assert valid is True

    def test_validate_commit_message_invalid_type(self, tmp_path, monkeypatch):
        """Should reject invalid commit type."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {
                "conventions": {
                    "types": ["feat", "fix"],
                    "scopes": {"mode": "off"},
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_commit_message("invalid: message", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL)

        assert valid is False

    def test_validate_commit_message_invalid_format(self, tmp_path, monkeypatch):
        """Should reject invalid commit format."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {"conventions": {"types": ["feat", "fix"]}},
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_commit_message("no colon here", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL)

        assert valid is False

    def test_validate_commit_message_strict_scope_invalid(self, tmp_path, monkeypatch):
        """Should reject unknown scope in strict mode."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {
                "conventions": {
                    "types": ["feat", "fix"],
                    "scopes": {
                        "mode": "strict",
                        "allowed": ["core", "lib"],
                        "internal": [],
                    },
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_commit_message("feat(unknown): message", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL)

        assert valid is False
        assert "unknown" in msg.lower() or "Unknown" in msg

    def test_validate_commit_message_internal_scope(self, tmp_path, monkeypatch):
        """Should accept internal scope in strict mode."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {
                "conventions": {
                    "types": ["feat", "fix", "chore"],
                    "scopes": {
                        "mode": "strict",
                        "allowed": ["core"],
                        "internal": ["ci", "deps"],
                    },
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_commit_message("chore(ci): update workflow", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL)

        assert valid is True

    def test_validate_commit_message_warn_mode(self, tmp_path, monkeypatch):
        """Should accept unknown scope in warn mode."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {
                "conventions": {
                    "types": ["feat", "fix"],
                    "scopes": {
                        "mode": "warn",
                        "allowed": ["core"],
                        "internal": [],
                    },
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_commit_message("feat(unknown): message", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL)

        # In warn mode, validation should pass
        assert valid is True

    def test_validate_commit_message_off_mode(self, tmp_path, monkeypatch):
        """Should accept any scope in off mode."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "git": {
                "conventions": {
                    "types": ["feat", "fix"],
                    "scopes": {
                        "mode": "off",
                        "allowed": [],
                        "internal": [],
                    },
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        valid, msg = validate_commit_message("feat(anything): message", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL)

        assert valid is True
