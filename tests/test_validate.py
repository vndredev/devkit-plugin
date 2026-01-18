"""Tests for events/validate.py - Git validation."""

import json
from unittest.mock import patch

import pytest

from events.validate import (
    extract_commit_message,
    is_plugin_self_development,
    validate_branch_name,
    validate_commit_message,
    validate_dk_enforcement,
    validate_gh_command,
)

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

        valid, msg = validate_commit_message(
            "feat: add new feature", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL
        )

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

        valid, msg = validate_commit_message(
            "fix(core): fix bug", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL
        )

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

        valid, msg = validate_commit_message(
            "invalid: message", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL
        )

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

        valid, msg = validate_commit_message(
            "feat(unknown): message", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL
        )

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

        valid, msg = validate_commit_message(
            "chore(ci): update workflow", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL
        )

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

        valid, msg = validate_commit_message(
            "feat(unknown): message", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL
        )

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

        valid, msg = validate_commit_message(
            "feat(anything): message", COMMIT_INVALID_TPL, SCOPE_INVALID_TPL
        )

        assert valid is True


# Templates for gh command tests
GH_BLOCKED_TPL = "Blocked: '{cmd}' - too dangerous for automatic execution"
PR_MISSING_BODY_TPL = "gh pr create requires --body with PR template"


class TestValidateGhCommand:
    """Tests for validate_gh_command()."""

    def test_blocks_repo_delete(self):
        """Should block gh repo delete."""
        valid, msg = validate_gh_command(
            "gh repo delete owner/repo", GH_BLOCKED_TPL, PR_MISSING_BODY_TPL
        )

        assert valid is False
        assert "repo delete" in msg

    def test_blocks_secret_delete(self):
        """Should block gh secret delete."""
        valid, msg = validate_gh_command(
            "gh secret delete MY_SECRET", GH_BLOCKED_TPL, PR_MISSING_BODY_TPL
        )

        assert valid is False
        assert "secret delete" in msg

    def test_blocks_api_delete(self):
        """Should block gh api -X DELETE."""
        valid, msg = validate_gh_command(
            "gh api -X DELETE /repos/owner/repo", GH_BLOCKED_TPL, PR_MISSING_BODY_TPL
        )

        assert valid is False
        assert "DELETE" in msg

    def test_requires_pr_body(self):
        """Should require --body for pr create."""
        valid, msg = validate_gh_command(
            "gh pr create --title 'Test'", GH_BLOCKED_TPL, PR_MISSING_BODY_TPL
        )

        assert valid is False
        assert "body" in msg.lower()

    def test_allows_pr_create_with_body(self):
        """Should allow pr create with --body."""
        valid, msg = validate_gh_command(
            "gh pr create --title 'Test' --body 'Description'", GH_BLOCKED_TPL, PR_MISSING_BODY_TPL
        )

        assert valid is True

    def test_allows_safe_commands(self):
        """Should allow safe gh commands."""
        valid, msg = validate_gh_command("gh pr list", GH_BLOCKED_TPL, PR_MISSING_BODY_TPL)

        assert valid is True

    def test_allows_issue_commands(self):
        """Should allow gh issue commands."""
        valid, msg = validate_gh_command(
            "gh issue create --title 'Bug'", GH_BLOCKED_TPL, PR_MISSING_BODY_TPL
        )

        assert valid is True


