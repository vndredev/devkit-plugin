#!/usr/bin/env python3
"""PostToolUse hook handler for Write/Edit.

Formats files, checks architecture, and provides hints.
"""

import json
import sys
from pathlib import Path

from lib.config import get
from lib.tools import format_file


def check_arch_violation(file_path: str, prompt_tpl: str) -> str | None:
    """Check if file change introduces architecture violation.

    Args:
        file_path: Path to the changed file.
        prompt_tpl: Template for violation message with {message} placeholder.

    Returns:
        Warning message if violation found, None otherwise.
    """
    # Only check src/ Python files
    if "/src/" not in file_path or not file_path.endswith(".py"):
        return None

    try:
        from arch.check import check_arch

        result = check_arch()

        if not result["ok"] and result["violations"]:
            # Find violations related to this file
            for v in result["violations"]:
                if file_path.endswith(v["file"].lstrip("./")):
                    return prompt_tpl.format(message=v["message"])

        return None
    except Exception:
        return None


def sync_architecture_md(file_path: str, prompt_tpl: str) -> str | None:
    """Auto-create/update ARCHITECTURE.md.

    Creates if:
    - File doesn't exist and src/ file is being edited

    Updates when:
    - config.jsonc changes (arch.layers might have changed)
    - src/arch/ file changes

    Args:
        file_path: Path to the changed file.
        prompt_tpl: Template for success message.

    Returns:
        Status message if created/updated, None otherwise.
    """
    from pathlib import Path

    # Check if ARCHITECTURE.md exists
    arch_file = Path.cwd() / "docs" / "ARCHITECTURE.md"
    file_exists = arch_file.exists()

    # Triggers for update (only if file exists)
    update_triggers = ["config.jsonc", "/src/arch/"]
    should_update = file_exists and any(t in file_path for t in update_triggers)

    # Triggers for create (only if file doesn't exist)
    create_triggers = ["/src/"]
    should_create = not file_exists and any(t in file_path for t in create_triggers)

    if not should_update and not should_create:
        return None

    try:
        from arch.docs import update_architecture_md

        success, _msg = update_architecture_md()
        if success:
            action = "Created" if should_create else "Updated"
            return prompt_tpl.replace("Updated", action) if should_create else prompt_tpl
        return None
    except Exception:
        return None


def noop() -> None:
    """Output empty response for PostToolUse."""
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse"}}))


def main() -> None:
    """Handle PostToolUse hook for Write/Edit."""
    # Read hook data
    try:
        hook_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        noop()
        return

    # Check if hook is enabled
    if not get("hooks.format.enabled", True):
        noop()
        return

    tool_name = hook_data.get("tool_name", "")

    # Only process Write/Edit
    if tool_name not in ("Write", "Edit"):
        noop()
        return

    tool_input = hook_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        noop()
        return

    # Load prompts from config
    prompts = get("hooks.format.prompts", {})
    formatted_tpl = prompts.get("formatted", "✓ Formatted: {file}")
    test_reminder_tpl = prompts.get("test_reminder", "💡 New file - consider adding: tests/{file}")
    arch_violation_tpl = prompts.get("arch_violation", "⚠️ Arch violation: {message}")
    arch_synced_tpl = prompts.get("arch_synced", "📄 Updated docs/ARCHITECTURE.md")

    messages = []

    # Auto-format
    auto_format = get("hooks.format.auto_format", True)
    if auto_format:
        success, _msg = format_file(file_path)
        if success:
            messages.append(formatted_tpl.format(file=Path(file_path).name))

    # Check for missing tests - only for NEW files in src/
    filepath = Path(file_path)
    is_new_file = tool_name == "Write"
    is_source_file = "/src/" in file_path and filepath.suffix == ".py"
    is_not_test = not filepath.name.startswith("test_")
    is_not_init = filepath.name != "__init__.py"

    if is_new_file and is_source_file and is_not_test and is_not_init:
        # Check if test file exists in tests/ directory
        # src/lib/config.py -> tests/test_config.py
        test_file_name = f"test_{filepath.name}"
        project_root = get("_project_root", filepath.parent.parent.parent)
        tests_dir = Path(project_root) / "tests"
        test_file = tests_dir / test_file_name

        if not test_file.exists():
            messages.append(test_reminder_tpl.format(file=test_file_name))

    # Check architecture violations for src/ files
    arch_check = get("hooks.format.arch_check", True)
    if arch_check:
        arch_warning = check_arch_violation(file_path, arch_violation_tpl)
        if arch_warning:
            messages.append(arch_warning)

    # Auto-update ARCHITECTURE.md when arch-related files change
    auto_sync_arch = get("hooks.format.auto_sync_arch", True)
    if auto_sync_arch:
        sync_msg = sync_architecture_md(file_path, arch_synced_tpl)
        if sync_msg:
            messages.append(sync_msg)

    # Output with proper hook format
    result = {"hookSpecificOutput": {"hookEventName": "PostToolUse"}}
    if messages:
        result["hookSpecificOutput"]["additionalContext"] = "\n".join(messages)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
