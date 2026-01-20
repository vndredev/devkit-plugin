#!/usr/bin/env python3
"""Stop hook handler.

Checks for plugin updates and protection sync after each response.
Runs when the main Claude Code agent has finished responding.
"""

import json
import time
from pathlib import Path

from lib.config import get
from lib.hooks import consume_stdin, get_project_dir, output_response
from lib.version import check_plugin_update, clear_plugin_cache, is_plugin_dev_mode

# Default cache TTL in seconds (5 minutes)
DEFAULT_PROTECTION_CHECK_TTL = 300


def _get_cache_file() -> Path:
    """Get path to protection check cache file."""
    try:
        project_dir = get_project_dir()
        cache_dir = project_dir / ".claude" / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "protection_check.json"
    except (OSError, Exception):
        return Path("/tmp/devkit_protection_check.json")


def _is_cache_valid() -> bool:
    """Check if protection check cache is still valid.

    Returns:
        True if cache exists and is within TTL, False otherwise.
    """
    cache_file = _get_cache_file()
    if not cache_file.exists():
        return False

    try:
        cache_data = json.loads(cache_file.read_text())
        last_check = cache_data.get("timestamp", 0)
        ttl = get("hooks.session.protection_check_ttl", DEFAULT_PROTECTION_CHECK_TTL)
        return (time.time() - last_check) < ttl
    except (json.JSONDecodeError, OSError, Exception):
        return False


def _update_cache(discrepancies: list) -> None:
    """Update protection check cache.

    Args:
        discrepancies: List of discrepancies found (empty if in sync).
    """
    cache_file = _get_cache_file()
    try:
        cache_data = {
            "timestamp": time.time(),
            "discrepancies": discrepancies,
        }
        cache_file.write_text(json.dumps(cache_data))
    except (OSError, Exception):
        pass


def _get_cached_discrepancies() -> list | None:
    """Get cached discrepancies if cache is valid.

    Returns:
        Cached discrepancies list, or None if cache invalid.
    """
    if not _is_cache_valid():
        return None

    cache_file = _get_cache_file()
    try:
        cache_data = json.loads(cache_file.read_text())
        return cache_data.get("discrepancies", [])
    except (json.JSONDecodeError, OSError, Exception):
        return None


def check_protection_sync() -> str | None:
    """Check if GitHub protection matches config.

    Uses caching to avoid repeated API calls. Only checks every N seconds
    (configurable via hooks.session.protection_check_ttl, default 5 min).

    Returns:
        Warning message if out of sync, None otherwise.
    """
    # Skip if protection check is disabled
    if not get("hooks.session.check_protection", True):
        return None

    # Get protection config
    protection_config = get("github.protection", {})
    if not protection_config.get("enabled", True):
        return None

    # Check cache first
    cached = _get_cached_discrepancies()
    if cached is not None:
        # Use cached result
        if not cached:
            return None
        issues = [
            f"{d['setting']}={d['config_value']} (GitHub: {d['github_value']})" for d in cached
        ]
        return f"⚠️ Protection out of sync: {', '.join(issues)} - run /dk git init"

    # Cache miss - do actual check
    try:
        from lib.github import compare_protection_config, get_repo_info

        # Get repo from git remote
        repo_info = get_repo_info()
        if not repo_info:
            return None

        repo = f"{repo_info.owner}/{repo_info.name}"
        discrepancies = compare_protection_config(repo, protection_config)

        # Update cache
        _update_cache(discrepancies)

        if not discrepancies:
            return None

        # Format discrepancies into warning
        issues = []
        for d in discrepancies:
            setting = d["setting"]
            config_val = d["config_value"]
            github_val = d["github_value"]
            issues.append(f"{setting}={config_val} (GitHub: {github_val})")

        return f"⚠️ Protection out of sync: {', '.join(issues)} - run /dk git init"

    except (ImportError, OSError, Exception):
        return None


def main() -> None:
    """Handle Stop hook."""
    # Consume stdin (hook data not needed)
    consume_stdin()

    # Skip if hook is disabled
    if not get("hooks.session.enabled", True):
        output_response({})
        return

    messages = []

    # Skip update check in dev mode (we're developing the plugin locally)
    if not is_plugin_dev_mode():
        # Check for plugin updates
        try:
            update_available, current, latest = check_plugin_update()

            if update_available and latest:
                # Clear cache so next session loads new version
                clear_plugin_cache()
                current_display = current or "unknown"
                messages.append(
                    f"Plugin update available: {current_display} → {latest}. "
                    "Restart session to apply."
                )
        except (ImportError, OSError):
            pass

    # Check protection sync (always, even in dev mode)
    protection_warning = check_protection_sync()
    if protection_warning:
        messages.append(protection_warning)

    # Output messages if any
    if messages:
        output_response({"systemMessage": "\n".join(messages)})
    else:
        output_response({})


if __name__ == "__main__":
    main()
