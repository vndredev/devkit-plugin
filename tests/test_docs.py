"""Tests for lib/docs.py - Documentation generator."""

import json
from pathlib import Path

import pytest

from lib.config import clear_cache
from lib.docs import (
    generate_arch_docs,
    generate_auto_section,
    get_docs_status,
    merge_sections,
    parse_sections,
)


class TestGenerateArchDocs:
    """Tests for generate_arch_docs()."""

    def test_returns_empty_for_no_layers(self, tmp_path, monkeypatch):
        """Should return empty string when no layers configured."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"arch": {"layers": {}}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = generate_arch_docs()

        assert result == ""

    def test_minimal_format(self, tmp_path, monkeypatch):
        """Should generate minimal format with layer names."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "arch": {
                "layers": {
                    "core": {"tier": 0},
                    "lib": {"tier": 1},
                }
            }
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = generate_arch_docs(format="minimal")

        assert "**Layers:**" in result
        assert "core" in result
        assert "lib" in result

    def test_compact_format(self, tmp_path, monkeypatch):
        """Should generate compact table format."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "arch": {
                "layers": {
                    "core": {"tier": 0, "description": "Core types"},
                    "lib": {"tier": 1, "description": "Library code"},
                }
            }
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = generate_arch_docs(format="compact")

        assert "| Layer | Tier | Description |" in result
        assert "`core`" in result
        assert "`lib`" in result
        assert "Core types" in result

    def test_full_format_includes_mermaid(self, tmp_path, monkeypatch):
        """Should generate full format with Mermaid diagram."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "arch": {
                "layers": {
                    "core": {"tier": 0},
                    "lib": {"tier": 1},
                }
            }
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = generate_arch_docs(format="full")

        assert "## Architecture" in result
        assert "```mermaid" in result
        assert "graph TD" in result
        assert "May Import" in result

    def test_full_format_shows_import_rules(self, tmp_path, monkeypatch):
        """Should show which layers can import from which."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "arch": {
                "layers": {
                    "core": {"tier": 0},
                    "lib": {"tier": 1},
                    "events": {"tier": 2},
                }
            }
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = generate_arch_docs(format="full")

        # core (tier 0) should only import from stdlib
        assert "stdlib only" in result
        # lib (tier 1) should be able to import from core
        assert "core" in result


class TestParseSections:
    """Tests for parse_sections()."""

    def test_parses_auto_section(self):
        """Should extract AUTO section content."""
        content = """# Header
<!-- AUTO:START -->
Auto content here
<!-- AUTO:END -->
Other content"""

        result = parse_sections(content)

        assert result["auto"] == "Auto content here"
        assert result["before_auto"] == "# Header"

    def test_parses_custom_section(self):
        """Should extract CUSTOM section content."""
        content = """<!-- AUTO:START -->
Auto content
<!-- AUTO:END -->
<!-- CUSTOM:START -->
Custom content here
<!-- CUSTOM:END -->"""

        result = parse_sections(content)

        assert result["custom"] == "Custom content here"

    def test_handles_missing_auto_section(self):
        """Should handle content without AUTO section."""
        content = """# Just a header
Some content"""

        result = parse_sections(content)

        assert result["auto"] == ""
        assert result["before_auto"] == ""

    def test_handles_missing_custom_section(self):
        """Should handle content without CUSTOM section."""
        content = """<!-- AUTO:START -->
Auto content
<!-- AUTO:END -->"""

        result = parse_sections(content)

        assert result["custom"] == ""

    def test_preserves_after_custom(self):
        """Should preserve content after CUSTOM section."""
        content = """<!-- AUTO:START -->
Auto
<!-- AUTO:END -->
<!-- CUSTOM:START -->
Custom
<!-- CUSTOM:END -->
Footer content"""

        result = parse_sections(content)

        assert result["after_custom"] == "Footer content"

    def test_handles_section_attributes(self):
        """Should handle sections with attributes."""
        content = """<!-- AUTO:START - Generated by devkit -->
Auto content
<!-- AUTO:END -->
<!-- CUSTOM:START - User content -->
Custom content
<!-- CUSTOM:END -->"""

        result = parse_sections(content)

        assert result["auto"] == "Auto content"
        assert result["custom"] == "Custom content"


class TestMergeSections:
    """Tests for merge_sections()."""

    def test_updates_auto_section(self):
        """Should replace AUTO section with new content."""
        old_content = """# Header
<!-- AUTO:START -->
Old auto content
<!-- AUTO:END -->
<!-- CUSTOM:START -->
Custom content
<!-- CUSTOM:END -->"""

        result = merge_sections(old_content, "New auto content")

        assert "New auto content" in result
        assert "Old auto content" not in result

    def test_preserves_custom_section(self):
        """Should preserve CUSTOM section content."""
        old_content = """<!-- AUTO:START -->
