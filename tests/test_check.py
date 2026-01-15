"""Tests for arch/check.py - Health check system."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from arch.check import check_all, check_config, check_sync


class TestCheckConfig:
    """Tests for check_config()."""

    def test_check_config_valid(self, tmp_path, monkeypatch):
        """Should pass for valid config."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        is_valid, errors, missing = check_config()

        assert is_valid is True
        assert errors == []

    def test_check_config_missing_project(self, tmp_path, monkeypatch):
        """Should fail when project is missing."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"hooks": {}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        is_valid, errors, missing = check_config()

        assert is_valid is False
        assert any("project" in e.lower() for e in errors)

    def test_check_config_missing_project_name(self, tmp_path, monkeypatch):
        """Should fail when project.name is missing."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"type": "python"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        is_valid, errors, missing = check_config()

        assert is_valid is False
        assert any("name" in e.lower() for e in errors)

    def test_check_config_missing_project_type(self, tmp_path, monkeypatch):
        """Should fail when project.type is missing."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        is_valid, errors, missing = check_config()

        assert is_valid is False
        assert any("type" in e.lower() for e in errors)

    def test_check_config_invalid_project_type(self, tmp_path, monkeypatch):
        """Should fail for invalid project type."""
        from lib.config import clear_cache

        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test", "type": "invalid"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        is_valid, errors, missing = check_config()

        assert is_valid is False
        assert any("invalid" in e.lower() for e in errors)

    def test_check_config_missing_file(self, tmp_path, monkeypatch):
        """Should fail when config file is missing."""
        from lib.config import clear_cache

        clear_cache()
        (tmp_path / ".claude").mkdir()
        monkeypatch.chdir(tmp_path)

        is_valid, errors, missing = check_config()

        # Empty config returns empty dict, which fails validation
        assert is_valid is False


class TestCheckSync:
    """Tests for check_sync()."""

    def test_check_sync_returns_list(self, tmp_path, monkeypatch):
        """Should return list of results."""
        from lib.config import clear_cache

        clear_cache()

        # Create minimal project structure
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "linters": {"preset": "strict"},
            "managed": {},
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        # Create minimal plugin structure
        plugin_root = tmp_path / "plugin"
        presets_dir = plugin_root / "presets"
        presets_dir.mkdir(parents=True)
        (presets_dir / "linters.json").write_text(
            json.dumps(
                {
                    "python": {"strict": {}},
                    "common": {"strict": {}},
                }
            )
        )

        monkeypatch.chdir(tmp_path)

        with patch("arch.check.get_plugin_root", return_value=plugin_root):
            results = check_sync()

        assert isinstance(results, list)

    def test_check_sync_detects_missing_file(self, tmp_path, monkeypatch):
        """Should detect missing managed files."""
        from lib.config import clear_cache

        clear_cache()

        # Create project structure
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "linters": {"preset": "strict"},
            "managed": {
                "linters": {
                    "ruff.toml": {
                        "template": "linters/python/ruff.toml.template",
                        "enabled": True,
                    }
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        # Create plugin structure with template
        plugin_root = tmp_path / "plugin"
        templates_dir = plugin_root / "templates" / "linters" / "python"
        templates_dir.mkdir(parents=True)
        (templates_dir / "ruff.toml.template").write_text("[tool.ruff]")

        presets_dir = plugin_root / "presets"
        presets_dir.mkdir(parents=True)
        (presets_dir / "linters.json").write_text(
            json.dumps(
                {
                    "python": {"strict": {}},
                    "common": {"strict": {}},
                }
            )
        )

        monkeypatch.chdir(tmp_path)

        with patch("arch.check.get_plugin_root", return_value=plugin_root):
            results = check_sync()

        # Should have result for ruff.toml
        ruff_result = [r for r in results if r[0] == "ruff.toml"]
        assert len(ruff_result) == 1
        assert ruff_result[0][1] is False  # Not in sync (missing)
        assert ruff_result[0][2] == "missing"


class TestCheckAll:
    """Tests for check_all()."""

    def test_check_all_returns_dict(self, tmp_path, monkeypatch):
        """Should return dict with all check results."""
        from lib.config import clear_cache

        clear_cache()

        # Create project structure
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "linters": {"preset": "strict"},
            "managed": {},
            "arch": {"layers": {}},
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        # Create plugin structure
        plugin_root = tmp_path / "plugin"
        presets_dir = plugin_root / "presets"
        presets_dir.mkdir(parents=True)
        (presets_dir / "linters.json").write_text(
            json.dumps(
                {
                    "python": {"strict": {}},
                    "common": {"strict": {}},
                }
            )
        )

        monkeypatch.chdir(tmp_path)

        with patch("arch.check.get_plugin_root", return_value=plugin_root):
            result = check_all()

        assert isinstance(result, dict)
        assert "healthy" in result
        assert "config" in result
        assert "sync" in result
        assert "arch" in result

    def test_check_all_healthy_when_valid(self, tmp_path, monkeypatch):
        """Should be healthy when all checks pass."""
        from lib.config import clear_cache

        clear_cache()

        # Create project structure
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "linters": {"preset": "strict"},
            "managed": {},
            "arch": {"layers": {}},
            "testing": {"enabled": False},  # Disable testing to pass
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        # Create plugin structure
        plugin_root = tmp_path / "plugin"
        presets_dir = plugin_root / "presets"
        presets_dir.mkdir(parents=True)
        (presets_dir / "linters.json").write_text(
            json.dumps(
                {
                    "python": {"strict": {}},
                    "common": {"strict": {}},
                }
            )
        )

        monkeypatch.chdir(tmp_path)

        with patch("arch.check.get_plugin_root", return_value=plugin_root):
            result = check_all()

        assert result["healthy"] is True

    def test_check_all_unhealthy_when_invalid(self, tmp_path, monkeypatch):
        """Should be unhealthy when checks fail."""
        from lib.config import clear_cache

        clear_cache()

        # Create invalid config (missing project.type)
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"name": "test"}}  # Missing type
        (config_dir / "config.json").write_text(json.dumps(config))

        # Create plugin structure
        plugin_root = tmp_path / "plugin"
        presets_dir = plugin_root / "presets"
        presets_dir.mkdir(parents=True)
        (presets_dir / "linters.json").write_text(
            json.dumps(
                {
                    "python": {"strict": {}},
                    "common": {"strict": {}},
                }
            )
        )

        monkeypatch.chdir(tmp_path)

        with patch("arch.check.get_plugin_root", return_value=plugin_root):
            result = check_all()

        assert result["healthy"] is False
        assert result["config"]["ok"] is False

    def test_check_all_includes_tests(self, tmp_path, monkeypatch):
        """Should include tests section in results."""
        from lib.config import clear_cache

        clear_cache()

        # Create project structure with testing enabled
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"name": "test", "type": "python"},
            "linters": {"preset": "strict"},
            "managed": {},
            "arch": {"layers": {}},
            "testing": {
                "enabled": True,
                "required_modules": {"lib/config.py": ["get"]},
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))

        # Create plugin structure
        plugin_root = tmp_path / "plugin"
        presets_dir = plugin_root / "presets"
        presets_dir.mkdir(parents=True)
        (presets_dir / "linters.json").write_text(
            json.dumps(
                {
                    "python": {"strict": {}},
                    "common": {"strict": {}},
                }
            )
        )

        monkeypatch.chdir(tmp_path)

        with patch("arch.check.get_plugin_root", return_value=plugin_root):
            result = check_all()

        assert "tests" in result
        assert "status" in result["tests"]
        assert result["tests"]["status"] == "FAIL"  # No tests dir
