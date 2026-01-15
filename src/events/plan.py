#!/usr/bin/env python3
"""ExitPlanMode hook handler.

Injects loop instructions when exiting plan mode.
"""

import json
import sys

from core.types import HookType
from lib.config import get

LOOP_INSTRUCTIONS = """
## Implementation Phase

You are now in implementation mode. Follow these steps:

1. **Work through the plan systematically**
   - Complete one task at a time
   - Mark tasks as done in your todo list

2. **Test as you go**
   - Run linters after code changes
   - Run tests if available

3. **Commit logical chunks**
   - Use conventional commits: type(scope): message
   - Don't batch too many changes

4. **Ask if blocked**
   - If unclear about requirements, ask
   - If hitting errors, show them
"""


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

    # Output loop instructions
    result = {
        "hook": HookType.POST_TOOL_USE.value,
        "output": LOOP_INSTRUCTIONS.strip(),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
