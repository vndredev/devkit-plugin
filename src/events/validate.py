#!/usr/bin/env python3
"""PreToolUse hook handler.

Validates branch names, commit messages, and blocks dangerous commands.
"""

import json
import re
import sys

from core.types import HookAction, HookType
from lib.config import get

# Default types if not configured
DEFAULT_TYPES = ["feat", "fix", "chore", "refactor", "test", "docs", "perf", "ci"]


def validate_branch_name(branch: str) -> tuple[bool, str]:
    """Validate branch name follows convention from config.

    Args:
        branch: Branch name to validate.

    Returns:
        Tuple of (valid, message).
    """
    protected = get("git.protected_branches", ["main"])
    if branch in protected:
        return True, "Protected branch"

    # Get types from config
    types = get("git.conventions.types", DEFAULT_TYPES)
    types_pattern = "|".join(types)
    pattern = rf"^({types_pattern})/[\w-]+$"

    if not re.match(pattern, branch):
        return False, f"Branch '{branch}' should match: {{{types_pattern}}}/description"

    return True, "Valid branch name"


def validate_commit_message(msg: str) -> tuple[bool, str]:
    """Validate commit message follows convention from config.

    Args:
        msg: Commit message to validate.

    Returns:
        Tuple of (valid, message).
    """
    # Get config
    types = get("git.conventions.types", DEFAULT_TYPES)
    scope_mode = get("git.conventions.scopes.mode", "strict")
    allowed_scopes = get("git.conventions.scopes.allowed", [])
    internal_scopes = get("git.conventions.scopes.internal", [])

    # Build pattern from config types
    types_pattern = "|".join(types)
    pattern = rf"^({types_pattern})(\([^)]+\))?: .+"

    match = re.match(pattern, msg)
    if not match:
        return False, f"Commit should match: type(scope): message (types: {types_pattern})"

    # Validate scope if present and mode is strict
    if scope_mode == "strict" and match.group(2):
        scope = match.group(2)[1:-1]  # Remove parentheses
        all_valid = allowed_scopes + internal_scopes
        if all_valid and scope not in all_valid:
            return False, f"Unknown scope '{scope}'. Allowed: {', '.join(all_valid)}"

    return True, "Valid commit message"


def extract_git_args(cmd: str) -> tuple[str, list[str]]:
    """Extract git subcommand and args from command string.

    Args:
        cmd: Full command string.

    Returns:
        Tuple of (subcommand, args).
    """
    parts = cmd.split()
    if len(parts) < 2 or parts[0] != "git":
        return "", []

    return parts[1], parts[2:]


# Dangerous gh commands that are always blocked
BLOCKED_GH_COMMANDS = [
    "gh repo delete",
    "gh secret delete",
    "gh api -X DELETE",
]


def validate_gh_command(cmd: str) -> tuple[bool, str]:
    """Validate gh CLI commands.

    Blocks dangerous commands like repo delete, secret delete.

    Args:
        cmd: Full command string.

    Returns:
        Tuple of (valid, message).
    """
    # Check for blocked commands
    for blocked in BLOCKED_GH_COMMANDS:
        if blocked in cmd:
            return False, f"Blocked: '{blocked}' - too dangerous for automatic execution"

    # Warn if pr create without --body (should use template)
    if "gh pr create" in cmd and "--body" not in cmd:
        return False, "gh pr create requires --body with PR template"

    return True, "Valid gh command"


def main() -> None:
    """Handle PreToolUse hook."""
    # Read hook data
    try:
        hook_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    # Check if hook is enabled
    if not get("hooks.validate.enabled", True):
        return

    tool_name = hook_data.get("tool_name", "")
    tool_input = hook_data.get("tool_input", {})

    # Only validate Bash commands
    if tool_name != "Bash":
        return

    command = tool_input.get("command", "")

    # Validate gh commands
    if command.startswith("gh "):
        block_gh = get("hooks.validate.block_dangerous_gh", True)
        if block_gh:
            valid, msg = validate_gh_command(command)
            if not valid:
                result = {
                    "hook": HookType.PRE_TOOL_USE.value,
                    "action": HookAction.DENY.value,
                    "message": msg,
                }
                print(json.dumps(result))
                sys.exit(0)
        return

    # Validate git commands
    if not command.startswith("git "):
        return

    subcmd, args = extract_git_args(command)

    # Block dangerous commands
    block_force = get("hooks.validate.block_force_push", True)
    is_force_push = subcmd == "push" and ("--force" in args or "-f" in args)
    if block_force and is_force_push:
        result = {
            "hook": HookType.PRE_TOOL_USE.value,
            "action": HookAction.DENY.value,
            "message": "Force push is blocked. Use --force-with-lease if needed.",
        }
        print(json.dumps(result))
        sys.exit(0)

    # Validate branch creation
    if subcmd == "checkout" and "-b" in args:
        try:
            idx = args.index("-b")
            if idx + 1 < len(args):
                branch = args[idx + 1]
                valid, msg = validate_branch_name(branch)
                if not valid:
                    result = {
                        "hook": HookType.PRE_TOOL_USE.value,
                        "action": HookAction.DENY.value,
                        "message": msg,
                    }
                    print(json.dumps(result))
                    sys.exit(0)
        except (ValueError, IndexError):
            pass

    # Validate commit message
    if subcmd == "commit" and "-m" in args:
        try:
            idx = args.index("-m")
            if idx + 1 < len(args):
                msg = args[idx + 1]
                valid, err = validate_commit_message(msg)
                if not valid:
                    result = {
                        "hook": HookType.PRE_TOOL_USE.value,
                        "action": HookAction.DENY.value,
                        "message": err,
                    }
                    print(json.dumps(result))
                    sys.exit(0)
        except (ValueError, IndexError):
            pass


if __name__ == "__main__":
    main()