class TestExtractCommitMessage:
    """Tests for extract_commit_message()."""

    def test_extract_simple_double_quotes(self):
        """Should extract message from -m with double quotes."""
        msg = extract_commit_message('git commit -m "feat: add feature"')

        assert msg == "feat: add feature"

    def test_extract_simple_single_quotes(self):
        """Should extract message from -m with single quotes."""
        msg = extract_commit_message("git commit -m 'fix: bug fix'")

        assert msg == "fix: bug fix"

    def test_extract_heredoc_eof(self):
        """Should extract message from HEREDOC with EOF."""
        cmd = '''git commit -m "$(cat <<'EOF'
feat(scope): add new feature

This is a longer description.

Co-Authored-By: Test <test@example.com>
EOF
)"'''
        msg = extract_commit_message(cmd)

        assert msg is not None
        assert "feat(scope): add new feature" in msg

    def test_extract_heredoc_with_multiline(self):
        """Should extract multiline HEREDOC message."""
        cmd = '''git commit -m "$(cat <<EOF
chore: update dependencies

- Updated package A
- Updated package B
EOF
)"'''
        msg = extract_commit_message(cmd)

        assert msg is not None
        assert "chore: update dependencies" in msg

    def test_returns_none_for_no_message(self):
        """Should return None if no -m flag."""
        msg = extract_commit_message("git commit --amend")

        assert msg is None

    def test_returns_none_for_empty_command(self):
        """Should return None for empty command."""
        msg = extract_commit_message("")

        assert msg is None

    def test_extract_with_scope(self):
        """Should extract message with scope."""
        msg = extract_commit_message('git commit -m "fix(core): resolve issue"')

        assert msg == "fix(core): resolve issue"


class TestIsPluginSelfDevelopment:
    """Tests for is_plugin_self_development()."""

    def test_returns_false_when_no_env_var(self, monkeypatch):
        """Should return False when CLAUDE_PLUGIN_ROOT is not set."""
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)

        result = is_plugin_self_development()

        assert result is False

    def test_returns_true_when_cwd_matches_plugin_root(self, tmp_path, monkeypatch):
        """Should return True when cwd matches CLAUDE_PLUGIN_ROOT."""
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        result = is_plugin_self_development()

        assert result is True

    def test_returns_false_when_cwd_differs_from_plugin_root(self, tmp_path, monkeypatch):
        """Should return False when cwd differs from CLAUDE_PLUGIN_ROOT."""
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        other_dir = tmp_path / "other"
        other_dir.mkdir()

        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
        monkeypatch.chdir(other_dir)

        result = is_plugin_self_development()

        assert result is False

    def test_handles_symlinks(self, tmp_path, monkeypatch):
        """Should resolve symlinks when comparing paths."""
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        symlink = tmp_path / "link"
        symlink.symlink_to(real_dir)

        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(real_dir))
        monkeypatch.chdir(symlink)

        result = is_plugin_self_development()

        assert result is True


class TestValidateDkEnforcement:
    """Tests for validate_dk_enforcement()."""

    def test_blocks_gh_pr_create(self):
        """Should block gh pr create command."""
        valid, msg = validate_dk_enforcement("gh pr create --title 'test'")

        assert valid is False
        assert "/dk git pr" in msg

    def test_blocks_gh_pr_merge(self):
        """Should block gh pr merge command."""
        valid, msg = validate_dk_enforcement("gh pr merge 123")

        assert valid is False
        assert "/dk git pr merge" in msg

    def test_blocks_vercel_deploy(self):
        """Should block vercel deploy command."""
        valid, msg = validate_dk_enforcement("vercel deploy --prod")

        assert valid is False
        assert "/dk vercel deploy" in msg

    def test_blocks_vercel_env(self):
        """Should block vercel env command."""
        valid, msg = validate_dk_enforcement("vercel env pull")

        assert valid is False
        assert "/dk vercel env" in msg

    def test_allows_unrelated_commands(self):
        """Should allow commands not in the mapping."""
        valid, msg = validate_dk_enforcement("git status")

        assert valid is True
        assert msg == ""

    def test_allows_commit_message_containing_gh_pr_create(self):
        """Should allow commit messages that contain 'gh pr create' as text."""
        # This tests that we use startswith, not substring match
        valid, msg = validate_dk_enforcement(
            'git commit -m "docs: update to use /dk git pr instead of gh pr create"'
        )

        assert valid is True

    def test_blocks_command_with_leading_whitespace(self):
        """Should handle commands with leading whitespace."""
        valid, msg = validate_dk_enforcement("  gh pr create --title 'test'")

        assert valid is False
        assert "/dk git pr" in msg
