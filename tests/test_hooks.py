"""Tests for lib/hooks.py - Shared hook utilities."""

import io
import json
import sys

import pytest

from lib.hooks import (
    consume_stdin,
    load_prompts,
    noop_response,
    output_response,
    read_hook_input,
)


class TestReadHookInput:
    """Tests for read_hook_input()."""

    def test_read_valid_json(self, monkeypatch):
        """Should parse valid JSON from stdin."""
        data = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(data)))

        result = read_hook_input()

        assert result == data
        assert result["tool_name"] == "Bash"

    def test_read_empty_object(self, monkeypatch):
        """Should parse empty JSON object."""
        monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

        result = read_hook_input()

        assert result == {}

    def test_read_invalid_json_returns_empty(self, monkeypatch):
        """Should return empty dict for invalid JSON."""
        monkeypatch.setattr(sys, "stdin", io.StringIO("not valid json"))

        result = read_hook_input()

        assert result == {}

    def test_read_empty_stdin_returns_empty(self, monkeypatch):
        """Should return empty dict for empty stdin."""
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))

        result = read_hook_input()

        assert result == {}


class TestConsumeStdin:
    """Tests for consume_stdin()."""

    def test_consume_valid_json(self, monkeypatch):
        """Should consume valid JSON without error."""
        monkeypatch.setattr(sys, "stdin", io.StringIO('{"key": "value"}'))

        # Should not raise
        consume_stdin()

    def test_consume_invalid_json(self, monkeypatch):
        """Should handle invalid JSON without error."""
        monkeypatch.setattr(sys, "stdin", io.StringIO("invalid"))

        # Should not raise
        consume_stdin()

    def test_consume_empty_stdin(self, monkeypatch):
        """Should handle empty stdin without error."""
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))

        # Should not raise
        consume_stdin()


class TestOutputResponse:
    """Tests for output_response()."""

    def test_output_simple_response(self, capsys):
        """Should output JSON response."""
        response = {"continue": True}

        output_response(response)

        captured = capsys.readouterr()
        assert json.loads(captured.out) == {"continue": True}

    def test_output_complex_response(self, capsys):
        """Should output complex JSON response."""
        response = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": "test context",
            }
        }

        output_response(response)

        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert parsed["hookSpecificOutput"]["additionalContext"] == "test context"


class TestNoopResponse:
    """Tests for noop_response()."""

    def test_noop_default_hook(self, capsys):
        """Should output noop for default PostToolUse hook."""
        noop_response()

        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed == {"hookSpecificOutput": {"hookEventName": "PostToolUse"}}

    def test_noop_custom_hook(self, capsys):
        """Should output noop for custom hook name."""
        noop_response("SessionStart")

        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed == {"hookSpecificOutput": {"hookEventName": "SessionStart"}}


class TestAllowResponse:
    """Tests for allow_response()."""

    def test_allow_exits(self):
        """Should exit with code 0."""
        from lib.hooks import allow_response

        with pytest.raises(SystemExit) as exc_info:
            allow_response()

        assert exc_info.value.code == 0

    def test_allow_outputs_continue_true(self, capsys):
        """Should output continue: true before exit."""
        from lib.hooks import allow_response

        with pytest.raises(SystemExit):
            allow_response()

        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["continue"] is True
        assert parsed["hookSpecificOutput"]["hookEventName"] == "PreToolUse"


class TestDenyResponse:
    """Tests for deny_response()."""

    def test_deny_exits(self):
        """Should exit with code 0."""
        from lib.hooks import deny_response

        with pytest.raises(SystemExit) as exc_info:
            deny_response("test reason")

        assert exc_info.value.code == 0

    def test_deny_outputs_reason(self, capsys):
        """Should output deny with reason before exit."""
        from lib.hooks import deny_response

        with pytest.raises(SystemExit):
            deny_response("blocked for testing")

        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert parsed["hookSpecificOutput"]["permissionDecisionReason"] == "blocked for testing"


class TestLoadPrompts:
    """Tests for load_prompts()."""

    def test_load_prompts_with_defaults(self, tmp_path, monkeypatch):
        """Should return defaults when config has no prompts."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"hooks": {"session": {}}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        defaults = {"greeting": "Hello", "farewell": "Goodbye"}
        result = load_prompts("hooks.session.prompts", defaults)

        assert result == defaults

    def test_load_prompts_merges_config(self, tmp_path, monkeypatch):
        """Should merge config prompts with defaults."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"hooks": {"session": {"prompts": {"greeting": "Hi there"}}}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        defaults = {"greeting": "Hello", "farewell": "Goodbye"}
        result = load_prompts("hooks.session.prompts", defaults)

        assert result["greeting"] == "Hi there"  # From config
        assert result["farewell"] == "Goodbye"  # From defaults

    def test_load_prompts_config_overrides_defaults(self, tmp_path, monkeypatch):
        """Should override all defaults with config values."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "hooks": {
                "session": {"prompts": {"greeting": "Hey", "farewell": "See ya", "extra": "Bonus"}}
            }
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        defaults = {"greeting": "Hello", "farewell": "Goodbye"}
        result = load_prompts("hooks.session.prompts", defaults)

        assert result["greeting"] == "Hey"
        assert result["farewell"] == "See ya"
        assert result["extra"] == "Bonus"
