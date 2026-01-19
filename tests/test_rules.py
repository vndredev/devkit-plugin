"""Tests for layer rules module."""

import pytest
from pathlib import Path
from unittest.mock import patch

from arch.rules import (
    LAYER_PRESETS,
    PYTHON_TEMPLATE,
    NEXTJS_TEMPLATE,
    get_violations,
    check_layer_rules,
    get_layer_info,
    init_project,
    get_init_preview,
)
from core.types import ProjectType


class TestLayerPresets:
    """Tests for LAYER_PRESETS configuration."""

    def test_has_small_preset(self):
        """Small preset exists with correct layers."""
        assert "small" in LAYER_PRESETS
        small = LAYER_PRESETS["small"]
        assert "lib" in small
        assert "entry" in small
        assert small["lib"]["tier"] < small["entry"]["tier"]

    def test_has_medium_preset(self):
        """Medium preset exists with core, lib, entry."""
        assert "medium" in LAYER_PRESETS
        medium = LAYER_PRESETS["medium"]
        assert "core" in medium
        assert "lib" in medium
        assert "entry" in medium

    def test_has_large_preset(self):
        """Large preset includes services layer."""
        assert "large" in LAYER_PRESETS
        large = LAYER_PRESETS["large"]
        assert "services" in large
        assert large["core"]["tier"] < large["services"]["tier"]

    def test_has_enterprise_preset(self):
        """Enterprise preset includes domain and usecases."""
        assert "enterprise" in LAYER_PRESETS
        enterprise = LAYER_PRESETS["enterprise"]
        assert "domain" in enterprise
        assert "usecases" in enterprise

    def test_tiers_are_ordered(self):
        """Each preset has ascending tier numbers."""
        for preset_name, preset in LAYER_PRESETS.items():
            tiers = sorted([cfg["tier"] for cfg in preset.values()])
            assert tiers == list(range(len(tiers))), f"Preset {preset_name} has non-sequential tiers"


class TestGetViolations:
    """Tests for get_violations function."""

    def test_returns_violations_from_analysis(self, tmp_path: Path):
        """Returns violations from analyze_dependencies."""
        mock_violations = [
            {"file": "src/core/test.py", "message": "imports from lib"}
        ]
        
        with patch("arch.rules.analyze_dependencies") as mock_analyze:
            mock_analyze.return_value = {"violations": mock_violations}
            result = get_violations(tmp_path)
        
        assert result == mock_violations

    def test_returns_empty_list_when_no_violations(self, tmp_path: Path):
        """Returns empty list when no violations."""
        with patch("arch.rules.analyze_dependencies") as mock_analyze:
            mock_analyze.return_value = {"violations": []}
            result = get_violations(tmp_path)
        
        assert result == []

    def test_uses_project_root_when_none_provided(self):
        """Uses get_project_root when root is None."""
        with patch("arch.rules.get_project_root") as mock_root, \
             patch("arch.rules.analyze_dependencies") as mock_analyze:
            mock_root.return_value = Path("/fake/root")
            mock_analyze.return_value = {"violations": []}
            
            get_violations(None)
            
            mock_root.assert_called_once()
            mock_analyze.assert_called_once_with(Path("/fake/root"))


class TestCheckLayerRules:
    """Tests for check_layer_rules function."""

    def test_returns_success_when_no_violations(self, tmp_path: Path):
        """Returns success tuple when no violations."""
        with patch("arch.rules.get_violations", return_value=[]):
            success, message = check_layer_rules(tmp_path)
        
        assert success is True
        assert "All imports follow layer rules" in message

    def test_returns_failure_with_violations(self, tmp_path: Path):
        """Returns failure tuple with violation details."""
        violations = [
            {"file": "src/core/test.py", "message": "imports lib.config"}
        ]
        
        with patch("arch.rules.get_violations", return_value=violations):
            with patch("arch.rules.get", return_value={}):
                success, message = check_layer_rules(tmp_path)
        
        assert success is False
        assert "1 layer violation" in message
        assert "src/core/test.py" in message
        assert "imports lib.config" in message

    def test_includes_layer_rules_from_config(self, tmp_path: Path):
        """Includes layer rules from config in message."""
        violations = [{"file": "test.py", "message": "violation"}]
        config_layers = {
            "core": {"tier": 0},
            "lib": {"tier": 1},
        }
        
        with patch("arch.rules.get_violations", return_value=violations):
            with patch("arch.rules.get", return_value=config_layers):
                success, message = check_layer_rules(tmp_path)
        
        assert "Layer Rules (from config.json)" in message
        assert "TIER 0: core" in message
        assert "TIER 1: lib" in message

    def test_includes_default_rules_when_no_config(self, tmp_path: Path):
        """Includes default rules when no config layers."""
        violations = [{"file": "test.py", "message": "violation"}]
        
        with patch("arch.rules.get_violations", return_value=violations):
            with patch("arch.rules.get", return_value={}):
                success, message = check_layer_rules(tmp_path)
        
        assert "Layer Rules:" in message
        assert "TIER 0 (core)" in message

    def test_formats_multiple_violations(self, tmp_path: Path):
        """Formats multiple violations correctly."""
        violations = [
            {"file": "src/core/a.py", "message": "violation 1"},
            {"file": "src/core/b.py", "message": "violation 2"},
        ]
        
        with patch("arch.rules.get_violations", return_value=violations):
            with patch("arch.rules.get", return_value={}):
                success, message = check_layer_rules(tmp_path)
        
        assert "2 layer violation(s)" in message
        assert "src/core/a.py" in message
        assert "src/core/b.py" in message


