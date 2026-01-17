"""Tests for lib/version.py."""

import json
import os
from unittest.mock import patch

import pytest

from lib.version import (
    get_plugin_dev_recommendation,
    get_version,
    is_plugin_loaded_via_plugin_dir,
    is_project_a_plugin,
    sync_versions,
)


class TestGetVersion:
    """Tests for get_version()."""

    def test_reads_from_pyproject(self, tmp_path):
        """Should read version from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.2.3"\n')

        version = get_version(tmp_path)

        assert version == "1.2.3"

    def test_returns_default_if_missing(self, tmp_path):
        """Should return 0.0.0 if pyproject.toml missing."""
        version = get_version(tmp_path)

        assert version == "0.0.0"

    def test_returns_default_if_no_version(self, tmp_path):
        """Should return 0.0.0 if version field missing."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'test'\n")

        version = get_version(tmp_path)

        assert version == "0.0.0"

    def test_handles_invalid_toml(self, tmp_path):
        """Should return 0.0.0 for invalid TOML."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("invalid { toml")

        version = get_version(tmp_path)

        assert version == "0.0.0"

    def test_reads_from_package_json_if_no_pyproject(self, tmp_path):
        """Should read version from package.json for Node.js projects."""
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({"name": "test", "version": "4.5.6"}))

        version = get_version(tmp_path)

        assert version == "4.5.6"

    def test_prefers_pyproject_over_package_json(self, tmp_path):
        """Should prefer pyproject.toml over package.json."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.0.0"\n')

        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({"name": "test", "version": "2.0.0"}))

        version = get_version(tmp_path)

        assert version == "1.0.0"

    def test_reads_from_plugin_json_if_no_other_source(self, tmp_path):
        """Should read version from plugin.json as last resort."""
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        plugin_json = plugin_dir / "plugin.json"
        plugin_json.write_text(json.dumps({"name": "test", "version": "7.8.9"}))

        version = get_version(tmp_path)

        assert version == "7.8.9"

    def test_strips_commit_suffix_from_plugin_json(self, tmp_path):
        """Should strip commit suffix from plugin.json version."""
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        plugin_json = plugin_dir / "plugin.json"
        plugin_json.write_text(json.dumps({"name": "test", "version": "1.2.3-abc123"}))

        version = get_version(tmp_path)

        assert version == "1.2.3"


class TestSyncVersions:
    """Tests for sync_versions()."""

    def test_syncs_package_json(self, tmp_path):
        """Should update version in package.json."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "2.0.0"\n')

        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({"name": "test", "version": "1.0.0"}))

        results = sync_versions(tmp_path)

        # Check results
        pkg_result = next(r for r in results if "package.json" in r[0])
        assert pkg_result[1] is True
        assert "1.0.0 -> 2.0.0" in pkg_result[2]

        # Check file was updated
        data = json.loads(package_json.read_text())
        assert data["version"] == "2.0.0"

    def test_syncs_plugin_json(self, tmp_path):
        """Should update version in plugin.json."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "3.0.0"\n')

        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        plugin_json = plugin_dir / "plugin.json"
        plugin_json.write_text(json.dumps({"name": "test", "version": "0.0.0"}))

        results = sync_versions(tmp_path)

        # Check file was updated
        data = json.loads(plugin_json.read_text())
        assert data["version"] == "3.0.0"

    def test_syncs_config_jsonc(self, tmp_path):
        """Should update version in config.jsonc preserving comments."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.5.0"\n')

        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config_jsonc = config_dir / "config.jsonc"
        config_jsonc.write_text("""{
  // This is a comment
  "project": {
    "name": "test",
    "version": "0.1.0"  // Version comment
  }
}
""")

        results = sync_versions(tmp_path)

        # Check file was updated
        content = config_jsonc.read_text()
        assert '"version": "1.5.0"' in content
        # Comments should be preserved
        assert "// This is a comment" in content

    def test_skips_missing_files(self, tmp_path):
        """Should skip files that don't exist."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.0.0"\n')

        results = sync_versions(tmp_path)

        # All should be skipped
        for result in results:
            assert result[1] is True
            assert "skipped" in result[2] or "not found" in result[2]

    def test_reports_already_synced(self, tmp_path):
        """Should report when version already matches."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.0.0"\n')

        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({"name": "test", "version": "1.0.0"}))

        results = sync_versions(tmp_path)

        pkg_result = next(r for r in results if "package.json" in r[0])
        assert "already 1.0.0" in pkg_result[2]

    def test_uses_explicit_version(self, tmp_path):
        """Should use explicit version if provided."""
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({"name": "test", "version": "1.0.0"}))

        results = sync_versions(tmp_path, version="9.9.9")

        data = json.loads(package_json.read_text())
        assert data["version"] == "9.9.9"


class TestIsProjectAPlugin:
    """Tests for is_project_a_plugin()."""

    def test_returns_true_if_plugin_json_exists(self, tmp_path):
        """Should return True if .claude-plugin/plugin.json exists."""
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text('{"name": "test"}')

        assert is_project_a_plugin(tmp_path) is True

    def test_returns_false_if_no_plugin_json(self, tmp_path):
        """Should return False if no plugin.json."""
        assert is_project_a_plugin(tmp_path) is False

    def test_returns_false_if_only_claude_plugin_dir(self, tmp_path):
        """Should return False if only directory exists without plugin.json."""
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()

        assert is_project_a_plugin(tmp_path) is False


class TestIsPluginLoadedViaPluginDir:
    """Tests for is_plugin_loaded_via_plugin_dir()."""

    def test_returns_true_if_plugin_root_matches(self, tmp_path):
        """Should return True if CLAUDE_PLUGIN_ROOT matches project dir."""
        with patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": str(tmp_path)}):
            assert is_plugin_loaded_via_plugin_dir(tmp_path) is True

    def test_returns_false_if_plugin_root_differs(self, tmp_path):
        """Should return False if CLAUDE_PLUGIN_ROOT differs from project dir."""
        with patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": "/some/other/path"}):
            assert is_plugin_loaded_via_plugin_dir(tmp_path) is False

    def test_returns_false_if_no_plugin_root(self, tmp_path):
        """Should return False if CLAUDE_PLUGIN_ROOT not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure CLAUDE_PLUGIN_ROOT is not set
            os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
            assert is_plugin_loaded_via_plugin_dir(tmp_path) is False


class TestGetPluginDevRecommendation:
    """Tests for get_plugin_dev_recommendation()."""

    def test_returns_none_if_not_plugin(self, tmp_path):
        """Should return None if project is not a plugin."""
        assert get_plugin_dev_recommendation(tmp_path) is None

    def test_returns_none_if_already_loaded(self, tmp_path):
        """Should return None if plugin is already loaded via --plugin-dir."""
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text('{"name": "test"}')

        with patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": str(tmp_path)}):
            assert get_plugin_dev_recommendation(tmp_path) is None

    def test_returns_command_if_plugin_not_loaded(self, tmp_path):
        """Should return command if plugin project not loaded via --plugin-dir."""
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text('{"name": "test"}')

        with patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": "/other/path"}):
            result = get_plugin_dev_recommendation(tmp_path)

        assert result is not None
        assert "--plugin-dir" in result
        assert str(tmp_path) in result
