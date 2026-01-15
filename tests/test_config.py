"""Tests for lib/config.py - Configuration loading and access."""

import json
from pathlib import Path

import pytest

from lib.config import clear_cache, get, get_project_root, load_config


class TestGetProjectRoot:
    """Tests for get_project_root()."""

    def test_get_project_root_finds_claude_dir(self, tmp_path, monkeypatch):
        """Should find project root when .claude/ exists."""
        clear_cache()
        # Create .claude directory
        (tmp_path / ".claude").mkdir()
        monkeypatch.chdir(tmp_path)

        result = get_project_root()
        assert result == tmp_path

    def test_get_project_root_finds_git_dir(self, tmp_path, monkeypatch):
        """Should find project root when .git/ exists."""
        clear_cache()
        # Create .git directory
        (tmp_path / ".git").mkdir()
        monkeypatch.chdir(tmp_path)

        result = get_project_root()
        assert result == tmp_path

    def test_get_project_root_prefers_claude_over_git(self, tmp_path, monkeypatch):
        """Should prefer .claude/ over .git/ when both exist."""
        clear_cache()
        # Create both directories
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".git").mkdir()
        monkeypatch.chdir(tmp_path)

        result = get_project_root()
        assert result == tmp_path

    def test_get_project_root_searches_parent_dirs(self, tmp_path, monkeypatch):
        """Should search parent directories for project root."""
        clear_cache()
        # Create .claude in root, subdir in child
        (tmp_path / ".claude").mkdir()
        subdir = tmp_path / "src" / "lib"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)

        result = get_project_root()
        assert result == tmp_path

    def test_get_project_root_raises_if_not_found(self, tmp_path, monkeypatch):
        """Should raise ConfigError if no project root found."""
        from core.errors import ConfigError

        clear_cache()
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigError):
            get_project_root()


class TestLoadConfig:
    """Tests for load_config()."""

    def test_load_config_reads_json(self, tmp_path, monkeypatch):
        """Should load and parse config.json."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test", "type": "python"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = load_config()

        assert result["project"]["name"] == "test"
        assert result["project"]["type"] == "python"

    def test_load_config_caches_result(self, tmp_path, monkeypatch):
        """Should cache config after first load."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "cached", "type": "python"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        # First load
        result1 = load_config()
        # Modify file (should not affect cached result)
        (config_dir / "config.json").write_text(json.dumps({"project": {"name": "modified", "type": "python"}}))
        # Second load (should return cached)
        result2 = load_config()

        assert result1["project"]["name"] == "cached"
        assert result2["project"]["name"] == "cached"

    def test_load_config_returns_empty_if_missing(self, tmp_path, monkeypatch):
        """Should return empty dict if config missing."""
        clear_cache()
        (tmp_path / ".claude").mkdir()
        monkeypatch.chdir(tmp_path)

        result = load_config()

        assert result == {}

    def test_load_config_handles_invalid_json(self, tmp_path, monkeypatch):
        """Should raise ConfigError for invalid JSON."""
        from core.errors import ConfigError

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        (config_dir / "config.json").write_text("invalid json {")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigError):
            load_config()


class TestGet:
    """Tests for get() - dot notation config access."""

    def test_get_simple_key(self, tmp_path, monkeypatch):
        """Should get simple top-level key."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test", "type": "python"}, "simple": "value"}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = get("simple")

        assert result == "value"

    def test_get_nested_key(self, tmp_path, monkeypatch):
        """Should get nested key with dot notation."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "nested-test", "type": "python"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = get("project.name")

        assert result == "nested-test"

    def test_get_deeply_nested_key(self, tmp_path, monkeypatch):
        """Should get deeply nested key."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"a": {"b": {"c": {"d": "deep"}}}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = get("a.b.c.d")

        assert result == "deep"

    def test_get_returns_default_if_missing(self, tmp_path, monkeypatch):
        """Should return default for missing key."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test", "type": "python"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = get("nonexistent.key", "default_value")

        assert result == "default_value"

    def test_get_returns_none_if_missing_no_default(self, tmp_path, monkeypatch):
        """Should return None for missing key without default."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test", "type": "python"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = get("nonexistent")

        assert result is None

    def test_get_returns_dict(self, tmp_path, monkeypatch):
        """Should return dict for nested object."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test", "type": "python"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = get("project")

        assert isinstance(result, dict)
        assert result["name"] == "test"

    def test_get_returns_list(self, tmp_path, monkeypatch):
        """Should return list values."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"items": ["a", "b", "c"]}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = get("items")

        assert result == ["a", "b", "c"]
