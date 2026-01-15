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
        if char == '\\' and in_string:
            escape_next = True
            result.append(char)
            i += 1
            continue

        # Skip comments only outside strings
        if not in_string:
            # Single-line comment
            if content[i:i+2] == '//':
                # Skip until end of line
                while i < len(content) and content[i] != '\n':
                    i += 1
                continue

            # Multi-line comment
            if content[i:i+2] == '/*':
                # Skip until */
                i += 2
                while i < len(content) - 1:
                    if content[i:i+2] == '*/':
                        i += 2
                        break
                    i += 1
                continue

        result.append(char)
        i += 1

    return ''.join(result)


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
