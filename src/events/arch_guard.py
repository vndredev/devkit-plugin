#!/usr/bin/env python3
"""PreToolUse hook handler for Edit/Write - Architecture Guard.

Blocks edits that would introduce layer violations.
Warns about similar code that already exists (code discovery).
Uses arch.analyze for import extraction (no duplication).
"""

import fnmatch
from pathlib import Path

from lib.config import get
from lib.hooks import allow_response, deny_response, output_response, read_hook_input


def _file_matches_layer(file_path: str, layer_config: dict, layer_name: str) -> bool:
    """Check if a file path matches a layer's patterns.

    Args:
        file_path: The file path to check.
        layer_config: Layer configuration with patterns or path.
        layer_name: Name of the layer (fallback for path).

    Returns:
        True if file matches the layer.
    """
    # Support both new patterns format and legacy path format
    patterns = layer_config.get("patterns", [])
    if patterns:
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in patterns)

    # Legacy fallback: use path key or derive from layer name
    layer_path = layer_config.get("path", f"src/{layer_name}")
    return layer_path in file_path


def check_layer_violation_in_content(
    file_path: str, content: str, layers: dict
) -> tuple[bool, str | None]:
    """Check if content would introduce layer violations.

    Args:
        file_path: Path to the file being modified.
        content: The new file content to check.
        layers: Layer configuration dict from config.

    Returns:
        Tuple of (has_violation, violation_message).
    """
    # Import here to avoid circular imports (events is tier 3, arch is tier 2)
    from arch.analyze import extract_imports_from_content

    # Determine which layer this file belongs to
    file_layer = None
    file_tier = -1

    for layer_name, layer_config in layers.items():
        if _file_matches_layer(file_path, layer_config, layer_name):
            file_layer = layer_name
            file_tier = layer_config.get("tier", 0)
            break

    if file_layer is None:
        return False, None

    # Extract imports from content
    imports = extract_imports_from_content(content)

    # Check each import against layer rules
    for imported_module in imports:
        for layer_name, layer_config in layers.items():
            if layer_name == file_layer:
                continue

            # Check if this import references this layer
            if imported_module == layer_name:
                imported_tier = layer_config.get("tier", 0)

                # Violation: importing from higher tier
                if imported_tier > file_tier:
                    return True, (
                        f"{file_layer} (tier {file_tier}) cannot import from "
                        f"{layer_name} (tier {imported_tier})"
                    )

    return False, None


def check_code_discovery(content: str, file_path: str, threshold: float = 0.7) -> list[str]:
    """Check for similar existing code.

    Args:
        content: New content being written.
        file_path: Path to file being edited (excluded from search).
        threshold: Similarity threshold.

    Returns:
        List of warning messages for similar code found.
    """
    try:
        from arch.discovery import find_similar_code
    except ImportError:
        return []

    matches = find_similar_code(content, threshold=threshold, exclude_file=file_path)

    if not matches:
        return []

    warnings = []
    for match in matches[:3]:  # Top 3 matches
        similarity_pct = int(match.similarity * 100)
        warnings.append(f"[{similarity_pct}%] {match.file}:{match.line} → {match.signature}")

    return warnings


def simulate_edit(file_path: str, old_string: str, new_string: str) -> str | None:
    """Simulate an edit operation and return the resulting content.

    Args:
        file_path: Path to the file.
        old_string: String to replace.
        new_string: Replacement string.

    Returns:
        New file content, or None if simulation fails.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return None
        content = path.read_text()
        if old_string not in content:
            return None
        return content.replace(old_string, new_string, 1)
    except Exception:
        return None


def main() -> None:
    """Handle PreToolUse hook for Edit/Write - Architecture Guard."""
    hook_data = read_hook_input()
    if not hook_data:
        allow_response()
        return

    # Early exit if hook is disabled (check before any processing)
    if not get("hooks.arch_guard.enabled", True):
        allow_response()
        return

    tool_name = hook_data.get("tool_name", "")
    tool_input = hook_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Only check Python files
    if not file_path.endswith(".py"):
        allow_response()
        return

    # Get the new content to check
    new_content = None

    if tool_name == "Write":
        new_content = tool_input.get("content", "")
    elif tool_name == "Edit":
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")
        new_content = simulate_edit(file_path, old_string, new_string)

    if not new_content:
        allow_response()
        return

    # === Check 1: Layer Violations (BLOCKING) ===
    layers = get("arch.layers", {})
    if layers:
        # Check if file is in a managed layer
        is_in_layer = any(
            _file_matches_layer(file_path, layer_config, name)
            for name, layer_config in layers.items()
        )

        if is_in_layer:
            has_violation, violation_msg = check_layer_violation_in_content(
                file_path, new_content, layers
            )
            if has_violation:
                deny_response(f"🚫 BLOCKED - Layer violation: {violation_msg}")
                return

    # === Check 2: Code Discovery (WARNING) ===
    discovery_enabled = get("hooks.arch_guard.discovery_enabled", True)
    if discovery_enabled:
        threshold = get("hooks.arch_guard.discovery_threshold", 0.7)
        warnings = check_code_discovery(new_content, file_path, threshold)

        if warnings:
            # Output warning but allow the operation
            warning_msg = "⚠️ Similar code exists - consider reusing:\n" + "\n".join(
                f"  {w}" for w in warnings
            )
            output_response(
                {
                    "continue": True,
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "additionalContext": warning_msg,
                    },
                }
            )
            return

    allow_response()


if __name__ == "__main__":
    main()
