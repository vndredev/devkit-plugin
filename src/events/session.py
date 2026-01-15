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

    # Gather context - only show what's relevant
    output_lines = []
    has_issues = False

    # Git status - compact format
    if get("hooks.session.show_git_status", True):
        try:
            branch = git_branch()
            status = git_status()

            git_parts = [f"📍 {branch}"]
            if status["staged"]:
                git_parts.append(f"⚡{len(status['staged'])} staged")
            if status["modified"]:
                git_parts.append(f"✏️{len(status['modified'])} modified")
            if status["untracked"]:
                git_parts.append(f"❓{len(status['untracked'])} untracked")

            output_lines.append(" | ".join(git_parts))
        except Exception:  # noqa: S110
            pass

    # Health check - only show if issues
    try:
        health_results = check_all()
        health_warning = format_compact(health_results)
        if health_warning:
            output_lines.append("")
            output_lines.append(health_warning)
            has_issues = True
    except Exception:  # noqa: S110
        pass

    # Commands hint - only if no issues (otherwise they know what to fix)
    if not has_issues:
        output_lines.append("")
        output_lines.append("Use `/dk` for commands, `/dk dev` for workflow")

    # Output
    result = {
        "hook": HookType.SESSION_START.value,
        "output": "\n".join(output_lines),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
