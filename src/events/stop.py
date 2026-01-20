#!/usr/bin/env python3
"""Stop hook handler.

Checks for plugin updates and protection sync after each response.
Runs when the main Claude Code agent has finished responding.
"""

from lib.config import get
from lib.hooks import consume_stdin, output_response
from lib.version import check_plugin_update, clear_plugin_cache, is_plugin_dev_mode


def check_protection_sync() -> str | None:
    """Check if GitHub protection matches config.

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

    try:
        from lib.github import compare_protection_config, get_repo_info

        # Get repo from git remote
        repo_info = get_repo_info()
        if not repo_info:
            return None

        repo = f"{repo_info.owner}/{repo_info.name}"
        discrepancies = compare_protection_config(repo, protection_config)
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