Auto
<!-- AUTO:END -->
<!-- CUSTOM:START -->
My custom docs
<!-- CUSTOM:END -->"""

        result = merge_sections(old_content, "Updated auto")

        assert "My custom docs" in result

    def test_preserves_header(self):
        """Should preserve content before AUTO section."""
        old_content = """# My Project

Some intro text

<!-- AUTO:START -->
Auto
<!-- AUTO:END -->
<!-- CUSTOM:START -->
Custom
<!-- CUSTOM:END -->"""

        result = merge_sections(old_content, "New auto")

        assert "# My Project" in result
        assert "Some intro text" in result

    def test_creates_default_custom_section(self):
        """Should create default CUSTOM section if missing."""
        old_content = """<!-- AUTO:START -->
Auto
<!-- AUTO:END -->"""

        result = merge_sections(old_content, "New auto")

        assert "<!-- CUSTOM:START" in result
        assert "## Project Specific" in result
        assert "_Add your documentation here._" in result


class TestGenerateAutoSection:
    """Tests for generate_auto_section()."""

    def test_includes_principles(self, tmp_path, monkeypatch):
        """Should include principles section."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"type": "python"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = generate_auto_section()

        assert "## Principles" in result

    def test_includes_custom_principles(self, tmp_path, monkeypatch):
        """Should use custom principles if configured."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {
                "type": "python",
                "principles": ["Test First - Write tests before code"],
            }
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = generate_auto_section()

        assert "**Test First**" in result
        assert "Write tests before code" in result

    def test_includes_commands_section(self, tmp_path, monkeypatch):
        """Should include commands section."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"type": "python"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = generate_auto_section()

        assert "## Commands" in result
        assert "/dk" in result

    def test_python_development_commands(self, tmp_path, monkeypatch):
        """Should show Python-specific development commands."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"type": "python"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = generate_auto_section()

        assert "uv run" in result

    def test_node_development_commands(self, tmp_path, monkeypatch):
        """Should show Node.js-specific development commands."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"type": "nextjs"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = generate_auto_section()

        assert "npm run dev" in result
        assert "npm test" in result

    def test_includes_git_conventions(self, tmp_path, monkeypatch):
        """Should include git conventions if configured."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {
            "project": {"type": "python"},
            "git": {
                "conventions": {
                    "types": ["feat", "fix", "chore"],
                    "branch_pattern": "{type}/{description}",
                }
            },
        }
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = generate_auto_section()

        assert "## Git Conventions" in result
        assert "feat" in result
        assert "fix" in result

    def test_includes_resources_section(self, tmp_path, monkeypatch):
        """Should include resources section."""
        clear_cache()
        config_dir = tmp_path / ".claude" / ".devkit"
        config_dir.mkdir(parents=True)
        config = {"project": {"type": "python"}}
        (config_dir / "config.json").write_text(json.dumps(config))
        monkeypatch.chdir(tmp_path)

        result = generate_auto_section()

        assert "## Resources" in result
        assert "Context7" in result


class TestGetDocsStatus:
    """Tests for get_docs_status()."""

    def test_returns_false_if_missing(self, tmp_path, monkeypatch):
        """Should return exists=False if CLAUDE.md missing."""
        clear_cache()
        (tmp_path / ".claude").mkdir()
        monkeypatch.chdir(tmp_path)

        result = get_docs_status(tmp_path)

        assert result["exists"] is False
        assert result["has_auto"] is False
        assert result["has_custom"] is False

    def test_detects_auto_section(self, tmp_path, monkeypatch):
        """Should detect AUTO section presence."""
        clear_cache()
        (tmp_path / ".claude").mkdir()
        (tmp_path / "CLAUDE.md").write_text("<!-- AUTO:START -->\nContent\n<!-- AUTO:END -->")
        monkeypatch.chdir(tmp_path)

        result = get_docs_status(tmp_path)

        assert result["exists"] is True
        assert result["has_auto"] is True

    def test_detects_custom_section(self, tmp_path, monkeypatch):
        """Should detect CUSTOM section presence."""
        clear_cache()
        (tmp_path / ".claude").mkdir()
        (tmp_path / "CLAUDE.md").write_text("<!-- CUSTOM:START -->\nContent\n<!-- CUSTOM:END -->")
        monkeypatch.chdir(tmp_path)

        result = get_docs_status(tmp_path)

        assert result["exists"] is True
        assert result["has_custom"] is True

    def test_detects_both_sections(self, tmp_path, monkeypatch):
        """Should detect both AUTO and CUSTOM sections."""
        clear_cache()
        (tmp_path / ".claude").mkdir()
        content = """<!-- AUTO:START -->
Auto
<!-- AUTO:END -->
<!-- CUSTOM:START -->
Custom
<!-- CUSTOM:END -->"""
        (tmp_path / "CLAUDE.md").write_text(content)
        monkeypatch.chdir(tmp_path)

        result = get_docs_status(tmp_path)

        assert result["exists"] is True
        assert result["has_auto"] is True
        assert result["has_custom"] is True
