"""Configuration management.

TIER 1: May import from core only.
"""

import json
import os
from pathlib import Path
from typing import Any

from core.errors import ConfigError

# Cache for loaded config
_config_cache: dict | None = None
_project_root_cache: Path | None = None


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


def load_config() -> dict:
    """Load config from .claude/.devkit/config.json.

    Returns:
        Configuration dictionary.
    """
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    config_path = get_project_root() / ".claude" / ".devkit" / "config.json"

    if not config_path.exists():
        _config_cache = {}
        return _config_cache

    try:
        _config_cache = json.loads(config_path.read_text())
        return _config_cache
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid config.json: {e}") from e


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
