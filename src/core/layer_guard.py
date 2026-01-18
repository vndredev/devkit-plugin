"""Runtime layer guard for Clean Architecture enforcement.

TIER 0: No internal imports, only Python stdlib.

The LayerGuard intercepts imports at runtime and blocks violations
of the Clean Architecture dependency rule.

Usage:
    # Enable in development mode
    export DEVKIT_LAYER_GUARD=1
    python -c "from core.layer_guard import enable_layer_guard; enable_layer_guard()"

    # Or in code (must be called before other imports)
    if os.getenv("DEVKIT_LAYER_GUARD"):
        from core.layer_guard import enable_layer_guard
        enable_layer_guard()

Note:
    This is a development tool. Do not enable in production.
    The guard adds overhead to every import operation.
"""

import inspect
import sys
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
from types import ModuleType

# Default layer configuration (can be overridden)
DEFAULT_LAYERS = {
    "core": 0,
    "lib": 1,
    "arch": 2,
    "events": 3,
}

# Track violations for reporting
_violations: list[dict] = []
_enabled = False


class LayerViolationError(ImportError):
    """Raised when an import violates layer rules."""

    def __init__(self, source: str, target: str, source_tier: int, target_tier: int):
        self.source = source
        self.target = target
        self.source_tier = source_tier
        self.target_tier = target_tier
        super().__init__(
            f"Layer violation: {source} (tier {source_tier}) "
            f"cannot import from {target} (tier {target_tier})"
        )


class LayerGuard(MetaPathFinder):
    """Meta path finder that enforces layer rules on imports.

    Intercepts import statements and checks if they violate
    the Clean Architecture dependency rule (higher tiers
    may only import from lower tiers).
    """

    def __init__(
        self,
        layers: dict[str, int] | None = None,
        strict: bool = False,
        log_violations: bool = True,
    ):
        """Initialize the layer guard.

        Args:
            layers: Layer name to tier mapping. Uses defaults if not provided.
            strict: If True, raise error on violation. If False, just log.
            log_violations: If True, collect violations for later reporting.
        """
        self.layers = layers or DEFAULT_LAYERS
        self.strict = strict
        self.log_violations = log_violations

    def find_spec(
        self,
        fullname: str,
        path: list[str] | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        """Check import for layer violations.

        This method is called for every import. We check if
        the import violates layer rules but don't actually
        load the module (return None to let other finders handle it).

        Args:
            fullname: Fully qualified module name being imported.
            path: Parent package path (if any).
            target: Target module (for reloads).

        Returns:
            None - we don't load modules, just check violations.

        Raises:
            LayerViolationError: If strict mode and violation detected.
        """
        # Get the importing module from the call stack
        frame = inspect.currentframe()
        if frame is not None:
            frame = frame.f_back  # Skip this frame to match _getframe(1) behavior
        while frame:
            module_name = frame.f_globals.get("__name__", "")
            if module_name and not module_name.startswith("importlib"):
                break
            frame = frame.f_back

        if not frame:
            return None

        importing_module = frame.f_globals.get("__name__", "")

        # Extract layer names from module paths
        source_layer = self._get_layer(importing_module)
        target_layer = self._get_layer(fullname)

        # Skip if not internal modules
        if source_layer is None or target_layer is None:
            return None

        source_tier = self.layers.get(source_layer, -1)
        target_tier = self.layers.get(target_layer, -1)

        # Skip unknown layers
        if source_tier < 0 or target_tier < 0:
            return None

        # Check for violation (importing from higher tier)
        if target_tier > source_tier:
            violation = {
                "source": importing_module,
                "target": fullname,
                "source_layer": source_layer,
                "target_layer": target_layer,
                "source_tier": source_tier,
                "target_tier": target_tier,
            }

            if self.log_violations:
                _violations.append(violation)

            if self.strict:
                raise LayerViolationError(source_layer, target_layer, source_tier, target_tier)

        return None

    def _get_layer(self, module_name: str) -> str | None:
        """Extract layer name from module path.

        Args:
            module_name: Full module name (e.g., 'lib.config').

        Returns:
            Layer name or None if not a layered module.
        """
        parts = module_name.split(".")
        if parts and parts[0] in self.layers:
            return parts[0]
        return None


def enable_layer_guard(
    layers: dict[str, int] | None = None,
    strict: bool = False,
) -> None:
    """Enable the runtime layer guard.

    Should be called early in application startup, before
    other imports are made.

    Args:
        layers: Custom layer configuration. Uses defaults if not provided.
        strict: If True, raise errors on violations. If False, just log.

    Example:
        # At the very start of your application
        import os
        if os.getenv("DEVKIT_DEV_MODE"):
            from core.layer_guard import enable_layer_guard
            enable_layer_guard(strict=True)

        # Now import your application modules
        from lib import config
    """
    global _enabled

    if _enabled:
        return

    guard = LayerGuard(layers=layers, strict=strict)
    sys.meta_path.insert(0, guard)
    _enabled = True


def disable_layer_guard() -> None:
    """Disable the runtime layer guard.

    Removes the LayerGuard from sys.meta_path.
    """
    global _enabled

    sys.meta_path[:] = [f for f in sys.meta_path if not isinstance(f, LayerGuard)]
    _enabled = False


def get_violations() -> list[dict]:
    """Get list of recorded layer violations.

    Returns:
        List of violation dictionaries with source, target, and tier info.
    """
    return _violations.copy()


def clear_violations() -> None:
    """Clear recorded violations."""
    _violations.clear()


def format_violations_report() -> str:
    """Format violations as a readable report.

    Returns:
        Formatted string report of all violations.
    """
    if not _violations:
        return "No layer violations detected."

    lines = [
        "Layer Violations Report",
        "=" * 50,
        "",
        f"Total violations: {len(_violations)}",
        "",
    ]

    lines.extend(
        f"- {v['source']} (T{v['source_tier']}) -> {v['target']} (T{v['target_tier']})"
        for v in _violations
    )

    return "\n".join(lines)


def is_enabled() -> bool:
    """Check if layer guard is currently enabled.

    Returns:
        True if the layer guard is active.
    """
    return _enabled
