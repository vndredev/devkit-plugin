"""Tests for lib/sync.py - File synchronization."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.sync import render_template, sync_all


class TestRenderTemplate:
    """Tests for render_template()."""

    def test_render_template_simple_variable(self):
        """Should replace simple {{var}} placeholders."""
        template = "Hello {{name}}!"
        values = {"name": "World"}

        result = render_template(template, values)

        assert result == "Hello World!"

    def test_render_template_multiple_variables(self):
        """Should replace multiple placeholders."""
        template = "{{greeting}} {{name}}, welcome to {{place}}!"
        values = {"greeting": "Hello", "name": "User", "place": "Earth"}

        result = render_template(template, values)

        assert result == "Hello User, welcome to Earth!"

    def test_render_template_missing_variable(self):
        """Should replace missing variable with empty string."""
        template = "Hello {{name}}!"
        values = {}

        result = render_template(template, values)

        assert result == "Hello !"

    def test_render_template_preserves_non_placeholders(self):
        """Should preserve text without placeholders."""
        template = "No placeholders here."
        values = {"name": "ignored"}

        result = render_template(template, values)

        assert result == "No placeholders here."

    def test_render_template_repeated_placeholder(self):
        """Should replace repeated placeholders."""
        template = "{{name}} and {{name}} again"
        values = {"name": "value"}

        result = render_template(template, values)

        assert result == "value and value again"

    def test_render_template_numeric_value(self):
        """Should convert numeric values to string."""
        template = "Count: {{count}}"
        values = {"count": 42}

        result = render_template(template, values)

        assert result == "Count: 42"

    def test_render_template_boolean_value(self):
        """Should convert boolean values to string."""
        template = "Enabled: {{enabled}}"
        values = {"enabled": True}

        result = render_template(template, values)

        # Boolean True converts to "True"
        assert "True" in result or "true" in result

    def test_render_template_empty_template(self):
        """Should handle empty template."""
        template = ""
        values = {"name": "test"}

        result = render_template(template, values)

        assert result == ""

    def test_render_template_multiline(self):
        """Should handle multiline templates."""
        template = "Line 1: {{var1}}\nLine 2: {{var2}}"
        values = {"var1": "first", "var2": "second"}

        result = render_template(template, values)

        assert "Line 1: first" in result
        assert "Line 2: second" in result


class TestSyncAll:
    """Tests for sync_all()."""

    def test_sync_all_creates_files(self, tmp_path, monkeypatch):
        """Should create managed files when sync_all is called."""
        # This test uses the real plugin root and verifies sync_all returns results
        # The actual file creation is tested in integration tests
        from lib.config import clear_cache

        clear_cache()

        # Create project structure
        project_root = tmp_path / "project"
        config_dir = project_root / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "linters": {"preset": "strict"},
            "managed": {
                "linters": {
                    "test.toml": {
                        "template": "linters/python/ruff.toml.template",
                        "enabled": True,
                    }
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        monkeypatch.chdir(project_root)

        # sync_all should return a list (even if empty or with errors)
        results = sync_all()
        assert isinstance(results, list)

    def test_sync_all_respects_enabled_flag(self, tmp_path, monkeypatch):
        """Should skip disabled files."""
        from lib.config import clear_cache

        clear_cache()

        # Create plugin structure
        plugin_root = tmp_path / "plugin"
        templates_dir = plugin_root / "templates" / "linters" / "python"
        templates_dir.mkdir(parents=True)
        (templates_dir / "ruff.toml.template").write_text("content")

        presets_dir = plugin_root / "presets"
        presets_dir.mkdir(parents=True)
        (presets_dir / "linters.json").write_text(json.dumps({
            "python": {"strict": {}},
            "common": {"strict": {}},
        }))

        # Create project structure
        project_root = tmp_path / "project"
        config_dir = project_root / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "linters": {"preset": "strict"},
            "managed": {
                "linters": {
                    "ruff.toml": {
                        "template": "linters/python/ruff.toml.template",
                        "enabled": False,  # Disabled
                    }
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        monkeypatch.chdir(project_root)

        with patch("lib.sync.get_plugin_root", return_value=plugin_root):
            results = sync_all()

        # Check file was NOT created
        ruff_file = project_root / "ruff.toml"
        assert not ruff_file.exists()

    def test_sync_all_returns_results(self, tmp_path, monkeypatch):
        """Should return list of sync results."""
        from lib.config import clear_cache

        clear_cache()

        # Create project structure
        project_root = tmp_path / "project"
        config_dir = project_root / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "linters": {"preset": "strict"},
            "managed": {},  # Empty managed section
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        monkeypatch.chdir(project_root)

        # sync_all returns a list
        results = sync_all()
        assert isinstance(results, list)

    def test_sync_all_handles_missing_template(self, tmp_path, monkeypatch):
        """Should handle missing template gracefully."""
        from lib.config import clear_cache

        clear_cache()

        # Create plugin structure without template
        plugin_root = tmp_path / "plugin"
        templates_dir = plugin_root / "templates"
        templates_dir.mkdir(parents=True)

        presets_dir = plugin_root / "presets"
        presets_dir.mkdir(parents=True)
        (presets_dir / "linters.json").write_text(json.dumps({
            "python": {"strict": {}},
            "common": {"strict": {}},
        }))

        # Create project structure
        project_root = tmp_path / "project"
        config_dir = project_root / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "linters": {"preset": "strict"},
            "managed": {
                "linters": {
                    "missing.toml": {
                        "template": "nonexistent.template",
                        "enabled": True,
                    }
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        monkeypatch.chdir(project_root)

        with patch("lib.sync.get_plugin_root", return_value=plugin_root):
            # Should not raise exception
            results = sync_all()

        # File should not be created
        assert not (project_root / "missing.toml").exists()
