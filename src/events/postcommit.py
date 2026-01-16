#!/usr/bin/env python3
"""PostToolUse:Bash hook - updates plugin version after git commit.

TIER 3: Entry point, may import from all layers.
"""

from lib.config import get
from lib.git import extract_git_args
from lib.hooks import get_project_dir, noop_response, output_response, read_hook_input
from lib.version import update_plugin_version


def main() -> None:
    """Handle PostToolUse:Bash - update version after commits."""
    hook_data = read_hook_input()

    # Only process Bash tool
    tool_name = hook_data.get("tool_name", "")
    if tool_name != "Bash":
        noop_response("PostToolUse")
        return

    # Check if devMode enabled
    if not get("project.devMode", False):
        noop_response("PostToolUse")
        return

    # Extract command
    tool_input = hook_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Detect git commit
    subcmd, _ = extract_git_args(command)
    if subcmd != "commit":
        noop_response("PostToolUse")
        return

    # Update plugin version with new commit ID
    project_dir = get_project_dir()
    if not project_dir:
        noop_response("PostToolUse")
        return

    ok, msg = update_plugin_version(project_dir)

    if ok:
        output_response(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": f"Plugin version updated: {msg}",
                }
            }
        )
    else:
        noop_response("PostToolUse")


if __name__ == "__main__":
    import json
    import sys

    try:
        main()
    except Exception as e:
        # On error, allow but report
        print(json.dumps({"continue": True, "message": f"⚠️ PostCommit hook error: {e}"}))
        sys.exit(0)
