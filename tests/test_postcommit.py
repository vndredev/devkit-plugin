"""Tests for events/postcommit.py - Version update after commit."""

import json
from io import StringIO
from unittest.mock import patch

import pytest


class TestPostcommitHook:
    """Tests for postcommit main()."""

    def test_ignores_non_bash_tool(self, tmp_path, monkeypatch, capsys):
        """Should noop for non-Bash tools."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test", "devMode": True}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        hook_input = {"tool_name": "Write", "tool_input": {}}
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps(hook_input)))

        from events.postcommit import main

        main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
        assert "additionalContext" not in output["hookSpecificOutput"]

    def test_ignores_when_devmode_disabled(self, tmp_path, monkeypatch, capsys):
        """Should noop when devMode is false."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test", "devMode": False}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        hook_input = {"tool_name": "Bash", "tool_input": {"command": "git commit -m 'test'"}}
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps(hook_input)))

        from events.postcommit import main

        main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
        assert "additionalContext" not in output["hookSpecificOutput"]

    def test_ignores_non_commit_git_commands(self, tmp_path, monkeypatch, capsys):
        """Should noop for non-commit git commands."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test", "devMode": True}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        hook_input = {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps(hook_input)))

        from events.postcommit import main

        main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
        assert "additionalContext" not in output["hookSpecificOutput"]

    def test_updates_version_on_git_commit(self, tmp_path, monkeypatch, capsys):
        """Should update plugin version after git commit."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test", "devMode": True}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        hook_input = {"tool_name": "Bash", "tool_input": {"command": "git commit -m 'feat: test'"}}
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps(hook_input)))

        with patch("events.postcommit.update_plugin_version") as mock_update:
            mock_update.return_value = (True, "0.19.0-abc1234")

            from events.postcommit import main

            main()

            mock_update.assert_called_once()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
        assert "Plugin version updated" in output["hookSpecificOutput"]["additionalContext"]

    def test_noop_when_update_fails(self, tmp_path, monkeypatch, capsys):
        """Should noop when version update fails."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test", "devMode": True}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        hook_input = {"tool_name": "Bash", "tool_input": {"command": "git commit -m 'feat: test'"}}
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps(hook_input)))

        with patch("events.postcommit.update_plugin_version") as mock_update:
            mock_update.return_value = (False, "plugin.json not found")

            from events.postcommit import main

            main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
        assert "additionalContext" not in output["hookSpecificOutput"]

    def test_handles_heredoc_commit(self, tmp_path, monkeypatch, capsys):
        """Should detect git commit with HEREDOC syntax."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test", "devMode": True}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        heredoc_cmd = '''git commit -m "$(cat <<'EOF'
feat: add feature

Co-Authored-By: Test <test@example.com>
EOF
)"'''
        hook_input = {"tool_name": "Bash", "tool_input": {"command": heredoc_cmd}}
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps(hook_input)))

        with patch("events.postcommit.update_plugin_version") as mock_update:
            mock_update.return_value = (True, "0.19.0-def5678")

            from events.postcommit import main

            main()

            mock_update.assert_called_once()
