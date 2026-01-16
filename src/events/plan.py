#!/usr/bin/env python3
"""ExitPlanMode hook handler.

Injects implementation instructions when exiting plan mode.
"""

import json
import sys

from lib.config import get

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


def noop() -> None:
    """Output empty response for PostToolUse."""
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse"}}))


def main() -> None:
    """Handle PostToolUse for ExitPlanMode."""
    # Read hook data
    try:
        hook_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        noop()
        return

    # Check if hook is enabled
    if not get("hooks.plan.enabled", True):
        noop()
        return

    tool_name = hook_data.get("tool_name", "")

    # Only process ExitPlanMode
    if tool_name != "ExitPlanMode":
        noop()
        return

    # Output loop instructions (from config or defaults)
    result = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": build_instructions(),
        }
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
