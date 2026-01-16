"""Tests for lib/version.py."""

import json

import pytest

from lib.version import get_version, sync_versions


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
