#!/usr/bin/env python3
"""PostToolUse hook handler for Write/Edit.

Formats files, checks architecture, and provides hints.
"""

import subprocess
from pathlib import Path

from lib.config import get
from lib.hooks import noop_response, output_response, read_hook_input
from lib.tools import format_file

# Code file extensions that require workflow
CODE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"}

# Frontend file extensions for browser verification
FRONTEND_EXTENSIONS = {".tsx", ".jsx", ".vue", ".svelte", ".css", ".scss", ".html", ".astro"}


def check_workflow_required(file_path: str) -> str | None:
    """Check if editing code on main branch without workflow.

    Args:
        file_path: Path to the changed file.

    Returns:
        Warning message if workflow required, None otherwise.
    """
    # Check if enforcement is enabled
    enforce_mode = get("hooks.format.enforce_workflow", "warn")
    if enforce_mode == "off":
        return None

    # Check if it's a code file
    suffix = Path(file_path).suffix
    if suffix not in CODE_EXTENSIONS:
        return None

    # Skip test files and config files
    if "/tests/" in file_path or "test_" in file_path:
        return None

    # Get current branch
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = result.stdout.strip()
    except Exception:
        return None

    # Check if on protected branch
    protected = get("git.protected_branches", ["main", "master"])
    if branch not in protected:
        return None

    # On main/master editing code - warn or block
    msg = f"⚠️ Editing code on `{branch}` - use `/dk dev feat|fix|chore <desc>` first"
    return msg


def check_frontend_change(file_path: str) -> str | None:
    """Return reminder if frontend file changed.

    Args:
        file_path: Path to the changed file.

    Returns:
        Reminder message if frontend file, None otherwise.
    """
    # Check if browser hook is enabled
    if not get("hooks.browser.enabled", True):
        return None

    suffix = Path(file_path).suffix
    if suffix not in FRONTEND_EXTENSIONS:
        return None

    # Get dev server URL from config
    dev_url = get("hooks.browser.dev_server.url", "http://localhost:3000")

    # Load prompt template
    prompts = get("hooks.browser.prompts", {})
    reminder_tpl = prompts.get(
        "frontend_changed",
        "🌐 Frontend changed - verify UI: `/dk browser verify` or browser_snapshot on {url}",
    )

    return reminder_tpl.format(url=dev_url)


def check_arch_violation(file_path: str) -> tuple[str | None, bool]:
    """Check if file change introduces architecture violation.

    Args:
        file_path: Path to the changed file.

    Returns:
        Tuple of (raw violation message, is_blocking). is_blocking=True means Claude
        MUST fix this before continuing.
    """
    # Only check src/ Python files
    if "/src/" not in file_path or not file_path.endswith(".py"):
        return None, False

    try:
        from arch.check import check_arch

        ok, violations = check_arch()

        if not ok and violations:
            # Find violations related to this file
            for v in violations:
                if "file" not in v:
                    continue
                if file_path.endswith(v["file"].lstrip("./")):
                    # Layer violations are blocking errors
                    is_layer_violation = (
                        "layer" in v.get("rule", "").lower()
                        or "tier" in v.get("message", "").lower()
                    )
                    return v["message"], is_layer_violation

        return None, False
    except Exception:
        return None, False


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
    # Check if ARCHITECTURE.md exists
    from lib.config import get_project_root

    arch_file = get_project_root() / "docs" / "ARCHITECTURE.md"
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


def main() -> None:
    """Handle PostToolUse hook for Write/Edit."""
    # Read hook data
    hook_data = read_hook_input()
    if not hook_data:
        noop_response()
        return

    # Check if hook is enabled
    if not get("hooks.format.enabled", True):
        noop_response()
        return

    tool_name = hook_data.get("tool_name", "")

    # Only process Write/Edit
    if tool_name not in ("Write", "Edit"):
        noop_response()
        return

    tool_input = hook_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        noop_response()
        return

    # Load prompts from config
    prompts = get("hooks.format.prompts", {})
    formatted_tpl = prompts.get("formatted", "✓ Formatted: {file}")
    test_reminder_tpl = prompts.get("test_reminder", "💡 New file - consider adding: tests/{file}")
    arch_violation_tpl = prompts.get("arch_violation", "⚠️ Arch violation: {message}")
    arch_synced_tpl = prompts.get("arch_synced", "📄 Updated docs/ARCHITECTURE.md")

    messages = []

    # Check workflow enforcement (editing code on main)
    workflow_msg = check_workflow_required(file_path)
    if workflow_msg:
        messages.append(workflow_msg)

    # Auto-format
    auto_format = get("hooks.format.auto_format", True)
    if auto_format:
        success, _msg = format_file(file_path)
        if success:
            messages.append(formatted_tpl.format(file=Path(file_path).name))

    # Check for missing artifacts (tests, docs) - only for NEW files
    filepath = Path(file_path)
    is_new_file = tool_name == "Write"
    is_source_file = "/src/" in file_path and filepath.suffix == ".py"
    is_not_test = not filepath.name.startswith("test_")
    is_not_init = filepath.name != "__init__.py"

    if is_new_file and is_source_file and is_not_test and is_not_init:
        try:
            from arch.consistency import get_missing_artifacts

            missing = get_missing_artifacts(file_path)
            if missing:
                # Use configured template with first missing artifact
                messages.append(test_reminder_tpl.format(file=missing[0]))
        except ImportError:
            # Fallback to simple check if consistency module not available
            from lib.config import get_project_root

            test_file_name = f"test_{filepath.name}"
            project_root = get_project_root()
            tests_dir = project_root / "tests"
            test_file = tests_dir / test_file_name

            if not test_file.exists():
                messages.append(test_reminder_tpl.format(file=test_file_name))

    # Check architecture violations for src/ files
    arch_check = get("hooks.format.arch_check", True)
    if arch_check:
        violation_msg, is_blocking = check_arch_violation(file_path)
        if violation_msg:
            if is_blocking:
                # Layer violations are critical - Claude MUST fix immediately
                blocking_tpl = get(
                    "hooks.format.prompts.arch_blocking",
                    "🚫 LAYER VIOLATION - FIX NOW: {message}. "
                    "Revert the import or fix the architecture.",
                )
                messages.append(blocking_tpl.format(message=violation_msg))
            else:
                messages.append(arch_violation_tpl.format(message=violation_msg))

    # Auto-update ARCHITECTURE.md when arch-related files change
    auto_sync_arch = get("hooks.format.auto_sync_arch", True)
    if auto_sync_arch:
        sync_msg = sync_architecture_md(file_path, arch_synced_tpl)
        if sync_msg:
            messages.append(sync_msg)

    # Check frontend file changes for browser verification reminder
    frontend_msg = check_frontend_change(file_path)
    if frontend_msg:
        messages.append(frontend_msg)

    # Output with proper hook format
    result: dict = {"hookSpecificOutput": {"hookEventName": "PostToolUse"}}
    if messages:
        result["hookSpecificOutput"]["additionalContext"] = "\n".join(messages)
    output_response(result)


if __name__ == "__main__":
    main()
