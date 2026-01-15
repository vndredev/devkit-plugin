#!/usr/bin/env python3
"""ExitPlanMode hook handler.

Injects loop instructions when exiting plan mode.
"""

import json
import sys

from core.types import HookType
from lib.config import get

# Default instructions if not configured
DEFAULT_INSTRUCTIONS = [
    "Complete one task at a time, mark done in todo list",
    "Run linters after code changes",
    "Run tests if available",
    "Use conventional commits: type(scope): message",
    "Ask if blocked or unclear",
]


def build_instructions() -> str:
    """Build implementation instructions from config or defaults.

    Returns:
        Formatted instruction string.
    """
    # Get project-specific instructions from config
    custom_instructions = get("hooks.plan.instructions", [])
    project_type = get("project.type", "unknown")

    # Use custom if provided, otherwise defaults
    instructions = custom_instructions if custom_instructions else DEFAULT_INSTRUCTIONS

    # Add project-type specific hints
    type_hints = {
        "python": "Use `uv run pytest` for tests, `uv run ruff check` for linting",
        "nextjs": "Use `npm test` for tests, `npm run lint` for linting",
        "node": "Use `npm test` for tests, `npm run lint` for linting",
    }

    lines = [
        "## Implementation Phase",
        "",
    ]

    for i, instruction in enumerate(instructions, 1):
        lines.append(f"{i}. {instruction}")

    # Add type-specific hint
    if project_type in type_hints:
        lines.append("")
        lines.append(f"💡 {type_hints[project_type]}")

    return "\n".join(lines)


def main() -> None:
    """Handle PostToolUse for ExitPlanMode."""
    # Read hook data
    try:
        hook_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    # Check if hook is enabled
    if not get("hooks.plan.enabled", True):
        return

    tool_name = hook_data.get("tool_name", "")

    # Only process ExitPlanMode
    if tool_name != "ExitPlanMode":
        return

    # Output loop instructions (from config or defaults)
    result = {
        "hook": HookType.POST_TOOL_USE.value,
        "output": build_instructions(),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
