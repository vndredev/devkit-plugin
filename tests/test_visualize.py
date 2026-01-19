"""Tests for architecture visualization."""

import pytest
from unittest.mock import patch

from arch.visualize import (
    generate_mermaid_diagram,
    generate_ascii_diagram,
    generate_dependency_matrix,
)


# Sample layer config for testing
SAMPLE_LAYERS = {
    "core": {"tier": 0, "description": "Core types and errors"},
    "lib": {"tier": 1, "description": "I/O adapters"},
    "arch": {"tier": 2, "description": "Architecture analysis"},
    "events": {"tier": 3, "description": "Hook handlers"},
}


class TestGenerateMermaidDiagram:
    """Tests for generate_mermaid_diagram."""

    def test_returns_mermaid_markup(self):
        """Returns valid Mermaid markdown."""
        result = generate_mermaid_diagram(layers=SAMPLE_LAYERS)
        assert result.startswith("```mermaid")
        assert result.endswith("```")
        assert "graph TD" in result

    def test_includes_all_layers(self):
        """Includes all layer names as nodes."""
        result = generate_mermaid_diagram(layers=SAMPLE_LAYERS)
        assert "core[" in result
        assert "lib[" in result
        assert "arch[" in result
        assert "events[" in result

    def test_handles_empty_layers(self):
        """Returns placeholder for empty layers."""
        result = generate_mermaid_diagram(layers={})
        assert "No layers configured" in result

    def test_handles_none_layers(self):
        """Uses config when layers is None."""
        with patch("arch.visualize.get", return_value=SAMPLE_LAYERS):
            result = generate_mermaid_diagram(layers=None)
            assert "core[" in result

    def test_shows_default_edges(self):
        """Shows edges between adjacent tiers by default."""
        result = generate_mermaid_diagram(layers=SAMPLE_LAYERS)
        assert "core --> lib" in result
        assert "lib --> arch" in result
        assert "arch --> events" in result

    def test_shows_custom_deps(self):
        """Shows edges based on provided dependencies."""
        deps = {"lib": ["core"], "arch": ["lib"]}
        result = generate_mermaid_diagram(layers=SAMPLE_LAYERS, deps=deps)
        assert "lib --> core" in result
        assert "arch --> lib" in result

    def test_highlights_violations(self):
        """Highlights violation edges when requested."""
        deps = {"core": ["lib"]}  # Violation: tier 0 imports tier 1
        result = generate_mermaid_diagram(
            layers=SAMPLE_LAYERS, deps=deps, show_violations=True
        )
        assert "violation" in result
        assert "-.->|violation|" in result


class TestGenerateAsciiDiagram:
    """Tests for generate_ascii_diagram."""

    def test_returns_ascii_diagram(self):
        """Returns ASCII diagram with boxes."""
        result = generate_ascii_diagram(layers=SAMPLE_LAYERS)
        assert "Architecture Layers" in result
        assert "┌" in result
        assert "│" in result
        assert "└" in result

    def test_includes_all_layers(self):
        """Includes all layer names."""
        result = generate_ascii_diagram(layers=SAMPLE_LAYERS)
        assert "core" in result
        assert "lib" in result
        assert "arch" in result
        assert "events" in result

    def test_shows_tiers(self):
        """Shows tier numbers."""
        result = generate_ascii_diagram(layers=SAMPLE_LAYERS)
        assert "TIER 0" in result
        assert "TIER 1" in result
        assert "TIER 2" in result
        assert "TIER 3" in result

    def test_shows_descriptions(self):
        """Shows layer descriptions."""
        result = generate_ascii_diagram(layers=SAMPLE_LAYERS)
        assert "Core types" in result
        assert "I/O adapters" in result

    def test_shows_arrows_between_layers(self):
        """Shows arrows between layers."""
        result = generate_ascii_diagram(layers=SAMPLE_LAYERS)
        assert "▼" in result

    def test_handles_empty_layers(self):
        """Returns message for empty layers."""
        result = generate_ascii_diagram(layers={})
        assert "No layers configured" in result

    def test_includes_rule_explanation(self):
        """Includes import rule explanation."""
        result = generate_ascii_diagram(layers=SAMPLE_LAYERS)
        assert "Higher tiers may import from lower tiers" in result


class TestGenerateDependencyMatrix:
    """Tests for generate_dependency_matrix."""

    def test_returns_matrix(self):
        """Returns dependency matrix."""
        deps = {"lib": ["core"], "arch": ["lib", "core"]}
        result = generate_dependency_matrix(deps, layers=SAMPLE_LAYERS)
        assert "Dependency Matrix" in result

    def test_includes_header(self):
        """Includes column header with layer names."""
        deps = {"lib": ["core"]}
        result = generate_dependency_matrix(deps, layers=SAMPLE_LAYERS)
        assert "cor" in result  # Truncated to 3 chars

    def test_shows_valid_imports(self):
        """Shows checkmark for valid imports."""
        deps = {"lib": ["core"]}  # Valid: tier 1 -> tier 0
        result = generate_dependency_matrix(deps, layers=SAMPLE_LAYERS)
        assert "✓" in result

    def test_shows_violations(self):
        """Shows X for violations."""
        deps = {"core": ["lib"]}  # Violation: tier 0 -> tier 1
        result = generate_dependency_matrix(deps, layers=SAMPLE_LAYERS)
        assert "X" in result

    def test_shows_no_import(self):
        """Shows dot for no import."""
        deps = {"lib": ["core"]}
        result = generate_dependency_matrix(deps, layers=SAMPLE_LAYERS)
        assert "·" in result

    def test_handles_empty_deps(self):
        """Returns message for empty deps."""
        result = generate_dependency_matrix({}, layers=SAMPLE_LAYERS)
        assert "No dependencies to display" in result

    def test_handles_empty_layers(self):
        """Returns message for empty layers."""
        deps = {"lib": ["core"]}
        result = generate_dependency_matrix(deps, layers={})
        assert "No dependencies to display" in result

    def test_includes_legend(self):
        """Includes legend explanation."""
        deps = {"lib": ["core"]}
        result = generate_dependency_matrix(deps, layers=SAMPLE_LAYERS)
        assert "Legend:" in result
        assert "valid import" in result
        assert "violation" in result
