"""Tests for runtime layer guard."""

import sys
import pytest

from core.layer_guard import (
    DEFAULT_LAYERS,
    LayerViolationError,
    LayerGuard,
    enable_layer_guard,
    disable_layer_guard,
    get_violations,
    clear_violations,
    format_violations_report,
    is_enabled,
)


@pytest.fixture(autouse=True)
def cleanup_layer_guard():
    """Ensure layer guard is disabled and violations cleared after each test."""
    yield
    disable_layer_guard()
    clear_violations()


class TestLayerViolationError:
    """Tests for LayerViolationError."""

    def test_creates_error_with_details(self):
        """Error contains source, target, and tier info."""
        error = LayerViolationError("lib", "arch", 1, 2)
        assert error.source == "lib"
        assert error.target == "arch"
        assert error.source_tier == 1
        assert error.target_tier == 2

    def test_error_message_format(self):
        """Error message explains the violation."""
        error = LayerViolationError("lib", "arch", 1, 2)
        assert "lib" in str(error)
        assert "arch" in str(error)
        assert "tier 1" in str(error)
        assert "tier 2" in str(error)


class TestLayerGuard:
    """Tests for LayerGuard class."""

    def test_uses_default_layers(self):
        """Uses default layer config when none provided."""
        guard = LayerGuard()
        assert guard.layers == DEFAULT_LAYERS

    def test_accepts_custom_layers(self):
        """Accepts custom layer configuration."""
        custom = {"api": 0, "services": 1, "repos": 2}
        guard = LayerGuard(layers=custom)
        assert guard.layers == custom

    def test_get_layer_extracts_first_part(self):
        """Extracts layer name from module path."""
        guard = LayerGuard()
        assert guard._get_layer("lib.config") == "lib"
        assert guard._get_layer("core.types") == "core"
        assert guard._get_layer("events.validate") == "events"

    def test_get_layer_returns_none_for_unknown(self):
        """Returns None for non-layered modules."""
        guard = LayerGuard()
        assert guard._get_layer("json") is None
        assert guard._get_layer("pathlib") is None
        assert guard._get_layer("unknown.module") is None

    def test_find_spec_returns_none(self):
        """find_spec returns None (doesn't load modules)."""
        guard = LayerGuard()
        result = guard.find_spec("lib.config", None, None)
        assert result is None


class TestEnableDisableLayerGuard:
    """Tests for enable/disable functions."""

    def test_enable_adds_to_meta_path(self):
        """enable_layer_guard adds LayerGuard to sys.meta_path."""
        enable_layer_guard()
        assert any(isinstance(f, LayerGuard) for f in sys.meta_path)

    def test_disable_removes_from_meta_path(self):
        """disable_layer_guard removes LayerGuard from sys.meta_path."""
        enable_layer_guard()
        disable_layer_guard()
        assert not any(isinstance(f, LayerGuard) for f in sys.meta_path)

    def test_enable_idempotent(self):
        """Multiple enable calls don't add multiple guards."""
        enable_layer_guard()
        enable_layer_guard()
        enable_layer_guard()
        guard_count = sum(1 for f in sys.meta_path if isinstance(f, LayerGuard))
        assert guard_count == 1

    def test_is_enabled_reflects_state(self):
        """is_enabled returns correct state."""
        assert is_enabled() is False
        enable_layer_guard()
        assert is_enabled() is True
        disable_layer_guard()
        assert is_enabled() is False


class TestViolationTracking:
    """Tests for violation tracking."""

    def test_get_violations_returns_copy(self):
        """get_violations returns a copy, not the original."""
        violations = get_violations()
        violations.append({"test": "data"})
        assert get_violations() == []  # Original unchanged

    def test_clear_violations_empties_list(self):
        """clear_violations removes all recorded violations."""
        # We can't easily trigger a real violation, so test the function
        clear_violations()
        assert get_violations() == []


class TestFormatViolationsReport:
    """Tests for format_violations_report."""

    def test_no_violations_message(self):
        """Returns message when no violations."""
        clear_violations()
        result = format_violations_report()
        assert "No layer violations" in result

    def test_report_includes_header(self):
        """Report includes header when violations exist."""
        # Mock a violation by directly adding to _violations
        from core import layer_guard
        layer_guard._violations.append({
            "source": "lib.test",
            "target": "arch.check",
            "source_layer": "lib",
            "target_layer": "arch",
            "source_tier": 1,
            "target_tier": 2,
        })
        
        result = format_violations_report()
        assert "Layer Violations Report" in result
        assert "lib.test" in result
        assert "arch.check" in result
        assert "T1" in result
        assert "T2" in result


class TestDefaultLayers:
    """Tests for default layer configuration."""

    def test_default_layers_structure(self):
        """Default layers have correct structure."""
        assert "core" in DEFAULT_LAYERS
        assert "lib" in DEFAULT_LAYERS
        assert "arch" in DEFAULT_LAYERS
        assert "events" in DEFAULT_LAYERS

    def test_default_layers_ordering(self):
        """Default layers have correct tier ordering."""
        assert DEFAULT_LAYERS["core"] == 0
        assert DEFAULT_LAYERS["lib"] == 1
        assert DEFAULT_LAYERS["arch"] == 2
        assert DEFAULT_LAYERS["events"] == 3

    def test_tiers_are_ascending(self):
        """Higher layers have higher tier numbers."""
        assert DEFAULT_LAYERS["core"] < DEFAULT_LAYERS["lib"]
        assert DEFAULT_LAYERS["lib"] < DEFAULT_LAYERS["arch"]
        assert DEFAULT_LAYERS["arch"] < DEFAULT_LAYERS["events"]
