#!/usr/bin/env python3
"""SessionStart hook handler.

Displays git status, config info, health check, and dev workflow reminder.
"""

import contextlib
import json
import sys

from arch.check import check_all, format_compact
from core.types import HookType
from lib.config import get
from lib.git import git_branch, git_status


def main() -> None:
    """Handle SessionStart hook."""
    # Read hook data (consume stdin even if not used)
    with contextlib.suppress(json.JSONDecodeError):
        json.load(sys.stdin)

    # Check if hook is enabled
    if not get("hooks.session.enabled", True):
        return

    # Gather context
    output_lines = []

    # Project info
    project_name = get("project.name", "unknown")
    project_type = get("project.type", "unknown")
    output_lines.extend([
        f"Project: {project_name}",
        f"Type: {project_type}",
        "",
    ])

    # Git status
    if get("hooks.session.show_git_status", True):
        try:
            branch = git_branch()
            status = git_status()
            output_lines.append(f"Branch: {branch}")

            if status["staged"]:
                output_lines.append(f"Staged: {len(status['staged'])} files")
            if status["modified"]:
                output_lines.append(f"Modified: {len(status['modified'])} files")
            if status["untracked"]:
                output_lines.append(f"Untracked: {len(status['untracked'])} files")

            output_lines.append("")
        except Exception:  # noqa: S110
            pass

    # Health check
    try:
        health_results = check_all()
        health_warning = format_compact(health_results)
        if health_warning:
            output_lines.append(health_warning)
            output_lines.append("")
    except Exception:  # noqa: S110
        pass

    # Dev workflow reminder
    output_lines.extend([
        "Use `/dk dev` for development workflow:",
        "  /dk dev feat <desc>  - New feature",
        "  /dk dev fix <desc>   - Bug fix",
        "  /dk arch check       - Check architecture",
    ])

    # Output
    result = {
        "hook": HookType.SESSION_START.value,
        "output": "\n".join(output_lines),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
