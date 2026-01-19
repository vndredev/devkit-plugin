#!/usr/bin/env python3
"""Stop hook handler.

Checks for plugin updates after each response.
Runs when the main Claude Code agent has finished responding.
"""

from lib.config import get
from lib.hooks import consume_stdin, output_response
from lib.version import check_plugin_update, clear_plugin_cache, is_plugin_dev_mode


def main() -> None:
    """Handle Stop hook."""
    # Consume stdin (hook data not needed)
    consume_stdin()

    # Skip if hook is disabled
    if not get("hooks.session.enabled", True):
        output_response({})
        return

    # Skip update check in dev mode (we're developing the plugin locally)
    if is_plugin_dev_mode():
        output_response({})
        return

    # Check for plugin updates
    try:
        update_available, current, latest = check_plugin_update()

        if update_available and latest:
            # Clear cache so next session loads new version
            clear_plugin_cache()

            # Notify user
            current_display = current or "unknown"
            output_response(
                {
                    "systemMessage": (
                        f"Plugin update available: {current_display} → {latest}. "
                        "Restart session to apply."
                    ),
                }
            )
            return

    except (ImportError, OSError):
        pass

    # No update or check failed - silent exit
    output_response({})


if __name__ == "__main__":
    main()
