"""Configuration management.

TIER 1: May import from core only.

Supports JSONC (JSON with Comments) for config files.
"""

import json
import os
from pathlib import Path
from typing import Any

from core.errors import ConfigError

# Cache for loaded config
_config_cache: dict | None = None
_project_root_cache: Path | None = None

# Config file names (priority order)
CONFIG_FILES = ["config.jsonc", "config.json"]


def strip_jsonc_comments(content: str) -> str:
    """Strip JSONC comments from content.

    Removes:
    - Single-line comments: // comment
    - Multi-line comments: /* comment */

    Preserves strings containing // or /* sequences.

    Args:
        content: JSONC content with comments.

    Returns:
        Valid JSON content without comments.
    """
    result = []
    i = 0
    in_string = False
    escape_next = False

    while i < len(content):
        char = content[i]

        # Handle escape sequences in strings
        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        # Track string boundaries
        if char == '"' and not escape_next:
            in_string = not in_string
            result.append(char)
            i += 1
            continue

        # Handle escape character
        if char == "\\" and in_string:
            escape_next = True
            result.append(char)
            i += 1
            continue

        # Skip comments only outside strings
        if not in_string:
            # Single-line comment
            if content[i : i + 2] == "//":
                # Skip until end of line
                while i < len(content) and content[i] != "\n":
                    i += 1
                continue

            # Multi-line comment
            if content[i : i + 2] == "/*":
                # Skip until */
                i += 2
                while i < len(content) - 1:
                    if content[i : i + 2] == "*/":
                        i += 2
                        break
                    i += 1
                continue

        result.append(char)
        i += 1

    return "".join(result)


def get_project_root() -> Path:
    """Get the project root directory.

    Looks for .claude/ directory or git root.

    Returns:
        Project root path.

    Raises:
        ConfigError: If project root cannot be found.
    """
    global _project_root_cache

    if _project_root_cache is not None:
        return _project_root_cache

    # Check environment variable first
    if env_root := os.environ.get("PROJECT_ROOT"):
        _project_root_cache = Path(env_root)
        return _project_root_cache

    # Walk up from current directory
    current = Path.cwd()
    while current != current.parent:
        if (current / ".claude").exists():
            _project_root_cache = current
            return _project_root_cache
        if (current / ".git").exists():
            _project_root_cache = current
            return _project_root_cache
        current = current.parent

    raise ConfigError("Could not find project root (no .claude/ or .git/ found)")


def get_config_path() -> Path | None:
    """Find config file path.

    Looks for config.jsonc first, then config.json.

    Returns:
        Path to config file, or None if not found.
    """
    devkit_dir = get_project_root() / ".claude" / ".devkit"

    for filename in CONFIG_FILES:
        config_path = devkit_dir / filename
        if config_path.exists():
            return config_path

    return None


def load_config() -> dict:
    """Load config from .claude/.devkit/config.jsonc or config.json.

    Supports JSONC (JSON with Comments) format.
    Looks for config.jsonc first, falls back to config.json.

    Returns:
        Configuration dictionary.
    """
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    config_path = get_config_path()

    if config_path is None:
        _config_cache = {}
        return _config_cache

    try:
        content = config_path.read_text()

        # Strip comments if JSONC
        if config_path.suffix == ".jsonc":
            content = strip_jsonc_comments(content)

        _config_cache = json.loads(content)
        return _config_cache
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid {config_path.name}: {e}") from e


def get(key: str, default: Any = None) -> Any:
    """Get config value by dot notation.

    Args:
        key: Dot-separated key path (e.g., "arch.layers").
        default: Default value if key not found.

    Returns:
        Config value or default.

    Example:
        get("project.name")  # Returns project name
        get("hooks.format.enabled", True)  # Returns True if not set
    """
    config = load_config()
    parts = key.split(".")

    value = config
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return default

    return value


def clear_cache() -> None:
    """Clear config cache (for testing)."""
    global _config_cache, _project_root_cache
    _config_cache = None
    _project_root_cache = None


