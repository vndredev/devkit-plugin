#!/usr/bin/env python3
"""PostToolUse hook handler for Write/Edit.

Formats files and provides hints.
"""

import json
import sys
from pathlib import Path

from core.types import HookType
from lib.config import get
from lib.tools import format_file


def main() -> None:
    """Handle PostToolUse hook for Write/Edit."""
    # Read hook data
    try:
        hook_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    # Check if hook is enabled
    if not get("hooks.format.enabled", True):
        return

    tool_name = hook_data.get("tool_name", "")

    # Only process Write/Edit
    if tool_name not in ("Write", "Edit"):
        return

    tool_input = hook_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        return

    messages = []

    # Auto-format
    auto_format = get("hooks.format.auto_format", True)
    if auto_format:
        success, _msg = format_file(file_path)
        if success:
            messages.append(f"Formatted: {Path(file_path).name}")

    # Check for missing tests
    filepath = Path(file_path)
    if filepath.suffix == ".py" and not filepath.name.startswith("test_"):
        test_file = filepath.parent / f"test_{filepath.name}"
        if not test_file.exists():
            messages.append(f"Consider adding tests: test_{filepath.name}")

    # Output
    if messages:
        result = {
            "hook": HookType.POST_TOOL_USE.value,
            "output": "\n".join(messages),
        }
        print(json.dumps(result))


if __name__ == "__main__":
    main()