class TestGetLayerInfo:
    """Tests for get_layer_info function."""

    def test_returns_markdown_info(self):
        """Returns markdown formatted info."""
        result = get_layer_info()
        assert "# Clean Architecture Layers" in result
        assert "## Dependency Rule" in result

    def test_includes_diagram(self):
        """Includes ASCII diagram."""
        result = get_layer_info()
        assert "ENTRY POINTS" in result
        assert "CORE (TIER 0)" in result

    def test_includes_layer_table(self):
        """Includes layer descriptions table."""
        result = get_layer_info()
        assert "| Layer |" in result
        assert "| core |" in result

    def test_includes_config_example(self):
        """Includes JSON config example."""
        result = get_layer_info()
        assert '"arch"' in result
        assert '"layers"' in result


class TestInitProject:
    """Tests for init_project function."""

    def test_creates_python_structure(self, tmp_path: Path):
        """Creates Python project structure."""
        created = init_project(tmp_path, ProjectType.PYTHON)
        
        assert len(created) > 0
        assert (tmp_path / "src" / "core" / "__init__.py").exists()
        assert (tmp_path / "src" / "core" / "types.py").exists()
        assert (tmp_path / "src" / "core" / "errors.py").exists()

    def test_creates_nextjs_structure(self, tmp_path: Path):
        """Creates Next.js project structure."""
        created = init_project(tmp_path, ProjectType.NEXTJS)
        
        assert len(created) > 0
        assert (tmp_path / "src" / "types" / "index.ts").exists()
        assert (tmp_path / "src" / "lib" / "utils.ts").exists()

    def test_creates_typescript_same_as_nextjs(self, tmp_path: Path):
        """TypeScript uses same template as Next.js."""
        created = init_project(tmp_path, ProjectType.TYPESCRIPT)
        
        assert (tmp_path / "src" / "types" / "index.ts").exists()

    def test_skips_existing_files(self, tmp_path: Path):
        """Does not overwrite existing files."""
        # Create existing file
        core_dir = tmp_path / "src" / "core"
        core_dir.mkdir(parents=True)
        init_file = core_dir / "__init__.py"
        init_file.write_text("# Custom content")
        
        created = init_project(tmp_path, ProjectType.PYTHON)
        
        # Should not be in created list
        assert "src/core/__init__.py" not in created
        # Content should be unchanged
        assert init_file.read_text() == "# Custom content"

    def test_returns_empty_for_unsupported_type(self, tmp_path: Path):
        """Returns empty list for unsupported project type."""
        created = init_project(tmp_path, ProjectType.NODE)
        assert created == []

    def test_returns_list_of_created_files(self, tmp_path: Path):
        """Returns list of relative paths created."""
        created = init_project(tmp_path, ProjectType.PYTHON)
        
        assert all(isinstance(f, str) for f in created)
        assert "src/core/__init__.py" in created


class TestGetInitPreview:
    """Tests for get_init_preview function."""

    def test_shows_python_files(self):
        """Shows Python template files."""
        result = get_init_preview(ProjectType.PYTHON)
        
        assert "src/core/__init__.py" in result
        assert "src/core/types.py" in result

    def test_shows_nextjs_files(self):
        """Shows Next.js template files."""
        result = get_init_preview(ProjectType.NEXTJS)
        
        assert "src/types/index.ts" in result
        assert "src/lib/utils.ts" in result

    def test_includes_layer_preset(self):
        """Includes layer preset information."""
        result = get_init_preview(ProjectType.PYTHON, size="large")
        
        assert "Layer preset: large" in result
        assert "TIER 0" in result

    def test_returns_error_for_unsupported(self):
        """Returns error message for unsupported type."""
        result = get_init_preview(ProjectType.NODE)
        
        assert "Unsupported project type" in result

    def test_uses_medium_preset_by_default(self):
        """Uses medium preset when not specified."""
        result = get_init_preview(ProjectType.PYTHON)
        
        assert "Layer preset: medium" in result

    def test_includes_header_with_type(self):
        """Includes header with project type."""
        result = get_init_preview(ProjectType.PYTHON)
        
        assert "Clean Architecture Scaffold" in result
        assert "python" in result


class TestTemplates:
    """Tests for template constants."""

    def test_python_template_has_core_module(self):
        """Python template includes core module files."""
        assert "src/core/__init__.py" in PYTHON_TEMPLATE
        assert "src/core/types.py" in PYTHON_TEMPLATE
        assert "src/core/errors.py" in PYTHON_TEMPLATE

    def test_python_template_has_lib_module(self):
        """Python template includes lib module files."""
        assert "src/lib/__init__.py" in PYTHON_TEMPLATE
        assert "src/lib/config.py" in PYTHON_TEMPLATE

    def test_nextjs_template_has_types(self):
        """Next.js template includes types directory."""
        assert "src/types/index.ts" in NEXTJS_TEMPLATE

    def test_nextjs_template_has_lib(self):
        """Next.js template includes lib utilities."""
        assert "src/lib/utils.ts" in NEXTJS_TEMPLATE

    def test_templates_have_content(self):
        """All template files have non-empty content."""
        for path, content in PYTHON_TEMPLATE.items():
            assert content, f"Empty content in {path}"
        
        for path, content in NEXTJS_TEMPLATE.items():
            assert content, f"Empty content in {path}"

