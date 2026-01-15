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

    # Load prompts from config
    prompts = get("hooks.session.prompts", {})
    branch_tpl = prompts.get("branch", "📍 {branch}")
    staged_tpl = prompts.get("staged", "⚡{count} staged")
    modified_tpl = prompts.get("modified", "✏️{count} modified")
    untracked_tpl = prompts.get("untracked", "❓{count} untracked")
    hint_tpl = prompts.get("hint", "Use `/dk` for commands, `/dk dev` for workflow")

    # Gather context - only show what's relevant
    output_lines = []
    has_issues = False

    # Git status - compact format
    git_status_line = ""
    if get("hooks.session.show_git_status", True):
        try:
            branch = git_branch()
            status = git_status()

            git_parts = [branch_tpl.format(branch=branch)]
            if status["staged"]:
                git_parts.append(staged_tpl.format(count=len(status["staged"])))
            if status["modified"]:
                git_parts.append(modified_tpl.format(count=len(status["modified"])))
            if status["untracked"]:
                git_parts.append(untracked_tpl.format(count=len(status["untracked"])))

            git_status_line = " | ".join(git_parts)
            output_lines.append(git_status_line)
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
        output_lines.append(hint_tpl)

    # Output
    result = {
        "hook": HookType.SESSION_START.value,
        "output": "\n".join(output_lines),
    }

    # Show systemMessage only for warnings (not shown to user, but in Claude context)
    if has_issues:
        warning_tpl = prompts.get(
            "system_warning", "⚠️ Project has issues - check with /dk plugin check"
        )
        result["systemMessage"] = warning_tpl

    print(json.dumps(result))


if __name__ == "__main__":
    main()