# Recommended defaults for optional config sections
# These are added when running /dk plugin update on older configs
RECOMMENDED_DEFAULTS = {
    "hooks.plan.planning": {
        "requirements": [
            "Identify affected layers (check arch.layers)",
            "List files to modify vs. create",
            "Consider edge cases and error handling",
            "Check for breaking changes",
        ],
        "structure": [
            "## Overview - What and why",
            "## Affected Files - List with rationale",
            "## Implementation Steps - Ordered tasks",
            "## Testing Strategy - How to verify",
            "## Risks - What could go wrong",
        ],
    },
    "hooks.plan.implementation": {
        "header": "## Implementation Phase",
        "instructions": [
            "Complete one task at a time, mark done in todo list",
            "Run linters after code changes",
            "Run tests if available",
            "Use conventional commits: type(scope): message",
            "Ask if blocked or unclear",
        ],
    },
    "hooks.plan.hints": [],  # Empty array, project should customize
    "git.conventions": {
        "types": ["feat", "fix", "chore", "refactor", "test", "docs", "perf", "ci"],
        "scopes": {
            "mode": "strict",
            "allowed": [],
            "internal": ["internal", "review", "ci", "deps"],
        },
        "branch_pattern": "{type}/{description}",
    },
}


def get_missing_sections() -> list[str]:
    """Check which recommended config sections are missing.

    Returns:
        List of missing section paths (dot notation).
    """
    config = load_config()
    missing = []

    for key_path in RECOMMENDED_DEFAULTS:
        # Navigate to the parent and check if key exists
        parts = key_path.split(".")
        current = config

        found = True
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                found = False
                break

        if not found:
            missing.append(key_path)

    return missing


def _set_nested(config: dict, key_path: str, value: Any) -> None:
    """Set a nested value in config using dot notation."""
    parts = key_path.split(".")
    current = config

    # Navigate/create path to parent
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    # Set the value
    current[parts[-1]] = value


def upgrade_config() -> tuple[bool, list[str]]:
    """Add missing recommended sections to config.

    Modifies config.jsonc in place, preserving comments where possible.

    Returns:
        Tuple of (success, list of added sections).
    """
    config_path = get_config_path()
    if config_path is None:
        return False, ["No config file found"]

    missing = get_missing_sections()
    if not missing:
        return True, []

    # Load current config
    config = load_config()

    # Add missing sections
    added = []
    for key_path in missing:
        if key_path in RECOMMENDED_DEFAULTS:
            _set_nested(config, key_path, RECOMMENDED_DEFAULTS[key_path])
            added.append(key_path)

    if not added:
        return True, []

    # Write back - we need to preserve JSONC structure
    # For now, we'll read the file, parse it, and intelligently insert
    # This is complex, so we'll use a simpler approach: regenerate with comments

    try:
        _write_config_with_comments(config_path, config)
        clear_cache()  # Clear cache to reload
        return True, added
    except Exception as e:
        return False, [f"Failed to write config: {e}"]


def _write_config_with_comments(config_path: Path, config: dict) -> None:
    """Write config back with section comments."""
    # Build JSONC content with comments
    lines = ["{"]
    lines.append('  "$schema": "./config.schema.json",')
    lines.append("")

    # Section order and comments
    sections = [
        ("project", "IDENTITY - Project information"),
        ("git", "DEVELOPMENT - Git configuration"),
        ("github", "DEVELOPMENT - GitHub configuration"),
        ("linters", "QUALITY - Linters configuration"),
        ("testing", "QUALITY - Testing configuration"),
        ("hooks", "AUTOMATION - Hooks configuration"),
        ("changelog", "AUTOMATION - Changelog configuration"),
        ("deployment", "DEPLOYMENT - Platform configuration"),
        ("arch", "ARCHITECTURE - Layer configuration"),
        ("managed", "MANAGED FILES - Auto-generated files"),
    ]

    written_keys = {"$schema"}

    for key, comment in sections:
        if key not in config:
            continue

        lines.append(f"  // {'=' * 70}")
        lines.append(f"  // {comment}")
        lines.append(f"  // {'=' * 70}")

        # Format the section
        section_json = json.dumps({key: config[key]}, indent=2)
        # Extract just the key-value part (skip outer braces)
        section_lines = section_json.split("\n")[1:-1]
        lines.extend(section_lines)

        # Add comma if not last
        if lines[-1].rstrip().endswith("}"):
            lines[-1] = lines[-1].rstrip() + ","
        lines.append("")

        written_keys.add(key)

    # Write any remaining keys not in our order
    for key, value in config.items():
        if key in written_keys:
            continue
        section_json = json.dumps({key: value}, indent=2)
        section_lines = section_json.split("\n")[1:-1]
        lines.extend(section_lines)
        if lines[-1].rstrip().endswith("}"):
            lines[-1] = lines[-1].rstrip() + ","
        lines.append("")

    # Remove trailing comma from last section
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            lines[i] = lines[i].rstrip().rstrip(",")
            break

    lines.append("}")

    config_path.write_text("\n".join(lines))
