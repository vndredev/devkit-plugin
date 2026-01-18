#!/usr/bin/env python3
"""ExitPlanMode hook handler.

Injects implementation instructions when exiting plan mode.
Creates plan marker file for feat/refactor branches.
"""

import re
from pathlib import Path

from lib.config import get
from lib.hooks import noop_response, output_response, read_hook_input

# Default instructions if not configured
DEFAULT_INSTRUCTIONS = [
    "YOU MUST complete one task at a time, mark done in todo list",
    "YOU MUST run linters after EVERY code change - use `uv run ruff check`",
    "YOU MUST run tests if available - use `uv run pytest`",
    "ALWAYS use conventional commits: type(scope): message",
    "ALWAYS ask if blocked or unclear - NEVER guess",
]


def get_tool_hint() -> str | None:
    """Generate tool hint dynamically from config.

    Returns:
        Tool hint string or None if not applicable.
    """
    project_type = get("project.type", "unknown")
    testing_framework = get("testing.framework", "")
    testing_enabled = get("testing.enabled", False)

    # Build test command based on framework
    test_cmd = ""
    if testing_enabled and testing_framework:
        if testing_framework == "pytest":
            test_cmd = "`uv run pytest`"
        elif testing_framework in ("jest", "vitest"):
            test_cmd = f"`npm run test` ({testing_framework})"

    # Build lint command based on project type
    lint_cmd = ""
    if project_type == "python":
        lint_cmd = "`uv run ruff check`"
    elif project_type in ("node", "nextjs", "typescript", "javascript"):
        lint_cmd = "`npm run lint`"

    # Combine into hint
    parts = []
    if test_cmd:
        parts.append(f"{test_cmd} for tests")
    if lint_cmd:
        parts.append(f"{lint_cmd} for linting")

    if parts:
        return "💡 " + ", ".join(parts)
    return None


def create_plan_marker(branch: str) -> None:
    """Create marker file for approved plan.

    Only creates marker for feat/* and refactor/* branches.

    Args:
        branch: Git branch name.
    """
    if not re.match(r"^(feat|refactor)/", branch):
        return

    sanitized = branch.replace("/", "-")
    marker = Path.cwd() / ".claude" / f".plan-approved-{sanitized}"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()


def build_instructions() -> str:
    """Build implementation instructions from config or defaults.

    Returns:
        Formatted instruction string.
    """
    # Load from new config structure
    implementation = get("hooks.plan.implementation", {})
    header = implementation.get("header", "## Implementation Phase")
    instructions = implementation.get("instructions", DEFAULT_INSTRUCTIONS)
    hints = get("hooks.plan.hints", [])

    lines = [header, ""]

    # Add numbered instructions
    for i, instruction in enumerate(instructions, 1):
        lines.append(f"{i}. {instruction}")

    # Add project-specific hints
    if hints:
        lines.append("")
        lines.append("**Project hints:**")
        lines.extend(f"- {hint}" for hint in hints)

    # Add dynamic tool hint
    tool_hint = get_tool_hint()
    if tool_hint:
        lines.append("")
        lines.append(tool_hint)

    return "\n".join(lines)


def main() -> None:
    """Handle PostToolUse for ExitPlanMode."""
    # Read hook data
    hook_data = read_hook_input()
    if not hook_data:
        noop_response()
        return

    # Check if hook is enabled
    if not get("hooks.plan.enabled", True):
        noop_response()
        return

    tool_name = hook_data.get("tool_name", "")

    # Only process ExitPlanMode
    if tool_name != "ExitPlanMode":
        noop_response()
        return

    # Create plan marker for feat/refactor branches (non-fatal)
    try:
        from lib.git import git_branch

        create_plan_marker(git_branch())
    except Exception:
        _ = None  # Marker creation is best-effort, non-fatal

    # Output loop instructions (from config or defaults)
    output_response(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": build_instructions(),
            }
        }
    )


if __name__ == "__main__":
    import json
    import sys

    try:
        main()
    except Exception as e:
        # On error, allow but report
        print(json.dumps({"continue": True, "message": f"⚠️ Plan hook error: {e}"}))
        sys.exit(0)
